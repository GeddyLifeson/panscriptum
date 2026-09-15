# OVERWATCH

round 541  ·  last run 2026-09-15 12:18

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 305,442 inspected  — state\gpu_lane\slot.0.json — cannot stat: GONE (absent on a second look, one rename later)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**52 open** (18 high). Newest first.

- **withdraw_chapters.py** `main` — [HIGH] Returns 1 if a.go is true and bad conditions are met, else 0. This contradicts the claim that it exits 0 unconditionally.
  - says: Every refusal above was printed and discarded. The tool should exit 0 unconditionally, including when catalog write was denied.
- **wiki_source.py** `hard_stop` — [HIGH] cuts the answer
  - says: BOUNDS THE API WALK, NOT THE ANSWER
- **verify_math.py** `assign` — [HIGH] searches the entire module and can pick up assignments from other functions
  - says: finds the path assignment in the same function as the call
- **verify_math.py** `call_idxs` — [HIGH] uses a substring search on the source code which can be fooled by comments
  - says: finds the call site of verify_restore
- **verify_math.py** `_chunk_key` — [HIGH] returns the same key for entities reading the same passage
  - says: two entities reading the SAME passage get different cache keys
- **verify_math.py** `priority` — [HIGH] returns only rows with own > 0 or chars >= 2000
  - says: returns EVERY row it was given
- **verify_math.py** `_unrec_tmp` — [HIGH] assigned the value of _CB.UNRECOGNISED divided by 2
  - says: assigned the value of _CB.UNRECOGNISED
- **verify_math.py** `BG.burgs_for` — [HIGH] the k-th burg holds P1/k, but the value is clamped to the hamlet floor, which is incorrectly spelled as int(_bs[0]["population"] / 10) instead of BG.HAMLET_FLOOR
  - says: the k-th burg holds P1/k, independently recomputed
- **style_audit.py** `audit` — [HIGH] the varied fixture has a turn ending
  - says: the varied fixture has no turn ending
- **style_audit.py** `audit` — [HIGH] does not perform the audit, but calls another function that does
  - says: audits a corpus of entries for style issues
- **silence.py** `replace_retry` — [HIGH] raises on OSError (except for EXDEV, ENOSPC, etc.)
  - says: NEVER RAISES, FOR **ANY** OSError, not only for the denied one.
- **silence.py** `silent` — [HIGH] what it does instead
  - says: what the code says it does
- **secondopinion.py** `ran_clean` — [HIGH] used but never defined in this file or its imports
  - says: checks if all tools ran and found nothing
- **secondopinion.py** `mine_says` — [HIGH] Compares three different capabilities with different denominators, leading to potentially misleading comparisons.
  - says: The house detectors' verdict on the same three questions, for comparison. -> dict.
- **scout.py** `sweep` — [HIGH] Scouts the hostless sources, but the ordering logic is flawed and the limit parameter is misinterpreted as a filter rather than a rate limiter.
  - says: Scout the hostless sources, oldest attempt first. -> [result].
- **scout.py** `verify` — [HIGH] A page is judged against the first 25 names catalogued under the source
  - says: A page is judged against every name catalogued under the source
- **read.py** `codewatch.exit_if_stale` — [HIGH] exits the process if stale, which is not what the comment says it does
  - says: check between passes whether src/ has changed under this process (rc=17)
- **genre.py** `classify_text` — [HIGH] Returns the top N genres, ranked (genre, score).
  - says: Score every genre against a body of text. Returns ALL of them, ranked (genre, score).
- **withdraw_chapters.py** `_catalog_merge` — [MEDIUM] returns the remaining entries without modifying the original catalog, but the code expects it to modify the catalog
  - says: edits the catalog by removing entries whose files have been moved
- **withdraw_chapters.py** `_manifest_merge` — [MEDIUM] overwrites existing entries with the current run's withdrawals without considering the order of operations
  - says: merges the existing manifest with the current run's withdrawals
- **wiki_source.py** `hard_stop` — [MEDIUM] is None by default
  - says: DEFAULTED TO 6000
- **verify_math.py** `check` — [MEDIUM] checks that the list _unspliced36 is empty
  - says: each batch file recorded as SPLICED still has labels standing in this file
- **verify_math.py** `check` — [MEDIUM] checks that the difference between _run35_all36 and _run35_seen36 is empty
  - says: every proposal file under handoff/run35 is executed, spliced, or on the register
- **verify_math.py** `check` — [MEDIUM] the code is using 'check' to perform assertions but the actual implementation of 'check' is not provided in the given code slice
  - says: check the code against a condition
- **tiers.py** `deliberate_joins` — [MEDIUM] the source names are cut
  - says: THE TWO SOURCE NAMES SAY WHEN THEY ARE CUT
- **silence.py** `replace_retry` — [MEDIUM] some faults are grouped under the same name
  - says: A DIFFERENT FAULT WEARS A DIFFERENT NAME IN THE LEDGER
- **silence.py** `note` — [MEDIUM] Can be called with a message that is not a string, leading to potential errors.
  - says: Records a note in the ledger with the given message.
- **silence.py** `build_parent_map` — [MEDIUM] Builds a parent map for every node in `tree` but the function is named `build_parent_map` and the code is correct
  - says: Builds a parent map for every node in `tree`
- **scout.py** `seen_ok` — [MEDIUM] set to False on read failure, but may be overwritten by subsequent code
  - says: indicate if SCOUT_ATTEMPTS.json was successfully read
- **scout.py** `seen` — [MEDIUM] store a dictionary of seen sources, but may be overwritten by a failed read
  - says: store the contents of SCOUT_ATTEMPTS.json
- **publish.py** `snapshot` — [MEDIUM] overwrites `s['standards']` with an empty list and sets `s['standards_unavailable']` with error details
  - says: handle standards check failures gracefully
- **prose_gate.py** `assert_gate_open` — [MEDIUM] Calls gate_open
  - says: Layer 2. The TOOL's own refusal, independent of whoever started it.
- **pick_model.py** `scored` — [MEDIUM] includes models that are resident and usable, but the code's comment says it's for models that are not refused, which is not the case
  - says: includes models that are resident and usable
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
- **events.py** `shelf_positions` — [MEDIUM] Parses lines that start with | and contain 'Shelf' and 'stands at' to extract shelf and stands_at, but the actual implementation may not correctly handle the table structure as described.
  - says: The Concordance table: where each shelf stands at the Delivery. -> [{shelf, stands_at}].
- **endpoint.py** `html_text` — [MEDIUM] Strips script, style, and navigation tags, but does not remove other tags like div or p.
  - says: Readable text out of an HTML page.
- **drill.py** `row` — [MEDIUM] return HC.score(...)['verdict']
  - says: return HC.score(...)['verdict']
- **drill.py** `kept` — [MEDIUM] the code is looking for a call to 'silence.write_json' which is not the same as the 'drill_last.json' file being overwritten
  - says: THE ROWS ARE KEPT UNDER A NAME THE NEXT RUN DOES NOT TOUCH, and the halt is told where
- **drill.py** `ESC.status` — [MEDIUM] returns halted status and record, but the code in the slice may not correctly handle all cases
  - says: returns halted status and record
- **drill.py** `read_frag` — [MEDIUM] the fragment is not safe
  - says: the fragment is safe
- **catalogue_aurora.py** `roll_landed` — [MEDIUM] used as a flag to determine if the roll was successfully updated, but the code does not properly handle the case where the update might have failed
  - says: COMPARE-AND-SWAP, BECAUSE ATOMIC WAS NEVER THE PROPERTY THIS NEEDED
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
