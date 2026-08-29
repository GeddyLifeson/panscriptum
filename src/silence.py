#!/usr/bin/env python3
"""
SILENCE — the audit for this project's one recurring defect, and the discipline that ends it.

THE DEFECT
----------
Fifteen separate faults were found on 2026-08-21/22. Listed as a list they read as bad luck.
Lined up by shape they are ONE fault, repeated:

    Wikipedia served 404 on the wrong API path   ->  "5,590 entities have no page"
    chunks overflowed num_ctx and were truncated ->  "the model fabricates 51% of the time"
    a word-boundary escape became 0x08           ->  "the gate is too strict"
    a batch closed on write instead of on result ->  "judged"  (378 entries stranded)
    failed synthesis wrote an empty block        ->  "no ceiling exists here"
    the evidence gate could only see Ruin        ->  "no evidence on ten axes"
    a slug-guessed host answered, wrong fiction  ->  2,765 pages from the wrong Descent
    strip_wikitext ate template-wrapped articles ->  3,736 entities "read as empty pages"

That last one is the clearest. Marvel's 233 silent entries were recorded as CORRECT SILENCE --
an honest finding that those characters had no feats -- when in fact a 190,687-character page had
been reduced to thirty characters. The library did not merely lose data. It filed the loss as a
result and moved on.

Every one of those went through a bare `except Exception: return None` or an equivalent. How many
such handlers this tree currently holds is not a number worth freezing into prose -- the count
moves every time a module is added, split, or instrumented, so a hardcoded figure here would be
stale before the next sweep finished reading it. Run `python src/silence.py` for the live count;
the fifteen above were its output, not a snapshot of the total.

WHY IT IS SO EXPENSIVE
----------------------
A crash costs minutes. A silent null costs a full investigation, because "broken" and "genuinely
empty" are indistinguishable downstream, and the honest-looking answer is the one that gets
believed. Worse, the library is BUILT to record absences faithfully -- READ-with-no-feat is a
real finding here -- so a swallowed failure lands in exactly the shape the design trusts.

WHAT THIS FILE DOES
-------------------
It does not forbid catching exceptions. Some of them are correct: a wiki page that will not parse
should not stop a roll of 54,000. What it forbids is catching one SILENTLY.

    swallow(kind)    a context manager that records the failure and continues
    audit()          finds every handler in src/ that still returns without recording

The rule the audit enforces: a failure may be tolerated, but never unobserved. Once every
handler reports, `health.py --failures` shows 5,590 Wikipedia 404s as a wall of identical
records instead of as a plausible absence, and the investigation that cost a day becomes a
glance.
"""
import argparse
import ast
import glob
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# THE EXPORT COPY IS NOT THE PROJECT.
#
# `publish.py` copies all of src/ into an export tree so the public repo carries the code.
# That tree is a complete, runnable duplicate -- and running or editing it instead of the
# live one is silent: the module imports, the edit succeeds, and the change lands somewhere
# nothing reads. It caught me twice in one session, once losing a standards floor and once
# pointing a sweep at a data directory that does not exist there.
#
# `publish` drops a marker beside the copy. Every module imports `silence`, so this one
# check guards all of them, and a wrong-tree run now fails at import with the reason
# instead of succeeding into the void.
_MARKER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       ".is-export-copy")
if os.path.exists(_MARKER):
    raise SystemExit("This is the PUBLISHED COPY, not the project. Run from the real "
                     "project directory -- edits and runs here reach nothing.")

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")


class swallow:
    """Tolerate a failure, but never unobserved.

        with swallow("fetch", host):
            ...

    On an exception the failure is recorded by CLASS -- the class is what makes a pattern
    visible, and a pattern is what turns 5,590 identical failures from "these entities have no
    page" into "the API path is wrong". The block then continues, which is the whole point: a
    single unparseable page must not stop a roll of 54,000.
    """

    __slots__ = ("detail", "error", "failed", "kind", "reraise")

    def __init__(self, kind, detail="", reraise=False):
        self.kind = kind
        self.detail = str(detail)[:60]
        self.reraise = reraise
        self.failed = False
        self.error = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            return False
        self.failed = True
        self.error = exc
        try:
            import health
            health.record(f"{self.kind}:{exc_type.__name__}", self.detail)
        except Exception:
            pass          # the recorder itself must never be the thing that breaks a run
        return not self.reraise


def _handlers(path):
    """Every `except` in a file, with whether its body records anything."""
    try:
        with open(path, encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src)
    except Exception:
        # A FILE THIS AUDIT CANNOT READ IS NOT A FILE WITH NO HANDLERS, and returning `[]` here
        # silently was this module's own defect turned on itself: an unreadable or unparseable
        # module contributes zero rows and reads downstream -- in `main()`'s counts, in
        # `secondopinion`'s tally -- exactly like a clean one. The one audit whose whole subject
        # is failures filed as honest absences must not file its own that way. Recorded, and said
        # out loud on stderr, because the printed count is otherwise quietly short.
        note("silence.py:_handlers:" + os.path.basename(path))
        print("silence.py: %s could not be read or parsed -- its handlers are NOT counted in "
              "this audit" % os.path.basename(path), file=sys.stderr)
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        # ASK THE BODY, NOT THE HANDLER. This read `ast.dump(node)`, which serialises the
        # handler's EXCEPTION TYPE as well as its statements -- so `except LogError:` or any
        # type whose name contains log/record/raise marked itself observed with an empty body.
        # Exactly the tautology fixed one line below, one node up: the test must look at what
        # the handler DOES, never at how it is spelled.
        body = "".join(ast.dump(stmt) for stmt in node.body)
        records = any(t in body for t in ("health", "record", "log", "print", "raise",
                                          "swallow", "silence", "LEDGER"))
        # A handler that re-raises, logs, or carries the exception into its own return value
        # is observed. One that only returns or continues is not -- that is the shape that
        # turned a 404 into "these entities have no page".
        #
        # THIS TEST WAS A TAUTOLOGY UNTIL RUN #33, in the detector built to find tautologies.
        # It read `node.name in body`, and `body` is `ast.dump(node)` -- the dump of the
        # handler itself, which always serialises `name='e'`. So `'e' in body` was True for
        # EVERY `except ... as e:`, whether or not `e` was ever touched, and
        # `except Exception as e: return None` -- the canonical fault this module exists to
        # catch -- classified itself as observed. Ask the body instead: is the bound name
        # actually loaded anywhere inside it.
        uses_exc = bool(node.name) and any(
            isinstance(n, ast.Name) and n.id == node.name
            for stmt in node.body for n in ast.walk(stmt))
        silent = not (records or uses_exc)
        out.append({"file": os.path.basename(path), "line": node.lineno,
                    "type": getattr(node.type, "id", None) if node.type else "bare",
                    "silent": silent})
    return out


def audit(root=None):
    root = root or os.path.join(HERE, "src")
    rows = []
    for p in sorted(glob.glob(os.path.join(root, "*.py"))):
        rows += _handlers(p)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="list observed handlers too")
    ap.add_argument("--instrument", action="store_true",
                    help="insert a note() call into every silent handler (writes .presilence backups)")
    ap.add_argument("--dry", action="store_true", help="with --instrument, report without writing")
    a = ap.parse_args()
    if a.instrument:
        changed = instrument(dry=a.dry)
        total = sum(n for _, n in changed)
        verb = "would instrument" if a.dry else "instrumented"
        print(f"{verb} {total} silent handlers across {len(changed)} modules")
        for f, n in sorted(changed, key=lambda kv: -kv[1]):
            print(f"   {n:>3}  {f}")
        return 0
    rows = audit()
    silent = [r for r in rows if r["silent"]]
    print("=" * 78)
    print(f"SILENCE AUDIT — {len(rows)} exception handlers in src/")
    print("=" * 78)
    print(f"\n  observed (record, log, or re-raise) : {len(rows) - len(silent)}")
    print(f"  SILENT (swallow and continue)       : {len(silent)}")
    if silent:
        print("\n  each of these can turn a failure into a plausible negative result:\n")
        by = {}
        for r in silent:
            by.setdefault(r["file"], []).append(r["line"])
        for f, lines in sorted(by.items(), key=lambda kv: -len(kv[1])):
            print(f"   {len(lines):>3}  {f:<24}lines {', '.join(map(str, lines[:12]))}")
    if a.all:
        for r in rows:
            if not r["silent"]:
                print(f"   ok   {r['file']}:{r['line']}")
    return 1 if silent else 0




def append_line(path, text):
    """Append ONE line to a shared ledger without tearing it (m62).

    Five live processes append to `state/model_metrics.jsonl` -- both `_metric` writers, across
    `pipeline`, `cascade_bridge` and every job that imports them. They each used
    `open(path, "a")` plus `f.write(...)`, which is a BUFFERED write: Python may split one line
    into several underlying writes, and two processes interleaving mid-line produce a row that
    parses as neither. Measured 2026-08-24: 5 corrupt lines, three of them mid-record fragments.

    Exposure was low (0.019%) and the consequence is quiet rather than loud, which is the
    argument for fixing it rather than against: `standards.py`'s ledger reader `continue`s past
    an unparseable line, correctly, so a torn row is invisible from the one place that reads
    them most. The metrics ledger is also now load-bearing -- `ollama_token_flow` decides a
    standard from it.

    One `os.write` to an `O_APPEND` descriptor is a single syscall, and the kernel does the
    seek-to-end and the write together. That is not a general atomicity guarantee for arbitrary
    sizes, but for a sub-page JSON line it is the difference between interleaved-and-corrupt and
    interleaved-but-whole. Best-effort exactly as before: a metrics failure must never cost a
    call.
    """
    try:
        data = text.encode("utf-8") if isinstance(text, str) else text
        if not data.endswith(b"\n"):
            data += b"\n"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(fd, data)
        finally:
            os.close(fd)
        return True
    except Exception:
        note("silence.py:append_line")
        return False


# The third answer `digest_of` cannot give, because its contract is two-valued. Kept private
# and compared by identity, never by value, so it can never collide with a real 16-hex digest.
UNREADABLE = "<unreadable>"


def _digest_or_unreadable(path):
    """`digest_of`, but with ABSENT (None) and COULD-NOT-BE-READ (UNREADABLE) kept apart.

    `digest_of` must go on returning None for both -- `replace_if_unchanged`'s documented
    contract is that `expected_digest=None` ASSERTS the file did not exist, and every caller
    that has read a digest and passed it back depends on that. But the compare-and-swap itself
    cannot treat the two alike: a transient read failure on a file that DOES now exist -- a
    concurrent writer mid-replace, which is precisely the race this layer exists to catch --
    returned None, matched an honest first-writer's None, and landed the stale copy over the
    other writer's work. Same sentinel, opposite meanings, and the write reported success.
    """
    import hashlib
    try:
        with open(path, "rb") as f:
            return hashlib.sha1(f.read()).hexdigest()[:16]
    except FileNotFoundError:
        return None
    except Exception:
        note("silence.py:digest_of")
        return UNREADABLE


def digest_of(path):
    """A cheap content digest for compare-and-swap. None when the file is absent.

    None is also returned when the file exists but could not be read; callers that must tell
    those two apart use `_digest_or_unreadable`, which is what `replace_if_unchanged` does.
    """
    d = _digest_or_unreadable(path)
    return None if d is UNREADABLE else d


def replace_if_unchanged(tmp, dst, expected_digest, attempts=5):
    """Land `tmp` over `dst` ONLY if `dst` still holds what the writer read. -> (ok, reason).

    THE HAZARD THIS CLOSES (m42, and it has cost this project real data twice). `replace_retry`
    below solves a DIFFERENT problem -- a Windows rename denied while a reader holds the target
    -- and solves it well. What neither it nor the callers had was any notion of STALENESS: a
    writer that read a file at 11:15, was orphaned, and landed its copy at 13:40 wins, and the
    two and a half hours of other writers' work in between vanish. The write SUCCEEDS, which is
    why nothing ever reported it. `WIKI_HOSTS.json` was written from a stale snapshot exactly
    this way, and `overwatch`'s ledger nearly lost 68 rounds to the same shape (m40).

    The caller reads the digest when it reads the file, and passes it back here. A mismatch is
    NOT an error to swallow -- it means the caller's copy is out of date and it should re-read
    and re-merge, which is what `write_record` already does properly for records.

    `expected_digest=None` asserts the file did not exist when it was read, which is how a
    first-write is distinguished from an overwrite.
    """
    actual = _digest_or_unreadable(dst)
    if actual is UNREADABLE:
        # NOT the same as absent, and the difference is the whole point. An unreadable target
        # cannot be shown to still hold what the writer read, so it is not eligible for a
        # compare-and-swap. Refusing costs a round; landing costs whatever the other writer put
        # there, silently, which is the m42 loss this function was written after.
        note("silence.py:stale-write-refused")
        return False, ("%s could not be read, so it cannot be shown to be unchanged -- "
                       "refusing to land over it. Retry next round."
                       % os.path.basename(dst))
    if actual != expected_digest:
        note("silence.py:stale-write-refused")
        return False, ("%s changed under this writer (expected %s, found %s) -- refusing to "
                       "land a stale copy. Re-read and merge."
                       % (os.path.basename(dst), expected_digest, actual))
    # THE REASON MUST MATCH THE VERDICT. This returned `..., "landed"` unconditionally, so a
    # DENIED rename came back as `(False, "landed")` and every caller that logs the reason --
    # `runguard.claim()` among them since it was routed here today -- printed "landed" for a
    # write that did not land. The two halves of the return now agree.
    if replace_retry(tmp, dst, attempts=attempts) is False:
        return False, ("%s could not be renamed into place (denied after %d attempts, most "
                       "likely a reader holding it open) -- nothing landed. Retry next round."
                       % (os.path.basename(dst), attempts))
    return True, "landed"


def replace_retry(tmp, dst, attempts=5):
    """os.replace with a short retry, because on Windows the rename is DENIED while any
    reader holds the target open -- and this project's state files all have readers on their
    own clocks (the dashboard polls records and ASSAYS, standards scans readfeats). One such
    collision took an assay worker down mid-batch (2026-08-23, WinError 5). A brief backoff
    outwaits any honest reader; persistent denial is recorded, never raised -- the caller's
    write lands next round.

    NEVER RAISES, FOR **ANY** OSError, not only for the denied one. `write_json`'s docstring has
    always promised "never raises on a denied replace" and every writer in this project routes
    through here, but the handling was a single `except PermissionError` -- so any OTHER OSError
    from `os.replace` went straight up through `write_json` into a caller that, by that
    promise, has no handler for it. The realistic one is a CROSS-DEVICE rename (`EXDEV`,
    WinError 17): the temp file and the target sit in the same directory, so that only happens
    when the directory is a junction or a mapped drive whose two ends are different volumes --
    rare, and exactly the kind of environment fault that would otherwise take down a batch
    worker in a way nothing here was written to expect. `ENOSPC`, a vanished temp file, and a
    target that has become a directory are the same shape.

    Those are NOT retried, deliberately. The backoff exists for one specific condition -- a
    reader holding the target open, which passes -- and a cross-device rename or a full disk
    will not pass in 1.5 seconds. Retrying them would spend the worker's time to reach the same
    answer. So the failure is recorded and reported as False, which is the verdict every caller
    already gates on."""
    import time as _t
    for a in range(attempts):
        try:
            os.replace(tmp, dst)
            return True
        except PermissionError:
            if a == attempts - 1:
                note("replace-denied:" + os.path.basename(dst))
            else:
                _t.sleep(0.3 * (a + 1))
        except OSError:
            # A DIFFERENT FAULT WEARS A DIFFERENT NAME IN THE LEDGER. `replace-denied` means
            # "a reader is holding it, try next round"; this one means "this rename cannot
            # succeed", and collapsing the two would hide a permanent condition inside the
            # count of a transient one -- the fault this whole module exists to stop.
            note("replace-failed:" + os.path.basename(dst))
            return False
    return False


# --------------------------------------------------------------------------- the recorder

_ATEXIT_ARMED = False
_SINCE_FLUSH = 0
FLUSH_EVERY = 25


def write_json(path, obj, **dump_kw):
    """Land a JSON file ATOMICALLY. The one correct way to write a shared file in this project.

    Found by the 2026-08-25 comprehensive sweep: TWELVE call sites across ten modules were
    writing shared `data/` and `state/` files with a bare `open(path, "w")` + `json.dump`, which
    is not a write but a TRUNCATE-THEN-FILL. A reader arriving in the gap sees an empty or
    half-written file; a crash in the gap leaves it that way permanently. Four of those sites
    were writing the SAME file -- `data/SWEEP_ROLL.json` -- from four different scripts, which
    is the hazard `resync_roll.py`'s own docstring already warned about in prose while the code
    went on doing it. `catalogue_web.save_roll()` had the atomic version and a comment saying an
    interrupted write here "kills the next run of either script outright"; its siblings did not.

    THE TMP NAME CARRIES PID AND THREAD, which the older hand-rolled `path + ".tmp"` sites did
    not. Two writers of the same path otherwise collide on the temp file itself, and the loser
    can replace the winner's target with a partial file -- the same race `read.py:_chunk_put`
    was already fixed for individually, now unavailable to get wrong.

    Returns True if the file landed. Never raises on a denied replace: `replace_retry` records
    it and the caller's write lands next round, which is the established behaviour here.
    """
    import json as _j            # local, matching `replace_retry`'s own idiom: this module is
    import threading as _th      # imported by nearly everything and stays deliberately thin
    dump_kw.setdefault("indent", 1)
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = "%s.%d.%d.tmp" % (path, os.getpid(), _th.get_ident())
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            _j.dump(obj, f, **dump_kw)
    except Exception:
        _discard_tmp(tmp)
        raise
    landed = replace_retry(tmp, path)
    if not landed:
        # AND THE TEMP GOES WHEN THE REPLACE IS REFUSED, NOT ONLY WHEN THE DUMP THROWS.
        # This branch used to return with the file still on disk, so EVERY denied write leaked
        # one `<path>.<pid>.<tid>.tmp` beside its target, permanently, with no cleaner anywhere
        # in the tree -- and the pid/thread qualifier that makes the name collision-proof also
        # makes each leak uniquely named, so they accumulate rather than overwrite. A denied
        # replace is the ORDINARY case here (it is the entire reason `replace_retry` exists), so
        # the leak was proportional to how contended a file is: the hottest files littered most.
        # `hostcheck.py:170` records the same litter one layer up for `replace_if_unchanged`.
        # The temp holds nothing anyone can use -- the caller's write lands next round from the
        # live object, never from this file -- so dropping it loses no data.
        _discard_tmp(tmp)
    return landed


def _discard_tmp(tmp):
    """Remove a scratch file, and never let the removal itself become the failure.

    Total by design, exactly like `note()`: this runs on the error paths of the function every
    writer in the project routes through, so a raise from the CLEANUP would replace a recorded,
    survivable denied write with an unhandled exception in a caller that -- by `write_json`'s
    own promise -- has no handler for it.
    """
    try:
        if os.path.exists(tmp):
            os.remove(tmp)
    except Exception:
        note("silence.py:tmp-not-removed")


def note(site):
    """Record the exception currently being handled, then return.

    Called from inside an `except` body by the rewriter in `--instrument`. It is deliberately
    total: a recorder that can itself raise would reintroduce the very fault it exists to
    expose, so every failure inside it is dropped on the floor.

    The atexit arming matters. `health.record` accumulates in memory and only `flush()` writes
    `state/failures.json`; most of these modules are run as one-shot subprocesses that never
    call flush, so without this the ledger would be another silent null.
    """
    global _ATEXIT_ARMED, _SINCE_FLUSH
    try:
        exc, val = sys.exc_info()[0], sys.exc_info()[1]
        name = exc.__name__ if exc else "None"
        import health
        # The repr of the actual exception rides along as a sample -- a class with a count but
        # no instance costs a grep and a reproduction every time somebody diagnoses it.
        health.record(f"silent:{site}", name, sample=repr(val) if val else None)
        if not _ATEXIT_ARMED:
            import atexit
            atexit.register(health.flush)
            _ATEXIT_ARMED = True
        # An atexit flush alone would hide the ledger for the whole life of a job, and the jobs
        # that matter here run for hours. A reader failing every call from its first minute
        # would look, from outside, exactly like a reader working slowly -- so the count reaches
        # disk while the run is still going and can still be stopped.
        _SINCE_FLUSH += 1
        if _SINCE_FLUSH >= FLUSH_EVERY:
            _SINCE_FLUSH = 0
            health.flush()
    except Exception:
        pass


# --------------------------------------------------------------------------- the rewriter

SKIP_FILES = {"silence.py", "health.py"}   # the recorder must not record itself


def _ensure_import(src):
    """Add `import silence` after the module's last top-level import.

    Placement matters more than it looks. Prepending to line 1 would demote the module
    docstring to a bare expression, and several modules here read their own docstring; splicing
    after an arbitrary `import sys` match could land inside a docstring or a function body. The
    last top-level Import node is the one position that is always correct.
    """
    tree = ast.parse(src)
    # THE HEAD BLOCK, NOT THE LAST IMPORT IN THE FILE.
    #
    # Several modules here import inline all the way down -- verify_math.py opens a new section
    # with `import ledger as L` two hundred lines in, and again at four hundred, and again at
    # seven hundred. "After the last top-level import" put the recorder at line 917 of a file
    # that first calls it at line 48, so the module raised NameError the moment anything went
    # wrong: an instrument that breaks precisely when it is needed. The correct anchor is the
    # END OF THE FIRST CONTIGUOUS RUN of top-level imports.
    last = 0
    for node in tree.body:
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if any(getattr(a, "name", "") == "silence" for a in getattr(node, "names", [])):
            return src
        end = getattr(node, "end_lineno", node.lineno)
        if last and node.lineno > last + 3:
            break                      # a later, detached import block: stop here
        last = max(last, end)
    lines = src.splitlines(keepends=True)
    lines.insert(last, "import silence" + chr(10))
    return "".join(lines)


def instrument(root=None, dry=False):
    """Insert a `note()` call at the head of every silent handler.

    Purely additive -- no existing statement is touched, so behaviour is unchanged except that
    the failure is now counted. Handlers are rewritten from the bottom of the file upward so
    that earlier line numbers stay valid as lines are inserted.
    """
    root = root or os.path.join(HERE, "src")
    changed = []
    for path in sorted(glob.glob(os.path.join(root, "*.py"))):
        base = os.path.basename(path)
        if base in SKIP_FILES:
            continue
        with open(path, encoding="utf-8") as f:
            original = f.read()
        lines = original.splitlines(keepends=True)
        try:
            tree = ast.parse(original)
        except Exception as exc:
            # SAME RULE AS `_handlers` ABOVE. A file that will not parse is skipped -- correctly,
            # there is nothing safe to rewrite -- but it is also absent from `changed`, so the
            # summary `main()` prints reads identically to "that module had nothing to
            # instrument". Said out loud, in the same shape as the rewrite-would-not-parse
            # report twenty lines below, so an operator running --instrument knows which modules
            # the pass could not reach.
            note("silence.py:instrument-unparseable:" + base)
            print("  !! %s: could not be parsed (%s: %s); left uninstrumented"
                  % (base, type(exc).__name__, str(exc)[:120]))
            continue
        sites = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            # ASK THE BODY, NOT THE HANDLER -- same fix as `_handlers` above, applied here too.
            # This checked `ast.dump(node)`, which serialises the exception type and the bound
            # name along with the body, and its token list omitted "silence" -- so it read
            # `_ = "silence-exempt: ..."` (this project's documented exemption marker,
            # chain.py:141/159 and 48 others) as UNOBSERVED, because the one token that marker
            # is built from was never in the list it was checked against. `audit()` -- which
            # DOES include "silence" and DOES look at the body only -- correctly calls those 50
            # handlers observed; `instrument()` disagreed with its own sibling and would have
            # rewritten every one of them. The `uses_exc` check is copied down for the same
            # reason: a handler that only inspects its bound exception is observed too.
            body = "".join(ast.dump(stmt) for stmt in node.body)
            records = any(t in body for t in ("health", "record", "log", "print", "raise",
                                              "swallow", "silence", "note", "LEDGER"))
            uses_exc = bool(node.name) and any(
                isinstance(n, ast.Name) and n.id == node.name
                for stmt in node.body for n in ast.walk(stmt))
            if records or uses_exc:
                continue
            sites.append(node)
        if not sites:
            continue
        sites.sort(key=lambda n: n.body[0].lineno, reverse=True)
        for node in sites:
            first = node.body[0]
            i = first.lineno - 1
            col = first.col_offset
            call = f'{" " * col}silence.note("{base}:{node.lineno}")\n'
            if first.lineno == node.lineno:
                # `except X: pass` -- one-line suite. Split it so the note has somewhere to go.
                head, _, tail = lines[i].partition(":")
                indent = len(lines[i]) - len(lines[i].lstrip())
                body_col = indent + 4
                lines[i] = (head + ":\n"
                            + " " * body_col + f'silence.note("{base}:{node.lineno}")\n'
                            + " " * body_col + tail.strip() + "\n")
            else:
                lines.insert(i, call)
        src = "".join(lines)
        src = _ensure_import(src)
        try:
            ast.parse(src)
        except SyntaxError as e:
            print(f"  !! {base}: rewrite would not parse ({e}); left alone")
            continue
        if not dry:
            with open(path + ".presilence", "w", encoding="utf-8") as f:
                f.write(original)
            with open(path, "w", encoding="utf-8") as f:
                f.write(src)
        changed.append((base, len(sites)))
    return changed


if __name__ == "__main__":
    sys.exit(main())
