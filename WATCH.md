# OVERWATCH

round 89  ·  last run 2026-08-26 19:00

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 212,637 inspected
- catalogued sources with no host: **10** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**14 open** (6 high). Newest first.

- **ingest_doc.py** `P.write_record_catalogue` — [HIGH] write_record_catalogue returns whether the rename actually landed, but the code discards the result and assumes it's successful
  - says: write_record_catalogue returns whether the rename actually landed
- **gpu_lane.py** `foreground_active` — [HIGH] Returns True if any foreground claim exists, even if it's expired
  - says: Is any LIVE foreground claim outstanding?
- **genre.py** `classify_source` — [HIGH] Truncates the entry list in stored order, changing the answer for 7 of 210 sources
  - says: Classify one source from its own catalogued entries.
- **generate.py** `generate_job` — [HIGH] generate_job is not defined in this slice and is used without being imported or defined here
  - says: generate_job is supposed to generate text for a job
- **foreman.py** `silence.replace_retry` — [HIGH] discards the boolean that reports the denied rename
  - says: CHECK THE RETURN THIS COMMENT ALREADY WARNS ABOUT (run #19). The paragraph above names the exact hazard -- a torn or stale write here silently discards overwatc
- **endpoint.py** `detect` — [HIGH] detect is not defined in this slice, but is called in api_url and raw_url
  - says: detect(host) returns the mode and path for a host
- **hostcheck.py** `fixed` — [MEDIUM] fixed is being used to store rejected hosts, but the code is not correctly handling the case where a host is rejected and needs to be recorded as a finding.
  - says: A rejected host is a FINDING and is written down.
- **gpu_lane.py** `_alive` — [MEDIUM] Returns False for unparseable PIDs, which contradicts the docstring's claim that unparseable PIDs are an 'unknown answer' and should be treated as ALIVE.
  - says: Is this PID still running? A dead holder's lease is broken immediately.
- **foreman.py** `codewatch.exit_if_stale` — [MEDIUM] Exits if the process is stale
  - says: Exits with rc=17 on purpose
- **foreman.py** `kill_stalled_job` — [MEDIUM] The function attempts to kill stalled jobs but has a flawed logic in determining which jobs can be restarted, potentially leading to incorrect kills or failures to kill jobs that s
  - says: A job that is UP and writing nothing is worse than a job that is down.
- **feats.py** `alive` — [MEDIUM] Queries the API with a specific request but does not actually check if the host is alive; returns a boolean based on the API response which may not reflect actual host availability
  - says: Check if a host is alive by querying its API
- **estate.py** `shutil.disk_usage` — [MEDIUM] disk check failed
  - says: disk check failed
- **drill.py** `coverage_totals_never_exceed_their_entry_count` — [MEDIUM] the code did an overflow check while the docstring promised a completeness check
  - says: No source's states may sum PAST its own entry count. One direction, and only one.
- **corpus_db.py** `con.execute` — [MEDIUM] inserts into source table with values including code, which is set to None if spine_code_for returns 'UNASSIGNED'
  - says: INSERT OR REPLACE INTO source VALUES (?,?,?,?,?,?,?,?,?)

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
