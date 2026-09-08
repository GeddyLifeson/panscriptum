"""ESCALATION — the chain of command, from the janitor to the owner, and the halt at the top.

WHY THIS EXISTS (owner ruling, 2026-08-25). The library wrote 145 chapters it should not have,
and the post-mortem's uncomfortable finding was that NOTHING FAILED. Every individual component
did what it was told. What was missing was a chain: nobody whose job it was to notice had the
authority to stop anything, and nobody with the authority to stop things was told.

A single guard is a person shouting into a room. A chain of command is a building where the
message travels until it reaches someone who can act, and where the last resort is that the whole
plant stops and waits for the owner. This module is that chain.

THE RUNGS. Each has ONE authority, and each records at every rung beneath it, so the lowest log
always holds the whole story even when the top rung fires.

    0  JANITOR      record it. No authority to stop anything, on duty at all hours.
                    -> silence.note / health.record. This is what already existed, alone.
    1  OPERATOR     refuse THIS unit of work -- one block, one entity, one call.
                    -> raise, and let the caller record a failure and move on.
    2  SUPERVISOR   refuse THIS SOURCE. Its area of the park closes; the rest keeps running.
    3  SAFETY       fail the BATTERY. No run may claim success while this stands.
    4  MANAGER      stop the SUBSYSTEM. The job stops and does not restart itself.
    5  OWNER        HALT EVERYTHING. Nothing starts until a person rules on it.

WHY EVERY SOURCE IS ITS OWN AREA. A fault in one source must never close the park. `Marvel`
having a bad host, or `Song of Syx` having nothing cited, is a SUPERVISOR-level event: that
source stops, its neighbours do not notice. Only an invariant that spans the whole library --
a corrupt shared ledger, a writer contract broken, evidence being attributed to the wrong entity
corpus-wide -- reaches the OWNER rung. Escalating everything is the same failure as escalating
nothing, because an alarm that always sounds is furniture.

THE HALT IS DELIBERATELY HARD TO CLEAR. It fails closed: an unreadable or malformed HALT file is
treated as halted, because a halt that a corrupted file can lift is not a halt. It cannot be
cleared programmatically, and as of run #33 that is a RUNTIME guarantee rather than a reading of
the source: `clear()` demands a written ruling, records who gave it, and REFUSES outright unless
this file is the program being run and its own `main()` is the caller -- see
`_by_a_person_at_the_cli`. `drill.py:_no_programmatic_clear` still scans `src/` for a call; that
is the review-time half, and it was the ONLY half until run #33, when an audit pointed out that
an import alias, a `from ... import`, or a `getattr` walks straight past a substring scan. An
autonomous run may RAISE a halt; only a person may lift one. That asymmetry is the entire point:
the last incident was caused by an automated agent removing a safety it had concluded was
unnecessary.
"""
import contextlib
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence  # noqa: E402

HALT_FILE = os.path.join(HERE, "state", "HALT.json")
LOG = os.path.join(HERE, "state", "escalation.log")

# THE SENTENCE A HALT REFUSES WITH, AND THE ONLY PLACE IT IS SPELLED. `allsweep` reads a child's
# output for this to tell REFUSED from BROKEN -- run #31 found it grading eight jobs that were
# obeying the halt as "8 subsystem(s) in a bad state" -- and it used to carry its own copy of the
# string. verify_math then had a row asserting the two copies matched, which could only compare
# them for real while the library was actually halted; on a healthy library both sides of that
# row collapsed to the same literal and it could not fail. Two files agreeing on a sentence by
# coincidence is the fault; one spelling in one place removes it rather than testing for it
# (lesson 14). Order 498dd8b128f7.
HALT_REFUSAL = "THE LIBRARY IS HALTED"

JANITOR, OPERATOR, SUPERVISOR, SAFETY, MANAGER, OWNER = range(6)
NAMES = {JANITOR: "JANITOR", OPERATOR: "OPERATOR", SUPERVISOR: "SUPERVISOR",
         SAFETY: "SAFETY", MANAGER: "MANAGER", OWNER: "OWNER"}
# The reverse map, so `escalate("OWNER", ...)` works as well as `escalate(OWNER, ...)`. Derived
# from NAMES rather than written out again: two hand-kept copies of one mapping is how they come
# to disagree, and this one decides which rung an alarm sounds at.
BY_NAME = {v: k for k, v in NAMES.items()}


class Refused(RuntimeError):
    """An OPERATOR- or SUPERVISOR-level stop: this unit or this source, not the library."""


class SystemHalted(RuntimeError):
    """The library is halted and is waiting for a person. Nothing may proceed."""


# --------------------------------------------------------------------------- the record


SRC_LOGS = os.path.join(HERE, "state", "escalations")

# WHAT EACH RUNG IS ALLOWED TO BE TOLD. A safety net carries only what its handler must act on.
# Passing the whole record upward is how an alarm becomes unreadable: the OWNER rung exists to
# buy one decision, and a decision drowned in transport detail is a decision not made. The
# janitor's log keeps EVERYTHING -- that is its job, and it is the only rung that gets the lot.
#
# `halt_landed` is admitted at the two rungs that can carry it: the janitor keeps everything, and
# an OWNER escalation whose halt file never appeared is an OWNER-rung fact in its own right. It
# is set by `escalate()` AFTER `_raise_halt` returns, so it is absent from the record the halt
# file itself is distilled from -- see the `level >= OWNER` arm.
#
# `recorded` is admitted at the same two rungs and for the same reason (order cd76813c39bc): it
# is `escalate()`'s answer to "did the janitor's rung actually take this down", set AFTER
# `_append_log` returns, so like `halt_landed` it is absent from the line the log itself is
# distilled from and present only where a record carrying it is briefed later. Admitting it on
# purpose is the whitelist working as documented, not a leak.
_FIELDS = {
    JANITOR:    ("at", "level_name", "code", "what", "source", "who", "evidence", "halt_landed",
                 "recorded"),
    OPERATOR:   ("at", "level_name", "code", "what", "source", "who"),
    SUPERVISOR: ("at", "level_name", "code", "what", "source"),
    SAFETY:     ("at", "level_name", "code", "what", "source"),
    MANAGER:    ("at", "level_name", "code", "what", "source", "who"),
    # `level_name` HERE TOO, and it was the one rung without it (order 7f7cceae27a5). Every
    # other tuple above carries it; OWNER's did not. `_append_log` writes the per-source history
    # with `brief(rec, rec.get("level", JANITOR))`, so in `state/escalations/<source>.log` a
    # SUPERVISOR or SAFETY entry about a source announced its rung and that source's MOST
    # SERIOUS entries did not. Not fail-open -- `state/escalation.log` is always briefed at
    # JANITOR and keeps the full picture -- but a person reading one source's own history had to
    # infer OWNER from the `code` string, and a hand-written `--raise-halt` code does not
    # reliably read as a rung. Purely additive: a whitelist gains a field the record already
    # carries.
    OWNER:      ("at", "level_name", "code", "what", "source", "evidence", "who", "halt_landed",
                 "recorded"),
}


def brief(rec, level):
    """The record as THIS rung should receive it -- nothing more.

    Deliberately a whitelist, not a blacklist: a field added to the record later must be
    admitted on purpose rather than leaking upward because nobody remembered to exclude it.
    """
    keep = _FIELDS.get(level, _FIELDS[JANITOR])
    return {k: rec[k] for k in keep if k in rec and rec[k] is not None}


_NAME_MAX = 60


def _safe_name(s):
    """A source name as a filename, and NEVER the same filename for two different sources.

    This returned `out[:60]`, and the result is used by `_append_log` as the per-source
    escalation log name: `state/escalations/<safe>.log`. "Every source is its own area of the
    park" is the doctrine this file opens with, and a truncating name silently merges two areas
    -- two sources agreeing in their first 60 sanitised characters write into ONE file, so the
    park map has fewer areas on it than the park has, and a person reading one source's log is
    reading another source's escalations without being told. That is not a display cap; it is a
    cap that changes where data is stored. The roll already runs close to it: `Kobold Press
    (Midgard Heroes Handbook, Midgard Worldbook)` sanitises to 57 characters, and the sources
    that collide are exactly the long parenthetical publisher-plus-title names, which are the
    ones most likely to share a prefix. Order e8cd908ce5e4.

    A length limit itself is kept -- a filename has real limits and 260-character paths are this
    machine's own recurring fault -- but the truncation is now made INJECTIVE by appending a
    digest of the whole sanitised name. Two sources sharing a prefix get two files, and the same
    source gets the same file every time (sha1 of the full name, not of the truncation, so the
    part that was cut is the part that disambiguates). Short names are untouched, so no existing
    log on disk is renamed.
    """
    out = "".join(c if (c.isalnum() or c in "-_") else "_" for c in str(s or "unscoped"))
    if len(out) > _NAME_MAX:
        out = out[:_NAME_MAX] + "-" + hashlib.sha1(out.encode("utf-8")).hexdigest()[:10]
    return out or "unscoped"


def _append(path, rec):
    """Append one line of JSON. Never the reason a caller dies.

    THROUGH `silence.append_line`, NOT A BUFFERED `open(path, "a")` (BUGS.md M38's last limb,
    open and verified since run #32). This wrote with `open(..., "a")` + `f.write`, which is a
    BUFFERED write: Python may split one line into several underlying writes, and two processes
    interleaving mid-line produce a row that parses as neither. That is the m62 torn-line class,
    measured on `state/model_metrics.jsonl` in run #24 and fixed there with this same helper.

    The exposure here is the same shape and the stakes are higher. `state/escalation.log` is the
    JANITOR'S RUNG -- the one log this module's own docstring says "always holds the whole story
    even when the top rung fires" -- and every process that can escalate appends to it, which is
    every standing job. A torn line in the metrics ledger costs a data point; a torn line here
    costs the record of why the library stopped, at the moment somebody is reading it to find
    out. One `os.write` to an `O_APPEND` descriptor is one syscall, and for a sub-page JSON line
    that is the difference between interleaved-and-corrupt and interleaved-but-whole.

    The verdict is still returned truthfully: `append_line` answers True/False exactly as this
    did, so `_append_log`'s caller and the drill nets that assert on it are unaffected.
    """
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return silence.append_line(path, json.dumps(rec, ensure_ascii=False))
    except Exception:
        silence.note("escalation.py:log")
        return False


def _append_log(rec):
    """The janitor's rung: the FULL record, append-only, on duty at all hours.

    Written in three places on purpose, because a safety record that exists once exists until the
    first bad write:
      1. state/escalation.log        every rung, every source, whole records
      2. state/escalations/<src>.log this source's own file -- its area of the park, distilled
                                     to what a person looking at THAT source needs
      3. state/failures.json         via health.record, where the existing tooling already looks

    -> True only when EVERY append this record was owed actually LANDED. It used to answer for
    the first one alone (order cd76813c39bc): `_append` is careful to return the truth, and the
    per-source append's answer was dropped on the floor one line later. `state/escalations/<src>
    .log` is the "area of the park" record this module's whole doctrine rests on, and its
    verdict was not merely ignored by the caller -- it never left this frame. A locked `state/`
    directory, a full disk or a Norton object lock on one of the two paths (all ordinary on this
    machine) lost that half of the janitor's rung with nothing anywhere able to say so.

    The two appends are BOTH attempted before the verdict is combined -- the per-source call is
    written first in the `and` deliberately, because short-circuiting on a failed LOG write
    would stop writing the very record this function exists to keep in more than one place.
    """
    ok = _append(LOG, brief(rec, JANITOR))
    src = rec.get("source")
    if src:
        ok = _append(os.path.join(SRC_LOGS, _safe_name(src) + ".log"),
                     brief(rec, rec.get("level", JANITOR))) and ok
    return ok


def escalate(level, code, what, evidence=None, source=None, who=None):
    """Report something amiss at `level`, recording it at every rung beneath as well.

    Returns the record. Raising is the CALLER's decision for rungs 1-4 -- this function does not
    decide control flow for them, because a guard that both detects and unwinds is hard to test.
    Rung 5 is the exception: OWNER writes the halt file, because a halt nobody wrote down is a
    halt that ends when the process does.
    """
    # ACCEPT THE NAME AS WELL AS THE NUMBER, and the reason is the worst kind of bug report.
    # `escalate("OWNER", ...)` raised `ValueError: invalid literal for int() with base 10:
    # 'OWNER'` -- and every call site that made this mistake was on an ERROR PATH. Five of them
    # were written on 2026-08-25 in `mutate.py` and `codewatch.py`, and not one could fire
    # during normal operation, so all five sat green until the first genuine fault reached them.
    # A mutation run then found a real problem, tried to report it, and **the alarm crashed
    # instead of sounding**, taking the whole run's results with it.
    #
    # The call sites were fixed. This is the other half, and it is the half that matters: an API
    # whose misuse is only ever discovered during an emergency is an API that will be misused
    # again, by someone who is also busy. `escalate(OWNER, ...)` and `escalate("OWNER", ...)`
    # now mean the same thing.
    #
    # AN UNRECOGNISABLE LEVEL LANDS AT **MANAGER**, NOT OWNER, and the first version of this
    # fix got that wrong. Fail-closed says an unknown answer must stop something -- but
    # resolving a typo to OWNER means `escalate("Owner ", ...)` or `escalate("MANGER", ...)`
    # **halts the entire library over a misspelling**, which is a denial of service anyone can
    # trigger by accident and is exactly the shape of over-eager safety this project keeps
    # having to walk back. MANAGER stops the subsystem, which is a real refusal and a loud one,
    # without handing a slip of the keyboard the power to close the park. The bad value travels
    # in the evidence so it is fixable rather than merely survived.
    _bad_level = None
    if isinstance(level, str):
        _named = BY_NAME.get(level.strip().upper())
        if _named is None:
            _bad_level, level = level, MANAGER
        else:
            level = _named
    # A NON-INTEGRAL FLOAT IS AN UNRECOGNISED LEVEL TOO, and `int()` was silently ROUNDING IT
    # DOWN INSTEAD (order 762256b4b844, owner ruling 2026-09-08 "Who may lift a halt or a
    # subsystem stop"). Every other malformed input above and below this line lands at MANAGER
    # with `unrecognised_level` in the evidence -- a bad string, None, an out-of-range int -- so
    # the caller can see what they typed. A float walked straight past all of it, because
    # `int(2.7)` does not raise: it returns 2, and `escalate(2.7, ...)` became a QUIET
    # `escalate(OPERATOR, ...)`, one rung of a six-rung chain chosen by a truncation nobody was
    # told about. That is the exact shape this whole block exists to refuse.
    #
    # `is_integer()` IS HONOURED, so `escalate(3.0, ...)` still means SAFETY. 3.0 names a rung
    # exactly; 2.7 does not name one at all, and the difference is not a matter of taste. Only
    # `float` is asked -- `bool` is an `int` subclass and `True` is rung 1 by the same arithmetic
    # every other integral caller uses, so nothing here changes for it.
    if isinstance(level, float) and not level.is_integer():
        _bad_level, level = repr(level), MANAGER
    try:
        level = int(level)
    except (TypeError, ValueError):
        _bad_level, level = repr(level), MANAGER
    if not (JANITOR <= level <= OWNER):
        _bad_level, level = level, MANAGER
    if _bad_level is not None:
        evidence = dict(evidence or {}) if isinstance(evidence, dict) else {"was": evidence}
        evidence["unrecognised_level"] = str(_bad_level)
        evidence["note"] = ("the caller named a rung that does not exist; recorded at MANAGER "
                            "so a typo cannot halt the library")
    rec = {"at": time.time(), "level": int(level), "level_name": NAMES.get(level, str(level)),
           "code": str(code), "what": str(what), "source": source,
           "who": who or os.path.basename(sys.argv[0] or "?"),
           "evidence": evidence if evidence is None or isinstance(evidence, (dict, list))
                       else str(evidence)}
    # THE VERDICT TRAVELS, exactly as `halt_landed` does at OWNER and `stop_recorded` does at
    # MANAGER (order cd76813c39bc). This was a bare `_append_log(rec)` -- no assignment, no
    # branch, nothing placed on the record -- so the record handed back to whoever raised the
    # alarm was byte-identical whether the alarm had been written down or lost. At rungs 1-4
    # that is the whole enforcement: OPERATOR, SUPERVISOR and SAFETY do not raise a halt and do
    # not write a state file, so if the append is lost the escalation leaves no trace a person
    # can find, and the caller is told nothing.
    #
    # SAID ON stderr WHEN IT IS False, because by construction it cannot be said in the log --
    # the log is the thing that just failed. Mirrors the HALT_NOT_RAISED corroboration line in
    # the `level >= OWNER` arm below, which exists for the identical shape one rung up.
    recorded = _append_log(rec)
    rec["recorded"] = bool(recorded)
    if not recorded:
        sys.stderr.write(
            "ESCALATION NOT RECORDED — %s at %s could not be appended to the janitor's log "
            "(state/escalation.log and/or state/escalations/<source>.log). The alarm was "
            "raised and there is no written trace of it: %s\n"
            % (rec["code"], rec["level_name"], rec["what"]))
    try:
        import health
        # THE SUBJECT TRAVELS, so a REHEARSAL can be told from a FAULT (order 5bbbb65e7787).
        # `health.is_selftest` matches `__drill[A-Za-z0-9_]*__` against the composed key AND
        # against `subject`, and until now only the key was offered. That caught six of the
        # seven synthetic rows this shift, because most drill rehearsals embed the marker in a
        # code or a source name that ends up inside the key. The seventh --
        # `escalation:SUPERVISOR:DRILL_AREA:drill: one area closing`, whose synthetic marker is
        # in `source` and nowhere in the key -- could not be caught by ANY reading of the key,
        # so `state/failures.json`, the ledger a person reads to find real faults, carried a
        # drill's own rehearsal as one. Passing the source is the whole fix.
        health.record("escalation:%s:%s" % (NAMES.get(level, level), code), rec["what"],
                      subject=rec.get("source"))
    except Exception:
        silence.note("escalation.py:health")
    # EVERY ESCALATION BECOMES A WORK ORDER (owner ruling 2026-08-25). The chain says how bad a
    # thing is and who may stop the line; the work order says WHO FIXES IT and disappears when
    # they have. Two questions, deliberately two files -- collapsing them gives a queue where
    # everything is urgent and nothing is addressed.
    #
    # The rung-to-handler map is intentionally NOT one-to-one. An OPERATOR-level refusal (one
    # block failed) is mechanical and belongs to the local model; an OWNER-level halt is a
    # library-wide invariant and belongs to a person. Severity and addressee are different axes.
    try:
        import workorders as WO
        handler = {JANITOR: "LOCAL", OPERATOR: "LOCAL", SUPERVISOR: "BOTS",
                   SAFETY: "RUN", MANAGER: "RUN", OWNER: "SESSION"}.get(level, "RUN")
        severity = {JANITOR: "INFO", OPERATOR: "MINOR", SUPERVISOR: "MINOR",
                    SAFETY: "MAJOR", MANAGER: "MAJOR", OWNER: "BLOCKING"}.get(level, "MAJOR")
        WO.file_order(rec["code"], rec["what"], handler, severity,
                      where=rec.get("source") or "", evidence=rec.get("evidence"),
                      found_by=rec.get("who") or "escalation")
    except Exception:
        silence.note("escalation.py:workorder")
    if level >= OWNER:
        # THE VERDICT USED TO STOP ONE FRAME SHORT OF HERE. `_raise_halt` was fixed in run #34 to
        # return whether the halt file actually LANDED -- on Windows the rename is DENIED while
        # any reader holds the target, and this file has readers on their own clocks (every
        # `assert_clear` opens it, the dashboard polls it). This call site then threw that answer
        # away: `_raise_halt(rec)` / `return rec`. So the record handed back to the actor that
        # escalated to OWNER could not distinguish a halt that took from a halt that never
        # appeared, and when it never appears every other process's `assert_clear()` finds no
        # halt file and carries straight on.
        #
        # Two changes, both required. The verdict goes ON the returned record, so a caller can
        # see it; and when it is False a SECOND janitor line is appended, because `_append_log`
        # above already ran BEFORE the write was attempted -- the first line says an OWNER fault
        # was raised, this one says the top rung did not actually engage. The janitor's rung is
        # where the whole story is supposed to live even when the top rung fires, and until now
        # this half of the story was only a generic silence.note counter and a stderr line that
        # nothing running under CREATE_NO_WINDOW has a reader for.
        landed = _raise_halt(rec)
        rec["halt_landed"] = bool(landed)
        if not landed:
            _append_log({"at": time.time(), "level": OWNER, "level_name": "OWNER",
                         "code": "HALT_NOT_RAISED",
                         "what": "the halt for %s was escalated to OWNER but state/HALT.json did "
                                 "NOT land, so every other process's assert_clear() will find no "
                                 "halt and carry on: %s" % (rec["code"], rec["what"]),
                         "source": rec.get("source"), "who": rec.get("who"),
                         "evidence": {"halt_landed": False, "of_code": rec["code"]},
                         "halt_landed": False})
    return rec


# --------------------------------------------------------------------------- the halt

# How long a halt lock file may sit untouched before the next writer treats it as abandoned and
# steals it. A halt write is a handful of milliseconds of JSON plus a rename; anything holding
# the lock for a minute is a process that died between the create and the remove, and a halt
# that cannot be raised because a dead process left a file behind is the worst outcome this
# module has. Same staleness idiom as `codewatch.LOCK_STALE_SECONDS` and `mutate`'s run lock.
HALT_LOCK_STALE_SECONDS = 60.0

# How long a writer waits for the lock before giving up and raising the halt UNLOCKED. Deliberately
# short: the lock is an optimisation on the compare-and-swap, never a precondition for it.
HALT_LOCK_ATTEMPTS = 40
HALT_LOCK_WAIT = 0.05


@contextlib.contextmanager
def _halt_lock():
    """Serialise the read-modify-write of the halt file across processes. FAILS OPEN.

    WHY (order 97cc0dc43ca7, owner ruling 2026-09-08 "The last checks before an irreversible
    outward act"). `_raise_halt` is compare-and-swapped and verified by read-back, and that
    measured a 25x improvement -- two concurrent first halts lost a fault in 1 trial of 25 where
    the unguarded version lost one in 25 of 25 -- but it did not close the race.
    `silence.replace_if_unchanged` re-reads its digest immediately before `os.replace`, and that
    pair is not atomic, so a writer can still land inside the window; the retry is bounded at
    STOP_CAS_ATTEMPTS, which four contending writers can exhaust. `O_CREAT|O_EXCL` is atomic on
    Windows and POSIX alike, so creating the lock file IS the mutual exclusion, with no
    check-then-act window for two processes to both win.

    AND IT FAILS **OPEN**, WHICH IS THE WHOLE DESIGN DECISION AND NOT AN OVERSIGHT. Every other
    layer in this module answers "I don't know" with STOP. This one must not, and the owner's
    ruling says so in as many words: fail-closed halt-write locking was considered and REJECTED
    as weakening a safety. A halt that cannot be raised because a lock file is stuck is far worse
    than a lost corroboration entry -- the corroboration is an `also` line, the halt is the
    library stopping. So if the lock cannot be taken inside the budget the write proceeds
    UNLOCKED, exactly as it did before this function existed, and the failure is noted.
    The lock only ever REMOVES a race; it can never add a refusal.

    Keyed off `HALT_FILE` AT CALL TIME, not at import, so a probe that redirects `HALT_FILE` to
    a scratch directory gets a scratch lock with it and never contends with the live library.
    """
    lock = HALT_FILE + ".lock"
    held = False
    for _ in range(HALT_LOCK_ATTEMPTS):
        try:
            os.makedirs(os.path.dirname(lock), exist_ok=True)
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            held = True
            break
        except FileExistsError:
            # STALENESS STEAL. A lock whose file has not been touched inside the window is a
            # lock nobody is holding: the process that made it died between the create and the
            # remove. Steal it and try again rather than wait out a corpse.
            try:
                if time.time() - os.path.getmtime(lock) > HALT_LOCK_STALE_SECONDS:
                    os.remove(lock)
                    continue
            except OSError:
                pass
            time.sleep(HALT_LOCK_WAIT)
        except OSError:
            # The lock could not be created for a reason that is not contention -- a read-only
            # or missing state/ directory, an object lock. Nothing to wait for. Fail open now.
            break
    if not held:
        silence.note("escalation.py:halt-lock-not-taken")
        sys.stderr.write(
            "HALT LOCK NOT TAKEN (%s) — raising the halt UNLOCKED rather than not raising it. "
            "A corroborating fault may be lost to a concurrent writer; the halt itself is "
            "not.\n" % lock)
        yield False
        return
    try:
        yield True
    finally:
        with contextlib.suppress(OSError):
            os.remove(lock)


def _raise_halt(rec):
    """Write the halt. Whole-file, atomic, and never overwritten once standing.

    A second fault while halted is appended as corroboration rather than replacing the first --
    the FIRST thing that went wrong is the one a person needs to see, and a later, louder symptom
    must not bury it.
    """
    # COMPARE-AND-SWAPPED, because this is a READ-MODIFY-WRITE on the one ledger that must never
    # lose a fault (BUGS.md M38's remaining limb, open and verified since run #32).
    #
    # The read below, the merge under it and the write at the bottom were three separate steps
    # with nothing between them. Two processes raising a FIRST halt at the same moment each read
    # "no halt", each built a fresh payload, and whichever renamed second replaced the other's --
    # so one OWNER fault vanished, silently, with a successful write. That is the corroboration
    # rule inverted: the `also` list exists precisely so a second fault cannot bury the first, and
    # without a CAS the race bypassed it entirely. It is not hypothetical here; the drill, the
    # keeper, the foreman and nine standing jobs can all reach `escalate(OWNER, ...)`, and a
    # library-wide invariant breaking tends to break for several of them at once.
    #
    # The digest is taken BEFORE the read, the same order and for the same reason as
    # `_write_stopped` and `binding_health._land_cas` in this same tree: read first and the digest
    # would match disk while the copy in hand is already stale, certifying the lost update instead
    # of catching it. `None` asserts the file did not exist when it was read, which is exactly the
    # first-halt case this race is about.
    # RETRIED ON ANY REFUSAL, not on a parsed reason. The first version of this loop broke out
    # unless `why == "changed"` -- a token `silence.replace_if_unchanged` never returns. It
    # answers a SENTENCE ("... changed under this writer (expected X, found Y) -- refusing to
    # ..."), so the equality was false on every path, the loop ran once, and the loser of a race
    # reported its halt as not raised instead of appending it as corroboration. The race net
    # caught that immediately, which is the whole reason it was written.
    #
    # Matching `stop_subsystem`'s loop in this same file: go round on ANY failure, bounded by
    # STOP_CAS_ATTEMPTS. A digest mismatch means somebody landed first and the next pass appends
    # to their `also`; a transient denial means a reader was holding the file and the next pass
    # may get it. Both want another attempt, and after five neither is transient any more.
    #
    # AND THE WHOLE LOOP RUNS UNDER AN EXCLUSIVE-CREATE LOCK (order 97cc0dc43ca7, owner ruling
    # 2026-09-08). The compare-and-swap narrows the lost-fault race by 25x and cannot close it,
    # for the reason spelled out in `_halt_lock`. The lock closes it by making the read, the
    # merge and the rename one section that only one writer is inside. It FAILS OPEN: when it
    # cannot be taken, `_halt_lock` yields False and every line below runs exactly as it did
    # before, because a halt that a stuck lock file can prevent is not a halt.
    landed, why = False, "not attempted"
    with _halt_lock():
        for _attempt in range(STOP_CAS_ATTEMPTS):
            expected = silence.digest_of(HALT_FILE)
            landed, why = _land_halt(rec, expected)
            if landed and _halt_file_records(rec):
                return True
            # READ BACK, AND DO NOT TRUST `landed` ALONE. The compare-and-swap NARROWS this
            # race and cannot close it: `replace_if_unchanged` re-reads the digest immediately
            # before its own `os.replace`, so there is still a window between that read and the
            # rename in which another writer can land. Two threads released together from a
            # barrier hit it, and BOTH
            # reported `halt_landed: True` while the file held only one of their faults -- which is
            # the original defect wearing the fix's clothes, and strictly worse than the defect
            # because now there is a verdict saying it did not happen.
            #
            # Verifying convergence is what actually closes it. If our fault is not in the file we
            # just wrote, somebody landed over us; go round, and this pass reads THEIR halt and
            # appends ours to its `also`. That terminates: each pass either finds our record
            # or finds a newer halt to attach it to, and the loop is bounded.
            landed = False
    # ONLY NOW IS IT LOUD. `_land_halt` is silent about a single refused attempt on purpose --
    # printing "CANNOT WRITE HALT FILE" for the intermediate pass of a working compare-and-swap
    # would be an alarm about the mechanism succeeding.
    silence.note("escalation.py:halt-write-denied")
    sys.stderr.write("CANNOT WRITE HALT FILE after %d attempts (%s) — %s: %s\n"
                     % (STOP_CAS_ATTEMPTS, why, rec["code"], rec["what"]))
    return landed


def _halt_file_records(rec):
    """Is THIS fault actually in the halt file now? -> bool.

    Identity is (code, at): `code` alone is not enough because a retrying job can raise the same
    code twice, and `at` alone is not enough because it is a float somebody could round. The
    fault counts as recorded whether it is the STANDING halt or one of its corroborating `also`
    entries -- both are "the record kept it", which is the only property that matters here.
    """
    cur = _read_halt_raw()
    if not isinstance(cur, dict):
        return False
    mine = (str(rec.get("code")), rec.get("at"))
    if (str(cur.get("code")), cur.get("raised_at")) == mine:
        return True
    return any((str(x.get("code")), x.get("at")) == mine
               for x in (cur.get("also") or []) if isinstance(x, dict))


def _land_halt(rec, expected):
    """One compare-and-swapped attempt at the halt file. -> (landed, why)."""
    cur = _read_halt_raw()
    if isinstance(cur, dict) and not cur.get("cleared", False):
        cur.setdefault("also", []).append(brief(rec, OWNER))
        payload = cur
    else:
        # DISTILLED for the rung that reads it. The halt file is what a person opens at the
        # worst moment; it carries the decision fields and nothing else. Everything discarded
        # here is still in state/escalation.log, in full, for whoever wants the detail.
        top = brief(rec, OWNER)
        payload = {"raised_at": top.get("at"), "code": top.get("code"), "what": top.get("what"),
                   "evidence": top.get("evidence"), "source": top.get("source"),
                   "by": top.get("who"), "cleared": False, "ruling": None, "also": []}
    # A DENIED RENAME IS A HALT THAT WAS NEVER RAISED, and until run #34 it was silent. The
    # verdict from `replace_retry` was discarded here, so on Windows -- where the rename is
    # DENIED while any reader holds the target, and this file has readers on their own clocks
    # (every `assert_clear` opens it, the dashboard polls it) -- the halt file simply did not
    # appear. No exception, no stderr, and `escalate()` returned normally. The library would
    # have carried on with its own alarm unrecorded, which is the precise failure the whole
    # escalation chain exists to make impossible.
    #
    # The `except` arm below was already loud, correctly, for the case where the WRITE throws.
    # It just never covered the case where the write succeeds and the LANDING is refused.
    landed, why = False, "not attempted"
    try:
        os.makedirs(os.path.dirname(HALT_FILE), exist_ok=True)
        # Through a temp + `replace_if_unchanged` rather than `write_json`, so the rename is
        # refused when the target moved under us. `write_json` retries a DENIED rename, which is
        # the right behaviour for a reader holding the file and the wrong one for a competing
        # WRITER -- it would land the stale payload just as happily.
        import threading as _th
        tmp = "%s.%d.%d.tmp" % (HALT_FILE, os.getpid(), _th.get_ident())
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=1, ensure_ascii=False)
        landed, why = silence.replace_if_unchanged(tmp, HALT_FILE, expected)
        if not landed:
            # Silent: this is ONE attempt of a compare-and-swap and the caller retries. It is
            # `_raise_halt` that decides the attempts are exhausted, and `_raise_halt` that is
            # loud about it.
            _unlink(tmp)
            return False, why
    except Exception:
        # A halt that cannot be written is the worst case, so it is the ONE thing that is
        # allowed to be loud on stderr as well as recorded.
        silence.note("escalation.py:halt-write")
        sys.stderr.write("CANNOT WRITE HALT FILE — %s: %s\n" % (rec["code"], rec["what"]))
        return False, "raised"
    return landed, why


def _unreadable_halt(why):
    """The fail-closed stand-in record. A halt file we cannot READ AS A RECORD is not an absent
    halt; it is a halt whose reason we have lost, which is strictly more alarming, not less."""
    return {"cleared": False, "code": "HALT_FILE_UNREADABLE",
            "what": "state/HALT.json exists but %s. Treating the library as halted: a halt "
                    "that a corrupted file can lift is not a halt." % why,
            "by": "escalation", "unreadable": True}


def _read_halt_raw():
    """-> the halt record, None when there is no halt file, or the fail-closed stand-in.

    IT ALWAYS RETURNS None OR A DICT, and until now it did not. `except Exception` wrapped the
    `json.load` and nothing after it, so a HALT.json holding VALID JSON OF THE WRONG SHAPE --
    `[]`, `null`, `"halted"`, a bare number, which is what a half-written or hand-edited file
    most easily becomes -- parsed cleanly and was handed straight back. Every caller then did
    `rec.get("cleared")` on a list or a string and got AttributeError instead of the documented
    fail-closed `SystemHalted`.

    That is the fail-closed promise breaking on its own edge case. `assert_clear` would raise
    the wrong exception type, and `verify_math`'s halt probe catches `SystemHalted` NARROWLY --
    so the one battery check whose job is to report on the halt would itself die uncaught, and
    the report about the alarm would be replaced by a traceback. Shape is now part of "can we
    read it", which is what the docstring below the `except` always claimed it was.
    """
    try:
        with open(HALT_FILE, encoding="utf-8") as f:
            rec = json.load(f)
    except FileNotFoundError:
        return None
    except Exception:
        return _unreadable_halt("does not parse")
    if rec is None:
        # `null` is not "no halt". A file that exists holds a claim; an EMPTY claim is the
        # unreadable case, not the absent one -- absence is the file not being there at all,
        # which is the `FileNotFoundError` arm above and the only thing allowed to mean clear.
        return _unreadable_halt("holds `null` rather than a halt record")
    if not isinstance(rec, dict):
        return _unreadable_halt("parses as %s rather than a halt record" % type(rec).__name__)
    return rec


def status():
    """-> (halted: bool, record or None)."""
    rec = _read_halt_raw()
    if rec is None:
        return False, None
    return (not rec.get("cleared", False)), rec


STOPPED = os.path.join(HERE, "state", "STOPPED.json")

# THE LIBRARY'S REAL STOP LEDGER, remembered at import so a redirection can be RECOGNISED.
# `drill._esc_sandbox` points `STOPPED` at a scratch directory before it drives this module, and
# `_a_probe_release` below uses the difference to tell a probe cleaning up after itself from a
# real rung-4 stop being lifted. Captured here rather than recomputed, because the whole value of
# the comparison is that it names the path this process STARTED with.
_REAL_STOPPED = STOPPED

# How many times a read-modify-write over STOPPED.json may re-read and swap again before it is
# reported as unrecordable. Same number as `binding_health.CAS_ATTEMPTS`, which guards the same
# shape on the other shared map this project keeps.
STOP_CAS_ATTEMPTS = 5


def stop_subsystem(name, reason, who="?", evidence=None):
    """Rung 4, made DURABLE. Stop one subsystem until a person resumes it. -> the record.

    THE GAP THIS CLOSES, found 2026-08-26 by the nightly run and proved on the worst available
    example. A maintenance run stopped `catalogue_web --recatalogue` at 22:5x because it was
    NULLING SYNTHESIS BLOCKS -- 26 sources in twenty-four hours, DC among them at 44,958
    entries. At 23:21 the keeper started it again. **The stop lasted twenty-five minutes and
    no person was ever told.**

    The chain had recorded that rung 4 fired. Nothing read it. So of five rungs exactly ONE --
    the OWNER halt -- could actually stop anything, and a MANAGER stop was a note in a file that
    the supervisor whose entire job is keeping jobs up never opened. Escalating to a rung that
    cannot enforce itself is the same as escalating to nobody, and it is worse than nobody
    because it reads as action taken.

    A stop here is deliberately NARROW: one subsystem closes, the rest of the library keeps
    running, which is the whole point of having a rung below the halt. It is also deliberately
    STICKY: `resume_subsystem` demands a written ruling, as `clear` does -- and a longer one, 20
    characters against 12 (order 8b1b81bcfee4; this sentence also used to claim the two bars
    matched) -- because the thing that undid the last one was an automated actor with good
    intentions and a restart timer.
    """
    rec = escalate(MANAGER, "SUBSYSTEM_STOPPED",
                   "%s stopped: %s" % (name, reason), evidence=evidence,
                   source=name, who=who)
    # A TRANSIENT RENAME DENIAL MUST NOT HALT THE LIBRARY (order 4f290dae34ef). This was one
    # unretried `os.replace` inside `try: ... except Exception:` whose answer to ANY failure was
    # `escalate(OWNER, ...)`. On Windows the rename is DENIED while any reader holds the target,
    # and `subsystem_stopped()` is exactly such a reader, polled by the keeper on its own clock
    # -- so the ordinary case that every other write in this project retries five times around
    # closed the whole park. That is the over-eager safety shape `escalate()`'s own comment walks
    # back for a misspelled rung name: a denial of service anyone can trigger by accident.
    #
    # The refusal is not weakened, only made truthful: the OWNER escalation now fires when the
    # RETRYING, compare-and-swapped write genuinely could not land, which is the condition its
    # sentence has always claimed to describe.
    landed, detail = False, "not attempted"
    for _ in range(STOP_CAS_ATTEMPTS):
        # THE DIGEST IS TAKEN BEFORE THE READ, the same order and for the same reason as
        # `binding_health._land_cas`: read first and the digest would match disk while the copy
        # in hand is already stale, certifying the lost update instead of catching it.
        expected = silence.digest_of(STOPPED)
        try:
            doc = _read_stopped()
        except Exception:
            silence.note("escalation.py:stop-read")
            landed, detail = False, "state/STOPPED.json could not be read at all"
            break
        if "__unreadable__" in doc:
            # NEVER OVERWRITE A LEDGER THAT COULD NOT BE READ. The old code wrote straight
            # through this case, landing the `__unreadable__` marker itself into the file and
            # destroying whatever standing stops it held -- the same fault
            # `binding_health.quarantine` was repaired for (order dd3ff361db49). An unrecordable
            # stop IS the OWNER case, so it falls out of the loop into the escalation below.
            landed, detail = False, ("state/STOPPED.json could not be read as a map of stops, so "
                                     "this stop cannot be added to the stops already in it "
                                     "without destroying them")
            break
        doc[str(name)] = {"at": time.time(), "reason": str(reason), "by": str(who),
                          "evidence": evidence if isinstance(evidence, (dict, list)) else None}
        try:
            landed, detail = _write_stopped(doc, expected)
        except Exception:
            # `_write_stopped` re-raises whatever stopped the temp copy being written. A stop is
            # already an emergency; it must not also become a traceback at its caller.
            silence.note("escalation.py:stop-write")
            landed, detail = False, "the temp copy could not be written"
        if landed:
            break
    if not landed:
        # A stop that cannot be written down is a stop nothing else can honour, and the caller
        # must not be left believing the subsystem is closed. Raised to OWNER: this is the one
        # failure of the MANAGER rung that genuinely does need everything to halt.
        escalate(OWNER, "SUBSYSTEM_STOP_UNRECORDABLE",
                 "could not record a MANAGER stop for %s (%s); the keeper will restart it"
                 % (name, detail), source=name, who=who)
        # AND THE FALSE `SUBSYSTEM_STOPPED` ORDER GOES WITH IT (order b1ffe2a0e293).
        #
        # The MANAGER escalation at the top of this function ran BEFORE any disk was touched,
        # and `escalate` turns every escalation into a work order -- so a MAJOR order keyed
        # (SUBSYSTEM_STOPPED, name) and addressed to RUN already exists, saying this subsystem
        # is stopped. It is not: the write did not land and state/STOPPED.json does not hold
        # the name. `resume_subsystem` is the only sanctioned path that closes that order, and
        # it returns early on `if str(name) not in doc` long before reaching its resolve_code
        # -- correctly, because refusing to write over a map that does not hold the name is
        # right -- so nothing anywhere could ever close this one. It is the same leak the
        # comment in `resume_subsystem` documents and repairs, entered through the failed-write
        # door instead of the resume door, with the same measured precedent: orders
        # 16d29e625d29 (pipeline) and a4b8fb03956e (feats) stood open against an empty
        # STOPPED.json. A false MAJOR is not clutter -- this rung's whole worth is that a real
        # stop can be FOUND in the queue, and it cannot be found among false copies of itself.
        #
        # THE RE-READ IS NOT OPTIONAL AND IS NOT A TIDY-UP. `landed` False does not by itself
        # prove the subsystem is running: if this name was ALREADY stopped by an earlier call
        # that did land, the order is TRUE and closing it would erase a live alarm. So the
        # ledger is asked, and `subsystem_stopped` fails closed -- an unreadable STOPPED.json
        # answers "stopped", which leaves the order standing, which is the safe reading. The
        # order is closed only where the ledger positively shows the name absent.
        #
        # Guarded in try/except with a silence.note, exactly as the resolve in
        # `resume_subsystem` is: a queue that will not accept the closure must never take the
        # OWNER escalation above down with it. Nothing here lifts anything -- no halt is
        # cleared, no stop is removed, no refusal is relaxed; the OWNER rung has already fired
        # and stands. This closes a claim that was never true.
        try:
            _still_stopped, _ = subsystem_stopped(name)
        except Exception:
            silence.note("escalation.py:stop-unlanded-recheck")
            _still_stopped = True        # cannot tell -> leave the order standing
        if not _still_stopped:
            try:
                import workorders as WO
                WO.resolve_code("SUBSYSTEM_STOPPED",
                                "stop was escalated but never recorded (%s); the subsystem is "
                                "NOT stopped" % detail, where=str(name), by=str(who))
            except Exception:
                silence.note("escalation.py:stop-unlanded-order")
    # THE VERDICT TRAVELS ON THE RECORD, exactly as `halt_landed` does one rung up, so a caller
    # can tell an attempted stop from a recorded one without re-reading the file.
    rec["stop_recorded"] = bool(landed)
    return rec


def _read_stopped():
    try:
        with open(STOPPED, encoding="utf-8") as f:
            d = json.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        # UNREADABLE MEANS STOPPED, for everything. The file only exists to say what must not
        # run, so failing to read it cannot be permission to run things.
        return {"__unreadable__": {"reason": "STOPPED.json could not be read", "at": time.time()}}
    if not isinstance(d, dict):
        # THE ONE PATH THAT FAILED OPEN, in the module whose three required properties are
        # INDEPENDENT, FAIL CLOSED and PROVEN. This read `return d if isinstance(d, dict) else {}`
        # -- so a STOPPED.json that is valid JSON but not an object (a list, a string, a number)
        # became an EMPTY MAPPING, and `subsystem_stopped()` then reported NOT STOPPED for every
        # subsystem in the library. The handler directly above promises the opposite in capitals,
        # and the two disagreed: a file that could not be PARSED stopped everything, while a file
        # that parsed to the wrong shape stopped nothing.
        #
        # Wrong-shape is not better evidence than unparseable. It is the same fact -- this file
        # does not say what it is supposed to say -- so it gets the same answer. Found by the
        # run #36 whole-tree sweep (batch 13) and reproduced live before the change.
        return {"__unreadable__": {"reason": "STOPPED.json is %s, not an object -- a MANAGER "
                                             "stop cannot be read from it" % type(d).__name__,
                                   "at": time.time()}}
    return d


def _unlink(path):
    """Remove a scratch file, and never let the removal itself become the failure."""
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except Exception:
        silence.note("escalation.py:tmp-not-removed")


def _write_stopped(doc, expected_digest=None):
    """Land the stopped-subsystems map. -> (landed, reason). Order 4f290dae34ef.

    THIS WAS THE ONLY WRITE IN THIS MODULE THAT DID NOT RETRY A DENIED RENAME. It was a
    hand-rolled `tmp = STOPPED + '.%d.tmp' % os.getpid()` followed by a bare `os.replace`, while
    `_raise_halt` and `clear()` twenty lines either side both go through `silence`, and the
    comments beside them spell out why: on Windows the rename is DENIED while any reader holds
    the target. `subsystem_stopped()` is exactly such a reader and the keeper polls it on its
    own clock, so the destination is routinely open. The cost of the omission was paid one
    caller up -- `stop_subsystem` answered the denial with an OWNER halt of the entire library,
    and `resume_subsystem` did not catch it at all, leaving an uncaught PermissionError with the
    subsystem still stopped on disk and its work order still open.

    AND IT IS A COMPARE-AND-SWAP, because both callers are READ-MODIFY-WRITE over a map two
    processes share. `expected_digest` is taken BEFORE the caller reads the file, exactly as
    `binding_health.quarantine`/`release` take theirs: two concurrent `stop_subsystem` calls
    each read the map, each add their own key, and whichever renames second lands a snapshot
    taken before the other's stop existed. That write SUCCEEDS, so nothing reports it, and the
    lost stop looks exactly like a subsystem that was never stopped -- which is the failure this
    whole rung was added for. `None` asserts the file did not exist when it was read.

    The temp name carries pid AND thread, which the old one did not: two writers otherwise
    collide on the temp file itself and the loser can land a half-written map.
    """
    import threading as _th
    os.makedirs(os.path.dirname(STOPPED), exist_ok=True)
    tmp = "%s.%d.%d.tmp" % (STOPPED, os.getpid(), _th.get_ident())
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            # `ensure_ascii=False` with an explicit utf-8 handle, matching `binding_health._land`:
            # `_read_stopped` opens this file as utf-8, so the two ends now agree by construction.
            json.dump(doc, f, indent=2, ensure_ascii=False)
    except Exception:
        _unlink(tmp)
        raise
    ok, why = silence.replace_if_unchanged(tmp, STOPPED, expected_digest)
    if not ok:
        # `replace_if_unchanged` leaves the temp where it is on a refusal, and litter beside a
        # shared state file is its own small fault.
        _unlink(tmp)
    return ok, why


def subsystem_stopped(name):
    """-> (bool, reason). Has a person-or-rung-4 closed this subsystem?

    Fails CLOSED: an unreadable ledger reports every subsystem stopped, because the only thing
    this file says is what must not run.
    """
    doc = _read_stopped()
    if "__unreadable__" in doc:
        return True, doc["__unreadable__"]["reason"]
    hit = doc.get(str(name))
    if not hit:
        return False, ""
    return True, "%s (by %s)" % (hit.get("reason", "no reason recorded"), hit.get("by", "?"))


def _a_probe_release(name):
    """Is this resume a DRILL PROBE cleaning up after itself, rather than a real rung-4 lift?

    THE PRIVATE, TEST-ONLY RELEASE PATH the owner's ruling of 2026-09-08 asked for, "so drill's
    three probes do not leave orphaned stops". The person check directly above is the real
    guard; this is the narrow, structural exemption from it, and it is deliberately not a flag a
    caller can set, because a flag is a guard anybody can switch off by passing True.

    TWO CONDITIONS, EITHER OF WHICH MAKES THIS PROVABLY NOT A REAL SUBSYSTEM:

      1. THE LEDGER IS NOT THE LIBRARY'S. `drill._esc_sandbox` points `STOPPED` at a scratch
         directory before driving this module, so a resume against a redirected ledger cannot
         lift anything the library is running on -- there is nothing on the other end of it.

      2. THE NAME CARRIES THE HOUSE SELF-TEST MARKER. `__drill_rung4__`, `__drill_rung4b__` and
         `__drill_litter_probe__` are reserved synthetic subjects; `health.py:73-74` already
         names `stop_subsystem`/`resume_subsystem` against exactly these as the case its
         self-test ledger exists for. The marker is BORROWED from `health.SELFTEST_SUBJECT`
         rather than re-spelled here: two hand-kept copies of one pattern is how they come to
         disagree, and this one decides whether a guard applies.

    FAILS CLOSED. If `health` cannot be imported the answer is False -- not a probe -- so the
    person check applies in full. An exemption that survives its own evidence going missing is
    not an exemption, it is a hole.
    """
    if STOPPED != _REAL_STOPPED:
        return True
    try:
        import health as _H
        return bool(_H.is_selftest(str(name)))
    except Exception:
        silence.note("escalation.py:probe-release-marker")
        return False


def resume_subsystem(name, ruling, by="?"):
    """Re-open one subsystem. A PERSON ONLY, and a written ruling -- a LONGER one than `clear`
    demands. -> bool.

    THE PERSON CHECK LANDED 2026-09-08 (order ddb5eadd8934, owner ruling "Who may lift a halt or
    a subsystem stop"). Until then this bar was twenty characters of anything and nothing else,
    so any autonomous run could re-open a rung-4 stop -- see `resume_subsystem_verdict`, which is
    where the refusal is spelled. A person resumes one with:

        python src/escalation.py --resume <subsystem> --ruling "<what you decided and why>"

    THE TWO BARS ARE NOT THE SAME AND THIS DOCSTRING USED TO SAY THEY WERE (order 8b1b81bcfee4,
    reported by sweep44-batch14). It read "exactly as `clear` does", while
    `resume_subsystem_verdict` demands 20 characters and `clear` demands 12. Corrected here to
    what the code actually enforces rather than by moving either threshold: this is the halt
    chain, where a wrong belief is most expensive, and a reader who trusts a docstring about it
    should get the real rule.
    WHICH NUMBER IS RIGHT IS LEFT OPEN ON PURPOSE. Both are defensible -- a resume is stickier
    than a lift in one reading, and strictly less consequential in another -- and `drill.py`
    probes `clear("")` and `clear("ok")` against the 12, so moving either bar is a behavioural
    change to a tested safety and not a docstring repair. Flagged for a ruling, not decided.

    THIN WRAPPER OVER `resume_subsystem_verdict` (order 7209d442c73e). This is a public function
    with a documented `-> bool`, so the signature stays -- but a bare bool collapses two
    entirely different worlds into one sentence, the exact shape `main()`'s `--clear` arm was
    already repaired for (see the `clear()` call site comment). World (a): the subsystem was
    never stopped, nothing to do, no fault. World (b): the write to state/STOPPED.json could not
    be landed after STOP_CAS_ATTEMPTS -- the subsystem is STILL STOPPED and this resume did not
    happen. `resume_subsystem_verdict` tells the two apart; a caller that only wants the bool
    (most of them) still gets exactly what it got before.
    """
    ok, _reason = resume_subsystem_verdict(name, ruling, by)
    return ok


def resume_subsystem_verdict(name, ruling, by="?"):
    """Re-open one subsystem. -> (bool, reason). The three-valued sibling of `resume_subsystem`.

    `drill.py`'s three rung-4 probes call `resume_subsystem` in a `finally` and discard the
    return, and this shift found live evidence of what that costs: state/STOPPED.json held
    three orphaned probe stops (`__drill_rung4__`, `__drill_rung4b__`, `__drill_litter_probe__`)
    written 34 seconds earlier by a drill run whose resumes had not landed, with nothing
    anywhere reporting it. A caller that wants to notice -- a probe that cannot clean up after
    itself is leaving state behind on a live library -- can call this instead and read `reason`,
    which carries a `NOT RESUMED:` prefix on the real-failure branch (world (b) above) and a
    plain, unprefixed reason on the "nothing to do" branch (world (a)), the same contract
    `binding_health.release()` and `_report_not_released` already use for the identical shape
    one rung over.
    """
    if not (ruling or "").strip() or len(str(ruling).strip()) < 20:
        raise ValueError("resuming a stopped subsystem needs a written ruling, not a shrug")
    # AND A PERSON, EXACTLY AS `clear` DEMANDS ONE (order ddb5eadd8934, owner ruling 2026-09-08
    # "Who may lift a halt or a subsystem stop"). `stop_subsystem`'s docstring has said in
    # capitals since the day it was written that the resume is "deliberately STICKY:
    # `resume_subsystem` demands a written ruling, EXACTLY AS `clear` DOES, because the thing
    # that undid the last one was an automated actor with good intentions and a restart timer".
    # It did not do exactly what `clear` does: the half that stops an automated actor was
    # absent, so any autonomous run could re-open a rung-4 stop with twenty characters of
    # anything -- and the incident that sentence cites (catalogue_web --recatalogue stopped at
    # 22:5x for nulling synthesis blocks, restarted by the keeper at 23:21) is precisely that
    # class of actor. The docstring is now true.
    #
    # THE REFUSAL ORDER IS PART OF THE CONTRACT. The written-ruling check runs FIRST and this
    # runs second, matching `clear()` for the same reason `clear()` gives: `drill.py` proves the
    # written-ruling rule by calling `resume_subsystem(name, "ok")` and requiring a ValueError,
    # and a person check ahead of it would answer that probe with the wrong refusal and leave
    # the ruling rule untested.
    if not _a_probe_release(name) and not _by_a_person_at_the_cli():
        raise PermissionError(
            "a stopped subsystem may not be re-opened programmatically. An autonomous run may "
            "STOP a subsystem; only a person may resume one, and that asymmetry is the same one "
            "the halt rests on. Resume it by hand:\n"
            "    python src/escalation.py --resume <subsystem> "
            "--ruling \"<what you decided and why>\"")
    # THE WRITE'S VERDICT IS READ, NOT ASSUMED (order 4f290dae34ef). This was a bare
    # `_write_stopped(doc)` with no guard at all, so the ordinary Windows rename denial came out
    # of here as an uncaught PermissionError -- after `doc.pop`, so the operator got a traceback
    # while the subsystem was still stopped on disk and its SUBSYSTEM_STOPPED order still open.
    # Retried and compare-and-swapped for the same reason `stop_subsystem` is: a resume that
    # loses its update leaves a stop standing that everybody believes was lifted.
    landed, detail = False, "not attempted"
    for _ in range(STOP_CAS_ATTEMPTS):
        # The digest goes BEFORE the read -- see `_write_stopped`.
        expected = silence.digest_of(STOPPED)
        doc = _read_stopped()
        if "__unreadable__" in doc:
            # Fail closed, and say so. An unreadable ledger means the standing stops cannot be
            # seen, so it cannot be said whether this one is held, and nothing may be written
            # over records nobody has read. The subsystem stays stopped, which is what is on disk.
            reason = ("NOT RESUMED: state/STOPPED.json could not be read as a map of stops, "
                      "so %s cannot be shown to be stopped and nothing may be written over "
                      "what it holds." % name)
            sys.stderr.write(reason + "\n")
            return False, reason
        if str(name) not in doc:
            # WORLD (a): NEVER STOPPED, NOTHING TO DO, NO FAULT. Deliberately no `NOT RESUMED:`
            # prefix -- that prefix is what `_report_not_released`-style callers test on to
            # decide whether to raise an alarm, and there is nothing here to alarm about.
            return False, "%s was not stopped; nothing to resume" % name
        doc.pop(str(name), None)
        try:
            landed, detail = _write_stopped(doc, expected)
        except Exception:
            silence.note("escalation.py:resume-write")
            landed, detail = False, "the temp copy could not be written"
        if landed:
            break
    if not landed:
        # NOT AN EXCEPTION, AND NOT A SILENT False EITHER. The stop is still on disk, so the
        # honest answer is that the resume did not happen -- said in the same voice `clear()`
        # uses for its own refused write, because it is the same fact one rung down.
        silence.note("escalation.py:resume-not-landed")
        reason = ("NOT RESUMED: state/STOPPED.json could not be written after %d attempts "
                  "(%s). %s is STILL STOPPED. Close whatever is holding the file and run "
                  "this again." % (STOP_CAS_ATTEMPTS, detail, name))
        sys.stderr.write(reason + "\n")
        return False, reason
    escalate(JANITOR, "SUBSYSTEM_RESUMED", "%s resumed: %s" % (name, ruling),
             source=name, who=by)
    # AND THE STOP'S OWN WORK ORDER IS CLOSED HERE, because nothing else was closing it.
    # `stop_subsystem` escalates at MANAGER, and `escalate` turns every escalation into a work
    # order -- so a stop opens a MAJOR order keyed (SUBSYSTEM_STOPPED, name). Lifting the stop
    # emptied `state/STOPPED.json` and filed a SECOND, separate SUBSYSTEM_RESUMED order, but left
    # the first one OPEN: the queue went on saying a subsystem was stopped after it had been
    # resumed, at MAJOR, addressed to RUN. Measured on 2026-08-29 -- `state/STOPPED.json` was
    # `{}` and nothing was stopped, while orders 16d29e625d29 (`pipeline`) and a4b8fb03956e
    # (`feats`) still stood open claiming otherwise, left behind by a scratch test harness at
    # 22:21. The drill's own probe never exposed this because the drill closes its orders BY
    # HAND afterwards; any other caller of the sanctioned API leaks one.
    #
    # A false MAJOR is not clutter. This is the rung whose entire purpose is that a real stop --
    # `catalogue_web --recatalogue` nulling synthesis blocks, order 4e7f1e47d0a0 -- can be found
    # in the record, and it cannot be found among stale copies of itself.
    #
    # Defensive exactly like `escalate`'s own workorder call: a queue that will not accept the
    # closure must never take the resume down with it. The stop has already been lifted above,
    # which is the part that matters, and a lingering order is recoverable by the next sweep.
    try:
        import workorders as WO
        WO.resolve_code("SUBSYSTEM_STOPPED",
                        "resumed by %s: %s" % (by, ruling), where=str(name), by=str(by))
    except Exception:
        silence.note("escalation.py:resume-order")
    return True, "%s resumed: %s" % (name, ruling)


# NO CALLER YET, AND KEPT ON PURPOSE -- the `feats.py` "REPORTED DEAD, NOT DELETED" idiom, under
# the owner ruling of 2026-09-08, question 1 ("Mark and keep: one line each, delete nothing").
# `refuse_unit` and `refuse_source` below are the sanctioned raisers `Refused` did not have. The
# four per-unit / per-source refusal sites that should route through them today live in modules
# this brief does not own -- `binding_health.py:291,416,419`, `foreman.py:659`,
# `thread_integrity.py:678` -- so the raisers land here and the adoption is owed by those
# modules. Do not delete these because nothing calls them: an uncalled raiser is one import away
# from being the whole point, and the state the ruling forbids is the OTHER one, a named safety
# with no site that can ever produce it. (order da15f582b2ea, 2026-09-08)
def refuse_unit(code, what, evidence=None, source=None, who=None):
    """Rung 1. Record it, then REFUSE THIS UNIT of work by raising `Refused`. Never returns.

    THE ONE SPELLING FOR AN OPERATOR REFUSAL (order da15f582b2ea, owner ruling 2026-09-08 "Who
    may lift a halt or a subsystem stop": "the existing per-unit and per-source refusals route
    through `escalation.Refused` so the chain has one spelling").

    WHAT WAS WRONG. `class Refused` has been declared at the top of this file since the chain was
    written -- "an OPERATOR- or SUPERVISOR-level stop: this unit or this source, not the library"
    -- and NOTHING in the tree raised it, caught it, imported it or named it. Its sibling
    `SystemHalted` is raised here and caught in `verify_math`; `prose_gate` declares and raises
    its own `ProseRefused`. So the two rungs of Hard Rule -1's chain that stop a UNIT and a
    SOURCE had a named exception type with no site that could ever produce one: a safety that
    exists in a file rather than in effect, which is the fourth property CLAUDE.md names. It was
    surfaced by `liveness.scan()`'s dead-class pass as the single finding across the whole tree.

    WHY IT RAISES RATHER THAN RETURNING. `escalate()` deliberately does not decide control flow
    for rungs 1-4 -- "a guard that both detects and unwinds is hard to test" -- and that stays
    true of `escalate`. This is the other half, for the callers that DO want to unwind: the
    record and the raise in one call, so a refusal cannot be recorded and then walked past.
    """
    escalate(OPERATOR, code, what, evidence=evidence, source=source, who=who)
    raise Refused("OPERATOR refusal — %s: %s" % (code, what))


def refuse_source(source, code, what, evidence=None, who=None):
    """Rung 2. Record it, then CLOSE THIS SOURCE'S AREA by raising `Refused`. Never returns.

    The per-source sibling of `refuse_unit`, and the reason the distinction is worth two
    functions rather than a level argument: "every source is its own area of the park". A fault
    in one source must never close the library, and a caller reaching for a refusal at the moment
    something has gone wrong should not also have to pick a rung number correctly.

    `source` is FIRST and required, because a SUPERVISOR escalation without one is not a
    per-source refusal at all -- it is an unattributed alarm, and `_append_log` would have
    nowhere to write the area's own history.
    """
    escalate(SUPERVISOR, code, what, evidence=evidence, source=source, who=who)
    raise Refused("SUPERVISOR refusal — %s (%s): %s" % (code, source, what))


def assert_clear(who="?"):
    """EVERY entry point calls this before doing anything. The plant-wide interlock.

    This is the rung that makes the chain real: without it a halt is a note in a file that the
    running jobs never read, and the library keeps working while its own alarm is sounding.
    """
    halted, rec = status()
    if not halted:
        return True
    raise SystemHalted(
        HALT_REFUSAL + " and %s may not proceed.\n"
        "  code     : %s\n  what     : %s\n  raised by: %s\n  source   : %s\n"
        "This is the top rung of the escalation chain: an invariant that spans the whole library "
        "was violated, so everything stopped rather than continuing on uncertain ground.\n"
        "Only a person may lift it:\n"
        "    python src/escalation.py --clear --ruling \"<what you decided and why>\""
        % (who, rec.get("code"), rec.get("what"), rec.get("by"), rec.get("source")))


def _by_a_person_at_the_cli():
    """True only for `python src/escalation.py --clear`. False for every programmatic call.

    THE GUARANTEE WAS A GREP UNTIL RUN #33. "It cannot be cleared programmatically" was enforced
    entirely by `drill.py:_no_programmatic_clear`, which reads every other `src/*.py` looking for
    the literal strings `escalation.clear(` and `ESC.clear(`. `import escalation as X; X.clear()`,
    `from escalation import clear`, `getattr(escalation, "clear")()` and any dynamically built
    call contain neither string, so the asymmetry the whole chain rests on held against two
    spellings rather than against the capability itself. That is a guarantee written in a comment.

    This makes it true in the code. Two conditions, both required:
      1. the program being run IS this file -- `__main__.__file__` resolves to escalation.py, so
         `python -c "import escalation; escalation.clear(...)"` and any importing job are out;
      2. the immediate caller is this file's own `main()`, so a module that reaches in and calls
         `escalation.main()` under a borrowed argv is out too.

    The grep stays. It catches the attempt when a person reads the diff; this catches it when the
    process runs, and a safety with one enforcement point is a safety that is one edit from none.
    """
    here = os.path.abspath(__file__)
    main_mod = sys.modules.get("__main__")
    if os.path.abspath(getattr(main_mod, "__file__", "") or "") != here:
        return False
    try:
        f = sys._getframe(2)          # 0 = this function, 1 = clear(), 2 = clear()'s caller
    except ValueError:
        return False
    return (f is not None and f.f_code.co_name == "main"
            and os.path.abspath(f.f_code.co_filename) == here)


def clear(ruling, by=None):
    """Lift the halt. A PERSON ONLY, and refused at run time if the caller is not one.

    Demands a written ruling because the halt exists to buy a decision, and a halt lifted with
    no decision recorded has bought nothing. The ruling is kept with the original fault.

    The ruling is validated FIRST and the caller second, deliberately: `drill.py` proves the
    written-ruling rule by calling `clear("")` and `clear("ok")` and requiring a `ValueError`,
    and a caller check that ran ahead of it would answer those probes with the wrong refusal and
    leave the ruling rule untested. Order of refusals is part of what is tested here.
    """
    if not ruling or not str(ruling).strip() or len(str(ruling).strip()) < 12:
        raise ValueError("a ruling is required, in words -- what did you decide, and why? "
                         "(at least a short sentence)")
    if not _by_a_person_at_the_cli():
        raise PermissionError(
            "the halt may not be lifted programmatically. An autonomous run may RAISE a halt; "
            "only a person may lift one, and that asymmetry is the point -- the incident this "
            "chain exists for was an automated agent removing a safety it had concluded was "
            "unnecessary. Lift it by hand:\n"
            "    python src/escalation.py --clear --ruling \"<what you decided and why>\"")
    # AND IT MUST BE SIGNED (order c614f7c145fc, owner ruling 2026-09-08 "Who may lift a halt or
    # a subsystem stop"). `by` defaulted to "owner" here and `--by` defaulted to "owner-cli" in
    # `main()`, and neither is evidence that a person ruled -- they are labels the CLI supplies
    # when nobody says otherwise. It has now happened TWICE: a halt lifted at 00:55 on a
    # scheduled run with nobody present, recorded as `owner-cli`, the first time with the publish
    # daemon resuming behind it. The only reason the second one reads as
    # `scheduled-maintenance-2026-09-05-daily` is that the actor VOLUNTEERED it.
    #
    # A default that reads as a person is worse than no attribution at all, because the ledger
    # then carries a positive false statement about who decided. So there is no default: the
    # caller says who, or the halt stays up. This is the one thing code CAN ask -- the runtime
    # guard above asks whether this file is the program being run, which is as close to "is
    # there a person here" as a process can get, and it cannot ask whose hands are on the
    # keyboard. What it can refuse is an unsigned ruling.
    #
    # AFTER THE PERSON CHECK, DELIBERATELY. `drill.py` proves the programmatic refusal by
    # calling `ESC.clear(r)` through four spellings with no `by` at all and requiring
    # PermissionError from every one; an attribution check ahead of it would answer those probes
    # with a ValueError and leave the asymmetry the whole chain rests on untested.
    if not str(by or "").strip():
        raise ValueError(
            "a halt lift must be SIGNED: pass --by with who is lifting it. There is no default, "
            "because the old one (\"owner-cli\") reads as a person and was twice recorded for a "
            "scheduled run with nobody present. An automated run lifting a halt under the "
            "self-caused clause must sign its own name.")
    # COMPARE-AND-SWAPPED, for the same reason `_raise_halt` and `_write_stopped` are, and this
    # was the last writer of `state/HALT.json` that was not (order 0f815b38363f). The read below,
    # the merge under it and the write at the bottom were three separate steps with nothing
    # between them, so a fault escalating to OWNER concurrently with a person's `--clear` was
    # SILENTLY DROPPED: `_land_halt` appends it to `also`, this function then landed a payload
    # built from the record as it stood BEFORE that append, and the fault vanished with a
    # successful write. Worse than the raise-side race it mirrors, because it takes the halt down
    # with it -- the library resumes on a ruling that was written about a different set of facts.
    #
    # The digest is taken BEFORE the read, the same ordering and for the same reason as
    # `_raise_halt`: read first and the digest would match disk while the record in hand is
    # already stale, certifying the lost update instead of catching it.
    #
    # A DIGEST MISMATCH DOES NOT RETRY THE LIFT. That is the one place this deliberately differs
    # from the raise side. `_raise_halt` goes round because appending a fault to whatever is
    # standing now is still the right act; a LIFT is a person's ruling about specific facts, and
    # re-merging it onto a record that has grown a fault they never read would launder their
    # signature onto a decision they did not make. So the file changing under this call is
    # reported, with the new fault named, and the halt STAYS UP until the person rules again.
    # Only a transient refusal -- the digest still exactly what we read -- is retried.
    first = None
    landed, why = False, "not attempted"
    for _attempt in range(STOP_CAS_ATTEMPTS):
        expected = silence.digest_of(HALT_FILE)
        halted, rec = status()
        if not halted:
            return False
        if first is None:
            first = _halt_identity(rec)
        elif _halt_identity(rec) != first:
            silence.note("escalation.py:halt-clear-raced")
            sys.stderr.write(
                "THE HALT WAS NOT LIFTED: state/HALT.json changed while this lift was being "
                "written -- a fault landed that your ruling was not written about. The library "
                "is STILL HALTED, deliberately. Read the halt again (python src/escalation.py "
                "--status) and rule on what it says now.\n")
            return False
        rec = dict(rec)
        rec.update({"cleared": True, "ruling": str(ruling).strip(), "cleared_by": by,
                    "cleared_at": time.time()})
        # THE SAME DISCARDED VERDICT AS `_raise_halt`, and the mirror-image consequence: the write
        # was never checked, so a refused rename left `cleared: false` on disk while this returned
        # True and the CLI printed "halt cleared." A person would walk away believing the library
        # was running, and every job would go on refusing. Reported as not-cleared instead, and
        # the HALT_CLEARED line is only appended once the lift has actually landed -- a ledger
        # entry for a lift that did not happen is worse than no entry, because it is what the
        # next reader trusts when the file and the log disagree.
        landed, why = _land_clear(rec, expected)
        # READ BACK, AND DO NOT TRUST `landed` ALONE, for the reason spelled out in `_raise_halt`:
        # `replace_if_unchanged` re-reads the digest immediately before its own rename, so a
        # writer can still land in the gap between that read and the rename. The file saying
        # `cleared` is the only evidence the lift actually happened.
        if landed and _halt_file_cleared():
            _append_log({"at": time.time(), "level": OWNER, "level_name": "OWNER",
                         "code": "HALT_CLEARED", "what": str(ruling).strip(), "who": by})
            return True
        landed = False
    silence.note("escalation.py:halt-clear-denied")
    sys.stderr.write("THE HALT WAS NOT LIFTED after %d attempts (%s): the write to "
                     "state/HALT.json could not land. The library is STILL HALTED. Try again.\n"
                     % (STOP_CAS_ATTEMPTS, why))
    return False


def _halt_identity(rec):
    """What this halt RECORDS, as a comparable value -- the standing fault plus every
    corroborating one. Used by `clear()` to tell a transient write refusal (identity unchanged,
    worth another attempt) from a fault landing mid-lift (identity grown, and the person's ruling
    no longer covers the file). Deliberately ignores the mutable fields a lift itself writes."""
    rec = rec if isinstance(rec, dict) else {}
    also = tuple(sorted((str(x.get("code")), x.get("at"))
                        for x in (rec.get("also") or []) if isinstance(x, dict)))
    return (str(rec.get("code")), rec.get("raised_at"), also)


def _halt_file_cleared():
    """Does the halt file on disk actually say `cleared` now? -> bool. The readback that makes
    the lift's verdict evidence rather than an assumption."""
    cur = _read_halt_raw()
    return isinstance(cur, dict) and bool(cur.get("cleared", False))


def _land_clear(rec, expected):
    """One compare-and-swapped attempt at lifting the halt. -> (landed, why).

    A sibling of `_land_halt`, and through a temp + `replace_if_unchanged` for the same reason:
    `write_json` retries a DENIED rename, which is right for a reader holding the file and wrong
    for a competing WRITER -- it would land the stale payload just as happily, which is the
    lost-update this whole function exists to stop.
    """
    try:
        os.makedirs(os.path.dirname(HALT_FILE), exist_ok=True)
        import threading as _th
        tmp = "%s.%d.%d.clear.tmp" % (HALT_FILE, os.getpid(), _th.get_ident())
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=1, ensure_ascii=False)
        landed, why = silence.replace_if_unchanged(tmp, HALT_FILE, expected)
        if not landed:
            # Silent: this is ONE attempt of a compare-and-swap and `clear()` decides when the
            # attempts are exhausted, and is loud about it.
            _unlink(tmp)
        return landed, why
    except Exception as e:
        silence.note("escalation.py:halt-clear")
        sys.stderr.write("CANNOT WRITE HALT FILE while lifting the halt — %s: %s\n"
                         % (type(e).__name__, e))
        return False, "raised"


def main():
    import argparse
    ap = argparse.ArgumentParser(description="the library's halt and escalation chain")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--clear", action="store_true")
    ap.add_argument("--ruling", default="")
    # WHO ACTUALLY LIFTED IT, and until now the record could not say. `--clear` hardcoded
    # `by="owner-cli"`, which is the CLI's default label and NOT evidence that a person ruled --
    # and order c614f7c145fc exists because exactly that happened: a halt was lifted at 00:55 on
    # a scheduled run with nobody present, and the ledger recorded `who=owner-cli`, so the only
    # way anybody learned an automated actor had done it was by reading the handoff prose.
    #
    # The runtime guard (`_by_a_person_at_the_cli`) asks whether this file is the program being
    # run, which is the strongest question code can ask; what it cannot ask is whether the hands
    # at the CLI belong to a person. That gap is not closable from here. What IS closable is the
    # record's ability to be honest when the caller volunteers the truth, so an automated run
    # that lifts a halt under the self-caused clause can sign its own name instead of wearing
    # the owner's. The default is unchanged, so a person at a terminal still records as before.
    # AND THERE IS NO LONGER A DEFAULT (order c614f7c145fc, owner ruling 2026-09-08). The
    # paragraph above records why the hardcoded `owner-cli` was wrong; the ruling closes the
    # remaining half of it, which is that a DEFAULT of "owner-cli" is the same false statement
    # the hardcoding was. `clear()` refuses an unsigned lift, so this is `None` and the refusal
    # is spelled once, in the function, where a programmatic caller meets it too.
    ap.add_argument("--by", default=None,
                    help="who is lifting it or resuming it. REQUIRED for --clear: there is no "
                         "default, because a default reads as a person. An automated run must "
                         "pass its own name.")
    # THE PERSON-FACING RESUME, AND UNTIL NOW THERE WAS NONE (order ddb5eadd8934, owner ruling
    # 2026-09-08). `resume_subsystem` lifts a MANAGER stop -- rung 4, "stop the SUBSYSTEM" -- and
    # this parser offered --status, --clear, --ruling and --raise-halt and no way to do it. So
    # the only callers of the sanctioned API were programs, which is precisely the class of actor
    # the stop exists to hold, and a person who wanted to resume one had to write Python.
    ap.add_argument("--resume", default="",
                    help="NAME — re-open one subsystem stopped at rung 4. Needs --ruling (20 "
                         "characters or more) and, like --clear, is refused to any caller that "
                         "is not this file being run by hand.")
    ap.add_argument("--raise-halt", dest="raise_halt", default="",
                    help="code:what — raise a halt by hand (testing, or a person stopping the "
                         "library deliberately)")
    a = ap.parse_args()
    if a.resume:
        # CALLED THROUGH `resume_subsystem_verdict`, NOT THROUGH THE `resume_subsystem` WRAPPER,
        # and the reason is the person check itself. `_by_a_person_at_the_cli` asks whether the
        # IMMEDIATE caller is this file's own `main()` -- `sys._getframe(2)` -- so going through
        # the one-line wrapper would put `resume_subsystem` in that frame and refuse the person
        # standing at the terminal. The verdict form is also the one that tells "was never
        # stopped" apart from "the write did not land", which is exactly what an operator needs
        # printed back at them here.
        try:
            # `"cli"` when nobody signed, NOT `"owner-cli"`: the same distinction `--raise-halt`
            # already draws with `who="cli"`. It names the CHANNEL, which is a fact, rather than
            # a person, which would be the false statement the `--by` default was removed for.
            ok, reason = resume_subsystem_verdict(a.resume, a.ruling, by=(a.by or "cli"))
        except (ValueError, PermissionError) as e:
            print("refused: %s" % e)
            return 2
        print(("resumed: " if ok else "not resumed: ") + reason)
        return 0 if ok else 1
    if a.raise_halt:
        code, _, what = a.raise_halt.partition(":")
        # THE LANDING VERDICT IS NOT THROWN AWAY HERE EITHER (order a1addbdff907). This was
        # `escalate(...)` / `print("halted.")` / `return 0`, so a person who deliberately halted
        # the library was told on stdout that they had -- with a success rc for any script
        # watching -- whether or not `state/HALT.json` ever appeared. When it does not appear
        # every other process's `assert_clear()` finds no halt and carries straight on, which is
        # the exact failure `escalate()` was rewritten to be able to report. Branched the same
        # way `--clear` names which of its two worlds it is in, ten lines down.
        rec = escalate(OWNER, code or "MANUAL", what or "raised by hand", who="cli")
        if not rec.get("halt_landed"):
            print("THE HALT WAS NOT RAISED — state/HALT.json could not be written (a reader is "
                  "holding it). Nothing is halted; close whatever holds the file and run this "
                  "again.")
            return 1
        print("halted.")
        return 0
    if a.clear:
        # PermissionError is caught alongside ValueError because `clear()` raises it for a
        # non-person caller, and the two refusals are the same event to a reader: the lift did
        # not happen and here is why. Uncaught, it printed a traceback instead of the sentence
        # the exception carefully spells out.
        try:
            did = clear(a.ruling, by=a.by)
        except (ValueError, PermissionError) as e:
            print("refused: %s" % e)
            return 2
        if did:
            print("halt cleared.")
            return 0
        # `clear()` RETURNS False FOR TWO ENTIRELY DIFFERENT WORLDS -- `if not halted: return
        # False` and `if not landed: ... return False` -- and this line used to collapse them
        # into one sentence: "nothing was halted." A person lifting a STANDING halt whose write
        # was refused (a reader holding HALT.json, which the module's own comment calls the
        # ordinary Windows case) was told on stdout that there had never been anything wrong,
        # while stderr said the opposite on the same console. That is the mirror of the defect
        # `clear()`'s own comment says it fixed, and it is the more expensive wrong belief of
        # the two. Re-read the file and name which world this is; rc follows, so a script can
        # tell a refused lift from a no-op as well.
        halted, _rec = status()
        if halted:
            print("THE HALT IS STILL STANDING — the write to state/HALT.json was refused.\n"
                  "Nothing was lifted. Close whatever is holding the file and run this again.")
            return 1
        print("nothing was halted.")
        return 0
    halted, rec = status()
    if not halted:
        print("clear — the library is running.")
        return 0
    print("HALTED")
    for k in ("code", "what", "by", "source", "raised_at"):
        print("  %-9s %s" % (k, (rec or {}).get(k)))
    extra = (rec or {}).get("also") or []
    if extra:
        print("  (+%d further fault(s) recorded while halted)" % len(extra))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
