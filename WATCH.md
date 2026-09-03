# OVERWATCH

round 299  ·  last run 2026-09-03 04:22

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 290,960 inspected (deep scan as of round 295)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**30 open** (7 high). Newest first.

- **publish.py** `leaks` — [HIGH] leaks is a list of findings that are not suppressed, and the code raises an error for them
  - says: Suppressed findings are REPORTED by the scanner and excluded from the refusal
- **publish.py** `prune_export` — [HIGH] deletes files from the live project
  - says: REFUSES TO RUN ANYWHERE BUT THE EXPORT COPY
- **pipeline.py** `write_record` — [HIGH] write_record returns True even if the merge is partial (i.e., some entries are not written due to name collisions), but the function does not ensure all entries are written to disk. The function may return True even if the merge is partial, which contradicts the docstring's claim that it was written to stop the 30,207-entries-to-1,051 revert.
  - says: write_record: ... returns True, 0 of 20 settled on disk
- **pipeline.py** `gate_done` — [HIGH] Marks a phase done if all artifacts landed, but the docstring says that the callers did not use the verdict from _landed(), leading to incorrect marking even if some artifacts failed to land.
  - says: Mark a phase done ONLY if every artifact it wrote actually landed.
- **onomast.py** `merged` — [HIGH] retired is True if cid is not in resolved
  - says: STANDING IS NOT RETIRED, AND THIS USED TO FLAG BOTH THE SAME WAY
- **magnitude.py** `band_hits` — [HIGH] counts BAND MATCHES ONLY (got_band == band), while the verdict requires every scored row consistent (got_band == band and abs(got_val - val) <= ci + got_ci)
  - says: anchor band reproduced on {band_hits}/{len(BENCHMARKS)} published assays
- **ledger_guard.py** `silence.append_line` — [HIGH] used bare `open(CHAIN, "a")`
  - says: THROUGH `silence.append_line`, NOT A BARE `open(CHAIN, "a")` (order f7b611d107cb, sweep41-batch10). This was the exact pattern measured on 2026-09-01 losing 704 of 3,200 rows: `O_APPEND` makes the seek-to-end and the write one operation on POSIX, and the Windows CRT implements it as a seek FOLLOWED BY a write, so two processes seek to the same end offset and the second lands ON the first. `silence.append_line` was written that same day to close it -- an OS-level lock on a sidecar plus `O_BINARY` -- and this call site, in the module whose own commentary quotes that measurement, was still using the old shape.
- **publish.py** `write` — [MEDIUM] Writes the data file with a temporary name based on pid and thread to avoid collisions
  - says: Land the page's data file. -> its path.
- **onomast.py** `well_formed` — [MEDIUM] Enforces constraints that may not align with the intended pronounceability checks
  - says: Is this a name a Custos could say aloud and write down twice the same way?
- **manifest_builder.py** `manifest_landed` — [MEDIUM] is assigned the return value of write_json, which is a boolean indicating JSON write success
  - says: returns whether the rename LANDED
- **magnitude.py** `census` — [MEDIUM] only contains attempted, answered, refused, sentences, sentences_unread
  - says: count of attempted, answered, refused, etc.
- **magnitude.py** `_HANDOFF` — [MEDIUM] Matches patterns where the entity is not the doer
  - says: The entity must be the DOER
- **hostcheck.py** `purge-record` — [MEDIUM] the entries are cleared and the removal is stamped into the record
  - says: the gap it leaves is a recorded finding rather than a silence
- **health.py** `preflight` — [MEDIUM] the function is called but its return value is not used in the code's logic
  - says: actually run, with no error -- the module would still exit 0/1 on whatever it did instead.
- **health.py** `preflight` — [MEDIUM] Returns the number of problems found, but the function's purpose is to run checks and write a stamp, not just count problems
  - says: Run every preflight check. -> the number of problems found.
- **generate.py** `generate_job` — [MEDIUM] generate_job is called but the code does not handle the case where the job generation fails, leading to unhandled exceptions
  - says: generate_job is called to generate text for a job
- **dashboard.py** `codewatch.exit_if_stale` — [MEDIUM] Exits rc=17 on purpose when src/ has changed and held still
  - says: Exits rc=17 on purpose when src/ has changed and held still
- **dashboard.py** `safety` — [MEDIUM] The function imports the `feats` and `binding_health` modules and processes the backoff and quarantine data. However, the code does not explicitly state that the backoff and quarantine data are used to identify hosts being paced slower or quarantined for persistent throttling, as described in the comment.
  - says: Hosts currently being paced slower than their base rate, and any host quarantined for persistent throttling. A backoff that nothing reports is indistinguishable from a slow network, which is how "we are being blocked" becomes "this source is empty".
- **dashboard.py** `safety` — [MEDIUM] The function imports the `assay` module and calls `calibration_report()`, which is used to derive the calibration data. However, the code does not explicitly state that this calibration is re-derived and not read from a constant, as mentioned in the comment.
  - says: The calibration is RE-DERIVED here, not read from a constant -- it is the one number every printed Magnitude in the library inherits, and the halved interval survived for months because the checks that watched it had been recorded from its own bad output.
- **dashboard.py** `safety` — [MEDIUM] The function reads data from `state/drill_last.json` and calculates the age of the data, which aligns with the claim. However, the code does not explicitly state that the age is crucial for distinguishing between current and past data states.
  - says: The drill writes `state/drill_last.json` when it runs and this reports what it found and HOW OLD that is -- an age is not decoration here, it is the difference between "57 nets held" and "57 nets held, at some point, possibly before the change you are looking at".
- **dashboard.py** `safety` — [MEDIUM] The function does not explicitly mention the polling interval or the denial-of-service concerns related to running the drill or liveness checks. The code focuses on reading data from files and does not address these specific polling or performance issues.
  - says: The dashboard polls every five seconds; a panel that ran the drill would be a denial-of-service against its own library, and a panel that ran `liveness` would take a minute per poll.
- **dashboard.py** `safety` — [MEDIUM] The function reads data from files (e.g., escalation, prose_gate, assay, feats, binding_health), but some fields may be computed or derived from these files rather than being directly read. For example, the 'age_min' in the 'drill' section is computed based on the file's modification time.
  - says: Every field here is READ from a file, never computed by running the thing it reports on.
- **dashboard.py** `safety` — [MEDIUM] The function returns a dictionary with various safety-related data, but the code does not explicitly state that this is the first thing the page shows or the first thing a run reads. The function's implementation does not directly relate to the page's initial display or the first thing a run reads.
  - says: The interlocks, as data. The FIRST thing the page shows and the first thing a run reads.
- **catalogue_models.py** `sweep` — [MEDIUM] The code processes rows where the outcome is either LISTED or EMPTY_LIST, but the comment explains that the code should consider EMPTY_LIST as a successful measurement. However, the code's logic for determining 'live' and 'verified' includes EMPTY_LIST, which aligns with the comment's intention. The comment's confusion might be due to a misunderstanding of how the code handles these outcomes, but the code itself correctly includes EMPTY_LIST in the live and verified lists.
  - says: ON THE OUTCOME, NOT ON TRUTHINESS (sweep42-batch14).
- **local_agent.py** `run` — [MEDIUM] The function does check the halt condition via `assert_clear` but does not handle the case where the model's answer is empty and no patches were attempted, which is a failure case that should set `ok=False`.
  - says: THE HALT IS CHECKED HERE, AND UNTIL RUN #35 IT WAS NOT CHECKED ANYWHERE ON THIS LANE.
- **drill.py** `GL._take_slot` — [MEDIUM] return None or False
  - says: arbitrate a slot
- **drill.py** `drill_no_top_ups` — [MEDIUM] The function defines and runs tests related to ruling on provider behaviors, but the actual implementation does not directly enforce the ruling. The ruling is more about the logic in the tests rather than the function itself.
  - says: OWNER RULING 2026-08-26: cooldown is fine; pay-to-continue is axed.
- **address.py** `_index_name_is_placed_like_a_title` — [MEDIUM] The function checks if the index name is placed like a title, but the logic is flawed in how it handles pluralization and partial matches, leading to incorrect categorization of vocabulary vs title evidence.
  - says: The index entry sits inside the target: is it there as the title, or as vocabulary?
- **escalation.py** `clear` — [MEDIUM] clear() returns False for two different reasons, but the code treats them as the same event, leading to incorrect messages about the lift not happening.
  - says: PermissionError is caught alongside ValueError because `clear()` raises it for a non-person caller, and the two refusals are the same event to a reader: the lift did not happen and here is why.
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
