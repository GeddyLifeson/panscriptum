# Sweep #28 — Batch 15 Audit

Modules: `src/assay.py` (649L), `src/derivation.py` (559L), `src/rosetta.py` (417L),
`src/address.py` (291L), `src/genre.py` (248L), `src/descending_ladder.py` (187L),
`src/catalog.py` (128L). Total 2,473 lines (wc -l), every line read.

`NEXT_STEPS.md` §3 and the owner-ruling list read first; findings cross-checked against it and
marked KNOWN/NEW accordingly.

---

## SPECIAL FOCUS #1 — `assay.py:302-322` `_SCALE` rescale (KNOWN, confirmed with numbers)

**Verdict: confirmed exactly as flagged in `NEXT_STEPS.md` item 1.5. STILL OPEN.**

```python
SIGMA_MAX = 9.9 / (12 ** 0.5)                       # = 2.8579  (line 302)
_RAW_SIGMA = {
    "Instrumented": 2.70, "Witnessed": 4.08, "Transcribed": 5.30,
    "Reconstructed": 7.00, "Disputed": 8.50,
}
_SCALE = SIGMA_MAX / max(_RAW_SIGMA.values())        # = 2.8579 / 8.50 = 0.33622   (line 315)
SIGMA_BY_ATTESTATION = {k: round(v * _SCALE, 4) for k, v in _RAW_SIGMA.items()}  # line 316
```

The adjacent comment (lines 274-300) states the raw `Witnessed` value 4.08 was **solved for**
to reproduce the charter's own published Kenshiro interval, M3.52 ± 0.12. That calibration is
real — I reproduced it directly (see below). But `_SCALE` then multiplies *every* raw sigma,
including the calibrated 4.08, by `SIGMA_MAX / 8.50 = 0.3362` so that the *worst* grade
(`Disputed`, 8.50) lands exactly on the ignorance ceiling. This discards the calibration: the
sigma actually used for `Witnessed` at runtime is `1.3718`, not `4.08`.

Numeric proof, run directly against the module (`src/assay.py`), reproducing Kenshiro's own
shape (eight physical Measures scored, three faculties unscored, attestation `Witnessed`,
single hand, anchor `M3`):

```
SIGMA_BY_ATTESTATION['Witnessed'] = 1.3718        (rescaled value actually used)
assay(anchor='M3', ..., attestation='Witnessed')  -> interval = 0.06

Manually substituting the RAW calibrated 4.08 back into the same propagation (ignorance term
still capped at SIGMA_MAX for the 3 unscored faculties, matching how the code caps it):
                                                    -> interval = 0.12   (exact charter match)
```

**What is lost:** the calibration that ties the published interval math to the charter's own
Kenshiro figure. **What depends on it:** every printed `± interval` for every entity assayed
under `Witnessed` (and, proportionally, every other grade) — the module's own comment claims
the interval "reproduces" the charter's calibration point, but the rescale silently halves it
(0.06 vs the charter's 0.12) for the exact worked example the comment cites. This is the
`NEXT_STEPS.md` item 5 finding ("STILL OPEN... discards the raw sigma..."), now confirmed with
an exact before/after number rather than by inspection alone.

Related, same file: `axis_score()` (lines 211-229) still returns a **flat 9.9** for any `x` at
the top rung (`band == "M10"`, `i + 1 >= len(LADDER)` at line 222-223) regardless of the actual
feat magnitude — this is `NEXT_STEPS.md` item 4 ("M18, CONFIRMED A FOURTH TIME"), re-confirmed
unchanged at source this run. KNOWN, STILL OPEN.

---

## SPECIAL FOCUS #2 — `genre.py:135,182,187` `most_common(top=3)` (KNOWN, confirmed numerically)

**Verdict: confirmed exactly as flagged in `NEXT_STEPS.md` §3. STILL OPEN. Confidence IS
inflated, and I measured the size of the inflation.**

```python
def classify_text(text, top=3):                 # line 135
    scores = collections.Counter()
    for g, spec in GENRES.items():               # 10 genres total in GENRES
        for pat, w in spec["cues"].items():
            scores[g] += w * len(re.findall(pat, text, re.I))
    return scores.most_common(top)                # <-- truncates to top 3 of 10

def classify_source(rec, cap=None):
    ...
    ranked = classify_text(" ".join(parts))       # line 182 — only 3 genres survive
    ...
    total = sum(s for _, s in ranked) or 1        # line 187 — sums only those 3, not all 10
    return {..., "confidence": round(score / total, 3), ..., "runners_up": ranked[1:], ...}
```

Both halves of the claim are real: (a) `ranked` (and therefore the persisted `runners_up` field
in `data/GENRES.json`) only ever holds up to 3 of the 10 genres, silently hiding any signal in
the other 7; (b) `total`, the confidence **denominator**, is summed only over those surviving 3
— not over all-genre scores — so `confidence` is `top / (top3 sum)` rather than the honest
`top / (all-genre sum)`.

Numeric proof, run directly against `src/genre.py` on a synthetic mixed-genre text (deliberately
straddling 5 genres with real cue hits):

```
FULL per-genre scores : high_fantasy 46, cyberpunk 40, mythology 39, post_apocalyptic 36,
                         space_opera 33, grimdark 4, military_modern 1  (sum = 199)
TRUE confidence (top / ALL 7 nonzero genres)  = 46/199 = 0.231
CODE confidence (top / top-3-sum, i.e. 46+40+39=125) = 46/125 = 0.368
```

**0.368 vs the true 0.231 — a 59% inflation** (ratio 1.59x) purely from truncating the
denominator before summing. The module's own `main()` treats `confidence < 0.45` as "genuinely
mixed, flagged not forced" (line 218) — an inflation of this size can readily carry a genuinely
mixed source (true confidence in the high-0.20s to low-0.40s) across that 0.45 line, so it is
silently classified with high confidence instead of being flagged for review, and the wrong
`register`/`priors` (used by `onomast.py`/`worldseed.py` downstream) get asserted as settled.
The sibling `cap` parameter in the same function (lines 173-177) was already hardened to raise
`SystemExit` rather than silently truncate — this `top=3` cap is the still-open twin of that
already-fixed pattern, exactly as `NEXT_STEPS.md` states.

---

## `assay.py` — other findings

### KNOWN — `axis_score()` flat 9.9 at M10 (lines 219-223)
Severity: HIGH. See Special Focus #1 above. Unchanged, `NEXT_STEPS.md` item 4.

### KNOWN — `_SCALE` rescale (lines 302-322)
Severity: HIGH. See Special Focus #1 above. `NEXT_STEPS.md` item 5.

### LOW — dead branch in `instrument()` (line 503)
```python
grade_n = max(0, LADDER.index(anchor) - 5)
grade = ["", "I", "II", "III", "IV", "V"][grade_n] if grade_n <= 5 else "V"
```
`LADDER` has 11 entries (`M0`..`M10`), so `grade_n` can never exceed 5 (`10-5=5`); the `else
"V"` branch is unreachable given the current `LADDER`. Harmless today, but silently stops being
harmless the moment `LADDER` grows past `M10` without this line being revisited — nothing here
would fail loudly, it would just start indexing the list correctly by luck rather than by
guarantee. Not urgent.

### LOW — `axis_score()`/`band_for_quantity()` treat a literal `0` band-edge as missing
`if not lo or not hi:` (line 226) and `BAND_EDGES[b].get(axis, math.inf)` (line 246) both use
falsy/default checks that would silently misbehave if a future band edge were legitimately `0`
rather than absent. No current table entry is `0`, so this is not live, but it is the same shape
of fragility flagged in HANDOFF for other modules. Speculative / not currently triggered.

---

## `derivation.py` — findings

The ledger graph itself is clean: `check_graph()` run directly returns **0 problems** (no
dangling parents, no rootless derivations, no cycles) against the current `LEDGER` dict of ~100
entries.

### NEW — LOW/MED — `main()`'s "deepest derivation chains" print is capped to 6 (line 534)
```python
for n in sorted(LEDGER, key=lambda x: -depth(x))[:6]:
```
This is a `[:N]` cap on a diagnostic listing, the exact shape lesson 16 in `NEXT_STEPS.md` calls
out ("a cap on a diagnostic hides the pattern, not just the rows"). It only affects the
`main()`/CLI report's visibility (the underlying `LEDGER` and `depth()`/`provenance()` are not
truncated, so `python derivation.py` alone would hide any quantity beyond the 6 deepest chains
from the reviewer reading this specific report section — e.g. if two different quantities tie
for "deepest," only 6 of an arbitrary number get shown, with no "...and N more" disclosure).
Low real-world impact (this is a human-facing summary, not data written to disk), but it is
exactly the shape the project has flagged as a Hard Rule 0 violation elsewhere.

### Note — `scan_constants()` only catches `ast.Assign`, not `ast.AnnAssign`
Line 494 `if isinstance(node, ast.Assign):` — a module using an annotated module-level constant
(`FOO: int = 3`) would not be picked up by the "where constants live" scan. The function's own
docstring/comment self-describes as "a reviewer's map, not a verdict," so this is disclosed as
non-exhaustive rather than a false guarantee — flagging as LOW/informational, not a bug per se.

---

## `rosetta.py` — findings

### NEW — HIGH — `--check`'s Assay value silently discards the magnitude/band, comparing decimal fraction only (line 402)
```python
assays = {k: v["result"]["decimal"] + P.__dict__.get("_x", 0)
          for k, v in json.load(open(path, encoding="utf-8")).items()
          if v.get("result") and v["result"].get("decimal") is not None}
```
`pipeline` (imported as `P`) has no module attribute `_x` anywhere in the codebase (confirmed by
grep across `src/`) — `P.__dict__.get("_x", 0)` always evaluates to `0`. So this line is exactly
`v["result"]["decimal"]`: only the **within-band fractional decimal** (0.00–0.99), never
combined with `v["result"]["magnitude"]` (the M-band, `"M0"`–`"M10"`, also present on every
`ASSAYS.json` result record written by `magnitude.py`). The correct full-scale value would be
`assay.LADDER.index(magnitude) + decimal`.

This is the entire point of `rosetta.py`'s `check()`: correlate a franchise's own published
ordering (bounties, power levels) against **our Assay's ordering**, and flag disagreement
(`rho < 0.3`, line 406). With the magnitude stripped, two entities in *different* M-bands are
compared purely on their fractional position within their own band, which is guaranteed to
scramble any comparison that crosses a band boundary — extremely common for any franchise whose
cast spans multiple magnitude tiers (which is precisely the interesting/large-N case this module
exists to validate).

Concrete failure scenario: entity A assayed at M2.10, entity B at M9.05 (B genuinely far
stronger and so ranked by the native scale). `check()`'s Spearman input uses A=0.10, B=0.05 —
**A now outranks B** in the correlation input, though the true Assay values (2.10 vs 9.05) and
the native scale both say the opposite. Any franchise whose characters span multiple bands (One
Piece, Dragon Ball — exactly the two the module's own docstring names as canonical large-N
ground truth) will have this noise injected into every `rho`, and the `DISAGREES` flag this
module exists to raise becomes essentially meaningless — a franchise could DISAGREE purely
because its cast spans bands, with zero information about whether the Assay's actual ordering is
right.

### NEW — MED/HIGH — `_STAND` regex is dead code; comment claims it parses Stand statistics, but nothing calls it (lines 90-92, 104-105)
```python
# ... Stand stats are read from their parameter block instead (see _STAND).
_STAND = re.compile(
    r"\b(power|speed|range|durability|precision|potential)\s*[:=|]\s*([A-E])\b", re.I)
```
`_STAND` is assigned once and never referenced again anywhere in the file (grep confirms — no
`_STAND.findall`/`.search`/`.match` call exists in `numeric_rows()`, `ordinal_rows()`, or
`scales_for()`, the only functions that parse wikitext). The comment at lines 90-92 explicitly
claims this problem ("Stand stats… read from their parameter block") is solved by `_STAND`, but
the solution is never wired in. Net effect: JoJo's Bizarre Adventure Stand statistics (Power/
Speed/Range/Durability/Precision/Potential, A–E grades) — one of the franchises the module's own
top-of-file docstring names by example ("Stand statistics… onto the Assay") — are never actually
mined by this module. This is a comment-contradicts-code finding (lens item 6): the comment
reads as a guarantee that a real bug class was fixed, and the fix was never connected.

### NEW — MED — `srlimit: "5"` with no continuation, for every scale-name search (line 194)
```python
d = F.api(host, {"action": "query", "list": "search", "srlimit": "5", "srsearch": q})
```
Run once per host per entry in `SCALE_QUERIES` (28 query strings, e.g. `"power level"`,
`"bounty list"`, `"curse grade"`...), with no `sroffset`/continuation handling — only the first 5
search hits per query are ever considered, and any relevant page ranked 6th or later (e.g. a
wiki that splits its bounty table across multiple "List of Bounties (Part 2)" pages, or has
several distinct scale pages that a single query legitimately surfaces beyond position 5) is
silently invisible to the miner. This is the same shape Hard Rule 0 explicitly calls out
(`srlimit`/`aplimit` without continuation) and the same class already recorded for `feats.py:
348-361` (`aplimit=500`/`srlimit=50`, m82) — but this instance in `rosetta.py` is not listed
anywhere in `NEXT_STEPS.md` or `HANDOFF.md`, and is considerably tighter (5 vs 50).

### NEW — LOW/MED (speculative) — outlier filter in `numeric_rows()` can drop legitimate top-of-distribution entries with no logging (lines 166-171)
```python
if len(out) >= 8:
    med = sorted(out.values())[len(out) // 2]
    out = {k: v for k, v in out.items() if v <= med * 1000}
```
Any parsed value more than 1000x the median is dropped as a presumed parse artefact. Native
scales the module targets (bounties, power levels) are canonically heavy-tailed — the docstring
of `refine()` (lines 317-321) itself notes "One Piece's bounties span six orders [of
magnitude]." A heavy-tailed distribution with a low median (many minor characters) and one or
two genuinely enormous top values (the protagonist/final antagonist) is exactly the shape this
filter is most likely to clip — silently, with no count of how many rows were dropped logged
anywhere (contrast with `refine()`, which does track and print `kept`/`dropped`). I have not
proven this fires on real wiki data in this session (would require a live `--mine` run against a
real wiki), so this is flagged as a plausible, unverified risk rather than a confirmed defect —
but the mechanism is real and undisclosed either way.

### NEW — LOW — diagnostic-only truncation in CLI output (lines 343, 391)
`--probe`: `top = sorted(...)[:6]` (preview of top 6 values only). `--refine`: prints only the
top 12 hosts by row count (`[:12]`, line 391). Neither affects the on-disk `ROSETTA.json` (the
full `out`/`keep_scales` dict is written whole in both paths) — console-only, but the same
"cap on a diagnostic" shape lesson 16 warns about.

---

## `address.py` — findings

No correctness bugs confirmed live. Notes:

### LOW (speculative, not reproduced against real data) — inconsistent tie-break between fallback tiers in `spine_code_for()`
The word-padded containment fallback (lines 94-99) returns the **first** matching entry in
`codes.items()` iteration order with no preference for exactness or length, whereas the
token-overlap fallback one tier down (lines 102-114) explicitly tracks and returns the
**best**-overlap match. I tested this directly against the live `data/CHARTER_SPINE_CODES.json`
(219 entries): running every entry's word-padded form against every other entry's, the only
containment collision found was a duplicate encoding-variant pair that both resolve to the same
code (`II.E`, a mojibake `—`→`�` artifact in one of the two strings, itself worth a data-quality
note but out of scope for source review). So this asymmetry is not currently exploitable against
the appendix as it stands; flagged only because a future addition to the appendix (e.g. two
entries where one's normalized name is a short prefix of another's, as demonstrated abstractly
with "Black" vs "Black Ops"/"Black Clover") would silently pick whichever happens to sort first
in the JSON, with no signal to the owner (unlike `UNASSIGNED`, which is designed to surface for
review).

---

## `genre.py` — other findings

### KNOWN — `most_common(top=3)` confidence-denominator inflation (lines 135, 182, 187)
Severity: HIGH. See Special Focus #2 above. `NEXT_STEPS.md` §3, "sibling cap already fixed in
the same file" (referring to the hardened `cap=` parameter at lines 173-177, confirmed present
and still raising `SystemExit` as documented).

### NEW — LOW — diagnostic caps in `main()` (lines 220-222)
```python
for s, v in low[:5]:
    ru = ", ".join(f"{g}:{n}" for g, n in v["runners_up"][:2])
```
Console-only: the low-confidence list is capped to 5 rows (no "...and N more"), and each row's
runners-up preview capped to 2. Doesn't affect `data/GENRES.json` (written whole via
`silence.write_json`, confirmed atomic per the comment at lines 237-240), but hides the true
count of low-confidence/genuinely-mixed sources from anyone reading the `main()` report only.

---

## `descending_ladder.py` — findings

### NEW — HIGH — `rung_for_length()`'s Planck rung (-14) is unreachable for any non-exact-equality input; the entire quark-confinement-to-Planck gap (17 orders of magnitude) is misclassified (lines 85-95)
```python
def rung_for_length(metres):
    if metres <= 0:
        return None, None
    if metres < PLANCK_LENGTH:
        return FOLD_RUNG, "Below the Fold"
    best = DESCENDING[0]
    for r in DESCENDING:
        if metres <= r[3]:
            best = r
    return best[0], best[2]
```
`DESCENDING`'s last row is `(-14, "Pk", "Planck", PLANCK_LENGTH, PLANCK_ENERGY)` — its length
threshold IS `PLANCK_LENGTH` itself. The guard above diverts any `metres < PLANCK_LENGTH`
straight to `FOLD_RUNG` (-15) before the loop runs at all. So the loop can only ever assign rung
-14 when `metres` is neither `< PLANCK_LENGTH` (caught by the guard) nor `> PLANCK_LENGTH`
(fails the loop's own `metres <= PLANCK_LENGTH` test for that row) — i.e. only at
floating-point-exact `metres == PLANCK_LENGTH`. Any size even one ULP smaller skips straight to
"Below the Fold"; nothing routes to "Planck" as a genuine bracket.

Verified directly by running the function:
```
1.000000e-18  -> rung -13  Quark-confinement
1.000000e-20  -> rung -13  Quark-confinement
1.000000e-25  -> rung -13  Quark-confinement
1.000000e-30  -> rung -13  Quark-confinement
1.000000e-34  -> rung -13  Quark-confinement
1.616255e-35  -> rung -13  Quark-confinement   (this literal float is slightly ABOVE PLANCK_LENGTH
                                                 due to the *1.0000001 fuzz in the test)
1.616255e-35  -> rung -14  Planck              (bit-exact PLANCK_LENGTH only)
1.616255e-35  -> rung -15  Below the Fold      (one ULP below PLANCK_LENGTH)
1.000000e-36  -> rung -15  Below the Fold
```
Every tested size from `1e-18` m down to just above `PLANCK_LENGTH` — the entire 17-order-of-
magnitude span the "Quark-confinement" rung is supposed to share with "Planck" — reports
"Quark-confinement." The module's own docstring (lines 18-22) describes extending the Ladder
downward by **fifteen** rungs specifically "to the Planck length"; in practice, rung -14 is
dead weight in the table (still present in `rung_table()`'s dict output, just never returned by
the actual classifier), and any descent that should land "at the Planck scale" is either
misreported as quark-confinement-scale or over-reported as already past the Fold. This
propagates directly into `shrink_report()`'s `target_rung`/`target_rung_name` fields (line 134),
which call `rung_for_length(to_m)` and would carry the same misclassification into any consumer
of that report.

Not listed in `NEXT_STEPS.md` or `HANDOFF.md` under this name (a prior, unrelated, and already-
refuted `compton_confinement_energy` finding exists in `HANDOFF.md:2165` — confirmed still
correct at lines 100-114 this run, distinct from this bug).

---

## `catalog.py` — findings

No correctness bugs found. This is a small read-only query CLI (`stats`/`search`/`address`/
`read`). `cmd_stats`'s `missing[:30]` display cap (line 64) explicitly discloses the omitted
count (`"... and N more"`, line 66-67) — the Hard-Rule-0-compliant way to truncate a console
listing, not a violation. `cmd_search` prints every match with no cap. No writes anywhere in the
module (pure reader), so the two-writer contract does not apply.

---

## Summary table

| Severity | Status | Location | Claim |
|---|---|---|---|
| HIGH | KNOWN | `assay.py:302-322` | `_SCALE` rescale discards the calibrated Witnessed sigma (4.08→1.3718); Kenshiro-shaped interval now computes 0.06 vs the charter's published 0.12 |
| HIGH | KNOWN | `assay.py:219-223` | `axis_score()` returns flat `9.9` for any input at M10, regardless of magnitude |
| HIGH | NEW | `rosetta.py:402` | `--check`'s assay value uses only the decimal fraction (`P.__dict__.get("_x",0)` is always 0), discarding the M-band entirely — cross-band comparisons are scrambled |
| HIGH | KNOWN | `genre.py:135,182,187` | `most_common(top=3)` truncates ranked genres AND the confidence denominator; measured 0.368 vs true 0.231 (59% inflation) on a synthetic mixed-genre text |
| HIGH | NEW | `descending_ladder.py:85-95` | `rung_for_length()` — the "Planck" rung is unreachable except at bit-exact equality; the entire 1e-18→Planck-length gap reports "Quark-confinement" instead |
| MED/HIGH | NEW | `rosetta.py:90-92,104-105` | `_STAND` regex, commented as the fix for Stand-statistic parsing, is dead code — never called; JoJo Stand stats are never mined |
| MED | NEW | `rosetta.py:194` | `srlimit: "5"`, no continuation, across 28 scale-name queries per wiki — Hard Rule 0 cap |
| LOW/MED | NEW | `rosetta.py:166-171` | outlier filter drops values >1000x median with no logging; plausible risk against heavy-tailed native scales, unverified against live data |
| LOW/MED | NEW | `derivation.py:534` | `main()`'s "deepest derivation chains" report capped to 6 rows, no disclosure of the rest |
| LOW | NEW | `rosetta.py:343,391` | diagnostic-only `[:6]`/`[:12]` caps in `--probe`/`--refine` console output |
| LOW | NEW | `genre.py:220-222` | diagnostic-only `[:5]`/`[:2]` caps in `main()` console output |
| LOW | NEW (speculative) | `address.py:94-99` | word-padded containment fallback picks first match, not best; no live collision found in current 219-entry appendix |
| LOW | — | `assay.py:503` | dead `else "V"` branch in `instrument()`, unreachable given current `LADDER` length |

batch15: 7 modules, 2473 lines read, 5 high, 3 med, 5 low, report at handoff/sweep28/AUDIT_batch15.md
