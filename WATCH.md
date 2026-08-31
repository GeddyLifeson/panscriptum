# OVERWATCH

round 220  ·  last run 2026-08-30 20:08

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 282,409 inspected (deep scan as of round 217)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**13 open** (3 high). Newest first.

- **corpus_db.py** `code` — [HIGH] code is assigned None, and if the resolver returns 'UNASSIGNED', it is set to None again. This means that 'UNASSIGNED' is treated as NULL, which is supposed to represent unshelved sources. However, the resolver is supposed to be the only one that can assign NULL, and this code is effectively allowing the resolver to assign NULL in some cases, which is a defect of fact.
  - says: RESOLVED, UNASSIGNED, OR NEVER ASKED -- THREE STATES, AND TWO OF THEM USED TO SHARE A SPELLING. `code = None` was initialised, the resolver was called inside a try/except that only `silence.note()`d, and the next line's comment stated the contract the except clause then broke: NULL means unshelved, and only the resolver may say so. On any exception NULL was written anyway. That matters far more than one row, because `address._load_spine_codes()` raises OUTRIGHT if data/CHARTER_SPINE_CODES.json is missing or unparseable, and `import address` still succeeds -- so `_spine_for` is truthy, the guard above catches nothing, and one unreadable data file makes ALL 216 sources report as unshelved. The `unaddressed` canned query and the Datasette page then present a whole-roll curatorial backlog, which is exactly the misreading this module's header spends fifteen lines on and nearly acted on once already. The only trace was a note. Now the failure gets its own value, is counted into `meta`, and is reported by the rebuild -- so the index can say "I could not ask" instead of answering for the resolver. (order 25266fa8c2dc)
- **completeness.py** `probe_failures` — [HIGH] IS PASSED HERE
  - says: IS NOT PASSED HERE, AND THAT IS THE FIX
- **canon_backup.py** `newest` — [HIGH] returns the newest canonical file
  - says: returns the newest snapshot
- **coverage.py** `measure` — [MEDIUM] measure() does not guard divisions in the report() function
  - says: measure() guards every division with max(n, 1)
- **compress_store.py** `load` — [MEDIUM] Reads a stored blob back, decompresses it, and checks the hash against the filename, but does not verify the decompressed content against the original text's hash. The verification is done by comparing the computed hash of the decompressed text with the filename's hash, which is correct.
  - says: Read a stored blob back, VERIFYING it against the address it is filed under.
- **codewatch.py** `main` — [MEDIUM] prints the current src/ fingerprint and information about restarts
  - says: print the current src/ fingerprint
- **codewatch.py** `exit_if_stale` — [MEDIUM] reads the budget and records the restart in separate operations with a gap in the middle
  - says: CHECK AND TAKE TOGETHER. Reading the budget here and recording the restart further down was two operations with a gap in the middle that two twins could both walk through.
- **cleanup.py** `clean_ceiling` — [MEDIUM] Returns the ceiling as-is if no match is found, but the docstring says it should leave it alone and report it as unresolved
  - says: Reduce a prose ceiling to the name it is about.
- **allsweep.py** `bad` — [MEDIUM] sum of bad findings from broken, verifiers' failed, lint_bad, and est's bad artifacts
  - says: sum of bad findings from broken, verifiers, lint_bad, and est's bad artifacts
- **workorders.py** `resolve` — [MEDIUM] Attempts to close an order but does not properly handle the case where the write could not land, leading to potential confusion between 'no such order' and 'order already closed'.
  - says: Close an order: REMOVE it from the open file, append it to the paper trail.
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops
- **foreman.py** `kill_stalled` — [MEDIUM] kill stalled jobs that can be restarted, and escalate those that cannot
  - says: kill stalled jobs
- **drill.py** `silence.write_json` — [MEDIUM] writes to a file that can be read by other processes, but the code around it suggests that the file should be written in a way that ensures readers see the complete data
  - says: this project's stated one correct way to land a shared file

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
