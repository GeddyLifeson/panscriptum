# sweep65 batch04 audit

## Scope

Read in full, start to finish, sequentially with the Read tool (offset/limit chunks for the
large files), no sampling and no grep-driven skimming. Line counts from `wc -l` at time of
reading:

- `src/mutate.py`            3291 lines — SAFETY-CRITICAL (mutation-testing harness). Per the
  brief: read only, NEVER executed, because a detached mutation pass was running against it live.
- `src/completeness.py`       905 lines
- `src/secondopinion.py`      708 lines
- `src/canon_backup.py`       549 lines
- `src/cleanup.py`            452 lines
- `src/catalogue_models.py`   364 lines
- `src/tuning.py`             286 lines
- `src/lognames.py`            52 lines

Total 6,607 lines across 8 modules, all read completely. READ-ONLY throughout: nothing under
`src/`, `data/`, `state/`, `output/`, `prompts/` or `reference/` was edited, and nothing was run
except the final `sweep_plan.record()` call. No subagents were spawned.

## Method and prior-audit cross-check

`CLAUDE.md` was read first (Hard Rule -1 escalation/halt, Hard Rule 0 no-caps, the three safety
properties, "a check that cannot fail looks exactly like a check that passed").

`handoff/sweep64/` was grepped for all eight module names before reading source:

- `AUDIT_batch04.md` (sweep64) covered `mutate.py` in full (under a different seven-file
  grouping) and filed one SUSPECTED finding against it: the routine (non-orphan) sandbox
  teardown in `_run_mutation`'s and `main()`'s `finally` blocks did a bare
  `shutil.rmtree(root, ignore_errors=True)` over a tree containing the same live junctions
  (`output/raw`, `output/index`, `prompts`, `reference`, every `data/<dir>`) that
  `reap_orphans()`/`drill._remove_scratch_tree()` unlink explicitly first, which falsified the
  governing comment's "one place in the project" claim.
- `AUDIT_batch13.md` (sweep64) covered `completeness.py`, `secondopinion.py`, `canon_backup.py`,
  `cleanup.py`, `tuning.py` and `lognames.py` together (with `assay.py`, `silence.py`, `sweep.py`
  out of this batch's scope) — 0 VERIFIED, 0 SUSPECTED new findings, two carried-forward
  QUESTIONs (the brief-vs-source mismatch on what `cleanup.py` deletes, and
  `canon_backup.py:274`'s `prune()` no-op on `--keep 0`/negative).
- `AUDIT_batch12.md` (sweep64) covered `catalogue_models.py` (365 lines then) alongside four
  other modules — 0 new findings, confirmed its LISTED/EMPTY_LIST/UNREACHABLE/UNCONFIGURED
  four-way accounting sound.

`state/workorders.json` was searched for every module name before writing anything; the only
hits are the SWEEP61/SWEEP63 question bundles (already-known carried QUESTIONs, not defects) and
unrelated cross-cutting orders (`BATTERY_IS_THE_ONLY_CALLER...`, `PRIMARY_HOST_ONLY_EVER_FANDOM`).
Nothing in this batch's scope has an open work order that a fresh read would duplicate.

## Findings

### 1. RESOLVED (was SUSPECTED in sweep64 batch04) — `mutate.py`'s ordinary sandbox teardown now
unlinks junctions before `rmtree`, closing last cycle's finding.

sweep64 batch04 filed: `_run_mutation`'s `finally` (then at mutate.py:2540-2542) and `main()`'s
`finally` (then at mutate.py:3218-3220) called a bare `shutil.rmtree(root, ignore_errors=True)`
over the sandbox root, which holds live junctions into `output/raw`, `output/index`, `prompts`,
`reference` and every top-level `data/<dir>` — while `reap_orphans()` and `drill.py`'s
`_remove_scratch_tree()` unlink those junctions explicitly first, with a comment claiming this
was "the ONE PLACE in the project" where that mattered.

Verified fixed this cycle. A new function, `_remove_sandbox(root)` (mutate.py:1250-1286), now
does exactly the unlink-junctions-then-rmtree sequence `reap_orphans()` uses (unlinks
`prompts`/`reference`/`output/index`/`output/raw` via `os.rmdir` — which fails harmlessly on a
real, non-empty directory and succeeds only on a junction — then walks `data/`'s top-level
entries the same way, then `shutil.rmtree(root, ignore_errors=True)`), and its own docstring
names the sweep64 finding directly: "THE ROUTINE TEARDOWN NOW DOES WHAT THE REAPER DOES (sweep64
batch04, run #64)." Both call sites now use it: `_run_mutation`'s `finally` at mutate.py:2594-2596
and `main()`'s `finally` (via `_session`) at mutate.py:3285-3287. Traced by hand rather than
trusted from the comment — both sites read `_remove_sandbox(root)`, not a bare `rmtree`, and
`_remove_sandbox`'s body was read in full and matches the reaper's own sequence line for line.
Closing this finding; nothing further to file.

## No other findings

Beyond the item above (a fix confirmed, not a new defect), no tautological/cannot-fail check,
fail-open branch, new undisclosed cap or truncation (Hard Rule 0), wrong-variable/off-by-one/
unit-mix bug, race outside the project's documented `silence.write_json`/`replace_retry` CAS
patterns, resource leak, or comment/docstring asserting behavior the code does not have was
found in any of the eight modules. Specifically traced and confirmed sound:

- `mutate.py`: the full AST-mutation engine (`_mutations`, `_spot`/`_between`/`_token_pos`/
  `_fallback_spot`, the UTF-8 byte-vs-character column correction in `_col`); the lock's
  O_EXCL-then-token-checked acquire/release (`_lock_acquire`/`_lock_release`/`_hold_lock`); the
  BUILDING_PREFIX-then-rename sandbox-claim sequence that closes the reaper-race window (M46);
  `_owner_pid`'s 72h ownership ceiling against pid recycling; `_touch_root`'s per-mutant
  keep-alive; the differential (never-absolute) kill test in `_gate_result`, `could_not_judge`,
  and `hang_confirms_a_kill`'s two-reading hang confirmation; `_refresh_baseline`'s mid-run
  re-photograph and its two distinct drift-event shapes both handled in `_session`'s print loop;
  the live-tree-refusal guard (`root == HERE`) and the missing-baseline / ungauged-gate refusals
  in `_run_mutation`; the ruled-equivalent registry's line-keyed order-id derivation (a ruling
  cannot silently misapply itself to a mutation that moved lines — `ruling_mismatch` catches a
  same-line collision); the shutil.rmtree at sandbox():1617, which fires before any junction is
  created (only `root/src` exists at that point) and is therefore safe unlike the two sites
  above it used to be.
- `completeness.py`: `work()`'s three-way split (no_denominator / genuine-absence-now-unreliable
  / existing-but-zero) and the `if n is not None` vs `if n` distinction for a `pages: 0` answer;
  `land()`'s three-outcome verdict (`True`/`False`/`SKIPPED_ONLY`) and its shrink-floor guard;
  the `wiki_host`/sentinel filtering that keeps `pages:`/`doc:` provenance markers and `None`
  hosts out of the network path.
- `secondopinion.py`: `ran_clean()` cannot be vacuously true (`run()` always populates all three
  tool keys); `_ruff`/`_vulture`/`_detect_secrets`'s returncode handling matches each tool's real
  exit-code contract (ruff 0/1, vulture 0/1/3, detect-secrets rc!=0 as failure); the
  before/after tree-fingerprint guard in `report()` that refuses `--file-orders` when the tree
  moved mid-scan.
- `canon_backup.py`: `members()`'s strict refusal on any missing canonical path; `snapshot()`'s
  read-back verification (re-opens the just-written zip, re-hashes every member); `verify()`'s
  archive-vs-manifest-vs-live three-way comparison including the `unreadable`-is-not-`changed`
  split and the `absent`/`extra` membership check; `restore()`'s open-source-before-truncate
  ordering and checked `replace_retry` verdict.
- `cleanup.py`: confirmed (again) that this module performs no filesystem deletion — its most
  destructive action is flipping `catalogued` to `False` with an `excluded` reason, consistent
  with the standing Question 1 from sweep64 batch13; `_ruby_question_mark`/`_ruby_parenthetical`'s
  non-ASCII guards and `clean_ceiling`'s exact/head/single-prefix-only resolution ladder
  (refusing to guess on `prefix-ambiguous`) are sound.
- `catalogue_models.py`: the LISTED/EMPTY_LIST/UNREACHABLE/UNCONFIGURED four-way outcome and its
  propagation into `live`/`unverified`/`verified` counting (EMPTY_LIST correctly counted as
  verified-and-live, not dropped as unreachable); `LAST_WRITE_LANDED`'s three-state (None/False/
  True) contract and honest `None` default.
- `tuning.py`: `regime()`/`profile()`'s `_CACHE["buckets"]` coupling (the worker count and the
  regime label always come from the same caching moment); `workers()`'s "zero is a request, not
  an absence" fix (`requested is not None`, not `if requested`); `cloud_success_rate`'s
  `MIN_CALLS_TO_JUDGE` floor against noise.
- `lognames.py`: a small, static constants module; no logic to fault.

## Questions (not findings)

Both carried forward from sweep64/sweep63/sweep61, not re-argued:

1. **`cleanup.py`'s brief premise.** Any future brief text asserting "cleanup.py can delete
   files" should be corrected — it cannot (see above). Still true this cycle.
2. **`canon_backup.py:274`**, `prune()`'s `for f in snaps[:-keep] if keep > 0 else []` still
   silently no-ops on `--keep 0` or a negative `--keep` rather than refusing or warning. Not
   exploitable under the current default (`KEEP = 7`). Still true, still undocumented, still not
   worth a fix on its own.

## Coverage recorded

Recorded via `sweep_plan.record('run65', ['mutate.py', 'completeness.py', 'secondopinion.py',
'canon_backup.py', 'cleanup.py', 'catalogue_models.py', 'tuning.py', 'lognames.py'], batch=4)`.
