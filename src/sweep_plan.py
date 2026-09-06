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
import hashlib
import json
import os
import sys as _sys
import threading
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "src")
COVERAGE = os.path.join(HERE, "state", "SWEEP_COVERAGE.json")
SHARDS = os.path.join(HERE, "state", "sweep_shards")
# One frozen batch plan per run, so a batch number names the same modules all run long. See
# `freeze_plan`. Its OWN directory rather than a loose state/sweep<N>_plan.json, because that
# convention was an operator shell redirect and estate graded the result corrupt -- see main().
PLANS = os.path.join(HERE, "state", "sweep_plan")


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


def batches(n=16, snapshot=None):
    """Greedy longest-first bin packing into `n` roughly equal-line batches.

    Longest-first matters: dropping the 3,459-line file into whichever bin is emptiest at the
    end produces one batch nobody can actually read. Packed largest-first, the spread across
    bins stays tight enough that every agent gets a context it can hold.

    `snapshot` IS THE FROZEN TABLE, and it is why a batch number can mean one thing for a whole
    run (order 4d44a6363245). Packing is a pure function of the module/line table it is given;
    given `modules()` it is a pure function of the LIVE line counts, so a one-line edit to any
    module re-runs the packing and reshuffles every bin. Measured on run39: `batches(16)[10]`
    returned nine modules at dispatch and eight different ones ninety minutes later, six having
    moved to other bins, while eight files in src/ were edited in that window -- which is the
    NORMAL condition of the tree during a sweep, because the standing set runs
    `foreman.py --go --patch` and its model lane edits src/ unattended.

    Pass the table `freeze_plan()` stored and the plan is reproducible; pass nothing and the
    behaviour is exactly what it always was. See `freeze_plan` for which of those is right.
    """
    n = max(1, int(n))
    bins = [{"batch": i + 1, "lines": 0, "modules": [], "unreadable": []} for i in range(n)]
    for m in (modules() if snapshot is None else list(snapshot)):
        b = min(bins, key=lambda b: b["lines"])
        b["modules"].append(m["module"])
        b["lines"] += m["lines"]
        if m.get("unreadable"):
            # Carry the flag `modules()` recorded THROUGH to the plan a coordinator actually
            # dispatches (order 32b2d67eebd4). `modules()`'s own comment already says intent --
            # "Recorded, and marked so the plan itself carries the fault" -- but this function
            # kept only `m["module"]`, so an unreadable file packed into a bin at lines: 0 and
            # read in the emitted plan exactly like an empty stub. `b["modules"]` stays a plain
            # list of labels (check_briefs() and the --batches JSON both depend on that shape);
            # this is an additive key so the agent that receives the batch can see which of its
            # modules could not be sized and report it rather than silently skip a stub.
            b["unreadable"].append(m["module"])
    return [b for b in bins if b["modules"]]


def _table_digest(table):
    """A short digest of a module/line table, so two plans can be told apart. -> str."""
    payload = json.dumps([[m.get("module"), m.get("lines", 0), bool(m.get("unreadable"))]
                          for m in table], sort_keys=True)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]


def plan_path(run):
    """Where a run's frozen plan lives. One file per run, named for the run."""
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in str(run))
    return os.path.join(PLANS, "%s.json" % safe)


def frozen_plan(run):
    """The plan `run` was dispatched from, or None if it was never frozen.

    Absent is honestly absent and returns None; UNREADABLE is noted rather than silently
    treated as absent, because falling back to a recomputed plan is precisely the reshuffle
    this exists to prevent, and doing it in silence would hide the one condition that matters.
    """
    p = plan_path(run)
    # ABSENT IS ASKED, NOT CAUGHT, so there is no silent handler here to exempt.
    #
    # This was an `except FileNotFoundError: return None`, and the 2026-09-05 run first tried to
    # settle it by writing a `silence-exempt:` comment on that handler. That was wrong twice
    # over, and the battery caught it within the hour (checks_L1
    # check_sweep_plan_data_reads_are_noted went red): `silence.audit()` counts a handler as
    # SILENT unless it can see a note beside it, and the exemption marker this project honours
    # elsewhere is not what that check reads. More importantly the marker was arguing the wrong
    # thing. A missing plan file is not a tolerated FAILURE that deserves an exemption -- it is
    # the ordinary state of a run nobody has frozen yet, which is a QUESTION with an answer, and
    # the honest shape for a question is to ask it rather than to catch the refusal.
    #
    # Asking also keeps the race honest: if the file vanishes between this check and the open
    # below, that FileNotFoundError now falls into the UNREADABLE arm and IS noted -- which is
    # right, because a plan file disappearing out from under a live run is exactly the condition
    # worth hearing about, and the old handler swallowed it identically to an ordinary absence.
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            rec = json.load(f)
    except Exception:
        try:
            import silence
            silence.note("sweep_plan.py:frozen-plan-unreadable")
        except Exception:
            pass
        print("sweep_plan: %s EXISTS and could not be read, so the frozen plan for run=%s is "
              "unavailable. Recomputing would reshuffle the batches this run was dispatched "
              "from; fix or remove the file instead." % (p, run), file=_sys.stderr)
        return None
    return rec if isinstance(rec, dict) else None


def freeze_plan(run, n=16):
    """Compute the plan for `run` ONCE and land it. -> the frozen record.

    THE BATCH NUMBER MUST MEAN ONE THING FOR A WHOLE RUN (order 4d44a6343245's sibling,
    4d44a6363245). `batches()` packs the live line counts, so during a sweep -- which is exactly
    when src/ is being edited, by ten agents and by foreman's unattended patch lane -- two
    agents asking for "batch 11" minutes apart get different module sets. Measured on run39: six
    of nine modules moved out of batch 11 in ninety minutes, and five modules then labelled
    "batch 11" were never in that agent's brief. Work is duplicated where the sets overlap, and
    a module can fall out of every dispatched brief if the coordinator dispatches at t0 and any
    agent recomputes later.

    WHAT IS FROZEN AND WHAT IS DELIBERATELY NOT. The PLAN is frozen: which modules a batch
    number names, for the life of the run. `missing()` and `check_briefs`'s `uncovered` stay on
    the LIVE `modules()`, and that is not an oversight -- it is the fail-safe direction. A
    module ADDED to src/ mid-run has been read by nobody, and freezing the completeness proof
    would make it invisible. So the plan answers "who was asked to read what" and the live tree
    answers "what is there to read"; freezing the first without the second is the whole fix.

    IDEMPOTENT: an existing frozen plan is RETURNED, never recomputed and never overwritten.
    Re-running the dispatch command cannot silently re-shuffle a run that is already underway.

    A REFUSED LANDING IS REPORTED, NOT ASSUMED. The record carries `frozen: False` when the
    write did not land, because a plan nobody can read back is not a frozen plan and the caller
    must not dispatch from it believing otherwise.
    """
    existing = frozen_plan(run)
    if existing is not None:
        return existing
    table = modules()
    rec = {"run": str(run), "at": time.time(), "n": max(1, int(n)),
           "src_table_digest": _table_digest(table),
           "modules": table, "batches": batches(n, snapshot=table), "frozen": True}
    try:
        import silence
        os.makedirs(PLANS, exist_ok=True)
        if not silence.write_json(plan_path(run), rec, indent=1):
            rec["frozen"] = False
            silence.note("sweep_plan.py:plan-freeze-denied")
            print("sweep_plan: the plan for run=%s did NOT land at %s (replace refused). It is "
                  "NOT frozen: another process asking for this run's plan will recompute it "
                  "from the live tree and may get different batches. Re-run before dispatching."
                  % (run, plan_path(run)), file=_sys.stderr)
    except Exception as exc:
        rec["frozen"] = False
        try:
            import silence
            silence.note("sweep_plan.py:plan-freeze-failed")
        except Exception:
            pass
        print("sweep_plan: the plan for run=%s could not be written (%s: %s). It is NOT frozen."
              % (run, type(exc).__name__, exc), file=_sys.stderr)
    return rec


def known_modules():
    """The exact vocabulary `record()` accepts: every label `batches()` emits. -> set.

    One function, asked by both sides, so the spelling a batch is GIVEN and the spelling its
    coverage is CHECKED against cannot be two different things.
    """
    return {m["module"] for m in modules()}


def normalise_module(name, known=None):
    """One recorded coverage name -> the label this module itself emits, or None if unknown.

    THE PROOF THAT A SWEEP COVERED EVERYTHING USED TO ACCEPT ANY STRING (order f307490add1e).
    `record()` stored whatever it was handed. On run41, fifteen batches that all genuinely read
    their modules in full sent THREE different spellings from three callers -- `drill.py` (what
    `batches()` emits, and the only form `missing()` matches), `src/publish.py` (path-prefixed),
    and `foreman` (extension stripped). `missing()` then named 26 of 116 modules as NEVER READ
    when every one of them had been read line by line, which costs a whole re-audit; one batch
    noticed and re-recorded, four did not, and nothing told them.

    THE OTHER DIRECTION IS THE ONE THAT MATTERS, and it is why this refuses rather than guesses.
    Shard run41.7 recorded `catalogue_local.py`, a name this module does not know -- it spells
    that file `deprecated/catalogue_local.py`. That entry sat in the coverage record matching
    nothing at all, and no mechanism anywhere noticed. A claim that matches no module is not
    coverage, and a check that cannot tell a claim from a reading is a check that cannot fail.

    NORMALISATION IS EXACT, NEVER APPROXIMATE. A `src/` prefix is stripped, a missing `.py` is
    added, and a bare basename resolves to a subdirectory label ONLY when exactly one known
    module has that basename. Two modules sharing a basename make the name ambiguous and it is
    refused -- picking one would be the invented coverage this whole function exists to stop.
    """
    known = known_modules() if known is None else known
    raw = str(name or "").strip().replace("\\", "/")
    while raw.startswith("./"):
        raw = raw[2:]
    if not raw:
        return None
    if raw in known:
        return raw
    cand = raw[4:] if raw.startswith("src/") else raw
    if cand in known:
        return cand
    if not cand.endswith(".py"):
        cand += ".py"
        if cand in known:
            return cand
    base = cand.rsplit("/", 1)[-1]
    hits = sorted(k for k in known if k.rsplit("/", 1)[-1] == base)
    if len(hits) == 1:
        return hits[0]
    return None


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

    AND EVERY NAME IS NORMALISED AND VALIDATED BEFORE IT COUNTS (order f307490add1e). See
    `normalise_module` for the measurement. A name this module can resolve is stored in
    `modules`, which is the field `covered_by()` -- and therefore `missing()`, and therefore the
    whole completeness proof -- reads. A name that resolves to NO module is stored in `unknown`,
    where nothing counts it as coverage, and is announced on stderr and to `silence`. It is kept
    rather than dropped because the fact that a batch claimed it is itself the finding: the point
    is not to tidy the record but to make a false claim VISIBLE, which is what `unknown_claims()`
    and `--missing` now report.

    IT DOES NOT RAISE, deliberately. `record()` is called by sixteen batch agents at the end of
    work already done; taking one of them down over a misspelling would discard the valid part
    of its claim as well, which is the opposite of what this is for. The unreadable-name half is
    refused; the readable half still lands.
    """
    _known = known_modules()
    _accepted, _unknown = [], []
    for _name in list(covered):
        _lbl = normalise_module(_name, _known)
        if _lbl is None:
            _unknown.append(str(_name))
        elif _lbl not in _accepted:
            _accepted.append(_lbl)
    if _unknown:
        print("sweep_plan: run=%s batch=%s recorded %d name(s) matching NO module in src/: %s. "
              "They are NOT counted as coverage and are kept under `unknown` in the shard. A "
              "coverage claim that names nothing is not a reading; check the spelling against "
              "`python src/sweep_plan.py --batches 16` and re-record."
              % (run, batch, len(_unknown), ", ".join(_unknown)), file=_sys.stderr)
        try:
            import silence
            silence.note("sweep_plan.py:coverage-name-unknown")
        except Exception:
            pass
    covered = _accepted
    now = time.time()
    try:
        os.makedirs(SHARDS, exist_ok=True)
        p = _shard_path(run, batch if batch is not None else "x")
        tmp = "%s.tmp" % p
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"run": run, "batch": batch, "at": now, "modules": covered,
                       "unknown": _unknown}, f, indent=1)
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
            # Mirror the COVERAGE fallback below: a refused replace leaves the temp on disk,
            # and `_shard_path` embeds run+batch+pid so a denied record() leaves a UNIQUELY
            # NAMED file each time rather than overwriting one -- pure litter in
            # state/sweep_shards/, never read as a shard (every reader globs `*.json`), but it
            # accumulates. NOTED, not swallowed, same as `record-fallback-tmp-not-removed`.
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                silence.note("sweep_plan.py:shard-tmp-not-removed")
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


def unknown_claims(run=None):
    """Coverage names a sweep recorded that match NO module in src/. -> [(run, batch, name)].

    THE FALSIFIER (order f307490add1e). `missing()` answers "which modules went unread", and it
    could never answer "did a batch claim something that is not a module": an unresolvable name
    was stored beside the real ones and matched nothing for ever, so a batch that read nothing
    and recorded a plausible-looking name was indistinguishable from one that read everything.
    `record()` now refuses such a name as coverage and keeps it under `unknown`; this is where
    that gets read. Reported alongside `--missing`, because the two together are the whole
    proof -- what was not read, and what was claimed but is not a thing.

    `run=None` asks the question of every shard on disk. NO CAP: every claim is returned.
    """
    want = None if run is None else str(run)
    out = []
    try:
        paths = sorted(glob.glob(os.path.join(SHARDS, "*.json")))
    except Exception:
        try:
            import silence
            silence.note("sweep_plan.py:unknown-claims-glob-failed")
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
        if want is not None and str(rec.get("run")) != want:
            continue
        for name in (rec.get("unknown") or []):
            out.append((str(rec.get("run")), str(rec.get("batch")), str(name)))
    # AND THE SHARDS WRITTEN BEFORE THIS EXISTED ARE STILL ASKED. They carry no `unknown` key,
    # so an unresolvable name recorded then is sitting in `modules` where nothing has ever
    # looked at it. Re-checking against the live module set is the only way that history
    # becomes visible; it costs one pass over names already read.
    known = known_modules()
    for p in paths:
        try:
            with open(p, encoding="utf-8") as f:
                rec = json.load(f)
        except Exception:
            # NOT SILENT. This loop re-checks recorded coverage shards, and an unreadable shard
            # is the one case where "nothing to report" and "could not look" are the same shape
            # -- which is precisely the defect this whole module was hardened against, since a
            # shard nobody could read would quietly shrink the set of claims being falsified.
            silence.note("sweep_plan.py:shard-unreadable")
            continue
        if want is not None and str(rec.get("run")) != want:
            continue
        if "unknown" in rec:
            continue
        for name in (rec.get("modules") or []):
            if str(name) not in known:
                out.append((str(rec.get("run")), str(rec.get("batch")), str(name)))
    return sorted(set(out))


# `latest_run()` (the run label of the most recently written shard) was REMOVED here (order
# 03da766af24d). It was written as the fix for "the completeness check must not name a run in
# a literal" but was superseded before it gained a caller: `latest_run` has no notion of a run
# being OVER, so it goes red the moment a sweep records its first batch, and order b18acbb35760
# replaced it in verify_math.py with a finished-run rule (a shard for every planned batch, or
# 3h quiescence) that scans state/sweep_shards/ itself rather than calling this function --
# verify_math.py:5007-5028, `_at20n`/`_batches20n`/`_run20n`. grep -rn 'latest_run(' src/*.py
# found only that def and two comment lines describing what the check USED to do. Deleting it
# is the smaller of the two remedies the order offered; the preferred one -- moving
# verify_math's finished-run selection INTO this module as `latest_finished_run(planned_batches)`
# so the shard-reading rule has one implementation instead of two -- needs an edit to
# verify_math.py, which is outside this file's ownership for this shift. Left as a note for
# whoever owns verify_math.py next.


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


def check_briefs(assigned, n=16, run=None):
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
    # AGAINST THE PLAN THE RUN WAS DISPATCHED FROM, WHEN THERE IS ONE (order 4d44a6363245).
    # This recomputed `batches(n)` at CHECK time, so running it after any src/ edit reported
    # `dropped` and `added` against a coordinator whose dispatch was exactly right when it was
    # made -- a net that fires on a correct dispatch, which is as corrosive to an audit as a
    # missed fault. The docstring above promises the comparison is "available BEFORE dispatch";
    # nothing made it mean the same thing afterwards. A frozen plan does, and it is the same
    # object the agents were dispatched from rather than a second computation of it.
    frozen = frozen_plan(run) if run else None
    if frozen is not None:
        plan = {str(b["batch"]): list(b["modules"]) for b in (frozen.get("batches") or [])}
        plan_source = "frozen plan for run=%s (%s)" % (run, plan_path(run))
        tree_moved = _table_digest(modules()) != frozen.get("src_table_digest")
    else:
        plan = {str(b["batch"]): list(b["modules"]) for b in batches(n)}
        plan_source = ("recomputed from the LIVE tree -- no frozen plan"
                       + (" for run=%s" % run if run else "; pass --run to freeze one"))
        tree_moved = None
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
        # SAY WHICH PLAN THIS WAS JUDGED AGAINST. A verdict that does not name its yardstick is
        # unreadable after the fact, and "the tree moved under a recomputed plan" is the one
        # explanation a reader must not have to guess at.
        "plan_source": plan_source,
        "tree_changed_since_freeze": tree_moved,
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
    ap.add_argument("--run", metavar="RUNID",
                    help="freeze this run's plan (or reuse the one already frozen) so a batch "
                         "number names the same modules all run long -- see freeze_plan")
    ap.add_argument("--out", metavar="PATH",
                    help="land the plan at PATH atomically instead of printing it to stdout. "
                         "Use this rather than a shell redirect; see the note in main()")
    a = ap.parse_args()
    if a.batches:
        # STDOUT CARRIES THE JSON AND NOTHING ELSE (order 2d6c9343cd32). These two summary
        # lines were printed to stdout directly after `json.dumps(plan)`, so the documented
        # way of keeping a plan -- redirecting this command into a file -- produced ONE JSON
        # DOCUMENT FOLLOWED BY COMMENT TEXT, which is not valid JSON. That is exactly the
        # "Extra data: line 231 column 1 (char 3476)" that allsweep's estate pass graded as a
        # corrupt artifact in state/sweep44_plan.json, and the order has been refiled twelve
        # times. The trap is here, in the printer, not in the operator who used a redirect.
        #
        # Nothing parses these lines: `--batches` has no programmatic consumer anywhere in
        # src/ (grep finds only this module's own docstring, MAINTENANCE.md and HANDOFF.md
        # describing the command for a human), so moving them to stderr breaks no reader. The
        # JSON stays on stdout because that is what a redirect is FOR and what every existing
        # instruction pipes; moving the JSON instead would break every one of them.
        plan_rec = freeze_plan(a.run, a.batches) if a.run else None
        plan = plan_rec["batches"] if plan_rec else batches(a.batches)
        if a.out:
            # THE REDIRECT MADE UNNECESSARY. Lands through the same helper every state file in
            # this project lands through -- pid/thread-stamped temp, then replace_retry -- so a
            # reader arriving mid-write never sees a half-file, and a refused landing is said
            # out loud instead of leaving a truncated plan behind.
            import silence
            if silence.write_json(a.out, plan, indent=1):
                print("plan for %d batch(es) landed at %s" % (len(plan), a.out),
                      file=_sys.stderr)
            else:
                print("sweep_plan: the plan did NOT land at %s (replace refused). NOTHING was "
                      "written there; do not dispatch from that path." % a.out,
                      file=_sys.stderr)
                return 2
        else:
            print(json.dumps(plan, indent=1))
        print("# %d modules, %d lines, %d batches"
              % (sum(len(b["modules"]) for b in plan),
                 sum(b["lines"] for b in plan), len(plan)), file=_sys.stderr)
        if plan_rec is not None:
            print("# plan for run=%s is %s at %s"
                  % (a.run, "FROZEN" if plan_rec.get("frozen") else "NOT FROZEN (write refused)",
                     plan_path(a.run)), file=_sys.stderr)
        else:
            print("# NOT frozen: this plan is packed from the live line counts and will "
                  "reshuffle as src/ changes. Pass --run RUNID to freeze it for the sweep.",
                  file=_sys.stderr)
        unreadable = sorted(m for b in plan for m in b.get("unreadable", []))
        if unreadable:
            # Self-announcing, on a console listing only (Hard Rule 0 concerns a listing that
            # loses evidence silently; this states its own count and every name, nothing is cut).
            print("# %d module(s) UNREADABLE: %s" % (len(unreadable), ", ".join(unreadable)),
                  file=_sys.stderr)
    elif a.check_briefs:
        with open(a.check_briefs, encoding="utf-8") as f:
            rep = check_briefs(json.load(f), a.batches or 16, run=a.run)
        print("planned %d batch(es), dispatched %d -- judged against the %s"
              % (rep["planned_batches"], rep["dispatched_batches"], rep["plan_source"]))
        if rep["tree_changed_since_freeze"]:
            print("note: src/ has changed since this plan was frozen. That does NOT invalidate "
                  "the diff below -- the frozen plan is what the agents were dispatched from -- "
                  "but a module added since is caught by `uncovered`, which reads the live tree.")
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
        # THE OTHER HALF OF THE PROOF (order f307490add1e). "nothing missing" is only evidence
        # of a complete sweep if every name that produced it was a real module. A claim that
        # resolves to nothing is not coverage, and printing it HERE is what makes a false claim
        # detectable instead of merely uncounted. Uncapped: every claim, every batch.
        bogus = unknown_claims(a.missing)
        if bogus:
            print("BUT %d recorded coverage name(s) match NO module in src/, so they prove "
                  "nothing and were not counted:" % len(bogus))
            for r, b, name in bogus:
                print("  run=%s batch=%s recorded %r" % (r, b, name))
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
