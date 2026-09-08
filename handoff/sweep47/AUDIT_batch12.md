# Sweep47 batch12 audit

Scope: every line of the 8 modules named in `brief_batch12.md` — `src/overnight.py` (1784),
`src/rigor.py` (1051), `src/derivation.py` (790), `src/ingest_doc.py` (570), `src/worldseed.py`
(492), `src/cosmography.py` (340), `src/coverage.py` (336), `src/profile.py` (272) — 5,635 lines
total, all read in full, none sampled.

## Overall impression

This batch is the most heavily self-audited code I have seen in the sweep so far. Nearly every
one of the seven fault shapes in the brief has already been found, fixed, and left with an
explicit docstring/comment naming the order that fixed it and the incident that motivated it
(silent truncation, could-not-measure-as-value, checks that couldn't fail, exit-code-always-ok,
etc. all have named, dated fixes in these eight files). The remaining open orders against these
modules are, almost without exception, genuinely still open in the code (verified below) or are
explicitly framed as owner questions the code cannot resolve on its own.

## Already-open orders: verification

Per instructions, I did not re-file any of these. Status after reading the actual code:

- **overnight.py** — all five open orders (2cb8756deb0a, 728d9e99e9ec, 5d14e90b5043,
  fe99e57e1993, 5ed00985ce04) match code that is still in the state their titles describe
  (e.g. the `pipeline` re-run inside the main cycle is still present, with the docstring
  explicitly saying it is "LEFT IN PLACE PENDING AN OWNER RULING"). No action needed.
- **rigor.py** — `dc501e776a2b` (theorem1-consistent-on-nan): `theorem_1_check` /
  `perron_weights` / `logrank_weights` still have no NaN/degenerate-matrix guard. Still open.
- **derivation.py** — `c9e6e50e792f` (DOF nine not ten): `LEDGER["assay_dof"]["parents"]` still
  lists exactly 9 entries while its own `note` says "ten survive the test". Still open, confirmed
  by direct count.
- **ingest_doc.py** — of the four listed orders, **two appear to already be fixed in code**:
  - `9da4543dc586` (INGEST_MINE_TRACEBACKS_ON_A_MISSING_RECORD): `mine()` now has an explicit
    `if not os.path.exists(rp): raise ValueError(...)` guard, with a comment citing this exact
    order number as the fix. This looks closed and could be resolved.
  - `cf861246e83e` (INGEST_CUMULATIVE_COUNTER_LABELLED_THIS_RUN): `mine()` now captures
    `started_at = state["found"]` at entry and reports `state["found"] - started_at` as "this
    run"'s count, with a comment citing this exact order number. This also looks closed.
  - `08c9ee5fb3bd` (INGEST_ASK_NONDICT_CRASH) and `e049b82ab858`
    (INGEST_CATEGORY_SILENT_DEFAULT) are still genuinely open: `_ask()`'s return value is used
    as `got.get("entries")` with no isinstance check, and the category field still silently
    falls back to `CATEGORIES[0]` with no note when the model's returned category is missing or
    invalid.
- **worldseed.py** — six open orders. `ad681057369a` (unreachable "primitive" tier) and
  `e68664e621bf` (`URL_SETTABLE` unread) are confirmed still present exactly as described
  (`URL_SETTABLE` is defined at module level and never referenced again — grep-verified).
  `475a06c19374` (band-unparsed looks like M0) is confirmed still open: an unparseable band
  falls through to `tier = 0`, indistinguishable from a genuine M0. `40e98eed6870` /
  `c0384991bfc5` (sweep34 findings) not independently re-diagnosed this pass; nothing suggests
  they've been closed. One order looks **already fixed**:
  - `82adeee9b7ee` (LIMIT_ZERO_READ_AS_NO_LIMIT): `build_all()`'s loop guard now reads
    `if limit is not None and len(out) >= limit`, with a comment citing this exact order. I
    checked every caller of `build_all` across `src/` (burgs.py, navtree.py, profile.py,
    render.py, sevenfold.py, verify_math.py, worldseed.py's own `main()`) and none passes
    `limit=0`, so the fix is complete at its only call site.
- **cosmography.py** — all four open orders (7099a092abd3, adaeaa7ad639, c22c8b1f426c,
  cdfeccbfbab0) match code that is explicitly and currently in the described state — e.g. the
  comment directly above `SIZE_CLASS_MAX_GALAXIES` says outright "with SIZE_CLASSES as it
  stands, POCKET computes 2.0e2 galaxies and MINOR 2.0e5, so both now REFUSE" and explicitly
  defers the choice to the owner. Still open, correctly framed as owner questions.
- **coverage.py** — `88a5f9192e1b` and `732f68f640cf` both match current code (the
  `--show`/`--show-best` default asymmetry is still present and is argued for in a comment,
  which is exactly what makes it a question rather than a defect). Still open.

## New finding filed

**PROFILE_ENCODE_CRASHES_ON_DECIMAL_BAND** (id `3e576b1a29ad`, LOCAL/MINOR) —
`profile.encode()` resolves a band string via `BANDS.index(band)` where `BANDS` is the literal
list `["M0", ..., "M10"]`. Any decimal-format Assay reading (the charter's own published
notation — `rigor.py`'s own docstring cites "A M3.52 ± 0.12" as an example) is not in that list,
so `encode()` raises an uncaught `ValueError` instead of degrading or reporting. Reproduced
directly:

```
profile.encode(12345, "mythology", "classical",
    {"landform":"isles","climate":"temperate","condition":"ruined","tech":"medieval"},
    "M3.52", 2)
-> ValueError: 'M3.52' is not in list
```

This would take down `profile.build_all()` and every caller of it (`navtree.py`, `burgs.py`,
`render.py`, `sevenfold.py`, `verify_math.py`) the instant any catalogued Place carries a decimal
band instead of a bare `M<int>` — which is the exact transition `worldseed.py`'s own comments
describe as imminent ("the first real Assay pass is what makes it live"). The sibling module
`worldseed.py` already hardened its *own* band parser for this exact transition
(`to_options()` uses a regex that reads only the integer head of the band string and falls back
to `silence.note` on an unparseable value rather than raising) — so the two modules reading the
*same* `band`/`magnitude` field now disagree about what a decimal value means: one degrades, the
other crashes. Checked the live corpus (`data/records/*.json`): every `magnitude` value today is
either `"unassayed"` or a bare `M<digit>`, so this is currently latent, not firing — filed as
MINOR rather than MAJOR for that reason, but it is a real, reproduced defect rather than a
hypothetical one, and it will start firing the day decimal Assay results land, which multiple
other files in this batch describe as planned.

*(Process note: my first attempt to file this order was mangled by the Bash tool interpreting
backticks inside the shell command as command substitution, corrupting parts of the `what` text.
I caught this by reading the order back, and re-filed it from a script file — `code`+`where` are
content-addressed so the id is unchanged and the second filing overwrote the corrupted text
cleanly. Recorded here in case anyone diffs `workorders.json` history and wonders about the
edit.)*

## Coverage

All 8 named modules read in full, top to bottom, no sampling, no line ranges skipped.
