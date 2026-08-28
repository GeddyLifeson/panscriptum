# Cross-module needs — LOCAL batch 3 (run 36)

Agent scope: cosmography.py, hosts.py, physics.py, pick_model.py only.

## Order 5925b90cb6d0 (cosmography.py dead constants) — partially disproven, partial cross-module fix needed

The order bundles three claims under one id. Verified against current source:

1. **DEFAULT_SIZE_CLASS (cosmography.py:133) — DISPROVEN.** The order says `census()`
   "re-types the same string in its own signature at cosmography.py:169, so editing the
   constant moves nothing." That is false against the current file: `census()` is defined as
   `def census(size_class=DEFAULT_SIZE_CLASS, ...)` — verified live
   (`inspect.signature(C.census).parameters['size_class'].default is C.DEFAULT_SIZE_CLASS`
   → `True`). Editing the constant does move the default. Either the audit was wrong or this
   was already fixed by someone else before this shift; either way, no action taken and none
   needed on this part.

2. **KARDASHEV_TYPE_I (line 66) and EARTH_POWER_2020 (line 69) — CONFIRMED, but the fix is
   outside src/cosmography.py.** Grep over src/ confirms zero readers of either name. The
   values ARE exercised, but only as re-typed literals in a module I do not own:
   `src/verify_math.py:193-194`:
   ```
   check("Kardashev K(Type I = 1e16 W) == 1.0", C.kardashev_K(1e16), 1.0, tol=1e-9)
   check("Kardashev K(Earth 2e13 W)", C.kardashev_K(2e13), 0.730, tol=2e-3)
   ```
   The module's own docstring (cosmography.py:18-20) promises "every convention is a named
   module-level constant... change one, re-run, and every downstream figure moves with it" —
   so the right fix is for verify_math.py to reference `C.KARDASHEV_TYPE_I` and
   `C.EARTH_POWER_2020` in place of the literals `1e16` and `2e13` on those two lines
   (mirroring how `C.KARDASHEV_TYPE_II` / `C.KARDASHEV_TYPE_III` are already referenced by
   name three lines below at 197/201), not for cosmography.py to delete the constants — that
   would work against the module's own reversibility premise.

**Whoever owns verify_math.py this shift:** please swap the two literals on lines 193-194 for
`C.KARDASHEV_TYPE_I` and `C.EARTH_POWER_2020` respectively. That closes the constants' dead-code
gap without touching cosmography.py. Order 5925b90cb6d0 left OPEN pending that.
