# Batch 14 audit — run #25

Files (read end to end, every line): `src/assay.py`, `src/chain.py`, `src/generate.py`,
`src/ingest_doc.py`, `src/tempus.py`, `src/chord_field.py`, `src/module_index.py`.

---

## SPECIAL TASK: the "1/1 consistent, 5 unscored, 31h old" red standard

**VERDICT: STALLED JOB / DOWNSTREAM TRANSPORT FAILURE, not a defect in `assay.py`'s scoring
code.** None of the 5 unscored benchmarks ever reached `assay.assay()` — the failure happens one
layer up, in `magnitude.assay_entity()` (not in this batch, but read to answer the question).

**What "unscored" means**, precisely, from `standards.py:693-717` (not my batch, read to trace
the standard): it reads `data/CHARTER_REGRESSION.json`, written by `magnitude.calibrate()`. A row
counts as `scored` only if `status == "SCORED"`; `unscored = len(rows) - len(scored)`. A row gets
`status: "SCORED"` (`magnitude.py:799`) only when `assay_entity()` returned a `result` dict with a
non-`None` decimal — i.e. only when `A.assay()` was actually called with a real worksheet and
returned a value.

**Why 5 of 6 are unscored — read directly off the live file, VERIFIED:**
```
$ cat data/CHARTER_REGRESSION.json   (at: 1787541881 = 2026-08-23 22:24:41; age 31.06h — MATCHES the reported "31h old" exactly)
Jotaro Kujo   -> status NO_SCORE  "no axis cleared its gate on this entity's own source pages"
Kenshiro      -> status DEFERRED "no transport answered (one-shot, split, or local); retried next run"
Monkey D. Luffy -> status DEFERRED "no transport carried even the split calls; retried on the next run"
Naruto Uzumaki  -> status DEFERRED "no transport answered (one-shot, split, or local); retried next run"
Goku            -> status DEFERRED "no transport answered (one-shot, split, or local); retried next run"
Jace Beleren    -> status SCORED, got M2.76 vs published M2.88±0.25, consistent: true
```
That is exactly "1/1 consistent, 5 unscored, 31h old." **NO_SCORE** (Jotaro) fires at
`magnitude.py:577-579` before any model call — the evidence miner found nothing citable on that
entity's own pages. **DEFERRED** (the other 4) fires at `magnitude.py:646-648` /
`:640-643` — the pool (`cascade_bridge`) AND the local model (`P.ask` via `gpu_lane`) AND the
per-axis split all failed to return a usable answer. This is consistent with, and likely caused
by, two already-known open issues neither of which is in this batch: the pool's dead credentials
(NEXT_STEPS §2.B2 — cloudflare/hyperbolic/zai) and the `gpu_lane` wedge (NEXT_STEPS §3,
`gpu_lane.py:326-455`, m99) that can starve `P.ask()` calls silently.

**What code path would have to run to score them:** re-run `magnitude.calibrate()` end to end for
each of the 4 DEFERRED entities, which requires the pool OR the local Ollama call to actually
return valid JSON that survives the citation-verbatim gate (`verify()`/`_split_gate()`), before
`standards.py`'s own 26h freshness window elapses (**it already has** — 31h > 26h, so this
standard would read RED purely on age even independent of the unscored count). Jotaro additionally
needs the evidence miner to find gate-clearing material on `jojo.fandom.com`, a separate,
earlier-stage problem.

**Bottom line for the owner:** this is not a bug to fix in `assay.py` — the module never got a
chance to be wrong on these 5. It's an operational stall: `calibrate()` needs to be re-run, and it
will likely reproduce the same DEFERRED pattern until the pool/GPU transport issues already on the
queue (B2, m99) are addressed.

---

## SPECIAL TASK: `assay.py` top/bottom-of-ladder edge-case inventory

Full inventory, all read from the current source. **9 items found** (2 previously known/confirmed,
7 new).

1. **`assay.py:222-223`** `if i + 1 >= len(LADDER): return 9.9` in `axis_score()`. **[KNOWN]**
   Confirmed unchanged: `axis_score(x, 'M10', 'ruin')` returns `9.9` for `x` in `{1, 1e50, 1e150}`
   — VERIFIED by direct call. Top-of-ladder: no next rung to interpolate to.

2. **`assay.py:90-94`** `INSTRUMENT_WINDOWS` table: `M5`..`M10` all `(30, 30)`. **[KNOWN]**
   Confirmed unchanged — VERIFIED: `[A.INSTRUMENT_WINDOWS[b] for b in ('M4','M5','M6','M9','M10')]`
   = `[(18, 30), (30, 30), (30, 30), (30, 30), (30, 30)]`. Cascades into `instrument():517`
   `value = min(30, round(lo + (s/10.0)*span))` — with `span = hi - lo = 0` for M5+, `value` is
   `30` for every `s` from 0.0 to 9.9 alike.

3. **`assay.py:226`** `axis_score()`: `if not lo or not hi or hi <= lo: return None`. **[NEW]**
   A silent "unscored" collapse (the function returns `None`, which downstream is
   indistinguishable from "the model didn't cite anything for this axis") if any band edge is
   falsy or a rung's next-edge doesn't strictly exceed it. VERIFIED currently **dead** against the
   live table: scanned every axis of every adjacent `BAND_EDGES` pair — zero falsy edges, zero
   non-increasing pairs. A defensive guard against a future table edit, not a live bug today, but
   it IS a silent-collapse branch waiting for the next hand-edit of `BAND_EDGES` (the same failure
   mode that produced the M3-floor "two bands low" bug the file's own top comment describes).

4. **`assay.py:502-503`** `instrument()`: `grade_n = max(0, LADDER.index(anchor) - 5)`, then
   `grade = [...][grade_n] if grade_n <= 5 else "V"`. **[NEW — a check that cannot fail.]**
   VERIFIED by iterating every anchor in `LADDER` (`M0`..`M10`): `grade_n` is `0` through `5` and
   never exceeds `5`, because the ladder tops out at `M10` (index 10) and `10 - 5 = 5`. The
   `else "V"` branch is **unreachable dead code** — it can only ever fire if `LADDER` grew past
   `M10` while `instrument()`'s hardcoded 6-element grade list did not, at which point it would
   silently print `"V"` for every band past the list's end rather than raising. Exactly guideline
   8's shape: a branch that has never had the chance to fail because its guard condition can never
   be true against the current ladder.

5. **`assay.py:424`** `assay()`: `denom = sum(W[k] for k in applicable) or 1.0`. **[NEW — a check
   that cannot fail.]** VERIFIED: by the time this line runs, the function has already returned
   early (`:399-401`) unless `used` is non-empty, and any axis in `used` is by construction not
   `INAPPLICABLE` (its score is numeric), so it is always counted in `applicable` with its
   positive `W[k]`. `denom` can never be `0` when this line executes; the `or 1.0` fallback is
   unreachable given the guard two dozen lines above it. Confirmed live: a scores dict with every
   axis `INAPPLICABLE` except one scored `ruin=5.0` produced `axis_coverage: 1.0`, not an error —
   the only way to reach `used == {}` is already intercepted upstream.

6. **`assay.py:437-444`** `assay()` ceiling/promotion clamp: `if _dec >= 1.0: ... _dec = 0.99`.
   **Not a defect — noted for contrast.** This is the one top-of-ladder collapse in the file that
   is **disclosed rather than silent**: the clamp is accompanied by `at_ladder_ceiling` and
   `promotion_due` flags in the returned dict, and the docstring explains exactly why (M10.100 is
   "a broken ruler"). Included in the inventory only because the audit asked for every edge
   resolution; this one passes the honesty bar the others should be held to.

7. **`assay.py:242-248`** `band_for_quantity()`: loop initializes `out = "M0"` and only raises it
   when `x` clears a higher floor. **[NEW]** Bottom-of-ladder mirror of finding 1. VERIFIED live:
   `band_for_quantity(50, 'ruin')` (below the M0 floor of `1e2`) and `band_for_quantity(100,
   'ruin')` (exactly at the M0 floor) both return `"M0"` — indistinguishable. A quantity that
   clears no rung at all reads identically to one that just clears the bottom rung. Docstring
   caveats this is "a helper for sanity checks, NOT the Anchor," which limits blast radius, but
   the collapse itself is real and unflagged in the return value (a bare string, no "below floor"
   marker).

8. **`assay.py:343`** `_interval()`: `sigma = min(SIGMA_MAX, SIGMA_BY_ATTESTATION.get(attestation,
   SIGMA_MAX))`. **[NEW, but a *safe* default — noted for contrast with #9.]** An unrecognized
   attestation grade defaults to `SIGMA_MAX`, the ceiling — the most conservative (widest) answer
   available, and the comment two lines above explains this is deliberate ("must not be able to
   claim more certainty than the ceiling").

9. **`assay.py:630-631`** `interval_from_hands()`: `floor = {...}.get(attestation, 0.30)`.
   **[NEW — inconsistent with #8.]** VERIFIED live: `interval_from_hands({'AVAR':7.0,'QUILL':7.0},
   attestation='TotallyMadeUpGrade')` returns `interval: 0.3` — narrower than `'Disputed'` (`0.55`)
   and wider than `'Witnessed'` (`0.10`)/`'Instrumented'` (`0.08`). Unlike `_interval()`'s ceiling
   default (#8), this default is an **arbitrary mid-table value**, not the widest available
   (`0.55`). Two functions in the same module answer "what if the attestation string is
   unrecognized/mistyped" in opposite spirits: one clamps to maximum ignorance, the other silently
   picks a value that could understate the true interval if the intended grade was `'Disputed'`.
   Low probability of triggering (attestation strings are drawn from a small fixed vocabulary
   elsewhere in the pipeline), but the module contradicts its own stated principle
   ("an unknown attestation grade must not be able to claim more certainty than the ceiling") in
   this one function.

**Count: 9 edge-case resolutions inventoried (2 known/confirmed unchanged, 7 new).** Of the 7 new,
2 are live silent-collapse risks (`#3` dead-but-latent, `#9` live-and-reachable-on-bad-input), 2
are dead-code "checks that cannot fail" (`#4`, `#5`), 1 is a bottom-of-ladder mirror of the known
M10 collapse (`#7`), and 2 are documented/safe (`#6`, `#8`, included for completeness/contrast).

---

## `chain.py:353` — confirmed

```python
353:                    unmatched[side[:40]] += 1
354:        with lock:
355:            done["n"] += len(chunk)
```
`unmatched` is a `collections.Counter` created once in `extract()` (`:304`) and closed over by
`work(chunk)`, which `ThreadPoolExecutor(max_workers=workers)` (up to 8 threads, `:366`) runs
concurrently. The increment at `:353` sits inside the `for o in got["outcomes"]` loop, **two lines
above** the `with lock:` block that protects every other shared mutation in the same function
(`edges`, `prov`, `done`). `Counter.__iadd__` is a non-atomic read-modify-write; concurrent threads
racing on the same key can lose increments. **KNOWN** (NEXT_STEPS §3 "Smaller, verified"),
confirmed present at the same line in current source. **VERIFIED** by reading the concurrency
structure directly — 8-worker `ThreadPoolExecutor` calling `work()`, shared `unmatched` closure,
unguarded mutation vs. the guarded block immediately below.

---

## `generate.py:382-384` — confirmed

```python
382:        raw_path = os.path.join(raw_dir, safe_filename(job["address"], "md"))
383:        with open(raw_path, "w", encoding="utf-8") as f:
384:            f.write(f"<!-- {job['address']} -->\n\n{text}")
```
Bare truncate-then-fill, no tmp+rename. **KNOWN** (NEXT_STEPS §3 "Non-atomic shared writes still
open"), confirmed at the same lines. **VERIFIED live process/reader pairing**:
`catalog.py:92-94` reads the same path directly —
```python
92:    raw_path = os.path.join(HERE, v["raw_path"])
93:    if os.path.exists(raw_path):
94:        with open(raw_path, encoding="utf-8") as f:
```
`generate.py` runs for hours (`CLAUDE.md`'s own workflow explicitly invites checking progress with
`python3 src/catalog.py stats`/`read` *while generation is running*), so a `catalog.py` invocation
that lands between the `open(...,"w")` truncate and the completed `f.write()` reads a truncated or
empty file for that address, mid-run, with no retry or lock on either side. Note `save_json` two
lines earlier in the same module (`:53-58`) is properly atomic via `silence.write_json` — the
inconsistency is confined to this one raw-text write.

---

## New findings

### `ingest_doc.py:record_path()` — ambiguous-match record routing, live-reproducible misroute

```python
116: def record_path(source):
...
121:    want = slug(source)
122:    for fn in os.listdir(RECORDS):
123:        base = fn[:-5]
124:        if want in base or base in want:
125:            return os.path.join(RECORDS, fn)
126:    return p
```
**NEW. VERIFIED live** by direct call against the real `data/records/` (217 files):
```
record_path('Fallout')      -> data/records/all-fallout.json
record_path('Metro')        -> data/records/all-metro.json
record_path('Civilization') -> data/records/all-civilization-games.json
```
The containment fallback returns the **first** filename in `os.listdir()` order whose slug either
contains or is contained by the requested source's slug — no uniqueness check, no exact-match
preference, no warning when more than one file could match. If the owner ever runs
`ingest_doc.py --source "Fallout" --mine` intending a *new, separate* per-game record distinct
from the existing "All Fallout" umbrella entry, every extracted entity is **silently merged into
the wrong record** (`all-fallout.json`) instead of creating/using `fallout.json`. No current
filename pair in the 217-record corpus happens to produce a *wrong* answer today (the three cases
above may be intentional/correct routing, depending on how the roll names these sources — that's
a curatorial question I can't resolve from the code alone), but the mechanism itself has zero
protection against a genuine ambiguity, and the failure mode is silent (no error, no log line —
the wrong file is opened and written to as though it were right). Worth an exact-match-first
ordering, or at minimum a printed warning when the containment match is not unique or not exact.

### `ingest_doc.py:98-99` — non-atomic write of the extraction corpus

```python
96:    d = os.path.join(DOCS, slug(source))
97:    os.makedirs(d, exist_ok=True)
98:    with open(os.path.join(d, "pages.json"), "w", encoding="utf-8") as f:
99:        json.dump(out, f, indent=0, ensure_ascii=False)
```
**NEW. VERIFIED by reading.** `extract()` writes the entire PDF-derived corpus (potentially
hundreds of pages) with a bare truncating `open()` — no tmp+rename, unlike every other write in
this same module (`register()` uses `silence.write_json` at `:112`; `mine()`'s `ingest_state.json`
uses tmp+`silence.replace_retry` at `:256-259`, with a comment explicitly calling out the same
crash-mid-write failure mode this line is exposed to: *"a crash between `open` and `json.dump` left
a zero-byte state file"*). If `extract()` is interrupted mid-write (Ctrl-C, OOM, crash on a large
PDF), `pages.json` is left truncated/corrupt, and the next `--mine` invocation's
`json.load()` at `:154` raises uncaught, killing the run before it can even read `ingest_state.json`
to see if a resume was possible. Lower severity than a genuinely shared/concurrent file (this one
has a single writer, invoked by the owner, not raced against a concurrent process), but it is the
one write in this module that didn't get the atomicity discipline the rest of the file visibly
cares about, and it guards the largest single artifact (the whole document text).

### `module_index.py:2` — stale docstring count

```python
2: """MODULE_INDEX — the map of the 87 modules, generated from their own first lines.
```
**NEW, minor.** `src/` currently holds **95** `.py` files (confirmed: `ls src/*.py | wc -l` = 95;
also matches NEXT_STEPS.md's own header, "Run #24's pass: 95 modules"). The docstring's "87" is
stale — the count has grown since it was written. Not a functional bug: the code itself
(`glob.glob(os.path.join(HERE, "src", "*.py"))` at `:53`) is fully dynamic and never hardcodes 87
anywhere; only the prose is wrong. Cosmetic, but it's exactly the kind of drifted claim guideline 6
asks to catch, and it's a one-line fix (or better, compute the count into the sentence instead of
hardcoding it, so it can't drift again).

### `module_index.py:75-76` — non-atomic write

```python
75:    with open(OUT, "w", encoding="utf-8") as f:
76:        f.write("\n".join(lines))
```
**[KNOWN]** (NEXT_STEPS §3 "Non-atomic shared writes still open"). Confirmed at the same lines.
Low real risk — this is a manually-invoked doc generator, single writer, no known concurrent
reader that would observe a torn file — but it is the one write in the codebase's growing
atomic-write convention that the project's own standard would still flag.

---

## Modules read end to end and found CLEAN

- **`tempus.py`** (254 lines) — full read. All ladder/band arithmetic correctly imports and
  reuses `assay.BAND_EDGES`/`LADDER` rather than re-declaring them. Its own top/bottom-of-ladder
  edge cases (`rung_description_length()`'s `L_r(M0) = 0`, `band_resolution()`'s M10-inherits-
  M9-M10-width fallback at `:206-209`) are both **explicitly documented in the docstring and
  reasoned about**, not silent. No caps, no shared-file writes, no concurrency. **[KNOWN clean,
  reconfirmed.]**
- **`chord_field.py`** (204 lines) — full read. Pure physics/data module (constants +
  `ADJUDICATIONS` dict + a handful of stateless functions). No writes, no I/O beyond the constants
  table, no concurrency, no caps. **[KNOWN clean, reconfirmed.]**
- **`chain.py`** — clean apart from the confirmed known `:353` race. `write_result()` is correctly
  the sole writer of `CHAIN.json` (verified by grepping every caller in the tree — `pipeline.py`
  imports `chain` and calls `CH.write_result`, matching the docstring's "THE ONE WRITER" claim
  exactly, no stray second writer found). `HARVEST_IDX` write is properly atomic
  (tmp + `silence.replace_retry`). The `_partials()`/`entity_index()` short-name resolution logic
  correctly refuses ambiguous matches (`clash` set, `:256-261`) rather than guessing — contrast
  with `ingest_doc.py`'s unprotected containment match above.
- **`generate.py`** — clean apart from the confirmed known `:382-384` non-atomic write. Chunked
  writing (`WRITE_CHUNK`) verifies every entry is present in its block and fails the whole job
  loudly on a still-missing entry after one retry — correctly honors Hard Rule 0 (no entry is ever
  silently dropped; a shortfall is a hard failure, not a smaller book). `--limit` is an explicit
  opt-in CLI flag for the caller, not a silent cap.
- **`ingest_doc.py`** — clean apart from the two new findings above and the known `:216`
  `description[:2000]` cap (Hard Rule 0 item F in NEXT_STEPS, unchanged, confirmed present).
  `write_record_catalogue`'s return value IS checked and honored (`:246-251`) — this module gets
  the two-writer contract and the "advance on the write, not the intent" lesson right, per its own
  extensive comment explaining exactly why.
- **`module_index.py`** — clean apart from the known `:75-76` non-atomic write and the new stale
  docstring count. No caps (the "Everything else" bucket at `:68-74` ensures every module is
  listed regardless of `GROUPS` membership — no Hard Rule 0 concern).
- **`assay.py`** — the scoring math itself (`assay()`, `_interval()`, `interval_from_hands()`,
  `regress_test()`) is internally consistent and its edge-case handling is catalogued in full
  above; no findings beyond the ladder-edge inventory.

---

## Summary of severities

- **HIGH / live operational**: the 5-unscored red standard (operational stall, not code defect —
  see verdict above; action item is re-running `magnitude.calibrate()` once pool/GPU transport is
  healthy, both already tracked elsewhere in NEXT_STEPS).
- **MEDIUM**: `ingest_doc.py` ambiguous record routing (silent misfile risk, live-reproducible
  mechanism); `chain.py:353` unguarded Counter race (KNOWN); `generate.py:382-384` non-atomic
  write against a live concurrent reader (KNOWN); `assay.py:630-631` interval_from_hands' non-
  conservative unknown-attestation default.
- **LOW**: `ingest_doc.py:98-99` non-atomic pages.json write; `module_index.py:75-76` non-atomic
  write (KNOWN); `assay.py:226` and `:424` dead-code safety nets; `assay.py:242-248`
  bottom-of-ladder `band_for_quantity()` collapse (docstring-scoped to "not the Anchor");
  `assay.py:502-503` unreachable `else "V"` branch; `module_index.py:2` stale module count.
