# OVERWATCH

round 86  ·  last run 2026-08-26 15:18

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 212,637 inspected
- catalogued sources with no host: **10** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**8 open** (1 high). Newest first.

- **endpoint.py** `detect` — [HIGH] detect is not defined in this slice, but is called in api_url and raw_url
  - says: detect(host) returns the mode and path for a host
- **estate.py** `shutil.disk_usage` — [MEDIUM] disk free
  - says: disk free
- **estate.py** `shutil.disk_usage` — [MEDIUM] disk check failed
  - says: disk check failed
- **drill.py** `coverage_totals_never_exceed_their_entry_count` — [MEDIUM] the code did an overflow check while the docstring promised a completeness check
  - says: No source's states may sum PAST its own entry count. One direction, and only one.
- **drill.py** `catalog_matches_disk` — [MEDIUM] only checks that the catalog entries exist on disk (one direction)
  - says: Every chapter the catalog claims exists on disk, AND VICE VERSA — both directions.
- **descending_ladder.py** `shrink_report` — [MEDIUM] the `is_descent` flag is computed based on `from_m` and `to_m` but the function does not prevent a non-descent from being reported
  - says: `is_descent` is reported, NOT enforced.
- **descending_ladder.py** `shrink_report` — [MEDIUM] reports `from_m` as part of the trajectory but does not enforce `is_descent`
  - says: Full accounting of a mass-conserving descent. Returns the physics, and the verdict.
- **corpus_db.py** `con.execute` — [MEDIUM] inserts into source table with values including code, which is set to None if spine_code_for returns 'UNASSIGNED'
  - says: INSERT OR REPLACE INTO source VALUES (?,?,?,?,?,?,?,?,?)

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
