"""Dump the open work orders, grouped by handler rung, as one markdown file per rung.

Written for the daily maintenance run's dispatch step: an agent given a fixing assignment needs
the FULL text of an order, not the console's one-line-per-order digest, and the console digest
is truncated by design. No cap, no sampling -- Hard Rule 0 applies to this run's own queue.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPEN = os.path.join(ROOT, "state", "workorders.json")
OUT = os.path.join(ROOT, "handoff", "queue")

SEV_ORDER = {"BLOCKING": 0, "MAJOR": 1, "MINOR": 2, "INFO": 3}


def main():
    with open(OPEN, encoding="utf-8") as fh:
        orders = json.load(fh)
    os.makedirs(OUT, exist_ok=True)
    rungs = {}
    for oid, o in orders.items():
        rungs.setdefault(o.get("handler", "?"), []).append(o)
    for rung, items in sorted(rungs.items()):
        items.sort(key=lambda o: (SEV_ORDER.get(o.get("severity"), 9), o.get("first_seen", 0)))
        path = os.path.join(OUT, "%s.md" % rung)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("# %s rung -- %d open orders\n\n" % (rung, len(items)))
            for o in items:
                fh.write("## %s  [%s]  %s\n\n" % (o["id"], o.get("severity"), o.get("code", "")))
                fh.write("- **where**: %s\n" % o.get("where", ""))
                fh.write("- **found_by**: %s\n" % o.get("found_by", ""))
                fh.write("- **seen**: %s\n\n" % o.get("seen"))
                fh.write("%s\n\n" % o.get("what", ""))
                ev = o.get("evidence")
                if ev:
                    fh.write("```\n%s\n```\n\n" % json.dumps(ev, indent=2)[:4000])
        print("%-8s %3d -> %s" % (rung, len(items), path))
    print("total open:", len(orders))
    return 0


if __name__ == "__main__":
    sys.exit(main())
