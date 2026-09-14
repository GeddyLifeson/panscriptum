# OVERWATCH

round 505  ·  last run 2026-09-14 04:16

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,616 inspected
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**11 open** (5 high). Newest first.

- **onomast.py** `well_formed` — [HIGH] Implements seven constraints but the docstring claims it was meant to implement four, and three of the four original constraints were misattributed
  - says: Is this a name a Custos could say aloud and write down twice the same way?
- **mutate.py** `killed` — [HIGH] count of mutants that were killed or survived
  - says: count of mutants that were killed
- **mutate.py** `indeterminate` — [HIGH] a record of mutants that could not be judged
  - says: the permanent record of the diff
- **mutate.py** `_lock_acquire` — [HIGH] Acquires a lock and writes a token to it, but does not release it.
  - says: Drop the lock, but only if it is still OURS.
- **health.py** `is_resume_probe` — [HIGH] Checks if `name` matches a regex pattern that includes many more subjects than the exact set defined in `SELFTEST_RESUME_SUBJECTS`.
  - says: Is `name` one of the three synthetic subjects allowed to resume without a person? -> bool.
- **mutate.py** `os.makedirs` — [MEDIUM] creates the directory if it does not exist
  - says: creates the directory
- **manifest_builder.py** `report_landed` — [MEDIUM] report_landed is assigned but never used beyond the check for its truth value
  - says: report_landed is the verdict on the report write
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0
- **foreman.py** `_checks_pass` — [MEDIUM] Runs verify_math.py and allsweep.py --quick, but the code's comment says it should check the exit code of allsweep.py --quick and ensure it's not broken
  - says: Everything that must still be true after a patch.
- **foreman.py** `kill_stalled` — [MEDIUM] The function returns a string that includes the horizons for all killed jobs, but the claim suggests it should name the horizon per job.
  - says: Name the horizon PER JOB: this remedy can kill a STANDING job (pipeline, back in 300s) and a main-lap job (read, roll) in the same breath, and one blanket clause cannot be true of both. See _restart_horizon.
- **feats.py** `main` — [MEDIUM] returns 0 or 1 based on the roll's success, but the comment claims it should follow the same pattern as `--hosts` and `resolve_hosts` which return 1 if _HOSTS_DENIED else 0 and exit nonzero on failure
  - says: the sibling branches in this same file already do it: `--hosts` twenty lines up returns `1 if _HOSTS_DENIED else 0`, and `resolve_hosts`'s own docstring promises "main() exits nonzero on it". `--roll` was the one place the pattern was never applied, even though `roll()` has always returned exactly the counters needed.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
