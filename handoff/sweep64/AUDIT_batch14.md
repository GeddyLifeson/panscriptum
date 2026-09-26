# sweep64 batch14 — audit report

Scope, read in full, start to finish, sequentially, no sampling:

| module | lines |
|---|---|
| src/hostcheck.py    | 1735 |
| src/health.py       | 1319 |
| src/liveness.py     | 1089 |
| src/weave.py        |  709 |
| src/tiers.py        |  555 |
| src/coverage.py     |  456 |
| src/cosmography.py  |  375 |
| src/entity_match.py |  319 |

Total 6,557 lines across 8 modules, every line read with the Read tool. Read-only: nothing under
`src/`, `data/`, `state/`, or `output/` was edited or created except this file and the coverage
record. No drill.py, verify_math.py, generate.py, pipeline, publish, mutate, or hostcheck job was
run. No subagents were spawned.

## Method

CLAUDE.md read first for doctrine (Hard Rule -1 escalation/halt chain, Hard Rule 0 no-caps,
fail-closed doctrine, "a check that cannot fail looks exactly like a check that passed").

`handoff/sweep63/` was grepped for all eight module names before reading code, and every
overlapping prior audit was read in full before starting:

- `sweep63/AUDIT_batch14.md` — same batch number, four of the same modules (hostcheck.py,
  health.py, liveness.py, tiers.py; that run's other four were cleanup.py, sweep.py, tells.py,
  which are not in this batch). Zero VERIFIED, zero SUSPECTED findings filed; two sweep61 items
  (liveness.py's `_function_line_ranges` bare-name collision, hostcheck.py's `probe()`
  per-page-not-per-name undercount) were confirmed fixed. One QUESTION carried: `liveness.py`'s
  `DECLARED_UNREACHABLE` lookup silently excuses nothing (rather than flagging staleness) when a
  ruled function name is a typo or has been renamed — filed as a documentation gap, safe direction
  (it only ever *removes* an excuse, never grants a false one).
- `sweep63/AUDIT_batch05.md` — covered `coverage.py` in full. Zero findings; `state_of()`'s
  six-way precedence ladder specifically traced and confirmed sound.
- `sweep63/AUDIT_batch13.md` — covered `cosmography.py` in full. Zero findings against it (the
  batch's one SUSPECTED finding was in `citecheck.py`, out of this batch's scope).
- `sweep63/AUDIT_batch16.md` — covered `entity_match.py` in full. Zero findings against it
  (`qualifier_compatible()`'s absolute gate, `similarity()`'s max-of-two-measures, the
  STRONG/WEAK raised-at-import ordering, and `candidates()`'s two early-exit dict shapes were all
  specifically re-traced and held).

This batch's own eight modules were then read fresh against the source, not taken on the prior
sweep's word, checking specifically for: fail-open branches, tautological/unfalsifiable checks,
Hard Rule 0 caps/truncations, off-by-one/race/inverted-condition bugs, comments asserting behavior
the code does not have, regex/escape corruption, and silent exception swallowing that manufactures
a false negative.

## Findings

**0 VERIFIED. 0 SUSPECTED (new). 1 QUESTION (carried forward, not re-argued).**

This is, as both sweep61 and sweep63 also concluded, one of the most heavily self-audited
stretches of this codebase. Essentially every non-trivial branch carries its own paragraph naming
the exact defect it was written to close, the order id, and (frequently) a reproduced before/after
measurement. Reading start to finish did not surface a new instance of any of the classes named in
the brief. Specific load-bearing logic traced by hand rather than taken on the module's own word:

- **hostcheck.py**: `probe()`'s API-branch hop-following (bounded against redirect cycles,
  counts hits per *probed name* not per returned page — sweep61 batch14's fix, still in place and
  correct); `null_rate()`'s cache key (host, exclude, sample, tuple(foreign)) and its `None`-vs-`0.0`
  handling for an unmeasured control; `score()`'s full verdict ladder including the
  `about is None and about_n == 0` vs `about_n is None` distinction (traced against every return
  path of `relevance()` — `about_n` is only ever `None` on the domain-named short-circuit, which
  always pairs with `about == 1.0`, so the `about is None` branch can never silently see a `None`
  `about_n`); `sweep(--repair)`'s lift-based selection and `_land_hosts`'s compare-and-swap
  (digest-before-read, absent-file refusal, no-op-merge-must-not-write guard) all check out.
- **health.py**: `_flush_ledger`/`_flush_samples`'s compare-and-swap and preserve-the-wreck
  branches; `flush()`'s thread-local re-entrancy guard; `check_api_paths`'s registered-domain
  family bucketing plus quarantine exemption; `check_caches`'s quarantine/exclusion/25-file-floor
  logic (traced the interaction of the three exemptions — quarantine, roll-exclusion, and the
  small-and-empty floor — against each other; they compose without a gap); `reopen_stranded`'s
  re-read-before-write compare-and-swap. All sound.
- **liveness.py**: `_credit_attrs`/`_scope_aliases`'s per-function alias scoping (the
  `resonance`-vs-`roll` `R` collision this was built to avoid does not recur); the DEAD/DEAD_CLASS/
  PHANTOM passes' four-set membership tests; `reachability()`'s subprocess-isolated coverage
  measurement (avoiding the `src/coverage.py` name shadow) and its fail-closed error returns.
- **weave.py**: `components()`'s complete-linkage agglomeration and its `threshold <= 0` refusal;
  `surprisal_pair_weights`'s uncapped shared-evidence lists; `null_threshold_surprisal`'s
  `NullThresholdUnmeasured` distinction from a genuine zero median.
- **tiers.py**: the `CUTS`/`MULTIVERSE_THRESHOLD` raised (not asserted) invariants; the
  `split_sources` containment scan (traced why skipping sources with no xenoverse cannot hide a
  real multiverse/metaverse split — any multi-member multiverse group is a complete-linkage clique
  at a threshold higher than the metaverse/xenoverse thresholds, so every member of such a group is
  guaranteed to have a non-`None` metaverse and xenoverse value already; the skip only ever excludes
  singletons that cannot violate the check); the grounding-derived vs. link-graph hyperverse kept as
  two clearly-separated, correctly-labeled measurements.
- **coverage.py**: `state_of()`'s CITED > READ > NO PAGE > UNREACHABLE > NOT ATTEMPTED precedence
  ladder traced through every combination of arrival order across two candidate paths — a later
  weaker state can never downgrade an established stronger one in any order tested; `_empty_state`'s
  transport-stamp-vs-legacy-record split; the classifier-version cache-invalidation key.
- **cosmography.py**: `validate()`'s two independent ceiling checks (the in-census Kardashev ratio
  ceilings and the absolute `SIZE_CLASS_MAX_GALAXIES` category ceiling) and why the ratio checks
  alone could not have caught the POCKET/MINOR incident the module's own history describes;
  `kardashev_to_magnitude`'s `None`-for-no-admissible-band fix.
- **entity_match.py**: `qualifier_compatible()`'s absolute gate; `candidates()`'s two early-exit
  paths (both now correctly return `dict` with `blocked_by_qualifier: {}`, not the historical
  list/dict mismatch); the `STRONG`/`WEAK` raised-not-asserted ordering check.

No tautology, no fail-open guard, no new Hard-Rule-0 cap/truncation, no off-by-one/unit-mix/race,
and no regex/escape corruption was found in any of the eight modules beyond what each module's own
in-line history already records as found-and-fixed.

## Questions

1. **`liveness.py:984-991`, `reachability()`'s `DECLARED_UNREACHABLE` lookup** — carried forward
   from sweep63, not re-argued, still open, still not a finding. If a name in
   `DECLARED_UNREACHABLE[module]` matches no def at all (a typo, or a function since renamed or
   removed), the loop takes neither the `ambiguous` branch nor the `span` branch — it silently
   contributes nothing to `declared_lines`, so the lines that ruling used to cover simply reappear
   in `unreached_undeclared` and get reported as fresh gaps rather than the tool saying outright
   "declared function `X` not found in `escalation.py`". This fails in the safe direction (a stale
   ruling can only stop excusing something, never grant a false excuse), which is why it is not
   filed as a defect. Still worth an explicit "declared but not found" row if the owner wants
   staleness here to be as loud as it is everywhere else in this file's own doctrine.

No other design questions arose in this batch that were not already answered by the modules' own
doctrine comments.

## Coverage recorded

Ran `sweep_plan.record('run64', ['hostcheck.py', 'health.py', 'liveness.py', 'weave.py',
'tiers.py', 'coverage.py', 'cosmography.py', 'entity_match.py'], batch=14)` from the kit directory.
