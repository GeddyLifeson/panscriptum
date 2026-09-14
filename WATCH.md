# OVERWATCH

round 525  ·  last run 2026-09-14 17:46

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,777 inspected (deep scan as of round 523)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**6 open** (2 high). Newest first.

- **canon_backup.py** `replace_retry` — [HIGH] the function is called but its result is ignored, and the code proceeds to raise an exception regardless of the result
  - says: THE VERDICT IS CHECKED, WHICH IS THE HALF THAT MATTERS. `replace_retry` NEVER RAISES, by contract; it reports False.
- **autostart.py** `installed_state` — [HIGH] not defined in this file or its imports
  - says: returns the state of the launcher
- **catalogue_models.py** `last` — [MEDIUM] a single-line exception repr with type and message joined by a space
  - says: a single-line exception repr
- **canon_backup.py** `restore` — [MEDIUM] Extracts a file from a snapshot, but the function's name and docstring imply it should extract a single file, yet the code may create a 0-byte file if the file is not present in the snapshot.
  - says: Extract ONE canonical file from a snapshot. -> written path.
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0
- **feats.py** `main` — [MEDIUM] returns 0 or 1 based on the roll's success, but the comment claims it should follow the same pattern as `--hosts` and `resolve_hosts` which return 1 if _HOSTS_DENIED else 0 and exit nonzero on failure
  - says: the sibling branches in this same file already do it: `--hosts` twenty lines up returns `1 if _HOSTS_DENIED else 0`, and `resolve_hosts`'s own docstring promises "main() exits nonzero on it". `--roll` was the one place the pattern was never applied, even though `roll()` has always returned exactly the counters needed.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
