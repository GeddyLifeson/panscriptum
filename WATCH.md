# OVERWATCH

round 48  ·  last run 2026-08-23 20:02

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 58,348 inspected
- catalogued sources with no host: **17** Arcanum Worlds (Odyssey of the Dragonlords), Clockwork Angels (Rush), Curious DM
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major
- ENTRIES BANDED ABOVE THEIR OWN SOURCE'S CEILING: **2** Star Trek:Trilithium (weapon use) M5>M4, Star Wars:Starkiller Base M5>M4

## What the model found in the code

**6 open** (2 high). Newest first.

- **catalogue_web.py** `record` — [HIGH] record is used but never defined in this file or its imports if the condition 'if not record' is false
  - says: record is defined before being used
- **catalogue_web.py** `MAX_PER_CATEGORY` — [HIGH] None, so the line that uses it raises TypeError
  - says: How deep to read a category before ranking. Must be well above MAX_PER_CATEGORY or ranking has nothing to choose from and the alphabetical bias returns.
- **cascade_bridge.py** `_alive` — [MEDIUM] Does not check if bucket is in _STRIKES or _DEAD before returning False
  - says: Returns False if bucket is in dead_forever() or starts with LOCAL_PREFIX
- **cascade_bridge.py** `dead_forever` — [MEDIUM] Excludes buckets with verdicts containing 'no such model', 'needs billing', or 'bad key', but does not check if these verdicts are actually permanent
  - says: Buckets excluded by proof — and ONLY for reasons that cannot fix themselves.
- **cascade_bridge.py** `_interval` — [MEDIUM] Returns 0.0 if rpm is not found or is <= 0, but does not handle the case where rpm is None
  - says: Minimum seconds between entries to this bucket, from its own declared rate.
- **cascade_bridge.py** `_CFG` — [MEDIUM] This variable is defined but never used in the provided code slice.
  - says: This variable is used to store configuration settings for the Engine.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
