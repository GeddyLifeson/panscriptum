# OVERWATCH

round 228  ·  last run 2026-08-31 00:15

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 283,040 inspected (deep scan as of round 223)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**25 open** (5 high). Newest first.

- **workorders.py** `_fire` — [HIGH] fires an order only if the first argument is True, but the code uses it with a negated condition
  - says: fire an order with the given parameters
- **mutate.py** `_lock_release` — [HIGH] does not exist in the code slice
  - says: release a lock previously acquired by `_lock_acquire`
- **allsweep.py** `bad` — [HIGH] sum of counts including ungraded reconcile rows
  - says: count of bad subsystems
- **escalation.py** `clear` — [HIGH] clear() returns False for two different reasons
  - says: clear() raises PermissionError for non-person callers
- **drill.py** `a_pure_ladder_is_all_ladder` — [HIGH] The function returns True if the decomposition result has converged, no evidence is False, eta is 1.0, curl fraction is 0.0, and irreducibly_chord is 0.0. However, the claim states that the STAR shape should return eta 0.0, which contradicts the actual code's expectation of eta 1.0.
  - says: A STAR is EXACTLY representable: theta_a = 0.75, the three losers -0.25 each, reproducing every edge. eta must be 1.0 and the curl fraction 0.0. Under Jacobi this was 0.0 -- the answer for a shape with NO ladder in it at all, returned for a shape that is nothing but ladder.
- **identity.py** `identify` — [MEDIUM] Returns `(base, continuity)` only if `desig` is in `continuities`
  - says: Return `(base, continuity)` for a resolved wiki title.
- **hostcheck.py** `purge-cache-remove` — [MEDIUM] the code does not do
  - says: the code says it does
- **hostcheck.py** `purge-record-denied` — [MEDIUM] the code does not do
  - says: the code says it does
- **hostcheck.py** `score` — [MEDIUM] score is called with by=by, but the by parameter is already passed as by[src], making the by=by redundant and possibly incorrect
  - says: score(host, by[src], src, by=by)
- **hostcheck.py** `HOST_MERGE_ATTEMPTS` — [MEDIUM] The symbol HOST_MERGE_ATTEMPTS is used but not defined in this slice of code.
  - says: A constant representing the number of merge attempts.
- **hostcheck.py** `merge` — [MEDIUM] The function is used to merge data into the hosts dictionary, but the variable 'merge' is not defined in this slice of code.
  - says: Merge the provided hosts into the existing hosts file.
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
- **escalation.py** `WO.file_order` — [MEDIUM] the code is passing 'where' and 'evidence' as keyword arguments, but the function may not be designed to handle them, leading to potential misuse or incorrect behavior
  - says: file_order is called with parameters including 'where' and 'evidence'
- **escalation.py** `escalate` — [MEDIUM] Reports at the level specified, but does not actually record at every rung beneath as described. The function only records at the level specified and the log files are not guaranteed to capture all rungs beneath.
  - says: Report something amiss at `level`, recording it at every rung beneath as well.
- **drill.py** `main` — [MEDIUM] raises SystemExit on main()
  - says: entry point for the module
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops
- **foreman.py** `kill_stalled` — [MEDIUM] kill stalled jobs that can be restarted, and escalate those that cannot
  - says: kill stalled jobs

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
