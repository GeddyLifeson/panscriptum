# OVERWATCH

round 45  ·  last run 2026-08-23 15:56

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 58,348 inspected
- catalogued sources with no host: **17** Arcanum Worlds (Odyssey of the Dragonlords), Clockwork Angels (Rush), Curious DM
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**3 open** (1 high). Newest first.

- **assay.py** `SIGMA_MAX` — [HIGH] SIGMA_MAX is set to 9.9 / sqrt(12), which is approximately 2.86, but the comment incorrectly states it as the maximum entropy dispersion for the scale, which is correct, yet the co
  - says: The maximum standard deviation for any axis, derived from a uniform prior over 0.0-9.9.
- **assay.py** `FACULTY_WEIGHTS` — [MEDIUM] FACULTY_WEIGHTS is defined but never used in the code. The weights for the faculties are instead used via the global WEIGHTS dictionary, which includes them, but FACULTY_WEIGHTS it
  - says: The FACULTY_WEIGHTS dictionary contains the weights for the faculties, which are set to 1/11 each.
- **anchors.py** `vector_score` — [MEDIUM] Returns 10.0 for any input >= 17, but the LADDER_RUNGS is 17, so input 17 should return 10.0, which it does. However, the function is called with 17 in The Seat of the Creator, whi
  - says: Vector on the 0-10 decimal scale, derived from the Ladder's own height. No new quantity.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
