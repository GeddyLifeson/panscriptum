# OVERWATCH

round 503  ·  last run 2026-09-14 03:20

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,019 inspected (deep scan as of round 499)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**15 open** (5 high). Newest first.

- **health.py** `is_resume_probe` — [HIGH] Checks if `name` matches a regex pattern that includes many more subjects than the exact set defined in `SELFTEST_RESUME_SUBJECTS`.
  - says: Is `name` one of the three synthetic subjects allowed to resume without a person? -> bool.
- **foreman.py** `kill_stalled_job` — [HIGH] A job that is UP and writing nothing is better than a job that is down.
  - says: A job that is UP and writing nothing is worse than a job that is down.
- **foreman.py** `CB._PROVEN[0]` — [HIGH] invalidates the cached proof in favor of something older
  - says: force the next _alive() to re-read
- **drill.py** `silence.write_json` — [HIGH] a TRUNCATE-THEN-FILL, not a write
  - says: this project's stated one correct way to land a shared file
- **drill.py** `CW.BUDGET_PER_HOUR` — [HIGH] hardcoded and not dynamically derived as the code around it suggests
  - says: used to determine budget per hour
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0
- **generate.py** `args.limit` — [MEDIUM] is not None
  - says: is not None
- **foreman.py** `_checks_pass` — [MEDIUM] Runs verify_math.py and allsweep.py --quick, but the code's comment says it should check the exit code of allsweep.py --quick and ensure it's not broken
  - says: Everything that must still be true after a patch.
- **foreman.py** `kill_stalled` — [MEDIUM] The function returns a string that includes the horizons for all killed jobs, but the claim suggests it should name the horizon per job.
  - says: Name the horizon PER JOB: this remedy can kill a STANDING job (pipeline, back in 300s) and a main-lap job (read, roll) in the same breath, and one blanket clause cannot be true of both. See _restart_horizon.
- **foreman.py** `restart_reader` — [MEDIUM] The function does not actually check if the reader is progressing or not; it only attempts to list processes and returns False if there's an error.
  - says: The reader is not progressing. Restarting is safe: every entity is cached only when it was fully read, so nothing is lost and nothing is re-read that was finished.
- **feats.py** `main` — [MEDIUM] returns 0 or 1 based on the roll's success, but the comment claims it should follow the same pattern as `--hosts` and `resolve_hosts` which return 1 if _HOSTS_DENIED else 0 and exit nonzero on failure
  - says: the sibling branches in this same file already do it: `--hosts` twenty lines up returns `1 if _HOSTS_DENIED else 0`, and `resolve_hosts`'s own docstring promises "main() exits nonzero on it". `--roll` was the one place the pattern was never applied, even though `roll()` has always returned exactly the counters needed.
- **feats.py** `work` — [MEDIUM] the code in the work function is not actually implementing the brake or hand-off mechanism described in the comment. Instead, it is handling the quarantine logic by checking if the host is in the held set and deferring the job if so, which is part of the deferred tail processing.
  - says: THE BRAKE THE HAND-OFF ALWAYS CLAIMED TO BE. `note_throttled` quarantines a host after THROTTLE_STRIKES consecutive 429s and its comment says the crawl stops spending requests on it; until the 2026-09-08 ruling nothing on the fetch path asked, so twelve workers went on queueing at the 32x ceiling. Asked here, once per entity, off a view refreshed at most once a minute.
- **feats.py** `retries` — [MEDIUM] hardcoded
  - says: the code around it says it should be derived
- **drill.py** `CW.LEDGER` — [MEDIUM] reassigned but not used correctly in the context of the code's logic
  - says: redirected to a temporary directory
- **drill.py** `CW.LEDGER_LOCK` — [MEDIUM] reassigned to a new value but not properly managed in the context of the code's logic
  - says: redirected to a lock file

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
