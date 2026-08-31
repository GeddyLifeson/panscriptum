# OVERWATCH

round 225  ·  last run 2026-08-30 22:58

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 283,040 inspected (deep scan as of round 223)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**17 open** (6 high). Newest first.

- **local_agent.py** `verify_math.py` — [HIGH] the gate runs only for Python files
  - says: the whole-suite gate runs for every file type, not just Python
- **escalation.py** `clear` — [HIGH] clear() returns False for two different reasons
  - says: clear() raises PermissionError for non-person callers
- **drill.py** `a_pure_ladder_is_all_ladder` — [HIGH] The function returns True if the decomposition result has converged, no evidence is False, eta is 1.0, curl fraction is 0.0, and irreducibly_chord is 0.0. However, the claim states that the STAR shape should return eta 0.0, which contradicts the actual code's expectation of eta 1.0.
  - says: A STAR is EXACTLY representable: theta_a = 0.75, the three losers -0.25 each, reproducing every edge. eta must be 1.0 and the curl fraction 0.0. Under Jacobi this was 0.0 -- the answer for a shape with NO ladder in it at all, returned for a shape that is nothing but ladder.
- **drill.py** `catalog_matches_disk` — [HIGH] only checks that the catalog does not claim chapters that do not exist on disk
  - says: Every chapter the catalog claims exists on disk, AND VICE VERSA — both directions.
- **verify_math.py** `priority` — [HIGH] excludes rows with own=0 and chars < 2000
  - says: These are still read -- nothing here is dropped
- **verify_math.py** `AS.map_seed` — [HIGH] the same function object is used, not a re-computed value
  - says: DERIVED — an independently loaded copy of the module recomputes it
- **local_agent.py** `rel_real` — [MEDIUM] path the filesystem actually resolves to relative to real_here
  - says: path the filesystem actually resolves to
- **escalation.py** `status` — [MEDIUM] returns (not rec.get("cleared", False)), rec
  - says: -> (halted: bool, record or None).
- **escalation.py** `WO.file_order` — [MEDIUM] the code is passing 'where' and 'evidence' as keyword arguments, but the function may not be designed to handle them, leading to potential misuse or incorrect behavior
  - says: file_order is called with parameters including 'where' and 'evidence'
- **escalation.py** `escalate` — [MEDIUM] Reports at the level specified, but does not actually record at every rung beneath as described. The function only records at the level specified and the log files are not guaranteed to capture all rungs beneath.
  - says: Report something amiss at `level`, recording it at every rung beneath as well.
- **drill.py** `main` — [MEDIUM] raises SystemExit on main()
  - says: entry point for the module
- **drill.py** `coverage_totals_never_exceed_their_entry_count` — [MEDIUM] checks that the states do not sum PAST the entry count
  - says: No source's states may sum PAST its own entry count. One direction, and only one.
- **generate.py** `save_raw` — [MEDIUM] is called with text that was not skipped
  - says: FILED AND SKIPPED LIKE EVERY OTHER REFUSAL IN THIS LOOP
- **verify_math.py** `check` — [MEDIUM] a function that checks a condition and raises an error if it fails
  - says: a function that checks a condition and raises an error if it fails
- **verify_math.py** `_KEY_SPELLING` — [MEDIUM] a string used to find code that rebuilds the entity cache path by hand
  - says: a string used to find code that rebuilds the entity cache path by hand
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops
- **foreman.py** `kill_stalled` — [MEDIUM] kill stalled jobs that can be restarted, and escalate those that cannot
  - says: kill stalled jobs

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
