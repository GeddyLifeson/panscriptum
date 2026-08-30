# OVERWATCH

round 178  ·  last run 2026-08-29 21:47

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 276,686 inspected (deep scan as of round 175)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**2 open** (1 high). Newest first.

- **standards.py** `fab` — [HIGH] the fabrication rate or UNMEASURED state
  - says: sentences that survive the verbatim check
- **overnight.py** `main` — [MEDIUM] the code around it says it should be derived
  - says: the main function

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
