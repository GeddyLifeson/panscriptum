# OVERWATCH

round 116  ·  last run 2026-08-28 14:10

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **1** of 268,382 inspected (deep scan as of round 115)  — handoff\run36\sweep_plan.json — malformed JSON: Extra data: line 213 column 1 (char 3102)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**3 open** (2 high). Newest first.

- **genre.py** `classify_source` — [HIGH] Uses a truncated ranked list for confidence calculation, leading to inflated confidence scores
  - says: Classifies a source based on its entries, using all scored genres for confidence calculation
- **generate.py** `compress_store.store` — [HIGH] is called but exceptions are caught and handled without raising
  - says: now RAISES when `silence.replace_retry` cannot land the blob
- **drill.py** `_landing_nothing_is_not_success` — [MEDIUM] a run that was refused five times running was indistinguishable, to the caller closing the order, from work actually done
  - says: a run that proposed patches and landed NONE cannot report success

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
