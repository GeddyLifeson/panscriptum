# OVERWATCH

round 318  ·  last run 2026-09-03 18:49

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 292,446 inspected (deep scan as of round 313)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**12 open** (3 high). Newest first.

- **feats.py** `roll` — [HIGH] the return value is discarded and 0 is returned unconditionally
  - says: THE COUNTERS REACH THE EXIT CODE
- **feats.py** `_QUANTITY` — [HIGH] fails to capture mantissa value when exponent is present
  - says: extracts physical quantities
- **feats.py** `_QUANTITY` — [HIGH] captures exponent but discards mantissa value
  - says: extracts physical quantities
- **endpoint.py** `one` — [MEDIUM] returns None for HTTP errors and HTML bodies, but not for other failures
  - says: fetch raw content from a URL and return it if successful
- **compress_store.py** `load` — [MEDIUM] Reads a stored blob back, decompresses it, and checks the filename against the content hash of the decompressed text, but does not verify that the decompressed text matches the content hash of the original text before compression.
  - says: Read a stored blob back, VERIFYING it against the address it is filed under.
- **entity_match.py** `qualifier_compatible` — [MEDIUM] Returns True if both qualifiers are None or their normalized forms are equal, but does not handle cases where one qualifier is None and the other is not.
  - says: Two names may only be compared if their qualifiers agree.
- **catalogue_aurora.py** `update_rows` — [MEDIUM] the function is called and its return value is checked, but the error message is printed and the script exits with 1 if there's a refusal
  - says: this whole function exists to argue that a write verdict must never be discarded, and this was the one call in it that still did
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
