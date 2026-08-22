#!/usr/bin/env python3
"""
FOREMAN — reads the work orders and actually does something about them.

THE OWNER'S BRIEF
-----------------
    "shouldn't there be something developed that reads the work orders and sends them to either
     you or the ollama model for fixing? cause rn it's just giving the list but nothing is being
     done about it"

Correct, and it is the obvious next thing. `standards` measures against declared floors and emits
a work order; `overwatch` reads the source and reports defects of fact. Both produce excellent
lists that sit there. A list nobody acts on is a slightly more organised version of the problem
this project keeps having -- a number nobody was looking at.

THREE LANES, AND THE SORTING IS THE WHOLE DESIGN
------------------------------------------------
Not every breach can be fixed the same way, and pretending otherwise is how an automatic repairer
becomes a hazard.

  AUTO      A remedy that is mechanical, deterministic, and reversible. Clearing a mis-learned
            rate cap, re-proving which buckets answer, re-running host adoption, refreshing a
            stale coverage measurement. Every one of these I have run by hand today, more than
            once, with no judgement involved. They are scripted here exactly as performed.

  MODEL     A defect of fact in the source: the code does something other than what it says.
            This needs reading and reasoning, which is what a model is for -- and it needs
            guarding, which is most of the code below.

  OWNER     Anything requiring a decision that is not mine to make. "The free tiers are spent,
            add providers" is not a bug to be fixed, it is a choice about money and accounts.
            "This roster looks like another fiction" needs somebody to read the roster. These
            queue into a file rather than being acted on.

WHY THE MODEL LANE IS FENCED THIS HARD
--------------------------------------
A model editing a live codebase unsupervised is a bad idea, and the reasons are not hypothetical
in this project: the same defect class that produced eighteen silent faults would produce silent
patches. So a proposed patch must clear every one of these before it is kept:

    one file, and not one on the denylist
    it parses
    it changes fewer than MAX_PATCH_LINES lines
    `python -c "import <module>"` still succeeds
    `verify_math.py` still reports 0 failures
    `allsweep.py --quick` reports no new broken module

Anything that fails, reverts. The backup is written before the patch and restored on any failure,
including an exception in the checking itself. The bar is deliberately higher than a human's,
because a human explains a change and a model does not.
"""
import argparse
import json
import os
import shutil
import subprocess
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

PY = sys.executable
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
LOG = os.path.join(HERE, "data", "FOREMAN.json")
FOR_OWNER = os.path.join(HERE, "FOR_OWNER.md")
BACKUPS = os.path.join(HERE, "state", "foreman_backups")

# Files a model may never edit. Each is either the thing that would have to be working to detect
# a bad patch, or the thing doing the patching.
DENYLIST = {"foreman", "silence", "health", "allsweep", "estate", "standards", "verify_math"}
MAX_PATCH_LINES = 40


def _run(args, timeout=900):
    return subprocess.run([PY] + args, capture_output=True, text=True, timeout=timeout,
                          env=ENV, cwd=HERE, encoding="utf-8", errors="replace")


# =========================================================================== the AUTO lane
#
# Each remedy returns (did_something, what_happened). They are written to be safe to run when
# they are not needed -- an idempotent remedy can be attempted on a hunch, and a destructive one
# cannot.

def clear_learned_caps():
    """Drop per-minute caps of 1, which are never real.

    A 429 arriving after a quiet minute teaches `rpm: 1`, and until the router was fixed nothing
    ever raised a learned cap again. Six buckets sat pinned that way -- both Geminis, Gemini
    Lite, both Groq models and zai -- against documented caps of 10, 10 and 15. The router now
    floors the learned value at 2 and expires it after six hours, so a fresh occurrence means
    something is generating 429 storms; this clears the damage either way.
    """
    n = 0
    for db in (os.path.join(HERE, "state", "cascade_scratch.db"),
               os.path.join(os.path.expanduser("~"), "cascade", "data.db")):
        if not os.path.exists(db):
            continue
        try:
            c = sqlite3.connect(db)
            n += c.execute("update bucket_state set learned=NULL "
                           "where learned like '%\"rpm\": 1%' or learned like '%\"rpm\":1%'"
                           ).rowcount
            c.commit()
        except Exception:
            silence.note("foreman.py:clear_learned_caps")
    return bool(n), f"cleared {n} bucket(s) pinned at one request per minute"


def reprove_pool():
    """Re-measure which buckets actually answer.

    Headroom is not evidence. Twenty-five of thirty-six buckets reported healthy quota while
    answering nothing, and each burned a full deadline every time it was claimed. This is the
    measurement that turns the pool's nominal width into its real one.
    """
    try:
        import cascade_bridge as CB
        rows = CB.prove()
        ok = [r for r in rows if r.get("verdict") == "answers"]
        with open(os.path.join(HERE, "data", "POOL_PROOF.json"), "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=1)
        CB._PROVEN[0] = None                      # force the next _alive() to re-read
        return True, f"{len(ok)} of {len(rows)} buckets answer"
    except Exception as e:
        silence.note("foreman.py:reprove_pool")
        return False, f"{type(e).__name__}: {str(e)[:80]}"


def adopt_hosts():
    """Find a wiki for sources that have none. Entries with no host are uncitable forever."""
    r = _run([os.path.join(SRC, "hostcheck.py"), "--adopt", "--go", "--workers", "3"],
             timeout=1800)
    tail = [ln for ln in (r.stdout or "").splitlines() if "adopted" in ln]
    return bool(tail), (tail[-1] if tail else "no adoption line in output")


def scout_hostless():
    """Ask the model where the sources with no host publish, and verify every answer.

    This was the last step that needed a person: knowing that KibblesTasty's material is at
    kthomebrew.com in the first place. `scout` asks the model and then PROVES each URL by
    fetching it and checking the page contains this source's own catalogued names -- a
    hallucinated URL 404s, a real URL about something else contains none of them. Nothing is
    registered on the model's say-so.
    """
    try:
        import scout as SC
        res = SC.sweep(limit=4)
        found = sum(1 for r in res if r.get("kept"))
        return bool(found), f"{found} of {len(res)} sources given somewhere to read from"
    except Exception as e:
        silence.note("foreman.py:scout_hostless")
        return False, f"{type(e).__name__}: {str(e)[:80]}"


def rerun_roll():
    """The page roll has not finished its pass. It is network-bound, so a stall is a host
    problem rather than a quota one -- and the supervisor restarts it next cycle anyway. This
    reports rather than acts, because two rolls at once is the failure the supervisor exists to
    prevent."""
    try:
        import overnight as ON
        if ON.running("feats.py"):
            return True, "roll is running; it will finish its pass"
    except Exception:
        silence.note("foreman.py:rerun_roll")
    return False, "roll is not running -- the supervisor starts it next cycle"


def triage_swallowed():
    """A spike in swallowed failures means something upstream is failing and being tolerated.

    The remedy is not to clear the ledger -- that would be deleting the evidence. It is to name
    the top classes, because the class names the module and the line, and a class that is 90% of
    the total is a single fault wearing thousands of hats.
    """
    path = os.path.join(HERE, "state", "failures.json")
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        silence.note("foreman.py:triage_swallowed")
        return False, "no ledger"
    if not d:
        return False, "ledger empty"
    top = sorted(d.items(), key=lambda kv: -kv[1])[:3]
    total = sum(d.values())
    share = top[0][1] / max(total, 1)
    detail = "; ".join(f"{k} x{v:,}" for k, v in top)
    # A single class dominating is a finding worth escalating rather than tolerating.
    return share < 0.5, f"{total:,} swallowed, top: {detail}"


def refresh_coverage():
    """Re-measure cited/settled. Stale figures understate the library and mislead every other
    standard that reads them."""
    r = _run([os.path.join(SRC, "coverage.py")], timeout=1800)
    return r.returncode == 0, "coverage recomputed" if r.returncode == 0 else "coverage failed"


def restart_reader():
    """The reader is not progressing. Restarting is safe: every entity is cached only when it was
    fully read, so nothing is lost and nothing is re-read that was finished."""
    try:
        import overnight as ON
        if ON.running("read.py"):
            return False, "reader is running; not touching it"
    except Exception:
        silence.note("foreman.py:restart_reader")
    return False, "reader is not running -- the supervisor starts it next cycle"


# standard name -> remedies to try, in order. A standard with no entry falls to the OWNER lane,
# which is the right default: acting on a breach nobody scripted a remedy for is guessing.
REMEDIES = {
    "no bucket pinned at rpm 1": [clear_learned_caps],
    "calls that succeed": [clear_learned_caps, reprove_pool],
    "model calls per hour": [clear_learned_caps, reprove_pool],
    "buckets with headroom": [reprove_pool],
    "coverage figures are current": [refresh_coverage],
    "corpus read is progressing": [restart_reader],
    "sources with a reachable wiki": [adopt_hosts, scout_hostless],
    "page roll complete": [rerun_roll],
    "swallowed failures not spiking": [triage_swallowed],
    # Both of these are the throughput standard wearing a different name: a passage nobody
    # answered and a read that will not finish are what a starved pool looks like from the
    # reader's side. Same diagnosis, same remedies -- and routing them to the owner instead
    # would put a capacity problem in a file meant for decisions about money.
    "chunks nobody answered": [clear_learned_caps, reprove_pool],
    "corpus read finishes inside a day": [clear_learned_caps, reprove_pool],
}


# =========================================================================== the MODEL lane

PATCH_SYSTEM = """You are given one Python function and a specific claim that it does something
other than what it says. Return a corrected version of THAT FUNCTION ONLY.

Rules:
- Return the complete function, from its `def` line to its last line, and nothing else.
- Change as little as possible. If the claim is wrong, return the function UNCHANGED.
- Preserve every comment and docstring unless the claim is about one of them.
- Do not add imports, do not rename anything, do not reformat.
- Indentation must match the original exactly.

Return JSON only:
{"verdict": "fix"|"claim is wrong", "function": "<the complete function source>"}"""

PATCH_SCHEMA = {
    "type": "object",
    "properties": {"verdict": {"type": "string"}, "function": {"type": "string"}},
    "required": ["verdict", "function"],
}


def _function_source(path, symbol):
    """The source of one top-level function or method, with its line span."""
    import ast as _ast
    with open(path, encoding="utf-8") as f:
        src = f.read()
    tree = _ast.parse(src)
    want = symbol.split("(")[0].split(".")[-1].strip()
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)) and node.name == want:
            lines = src.splitlines(keepends=True)
            start = node.lineno - 1
            end = getattr(node, "end_lineno", node.lineno)
            return "".join(lines[start:end]), start, end
    return None, None, None


def _checks_pass(module):
    """Everything that must still be true after a patch.

    Deliberately more than "it parses". A patch that parses and breaks an import is exactly the
    kind of silent damage this project spends its life catching.
    """
    r = _run(["-c", f"import sys; sys.path.insert(0, r'{SRC}'); import {module}"], timeout=300)
    if r.returncode != 0:
        return False, "module no longer imports"
    r = _run([os.path.join(SRC, "verify_math.py")], timeout=1200)
    if "0 FAILED" not in (r.stdout or ""):
        return False, "verify_math no longer passes"
    r = _run([os.path.join(SRC, "allsweep.py"), "--quick"], timeout=900)
    if "BROKEN" in (r.stdout or ""):
        return False, "allsweep reports a broken module"
    return True, "checks pass"


def attempt_patch(finding, dry=True):
    """Have the model repair one finding, then prove the repair or revert it."""
    module = finding.get("module")
    symbol = finding.get("symbol") or ""
    if not module or module in DENYLIST:
        return {"ok": False, "why": f"{module} is on the denylist"}
    path = os.path.join(SRC, module + ".py")
    if not os.path.exists(path):
        return {"ok": False, "why": "no such module"}

    body, start, end = _function_source(path, symbol)
    if not body:
        # NOT EVERY FINDING POINTS AT PYTHON. `build_terminal.place` is JavaScript inside a
        # template string and `assay.SIGMA_MAX` is a module constant -- both are real code and
        # neither is a function this can replace. Retiring rather than refusing forever: an
        # unactionable finding that stays open is a permanent breach of the standard that reads
        # it, which trains everybody to ignore that standard.
        return {"ok": False, "why": f"{symbol} is not a Python function here", "retire": True}
    if len(body.splitlines()) > 400:
        return {"ok": False, "why": "function too large to patch safely"}

    prompt = (f"MODULE: {module}.py\nSYMBOL: {symbol}\n"
              f"CLAIM: the code {finding.get('actual', '')}\n"
              f"IT SAYS: {finding.get('claim', '')}\n\nFUNCTION:\n{body}")
    try:
        import read as R
        R.ensure_transport(verbose=False)
        got = R._ask(R.config(), PATCH_SYSTEM, prompt, PATCH_SCHEMA)
    except Exception as e:
        silence.note("foreman.py:attempt_patch-ask")
        return {"ok": False, "why": f"model unreachable: {type(e).__name__}"}
    if not got:
        return {"ok": False, "why": "no answer from the model"}
    if got.get("verdict") != "fix":
        return {"ok": False, "why": "model says the claim is wrong", "retire": True}

    new = (got.get("function") or "").rstrip() + "\n"
    if not new.lstrip().startswith("def ") and not new.lstrip().startswith("async def"):
        return {"ok": False, "why": "reply is not a function"}
    delta = abs(len(new.splitlines()) - len(body.splitlines()))
    if delta > MAX_PATCH_LINES:
        return {"ok": False, "why": f"patch changes {delta} lines; cap is {MAX_PATCH_LINES}"}
    if new.strip() == body.strip():
        return {"ok": False, "why": "no change proposed", "retire": True}
    if dry:
        return {"ok": True, "why": "would patch", "delta": delta, "preview": new[:400]}

    os.makedirs(BACKUPS, exist_ok=True)
    backup = os.path.join(BACKUPS, f"{module}.{int(time.time())}.py")
    shutil.copy2(path, backup)
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        lines[start:end] = [new]
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        good, why = _checks_pass(module)
        if not good:
            shutil.copy2(backup, path)
            return {"ok": False, "why": f"reverted: {why}", "backup": backup}
        return {"ok": True, "why": "patched and verified", "delta": delta, "backup": backup}
    except Exception as e:
        silence.note("foreman.py:attempt_patch-apply")
        try:
            shutil.copy2(backup, path)
        except Exception:
            silence.note("foreman.py:attempt_patch-revert")
        return {"ok": False, "why": f"reverted after {type(e).__name__}"}


# =========================================================================== the round

def _retire(finding):
    """Close a finding the model lane can never act on, so it stops blocking its standard."""
    path = os.path.join(HERE, "data", "OVERWATCH.json")
    try:
        with open(path, encoding="utf-8") as f:
            led = json.load(f)
        for fid, v in (led.get("findings") or {}).items():
            if (v.get("module") == finding.get("module")
                    and v.get("symbol") == finding.get("symbol")
                    and v.get("state") == "open"):
                v["state"] = "retired"
                v["retired_why"] = finding.get("why", "unactionable")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(led, f, indent=1, sort_keys=True)
    except Exception:
        silence.note("foreman.py:_retire")


def _pool_has_room(floor=600):
    """Is there spare provider capacity, or is the corpus read starving?

    Reading the library is the work. Repairing the code is what protects the work, and the
    watcher, the publisher and this all draw on the same few hundred calls an hour the free tiers
    allow. Four of my own processes competing for one thin pool is a self-inflicted outage, and
    the reader is the one that must not lose.

    A patch attempt costs several calls and the finding will still be there in half an hour.
    """
    try:
        import dashboard as D
        return (D.throughput(10) or {}).get("per_hour", 0) >= floor
    except Exception:
        silence.note("foreman.py:pool_has_room")
        return False


def owner_queue(items):
    """Everything nobody but the owner can decide, in one file they can read in ten seconds."""
    lines = ["# FOR THE OWNER", "",
             f"*Written by `src/foreman.py` — {time.strftime('%Y-%m-%d %H:%M')}*", "",
             "These need a decision, not a fix. Everything mechanical has already been done.",
             ""]
    for it in items:
        lines.append(f"### {it['standard']}")
        lines.append("")
        lines.append(f"- observed **{it['observed']}**, floor **{it['floor']}**")
        lines.append(f"- {it['order']}")
        lines.append("")
    if len(lines) <= 6:
        lines.append("Nothing outstanding.")
    with open(FOR_OWNER, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return FOR_OWNER


def round_once(dry=True, patch=False):
    import standards as ST
    log = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "auto": [], "model": [], "owner": []}

    orders = ST.work_orders()
    print(f"{len(orders)} work order(s) open")

    # A code finding is not the owner's problem; it is the model lane's, by definition. Routing
    # it to the owner queue would put "some function does not do what it says" in a file meant
    # for decisions about money and accounts, and the two need different readers.
    MODEL_LANE = {"no high-severity findings open"}

    for o in orders:
        if o["standard"] in MODEL_LANE:
            log["model_pending"] = log.get("model_pending", []) + [o["standard"]]
            print(f"   MODEL  {o['standard']}: {o['observed']} open "
                  f"-> run with --patch to attempt repairs")
            continue
        remedies = REMEDIES.get(o["standard"])
        if not remedies:
            log["owner"].append(o["standard"])
            print(f"   OWNER  {o['standard']}: {o['observed']} (floor {o['floor']})")
            continue
        for fn in remedies:
            if dry:
                print(f"   AUTO   {o['standard']} -> would run {fn.__name__}")
                log["auto"].append({"standard": o["standard"], "remedy": fn.__name__,
                                    "dry": True})
                continue
            did, what = fn()
            print(f"   AUTO   {o['standard']} -> {fn.__name__}: {what}")
            log["auto"].append({"standard": o["standard"], "remedy": fn.__name__,
                                "did": did, "result": what})
            if did:
                break

    if patch and not _pool_has_room():
        print("   MODEL  skipped: the pool is below the floor and the corpus read needs it")
    if patch and _pool_has_room():
        try:
            led = json.load(open(os.path.join(HERE, "data", "OVERWATCH.json"), encoding="utf-8"))
            open_f = [f for f in (led.get("findings") or {}).values()
                      if f.get("state") == "open"]
        except Exception:
            silence.note("foreman.py:round-findings")
            open_f = []
        for f in sorted(open_f, key=lambda x: -(x.get("severity") == "high"))[:3]:
            res = attempt_patch(f, dry=dry)
            print(f"   MODEL  {f.get('module')}.{f.get('symbol')}: {res.get('why')}")
            log["model"].append({"module": f.get("module"), "symbol": f.get("symbol"), **res})
            if res.get("retire") and not dry:
                _retire(f)

    owner_items = [o for o in orders if o["standard"] in log["owner"]]
    p = owner_queue(owner_items)
    print(f"\n{len(owner_items)} for the owner -> {p}")

    try:
        prev = json.load(open(LOG, encoding="utf-8")) if os.path.exists(LOG) else []
    except Exception:
        prev = []
    prev.append(log)
    with open(LOG, "w", encoding="utf-8") as f:
        json.dump(prev[-200:], f, indent=1)
    return log


def main():
    ap = argparse.ArgumentParser(description="read the work orders and act on them")
    ap.add_argument("--go", action="store_true", help="actually run the remedies")
    ap.add_argument("--patch", action="store_true",
                    help="also let the model attempt code repairs (guarded, auto-reverting)")
    ap.add_argument("--loop", type=float, default=0, help="keep going, minutes apart")
    a = ap.parse_args()
    while True:
        print("=" * 88)
        print(f"FOREMAN  {time.strftime('%H:%M:%S')}" + ("" if a.go else "   (dry run)"))
        print("=" * 88)
        round_once(dry=not a.go, patch=a.patch)
        if not a.loop:
            return 0
        time.sleep(a.loop * 60)


if __name__ == "__main__":
    sys.exit(main())
