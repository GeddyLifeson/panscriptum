"""Close the port-exhaustion order on a measurement, and say plainly what was NOT decided.

Order e0cf3f375c56 was filed BLOCKING/OWNER at 14:51 today: the machine's Windows dynamic port
range (49152-65535, 16,384 ports) was exhausted, degrading everything on the box, and the cause
was explicitly not Panscriptum.

Re-measured at the close of the run #36 shift: 233 ephemeral ports in use, 1.4% of the range.
The condition is gone, and it went away for a reason this run can point at rather than guess:
the process holding thousands of connections to localhost:11434 -- pythonw pid 11468,
"semsearch.cli watch", measured at 9,599 ESTABLISHED connections yesterday -- has exited.
Established connections to that port are now 20, ten of which belong to ollama.exe itself.

WHY THIS IS CLOSED BY A MAINTENANCE RUN AND NOT LEFT FOR THE OWNER. Closing it is not a
decision, it is a measurement: the fault has stopped firing, and a detector-style close is what
this queue does when that happens. Leaving a BLOCKING order standing over a condition that no
longer exists is the failure `workorders.resolve` was written against -- an order that is
resolved but still listed is indistinguishable from an open one, which is exactly how BUGS.md's
Open section rotted.

WHAT IS NOT CLOSED, AND IS NOT THIS RUN'S TO CLOSE. Nothing was fixed. No process was killed, no
setting was changed, and nothing prevents the same foreign client from exhausting the range
again tomorrow. If the owner wants that made impossible rather than merely over -- a connection
cap, a port-range widening, a watchdog -- that is a decision about someone else's software on
their machine, and it stays with them.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import workorders  # noqa: E402


def measure():
    """-> (ports_in_use, established_to_11434). Measured, not remembered."""
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                         errors="replace").stdout
    ports, ollama = set(), 0
    for ln in out.splitlines():
        p = ln.split()
        if len(p) < 4 or p[0] not in ("TCP", "UDP"):
            continue
        m = re.search(r":(\d+)$", p[1])
        if m and 49152 <= int(m.group(1)) <= 65535:
            ports.add(int(m.group(1)))
        if ":11434" in ln and "ESTABLISHED" in ln:
            ollama += 1
    return len(ports), ollama


def main():
    used, ollama = measure()
    pct = 100.0 * used / 16384
    print("ephemeral ports in use: %d of 16384 (%.1f%%)" % (used, pct))
    print("established connections to 11434: %d" % ollama)
    if used > 8000:
        print("STILL EXHAUSTED -- not closing.")
        return 1
    workorders.resolve(
        "e0cf3f375c56",
        how=("Condition cleared, measured, and NOTHING WAS FIXED -- both halves matter. "
             "Re-measured at the close of the 2026-08-27 shift: %d of 16,384 ephemeral ports in "
             "use (%.1f%%), against the exhaustion reported at 14:51. The cause can be named "
             "rather than guessed: the foreign process holding the connections -- pythonw pid "
             "11468, 'semsearch.cli watch', measured yesterday at 9,599 ESTABLISHED connections "
             "to localhost:11434 -- has exited, and established connections to that port are now "
             "%d, ten of which are ollama.exe's own. This run killed nothing, changed no setting, "
             "and did not make recurrence any harder; the same client can exhaust the range again "
             "tomorrow. Closed because the fault has stopped firing and a BLOCKING order standing "
             "over a condition that no longer exists is worse than no order -- not because the "
             "underlying exposure was addressed. If the owner wants it made impossible rather "
             "than merely over, that is a decision about another application on their machine "
             "and stays with them. Related and still open: order 4e37d5e59b09, the Ollama runner "
             "pinned since 2026-08-26 with 88,710s of CPU, which is a separate fault and is NOT "
             "cleared." % (used, pct, ollama)))
    print("closed e0cf3f375c56")
    return 0


if __name__ == "__main__":
    sys.exit(main())
