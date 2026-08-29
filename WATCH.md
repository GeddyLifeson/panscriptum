# OVERWATCH

round 157  ·  last run 2026-08-29 12:17

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **0** of 273,738 inspected
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**3 open** (2 high). Newest first.

- **endpoint.py** `silence.replace_if_unchanged` — [HIGH] handles neither stale nor lost-update scenarios
  - says: STALENESS
- **cosmology_graph.py** `components` — [HIGH] clusters at weight >= threshold, but the function is named components and the code is not filtering by threshold
  - says: CANDIDATE CLUSTERS at weight >= {args.threshold} : {len(comps)}
- **assay.py** `used` — [MEDIUM] A subset of scored axes that are numeric
  - says: A subset of scored axes

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
