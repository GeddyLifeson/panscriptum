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
_FIELDS = {
    JANITOR:    ("at", "level_name", "code", "what", "source", "who", "evidence"),
    OPERATOR:   ("at", "level_name", "code", "what", "source", "who"),
    SUPERVISOR: ("at", "level_name", "code", "what", "source"),
    SAFETY:     ("at", "level_name", "code", "what", "source"),
    MANAGER:    ("at", "level_name", "code", "what", "source", "who"),
    OWNER:      ("at", "code", "what", "source", "evidence", "who"),
}


def brief(rec, level):
    """The record as THIS rung should receive it -- nothing more.

    Deliberately a whitelist, not a blacklist: a field added to the record later must be
    admitted on purpose rather than leaking upward because nobody remembered to exclude it.
    """
    keep = _FIELDS.get(level, _FIELDS[JANITOR])
    return {k: rec[k] for k in keep if k in rec and rec[k] is not None}


def _safe_name(s):
    out = "".join(c if (c.isalnum() or c in "-_") else "_" for c in str(s or "unscoped"))
    return (out[:60] or "unscoped")


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
        _raise_halt(rec)
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
    try:
        os.makedirs(os.path.dirname(HALT_FILE), exist_ok=True)
        tmp = HALT_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=1, ensure_ascii=False)
        silence.replace_retry(tmp, HALT_FILE)
    except Exception:
        # A halt that cannot be written is the worst case, so it is the ONE thing that is
        # allowed to be loud on stderr as well as recorded.
        silence.note("escalation.py:halt-write")
        sys.stderr.write("CANNOT WRITE HALT FILE — %s: %s\n" % (rec["code"], rec["what"]))


def _read_halt_raw():
    try:
        with open(HALT_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception:
        # FAIL CLOSED. A halt file we cannot read is not an absent halt; it is a halt whose
        # reason we have lost, which is strictly more alarming, not less.
        return {"cleared": False, "code": "HALT_FILE_UNREADABLE",
                "what": "state/HALT.json exists but does not parse. Treating the library as "
                        "halted: a halt that a corrupted file can lift is not a halt.",
                "by": "escalation", "unreadable": True}


def status():
    """-> (halted: bool, record or None)."""
    rec = _read_halt_raw()
    if rec is None:
        return False, None
    return (not rec.get("cleared", False)), rec


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
    tmp = HALT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1, ensure_ascii=False)
    silence.replace_retry(tmp, HALT_FILE)
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
        escalate(OWNER, code or "MANUAL", what or "raised by hand", who="cli")
        print("halted.")
        return 0
    if a.clear:
        try:
            did = clear(a.ruling, by="owner-cli")
        except ValueError as e:
            print("refused: %s" % e)
            return 2
        print("halt cleared." if did else "nothing was halted.")
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
