# OVERWATCH

round 489  ·  last run 2026-09-10 18:49

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 303,086 inspected (deep scan as of round 487)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**25 open** (6 high). Newest first.

- **onomast.py** `well_formed` — [HIGH] Implements seven constraints but the docstring claims four, and three of the four original constraints are misattributed
  - says: Is this a name a Custos could say aloud and write down twice the same way?
- **ledger_guard.py** `silence.note` — [HIGH] discards the reason a SEAL failed
  - says: TAGGED, like every sibling except-block in this file
- **foreman.py** `lines_changed` — [HIGH] Calculates the number of lines changed based on the diff between old and new code, but the docstring says it's not `abs(len(new) - len(old))` and instead explains a different method. However, the code correctly implements the described logic using difflib's SequenceMatcher. The docstring's claim is accurate, and the code aligns with it. Therefore, no defect of fact is found here.
  - says: How many lines a rewrite actually touches.
- **foreman.py** `kill_stalled_job` — [HIGH] kills stalled jobs that cannot be restarted, which is against the stated policy
  - says: A job that is UP and writing nothing is worse than a job that is down.
- **estate.py** `external` — [HIGH] The function is named 'external' but the code inside it is not related to external dependencies, but rather to checking the status of Ollama, Cascade, and disk space.
  - says: The dependencies that live outside this project and can fail without it changing.
- **silence.py** `append_line` — [HIGH] Appends a line but does not handle the Windows-specific issues with O_APPEND and text mode, leading to potential data corruption and line tearing.
  - says: Append ONE line to a shared ledger without tearing it (m62).
- **pick_model.py** `vram_gb` — [MEDIUM] 0.0GB VRAM currently free
  - says: 0.0GB VRAM currently free
- **manifest_builder.py** `silence.replace_retry` — [MEDIUM] is used to replace the temporary report file with the final report path, but the comment suggests it's meant to handle the report writing process including retries and error handling
  - says: Land it through a pid+thread temp and silence.replace_retry
- **ledger.py** `from_standards` — [MEDIUM] The inverse of `to_standards`, but returns None for unlisted currencies, not handling the case where a currency is deliberately non-convertible as per the docstring
  - says: The inverse of `to_standards`. None where the currency is not convertible -- for UNLISTED vs. deliberately non-convertible, see `currency_status`.
- **ledger.py** `to_standards` — [MEDIUM] Converts a local sum into Standards, but returns None for unlisted currencies, not handling the case where a currency is deliberately non-convertible as per the docstring
  - says: Convert a local sum into Standards. None where the currency is not convertible -- for UNLISTED vs. deliberately non-convertible, see `currency_status`.
- **hostcheck.py** `score` — [MEDIUM] Calculates a score based on probe results and baseline, but the code's logic for handling unmeasured controls and defaults may not align with the stated purpose of measuring lift above baseline.
  - says: One host, fully judged: how much of this roster it holds, ABOVE ITS OWN BASELINE.
- **hostcheck.py** `rate` — [MEDIUM] rate is assigned the value of r.get("rate") which could be None, but the code does not explicitly handle the None case as described in the comment
  - says: A CONTROL THAT DID NOT MEASURE IS `None`, NOT ZERO
- **generate.py** `call_ollama` — [MEDIUM] call_ollama is used to generate text based on prompts, but the code does not handle the case where the generated text is empty or contains missing entries properly
  - says: call_ollama is used to generate text based on prompts
- **foreman.py** `_contracts_pass` — [MEDIUM] Returns a tuple indicating success or failure of the contracts pass
  - says: Everything that must still be true after a patch.
- **foreman.py** `restart_reader` — [MEDIUM] The function is supposed to determine if a reader can be restarted, but it's actually enumerating processes and returning False or a message if it can't, without checking if the reader is actually restartable.
  - says: The reader is not progressing. Restarting is safe: every entity is cached only when it was fully read, so nothing is lost and nothing is re-read that was finished.
- **foreman.py** `reprove_pool` — [MEDIUM] returns False when the proof is not written
  - says: This returned True whenever the proof was written
- **estate.py** `inspect` — [MEDIUM] The function does not open or parse the file content; it only checks the file size and handles errors related to file access.
  - says: WHAT IS OPENED, exactly, because the header used to promise more than this performed: ...
- **estate.py** `inspect` — [MEDIUM] The function attempts to read file sizes and handle errors but does not actually open or parse the file content as described.
  - says: One file, opened and actually read where its type can be parsed. Size is a hint.
- **derivation.py** `main` — [MEDIUM] returns 1 if problems exist, 0 if the ledger closes
  - says: returns 0 if the ledger closes, 1 otherwise
- **derivation.py** `college_size` — [MEDIUM] the count is derived, not chosen: a direction with nobody
  - says: one Custos per degree of freedom
- **anchors.py** `vector_score` — [MEDIUM] Returns a value based on the LADDER_RUNGS constant, which is 17, but the comment says it's derived from the Ladder's own height. The function uses a fixed value for LADDER_RUNGS, which may not be correct if the ladder's actual height differs.
  - says: Vector on the 0-10 decimal scale, derived from the Ladder's own height. No new quantity.
- **thread_integrity.py** `dist` — [MEDIUM] initialized to None but not properly calculated or handled in all cases
  - says: distance for propagation calculation
- **thread_integrity.py** `detail` — [MEDIUM] appends tuples to the detail dictionary for various categories but may not be correctly structured as per the comments
  - says: stores detailed information about each category
- **thread_integrity.py** `out` — [MEDIUM] increments the count for partially dangling pairs but also for other categories like IMPLIED-UNRECORDED and RECIPROCAL
  - says: counts the number of partially dangling pairs
- **verify_math.py** `max` — [MEDIUM] the tolerance is silently discarded as the code compares integers exactly
  - says: the k-th burg holds P1/k, independently recomputed

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
