# OVERWATCH

round 111  ·  last run 2026-08-28 11:24

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 267,074 inspected  — handoff\run36\sweep_plan.json — malformed JSON: Extra data: line 213 column 1 (char 3102)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major
- NOT RUNNING: **0** read.py
- NOT RUNNING: **0** feats.py --roll

## What the model found in the code

**5 open** (2 high). Newest first.

- **canon_backup.py** `silence.replace_retry` — [HIGH] the manifest write is not checked, and the code proceeds as if the manifest was written successfully
  - says: the snapshot landed at %s but its manifest could not be written, so nothing records what it contains and verify() cannot check it. Re-run the snapshot.
- **binding_health.py** `run()` — [HIGH] known_present_titles returns a list of titles, so `title` becomes a list, but later is passed to canary() as if it were a single title string
  - says: title = known_present_titles(h, hosts_map)  # expects a single title string
- **canon_backup.py** `print("snapshot: %d files, %.1f MB, verified, in %.1fs" % (man["files"], man["bytes"] / 1e6, time.time() - t0))` — [MEDIUM] No verification of the snapshot is performed before printing
  - says: The printed message claims the snapshot is verified
- **canon_backup.py** `snaps[:-keep] if keep > 0 else []` — [MEDIUM] When keep is 0 (or <=0), the loop iterates over an empty list, so no snapshots are deleted
  - says: Delete all but the newest `keep` snapshots; if keep=0, delete all snapshots
- **profile.py** `encode` — [MEDIUM] the code says it does
  - says: the code says it does

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
