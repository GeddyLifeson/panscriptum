# AUDIT batch02 — src/pipeline.py, src/sweep.py, src/halo.py, src/physics.py

Full line-by-line read of all four files (pipeline.py 1876 lines, sweep.py 241 lines,
halo.py 179 lines, physics.py 150 lines). Findings below; each cited `file.py:LINE`, each
labeled VERIFIED (read + traced) or UNVERIFIED (plausible, not traced).

---

## src/pipeline.py

### KNOWN/ALREADY-FILED — confirmed, not re-derived

**pipeline.py:487-530 (`write_record`)** — CONFIRMED. The drift check at line 506 is
length-only:
```python
if len(disk.get("entries") or []) != len(rec.get("entries") or []):
```
A concurrent writer that changes the *same* number of entries (edits fields without
adding/removing any) produces no drift signal, so `merged = rec` (the stale in-memory copy)
silently overwrites the concurrent writer's changes. VERIFIED by reading the branch.

Both merge field lists omit `"excluded"` — CONFIRMED at **both** sites:
- `write_record_catalogue`, line 434-435:
  `for fld in ("category", "scale_note", "scale_note_rejected", "magnitude", "topic", "catalogued"):`
- `write_record`, line 512-513: identical tuple.

Neither carries `"excluded"`, so a deliberate `cleanup.py` strike (`catalogued: False` +
`excluded: "<reason>"`) can have its `catalogued` field merged back toward `True` from a stale
disk copy, or (in `write_record_catalogue`) lose its `excluded` reason string entirely when an
entry is merged from disk into a fresh re-catalogue pass, because "excluded" is simply never
copied in either direction. VERIFIED by reading both merge loops and `entry_settled` (line
963-979) / `batch_settled` (line 982-1000), which is exactly the predicate this would defeat —
an entry losing its `excluded` marker becomes unsettled again and is resent to the model,
reproducing the "149 entries un-struck" failure mode the file's own comments describe as
already fixed once (line 991-997).

### New findings

**pipeline.py:673 — Hard Rule 0 caution, MOSTLY-DEFENDED — VERIFIED (truncates real data in the fallback branch)**
```python
chunks = [with_feats[i:i + 14] for i in range(0, len(with_feats), 14)] or [rest[:14]]
```
When a source has **zero** feat-bearing entries in the mined-feats cache (`with_feats` empty —
common early in a source's life per `_mined_feats`, line 584-618), the fallback samples only
the top-14-by-description-length entries (`rest[:14]`) out of the source's full cast and shows
only those to the ceiling-nomination model. Every other entry — possibly hundreds — is never
looked at for this source's synthesis pass. The surrounding comment (lines 664-672) defends
this as deliberate ("a lead paragraph cannot carry a ceiling feat"), but that argument assumes
mining has already found every real feat in the source, which is not what "no cached mined
feat" means — an entity's description can still legitimately state a feat that the feat-miner
simply hasn't reached yet. This is a real truncation of an ordered listing of entities feeding
a judgment call, gated only by author's-note reasoning, not by data completeness. Flagging per
Hard Rule 0's letter even though the code comment argues the risk is low.

The feat-bearing branch itself (`with_feats[i:i+14]` chunked across the whole list) is NOT
capped — every feat-bearing entry gets a chunk, this is fine.

**pipeline.py:1289-1295 (`update_handoff`) — two-writer/atomic-write inconsistency — VERIFIED (code fact); consequence UNVERIFIED**
```python
os.makedirs(os.path.dirname(HANDOFF), exist_ok=True)
tmp = HANDOFF + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    f.write(md)
os.replace(tmp, HANDOFF)
```
This is the only atomic-rename write in the file that bypasses `_landed`/`silence.replace_retry`
(every other tmp+rename in this file — `save_state`, `land_json`, `write_record`,
`write_record_catalogue` — routes through `silence.replace_retry`, which the project's own
two-writer contract mandates for shared state/data files: "shared state/data files must land
atomically via `silence.write_json` or `silence.replace_retry`"). `HANDOFF` (`RUN_STATUS.md`)
is written after every completed unit and is read by `--status` (line 1804) — a real
writer/reader pair. Because this call bypasses `silence.replace_retry`, if `os.replace` hits a
transient Windows file-lock (antivirus, an open `--status` read, an indexer) the exception
propagates to the surrounding bare `except Exception: log(...)` at line 1294-1295, which only
logs — no retry, no signal that the update did not land, unlike every other write in the file.
Whether this actually fires in practice depends on `silence.replace_retry`'s retry semantics,
which are outside this batch (`silence.py` not read) — flagged UNVERIFIED for real-world
impact, VERIFIED for the code-level inconsistency with the file's own established pattern.

### Reviewed, not flagged (for completeness)

- All `except Exception` / `except FileNotFoundError` blocks in pipeline.py were checked
  systematically (grep across the whole file): every one calls `silence.note(...)`, logs via
  `log(...)`, or carries an explicit `"silence-exempt: ..."` comment explaining the omission.
  No bare `except: pass`. CLEAN on the swallowed-failure lens.
- `records()` (397-408), `phase_synthesis`'s feat-chunking main path, `phase_weave`,
  `phase_cosmology`, `phase_history`, `phase_shelve`, `phase_write` — no other capped/truncated
  entity listings found; the file's own commentary shows several caps were already found and
  removed in prior passes (m13, "WHOLE list -- Hard Rule 0" at line 1761, etc.).
- `land_json` / `_landed` / `save_state` — all atomic via `silence.replace_retry`, correctly
  return/propagate the landed verdict per the docstrings. No bugs found.
- Ordering/clamp logic in `phase_entrypass` (lines 1108-1134, the magnitude clamp against
  synthesis ceiling) is correct: `order = ["M%d" % n for n in range(11)]` indexes M0..M10
  ascending, matching band strength; the clamp only ever lowers, never raises.

---

## src/sweep.py

**sweep.py:132-163 / 167-193 — funnel-invariant contradiction between docstring and code — VERIFIED (structural), consequence UNVERIFIED without live data**

The module docstring (lines 10-22) states: "Each stage is a strictly smaller set than the one
above" for the `catalogued → addressed → reachable → read → evidenced → assayable` funnel, and
`report()` (line 167-193) prints a "drop" per stage on that assumption (`drop = prev - f[k]`,
line 185).

But `shelfmark` (→ "addressed") and `host` (→ "reachable") are computed **per source**
(lines 134-140, outside the per-entry loop), while `catalogued` (line 146) is computed **per
entry**:
```python
host = hosts.get(src)          # per-source
key = where.get(src)           # per-source -> shelf
...
for e in r["entries"]:
    row = {..., "shelfmark": shelf, "catalogued": bool(e.get("catalogued")), ...}
```
Nothing ties an entry's `catalogued` flag to whether its *source* has a shelfmark or a known
host. An uncatalogued entry belonging to an already-shelved, already-reachable source is
counted as "addressed" and "reachable" but not "catalogued" — which is the opposite of nesting.
Given `phase_weave`/`phase_cosmology`/`phase_shelve` in pipeline.py are explicitly documented
as running independently of (and often ahead of) phase 2's completion ("safe to run before
phase 2 finishes", pipeline.py:1729), this mismatch is very likely to manifest as a negative
"drop" at the `addressed` stage in real output, not just a theoretical edge case. VERIFIED that
the code doesn't enforce the nesting the docstring claims; UNVERIFIED whether the live
`CHARACTER_SWEEP.json`/console output currently shows a negative drop (would require running
the sweep against real data, out of scope for a read-only audit).

By contrast, `read ⊆ reachable`, `evidenced ⊆ read`, and `assayable ⊆ evidenced` ARE correctly
enforced structurally (axis/page data is only ever populated inside the `if host: ev =
load(...)` block, lines 150-159), so only the `catalogued`/`addressed`/`reachable` portion of
the funnel is at risk.

### Reviewed, not flagged

- `report(rows, top=18)` (line 167), `gap.most_common(10)` (line 215), `bysrc.most_common(8)`
  (line 222) — all bound a printed diagnostic table only; the full untruncated `rows` list is
  written whole to `data/CHARACTER_SWEEP.json` (line 233-234) with no cap. Not a Hard Rule 0
  violation — these bound a preview, not the stored data.
- `load()` (63-91) — the FileNotFoundError/corrupt-file split is a deliberate, well-reasoned
  distinction (explained in its own docstring) between "expected absence" and "real corruption
  ledger noise", consistent with the project's `silence` convention. CLEAN, arguably exemplary.
- `sweep()`'s main entry loop (141-163) has no cap — every Persons-category entry across every
  record is included, no truncation.
- `cache_path()`'s `[:40]`/`[:80]` truncation (58-60) is filename-length hygiene, not an entity-
  listing truncation — same convention used elsewhere in the project (e.g.
  `pipeline.py:_mined_feats`). Not a Hard Rule 0 concern.

---

## src/halo.py

**halo.py:170-171 — non-atomic write of a data-output file — VERIFIED (code fact); shared-file status UNVERIFIED**
```python
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
```
`OUT` = `data/HALO_ASSAYS.json`, written with a bare `open(...,"w")` + `json.dump`, no
tmp-file + atomic rename, no `silence.write_json`/`silence.replace_retry`. This is exactly the
class of bug `pipeline.py`'s own `land_json` docstring (pipeline.py:468-484) says was already
found and fixed once elsewhere in this project ("later phases wrote their artifacts as
`json.dump(obj, open(path, "w"), ...)`: not atomic... a reader could see a half-serialised
file"). If `halo.py` is interrupted mid-write (Ctrl-C, crash), any concurrent reader of
`HALO_ASSAYS.json` sees a truncated/invalid JSON file. I did not verify whether any other
module in this batch or elsewhere reads `HALO_ASSAYS.json` concurrently with `halo.py`'s run
(halo.py is a standalone, manually-invoked script per its own module structure, not one of the
pipeline's own phases) — so severity is UNVERIFIED, but the pattern mismatch with the project's
own established atomic-write discipline is directly verifiable and worth fixing for
consistency/safety regardless.

### Reviewed, not flagged

- `ROSTER` (43-130) is a fixed, hand-authored dataset of exactly 3 entities (Precursors,
  Gravemind, Ur-Didact) — a deliberately curated worked example, not a truncated scan of a
  larger roster. Not a Hard Rule 0 concern.
- `compute()` (133-143) iterates the whole `ROSTER` dict, no cap.
- No swallowed exceptions anywhere in the file (none present at all — the file does no
  speculative I/O beyond the startup bad-char self-check, which raises `SystemExit` rather than
  swallowing).

---

## src/physics.py — CLEAN

Read in full (150 lines). This is a pure-math module (kinetic energy, material specific
energies, sphere volume, gravitational binding energy) with no file I/O beyond the standard
startup bad-char self-check, no shared-state writes, no caps/truncation of any listing, and no
exception handling to swallow. Checked the two most bug-prone spots by hand:

- `kinetic()` (75-93): correctly raises `ValueError` for `v >= C` rather than returning a huge
  number (line 85-89); Newtonian/relativistic switch at `0.1c` is numerically continuous
  (checked both formulas at the boundary — they agree to ~3 significant figures, as expected
  for a first-order relativistic correction at 0.1c).
- `joules_for()` (96-108): raises `KeyError` on an unknown material or mode rather than
  silently defaulting to rock — explicitly and correctly avoids the "wrong energy wearing the
  shape of a right one" failure the docstring calls out.
- `binding_energy()` (115-125): standard uniform-sphere formula `U = 3GM²/5R`, correctly
  implemented; docstring correctly flags it as an approximation not to be used for setting a
  band, consistent with actual usage note.

No findings. Explicitly reporting this module clean rather than manufacturing something.

---

## Coverage note

Ran the coverage-recording command per instructions from the repo root after writing this
report (see tool log).
