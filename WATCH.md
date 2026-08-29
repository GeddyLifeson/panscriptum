# OVERWATCH

round 158  ·  last run 2026-08-29 13:12

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **0** of 273,738 inspected (deep scan as of round 157)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**2 open** (1 high). Newest first.

- **estate.py** `inspect` — [HIGH] inspect a file path, but the function is not defined in this slice
  - says: inspect a file path
- **assay.py** `denom` — [MEDIUM] sum of weights over applicable axes or 1.0
  - says: sum of weights over applicable axes

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
