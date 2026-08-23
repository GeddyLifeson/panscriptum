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
    cmd = ('Chr(34) & "' + PY + '"' + q + '" -u "' + q + '"' + script + '"' + q +
           '" --watch"')
    return (
        'Set sh = CreateObject("WScript.Shell")' + chr(10) +
        'sh.CurrentDirectory = "' + HERE + '"' + chr(10) +
        'sh.Run ' + cmd + ', 0, False' + chr(10)
    )


def install():
    if not os.path.isdir(STARTUP):
        return None, "no Startup folder on this machine"
    with open(VBS, "w", encoding="utf-8") as f:
        f.write(_vbs_body())
    return VBS, "installed"


def uninstall():
    if os.path.exists(VBS):
        os.remove(VBS)
        return True
    return False


def supervisor_alive():
    try:
        import overnight as ON
        return ON.running("overnight.py")
    except Exception:
        silence.note("autostart.py:alive")
        return False


def start_supervisor(read_hours=10):
    """Launch the supervisor detached, with its own logs.

    Detached deliberately: the watchdog must be able to die without taking the supervisor with
    it, and vice versa. Two processes that can only fail together are one process wearing a
    disguise.
    """
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    out = open(os.path.join(LOGDIR, "overnight_stdout.log"), "a", encoding="utf-8")
    err = open(os.path.join(LOGDIR, "overnight_stderr.log"), "a", encoding="utf-8")
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
    return subprocess.Popen(
        [PY, "-u", os.path.join(SRC, "overnight.py"), "--read-hours", str(read_hours)],
        cwd=HERE, env=env, stdout=out, stderr=err, creationflags=flags)


def _twin_watchdog():
    """Is another autostart --watch already running (any interpreter, excluding self)?"""
    import subprocess
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name='python.exe' or Name='pythonw.exe'\" | "
             "ForEach-Object { $_.ProcessId.ToString() + '|' + $_.CommandLine }"],
            capture_output=True, text=True, timeout=60,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    except Exception:
        return False
    me = os.getpid()
    for ln in out.splitlines():
        pid, _, cmd = ln.partition("|")
        try:
            if int(pid.strip()) == me:
                continue
        except ValueError:
            continue
        if "autostart.py" in cmd and "--watch" in cmd:
            return True
    return False


def watch(read_hours=10):
    """Keep the supervisor alive. The one thing it cannot do for itself.

    ONE WATCHDOG. Three of these once ran at once -- the logon .vbs copy, a shell relaunch,
    and a PowerShell relaunch -- each starting supervisors on its own three-minute clock. The
    supervisors' foremen then treated each other's stacks as duplicates and shot them, and the
    whole arrangement respawned itself in a loop. A watchdog that finds a twin at startup
    exits; the twin is already doing the job.
    """
    if _twin_watchdog():
        with open(os.path.join(LOGDIR, "autostart.log"), "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] another watchdog is already "
                    f"running; this one exits" + chr(10))
        return
    log = os.path.join(LOGDIR, "autostart.log")
    while True:
        try:
            if not supervisor_alive():
                start_supervisor(read_hours)
                with open(log, "a", encoding="utf-8") as f:
                    f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] supervisor was not "
                            f"running; started it{chr(10)}")
        except Exception as e:
            silence.note("autostart.py:watch")
            try:
                with open(log, "a", encoding="utf-8") as f:
                    f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] watchdog error: "
                            f"{type(e).__name__}{chr(10)}")
            except Exception:
                pass
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
        if not supervisor_alive():
            start_supervisor(a.read_hours)
            print("supervisor started")
        return 0
    if a.watch:
        watch(a.read_hours)
        return 0

    print("Startup launcher : " + ("installed" if os.path.exists(VBS) else "NOT installed"))
    print("supervisor       : " + ("running" if supervisor_alive() else "NOT running"))
    try:
        import overnight as ON
        for job in ("dashboard.py", "publish.py", "foreman.py", "overwatch.py",
                    "feats.py", "read.py"):
            print(f"  {job:<16}" + ("running" if ON.running(job) else "not running"))
    except Exception:
        silence.note("autostart.py:status")
    return 0


if __name__ == "__main__":
    sys.exit(main())
