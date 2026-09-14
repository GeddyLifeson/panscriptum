# OVERWATCH

round 504  ·  last run 2026-09-14 03:43

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,019 inspected (deep scan as of round 499)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**22 open** (7 high). Newest first.

- **local_agent.py** `_mod_l` — [HIGH] The code converts the module name to lowercase, making the denylist check case-insensitive, which contradicts the claim that the denylist is case-sensitive.
  - says: THE DENY,LIST IS CASE-SENSITIVE AND THE FILESYSTEM IS NOT.
- **local_agent.py** `_deny_paths` — [HIGH] The code converts the denylist paths to lowercase, making them case-insensitive, which contradicts the claim that the denylist is case-sensitive.
  - says: THE DENYLIST IS CASE-SENSITIVE AND THE FILESYSTEM IS NOT.
- **local_agent.py** `_deny` — [HIGH] The code converts the denylist to lowercase, making it case-insensitive, which contradicts the claim that the denylist is case-sensitive.
  - says: THE DENYLIST IS CASE-SENSITIVE AND THE FILESYSTEM IS NOT.
- **ledger_guard.py** `seal` — [HIGH] raises LedgerViolation on failure
  - says: returns None on any write failure with no exception raised
- **health.py** `is_resume_probe` — [HIGH] Checks if `name` matches a regex pattern that includes many more subjects than the exact set defined in `SELFTEST_RESUME_SUBJECTS`.
  - says: Is `name` one of the three synthetic subjects allowed to resume without a person? -> bool.
- **foreman.py** `kill_stalled_job` — [HIGH] A job that is UP and writing nothing is better than a job that is down.
  - says: A job that is UP and writing nothing is worse than a job that is down.
- **foreman.py** `CB._PROVEN[0]` — [HIGH] invalidates the cached proof in favor of something older
  - says: force the next _alive() to re-read
- **local_agent.py** `json.loads` — [MEDIUM] loads a JSON string into a Python object, but the code then proceeds to append the content to messages regardless of whether it was valid JSON or not
  - says: error instead of half a dict, and the ledger records that it happened.
- **local_agent.py** `_spellings` — [MEDIUM] The code checks the lowercase version of the path for allowlist checks, which may not accurately represent the actual file path, leading to potential false negatives in allowlist checks.
  - says: ASKED OF BOTH SPELLINGS OF THE PATH — BYPASS CLASS SEVEN
- **local_agent.py** `_rel_l` — [MEDIUM] The code uses the lowercase version of the relative path for denylist checks, which may not accurately represent the actual file path, leading to potential false negatives in denylist checks.
  - says: THE DENYLIST ASKED OF THE FILE, NOT OF ITS NAME
- **local_agent.py** `rel` — [MEDIUM] rel is the repo-relative path, but the denylist check for non-python files is not properly handled because modname is None for non-python files, and the code only checks modname when it exists.
  - says: The denylist has to be answerable for NON-python files too. Match on the module name when there is one, and on the repo-relative path otherwise.
- **local_agent.py** `modname` — [MEDIUM] the module name
  - says: the module name
- **local_agent.py** `hits` — [MEDIUM] the list of matches
  - says: the list of matches
- **local_agent.py** `full` — [MEDIUM] the path to the file being scanned
  - says: the path inside the project
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

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
