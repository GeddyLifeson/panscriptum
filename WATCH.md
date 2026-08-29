# OVERWATCH

round 167  ·  last run 2026-08-29 16:51

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **0** of 274,390 inspected (deep scan as of round 163)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**3 open** (1 high). Newest first.

- **dashboard.py** `movement` — [HIGH] What has NOT CHANGED, not what the level is.
  - says: What has CHANGED, not what the level is.
- **custodes.py** `convene` — [MEDIUM] The function does not actually convene the full college; it returns a dictionary with computed statistics and flags, but the actual 'convening' logic is not executed.
  - says: Convene the full college. The interval is the DISPERSION of their readings.
- **compress_store.py** `store` — [MEDIUM] writes to a temporary file and attempts to replace it, but the returned dict does not include the actual file path or content
  - says: Compress `text`, write it to compressed_dir keyed by content hash, and return

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
