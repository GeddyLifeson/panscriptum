# OVERWATCH

round 137  ·  last run 2026-08-29 00:53

## Structure

- modules that will not import: **0**
- files that will not parse: **2** of 270,644 inspected (deep scan as of round 133)  — state\gpu_lane\slot.1.json — cannot stat; state\snapshots\AppData\Local\Temp\sweep37probe_a76ncjt1\real.txt — cannot stat
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**9 open** (3 high). Newest first.

- **gpu_lane.py** `_heartbeat` — [HIGH] Does not actively refresh leases; relies on external mechanisms which may not keep leases fresh during long-running calls
  - says: Keep every lease this call holds fresh until the call finishes
- **gpu_lane.py** `_write_claim` — [HIGH] Attempts to replace the file but fails silently if the replacement is denied, potentially leaving the file in an inconsistent state
  - says: Write a claim to a file, ensuring it replaces an existing one if needed
- **feats.py** `_QUANTITY` — [HIGH] The regex captures the exponent group (group 2) and the superscript exponent group (group 3), but the code only reads groups 1 and 3, effectively discarding the exponent group (gro
  - says: The EXPONENT WAS CAPTURED AND THROWN AWAY. `_QUANTITY`'s second group holds the N of an `x 10^N`, and for as long as it existed only groups 1 and 3 were read --
- **gpu_lane.py** `_take_slot` — [MEDIUM] Attempts to claim a slot but may return None even if slots are available due to exceptions during file operations
  - says: Claim one of MAX_SLOTS leases, or return None if they are all live
- **escalation.py** `_read_halt_raw` — [MEDIUM] returns a dict or None, but the docstring says it returns a dict or None, and the code does that. The claim is correct, but the code does not break the promise. However, the docstr
  - says: IT ALWAYS RETURNS None OR A DICT
- **drill.py** `SC.hostless` — [MEDIUM] A function that is being mocked to return a synthetic dictionary of sources
  - says: A function that returns hostless sources
- **drill.py** `SC.LOG` — [MEDIUM] A path that is being set to a temporary directory for testing
  - says: A path to the log file
- **drill.py** `SC.ATTEMPTS` — [MEDIUM] A path that is being set to a temporary directory for testing
  - says: A path to the attempts ledger file
- **drill.py** `SC.scout` — [MEDIUM] A function that is being mocked to return a fixed dictionary structure
  - says: A function that simulates scouting behavior for testing purposes

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
