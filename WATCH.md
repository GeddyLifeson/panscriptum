# OVERWATCH

round 70  ·  last run 2026-08-24 13:25

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 64,919 inspected
- catalogued sources with no host: **20** Clockwork Angels (Rush), Curious DM Investigations (the Sharkin), Dr. Firestorm'
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**12 open** (5 high). Newest first.

- **descending_ladder.py** `compton_confinement_energy` — [HIGH] Returns the kinetic energy from momentum spread p ~ hbar/(2r), but uses HBAR (reduced Planck constant) instead of hbar/2 in the momentum calculation, leading to incorrect scaling. 
  - says: Energy required to CONFINE a mass to a given size, from the uncertainty principle.
- **cosmography.py** `_fmt` — [HIGH] is used but never defined in this file or its imports
  - says: formats a value for display in the Kardashev distribution output
- **cleanup.py** `clean_ceiling` — [HIGH] The function returns the original ceiling unchanged only if no strategy succeeds, but the 'unresolved' case is reported via the `ceil_unres` list in `main()`, which means the ceili
  - says: If none of the strategies land, the ceiling is left ALONE and reported -- guessing a name would be worse than admitting phase 1 answered the wrong question.
- **silence.py** `note` — [HIGH] Records the exception currently being handled, but also flushes the health ledger every FLUSH_EVERY calls, even if the exception was not successfully recorded due to an internal fa
  - says: Record the exception currently being handled, then return.
- **build_terminal.py** `view.w` — [HIGH] The view width is set to the maximum of the SVG's width and height scaled by the aspect ratio, but the code uses `view.w = Math.max(b.width, b.height * ar) * 1.07;` which incorrect
  - says: The view width is adjusted based on the SVG's actual bounding box dimensions after drawing.
- **catalogue_web.py** `write_record_catalogue` — [MEDIUM] returns whether the rename was successful
  - says: returns whether the rename LANDED
- **catalogue_web.py** `ws.rank_by_size` — [MEDIUM] truncates at top=None
  - says: rank, never truncate
- **hostcheck.py** `add` — [MEDIUM] Adds a host to the grounded list if speculative is False, but the function is called with speculative=True for some cases, which is not handled correctly
  - says: Adds a host to either the speculative or grounded list
- **feats.py** `roll` — [MEDIUM] restrict the roll to sources containing this string
  - says: mine the whole corpus
- **rigor.py** `p_point` — [MEDIUM] p_point is computed as 1.0 - math.exp(-(10.0 ** log10_median)), which is P evaluated at the mean of lambda, but the comment claims this is the 'point-estimate column' and warns it 
  - says: the point-estimate column is the one to distrust; it is P evaluated at the mean, not the mean of P
- **build_terminal.py** `bindStage` — [MEDIUM] The `pointermove` handler uses `stage.getBoundingClientRect()` to compute scale, but if the stage is not yet rendered or has collapsed dimensions (e.g., width/height < 2), it retur
  - says: The stage event listeners for wheel and pointermove are bound to enable zoom and pan, with proper handling of pointer events.
- **build_terminal.py** `srFit` — [MEDIUM] The variable srFit is computed using fitIn with the maximum length of the source names, the radius sr, and a font size of 46, but this value is never used. Instead, the code uses s
  - says: The variable srFit is computed using fitIn with the maximum length of the source names, the radius sr, and a font size of 46, to determine how much text fits in

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
