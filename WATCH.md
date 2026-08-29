# OVERWATCH

round 166  ·  last run 2026-08-29 16:20

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 274,390 inspected (deep scan as of round 163)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**2 open** (1 high). Newest first.

- **catalogue_web.py** `record_path` — [HIGH] the function is used but never defined in this file or its imports
  - says: with the cap gone the raw join would look for the un-truncated name, miss the record this module itself wrote under the cap, and write a SECOND one beside it --
- **cleanup.py** `changed` — [MEDIUM] set to True in multiple branches but not always initialized
  - says: tracking whether any changes were made to a record

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
