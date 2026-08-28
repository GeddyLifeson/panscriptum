# OVERWATCH

round 109  ·  last run 2026-08-27 23:41

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 267,074 inspected  — handoff\run36\sweep_plan.json — malformed JSON: Extra data: line 213 column 1 (char 3102)
- catalogued sources with no host: **9** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major
- NOT RUNNING: **0** publish.py
- NOT RUNNING: **0** pipeline.py
- NOT RUNNING: **0** feats.py --roll

## What the model found in the code

**12 open** (4 high). Newest first.

- **address_space.py** `pack` — [HIGH] pack is called with keyword arguments, but the code is using positional arguments for the fields, which may not match the expected parameters
  - says: BY KEYWORD, ALWAYS. This demo was written when the address had five fields and was never updated when xenoverse, metaverse and multiverse were added -- so `pack
- **pipeline.py** `phase_cosmology` — [HIGH] does not run any of the described modules
  - says: chart the tiers, and answer the First Argument per cosmos.
- **pipeline.py** `phase_chain` — [HIGH] A function that does not implement phase 4 logic but instead serves as a placeholder that stops the runner cleanly when phase 4 is reached
  - says: Phase 4 -- the Chain of Defeats. See chain.py for the reasoning.
- **pipeline.py** `gate_done` — [HIGH] Marks a phase done even if some artifacts did not land, because the condition is incorrect
  - says: Mark a phase done ONLY if every artifact it wrote actually landed.
- **backfill.py** `write_record_catalogue` — [MEDIUM] returns whether the rename was successful
  - says: returns whether the rename LANDED
- **backfill.py** `lead` — [MEDIUM] returns a substring of the input text without checking for a terminal punctuation
  - says: extracts a lead sentence from a block of text
- **axis_correlation.py** `main` — [MEDIUM] returns 0 unconditionally
  - says: returns 0 on success
- **assay.py** `denom` — [MEDIUM] sum of weights over applicable axes or 1.0 if empty
  - says: sum of weights over applicable axes
- **address_space.py** `shelfmark` — [MEDIUM] The function prints H and X as the charted integers they now are, but the docstring incorrectly stated that it claimed H and X print as '?'
  - says: The charter's own notation, with H and X printed as the charted integers they now are.
- **profile.py** `encode` — [MEDIUM] the code says it does
  - says: the code says it does
- **pipeline.py** `batch_settled` — [MEDIUM] The function batch_settled is called with key, done_keys, and batch, but the code does not actually check if the batch is closed or if entries have been added after the batch was c
  - says: A CLOSED BATCH IS NOT A CLOSED SPAN. The resume key is `source#start`, but the span it names is `entries[start:start+B]` -- and a record's entry list GROWS afte
- **pipeline.py** `write_record_catalogue` — [MEDIUM] write_record_catalogue is the catalogue's side of the two-writer contract
  - says: write_record_catalogue below is the pipeline's.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
