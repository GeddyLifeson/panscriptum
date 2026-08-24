# OVERWATCH

round 65  ·  last run 2026-08-24 08:32

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 63,771 inspected
- catalogued sources with no host: **20** Clockwork Angels (Rush), Curious DM Investigations (the Sharkin), Dr. Firestorm'
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**22 open** (13 high). Newest first.

- **standards.py** `job_stamp` — [HIGH] The function is never defined or imported in this slice.
  - says: Carrying the stamp forward while the size holds is what makes the number mean silence.
- **descending_ladder.py** `compton_confinement_energy` — [HIGH] Returns the kinetic energy from momentum spread p ~ hbar/(2r), but uses HBAR (reduced Planck constant) instead of hbar/2 in the momentum calculation, leading to incorrect scaling. 
  - says: Energy required to CONFINE a mass to a given size, from the uncertainty principle.
- **cosmography.py** `_fmt` — [HIGH] is used but never defined in this file or its imports
  - says: formats a value for display in the Kardashev distribution output
- **cleanup.py** `clean_ceiling` — [HIGH] The function returns the original ceiling unchanged only if no strategy succeeds, but the 'unresolved' case is reported via the `ceil_unres` list in `main()`, which means the ceili
  - says: If none of the strategies land, the ceiling is left ALONE and reported -- guessing a name would be worse than admitting phase 1 answered the wrong question.
- **backfill.py** `backfill_source` — [HIGH] returns a dictionary with 'missing' key indicating how many entries were missing after applying the cap, not the original number of missing entries
  - says: returns a dictionary with 'absent' key indicating how many entries were missing from the source's roster
- **silence.py** `note` — [HIGH] Records the exception currently being handled, but also flushes the health ledger every FLUSH_EVERY calls, even if the exception was not successfully recorded due to an internal fa
  - says: Record the exception currently being handled, then return.
- **profile.py** `decode` — [HIGH] The 'band' field is decoded correctly, but the code uses B32.index(band) when band is 'u', which raises ValueError because 'u' is not in B32. The code should check for 'u' before u
  - says: The 'band' field in the profile is decoded correctly from the 'u' or a base32 digit, and mapped to 'unassayed' or a band value from BANDS.
- **pipeline.py** `phase_cosmology` — [HIGH] The function incorrectly passes the source name to `G.classify_source` instead of the full record, which causes 209 AttributeErrors and results in all sources being marked as 'ungr
  - says: The function processes the cosmology phase, charting tiers, grounding sources, censusing populations, and assigning addresses to worlds based on their tier stac
- **pipeline.py** `batch_settled` — [HIGH] The function checks if the key is in done_keys and if all entries in the batch have a 'catalogued' field, but it does not verify that the 'catalogued' field is truthy. It uses `e.g
  - says: True when an entrypass batch may be skipped on resume, based on the key being in done_keys and all entries in the batch having a 'catalogued' flag.
- **build_terminal.py** `view.w` — [HIGH] The view width is set to the maximum of the SVG's width and height scaled by the aspect ratio, but the code uses `view.w = Math.max(b.width, b.height * ar) * 1.07;` which incorrect
  - says: The view width is adjusted based on the SVG's actual bounding box dimensions after drawing.
- **manifest_builder.py** `load_record` — [HIGH] The function incorrectly checks `norm_target in norm_fname` (substring containment) and `norm_target.startswith(norm_fname)` (prefix containment), but the logic is reversed: it sho
  - says: Finds the best matching record file by checking if the normalized source name is a substring of the normalized filename or if the normalized filename is a prefi
- **foreman.py** `kill_duplicate_jobs` — [HIGH] The function uses `started.group(1)` to extract the creation timestamp, but if the `started` regex does not match, it defaults to a string of '9's. This can lead to incorrect sorti
  - says: Keep the OLDEST instance of each job and end the rest.
- **feats.py** `api` — [HIGH] May make a MediaWiki API call to the wrong endpoint if the wiki is not Fandom or Wikipedia
  - says: Makes a MediaWiki API call to the correct endpoint
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
- **foreman.py** `kill_stalled_job` — [MEDIUM] The function attempts to kill processes based on a job name parsed from a string, but the regex pattern used to extract job names (`_re.findall(r"([A-Za-z0-9_]+) \(\d+ min", str(ro
  - says: A job that is UP and writing nothing is worse than a job that is down.
- **autostart.py** `ap.add_argument('--read-hours', type=float, default=10)` — [MEDIUM] read-hours argument is used to start the supervisor
  - says: read-hours argument is used to determine the hours to read

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
