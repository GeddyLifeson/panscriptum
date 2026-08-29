# OVERWATCH

round 140  ·  last run 2026-08-29 02:21

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 271,124 inspected (deep scan as of round 139)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**5 open** (5 high). Newest first.

- **local_agent.py** `t_propose_patch` — [HIGH] does not handle failed reverts, does not trigger exit code
  - says: A FAILED REVERT MUST REACH THE EXIT CODE.
- **liveness.py** `scoped` — [HIGH] a dictionary that is never populated because the loop that assigns it is never executed
  - says: a dictionary mapping keys to sets of attributes
- **ingest_doc.py** `main` — [HIGH] returns 0 regardless of input
  - says: entry point for the script
- **ingest_doc.py** `write_record_catalogue` — [HIGH] the code calls write_record_catalogue but the comment says it should be write_record
  - says: ADVANCE ON THE WRITE, NOT ON THE INTENT
- **gpu_lane.py** `_heartbeat` — [HIGH] Does not actually keep leases fresh; it was supposed to call _touch to refresh leases but does not do so.
  - says: Keep every lease this call holds fresh until the call finishes.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
