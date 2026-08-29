# OVERWATCH

round 124  ·  last run 2026-08-28 19:26

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 269,194 inspected (deep scan as of round 121)  — handoff\run36\sweep_plan.json — malformed JSON: Extra data: line 213 column 1 (char 3102)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**18 open** (8 high). Newest first.

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
- **overnight.py** `_keep_warm` — [HIGH] Attempts to import gpu_lane and silently ignores failures, which could prevent the model from staying resident and cause the keep-warm function to fail silently
  - says: Hold the model resident AT THE CONFIGURED num_ctx.
- **mutate.py** `_lock_acquire` — [HIGH] Defined but never called within the module
  - says: Acquire a lock to prevent concurrent mutation runs
- **genre.py** `classify_source` — [HIGH] Uses a truncated ranked list for confidence calculation, leading to inflated confidence scores
  - says: Classifies a source based on its entries, using all scored genres for confidence calculation
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
- **overnight.py** `run` — [MEDIUM] Checks if the stage is already running by the basename of the argument, but the comment says it should match on the full path
  - says: Run one stage to completion, refusing to start a duplicate.
- **mutate.py** `escalation.OWNER` — [MEDIUM] The code is raising an escalation for a live file change during a sandboxed run, which the comment says is impossible by construction.
  - says: This must be impossible by construction -- the live path is never opened for writing.
- **magnitude.py** `slice_census` — [MEDIUM] Calculates totals but does not account for unread characters or sentences per axis, which are critical for understanding which axes had incomplete evidence processing.
  - says: How much of the evidence a split sheet was actually read from.
- **liveness.py** `used_local` — [MEDIUM] used_local is a dictionary mapping module names to sets of names used in that module
  - says: used_local is a set of names used in the current module

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
