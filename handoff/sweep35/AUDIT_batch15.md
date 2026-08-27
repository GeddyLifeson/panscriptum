# SWEEP35 batch15 audit

Modules read complete: src/rigor.py (909), src/overwatch.py (789), src/weave.py (500),
src/address_space.py (384), src/address.py (323), src/burgs.py (273),
src/descending_ladder.py (221), src/scope.py (175). 3,574 lines.

## Findings filed (4)

1. **80a54e548985** — address_space.py:26-29 — the module docstring's field-width table
   ("3 bits ... 38 bits ... = 89 bits, 12 bytes") is hand-restated prose, not derived from
   WIDTHS/TOTAL_BITS. Currently correct (verified: TOTAL_BITS==89) but this is the exact shape
   of the 74-vs-89 drift the docstring itself narrates; a future re-charting (already shown live
   by order 60dc7c624c06's TIERS.json/hyperverse-count mismatch in the same docstring) changes
   WIDTHS but not this hardcoded paragraph. MINOR — future risk, not a present error.

2. **0e81459ad875** — descending_ladder.py:171 vs 186/213 — `shrink_report()` hardcodes the
   nuclear-saturation-density verdict threshold as bare `1e17`, while the module's own
   `NUCLEAR_DENSITY = 2.3e17` constant (defined 15 lines later) is what `transgression_bits()`
   actually prices against. For densities between 1e17 and 2.3e17 kg/m^3 the verdict says
   unlawful/black-hole territory while the cost model prices the same trajectory at zero extra
   bits for that term. MAJOR.

3. **09d47bc950d9** — scope.py:100-107 — `scope_for()`'s no-tier-clears-the-floor fallback
   reverts to `max(counts, key=counts.get)`, i.e. literally "the commonest tier" (the comment's
   own words), which is the exact frequency-based method the module's header exists to reject
   ("Not by frequency ... never the most frequent one", citing Marvel's planet-vs-universe
   mention counts as the cautionary case). The fallback fires precisely in the sparse-evidence
   case where that bias matters most. MAJOR.

4. **0f43af7e5e1c** — scope.py:116-138 — `build()` caches a failed `scope_for()` call
   (exception path) and a genuine "no qualifying pages found" call identically as `out[h] =
   None`, and both permanently exclude that host from all future `--build` runs via
   `h not in out`. A transient API hiccup gets the same permanent skip as a real empty result,
   with no retry and no way to tell them apart from SCOPE.json alone. MAJOR.

## Reviewed, no new finding
rigor.py, overwatch.py, weave.py, address.py, burgs.py are already heavily self-audited in
their own docstrings (each carries multiple "found/fixed on <date>" notes); spot-verified several
of those claims against source and they hold. address_space.py and descending_ladder.py already
carry open orders for dead code (UNADDRESSED, citation_card/seed_from_card, ceiling_for,
descending_ladder as a whole) — not re-filed.
