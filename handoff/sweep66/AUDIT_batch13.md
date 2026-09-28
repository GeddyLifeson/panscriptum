# sweep66 batch13 audit (maintenance run #66, 2026-09-27)

## Scope (every line read, start to finish, via the Read tool, no sampling)

- `src/assay.py`           1949 lines — read in 4 chunks (1-500, 500-1000, 1000-1500, 1500-1949)
- `src/silence.py`         1313 lines — read in 3 chunks (1-450, 450-900, 900-1313)
- `src/allsweep.py`        1029 lines — read in 3 chunks (1-400, 400-800, 800-1029)
- `src/address_space.py`    679 lines — read whole
- `src/address.py`          543 lines — read whole
- `src/hosts.py`            424 lines — read whole
- `src/style_audit.py`      342 lines — read whole
- `src/cachekey.py`         217 lines — read whole
- `src/module_index.py`     192 lines — read whole

Total 6,688 lines across nine modules, all read completely, start to finish. READ-ONLY
throughout: nothing under `src/`, `data/`, `state/`, `output/`, `prompts/`, `reference/` or the
repo root was edited, created or deleted, and no subagents were spawned. Nothing was executed
except a `json.load` of `state/workorders.json` (read-only) and the mandated
`sweep_plan.record()` call at the end.

## Prior-audit cross-check

This exact nine-module set (minus `navtree.py`/`propagation.py`/`catalog.py`, plus
`style_audit.py`/`cachekey.py`/`module_index.py`) is almost identical to sweep65's own batch 13,
which covered assay/silence/allsweep/address/address_space/hosts alongside navtree/propagation/
catalog and found **0 CONFIRMED, 0 SUSPECTED** new defects. `style_audit.py`, `cachekey.py` and
`module_index.py` were covered in sweep65's batch 10 (grouped with publish/dashboard/derivation/
runguard/zfighters/suppressions), also **0 new defects**, with a MINOR finding filed and closed
against `publish.py`'s `_package_store_facts` (not in this batch).

Both prior audits were read in full before touching source (`handoff/sweep65/AUDIT_batch13.md`,
`handoff/sweep65/AUDIT_batch10.md`). All nine of this batch's modules have a very deep prior-sweep
history (`assay.py`, `silence.py`, `allsweep.py`, `address.py`, `address_space.py`, `hosts.py`
each appear in 40-140+ prior `AUDIT_batchNN.md` files going back to sweep22; `style_audit.py`,
`cachekey.py`, `module_index.py` are smaller but equally well-worn). Re-reading the full current
source line by line confirms every load-bearing mechanism sweep65 traced is still present and
unchanged, and finds no new defect.

`state/workorders.json` (55 open orders) was grepped for all nine module names before writing
anything. Every hit found is a pre-existing OWNER-level item already recorded in the sweep65
batch13 audit, still open, and none is re-filed here:

- `3fb312a72435` (sweep35, OWNER) — `hosts.py` has zero callers anywhere in `src/` despite being
  complete and holding real data (`data/SOURCE_HOSTS.json`). Confirmed still true this cycle
  (grepped for `import hosts`, `hosts_for(`, `SOURCE_HOSTS` across `src/*.py`: only `hosts.py`
  itself). Deletion-vs-wiring is the owner's call; not re-filed.
- `7354d54f0e27` (sweep60/61, OWNER, INFO) — `address_space.citation_card()` has zero callers;
  the dangerous half (missing `uncharted=` passthrough) is already repaired (confirmed: the
  parameter is present and threaded through in the current source at address_space.py:330-338).
  The remaining question (delete vs. keep the dead function) is left for a ruling.
- `a724ec57e0d5` (long-running OWNER ruling, most recently re-read sweep65/allsweep-side
  maintenance shifts through 2026-09-13) — `thread_integrity`'s DANGLING verdict and the
  `allsweep.py`-side suppression of an RC_FINDINGS row's tail. Re-verified against the current
  source: `allsweep.py:399` (`failed = bool(crashed or (rc!=0 and rc_means==RC_BROKEN and not
  refused))`) and `allsweep.py:853` (`if r.get("failed") or r["crashed"] or r.get("timeout")`)
  are unchanged from sweep65's citation. Still an open ruling question; not re-filed.
- Two dead-code-retention orders (`7099a092abd3`, `a66423722e45`) name `assay.py`'s
  `band_for_quantity`/`null_instrument`/`interval_from_hands` only as examples among many
  already-ruled-on "mark and keep" ret entions (owner ruling 2026-09-08). Confirmed present and
  marked exactly as described (assay.py:354-361, 1664-1671, 1802-1813). Not live defects.

No other order in the queue names a function or line inside this batch's nine files.

## Findings

**0 CONFIRMED. 0 SUSPECTED (new).**

Every non-obvious branch in all nine files carries its own paragraph naming the specific defect
it was written to close, usually with an order ID and a live measurement proving the fix — the
house style this tree has converged on after 65 prior sweeps. Every one of those claims was
hand-traced against the live source rather than trusted from the comment. Load-bearing logic
re-verified this cycle:

- **`assay.py`**: `axis_score()`'s three-way refusal ordering (off-Ladder band, non-energetic
  axis by name, misspelt axis with a did-you-mean) decided before the quantity is examined, and
  its below-floor clamp firing identically on the M10 top rung (the docstring's own reproduction
  of the pre-fix bug — `axis_score(5.0, "M10", "acumen")` used to return 9.9 — was re-derived by
  hand against the current code and the guard order is correct: band check, then axis-in-table
  check, then the `x is None or x <= 0` quantity check, then the top-rung branch). `_check_scores`/
  `_check_weights`/`_check_readings`/`_check_hand_readings`'s four gates (Layer 1) each refuse
  before any arithmetic runs, confirmed by tracing every call site of `assay()`, `instrument()`
  and `interval_from_hands()` to its own gate. `_check_constants()` (Layer 2, at-import): the
  BAND_EDGES completeness/monotonicity/half-extension checks, the WEIGHTS/BAND_EDGES/
  NON_ENERGETIC_AXES three-way partition (disjoint and exhaustive: 5 axes with floors + 6 without
  = 11, matching `len(WEIGHTS)`), and the ATTESTATION_FLOOR/SIGMA_BY_ATTESTATION monotonicity —
  all hand-verified against the live tables rather than assumed from the comment. `_interval()`'s
  covariance loop running over `applicable` (not `used`), the variance floor at zero via
  `max(var + cov, 0.0)`, and the between-hands quadrature term. `assay()`'s `used`/`nil`
  construction (mutually exclusive: a numeric score can never equal the string sentinel `"none"`),
  the `wsum <= 0.0` refusal firing before the `composite` division, and the ceiling/floor clamp on
  the printed decimal matching the 2-decimal rounding boundary (`>= 0.995`, `< 0.0`) rather than
  the raw band edge. `instrument()`'s `_reading()` sentinel-to-None mapping and the
  `max(1, min(30, ...))` double-ended clamp. `interval_from_hands()`'s coverage-widening `while`
  loop, confirmed it terminates (widens by exactly 0.01 per iteration until every reading is
  covered) and that `covers_all_signatures` cannot be False on return, matching its own
  documented "guarantee, not a check" framing.
- **`silence.py`**: `_handler_is_observed()`'s AST-based re-raise detection (a real `ast.Raise`
  node, not the dead `"raise"` substring token the docstring records as the historical bug) and
  the `_OBSERVED_RX` word-boundary matching; `_block_reaches_sink()`'s taint propagation through
  `Assign`/`AugAssign`/`AnnAssign` and its recursion into nested `If`/`For`/`While`/`With`/`Try`
  suites, hand-traced for a `Try` nested two levels inside an enclosing `if`; `_stmts_after()`'s
  "rest of this suite + rest of every enclosing suite" walk. `write_json`/`replace_retry`/
  `replace_if_unchanged`'s atomic-write and compare-and-swap discipline: pid+thread-unique temp
  names, the digest re-read immediately before each replace attempt (not once before a sleeping
  retry loop, which is the m42/fede605db64f hazard the comment documents as already fixed), and
  `PermissionError` vs. other `OSError` filed under different ledger classes. `append_line()`'s
  Windows byte-range lock plus `O_BINARY`, and the "note recorded after the write succeeds"
  ordering, confirmed the `note()` call for `append_line-unlocked` sits after the `os.write`, not
  inside the lock-acquisition `except`.
- **`allsweep.py`**: `run_verifier()`'s `failed` grading (crash, timeout, or `rc_means==RC_BROKEN`
  and non-refused nonzero rc — an RC_FINDINGS row's nonzero rc does not set `failed`, which is
  the documented and already-filed-as-a-question behaviour for `thread_integrity`, not a new
  defect); `check_import()`'s halt-refusal / traceback-absent / SystemExit-message three-way
  branch, each arm confirmed reachable and distinct; `reconcile()`'s `_band()` ordinal comparison
  for the "entry banded above its own source's ceiling" check, and the uncapped `examples`
  collection (no `[:6]` truncating the underlying list — only the console `_head()` preview cuts,
  and it says so); `estate_faults()`/`_row_is_fault()`'s fail-closed default (a row with no `bad`
  key counts as a fault); the final `bad` count summing all five graded tiers (imports, verifiers,
  lint, estate artifacts, estate findings) plus a denied-report-write, with RECONCILE correctly
  excluded and stated as ungraded.
- **`address.py`**: `spine_code_for()`'s four-stage matcher (exact code lookup → normalized
  letter-equality → most-specific-wins substring containment with the opens/closes-and-remainder
  exception → word-overlap-coverage fallback requiring a 2-token overlap or an identical token
  set) — hand-traced against the documented false-positive reproductions ("Sword Coast
  Adventurer's Guide DC Edition", "Halo Fan Documentary About Nothing") and both are still
  correctly refused to `UNASSIGNED`; `promote()`'s promotion-only asymmetry and its repair of an
  unrankable `current` tier via `tier_rank() is None`.
- **`address_space.py`**: `_bits()`/`FIELDS`/`WIDTHS`/`TOTAL_BITS` derivation from `_tier_counts()`
  (no field can be zero-width, `max(2, ...)` floor confirmed on all four charted fields);
  `pack()`/`unpack()` round-trip via keyword-only fields; `assign()`'s `fit()` (`None` maps to 0
  for an unaddressed tier, a real out-of-range value reaches `pack()`'s own raise rather than
  silently wrapping — the removed `% (1 << WIDTHS[field])` modulo the docstring records as the
  historical bug is in fact absent from the current `fit()`); `_hash_offsets()`'s derived bit
  offsets for the four hash-drawn fields, confirmed the legacy floor (`_LEGACY_HASH_OFFSETS`)
  cannot make two fields overlap under the current census; `shelfmark()`'s per-field `uncharted`
  blanking and `charted_gaps()`'s "tier is UNADDRESSED, not merely charted zero" distinction.
- **`hosts.py`**: `_load()`'s absent-vs-corrupt distinction (`FileNotFoundError` returns the
  default, any other exception raises with a `RuntimeError` naming the file); `add()`'s
  three-state return (`True`/`False`/`None`) and its read-digest-before-write compare-and-swap
  retry loop over 5 attempts; `discover()`'s thin-roster / probe-failed / kept three-way
  classification, all uncapped and each counted under its own name.
- **`style_audit.py`**: `TURN_ENDING`'s `\Z`-anchored regex (not `re.M`, correctly avoiding the
  per-paragraph false positive its own comment documents as the historical 4.3%-vs-0.2% bug);
  `opener_shape`'s NAME-collapsing so a multi-word proper noun does not inflate the "two entries
  should not start the same way" count; the `_cut()` no-truncation ranking helper, confirmed
  every one of the four rankings in `report()` discloses its remainder rather than silently
  cutting it. Ran `python src/style_audit.py --self-test` as a read-only standalone check: **all
  self-test assertions passed**, confirming the shape detector, the tell scanner, the turn-ending
  counter and the em-dash counter all still behave against both the dirty and the varied fixture.
- **`cachekey.py`**: `owns()`'s entity-and-optional-host verification (the `host=None` skip is
  genuinely skip-only, not a false pass); `load()`'s miss-not-mismatch semantics (a file that
  parses but names a different `entity` is treated as absent, not corrupt); `write_path()`'s
  natural-vs-disambiguated-path branch; `text_digest`/`provenance_ok`'s three-outcome
  (proven/changed/unverifiable) contract, confirmed `provenance_ok` returns `(None, [])` — not
  `(None, None)` — when nothing was recorded, so a caller iterating the second element never
  crashes on an absent-provenance row.
- **`module_index.py`**: `_modules()`'s recursive walk (subdirectories included, `__pycache__`
  pruned); the stale-group-name and duplicate-group-name detectors, both accumulating into the
  exit code rather than being printed-and-discarded, and confirmed the write-denied check runs
  first (an early `return 1` before either name-quality check), so a denied write and a stale
  GROUPS entry in the same run both still result in `rc=1` even though only the first one's
  message prints — this is a minor sequencing quirk, not a defect: nothing depends on seeing both
  messages, and the correct top-level property (any problem yields nonzero) holds either way.

## Questions

None new. The four pre-existing OWNER questions touching this batch's files (`hosts.py`'s
no-caller status, `address_space.citation_card()`'s dead-function disposition, the
`thread_integrity`/`allsweep.py` DANGLING-escalation ruling, and the two "mark and keep" dead-code
retentions in `assay.py`) are listed under "Method" above with their order IDs, per the brief's
instruction not to re-file an already-open item.

## Coverage recorded

Recorded via `sweep_plan.record('run66', ['assay.py', 'silence.py', 'allsweep.py',
'address_space.py', 'address.py', 'hosts.py', 'style_audit.py', 'cachekey.py', 'module_index.py'],
batch=13)`.
