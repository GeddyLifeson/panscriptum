# OVERWATCH

round 164  ·  last run 2026-08-29 15:34

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **0** of 274,390 inspected (deep scan as of round 163)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**1 open** (0 high). Newest first.

- **catalogue_aurora.py** `roll_landed` — [MEDIUM] is assigned the result of silence.write_json() which writes to disk
  - says: would silently re-parse sources it had already, correctly, catalogued. Found by the run #33 sweep, same batch as the record-level fix above.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
