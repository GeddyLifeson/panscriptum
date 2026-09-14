# OVERWATCH

round 501  ·  last run 2026-09-14 02:06

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,019 inspected (deep scan as of round 499)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**14 open** (8 high). Newest first.

- **entity_match.py** `candidates` — [HIGH] Returns a dictionary with a list of matches, but the structure is inconsistent (returns a dict when names are present, but a list when names are absent).
  - says: Rank every compatible catalogue entry for `name`.
- **drill.py** `silence.write_json` — [HIGH] a TRUNCATE-THEN-FILL, not a write
  - says: this project's stated one correct way to land a shared file
- **drill.py** `CW.BUDGET_PER_HOUR` — [HIGH] hardcoded and not dynamically derived as the code around it suggests
  - says: used to determine budget per hour
- **drill.py** `the_probe_exemption_fails_closed_without_its_evidence` — [HIGH] returns False when health is present but raises, and when health is not present
  - says: must answer False when it cannot ask health at all
- **drill.py** `lambda: "pages_refused" in F.evidence_for.__doc__ or True` — [HIGH] testing if a docstring mentions the key, but the docstring does not mention it
  - says: testing if a docstring mentions the key
- **drill.py** `lambda: "pages_refused" in F.evidence_for.__doc__ or True` — [HIGH] a net that is unconditionally true due to or True
  - says: a net that could not fail until run #33
- **drill.py** `get` — [HIGH] undefined variable
  - says: retrieve data
- **descending_ladder.py** `PLANCK_LENGTH` — [HIGH] undefined
  - says: used here
- **drill.py** `CW.LEDGER` — [MEDIUM] reassigned but not used correctly in the context of the code's logic
  - says: redirected to a temporary directory
- **drill.py** `CW.LEDGER_LOCK` — [MEDIUM] reassigned to a new value but not properly managed in the context of the code's logic
  - says: redirected to a lock file
- **drill.py** `W.script_of` — [MEDIUM] returns the script name from a command tokenized by ON._cmd_tokens
  - says: returns the script name from a command
- **drill.py** `SC.mutate` — [MEDIUM] mutate a corpus with a lambda that updates the 'first' field
  - says: mutate a corpus
- **drill.py** `_failed_revert_is_escalated` — [MEDIUM] Analyzes the local_agent.py module for escalation paths, but the docstring indicates it should check if a failed revert is escalated
  - says: A revert that fails must reach something outliving the process
- **drill.py** `_the_retry_loop_runs_at_least_once` — [MEDIUM] Checks if STOP_CAS_ATTEMPTS is an integer >= 1, but the docstring indicates it should ensure the loop runs at least once
  - says: Ensure STOP_CAS_ATTEMPTS is an integer >= 1

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
