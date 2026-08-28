"""Run the two nets run #36 merged into drill.py, in isolation, both directions.

Merging a net is a change to the file that HALTS THE LIBRARY when a net goes red. This shift
already lost its library for half an hour to a net asserting a behaviour another agent had just
correctly changed, so a net is not merged here on the strength of having been staged: it is run,
and it is watched refuse.

The two are `a reap never deletes a sandbox whose owner is still running` (M46) and `a canonical
snapshot refuses when it cannot verify itself` (the corpus backup). Both guard fixes made today.
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))

import drill  # noqa: E402  -- imported for its helpers and module globals


def _predicates():
    """Pull the two nets' predicates out of drill_mutation by running it with net() captured."""
    found = {}
    real_net = drill.net

    def capture(area, label, fn, why=""):
        found[label] = fn

    drill.net = capture
    try:
        drill.drill_mutation()
    finally:
        drill.net = real_net
    return found


def main():
    got = _predicates()
    want = ["a reap never deletes a sandbox whose owner is still running",
            "a canonical-corpus snapshot refuses when it cannot verify itself"]
    missing = [w for w in want if w not in got]
    if missing:
        print("NOT REGISTERED:", missing)
        return 1

    ok = True
    for label in want:
        held = bool(got[label]())
        print("%-62s %s" % (label[:62], "HELD" if held else "BREACHED"))
        ok = ok and held

    # THE CONTROLS. Break the guard each net is about and watch that net refuse.
    import mutate as M
    import canon_backup as CB

    real_owner = M._owner_pid
    M._owner_pid = lambda _p: None                  # as if ownership were never recorded
    red1 = not bool(got[want[0]]())
    M._owner_pid = real_owner
    print("%-62s %s" % ("CONTROL: ownership check removed", "RED as required" if red1
                        else "STILL GREEN -- the net is furniture"))

    real_members = CB.members

    def lax(strict=True):
        return real_members(strict=False)           # as if a partial set were acceptable

    CB.members = lax
    red2 = not bool(got[want[1]]())
    CB.members = real_members
    print("%-62s %s" % ("CONTROL: partial-set refusal removed", "RED as required" if red2
                        else "STILL GREEN -- the net is furniture"))

    good = ok and red1 and red2
    print("\nVERDICT:", "both merged nets hold and both are load-bearing" if good
          else "DO NOT KEEP THESE MERGED -- a net that cannot refuse is furniture")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
