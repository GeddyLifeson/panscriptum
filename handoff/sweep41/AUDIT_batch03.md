# SWEEP41 — BATCH 03 AUDIT

Auditor: sweep41-batch03. Scope: `src/pipeline.py`, `src/manifest_builder.py`,
`src/withdraw_chapters.py`, `src/thread_integrity.py`, `src/cleanup.py`, `src/tempus.py`,
`src/compress_store.py`, `src/catalog.py` — 5,144 lines, every one read in full (verified by line
count per file against `wc -l`, matching the task total exactly).

This is an audit, not a repair shift. No file in `src/` was edited. `prose_enabled`,
`step4_enabled` and `escalation.clear()` were not touched.

## Method

Read every module top to bottom (no sampling). For each candidate finding, cross-checked
`state/workorders.json` for an existing open order covering the same code before filing anything,
to avoid re-filing what earlier sweeps already caught (this batch's modules turned out to already
carry 24 open orders from sweeps 34/39/40, most of them well-evidenced and still matching the
current source). Only genuinely new, source-verified findings were filed.

## New finding filed

**0a45c595655b** — MAJOR — `WRITE_RECORD_CATALOGUE_FOLD_INERT_FOR_ALWAYS_POPULATED_FIELDS`

`pipeline.write_record_catalogue`'s per-entry fold (pipeline.py:620-623) is:

```python
for fld in MERGED_ENTRY_FIELDS:
    dv, sv = de.get(fld), se.get(fld)
    if dv and (not sv or sv == "unassayed"):
        se[fld] = dv
```

`de` is the disk (curated) entry, `se` is the fresh cast's matching entry. This only lets a disk
value win when the fresh value is falsy or the `"unassayed"` sentinel — correct for `magnitude`
and `topic`, which no catalogue writer ever populates on a fresh entry (confirmed by grep: no
such key anywhere in catalogue_web.py), so `sv` is always `None` there and the disk judgment
always wins.

But `category` and `description` are also in `MERGED_ENTRY_FIELDS` — added by order 4866dfb2d9fc
specifically so cleanup.py's and phase_entrypass's corrections would "survive the writer that
carries them" — and catalogue_web.py:246 and :458 (and every other write_record_catalogue caller
that builds fresh entries: catalogue_aurora.py, catalogue_codex.py, ingest_doc.py, backfill.py)
sets BOTH of those fields to a real, non-empty value on **every** entry it emits, unconditionally.
So for these two fields `sv` is essentially always truthy, the disk value never wins, and:

1. phase_entrypass's category corrections ("an ability filed as an object... is a POWER, never a
   Vessel") are silently reverted to catalogue_web's initial guess the next time that source is
   re-catalogued or has entities appended against already-present names.
2. cleanup.`clean_description`'s markup stripping (cleanup.py:143-147 — grep confirms it is
   called from nowhere else in the tree) is silently reverted to raw wiki text — ruby
   annotations, citation stubs, `WP` link markers — for any entry the fresh cast re-emits under
   the same name. This is the description text "the evidence every later volume quotes from," so
   the regression reaches finished prose.

Not hypothetical: `write_record`'s own docstring cites a real precedent for whole-source
re-catalogue against an already-processed record ("marvel.json went from 1,051 entries to 30,207
in one such pass"), and `ingest_doc.py`'s entire purpose is appending to existing records through
this exact writer.

Filed on the traced mechanism plus two concrete, grep-confirmed producer call sites; not
reproduced against live data with a measured count (that is left to whoever picks up the order —
handler RUN, since the fix is a design decision about what signal distinguishes "curated" from
"freshly guessed" for a field the fresh cast always populates, not a one-line change).

## Existing open orders re-verified against current source (all still accurate, none re-filed)

All 24 pre-existing open orders whose `where` touches this batch's files were checked against the
current file content. Every one still matches (code, line-shifted but unchanged in substance).
None was stale, none was already fixed. Listed by id, not repeated in full here:

`0058f581b42b`, `00ef174b7495`, `0291835411d9`, `18f7673b77ce`, `19c507a16430`, `1a9c237dda4d`,
`3f4d2d058fdc`, `541384445ec3`, `5c8a7bc883e7`, `7716ac4884cc`, `8d8ba5377fb6`, `9038da917a70`,
`a3d518d078c3`, `a724ec57e0d5`, `b186bc4dad8f`, `b67dc1990af6` (not re-filed per instructions),
`b813fc5a37e2`, `bd3f737f4241`, `c391a1f77e42`, `c3eb0a80bb8a`, `c410fcfc7c08`, `c8dc624e4e02`,
`ceb139670422`, `d1794144717c`, `db36d589713e`, `ed6e66c0c12d`.

## Candidates investigated and NOT filed

- **`write_record_catalogue`'s per-entry fold restoring a stale `excluded` reason onto a fresh
  cast that omits it.** Initially looked like "absence read as clean" in reverse. Traced fully:
  no catalogue-side writer ever sets `excluded` on a fresh entry (that field is exclusively
  cleanup.py's), so there is no code path where a catalogue rebuild deliberately means to
  *lift* an exclusion and gets overridden — the fold's behaviour here (disk's exclusion always
  wins) is the correct and intended one, matching the reverted-exclusion history the module's
  own comments describe. Not a bug.
- **`pipeline.py`'s meta-language-ban functions (`meta_violations`, `assert_in_universe`)
  defined textually after `if __name__ == "__main__": main()`.** Unusual layout, but harmless:
  when imported as a module (the only way these functions are ever called — by generate.py and
  audit.py) the whole file executes top to bottom and both are defined normally; `main()` never
  calls either of them itself. No functional defect.
- **`catalog.cmd_read`'s `os.path.exists(raw_path)` conflating "absent" with "cannot stat"
  (permission/lock)**, structurally the same class of check `withdraw_chapters._file_state` was
  hardened against. Investigated and NOT filed: unlike withdraw_chapters (where a wrong verdict
  destructively deletes a catalog record), here a false "doesn't exist" only causes a fallback
  to `compress_store.load()` on the compressed copy — which is itself content-hash-verified
  against tampering — so the worst case is reading a verified backup instead of the primary, not
  data loss or a wrong answer. Judged not worth a work order.
- **`tempus.rung_description_length` / `band_resolution` band-edge ordering.** Checked whether
  `assay.LADDER`'s ordering (weak-to-strong or strong-to-first) could make `band_resolution`'s
  `log2(hi/lo)` go negative for a mis-ordered ladder. Verified `LADDER = ["M0", ..., "M10"]` is
  ascending by strength, so the arithmetic is correct as written. No finding.

## Coverage notes

Every module in this batch had already been read by earlier sweeps in enough depth to leave
22-24 well-evidenced open orders behind, several with live measurements from 2026-08 runs. This
batch's contribution is one new finding that only becomes visible by tracing the interaction
between `write_record_catalogue`'s generic per-entry fold and the *specific* fields each
catalogue-producing module actually populates on a fresh cast — a cross-file argument that a
single-file read of pipeline.py alone would not surface without also checking catalogue_web.py
and cleanup.py, which this pass did.
