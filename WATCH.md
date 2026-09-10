# OVERWATCH

round 482  ·  last run 2026-09-10 13:27

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 302,961 inspected (deep scan as of round 481)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**37 open** (18 high). Newest first.

- **silence.py** `append_line` — [HIGH] Appends a line but does not handle the Windows-specific issues with O_APPEND and text mode, leading to potential data corruption and line tearing.
  - says: Append ONE line to a shared ledger without tearing it (m62).
- **silence.py** `audit` — [HIGH] audit() returns rows of handlers, but the function's name and comment suggest it should audit for silence, not collect handlers
  - says: audit(root=None)
- **compress_store.py** `load` — [HIGH] Reads a stored blob back without verifying it against the address it is filed under, and does not check the hash of the decompressed text.
  - says: Read a stored blob back, VERIFYING it against the address it is filed under.
- **withdraw_chapters.py** `main` — [HIGH] exits 1 when a.go is True and any of several conditions are met
  - says: exits 0 unconditionally
- **tuning.py** `cloud_success_rate` — [HIGH] The function reads from `state/cascade_scratch.db`'s `usage` table, but the path is hardcoded to a specific location, which may not be the correct one if SCRATCH_DB is repointed.
  - says: The pool's MEASURED success rate over the recent past: (rate, calls).
- **rosetta.py** `stand_rows` — [HIGH] does not parse Stand parameters as described, but instead is a placeholder for a parser that was never implemented
  - says: (name, mean Stand-parameter grade) pairs read from labelled parameter blocks. -> {}
- **verify_math.py** `_flowok19ab` — [HIGH] the check passed whatever that function actually did, INCLUDING the response-only predicate it exists to refuse
  - says: the exact payload measured on 2026-08-24 -- eval_count 8, thinking non-empty, response empty -- put through standards.ollama_token_flow itself rather than through a copy of its predicate written here. The old predicate returns False on this payload and reports a healthy truncated generation as a dead daemon
- **verify_math.py** `max` — [HIGH] clamped to HAMLET_FLOOR, which is 40, but the code never used the floor
  - says: the k-th burg holds P1/k, independently recomputed
- **standards.py** `flow` — [HIGH] the local model produces tokens
  - says: the local model produces tokens
- **standards.py** `CHARTER_REGRESSION_MAX_AGE_H` — [HIGH] the value is hardcoded as a literal '26h' in the comment, but the code uses the variable CHARTER_REGRESSION_MAX_AGE_H
  - says: every scored reference overlaps its published interval, within CHARTER_REGRESSION_MAX_AGE_Hh
- **standards.py** `fab is not None and fab <= MAX_FABRICATION` — [HIGH] the condition is evaluated as a boolean, but the text says it's not green when unmeasured
  - says: UNMEASURED IS NOT GREEN
- **standards.py** `names` — [HIGH] only the error string is named, not the provider
  - says: NOTHING IS CAPPED -- every unverified provider is named
- **standards.py** `body` — [HIGH] hardcoded to 6144 when config.yaml is missing or has no num_ctx entry
  - says: num_ctx FROM CONFIG, never a literal -- see the docstring. A foreign window turns this probe into a runner rebuild, which is the one call shape that cannot finish.
- **scope.py** `mutate` — [HIGH] reads the file, attempts to update it, but does not actually perform a compare-and-swap operation as described
  - says: Land a change to SCOPE.json through a COMPARE-AND-SWAP. -> (landed, why).
- **scope.py** `scope_for` — [HIGH] returns a scope with best[0] and best[1] when best is not None
  - says: returns None when no tier reaches MIN_MENTIONS
- **mutate.py** `_lock_acquire` — [HIGH] Acquires a lock and writes a token to it, but the function is named and documented as releasing a lock.
  - says: Drop the lock, but only if it is still OURS.
- **chain.py** `main` — [HIGH] the main function is not defined in this slice
  - says: the main function
- **local_agent.py** `t_propose_patch` — [HIGH] appends to `unreverted` but does not raise an alarm or note
  - says: raises the durable alarms for this case -- a SAFETY escalation and a `silence.note`
- **thread_integrity.py** `dist` — [MEDIUM] initialized to None but not properly calculated or handled in all cases
  - says: distance for propagation calculation
- **thread_integrity.py** `detail` — [MEDIUM] appends tuples to the detail dictionary for various categories but may not be correctly structured as per the comments
  - says: stores detailed information about each category
- **thread_integrity.py** `out` — [MEDIUM] increments the count for partially dangling pairs but also for other categories like IMPLIED-UNRECORDED and RECIPROCAL
  - says: counts the number of partially dangling pairs
- **scout.py** `deferred` — [MEDIUM] the code uses the old `
  - says: NOT a truncation of the universe: these are ahead of nobody and behind everybody, and each moves to the front by waiting. Named so the deferral is legible.
- **scout.py** `silence.replace_if_unchanged` — [MEDIUM] refuses only when the target is unreadable as bytes at write time
  - says: refuse to write over an unreadable file
- **rosetta.py** `check` — [MEDIUM] check() is called with rosetta and assays, but the code does not show how check() is implemented or its actual behavior.
  - says: check() is supposed to match anything at all -- see check()'s docstring on the bare-name lookup that scored 0 overlap on all eight standing scales.
- **verify_math.py** `check` — [MEDIUM] the code does something else
  - says: the code says it does
- **verify_math.py** `_restart_horizon` — [MEDIUM] the reader is in the keeper's STANDING set
  - says: the reader is still identified by one contiguous lognames fragment
- **verify_math.py** `_flowsecs19ab` — [MEDIUM] the fast path returns True on a warm metrics row without ever evaluating the predicate
  - says: the fast path returns True on a warm metrics row without ever evaluating the predicate; without this pin the check above could read green off a stale tps and would survive the predicate being deleted outright
- **verify_math.py** `A.axis_score` — [MEDIUM] returns None for missing quantities but raises an error for unknown bands
  - says: a missing quantity cannot become an axis score
- **verify_math.py** `A.axis_score` — [MEDIUM] returns None for non-positive quantities but raises an error for unknown bands
  - says: a non-positive quantity cannot become an axis score
- **verify_math.py** `max` — [MEDIUM] the tolerance is silently discarded as the code compares integers exactly
  - says: the k-th burg holds P1/k, independently recomputed
- **standards.py** `scoreable` — [MEDIUM] count of rows that can be scored
  - says: count of scoreable rows
- **standards.py** `inside` — [MEDIUM] count of references matching the charter interval with a tolerance
  - says: count of references inside the charter interval
- **standards.py** `unans_files` — [MEDIUM] calculated inside a try block that does not handle the case where the directory is missing or renamed
  - says: Cached on a 2-minute clock
- **standards.py** `_dropped` — [MEDIUM] appended to when a failure occurs, but the code around it says it should be used when a measurement is not taken
  - says: the mechanism for "unmeasurable"
- **feats_index.py** `load_index` — [MEDIUM] WHAT IT COULD NOT INDEX IS COUNTED, not merely skipped
  - says: WHAT IT COULD NOT INDEX IS COUNTED, not merely skipped
- **feats_index.py** `host_to_sources` — [MEDIUM] RAISES an exception when the host file cannot be read
  - says: RAISES rather than returning an empty map when the host file cannot be read
- **pipeline.py** `land_json` — [MEDIUM] land_json is used to land JSON data but the code around it suggests it should be derived
  - says: land_json is used to land JSON data

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
