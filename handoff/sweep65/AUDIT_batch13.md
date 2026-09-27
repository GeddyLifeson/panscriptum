# sweep65 batch 13 — audit

## Scope

Read in full, start to finish, sequentially with the Read tool (offset/limit chunks for the
larger files), no sampling and no grep-driven skimming. Line counts from `wc -l` at time of
reading:

- `src/assay.py`           1949 lines — read in 4 chunks (1-500, 501-1000, 1001-1500, 1501-1949)
- `src/silence.py`         1313 lines — read in 3 chunks (1-450, 450-900, 900-1313)
- `src/allsweep.py`        1029 lines — read in 3 chunks (1-450, 450-900, 899-1029)
- `src/address_space.py`    679 lines — read whole
- `src/address.py`          543 lines — read whole
- `src/hosts.py`            424 lines — read whole
- `src/navtree.py`          335 lines — read whole
- `src/propagation.py`      254 lines — read whole
- `src/catalog.py`          167 lines — read whole

Total 6,693 lines across 9 modules, all read completely. Read-only throughout: nothing under
`src/`, `data/`, `state/`, `output/`, `prompts/` or `reference/` was edited, created or deleted,
and nothing was run except the final `sweep_plan.record()` call this batch was instructed to
make.

## Method and prior-audit cross-check

`CLAUDE.md` and `handoff/sweep65/BRIEF.md` were read first. This exact nine-module combination
has not been audited together as one batch before, but every one of the nine modules individually
has an extremely deep prior-sweep history — `assay.py`, `silence.py`, `allsweep.py`, `address.py`,
`address_space.py`, `hosts.py`, `navtree.py`, `propagation.py` and `catalog.py` each appear in
40-140+ prior `AUDIT_batchNN.md` files going back to sweep22. `handoff/sweep64/AUDIT_batch13.md`
(same batch number, previous run, different module set that overlapped on `assay.py` and
`silence.py`) recorded 0 VERIFIED/SUSPECTED findings against both.

`state/workorders.json` (56 open orders) was grepped for all nine module names before writing
anything. Relevant open orders found, all pre-existing and none re-filed here:

- `3fb312a72435` (sweep35, OWNER) — `hosts.py` has no caller anywhere in `src/` despite being a
  complete, working module with real data (`data/SOURCE_HOSTS.json`) on disk. Confirmed still
  true by this read (nothing in the other 8 modules or elsewhere imports it). Deletion-vs-wiring
  is the owner's call; not re-filed.
- `7354d54f0e27` (sweep60/61, OWNER, INFO) — `address_space.citation_card()` has zero callers;
  the dangerous half (missing `uncharted=` passthrough) was already repaired, the remaining
  question (delete the dead function or keep it) is left for a ruling.
- `5bb12b398783` (sweep54, OWNER) item 5 — `navtree.py` (and `rosetta.py`) write outside
  `output/`/`state/` (`data/NAVTREE.json`) without calling `escalation.assert_clear()` first.
  Confirmed still true by this read: `navtree.main()`'s `--write` path calls `silence.write_json`
  directly with no halt check. Already an open OWNER question; not re-filed.
- `a724ec57e0d5` (long-running OWNER ruling question, most recently re-read sweep58) —
  `thread_integrity`'s DANGLING verdict is computed and printed but not escalated, and the
  `allsweep.py`-side half (an RC_FINDINGS row's tail is suppressed by `allsweep.py:329`/`:720`,
  so a nonzero DANGLING count would be invisible in the sweep's own console output) is confirmed
  still present in `allsweep.py:399` (`failed = bool(crashed or (rc!=0 and rc_means==RC_BROKEN and
  not refused))`) and `:853` (`if r.get("failed") or r["crashed"] or r.get("timeout")`). Already
  filed and repeatedly re-read as a ruling question; not re-filed.
- `d2f103634cf1` (sweep64, OWNER) item 6 mentions `assay.py:908` (now shifted to 909) only as an
  example of `mutate.py`'s ruling-keying scheme going stale on unrelated line moves — not a defect
  in `assay.py` itself.
- `7099a092abd3` / `a66423722e45` — dead-code-retention and export-scratch-copy orders that name
  `assay.py` only as one example among many; both already ruled on (kept, not deleted) and not
  about a live defect.

No other order in the queue names any function or line inside this batch's nine files.

## Findings

**0 CONFIRMED. 0 SUSPECTED (new).**

Every non-obvious branch in all nine files carries its own paragraph naming the specific defect
it was written to close (an order ID, and usually a live measurement proving the fix), which is
the house style this whole tree has converged on after 64 prior sweeps. I read every line looking
for a defect the code's own comments do not already name, hand-traced the load-bearing logic
below rather than trusting the comments, and did not find one:

- **`assay.py`**: `axis_score()`'s ordering (structural refusals — off-Ladder band, non-energetic
  axis, misspelt axis — decided before the quantity is even looked at) and its below-floor clamp
  applying identically on the M10 top rung; `_check_constants()`'s BAND_EDGES completeness/
  monotonicity/half-extension checks, the WEIGHTS/BAND_EDGES/NON_ENERGETIC_AXES three-way
  partition (disjoint, exhaustive — 5 axes with floors + 6 without = 11), and the
  ATTESTATION_FLOOR/SIGMA_BY_ATTESTATION monotonicity checks, all hand-verified against the live
  tables; `_interval()`'s covariance loop running over `applicable` (not just `used`, which is
  the exact fix a prior regression made necessary) and the variance floor at zero; `assay()`'s
  `used`/`nil` construction (mutually exclusive by construction — a numeric value can never equal
  the `NONE` string sentinel), the `wsum <= 0.0` refusal firing before the `denom` division can
  ever divide by zero given `_check_weights` already refuses negative weights, and the
  ceiling/floor clamp on the printed decimal matching the 2-decimal rounding boundary
  (`>= 0.995`) rather than the raw `>= 1.0`/`< 0.0` band edge; `instrument()`'s `_reading()`
  sentinel-to-None mapping (no longer raises out of its own arithmetic on INAPPLICABLE/
  UNESTIMABLE/NONE) and the `max(1, min(30, ...))` double-ended faculty clamp;
  `interval_from_hands()`'s coverage-widening loop (traced against the "unrecognised Hand"/
  "unrecognised attestation grade" paths, both additive and neither a refusal).
- **`silence.py`**: `_handler_is_observed()`'s AST-based re-raise detection and the
  `_OBSERVED_RX` word-boundary matching (not substring); `_block_reaches_sink()`'s taint
  propagation through `Assign`/`AugAssign`/`AnnAssign` and its recursion into nested
  `If`/`For`/`While`/`With`/`Try` suites, and `_stmts_after()`'s "rest of this suite + rest of
  every enclosing suite" walk, traced by hand for a `Try` nested inside an enclosing suite;
  `write_json`/`replace_retry`/`replace_if_unchanged`'s atomic-write and compare-and-swap
  discipline (pid+thread-unique temp names, digest re-read immediately before each replace
  attempt, `PermissionError` vs. other `OSError` given different ledger classes, `UNREADABLE`
  kept distinct from an absent-file `None`); `append_line()`'s Windows-specific O_APPEND-is-not-
  atomic repair (byte-range lock plus `O_BINARY`) and the "note recorded only after the write
  succeeds, not inside the lock-acquisition except" ordering.
- **`allsweep.py`**: `run_verifier()`'s `failed` grading (crash, or `rc_means==RC_BROKEN` and
  non-refused nonzero rc; an RC_FINDINGS row's nonzero rc does NOT set `failed`, which is the
  documented and already-filed-as-a-question behaviour for `thread_integrity`, not a new
  defect); `check_import()`'s halt-refusal / traceback-absent / SystemExit-message three-way
  branch, confirmed each arm is reachable and distinct; `reconcile()`'s `_band()` ordinal
  comparison for the "entry banded above its own source's ceiling" check, and the uncapped
  `examples` collection (no `[:6]` cutting off the underlying list, only the console `_head()`
  preview does); `estate_faults()`/`_row_is_fault()`'s fail-closed default (a row with no `bad`
  key counts as a fault); the final `bad` count summing all five graded tiers (imports, verifiers,
  lint, estate artifacts, estate findings) plus a denied-report-write, with RECONCILE correctly
  excluded and stated as ungraded rather than silently summed.
- **`address.py`**: `spine_code_for()`'s four-stage matcher (exact code lookup → normalized
  letter-equality → most-specific-wins substring containment with the opens/closes-and-remainder
  exception → word-overlap-coverage fallback requiring a 2-token overlap or an identical token
  set), hand-traced against the documented false-positive reproductions (`Sword Coast
  Adventurer's Guide DC Edition`, `Halo Fan Documentary About Nothing`) to confirm each is
  correctly refused to `UNASSIGNED` rather than mis-shelved; `promote()`'s promotion-only
  (never-demotion) asymmetry and its repair of an unrankable `current` tier.
- **`address_space.py`**: `_bits()`/`FIELDS`/`WIDTHS`/`TOTAL_BITS` derivation from `_tier_counts()`
  and `cosmography`, confirmed no field can be zero-width (`max(2, ...)` floor); `pack()`/
  `unpack()` round-trip via keyword-only fields; `assign()`'s `fit()` (None→0 for an unaddressed
  tier, real out-of-range values reaching `pack()`'s own raise rather than wrapping) and
  `_hash_offsets()`'s derived-not-hardcoded bit offsets for the four hash-drawn fields, confirmed
  they cannot overlap under the current census; `shelfmark()`'s per-field `uncharted` blanking
  and `charted_gaps()`'s "tier is UNADDRESSED, not merely charted zero" distinction.
- **`hosts.py`**: `_load()`'s absent-vs-corrupt distinction (FileNotFoundError returns the
  default, any other exception raises); `add()`'s three-state return (`True`/`False`/`None`) and
  its read-digest-before-write compare-and-swap retry loop; `discover()`'s thin-roster /
  probe-failed / kept three-way classification, all uncapped and each counted under its own name
  rather than folded into a bare drop.
- **`navtree.py`**: `build()`'s "sources first, so a branch exists even where nothing is
  catalogued yet" ordering; `register_for()`'s and the hyperverse-naming loop's hash-order tie
  breaks, both resolved deterministically by a secondary key (`(count, name)`); `sources_under()`'s
  `+ "."` boundary fix so a sibling branch sharing a numeric prefix (e.g. `0.1.2` vs `0.1.20`)
  cannot vote in the wrong node's naming ballot; `audit()`'s child-sum-vs-claimed-count check and
  its own fail-safe against a dangling child key.
- **`propagation.py`**: `observed_mark()`'s two-clock model (vertical ascension independent of
  lateral distance) and the "trailing `return 0` is unreachable because rung 1's
  `ascension_years` is exactly 0.0 so the loop always matches by its last iteration" claim,
  confirmed by hand-tracing the loop bounds; `shortest()`'s Dijkstra with a `seen` set guarding
  against re-processing a popped node.
- **`catalog.py`**: `load_catalog()`'s missing-file-vs-empty-catalogue distinction; `main()`'s
  `sys.exit(main())` / per-subcommand return-code discipline so a miss (`No entry for address`)
  exits 1 rather than 0.

## Questions

None new. The pre-existing open OWNER questions touching this batch's files (`hosts.py`'s
no-caller status, `navtree.py`'s missing halt check before writing `data/NAVTREE.json`,
`address_space.citation_card()`'s dead-function disposition, and the `thread_integrity`/
`allsweep.py` DANGLING-escalation ruling) are listed under "Method" above with their order IDs
rather than repeated here, per the brief's instruction not to re-file an already-open item.

## Cleared

Beyond the load-bearing logic named above, examined closely and found correct, one line each:

- `assay.py`: `band_for_quantity()`'s "refuse an axis not on BAND_EDGES before the loop can lie
  about reaching M0" guard; `calibration_report()`'s per-call `sigma=` sweep touching no shared
  state; `_attestation_sigma()`'s `min(SIGMA_MAX, raw)` clamp applying to a `sigma=` override too.
- `silence.py`: `_suppress_is_declared()`'s `contextlib.suppress` exemption-marker check;
  `_ensure_import()`'s "end of the first contiguous run of top-level imports" anchor, correctly
  avoiding a module that imports inline two hundred lines down.
- `allsweep.py`: `NEVER_RUN`'s roster is documentation only (nothing reads it as a gate, correctly
  stated in its own comment); `verifier_console_lines()`'s tail-window disclosure.
- `address.py`: `_worded()`'s space-padded boundary construction, confirmed it cannot match a
  substring mid-word.
- `address_space.py`: `HASH_BYTES` guard raising if a layout ever needed more than 32 bytes of
  SHA-256 digest.
- `hosts.py`: `coverage()`'s `with_a_host`/`with_more_than_one` counts, confirmed independent of
  `_load`'s corrupt-vs-absent distinction (both paths return a dict either way at this call site).
- `navtree.py`: `touch()`'s `nodes.setdefault` idiom, confirmed a node is created exactly once per
  key regardless of visit order (sources pass then worlds pass).
- `propagation.py`: `load_graph()`'s "keep the smaller of two recorded weights for a pair" dedup.
- `catalog.py`: `cmd_read()`'s raw-path-first-then-compressed-fallback read order.

## Coverage

Recorded via `sweep_plan.record('run65', ['assay.py', 'silence.py', 'allsweep.py',
'address_space.py', 'address.py', 'hosts.py', 'navtree.py', 'propagation.py', 'catalog.py'],
batch=13)`.
