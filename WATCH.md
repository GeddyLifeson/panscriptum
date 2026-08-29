# OVERWATCH

round 136  ·  last run 2026-08-29 00:39

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **2** of 270,644 inspected (deep scan as of round 133)  — state\gpu_lane\slot.1.json — cannot stat; state\snapshots\AppData\Local\Temp\sweep37probe_a76ncjt1\real.txt — cannot stat
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major
- NOT RUNNING: **0** overnight.py
- NOT RUNNING: **0** publish.py

## What the model found in the code

**10 open** (3 high). Newest first.

- **feats.py** `_QUANTITY` — [HIGH] The regex captures the exponent group (group 2) and the superscript exponent group (group 3), but the code only reads groups 1 and 3, effectively discarding the exponent group (gro
  - says: The EXPONENT WAS CAPTURED AND THROWN AWAY. `_QUANTITY`'s second group holds the N of an `x 10^N`, and for as long as it existed only groups 1 and 3 were read --
- **drill.py** `POL.resolve` — [HIGH] a resolver that returns only the value makes 'holds null' and 'has no such key' different
  - says: a resolver that returns only the value makes 'holds null' and 'has no such key' identical
- **drill.py** `POL.evaluate` — [HIGH] flagging everything is not the same as flagging nothing
  - says: flagging everything is the same as flagging nothing
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
- **drill.py** `coverage_totals_never_exceed_their_entry_count` — [MEDIUM] Checks that the sum of states does not exceed the entry count (i.e., no overflow).
  - says: No source's states may sum PAST its own entry count. One direction, and only one.
- **dashboard.py** `tick` — [MEDIUM] fetches from /api/state but does not handle errors properly
  - says: fetches state data and updates the dashboard

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
