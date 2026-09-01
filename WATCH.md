# OVERWATCH

round 248  ·  last run 2026-08-31 21:33

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 286,381 inspected (deep scan as of round 247)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**32 open** (5 high). Newest first.

- **drill.py** `a_raised_halt_reads_back_as_halted` — [HIGH] returns True only if the halt is marked as cleared, which contradicts the claim that it reads back as standing
  - says: a halt that was raised reads back as standing
- **genre.py** `classify_source` — [HIGH] Truncates the entry list in stored order, which changes the classification for some sources
  - says: Classifies a source based on its entries and returns genre, score, confidence, etc.
- **drill.py** `excluded` — [HIGH] fetches the exclusions from a variable that is not used elsewhere in the code
  - says: fetches the exclusions on the path the program actually runs
- **drill.py** `ESC` — [HIGH] ESC is not defined anywhere in this slice or its visible imports; referencing it raises NameError
  - says: ESC.SUPERVISOR is accessed as if ESC is a module or object with a SUPERVISOR attribute
- **drill.py** `RESULTS` — [HIGH] RESULTS is never defined or imported in this module, so referencing it raises a NameError
  - says: net() appends a dict to the global RESULTS list to record the attack outcome
- **drill.py** `the_verdict_travels_on_the_record` — [MEDIUM] returns True if the halt_landed is True, but the comment suggests it's about whether the halt was successful, which may not be the same
  - says: the record says whether the halt actually landed
- **drill.py** `net` — [MEDIUM] net runs a test that is not properly scoped to the function it's testing
  - says: net runs a test
- **drill.py** `brief_drops_none_but_keeps_falsey` — [MEDIUM] brief keeps falsey fields and drops only the absent ones
  - says: brief keeps present fields and drops only the absent ones
- **drill.py** `coverage_totals_never_exceed_their_entry_count` — [MEDIUM] Checks if the sum of states (cited, read, no_page, no_host) exceeds the entry count, returning False if it does.
  - says: No source's states may sum PAST its own entry count.
- **derivation.py** `band_edges_ruin` — [MEDIUM] X.2 §4 band edges
  - says: X.2 §4 band edges
- **cascade_bridge.py** `key` — [MEDIUM] the key is folded to lowercase, while the text is stored verbatim
  - says: folding here cannot hide anything: `text` -- the thing a person reads and classifies -- is stored verbatim
- **cascade_bridge.py** `key` — [MEDIUM] the key is derived from the bucket and text.lower()
  - says: the key is derived from the bucket and text
- **cascade_bridge.py** `client_rejection` — [MEDIUM] It is used in a condition to skip entries where the `v` string matches `local_transport` or `client_rejection`.
  - says: A FAULT ON THIS MACHINE IS NOT EVIDENCE ABOUT A PROVIDER'S ACCOUNT, and now that the provider's raw text reaches this line, it can arrive carrying one.
- **cascade_bridge.py** `local_transport` — [MEDIUM] It is used in a condition to skip entries where the `v` string matches `local_transport` or `client_rejection`.
  - says: A FAULT ON THIS MACHINE IS NOT EVIDENCE ABOUT A PROVIDER'S ACCOUNT, and now that the provider's raw text reaches this line, it can arrive carrying one.
- **build_terminal.py** `silence.replace_retry` — [MEDIUM] does unlink `tmp` when it fails
  - says: does NOT unlink `tmp` when it fails
- **build_terminal.py** `descend` — [MEDIUM] descend(key) calls layout, draw, resetView, and panel, which may cause the page to rebuild, but the function's name suggests it should only navigate without rebuilding
  - says: descend(key) is supposed to navigate to a key
- **build_terminal.py** `esc` — [MEDIUM] esc is a function that escapes HTML characters, but the code does not use it in the context of innerHTML
  - says: Every catalogue-derived string goes through this before it reaches innerHTML
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
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
