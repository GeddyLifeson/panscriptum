# OVERWATCH

round 282  ·  last run 2026-09-02 15:52

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 289,399 inspected (deep scan as of round 277)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**18 open** (4 high). Newest first.

- **worldseed.py** `write_json` — [HIGH] returns True on a successful write
  - says: returns False on a denied replace instead of raising
- **worldseed.py** `build_all` — [HIGH] The function attempts to build data structures but has a defect in handling the 'continuity_groups' JSON file. It does not correctly process the 'groups' data and may not handle errors properly, leading to potential issues in the build process.
  - says: Builds all the data structures needed for the worldseed library.
- **verify_math.py** `_cb20i.UNRECOGNISED` — [HIGH] replaces the UNRECOGNISED attribute with the path
  - says: retrieves the path to the unrecognised ledger
- **verify_math.py** `check` — [HIGH] the k-th burg holds P1/k, but the code compares it to a value that is not derived from P1/k and instead uses a hardcoded value that is incorrect
  - says: the k-th burg holds P1/k, independently recomputed
- **worldseed.py** `unreachable_by_url` — [MEDIUM] Returns a dictionary of opt items for keys that are not delivered via URL, but the function's name and comment suggest it's about what cannot be delivered via URL. However, the function's actual behavior is to return a subset of opt items, which is consistent with the claim. No defect of fact found.
  - says: What the profile derives that a query string cannot deliver. Named, not hidden.
- **worldseed.py** `seed_for` — [MEDIUM] Generates a 32-bit seed, but the hash is 64 characters long, and the first 8 hex digits are used, which is 32 bits. However, the function returns an integer, which can be up to 2^32 - 1, which is correct for a 32-bit seed.
  - says: 32-bit seed. Deterministic, so a world regenerates identically for anyone who has its row.
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
- **escalation.py** `clear` — [MEDIUM] clear() returns False for two different reasons, but the code treats them as the same event, leading to incorrect messages about the lift not happening.
  - says: PermissionError is caught alongside ValueError because `clear()` raises it for a non-person caller, and the two refusals are the same event to a reader: the lift did not happen and here is why.
- **cascade_bridge.py** `selftest` — [MEDIUM] executes the live check
  - says: The live check is NOT dropped
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
