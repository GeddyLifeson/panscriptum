# sweep65 batch16 — audit

Auditor for batch 16 of sweep65 (maintenance run #65, 2026-09-26). Read-only throughout on
`src/`, `data/`, `state/`, `output/`, `prompts/`, `reference/` and the repo root — nothing under
those trees was edited, created or deleted. Did not run `drill.py`, `verify_math.py`,
`generate.py`, the pipeline, `publish`, the crawl, `overwatch`, `foreman`, `mutate`, or any job.
No subagent was spawned. No halt-clearing call was made and `prose_enabled`/`step4_enabled` were
not touched.

## Scope, read in full start to finish (no sampling, no grep-only skim)

- `src/local_agent.py`             1650 lines — read in 3 chunks [SAFETY-CRITICAL: write gate]
- `src/binding_health.py`          1616 lines — read in 3 chunks [canary / quarantine gate]
- `src/threads.py`                 1020 lines — read in 2 chunks
- `src/gpu_lane.py`                 684 lines — read in 1 chunk
- `src/worldseed.py`                536 lines — read in 1 chunk
- `src/pantheon.py`                 432 lines — read in 1 chunk
- `src/deprecated/catalogue_local.py` 333 lines — read in 1 chunk (including the dead code after
  the self-refusing `raise SystemExit`, deliberate per the module's own header)
- `src/halo.py`                     219 lines — read in 1 chunk
- `src/repass_bands.py`             214 lines — read in 1 chunk

Total: 6,704 lines across 9 modules, all read in full.

## Method

Read `CLAUDE.md`'s doctrine first (Hard Rule -1 escalation/halt, Hard Rule 0 no caps, fail-closed,
"a check that cannot fail looks exactly like a check that passed"). Then grepped `handoff/sweep64/`
for every one of these nine module names and read every prior audit that named one, in full,
before touching current source:

- `handoff/sweep64/AUDIT_batch16.md` — the immediately prior audit of `local_agent.py`,
  `binding_health.py` and `threads.py` (that sweep's batch16 carried a different six-module
  pairing for the rest: `address_space.py`, `handbuilt.py`, `render.py`, `style_audit.py`,
  `audit.py`, `compress_store.py`). Filed one VERIFIED finding (a fully-throttled host scored
  `healthy=False` and quarantined) and one SUSPECTED finding (a hard link from the writable
  surface into a protected region would bypass every gate in `local_agent.py`).
- `handoff/sweep64/AUDIT_batch04.md` — covered `gpu_lane.py` and `pantheon.py`. 0 findings on
  either.
- `handoff/sweep64/AUDIT_batch10.md` — covered `worldseed.py`. 0 findings.
- `handoff/sweep64/AUDIT_batch03.md` — covered `deprecated/catalogue_local.py`. 0 findings
  (confirmed unchanged, self-refusing).
- `handoff/sweep64/AUDIT_batch15.md` — covered `halo.py`. 0 findings.
- `handoff/sweep64/AUDIT_batch11.md` — covered `repass_bands.py`. 0 findings.

Also searched `state/workorders.json` for every module name and for the specific mechanisms named
in sweep64's findings (`throttled`, `_probe_absent`, `_probe_reachable`, `outcome=`, hard link,
`DENYLIST_PREFIXES`, `_protected_identities`, canary/quarantine) before writing anything, per the
brief's instruction not to re-file an already-open order.

## Re-verification of sweep64's two findings against CURRENT source

### 1. binding_health.py throttled-probe false quarantine — FIXED, re-verified against source

Sweep64 batch16 found that `_probe_absent` and `_probe_reachable` did not thread `feats.fetch`'s/
`feats.api`'s `outcome=` channel, so a fully-throttled (HTTP 429) host could read as "correctly
absent" or "unreachable" and be quarantined for 24h on nothing but rate-limiting.

Read both functions in full against the current source. Both are now fixed, and the fix is
labelled with this exact provenance:

- `_probe_absent` (binding_health.py:762-770): `got = F.fetch(host, [ABSENT_PROBE], outcome=_oc)`,
  with the comment "THE OUTCOME CHANNEL, AS `_fetch_chars` ALREADY ASKS FOR IT (sweep64 batch16,
  run #64)". A `why` of `"throttled"` (not in `F.CLEAN_NEGATIVES`) now returns `None` ("could not
  ask"), not a clean pass or fail.
- `_probe_reachable` (binding_health.py:871-874): "THROTTLED IS NOT DOWN (sweep64 batch16, run
  #64). A 429 on siteinfo is the host answering -- with 'slow down' -- and False here is the
  value `verdict()` quarantines on." — `_oc.get("why") == "throttled"` now returns `None` rather
  than `False`.
- `verdict()` (binding_health.py:1016-1064) already handled `ok_absent is None` and
  `ok_reachable is None` as "not proven sound, not proven at fault" before either fix landed,
  which is why threading the outcome channel through the two probes was sufficient on its own.

No new defect found in this area. **Closed — not re-filed.**

### 2. local_agent.py hard-link/region gap — unchanged, already routed to OWNER, not re-filed

Sweep64's SUSPECTED finding (a hard link from `src/`/`prompts/`/`handoff/` onto a file inside a
`DENYLIST_PREFIXES` region would satisfy every string-based gate, because `_protected_identities()`
deliberately builds its identity set from `DENYLIST`/`DENYLIST_PATHS` only, never from the
prefix regions) is unchanged in the current source: `_protected_identities()`
(local_agent.py:548-593) and `t_propose_patch`'s `DENYLIST_PREFIXES` loop
(local_agent.py:1011-1020) still test only the as-written spelling for regions.

This is **already on the open queue**: `state/workorders.json` order `d2f103634cf1`
(`SWEEP64_QUESTIONS`, handler OWNER) carries it verbatim as item 2, with a measurement ("0 of 972
files under src/, prompts/ and handoff/ [carry a hard link into a protected region today]").
**Not re-filed.** Re-read the surrounding gate logic (`_safe`, `_denied_target`, the
`WRITABLE_PREFIXES` both-spellings check, the blast-radius cap) end to end and found no
additional bypass beyond this already-tracked one.

## Findings

**0 new VERIFIED. 0 new SUSPECTED.** Both items carried over from sweep64 are resolved above
(one fixed, one already an open OWNER order) rather than being new findings.

## Questions

None met the bar this batch — no fresh design ambiguity was found that isn't already recorded
in the source itself (`worldseed.py`'s unreachable `"primitive"` size key is already ruled and
marked; `threads.py`'s deviation from the ratified per-shelfmark file shape is already flagged
in its own docstring and in the handoff).

## Cleared (examined closely this batch, no defect found)

- **`local_agent.py`**: full re-trace of the write gate — module/path denylist (case-folded),
  identity check (`_protected_identities`/`_identity_denied`, hard-link-safe for named
  modules/paths), the allowlist checked on both the written and resolved spelling, the
  `DENYLIST_PREFIXES` region check, the blast-radius cap (`_blast_ok`, charged only once an edit
  is actually about to land), `_gates()`'s per-format parse/lint/import/whole-suite sequence
  (including the in-memory `compile()` swap that keeps the "read-only by construction" promise
  true, and the by-path import for a patched file outside `src/`), the revert-on-failure path
  and its SAFETY escalation on a failed revert, `_tool_message`'s always-valid-JSON truncation,
  `_achievement`'s four false-success traps (attempted-but-none-landed, blank answer, zero tool
  calls, an answer written over an unpaged truncated slice), and the halt check at the top of
  `run()`. All intact and consistent with their own extensive in-line documentation.
- **`binding_health.py`**: the three-probe canary (`_probe_present`/`_probe_absent`/
  `_probe_reachable`) and `verdict()`'s three-valued truth table traced by hand against every
  combination named in the docstrings, including the RAW-mode reachability arm and its own
  exception-vs-clean-negative handling; the CAS write paths for `quarantine()`/`release()`/the
  partial-pass merge in `run()`; `_spread`'s even-across-the-catalogue sampling (not an
  alphabetical head); `binding_verdict`'s containment-vs-tight scoring and its documented,
  deliberately-unresolved threshold band. No defect found.
- **`threads.py`**: T1/T2/T3/T4 derivation, `edge()`'s two refusals (class and anti-dangling),
  `annex_join()`'s three-way absent/unreadable/malformed-row handling, `cohort_family`'s
  `parts[:2]` (a field decomposition, not a listing truncation — matches the file's own
  Hard-Rule-0 self-audit), `verify()`'s round-tripped-graph checks (including the T3-against-
  `annex_codes()` check rather than the graph's own possibly-mangled `known` set), and
  `threads_for`'s refusal for an unaddressed source rather than a silent blank. No defect found.
- **`gpu_lane.py`**: `_slot_count`'s auto/zero/malformed-env handling; `_alive`'s
  Windows-`OpenProcess` liveness check and its documented "unknown answers are ALIVE" policy;
  `_take_slot`'s three-way (path/False/None) return; `_touch`'s never-resurrects guard;
  `_heartbeat`'s dual-lease refresh and the shutdown ordering in `lane()`'s `finally`
  (heartbeat stopped before release). No defect found.
- **`worldseed.py`**: `_first`'s attested-vs-seeded provenance tagging; `to_options`'s
  band-provenance three-way split (`ok`/`unparsed`/`out_of_range`); `build_all`'s
  `limit is not None` guard and its ONOMASTICON/CONTINUITY_GROUPS unreadable-vs-partial
  reporting; the designation-collision report in `main()` `--write`. No defect found.
- **`pantheon.py`**: `compute()`/`value()` and the `Z_FIGHTERS.json` merge's three-way failure
  handling (partial roster via `_incomplete`, total merge failure, denied write), all three
  correctly folded into the exit code as well as the console. No defect found.
- **`deprecated/catalogue_local.py`**: unchanged self-refusing module (`raise SystemExit(_REFUSAL)`
  at import except for `--help`, per `allsweep.check_import`'s needs). The code after the raise
  is genuine dead code, and the module's own header says it is kept unrepaired on purpose as a
  record of the failure mode it documents (guessed entries filed as Reconstructed, a third writer
  against the two-writer record contract, a non-atomic roll rewrite). No defect found.
- **`halo.py`**: per-axis (not blanket) provenance tagging in `compute()`; the gated, atomic
  `HALO_ASSAYS.json` write and its rc propagation on a denied replace; `--full`'s uncapped,
  wrapped (not cut) citation display. No defect found.
- **`repass_bands.py`**: the write-then-gate-on-`write_record()` pattern (denials counted, not
  just printed, and folded into the exit code); the preserve-not-destroy handling of a demoted
  `scale_note` (the `scale_note_rejected` companion is set, matching `pipeline`'s own
  `ENTRY_REJECTION_COMPANIONS` contract) rather than silently blanking it; both the SURVIVORS and
  DEMOTED rosters and the source-ceiling roster are genuinely uncapped. No defect found.

## Coverage

Recorded via `sweep_plan.record("run65", ["local_agent.py", "binding_health.py", "threads.py",
"gpu_lane.py", "worldseed.py", "pantheon.py", "deprecated/catalogue_local.py", "halo.py",
"repass_bands.py"], batch=16)` for the nine modules above, all read in full.
