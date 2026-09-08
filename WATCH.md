# OVERWATCH

round 430  ·  last run 2026-09-07 20:49

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 299,328 inspected (deep scan as of round 427)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**4 open** (1 high). Newest first.

- **onomast.py** `well_formed` — [HIGH] Implements seven constraints, but the docstring claims it was meant to implement four with three added later, and the docstring's summary undercounts the function by three
  - says: Is this a name a Custos could say aloud and write down twice the same way?
- **onomast.py** `merged` — [MEDIUM] overwrites records from prior with out
  - says: APPEND-ONLY. Carried-forward records first...
- **cascade_bridge.py** `reason` — [MEDIUM] The `reason` variable is assigned values like 'model disabled in config' and 'the serving model ... could not be mapped to a bucket', but the comment suggests it should carry the provider's own disposition from `served[
  - says: reason puts it in the file
- **cascade_bridge.py** `verdict` — [MEDIUM] The `verdict` variable is assigned values like 'answers' and 'no answer', which are part of the old vocabulary, but the code also assigns it values like 'model disabled' and 'no API key / provider disabled', which are not part of the original vocabulary described in the docstring.
  - says: verdict keeps its exact old vocabulary

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
