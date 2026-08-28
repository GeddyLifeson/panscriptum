"""Partition a handler rung's open orders into agent batches, GROUPED BY TARGET MODULE.

WHY BY MODULE AND NOT BY COUNT. Two agents editing the same file at the same time is how this
project loses work: the second write lands over the first, the first agent reports success, and
the order closes with the fix gone. It is also the noise that made M46 look like an engine bug.
So every order naming the same module goes to ONE agent, and an agent owns its modules outright.

Balance is by order count within that constraint -- a greedy longest-first bin packing, which is
close enough for a dozen bins and has the property that the biggest module group is never split.
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPEN = os.path.join(ROOT, "state", "workorders.json")

SEV_ORDER = {"BLOCKING": 0, "MAJOR": 1, "MINOR": 2, "INFO": 3}
_MOD = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\.py")


def module_of(order):
    """The module an order is about. -> name, or '' when it names none.

    Read from `where` first because that is the field that is supposed to say so; the `what`
    prose is the fallback, and it is a fallback rather than the primary because prose mentions
    modules it is only comparing against.
    """
    for field in ("where", "what"):
        m = _MOD.search(order.get(field) or "")
        if m:
            return m.group(1) + ".py"
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rung", default="RUN")
    ap.add_argument("--bins", type=int, default=8)
    a = ap.parse_args()

    with open(OPEN, encoding="utf-8") as fh:
        orders = json.load(fh)
    mine = [o for o in orders.values() if o.get("handler") == a.rung]

    groups = {}
    for o in mine:
        groups.setdefault(module_of(o) or ("~solo:" + o["id"]), []).append(o)
    ranked = sorted(groups.items(), key=lambda kv: -len(kv[1]))

    bins = [[] for _ in range(a.bins)]
    for mod, items in ranked:
        target = min(bins, key=len)
        target.extend(items)

    out = os.path.join(ROOT, "handoff", "queue", "%s_batches.json" % a.rung)
    payload = []
    for i, b in enumerate(bins, 1):
        b.sort(key=lambda o: (SEV_ORDER.get(o.get("severity"), 9), o.get("first_seen", 0)))
        mods = sorted({module_of(o) for o in b if module_of(o)})
        payload.append({"batch": i, "ids": [o["id"] for o in b], "modules": mods,
                        "orders": b})
        print("batch %2d: %2d orders, modules: %s" % (i, len(b), ", ".join(mods) or "(none)"))
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print("-> %s   (%d orders total in %s)" % (out, len(mine), a.rung))
    return 0


if __name__ == "__main__":
    sys.exit(main())
