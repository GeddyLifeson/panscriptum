# OVERWATCH

round 131  ·  last run 2026-08-28 22:45

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **1** of 269,929 inspected (deep scan as of round 127)  — handoff\run36\sweep_plan.json — malformed JSON: Extra data: line 213 column 1 (char 3102)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major
- MORE THAN ONE INSTANCE RUNNING: **2** publish.py: 2 processes

## What the model found in the code

**11 open** (4 high). Newest first.

- **binding_health.py** `merged, prior = list(out), {}` — [HIGH] merged and prior are initialized as a list of out and an empty dictionary, but the code does not actually perform any shrinking or re-probing of the estate as described in the comm
  - says: this report AS the estate -- `workorders.sweep`'s binding detector decides which hosts are suspect from it, and allsweep reconciles against it -- so a targeted 
- **binding_health.py** `binding_verdict` — [HIGH] does not perform the intended comparison between sitename and source_names
  - says: PURE. Does the wiki's own name correspond to the source bound to it?
- **verify_math.py** `_writes_the_config20p` — [HIGH] finds functions that name config.yaml and open something in a write mode
  - says: no function in drill.py may both name config.yaml and open something in a write mode
- **verify_math.py** `check` — [HIGH] the check passes if the verdict is not 'ledger', but the note says it should confirm the verdict came from the probe
  - says: and the verdict came from the PROBE, not from the ledger shortcut
- **axis_correlation.py** `rho` — [MEDIUM] Returns 0.0 when the matrix is missing, which contradicts the docstring's claim that it should return 0.0 for a missing matrix as a fallback, but the docstring explicitly states th
  - says: Correlation between two axes. -> float.
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

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
