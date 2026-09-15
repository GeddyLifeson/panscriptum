# OVERWATCH

round 542  ·  last run 2026-09-15 13:22

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 305,442 inspected (deep scan as of round 541)  — state\gpu_lane\slot.0.json — cannot stat: GONE (absent on a second look, one rename later)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**38 open** (14 high). Newest first.

- **feats_index.py** `source_binding` — [HIGH] Returns "unknown" when the WIKI_HOSTS file is unreadable, which is not unbound.
  - says: Why does this source have no host? -> "bound" | "pages" | "doc" | "unbound".
- **worldseed.py** `to_fmg_query` — [HIGH] emits parameters that are not actually honoured by the generator, such as 'options' and 'width', 'height'
  - says: Render for Azgaar, emitting ONLY what that generator actually honours.
- **workorders.py** `for_ladder` — [HIGH] the function is called but the code does not handle the case where the queue is unreadable, instead it proceeds to check if rungs is empty and prints "no open work orders" which is incorrect for an unreadable queue
  - says: AN UNREADABLE QUEUE IS NOT AN EMPTY ONE, AND THE DIFFERENCE IS THE WHOLE POINT (order 5d3794de8b81). Before this, a corrupt state/workorders.json reached the reader as `{}` and printed the "nothing outstanding" line below -- which `battery_faults`' own docstring records as precisely the failure this module was built to end. `_load` now raises instead, and this is where a person sees it: a named file, a named cause, and a nonzero exit so no script reads the shift as clean.
- **workorders.py** `resolve_code` — [HIGH] is never called because the condition is always false
  - says: resolves a code to a resolution
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
- **genre.py** `classify_text` — [HIGH] Returns the top N genres, ranked (genre, score).
  - says: Score every genre against a body of text. Returns ALL of them, ranked (genre, score).
- **worldseed.py** `to_fmg_query` — [MEDIUM] to_fmg_query is supposed to generate a query string for a worldseed, but the code uses it to print a truncated URL without further processing
  - says: to_fmg_query is supposed to generate a query string for a worldseed
- **worldseed.py** `to_options` — [MEDIUM] to_options is supposed to generate options for a worldseed, but the code uses it to append entries to the output list without further processing
  - says: to_options is supposed to generate options for a worldseed
- **worldseed.py** `WORLD` — [MEDIUM] The regex is supposed to find any of the specified words in the name or description, but the code checks for the absence of such words and skips entries without them
  - says: The regex is supposed to find any of the specified words in the name or description
- **worldseed.py** `build_all` — [MEDIUM] build_all(limit=0) returns an empty list because the limit check is triggered immediately
  - says: build_all(limit=0) is supposed to return all entries without limit
- **workorders.py** `reroute` — [MEDIUM] move an order to a different rung
  - says: reroute an order
- **workorders.py** `resolve` — [MEDIUM] close an order
  - says: resolve an order
- **workorders.py** `filed.extend([])` — [MEDIUM] no-op standing where the close pass should have been
  - says: close the ones that recovered
- **workorders.py** `path` — [MEDIUM] is assigned the value of `path` or `OPEN_FILE` but not checked for existence
  - says: DEFAULTS TO THE LIVE `OPEN_FILE` AND EXISTS SO A READ-ONLY CALLER CAN POINT THIS AT A DISPOSABLE COPY INSTEAD
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
- **mutate.py** `base` — [MEDIUM] baseline
  - says: baseline
- **foreman.py** `codewatch.exit_if_stale` — [MEDIUM] checks if the code is stale and exits if it is, but the comment says it's for picking up code changes
  - says: PICK UP CODE CHANGES
- **foreman.py** `lines_changed` — [MEDIUM] measures the number of lines changed using difflib, which is correct
  - says: LINES CHANGED, not the difference in line COUNT. This gate is the one the module docstring sells as bounding how much of a function a model rewrite may touch, and it was measuring `abs(len(new) - len(old))` -- a net total. A rewrite that replaced every line of an 80-line function and happened to land on 82 lines scored `delta = 2` and passed a gate meant to stop exactly that. The message said "patch changes 2 lines", which was false.
- **foreman.py** `restart_ollama` — [MEDIUM] return a tuple indicating success or failure
  - says: restart the local model
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
