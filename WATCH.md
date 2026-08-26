# OVERWATCH

round 80  ·  last run 2026-08-26 10:00

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 198,069 inspected
- catalogued sources with no host: **15** Clockwork Angels (Rush), Curious DM Investigations (the Sharkin), Genuine Fantas
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**2 open** (2 high). Newest first.

- **cascade_bridge.py** `got` — [HIGH] the code uses `if got` to check for truthiness, but the comment says it should guard against the reply shape that would raise an AttributeError
  - says: if got is TRUTHINESS, not type. `_extract_json` can return a list, and a non-empty list is truthy
- **binding_health.py** `quarantine` — [HIGH] Attempts to record a host as failing but may not persist the record to disk if the write fails, leading to potential silent skips and incomplete records.
  - says: Record a host as failing, WITH ITS REASON. Never a silent skip, never a deletion.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
