# Sweep 47 — Batch 14 audit

Modules assigned: `src/hostcheck.py`, `src/escalation.py`, `src/ledger_guard.py`,
`src/build_terminal.py`, `src/anchors.py`, `src/pick_model.py`, `src/resonance.py`, `src/halo.py`.
This is an audit shift, not a repair shift — no source file was edited.

## Coverage

Read in full, every line, in this order: `src/halo.py` (219), `src/resonance.py` (298),
`src/pick_model.py` (417), `src/anchors.py` (457), `src/build_terminal.py` (667),
`src/ledger_guard.py` (810), `src/escalation.py` (1150, both halves), `src/hostcheck.py` (1573,
both halves). All 8 modules, 5,590 lines, read in full — no module and no line range was skipped.

Supporting reads outside the batch, to verify specific claims rather than to audit those files:
`src/workorders.py` (grep for the handler `LADDER`, to check `escalation.py`'s handler map is
valid), `src/hosts.py` and `src/drill.py` (grep + spot read, to confirm every current caller of
`hostcheck.score()` passes `by=`), and `data/NAVTREE.json` (a Node script, to check field
completeness against `build_terminal.py`'s JS assumptions).

## General impression

All 8 modules are unusually mature. Every one of them carries extensive in-line commentary
documenting past defects, the measurements that found them, and the fixes applied — this looks
like the product of many prior sweeps. `escalation.py`, `hostcheck.py`, `ledger_guard.py` and
`anchors.py` in particular read as heavily hardened already, and most of the "obvious" fault
shapes (silent truncation, could-not-measure-as-zero, checks that can't fail) that were once
present are now caught, tested, and narrated in the surrounding comments. The already-open work
orders in the brief match real, still-present conditions in every case I could verify against
this batch's own files — none of them looked fixed. Two new, narrower findings below.

## Findings

### 1. `hostcheck.score()` still has an "unmeasured control read as a confident zero" path — MINOR, OWNER

This file's own docstring is a sustained argument against exactly this defect: `null_rate()` was
rewritten to return `None` rather than `0.0` when the control could not be measured, specifically
because a flattering zero baseline had already caused a live mis-adoption (`warhammer40k.fandom.com`
unassigned from Warhammer 40,000 on throttled probes reading as 0%). `score()` reads:

```python
base = null_rate(host, by=by, exclude=source) if by else 0.0
```

If `by` is falsy (`None`, or an empty dict), `base` is set to `0.0` directly, bypassing
`null_rate()` entirely — reintroducing the identical "no baseline measured, so assume the most
generous possible one" conflation the surrounding code was rewritten to eliminate. Every
downstream `lift` computation, and therefore every verdict, is computed against that invented
zero as though it had been measured.

**Verified not currently reachable through any live call site**: every present caller passes a
non-empty `by` —
- `sweep()` builds `todo`/`hostless` filtered on `by.get(s)`, so `by` is never empty when `score()`
  is reached from there;
- `adopt()` similarly filters on `recs`, and always calls `score(h, by[src], src, by=by)`;
- `hosts.py:discover()`'s `work()` calls `HC.score(h, names, source, by=by)` with a `by` built
  from `HC.entities_by_source()`;
- `drill.py`'s only exercise of `score()` (`drill_hostcheck`) always passes a non-empty `by`.

So this is not live today. It is a landmine for the next caller who calls `score()` positionally
or drops the keyword — the exact "an API whose misuse is only ever discovered during an
emergency is an API that will be misused again" argument `escalate()`'s own docstring makes about
itself, elsewhere in this same batch. Given `score()` is a public, externally-called function
(three modules outside `hostcheck.py` already call it), I'd suggest changing the fallback to
`base = null_rate(host, by=by, exclude=source) if by else None` so a missing `by` fails the same
honest way an unmeasured control already does — but that is a repair decision, not mine to make
in an audit shift.

**Where:** `src/hostcheck.py`, `score()`, the `base = ...` line (currently line 767).

### 2. `ledger_guard.py`'s per-seal loss tolerance can be spent repeatedly against one baseline — MAJOR, OWNER

This is a different mechanism from the already-open `LEDGER_GUARD_LOSS_TOLERANCE_CANNOT_TELL_TYPO`
(27f823fd6ed5), which is about a single check being unable to tell a large typo-fix from a small
truncation within one `MAX_LOST_FRACTION` (0.05) band. This finding is about what happens
*across* checks.

`seal()` overwrites `state/ledger_snapshot/<name>` with the ledger's *current* live content every
time it runs successfully (i.e., after every push through `assert_intact()`). `check_since_snapshot()`
then compares the live file only against that one most-recent snapshot, and explicitly tolerates
losing up to `MAX_LOST_FRACTION` (5%) of an append-only ledger's substantive lines as "edited
rather than appended to" — `assert_intact()` does not refuse, and `seal()` immediately re-baselines
against the now-smaller file.

Nothing anywhere compares a ledger against anything older than its immediately-preceding seal, or
against a fixed historical floor. So a sequence of pushes that each lose, say, 4% of
`handoff/HANDOFF.md`'s substantive lines — each one individually indistinguishable from "a person
fixed a typo in an old entry", which is exactly the case `check_since_snapshot()`'s docstring says
the tolerance exists to protect — will pass every single check, with the baseline re-set lower
each time. There is no mechanism in this file that would ever notice or report the compounding:
`verify_chain()`'s SHRANK detector only compares adjacent hash-chain links (same one-step window),
and `_lost_fraction()` is always called with `old = _read_snapshot(name)`, i.e. the last seal, never
an older one or an original baseline.

This matters specifically because this module's own stated purpose is catching "a run that
truncates HANDOFF.md" — the docstring's central failure mode — and a truncation spread across many
small below-the-floor pushes is exactly as silent and exactly as capable of destroying the
project's continuity record as a single big one, while satisfying every gate this file has. I am
filing this as a finding rather than certain that it needs a code change: it may be an accepted
tradeoff (the docstring for `MAX_LOST_FRACTION` explicitly frames the choice as "a safety that
stops the operator doing ordinary work is a safety that gets deleted," and a stricter,
long-horizon check would reintroduce exactly that risk for a person doing years of legitimate
copy-editing). That tradeoff call belongs to the owner, which is why this is filed OWNER — but I
don't think the compounding risk is currently written down anywhere in the file, and it should be
even if the ruling is "accepted."

**Where:** `src/ledger_guard.py`, `seal()` (snapshot re-baselining, ~lines 288–337) together with
`check_since_snapshot()`/`_lost_fraction()` (~lines 372–457).

## Modules with no new verified finding

- `src/halo.py` — fully read; every mechanism (per-axis provenance, wrapped-not-cut `--full`
  citations, atomic write with a checked verdict) already matches this project's own hardening
  conventions. No open WOs listed against it in the brief, and I found nothing to add.
- `src/anchors.py` — fully read, including the invariant-grading `run()`. Both open WOs in the
  brief (`LUMEN_AND_THRENODY_ARE_UNWIRED`, `ANCHORS_COLLEGE_AND_BIT_VALUE_PRINTED_NEVER_...`) are
  still live and match the code as it stands (the COLLEGE interval and bit-value are printed at
  lines ~205–209 but never appear in the `CLAIMS`/`verdict()` table that decides the exit code;
  `convene()` at line 190 still passes no eta). Neither looked fixed.
- `src/pick_model.py` — fully read. Both open WOs (`resident()`/`fit_note()` using different VRAM
  bases — `budget` (total-derived) vs `vram_gb` (free-derived) — and the two "SWEEP39_B07" notes)
  are still live as described. Nothing else new found.
- `src/resonance.py` — fully read. The shared `LUMEN_AND_THRENODY_ARE_UNWIRED` finding
  (`hodge_decompose`/`resonance_strength` have zero production callers, so Threnody's curl-veto in
  `custodes.convene()` never actually receives an eta) is confirmed current: `anchors.py:190` is
  still the only real caller of `convene()` and still passes none. Not fixed.
- `src/build_terminal.py` — fully read, including the inline JS template. No open WOs listed
  against it in the brief. I checked one hypothesis (a JS `nd.k.length` dereference in `panel()`
  that would throw if a node lacked a `k`/`n`/`src` field) against the live `data/NAVTREE.json`
  (734 nodes) and found every node carries `n`, `src`, `k`, and `t`; `s` and `w` are the only
  fields ever absent, and both are already guarded (`nd.s?...`, `nd.w?...`) everywhere they're
  read. Not filed, since I could not reproduce a fault against real data — noting it here only so
  it isn't silently unmentioned.

## Open work orders checked against this batch's code — none appear fixed

`hostcheck.py`: `HALT_CHECK_STALE_BEFORE_LONG_PROBE` (58cfc2b6dbc4) — confirmed still true;
`_assert_not_halted()` is called once before `adopt()`/`purge()`'s multi-minute threaded probe,
with nothing re-checking the halt before the eventual write. `HOSTCHECK_UNFIT_WRITTEN_WHEN_MERGE_REFUSED`
(79da6c08c536) — confirmed still true; `n_reject`/`unfit_landed` in `sweep()`'s repair branch are
computed and written regardless of whether `_land_hosts()` actually landed the corresponding host
removal. `CODEWATCH_UNCOVERED_JOBS_OUTSIDE_THE_KEEPER` and `cachekey-owns-ignores-host-dimension`
reference modules outside this batch (`codewatch.py`, `cachekey.py`) and I did not re-verify them
from `hostcheck.py`'s call sites alone.

`escalation.py`: all six open WOs (`HALT_WRITE_RACE_NARROWED_25X_BUT_NOT_CLOSED`,
`HALT_LIFT_PATH_UNREACHABLE_FROM_EVERY_AUTOMA...` — correct/deliberate per the brief,
`NO_DETECTOR_MEASURES_GATE_REACHABILITY`, `RESUME_SUBSYSTEM_HAS_NO_PERSON_CHECK`,
`ESCALATION_REFUSED_IS_DECLARED_WITH_NO_RAISE`, `ESCALATE_FLOAT_LEVEL_TRUNCATES`) match the code
as read: `resume_subsystem_verdict()` checks only ruling length, never who is calling, unlike
`clear()`'s `_by_a_person_at_the_cli()`; the `Refused` exception class is still declared and never
raised anywhere in this file; `level = int(level)` still truncates a fractional level with no
rounding or rejection.

`ledger_guard.py`: `LEDGER_GUARD_LOSS_TOLERANCE_CANNOT_TELL_TYPO` (27f823fd6ed5) — still live; see
Finding 2 above for the distinct, related mechanism I filed alongside it.

`anchors.py` / `resonance.py`: `LUMEN_AND_THRENODY_ARE_UNWIRED` (bd673ceaaf31) and
`ANCHORS_COLLEGE_AND_BIT_VALUE_PRINTED_NEVER_...` (18d0fedabf13) — both confirmed still live, as
detailed above.

`pick_model.py`: `CONFIGURED_MODEL_IS_A_THINKING_VARIANT_THE_C...` (342ccfafa4a4) and
`SWEEP39_B07_PICKMODEL_MOE_MARKERS_CLAIM_QUES...` (85a6b7b9e2c8) — I could not independently
re-verify these two against only this batch's files (they concern claims about specific model
tags/benchmarks I have no way to re-measure here); left as-is. `PICK_MODEL_RESIDENT_AND_FIT_NOTE_USE_DIFFERE...`
(2f38b3e5258d) and `SWEEP39_B07_PICKMODEL_TWO_BUDGETS_ONE_TABLE` (e038ec1759a9) — both confirmed
still live and appear to describe the same underlying `resident()`/`fit_note()` VRAM-basis
mismatch from two different sweeps.
