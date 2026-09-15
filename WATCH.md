# OVERWATCH

round 538  ·  last run 2026-09-15 10:33

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,914 inspected (deep scan as of round 535)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**48 open** (15 high). Newest first.

- **policy.py** `ev_unreadable` — [HIGH] A RECORD THAT COULD NOT BE READ IS A PASS
  - says: A RECORD THAT COULD NOT BE READ IS NOT A PASS
- **onomast.py** `load_onomasticon` — [HIGH] Returns an empty dict on FileNotFoundError and on parse errors, but the docstring says it should return the loaded onomasticon or an empty dict on error
  - says: Return the loaded onomasticon or an empty dict on error
- **onomast.py** `coin_well_formed` — [HIGH] Returns a name that may be malformed or already taken, and does not ensure uniqueness or well-formedness.
  - says: First well-formed, unused name for this seed. Deterministic: same input, same output.
- **onomast.py** `well_formed` — [HIGH] Implements seven constraints, but the docstring claims it checks four constraints and misattributes three of them.
  - says: Is this a name a Custos could say aloud and write down twice the same way?
- **hostcheck.py** `audit` — [HIGH] the audit is being filtered based on rate and judgeable flags
  - says: the audit shortlists, a person decides.
- **hostcheck.py** `foreign` — [HIGH] stride first, then dedupe
  - says: dedupe first, then stride
- **hostcheck.py** `_get` — [HIGH] Does not use feats._throttle as described in its docstring
  - says: One API call, PACED PER HOST.
- **genre.py** `classify_text` — [HIGH] Returns the top N genres, ranked (genre, score).
  - says: Score every genre against a body of text. Returns ALL of them, ranked (genre, score).
- **generate.py** `failures.pop` — [HIGH] popped before the catalog entry is built
  - says: popped only AFTER the catalog entry above is built
- **feats.py** `outcome` — [HIGH] never defined in this file or its imports
  - says: used as a channel for why None came back
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
- **prose_gate.py** `assert_gate_open` — [MEDIUM] Calls gate_open
  - says: Layer 2. The TOOL's own refusal, independent of whoever started it.
- **prose_gate.py** `step4_gate_open` — [MEDIUM] Calls gate_open
  - says: Layer 2. The TOOL's own refusal, independent of whoever started it.
- **profile.py** `B32` — [MEDIUM] used as an index lookup for features but the code may raise IndexError if the index is out of range
  - says: used as an index lookup for features
- **pick_model.py** `scored` — [MEDIUM] includes models that are resident and usable, but the code's comment says it's for models that are not refused, which is not the case
  - says: includes models that are resident and usable
- **pick_model.py** `fit_note` — [MEDIUM] returns a note that is only shown when VRAM is measured and the model is not refused, but suppresses the note when VRAM is zero
  - says: reports whether a model fits in VRAM
- **mutate.py** `base` — [MEDIUM] baseline
  - says: baseline
- **generate.py** `silence.note` — [MEDIUM] logs a generic message without specific error details
  - says: logs the failure with a meaningful message
- **generate.py** `generate_job` — [MEDIUM] may raise exceptions that are not properly handled or logged
  - says: generates a job's content
- **generate.py** `floor` — [MEDIUM] the evidence floor is misconfigured
  - says: the evidence floor is misconfigured
- **foreman.py** `codewatch.exit_if_stale` — [MEDIUM] checks if the code is stale and exits if it is, but the comment says it's for picking up code changes
  - says: PICK UP CODE CHANGES
- **foreman.py** `lines_changed` — [MEDIUM] measures the number of lines changed using difflib, which is correct
  - says: LINES CHANGED, not the difference in line COUNT. This gate is the one the module docstring sells as bounding how much of a function a model rewrite may touch, and it was measuring `abs(len(new) - len(old))` -- a net total. A rewrite that replaced every line of an 80-line function and happened to land on 82 lines scored `delta = 2` and passed a gate meant to stop exactly that. The message said "patch changes 2 lines", which was false.
- **foreman.py** `restart_ollama` — [MEDIUM] return a tuple indicating success or failure
  - says: restart the local model
- **foreman.py** `restart_ollama` — [MEDIUM] The function may not restart the service if the restart stamp is unreadable or if the tray is not running, but it does not clearly handle the case where the daemon is wedged and needs a restart. The function's logic for handling the tray and daemon states is complex and may not fully address the intended behavior of restarting the service when tokens stop flowing.
  - says: Restart the local model service when tokens stop flowing. AUTO by owner ruling (2026-08-24, "FIX IT ALL"): the wedge cannot clear itself -- twice in one day the daemon answered /api/tags while zero generations completed, once with no runner process and once with a runner spinning at 98% completing nothing -- and both times the only cure was a restart a person had to perform. The restart is mechanical and reversible (the tray app respawns the daemon; the resident model reloads on first call), and it is rate-limited: at most one automated restart per 30 minutes, so a deeper fault escalates to the owner instead of being restart-looped into invisibility.
- **foreman.py** `kill_stalled` — [MEDIUM] killed stalled or spared based on conditions
  - says: killed stalled
- **foreman.py** `CB._PROVEN[0]` — [MEDIUM] clears the cached proof but does not force re-reading
  - says: force the next _alive() to re-read
- **feats.py** `work` — [MEDIUM] The function `work` is responsible for processing jobs, but the code inside the `if honour_quarantine` block does not correctly implement the intended quarantine logic. It checks if the host is in `held` and defers the job, but the comment suggests that the code should be enforcing the quarantine by stopping requests, which is not happening as described.
  - says: THE BRAKE THE HAND-OFF ALWAYS CLAIMED TO BE. `note_throttled` quarantines a host after THROTTLE_STRIKES consecutive 429s and its comment says the crawl stops spending requests on it; until the 2026-09-08 ruling nothing on the fetch path asked, so twelve workers went on queueing at the 32x ceiling. Asked here, once per entity, off a view refreshed at most once a minute.
- **feats.py** `_HOSTS_DENIED` — [MEDIUM] is set to the boolean result of replace_retry
  - says: is set to not silence.replace_retry(tmp, HOSTS)
- **feats.py** `replace_retry` — [MEDIUM] returns a boolean indicating whether the rename was successful
  - says: answers False rather than raising when the rename is denied
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
- **catalogue_aurora.py** `roll_landed` — [MEDIUM] used as a flag to determine if the roll was successfully updated, but the code does not properly handle the case where the update might have failed
  - says: COMPARE-AND-SWAP, BECAUSE ATOMIC WAS NEVER THE PROPERTY THIS NEEDED
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
