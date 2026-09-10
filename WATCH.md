# OVERWATCH

round 471  ·  last run 2026-09-10 02:33

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 302,231 inspected (deep scan as of round 469)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**54 open** (24 high). Newest first.

- **feats_index.py** `host_to_sources` — [HIGH] returns an empty map and does not raise an exception
  - says: RAISES rather than returning an empty map when the host file cannot be read
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
- **corpus_db.py** `rebuild` — [HIGH] Rebuilds the index but does not process JSON files correctly, leading to potential data loss or incorrect counts.
  - says: Rebuild the index from the canonical JSON. -> counts.
- **binding_health.py** `run` — [HIGH] Returns an empty list and 0 on an empty or unreadable hosts map, which contradicts the claim that it canary every bound host.
  - says: Canary every bound host. Error-resilient: one bad host never aborts the sweep.
- **magnitude.py** `verify` — [HIGH] Applies guards 1-3 but also handles status scores and fabricates provenance for empty citations
  - says: Apply guards 1-3. Returns (scores, worksheet, rejections).
- **endpoint.py** `register` — [HIGH] Attempts to write a temporary file without proper atomic operations, leading to potential data loss or corruption due to concurrent writes.
  - says: Record where a source's material actually lives.
- **overnight.py** `snap` — [HIGH] snap is updated with cycle and at information even when there's an error
  - says: A crashed snapshot carries ONLY an "error" key
- **grounding.py** `silence.write_json` — [HIGH] writes JSON to the file and returns a boolean indicating success
  - says: uses to mean "this run did not do what it was asked"
- **feats_index.py** `entries_by_norm` — [MEDIUM] used downstream when the feats prose is generated -- is taken from the correct one of two same-named catalogue entries.
  - says: description and magnitude used downstream when the feats prose is generated -- is taken from the wrong one of two same-named catalogue entries.
- **feats_index.py** `index_faults` — [MEDIUM] Builds the index if it has not been built, but the function does not handle the case where the index is built but has faults.
  - says: Builds the index if it has not been built, so the answer is never a stale zero.
- **feats_index.py** `load_index` — [MEDIUM] counts unreadable records but not collided keys
  - says: WHAT IT COULD NOT INDEX IS COUNTED, not merely skipped
- **feats_index.py** `_norm` — [MEDIUM] normalises a string to lowercase and alphanumeric characters
  - says: normalises a string to lowercase and alphanumeric characters
- **completeness.py** `no_denominator` — [MEDIUM] a case where all category probes were answered and none existed
  - says: a THIRD answer beside those two
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
- **chain.py** `write_result` — [MEDIUM] the edge list is written only when strengths are present
  - says: the edge list is still the finding, so it is written either way
- **cascade_bridge.py** `ask` — [MEDIUM] ask is called with max_attempts=1 but the comment suggests it's to prevent neighbor buckets from answering, but the code allows neighbor buckets to answer because the max_attempts=1 is not sufficient to prevent it
  - says: ask is called with max_attempts=1 to prevent neighbor buckets from answering
- **cascade_bridge.py** `_reset` — [MEDIUM] reset the strike count for a bucket if it exists
  - says: reset the strike count for a bucket
- **cascade_bridge.py** `_bucket_of` — [MEDIUM] returns the bucket name from a model's answer or an empty string if unresolved
  - says: returns the bucket name from a model's answer
- **burgs.py** `burg_link` — [MEDIUM] Generates a URL that includes the 'burg' parameter, which is supposed to be handled by Azgaar, but the function's implementation may not correctly reflect this if it's not using the correct parameters or if there's a misunderstanding in the URL construction.
  - says: The route to a settlement's own map: THROUGH Azgaar, not around it.
- **binding_health.py** `tight` — [MEDIUM] a fuzz ratio score between 0 and 100
  - says: the same pair judged as whole strings, and the distance between them is how one-sided the match is
- **binding_health.py** `containment` — [MEDIUM] a boolean indicating whether one set of words is a subset of the other
  - says: the strength of the evidence, not a second verdict. `containment` says one name's words sit wholly inside the other's, which is what `token_set_ratio` scores 100
- **binding_health.py** `binding_verdict` — [MEDIUM] Returns a verdict based on string similarity between the sitename and source names, but the function's purpose is to determine if the binding is correct or not, which is not directly related to the string similarity score.
  - says: Does the wiki's own name correspond to the source bound to it?
- **binding_health.py** `available` — [MEDIUM] passed in
  - says: UNMEASURED
- **binding_health.py** `PRESENT_CANDIDATES` — [MEDIUM] hardcoded value
  - says: bound
- **physics.py** `joules_for` — [MEDIUM] Energy to do `mode` to `volume_m3` of `material` with a default material of 'rock' and mode of 'pulv'.
  - says: Energy to do `mode` to `volume_m3` of `material`.
- **hosts.py** `discover` — [MEDIUM] Only keeps hosts that score well on LIFT, and discards others
  - says: Find every ADDITIONAL host each source can be read from, and keep all that hold.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
