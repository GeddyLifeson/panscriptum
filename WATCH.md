# OVERWATCH

round 85  ·  last run 2026-08-26 13:59

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **0** of 212,637 inspected
- catalogued sources with no host: **15** Clockwork Angels (Rush), Curious DM Investigations (the Sharkin), Genuine Fantas
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**8 open** (2 high). Newest first.

- **endpoint.py** `detect` — [HIGH] detect is not defined in this slice, but is called in api_url and raw_url
  - says: detect(host) returns the mode and path for a host
- **chain.py** `work` — [HIGH] increments `unmatched` directly without proper locking
  - says: TALLIED LOCALLY, MERGED UNDER THE LOCK, for the same reason `local` exists.
- **drill.py** `catalog_matches_disk` — [MEDIUM] only checks that the catalog entries exist on disk (one direction)
  - says: Every chapter the catalog claims exists on disk, AND VICE VERSA — both directions.
- **descending_ladder.py** `shrink_report` — [MEDIUM] the `is_descent` flag is computed based on `from_m` and `to_m` but the function does not prevent a non-descent from being reported
  - says: `is_descent` is reported, NOT enforced.
- **descending_ladder.py** `shrink_report` — [MEDIUM] reports `from_m` as part of the trajectory but does not enforce `is_descent`
  - says: Full accounting of a mass-conserving descent. Returns the physics, and the verdict.
- **descending_ladder.py** `rung_for_length` — [MEDIUM] Returns (rung, name) for sizes within the range of the descending rungs, but returns (FOLD_RUNG, "Below the Fold") for sizes below the Planck length and (None, None) for sizes abov
  - says: Which descending rung does a given size belong to? Returns (rung, name).
- **dashboard.py** `jobs` — [MEDIUM] The function is supposed to handle reading and rolling data, but the code does not actually perform these operations; it only appends to an output list which is then returned. Howe
  - says: The long-running work, each as a fraction of its own honest denominator.
- **corpus_db.py** `con.execute` — [MEDIUM] inserts into source table with values including code, which is set to None if spine_code_for returns 'UNASSIGNED'
  - says: INSERT OR REPLACE INTO source VALUES (?,?,?,?,?,?,?,?,?)

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
