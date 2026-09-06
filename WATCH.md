# OVERWATCH

round 383  ·  last run 2026-09-05 22:35

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 296,341 inspected (deep scan as of round 379)  — state\gpu_lane\slot.0.json — cannot stat
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**10 open** (4 high). Newest first.

- **assay.py** `instrument` — [HIGH] Raises ValueError if anchor is not in INSTRUMENT_WINDOWS, which may not be the same as LADDER
  - says: Deterministic conversion to the six faculties, 1-30, plus Transcendence Grade.
- **address_space.py** `assign` — [HIGH] assign(desig, tiers.get(src) or {}) with wrong second argument
  - says: assign(desig, tiers.get(src) or {})
- **address_space.py** `pack` — [HIGH] pack(**fields) with fields having wrong keys
  - says: pack(3, 11, ...)
- **address_space.py** `FIELDS` — [HIGH] hyperverse and xenoverse ARE fields with computed widths counting toward TOTAL_BITS
  - says: hyperverse and xenoverse are NOT fields ... reserving bits for them would invite filling them in
- **allsweep.py** `bad` — [MEDIUM] sum of various counts including ungraded reconcile rows
  - says: count of bad subsystems
- **address_space.py** `drawn` — [MEDIUM] drawn field from the digest, but the comment says it's a hash draw and the code contradicts the comment
  - says: drawn field from the digest
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
