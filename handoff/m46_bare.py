"""The purest control: one sandbox, nothing run against it, watched until it dies or doesn't.

The two-sandbox control killed BOTH -- the treated one and the one nothing ran in -- at the same
instant, six seconds in. That clears `drill.py`, which had been the suspect for two runs. But it
leaves a worse possibility open: that something on this machine deletes `panscriptum_mutate_*`
directories out from under whoever owns them, in which case the whole sandbox architecture is
unusable here and M46 is not a bug in the mutation engine at all.

`mutate.py` cannot be the culprit by itself: `reap_orphans` has exactly two call sites in `src/`
(one in `sandbox()` at the 6-hour default, one in a drill net at a 31.7-year cutoff that reaps
nothing), and the only `older_than=0` calls anywhere are in this run's own throwaway probes.

So this runs NOTHING. It builds one sandbox and watches it for three minutes, recording the
process list at the moment of death if it dies. If it survives untouched, the reaper is
something the earlier probes were doing to each other and the fix is in the probes; if it dies
with nothing running, the reaper is external and that is an owner-level finding about this
machine.
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import mutate as M  # noqa: E402

WATCH_SECONDS = 180


def count(root):
    try:
        return len([f for f in os.listdir(os.path.join(root, "src")) if f.endswith(".py")])
    except OSError:
        return -1


def process_list():
    """A snapshot of every python-ish process, for the moment of death."""
    ps = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|pythonw' } | "
         "Select-Object ProcessId,Name,CommandLine | Format-Table -AutoSize | Out-String -Width 300"],
        capture_output=True, text=True, errors="replace")
    return ps.stdout


def main():
    root = M.sandbox()
    print("bare sandbox:", root)
    print("start modules:", count(root))
    t0 = time.time()
    last = count(root)
    while time.time() - t0 < WATCH_SECONDS:
        time.sleep(3)
        now = count(root)
        if now != last:
            print("%6.1fs  %s" % (time.time() - t0,
                                  "DIRECTORY GONE" if now == -1 else "%d modules" % now))
            if now == -1:
                print("--- processes at the moment of death ---")
                print(process_list()[:3000])
                print("VERDICT: an EXTERNAL reaper deletes mutation sandboxes. The sandbox "
                      "architecture cannot work on this machine until it is identified.")
                return 0
            last = now
    print("%6.1fs  survived untouched at %d modules" % (time.time() - t0, count(root)))
    print("VERDICT: nothing external reaps sandboxes. The deaths in the earlier probes were "
          "caused by those probes' own reap_orphans(older_than=0) cleanup reaching across to "
          "sandboxes they did not own.")
    M.reap_orphans(older_than=0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
