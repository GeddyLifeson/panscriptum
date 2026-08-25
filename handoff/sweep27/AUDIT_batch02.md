# BATCH 02 AUDIT — sweep run27

Modules read, every line, no sampling:
- src/pipeline.py — 1909 lines
- src/sweep.py — 249 lines
- src/thread_integrity.py — 184 lines
- src/ledger.py — 136 lines

Total: 2478 lines.

---

## 1. pipeline.py:1327 — `update_handoff` writes RUN_STATUS.md with raw `os.replace`, not `silence.replace_retry`

**Severity: medium.  CONFIRMED (known-open, re-verified).**

```python
os.makedirs(os.path.dirname(HANDOFF), exist_ok=True)
tmp = HANDOFF + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    f.write(md)
os.replace(tmp, HANDOFF)
```

Every other writer in this file (`save_state`, `write_record`, `write_record_catalogue`,
`land_json`) goes through `silence.replace_retry`/`_landed`, which retries on a transient Windows
`PermissionError` (an antivirus scan or a concurrent reader holding the handle) and reports the
verdict rather than raising. `update_handoff` is called after *every single unit* across every
phase, so it is the highest-frequency writer to a shared file in the whole pipeline, and it is the
one writer with no retry and no failure signal — a denied replace here is caught only by the
generic `except Exception: log("(handoff update failed...")` around the whole function, which logs
and moves on, leaving `tmp` orphaned and `RUN_STATUS.md` stale with no downstream consumer told
anything is wrong. Failure scenario: a virus scanner or another process (e.g. `--status` invoked
concurrently, which itself does `open(HANDOFF).read()`) holds a read handle on `RUN_STATUS.md` at
the moment of `os.replace` on Windows; the replace raises `PermissionError`, is swallowed by the
outer `except Exception`, and the status file silently stops updating for however long the
contention lasts — with nothing in the loop retrying.

Also note: this same function is the one the docstring at the top of the file (line ~50-64) singles
out as "THE RUNNER GETS ITS OWN FILE" specifically to stop a two-writer clobber — the intent (loud,
safe, atomic replace) is stated in the file's own header comment, but the mechanism actually used
for *this* file is the one without the retry/verdict discipline every sibling writer in the same
module was given.

---

## 2. pipeline.py:521 (`write_record`) — drift detection only catches entry-COUNT changes, not entry-CONTENT changes at equal count

**Severity: high.  CONFIRMED (traced).**

```python
if len(disk.get("entries") or []) != len(rec.get("entries") or []):
    # ... per-entry judgment-field merge, disk wins for entries, logs "drifted... merged"
    merged = disk
else:
    pass  # falls through — merged stays == rec, the STALE in-memory copy
...
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)
return _landed(tmp, path)
```

The function's whole stated purpose (docstring, lines 503-516) is "WITHOUT clobbering a concurrent
writer's work" — it merges *only* when `len(disk.entries) != len(rec.entries)`. If
`write_record_catalogue` (the other writer) replaces, renames, or corrects entries on disk in a way
that happens to leave the total entry **count** unchanged — e.g. it fixes 5 mis-scraped entry names,
or swaps 3 junk entries for 3 real ones during the same window the pipeline is mid-phase holding an
older in-memory copy of the same length — this drift is invisible to the length check. The function
takes the "fast path", `merged` stays `rec` (the pipeline's hours-old in-memory copy), and that
stale copy is written whole over the disk file with **no log message** (the "drifted... merged" log
line only fires on the length-mismatch branch) and no distinguishable trace from the normal
no-drift case. This is exactly the failure class the function's docstring says it exists to
prevent ("marvel.json went from 1,051 entries to 30,207... writing the pipeline's stale in-memory
copy over that would silently revert"), just gated on count instead of content, so a same-count
content drift reproduces the identical loss silently. Concrete repro: catalogue rewrites 5 of
marvel.json's 1,051 entries (same total, different names/descriptions/whatever fields) while the
pipeline holds its own 1,051-entry copy from phase start; the next `write_record` call for that
path takes the fast path and overwrites the catalogue's 5 fixes with the pipeline's stale versions,
with zero indication in the log that anything happened.

Compare to the sibling `write_record_catalogue` (line 411), which merges unconditionally by entry
*name*, not by list length — it does not have this gap. The asymmetry between the two "two-writer
contract" functions is itself worth the supervisor's attention: one merges on content identity, the
other on count, and only the count-based one can silently regress.

---

## 3. ledger.py:130-133 — `assay_to_standards` hi==lo collapse at the top of the ladder

**Severity: medium.  CONFIRMED (known-open, re-verified, traced against assay.py's LADDER/BAND_EDGES).**

```python
i = LADDER.index(magnitude_band)
lo = BAND_EDGES[magnitude_band]["ruin"]
hi = BAND_EDGES[LADDER[min(i + 1, len(LADDER) - 1)]]["ruin"]
joules = math.exp(math.log(lo) + (ruin_score / 10.0) * (math.log(hi) - math.log(lo)))
```

`LADDER = ["M0", ..., "M10"]` (assay.py:105). For `magnitude_band == "M10"`, `i == 10 ==
len(LADDER)-1`, so `min(i+1, len(LADDER)-1)` clamps back to `i` itself: `hi == lo` (both
`BAND_EDGES["M10"]["ruin"] == 1e99`). The interpolation term `(math.log(hi) - math.log(lo))`
is then exactly `0.0`, so `joules == lo == 1e99` **regardless of `ruin_score`**. Failure scenario:
`assay_to_standards("M10", ruin_score=0)` and `assay_to_standards("M10", ruin_score=10)` return the
identical `joules`/`standards` value — an M10 entity assayed at the very bottom of its band's
within-band range prices identically to one assayed at the top. Every entity landing in the top
band of the Ladder (the band the charter calls Omniversal, presumably a non-trivial fraction of the
priced roster once assay-backed entries exist) loses all price differentiation the `ruin_score`
parameter is supposed to provide. The function has no special-case or fallback for the top band —
no synthetic ceiling above M10 is defined anywhere in `BAND_EDGES` to interpolate toward.

---

## 4. thread_integrity.py:106-113 — DANGLING requires ALL shared keys to have drifted, not any

**Severity: low/medium.  SUSPECTED — plausibly deliberate, flagged as a question.**

```python
if ents is not None:
    gone = [k for k in shared if k not in ents.get(a, ()) or k not in ents.get(b, ())]
    if gone and len(gone) == len(shared):
        out["DANGLING"] += 1
        ...
        continue
```

The docstring for `classify()` describes DANGLING as computed "against the live records: a
candidate key whose source no longer holds that entity (weave drift)" — phrasing that reads as
per-key. The code instead requires **every** shared key behind a source-pair's implied thread to
have drifted (`len(gone) == len(shared)`) before the pair is marked DANGLING; a pair backed by 3
shared entities where 1 has since been renamed/removed from one side stays classified
IMPLIED-UNRECORDED, with the drifted key silently absorbed and never surfaced anywhere (it is not
in `detail["DANGLING"]`, and `gone` itself is discarded after the length check). This may be the
intended semantics (a pair with *any* live shared evidence is still a real implied thread, weaker
but not false) — flagging because the docstring's wording doesn't obviously say "requires total
drift," and because a partially-drifted key is currently unobservable in the tool's output at all,
which cuts against the module's own stated purpose of surfacing exactly this kind of hole.

---

## 5. pipeline.py:1653 (`phase_shelve`) — `shelved` dict keyed `source::name` silently collapses same-name entries within one source

**Severity: low/medium.  SUSPECTED — depends on whether intra-source duplicate names occur in the corpus.**

```python
for e in r.get("entries", []):
    key = "%s::%s" % (src, e.get("name"))
    shelved[key] = {...}
```

`weave` (phase 3) resolves entity identity **across** sources; nothing in these four modules
de-duplicates two entries carrying the identical `name` **within the same source's own entry
list** (e.g. two different NPCs both literally named "Guard", or a doc-ingest appending an entry
whose name collides with an existing catalogued one). If that occurs, the second entry silently
overwrites the first in `shelved`, and the discarded entry is dropped from `SHELVES.json` with no
log line, no count adjustment beyond `len(shelved)` being smaller than the true entry total, and no
way to tell from the output that it happened. Not confirmed against the actual corpus (would need
a scan of data/records/*.json for intra-source name collisions to promote this to CONFIRMED).

---

## 6. Hard-Rule-0-shaped items: text truncated before being shown to the model or written to a field (all documented, none appear to drop corpus coverage)

**Severity: low.  Framed as a question, not asserted as bugs — flagging per the sweep's explicit "even if it looks reasonable" instruction.**

pipeline.py contains numerous `[:N]` truncations of *text content* (not entry lists) with
explicit owner-reasoning comments attached, e.g.:
- `pipeline.py:707` — `chunks = [...] or [rest[:14]]`: when a source has **zero** feat-bearing
  entries, only the 14 longest-description entries are ever shown to the model for ceiling
  nomination; any 15th+ description-only entry is never nominated in that source's synthesis pass
  at all. Documented at length (lines 686-706) as a deliberate consequence of "a lead paragraph
  cannot carry a ceiling feat," but it is still a hard cap on which entries are ever *considered*
  for the ceiling role, specifically in the case where a source has no mined feats yet (an early,
  under-explored source is exactly the case where this matters most).
- `pipeline.py:1080` — entrypass descriptions truncated to 240 chars before judgment; a feat
  stated only after char 240 of a long description would never be seen by the model in that pass.
- `pipeline.py:634/636`, `sweep.py:59-60` — filename-safety truncation of source/entity name to
  40/80 chars for cache paths; two different entities whose *first* 40/80 sanitized characters
  collide would silently share a cache file. Not observed, and low-probability given entity naming
  conventions, but the collision is structurally possible and undetected if it happens.

None of these drop an *entry* from the corpus outright (all entries still get a batch/chunk turn
eventually across the full sweep) — they cap what text is *shown* per call. Distinguishing this
from the two prior batches' likely findings on drop-an-entry caps; raising here only because the
sweep's instructions call for reporting every `[:N]` regardless of apparent reasonableness.

---

## Items checked and found clean

- All record/state writers in pipeline.py other than `update_handoff` (line 1327) go through
  `silence.replace_retry` via the shared `_landed()` helper — verified by grepping every
  `os.replace`/`json.dump` site in the file.
- sweep.py's final write (`silence.write_json(OUT, rows, ...)`) is correctly guarded and reports
  its own verdict to the caller (exit code 1 on denial) — no violation.
- thread_integrity.py performs no writes at all (read-only tool); no two-writer or concurrency
  exposure.
- No bare `except:` anywhere in the four modules; every `except Exception` either calls
  `silence.note(...)` or carries an explicit `"silence-exempt: ..."` comment justifying the
  omission (pipeline.py:441, 540) — both are `FileNotFoundError` handlers for a documented,
  expected first-run-empty-state case, consistent with the project's own convention elsewhere in
  the file.
- `clean_band`/`ceiling_band` split (pipeline.py:133-146): re-verified the fullmatch vs.
  match-with-`\b` distinction is applied correctly and in the safe direction — `ceiling_band`'s
  laxer parse is used only to *lower* a clamp, never to accept an unearned band, so the historical
  "M4.31 laundered into M4" failure mode the header comment describes does not reproduce through
  either function as currently written.
- `entry_settled`/`batch_settled` (pipeline.py:998-1034) — traced against the described m20/m14
  history; the single-predicate design and the "excluded entries never re-sent to the model" guard
  (`if batch[i].get("excluded"): continue` at the result-walk) both hold as documented.
- The M0-out-of-band clamp in `phase_entrypass` (`order.index(band) > order.index(syn)`) is in the
  correct direction — clamps *down* to the source's ceiling band, never up. Verified the index
  ordering (`order = ["M%d" % n for n in range(11)]`) matches ascending magnitude.
- ledger.py's `to_standards`/`from_standards`/`cross_rate` — sanity-checked the conversion algebra
  by hand (gil/zenny example); no inversion.
- thread_integrity.py's use of `d * 1000.0` against `event_age_years` — cross-checked against
  propagation.py's `YEARS_PER_UNIT_DISTANCE = 1000.0` constant; the scaling is consistent with
  that module's declared convention, not a unit-mismatch bug.
