# OVERWATCH

round 544  ·  last run 2026-09-15 14:36

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 305,442 inspected (deep scan as of round 541)  — state\gpu_lane\slot.0.json — cannot stat: GONE (absent on a second look, one rename later)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**44 open** (15 high). Newest first.

- **manifest_builder.py** `feats_index.feats_for_source` — [HIGH] The code does not handle exceptions and does not produce the expected observable result when a failed lookup occurs.
  - says: AND A FAILED LOOKUP SAYS SO, OUT LOUD. `except Exception: silence.note(...)` alone made a BUG in `feats_index` -- a KeyError on a malformed record, an AttributeError, anything -- produce the identical observable result to "this source genuinely has no attested feats": `feat_rows = []`, no Feats chapter emitted, and a build report (the prints in `main()`) that reads exactly the same as a clean run. That is Hard Rule 0's central failure, a smaller-than-real output that nothing distinguishes from a legitimately small one, sitting directly under the comment explaining that 39,862 mined feats once existed with no volume able to print one. The note is kept for the ledger; the print is what reaches the operator watching the build. Found by the run #33 sweep (batch 15).
- **local_agent.py** `_deny_paths` — [HIGH] The code converts the denylist paths to lowercase, making the comparison case-insensitive, which may not be correct for the denylist asking of the file, not of its name.
  - says: THE DENYLIST ASKED OF THE FILE, NOT OF ITS NAME
- **local_agent.py** `_deny` — [HIGH] The code converts the denylist to lowercase, making the comparison case-insensitive, which may not be correct for the denylist asking of the file, not of its name.
  - says: THE DENYLIST ASKED OF THE FILE, NOT OF ITS NAME
- **local_agent.py** `_deny_paths` — [HIGH] The code converts the denylist paths to lowercase, making the denylist case-insensitive, which contradicts the claim that the denylist is case-sensitive.
  - says: THE DENYLIST IS CASE-SENSITIVE AND THE FILESYSTEM IS NOT.
- **ingest_doc.py** `write_record_catalogue` — [HIGH] it is a writer that merges and discards existing entries
  - says: this is a cast-growing writer
- **health.py** `F.api` — [HIGH] probe a host that may have been quarantined
  - says: probe a host we are actually still talking to
- **withdraw_chapters.py** `main` — [HIGH] Returns 1 if a.go is true and bad conditions are met, else 0. This contradicts the claim that it exits 0 unconditionally.
  - says: Every refusal above was printed and discarded. The tool should exit 0 unconditionally, including when catalog write was denied.
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
- **silence.py** `replace_retry` — [HIGH] raises on OSError (except for EXDEV, ENOSPC, etc.)
  - says: NEVER RAISES, FOR **ANY** OSError, not only for the denied one.
- **silence.py** `silent` — [HIGH] what it does instead
  - says: what the code says it does
- **manifest_builder.py** `silence.replace_retry` — [MEDIUM] The function is used to replace the temporary report file with the final path, but the comment suggests it's used for retrying operations, which may not be the intended use.
  - says: Land it through a pid+thread temp and silence.replace_retry, and report the verdict on the same footing as the manifest write instead of assuming it.
- **magnitude.py** `anchor` — [MEDIUM] assigned based on ladder index comparison and possibly from got
  - says: that, at the one place that knows nothing rescued it.
- **magnitude.py** `used` — [MEDIUM] used is set to 'split' if the prompt is too long, but in the 'local' branch, it's set to 'local' even if the prompt is not too long
  - says: used is set to 'split' if the prompt is too long, otherwise 'pool' or 'local'
- **local_agent.py** `backup` — [MEDIUM] store a copy of the original content but then immediately overwritten by the replacement operation
  - says: store a copy of the original content
- **local_agent.py** `original` — [MEDIUM] read the entire content of the file but then immediately overwritten by the replacement operation
  - says: read the entire content of the file
- **local_agent.py** `_spellings` — [MEDIUM] The code appends the lowercase version of the real path to the spellings list, which may not be correct for the denylist asking of both spellings of the path.
  - says: ASKED OF BOTH SPELLINGS OF THE PATH — BYPASS CLASS SEVEN
- **local_agent.py** `modname` — [MEDIUM] modname is assigned a value based on the file extension, but the code later uses it in a case-insensitive comparison with the denylist, which may not be correct for non-python files.
  - says: The denylist has to be answerable for NON-python files too. Match on the module name when there is one, and on the repo-relative path otherwise.
- **ingest_doc.py** `write_record_catalogue` — [MEDIUM] the cursor may lag; it may never lead
  - says: the cursor may lag; it may never lead
- **ingest_doc.py** `write_record_catalogue` — [MEDIUM] returns whether the rename actually landed
  - says: returns whether the rename actually landed
- **hosts.py** `discover` — [MEDIUM] probe alternative hosts for every source but does not keep all that hold
  - says: probe alternative hosts for every source and keep all that hold
- **hosts.py** `primary_host` — [MEDIUM] Returns the primary host or None if not found, but does not handle cases where the primary host is a sentinel like 'pages:' or 'doc:'
  - says: Return the primary host for a source
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the reopen_stranded function returns a value that is None, else 0
  - says: return 1 if the reopen_stranded function returns None, else 0
- **worldseed.py** `to_options` — [MEDIUM] to_options is supposed to generate options for a worldseed, but the code uses it to append entries to the output list without further processing
  - says: to_options is supposed to generate options for a worldseed
- **worldseed.py** `WORLD` — [MEDIUM] The regex is supposed to find any of the specified words in the name or description, but the code checks for the absence of such words and skips entries without them
  - says: The regex is supposed to find any of the specified words in the name or description
- **worldseed.py** `build_all` — [MEDIUM] build_all(limit=0) returns an empty list because the limit check is triggered immediately
  - says: build_all(limit=0) is supposed to return all entries without limit
- **workorders.py** `reroute` — [MEDIUM] move an order to a different rung
  - says: reroute an order
- **workorders.py** `filed.extend([])` — [MEDIUM] no-op standing where the close pass should have been
  - says: close the ones that recovered
- **withdraw_chapters.py** `_catalog_merge` — [MEDIUM] returns the remaining entries without modifying the original catalog, but the code expects it to modify the catalog
  - says: edits the catalog by removing entries whose files have been moved
- **verify_math.py** `check` — [MEDIUM] checks that the list _unspliced36 is empty
  - says: each batch file recorded as SPLICED still has labels standing in this file
- **verify_math.py** `check` — [MEDIUM] checks that the difference between _run35_all36 and _run35_seen36 is empty
  - says: every proposal file under handoff/run35 is executed, spliced, or on the register
- **verify_math.py** `check` — [MEDIUM] the code is using 'check' to perform assertions but the actual implementation of 'check' is not provided in the given code slice
  - says: check the code against a condition
- **silence.py** `replace_retry` — [MEDIUM] some faults are grouped under the same name
  - says: A DIFFERENT FAULT WEARS A DIFFERENT NAME IN THE LEDGER
- **silence.py** `note` — [MEDIUM] Can be called with a message that is not a string, leading to potential errors.
  - says: Records a note in the ledger with the given message.
- **silence.py** `build_parent_map` — [MEDIUM] Builds a parent map for every node in `tree` but the function is named `build_parent_map` and the code is correct
  - says: Builds a parent map for every node in `tree`
- **scout.py** `seen_ok` — [MEDIUM] set to False on read failure, but may be overwritten by subsequent code
  - says: indicate if SCOUT_ATTEMPTS.json was successfully read
- **foreman.py** `restart_ollama` — [MEDIUM] The function may not restart the service if the restart stamp is unreadable or if the tray is not running, but it does not clearly handle the case where the daemon is wedged and needs a restart. The function's logic for handling the tray and daemon states is complex and may not fully address the intended behavior of restarting the service when tokens stop flowing.
  - says: Restart the local model service when tokens stop flowing. AUTO by owner ruling (2026-08-24, "FIX IT ALL"): the wedge cannot clear itself -- twice in one day the daemon answered /api/tags while zero generations completed, once with no runner process and once with a runner spinning at 98% completing nothing -- and both times the only cure was a restart a person had to perform. The restart is mechanical and reversible (the tray app respawns the daemon; the resident model reloads on first call), and it is rate-limited: at most one automated restart per 30 minutes, so a deeper fault escalates to the owner instead of being restart-looped into invisibility.
- **drill.py** `ESC.status` — [MEDIUM] returns halted status and record, but the code in the slice may not correctly handle all cases
  - says: returns halted status and record
- **drill.py** `read_frag` — [MEDIUM] the fragment is not safe
  - says: the fragment is safe
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
