# Sweep 59 -- AUDIT batch 04

Modules read in full:

| module | lines | read (top to bottom? mtime) |
|---|---|---|
| src/mutate.py | 3199 | yes, full (mtime 23:55:34) |
| src/onomast.py | 844 | yes, full (mtime 22:14:57) |
| src/custodes.py | 714 | yes, full (mtime 22:21:23) |
| src/policy.py | 598 | yes, full (mtime 22:14:57) |
| src/burgs.py | 442 | yes, full (mtime 22:14:41) |
| src/citecheck.py | 353 | yes, full (mtime 22:14:57) |
| src/cosmology_graph.py | 261 | yes, full (mtime 23:41:56) |
| src/chord_field.py | 210 | yes, full (mtime 22:52:48) |

All eight mtimes were re-checked after the full pass and were unchanged from the values above, so
nothing moved under this batch while it was being read.

## src/mutate.py

### New findings

**DEFECT MAJOR -- naming a code path that can delete a live pass's sandbox (answers order 9ea4d3545524)**

where: src/mutate.py `OWNERSHIP_CEILING_SECONDS`/`_owner_pid` (lines 1139, 1142-1181),
`reap_orphans` (lines 1223-1336, ownership check at 1283-1286), `sandbox()` (line 1452 calls
`reap_orphans()` with the plain 6-hour default against the REAL `tempfile.gettempdir()`); and
src/drill.py `scratch_tree()` (lines 780-790) and the fixture at drill.py:9627-9646, both of which
call the REAL `mutate.sandbox()` with `tempfile.tempdir` **not** redirected.

evidence:
```
# mutate.py:1157-1161
So the claim carries the time it was made, and it stops being believed after
`OWNERSHIP_CEILING_SECONDS`. That is comfortably longer than the longest plausible mutation
run (hours) and comfortably shorter than forever, so a live owner is protected for as long
as it could possibly still be working, and a recycled pid can strand a directory for at most
one day instead of for good.
...
# mutate.py:1178-1181 (_owner_pid)
    if time.time() - started > OWNERSHIP_CEILING_SECONDS:
        silence.note("mutate.py:owner-claim-expired")
        return None
    return pid
...
# mutate.py:1283-1286 (reap_orphans)
        owner = _owner_pid(p)
        if owner is not None and _pid_alive(owner):
            silence.note("mutate.py:reap-skipped-live-owner")
            continue
...
# mutate.py:1139
OWNERSHIP_CEILING_SECONDS = 24 * 3600
...
# mutate.py:2653 (main(), the --detach comment)
    # A completed pass takes about twenty hours -- the 2026-09-04 run logged 72,310s across its
...
# drill.py:780-790
def scratch_tree():
    """A throwaway copy of this library, in `mutate.sandbox()`'s exact shape. -> root path.
    ...
    """
    import mutate as M
    return M.sandbox()
```

failure: `_owner_pid` (1142-1181) makes the ownership claim that protects a live sandbox "at ANY
age" (reap_orphans's own comment, line 1252) EXPIRE after `OWNERSHIP_CEILING_SECONDS` = 24h,
*regardless of whether the pid is still demonstrably alive* -- confirmed as intended behaviour by
drill.py's own net at line ~19001-19002, which constructs a fixture with a genuinely live pid
(`child.pid`, a real subprocess) and an 25-hour-old `started`, then asserts the sandbox IS reaped
("a recycled pid cannot protect for ever"). Once that ceiling lapses, protection falls back
entirely to the sandbox root's mtime being kept fresh by `_touch_root` (called once per mutant,
line 2339) against the plain `ORPHAN_AGE_SECONDS` = 6h default `reap_orphans()` uses on every
ordinary call.

The file's own evidence undercuts the "comfortably longer than the longest plausible mutation run"
claim at line 1158: this same file logs a completed run at 72,310s = 20.09h (line 2653) and another
at 58,709s = 16.3h (order 58a00e909217's evidence), and the sandbox() docstring itself records two
passes that were still only two-of-three targets in at ~12.3h before they died (lines ~1470-1473).
20.09h leaves only ~3.9h of margin under the 24h ceiling, on a module whose own `--rebaseline-every`
default (1800s) and hang-detection/drift machinery keep adding wall-clock overhead run over run.

`reap_orphans()` is not a function the mutation pass calls only on itself: `sandbox()` calls it
unconditionally, at the top, against the REAL system temp directory (`tempfile.gettempdir()`,
never redirected in production) -- and `drill.py`'s `scratch_tree()` (called from `prove_net()`,
the mechanism behind `python src/drill.py --prove <net>`, an ordinary diagnostic command this
project runs routinely) and the fixture at drill.py:9627-9646 both call the REAL, un-redirected
`mutate.sandbox()`. (Contrast the two nets at drill.py:18975-19028 and :19036-19092, which
deliberately swap `tempfile.tempdir` to a throwaway root *specifically because* an un-contained
`reap_orphans()` call was once found to delete every concurrent sandbox on the machine -- that
containment was never applied to `scratch_tree()`/`prove_net()`, whose job is exactly to build a
real sandbox via the real `mutate.sandbox()`.)

So the concrete chain order 9ea4d3545524 asks for is: a mutation pass runs past
`OWNERSHIP_CEILING_SECONDS` (plausible -- see the timings above) -> its ownership claim silently
expires while the process is still very much alive and working -> at some point later (before its
root's mtime, refreshed every mutant by `_touch_root`, happens to lapse past 6h, which requires
either a stall or simply bad timing) somebody on the same machine runs `python src/drill.py --prove
<any net that calls prove_net>` for a completely unrelated reason -> that invocation's
`scratch_tree()` builds ITS OWN sandbox via the real `mutate.sandbox()`, which calls the real
`reap_orphans()` with the default 6h age -> the live pass's now-unprotected, momentarily-stale
sandbox is deleted mid-run, from a process that has no idea the pass exists and that leaves no
cross-reference in the live pass's own log. This is consistent with the symptom on record ("died on
a FileNotFoundError for their own sandbox path, mid-run") and gives the previously-unnamed deleting
actor a name: an ordinary, unrelated `drill.py --prove` invocation, once the 24h ownership ceiling
has lapsed on a run that is (per this file's own logged history) not implausibly long.

remedy: the smallest fix that removes the exposure without touching the "recycled pid" protection
`OWNERSHIP_CEILING_SECONDS` exists for: have `_touch_root`'s per-mutant call also rewrite the
`_owner.json` claim's `started` field (or add a separate `last_seen` field `_owner_pid` checks
instead of `started`), so a pass that is still actively touching its own sandbox never ages out of
ownership no matter how long it runs, while a pass that stops touching it (crashed, or truly
orphaned) still degrades to the existing age-only fallback. Separately, `scratch_tree()`/
`prove_net()` should redirect `tempfile.tempdir` the same way the two reaper-proving nets already
do, so an ordinary `--prove` run cannot invoke `reap_orphans()` against the real temp directory at
all.

### Known (already open orders)
- `9ea4d3545524` (MUTATE_SANDBOX_FILENOTFOUND_MID_PASS_UNEXPLAINED) -- still open, and the finding
  above is offered as new evidence toward it: a concrete code path (ownership-ceiling lapse +
  `drill.py --prove`'s un-redirected `scratch_tree()`) rather than a full reproduction. Not closing
  it myself (Hard Rule -1: I found this, I did not cause it -- the halt-lift asymmetry applies to
  orders the same way it applies to halts).
- `58a00e909217` (MUTATION_LONG_RUN_SCORED_AN_UNKILLABLE_MUTANT_AS_KILLED) -- still accurate. Its
  "leading explanation" (a `data/` junction drift over a 16-hour run) is a different mechanism from
  the sandbox-deletion one above; both can be true at once and neither rules out the other.
- `1d45a56ae1d8` (STALE_CITATIONS_SWEEP57...) -- still accurate for mutate.py. Re-checked: the
  `assay.py:593` citation is still present, now at line 887 (was ~886); the `reap_orphans()` call-
  site comment discussed at ~1264 and the verify_math live-failure-ledger citation at ~1677 are
  both still in the file in the same shape (lines 1264-1265 and ~1677-1680 respectively). Line
  drift only; not re-filed per the sweep brief and per orders 89503c58409f/1d45a56ae1d8/d7efd67caa6f.

### Checked and clean
- The `--detach` re-spawn (lines 2672-2696) does NOT create the pid-mismatch hazard its own
  candidate-causes list raises: the parent process spawns the child and returns at line 2696,
  before ever reaching `_session()`/`sandbox()` (line 2782); only the child ever calls
  `_claim_sandbox`, so the owner file always records the pid of the process that is actually doing
  the work, not a parent that has already exited.
- `sandbox()`'s `BUILDING_PREFIX` -> rename -> `SANDBOX_PREFIX` claim sequence (lines 1476-1497) is
  sound as re-verified by reading it end to end: `_claim_sandbox(staging)` is called before the
  `os.rename`, so there is no instant at which a name the reaper matches exists without an owner
  claim inside it, and the fallback path when `os.rename` fails also claims before use.
- `reap_orphans`'s junction-unlinking of `data/`'s per-entry subdirectories (lines 1298-1319)
  matches the described mechanism in `sandbox()` (hardlinked top-level files, junctioned top-level
  directories) and unlinks each one individually rather than trusting `shutil.rmtree` to skip
  junctions, consistent with the comment's own claim to have verified that behaviour directly.
- `_hold_lock`'s re-entrant token handling (lines 337-376) correctly clears `_HELD` before
  releasing, so a re-entrant caller mid-release cannot observe a stale claim.

## src/onomast.py

### Checked and clean
- `well_formed()`'s seven constraints (lines 213-239) match its own docstring's list (length,
  echo, stutter, cluster, density, vowel run, vowel floor) exactly against the code, including the
  three attribution corrections the docstring itself records (Shessasha/Goggoktok/Zgournazhun).
- `name_worlds()`'s retired-vs-standing carry-forward logic (lines 649-695) is internally
  consistent: a cid in `naming` this run always appears in `out` (same `by_key`/`naming`
  derivation), and `merged`'s `retired: cid not in resolved` correctly leaves a shelf that shrank
  to one world (still in `resolved`, no longer colliding) unflagged.
- `register_for`'s "HELD, MARKED, AND NOT WIRED" gap (lines 450-480) is an owner-ruled, already-
  documented design hold (order `ae25c89f0179`), not a live defect; `name_worlds` calling it with
  one positional argument is consistent with that ruling, not an oversight.
- No `_BAD_CHARS` gap: the guard is present (lines 78-80), matching the brief's list of 24 modules
  run #59 already patched.

## src/custodes.py

### Known (already open orders)
- `34ec8a90c42f` item 4 (OWNER_QUESTIONS_FROM_SWEEP57_BUNDLE, custodes.py `_transit_widening()`) --
  still accurate. Re-verified against the current `_transit_widening` (lines 388-428): the sum
  really would double-count if a second `dof="currency"` dispersive Custos were ever added: only
  Lumen carries `dispersive=True` with `dof="currency"` today, so nothing is currently wrong, and
  the docstring at lines 399-405 states the accumulate-per-Custos design plainly. Not re-filed.

### Checked and clean
- `table_faults()` (lines 600-631) correctly targets the tilt=0/sensitivity!=0 coupling class it
  documents, and both zero-tilt Custodes (Threnody, Lumen) declare `evidence_sensitivity=0.0` today,
  so `main()`'s `return 1 if _faults else 0` (line 710) is currently 0 -- consistent, not a false
  green (the table really is clean right now).
- `convene()`'s attendance/abstention bookkeeping (lines 469-588) matches its own docstring: the
  band-only early return (line 512-513) and the full return both carry `staleness_measured`/
  `comparability_measured` from the same `attendance` dict built before either return.

## src/policy.py

### New findings

**QUESTION -- `is_type` with `arg="int"` silently accepts a bool**

where: src/policy.py `OPS["is_type"]` (line 78), `TYPES` (line 93).

evidence:
```python
"is_type":   lambda v, a: isinstance(v, TYPES[a]),
...
TYPES = {"str": str, "int": int, "float": float, "bool": bool, "list": list, "dict": dict}
```
Because `bool` subclasses `int` in Python, a rule `{"op": "is_type", "arg": "int"}` against a
field holding `True`/`False` returns `ok=True` -- `isinstance(True, int)` is `True`. No rule in
`RECORD_RULES`/`EVIDENCE_RULES`/`COVERAGE_RULES` currently uses `is_type` with `arg` other than
`"list"`, so nothing is misfiring in production today; this is a landmine for the next table, in
exactly the shape `TYPES`'s own comment (lines 83-92) already warns about for an unvalidated
default. Two readings, and why this needs a ruling rather than a mechanical fix: (a) treat it as a
gap and special-case `int`/`bool` in `is_type` so a boolean only satisfies `arg="bool"`, matching
how a person reads "is this an int"; or (b) leave it, since Python's own type system makes the same
choice and a table author who cares about the distinction can write two rules (`is_type: int` and
`ne: true`/`ne: false`). Not filed as a DEFECT because nothing observably breaks today; flagged so
the next table author is not the one who discovers it.

### Known (already open orders)
- `21c075e5e2d6` (MORE_WRITERS_WITHOUT_A_HALT_INTERLOCK_SWEEP58) -- names `policy.py` among the
  writers that never call `escalation.assert_clear()`. Still accurate: `main()`/`report()` write
  `state/policy_report.json` unconditionally regardless of `escalation.status()`.

### Checked and clean
- `evaluate()`'s vacuous-pass exemption for `op == "absent"` (lines 219-228) is narrow exactly as
  documented and does not extend to `not_matches`, whose `v is None` clause is confirmed (by
  reading `OPS["not_matches"]`, line 76) to pass vacuously on an absent field as a side effect.
- `check_rule`'s KeyError/TypeError containment for malformed rules (lines 164-204) correctly keeps
  a bad rule from being reported as a document failure -- verified the `is_type`/`in_range`/
  `ARG_REQUIRED` checks all run before `resolve()`/the lambda call, so a malformed rule always
  raises `BadRule` rather than falling into the `except Exception` at line 199.

## src/burgs.py

### Checked and clean
- `_rank_at_or_above` (lines 206-225) and `rank_population` (lines 156-164) agree at their
  boundary in every case traced by hand (p1 < lo, lo <= HAMLET_FLOOR, and the general case), so the
  closed-form-then-corrected-by-the-real-expression design does not silently disagree with itself.
- `burgs_for`'s `--limit` handling (lines 268-269) correctly narrows-only (`max(0, min(int(limit),
  n))`), matching the fix order `1bc825e806a9` describes; `limit=0` returns zero rows rather than
  falling through to the whole roll.
- `main()`'s `per_world` keyed by a list per designation (lines 337-344), the histogram accumulation
  and `total` are all built from the same per-world loop, so the percentages printed at lines
  353-355 are guaranteed to sum against the same denominator (the numerator/denominator split bug
  order `65ae84ee4bd7`/comment at 350-352 describes is not reproducible against the current code).

## src/citecheck.py

### Checked and clean
- `_classify`'s lineno<1 handling (line 141) correctly reports `PAST_EOF` for a `.py:0` citation
  rather than reaching a negative-index read of `lines[-1]`.
- `_in_tree_lead` (lines 162-188) and the `_PATH_LEAD`/`_PLACEHOLDERS` checks are applied
  identically in `stale_citations` (lines 231-292) and `citations_in_text` (lines 191-228) even
  though the two loops are separate copies, matching the docstring's claim that only `_classify`/
  `_in_tree_lead`/`_PLACEHOLDERS` are the shared "rules", not the scanning loop itself.
- `CITATION`'s regex (line 67) with its trailing `\b` correctly captures only the first number of a
  `file.py:1741,1744` or `file.py:1584-86` style citation, matching the docstring's claim.

## src/cosmology_graph.py

### Checked and clean
- `build_graph()`'s pair key ordering (`sources[i], sources[j]` from a single `sorted()` call,
  lines 114-139) guarantees one canonical key per source pair regardless of which shared entity is
  processed first, so weights from different entities correctly accumulate onto the same pair key
  rather than fragmenting into `(a,b)` and `(b,a)` variants.
- The `--write` path (lines 206-256) writes every pair unfiltered with `pairs_filtered: False` and
  `threshold_applies_to: "clusters"` stated explicitly, matching the module's own historical note
  about the previously-undeclared `if w >= 1.0` filter (order `9861c18b8485`) -- not reproducible
  against the current code.

## src/chord_field.py

### Checked and clean
- `landauer_floor`, `recoil_momentum` and `critical_power_self_focus` (lines 188-210) all match
  their stated physics formulas (Landauer bound, p=E/c, Marburger critical-power expression) with
  no unit or constant errors found.
- No dead constants: `C_LIGHT` and `K_BOLTZMANN` (lines 44-45) are both read by name inside this
  file (`recoil_momentum`, `landauer_floor`), consistent with the module's own comment about having
  removed the previously-unused `G_NEWTON`/`HBAR` pair.

---
Coverage recorded via `sweep_plan.record('run59', [...], batch=4)`.
