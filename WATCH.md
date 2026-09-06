# OVERWATCH

round 387  ·  last run 2026-09-06 03:11

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 296,661 inspected (deep scan as of round 385)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**25 open** (11 high). Newest first.

- **feats.py** `wiki_source` — [HIGH] Used to gate the expensive `strip_wikitext` call, but the logic is inverted
  - says: The CHEAP GATE IN FRONT OF THE EXPENSIVE ONE. A block page, a soft-404 or a rate-limit interstitial is a real document that mines to zero feats, and "zero feats" is indistinguishable from an honest absence once it is written to the cache.
- **feats.py** `wiki_source` — [HIGH] Recomputed here, not answered by `reads_as_wiki`
  - says: Answered by `reads_as_wiki` rather than recomputed here, so the cache-staleness check above and this mining path can never disagree about what kind of corpus a host is.
- **estate.py** `note` — [HIGH] appends a finding to, but the code in the comment says it should append nothing
  - says: appends a finding to the report
- **estate.py** `note` — [HIGH] appends a finding to the report
  - says: appends a finding to the report
- **escalation.py** `landed, why` — [HIGH] A variable that is used but never defined in this file or its imports
  - says: One compare-and-swapped attempt at lifting the halt. -> (landed, why).
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
- **health.py** `reopen_stranded` — [MEDIUM] return value is used to determine exit code, but the code does not handle the case where it returns None
  - says: THE VERDICT IS THE EXIT CODE (sweep42-batch10). This discarded `reopen_stranded()`'s return value and returned 0 unconditionally, so a repair that could not read or write PIPELINE_STATE.json reported success to whatever ran it -- the check-that-cannot-fail shape, on a repair.
- **health.py** `silence.write_json` — [MEDIUM] is called and the return value is checked, but the code does not handle the case where it returns False
  - says: RETURNS False rather than raising when the atomic replace is denied
- **feats.py** `_QUANTITY` — [MEDIUM] does not capture the exponent part of a quantity
  - says: captures the exponent part of a quantity
- **escalation.py** `escalate` — [MEDIUM] escalate is not called here and the code does not handle its exceptions
  - says: escalate(...)
- **escalation.py** `clear` — [MEDIUM] clear() is not called here and the code does not handle its exceptions
  - says: clear() raises it for a non-person caller
- **escalation.py** `why` — [MEDIUM] being initialized to 'not attempted' and then overwritten in the loop, but the loop may not have run at all
  - says: tracking the reason for failure
- **escalation.py** `landed` — [MEDIUM] being set to False after the loop, but the loop may not have run at all
  - says: tracking whether the halt was successfully landed
- **drill.py** `coverage_totals_never_exceed_their_entry_count` — [MEDIUM] checks that the sum of certain fields does not exceed the total entries
  - says: states that sum past the total mean an entry counted twice -- the M23 shape
- **drill.py** `if not any(isinstance(b, ast.Raise) for b in _live_stmt_walk(_live_stmts(n.body)))` — [MEDIUM] Check for a raise in the handler's body, but the code does not verify that the raise is reachable
  - says: Ensure that a raise is present in the handler
- **drill.py** `return all(_reaches_call(tree, want, entries) for want, entries in (` — [MEDIUM] Check that three guards are callable from their entry points, but the code does not verify that they are actually called
  - says: Check that three guards are reachable from their entry points
- **dashboard.py** `silence.write_json` — [MEDIUM] the write is attempted regardless of whether it succeeds, and the function returns [] on failure
  - says: this server is threaded (daemon_threads=True) and every /api/state poll runs this function, so two concurrent pollers on a fixed temp name collide on the temp file itself. The PID+thread-qualified tmp name write_json uses closes that race.
- **completeness.py** `work` — [MEDIUM] A HOST THAT IS DOWN STILL GETS A ROW. Asking the domain once and emitting an honest `unreliable` row costs one socket call; probing it 8 times per source costs ~17 minutes per source under a block and produces the identical conclusion. The row matters: a source missing from COMPLETENESS.json reads downstream as "nothing on the wiki", which is the opposite of "we could not ask", and a file that loses every fandom source during an outage is the empty-file catastrophe of 2026-08-24 wearing a smaller hat.
  - says: A HOST THAT IS DOWN STILL GETS A ROW. Asking the domain once and emitting an honest `unreliable` row costs one socket call; probing it 8 times per source costs ~17 minutes per source under a block and produces the identical conclusion. The row matters: a source missing from COMPLETENESS.json reads downstream as "nothing on the wiki", which is the opposite of "we could not ask", and a file that loses every fandom source during an outage is the empty-file catastrophe of 2026-08-30 wearing a smaller hat.
- **entity_match.py** `qualifier_compatible` — [MEDIUM] Returns True if both qualifiers are None or their normalized forms are equal, but does not handle cases where one qualifier is None and the other is not.
  - says: Two names may only be compared if their qualifiers agree.
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
