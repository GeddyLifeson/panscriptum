# BATCH 02 audit — pipeline.py, wh40k.py, recover_folder_records.py, scale_theories.py

run26, full line-by-line read of all four files (1909 + 238 + 180 + 148 = 2475 lines).

---

## src/pipeline.py (1909 lines)

### MAJOR — `phase_synthesis` still caps the no-feat fallback roster to 14 entries
`src/pipeline.py:707`
```python
chunks = [with_feats[i:i + 14] for i in range(0, len(with_feats), 14)] or [rest[:14]]
```
When a source has at least one feat-bearing entry, `with_feats` is chunked across its *entire*
length — no cap, every feat-bearing entry eventually gets nominated. But when a source has
**zero** feat-bearing entries, the fallback is a single chunk: `rest[:14]`, where `rest` is
`rec["entries"]` sorted by description length descending. Only the top 14 entries by description
length are ever shown to the model for ceiling nomination; everything past rank 14 is never
considered, in any run, for as long as the source has no mined feats. That is precisely the
"rank then truncate" pattern Hard Rule 0 names as forbidden ("Ranking is still allowed... Ranking
then truncating is not"). The comment two lines up (698–706) argues this is deliberate and safe
("a lead paragraph cannot carry a ceiling feat"), and that may well be true in practice, but the
code still permanently excludes part of the roster from consideration, which is the exact shape
Hard Rule 0 prohibits regardless of how well-reasoned the truncation is. Concrete scenario: a
source with 200 entries and no feats mined yet (feats mining is itself an ongoing background
process per `_mined_feats`'s docstring) — entries ranked 15–200 by description length are never
offered to the model as a ceiling candidate this pass, even though a later feats-mining pass
could reveal one of them, at which point it would move to `with_feats` and get considered. Until
then, this is a silent, un-widened sample of 14 out of N.

### MAJOR — `update_handoff` bypasses the sanctioned atomic-write path
`src/pipeline.py:1323-1329`
```python
os.makedirs(os.path.dirname(HANDOFF), exist_ok=True)
tmp = HANDOFF + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    f.write(md)
os.replace(tmp, HANDOFF)
except Exception:
    log("  (handoff update failed: " + traceback.format_exc(limit=1).strip() + ")")
```
Every other writer in this file — `save_state`, `write_record`, `write_record_catalogue`,
`land_json` — routes its rename through `_landed()` → `silence.replace_retry`, specifically
because a bare `os.replace` can raise `PermissionError` on Windows when any reader (this
project's own dashboard/scanner tooling) has the target open, and `_landed`'s own docstring
explains at length why a denied rename must be retried and its verdict returned rather than
dropped. `update_handoff` does none of that: it calls raw `os.replace`, and if it raises, the
*entire* function body is wrapped in one outer `try/except Exception` (this snippet is the tail
of that block) that just logs one line and returns nothing. Nothing downstream checks a return
value from `update_handoff` (it has none), so a transiently-locked `handoff/RUN_STATUS.md` is
silently skipped for that unit with no retry — indistinguishable from success to every caller.
This is the one write path in the file that still has the failure mode `_landed` was built to
close, in the same module whose own header comment (lines 62–72) recounts HANDOFF.md's sibling
file being destroyed by exactly this kind of unguarded clobber.

### MINOR — dead `_MAGNITUDE` re-check in `valid_scale_note`
`src/pipeline.py:973-974` then `:987`
```python
if _MAGNITUDE.search(t):
    return t
...
if _REPUTATION.search(t) and not _MAGNITUDE.search(t):
    return ""                       # a title or a rumour, not a deed
```
By the time execution reaches line 987, `_MAGNITUDE.search(t)` has already been checked at line
973 and, since the function didn't return there, is guaranteed to be `False` on line 987 too (the
same immutable `t`). So `and not _MAGNITUDE.search(t)` is always `True` and the condition
collapses to `if _REPUTATION.search(t): return ""`. Not a behavioural bug — the code does what
the simplified form would do — but it is a "check that cannot fail" (lens item 7): it reads as
though a reputation phrase *combined with* a magnitude phrase should be let through, which never
happens because the magnitude branch already exited. Worth a comment or removal so a future
reader doesn't infer intent that the control flow forecloses.

### MINOR — `phase_cosmology`'s per-source classify try/except can hide a future regression the same way it once did
`src/pipeline.py:1416-1420`
```python
try:
    grounds[src] = G.classify_source(rec)
except Exception:
    silence.note("pipeline.py:phase_cosmology-ground")
    grounds[src] = {"type": G.UNGROUNDED}
```
The comment directly above (1402–1407) recounts that this exact pattern previously converted a
`TypeError`/`AttributeError` bug (passing a source *name* instead of the *record*) into 209
silent `UNGROUNDED` results, invisible because `UNGROUNDED` is itself "a real category in the
charter." The call-site bug is fixed, but the `except Exception` is still unconditional: any
future exception inside `classify_source` (a real crash, not just a bad argument) is still
converted into the same legitimate-looking `UNGROUNDED` value with no distinguishing marker.
Nothing here re-introduces the original bug, but the guard that would catch a *recurrence* of the
same failure class is exactly as blind as it was before.

### MINOR — stale numeric `silence.note` tags no longer match their lines
`src/pipeline.py:404, 539, 629, 646`
```
404:  silence.note("pipeline.py:191")
539:  silence.note("pipeline.py:301")
629:  silence.note("pipeline.py:261")
646:  silence.note("pipeline.py:277")
```
Every other `silence.note` call in this file (and the rest of the module, post-2026-08-24 per
`silence.write_json`'s own docstring about the sweep that found unatomic writers) uses a
descriptive tag (`"pipeline.py:vram"`, `"pipeline.py:write_record-merge"`, etc.) that stays
correct regardless of future line churn. These four are leftover line-number tags from an earlier
version of the file and now point at unrelated code (line 191 is inside `save_state`, not
`records()`; line 301 is inside `ask_pool_first`'s docstring, not `write_record`'s
`FileNotFoundError` handler). Cosmetic only — `note()` doesn't validate its argument — but it
degrades any tooling that greps these tags to locate a failure site, which is exactly the
purpose a tag exists for.

### Clean / verified sound
- **Two-writer contract in this file is otherwise well-formed.** `write_record` and
  `write_record_catalogue` both merge-before-write, refuse to write on a failed read (returning
  `False` rather than falling through to an overwrite), and route the final rename through
  `_landed` → `silence.replace_retry`. `land_json` does the same for phase artifacts. This is the
  strongest part of the file and matches its own extensive documentation of the two "run #24"
  incidents.
- **`clean_band` vs `ceiling_band` asymmetry is correct as documented.** `clean_band` uses
  `fullmatch` (fixing the historical `re.match` + `\b` decimal-laundering bug described at
  123–133); `ceiling_band` is deliberately lax and is only ever used to *lower* a clamp (verified
  at the one call site, line 1163–1167), never to accept a value for publication.
- **`entry_settled` / `batch_settled`** correctly implement the single predicate described in
  their docstrings; verified the resume gate and the write-completion gate in `phase_entrypass`
  both call the same function (no duplicate-logic drift).
- **The only subprocess spawn in the file** (`nvidia-smi` in `_vram_mb`, line 211) passes
  `creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)`. Clean.
- **`ask()`'s retry loop** correctly returns `None` (not a stale/partial value) after exhausting
  retries, and every caller of `ask`/`ask_pool_first` in this file treats `None` as "unit not
  done" rather than writing a partial result.
- Text-length truncations scattered through phase 1/2 (`[:300]`, `[:240]`, `[:600]`, `[:900]`,
  `[:500]`, `[:150]`, `[:420]`, `[:120]`) are per-field token-budget bounds applied uniformly to
  *every* entry shown/returned, not a truncation of *which* entries are considered — distinct
  from the Hard-Rule-0 violation above and not flagged as one.

---

## src/wh40k.py (238 lines)

### MAJOR — direct `open(...,'w')` + `json.dump` on a shared data file
`src/wh40k.py:230-231`
```python
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
```
`OUT = data/WH40K_ASSAYS.json` is a shared `data/` file per the same class silence.write_json's
own docstring calls out by name as a historically-clobbered category ("TWELVE call sites across
ten modules were writing shared `data/` and `state/` files with a bare `open(path, "w")` +
`json.dump`"). This write is non-atomic (no tmp file, no rename) and unguarded: a crash or a
concurrent reader mid-`json.dump` sees a truncated/partial file, and there is no retry-on-lock
behaviour for Windows' transient `PermissionError`. This is the exact `open(...,'w')` /
`json.dump` pattern the two-writer contract forbids for a "record or shared state file." Fix
would be `silence.write_json(OUT, out, indent=1, ensure_ascii=False)`.

### Clean / verified sound
- No subprocess spawns.
- `ROSTER` is a fixed, hand-authored dict of five entities (not a swept corpus) — no Hard Rule 0
  exposure; nothing here truncates an ingested list.
- `_BAD_CHARS` self-scan at the top matches `pipeline.py`'s identical guard, consistently applied.
- `compute()` and `main()`'s ranking (`A.LADDER.index(...) + decimal`, negated for descending
  sort) are internally consistent given `clean_band`-style band strings; no off-by-one found in
  the sort key construction itself (external `assay.py` semantics not in scope for this batch).

---

## src/recover_folder_records.py (180 lines)

### MAJOR — final `SWEEP_ROLL.json` write is unguarded, unlike the per-record write two lines above
`src/recover_folder_records.py:162-164`
```python
if not args.dry_run and written:
    # ATOMIC: `resync_roll.py`'s docstring names THIS script as a roll-clobber source.
    silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)
```
compare against the per-record gate immediately above it in the same loop, at lines 155-157:
```python
if not silence.write_json(path, record, indent=2, ensure_ascii=False):
    print(f"  WRITE DENIED {name}; roll left untouched", flush=True)
    continue
```
The per-record write is gated specifically because of the "run #25" incident documented in the
comment at 149-154: a record write that silently failed but still let the roll get marked
`catalogued` with a real `entry_count` left the roll "actively LYING about a record that is not
on disk," and because work selection is `entry_count == 0`, the source was then never revisited.
The fix applied there was: check the return value, skip the roll mutation on failure. The exact
same failure shape exists at the final combined roll write two lines later and is **not** gated:
`silence.write_json(ROLL, roll, ...)`'s return value is discarded. If this call returns `False`
(a persistently locked `SWEEP_ROLL.json` — plausible, since the same comment block notes the
dashboard and other tooling poll these files on their own clocks), every individual record file
was written successfully to disk, but the roll never gets updated to say so. The script still
prints `"Wrote N records, M entries"` — a success message — even though the state file the next
run's work-selection depends on (`empty = [... entry_count == 0 ...]`) was never touched, so the
next run will silently redo the same N sources. Less severe than the record-level bug this file
already fixed (no data loss, since records are individually gated and idempotent to re-write),
but it is the identical unguarded-write pattern in the same function, discovered and fixed for
its sibling two lines above but not for itself, and it does produce a report ("Wrote N records")
that overstates what actually landed on disk when the roll write fails.

### QUESTION — record writes bypass the pipeline's own catalogue writer, self-flagged
`src/recover_folder_records.py:143-157`
The code already documents this itself (comment at 145-148): records here are written via
`silence.write_json` directly rather than through `pipeline.write_record_catalogue`, which is the
sanctioned writer for cast-growing/catalogue-side record writes per the two-writer contract. The
comment says this is intentional — routing through the catalogue writer "changes its merge
semantics" — and flags it as tracked in `NEXT_STEPS`. Confirmed this is at minimum atomic
(`silence.write_json` does tmp+PID+thread-qualified name, then `replace_retry`), so it does not
have the non-atomic-write hazard the MAJOR findings above describe. Flagging only because the
task's lens explicitly calls out any record write that isn't through the two sanctioned
functions — this one is a known, documented exception rather than an oversight, and the
"NEXT_STEPS" pointer wasn't independently verified in this batch (out of scope files).

### Clean / verified sound
- `entries` accumulation loop (`for register_source, _declared_count in mapped: ... for item in
  by_source.get(register_source, []): entries.append(...)`) has no cap — every item for every
  mapped register source is transcribed, satisfying Hard Rule 0.
- `EXCLUDED_REGISTER_SOURCES = {"ME"}` is a documented data-quality exclusion (seven unrelated
  roll sources were being fed the same 7 mismatched entries), not a truncation of legitimate
  data — correctly distinct from a Hard Rule 0 violation.
- `slug()`'s `[:60]` bound is a filesystem-filename-length bound, not a data cap.
- `roll_by_name[name]` direct-index lookup (no `.get`) is safe: `name` is always drawn from
  `empty`, which is itself derived from the same `roll` list `roll_by_name` was built from, so
  the key is guaranteed present.
- No subprocess spawns.

---

## src/scale_theories.py (148 lines)

Pure physics/math module — no file I/O, no writers, no subprocess, no data ingestion, so most of
the lens (two-writer contract, caps, concurrency) doesn't apply. Read for correctness only.

### MINOR — module-level physical constants are declared and never used
`src/scale_theories.py:23-27`
```python
C_LIGHT = 2.99792458e8
G_NEWTON = 6.67430e-11
HBAR = 1.054571817e-34
NUCLEAR_DENSITY = 2.3e17
PLANCK_LENGTH = 1.616255e-35
```
None of `G_NEWTON`, `HBAR`, or `PLANCK_LENGTH` are referenced anywhere in this file. `C_LIGHT`
and `NUCLEAR_DENSITY` also aren't referenced in code — the T1 theory's `"physics"` string
hardcodes `"nuclear saturation (2.3e17 kg/m^3)"` as a literal rather than formatting in
`NUCLEAR_DENSITY`, and the T2 theory's `"physics"` string hardcodes `"m*c^2 = 6.3e18 J"` as a
literal rather than computing it from `C_LIGHT`. Not a functional bug (the hand-checked literals
are numerically correct: 70 kg × c² ≈ 6.3×10¹⁸ J, ≈1506 megatons TNT, matches "fifteen hundred
megatons"), but the constants exist purely as unused documentation and the literals they describe
can drift out of sync with them silently — if `C_LIGHT` were ever corrected, the prose numbers
derived from it by hand would not move.

### Clean / verified sound
- `bulk_export_beta`, `growth_strike`, `penetration_pressure` all guard their divisions
  (`max(growth_time_s, 1e-6)`, `max(contact_area_m2, 1e-30)`, the `resident_mass_kg <= 0` check)
  against zero/negative inputs without silently returning a wrong-but-plausible number — they
  return a defined floor value or raise nothing unexpected.
- `surviving_theory()`'s `startswith("Nothing attested")` filter correctly selects exactly
  `T3_BULK_EXPORT` against the fixed `THEORIES` dict — hand-verified against all four entries'
  `falsified_by` strings.
- `THEORIES` is a fixed, small, hand-authored dict (4 entries) — no Hard Rule 0 exposure.
