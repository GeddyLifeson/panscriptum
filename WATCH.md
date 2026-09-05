# OVERWATCH

round 355  ·  last run 2026-09-05 00:44

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 295,231 inspected
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**20 open** (8 high). Newest first.

- **magnitude.py** `verify` — [HIGH] deciding on the SENTENCE alone
  - says: the entity must be the DOER
- **local_agent.py** `t_propose_patch` — [HIGH] appends to the `unreverted` list but does not raise alarms or trigger safety escalations
  - says: raises the durable alarms for this case -- a SAFETY escalation and a `silence.note`
- **escalation.py** `status` — [HIGH] returns a tuple (halted, _rec) which is then used to determine the output, but the code does not actually re-read the file or determine the world as described in the comment
  - says: re-read the file and name which world this is; rc follows, so a script can tell a refused lift from a no-op as well.
- **drill.py** `ESC.escalate` — [HIGH] the rung that actually stops the plant
  - says: every escalation becomes a work order, addressed and graded
- **drill.py** `paid_access_stays_switched_off` — [HIGH] returns True when the config file is absent or unreadable, which may allow paid access even if the key is not present
  - says: allow_paid is owner-held. Nothing automatic may switch it on.
- **drill.py** `coverage_totals_never_exceed_their_entry_count` — [HIGH] The code sums four of the five columns mentioned in the docstring and excludes 'not_attempted', which means it does not check for the exact sum that the docstring claims to verify.
  - says: No source's states may sum PAST its own entry count. One direction, and only one.
- **drill.py** `fired` — [HIGH] returns the set of faults that should be closed
  - says: returns the set of faults that should be filed
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [HIGH] The code returns 1 if the result is None, else 0, which is the opposite of what the comment says it does. The comment states that the return value should be used to determine the exit code, but the code inverts this logic.
  - says: THE VERDICT IS THE EXIT CODE (sweep42-batch10). This discarded `reopen_stranded()`'s return value and returned 0 unconditionally, so a repair that could not read or write PIPELINE_STATE.json reported success to whatever ran it -- the check-that-cannot-fail shape, on a repair. It is invoked from scripts, which have nothing else to read.
- **mutate.py** `os.makedirs` — [MEDIUM] create the state directory if it doesn't exist
  - says: create the state directory
- **magnitude.py** `band_hits` — [MEDIUM] counts BAND MATCHES ONLY (got_band == band)
  - says: anchor band reproduced on {band_hits}/{len(BENCHMARKS)} published assays
- **local_agent.py** `modname` — [MEDIUM] Derives `modname` through a CASE-SENSITIVE `.endswith(".py")` but then folds on both sides when checking against the denylist
  - says: Folds the denylist while deriving `modname` through a CASE-SENSITIVE `.endswith(".py")`
- **generate.py** `failures.pop` — [MEDIUM] removes a failure from the failures list
  - says: A DEAD REFUSAL MUST NOT READ LIKE A LIVE ONE
- **escalation.py** `landed` — [MEDIUM] landed is overwritten with False in the except block, which may not reflect the actual state of the file
  - says: landed is used to determine if the halt was lifted
- **escalation.py** `landed` — [MEDIUM] landed is set to False in the except block, but the code returns False in the case where the file wasn't cleared
  - says: landed is set to False if the attempt failed
- **binding_health.py** `F.page_looks_real` — [MEDIUM] check if text is an article
  - says: check if text is an article
- **binding_health.py** `F.fetch` — [MEDIUM] import feats and call fetch
  - says: fetch a host and title
- **entity_match.py** `qualifier_compatible` — [MEDIUM] Returns True if both qualifiers are None or their normalized forms are equal, but does not handle cases where one qualifier is None and the other is not.
  - says: Two names may only be compared if their qualifiers agree.
- **dashboard.py** `safety` — [MEDIUM] The function reads data from `state/drill_last.json` and calculates the age of the data, which aligns with the claim. However, the code does not explicitly state that the age is crucial for distinguishing between current and past data states.
  - says: The drill writes `state/drill_last.json` when it runs and this reports what it found and HOW OLD that is -- an age is not decoration here, it is the difference between "57 nets held" and "57 nets held, at some point, possibly before the change you are looking at".
- **address.py** `_index_name_is_placed_like_a_title` — [MEDIUM] The function checks if the index name is placed like a title, but the logic is flawed in how it handles pluralization and partial matches, leading to incorrect categorization of vocabulary vs title evidence.
  - says: The index entry sits inside the target: is it there as the title, or as vocabulary?
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
