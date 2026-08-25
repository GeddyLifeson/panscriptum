# BATCH 07 — Comprehensive code audit (run26)

Modules read in full, line by line:
- `src/magnitude.py` (1026 lines)
- `src/allsweep.py` (447 lines)
- `src/address_space.py` (346 lines)
- `src/tuning.py` (263 lines)
- `src/style_audit.py` (211 lines)
- `src/scope.py` (152 lines)

Total: 2445 lines.

---

## MAGNITUDE.PY

### M18 — CONFIRMED: `assay.axis_score(x, "M10", axis)` returns a flat 9.9 for every input, and `magnitude.py` feeds it straight into the published worksheet

**`src/assay.py:211-229`**

```python
def axis_score(x, band, axis):
    if x is None or x <= 0 or band not in BAND_EDGES:
        return None
    i = LADDER.index(band)
    if i + 1 >= len(LADDER):
        return 9.9
    lo = BAND_EDGES[band].get(axis)
    hi = BAND_EDGES[LADDER[i + 1]].get(axis)
    ...
    frac = (math.log(x) - math.log(lo)) / (math.log(hi) - math.log(lo))
    return round(10.0 * max(0.0, min(1.0, frac)), 2)
```

`LADDER = ["M0", ..., "M10"]` (11 rungs, indices 0-10). When `band == "M10"`, `i == 10`, `i + 1 == 11 >= len(LADDER)`, so the function short-circuits to a **hardcoded 9.9** regardless of `x`'s actual magnitude — a quantity of "40 tons" and a quantity of "10^90 joules" both score 9.9 if the entity anchors M10. Every other rung (M0-M9) computes a real log-interpolated fraction against the next rung's floor; only the top rung has no "next rung" to interpolate against, and the code silently substitutes a ceiling constant instead of, e.g., extrapolating the M9→M10 slope or returning `None`/`UNESTIMABLE`.

**Call path, confirmed against source:**

1. `magnitude.py:224-251 quantity_scores(ev, anchor)` — for every mined quantity (`"40 tons"`, `"3,000 km"`, etc.) converts to SI and calls `A.axis_score(x, anchor, axis)` at **`magnitude.py:244`**, axis restricted to `"ruin"` (joules) or `"reach"` (metres) per the `_TO_JOULES`/`_TO_METRES` tables (lines 207-221). `s is None` is the only skip condition (line 245-246) — a 9.9 return is accepted and used.
2. `magnitude.py:574 assay_entity()` computes `anchor` (line 660, clamped by `ceiling` at 661-662, both of which can legitimately be `"M10"` since `A.LADDER` and `SCOPE.json`/`host_ceiling()` both permit it).
3. **`magnitude.py:706-711`**, guard 5 QUANTITY:
   ```python
   for ax, q in quantity_scores(ev, anchor).items():
       scores[ax] = q["score"]
       sheet[ax] = f"INSTRUMENT {q['measured']} = {q['si']:.3g} SI  <- {q['feat'][:120]}"
   ```
   This **unconditionally overwrites** whatever the model/verify()/split-gate produced for that axis — comment above it explicitly says "an instrument outranks an opinion." For an M10-anchored entity, any measured Ruin or Reach feat therefore always prints `9.9`, no matter how small the measured quantity actually is, and this happens *after* every other guard (verbatim/relevance/subject/cross-axis) has already run, so nothing downstream catches it.
4. This flows straight through to `A.assay(anchor, scores, ...)` (line 718) and into the published worksheet/decimal for the entity.

**Consequence:** every M10-anchored entity with so much as one measured Ruin/Reach feat gets an artificially pinned 9.9 on that axis, which then also feeds `saturated()` (line 390-393, `len(nums) >= 6 and min(nums) >= 9.0`) — an M10 entity with a couple of real quantity feats is pushed measurably closer to a false SATURATION rejection (guard 4) by a value the instrument fabricated, not measured. This is the exact "top of range collapses silently" shape requested.

**Fix shape:** `axis_score` needs either (a) a real top-rung interpolation (extrapolate the M9→M10 slope, or use a defined "M10 ceiling" edge one rung further out) or (b) to return `None`/`UNESTIMABLE` at the top rung so guard 5 leaves the model's own judgement in place rather than silently overwriting it with a constant.

### MAJOR — Split-path assay skips guard 3 (SUBJECT), reintroducing the exact Zeno/Goku bug the file's own header documents

`_split_gate()` (**`src/magnitude.py:553-571`**), used for every split-path sheet, only re-checks verbatim citation:

```python
def _split_gate(got, cand):
    """Verbatim + relevance gate for split-path sheets. Axis-relevance is by construction
    (each axis was scored only from its own candidate list); verbatim is checked against that
    same list."""
    ...
    if isinstance(sc, (int, float)) and ft and any(ft in o for o in own):
        scores[ax] = max(0.0, min(9.9, float(sc)))
        ...
```

Compare with the one-shot path's `verify()` (**`magnitude.py:335-381`**), which additionally runs guard 3 at line 373: `if P._PATIENT.search(text) or _HANDOFF.search(text): ...reject...`. `_HANDOFF` (defined at **`magnitude.py:196-199`**) is the regex purpose-built to catch "Goku summoned Zeno, who immediately proceeded to erase the rogue Kai" — the flagship bug quoted verbatim in this file's own module docstring (lines 12-23) as the reason the five-guard architecture exists at all.

`_HANDOFF` is referenced exactly once in the whole file (`grep` confirms: line 196 definition, line 373 use). It is **never** consulted by `_split_gate()`, nor by `feats.py`'s `by_axis()`/`axis_evidence()` (checked directly — those only apply `P._PATIENT`, a *passive-voice* detector, e.g. "was destroyed", "consumed by X"; `_HANDOFF` matches *active-voice* actor handoff — "Goku summoned Zeno, who...", a shape `_PATIENT` structurally cannot catch, confirmed by reading `pipeline.py:898-905`).

Split is not a rare path — **`ONE_SHOT_MAX = 30000`** (line 429) makes it the *default* for any entity whose evidence exceeds ~30k characters, and the module's own commentary (lines 432-443, 594-599) says this is specifically the heaviest, best-documented entities: Goku, Jace Beleren, and "the five heaviest entities in the library." Those are exactly the entities the guard was written to protect, and they are exactly the ones now assayed without it.

### MINOR — stale diagnostic tag

`magnitude.py:235`: `silence.note("magnitude.py:151")` inside `quantity_scores()`'s except-block — every other `silence.note()` call in this file uses a descriptive function-name tag (`"magnitude.py:pool_ready"`, `"magnitude.py:_ask-cascade"`, etc. — 11 of 12 call sites). This one alone uses a stale line-number reference that doesn't correspond to the current line (235, not 151), presumably left over from an earlier refactor. Breaks traceability of this specific silent-failure site in `silence`'s logs.

### QUESTION — dead capability, currently harmless

`candidates(ev, cap=None)` (line 396) accepts a `cap` parameter that would truncate an axis's candidate list — a direct Hard Rule 0 violation shape — but it is never passed a non-`None` value anywhere in the codebase (only call site: `magnitude.py:576`, `candidates(ev)`). Not currently exercised, but the capability sits loaded.

`compose(entity, cand, epoch, budget, ...)` similarly has a whole budget-based dropping branch (lines 505-530) that is dead: the only call site (`magnitude.py:591`) always passes `budget=None`. This one is self-aware — the comment at line 730 explicitly says `"evidence_dropped_to_fit": dropped, # always 0 now; kept so a future budget cannot be silent"` — so it's intentionally-retained dead code, not an oversight.

### QUESTION — default-to-M0 on invalid anchor

`magnitude.py:660`: `anchor = got.get("anchor") if got.get("anchor") in A.LADDER else "M0"`. If the model returns a band string outside `A.LADDER` (malformed JSON field, typo, etc.), the entity silently anchors at the *bottom* of the ladder rather than being treated as a parse failure/DEFERRED. Given the SCHEMA already constrains `anchor` to `A.LADDER` via enum (line 315), this is likely unreachable in practice through the schema-validated cloud/local paths, but the split-retry path re-derives `anchor` the same way at line 692 (`got.get("anchor") if got.get("anchor") in A.LADDER else anchor` — that one at least falls back to the *previous* anchor rather than M0, so the two fallback behaviors are inconsistent with each other).

---

## ALLSWEEP.PY

### MAJOR — VERIFIERS list silently omits two of the "nine verifiers" the module's own docstring says it unifies

Docstring (lines 7-11) names nine subsystems: `health`, `silence`, `coverage`, `hostcheck`, `verify_math`, `thread_integrity`, `anchors`, `audit`, `style_audit`.

Actual `VERIFIERS` list (**lines 78-88**):
```python
VERIFIERS = [
    ("preflight", ["health.py", "--preflight"]),
    ("swallowed failures", ["silence.py"]),
    ("citation coverage", ["coverage.py"]),
    ("the numbers", ["verify_math.py"]),
    ("thread integrity", ["thread_integrity.py"]),
    ("the instrument", ["anchors.py"]),
    ("catalogue backscan", ["audit.py"]),
    ("continuity inventory", ["identity.py"]),
    ("calibration assays", ["reference.py"]),
]
```

`hostcheck.py` and `style_audit.py` — both confirmed to exist in `src/` — are **not in this list**, replaced by `identity.py` and `reference.py` (neither named in the docstring's enumeration). `hostcheck` is separately listed in `NEVER_RUN` (line 74) as a module whose bare run "does real, expensive or mutating work," which explains (but does not excuse — the docstring should say so) why it can't be a read-only VERIFY-tier entry. `style_audit.py` has no such excuse: its `main()` (confirmed by direct reading, see below) runs read-only and returns 0 cleanly when there's no generated output yet (`src/style_audit.py:197-200`) — nothing structurally prevents adding it. As things stand, prose-repetition regressions (the entire purpose of `style_audit.py`, and one of my other assigned modules this batch) are never checked by the integrity suite this project runs "so the answer is never more than one cycle old."

### MAJOR — LINT and RECONCILE tier findings never affect the exit code, and LINT results are never persisted

**`allsweep.py:439-443`**:
```python
bad = (len(broken)
       + sum(1 for r in verifiers if r["crashed"] or r.get("timeout"))
       + len((est.get("artifacts") or {}).get("bad", [])))
...
return 1 if bad else 0
```

`lint_bad` (LINT tier's undefined-name findings, lines 355-372) and `findings` (RECONCILE tier's output, lines 424-425 — the tier the docstring calls "the part no single verifier can do" and "where the next eighteen faults live," including hard findings like `"ENTRIES BANDED ABOVE THEIR OWN SOURCE'S CEILING"` and `"PHASES NAMED BY THE RUNNER WITH NO IMPLEMENTATION"`) are **never added to `bad`**. A run that surfaces real undefined-name bugs or real cross-subsystem disagreements still returns exit code 0 — "0 subsystem(s) in a bad state" is literally false in that case. Any supervisor/CI gate keyed off this exit code (which the docstring implies exists: "the supervisor calls it so the answer is never more than one cycle old") cannot see either tier's findings at all.

Compounding this: `lint_bad` is **printed to stdout only** — it is never included in the JSON written at line 436-438 (`{"imports": ..., "verifiers": ..., "reconcile": findings, "estate": est, "seconds": ...}` has no `"lint"` key), so nothing reading `ALLSWEEP.json` programmatically (a dashboard, another tool) can see LINT findings at all, even though the tier's own comment (lines 346-354) calls it "the sweep's answer to 'examine every line of every module.'"

### MAJOR — an unhandled exception inside the IMPORT or ESTATE tier crashes `main()` entirely, silently skipping RECONCILE and leaving a stale `ALLSWEEP.json` on disk

`check_import()` (**lines 98-119**) calls `subprocess.run([...], timeout=120, ...)` with **no try/except at all**. If any one of the ~95 modules hangs past 120s on `--help` (blocking I/O, a stray `input()`, a network call at import time, etc.), `subprocess.TimeoutExpired` propagates out of `check_import`, through `ex.map(check_import, mods)` at **line 340** (`imports = list(ex.map(check_import, mods))` — `list()` forces the exception to surface), and crashes `main()` before LINT, VERIFY, ESTATE, or RECONCILE ever run. Nothing is written to `ALLSWEEP.json` (the write is at line 436, never reached), so the file on disk is whatever the *previous* successful run left — silently stale, indistinguishable from "just ran clean."

`E.artifacts(workers=a.workers)` at **line 397** has the same shape: no try/except around the call itself (only the four per-label checks below it, lines 411-419, are individually guarded). A bug or an inaccessible file causing `estate.py` to raise anything other than its own per-file "bad" reporting takes down RECONCILE and the write the same way.

This is a real asymmetry within the file: `run_verifier()` (tier 2, lines 124-147) and the pyflakes subprocess call (tier LINT, lines 356-366) both correctly wrap their subprocess calls in `try/except subprocess.TimeoutExpired` / `except Exception`, matching the module's own stated purpose ("A defect nobody looked for is indistinguishable from a defect that is not there"). Tier 1 (IMPORT) and the ESTATE artifacts call do not, and are exactly the two entry points that would take the rest of the suite down with them.

### MINOR — `NEVER_RUN` set is defined and never consulted

**`allsweep.py:69-75`** defines a 30-module set documented as covering modules "whose no-argument run does real, expensive or mutating work" — but `grep` confirms it is referenced nowhere else in the file. Nothing in `check_import()`, `run_verifier()`, or `main()` reads it. It currently causes no harm only because `VERIFIERS` (the one place invocation actually happens) is a hand-curated static list that happens not to intersect badly with it — except it does contradict itself internally: `"silence"` is *in* `NEVER_RUN` (implying its bare run is unsafe/mutating) yet `VERIFIERS` explicitly invokes `silence.py` with no arguments (`("swallowed failures", ["silence.py"])`, line 80) as one of the read-only verifiers. Since `NEVER_RUN` is inert, this contradiction has no runtime effect, but it means the set can no longer be trusted as documentation either.

### Everything else checked and confirmed sound
- The `"undefined name" in ln or "local variable" in ln and "referenced before" in ln` LINT filter (line 362) relies on Python's `and`-before-`or` precedence, which happens to correctly implement "match `undefined name`, OR match `local variable` AND `referenced before`" — verified against pyflakes' actual `UndefinedLocal` message shape. Not a bug, but fragile: looks miswritten at a glance.
- `modules()` (line 93-95) globs `src/*.py` non-recursively — genuinely scans every module in `src/` (confirmed 95 files, none underscore-prefixed today), correctly excludes `src/deprecated/` (one file, intentionally out of scope).
- All the `[:6]`-style truncations inside `reconcile()`'s `note()` calls (`orphan_hosts[:6]`, `missing[:6]`, `stale[:6]`, `examples` capped at 6, `art["bad"][:25]`) only bound the **display string**; the paired `count`/`n` value is always the true, uncapped count, and `art["bad"] > 25"` explicitly prints "...and N more." These are legitimate summary-display bounds, not Hard Rule 0 violations.
- Every `subprocess.run` call passes `creationflags=_NO_WIN` (module-level `_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)`, line 50) — confirmed at all four call sites (lines 108, 133, 298, 359). No console-window leaks.

---

## ADDRESS_SPACE.PY

### MAJOR — the charted-tier fields have zero headroom and wrap silently instead of raising, unlike the hash-derived fields

`assign()` (**lines 240-261**) packs eight fields: four ("hyperverse", "xenoverse", "metaverse", "multiverse") come straight from `tiers` (the per-source charted stack, computed live by `tiers.chart()` and reloaded from `TIERS.json`); four ("universe", "galaxy", "star", "planet") are hashed from the designation string.

The charted fields go through `fit()` (**lines 251-252**):
```python
def fit(v, field):
    return (0 if v is None else int(v)) % (1 << WIDTHS[field])
```
— a **silent modulo wrap** on overflow. The hash-derived fields, by contrast, are bounds-checked by `pack()` (**lines 145-159**), which **raises `ValueError`** on any out-of-range value ("a silently wrapped address would name a different world, which is the one failure mode worth being loud about," line 148 comment) — but `fit()` runs *before* `pack()` sees the value, so `pack()` never gets the chance to catch an overflowing charted-tier index; it only ever sees the already-wrapped-safe result.

`WIDTHS` for the charted fields is sized by `_tier_counts()` (**lines 106-116**) to *exactly* `max(existing index) + 1`, read **once at module import**. Zero margin is left for the taxonomy growing afterward. `pipeline.py:phase_cosmology` (lines 1377-1447) is the live call path that can trigger this: it computes a **fresh** `charted = T.chart()` (line 1396) and writes a fresh `TIERS.json` (line 1400) in the *same phase*, before calling `AS.assign(desig, charted.get(src) or {})` (line 1442) — using the in-memory `charted` dict, not a reload of the file `address_space.py`'s `_TC` was computed from at its own import time. If the freshly-charted tier stack has grown past what `_TC`/`WIDTHS` captured when `address_space` was first imported (a newly-discovered multiverse/metaverse/xenoverse pushing the max index past the cached field width), the new tier's index silently aliases onto an existing lower tier via `fit()`'s modulo — two genuinely different multiverses would print the same `Mv.N` shelfmark segment, which is precisely the "collision makes citations ambiguous" failure this focus area asks about, and it would happen *without* necessarily showing up in the `dupes`/`"collisions"` count reported below (see next finding), because the other four (hash-derived) fields would very likely still differ.

### MINOR — the collision check is computed and printed, but never gates anything

Both `address_space.py:main()` (**line 332**: `print(f"   collisions       : {len(addrs) - len(set(addrs.values()))}")`) and `pipeline.py:phase_cosmology` (**line 1445-1446**: `dupes = len(marks) - len({v["address"] for v in marks.values()}); log("  addressed %d worlds, %d collision(s)" % (len(marks), dupes))`) honestly compute and log a real collision count. Neither place does anything with a nonzero result — no `sys.exit(1)`, no retry, no exclusion from the write. `SHELFMARKS.json` is written unconditionally in both places even when `dupes > 0`, so a genuine collision (however rare given the ~72-bit hash space against ~5,200 catalogued worlds) ships silently to disk as two ambiguous citations, with the only trace being a log line easy to miss in a scrolling batch run.

### MINOR — module docstring is stale: claims 74 bits / 5 fields, code is 8 fields / ~87-89 bits

The file's title (line 3, "A 74-BIT NAME FOR EVERY PLANET") and opening table (lines 26-27) describe a 5-field, 74-bit scheme (`hyperverse 3b | universe 5b | galaxy 38b | star 27b | planet 1b`). The code has since grown to 8 fields (`FIELDS`, lines 130-139: hyperverse, xenoverse, metaverse, multiverse, universe, galaxy, star, planet) — the "CORRECTED against Part Two" comment block right below it (lines 75-105) explicitly documents this evolution ("an earlier version of this module had five, silently omitting xenoverse, metaverse and multiverse"), but the header above it was never updated to match. `pipeline.py:1383` independently calls the real total "a real 89-bit address," confirming the header's "74-bit" figure is stale, not just imprecise. Separately, the header table's claim that `universe` is derived "from the 168 the catalogue resolved" (giving 24/hyperverse, 5 bits) doesn't match the actual code, which hardcodes `("universe", 1 << 6)` = 64 (**line 135**) — 6 bits, disconnected from `_continuities()`/168 entirely. Functionally harmless (`TOTAL_BITS`/`CAPACITY` are computed dynamically from the real `WIDTHS`, line 141-142, so the runtime capacity printout at lines 278-279 is correct), but misleading to anyone reasoning about collision margins from the docstring alone.

### Everything else checked and confirmed sound
- `pack()`/`unpack()` round-trip is exact (keyword-only call convention, enforced by the header comment at 284-289 documenting a prior positional-call bug that's now fixed).
- `assign()` itself is a pure function of `(designation, tiers)` with no shared mutable state — safe under concurrent/threaded callers, no lock needed.
- `_bits()` correctly floors at 1 bit via `max(2, n)` before `log2`, avoiding a 0-bit field for `n <= 1`.

---

## TUNING.PY

No correctness bugs found. This module reads as carefully hardened — several inline comments document and fix exactly the kind of defect this audit looks for (the `workers()` "0 is a request, not an absence" fix at lines 233-240 is a textbook example of catching and correctly fixing this class of bug). Two minor observations:

### QUESTION — `profile()`'s worker-count scaling bypasses `regime()`'s own throttle

`regime()` (lines 188-212) is explicitly throttled to re-checking the pool at most every `RECHECK_SECONDS` (180s) unless `force=True` — the module's stated design principle ("re-read on a timer... because it CHANGES underneath a long job"). But `profile()` (**lines 215-223**) calls `_answering_buckets()` a *second* time, unconditionally, on every call, to size `p["workers"] = max(4, min(16, n + 2))` — bypassing the same throttle that gates the "is this cloud at all" verdict. Within one 180s window, the cached `"cloud"` label can stay fixed while the worker count derived from the same underlying signal (`n`) drifts on every call. Low consequence (extra `POOL_PROOF.json` reads, not a wrong verdict), but inconsistent with the file's own stated caching rationale.

### QUESTION — unlocked module-level `_CACHE` dict under concurrent callers

`_CACHE` (line 104) is updated via `_CACHE.update(...)` (line 211) with no lock. `regime()`/`profile()`/`workers()` are called from threaded batch code elsewhere in the kit. A reader on another thread mid-update could theoretically observe a torn `(regime, why, at)` combination from two different generations. Consequence is cosmetic (a mismatched `why` string), not a wrong worker count or wrong file write, since `regime()` returns its freshly-computed local `r`, not a re-read of `_CACHE`.

---

## STYLE_AUDIT.PY

### MAJOR — `TURN_ENDING` regex overcounts "entries ending on a turn" because `re.M` makes `$` match every internal line break, not just the true end of the record

**`style_audit.py:38-39`**:
```python
TURN_ENDING = re.compile(
    r"(?:\.|\?)\s+(?:And|But|Yet|Still|Which|That)\b[^.]{0,80}\.\s*$", re.M)
```

`record_of()` (lines 48-51) extracts a multi-sentence, multi-paragraph "Record" block that routinely contains internal newlines (`.strip()` only trims the ends). With `re.M`, `$` matches before *every* `\n` in the string, not only at the true end of the record — and `[^.]` (a negated character class) matches newlines too, since it isn't scoped by `re.S`/`DOTALL`. So `TURN_ENDING.search(r)` returns a match whenever **any interior line** of the record happens to end on a turn-construction sentence, even when the record's actual final sentence does not. This inflates `turns`/`turn_rate` (used at **lines 128-129** and reported with a hard `"OVER (target <= 25%)"` threshold at **line 169**) — the metric silently counts records as "ending on a turn" that don't, in the exact direction that would make the tool cry wolf on entries that are actually fine, or dilute genuine over-threshold signal with noise. Fix: anchor against the true string end only (drop `re.M`, or use `\Z`).

### MINOR — `main()` never fails on its own findings; exit code is always 0 outside `--self-test`

The non-self-test path of `main()` (**lines 195-207**) always `return 0`, regardless of what `report()` prints — even when `banned` tells are wildly over threshold or `turn_rate`/`em_per_entry` are flagged `"OVER"`. This breaks the same convention `allsweep.py` documents for its own sibling verifiers ("`silence` and `audit` exit 1 when they HAVE findings — that is their contract, so a shell can gate on them," `allsweep.py:380-382`); `style_audit.py` has no such contract at all, human or automated. Combined with the `allsweep.py` finding above (this module is missing from `VERIFIERS`), style regressions currently have no automated detection path in this project at all — someone has to run this by hand and read stdout.

### MINOR — sentence-initial capitalization is indistinguishable from a proper name, in two places

`opener_shape()` (lines 59-86) collapses any capitalized non-function word into a `NAME` token — correctly fixing the multi-word-proper-noun bug the docstring describes, but a record opening with any ordinary word that's merely capitalized because it's sentence-initial ("Long before the war...", "Deep beneath the ruins...") also collapses to `NAME ...`, conflating genuinely different openings that only coincidentally start with a capital letter. The `vocab` Counter (**lines 130-132**) has the mirror problem: `not w[:1].isupper()` excludes capitalized words to avoid counting character names, but this also silently excludes any common word that happens to start a sentence somewhere in the corpus, systematically undercounting legitimate overused-vocabulary signal for exactly the words most likely to open a sentence (however, beneath, across, throughout, ...). Both are inherent to the lightweight heuristic rather than clear-cut bugs, but worth knowing as a source of false negatives/false positives in the reported numbers.

### Everything else checked and confirmed sound
- `entries()`'s `[◈◈]` character class duplicates the same glyph twice (functionally identical to `[◈]`) — confirmed against every real usage site (`generate.py`, `prompts/chapter_prompt.txt`, `prompts/system_style.txt`) that only ever a single "◈" marker is used in this project, so this is a harmless copy-paste artifact, not a missed-delimiter bug.
- The glob in `main()` (`**/*.md` + `**/*.txt`, recursive, lines 195-196) is genuinely uncapped — scans every generated file under `--path`, no Hard Rule 0 issue.
- `n = max(1, len(recs))` guards every rate computation against division by zero on an empty corpus.

---

## SCOPE.PY

### MAJOR — the no-signal fallback silently reintroduces the exact frequency bias the module's docstring says is wrong, in precisely the lowest-confidence cases the floor exists to protect

`scope_for()` (**lines 86-93**):
```python
best = None
for lab, _, band in _RE:
    if counts[lab] >= MIN_MENTIONS:
        best = (lab, band)
if best is None:                       # nothing clears it: fall back to the commonest tier
    lab = max(counts, key=counts.get)
    band = dict((l, b) for l, _, b in _RE)[lab]
    best = (lab, band) if counts[lab] else None
```

The main loop is correct and matches the docstring precisely — it walks tiers low-to-high and keeps overwriting `best`, so it lands on the *highest* tier clearing `MIN_MENTIONS = 10`, not the most frequent one (the docstring's own worked example: Marvel's 112 "planet" mentions vs. 61 "universe" mentions correctly resolves to universe, since both clear the floor and universe is higher).

But when **no** tier reaches the floor of 10, the fallback picks `max(counts, key=counts.get)` — literally the most frequent tier, with no floor at all (down to a single incidental mention, since the only guard is `counts[lab]` being nonzero). This is the exact behavior the docstring calls out as the mistake this module exists to avoid ("READING THE SIGNAL... Not by frequency," lines 25-30), reintroduced silently in exactly the population most vulnerable to it: thin wikis with sparse scope vocabulary are, per the module's own docstring, the *common* case ("203 of 211 sources carry `provisional_magnitude: unassayed`," line 12) — precisely the sources most likely to have every tier under 10 mentions and hit this branch. The resulting `ceiling` feeds directly into `magnitude.py:host_ceiling()` → `assay_entity(..., ceiling=...)`, which only ever clamps an anchor *downward* (`magnitude.py:661-662`). A ceiling set by one or two incidental "kingdom" mentions on a genuinely galaxy-scale fiction that only mentions "galaxy" once fewer would silently and permanently cap every entity from that source at M1, with no recourse — the opposite failure from the one the module was built to fix (Jace Beleren anchoring M10.77), but just as wrong.

### MINOR — `build(records, hosts)`: the `records` parameter is accepted and never used

**`scope.py:102-120`**. `records` does not appear anywhere in the function body; `todo` is derived purely from `hosts` (**line 106-107**: `{h for s, h in hosts.items() if h and h not in out and not F.is_wikipedia(h)}`). Called as `build(P.records(), hosts)` from `main()` (line 143) — the caller goes to the trouble of loading the full catalogue records and passing them in, for nothing. Two consequences: (1) `build()` will probe-and-scope hosts that have no catalogue record at all if they're still present in the host map, wasting live wiki-search calls; (2) more importantly, `build()` only *adds* to the existing on-disk `SCOPE.json` (`out = json.load(...)` then `out[h] = sc` for new entries) and never removes an entry for a source that's since been purged from `records` — unlike the parallel pattern `allsweep.py`'s `reconcile()` explicitly checks for other data types via `ROSTER_PURGES.json` ("purged rosters must be gone from the records, not merely marked," `allsweep.py:228-239`). `SCOPE.json` has no equivalent check anywhere, and `scope.py` itself is the one place positioned to have prevented the staleness in the first place.

### MINOR — `titles[:8]` caps the pages that feed the scope signal that becomes a hard per-host ceiling

**`scope.py:81`**: `pages = F.fetch(host, titles[:8])`. Up to 4 queries × `srlimit=3` (line 74, a legitimate ranked-search bound — MediaWiki's own top-N relevance search, not a truncation of an ordered catalogue) can surface up to 12 distinct candidate titles, silently cut to the first 8 before fetching full text. Given the resulting `counts` dict directly determines a ceiling that hard-clamps every entity assayed against that host (see finding above), discarding up to a third of the candidate pages is worth flagging for classification even though it's more defensible than a raw content-listing cap — it bounds a *signal-detection probe*, not the permanent catalogue itself. Recommend either dropping the slice (uncapped `F.fetch(host, titles)`) or documenting explicitly why 8 is sufficient.

### MINOR — dead function, duplicated logic

`ceiling_for()` (**lines 123-130**) is never called anywhere in the codebase (confirmed by grep — `scope.py` is the only file that references the name). `magnitude.py`'s `host_ceiling()` (magnitude.py:854-882) independently reimplements the same "read `SCOPE.json`, look up by host, fall back to a live `scope_for()` call" logic instead of calling this function. Not a bug on its own, but the intended access point went unused while its logic was duplicated elsewhere.

### QUESTION — M5 ("star clusters") has no keyword tier at all

`TIERS` (lines 52-61) jumps directly from `"star system"` (M4) to `"galaxy"` (M6) — there is no tier keyed to the charter's own M5 rung ("star clusters," per `magnitude.py`'s SYSTEM prompt ladder, line 277). A fiction whose largest evidenced scope is genuinely cluster-scale has no matching keyword bucket and will land on whichever of M4/M6 has matching vocabulary, over- or under-shooting the true ceiling by one full rung. Likely an intentional simplification (M5-M10 share the same `(30, 30)` instrument window in `assay.py:INSTRUMENT_WINDOWS`, suggesting this range is less load-bearing already) rather than an oversight, but flagged for the owner to confirm.

### Everything else checked and confirmed sound
- `scope_for()`'s main tier-selection loop is correct (see above).
- `build()` correctly wraps each host's `scope_for()` call in try/except (lines 109-113), so a single host's live-wiki failure can't take down the batch — consistent with the module's role as a batch probe.
- `ceiling_for()`, despite being dead, is itself logically sound.
