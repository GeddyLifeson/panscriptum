# AUDIT — Batch 15 (run29)

Modules: `src/assay.py`, `src/derivation.py`, `src/rosetta.py`, `src/address.py`,
`src/genre.py`, `src/descending_ladder.py`, `src/physics.py`

Every line of every module was read. Per instructions, three items already flagged by the
supervisor are **not re-derived** here: `assay._SCALE` discarding the charter-calibrated sigma
(measured 0.06 vs charter's published 0.12); `rosetta.py:402`'s `--check` comparing only the
decimal fraction; `descending_ladder.py:85-95`'s unreachable Planck rung (confirmed again below
only because a NEW, related finding — the module's total disconnection from the pipeline — sits
right next to it and needed the same reproduction harness); and `genre.py:135,182,187`'s
truncation of ranked genres / confidence denominator (also reproduced below for completeness,
since the reproduction directly informed a second, unflagged bug in the same cue table).

---

## src/genre.py

### FINDING G1 — HIGH — cue regexes over-match ordinary English words via unconstrained `\w*` after short stems
**Lines:** 69 (`grimdark`), 89 (`cyberpunk`), 104 (`military_modern`), 118 (`eastern`)
**Status: REPRODUCED**

`classify_text` scores a genre cue as `w * len(re.findall(pat, text, re.I))`, and several cue
alternations are `\b(...)\w*` where one of the alternatives is a short common-English stem. The
trailing `\w*` is unanchored on the right, so the pattern matches any longer word that happens to
begin with the stem, not just inflections of the intended term:

- `military_modern`, line 104: `r"\b(soldier|war|army|weapon|mission|combat)\w*"` — `war` matches
  `warm`, `ward`, `wardrobe`, `warmly`, `warn`, etc.
- `grimdark`, line 69: `r"\b(demon|hell|undead|necro|plague|curse|dread)\w*"` — `hell` matches
  `hello`.
- `cyberpunk`, line 89: `r"\b(cyber|netrunner|megacorp|implant|augment|neural|hacker|corpo|neon|
  chrome|black ?ice)\w*"` — `corpo` matches `Corporal` (a military rank!), `corporate`,
  `corporation`.
- `eastern`, line 118: `r"\b(ninja|sword saint|clan|honor|spirit)\w*"` — `clan` matches
  `clandestine`.

Reproduced end-to-end through `genre.classify_text`:

```
text = "The warm summer afternoon left her ward feeling warmly welcomed near the wardrobe."
genre.classify_text(text) -> [('military_modern', 4), ('mythology', 0), ('high_fantasy', 0)]
```

A sentence with zero military content scores `military_modern` purely from `warm`/`ward`/
`wardrobe`. Likewise:

```
"She waved and said hello to her friend..." -> grimdark scores 2 (from "hello")
"...led his platoon...corporate boardroom...corporation papers." -> cyberpunk scores 14,
    driven by "Corporal" + "corporate" + "corporation" all matching the `corpo` stem
    (with "corporation" double-counted a second time by the cyberpunk weight-2 group too)
```

**Consequence:** `classify_source` (the function that decides a whole source's `register` and
world-generation `priors` — the entire stated purpose of this module, replacing the old
hash-based register assignment) is built on `classify_text`. Because these stems are common
across ordinary prose (any dialogue with "hello", any description of weather with "warm", any
rank list with "Corporal"), the score pollution is not confined to edge cases — it is present in
essentially every source's text, silently pushing genre scores (and therefore register and world
priors) toward `military_modern`/`grimdark`/`cyberpunk`/`eastern` regardless of actual content.
Because the whole corpus is scored the same way, sources that are borderline between two genres
are the ones most likely to be pushed to the wrong side by this noise — which is exactly the
population `confidence` is supposed to protect (see G2), and G2's own denominator bug means the
false confidence from this noise is *additionally* inflated.

This is a correctness bug, not a truncation, but it directly undermines the fix this module's own
docstring claims to have made (mis-registered sources like the Alien/Doom/Cowboy-Bebop/Pantheon
cases the header calls out).

### FINDING G2 — KNOWN (confirmed via reproduction, not counted as new) — `classify_text`'s `most_common(top=3)` truncates the confidence denominator
**Lines:** 135 (`classify_text` signature/`most_common(top)`), 182 (`ranked = classify_text(...)`),
187 (`total = sum(s for _, s in ranked) or 1`)
**Status: REPRODUCED (already flagged by supervisor — not claimed as a new finding)**

`classify_text` computes a real score for **all 11** genres (the nested loop always executes
`scores[g] += ...` for every genre, so every genre gets an entry in the `Counter`, including
zeros), then truncates to the top 3 via `most_common(3)`. `classify_source` then computes
`confidence = score / total` where `total` is `sum` over only those 3 returned entries — genres
ranked 4th and below (which can carry real, nonzero signal) are excluded from the denominator,
inflating the reported confidence.

Reproduced:
```
text scored 'mythology':69 'high_fantasy':60 'grimdark':48 'space_opera':24 'cyberpunk':16
    'post_apocalyptic':16 'military_modern':3  (true total 236)
classify_text(text, top=3) -> [('mythology',69), ('high_fantasy',60), ('grimdark',48)]  (sums to 177)
confidence as computed by classify_source: 69/177 = 0.39
confidence against the TRUE total:         69/236 = 0.292
```
A ~10-point confidence inflation in this example; worse whenever more than 3 genres carry signal
(which G1's over-matching makes more likely, since a false-positive stem hit from an unrelated
genre now routinely adds a 4th/5th/6th nonzero score that gets dropped from the denominator).

### Swallowed failures / two-writer / concurrency — genre.py
- `main()`'s `--write` path uses `silence.write_json(p, out, ...)` (line 241) — correct, atomic,
  compliant with the two-writer contract (this is a shared `data/` file, not a per-record write).
- No bare `except: pass` in this module.

### Checks that cannot fail — genre.py
None found; `classify_source` correctly refuses a numeric `cap` (raises `SystemExit`) rather than
silently accepting one — this is a real, working guard, not a tautology.

---

## src/rosetta.py

### FINDING R1 — MEDIUM-HIGH — `srlimit=5` caps every wiki search query, a DATA truncation of the mined scale corpus
**Line:** 194 — `d = F.api(host, {"action": "query", "list": "search", "srlimit": "5", "srsearch": q})`
**Status: VERIFIED-BY-READING** (network access to live wikis not exercised in this session)

`scales_for` is documented as finding "every native scale this wiki publishes." It runs 24
different `SCALE_QUERIES` search terms per wiki, but each individual MediaWiki search call is
capped to `srlimit=5` — only the top 5 relevance-ranked results per query text are ever examined
for a scale-page hit (filtered further by `_SCALE_TITLE`/size >= 1500). If a wiki hosts more than
5 pages that plausibly match one query phrase (e.g. multiple "list of power levels" sub-pages, or
several bounty-list pages for different arcs/sagas), everything past the 5th is invisible to the
miner, and this silently shrinks the corpus written to `data/ROSETTA.json` — a DATA truncation,
not a display one, since the mined result feeds directly into `--mine`'s `out[host] = sc` write.
This is exactly the `srlimit=`-shaped cap Hard Rule 0 names explicitly. The per-query breadth (24
query strings) mitigates but does not eliminate the risk — a wiki whose scale pages are all
returned under one query phrase is still capped at 5 of them.

### FINDING R2 — LOW — dead no-op expression in the `--check` assay-loading line
**Line:** 402 — `assays = {k: v["result"]["decimal"] + P.__dict__.get("_x", 0) ...}`
**Status: REPRODUCED** (confirmed by grep: `pipeline.py` defines no `_x` attribute anywhere)

This sits directly on the already-known bug (comparing only the decimal fraction, never the
magnitude/band). The `+ P.__dict__.get("_x", 0)` term is dead code — `pipeline` has no module
attribute `_x`, so this always adds `0` and does nothing. It reads like an abandoned attempt to
patch in the missing magnitude term (e.g. `P.__dict__.get("_x", 0)` was perhaps meant to reach for
`LADDER.index(anchor)` via some helper) that was never finished and never removed. Worth flagging
alongside R-known because a maintainer skimming this line could mistake it for the fix already
being present.

### Swallowed failures / concurrency — rosetta.py
- `--mine` and `--refine` both correctly use `silence.write_json` with an explicit failure check
  (`if not silence.write_json(...): print(...); return 1`) rather than assuming success — good,
  no swallowed failure here.
- `numeric_rows`'s `offer()` catches `ValueError` from `float(raw...)` narrowly and calls
  `silence.note("rosetta.py:136")` rather than passing silently — acceptable, narrowly scoped,
  and recorded rather than swallowed.
- The `_BAD_CHARS` guard (lines 47-56) duplicates the identical block in `assay.py` and
  `physics.py` verbatim; not a bug, just triplicated boilerplate worth a shared helper someday —
  not flagging as a defect.

### Checks that cannot fail — rosetta.py
None found.

---

## src/address.py

### FINDING A1 — LOW — `slugify`'s 60-character cap can collide two distinct long category labels into the identical address slug
**Line:** 127 — `return "".join(p[:1].upper() + p[1:] for p in parts)[:60]`
**Status: REPRODUCED**

```
slugify("A"*60 + " Alpha Category Distinct Tail One") == slugify("A"*60 + " Beta Category Distinct Tail Two")
-> both truncate to the identical 60 "A" characters
```
`slugify` is the fallback used by `chapter_slug()` only when a `category_label` is **not** one of
the 9 known keys in `CHAPTER_SLUGS` (line 179). In current practice the entrypass classifier only
ever emits those 9 known labels, so this path is not exercised by the live pipeline today — but
it is exactly the kind of silent-collision hazard that would corrupt `build_address()` outputs
(two different unknown-category sources landing on the identical `<SpineCode>/<Chapter>` address,
each overwriting or being confused with the other) the day a 10th category label with a >60-char
shared prefix is introduced. Low severity given it's presently dead-path, but worth a note rather
than a truncation to a hash or a longer cap.

### Reviewed, no defect found
- `spine_code_for`'s four-stage fallback (exact code, letter-normalized equality, word-padded
  containment, token-overlap ≥0.8) is carefully commented with the history of two real bugs it
  already fixed (the "dc" mis-match, the equality-vs-containment regression) and reads correctly
  on inspection; the containment stage pads with spaces specifically to avoid the earlier
  substring hazard.
- `tier_for` / `tier_rank` / `promote`: correct monotone-floor logic; `promote` is
  promotion-only by explicit design and comment, matches its own doc, and the `tier_rank`
  fallback of `0` for an unranked/unknown tier is safe (treated as lowest).
- `recipe_hash` correctly folds a `content_hash` parameter into the cache key (matches
  CLAUDE.md's description of stale-data invalidation) — no bug.
- No writer other than the caller's own `build_address`/`recipe_hash`/`babel_coordinate` outputs
  (this module performs no file I/O itself) — no two-writer contract issue.

---

## src/descending_ladder.py

### FINDING D1 — HIGH — the entire module is orphaned: nothing in the codebase calls it
**Status: REPRODUCED** (via exhaustive grep, not just reading)

```
grep -rln "descending_ladder" src/*.py   ->  only derivation.py (which merely lists the
                                              module's *name* as a string in SCAN_MODULES,
                                              for the constant-count report — it never imports it)
grep -rn "binding_J|rung_table|DESCENDING\b" src/*.py   -> no hits outside descending_ladder.py itself
grep -n "__main__" src/descending_ladder.py             -> no hits (no CLI entrypoint either)
```

None of `rung_for_length`, `shrink_report`, `transgression_bits`, `compton_confinement_energy`,
`density_at_scale`, or `schwarzschild_radius` is imported or called by any other module in
`src/` — not `assay.py` (which still has no sub-planetary `BAND_EDGES` entries), not
`address_space.py`, not `physics.py`, not any generation/pipeline script. There is no CLI
entrypoint (`__main__`) either, so it cannot even be run standalone for a manual check.

**Consequence — this directly contradicts the module's own docstring.** The header states the gap
is "silently load-bearing": *"X.2's Reach axis is measured in metres and its band edges are
'rung-characteristic lengths' — but there are no rung-characteristic lengths below 1e7 m, so
every sub-planetary Reach is scored against a floor that does not exist,"* and presents this
186-line module as **the fix**. It is not wired to anything, so the omission it describes is
still live in the shipped Assay (`assay.py`'s `BAND_EDGES` still bottoms out at M0's Reach floor
of `1e0` m — nothing sub-planetary). Any entity whose feats require descending below Planet-scale
(the Ant-Man/Quantum-Realm case the docstring leads with) is scored exactly as before this module
was written. This is a category-7 (comment/docstring contradicts code) finding of unusually large
scope: the contradiction isn't local to a line, it's the whole module's stated reason for
existing versus its total absence from the call graph.

### FINDING D2 — KNOWN (confirmed via reproduction, not counted as new) — the Planck rung (-14) is reachable only at one exact floating-point value
**Lines:** 85-95 (`rung_for_length`)
**Status: REPRODUCED**

```
rung_for_length(PLANCK_LENGTH * 10)        -> (-13, 'Quark-confinement')
rung_for_length(PLANCK_LENGTH * 2)         -> (-13, 'Quark-confinement')
rung_for_length(PLANCK_LENGTH * 1.0000001) -> (-13, 'Quark-confinement')
rung_for_length(PLANCK_LENGTH)             -> (-14, 'Planck')
rung_for_length(PLANCK_LENGTH * 0.999999)  -> (-15, 'Below the Fold')
```
Everything strictly above `PLANCK_LENGTH` (even by one part in 1e7) resolves to
Quark-confinement (-13); everything strictly below falls into the Fold (-15, via the
`metres < PLANCK_LENGTH` guard at line 89). Rung -14 is a measure-zero target that no real
(non-exact-constant) input will ever hit. Given Finding D1, this is moot in production today
(nothing calls the function), but would need fixing (e.g. `<=` boundary redesign, or collapsing
Planck into the Fold notation) before the module could be wired up safely.

### Reviewed, no defect found
- `compton_confinement_energy`, `density_at_scale`, `schwarzschild_radius`,
  `transgression_bits`: formulas match their cited physics, guards on non-positive inputs are
  correct, and the erratum documented at lines 163-172 (why the patch is priced against
  degeneracy/Schwarzschild rather than the uncertainty principle) reads as a genuine, previously
  fixed bug rather than a current one.
- `DESCENDING`'s `binding_J` column is not monotonic in a naive sense across the full 15 rows
  (aggregate energies for rungs 0..-5, then much smaller per-particle bond/ionization energies for
  rungs -6..-13, then a jump back up to the Planck energy at -14) — but since **nothing reads
  `binding_J` anywhere in the codebase** (see D1), this is inert data, not a live bug. Flagging
  only as something to sanity-check if/when the module is ever wired up: an aggregate-vs-per-
  particle unit inconsistency in one column would need resolving before `binding_J` could be used
  the way `BAND_EDGES["ruin"]` is used in `assay.py`.

---

## src/assay.py

No new correctness/truncation/swallowed-failure/two-writer/concurrency findings beyond the
already-known `_SCALE` sigma-discarding issue (not re-derived here). Specific checks performed
and cleared:

- **HARD RULE 0 scan:** no `[:N]`, `limit=`, `most_common(`, or sampling anywhere in this module —
  clean.
- **Swallowed failures:** no bare `except`. The `_BAD_CHARS` control-character guard raises
  `SystemExit` loudly rather than swallowing corruption (matches the pattern's own stated intent).
- **Two-writer contract:** this module performs no file writes at all — n/a.
- **Checks that cannot fail:** none found; `axis_score`'s clamp, `assay()`'s `used`/`nil`/
  `applicable`/`unscored` partition, and `_interval`'s variance propagation were traced by hand
  and are mutually exclusive and exhaustive over `W`'s keys (verified: every key in `W` lands in
  exactly one of `used`, `nil`, `unscored ∪ unestimable`, or is excluded via `INAPPLICABLE`).
- **Ceiling/promotion logic** (lines 437-444): confirmed by reading that `axis_score` can return
  exactly `10.0` (not just `9.9`) when a feat clears the top of a band's log window
  (`min(1.0, frac)` hits exactly 1.0), and the `_dec >= 1.0` promotion/ceiling branch correctly
  catches that case before it could print an invalid `M10.100`-style overflow.
- **`_interval`'s per-call `weights=` override** (lines 344-351): the comment describes a 2026-08-24
  fix (custodes' axis-emphasis reweighting no longer silently uses the module-global `WEIGHTS`
  denominator) — read the code and confirmed the fix is actually in place (`W = weights if
  weights is not None else WEIGHTS`, used consistently for both the composite and the interval);
  not a currently-live bug.
- `interval_from_hands`'s "must cover every signed reading" while-loop (lines 636-637) is a
  genuine enforced invariant, not a tautology — confirmed it actually widens `interval` until the
  containment holds, rather than asserting something already guaranteed by construction.

---

## src/derivation.py

No correctness bugs found. This module is a static dependency ledger plus a graph-integrity
checker; it doesn't touch any of the seven finding categories in a live way, with one minor,
benign note:

### Note (not a finding) — `main()`'s "deepest derivation chains" report is display-truncated to 6
**Line:** 534 — `for n in sorted(LEDGER, key=lambda x: -depth(x))[:6]:`
This is a printed console summary only ("deepest derivation chains ... [:6]"); it does not affect
`check_graph()`'s pass/fail verdict, does not write any file, and does not change which quantities
are considered DERIVED/OWNER/etc. Confirmed DISPLAY truncation, not DATA truncation — the full
graph is still checked and the full failure list (`problems`) is printed unabridged above it.

### Reviewed, no defect found
- `check_graph()`'s dangling-parent / rootless-derivation / cycle-detection DFS (`visit`) is
  correct: `state` correctly distinguishes `"open"` (on the current DFS stack, so revisiting means
  a real cycle) from `"done"` (fully explored, safe to skip).
- `scan_constants` only scans **top-level** (`tree.body`) `ast.Assign` nodes, so a module-level
  constant defined inside a conditional or nested block would be invisible to this scan — but the
  function's own docstring already calls this "a reviewer's map, not a verdict," so this is a
  documented limitation rather than a silent gap; not flagging as a defect.
- No file writes in this module — two-writer contract n/a.

---

## src/physics.py

No findings. Read in full; no caps, no truncation, no swallowed exceptions (both `joules_for` and
`kinetic` raise loudly on bad input rather than defaulting), no file writes, and the
Newtonian/relativistic kinetic-energy switch at `0.1c` (lines 90-93) was checked by hand for a
discontinuity at the boundary and found continuous to within numerical precision (the two
formulas agree to <1% at exactly `v = 0.1c`). `binding_energy`'s own docstring correctly
discloses that it underestimates a centrally-condensed body like the Sun and that
`assay.BAND_EDGES` deliberately uses the literature value instead — consistent with what was
found in `assay.py`.

---

## Summary table (severity-ordered, NEW findings only; known items listed for cross-reference)

| ID | Severity | File:Line | Status | One-line |
|----|----------|-----------|--------|----------|
| G1 | HIGH | genre.py:69,89,104,118 | REPRODUCED | genre cue regexes over-match common English words (`war`→warm/ward, `hell`→hello, `corpo`→Corporal, `clan`→clandestine), corrupting genre/register/world-prior assignment for most sources |
| D1 | HIGH | descending_ladder.py (whole module) | REPRODUCED | module is completely unwired (no imports, no callers, no `__main__`); the sub-planetary Reach gap its docstring claims to fix is still unfixed in the live Assay |
| R1 | MEDIUM-HIGH | rosetta.py:194 | VERIFIED-BY-READING | `srlimit="5"` caps every wiki search query to 5 hits, a DATA truncation of the mined scale corpus written to ROSETTA.json |
| A1 | LOW | address.py:127 | REPRODUCED | `slugify`'s 60-char cap can collide two distinct long category labels into an identical address slug (currently dead-path, no live category triggers it) |
| R2 | LOW | rosetta.py:402 | REPRODUCED | `+ P.__dict__.get("_x", 0)` next to the known decimal-only bug is dead no-op code (pipeline has no `_x` attribute) |
| G2 | (known) | genre.py:135,182,187 | REPRODUCED (already flagged) | `most_common(3)` truncates the confidence denominator; reproduced with a live example (0.39 reported vs 0.292 true) |
| D2 | (known) | descending_ladder.py:85-95 | REPRODUCED (already flagged) | Planck rung reachable only at one exact float value; moot while D1 stands |
