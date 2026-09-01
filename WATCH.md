# OVERWATCH

round 251  ·  last run 2026-09-01 04:24

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 286,381 inspected (deep scan as of round 247)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**15 open** (5 high). Newest first.

- **corpus_db.py** `code` — [HIGH] code is set to None when the resolver returns 'UNASSIGNED', which is supposed to represent unshelved sources. However, the code is then set to None, which is the same value as when the resolver is unavailable or an exception occurs. This leads to ambiguity in distinguishing between these states.
  - says: RESOLVED, UNASSIGNED, OR NEVER ASKED -- THREE STATES, AND TWO OF THEM USED TO SHARE A SPELLING. `code = None` was initialised, the resolver was called inside a try/except that only `silence.note()`d, and the next line's comment stated the contract the except clause then broke: NULL means unshelved, and only the resolver may say so. On any exception NULL was written anyway. That matters far more than one row, because `address._load_spine_codes()` raises OUTRIGHT if data/CHARTER_SPINE_CODES.json is missing or unparseable, and `import address` still succeeds -- so `_spine_for` is truthy, the guard above catches nothing, and one unreadable data file makes ALL 216 sources report as unshelved. The `unaddressed` canned query and the Datasette page then present a whole-roll curatorial backlog, which is exactly the misreading this module's header spends fifteen lines on and nearly acted on once already. The only trace was a note. Now the failure gets its own value, is counted into `meta`, and is reported by the rebuild -- so the index can say "I could not ask" instead of answering for the resolver. (order 25266fa8c2dc)
- **allsweep.py** `run_verifier` — [HIGH] the code does not call `run_verifier`
  - says: Run one verifier and PUBLISH ITS GRADE, not just its exit code.
- **allsweep.py** `check_import` — [HIGH] the code does not call `check_import`
  - says: Does it import, and does its CLI parse?
- **allsweep.py** `sweep_plan.modules()` — [HIGH] the code does not call `sweep_plan.modules()`
  - says: had (order f42c55355431). Both consumers below join `SRC` with the name plus `.py`
- **drill.py** `a_raised_halt_reads_back_as_halted` — [HIGH] returns True only if the halt is marked as cleared, which contradicts the claim that it reads back as standing
  - says: a halt that was raised reads back as standing
- **dashboard.py** `codewatch.exit_if_stale` — [MEDIUM] Exits when the dashboard code has changed and is held still
  - says: Exits rc=17 on purpose when src/ has changed and held still
- **dashboard.py** `tick` — [MEDIUM] Does not handle errors properly when fetching state
  - says: Fetches and updates the dashboard state periodically
- **chain.py** `side_epoch` — [MEDIUM] returns (epoch, its own sentences' disagreement, whether anything probed) for one side, but the 'epoch' is the minimum of the unique epochs, which may not be the one that the side's sentences actually date to
  - says: -> (epoch, its own sentences' disagreement, whether anything probed) for one side.
- **anchors.py** `vector_score` — [MEDIUM] Returns a value derived from the LADDER_RUNGS constant, which is 17, but the comment says it's derived from the Ladder's own height. The function is named 'vector_score' but the comment says it's derived from the Ladder's own height, which is not the same as the LADDER_RUNGS constant.
  - says: Vector on the 0-10 decimal scale, derived from the Ladder's own height. No new quantity.
- **allsweep.py** `bad` — [MEDIUM] counts some subsystems but excludes reconcile findings and some estate findings
  - says: count the number of bad subsystems
- **allsweep.py** `allsweep.Verifier.__iter__` — [MEDIUM] returns an iterator over (label, argv)
  - says: it would have broken verify_math.py:6824-6825
- **allsweep.py** `allsweep.VERIFIERS` — [MEDIUM] a list of Verifier objects
  - says: A plain three-tuple was the obvious shape
- **drill.py** `the_verdict_travels_on_the_record` — [MEDIUM] returns True if the halt_landed is True, but the comment suggests it's about whether the halt was successful, which may not be the same
  - says: the record says whether the halt actually landed
- **drill.py** `net` — [MEDIUM] net runs a test that is not properly scoped to the function it's testing
  - says: net runs a test
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
