# OVERWATCH

round 170  ·  last run 2026-08-29 18:25

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 275,602 inspected (deep scan as of round 169)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**5 open** (2 high). Newest first.

- **ingest_doc.py** `main` — [HIGH] return sys.exit(main())
  - says: return 0
- **generate.py** `generate_job` — [HIGH] does not exist in this code slice
  - says: generates a job's text
- **gpu_lane.py** `_take_slot` — [MEDIUM] Attempts to create a file with O_CREAT|O_EXCL but may return None on failure without proper error handling
  - says: Claim one of MAX_SLOTS leases, or return None if they are all live
- **gpu_lane.py** `_write_claim` — [MEDIUM] Returns a boolean indicating success, but the actual replacement is handled by replace_retry which may not be properly handled in some cases
  - says: Write a claim to a file, ensuring it's replaced
- **generate.py** `_PG` — [MEDIUM] used as a variable name for the prose_gate module, not the module itself
  - says: imported module for prose gate checks

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
