# OVERWATCH

round 83  ·  last run 2026-08-26 11:23

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **0** of 198,069 inspected
- catalogued sources with no host: **15** Clockwork Angels (Rush), Curious DM Investigations (the Sharkin), Genuine Fantas
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**5 open** (2 high). Newest first.

- **completeness.py** `api_base` — [HIGH] Hardcodes `/api.php` and returns None for RAW/DEAD hosts, which is a different fact from "the probe failed".
  - says: Through `endpoint.api_url`, never hardcoded, for the reason `host_reachable` states below: `/api.php` is a Fandom assumption and Wikipedia serves `/w/api.php`. 
- **chain.py** `work` — [HIGH] increments `unmatched` directly without proper locking
  - says: TALLIED LOCALLY, MERGED UNDER THE LOCK, for the same reason `local` exists.
- **corpus_db.py** `con.execute` — [MEDIUM] inserts into source table with values including code, which is set to None if spine_code_for returns 'UNASSIGNED'
  - says: INSERT OR REPLACE INTO source VALUES (?,?,?,?,?,?,?,?,?)
- **compress_store.py** `store` — [MEDIUM] returns raw_bytes length and compressed_bytes length as integers, not the actual byte values
  - says: Compress `text`, write it to compressed_dir keyed by content hash, and return {"hash":..., "path":..., "codec":..., "raw_bytes":..., "compressed_bytes":...}
- **cleanup.py** `changed` — [MEDIUM] sometimes not set when a thin description is marked
  - says: tracking whether any changes were made to a record

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
