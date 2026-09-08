# OVERWATCH

round 432  ·  last run 2026-09-07 22:23

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 299,328 inspected (deep scan as of round 427)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**3 open** (1 high). Newest first.

- **standards.py** `work_orders` — [HIGH] returns 1 if bad else 0, but the comment says it should return 0 no matter what
  - says: THE SAME EXIT CONVENTION ON EVERY PATH (order 92fdcb9a8310). Both of these branches end `return 0` no matter what they had just printed, while the default path below ends `return 1 if work_orders(state) else 0` -- the convention this file's own module docstring exists to establish.
- **standards.py** `probe` — [MEDIUM] sum of values for keys containing specific strings
  - says: counted every swallowed exception
- **gpu_lane.py** `ignore_pid` — [MEDIUM] Is any foreground claim outstanding, ignoring the specified PID
  - says: Is any LIVE foreground claim outstanding?

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
