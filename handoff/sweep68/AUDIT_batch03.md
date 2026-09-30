# Sweep68 (run68) AUDIT batch 03

## Scope
Every line read, sequentially, with the Read tool. Read-only for the project; scratch scripts and reproductions live in
`%TEMP%/aud68_03` and import the modules against temp directories with `silence.note` and `pipeline.log` stubbed.
CLAUDE.md (Hard Rule -1, Hard Rule 0) read first. Also read for the phase 8 check: `manifest_builder.volume_codes`,
`build_jobs_for_source` head, `main` numbering block, `generate.hold_shared_addresses`, `drill._net_run68_phase8_volume_codes`,
drill.py:6935-6992 and verify_math section 20ab.

| module | lines |
|---|---|
| src/pipeline.py | 3,993 |
| src/weave_index.py | 842 |
| src/policy.py | 640 |
| src/reference.py | 497 |
| src/navtree.py | 390 |
| src/roll.py | 347 |
| src/halo.py | 219 |

## Prior-audit cross-check (sweep67 batch 03, plus its modules' earlier findings)
- F1 both record writers had no compare-and-swap: **FIXED, verified.** `_landed_cas` + `_CAS_RETRIES`. Repro (pl_repro.py B/B2):
  a second writer lands entry C during the dump; both `write_record` and `write_record_catalogue` retry and the disk ends
  `[A, B, C]`. The retry re-enters with `rec` already carrying the first pass's `carry`/`stale_since` marks; re-merge is idempotent.
- F2 per-entry fold reverting other writers' merged fields: **widened to all MERGED_ENTRY_FIELDS (`_desc_fingerprint`), but two
  holes remain: N1 (the watermark is defeated by `records()`) and N2 (companion clears are not watermarked).**
- F3 temp file left behind: **FIXED** for the record writers (`_dump_tmp`, `_landed`, `_landed_cas`). The four legacy orphans
  (`marvel.json.*.tmp` x3, `gundam-...json.25428.25044.tmp`) are still in data/records/ (`ls` this run); the owner may delete them.
  The same shape survives in `roll.mutate` (N8).
- F4 cloud items not shape-checked: **FIXED for phase 2** (`_entry_index`, `_res_text`); **phase 1 was not touched** (N7).
- F5 `with_syn` counted empty ceilings: FIXED (`update_handoff` counts `ceiling_entity`).
- F6 `thin` roster never read: FIXED (`phase_write` names it uncapped).
- F9 stale line-number citations: FIXED (cited by symbol). One new stale one, N9.
- Carried questions: (Q1) "nine-measure worksheet" still in `SYNTH_SYSTEM` (pipeline.py:1775) and the persisted `method` string
  (2116); (Q2) halo.py:85 `M3 (Halo 2-3)` still there; (Q4) policy VACUOUS never affects rc, still true (and moot, see Cleared);
  (Q5) `--phase N` moves the pointer to N+1 still true (main, `st["phase"] = ph + 1`); (Q6) `_META_TERMS`/`meta_violations` still
  sit after `sys.exit(main())` (3945-3993). genre.py, catalogue_web.py, cachekey.py, deprecated/ are not in this batch's scope and
  were not re-audited.

## Findings

### N1 (HIGH) pipeline.py:803 (called from 2779) - `records()` advances the write watermarks as a side effect, so `update_handoff` switches off the protection of orders a4b5ffc46f95 / cb31bf2707ad / sweep67-F2 for a phase holding a load-time record
`records()` ends each loaded record with `_remember_top_keys(p, r)`, which overwrites `_TOP_SNAPSHOT[path]` and
`_DESC_SNAPSHOT[path]` with fingerprints of what is on disk NOW. `update_handoff` (2779) calls `records()` only to count, and
discards the result, but it still resets every record's watermark. `phase_entrypass` calls `update_handoff` after every source
(2759) and `phase_synthesis` after every unit (2159); the recount cache is 120 s. So after the first recount the watermark
describes the fresh disk while the phase's own `rec` is still the copy loaded at phase start. In `write_record`, "caller value ==
watermark" is the test for "unauthored, disk wins"; a stale caller value no longer equals the (now fresh) watermark, so it reads
as authored and reverts disk.
Reproduction (pl_repro2.py): load with `records()`; another writer sets entry A `description` (markup stripped) and
`magnitude` M3 and refreshes `synthesis`; write a batch that judges only entry B.
  no recount   : ('raw wiki markup', 'M3', 'NEW')          <- the fix working
  after recount: ('raw [[wiki]] markup', 'unassayed', 'old')   <- description, band and synthesis all reverted, landed True
Every entrypass batch write after the first recount can revert cleanup.py's description repair, repass_bands' band demotion,
the `excluded` strikes (`excluded` is a merged field), and the refreshed `synthesis`/`purged_roster`. The drill/verify nets for the
watermark never call `records()` between the load and the write, so they cannot see it.
Fix: give `records()` a `remember=True` parameter and have `update_handoff` (and any counting caller) pass `remember=False`; or
advance a path's watermark only from `phase_*` loaders and from `write_record` itself.

### N2 (MEDIUM) pipeline.py:1619-1621 - the companion clears are not watermarked, so a concurrent writer's preserved rejection is deleted
`for fld, rej in ENTRY_REJECTION_COMPANIONS.items(): if fld in se and rej not in se: de.pop(rej)` runs for every paired disk
entry, not only the ones this call judged, and has no "did the caller author the absence" test. `repass_bands.py:136-149` sets
`scale_note_rejected` (and clears `scale_note`) on disk precisely so the note is preserved, and its comment relies on this
writer not popping it - but the pop fires for the pipeline's stale copy, which has `scale_note` and no rejection key.
Reproduction (pl_repro.py A): disk entry A gets `scale_note_rejected` and `scale_note=""` from another writer; the pipeline writes
a batch judging only entry B. Result: `landed True`, entry A `{'scale_note': '', 'scale_note_rejected': None}` - the preserved
text is gone. Same shape for `topic_rejected`, `subroom_rejected`, `category_rejected`.
Fix: treat the pop like a merged field - only pop when the entry is one this call judged (pass the touched index set) or when the
in-memory entry differs from its load-time watermark.

### N3 (MEDIUM) weave_index.py:391-395, 788-792 - `main --write` checks `LAST_UNREADABLE` from a different pass than the one that built the index; a record that heals between the two lands a short index, rc 0
`build()` calls `load_records()` (pass 1, `recs`), then `designations()`, which on a fresh process calls `load_records()` AGAIN
(pass 2). `LAST_UNREADABLE` is a global overwritten by the LAST pass. If a record is unreadable in pass 1 (a Windows denied open
during another writer's rename - the exact case sweep67 batch 07 F3 fixed) and readable in pass 2, `recs`/`index` lack it while
`LAST_UNREADABLE == []`, so the guard passes.
Reproduction (wi_repro.py): two records, one torn; a `silence.note` hook heals it when pass 1 notes it.
  torn stays torn       : rc 1, nothing written, "NOT WRITTEN: 1 record file(s) could not be read"   <- guard works
  torn heals mid-run    : rc 0, ENTITY_INDEX.json written with sources ['a'] only                   <- short index lands
Fix: pass the list already in hand - `known = designations(recs)` (an explicit list is never cached) - or snapshot
`LAST_UNREADABLE` immediately after build()'s own `load_records()` and check that copy.

### N4 (MEDIUM) pipeline.py:3491-3555 with manifest_builder.py:496-506 - run #68's phase 8 still emits 15 shared addresses among ready sources; 30 of 138 buildable sources, including most flagships, are held by generate and phase 8 says nothing
Live data (pw_live.py, read only): roll 215, `volume_codes` 205, 139 ready in COVERAGE, 138 buildable. A Set-level source (code
`II.A`) is numbered `II.A.1`, which is also the real Series code of another source, so both take the same job ids. 15 such codes
among ready sources: II.A.1 Baki/Dragon Ball Z, II.A.3 One Piece/Rosario + Vampire, II.A.4 Naruto/all the Fate series, II.F.2
Star Trek/Helldivers 1 & 2, II.F.3 Mass Effect/Star Fox, II.F.4 Halo/StarCraft, II.F.5 Destiny 1 & 2/Xenoblade, II.H.1 Cowboy
Bebop/Robocop, II.H.2 Metal Gear Solid/Sakamoto Days, II.L.1 The Lord of the Rings/Fire Emblem, II.L.2 all Elder Scrolls/God of
War, II.L.3 Diablo/League of Legends, II.L.4 Path of Exile/Legend of Zelda, II.L.5 all Final Fantasy/World of Warcraft, II.P.3 the
Skate games/Mario and his expanded universe (19 codes in total are shared across the whole roll).
`generate.hold_shared_addresses` correctly refuses to write them (both sides are held, printed by generate), so nothing is
overwritten. But phase 8 itself logs only "N job(s) across M source(s)", lands the manifest containing the colliding jobs, and
`gate_done` closes the phase; nothing in RUN_STATUS or the phase log says 30 sources will not be written until the owner rules.
The drill net (`_net_run68_phase8_volume_codes`) uses a fixture with no Series/Set overlap, so it cannot see this class.
Fix: make the Volume suffix unable to collide with the Series level (e.g. a distinct delimiter, or skip integers already owned
by a real Series in that Set) inside `volume_codes`; and have `phase_write` log the colliding sources, uncapped, or refuse to
close on them. Either is an owner-visible curatorial choice (Hard Rule 2), so this is filed rather than fixed.

### N5 (MEDIUM) pipeline.py:288-297, 2609-2618, 2682-2689 - the type-vs-category guard (order be5d399f163c) stops at `category`; the axis `worldseed` selects on (`topic == "Places"`) is unguarded, and the guard's premise is contradicted by the corpus
Measured over data/records (topic_scan.py): 133,239 Character/Person-typed entries; 0 now carry a Places category (the
13,394 were repaired), 0 carry a "contradicts type" `category_rejected` (the guard has not fired yet), but 2,209 carry
`topic == "Places"` while their category is not Places. `worldseed.py:427` selects `catalogued and topic == "Places"`, so each
of those is built into a world. At the same time the crawl's `type` is not reliable in every source: on a conservative
"is a <place noun>" lead test, at least 207 of the 2,209 are real places typed Character (Lindblum, Ambervale, Alfitaria, Lily
Hills, Shinmura, Earth, and Dune's Elacca, Jericha and Thalidei). For those the guard, when it fires, refuses a correct
"Places" answer and keeps them in Persons. So the guard is both one-sided (topic passes) and trusting of a noisy label. The
other ~2,000 (Senorita Mesquite, Levas Crompton, Marzipan City Police Department, Apple People) are persons or factions that
`worldseed` turns into worlds. UNVERIFIED which fraction of the 2,002 remainder is wrong; the counts are exact.
Fix (owner decision): apply the same contradiction test to `topic` (a Character/Person cannot be topic Places) and key the test
on something firmer than a per-wiki `type` label, or let the description lead decide when they disagree.

### N6 (LOW) weave_index.py:124-157 - `designations()` caches an answer built from a short pass under the valid signature
Only `_REC_CACHE` was made short-pass-safe. `designations()` computes from whatever `load_records()` returned and stores
`(sig, out)`; a record unreadable at that moment drops its parentheticals from the set, and the answer is served until the
signature moves. Reproduction (wi_repro2.py, `open` patched to raise PermissionError once): `bayverse` (a 3-name marker) not
learned, `_DESIGNATIONS` cached, and after the file is readable again with the same signature it is still not learned. Effect:
"Optimus (Bayverse)" and the G1 Optimus fold to one key (the expensive direction per the module header). Long-lived processes only.
Fix: skip the cache write when `LAST_UNREADABLE` is non-empty.

### N7 (LOW) pipeline.py:2097-2114 - phase 1 does not coerce cloud answer fields; a non-string `evidence` crashes the phase
Phase 2 got `_res_text`/`_entry_index` (order f6a751c55c84); phase 1 still does `(g.get("evidence") or "").strip()`,
`(got.get("ceiling_entity") or "").strip()`, `.rationale`. `_pool_answer_usable` only checks that the required keys exist.
Reproduction (pl_repro.py C, `ask_pool_first` stubbed to return `evidence: ["a","b"]`): `AttributeError: 'list' object has no
attribute 'strip'` out of `phase_synthesis`, i.e. "PHASE CRASHED", rc 1, ladder stalled. Only the cloud arm can produce it.
Fix: `_res_text(...)` on all four fields.

### N8 (LOW) roll.py:146-151 - `mutate` leaves its staged temp file when the dump raises
`except Exception: return False, ...` never removes `tmp`. Reproduction (roll_repro.py, a `set` in a row): returns
`(False, 'could not stage the new roll ...')` and `SWEEP_ROLL.json.<pid>.<tid>.0.tmp` remains beside the canonical roll. The pid+thread name
means it is never overwritten. This is the shape pipeline's `_dump_tmp` was written to close.
Fix: `os.remove(tmp)` in that handler.

### N9 (LOW) pipeline.py:3937 - stale citation "overnight.py:602-660"
`overnight.run()`'s `p.returncode` fold is at overnight.py:765-830. The repo rule is to cite by symbol.

### N10 (LOW, throughput) pipeline.py:877-900 - the widened watermark costs 10x the load it protects
`_desc_fingerprint` now sha1s `json.dumps` of 13 fields per entry. Measured (rec_time.py): loading all 216 records 3.3 s; the
watermark pass over them 35.1 s and +521 MB RSS (282,853 entries). marvel.json alone (59,170 entries) 7-13 s per call, and it runs
after EVERY landed `write_record` (line 1699) and at every `records()`. With N1's recount that is a 35 s stall about every 2 min
in the phase-2 daemon. Fix: hash one `repr(tuple)` per entry, or fingerprint only the entries of the batch written, or keep the
load-time values by reference instead of hashing.

## Questions (possible deliberate design; owner decides)
1. **Bone (Jeff Smith)** has a record (86 entries, all read) and a COVERAGE row but no roll row at all (roll 215 rows, 216 records).
   `phase_write` now refuses it "not on the roll" (correct), and since other sources build, the phase closes. Renamed row,
   deleted row, or an unrostered source?
2. **Phase 8 closes on partial refusal.** `elif refused:` only holds the phase open when NO job built. Any number of ready sources
   can be refused (e.g. `ContextOverflow` from the feats budget) and phase 8 is still marked done with the names only in
   pipeline.log. Documented as "name every refusal"; is closing acceptable for a partial one?
3. **generate.py does not read `roll.out_of_scope`.** The manifest is the only carrier of an exclusion. If phase 8 lands nothing
   (all ready sources held or empty) the previous manifest, possibly holding a source excluded since, stays on disk and generate
   runs it. Small window, but it is the one path where an owner exclusion is not re-asked.
4. **halo.py:207 and reference.py:376 write `data/HALO_ASSAYS.json` / `data/REFERENCE_ASSAYS.json` with no halt check**, while the
   twin `wh40k.py` is on the `_INTERLOCKED` roster. `standards.py` and `zfighters.py` read the reference file as the benchmark. Corpus
   writers only by design, or an omission of the 2026-09-28 sweep?
5. **navtree `--write` is refused for good, and state/NAVTREE_AUDIT.json is stale.** `navtree.build()` now audits 13,614 problems
   (13,458 built worlds not in SEVENFOLD.json, 82 in SEVENFOLD but not built, 74 duplicate designations). data/SEVENFOLD.json is
   from Aug 20, NAVTREE.json from Aug 24; nothing regenerates SEVENFOLD. state/NAVTREE_AUDIT.json (Aug 29) still says
   `{"count": 0}` because nothing reruns the audit. The refusal is the gate working; who schedules `sevenfold.py` and the audit?
6. Carried: `pipeline.py:1775`/`2116` "nine-measure" versus eleven axes; `halo.py:85` `M3 (Halo 2-3)`; `--phase N` sets the
   pointer to N+1; `_META_TERMS` unreachable when run as a script (all unchanged since sweep67).

## Cleared (read, no defect found; what was checked)
- pipeline `_merge_state`/`_fold_state`/`save_state` (absent-key, list-set and dict recursion cases traced); `_stored_cut`;
  `clean_band` vs `ceiling_band`; `write_record_catalogue` lone/clashing/idempotence and its CAS retry (B2); `_landed`/`_landed_cas`
  cleanup; `gate_done`/`mark_done`; `entry_settled`/`batch_settled`; `synthesis_blocks` `+`; `_unassayable_verdict_is_stale`;
  phase 5/6/7 absent-vs-corrupt handling; `main()` pointer logic and rc paths.
- **phase_write run #68 change, checked hard:** `volume_codes(roll_rows)` matches `main`'s numbering pool exactly (same exclusion and
  entry_count filters, assigned + unassigned); `excluded` is keyed by roll `name` and COVERAGE `source` equals it on every one of the 210
  rows; UNASSIGNED sources are held, out-of-scope sources are held, empty ones are counted, an unreadable roll raises (crash, not a
  silent empty); the bare-list manifest is accepted by generate.py (1255-1264). Live classification of the 139 ready sources: 138
  build, 1 refused (Bone). The drill fixture (`_EverySource`, drill.py:6958) and net (drill.py:28558) go red when the change is
  reverted (job ids `II.Z.9/Persons` twice; Gamma Out or Delta Loose included). verify_math 20ab's phase 8 cases return before
  the manifest_builder calls, so they are unaffected. Only N4 above stands against it.
- weave_index `_records_sig` (memo, scandir, None-signature paths), `staleness`/`stale_verdict` truth table, candidate/stopname/short-key
  rules, all-buckets printing, paired write with SPLIT report.
- policy.py: closed OPS/TYPES/ARG_REQUIRED, `absent` on `found`, uncapped sweeps, unreadable files folded into rc 1, rc 2 for an
  unlanded report. Every op used by the three tables fails (not passes) on an absent field, so no rule can produce a vacuous pass today.
- reference.py: 11 axes present for all three entities, delta/interval arithmetic and the `%02d` rendering of 7.62/4.31/4.08,
  calibration folded into rc, `--compare` keying by (host, entity).
- roll.py: `mutate` digest-before-read and re-apply per attempt, `update_rows` seen/missed, `exclude` raising on a typo and using the
  caller's `rows` only in memory. In-tree callers of `in_scope` pass their own loaded roll, so the fail-open default on an unreadable
  roll is not reachable today.
- halo.py: 11 axes, gated write, rc. navtree.py: node/name determinism (tie-breaks), audit arithmetic, gated writes.
