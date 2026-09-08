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


def read_verdict(path=GUARD):
    """The current record AND whether the file was intact. -> (record_or_None, fault_or_None).

    ABSENT AND TORN ARE NOW DISTINGUISHED, and the ANSWER to each is still the same (order
    70f66fbd98aa, owner ruling 2026-09-08 "Which faults sound, and on which rung"). This module
    fails OPEN on a corrupt guard on purpose -- `read()`'s docstring has always said so: "an
    unreadable guard cannot prove a predecessor is live, and refusing to run on a corrupt guard
    would wedge the pass permanently on a file nothing else repairs". That is a real, deliberate
    departure from Hard Rule -1's FAIL CLOSED mandate, and sweep43-batch11 was right that it had
    never been put to the owner. It has now been, and the ruling KEPT the fail-open behaviour and
    took away its silence: "have runguard escalate on a corrupt guard while still allowing the
    claim, so the authorisation stops being silent."

    So nothing about what runs changes. What changes is that the fault now leaves a record: an
    absent guard returns `(None, None)` -- honestly nothing, the normal state before the very
    first run -- while a torn one returns `(None, "<what is wrong with it>")`, and `claim()`
    raises that at SAFETY before proceeding. A pass that ran with the overlap invariant
    unenforceable can then be found in the record afterwards, which is the whole difference
    between a known exception and an unnoticed one.

    THREE FAULTS, NOT ONE. Unparseable, wrong-shape (a list, a string, a number: the file does
    not say what it is supposed to say, which is the same fact as unparseable and gets the same
    answer -- `escalation._read_stopped` draws exactly this line one module over), and a present,
    unfinished record whose `heartbeat` is missing or not a number, which is the arm
    `holder_is_live` answers False to. That last one is the most dangerous of the three, because
    it is the one a reader is least likely to notice: the file parses, it has an agent name, and
    it silently cannot prove liveness either way.
    """
    try:
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
    except FileNotFoundError:
        _ = "silence-exempt: no guard file is the normal state before the very first run"
        return None, None
    except Exception as e:
        silence.note("runguard.read")
        return None, ("%s exists but could not be read as JSON (%s: %s)"
                      % (path, type(e).__name__, e))
    if not isinstance(rec, dict):
        silence.note("runguard.read")
        return None, ("%s parsed as %s, not an object, so it cannot say whether a predecessor "
                      "is live" % (path, type(rec).__name__))
    if not rec.get("done") and not isinstance(rec.get("heartbeat"), (int, float)):
        return rec, ("%s holds an UNFINISHED record for %r with no numeric heartbeat, so "
                     "liveness cannot be established from it either way"
                     % (path, rec.get("agent", "?")))
    return rec, None


def read(path=GUARD):
    """The current record, or None if there is no readable one.

    The two-valued form every existing caller wants: `codewatch._maintenance_run_live` and
    `holder_is_live` ask whether there is a live predecessor, and for that question an absent
    guard and a torn one still mean the same thing. `read_verdict` above is where the difference
    is available to a caller that is about to AUTHORISE something on the answer.
    """
    rec, _fault = read_verdict(path)
    return rec


def _land_claim(rec, path, expected_digest):
    """Land a CLAIM, and only onto the file the claimant actually read. -> (ok, reason).

    THE RACE THIS CLOSES. `claim()` read the guard, decided it was free, and wrote -- with
    nothing between the read and the write. Two processes firing on the same cadence can both
    read a free (or stale) guard inside that window and both come away believing `ok=True`, which
    defeats the single invariant this module exists to hold: only one run at a time. The plain
    writer this replaced (`_land`, deleted run #36) was atomic in the sense `silence.write_json`
    means it -- the file is never half-written -- but atomicity of one write says nothing about
    STALENESS, and staleness is the whole hazard here. `silence.replace_if_unchanged` is the
    compare-and-swap this codebase already grew for exactly this shape (m42) and it was simply
    not used on the one file that decides whether two maintenance runs may overlap. Found by the
    run #33 sweep (batch 04).

    THE OLD WRITER IS GONE, NOT KEPT BESIDE THIS ONE (run #36, batch 08). `claim()`, `beat()`
    and `release()` were all moved onto this function during run #35, which left `_land` with
    no caller anywhere in `src/` -- a superseded writer for the guard file, sitting in the one
    module whose stated purpose is that the guard protocol has EXACTLY ONE implementation. A
    second writer nothing calls is not inert: it is a correct-looking landing spot a future edit
    can be pointed back at, and it would silently drop the compare-and-swap that is the entire
    reason this function exists. Its history is worth keeping, so it is recorded here rather
    than in a body: it wrote to a FIXED `path + ".tmp"` until run #33 -- one temp filename
    shared by every process that ever claims a guard -- and `HANDOFF.md` records
    `runguard._land:PermissionError` firing 99 times in production, which is direct evidence
    that multiple writers really do contend on this path in the live system. That is why the
    temp name below carries pid and thread.

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
    OUR name, `done: False` and an old heartbeat, and writing it back through a plain write
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

    A MISSING OR NON-NUMERIC `heartbeat` ALSO READS AS "not live", and that arm is the fail-open
    one the owner ruled on 2026-09-08 (order 70f66fbd98aa): unknown liveness lets the next claim
    through. The behaviour is unchanged and deliberate. It is no longer SILENT -- `read_verdict`
    names that record as a fault and `claim()` escalates it at SAFETY before proceeding -- so
    the answer this function gives on an unreadable record is now one somebody can find
    afterwards rather than one only the code knows about.
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
    prior, fault = read_verdict(path)
    # THE FAIL-OPEN IS ANNOUNCED, NOT SILENT (order 70f66fbd98aa, owner ruling 2026-09-08).
    # `claim()` is the call that decides whether work happens at all, so it is the one place
    # where "the guard could not be read" is an AUTHORISATION rather than an observation -- and
    # it was being granted with nothing written down anywhere. The claim still proceeds, exactly
    # as the ruling directs and as this module's own docstring has always argued: refusing here
    # would wedge the maintenance pass permanently on a file nothing else repairs, and a wedged
    # pass is the failure that gets a guard deleted. What it no longer does is proceed quietly.
    #
    # SAFETY, not MANAGER. Rung 4 stops the subsystem, which is precisely what the ruling says
    # must NOT happen; rung 3 fails the BATTERY -- "no run may claim success while this stands"
    # -- which is the honest reading: the pass may run, and it may not come back saying the
    # overlap invariant held, because for this run it could not be checked. Rung 0 would have
    # been the same silence in a different file.
    #
    # DEFENSIVE, like every other escalate() call on an error path in this tree. A missing or
    # broken escalation chain must not turn a readable-guard problem into a traceback at the top
    # of a maintenance run; `silence.note` keeps the janitor's copy either way.
    if fault:
        try:
            import escalation as _ESC
            _ESC.escalate(_ESC.SAFETY, "RUNGUARD_CORRUPT_GUARD_RECORD",
                          "the overlap guard could not be read, so this claim by %r proceeds "
                          "WITHOUT the one invariant runguard exists to hold (bug m27: two "
                          "maintenance runs overlapping, one clobbering the other's work). %s"
                          % (agent, fault),
                          evidence={"guard": path, "fault": fault, "agent": agent,
                                    "claim_allowed": True},
                          source="runguard", who=str(agent))
        except Exception:
            silence.note("runguard.corrupt-guard-escalate")
        sys.stderr.write("runguard: PROCEEDING ON AN UNREADABLE GUARD — %s\n" % fault)
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
    Landed through `_land_claim`'s compare-and-swap rather than a plain write -- see
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

    DIGEST BEFORE READ, same as `beat()` and for the identical reason: without the
    compare-and-swap, a successor's claim landing between our read and our write would be
    overwritten by us re-stamping OUR OWN stale copy of the record `done: true` on top of it,
    closing a run we no longer hold ownership of the file for (found run35, batch 6).
    """
    expected = silence.digest_of(path)
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
    ok, why = _land_claim(rec, path, expected)
    if not ok:
        print("runguard: release CAS refused for %r -- the guard changed underneath us (%s). "
              "A successor may have claimed it; not overwriting." % (agent, why), file=sys.stderr)
    return ok


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
