# OVERWATCH

round 82  ·  last run 2026-08-26 11:14

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **0** of 198,069 inspected
- catalogued sources with no host: **15** Clockwork Angels (Rush), Curious DM Investigations (the Sharkin), Genuine Fantas
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**4 open** (2 high). Newest first.

- **chain.py** `work` — [HIGH] increments `unmatched` directly without proper locking
  - says: TALLIED LOCALLY, MERGED UNDER THE LOCK, for the same reason `local` exists.
- **binding_health.py** `quarantine` — [HIGH] If the write to disk fails, it still records the host as quarantined in memory but does not escalate the failure to write, leading to potential inconsistencies.
  - says: Record a host as failing, WITH ITS REASON. Never a silent skip, never a deletion.
- **cleanup.py** `changed` — [MEDIUM] sometimes not set when a thin description is marked
  - says: tracking whether any changes were made to a record
- **catalogue_models.py** `stale` — [MEDIUM] the code appends entries to stale with the available models, which are the names, not the keys
  - says: the keys work; the names do not.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
