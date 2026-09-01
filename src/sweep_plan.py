"""Partition EVERY module in `src/` into balanced audit batches, and record what got covered.

Owner ruling 2026-08-25: *"the first thing that should be done after what's immediate is a full
in-depth comprehensive sweep of every line of code across every module ... make it such that
every sweep is as in-depth and comprehensive as possible every time until nothing bad is
reported back, just that things are being waited on."*

WHY THIS FILE EXISTS AT ALL. The maintenance pass used to audit by ROTATION -- "take the top two
never-audited files" -- with the rotation state kept in prose in `NEXT_STEPS.md`. That is a cap
wearing a schedule's clothing, and it is the exact shape Hard Rule 0 forbids: it returned a
smaller universe (2 modules) in the same shape as the real one (94), it never failed, and the
handoff read like a completed audit either way. At two modules a run against 94 modules, a given
file was re-read about twice a year, so "never audited" was the normal state of most of the tree.

THE RULE THIS ENFORCES: every module, every sweep. Not a sample, not a rotation, not the biggest
N. `batches()` exists only to make that survivable inside finite agent contexts -- it splits the
work, it never drops any of it, and `missing()` is the check that proves nothing was dropped.

    python src/sweep_plan.py --batches 16     # the plan, as JSON
    python src/sweep_plan.py --coverage       # what the last sweep actually covered
"""

import argparse
import glob
import json
import os
import sys as _sys
import threading
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "src")
COVERAGE = os.path.join(HERE, "state", "SWEEP_COVERAGE.json")
SHARDS = os.path.join(HERE, "state", "sweep_shards")


def _src_py_files():
    """Every `.py` file under src/, SUBDIRECTORIES INCLUDED. -> [(label, full path)].

    THE GLOB SAID "EVERY MODULE IN src/" AND MEANT "every module in the TOP LEVEL of src/"
    (order f42c55355431, run #37). `glob(SRC + "/*.py")` does not descend, and `src/deprecated/`
    holds `catalogue_local.py` (280 lines), so that file was invisible to every sweep ever run
    here -- never batched, never import-checked, never read by overwatch's model.

    The structural half is why it mattered more than one skipped file: `missing()` is
    `modules()` minus `covered_by(run)`, so a module `modules()` CANNOT SEE is one `missing()`
    can never name. The completeness check could not notice this class of gap by construction,
    which is the "a check that cannot fail looks exactly like a check that passed" shape this
    project keeps finding. Deleting `src/deprecated/` was the order's other suggested remedy and
    is deliberately NOT taken: its README says it is kept as a record of a failure mode, and two
    of drill.py's nets reason about a module living there. A directory kept on purpose is a
    directory the sweep has to read.

    The label is the path relative to src/ with forward slashes, matching
    `drill.py:_src_py_files`. For every top-level file that is exactly the basename it always
    was, so no recorded coverage key changes meaning; only `deprecated/catalogue_local.py` is
    new. `__pycache__` is skipped because it holds no source.
    """
    out = []
    for root, dirs, files in os.walk(SRC):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in sorted(files):
            if f.endswith(".py"):
                full = os.path.join(root, f)
                out.append((os.path.relpath(full, SRC).replace(os.sep, "/"), full))
    return sorted(out)


def modules():
    """Every module in src/, newest-largest first. NO exclusions, deliberately.

    Not even this file, and not `verify_math.py` because it is "only tests" -- a check that is
    wrong is worse than a missing one, since it reports green forever. If a module is genuinely
    not worth auditing, that is an argument for deleting it, not for skipping it.

    "In src/" means UNDER src/, subdirectories included -- see `_src_py_files` for why that
    sentence had to be made true rather than merely written down.
    """
    out = []
    for label, p in _src_py_files():
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                n = sum(1 for _ in f)
        except Exception:
            # NOT a zero-line module. An unreadable file used to fall through to `n = 0` with
            # no note, which sorts it last, packs it into a bin as free weight, and reads in
            # the plan exactly like an empty stub -- a file silently dropped out of a sweep
            # whose entire purpose is that nothing is dropped. Recorded, and marked so the
            # plan itself carries the fault. (Found by the sweep auditing this very file,
            # hours after it was written. 2026-08-25.)
            try:
                import silence
                silence.note("sweep_plan.py:module-lines")
            except Exception:
                pass
            out.append({"module": label, "lines": 0, "unreadable": True})
            continue
        out.append({"module": label, "lines": n})
    return sorted(out, key=lambda m: -m["lines"])


def batches(n=16):
    """Greedy longest-first bin packing into `n` roughly equal-line batches.

    Longest-first matters: dropping the 3,459-line file into whichever bin is emptiest at the
    end produces one batch nobody can actually read. Packed largest-first, the spread across
    bins stays tight enough that every agent gets a context it can hold.
    """
    n = max(1, int(n))
    bins = [{"batch": i + 1, "lines": 0, "modules": []} for i in range(n)]
    for m in modules():
        b = min(bins, key=lambda b: b["lines"])
        b["modules"].append(m["module"])
        b["lines"] += m["lines"]
    return [b for b in bins if b["modules"]]


_RECORD_LOCK = threading.Lock()


def _shard_path(run, batch):
    """A filename no other writer can collide with: run + batch + pid.

    The batch id alone is not enough — an agent that is retried, or a batch re-run by hand,
    would land on the same name as its predecessor mid-write.
    """
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in "%s.%s" % (run, batch))
    return os.path.join(SHARDS, "%s.%d.json" % (safe, os.getpid()))


def _read_shards():
    """Every shard on disk, merged newest-wins. Unreadable shards are NOTED, never skipped
    in silence — a shard that will not parse is a batch whose coverage we cannot prove."""
    out = {}
    try:
        paths = sorted(glob.glob(os.path.join(SHARDS, "*.json")))
    except Exception:
        try:
            import silence
            silence.note("sweep_plan.py:shards-dir-unreadable")
        except Exception:
            pass
        return out
    for p in paths:
        try:
            with open(p, encoding="utf-8") as f:
                rec = json.load(f)
        except Exception:
            try:
                import silence
                silence.note("sweep_plan.py:shard-unreadable")
            except Exception:
                pass
            continue
        run = rec.get("run")
        at = rec.get("at") or 0
        for m in (rec.get("modules") or []):
            prev = out.get(m)
            if prev is None or (at or 0) >= (prev.get("at") or 0):
                out[m] = {"run": run, "at": at}
    return out


def record(run, covered, batch=None):
    """Stamp which modules a sweep actually read. `covered` is an iterable of basenames.

    WRITTEN AS A PER-BATCH SHARD, because the whole point of this file is that sixteen batches
    run AT ONCE — and, since run #28, each one in ITS OWN PROCESS. The first version did an
    unguarded read-modify-write and lost the loser's modules; the second serialised it behind a
    `threading.Lock`, which is the right lock for the wrong topology: a threading lock is not
    held across processes, so sixteen subagents each running `python -c "sweep_plan.record(...)"`
    contend exactly as if there were no lock at all. Two of them interleaving read-modify-write
    still drops one batch's modules, and `missing()` would then report a gap that never
    happened — or, if the survivor happened to be the fuller file, hide one that did.

    So there is no shared mutable file on the write path any more. Each caller writes its OWN
    file, named for its run/batch/pid, and `missing()` merges them at read time. Concurrent
    writers cannot collide because they never touch the same path. The lock is kept only for
    the best-effort fold into the aggregate `SWEEP_COVERAGE.json`, which is now a CONVENIENCE
    VIEW for `--coverage` — nothing draws a conclusion from it that the shards do not support.
    (Race found by the sweep auditing this very file; topology bug found the run after, by the
    sweep auditing it again. 2026-08-25.)
    """
    covered = list(covered)
    now = time.time()
    try:
        os.makedirs(SHARDS, exist_ok=True)
        p = _shard_path(run, batch if batch is not None else "x")
        tmp = "%s.tmp" % p
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"run": run, "batch": batch, "at": now, "modules": covered}, f, indent=1)
        # replace_retry, not a bare os.replace -- the other two landings in this file already go
        # through it. `_read_shards()` in a sibling process globs and opens this very directory
        # on its own clock, and on Windows the rename is DENIED while any reader holds the
        # target. Today `_shard_path` embeds run+batch+pid so the name is usually brand new; it
        # stops being new the moment a caller retries `record()` for the same run/batch in the
        # same process, which is exactly when losing the write costs a batch its coverage.
        #
        # GATED, and this is the load-bearing write in this function -- not the aggregate fold
        # below it. The SHARDS are what `covered_by()` and therefore `missing()` read, so this
        # file IS this batch's evidence that it read what it read; `SWEEP_COVERAGE.json` is the
        # convenience view the docstring above already calls best-effort. The comment directly
        # above names the case (a retried `record()` for the same run/batch in one process
        # reuses the name, "which is exactly when losing the write costs a batch its coverage")
        # and the code then discarded the verdict that reports it. A lost shard does not make
        # an incomplete sweep look complete -- `covered_by` unions, so the error is toward
        # reporting a gap -- but it makes a batch that DID its work unprovable, and the sweep's
        # completeness check then blames an agent that read every line. Said out loud so the
        # caller can re-record instead of arguing with a phantom gap later.
        import silence
        if not silence.replace_retry(tmp, p):
            silence.note("sweep_plan.py:shard-write-denied")
            print("sweep_plan: coverage shard for run=%s batch=%s did NOT land (replace "
                  "refused). This batch's %d module(s) are unprovable and `--missing %s` will "
                  "name them; call record() again."
                  % (run, batch, len(covered), run), file=_sys.stderr)
    except Exception:
        try:
            import silence
            silence.note("sweep_plan.py:shard-write")
        except Exception:
            pass
    with _RECORD_LOCK:
        data = _read_shards()
        try:
            with open(COVERAGE, encoding="utf-8") as f:
                old = json.load(f)
            if isinstance(old, dict):
                for m, r in old.items():
                    data.setdefault(m, r)
        except Exception:
            try:
                import silence
                silence.note("sweep_plan.py:record-aggregate-merge-failed")
            except Exception:
                pass
        # VERDICT DELIBERATELY UNUSED HERE, and this one was worth checking rather than gating
        # on the strength of the filename. `SWEEP_COVERAGE.json` LOOKS like the proof that a
        # comprehensive sweep covered every module, and it is not: `covered_by()` -- which
        # `missing()` and therefore the completeness check are built on -- reads the SHARDS,
        # and consults this file only as an additive fallback for coverage recorded before
        # shards existed (`out.add(m)`, never a removal). So a refused write here cannot make
        # an incomplete sweep look complete. It can only make a complete one look short, in
        # `--coverage`'s human-facing count, which is the fail-safe direction.
        #
        # It is also SELF-HEALING, which is the other half of the argument. This file is folded
        # fresh from `_read_shards()` plus whatever survives on disk on EVERY `record()` call,
        # so a refused replace leaves the previous file intact and the next batch's record
        # rebuilds the same content over it. Nothing is lost that anything can lose, and
        # `write_json` -> `replace_retry` already puts the denial in state/failures.json. The
        # shard write above is where this function's verdict actually matters; that one is
        # gated. Do not "fix" this by aborting a sweep over a derived view.
        try:
            import silence
            silence.write_json(COVERAGE, data, indent=1, sort_keys=True)
        except Exception:
            try:
                silence.note("sweep_plan.py:record-write-json-fallback")
            except Exception:
                pass
            # AND THE FALLBACK MUST NOT BE THE THING THAT RAISES. This was a bare `os.replace`
            # sitting inside an `except` body with nothing around it, so the Windows denial the
            # rest of this module routes through `replace_retry` for would escape `record()`
            # into a sweep agent -- the one path where a coverage write, which is meant to cost
            # nothing, takes the batch down. Same helper as every other landing in this file.
            # Its verdict is unused for the reason given in the block above: this is the derived
            # view, it is rebuilt from the shards on the next `record()`, and `replace_retry`
            # already records a denial. The authoritative write is the shard, and that is gated.
            #
            # AND THE PROMISE ABOVE WAS STILL HALF TRUE UNTIL ORDER 6794cb447987. Only the
            # LANDING was guarded; the `open` and the `json.dump` sat bare, and they are the
            # likelier raiser of the two. `silence.write_json` re-raises a failed dump
            # (silence.py:515-517, `except Exception: _discard_tmp(tmp); raise`), so the very
            # condition that sends control into this fallback is usually the same condition that
            # breaks it two lines later -- an unserialisable `data`, a full disk, a read-only
            # state/ -- and the exception escaped `record()` into the sweep agent anyway. The
            # whole fallback is inside the try now, and the temp is discarded on the way out so
            # a refused landing does not leave litter beside COVERAGE, exactly as `write_json`
            # discards its own.
            tmp = "%s.%d.tmp" % (COVERAGE, os.getpid())
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=1, sort_keys=True)
                import silence as _s
                _s.replace_retry(tmp, COVERAGE)
            except Exception:
                try:
                    silence.note("sweep_plan.py:record-fallback-write-failed")
                except Exception:
                    pass
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                # NOTED, not swallowed. A refused unlink leaves a pid-qualified scratch file
                # beside COVERAGE, and one per failing run accumulates -- the same litter
                # `silence.write_json` cleans up after itself and `foreman.py` notes as
                # `for-owner-tmp-not-removed`. This was the one handler in this module that
                # swallowed in silence (checks_L1 caught it); the note is what makes the
                # accumulation visible instead of something found later by `ls`.
                try:
                    import silence
                    silence.note("sweep_plan.py:record-fallback-tmp-not-removed")
                except Exception:
                    pass
        return data


def coverage_map():
    """The authoritative view: shards first, the aggregate file only where a shard is absent.

    NEWEST-WINS, because this answers "when was module X last audited, and by which run?" --
    a question with exactly one right answer. It is the wrong instrument for `missing()`; see
    there.
    """
    data = _read_shards()
    try:
        with open(COVERAGE, encoding="utf-8") as f:
            old = json.load(f)
        if isinstance(old, dict):
            for m, r in old.items():
                if isinstance(r, dict):
                    data.setdefault(m, r)
    except Exception:
        try:
            import silence
            silence.note("sweep_plan.py:coverage-map-aggregate-unreadable")
        except Exception:
            pass
    return data


def covered_by(run):
    """The set of modules ANY shard records `run` as having read.

    Deliberately NOT derived from `coverage_map()`. That map is newest-wins across all runs, so
    asking it "did run29 cover X?" really asks "was run29 the LAST run to cover X?" -- a
    different question with a different answer the moment a second run records the same module
    with a later stamp. Shards are never pruned, so those two questions diverge permanently,
    and the divergence is invisible: `missing()` would name a module the agent demonstrably
    read, and the sweep's completeness proof would report a gap that did not happen.

    A membership question deserves a membership answer. (Found by the sweep auditing this very
    file, in the same run that introduced the shards. 2026-08-25, run #29, batch 08.)
    """
    want = str(run)
    out = set()
    try:
        paths = sorted(glob.glob(os.path.join(SHARDS, "*.json")))
    except Exception:
        # THE SHARPEST OF THIS FILE'S SILENT HANDLERS. A swallowed glob error here used to
        # return an empty set with no record, which reads to `missing()` exactly like "this
        # run covered nothing" -- so a completeness proof was silently indistinguishable from
        # a directory the OS could not list. Order 97880e5e40e1.
        try:
            import silence
            silence.note("sweep_plan.py:covered-by-glob-failed")
        except Exception:
            pass
        paths = []
    for p in paths:
        try:
            with open(p, encoding="utf-8") as f:
                rec = json.load(f)
        except Exception:
            try:
                import silence
                silence.note("sweep_plan.py:shard-unreadable")
            except Exception:
                pass
            continue
        if str(rec.get("run")) == want:
            for m in (rec.get("modules") or []):
                out.add(m)
    # The aggregate file is a fallback for a coverage record written before shards existed.
    try:
        with open(COVERAGE, encoding="utf-8") as f:
            old = json.load(f)
        if isinstance(old, dict):
            for m, r in old.items():
                if isinstance(r, dict) and str(r.get("run")) == want:
                    out.add(m)
    except Exception:
        try:
            import silence
            silence.note("sweep_plan.py:covered-by-aggregate-unreadable")
        except Exception:
            pass
    return out


def latest_run():
    """The run label of the most recently written shard, or None if nothing has ever swept.

    THE COMPLETENESS CHECK MUST NOT NAME A RUN IN A LITERAL. `verify_math`'s "the live sweep
    proves its own completeness" asked `missing("run29")`, hardcoded -- so from run #30 onward
    it was answering a question about a sweep that had already finished, and no later sweep,
    however complete or however skipped, could move it. It is the THIRD spelling of the same
    defect in three consecutive runs: #28 found `record()` losing an update, #29 found
    `missing()` asking "was run N the LAST to read X?" instead of "did run N read X?", and this
    is #31's -- the instrument frozen on a past run. Lesson 25 keeps being right: the sweep
    audits the sweep, and that is where the best finding keeps being.

    Returns None rather than a guess when there is no evidence, so the caller can FAIL CLOSED
    instead of proving the completeness of a sweep that never happened.
    """
    newest = None
    try:
        paths = glob.glob(os.path.join(SHARDS, "*.json"))
    except Exception:
        try:
            import silence
            silence.note("sweep_plan.py:latest-run-glob-failed")
        except Exception:
            pass
        paths = []
    for p in paths:
        try:
            with open(p, encoding="utf-8") as f:
                rec = json.load(f)
        except Exception:
            try:
                import silence
                silence.note("sweep_plan.py:shard-unreadable")
            except Exception:
                pass
            continue
        at = rec.get("at")
        run = rec.get("run")
        if run is None or not isinstance(at, (int, float)):
            continue
        if newest is None or at > newest[0]:
            newest = (at, str(run))
    return newest[1] if newest else None


def missing(run):
    """Modules NOT covered by `run` — the proof that a sweep was complete, or the list of what
    it silently skipped. A sweep that cannot answer this is a sweep nobody can trust."""
    seen = covered_by(run)
    return [m["module"] for m in modules() if m["module"] not in seen]


def _assignment(obj):
    """Normalise a dispatched assignment to {batch id (str): [module, ...]}.

    Accepts BOTH shapes so the check can be run against whatever the coordinator has to hand:
    the exact JSON `--batches` emits (a list of {"batch":, "modules":}) and a plain
    {batch: [modules]} map written out by hand. Refusing one of them would just move the
    hand-transcription step somewhere else, which is the fault being closed.
    """
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, dict):                       # {"1": {"modules": [...]}}
                v = v.get("modules") or []
            out[str(k)] = [str(x) for x in (v or [])]
    elif isinstance(obj, list):
        for row in obj:
            if isinstance(row, dict):
                out[str(row.get("batch"))] = [str(x) for x in (row.get("modules") or [])]
    return out


def check_briefs(assigned, n=16):
    """Diff what was DISPATCHED against `batches(n)`. -> a report dict; empty faults means clean.

    THE COORDINATOR'S OWN BRIEFS LOST TWO MODULES AND ONLY `missing()` NOTICED (order
    34cf5b961af1). `batches(16)` put nine modules in batch 08 and nine in batch 15; the briefs
    written from that plan listed eight each, dropping `compress_store.py` and `lognames.py`.
    Both agents read and recorded exactly what they were given, correctly, and both reports read
    as complete because they WERE complete against their briefs. Nothing else in the pipeline
    could see the gap -- not the agent summaries, not the audit files, not the order counts --
    because the transcription step is a hand-copy of machine-generated data and nothing compared
    the copy with the original. `missing()` caught it, but only AFTER the sweep had run.

    This is that comparison, available BEFORE dispatch, so the check costs a command instead of
    a shift. `dropped` is the fault that matters: a module the plan assigned to a batch that the
    batch's brief does not mention. `uncovered` is the same question asked of the whole tree, and
    is the one to read if the batching was reorganised deliberately -- a module may legitimately
    move between batches, but it may never fall out of all of them.

    -> {"planned_batches", "dispatched_batches", "dropped": {batch: [...]},
        "added": {batch: [...]}, "undispatched": [batch, ...], "uncovered": [...], "clean": bool}
    NO CAPS on any list here: this is read to act on, and a truncated one is the fault it hunts.
    """
    plan = {str(b["batch"]): list(b["modules"]) for b in batches(n)}
    got = _assignment(assigned)
    dropped, added = {}, {}
    for bid, mods in plan.items():
        if bid not in got:
            continue                                      # counted under `undispatched` below
        lost = [m for m in mods if m not in got[bid]]
        extra = [m for m in got[bid] if m not in mods]
        if lost:
            dropped[bid] = lost
        if extra:
            added[bid] = extra
    everything = set()
    for mods in got.values():
        everything.update(mods)
    return {
        "planned_batches": len(plan),
        "dispatched_batches": len(got),
        "dropped": dropped,
        "added": added,
        "undispatched": sorted(b for b in plan if b not in got),
        # THE BOTTOM LINE, and it does not care which batch a module ended up in.
        "uncovered": [m["module"] for m in modules() if m["module"] not in everything],
        "clean": not dropped and not [m["module"] for m in modules()
                                      if m["module"] not in everything],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--batches", type=int, default=0, help="emit N balanced batches as JSON")
    ap.add_argument("--coverage", action="store_true", help="show the last recorded coverage")
    ap.add_argument("--missing", help="list modules not covered by the given run id")
    ap.add_argument("--check-briefs", metavar="FILE",
                    help="diff the dispatched module lists in FILE against --batches N, "
                         "BEFORE dispatch (see check_briefs)")
    a = ap.parse_args()
    if a.batches:
        plan = batches(a.batches)
        print(json.dumps(plan, indent=1))
        print("# %d modules, %d lines, %d batches"
              % (sum(len(b["modules"]) for b in plan),
                 sum(b["lines"] for b in plan), len(plan)))
    elif a.check_briefs:
        with open(a.check_briefs, encoding="utf-8") as f:
            rep = check_briefs(json.load(f), a.batches or 16)
        print("planned %d batch(es), dispatched %d"
              % (rep["planned_batches"], rep["dispatched_batches"]))
        for bid, mods in sorted(rep["dropped"].items()):
            print("DROPPED   batch %s is missing: %s" % (bid, ", ".join(mods)))
        for bid, mods in sorted(rep["added"].items()):
            print("added     batch %s also lists: %s" % (bid, ", ".join(mods)))
        if rep["undispatched"]:
            print("NOT DISPATCHED AT ALL: batch(es) %s" % ", ".join(rep["undispatched"]))
        if rep["uncovered"]:
            print("UNCOVERED BY ANY BRIEF (%d): %s"
                  % (len(rep["uncovered"]), ", ".join(rep["uncovered"])))
        print("clean" if rep["clean"] else "NOT CLEAN -- fix the briefs before dispatch")
        # A NON-ZERO RC, so this can gate a dispatch script rather than only inform a reader.
        return 0 if rep["clean"] else 1
    elif a.missing:
        miss = missing(a.missing)
        print("\n".join(miss) if miss else "nothing missing -- the sweep was complete")
    elif a.coverage:
        try:
            with open(COVERAGE, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            try:
                import silence
                silence.note("sweep_plan.py:coverage-cli-read-failed")
            except Exception:
                pass
            data = {}
        runs = {}
        for m, r in data.items():
            runs.setdefault(str(r.get("run")), []).append(m)
        for r, ms in sorted(runs.items()):
            print("%-28s %d module(s)" % (r, len(ms)))
        print("%d module(s) in src/ total" % len(modules()))
    else:
        ms = modules()
        print("%d modules, %d lines" % (len(ms), sum(m["lines"] for m in ms)))
    return 0


if __name__ == "__main__":
    # THE RC IS CARRIED OUT OF main(), so `--check-briefs` can gate a dispatch. Every other
    # path returns 0 exactly as before.
    raise SystemExit(main())
