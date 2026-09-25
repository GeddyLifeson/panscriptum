# sweep63 batch10 audit (maintenance run #63, 2026-09-24)

Scope (read in full, start to finish, in chunks; line counts as of this run; READ-ONLY on
src/ — nothing was run beyond reading the source text):

- src/publish.py       2207 lines — READ IN FULL
- src/generate.py      1184 lines — READ IN FULL
- src/catalogue_web.py  821 lines — READ IN FULL
- src/gpu_lane.py       684 lines — READ IN FULL
- src/address.py        543 lines — READ IN FULL
- src/render.py         441 lines — READ IN FULL
- src/profile.py        354 lines — READ IN FULL
- src/tempus.py         297 lines — READ IN FULL

Total: 6,531 lines across 8 modules.

## Context and prior coverage

Skimmed CLAUDE.md's doctrine (Hard Rule -1 escalation/halt, Hard Rule 0 no caps, fail-closed,
"a check that cannot fail looks exactly like a check that passed") first. Grepped
`handoff/sweep*/AUDIT_batch*.md` for each module name before reading, to avoid re-reporting
resolved items:

- **publish.py / generate.py / catalogue_web.py** — all three read clean in sweep60/batch10 and
  sweep61/batch10 (sweep61's report is the direct predecessor at this same batch slot, though
  with a different module set — ingest_doc.py/pick_model.py/physics.py stood where
  gpu_lane.py/render.py/tempus.py stand this run). sweep61 flagged one SUSPECTED item in
  `publish.py:git()` (the `gh.exe` "No such file or directory" recurrence, tied to
  `LOCALAPPDATA` possibly being empty in the daemon's inherited environment) and one QUESTION
  in `generate.py:_covered()` (empty-name fail-open, defended-but-unreachable). Both re-verified
  by reading the current code: unchanged, still standing, not re-filed here.
- **render.py / gpu_lane.py / tempus.py** — read clean in sweep61/batch13 (render.py) and
  sweep61/batch15 (gpu_lane.py, tempus.py). batch15 left one QUESTION open on
  `tempus.band_resolution()`'s `LADDER.index(band)` call (guarded by `band not in BAND_EDGES`,
  not by `band not in LADDER`) as unverifiable without reading `assay.py`, out of scope again
  this run. Re-verified as unchanged; not re-filed.
- **profile.py** — read clean in sweep61/batch10, including a direct check of `encode()`'s
  `attested` range-refusal (bool excluded before the int check, range 0-4 inclusive). Re-verified
  unchanged.
- **address.py** — read clean in sweep59/batch09 and sweep60/batch11 (the spine-code matcher's
  `_normalize`/`_token_set`/`_index_name_is_placed_like_a_title` chain, and the `_FILLER`
  single-character-token question already on record there). Re-verified unchanged.

## Findings

**None.** No VERIFIED and no SUSPECTED findings from this pass. All eight modules carry the
same dense, order-numbered self-documentation the last several sweeps at this batch slot have
already noted — most of the shapes this brief's priority list asks about (tautological checks,
fail-open guards, caps/truncations, fabricated Instrument scores, halt bypasses, regex
corruption) are already named, fixed, and cross-referenced against drill/verify_math nets in the
code's own comments. I traced the load-bearing logic by hand rather than trusting those
self-reports (the CAS merge/retry paths in `generate.py`'s `_land_catalog`/`_land_failures`, the
three independent push-time locks in `publish.py:push()`, the Windows PID-liveness and lease
arithmetic in `gpu_lane.py`, the spine-code specificity scoring in `address.py:spine_code_for()`,
the coordinate-completeness guard in `render.py:children_of()`, and `profile.py`'s
encode/decode round trip) and did not find a live defect in any of them.

Two items were re-verified as unchanged from prior sweeps and are carried forward by reference
only (not re-filed as new findings, per the brief's instruction not to re-report what the code
already names and handles):

- `publish.py:git()` (~line 746) — SUSPECTED, first filed sweep61/batch10: if `LOCALAPPDATA` is
  empty in the standing daemon's inherited environment, `gh_dir` resolves to the relative path
  `gh-cli\bin`, `os.path.isdir()` evaluates it against the process's actual cwd, returns False,
  and the PATH-widening `if` body is skipped silently — plausible explanation for the recurring
  "gh.exe: No such file or directory" symptom. Unconfirmed without reading the live daemon's
  environment, which is out of scope for a read-only audit.
- `tempus.py:band_resolution()` (line 240) — QUESTION, first filed sweep61/batch15: `LADDER.
  index(band)` is guarded by `if band not in BAND_EDGES` but not by `band not in LADDER`; if the
  two ever have different keysets this raises uncaught. Verifying requires reading `assay.py`,
  out of this batch's scope both times.

## Questions

None new. See the two carried-forward items above.

## Coverage recorded

Recording via `sweep_plan.record('run63', [...], batch=10)` per the brief.
