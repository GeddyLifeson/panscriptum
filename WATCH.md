# OVERWATCH

round 385  ·  last run 2026-09-06 00:21

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 296,661 inspected
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**14 open** (2 high). Newest first.

- **corpus_db.py** `code` — [HIGH] code is set to None if the resolver returns 'UNASSIGNED', which is then replaced with None, but the code is also set to SPINE_LOOKUP_FAILED when the resolver is unavailable or raises an exception. This leads to incorrect state representation for unshelved sources.
  - says: RESOLVED, UNASSIGNED, OR NEVER ASKED -- THREE STATES, AND TWO OF THEM USED TO SHARE A SPELLING. `code = None` was initialised, the resolver was called inside a try/except that only `silence.note()`d, and the next line's comment stated the contract the except clause then broke: NULL means unshelved, and only the resolver may say so. On any exception NULL was written anyway. That matters far more than one row, because `address._load_spine_codes()` raises OUTRIGHT if data/CHARTER_SPINE_CODES.json is missing or unparseable, and `import address` still succeeds -- so `_spine_for` is truthy, the guard above catches nothing, and one unreadable data file makes ALL 216 sources report as unshelved. The `unaddressed` canned query and the Datasette page then present a whole-roll curatorial backlog, which is exactly the misreading this module's header spends fifteen lines on and nearly acted on once already. The only trace was a note. Now the failure gets its own value, is counted into `meta`, and is reported by the rebuild -- so the index can say "I could not ask" instead of answering for the resolver. (order 25266fa8c2dc)
- **autostart.py** `ON.running` — [HIGH] leans on truthiness
  - says: callers "test `is None` explicitly rather than leaning on truthiness"
- **completeness.py** `work` — [MEDIUM] A HOST THAT IS DOWN STILL GETS A ROW. Asking the domain once and emitting an honest `unreliable` row costs one socket call; probing it 8 times per source costs ~17 minutes per source under a block and produces the identical conclusion. The row matters: a source missing from COMPLETENESS.json reads downstream as "nothing on the wiki", which is the opposite of "we could not ask", and a file that loses every fandom source during an outage is the empty-file catastrophe of 2026-08-24 wearing a smaller hat.
  - says: A HOST THAT IS DOWN STILL GETS A ROW. Asking the domain once and emitting an honest `unreliable` row costs one socket call; probing it 8 times per source costs ~17 minutes per source under a block and produces the identical conclusion. The row matters: a source missing from COMPLETENESS.json reads downstream as "nothing on the wiki", which is the opposite of "we could not ask", and a file that loses every fandom source during an outage is the empty-file catastrophe of 2026-08-30 wearing a smaller hat.
- **cleanup.py** `ceil_fixed` — [MEDIUM] appends tuples with the original ceiling and fixed value
  - says: ceiling entities reduced to a name
- **cleanup.py** `clean_ceiling` — [MEDIUM] cuts the ceiling prose at 70 and 52 characters with no marker
  - says: the per-name character cuts in the same statements go with them
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
- **entity_match.py** `qualifier_compatible` — [MEDIUM] Returns True if both qualifiers are None or their normalized forms are equal, but does not handle cases where one qualifier is None and the other is not.
  - says: Two names may only be compared if their qualifiers agree.
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
