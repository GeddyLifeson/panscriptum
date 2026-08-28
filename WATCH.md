# OVERWATCH

round 119  ·  last run 2026-08-28 16:22

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 268,382 inspected (deep scan as of round 115)  — handoff\run36\sweep_plan.json — malformed JSON: Extra data: line 213 column 1 (char 3102)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major
- NOT RUNNING: **0** pipeline.py

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
- **ingest_doc.py** `state` — [MEDIUM] reset to 0, found to 0 on exception
  - says: tracking progress
- **hostcheck.py** `add` — [MEDIUM] Adds a host to the speculative list if not in grounded, but the code uses 'spec' and 'grounded' in a way that may not align with the function's name
  - says: Adds a host to either the speculative or grounded list
- **dashboard.py** `state` — [MEDIUM] Imports standards and applies check, but may return empty list on error
  - says: Collects state data including standards
- **dashboard.py** `movement` — [MEDIUM] Calculates deltas based on the oldest sample within a moving window, but the comment and docstring suggest it should compute changes against the most recent sample in the window.
  - says: What has CHANGED, not what the level is.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
