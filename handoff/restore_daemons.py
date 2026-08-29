"""Bring the library's daemons back after run #36b stopped them for the synthesis restore.

`autostart.py --watch` is the top of the tree: it keeps `overnight.py` alive, and overnight's
keeper re-asserts the STANDING set (foreman, overwatch, publish, pipeline, read) within about
five minutes. So the correct restore is to start ONE thing and let the machine rebuild itself,
rather than hand-starting six and racing the keeper for ownership of each.

Written as a file rather than a heredoc: the paths are full of backslashes.
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYW = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
AUTOSTART = os.path.join(HERE, "src", "autostart.py")
_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_DETACHED = 0x00000008


def running():
    """-> {name: pid} for the project's own python daemons."""
    o = subprocess.run(["powershell", "-NoProfile", "-Command",
                        'Get-CimInstance Win32_Process | Where-Object { $_.Name -eq '
                        '"pythonw.exe" } | Select-Object ProcessId,CommandLine | ConvertTo-Json'],
                       capture_output=True, text=True, errors="replace")
    import json
    try:
        rows = json.loads(o.stdout or "[]")
    except ValueError:
        return {}
    rows = rows if isinstance(rows, list) else [rows]
    out = {}
    for r in rows:
        cl = r.get("CommandLine") or ""
        if "panscriptum-library-kit" not in cl and "src/" not in cl:
            continue
        for name in ("autostart", "overnight", "foreman", "overwatch", "publish",
                     "pipeline", "read", "dashboard", "magnitude"):
            if name + ".py" in cl:
                out.setdefault(name, r["ProcessId"])
    return out


def main():
    before = running()
    print("running before:", before or "(none)")
    if "autostart" not in before:
        if not os.path.isfile(PYW):
            raise SystemExit("pythonw not found at %s" % PYW)
        subprocess.Popen([PYW, "-u", AUTOSTART, "--watch"], cwd=HERE,
                         creationflags=_NO_WIN | _DETACHED,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("started autostart.py --watch")
    else:
        print("autostart already up; the keeper will re-assert the rest")
    time.sleep(12)
    print("running after :", running())
    print("\nThe keeper re-asserts the STANDING set on its own cycle (~5 min). If foreman, "
          "overwatch, publish, pipeline and read are not all back within that, check "
          "state/overnight.log.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
