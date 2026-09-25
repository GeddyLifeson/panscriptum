# sweep61 batch07 audit

Scope (all under `src/`), read in full, start to finish:

- `standards.py` (2477 lines)
- `rigor.py` (1132 lines)
- `wiki_source.py` (808 lines)
- `withdraw_chapters.py` (614 lines)
- `backfill.py` (494 lines)
- `retry_synthesis.py` (379 lines)
- `catalogue_aurora.py` (328 lines)
- `ledger.py` (220 lines)
- `repass_bands.py` (214 lines)

Total 6,666 lines, all read (no sampling). Read-only: no files under `src/`, `state/`, `data/`,
`config.yaml` or any ledger were modified.

## Findings

### 1. VERIFIED — `standards.py`, "cached records that were fully read" standard (function `check()`, ~lines 1234–1259), false-positive breach on entities with long `pages` lists

```python
_readfeats = os.path.join(HERE, "data", "readfeats")
...
for fp in _g.glob(os.path.join(_readfeats, "**", "*.json"), recursive=True):
    with open(fp, encoding="utf-8") as f:
        head = f.read(700)
    if '"chunks_unanswered": 0' not in head and "chunks_unanswered" in head:
        unans_files += 1
    elif "chunks_unanswered" not in head:
        unans_files += 1          # written before the guard existed
```

`read.py`'s `read_entity` (around line 983) writes the cache record with `pages` *before*
`chunks_unanswered` in field order: `{"entity":.., "host":.., "pages": sorted(text),
"chunks_read":.., "chunks_unanswered":.., ...}`, dumped with `indent=1`
(`silence.write_json(path, out, indent=1, ...)`, `read.py:1019`). `pages` is a per-Hard-Rule-0
*uncapped* list of every wiki page an entity's evidence was pulled from. When that list is long
enough, `chunks_unanswered` lands past byte 700 of the file, so `head` (only the first 700 bytes)
never contains the key at all — even though the full record has it and its value is `0` (fully
answered). The `elif "chunks_unanswered" not in head` branch then increments `unans_files`,
under the comment "written before the guard existed" — but the record is not old, it is just a
rich one. This is a HIGH-severity standard (`MAX_UNANSWERED_RECORDS = 0`) whose remedy text says
"Delete those files so the entities are read again" — i.e. it tells an operator to destroy a
complete, correctly-cached record and pay to re-read it from the model.

**Verified against the real corpus on disk** (`data/readfeats/**/*.json`, 3,463 files): 39 files
have `chunks_unanswered` genuinely present in the full JSON but absent from the first 700 bytes.
Checked one directly:

```
data/readfeats/finalfantasy_fandom_com/Final_Fantasy_VII_enemy_abilities.json
  chunks_unanswered (full file): 0        <- fully answered, NOT incomplete
  pages: 24 entries
  "chunks_unanswered" in head(700 bytes): False
```

So this file — a complete, correctly-answered record — is miscounted as an unanswered/incomplete
one purely because its `pages` array is long (a direct consequence of this project's own
mandatory-uncapped-listing rule elsewhere in the codebase). All 10 worst offenders found are
`finalfantasy.fandom.com` "enemy abilities" compilation pages (13–31 KB files, `chunks_unanswered`
sitting at byte offset 713–1840). These are exactly the richest, most cross-referenced entities —
the ones the library most needs kept, not deleted.

Verification method: read every file's first 700 bytes and its full contents with
`miniconda3/python.exe`, confirmed the key is absent from the 700-byte head but present (value
`0`) in the full parse, for 39/3463 files; hand-checked one file's actual JSON structure and byte
offsets to confirm the mechanism (field order + uncapped `pages` list pushes the key out of the
probe window).

### QUESTION (not a finding) — `rigor.py`, `adjudication_beta()` (~line 670)

```python
k = max(1, min(n_laws_touched, M))
```

Forces `k >= 1` even when `n_laws_touched == 0`, so a hypothetical caller asking "what does 0
laws touched cost" would be charged `log2(C(M,1))` bits rather than 0. Not exercised anywhere in
the tree — the only caller (`rigor.main()`'s `_AUDIT_ROWS`) always passes `laws >= 1`, and
`verify_math.py`'s two call sites use `(3,4)`/`(1,4)`/loop values `>=1` — so this is dormant
rather than live, and may well be intentional (an adjudication that touches zero laws may not be
a meaningful call to price at all). Flagged as a question, not a defect.

## Everything else

The remaining eight modules, and the rest of `standards.py`, are unusually heavily
self-documented: nearly every non-obvious line carries a comment recording a prior defect, its
fix, and how it was verified (order IDs, run numbers, measured byte counts). I checked each of
these documented fixes against the current code rather than re-reporting them, per the brief.
No tautologies, fail-open guards, unmarked truncations, or false doc/code mismatches were found
beyond the one above. Nothing looked like dead code beyond what is already labelled
"REPORTED DEAD, NOT DELETED" with its own reader-count justification (`ledger.py`'s
`STANDARD_GLYPH`, `CONDENSATES`, `currency_status`).

## Summary

- Findings by kind: 1 VERIFIED real bug (category 4, with a category-3/Hard-Rule-0 flavor: an
  uncapped listing elsewhere defeats a fixed-size read here); 1 QUESTION (not counted as a
  finding).
- VERIFIED: `standards.py`, `check()`'s "cached records that were fully read" standard —
  `head = f.read(700)` truncation misreads any `data/readfeats/*.json` record whose `pages`
  array pushes `chunks_unanswered` past byte 700 as unanswered, even when the record is complete
  (`chunks_unanswered: 0`), confirmed live on 39/3,463 cache files including
  `finalfantasy_fandom_com/Final_Fantasy_VII_enemy_abilities.json`.

## Coverage

Recorded via `sweep_plan.record('run61', [...], batch=7)` for all nine modules listed above.
