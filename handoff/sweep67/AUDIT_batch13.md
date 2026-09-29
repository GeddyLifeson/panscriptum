# sweep67 batch13 audit (run67)

## Scope
Every line read, in chunks, no skimming:
assay.py (1949), health.py (1399), corpus_db.py (1053), ingest_doc.py (702), address.py (543),
cleanup.py (452), resync_roll.py (381), audit.py (275), whoruns.py (159). Read-only; repros are
scratch scripts under %TEMP% (a13.py, i13.py, w13.py, nav13.py). No project file touched.
Changed since sweep66: health.py (1319 -> 1399, Sep 28) and resync_roll.py (332 -> 381, Sep 28).
The other seven are unchanged since Sep 13-16.

## Prior-audit cross-check (handoff/sweep66)
- **sweep66 b14 DEFECT 1, health `_flush_samples` silent double-failure swallow: FIXED.**
  `health.py:462-473` now prints to stderr and `return`s (samples kept in memory), mirroring
  `_flush_ledger`. The outer `except Exception: pass` (:518) still exists but only covers
  genuinely unexpected errors now.
- sweep66 b14 dandwiki headline ("did not answer" for a 403): FIXED. `health.py:763-765`
  distinguishes `http-NNN` / ok ("answered without a usable API") from silence. Shelved-host
  handling added (:710-737, :850-859); `shelved_hosts()` returns a dict, iteration is correct.
- sweep66 b09 Q1 (resync_roll closing figure summed from memory): FIXED. `resync_roll.py:349-370`
  reads the roll back from disk after `roll.mutate`, labels dry-run/readback-failed basis.
- sweep66 b09 Q2 / open orders 1e6f99e54b25, 21c075e5e2d6 (no halt interlock in resync_roll,
  health --reopen --go): FIXED. `_assert_not_halted` added to both (`resync_roll.py:37-61,81-83`;
  `health.py:1305-1329,1352-1354`), narrow to write paths, fail-closed on ImportError.
- sweep66 b13 (assay/address): nothing changed; dead-code retentions (`band_for_quantity`,
  `null_instrument`, `interval_from_hands`) still marked as ruled (assay.py:354-361, 1664-1671,
  1802-1813). Cleared again below, but see finding 2 for `interval_from_hands`.
- sweep66 b15 (corpus_db, ingest_doc), b16 (whoruns), b10 (audit), b04 (cleanup): no open
  finding; the mechanisms they traced are all still present. Two new items on corpus_db and
  whoruns are below (not previously raised).

## Findings

### 1. ingest_doc.py:154-157, 170, 458-614 -- an image-only or partly image-only PDF ingests as "complete" (MAJOR class, low frequency)
`extract()` keeps a page only `if t:` (non-empty after `_clean`), with no count of pages that
yielded no text and no check that `out` is non-empty. An all-scanned PDF writes `pages.json` as
`{}`, `register()` binds `doc:<slug>`, and `mine()` builds zero chunks and prints
"ingest complete: 0 new entries merged" and returns True; `main()` exits 0.
Repro (scratch temp tree, `_assert_not_halted` stubbed): pages.json `{}` ->
`Scanbook: 0 chunks, resuming at 0 ... ingest complete: 0 new entries merged this run` /
`mine() -> True`. A book with 40% scanned pages is the same fault in partial form: the missing
pages are simply absent from the page-keyed corpus, with "extracted N pages" not saying N of how
many. This is the module's own named danger ("a partial run must never look complete").
Fix: in `extract()` count `len(doc)` vs `len(out)`, print/return the number of textless pages,
and raise OSError (same refusal path as the write denial) when `out` is empty.

### 2. assay.py:1881-1882 -- `interval_from_hands` hangs on large finite readings (MINOR; zero production callers)
The coverage `while any(abs(v-centre) > interval ...): interval = round(interval + 0.01, 2)` is
linear in the deviation/0.01 and never terminates once `interval` is large enough that adding
0.01 is absorbed by float precision. `_check_readings` deliberately accepts any finite value.
Repro: `{"AVAR":0,"QUILL":0,"MOTH":3000}` -> 2000.0 in 0.08 s; `MOTH=1e17` did not return in 5 s
(and cannot ever). Fix: closed form, `interval = max(interval, math.ceil(max_dev*100)/100)`, or
refuse a reading range beyond the owner's eventual bound (left open by `_check_readings`).
Dead code today, so latent; it is the future publisher of the charter's +/-.

### 3. assay.py:334-351 -- `axis_score` turns a NaN quantity into the maximum reading (MINOR, latent)
`x is None or x <= 0` does not catch NaN; `math.log(nan)` -> nan, and
`max(0.0, min(1.0, nan))` returns 1.0 (min keeps the first arg when the comparison is False).
Repro: `axis_score(nan,"M3","ruin")` -> 10.0, `axis_score(inf,...)` -> 10.0 (inf is arguably
right), `axis_score(nan,"M10","ruin")` -> 0.0. So a could-not-measure returns the top score, the
exact shape the docstring says this function was fixed against. Not reachable today: every
production caller (anchors.py:78-101) passes literals; `_check_scores`/`_check_readings`/
`_check_weights` all already refuse non-finite values, this door is the only one without it.
Fix: `if x is None or not math.isfinite(x) or x <= 0: return None` (or refuse NaN like the
sibling doors).

### 4. whoruns.py:69-70 -- attached `-mMOD` / `-cCODE` spellings are read as "an interpreter flag, keep looking" (MINOR)
`script_of` refuses only the exact tokens `-m` and `-c`. `-mpyflakes` and `-c"..."` begin with
"-", are skipped, and the next `.py` token is returned. Repro: `['python','-mpyflakes','src/mutate.py']`
-> `src/mutate.py` (should be None: it lints it); `['python','-cprint(1)','src/mutate.py']`
likewise. That is the false-positive class this module exists to stop, arriving through the
spelling its docstring does not mention (only `-Xutf8`/`-Wignore` attached forms are discussed).
Fix: before the `startswith("-")` arm, `if tok.startswith(("-m","-c")) and tok not in (...)`:
return None (mind that `-mx` must not collide with other flags; none of the real flags start
with -m or -c except `-c`/`-m` themselves).

### 5. corpus_db.py:1011-1026 -- an unknown `--canned NAME` exits 0 with a status line (MINOR)
`sql = a.sql or CANNED.get(a.canned or "")`: a typo'd canned name yields `sql=None`, falls into
the "no query given" branch, prints "corpus.db built N min ago" plus the canned list and returns
0. A script running `--canned worst_citd` sees rc 0 and no rows. Fix: if `a.canned` is set and
not in CANNED, `print("unknown canned query ...")` and return 2.

### 6. corpus_db.py:281-295 -- two records declaring one source are silently merged wrongly (MINOR, latent)
`INSERT OR REPLACE INTO source` keeps the last file's row (`entries` = that file's count) while
`entry` receives rows from both files, so `source.entries` disagrees with `COUNT(*) FROM entry`
for that source and `worst_cited`'s `100.0*cited/entries` uses the wrong denominator. `resync_roll`
already detects and reports this (dupes); corpus_db does not. Measured today: 0 duplicate
sources among the 216 records, so latent. Fix: track seen `src`, add to the `unreadable`-style
list and the meta row.

## Questions (not asserted as defects)
1. ingest_doc.py:390-405, 424-427, 490-492 -- `known` dedups by normalised name across the whole
   book, so a later mention of an already-known name never merges its description, and a name
   that is both a person and a place keeps only the first category. Is first-mention-wins the
   intended rule for a source book (it is the wiki-side rule too)?
2. ingest_doc.py:396-397 -- an oversize page is re-split at fixed 9000-character offsets with no
   overlap, so a name straddling the cut is seen by neither half. The comment says this mirrors
   read.py; is a small overlap wanted, or is the mirror deliberate?
3. ingest_doc.py:195-196 -- `register()` keeps a `pages:` binding (a URL-list sentinel, not a
   live wiki) and returns it, so `--pdf` on such a source extracts a corpus that nothing will
   read. Should a `pages:` source be repointed to `doc:` like an unbound one, or is `pages:`
   meant to outrank a static text? (None values in WIKI_HOSTS are handled.)
4. ingest_doc.py:407-422 vs extract() -- re-running `--pdf` for the same source with a different
   PDF (or a re-extraction that changes chunk boundaries) does not reset or validate
   `ingest_state.json`; a stale cursor can point past or into the middle of the new corpus
   (past the end -> "ingest complete" with nothing mined). Intended, given "delete it only to
   re-mine"?
5. resync_roll.py:197-202, 260-276 -- the key-wise `_apply` lands this run's `entry_count`
   computed from an earlier disk read. A cataloguer that grows a record and its roll row inside
   the walk window is regressed to the older count until the next resync. Narrow window, and
   the old whole-file clobber is gone, but a `>=`-style guard (only raise) or a re-count inside
   `_apply` would close it. Deliberate?
6. audit.py:246-271 -- the RANDOM SAMPLE / BANDED SAMPLE blocks are documented reading aids
   (`--sample`), not a universe truncation; the invariants pass is exhaustive. Noting only
   because Hard Rule 0 forbids "sample" as a listing: confirm this is understood as exempt.
7. audit.py:264 -- `banded` admits `magnitude == ""` (only None/"unassayed" excluded) although
   the invariant pass flags "" as off-ladder; the banded sample could show a non-claim as one.
   Trivial; intended?

## Cleared (read in full; mechanisms verified, no defect)
- **assay.py**: five-way `axis_score` refusal ordering; constants table + `_check_constants`
  (sigma monotonicity, BAND_EDGES symmetry/strict increase, ATTESTATION_FLOOR, partition of
  WEIGHTS vs BAND_EDGES vs NON_ENERGETIC_AXES); `_check_scores/weights/readings/hand_readings`
  (NaN scores are refused: `not (0 <= nan <= 10)`); `_interval` full covariance with
  `max(var+cov,0)`; `assay()` wsum guard, `[0.995,1)` and negative clamps, promotion/demotion
  flags; `calibration_report` no longer mutates shared tables; `instrument()` sentinel handling;
  `regress_test`; `_rho_doc` one-shot cache with announced fallback.
- **health.py**: `_flush`/`_flush_ledger`/`_flush_samples` CAS retry, settle-only-on-landed,
  preserve-the-wreck; re-entrancy guard; `check_api_paths` family bucketing + quarantine + shelved
  probing; `check_caches` uncapped stat pass, 25-file floor as weaker verdict, excluded/shelved/
  quarantined excusal, fail-closed on unreadable records; `check_state`; `reopen_stranded`
  digest-before-read, byte compare, `_cas_land`; `--reopen` exit code (None vs []); halt gate.
  `set(reopen)` rebuilt per element at :1189 costs 0.24 s on the live 13,794-key list against
  1,000 reopened keys (measured); INFO only.
- **corpus_db.py**: three-state spine/host sentinels, meta rows, staleness by mtime plus
  deleted-record arm, `drift()` naming unreadable files, readonly connect, unique temp name,
  `replace_retry` verdict, CANNED uncapped, `_cell` marked cut, datasette write gated.
- **ingest_doc.py**: `record_path` ambiguity refusal, cursor absent-vs-unreadable-vs-wrong-shape,
  advance-on-write, denied-cursor accounting, bad-category counter, halt re-asked per chunk,
  no description slice.
- **address.py**: four-stage `spine_code_for` (exact, letter-equality, most-specific containment
  with single-token opens/closes and remainder rules, token-set fallback with same-set rule);
  `promote` never demotes and repairs unrankable tiers noisily; `slugify` uncapped;
  `build_address` marked dead and stale as ruled.
- **cleanup.py**: `_NAV` prefix arms measured against all 274,005 catalogued names: 36 hits, all
  wiki furniture ("Character*", "Characters*", one "Gameplay Elements of ...", one
  "Trophies (Diablo Immortal)", one "Downloadable Content") -- no real entity struck; ruby `?`
  and parenthetical functions decline on pure ASCII; `clean_ceiling` refuses ambiguous prefix;
  gated `write_record`, exit code, uncapped rosters.
- **resync_roll.py**: argparse dry-run, halt gate on write path only, per-row guards, status rule
  respects OUT_OF_SCOPE on the fresh row, denied-write branch returns 1 with pre-fix figures,
  read-back closing line with basis, caveat travels with the figure. (Rows/records that are
  non-dict or carry `entries: null` would raise at :94/:178/:197; the live roll and records
  are clean, and the failure is a loud crash, not a wrong number.)
- **audit.py**: `_JUNK` per-alternative anchoring, one-key-one-row synthesis ladder, per-class
  denominators, whole-value printing, every occurrence listed.
- **whoruns.py**: own-PID exclusion, `-m`/`-c` refusal (exact tokens), `-X/-W` two-token skip,
  `_in_this_tree` narrowing, tri-state None/[]/hits and grep-style exit codes.
