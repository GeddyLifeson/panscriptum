# OVERWATCH

round 554  ·  last run 2026-09-15 21:05

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 305,592 inspected (deep scan as of round 553)  — state\gpu_lane\slot.0.json — cannot stat: GONE (absent on a second look, one rename later)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**7 open** (4 high). Newest first.

- **estate.py** `external` — [HIGH] The function does not actually check external dependencies but instead collects various system state information and logs findings.
  - says: The dependencies that live outside this project and can fail without it changing.
- **estate.py** `artifacts` — [HIGH] The code does not discover roots automatically; it uses a hand-kept list of directories and files, and the docstring's claim is contradicted by the code's behavior.
  - says: Every file in the project, opened and checked. No sampling anywhere.
- **thread_integrity.py** `dist` — [HIGH] is never assigned a value beyond the initial None
  - says: is assigned the distance between entities
- **gpu_lane.py** `foreground` — [HIGH] Modifies a claim file with a refcount, but does not actually mark the process as foreground in any way that affects background jobs
  - says: Mark this process as doing work that background jobs should get out of the way for.
- **foreman.py** `restart_ollama` — [MEDIUM] The function may not restart the service if the restart stamp is unreadable or if the tray is not running, but it does not clearly handle the case where the daemon is wedged and needs a restart. The function's logic for handling the tray and daemon states is complex and may not fully address the intended behavior of restarting the service when tokens stop flowing.
  - says: Restart the local model service when tokens stop flowing. AUTO by owner ruling (2026-08-24, "FIX IT ALL"): the wedge cannot clear itself -- twice in one day the daemon answered /api/tags while zero generations completed, once with no runner process and once with a runner spinning at 98% completing nothing -- and both times the only cure was a restart a person had to perform. The restart is mechanical and reversible (the tray app respawns the daemon; the resident model reloads on first call), and it is rate-limited: at most one automated restart per 30 minutes, so a deeper fault escalates to the owner instead of being restart-looped into invisibility.
- **drill.py** `ESC.status` — [MEDIUM] returns halted status and record, but the code in the slice may not correctly handle all cases
  - says: returns halted status and record
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
