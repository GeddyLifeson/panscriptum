# OVERWATCH

round 130  ·  last run 2026-08-28 22:08

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 269,929 inspected (deep scan as of round 127)  — handoff\run36\sweep_plan.json — malformed JSON: Extra data: line 213 column 1 (char 3102)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**14 open** (4 high). Newest first.

- **verify_math.py** `_writes_the_config20p` — [HIGH] finds functions that name config.yaml and open something in a write mode
  - says: no function in drill.py may both name config.yaml and open something in a write mode
- **verify_math.py** `check` — [HIGH] the check passes if the verdict is not 'ledger', but the note says it should confirm the verdict came from the probe
  - says: and the verdict came from the PROBE, not from the ledger shortcut
- **verify_math.py** `check` — [HIGH] the check passes if the predicate returns True, but the note says it should fail
  - says: a reasoning model's truncated generation reads as FLOW, not a wedge
- **rosetta.py** `main` — [HIGH] The function returns 0 unconditionally, ignoring the bad list and the printout.
  - says: The exit code has to carry the verdict, not just the printout.
- **verify_math.py** `A.instrument` — [MEDIUM] Prints nothing when only one of its two axes is attested but with a logical operator change
  - says: Prints nothing when only one of its two axes is attested
- **verify_math.py** `A._interval` — [MEDIUM] Calculates between-hand variance with an inverted condition
  - says: Calculates between-hand variance for more than one reading
- **verify_math.py** `A.assay` — [MEDIUM] Asserts that an entry may belong one rung up but with a flipped condition
  - says: Asserts that an entry may belong one rung up
- **verify_math.py** `check` — [MEDIUM] the first argument is a string, the second is a boolean, and the third is a boolean
  - says: check the condition is true
- **verify_math.py** `measure_bit_value` — [MEDIUM] the worked example incorrectly references the old cumulative figure instead of the updated band_resolution value
  - says: the worked example quotes the value the function actually returns
- **verify_math.py** `measure_bit_value` — [MEDIUM] the function uses band_resolution, but the docstring still references the cumulative figure
  - says: the cumulative figure made every M0 axis point worth zero bits
- **verify_math.py** `AS.assign` — [MEDIUM] compares the same value across two different module instances, but the function's implementation may not ensure deterministic behavior across different loads
  - says: assignment is deterministic across an independent load of the module
- **verify_math.py** `A.axis_score` — [MEDIUM] A.axis_score is being called with 1e-3, but the code is comparing it to the value at the band floor (A.BAND_EDGES['M3']['ruin']), which may not be zero
  - says: axis_score CLAMPS at zero, so 0.0 is a bound not a point
- **thread_integrity.py** `classify` — [MEDIUM] the function is called with args.age, but the code around it says it should be derived from the distance function
  - says: classify(pairs, dist, args.age, ents=ents)
- **suppressions.py** `problems` — [MEDIUM] returns a list of problems, including expired and dangling suppressions, but the code does not actually check for expiration or dangling paths correctly
  - says: -> [problems]. An expired or dangling suppression is a FAULT, not a silent pass.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
