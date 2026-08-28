# OVERWATCH

round 112  ·  last run 2026-08-28 11:46

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 267,074 inspected  — handoff\run36\sweep_plan.json — malformed JSON: Extra data: line 213 column 1 (char 3102)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**6 open** (3 high). Newest first.

- **catalogue_web.py** `_P.write_record_catalogue` — [HIGH] returns whether the rename LANDED, but the code discards the failure and sets `status = "catalogued"` regardless
  - says: returns whether the rename LANDED
- **catalogue_models.py** `sweep` — [HIGH] sweep() does not actually perform a sweep; it only prepares data and writes it to a JSON file without returning or using the data for any purpose
  - says: sweep(config_path=None, workers=6)
- **canon_backup.py** `silence.replace_retry` — [HIGH] the manifest write is not checked, and the code proceeds as if the manifest was written successfully
  - says: the snapshot landed at %s but its manifest could not be written, so nothing records what it contains and verify() cannot check it. Re-run the snapshot.
- **chain.py** `write_result` — [MEDIUM] writes the result to stdout
  - says: writes the result to a file
- **canon_backup.py** `print("snapshot: %d files, %.1f MB, verified, in %.1fs" % (man["files"], man["bytes"] / 1e6, time.time() - t0))` — [MEDIUM] No verification of the snapshot is performed before printing
  - says: The printed message claims the snapshot is verified
- **canon_backup.py** `snaps[:-keep] if keep > 0 else []` — [MEDIUM] When keep is 0 (or <=0), the loop iterates over an empty list, so no snapshots are deleted
  - says: Delete all but the newest `keep` snapshots; if keep=0, delete all snapshots

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
