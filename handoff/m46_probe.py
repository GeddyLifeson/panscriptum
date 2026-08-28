"""M46 PROBE -- does running the drill gate inside a mutation sandbox delete the sandbox's
own copy of a TARGET module?

Run #35 measured that `<sandbox>/src/assay.py` was present after the import gate and after the
verify_math gate, and that a `--target all` run died on a bare FileNotFoundError for that exact
path about four minutes in -- which is roughly one drill run. The drill gate was the remaining
untested suspect. This runs it alone and stats the file on both sides.

Deliberately NOT a drill net: it is a one-shot measurement, and it must be able to report a
sandbox that is fine as clearly as one that is not.
"""
import os
import subprocess
import sys

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
sys.path.insert(0, SRC)
import mutate as M  # noqa: E402

_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def stat(root, label):
    hits = {}
    for t in M.TARGETS:
        p = os.path.join(root, "src", t)
        hits[t] = os.path.getsize(p) if os.path.isfile(p) else None
    print("%-14s %s" % (label, hits))
    return hits


def main():
    root = M.sandbox()
    print("sandbox:", root)
    try:
        before = stat(root, "before drill")
        n_before = len([f for f in os.listdir(os.path.join(root, "src")) if f.endswith(".py")])
        print("modules before:", n_before)
        cmd = [sys.executable, "src/drill.py"]
        p = subprocess.run(cmd, cwd=root, capture_output=True, text=True,
                           errors="replace", timeout=1800, creationflags=_NO_WIN)
        print("drill rc =", p.returncode)
        tail = (p.stdout or "").strip().splitlines()[-25:]
        print("--- drill stdout tail ---")
        for line in tail:
            print(line)
        if p.stderr and p.stderr.strip():
            print("--- drill stderr tail ---")
            for line in p.stderr.strip().splitlines()[-25:]:
                print(line)
        after = stat(root, "after drill")
        n_after = len([f for f in os.listdir(os.path.join(root, "src")) if f.endswith(".py")])
        print("modules after:", n_after)
        lost = [t for t in M.TARGETS if before[t] is not None and after[t] is None]
        print("VERDICT:", ("DRILL DESTROYS THE SANDBOX TARGETS: " + repr(lost)) if lost
              else "targets intact after drill; the drill gate is NOT the M46 cause")
    finally:
        M.reap_orphans(older_than=0)


if __name__ == "__main__":
    main()
