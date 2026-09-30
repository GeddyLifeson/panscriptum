# Sweep 68 (run68) - AUDIT batch 14

## Scope

Read in full, sequentially, with the Read tool (CLAUDE.md and BRIEF.md first):

| module | lines |
|---|---|
| src/binding_health.py | 1791 (3 chunks) |
| src/escalation.py | 1627 (3 chunks) |
| src/corpus_db.py | 1073 (2 chunks) |
| src/ingest_doc.py | 714 |
| src/worldseed.py | 556 |
| src/retry_synthesis.py | 433 |
| src/sweep.py | 387 |
| src/tuning.py | 290 |
| src/compress_store.py | 159 |

Strictly read-only against the project: nothing under src/, data/, state/, output/, prompts/ or
config.yaml was edited, no `main()` was run against the live tree, no model was called, no subagents.
Five scratch reproductions under `%TEMP%\aud68_14` (`r1_corpus.py` .. `r5_records.py`) redirect every
write path (`HERE`, `DB`, `HALT_FILE`, `RECORDS`, `DOCS`, `silence.note`, `workorders`, `health`) into that
directory. Nothing under the kit's `state/` or `data/` was touched.

Side observation (not this batch's finding): `state/HALT.json` stands in the live tree, `DRILL_BREACH`,
last written 2026-09-24 22:40 ("the catalog and the shelf agree in BOTH directions"). I did not create it
and did not touch it.

## Prior-audit cross-check (handoff/sweep67/AUDIT_batch*.md)

- b14 F1 (binding_health `run()` filed a raising `canary()` as `healthy: False` and quarantined): FIXED.
  `run()` now stores `healthy: None` with a `silence.note` (binding_health.py:1496-1509).
- b14 F5 (`--host` names matching nothing dropped when others match): FIXED. `_filter_hosts` returns the
  unmatched names and `run()` raises BINDING_FILTER_HOST_UNMATCHED (:1374-1377, :1420-1432).
- b14 F4 (binding_health stale line citations at :1456 / :1490): FIXED; the comments now cite by symbol.
- b14 Q5 (`known_present_titles`/`known_present_title` draw canary titles from struck entries): STILL
  STANDS, unchanged (:1333-1337, :1367-1370, no `excluded` test). Low impact, same blind spot as before.
- b13 F1 (ingest_doc image-only PDF ingested as "complete"): FIXED (`extract()` counts textless pages and
  raises OSError before anything is written, :162-169).
- b13 F5 (corpus_db unknown `--canned` exits 0): FIXED (:1024-1030). b13 F6 (duplicate source merged
  wrongly): FIXED (:279-288, sums and names the duplicate).
- b13 Q4 (ingest_doc stale `ingest_state.json` cursor on a re-extract): STILL STANDS, unchanged; reproduced
  here, filed as F4.
- b15 F4 (escalation `cleared` tested for truthiness): FIXED (`is not True` at :583, :678, :1453).
- b15 Q4 (`_land_halt` builds on the fail-closed stand-in): STILL STANDS, unchanged; reproduced with a
  persistently corrupt file (not only a transient read failure), filed as F6.
- b08 F7 (worldseed `--limit N --write` writes a partial roster): FIXED (:453-457 refuses).
- b08 F8 (short-stem `\w*` "attested" false positives): PARTLY FIXED. Short stems (war, sea, ash, ice, keep,
  plain) are now listed with suffixes; other stems keep the `\w*` tail. Filed as F5.
- b16 F5 (sweep.py absent inputs become an all-negative sweep): FIXED for HOSTS (refuses, :167-171); ROSETTA
  and NAVTREE warn on stderr. The related unreadable-record path is not covered, filed as F3.
- b04 F11 (tuning `cloud_success_rate` creates the db it probes): FIXED (`mode=ro`, :196). b04 Q5 (stale
  POOL_PROOF counted at full strength): STILL STANDS, unchanged and marked open in its own comment.
- b05 F9 (compress_store leaks its temp when the write fails): FIXED (:57-65).
- b06 (retry_synthesis exit code, `--only` typo, halt interlock): FIXED (`still_failing`, `unmatched_only`,
  `_assert_not_halted`).

## Findings

### F1. corpus_db `built_at` is stamped at the END of the rebuild, so freshness() calls a record written mid-rebuild "not stale"
`src/corpus_db.py:365` (`INSERT OR REPLACE INTO meta VALUES ('built_at', ?)`, `str(time.time())`), compared at
`:558` (`os.path.getmtime(p) > built`). Severity: MEDIUM (reproduced).

`rebuild()` reads each record inside the loop at :228-308 and then the (long) evidence scan at :324-363, and
only then writes `built_at`. A record rewritten after `rebuild()` read it but before `built_at` is stamped has
`mtime < built_at`, so `freshness()` reports `stale=False, "no record has been changed or deleted since the
index was built"` while the index holds the old rows. `t0 = time.time()` already exists at :143 and is the
correct stamp. The module's one promise is that the banner "cannot understate" staleness; this is the one
window where it does, and the crawl writes records continuously (the docstring itself says 8,613 entries in 27
minutes).

Repro (`r1_corpus.py`: a record is rewritten from a patched `address.spine_code_for` after it was read, inside
`rebuild()`; DB and HERE redirected):
```
rebuilt entries: 1
stale: False | newer_records: 0 | no record has been changed or deleted since the index was built
records now hold 3 entries, index holds 1
drift: (1, 3, 2, [])
```
Fix: `built_at = t0` (taken before the first read), not `time.time()` at the end.

### F2. worldseed `--write` lands a library-wide degenerate roster over the good one when ONOMASTICON / CONTINUITY_GROUPS are unreadable, rc 0
`src/worldseed.py:386-410` (warns only), `:473-477` (prints "INPUTS NOT FULLY READ"), `:507-542` (writes anyway).
Severity: MEDIUM (reproduced).

`build_all` records `LAST_BUILD["onomasticon"] = "unread"` and prints to stderr that every world takes the
`classical` fallback and `culture_set` is `antique` library-wide, "a failed read, not a property of the
catalogue". `main()` then prints its notice and goes on to `silence.write_json(WORLDSEEDS.json, ...)` and
returns 0. Nothing reads `LAST_BUILD` outside this file (grep over src/ finds no other reader), so the six
`build_all` consumers (burgs, navtree, profile, render, sevenfold, verify_math) get the same uniform library
with no flag. This is the module's own named failure ("a library that derived nothing and believes it
derived one") reached by the write path.

Repro (`r2_worldseed.py`: torn ONOMASTICON.json, no CONTINUITY_GROUPS.json, a prior roster with
`culture_set: oriental`): `rc = 0`, `LAST_BUILD = {'onomasticon': 'unread', 'continuity_groups': 'unread'}`,
file after: every row `antique`; the prior roster is gone.
Fix: in `--write`, refuse (rc 1, write nothing) when `LAST_BUILD["onomasticon"] != "ok"` or
`LAST_BUILD["continuity_groups"] != "ok"`; `"partial"` deserves the same refusal or an explicit flag.

### F3. sweep.py and worldseed --write build a whole-library file from `pipeline.records()`, which silently drops unreadable records
`src/sweep.py:162` (`recs = P.records()`), `:378` (`write_json(OUT, rows)`); `src/worldseed.py:414`,
`:539`; root cause `src/pipeline.py:792-804` (`except Exception: silence.note(...); continue`).
Severity: MEDIUM (worldseed reproduced; sweep by reading, same call).

A record that cannot be read at that instant (torn, AV lock, a rename in progress -- all ordinary on this
machine, and `data/records/` has "two writers as the normal situation") is skipped with a note, and the
downstream file is landed without that source. The sweep's own comment says CHARACTER_SWEEP.json is read "as
fact" by magnitude, standards, foreman and hostcheck; the file has no shrink floor (unlike
`axis_correlation.SHRINK_FLOOR`), and `report()` prints only `across N sources`, so a missing Marvel (17k
Persons) reads as a smaller universe in the shape of the real one. `worldseed --write` is the same, over
WORLDSEEDS.json.

Repro (`r5_records.py`, records dir redirected, one good record and one torn `marvel.json`):
```
PL.records() sources: ['Good'] | notes: [('pipeline.py:records-unreadable',)]
worldseed --write rc = 0 | roster before: 3 rows | after: ['Good::Kelvar']
```
(Marvel's two rows vanished; rc 0.) Fix: compare the count of `data/records/*.json` on disk with the sources
yielded and refuse to land when they disagree (corpus_db.rebuild already does exactly this: it names every
unreadable record).

### F4. ingest_doc: a re-extract does not reset or validate the resume cursor, so a re-supplied book is never mined and reports "complete"
`src/ingest_doc.py:138-188` (`extract()` rewrites pages.json only), `:361-381` (cursor accepted if it is a
non-negative int pair), `:470`, `:622-625`. Severity: MEDIUM (reproduced; b13 Q4, still unanswered).

`ingest_state.json` lives beside pages.json and survives the re-extract. `--pdf` again with a better PDF (an
OCR'd or corrected edition, the natural follow-up to the image-only refusal now in `extract()`) replaces the
corpus; `--mine` then resumes at the old `next`. If `next >= len(chunks)` the loop never runs and it prints
"ingest complete: 0 new entries merged", returns True, rc 0; if `next` is inside the new book, everything
before it is skipped.

Repro (`r3_ingest.py`, cursor `{"next": 20, "found": 5}` left from the first edition, new pages.json):
```
Book: 20 chunks, resuming at 20, 0 entries already known
ingest complete: 0 new entries merged this run (5 total for this book)
mine -> True    (model calls made: 0)
```
Fix: `extract()` records a digest of the new pages.json in the state file (or removes the cursor after
archiving it), and `mine()` refuses when the cursor's digest differs from the corpus it is about to read.

### F5. worldseed feature tables still label stem hits as "attested"
`src/worldseed.py:83` (`crag\w*`), `:84` (`nation\w*`), `:106` (`capital|golden|jewel ...\w*`), `:111`
(`engine|machine|steam\w*`). Severity: LOW (reproduced).

Sweep67 order 4c7cf744461d fixed the short stems in CLIMATE/CONDITION/TECH; the same class remains in the other
tables. `features("Cragmaw Hideout", ...)` -> landform `highland` attested (Cragmaw is a place name);
`"Capitalist Bloc"`, `"Goldenrod"` -> condition `thriving` attested; `"Engineer Guild"` -> tech `industrial`
attested. The `attested`/`seeded` tag exists so a reader can trust it. Fix: trailing `\b` or the intended
suffix list, as the ruling did for the short stems.

### F6. escalation `_land_halt` overwrites a corrupt HALT.json with the stand-in, destroying the original halt's reason
`src/escalation.py:583-586`, stand-in built at `:631-637`, read at `:640-662`. Severity: LOW (reproduced;
b15 Q4, unchanged).

When HALT.json is persistently unparseable (hand edit, foreign writer), `escalate(OWNER, ...)` reads the
stand-in, appends the new fault to it, and lands it over the corrupt file (the digest matches, so the CAS
passes). The library stays halted (fail-closed holds) but the first halt's `code`/`what`/`raised_at` are
gone from HALT.json; they survive only in `state/escalation.log`.

Repro (`r4_misc.py`, HALT_FILE redirected): file holding a torn `LEDGER_CORRUPT` halt, then a second OWNER
escalation: HALT.json becomes `code: HALT_FILE_UNREADABLE ... also: [SECOND_FAULT]`; `LEDGER_CORRUPT` no
longer appears in the file. Fix: copy the unreadable file aside (`HALT.json.unreadable-<ts>`) before
replacing it, or refuse to build on a stand-in (`return False, "unreadable"`) so the halt that is standing
is left alone.

### F7. escalation `pause()` accepts a non-positive duration
`src/escalation.py:771` (`if hours` / `float(hours)`). Severity: LOW (reproduced).
`--hours -2` writes a pause whose `until` is already past: `pause()` reports `landed=True`, `paused()` returns
`(False, "pause expired ...")` at once, and the CLI prints "paused: pause expired at ..." with rc 0. `--hours
0` is falsy, so it writes a pause with NO end time (indefinite), the opposite of what "0 hours" says. Fix:
`if hours is not None and hours <= 0: raise ValueError`.

### F8. retry_synthesis `--only` with no names, and `--smallest` with a non-positive N, select the wrong population
`src/retry_synthesis.py:365`, `:377-381`. Severity: LOW (by reading).
`--only` with `nargs="*"` and no values gives `[]`, which `if args.only:` reads as "no filter", so the run
retries every failed and stranded source (Marvel and DC among them, hours of model calls) when the operator
passed an empty list from a shell variable. `--smallest 0` is also falsy (runs everything); `--smallest -3`
slices `[: -3]` and drops the three LARGEST sources rather than selecting nothing. Fix: test `is not None`
and reject `<= 0`.

### F9. corpus_db `drift()` and `rebuild()` disagree on what an entry is; rebuild crashes on odd evidence fields
`src/corpus_db.py:645` versus `:299-308`; `:354`. Severity: LOW.
`drift()` counts `len(entries)` including non-dict rows, `rebuild()` skips them (`isinstance(e, dict)`), so a
record with a stray non-dict entry makes `gap` permanently non-zero although the index is current.
`rebuild()` also does `int(d.get("chars_read") or 0)` and `(d.get("provenance") or {}).get(...)` outside any
try, so one feats file with `chars_read: "12.5"` or a list `provenance` aborts the whole rebuild with a
traceback (loud, but the tmp database is left behind under its pid/thread name). Not run. Fix: count only dict
entries in `drift()`; wrap the per-file row build in the same try that already names unreadable evidence.

### F10. escalation `subsystem_stopped` reads a falsy stop row as "not stopped"
`src/escalation.py:1028-1031` (`if not hit: return False, ""`). Severity: LOW (by reading, hand-edit only).
`_read_stopped` validates that the ledger is an object but not its rows; `{"pipeline": null}` (or `""`,
`{}`, `false`) answers not stopped, while a truthy non-dict row raises AttributeError, which the one caller
(`overnight._manager_stopped`) turns into "stopped" (fail closed). The two malformed shapes therefore
disagree. Fix: `if hit is None: return False`, and treat any non-dict row as the unreadable marker.

## Questions (possibly deliberate)

1. Interlock roster (verify_math.py:7762-7770): the 2026-09-28 ruling reads "every hand-run tool that writes
   the corpus or the library's output refuses while HALTED". `sweep.py` (`main()` writes
   data/CHARACTER_SWEEP.json, which four modules read "as fact"), `worldseed.py --write` (WORLDSEEDS.json)
   and `corpus_db.py --rebuild` (state/corpus.db) write and are not on `_INTERLOCKED`, and none calls
   `assert_clear`. Was the roster of "twenty" drawn to exclude derived outputs, or were these missed? (The
   roster check `every module that consults the halt is on the roster` cannot see a module that does not
   consult it.)
2. `ingest_doc.register()` (:204-215) reads WIKI_HOSTS.json and writes it back whole with `write_json`, no
   compare-and-swap, while `hostcheck._land_hosts` and other writers of the same file use one. The window
   is small but it is the file the doctrine calls not reconstructible. Deliberate for a hand-run tool?
3. `retry_synthesis.synthesise()` returns a block for a source whose best band is `unassayed` (evidence
   failed `valid_scale_note`), and `--merge` writes it, after which `stranded_sources()` no longer lists the
   source (it now "has a synthesis"). Parity with `phase_synthesis`, but the source still has no ceiling
   and no band and nothing lists it as outstanding. Intended terminal state?
4. binding_health.py Q5 (b14) and tuning.py stale-proof Q (b04) stand as before.

## Cleared (read closely, found correct)

- binding_health.py: `_read_quarantine`/`quarantine`/`release` digest-before-read CAS, unreadable != empty,
  `_land_cas` unique temp and cleanup, `_report_not_written`/`_report_not_released` rungs, `_spread` (evenly
  stepped, distinct while n > want), `_probe_present`/`_probe_absent`/`_probe_reachable` three-valued arms
  (exceptions and throttling return None), `verdict()` truth table (every None branch reachable and none
  returns True), `binding_verdict` containment/tight/ruling logic, `run()` (empty-estate refusal, filtered
  merge under CAS, `--limit 0`, `checked`/`failed` over `merged`, canary-raised now None), `main()` exit
  codes.
- escalation.py: `escalate()` level coercion, `brief` whitelist, `_safe_name` injective truncation,
  `_halt_lock` fail-open, `_raise_halt` CAS plus read-back convergence, `clear()` ruling/person/signature
  order and its no-retry-on-changed-identity rule, `_by_a_person_at_the_cli`, `stop_subsystem`/
  `resume_subsystem_verdict` CAS loops, `_read_stopped` shape check, pause/unpause, `_a_probe_release`
  equality-based exemption.
- corpus_db.py: three-state spine/host sentinels, meta rows, deletion arm of `freshness()`, duplicate-source
  sum, `landed` verdict, canned queries (no LIMITs, NULL-first fixed), `--sql` read-only via `mode=ro`.
- ingest_doc.py: `record_path` ambiguity refusal, cursor absent/unreadable/wrong-shape, oversize page
  re-split, write-before-advance with `known` rewind, halt re-asked per chunk, category-miss count.
- retry_synthesis.py: shared block/prompt/band/gate code with pipeline, `save_side` merge and verdict,
  `do_merge` through `write_record`, unmerged names, exit code.
- sweep.py: `nested_run`, funnel report, HOSTS refusal, gated write. tuning.py: `regime()` AND of buckets and
  measured success, cached `buckets`, `workers()` ceiling. compress_store.py: unique temp, cleanup on both
  failure paths, verifying `load()`.
