# OVERWATCH

round 384  ·  last run 2026-09-05 23:27

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 296,341 inspected (deep scan as of round 379)  — state\gpu_lane\slot.0.json — cannot stat
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**14 open** (4 high). Newest first.

- **autostart.py** `ON.running` — [HIGH] leans on truthiness
  - says: callers "test `is None` explicitly rather than leaning on truthiness"
- **assay.py** `instrument` — [HIGH] Raises ValueError if anchor is not in INSTRUMENT_WINDOWS, which may not be the same as LADDER
  - says: Deterministic conversion to the six faculties, 1-30, plus Transcendence Grade.
- **address_space.py** `assign` — [HIGH] assign(desig, tiers.get(src) or {}) with wrong second argument
  - says: assign(desig, tiers.get(src) or {})
- **address_space.py** `pack` — [HIGH] pack(**fields) with fields having wrong keys
  - says: pack(3, 11, ...)
- **cascade_bridge.py** `record_unrecognised` — [MEDIUM] The key is folded by lowercasing the text, which may cause different errors with the same folded text to be merged, potentially losing case sensitivity information.
  - says: Keyed by bucket + the error's leading text so a provider repeating one fault stays one row with a count rather than flooding the file.
- **cascade_bridge.py** `record_unrecognised` — [MEDIUM] Attempts to write down a pool failure but may overwrite existing entries due to the re-derivation logic and the compare-and-swap mechanism which is not atomic.
  - says: Write down a pool failure that matched no known disposition, so it can be investigated.
- **canon_backup.py** `restore` — [MEDIUM] Attempts to restore a file by extracting it from a snapshot and replacing the destination file, but the code's comment and docstring indicate it should handle restoration with atomic operations and error handling.
  - says: Extract ONE canonical file from a snapshot. -> written path.
- **canon_backup.py** `final` — [MEDIUM] the final name includes the stamp which includes seconds, leading to sorted order
  - says: THE NAMING CONVENTION STILL SORTS
- **canon_backup.py** `stamp` — [MEDIUM] used to generate a unique filename by combining with PID and thread ID
  - says: a second-resolution stamp is not a disambiguator
- **autostart.py** `watch` — [MEDIUM] Exits if another watchdog is running, but does not handle staleness or budgeting as described
  - says: Keep the supervisor alive. The one thing it cannot do for itself.
- **audit.py** `audit_invariants` — [MEDIUM] audit_invariants is called with recs, but the function is not defined in the provided code slice
  - says: audit_invariants is called with recs
- **allsweep.py** `bad` — [MEDIUM] sum of various counts including ungraded reconcile rows
  - says: count of bad subsystems
- **entity_match.py** `qualifier_compatible` — [MEDIUM] Returns True if both qualifiers are None or their normalized forms are equal, but does not handle cases where one qualifier is None and the other is not.
  - says: Two names may only be compared if their qualifiers agree.
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
