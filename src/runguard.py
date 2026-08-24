#!/usr/bin/env python3
"""
RUNGUARD — the overlap guard for the maintenance pass, as code instead of as a convention.

WHY THIS FILE EXISTS
--------------------
`state/MAINTENANCE_RUN.json` is the one piece of machinery every maintenance run depends on:
it is how a run learns whether a predecessor is still live, and how it tells its successor that
it has finished. Until now there was no implementation of it anywhere in `src/`. The protocol
lived in prose in `MAINTENANCE.md`, and every run re-improvised the read-modify-write inline.

That is the root cause of bug m27, and m27 is what it costs. On 2026-08-24 an interactive
session claimed the guard while run #6 was live. Run #6 went on refreshing the heartbeat for
roughly 45 minutes -- because its improvised helper loaded the file, stamped `heartbeat` and
wrote it back, and nothing in that sequence asks whose record it is. The effect is the exact
inverse of what the guard is for: a FINISHED run was kept looking live by the heartbeat of a
DIFFERENT run, so the next run would have been told to stand down by a corpse.

The claim was always checked. The refresh never was. So the invariant this module exists to
hold is one line long:

    A run may only ever refresh, or close, a record that carries its own name.

Everything else here follows the protocol MAINTENANCE.md already describes; the point is that
it now has exactly one implementation, and that implementation checks.

WHY IT DOES NOT RAISE
---------------------
`beat()` returns False and says so on stderr rather than raising. A heartbeat is a
side-observation, not the work; a run that has legitimately lost the guard should find out
loudly and keep its own bookkeeping honest, not die mid-phase and strand whatever it was
holding. `claim()` is the call that decides whether work happens at all, and it reports its
refusal as a value the caller must act on.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import silence  # noqa: E402

GUARD = os.path.join(HERE, "state", "MAINTENANCE_RUN.json")

# MAINTENANCE.md's threshold. A predecessor is live only if it is both unfinished AND recently
# heard from; a stale heartbeat means a crashed run, which must not block its successor forever.
STALE_AFTER_S = 15 * 60


def read(path=GUARD):
    """The current record, or None if there is no readable one.

    Absent and torn are deliberately NOT distinguished here the way `health` distinguishes them,
    because for this file the response is the same: an unreadable guard cannot prove a
    predecessor is live, and refusing to run on a corrupt guard would wedge the pass permanently
    on a file nothing else repairs.
    """
    try:
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
        return rec if isinstance(rec, dict) else None
    except FileNotFoundError:
        _ = "silence-exempt: no guard file is the normal state before the very first run"
        return None
    except Exception:
        silence.note("runguard.read")
        return None


def _land(rec, path):
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=2)
    except Exception:
        silence.note("runguard._land")
        return False
    return silence.replace_retry(tmp, path)


def holder_is_live(rec, now=None):
    """Is this record a predecessor that is still working?

    True only for an unfinished record with a fresh heartbeat. `done: true`, a stale heartbeat
    and a missing record all read the same way to a would-be successor: go ahead.
    """
    if not rec or rec.get("done"):
        return False
    now = time.time() if now is None else now
    hb = rec.get("heartbeat")
    if not isinstance(hb, (int, float)):
        return False
    return (now - hb) < STALE_AFTER_S


def claim(agent, path=GUARD, note=None):
    """Take the guard for `agent`, or refuse.

    Returns (ok, reason). On refusal the caller must write nothing and stop -- landing on a live
    predecessor is the NORMAL outcome of a cadence that fires more often than a run takes, and
    exiting immediately is the correct result rather than a failure.
    """
    prior = read(path)
    if holder_is_live(prior):
        age = time.time() - prior.get("heartbeat", 0)
        return False, ("live predecessor %r, heartbeat %.1f min old"
                       % (prior.get("agent", "?"), age / 60.0))
    now = time.time()
    rec = {"started": now, "heartbeat": now, "done": False, "agent": agent}
    if note:
        rec["note"] = note
    if prior is not None and not prior.get("done"):
        # A crashed run's record is being taken over, not merely replaced. Say whose it was, so
        # the takeover is legible in the file itself rather than only in a handoff entry.
        rec["superseded"] = {"agent": prior.get("agent"), "started": prior.get("started"),
                             "heartbeat": prior.get("heartbeat")}
    if not _land(rec, path):
        return False, "could not write the guard record"
    return True, "claimed"


def beat(agent, path=GUARD):
    """Refresh the heartbeat -- but ONLY on a record that is ours.

    This is the m27 fix and the whole reason the module exists. Returns True if our heartbeat
    landed. Returns False, loudly, if the record now belongs to someone else, has gone missing,
    or has already been closed: in each of those cases stamping it would be a lie about who is
    working, and the last one would silently reopen a finished run.
    """
    rec = read(path)
    if rec is None:
        print("runguard: guard record is gone; not recreating it mid-run "
              "(a claim, not a heartbeat, is what creates one)", file=sys.stderr)
        return False
    owner = rec.get("agent")
    if owner != agent:
        print("runguard: REFUSING to refresh a heartbeat for %r -- the guard now belongs to %r. "
              "This run no longer holds it." % (agent, owner), file=sys.stderr)
        return False
    if rec.get("done"):
        print("runguard: REFUSING to refresh %r -- the record is already closed. "
              "Reopening a finished run would make it look live to the next one." % (agent,),
              file=sys.stderr)
        return False
    rec["heartbeat"] = time.time()
    return _land(rec, path)


def release(agent, path=GUARD, note=None):
    """Close our own record. Same ownership rule: a run may only ever close its own.

    Returns True if the closure landed. A run that has lost the guard must NOT stamp
    `done: true` on the record of whoever holds it now -- that would hand a live run's guard
    away to the next comer, which is the m27 failure pointed the other way.
    """
    rec = read(path)
    if rec is None:
        print("runguard: guard record is gone; nothing to release", file=sys.stderr)
        return False
    owner = rec.get("agent")
    if owner != agent:
        print("runguard: REFUSING to close a record belonging to %r (we are %r). "
              "Closing another run's guard would release a lock we do not hold."
              % (owner, agent), file=sys.stderr)
        return False
    rec["done"] = True
    rec["finished"] = time.time()
    if note:
        rec["note"] = note
    return _land(rec, path)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="inspect or drive the maintenance overlap guard")
    ap.add_argument("--agent", help="the agent name to claim/beat/release as")
    ap.add_argument("--claim", action="store_true")
    ap.add_argument("--beat", action="store_true")
    ap.add_argument("--release", action="store_true")
    args = ap.parse_args()

    if args.claim or args.beat or args.release:
        if not args.agent:
            print("--agent is required for --claim/--beat/--release", file=sys.stderr)
            return 2
        if args.claim:
            ok, why = claim(args.agent)
            print(("CLAIMED" if ok else "REFUSED") + ": " + why)
            return 0 if ok else 1
        if args.beat:
            return 0 if beat(args.agent) else 1
        return 0 if release(args.agent) else 1

    rec = read()
    print("=" * 100)
    print("RUN GUARD — state/MAINTENANCE_RUN.json")
    print("=" * 100)
    if rec is None:
        print("\nno readable record — a run may proceed")
        return 0
    live = holder_is_live(rec)
    hb = rec.get("heartbeat")
    age = (time.time() - hb) / 60.0 if isinstance(hb, (int, float)) else float("nan")
    print("\n  agent      : %s" % rec.get("agent"))
    print("  done       : %s" % rec.get("done"))
    print("  heartbeat  : %.1f min ago" % age)
    print("  verdict    : %s" % ("A PREDECESSOR IS LIVE — do not run"
                                 if live else "free — a run may proceed"))
    if rec.get("superseded"):
        print("  superseded : %s" % rec["superseded"].get("agent"))
    if rec.get("note"):
        print("  note       : %s" % rec["note"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
