# OVERWATCH

round 68  ·  last run 2026-08-24 09:59

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 64,919 inspected
- catalogued sources with no host: **20** Clockwork Angels (Rush), Curious DM Investigations (the Sharkin), Dr. Firestorm'
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**19 open** (8 high). Newest first.

- **standards.py** `job_stamp` — [HIGH] The function is never defined or imported in this slice.
  - says: Carrying the stamp forward while the size holds is what makes the number mean silence.
- **descending_ladder.py** `compton_confinement_energy` — [HIGH] Returns the kinetic energy from momentum spread p ~ hbar/(2r), but uses HBAR (reduced Planck constant) instead of hbar/2 in the momentum calculation, leading to incorrect scaling. 
  - says: Energy required to CONFINE a mass to a given size, from the uncertainty principle.
- **cosmography.py** `_fmt` — [HIGH] is used but never defined in this file or its imports
  - says: formats a value for display in the Kardashev distribution output
- **cleanup.py** `clean_ceiling` — [HIGH] The function returns the original ceiling unchanged only if no strategy succeeds, but the 'unresolved' case is reported via the `ceil_unres` list in `main()`, which means the ceili
  - says: If none of the strategies land, the ceiling is left ALONE and reported -- guessing a name would be worse than admitting phase 1 answered the wrong question.
- **silence.py** `note` — [HIGH] Records the exception currently being handled, but also flushes the health ledger every FLUSH_EVERY calls, even if the exception was not successfully recorded due to an internal fa
  - says: Record the exception currently being handled, then return.
- **profile.py** `decode` — [HIGH] The 'band' field is decoded correctly, but the code uses B32.index(band) when band is 'u', which raises ValueError because 'u' is not in B32. The code should check for 'u' before u
  - says: The 'band' field in the profile is decoded correctly from the 'u' or a base32 digit, and mapped to 'unassayed' or a band value from BANDS.
- **build_terminal.py** `view.w` — [HIGH] The view width is set to the maximum of the SVG's width and height scaled by the aspect ratio, but the code uses `view.w = Math.max(b.width, b.height * ar) * 1.07;` which incorrect
  - says: The view width is adjusted based on the SVG's actual bounding box dimensions after drawing.
- **manifest_builder.py** `load_record` — [HIGH] The function incorrectly checks `norm_target in norm_fname` (substring containment) and `norm_target.startswith(norm_fname)` (prefix containment), but the logic is reversed: it sho
  - says: Finds the best matching record file by checking if the normalized source name is a substring of the normalized filename or if the normalized filename is a prefi
- **cascade_bridge.py** `ask` — [MEDIUM] The function is used in a way that may not align with its intended purpose, as the code may not correctly handle the 'pin' parameter and the 'timeout' parameter might not be proper
  - says: Send one tiny call to EVERY bucket and record which actually answer.
- **hostcheck.py** `add` — [MEDIUM] Adds a host to the grounded list if speculative is False, but the function is called with speculative=True for some cases, which is not handled correctly
  - says: Adds a host to either the speculative or grounded list
- **feats.py** `roll` — [MEDIUM] restrict the roll to sources containing this string
  - says: mine the whole corpus
- **standards.py** `work_orders` — [MEDIUM] Sorted by severity rank, but the comment and the code in report() contradict this by sorting by severity strings (high, low, medium) instead of using the rank dict
  - says: Only the breaches, worst first — the thing a person or a model is meant to act on.
- **standards.py** `_RUNNER` — [MEDIUM] update a dictionary named _RUNNER
  - says: update the runner status
- **rigor.py** `p_point` — [MEDIUM] p_point is computed as 1.0 - math.exp(-(10.0 ** log10_median)), which is P evaluated at the mean of lambda, but the comment claims this is the 'point-estimate column' and warns it 
  - says: the point-estimate column is the one to distrust; it is P evaluated at the mean, not the mean of P
- **endpoint.py** `fetch_html` — [MEDIUM] The function uses `max_workers=2` but the comment says 'Two workers, and politely' — however, the actual value is hardcoded as 2, which contradicts the implication that it's a conf
  - says: Two workers, and politely. These are one-author sites on shared hosting, not Fandom's CDN, and the entire point of reading them is that the author put the mater
- **build_terminal.py** `resetView` — [MEDIUM] The code attempts to get the bounding box via `f.getBBox()` but does not account for the fact that `getBBox()` returns `null` if the element is not rendered or not visible in the D
  - says: The view is adjusted to fit the actual SVG content by measuring its bounding box.
- **build_terminal.py** `bindStage` — [MEDIUM] The `pointermove` handler uses `stage.getBoundingClientRect()` to compute scale, but if the stage is not yet rendered or has collapsed dimensions (e.g., width/height < 2), it retur
  - says: The stage event listeners for wheel and pointermove are bound to enable zoom and pan, with proper handling of pointer events.
- **build_terminal.py** `srFit` — [MEDIUM] The variable srFit is computed using fitIn with the maximum length of the source names, the radius sr, and a font size of 46, but this value is never used. Instead, the code uses s
  - says: The variable srFit is computed using fitIn with the maximum length of the source names, the radius sr, and a font size of 46, to determine how much text fits in
- **autostart.py** `ap.add_argument('--read-hours', type=float, default=10)` — [MEDIUM] read-hours argument is used to start the supervisor
  - says: read-hours argument is used to determine the hours to read

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
