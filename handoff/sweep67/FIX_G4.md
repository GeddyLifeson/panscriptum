# FIX G4 (run #67)

| order | verdict | how | net |
|---|---|---|---|
| 05576868dd8f | FIXED | codewatch `_ledger_lock` and `_claim_restart_slot` docstrings now name `_take_locked` as the live writer; `_record_restart` docstring says it is a kept test entry | comment-only |
| 9bd9d77d5e0d | FIXED | completeness.land: only FileNotFoundError is silent; a torn prior notes and says the floor was not applied; any other read fault notes and refuses the write | nets/9bd9d77d5e0d.py |
| 92b6168fdd74 | FIXED | corpus_db.rebuild: a duplicate source sums entries into the existing row and is named in unreadable_records / meta | nets/92b6168fdd74.py |
| ee9365750ddf | FIXED | coverage.measure: retries records() 4x; if a record that parses with entries (or fails to parse) is absent from the result, SystemExit | nets/ee9365750ddf.py |
| 9cc87ededee1 | FIXED | ingest_doc.extract: prints textless page count; raises OSError (existing refusal) before any write when nothing extracted | nets/9cc87ededee1.py |
| 273bd193d454 | FIXED | sweep.sweep: SystemExit when WIKI_HOSTS.json absent or empty; stderr warning when ROSETTA/NAVTREE empty | nets/273bd193d454.py |
| 2a0dd1d54ff6 | FIXED | sweep_plan.main: `if a.batches and not a.check_briefs`, so the diff branch runs with N | nets/2a0dd1d54ff6.py |
| 939cb74c818a | FIXED | sweep_plan.unknown_claims: `import silence` once at function top, local imports removed | nets/939cb74c818a.py |

All nets print True on fixed code and False with their `_revert.json` applied (checked in a scratch copy of src/). pyflakes clean and import OK on all seven modules.

Notes: ingest_doc.py is CRLF; revert JSON `old` text is LF (text-mode read), like the other modules. Design choice on 9bd9d77d5e0d: a torn (unparseable) prior proceeds with a loud "floor NOT applied" message rather than refusing forever, since a corrupt file holds nothing to protect; a permission/other read fault refuses.
