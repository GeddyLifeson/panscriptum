# OVERWATCH

round 222  ·  last run 2026-08-30 20:55

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 282,409 inspected (deep scan as of round 217)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**13 open** (0 high). Newest first.

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
- **dashboard.py** `out` — [MEDIUM] out is a dictionary that is being populated with various keys, but the initial value is not used as it is overwritten in subsequent assignments
  - says: out = {"halted": None, "prose_gate": None, "drill": None, "escalation_recent": None}
- **dashboard.py** `throughput` — [MEDIUM] Calculates total calls and per-hour rate, but does not accurately represent the actual calls made in the recent past due to potential data aggregation issues.
  - says: Calls actually made in the recent past, per bucket. The quota panel says what is LEFT; this says what is being SPENT, and the two together are the whole picture.
- **codewatch.py** `main` — [MEDIUM] prints the current src/ fingerprint and information about restarts
  - says: print the current src/ fingerprint
- **codewatch.py** `exit_if_stale` — [MEDIUM] reads the budget and records the restart in separate operations with a gap in the middle
  - says: CHECK AND TAKE TOGETHER. Reading the budget here and recording the restart further down was two operations with a gap in the middle that two twins could both walk through.
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
