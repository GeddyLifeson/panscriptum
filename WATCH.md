# OVERWATCH

round 169  ·  last run 2026-08-29 17:50

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **0** of 275,602 inspected
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**8 open** (1 high). Newest first.

- **generate.py** `generate_job` — [HIGH] does not exist in this code slice
  - says: generates a job's text
- **gpu_lane.py** `_take_slot` — [MEDIUM] Attempts to create a file with O_CREAT|O_EXCL but may return None on failure without proper error handling
  - says: Claim one of MAX_SLOTS leases, or return None if they are all live
- **gpu_lane.py** `_write_claim` — [MEDIUM] Returns a boolean indicating success, but the actual replacement is handled by replace_retry which may not be properly handled in some cases
  - says: Write a claim to a file, ensuring it's replaced
- **generate.py** `_PG` — [MEDIUM] used as a variable name for the prose_gate module, not the module itself
  - says: imported module for prose gate checks
- **generate.py** `call_ollama` — [MEDIUM] used as a variable name for the result of the API call, not the function itself
  - says: calls the Ollama API to generate text based on a prompt
- **escalation.py** `_read_halt_raw` — [MEDIUM] returns a dict or None, but the code does not handle cases where the JSON is invalid or malformed
  - says: IT ALWAYS RETURNS None OR A DICT
- **drill.py** `coverage_totals_never_exceed_their_entry_count` — [MEDIUM] Checks that states do not sum PAST the entry count (the overflow direction), but the docstring mentions this was previously a completeness check
  - says: No source's states may sum PAST its own entry count. One direction, and only one.
- **drill.py** `catalog_matches_disk` — [MEDIUM] Only checks that the catalog entries exist on disk (one direction), not that all disk files are cataloged
  - says: Every chapter the catalog claims exists on disk, AND VICE VERSA — both directions.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
