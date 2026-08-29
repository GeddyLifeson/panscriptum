# OVERWATCH

round 162  ·  last run 2026-08-29 14:50

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 273,738 inspected (deep scan as of round 157)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**1 open** (0 high). Newest first.

- **snapshot.py** `restore` — [MEDIUM] Copies a snapshot into a directory, but the function's name and comment suggest it should be restoring from a snapshot, not copying into a directory
  - says: Copy a snapshot back. `into` defaults to the live tree -- pass a temp dir to test it.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
