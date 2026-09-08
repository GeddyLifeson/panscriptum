# Sweep 47 — Batch 04 audit

Modules read in full, every line: `src/mutate.py` (2867 lines), `src/identity.py` (727),
`src/manifest_builder.py` (637), `src/backfill.py` (449), `src/hosts.py` (396),
`src/context_budget.py` (296), `src/chord_field.py` (210), `src/lognames.py` (52).
Total 5,634 lines, matching the brief. No module or line range was skipped.

This was an audit shift against a batch that has already been through many prior sweeps
(13 open orders against `mutate.py` alone). The bulk of the work here was **verification**:
confirming each already-open order still reproduces against the current source, and reading
past those known findings for anything new. No new defect was filed. Two already-open orders
appear to be resolved by code that has landed since they were filed; both are detailed below
rather than re-filed.

## Already-open orders: verified status

### Confirmed FIXED — recommend closing

**`mutate.py` — `2461a04d8849` MUTATE_BASELINE_DOES_NOT_NAME_ITS_RED_ROWS.**
The order says `baseline()` reported only a gate signature and never which rows were red.
Current code has `_row_ids()` (extracts individual `FAILED …` / `BREACHED …` lines),
`rows_out`/`base_rows` side channels threaded through `_gate_result`, `baseline()` and
`_run_mutation`, and `_session()` prints every red row by name at launch, beside each target's
score, and after a mid-run drift (`"red at launch: %s" % rid`, `"red after the drift: %s" % rid`).
The row-identification feature this order asked for is implemented and exercised on every
run path I read. Recommend closing.

**`chord_field.py` — `7e360eaec3a6` SWEEP34_FINDING (no caller anywhere).**
Confirmed fixed. `src/rigor.py:917` now does `import chord_field as CF` and reads
`CF.ADJUDICATIONS[...]["beta_bits"]` in its MDL-audit table (`_AUDIT_ROWS`), with a
completeness check (`_unaccounted`) that warns if a new `ADJUDICATIONS` key is added to
`chord_field.py` without a matching audit row or an explicit excuse. `rigor.py`'s own comment
at the import site says so directly: "This also gives chord_field.py its first real
importer/caller in the tree (see order 7e360eaec3a6)." Recommend closing.

### Substantially mitigated, not fully closed

**`mutate.py` — `58a00e909217` MUTATION_LONG_RUN_SCORED_AN_UNKILLABLE_MUTANT_AS_KILLED.**
The order documents the 2026-09-03 confirmed false kill (a 16-hour run scoring a mutant killed
that a fresh re-attack showed survives cleanly). The current code's `--rebaseline-every`
machinery (`_refresh_baseline`, `baseline_drifts`, the `drifted`/`judged_since` bookkeeping,
`hang_confirms_a_kill`) is explicitly built and commented as the response to this exact
incident, and it now detects a moved baseline mid-run, records which verdicts were judged
under the stale photograph, and reports them as "in doubt" rather than silently keeping them
as kills. This converts the failure from silent to detected-and-reported, which is most of
what the order asks for. It does not eliminate the root cause (the sandbox still junctions
`data/` to the live tree, which is what moves under a long run) — that half is tracked
separately by the still-open `f40f701594a4` and `79d51aef8b71`. Left open per the brief;
noting the mitigation for whoever triages it next.

### Confirmed still open, reproduces as described

- `mutate.py` `fbc0930ae309` (no scratch-tree affordance for behavioural drill nets) —
  unverifiable from this batch alone since the counterpart lives in `drill.py`, not in my
  module list; nothing in `mutate.py`'s sandbox machinery provides it.
- `mutate.py` `71ae3fa7e55e` (breach read mid-edit halted the library) — the fix lives in
  `drill.py`, outside this batch.
- `mutate.py` `4f5fa3146cc4` (live-digest check escalates at OWNER for reasons that are not
  mutate's fault) — still true: `_session()` still calls
  `escalation.escalate(escalation.OWNER, "MUTATE_TOUCHED_LIVE_TREE", ...)` unconditionally
  whenever `live_file_untouched` is false, with no path for "this was a foreign edit, not
  ours." Note: the order's own line citations (`:1866`, `:2108`, `:2138`, `:2562-2570`) have
  drifted — the file has grown since it was filed and those lines now hold unrelated comments;
  the actual `live_before`/`live_after`/escalation call sites are at different lines today
  (roughly 1969, 2237, 2752-2762). The finding itself still holds; only the pinpoint has aged.
  Not re-filed as a separate order per the brief's instruction to file drift as a QUESTION only
  when it changes what a reader should do — here it doesn't; flagging for whoever next edits
  that order's `where` field.
- `mutate.py` `19791681f257` (shared `red_gates_disabled` list mutated in place across
  survivors) — confirmed still present. `red_at_baseline` is a single list; `_refresh_baseline`
  updates it via `red_at_baseline[:] = [...]` (in-place), and every survivor dict stores the
  same list object by reference (`"red_gates_disabled": red_at_baseline`), not a copy. A
  mid-run refresh silently rewrites the caveat attached to every survivor found before it.
- `mutate.py` `f9643582fd29`, `f40f701594a4`, `79d51aef8b71`, `ef26ed6029e7`, `a1aa2be36b7e` —
  all reproduce as described; no code change touches any of them.
- `mutate.py` `2d8b96343896` (stale `drill.py:4256` citation) — still a live example of the
  problem it names: `reap_orphans()` is now called from `drill.py` at lines 12047 and 12144
  (plus mentions at 11977/12010), not 4256. Confirms the general point; already filed as a
  question, not re-filed.
- `mutate.py` `c72431056a14` (`_TOKEN_ENV` written, never read) — confirmed: a fresh grep for
  `_TOKEN_ENV` / `PANSCRIPTUM_MUTATION_TOKEN` across `src/` finds only the three lines already
  named in the order (declaration, set, pop). No reader anywhere.
- `identity.py` `1cdc2f8cd2f3` (`top[:6]` announced console truncation) — confirmed present,
  unchanged, at `main()`'s continuity-inventory summary.
- `manifest_builder.py` `c8dc624e4e02`, `db36d589713e` — `FEATS_BLOCK_CHARS = 20000` at
  `manifest_builder.py:168` is still read by nothing except two comments (`context_budget.py:20`,
  `manifest_builder.py:366`); the live budget path is `context_budget.feats_block_budget(cfg)`.
  `feats_index.feats_for_source`'s bare-`[]`-on-unbound-host behaviour is unverifiable from this
  batch (the file isn't in my module list).
- `backfill.py` `9586cdf72b82` (`lead()`'s mid-word fallback cut, no marker) — confirmed
  present, unchanged, at the tail of `lead()`.
- `backfill.py` `929622118156` (`backfill_source`'s `next()` with no default raises bare
  `StopIteration` on an unmatched `--source` name) — confirmed present, unchanged; the `--all`
  path wraps calls in try/except but the explicit `--source name` CLI path (`main()`'s final
  loop) still does not.
- `backfill.py` `5c8c8b99e655` (`roster()`'s docstring describes a limit it no longer has) —
  confirmed present; `roster(host, limit=None)`, docstring still reads as if a hard default
  limit exists.
- `backfill.py` `fe99e57e1993` (unmarked name cuts, sweep44) — the specific `backfill.py:364`
  citation is now **fixed**: that line prints `x['source']` in full, directly beneath a comment
  documenting the removal of the old `x['source'][:52]` cut. The order spans many other files
  (`catalogue_web.py`, `cleanup.py`, `weave.py`, `tiers.py`, `policy.py`, `completeness.py`,
  `repass_bands.py`, `overnight.py`), none of which are in this batch, so the order as a whole
  cannot be closed from here — only its `backfill.py` portion is confirmed done.
- `hosts.py` `3fb312a72435` (no caller anywhere in the pipeline) — confirmed still true. A
  fresh grep for `import hosts`, `hosts_for(`, `primary_host(`, `hosts.discover`, `hosts.add(`
  and `SOURCE_HOSTS` across `src/*.py` turns up only false-positive matches (a `set.add()` call
  in `chain.py`, a comment mentioning `hosts.discover` in `hostcheck.py`, a `set.add()` call in
  `workorders.py`) — no real import or call site anywhere. `data/SOURCE_HOSTS.json` still holds
  real discovered data with nothing downstream reading it.
- `context_budget.py` `db36d589713e`, `3859043e365e` — both confirmed unchanged/still
  applicable (the latter is a standing owner question about `num_predict: -1` and a
  reasoning-model's hidden tokens, not something code can settle either way).
- `chord_field.py` `7e360eaec3a6` — see "Confirmed FIXED" above.

## New findings

None filed. I read all eight modules end to end specifically hunting the seven fault shapes in
the brief (silent truncation, could-not-measure-as-confident-value, tautological checks,
fail-open guards, stale premises/citations, two-writer races, and always-OK exit codes) and did
not find an instance in these files that isn't already covered by an open order above. This
batch's modules are unusually heavily audited already — `mutate.py` alone carries 13 prior
findings, most still open and independently reproduced above — and the remaining candidates I
chased down (a possible two-writer race in `hosts.add()`'s read-modify-write of
`SOURCE_HOSTS.json`; a possible fail-open denylist in `backfill._NOT_A_CHARACTER`) turned out
not to hold up: `hosts.add()`'s only real-world caller sequence (`discover()`) invokes it
sequentially from one thread even though candidate scoring is parallelised, so there is no
live race today (the module also has no pipeline caller at all, per `3fb312a72435`); and
`backfill.py`'s denylist regex is a supplementary roster filter, not a security or correctness
gate, so an occasional missed non-character page is a cosmetic miss, not a Hard-Rule-0-shaped
defect.

## Coverage

All 8 assigned modules read in full: `mutate.py`, `identity.py`, `manifest_builder.py`,
`backfill.py`, `hosts.py`, `context_budget.py`, `chord_field.py`, `lognames.py`. No line ranges
skipped.
