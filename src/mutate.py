"""MUTATE — break the library on purpose, and find out which safeties failed to notice.

THE STANDING LESSON, FINALLY MECHANISED. "A check that cannot fail looks exactly like a check
that passed" is the most-repeated finding in this project's ledger. `liveness.py` finds the
SHAPES of that -- dead functions, tautological comparisons, guards on undefined names -- but a
check can be live, well-formed, and still worthless because nothing it examines can ever come
out wrong. No static analysis can tell you that. Only breaking the code can.

So this is mutation testing, and the question it asks is the exact inverse of the one the
battery asks. The battery asks *does the library pass its checks*. This asks **would the library
still pass them if it were broken** -- and if the answer is yes, the check is furniture.

    a mutant is KILLED     something went red. The safeties noticed. Good.
    a mutant SURVIVES      the code was changed to something wrong and every check still
                           passed. That is a hole, and it is reported as one.

WHY THESE THREE MODULES AND NOT ALL 110. Mutation testing costs one full battery run per
mutant, and the battery takes minutes. Running it over 48,000 lines would take days and nobody
would ever do it twice. So it is pointed at the three files where a silent wrong answer does the
most damage and where the checks are densest enough that survivors are genuinely informative:

    assay.py         every published Moth Number and every error bar in the library
    prose_gate.py    the interlocks that stand between the catalogue and a written volume,
                     which is the gate whose DELETION cost 145 unauthorised chapters
    escalation.py    the chain of command and the halt -- if this can be broken silently,
                     nothing else here means anything

WHAT A SURVIVOR IS AND IS NOT. A survivor is not automatically a bug. Some mutations are
genuinely equivalent (changing a constant that only affects a log string), and some fall in code
that is deliberately untested. What a survivor IS, always, is a place where **the library cannot
tell the difference** between the real code and a corrupted version of it. That is worth
knowing even when the answer turns out to be "and that is fine", and the reason each one is
filed with its exact diff rather than a count.

HOW IT IS SAFE TO RUN. Every mutation is written to a real file, because a check that reads
from disk cannot be fooled by an in-memory patch -- and this project's checks read from disk
constantly. So the original bytes are captured first, restored in a `finally`, and verified
byte-for-byte afterwards. `--verify-restore` proves the restore works before any mutation is
applied, and refuses to start if it does not. **It will not run while a halt is standing**, and
it refuses to touch a file with uncommitted changes it did not make itself.
"""
import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SRC)
import escalation  # noqa: E402

_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# The files worth the wall clock. Ordered by how much a silent wrong answer costs.
TARGETS = ("assay.py", "prose_gate.py", "escalation.py")

# The checks a mutant must survive to count as surviving. Cheapest first so a mutant that is
# going to be killed is usually killed in seconds rather than minutes -- mutation testing is
# entirely bounded by how fast a killed mutant can be recognised.
#
# `verify_math` before `drill` deliberately: it is the faster of the two and it is where the
# assay arithmetic actually lives, so an assay mutation dies in its first gate.
GATES = (
    ("import", [sys.executable, "-c", "import sys; sys.path.insert(0,'src'); import assay,"
                " prose_gate, escalation"]),
    ("verify_math", [sys.executable, "src/verify_math.py"]),
    ("drill", [sys.executable, "src/drill.py"]),
)


# --------------------------------------------------------------------------- the lock
#
# THE INCIDENT THIS EXISTS BECAUSE OF, 2026-08-25, within an hour of this module being written.
# A mutation run was in progress -- `prose_gate.py` deliberately corrupted on disk, as designed
# -- when two other things touched the same file:
#
#   * a separate `drill.py` run read the mutated gate, found two nets failing, and **HALTED THE
#     LIBRARY**, which is precisely the "a safety that stops work is not a fault that stops work"
#     confusion recorded in CLAUDE.md, arriving from a direction nobody had guarded;
#   * `publish.py --push` synced the corrupted file and **SHIPPED A BROKEN PROSE GATE TO
#     GITHUB**, where `cited_fraction()` matched every source EXCEPT the one it was asked about.
#
# The second is the serious one. Mutation testing's whole method is putting wrong code on disk,
# so every other consumer of that disk has to know. This lock is how they know, and `publish.py`
# refuses to push while it is held.
#
# STALENESS IS HANDLED, because a lock that outlives its holder is an outage. The record carries
# the PID and the start time; `active()` treats a lock whose process is gone as absent, and says
# so rather than silently ignoring it.
LOCK = os.path.join(HERE, "state", "MUTATION_ACTIVE.json")
_TOKEN_ENV = "PANSCRIPTUM_MUTATION_TOKEN"


def _pid_alive(pid):
    """-> True if that PID is still running. Unknown counts as ALIVE.

    Fails toward "the lock is real". A false 'stale' releases the lock while a mutation run is
    genuinely mid-flight, which puts corrupted source back in reach of the publisher -- the
    exact failure this whole mechanism exists to prevent. A false 'alive' merely delays a push.
    """
    try:
        if os.name == "nt":
            r = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid], capture_output=True,
                               text=True, creationflags=_NO_WIN, timeout=30)
            return str(pid) in (r.stdout or "")
        os.kill(pid, 0)
        return True
    except Exception:
        return True


def active():
    """-> (bool, record). Is a mutation run putting wrong code on disk right now?"""
    try:
        with open(LOCK, encoding="utf-8") as f:
            rec = json.load(f)
    except FileNotFoundError:
        return False, None
    except Exception:
        # An unreadable lock is treated as HELD. If this file exists at all, something claimed
        # the right to corrupt the tree, and "I could not read the claim" is not permission.
        return True, {"unreadable": True}
    pid = rec.get("pid")
    if isinstance(pid, int) and not _pid_alive(pid):
        rec["stale"] = True
        return False, rec
    return True, rec


def _lock_acquire(targets, token):
    held, rec = active()
    if held:
        raise RuntimeError("a mutation run is already active (%s); refusing to start a second"
                           % json.dumps(rec)[:160])
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    with open(LOCK, "w", encoding="utf-8") as f:
        json.dump({"pid": os.getpid(), "started": time.time(),
                   "targets": list(targets), "token": token,
                   "warning": "SOURCE FILES IN src/ MAY BE DELIBERATELY CORRUPT RIGHT NOW. "
                              "Do not publish, and do not read a failing check as a real fault."},
                  f, indent=2)


def _lock_release():
    try:
        os.remove(LOCK)
    except FileNotFoundError:
        pass
    except Exception:
        # A lock we cannot remove will block every future push. Loud, not silent.
        import escalation as _esc
        _esc.escalate("MANAGER", "MUTATION_LOCK_STUCK",
                      "could not remove %s; publishing stays blocked until it is gone" % LOCK,
                      who="mutate.py")


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def _write(path, data):
    with open(path, "wb") as f:
        f.write(data)


def _digest(data):
    return hashlib.sha256(data).hexdigest()[:16]


# --------------------------------------------------------------------------- the mutations

def _mutations(tree, text):
    """-> [(lineno, description, old_src, new_src)] for one module.

    SOURCE-LEVEL, NOT AST-ROUNDTRIP. Unparsing an AST and writing it back reformats the whole
    file, so every mutant would differ from the original in thousands of irrelevant ways and a
    survivor's diff would be unreadable. These are surgical single-token edits on the original
    text, which keeps the diff to exactly the thing that changed.
    """
    out = []
    lines = text.splitlines(keepends=True)

    def line_of(node):
        i = node.lineno - 1
        return (i, lines[i]) if 0 <= i < len(lines) else (None, None)

    for node in ast.walk(tree):
        # --- comparison operators: the single richest source of real defects
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            swap = {ast.Lt: ("<", ">="), ast.Gt: (">", "<="), ast.LtE: ("<=", ">"),
                    ast.GtE: (">=", "<"), ast.Eq: ("==", "!="), ast.NotEq: ("!=", "==")}
            got = swap.get(type(node.ops[0]))
            if got:
                i, line = line_of(node)
                if line and got[0] in line:
                    out.append((node.lineno, "%s -> %s" % got, line,
                                line.replace(got[0], got[1], 1)))
        # --- boolean connectives
        elif isinstance(node, ast.BoolOp):
            a, b = ("and", "or") if isinstance(node.op, ast.And) else ("or", "and")
            i, line = line_of(node)
            if line and (" %s " % a) in line:
                out.append((node.lineno, "%s -> %s" % (a, b), line,
                            line.replace(" %s " % a, " %s " % b, 1)))
        # --- `not`, dropped. A guard that forgets its negation is a guard that inverts.
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            i, line = line_of(node)
            if line and "not " in line:
                out.append((node.lineno, "drop `not`", line, line.replace("not ", "", 1)))
        # --- the two constants that decide everything
        elif isinstance(node, ast.Constant) and node.value is True:
            i, line = line_of(node)
            if line and "True" in line:
                out.append((node.lineno, "True -> False", line,
                            line.replace("True", "False", 1)))
        elif isinstance(node, ast.Constant) and node.value is False:
            i, line = line_of(node)
            if line and "False" in line:
                out.append((node.lineno, "False -> True", line,
                            line.replace("False", "True", 1)))

    # Deduplicate: several AST nodes can sit on one line and produce the same edit.
    seen, uniq = set(), []
    for m in out:
        key = (m[0], m[1])
        if key not in seen and m[2] != m[3]:
            seen.add(key)
            uniq.append(m)
    return uniq


# --------------------------------------------------------------------------- running them

def _gate_passes(name, cmd, timeout=1200, env=None, cwd=None):
    try:
        r = subprocess.run(cmd, cwd=(cwd or HERE), capture_output=True, text=True,
                           creationflags=_NO_WIN, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, type(e).__name__
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        return False, "exit %d" % r.returncode
    # A zero exit is not the same as a clean run for these two: both report their failures on
    # stdout and still exit 0 in some paths. Reading the words the report uses is what a person
    # would do, and it is what the maintenance prompt tells a person to do.
    if name == "verify_math" and "0 FAILED" not in out:
        return False, "verify_math reported failures"
    if name == "drill" and "0 BREACHED" not in out:
        return False, "drill reported a breach"
    return True, "clean"


def verify_restore(path):
    """Prove the save/restore cycle is byte-exact BEFORE mutating anything. -> bool.

    A restore that does not restore turns a diagnostic into a corruption, on the three files
    this project can least afford to corrupt. This is the first thing `run()` does and it
    refuses to continue if it fails.
    """
    original = _read(path)
    probe = original + b"\n# mutate.py restore probe\n"
    try:
        _write(path, probe)
        if _read(path) != probe:
            return False
    finally:
        _write(path, original)
    return _read(path) == original


def _junction(link, target):
    """Windows directory junction, so the sandbox shares `data/` instead of copying a gigabyte.

    Junctions need no administrator rights, unlike symlinks. Falls back to a plain copy nowhere:
    if this fails the sandbox is unusable and `sandbox()` says so rather than silently building
    a half-tree whose gates would then fail for reasons that have nothing to do with a mutation.
    """
    if os.name == "nt":
        r = subprocess.run(["cmd", "/c", "mklink", "/J", link, target],
                           capture_output=True, text=True, creationflags=_NO_WIN, timeout=60)
        if not os.path.isdir(link):
            raise RuntimeError("could not junction %s -> %s: %s"
                               % (link, target, (r.stderr or r.stdout or "?").strip()[:120]))
        return
    os.symlink(target, link)


def sandbox():
    """Build a throwaway copy of the tree to mutate. -> path.

    THE ARCHITECTURE THAT SHOULD HAVE BEEN HERE FROM THE START, and the reason is a list of
    things that actually happened on 2026-08-25 within two hours of the in-place version being
    written:

      * a `publish.py --push --loop 1` DAEMON, running since 14:28 with the pre-guard code
        loaded in memory, pushed a mutated `prose_gate.py` and a mutated `escalation.py` to a
        public GitHub repo. The lock added to stop it was invisible to it: **a guard added to
        source does nothing to a process already running that source.**
      * a concurrent `drill.py` read a mutated gate and HALTED the library over code that was
        restored seconds later.
      * two hard kills stranded a live mutation on disk, because `finally` does not run when a
        process is killed.
      * `local_agent.py --patch` is also writing into `src/` on its own schedule, so a mutation
        and a repair could interleave on the same file.

    Every one of those is the same root cause: **the live tree was being corrupted, and fifteen
    other processes read the live tree.** No amount of locking fixes that, because the other
    processes have to agree to look, and the ones already running never will.

    So mutation now happens somewhere else entirely. `src/` is COPIED (it is small); `data/`,
    `prompts/` and `reference/` are junctioned (they are large and read-only in this context);
    `state/` and `output/` are created EMPTY, which is what stops a sandboxed `drill.py` from
    raising a real halt or a sandboxed run from writing real ledgers. The live tree is never
    opened for writing at any point.
    """
    root = tempfile.mkdtemp(prefix="panscriptum_mutate_")
    os.makedirs(os.path.join(root, "src"))
    for f in os.listdir(SRC):
        if f.endswith(".py"):
            shutil.copy2(os.path.join(SRC, f), os.path.join(root, "src", f))
    for shared in ("data", "prompts", "reference"):
        src_dir = os.path.join(HERE, shared)
        if os.path.isdir(src_dir):
            _junction(os.path.join(root, shared), src_dir)
    for fresh in ("state", "output"):
        os.makedirs(os.path.join(root, fresh), exist_ok=True)
    for f in ("config.yaml", "requirements.txt"):
        p_ = os.path.join(HERE, f)
        if os.path.exists(p_):
            shutil.copy2(p_, os.path.join(root, f))
    return root


def baseline(root, gates=GATES):
    """Do the gates pass on UNMUTATED code? -> (bool, [(gate, why)]).

    THE CHECK THAT MAKES EVERY OTHER RESULT MEAN ANYTHING, and its absence produced a run that
    looked perfect and was worthless. `verify_math` was reporting `795 passed, 1 FAILED` --
    an honest red about sweep coverage, nothing to do with any mutation -- so **every mutant
    died at the same gate for the same unrelated reason.** 146 mutants, 146 kills, zero
    survivors: the best possible score, meaning nothing at all.

    A mutant killed by a pre-existing failure is not a mutant killed. If the baseline is not
    clean, the honest output is a refusal, not a number.
    """
    bad = []
    for name, cmd in gates:
        ok, why = _gate_passes(name, cmd, cwd=root)
        if not ok:
            bad.append((name, why))
    return (not bad), bad


def run(target, limit=None, gates=GATES, root=None, keep=False):
    """Mutate one module IN A SANDBOX and report which mutants survived. -> dict."""
    own_sandbox = root is None
    root = root or sandbox()
    path = os.path.join(root, "src", target)
    live = os.path.join(SRC, target)
    live_before = _digest(_read(live))

    try:
        original = _read(path)
        if not verify_restore(path):
            raise RuntimeError("restore is not byte-exact for %s; refusing to mutate it" % target)

        text = original.decode("utf-8")
        try:
            tree = ast.parse(text)
        except SyntaxError as e:
            raise RuntimeError("%s will not parse: %s" % (target, e))

        muts = _mutations(tree, text)
        if limit:
            # Explicitly reported, never silent. Hard Rule 0 forbids a cap that hides a smaller
            # universe; this one is an interactive convenience and it must say so in the result.
            muts = muts[:limit]

        lines = text.splitlines(keepends=True)
        survivors, killed = [], 0
        try:
            for lineno, desc, old_line, new_line in muts:
                mutated = list(lines)
                mutated[lineno - 1] = new_line
                _write(path, "".join(mutated).encode("utf-8"))
                died_at = None
                for gname, cmd in gates:
                    ok, why = _gate_passes(gname, cmd, cwd=root)
                    if not ok:
                        died_at = "%s (%s)" % (gname, why)
                        break
                if died_at:
                    killed += 1
                else:
                    survivors.append({"line": lineno, "mutation": desc,
                                      "was": old_line.strip()[:120],
                                      "became": new_line.strip()[:120]})
        finally:
            _write(path, original)

        # THE LIVE FILE MUST BE BYTE-IDENTICAL TO HOW WE FOUND IT. Not "should be" -- checked,
        # every run, because the whole class of incident this rewrite exists to end began with
        # a corrupted live file that nobody noticed until it was on GitHub.
        live_after = _digest(_read(live))
        return {"target": target, "mutants": len(muts), "killed": killed,
                "survived": len(survivors), "survivors": survivors,
                "capped": bool(limit) and len(muts) == limit,
                "sandbox": root,
                "live_file_untouched": live_after == live_before,
                "restored_exactly": _digest(_read(path)) == _digest(original)}
    finally:
        if own_sandbox and not keep:
            shutil.rmtree(root, ignore_errors=True)


def file_orders(result, found_by="mutate"):
    """A survivor is a hole in the safeties. File it as one. -> ids."""
    import workorders
    ids = []
    for s in result["survivors"]:
        oid = workorders.file_order(
            code="MUTANT_SURVIVED_%s_L%d" % (result["target"].replace(".py", "").upper(),
                                             s["line"]),
            what=("%s:%d was changed to something WRONG (%s) and the entire battery still "
                  "passed. `%s` became `%s`. Either a check is missing here, or the mutation is "
                  "genuinely equivalent -- and which of those it is has to be decided by "
                  "reading it, not assumed."
                  % (result["target"], s["line"], s["mutation"], s["was"], s["became"])),
            handler="RUN", severity="MAJOR",
            where="src/%s:%d" % (result["target"], s["line"]),
            found_by=found_by, evidence=s)
        if oid:
            ids.append(oid)
    return ids


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", choices=TARGETS + ("all",), default="prose_gate.py")
    ap.add_argument("--limit", type=int, help="stop after N mutants (interactive only)")
    ap.add_argument("--list", action="store_true", help="count the mutants, run none of them")
    ap.add_argument("--file-orders", action="store_true")
    ap.add_argument("--keep-sandbox", action="store_true",
                    help="leave the sandbox on disk for inspection")
    a = ap.parse_args()

    # A halt means the library is not in a state anyone should be deliberately breaking.
    halted, _rec = escalation.status()
    if halted:
        print("HALTED — refusing to mutate. Clear the halt first.")
        return 2

    targets = TARGETS if a.target == "all" else (a.target,)

    if a.list:
        for t in targets:
            text = _read(os.path.join(SRC, t)).decode("utf-8")
            n = len(_mutations(ast.parse(text), text))
            print("  %-18s %4d mutant(s)" % (t, n))
        return 0

    root = sandbox()
    print("sandbox: %s" % root)
    try:
        # THE BASELINE, FIRST, AND IT IS A HARD REFUSAL. Without this the first real run was
        # worthless in a way that looked perfect: `verify_math` was reporting one honest
        # pre-existing red about sweep coverage, so all 146 mutants died at that same gate for
        # a reason unrelated to any mutation, and the report would have read
        # "146 killed, 0 survived" -- a flawless score from a test that never tested anything.
        #
        # A mutant killed by a pre-existing failure is not a mutant killed, and a number
        # produced that way is worse than no number, because it is believable.
        ok, bad = baseline(root)
        if not ok:
            print("\nBASELINE IS NOT CLEAN — REFUSING TO MUTATE.")
            for gname, why in bad:
                print("   %-14s %s" % (gname, why))
            print("\nEvery mutant would die at these gates for reasons that have nothing to do")
            print("with the mutation, and the run would report a perfect score. Fix the")
            print("baseline first, or pass --gates to narrow it.")
            return 3
        print("baseline clean: %s" % ", ".join(g for g, _ in GATES))

        total_s = 0
        for t in targets:
            t0 = time.time()
            r = run(t, limit=a.limit, root=root)
            total_s += time.time() - t0
            print("\n%s — %d mutants, %d killed, %d SURVIVED   (%.0fs)"
                  % (t, r["mutants"], r["killed"], r["survived"], time.time() - t0))
            if not r["restored_exactly"]:
                print("  *** THE SANDBOX FILE WAS NOT RESTORED. Later targets are unreliable. ***")
                escalation.escalate("MANAGER", "MUTATE_RESTORE_FAILED",
                                    "mutate.py did not restore %s in the sandbox" % t,
                                    evidence=r, source=t, who="mutate.py")
            if not r["live_file_untouched"]:
                # This must be impossible by construction -- the live path is never opened for
                # writing. Checked anyway, and at OWNER level, because the incident that caused
                # this rewrite was a corrupted live file reaching a public repo.
                print("  *** THE LIVE FILE CHANGED DURING A SANDBOXED RUN. STOP. ***")
                escalation.escalate("OWNER", "MUTATE_TOUCHED_LIVE_TREE",
                                    "src/%s changed during a sandboxed mutation run" % t,
                                    evidence=r, source=t, who="mutate.py")
            if r["capped"]:
                print("  (capped at --limit %d; this is NOT the whole set)" % a.limit)
            for s in r["survivors"]:
                print("  SURVIVED  %s:%-5d %-16s  %s"
                      % (t, s["line"], s["mutation"], s["was"][:70]))
            if a.file_orders and r["survivors"]:
                print("  filed %d work order(s)" % len(file_orders(r)))
        print("\ntotal %.0fs" % total_s)
        return 0
    finally:
        if not a.keep_sandbox:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
