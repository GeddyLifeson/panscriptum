# OVERWATCH

round 114  ·  last run 2026-08-28 13:06

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **1** of 267,074 inspected  — handoff\run36\sweep_plan.json — malformed JSON: Extra data: line 213 column 1 (char 3102)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**9 open** (4 high). Newest first.

- **descending_ladder.py** `rung_for_length` — [HIGH] Returns (rung, name) for sizes within the descending ladder, but returns (FOLD_RUNG, "Below the Fold") for sizes below the Planck length and (None, None) for sizes above the descen
  - says: Which descending rung does a given size belong to? Returns (rung, name).
- **dashboard.py** `movement` — [HIGH] calls a function named movement that may not exist
  - says: returns a section element with movement data
- **cosmology_graph.py** `components` — [HIGH] clusters at weight >= threshold, but the threshold is applied to pairs, not clusters
  - says: CANDIDATE CLUSTERS at weight >= {args.threshold} : {len(comps)}
- **completeness.py** `audit` — [HIGH] audit every source that happens to be on fandom
  - says: audit every source the library knows of
- **dashboard.py** `movement` — [MEDIUM] The code calculates deltas without considering that some counters may reset to zero, leading to negative deltas that are incorrectly reported as movement rather than resets.
  - says: A COUNTER THAT FELL IS NOT A COUNTER THAT MOVED.
- **dashboard.py** `movement` — [MEDIUM] Returns a list of metrics with their current values and deltas, but the delta calculation does not account for potential resets due to counter discontinuities, which can incorrectl
  - says: What has CHANGED, not what the level is.
- **corpus_db.py** `serve_command` — [MEDIUM] returns a string that includes the path to a datasette.json file, but does not ensure that the file actually exists or is correctly formatted
  - says: -> the exact command line that serves the index, with the config this module wrote.
- **corpus_db.py** `evidence_limit` — [MEDIUM] now inert, does not truncate
  - says: used to slice `files[:evidence_limit]`
- **compress_store.py** `store` — [MEDIUM] returns a dictionary with lengths instead of the actual bytes
  - says: Compress `text`, write it to compressed_dir keyed by content hash, and return

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
