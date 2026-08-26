# OVERWATCH

round 84  ·  last run 2026-08-26 12:33

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 198,069 inspected
- catalogued sources with no host: **15** Clockwork Angels (Rush), Curious DM Investigations (the Sharkin), Genuine Fantas
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major
- NOT RUNNING: **0** read.py

## What the model found in the code

**4 open** (2 high). Newest first.

- **completeness.py** `api_base` — [HIGH] Hardcodes `/api.php` and returns None for RAW/DEAD hosts, which is a different fact from "the probe failed".
  - says: Through `endpoint.api_url`, never hardcoded, for the reason `host_reachable` states below: `/api.php` is a Fandom assumption and Wikipedia serves `/w/api.php`. 
- **chain.py** `work` — [HIGH] increments `unmatched` directly without proper locking
  - says: TALLIED LOCALLY, MERGED UNDER THE LOCK, for the same reason `local` exists.
- **cosmology_graph.py** `components` — [MEDIUM] clusters at weight >= threshold, but the threshold is applied to clusters, not pairs
  - says: CANDIDATE CLUSTERS at weight >= {args.threshold} : {len(comps)}
- **corpus_db.py** `con.execute` — [MEDIUM] inserts into source table with values including code, which is set to None if spine_code_for returns 'UNASSIGNED'
  - says: INSERT OR REPLACE INTO source VALUES (?,?,?,?,?,?,?,?,?)

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
