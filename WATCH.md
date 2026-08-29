# OVERWATCH

round 134  ·  last run 2026-08-28 23:52

## Structure

- modules that will not import: **0**
- files that will not parse: **2** of 270,644 inspected (deep scan as of round 133)  — state\gpu_lane\slot.1.json — cannot stat; state\snapshots\AppData\Local\Temp\sweep37probe_a76ncjt1\real.txt — cannot stat
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**4 open** (0 high). Newest first.

- **compress_store.py** `store` — [MEDIUM] returns a dictionary with 'raw_bytes' as the length of the raw bytes and 'compressed_bytes' as the length of the compressed blob, not the actual raw and compressed byte data
  - says: Compress `text`, write it to compressed_dir keyed by content hash, and return
- **codewatch.py** `exit_if_stale` — [MEDIUM] Exits the process if its code is out of date, but does not raise on the budget path.
  - says: Exits the process if its code is out of date.
- **cleanup.py** `changed` — [MEDIUM] set to True in multiple branches but not all, leading to some changes not being recorded
  - says: tracking whether any changes were made to a record
- **cleanup.py** `clean_ceiling` — [MEDIUM] Attempts to find a match in entry names but fails to handle cases where the ceiling is a name that is not in the entry names list, leaving it unchanged and reporting it as a proble
  - says: Reduce a prose ceiling to the name it is about.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
