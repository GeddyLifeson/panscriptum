# OVERWATCH

round 212  ·  last run 2026-08-30 16:01

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 281,680 inspected (deep scan as of round 211)  — state\gpu_lane\slot.0.json — cannot stat
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**15 open** (3 high). Newest first.

- **genre.py** `classify_source` — [HIGH] Truncates the entry list in stored order, leading to incorrect classifications for some sources
  - says: Classifies a source based on its entries and returns genre, score, confidence, etc.
- **verify_math.py** `_chunk_key` — [HIGH] the key is not stable across runs
  - says: the same entity and passage still hit the same key IN A LATER PROCESS
- **verify_math.py** `priority` — [HIGH] excludes rows with own=0 and chars >= 2000
  - says: These are still read -- nothing here is dropped
- **workorders.py** `_fire` — [MEDIUM] reports a problem with the ledger chain when the chain is ok
  - says: reports a problem with the ledger chain
- **workorders.py** `_fire` — [MEDIUM] reports a problem with the ledger structure when there are no bad rows
  - says: reports a problem with the ledger structure
- **workorders.py** `resolve` — [MEDIUM] Attempts to close an order but does not properly handle the case where the write could not land, leading to potential confusion between 'no such order' and 'order already closed'.
  - says: Close an order: REMOVE it from the open file, append it to the paper trail.
- **workorders.py** `file_order` — [MEDIUM] Creates a new order or updates an existing one, but does not return the order directly. Instead, it returns the record if the write landed, otherwise None.
  - says: Open (or refresh) one work order. -> the order.
- **verify_math.py** `check` — [MEDIUM] checks if the code contains 'if span_min >= 40:'
  - says: the counters-moving standard is not gated behind a history-length check
- **verify_math.py** `qualifier_compatible` — [MEDIUM] returns False for two DC continuities
  - says: two DC continuities are never compatible
- **tuning.py** `workers` — [MEDIUM] The worker count to use, but inverts the requested value when a request is made.
  - says: The worker count to actually use.
- **tiers.py** `deliberate_joins` — [MEDIUM] returns a sorted list of tuples with shared data, but the actual implementation does not apply the `[:3]` slice
  - says: THE WHOLE SHARED LIST. This returned `shared.get((a, b), [])[:3]`
- **retry_synthesis.py** `save_side` — [MEDIUM] The function save_side is called but its implementation is not provided in the given code slice, leading to a potential runtime error or undefined behavior.
  - says: Take the MERGED mapping back, so this run's own tally counts what is actually on disk rather than only what this process rescued -- see `save_side`. The second half of that return says whether it reached disk at all; a rescue that did not land must not print like one that did, because nothing re-runs the model call behind it.
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops
- **foreman.py** `kill_stalled` — [MEDIUM] kill stalled jobs that can be restarted, and escalate those that cannot
  - says: kill stalled jobs
- **drill.py** `silence.write_json` — [MEDIUM] writes to a file that can be read by other processes, but the code around it suggests that the file should be written in a way that ensures readers see the complete data
  - says: this project's stated one correct way to land a shared file

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
