# Audit batch 14 — assay.py, chain.py, rosetta.py, pantheon.py, grounding.py, chord_field.py, compress_store.py

Every line of all seven files was read in full (assay.py 649, chain.py 497, rosetta.py 409,
pantheon.py 309, grounding.py 246, chord_field.py 204, compress_store.py 66).

---

## src/assay.py

### Confirming the three already-filed findings

1. **`assay.py:221-223` — M18, `axis_score()` returns constant `9.9` at M10 for ANY input.**
   VERIFIED. Code:
   ```python
   i = LADDER.index(band)
   if i + 1 >= len(LADDER):
       return 9.9
   ```
   `LADDER` has 11 rungs (M0..M10), so `band == "M10"` gives `i == 10`, and `i+1 (11) >= len(LADDER)
   (11)` is always true — the branch is taken and `x` (the magnitude being scored) is never
   consulted. `1e30` and `1e40` both produce `9.9`. This happens strictly before `x` is used in
   the log-interpolation formula the docstring describes, so the docstring at 212-217 and the
   code diverge exactly as filed. No other caller of `axis_score` exists anywhere in this batch's
   seven files (grepped `axis_score\|INSTRUMENT_WINDOWS\|BAND_EDGES` across chain/rosetta/pantheon/
   grounding/chord_field/compress_store — the only hit was `pantheon.py:298` reading `A.WEIGHTS`,
   unrelated). Per instructions, not proposing a patch — reporting the mechanism only.

2. **`INSTRUMENT_WINDOWS` collapses to `(30, 30)` for M5–M10.** VERIFIED, confirmed by direct
   read of `assay.py:90-94`:
   ```python
   INSTRUMENT_WINDOWS = {
       "M0": (1, 18), "M1": (8, 22), "M2": (12, 26), "M3": (16, 28), "M4": (18, 30),
       "M5": (30, 30), "M6": (30, 30), "M7": (30, 30), "M8": (30, 30), "M9": (30, 30),
       "M10": (30, 30),
   }
   ```
   Every band from M5 up shares the identical degenerate `(lo, hi)` pair. In `instrument()`
   (line 501: `span = hi - lo`), `span == 0` for all of them, so `value = min(30, round(lo + (s/10)*span))
   = 30` regardless of the axis score `s` — every faculty at M5+ prints a flat `30`, differentiated
   only by the `transcendence_grade` suffix, never by the underlying axis score. Confirmed the
   shape; not re-deriving further since it's already filed.

3. **`assay.py:630-631` attestation→uncertainty table, re-typed by `custodes.py:229-230`'s
   `_ATT_BASE`.** Confirmed location and content:
   ```python
   floor = {"Witnessed": 0.10, "Instrumented": 0.08, "Transcribed": 0.20,
            "Reconstructed": 0.40, "Disputed": 0.55}.get(attestation, 0.30)
   ```
   This lives inside `interval_from_hands()` (Vol 0.5 §2 Theorem 4's between-hands interval), and
   is a *different* table from `SIGMA_BY_ATTESTATION` at lines 308-316 (used by `_interval()` for
   the per-axis composite propagation in `assay()`). Two independently-maintained attestation
   tables exist in this same file for two different formulas — worth flagging as the kind of
   duplication that produced the custodes.py hand-copy in the first place, even though each table
   is internally consistent with its own caller. `custodes.py` is outside this batch, not
   re-derived.

### Other findings

None. The rest of the module (BAND_EDGES, WEIGHTS/FACULTY_WEIGHTS derivation at 137-143,
`_interval()`, `assay()`, `null_instrument()`, `regress_test()`, `interval_from_hands()`) was read
line by line; the extensive inline erratum comments (Erratum 1 Kenshiro clamp, the X.11 faculty-
weight-zero erratum, the `_interval` weights-table-mismatch fix dated 2026-08-24, the SIGMA_MAX
derivation) all check out against the code that follows them — no comment/code contradiction found
beyond the three items above. `interval_from_hands()`'s coverage-enforcement loop (line 636:
`while any(abs(v-centre) > interval for v in vals): interval += 0.01`) terminates correctly since
`interval` is monotonically increasing past the maximum deviation.

---

## src/chain.py

### VERIFIED — unguarded concurrent read-modify-write on `unmatched` Counter (concurrency race)

`chain.py:353`, inside `extract()`'s `work(chunk)` closure, run by `ThreadPoolExecutor(max_workers=workers)`
(line 366, workers default 8):

```python
else:
    for side, k in ((w, wk), (l, lk)):
        if k not in idx:
            unmatched[side[:40]] += 1        # <-- line 353, OUTSIDE the lock
with lock:                                    # <-- line 354
    done["n"] += len(chunk)
    ...
    for e, src in local:
        edges[e] += 1
        prov[e].append(src)
        done["kept"] += 1
```

`unmatched` is a single `collections.Counter()` created once in `extract()` (line 304) and shared
across every worker thread. `done`, `edges`, and `prov` are all correctly updated inside the
`with lock:` block a few lines below, but `unmatched[side[:40]] += 1` executes earlier in the same
function, for every outcome in every chunk, **without the lock**. This is a genuine unguarded
read-modify-write on a dict touched by ThreadPoolExecutor workers (lens 5) — a lost-update race
under thread interleaving, which under-counts entries in the `unmatched` Counter. Contrast with
the careful locking discipline visible two lines later, which makes this look like an oversight
rather than a deliberate choice.

Consequence: `unmatched.most_common(40)` (line 108, persisted to `data/CHAIN.json`) and
`unmatched.most_common(8)` (line 456, printed to console) can silently undercount how often a
given unmatched name occurred. Grepped the rest of the batch and the wider `src/` tree for readers
of `CHAIN.json`'s `"unmatched"` field — found none (only `chain.py` itself reads/writes it), so
this is a race on a diagnostic-only field with no downstream consumer today; still a real bug
worth fixing since a future consumer would inherit silently-wrong counts.

### Hard Rule 0 — reviewed, judged non-violating

`chain.py:108` — `unmatched.most_common(40)` written into the persisted `CHAIN.json`. This ranks
then truncates to 40. However `unmatched` is a diagnostic tally of names that matched nothing in
the catalogue index — not itself a roster of catalogued entities, and (per the grep above) nothing
downstream reads it back for further processing; it exists purely to tell an operator what's being
missed most often. Per the lens's own instruction to "say whether it truncates real data or merely
bounds a diagnostic/preview" — this bounds a diagnostic. The **actual** contest data (`edges`,
`prov`) is never capped anywhere in this file. `chain.py:456` (`unmatched.most_common(8)`) and
`chain.py:487` (`order[...][:14]`) are console-print-only diagnostics, not persisted.
`extract(rows, limit=None, ...)`'s `rows = rows[:limit] if limit else rows` (line 301) is an
explicit, opt-in `--limit` CLI flag defaulting to no cap — not a silent truncation.

### Confirmed clean: atomicity, dedup-key, and the self-documented fixes

`write_result()` (chain.py:91-122) and `harvest()`'s incremental index (chain.py:189-206) both
write via `tmp = OUT + ".tmp"` + `silence.replace_retry(tmp, OUT)`, with an explicit
`print(...file=sys.stderr)` if the replace is denied — correct atomic-write discipline for these
two shared files (`data/CHAIN.json`, `state/chain_harvest_idx.json`). The self-documented m37 fix
(dedup key changed from `sentence[:120]` to the full sentence, chain.py:209-221) and the "outcome
index belongs to the model's numbered sentence, not chunk position" fix (chain.py:314-334) were
both read and the code matches the comments describing the fix — no regression found.

---

## src/rosetta.py

### Confirming the two already-filed findings

1. **`rosetta.py:194` — `srlimit=5`, Hard Rule 0.** VERIFIED:
   ```python
   d = F.api(host, {"action": "query", "list": "search", "srlimit": "5", "srsearch": q})
   ```
   inside `scales_for()`'s loop over `SCALE_QUERIES` (28 query strings). Every search for a native
   power-scale page on a given wiki is capped to the top 5 MediaWiki search hits — a real
   truncation of an ordered listing of candidate pages, not a diagnostic. This directly matches
   the Hard Rule 0 pattern the project calls out by name (`srlimit=`).

2. **`rosetta.py:365` and `rosetta.py:377` — non-atomic shared-file writes.** VERIFIED, both are
   bare truncating opens on `ROSETTA.json` (and its `.raw.json` sibling):
   ```python
   # line 364-366, inside `--mine`:
   for path in (OUT, OUT.replace(".json", ".raw.json")):
       with open(path, "w", encoding="utf-8") as f:
           json.dump(out, f, indent=1, ensure_ascii=False)
   # line 377-378, inside `--refine`:
   with open(OUT, "w", encoding="utf-8") as f:
       json.dump(out, f, indent=1, ensure_ascii=False)
   ```
   Both violate the two-writer/atomic-write contract — `ROSETTA.json` is a shared data file and
   should land via `silence.write_json`/`silence.replace_retry` like `chain.py`'s `CHAIN.json`
   does. Ironically the `--mine` branch's own comment (rosetta.py:361-363) warns that `--refine`
   being run "against a stale raw copy... silently discarded a good 3,514-row mine" — the fix
   applied was writing a `.raw.json` backup copy, not making either write atomic, so a crash
   mid-`json.dump` on either path still leaves a torn/truncated `ROSETTA.json` or `.raw.json`.

### New finding — dead/vestigial code, currently harmless

`rosetta.py:394` (inside `a.check`):
```python
assays = {k: v["result"]["decimal"] + P.__dict__.get("_x", 0)
          for k, v in json.load(open(path, encoding="utf-8")).items()
          if v.get("result") and v["result"].get("decimal") is not None}
```
`P.__dict__.get("_x", 0)` reads an undocumented attribute `_x` off the `pipeline` module,
defaulting to `0`. Grepped all of `src/*.py` for any setter of `_x`/`P._x`/`pipeline._x` — none
exists anywhere in the codebase, so this always evaluates to `0` today and is a no-op. UNVERIFIED
as a live bug (it currently does nothing), but it's unexplained, unlabelled code that would
silently shift every Assay decimal used in the rank-correlation check if anyone ever sets
`pipeline._x` for debugging — worth removing or documenting rather than leaving as an inert trap.

### Hard Rule 0 — reviewed, judged non-violating

`numeric_rows()` (rosetta.py:169-171) drops values `> median * 1000` when `len(out) >= 8`. This is
a magnitude-based outlier filter (removing what the comment identifies as parse artefacts spanning
implausible orders of magnitude), not an order-then-truncate operation on a roster — every entity
is evaluated against the same threshold regardless of position, so it isn't the "top N" pattern
the rule targets. `main()`'s `--probe` (`top = sorted(...)[:6]`, line 343) and `--refine` summary
print (`sorted(...)[:12]`, line 383) are both console-only diagnostics, never persisted.

---

## src/pantheon.py

### Confirming the already-filed finding

**`pantheon.py:260` — non-atomic write of `PANTHEON.json`.** VERIFIED:
```python
out = compute(GODS)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
```
Same pattern as `rosetta.py:365/377` — a shared data file (`data/PANTHEON.json`) written via a
bare truncating `open(...,"w")` instead of `silence.write_json`/`silence.replace_retry`.

### Other findings

None. `GODS` is a hand-authored dict (Zeno, Vados, Whis, Beerus, Champa, Grand Minister) — read in
full; every entity has all 11 axes scored with citations, and `compute()`'s use of
`A.assay(anchor, scores, attestation="Transcribed", ..., worksheet=sheet)` always supplies a
worksheet, so none of these hit the H5 band-only path. Anchors used are M7/M8 only, so the M18
(M10-only) `axis_score` bug does not reach this file. `main()`'s merge of `Z_FIGHTERS.json`
(pantheon.py:264-271) swallows any exception via `silence.note("pantheon.py:merge")` — this
follows the project's established silence-logging idiom used identically elsewhere in this batch
(chain.py, rosetta.py) rather than a bare `except: pass`, so not flagged as a new violation. No
truncation of the `GODS` roster or the combined ranking (`rank = sorted(combined.items(), ...)` at
line 273 is a full sort with no slice; the `--full` detail loop at 289 iterates all of `rank`,
only skipping entries not in `out`, i.e. non-god entries, by design).

---

## src/grounding.py — CLEAN

Read in full. This module already carries its own fix for a previously-filed Hard Rule 0 bug: a
`cap` parameter on `classify_source()` now **refuses to run** if a caller passes a non-`None`
value (grounding.py:143-147):
```python
if cap is not None:
    raise SystemExit(
        "grounding.classify_source: `cap` truncates the origin-entry list in STORED order "
        "(Marvel: 153 of 5,012 origin entries read). Hard Rule 0 -- rank if you must, never "
        "truncate. Pass cap=None.")
```
and the docstring above it (120-141) is an honest post-mortem of the original bug (Marvel's
origin-entry count undercounted 33-fold), consistent with the code that follows. Verified
`classify_source()`'s actual scan (154-159) iterates every entry in `rec.get("entries", [])` with
no slicing. The `--write` path (235-239) uses `silence.write_json(p, out, ...)` for the shared
`GROUNDINGS.json`, correctly atomic, with an explicit inline comment noting the 2026-08-25
whole-tree atomicity sweep. `classify_text(text, top=3)`'s `scores.most_common(top)` (line 117)
ranks the fixed 6-member `GROUNDINGS` type dict, not an open-ended entity roster — not a Hard
Rule 0 concern. `main()`'s `low[:5]` sample print (line 231) is console-only. No comment/code
contradictions found.

---

## src/chord_field.py — CLEAN

Read in full. Pure physics-constant data (`ADJUDICATIONS` dict) and six small formula functions —
no file I/O, no loops over entity rosters, nothing to cap or race. Spot-checked the formulas
against the physics they claim to implement: `landauer_floor` = `bits * k_B * T * ln2` (correct
Landauer bound), `recoil_momentum` = `E/c` (correct photon-like relation, matches the A2 adjudication
text's own `p >= E/c` claim), `critical_power_self_focus` = Marburger self-focusing formula
`3.77·λ²/(8π·n0·n2)` (matches the standard form). `total_beta()` sums the six `beta_bits` values
correctly (64+96+8+0+128+32=328, arithmetic not hardcoded, derived from the dict). No findings.

---

## src/compress_store.py — CLEAN (one minor note)

Read in full (66 lines). `content_hash()` truncates a sha256 hex digest to 32 characters — this is
a deliberate content-hash length choice (128 bits of a hash), not the kind of ordered-listing
truncation Hard Rule 0 targets.

Minor note (not counted as a violation): `store()`'s blob write (compress_store.py:43,
`with open(path, "wb") as f: f.write(blob)`) is not an atomic tmp+rename write. Traced its only
callers: `generate.py:386` calls `store()` unconditionally per job (no existence-check-then-skip),
sequentially with no `ThreadPoolExecutor`/threading in `generate.py`, and the in-memory `catalog`
dict entry referencing the new hash is only added *after* `store()` returns, with `catalog.json`
itself flushed via `save_json` (not this batch) every 5 jobs and at the end. So: (a) no concurrent-
writer race is possible today (single-threaded caller), and (b) since the path is content-addressed
and `store()` always rewrites unconditionally rather than skip-if-exists, a torn write from a
hard interrupt is self-healing on the next run of the same job, and if it were ever read before
being re-run, `load()` raises loudly (`gzip.decompress`/`zstd` decompression error or the explicit
`ValueError`/`RuntimeError` for a bad codec) rather than returning silently-wrong prose. Reporting
for completeness since it's still a bare `open(...,"wb")` on a file that could in principle be read
concurrently by `catalog.py:97`'s `compress_store.load()`, but judged low severity given the above.
