# OVERWATCH

round 168  ·  last run 2026-08-29 17:13

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 274,390 inspected (deep scan as of round 163)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**7 open** (0 high). Newest first.

- **escalation.py** `_read_halt_raw` — [MEDIUM] returns a dict or None, but the code does not handle cases where the JSON is invalid or malformed
  - says: IT ALWAYS RETURNS None OR A DICT
- **drill.py** `coverage_totals_never_exceed_their_entry_count` — [MEDIUM] Checks that states do not sum PAST the entry count (the overflow direction), but the docstring mentions this was previously a completeness check
  - says: No source's states may sum PAST its own entry count. One direction, and only one.
- **drill.py** `catalog_matches_disk` — [MEDIUM] Only checks that the catalog entries exist on disk (one direction), not that all disk files are cataloged
  - says: Every chapter the catalog claims exists on disk, AND VICE VERSA — both directions.
- **drill.py** `LA.blast_reset` — [MEDIUM] The function is called but the code later checks if LA._BLAST['patches'] == 0, which may not be accurate due to the way the budget is being tracked.
  - says: LA.blast_reset() clears the WHOLE budget, both halves of it
- **drill.py** `LA._BLAST` — [MEDIUM] The code checks if LA._BLAST['patches'] != 0 after a staged dry run, but the actual behavior is that the budget is not being tracked correctly, leading to incorrect assertions.
  - says: LA._BLAST is a dictionary that tracks the budget
- **drill.py** `LA.t_propose_patch` — [MEDIUM] The function is called with apply=True, but the code checks if the patch was not applied (r.get("applied") is not False), which contradicts the apply=True parameter.
  - says: r = LA.t_propose_patch(rel, "MARKER-ONCE", "MARKER-TWICE", why="drill", apply=True)
- **drill.py** `LA.t_propose_patch` — [MEDIUM] The function is called with apply=False, but the code later checks if the patch was applied (r.get("applied") is not False), which contradicts the apply=False parameter.
  - says: staged = LA.t_propose_patch(rel, "MARKER-ONCE", "MARKER-TWICE", why="drill", apply=False)

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
