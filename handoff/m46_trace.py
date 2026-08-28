"""WHICH drill net deletes the mutation sandbox? Trace it rather than guess.

`handoff/m46_probe.py` established the fact: run `drill.py` with its cwd inside a mutation
sandbox and the sandbox's own `src/` goes from 113 modules to 2. That is M46 -- the bare
FileNotFoundError on `<sandbox>/src/assay.py` four minutes into `mutate.py --target all`, which
has blocked the entire mutation mandate for two runs.

The fact is not the cause. This finds the cause by running drill inside the sandbox with
`shutil.rmtree`, `os.remove` and `os.unlink` wrapped so that any call whose target contains the
sandbox root prints a full stack trace before it proceeds. The first such trace names the net.

Wrapping rather than blocking: a blocked delete would change drill's behaviour and could send
the run down a different path than the one that actually does the damage.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)
import mutate as M  # noqa: E402

_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

SHIM = '''"""Injected tracer -- not part of the library. Wraps the three delete calls and
reports any that lands inside this sandbox, with the stack that asked for it."""
import os
import shutil
import sys
import traceback

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.environ["M46_LOG"]   # OUTSIDE the sandbox: the first tracer put its own
                              # log inside the tree being deleted, so the reap
                              # destroyed the evidence and reported "no events".


def _inside(path):
    """Any mutation sandbox, not only this one -- a global reap kills siblings too."""
    try:
        return "panscriptum_mutate_" in os.path.abspath(str(path)).lower()
    except Exception:
        return False


def _report(kind, path):
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write("\\n=== %s -> %s\\n" % (kind, path))
        fh.write("".join(traceback.format_stack()[:-1]))


_rmtree, _remove, _unlink, _rmdir = shutil.rmtree, os.remove, os.unlink, os.rmdir


def rmtree(path, *a, **k):
    if _inside(path):
        _report("rmtree", path)
    return _rmtree(path, *a, **k)


def remove(path, *a, **k):
    if _inside(path):
        _report("remove", path)
    return _remove(path, *a, **k)


def unlink(path, *a, **k):
    if _inside(path):
        _report("unlink", path)
    return _unlink(path, *a, **k)


def rmdir(path, *a, **k):
    if _inside(path):
        _report("rmdir", path)
    return _rmdir(path, *a, **k)


shutil.rmtree, os.remove, os.unlink, os.rmdir = rmtree, remove, unlink, rmdir

sys.argv = ["drill.py"]
sys.path.insert(0, os.path.join(ROOT, "src"))
with open(os.path.join(ROOT, "src", "drill.py"), encoding="utf-8") as fh:
    _body = fh.read()
exec(compile(_body, os.path.join(ROOT, "src", "drill.py"), "exec"),
     {"__name__": "__main__", "__file__": os.path.join(ROOT, "src", "drill.py")})
'''


def main():
    root = M.sandbox()
    print("sandbox:", root)
    shim = os.path.join(root, "_trace_shim.py")
    logpath = os.path.join(HERE, "handoff", "m46_deletes.log")
    if os.path.isfile(logpath):
        os.remove(logpath)
    with open(shim, "w", encoding="utf-8") as fh:
        fh.write(SHIM)
    n_before = len([f for f in os.listdir(os.path.join(root, "src")) if f.endswith(".py")])
    print("modules before:", n_before)
    env = dict(os.environ, M46_LOG=logpath, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, shim], cwd=root, capture_output=True, text=True,
                       errors="replace", timeout=2400, creationflags=_NO_WIN, env=env)
    print("rc =", p.returncode)
    try:
        n_after = len([f for f in os.listdir(os.path.join(root, "src")) if f.endswith(".py")])
    except OSError:
        n_after = -1
    print("modules after:", n_after)
    log = logpath
    if os.path.isfile(log):
        with open(log, encoding="utf-8") as fh:
            body = fh.read()
        print("delete events:", body.count("==="), "-> handoff/m46_deletes.log")
        print(body[:6000])
    else:
        print("NO delete events recorded inside the sandbox")
        print("--- stderr tail ---")
        for line in (p.stderr or "").strip().splitlines()[-20:]:
            print(line)
    M.reap_orphans(older_than=0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
