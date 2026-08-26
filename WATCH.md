# OVERWATCH

round 79  ·  last run 2026-08-26 09:38

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 198,069 inspected
- catalogued sources with no host: **15** Clockwork Angels (Rush), Curious DM Investigations (the Sharkin), Genuine Fantas
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major
- NOT RUNNING: **0** read.py
- NOT RUNNING: **0** feats.py --roll

## What the model found in the code

**4 open** (2 high). Newest first.

- **address_space.py** `assign` — [HIGH] assign is called with a dictionary, but the comment says it should take a source's CHARTED TIER STACK
  - says: assign(desig, tiers.get(src) or {})
- **address_space.py** `galaxy` — [HIGH] hardcoded to 2.0e11
  - says: derived from cosmography.GALAXIES_DEFAULT
- **autostart.py** `uninstall` — [MEDIUM] uninstalls but does not handle the supervisor's state
  - says: remove it
- **autostart.py** `install` — [MEDIUM] installs the launcher but does not handle the supervisor's state
  - says: add the Startup launcher

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
