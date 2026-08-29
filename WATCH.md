# OVERWATCH

round 126  ·  last run 2026-08-28 20:26

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **1** of 269,194 inspected (deep scan as of round 121)  — handoff\run36\sweep_plan.json — malformed JSON: Extra data: line 213 column 1 (char 3102)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**12 open** (6 high). Newest first.

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
- **secondopinion.py** `NOT_FILED` — [MEDIUM] Entries are rules that the codebase does not argue with, but the codebase's own 
  - says: Entries are waived rules that the codebase argues with
- **scope.py** `build` — [MEDIUM] The function returns the verdict now so its one caller can tell the difference.
  - says: ATOMIC: SCOPE.json is read by magnitude.py and pipeline.py. 2026-08-25.
- **rigor.py** `ceiling_confidence` — [MEDIUM] Returns a value based on n_scored / n_entries, but the description states that the pipeline does not sample randomly and the calculation should reflect a biased estimate due to the
  - says: How much of a source's true ceiling has been seen, after scoring n of N entries?
- **publish.py** `git` — [MEDIUM] git is used to push to origin/main without checking if the rebase was successful
  - says: git is a function that executes git commands
- **prose_gate.py** `evidence_ok` — [MEDIUM] Returns False if the floor is not a number or outside (0, 1], but does not properly handle the case where the source is unmeasured (returns None) and does not correctly enforce the
  - says: Has this source been read enough to be worth writing about?
- **pipeline.py** `land_json` — [MEDIUM] Writes the object to a temporary file and returns whether the rename succeeded, but does not ensure atomicity as described due to the lack of proper atomic write handling.
  - says: Write a phase artifact atomically. Returns whether it landed.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
