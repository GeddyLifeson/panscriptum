# OVERWATCH

round 325  ·  last run 2026-09-04 00:43

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 293,038 inspected
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py
- NOT RUNNING: **0** read.py

## What the model found in the code

**31 open** (8 high). Newest first.

- **pipeline.py** `landed` — [HIGH] landed is a list that contains JSON landings and a False value when all sources refused to build
  - says: landed is a list of booleans indicating whether each job was successfully landed
- **pipeline.py** `merged` — [HIGH] merged is assigned the value of `disk` before any merge operations
  - says: Folding onto `disk` keeps every disk-authored top-level key
- **pipeline.py** `gate_done` — [HIGH] Marks a phase done unconditionally, ignoring the landed status of artifacts.
  - says: Mark a phase done ONLY if every artifact it wrote actually landed.
- **mutate.py** `absent` — [HIGH] list of missing target directories
  - says: list of missing target files
- **drill.py** `reap_orphans` — [HIGH] always returns an empty list when called with older_than=10 ** 9
  - says: reaps orphans based on age and ownership
- **drill.py** `the_loser_of_a_race_is_refused_mid_backoff` — [HIGH] The function does not properly handle the case where a writer lands during the backoff period. It does not ensure the retrying writer is refused and the file remains untouched if the write happened anyway.
  - says: THE COMPARE AND THE SWAP HAVE TO BE ADJACENT -- driven, not asserted. ... A reason is not a refusal if the write happened anyway.
- **drill.py** `reason_matches_verdict` — [HIGH] The function raises a PermissionError on Windows, but the code does not handle it, leading to an uncaught exception. The function also does not ensure the file remains untouched if the rename is denied.
  - says: A denied rename must not come back describing itself as a landing. ... The file must also be untouched afterwards: a reason is not evidence if the write happened anyway.
- **drill.py** `PL._chain_landed` — [HIGH] PL._chain_landed is used to determine if a write landed, but the code checks if the disk content matches the built document, which is the opposite of what the comment says it should do.
  - says: Phase 4's done-key must be gated on the artifact, not on the writer's say-so.
- **resync_roll.py** `have` — [MEDIUM] count of sources with entry_count > 0
  - says: count of sources catalogued
- **resync_roll.py** `relabelled` — [MEDIUM] THE VERDICT IS NOT OPTIONAL
  - says: THE VERDICT IS NOT OPTIONAL
- **resync_roll.py** `relabelled` — [MEDIUM] THE STATUS RULE IS ABOUT THE COUNT, NOT ABOUT THE COUNT HAVING MOVED
  - says: THE STATUS RULE IS ABOUT THE COUNT, NOT ABOUT THE COUNT HAVING MOVED
- **resync_roll.py** `relabelled` — [MEDIUM] A ROLL ROW WITH NO RECORD FILE IS UNCHECKED, NOT AGREED
  - says: A ROLL ROW WITH NO RECORD FILE IS UNCHECKED, NOT AGREED
- **resync_roll.py** `dupes` — [MEDIUM] stores duplicate source filenames in a list
  - says: index every record file by its declared `source`
- **pipeline.py** `batch_settled` — [MEDIUM] the function is used to determine if a batch is settled (i.e., all entries are judged), and skips processing if true
  - says: was written to kill; that fix stopped batches closing over unjudged entries, but nothing reopened a batch that acquired unjudged entries afterwards.
- **mutate.py** `confirm` — [MEDIUM] the gates to be mutated
  - says: the gates to be confirmed
- **mutate.py** `gates` — [MEDIUM] the gates to be confirmed
  - says: the gates to be mutated
- **mutate.py** `os.walk` — [MEDIUM] copy files recursively
  - says: copy files recursively
- **mutate.py** `os.makedirs` — [MEDIUM] create state directory
  - says: create state directory
- **mutate.py** `missed` — [MEDIUM] list of files that were not copied
  - says: list of files that were not copied
- **ledger_guard.py** `verify_chain` — [MEDIUM] Three distinct faults are reported separately, but the description is incomplete and the explanation about dropped FINAL links is not fully accurate.
  - says: Three distinct faults are reported separately, because they mean different things: UNPARSEABLE a line of the chain file will not read as JSON. The link it held is GONE from every check below, and a dropped FINAL link is invisible to all of them -- so it is a fault in its own right, not a line to skip past. (order 77b098d098d099e6)
- **ledger_guard.py** `verify_chain` — [MEDIUM] An ACKNOWLEDGED problem is one a person has ruled on by name (see `ACKNOWLEDGED` above). It is removed from `problems` -- so it does not fail the chain -- and returned separately so it is still reported.
  - says: An ACKNOWLEDGED problem is one a person has ruled on by name (see `ACKNOWLEDGED` above). It is removed from `problems` -- so it does not fail the chain -- and returned separately so it is still reported.
- **foreman.py** `refresh_coverage` — [MEDIUM] Returns a boolean indicating if the coverage.py script ran successfully, without indicating whether the coverage was actually recomputed or if there were errors.
  - says: Re-measure cited/settled. Stale figures understate the library and mislead every other standard that reads them.
- **drill.py** `silence.write_json` — [MEDIUM] writes to a file that may not be accessible due to the exception handling
  - says: this project's stated one correct way to land a shared file
- **drill.py** `ESC.escalate` — [MEDIUM] the code may not be handling out-of-range rung numbers correctly
  - says: unknown must stop something real without handing a slip of the keyboard the park
- **drill.py** `ESC.escalate` — [MEDIUM] the code may not be handling evidence correctly or typo resolution as described
  - says: resolving a typo to OWNER makes `escalate('Owner ', ...)` a denial of service anyone can trigger by accident; `dict(evidence or {})` flipped to `and` throws the caller's evidence away and leaves the typo unfixable
- **drill.py** `coverage_totals_never_exceed_their_entry_count` — [MEDIUM] the code checks for overflow (summing past entry count) but the docstring says it's only checking one direction
  - says: No source's states may sum PAST its own entry count. One direction, and only one.
- **entity_match.py** `qualifier_compatible` — [MEDIUM] Returns True if both qualifiers are None or their normalized forms are equal, but does not handle cases where one qualifier is None and the other is not.
  - says: Two names may only be compared if their qualifiers agree.
- **dashboard.py** `safety` — [MEDIUM] The function reads data from `state/drill_last.json` and calculates the age of the data, which aligns with the claim. However, the code does not explicitly state that the age is crucial for distinguishing between current and past data states.
  - says: The drill writes `state/drill_last.json` when it runs and this reports what it found and HOW OLD that is -- an age is not decoration here, it is the difference between "57 nets held" and "57 nets held, at some point, possibly before the change you are looking at".
- **address.py** `_index_name_is_placed_like_a_title` — [MEDIUM] The function checks if the index name is placed like a title, but the logic is flawed in how it handles pluralization and partial matches, leading to incorrect categorization of vocabulary vs title evidence.
  - says: The index entry sits inside the target: is it there as the title, or as vocabulary?
- **escalation.py** `clear` — [MEDIUM] clear() returns False for two different reasons, but the code treats them as the same event, leading to incorrect messages about the lift not happening.
  - says: PermissionError is caught alongside ValueError because `clear()` raises it for a non-person caller, and the two refusals are the same event to a reader: the lift did not happen and here is why.
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
