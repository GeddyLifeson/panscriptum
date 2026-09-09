# Sweep 48, Batch 13 — Audit

Modules assigned and lines read (full file, read end to end, no sampling):

| Module | Total lines | Lines read |
|---|---|---|
| src/assay.py | 1914 | 1-1914 (all) |
| src/health.py | 1221 | 1-1221 (all) |
| src/wiki_source.py | 789 | 1-789 (all) |
| src/threads.py | 671 | 1-671 (all) |
| src/catalogue_codex.py | 511 | 1-511 (all) |
| src/hosts.py | 396 | 1-396 (all) |
| src/deprecated/catalogue_local.py | 333 | 1-333 (all) |
| src/context_budget.py | 296 | 1-296 (all) |

All findings below were checked against the live source at the quoted line numbers (re-verified
with `grep -n` / `sed -n` after locating them by content search, not assumed from memory of an
earlier read).

---

## Finding 1 — MAJOR — `src/health.py:973-1069` (`reopen_stranded`) — stale read then blind
overwrite of `state/PIPELINE_STATE.json`, the file `pipeline.py` also owns

**What is wrong.** `reopen_stranded()` reads `state/PIPELINE_STATE.json` exactly once, at the
top of the function:

```
994:        with open(path, encoding="utf-8") as f:
995:            st = json.load(f)
```

It then iterates the whole corpus (`for _, r in P.records(): ...`, a potentially slow walk) to
decide which batches to reopen, and — only if `--go` was passed — patches one field of the
*same* `st` object read at the top and writes the *whole document* back:

```
1050:        st["done"]["entrypass"] = [k for k in done if k not in set(reopen)]
...
1064:        if silence.write_json(path, st, indent=1):
```

`silence.write_json` (src/silence.py:773) is atomic (pid+thread temp name, then a rename) but is
**not** a compare-and-swap: it never checks that the file on disk still matches what was read.
There is no re-read, no digest comparison, and no retry-on-conflict here — contrast this with
`health.py`'s own `_flush_ledger`/`_cas_land` machinery twenty lines above in the *same file*
(src/health.py:227-337), which takes a digest *before* the read specifically so that "anything
landing afterwards refuses this write instead of disappearing under it," and which the file's
own docstring calls out as the fix for exactly this class of bug ("THIS WAS A LOST UPDATE, IN
THE RECORDER", src/health.py:262).

The function's own docstring says this tool is meant to run concurrently with a live pipeline:

> "and it is invoked precisely when a pipeline may be live, since that is when batches strand."
> (src/health.py:1054-1055)

and `pipeline.py`'s own docs independently warn that concurrent writers to this exact file are a
known hazard ("Run one instance only. Two concurrent runners both write `PIPELINE_STATE.json`
... that happened on 2026-08-21 and the records survived by luck," src/pipeline.py:2389-2390).
So `health.py --reopen --go` is a *second*, undocumented writer of the same file, running in
exactly the window pipeline.py warns about, and it carries a stale full-document snapshot back
to disk with no staleness check at all. If `pipeline.py` writes any other part of
`PIPELINE_STATE.json` (a different phase's `done` key, `failed`, anything) between health.py's
read at line 995 and its write at line 1064, that write is silently clobbered — the exact "lost
update" shape the surrounding comments in this same file spend several hundred lines
documenting and fixing for `state/failures.json`, just not applied here.

**How I verified it.** Read `reopen_stranded` in full (src/health.py:973-1069). Confirmed
`silence.write_json` performs no compare-and-swap by reading its definition
(src/silence.py:773-800) and contrasting it with `silence.replace_if_unchanged`
(src/silence.py:624) and `_cas_land` (src/health.py:227-245), which health.py uses for its own
ledger file. Confirmed pipeline.py's single-instance caveat at src/pipeline.py:2389-2391.

**Proposed remedy.** Give `reopen_stranded`'s write the same treatment `_flush_ledger` already
has in this file: take `silence.digest_of(path)` before the initial read, and land through
`silence.replace_if_unchanged` (re-reading and re-merging the `done.entrypass` patch against the
live file on a refusal) instead of `silence.write_json` on a stale in-memory copy. Since this
tool only ever touches one key (`done.entrypass`), the merge is cheap and the CAS retry loop can
be small, mirroring `FLUSH_CAS_ATTEMPTS`.

---

## Finding 2 — MINOR — stale line-number citations in `src/assay.py` (Hard Rule 6)

Three self-citations inside `assay.py` point at line numbers that no longer match the code they
describe, because comments were added above them after the citations were written:

1. **src/assay.py:811** — "the mutation survivor at L228 is what exposed the problem" (referring
   to `axis_score`'s `if not hi or hi <= lo: return None` refusal). That refusal is currently at
   **line 348**, not 228 (drift of ~120 lines).
2. **src/assay.py:890** — "anchors.py:427 is worse: it indexes INSTRUMENT_WINDOWS[b] for every b
   in LADDER with no guard at all." The unguarded `INSTRUMENT_WINDOWS[b]` indexing in
   `anchors.py` is currently at **lines 546 and 551**, not 427.
3. **src/assay.py:1868** — "The mutation survivor at :1392 (`<=` flipped to `>`)" (referring to
   the `covers_all_signatures` field). That field is currently defined at **line 1872**, not
   1392 (drift of ~480 lines).

By contrast, two other self-citations in the same file remain accurate and should not be
"corrected" by a future pass that assumes all such citations are equally stale:
`anchors.py:34` ("does `import assay as A`", src/assay.py:238) is exactly right, and
`axis_correlation.py:284-292` (the `load()` function, src/assay.py:1097) is exactly right too.

**How I verified it.** Located each cited construct with `grep -n` against the current file
content and compared to the quoted number.

**Proposed remedy.** Update the three stale numbers, or switch them to the symbol-based citation
style this project already uses elsewhere when a citation has drifted before (e.g.
`catalogue_web.py:150` → `catalogue_web.catalogue_composite`'s dedup comment, and
`health.py`'s own `summary()` docstring switching dashboard/standards citations to
`silence.note` tags for exactly this reason — see Finding 3).

---

## Finding 3 — MINOR — stale line-number citations pointing out of `src/health.py`, including
one inside a docstring that already warns about this exact failure mode

`health.py:summary()`'s docstring (src/health.py:483-500) explicitly discusses the fragility of
citing line numbers in another file, and switches to citing `silence.note` tags instead
specifically because an earlier citation ("dashboard.py:331-339, standards.py:797-800") had
already drifted. It then states, as of its own writing:

> "As of this writing they sit at dashboard.py:350-360 and standards.py:1000-1028." (src/health.py:499-500)

Both of *those* numbers have now drifted too: the actual `silence.note("dashboard.py:failures")`
guard is at **src/dashboard.py:375**, and the actual `silence.note("standards.py:ledger")` guard
is at **src/standards.py:1086** — off by roughly 15-25 and 58-86 lines respectively.

Separately, in `src/deprecated/catalogue_local.py` (one of this batch's own modules): three
*other* files — `src/liveness.py:122`, `src/sweep_plan.py:47`, and `src/silence.py:264` — each
describe this deprecated file as "(280 lines)". The file is actually **333 lines**
(`wc -l src/deprecated/catalogue_local.py` = 333) — the file grew by 53 lines (mostly the
in-file quarantine-notice block documented at the top of the file) after those three citations
were written.

**How I verified it.** `grep -n "silence.note(\"dashboard.py:failures\")" src/dashboard.py` and
the equivalent for standards.py; `wc -l src/deprecated/catalogue_local.py` plus
`grep -n "280 lines" src/liveness.py src/sweep_plan.py src/silence.py`.

**Proposed remedy.** Health.py's own doctrine (cite the `silence.note` tag, not a line number)
already solves the dashboard/standards case if the two numbers are simply dropped from the
sentence. For the "(280 lines)" citations, either drop the parenthetical line count (the file's
identity as "the deprecated module in `src/deprecated/`" does not need a line count to make its
point) or update it to 333.

---

## Finding 4 — MINOR — stale cross-file line citations in `src/wiki_source.py`

Two citations to `catalogue_web.py` inside `wiki_source.py` have drifted:

1. **src/wiki_source.py:450** — "matching the comment at catalogue_web.py:257-259, which
   describes exactly this." The matching comment about `catalogue()`'s single-wiki path is
   currently at **src/catalogue_web.py:324** (drift of ~65 lines).
2. **src/wiki_source.py:665** — "`catalogue_composite`'s per-category `try/except`
   (catalogue_web.py:220-224)." That try/except is currently at
   **src/catalogue_web.py:274-279** (drift of ~55 lines).

**How I verified it.** Located both target constructs in `catalogue_web.py` with `grep -n` and
compared to the cited ranges.

**Proposed remedy.** Same as Finding 2/3: update the numbers, or cite by function name
(`catalogue_composite`'s per-category loop) the way this same file already does elsewhere for a
citation it knows has drifted once before (src/wiki_source.py's own `clean_titles` docstring,
which explicitly moved off a stale `catalogue_web.py:150` citation for this exact reason).

---

## Finding 5 — INFO — approximate self-citation in `src/catalogue_codex.py` has also drifted

`src/catalogue_codex.py:103-104` hedges its own citation ("see its own comment at
:326-329ish") when pointing at where `main()` calls `record_path()`. The actual call site is now
at **src/catalogue_codex.py:443**, well outside even the hedged range. Given the "-ish" already
signals low confidence, I am reporting this as INFO rather than MINOR, but it is worth folding
into the same cleanup pass as Findings 2-4 since it is the same defect class (Hard Rule 6).

---

## What I read and found nothing wrong in

- **src/assay.py** core arithmetic: `axis_score`'s band-lookup ordering, the Layer-1 refusals in
  `_check_scores` / `_check_weights` / `_check_readings` (including NaN/inf handling, verified
  by hand-tracing the comparison logic), `_interval`'s variance-plus-covariance composition, the
  ceiling/floor clamping in `assay()`, and `instrument()`'s Constitution-mean and bounded-output
  logic. All of the many "check that cannot fail" self-audits already present in the file's own
  comments (the `or 1.0` backstop, the top-rung saturation branch, the BAND_EDGES monotonicity
  checks in `_check_constants`) were traced by hand and are, as claimed, either genuinely
  reachable guards or explicitly-labelled structural backstops — none of them is a live
  check-that-cannot-fail masquerading as a real one.
- **src/health.py**: the failures.json ledger's compare-and-swap write path
  (`_flush_ledger`/`_flush_samples`/`_cas_land`), which is exactly the CAS discipline Finding 1
  says is missing from `reopen_stranded`; `check_api_paths`, `check_caches`, and `check_state`'s
  quarantine/exclusion/backlog-vs-loss reasoning; the self-test-vs-real ledger routing
  (`is_selftest`). No other check-that-cannot-fire or fail-open path found.
- **src/wiki_source.py**: rate limiting and retry logic in `_get`, `resolve_wiki`'s
  hosts-file-first resolution and non-fandom short-circuit, the `CATEGORY_MIN_PAGES` floor and
  its `category_floor_report` honesty about being unable to count what it excludes,
  `all_categories`'/`category_members`'/`extracts`' raise-on-transport-failure discipline (all
  three were fixed from silent-partial-return to raise, and all three actually do raise on the
  live code path).
- **src/threads.py**: the T1/T2 derivation in `build()`, the `cohort_family`/`category_path`
  finest-shared-room matching, `threads_for`'s refuse-rather-than-blank contract, and `verify`'s
  round-tripped-graph checks. The one `[:n]` the module's own docstring flags
  (`parts[:2]` in `cohort_family`) is exactly what it says it is — an address decomposition, not
  a truncation of a reader-facing list.
- **src/catalogue_codex.py**: the manifest-count cross-check in `parse_codex`, the
  norm()-collision reporting for section titles/register descriptions/duplicate elements
  (all uncapped, all printed before the write summary as the module claims), and the
  compare-and-swap roll write via `roll.update_rows` at the end of `main()`.
- **src/hosts.py**: read in full. This module's "almost nothing calls it" state is already
  recorded by the owner (order 3fb312a72435) and is not re-reported here. Checked it for
  internal consistency instead: `KEEP = ("holds", "partial")` matches the verdict strings
  `hostcheck.score` actually emits (`src/hostcheck.py:890,892`); the `_PROBE_FAILED` /
  `None` / thin-roster three-way distinction in `discover()` is honoured all the way through to
  the printed summary; `add()`'s three-state return (`True`/`False`/`None`) is honoured by its
  one real caller inside `discover()`. Found nothing inconsistent with what a caller would need.
- **src/deprecated/catalogue_local.py**: confirmed the top-of-file `raise SystemExit(_REFUSAL)`
  (with the `--help` exemption) makes every line below it — including the writes to
  `data/records/` and non-atomic `data/SWEEP_ROLL.json` rewrite the file's own header names as
  dangerous — genuinely unreachable on both `import` and direct execution, for any argv that is
  not exactly `-h`/`--help`.
- **src/context_budget.py**: hand-traced the derivation chain end to end
  (`window` → `content_budget_chars` → `feats_block_budget`) including the
  prose-vs-content token ratio split and the `JOB_OVERHEAD_CHARS`/`METADATA_INFLATION`
  corrections, and confirmed the arithmetic direction (converting a token budget back to
  characters via the *content* ratio, charging JOB_OVERHEAD at content rather than prose price)
  is internally consistent with the file's own stated reasoning.
