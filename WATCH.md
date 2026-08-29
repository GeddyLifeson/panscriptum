# OVERWATCH

round 141  ·  last run 2026-08-29 02:45

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **0** of 271,124 inspected (deep scan as of round 139)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**10 open** (6 high). Newest first.

- **magnitude.py** `verify` — [HIGH] decides on the SENTENCE alone
  - says: the entity must be the DOER
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
- **manifest_builder.py** `volume_code` — [MEDIUM] The code assigns volume numbers based on sorted source names, but the logic for generating the volume code may not correctly reflect the intended deterministic assignment based on 
  - says: Volume numbers are assigned deterministically by sorted source name so the address of a given book is stable across rebuilds.
- **manifest_builder.py** `volume_code` — [MEDIUM] volume_code is assigned based on sorted source names, but the code does not ensure that the Volume numbers are assigned correctly according to the Series code and source name order
  - says: Resolve each source to its Series code first, THEN hand out Volume numbers where a Series holds more than one source.
- **magnitude.py** `main` — [MEDIUM] always returns 0, but the script may have failed
  - says: exits with 0 on success
- **magnitude.py** `run_batch` — [MEDIUM] ASSAYS.json is not rewritten on each completion, but instead loaded once at the beginning and then overwritten at the end
  - says: Written to be killed. The roll runs for hours against a rate-limited pool, and a crash at hour three must not cost hours one and two -- so ASSAYS.json is rewrit

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
