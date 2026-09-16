# OVERWATCH

round 551  ·  last run 2026-09-15 19:43

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 305,503 inspected (deep scan as of round 547)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**12 open** (5 high). Newest first.

- **retry_synthesis.py** `PL.ask_pool_first` — [HIGH] calls a single model (Ollama only)
  - says: calls the pool's first model
- **escalation.py** `subsystem_stopped` — [HIGH] fails closed when the file is unreadable, but the code expects it to leave the order standing
  - says: re-checks if the subsystem is stopped
- **standards.py** `bool(refs) and inside >= len(refs)` — [HIGH] the condition is checking if inside is greater than or equal to the length of refs, but the comment indicates it should check if inside is greater than or equal to the scoreable count
  - says: the assay reading is valid
- **standards.py** `unans_files` — [HIGH] unans_files is initialized to 0 before the try block, and if any of the three unmeasurable cases occur (raise, unreadable file, missing/renamed data/readfeats), the except block is not triggered, and the zero is cached in _UNANS_CACHE for 120 seconds, resulting in no trace of the error
  - says: THIS ONE LEFT NO TRACE AT ALL (2026-08-28). `unans_files = 0` sat before the try and the only out.append sat after it, so a HIGH-severity evidence standard was emitted MET with an observed `0` in three separate unmeasurable cases
- **standards.py** `resident_context` — [HIGH] The context window served by the runner holding any model that matches the configured model name.
  - says: The context window served by the runner holding THIS project's model.
- **retry_synthesis.py** `PL._stored_cut` — [MEDIUM] cuts evidence to 600 chars and marks the cut
  - says: cuts evidence to 600 chars and marks the cut
- **standards.py** `fab` — [MEDIUM] is set to None and used to determine the standard's status, but the logic is flawed
  - says: represents the fabrication rate
- **standards.py** `resident_context` — [MEDIUM] Now iterates through all rows and returns the first matching model's context length.
  - says: IT USED TO TAKE WHICHEVER ROW /api/ps LISTED FIRST
- **foreman.py** `restart_ollama` — [MEDIUM] The function may not restart the service if the restart stamp is unreadable or if the tray is not running, but it does not clearly handle the case where the daemon is wedged and needs a restart. The function's logic for handling the tray and daemon states is complex and may not fully address the intended behavior of restarting the service when tokens stop flowing.
  - says: Restart the local model service when tokens stop flowing. AUTO by owner ruling (2026-08-24, "FIX IT ALL"): the wedge cannot clear itself -- twice in one day the daemon answered /api/tags while zero generations completed, once with no runner process and once with a runner spinning at 98% completing nothing -- and both times the only cure was a restart a person had to perform. The restart is mechanical and reversible (the tray app respawns the daemon; the resident model reloads on first call), and it is rate-limited: at most one automated restart per 30 minutes, so a deeper fault escalates to the owner instead of being restart-looped into invisibility.
- **drill.py** `ESC.status` — [MEDIUM] returns halted status and record, but the code in the slice may not correctly handle all cases
  - says: returns halted status and record
- **drill.py** `read_frag` — [MEDIUM] the fragment is not safe
  - says: the fragment is safe
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
