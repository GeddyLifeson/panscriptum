# sweep65 batch12 audit

## Scope

Every module read in full, top to bottom, sequentially, in Read-tool chunks (magnitude.py and
generate.py each needed a second chunk; the other six fit in one read apiece). No sampling, no
grep-only skimming.

  - src/magnitude.py         1989 lines  (chunks: 1-981, 982-1989)
  - src/generate.py          1305 lines  (chunks: 1-998, 999-1306)
  - src/onomast.py            844 lines  (one read)
  - src/custodes.py           714 lines  (one read)
  - src/policy.py             611 lines  (one read)
  - src/axis_correlation.py   443 lines  (one read)
  - src/descending_ladder.py  362 lines  (one read)
  - src/resonance.py          298 lines  (one read)

Total 6,566 lines. READ-ONLY throughout: nothing under `src/`, `data/`, `state/`, `output/`,
`prompts/` or the repo root was edited, created or deleted. No subagent was spawned. No job,
`generate.py`, `publish`, the crawl, `overnight`, `foreman`, `mutate`, `drill` or `verify_math`
was run; no halt or `prose_enabled`/`step4_enabled` was touched. This file and the one scratch
`.py` file used to run `sweep_plan.record` (written under `%TEMP%`, then removed) are the only
writes made.

## Prior audits consulted

`handoff/sweep64/AUDIT_batch12.md` (same day, run #64): covered `magnitude.py` and `generate.py`
in full under a different eight-file grouping; traced generate.py's 2026-09-25
`complete_fixed_tail`/corrective-retry change line by line against `prose_gate.py` and found
0 defects. `handoff/sweep64/AUDIT_batch11.md`: covered `onomast.py`, `custodes.py`, `policy.py`,
`axis_correlation.py`, `descending_ladder.py` in full, filed clean beyond two owner-routed
questions already on the books. `handoff/sweep64/AUDIT_batch03.md` and `handoff/sweep63/
AUDIT_batch06.md`: covered `resonance.py` in full, re-verified the Gauss-Seidel convergence fix
and the module's continuing zero-production-caller status.

Every one of this batch's eight files was therefore audited clean, in full, within the last two
maintenance runs (both same-day, 2026-09-26). This pass re-read all eight from scratch rather than
trusting that history, per the brief, and independently re-derived the same verdict rather than
citing the prior reports as a substitute for reading.

`state/workorders.json` was searched for every module name before writing anything. Ten existing
orders name one or more of these eight files (`1e6f99e54b25`, `21c075e5e2d6`, `28f335ecefd3`,
`3099138a82bd`, `34ec8a90c42f`, `5bb12b398783`, `670c907af5e3`, `8454be695dc7`, `a66423722e45`,
`d2f103634cf1`), all still open (`handler: OWNER`, no `resolved` field). None of them is re-filed
below. The one live-relevant to this batch is `670c907af5e3` (`PROSE_TEMPLATE_TAIL_DROPPED`,
BLOCKING, `where: src/generate.py generate_job / prompts/system_style.txt ENTRY TEMPLATE`): this
is the order that produced `complete_fixed_tail` and the one corrective retry now in
`generate_job` (2026-09-25, option (a)). It is still open awaiting the owner's read of whether
option (a) alone resolved the 0-chapters-written incident; nothing in this read changes that
status, and sweep64's trace (recapped above) already re-verified the gate is unweakened by it.

## Findings

**0 CONFIRMED. 0 SUSPECTED.** No new defect was found in any of the eight modules: no wrong
logic, off-by-one, inverted condition, silently swallowed exception where the code claims to fail
closed, guard that cannot fail, race on a shared file, uncapped-then-capped roster, stale comment,
dead branch, or Windows-specific breakage.

Two candidate leads were run down and both cleared (traced, not merely read):

- **`descending_ladder.rung_for_length`'s bucketing loop** (`src/descending_ladder.py:213-219`):
  walks `DESCENDING` top-down and keeps overwriting `best` while `metres <= r[3]`, never
  `break`ing. Hand-traced against `metres=5e3` (between Civic's 1e4 edge and Structural's 1e2
  edge): the loop correctly settles on Civic, the coarsest-to-finest walk converging on the
  smallest edge still `>=` the input. Monotonic in `DESCENDING`'s length column as the module's
  own docstring claims; no defect.
- **`generate.py:complete_fixed_tail`'s Threads-reinsertion branch** (line 646-651): re-checked
  that `list(_THREADS_FIELD.finditer(body))[-1]` picking the *last* match only matters if an
  entry's body contains the literal pattern `^[\s*_#>-]*Threads[\s*_]*:` more than once. Grepped
  a sample of `output/raw/*.md` for a second occurrence of that pattern inside one `◈` entry:
  none found. Left as a real but currently unreached edge case, not a finding.

## Questions (possible deliberate design, not filed as new — already on record)

Both of the following were re-examined against source this run and are unchanged from sweep64's
own filing; neither is new, so neither is re-added to `state/workorders.json`:

1. `generate.py:597` — `_NOT_A_BEING = {"world": "places", "polity": "polities", "event":
   "events"}` covers 3 of the template's 7 non-being `Class:` values (Relic, Vessel, Praxis,
   Substance fall through to the generic `"things"` at line 636). Cosmetic only:
   `instrument_shortfall` gates on the `▣`/"Instrument" marker and the "not applicable" phrase,
   never on which noun follows "not", so no entry's pass/fail changes. Recorded in
   `handoff/sweep64/AUDIT_batch12.md`; not re-filed.
2. `roll.py`'s `in_scope()` fails open on an unreadable roll — out of this batch's file list
   (`roll.py` is not one of the eight above) but re-noted here only because it was already
   filed against the same reading in sweep64 batch12 and is not this batch's to re-litigate.

## Cleared (examined closely, found correct — one line each)

- `magnitude.py` guards 1-5 (`_resolve_citation`, `AXIS_RE`, `subject_refusal`, `saturated`,
  `quantity_scores`): each re-traced against the worked examples in their own docstrings; all
  five still refuse the failure case they were written against.
- `magnitude.py:_split_assay`/`_split_gate`/`slice_census`: per-axis slicing, refusal counting and
  the guard-3 subject check on the split path all still match the one-shot path's contract.
- `magnitude.py:assay_entity`: pool-then-split-then-local-then-defer ladder, epoch mandate,
  ceiling clamp and the `settled()`/DEFERRED distinction all re-verified against their comments.
- `generate.py:strip_think`, `_covered`, `_deed_traced`/`_deed_shortfall`, `complete_fixed_tail`,
  `block_problems`, `generate_job`'s corrective retry, `_land_catalog`/`_land_failures` CAS merges,
  `save_raw`'s atomic replace, and `main()`'s evidence-floor / manifest / meta-ban-import-failure
  fail-closed paths: each re-read end to end; all still do what their comments claim.
- `onomast.py`: `is_carried`, `well_formed`'s seven constraints, `coin_well_formed_stamped`'s
  ordinary/exhausted/digest-tail fallback ladder, `name_worlds`'s append-only carry-forward and
  standing-vs-retired split, `land_onomasticon`'s CAS retry — all re-traced, all sound.
- `custodes.py`: `_custos_reading`'s private per-call weight table, `convene()`'s abstention
  wiring for Lumen/Threnody, `_transit_widening`'s dispersive-vs-unmechanised split, `half`'s
  cover-every-reading floor, `table_faults()` — all re-verified.
- `policy.py`: `OPS`/`TYPES`/`ARG_REQUIRED` remain closed sets refused at load, `check_rule`'s
  malformed-rule-vs-document-failure separation, `evaluate()`'s vacuous-pass detector and its
  `absent`-op exemption, `main()`'s uncapped default corpus sweep and the two-tier (1/2) exit
  code — all re-verified.
- `axis_correlation.py`: `_scores_of`'s bool-exclusion on both stored shapes, `observations()`'s
  read/missing accounting, `rho()`/`widening()`'s single-`_no_matrix`-call-per-run fix — all
  re-verified.
- `descending_ladder.py`: `rung_for_length`'s domain guards at both ends, `shrink_report`'s and
  `transgression_bits`'s non-positive-input refusals, the U-shaped binding column documented as
  deliberate — re-verified; module remains HELD/unwired by design (order `66f96febdb3a`), no
  caller in `src/`.
- `resonance.py`: `hodge_decompose`'s Gauss-Seidel convergence check and the no-evidence-vs-
  eta-1.0 distinction, `dominates`/`incomparability_rate`'s unmeasured/tied/incomparable split —
  re-verified; module remains without a production caller.

## Coverage

Recorded via `sweep_plan.record('run65', ['magnitude.py', 'generate.py', 'onomast.py',
'custodes.py', 'policy.py', 'axis_correlation.py', 'descending_ladder.py', 'resonance.py'],
batch=12)` — see the scratch script run for this (`sweep_plan_record_batch12.py` under
`%TEMP%\claude\...\scratchpad`, removed after running).
