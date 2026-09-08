# OVERWATCH

round 443  ·  last run 2026-09-08 17:42

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 300,109 inspected (deep scan as of round 439)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py
- NOT RUNNING: **0** overnight.py
- NOT RUNNING: **0** dashboard.py
- NOT RUNNING: **0** publish.py
- NOT RUNNING: **0** pipeline.py

## What the model found in the code

**6 open** (5 high). Newest first.

- **address_space.py** `FIELDS` — [HIGH] hyperverse and xenoverse ARE fields with computed widths
  - says: hyperverse and xenoverse are NOT fields ... reserving bits for them
- **address_space.py** `_tier_counts` — [HIGH] returns hardcoded values when an exception occurs
  - says: renders the live sentence from the same function the widths come from, so the two cannot disagree again.
- **chain.py** `main` — [HIGH] The function is called but not defined in the provided code slice
  - says: The function is supposed to handle the main logic of the program
- **chain.py** `fit` — [HIGH] Returns an error when there are fewer than 3 edges, but the comment suggests that the edges are kept and the graph is the result even when the fit refuses.
  - says: Bradley-Terry over the recorded outcomes, with Ford's condition reported either way.
- **thread_integrity.py** `main` — [HIGH] returns 1 if failed else 0
  - says: THE VERDICT REACHES THE EXIT CODE, WHICH IS THE ONLY THING WATCHING (order aa075aa80f5c). `main()` had no `return` on any path and was invoked bare, so the process always exited 0 -- and `allsweep` reads the rc and nothing else. A run in which EVERY implied thread was DANGLING was byte-identical, to its only automated consumer, to a run in which none was. The comment two hundred lines up states the premise ("main() is the ONLY reporting surface this module has") and stopped one step short of the consequence. Same defect `allsweep` records as just fixed for rosetta.py: "main() returned 0 whatever the rhos said".
- **anchors.py** `vals` — [MEDIUM] vals is a dictionary that may exclude refused anchors, leading to ungraded anchors not being checked
  - says: the declared ladder must name every anchor, and only anchors

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
