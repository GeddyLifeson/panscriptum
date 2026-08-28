"""Partition the LOCAL rung for Claude agents, AROUND the modules still being edited.

The LOCAL rung is meant for the free local model. It was measured closed again this shift -- a
single small, well-specified task returned nothing in 300 seconds (rc=124) against an Ollama
runner that has burned 24 hours of CPU and rejects requests with "maximum pending requests
exceeded". So this rung escalates to Claude agents, deliberately and once, rather than being
discovered order by order.

The constraint that makes this non-trivial: three RUN agents are still working, and each owns a
set of modules outright. An order naming one of those modules must WAIT, not be handed to a
second writer -- concurrent edits to one file is how this project loses fixes.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "handoff"))
from partition_orders import SEV_ORDER, module_of  # noqa: E402

OPEN = os.path.join(ROOT, "state", "workorders.json")

# Owned by RUN batches still in flight at the time this run dispatched LOCAL.
BUSY = {
    "backfill.py", "endpoint.py", "pipeline.py", "policy.py", "verify_math.py",
    "catalogue_web.py", "dashboard.py", "drill.py", "publish.py", "render.py", "resync_roll.py",
    "allsweep.py", "entity_match.py", "estate.py", "runguard.py", "standards.py",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bins", type=int, default=6)
    a = ap.parse_args()

    with open(OPEN, encoding="utf-8") as fh:
        orders = json.load(fh)
    mine = [o for o in orders.values() if o.get("handler") == "LOCAL"]

    ready, deferred = [], []
    for o in mine:
        (deferred if module_of(o) in BUSY else ready).append(o)

    groups = {}
    for o in ready:
        groups.setdefault(module_of(o) or ("~solo:" + o["id"]), []).append(o)
    bins = [[] for _ in range(a.bins)]
    for _mod, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        min(bins, key=len).extend(items)

    payload = []
    for i, b in enumerate(bins, 1):
        b.sort(key=lambda o: (SEV_ORDER.get(o.get("severity"), 9), o.get("first_seen", 0)))
        mods = sorted({module_of(o) for o in b if module_of(o)})
        payload.append({"batch": i, "ids": [o["id"] for o in b], "modules": mods, "orders": b})
        print("L%d: %2d orders | %s" % (i, len(b), ", ".join(mods) or "(none)"))

    out = os.path.join(ROOT, "handoff", "queue", "LOCAL_batches.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    dpath = os.path.join(ROOT, "handoff", "queue", "LOCAL_deferred.json")
    with open(dpath, "w", encoding="utf-8") as fh:
        json.dump(deferred, fh, indent=2)
    print("\nready now: %d in %d bins -> %s" % (len(ready), a.bins, out))
    print("deferred (module busy): %d -> %s" % (len(deferred), dpath))
    print("  deferred modules:", ", ".join(sorted({module_of(o) for o in deferred})))
    return 0


if __name__ == "__main__":
    sys.exit(main())
