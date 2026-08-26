"""CODEWATCH — a running process is a photograph of the code as it was when it started.

THE INCIDENT, 2026-08-25. `mutate.py` deliberately corrupts source files on disk; that is its
method. A guard was added to `publish.py` to refuse pushing while a mutation run is active, it
was tested by hand, and it worked. Then a mutated `prose_gate.py` and a mutated `escalation.py`
were **pushed to a public GitHub repo anyway**, twice.

The guard was fine. It was never consulted, because `publish.py --push --loop 1` had been
running since 14:28 with the PRE-GUARD code loaded into memory, and a Python process does not
re-read its own source. Editing a file changes what the NEXT process does. It changes nothing
about the fifteen already running.

That generalises past mutation testing, and it is the part worth writing down: **every safety
added to this project is invisible to every job already running until that job restarts.** A
fix landed at 19:00 and a keeper that restarts jobs only when they die means the fix may not be
in effect at 03:00. Nothing reports this. Both the old code and the new code run quietly.

WHAT THIS DOES. A long-lived loop calls `exit_if_stale()` once per cycle. If `src/` has changed
since the process started, the job **exits on purpose** with a distinctive code, and
`overnight.py`'s keeper -- which re-asserts its STANDING set every five minutes -- starts it
again running the new code. Restarting is the only way a Python process picks up a source edit,
so the design makes that the routine, cheap, expected thing rather than an event.

AND THE THREE WAYS THIS COULD ITSELF BE THE PROBLEM, each handled:

  * **A restart storm.** `local_agent.py --patch` writes into `src/` on its own schedule, and a
    naive version would bounce every daemon on every patch, forever. So restarts are BUDGETED
    per job per hour; past the budget the job keeps running stale and escalates, because
    thrashing is worse than lag and a person needs to know either way.
  * **Restarting mid-edit.** A digest taken while a file is half-written is a digest of garbage,
    and would trigger a restart into broken code. So a change must be STABLE for a settling
    period before it counts -- the same digest observed twice, `STABLE_SECONDS` apart.
  * **Looking like a crash.** This project's longest outage was a watcher reading
    jobs-exiting-on-purpose as jobs-crashing. So the exit code is distinctive, the log line says
    what happened in words, and `name_rc` in `overnight.py` is taught to read it.
"""
import argparse
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SRC)
import silence  # noqa: E402

# Distinctive on purpose. `rc=17` must never be confused with a crash, and `overnight.name_rc`
# translates it into a sentence.
RC_STALE = 17

# A change must hold still this long before it counts. Covers a multi-file edit, an editor's
# write-temp-then-rename, and `local_agent` applying a patch set -- all of which touch several
# files over a few seconds and none of which should each trigger their own restart.
STABLE_SECONDS = 180

# Past this many restarts in an hour, a job stops asking and starts complaining. A daemon that
# bounces every cycle does no work at all, which is a worse failure than running slightly old
# code, and it is the failure that looks most like everything being fine.
BUDGET_PER_HOUR = 4

LEDGER = os.path.join(HERE, "state", "CODEWATCH.json")

_START = {"digest": None, "at": None}
_PENDING = {"digest": None, "first_seen": None}


def fingerprint(root=None):
    """-> a digest of every .py in src/, or None if it cannot be taken.

    NONE IS NOT "UNCHANGED". A caller that treats an unreadable tree as a matching digest would
    silently stop watching, which is the failure this module exists to end wearing a different
    hat. Every caller below checks for None explicitly.
    """
    root = root or SRC
    h = hashlib.sha256()
    try:
        for name in sorted(os.listdir(root)):
            if not name.endswith(".py"):
                continue
            p = os.path.join(root, name)
            try:
                with open(p, "rb") as f:
                    h.update(name.encode("utf-8"))
                    h.update(f.read())
            except OSError:
                # A file that cannot be read right now is very likely being written right now.
                # Refuse the whole fingerprint rather than produce one that omits it.
                return None
    except OSError:
        return None
    return h.hexdigest()[:16]


def stamp(who="?"):
    """Record the code this process actually started with. Call once, at startup."""
    _START["digest"] = fingerprint()
    _START["at"] = time.time()
    _PENDING["digest"] = None
    _PENDING["first_seen"] = None
    return _START["digest"]


def _budget_left(who):
    """-> (remaining, used). Restarts are counted per job per rolling hour."""
    try:
        with open(LEDGER, encoding="utf-8") as f:
            doc = json.load(f)
    except Exception:
        doc = {}
    cutoff = time.time() - 3600
    recent = [t for t in (doc.get(who) or []) if isinstance(t, (int, float)) and t > cutoff]
    return BUDGET_PER_HOUR - len(recent), len(recent)


def _record_restart(who):
    try:
        with open(LEDGER, encoding="utf-8") as f:
            doc = json.load(f)
    except Exception:
        doc = {}
    cutoff = time.time() - 3600
    doc[who] = [t for t in (doc.get(who) or []) if isinstance(t, (int, float)) and t > cutoff]
    doc[who].append(time.time())
    try:
        silence.write_json(LEDGER, doc, indent=2)
    except Exception:
        silence.note("codewatch.py:record")


def stale(who="?"):
    """Has src/ changed, stably, since this process started? -> (bool, reason).

    Returns False with a REASON in every negative case, so a caller that logs the reason can
    tell "nothing changed" from "something changed and is still settling" from "I could not
    read the tree" -- three states a bare False would flatten into one.
    """
    if _START["digest"] is None:
        return False, "not stamped; call stamp() at startup"
    now = fingerprint()
    if now is None:
        return False, "source unreadable right now (probably mid-write)"
    if now == _START["digest"]:
        _PENDING["digest"] = None
        _PENDING["first_seen"] = None
        return False, "unchanged"
    if _PENDING["digest"] != now:
        _PENDING["digest"] = now
        _PENDING["first_seen"] = time.time()
        return False, "changed, settling"
    held = time.time() - (_PENDING["first_seen"] or time.time())
    if held < STABLE_SECONDS:
        return False, "changed, settling (%.0fs of %ds)" % (held, STABLE_SECONDS)
    return True, "src/ changed %s -> %s and held for %.0fs" % (
        _START["digest"], now, held)


def exit_if_stale(who="?", rc=RC_STALE):
    """The one call a long-lived loop makes. Exits the process if its code is out of date.

    DOES NOT RAISE ON THE BUDGET PATH. When a job has already restarted BUDGET_PER_HOUR times
    this hour it keeps running -- old code and all -- and escalates instead. A daemon that
    bounces forever performs no work while looking busy, and this project has already paid for
    one respawn loop (see `autostart._twin_watchdog`).
    """
    is_stale, why = stale(who)
    if not is_stale:
        return False
    left, used = _budget_left(who)
    if left <= 0:
        try:
            import escalation
            escalation.escalate(
                "MANAGER", "CODEWATCH_BUDGET",
                "%s has restarted %d times this hour for source changes and is now running "
                "STALE code on purpose, because bouncing is worse than lag. A person should "
                "look at what keeps rewriting src/." % (who, used),
                evidence={"job": who, "restarts_this_hour": used}, source=who, who="codewatch")
        except Exception:
            silence.note("codewatch.py:budget-escalate")
        return False
    _record_restart(who)
    print("[codewatch] %s: %s — exiting with rc=%d ON PURPOSE so the keeper restarts this job "
          "with the current code. This is NOT a crash." % (who, why, rc), flush=True)
    try:
        import escalation
        escalation.escalate("JANITOR", "CODEWATCH_RESTART",
                            "%s exited to pick up changed source (%s)" % (who, why),
                            evidence={"job": who, "restarts_this_hour": used + 1},
                            source=who, who="codewatch")
    except Exception:
        silence.note("codewatch.py:escalate")
    raise SystemExit(rc)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--digest", action="store_true", help="print the current src/ fingerprint")
    a = ap.parse_args()
    if a.digest:
        print(fingerprint())
        return 0
    print("CODEWATCH — every running job is a photograph of the code it started with")
    print("=" * 78)
    print("  current src/ fingerprint : %s" % fingerprint())
    try:
        with open(LEDGER, encoding="utf-8") as f:
            doc = json.load(f)
    except Exception:
        doc = {}
    cutoff = time.time() - 3600
    if not doc:
        print("  no source-change restarts recorded")
    for who, times in sorted(doc.items()):
        recent = [t for t in times if isinstance(t, (int, float)) and t > cutoff]
        print("  %-16s %d restart(s) in the last hour (budget %d)"
              % (who, len(recent), BUDGET_PER_HOUR))
    print("\n  rc=%d means 'my code changed, restart me'. It is not a crash." % RC_STALE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
