# SWEEP35 batch 13 — audit report

Modules read in full: src/mutate.py (973 lines), src/wiki_source.py (675), src/allsweep.py (525),
src/reference.py (411), src/grounding.py (320), src/catalogue_models.py (262),
src/catalogue_codex.py (229), src/roll.py (144), src/module_index.py (111). 3,650 lines total.
No file under src/ was edited. mutate.py was read only, never executed.

## Filed

- **5863bd9f566a** (SWEEP35_FINDING, MAJOR) — `allsweep.py`'s ESTATE tier runs four checks
  (`estate.charter()`, `.written()`, `.terminal()`, `.external()`) whose findings — e.g. MASTER
  CHARTER MISSING, KEYSTONE VOLUME MISSING, TERMINAL HAS NO HTML ENTRY POINT, OLLAMA UNREACHABLE,
  a config.yaml model Ollama does not have — are printed and written into ALLSWEEP.json but never
  enter `main()`'s `bad` count (allsweep.py:511-514 sums only imports + crashed/timeout verifiers
  + lint + `estate.artifacts.bad`). `workorders.battery_faults` (workorders.py:130-172) mirrors
  the identical formula and also reads only `estate.artifacts.bad`. So a real, specific, named
  finding from those four checks can stand indefinitely without failing allsweep's exit code or
  ever raising a BATTERY_GRADED order — structurally invisible to every grading path in the
  project, not merely an unreachable-subsystem edge case (estate.py already converts its own
  internal sub-check failures into `note()` rows rather than raising).

## Investigated, not filed (verified as not live/already covered)

- `roll.exclude(rows=...)` write-goes-to-live-file trap: this is the incident already described
  in the module's own docstring and CLAUDE.md context; confirmed `exclude()` has zero callers
  anywhere in `src/` (grep), so the current code path is the already-applied fix, not a new
  finding.
- `wiki_source.rank_by_size(top=...)` and `find_categories(limit=...)`/`category_members
  (limit=...)`: all real callers in `catalogue_web.py` pass `top=None`/`limit=None`
  ("rank, never truncate" — comments confirm this was deliberately fixed). No live Hard-Rule-0
  violation.
- `grounding.py`'s truncated-denominator defect: already fixed in code (confirmed by reading);
  the stale-data consequence in `data/GROUNDINGS.json` is already tracked by
  3eff62be6cc3.
- `allsweep.run_verifier` has no halt-refusal special-case (unlike `check_import`, which was
  fixed for this in run #31). Checked whether this is currently exploitable: none of the ten
  VERIFIERS (`health.py`, `silence.py`, `coverage.py`, `verify_math.py`, `thread_integrity.py`,
  `anchors.py`, `audit.py`, `identity.py`, `reference.py`, `rosetta.py`) import `escalation` at
  all, so none can currently raise `SystemHalted` mid-run. Not filed — speculative, not
  demonstrated.
- `catalogue_codex.py`'s substring-fallback section-matcher (main():145-149) carries the same
  collision shape as the "Curse of Strahd -> Roblox wiki" incident, but the code's own comment
  already documents this as an accepted, watched risk ("No live collision was found, which is
  the moment to add the guard") rather than an unaddressed defect.
- `mutate.py`: read in full. The module is unusually heavily self-documented with prior incident
  history and already-filed order IDs (d779f541cd0b, 6d7f88ffb76e, adba96551729) covering the
  lock-had-no-caller fix, the junction-is-a-portal-not-a-wall caveat, and the sandbox-missing-
  target guard. No new defect found beyond what its own comments already flag as open risk.
- `catalogue_models.py`, `reference.py`, `module_index.py`: read in full, no new defect found.

## Coverage recorded

`sweep_plan.record('run35', [...9 modules...], batch=13)` — done.
