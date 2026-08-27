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
import contextlib
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
LEDGER_LOCK = LEDGER + ".lock"

# A read-modify-write of this small a doc never legitimately takes this long. A lock file
# older than this belongs to a process that died holding it, not one still working, so it is
# stolen rather than waited on forever.
LOCK_STALE_SECONDS = 30

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


def runs_script(argv, module, root=None, cwd=None):
    """PURE. Is this command line running `<root>/<module>.py` as its SCRIPT? -> bool.

    EXTRACTED SO IT CAN BE TESTED WITHOUT A PROCESS TABLE, which is the whole point. The drill
    net for this behaviour asked the LIVE process table twice -- `twins("verify_math") == []` --
    and twice halted the library against perfectly correct code, because the battery runs
    `verify_math.py` and `mutate.py` runs it again inside a sandbox. A net whose answer depends
    on what happens to be running when it looks is not testing anything; it is sampling the
    weather. Synthetic argv in, deterministic answer out.

    Three ways a command line can NAME this module without RUNNING it, all of them seen:

      * a linter -- `python -m pyflakes src/publish.py` -- which matched three daemons at once
        under the first implementation, and would have made each refuse to start;
      * an import -- `python -c "import publish"` -- which is not a second daemon;
      * ANOTHER TREE's copy -- `python /tmp/sandbox/src/publish.py` -- a real occurrence, since
        `mutate.py` deliberately runs the whole battery from a throwaway copy of `src/`.

    So: argv[0] must be python; the SCRIPT is the first argument that is a `.py` path (skipping
    interpreter flags, stopping at the first non-flag that is not one); and it must resolve to
    the same file as `<root>/<module>.py`. `-m` is not a script path, so `-m pyflakes x.py`
    stops at `pyflakes` and never reaches the filename.
    """
    root = root or SRC
    needle = module if module.endswith(".py") else module + ".py"
    if not argv or len(argv) < 2:
        return False
    if "python" not in os.path.basename(str(argv[0])).lower():
        return False
    script = None
    for arg in argv[1:]:
        a = str(arg).replace("\\", "/")
        if a.endswith(".py"):
            script = a
            break
        if not a.startswith("-"):
            break            # a non-flag, non-.py argument: this is not `python x.py`
    if not script or os.path.basename(script) != needle:
        return False
    resolved = script
    if not os.path.isabs(resolved):
        if not cwd:
            return False     # cannot tell whose copy it is -- FAIL OPEN
        resolved = os.path.join(cwd, resolved)
    target = os.path.join(root, needle)
    try:
        return os.path.samefile(resolved, target)
    except OSError:
        # One of them does not exist (a sandbox already reaped, a path from another machine).
        # Fall back to comparing normalised absolute paths rather than guessing.
        return os.path.normcase(os.path.abspath(resolved)) ==                os.path.normcase(os.path.abspath(target))


def twins(module, exclude_pid=None):
    """-> [pid] of other live processes running `src/<module>.py`.

    FOUND BY WATCHING IT HAPPEN. Minutes after the keeper was asked to restart three daemons it
    started **two `publish.py` processes seventeen seconds apart** -- one from the keeper's
    STANDING re-assertion, one from something else that noticed the same gap. Two publishers
    means two writers pushing into one export repo, which `publish.push` has a whole paragraph
    about: run #5 counted five silent-ish rejected pushes in a morning from exactly that.

    `autostart._twin_watchdog` already applies this idea to the watchdog, for the same reason
    and after a worse incident (three watchdogs, each restarting the others' supervisors, in a
    respawn loop). It was never generalised to the daemons the watchdog supervises.
    """
    # SELF-EXCLUSION IS NOT OPTIONAL, and `exclude_pid` used to REPLACE it rather than add to
    # it -- so `twins(m, exclude_pid=X)` stopped excluding this process and reported ITSELF as
    # its own twin. `claim_singleton` would then have stood a healthy daemon down because it
    # found itself. Found by the run #34 sweep reading the line, not by anything failing: no
    # caller passes `exclude_pid` today, so the bug was live, unreachable, and waiting.
    skip = {os.getpid()}
    if exclude_pid is not None:
        skip.add(exclude_pid)
    found = []
    try:
        import psutil
    except ImportError:
        return found                 # cannot tell; say so by finding nothing, and FAIL OPEN
    needle = module if module.endswith(".py") else module + ".py"
    # The matching itself lives in `runs_script` so it can be tested against SYNTHETIC command
    # lines. The drill net for this originally asserted `twins("verify_math") == []`, which was
    # true only when no `verify_math.py` happened to be running -- and the battery runs it as a
    # subprocess, so the net breached at random and halted the library. A net whose answer
    # depends on what is running at the moment it looks is not testing the code.
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            if proc.info["pid"] in skip:
                continue
            argv = proc.info.get("cmdline") or []
            # ONE PREDICATE, TESTED SEPARATELY. The matching used to be inline here, which meant
            # the only way to test it was to ask the live process table -- and the drill net that
            # did so halted the library twice against correct code. `runs_script` is pure and the
            # net puts synthetic command lines to it; this loop now just supplies the arguments.
            cwd = None
            try:
                cwd = proc.cwd()
            except Exception:
                cwd = None       # unreadable cwd: runs_script FAILS OPEN on a relative path
            if runs_script(argv, needle, root=SRC, cwd=cwd):
                found.append(proc.info["pid"])
        except Exception:
            continue
    return found


def claim_singleton(who, module=None, exit_code=0):
    """Exit quietly if a twin of this daemon is already running. -> [pid] of twins found.

    EXITS 0, NOT AN ERROR CODE. The twin is already doing the job, so nothing is wrong and
    nothing should be reported as wrong -- a non-zero exit here would have the keeper log a
    failure every time it lost a race with itself, and a log full of harmless failures is how
    a real one goes unread.

    FAILS OPEN. If `psutil` is missing or the process table cannot be walked, this finds no
    twins and the daemon starts. Refusing to start because we could not tell would convert an
    inability to observe into an outage, and an outage that reports itself as caution is the
    worst shape a safety can take.
    """
    others = twins(module or who)
    if not others:
        return []
    print("[codewatch] %s: another instance is already running (pid %s). This one exits; the "
          "twin is doing the job. Not an error." % (who, ", ".join(str(p) for p in others)),
          flush=True)
    try:
        import escalation
        escalation.escalate(escalation.JANITOR, "DAEMON_TWIN",
                            "%s found %d twin(s) at startup and exited" % (who, len(others)),
                            evidence={"job": who, "twins": others}, source=who, who="codewatch")
    except Exception:
        silence.note("codewatch.py:twin-escalate")
    raise SystemExit(exit_code)


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


@contextlib.contextmanager
def _ledger_lock(attempts=50, wait=0.05):
    """Serialise read-modify-write access to LEDGER across processes.

    `_record_restart` reads the whole ledger, adds ONLY ITS OWN key, and writes the whole
    ledger back -- and `silence.write_json` makes that final write atomic without making the
    READ-then-write atomic. foreman, overwatch and publish each call `exit_if_stale()`
    independently, and the normal case is one `src/` edit going stale for all three at once, so
    two or three daemons land in `_record_restart` within the same second. Each reads the
    pre-edit doc, mutates only its own key, and whichever writes last silently erases the
    others' entire restart history -- undercounting BUDGET_PER_HOUR exactly when multiple
    daemons are restarting together, which is the scenario the budget exists to catch.

    Same primitive `gpu_lane._take_slot` already uses for its lease files: `O_CREAT|O_EXCL` is
    atomic on Windows and POSIX alike, so creating the lock file IS the mutual exclusion, with
    no separate check-then-act window for two processes to both win.
    """
    for _ in range(attempts):
        try:
            os.close(os.open(LEDGER_LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            break
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(LEDGER_LOCK) > LOCK_STALE_SECONDS:
                    os.remove(LEDGER_LOCK)
                    continue
            except OSError:
                pass
            time.sleep(wait)
    else:
        # Could not get the lock inside the budget above. Proceed unlocked rather than lose this
        # restart record entirely -- matching gpu_lane's own "cannot arbitrate -- caller
        # proceeds unmetered": an occasional missed count is far cheaper than a daemon that
        # never restarts because a stuck lock file made it give up.
        yield
        return
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            os.remove(LEDGER_LOCK)


def _record_restart(who):
    with _ledger_lock():
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
        escalation.escalate(escalation.JANITOR, "CODEWATCH_RESTART",
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
