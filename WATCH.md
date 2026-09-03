# OVERWATCH

round 308  ·  last run 2026-09-03 10:52

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 292,042 inspected (deep scan as of round 307)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py
- NOT RUNNING: **0** read.py

## What the model found in the code

**20 open** (5 high). Newest first.

- **withdraw_chapters.py** `shutil.move` — [HIGH] A failed move may overwrite existing files in the archive
  - says: A failed move keeps its record
- **standards.py** `_dup` — [HIGH] a variable that is not appended to the out list
  - says: one instance of each job
- **standards.py** `errs` — [HIGH] sum of all calls minus successful ones
  - says: sum of failed calls
- **standards.py** `calls` — [HIGH] sum of all calls minus successful ones
  - says: sum of successful calls
- **silence.py** `audit` — [HIGH] undefined
  - says: audit
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
- **workorders.py** `_fire` — [MEDIUM] appends to `filed` and may close orders
  - says: raises an order for a problem
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
