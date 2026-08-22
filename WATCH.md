# OVERWATCH

round 2  ·  last run 2026-08-22 14:42

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 0 inspected
- catalogued sources with no host: **32** A Plethora of Paladins, Arcanum Worlds (Odyssey of the Dragonlords), Clockwork A
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major
- PHASES NAMED BY THE RUNNER WITH NO IMPLEMENTATION: **4** cosmology, history, shelve, write

## What the model found in the code

**2 open** (1 high). Newest first.

- **assay.py** `interval` — [HIGH] The while loop condition checks `any(abs(v - centre) > interval for v in vals)`, but the loop body increases `interval` by 0.01 each time. However, the `interval` is rounded to 2 d
  - says: The interval must cover every signed reading, enforced by a while loop that increases interval until all readings are within bounds.
- **assay.py** `SIGMA_MAX` — [MEDIUM] SIGMA_MAX is defined as 9.9 / sqrt(12), which is correct for the standard deviation of a uniform distribution over [0.0, 9.9], but this value is used as a hard ceiling for uncertai
  - says: The maximum standard deviation for any axis, derived from a uniform prior over 0.0-9.9.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
