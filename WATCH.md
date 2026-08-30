# OVERWATCH

round 176  ·  last run 2026-08-29 20:54

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 276,686 inspected (deep scan as of round 175)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**2 open** (0 high). Newest first.

- **rosetta.py** `refine` — [MEDIUM] refines the rosetta data by applying filters and updating the data structure
  - says: drop scale rows that name nothing this library catalogues
- **overnight.py** `main` — [MEDIUM] the code around it says it should be derived
  - says: the main function

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
