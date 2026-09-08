# OVERWATCH

round 444  ·  last run 2026-09-08 18:05

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 300,109 inspected (deep scan as of round 439)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**6 open** (2 high). Newest first.

- **catalogue_web.py** `write_record_catalogue` — [HIGH] is called with the wrong record_path
  - says: returns whether the rename LANDED
- **binding_health.py** `canary` — [HIGH] Only performs two probes and does not properly handle the third probe's result
  - says: All three probes for one host, plus its identity when the titles failed. -> record.
- **binding_health.py** `_land_cas` — [MEDIUM] discards the failure and returns False, 'the temp copy could not be written'
  - says: deliberately RE-RAISES whatever stopped the temp copy being written
- **binding_health.py** `len(tried)` — [MEDIUM] the code uses len(tried) instead of len(candidates) to show how many were asked
  - says: the reader can see how many were asked
- **binding_health.py** `F.page_looks_real` — [MEDIUM] judge page as real article based on text, not title
  - says: judge page as real article
- **anchors.py** `vals` — [MEDIUM] vals is a dictionary that may exclude refused anchors, leading to ungraded anchors not being checked
  - says: the declared ladder must name every anchor, and only anchors

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
