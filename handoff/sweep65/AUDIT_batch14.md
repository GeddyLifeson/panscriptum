# sweep65 batch14 — audit report

## Scope

Every module read in full, start to finish, sequentially, via the Read tool in chunks (large files
split into two or three reads with no gap between offsets), no sampling and no grep-driven
skimming. Line counts from `wc -l` at time of reading:

| module          | lines |
|-----------------|------:|
| src/hostcheck.py | 1735 |
| src/health.py    | 1319 |
| src/liveness.py  | 1089 |
| src/weave.py     |  709 |
| src/anchors.py   |  576 |
| src/coverage.py  |  456 |
| src/sweep.py     |  374 |
| src/roll.py      |  313 |

Total 6,571 lines across 8 modules, all read completely.

READ-ONLY throughout: nothing under `src/`, `data/`, `state/`, `output/`, `prompts/`, `reference/`
or the repo root was edited or created, other than this file and the `sweep_plan.record()` call at
the end. No `generate.py`, `pipeline.py`, `publish.py`, the crawl, `overnight.py`, `foreman.py`,
`mutate.py`, `drill.py`, or `verify_math.py` was run. No `escalation` halt or `prose_enabled`/
`step4_enabled` gate was touched. No subagent was spawned.

## Method and prior-audit cross-check

`CLAUDE.md` was read first (Hard Rule -1 escalation/halt chain and its three safety properties,
Hard Rule 0 no-caps/no-truncation, "a check that cannot fail looks exactly like a check that
passed"). `handoff/sweep64/` and `handoff/sweep63/` were then grepped for all eight module names
and every matching report read in full before touching source:

- `sweep64/AUDIT_batch14.md` — same batch number, five of the same eight modules (hostcheck.py,
  health.py, liveness.py, weave.py, coverage.py). Zero VERIFIED, zero SUSPECTED findings against
  any of them; one QUESTION carried forward (`liveness.py`'s `DECLARED_UNREACHABLE` lookup, below).
- `sweep64/AUDIT_batch12.md` — covered `anchors.py` and `roll.py` in full as part of a different
  eight-file grouping. Zero findings against either; two QUESTIONs filed elsewhere in that batch
  (against `pick_model.py` and `generate.py`, neither in this batch's scope).
- `sweep64/AUDIT_batch13.md` / `AUDIT_batch04.md` — covered `sweep.py` (two different sweep64
  batches, both zero findings against it).
- `sweep63/AUDIT_batch08.md`/`AUDIT_batch09.md` — covered `roll.py` under yet earlier groupings,
  zero findings.

So all eight of this batch's modules already carry a full-line sweep63/sweep64 read with no live
findings against any of them. `state/workorders.json` was searched for every module's filename
before writing anything down (`hostcheck.py`, `health.py`, `liveness.py`, `weave.py`, `sweep.py`
each have open OWNER-routed orders on file — none of them a fresh finding this batch would
duplicate; see "Open orders already covering this batch" below).

This run was done as an independent re-read rather than a rubber stamp: every function was traced
by hand against the hazards named in the brief (fail-open branches, off-by-ones, inverted
conditions, exceptions swallowed where the code claims to fail closed, guards that cannot fail,
races on shared files, Hard-Rule-0 caps/truncations, stale comments, dead branches, wrong units,
Windows breakage). It reaches the same conclusion as sweep63 and sweep64: **no new VERIFIED or
SUSPECTED defect found in any of the eight modules.**

## Findings

**0 CRITICAL. 0 MAJOR. 0 MINOR. 0 COSMETIC (new).**

This is, again, one of the most heavily self-audited stretches of this codebase — nearly every
non-trivial branch in every one of these eight files carries its own paragraph naming the specific
defect it was written to close, the order id, and often a reproduced before/after measurement.
Logic specifically traced by hand this pass, not merely taken on the comments' word:

- **hostcheck.py**: `score()`'s full verdict ladder (rate=None -> UNREACHABLE; base=None -> a
  distinct UNREACHABLE; probed<MIN_PROBE; hits<2 or lift<=LIFT_MIN; the about-veto's `about is
  None and about_n == 0` branch vs. the `about_n < ABOUT_MIN` branch, confirmed mutually exclusive
  and confirmed lift can never be `None` by the time the `lift <= LIFT_MIN` comparison runs, since
  both `rate is None` and `base is None` are handled in strictly earlier branches); `null_rate`'s
  dedupe-then-stride sampling (`uniq[::max(1, len(uniq)//sample)][:sample]`, confirmed correct at
  both `len(uniq) < sample` and `>= sample`); `probe()`'s hop-following hit counting (per probed
  name, not per returned page) and its RAW-vs-API branch, including the `fetch_raw_verdict`
  tally-based `rate: None` vs `rate: 0.0` distinction; `_land_hosts`'s compare-and-swap (digest
  before read, absent-file refusal, no-op-merge-must-not-write guard) and its post-repair
  UNFIT-file provenance stamping; `purge()`'s per-record-file accumulation (not overwritten by the
  last file) and its cache-removal accounting (`removed` vs `files`, gated on `landed`).
- **health.py**: `_flush_ledger`/`_flush_samples`'s compare-and-swap, preserve-the-wreck branch,
  and wrong-shape (non-dict) detection; `flush()`'s thread-local re-entrancy guard (confirmed
  necessary given `silence.replace_retry` -> `silence.note` -> `health.flush()` re-entry path);
  `check_api_paths`'s registered-domain family bucketing plus quarantine exemption (traced why a
  wholly-quarantined family is correctly skipped rather than probed); `check_caches`'s
  quarantine/roll-exclusion/25-file-floor triple exemption, confirmed to compose without one
  silently overriding another; `reopen_stranded`'s re-read-before-write compare-and-swap and its
  `None`-vs-`[]` return contract (verified `main()` is the only caller, so the contract cannot be
  misread by a second one).
- **liveness.py**: `_credit_attrs`/`_scope_aliases`'s per-function-scoped alias resolution (traced
  the `drill.py` `R = roll` vs `R = resonance` worked example by hand: two functions aliasing the
  same letter to two different modules do not cross-credit); the DEAD/DEAD_CLASS/PHANTOM passes'
  four-set membership tests (`used`, `used_local`, `used_by_module`, `scoped`); `reachability()`'s
  subprocess-isolated coverage measurement (confirmed it runs with `cwd=HERE`, not `SRC`, so its
  own `import coverage` cannot resolve to this project's `src/coverage.py`) and its fail-closed
  `{"error": ...}` returns on every one of the four subprocess failure points.
- **weave.py**: `components()`'s complete-linkage agglomeration, its `threshold <= 0` refusal, and
  `min_cross`'s early-exit-on-sub-threshold-value (confirmed the exact returned value below
  threshold never matters to the caller, since any value under threshold fails the same
  `m >= threshold` test regardless of which sub-threshold value was returned); `resonance_graph`'s
  BFS-per-source component sizing and isolate handling; `surprisal_pair_weights`'s uncapped
  shared-evidence lists; `null_threshold_surprisal`'s `NullThresholdUnmeasured` distinction from a
  genuine zero median.
- **anchors.py**: the `CLAIMS` table's five per-anchor tests re-traced against each anchor's actual
  `scores` dict (Skate Guy's 11-key count and zero-struck-axes claim; Sword's `_struck(a) ==
  ["volition"]`; Goku's/Yggdrasil's volition-status claims) — all hold as printed; the
  `ungraded`/`unanchored` asymmetric membership check (against `scored`, not `vals`, specifically
  so an assay refusal reads as "refused" rather than "absent from ANCHORS").
- **coverage.py**: `state_of()`'s CITED > READ > NO PAGE > UNREACHABLE > NOT ATTEMPTED precedence
  ladder re-traced through combinations of candidate-path arrival order; `_empty_state`'s
  transport-stamp-vs-legacy-record split and its explicit non-use of `pages_refused`;
  `_CLASSIFIER_VERSION` cache-invalidation gate, confirmed it discards wholesale on any mismatch
  including an unversioned (pre-existing) cache.
- **sweep.py**: `nested_run()`'s longest-consecutive-subset-chain search (confirmed it always
  returns a chain of length >= 1, so `report()`'s `chain[0]` can never index an empty list); the
  Hard-Rule-0-compliant uncapped `BIGGEST GAPS`/`REACHED BUT SILENT` listings.
- **roll.py**: `mutate()`'s digest-before-read compare-and-swap and its distinct absent-vs-unreadable
  refusals; `exclude()`'s required-note validation and its `rows`-supplied-vs-omitted branching
  (confirmed a caller-supplied `rows` no longer risks landing on the live `ROLL` path, per the
  2026-08-26 incident this function's docstring records); `update_rows`'s `seen`-vs-`ch` distinction
  (confirmed `seen.add` now runs unconditionally on a name match, so the historical "row reported
  lost when it was merely given nothing to change" bug is fixed and does not recur).

No tautology, no fail-open guard, no new Hard-Rule-0 cap/truncation, no off-by-one/unit-mix/race,
and no regex/escape corruption was found in any of the eight modules beyond what each module's own
in-line order history already records as found-and-fixed.

## Open orders already covering this batch (not re-filed)

Searched `state/workorders.json` by filename before writing anything; these are pre-existing,
still-open, OWNER-routed orders touching this batch's modules, none of them contradicted by this
read and none needing a duplicate filing:

- `1e6f99e54b25` / `21c075e5e2d6` / `3099138a82bd` (writers without a halt interlock) — `health.py`
  and `hostcheck.py` are both named as members of this class in earlier sweeps; unchanged here.
- `a8e02f3bbf76` (`HOSTCHECK_EXAMPLES_PERSISTED_CAP`) — `probe()`'s `examples` field is still
  `sorted(got)[:5]` / `found[...][:5]` in both the RAW and API branches, while `titles` carries the
  uncapped list. Confirmed still accurate against current source; already OWNER-routed, not
  re-filed.
- `5bb12b398783` / `6b59a5d4302a` (sweep54/63 owner-question bundles) — both name `health.py`/
  related files; nothing in this read contradicts either.
- `32eaec248adf` / `8b3f2911fa0c` (dandwiki 403-by-policy preflight problem) — `check_api_paths`'s
  live behavior confirmed unchanged and consistent with these orders' description.
- `a724ec57e0d5` / `d9328fe1ee38` (thread_integrity/stall-standard questions) — reference
  `sweep.py` only incidentally (as an allsweep verifier row name); not contradicted.

## Questions (possible deliberate design — not findings)

1. **Carried forward from sweep63/sweep64, unchanged** — `liveness.py:984-991`
   (`reachability()`'s `DECLARED_UNREACHABLE` handling). Re-traced this pass: if a name in
   `DECLARED_UNREACHABLE[module]` matches **no** def at all in `_function_line_ranges` (a typo, or
   a function since renamed/removed), the loop takes neither the `ambiguous` branch (`fn_name in
   ranges` is False) nor the `span` branch (`ranges.get(fn_name)` is `None`) — it silently
   contributes nothing to `declared_lines`, so those lines simply reappear in
   `unreached_undeclared` as fresh gaps rather than the tool saying outright "declared function `X`
   not found in `escalation.py`". This fails in the safe direction (a stale ruling can only stop
   excusing something, never grant a false excuse), which is why it remains a QUESTION and not a
   finding. Still true of the current source; still worth an explicit "declared but not found" row
   if the owner wants staleness here to be as loud as it is everywhere else in this file's own
   doctrine.

No other design questions arose in this batch that were not already answered by the modules' own
doctrine comments or by the open orders listed above.

## Cleared (examined closely, found correct)

- `hostcheck.py`: `_land_hosts`'s absent-vs-unreadable WIKI_HOSTS.json refusal split; `sweep()`'s
  JUDGED-verdict gating of the repair pass; `adopt()`'s whole-candidate-list scan (Wikipedia
  ranked last, never head-truncated out of consideration); `roster_audit()`'s judgeable/
  unjudgeable split and its ownership-checked (`cachekey.owns`) text reads.
- `health.py`: `check_context_budget`'s token-budget arithmetic; `check_state`'s
  `pipeline.entry_settled`-as-single-source-of-truth (no re-spelled predicate); `preflight()`'s
  stamp-write verdict gating (never silently claims a fresh stamp landed).
- `liveness.py`: `_function_line_ranges`'s qualified-name collision handling (bare name maps to
  `None` when ambiguous, never to whichever span happened to be seen last); the PHANTOM pass's
  widened test coverage (`match` guards, bare `and`/`or` statements, comprehension filters, on top
  of `if`/`while`/`assert`).
- `weave.py`: `idf_table`/`name_surprisal`'s token-based surprisal computation; `filtered_index`'s
  fail-closed `pipeline._STATBLOCK` import (raises rather than silently disabling half the filter).
- `anchors.py`: `vector_score`'s clamp to `[0, LADDER_RUNGS]`; the `collapsed`-window
  OWNER-QUESTION report (printed every run, not gated on failure).
- `coverage.py`: `_p()`'s M23 ownership-verification delegation to `cachekey.owns`; `measure()`'s
  4-attempt retry-then-fail-closed host-map read.
- `sweep.py`: `rosetta_index()`'s finer-grained-scale-wins tie-break; `STAGE_TESTS`'s
  membership-based (not count-based) nesting.
- `roll.py`: `out_of_scope()`'s reason-carrying exclusion map; `main()`'s uncapped name/reason
  printing.

## Coverage recorded

Ran `sweep_plan.record('run65', ['hostcheck.py', 'health.py', 'liveness.py', 'weave.py',
'anchors.py', 'coverage.py', 'sweep.py', 'roll.py'], batch=14)` from the kit directory via the
miniconda python, per the brief.
