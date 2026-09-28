# sweep66 batch04 — audit

## Scope

Every module read in full, start to finish, sequentially, via the Read tool in chunks (large
files split across multiple offset/limit reads with no gap between them), no sampling and no
grep-driven skimming. Line counts from `wc -l` at time of reading:

| module                 | lines |
|-------------------------|------:|
| src/mutate.py            | 3291 |
| src/completeness.py      |  905 |
| src/weave.py             |  709 |
| src/canon_backup.py      |  549 |
| src/cleanup.py           |  452 |
| src/catalogue_models.py  |  364 |
| src/tempus.py            |  297 |

Total 6,567 lines across 7 modules, all read completely.

READ-ONLY throughout: nothing under `src/`, `data/`, `state/`, `output/`, `prompts/`,
`reference/` or the repo root was edited, other than this file and the final
`sweep_plan.record()` call. No subagent was spawned. No network call was made. `mutate.py` was
read only, never executed (per the brief and per this module's own standing rule that a
mutation pass must run in a sandbox, never against the live tree).

## Method and prior-audit cross-check

`CLAUDE.md` was read first this session (Hard Rule -1 escalation/halt chain and its three
safety properties — INDEPENDENT, FAIL CLOSED, PROVEN — and Hard Rule 0, no caps/no truncation).

`handoff/sweep65/` was grepped for all seven module names and every matching report read in
full before touching source:

- `sweep65/AUDIT_batch04.md` — same batch number, covered `mutate.py`, `completeness.py`,
  `canon_backup.py`, `cleanup.py`, `catalogue_models.py` (plus `secondopinion.py`, `tuning.py`,
  `lognames.py`, out of this batch's current scope) in full. Zero new findings; one item closed
  that cycle (`mutate.py`'s sandbox teardown now unlinks junctions before `rmtree`, fixing a
  sweep64 finding); two carried QUESTIONs (`cleanup.py`'s brief-vs-source mismatch on what it
  can delete; `canon_backup.py:274`'s `prune()` no-op on `--keep 0`/negative).
- `sweep65/AUDIT_batch14.md` — covered `weave.py` in full alongside `hostcheck.py`, `health.py`,
  `liveness.py`, `anchors.py`, `coverage.py`, `sweep.py`, `roll.py`. Zero VERIFIED/SUSPECTED
  findings against `weave.py`; the standing OWNER-routed order about writers with no
  `escalation.assert_clear()` interlock (naming `weave.py` among others) noted but not
  re-litigated.
- `sweep65/AUDIT_batch15.md` — covered `tempus.py` in full (new to that batch's roster that
  cycle). Zero findings; the standing OWNER order about `tempus.py`'s battery-only public
  functions (`7099a092abd3`) noted but not re-litigated.

`state/workorders.json` was searched for all seven module names before writing anything down.
Four hits, all already-open OWNER-routed bundles, none of them contradicted by this read and
none needing a duplicate filing:

- `weave.py` (and `chain.py`, `axis_correlation.py`, `roll.py`) named as writers of derived
  library state with no `escalation.assert_clear()` call — order bundle including
  `1e6f99e54b25`/`21c075e5e2d6`. Verified unchanged this cycle: `weave.py`'s `main()` writes
  `CONTINUITY_GROUPS.json`/`RESOLVED_ENTITIES.json`/`SHARED_STAGE_GRAPH_IDF.json` under
  `--write` with no halt check anywhere in the module. Already open; not re-filed.
- `tempus.py`'s `retrocausality_beta`/`contemporaneous`/`is_present_at`/
  `prescience_horizon_bits` named (alongside `assay.py`/`ledger.py`/`cosmography.py` functions)
  as having no production caller besides `verify_math.py`'s own battery — order
  `1a9c237dda4d`, corrected/cross-referenced by a later order at line 398. Verified unchanged:
  grepping the tree finds no caller of these four outside `verify_math.py`. Already open at
  OWNER; not re-filed.
- `mutate.py` named once, as the subject whose baseline signature a GPU-contention finding
  concerns (`src/verify_math.py` holding a live Ollama connection during a run) — not a defect
  in `mutate.py` itself, a resource-contention finding about what it measures. Unchanged.
- `completeness.py:primary` — the shared-non-fandom-host "no primary can be identified" question
  (order `f5b8e4afb558`). Verified against live source: `work()`'s `elif shared[host] > 1 and
  ...` branch at completeness.py:703-714 still carries the corrected reporting-only wording
  ("Not 'this source lost'; 'the question was never asked'") landed by an earlier sweep; the
  measuring-half ruling itself remains open at OWNER. Not re-filed.

The SWEEP61/SWEEP63 six-question bundle (workorders.json line 106) was also re-read: item 1
("`mutate.py`'s `--list` is refused under a standing halt while `--list-ruled`/
`--rule-equivalent`/`--unrule` are exempt") and item 5 ("`canon_backup.py` `prune()`'s `--keep
0`/negative silent no-op") both touch this batch. Both re-verified against current source (see
Questions below) and not re-filed.

## Findings

**0 CRITICAL. 0 MAJOR. 0 MINOR. 0 COSMETIC (new). 0 SUSPECTED.**

This is, again, one of the most heavily self-documented and previously-audited stretches of the
codebase — nearly every non-trivial branch across all seven files carries its own paragraph
naming the specific defect it was written to close, the order id, and often a reproduced
before/after measurement. Traced by hand this pass rather than taken on the comments' word,
against the hazards named in the brief (fail-open branches, off-by-ones, inverted conditions,
silently swallowed exceptions where the code claims fail-closed, guards that cannot fail, races
on shared state files, Hard-Rule-0 caps/truncations, stale comments, dead branches):

- **mutate.py** (SAFETY-CRITICAL, mutation-testing harness): the full AST-mutation engine
  (`_mutations`, `_spot`/`_between`/`_token_pos`/`_fallback_spot`, the UTF-8 byte-vs-character
  `_col` correction, the per-occurrence dedup keyed on `(lineno, new_src)` rather than
  description); the lock's O_EXCL-then-token-checked acquire/release
  (`_lock_acquire`/`_lock_release`/`_hold_lock`) and its now-wired re-entrant hold via
  `_hold_lock`/`run()`/`main()`; the BUILDING_PREFIX-then-rename sandbox-claim sequence (M46);
  `_owner_pid`'s 72h ownership ceiling against pid recycling; `_touch_root`'s per-mutant
  keep-alive so a live pass does not age into `reap_orphans`; the differential (never-absolute)
  kill test in `_gate_result`/`could_not_judge`/`hang_confirms_a_kill`'s two-independent-reading
  hang confirmation; `_refresh_baseline`'s mid-run re-photograph, its "unusable refresh is
  discarded, not adopted" guard, and both `baseline_drifts` event shapes correctly handled in
  `_session`'s print loop; the live-tree-refusal guard (`root == HERE` / `root/src == SRC`) and
  the missing-baseline / ungauged-gate hard refusals in `_run_mutation`; the ruled-equivalent
  registry's line-keyed order-id derivation and `ruling_mismatch`'s exact-field comparison (a
  ruling cannot silently misapply itself to a mutation that moved lines); `_remove_sandbox`
  (confirmed identical in sequence to `reap_orphans`'s own junction-unlink-then-rmtree, closing
  the sweep64 finding for good — both call sites, `_run_mutation`'s `finally` and `main()`'s via
  `_session`'s `finally`, read `_remove_sandbox(root)`, not a bare `rmtree`); the `sandbox()`
  hardlink-not-copy treatment of top-level `data/` files (proven safe against
  `silence.write_json`'s atomic-replace semantics, per the module's own docstring) and its
  directory-vs-file per-entry branching; `main()`'s `--list`/registry-command/halt-check
  ordering (see Questions).
- **completeness.py**: `work()`'s multi-way split (no-host sentinel / unreachable host /
  no-denominator / existing-but-zero / genuine "no such category" / cov>1.0 probe-set-miss /
  shared-host primary) and the `if n is not None` vs `if n` distinction preserving a genuine
  `pages: 0` answer from a `missing` category; `land()`'s three-outcome verdict
  (`True`/`False`/`SKIPPED_ONLY`), its shrink-floor guard, and its `silence.write_json`-gated
  atomic write; `host_reachable`'s three-mode (RAW/API/DEAD) probe dispatch; the `primary`
  dict's longest-alnum-key-match construction, re-traced by hand against `shared[host] > 1`
  branching — the primary source for a shared host correctly takes none of the disqualifying
  `why` branches.
- **weave.py**: `components()`'s complete-linkage agglomeration and its `threshold <= 0`
  refusal (a pair with no shared entity defaults to 0.0 in `lookup.get`, so a non-positive
  threshold would merge everything — correctly refused); `null_threshold_surprisal`'s
  `NullThresholdUnmeasured` distinction from a genuine zero-valued median; `filtered_index`'s
  fail-closed re-raise on an unimportable `pipeline` (confirmed both current callers,
  `pipeline.phase_weave` and `tiers._graph`, already call it unwrapped and expect the raise to
  propagate); `resonance_graph`'s BFS-per-source eccentricity/diameter computation; `resolve`'s
  homonym-vs-fusion split by continuity-group id.
- **canon_backup.py**: `members()`'s strict refusal on any missing declared canonical path
  (never silently backs up a subset); `snapshot()`'s read-back verification (reopens the
  just-written zip, re-hashes every member, refuses to record success on any mismatch) and its
  now-checked manifest write; `prune()`'s "half-removed pair counts as not removed" logic and
  its orphan-scratch-file age-based reaping; `verify()`'s archive-vs-manifest-vs-live three-way
  comparison, including the `unreadable`-is-not-`changed` split (a locked live file must not
  read as data drift) and the archive-contains-what-the-manifest-claims check (`absent`/`extra`
  computed from `z.namelist()`, not merely `testzip()`); `restore()`'s open-source-before-create
  ordering and its checked `replace_retry` verdict.
- **cleanup.py**: confirmed (again) that this module performs no filesystem deletion — its most
  destructive action is flipping `catalogued` to `False` with an `excluded` reason, consistent
  with the standing brief-vs-source Question; `_ruby_question_mark`/`_ruby_parenthetical`'s
  non-ASCII guards (correctly decline on plain English "(and, uh, Hawkeye?)"-shaped text) and
  the `(?<!\?\?)` lookbehind that makes the stray-`?` rule idempotent; `clean_ceiling`'s
  exact/head/single-prefix-only resolution ladder, specifically re-traced for the
  `prefix-ambiguous` guard (`len(low_pref) == 1` required before a prefix match is accepted,
  never the shortest-of-several guess the sibling comment records as a prior defect); the
  guarded-once `thin_description` mark (only sets `changed` the first time, per its own inline
  order note) and the gated `write_record` call whose False return is checked and reported via
  `unwritten`, never silently swallowed.
- **catalogue_models.py**: the LISTED/EMPTY_LIST/UNREACHABLE/UNCONFIGURED four-way outcome and
  its propagation into `live`/`stale`/`unverified` accounting (EMPTY_LIST correctly counted as
  verified-and-live in both branches that matter, not folded into "unreachable" by a truthiness
  test on an empty list); `LAST_WRITE_LANDED`'s three-state (None/False/True) contract, its
  honest `None` default, and confirmed that `main()`'s bare `return 0 if LAST_WRITE_LANDED else
  1` correctly sees `sweep()`'s `global` reassignment (both live in the same module namespace).
- **tempus.py**: `rung_description_length`'s derivation of `L_r` from `assay.BAND_EDGES` (no
  invented free parameter) and its `band not in BAND_EDGES -> None` refusal; `band_resolution`'s
  M10 saturation branch correctly reusing the M9→M10 width; `is_present_at`'s `>=` direction
  matching "a lower rung sees a larger now"; `prescience_horizon_bits`'s positive-lead-time
  guard (raises rather than silently producing a negative/zero bit cost); `apparent_lag_years`'s
  uniform return shape (`distance`/`lag_years`/`path`/`note` always present, even on the
  no-path branch) confirmed correct in both branches by hand.

No tautological/cannot-fail check, fail-open branch, new undisclosed Hard-Rule-0
cap/truncation, off-by-one/unit-mix bug, race outside the project's documented
`silence.write_json`/`replace_retry` CAS patterns, resource leak, or comment/docstring
asserting behavior the code does not have was found in any of the seven modules beyond what is
already recorded, fixed, and documented in the source itself or in a standing work order.

## Questions (possible deliberate design — not findings; not re-filed, both already open)

1. **`mutate.py`'s `--list` refusal asymmetry** (sweep61 question, workorders.json line 106,
   item 1). Re-verified against current `main()` (mutate.py:2694-2856): the registry commands
   (`--list-ruled`, `--rule-equivalent`, `--unrule`) run and `return` *before* the
   `escalation.status()` halt check at line 2826, on the stated reasoning that none of them
   mutates anything. `--list` (mutate.py:2833, "count the mutants, run none of them") is checked
   *after* the halt check, alongside every mutating path, so it is refused under a standing
   halt for the identical reason ("counts, mutates nothing") that exempts the other three. Still
   fail-closed (a convenience refused, not a safety bypassed), still unchanged from sweep61/65.
   Not re-filed — already routed to the owner as part of the six-question SWEEP61 bundle.
2. **`canon_backup.py:274`'s `prune()` no-op on `--keep 0`/negative** (sweep61 question,
   workorders.json line 106, item 5; also sweep64 batch13, sweep65 batch04). Re-verified: `for f
   in snaps[:-keep] if keep > 0 else []` at canon_backup.py:274 still silently deletes nothing
   when `--keep` is 0 or negative, with no message either way. Not exploitable under the current
   default (`KEEP = 7`); the CLI's own `--keep` argument has no floor. Still undocumented, still
   not worth a standalone fix per the standing reading. Not re-filed.

No other design questions arose that were not already answered by the modules' own doctrine
comments or by the open orders cross-checked above.

## Coverage recorded

Ran `sweep_plan.record('run66', ['mutate.py', 'completeness.py', 'weave.py', 'canon_backup.py',
'cleanup.py', 'catalogue_models.py', 'tempus.py'], batch=4)` from the kit directory via the
miniconda python, per the brief. All seven modules were read in full before this call.
