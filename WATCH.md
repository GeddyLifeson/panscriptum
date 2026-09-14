# OVERWATCH

round 517  ·  last run 2026-09-14 12:31

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,730 inspected
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**7 open** (1 high). Newest first.

- **escalation.py** `clear` — [HIGH] clear() is not properly handling the case where the halt file is not cleared, leading to incorrect state reporting
  - says: clear() is supposed to clear the halt and record the ruling
- **resync_roll.py** `dupes` — [MEDIUM] stores duplicate source filenames but does not track the entry counts from the record files
  - says: index every record file by its declared `source`
- **propagation.py** `observed_mark` — [MEDIUM] returns 0 when lag < 0 (shelf hasn't heard yet), but the docstring says it should return 0 when the shelf has heard (i.e., lag >= 0). The function's logic is inverted relative to its docstring's claim.
  - says: The ascension mark a DISTANT shelf should currently see. The field an entry must print when it claims a neighbour has not heard.
- **worldseed.py** `build_all` — [MEDIUM] build_all(limit=0) still let exactly one entry through because the first append always happens before the first post-append check fires.
  - says: build_all(limit=0) skipped this guard entirely and walked the whole ~12,435-entry catalogue instead of stopping at zero.
- **escalation.py** `clear` — [MEDIUM] clear() returns False for two entirely different worlds
  - says: PermissionError is caught alongside ValueError because `clear()` raises it for a non-person caller
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0
- **feats.py** `main` — [MEDIUM] returns 0 or 1 based on the roll's success, but the comment claims it should follow the same pattern as `--hosts` and `resolve_hosts` which return 1 if _HOSTS_DENIED else 0 and exit nonzero on failure
  - says: the sibling branches in this same file already do it: `--hosts` twenty lines up returns `1 if _HOSTS_DENIED else 0`, and `resolve_hosts`'s own docstring promises "main() exits nonzero on it". `--roll` was the one place the pattern was never applied, even though `roll()` has always returned exactly the counters needed.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
