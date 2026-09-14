# Sweep 58 — Batch 05 Audit

Modules read in full, top to bottom (offset-paged where needed):

| Module | Lines |
|---|---|
| src/feats.py | 2794 |
| src/corpus_db.py | 1040 |
| src/thread_integrity.py | 721 |
| src/feats_index.py | 595 |
| src/coverage.py | 456 |
| src/sweep.py | 374 |
| src/entity_match.py | 315 |
| src/repass_bands.py | 214 |

## Open-queue check

Ran `workorders.open_orders()` from the scratchpad and grepped for every module in this batch.
Relevant orders found: `c8dc624e4e02`, `6d594a775899`, `a724ec57e0d5`, `fe99e57e1993` (repass_bands.py
lines only), `abc943bb6464`, `e3b2668af9af`, `54db4a3baec8`, `5d0fa30e4b09`. No open order names
corpus_db.py, sweep.py, or entity_match.py. Findings against each are reported below as
`KNOWN <id>`, with a note on current accuracy — most of them have been fixed on disk this shift
and are no longer accurate as filed.

---

## src/feats.py (2794 lines)

Extremely mature, heavily self-documented module; read in full including `roll()`, the
transport/backoff machinery, `discover`/`resolve_title`, `strip_wikitext`/`_unwrap_templates`,
the axis gates, and `main()`.

- **KNOWN 54db4a3baec8** (`reads_as_wiki`, `pages:` arm of `evidence_for`). Still accurate as a
  live concern (agent R may be mid-edit on this file, order `54db4a3baec8`), but the code on
  disk at read time already matches the order's own remedy: `reads_as_wiki` lets
  `endpoint.source_pages`'s `PagesRegistryUnreadable` propagate rather than catching it (feats.py
  lines ~513-527), and `evidence_for`'s `pages:` branch comments confirm the same
  ("An unreadable registry RAISES here ... order 54db4a3baec8"). Nothing further to add; flagged
  KNOWN rather than re-verified line-by-line given the concurrent-edit warning.
- **KNOWN 6d594a775899** (feats-pages-read-includes-refused). **No longer accurate.** `evidence_for`
  now writes `pages_read` from `sorted(text)` (gate-passing pages only) and separately
  `pages_fetched`/`chars_fetched` for everything that arrived; the docstring at the `out = {...}`
  literal explicitly cites this order as closed ("`pages_read` HOLDS ONLY THE PAGES THAT PASSED
  THE GATE (order 6d594a775899; owner ruling 2026-09-08)"), and `roll()`'s `work()` counts
  `refused` off `pages_fetched`, not `pages_read`.
- Nothing else found. Checked in particular: the compare-and-swap-shaped `_throttle`/
  `note_throttled`/`note_ok` per-domain locking (correct — `_HOST_LOCKS[registrable_domain]` is
  held around every `_BACKOFF`/`_STRIKE` mutation), `_COUNTS_LOCK` around every shared-counter
  increment, `resolve_hosts`'s null-vs-missing-key handling, `_api_list_all`'s continuation-loop
  cap accounting, and `main()`'s escalation gate (`_ESC.assert_clear` first thing, fail-closed on
  a missing `escalation` module).

## src/corpus_db.py (1040 lines)

Read in full, including `rebuild()`, `freshness()`, `drift()`, `_freshness_banner()`, `CANNED`,
and `main()`.

- **DEFECT MAJOR** — `CANNED["worst_cited"]` silently drops every hosted source under 40 entries
  from the worst-covered ranking, exactly the Hard-Rule-0 shape already filed (and fixed this
  shift, with disclosure) against `coverage.py` in order `e3b2668af9af` — but this is a
  **separate, still-undisclosed site** that order does not cover and this shift's changes did not
  touch.

  ```python
  "worst_cited": "SELECT name, entries, cited, ROUND(100.0*cited/entries,1) pct "
                 "FROM source WHERE entries>=40 AND cited IS NOT NULL ORDER BY pct ASC",
  ```

  The `entries>=40` clause is a population cut applied *before* the ranking, with no companion
  query or banner naming what it excluded (contrast `unmeasured`, which the same file's own
  comment says exists specifically so the `cited IS NULL` exclusion is "NAMED rather than merely
  dropped from the work list" — no equivalent exists for the entries-under-40 exclusion). Failure
  scenario: a source with 30 entries and 0% cited never appears in `--canned worst_cited` or the
  Datasette page built from it (`datasette_metadata()` renders `CANNED` verbatim), and nothing in
  `main()`'s output, the query itself, or `_freshness_banner()` says any source was excluded by
  entry count. An operator using this canned query as the worklist for "which under-cited source
  needs attention" will never see it. Remedy: print a count (and ideally the names, per this
  module's own Hard-Rule-0 practice elsewhere) of hosted sources under the 40-entry floor,
  mirroring what `coverage.report()` now does for the identical cut (`below_floor` block).

- Nothing else found. Checked in particular: `rebuild()`'s unique-per-process tmp naming and
  landed/not-landed handling, the `SPINE_LOOKUP_FAILED`/`HOST_LOOKUP_FAILED` sentinel handling
  (a genuinely distinct third state, not conflated with NULL), `freshness()`'s deletion-tracking
  via `meta.record_files`, and the read-only `connect()`/`query()` path's failure handling in
  `main()` (both `--sql`/`--canned` and the bare-invocation path now guard `freshness()` before
  opening a possibly-absent database).

## src/thread_integrity.py (721 lines)

Read in full, including `load_thread_graph`, `_floor_verdict`, `classify`, and `main()`.

- **KNOWN a724ec57e0d5** (TI_DANGLING_VERDICT_STOPS_SHORT_OF_THE_LADDER). Filed as a QUESTION, not
  a defect, and it remains one. Partially stale as quoted: the order's own snippet
  (`dangling = counts.get('DANGLING', 0); return 1 if dangling else 0`) describes an earlier
  version of `main()`. The function on disk now also fails on `unresolvable` threads (escalated
  at SUPERVISOR, STEP4_PLAN §8) and on the `ASYMMETRIC-SUSPECT` regression floor
  (`_floor_verdict`), both gating the same `failed` flag as `dangling`. The underlying question —
  whether `IMPLIED-UNRECORDED`/`PARTIALLY-DANGLING` should also affect the exit code — is
  unchanged and still open; the two new gates the order's text does not mention do not close it.
- **QUESTION** — `main()` never calls `escalation.assert_clear()`, despite writing
  `state/THREAD_INTEGRITY_FLOOR.json` (via `_floor_verdict`) and issuing `SUPERVISOR`/`OWNER`
  escalations. This is consistent with every other module in this batch (`coverage.py`,
  `corpus_db.py`, `sweep.py` — none of the seven modules call `assert_clear`), and the one open
  order that names the halt-interlock gap (`1e6f99e54b25`,
  CORPUS_WRITERS_WITHOUT_A_HALT_INTERLOCK) scopes it to canonical corpus writers
  (`generate.py`, `retry_synthesis.py --merge`, `repass_bands.py --apply`, `resync_roll.py`) and
  does not name `thread_integrity.py`. Read as probably-deliberate (a diagnostic/report tool
  writing a small ratchet file, not a corpus mutator) rather than a defect, but flagged since the
  module does escalate to OWNER/SUPERVISOR on its own initiative without first checking whether
  the plant is already halted.
- Nothing else found. Checked in particular: `_charter_codes()`'s three-way
  absent/corrupt/wrong-shape handling, `load_thread_graph`'s fail-closed
  `ThreadGraphUnreadable` (never silently returns an empty graph), and `classify`'s
  both-directions test for RECIPROCAL vs ASYMMETRIC (order `7bffb5634d7a`, already fixed).

## src/feats_index.py (595 lines)

Read in full, including `host_to_sources`, `load_index`, `source_binding`, `feats_for_source`,
`binding_report`, `audit`, and `main()`.

- **KNOWN c8dc624e4e02** (FEATS_FOR_SOURCE_UNBOUND_HOST_SILENT). **No longer accurate.**
  `feats_for_source` now takes an optional `binding` out-channel stamped with
  `source_binding()`'s verdict (`"bound"|"pages"|"doc"|"unbound"|"unknown"`) whenever `hosts` is
  empty for the source, and unconditionally records the source in the module-level
  `_UNBOUND_ASKED` dict (read back via `unbound_asked()`) regardless of whether a caller passes
  the out-channel. The bare `[]` this order objected to is now always accompanied by a
  distinguishable, queryable reason.
- Confirms brief item: `binding_report()` (lines 416-455) now returns and `main()` prints both
  `unreadable_files` (a record that would not parse) and `sourceless_files` (parsed, but no
  `source` field) — the two failure classes order `5d0fa30e4b09` item 12 named as missing.
- Nothing else found. `_norm`'s no-parenthetical-stripping behaviour is documented accurately
  against its own docstring's earlier (corrected) claim; `qualifier`-shaped collisions in
  `load_index` and `feats_for_source` are both counted and named, uncapped.

## src/coverage.py (456 lines)

Read in full, including `state_of`, `_empty_state`, `_state_of_file`, `measure`, `report`, and
`main()`.

- **KNOWN e3b2668af9af** (COVERAGE_RANKINGS_DROP_SMALL_HOSTS_UNDISCLOSED). **No longer
  accurate.** `report()` still filters `entries>=40` before ranking (`have`/`below_floor` at
  lines 394-395), but the floor is now disclosed: `below_floor` is counted and printed
  ("N of M hosted sources excluded from both tables below: floor >=40 entries...") before either
  the WORST COVERED or BEST COVERED table, matching this shift's stated change. See the
  corpus_db.py finding above — the identical cut in `corpus_db.py`'s `worst_cited` canned query
  was **not** given the same treatment.
- Confirms brief item: `state_of()` now keeps the larger page count on a repeated READ verdict
  rather than the most-recently-seen one (line ~197, "keep the larger page count, not the more
  recent one" — order `3fc19ad4d1c6`'s remedy).
- Nothing else found. `measure()`'s fail-closed host-map read (4 retries, `SystemExit` on
  persistent failure rather than reporting a wrong-but-confident coverage figure) and
  `_so_load`/`_so_save`'s classifier-version-keyed cache invalidation were both read in full and
  are sound.

## src/sweep.py (374 lines)

Read in full, including `sweep()`, `nested_run`, `report()`, and `main()`.

Nothing found. This module's own docstring documents a comprehensive prior fix (the funnel-nesting
assertion that used to be false and printed a garbled negative drop, order `2420550a2b8e`) and the
current `nested_run`/`report` code tests nesting empirically rather than assuming it, exactly as
described. `main()`'s write of `data/CHARACTER_SWEEP.json` is gated on `silence.write_json`'s
verdict (denied replace returns 1 and says so) rather than assumed to have landed. Checked in
particular for Hard Rule 0 caps: the BIGGEST GAPS and REACHED BUT SILENT listings are uncapped
and named per their own in-line commentary; `DEEPEST EVIDENCE`'s `[:top]` is an explicit,
disclosed `--top` request.

## src/entity_match.py (315 lines)

Read in full — this is the whole file (`split_qualifier`, `qualifier_compatible`, `similarity`,
`candidates`, `best`, `embed_available`).

- Confirms brief item: the `STRONG`/`WEAK` ordering ratchet at module scope now `raise`s
  (`ValueError`) rather than using a bare `assert`, with an explicit comment citing the reason
  (`python -O` strips assertions) and the originating sweep57 question bundle
  (`bf1340bc3b3f`).
- Nothing else found. This is a small, self-contained, propose-only module (never merges the
  catalogue) with no network or filesystem writes in its core path; `embed_available()`'s Ollama
  probe is read-only and fails closed to `{"available": False}`. The qualifier gate
  (`qualifier_compatible`) is absolute as documented — no code path lets `similarity()` overrule
  it.

## src/repass_bands.py (214 lines)

Read in full — the whole file.

- **KNOWN abc943bb6464** (HARD_RULE_0_CUTS_SWEEP54, repass_bands.py lines 53/67/69 at time of
  filing) and **KNOWN fe99e57e1993** (UNMARKED_NAME_CUTS_SWEEP44, repass_bands.py lines
  52/66/68/126/137 at time of filing) — **both no longer accurate for this file.** The SURVIVORS
  and DEMOTED listings are fully uncapped (comments at lines 168-196 cite orders `89fc2eaf23f1`
  and note sweep42-batch04/sweep43-batch05 uncapped them), the `demoted_sources` roster is
  printed in full (order `215f9e7b86ff`), and a refused `scale_note` is preserved in
  `scale_note_rejected` via `PL._stored_cut` rather than destroyed (owner ruling 2026-09-08,
  closing order `4398d76f822f`) — this is the opposite of an unmarked cut. (`fe99e57e1993` bundles
  several other files this batch does not cover; only the repass_bands.py lines are addressed
  here.)
- **KNOWN 1e6f99e54b25** (CORPUS_WRITERS_WITHOUT_A_HALT_INTERLOCK). **Still accurate.** Confirmed
  directly: `repass_bands.py` has no `import escalation` and no `assert_clear` call anywhere in
  the file (`grep -n assert_clear src/repass_bands.py` — no hits), yet `main()`'s `--apply` path
  calls `PL.write_record(path, rec)` to demote Magnitude bands directly in `data/records/*.json` —
  a canonical corpus write, unconditionally on every `--apply` invocation. This is exactly the
  behaviour the order describes and it is unchanged.
- Nothing else found. The write-denial accounting (`touched`/`denied`, rc=1 on any denial) and
  the `PL.write_record` gate (order run #25's fix) were both read and are sound.

---

## Summary counts

- DEFECT: 1 (MAJOR — corpus_db.py `worst_cited`)
- QUESTION: 2 (thread_integrity.py DANGLING ladder scope, restated; thread_integrity.py's own
  missing `assert_clear`)
- KNOWN: 8 references across 6 orders touching this batch's modules (`54db4a3baec8`,
  `6d594a775899`, `c8dc624e4e02`, `e3b2668af9af`, `a724ec57e0d5`, `abc943bb6464` +
  `fe99e57e1993` for repass_bands.py, `1e6f99e54b25`) — 6 of these 8 are no longer accurate as
  filed (already fixed on disk this shift or earlier); `54db4a3baec8` and `1e6f99e54b25` remain
  accurate.
