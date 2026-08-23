# OVERWATCH

round 47  ·  last run 2026-08-23 16:41

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 58,348 inspected
- catalogued sources with no host: **17** Arcanum Worlds (Odyssey of the Dragonlords), Clockwork Angels (Rush), Curious DM
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**6 open** (5 high). Newest first.

- **chain.py** `pos` — [HIGH] outcome number i belongs to sentence number i - 1 due to 1-based indexing in the prompt and 0-based indexing in code
  - says: outcome number i belongs to sentence number i
- **catalogue_web.py** `MAX_PER_SOURCE` — [HIGH] The code raises SystemExit when MAX_PER_SOURCE is not None, but this check is performed after the code has already processed the data without truncation, making the check redundant
  - says: MAX_PER_SOURCE was set to a non-None value, which would cause the code to raise SystemExit
- **catalogue_web.py** `MAX_PER_CATEGORY` — [HIGH] The code attempts to compare len(titles) > MAX_PER_CATEGORY, but MAX_PER_CATEGORY is None, causing a TypeError
  - says: The code checks if the number of titles exceeds MAX_PER_CATEGORY to decide whether to rank by size
- **cascade_bridge.py** `e.stream_chat` — [HIGH] The stream_chat function is called without a timeout parameter, and the caller relies on a separate thread with a hard deadline enforced by a threading.Event and a separate pump fu
  - says: The stream_chat function is called with the correct parameters to ensure the call respects the deadline and does not hang indefinitely.
- **cascade_bridge.py** `dead_forever` — [HIGH] Returns buckets excluded by proof, but also includes buckets with 'no such model', 'needs billing', or 'bad key' in the verdict, which are not explicitly covered in the claim and m
  - says: Returns buckets excluded by proof — and ONLY for reasons that cannot fix themselves.
- **anchors.py** `vector_score` — [MEDIUM] Returns 10.0 for any input >= 17, but the LADDER_RUNGS is 17, so input 17 should return 10.0, which it does. However, the function is called with 17 in The Seat of the Creator, whi
  - says: Vector on the 0-10 decimal scale, derived from the Ladder's own height. No new quantity.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
