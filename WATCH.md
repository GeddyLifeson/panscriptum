# OVERWATCH

round 174  ·  last run 2026-08-29 20:00

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **0** of 275,602 inspected (deep scan as of round 169)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**2 open** (0 high). Newest first.

- **overnight.py** `main` — [MEDIUM] the code around it says it should be derived
  - says: the main function
- **navtree.py** `max` — [MEDIUM] returns the maximum element based on a key, but the comment indicates it should handle ties deterministically by using the name as a secondary key
  - says: returns the maximum element based on a key

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
