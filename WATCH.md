# OVERWATCH

round 295  ·  last run 2026-09-03 00:19

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 290,960 inspected
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**23 open** (11 high). Newest first.

- **drill.py** `ESC.escalate` — [HIGH] rejects every VALID rung and accepts every invalid one
  - says: the bounds test `JANITOR <= level <= OWNER`
- **drill.py** `ESC.brief` — [HIGH] hands every rung an empty record
  - says: a field that is None must not
- **drill.py** `ESC._safe_name` — [HIGH] a truncating name silently merges two areas of the park
  - says: two long source names sharing a 60-character prefix do NOT share a log
- **drill.py** `ESC._safe_name` — [HIGH] renames every existing log on disk and stops disambiguating the names that actually collide
  - says: a short name is not given a digest it does not need
- **drill.py** `ESC._safe_name` — [HIGH] collapses into one file named for none of them
  - says: INJECTIVITY: every source is its own area of the park
- **drill.py** `drill_binding_identity` — [HIGH] The function is incomplete and does not fully implement the logic described in its docstring.
  - says: Can an unfixable fault be filed, for ever, at a handler that cannot fix it?
- **drill.py** `drill_stale_writer` — [HIGH] The function does not actually perform the rename operation, so the file is never modified and the test for the file being untouched is moot.
  - says: The file must also be untouched afterwards: a reason is not evidence if the write happened anyway.
- **drill.py** `drill_stale_writer` — [HIGH] The function tests for a denied rename but the code does not actually perform the rename operation, leaving the file untouched and not testing the denial scenario.
  - says: A denied rename must not come back describing itself as a landing.
- **drill.py** `LG.seal()` — [HIGH] flattens a nested name and _read_snapshot() did not
  - says: gates `publish.push()` on
- **drill.py** `denied` — [HIGH] Confuses 'no such file' (file absence) with gate refusal, leading to false positives
  - says: The code distinguishes between gate refusals and ordinary failures
- **drill.py** `denied` — [HIGH] Returns True for 'no such file' errors, which are not gate refusals but file absence
  - says: Was the path refused BY A GATE, as opposed to failing for an unrelated reason?
- **local_agent.py** `out` — [MEDIUM] the code returns a dictionary that may not have 'ALARM' key if the 'unreverted' condition is not met
  - says: the code says it returns a dictionary with 'ok', 'error', 'patches', 'tool_calls', and 'ALARM' keys
- **local_agent.py** `run` — [MEDIUM] The function does check the halt condition via `assert_clear` but does not handle the case where the model's answer is empty and no patches were attempted, which is a failure case that should set `ok=False`.
  - says: THE HALT IS CHECKED HERE, AND UNTIL RUN #35 IT WAS NOT CHECKED ANYWHERE ON THIS LANE.
- **local_agent.py** `apply` — [MEDIUM] apply is used in a condition that checks if the patch is not applied, but the code proceeds to apply the patch regardless
  - says: apply is a flag that determines whether the patch is applied
- **drill.py** `GL._take_slot` — [MEDIUM] return None or False
  - says: arbitrate a slot
- **drill.py** `GL.lane` — [MEDIUM] create a context manager that does nothing
  - says: arbitrate a lane
- **drill.py** `CW._budget_left` — [MEDIUM] the ledger path is swapped to a scratch file for the same litter discipline
  - says: the ledger path is swapped to a scratch file
- **drill.py** `drill_no_top_ups` — [MEDIUM] The function defines and runs tests related to ruling on provider behaviors, but the actual implementation does not directly enforce the ruling. The ruling is more about the logic in the tests rather than the function itself.
  - says: OWNER RULING 2026-08-26: cooldown is fine; pay-to-continue is axed.
- **drill.py** `CB.permanent_refusal` — [MEDIUM] the code contradicts
  - says: the code says it does instead
- **drill.py** `WO.resolve_code` — [MEDIUM] The code attempts to resolve a work order but does not handle the case where the cleanup failed, leading to a potential leak of the LOCAL_AGENT_BLAST_CAP order in the live queue.
  - says: A FAILED CLEANUP IS NOT NOTHING. Was `except Exception: pass`; a resolve that did not happen leaves a LOCAL_AGENT_BLAST_CAP order standing in the live queue on every cycle, and the reason it did not happen was thrown away at the moment it was known. Recorded now, in the ledger the rest of the project uses for exactly this.
- **address.py** `_index_name_is_placed_like_a_title` — [MEDIUM] The function checks if the index name is placed like a title, but the logic is flawed in how it handles pluralization and partial matches, leading to incorrect categorization of vocabulary vs title evidence.
  - says: The index entry sits inside the target: is it there as the title, or as vocabulary?
- **escalation.py** `clear` — [MEDIUM] clear() returns False for two different reasons, but the code treats them as the same event, leading to incorrect messages about the lift not happening.
  - says: PermissionError is caught alongside ValueError because `clear()` raises it for a non-person caller, and the two refusals are the same event to a reader: the lift did not happen and here is why.
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
