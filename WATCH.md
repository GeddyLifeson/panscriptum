# OVERWATCH

round 390  ·  last run 2026-09-06 06:44

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 296,661 inspected (deep scan as of round 385)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**36 open** (7 high). Newest first.

- **pipeline.py** `phases` — [HIGH] the code proceeds to process phases even when the list is empty
  - says: A RUNNER WITH AN EMPTY WORK LIST MUST SAY WHICH KIND OF EMPTY IT IS.
- **pipeline.py** `landed` — [HIGH] The code adds a third arm to handle the case where all sources have no entries, but this contradicts a deliberate decision that this case should not keep phase 8 open.
  - says: A THIRD ARM WAS ADDED HERE ON 2026-09-01 AND REVERTED THE SAME SHIFT. Recorded so the next reader does not re-derive it a third time.
- **overnight.py** `run` — [HIGH] does not order anything and cannot run after the reader
  - says: Runs after the reader so it sees the evidence the reader just produced
- **estate.py** `note` — [HIGH] appends a finding to, but the code in the comment says it should append nothing
  - says: appends a finding to the report
- **estate.py** `note` — [HIGH] appends a finding to the report
  - says: appends a finding to the report
- **escalation.py** `landed, why` — [HIGH] A variable that is used but never defined in this file or its imports
  - says: One compare-and-swapped attempt at lifting the halt. -> (landed, why).
- **drill.py** `R.hodge_decompose` — [HIGH] returns a result that does not match the expected values for a pure ladder
  - says: A pure ladder measures as 100% ladder
- **profile.py** `decode` — [MEDIUM] raises ValueError on invalid profiles but does not validate the decoded components against the B32 alphabet
  - says: decodes a world profile string into its components
- **policy.py** `main` — [MEDIUM] The function returns 0, 1, or 2 based on the presence of failures, unreadable records, and whether the report was landed. The comment suggests that the function should print all failures and vacuous passes, but the code only returns exit codes without printing all the details.
  - says: Every failure and every vacuous pass is named. These printed 12 and stopped, which on a 216-record corpus meant the 13th failure onward existed only in state/policy_report.json -- and the line above it announced a count that looked like the whole list.
- **policy.py** `ev_read` — [MEDIUM] initialized to 0 and then set to the length of feats, which is the number of evidence files that were processed
  - says: counts the number of evidence files that were read
- **policy.py** `ev_total` — [MEDIUM] initialized to 0 and then set to the length of all_feats, which is the total number of evidence files
  - says: counts the total number of evidence files
- **policy.py** `nonempty` — [MEDIUM] Checks if the value has a __len__ attribute and its length is greater than zero, which would include numbers if they are containers (like a list or dict) but not numbers in a name field.
  - says: Spelled as what it means: a non-empty container or string.
- **pipeline.py** `batch_settled` — [MEDIUM] skips when the batch is already in done_keys
  - says: skip when the span as it stands right now is fully judged
- **overwatch.py** `round_once` — [MEDIUM] The function resets the _LOCAL_BUSY counter to 0 at the beginning of each round, but the comment suggests that the budget was previously per process and not per round, implying that the function may not correctly handle the budgeting logic as intended.
  - says: THE BUDGET IS PER ROUND, AND UNTIL NOW IT WAS PER PROCESS. CLOUD_BUDGET's own comment calls it "calls the watcher may take from the shared pool in one round", and the yield it guards is explicitly meant to last "for as long as the busy period lasted" -- but nothing ever reset the counter. In `--loop` mode (the standing sweep, which runs for days) one busy stretch pushed the lifetime total past 20 and every later GPU-busy call returned None forever after, with no cloud fallback. The watcher quietly stopped watching, which this file's own comment names as the thing it exists to prevent. Reset where the round begins.
- **overnight.py** `drill_rc` — [MEDIUM] assigned the value of safety_drill() which is not checked against any condition
  - says: supposed to stop us still able to? Cheap (no model calls, no network) and it is the only check that would notice a safety having been REMOVED rather than having failed.
- **overnight.py** `run` — [MEDIUM] Runs a stage to completion, but does not properly handle the case where the process is already running, leading to potential duplicate runs.
  - says: Run one stage to completion, refusing to start a duplicate.
- **onomast.py** `load_onomasticon` — [MEDIUM] returns {} on FileNotFoundError and catches all exceptions, raising OnomasticonUnreadable only if the file exists and cannot be parsed
  - says: RAISES `OnomasticonUnreadable` if the file is on disk and will not parse, and is allowed to propagate on purpose
- **mutate.py** `dead` — [MEDIUM] dead is assigned the result of unusable_gates(base), which is a list of gates that could not complete on clean code
  - says: dead = unusable_gates(base)
- **mutate.py** `no_verdict` — [MEDIUM] no_verdict is used to represent a verdict, but the comment suggests it should be a candidate for being a survivor
  - says: A SURVIVOR OF THE FAST GATES IS ONLY A CANDIDATE
- **mutate.py** `no_verdict` — [MEDIUM] no_verdict is assigned the value of sig, which is used to indicate a verdict, but the comment suggests it should represent the absence of a verdict
  - says: THE GATE DID NOT REACH A VERDICT. Not a kill: see `could_not_judge`.
- **mutate.py** `missed` — [MEDIUM] list of files that were not copied due to sandbox issues
  - says: list of files that were not copied due to sandbox issues
- **mutate.py** `absent` — [MEDIUM] list of targets that are not files in the sandbox
  - says: list of targets missing from the sandbox
- **mutate.py** `suppressed_on_record` — [MEDIUM] returns entries with 'ruled_equivalent' key, which may not be suppressed
  - says: every survivor a standing ruling kept out of the queue
- **mutate.py** `survivors_on_record` — [MEDIUM] filters out baseline_event and ruled_equivalent entries, but includes entries with 'line' key
  - says: FILTERED TO ACTUAL SURVIVORS
- **liveness.py** `scoped` — [MEDIUM] the code says it does instead
  - says: the code says it does instead
- **hostcheck.py** `sweep` — [MEDIUM] searches for replacements for hosts that failed to hold their fiction but uses a flawed logic for selecting replacements
  - says: searches for replacements for hosts that failed to hold their fiction
- **hostcheck.py** `candidates` — [MEDIUM] Returns the same flat list as `candidates_split`
  - says: Unchanged for every caller: the same flat `grounded + spec` list it has always returned.
- **health.py** `reopen_stranded` — [MEDIUM] return value is used to determine exit code, but the code does not handle the case where it returns None
  - says: THE VERDICT IS THE EXIT CODE (sweep42-batch10). This discarded `reopen_stranded()`'s return value and returned 0 unconditionally, so a repair that could not read or write PIPELINE_STATE.json reported success to whatever ran it -- the check-that-cannot-fail shape, on a repair.
- **health.py** `silence.write_json` — [MEDIUM] is called and the return value is checked, but the code does not handle the case where it returns False
  - says: RETURNS False rather than raising when the atomic replace is denied
- **feats.py** `_QUANTITY` — [MEDIUM] does not capture the exponent part of a quantity
  - says: captures the exponent part of a quantity
- **escalation.py** `escalate` — [MEDIUM] escalate is not called here and the code does not handle its exceptions
  - says: escalate(...)
- **escalation.py** `clear` — [MEDIUM] clear() is not called here and the code does not handle its exceptions
  - says: clear() raises it for a non-person caller
- **escalation.py** `why` — [MEDIUM] being initialized to 'not attempted' and then overwritten in the loop, but the loop may not have run at all
  - says: tracking the reason for failure
- **escalation.py** `landed` — [MEDIUM] being set to False after the loop, but the loop may not have run at all
  - says: tracking whether the halt was successfully landed
- **entity_match.py** `qualifier_compatible` — [MEDIUM] Returns True if both qualifiers are None or their normalized forms are equal, but does not handle cases where one qualifier is None and the other is not.
  - says: Two names may only be compared if their qualifiers agree.
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
