# OVERWATCH

round 135  ·  last run 2026-08-29 00:14

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **2** of 270,644 inspected (deep scan as of round 133)  — state\gpu_lane\slot.1.json — cannot stat; state\snapshots\AppData\Local\Temp\sweep37probe_a76ncjt1\real.txt — cannot stat
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major
- NOT RUNNING: **0** overnight.py

## What the model found in the code

**4 open** (0 high). Newest first.

- **custodes.py** `convene` — [MEDIUM] The function does not convene the full college but instead computes a consensus and interval based on available readings, with some parameters like `eta` and `distance` being unuse
  - says: Convene the full college. The interval is the DISPERSION of their readings.
- **corpus_db.py** `evidence_limit` — [MEDIUM] now inert
  - says: used to slice `files[:evidence_limit]`
- **codewatch.py** `_take_locked` — [MEDIUM] take a lock with enforce=False
  - says: take a lock
- **cleanup.py** `changed` — [MEDIUM] set to True in multiple branches but not all, leading to some changes not being recorded
  - says: tracking whether any changes were made to a record

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
