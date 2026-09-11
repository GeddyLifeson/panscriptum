# OVERWATCH

round 490  ·  last run 2026-09-10 19:29

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 303,086 inspected (deep scan as of round 487)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**10 open** (5 high). Newest first.

- **roll.py** `apply` — [HIGH] Apply a function to rows, returning modified rows
  - says: Apply `{source_name: {field: value, ...}}` to the roll, key-wise.
- **onomast.py** `well_formed` — [HIGH] Implements seven constraints but the docstring claims four, and three of the four original constraints are misattributed
  - says: Is this a name a Custos could say aloud and write down twice the same way?
- **foreman.py** `lines_changed` — [HIGH] Calculates the number of lines changed based on the diff between old and new code, but the docstring says it's not `abs(len(new) - len(old))` and instead explains a different method. However, the code correctly implements the described logic using difflib's SequenceMatcher. The docstring's claim is accurate, and the code aligns with it. Therefore, no defect of fact is found here.
  - says: How many lines a rewrite actually touches.
- **foreman.py** `kill_stalled_job` — [HIGH] kills stalled jobs that cannot be restarted, which is against the stated policy
  - says: A job that is UP and writing nothing is worse than a job that is down.
- **estate.py** `external` — [HIGH] The function is named 'external' but the code inside it is not related to external dependencies, but rather to checking the status of Ollama, Cascade, and disk space.
  - says: The dependencies that live outside this project and can fail without it changing.
- **publish.py** `push` — [MEDIUM] push() raises a PushHeld exception when a push is held, which is caught in an except block that prints the exception and sets rc=1
  - says: push() now has only two RETURN values, and both are honest ones: it landed, or there was nothing to land. The third outcome -- committed but held -- comes out as `PushHeld` and is caught below, where it prints and sets rc=1
- **foreman.py** `_contracts_pass` — [MEDIUM] Returns a tuple indicating success or failure of the contracts pass
  - says: Everything that must still be true after a patch.
- **foreman.py** `restart_reader` — [MEDIUM] The function is supposed to determine if a reader can be restarted, but it's actually enumerating processes and returning False or a message if it can't, without checking if the reader is actually restartable.
  - says: The reader is not progressing. Restarting is safe: every entity is cached only when it was fully read, so nothing is lost and nothing is re-read that was finished.
- **foreman.py** `reprove_pool` — [MEDIUM] returns False when the proof is not written
  - says: This returned True whenever the proof was written
- **verify_math.py** `max` — [MEDIUM] the tolerance is silently discarded as the code compares integers exactly
  - says: the k-th burg holds P1/k, independently recomputed

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
