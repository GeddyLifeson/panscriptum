# sweep66 batch16 — audit

Auditor for batch 16 of sweep66 (maintenance run #66, 2026-09-27). Read-only throughout on
`src/`, `data/`, `state/`, `output/`, `prompts/`, `reference/` and the repo root — nothing under
those trees was edited, created or deleted except this report and the mandated
`sweep_plan.record()` call. Did not run `drill.py`, `verify_math.py`, `generate.py`, the
pipeline, `publish`, the crawl, `overwatch`, `foreman`, `mutate`, or any job. No subagent was
spawned (per the brief). No halt-clearing call was made and `prose_enabled`/`step4_enabled` were
not touched.

## Scope, read in full start to finish (no sampling, no grep-only skim)

- `src/local_agent.py`                1650 lines — read in 3 chunks (1-928, 929-1328, 1329-1650)
- `src/binding_health.py`             1616 lines — read in 3 chunks (1-550, 551-1100, 1101-1616)
- `src/threads.py`                    1022 lines — read in 3 chunks (1-550, 551-1021, 1021-1023)
- `src/gpu_lane.py`                    684 lines — read in 1 chunk
- `src/worldseed.py`                   536 lines — read in 1 chunk
- `src/pantheon.py`                    432 lines — read in 1 chunk
- `src/deprecated/catalogue_local.py`  333 lines — read in 1 chunk (including the dead code after
  the self-refusing `raise SystemExit`, deliberate per the module's own header)
- `src/cosmology_graph.py`             261 lines — read in 1 chunk
- `src/whoruns.py`                     159 lines — read in 1 chunk

Total: 6,693 lines across 9 modules, all read in full this session.

## Method and prior-audit cross-check

`CLAUDE.md` read first (Hard Rule -1 escalation/halt chain, Hard Rule 0 no caps ever, fail-closed
doctrine, "a check that cannot fail looks exactly like a check that passed"). `handoff/sweep65/`
was then grepped for all nine module names and every matching report read in full before touching
current source:

- `handoff/sweep65/AUDIT_batch16.md` — the immediately prior audit of exactly seven of these nine
  modules (`local_agent.py`, `binding_health.py`, `threads.py`, `gpu_lane.py`, `worldseed.py`,
  `pantheon.py`, `deprecated/catalogue_local.py`), paired that run with `halo.py` and
  `repass_bands.py` instead of this batch's `cosmology_graph.py`/`whoruns.py`. Filed **0 new
  findings**; both items carried over from sweep64 were resolved (one fixed and verified, one
  already an open OWNER order, not re-filed).
- `handoff/sweep65/AUDIT_batch08.md` — covers `cosmology_graph.py` and `whoruns.py`, this batch's
  remaining two modules. Filed **0 findings** on either.

Re-verified sweep65's clearances against the CURRENT source rather than trusting them, per this
sweep's standing instruction that a prior audit can be wrong in either direction. **No behavioural
change was found in any of the nine modules since sweep65**: a targeted grep for recent-dated
order comments (`2026-09-2[4-7]`, `sweep65`, `sweep66`, `run65`, `run66`) inside these nine files
returned nothing, and the two files whose line counts I could check against sweep65's own count
(`threads.py` 1020→1022, everything else unchanged) show no substantive change — the two extra
lines are not adjacent to any new order or logic change I could find on a full read.

`state/workorders.json` was searched for every module name in this batch. Relevant **already-open**
orders, not re-filed:

- `30854f11f322` (binding_health.py:916-997, `binding_verdict`) — a wiki sitename that is a
  word-subset of its bound source's name scores 100 on `rapidfuzz.token_set_ratio` and reaches
  `CONFIRMED` on containment alone (e.g. "Prime" inside "Prime World Equipment"). The module's own
  docstring documents this at length and the order is explicitly routed to OWNER because no
  string metric measured separates the three genuine calibrated bindings (Eberron, War Thunder,
  ANEURISM) from the false-positive shape without also breaking them. Re-read `binding_verdict` in
  full against current source: unchanged, still routed to OWNER, not re-derived here.
- `325ccb493c45` (threads.py `build()`, `annex_join_unmatched`) — whether a join key that threads
  nothing (currently exactly one: "Lost Mines of Phandelver") should stop the build or only be
  reported. Currently only reported. Unchanged in current source (threads.py:630-647); OWNER
  question, not re-filed.
- `21c075e5e2d6` (names `binding_health.py` among others) — whether writers of reversible,
  self-healing state (quarantine records) should refuse under a plant-wide halt. Policy question,
  unchanged, not re-filed.
- `de265a105279` — a structural note that adding `whoruns.py` to `src/` makes
  `verify_math`'s "the newest finished sweep proves its own completeness" row fail until a full
  16-batch sweep runs. Not a defect in `whoruns.py` itself; already OWNER-routed.

No open order names a defect in `gpu_lane.py`, `worldseed.py`, `pantheon.py`,
`deprecated/catalogue_local.py` or `cosmology_graph.py`.

## Findings

**0 new VERIFIED. 0 new SUSPECTED.**

## Questions

None met the bar this batch. No fresh design ambiguity was found beyond what is already recorded
in the source itself and already carried on the open-order queue (see above): `worldseed.py`'s
unreachable `"primitive"` size key is already ruled and marked (owner ruling 2026-09-08, order
40e98eed6870); `threads.py`'s deviation from the ratified per-shelfmark file shape is flagged in
its own module docstring and in prior handoffs; `binding_health.py`'s containment-based
`CONFIRMED` threshold is an open OWNER order (30854f11f322), not re-derived.

## Cleared (examined closely this batch, no defect found)

- **`local_agent.py`**: re-traced the full write gate on current source — module/path denylist
  (case-folded), `_protected_identities`/`_identity_denied` (hard-link-safe for named
  modules/paths), the `WRITABLE_PREFIXES`/`WRITABLE_FILES` allowlist checked on both the written
  and the resolved spelling, the `DENYLIST_PREFIXES` region check, the blast-radius cap
  (`_blast_ok`, charged only once an edit is actually about to land, after uniqueness and
  `--no-apply` are settled), `_gates()`'s per-format parse/lint/import/whole-suite sequence
  (the in-memory `compile()` swap, the by-path import for a file patched outside `src/`, the
  `RESULT:\s*\d+\s+passed,\s*(\d+)\s+FAILED` regex rather than a `"0 FAILED" not in stdout`
  substring test), the revert-on-failure path and its SAFETY escalation on a failed revert,
  `_tool_message`'s always-valid-JSON shrink-to-fit, `_achievement`'s four false-success traps, and
  the halt check at the top of `run()`. All intact, matching the extensive in-line documentation
  and matching sweep64/65's own trace of the identical gate. The one open item touching this file
  (a hard link from the writable surface into a `DENYLIST_PREFIXES` region — sweep64's SUSPECTED
  finding) is unchanged and already carried on order `d2f103634cf1` (OWNER); not re-derived.
- **`binding_health.py`**: the three-probe canary (`_probe_present`/`_probe_absent`/
  `_probe_reachable`) and `verdict()`'s three-valued truth table, including the outcome-channel
  threading sweep64 batch16 added (`why == "throttled"` now returns `None`, not a clean pass or
  fail, in both `_probe_absent` and `_probe_reachable`) — confirmed still present and correct;
  the CAS write paths for `quarantine()`/`release()`/the partial-pass merge in `run()`; `_spread`'s
  even-across-the-catalogue sampling; `binding_verdict`'s containment-vs-tight scoring (open OWNER
  order, see above). No defect found.
- **`threads.py`**: T1/T2/T3/T4 derivation, `edge()`'s two refusals (class and anti-dangling),
  `annex_join()`'s three-way absent/unreadable/malformed-row handling, `cohort_family`'s
  `parts[:2]` (a field decomposition, not a listing truncation), `verify()`'s round-tripped-graph
  checks (T3 checked against `annex_codes()` rather than the graph's own `known`), and
  `threads_for`'s refusal for an unaddressed source rather than a silent blank. No defect found.
- **`gpu_lane.py`**: `_slot_count`'s auto/zero/malformed-env handling; `_alive`'s Windows-
  `OpenProcess` liveness check and its "unknown answers are ALIVE" policy; `_take_slot`'s
  three-way (path/False/None) return and the unreadable-vs-mid-creation slot-file distinction;
  `_touch`'s never-resurrects guard; `_heartbeat`'s dual-lease refresh and the shutdown ordering
  in `lane()`'s `finally` (heartbeat stopped before release). No defect found.
- **`worldseed.py`**: `_first`'s attested-vs-seeded provenance tagging; `to_options`'s
  band-provenance three-way split (`ok`/`unparsed`/`out_of_range`); `build_all`'s
  `limit is not None` guard and its ONOMASTICON/CONTINUITY_GROUPS unreadable-vs-partial reporting;
  the unreachable `"primitive"` size key, marked per owner ruling rather than dead code to delete.
  No defect found.
- **`pantheon.py`**: `compute()`/`value()` and the `Z_FIGHTERS.json` merge's three-way failure
  handling (partial roster via `_incomplete`, total merge failure, denied write), all folded into
  the exit code and the console. No defect found.
- **`deprecated/catalogue_local.py`**: unchanged self-refusing module (`raise SystemExit(_REFUSAL)`
  at import except for `--help`). The code after the raise is genuine dead code, kept unrepaired on
  purpose as a record of the failure mode it documents. No defect found.
- **`cosmology_graph.py`**: the `1/log(n+1.5)` inverse-frequency weight formula with the `x0.15`
  ubiquity penalty, matching the docstring's worked numbers; `--write` emitting every pair and
  cluster uncapped with `threshold_applies_to: "clusters"` stated explicitly; the gated,
  verdict-checked write in `main()`. No defect found.
- **`whoruns.py`**: `script_of`'s `-m`/`-c` short-circuit and the `_FLAGS_WITH_A_VALUE` two-token
  skip; `running()`'s tri-state (`None` = unmeasurable) and its use of `ON._in_this_tree` to avoid
  a mutation-sandbox false positive; the exit-code documentation warning that 0 means "something is
  running," matching grep's convention. No defect found.

## Coverage

Recorded via `sweep_plan.record('run66', ['local_agent.py', 'binding_health.py', 'threads.py',
'gpu_lane.py', 'worldseed.py', 'pantheon.py', 'deprecated/catalogue_local.py',
'cosmology_graph.py', 'whoruns.py'], batch=16)` for the nine modules above, all read in full this
session, none substituted or skipped.
