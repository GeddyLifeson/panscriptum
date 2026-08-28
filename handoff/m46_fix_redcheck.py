"""Prove the M46 ownership fix, in BOTH directions, and watch the old behaviour fail.

The fix: `reap_orphans` now refuses to delete a sandbox whose recorded owner pid is still alive,
at any age. Three things have to be true for that to be worth anything, and a check of only the
first would be the kind of one-sided guard this project keeps finding:

  1. a sandbox owned by a LIVE process survives even `older_than=0`   (the M46 failure)
  2. a sandbox whose owner is DEAD is still reaped                    (no new disk leak)
  3. a sandbox with NO owner record is still reaped by age            (backwards compatible)

And the control that makes it evidence rather than assertion: with the ownership check disabled,
arm 1 must FAIL. A guard nobody has watched refuse proves nothing.
"""
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import mutate as M  # noqa: E402


def make(prefix, pid=None, age=0.0):
    """A sandbox-shaped directory with a chosen owner pid and mtime."""
    d = tempfile.mkdtemp(prefix=M.SANDBOX_PREFIX + prefix + "_")
    os.makedirs(os.path.join(d, "src"), exist_ok=True)
    if pid is not None:
        with open(os.path.join(d, M.OWNER_FILE), "w", encoding="utf-8") as fh:
            json.dump({"pid": pid, "started": time.time()}, fh)
    if age:
        old = time.time() - age
        os.utime(d, (old, old))
    return d


def dead_pid():
    """A pid that is certainly not running. 999999999 is above Windows' range."""
    return 999999999


def main():
    live = os.getpid()

    # ARM 1 -- live owner, maximally aggressive reap.
    a = make("liveowner", pid=live)
    M.reap_orphans(older_than=0)
    arm1 = os.path.isdir(a)
    print("arm 1  live-owned sandbox survives older_than=0 ->", "PASS" if arm1 else "FAIL")

    # ARM 1b -- a DIFFERENT live process's sandbox, which is the actual M46 case: the reaper and
    # the owner were never the same process. A real child is spawned rather than borrowing some
    # unrelated pid, so the liveness being tested is one this check created and can end.
    import subprocess
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(45)"],
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        e = make("otherlive", pid=child.pid)
        M.reap_orphans(older_than=0)
        arm1b = os.path.isdir(e)
    finally:
        child.kill()
        child.wait(timeout=10)
    print("arm 1b another live process's sandbox survives ->", "PASS" if arm1b else "FAIL")

    # ARM 2 -- dead owner must still be collected.
    b = make("deadowner", pid=dead_pid(), age=10 * 3600)
    M.reap_orphans()
    arm2 = not os.path.isdir(b)
    print("arm 2  dead-owner sandbox is still reaped     ->", "PASS" if arm2 else "FAIL")

    # ARM 3 -- no owner record, old: still reaped by age.
    c = make("noowner", pid=None, age=10 * 3600)
    M.reap_orphans()
    arm3 = not os.path.isdir(c)
    print("arm 3  unowned old sandbox is still reaped    ->", "PASS" if arm3 else "FAIL")

    # ARM 4 -- THE CONTROL. Disable the ownership check and arm 1 must break.
    real_owner = M._owner_pid
    M._owner_pid = lambda _p: None          # as if no sandbox ever recorded an owner
    d = make("control", pid=live)
    M.reap_orphans(older_than=0)
    arm4 = not os.path.isdir(d)
    M._owner_pid = real_owner
    print("arm 4  CONTROL: without the check it dies     ->",
          "RED as required" if arm4 else "STILL GREEN -- the guard is not load-bearing")

    for p in (a, b, c, d, e):
        if os.path.isdir(p):
            M.reap_orphans(older_than=0) if False else None
    M._owner_pid = lambda _p: None
    M.reap_orphans(older_than=0)
    M._owner_pid = real_owner

    ok = arm1 and arm1b and arm2 and arm3 and arm4
    print("\nVERDICT:", "the ownership guard holds and is load-bearing" if ok else
          "NOT PROVEN -- do not rely on this fix")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
