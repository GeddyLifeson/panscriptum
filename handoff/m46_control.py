"""THE CONTROL RUN #35 AND THIS RUN BOTH SKIPPED.

Two measurements so far agree that a mutation sandbox loses its modules while `drill.py` runs
inside it (113 -> 2, then 113 -> the directory gone). Both blamed drill, and the tracer that
wrapped `shutil.rmtree`, `os.remove` and `os.unlink` inside drill's own process recorded NOT ONE
delete. Those two facts cannot both point at drill, so one of them is being read wrong.

The obvious control was never run: build TWO sandboxes, run drill in only ONE, and watch both.

  * if only the drill sandbox dies, it is drill, and the tracer missed the call;
  * if BOTH die, drill is innocent and something else on this machine reaps sandboxes --
    which would make M46 an interference bug, not a mutation-engine bug at all, and would
    explain why it survived a stable tree with no agents editing anything.

The twin is polled while drill runs, so the moment of death is recorded rather than inferred
from a before-and-after pair. That is the difference between knowing what happened and knowing
only that something did.
"""
import os
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import mutate as M  # noqa: E402

_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_stop = threading.Event()


def count(root):
    """-> number of .py files in <root>/src, or -1 when the directory is gone."""
    try:
        return len([f for f in os.listdir(os.path.join(root, "src")) if f.endswith(".py")])
    except OSError:
        return -1


def watch(label, root, log):
    """Poll one sandbox every two seconds and record every change in its module count."""
    last = count(root)
    log.append((0.0, label, last))
    t0 = time.time()
    while not _stop.is_set():
        time.sleep(2)
        now = count(root)
        if now != last:
            log.append((time.time() - t0, label, now))
            last = now
            if now == -1:
                return


def main():
    treated = M.sandbox()
    control = M.sandbox()
    print("treated (drill runs here):", treated)
    print("control (nothing runs here):", control)
    print("start counts: treated=%d control=%d" % (count(treated), count(control)))

    log = []
    threads = [threading.Thread(target=watch, args=(lab, r, log), daemon=True)
               for lab, r in (("treated", treated), ("control", control))]
    for t in threads:
        t.start()

    t0 = time.time()
    p = subprocess.run([sys.executable, "src/drill.py"], cwd=treated, capture_output=True,
                       text=True, errors="replace", timeout=2400, creationflags=_NO_WIN)
    elapsed = time.time() - t0
    _stop.set()
    for t in threads:
        t.join(timeout=5)

    print("drill rc=%s after %.0fs" % (p.returncode, elapsed))
    print("\n--- module count timeline ---")
    for when, label, n in log:
        print("  %6.1fs  %-8s %s" % (when, label, "DIRECTORY GONE" if n == -1 else "%d modules" % n))
    ct, cc = count(treated), count(control)
    print("\nfinal: treated=%s control=%s" % (ct, cc))
    if ct < 100 and cc < 100:
        print("VERDICT: BOTH sandboxes died -- drill is NOT the cause. Something on this "
              "machine reaps panscriptum_mutate_* directories.")
    elif ct < 100:
        print("VERDICT: only the drill sandbox died -- drill IS the cause, and it deletes "
              "through a path the rmtree/remove/unlink tracer did not cover.")
    else:
        print("VERDICT: neither died. The failure did not reproduce this time.")
    for r in (treated, control):
        M.reap_orphans(older_than=0) if False else None
    return 0


if __name__ == "__main__":
    sys.exit(main())
