# OVERWATCH

round 153  ·  last run 2026-08-29 10:11

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 273,179 inspected (deep scan as of round 151)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**8 open** (1 high). Newest first.

- **rosetta.py** `main` — [HIGH] The function returns 0 unconditionally, but the code comments indicate that it should return 1 if there are disagreements.
  - says: The exit code has to carry the verdict, not just the printout.
- **autostart.py** `start_supervisor` — [MEDIUM] starts the supervisor if it's not already running
  - says: starts the supervisor
- **autostart.py** `subprocess.Popen` — [MEDIUM] return a subprocess.Popen object immediately without waiting for it to complete
  - says: start a new process
- **verify_math.py** `_own_nodes20p` — [MEDIUM] Yields nodes of `fn` including nested functions, but skips the nested functions' nodes.
  - says: Every node belonging to `fn` ITSELF, not to a function nested inside it.
- **verify_math.py** `_writes_the_config20p` — [MEDIUM] Checks if a function both names 'config.yaml' and opens something in write mode.
  - says: Every node belonging to `fn` ITSELF, not to a function nested inside it.
- **verify_math.py** `check` — [MEDIUM] the check is for a literal string match, but the comment says it should check the AST for the correct behavior
  - says: check('the auth bench is still four hours', ...)
- **overnight.py** `run` — [MEDIUM] cannot run after the reader because pipeline is started in the background and the keeper re-asserts the standing set every 300s
  - says: Runs after the reader so it sees the evidence the reader just produced
- **navtree.py** `register_for` — [MEDIUM] returns a register for a node, but the logic for tie-breaking is flawed and non-deterministic
  - says: returns a register for a node

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
