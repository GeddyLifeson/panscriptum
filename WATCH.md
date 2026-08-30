# OVERWATCH

round 202  ·  last run 2026-08-30 10:39

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 280,497 inspected (deep scan as of round 199)  — state\gpu_lane\slot.2.json — cannot stat
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**12 open** (1 high). Newest first.

- **resync_roll.py** `main` — [HIGH] the exit code is not used as the scheduler looks at the return value of main()
  - says: the exit code is the number the scheduler actually looks at
- **retry_synthesis.py** `save_side` — [MEDIUM] The function save_side is called but its implementation is not provided in the given code slice, leading to a potential runtime error or undefined behavior.
  - says: Take the MERGED mapping back, so this run's own tally counts what is actually on disk rather than only what this process rescued -- see `save_side`. The second half of that return says whether it reached disk at all; a rescue that did not land must not print like one that did, because nothing re-runs the model call behind it.
- **resonance.py** `dominates` — [MEDIUM] returns False when neither dominates, which is the condition for incomparable pairs
  - says: answers False for both of those for an unrelated reason
- **repass_bands.py** `PL.write_record` — [MEDIUM] The code appends to `denied` and prints a message when the write fails, which aligns with the claim that denials are counted and printed.
  - says: AND THE DENIAL IS COUNTED, NOT ONLY PRINTED (order 6e7bebc7c601). The gate above holds, but a denial reached no summary line and no exit code
- **repass_bands.py** `PL.write_record` — [MEDIUM] The code appends to `touched` regardless of whether the write succeeded or failed, which contradicts the claim that it ignores the return value.
  - says: GATE ON THE WRITE. `write_record` returns whether the write LANDED; this ignored it and appended to `touched` regardless, so the run's closing "APPLIED. N rewritten" counted sources whose file was never modified.
- **reference.py** `shelfmark` — [MEDIUM] The function returns a shelfmark that includes both upper and lower rungs, but the code may not correctly handle cases where the lengths of upper and lower do not match the expected RUNGS length
  - says: The charter's canonical Shelfmark
- **read.py** `set_transport` — [MEDIUM] sets the transport method but the argument is not validated against the allowed choices
  - says: sets the transport method based on the argument
- **pipeline.py** `write_record` — [MEDIUM] The function is called without verifying that the write actually reached the disk
  - says: A batch is done only when every entry in it carries a result AND the write that carries those results actually reached the disk
- **overnight.py** `busy` — [MEDIUM] A list of statuses that are considered busy, but the code uses 'busy' to check for busy states and then proceeds to sleep, which is correct. However, the code may have a logical error in the condition where it checks 'busy and snap['cycle_seconds'] < MIN_CYCLE_SECONDS' which could be misinterpreted if 'busy' is not properly defined or if the logic is flawed.
  - says: A list of statuses that are considered busy
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops
- **foreman.py** `kill_stalled` — [MEDIUM] kill stalled jobs that can be restarted, and escalate those that cannot
  - says: kill stalled jobs
- **drill.py** `silence.write_json` — [MEDIUM] writes to a file that can be read by other processes, but the code around it suggests that the file should be written in a way that ensures readers see the complete data
  - says: this project's stated one correct way to land a shared file

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
