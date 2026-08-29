# OVERWATCH

round 132  ·  last run 2026-08-28 23:12

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **1** of 269,929 inspected (deep scan as of round 127)  — handoff\run36\sweep_plan.json — malformed JSON: Extra data: line 213 column 1 (char 3102)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major
- NOT RUNNING: **0** overnight.py
- NOT RUNNING: **0** pipeline.py

## What the model found in the code

**4 open** (0 high). Newest first.

- **catalogue_aurora.py** `roll_landed` — [MEDIUM] is assigned the result of silence.write_json, which writes to disk
  - says: would silently re-parse sources it had already, correctly, catalogued. Found by the run #33 sweep, same batch as the record-level fix above.
- **catalogue_aurora.py** `parse_folder` — [MEDIUM] does not collect dropped entries as described
  - says: collects what collapsed
- **cascade_bridge.py** `prove` — [MEDIUM] Send one tiny call to EVERY bucket and record which actually answer, but the function's docstring mentions a specific issue with the 'max_attempts=1' parameter and the 'served' par
  - says: Send one tiny call to EVERY bucket and record which actually answer.
- **address_space.py** `HASH_BYTES` — [MEDIUM] Hardcoded to 16 bytes regardless of the calculated value
  - says: Derived from the offsets, floored at the historical 16 bytes so today's addresses are unchanged.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
