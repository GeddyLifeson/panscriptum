# OVERWATCH

round 278  ·  last run 2026-09-02 12:15

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 289,399 inspected (deep scan as of round 277)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**28 open** (5 high). Newest first.

- **workorders.py** `_detector` — [HIGH] is called with a boolean that is the inverse of the actual detection status
  - says: detects a problem and triggers a detector
- **catalogue_models.py** `sweep` — [HIGH] sweep
  - says: sweep
- **catalogue_aurora.py** `parse_folder` — [HIGH] does not collect dropped entries
  - says: collects what collapsed
- **verify_math.py** `A.calibration_report` — [HIGH] the function may not return a dict and instead return None or another type
  - says: calibration_report answers with a dict at all
- **verify_math.py** `_stamp` — [HIGH] the stamp lies about which arithmetic produced the bar
  - says: the correlation stamp names its provenance
- **local_agent.py** `rel_real` — [MEDIUM] the resolved path is compared to the real path relative to the real HERE, which may not be the same as the original path's relative position
  - says: compare the two project-relative spellings, and only interrogate the resolved one when the filesystem disagrees with the string.
- **coverage.py** `measure` — [MEDIUM] does not guard divisions in `coverage`/`settled` keys
  - says: guards every division with max(n, 1)
- **codewatch.py** `exit_if_stale` — [MEDIUM] Exits the process if its code is out of date, but the code does not actually exit the process.
  - says: Exits the process if its code is out of date.
- **catalog.py** `cmd_address` — [MEDIUM] Prints 'No entry for address' if the address is not found, but the function is named 'cmd_address' which implies it handles addresses
  - says: Prints the entry for the given address
- **binding_health.py** `quarantined` — [MEDIUM] Silences the error instead of raising it when strict is False.
  - says: RAISES `QuarantineUnreadable` when the file exists and cannot be read.
- **verify_math.py** `check` — [MEDIUM] only consults `tol` inside `if isinstance(want, float)`
  - says: consults `tol` inside `if isinstance(want, float)`
- **verify_math.py** `check` — [MEDIUM] the check is for the assay not being at the ceiling, but the actual result is that the assay is considered to be at the ceiling when it's not
  - says: check('an ordinary assay is NOT at the Ladder's ceiling', ...)
- **verify_math.py** `check` — [MEDIUM] the check is for the fallback stamp containing the reason, but the actual result is that the stamp does not include the reason due to a logical error in the code
  - says: check('a FALLBACK correlation stamp names its cause instead of trailing off', ...)
- **verify_math.py** `check` — [MEDIUM] the check is for the fallback reason after a successful load, but the actual result is that the fallback reason is set to 'load() returned nothing'
  - says: check('a matrix that loads cleanly files NO fallback reason', ...)
- **verify_math.py** `check` — [MEDIUM] the check is for the result of axis_score when a band edge is half-defined, but the actual result is an exception raised instead of None
  - says: check('axis_score refuses a HALF-DEFINED band edge (floor present, ceiling missing)', ...)
- **verify_math.py** `check` — [MEDIUM] the condition is checking for a dict _cal and whether margin is None or the band is valid, but the actual check is for the presence of a margin and the band being valid
  - says: check('the calibration margin is None unless a real passing band was bracketed', ...)
- **verify_math.py** `A.assay` — [MEDIUM] the function may incorrectly categorize INAPPLICABLE and UNESTIMABLE Measures
  - says: unscored is the list of Measures nobody read
- **verify_math.py** `A.instrument` — [MEDIUM] the function may incorrectly compute Constitution when only one axis is attested
  - says: Constitution prints nothing when only one of its two axes is attested
- **verify_math.py** `A._interval` — [MEDIUM] the function may incorrectly compute between-hand variance for a single reading
  - says: Between-hand dispersion is only defined for MORE THAN ONE reading
- **verify_math.py** `A.assay` — [MEDIUM] the assay function may not correctly compute promotion_watch due to a condition change
  - says: promotion_watch is a curatorial trigger that must fire on the boundary and not below it
- **verify_math.py** `A.null_instrument` — [MEDIUM] returns a null but does not indicate it is computed
  - says: Theorem 3(ii) is that the mathematics RETURNS a null for a degenerate agent; a null that does not claim to be computed is indistinguishable from a missing reading
- **verify_math.py** `measure_bit_value` — [MEDIUM] the function is NOT the cumulative figure the stale docstring quoted
  - says: the function is NOT the cumulative figure the stale docstring quoted
- **verify_math.py** `measure_bit_value` — [MEDIUM] the function uses band_resolution, not the cumulative length
  - says: the function uses band_resolution, not the cumulative length
- **verify_math.py** `_read_frag19` — [MEDIUM] the reader is identified by a slice of the lognames.OWNER attribute, which is not a contiguous fragment
  - says: the reader is still identified by one contiguous lognames fragment
- **verify_math.py** `_CBud` — [MEDIUM] the budget is derived from the window's num_ctx
  - says: the budget is derived from the window
- **escalation.py** `clear` — [MEDIUM] clear() returns False for two different reasons, but the code treats them as the same event, leading to incorrect messages about the lift not happening.
  - says: PermissionError is caught alongside ValueError because `clear()` raises it for a non-person caller, and the two refusals are the same event to a reader: the lift did not happen and here is why.
- **cascade_bridge.py** `selftest` — [MEDIUM] executes the live check
  - says: The live check is NOT dropped
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
