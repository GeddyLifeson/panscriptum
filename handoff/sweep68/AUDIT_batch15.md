# sweep68 batch 15 audit (run #68)

Read-only. Nothing under src/, data/, state/, output/, prompts/ or config.yaml was edited. No subagent spawned. No module's `main()` run, no model call, no generate/publish/mutate/drill/verify_math/pipeline run. Scratch scripts are in `%TEMP%\aud68_15\` (t1..t9). Reproductions import modules and either only read the live tree (t1, t2, t3, t4, t8, t9 read `data/`, `output/index/` and never write) or patch `silence.note` and the function under test (t6 drives `generate_job` with a stubbed `call_ollama`; t7 drives `find_categories` with a stubbed `_api`).

CLAUDE.md Hard Rule -1 and Hard Rule 0 read first, then `BRIEF.md`.

## Scope (every line read, in sequential chunks; counts match `wc -l`)

| module | lines |
|---|---:|
| src/hostcheck.py | 1790 |
| src/generate.py | 1684 |
| src/wiki_source.py | 935 |
| src/manifest_builder.py | 745 |
| src/canon_backup.py | 561 |
| src/coverage.py | 487 |
| src/wh40k.py | 384 |
| src/audit.py | 275 |
| src/whoruns.py | 162 |
| total | 7023 |

## Tonight's changes, checked first

`generate.hold_shared_addresses` (generate.py:1197-1211, called at :1273) and `manifest_builder.volume_codes` (manifest_builder.py:475-507, used by `main` at :611 and by `pipeline.phase_write` at pipeline.py:3491).

- `hold_shared_addresses` is correct for what it does: it maps address -> set of source names, drops every job at an address with more than one source, and reports `{source: jobs held}` uncapped. On the live manifest (30,636 jobs, a bare list written by `phase_write`) it holds 580 addresses and 1,160 jobs from 38 sources, and runs 29,476. It does not see two jobs of ONE source at one address (checked live: 0 such), does not compare against the catalog (F3), and leaves no durable record (F10).
- `volume_codes` is the single decision point and `main` and `phase_write` now agree (live manifest vs `volume_codes(roll)`: 0 mismatches over 205 sources). But it does NOT produce distinct codes (F2), and the codes it produces are not stable (F4).
- Other paths where two jobs could land on one catalog key or one file, all checked against the live manifest and roll: duplicate roll names (0); one record file resolving for two sources through `load_record` (0 of 215, t8); same-source duplicate addresses, e.g. `chapter_slug` collisions or `#range` collisions (0); addresses that fold to one `safe_filename` (`[^A-Za-z0-9]+ -> _`, compared case-insensitively for NTFS) (0); codes differing only by case (0). Nothing further found on those paths today. The remaining routes are the cross-manifest one (F3) and the drifting number (F4).

## Prior-audit cross-check (sweep67 batches 05, 10, 12, 13, 14, 15, 16)

- b15 F1 (hostcheck `probe()` reads an API error body as rate 0.0): FIXED (hostcheck.py:444-453 now returns `rate: None` with the error body; `null_rate` therefore does not cache it). Closed.
- b15 F2 (`purge --go` deletes a shared host's whole cache): FIXED (hostcheck.py:1454-1467, `shared` keeps the cache and the log records `cache_kept_shared_with`). One residual, F8.
- b15 F5 (`sweep(only=)` overwrites HOST_FITNESS.json): FIXED (hostcheck.py:1263-1265). F8 (adopt unreachable wording): FIXED (:1719-1722). Closed.
- b15 Q1 (head sample of 40 names as the host probe) and Q2 (purge read-modify-write without CAS): still open as questions, unchanged.
- b14 F2 (Feats jobs built from the unfiltered record): FIXED (manifest_builder.py:407-411, `dict(record, entries=entries)`). b14 F3 (`--only` matching nothing writes an empty manifest): FIXED (:558-570). b14 F6 (null `entry_count`, `r["category"]`): FIXED at :541 and :714, with one residue (F7).
- b14 Q1 and Q2 (generate returns rc 0 when every job failed, and when the gate is closed): still stand exactly as written. `main()` still falls off the end after "Done. 0 generated, N failed" (generate.py:1664-1674) and the gate-closed return is `return 0` (:1238).
- b14 Q4 (volume numbering shifts when a source flips populated or is put out of scope): STILL STANDS and is now measured, so it is filed as F4.
- b16 F4 (`page_text` returns "" when all three section fetches raised): FIXED (`PageFetchFailed`, wiki_source.py:565, 599-604, and `page_texts` collects `failed`).
- b13 #4 (whoruns `-mMOD`/`-cCODE`): FIXED (whoruns.py:67).
- b12 F11 (coverage drops an unreadable record): FIXED (coverage.py:322-346, four attempts then refuse). b12 Q5 (`_CLASSIFIER_VERSION` does not track `feats.CLEAN_NEGATIVES`): still stands, Question 4 below.
- b10 Q2 (canon_backup digest-then-zip race makes a busy crawl fail the snapshot): still stands, F9.
- b05 Q3 (wh40k Khorne ruin called "the highest ruin in the setting" while Slaanesh's ruin is also 9.5): still stands, cosmetic; wh40k.py:91-94 vs :150.

## Findings

### F1. MEDIUM (reproduced) - generate.py:1046-1054, 1080-1083, 1154 - a corrective retry that recovers a missing entry is thrown away and the chapter is refused anyway

`lacking` is computed once from the first response (and the missing-names retry) at :1046. The corrective retry at :1074-1086 can replace `text` with a version that names every entry (`if _fix.strip() and not [... _covered ... _fix]`, then `text = _fix`), but `lacking` is never recomputed. At :1154, `missing.extend(e.get("name") ... for e in lacking)` still adds the entries the kept text now contains, and :1155-1166 raises `ChapterRefused("entries not written after retry: ...")`.

Scenario (`t6.py`, `call_ollama` stubbed, two entries A and B): attempt 1 and the missing-names retry both return only A; the third call (corrective retry) returns A and B in full. Output:
```
block 1/1: corrective retry for 1 fault(s) -> 0 left
block 1/1: supplied the fixed tail (Threads on 2, Instrument on 2)
RAISED ChapterRefused entries not written after retry: Beta Second
```
Zero faults left, every gate after it would pass, and the chapter is still filed as a failure and the remaining blocks of the job are derived as "unattempted". The corrective retry (the fix for the 469 refusals in the header comment at :1068-1073) can therefore never rescue the omission case it is worded for. Loud, not silent, but it burns three model calls per block on the GPU-bound lane for a chapter that then repeats the same way every run.

Fix: after a kept `_fix`, `lacking = [e for e in g if not _covered(e.get("name", ""), text)]` (and again after `meta_rewrite`/`drop_*` if any could remove a name).

### F2. MEDIUM (reproduced) - manifest_builder.py:475-507 `volume_codes` hands two sources the same code for 19 Series, and nothing at build time says so

The docstring calls it "THE ONE PLACE A SOURCE'S ADDRESS IS DECIDED". It numbers members of a multi-source Series `code.1 .. code.N` without asking whether `code.N` is already the real charter code of a different source. Live roll (`t1.py`, `volume_codes(roll)`): 19 codes are each held by two sources, e.g. `II.P.1: ARMS + Fortnite`, `II.A.1: Baki + Dragon Ball Z`, `II.L.1: Fire Emblem + The Lord of the Rings`, `II.F.4: StarCraft + Halo`, `II.H.2: Metal Gear Solid + Sakamoto Days` (a Set-level source numbered `II.P.1` lands on the real Series `II.P.1`). This is the 580 addresses / 38 sources run #68's own comment at generate.py:1266-1272 reports. `generate.py` now holds them, which is the right fail-closed answer for the run, but `manifest_builder.main()` builds and writes the manifest with these colliding jobs and prints only "Wrote N jobs" (:646-647), and `phase_write` likewise. The only place anyone is told is the generate console, and only for jobs present in the manifest handed to it (F3, F10).

A deterministic resolution exists that is not a curatorial claim (skip numbers already claimed by another source's own code, or number Set-level members `code.vN`); the choice is Hard Rule 2's owner call, so this is filed as: detect it where the code is decided. Fix (minimum): in `volume_codes`, after building `out`, raise or return the collision set so `main` and `phase_write` print it, uncapped, and a drill net can go red on it.

### F3. MEDIUM (traced from the code; the catalog is empty today, so latent) - generate.py:1374-1385 nothing compares a catalog row's source with the job's source

`hold_shared_addresses` judges only the jobs in the manifest it was given. `catalog.json` rows carry `source_name` (:1604), but the pending test is `cached = catalog.get(job["address"], {})` then `cached.get("recipe_hash") == rh` and nothing else. A `--pilot` or `--only` manifest never contains the colliding partner, so it is not held: pilot source ARMS writes `II.P.1/Persons`, catalogued under ARMS; a later run whose manifest has Fortnite at `II.P.1/Persons` (or any run after F4's shift) sees a different recipe hash, counts it as "stale", regenerates and overwrites the raw file and the catalog row (the raw path is `safe_filename(address)`, a pure function of the address). The first source's chapter is gone from disk with no failure row and no note; the closing line says "N generated". This is the overwrite run #68 set out to stop, arriving through a manifest that does not contain both sources.

Fix: in the pending loop, if `cached and cached.get("source_name") not in (None, job["source_name"])`, treat the address as claimed by another source and hold it exactly as `shared_addr` does.

### F4. MEDIUM (reproduced, latent while the catalog is empty) - manifest_builder.py:493-506 the `.N` in a job address shifts whenever the populated, in-scope set of a Series changes

Numbers are sorted-by-name positions over the populated, non-excluded members, and the address is the catalog key, the raw filename and the babel coordinate. The docstring at :579-590 promises "the address of a given book is stable across rebuilds". Measured on the live roll (`t2.py`): making `Lost Mines of Phandelver` (entry_count 0 now, 262 purged entries) populated moves 26 D&D sources (`Monster Manual II.L.7.29 -> II.L.7.30`, `Mordenkainen's Tome of Foes .30 -> .31`, ...). The same happens when the owner puts a source out of scope (eight are today: the current numbering already skips `Savant`, `Mage Hand Press`, `Yorviing's Arcane Grimoire`, `Dr. Firestorm's Engineering Corps`) and when a Series goes from one populated member to two (the existing source changes from bare `X` to `X.1`). Chunking has the same shape: an entry added to a 30-entry chapter turns `X/Persons` into `X/Persons#1-30` + `X/Persons#31-31`.

Effect once prose lands: after a shift, `II.L.7.30/Persons` in catalog.json and on disk is one source's chapter while the manifest says it belongs to another; each row is only corrected when that job regenerates (F3 lets it overwrite silently), and the old-address rows/files are orphaned when the chunk or number no longer exists. `prose_enabled` is true and the catalog is empty (0 rows, 281 failures), so this arrives with the first successful chapters.

Fix: persist the assignment (an append-only `data/VOLUME_NUMBERS.json`: source -> code, new sources take the next free number, an exclusion never renumbers), or key the catalog on source name plus chapter instead of the shifting number.

### F5. MEDIUM (reproduced) - wiki_source.py:544-552 `find_categories` swallows a failed canonical-category probe, and `catalogue_web` reads the empty result as "this wiki has no such class"

```
except Exception:
    silence.note("wiki_source-category-probe")
    continue
```
`all_categories`/`category_members` were changed to raise (Hard Rule 0, orders de0681cb9edc etc.); this loop, which answers the same "which categories exist" question, still turns a transient failure into a missing category. The `discover` half cannot rescue it for a category under the 40-page floor (`acmin=40`, wiki_source.py:399-402) or one whose name matches no keyword. `catalogue_web.py:500-502` then does `if not cats: continue`, so the whole class is silently absent from that source's catalogue and the run looks complete.

Reproduction (`t7.py`, `_api` stubbed; a wiki whose `Characters` category holds 30 pages, one throttled call, exactly what `_get` raises after its two 429/503 retries): first walk `[]`, second walk `['Characters']`. Nothing distinguishes the first result from a real absence except a ledger note.

Fix: let the probe's exception propagate (matching `all_categories`), or collect failed probes and return/raise when any canonical probe failed and nothing was found.

### F6. LOW (reproduced) - audit.py:129-142, 165-185, 247 the invariants pass counts entries the cleanup pass has already struck

`audit_invariants` does not skip `excluded` (or `stale_since`) rows, although the rest of the pipeline (manifest_builder.py:266-270, phase_entrypass) treats a struck entry as out of the library. Live (`t3.py`): of 315 "wiki navigation artefact" hits, 80 are entries with `excluded` set; of 425 "empty description" hits, 20 are struck. `allsweep` runs this as the "catalogue backscan" verifier with findings-by-contract, so its count can never reach zero by cleanup alone, and the flagged rows the operator has to act on (235 unstruck navigation names) are mixed with ones already handled. The RANDOM SAMPLE pool (:247) also draws struck rows. Fix: skip `e.get("excluded") or e.get("stale_since")` in the entry loop and the pool, and report the struck count separately.

### F7. LOW - manifest_builder.py:542 `skipped_empty` uses `r.get("entry_count", 0) == 0`

`populated` (:541) was hardened to `(r.get("entry_count") or 0) > 0` after b14 F6, but `skipped_empty` was not. A source with `entry_count: null` (the state `recover_folder_records` writes, per the comment at :539) is in neither list, and the line "Skipped N sources with entry_count == 0" understates by one per such source. No such row today (live roll: six zeros, no nulls). Fix: `not (r.get("entry_count") or 0)`.

### F8. LOW (UNVERIFIED, no live instance) - hostcheck.py:1417, 1459-1468 `purge --go` removes caches when no record matched the source, and counts "shared" only by current binding

(a) If `audit.get(src)` exists but no record file has `"source" == src` (a renamed source), `n_entries` stays 0, `landed` stays True, and the caches under `data/feats/<mined>` and `data/readfeats/<mined>` are deleted with no entry emptied and no purge note written into any record: the exact "entries stayed, evidence gone" state the comment at :1393-1403 was written to prevent. Live: all 43 audit sources have a record whose `source` matches, so it is not reachable today. (b) `shared` is `hosts.items()` bound to `mined` right now. A source that was repointed away but mined from `mined` (the situation `roster_audit` documents: "repointing a bad host does not move the cache it already wrote") still has evidence in that directory and is not counted. Fix: refuse the cache delete when `n_entries == 0` and no record matched, and add the sources whose CHARACTER_SWEEP `host` equals `mined` to `shared`.

### F9. LOW (traced) - hostcheck.py:247-251 `_land_hosts` applies `merge` to a fresh read without checking the values it was decided from

The CAS protects against a torn read but the merge is unconditional: `adopt` decided "this source is hostless" minutes ago; if `scout.py` registered a host for it meanwhile, `hosts[k] = v` replaces it. Likewise `sweep(--repair)`'s `None` removes a host another writer has just repointed. Hand-run only, and the halt is re-asked first, so LOW. Fix: pass `{source: (expected_old, new)}` and skip a key whose current value is not `expected_old`.

### F10. LOW - generate.py:1273-1279 held sources are recorded only on stdout, and the run exits 0

The 38 held sources are "held and NAMED" on the console only. No `silence.note`, no failures.json row, no escalation, and `main()` returns None (rc 0) when nothing else failed. The doctrine's JANITOR rung is "record it"; a scheduler reading rc 0 and a dashboard reading failures.json see a clean pass while 38 sources (the 19 colliding Series pairs) write nothing. Fix: `silence.note("generate.py:address-held")` per source and a non-zero rc (or a per-source SUPERVISOR-level record) while `shared_addr` is non-empty.

### F11. LOW - coverage.py:245-281 an unreadable cache file reads as NOT ATTEMPTED, and `_empty_state` trusts the shape of `mined_under.transport`

`_state_of_file` returns None when `json.load(fp)` fails (a reader/writer lock, a torn file), so `state_of` reports NOT ATTEMPTED (`nothing has ever fetched this`) for an entity that has evidence on disk; module docstring calls that state "a finding about US" and a lock is not that. Separately `tr.get("why")` at :239 raises `AttributeError` outside the try if `transport` is a string, aborting `measure()` (loud). Fix: treat a read failure as UNREACHABLE-for-this-pass (or retry once), and `isinstance(tr, dict)`.

### F12. LOW (reproduced) - wiki_source.py:705-708 `strip_banner_prefix` strips a real first sentence that starts with "This character needs"

`strip_banner_prefix("This character needs no introduction to fans of the series. He rules the north.")` returns `"He rules the north."`, and generate.py:1354-1357 uses `strip_banner_prefix(d) != d.strip()` to HOLD a job whose entry description is "furniture". Live effect today: 0 of 282,726 live descriptions trip it (`t9.py`), so no job is wrongly held; the risk is a future mined lead or a homebrew source (this repo mines D&D-Wiki style sources) that opens with those words. Fix: require the banner wording (`is a stub`, `seems to be empty`, `requires cleanup`) and drop the bare `needs` alternative, or anchor it to `needs (?:to be|more|improvement|cleanup|expansion)`.

## Questions (possibly deliberate; not filed as defects)

1. generate.py rc (b14 Q1, Q2 carried): an all-failed pass, a closed prose gate, and now a pass that held every job at a shared address all exit 0. Is rc 0 the keeper's intended reading for "produced nothing"?
2. hostcheck.py:298-411, 520-568 (b15 Q1 carried): host fitness is measured from the first 40 names of a rank-ordered roster and the first 12 (API) or 8 (RAW) bodies. Measurement of a host rather than a roster, so Hard Rule 0 may not apply; is a head sample intended, or a stride like `null_rate`'s?
3. canon_backup.py:52-58, 162-199 (b10 Q2 carried, F9 in spirit): the digest is taken before the zip, so a record rewritten by the crawl between the two makes the read-back mismatch, the archive is deleted and the snapshot raises. Loud and safe, but a busy crawl can starve `canon_backup_cycle` for a reason that is not corruption (the two newest snapshots are 09-29 07:31 and 20:23, twelve hours apart). Hash while writing? Also: `CANON_FILES`/`CANON_DIRS` cover WIKI_HOSTS, CHARTER_SPINE_CODES, SWEEP_ROLL and `data/records` only. `HOST_UNFIT.json`, `ROSTER_PURGES.json`, the generated volumes under `output/` (the raw and compressed chapters, which cost GPU-hours) and `output/index/catalog.json` are outside it; are they meant to be rebuildable?
4. coverage.py:85 (b12 Q5 carried): `_empty_state` depends on `feats.CLEAN_NEGATIVES`, but `_CLASSIFIER_VERSION` does not track it. Fold the tuple into the memo key?
5. wh40k.py:93 (b05 Q3 carried): Khorne's ruin and Slaanesh's ruin are both 9.5; the Khorne text says "the highest ruin in the setting". Cosmetic.
6. whoruns.py:58, 119: `script_of` returns None unless `tokens[0]` contains "python" and `running` compares the script basename case-sensitively, so a job started through a wrapper (`cmd /c`, a `.bat`) or with the file cased differently reads as NOT running. `_proc_lines` only enumerates python.exe/pythonw.exe anyway, so this is the same blind spot as the sensor, not new. Left as is?

## Cleared (examined by hand or by running, found correct)

- generate.py: `strip_think` (block, stray-close, stray-open ordering), `_land_catalog` / `_land_failures` (digest before read, `own` cleared only on a landing, non-object and unparseable refusals, no-retry when the file stood still), `save_raw`, `safe_filename` collision surface on the live manifest (none, case-insensitive too), `_covered` (empty name refuses; the strict `SECTION_LOSS_FLOOR = 0.0` gate in prose_gate is what makes the weak first-and-last-word test safe), `_deed_traced`, `complete_fixed_tail` ordering and operator precedence, `restore_supplied_fields`, `meta_rewrite`'s keep predicate, the floor/coverage/furniture fail-closed returns, `--limit 0`, the failures-cleared-only-after-catalogued rule, the final CAS landings deciding rc.
- manifest_builder.py: `load_record` (215 of 215 roll sources resolve, none shares a record file, roll name == record `source` for all, t8), `pack_feats` pagination (every deed emitted, flush-before-exceed), `build_jobs_for_source` chunking and the live-cast filter for the Feats chapter, `--only` refusal, `volume_codes`/`main` agreement.
- hostcheck.py: `probe` hop-following per name and the API-error refusal, RAW verdict tally, `null_rate` dedupe-then-stride and the MIN_PROBE floor, `score()` ladder (unmeasured control, about-n 0 versus below ABOUT_MIN, veto placement), `candidates_split`, `_land_hosts` absent/unreadable/non-dict refusals and the second halt check, `sweep` lift-based selection and `judged_any`, `roster_audit`, halt interlock on writing paths only.
- wiki_source.py: `all_categories`/`category_members`/`extracts`/`rank_by_size` all raise on a transport failure and do not memoise a partial walk, `page_text`/`page_texts` `failed` channel, `resolve_wiki` non-fandom-host short-circuit, `_furniture_spans` fail-closed on an unclosed container, `_paragraphs`, `clean_titles` O(n). No cap on any roster path (callers pass `limit=None`, `top=None`).
- canon_backup.py: `members` refusing a missing declared path, snapshot read-back against the first digests, unique stamp and temp names, `prune` half-removed pairs and the `keep >= 1` refusal, `verify` fail-closed on a missing/unreadable manifest and on archive members absent, `restore` opening the source before the destination.
- coverage.py: state precedence CITED > READ > NO PAGE > UNREACHABLE > NOT ATTEMPTED, memo keyed on path and name and discarded on a classifier-version change, `measure()` refusing on an unreadable host map or a lost record, `pages:`/`doc:` hosts (7 sources in the live map) carry real cache files and are counted (COVERAGE.json rows show cited/read/no_page, not NO HOST).
- wh40k.py: all five ROSTER records carry exactly the eleven `A.WEIGHTS` axes; `compute()` reproduces the docstring's magnitudes (Tzeentch M7.86, Slaanesh M7.85, Nurgle M7.80, Khorne M7.76, the Emperor M6.76, t4); the 13 axes tagged `wiki` were re-checked against the 3,917-page cache (39.4M folded characters): every one has a verbatim fragment (the one apparent miss, Khorne `ruin`, is found verbatim once its apostrophe is not split); write only after the halt check, gated verdict.
- audit.py: denominator per class (synthesis vs entry), every occurrence printed (no cap), `_field` wraps rather than slices, seed fixed. Only F6.
- whoruns.py: `script_of` on `-X utf8`, `-Xutf8`, `-mMOD`, `-c<code>`, `-W`, own-pid exclusion, tri-state exit codes, `_proc_lines` returning a string.
