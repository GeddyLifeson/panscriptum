"""Is the reaper OURS (matching on the sandbox prefix) or GENERIC (sweeping TEMP)?

A bare sandbox with nothing running against it was deleted anyway, which clears `drill.py` and
makes M46 an interference bug rather than a mutation-engine bug. The remaining fork decides who
owns the fix:

  * if only the `panscriptum_mutate_` directory dies and an identically-shaped one under a
    different prefix survives, the reaper is CODE IN THIS PROJECT matching that prefix, and one
    of the five standing daemons is calling it;
  * if BOTH die, nothing here is doing it -- something on this machine sweeps TEMP, and the fix
    is to stop building sandboxes in TEMP at all.

Three directories are watched: a real sandbox, a same-shaped decoy under a neutral prefix, and
a decoy under a prefix that merely CONTAINS the project's name -- which separates "matches the
sandbox prefix exactly" from "matches anything panscriptum-ish".
"""
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import mutate as M  # noqa: E402

WATCH_SECONDS = 240


def decoy(prefix):
    """A directory shaped like a sandbox but built by hand, so nothing of ours made it."""
    root = tempfile.mkdtemp(prefix=prefix)
    os.makedirs(os.path.join(root, "src"), exist_ok=True)
    for i in range(20):
        with open(os.path.join(root, "src", "mod%02d.py" % i), "w", encoding="utf-8") as fh:
            fh.write("# filler\n")
    return root


def count(root):
    try:
        return len([f for f in os.listdir(os.path.join(root, "src")) if f.endswith(".py")])
    except OSError:
        return -1


def main():
    watched = [
        ("real sandbox      ", M.sandbox()),
        ("neutral prefix    ", decoy("zzdrilldecoy_")),
        ("panscriptum-ish   ", decoy("panscriptum_decoy_")),
    ]
    for label, root in watched:
        print("%s %s  (%d modules)" % (label, root, count(root)))
    print("\nwatching for %ds -- started %s\n" % (WATCH_SECONDS, time.strftime("%H:%M:%S")))

    last = {label: count(root) for label, root in watched}
    t0 = time.time()
    while time.time() - t0 < WATCH_SECONDS:
        time.sleep(2)
        for label, root in watched:
            now = count(root)
            if now != last[label]:
                print("%6.1fs  %s  %s  [%s]"
                      % (time.time() - t0, label,
                         "GONE" if now == -1 else "%d modules" % now,
                         time.strftime("%H:%M:%S")))
                last[label] = now

    print("\nfinal:")
    for label, root in watched:
        print("  %s %s" % (label, "GONE" if count(root) == -1 else "%d modules" % count(root)))
    real, neutral, ish = (count(r) for _l, r in watched)
    if real == -1 and neutral >= 0 and ish >= 0:
        print("\nVERDICT: the reaper matches the SANDBOX PREFIX. It is code in this project, "
              "and one of the standing daemons is calling it.")
    elif real == -1 and neutral == -1:
        print("\nVERDICT: something sweeps TEMP generically. Not this project's code; sandboxes "
              "must not live in TEMP.")
    elif real >= 0:
        print("\nVERDICT: nothing died this window. The reap is intermittent -- correlate with "
              "the daemon loop periods rather than concluding it is fixed.")
    for _l, r in watched:
        if not r.startswith(tempfile.gettempdir()):
            continue
        if "zzdrilldecoy_" in r or "panscriptum_decoy_" in r:
            shutil.rmtree(r, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
