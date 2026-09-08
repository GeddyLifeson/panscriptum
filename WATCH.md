# OVERWATCH

round 428  ·  last run 2026-09-07 19:51

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 299,328 inspected (deep scan as of round 427)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**8 open** (0 high). Newest first.

- **prose_gate.py** `floor_ok` — [MEDIUM] Checks if the floor is a number and within (0, 1], but does not validate that the floor is greater than 0.0
  - says: Is this a usable evidence floor? Asked in ONE place, by both layers.
- **handbuilt.py** `score_str` — [MEDIUM] score_str is assigned a value based on the type of 'score', but the comment indicates that 'score' can be a sentinel (string) and that formatting it as a float could raise an error. However, the code does not handle the case where 'score' is a string, and the comment suggests that this is a known issue.
  - says: A SCORE CAN BE A SENTINEL, NOT A NUMBER. Zalama's ruin, continuity, celerity, vector, volition and discernment are all the string "unestimable" (:184-203), and `%5.1f` on a string raises TypeError -- which killed `--full` on the one sheet the module documents as its most instructive, because the JSON write above already landed and nothing downstream of it was checked again.
- **worldseed.py** `build_all` — [MEDIUM] build_all is not properly handling the case where the ONOMASTICON file is empty or malformed, leading to incorrect state in LAST_BUILD and potential misreporting of errors
  - says: build_all is supposed to read and process the ONOMASTICON and CONTINUITY_GROUPS JSON files, handling errors and reporting issues
- **workorders.py** `want` — [MEDIUM] want is checked against LADDER, but if invalid, it still proceeds to print the entire queue instead of refusing
  - says: want not in LADDER causes a refusal message and return 2
- **workorders.py** `shown` — [MEDIUM] shown is set to LADDER (show everything) by default, and only set to [want] if a.handler is valid
  - says: An unknown rung REFUSES rather than falling back to "show everything"
- **workorders.py** `BATTERY_CODES` — [MEDIUM] codes that the battery checks, but the battery does not check all codes
  - says: codes that the battery checks
- **workorders.py** `closed` — [MEDIUM] tracks closed codes, but the code is not closed when it should be
  - says: tracks closed codes
- **workorders.py** `resolve_code` — [MEDIUM] resolves a code to a resolution, but the code is not closed when it should be
  - says: resolves a code to a resolution

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
