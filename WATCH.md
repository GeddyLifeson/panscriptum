# OVERWATCH

round 285  ·  last run 2026-09-02 17:27

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 289,770 inspected (deep scan as of round 283)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**9 open** (0 high). Newest first.

- **address_space.py** `HASH_BYTES` — [MEDIUM] Hardcoded to 16 bytes regardless of the offset calculation
  - says: Derived from the offsets, floored at the historical 16 bytes so today's addresses are unchanged.
- **build_terminal.py** `silence.replace_retry` — [MEDIUM] does NOT unlink tmp when it fails
  - says: THE VERDICT REACHES THE EXIT CODE, AND THE SCRATCH FILE GOES (order ca499449f966).
- **entity_match.py** `similarity` — [MEDIUM] Calculates similarity between base names but also uses the `difflib.SequenceMatcher.ratio` which is order-sensitive and contiguity-sensitive, contradicting the claim that qualifiers are not considered.
  - says: Base-name similarity in [0,1]. Qualifiers are NOT considered -- the gate handles those.
- **worldseed.py** `unreachable_by_url` — [MEDIUM] Returns a dictionary of opt items for keys that are not delivered via URL, but the function's name and comment suggest it's about what cannot be delivered via URL. However, the function's actual behavior is to return a subset of opt items, which is consistent with the claim. No defect of fact found.
  - says: What the profile derives that a query string cannot deliver. Named, not hidden.
- **worldseed.py** `seed_for` — [MEDIUM] Generates a 32-bit seed, but the hash is 64 characters long, and the first 8 hex digits are used, which is 32 bits. However, the function returns an integer, which can be up to 2^32 - 1, which is correct for a 32-bit seed.
  - says: 32-bit seed. Deterministic, so a world regenerates identically for anyone who has its row.
- **thread_integrity.py** `implied_threads` — [MEDIUM] implied_threads is called but its output is not used in the code slice provided
  - says: NAMED FOR WHAT IT COUNTS (order 30581ee9cca2). `implied_threads` adds both (a,b) and (b,a) for every shared entity, so this is DIRECTED and is exactly twice the deduped pair count `classify` reports two lines below -- the same population, printed twice, 2x apart, with nothing on the page saying so.
- **escalation.py** `clear` — [MEDIUM] clear() returns False for two different reasons, but the code treats them as the same event, leading to incorrect messages about the lift not happening.
  - says: PermissionError is caught alongside ValueError because `clear()` raises it for a non-person caller, and the two refusals are the same event to a reader: the lift did not happen and here is why.
- **cascade_bridge.py** `selftest` — [MEDIUM] executes the live check
  - says: The live check is NOT dropped
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
