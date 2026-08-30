# OVERWATCH

round 177  ·  last run 2026-08-29 21:24

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 276,686 inspected (deep scan as of round 175)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**3 open** (1 high). Newest first.

- **secondopinion.py** `mine_says` — [HIGH] is never called in the code slice
  - says: returns the same questions, asked by code this project did not write
- **reference.py** `shelfmark` — [MEDIUM] generates a shelfmark based on tier_key and lower_rungs, but the code does not correctly handle the mapping of the RUNGS tuple to the upper and lower parts
  - says: The charter's canonical Shelfmark
- **overnight.py** `main` — [MEDIUM] the code around it says it should be derived
  - says: the main function

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
