# OVERWATCH

round 197  ·  last run 2026-08-30 08:15

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 279,878 inspected (deep scan as of round 193)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**14 open** (2 high). Newest first.

- **overnight.py** `start` — [HIGH] calls a function named start that is not defined in this slice
  - says: start a service with given arguments
- **mutate.py** `_lock_release` — [HIGH] does not exist in the code
  - says: release a lock previously acquired by `_lock_acquire`
- **overnight.py** `busy` — [MEDIUM] A list of statuses that are considered busy, but the code uses 'busy' to check for busy states and then proceeds to sleep, which is correct. However, the code may have a logical error in the condition where it checks 'busy and snap['cycle_seconds'] < MIN_CYCLE_SECONDS' which could be misinterpreted if 'busy' is not properly defined or if the logic is flawed.
  - says: A list of statuses that are considered busy
- **overnight.py** `preflight` — [MEDIUM] Returns (0, False) when preflight fails, but does not properly handle all failure cases or correctly identify blocking checks
  - says: Returns (n_failing_checks, blocking). Only corrupted source blocks.
- **overnight.py** `coverage_snapshot` — [MEDIUM] This cycle's coverage figures, or `{
  - says: This cycle's coverage figures, or `{
- **overnight.py** `os.path.samefile` — [MEDIUM] check if script is the same file as the one in src, but the script is constructed with psutil.Process(pid).cwd() which may not be the same as the original script path
  - says: check if script is the same file as the one in src
- **navtree.py** `silence.write_json` — [MEDIUM] write_json is called with a path that is not the correct one for the operation
  - says: write_json
- **magnitude.py** `assay_entity` — [MEDIUM] returns a deferred status when the anchor is not in the ladder or when the ceiling is not met
  - says: assays an entity by trying different methods
- **local_agent.py** `full.lower().endswith(('.yaml', '.yml'))` — [MEDIUM] Checks for .yaml or .yml but uses the same variable name as the JSON check, which could lead to confusion or errors in logic
  - says: Check if the file ends with .yaml or .yml
- **local_agent.py** `full.lower().endswith(('.yaml', '.yml'))` — [MEDIUM] Checks for .yaml or .yml but uses the same logic as the JSON check, which may not handle case sensitivity correctly
  - says: Check if the file ends with .yaml or .yml
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops
- **hostcheck.py** `adopt` — [MEDIUM] Finds a host for sources that have none, but the function's logic may not correctly handle all cases, especially when the host is not found or when there are no entries for a source.
  - says: Find a host for every catalogued source that has none.
- **foreman.py** `kill_stalled` — [MEDIUM] kill stalled jobs that can be restarted, and escalate those that cannot
  - says: kill stalled jobs
- **drill.py** `silence.write_json` — [MEDIUM] writes to a file that can be read by other processes, but the code around it suggests that the file should be written in a way that ensures readers see the complete data
  - says: this project's stated one correct way to land a shared file

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
