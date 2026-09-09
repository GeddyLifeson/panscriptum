# OVERWATCH

round 445  ·  last run 2026-09-08 19:10

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 301,105 inspected
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**3 open** (1 high). Newest first.

- **completeness.py** `land` — [HIGH] Returns a third outcome SKIPPED_ONLY, which is truthy but does not indicate the file holds `rows`
  - says: Returns True if the file now holds `rows`
- **completeness.py** `failed` — [MEDIUM] counts failed probes but is used in a condition that checks for zero failures when sizes is empty
  - says: counts failed probes
- **codewatch.py** `exit_if_stale` — [MEDIUM] Exits the process if its code is out of date, but the function's docstring indicates it should not raise on the budget path, which is not the case here.
  - says: Exits the process if its code is out of date.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
