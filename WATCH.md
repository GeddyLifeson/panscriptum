# OVERWATCH

round 182  ·  last run 2026-08-29 23:50

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 277,455 inspected (deep scan as of round 181)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major
- NOT RUNNING: **0** overnight.py

## What the model found in the code

**9 open** (5 high). Newest first.

- **autostart.py** `installed_state` — [HIGH] not defined in the slice
  - says: returns the state of the VBS file
- **assay.py** `instrument` — [HIGH] Returns 'uninstrumented — no faculties on file' when no worksheet is provided, which is a refusal rather than a conversion.
  - says: Deterministic conversion to the six faculties, 1-30, plus Transcendence Grade.
- **assay.py** `calibration_report` — [HIGH] the loop touches nothing shared and does not modify SIGMA_BY_ATTESTATION
  - says: The loop used to assign each trial sigma into SIGMA_BY_ATTESTATION and put it back in a `finally`
- **assay.py** `calibration_report` — [HIGH] asserts stored constants by comparing to CHARTER_KENSHIRO_INTERVAL and CHARTER_KENSHIRO_DECIMAL
  - says: Re-DERIVE the charter's published numbers; never assert a stored constant.
- **address_space.py** `assign` — [HIGH] assign is called with a designation and a tier stack, but the second argument is a continuity-group integer instead of a tier stack
  - says: assign(desig, tiers.get(src) or {})
- **autostart.py** `start_supervisor` — [MEDIUM] starts the supervisor even if it's not definitely not running
  - says: starts the supervisor if it's not running
- **assay.py** `_check_scores` — [MEDIUM] Validates scores against the FULL WEIGHTS table, but the comment suggests it only validates against the axes FACULTY_READS consumes, leading to confusion.
  - says: Validated against the FULL WEIGHTS table rather than only the axes FACULTY_READS consumes
- **assay.py** `_rho_source` — [MEDIUM] constructs fallback reason
  - says: provenance stamp for correlations
- **assay.py** `RHO_FALLBACK_REASON` — [MEDIUM] announces fallback reason
  - says: guard against missing matrix

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
