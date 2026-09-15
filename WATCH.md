# OVERWATCH

round 548  ·  last run 2026-09-15 18:17

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 305,503 inspected (deep scan as of round 547)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**24 open** (6 high). Newest first.

- **weave.py** `null_threshold` — [HIGH] Calculates a permutation null based on IDF weights, but the function is marked as superseded and not called anywhere
  - says: Permutation null: what pair weight arises purely by chance?
- **standards.py** `bool(refs) and inside >= len(refs)` — [HIGH] the condition is checking if inside is greater than or equal to the length of refs, but the comment indicates it should check if inside is greater than or equal to the scoreable count
  - says: the assay reading is valid
- **standards.py** `unans_files` — [HIGH] unans_files is initialized to 0 before the try block, and if any of the three unmeasurable cases occur (raise, unreadable file, missing/renamed data/readfeats), the except block is not triggered, and the zero is cached in _UNANS_CACHE for 120 seconds, resulting in no trace of the error
  - says: THIS ONE LEFT NO TRACE AT ALL (2026-08-28). `unans_files = 0` sat before the try and the only out.append sat after it, so a HIGH-severity evidence standard was emitted MET with an observed `0` in three separate unmeasurable cases
- **standards.py** `resident_context` — [HIGH] The context window served by the runner holding any model that matches the configured model name.
  - says: The context window served by the runner holding THIS project's model.
- **health.py** `F.api` — [HIGH] probe a host that may have been quarantined
  - says: probe a host we are actually still talking to
- **withdraw_chapters.py** `main` — [HIGH] Returns 1 if a.go is true and bad conditions are met, else 0. This contradicts the claim that it exits 0 unconditionally.
  - says: Every refusal above was printed and discarded. The tool should exit 0 unconditionally, including when catalog write was denied.
- **whoruns.py** `hits` — [MEDIUM] the result of the running function which may return None
  - says: count a same-named script running out of ANY tree
- **weave_index.py** `cacheable` — [MEDIUM] cacheable is set to True when records is None, but the code later uses it to determine whether to use the cached designation
  - says: cacheable = records is None
- **weave.py** `pair_weights` — [MEDIUM] Summed idf of everything each source-pair shares, but with no cap on the summed idf value, which may lead to over-weighting.
  - says: Summed idf of everything each source-pair shares.
- **tells.py** `prompt_in_sync` — [MEDIUM] Compares the generated block to the prompt file after replacing \r\n with \n
  - says: Compares the generated block to the prompt file
- **standards.py** `fab` — [MEDIUM] is set to None and used to determine the standard's status, but the logic is flawed
  - says: represents the fabrication rate
- **standards.py** `resident_context` — [MEDIUM] Now iterates through all rows and returns the first matching model's context length.
  - says: IT USED TO TAKE WHICHEVER ROW /api/ps LISTED FIRST
- **overnight.py** `blocking` — [MEDIUM] The variable 'blocking' is assigned the value of checking if the output contains the string 'FAIL  ' + _control_label, but the comment indicates that the original logic was based on two substrings from health.py's console output, which is now replaced by a label from health.CHECKS. The actual implementation uses a label from health.CHECKS, which may not match the original intended behavior.
  - says: The blocking condition is determined by checking if the output contains the exact string 'FAIL  ' + _control_label
- **manifest_builder.py** `silence.replace_retry` — [MEDIUM] The function is used to replace the temporary report file with the final path, but the comment suggests it's used for retrying operations, which may not be the intended use.
  - says: Land it through a pid+thread temp and silence.replace_retry, and report the verdict on the same footing as the manifest write instead of assuming it.
- **local_agent.py** `_spellings` — [MEDIUM] The code appends the lowercase version of the real path to the spellings list, which may not be correct for the denylist asking of both spellings of the path.
  - says: ASKED OF BOTH SPELLINGS OF THE PATH — BYPASS CLASS SEVEN
- **hosts.py** `discover` — [MEDIUM] probe alternative hosts for every source but does not keep all that hold
  - says: probe alternative hosts for every source and keep all that hold
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the reopen_stranded function returns a value that is None, else 0
  - says: return 1 if the reopen_stranded function returns None, else 0
- **worldseed.py** `to_options` — [MEDIUM] to_options is supposed to generate options for a worldseed, but the code uses it to append entries to the output list without further processing
  - says: to_options is supposed to generate options for a worldseed
- **workorders.py** `reroute` — [MEDIUM] move an order to a different rung
  - says: reroute an order
- **workorders.py** `filed.extend([])` — [MEDIUM] no-op standing where the close pass should have been
  - says: close the ones that recovered
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
