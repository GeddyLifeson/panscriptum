# OVERWATCH

round 535  ·  last run 2026-09-15 01:57

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,914 inspected
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**29 open** (8 high). Newest first.

- **drill.py** `M.reap_orphans` — [HIGH] reaping all sandboxes in the temporary directory, including those not owned by the current process
  - says: reaping matched a prefix and an age and nothing else
- **drill.py** `ESC` — [HIGH] is used to refer to a variable or function that is not defined in this slice
  - says: is used to refer to the Escalation module
- **drill.py** `paid_access_stays_switched_off` — [HIGH] returns True when the config file is absent or unreadable, which could allow paid access if the config is missing or corrupted
  - says: allow_paid is owner-held. Nothing automatic may switch it on.
- **drill.py** `PL.phase_write` — [HIGH] Calls a function that does not exist in the current context, leading to potential errors or unexpected behavior.
  - says: Drive `pipeline.main()`'s phase loop over stubbed phases.
- **drill.py** `PL.phase_entrypass` — [HIGH] Calls a function that does not exist in the current context, leading to potential errors or unexpected behavior.
  - says: Drive `pipeline.main()`'s phase loop over stubbed phases.
- **completeness.py** `host_reachable` — [HIGH] returns a message about host unreachability but does not actually check reachability
  - says: checks if a host is reachable
- **codewatch.py** `escalation.escalate` — [HIGH] escalate is called with a value that is not escalation.MANAGER
  - says: MANAGER EITHER WAY -- see the docstring. The run guard describes; it does not rank.
- **chain.py** `write_result` — [HIGH] only persists `names` and `strengths` if the fit was successful
  - says: persist `names` and `strengths` whole
- **events.py** `shelf_positions` — [MEDIUM] Parses lines that start with | and contain 'Shelf' and 'stands at' to extract shelf and stands_at, but the actual implementation may not correctly handle the table structure as described.
  - says: The Concordance table: where each shelf stands at the Delivery. -> [{shelf, stands_at}].
- **endpoint.py** `html_text` — [MEDIUM] Strips script, style, and navigation tags, but does not remove other tags like div or p.
  - says: Readable text out of an HTML page.
- **endpoint.py** `fetch_raw` — [MEDIUM] returns the dict of found titles and the tally, but the tally is discarded
  - says: THIN WRAPPER OVER `fetch_raw_verdict`, ABOVE. This function's return contract is unchanged -- a dict of found titles only, nothing else -- so no existing caller (feats.py, hostcheck.py) needs to change. A caller that needs to tell a total refusal apart from a genuine absence should call `fetch_raw_verdict` directly for its tally instead of reading anything into this function's `{}`.
- **drill.py** `row` — [MEDIUM] return HC.score(...)['verdict']
  - says: return HC.score(...)['verdict']
- **drill.py** `kept` — [MEDIUM] the code is looking for a call to 'silence.write_json' which is not the same as the 'drill_last.json' file being overwritten
  - says: THE ROWS ARE KEPT UNDER A NAME THE NEXT RUN DOES NOT TOUCH, and the halt is told where
- **drill.py** `GL.lane` — [MEDIUM] the code tests for unarbitrable and busy lanes, but the actual behavior is not clearly defined in the code
  - says: a lane that cannot be arbitrated proceeds AT ONCE, and a busy one still waits
- **drill.py** `CW._report_if_never_settling` — [MEDIUM] returns False when the condition is met
  - says: reports if never settling
- **drill.py** `ESC.status` — [MEDIUM] returns halted status and record, but the code in the slice may not correctly handle all cases
  - says: returns halted status and record
- **drill.py** `a_lost_escalation_says_so_on_the_record` — [MEDIUM] the code attempts to test that an escalation is recorded, but the test is flawed and does not correctly verify the behavior described in the docstring
  - says: THE JANITOR'S RUNG REPORTS WHETHER IT ACTUALLY TOOK THE ALARM DOWN.
- **drill.py** `F.fetch` — [MEDIUM] replaced with a stub that returns an empty dict
  - says: called `feats.fetch(host, [title])` WITHOUT the `outcome=` dict
- **drill.py** `generate_failures_save_keeps_a_concurrent_runs_rows` — [MEDIUM] The function tests that generate.py does not write failures.json as a whole, but the code in the function does not actually perform this check; it only collects problems and does not enforce the behavior.
  - says: generate.py must land only its own failures.json changes, merged into the file as it is NOW -- the sibling of the catalog net above, for order ec8b8b35e521.
- **drill.py** `hosts_add_keeps_a_host_another_writer_landed_in_the_gap` — [MEDIUM] The function is named to imply a race condition scenario but the code does not implement any concurrency mechanisms or race condition handling. The code only sets up variables but does not perform any operations that would trigger the described race condition.
  - says: A rival writer lands its host AFTER `add()` has read the map and BEFORE `add()` writes. Without compare-and-swap the rival's host is overwritten and both callers believe they succeeded.
- **drill.py** `read_frag` — [MEDIUM] the fragment is not safe
  - says: the fragment is safe
- **drill.py** `creationflags` — [MEDIUM] sets the creation flags for the subprocess on Windows
  - says: suppresses its console window
- **cleanup.py** `low_pref` — [MEDIUM] filter entries starting with the ceiling entity but return the shortest one as 'prefix' when there's exactly one match
  - says: filter entries starting with the ceiling entity
- **chain.py** `changed` — [MEDIUM] Seeded at 1, not 0, when the recipe itself just changed above: that write belongs in this cycle's land even on an empty corpus (no file loop iteration would otherwise set `changed`)
  - says: Seeded at 1, not 0, when the recipe itself just changed above: that write belongs in this cycle's land even on an empty corpus (no file loop iteration would otherwise set `changed`)
- **chain.py** `live` — [MEDIUM] Seeded at 1, not 0, when the recipe itself just changed above: that write belongs in this cycle's land even on an empty corpus (no file loop iteration would otherwise set `changed`)
  - says: Seeded at 1, not 0, when the recipe itself just changed above: that write belongs in this cycle's land even on an empty corpus (no file loop iteration would otherwise set `changed`)
- **catalogue_web.py** `tally` — [MEDIUM] tally is a dictionary that is modified in a non-atomic way, leading to potential race conditions when multiple threads access it concurrently.
  - says: Record and roll writes are serialized under a lock; a source is still written atomically, whole.
- **cascade_bridge.py** `try_disabled` — [MEDIUM] Attempts to enable models and test them, but the code does not actually verify if they have a working key as described.
  - says: Test models that are switched off in config but DO have a working key.
- **catalogue_aurora.py** `roll_landed` — [MEDIUM] used as a flag to determine if the roll was successfully updated, but the code does not properly handle the case where the update might have failed
  - says: COMPARE-AND-SWAP, BECAUSE ATOMIC WAS NEVER THE PROPERTY THIS NEEDED
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
