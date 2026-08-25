# Batch 02 audit — run #25

Files read end to end, every line, no sampling:
- `src/pipeline.py` (1909 lines)
- `src/burgs.py` (235 lines)
- `src/halo.py` (178 lines)
- `src/repass_bands.py` (112 lines)

Plus, per the batch instructions ("audit every CALLER of write_record / write_record_catalogue"),
I grepped every caller of both functions across `src/` and read the call sites of every one that
does NOT visibly gate on the return value already (`catalogue_aurora.py`, `catalogue_codex.py`).
That surfaced this run's most important finding, reported below even though the two files
themselves belong to other batches.

---

## NEW FINDINGS

### 1. `catalogue_aurora.py:143-146` and `catalogue_codex.py:194-197` — callers of `write_record_catalogue` ignore its return value and report success anyway

**VERIFIED** (read the call sites directly, and independently proved `write_record_catalogue`
returns `False` on a torn/corrupt disk read — see reproduction below).

`catalogue_aurora.py`:
```python
if not args.dry_run:
    import pipeline as _P
    _P.write_record_catalogue(
        os.path.join(RECORDS, slug(source_name) + ".json"), record)
    r["entry_count"] = len(entries)
    r["status"] = "catalogued"
```

`catalogue_codex.py`:
```python
if not args.dry_run:
    import pipeline as _P
    _P.write_record_catalogue(
        os.path.join(RECORDS, slug(r["name"]) + ".json"), rec)
    r["entry_count"] = len(rec["entries"])
    r["status"] = "catalogued"
```

`pipeline.write_record_catalogue` (`pipeline.py:411-463`) is documented and coded to **return
`False` and refuse to write** whenever the disk copy cannot be read for merge — exactly the
scenario run #24 hardened it against (a concurrent writer mid-write). Both call sites here call
it and then, unconditionally and on the very next line, set `entry_count` and
`status = "catalogued"` in the in-memory roll row regardless of what happened. Both files then
write that roll row to `data/SWEEP_ROLL.json` a few lines later via `silence.write_json`.

Two other callers of the same function in the tree do this correctly and were used as the
contrast: `catalogue_web.py:344` (`if not _P.write_record_catalogue(...): ...` skip/report) and
`ingest_doc.py:246` (identical gate, with a comment explicitly calling out "ADVANCE ON THE WRITE,
NOT ON THE INTENT"). `catalogue_aurora.py` and `catalogue_codex.py` are the two callers that never
learned that lesson.

**Consequence:** a refused write leaves the record file untouched (still the old/corrupt content,
possibly zero entries), but the roll row is marked `catalogued` with the intended `entry_count`.
Both scripts gate their own re-run skip on `entry_count > 0` (`catalogue_aurora.py:117`,
`catalogue_codex.py:128`), so a source whose write was silently refused looks done forever and
is never retried — permanent, silent loss of exactly the cast the write was supposed to add.

**Reproduction** (proves `write_record_catalogue` really does return `False` on a corrupt disk
copy, which is the trigger condition both callers ignore):
```
$ python -c "..."
[..] write_record_catalogue: test.json could not be read for merge; REFUSING to write an
     unmerged cast over it -- this unit stays open
write_record_catalogue returned: False
```

---

### 2. `repass_bands.py:78-80` — `write_record`'s return value is ignored; the script reports "APPLIED" even when the write was refused

**VERIFIED** by direct execution.

```python
if changed:
    PL.write_record(path, rec)
    touched.append(src)
```
and later:
```python
if args.apply:
    print(f"\nAPPLIED. {len(touched)} record files rewritten.")
```

`pipeline.write_record` (`pipeline.py:503-564`) — the function run #24 specifically hardened so
it refuses to overwrite a record it cannot read for merge and returns `False` instead — is called
here and its return value is discarded entirely. `src` is unconditionally appended to `touched`,
and the final banner reports every touched source as "rewritten" whether or not the write landed.
Since `repass_bands.py` demotes bands to `unassayed` in memory and only that in-memory change is
ever lost on a refused write, a demotion that should have stuck (because the evidence gate
correctly rejected it) can silently fail to persist while the tool claims success.

`repass_bands.py` is exactly the kind of one-shot maintenance script that gets run by hand while
`pipeline.py` is live (this batch's brief notes it's "a live long-running process right now"), so
the trigger condition — reading a record file the pipeline is mid-write on — is not hypothetical.

**Reproduction** (same mechanism `write_record` uses internally, isolated to prove the return
value really is `False` and the write really is skipped):
```
$ python -c "..."
[..] write_record: test.json could not be read for merge; REFUSING to write the in-memory copy
     over it -- this unit stays open
write_record returned: False
file on disk still: {not valid json
```
`repass_bands.py` never sees this line and never checks the return, so its own console report
would still say "APPLIED. 1 record files rewritten." for this exact case.

This is the same bug class as run #24's m119/m120 fixes and the NEXT_STEPS §3 item "every
one-shot caller in batch 06 ignores the return (`navtree.py:263`, `catalogue_codex.py:203`,
`scope.py:119`)" — but that item is about `silence.write_json`, a different function. This is the
first confirmed case of a caller ignoring `write_record`/`write_record_catalogue`'s own hardened
return value specifically, which is the exact audit the batch brief asked for.

---

### 3. `pipeline.py` — four `silence.note()` tags carry stale line numbers, pointing the failure ledger at the wrong code

**VERIFIED** by comparing each tag's claimed line to its actual location.

```
line 404   silence.note("pipeline.py:191")   (records(), actually at ~397-408)
line 539   silence.note("pipeline.py:301")   (write_record's FileNotFoundError arm, actually ~538)
line 629   silence.note("pipeline.py:261")   (_mined_feats, actually ~618-630)
line 646   silence.note("pipeline.py:277")   (_mined_feats' inner loop, actually ~636-651)
```

`silence.note(site)`'s own docstring frames `site` as "the site" being recorded — the failure
ledger (`state/failures.json` via `health.record`) is read by `standards.py`, `dashboard.py` and
maintenance runs specifically to go find the code behind a recorded failure. All four of these
tags are now 130-370 lines away from where they actually sit, because the file has grown
substantially since the tags were written (visible from the module's own comments, e.g. the m6/m13
fixes documented inline). Anyone following one of these four tags into the file lands on unrelated
code (e.g. `"pipeline.py:301"` now sits inside `phase_synthesis`'s docstring, not near
`write_record`).

This is the same defect shape NEXT_STEPS §3 already calls out generically ("stale `silence.note()`
line tags across `foreman.py`, `feats.py`, `scout.py`") — this batch confirms `pipeline.py` itself
also has the problem, which that item did not name.

---

### 4. `burgs.py:76` — `GENERATORS` dict is dead code; the field it claims to populate is never produced by it

**VERIFIED** by grep (`GENERATORS` appears exactly once in the file, on its own definition line).

```python
GENERATORS = {"city": "Watabou city generator", "village": "Watabou village generator"}
```
with the comment above it: *"Which of Watabou's two generators a settlement belongs in. Recorded
for reference only."* But `classify()` (line 121-125) returns `gen` straight from `CLASSES`'
fourth tuple field — the bare string `"city"` or `"village"` — and that raw string is what
`burgs_for()` stores under the `"generator"` key (line 157) and what `main()` prints as the
`generator` column. `GENERATORS` is never looked up anywhere. The comment describes a translation
step ("recorded for reference") that the dict was presumably meant to perform and does not: the
descriptive strings `"Watabou city generator"` / `"Watabou village generator"` are never actually
written to any output, JSON or console. Low severity — no other module reads the `generator`
field (checked via grep across `src/*.py`) — but it is a real comment/code mismatch under this
audit's lens 6, and the dead dict should either be wired in or removed.

---

## KNOWN FINDINGS (confirmed still present, kept brief per instructions)

- **`pipeline.py:1327`** `os.replace(tmp, HANDOFF)` — bare, non-atomic replace of
  `handoff/RUN_STATUS.md`, unlike every other writer in this file (which all route through
  `_landed`/`silence.replace_retry`). Matches NEXT_STEPS §3's "Non-atomic shared writes still
  open" list (there cited as `pipeline.py:1293`; the file has grown since, current line is 1327).
  Confirmed present, unchanged in behavior.
- **`pipeline.py:397-408`** `records()` silently drops any record file that fails to parse
  (`except Exception: ... continue`), with no distinction from "genuinely no entries". Matches
  NEXT_STEPS §3 verbatim.
- **`burgs.py:227`** bare `open(p, "w")` + `json.dump` on `data/BURGS_SAMPLE.json`, not routed
  through `silence.write_json`/`replace_retry`. Matches NEXT_STEPS §3's non-atomic-writers list.
- **`burgs.py:230`** — `print(f"\nwrote {p} (sample of 50 worlds; the rest regenerate on
  demand)")` — the message claims a 50-world sample; the code above it (`per_world[w["designation"]]
  = bs` inside `for w in worlds:`, no slice) writes every world in `worlds`. Matches NEXT_STEPS §3
  exactly ("message says 'sample of 50 worlds', code writes all").
- **`halo.py:146-174`** — `main()` prints `rec["assay"]["moth_number"]` (line 158, 163; this
  string embeds the 𝔄 glyph per `assay.py`'s own docstring) to stdout before the atomic
  `silence.write_json(OUT, ...)` call at line 171, with no `sys.stdout.reconfigure` guard —
  the same UnicodeEncodeError-before-write shape `handbuilt.py` already fixed elsewhere. Matches
  NEXT_STEPS §3 exactly, including the cited line range.
- **`repass_bands.py:91`** — `print(f"  demoted to unassayed: {len(demoted_sources):,} of 211")`
  — the `211` is a hardcoded literal, not derived from `len(recs)` or the actual roll size.
  Matches NEXT_STEPS §3 exactly.

---

## Checked and found NOT a bug (worth recording so it isn't re-flagged)

- `pipeline.py` phase-2/phase-1 callers of `write_record` (`phase_synthesis:753`,
  `phase_entrypass:1177`) **do** correctly gate on the return value (`if not write_record(...)`
  / `landed = write_record(...); if landed and all(...)`) and mark the unit as failed/left-open
  rather than done when the write is refused — this is the correct pattern that
  `catalogue_aurora.py`/`catalogue_codex.py`/`repass_bands.py` above fail to follow.
- `burg_count()`'s rank-size derivation (`n = (P_1/P_min)^(1/q)`) is algebraically consistent
  with the docstring's simplified `n = P_1/P_min` given `ZIPF_Q = 1.0`; not a bug as currently
  configured.
- `halo.py`'s `A.assay(...)` call matches `assay.py`'s real signature
  (`assay(anchor, scores, attestation=..., epoch=..., worksheet=..., hand_readings=None,
  weights=None)`) and supplies a non-empty `worksheet`, so it correctly takes the full-decimal
  path rather than the band-only fallback.
- `repass_bands.py`'s `kept_entries[:14]` / `demoted_entries[:8]` slices (lines 95, 101) are
  console-report samples only — every entry is still processed and (when `--apply`) demoted;
  nothing is dropped from the actual work. Not a Hard Rule 0 violation.

---

## Modules read end to end and found CLEAN this run

None of this batch's four modules is fully clean — each carries at least a KNOWN or NEW finding
above. No additional modules were read end-to-end beyond the four assigned (the caller
cross-check of `catalogue_aurora.py`/`catalogue_codex.py` was targeted at specific call sites,
not a full read of those files, so they are not claimed as read or clean here).
