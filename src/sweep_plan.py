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


def record(run, covered):
    """Stamp which modules a sweep actually read. `covered` is an iterable of basenames.

    SERIALISED, because the whole point of this file is that sixteen batches run AT ONCE and
    each one reports its own coverage. The first version did an unguarded read-modify-write:
    two batches reading the same file, each adding its own modules, each writing back its own
    copy -- and the loser's modules vanish from the record. That would make `missing()` report
    a gap that never happened, or worse, hide one that did. The lock covers this process; the
    atomic land covers a torn read. (Found by the sweep auditing this very file. 2026-08-25.)
    """
    with _RECORD_LOCK:
        try:
            with open(COVERAGE, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}
        now = time.time()
        for m in covered:
            data[m] = {"run": run, "at": now}
        try:
            import silence
            silence.write_json(COVERAGE, data, indent=1, sort_keys=True)
        except Exception:
            tmp = "%s.%d.tmp" % (COVERAGE, os.getpid())
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=1, sort_keys=True)
            os.replace(tmp, COVERAGE)
        return data


def missing(run):
    """Modules NOT covered by `run` — the proof that a sweep was complete, or the list of what
    it silently skipped. A sweep that cannot answer this is a sweep nobody can trust."""
    try:
        with open(COVERAGE, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    return [m["module"] for m in modules()
            if str((data.get(m["module"]) or {}).get("run")) != str(run)]


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
