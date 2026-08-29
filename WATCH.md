# OVERWATCH

round 161  ·  last run 2026-08-29 14:28

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 273,738 inspected (deep scan as of round 157)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**4 open** (1 high). Newest first.

- **sevenfold.py** `seams` — [HIGH] Slices the block into evenly sized pieces when no affinity data is provided, which does not correspond to the weakest seams
  - says: Where the affinity ordering is weakest -- the natural places to cut.
- **runguard.py** `release` — [MEDIUM] Close our own record. Same ownership rule: a run may only ever close its own.
  - says: Close our own record. Same ownership rule: a run may only ever close its own.
- **runguard.py** `beat` — [MEDIUM] Refresh the heartbeat -- but ONLY on a record that is ours.
  - says: Refresh the heartbeat -- but ONLY on a record that is ours.
- **runguard.py** `claim` — [MEDIUM] Take the guard for `agent`, or refuse.
  - says: Take the guard for `agent`, or refuse.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
