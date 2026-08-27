# SWEEP35 BATCH 10 -- audit report

Modules read in full (3,578 lines): assay.py, corpus_db.py, zfighters.py, sweep_plan.py,
pantheon.py, ledger_guard.py, thread_integrity.py, scale_theories.py, lognames.py.

No files under src/ were edited. No forbidden scripts (verify_math.py, drill.py, mutate.py,
corpus_db.py --rebuild) were run. Existing open workorders were checked before filing; several
suspicions (the `_check_constants` tautology, `corpus_db.evidence_limit`, the datasette bare
`open()`, the corpus_db prose/disk mismatch, `sweep_plan.coverage_map` dead code,
`scale_theories.py` dead module) were already covered and were NOT re-filed.

## Findings filed (4)

1. **assay.py:1038-1114** (MAJOR) -- `HANDS`/`interval_from_hands`, the multi-hand-divergence
   interval mechanism described at length in the module docstring, has zero production callers
   anywhere in `src/` (only `verify_math.py` tests and a non-calling comment in `custodes.py`).
   The docstring nonetheless cites this exact mechanism as the reason the Emperor of Mankind is
   published at +/- 0.85. Measured: `data/WH40K_ASSAYS.json`'s actual Emperor entry carries
   interval **0.06**, computed by the ordinary single-attestation `assay()`/`_interval()` path.
   The prose describes a theorem-backed subsystem that the pipeline never wires in.

2. **ledger_guard.py:57-144** (MAJOR) -- `check_append_only()`, the pre-write HANDOFF.md
   truncation guard whose own docstring says "Raised before the write, never after," has zero
   production callers; only drill.py's test lambdas invoke it directly. `HANDOFF.md` is never
   programmatically written from `src/` at all (`pipeline.py:36`: "hand-written ... NEVER
   written here"), so there is no write path to hook the guard into. The only real defence is
   the retrospective hash-chain SHRANK check in `verify_chain()`, which fires only at
   `publish.py`'s push (`publish.py:622`) -- a truncation between two pushes is invisible for
   the whole gap.

3. **thread_integrity.py:199,204,209** (MAJOR) -- `main()` is the module's only reporting
   surface (no JSON output anywhere in the file; `allsweep.py:107` just runs it as a bare
   subprocess health check). It truncates three ranked obligation lists to a fixed top N
   (PARTIALLY-DANGLING `[:8]`, RECIPROCAL `[:8]`, ASYMMETRIC-SUSPECT `[:6]`) under headers that
   read as complete/actionable ("review these") rather than as samples, with no "top N of M"
   marker beside the list. `classify()` computes the full lists; everything past the cut is
   discarded with no record that more exists.

4. **assay.py:847** (MINOR) -- `denom = sum(W[k] for k in applicable) or 1.0` is a
   divide-by-zero fallback that current callers can never trigger: `used` (numeric scores) is
   always a subset of `applicable` (everything not marked INAPPLICABLE) by construction, and
   `assay()` already returns early whenever `used` is empty, so `denom` cannot legitimately be
   zero when this line runs. Harmless today, but it is the one arithmetic path in this file that
   would fail OPEN (silently substituting 1.0) rather than raising `AssayIntegrityError`, if a
   future edit ever broke the invariant.

## Notable non-findings (verified, not filed)

- `corpus_db.py`'s nine `CANNED` queries currently carry **no** `LIMIT` clause -- the Hard
  Rule 0 fix documented in the module's own comment block has already landed and holds.
- `zfighters.py`/`pantheon.py`'s hand-built rosters never use `NONE`/`INAPPLICABLE`/
  `UNESTIMABLE` sentinels, so `value()`'s unguarded `+ r["decimal"]` cannot currently hit a
  `None` from either module's own data; ran `zfighters.compute()` directly and confirmed all 14
  entries produce numeric decimals with full (1.0) axis coverage. Flagged as latent fragility
  only, not filed, since nothing on the live path reaches it.
- `instrument()` (assay.py) does not call `_check_scores()` on its `axis_scores` argument, but
  its only production caller (`anchors.py:186`) pre-filters to numeric values from its own
  bounded hand-written table -- not a live path to an unchecked reading.
- `lognames.OWNER` fragments were checked against every named script's actual argparse flags
  (`read.py --run`, `feats.py --roll`, `catalogue_web.py --recatalogue`,
  `magnitude.py --calibrate`) -- all exist and match `overnight.py`'s invocation order.
- `sweep_plan.py` and `corpus_db.py` are both extensively self-documented with prior fixes
  (race conditions, atomic writes, stale prose) from earlier runs; read in full, no new gap
  found beyond what is already on file.
