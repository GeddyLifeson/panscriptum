# sweep64 batch04 audit

Scope (every line read start to finish, in chunks, no sampling; READ-ONLY on src/, data/,
state/, output/ throughout -- nothing was run except reading source text and the coverage
record call at the end):

- src/mutate.py       3224 lines
- src/allsweep.py     1029 lines
- src/gpu_lane.py       684 lines
- src/address.py       543 lines
- src/pantheon.py       432 lines
- src/navtree.py        335 lines
- src/tempus.py         297 lines

Total 6,544 lines, all seven read in full.

## Method

Read `CLAUDE.md`'s doctrine first (Hard Rule -1 escalation/halt, Hard Rule 0 no caps, the three
safety properties, "a check that cannot fail looks exactly like a check that passed"). Then
read the prior audits covering these seven modules before touching source:
`handoff/sweep63/AUDIT_batch04.md` (mutate.py, allsweep.py), `AUDIT_batch10.md` (gpu_lane.py,
address.py, tempus.py), `AUDIT_batch12.md` (pantheon.py), `AUDIT_batch08.md` (navtree.py). All
four reported 0 VERIFIED defects in these files; batch04 filed two SUSPECTED items (allsweep's
`--quick` not skipping LINT despite its help text, and mutate's `_gate_result` subprocess call
lacking explicit `encoding="utf-8"`) and batch10 carried forward one QUESTION on
`tempus.band_resolution()`'s `LADDER.index(band)` guard, left unverifiable twice because
`assay.py` was out of scope both times.

Per the brief, this run's specific charge was today's run #64 change: `mutate.sandbox()` now
junctions `output/raw` beside `output/index`, and `reap_orphans()`'s unlink list grew the same
entry. Every line of `mutate.py` was read start to finish and then every sandbox-teardown call
site was traced by hand (not assumed from its docstring) to check whether a gate running inside
the sandbox could write through that junction to the live shelf, or whether a teardown path
could delete it. `drill.py` and `verify_math.py` are not in this batch's scope, but both are the
gate commands mutate.py actually runs, so the parts of each relevant to output/raw were read
directly to verify claims made about them, rather than trusting mutate.py's own comments.

## Findings

### 1. SUSPECTED -- `mutate.py`: the two teardown paths that fire on every ordinary (non-orphan)
sandbox do not defend the junctions the way `reap_orphans()` and `drill.py`'s mirror of it do,
and the comment claiming uniqueness for that defense is now demonstrably false.

Today's change added `output/raw` to the sandbox as a fourth junction (`mutate.py:1753-1755`,
alongside the pre-existing `prompts`, `reference`, `output/index`) and to `reap_orphans()`'s
explicit unlink-before-rmtree list (`mutate.py:1303-1304`):

```python
for shared in ("prompts", "reference", os.path.join("output", "index"),
               os.path.join("output", "raw")):
    link = os.path.join(p, shared)
    try:
        if os.path.isdir(link):
            os.rmdir(link)          # unlinks a junction; fails on a real directory
    except OSError:
        pass
```

The comment immediately above that loop (`mutate.py:1299-1302`) says:

> "The junctions inside must be unlinked, NOT followed. `shutil.rmtree` on Windows does not
> traverse a directory junction, but this is the ONE PLACE in the project where getting that
> wrong would delete `data/` -- 1.1 GB of mined corpus -- so the junctions are removed
> explicitly first and the tree only then."

`drill.py`'s `_remove_scratch_tree()` (drill.py:880-920) mirrors this exact defense, explicitly
"the way `mutate.reap_orphans` removes a sandbox," and was itself updated today to include
`output/raw` in its own `shared` list (drill.py:900-901) -- confirmed via the net
`the_mutation_sandbox_sees_the_shelf_the_live_tree_sees` (drill.py:12462-12491), which builds a
REAL sandbox with `M.sandbox()` and tears it down with this exact function.

But `mutate.py`'s own two teardown sites for the SAME sandbox -- the one built once per CLI
session and shared across every target -- do neither:

- `_run_mutation()`'s `finally` (mutate.py:2540-2542):
  ```python
  finally:
      if own_sandbox and not keep:
          shutil.rmtree(root, ignore_errors=True)
  ```
- `main()`'s `finally` (mutate.py:3218-3220), which tears down the `_session()` sandbox built at
  `root = sandbox()` (mutate.py:2807) and shared across every target in a `--target all` run:
  ```python
  finally:
      if not a.keep_sandbox:
          shutil.rmtree(root, ignore_errors=True)
  ```

Both call a bare `shutil.rmtree(root, ignore_errors=True)` on a tree containing the identical
junction set `reap_orphans()` treats as dangerous enough to warrant explicit, commented
defense-in-depth -- `prompts`, `reference`, `output/index`, `output/raw`, and every top-level
directory under `data/` (`records/`, `feats/`, `chunkfeats/`, `readfeats/`, `docs/`), all
junctioned in by the same `sandbox()` function. `main()`'s cleanup at line 3220 is the one that
fires after every single successful mutate.py CLI invocation -- not an edge case reached only
when a run is killed, which is what `reap_orphans()` exists for.

**The "one place" framing is therefore false as written**: there are at least two other call
sites in this same module performing the identical unprotected `shutil.rmtree` over the identical
junction set, one of which (`main()`'s) is the routine, successful-exit path exercised by every
ordinary run. The practical exposure is bounded by the fact this project already empirically
proved (per the same comment block, mutate.py:1317-1320) that `shutil.rmtree` does not traverse a
Windows junction on this Python -- "a throwaway junction survived a `shutil.rmtree` of its
container with its target untouched" -- so under that proven behavior neither unprotected site
actually deletes into the live tree today. But that proof is about Python's own junction handling
in `shutil.rmtree`, not about this specific machine's stack: this same CLAUDE.md records that
Norton's TLS interception already breaks unrelated filesystem/networking assumptions on this box
(`machine-tls-and-installer-constraints`), so a general claim that "X never happens on this
filesystem" carries more residual risk here than the comment's confidence suggests, and the
component with NO explicit defense is the one every routine run actually exercises.

Concrete failure scenario, contingent on that general property ever not holding (a different
Python patch version, a different antivirus/filesystem filter driver intercepting reparse-point
handling, or any other case where `shutil.rmtree` DOES recurse into a junction rather than
unlinking it): a normal `python src/mutate.py --target all` run finishes, hits `main()`'s
`finally` at line 3220, and `shutil.rmtree(root, ...)` recurses through `root/output/raw` (a
junction to the LIVE `output/raw`) and `root/data/records` etc., deleting the live shelf of
generated chapters and the mined corpus -- silently, because `ignore_errors=True` swallows
whatever the traversal raises and prints nothing.

Not filed as VERIFIED because the underlying "rmtree does not traverse a Windows junction" claim
is the project's own tested finding and most likely still holds; filed as SUSPECTED because the
comment's uniqueness claim is directly falsified by source in the same file, the routine-path
teardown (`main()`, exercised by every run, not just orphan-recovery) is the one left
unprotected, and this is exactly the shape of gap the brief asked to check for in today's
specific change (a gate/teardown path that could reach the live `output/raw`).

Suggested fix: either give `_run_mutation()`'s and `main()`'s cleanup the same
unlink-junctions-first treatment as `reap_orphans()`/`drill._remove_scratch_tree()` (a small,
already-written pattern to copy), or correct the comment to say "one of several places" and
explain why the other two are considered safe without the same defense.

### 2. VERIFIED (sound, no defect) -- run64's line-drift concern for ruled-equivalent survivors
is already handled correctly.

The brief asked specifically whether a survivor ruling keyed by `file:line` goes stale when
lines move, citing `assay.py:908` becoming `909`. Traced `mutate.py`'s ruling registry end to
end: `rule_equivalent()` (mutate.py:1076-1101) derives its key via `_order_identity()`
(mutate.py:1068-1073), which is `workorders.order_id(code, where)` over
`"MUTANT_SURVIVED_<TARGET>_L<line>"` and `"src/<target>:<line>"` -- the LINE NUMBER is baked into
the id. A ruling recorded against line 908 therefore produces a different order id than a
survivor now found at line 909; `file_orders()` (mutate.py:2564-2612) looks up
`registry.get(oid)` by the CURRENT survivor's own freshly-derived id, so the old-line ruling is
never even consulted for the new-line survivor -- it is filed as ordinary new work, which is the
documented, safe default (`ruled_equivalent()`'s own docstring at mutate.py:987-990 states this
outcome by design: "a ruling stops matching the moment the line moves ... it is filed again as
new work"). `ruling_mismatch()` (mutate.py:1027-1037) provides a second layer for the case where
an old id happens to collide with a different mutation at the same numeral, comparing target,
line, mutation text, and the exact `was`/`became` source strings, and `file_orders` reports any
disagreement in the filed order rather than silently applying a stale ruling. No fail-open path
found here; NEXT_STEPS.md's own note about assay.py:909 ("If assay's old survivor comes back at
line 909, it is already proven equivalent ... `mutate.py --rule-equivalent assay.py:909`")
matches this mechanism exactly -- the line move requires a fresh `--rule-equivalent` call, which
is the intended operator action, not evidence of a bug.

### QUESTION RESOLVED (not a new finding) -- `tempus.py:240`, `band_resolution()`'s
`LADDER.index(band)`.

Carried forward unverified across sweep61/batch15 and sweep63/batch10 ("`LADDER.index(band)` is
guarded by `if band not in BAND_EDGES` but not by `band not in LADDER`; if the two ever have
different keysets this raises uncaught... verifying requires reading `assay.py`, out of scope
both times"). `assay.py` is not in this batch's file list either, but resolving a load-bearing
open question about one of my own assigned files' correctness is in scope for verifying my own
module. Read directly: `assay.py:73-89` declares `BAND_EDGES` as a literal dict with keys
`M0`..`M10` and `assay.py:107` declares `LADDER = ["M0", "M1", ..., "M10"]` -- both are
hand-written literals enumerating the identical eleven bands, a few lines apart in the same
module, with no derivation of one from the other that could drift silently. `band not in
BAND_EDGES` and `band not in LADDER` are therefore equivalent today by direct inspection, and the
guard in `tempus.py` cannot currently be bypassed. The theoretical risk named by the two prior
audits (someone edits one list and not the other) remains a real maintenance hazard in principle,
but it is not a live defect and the guard is sound as written. Downgrading this from an open
QUESTION to closed.

## No other findings

Beyond the two items above, no other tautological/cannot-fail check, fail-open branch, new
undisclosed cap or truncation (Hard Rule 0), wrong-variable/off-by-one/unit-mix bug, race outside
the documented `silence.replace_retry`/CAS patterns, resource leak, or comment/docstring
asserting behavior the code does not have was found in any of the seven modules. Specifically
traced and found sound:

- `mutate.py`: the AST-span mutation locator (`_spot`/`_between`/`_token_pos`/`_fallback_spot`)
  and its UTF-8 byte/character column correction; the `_gate_result` subprocess call now DOES
  carry `encoding="utf-8", errors="replace"` (mutate.py:801-802) -- the sweep63/batch04 SUSPECTED
  finding against this exact line is fixed and not re-filed; the sandbox build order
  (BUILDING_PREFIX -> claim -> atomic rename to SANDBOX_PREFIX); the per-mutant `_touch_root`
  keep-alive; the differential (not absolute) kill test in `_gate_result`/`could_not_judge`; the
  hang-confirmation asymmetry check (`hang_confirms_a_kill`); the mid-run `_refresh_baseline`
  drift bookkeeping and its two event shapes both being handled in `_session`'s print loop; the
  live-tree-refusal guard in `_run_mutation` (root == HERE); the missing-baseline refusal; no
  gate in `FAST_GATES`/`CONFIRM_GATES` writes to `output/raw` (confirmed directly: `verify_math.py`
  has no reference to `output`/`raw` at all beyond an unrelated dict key named "raw"; every real,
  non-scratch-tree read of `output/raw` in `drill.py`, including the new
  `the_mutation_sandbox_sees_the_shelf_the_live_tree_sees` net and
  `gate_claim_matches_reality`/`_catalog_matches_disk`, uses only `os.path.isdir`/`os.listdir`/
  `os.path.exists`, never a write).
- `allsweep.py`: the sweep63/batch04 SUSPECTED finding against `--quick`'s help text vs. behavior
  is fixed (allsweep.py:754-755 now documents that LINT intentionally still runs under `--quick`,
  matching the code); `_row_is_fault`'s fail-closed default on a keyless ESTATE row;
  `estate_faults`/`bad` sum covering IMPORT/LINT/VERIFY/ESTATE/write-denied, with RECONCILE
  deliberately and honestly left ungraded; every reconcile listing (`_head`) confirmed to keep the
  full `names` list for the JSON record while only the console line is capped.
- `gpu_lane.py`: `_slot_count`'s auto/zero/malformed-env handling; `_alive`'s Windows
  OpenProcess-based liveness check and its "unknown answers are ALIVE" fail-open policy;
  `_take_slot`'s three-way (path/False/None) return and the None="unarbitrable, go now" fix;
  `_touch`'s never-resurrects guard; `_heartbeat`'s dual-lease refresh (slot and foreground claim)
  and the shutdown ordering in `lane()`'s `finally` (stop heartbeat before releasing).
- `address.py`: `spine_code_for`'s four-stage matcher (exact/normalized-equality/most-specific
  containment with `_index_name_is_placed_like_a_title`/token-overlap fallback) traced by hand
  against its own extensively-documented false-positive history; `tier_for`/`tier_rank`/`promote`
  promotion-only-never-demotion logic; `slugify`'s uncapped output.
- `pantheon.py`: `compute()`/`value()`/the Z_FIGHTERS merge and its three-way failure handling
  (partial roster via `_incomplete`, total merge failure, write-denied), all three correctly
  folded into the exit code as well as the console.
- `navtree.py`: `sources_under`'s `+ "."` boundary fix; `register_for`/the hyperverse-naming
  tie-break's deterministic secondary key; `audit()`'s bidirectional catalog/child-sum check;
  the write gating on a clean audit and on `write_json`'s return value.
- `tempus.py`: `rung_description_length`/`band_resolution`'s derivation from `BAND_EDGES`;
  `prescience_horizon_bits`'s positive-lead-time guard; `DEGENERATE_TIME`'s "reported dead, not
  deleted" marker verified still accurate (one battery reader, `verify_math.py:861`, no
  production caller).

## Coverage recorded

Recorded via `sweep_plan.record('run64', [...], batch=4)` for the seven modules above, from the
kit directory.
