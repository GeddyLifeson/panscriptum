# OVERWATCH

round 581  ·  last run 2026-09-28 08:02

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 308,357 inspected (deep scan as of round 577)  — reference\owner_source_material\rodais\Diathir_Atlas\fmg\libs\jszip.min.js — 2 control character(s) where an escape should be
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**24 open** (12 high). Newest first.

- **foreman.py** `restart_ollama` — [HIGH] Refuses to restart if the restart stamp could not be read, even though the comment says that an unreadable stamp is not an absent one and should allow the restart to proceed. The code returns False and a message, preventing the restart, while the comment indicates that the stamp should be treated as absent and the restart should proceed.
  - says: Restart the local model service when tokens stop flowing. AUTO by owner ruling (2026-08-24, "FIX IT ALL"): the wedge cannot clear itself -- twice in one day the daemon answered /api/tags while zero generations completed, once with no runner process and once with a runner spinning at 98% completing nothing -- and both times the only cure was a restart a person had to perform. The restart is mechanical and reversible (the tray app respawns the daemon; the resident model reloads on first call), and it is rate-limited: at most one automated restart per 30 minutes, so a deeper fault escalates to the owner instead of being restart-looped into invisibility.
- **feats.py** `roll` — [HIGH] the return value of `roll()` is discarded and 0 is returned unconditionally
  - says: THE COUNTERS REACH THE EXIT CODE
- **feats.py** `_QUANTITY_UNIT_FIRST` — [HIGH] Matches 'mach' followed by a number, but the regex is missing the unit part
  - says: A separate pattern for Mach numbers with unit-first form
- **feats.py** `why not in CLEAN_NEGATIVES` — [HIGH] The code is checking if 'why' is not in CLEAN_NEGATIVES, which is the opposite of what the comment suggests
  - says: Check if 'why' is not in CLEAN_NEGATIVES
- **drill.py** `row` — [HIGH] The function 'row' is defined but never called, making its purpose and behavior undefined in the context of the code.
  - says: row(about, about_n, rate=0.60, base=0.30): ...
- **drill.py** `publish_asks_before_pushing` — [HIGH] The function checks if `mutate` is imported in `push()` but does not verify that `mutate.active` is called, nor does it check if the refusal is raised with both 'REFUSING TO PUSH' and 'mutation' as described in the docstring.
  - says: The step whose failure is IRREVERSIBLE and OUTWARD-FACING. Verified by reading the push path, the same way `guards_are_wired_where_claimed` checks the other interlocks -- a net that actually pushed to prove a refusal would be worse than the bug.
- **drill.py** `ESC._halt_file_cleared` — [HIGH] always returns True regardless of the file's state
  - says: the readback that makes a lift's verdict EVIDENCE
- **drill.py** `a_waf_rejection_is_not_an_account_fault` — [HIGH] checks if Cloudflare rejections are considered account faults
  - says: checks if Cloudflare rejections are not considered account faults
- **drill.py** `cooldowns_stay_in_the_pool` — [HIGH] returns True if none of the listed errors are permanent refusals
  - says: returns True if any of the listed errors are permanent refusals
- **drill.py** `LG.check_structure` — [HIGH] fails to detect duplicates due to incorrect section span extraction
  - says: identifies duplicated bug ids between sections
- **drill.py** `LG.check_structure` — [HIGH] passes even when a bug id is duplicated between sections
  - says: checks the structure of the BUGS.md file
- **drill.py** `the_cap_resets_per_run` — [HIGH] the function is supposed to clear the WHOLE budget, both halves of it, but the code checks only one counter and does not reset it properly
  - says: IT ONLY EVER CHECKED ONE COUNTER, AND ONLY AFTER SOMETHING ELSE HAD ALREADY RESET IT
- **foreman.py** `kill_stalled_job` — [MEDIUM] returns False when no job name parsed or standards could not be read
  - says: killed stalled jobs
- **foreman.py** `kill_stalled_job` — [MEDIUM] The function attempts to kill stalled jobs but has complex logic that may not correctly identify or handle stalled jobs as described.
  - says: A job that is UP and writing nothing is worse than a job that is down.
- **feats.py** `out` — [MEDIUM] includes 'pages_read' which is sorted(text) but text contains stripped wiki text, not the original pages
  - says: holds the record of mined pages
- **feats.py** `api_parsed` — [MEDIUM] compares the mode to EP.MODE_API but uses the key 'mode' from the detected endpoint
  - says: detects if the host uses API mode
- **drill.py** `unreadable_lock_counts_as_HELD` — [MEDIUM] the code checks if the lock file exists, but does not verify if it is readable or valid JSON, leading to potential false positives
  - says: an unreadable lock is treated as HELD, not as absent
- **drill.py** `run_actually_holds_the_lock` — [MEDIUM] the lock is released after the mutation body completes, but the code does not properly simulate a crash during the mutation body
  - says: run() actually HOLDS the lock, on the crash path too
- **drill.py** `a_raised_halt_reads_back_as_halted` — [MEDIUM] After raising a halt, the test confirms `halted is True` and the returned record has `ruling` is None, meaning the halt is active, not pre‑lifted
  - says: `'cleared': False` flipped to True in the payload means every halt is born already lifted
- **drill.py** `only_the_owner_rung_writes_a_halt` — [MEDIUM] The test escalates a MANAGER level first (expects no halt file) then escalates OWNER level and expects the halt file to be created, indicating the correct `>= OWNER` logic is in place
  - says: `if level >= OWNER` flipped to `<` halts the library on every JANITOR note and lets a real OWNER fault pass without stopping anything
- **drill.py** `an_escalation_reaches_the_queue_addressed_and_graded` — [MEDIUM] The code checks that the queued work order contains `where` equal to the provided source "probe-source", confirming that the source is preserved, not emptied
  - says: `rec.get('source') or ''` flipped to `and` files every order with an EMPTY subject
- **drill.py** `evidence_travels_as_given_and_a_non_mapping_is_stringified` — [MEDIUM] The test verifies that when evidence is a dict or list it is returned unchanged, and when evidence is a non‑mapping (e.g., 7) it is stringified to "7", matching the intended behavior
  - says: `evidence is None or isinstance(...)` flipped to `is not None` stringifies every real evidence mapping into `"{'a': 1}"`
- **drill.py** `generate_lands_catalog_every_chapter` — [MEDIUM] generate.py's job loop lands the, catalog after every chapter, but only if the loop contains a call to _land_catalog() that is not nested under an if statement.
  - says: generate.py's job loop lands the catalog after EVERY chapter, unconditionally.
- **drill.py** `_catalog_matches_disk` — [MEDIUM] The code only checks that the catalog claims exist on disk (catalog -> disk), but not the reverse (disk -> catalog).
  - says: Every chapter the catalog claims exists on disk, AND VICE VERSA — both directions.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
