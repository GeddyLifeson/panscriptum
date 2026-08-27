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
    """Land the run guard atomically.

    THROUGH `silence.write_json`, WHICH PUTS PID AND THREAD IN THE TEMP NAME. This wrote to a
    fixed `path + ".tmp"` until run #33 -- one temp filename shared by every process that ever
    claims a guard. That is the precise collision `sweep_plan`'s shard docstring warns about and
    `silence.write_json` was written to end: two claimants racing can have the loser's partial
    file replace the winner's target, and the file at stake here is the one that decides whether
    two maintenance runs may run at once. `HANDOFF.md` already records
    `runguard._land:PermissionError` firing 99 times in production, which is direct evidence
    that multiple writers do contend on this path in the live system rather than in theory.
    Found by the run #33 sweep (batch 04).
    """
    return silence.write_json(path, rec, indent=2)


def _land_claim(rec, path, expected_digest):
    """Land a CLAIM, and only onto the file the claimant actually read. -> (ok, reason).

    THE RACE THIS CLOSES. `claim()` read the guard, decided it was free, and wrote -- with
    nothing between the read and the write. Two processes firing on the same cadence can both
    read a free (or stale) guard inside that window and both come away believing `ok=True`, which
    defeats the single invariant this module exists to hold: only one run at a time. `_land`
    below is atomic in the sense `silence.write_json` means it -- the file is never half-written
    -- but atomicity of one write says nothing about STALENESS, and staleness is the whole
    hazard here. `silence.replace_if_unchanged` is the compare-and-swap this codebase already
    grew for exactly this shape (m42) and it was simply not used on the one file that decides
    whether two maintenance runs may overlap. Found by the run #33 sweep (batch 04).

    IT FAILS CLOSED, and that is the correct direction: a refused claim means the run stands
    down and the next cadence tries again, which is the NORMAL outcome this guard is built
    around. A false claim means two runs writing the library at once, which is not recoverable
    by waiting.

    `beat()` AND `release()` USE THIS TOO (found run35, batch 6; they did not before). This
    docstring used to say they did not need it, on the reasoning that their protection is the
    ownership check and "a heartbeat that loses a CAS race with itself has nothing useful to do
    about it" -- but the race those two functions face is not with themselves, it is with a
    SUCCESSOR. `beat()`'s and `release()`'s own bodies both do `rec = read(path)`, check
    `rec["agent"] == agent`, mutate `rec`, and write it back -- a check-then-write with the read
    and the write as far apart as an ownership check and a full write. If a new claimant's
    `claim()` lands in that gap, the record `rec` was read from is now stale: it still carries
    OUR name, `done: False` and an old heartbeat, and writing it back through plain `_land`
    restores exactly that stale record over the successor's fresh claim, silently erasing it
    with no trace -- m27 again, just entered through the heartbeat instead of through the
    original inline read-modify-write this module was written to replace.
    """
    import threading as _th
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    # PID AND THREAD IN THE TEMP NAME, matching `silence.write_json`: a fixed `path + ".tmp"`
    # is itself a collision between two claimants, which is what run #33 found in `_land`.
    tmp = "%s.%d.%d.tmp" % (path, os.getpid(), _th.get_ident())
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=2)
    except Exception:
        silence.note("runguard._land_claim")
        return False, "could not stage the guard record"
    ok, why = silence.replace_if_unchanged(tmp, path, expected_digest)
    if not ok:
        try:
            os.remove(tmp)
        except OSError:
            _ = "silence-exempt: a leftover temp carries our own pid and collides with nobody"
    return ok, why


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
    # THE DIGEST IS TAKEN BEFORE THE READ, NOT AFTER, and the order is the entire safety
    # property. Digest-then-read means a competitor landing in the gap leaves us holding an
    # older digest than the bytes we went on to reason about, so the compare-and-swap below
    # refuses and we stand down -- the safe direction. Read-then-digest inverts it: we would
    # hold the NEWER digest while reasoning about the older content, and the swap would happily
    # let us overwrite a claim we never saw.
    expected = silence.digest_of(path)
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
    ok, why = _land_claim(rec, path, expected)
    if not ok:
        return False, "could not write the guard record: %s" % why
    return True, "claimed"


def beat(agent, path=GUARD):
    """Refresh the heartbeat -- but ONLY on a record that is ours.

    This is the m27 fix and the whole reason the module exists. Returns True if our heartbeat
    landed. Returns False, loudly, if the record now belongs to someone else, has gone missing,
    or has already been closed: in each of those cases stamping it would be a lie about who is
    working, and the last one would silently reopen a finished run.

    DIGEST BEFORE READ, same order and the same reason as `claim()`: a successor's `claim()`
    landing in the gap between our read and our write must make OUR write lose, never theirs.
    Landed through `_land_claim`'s compare-and-swap rather than plain `_land` -- see
    `_land_claim`'s docstring for the race this closes (found run35, batch 6).
    """
    expected = silence.digest_of(path)
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
    ok, why = _land_claim(rec, path, expected)
    if not ok:
        print("runguard: heartbeat CAS refused for %r -- the guard changed underneath us (%s). "
              "A successor may have claimed it; not overwriting." % (agent, why), file=sys.stderr)
    return ok


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
