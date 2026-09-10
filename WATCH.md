# OVERWATCH

round 474  ·  last run 2026-09-10 06:08

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 302,231 inspected (deep scan as of round 469)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**60 open** (27 high). Newest first.

- **mutate.py** `_lock_acquire` — [HIGH] Acquires a lock and writes a token to it, but the function is named and documented as releasing a lock.
  - says: Drop the lock, but only if it is still OURS.
- **chain.py** `main` — [HIGH] the main function is not defined in this slice
  - says: the main function
- **pipeline.py** `build_jobs_for_source` — [HIGH] The function is called with only two arguments, but the comment claims it should be called with four, leading to incorrect behavior where sources are marked as refusing to build when they actually have no entries.
  - says: The real signature is build_jobs_for_source(cfg, roll_entry, record, spine) -- four arguments, in that order. Calling it with two produced "117 sources would not build", which reads as a property of the sources and was a property of the call.
- **pipeline.py** `rest` — [HIGH] the rest of the entries are added to the nomination blocks
  - says: the description-only fallback stays a single ranked block
- **local_agent.py** `t_propose_patch` — [HIGH] appends to `unreverted` but does not raise an alarm or note
  - says: raises the durable alarms for this case -- a SAFETY escalation and a `silence.note`
- **local_agent.py** `_rel_l` — [HIGH] The code converts the relative path to lowercase, making the comparison case-insensitive, which contradicts the claim that the denylist is case-sensitive.
  - says: THE DENYLIST IS CASE-SENSITIVE AND THE FILESYSTEM IS NOT.
- **local_agent.py** `_mod_l` — [HIGH] The code converts the module name to lowercase, making the comparison case-insensitive, which contradicts the claim that the denylist is case-sensitive.
  - says: THE DENYLIST IS CASE-SENSITIVE AND THE FILESYSTEM IS NOT.
- **local_agent.py** `_deny_paths` — [HIGH] The code converts the denylist paths to lowercase, making the deny, which contradicts the claim that the denylist is case-sensitive.
  - says: THE DENYLIST IS CASE-SENSITIVE AND THE FILESYSTEM IS NOT.
- **local_agent.py** `_deny` — [HIGH] The code converts the denylist to lowercase, making the denylist case-insensitive, which contradicts the claim that the denylist is case-sensitive.
  - says: THE DENYLIST IS CASE-SENSITIVE AND THE FILESYSTEM IS NOT.
- **feats.py** `_QUANTITY_UNIT_FIRST` — [HIGH] The regex looks for 'mach' followed by a number, but the comment says it's for number-first forms
  - says: Matches unit-first forms like '5 mach'
- **feats.py** `_QUANTITY_UNIT_FIRST` — [HIGH] Matches 'mach 5' (unit-first) but the comment says it's for number-first forms
  - says: Matches unit-first forms like '5 mach'
- **feats.py** `known` — [HIGH] A CLEAN NEGATIVE IS CACHED AS A NULL
  - says: A CLEAN NEGATIVE MAY BE CACHED
- **feats.py** `known` — [HIGH] A NULL IS CACHED AS A FAILURE AND IS A NEGATIVE
  - says: A NULL IS A CACHED FAILURE, NOT AN ANSWER
- **feats.py** `mined_under_failed_transport` — [HIGH] returns False for 404 responses, which is the opposite of what the docstring claims
  - says: -> did this record's fetch FAIL, leaving an absence that is not evidence of absence?
- **events.py** `shelf_positions` — [HIGH] Joins shelf names with their positions by parsing lines containing 'Shelf' and 'stands at' and extracting the shelf and its position.
  - says: Parsed but NOT joined here. Whether a shelf name corresponds to a source on the Acquisitions Roll is `threads.py`'s question, answered by the address resolver, never by this module.
- **drill.py** `landed` — [HIGH] the verdict did not land, but the code proceeds as if it did
  - says: the verdict landed in state/drill_last.json
- **drill.py** `a_second_fault_corroborates_and_does_not_bury_the_first` — [HIGH] the function is incomplete and does not perform the intended action
  - says: a second fault corroborates and does not bury the first
- **drill.py** `ESC.brief` — [HIGH] empties every brief
  - says: keeps what the rung needs and drops the rest
- **drill.py** `drill_probe_honesty` — [HIGH] The probe incorrectly certifies hosts as healthy even when they should be considered unreachable or faulty.
  - says: The probe returns True on every exception, certifying hosts it never tested
- **drill.py** `drill_probe_honesty` — [HIGH] The function returns True for all exceptions, including those that should indicate a host is unreachable or faulty.
  - says: A probe that could not run must not be counted as a probe that passed.
- **drill.py** `catalog_matches_disk` — [HIGH] Only checks that chapters in the catalog exist on disk (catalog -> disk), but not that chapters on disk are in the catalog (disk -> catalog)
  - says: Every chapter the catalog claims exists on disk, AND VICE VERSA — both directions.
- **drill.py** `LA.t_propose_patch` — [HIGH] is called with the un-resolved path
  - says: is called with the resolved path
- **canon_backup.py** `silence.replace_retry` — [HIGH] the function is called and the result is checked, but the code raises an exception when the result is False, which contradicts the contract that `replace_retry` never raises
  - says: THE VERDICT IS CHECKED, WHICH IS THE HALF THAT MATTERS. `replace_retry` NEVER RAISES, by contract; it reports False.
- **descending_ladder.py** `beta` — [HIGH] beta is initialized to 0.0 but the code does not actually modify it in the if conditions
  - says: beta is initialized to 0.0 and then modified based on conditions
- **cascade_bridge.py** `pinned` — [HIGH] can be assigned a local bucket
  - says: never dispatches to the local GPU
- **corpus_db.py** `main` — [HIGH] It skips the freshness check for --canned queries, leading to potential unhandled exceptions when the database file is missing
  - says: The code says it handles --canned queries safely
- **grounding.py** `silence.write_json` — [HIGH] writes JSON to the file and returns a boolean indicating success
  - says: uses to mean "this run did not do what it was asked"
- **mutate.py** `judged_since` — [MEDIUM] record of verdicts cast by the current baseline
  - says: record of verdicts cast by the current baseline
- **mutate.py** `owner` — [MEDIUM] Return the owner's PID if it exists, otherwise None
  - says: Record this process as the sandbox's owner. Never raises.
- **mutate.py** `suppressed_on_record` — [MEDIUM] filters for ruled_equivalent but not revoked
  - says: every survivor a standing ruling kept out of the queue
- **ingest_doc.py** `fresh` — [MEDIUM] fresh entries with potential category issues
  - says: fresh entries
- **ingest_doc.py** `misses` — [MEDIUM] count of misses leading to stop
  - says: count of misses
- **ingest_doc.py** `rec` — [MEDIUM] record data loaded from file
  - says: record data
- **ingest_doc.py** `chunks` — [MEDIUM] list of chunks with labels and text
  - says: list of chunks to process
- **ingest_doc.py** `cur_pages` — [MEDIUM] current labels being tracked
  - says: current pages being tracked
- **retry_synthesis.py** `PL._stored_cut` — [MEDIUM] applies a fixed cut length
  - says: keeps the two writers in step through the NEXT change to it
- **feats_index.py** `load_index` — [MEDIUM] WHAT IT COULD NOT INDEX IS COUNTED, not merely skipped
  - says: WHAT IT COULD NOT INDEX IS COUNTED, not merely skipped
- **feats_index.py** `host_to_sources` — [MEDIUM] RAISES an exception when the host file cannot be read
  - says: RAISES rather than returning an empty map when the host file cannot be read
- **pipeline.py** `land_json` — [MEDIUM] land_json is used to land JSON data but the code around it suggests it should be derived
  - says: land_json is used to land JSON data
- **pipeline.py** `batch_settled` — [MEDIUM] the function is called but its purpose is not clear from the code
  - says: what the write-gate comment below already priced and accepted.
- **local_agent.py** `_gates` — [MEDIUM] parse, lint, import, but not whole-suite
  - says: parse, lint, import, whole-suite
- **local_agent.py** `_scan` — [MEDIUM] scan a file but ignore line numbers and content
  - says: scan a file for regex matches
- **local_agent.py** `rel_real` — [MEDIUM] compares the normalized case of the relative paths, but the check for denied target is based on the resolved path's region and paths, not the original string-based path.
  - says: compare the two project-relative spellings, and only interrogate the resolved one when the filesystem disagrees with the string.
- **local_agent.py** `rel_written` — [MEDIUM] compares the normalized case of the relative paths, but the check for denied target is based on the resolved path's region and paths, not the original string-based path.
  - says: compare the two project-relative spellings, and only interrogate the resolved one when the filesystem disagrees with the string.
- **codewatch.py** `reportable` — [MEDIUM] a set of jobs derived from coverage() with a split on job names
  - says: a set of reportable jobs
- **drill.py** `index_spine_agrees_with_the_resolver` — [MEDIUM] The function checks if the stored spine code matches the real spine code, but the comment suggests it should verify that the index's spine column is derived through the same resolver code as `address.spine_code_for()`
  - says: THE ONE THAT ALREADY COST A FALSE ALARM. The index's `spine` column must come from `address.sp,ine_code_for()`, not from a simpler reimplementation of it.
- **drill.py** `CW._budget_left` — [MEDIUM] is used to check if the budget is exhausted, but the docstring indicates that the budget-exhausted branch is the only safe one to drive, and the actual code may not be correctly implementing this logic
  - says: Spend the budget against a scratch ledger and require it to RUN OUT, then refill.
- **drill.py** `ESC._safe_name` — [MEDIUM] suffixes every short name and truncates no long one
  - says: sanitises source names
- **drill.py** `coverage_totals_never_exceed_their_entry_count` — [MEDIUM] The code checks for overflow (sum exceeding entry count) but the docstring and comment mention a correction that the code does not implement
  - says: No source's states may sum PAST its own entry count. One direction, and only one.
- **drill.py** `PL.write_record` — [MEDIUM] returns False instead of denying the write
  - says: a write that is denied
- **drill.py** `multi_line` — [MEDIUM] controls whether the input is multi-line, but the variable is named 'multi_line' which is misleading
  - says: controls whether the input is multi-line
- **drill.py** `seam` — [MEDIUM] controls the maximum number of lines to read, but the variable is named 'seam' which is misleading
  - says: controls the maximum number of lines to read
- **drill.py** `cap` — [MEDIUM] controls the maximum number of lines to read, but the variable is named 'cap' which is misleading
  - says: controls the maximum number of lines to read
- **drill.py** `only` — [MEDIUM] checks if a string is the only one in a list, but the function is named 'only' which is misleading
  - says: checks if a string is the only one in a list
- **drill.py** `F._restartable` — [MEDIUM] asserts the target is restartable and checks agreement between _restart, _restart_horizon
  - says: A remedy never kills a job nothing would restart
- **drill.py** `F._restartable` — [MEDIUM] asserts the target is restartable and checks agreement between _restartable and _restart_horizon
  - says: A remedy never kills a job nothing would restart
- **drill.py** `_empty` — [MEDIUM] The function writes an empty config.yaml and checks if the gates refuse it for the wrong reason
  - says: The gates must READ config.yaml, not merely survive opening it.
- **cascade_bridge.py** `ask` — [MEDIUM] ask is called with max_attempts=1 but the comment suggests it's to prevent neighbor buckets from answering, but the code allows neighbor buckets to answer because the max_attempts=1 is not sufficient to prevent it
  - says: ask is called with max_attempts=1 to prevent neighbor buckets from answering
- **cascade_bridge.py** `_reset` — [MEDIUM] reset the strike count for a bucket if it exists
  - says: reset the strike count for a bucket
- **cascade_bridge.py** `_bucket_of` — [MEDIUM] returns the bucket name from a model's answer or an empty string if unresolved
  - says: returns the bucket name from a model's answer

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
