# OVERWATCH

round 94  ·  last run 2026-08-26 23:44

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **0** of 230,350 inspected
- catalogued sources with no host: **10** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**7 open** (4 high). Newest first.

- **local_agent.py** `run` — [HIGH] returns a verdict that is not reliable when a model fails to produce a tool call or answer, and does not account for safety alarms properly
  - says: returns a verdict indicating whether the run was successful
- **overnight.py** `start` — [HIGH] Calls a function that does not exist in the current scope
  - says: Starts a background process with the given command and log file
- **overnight.py** `_cmd_is_running` — [HIGH] Checks if the command line contains the fragment as a substring, not considering arguments or context
  - says: PURE. Does this command line show `fragment` BEING RUN, rather than merely mentioned?
- **genre.py** `classify_source` — [HIGH] Truncates the entry list in stored order, changing the answer for 7 of 210 sources
  - says: Classify one source from its own catalogued entries.
- **assay.py** `sigma` — [MEDIUM] clamp the sigma value to SIGMA_MAX but the code does not handle the case where sigma is None
  - says: clamp the sigma value to SIGMA_MAX
- **address_space.py** `C.GALAXIES_DEFAULT` — [MEDIUM] the default number of galaxies per universe as defined in the cosmography module
  - says: the number of galaxies per universe
- **local_agent.py** `t_propose_patch` — [MEDIUM] The denylist is case-insensitive and the filesystem is not, but the code does not handle non-python files correctly.
  - says: The denylist has to be answerable for NON-python files too.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
