# The phase contracts, on one page

*What each phase reads, what it writes, and the invariant that makes its output trustworthy.
The code is the authority; this page is the map. Runner: `src/pipeline.py` (phases dispatch to
`phase_<name>`), resumable via `state/PIPELINE_STATE.json` — per-phase done-lists, never
re-judging what is already judged. Two-writer discipline: the pipeline writes records through
`write_record` (disk entry-list wins), the catalogue through `write_record_catalogue` (fresh
cast wins, disk judgments preserved). Every state file lands atomically via
`silence.replace_retry`.*

| # | Phase | Reads | Writes | The invariant |
|---|-------|-------|--------|---------------|
| 1 | **synthesis** | `data/records/*.json` entries | `rec.synthesis` {ceiling_entity, provisional_magnitude, evidence, rationale} | Band-only M0–M10 or `unassayed`; a malformed band never files silently. This band is the source's ceiling — phase 2 and allsweep's reconcile both enforce against it. |
| 2 | **entrypass** | records entries (+ descriptions) | per-entry `category`, `scale_note`, `magnitude`, `topic`, `catalogued` | NO FEAT, NO BAND (H5); rejected scale notes are kept (`scale_note_rejected`), never destroyed; entry band is CLAMPED to the source's synthesis ceiling. Batches close on RESULT, not on write — `health.reopen_stranded` clears any interruption. |
| 3 | **weave** | records | `data/ENTITY_INDEX.json`, `data/WEAVE_CANDIDATES.json` | Candidates, never rulings — a shared name is evidence, not identity. Continuity parentheticals survive the fold (two Thors stay two Thors); when uncertain, split. |
| 4 | **chain** | feats corpus (incremental via `state/chain_harvest_idx.json`), entity index | `data/CHAIN.json` (ONE schema, `chain.write_result`) | An edge needs both parties named in the sentence itself; Bradley–Terry strengths only within a strongly-connected component (Ford's condition) — no number between entities who never met. |
| 5 | **cosmology** | records, weave | `data/TIERS.json`, `data/GROUNDINGS.json` | Tier claims grounded in the source's own text; the First Argument answered per cosmos, not assumed. |
| 6 | **history** | shelves, tiers | `data/CHRONICLE.json`, `data/CENSUS.json` | Lag walks X.7's propagation graph between two shelves — never a bare subtraction of dates. |
| 7 | **shelve** | records, `data/WORLDSEEDS.json`, spine codes | `data/SHELFMARKS.json` | Real addresses only: charter spine codes from the Acquisitions Index, `?` placeholders where classification research does not exist. Collisions are a standard (floor 0). |
| 8 | **write** | `data/COVERAGE.json`, records | `output/index/manifest.json` → prose via `generate.py` | Gated on WRITE_SETTLED_MIN=0.60 — the library does not write about entities nobody has read. Chapters write in verified 8-entry blocks; a missing entry fails the job LOUDLY and it stays pending. The supervisor runs `generate.py` every cycle. |

**The assay lane** (parallel to the phases, `magnitude.py --batch`): reads
`data/CHARACTER_SWEEP.json` + the feats evidence cache; writes `data/ASSAYS.json`
(multi-accession keys `host|name@epoch`). Invariants: verbatim citations only, source-ceiling
clamp, epoch mandate for `identity.EPOCH_REQUIRED` hosts on every path including the split
retry, split-never-truncate above 30k chars, DEFER-never-truncate everywhere —
`settled()` requeues anything that is not a finding.

**The instrument's own regression**: `magnitude.py --calibrate` →
`data/CHARTER_REGRESSION.json`, asserted daily by the `automation reproduces the charter`
standard (interval-overlap consistency), dispatched by the foreman when ≥3 buckets answer.
