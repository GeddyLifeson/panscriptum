# OVERWATCH

round 439  ·  last run 2026-09-08 05:16

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 300,109 inspected
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**39 open** (15 high). Newest first.

- **secondopinion.py** `mine_says` — [HIGH] mine_says is not defined in the provided code, and the code uses a different approach to get the secrets count
  - says: mine_says(paths) is called to get the secrets count
- **publish.py** `prune_export` — [HIGH] Deletes files and directories in the export copy when they are not in the wanted set
  - says: Refuses to delete a live tree, but the code does not actually refuse to delete anything
- **onomast.py** `load_onomasticon` — [HIGH] Returns an empty dict on FileNotFoundError and on unreadable files, overwriting existing data instead of refusing to overwrite.
  - says: Load the onomasticon from a file, returning the content or an empty dict on error.
- **onomast.py** `well_formed` — [HIGH] Implements seven constraints, but the docstring claims the function was meant to have four constraints and incorrectly attributes three of the four to the wrong constraints
  - says: Is this a name a Custos could say aloud and write down twice the same way?
- **entity_match.py** `candidates` — [HIGH] Returns a list of {name, score, reason} sorted best-first, but the function's return shape is inconsistent between early exits and the normal path, returning a dict for the normal path and a list for early exits, which can cause AttributeErrors when accessing keys like 'blocked_by_qualifier' on lists.
  - says: Rank every compatible catalogue entry for `name`.
- **drill.py** `axis_score` — [HIGH] returns a number when hi == lo
  - says: An inverted or degenerate band pair must return None, not a number.
- **drill.py** `a_lift_keeps_the_characters_of_the_ruling` — [HIGH] the ruling is stored as Unicode escape sequences
  - says: the ruling is kept in the characters it was written in
- **drill.py** `ESC.escalate` — [HIGH] stringifies every real evidence mapping into `"{'a': 1}"`, which no reader can index
  - says: evidence survives as a mapping or a list, and anything else becomes text
- **drill.py** `ESC.escalate` — [HIGH] records the SCRIPT for every escalation, so every alarm in the log claims to come from whatever ran it
  - says: the caller's name is recorded, not the process's
- **drill.py** `ESC.escalate` — [HIGH] sends every correctly-named rung to MANAGER instead
  - says: a rung named as a string resolves to that rung
- **drill.py** `ESC.brief` — [HIGH] hands every rung an empty record -- the alarm sounds and says nothing
  - says: a field that is None must not
- **drill.py** `ESC._safe_name` — [HIGH] a truncating name silently merges two areas of the park, and a person reading one source's escalations is reading another's without being told
  - says: two long source names sharing a 60-character prefix do NOT share a log
- **drill.py** `ESC._safe_name` — [HIGH] returns 'unscoped' for EVERY source, which is the same collapse arriving from the other side
  - says: an empty source name gets the documented stand-in
- **drill.py** `ESC._safe_name` — [HIGH] suffixes every short name and truncates no long one -- it renames every existing log on disk and stops disambiguating the names that actually collide
  - says: a short name is not given a digest it does not need
- **drill.py** `ESC._safe_name` — [HIGH] it renames every existing log on disk and stops disambiguating the names that actually collide
  - says: every alphanumeric becomes '_' and every source's log collapses into one file named for none of them
- **read.py** `run` — [MEDIUM] ok is False when this pass errored on every entity it touched
  - says: ok is False when this pass errored on every entity it touched
- **read.py** `_ask_ungated` — [MEDIUM] Is called directly in some cases, bypassing the gate, which may lead to incorrect resource management.
  - says: The transport ladder itself. Call _ask, not this, unless you are the gate.
- **read.py** `_ask` — [MEDIUM] Always uses the adaptive gate, but the gate's logic may not correctly handle the local transport due to the way _card_gate is used.
  - says: One structured call, by whichever transport is available -- through the adaptive gate.
- **publish.py** `push` — [MEDIUM] push() raises PushHeld when a push is held, which is caught in an except block that prints the error and sets rc=1. However, the comment block claims that push() has only two return values (landed or no change) and that the third outcome (committed but held) comes out as PushHeld. This is correct, but the comment block's wording is misleading because it implies that push() returns values, whereas in reality, push() raises exceptions. The comment block's claim is about return values, but the actual behavior is about exception raising. This is a defect of fact because the code's behavior contradicts the comment's claim.
  - says: push() now has only two RETURN values, and both are honest ones: it landed, or there was nothing to land. The third outcome -- committed but held -- comes out as `PushHeld` and is caught below, where it prints and sets rc=1, because a held push reported as "no change to push" with rc=0 is this comment block's own rule broken one line further down the function.
- **publish.py** `porcelain` — [MEDIUM] porcelain
  - says: porcelain
- **publish.py** `git` — [MEDIUM] git
  - says: git
- **publish.py** `leaks` — [MEDIUM] leaks includes suppressed findings by checking if not str(h[2]).startswith('SUPPRESSED')
  - says: Suppressed findings are REPORTED by the scanner and excluded from the refusal
- **pipeline.py** `gate_done` — [MEDIUM] marks phase 8 done on `all([]) == True` having built nothing
  - says: A THIRD ARM WAS ADDED HERE ON 2026-09-01 AND REVERTED THE SAME SHIFT. Recorded so the next reader does not re-derive it a third time.
- **overwatch.py** `codewatch.exit_if_stale` — [MEDIUM] Exits with rc=17 if the process is stale
  - says: Exits with rc=17 on purpose
- **mutate.py** `run` — [MEDIUM] execute a target and return results
  - says: run a target
- **mutate.py** `could_not_judge` — [MEDIUM] returns True if the signature starts with 'TIMEOUT' or 'ERROR:'
  - says: -> True if this signature means the gate never reached a verdict, on clean code OR on a mutant.
- **local_agent.py** `out` — [MEDIUM] overwritten by the loop's final return
  - says: the final output of the loop
- **local_agent.py** `t_find_symbol` — [MEDIUM] Returns a list of hits with file, line, and kind, but does not provide uniqueness verdict or enclosing class information as claimed.
  - says: Every definition of `name`, with its enclosing class and a uniqueness verdict.
- **ingest_doc.py** `bad_category` — [MEDIUM] bad_category is a counter for invalid categories, not a mechanism for substitution
  - says: bad_category is what makes the substitution visible instead of silent
- **ingest_doc.py** `write_record_catalogue` — [MEDIUM] write_record_catalogue is used for writing to the catalogue, not for merging records
  - says: write_record's disk-wins merge DISCARDED the first 14 entities this module ever found
- **foreman.py** `unrestartable` — [MEDIUM] unrestartable jobs are not escalated
  - says: A stalled job nothing would restart is escalated, not silently left
- **foreman.py** `kill_stalled` — [MEDIUM] killed stalled and unrestartable jobs
  - says: killed stalled
- **foreman.py** `silence.write_json` — [MEDIUM] write_json is called with the wrong parameters
  - says: write_json
- **drill.py** `GL._take_slot` — [MEDIUM] None from `_take_slot` means GO NOW; False means wait. -> bool.
  - says: None from `_take_slot` means GO NOW; False means wait. -> bool.
- **drill.py** `the_floor_never_rises_to_go_green` — [MEDIUM] The function tests for a floor that is never raised, but the test case includes a deliberately unparseable floor file which causes `_floor_verdict` to raise an exception, and the function does not handle this exception properly, leading to an incorrect test result.
  - says: §8's ratchet, read in the direction this floor points: a baseline is recorded once, lowered when the count drops, and NEVER raised by anything in the automation.
- **drill.py** `the_verdict_travels_on_the_record` — [MEDIUM] the code returns the value of 'halt_landed' which is not updated in the function
  - says: the record says whether the halt actually landed
- **drill.py** `a_raised_halt_reads_back_as_halted` — [MEDIUM] the code checks if the halt is not cleared, but the comment says it should read back as standing
  - says: a halt that was raised reads back as standing
- **drill.py** `a_waf_rejection_is_not_an_account_fault` — [MEDIUM] returns True if both 'HTTP 403 error code: 1010' and '403 Just a Moment... cloudflare' are not permanent refusals
  - says: checks if Cloudflare rejections are not considered account faults
- **descending_ladder.py** `rung_for_length` — [MEDIUM] Returns (rung, name) for sizes within the DESCENDING range, but returns (None, None) for sizes above the range, and a Fold name for sizes below the Planck length. However, the function's docstring states that the domain is bounded at both ends and out-of-domain is answered with (None, None) at both ends, but the function returns a Fold name for sizes below the Planck length, which is not explicitly mentioned in the docstring.
  - says: Which descending rung does a given size belong to? Returns (rung, name).

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
