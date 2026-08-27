#!/usr/bin/env python3
"""
OVERWATCH — a standing debug sweep. Structure checked continuously, code read by the model.

THE OWNER'S BRIEF
-----------------
    "you should develop an overwatch module that watches all modules for bugs, breaks, and
     inconsistencies and such, or even just have ollama run itself against all the modules all
     the time reporting on what's up and what should be fixing it ... that way there's a
     constant debug sweep active"

Right, and it follows from everything found so far. `allsweep` is a snapshot: somebody runs it,
reads it, acts. Every fault in this project's history was detectable by a measurement nobody was
taking at the time — four modules that would not import, a numbers-verifier that had not run, an
Assay publishing narrower intervals for less knowledge. None of them were hard to find. They
were simply not being looked for between the moments somebody looked.

WHAT IT WATCHES, AND WHY TWO KINDS
----------------------------------
STRUCTURE is cheap, total and objective. Imports, file integrity, subsystem reconciliation --
the `allsweep` tiers, run on a loop. It cannot miss a break and it cannot invent one.

SEMANTICS is what structure cannot reach. A module that imports, parses, runs, and quietly does
the wrong thing passes every structural check there is. `read.py` called `P.ask` instead of
`_ask` for a whole morning: valid Python, correct types, no exception, and the entire cloud pool
sat idle while one GPU serialised. No import check would ever have caught it. Reading the code
would have, in about ten seconds.

So the model reads the modules. **Locally, on the GPU, deliberately** -- the corpus reader now
runs through Cascade's cloud buckets, which leaves the card idle, and code review is exactly the
work to put on an idle local model: unlimited, private, and not competing for the meters the
library's actual reading depends on.

WHY THE FINDINGS ARE FILTERED HARD
----------------------------------
A model asked to find bugs will always find bugs. Most will be style, some will be wrong, and a
few will be real -- and a report that is 90% noise gets skimmed, which is worse than no report
because it teaches the reader that the watcher cries wolf. This project has already paid for
that lesson twice: a preflight FAIL that everyone learned to scroll past, and an auditor that
called an empty log file corrupt.

Three filters, in order:

    ANCHORED   a finding must name a symbol or a line that actually exists in the file. A
               claim about `feats.kinetic` is checkable; a claim about "the error handling"
               is not, and is dropped.
    NOVEL      findings are fingerprinted and remembered. The same one is reported ONCE, and
               stays open until the code it points at changes.
    SEVERE     "this could be clearer" is not a defect. The prompt asks for one class of thing
               -- code that does something OTHER than what it says -- and everything else is
               discarded on arrival.

The output is `WATCH.md`, written for a human to read in ten seconds, and `data/OVERWATCH.json`
for the ledger.
"""
import argparse
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

LEDGER = os.path.join(HERE, "data", "OVERWATCH.json")
REPORT = os.path.join(HERE, "WATCH.md")

# m40. What this process believed the ledger was when it last read or wrote it. `save()` compares
# it against the file on disk, because two PROCESSES can hold this ledger at once even though only
# this module ever writes it -- the standing `--loop` job plus any ad-hoc `verify_open` call. A
# save is a whole-file replace, so a writer holding an old snapshot erases everything the other
# recorded in between. None means "never read the file", where there is nothing to compare.
_SNAPSHOT = {"digest": None}
PY = sys.executable
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")

# Read the file in pieces this big. The local model's window is the binding constraint, and the
# measured lesson from the corpus reader applies here too: a longer passage thins attention and
# recall falls faster than the call count does. Small pieces, more of them.
SLICE = 7000

# How many review calls fell through to the cloud because the GPU was busy. Reported, so a
# watcher quietly running on the wrong resource is visible rather than merely slower.
_LOCAL_BUSY = [0]

# Open every file in the tree this often. Every round is too expensive while the roll and
# the reader are working; never is how a corrupt cache goes unnoticed for a day.
DEEP_EVERY = 6

# Review calls the watcher may take from the shared pool in one round when the GPU is busy.
# Small on purpose: the corpus read has priority over the code read, always.
CLOUD_BUDGET = 20

SYSTEM = """You are reviewing one slice of a Python module for DEFECTS OF FACT.

A defect of fact is code that does something OTHER than what its name, its docstring, or its
comment says it does. Those are the only findings wanted.

Report:
- a call to the wrong function where a similarly-named one is clearly meant
- a variable, attribute or key that is used but never defined in this file or its imports
- a docstring or comment that states behaviour the code contradicts
- a condition that can never be true, or never false
- a value hardcoded where the code around it says it should be derived
- an exception handler that discards a failure the surrounding comment says is important
- an off-by-one, a wrong default, a swapped argument

Do NOT report:
- style, naming, formatting, or how something reads
- missing tests, missing types, missing documentation
- anything you would phrase as "consider", "could be improved", or "might be clearer"
- anything you cannot point at a specific symbol or line for

Return JSON only:
{"findings": [{"symbol": "<the exact function, variable or attribute involved>",
               "claim": "<what the code says it does>",
               "actual": "<what it does instead>",
               "severity": "high"|"medium"}]}

Return {"findings": []} if the slice is sound. Most slices are sound. An empty list is the
expected answer and is never wrong to give."""

SCHEMA = {
    "type": "object",
    "properties": {"findings": {"type": "array", "items": {
        "type": "object",
        "properties": {"symbol": {"type": "string"}, "claim": {"type": "string"},
                       "actual": {"type": "string"}, "severity": {"type": "string"}},
        "required": ["symbol", "claim", "actual"]}}},
    "required": ["findings"],
}


# --------------------------------------------------------------------------- the ledger

def load():
    """The ledger, or a fresh one -- but never a fresh one that silently REPLACED a damaged one.

    m28. This used to answer every failure with an empty ledger, so a torn OVERWATCH.json
    discarded every open finding and the round counter, and the next save() wrote that emptiness
    back as fact. `health.flush()` faces the identical situation and handles it properly: keep
    the wreck as `.corrupt`, say so on stderr, and start fresh only then. Same treatment here.

    An ABSENT file and a DAMAGED one are not the same event and must not get the same response.
    Absent is the ordinary first run. Damaged means findings existed and are now unreadable --
    recoverable by hand from the preserved copy, but only if something preserves it.
    """
    fresh = {"findings": {}, "seen": {}, "rounds": 0}
    if not os.path.exists(LEDGER):
        _SNAPSHOT["digest"] = ""
        return fresh
    try:
        with open(LEDGER, encoding="utf-8") as f:
            d = json.load(f)
        _SNAPSHOT["digest"] = _digest(LEDGER)
        return d
    except Exception as e:
        _SNAPSHOT["digest"] = ""
        silence.note("overwatch.py:load")
        try:
            silence.replace_retry(LEDGER, LEDGER + ".corrupt")
            kept = os.path.basename(LEDGER) + ".corrupt"
        except Exception:
            silence.note("overwatch.py:load-preserve")
            kept = "NOT PRESERVED -- the wreck could not be renamed"
        print(f"overwatch: ledger unreadable ({type(e).__name__}); kept as {kept}. "
              f"Open findings and the round counter are NOT lost, but they are no longer live; "
              f"recover them from that file if the next round matters.", file=sys.stderr)
        return fresh


def save(d):
    """Write the ledger, MERGING first if another process wrote it since we read it.

    m40. A save is a whole-file replace, and two processes hold this ledger routinely: the
    standing `--loop` job, plus any ad-hoc `verify_open` call a maintenance run leaves behind.
    A writer holding a stale snapshot used to erase every finding recorded in between -- silently,
    because the write itself succeeds. Observed 2026-08-24: an orphaned 09:02 call, blocked on a
    model reply for two and a half hours, was one return away from wiping four findings and
    regressing the round counter from 68.

    Merging is safe here precisely because NOTHING in this module ever deletes a finding or a
    `seen` entry -- retirement is a state change, not a removal -- so the union of two ledgers
    loses nothing that either writer knew. See `_merge_ledgers` for the per-key rule.
    """
    try:
        os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
        d = _reconcile_with_disk(d)
        tmp = LEDGER + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1, sort_keys=True)
        # replace_retry, not a bare os.replace: the dashboard and the standards board both read
        # this file on their own clocks, and on Windows a rename is DENIED while a reader holds
        # the target -- which here would throw away the whole round's findings.
        silence.replace_retry(tmp, LEDGER)
        _SNAPSHOT["digest"] = _digest(LEDGER)
    except Exception:
        silence.note("overwatch.py:save")


def _fingerprint(module, f):
    key = f"{module}|{f.get('symbol','')}|{f.get('actual','')[:80]}".lower()
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _digest(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:
        silence.note("overwatch.py:digest")
        return ""


# How far along a finding's life a state is. A terminal verdict outranks an open one, so whichever
# writer reached the verdict wins the key -- in either direction, which is the point: the stale
# writer is not always the one with less to say, it is only the one that must not overwrite blind.
_STATE_RANK = {"open": 0, "stale": 1, "confirmed": 1, "refuted": 2, "retired": 2, "closed": 2}


def _progress(f):
    if not isinstance(f, dict):
        return (-1, "", 0)
    return (_STATE_RANK.get(str(f.get("state", "")).lower(), 0),
            str(f.get("retired_at") or f.get("closed_at") or ""),
            len(f))


def _merge_ledgers(disk, mine):
    """Union of two ledgers. Never drops a finding, a `seen` entry, or a round.

    Per-key rules, all of them monotone -- applying this twice changes nothing the second time:
      findings  union by fingerprint; a key in both goes to whichever is further along
                (`_progress`), ties to disk, since disk is by definition the more recent write.
      seen      union by module; a key in both goes to the LATER `at`, which is what the
                digest-vs-`at` staleness check downstream actually reads.
      rounds    max. It is a monotone counter and regressing it re-reviews finished work.
      last_run  max as a string; these are zero-padded 'YYYY-MM-DD HH:MM', so that is time order.
      anything else  mine, falling back to disk -- an unknown key is not something to guess at.
    """
    if not isinstance(disk, dict):
        return mine
    out = dict(disk)
    out.update({k: v for k, v in mine.items()
                if k not in ("findings", "seen", "rounds", "last_run")})

    df, mf = disk.get("findings") or {}, mine.get("findings") or {}
    merged = dict(df)
    for k, v in mf.items():
        if k not in merged or _progress(v) > _progress(merged[k]):
            merged[k] = v
    out["findings"] = merged

    ds, ms = disk.get("seen") or {}, mine.get("seen") or {}
    seen = dict(ds)
    for k, v in ms.items():
        old = seen.get(k)
        if not isinstance(old, dict) or float((v or {}).get("at") or 0) > float(old.get("at") or 0):
            seen[k] = v
    out["seen"] = seen

    try:
        out["rounds"] = max(int(disk.get("rounds") or 0), int(mine.get("rounds") or 0))
    except Exception:
        # A non-numeric round counter is not a thing to shrug at: it is the one field that says
        # how much review has already happened, and this merge exists to stop it regressing.
        silence.note("overwatch.py:merge-rounds")
        out["rounds"] = mine.get("rounds", disk.get("rounds", 0))
    lr = [str(x) for x in (disk.get("last_run"), mine.get("last_run")) if x]
    if lr:
        out["last_run"] = max(lr)
    return out


def _reconcile_with_disk(d):
    """`d`, or `d` merged over a ledger that changed underneath us since we read it."""
    known = _SNAPSHOT.get("digest")
    if known is None or not os.path.exists(LEDGER):
        return d                                  # never read it; nothing to be stale against
    current = _digest(LEDGER)
    if not current or current == known:
        return d
    try:
        with open(LEDGER, encoding="utf-8") as f:
            disk = json.load(f)
    except Exception:
        # Unreadable on disk. load() owns the preserve-the-wreck path; here the safe move is to
        # write what we hold rather than lose it too.
        silence.note("overwatch.py:reconcile")
        return d
    merged = _merge_ledgers(disk, d)
    gained = len(merged.get("findings", {})) - len(d.get("findings", {}))
    if gained > 0:
        print(f"overwatch: ledger changed under this process since it was read; merged rather "
              f"than replaced ({gained} finding(s) kept that this process had not seen).",
              file=sys.stderr)
    return merged


# --------------------------------------------------------------------------- structure

def structure(deep=True):
    """The objective half: what allsweep measures, reduced to a pass/fail per subsystem.

    `deep` opens all 45,000 files. That is a minute of disk on an idle machine and several
    minutes when the roll and the reader are both working, so on a loop it runs every DEEP_EVERY
    rounds rather than every round. The import tier is cheap and always runs -- it is the one
    that caught four dead modules, and it is the one most likely to catch the next.
    """
    out = {}
    try:
        import allsweep as A
        mods = [m for m in A.modules() if not m.startswith("_")]
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max(2, (os.cpu_count() or 4) - 2)) as ex:
            imports = list(ex.map(A.check_import, mods))
        out["broken_modules"] = [r["module"] + ": " + r["detail"]
                                 for r in imports if not r["ok"]]
        out["reconcile"] = [r for r in A.reconcile()
                            if r["finding"].isupper() or "no host" in r["finding"]
                            or "never catalogued" in r["finding"]
                            or "MORE THAN ONE" in r["finding"]]
    except Exception as e:
        silence.note("overwatch.py:structure-import-reconcile")
        out["error"] = f"{type(e).__name__}: {str(e)[:90]}"
    if not deep:
        return out
    try:
        import estate as E
        art = E.artifacts(workers=8)
        out["corrupt_files"] = [r["path"] + " — " + r["error"] for r in art["bad"]]
        out["files"] = art["total"]
    except Exception as e:
        silence.note("overwatch.py:structure-estate")
        out["estate_error"] = f"{type(e).__name__}: {str(e)[:90]}"
    return out


# --------------------------------------------------------------------------- semantics

def _ask(system, prompt, schema, local=True):
    """One review call. LOCAL by default, so this never competes with the corpus reader.

    The library's reading runs through Cascade's cloud buckets now, which leaves the GPU idle.
    Code review is the right thing to put there: unlimited, private, and metered by nobody.
    """
    import read as R
    if local:
        import pipeline as P
        nc = 4096 if len(prompt) + len(system) < 11000 else 8192
        got = P.ask(R.config(), system, prompt, schema, timeout=300, num_ctx=nc,
                    tag="overwatch")
        if got is not None:
            return got
        # LOCAL FIRST, BUT NEVER LOCAL-ONLY.
        #
        # The premise -- the GPU is idle now that the corpus reads through Cascade -- is true
        # most of the time and false exactly when the pipeline is doing its own model work.
        # Ollama then answers "maximum pending requests exceeded" and a watcher that insisted
        # on the card would simply stop watching, quietly, for as long as the busy period
        # lasted. A watcher that stops watching is the thing this file exists to prevent.
        _LOCAL_BUSY[0] += 1
        if _LOCAL_BUSY[0] > CLOUD_BUDGET:
            # THE WATCHER YIELDS. Reading the corpus is the work; watching the code is the
            # nicety that protects it. When the GPU is jammed, every review call the watcher
            # sends to Cascade is a passage the reader does not get read, and the pool's
            # sustained capacity is roughly 3,000 calls an hour for everything combined.
            # Better a round that says "the card was busy, I read less" than a watcher quietly
            # eating the library's throughput to check for bugs that will still be there in
            # twenty minutes.
            return None
    R.ensure_transport(verbose=False)
    return R._ask(R.config(), system, prompt, schema)


def _slices(path):
    with open(path, encoding="utf-8") as f:
        src = f.read()
    lines = src.splitlines(keepends=True)
    out, buf, start = [], [], 1
    for i, ln in enumerate(lines, 1):
        buf.append(ln)
        if sum(len(x) for x in buf) >= SLICE:
            out.append((start, i, "".join(buf)))
            buf, start = [], i + 1
    if buf:
        out.append((start, len(lines), "".join(buf)))
    return out


def _anchored(finding, src):
    """Does the finding point at something that exists?

    A model will happily report a defect in "the retry logic". That is unactionable and
    unverifiable, and half of them are hallucinated. Requiring the named symbol to appear
    literally in the file removes both problems at once and costs one string search.
    """
    sym = (finding.get("symbol") or "").strip()
    if not sym or len(sym) < 3:
        return False
    bare = sym.split("(")[0].split(".")[-1].strip()
    return bool(bare) and bare in src


def review(module, local=True):
    """Read one module and return (findings, complete). NOVEL filtering (has this finding
    already been logged) is the caller's job against its own ledger -- `review` used to take a
    `ledger` parameter it never read, which claimed a filter this function does not apply.

    `complete` is False the moment any slice's `_ask` comes back `None` -- the GPU was busy and
    this round's cloud budget was already spent (see `_ask`'s "THE WATCHER YIELDS" comment). A
    skipped slice and a slice the model actually read and found nothing in look identical from
    here: both hand `kept` nothing. `round_once` used to stamp the module `seen` regardless, which
    made an unreviewed module indistinguishable from a freshly-clean one to `rotation()` -- it was
    sorted to the BACK of the stale queue exactly as if it had been read, the worst place for a
    module nobody actually looked at. The caller now only stamps `seen` when `complete` is True,
    so a yielded review leaves the module's old timestamp in place and it comes back up soon.
    Order a3ee0d1d2d4c.
    """
    path = os.path.join(SRC, module + ".py")
    if not os.path.exists(path):
        return [], True
    with open(path, encoding="utf-8") as f:
        src = f.read()
    kept = []
    complete = True
    for start, end, chunk in _slices(path):
        got = _ask(SYSTEM, f"MODULE: {module}.py   LINES {start}-{end}\n\n{chunk}",
                   SCHEMA, local=local)
        if got is None:
            complete = False
        for f_ in (got or {}).get("findings", []):
            if (f_.get("severity") or "medium").lower() not in ("high", "medium"):
                continue
            if not _anchored(f_, src):
                continue
            f_["module"] = module
            f_["lines"] = [start, end]
            kept.append(f_)
    return kept, complete


# --------------------------------------------------------------------------- the round

VERIFY_SYSTEM = (
    "You are re-checking an OLD finding against the CURRENT code. The finding claims the code "
    "has a specific defect. Read the numbered code region and judge: 'refuted' if the code "
    "plainly does not have the defect as described (the claim mischaracterizes it, describes "
    "something the code guards against, or refers to a shape no longer present); 'confirmed' "
    "if the defect is really there as described; 'unclear' if this region cannot settle it. "
    "Never guess: unclear is the honest third answer. One-sentence why, citing a line number."
)

VERIFY_SCHEMA = {
    "type": "object",
    "properties": {"verdict": {"type": "string", "enum": ["confirmed", "refuted", "unclear"]},
                   "why": {"type": "string"}},
    "required": ["verdict", "why"],
}


def verify_open(led, local=True, budget=6):
    """The CLOSER the findings lifecycle never had (owner, 2026-08-24: "fix the bug that
    persists stale work orders instead of removing them").

    Digest-retirement clears findings whose file changed; nothing ever cleared the rest --
    every filed claim sat open until a person triaged it, and after a busy day the open count
    only grew. This re-verifies open findings oldest-verification-first against the current
    source, on the resident local model: refuted closes with a recorded verdict, confirmed
    stays open and says so, unclear cycles back later. Budgeted per round like the review
    rotation itself -- pacing, not truncation; every finding cycles through."""
    opens = sorted(((fid, f) for fid, f in led["findings"].items()
                    if f.get("state") == "open"),
                   key=lambda kv: kv[1].get("last_verified", kv[1].get("first_seen", 0)))
    checked = closed = 0
    for fid, f in opens[:budget]:
        path = os.path.join(SRC, f.get("module", "") + ".py")
        try:
            lines = open(path, encoding="utf-8").read().splitlines()
        except Exception:
            silence.note("overwatch.py:verify-read")
            continue
        span = f.get("lines") or [1, 1]
        a = max(0, int(span[0]) - 40)
        b = min(len(lines), int(span[-1]) + 40)
        region = chr(10).join("%d: %s" % (i, ln)
                              for i, ln in enumerate(lines[a:b], a + 1))
        prompt = ("FINDING under re-check, filed against %s.%s:%s" % (
                      f.get("module"), f.get("symbol"), chr(10))
                  + "CLAIM: " + str(f.get("claim"))[:400] + chr(10)
                  + "OBSERVED THEN: " + str(f.get("actual"))[:400] + chr(10) + chr(10)
                  + "CURRENT CODE (lines %d-%d of %s.py):" % (a + 1, b, f.get("module"))
                  + chr(10) + region)
        got = _ask(VERIFY_SYSTEM, prompt, VERIFY_SCHEMA, local=local)
        f["last_verified"] = time.time()
        checked += 1
        verdict = (got or {}).get("verdict")
        why = str((got or {}).get("why") or "")[:300]
        if verdict == "refuted":
            f["state"] = "closed"
            f["verdict"] = "auto-triage refuted: " + why
            f["closed_at"] = time.time()
            closed += 1
        elif verdict == "confirmed":
            f["confirmed_n"] = f.get("confirmed_n", 0) + 1
            f["last_confirm_why"] = why
    if checked:
        print("   auto-triage: %d open finding(s) re-verified, %d refuted and closed"
              % (checked, closed), flush=True)
    return checked, closed


def rotation(led, modules_all):
    """Which modules to read this round: the ones that changed, then the longest unread.

    A module nobody has touched since it was last read cannot have acquired a new defect, so
    re-reading it is spend with no expected return. A module that changed since the last round
    is exactly where a new defect would be.
    """
    changed, stale = [], []
    for m in modules_all:
        p = os.path.join(SRC, m + ".py")
        d = _digest(p)
        prev = (led["seen"].get(m) or {})
        if prev.get("digest") != d:
            changed.append(m)
        else:
            stale.append((prev.get("at", 0), m))
    stale.sort()
    return changed, [m for _, m in stale]


def write_report(led, struct):
    open_f = [f for f in led["findings"].values() if f.get("state") == "open"]
    hi = [f for f in open_f if (f.get("severity") or "").lower() == "high"]
    lines = [
        "# OVERWATCH",
        "",
        f"round {led['rounds']}  ·  last run {led.get('last_run', '?')}",
        "",
        "## Structure",
        "",
    ]
    broken = struct.get("broken_modules") or []
    corrupt = struct.get("corrupt_files") or []
    # A CHECK THAT CRASHED IS NOT A CHECK THAT PASSED.
    #
    # Found 2026-08-25 (run #23) by the whole-tree sweep. `structure()` records its own
    # failures in `struct["error"]` and `struct["estate_error"]`, and this function had never
    # read either key. So when the import scan or the artifact scan raised, `broken_modules`
    # and `corrupt_files` were simply ABSENT, `len([])` was 0, and WATCH.md announced
    # "modules that will not import: **0**" and "files that will not parse: **0** of 0
    # inspected" -- a clean bill of health printed by a check that never ran. In the file
    # whose entire job is to report what is wrong.
    #
    # The `of 0 inspected` was the only tell, and it is the kind of tell nobody reads.
    # An error now REPLACES the reassuring number rather than sitting beside it.
    if struct.get("error"):
        lines.append("- modules that will not import: **UNKNOWN — the import scan itself "
                     f"failed**  — {struct['error']}")
    else:
        lines.append(f"- modules that will not import: **{len(broken)}**"
                     + ("" if not broken else "  — " + ", ".join(broken[:4])))
    if struct.get("estate_error"):
        lines.append("- files that will not parse: **UNKNOWN — the artifact scan itself "
                     f"failed**  — {struct['estate_error']}")
    else:
        lines.append(f"- files that will not parse: **{len(corrupt)}** of "
                     f"{struct.get('files', 0):,} inspected"
                     + ("" if not corrupt else "  — " + "; ".join(corrupt[:3])))
    for r in (struct.get("reconcile") or []):
        n = r.get("count")
        lines.append(f"- {r['finding']}: **{n if n is not None else ''}** {r['detail'][:80]}")
    lines += ["", "## What the model found in the code", ""]
    if not open_f:
        lines.append("Nothing open. Every finding so far has been fixed or was retired when the "
                     "code it pointed at changed.")
    else:
        lines.append(f"**{len(open_f)} open** ({len(hi)} high). Newest first.")
        lines.append("")
        for f in sorted(open_f, key=lambda x: (-(x.get("severity") == "high"),
                                               -x.get("first_seen", 0)))[:40]:
            sev = (f.get("severity") or "medium").upper()
            lines.append(f"- **{f['module']}.py** `{f.get('symbol','')}` — [{sev}] "
                         f"{f.get('actual','')[:180]}")
            lines.append(f"  - says: {f.get('claim','')[:160]}")
    lines += ["", "---", "",
              "Written by `src/overwatch.py`. Structure is checked every round; the model reads "
              "modules that changed first, then whichever has gone longest unread. A finding "
              "stays open until the file it points at changes.", ""]
    # ATOMIC: WATCH.md is read by the maintenance pass and by anyone watching the loop; a
    # truncate-then-fill leaves it empty for the length of the write. Not JSON, so this uses
    # replace_retry directly rather than silence.write_json. 2026-08-25.
    _tmp = "%s.%d.tmp" % (REPORT, os.getpid())
    with open(_tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    silence.replace_retry(_tmp, REPORT)


def round_once(limit=6, local=True, skip_model=False):
    import allsweep as A
    # THE BUDGET IS PER ROUND, AND UNTIL NOW IT WAS PER PROCESS. CLOUD_BUDGET's own comment
    # calls it "calls the watcher may take from the shared pool in one round", and the yield it
    # guards is explicitly meant to last "for as long as the busy period lasted" -- but nothing
    # ever reset the counter. In `--loop` mode (the standing sweep, which runs for days) one
    # busy stretch pushed the lifetime total past 20 and every later GPU-busy call returned None
    # forever after, with no cloud fallback. The watcher quietly stopped watching, which this
    # file's own comment names as the thing it exists to prevent. Reset where the round begins.
    _LOCAL_BUSY[0] = 0
    led = load()
    led["rounds"] = led.get("rounds", 0) + 1
    led["last_run"] = time.strftime("%Y-%m-%d %H:%M")

    deep = (led["rounds"] % DEEP_EVERY) == 1 or DEEP_EVERY <= 1
    print("structure ..." + ("" if deep else "  (imports only this round)"), flush=True)
    struct = structure(deep=deep)
    if not deep:
        # Carry the last deep result forward rather than reporting zero, which would read as
        # "no corrupt files" when the truth is "not looked at this round".
        #
        # AND WITH NOTHING CACHED, SAY SO. An absent `last_deep` used to fill in `[]` and `0`,
        # which is the "0 of 0 inspected" clean bill of health that `write_report` below spends
        # a dozen lines explaining -- printed here instead of there.
        prev = led.get("last_deep") or {}
        if prev:
            struct.setdefault("corrupt_files", prev.get("corrupt_files", []))
            struct.setdefault("files", prev.get("files", 0))
        else:
            struct.setdefault("estate_error", "no deep artifact scan has completed yet -- "
                                              "there is no earlier result to carry forward")
    elif not struct.get("estate_error"):
        # ONLY A SCAN THAT RAN GETS CACHED. `structure(deep=True)` leaves `corrupt_files` and
        # `files` UNSET when the estate scan raises and records `estate_error` instead, so this
        # cached `{[], 0}` on a failed scan and overwrote the last real reading. THIS round still
        # reported honestly (write_report reads `estate_error`), but the next several shallow
        # rounds copied the poisoned zeros in above and carried no error key, so WATCH.md printed
        # "files that will not parse: 0 of 0 inspected" -- the exact false clean the 2026-08-25
        # fix was for, reappearing through the cache that fix did not cover, and surfacing rounds
        # after the failure where nobody would connect the two. A crashed scan now leaves the
        # last good reading in place instead of replacing it with a reassuring zero.
        led["last_deep"] = {"corrupt_files": struct.get("corrupt_files", []),
                            "files": struct.get("files", 0)}
    print(f"   {len(struct.get('broken_modules') or [])} module(s) will not import, "
          f"{len(struct.get('corrupt_files') or [])} file(s) will not parse", flush=True)

    # RETIRE findings whose file has changed. The code they point at no longer exists in that
    # form, so the finding is neither confirmed nor refuted -- it is stale, and carrying it
    # forward would slowly fill the report with claims about code that is gone.
    for fid, f in list(led["findings"].items()):
        if f.get("state") != "open":
            continue
        d = _digest(os.path.join(SRC, f["module"] + ".py"))
        if d and d != f.get("digest"):
            f["state"] = "retired"
            f["retired_at"] = led["last_run"]

    if not skip_model:
        verify_open(led, local=local, budget=limit)
        save(led)
        mods = [m for m in A.modules()
                if not m.startswith("_") and m not in ("overwatch", "allsweep")]
        changed, stale = rotation(led, mods)
        todo = (changed + stale)[:limit]
        print(f"model reads {len(todo)} module(s): {', '.join(todo)}", flush=True)
        for m in todo:
            t = time.time()
            try:
                found, complete = review(m, local=local)
            except Exception as e:
                silence.note("overwatch.py:review")
                print(f"   {m}: review failed ({type(e).__name__})", flush=True)
                continue
            d = _digest(os.path.join(SRC, m + ".py"))
            # ONLY A COMPLETE READ COUNTS AS SEEN. A slice skipped because the GPU was busy and
            # the round's cloud budget was spent (see `review`'s docstring) looks exactly like a
            # slice read and found clean -- both contribute zero findings -- so stamping `seen`
            # here regardless used to let an UNREVIEWED module get sorted to the back of
            # `rotation()`'s stale queue as if it had just been read. Leaving the old timestamp in
            # place on an incomplete read means the module stays near the front and comes back up
            # next round instead of waiting a full cycle. Order a3ee0d1d2d4c.
            if complete:
                led["seen"][m] = {"digest": d, "at": time.time()}
            fresh = 0
            for f in found:
                fid = _fingerprint(m, f)
                if fid in led["findings"]:
                    continue
                f.update({"state": "open", "first_seen": time.time(), "digest": d})
                led["findings"][fid] = f
                fresh += 1
            # Persist after EVERY module, not at the end of the round. A round is several
            # minutes and this process is meant to be killed and restarted freely; saving only
            # at the end means a restart silently discards everything the model just read, and
            # the next round re-reads the same files to find the same things.
            save(led)
            note = ""
            if _LOCAL_BUSY[0]:
                note = f"   (GPU busy; {min(_LOCAL_BUSY[0], CLOUD_BUDGET)} calls to the cloud"
                note += ", budget spent)" if _LOCAL_BUSY[0] > CLOUD_BUDGET else ")"
            if not complete:
                note += "   NOT MARKED SEEN -- a slice was skipped, retried next round"
            print(f"   {m:<24}{len(found):>3} raw  {fresh:>3} new   {time.time()-t:>5.0f}s"
                  + note, flush=True)

    save(led)
    write_report(led, struct)
    open_n = sum(1 for f in led["findings"].values() if f.get("state") == "open")
    print(f"\n{open_n} finding(s) open  ->  {REPORT}")
    return open_n


def main():
    # PLANT-WIDE INTERLOCK. The top rung of the escalation chain (escalation.py). If a
    # library-wide invariant has been violated, nothing starts until a person rules on it.
    # Placed first in main() so there is no path into this job that skips it.
    try:
        import escalation as _ESC
    except ImportError as _esc_gone:
        # FAIL CLOSED. This used to be `except ImportError: pass`, which meant a deleted or
        # unparseable `escalation.py` silently switched the plant-wide halt off in every job
        # at once -- nine sites, all of them quiet about it. That is Hard Rule -1's own
        # incident wearing different clothes: the last one began with an autonomous run
        # removing a safety it had concluded was unnecessary, and nothing downstream could
        # tell. A job that cannot ask whether the library is halted has no business
        # starting. Pinned by verify_math so the swallow cannot come back. (run #31)
        raise SystemExit(
            "REFUSING TO START: the escalation chain (src/escalation.py) could not be "
            "imported (%s), so the halt cannot be read. Hard Rule -1." % _esc_gone) from _esc_gone
    _ESC.assert_clear(os.path.basename(__file__))
    ap = argparse.ArgumentParser(description="a standing debug sweep over every module")
    ap.add_argument("--modules", type=int, default=6,
                    help="how many modules the model reads this round")
    ap.add_argument("--cloud", action="store_true",
                    help="review through Cascade instead of the local GPU (competes with read.py)")
    ap.add_argument("--structure-only", action="store_true",
                    help="skip the model pass; imports, files and reconciliation only")
    ap.add_argument("--loop", type=float, default=0,
                    help="keep going, this many minutes between rounds")
    ap.add_argument("--show", action="store_true", help="print the open findings and stop")
    a = ap.parse_args()

    if a.show:
        led = load()
        for f in sorted((f for f in led["findings"].values() if f.get("state") == "open"),
                        key=lambda x: x["module"]):
            print(f"  {f['module']}.py  {f.get('symbol','')}\n     {f.get('actual','')[:150]}")
        return 0

    import codewatch
    # ONE OF ME. Two `publish.py` daemons were observed running seventeen seconds
    # apart on 2026-08-25 after a restart race, and two writers into one export repo
    # is the failure `push()` documents at length. Fails open: if the process table
    # cannot be read this starts anyway, because not being able to look is not a
    # reason to take the job down.
    # ONLY IN LOOP MODE, and this needed correcting within the minute: the guard was
    # unconditional at first and immediately refused a hand-run one-shot `--push`
    # because the standing daemon was up. A one-shot is not a second daemon; it is a
    # person doing one thing deliberately, and a safety that blocks the operator
    # from acting is a safety that will be removed.
    if a.loop:
        codewatch.claim_singleton("overwatch")
        codewatch.stamp("overwatch")
    while True:
        print("=" * 88)
        print(f"OVERWATCH  {time.strftime('%H:%M:%S')}")
        print("=" * 88)
        round_once(limit=a.modules, local=not a.cloud, skip_model=a.structure_only)
        if not a.loop:
            return 0
        # PICK UP CODE CHANGES. A running process is a photograph of the source as it was
        # when it started, and on 2026-08-25 a `publish.py --loop` daemon from 14:28 pushed
        # deliberately-corrupted files to a public repo because the guard written to stop it
        # at 19:00 was never in its memory. Exits with rc=17 on purpose; the keeper's STANDING
        # set restarts it within five minutes running the current code. Budgeted and settled,
        # so an edit storm cannot turn this into a respawn loop -- see codewatch.py.
        codewatch.exit_if_stale("overwatch")
        time.sleep(a.loop * 60)


if __name__ == "__main__":
    sys.exit(main())
