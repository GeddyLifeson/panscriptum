# OVERWATCH

round 87  ·  last run 2026-08-26 17:14

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 212,637 inspected
- catalogued sources with no host: **10** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**10 open** (3 high). Newest first.

- **generate.py** `generate_job` — [HIGH] generate_job is not defined in this slice and is used without being imported or defined here
  - says: generate_job is supposed to generate text for a job
- **foreman.py** `silence.replace_retry` — [HIGH] discards the boolean that reports the denied rename
  - says: CHECK THE RETURN THIS COMMENT ALREADY WARNS ABOUT (run #19). The paragraph above names the exact hazard -- a torn or stale write here silently discards overwatc
- **endpoint.py** `detect` — [HIGH] detect is not defined in this slice, but is called in api_url and raw_url
  - says: detect(host) returns the mode and path for a host
- **foreman.py** `codewatch.exit_if_stale` — [MEDIUM] Exits if the process is stale
  - says: Exits with rc=17 on purpose
- **foreman.py** `kill_stalled_job` — [MEDIUM] The function attempts to kill stalled jobs but has a flawed logic in determining which jobs can be restarted, potentially leading to incorrect kills or failures to kill jobs that s
  - says: A job that is UP and writing nothing is worse than a job that is down.
- **feats.py** `alive` — [MEDIUM] Queries the API with a specific request but does not actually check if the host is alive; returns a boolean based on the API response which may not reflect actual host availability
  - says: Check if a host is alive by querying its API
- **estate.py** `shutil.disk_usage` — [MEDIUM] disk free
  - says: disk free
- **estate.py** `shutil.disk_usage` — [MEDIUM] disk check failed
  - says: disk check failed
- **drill.py** `coverage_totals_never_exceed_their_entry_count` — [MEDIUM] the code did an overflow check while the docstring promised a completeness check
  - says: No source's states may sum PAST its own entry count. One direction, and only one.
- **corpus_db.py** `con.execute` — [MEDIUM] inserts into source table with values including code, which is set to None if spine_code_for returns 'UNASSIGNED'
  - says: INSERT OR REPLACE INTO source VALUES (?,?,?,?,?,?,?,?,?)

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
