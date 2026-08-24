# OVERWATCH

round 49  ·  last run 2026-08-23 21:31

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 58,979 inspected
- catalogued sources with no host: **20** Clockwork Angels (Rush), Curious DM Investigations (the Sharkin), Dr. Firestorm'
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**7 open** (0 high). Newest first.

- **cascade_bridge.py** `_clear` — [MEDIUM] Does not check if _STRIKES or _DEAD is None before trying to access it
  - says: Clear a bucket's strikes and dead time
- **cascade_bridge.py** `_bury` — [MEDIUM] Does not check if _DEAD is None before trying to access it
  - says: Bury a bucket for a certain amount of time
- **cascade_bridge.py** `_alive` — [MEDIUM] Does not check if _DEAD is None before trying to access it
  - says: Check if a bucket is alive
- **cascade_bridge.py** `dead_forever` — [MEDIUM] Does not check if rows is None before trying to iterate over it
  - says: Buckets excluded by proof — and ONLY for reasons that cannot fix themselves.
- **cascade_bridge.py** `_pace` — [MEDIUM] Does not check if gap is None before trying to compare it to 0.0
  - says: Block until this bucket's turn. One waiter at a time per bucket, so the queue is orderly.
- **cascade_bridge.py** `_interval` — [MEDIUM] Returns 0.0 if rpm is not found or is <= 0, but does not check if rpm is None before trying to divide by it
  - says: Minimum seconds between entries to this bucket, from its own declared rate.
- **autostart.py** `ap.add_argument('--read-hours', type=float, default=10)` — [MEDIUM] read-hours argument is used to start the supervisor
  - says: read-hours argument is used to determine the hours to read

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
