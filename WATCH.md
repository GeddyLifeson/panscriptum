# OVERWATCH

round 296  ·  last run 2026-09-03 01:00

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 290,960 inspected (deep scan as of round 295)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**19 open** (9 high). Newest first.

- **catalogue_web.py** `record_path` — [HIGH] returns the path to the record file
  - says: returns whether the rename LANDED
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
- **catalogue_models.py** `sweep` — [MEDIUM] The code processes rows where the outcome is either LISTED or EMPTY_LIST, but the comment explains that the code should consider EMPTY_LIST as a successful measurement. However, the code's logic for determining 'live' and 'verified' includes EMPTY_LIST, which aligns with the comment's intention. The comment's confusion might be due to a misunderstanding of how the code handles these outcomes, but the code itself correctly includes EMPTY_LIST in the live and verified lists.
  - says: ON THE OUTCOME, NOT ON TRUTHINESS (sweep42-batch14).
- **local_agent.py** `run` — [MEDIUM] The function does check the halt condition via `assert_clear` but does not handle the case where the model's answer is empty and no patches were attempted, which is a failure case that should set `ok=False`.
  - says: THE HALT IS CHECKED HERE, AND UNTIL RUN #35 IT WAS NOT CHECKED ANYWHERE ON THIS LANE.
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
- **address.py** `_index_name_is_placed_like_a_title` — [MEDIUM] The function checks if the index name is placed like a title, but the logic is flawed in how it handles pluralization and partial matches, leading to incorrect categorization of vocabulary vs title evidence.
  - says: The index entry sits inside the target: is it there as the title, or as vocabulary?
- **escalation.py** `clear` — [MEDIUM] clear() returns False for two different reasons, but the code treats them as the same event, leading to incorrect messages about the lift not happening.
  - says: PermissionError is caught alongside ValueError because `clear()` raises it for a non-person caller, and the two refusals are the same event to a reader: the lift did not happen and here is why.
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
