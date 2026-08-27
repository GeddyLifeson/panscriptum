# SWEEP35 BATCH 7 — audit report

Modules read in full (3,603 lines): src/magnitude.py, src/build_terminal.py,
src/secondopinion.py, src/weave_index.py, src/navtree.py, src/cleanup.py,
src/retry_synthesis.py, src/repass_bands.py.

## Findings filed

1. **a32028fe76b7** (SWEEP35_FINDING, MAJOR, `src/secondopinion.py:112-115,138-168,350`)
   `NOT_FILED` silently swallows the largest ruff category it audits. The module's own
   docstring (lines 112-115) states plainly: "BLE001 alone runs into the hundreds ... and
   it is still a real finding, which is why it is NOT in this list." It IS in the list —
   `NOT_FILED["BLE001"]` at lines 161-168 — so `file_orders()`'s `if code in NOT_FILED:
   continue` (line 350) drops every BLE001 site before a work order can ever be filed.
   Measured live with the module's own `RUFF_RULES`/`RUFF_IGNORE`
   (`ruff check --statistics src`): BLE001=531 of 1002 total selected findings — over
   half the whole report. The stated reason is separately false on its own terms: it
   (and the identical claim under S110) says `silence.audit()` already treats the 151-152
   SILENT handlers as "an accepted category ... not a miss," but `silence.py` itself
   prints "each of these can turn a failure into a plausible negative result"
   (`silence.py:190`) and returns exit code 1 whenever any SILENT handler exists
   (`silence.py:200`) — there is no per-site acceptance anywhere in `silence.py`, every
   SILENT handler is an open, equally-weighted failure. Between BLE001, SIM115, S110,
   S112, E402, PLW1510, B007, RUF059, RUF100, PLW0603 and PLW2901, 960 of 1002 measured
   findings (96%) never reach the second-opinion queue — the exact "no findings looks
   like a clean bill of health" failure this module's own docstring (lines 42-46) says it
   must never produce.

## Areas checked and cleared (no filing)

- `magnitude.py`'s five assay guards (verbatim/relevance/subject/saturation/quantity),
  `quantity_scores()`'s unit conversion, `_split_assay`/`slice_census` bookkeeping,
  `settled()`/`run_batch()` resume logic, `calibrate()` checkpointing — all internally
  consistent with their extensive docstrings; no silent mis-parse of the "3 x 10^9
  megatons" shape found in this module (it consumes already-mined `q["value"]`/`unit`
  pairs; the mining regex itself lives in `feats.py`, outside this batch).
- `navtree.py` is explicitly Hard-Rule-0-aware (uncapped world lists, a written audit
  trail to `state/NAVTREE_AUDIT.json`); its tie-break and child-sum audit logic checked
  out.
- `weave_index.py`'s console report truncates two preview lists (`top = ...[:18]`,
  `spread ... [:10]`) but the written outputs (`ENTITY_INDEX.json`, `WEAVE_CANDIDATES.json`)
  are full and uncapped — judged not filing-worthy (unlike the already-filed
  `cosmology_graph.py` case, nothing here is asserted as complete).
- `cleanup.py`'s per-category console previews (`nav[:5]`, `ceil_fixed[:6]`, etc.) act as
  samples alongside an accurate full count and process every record regardless — not a
  Hard Rule 0 violation.
- `retry_synthesis.py`, `repass_bands.py`, `build_terminal.py` — read in full; no swallowed
  failures, tautologies, or dead code found beyond what their own docstrings already
  document as historical (fixed) bugs. `repass_bands.py`'s `len(recs)` after consuming
  `PL.records()` is safe — `pipeline.records()` returns a list, not a generator.

## Coverage recorded

`sweep_plan.record('run35', [...8 modules...], batch=7)` — landed.
