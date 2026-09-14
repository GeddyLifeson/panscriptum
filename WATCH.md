# OVERWATCH

round 521  ·  last run 2026-09-14 15:07

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,730 inspected (deep scan as of round 517)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**7 open** (2 high). Newest first.

- **estate.py** `external` — [HIGH] The function is named 'external' but the code inside it is not about external dependencies, but rather about checking various system states and configurations (Ollama, Cascade, disk space).
  - says: The dependencies that live outside this project and can fail without it changing.
- **estate.py** `artifacts` — [HIGH] The code does not discover roots from the tree; it uses a hand-kept list of directories and files, and the docstring claims it does not sample.
  - says: Every file in the project, opened and checked. No sampling anywhere.
- **estate.py** `note` — [MEDIUM] appends a finding to the out, but the function is not properly defined with a docstring or comment explaining its purpose
  - says: appends a finding to the out list
- **estate.py** `note` — [MEDIUM] appends a finding to the out list but the function is not properly defined with a docstring or comment explaining its purpose
  - says: appends a finding to the out list
- **assay.py** `grade` — [MEDIUM] grade_n is compared to 5, but the Ladder has eleven rungs (indices 0-10), so grade_n can be 0-10, making the condition grade_n <= 5 true for 0-5, but the code uses a list with six slots (indices 0-5), so grade_n=6 would be out of range
  - says: grade_n <= 5 cannot be false while the Ladder has eleven rungs
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0
- **feats.py** `main` — [MEDIUM] returns 0 or 1 based on the roll's success, but the comment claims it should follow the same pattern as `--hosts` and `resolve_hosts` which return 1 if _HOSTS_DENIED else 0 and exit nonzero on failure
  - says: the sibling branches in this same file already do it: `--hosts` twenty lines up returns `1 if _HOSTS_DENIED else 0`, and `resolve_hosts`'s own docstring promises "main() exits nonzero on it". `--roll` was the one place the pattern was never applied, even though `roll()` has always returned exactly the counters needed.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
