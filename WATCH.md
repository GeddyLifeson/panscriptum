# OVERWATCH

round 292  ·  last run 2026-09-02 21:18

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 289,998 inspected (deep scan as of round 289)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py
- NOT RUNNING: **0** read.py

## What the model found in the code

**9 open** (0 high). Newest first.

- **cascade_bridge.py** `key` — [MEDIUM] text is stored verbatim but key is folded (lowercase) for deduplication
  - says: folding here cannot hide anything: `text` -- the thing a person reads and classifies -- is stored verbatim
- **cascade_bridge.py** `key` — [MEDIUM] the key is derived from bucket and text.lower()
  - says: the key is derived from bucket and text
- **cascade_bridge.py** `client_rejection` — [MEDIUM] It is used in a condition to skip entries where the `v` string matches either `local_transport` or `client_rejection`.
  - says: A FAULT ON THIS MACHINE IS NOT EVIDENCE ABOUT A PROVIDER'S ACCOUNT, and now that the provider's raw text reaches this line, it can arrive carrying one.
- **cascade_bridge.py** `local_transport` — [MEDIUM] It is used in a condition to skip entries where the `v` string matches either `local_transport` or `client_rejection`.
  - says: A FAULT ON THIS MACHINE IS NOT EVIDENCE ABOUT A PROVIDER'S ACCOUNT, and now that the provider's raw text reaches this line, it can arrive carrying one.
- **axis_correlation.py** `mean_str` — [MEDIUM] formatted as a float with 4 decimal places if doc['mean_r'] is not None, else 'n/a (no pair reached MIN_N)'
  - says: formatted as a float with 4 decimal places or 'n/a (no pair reached MIN_N)'
- **address.py** `_index_name_is_placed_like_a_title` — [MEDIUM] The function checks if the index name is placed like a title, but the logic is flawed in how it handles pluralization and partial matches, leading to incorrect categorization of vocabulary vs title evidence.
  - says: The index entry sits inside the target: is it there as the title, or as vocabulary?
- **escalation.py** `clear` — [MEDIUM] clear() returns False for two different reasons, but the code treats them as the same event, leading to incorrect messages about the lift not happening.
  - says: PermissionError is caught alongside ValueError because `clear()` raises it for a non-person caller, and the two refusals are the same event to a reader: the lift did not happen and here is why.
- **cascade_bridge.py** `selftest` — [MEDIUM] executes the live check
  - says: The live check is NOT dropped
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
