# OVERWATCH

round 386  ·  last run 2026-09-06 00:54

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 296,661 inspected (deep scan as of round 385)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**21 open** (6 high). Newest first.

- **drill.py** `R.hodge_decompose` — [HIGH] returns a result that does not match the expected values for a pure ladder
  - says: A pure ladder measures as 100% ladder
- **drill.py** `generator_actually_skips_an_excluded_source` — [HIGH] the function checks if exclusions are filtered but does not verify they are skipped
  - says: The manifest builder must consult `roll`, not just read the file.
- **drill.py** `drill_scope` — [HIGH] the function checks if excluded sources have reasons but does not enforce exclusion
  - says: An owner exclusion must actually exclude — the status that did nothing for five days.
- **drill.py** `drill_does_not_halt_during_a_mutation_run` — [HIGH] the function returns False when a breach is detected, which raises an OWNER halt
  - says: a breach during a mutation run is reported but does not halt the library
- **drill.py** `paid_access_stays_switched_off` — [HIGH] returns True when the config file is absent, which could allow paid access even if the owner hasn't explicitly set it
  - says: allow_paid is owner-held. Nothing automatic may switch it on.
- **drill.py** `catalog_matches_disk` — [HIGH] Only checks that the catalog claims exist on disk (catalog -> disk), but not the reverse (disk -> catalog)
  - says: Every chapter the catalog claims exists on disk, AND VICE VERSA — both directions.
- **drill.py** `coverage_totals_never_exceed_their_entry_count` — [MEDIUM] checks that the sum of certain fields does not exceed the total entries
  - says: states that sum past the total mean an entry counted twice -- the M23 shape
- **drill.py** `if not any(isinstance(b, ast.Raise) for b in _live_stmt_walk(_live_stmts(n.body)))` — [MEDIUM] Check for a raise in the handler's body, but the code does not verify that the raise is reachable
  - says: Ensure that a raise is present in the handler
- **drill.py** `return all(_reaches_call(tree, want, entries) for want, entries in (` — [MEDIUM] Check that three guards are callable from their entry points, but the code does not verify that they are actually called
  - says: Check that three guards are reachable from their entry points
- **dashboard.py** `state` — [MEDIUM] imports and uses the standards module, but the code does not show how it is used in the returned dictionary
  - says: returns a dictionary with state information
- **dashboard.py** `silence.write_json` — [MEDIUM] the write is attempted regardless of whether it succeeds, and the function returns [] on failure
  - says: this server is threaded (daemon_threads=True) and every /api/state poll runs this function, so two concurrent pollers on a fixed temp name collide on the temp file itself. The PID+thread-qualified tmp name write_json uses closes that race.
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
- **entity_match.py** `qualifier_compatible` — [MEDIUM] Returns True if both qualifiers are None or their normalized forms are equal, but does not handle cases where one qualifier is None and the other is not.
  - says: Two names may only be compared if their qualifiers agree.
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
