# OVERWATCH

round 113  ·  last run 2026-08-28 12:45

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **1** of 267,074 inspected  — handoff\run36\sweep_plan.json — malformed JSON: Extra data: line 213 column 1 (char 3102)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**4 open** (1 high). Newest first.

- **completeness.py** `audit` — [HIGH] audit every source that happens to be on fandom
  - says: audit every source the library knows of
- **corpus_db.py** `serve_command` — [MEDIUM] returns a string that includes the path to a datasette.json file, but does not ensure that the file actually exists or is correctly formatted
  - says: -> the exact command line that serves the index, with the config this module wrote.
- **corpus_db.py** `evidence_limit` — [MEDIUM] now inert, does not truncate
  - says: used to slice `files[:evidence_limit]`
- **compress_store.py** `store` — [MEDIUM] returns a dictionary with lengths instead of the actual bytes
  - says: Compress `text`, write it to compressed_dir keyed by content hash, and return

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
