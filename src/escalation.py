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
_FIELDS = {
    JANITOR:    ("at", "level_name", "code", "what", "source", "who", "evidence", "halt_landed"),
    OPERATOR:   ("at", "level_name", "code", "what", "source", "who"),
    SUPERVISOR: ("at", "level_name", "code", "what", "source"),
    SAFETY:     ("at", "level_name", "code", "what", "source"),
    MANAGER:    ("at", "level_name", "code", "what", "source", "who"),
    OWNER:      ("at", "code", "what", "source", "evidence", "who", "halt_landed"),
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
    """Append one line of JSON. Never the reason a caller dies."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return True
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
    """
    ok = _append(LOG, brief(rec, JANITOR))
    src = rec.get("source")
    if src:
        _append(os.path.join(SRC_LOGS, _safe_name(src) + ".log"),
                brief(rec, rec.get("level", JANITOR)))
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
    _append_log(rec)
    try:
        import health
        health.record("escalation:%s:%s" % (NAMES.get(level, level), code), rec["what"])
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


def _raise_halt(rec):
    """Write the halt. Whole-file, atomic, and never overwritten once standing.

    A second fault while halted is appended as corroboration rather than replacing the first --
    the FIRST thing that went wrong is the one a person needs to see, and a later, louder symptom
    must not bury it.
    """
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
    landed = False
    try:
        os.makedirs(os.path.dirname(HALT_FILE), exist_ok=True)
        landed = silence.write_json(HALT_FILE, payload, indent=1, ensure_ascii=False)
    except Exception:
        # A halt that cannot be written is the worst case, so it is the ONE thing that is
        # allowed to be loud on stderr as well as recorded.
        silence.note("escalation.py:halt-write")
        sys.stderr.write("CANNOT WRITE HALT FILE — %s: %s\n" % (rec["code"], rec["what"]))
        return False
    if not landed:
        silence.note("escalation.py:halt-write-denied")
        sys.stderr.write("CANNOT WRITE HALT FILE (the rename was refused, a reader is holding "
                         "it) — %s: %s\n" % (rec["code"], rec["what"]))
    return landed


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
    STICKY: `resume_subsystem` demands a written ruling, exactly as `clear` does, because the
    thing that undid the last one was an automated actor with good intentions and a restart
    timer.
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


def resume_subsystem(name, ruling, by="?"):
    """Re-open one subsystem. Demands a written ruling, exactly as `clear` does. -> bool."""
    if not (ruling or "").strip() or len(str(ruling).strip()) < 20:
        raise ValueError("resuming a stopped subsystem needs a written ruling, not a shrug")
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
            sys.stderr.write("NOT RESUMED: state/STOPPED.json could not be read as a map of "
                             "stops, so %s cannot be shown to be stopped and nothing may be "
                             "written over what it holds.\n" % name)
            return False
        if str(name) not in doc:
            return False
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
        sys.stderr.write("NOT RESUMED: state/STOPPED.json could not be written after %d attempts "
                         "(%s). %s is STILL STOPPED. Close whatever is holding the file and run "
                         "this again.\n" % (STOP_CAS_ATTEMPTS, detail, name))
        return False
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
    return True


def assert_clear(who="?"):
    """EVERY entry point calls this before doing anything. The plant-wide interlock.

    This is the rung that makes the chain real: without it a halt is a note in a file that the
    running jobs never read, and the library keeps working while its own alarm is sounding.
    """
    halted, rec = status()
    if not halted:
        return True
    raise SystemHalted(
        "THE LIBRARY IS HALTED and %s may not proceed.\n"
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


def clear(ruling, by="owner"):
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
    halted, rec = status()
    if not halted:
        return False
    rec = dict(rec or {})
    rec.update({"cleared": True, "ruling": str(ruling).strip(), "cleared_by": by,
                "cleared_at": time.time()})
    # THE SAME DISCARDED VERDICT AS `_raise_halt`, and the mirror-image consequence: the write
    # was never checked, so a refused rename left `cleared: false` on disk while this returned
    # True and the CLI printed "halt cleared." A person would walk away believing the library was
    # running, and every job would go on refusing. Reported as not-cleared instead, and the
    # HALT_CLEARED line is only appended once the lift has actually landed -- a ledger entry for
    # a lift that did not happen is worse than no entry, because it is what the next reader
    # trusts when the file and the log disagree.
    landed = silence.write_json(HALT_FILE, rec, indent=1, ensure_ascii=False)
    if not landed:
        silence.note("escalation.py:halt-clear-denied")
        sys.stderr.write("THE HALT WAS NOT LIFTED: the write to state/HALT.json was refused (a "
                         "reader is holding it). The library is STILL HALTED. Try again.\n")
        return False
    _append_log({"at": time.time(), "level": OWNER, "level_name": "OWNER", "code": "HALT_CLEARED",
                 "what": str(ruling).strip(), "who": by})
    return True


def main():
    import argparse
    ap = argparse.ArgumentParser(description="the library's halt and escalation chain")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--clear", action="store_true")
    ap.add_argument("--ruling", default="")
    ap.add_argument("--raise-halt", dest="raise_halt", default="",
                    help="code:what — raise a halt by hand (testing, or a person stopping the "
                         "library deliberately)")
    a = ap.parse_args()
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
            did = clear(a.ruling, by="owner-cli")
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
