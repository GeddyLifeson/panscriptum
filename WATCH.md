# OVERWATCH

round 127  ·  last run 2026-08-28 20:52

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **1** of 269,929 inspected  — handoff\run36\sweep_plan.json — malformed JSON: Extra data: line 213 column 1 (char 3102)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**14 open** (9 high). Newest first.

- **standards.py** `fab` — [HIGH] can be None or a value
  - says: UNMEASURED IS NOT GREEN
- **standards.py** `ollama_token_flow` — [HIGH] Hardcodes `num_ctx: 512` while the code around it says it should derive the window from `config.yaml`
  - says: Does a generation actually COMPLETE? The third liveness lesson in two days.
- **snapshot.py** `restore` — [HIGH] Copies a snapshot back into a base directory, but the function's name and docstring suggest it should be restoring from a snapshot, but the code is actually copying from a snapshot
  - says: Copy a snapshot back.
- **sevenfold.py** `write_json` — [HIGH] discarded the verdict and printed "wrote {p}" regardless
  - says: returns whether the rename LANDED
- **sevenfold.py** `split` — [HIGH] split(order, 0)
  - says: split(block, level)
- **sevenfold.py** `seams` — [HIGH] Slices the first k-1 gaps regardless of their strength, leading to uneven divisions
  - says: Where the affinity ordering is weakest -- the natural places to cut.
- **secondopinion.py** `NOT_FILED` — [HIGH] A dictionary of rules that are not filed, but the entries are not actually waived
  - says: A dictionary of waived rules
- **scope.py** `scope_for` — [HIGH] the code does something else
  - says: the code says it does
- **rosetta.py** `main` — [HIGH] The function returns 0 unconditionally, ignoring the bad list and the printout.
  - says: The exit code has to carry the verdict, not just the printout.
- **standards.py** `report` — [MEDIUM] the code uses a _rank dictionary that sorts 'high' as 0, 'medium' as 1, and 'low' as 2, which would sort high first, then medium, then low. However, the comment suggests that the r
  - says: By RANK, not alphabetically. Sorting the severity strings gives high, low, medium -- so the CLI report buried every medium work order below the lows, which is t
- **standards.py** `fandom_ipv4_reachable` — [MEDIUM] The function does not enforce IPv4-only connections, and the host parameter is not properly validated to ensure IPv4 resolution.
  - says: Can this machine open a TCP connection to fandom's edge OVER IPv4?
- **secondopinion.py** `NOT_FILED` — [MEDIUM] Entries are rules that the codebase does not argue with, but the codebase's own 
  - says: Entries are waived rules that the codebase argues with
- **scope.py** `build` — [MEDIUM] The function returns the verdict now so its one caller can tell the difference.
  - says: ATOMIC: SCOPE.json is read by magnitude.py and pipeline.py. 2026-08-25.
- **publish.py** `git` — [MEDIUM] git is used to push to origin/main without checking if the rebase was successful
  - says: git is a function that executes git commands

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
