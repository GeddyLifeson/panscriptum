# OVERWATCH

round 229  ·  last run 2026-08-31 00:41

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 283,526 inspected
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **7** DC, HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, and 1 more

## What the model found in the code

**16 open** (2 high). Newest first.

- **allsweep.py** `bad` — [HIGH] sum of counts including ungraded reconcile rows
  - says: count of bad subsystems
- **escalation.py** `clear` — [HIGH] clear() returns False for two different reasons
  - says: clear() raises PermissionError for non-person callers
- **magnitude.py** `assay_entity` — [MEDIUM] returns a deferred status when the anchor is not in the ladder
  - says: assays an entity by trying different methods
- **identity.py** `identify` — [MEDIUM] Returns `(base, continuity)` only if `desig` is in `continuities`
  - says: Return `(base, continuity)` for a resolved wiki title.
- **hostcheck.py** `score` — [MEDIUM] score is called with by=by, but the by parameter is already passed as by[src], making the by=by redundant and possibly incorrect
  - says: score(host, by[src], src, by=by)
- **workorders.py** `_detector` — [MEDIUM] marks as detected regardless of whether an exception occurred
  - says: detects a problem and marks it as detected
- **publish.py** `_may_delete_in_export` — [MEDIUM] Checks if SITE is a different directory from HERE and if the marker file exists, but the function is supposed to determine if deletion is allowed based on the marker file alone
  - says: May anything be DELETED under `SITE` at all? -> bool
- **overnight.py** `snap` — [MEDIUM] snap is used to check for 'error' and other keys, but the code does not verify that 'error' is the only key present
  - says: A crashed snapshot carries ONLY an "error" key
- **overnight.py** `run` — [MEDIUM] Does not run after the reader; it runs concurrently with the reader due to the pipeline being started in the background
  - says: Runs after the reader so it sees the evidence the reader just produced
- **overnight.py** `preflight` — [MEDIUM] Returns (n_failing_checks, blocking) but the blocking check is based on a substring that may not be reliable due to potential changes in the label
  - says: Returns (n_failing_checks, blocking). Only corrupted source blocks.
- **overnight.py** `start` — [MEDIUM] Launches a job and returns a dictionary with the process and file handle
  - says: Launch a job without waiting for it.
- **allsweep.py** `VERIFIERS` — [MEDIUM] A list of Verifier objects with the argv that makes each one report rather than act, but the Verifier class's __iter__ method returns a tuple of (label, argv) instead of the actual arguments
  - says: A list of Verifier objects with the argv that makes each one report rather than act
- **allsweep.py** `Verifier` — [MEDIUM] An iterable that yields a two-element tuple (label, argv), but the __iter__ method returns iter((self.label, self.argv)) which is a tuple, not a list
  - says: An iterable that yields exactly (label, argv)
- **escalation.py** `status` — [MEDIUM] returns (not rec.get("cleared", False)), rec
  - says: -> (halted: bool, record or None).
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops
- **foreman.py** `kill_stalled` — [MEDIUM] kill stalled jobs that can be restarted, and escalate those that cannot
  - says: kill stalled jobs

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
