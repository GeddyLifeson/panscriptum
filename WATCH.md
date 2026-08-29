# OVERWATCH

round 125  ·  last run 2026-08-28 20:03

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 269,194 inspected (deep scan as of round 121)  — handoff\run36\sweep_plan.json — malformed JSON: Extra data: line 213 column 1 (char 3102)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**20 open** (9 high). Newest first.

- **rosetta.py** `main` — [HIGH] The function returns 0 unconditionally, ignoring the bad list and the printout.
  - says: The exit code has to carry the verdict, not just the printout.
- **rosetta.py** `refine` — [HIGH] discards a failure the surrounding comment says is important
  - says: drop scale rows that name nothing this library catalogues
- **resync_roll.py** `roll` — [HIGH] Overwritten by the script's own modifications during the resync process
  - says: Rebuilds SWEEP_ROLL.json's entry_count/status from the record files on disk.
- **resonance.py** `dominates` — [HIGH] returns True when all values are equal
  - says: answers False for both of those for an unrelated reason
- **read.py** `_ask` — [HIGH] is the local GPU, unconditionally.
  - says: is the router: Cascade first, across a dozen separately-metered providers, with the local GPU only when all of them decline.
- **pipeline.py** `phase_chain` — [HIGH] Phase 4 that never runs because no code dispatches to it
  - says: Phase 4 -- the Chain of Defeats. See chain.py for the reasoning.
- **overnight.py** `run` — [HIGH] does not run the stage at all, as the pipeline is started in the background and the run() function checks for an existing instance
  - says: Runs after the reader so it sees the evidence the reader just produced
- **mutate.py** `_lock_acquire` — [HIGH] Defined but never called within the module
  - says: Acquire a lock to prevent concurrent mutation runs
- **genre.py** `classify_source` — [HIGH] Uses a truncated ranked list for confidence calculation, leading to inflated confidence scores
  - says: Classifies a source based on its entries, using all scored genres for confidence calculation
- **rigor.py** `lognormal_product` — [MEDIUM] the real Milky Way is not the claim
  - says: the real Milky Way
- **rigor.py** `ceiling_confidence` — [MEDIUM] Returns a value based on n_scored / n_entries, but the description states that the pipeline does not sample randomly and the calculation should reflect a biased estimate due to the
  - says: How much of a source's true ceiling has been seen, after scoring n of N entries?
- **rigor.py** `measure_bit_value` — [MEDIUM] The bit-worth of ONE point on any decimal axis at a given band, but the example in the docstring uses an outdated value (13.23 instead of 3.043) and the function's implementation m
  - says: The bit-worth of ONE point on any decimal axis at a given band.
- **reference.py** `by_pair` — [MEDIUM] indexes on host and entity from the key split, but the key split is only a fallback
  - says: index on host and entity rather than re-spelling the separator
- **reference.py** `shelfmark` — [MEDIUM] constructs a shelfmark with upper and lower rungs, but the code does not correctly handle cases where the tier_key or lower_rungs have different lengths than expected
  - says: The charter's canonical Shelfmark
- **read.py** `ensure_transport` — [MEDIUM] Resolves the transport configuration in a thread-safe manner, but the function's description mentions a 'lazy if _CASCADE_OK is None' which was a race condition, but the current im
  - says: Decide the transport ONCE, before any worker starts, and say which one won.
- **publish.py** `git` — [MEDIUM] git is used to push to origin/main without checking if the rebase was successful
  - says: git is a function that executes git commands
- **prose_gate.py** `evidence_ok` — [MEDIUM] Returns False if the floor is not a number or outside (0, 1], but does not properly handle the case where the source is unmeasured (returns None) and does not correctly enforce the
  - says: Has this source been read enough to be worth writing about?
- **pipeline.py** `land_json` — [MEDIUM] Writes the object to a temporary file and returns whether the rename succeeded, but does not ensure atomicity as described due to the lack of proper atomic write handling.
  - says: Write a phase artifact atomically. Returns whether it landed.
- **mutate.py** `escalation.OWNER` — [MEDIUM] The code is raising an escalation for a live file change during a sandboxed run, which the comment says is impossible by construction.
  - says: This must be impossible by construction -- the live path is never opened for writing.
- **magnitude.py** `slice_census` — [MEDIUM] Calculates totals but does not account for unread characters or sentences per axis, which are critical for understanding which axes had incomplete evidence processing.
  - says: How much of the evidence a split sheet was actually read from.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
