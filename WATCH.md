# OVERWATCH

round 359  ·  last run 2026-09-05 03:38

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 295,231 inspected (deep scan as of round 355)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py
- NOT RUNNING: **0** read.py

## What the model found in the code

**11 open** (3 high). Newest first.

- **catalogue_codex.py** `main` — [HIGH] returns 0 when roll_landed is False and denied is False
  - says: return 1 on a denied write
- **foreman.py** `rate` — [HIGH] rate is the count of sources with gap[s] >= CATALOGUE_SHORTFALL, which is a hard filter, not a rate
  - says: rate is derived from the same audit each round, so the rate tracks whatever the old behaviour would have done while the MEMBERSHIP rotates underneath it.
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [HIGH] The code returns 1 if the result is None, else 0, which is the opposite of what the comment says it does. The comment states that the return value should be used to determine the exit code, but the code inverts this logic.
  - says: THE VERDICT IS THE EXIT CODE (sweep42-batch10). This discarded `reopen_stranded()`'s return value and returned 0 unconditionally, so a repair that could not read or write PIPELINE_STATE.json reported success to whatever ran it -- the check-that-cannot-fail shape, on a repair. It is invoked from scripts, which have nothing else to read.
- **cascade_bridge.py** `text` — [MEDIUM] the text is truncated to 300 characters and split into words before being stored
  - says: the text is stored verbatim
- **cascade_bridge.py** `key` — [MEDIUM] the key is derived from the bucket and the text lowercased, but the text is not stored verbatim
  - says: the key is derived from the bucket and the text
- **workorders.py** `resolve_code` — [MEDIUM] is used in a context where it's supposed to close orders but may not be called correctly
  - says: resolves a code to a resolution
- **workorders.py** `is_selftest` — [MEDIUM] checks if the order was FILED as one or CLOSED as one, but the code uses it to determine if the order is a real blast-cap order closed by anybody else
  - says: a self-test if it was FILED as one or CLOSED as one
- **entity_match.py** `qualifier_compatible` — [MEDIUM] Returns True if both qualifiers are None or their normalized forms are equal, but does not handle cases where one qualifier is None and the other is not.
  - says: Two names may only be compared if their qualifiers agree.
- **dashboard.py** `safety` — [MEDIUM] The function reads data from `state/drill_last.json` and calculates the age of the data, which aligns with the claim. However, the code does not explicitly state that the age is crucial for distinguishing between current and past data states.
  - says: The drill writes `state/drill_last.json` when it runs and this reports what it found and HOW OLD that is -- an age is not decoration here, it is the difference between "57 nets held" and "57 nets held, at some point, possibly before the change you are looking at".
- **address.py** `_index_name_is_placed_like_a_title` — [MEDIUM] The function checks if the index name is placed like a title, but the logic is flawed in how it handles pluralization and partial matches, leading to incorrect categorization of vocabulary vs title evidence.
  - says: The index entry sits inside the target: is it there as the title, or as vocabulary?
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
