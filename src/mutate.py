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
    # `active()` FIRST, BUT IT DOES NOT DECIDE ANYTHING. It is asked here for two things only:
    # the friendly, informative refusal below (which needs the other holder's record), and
    # clearing a record whose process is gone so the exclusive create can win. The decision is
    # made by O_EXCL. This used to be a check-then-create -- active() then open(LOCK, 'w') --
    # and two runs starting together could both observe no lock and both write one, the second
    # silently overwriting the first's pid, started and token, which is precisely the "two
    # mutants on disk and no way to attribute either" the lock exists to prevent.
    # Order a693fe8a33cc.
    held, rec = active()
    if held:
        raise RuntimeError("a mutation run is already active (%s); refusing to start a second"
                           % json.dumps(rec)[:160])
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    if rec is not None:
        # Not held, but a file is on disk -- a stale record from a dead holder. Clear it, or
        # the O_EXCL create below would refuse forever and a dead run would block every push.
        try:
            os.remove(LOCK)
        except FileNotFoundError:
            pass
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        # Somebody won the race between active() and here. That is the case this call is for.
        raise RuntimeError("a mutation run claimed %s first; refusing to start a second" % LOCK)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
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


def _lock_release(token=None):
    """Drop the lock, but only if it is still OURS.

    THE TOKEN WAS WRITTEN AND NEVER READ. `_lock_acquire` stamps a per-run token into the
    record at :222 specifically so ownership can be established, and the release was a bare
    `os.remove(LOCK)`: in any overlap the session that finished first deleted the lock a
    still-running session believed it held, and `publish.py` -- whose refusal to push is the
    entire reason this lock exists after a deliberately-corrupted `prose_gate.py` reached
    GitHub twice -- was unblocked mid-run. Order a693fe8a33cc.

    `token=None` means "no ownership claim", and then the file is removed unconditionally: that
    is the caller who acquired without recording a token (the drill nets do exactly this), and
    refusing there would leave a lock nobody can ever drop. An UNREADABLE record is also
    removed, for the same reason in stronger form -- with the O_EXCL acquire above, nothing
    else can have written over our claim, so an unreadable one can only be our own, and a lock
    no reader can parse is treated as HELD by `active()` and would block every future push.
    """
    if token is not None:
        try:
            with open(LOCK, encoding="utf-8") as f:
                rec = json.load(f)
        except FileNotFoundError:
            return
        except Exception:
            silence.note("mutate.py:lock-release-unreadable")
            rec = None
        if isinstance(rec, dict) and rec.get("token") != token:
            # Somebody else's claim. Deleting it is the failure this check exists to stop.
            silence.note("mutate.py:lock-release-not-ours")
            return
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
        # The token is handed to the release explicitly rather than read back off `_HELD`,
        # because `_HELD` has to be cleared before the release (a re-entrant caller must not see
        # a claim this frame is in the middle of dropping) and the release now needs it to prove
        # the lock on disk is the one this frame took. Order a693fe8a33cc.
        _HELD = None
        os.environ.pop(_TOKEN_ENV, None)
        _lock_release(token)


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def _write(path, data):
    with open(path, "wb") as f:
        f.write(data)


def _digest(data):
    return hashlib.sha256(data).hexdigest()[:16]


# --------------------------------------------------------------------------- the mutations

def _mutations(tree, text, skipped=None):
    """-> [(lineno, description, old_src, new_src)] for one module.

    `skipped`, if a list is passed, receives `(lineno, kind, why)` for every mutation SITE this
    function found in the parse tree and could not turn into a mutant. It is not decoration.
    Until 2026-08-29 this function mutated only six of the ten `ast.cmpop` types and only when
    `len(node.ops) == 1`, so `in`, `not in`, `is`, `is not` and every operator inside a chained
    comparison produced NO MUTANT AT ALL -- 55 of the 93 comparison-operator sites across the
    three targets, 59% of them, and nothing in `--list`, in the run summary or in the journal
    said so. A tool whose only job is measuring coverage was reporting 188 attempted as though
    it were the whole attemptable set. What cannot be attempted must be COUNTED and NAMED, or
    the number this module exists to produce is a smaller universe wearing the same shape.

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

    AN OPERATOR IS NOW LOCATED IN THE GAP BETWEEN ITS TWO OPERANDS (`_between`), not anywhere
    inside the node's own span. The span of a `Compare` includes both operands, so searching it
    finds the operator text sitting in an OPERAND first -- `if (a == b) == c` mutated the inner
    `==` twice and the outer one never. The gap between one operand's `end_col_offset` and the
    next one's `col_offset` can contain nothing but whitespace, brackets and the operator
    itself, so a match there is the right occurrence by construction. It is also what makes a
    CHAINED comparison mutable at all: `a < b < c` is one node with two ops, and each op has its
    own gap.

    A pair whose operands sit on different lines falls back PER PAIR, not per node. The old
    whole-line `replace(..., 1)` fallback ran only `if not found_any`, so in a chain where one
    connective wrapped and another did not, the wrapped one was never attempted at all -- three
    connectives across the three targets, absent from both the killed and the survived totals.
    The wrapped operator is now looked for on the right operand's line before it, then on the
    left operand's line after it (comment text on that line cut off first, since a `#` following
    an operand can only start a comment). What still cannot be found is recorded in `skipped`
    rather than guessed at.

    AND EVERY MATCH IS TOKEN-BOUNDED (`_token_pos`). The word operators make that mandatory
    rather than tidy: `in` sits inside `print`, `index` and `min`, so a whole-line
    `replace("in", "not in", 1)` on `print(a in b)` yields source that will not parse. A mutant
    that cannot parse dies at the first gate for a reason that has nothing to do with the guard
    it was meant to break -- a FALSE KILL, which is the direction that hides holes.
    """
    out = []
    lines = text.splitlines(keepends=True)

    def _skip(lineno, kind, why):
        """Record a site that exists in the tree and produced no mutant. See `skipped` above."""
        if skipped is not None:
            skipped.append((lineno, kind, why))

    def line_of(node):
        i = node.lineno - 1
        return (i, lines[i]) if 0 <= i < len(lines) else (None, None)

    def _col(line, col):
        """An AST column is a UTF-8 BYTE offset; slicing a `str` needs a CHARACTER offset. -> int.

        FOUND 2026-08-29 while counting skipped sites, and it had been silently wrong since
        occurrence-tracking was written. `prose_gate.py:201` is
        `re.split(r"(?m)^◈\\s", text or "")`: the marker is three bytes and one character, so
        every column the parser reports for that line is two too far right, the gap search for
        `or` looked at `xt o`, found nothing, and the connective was NEVER ATTEMPTED. This
        project's source is full of non-ASCII in code -- the entry marker, the assay sigil, the
        thread glyph -- so this is not a corner case here, and the direction it fails in is the
        bad one: a site quietly absent from both the killed and the survived counts.

        The pure-ASCII line, which is almost all of them, is answered without allocating.
        """
        if col <= 0:
            return 0
        raw = line.encode("utf-8")
        if len(raw) == len(line):
            return col
        return len(raw[:col].decode("utf-8", "ignore"))

    # PER-(LINE, TOKEN) CURSOR FOR THE WHOLE-LINE FALLBACK (order bed9a7e93c29). `_spot` handles
    # the common case exactly, by column; this dict is only consulted when `_spot` gives up
    # because a node's span crosses lines (or an old Python lacks `end_col_offset`), and the
    # code falls back to finding the bare token text on the line the node STARTS on. The naive
    # form of that fallback was `line.replace(old, new, 1)`, which always rewrites the token at
    # its FIRST position on the line -- so two same-token nodes (`not`/`True`/`False`) whose
    # spans both cross lines and which both start on the same line produced the IDENTICAL
    # new_src, and the dedup step below (keyed on (lineno, new_src)) silently collapsed them into
    # one mutant. Because the fallback SUCCEEDED, `_skip` was never called either, so the lost
    # site was invisible in both the mutant list and `not_attempted` -- the one path in this
    # function where that could happen in both directions at once. Tracking where the last
    # fallback match on this exact (line, token) ended, and searching forward from there, gives
    # each such node its own occurrence; when none remains, the site is `_skip`ped rather than
    # silently reusing an already-claimed spot.
    _fallback_next = {}

    def _fallback_spot(idx, token):
        """Find `token` in `lines[idx]`, after any prior fallback match on this (line, token).

        -> (line, pos) or None. See `_fallback_next` above for why "after any prior match" and
        not "at the first occurrence" -- the latter is exactly the bug this exists to close.
        """
        if idx is None:
            return None
        line = lines[idx]
        start = _fallback_next.get((idx, token), 0)
        pos = line.find(token, start)
        if pos == -1:
            return None
        _fallback_next[(idx, token)] = pos + len(token)
        return line, pos

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
        pos = line.find(old, _col(line, node.col_offset), _col(line, end_col))
        if pos == -1:
            return None
        return line, pos

    def _token_pos(line, tok, start, end):
        """Position of `tok` inside `line[start:end]` as a STANDALONE token. -> int or -1.

        The boundary test is what makes the word operators safe to mutate at all: `in` is a
        substring of `print`, `index`, `min` and `finished`, and an unbounded match produces
        source that will not parse. See the docstring on false kills.
        """
        i = line.find(tok, start, end)
        while i != -1:
            before = line[i - 1] if i else " "
            after = line[i + len(tok)] if i + len(tok) < len(line) else " "
            if not (before.isalnum() or before == "_") and not (after.isalnum() or after == "_"):
                return i
            i = line.find(tok, i + 1, end)
        return -1

    def _find_op(line, tok, start, end):
        """-> (start, end) of the operator `tok` within `line[start:end]`, or None.

        `tok` may be TWO words (`not in`, `is not`), and each word is located separately with
        only whitespace permitted between them, so `x is  not None` -- legal Python, two spaces
        -- is found rather than skipped by an exact-string search that assumes one.
        """
        parts = tok.split(" ")
        pos = _token_pos(line, parts[0], start, end)
        if pos == -1:
            return None
        cur = pos + len(parts[0])
        for p in parts[1:]:
            nxt = _token_pos(line, p, cur, end)
            if nxt == -1 or line[cur:nxt].strip():
                return None
            cur = nxt + len(p)
        return pos, cur

    def _between(left, right, tok):
        """Locate `tok` in the gap between two operands. -> (lineno, line, start, end) or None.

        THE GAP, not the enclosing node's span: see the docstring. Same line is the common case
        and is exact. Different lines is the per-PAIR fallback -- the right operand's line first
        (a wrapped expression almost always carries the connective at the head of the
        continuation), then the left operand's line, with any trailing comment cut off, because
        a `#` sitting after an operand can only begin a comment and `and` inside a comment is
        not an operator.
        """
        l_end_lineno = getattr(left, "end_lineno", None)
        l_end_col = getattr(left, "end_col_offset", None)
        if l_end_col is None or l_end_lineno is None:
            return None
        if l_end_lineno == right.lineno:
            _, line = line_of(right)
            if line is None:
                return None
            got = _find_op(line, tok, _col(line, l_end_col), _col(line, right.col_offset))
            return (right.lineno, line, got[0], got[1]) if got else None
        _, r_line = line_of(right)
        if r_line is not None:
            got = _find_op(r_line, tok, 0, _col(r_line, right.col_offset))
            if got:
                return right.lineno, r_line, got[0], got[1]
        i = l_end_lineno - 1
        if 0 <= i < len(lines):
            l_line = lines[i]
            start = _col(l_line, l_end_col)
            cut = l_line.find("#", start)
            got = _find_op(l_line, tok, start, cut if cut != -1 else len(l_line))
            if got:
                return l_end_lineno, l_line, got[0], got[1]
        return None

    # ALL TEN `ast.cmpop` TYPES, and the four added on 2026-08-29 are the ones that matter most.
    # `is None` -> `is not None` and `not in` -> `in` are guard INVERSIONS -- precisely the
    # defect class this branch's own comment calls the single richest source of real defects --
    # and 49 of them stood unmutated across the three targets, 13 of the 20 operator sites in
    # `escalation.py`, the chain of command and the halt.
    CMP_SWAP = {ast.Lt: ("<", ">="), ast.Gt: (">", "<="), ast.LtE: ("<=", ">"),
                ast.GtE: (">=", "<"), ast.Eq: ("==", "!="), ast.NotEq: ("!=", "=="),
                ast.In: ("in", "not in"), ast.NotIn: ("not in", "in"),
                ast.Is: ("is", "is not"), ast.IsNot: ("is not", "is")}

    for node in ast.walk(tree):
        # --- comparison operators: the single richest source of real defects
        if isinstance(node, ast.Compare):
            # EVERY op, not just `node.ops[0]`, and no `len(node.ops) == 1` guard. A chained
            # comparison holds several operators in ONE node; the old code declined the whole
            # node rather than the operators it could not place.
            for i, op in enumerate(node.ops):
                got = CMP_SWAP.get(type(op))
                if got is None:
                    # Unreachable today -- CMP_SWAP covers all ten cmpop types. Kept so that a
                    # cmpop added by a future Python is REPORTED rather than silently dropped,
                    # which is the whole failure this order was filed for.
                    _skip(node.lineno, "compare", "no swap for %s" % type(op).__name__)
                    continue
                left = node.left if i == 0 else node.comparators[i - 1]
                where = _between(left, node.comparators[i], got[0])
                if where:
                    lineno, line, s_, e_ = where
                    out.append((lineno, "%s -> %s" % got, line, line[:s_] + got[1] + line[e_:]))
                else:
                    _skip(node.comparators[i].lineno, "compare",
                          "`%s` not locatable between its operands" % got[0])
        # --- boolean connectives: one mutant PER CONNECTIVE, not per BoolOp node, so a chain
        # like `a and b and c` -- one node holding TWO `and`s -- gets each mutated independently.
        elif isinstance(node, ast.BoolOp):
            a, b = ("and", "or") if isinstance(node.op, ast.And) else ("or", "and")
            for left, right in zip(node.values, node.values[1:]):
                where = _between(left, right, a)
                if where:
                    lineno, line, s_, e_ = where
                    out.append((lineno, "%s -> %s" % (a, b), line, line[:s_] + b + line[e_:]))
                else:
                    _skip(right.lineno, "boolop", "`%s` not locatable between its operands" % a)
        # --- `not`, dropped. A guard that forgets its negation is a guard that inverts.
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            spot = _spot(node, "not ")
            if spot:
                line, pos = spot
                new_line = line[:pos] + line[pos + len("not "):]
                out.append((node.lineno, "drop `not`", line, new_line))
            else:
                idx, _line = line_of(node)
                spot2 = _fallback_spot(idx, "not ")
                if spot2:
                    line, pos = spot2
                    out.append((node.lineno, "drop `not`", line,
                               line[:pos] + line[pos + len("not "):]))
                else:
                    _skip(node.lineno, "not", "`not ` not locatable on its line")
        # --- the two constants that decide everything
        elif isinstance(node, ast.Constant) and node.value is True:
            spot = _spot(node, "True")
            if spot:
                line, pos = spot
                new_line = line[:pos] + "False" + line[pos + len("True"):]
                out.append((node.lineno, "True -> False", line, new_line))
            else:
                idx, _line = line_of(node)
                spot2 = _fallback_spot(idx, "True")
                if spot2:
                    line, pos = spot2
                    out.append((node.lineno, "True -> False", line,
                               line[:pos] + "False" + line[pos + len("True"):]))
                else:
                    _skip(node.lineno, "const", "`True` not locatable on its line")
        elif isinstance(node, ast.Constant) and node.value is False:
            spot = _spot(node, "False")
            if spot:
                line, pos = spot
                new_line = line[:pos] + "True" + line[pos + len("False"):]
                out.append((node.lineno, "False -> True", line, new_line))
            else:
                idx, _line = line_of(node)
                spot2 = _fallback_spot(idx, "False")
                if spot2:
                    line, pos = spot2
                    out.append((node.lineno, "False -> True", line,
                               line[:pos] + "True" + line[pos + len("False"):]))
                else:
                    _skip(node.lineno, "const", "`False` not locatable on its line")

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

def _row_ids(out):
    """-> [str] the individual failing-row identities inside one gate's raw output.

    Order 2461a04d8849: `baseline()` kept only the gate's SIGNATURE (the `RESULT:`/`DRILL:`
    count line), never WHICH rows were red, so a refusal like
        verify_math    rc=1|RESULT: 1055 passed, 5 FAILED
    was the whole of what a run said. Learning which five rows were red took building a sandbox
    by hand and diffing against the live tree -- and it turned out all five were sandbox
    omissions (a missing state/sweep_shards/ and six dashboard logs), not library defects. Those
    five had been red, and therefore DISABLED AS DETECTORS, in every mutation run this project
    has ever made, and nothing said so.

    Both gates already print the row identity on its own line, so no gate-specific parser is
    needed -- only a prefix match on the stripped line: verify_math with
    `  FAILED <label>: got ..., want ... <note>` (verify_math.py:7990) and drill with
    `  BREACHED  <net name>` (drill.py:9604). An unrecognised gate, or a clean run, yields [].
    """
    rows = []
    for line in out.splitlines():
        t = line.strip()
        if t.startswith("FAILED ") or t.startswith("BREACHED "):
            rows.append(t)
    return rows


def _gate_result(name, cmd, timeout=1200, env=None, cwd=None, rows_out=None):
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

    `name` IS USED, AND IT WAS NOT. It was threaded through all three call sites and discarded,
    while the function returned a bare 'TIMEOUT'/'timeout' with no idea which gate produced it
    and every caller re-attached the name by hand. It is now carried in both halves of the
    return, so `could_not_judge` output and the indeterminate journal rows name the gate on
    their own. The name is a CONSTANT per gate and the comparison is always baseline-vs-mutant
    for the SAME gate, so adding it cannot change any differential verdict. Order 7bd7f47b012d.

    `rows_out`, IF GIVEN, IS FILLED AS A SIDE EFFECT: `rows_out[name] = [row id, ...]` (order
    2461a04d8849), the individual `FAILED <label>` / `BREACHED <net>` lines from this gate's raw
    output -- see `_row_ids`. A side channel rather than a wider return tuple on purpose: this
    function is called from three places and two of them (`flaky_gates`, the per-mutant judging
    loop in `_run_mutation`) unpack a fixed 2-tuple; changing the arity would break both. Left
    None, the default, this costs nothing extra and behaves exactly as before.
    """
    try:
        r = subprocess.run(cmd, cwd=(cwd or HERE), capture_output=True, text=True,
                           creationflags=_NO_WIN, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        # The `|name` suffix rides behind the existing prefixes on purpose: `could_not_judge`
        # matches on the PREFIX, so a bare 'TIMEOUT' or 'ERROR:OSError' from an older record
        # (or from a drill net that hands one in directly) is still recognised.
        if rows_out is not None:
            rows_out[name] = []
        return "TIMEOUT|%s" % name, "%s timed out after %ds" % (name, timeout)
    except Exception as e:
        if rows_out is not None:
            rows_out[name] = []
        return ("ERROR:%s|%s" % (type(e).__name__, name),
                "%s raised %s" % (name, type(e).__name__))
    out = (r.stdout or "") + (r.stderr or "")
    # The signature is the exit code plus the COUNT LINE each tool prints -- not the whole
    # output, which carries timings and paths that differ run to run and would make every
    # mutant look different from the baseline.
    marks = []
    for line in out.splitlines():
        t = line.strip()
        if t.startswith("RESULT:") or t.startswith("DRILL:"):
            marks.append(t)
    if rows_out is not None:
        rows_out[name] = _row_ids(out)
    return ("rc=%d|%s" % (r.returncode, " ".join(marks)),
            "%s %s" % (name, marks[0] if marks else "rc=%d" % r.returncode))


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

# WAS THE TREE BEING EDITED WHEN THIS SESSION TOOK ITS BASELINE? Set once by `_session` from
# `tree_is_moving()` and stamped onto every survivor row, because a survivor list is read days
# later by somebody who has no other way to know a maintenance shift was mid-edit when the
# baseline photograph was taken. `None` means the question was never asked (a caller that used
# `run()` directly rather than the CLI). Order 78e796b8b9b6.
_TREE_WAS_MOVING = None


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
        row["tree_was_moving"] = _TREE_WAS_MOVING
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
# (Dedented from four spaces, order 0129ac1cee0a: comment-only lines emit no INDENT token so it
# always parsed, but at module level an indented comment reads as the tail of a function body,
# and in this file the comments are the documentation.)
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
        # ignore_errors=True means rmtree itself never raises -- the junction case in the
        # unlink loop just above (an unlinked-but-undeletable mount, permissions, a file still
        # open in the pass that crashed) leaves `p` standing with no exception to catch. The
        # citation here used to read ":506-511", which is the `ast.Compare` branch of
        # `_mutations` and has nothing to do with junctions; a line number inside a comment is a
        # claim nothing can keep honest, so it is named by position instead (order b2a113a33d50,
        # the same argument generate.py's "NAMED, NOT NUMBERED" comment on `job-failed` makes for
        # symbolic silence.note() tags). Check
        # what is actually on
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
    # JSON AND JSONL, and no logs. `state/` is 109 MB, almost all of it `.log` files no check
    # reads, and copying those per run would cost more than the mutation testing itself.
    #
    # `.jsonl` WAS EXCLUDED WITH THE LOGS AND IS NOT A LOG (order f8f74627266f). The append-only
    # ledgers live under that extension -- `ledger_chain.jsonl` (the tamper-evident chain),
    # `workorders_closed.jsonl` (the paper trail), `reap_ledger.jsonl`, `model_metrics.jsonl` --
    # and several checks read them, so five more nets sat BREACHED in the baseline of every
    # mutation run, which disables them as detectors for that whole run exactly as the missing
    # STEP4_PLAN.md did. Measured 2026-08-30: all six `.jsonl` files together are 14.1 MB, and
    # `sandbox()` is built ONCE per run rather than once per mutant, so the cost the original
    # rationale was avoiding does not apply to them. The `.log` exclusion stands unchanged; that
    # is where the 109 MB actually is.
    # RECURSIVE, NOT ONE LEVEL (order 21ae41adc29c). `os.listdir` names the top of `state/` and
    # nothing under it, so `state/sweep_shards/` -- 155 files, 30 KB -- was absent from the
    # baseline of every mutation run ever made. The two sweep-coverage rows in verify_math read
    # those shards to find the newest FINISHED sweep; with no shard on disk the first goes red
    # ("the sweep coverage ledger names a FINISHED run at all") and the second reports
    # `['<no finished sweep on record>']`. Both were therefore DISABLED AS DETECTORS for the
    # whole run, which is the same fault as the missing STEP4_PLAN.md one paragraph down,
    # arriving through the directory walk instead of the manifest.
    #
    # The whole `.json`/`.jsonl` payload under every subdirectory of `state/` is 0.23 MB
    # measured 2026-08-30 -- `backups/` is 359 MB but almost all of it is `.zip` and
    # `.pre*` source snapshots, which this filter never had any reason to take. There is no
    # volume argument against the recursive walk, only the accident that it was written flat.
    os.makedirs(os.path.join(root, "state"), exist_ok=True)
    _live_state = os.path.join(HERE, "state")
    for _dirpath, _, _files in os.walk(_live_state):
        _rel = os.path.relpath(_dirpath, _live_state)
        _dest = os.path.join(root, "state") if _rel == "." else os.path.join(root, "state", _rel)
        for f in _files:
            if not (f.endswith(".json") or f.endswith(".jsonl")):
                continue
            try:
                os.makedirs(_dest, exist_ok=True)
                shutil.copy2(os.path.join(_dirpath, f), os.path.join(_dest, f))
            except OSError:
                pass
    # AND THE SIX LOGS THE DASHBOARD ACTUALLY READS, which the blanket `.log` exclusion took
    # with the other 109 MB. `dashboard._read_row` tails `state/read_auto.log` for the `dropped`
    # count -- the model sentences the verbatim check rejected -- and `standards.check` turns
    # that into the HIGH standard `sentences that survive the verbatim check`. With the log
    # absent the row reads UNMEASURED, so three more verify_math rows sat red in every baseline:
    # `and it is MEASURED, not merely present`, `the reader's job dict carries the count the
    # guard needs`, and `every standard standards.py declares actually emits a row` (five of the
    # 46 declared standards cannot emit without their logs).
    #
    # DERIVED FROM `lognames`, NOT HAND-KEPT, for the same reason the root manifest above is
    # taken from `publish`: a second copy of a list is how the two come to disagree. `lognames`
    # is the module the dashboard itself names these files by, so a log added there travels here
    # without anyone remembering to. The six together are 4.3 MB, copied once per run.
    try:
        import lognames as _ln
        _gate_logs = sorted({getattr(_ln, _k) for _k in dir(_ln) if _k.isupper()
                             if isinstance(getattr(_ln, _k), str)
                             and getattr(_ln, _k).endswith(".log")})
    except Exception:
        silence.note("mutate.py:sandbox-lognames")
        _gate_logs = ("read_auto.log", "roll_auto.log", "pipeline_auto.log",
                      "recatalogue.log", "sweep.log", "calibrate.log")
    for f in _gate_logs:
        p_ = os.path.join(_live_state, f)
        if os.path.isfile(p_):
            try:
                shutil.copy2(p_, os.path.join(root, "state", f))
            except OSError:
                silence.note("mutate.py:sandbox-copy-log:" + f)
    # AND CASCADE'S SCRATCH DB, WHICH IS NEITHER `.json`, `.jsonl` NOR `.log` AND SO FELL
    # THROUGH EVERY FILTER ABOVE. Same fault as the missing STEP4_PLAN.md, the excluded `.jsonl`
    # ledgers and the flat `state/` walk that lost `sweep_shards/` -- a file the gates read is
    # absent from the sandbox, a check goes red in the BASELINE, and a red baseline DISABLES
    # that check as a detector for the entire mutation run, because mutants are judged by
    # difference from it. This one was worse than disabling a row: it took the whole pass down.
    # Measured 2026-09-03 -- `mutate --target all` REFUSED to run at all, on
    # "RED BASELINE TAKEN FROM A TREE UNDER EDIT", and the single red row was
    # `no probe anywhere in this battery writes into the live failure ledger`, reporting three
    # escapes: `verify_math.py:3639 -> silent:tuning.py:cloud-success` and two
    # `-> silent:cascade_bridge.py:provider-error`. All three are the SAME missing file.
    # `cascade_bridge.provider_error` opens it `mode=ro` and notes when that raises;
    # `tuning.cloud_success` connects without `mode=ro`, which CREATES an empty file and then
    # fails on `select ... from usage` because the table is not there, and notes too. Both were
    # reproduced directly by pointing `SCRATCH_DB` at a path that does not exist.
    #
    # BY NAME, NOT BY EXTENSION. A blanket `.db` would also drag in `state/corpus.db` -- 78 MB
    # of DERIVED index that nothing in the gate path reads and that was not red in any baseline
    # -- for 88.6 MB a run instead of 14.6. The name is taken from `cascade_bridge.SCRATCH_DB`
    # rather than written out here, for the reason the log list is taken from `lognames`: a
    # second copy of a path is how the two come to disagree.
    #
    # COPIED THROUGH SQLITE'S BACKUP API, NOT `shutil.copy2`. Cascade writes this database while
    # the sandbox is being built, and a byte copy of a live SQLite file can be torn -- which
    # would fail the same `select` and put the same three escapes back, INTERMITTENTLY. A
    # baseline that is red one run in five is harder to diagnose than one that is red every run,
    # so the consistent-snapshot path is the one that belongs here.
    try:
        import sqlite3 as _sq3
        import cascade_bridge as _cb_sb
        _scratch = _cb_sb.SCRATCH_DB
        if os.path.isfile(_scratch):
            _src_con = _sq3.connect("file:%s?mode=ro" % _scratch, uri=True, timeout=5.0)
            try:
                _dst_con = _sq3.connect(os.path.join(root, "state",
                                                     os.path.basename(_scratch)))
                try:
                    _src_con.backup(_dst_con)
                finally:
                    _dst_con.close()
            finally:
                _src_con.close()
    except Exception:
        # NOTED, NOT RAISED, and deliberately loud in the ledger: the sandbox is still usable
        # without it, but the baseline will carry those three escapes again and the run will
        # refuse. The note is what tells the next shift which of the two it is looking at.
        silence.note("mutate.py:sandbox-copy-scratch-db")
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
    # THE DOCUMENTS A GATE READS ARE PART OF THE GATE (order f8f74627266f). `STEP4_PLAN.md` was
    # not on this list, and `step4_gate_open` checks the PLAN before it checks the FLAG -- so in
    # the baseline of every mutation run ever made, the plan was absent, `_step4_needs_its_plan`
    # was BREACHED, and every step-4 net short-circuited on the same missing document instead of
    # discriminating. A net that is red in the baseline is DISABLED AS A DETECTOR, because
    # mutants are judged by DIFFERENCE from the baseline: it cannot kill anything.
    #
    # Measured while reproducing batch C01 on 2026-08-30: a sandbox baseline read `271 nets,
    # 265 held`; copying this one 15 KB file in turned that net green and dropped the breaches
    # to five. FIVE of that batch's twenty-two reported "survivors" were this artefact and
    # nothing else -- each is killed by an EXISTING net the moment the sandbox has the plan. The
    # mutation report was measuring the sandbox and reading exactly like a report about the
    # battery, which is this project's signature failure wearing a new hat.
    #
    # `config.yaml` was already here for the same reason and the plan belongs beside it: both
    # are repository-root documents a gate's predicate names, and a sandbox that silently omits
    # one produces confident nonsense.
    # DERIVED FROM PUBLISH'S OWN MANIFEST, not hand-kept (order 21ae41adc29c). `publish` already
    # maintains the authoritative list of what constitutes this library as a thing outside src/
    # -- COPY_FILES is every root document and COPY_DIRS every directory -- and the gates read
    # those documents: `ledger_guard` parses HANDOFF.md, BUGS.md, NEXT_STEPS.md and
    # MAINTENANCE.md by name, and the suppression nets scan COPY_DIRS for credential-shaped
    # values. A second hand-kept copy of that list here is exactly how the two come to disagree,
    # which is what happened: STEP4_PLAN.md was in publish's list and not in this one for the
    # whole life of the mutation tester.
    #
    # Measured 2026-08-30, sandbox baseline before this: `278 nets, 273 held, 5 BREACHED` --
    # `no suppression is expired or dangling`, `a suppressed finding is still REPORTED`, `the
    # live ledgers are intact`, `a TRUNCATION padded back to length is refused`, `an empty
    # overwrite is refused`. Every one of the five was the sandbox missing a file, not a defect,
    # and every one was therefore disabled as a detector for the whole run.
    #
    # COPIED, NOT JUNCTIONED, unlike data/prompts/reference above: a junction would let a
    # sandboxed run write into the REAL handoff/ and the real ledgers, and the whole point of a
    # sandbox is that a deliberately-corrupted library cannot reach the live one. 12.7 MB, once
    # per run. Imported lazily because `publish` imports `mutate` for its own interlock, and a
    # module-level import here would be a cycle; the literal fallback keeps the sandbox buildable
    # if publish is ever unimportable, which is the condition mutation testing most wants to
    # survive.
    try:
        import publish as _pub
        root_files, root_dirs = _pub.COPY_FILES, _pub.COPY_DIRS
    except Exception:
        silence.note("mutate.py:sandbox-manifest")
        root_files = ("CLAUDE.md", "README.md", "config.yaml", "requirements.txt", "WATCH.md",
                      "STATUS.md", "HANDOFF.md", "BUGS.md", "NEXT_STEPS.md", "MAINTENANCE.md",
                      "STEP4_PLAN.md")
        root_dirs = ("src", "prompts", "reference", "registry_terminal", "handoff")
    for f in root_files:
        p_ = os.path.join(HERE, f)
        if os.path.isfile(p_):
            try:
                shutil.copy2(p_, os.path.join(root, f))
            except OSError:
                silence.note("mutate.py:sandbox-copy:" + f)
    for d in root_dirs:
        # src is copied above file by file; the three shared corpora are junctioned above and
        # must stay that way -- they are gigabytes and nothing in the gate path writes to them.
        if d in ("src", "data", "prompts", "reference"):
            continue
        s_ = os.path.join(HERE, d)
        if os.path.isdir(s_) and not os.path.exists(os.path.join(root, d)):
            try:
                shutil.copytree(s_, os.path.join(root, d),
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            except OSError:
                silence.note("mutate.py:sandbox-copy-dir:" + d)
    return root


def baseline(root, gates=GATES, rows_out=None):
    """What does each gate say about UNMUTATED code? -> {gate: signature}.

    This is the reference every mutant is compared against. It does NOT require the tree to be
    green -- see `_gate_result` for why demanding green would mean never running at all. It only
    requires the gates to be REPRODUCIBLE: a gate whose signature changes between two clean runs
    is a gate that cannot judge anything, and `flaky_gates()` finds those before they produce
    imaginary survivors.

    `rows_out`, IF GIVEN, IS FILLED AS A SIDE EFFECT (order 2461a04d8849): {gate: [row id, ...]}
    naming the individual `FAILED`/`BREACHED` rows inside each gate's own output, not merely the
    signature -- so a caller can say WHICH checks are down when it reports a red baseline, rather
    than just that the gate is down. The return type is unchanged so every existing caller that
    treats `base` as {gate: signature} (`red_gates`, `unusable_gates`, `flaky_gates`,
    `_run_mutation`'s kill test, `run()`'s public contract) needs no changes.
    """
    out = {}
    for name, cmd in gates:
        out[name] = _gate_result(name, cmd, cwd=root, rows_out=rows_out)[0]
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
    return [(n, s_) for n, s_ in base.items() if could_not_judge(s_)]


def red_gates(base):
    """-> [(gate, signature)] for gates that DID reach a verdict on clean code and it was red.

    Deliberately distinct from `unusable_gates`, which is about gates that reached no verdict at
    all. A red baseline is not by itself a reason to refuse -- see `_gate_result`: this project
    carries a standing honest red most days, and "green or refuse" means "never runs". It is a
    reason to refuse only in combination with a tree somebody is editing; see `tree_is_moving`.
    """
    return [(n, s_) for n, s_ in base.items()
            if not could_not_judge(s_) and not s_.startswith("rc=0|")]


def tree_is_moving(now=None):
    """Is a maintenance shift part-way through editing src/ right now? -> (bool, why).

    THE BASELINE IS A PHOTOGRAPH OF A TREE THAT MAY BE MOVING, AND THAT COST A SHIFT ITS RUN.
    On 2026-08-29 a mutation pass was launched the moment `drill.py` was released, while a
    second agent was doing what the standing rule requires -- reinstating each defect in turn to
    watch its net go red before leaving it green. The sandbox snapshot froze six transient
    breaches into the baseline. Mutants are judged by DIFFERENCE from that baseline, so for the
    whole run those six nets were disabled as detectors (they cannot kill anything; they were
    already red) and any mutant reproducing exactly those breaches scored SURVIVED. A mutation
    pass exists to answer "which corruptions can this battery not see"; starting it with part of
    the battery held down answers a different question while looking exactly like an answer to
    the real one. Order 78e796b8b9b6.

    "all gates reproducible" did not catch it and could not: it reads each gate twice seconds
    apart, and the provocation outlasted both readings. Reproducible-over-seconds is not
    stable-for-the-hours the run will take.

    THE QUESTION IS ALREADY ANSWERED ELSEWHERE, so this asks it rather than inventing a second
    guard: `publish.maintenance_shift_live()` reads `state/MAINTENANCE_RUN.json` and reports
    whether a shift is mid-edit, treating a stale heartbeat as a crashed run.

    FAILS CLOSED, AND THAT IS THE OPPOSITE OF PUBLISH'S RULE FOR THE SAME READING. `publish`
    must fail OPEN because a wedged publisher is worse than one bad cycle. Here the asymmetry
    runs the other way: a mutation pass costs hours and produces a number people act on, and
    wasting the hours is cheaper than trusting the number. Note this only ever REFUSES in
    combination with a red baseline, so a failure to read the guard cannot block a run on a
    healthy tree.
    """
    try:
        # Imported here, not at module scope: `publish` imports `mutate` (for `active()`), so a
        # top-level import would be a cycle.
        import publish as _pub
        return _pub.maintenance_shift_live(now=now)
    except Exception as e:
        silence.note("mutate.py:maintenance-guard-unreadable")
        return True, ("could not ask publish.maintenance_shift_live (%s); assuming the tree is "
                      "being edited" % type(e).__name__)


def could_not_judge(sig):
    """-> True if this signature means the gate never reached a verdict, on clean code OR on a
    mutant.

    THE OTHER DIRECTION OF `unusable_gates`, AND IT WAS UNGUARDED (order d2fb14ffa8c6).
    `unusable_gates` reasons carefully about a baseline TIMEOUT producing false SURVIVORS. Once
    the baseline is healthy, a gate returning `TIMEOUT` or `ERROR:<Type>` on a MUTANT differs
    from the baseline signature, so the old code set `died_at` and counted a KILL -- and nothing
    in the result, the summary or the journal could tell a mutant the safeties caught from one
    whose gate merely failed to finish. `verify_math` reaches the network and the confirm gate
    carries a 1200-second timeout, so on a loaded machine "the gate could not finish" silently
    became "the safeties noticed", inside the one number this module exists to produce. False
    kills are the direction that HIDES holes, and they look exactly like real ones.
    """
    # PREFIX MATCH, not equality: `_gate_result` now names the gate in the signature itself
    # ("TIMEOUT|drill", "ERROR:OSError|verify_math") so an indeterminate row says which gate
    # gave up. A bare "TIMEOUT" still matches, which is what keeps older journal rows and the
    # drill net that hands one in literally reading the same way. Order 7bd7f47b012d.
    return sig.startswith("TIMEOUT") or sig.startswith("ERROR:")


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

    `base` IS REQUIRED IN EVERY REAL CALL. It still defaults to None in the signature, because
    the signature is public and callers pass it by keyword, but None is now a SENTINEL THAT
    REFUSES rather than a default that silently scores every mutant killed. Build one with
    `baseline(root)` and hand it in. The refusal, and the two baseline-health guards that used
    to live only in `_session`, are in `_run_mutation`.
    """
    with _hold_lock([target]):
        return _run_mutation(target, limit=limit, gates=gates, root=root, keep=keep,
                             base=base, confirm=confirm)


def _run_mutation(target, limit=None, gates=FAST_GATES, root=None, keep=False, base=None,
                  confirm=CONFIRM_GATES):
    """The body of `run`, with the mutation lock already held. Do not call this directly."""
    # A MISSING BASELINE IS REFUSED, NOT DEFAULTED (order 91c1a581453d). This was
    # `base = {} if base is None else base`, and `run()`'s public signature defaults
    # `base=None`, so every caller entering through `run()` -- which its own docstring names as
    # the way in for "the drill, a work-order reproduction, a future scheduler" -- got an empty
    # dict. The kill test is `sig != base.get(gname)`; `{}.get(x)` is None and no gate signature
    # is ever None, so the test was TRUE for the FIRST gate of EVERY mutant. Every mutant scored
    # killed, `survivors` came back empty, and the result dict reported a flawless score. That
    # is verbatim the failure `_gate_result`'s docstring exists to end -- "146 killed, 0
    # survived, a flawless score from a test that never tested anything" -- fixed on the CLI
    # path in `_session` and left standing on the public entry point.
    #
    # Refusing, rather than building a baseline here, is deliberate: a baseline costs a full
    # gate sweep and the caller has to know it is paying for one. Raising is what this function
    # already does for a restore that is not byte-exact, for the same reason.
    if base is None:
        raise RuntimeError(
            "no baseline: refusing to mutate %s. Every mutant would be scored KILLED, because "
            "the kill test compares each gate's signature against base.get(name) and an absent "
            "baseline answers None, which no signature ever equals. Call baseline(root) first "
            "and pass base=." % target)
    wanted = [g for g, _c in tuple(gates) + tuple(confirm)]
    ungauged = [g for g in wanted if g not in base]
    if ungauged:
        raise RuntimeError(
            "the baseline does not cover %s: refusing to mutate %s. A gate with no baseline "
            "entry is compared against None and kills every mutant it is asked about."
            % (", ".join(ungauged), target))
    # AND THE GUARDS THAT WERE ONLY IN `_session`. `unusable_gates` refuses a run whose gates
    # could not complete on CLEAN code -- there, `TIMEOUT == TIMEOUT` reports the whole set as
    # SURVIVING. It was called from the CLI path alone, so a caller entering through `run()`
    # got neither that guard nor `flaky_gates`. This is the cheap half; `flaky_gates` costs a
    # second full sweep and stays opt-in at the CLI, which is where somebody can decide to pay.
    dead = unusable_gates({g: base[g] for g in wanted})
    if dead:
        raise RuntimeError(
            "gates that could not complete on clean code (%s): refusing to mutate %s. A gate "
            "that cannot finish on unmutated code cannot judge a mutant."
            % (", ".join("%s=%s" % (n, s_) for n, s_ in dead), target))
    # WHICH GATES CANNOT KILL ANYTHING THIS RUN, CARRIED ALONGSIDE THE RESULT (order
    # 1b9a090fee64). `_session` already prints this list when it is non-empty (order
    # 90a5d3d6b96f) -- but only on the CLI path, and only at the console, where a survivor read
    # days later from `state/MUTANTS_SURVIVED.jsonl` or the result dict cannot see it. A gate
    # that is red in `base` matches every mutant's signature and kills nothing (the kill test is
    # `sig != base.get(gname)`), so a survivor scored while a detector was down needs that fact
    # travelling WITH it, not only printed once at launch. `red_gates` is a pure read of `base`
    # (no subprocess call), so recomputing it here costs nothing.
    red_at_baseline = [g for g, _s in red_gates({g: base[g] for g in wanted})]
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

        not_attempted = []
        muts = _mutations(tree, text, skipped=not_attempted)
        if limit:
            # Explicitly reported, never silent. Hard Rule 0 forbids a cap that hides a smaller
            # universe; this one is an interactive convenience and it must say so in the result.
            muts = muts[:limit]

        lines = text.splitlines(keepends=True)
        survivors, killed, indeterminate = [], 0, []
        try:
            for lineno, desc, old_line, new_line in muts:
                mutated = list(lines)
                mutated[lineno - 1] = new_line
                _write(path, "".join(mutated).encode("utf-8"))
                died_at = None
                no_verdict = None
                for gname, cmd in tuple(gates) + tuple(confirm):
                    # A SURVIVOR OF THE FAST GATES IS ONLY A CANDIDATE, so the expensive confirm
                    # gate is reached only by falling off the end of the fast ones -- the loops
                    # were merged so that the TIMEOUT/ERROR check below could not be added to one
                    # of them and forgotten on the other, which is how this defect got in.
                    sig, why = _gate_result(gname, cmd, cwd=root)
                    # THE GATE DID NOT REACH A VERDICT. Not a kill: see `could_not_judge`. The
                    # mutant is set aside as INDETERMINATE and counted separately, so `killed`
                    # and `survived` contain only mutants that were actually judged.
                    if could_not_judge(sig):
                        # `sig` and `why` both carry the gate name now (see `_gate_result`), so
                        # the caller no longer re-attaches `gname` by hand. Order 7bd7f47b012d.
                        no_verdict = sig
                        break
                    # DIFFERENT from clean, not merely failing. A gate that was already red on
                    # unmutated code stays red here and correctly kills nothing.
                    if sig != base.get(gname):
                        died_at = why
                        break
                if no_verdict:
                    # UNCUT (order c99634cb840e): this is the permanent record of the diff, not
                    # a console line. A [:120] slice here is indistinguishable from a short line
                    # -- Hard Rule 0 -- and it silently violates the module's own docstring
                    # promise (mutate.py:33) that a survivor "is filed with its exact diff rather
                    # than a count". Any bound belongs only at the point of printing (see the
                    # `[:70]` on the console summary line below, which is reversible because the
                    # full value lives here), never on what gets journaled or filed.
                    indeterminate.append({"line": lineno, "mutation": desc,
                                          "was": old_line.strip(),
                                          "became": new_line.strip(),
                                          "gate": no_verdict})
                elif died_at:
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
                    #
                    # UNCUT (order c99634cb840e): see the comment on the indeterminate branch
                    # above. `was`/`became` here are what `_journal` persists to
                    # MUTANTS_SURVIVED.jsonl and what `file_orders` pastes verbatim into the
                    # permanent work order -- Hard Rule 0 forbids truncating either without a
                    # marker, and the module's own docstring already promises the exact diff.
                    # "red_gates_disabled" TRAVELS WITH THE ROW (order 1b9a090fee64), beside
                    # `tree_was_moving` (which `_journal` stamps on itself) -- so a survivor read
                    # days later shows which detectors were down when it was scored, not only
                    # that some were.
                    _journal(target, {"line": lineno, "mutation": desc,
                                      "was": old_line.strip(),
                                      "became": new_line.strip(),
                                      "confirmed": bool(confirm),
                                      "red_gates_disabled": red_at_baseline})
                    survivors.append({"line": lineno, "mutation": desc,
                                      "was": old_line.strip(),
                                      "became": new_line.strip(),
                                      "confirmed": bool(confirm),
                                      "red_gates_disabled": red_at_baseline})
        finally:
            _write(path, original)

        # THE LIVE FILE MUST BE BYTE-IDENTICAL TO HOW WE FOUND IT. Not "should be" -- checked,
        # every run, because the whole class of incident this rewrite exists to end began with
        # a corrupted live file that nobody noticed until it was on GitHub.
        live_after = _digest(_read(live))
        return {"target": target, "mutants": len(muts), "killed": killed,
                "survived": len(survivors), "survivors": survivors,
                # WHICH GATES COULD NOT KILL ANYTHING THIS RUN (order 1b9a090fee64) -- a gate
                # already red in `base` matches every mutant and cannot judge one. Empty on a
                # clean baseline; named here (not just printed once by `_session`) so a caller
                # reading this dict, rather than the console, can see the same fact.
                "red_gates_disabled": red_at_baseline,
                # JUDGED, NOT SCORED. `killed + survived + indeterminate == mutants`, and the
                # third term is the one that used to be silently folded into the first.
                "indeterminate": len(indeterminate), "indeterminates": indeterminate,
                # SITES THIS RUN COULD NOT EVEN ATTEMPT. Reported beside the mutant count so
                # that "264 attempted" is never read as "264 attemptable" -- Hard Rule 0 applied
                # to the tool that measures coverage. Not truncated.
                "not_attempted": [{"line": ln, "kind": k, "why": w}
                                  for ln, k, w in not_attempted],
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
    # LINE-BUFFER STDOUT AS THE FIRST ACT (order af40a3c2e7e3). Python block-buffers stdout the
    # moment it is redirected to a file, so `python src/mutate.py ... > state/mutate_<date>.log`
    # writes NOTHING until the buffer fills or the process exits cleanly -- a run that is still
    # going, or that was killed, leaves a zero-byte log. Measured 2026-08-30 and before:
    # mutate_20260825.log, mutate_20260827.log and mutate_20260828.log were all 0 bytes, and the
    # 2026-08-30 run reproduced it on its OWN first launch despite run #37's NEXT_STEPS naming
    # the fix (`python -u`) explicitly, because the launch line lived in the maintenance card and
    # not in the module -- four different launchers (the card, the keeper, an owner at a prompt,
    # a scheduled run) and only one of them has to forget the flag. Doing it here means the log
    # is readable WHILE a multi-hour run is still in progress, no matter how it was started. This
    # does not change what gets logged or how a run is judged -- only when the bytes reach disk --
    # so it is safe to land under a mutation pass already in flight (that pass copied the tree at
    # launch and will not re-read this file).
    #
    # THE EMPTY LOG WAS NEVER A LOST RUN. `state/MUTANTS_SURVIVED.jsonl`, the filed work orders,
    # and `survivors_on_record()` are written independently of stdout and are unaffected either
    # way -- a zero-byte log is a reporting failure, not a data loss. Say that plainly if this is
    # ever the reason someone opens an old empty log expecting nothing to be recoverable.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        # stdout may already be closed, replaced, or a stream without `reconfigure` (rare, but
        # this must never be the reason the run itself fails to start).
        pass
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
            skipped = []
            n = len(_mutations(ast.parse(text), text, skipped=skipped))
            # THE COUNT ALONE WAS THE DEFECT. `--list` printed "N mutant(s)" and nothing said
            # which sites produced none, so a number that had silently excluded 59% of the
            # comparison operators in the file read as the whole attemptable set. Every skipped
            # site is named -- no cap, no "and N more" -- because this is the listing a person
            # reads to decide whether the coverage number means anything.
            print("  %-18s %4d mutant(s)%s"
                  % (t, n, "" if not skipped else
                     "   %d SITE(S) NOT ATTEMPTED:" % len(skipped)))
            for ln, kind, why in skipped:
                print("       %s:%-5d %-8s %s" % (t, ln, kind, why))
        return 0

    # SESSION-LEVEL HOLD, above the per-target one. `--target all` is ONE continuous window in
    # which this machine is deliberately breaking code, and a publisher that slipped through the
    # gap between two targets would be pushing during a mutation run by any honest reading of
    # the phrase. Held from before the sandbox is built until after it is torn down.
    with _hold_lock(targets):
        return _session(a, targets)


def _session(a, targets):
    """One mutation session, with the lock held. -> exit code."""
    global _TREE_WAS_MOVING
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
        # base_rows IS THE SIDE CHANNEL (order 2461a04d8849): {gate: [row id, ...]}, the
        # individual FAILED/BREACHED lines behind each gate's signature. See `baseline`'s
        # docstring and `_row_ids` for why a red baseline used to be reported by SIGNATURE ALONE
        # -- "verify_math rc=1|RESULT: 1055 passed, 5 FAILED" and nothing naming which five --
        # which cost a shift a hand-built sandbox and a manual diff to learn the answer was five
        # sandbox omissions, not library defects.
        base_rows = {}
        base = baseline(root, gates=gates + confirm, rows_out=base_rows)
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
                for rid in base_rows.get(gname) or []:
                    print("       %s" % rid)
            print("\nA gate that cannot finish on unmutated code cannot judge a mutant. Every")
            print("comparison against it would read TIMEOUT == TIMEOUT and report the whole")
            print("set as surviving, which looks exactly like a finished run.")
            return 4

        # WAS THE TREE MOVING WHEN THAT PHOTOGRAPH WAS TAKEN? See `tree_is_moving` for the
        # 2026-08-29 incident this is the repair for. Asked AFTER the baseline rather than
        # before, so the answer can be weighed against what the baseline actually said: a red
        # baseline on a quiet tree may be a real standing fault the run can legitimately be
        # judged against, and a blanket "refuse unless green" would block the very shift that
        # is supposed to launch this. It is the COMBINATION -- red, and somebody editing --
        # that means the redness is probably transient. Order 78e796b8b9b6.
        moving, why_moving = tree_is_moving()
        _TREE_WAS_MOVING = moving          # stamped onto every survivor row; see `_journal`
        red = red_gates(base)
        if moving:
            print("\n*** A MAINTENANCE SHIFT IS EDITING THIS TREE: %s" % why_moving)
            print("    The baseline above is a snapshot of source somebody is changing.")
        if moving and red:
            print("\nRED BASELINE TAKEN FROM A TREE UNDER EDIT — REFUSING TO MUTATE.")
            for gname, sig_ in red:
                print("   %-14s %s" % (gname, sig_[:90]))
                for rid in base_rows.get(gname) or []:
                    print("       %s" % rid)
            print("\nMutants are judged by DIFFERENCE from the baseline, so a gate that is red")
            print("in it is disabled as a detector for the whole run and any mutant that")
            print("reproduces exactly that redness scores SURVIVED. While a shift holds the")
            print("guard the redness is most likely a net being deliberately provoked, not the")
            print("state of the library. Relaunch once the LAST agent touching drill.py or")
            print("verify_math.py has finished. (A red baseline on a QUIET tree is a different")
            print("thing and is allowed through -- it may be a real standing fault.)")
            return 6
        if red:
            # A RED BASELINE ON A QUIET TREE IS ALLOWED THROUGH, AND IT MUST STILL BE
            # SAID (order 90a5d3d6b96f, sweep39-batch07). `red_gates` was computed and
            # its answer used only by the `moving and red` arm above, so on a quiet tree
            # the list was discarded and the very next line printed "all gates
            # reproducible" -- with part of the battery disabled for the whole run.
            #
            # Disabled is exactly what it means, in this module's own words: mutants are
            # judged by DIFFERENCE from the baseline, so a gate that is already red
            # matches every mutant's signature and cannot kill anything. A run reporting
            # survivors while a detector is switched off reads exactly like a run
            # reporting survivors while it is not, which is the failure this whole module
            # exists to measure, arriving inside the measurement.
            #
            # Named rather than refused: the refusal above is deliberately narrow (a red
            # baseline is allowed through on a quiet tree because it may be a real
            # standing fault, and "green or refuse" means "never runs"). The fix is to
            # stop it being SILENT, not to stop it happening.
            print("\nRED IN THE BASELINE ON A QUIET TREE — RUNNING ANYWAY, BUT THESE "
                  "GATES ARE DISABLED:")
            for gname, sig_ in red:
                print("   %-14s %s" % (gname, sig_[:90]))
                # NAMED, NOT JUST SIGNATURED (order 2461a04d8849). Which rows are actually red
                # is what tells a reader whether this is a real standing fault or a sandbox
                # artefact -- the finding that cost a shift a hand-built sandbox to learn once.
                for rid in base_rows.get(gname) or []:
                    print("       %s" % rid)
            print("   Each is already red on UNMUTATED code, so it matches every mutant "
                  "and kills none.")
            print("   Any survivor below may be this and not a hole in the battery. "
                  "Read these first.")

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
        # "reproducible" is qualified out loud when the tree is moving, because the unqualified
        # line reads as an all-clear and it is only ever a statement about two readings seconds
        # apart -- not about the hours this run will take. Order 78e796b8b9b6.
        print("all gates reproducible; mutants judged by DIFFERENCE from the above"
              + ("   *** BUT THE TREE IS BEING EDITED -- reproducible over seconds is not"
                 " stable over the hours this run takes ***" if moving else ""))

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
        # A REFUSAL THAT PRINTS AND DOES NOT STOP THE CALLER, INSIDE THE MODULE WRITTEN TO FIND
        # THAT SHAPE. Both branches below used to print a full stop -- "Later targets are
        # unreliable", "THE LIVE FILE CHANGED DURING A SANDBOXED RUN. STOP." -- escalate, and
        # then fall straight into the next iteration: the remaining targets were mutated in the
        # sandbox this code had just declared unreliable, their survivors were printed as
        # findings and filed by --file-orders, and `_session` returned 0 with an OWNER halt
        # standing on disk. `escalation.escalate()` does not raise, by its own docstring --
        # "Raising is the CALLER's decision for rungs 1-4" -- so stopping is this loop's job and
        # nothing else's. `main()`'s halt check only guards the START of a session. The rc is
        # carried out of the loop and returned in place of the old unconditional `return 0`.
        # Order 282ae72dfaec.
        rc = 0
        stopped_at = None
        for i, t in enumerate(targets):
            t0 = time.time()
            r = run(t, limit=a.limit, root=root, base=base, gates=gates, confirm=confirm)
            total_s += time.time() - t0
            print("\n%s — %d mutants, %d killed, %d SURVIVED, %d INDETERMINATE   (%.0fs)"
                  % (t, r["mutants"], r["killed"], r["survived"], r["indeterminate"],
                     time.time() - t0))
            if not r["restored_exactly"]:
                print("  *** THE SANDBOX FILE WAS NOT RESTORED. Later targets are unreliable. ***")
                escalation.escalate(escalation.MANAGER, "MUTATE_RESTORE_FAILED",
                                    "mutate.py did not restore %s in the sandbox" % t,
                                    evidence=r, source=t, who="mutate.py")
                # Every remaining target shares `root`, so they would be judged against a
                # sandbox this run has just declared unreliable.
                rc, stopped_at = 4, i
            if not r["live_file_untouched"]:
                # This must be impossible by construction -- the live path is never opened for
                # writing. Checked anyway, and at OWNER level, because the incident that caused
                # this rewrite was a corrupted live file reaching a public repo.
                print("  *** THE LIVE FILE CHANGED DURING A SANDBOXED RUN. STOP. ***")
                escalation.escalate(escalation.OWNER, "MUTATE_TOUCHED_LIVE_TREE",
                                    "src/%s changed during a sandboxed mutation run" % t,
                                    evidence=r, source=t, who="mutate.py")
                # OWNER writes the halt file, and this process must not keep deliberately
                # corrupting code underneath a standing halt. Nothing further at all.
                rc, stopped_at = 5, i
            if r["capped"]:
                print("  (capped at --limit %d; this is NOT the whole set)" % a.limit)
            # NEITHER KILLED NOR SURVIVED, AND SAID SO. A gate that timed out or errored on a
            # mutant used to be counted as a kill, which is the direction that hides holes.
            for s_ in r["indeterminates"]:
                print("  NO VERDICT %s:%-5d %-16s  gate %s"
                      % (t, s_["line"], s_["mutation"], s_["gate"]))
            if r["indeterminate"]:
                print("  %d mutant(s) were never judged. They are NOT in the killed count and"
                      " NOT in the survived count; the score below is over %d judged mutants,"
                      " not %d." % (r["indeterminate"], r["killed"] + r["survived"],
                                    r["mutants"]))
            # WHAT WAS NOT EVEN ATTEMPTED, printed in full. See `_mutations`'s `skipped`.
            for na in r["not_attempted"]:
                print("  NOT ATTEMPTED %s:%-5d %-8s %s"
                      % (t, na["line"], na["kind"], na["why"]))
            for s in r["survivors"]:
                tag = "SURVIVED " if confirm else "UNCONFIRMED"
                print("  %s %s:%-5d %-16s  %s"
                      % (tag, t, s["line"], s["mutation"], s["was"][:70]))
            if r["survivors"] and not confirm:
                print("  --no-confirm was used: these passed the FAST gates only. They are"
                      " candidates, not findings, and must not be filed as findings.")
            if a.file_orders and r["survivors"] and confirm:
                print("  filed %d work order(s)" % len(file_orders(r)))
            # BREAK AFTER this target's own report, not before it: the findings for the target
            # that tripped the check were computed before the check tripped and are still worth
            # printing. What must not happen is the NEXT target.
            if stopped_at is not None:
                break
        if stopped_at is not None:
            skipped = targets[stopped_at + 1:]
            print("\n*** RUN IS PARTIAL. Stopped after %s. %d target(s) not attempted%s"
                  % (targets[stopped_at], len(skipped),
                     "." if not skipped else ": " + ", ".join(skipped)))
            print("    Exit code %d. The survivor list above covers %d of %d targets and is"
                  " NOT a coverage number for this library."
                  % (rc, stopped_at + 1, len(targets)))
        print("\ntotal %.0fs" % total_s)
        return rc
    finally:
        if not a.keep_sandbox:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
