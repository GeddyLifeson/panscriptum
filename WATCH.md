# OVERWATCH

round 411  ·  last run 2026-09-07 03:30

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 298,265 inspected (deep scan as of round 409)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**21 open** (7 high). Newest first.

- **estate.py** `low` — [HIGH] low is a variable that is used but never defined in this file or its imports
  - says: low is a variable that is supposed to represent the combined lowercase text of the bottom three bands' descriptions
- **endpoint.py** `html_text` — [HIGH] Defined in another module, but not imported here
  - says: Extract text from HTML body
- **drill.py** `a_pure_ladder_is_all_ladder` — [HIGH] The function returns a result where 'eta' is 1.0, but the comment suggests it should return 0.0 for a shape with no ladder in it. The actual result contradicts the claim.
  - says: A STAR is EXACTLY representable: theta_a = 0.75, the three losers -0.25 each, reproducing every edge. eta must be 1.0 and the curl fraction 0.0. Under Jacobi this was 0.0 -- the answer for a shape with NO ladder in it at all, returned for a shape that is nothing but ladder.
- **drill.py** `S.replace_if_unchanged` — [HIGH] The function unconditionally returns "landed" for denied operations, which is incorrect.
  - says: The function should return the correct reason for a denied operation.
- **drill.py** `S.replace_if_unchanged` — [HIGH] The function returns (False, "landed") unconditionally, leading to incorrect logging of denied operations as successful.
  - says: A denied rename must not come back describing itself as a landing.
- **drill.py** `net` — [HIGH] The code calls net with a function that attempts to create a junction, which is unrelated to the scenario described in the first net call
  - says: The first net call claims to test a scenario where the local model may not write the prose gate or the module that pushes to the public
- **corpus_db.py** `deletion_check` — [HIGH] report unavailable when missing key
  - says: report deletions
- **escalation.py** `clear` — [MEDIUM] The code catches ValueError and PermissionError, but the comment suggests they are the same event, which may not be accurate.
  - says: PermissionError is caught alongside ValueError because `clear()` raises it for a non-person caller, and the two refusals are the same event to a reader: the lift did not happen and here is why.
- **escalation.py** `assert_clear` — [MEDIUM] raises an exception if the system is not halted, but the docstring says it's the interlock that makes the chain real and prevents the library from working while halted
  - says: EVERY entry point calls this before doing anything. The plant-wide interlock.
- **escalation.py** `escalate` — [MEDIUM] Rung 4, made DURABLE. Stop one subsystem until a person resumes it. -> the record.
  - says: Rung 4, made DURABLE. Stop one subsystem until a person resumes it.
- **drill.py** `CW._budget_left` — [MEDIUM] returns the budget and used counts, but the docstring says it's about spending and requiring it to run out
  - says: Spend the budget against a scratch ledger and require it to RUN OUT, then refill.
- **drill.py** `only_the_owner_rung_writes_a_halt` — [MEDIUM] the code checks for the existence of the halt file before escalating to OWNER, which may not have been created yet
  - says: a halt file appears at OWNER and at no rung below it
- **drill.py** `os.replace` — [MEDIUM] a stand-in that raises a PermissionError on the first attempt but allows subsequent calls
  - says: the function that performs a file rename
- **drill.py** `the_cap_resets_per_run` — [MEDIUM] ``blast_reset()` only clears the `patches` counter, not the `files` set, and the test is designed to check this
  - says: ``blast_reset()` clears the WHOLE budget, both halves of it.
- **drill.py** `LA._safe` — [MEDIUM] LA._safe is used to check a path that is supposed to be reachable, but the code indicates that the path is not reachable and the check is meant to verify that the path is accessible.
  - says: An ordinary in-surface path must still be reachable: a gate that refuses everything passes every refusal test ever written.
- **dashboard.py** `panelWatch` — [MEDIUM] displays swallowed failures but not all open findings
  - says: Overwatch — the standing sweep
- **dashboard.py** `hist` — [MEDIUM] is validated to be a list of dicts with numeric 'at' keys
  - says: THE GUARD HAS TO COVER THE FIELDS THE ARITHMETIC BELOW ACTUALLY USES
- **dashboard.py** `hist` — [MEDIUM] is reset to an empty list on any exception during loading
  - says: A CORRUPT HISTORY FILE MUST HEAL, NOT WEDGE.
- **dashboard.py** `movement` — [MEDIUM] Computes deltas against the oldest sample inside the window, but the comment suggests it should report changes over time, not just deltas.
  - says: What has CHANGED, not what the level is.
- **binding_health.py** `F.fetch` — [MEDIUM] fetch host and list of titles
  - says: fetch host and title
- **entity_match.py** `qualifier_compatible` — [MEDIUM] Returns True if both qualifiers are None or their normalized forms are equal, but does not handle cases where one qualifier is None and the other is not.
  - says: Two names may only be compared if their qualifiers agree.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
