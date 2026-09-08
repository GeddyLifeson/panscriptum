# Sweep 47, Batch 07 — Audit

Scope (brief `brief_batch07.md`): 8 modules, 5,623 lines. All eight were read in full, top to
bottom, in this session:

- `src/workorders.py` (2,020 lines)
- `src/allsweep.py` (985 lines) — read as it stands NOW; another lane edited it earlier today.
- `src/weave.py` (698 lines)
- `src/weave_index.py` (530 lines)
- `src/cleanup.py` (445 lines)
- `src/render.py` (402 lines)
- `src/roll.py` (289 lines)
- `src/propagation.py` (254 lines)

No source file was edited. This is an audit only.

## Already-open orders: verified status against the CURRENT source

Per the brief, none of the orders already open against these eight modules were re-filed. Two
were re-verified this shift and found to be **already fixed**; the rest were spot-checked and
still reproduce as described.

### `2d6c9343cd32` [RUN] BATTERY_GRADED (render.py) — ALREADY FIXED

The order's evidence is `import render: NameError: name 'add_argument' is not defined` plus a
matching `pyflakes ...:294:8: undefined name 'add_argument'`. The current `src/render.py:292-298`
reads:

```python
ap = argparse.ArgumentParser()
ap.add_argument("--write", action="store_true")
ap.add_argument("--probe", action="store_true", ...)
```

Both calls are correctly prefixed with `ap.`. Verified live, not just by inspection:

```
PYTHONIOENCODING=utf-8 python src/render.py --help   -> usage printed, rc=0
python -m pyflakes src/render.py                     -> no output (clean)
```

The NameError this order names does not reproduce. Recommend closing `2d6c9343cd32`.

### `18f7673b77ce` [OWNER] CLEANUP_CEILING_PREFIX_AMBIGUITY — ALREADY FIXED

The order's text: "The prefix match picks the shortest candidate with no ambiguity check when
two entities share a name stem." That is the exact defect `clean_ceiling()`'s own inline comment
(src/cleanup.py:238-249) describes as **already repaired under a different order, `ed6e66c0c12d`**
(confirmed closed in `state/workorders.json`): the old guard was `len(low_pref) >= 1` followed by
`min(low_pref, key=len)`, picking the shortest match on no evidence. The current code:

```python
if len(low_pref) == 1:
    return low_pref[0], "prefix"
if low_pref:
    return ce, "prefix-ambiguous"     # several matched -- reported, not guessed
```

`main()` reports `prefix-ambiguous` rows separately with every candidate listed
(`ceil_ambig`, cleanup.py:296-300, 402-408) rather than silently picking one. The finding named by
`18f7673b77ce` and the fix landed under `ed6e66c0c12d` are the same defect. Recommend closing
`18f7673b77ce` as a duplicate of the already-resolved `ed6e66c0c12d`.

### `fe99e57e1993` [LOCAL] UNMARKED_NAME_CUTS_SWEEP44 — PARTIALLY fixed for cleanup.py

The order's cleanup.py citation is `cleanup.py:231,233,261 ce[:70], ce[:52], d[:46]/cd[:46] --
beneath a comment claiming these per-name cuts were fixed alongside the roster caps.`

Verified against current source:

- **`ce[:70]` and `ce[:52]` are gone.** `ceil_fixed`/`ceil_unres`/`ceil_ambig` now carry the whole
  `ce` string and print it whole (cleanup.py:395-408, under the "WHOLE CEILINGS IN ALL THREE
  ROSTERS" comment at line 288). This part of the order is fixed.
- **`d[:46]/cd[:46]` is still present**, now at `src/cleanup.py:333`:
  ```python
  desc_fixed.append((src, nm, d[:46], cd[:46]))
  ```
  and printed with no truncation marker at cleanup.py:410-412 (`print(f"     {str(n):<24}{b!r}")`
  / `print(f"     {'':<24}-> {a!r}")`). A long description's before/after text is silently cut at
  46 characters in this diagnostic with no "…" or "+N chars" — Hard Rule 0's exact shape, on the
  one row (`3. descriptions with markup stripped`) whose whole job is showing what markup removal
  did. This is not re-filed (it's the order already open); flagging that the line numbers in the
  order (`231,233,261`) have drifted — the surviving cut is now at line 333 — for whoever works it.

### Other open orders — spot-checked, still valid

- `8f50f37255b5` `_STOPNAMES` dropping real entities (weave_index.py:49-54, 368-370) — still
  present, unchanged.
- `5f1dc97d5216` `_records_sig` top-level `OSError` reading an unreadable directory as an empty
  corpus (weave_index.py:270-276) — still present, comment (`silence-exempt: an unreadable
  records dir reads as an empty corpus, as it always did`) unchanged.
- `707fefc17465` render.py unreachable — still true; grepped `src/` for `import render` /
  `from render` and found none; the only other mention is a comment in `build_terminal.py:87`.
- `c9146abf92df` roll.py/foreman.py two-writer hazard — still present. See new finding below:
  the order's own `where` citation for roll.py has drifted.
- `e866d1520c16` STALE_CITATION_TIERS — the order records having re-verified its own citations
  against the live tree on 2026-09-07 (today) and updated the weave.py citation to `weave.py:306`.
  Checked that line: 306 is inside a *comment* in `surprisal_pair_weights` that itself quotes the
  phrase "WHOLE list -- Hard Rule 0," while describing history; the actual `shared_sample` field
  carrying that marker live is at `weave.py:671`. So even today's re-verification landed on the
  wrong one of two textual matches for the same phrase. Not re-filed (this is the same order,
  continuing to exhibit the exact defect it is about), but noted here as fresh evidence for
  whoever next works it: grep found two occurrences of the phrase and the wrong one was kept.
- `5c962f306e58`, `5a0c4196142f`, `a724ec57e0d5`, `bfafac3e1c5e`, `e637c67ab438` — all reference
  conditions still visible in the current source (verify_math's bare-identifier pin referenced in
  allsweep.py's own Verifier docstring; `weave.null_threshold` still dead/uncalled; etc.). Not
  independently re-verified line-by-line beyond confirming the named functions/behaviour still
  exist as described.

## New finding filed this batch

**`ROLL_ORDER_CITATION_DRIFTED_C9146`** (LOCAL / MINOR) — the currently open order `c9146abf92df`
(ROLL_LOST_UPDATE_REMAINING_WRITERS) cites its second unsafe writer as `src/roll.py:127
(exclude)`. Line 127 of the current `src/roll.py` is inside `mutate()` (`digest =
silence.digest_of(path)`), unrelated to `exclude()`. The actual ungated write this order is about
— `return silence.write_json(ROLL, rows, indent=2, ensure_ascii=False)` inside `exclude()` — is
now at line 267. The underlying two-writer finding is still correct and is not re-filed; only the
citation is wrong, and following it lands a reader inside the wrong function.

## Coverage caveats

All 5,623 lines across the eight named modules were read. No section of any of the eight was
skipped. Modules these eight import or reference (`silence.py`, `escalation.py`, `pipeline.py`,
`ledger_guard.py`, `local_agent.py`, `binding_health.py`, `publish.py`, `estate.py`,
`cosmology_graph.py`, `overnight.py`, `retry_synthesis.py`, `feats.py`, `cachekey.py`, `roll.py`
callers `foreman.py`/`catalogue_web.py`/`catalogue_aurora.py`/`catalogue_codex.py`/
`recover_folder_records.py`/`resync_roll.py`) were **not** read in this batch except where a
one- or two-line grep was needed to confirm a specific citation or call site named above; they
are out of this batch's scope and were not audited for their own faults.
