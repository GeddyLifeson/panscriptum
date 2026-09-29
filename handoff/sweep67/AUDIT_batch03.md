# Sweep67 (run67) AUDIT batch 03

## Scope
Every line read, sequentially, with the Read tool (no skimming):

| module | lines |
|---|---|
| src/pipeline.py | 3,827 (read in 8 chunks) |
| src/catalogue_web.py | 821 |
| src/policy.py | 640 |
| src/reference.py | 497 |
| src/genre.py | 386 |
| src/deprecated/catalogue_local.py | 333 (incl. the dead code after the import-time refusal) |
| src/halo.py | 219 |
| src/cachekey.py | 217 |

Read-only for the project. Scratch scripts lived under %TEMP%/aud3. Reproductions imported `pipeline`
against a temp directory with `log`/`silence.note` stubbed, so nothing under state/ or data/ was written.
CLAUDE.md hard rules read first (Hard Rule -1 chain, Hard Rule 0 no caps).

## Prior-audit cross-check (handoff/sweep66 AUDIT_batch03/06/07/08/10/12/13/15/16)
- pipeline `physiology` field never merged (order 0aceab8473e1): **FIXED, no longer stands.** `physiology` is in
  `MERGED_ENTRY_FIELDS` (pipeline.py:893) and `phase_entrypass` writes it for category 8 (2582-2584).
- pipeline `ENTRY_SCHEMA` bare `category` integer (sweep66 Q2): **FIXED.** Schema now carries minimum 1 / maximum
  `len(CATEGORIES)` (2175-2176); the range check and `category_rejected` remain as the second line.
- `write_record_catalogue` unpaired-row drop (sweep65): still fixed, and further changed by order beb7db270826
  (every lone row kept and stamped `stale_since`). Re-read: idempotent, and the clashing-row budget arithmetic is right.
- genre `genres_scored` invariant (sweep66 Q2, order f646c1c5f1d0): **RESOLVED**, renamed `genre_field_size`
  with a per-record `genres_with_signal` beside it. data/GENRES.json (regenerated 2026-09-28 15:44) carries the new key on
  all 210 records; nothing in src/ reads either name, so no consumer broke.
- genre dead `not ranked` disjunct / `or 1`: still gone.
- catalogue_web `MAX_PER_CATEGORY`/`CATEGORY_SCAN_DEPTH`: still dead-but-kept, marked. `MAX_PER_SOURCE` tripwire
  still fires at import and cannot fail while the constant is None (deliberate, documented).
- catalogue_web `CATALOGUE_WEB_STORED_TYPES_NEED_RECATALOGUE`: still an open owner cost decision; not re-filed.
- policy.py, cachekey.py, reference.py, halo.py, deprecated/catalogue_local.py: sweep66 found nothing; all re-read
  and their sweep66 conclusions still hold. The halo/reference `[wiki]` provenance tags were spot-checked against
  data/feats and data/readfeats: 9 of 9 halo quotes and the Goku/Luffy quotes are present verbatim.
- sweep66's clean bill for pipeline.py no longer holds: F1 and F2 below are new (the file grew 3,686 -> 3,827 lines).

## Findings

### F1 (MEDIUM) pipeline.py:1243-1247, 1596-1607, 1250-1265 - both record writers land with no compare-and-swap; lost update, still returns True
`write_record` and `write_record_catalogue` read the disk copy, merge, `json.dump` the merged copy to a temp file
(0.5 s for the 59k-entry, 60 MB marvel.json here, more with the disk write), then `_landed` renames it with
`silence.replace_retry`. Anything another writer lands between the read and the rename is overwritten. `save_state` in
the same file already does this correctly (digest before read, `silence.replace_if_unchanged`, re-merge on mismatch,
431-489); `silence.replace_if_unchanged`'s own docstring says "re-read and re-merge, which is what write_record already
does properly for records", but the records only merge against the read, not against the rename.
Evidence (%TEMP%/aud3/race.py): a second writer lands a 3-entry cast while `write_record` is serialising; output
`landed: True`, `entries on disk: ['A', 'B']` - the other writer's entry C is gone and nothing reports it. The catalogue
crawl and the pipeline write the same files for hours.
Suggested fix: take `silence.digest_of(path)` before the `open`/`json.load`, land through `replace_if_unchanged`, and on a
mismatch re-read and re-merge (bounded attempts, as `save_state` does); return False when it never lands.

### F2 (MEDIUM) pipeline.py:1521-1528 - the per-entry fold from a load-time `rec` reverts other writers' edits to every merged field except `description`
`write_record` folds `MERGED_ENTRY_FIELDS` (category, scale_note, magnitude, topic, subroom, catalogued, excluded,
thin_description, ...) from the in-memory copy onto EVERY disk entry of the record (`if fld in se: de[fld] = se[fld]`), not
just the batch it judged, and `phase_entrypass` holds one load-time `rec` for the whole phase. Order cb31bf2707ad closed
exactly this for `description` with `_DESC_SNAPSHOT`; the other fields have no watermark, so a value repaired on disk
mid-phase (repass_bands `magnitude`/`scale_note`, cleanup `category`/`excluded`) is put back by the next batch of that source.
Evidence (%TEMP%/aud3/stale.py): record loaded; another writer sets entry A `magnitude=M3` and a scale_note; the pipeline
judges only entry C and calls `write_record`. Result `landed: True`, A back at `unassayed` / `''`.
Suggested fix: extend the per-entry watermark to all merged fields (fingerprint per (name, k, field) at load and after
each landed write; disk wins where the caller's value still equals its watermark), or restrict the fold to entries the call
actually judged (pass the touched index set).

### F3 (LOW) pipeline.py:1250-1265 (and 1244-1247, 1597-1600, 1343-1346) - temp file left behind when the rename is refused or the dump raises
`_landed` returns False on a denied rename but never removes `tmp`; nothing wraps the dump in try/finally. `save_state`
does remove its temp (479-482). Live evidence in data/records/: `marvel.json.73756.69064.tmp` (54.2 MB, Sep 8),
`marvel.json.28464.70252.tmp` (18.0 MB), `marvel.json.66212.63416.tmp` (1.6 MB),
`gundam-all-centuries-incl-g-gundam.json.25428.25044.tmp` (1.0 MB) - about 75 MB of orphans. The pid.thread name means a dead
process's temp is never overwritten. Glob `*.json` does not match them, so no reader is misled; it is disk leakage and a
mislabelled-data risk for any tool that lists the directory. Fix: `os.remove(tmp)` on the False branch and on exception.
The four existing orphans were not touched (read-only run); the owner may delete them.

### F4 (LOW) pipeline.py:2483-2585, 1999-2021 - cloud answer items are not shape-checked; malformed items crash the phase, and `true` reads as category 1
`_pool_answer_usable` checks only the top-level `required` keys, and `_judged_something` uses `any()`, which
short-circuits on the first good item. Later items are then used raw: a non-dict item makes `res.get` raise, a non-string
`scale_note`/`topic`/`evidence` makes `.strip()` raise (uncaught -> "PHASE CRASHED", rc=1, loud not silent), and a JSON
`true` for `category` passes `isinstance(ci, int) and 1 <= ci <= 8` (bool is an int) and files the entry under Persons
(by inspection). Only the cloud arm can produce these (Ollama constrains to the schema). Fix: `if not isinstance(res, dict): continue`,
`isinstance(x, str)` coercion, and exclude bool as `clean_band`/policy `is_type` already do.

### F5 (LOW) pipeline.py:2655, 2704 - RUN_STATUS "Sources with a ceiling nominated (phase 1)" counts empty ceilings
`with_syn = sum(1 for _, r in recs if r.get("synthesis"))` counts any non-empty synthesis dict, including the
`unassayable` blocks (`ceiling_entity: ""`). Measured over data/records: 212 records carry a truthy synthesis, 45 of them with
an empty ceiling_entity. The owner reads this file to judge unattended runs; the row overstates by about 45. Fix: count
`(r.get("synthesis") or {}).get("ceiling_entity")`.

### F6 (LOW) pipeline.py:3323-3327 - `thin` roster of refused-for-thinness sources is built and never read
`phase_write` appends every source under WRITE_SETTLED_MIN to `thin` and then only logs the count (`%d of %d`). The
sibling rosters `refused` and `empty` are named in full for exactly the Hard-Rule-0 reason its own comments give; the
sources actually withheld from writing are the one list that is not. `thin` is never read (grep: two occurrences).
Fix: log `thin` uncapped, or drop it.

### F7 (LOW) catalogue_web.py:308-315 and 543-550 - a title whose fetch returned no text still shadows later same-key titles, which are reported as "kept"
`seen[key] = title` is set before `page_texts` runs. If the first title's fetch comes back "" (`no_text`, which the code
itself says cannot distinguish a failed fetch from an empty page), a later title with the same normalised key (another
category or class) is dropped as a duplicate of a title that produced NO entry, and the provenance records it as
"dropped title -> kept title". The entity ends up with no entry and a record that claims one was kept. Fix: register in
`seen` only when text arrives, or re-fetch the deduped twins of any `no_text` title.

### F8 (LOW) catalogue_web.py:152-153 - `_singular` mangles -zes / silent-e -ches words, contradicting its "never worse than rstrip" docstring
Reproduced (%TEMP%/aud3/s.py): Prizes -> Priz, Mazes -> Maz, Sizes -> Siz, Bronzes -> Bronz, Caches -> Cach, Niches -> Nich,
Avalanches -> Avalanch, Statuses -> Statuse; the old rstrip gave Prize/Maze/Size/Cache. No stored type shows it today
(scanned 12,860 distinct web types for those stems), so it is latent, but the value is written into records and prompts.
Fix: drop "zes" and "ches" from the sibilant rule (leave them intact like -ies/-oes) or test a small exception list.

### F9 (LOW) stale line-number citations in comments (the repo's own rule is "cite by symbol")
- pipeline.py:775 "`phase_entrypass` calls `records()` ONCE (:1576)" - the call is at :2408.
- pipeline.py:936-937 "`catalogue_web.py:244-246` and `:456-458`" set category/description - now :330-333 and :578-581.
- policy.py:489 "uncut at policy.py:339" (that is `_assert_not_halted`; the record loop is 410-422) and policy.py:563 "~477" (now ~594).
- reference.py:374 "used at :245" (:246).
Fix: cite by symbol.

## Questions (possible deliberate design; owner decides)
1. **"nine-measure worksheet"** in pipeline.py:1682 (model prompt) and :2023 (the `method` string persisted into
   160 records), against an Assay of eleven axes (assay.WEIGHTS = 11, verify_math checks it). threads.py:160 shows the charter
   volume is titled "The Nine Measures", and CLAUDE.md says "eight". Legacy title kept on purpose, or stale?
2. **halo.py:85** epoch `"the Forerunner-Flood war, and again in M3 (Halo 2-3)"`: an epoch is a time index, `M3` reads as
   a magnitude band. Typo for `H3`, or is the M3 meant?
3. **genre.py cue stems** match as prefixes, so whole-word stems over-match: `hell` matches hello, `ration` matches rational,
   `war` matches ward/warm, `fun` matches function. Reproduced: "hello there, a rational person went to a function; warm ward"
   scores grimdark 2, post_apocalyptic 2, military_modern 2. Noise on large casts, real tilt on small ones. Loose-stem
   heuristic by design?
4. **policy.py:578-607** VACUOUS passes are printed but never affect the exit code, though the module's opening thesis is that a
   vacuous pass is a non-result. Intended?
5. **pipeline.py:3698/3728** a single-phase `--phase N` run sets `st["phase"]` to N+1 even after a full ladder, so the next
   daemon pass re-runs phases N+1..8. Documented as the recovery action; intended side effect?
6. **pipeline.py:3782-3827** `_META_TERMS`/`meta_violations`/`assert_in_universe` sit after `sys.exit(main())`, so they
   are undefined when the file runs as a script (fine for import, which audit.py/drill.py use). The term list also flags
   in-world words (campaign, session, initiative, players, stub). Both look owner-ruled; noting only.
7. (out of batch) `wiki_source.clean_titles` drops every title containing "/", feeding catalogue_web. Real names with a slash
   vanish without appearing in `deduped` or `no_text`. Not verified against a live wiki.
8. Carried from sweep66: `CATALOGUE_WEB_STORED_TYPES_NEED_RECATALOGUE` (owner cost decision), unchanged.

## Cleared (read, no defect)
- pipeline: `_merge_state`/`_fold_state`/`save_state` CAS merge; `clean_band` full-match vs `ceiling_band` lax-clamp asymmetry;
  `_stored_cut` marking; `write_record_catalogue` lone/clashing/budget arithmetic and idempotence; `_merge_top_keys` watermark;
  ENTRY_REJECTION_COMPANIONS pops; `entry_settled`/`batch_settled`; `valid_scale_note` gate order (checked on a sample sentence);
  `synthesis_blocks` `+` not `or`, uncapped tail; `synthesis_prompt` ranked-and-declared feat budget; `_unassayable_verdict_is_stale`;
  gate_done/mark_done/`_chain_landed`; absent-vs-corrupt handling in phases 5/6/7/8; SHELVES key ordinal (walked equals written);
  main() rc paths and pointer logic; hard-coded "138 tells" (60+31+15+32) and "ten Custodes" still true.
- catalogue_web: composite/single-wiki flow, uncapped ranking (`top=None`), `save_roll` via `roll.update_rows`, exit code.
- policy: closed OPS/TYPES/ARG_REQUIRED, `absent` on `found`, uncapped sweeps, unreadable files folded into rc 1, rc 2 for a
  report that did not land.
- reference/halo: 11 axes present for all entities, interval arithmetic, gated writes, CALIBRATION verdict in the exit code.
- cachekey: verify-on-read, host check, `write_path` disambiguation (NTFS case-fold collisions are caught by `owns`).
- deprecated/catalogue_local.py: refuses at import except `--help`; the dead code after the raise is deliberate.
