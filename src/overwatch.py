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
    try:
        with open(LEDGER, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        silence.note("overwatch.py:load")
        return {"findings": {}, "seen": {}, "rounds": 0}


def save(d):
    try:
        os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
        tmp = LEDGER + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1, sort_keys=True)
        # replace_retry, not a bare os.replace: the dashboard and the standards board both read
        # this file on their own clocks, and on Windows a rename is DENIED while a reader holds
        # the target -- which here would throw away the whole round's findings.
        silence.replace_retry(tmp, LEDGER)
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
        silence.note("overwatch.py:193")
        out["error"] = f"{type(e).__name__}: {str(e)[:90]}"
    if not deep:
        return out
    try:
        import estate as E
        art = E.artifacts(workers=8)
        out["corrupt_files"] = [r["path"] + " — " + r["error"] for r in art["bad"]]
        out["files"] = art["total"]
    except Exception as e:
        silence.note("overwatch.py:202")
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


def _anchored(module, finding, src):
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


def review(module, local=True, ledger=None):
    """Read one module and return the findings that survive all three filters."""
    path = os.path.join(SRC, module + ".py")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        src = f.read()
    kept = []
    for start, end, chunk in _slices(path):
        got = _ask(SYSTEM, f"MODULE: {module}.py   LINES {start}-{end}\n\n{chunk}",
                   SCHEMA, local=local)
        for f_ in (got or {}).get("findings", []):
            if (f_.get("severity") or "medium").lower() not in ("high", "medium"):
                continue
            if not _anchored(module, f_, src):
                continue
            f_["module"] = module
            f_["lines"] = [start, end]
            kept.append(f_)
    return kept


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
        region = chr(10).join("%d: %s" % (i, l)
                              for i, l in enumerate(lines[a:b], a + 1))
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
    lines.append(f"- modules that will not import: **{len(broken)}**"
                 + ("" if not broken else "  — " + ", ".join(broken[:4])))
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
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


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
        prev = led.get("last_deep") or {}
        struct.setdefault("corrupt_files", prev.get("corrupt_files", []))
        struct.setdefault("files", prev.get("files", 0))
    else:
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
                found = review(m, local=local, ledger=led)
            except Exception as e:
                silence.note("overwatch.py:review")
                print(f"   {m}: review failed ({type(e).__name__})", flush=True)
                continue
            d = _digest(os.path.join(SRC, m + ".py"))
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
            print(f"   {m:<24}{len(found):>3} raw  {fresh:>3} new   {time.time()-t:>5.0f}s"
                  + note, flush=True)

    save(led)
    write_report(led, struct)
    open_n = sum(1 for f in led["findings"].values() if f.get("state") == "open")
    print(f"\n{open_n} finding(s) open  ->  {REPORT}")
    return open_n


def main():
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

    while True:
        print("=" * 88)
        print(f"OVERWATCH  {time.strftime('%H:%M:%S')}")
        print("=" * 88)
        round_once(limit=a.modules, local=not a.cloud, skip_model=a.structure_only)
        if not a.loop:
            return 0
        time.sleep(a.loop * 60)


if __name__ == "__main__":
    sys.exit(main())
