# OVERWATCH

round 155  ·  last run 2026-08-29 10:55

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **0** of 273,179 inspected (deep scan as of round 151)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**4 open** (1 high). Newest first.

- **catalogue_models.py** `sweep` — [HIGH] sweep() does not actually perform any sweeping or cleaning of data, but instead generates a payload and writes it to a JSON file
  - says: sweep(config_path=None, workers=6)
- **canon_backup.py** `snapshot` — [MEDIUM] return the path of the snapshot
  - says: create a new snapshot
- **backfill.py** `lead` — [MEDIUM] The function is used to extract a lead sentence, but the code inside the function is not provided, making it impossible to verify its actual behavior.
  - says: A lead sentence has length and terminal punctuation. Template residue has neither.
- **assay.py** `used` — [MEDIUM] Used to filter scores based on weights, but the variable is not properly initialized in all cases.
  - says: Used to filter scores based on weights.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
