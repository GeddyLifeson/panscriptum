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

HOW IT IS SAFE TO RUN, AND THE VERSION OF THIS PARAGRAPH THAT WAS WRONG. This first said that
every mutation is written to a real file and restored in a `finally`. That was true, and it was
the design, and within two hours it had:

  * halted the library, when a concurrent `drill.py` read a mutated `prose_gate.py`;
  * **pushed deliberately-corrupted source to a public GitHub repo, twice**, because a
    `publish.py --loop` daemon from 14:28 was running the code as it stood before the guard
    against exactly that was written -- a Python process does not re-read its own source;
  * left a live mutation stranded on disk when the run was killed, because `finally` does not
    run when a process is killed;
  * and leaked 154 MB of abandoned working directories doing it.

The root cause was one decision: **the live tree was being corrupted, and fifteen other
processes read the live tree.** No lock fixes that, because a lock only works on processes that
agree to look, and the ones already running never will.

So mutation now happens in a SANDBOX (`sandbox()`): `src/` is copied, `data/` `prompts/`
`reference/` are junctioned, `state/` is copied minus `HALT.json`, and the gates run with their
working directory inside it. **The live tree is never opened for writing**, and every run
asserts the live file's digest is unchanged anyway, because that assertion is cheap and the
thing it is checking for reached GitHub once already. Orphaned sandboxes older than six hours
are reaped at startup. It still refuses to run while a halt is standing.

AND A MUTANT IS JUDGED DIFFERENTIALLY, not against green. See `_gate_result`: the first real
run reported `146 killed, 0 survived` -- a perfect score -- because one honest pre-existing
failure was killing every mutant at the same gate for a reason unrelated to any mutation.
"""
import argparse
import ast
import contextlib
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
import silence  # noqa: E402

_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# The files worth the wall clock. Ordered by how much a silent wrong answer costs.
TARGETS = ("assay.py", "prose_gate.py", "escalation.py")

# The checks a mutant must survive to count as surviving. Cheapest first so a mutant that is
# going to be killed is usually killed in seconds rather than minutes -- mutation testing is
# entirely bounded by how fast a killed mutant can be recognised.
#
# `verify_math` before `drill` deliberately: it is the faster of the two and it is where the
# assay arithmetic actually lives, so an assay mutation dies in its first gate.
# TIERED, because the arithmetic is unforgiving. `drill.py` takes about five minutes; there are
# 146 mutants; running the full battery per mutant is twelve hours before the baseline even
# starts, and a check nobody can afford to run is a check that does not run -- which is exactly
# the defect this module was written to find, so it must not be the shape of the module itself.
#
# FAST gates run on every mutant. The expensive CONFIRM gate runs only on the ones that SURVIVE
# them, which is the small set where five more minutes can still change the answer. A mutant
# killed by `import` in one second and a mutant killed by `drill` in five minutes are the same
# fact; only survivors are worth paying full price for.
FAST_GATES = (
    ("import", [sys.executable, "-c", "import sys; sys.path.insert(0,'src'); import assay,"
                " prose_gate, escalation"]),
    ("verify_math", [sys.executable, "src/verify_math.py"]),
)
CONFIRM_GATES = (
    ("drill", [sys.executable, "src/drill.py"]),
)
GATES = FAST_GATES + CONFIRM_GATES


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

    USES `psutil`, AND THE FALLBACK IS THE REASON THIS COMMENT EXISTS. The first version
    shelled out to `tasklist /FI "PID eq N"` and substring-matched the output, which is wrong
    in two ways a maintained library is not: `tasklist` prints "INFO: No tasks are running
    which match the specified criteria" on a MISS, and that string contains no PID -- fine --
    but the PID being searched for can also appear in an unrelated column of a HIT for a
    different process, so a recycled or coincidental number reads as alive. It also spawns a
    process per check, on a path called once per gate. `psutil.pid_exists` is a syscall.

    ON A CHECKOUT WITHOUT `psutil`, the fallback must still be able to say "dead" -- a Windows
    stdlib fallback that always answers ALIVE means a genuinely orphaned lock (owner process
    hard-killed) can never be marked stale and blocks every push forever, which is worse than
    the "false alive delays a push" this function otherwise trades toward on purpose.
    """
    try:
        import psutil
        return psutil.pid_exists(pid)
    except ImportError:
        # Stdlib fallback, kept because this module must not become unusable on a machine where
        # an optional dependency is missing. On POSIX `kill(pid, 0)` is exact.
        try:
            if os.name == "nt":
                return _pid_alive_windows(pid)
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except Exception:
            return True
    except Exception:
        return True


def _pid_alive_windows(pid):
    """-> True if `pid` is a live Windows process, via ctypes (no psutil, no subprocess).

    OpenProcess failing with ERROR_INVALID_PARAMETER (87) means Windows has no such PID at all
    -- dead. Any other OpenProcess failure (access denied on someone else's process, for
    instance) and any GetExitCodeProcess failure err toward ALIVE, the same direction `_pid_alive`
    already commits to for everything it cannot resolve cleanly.
    """
    import ctypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ctypes.get_last_error() != 87
    try:
        code = ctypes.c_ulong()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return True
        return code.value == STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


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
                   # WHETHER THE LIVE TREE IS AT RISK, which is the only thing a reader of this
                   # lock actually needs to decide anything. Since the sandbox rewrite the live
                   # tree is never opened for writing, so a publisher may proceed -- and it
                   # must be told so, because a guard that blocks correct work for hours every
                   # night is a guard somebody deletes. Readers FAIL CLOSED on a missing or
                   # false value: an older lock, or a future in-place mode, still refuses.
                   "sandboxed": True,
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
        _esc.escalate(_esc.MANAGER, "MUTATION_LOCK_STUCK",
                      "could not remove %s; publishing stays blocked until it is gone" % LOCK,
                      who="mutate.py")


# THE LOCK HAD NO CALLER, AND THAT IS THE WHOLE DEFECT. Everything above was written, commented
# at length, and exercised by a drill net that calls `_lock_acquire` DIRECTLY -- but neither
# `_lock_acquire` nor `_lock_release` had a single call site inside this module. The only other
# readers were `publish.py` and the nets. So `publish.py`'s "REFUSING TO PUSH while a mutation
# run is active" could not fire for any run of this code, at all, and four green drill nets sat
# on top of an interlock wired to nothing. That is this project's own recurring shape -- a check
# that cannot fail looks exactly like a check that passed -- arriving in the mechanism built to
# stop the incident where a deliberately-corrupted `prose_gate.py` was pushed to GitHub.
# (Ops audit 2026-08-25, order d779f541cd0b.)
#
# RE-ENTRANT ON PURPOSE. `main()` holds it for the whole session and `run()` asks again per
# target, so the lock is held whichever entry point a caller uses -- and the inner ask is a
# no-op rather than tripping `_lock_acquire`'s "already active" refusal against its own holder.
_HELD = None


@contextlib.contextmanager
def _hold_lock(targets):
    """Hold the mutation lock across the block, and release it on EVERY exit path.

    Yields True if this frame took the lock, False if an outer frame already holds it. The
    release is in a `finally`, because the failure path is the one that matters: a run that
    dies mid-mutation is exactly when the tree is most likely to be sitting corrupt, and a lock
    left behind blocks every future push until someone deletes a file by hand. `active()`
    already treats a lock whose PID is gone as absent, so a hard kill degrades to stale rather
    than to stuck.
    """
    global _HELD
    if _HELD is not None:
        yield False
        return
    token = "%d-%s" % (os.getpid(), hashlib.sha256(
        ("%s|%s" % (time.time(), tuple(targets))).encode("utf-8")).hexdigest()[:12])
    _lock_acquire(list(targets), token)
    _HELD = token
    # Into the environment so the gate subprocesses spawned inside the sandbox inherit it and
    # can tell "this tree is broken because WE are breaking it" from "this tree is broken and
    # nobody is admitting to it" -- which is the distinction the drill got wrong the first time.
    os.environ[_TOKEN_ENV] = token
    try:
        yield True
    finally:
        _HELD = None
        os.environ.pop(_TOKEN_ENV, None)
        _lock_release()


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

    EACH OCCURRENCE ON A LINE IS ITS OWN MUTANT, not merely each AST node. The first version of
    this used `line.replace(old, new, 1)`, which always rewrites the FIRST occurrence of the
    target text on the line -- so `if a < b and c < d:` (two Compare nodes, one per `<`) asked
    for the edit twice and got the identical answer both times: `a >= b and c < d`, never
    `a < b and c >= d`. The dedup step below then collapsed the two identical-looking entries
    into one, so the second `<` was a mutation NEVER ATTEMPTED, silently absent from both the
    killed and the survived counts -- a coverage hole in the tool whose only job is measuring
    coverage. The same shape hit `and`/`or` chains and repeated `not`/`True`/`False` on one line.

    THE FIX LOCATES EACH OCCURRENCE BY ITS OWN NODE, not by counting through the line. Every
    node in `ast.parse` output (3.8+) carries `end_lineno`/`end_col_offset` alongside
    `lineno`/`col_offset`, so a Compare, UnaryOp or Constant node's own span brackets exactly the
    text that one node produced -- searching for the operator WITHIN that span, instead of from
    the start of the line, finds the right occurrence even when another identical one sits
    earlier on the same line. `BoolOp.values` holds every operand of a same-precedence chain
    (`a and b and c` is ONE node with three values, not two nested ones), so each ADJACENT PAIR
    of values is walked separately and the connective between that specific pair is what gets
    mutated -- which is what turns "one BoolOp node" into "as many mutants as connectives".

    A node whose span crosses lines (a wrapped comparison, a multi-line boolean expression) is
    not something this function's line-oriented editing was ever built to target precisely, so
    those fall back to the previous whole-line `replace(..., 1)` behaviour rather than guessing
    at a column that might land in the wrong place -- unchanged from before this fix, and no
    worse than it was.
    """
    out = []
    lines = text.splitlines(keepends=True)

    def line_of(node):
        i = node.lineno - 1
        return (i, lines[i]) if 0 <= i < len(lines) else (None, None)

    def _spot(node, old):
        """The exact column of `old` inside `node`'s own source span. -> (line, pos) or None.

        None means the span cannot be trusted (crosses lines, too old a Python to carry
        end_col_offset, or `old` simply is not in it) -- callers fall back to whole-line
        matching in that case, exactly as this function did before occurrence-tracking existed.
        """
        end_lineno = getattr(node, "end_lineno", None)
        end_col = getattr(node, "end_col_offset", None)
        if end_lineno != node.lineno or end_col is None:
            return None
        _, line = line_of(node)
        if line is None:
            return None
        pos = line.find(old, node.col_offset, end_col)
        if pos == -1:
            return None
        return line, pos

    for node in ast.walk(tree):
        # --- comparison operators: the single richest source of real defects
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            swap = {ast.Lt: ("<", ">="), ast.Gt: (">", "<="), ast.LtE: ("<=", ">"),
                    ast.GtE: (">=", "<"), ast.Eq: ("==", "!="), ast.NotEq: ("!=", "==")}
            got = swap.get(type(node.ops[0]))
            if got:
                spot = _spot(node, got[0])
                if spot:
                    line, pos = spot
                    new_line = line[:pos] + got[1] + line[pos + len(got[0]):]
                    out.append((node.lineno, "%s -> %s" % got, line, new_line))
                else:
                    _, line = line_of(node)
                    if line and got[0] in line:
                        out.append((node.lineno, "%s -> %s" % got, line,
                                    line.replace(got[0], got[1], 1)))
        # --- boolean connectives: one mutant PER CONNECTIVE, not per BoolOp node, so a chain
        # like `a and b and c` -- one node holding TWO `and`s -- gets each mutated independently.
        elif isinstance(node, ast.BoolOp):
            a, b = ("and", "or") if isinstance(node.op, ast.And) else ("or", "and")
            found_any = False
            for left, right in zip(node.values, node.values[1:]):
                l_end_lineno = getattr(left, "end_lineno", None)
                l_end_col = getattr(left, "end_col_offset", None)
                if l_end_col is None or l_end_lineno != right.lineno:
                    continue
                _, line = line_of(right)
                if line is None:
                    continue
                pattern = " %s " % a
                pos = line.find(pattern, l_end_col, right.col_offset)
                if pos == -1:
                    continue
                found_any = True
                new_line = line[:pos] + (" %s " % b) + line[pos + len(pattern):]
                out.append((right.lineno, "%s -> %s" % (a, b), line, new_line))
            if not found_any:
                _, line = line_of(node)
                if line and (" %s " % a) in line:
                    out.append((node.lineno, "%s -> %s" % (a, b), line,
                                line.replace(" %s " % a, " %s " % b, 1)))
        # --- `not`, dropped. A guard that forgets its negation is a guard that inverts.
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            spot = _spot(node, "not ")
            if spot:
                line, pos = spot
                new_line = line[:pos] + line[pos + len("not "):]
                out.append((node.lineno, "drop `not`", line, new_line))
            else:
                _, line = line_of(node)
                if line and "not " in line:
                    out.append((node.lineno, "drop `not`", line, line.replace("not ", "", 1)))
        # --- the two constants that decide everything
        elif isinstance(node, ast.Constant) and node.value is True:
            spot = _spot(node, "True")
            if spot:
                line, pos = spot
                new_line = line[:pos] + "False" + line[pos + len("True"):]
                out.append((node.lineno, "True -> False", line, new_line))
            else:
                _, line = line_of(node)
                if line and "True" in line:
                    out.append((node.lineno, "True -> False", line,
                                line.replace("True", "False", 1)))
        elif isinstance(node, ast.Constant) and node.value is False:
            spot = _spot(node, "False")
            if spot:
                line, pos = spot
                new_line = line[:pos] + "True" + line[pos + len("False"):]
                out.append((node.lineno, "False -> True", line, new_line))
            else:
                _, line = line_of(node)
                if line and "False" in line:
                    out.append((node.lineno, "False -> True", line,
                                line.replace("False", "True", 1)))

    # Deduplicate: several AST nodes can still legitimately produce the exact same edit (e.g. an
    # equivalent node visited twice). Keyed on the RESULTING TEXT, not the description, because
    # two independent mutations on one line (the first `<` flipped, the second `<` flipped) now
    # produce two DIFFERENT `new_src` strings under the same description and must both survive
    # this step -- keying on description alone is what collapsed them before this fix.
    seen, uniq = set(), []
    for m in out:
        key = (m[0], m[3])
        if key not in seen and m[2] != m[3]:
            seen.add(key)
            uniq.append(m)
    return uniq


# --------------------------------------------------------------------------- running them

def _gate_result(name, cmd, timeout=1200, env=None, cwd=None):
    """Run one gate and return a SIGNATURE of what it said. -> (signature, detail).

    A SIGNATURE, NOT A BOOLEAN, and this is the correction for the failure that made the first
    real mutation run worthless. The original returned pass/fail, and a mutant was "killed" by
    any failure at all -- so when `verify_math` was reporting one honest pre-existing red about
    sweep coverage, all 146 mutants died at that gate for a reason unrelated to any mutation,
    and the report would have read `146 killed, 0 survived`. A flawless score from a test that
    never tested anything.

    Requiring a green tree first was the obvious fix and it is the wrong one: this project has a
    standing honest red almost every day (a new module the sweep has not read yet), so "green or
    refuse" means "never runs", and a check that never runs is the thing this module exists to
    find.

    So a mutant is judged DIFFERENTIALLY -- killed if it makes a gate say something DIFFERENT
    from what that gate says about unmutated code. A pre-existing failure is present in the
    baseline signature too, so it cancels out and stops mattering.
    """
    try:
        r = subprocess.run(cmd, cwd=(cwd or HERE), capture_output=True, text=True,
                           creationflags=_NO_WIN, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return "TIMEOUT", "timeout"
    except Exception as e:
        return "ERROR:" + type(e).__name__, type(e).__name__
    out = (r.stdout or "") + (r.stderr or "")
    # The signature is the exit code plus the COUNT LINE each tool prints -- not the whole
    # output, which carries timings and paths that differ run to run and would make every
    # mutant look different from the baseline.
    marks = []
    for line in out.splitlines():
        t = line.strip()
        if t.startswith("RESULT:") or t.startswith("DRILL:"):
            marks.append(t)
    return "rc=%d|%s" % (r.returncode, " ".join(marks)), (marks[0] if marks else "rc=%d" % r.returncode)


def verify_restore(path):
    """Prove the save/restore cycle is byte-exact on THIS path BEFORE mutating it. -> bool.

    `path` is always a sandbox copy under `sandbox()`'s throwaway root -- that stopped being a
    live file when mutation moved into a sandbox, and this docstring used to still say it
    protects "the three files this project can least afford to corrupt", which is no longer
    what `path` ever is. The LIVE file's protection is separate and stronger: `_run_mutation`
    digests it before and after and reports `live_file_untouched`, escalating at OWNER level if
    it ever moves. What this function actually proves is narrower and still worth proving --
    that `_write`/`_read` round-trip a byte string faithfully on this filesystem for this one
    file before `run()` starts overwriting it with mutants -- because a save/restore that
    silently drops a byte would make every mutant's "restored" claim for the rest of the run
    worthless. A permission error, a locked file or a full disk RAISES out of `_write`/`_read`
    rather than being caught into a `False` here; that is deliberate, not a gap -- `run()`'s own
    try/finally still puts the original bytes back on the way out. Order adba96551729.
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


JOURNAL = os.path.join(HERE, "state", "MUTANTS_SURVIVED.jsonl")


def _journal(target, rec):
    """Append one survivor to disk immediately. Never raises. -> None.

    APPEND-ONLY AND FAILURE-PROOF BY DESIGN. This runs inside the mutation loop, so anything it
    raises would abort a run that is otherwise working -- a recorder that can break the thing it
    records is worse than no recorder. It is also append-only rather than rewrite-the-file,
    because a rewrite has a window in which the previous findings are gone.
    """
    try:
        os.makedirs(os.path.dirname(JOURNAL), exist_ok=True)
        row = dict(rec)
        row["target"] = target
        row["at"] = time.time()
        with open(JOURNAL, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        silence.note("mutate.py:journal")


def survivors_on_record(target=None):
    """-> the survivors written by every run so far, newest last."""
    rows = []
    try:
        with open(JOURNAL, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if target is None or r.get("target") == target:
                    rows.append(r)
    except FileNotFoundError:
        return []
    except Exception:
        silence.note("mutate.py:journal-read")
    return rows


SANDBOX_PREFIX = "panscriptum_mutate_"
ORPHAN_AGE_SECONDS = 6 * 3600


OWNER_FILE = "_owner.json"


    # HOW LONG A LIVE OWNER MAY PROTECT A SANDBOX. Beyond this, age wins regardless of what the
    # owner file says. See `_owner_pid` for why this ceiling has to exist at all.
OWNERSHIP_CEILING_SECONDS = 24 * 3600


def _owner_pid(sandbox_root):
    """The pid that built this sandbox, if the claim is still credible. -> int or None.

    None means "no credible claim on record", which is deliberately different from "the owner is
    dead": the caller treats an unknown owner as reapable-by-age, because a sandbox nobody can
    ever delete is the disk leak this reaper exists to prevent.

    AND THAT IS WHY THIS EXPIRES. The first version of the M46 fix read only `pid` and trusted
    `_pid_alive` -- which the run #36 whole-tree sweep audited on the same day it was written and
    correctly refused: **pids are recycled.** Once the owning run has died, its number is handed
    out again, and the moment any unrelated long-lived process on this machine inherits it the
    sandbox becomes permanently undeletable -- reintroducing the 154 MB leak the reaper exists
    for, by way of the guard added to protect it. A fix whose failure mode is the bug it
    replaced is not a fix.

    So the claim carries the time it was made, and it stops being believed after
    `OWNERSHIP_CEILING_SECONDS`. That is comfortably longer than the longest plausible mutation
    run (hours) and comfortably shorter than forever, so a live owner is protected for as long
    as it could possibly still be working, and a recycled pid can strand a directory for at most
    one day instead of for good.

    A claim with no `started` -- one written by the first version of this code -- is treated as
    expired rather than as eternal, for the same reason: unknown provenance must not buy more
    protection than a known one.
    """
    try:
        with open(os.path.join(sandbox_root, OWNER_FILE), encoding="utf-8") as fh:
            rec = json.load(fh)
        pid, started = rec.get("pid"), rec.get("started")
    except (OSError, ValueError, AttributeError):
        return None
    if not isinstance(pid, int):
        return None
    if not isinstance(started, (int, float)):
        silence.note("mutate.py:owner-claim-undated")
        return None
    if time.time() - started > OWNERSHIP_CEILING_SECONDS:
        silence.note("mutate.py:owner-claim-expired")
        return None
    return pid


def _claim_sandbox(sandbox_root):
    """Record this process as the sandbox's owner. Never raises.

    Written FIRST, before any module is copied in, so that a sandbox is protected during the
    window when it is most fragile -- the copy itself, which is where M46 surfaced.
    """
    try:
        with open(os.path.join(sandbox_root, OWNER_FILE), "w", encoding="utf-8") as fh:
            json.dump({"pid": os.getpid(), "started": time.time(), "argv": sys.argv[:4]}, fh)
    except OSError:
        silence.note("mutate.py:owner-file-unwritable")


def reap_orphans(older_than=ORPHAN_AGE_SECONDS):
    """Delete sandboxes abandoned by runs that were killed. -> [paths removed].

    `run()` removes its sandbox in a `finally`, and a `finally` does not execute when a process
    is killed. Two hard kills on 2026-08-25 left **154 MB across three orphaned sandboxes** in
    TEMP within two hours, and a nightly job that leaks 50 MB per interrupted run fills a disk
    quietly -- which on this machine would take down the crawl, the model and the publisher at
    once, for a reason nobody would look for.

    AGE-GATED, NOT INDISCRIMINATE. A running mutation pass owns a fresh sandbox and deleting it
    would corrupt the pass that is deleting it. Six hours is comfortably longer than the longest
    plausible run and comfortably shorter than "forever".
    """
    removed = []
    root = tempfile.gettempdir()
    cutoff = time.time() - older_than
    try:
        names = os.listdir(root)
    except OSError:
        return removed
    for name in names:
        if not name.startswith(SANDBOX_PREFIX):
            continue
        p = os.path.join(root, name)
        try:
            if not os.path.isdir(p) or os.path.getmtime(p) > cutoff:
                continue
        except OSError:
            continue
        # OWNERSHIP BEATS AGE, and this is the fix for M46 -- the bug that blocked the whole
        # mutation mandate for three runs and was misdiagnosed three times (concurrent edits,
        # then the drill gate, then drill.py generally).
        #
        # The real defect: this reaper matches on a PREFIX and nothing else, so it deletes
        # sandboxes belonging to OTHER LIVE PROCESSES. The age gate was the only thing standing
        # between a reap and somebody else's in-flight run, and an age gate is exactly what a
        # caller lowers when it wants to see reaping actually happen -- so the drill net
        # `abandoned_sandboxes_are_reaped`, in the act of being made able to go red, deleted
        # every concurrent sandbox on the machine. Measured on 2026-08-27: two sandboxes built,
        # `drill.py` run in only ONE, and BOTH died together at six seconds; a bare sandbox with
        # nothing running against it died too; decoy directories under other prefixes survived
        # the same window untouched; and the reap ledger added this shift named the call site,
        # `drill.py:4256 -> M.reap_orphans()`.
        #
        # So a sandbox now records the pid that built it, and a live owner makes it untouchable
        # at ANY age. That turns the age gate into what it should always have been -- a fallback
        # for sandboxes whose owner died without cleaning up -- and it lets a net reap
        # aggressively to prove reaping works without stepping on a run in progress.
        #
        # FAILS SAFE ON DOUBT. An unreadable, malformed or absent owner file leaves the old
        # age-only behaviour in force rather than making the directory permanently undeletable:
        # a sandbox nothing can ever reap is how the 154 MB leak that motivated this reaper
        # happened in the first place.
        # ANY live owner, INCLUDING THIS PROCESS. The first cut of this exempted only OTHER
        # processes, on the reasoning that a run should be able to tidy its own leftovers -- and
        # the red-check caught it immediately: a sandbox owned by the reaping process itself was
        # still deleted at `older_than=0`, which is one `reap_orphans()` call inside a live run
        # away from being M46 again with a shorter stack. `run()` already removes its own root
        # by path in a `finally`; this function is for ORPHANS, and a sandbox whose owner is
        # still breathing is by definition not one.
        owner = _owner_pid(p)
        if owner is not None and _pid_alive(owner):
            silence.note("mutate.py:reap-skipped-live-owner")
            continue
        # The junctions inside must be unlinked, NOT followed. `shutil.rmtree` on Windows does
        # not traverse a directory junction, but this is the one place in the project where
        # getting that wrong would delete `data/` -- 1.1 GB of mined corpus -- so the junctions
        # are removed explicitly first and the tree only then.
        for shared in ("data", "prompts", "reference", os.path.join("output", "index")):
            link = os.path.join(p, shared)
            try:
                if os.path.isdir(link):
                    os.rmdir(link)          # unlinks a junction; fails on a real directory
            except OSError:
                pass
        shutil.rmtree(p, ignore_errors=True)
        # ignore_errors=True means rmtree itself never raises -- the junction case at :506-511
        # (an unlinked-but-undeletable mount, permissions, a file still open in the pass that
        # crashed) leaves `p` standing with no exception to catch. Check what is actually on
        # disk rather than trusting the call to have worked.
        if os.path.isdir(p):
            silence.note("mutate.py:reap-incomplete")
        else:
            removed.append(p)
    if removed:
        _record_reap(removed, older_than)
    return removed


# --------------------------------------------------------------------------- the reap ledger
#
# A DESTRUCTIVE SWEEP THAT LEAVES NO RECORD COST THREE RUNS TO DIAGNOSE. M46 -- a `--target all`
# session dying on a bare FileNotFoundError for `<sandbox>/src/assay.py` about four minutes in,
# after its own baseline gates had passed -- was blamed on concurrent edits by run #34, on the
# `drill` gate by run #35, and on `drill.py` again by run #36's first two probes. All three were
# wrong. A control that built TWO sandboxes and ran drill in only ONE killed BOTH, which cleared
# drill; a bare sandbox with nothing whatsoever running against it died as well; and decoy
# directories under other prefixes survived the same window untouched. So the reaper is code in
# this project matching SANDBOX_PREFIX, and the reason nobody could name it is that reaping was
# the one destructive operation here that reported nothing at all -- `removed` was returned to a
# caller that mostly discarded it, and the only trace was a `note()` for the FAILURE case.
#
# The asymmetry is the bug: an incomplete reap was recorded and a successful one was not, so the
# louder event was invisible and the quieter one was logged. This records what was deleted, on
# whose behalf, and from which stack, to a file OUTSIDE the temp tree being deleted -- the first
# tracer this run wrote put its log inside the sandbox and the reap destroyed its own evidence.
REAP_LEDGER = os.path.join(HERE, "state", "reap_ledger.jsonl")


def _record_reap(removed, older_than):
    """Append one line naming what was reaped and who asked. Never raises.

    Never raises because a reaper that cannot write its ledger must still be a working reaper --
    this is accounting, not a gate. It is deliberately append-only JSONL rather than a rewritten
    document: the writers here are concurrent daemons, and a read-modify-write shared between
    them is the exact defect three other modules were repaired for this shift.
    """
    import traceback
    try:
        stack = [ln.strip() for ln in traceback.format_stack()[:-2]][-6:]
        row = {"at": time.time(), "pid": os.getpid(), "older_than": older_than,
               "argv": sys.argv[:4], "removed": removed, "stack": stack}
        os.makedirs(os.path.dirname(REAP_LEDGER), exist_ok=True)
        with open(REAP_LEDGER, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
    except Exception:
        silence.note("mutate.py:reap-ledger-unwritable")


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

    So mutation now happens somewhere else entirely. `src/` and `state/` are COPIED -- the only
    two subtrees a gate can write to and have the write land in this throwaway tree instead of
    the live one. `data/`, `prompts/`, `reference/` and `output/index` are JUNCTIONED, not
    copied, because copying them costs gigabytes this runs too often to afford; a junction is a
    portal, not a wall, so a write through one of the four lands on the LIVE tree exactly as if
    the sandbox did not exist. **This is not a written guarantee, because a junction cannot back
    one.** It holds today only because the gate commands in `GATES`/`FAST_GATES` happen not to
    write to those four paths -- verified by reading them, not assumed -- and a future gate that
    does write there would corrupt the live tree with nothing here to say so. Order 6d7f88ffb76e.
    """
    reap_orphans()
    root = tempfile.mkdtemp(prefix="panscriptum_mutate_")
    # ACCEPTED RISK, VERIFIED, NOT FIXED (order 404d0ccf9df5). There is a real, narrow window
    # right here: `root` exists and matches SANDBOX_PREFIX before the next line writes its
    # owner file, so a concurrent `reap_orphans(older_than=0)` landing in that exact gap would
    # read `_owner_pid(root)` as None (no owner file yet) and delete it out from under this
    # call. Re-audited rather than assumed: `reap_orphans()`'s own age gate is what closes this
    # in every real run -- the default `ORPHAN_AGE_SECONDS` is six hours, so a directory whose
    # mtime is microseconds old is always skipped by `getmtime(p) > cutoff` -- and an
    # `older_than=0` call only exists in this codebase as a deliberately aggressive drill-net
    # probe proving the reaper can reap at all (see the M46 comments on `reap_orphans` above),
    # never in a nightly or scheduled path. Landing that probe inside this specific gap, on this
    # specific machine's tempdir, is not something a lock is worth adding for: the fix that
    # would close it cleanly -- publishing the directory under SANDBOX_PREFIX only after its
    # owner file already exists inside it -- means restructuring `sandbox()`'s own claim
    # sequence, which is exactly the sandbox/ownership machinery this project does not let an
    # automated pass touch without a person reading the change. Left open on purpose.
    _claim_sandbox(root)
    os.makedirs(os.path.join(root, "src"))
    # THE COPY IS NOT ATOMIC AGAINST A TREE SOMEBODY IS EDITING. `os.listdir` names the modules
    # once and each is copied after that, so a file that is renamed, replaced or briefly removed
    # in between -- which is what a maintenance run repairing `src/` looks like from here -- can
    # be listed and then not copied. On 2026-08-27 a `--target all` session died four minutes in
    # with a bare FileNotFoundError on `<sandbox>/src/assay.py`, AFTER the baseline gates had
    # already run and passed, while several repair agents were editing that very file.
    #
    # The crash was not the fault. The fault was that a sandbox missing the module about to be
    # mutated read as a working sandbox right up until something tried to open the file, so the
    # failure surfaced far from its cause and looked like a bug in the mutation engine. The
    # targets are the one thing this sandbox exists to hold, so they are CHECKED here, at the
    # point where the answer is still cheap and the reason is still legible.
    missed = []
    for f in os.listdir(SRC):
        if not f.endswith(".py"):
            continue
        try:
            shutil.copy2(os.path.join(SRC, f), os.path.join(root, "src", f))
        except OSError:
            # A module that vanished mid-copy is recorded, not raised: only the TARGETS are
            # load-bearing, and a run that can still do its job should not be stopped by an
            # unrelated file being rewritten a directory away.
            silence.note("mutate.py:sandbox-copy:" + f)
            missed.append(f)
    absent = [t for t in TARGETS if not os.path.isfile(os.path.join(root, "src", t))]
    if absent:
        shutil.rmtree(root, ignore_errors=True)
        raise RuntimeError(
            "the sandbox is missing %s -- the live tree was being written while it was copied "
            "(%d module(s) could not be read). Nothing was mutated. Re-run when src/ is not "
            "being edited." % (", ".join(absent), len(missed) or 1))
    for shared in ("data", "prompts", "reference"):
        src_dir = os.path.join(HERE, shared)
        if os.path.isdir(src_dir):
            _junction(os.path.join(root, shared), src_dir)
    # STATE IS COPIED, NOT CREATED EMPTY, and the first attempt got this wrong in a way that
    # was quietly fatal: an empty `state/` made a sandboxed `drill.py` fail on missing files, so
    # the BASELINE was dirty for purely structural reasons and every mutant would have died at
    # that gate -- the exact worthless-perfect-score failure the baseline check exists to catch,
    # reintroduced by the fix for it. The gates need the state they read.
    #
    # JSON only, and no logs. `state/` is 109 MB, almost all of it log files no check reads,
    # and copying those per run would cost more than the mutation testing itself.
    os.makedirs(os.path.join(root, "state"), exist_ok=True)
    for f in os.listdir(os.path.join(HERE, "state")):
        if f.endswith(".json"):
            try:
                shutil.copy2(os.path.join(HERE, "state", f), os.path.join(root, "state", f))
            except OSError:
                pass
    # HALT AND LOCK DO NOT TRAVEL. A halt copied into the sandbox would make every gate refuse
    # on purpose, and a copied mutation lock would make the sandbox refuse to mutate. Both are
    # facts about the LIVE library, not about this throwaway copy of it.
    for gone in ("HALT.json", "MUTATION_ACTIVE.json"):
        try:
            os.remove(os.path.join(root, "state", gone))
        except OSError:
            pass
    # output/index carries the manifest several checks read. Junctioned rather than copied: it
    # is 85 MB and nothing in the gate path writes to it.
    os.makedirs(os.path.join(root, "output"), exist_ok=True)
    idx = os.path.join(HERE, "output", "index")
    if os.path.isdir(idx):
        _junction(os.path.join(root, "output", "index"), idx)
    for f in ("config.yaml", "requirements.txt"):
        p_ = os.path.join(HERE, f)
        if os.path.exists(p_):
            shutil.copy2(p_, os.path.join(root, f))
    return root


def baseline(root, gates=GATES):
    """What does each gate say about UNMUTATED code? -> {gate: signature}.

    This is the reference every mutant is compared against. It does NOT require the tree to be
    green -- see `_gate_result` for why demanding green would mean never running at all. It only
    requires the gates to be REPRODUCIBLE: a gate whose signature changes between two clean runs
    is a gate that cannot judge anything, and `flaky_gates()` finds those before they produce
    imaginary survivors.
    """
    out = {}
    for name, cmd in gates:
        out[name] = _gate_result(name, cmd, cwd=root)[0]
    return out


def unusable_gates(base):
    """-> [(gate, signature)] for gates that could not complete on CLEAN code.

    A GATE THAT TIMES OUT ON UNMUTATED CODE CANNOT JUDGE ANYTHING, and letting it try produces
    confident nonsense rather than an error. Measured 2026-08-26: `verify_math` reaches the
    NETWORK -- section 19aa makes a live API call to fandom and Wikipedia -- so in a sandbox
    under load it stalled past five minutes. The differential comparison then read
    `TIMEOUT == TIMEOUT` and reported every mutant as SURVIVING, which is the same worthless
    answer as the pre-baseline version's "everything killed", just pointing the other way.
    Both directions of that failure look exactly like a finished run.
    """
    return [(n, s_) for n, s_ in base.items()
            if s_ == "TIMEOUT" or s_.startswith("ERROR:")]


def flaky_gates(root, base, gates=GATES):
    """Run the gates a second time on clean code and report any that disagree with themselves.

    A FLAKY GATE INVENTS RESULTS IN BOTH DIRECTIONS. If it differs from its own baseline at
    random, every mutant it judges is a coin flip: some survive that should have died, some die
    that should have survived, and the report looks exactly as confident either way. Cheap to
    check once, and impossible to reason about afterwards if you do not.
    """
    bad = []
    for name, cmd in gates:
        sig = _gate_result(name, cmd, cwd=root)[0]
        if sig != base.get(name):
            bad.append((name, base.get(name), sig))
    return bad


def run(target, limit=None, gates=FAST_GATES, root=None, keep=False, base=None,
        confirm=CONFIRM_GATES):
    """Mutate one module IN A SANDBOX and report which mutants survived. -> dict.

    THE LOCK IS TAKEN HERE, around the whole of it, and here rather than only in `main()`
    because `run()` is the public entry point: anything that imports this module and calls it
    directly -- the drill, a work-order reproduction, a future scheduler -- must announce itself
    to `publish.py` just as the CLI does. Held before the first mutant is written and released
    on the failure path too. The body is `_run_mutation`; the split exists so the lock cannot be
    skipped by an edit to the body.
    """
    with _hold_lock([target]):
        return _run_mutation(target, limit=limit, gates=gates, root=root, keep=keep,
                             base=base, confirm=confirm)


def _run_mutation(target, limit=None, gates=FAST_GATES, root=None, keep=False, base=None,
                  confirm=CONFIRM_GATES):
    """The body of `run`, with the mutation lock already held. Do not call this directly."""
    base = {} if base is None else base
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
            raise RuntimeError("%s will not parse: %s" % (target, e)) from e

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
                    sig, why = _gate_result(gname, cmd, cwd=root)
                    # DIFFERENT from clean, not merely failing. A gate that was already red on
                    # unmutated code stays red here and correctly kills nothing.
                    if sig != base.get(gname):
                        died_at = "%s (%s)" % (gname, why)
                        break
                # A SURVIVOR OF THE FAST GATES IS ONLY A CANDIDATE. The expensive gate runs
                # here and nowhere else, so its five minutes is spent exactly on the mutants
                # where it can still change the answer -- which is what makes running this over
                # 146 mutants affordable at all.
                if not died_at:
                    for gname, cmd in confirm:
                        sig, why = _gate_result(gname, cmd, cwd=root)
                        if sig != base.get(gname):
                            died_at = "%s (%s)" % (gname, why)
                            break
                if died_at:
                    killed += 1
                else:
                    # APPENDED TO DISK THE MOMENT IT IS FOUND, not collected and reported at
                    # the end. A 3.7-hour run over `assay.py` found **20 survivors out of 58
                    # mutants** and then lost every one of them: the summary line printed, and
                    # the very next statement -- an `escalate()` call with a string level --
                    # raised `ValueError` before the details were written anywhere. Hours of
                    # GPU-adjacent wall clock, and the only artefact was a count.
                    #
                    # A long run must not hold its findings in memory until it is finished.
                    # Anything that can crash, be killed, lose power or hit a full disk between
                    # the finding and the report will take the finding with it, and the longer
                    # the run the likelier that is.
                    _journal(target, {"line": lineno, "mutation": desc,
                                      "was": old_line.strip()[:120],
                                      "became": new_line.strip()[:120],
                                      "confirmed": bool(confirm)})
                    survivors.append({"line": lineno, "mutation": desc,
                                      "was": old_line.strip()[:120],
                                      "became": new_line.strip()[:120],
                                      "confirmed": bool(confirm)})
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
    ap.add_argument("--check-flaky", action="store_true",
                    help="run the gates twice on clean code first; doubles startup cost")
    ap.add_argument("--no-confirm", action="store_true",
                    help="skip the slow confirm gate; SURVIVORS BECOME UNCONFIRMED")
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

    # SESSION-LEVEL HOLD, above the per-target one. `--target all` is ONE continuous window in
    # which this machine is deliberately breaking code, and a publisher that slipped through the
    # gap between two targets would be pushing during a mutation run by any honest reading of
    # the phrase. Held from before the sandbox is built until after it is torn down.
    with _hold_lock(targets):
        return _session(a, targets)


def _session(a, targets):
    """One mutation session, with the lock held. -> exit code."""
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
        gates = FAST_GATES
        confirm = () if a.no_confirm else CONFIRM_GATES
        base = baseline(root, gates=gates + confirm)
        print("baseline signatures:")
        for gname, sig in base.items():
            print("   %-14s %s" % (gname, sig[:90]))
        # OPT-IN, because it runs every gate a second time and the slow one is five minutes.
        # Worth paying before trusting a survivor list; not worth paying on every smoke run.
        dead = unusable_gates(base)
        if dead:
            print("\nGATES THAT COULD NOT COMPLETE ON CLEAN CODE — REFUSING TO MUTATE.")
            for gname, sig_ in dead:
                print("   %-14s %s" % (gname, sig_))
            print("\nA gate that cannot finish on unmutated code cannot judge a mutant. Every")
            print("comparison against it would read TIMEOUT == TIMEOUT and report the whole")
            print("set as surviving, which looks exactly like a finished run.")
            return 4

        # gates=gates + confirm, matching the call that built `base` two lines up. The default
        # (gates=GATES) always includes CONFIRM_GATES, so under --no-confirm this would score a
        # gate (e.g. drill) that `base` never ran against base.get(name) == None -- an eternal
        # mismatch that pays drill's five minutes and then refuses to mutate regardless of the
        # code, no matter how many times it is run.
        flaky = flaky_gates(root, base, gates=gates + confirm) if a.check_flaky else []
        if not a.check_flaky:
            print("   (flakiness not checked — pass --check-flaky before trusting survivors)")
        if flaky:
            print("\nFLAKY GATES — REFUSING TO MUTATE.")
            for gname, a_, b_ in flaky:
                print("   %-14s run1=%s   run2=%s" % (gname, str(a_)[:40], str(b_)[:40]))
            print("\nA gate that disagrees with itself on unmutated code judges every mutant")
            print("by coin flip, and the report looks equally confident either way.")
            return 3
        print("all gates reproducible; mutants judged by DIFFERENCE from the above")

        # WHAT PREVIOUS RUNS ALREADY FOUND. Printed before this run starts, because a survivor
        # is a standing finding until somebody rules on it -- and a run that reports only its
        # own 20 while 20 identical ones sit unread on disk is inviting the same work twice.
        _prior = survivors_on_record()
        if _prior:
            _by = {}
            for _r in _prior:
                _by[_r.get("target")] = _by.get(_r.get("target"), 0) + 1
            print("on record from earlier runs: "
                  + ", ".join("%s x%d" % (k, v) for k, v in sorted(_by.items())))

        total_s = 0
        for t in targets:
            t0 = time.time()
            r = run(t, limit=a.limit, root=root, base=base, gates=gates, confirm=confirm)
            total_s += time.time() - t0
            print("\n%s — %d mutants, %d killed, %d SURVIVED   (%.0fs)"
                  % (t, r["mutants"], r["killed"], r["survived"], time.time() - t0))
            if not r["restored_exactly"]:
                print("  *** THE SANDBOX FILE WAS NOT RESTORED. Later targets are unreliable. ***")
                escalation.escalate(escalation.MANAGER, "MUTATE_RESTORE_FAILED",
                                    "mutate.py did not restore %s in the sandbox" % t,
                                    evidence=r, source=t, who="mutate.py")
            if not r["live_file_untouched"]:
                # This must be impossible by construction -- the live path is never opened for
                # writing. Checked anyway, and at OWNER level, because the incident that caused
                # this rewrite was a corrupted live file reaching a public repo.
                print("  *** THE LIVE FILE CHANGED DURING A SANDBOXED RUN. STOP. ***")
                escalation.escalate(escalation.OWNER, "MUTATE_TOUCHED_LIVE_TREE",
                                    "src/%s changed during a sandboxed mutation run" % t,
                                    evidence=r, source=t, who="mutate.py")
            if r["capped"]:
                print("  (capped at --limit %d; this is NOT the whole set)" % a.limit)
            for s in r["survivors"]:
                tag = "SURVIVED " if confirm else "UNCONFIRMED"
                print("  %s %s:%-5d %-16s  %s"
                      % (tag, t, s["line"], s["mutation"], s["was"][:70]))
            if r["survivors"] and not confirm:
                print("  --no-confirm was used: these passed the FAST gates only. They are"
                      " candidates, not findings, and must not be filed as findings.")
            if a.file_orders and r["survivors"] and confirm:
                print("  filed %d work order(s)" % len(file_orders(r)))
        print("\ntotal %.0fs" % total_s)
        return 0
    finally:
        if not a.keep_sandbox:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
