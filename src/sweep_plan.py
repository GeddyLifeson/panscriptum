"""Partition EVERY module in `src/` into balanced audit batches, and record what got covered.

Owner ruling 2026-08-25: *"the first thing that should be done after what's immediate is a full
in-depth comprehensive sweep of every line of code across every module ... make it such that
every sweep is as in-depth and comprehensive as possible every time until nothing bad is
reported back, just that things are being waited on."*

WHY THIS FILE EXISTS AT ALL. The maintenance pass used to audit by ROTATION -- "take the top two
never-audited files" -- with the rotation state kept in prose in `NEXT_STEPS.md`. That is a cap
wearing a schedule's clothing, and it is the exact shape Hard Rule 0 forbids: it returned a
smaller universe (2 modules) in the same shape as the real one (94), it never failed, and the
handoff read like a completed audit either way. At two modules a run against 94 modules, a given
file was re-read about twice a year, so "never audited" was the normal state of most of the tree.

THE RULE THIS ENFORCES: every module, every sweep. Not a sample, not a rotation, not the biggest
N. `batches()` exists only to make that survivable inside finite agent contexts -- it splits the
work, it never drops any of it, and `missing()` is the check that proves nothing was dropped.

    python src/sweep_plan.py --batches 16     # the plan, as JSON
    python src/sweep_plan.py --coverage       # what the last sweep actually covered
"""

import argparse
import glob
import json
import os
import threading
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "src")
COVERAGE = os.path.join(HERE, "state", "SWEEP_COVERAGE.json")
SHARDS = os.path.join(HERE, "state", "sweep_shards")


def modules():
    """Every module in src/, newest-largest first. NO exclusions, deliberately.

    Not even this file, and not `verify_math.py` because it is "only tests" -- a check that is
    wrong is worse than a missing one, since it reports green forever. If a module is genuinely
    not worth auditing, that is an argument for deleting it, not for skipping it.
    """
    out = []
    for p in sorted(glob.glob(os.path.join(SRC, "*.py"))):
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                n = sum(1 for _ in f)
        except Exception:
            # NOT a zero-line module. An unreadable file used to fall through to `n = 0` with
            # no note, which sorts it last, packs it into a bin as free weight, and reads in
            # the plan exactly like an empty stub -- a file silently dropped out of a sweep
            # whose entire purpose is that nothing is dropped. Recorded, and marked so the
            # plan itself carries the fault. (Found by the sweep auditing this very file,
            # hours after it was written. 2026-08-25.)
            try:
                import silence
                silence.note("sweep_plan.py:module-lines")
            except Exception:
                pass
            out.append({"module": os.path.basename(p), "lines": 0, "unreadable": True})
            continue
        out.append({"module": os.path.basename(p), "lines": n})
    return sorted(out, key=lambda m: -m["lines"])


def batches(n=16):
    """Greedy longest-first bin packing into `n` roughly equal-line batches.

    Longest-first matters: dropping the 3,459-line file into whichever bin is emptiest at the
    end produces one batch nobody can actually read. Packed largest-first, the spread across
    bins stays tight enough that every agent gets a context it can hold.
    """
    n = max(1, int(n))
    bins = [{"batch": i + 1, "lines": 0, "modules": []} for i in range(n)]
    for m in modules():
        b = min(bins, key=lambda b: b["lines"])
        b["modules"].append(m["module"])
        b["lines"] += m["lines"]
    return [b for b in bins if b["modules"]]


_RECORD_LOCK = threading.Lock()


def _shard_path(run, batch):
    """A filename no other writer can collide with: run + batch + pid.

    The batch id alone is not enough — an agent that is retried, or a batch re-run by hand,
    would land on the same name as its predecessor mid-write.
    """
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in "%s.%s" % (run, batch))
    return os.path.join(SHARDS, "%s.%d.json" % (safe, os.getpid()))


def _read_shards():
    """Every shard on disk, merged newest-wins. Unreadable shards are NOTED, never skipped
    in silence — a shard that will not parse is a batch whose coverage we cannot prove."""
    out = {}
    try:
        paths = sorted(glob.glob(os.path.join(SHARDS, "*.json")))
    except Exception:
        return out
    for p in paths:
        try:
            with open(p, encoding="utf-8") as f:
                rec = json.load(f)
        except Exception:
            try:
                import silence
                silence.note("sweep_plan.py:shard-unreadable")
            except Exception:
                pass
            continue
        run = rec.get("run")
        at = rec.get("at") or 0
        for m in (rec.get("modules") or []):
            prev = out.get(m)
            if prev is None or (at or 0) >= (prev.get("at") or 0):
                out[m] = {"run": run, "at": at}
    return out


def record(run, covered, batch=None):
    """Stamp which modules a sweep actually read. `covered` is an iterable of basenames.

    WRITTEN AS A PER-BATCH SHARD, because the whole point of this file is that sixteen batches
    run AT ONCE — and, since run #28, each one in ITS OWN PROCESS. The first version did an
    unguarded read-modify-write and lost the loser's modules; the second serialised it behind a
    `threading.Lock`, which is the right lock for the wrong topology: a threading lock is not
    held across processes, so sixteen subagents each running `python -c "sweep_plan.record(...)"`
    contend exactly as if there were no lock at all. Two of them interleaving read-modify-write
    still drops one batch's modules, and `missing()` would then report a gap that never
    happened — or, if the survivor happened to be the fuller file, hide one that did.

    So there is no shared mutable file on the write path any more. Each caller writes its OWN
    file, named for its run/batch/pid, and `missing()` merges them at read time. Concurrent
    writers cannot collide because they never touch the same path. The lock is kept only for
    the best-effort fold into the aggregate `SWEEP_COVERAGE.json`, which is now a CONVENIENCE
    VIEW for `--coverage` — nothing draws a conclusion from it that the shards do not support.
    (Race found by the sweep auditing this very file; topology bug found the run after, by the
    sweep auditing it again. 2026-08-25.)
    """
    covered = list(covered)
    now = time.time()
    try:
        os.makedirs(SHARDS, exist_ok=True)
        p = _shard_path(run, batch if batch is not None else "x")
        tmp = "%s.tmp" % p
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"run": run, "batch": batch, "at": now, "modules": covered}, f, indent=1)
        os.replace(tmp, p)
    except Exception:
        try:
            import silence
            silence.note("sweep_plan.py:shard-write")
        except Exception:
            pass
    with _RECORD_LOCK:
        data = _read_shards()
        try:
            with open(COVERAGE, encoding="utf-8") as f:
                old = json.load(f)
            if isinstance(old, dict):
                for m, r in old.items():
                    data.setdefault(m, r)
        except Exception:
            pass
        try:
            import silence
            silence.write_json(COVERAGE, data, indent=1, sort_keys=True)
        except Exception:
            tmp = "%s.%d.tmp" % (COVERAGE, os.getpid())
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=1, sort_keys=True)
            os.replace(tmp, COVERAGE)
        return data


def coverage_map():
    """The authoritative view: shards first, the aggregate file only where a shard is absent.

    NEWEST-WINS, because this answers "when was module X last audited, and by which run?" --
    a question with exactly one right answer. It is the wrong instrument for `missing()`; see
    there.
    """
    data = _read_shards()
    try:
        with open(COVERAGE, encoding="utf-8") as f:
            old = json.load(f)
        if isinstance(old, dict):
            for m, r in old.items():
                if isinstance(r, dict):
                    data.setdefault(m, r)
    except Exception:
        pass
    return data


def covered_by(run):
    """The set of modules ANY shard records `run` as having read.

    Deliberately NOT derived from `coverage_map()`. That map is newest-wins across all runs, so
    asking it "did run29 cover X?" really asks "was run29 the LAST run to cover X?" -- a
    different question with a different answer the moment a second run records the same module
    with a later stamp. Shards are never pruned, so those two questions diverge permanently,
    and the divergence is invisible: `missing()` would name a module the agent demonstrably
    read, and the sweep's completeness proof would report a gap that did not happen.

    A membership question deserves a membership answer. (Found by the sweep auditing this very
    file, in the same run that introduced the shards. 2026-08-25, run #29, batch 08.)
    """
    want = str(run)
    out = set()
    try:
        paths = sorted(glob.glob(os.path.join(SHARDS, "*.json")))
    except Exception:
        paths = []
    for p in paths:
        try:
            with open(p, encoding="utf-8") as f:
                rec = json.load(f)
        except Exception:
            try:
                import silence
                silence.note("sweep_plan.py:shard-unreadable")
            except Exception:
                pass
            continue
        if str(rec.get("run")) == want:
            for m in (rec.get("modules") or []):
                out.add(m)
    # The aggregate file is a fallback for a coverage record written before shards existed.
    try:
        with open(COVERAGE, encoding="utf-8") as f:
            old = json.load(f)
        if isinstance(old, dict):
            for m, r in old.items():
                if isinstance(r, dict) and str(r.get("run")) == want:
                    out.add(m)
    except Exception:
        pass
    return out


def latest_run():
    """The run label of the most recently written shard, or None if nothing has ever swept.

    THE COMPLETENESS CHECK MUST NOT NAME A RUN IN A LITERAL. `verify_math`'s "the live sweep
    proves its own completeness" asked `missing("run29")`, hardcoded -- so from run #30 onward
    it was answering a question about a sweep that had already finished, and no later sweep,
    however complete or however skipped, could move it. It is the THIRD spelling of the same
    defect in three consecutive runs: #28 found `record()` losing an update, #29 found
    `missing()` asking "was run N the LAST to read X?" instead of "did run N read X?", and this
    is #31's -- the instrument frozen on a past run. Lesson 25 keeps being right: the sweep
    audits the sweep, and that is where the best finding keeps being.

    Returns None rather than a guess when there is no evidence, so the caller can FAIL CLOSED
    instead of proving the completeness of a sweep that never happened.
    """
    newest = None
    try:
        paths = glob.glob(os.path.join(SHARDS, "*.json"))
    except Exception:
        paths = []
    for p in paths:
        try:
            with open(p, encoding="utf-8") as f:
                rec = json.load(f)
        except Exception:
            try:
                import silence
                silence.note("sweep_plan.py:shard-unreadable")
            except Exception:
                pass
            continue
        at = rec.get("at")
        run = rec.get("run")
        if run is None or not isinstance(at, (int, float)):
            continue
        if newest is None or at > newest[0]:
            newest = (at, str(run))
    return newest[1] if newest else None


def missing(run):
    """Modules NOT covered by `run` — the proof that a sweep was complete, or the list of what
    it silently skipped. A sweep that cannot answer this is a sweep nobody can trust."""
    seen = covered_by(run)
    return [m["module"] for m in modules() if m["module"] not in seen]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--batches", type=int, default=0, help="emit N balanced batches as JSON")
    ap.add_argument("--coverage", action="store_true", help="show the last recorded coverage")
    ap.add_argument("--missing", help="list modules not covered by the given run id")
    a = ap.parse_args()
    if a.batches:
        plan = batches(a.batches)
        print(json.dumps(plan, indent=1))
        print("# %d modules, %d lines, %d batches"
              % (sum(len(b["modules"]) for b in plan),
                 sum(b["lines"] for b in plan), len(plan)))
    elif a.missing:
        miss = missing(a.missing)
        print("\n".join(miss) if miss else "nothing missing -- the sweep was complete")
    elif a.coverage:
        try:
            with open(COVERAGE, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        runs = {}
        for m, r in data.items():
            runs.setdefault(str(r.get("run")), []).append(m)
        for r, ms in sorted(runs.items()):
            print("%-28s %d module(s)" % (r, len(ms)))
        print("%d module(s) in src/ total" % len(modules()))
    else:
        ms = modules()
        print("%d modules, %d lines" % (len(ms), sum(m["lines"] for m in ms)))


if __name__ == "__main__":
    main()
