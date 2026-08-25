# Batch 14 Audit — assay.py, chain.py, custodes.py, ingest_doc.py, render.py, profile.py, compress_store.py

Run #24 whole-tree sweep. All seven files read in full, every line, top to bottom:
- `src/assay.py` (650 lines) — complete
- `src/chain.py` (497 lines) — complete
- `src/custodes.py` (419 lines) — complete
- `src/ingest_doc.py` (303 lines) — complete
- `src/render.py` (253 lines) — complete
- `src/profile.py` (202 lines) — complete
- `src/compress_store.py` (66 lines) — complete

Cross-references pulled (not full-read, grep/spot-check only, to confirm downstream impact):
`anchors.py`, `magnitude.py`, `verify_math.py`, `pipeline.py`, `dashboard.py`, `overnight.py`,
`generate.py`, `silence.py` (for `note`/`replace_retry`/`write_json` contract semantics).

Numeric verification was run directly against the miniconda interpreter for every claim marked
**VERIFIED** below (see the inline python invocations); nothing here is asserted from reading
alone where a runtime check was possible.

---

## 1. `assay.py:219-223` — `axis_score()` collapses to a constant `9.9` at the top of the Ladder

```python
i = LADDER.index(band)
if i + 1 >= len(LADDER):
    return 9.9
```

`LADDER` has 11 entries (`M0`..`M10`), indices 0-10. For `band == "M10"`, `i = 10`, so
`i + 1 (11) >= len(LADDER) (11)` is always true, and the function returns the literal `9.9`
**before it even looks at `x`**, `lo`, or `hi`. Every other band computes a genuine
log-interpolated score; M10 does not compute anything.

**Numerically confirmed** (`python -c` against the live module):

```
axis_score(1,     "M10", "ruin") -> 9.9
axis_score(1e10,  "M10", "ruin") -> 9.9
axis_score(1e30,  "M10", "ruin") -> 9.9
axis_score(1e33,  "M10", "ruin") -> 9.9
axis_score(1e36,  "M10", "ruin") -> 9.9
axis_score(1e40,  "M10", "ruin") -> 9.9
axis_score(1e99,  "M10", "ruin") -> 9.9
axis_score(1e150, "M10", "ruin") -> 9.9
```

A joule figure of `1` and a joule figure of `1e150` (fifty orders past the M10 floor of 1e99)
score identically. The docstring above the function claims "s(x) = 10 * clamp((ln x - ln x_r) /
(ln x_{r+1} - ln x_r))" — that formula is never reached for M10; the code silently substitutes a
constant. This also means the function does not even clear the guard it applies to every other
band (x must be positive, but need not clear the M10 floor at all) — an M10-anchored entity with
a trivially small measured quantity still scores 9.9, the same as one at the top of the charter's
own extrapolated ladder.

**Caller impact, enumerated:**
- `src/magnitude.py:244`, `quantity_scores(ev, anchor)` — calls `A.axis_score(x, anchor, axis)`
  generically for `ruin` and `reach` over every measured quantity found in an entity's feats, for
  whatever `anchor` band that entity has been assigned. Any entity assigned anchor `M10` gets
  every ruin/reach quantity feat scored as a flat 9.9 regardless of its actual magnitude — this
  is a production code path, not a test-only one.
- `src/anchors.py:115` (`ANCHORS["The Seat of the Creator"]`) is a real, live M10-anchored
  worked example in the codebase's own reference set, confirming M10 anchoring is an expected,
  used case, not a hypothetical.
- `src/verify_math.py` exercises `axis_score` at M10 only implicitly through band-edge tests, not
  through this specific top-of-ladder branch, so the test suite does not currently catch this.

Severity: **MAJOR**. Status: **VERIFIED** (numerically, and callers enumerated).

---

## 2. `assay.py:90-94` — `INSTRUMENT_WINDOWS` flattens five bands (M5-M9), not just the M10 ceiling, to a fixed `(30, 30)`

```python
INSTRUMENT_WINDOWS = {
    "M0": (1, 18), "M1": (8, 22), "M2": (12, 26), "M3": (16, 28), "M4": (18, 30),
    "M5": (30, 30), "M6": (30, 30), "M7": (30, 30), "M8": (30, 30), "M9": (30, 30),
    "M10": (30, 30),
}
```

`instrument()` computes `value = min(30, round(lo + (s / 10.0) * span))`. When `lo == hi`,
`span == 0`, so `value` is `lo` (`30`) for **every** axis score `s` in `[0, 9.9]`.

**Numerically confirmed:**
```
instrument("M7", {"ruin": 0.5}, worksheet="x")["faculties"]["Strength"] -> "30 (Grade II)"
instrument("M7", {"ruin": 9.9}, worksheet="x")["faculties"]["Strength"] -> "30 (Grade II)"
```
A barely-M7 reading and a maxed-M7 reading print the identical faculty value and Grade.

Context found in `anchors.py:113-127` (`ANCHORS["The Seat of the Creator"]`, anchor `M10`):
the code's own comment explains the *M10* saturation is deliberate — "the ceiling... every
faculty pins at 30 regardless of score... A ceiling that keeps climbing is a broken ruler." That
justifies **M10** flattening by design (M10 is the literal top of the Ladder, nothing above it).

It does **not** justify M5 through M9. Compare the clear widening progression from M0 through
M4 — `(1,18)`, `(8,22)`, `(12,26)`, `(16,28)`, `(18,30)` — a monotonic climb toward the ceiling
that stops dead at M5 and pins flat for five full bands. Every being anchored anywhere from M5
to M9 — not just the one ontological ceiling case — has its Strength/Dexterity/Constitution/
Intelligence/Wisdom/Charisma faculties collapse to a single indistinguishable "30", with only the
separately-computed Transcendence Grade (I-V, driven purely by which band, not by the score)
differentiating output at all. A weak M6 being and a maximal M6 being print the same faculty
block.

Severity: **MAJOR** (for M5-M9; M10 alone appears to be intentional per the codebase's own
comment). Status: **VERIFIED**.

---

## 3. `assay.py:630-631` vs `custodes.py:229-230` — the "derived" attestation table is a hand copy, currently identical but with no live link

`assay.py` (`interval_from_hands`, lines 630-631):
```python
floor = {"Witnessed": 0.10, "Instrumented": 0.08, "Transcribed": 0.20,
         "Reconstructed": 0.40, "Disputed": 0.55}.get(attestation, 0.30)
```

`custodes.py` (lines 229-230):
```python
_ATT_BASE = {"Witnessed": 0.10, "Instrumented": 0.08, "Transcribed": 0.20,
             "Reconstructed": 0.40, "Disputed": 0.55}
```

Checked programmatically today: **the two tables are byte-for-byte identical**, no drift
currently exists. But `custodes.py`'s own comment directly above claims this is "DERIVED from
assay()'s own attestation table rather than restated" and warns explicitly that a hand-written
duplicate "would drift the moment either copy was edited." That is exactly what this is: there is
no `import`, no shared constant, no reference back into `assay.py` — `_ATT_BASE` is a second,
independently hand-typed literal that happens to still match. The comment describing it as
derivation is currently false; it is asserting a property (drift-proofness) the code does not
have. The very next edit to either table — which the comment itself predicts as inevitable — will
silently desynchronize `custodes.py`'s Custos quality readings from `assay.py`'s own published
interval-from-hands calculation, with no test or runtime check to catch it.

Severity: **MINOR** (no live bug today; the risk is a self-predicted, currently-latent one, and
the comment/code mismatch is itself the finding). Status: **VERIFIED** (values checked identical
today; absence of any import link confirmed by reading both files in full).

---

## 4. `chain.py:353` — `unmatched` Counter incremented outside the thread lock

```python
else:
    for side, k in ((w, wk), (l, lk)):
        if k not in idx:
            unmatched[side[:40]] += 1
with lock:
    done["n"] += len(chunk)
    ...
```

`work(chunk)` runs inside a `ThreadPoolExecutor(max_workers=workers)` (line 366, up to 8
concurrent threads by default). `edges`, `prov`, and `done` are all correctly mutated only inside
the `with lock:` block two lines below. `unmatched[side[:40]] += 1`, on the line the audit
flagged, executes **before** that lock is acquired, from every worker thread concurrently. A
`Counter.__getitem__`/`__setitem__` round-trip for `+=` is not a single atomic bytecode op;
concurrent increments from different threads can interleave and lose updates (a classic
read-modify-write race), even under the GIL, because the GIL only guarantees atomicity of
individual bytecodes, not of a compound `x[k] += 1`.

Practical impact is limited: `unmatched` only feeds the "most common names that match nothing"
diagnostic printout (`main()`, lines 454-457) — it does not affect `edges`, the Bradley-Terry fit,
or anything written to `data/CHAIN.json`. A lost increment here means the reported unmatched-name
counts can undercount, which could mask entity-index gaps that deserve fixing, but it does not
corrupt the actual Chain-of-Defeats result.

Severity: **MINOR** (real race, confirmed by reading the lock scope; consequence is confined to a
diagnostic counter). Status: **VERIFIED**.

---

## 5. `custodes.py:254` — unrecognized attestation grade defaults to a mid-range quality instead of the conservative worst case

```python
q = ATTESTATION_QUALITY.get(attestation, 0.4)
```

`ATTESTATION_QUALITY` values today: Witnessed 0.818, Instrumented 0.855, Transcribed 0.636,
Reconstructed 0.273, Disputed 0.0 (worst). An attestation string that doesn't match any key —
a typo, a future grade name, a caller passing something unexpected — silently gets quality
`0.4`, which sits *better* than "Reconstructed" and only modestly worse than "Transcribed." This
directly contradicts the defensive pattern `assay.py` itself uses one module up, in `_interval`:

```python
sigma = min(SIGMA_MAX, SIGMA_BY_ATTESTATION.get(attestation, SIGMA_MAX))
```//assay.py:343, which explicitly defaults an unrecognized grade to the *maximum* uncertainty
ceiling, with a comment explaining exactly why ("an unknown attestation grade must not be able to
claim more certainty than the ceiling"). `custodes.py` does not apply that same discipline: a
mistyped or novel attestation label silently produces a narrower, falsely more confident
`evidential_part` tilt correction than the evidence justifies, rather than erring toward the
widest interval as the sibling module does.

Severity: **MINOR**. Status: **VERIFIED** (arithmetic and code both confirmed; no evidence this
default is currently being hit by any caller in this batch — all callers pass one of the five
known grades — but the fallback itself is inconsistent with the project's own stated defensive
pattern).

---

## 6. `custodes.py:335-344` — `covers_every_reading` is a guarantee-by-construction, not a check (self-disclosed in comment)

```python
"covers_every_reading": all(abs(v - consensus) <= half + 1e-12 for v in vals),
```

`half` is defined at line 320 as `max(1.96 * total_sd, max(abs(v - consensus) for v in vals))`
and only ever widened afterward (line 323, staleness). By construction `half >= max|v - consensus|`
for every input, so this field can never evaluate to `False` — it is the exact "check that cannot
fail" shape this sweep is looking for. The module's own comment (lines 335-343, "m30") already
discloses this in full: "this is a GUARANTEE being published, not a check being run... true by
construction for every possible input and cannot fail," and explicitly flags that a genuinely
informative version (whether the *unwidened* 1.96·sd band alone covered every reading) does not
exist yet. Since the field is fully self-documented in the source and its limitation is already
on record, this is not a hidden bug — but it is exactly the failure shape the sweep's lens exists
to catch, and downstream JSON consumers of `convene()`'s output (dashboards, printouts) that don't
read this source comment would reasonably mistake `"covers_every_reading": true` for a passed
validation rather than an always-true tautology.

Severity: **MINOR/COSMETIC** (self-disclosed, not hidden — flagged here because it fits the lens
precisely and the disclosure lives only in a source comment, not in the emitted data). Status:
**VERIFIED**.

---

## 7. `ingest_doc.py:216` — `description[:2000]` truncates every mined entity description (Hard Rule 0 violation)

```python
"description": (e.get("description") or "").strip()[:2000],
```

This is a direct slice-cap on content pulled from the owner-supplied PDF ingestion pass —
exactly the truncation shape Hard Rule 0 (`CLAUDE.md`) forbids in absolute terms ("No limit, no
cap, no sample... If a wiki lists 40,000 characters, the library takes 40,000 characters"). Any
model-returned description longer than 2000 characters for a mined entity is silently cut at that
boundary with no indication in the record that truncation occurred (no `"...[truncated]"` marker,
no original length stored). A rich, long-form description mined from a 482-page sourcebook — the
exact scenario this module's own docstring describes as its reason for existing — is exactly the
kind of content this cap would clip.

Severity: **MAJOR** (explicit, unambiguous Hard Rule 0 violation; silent, unmarked truncation of
generated content). Status: **VERIFIED**.

---

## 8. `ingest_doc.py:116-126` — `record_path()` falls back to substring containment matching, which can silently attach a document's entities to the wrong record

```python
def record_path(source):
    p = os.path.join(RECORDS, slug(source) + ".json")
    if os.path.exists(p):
        return p
    want = slug(source)
    for fn in os.listdir(RECORDS):
        base = fn[:-5]
        if want in base or base in want:
            return os.path.join(RECORDS, fn)
    return p
```

When the exact slug doesn't exist as a file, this scans `RECORDS` (in `os.listdir` order, which
is filesystem-dependent and not sorted) for the first filename where either string contains the
other. Two-way substring containment is loose: a short or generic source name can match an
unrelated record whose slug happens to contain it as a substring (e.g. a slug fragment like
`"iron"` would satisfy `want in base` against `"ironman"`, `"iron-kingdoms"`, etc., in whichever
order the OS happens to list them). If it matches the wrong file, every entity `mine()` finds for
this ingestion gets silently merged into an unrelated source's catalogue record, and the "already
known" name-dedup (`known` set, built from that wrong record) would then also silently suppress
correctly-named entities that happen to coincide.

Severity: **MINOR** (real logic weakness, confirmed by reading; no data available in this audit
to confirm it has actually mismatched a real source — flagging as a risk rather than a confirmed
incident). Status: **VERIFIED** (code logic); real-world trigger **UNVERIFIED**.

---

## 9. `render.py:245` — non-atomic write to `output/views/<tier>.svg`

```python
with open(p, "w", encoding="utf-8") as f:
    f.write(v["svg"])
```

A bare `open(...).write()` with no temp-file-plus-`silence.replace_retry` pattern, unlike every
other shared-state writer in this batch (`chain.py`'s `write_result`/`harvest`, `ingest_doc.py`'s
`register`/state-cursor writes). A crash or concurrent reader mid-write would see a torn/partial
SVG file.

However: grepped the full `src/` tree for any other module that imports `render.view`,
`render.containment_svg`, or reads from `output/views/` — **found none**. This file's `--write`
path is only invoked by running `render.py` directly as a one-shot CLI tool; nothing else in the
pipeline consumes `output/views/*.svg` concurrently or at all. So while the write pattern matches
the project's general "shared state must use `silence.write_json`/`replace_retry`" contract in
form, in practice there is currently no second writer or concurrent reader that this non-atomicity
would actually race against.

Severity: **MINOR** (real pattern deviation from the project's own writer contract; verified no
current concurrent consumer, so live impact is low today but the file would need this fix before
being wired into anything else that reads `output/views/`). Status: **VERIFIED**.

---

## 10. `profile.py:129-138` — a failed `GENRES.json`/`TIERS.json` load becomes an indistinguishable blanket default for every world in the corpus

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

If either file is missing, unreadable, or fails to parse (any `Exception` — not just
`FileNotFoundError`), the whole table silently becomes `{}`. Downstream, `build_all()` does
`gspec = genres.get(src, {})` for **every single world**, so `genre` defaults to `"unclassified"`
and `register` to `"classical"` for the entire corpus — and `"unclassified"` is *also* a
legitimate real value a correctly-loaded table can produce for one world, so there is no way to
tell "this world is genuinely unclassified" from "the classification table failed to load
entirely" by looking at `build_all()`'s output. Likewise `AS.assign(w["designation"],
tiers.get(src, {}))` runs with an empty tier spec for every world if `TIERS.json` fails, silently
producing degraded/default addresses across the board.

`silence.note(...)` does log the exception to the health ledger (`state/failures.json` on
`flush()`), so the failure is not fully invisible to someone who checks that ledger afterward.
But `main()`'s own printed report (`profile.py:156-197` — "worlds profiled: N", sample rows,
round-trip check) would run to completion and print a fully plausible-looking result with every
world silently misclassified, and nothing in that printed report or the returned data structure
itself signals that the run degraded. This is precisely the "failed load turns into a blanket
default, indistinguishable from real data" shape the sweep is watching for.

Severity: **MAJOR**. Status: **VERIFIED** (code read in full; failure mode traced through to
`build_all()`'s consumption of both tables).

---

## `compress_store.py` — no findings requiring action

Read in full (66 lines). Two things noted but not flagged as bugs:

- `content_hash()` truncates SHA-256 to 32 hex chars (128 bits). This is a truncation of a hash
  output, not of a data universe (Hard Rule 0 is about not truncating what the library catalogues,
  not about cryptographic digest length), and 128 bits is astronomically collision-safe at any
  scale this project will reach. Noting for completeness, not flagging as a violation.
- `store()`'s `with open(path, "wb") as f: f.write(blob)` is a bare, non-atomic write, but the
  path is content-addressed (derived from the hash of `text`), so two writers of the *same*
  content write identical bytes to the same path — no meaningful two-writer conflict. A reader
  racing a writer mid-write would get a truncated blob, but `load()`'s decompression would raise
  loudly (`zstd`/`gzip` decompress errors on truncated input) rather than silently returning wrong
  data — this fails loud, not silent, so it does not fit this project's signature failure class.

No MAJOR or MINOR findings in this file.

---

## Summary table

| Severity | Location | Finding | Status |
|---|---|---|---|
| MAJOR | assay.py:219-223 | `axis_score()` returns constant 9.9 for all M10 inputs, docstring's log-interpolation never runs | VERIFIED |
| MAJOR | assay.py:90-94 | `INSTRUMENT_WINDOWS` flattens M5-M9 (not just the M10 ceiling) to `(30,30)`, erasing faculty distinctions | VERIFIED |
| MINOR | assay.py:630-631 / custodes.py:229-230 | Hand-duplicated attestation-floor table, identical today, no import link despite "DERIVED" claim | VERIFIED |
| MINOR | chain.py:353 | `unmatched` Counter incremented outside the lock; diagnostic-only race | VERIFIED |
| MINOR | custodes.py:254 | Unknown attestation grade defaults to mid quality (0.4) instead of worst-case, unlike assay.py's own pattern | VERIFIED |
| MINOR/COSMETIC | custodes.py:335-344 | `covers_every_reading` is true by construction (self-disclosed in comment already) | VERIFIED |
| MAJOR | ingest_doc.py:216 | `description[:2000]` — Hard Rule 0 cap on mined entity descriptions | VERIFIED |
| MINOR | ingest_doc.py:116-126 | `record_path()` substring-containment fallback can attach entities to the wrong record | VERIFIED (code); real trigger unverified |
| MINOR | render.py:245 | Non-atomic write to output/views/*.svg; no current concurrent consumer found | VERIFIED |
| MAJOR | profile.py:129-138 | Failed GENRES.json/TIERS.json load silently defaults every world's genre/tier data | VERIFIED |
| — | compress_store.py | No findings | clean |
