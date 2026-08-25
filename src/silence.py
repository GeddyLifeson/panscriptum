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

Every one of those went through a bare `except Exception: return None` or an equivalent. There
are 45 such handlers in this tree, and that number is the real bug; the fifteen were its output.

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

    __slots__ = ("kind", "detail", "reraise", "failed", "error")

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
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        body = ast.dump(node)
        records = any(t in body for t in ("health", "record", "log", "print", "raise",
                                          "swallow", "silence", "LEDGER"))
        # A handler that re-raises, logs, or carries the exception into its own return value
        # is observed. One that only returns or continues is not -- that is the shape that
        # turned a 404 into "these entities have no page".
        uses_exc = bool(node.name) and node.name in body
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


def replace_retry(tmp, dst, attempts=5):
    """os.replace with a short retry, because on Windows the rename is DENIED while any
    reader holds the target open -- and this project's state files all have readers on their
    own clocks (the dashboard polls records and ASSAYS, standards scans readfeats). One such
    collision took an assay worker down mid-batch (2026-08-23, WinError 5). A brief backoff
    outwaits any honest reader; persistent denial is recorded, never raised -- the caller's
    write lands next round."""
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
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        raise
    return replace_retry(tmp, path)


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
        except Exception:
            continue
        sites = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if any(t in ast.dump(node) for t in ("health", "record", "log", "print",
                                                 "raise", "swallow", "note", "LEDGER")):
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
