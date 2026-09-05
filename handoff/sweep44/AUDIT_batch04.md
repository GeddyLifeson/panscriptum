# Audit batch 04 — run44

Modules read in full: `src/standards.py` (2,247 lines), `src/completeness.py` (753),
`src/onomast.py` (608), `src/withdraw_chapters.py` (479), `src/hosts.py` (393),
`src/catalogue_aurora.py` (324), `src/tempus.py` (274), `src/compress_store.py` (149).
5,227 lines total, read top to bottom, no sampling.

## Summary up front

These eight modules are unusually heavily self-audited already: nearly every function in
`standards.py`, `completeness.py`, `onomast.py`, `withdraw_chapters.py` and `hosts.py` carries a
docstring or inline comment narrating a specific historical defect (with an order id, a date, and
sometimes a reproduction), and the code beside it is the fix. I checked each of those narrated
fixes against the code that actually sits under the comment rather than taking the comment's word
for it, and in every case I could verify, the code matches the claimed fix — I did not find a
"fixed" comment sitting over code that still has the bug.

Net result: one live finding (`completeness.py`), reported below as a question rather than a
confirmed defect because its two current call sites happen to make it harmless today. I also ran
`standards.py`'s own "every declared floor is measured" self-check against its own source as a
cross-check (see Verification, below) rather than trusting its green reading secondhand, and it
came back clean: 28 declared `MIN_`/`MAX_` constants, 0 dead.

No caps, swallowed verdicts, inverted conditions, or falsy-zero slips were found in
`onomast.py`, `withdraw_chapters.py`, `hosts.py`, `catalogue_aurora.py`, `tempus.py`, or
`compress_store.py` beyond the one item below.

---

## completeness.py

### QUESTION — `catalogued_counts()` truncates category names to 40 characters as a dict key

`src/completeness.py:293`:

```python
c[str(e.get("category") or "?")[:40]] += 1
```

This is exactly the fault class Hard Rule 0 exists to name: a `[:N]` slice with no marker,
truncating a value used as a lookup key. The module's own `PERSONS` constant —

```python
PERSONS = "Persons (named individual characters, real or fictional)"   # completeness.py:58
```

— is 56 characters long. Truncated to 40 it becomes `"Persons (named individual characters, re"`,
so two different record entries whose `category` field is `PERSONS` and, say, a longer
Persons-adjacent category string that happens to share the same 40-character prefix would collapse
into one `Counter` bucket. In principle this is the identical shape to the source-name collision
this same codebase has already found and fixed twice elsewhere (`str(c["source"])[:18]` in
`standards.py`, noted at `standards.py:1401` as measured to actually collide on real roll names).

**Why I am not filing this as a confirmed defect:** I checked every place `by_category` is read
back in this file, and both do a prefix test rather than an exact-key lookup:

- `completeness.py:455-456` — `sum(v for k, v in rec0["by_category"].items() if k.startswith("Persons"))`
- `completeness.py:568` — `sum(v for k, v in rec["by_category"].items() if k.startswith("Persons"))`

Because both consumers sum every key that starts with `"Persons"` rather than looking up the exact
`PERSONS` string, the 40-character truncation does not currently corrupt the one figure
(`catalogued_persons`) this module derives from `by_category`. Any two categories that both start
with `"Persons"` and share a 40-character prefix would still be summed together correctly by
`startswith`, and any two *non*-Persons categories that collide under the truncation are never
read back by anything in this file — `by_category` is not written to `COMPLETENESS.json`, only
kept in the in-memory `have`/`byslug` maps this same process built.

**The two readings:**
1. *Deliberate/harmless*: the 40-char cut was chosen (or never revisited) because nothing in this
   module ever needed an exact `by_category` key, only the "starts with Persons" aggregate — so
   the truncation genuinely costs nothing today.
2. *A live landmine*: it is a silent truncation with no marker, sitting in a file whose whole
   subject is Hard Rule 0 violations elsewhere in the codebase (`MAX_PER_SOURCE`, the wiki-cast
   caps the module's own docstring exists to catch). It currently causes no wrong number only by
   the accident that both readers use `startswith`; a future caller of `catalogued_counts()` that
   wants an exact per-category count (e.g. to report "how many Places vs Persons" broken down more
   finely than the current binary) would silently get merged buckets for any two category strings
   agreeing on their first 40 characters, with nothing to say it happened.

Confidence: high that the truncation exists and is unmarked as described; medium on whether it is
worth a work order today, since I could not find a live consumer it currently corrupts, and it is
plausible the 40 was picked as "long enough for the one category summary this module actually
computes" rather than as a corpus-wide cap.

---

## standards.py

No confirmed defects found. This file's own extensive narration ("green by absence", "a check that
cannot fail looks exactly like a check that passed", multiple `UNMEASURED-vs-green` repairs) covers
almost every one of the fault classes I was asked to hunt, and in each case I traced the code under
the comment and it matches the claimed repair — for example:

- `resident_context()` (`:497-517`) and `context_verdict()` (`:431-447`) correctly return `None`
  rather than a false agreement/disagreement when the daemon cannot be asked, and `check()`'s
  caller at `:1855-1863` correctly treats `None` as a breach with an `UNMEASURED --` reading, not a
  silent pass.
- The fabrication standard (`:1126-1167`) reads `jobs.get("corpus read")` and `read.get("dropped")`
  correctly per its own fix narrative, and is appended unconditionally (not gated behind a truthy
  check that would drop it on a `None`).
- `job_stamp()` (`:403-412`) carries the previous timestamp forward correctly when the size holds,
  which is what makes `MAX_JOB_SILENCE_MIN` reachable at all (verified by reading the call site at
  `:1537-1539`, not just the function in isolation).
- The self-check at `:2108-2147` ("every declared floor is measured") does not merely claim to
  scan the whole file for `MIN_/MAX_` usage — it does, and I independently reran its regex logic
  against the live file (see Verification) and got the same "all measured" result it would report.

One thing I looked at hard and could not fault: `standards.py:1234`,
`mine = float(str(band)[1:]) + float(got.get("decimal", 0))`, which strips the first character off
a `"band"` string. This is safe only because bands in this codebase are always named `"M0"`
through `"M10"` (confirmed against `src/assay.py`'s `BAND_EDGES`/`LADDER`), so `[1:]` always drops
exactly the leading `"M"`. Not a defect, but worth flagging as a place where a format assumption
(no other module in this batch defines its own band-naming scheme) rides on an un-guarded slice;
if a caller ever put a two-letter prefix band string into `REFERENCE_ASSAYS.json` this would
silently parse it wrong rather than raising. Confidence low that this is worth a work order on its
own — reported for completeness since I traced it fully rather than assuming it was fine.

---

## onomast.py, withdraw_chapters.py, hosts.py, catalogue_aurora.py, tempus.py, compress_store.py

No confirmed defects found in any of these six modules. Each was read in full and cross-checked
against its own historical-fix commentary the same way as above; specific things I verified rather
than assumed:

- `onomast.py`: `name_worlds()`'s append-only merge (`:502-527`) correctly distinguishes "standing"
  from "retired" by cid membership in `resolved`, not by whether this run renamed it — I traced the
  `naming`/`by_key`/`taken` sets together rather than reading the comment alone, since this is
  exactly the kind of three-state logic that's easy to get subtly wrong even with a correct-sounding
  comment above it. The `[:4]`/`[:9]` print caps in `main()` are both loudly marked with an
  "... and N more" line and do not touch what is written to `ONOMASTICON.json` (`:596`), so they
  are not Hard Rule 0 violations.
- `withdraw_chapters.py`: traced the per-path (`raw_path`/`compressed_path`) vs per-entry (`stuck`)
  accounting through every branch of the withdrawal loop (`:239-297`) to confirm a partially-moved
  entry is amended rather than silently dropped or silently kept stale, in the several distinct
  orderings (raw moves + compressed gone, raw gone + compressed moves, raw moves + compressed
  collides, etc.) — all resolve correctly. The `moved[sub] += 1` / `extra += 1` counters incrementing
  outside the `if a.go:` guard are deliberate dry-run preview counts, not a bug (the "DRY RUN --
  pass --go to move" banner confirms nothing was actually moved in that mode).
- `hosts.py`: confirmed the `_PROBE_FAILED` sentinel and the `None`-vs-`[]`-vs-real-list three-way
  branch in `discover()`'s `work()` closure (`:193-268`) actually reaches all three named outcomes
  in the caller (`:277-308`) rather than any of them silently collapsing into another.
- `catalogue_aurora.py`: `slug()` is genuinely uncapped (`:91`); `record_path()`'s legacy-cap
  fallback (`:109-115`) only matches records that literally exist on disk under the old 60-char
  name, so it cannot accidentally borrow an unrelated record.
- `tempus.py`: worked through the band-edge arithmetic in `rung_description_length()` and
  `band_resolution()` by hand against `assay.py`'s actual `BAND_EDGES`/`LADDER` and confirmed the
  M10-inherits-M9-width edge case is handled as documented, and confirmed `is_present_at()`'s
  `event_mark >= observer_rung` matches its own docstring's stated semantics (lower rung = larger
  "now").
- `compress_store.py`: the temp-name-carries-pid-and-thread pattern and the `replace_retry`-then-raise
  path (`:52-89`) correctly cleans up the temp file before raising, and `load()`'s hash-verification
  (`:139-148`) checks against the actual re-hashed decompressed text, not a stored/cached value.

---

## Verification

Re-ran `standards.py`'s own "every declared floor is measured" self-check logic (copied verbatim,
not modified) against the live `src/standards.py` source, independently of the module's own
internal report:

```
declared: 28
dead: []
```

Confirms the file's own instrument-integrity check is telling the truth about itself at time of
audit — no declared `MIN_`/`MAX_` floor in this file is currently unreferenced.

Environment: `C:/Users/imarl/miniconda3/python.exe` was used for the one verification script; no
source file under `src/` was modified.
