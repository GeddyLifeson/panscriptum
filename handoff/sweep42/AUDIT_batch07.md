# sweep42 batch 7 — audit

Modules read in full: `src/feats.py` (1900 lines), `src/corpus_db.py` (795), `src/threads.py`
(630), `src/weave_index.py` (516), `src/catalogue_codex.py` (404),
`src/deprecated/catalogue_local.py` (333), `src/recover_folder_records.py` (283),
`src/cachekey.py` (190).

General note: all eight modules are already extremely heavily self-audited — most carry
multi-paragraph comments documenting past bugs (with `order <hash>` / `run #N` references) that
were found and fixed by earlier sweeps, including several previous Hard Rule 0 truncation fixes.
`src/deprecated/catalogue_local.py` is fully quarantined: it raises `SystemExit` at import time
(before any config is read or any file touched) except for `--help`, so the bugs documented in
its own header comment (bare-write to `data/records/`, non-atomic roll write, `main()` returning
`None`, the `[:60]` slug cap, `per_cat[key] = 0` on a failed call) are dead code the file itself
says are "DELIBERATELY NOT REPAIRED" as the record of a failure mode. Per the task brief ("a
safety that stops work is not a fault"), these are not filed as findings.

## Confirmed defects

1. **`src/recover_folder_records.py:253`** — Hard Rule 0 display truncation, unmarked.
   ```python
   print(f"  {n:5d}  {name[:48]:50s} -> {fn}")
   ```
   In the `written` report loop (uncapped in *count* — every recovered source is printed), each
   source **name** is silently cut to 48 characters with no ellipsis or "cut" marker, then padded
   to 50 columns with blank space. This is the exact anti-pattern `src/corpus_db.py`'s `_cell()`
   was written to fix elsewhere in this same codebase (order 6160ef68b229: "the renderer printed
   `str(v)[:40]` with nothing to say a value had been cut... A MARKER, NOT REMOVAL... refuses it
   when nothing says the cut happened"). This very file's own header (line 57-63) already
   discusses a source name ("Who Framed Roger Rabbit (incl. all content from its associated
   crossover-toon IPs)") long enough to have broken an identical cap elsewhere in the pipeline, so
   the failure mode is not hypothetical here. Confidence: **high** (unambiguous unmarked cut on a
   report a person reads to confirm what was written; low blast radius since only the console
   line is affected, not the record on disk).

2. **`src/weave_index.py:463-464`** — same anti-pattern, in the "most cross-attested entities
   (the weave's backbone)" leaderboard:
   ```python
   print(f"   {hits[0]['name'][:26]:28s} {len(srcs):2d} sources: "
         f"{', '.join(s[:16] for s in srcs[:5])}"
         f"{f' … and {len(srcs) - 5} more sources' if len(srcs) > 5 else ''}")
   ```
   `srcs[:5]` (the per-entity source list) is properly marked with "… and N more sources", and
   the `TOP_N = 18` list-level cut is marked with a stated floor (order 4cea367c9235) — both
   already fixed correctly. But the **entity name** (`hits[0]['name'][:26]`) and **each source
   name** (`s[:16]`) inside that same line are cut with no ellipsis or indication anything was
   removed. A long entity or source name (this corpus is full of them — see finding 1) prints as
   a shorter, different-looking string with nothing to say so. Confidence: **high**, same
   reasoning as finding 1: it is the identical unmarked-truncation shape this codebase has
   explicitly ruled against elsewhere (`corpus_db._cell`), just not yet applied here.

Both findings are display-only: the underlying data (`data/records/*.json`,
`WEAVE_CANDIDATES.json`, `ENTITY_INDEX.json`) is untouched and uncapped: only the console report
a person reads shows a possibly-misleading shortened string.

## Questions (possibly deliberate, not filed as fixes)

3. **`src/feats.py:1174`** — the `_QUANTITY` regex's unit alternation includes a bare `kili` as
   one of the matchable unit words:
   ```python
   r"kili|power\s*level|degrees?|kelvin|celsius|mach|times\s+the\s+speed\s+of\s+light)\b",
   ```
   No mass unit (`grams?`, `kilograms?`, `pounds?`, `tons?` is present but that's already listed
   separately for explosive-yield tons) appears anywhere else in the list, and `kili` does not
   read as a complete, real physical unit word on its own (it's not a prefix of `kilomet(?:er|re)`
   or `kiloton`, which are already spelled out fully elsewhere in the same alternation). Two
   readings: either this is a corruption/leftover fragment of an intended unit word (this file
   elsewhere has a documented history of literal control-characters and eaten regex escapes
   corrupting exactly this kind of pattern — see the `_BAD`/`_SRC` self-check at lines 415-419),
   or it is a deliberate, terse match for a real in-fiction scale unit this project's corpus uses
   (some franchises spell power-level units idiosyncratically). Not confirmed either way from
   reading the file alone. Confidence in it being a defect: **low-medium** — flagging rather than
   fixing, per the audit brief.

## Not filed as findings (explicitly deliberate / already fixed in-file)

- `src/deprecated/catalogue_local.py` — the whole module is a documented, hard-refusing
  quarantine; the bugs in its dead code below the `SystemExit` are the deliberate historical
  record the file exists to keep, not live defects.
- `src/feats.py`'s `_show()` (lines 1780-1787), `discover()`, `resolve_hosts()`'s unprobed-source
  printer, `roll()`'s summary counters, `corpus_db.py`'s `CANNED` queries and `_cell()`,
  `threads.py`'s cohort/T2 edge emission, and `weave_index.py`'s `ENTITY_INDEX.json` description
  field and `TOP_N` cut are all Hard-Rule-0-relevant spots that already carry the fix (either
  fully uncapped, or capped-and-marked with an explicit "N of M, all in the record" / "and N more"
  / ellipsis indicator). Re-verified rather than re-filed.
