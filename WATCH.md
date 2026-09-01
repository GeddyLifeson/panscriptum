# OVERWATCH

round 247  ·  last run 2026-08-31 13:49

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 286,381 inspected
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**25 open** (7 high). Newest first.

- **genre.py** `classify_source` — [HIGH] Truncates the entry list in stored order, which changes the classification for some sources
  - says: Classifies a source based on its entries and returns genre, score, confidence, etc.
- **drill.py** `excluded` — [HIGH] fetches the exclusions from a variable that is not used elsewhere in the code
  - says: fetches the exclusions on the path the program actually runs
- **drill.py** `ESC` — [HIGH] ESC is not defined anywhere in this slice or its visible imports; referencing it raises NameError
  - says: ESC.SUPERVISOR is accessed as if ESC is a module or object with a SUPERVISOR attribute
- **drill.py** `RESULTS` — [HIGH] RESULTS is never defined or imported in this module, so referencing it raises a NameError
  - says: net() appends a dict to the global RESULTS list to record the attack outcome
- **allsweep.py** `bad` — [HIGH] sum of various counts including reconcile findings which are not all faults
  - says: count of bad subsystems
- **cosmology_graph.py** `components` — [HIGH] clusters at weight >= threshold, but the threshold is not applied correctly in the function
  - says: CANDIDATE CLUSTERS at weight >= {args.threshold} : {len(comps)}
- **withdraw_chapters.py** `shutil.move` — [HIGH] THE RECORD IS NOT KEPT (entry_left is not updated).
  - says: THE RECORD IS KEPT AND MADE TRUE.
- **genre.py** `HERE` — [MEDIUM] undefined variable
  - says: used to construct file path
- **genre.py** `silence` — [MEDIUM] undefined variable
  - says: used to write JSON atomically
- **drill.py** `filters` — [MEDIUM] is a boolean flag that is set to True if any condition in a comprehension uses the exclusion list
  - says: checks if the exclusion list is used in a comprehension filter
- **drill.py** `reap_orphans` — [MEDIUM] deletes directories based on age and ownership claims
  - says: reaping a directory to demonstrate the net now requires that directory to have a dead or absent owner
- **drill.py** `_a_scan_can_tell_code_from_prose_about_code` — [MEDIUM] The other half of the same family, and it cost a halt this morning
  - says: The other half of the same family, and it cost a halt this morning
- **drill.py** `_counts_decided_by_substring` — [MEDIUM] -> [site] where a gate reads a NUMBER out, but the logic is flawed and may not correctly identify all cases
  - says: -> [site] where a gate reads a NUMBER out of process output with `in`
- **drill.py** `_is_process_output` — [MEDIUM] Determines if an AST node represents an expression that plausibly holds the text a subprocess printed
  - says: Determines if an AST node represents an expression that plausibly holds the text a subprocess printed
- **drill.py** `_calls_within` — [MEDIUM] Checks if a function `main` in a module calls a specific function `codewatch.claim_singleton`
  - says: Checks if a function `main` in a module calls a specific function `codewatch.claim_singleton`
- **drill.py** `coverage_totals_never_exceed_their_entry_count` — [MEDIUM] checks that the sum of states does not exceed the entry count
  - says: No source's states may sum PAST its own entry count. One direction, and only one.
- **drill.py** `restore_then_mangle` — [MEDIUM] modifies the file after restoration but does not return the modified file handle
  - says: mangles the file after restoration
- **drill.py** `SNAP.verify` — [MEDIUM] returns a tuple where the first element is a boolean indicating success
  - says: must return False with a reason that says the bytes differ
- **drill.py** `snapshot` — [MEDIUM] A function that creates temporary directories and verifies snapshots, but does not actually prove directories file by file as described
  - says: A snapshotted DIRECTORY must be proved file by file, not by the folder still existing.
- **drill.py** `drill_profile` — [MEDIUM] A function that runs tests related to the profile's decoding behavior
  - says: One string that says everything — including, if the alphabet is wrong, something else.
- **drill.py** `PG.step4_gate_open` — [MEDIUM] the redirect never reached the predicate
  - says: the redirect never reached the predicate
- **thread_integrity.py** `out["IMPLIED-UNRECORDED"]` — [MEDIUM] used in two places, once for partially dangling pairs and once for pairs where neither end records the thread, leading to potential double-counting
  - says: counts pairs where neither end records the thread
- **thread_integrity.py** `out["PARTIALLY-DANGLING"]` — [MEDIUM] increments the count for partially dangling pairs, but the comment indicates that this should be for pairs that have drifted
  - says: counts the number of pairs that are partially dangling
- **withdraw_chapters.py** `bad` — [MEDIUM] The variable 'bad' is computed based on conditions that may not align with the actual exit code logic, potentially leading to incorrect exit codes.
  - says: EVERY REFUSAL ABOVE WAS PRINTED AND THEN DISCARDED. `main()` had no `return` on any path and the entry point was a bare `main()`...
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
