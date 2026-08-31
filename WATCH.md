# OVERWATCH

round 218  ·  last run 2026-08-30 19:11

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 282,409 inspected (deep scan as of round 217)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**10 open** (3 high). Newest first.

- **canon_backup.py** `newest` — [HIGH] returns the newest canonical file
  - says: returns the newest snapshot
- **build_terminal.py** `DATA` — [HIGH] contains data
  - says: contains data
- **build_terminal.py** `esc` — [HIGH] escapes HTML characters
  - says: escapes HTML characters
- **allsweep.py** `bad` — [MEDIUM] sum of bad findings from broken, verifiers' failed, lint_bad, and est's bad artifacts
  - says: sum of bad findings from broken, verifiers, lint_bad, and est's bad artifacts
- **allsweep.py** `lint_bad` — [MEDIUM] collects undefined names and pyflakes completion status
  - says: collects undefined names from pyflakes output
- **workorders.py** `resolve` — [MEDIUM] Attempts to close an order but does not properly handle the case where the write could not land, leading to potential confusion between 'no such order' and 'order already closed'.
  - says: Close an order: REMOVE it from the open file, append it to the paper trail.
- **verify_math.py** `qualifier_compatible` — [MEDIUM] returns False for two DC continuities
  - says: two DC continuities are never compatible
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops
- **foreman.py** `kill_stalled` — [MEDIUM] kill stalled jobs that can be restarted, and escalate those that cannot
  - says: kill stalled jobs
- **drill.py** `silence.write_json` — [MEDIUM] writes to a file that can be read by other processes, but the code around it suggests that the file should be written in a way that ensures readers see the complete data
  - says: this project's stated one correct way to land a shared file

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
