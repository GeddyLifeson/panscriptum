# OVERWATCH

round 231  ·  last run 2026-08-31 01:29

## Structure

- modules that will not import: **UNKNOWN — the import scan itself failed**  — TimeoutExpired: Command '['C:\\Users\\imarl\\miniconda3\\pythonw.exe', 'C:\\Users\\imarl\\panscriptum-libr
- files that will not parse: **0** of 283,526 inspected (deep scan as of round 229)

## What the model found in the code

**14 open** (1 high). Newest first.

- **pipeline.py** `phase_chain` — [HIGH] This function is not implemented and causes the runner to stop at phase 4 because the function is missing.
  - says: Phase 4 -- the Chain of Defeats. See chain.py for the reasoning.
- **pipeline.py** `phases` — [MEDIUM] The 'phases' variable is assigned a list of phases based on 'st.get("phase")' and 'len(PHASES)', but the code does not correctly handle the case where the phase pointer is past the last phase and there are no completion markers, which is the scenario the comment explicitly describes.
  - says: A RUNNER WITH AN EMPTY WORK LIST MUST SAY WHICH KIND OF EMPTY IT IS.
- **pipeline.py** `merged` — [MEDIUM] initialised to `rec` and overwritten by `disk` if read succeeds
  - says: carries the caller's fresh per-entry judgments
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
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops
- **foreman.py** `kill_stalled` — [MEDIUM] kill stalled jobs that can be restarted, and escalate those that cannot
  - says: kill stalled jobs

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
