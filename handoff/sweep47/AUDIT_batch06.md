# Sweep47 batch06 audit

Batch: 9 modules, 5,711 lines. All read in full, every line, no sampling.

- `src/cascade_bridge.py` (2,054 lines) — read in full (3 passes: 1-970, 971-1520, 1521-2054).
- `src/chain.py` (859 lines) — read in full.
- `src/catalogue_web.py` (714 lines) — read in full.
- `src/policy.py` (575 lines) — read in full.
- `src/reference.py` (486 lines) — read in full.
- `src/genre.py` (362 lines) — read in full.
- `src/resync_roll.py` (333 lines) — read in full.
- `src/ledger.py` (173 lines) — read in full.
- `src/module_index.py` (164 lines) — read in full.

No lines or modules were skipped in this batch.

## Already-open work orders: status against current code

I did not re-file any of the 20 already-open orders listed in the brief. Notes on a few I could
positively confirm one way or the other by reading the current source (the rest I could not
disprove or confirm from code alone and left untouched, as instructed):

- **`catalogue_web.py` `1e45fae97848` (CATALOGUE_WEB_MAIN_NO_EXIT_CODE)** — the code now has
  `return 1 if todo and tally['failed'] == len(todo) else 0` at the foot of `main()`, with a
  comment citing this exact order id as the fix. **This looks already fixed** — worth confirming
  and closing rather than treating as still open.
- **`catalogue_web.py` `8bd76479c64e`** and **`26b0e8cb30a1`** — both have matching in-code
  comments citing the same order ids as already applied (dedup key keeps the parenthetical
  disambiguator; `catalogue_composite`'s `bits` list is now built before the empty-result
  check). **These also look already fixed.**
- **`catalogue_web.py` `ea1a063d75d6`** (exit code masks partial failure) — confirmed **still
  live**: `main()`'s `return 1 if todo and tally['failed'] == len(todo) else 0` only fails the
  process when *every* source in `todo` failed; a run where 10 of 50 sources failed still exits
  0. Not re-filed since it's already on the books.
- **`chain.py` `e8466cd6ed14`** (main rc ignores denied write) — confirmed **still live**: none
  of the three `write_result(...)` call sites in `main()` check the return value, and `main()`'s
  own `return` codes never depend on whether the write landed.
- **`genre.py` `f646c1c5f1d0`** — the "dead disjunct" half is fixed (the `not ranked` branch is
  gone, with a comment explaining why it was unreachable); the "invariant `genres_scored` field"
  half is explicitly left as an open question for the owner in the code's own comment. Correctly
  still open.

I have no way to check the three `[OWNER]`-tier orders that reference *data* already on disk
(`GENRES.json`/`GROUNDINGS.json` inflated confidences, `SWEEP35_FINDING`, module-partition
coverage) from source code alone — those need the actual JSON files compared, which is an
owner-tier judgment call as the brief already tags them.

## New findings filed this batch

Four new work orders, all LOCAL/MINOR-or-INFO — no MAJOR findings survived verification. I found
several other candidate shapes that I traced through and could **not** confirm reproduce (see
"Traced and rejected" below); those are not filed.

1. **`3363994a27b1` GENRE_LOG_NAME_CUT_UNMARKED** (MINOR, LOCAL) — `genre.py main()` truncates
   source names to 30/26 chars in two diagnostic print lines (`s[:30]`, `s[:26]`) with no
   truncation marker. Same fault shape as the already-recognised UNMARKED_NAME_CUTS_SWEEP44
   pattern fixed elsewhere in this codebase (`catalogue_web.py`, `policy.py`), at a location
   that fix never reached. Console-only — `GENRES.json` itself stores the untruncated name.

2. **`8ab3ce3fc1eb` MODULE_INDEX_GROUPS_DUPLICATE_UNDETECTED** (INFO, LOCAL) — `module_index.py`'s
   hand-kept `GROUPS` table has no guard against the same module name being listed under two
   different stage headings. The existing stale-name check only verifies every named module
   still exists in `src/`; it never checks a name is claimed at most once. If it ever happens,
   the generated `handoff/MODULE_INDEX.md` would silently show the module twice with rc=0 — the
   "check that cannot fail" shape this exact file's docstring argues against, currently latent
   (no duplicate exists in the six lists today).

3. **`1d8e99b28613` REFERENCE_SHELFMARK_UNKNOWN_CONFLATES_READ_FAILURE** (MINOR, LOCAL) —
   `reference.shelfmark()` catches *any* exception reading `data/NAVTREE.json` (missing file,
   corrupt JSON, a lock) and falls back to `["?", "?", "?"]` — which prints identically, in the
   FORMAL CITATION text a person actually reads, to the charter's own convention for "this rung
   is genuinely unresearched." `silence.note` logs the fault internally, but the citation itself
   carries no marker distinguishing the two cases.

4. **`2a0d854b0b68` ASSAY_MOTH_NUMBER_CEILING_THRESHOLD_GAP** (MINOR, LOCAL) — found while
   auditing `reference.py`'s consumption of `assay.assay()`'s `moth_number` field
   (`reference.card()` prints it verbatim). `assay.py`'s ceiling clamp only fires at `_dec >=
   1.0` exactly, but `moth_number` is built from `round(_dec * 100)`, and `AXIS_MAX` is `10.0` —
   so a composite landing in `[9.95, 10.0)` produces an unclamped `_dec` in `[0.995, 1.0)` that
   `round(..., 100)` still rounds up to `100`, reproducing the exact `M<n>.100` broken-notation
   bug the surrounding comment (order `8b74d2b4f569`) says was already fixed, just past a
   slightly different threshold than the one actually guarded against. The site of the defect is
   `assay.py` (outside this batch's module list), surfaced through `reference.py`'s own citation
   output — filed because it is directly reproducible from the read lines, not a guess.

## Traced and rejected (worth recording so nobody re-chases them)

- **`cascade_bridge.owner_excluded()` prefix matching** — matches on the bucket's provider
  prefix (`zai:free` also excludes any other `zai:*` bucket). Considered whether this could
  wrongly exclude a hypothetical second `zai:*` bucket with a different, working key. Could not
  verify either way without reading Cascade's own `config.json` (a separate project outside this
  repo and outside my read access for this audit) — left as an unfiled, unverifiable question
  rather than a work order, per "a finding you could not verify is a QUESTION."
- **`resync_roll.py`'s unconditional `entry_count` repair on OUT_OF_SCOPE rows** — the status
  repair is guarded against re-promoting an owner-excluded source, but the `entry_count` repair
  is not. Checked `roll.py`: work-selection actually gates on `roll.in_scope()`/`status`, not on
  `entry_count`, so an out-of-scope source getting its `entry_count` refreshed does not
  re-admit it to work. Not a bug.
- **`policy.py` `OPS`/`is_type` dict shapes, `chain.py` `_ask()` fallback ordering, `ledger.py`
  `assay_to_standards()`'s M10 ceiling extrapolation** — read closely, worked through the
  arithmetic/logic by hand, found consistent with their own extensive docstrings. No defect.

## Coverage recorded

`sweep_plan.record('run47', [...9 basenames...], batch=6)` — see tool output.
