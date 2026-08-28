# OVERWATCH

round 120  ·  last run 2026-08-28 17:15

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 268,382 inspected (deep scan as of round 115)  — handoff\run36\sweep_plan.json — malformed JSON: Extra data: line 213 column 1 (char 3102)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**8 open** (4 high). Newest first.

- **identity.py** `epoch_of` — [HIGH] return an empty string when the probe is unavailable or the response is unparsable
  - says: determine the epoch of a sentence
- **identity.py** `_ask` — [HIGH] swallow all exceptions and return None
  - says: ask a question and return the answer
- **genre.py** `classify_source` — [HIGH] Uses a truncated ranked list for confidence calculation, leading to inflated confidence scores
  - says: Classifies a source based on its entries, using all scored genres for confidence calculation
- **generate.py** `compress_store.store` — [HIGH] is called but exceptions are caught and handled without raising
  - says: now RAISES when `silence.replace_retry` cannot land the blob
- **magnitude.py** `slice_census` — [MEDIUM] Calculates totals but does not account for unread characters or sentences per axis, which are critical for understanding which axes had incomplete evidence processing.
  - says: How much of the evidence a split sheet was actually read from.
- **local_agent.py** `modname` — [MEDIUM] derive module name from file path but case-insensitively
  - says: derive module name from file path
- **liveness.py** `used_local` — [MEDIUM] used_local is a dictionary mapping module names to sets of names used in that module
  - says: used_local is a set of names used in the current module
- **ingest_doc.py** `state` — [MEDIUM] reset to 0, found to 0 on exception
  - says: tracking progress

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
