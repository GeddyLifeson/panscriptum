# Audit batch 05 — read.py, generate.py, address.py, tempus.py, cleanup.py, resync_roll.py

Full line-by-line read of all six files (1135 + 421 + 290 + 254 + 208 + 81 = 2,389 lines).
No bare `except:` anywhere in this batch (grep-verified).

---

## src/read.py (1135 lines) — CLEAN, with one trivial doc-staleness note

This module is unusually well self-documented: nearly every non-obvious line carries a comment
that names a specific past incident, the measured evidence, and the fix. Read all of it,
including the transport ladder, the adaptive gate, the chunk cache, the entity-completeness
guard, and the priority/queue functions.

### SPECIAL FOCUS answer (read.py named as the standard-flagged "not running" job)

Traced the whole transport path an outside observer would see stall:

- `ensure_transport()` (read.py:231-261) resolves the transport exactly once, behind
  `_TRANSPORT_LOCK`, before any worker races on it — the lazy-race bug this replaced is
  described and fixed in its own docstring.
- `_gate()` / `_card_gate()` (read.py:291-325) bind concurrency to the real GPU slot count
  (`GATE_LOCAL_N`, from `PANSCRIPTUM_GPU_SLOTS`/`OLLAMA_NUM_PARALLEL`/default 2) **regardless of
  what `tuning.regime()` reports**, specifically because a mislabelled "cloud" regime was
  measured (2026-08-24, comment at read.py:476-496) admitting 16 workers onto a 2-slot card and
  discarding 94.6% of chunks as timeouts. That specific wedge is fixed in place.
- `read_entity()` (read.py:753-759) never writes the per-entity cache file if any chunk came
  back `unanswered` — so a starved pool cannot silently mark an entity "done" with fewer feats
  than it has. This was the actual mechanism behind the historical "looks fine, 71% never read"
  incident (comment at read.py:742-752) and it is closed: an entity with unanswered chunks stays
  perpetually re-offered to the queue on the next pass instead of being filed complete.
- `run()`'s progress line (read.py:1026-1030) explicitly prints
  `chunks_read/CHUNK_BUDGET (N to GPU, M UNANSWERED, not cached)` plus benched-bucket names, so a
  run that is actually being refused by every transport is visibly distinguishable from one that
  is progressing — it does NOT look identical to a healthy run from the log alone.
- Net: **if the pool is broadly declining and the local GPU is benched (`_GPU_DOWN_UNTIL`),
  entities-attempted (`n`) keeps incrementing while `feats`/`chunks` stay flat** — that is the
  shape that would look "stalled" to a glance at process liveness alone (still running, no new
  output files), but the printed progress line itself already reports the unanswered count and
  the benched buckets, so a diagnosis from the log is not blind. This is documented, deliberate
  behavior (deferred-not-lost), not a newly-found defect.

### Findings

- **read.py:213-216 — LOW — stale illustrative number in a comment, not a functional bug — VERIFIED.**
  ```python
  # Attempts through the pool before a chunk is handed to the local GPU. Each attempt claims a
  # different bucket, so three is three providers, not one provider three times.
  CASCADE_TRIES = 5
  ```
  The comment's example ("three is three providers") doesn't match the current constant (5).
  The underlying claim (each attempt = a different bucket) is still true and unaffected; only
  the illustrative number is stale, most likely left over from before `CASCADE_TRIES` was raised
  from 3 to 5. Cosmetic only.

- **read.py:666-667, 971-972, 1107-1128 — INFO, not a Hard-Rule-0 violation — VERIFIED.**
  `cap_chunks` (`--chunks`) and `limit` (`--limit`) both default to `None`/uncapped, are only
  ever set by an explicit CLI flag the operator must type, chunks are fully ranked (density,
  own-page-first) before any optional truncation, and the help text says
  `"omit to read every chunk of every page"`. This is the diagnostic/testing-knob shape Hard
  Rule 0 explicitly allows, not a silent default cap. `out["feats"][:12]` at read.py:1120 is a
  console preview for the manual `--one` debug command, printed *after* the full record was
  already written to disk uncapped (read.py:755-759) — it never touches stored data.

No swallowed-failure, two-writer-contract, or concurrency-race findings in this file: every
shared-file write (`_chunk_put`, the per-entity cache, `_save_qcache`) uses a per-pid/thread
temp name plus `silence.replace_retry`, matching the two-writer contract for shared state files.

---

## src/generate.py (421 lines) — CLEAN

- Uses `silence.write_json` for `catalog.json`/`failures.json` (the shared, multi-hour-run
  files) — generate.py:53-58, with an explicit comment naming why (`estate.py`/`catalog.py`
  read them concurrently).
- Hard Rule 0 is actively enforced rather than merely respected: a chapter written in
  `WRITE_CHUNK`-sized blocks (generate.py:37, 271-300) verifies every entry name is traceable in
  the returned text (`_covered`), retries once, and **raises loudly** (fails the whole job,
  leaving it pending for the next run) rather than silently shipping a book missing entries.
  Same pattern for feats blocks, with an additional `_deed_shortfall` probe
  (generate.py:179-268) that catches a block which kept every entity heading but dropped most of
  the underlying deeds — the exact shape a truncated prompt produces.
  `context_budget.assert_fits` (called from `call_ollama`, generate.py:132-133) refuses to send
  an over-window prompt in the first place, which is the primary defense; the deed-trace floor
  is explicitly documented as a backstop for a truncation that arrives some other way.
- Failures/catalog files are single-writer (this script runs single-threaded, no
  ThreadPoolExecutor) so the raw-markdown `open(path, "w")` at generate.py:383-384 is not a
  shared-file violation — each job writes to its own dedicated `safe_filename(address)` path.

No caps on any ordered listing, no bare/broad exception swallowing beyond the documented
`silence.note` + re-raise-safe pattern.

---

## src/address.py (290 lines) — CLEAN

Pure functions only (spine-code lookup, slugify, tier/promotion ladder, hashing) — no file
writes beyond a cached read of `data/CHARTER_SPINE_CODES.json`, no concurrency, no caps on any
listing. The module's own comments document two already-fixed correctness bugs (substring vs.
word-boundary matching that mis-shelved "Sword Coast Adventurer's Guide" under DC Comics; the
`promote()` ratchet being promotion-only, deliberately never demoting on a dip, with the
reasoning given inline). Nothing further to report.

---

## src/tempus.py (254 lines) — CLEAN

Pure math/lore module (no file I/O, no shared state, no caps, no concurrency). Every function is
a closed-form derivation with its reasoning in the docstring. Nothing to report.

---

## src/cleanup.py (208 lines) — CLEAN

- Uses `PL.write_record(path, rec)` (cleanup.py:180) — the correct pipeline-side writer per the
  two-writer contract.
- The `nav[:5]`, `ceil_fixed[:6]`, `ceil_unres[:4]`, `desc_fixed[:5]`, `thin[:5]` slices
  (cleanup.py:186-201) are console-report previews only — the full lists are computed and
  (under `--apply`) applied in full beforehand; only the printed sample is capped. Not a
  Hard-Rule-0 violation (diagnostic preview, not a truncation of what gets acted on).
- Minor: cleanup.py:77-80's guard loop iterates
  `(("_NAV", _NAV), ("_EMPTY_MECHANIC", _EMPTY_MECHANIC), ("_SETTING_META", None))` — `_SETTING_META`
  is not defined anywhere else in this file and the tuple entry is inert (guarded by
  `if _p is not None`). Harmless dead reference, likely left over from a regex that was removed
  elsewhere; not worth more than a note.

---

## src/resync_roll.py (81 lines) — ONE FINDING (concurrency race)

- **resync_roll.py:33-68 — MEDIUM — unguarded read-modify-write on the shared, multi-writer
  `data/SWEEP_ROLL.json` — VERIFIED (mechanism traced against `silence.write_json`/`replace_retry`).**

  The script's own docstring explains the hazard it exists to *repair*: four different
  cataloguer scripts (`catalogue_web.py`, `catalogue_aurora.py`, `catalogue_codex.py`,
  `recover_folder_records.py`) each rewrite the whole roll after every source, and "two of them
  running concurrently will have one clobber the other's counters with a stale copy read minutes
  earlier" — with a real incident cited (Aurora wrote 425/681 entries for two sources, then a
  concurrent wiki-cataloguer's later save reset both back to 0).

  `resync_roll.py` itself has exactly the same shape of exposure and nothing in it or in
  `silence.write_json`/`replace_retry` (src/silence.py:223-287) closes it:

  ```python
  with open(ROLL, encoding="utf-8") as f:      # read.py:33 — one snapshot taken
      roll = json.load(f)
  ...
  for fn in os.listdir(RECORDS): ...           # potentially many files scanned/parsed
  ...
  if changed and not dry:
      silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)   # line 68 — writes the
                                                                       # in-memory snapshot back
  ```

  `silence.write_json` makes the *write itself* atomic (per-pid/thread temp file + `os.replace`
  with retry) — it prevents a reader from ever seeing a half-written file, and prevents two
  writers' temp files from colliding. It does **not** re-read the file immediately before
  writing, and does not merge against whatever is on disk at that moment. So if any of the four
  cataloguer scripts named in this file's own docstring writes `SWEEP_ROLL.json` at any point
  between resync_roll.py's line-33 read and its line-68 write (a window that includes a full
  `os.listdir`+parse of every file in `data/records`, potentially thousands of files), that
  writer's update is silently overwritten by resync_roll.py's write, which is built from the
  now-stale in-memory snapshot. This is the exact clobber shape the docstring says already
  happened once — resync_roll.py just adds itself as a fifth possible clobbering writer, despite
  existing specifically to fix the results of that class of bug.

  The docstring's claim "It is safe to run at any time" is true for *not corrupting the file
  structurally* (thanks to the atomic write), but not for *never losing a concurrent writer's
  update* — those are different guarantees, and the second one is what an operator would
  reasonably read "safe to run at any time" as promising, including running it during a live
  cataloguing session.

No other findings in this file: `by_source` indexing, `norm()`, and the change-detection loop
are all correct and uncapped (`os.listdir` and the roll iteration are both full scans, no
truncation).

---

## Summary table

| File | Verdict |
|---|---|
| read.py | Clean; 1 cosmetic stale-comment number; special-focus stall mechanism traced and found already hardened |
| generate.py | Clean |
| address.py | Clean |
| tempus.py | Clean |
| cleanup.py | Clean; 1 harmless dead tuple entry |
| resync_roll.py | 1 real finding: read-modify-write race on shared multi-writer SWEEP_ROLL.json |
