"""LEDGER GUARD — the relay's own integrity, checked rather than trusted.

WHY THE LEDGERS NEEDED NETS AND HAD NONE.

Every maintenance run is a fresh session with no memory of the last one. What survives is four
files -- `HANDOFF.md`, `BUGS.md`, `NEXT_STEPS.md`, `MAINTENANCE.md` -- and they are the ONLY
thing carrying continuity. That makes them the highest-leverage target in the project and, until
2026-08-25, the least defended: `HANDOFF.md` was append-only *by convention*, `NEXT_STEPS.md` is
overwritten wholesale every run, and nothing anywhere parsed `BUGS.md` for structure.

The failure mode is specific and nasty. A run that truncates `HANDOFF.md`, or writes a
`NEXT_STEPS.md` that is empty or garbled, does not crash anything. It poisons **every future
run**, silently, because the next run reads it as fact and has nothing to compare it against.
That is the exact profile the owner's rule selects for: a failure that is silent AND outlives the
run that caused it.

THREE INDEPENDENT SYSTEMS, per the standing doctrine:

  1. APPEND-ONLY, ENFORCED. `HANDOFF.md` is history. New content must CONTAIN the old, verbatim.
     Not "be longer than" -- longer is what a truncation plus a large new entry looks like.
  2. STRUCTURE, PARSED. `BUGS.md` must have its three sections, and no bug id may appear in both
     Open and Resolved. That second check has been run BY HAND at the end of every session in
     this project's history, which is a good sign it should not have been a manual step.
  3. SUBSTANCE, MEASURED. A ledger that exists but says nothing is indistinguishable from a
     healthy one to any check that only asks "does the file parse". Each has a floor.

These are deliberately cheap -- string containment and a section split, no model, no network --
because a guard that costs anything gets skipped on the run that most needed it.
"""
import json
import os
import re
import sys
import threading

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# This module is imported by `publish.push` -> `assert_intact` from processes whose sys.path may
# not carry src/, so it is put there rather than assumed -- the same two lines every other
# module in this directory opens with. `silence` is needed by seal() below, which used to
# swallow its one failure with a bare `pass` and therefore left no trace in state/failures.json.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence                                                          # noqa: E402

# `handoff/HANDOFF.md` JOINED THIS LIST ON 2026-08-31 (order 42db308cc85d, run40 sweep).
#
# The four root-level ledgers were guarded and this one was not, while the project's own file
# headers describe it as the durable carrier of "the project's deep engineering history,
# doctrine, and architecture" -- the reference book to the root HANDOFF.md's run journal. That
# is a ledger by every definition this module uses, and `pipeline.py`'s own commentary records
# it ALREADY LOSING 629 LINES to exactly the truncation class this file exists to prevent.
# None of the three mechanisms here could see it, and `publish.py` copies the whole `handoff/`
# directory into the public export tree with no integrity check on the way.
#
# The module docstring's claim that four files "are the ONLY thing carrying continuity" was a
# false completeness claim -- the most expensive kind in this project, because it reads as
# coverage. Five now, and the fifth is the one with the history in it.
APPEND_ONLY = ("HANDOFF.md", "handoff/HANDOFF.md")
# Floors, set well below the current sizes so ordinary editing never trips them. They exist to
# catch a TRUNCATION -- a file that lost its history -- not to police how much a run writes.
# handoff/HANDOFF.md is ~58 KB today; 20000 is the same proportional slack the root ledger gets.
MIN_BYTES = {"HANDOFF.md": 20000, "BUGS.md": 8000, "NEXT_STEPS.md": 3000,
             "MAINTENANCE.md": 5000, "handoff/HANDOFF.md": 20000}
REQUIRED_SECTIONS = {"BUGS.md": ("## Open", "## Resolved")}


class LedgerViolation(RuntimeError):
    """A ledger was about to lose something. Raised before the write, never after."""


def _read(name):
    p = os.path.join(HERE, name)
    try:
        with open(p, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def _one_insertion(old, new):
    """Is `new` exactly `old` with ONE contiguous block inserted at one point? -> bool.

    NEWEST ON TOP IS THIS FILE'S DOCUMENTED CONVENTION, and the substring test alone could not
    express it. `HANDOFF.md` says so in its own header and `MAINTENANCE.md:143` repeats it:
    "dated run journal, newest on top". A legitimate run therefore writes
    `header + new entry + everything that was under the header before` -- which loses NOTHING,
    and which `old in new` REJECTS, because the old text is no longer contiguous once an entry
    is spliced in behind the header. Measured 2026-08-27 (run #36) against the live 473,848-byte
    file: the real append pattern was rejected, a bottom-append accepted. A guard that refuses
    the only writing pattern its file actually uses cannot be wired to a writer, which is a large
    part of why it never was.

    So: longest common prefix plus longest common suffix must cover the whole of `old`. That is
    precisely "nothing removed, one block inserted at a single point" -- true for a bottom
    append (insert at the end), a top append (insert at the start), and the newest-on-top
    append-after-header this project uses. It is NOT true of a truncation, a reordering, or an
    edit that removes a line from the middle, all of which still fail.
    """
    if new is None or len(new) < len(old):
        return False
    n = len(old)
    p = 0
    while p < n and old[p] == new[p]:
        p += 1
    if p >= n:
        return True
    s = 0
    while s < n - p and old[n - 1 - s] == new[len(new) - 1 - s]:
        s += 1
    return p + s >= n


def check_append_only(name, new_text, old=None):
    """-> (ok, reason). Would this write LOSE history?

    Containment, not length. A run that truncated the file and then appended a long entry
    produces a LONGER file, so a size comparison would wave it through -- and that is precisely
    the shape a botched overwrite takes.

    `old` is an ADDITIVE keyword with the previous behaviour as its default (read the live file):
    `check_since_snapshot()` compares a live ledger against the last SEALED copy of itself rather
    than against itself, and that is the same question asked from the other side of the write.
    """
    if name not in APPEND_ONLY:
        return True, "%s is not append-only" % name
    old = _read(name) if old is None else old
    if old is None:
        return True, "%s does not exist yet" % name
    if old.strip() and not (old in (new_text or "") or _one_insertion(old, new_text)):
        return False, ("%s is append-only and this write does not contain the existing file. "
                       "History is the whole value of a relay ledger; a run that cannot see the "
                       "last run's entry is a run starting from nothing." % name)
    return True, "history preserved"


def check_structure(name, text=None):
    """-> (ok, [problems]). Sections present, floors met, and no bug filed in two places."""
    text = text if text is not None else _read(name)
    problems = []
    if text is None:
        return False, ["%s is missing entirely" % name]
    floor = MIN_BYTES.get(name)
    if floor and len(text.encode("utf-8")) < floor:
        problems.append("%s is %d bytes, below the %d-byte floor — a ledger this short has lost "
                        "something" % (name, len(text.encode("utf-8")), floor))
    for sec in REQUIRED_SECTIONS.get(name, ()):
        if sec not in text:
            problems.append("%s has no '%s' section" % (name, sec))
    if name == "BUGS.md" and "## Open" in text and "## Resolved" in text:
        # SECTIONS BOUNDED BY THE ORDER THEY ARE FOUND IN, not by an assumed Open-then-Resolved
        # layout. The earlier version sliced `text[i:j]` on that assumption; reorder the file --
        # a human edit, a template change -- and `i > j` makes Python answer the slice with `""`,
        # so `op` is empty, the intersection is empty, and the one check that exists to catch a
        # bug filed in two places passes even when every Resolved bug is still sitting in Open.
        # A check that cannot fail reads exactly like a check that passed.
        marks = sorted((text.find(s), s) for s in ("## Open", "## Resolved", "## Watching")
                       if text.find(s) >= 0)
        span = {}
        for n, (at, sec) in enumerate(marks):
            span[sec] = text[at:(marks[n + 1][0] if n + 1 < len(marks) else len(text))]
        op, res = span["## Open"], span["## Resolved"]
        both = sorted(set(re.findall(r"\[([Mm]\d+)\]", op))
                      & set(re.findall(r"\[([Mm]\d+)\]", res)))
        if both:
            problems.append("these bug ids are in BOTH Open and Resolved: %s — a resolved bug "
                            "left in Open is how the Open section rots" % ", ".join(both))
    return (not problems), problems


def check_all():
    """-> {name: [problems]} across every ledger. Empty dict is the good state."""
    out = {}
    for name in list(MIN_BYTES):
        ok, problems = check_structure(name)
        if not ok:
            out[name] = problems
    return out


CHAIN = os.path.join(HERE, "state", "ledger_chain.jsonl")
# The last SEALED copy of every append-only ledger. The chain records digests, and a digest can
# only ever answer "did this change" -- never "did the change keep the history", which is the
# one question `check_append_only` was written to answer and the one thing a hash cannot be
# asked. One file per append-only ledger, overwritten each seal.
SNAPSHOT_DIR = os.path.join(HERE, "state", "ledger_snapshot")

# How much of an append-only ledger may disappear between two seals before it is a TRUNCATION
# rather than an edit. A person fixing a typo in an old entry, or re-wrapping a paragraph,
# removes a handful of lines out of thousands; a run that lost its history removes most of them.
# Set high enough that ordinary hand-editing cannot reach it, because this refuses a PUSH and a
# safety that stops the operator doing ordinary work is a safety that gets deleted.
MAX_LOST_FRACTION = 0.05


def _digest(text):
    import hashlib
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:32]


def seal():
    """Append a hash-chained record of the ledgers' current state. -> the new link.

    THE THIRD MECHANISM, and it answers what the other two cannot.

    `check_append_only` proves a PROPOSED write keeps history -- but only if it is called, and
    only by a writer that chose to call it. (Run #36 gave it the one caller this project can
    actually give it: `check_since_snapshot()` below asks the same question AFTER the write, from
    `assert_intact()`, because nothing in `src/` writes HANDOFF.md and a Python function cannot
    gate a person's editor.) `check_structure` proves the file parses. Neither
    can answer the question a relay actually needs: *did anything change these files between the
    last run and this one, and if so what?* A run that edits HANDOFF.md directly, or a crash
    mid-write, or an edit made by hand between runs, leaves both of them satisfied.

    A hash chain answers it. Each link records the digest of every ledger plus the digest of the
    PREVIOUS link, so the sequence is tamper-evident: change any past link and every link after
    it stops verifying. Borrowed from the audit-trail pattern used for autonomous-agent logs
    (Asqav), minus the signing -- there is one writer here and no adversary to authenticate
    against, so the chain-of-hashes property is the whole value and the PKI would be theatre.

    Deliberately a SEPARATE file rather than hashes embedded in the markdown: the ledgers are
    prose a person reads and an agent appends to, and threading hashes through them would make
    every ordinary edit look like tampering.
    """
    prev = None
    links = read_chain()
    if links:
        prev = links[-1].get("self")
    import time
    rec = {"at": time.time(), "prev": prev,
           "ledgers": {n: {"digest": _digest(_read(n) or ""), "bytes": len((_read(n) or ""))}
                       for n in sorted(MIN_BYTES)}}
    rec["self"] = _digest(json.dumps({k: rec[k] for k in ("at", "prev", "ledgers")},
                                     sort_keys=True))
    try:
        os.makedirs(os.path.dirname(CHAIN), exist_ok=True)
        with open(CHAIN, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        return None
    # AND KEEP THE TEXT, not only its digest, for the append-only ones. A stale or missing
    # snapshot makes the next `check_since_snapshot()` compare against an OLDER state, which is
    # strictly a subset of the history the live file should still contain -- so a failure here
    # cannot wave a truncation through, only report one late. That is why it does not fail the
    # seal it rides along with.
    #
    # THAT REASONING IS TRUE OF STALE AND FALSE OF TORN (order be7b01fe1467). The temp file was
    # a FIXED, SHARED name -- `HANDOFF.md.tmp` -- and seal() is reached from `assert_intact()`,
    # which `publish.push()` calls before every push, while this project runs a `publish.py
    # --loop` daemon alongside manual pushes. Two sealers meeting here is an ordinary
    # situation, not a rarity: both open the same temp, the second truncates the first, and the
    # first's `os.replace` lands whatever was in the file at that instant. A torn snapshot is a
    # PREFIX of HANDOFF.md, and `_one_insertion(old=prefix, new=live)` returns True for any live
    # file that still begins with that prefix, because the longest common prefix already covers
    # the whole of `old`. So `check_since_snapshot` would answer "history preserved" for a
    # HANDOFF.md truncated and regrown -- precisely the attack it was added on 2026-08-27 (run
    # #36, order db2728e0f4bb) to catch, and which its own docstring records having passed
    # check_all(), verify_chain() and assert_intact() before it existed. The weakening is
    # proportional to the tear and was completely silent, because `except Exception: pass` did
    # not even reach the ledger.
    #
    # Unique per writer, matching `hostcheck._land_hosts` and `silence.write_json`; noted rather
    # than swallowed; and the temp is unlinked on failure so a shared state directory is not
    # littered with half-written snapshots. NOT failing the seal is still deliberate and
    # unchanged -- only the silence and the shared name are gone.
    for n in APPEND_ONLY:
        text = _read(n)
        if text is None:
            continue
        # FLATTENED, because a guarded name may now contain a path separator. With
        # `handoff/HANDOFF.md` on the list the old spelling built a snapshot path inside a
        # `handoff/` SUBDIRECTORY of SNAPSHOT_DIR that nothing creates, so the write would have
        # raised, been swallowed into `silence.note`, and left the one file this order added
        # unsnapshotted -- a guard that reports itself installed and takes no copy.
        flat = n.replace("/", "__").replace(os.sep, "__")
        tmp = os.path.join(SNAPSHOT_DIR,
                           "%s.%d.%d.tmp" % (flat, os.getpid(), threading.get_ident()))
        try:
            os.makedirs(SNAPSHOT_DIR, exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp, os.path.join(SNAPSHOT_DIR, flat))
        except Exception:
            silence.note("ledger_guard.py:snapshot")
            try:
                os.unlink(tmp)
            except OSError:
                # Never written, or already renamed away. Nothing to clean and nothing to say.
                pass
    return rec


def _read_snapshot(name):
    try:
        with open(os.path.join(SNAPSHOT_DIR, name), encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def _lost_fraction(old, new):
    """How much of `old`'s substance is missing from `new`. -> float in [0, 1].

    Lines rather than bytes, and set membership rather than position, so a reordering or a
    reflowed paragraph is not read as a loss. Blank and rule-only lines are dropped because a
    markdown ledger is full of them and they carry no history.
    """
    def body(t):
        return {ln.strip() for ln in (t or "").splitlines()
                if ln.strip() and set(ln.strip()) - set("-=*_# ")}
    was = body(old)
    if not was:
        return 0.0
    return len(was - body(new)) / len(was)


def check_since_snapshot(name):
    """-> (ok, reason). Has this ledger LOST history since it was last sealed?

    THE ONLY PLACE `check_append_only` CAN ACTUALLY STAND IN THIS PROJECT. It was written as a
    PRE-write guard, and it had no production caller for a structural reason rather than an
    oversight: nothing in `src/` writes `HANDOFF.md` at all (`pipeline.py:36` says so outright),
    because the file is written by hand -- by a person, or by an agent's editor -- and a Python
    function cannot gate an editor. Left there, it was a safety in a file rather than a safety in
    effect, which is the exact fourth property Hard Rule -1 was written about.

    Asked from the other side of the write it becomes answerable. `seal()` keeps the last
    published copy; this compares the live file against it and hands the verdict to
    `assert_intact()`, which `publish.push()` already calls before every push. Measured on
    2026-08-27 (run #36): a HANDOFF.md truncated to its header and regrown LONGER than it began
    -- 473,848 -> 476,271 bytes -- passed `check_all()`, passed `verify_chain()` (no SHRANK: it
    grew) and passed `assert_intact()`. The whole relay history would have been published as
    fact. The byte floor and the SHRANK test are both size tests, and size is precisely what a
    truncate-then-append preserves.

    The tolerance is deliberate and it is not a weakening. `check_append_only` alone would refuse
    a person fixing a typo in a two-month-old entry, and that refusal blocks the PUSH -- a
    safety that stops ordinary work gets removed, and this project has already lost one gate
    that way. So an exact append passes outright, and anything else is measured: losing more
    than MAX_LOST_FRACTION of the ledger's lines is a truncation whoever caused it.
    """
    old = _read_snapshot(name)
    if old is None:
        return True, "no sealed snapshot of %s yet -- this run makes the first one" % name
    new = _read(name)
    if new is None:
        return False, ("%s existed at the last seal and is GONE now -- the relay's history was "
                       "deleted, not edited" % name)
    ok, why = check_append_only(name, new, old=old)
    if ok:
        return True, why
    lost = _lost_fraction(old, new)
    if lost <= MAX_LOST_FRACTION:
        return True, ("%s was edited rather than appended to (%.1f%% of its lines are gone, "
                      "under the %.0f%% truncation floor)" % (name, lost * 100,
                                                              MAX_LOST_FRACTION * 100))
    return False, ("%s has LOST %.0f%% of its lines since the last seal -- that is a truncation, "
                   "not an edit. The sealed copy is %s; compare it before writing anything else, "
                   "because the live file is no longer the history."
                   % (name, lost * 100, os.path.join(SNAPSHOT_DIR, name)))


def read_chain():
    """Read the chain, or raise -- "no chain yet" and "could not be read" are not the same claim.

    Only `FileNotFoundError` means "no chain yet": a fresh project, or the first run after this
    file was introduced, where an empty list is simply true. The blanket `except Exception:
    return []` that used to sit beside it collapsed every OTHER failure into that same empty
    list -- permission denied, the file held open by another process, a directory sitting where
    the file should be, an encoding that will not decode. Those are not "no chain"; they are
    "cannot tell", and `verify_chain()` on an empty list reports the chain intact because it
    never got the chance to find otherwise. `assert_intact()` trusts that report before `push()`
    reaches the PUBLIC repo. So this now only swallows the one exception that is genuinely
    silence-shaped, and lets everything else propagate: `verify_chain()` and `assert_intact()`
    make no attempt to catch it either, which means an unreadable chain now STOPS the publish
    (and, in `workorders.py`'s sweep, files a DETECTOR_FAILED order instead of a clean one) —
    fail closed, per the project rule that a layer that does not know must never authorise.
    """
    out = []
    try:
        with open(CHAIN, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if ln:
                    try:
                        out.append(json.loads(ln))
                    except Exception:
                        continue
    except FileNotFoundError:
        return []
    return out


def verify_chain():
    """-> (ok, [problems]). Recompute every link and report the first that does not verify.

    Two distinct faults are reported separately, because they mean different things:
      BROKEN LINK   the chain itself was edited -- someone rewrote history
      SHRANK        a ledger got SMALLER between two links. Not proof of wrongdoing (a file can
                    legitimately be rewritten) but it is exactly the shape of a truncation, and
                    it is invisible to every other check once the write has happened.
    """
    links = read_chain()
    problems = []
    prev = None
    for i, rec in enumerate(links):
        body = {k: rec.get(k) for k in ("at", "prev", "ledgers")}
        if rec.get("self") != _digest(json.dumps(body, sort_keys=True)):
            problems.append("link %d does not verify -- the chain has been edited" % i)
        if rec.get("prev") != prev:
            problems.append("link %d does not follow link %d" % (i, i - 1))
        if i:
            for name, cur in (rec.get("ledgers") or {}).items():
                was = ((links[i - 1].get("ledgers") or {}).get(name) or {}).get("bytes")
                now = (cur or {}).get("bytes")
                # `is not None`, not truthiness: a ledger wiped to a genuinely EMPTY file records
                # `now == 0`, which is falsy, and the old `was and now and ...` short-circuited
                # to False on exactly the total truncation this check exists to catch. That it
                # never bit is owed to `assert_intact()` running `check_all()`'s byte floor
                # first -- redundancy in the caller, not a property of this function, and any
                # standalone caller (a drill, a health check) got a clean pass on a wiped ledger.
                if was is not None and now is not None and name in APPEND_ONLY and now < was:
                    problems.append("%s SHRANK between link %d and %d (%d -> %d bytes)"
                                    % (name, i - 1, i, was, now))
        prev = rec.get("self")
    return (not problems), problems


def assert_intact():
    """Raise unless every ledger is whole. Called by `publish` before anything is pushed.

    The ledgers travel to the PUBLIC repo with everything else, so a truncated HANDOFF or a
    BUGS.md with a resolved bug still sitting in Open does not just mislead the next run -- it
    is published. This is the enforcing wrapper; `check_all` is the reporting one, and both
    exist because a checker with no caller is a checker that never runs.
    """
    bad = check_all()
    if bad:
        raise LedgerViolation(
            "the relay's ledgers are not intact:\n"
            + "\n".join("  %s: %s" % (n, "; ".join(p)) for n, p in sorted(bad.items())))
    ok, problems = verify_chain()
    if not ok:
        raise LedgerViolation(
            "the ledger hash chain does not verify:\n  " + "\n  ".join(problems[:6]))
    # THE APPEND-ONLY RULE, ENFORCED RATHER THAN DECLARED. Before this, `APPEND_ONLY` was a
    # tuple nothing consulted on any production path: `check_append_only` had no caller outside
    # `drill.py`, and the two checks that DO run here are both size tests that a
    # truncate-then-append passes by growing. Run #36 order db2728e0f4bb.
    for name in APPEND_ONLY:
        ok, why = check_since_snapshot(name)
        if not ok:
            raise LedgerViolation(why)
    # `seal()` returns None on any write failure (disk full, permissions, the state/ directory
    # gone) with no exception raised. A bare call here used to discard that -- `verify_chain`
    # would keep passing on every later run, because the existing links still verify against
    # each other; there would simply be no new one. The mechanism whose whole job is answering
    # "did anything change these files since the last run" would have silently stopped
    # answering, and nothing downstream would know to stop trusting it.
    if seal() is None:
        raise LedgerViolation(
            "the ledger hash chain could not be sealed this run -- the new link was not "
            "written, so a future run cannot tell whether these files changed underneath it")
    return True


def main():
    """The CLI. RUNS ALL THREE MECHANISMS, because it says all three passed.

    ORDER 418e83501f0f. This called `check_all()` and, on an empty result, printed "ledgers: all
    intact" and returned 0 -- having run ONE of the three mechanisms this module's docstring
    enumerates. It never called `verify_chain()` and never called `check_since_snapshot()`, and
    the second of those was added on 2026-08-27 specifically because `check_all()`'s byte floor
    and `verify_chain()`'s SHRANK test are BOTH size tests and a truncate-then-append preserves
    size. So a broken hash chain, or a HANDOFF.md truncated to its header and regrown, printed
    "all intact" and exited 0 out of the module whose entire subject is that failure.
    `assert_intact()` does run all three, but it is reached only from `publish.push()`; the CLI
    is the surface a person uses to ASK, and it was the one answering from the least evidence.

    Deliberately does NOT seal. `assert_intact()` seals because it is the gate on a write that is
    about to happen; a question asked from the command line must not change the state it is
    asking about, or every `--check` would move the baseline the next one compares against.

    Each mechanism reports separately, pass or fail. A single "all intact" line is what let the
    gap hide: three verdicts collapsed into one sentence cannot be audited against the code.
    """
    import argparse
    ap = argparse.ArgumentParser(description="check the relay's ledgers")
    ap.parse_args()
    failures = 0

    bad = check_all()
    if bad:
        failures += 1
        print("STRUCTURE + FLOORS: FAILED")
        for name, problems in sorted(bad.items()):
            print("  %s:" % name)
            for p in problems:
                print("     " + p)
    else:
        print("STRUCTURE + FLOORS: ok (%d ledger(s) parsed, all above their byte floors)"
              % len(MIN_BYTES))

    ok, problems = verify_chain()
    links = len(read_chain())
    if ok:
        print("HASH CHAIN       : ok (%d link(s) verify, no append-only ledger shrank)" % links)
    else:
        failures += 1
        # Uncapped. `assert_intact()` prints the first six into an exception message, which is a
        # different job; this is the surface somebody reads to go and repair the chain, and a
        # truncated fault list is how a second break gets missed behind the first.
        print("HASH CHAIN       : FAILED over %d link(s)" % links)
        for p in problems:
            print("     " + p)

    for name in APPEND_ONLY:
        ok, why = check_since_snapshot(name)
        if ok:
            print("SINCE LAST SEAL  : ok  %s -- %s" % (name, why))
        else:
            failures += 1
            print("SINCE LAST SEAL  : FAILED  %s -- %s" % (name, why))

    print("\nledgers: all intact" if not failures
          else "\nledgers: %d of the three mechanisms reported a fault" % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
