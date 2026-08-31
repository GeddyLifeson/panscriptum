# OVERWATCH

round 223  ·  last run 2026-08-30 21:29

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 283,040 inspected
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**11 open** (0 high). Newest first.

- **drill.py** `silence.write_json` — [MEDIUM] writes to a file that can be read by other processes but does not handle time fields or staleness correctly
  - says: this project's stated one correct way to land a shared file
- **drill.py** `catalog_matches_disk` — [MEDIUM] Only checks that the catalog claims exist on disk, but not the other way around
  - says: Every chapter the catalog claims exists on disk, AND VICE VERSA — both directions.
- **estate.py** `note` — [MEDIUM] appends a dictionary with 'finding', 'detail', and 'bad' keys
  - says: appends a finding to the out list
- **escalation.py** `clear` — [MEDIUM] The function `clear()` is called with `by=a.by` but the code does not check if `clear()` actually returned a value or handled its return value correctly, leading to potential incorrect handling of the refusal cases.
  - says: PermissionError is caught alongside ValueError because `clear()` raises it for a non-person caller, and the two refusals are the same event to a reader: the lift did not happen and here is why.
- **escalation.py** `clear` — [MEDIUM] Lifts the halt if called from the CLI, but does not verify that the caller is a person. The function allows programmatic calls if the caller is the CLI, which may not be a person.
  - says: Lift the halt. A PERSON ONLY, and refused at run time if the caller is not one.
- **drill.py** `LA.MAX_FILES_PER_RUN` — [MEDIUM] set to zero, but then immediately overwritten by the value from the previous run
  - says: taken to zero
- **drill.py** `LA.MAX_PATCHES_PER_RUN` — [MEDIUM] set to zero, but then immediately overwritten by the value from the previous run
  - says: taken to zero
- **allsweep.py** `bad` — [MEDIUM] sum of bad findings from broken, verifiers' failed, lint_bad, and est's bad artifacts
  - says: sum of bad findings from broken, verifiers, lint_bad, and est's bad artifacts
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops
- **foreman.py** `kill_stalled` — [MEDIUM] kill stalled jobs that can be restarted, and escalate those that cannot
  - says: kill stalled jobs
- **drill.py** `silence.write_json` — [MEDIUM] writes to a file that can be read by other processes, but the code around it suggests that the file should be written in a way that ensures readers see the complete data
  - says: this project's stated one correct way to land a shared file

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
