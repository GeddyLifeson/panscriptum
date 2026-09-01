# OVERWATCH

round 257  ·  last run 2026-09-01 14:27

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 287,541 inspected (deep scan as of round 253)  — state\model_metrics.jsonl — malformed JSON on line 102599: Expecting value: line 1 column 1 (char 0)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py
- NOT RUNNING: **0** read.py

## What the model found in the code

**21 open** (8 high). Newest first.

- **standards.py** `ollama_token_flow` — [HIGH] Hardcodes a context size of 512, which may not match the actual configuration, leading to incorrect probe results.
  - says: Does a generation actually COMPLETE? The third liveness lesson in two days.
- **resync_roll.py** `return 1` — [HIGH] Indicates a failure, but the comment says it's for when the roll is unchanged and the fixes didn't land. However, the code returns 1 when the roll is unchanged, which contradicts the comment's explanation.
  - says: Nonzero, because this is the branch where the file on disk is NOT what the lines above describe. `main()`'s value only became the process's exit code when the module started calling `sys.exit(main())` below; before that a supervisor or a person reading $? after a cataloguing session was told the roll now agrees with the record files while the roll was untouched. Two independent defects, one signal -- the bare `return` here was the other half.
- **prose_gate.py** `section_shortfall` — [HIGH] Returns present, required, missing without raising exceptions
  - says: Raise unless every entry in this block carries every required section.
- **pipeline.py** `phases` — [HIGH] uses args.phase which is validated to be in range, but the code later uses PHASES[ph-1] which could be out of range if ph is 0 or len(PHASES)+1
  - says: derive the range of phases to run based on --phase and state
- **pipeline.py** `gate_done` — [HIGH] The code is using `gate_done` to mark phase 8 as done based on the `landed` list, which may be empty or contain False, leading to incorrect phase completion in cases where all sources refused to build.
  - says: A THIRD ARM WAS ADDED HERE ON 2026-09-01 AND REVERTED THE SAME SHIFT. Recorded so the next reader does not re-derive it a third time.
- **pipeline.py** `phase_chain` — [HIGH] Phase 4 -- the Chain of Defeats. See chain.py for the reasoning. This existed as a standalone module and NOT as a phase, so the runner reached phase 4, found no `phase_chain`, and stopped cleanly every single time -- reporting "not implemented yet" about a module that was finished and working. Phase 4 only ever ran when somebody invoked it by hand, and phases 5 through 8 were never even attempted, because the runner never got past the gap. A finished stage that nothing dispatches to is indistinguishable from a stage that was never written, which is this project's defect wearing yet another hat.
  - says: Phase 4 -- the Chain of Defeats. See chain.py for the reasoning.
- **pipeline.py** `_PATIENT` — [HIGH] Matches text that describes something done TO the subject (PATIENT), which should be rejected, but the code returns an empty string, effectively discarding the failure the comment says is important
  - says: The entity must be the AGENT. 'must be located, activated, and destroyed to save a planet' describes something done TO the subject and was licensing an M3.
- **magnitude.py** `band_hits` — [HIGH] counts BAND MATCHES ONLY (got_band == band), but the code returns it as the verdict which requires all scored rows to be consistent
  - says: counts BAND MATCHES ONLY (got_band == band)
- **sweep.py** `sil` — [MEDIUM] list of rows with pages but no axes
  - says: REACHED BUT SILENT — read, yet no axis found anything
- **sweep.py** `gap` — [MEDIUM] counts the number of sources with no host
  - says: HARD RULE 0 ON BOTH LISTS BELOW. These were `most_common(10)` and `most_common(8)`, ranked
- **standards.py** `fab` — [MEDIUM] fabrication rate only if the reader has progress line and the line can be parsed
  - says: fabrication rate
- **prose_gate.py** `evidence_ok` — [MEDIUM] Checks if frac < floor, but the comment says it should fail closed on an unmeasured source
  - says: Has this source been read enough to be worth writing about?
- **prose_gate.py** `floor_ok` — [MEDIUM] Returns False for floor <= 0, but the comment says a floor at or below zero is MISCONFIGURED and should refuse
  - says: Is this a usable evidence floor? Asked in ONE place, by both layers.
- **overnight.py** `preflight` — [MEDIUM] Returns (n_failing_checks, blocking) even when preflight fails to run, which can lead to incorrect blocking decisions
  - says: Returns (n_failing_checks, blocking). Only corrupted source blocks.
- **magnitude.py** `anchor` — [MEDIUM] assigned based on got.get("anchor") and ceiling[1]
  - says: a fiction cannot be out-scaled by its own inhabitant
- **magnitude.py** `quantity_scores` — [MEDIUM] Axis scores computed from quantities, but the function does not properly handle the case where the entity is not the one performing the act, and the function does not properly handle the case where the quantity is not convertible to the required units.
  - says: Axis scores computed arithmetically from measured quantities. No model opinion involved.
- **health.py** `silence.write_json` — [MEDIUM] silence.write_json returns False when denied, but the code does not handle this case properly, leading to a potential failure to record problems
  - says: NEVER FATAL. A preflight that dies because it could not write its own report is worse than one that cannot report
- **generate.py** `generate_job` — [MEDIUM] generate_job is called but the code does not handle any exceptions or errors that may occur during generation
  - says: generate_job is called to generate the job's text
- **allsweep.py** `allsweep.VERIFIERS` — [MEDIUM] a list of Verifier objects
  - says: A plain three-tuple was the obvious shape
- **drill.py** `net` — [MEDIUM] net runs a test that is not properly scoped to the function it's testing
  - says: net runs a test
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
