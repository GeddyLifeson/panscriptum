# OVERWATCH

round 306  ·  last run 2026-09-03 09:38

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 291,426 inspected (deep scan as of round 301)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py
- NOT RUNNING: **0** read.py

## What the model found in the code

**21 open** (0 high). Newest first.

- **render.py** `view` — [MEDIUM] calls view() for the four FETCHED tiers, but the comment says that the loop only ever calls view() for the four FETCHED tiers -- four pure f-strings (galaxy_view / system_view / planet, no request made. However, the code actually calls view() for the four FETCHED tiers, which may involve making requests. The comment is misleading as it suggests no requests are made, but the code may actually make requests.
  - says: calls view() for the four FETCHED tiers -- four pure f-strings (galaxy_view / system_view / planet_view / burg_view), no request made
- **pick_model.py** `vram_measured` — [MEDIUM] is a boolean indicating whether _measured_vram was not None
  - says: carries the provenance to both places that need it: the printed budget (via _budget_note() below) and the residency gate itself
- **foreman.py** `reprove_pool` — [MEDIUM] corpus read finishes inside a day are not handled
  - says: corpus read finishes inside a day
- **foreman.py** `reprove_pool` — [MEDIUM] chunks nobody answered are not handled
  - says: chunks nobody answered
- **foreman.py** `reprove_pool` — [MEDIUM] corpus read is not progressing
  - says: corpus read is progressing
- **foreman.py** `reprove_pool` — [MEDIUM] buckets with headroom are not handled
  - says: buckets with headroom
- **foreman.py** `reprove_pool` — [MEDIUM] model calls per hour are not tracked
  - says: model calls per hour
- **foreman.py** `reprove_pool` — [MEDIUM] the library's counters are not moving
  - says: the library's counters are moving
- **workorders.py** `hits` — [MEDIUM] filters out suppressed findings but does not count or sample as described
  - says: Count, labelled sample, complete list in evidence
- **workorders.py** `scanned` — [MEDIUM] checks if the directory exists, not if the scan was run
  - says: gated on the scan having actually happened
- **workorders.py** `filed` — [MEDIUM] appends file orders for binding issues but the code is designed to close orders when hosts recover
  - says: appends file orders for binding issues
- **workorders.py** `filed` — [MEDIUM] is a list of orders to be filed and closed
  - says: is a list of orders to be filed
- **workorders.py** `_fire` — [MEDIUM] appends to `filed` and may close orders
  - says: raises an order for a problem
- **workorders.py** `allsweep` — [MEDIUM] re-derives the severity from the `failed` flag, not reading the precomputed grade
  - says: reads it rather than re-deriving it, because a second copy of the rule is how the two came to drift before
- **workorders.py** `allsweep` — [MEDIUM] only tracks imports, crashed/timed-out verifiers, and the graded ESTATE findings; lint and bad estate artifacts are not tracked
  - says: Tracks allsweep's own `bad` formula term for term -- imports, crashed/timed-out verifiers, lint, bad estate artifacts, and the graded ESTATE findings
- **weave.py** `write_json` — [MEDIUM] writes JSON to a file and returns a boolean indicating success
  - says: returns whether the rename LANDED
- **snapshot.py** `restore` — [MEDIUM] Copies a snapshot back into a given directory, but returns the number of paths restored, and raises SnapshotFailed if any of the manifest's `took` entries could not be copied back. However, the function does not handle the case where the `into` directory is not writable or does not exist, which could lead to errors not being properly handled.
  - says: Copy a snapshot back. `into` defaults to the live tree -- pass a temp dir to test it. -> the number of paths restored. RAISES SnapshotFailed if any of the manifest's `took` entries could not be copied back -- it does not silently return fewer than it promised.
- **dashboard.py** `safety` — [MEDIUM] The function reads data from `state/drill_last.json` and calculates the age of the data, which aligns with the claim. However, the code does not explicitly state that the age is crucial for distinguishing between current and past data states.
  - says: The drill writes `state/drill_last.json` when it runs and this reports what it found and HOW OLD that is -- an age is not decoration here, it is the difference between "57 nets held" and "57 nets held, at some point, possibly before the change you are looking at".
- **address.py** `_index_name_is_placed_like_a_title` — [MEDIUM] The function checks if the index name is placed like a title, but the logic is flawed in how it handles pluralization and partial matches, leading to incorrect categorization of vocabulary vs title evidence.
  - says: The index entry sits inside the target: is it there as the title, or as vocabulary?
- **escalation.py** `clear` — [MEDIUM] clear() returns False for two different reasons, but the code treats them as the same event, leading to incorrect messages about the lift not happening.
  - says: PermissionError is caught alongside ValueError because `clear()` raises it for a non-person caller, and the two refusals are the same event to a reader: the lift did not happen and here is why.
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
