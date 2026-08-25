# Batch 16 audit — build_terminal.py, derivation.py, custodes.py, ingest_doc.py, render.py, profile.py, lognames.py

Every line of every file in this batch was read in full (build_terminal.py 580 lines,
derivation.py 559 lines, custodes.py 418 lines, ingest_doc.py 302 lines, render.py 252 lines,
profile.py 201 lines, lognames.py 36 lines).

`ingest_doc.py` was a **live job** at read time (`--source "Arcanum Worlds (Odyssey of the
Dragonlords)" --mine`). It was read only; nothing was run or touched, and none of its state
files (`data/docs/*/ingest_state.json`, `data/records/*.json`) were opened for write.

---

## build_terminal.py

### CONFIRMED (already filed) — build_terminal.py:572 — non-atomic shared-file write

```python
os.makedirs(os.path.dirname(OUT), exist_ok=True)
html = TEMPLATE.replace("__DATA__", data)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
```

`OUT = output/registry_terminal.html`. Plain `open(path,"w")` + `write`, no temp-file-and-rename.
A crash mid-write, or a reader (e.g. someone with the terminal open and reloading) landing in the
gap, sees a truncated/partial HTML file. `silence.write_json`/`silence.replace_retry` exist in
this codebase for exactly this reason and are not used here. VERIFIED — confirms the prior filing.
(Mitigating factor: this is a single-writer batch-regeneration script, not concurrently written by
multiple processes, so it is a data-integrity/atomicity gap rather than a race, but it is still the
"truncate-then-fill" pattern `silence.write_json`'s own docstring calls out.)

### Escaping is correct, not a bug

`main()` replaces every `<` in the JSON payload with `<` before splicing it into an inline
`<script>` block (line 568), and the JS-side `esc()` (lines 85–87) escapes `& < > " '` before any
catalogue string reaches `innerHTML`. Both are documented in-line as fixes for a real prior bug
(BUGS m10, 2026-08-24) and both are correct as written: only `<` needs neutralising inside a raw
`<script>` text node (the HTML parser only watches for the literal sequence `</script`), and the
Python-side replace operates only on `data`, not on `TEMPLATE`, so none of the template's own
markup is touched. CLEAN.

### Roster/cap review

`.roster{max-height:190px;overflow-y:auto}` (line 55) is explicitly documented as the fix for a
prior HARD RULE 0 violation (a shelved-source roster used to be sliced to 8) — it is now bounded
by CSS scroll, not by truncation; every name in `nd.s` is still rendered into the DOM
(`nd.s.map(...)`, line 492). Display-only string trims elsewhere (`.slice(0,24)`, `.slice(0,22)`,
`.slice(0,17)+"…"` at lines 241, 291, 323, 348, 353) shorten individual **labels** for legibility;
they do not drop items from `ss.forEach`/`ws.forEach`/`kids.forEach`, which iterate every element
of the underlying arrays with no cap. CLEAN — no HARD RULE 0 violation found.

### Correctness

The `holds` computation (line 483-484) sums `nd.k.length + nd.w?.length + nd.s?.length` rather
than using `||` short-circuit — this is itself documented as the fix for a prior undercounting bug
and is correct as written. No other logic bugs found in the layout/draw/pan/zoom code; it is
unusually heavily self-documented with prior-bug explanations, all of which check out against the
current code.

**Verdict: CLEAN except the confirmed non-atomic write at line 572 (already filed).**

---

## derivation.py

Pure data module (the `LEDGER` dict) plus a small graph-integrity checker (`check_graph`,
`depth`, `provenance`) and an AST-based constant scanner (`scan_constants`). No file writes at
all in this module.

- `scan_constants` (line 480-500) catches only `SyntaxError` narrowly (line 489-491) — not a
  broad `except Exception`, appropriately scoped. CLEAN.
- `check_graph`/`visit` (line 419-446) correctly detects dangling parents, rootless DERIVED
  entries, and cycles via an open/done state map — traced through, no bug found.
- `main()`'s "deepest derivation chains" printout (line 534) takes `sorted(LEDGER, ...)[:6]` —
  this is a **diagnostic report slice**, not a truncation of real data: `check_graph()` above it
  already validates every one of the 100+ ledger entries unconditionally, and this slice only
  bounds what gets printed to the terminal for human skimming. Not a HARD RULE 0 violation.
- This module is the **source of the fourth-copy claim** filed against `custodes.py:229-230` —
  see that entry below for the side-by-side quote.

**Verdict: CLEAN.**

---

## custodes.py

### CONFIRMED (already filed) — custodes.py:229-230 — comment claims "DERIVED", table is hand-copied

The comment (lines 221-228):

> "DERIVED from assay()'s own attestation table rather than restated. A second hand-written table
> of evidence quality would be a duplicate mechanism for a quantity the charter has already fixed
> -- the same error as the withdrawn tempo table (X.10 §4), and it would drift the moment either
> copy was edited. Quality is the complement of the interval that grade already earns:
>     quality(g) = 1 - base(g) / max(base)
> Monotone by construction, and it moves automatically if the charter revises a grade."

The code immediately under it (lines 229-231):

```python
_ATT_BASE = {"Witnessed": 0.10, "Instrumented": 0.08, "Transcribed": 0.20,
             "Reconstructed": 0.40, "Disputed": 0.55}
_ATT_WORST = max(_ATT_BASE.values())
```

And `assay.py` (its own `interval_from_hands`, lines 630-631):

```python
floor = {"Witnessed": 0.10, "Instrumented": 0.08, "Transcribed": 0.20,
         "Reconstructed": 0.40, "Disputed": 0.55}.get(attestation, 0.30)
```

The two dicts are byte-for-byte identical in keys and values. `_ATT_BASE` is not computed *from*
anything in `assay.py` — there is no import, no function call, no cross-reference — it is a
second hand-typed literal. `ATTESTATION_QUALITY` (line 234) is genuinely computed as
`1 - base/max(base)` **from `_ATT_BASE`**, so the *formula* is derived, but its *input table* is
exactly the duplicate mechanism the comment says this replaces — the same failure mode as the
withdrawn tempo table it cites as the cautionary example. If `assay.py`'s floor table is ever
revised, `custodes.py`'s copy silently goes stale, which is precisely the drift the comment
claims cannot happen. VERIFIED — confirms the prior filing exactly.

### Concurrency — already fixed, confirmed correct

`_custos_reading` (lines 237-252) builds a **private** weights dict (`w = {...}`) per call rather
than mutating `A.WEIGHTS` in place; the comment at line 247 explicitly documents this as the fix
for a prior "mutate-and-restore" race that was "correct single-threaded and silently wrong beside
any concurrent assay() call." Read through: `A.WEIGHTS` itself is never written to in this
function. CLEAN, confirmed fixed.

### `convene()` — traced, correct

- The interval-must-cover-every-reading invariant (line 320,
  `half = max(1.96*total_sd, max(abs(v-consensus) for v in vals))`) is enforced by construction,
  and `covers_every_reading` (line 344) is explicitly commented as a tautological check under the
  current definition of `half` — an honest self-aware comment, not a bug (it says outright that it
  "must not be mistaken for verification").
- Threnody's veto (line 352-356) correctly reuses `CURL_VETO_THRESHOLD = 0.10` (Saaty's CR bar via
  Theorem 1, not a fresh number) and correctly sets `decimal` to `None` with a reason string on
  veto, rather than returning a silently-wrong scalar. This is the *opposite* of a swallowed
  failure — a deliberate, signalled non-answer.
- `staleness_widening` (line 271-287) correctly guards `distance is None or years_since is None`
  before calling `propagation.observed_mark`.

**Verdict: one confirmed finding (comment-contradicts-code at 229-230, matches the filed report).
Everything else CLEAN.**

---

## ingest_doc.py (read only — live job, not touched)

### Finding — ingest_doc.py:98-99 — non-atomic write of `pages.json`

```python
with open(os.path.join(d, "pages.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=0, ensure_ascii=False)
```

Plain truncate-and-fill, not `silence.write_json`. Lower severity than the `build_terminal.py`/
`render.py` findings: this file is written exactly once per document, during the one-time `--pdf`
extraction step, by a single process, and nothing else in the codebase writes to this same path
concurrently (the `--mine` pass only *reads* it). A crash mid-write would corrupt that document's
extracted corpus and require re-running `--pdf` for that source, which is recoverable but not
silent-safe. VERIFIED as non-atomic; UNVERIFIED whether any code path ever writes it a second time
(a re-run of `--pdf` on the same source would, which would then make this a real hazard — not
traced further, out of scope for this batch).

### Finding — ingest_doc.py:216 — entity description silently truncated to 2000 chars

```python
"description": (e.get("description") or "").strip()[:2000],
```

This is a **field-level content truncation**, not a roster/listing truncation — it does not drop
any entity from the extraction, and the module's own docstring (lines 12-15) is explicit that
"the whole document is extracted, the whole corpus is chunked, every chunk is mined," which this
does not contradict at the entity-count level. But it does cut the *content* of any single
entity's description at 2000 characters with no signal that truncation occurred, which is in the
spirit of HARD RULE 0's "the library takes the full text" even though the rule's own examples
are all about roster/page/chunk-count caps rather than field-length caps. Flagging for the
supervisor to classify — VERIFIED the cap exists and is silent (no truncation marker, no log),
UNVERIFIED whether any real LLM extraction has ever actually hit 2000 characters for one entity's
description (plausible but not traced against actual `data/records/*.json` content).

### Finding — ingest_doc.py:159-160 — overly broad except when reading resume state

```python
try:
    with open(state_p, encoding="utf-8") as f:
        state = json.load(f)
except Exception:
    silence.note("ingest_doc.py:159")
    state = {"next": 0, "found": 0}
```

Catches every exception, not just "file doesn't exist yet" (the expected first-run case) — a
corrupt/truncated `ingest_state.json` (e.g. from the exact kind of non-atomic-write crash flagged
above, though this particular state file IS written atomically at lines 256-259) would also
silently reset to chunk 0 rather than surfacing as a distinct error. Low severity because the
consequence is bounded and safe: `known` is rebuilt from the record file's own entries (line 181),
so restarting the chunk cursor at 0 causes redundant LLM calls and re-skipping of already-known
entities, not data loss or duplication. VERIFIED as over-broad; the actual blast radius is small
because of the idempotent `known`-set design elsewhere in the same function.

### Two-writer contract — correctly followed

- `register()` (line 103-113) writes the shared `data/WIKI_HOSTS.json` via `silence.write_json`
  — correct, and the comment (line 111) correctly notes it's shared with `feats.resolve_hosts`
  and `standards`.
- The entity-merge write (line 246, `P.write_record_catalogue(rp, rec)`) correctly uses the
  **catalogue-side** writer, with an extensive comment (lines 228-245) explaining exactly why
  (a prior bug where `write_record`'s disk-wins merge discarded the first 14 entities this module
  ever found) and correctly checking the boolean return and rewinding `known` + stopping without
  advancing the cursor on a denied write, rather than assuming success. This is a well-built,
  correctly-guarded read-modify-write against a resumable job. VERIFIED correct.
- The provenance patch (line 290-293) uses `P.write_record` (the pipeline-side writer) for a
  single-field update to the same record — correct side of the contract for a non-cast-growing
  write.
- The resume-cursor write (line 256-259) uses a PID/thread-free `path + ".tmp"` name followed by
  `silence.replace_retry` — atomic, though note `silence.write_json`'s own docstring (read while
  cross-checking) says the plain `path + ".tmp"` naming (vs. `write_json`'s PID+thread-qualified
  temp name) is exactly the pattern that let two concurrent writers collide on the temp file
  itself elsewhere in the project. Low risk here specifically because `ingest_state.json` is
  per-document and this function is not designed to run twice concurrently on the same source,
  but it is not using the hardened helper. UNVERIFIED as an actual live hazard (would require two
  simultaneous `--mine` runs against the same `--source`), flagged for awareness only.

**Verdict: two-writer contract correctly followed for the shared/growing record files. Three
findings, all field/file-level rather than the roster-caps or race conditions the lens
prioritises — see above for severity notes.**

---

## render.py

### CONFIRMED (already filed) — render.py:245 — non-atomic write of diagram SVGs

```python
for t in DRAWN:
    v = view(t, coord=sample, tree=tree)
    p = os.path.join(out, f"{t}.svg")
    with open(p, "w", encoding="utf-8") as f:
        f.write(v["svg"])
```

Plain `open(path,"w")`, five files (`output/views/{hyperverse,xenoverse,metaverse,multiverse,
universe}.svg`), invoked only from `main()` under `--write`. Same non-atomic pattern as
`build_terminal.py:572`; same mitigating factor (single-writer, one process, not concurrently
contended). VERIFIED — confirms the prior filing.

### Everything else — traced, correct

- `children_of()` (line 163-187) correctly gates on whether the tree charts the next tier
  (`child_tier not in c`) rather than on a hardcoded schema assumption — the comment (lines
  169-175) explicitly documents this as a deliberate fix to avoid a stale-guard false-empty. No
  bug found; the fallback dict-merge `pools = {**tree.get("sources", {}), **tree.get("worlds",
  {})}` (line 166) would only silently drop entries on an exact key collision between a source
  name and a world designation string, which is structurally implausible given how those keys are
  built elsewhere (not traced further — UNVERIFIED, very low likelihood, not raised as a real
  finding).
- No roster/listing caps anywhere in `children_of` or `containment_svg` — every child is drawn
  (`for i, ch in enumerate(children)`, line 128), sized logarithmically for legibility but never
  dropped.
- `escape` used correctly and consistently (`html.escape`) on every interpolated string that
  reaches the SVG output (tier, label, child id, child name) — CLEAN, matches the contract
  `build_terminal.py`'s own comment (line 83) cites this module for.
- No bare/broad excepts anywhere in the file.

**Verdict: CLEAN except the confirmed non-atomic write at line 245 (already filed).**

---

## profile.py

### Finding — profile.py:129-138 — broad except swallows data-file load failures into an indistinguishable-from-empty default

```python
try:
    genres = json.load(open(os.path.join(HERE, "data", "GENRES.json"), encoding="utf-8"))
except Exception:
    silence.note("profile.py:131")
    genres = {}
try:
    tiers = json.load(open(os.path.join(HERE, "data", "TIERS.json"), encoding="utf-8"))
except Exception:
    silence.note("profile.py:135")
    tiers = {}
```

This is the lens-2 pattern precisely: on ANY failure (missing file, malformed JSON, permission
error, encoding error) both variables silently become `{}`, and `build_all()` (line 141-153) then
proceeds to produce a profile for **every single world** with `genre="unclassified",
register="classical"` and an untiered address — which is *exactly* the same output a correctly
parsed but genuinely-empty/legitimately-unclassified data file would produce. `silence.note()`
does record the exception to `state/failures.json` via `health.record` (confirmed by reading
`silence.py`'s `note()`), so this is not a fully silent failure in the project's own terms — but
nothing in `build_all()`'s return value, nor in `main()`'s printed report, distinguishes "GENRES/
TIERS.json failed to parse, all N worlds got the fallback" from "these are the actual
classifications." A caller of `build_all()` who doesn't separately go check `state/failures.json`
would see a fully-populated, plausible-looking profile catalogue with no visible sign that every
genre/register/tier field in it is a blanket default. VERIFIED — traced the exception path and the
consuming code (`build_all`'s `gspec = genres.get(src, {})` and `tiers.get(src, {})`) to confirm
the fallback is silently indistinguishable downstream.

### Everything else — traced, correct

- `encode`/`decode` (lines 86-112) round-trip correctly by construction: `_b32`/`_unb32` are
  inverse base-32 codecs, the regex in `decode` (line 95) matches exactly the format `encode`
  produces, and `main()`'s own round-trip check (lines 179-187) validates this over every world —
  not re-run here, but the logic was traced by hand and is internally consistent.
- `build_all()` (line 127-153) calls `WS.build_all(limit)` with `limit=None` by default —
  uncapped, all worlds processed. `main()`'s `rows[:8]` (line 171) is a printed-sample-only slice
  for the human-readable report, not a cap on the computed data (`rows` itself, from `build_all()`
  with no `limit` argument at line 157, is already the full uncapped set) — CLEAN, not a HARD
  RULE 0 violation.
- No file writes, no threading, no bare excepts beyond the one flagged above.

**Verdict: one finding (broad-except data-load fallback at 129-138). Everything else CLEAN.**

---

## lognames.py

36 lines: five log-filename constants (`READ`, `ROLL`, `PIPELINE`, `RECATALOGUE`, `SWEEP`,
`CALIBRATE`) and one `OWNER` dict mapping each filename to the command-line fragment that
identifies its live process, with a docstring explaining why this consolidation exists (a prior
bug where the stall detector's naming assumption silently blinded three job types). Read in full.
No logic, no I/O, no caps, no writes, no concurrency, nothing to find.

**Verdict: CLEAN.**

---

## Summary table

| Finding | Severity | Status |
|---|---|---|
| custodes.py:229-230 — `_ATT_BASE` claims DERIVED, is hand-copied from assay.py:630-631 | comment-contradicts-code | VERIFIED (confirms filed) |
| build_terminal.py:572 — non-atomic write of registry_terminal.html | atomicity | VERIFIED (confirms filed) |
| render.py:245 — non-atomic write of output/views/*.svg | atomicity | VERIFIED (confirms filed) |
| ingest_doc.py:98-99 — non-atomic write of pages.json | atomicity, low | VERIFIED |
| ingest_doc.py:216 — description field capped at 2000 chars, silent | content truncation, borderline HARD RULE 0 | VERIFIED (exists), UNVERIFIED (real impact) |
| ingest_doc.py:159-160 — broad except on state-file read | swallowed failure, low blast radius | VERIFIED |
| profile.py:129-138 — broad except on GENRES/TIERS load, fallback indistinguishable from empty | swallowed failure | VERIFIED |

derivation.py and lognames.py: CLEAN, nothing to report.
