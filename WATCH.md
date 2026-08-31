# OVERWATCH

round 246  ·  last run 2026-08-31 13:14

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 285,721 inspected (deep scan as of round 241)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**13 open** (6 high). Newest first.

- **drill.py** `third_writer_detected` — [HIGH] a third writer is not detected
  - says: an entry added outside the writer is DETECTED
- **allsweep.py** `bad` — [HIGH] sum of various counts including reconcile findings which are not all faults
  - says: count of bad subsystems
- **cosmology_graph.py** `components` — [HIGH] clusters at weight >= threshold, but the threshold is not applied correctly in the function
  - says: CANDIDATE CLUSTERS at weight >= {args.threshold} : {len(comps)}
- **withdraw_chapters.py** `shutil.move` — [HIGH] THE RECORD IS NOT KEPT (entry_left is not updated).
  - says: THE RECORD IS KEPT AND MADE TRUE.
- **withdraw_chapters.py** `shutil.move` — [HIGH] A FAILED MOVE discards the record (adds to stuck).
  - says: A FAILED MOVE KEEPS ITS RECORD.
- **wiki_source.py** `resolve_wiki` — [HIGH] Does not consult the library's host map and instead relies on guessing subdomains
  - says: Return (subdomain, sitename) for a verified wiki, or (None, None). THE LIBRARY'S OWN HOST MAP IS CONSULTED FIRST.
- **thread_integrity.py** `out["IMPLIED-UNRECORDED"]` — [MEDIUM] used in two places, once for partially dangling pairs and once for pairs where neither end records the thread, leading to potential double-counting
  - says: counts pairs where neither end records the thread
- **thread_integrity.py** `out["PARTIALLY-DANGLING"]` — [MEDIUM] increments the count for partially dangling pairs, but the comment indicates that this should be for pairs that have drifted
  - says: counts the number of pairs that are partially dangling
- **drill.py** `resync_cannot_revert_an_exclusion` — [MEDIUM] The function checks for guards in the parse tree that ensure excluded sources do not have their status rewritten, but the comment suggests it's about preventing silent promotion back, which is not directly addressed by the code.
  - says: THE TRAP THIS ALMOST FELL INTO. `resync_roll` rebuilds status from records on disk with the rule `catalogued if n else keep` -- so an excluded source that still HAS records would be silently promoted back. All four of the 2026-08-25 exclusions have records.
- **drill.py** `catalog_matches_disk` — [MEDIUM] only checks that the catalog entries exist on disk
  - says: Every chapter the catalog claims exists on disk, AND VICE VERSA — both directions.
- **withdraw_chapters.py** `bad` — [MEDIUM] The variable 'bad' is computed based on conditions that may not align with the actual exit code logic, potentially leading to incorrect exit codes.
  - says: EVERY REFUSAL ABOVE WAS PRINTED AND THEN DISCARDED. `main()` had no `return` on any path and the entry point was a bare `main()`...
- **tiers.py** `main` — [MEDIUM] returns 0 if the write was successful, else 1
  - says: returns 0 if the rename landed, else 1
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
