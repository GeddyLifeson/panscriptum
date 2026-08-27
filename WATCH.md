# OVERWATCH

round 92  ·  last run 2026-08-26 21:20

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 230,350 inspected
- catalogued sources with no host: **10** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major
- NOT RUNNING: **0** read.py

## What the model found in the code

**16 open** (12 high). Newest first.

- **overnight.py** `start` — [HIGH] Calls a function that does not exist in the current scope
  - says: Starts a background process with the given command and log file
- **overnight.py** `_cmd_is_running` — [HIGH] Checks if the command line contains the fragment as a substring, not considering arguments or context
  - says: PURE. Does this command line show `fragment` BEING RUN, rather than merely mentioned?
- **mutate.py** `_lock_release` — [HIGH] Release the mutation lock but never used in this module
  - says: Release the mutation lock
- **mutate.py** `_lock_acquire` — [HIGH] Acquire the mutation lock but never used in this module
  - says: Acquire the mutation lock
- **manifest_builder.py** `feats_block_chars` — [HIGH] The variable is used but not defined in the slice, leading to potential runtime errors.
  - says: DERIVED, NOT DECLARED (m46). `FEATS_BLOCK_CHARS` had no arithmetic relationship to `num_ctx`
- **manifest_builder.py** `placeholder_shelfmark` — [HIGH] The function is called but its implementation is not provided in the slice, leading to potential runtime errors.
  - says: Supplying the honest UNCHARTED placeholder gives the model something correct to copy.
- **magnitude.py** `_ask` — [HIGH] is never defined or imported
  - says: asks the system for a response
- **local_agent.py** `t_grep` — [HIGH] ignores the subtree parameter and searches in the current directory
  - says: searches for pattern in specified files
- **local_agent.py** `t_find_symbol` — [HIGH] Overwrites the wrong function (m38) by resolving a symbol by bare name with no uniqueness check
  - says: Every definition of `name`, with its enclosing class and a uniqueness verdict.
- **genre.py** `classify_source` — [HIGH] Truncates the entry list in stored order, changing the answer for 7 of 210 sources
  - says: Classify one source from its own catalogued entries.
- **foreman.py** `silence.replace_retry` — [HIGH] discards the boolean that reports the denied rename
  - says: CHECK THE RETURN THIS COMMENT ALREADY WARNS ABOUT (run #19). The paragraph above names the exact hazard -- a torn or stale write here silently discards overwatc
- **endpoint.py** `detect` — [HIGH] detect is not defined in this slice, but is called in api_url and raw_url
  - says: detect(host) returns the mode and path for a host
- **onomast.py** `well_formed` — [MEDIUM] the code checks for repeated pairs of characters (n[i:i+2] == n[i+2:i+4]), which does not detect doubled syllables (e.g., 'gog' is not a doubled syllable, but 'gogog' would be caug
  - says: no immediately doubled syllable (kills Goggoktok, Khakak)
- **mutate.py** `run` — [MEDIUM] run is called with parameters that may not match the expected function signature
  - says: run(t, limit=a.limit, root=root, base=base, gates=gates, confirm=confirm)
- **foreman.py** `kill_stalled_job` — [MEDIUM] The function attempts to kill stalled jobs but has a flawed logic in determining which jobs can be restarted, potentially leading to incorrect kills or failures to kill jobs that s
  - says: A job that is UP and writing nothing is worse than a job that is down.
- **feats.py** `alive` — [MEDIUM] Queries the API with a specific request but does not actually check if the host is alive; returns a boolean based on the API response which may not reflect actual host availability
  - says: Check if a host is alive by querying its API

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
