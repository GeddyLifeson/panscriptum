#!/usr/bin/env python3
"""
AUTOSTART — make the library survive a reboot, and make the supervisor survive its own death.

TWO GAPS THAT "FULLY AUTOMATED" DID NOT COVER
---------------------------------------------
Seven processes were running under `overnight.py` and every one of them was started by hand, in
this session, by me. That is automation of the WORK and not of the RUNNING, and the difference
shows up the first time the machine restarts: everything stops, nothing says so, and the
dashboard keeps serving the last numbers it had until somebody notices the timestamp.

    a reboot            kills all seven and nothing brings them back
    the supervisor dies  nothing restarts it, and it is what restarts everything else

The second is the sharper one. `overnight.py` is the thing that notices a job has stopped and
starts it again -- so it is the single point whose own failure is invisible by construction. It
watches everything except itself.

WHAT THIS INSTALLS
------------------
A Startup shortcut that runs the supervisor hidden at login, matching the pattern already on this
machine (`CooldownGuard.vbs`), and a watchdog loop inside it that checks the supervisor is alive
every few minutes and restarts it if not.

Nothing here is clever. It is the difference between a system that runs while somebody is
watching it and one that runs.
"""
import argparse
import os
import subprocess
# Every subprocess this module starts carries this flag -- owner directive, no console window may
# ever appear. Named once here and used at both call sites, the way allsweep.py, foreman.py,
# local_agent.py and mutate.py all do it: two independent re-spellings of the same expression are
# two places for the flag to be forgotten, and this module's whole job is running unattended.
_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

PY = sys.executable
STARTUP = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows",
                       "Start Menu", "Programs", "Startup")
VBS = os.path.join(STARTUP, "Panscriptum.vbs")
LOGDIR = os.path.join(HERE, "state")

# How often the watchdog looks. Long enough that it costs nothing, short enough that a supervisor
# that died at 3am is back before the night is wasted.
CHECK_SECONDS = 180

# A BUDGET ON STARTING. A watchdog with no budget is one bad answer away from being a respawn
# loop, and this module's own docstring is the incident report for that shape. A supervisor that
# genuinely died comes back on the FIRST start, so a second and third in the same hour are
# already evidence that starting is not the cure; a fourth is the loop. See watch().
MAX_STARTS_PER_HOUR = 3
START_WINDOW_SECONDS = 3600

# How many times _twin_watchdog asks the process table before conceding it cannot tell. See its
# docstring: neither of the two obvious answers to a transient failure is safe here, so the
# answer is to ask again rather than to guess.
TWIN_TRIES = 4
TWIN_RETRY_SECONDS = 5


def _log(msg):
    """One line into state/autostart.log, and never raise doing it.

    This is the watchdog's only voice. A watchdog that dies trying to complain is strictly worse
    than a quiet one, so every failure here is swallowed into the ledger instead.
    """
    try:
        # AND THE DIRECTORY IS MADE FIRST, the way overnight.log() has always done it. On a tree
        # where state/ does not exist yet -- a fresh checkout, or a clean that took it -- every
        # _log call raised, was swallowed into the ledger above, and this watchdog's ONLY voice
        # went mute with nothing in the log to say so. The auditability of the start budget is
        # what its own docstring calls the whole difference between a watchdog and a fork bomb.
        os.makedirs(LOGDIR, exist_ok=True)
        with open(os.path.join(LOGDIR, "autostart.log"), "a", encoding="utf-8") as f:
            f.write("[" + time.strftime("%Y-%m-%d %H:%M:%S") + "] " + msg + chr(10))
    except Exception:
        silence.note("autostart.py:log")


def _launcher_py():
    """The interpreter to BAKE INTO the launcher: pythonw.exe where one exists beside PY.

    `PY = sys.executable` is right for the children this module spawns, because every one of
    those carries `_NO_WIN` and Windows honours it. The .vbs has no such flag -- WScript.Shell
    only gets a window STYLE -- so the interpreter itself is the only place the owner's "no
    console window may ever appear" directive can be enforced at logon.

    IT ALSO MAKES THE NEW STALENESS TEST HONEST. The launcher installed on this machine runs
    `pythonw.exe` while `sys.executable` under an interactive shell is `python.exe`, so a body
    built from PY differs from what is on disk in exactly one word -- and installed_state()
    would have reported a perfectly good launcher as STALE and invited an operator to overwrite
    it with the console-allocating twin. Falls back to PY when there is no pythonw beside it
    (a non-Windows tree, or an embedded interpreter), which is the honest answer there.
    """
    base, name = os.path.split(PY)
    if name.lower() == "python.exe":
        cand = os.path.join(base, "pythonw.exe")
        if os.path.exists(cand):
            return cand
    return PY


def _vbs_body():
    """A hidden launcher. WScript.Shell with window style 0 leaves no console behind.

    The watchdog runs INSIDE this, not as a separate service, so there is exactly one thing to
    install and exactly one thing to remove.
    """
    # Chr(34), not a nested quote. VBScript has no escape character -- a literal quote inside a
    # string is written by doubling it, and the paths here are full of quotes AND backslashes.
    # The obvious f-string produced `sh.Run ""C:\..." -u "..."`, which VBScript reads as an
    # empty string followed by a syntax error, and Windows would have failed it silently at
    # every login. A launcher that never launches is the worst kind of automation: it looks
    # installed.
    q = ' & Chr(34) & '
    script = os.path.join(SRC, "autostart.py")
    cmd = ('Chr(34) & "' + _launcher_py() + '"' + q + '" -u "' + q + '"' + script + '"' + q +
           '" --watch"')
    return (
        'Set sh = CreateObject("WScript.Shell")' + chr(10) +
        'sh.CurrentDirectory = "' + HERE + '"' + chr(10) +
        'sh.Run ' + cmd + ', 0, False' + chr(10)
    )


def installed_state():
    """What is actually in the Startup folder -> 'current' | 'stale' | 'absent' | 'unreadable'.

    EXISTENCE IS NOT INSTALLATION. `--status` used to print "installed" off a bare
    os.path.exists(VBS), and there are two real states it cannot see. A write interrupted
    part-way (a kill, a full disk, or this machine's documented Norton interference) leaves a
    syntactically broken .vbs that Windows fails SILENTLY at every logon -- the exact failure
    `_vbs_body`'s own docstring is written about: "a launcher that never launches is the worst
    kind of automation: it looks installed". And PY, HERE and SRC are BAKED IN at install time,
    so moving the checkout or the interpreter leaves a launcher that exists, parses, runs, and
    starts nothing. Both read as "installed" to an existence test and neither is.
    """
    if not os.path.exists(VBS):
        return "absent"
    try:
        with open(VBS, encoding="utf-8") as f:
            on_disk = f.read()
    except Exception:
        silence.note("autostart.py:vbs-read")
        return "unreadable"
    return "current" if on_disk == _vbs_body() else "stale"


def install():
    """Write the Startup launcher, land it atomically, and READ IT BACK. -> (path, verdict).

    This was a plain truncating `open(VBS, "w")` followed by `return VBS, "installed"` with no
    readback -- on the one file in this module whose whole purpose is to survive a reboot
    unattended, and which nothing ever exercises until the next logon, when the only symptom of
    a bad write is that nothing happens. Every other shared-state write in this tree goes
    through silence.replace_retry for exactly this reason. Landing through a pid-named temp also
    means an interrupted write leaves the PREVIOUS working launcher in place rather than a
    half-file. (order e4d9dbe599a2)
    """
    if not os.path.isdir(STARTUP):
        return None, "no Startup folder on this machine"
    body = _vbs_body()
    tmp = "%s.%d.tmp" % (VBS, os.getpid())
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(body)
    except Exception:
        silence.note("autostart.py:vbs-tmp")
        return VBS, "WRITE FAILED (could not create the temp file beside it)"
    if not silence.replace_retry(tmp, VBS):
        # replace_retry never raises and has already recorded the denial; the previous launcher,
        # if any, is untouched, which is the right outcome -- a stale launcher beats none.
        return VBS, "WRITE DENIED (something is holding it open); the previous launcher stands"
    state = installed_state()
    if state != "current":
        return VBS, "WROTE BUT READBACK DIFFERS (%s) -- do NOT trust this launcher" % state
    return VBS, "installed"


def uninstall():
    if os.path.exists(VBS):
        os.remove(VBS)
        return True
    return False


def supervisor_alive():
    """Is the supervisor up? -> True, False, or None meaning COULD NOT TELL.

    THREE ANSWERS, NOT TWO. This returned a bool, so every failure on the way to the answer --
    a WMI hiccup, psutil losing a race with a process that was exiting anyway, `overnight`
    momentarily unimportable while its file is being written -- was converted into "dead". And
    "dead" is the word `watch()` acts on: it starts a supervisor, then asks again 180 seconds
    later, and if the instrument is still broken it starts another one. The module docstring at
    the top of this file is the incident report for exactly that shape (three watchdogs, each
    restarting the others' supervisors, respawning in a loop) -- so this defect was the one thing
    this module exists to prevent, sitting in the sensor the prevention depends on.

    An inability to observe is not an observation. `None` says so, and the callers below decline
    to act on it. That refusal is the whole difference between a watchdog and a fork bomb.

    AND THE SENSOR CAN NOW SAY IT TOO (order 1d556b6ef535). This used to be `bool(...)` around
    `ON.running`, which was itself a two-answer function: a PowerShell/CIM probe that failed
    came back as `''` and became False here, so the `None` branch below was reachable only
    through an import error and the "DO NOT ACT ON A BLIND SPOT" path in `watch()` never fired
    for the failure mode it was written for. `overnight.running()` now answers None for an
    unreadable process table; it is passed straight through rather than collapsed.
    """
    try:
        import overnight as ON
        up = ON.running("overnight.py")
        return None if up is None else bool(up)
    except Exception:
        silence.note("autostart.py:alive")
        return None


def start_supervisor(read_hours=10):
    """Launch the supervisor detached, with its own logs.

    Detached deliberately: the watchdog must be able to die without taking the supervisor with
    it, and vice versa. Two processes that can only fail together are one process wearing a
    disguise.

    THE DIRECTORY IS MADE FIRST, matching `_log` (order 6d3eb126941f). On a tree where state/
    does not exist yet -- a fresh checkout, or a clean that took it -- this used to open the two
    log files with no `os.makedirs` first, so `--install` on such a tree printed "installed" and
    then died on an uncaught FileNotFoundError from this open() -- a success line immediately
    followed by a crash, on the one command whose whole job is to be trusted unattended.
    """
    os.makedirs(LOGDIR, exist_ok=True)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    out = open(os.path.join(LOGDIR, "overnight_stdout.log"), "a", encoding="utf-8")
    err = open(os.path.join(LOGDIR, "overnight_stderr.log"), "a", encoding="utf-8")
    flags = 0
    if os.name == "nt":
        flags = _NO_WIN | subprocess.DETACHED_PROCESS
    try:
        return subprocess.Popen(
            [PY, "-u", os.path.join(SRC, "overnight.py"), "--read-hours", str(read_hours)],
            cwd=HERE, env=env, stdout=out, stderr=err, creationflags=flags)
    finally:
        # The child inherits its own duplicate of each handle when Popen creates it, so the
        # parent's copies do nothing after Popen returns -- except sit open. `watch()` calls
        # this once per supervisor restart from an infinite loop, so a long-lived watchdog that
        # has restarted the supervisor N times was holding 2N handles open for no reason.
        out.close()
        err.close()


def _twin_watchdog():
    """Is another `autostart.py --watch` FROM THIS TREE already running (excluding self)?

    THIS TREE'S COPY, NOT ANY FILE OF THAT NAME. The test used to be `"autostart.py" in cmd`, a
    raw substring of a command line, and that is the same defect fixed in `codewatch.twins()` on
    2026-08-25 -- where matching a bare filename meant a process running a DIFFERENT checkout's
    namesake counted as a twin, and a sandboxed temp copy of `verify_math.py` raised a real halt.
    Here the consequence is worse in kind, because the answer is acted on by standing DOWN: a
    `--watch` started inside `mutate.py`'s throwaway sandbox, or in the export tree, or in any
    second checkout on this machine, would make the LIVE watchdog exit and leave the supervisor
    unwatched until the next logon. A guard that can be switched off by a copy of itself is a
    guard that reports its own outage as caution.

    So the resolution work is delegated to `codewatch.twins()` rather than re-spelled here: it
    already requires the interpreter to be python, already picks out the SCRIPT rather than any
    mention of the name, already resolves a relative path against the process's own cwd, and
    already fails open when it cannot tell whose copy it is. Two implementations of one rule is
    how the two sites drifted apart in the first place. `--watch` is then checked on the survivors,
    because a one-shot `--status` in this tree is not a twin of anything.

    AND THE FAIL-OPEN IS RETRIED, AND SAID ALOUD. This conceded on the first exception and said
    nothing. Neither obvious repair is right: failing CLOSED means one transient hiccup at boot
    leaves the supervisor unwatched until next logon, since nothing restarts the `.vbs`; and
    moving the check inside `watch()`'s loop creates a mutual-suicide race where two watchdogs
    each see the other and both exit -- the startup-only check avoids that BY DESIGN, because
    only the newcomer ever runs it. The middle is to ask again a few times before conceding, and
    to write the concession into `autostart.log` so that "there may now be two watchdogs" stops
    being a silent event nobody can find afterwards.
    """
    try:
        import psutil
        import codewatch
    except Exception:
        silence.note("autostart.py:twin-import")
        _log("FAILED OPEN: cannot tell whether another watchdog is running (psutil or "
             "codewatch unavailable); starting anyway -- if one was already up, there are "
             "now two, and two is the respawn incident in this module's docstring")
        return False
    why = "no reason recorded"
    for attempt in range(TWIN_TRIES):
        try:
            pids = codewatch.twins("autostart")
        except Exception as e:
            why = type(e).__name__
            silence.note("autostart.py:twin-query")
            time.sleep(TWIN_RETRY_SECONDS)
            continue
        for pid in pids:
            try:
                argv = psutil.Process(pid).cmdline()
            except Exception:
                # This one process vanished or is unreadable. It is not the whole answer, so
                # skip it rather than conceding the query -- the remaining pids still count.
                silence.note("autostart.py:twin-cmdline")
                continue
            if "--watch" in argv:
                return True
        return False
    _log("FAILED OPEN: could not read the process table after %d tries (%s); starting a "
         "watchdog anyway -- if one was already up, there are now two" % (TWIN_TRIES, why))
    return False


def watch(read_hours=10):
    """Keep the supervisor alive. The one thing it cannot do for itself.

    ONE WATCHDOG. Three of these once ran at once -- the logon .vbs copy, a shell relaunch,
    and a PowerShell relaunch -- each starting supervisors on its own three-minute clock. The
    supervisors' foremen then treated each other's stacks as duplicates and shot them, and the
    whole arrangement respawned itself in a loop. A watchdog that finds a twin at startup
    exits; the twin is already doing the job.

    TWO THINGS NOW STAND BETWEEN THAT INCIDENT AND THIS LOOP, because the twin check alone only
    ever covered ONE of the two ways to stack supervisors:

      * `supervisor_alive()` may answer "I could not tell", and a blind spot is not a death.
        Starting on it made a broken instrument into a supervisor factory at twenty starts an
        hour.
      * even a genuine "dead" is BUDGETED. A supervisor that really died is back on the first
        start; a second and a third in the same hour are evidence that starting is not the cure,
        and a fourth is the loop itself. Past the budget this stops starting and says so, which
        leaves a person a line to read instead of a process table to untangle.
    """
    if _twin_watchdog():
        _log("another watchdog is already running; this one exits")
        return
    # STAMPED, AND THE STALENESS IS SAID OUT LOUD -- BUT NOT ACTED ON. (Order bee9d16f4174,
    # partial: this closes the VISIBILITY half only.)
    #
    # This is the longest-lived process in the kit: started by the Startup .vbs at logon, a bare
    # `while True` on a 180s sleep, and it had no codewatch check at all, so CLAUDE.md Hard Rule
    # -1's fourth property was in effect against it -- a Python process does not re-read its own
    # source. Every fix to autostart.py, including any change to MAX_STARTS_PER_HOUR or to the
    # tri-state sensor, was silently deferred to the next logon however green the drill was.
    #
    # WHY `stale()` AND NOT `exit_if_stale()`, WHICH IS THE HOUSE IDIOM EVERYWHERE ELSE
    # (foreman.py, overwatch.py, publish.py): rc=17 only helps a job that something restarts,
    # and as `_twin_watchdog`'s own docstring says, NOTHING RESTARTS THE .vbs. Exiting here would
    # convert "running old code" into "not running", which is strictly worse -- the supervisor
    # would then be unwatched until the next logon. Pairing the exit with a keeper entry for this
    # watchdog or with a self-relaunch is a design decision (a self-relaunch races its own twin
    # check: the replacement starts while this process is still in the table, sees a twin, and
    # exits, leaving nothing), so it is left to the shift and the order stays open for it.
    #
    # What can be done without that ruling is refuse to let the condition be silent. A person
    # reading autostart.log now learns that this watchdog is on old code, and what to do about it.
    #
    # AND NOT `codewatch.claim_singleton("autostart")`, WHICH THE ORDER ALSO ASKS FOR. That
    # helper is `twins(who)` plus an exit, and `_twin_watchdog()` above is the STRICTER version
    # of the same idea: it additionally requires "--watch" in the candidate's argv. autostart.py
    # is also invoked as `--install` and `--status`, so a bare twins() check would see a
    # concurrent `--status` run as a twin and exit the only watchdog on the machine. Swapping it
    # in would be a regression, so the singleton half of that order is already satisfied, by the
    # better instrument. (checked maintenance-2026-08-29 queueC05)
    try:
        import codewatch
        codewatch.stamp("autostart")
    except Exception:
        silence.note("autostart.py:codewatch-stamp")
        codewatch = None
    starts = []                 # when this watchdog started a supervisor, for the hourly budget
    said_unknown_at = 0.0       # all three of these are rate-limited: at CHECK_SECONDS a
    said_budget_at = 0.0        # persistent condition would otherwise write twenty identical
    said_stale_at = 0.0         # lines an hour
    while True:
        try:
            alive = supervisor_alive()
            now = time.time()
            if codewatch is not None and now - said_stale_at >= START_WINDOW_SECONDS:
                is_stale, why = codewatch.stale("autostart")
                if is_stale:
                    said_stale_at = now
                    _log("THIS WATCHDOG IS RUNNING OLD CODE (%s). It does NOT exit on that, "
                         "because nothing restarts the Startup .vbs and exiting would leave the "
                         "supervisor unwatched until the next logon -- worse than lag. Every "
                         "change to autostart.py since this process started takes effect at the "
                         "NEXT LOGON and not before. To apply one now: kill this process and run "
                         "%s src/autostart.py --watch" % (why, PY))
            if alive is None:
                # DO NOT ACT ON A BLIND SPOT. See supervisor_alive().
                if now - said_unknown_at >= START_WINDOW_SECONDS:
                    said_unknown_at = now
                    _log("cannot tell whether the supervisor is running, so NOT starting one "
                         "-- an inability to observe is not a death. Will keep looking.")
            elif not alive:
                starts = [t for t in starts if now - t < START_WINDOW_SECONDS]
                if len(starts) >= MAX_STARTS_PER_HOUR:
                    if now - said_budget_at >= START_WINDOW_SECONDS:
                        said_budget_at = now
                        _log("supervisor is down and %d start(s) in the last hour did not fix "
                             "it; NOT starting another. This is deeper than a crash and needs "
                             "a person -- respawning past this point is the loop, not the cure."
                             % len(starts))
                else:
                    start_supervisor(read_hours)
                    starts.append(now)
                    _log("supervisor was not running; started it (%d of %d allowed this hour)"
                         % (len(starts), MAX_STARTS_PER_HOUR))
        except Exception as e:
            silence.note("autostart.py:watch")
            # THE MESSAGE NAMES THE EXCEPTION'S OWN STR, NOT JUST ITS CLASS (order 6d3eb126941f).
            # "watchdog error: FileNotFoundError" does not say which file or directory was
            # missing, so a missing state/ (which this loop self-heals: `_log` above makes the
            # directory on its way out, and `starts` is not appended, so no start budget is
            # consumed) read identically to any other FileNotFoundError in autostart.log. The str
            # is what makes the two conditions distinguishable after the fact.
            _log("watchdog error: %s: %s" % (type(e).__name__, e))
        time.sleep(CHECK_SECONDS)


def main():
    ap = argparse.ArgumentParser(description="survive a reboot, and the supervisor's own death")
    ap.add_argument("--install", action="store_true", help="add the Startup launcher")
    ap.add_argument("--uninstall", action="store_true", help="remove it")
    ap.add_argument("--watch", action="store_true", help="run the watchdog loop")
    ap.add_argument("--status", action="store_true", help="what is installed and running")
    ap.add_argument("--read-hours", type=float, default=10)
    a = ap.parse_args()

    if a.uninstall:
        print("removed" if uninstall() else "nothing installed")
        return 0
    if a.install:
        path, why = install()
        print(f"{why}: {path}" if path else why)
        # THE VERDICT REACHES THE EXIT CODE. install() can now come back "WRITE DENIED" or
        # "WROTE BUT READBACK DIFFERS", and a caller that reads rc must not see those as a
        # clean install -- this is the one file whose failure is invisible until the next
        # logon. Matches the gated-write pattern grounding.py and allsweep.py already use.
        if why != "installed":
            return 1
        # `is False`, not `not`. With a tri-state sensor a bare truth test starts a supervisor on
        # "could not tell" -- and doing that during an install, when a supervisor is very likely
        # already up, is how the second one gets born. Only a definite NO starts anything.
        alive = supervisor_alive()
        if alive is False:
            start_supervisor(a.read_hours)
            print("supervisor started")
        elif alive is None:
            print("could not tell whether the supervisor is running; started nothing")
        return 0
    if a.watch:
        watch(a.read_hours)
        return 0

    # THE CONTENT, NOT MERELY THE PATH. See installed_state() for the two states an existence
    # test reports as "installed" while the machine boots to nothing.
    _vbs_state = installed_state()
    print("Startup launcher : " + {
        "current": "installed (current)",
        "stale": "installed but STALE — the baked-in paths no longer match; rerun --install",
        "unreadable": "PRESENT BUT UNREADABLE — rerun --install",
        "absent": "NOT installed",
    }[_vbs_state])
    _alive = supervisor_alive()
    print("supervisor       : " + ("running" if _alive else
                                   "UNKNOWN (could not read the process table)"
                                   if _alive is None else "NOT running"))
    try:
        import overnight as ON
        # THE SINGLE ROSTER, NOT A HAND-KEPT SUBSET OF IT. This used to be a six-item tuple
        # typed out here, and it had already drifted from `ON.STANDING`: it named "feats.py"
        # where the roster's own entry is "feats.py --roll" (a real fragment-with-argument,
        # per `_cmd_is_running`'s own docstring, not a mention), and it had no entry at all for
        # `pipeline`, which joined STANDING after this tuple was written -- so `--status` could
        # print every job on ITS list green while pipeline.py was down. `ON.ALL_JOBS` is the
        # roster its own comment in overnight.py says exists so nothing keeps a partial copy;
        # `autostart.py`/`overnight.py` are skipped here because this report already named them
        # above, as the launcher and supervisor lines.
        # AND THE TRI-STATE IS KEPT, exactly as the supervisor line ten lines above already keeps
        # it (sweep 44, batch 3). `overnight.running()` returns None -- not False -- when the
        # probe could not read the process table, and its own docstring says callers "test
        # `is None` explicitly rather than leaning on truthiness". This loop leaned on
        # truthiness, so "I could not see" was printed as "not running": the one answer an
        # operator acts on, produced by the one condition that means nobody knows. That is the
        # FAIL-CLOSED property inverted -- a report that answers "I don't know" with a confident
        # negative -- and it sat four lines under the same file's correct handling of the same
        # tri-state for the supervisor, which is how a reader learns the wrong one is deliberate.
        for job in ON.ALL_JOBS:
            if job in ("autostart.py", "overnight.py"):
                continue
            _up = ON.running(job)
            print(f"  {job:<16}" + ("running" if _up else
                                    "UNKNOWN (could not read the process table)"
                                    if _up is None else "not running"))
    except Exception:
        silence.note("autostart.py:status")
    return 0


if __name__ == "__main__":
    sys.exit(main())
