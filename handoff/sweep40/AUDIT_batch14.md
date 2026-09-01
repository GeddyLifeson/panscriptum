# Sweep40 batch14 audit

Modules read in full: `src/assay.py` (1374 lines), `src/overwatch.py` (975 lines),
`src/wiki_source.py` (689 lines), `src/weave.py` (546 lines), `src/canon_backup.py` (418 lines),
`src/snapshot.py` (339 lines), `src/catalogue_models.py` (301 lines), `src/roll.py` (270 lines).

`assay.py` was flagged as possibly transiently corrupted by a concurrent mutation run. It was
read twice; both reads were identical and internally coherent (import-time `_check_constants()`
guard, `_BAD_CHARS` guard, full arithmetic chain all consistent). No anomaly attributable to the
mutation run was observed, so nothing about its content is reported as a finding.

Overall verdict: this is an extremely well-hardened batch. Every write in every module goes
through `silence.write_json`/`silence.replace_retry` and its verdict is checked; every truncation
this sweep looked for is already ruled out and explained in comments (Hard Rule 0 compliance
looks genuine throughout `wiki_source.py`, `weave.py`, `assay.py`, `overwatch.py`); `roll.py`,
`canon_backup.py` and `snapshot.py` implement careful compare-and-swap / containment-check /
verify-by-readback patterns with no gaps found. The two findings below are both stale
`file.py:NNN` cross-references in comments -- the class of defect Hard Rule 0's audit brief
specifically asks to be verified line-by-line.

---

## Finding 1 (MINOR) -- stale cross-reference in overwatch.py, two sites, both pointing at the
wrong line in ingest_doc.py

**Where:** `src/overwatch.py:741` and `src/overwatch.py:935`

Both comments assert a "house exemption for console renderers" is documented at
`ingest_doc.py:348`:

```
740:            # a defect-of-fact finding. WATCH.md is a file, not a console, so the house
741:            # exemption for console renderers (ingest_doc.py:348) does not reach it.
```

```
934:                        key=lambda x: x["module"]):
935:            # A CONSOLE renderer, so the cut stays (house exemption, ingest_doc.py:348) -- but
```

**What's actually at `ingest_doc.py:348`:**

```python
346:        for e in (got.get("entries") or []):
347:            if not isinstance(e, dict) or not (e.get("name") or "").strip():
348:                continue
349:            k = _key(e["name"])
```

Line 348 is a bare `continue` inside an entry-filtering loop -- it has nothing to do with console
truncation or any "house exemption" doctrine. The actual text the comments mean to cite is
several lines further down, at `ingest_doc.py:363`:

```python
355:                # NO [:2000] (order baf4a18d1f1a, HARD RULE 0). This module's own docstring
...
362:                # descriptions are the homebrew sourcebooks this module targets. Other writers
363:                # store them whole; the console renderers truncate at their own call sites. If a
364:                # per-entry ceiling is ever wanted it must be a REFUSAL with the length stated.
```

`ingest_doc.py:363` ("Other writers store them whole; the console renderers truncate at their own
call sites") is the sentence that actually states the doctrine both `overwatch.py` comments rely
on. The file has clearly been edited since these two citations were written -- exactly the "drift"
this project's own doctrine warns about elsewhere ("Content labels, not line numbers... a stale
number costs a grep every time someone diagnoses it", `weave.py:212-216`, `wiki_source.py:672`).
The house style in this project's own recent fixes (see `weave.py`, `wiki_source.py`) has been to
replace such citations with content labels/symbol names precisely so they cannot drift. These two
survived as bare line numbers and drifted.

**Why it matters:** low severity by itself (`ingest_doc.py` line 348 still exists and the doctrine
still exists a few lines away), but a reader who checks the citation as instructed -- which this
codebase's own doctrine repeatedly insists on doing -- finds a `continue` statement and nothing
about console rendering, and has to hunt for the real sentence. It is exactly the kind of drift
this project has fixed by hand at least twice before in these same eight files (`weave.py:187`
self-correction, `catalogue_web.py:150` self-correction cited in `wiki_source.py`).

**Remedy:** update both citations in `overwatch.py` (lines 741 and 935) to point at
`ingest_doc.py:363`, or better, follow the project's own established fix pattern and cite by
content/symbol instead of line number (e.g. "ingest_doc.py's `NO [:2000]` comment") so future
edits to `ingest_doc.py` cannot silently re-break the pointer.

---

## Finding 2 (MINOR) -- stale cross-reference in weave.py pointing at the wrong line in pipeline.py

**Where:** `src/weave.py:247`

```
243:                # NO CAP. `if len(shared[p]) < 8` was the last cap standing in the weave, and it
244:                # was invisible because it sat in the BUILDER while both consumers -- this
245:                # module's own writer and `pipeline.py:1761`, the production path that writes
246:                # `data/RESONANCE_GRAPH.json` -- carried the comment "WHOLE list -- Hard Rule 0,
247:                # ruled 2026-08-24" directly above it. The comment described the ruling; the data
```

**What's actually at `pipeline.py:1761`:**

```python
1760:**Run one instance only.** Two concurrent runners both write `PIPELINE_STATE.json` and the same
1761:record files; that happened on 2026-08-21 and the records survived by luck. Check before starting:
```

Line 1761 is inside a markdown docstring about not running two pipeline instances concurrently --
unrelated to `RESONANCE_GRAPH.json` or the `shared_sample` list. The actual write site the comment
means to cite is at `pipeline.py:2372-2375`:

```python
2372:    landed.append(land_json(os.path.join(HERE, "data/RESONANCE_GRAPH.json"),
...
2375:                          "shared_sample": shared[(a, b)]}   # WHOLE list -- Hard Rule 0, ruled 2026-08-24
```

This is the exact "WHOLE list -- Hard Rule 0, ruled 2026-08-24" comment `weave.py`'s own text
quotes, confirming this is the intended target and the line number has simply drifted (pipeline.py
has clearly grown by roughly 600 lines since this comment was written).

**Why it matters:** same class and severity as Finding 1. `weave.py`'s own docstring (module
header, `main()`, and multiple inline comments in this exact file) is unusually insistent that
citations must be checkable and that stale ones "cost a grep every time someone diagnoses it" --
this citation fails that standard the file itself sets.

**Remedy:** update `weave.py:247` to cite `pipeline.py:2372` (or the `land_json(...
"data/RESONANCE_GRAPH.json"...)` call by name) instead of `:1761`.

---

## Noted but not filed (INFO / not a defect)

* `overwatch.py:301`, `_STATE_RANK = {"open": 0, "stale": 1, "confirmed": 1, "refuted": 2,
  "retired": 2, "closed": 2}` -- the `"stale"` and `"confirmed"` keys are never assigned as a
  finding's `state` anywhere in this file (`verify_open` only ever sets `state` to `"closed"`,
  leaves it `"open"`, or `round_once` sets `"retired"`). Grepped the whole `src/` tree for any
  other writer of `overwatch`'s ledger `state` field and found none. These two dict entries are
  therefore currently dead. Not filed as a finding: `_progress()` is a defensive helper reading a
  JSON ledger that could in principle be hand-edited or extended by a future caller, and a
  tolerant rank table over states the code doesn't currently produce is a reasonable defensive
  posture rather than a tautology or a masked failure -- there is no check here that always
  passes, just two unreachable-today dict keys. Flagged for the record in case a future audit
  wants to either wire up `"stale"`/`"confirmed"` as real states or trim the table.

* No cap/truncation defects were found in any of the eight modules on this pass -- every place
  that historically had one (`wiki_source.py`'s `category_members`/`find_categories`/
  `rank_by_size`, `weave.py`'s `pair_weights`/`surprisal_pair_weights`/main() write block,
  `canon_backup.py`'s `members()`/`snapshot()` error strings, `overwatch.py`'s `write_report`)
  already carries a comment explaining why it was fixed and is currently uncapped in the live
  code. Verified each of these directly against the source rather than trusting the comment.

* No discarded write-verdicts were found -- every `silence.write_json`/`silence.replace_retry`
  call across all eight files has its boolean return checked and acted on.
