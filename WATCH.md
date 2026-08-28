# OVERWATCH

round 121  ·  last run 2026-08-28 17:39

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 269,194 inspected  — handoff\run36\sweep_plan.json — malformed JSON: Extra data: line 213 column 1 (char 3102)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**15 open** (7 high). Newest first.

- **overnight.py** `run` — [HIGH] does not run the stage at all, as the pipeline is started in the background and the run() function checks for an existing instance
  - says: Runs after the reader so it sees the evidence the reader just produced
- **overnight.py** `_keep_warm` — [HIGH] Attempts to import gpu_lane and silently ignores failures, which could prevent the model from staying resident and cause the keep-warm function to fail silently
  - says: Hold the model resident AT THE CONFIGURED num_ctx.
- **mutate.py** `_lock_acquire` — [HIGH] Defined but never called within the module
  - says: Acquire a lock to prevent concurrent mutation runs
- **identity.py** `epoch_of` — [HIGH] return an empty string when the probe is unavailable or the response is unparsable
  - says: determine the epoch of a sentence
- **identity.py** `_ask` — [HIGH] swallow all exceptions and return None
  - says: ask a question and return the answer
- **genre.py** `classify_source` — [HIGH] Uses a truncated ranked list for confidence calculation, leading to inflated confidence scores
  - says: Classifies a source based on its entries, using all scored genres for confidence calculation
- **generate.py** `compress_store.store` — [HIGH] is called but exceptions are caught and handled without raising
  - says: now RAISES when `silence.replace_retry` cannot land the blob
- **overnight.py** `run` — [MEDIUM] Checks if the stage is already running by the basename of the argument, but the comment says it should match on the full path
  - says: Run one stage to completion, refusing to start a duplicate.
- **overnight.py** `_cmd_is_running` — [MEDIUM] Checks if the command line contains the fragment as the script name, but not its arguments, and if the interpreter is Python
  - says: PURE. Does this command line show `fragment` BEING RUN, rather than merely mentioned?
- **onomast.py** `well_formed` — [MEDIUM] Enforces constraints that may not align with the intended pronounceability criteria
  - says: Is this a name a Custos could say aloud and write down twice the same way?
- **mutate.py** `escalation.OWNER` — [MEDIUM] The code is raising an escalation for a live file change during a sandboxed run, which the comment says is impossible by construction.
  - says: This must be impossible by construction -- the live path is never opened for writing.
- **magnitude.py** `slice_census` — [MEDIUM] Calculates totals but does not account for unread characters or sentences per axis, which are critical for understanding which axes had incomplete evidence processing.
  - says: How much of the evidence a split sheet was actually read from.
- **local_agent.py** `modname` — [MEDIUM] derive module name from file path but case-insensitively
  - says: derive module name from file path
- **liveness.py** `used_local` — [MEDIUM] used_local is a dictionary mapping module names to sets of names used in that module
  - says: used_local is a set of names used in the current module
- **ingest_doc.py** `state` — [MEDIUM] reset to 0, found to 0 on exception
  - says: tracking progress

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
