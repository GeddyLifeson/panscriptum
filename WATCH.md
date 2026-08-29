# OVERWATCH

round 129  ·  last run 2026-08-28 21:45

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 269,929 inspected (deep scan as of round 127)  — handoff\run36\sweep_plan.json — malformed JSON: Extra data: line 213 column 1 (char 3102)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**5 open** (2 high). Newest first.

- **standards.py** `fab` — [HIGH] can be None or a value
  - says: UNMEASURED IS NOT GREEN
- **rosetta.py** `main` — [HIGH] The function returns 0 unconditionally, ignoring the bad list and the printout.
  - says: The exit code has to carry the verdict, not just the printout.
- **thread_integrity.py** `classify` — [MEDIUM] the function is called with args.age, but the code around it says it should be derived from the distance function
  - says: classify(pairs, dist, args.age, ents=ents)
- **sweep_plan.py** `silence` — [MEDIUM] imported but not used in the code
  - says: imported to handle errors
- **suppressions.py** `problems` — [MEDIUM] returns a list of problems, including expired and dangling suppressions, but the code does not actually check for expiration or dangling paths correctly
  - says: -> [problems]. An expired or dangling suppression is a FAULT, not a silent pass.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
