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

# m28 tail. Set by `load()` when it found the ledger DAMAGED and could not set the wreck aside
# as `.corrupt`. `save()` refuses to write while it is on, because overwriting a file we could
# not first preserve destroys the only copy of whatever tore it. `health._flush_ledger` takes
# exactly this position on its own ledger ("PRESERVATION IS THE PRECONDITION, NOT A COURTESY");
# the two copies of this code now agree.
_UNPRESERVED = {"on": False}
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

class _NotALedger(ValueError):
    """Raised by `load()` for a file that PARSES but is not a ledger.

    It exists only so the wrong-shape case can travel the same road as the unparseable one --
    preserve the wreck, refuse the next save, hand back a fresh ledger -- while still printing a
    sentence a person can act on instead of the bare exception name. See `load`'s docstring."""


def load():
    """The ledger, or a fresh one -- but never a fresh one that silently REPLACED a damaged one.

    m28. This used to answer every failure with an empty ledger, so a torn OVERWATCH.json
    discarded every open finding and the round counter, and the next save() wrote that emptiness
    back as fact. `health.flush()` faces the identical situation and handles it properly: keep
    the wreck as `.corrupt`, say so on stderr, and start fresh only then. Same treatment here.

    An ABSENT file and a DAMAGED one are not the same event and must not get the same response.
    Absent is the ordinary first run. Damaged means findings existed and are now unreadable --
    recoverable by hand from the preserved copy, but only if something preserves it.

    DAMAGED INCLUDES WRONG-SHAPE, which is the half m28's fix did not cover. Only an UNPARSEABLE
    ledger reached the handler below; a ledger that is valid JSON but is not a ledger -- `null`,
    `[]`, `{}`, a bare string, an object with no `findings` -- parsed fine and was returned
    untouched, so the `.corrupt` preservation, the `_UNPRESERVED` refusal and this fresh-ledger
    fallback were ALL skipped and `round_once` died two statements later dereferencing it
    (AttributeError / TypeError / KeyError, one per shape). Under the keeper's restart set the
    standing `--loop` job then crashed EVERY round, forever, with the wreck never set aside --
    the exact m28 loss, through the one door the m28 quarantine did not cover. A file that
    parses but does not say what a ledger says is no better evidence than one that does not
    parse; it is the same fact, so it takes the same road. Order 302c7da84032.
    """
    fresh = {"findings": {}, "seen": {}, "rounds": 0}
    _UNPRESERVED["on"] = False        # a fresh read clears any refusal the last one raised
    if not os.path.exists(LEDGER):
        _SNAPSHOT["digest"] = ""
        return fresh
    try:
        with open(LEDGER, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            raise _NotALedger("the file holds %s, not a ledger object" % type(d).__name__)
        missing = [k for k in ("findings", "seen") if not isinstance(d.get(k), dict)]
        if missing:
            raise _NotALedger("no usable %s in it" % " or ".join(missing))
        _SNAPSHOT["digest"] = _digest(LEDGER)
        return d
    except Exception as e:
        _SNAPSHOT["digest"] = ""
        silence.note("overwatch.py:load")
        # GATED, and this is the half `health.py` already had right in its own copy of this
        # code. `replace_retry` NEVER RAISES -- a denied or failed rename comes back as False --
        # so the `except` this was wrapped in could not fire for the realistic failure (a reader
        # holding OVERWATCH.json open denies the rename on Windows), and `kept` announced
        # ".corrupt" for a wreck still sitting there under its own name. Worse than the wrong
        # message: `round_once` then `save()`s a FRESH ledger straight over the only copy of the
        # damaged one, so the findings the message promises are recoverable are gone. Ask the
        # verdict; on a refusal say so and stop this process from saving.
        if silence.replace_retry(LEDGER, LEDGER + ".corrupt"):
            kept = os.path.basename(LEDGER) + ".corrupt"
            tail = ("Open findings and the round counter are NOT lost, but they are no longer "
                    "live; recover them from that file if the next round matters.")
        else:
            silence.note("overwatch.py:load-preserve")
            kept = "NOT PRESERVED -- the rename was refused"
            tail = ("This process will NOT save over it, so nothing further is destroyed and "
                    "this round's findings are not persisted. Move data/OVERWATCH.json aside "
                    "by hand, or close whatever is holding it open, and rerun.")
            _UNPRESERVED["on"] = True
        why = str(e) if isinstance(e, _NotALedger) else type(e).__name__
        print(f"overwatch: ledger unreadable ({why}); kept as {kept}. {tail}",
              file=sys.stderr)
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
    # PRESERVATION IS THE PRECONDITION. `load()` found the ledger damaged and could not set the
    # wreck aside; writing here would replace the only copy of it with a fresh empty one.
    if _UNPRESERVED["on"]:
        silence.note("overwatch.py:save-refused-unpreserved")
        print("overwatch: NOT saving -- the ledger on disk is damaged and could not be moved to "
              ".corrupt. Writing over it would destroy the only copy. Findings from this round "
              "are not persisted.", file=sys.stderr)
        return False
    try:
        os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
        d = _reconcile_with_disk(d)
        tmp = LEDGER + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1, sort_keys=True)
        # replace_retry, not a bare os.replace: the dashboard and the standards board both read
        # this file on their own clocks, and on Windows a rename is DENIED while a reader holds
        # the target -- which here would throw away the whole round's findings.
        #
        # GATED: the comment above names the cost and the code then dropped the verdict that
        # reports it. `round_once` saves after EVERY module precisely so a restart cannot lose
        # the model's reads; a denied replace made each of those saves a no-op that looked
        # identical to a successful one, and the round went on printing its per-module lines.
        # Worse, `_SNAPSHOT["digest"]` was then re-stamped from the UNCHANGED file, so this
        # process's staleness guard agreed with disk and the loss left no trace anywhere.
        if not silence.replace_retry(tmp, LEDGER):
            print("overwatch: ledger write DENIED (a reader is holding %s open) -- this round's "
                  "findings did NOT land and will be re-derived next round."
                  % os.path.basename(LEDGER), file=sys.stderr)
            return False
        _SNAPSHOT["digest"] = _digest(LEDGER)
        return True
    except Exception:
        silence.note("overwatch.py:save")
        return False


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
        # ONE RUNNER, ONE CONTEXT -- and getting this wrong cost the library its local rung for
        # thirty-one hours. This sized the window to the prompt (4096 under ~11k chars, else
        # 8192), which reads as thrift and is the opposite. Ollama holds a model at ONE context
        # size: a request naming a different num_ctx does not get a cheaper window, it forces
        # the runner to be REBUILT. This daemon loops continuously, so every cycle it dragged
        # the resident model back down to 4096 while `pipeline.ask` asked for config's 12288 --
        # and both of them send `keep_alive: -1`, so whichever won was pinned indefinitely.
        #
        # Measured 2026-08-28: `llama-server` had been resident for 31 hours at 4096 having
        # burned 95,241 seconds of CPU, answering nothing -- every request either timing out at
        # 90s or rejected with "maximum pending requests exceeded". Killing the runner did not
        # help: a fresh one loaded and was re-pinned at 4096 within seconds, by this call site.
        # The reload war, not the mismatch itself, is what saturated the queue -- a 6 GB model
        # being rebuilt on a loop cannot also serve.
        #
        # Two earlier diagnoses were wrong about this and both were recorded as fact: run #35
        # blamed a foreign `semsearch` client, and run #36 blamed the runner's infinite
        # keep_alive alone. The foreign client had already exited and the stall continued; the
        # keep_alive is ours. So is this. (order cf54b3ed349d)
        got = P.ask(R.config(), system, prompt, schema, timeout=300, tag="overwatch")
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
    rotation itself -- pacing, not truncation; every finding cycles through.

    ONLY A FINDING THE MODEL ACTUALLY ANSWERED FOR IS STAMPED. `f['last_verified']` and the
    `checked` count were written BEFORE `got` was tested, and `_ask` returns None ON PURPOSE
    when the GPU is busy and the round's cloud budget is spent (see "THE WATCHER YIELDS"). So a
    finding nobody looked at was recorded as JUST VERIFIED and sorted to the BACK of this
    function's own oldest-verification-first queue -- the worst place for the finding least
    recently checked -- and the round printed "N re-verified" for an N of zero. Across a busy
    stretch the entire open set could be stamped and rotated without a single verification, so
    the closer that exists to stop the open count growing quietly stopped closing while still
    reporting that it had. This is the identical defect fixed one function over for the `seen`
    stamp under order a3ee0d1d2d4c, where `review` grew a `complete` flag and `round_once` only
    stamps `seen` when it is True; `last_verified` never got the same treatment. It has it now:
    a yielded finding keeps its old timestamp, stays at the FRONT of the queue, and is counted
    and printed as yielded rather than as checked. Order c6f64c1424fa."""
    opens = sorted(((fid, f) for fid, f in led["findings"].items()
                    if f.get("state") == "open"),
                   key=lambda kv: kv[1].get("last_verified", kv[1].get("first_seen", 0)))
    checked = closed = yielded = 0
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
        if got is None:
            # THE WATCHER YIELDED on this one. Nothing looked at it, so nothing is recorded
            # about it -- no stamp, not counted as checked. Its old `last_verified` stands and
            # it stays where it belongs in the queue: at the front.
            yielded += 1
            continue
        f["last_verified"] = time.time()
        checked += 1
        verdict = got.get("verdict")
        why = str(got.get("why") or "")[:300]
        if verdict == "refuted":
            f["state"] = "closed"
            f["verdict"] = "auto-triage refuted: " + why
            f["closed_at"] = time.time()
            closed += 1
        elif verdict == "confirmed":
            f["confirmed_n"] = f.get("confirmed_n", 0) + 1
            f["last_confirm_why"] = why
    if checked or yielded:
        line = ("   auto-triage: %d open finding(s) re-verified, %d refuted and closed"
                % (checked, closed))
        if yielded:
            line += ("   (%d skipped -- the GPU was busy, not re-verified and not stamped)"
                     % yielded)
        print(line, flush=True)
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
        # EVERY ONE OF THEM, not the first four. See the note above the findings list below:
        # the same cap, and this one is a WORK LIST -- module #5 that will not import is a
        # module nobody is told about, under a count that says there are five.
        lines.append(f"- modules that will not import: **{len(broken)}**"
                     + ("" if not broken else "  — " + ", ".join(broken)))
    if struct.get("estate_error"):
        lines.append("- files that will not parse: **UNKNOWN — the artifact scan itself "
                     f"failed**  — {struct['estate_error']}")
    else:
        # THE CARRIED-FORWARD COUNT NOW SAYS HOW OLD IT IS. A shallow round copies the last deep
        # scan forward (see round_once) rather than reporting zero -- correct, but printed with
        # no indication of its age it can be several rounds stale and read as current. One field,
        # only shown when the reading did not come from this round. Found e40b786256e1.
        _dor = struct.get("deep_as_of_round")
        _age = f" (deep scan as of round {_dor})" if (_dor is not None
                                                       and _dor != led["rounds"]) else ""
        lines.append(f"- files that will not parse: **{len(corrupt)}** of "
                     f"{struct.get('files', 0):,} inspected{_age}"
                     # Uncapped for the same reason as the line above it: a file that will not
                     # parse is a file somebody has to open, and the fourth one was invisible.
                     + ("" if not corrupt else "  — " + "; ".join(corrupt)))
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
        # EVERY OPEN FINDING, RANKED -- NEVER THE FIRST FORTY. This list was sorted and then cut
        # at [:40] under a header stating the true count, which is Hard Rule 0's exact shape: the
        # ranking is kept and encouraged, the truncation is the fault. WATCH.md is the ONLY thing
        # a person reads to learn what the standing sweep found, so finding #41 was a finding
        # nobody would ever be told about. The identical cap has already been ruled a truncation
        # four times in the sibling instrument -- dashboard.py's open findings, swallowed
        # failures, breached nets and quarantined hosts -- and this is the sibling nobody
        # visited. Fixed while it was still latent (4 findings open, 288 total, round 132), which
        # is the cheap moment rather than the one where it has already hidden something.
        # (order e8e095597f74)
        for f in sorted(open_f, key=lambda x: (-(x.get("severity") == "high"),
                                               -x.get("first_seen", 0))):
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
    #
    # GATED: WATCH.md is the only thing a person reads to learn what this job found, and
    # `round_once` prints "N finding(s) open  ->  WATCH.md" immediately after this call. With
    # the verdict discarded, a denied rename left the PREVIOUS round's report on disk under
    # that announcement -- a stale round number and a stale finding list read as this round's,
    # which is the wrong-answer half of this defect rather than the merely-absent half.
    _tmp = "%s.%d.tmp" % (REPORT, os.getpid())
    with open(_tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    if not silence.replace_retry(_tmp, REPORT):
        print("overwatch: %s was NOT rewritten (replace refused) -- the file on disk is the "
              "PREVIOUS round's report, not this one's."
              % os.path.basename(REPORT), file=sys.stderr)
        return False
    return True


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
            # AGE, NOT JUST THE CARRIED NUMBER. `prev`'s round is stamped when it was cached
            # (below) so write_report can say how stale it is instead of it reading as current.
            struct.setdefault("deep_as_of_round", prev.get("round"))
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
                            "files": struct.get("files", 0),
                            "round": led["rounds"]}
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
        # THE WATCHER READS ITSELF. This was `... and m not in ("overwatch", "allsweep")`, with
        # nothing beside it saying why, while the CLI calls this job "a standing debug sweep over
        # every module" and the owner's brief in the docstring is "watches all modules for bugs".
        # The two files excluded were the watching machinery itself -- the pair whose defects
        # mean no watching happens at all, and therefore the pair whose defects nothing else in
        # the project is positioned to find. The exclusion was also inconsistent inside this very
        # file: `structure()` above import-scans both of them.
        #
        # `sweep_plan.modules()` argues the opposite position for the same reason and is right --
        # "Not even this file, and not verify_math.py because it is only tests ... if a module is
        # genuinely not worth auditing, that is an argument for deleting it, not for skipping
        # it." Nothing here executes the module it reads; reading own source costs a slice of the
        # round's budget and no more. So the exclusion is dropped rather than annotated, and the
        # code now matches the claim two docstrings make about it. (order 97373afb2d5b)
        mods = [m for m in A.modules() if not m.startswith("_")]
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
    wrote = write_report(led, struct)
    open_n = sum(1 for f in led["findings"].values() if f.get("state") == "open")
    print(f"\n{open_n} finding(s) open  ->  "
          + (REPORT if wrote else REPORT + "  (NOT UPDATED -- see stderr)"))
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
