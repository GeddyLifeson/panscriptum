# OVERWATCH

round 281  ·  last run 2026-09-02 15:14

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 289,399 inspected (deep scan as of round 277)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**18 open** (3 high). Newest first.

- **verify_math.py** `_cb20i.UNRECOGNISED` — [HIGH] replaces the UNRECOGNISED attribute with the path
  - says: retrieves the path to the unrecognised ledger
- **verify_math.py** `check` — [HIGH] the k-th burg holds P1/k, but the code compares it to a value that is not derived from P1/k and instead uses a hardcoded value that is incorrect
  - says: the k-th burg holds P1/k, independently recomputed
- **drill.py** `drill_no_top_ups` — [HIGH] The function's implementation does not align with the ruling's intent, as it does not properly distinguish between cooldown and pay-to-continue scenarios.
  - says: OWNER RULING 2026-08-26: cooldown is fine; pay-to-continue is axed.
- **repass_bands.py** `PL.write_record` — [MEDIUM] The code appends to `touched` regardless of the result of `write_record`
  - says: GATE ON THE WRITE. `write_record` returns whether the write LANDED; this ignored it and appended to `touched` regardless, so the run's closing "APPLIED. N rewritten" counted sources whose file was never modified.
- **profile.py** `encode` — [MEDIUM] the code does not use it correctly
  - says: the code says it does
- **verify_math.py** `_ALL_SRC` — [MEDIUM] list of all .py files in the current directory (which may not be the src directory)
  - says: list of all .py files in the src directory
- **verify_math.py** `_KEY_SPELLING` — [MEDIUM] a string used as a search pattern for the key spelling in source files
  - says: "_", name)[:80]
- **verify_math.py** `check` — [MEDIUM] checks if the code contains 'not enough history yet'
  - says: and it reports short history honestly instead of vanishing
- **thread_integrity.py** `dangling` — [MEDIUM] dangling is assigned the value of counts.get("DANGLING", 0), which is the count of DANGLING entries, not the actual list of DANGLING entries
  - says: THE UNIT IS SOURCE PAIRS, NOT THREADS, and this is the line the module will be read on as a release gate (STEP4_PLAN.md §8), so it says which. Each DANGLING row prints n of tot keys gone, so one pair here can stand for a hundred vanished entities.
- **thread_integrity.py** `implied_threads` — [MEDIUM] implied_threads is called but its output is not used in the code slice provided
  - says: NAMED FOR WHAT IT COUNTS (order 30581ee9cca2). `implied_threads` adds both (a,b) and (b,a) for every shared entity, so this is DIRECTED and is exactly twice the deduped pair count `classify` reports two lines below -- the same population, printed twice, 2x apart, with nothing on the page saying so.
- **drill.py** `breached` — [MEDIUM] list of results where 'held' is False
  - says: list of results where 'held' is False
- **drill.py** `held` — [MEDIUM] count of results where 'held' is True
  - says: sum(1 for r in RESULTS if r['held'])
- **drill.py** `coverage_totals_never_exceed_their_entry_count` — [MEDIUM] sums all five columns but the docstring says it only checks one direction
  - says: No source's states may sum PAST its own entry count. One direction, and only one.
- **drill.py** `catalog_matches_disk` — [MEDIUM] only checks catalog to disk, not disk to catalog
  - says: Every chapter the catalog claims exists on disk, AND VICE VERSA — both directions.
- **drill.py** `dead_forever` — [MEDIUM] buries the permanent codes and the timeout code
  - says: buries the permanent codes and ONLY those
- **escalation.py** `clear` — [MEDIUM] clear() returns False for two different reasons, but the code treats them as the same event, leading to incorrect messages about the lift not happening.
  - says: PermissionError is caught alongside ValueError because `clear()` raises it for a non-person caller, and the two refusals are the same event to a reader: the lift did not happen and here is why.
- **cascade_bridge.py** `selftest` — [MEDIUM] executes the live check
  - says: The live check is NOT dropped
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
