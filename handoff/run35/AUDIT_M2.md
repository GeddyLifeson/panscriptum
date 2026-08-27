# run35, wave 2, batch M2 -- audit notes

Twenty-four orders worked. Owned files touched: `src/sweep.py`, `src/coverage.py`,
`src/ingest_doc.py`, `src/backfill.py`, `src/wiki_source.py`, `src/overwatch.py`,
`src/catalogue_web.py`, `src/hostcheck.py`, `src/scout.py`, `src/feats.py`, `src/read.py`.
Seventeen closed FIXED; one closed as a verified PARTIAL fix (`6d6c02c903b0`, half the sites
owned, half not); six left open because their real fix lives in a file this batch does not own,
or (one case) requires a public-signature/design decision the rules say not to make
unilaterally.

**d49cda5cc058** (the priority order). FIXED. `sweep.sweep()` called
`cachekey.load(F.CACHE, host, e["name"])` with no `on_corrupt`, so a truncated or unparseable
evidence-cache file returned `(None, None)` -- identical to an entity nothing was ever mined
for, on the evidence base every published measurement rests on. `sweep.load` (sweep.py:62)
exists to make exactly this distinction and has no caller. Added
`on_corrupt=lambda fp: silence.note("sweep.py:evidence-unreadable")` to the call, matching the
identical `_corrupt`-callback pattern already used at `feats.py:937` and `read.py:670`.

**00d8436bb86d**. FIXED. Seven stale numeric `silence.note` tags in `wiki_source.py` (lines
190/196/241/318/590/609/636, each naming an unrelated line) retagged with stable content
labels: `get-httperror`, `get-connect-error` (the shared `read.py:188`-style merge of `_get`'s
two distinct except-handlers), `verify-search-api`, `resolve-candidate-api`,
`category-members-api`, `extracts-api`, `rank-by-size-api`. Matches the four sites the module
already converted (wiki_source.py:289-292).

**09405680f175**. FIXED. `backfill.py --audit` printed `rows[:26]` with no indication of the
remainder. Added `catalog.py:66-67`'s pattern: `if len(rows) > 26: print(f"  ... and {len(rows)
- 26} more")`.

**1090feb5f6f1**. LEFT OPEN (real fix not owned). Confirmed: `recover_folder_records.py`'s
`slug()` comment says "Matches ingest.py's slug()" -- there is no `src/ingest.py`, and
`ingest_doc.slug` actually lacks the `[:60]` truncation this one has. The function it matches
character-for-character is `catalogue_web.slug` (catalogue_web.py:68-69). `recover_folder_
records.py` is not in this batch's owned-file list.

**2b10b8d71c45**. FIXED. `ingest_doc.py main()` discarded `pipeline.write_record`'s landed
verdict when stamping provenance. `write_record` returns `pipeline._landed` (True/False) and
never raises. Added `if not P.write_record(rp, rec): print(...)` so a denied write is reported
rather than read as success; the existing `"ingest_doc" not in provenance` guard already makes
a re-run retry naturally.

**322cc5ab6f31**. FIXED. Two stale `silence.note` tags in `overwatch.structure()` (line 331
tagged `:193`, actually the import/reconcile handler; line 341 tagged `:202`, actually the
estate handler) retagged `structure-import-reconcile` and `structure-estate`.

**3784508bc4da**. FIXED (comment only; constant NOT deleted per the no-delete-dead-code rule).
`catalogue_web.CATEGORY_SCAN_DEPTH`'s comment described a scan-then-rank relationship against
`MAX_PER_CATEGORY` that no longer exists (categories are pulled with `limit=None`, ranked with
`top=None`). Rewrote the comment to say plainly that the constant is dead and kept only as a
name other code may import, matching `MAX_PER_CATEGORY`'s own treatment two lines above.
`MAX_PER_SOURCE` untouched (still `None`, Hard Rule 0).

**6a83762ab9bb**. LEFT OPEN (real fix not owned). Confirmed by reading `hosts.py:157-160`:
`HC.candidates(source, cur, by=by)` omits `hosts=prim` (loaded at hosts.py:142), silently
disabling `hostcheck.candidates()`'s NEIGHBOURS generator (gated on `if by and hosts:`,
hostcheck.py:335) -- the only caller in the tree that omits it; `hostcheck.py:536` and `:878`
both pass `hosts=hosts`. `hosts.py` is not in this batch's owned-file list.

**6d6c02c903b0**. PARTIAL, closed with that stated. Retagged the 4 stale `read.py` sites this
order lists (owned): the shared `read.py:188` tag, used at two distinct `_ask()`
except-handlers (quick-pool attempt and backoff-ladder attempt, merging two failure modes into
one health-ledger key) split into `ask-quick-pool` / `ask-backoff-ladder`; `read.py:354`
(actually `queue()`'s per-entity evidence read) -> `queue-evidence-read`; `read.py:379`
(actually `run()`'s `work()` wrapper around `read_entity`) -> `work-read-entity`. The four
`chain.py` sites this same order lists (chain.py:169/276/283/345) are untouched -- `chain.py` is
not in this batch's owned-file list. Left for whichever batch owns it.

**7c13fa26cf6d**. FIXED. `hostcheck.py`'s `--purge` argparse help advertised a phantom
safeguard ("remove rosters the audit rejected AND whose host was independently rejected") that
`purge()`'s own docstring (643-648) says the code never had -- confirmed against the body
(670-676): targets come from `--source` and the audit rows alone; `hosts.get(src)` is only
logged, never gated on. Rewrote the help text to describe the real requirement: an explicit
`--source` list after a human reads the audit shortlist.

**7dd11bb4dae8**. FIXED, with the order's central claim corrected against current source.
Verified: `scout.py`'s `WIKI_HOSTS.json`/`SCOUT_ATTEMPTS.json`/`SCOUT_BLOCKED.json` writes
already moved off `_land` onto `_mutate`'s CAS read-modify-write (order d3313adbf641,
pid+attempt-named temp files) -- `_land`'s only live caller lands `data/SCOUT.json`,
single-writer, so the specific collision with `hostcheck.py`'s `_land` on `WIKI_HOSTS.json` this
order describes is not live today. Hardened `_land` anyway: rewrote it to delegate to
`silence.write_json` (the same run #33 fix already applied to the identical `runguard._land`),
removing the fixed-temp-name pattern for this and any future caller, and corrected the
docstring's stale claim about who writes `WIKI_HOSTS.json`. `hostcheck.py:77`'s own `_land`
still builds the fixed name for the files it actually writes, but `hostcheck.py` is not owned by
this batch.

**93e99cd8bd7e**. FIXED. Two hand-rolled `path + ".tmp"` writes left behind by the
`silence.write_json` migration: `read_entity`'s final cache write (runs in every pool worker,
and discarded `replace_retry`'s verdict) and `_save_qcache`. Both rewritten through
`silence.write_json` (pid+thread temp names, matching the sibling fix already applied to
`_chunk_put` at read.py:645). `read_entity`'s write now checks the landed verdict and notes
`read.py:read-entity-write-denied` on failure instead of silently treating a denied write as a
complete cache.

**96e8ac88c6f8**. LEFT OPEN (real fix not owned). Confirmed: `endpoint.source_pages()`'s
docstring says "`{}` when it has none" but both return paths (failure and success-with-nothing)
return `[]`. The one caller (`feats.py:975`) already reads it as a list, so the code is right
and the docstring is wrong. `endpoint.py` is not in this batch's owned-file list.

**9beb0391c8ab**. LEFT OPEN (design/signature decision). Confirmed: `feats.page_looks_real(text,
title="", wiki=True)` never reads `title` in its body -- it appears only in the signature, not
even in the docstring. `binding_health.py:183` (not owned) passes one. Fixing this properly
means either (a) designing real title-based verification logic (what a soft-404/wrong-article
mismatch actually looks like, a judgment call this batch's rules say not to make unilaterally)
or (b) dropping the parameter and updating the call site in `binding_health.py`, which is on
this batch's explicit do-not-edit list and changes a function's public signature. Left open with
the finding confirmed true.

**a8c3f7ee6965**. FIXED. `feats.api()` called `note_ok(host)` before `json.loads(_body)`, so a
200 carrying an HTML challenge/login-wall page (the case the `json.JSONDecodeError` handler
exists for) decayed backoff and zeroed `_STRIKE[host]` before the parse failure was ever
recorded -- a host refusing every call with an interstitial could never accumulate
`THROTTLE_STRIKES` and reach `binding_health.quarantine`. Reordered: parse first
(`parsed = json.loads(_body)`), call `note_ok(host)` only after the parse succeeds, then
`return parsed`. A 404 arrives as `HTTPError` and is unaffected.

**b41b17c1b12b**. FIXED. `catalogue_web.catalogue()`'s fetch-progress heartbeat closed over
`_short`, which was bound only in the discovery loop (`for canon in ws.CATEGORY_KEYWORDS`) and
never rebound in the fetch loop (`for canon, cats, titles in planned`), so every
"`<class> fetching d/t`" line named the last class discovery had categories for, not the class
in flight. Added `_short = canon.split(" (")[0][:16]` at the top of the fetch loop body.

**b9769e6a9ef6**. FIXED. `read.run()`'s `done["skipped"]` (summed from
`out["chunks_skipped"]`) was accumulated and never printed. Added it to the periodic progress
line and the closing "done in Xh" line.

**ba9f7292b400**. FIXED. `read._gate()` tested and set `_GATE_STATE["at"]`/`"regime"` with no
lock, so every in-flight worker (up to `GATE_CLOUD_N=16`) could pass a stale 120s-recheck window
at once and all call `tuning.regime()` simultaneously on each recheck. Added `_GATE_LOCK`
(same shape as the existing `_TRANSPORT_LOCK`) with double-checked locking: the common-case read
stays lock-free, and only one thread performs the recheck+write once the window has actually
expired.

**cf719be96588**. FIXED. Verified against current source: `read_entity`'s "RANKED AND CAPPED
... twelve covers the whole of most subjects" comment justified a default `cap_chunks=12` that
no longer exists (`cap_chunks` defaults to `None`/uncapped, Hard Rule 0), contradicting the
correct comment three lines below and the code (`chunks.sort()` ranks; `cap_chunks` only slices
if a human explicitly passes `--chunks`). Rewrote to "RANKED, NOT CAPPED", kept the still-true
density-ranking rationale, dropped the stale cap justification.

**d7a7bbb70bf1**. LEFT OPEN (real fix not owned). Confirmed: `health.py:288`'s quarantine
exemption spells the cache-directory key as `h.replace(".", "_").replace("-", "_")` instead of
calling `cachekey.host_dir` (`_SANITISE.sub("_", host)[:40]`), in the same comment block that
warns a wrong spelling makes the exemption a silent no-op. `health.py` is not in this batch's
owned-file list.

**d7a7bbb70bf1 / de9a39b2b47c** grouping note: also confirmed `de9a39b2b47c` independently.
LEFT OPEN (real fix not owned). `weave_index.load_records()`'s docstring says "63MB across 217
files (marvel.json alone is 27MB)"; `data/records/` holds 216 `.json` files on disk, and
`corpus_db.py`'s own header already agrees with the disk (216) -- so the fix is entirely inside
`weave_index.py`, which is not in this batch's owned-file list. `corpus_db.py` itself needed no
change.

**eb626e4d9dde**. FIXED. Two stale `silence.note` tags in `catalogue_web.py`: line 102 (now
105) tagged `catalogue_web.py:79` (actually `catalogue_composite`'s category handler) ->
`composite-category-members`; line 315 (now 341) tagged `catalogue_web.py:266` (actually
`main`'s `--shortfall` `COMPLETENESS.json` read) -> `shortfall-completeness-read`.

**f7577dc52f5c**. FIXED. `feats.strip_wikitext`'s table-cell rule only stripped attributes with
a QUOTED value and lowercase name, and only the leading line-start pipe, so unquoted
(`colspan=2`) and capitalised (`Style=`) attributes and inline `||` cell separators survived
into mined prose. Broadened the attribute alternation to accept any-case names with a quoted
(single or double) or bare unquoted value, and added a second substitution treating inline
`||`/`!!` the same as the line-start marker (attributes and all), turning it into a newline so
each cell becomes its own unit. Verified against all 3 measured cases from the order's evidence,
including the already-working lowercase+quoted case (`style="width:10em" | Kaioken` still ->
`Kaioken`).

## Checks proposed

`handoff/run35/checks_M2.py` -- 16 standalone `check_*` functions, all run and passing against
the fixed source: the `sweep.py` on-corrupt callback (exercised end-to-end against a genuinely
truncated cache file), the `coverage._so_save` dirty-gate, the `ingest_doc.py` write-verdict
check, the `backfill.py --audit` remainder line, a sweep over `wiki_source.py`/`overwatch.py`/
`catalogue_web.py` for any remaining bare numeric `silence.note` tag, the `catalogue_web.py`
`_short` rebind and `CATEGORY_SCAN_DEPTH` comment honesty (plus `MAX_PER_SOURCE` staying
`None`), the `hostcheck.py --purge` help text, `feats.api()`'s note-ok-after-parse ordering,
`feats.strip_wikitext`'s three measured table-cell cases, `scout._land`'s and `read.py`'s two
cache writers' move to `silence.write_json` (checked as an actual `tmp = ... + ".tmp"`
assignment statement via regex, not a bare substring, since the fixes' own explanatory comments
quote the retired code by name), `read._gate`'s lock, and `read.run()`'s skipped-counter print.

## Note on order scope and file ownership

Several orders in this batch named defects that span both an owned and an unowned file (most
directly `6d6c02c903b0`, listing four `read.py` sites and four `chain.py` sites under one
finding). Where the owned half of a split order was a clean, independent fix, it was made and
the order was closed with an explicit note on what remained unaddressed and why, rather than
leaving a fully-fixable owned defect unfixed because a sibling file could not be touched in the
same pass.
