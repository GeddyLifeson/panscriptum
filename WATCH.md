# OVERWATCH

round 586  ·  last run 2026-09-29 02:37

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 311,079 inspected (deep scan as of round 583)  — state\gpu_lane\slot.0.json — cannot stat: GONE (absent on a second look, one rename later)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Prime World Equipment, Super Energy Apocalypse 1 & 2, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**38 open** (30 high). Newest first.

- **axis_correlation.py** `rho` — [HIGH] returns 0.0 unless `default` is provided, contradicting the docstring's claim that the default is the measured mean
  - says: THE DEFAULT IS THE MEASURED MEAN, NOT ZERO
- **axis_correlation.py** `observations` — [HIGH] Processes all `SOURCES` files, reading and parsing them even though the comment states that the code changes nothing today and the population remains 45 until fresh assays land.
  - says: -> ([{axis: score}], {'read': [...], 'missing': [...]}) -- entities with >=2 numeric axis scores, plus which of `SOURCES` were actually read this call.
- **assay.py** `_check_constants` — [HIGH] Checks constants (as implied by the function name), but the comment suggests it should validate instrument fitness
  - says: The instrument checks itself at import and refuses to load if unfit
- **assay.py** `interval_from_hands` — [HIGH] The function calculates a centre and half_spread but does not compute the interval by adding the attestation floor in quadrature. The critical interval derivation step is missing.
  - says: Derive the published +/- from the Hands' divergence. ... The attestation floor is added in quadrature because evidence-quality noise and prior divergence are independent sources of variance
- **assay.py** `SIGMA_MAX` — [HIGH] undefined variable
  - says: used in the attestation_source string
- **assay.py** `scores` — [HIGH] The code always includes the 'scores' key with an empty dict when no scores exist, contradicting the claim that its absence indicates not recorded.
  - says: A ROW WITHOUT THIS KEY IS 'NOT RECORDED', NEVER ZERO.
- **assay.py** `assay` — [HIGH] Returns a tuple of (float, dict)
  - says: Returns a dict, never a bare float
- **assay.py** `_fr_unknown` — [HIGH] The code raises an error when FACULTY_READS contains axes not in WEIGHTS, contradicting the comment's assertion that such a misspelt axis name would result in a silent drop.
  - says: FACULTY_READS names Measures that are not in WEIGHTS: %s. `instrument()` reads them with `.get()`, so each one prints its faculty as unattested -- a claim that the subject was never observed exercising it, made because a constant is misspelt.
- **assay.py** `_check_readings` — [HIGH] NaN values are refused due to non-finite check
  - says: NaN values are not refused
- **assay.py** `SIGMA_MAX` — [HIGH] assigned the value of SIGMA_UNIFORM_PRIOR (9.9/sqrt(12)) which represents a uniform prior dispersion for a single reading
  - says: the ceiling on an ATTESTATION sigma, which measures something else entirely
- **assay.py** `band_for_quantity` — [HIGH] Checks if the axis exists only in the first band (LADDER[0]) rather than any band, leading to incorrect None returns for valid axes in other bands
  - says: Which rung's floor does this quantity clear? A helper for sanity checks, NOT the Anchor.
- **anchors.py** `collapsed` — [HIGH] the message is only printed when there are collapsed bands (i.e., when `collapsed` is non-empty), not on every invocation
  - says: THE MESSAGE NO LONGER NAMES A CULPRIT (order e954295c02e1). ... the sentence below runs on every invocation whether or not anything failed
- **anchors.py** `verdict("the college measures a finite, non-zero interval at every anchor",` — [HIGH] the code checks for intervals that are invalid (not int/float, bool, or outside 0-infinity range)
  - says: the college measures a finite, non-zero interval at every anchor
- **anchors.py** `unanchored` — [HIGH] The code checks if names in 'order' are not in 'scored', but the comment explicitly states membership should be checked against 'vals'
  - says: Membership should be checked against 'vals' instead of 'scored'
- **anchors.py** `vals` — [HIGH] The code checks if 'dec' is a bool or not an int/float, adding to 'refused' when 'dec' is None, which contradicts the comment's requirement to default to 0.0
  - says: The code should handle refusal by defaulting to 0.0 when 'decimal' is None, but it adds to 'refused' instead
- **allsweep.py** `dangling_count` — [HIGH] undefined in this slice
  - says: used to determine if there's dangling data
- **allsweep.py** `err` — [HIGH] set to tail[-1], the last line of stderr
  - says: keep the whole thing (not clipped)
- **allsweep.py** `has_parser` — [HIGH] set to True, assuming the module has a parser
  - says: handle unreadable files by letting the subprocess report it
- **allsweep.py** `RC_BROKEN` — [HIGH] Undefined in this module or its imports
  - says: Used in the VERIFIERS list as a default value for rc_means
- **address_space.py** `blanked` — [HIGH] total number of gaps across all designations
  - says: count of designations with at least one uncharted tier
- **address_space.py** `HERE` — [HIGH] HERE is referenced but not defined in this slice, leading to a NameError
  - says: HERE is used to construct file paths but not defined in this file or its imports
- **address_space.py** `TOTAL_BITS` — [HIGH] TOTAL_BITS is referenced but not defined in this slice, leading to a NameError
  - says: TOTAL_BITS is used in output formatting but not defined in this file or its imports
- **address_space.py** `silence` — [HIGH] silence is referenced but not defined in this slice, leading to a NameError
  - says: silence is used to note exceptions but not defined in this file or its imports
- **address_space.py** `map_seed` — [HIGH] map_seed is referenced but not defined in this slice, leading to a NameError
  - says: map_seed is used in output but not defined in this file or its imports
- **address_space.py** `tier_census` — [HIGH] tier_census is referenced but not defined in this slice, leading to a NameError
  - says: tier_census is used in output but not defined in this file or its imports
- **address_space.py** `CAPACITY` — [HIGH] CAPACITY is referenced but not defined in this slice, leading to a NameError
  - says: CAPACITY is used in output formatting but not defined in this file or its imports
- **address_space.py** `_continuities` — [HIGH] _continuities is referenced but not defined in this slice, leading to a NameError
  - says: _continuities is used in calculations but not defined in this file or its imports
- **address_space.py** `WIDTHS` — [HIGH] WIDTHS is referenced but not defined in this slice, leading to a NameError
  - says: WIDTHS is used to format output but not defined in this file or its imports
- **address_space.py** `FIELDS` — [HIGH] FIELDS is referenced but not defined in this slice, leading to a NameError
  - says: FIELDS is used in a loop to iterate over field names but not defined in this file or its imports
- **address_space.py** `tier_census` — [HIGH] Returns hardcoded fallback values if `_tier_counts()` fails, contradicting its claim to represent live data.
  - says: The live upper-tier charting, as a sentence, read from `_tier_counts()`.
- **assay.py** `_check_hand_readings` — [MEDIUM] Converts hand_readings list to a dictionary with string keys before passing to _check_readings, which may not match expected input format
  - says: Raises AssayIntegrityError for invalid hand_readings, checks for None values, and delegates to _check_readings
- **allsweep.py** `est_faults` — [MEDIUM] est_faults is assigned but not added to the est dictionary
  - says: estate_faults is landed as its own top-level key
- **allsweep.py** `feats_on_disk` — [MEDIUM] counts only JSON files larger than 400 bytes
  - says: readfeats records holding text
- **allsweep.py** `tail` — [MEDIUM] full exception message is stored
  - says: exception message is cut to first 120 characters
- **allsweep.py** `Verifier("franchise rank agreement", ["rosetta.py", "--check"], RC_BROKEN)` — [MEDIUM] The Verifier is incorrectly marked as RC_BROKEN when it should be RC_FINDINGS.
  - says: The code is marked as BROKEN, but the comment indicates it should be a finding.
- **allsweep.py** `Verifier("the instrument", ["anchors.py"], RC_BROKEN)` — [MEDIUM] The Verifier is incorrectly marked as RC_BROKEN when it should be RC_FINDINGS.
  - says: The code is marked as BROKEN, but the comment indicates it should be a finding.
- **allsweep.py** `RC_FINDINGS` — [MEDIUM] never used in the code
  - says: used in the sum to determine exit code semantics
- **allsweep.py** `RC_BROKEN` — [MEDIUM] never used in the code
  - says: used in the sum to determine exit code semantics

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
