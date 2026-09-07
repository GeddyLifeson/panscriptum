# OVERWATCH

round 422  ·  last run 2026-09-07 14:13

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 299,182 inspected (deep scan as of round 421)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**15 open** (10 high). Newest first.

- **thread_integrity.py** `dist` — [HIGH] dist is assigned None and then possibly set to _measure, but the code's comment suggests it should represent distance between entities, and the handling of exceptions sets it to None without recording failures, leading to incorrect asymmetry classification
  - says: the code says it does instead
- **sweep_plan.py** `record` — [HIGH] raises an exception when the shard write is denied
  - says: IT DOES NOT RAISE, deliberately. `record()` is called by sixteen batch agents at the end of work already done; taking one of them down over a misspelling would discard the valid part of its claim as well, which is the opposite of what this is for.
- **sevenfold.py** `main` — [HIGH] did not gate its own write
  - says: gated writes
- **secondopinion.py** `run` — [HIGH] is not defined in this slice
  - says: -> a digest of the .py files in `roots`, or None if any of them could not be read.
- **scout.py** `seen` — [HIGH] empty because the file would not open
  - says: pre-read of attempts
- **scout.py** `silence.replace_if_unchanged` — [HIGH] Refuses only when the TARGET is unreadable AS BYTES at write time, and a corrupt-but-readable file digests perfectly well.
  - says: Refuse the write and say why; a caller told "not landed" retries or escalates, where a caller told "landed" over a wreck loses the file silently.
- **rosetta.py** `silence.write_json` — [HIGH] overwrites without checking if the new mine is larger
  - says: DO NOT OVERWRITE A BIGGER MINE WITH A SMALLER ONE WITHOUT SAYING SO (order 6447bcc2f18c)
- **rosetta.py** `kept` — [HIGH] kept counts rows before they are filtered by the 4-row floor
  - says: kept MUST ONLY COUNT ROWS THAT SURVIVE INTO `out`
- **roll.py** `apply` — [HIGH] Apply a function to rows, returning the modified rows.
  - says: Apply `{source_name: {field: value, ...}}` to the roll, key-wise.
- **rigor.py** `identified` — [HIGH] the code checks for a single component but the variable is used in a condition that implies the absence of undefeated or winless entrants
  - says: the beat graph is ONE strongly connected component spanning every entrant
- **threads.py** `recorded_pairs` — [MEDIUM] a function that returns the number of source->source directions
  - says: a function that returns the number of source->source directions
- **secondopinion.py** `run` — [MEDIUM] Returns a dictionary with 'status' and 'findings' for each tool, but the 'status' field is not accurately reflecting whether the tool ran or not. For example, if a tool throws an exception, the status is set to 'ERRORED', but the findings are still empty. However, the docstring states that a tool that did not run has status 'NOT INSTALLED' and an empty finding list, and those two facts must always be read together.
  - says: Ask all three. -> {tool: {'status': str, 'findings': [...]}}.
- **scout.py** `never_asked` — [MEDIUM] sources that were never asked but their stamps are left as they are
  - says: sources that were never asked
- **scout.py** `tmp` — [MEDIUM] A temporary file path that is not unique across threads, leading to potential data loss in multi-threaded environments
  - says: A temporary file path for writing the modified content
- **rosetta.py** `kept` — [MEDIUM] kept is incremented before potential filtering by the 4-row floor
  - says: kept + dropped stayed arithmetically equal to the pre-refine total

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
