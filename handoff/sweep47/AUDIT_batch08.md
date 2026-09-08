# Sweep 47, Batch 08 — audit

Modules read in full, every line, top to bottom: `src/feats.py` (1978), `src/sweep_plan.py`
(1012), `src/custodes.py` (698), `src/zfighters.py` (536), `src/catalogue_codex.py` (457),
`src/snapshot.py` (376), `src/physics.py` (312), `src/suppressions.py` (254). All 8 modules named
in the brief, 5,623 lines total, no skips, no sampling.

## Context on this batch

All eight modules here are unusually mature: most already carry dense docstrings narrating their
own prior faults, the orders that fixed them, and (in several cases) explicit self-measurement
against the live corpus. `feats.py` alone had 17 work orders already open against it, and reading
it end to end turned up nothing beyond what those orders already describe — every fault shape I
could construct while reading (host-resolution race, cache staleness, truncated discovery lists,
refusal-marker false positives, the exponent-parsing bug, the `pages:` name-match hole) is already
named by an existing order, several with their own audit trail. `custodes.py`, `physics.py` and
`snapshot.py` are similarly hardened — physics.py in particular has been through three rounds of
"the guard refuses the input but not the overflowing result" fixes and I could not find a fourth.
`zfighters.py` is mostly curated data (hand-scored assay sheets); I checked its arithmetic paths
and its score data (nothing exceeds the 0-9.9 axis range) rather than treating it as prose.

Three modules already fixed vs. their filed orders, confirmed by direct measurement rather than
by reading the comment alone:
- `sweep_plan.py`: `coverage_map()` genuinely has zero callers (order d411f780d347) — `main()`'s
  `--coverage` branch reads `COVERAGE` directly rather than calling it. Still true, still dead.
- `catalogue_codex.py`: `TYPE_CATEGORY` now maps `race variant` and `background variant` (the
  order's own comment describes them as already fixed); `weapon property` is confirmed STILL
  unmapped by re-running `parse_codex()` against the live codex today (35 occurrences, 1 of 18
  distinct element types) — order 85cdecef25f8 is correctly still open, not stale.
- `suppressions.py`: both open orders confirmed still live by reading `data/SUPPRESSIONS.json`
  directly — the `Encrypted.json` row is still exactly 300 characters, still cut mid-word
  ("...this only sur"), and `problems()`'s dangling-check glob is unchanged (still walks the
  whole tree per row, still case- and dot-blind by construction). Neither needed re-filing.

## New findings filed (3)

1. **`cac0c6466cfc`** (MINOR, LOCAL) — `catalogue_codex.py`'s `TYPE_CATEGORY.get(etype.lower(),
   THINGS)` silently defaults any unrecognized element type to THINGS with **no measurement or
   report anywhere**, unlike every other collision class in this same file (section-title
   clashes, ambiguous source bindings, register-description collisions, duplicate elements),
   which are all counted and printed uncapped before the write summary. This is *why*
   `weapon property` was only ever caught by manual grep rather than by the tool — and why the
   next new element type the owner adds to the codex will fail the identical silent way. Verified
   live: 1 of 18 distinct types unmapped today.

2. **`f1d5165b188b`** (MINOR, LOCAL) — same file's manifest regex captures the codex's own
   declared item count (`Magic Item (41): ...`) in `m.group(2)` and never reads it again;
   nothing cross-checks it against the number of names actually parsed. Verified against the live
   codex: 0 mismatches across all 281 manifest lines today, so this is a dormant gap rather than
   an active loss — but there is currently no code path that would notice a future truncation
   (line wrap, encoding hiccup, hand-edit) that this count exists specifically to catch.

3. **`bf316bbb7f89`** (MINOR, SESSION) — `sweep_plan.py`'s `freeze_plan()` has a genuine
   check-then-write race with no lock or compare-and-swap: two concurrent callers for the same
   `run` can both see "absent," both compute, and the second write silently overwrites the first
   via `replace_retry` with no verification against what actually landed. The losing caller's
   in-memory return still claims `frozen: True`, contradicting the function's own "never
   recomputed and never overwritten" contract. `check_briefs()` bounds the damage after the fact
   (it diffs dispatched briefs against the disk-frozen plan), and `freeze_plan` has very few call
   sites today, so this is a real but narrow-window gap rather than a live incident.

## Verified clean / no new findings

- **`feats.py`**: read fully; every fault pattern found matches an already-open order. No new
  findings.
- **`custodes.py`**: the DOF/Custos table is internally consistent (10 Custodes, 10 degrees of
  freedom, exact 1:1 mapping); the two OWNER orders already on file (Lumen/Threnody unwired,
  assay_dof count) cover what's actually wrong here. Noted but did not file: `prior_share = 1.0`
  when `total_var == 0` is a real edge-case default, but it requires exact floating-point equality
  across independently-computed Custos readings, which does not happen with the live axis-emphasis
  weighting — treated as unreachable in practice rather than a defect.
- **`zfighters.py`**: no open orders against it; read as both code and data. Arithmetic paths
  (`compute()`, `value()`, the `--full` display) are sound; hand-scored data is within range.
- **`snapshot.py`**: no open orders; this is the most defensively-written module in the batch
  (containment checks on paths, atomic manifest writes, directory-content verification on
  restore, partial-snapshot refusal). Found nothing to file.
- **`physics.py`**: no open orders; every numeric guard (mass/speed/radius positivity,
  finiteness, NaN, and now post-arithmetic overflow) has already been hardened through three
  rounds of fixes. Found nothing to file.
- **`suppressions.py`**: both open orders reconfirmed live (see above); no new findings.

## Coverage recorded

`sweep_plan.record('run47', [...8 modules...], batch=8)` — landed, 164 modules now recorded in
the merged shard view.
