# SWEEP35 batch 12 — audit report

Modules read completely (3,570 lines): src/dashboard.py, src/completeness.py,
src/manifest_builder.py, src/codewatch.py, src/backfill.py, src/tuning.py,
src/cosmology_graph.py, src/halo.py.

No edits made to src/ — audit only. Did not run verify_math.py, drill.py, or mutate.py; did
not touch any daemon.

## Findings filed (4)

1. **c81c6ea16d10** MAJOR — `codewatch.py:247-256,356`. `_budget_left()` is read UNLOCKED in
   `exit_if_stale()` before the (today's-fix) locked `_record_restart()` write. The lock
   protects the write from being clobbered but not the budget check-then-act decision, so two
   processes sharing the same job key (a twin — this file's own `twins()` docstring records a
   real prior incident of two `publish.py` processes 17s apart) can both read `left=1`, both
   pass the gate, and both restart — exceeding `BUDGET_PER_HOUR` in exactly the storm scenario
   the budget exists to cap. verify_math's `d99b11ec050e` test only exercises the write lock
   across three DIFFERENT keys, never this same-key race.

2. **7bf743b4acb4** MAJOR — `dashboard.py` panelSafety (JS). `br.slice(0,6)` (breached nets)
   and `Object.keys(qn).slice(0,4)` (quarantined hosts) are silent caps of the exact shape two
   sibling lists in the same panel had removed today (open findings, swallowed failures — both
   now documented as "ALL, a cap ruled a truncation"). The summary line states the true,
   uncapped count while only a handful of detail lines render, with no "+N more" note on either.

3. **d673aa4d609a** MAJOR — `backfill.py:200-203`. The sort key
   `(t not in sizes, -sizes.get(t, 0))` does the opposite of the comment two lines above it:
   verified by direct execution, a title whose size lookup FAILED sorts after every title with
   a KNOWN size, however tiny — not "ranked with the deepest articles" as claimed. Under
   `--cap` a transient network failure is therefore the single most likely reason a title gets
   dropped, which is exactly the failure the comment says this line prevents.

4. **2345e4b431fe** MINOR — `halo.py:137`. Same defect class as the already-open
   `1770c2b84786` (wh40k.py:197): every axis worksheet line is stamped `"[wiki] "`
   unconditionally, including several axes with no quoted material at all (Precursors/
   Gravemind/Ur-Didact `celerity`, all plain paraphrase). `zfighters.py` already has the
   correct per-axis provenance pattern and documents why; halo.py has neither.

## Checked and NOT re-filed (already open / already fixed)

- `946153deafe9` (completeness.category_size dead) — confirmed still dead; `category_size_probe`
  is the only thing anything calls now.
- `f883d9bb534e` (codewatch.twins exclude_pid) — confirmed still present, already filed.
- `aad11acb1183` (dashboard.py assert_clear blocks the halt display) — confirmed still present
  at the current line (991), already filed and open.
- `47c8def059e3` (cosmology_graph console truncations) — re-read the current file: the code now
  fully discloses every console cap ("--show 0 prints them all", "--write emits every pair",
  explicit "... N further ... not printed here" lines) and writes the complete artifact
  unconditionally. Matches the existing MINOR order's own text (already display-only, pending
  owner ruling); nothing new to add.

## Modules that looked solid on this pass

`manifest_builder.py`, `tuning.py` — both heavily self-documented with prior fixes; no new
defect found matching the audit's priority list after full read.

Coverage recorded: `sweep_plan.record('run35', [8 modules], batch=12)`.
