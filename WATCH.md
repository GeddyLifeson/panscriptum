# OVERWATCH

round 434  ·  last run 2026-09-08 00:27

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 299,507 inspected (deep scan as of round 433)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**10 open** (2 high). Newest first.

- **cascade_bridge.py** `_tried_add` — [HIGH] called without being defined in this file or its imports
  - says: THE WIDEN PATH NAMES ITS BUCKET TOO (order d5012fbc73c1). The tagged-pool claim loop above calls `_tried_add(cand.bucket)`; this branch reserved, pinned and returned without it, so `_tried()` was empty for every widened call and `ask()`'s metric row wrote `
- **canon_backup.py** `verify` — [HIGH] appends notes about changed, added, and gone files but does not verify the archive's integrity
  - says: is the archive itself still intact and readable, AND WHICH CANONICAL FILES HAVE CHANGED since it was taken
- **catalogue_web.py** `record_path` — [MEDIUM] record_path is used to write the record, but the actual implementation is not shown in the provided code snippet
  - says: the raw join would look for the un-truncated name, miss the record this module itself wrote under the cap, and write a SECOND one beside it
- **cascade_bridge.py** `selftest` — [MEDIUM] the code does instead
  - says: the code says it does
- **cascade_bridge.py** `served` — [MEDIUM] the `served` dict the caller reads still says "answered" with no error text and the reply itself discarded
  - says: the caller reads still says "answered" with no error text
- **binding_health.py** `known_present_titles` — [MEDIUM] not defined in this file or its imports
  - says: returns candidate titles for a host
- **binding_health.py** `known_present_title` — [MEDIUM] not defined in this file or its imports
  - says: returns the primary title for a host
- **binding_health.py** `is_quarantined` — [MEDIUM] returns True if the host is in the quarantined list, but does not raise an exception when the file is unreadable (when strict=False)
  - says: Is this host already held? -> bool. Answers False when the file cannot be  read.
- **binding_health.py** `quarantined` — [MEDIUM] returns a dictionary of hosts that are quarantined, but does not raise an exception when the file is unreadable (when strict=False)
  - says: -> {host: record}. Only those whose retry-after has not yet passed.
- **backfill.py** `backfill_source` — [MEDIUM] backfill_source is used in a context where its output is being summed and printed, but the comment suggests it was meant to be used in a different way
  - says: backfill_source IS CAREFUL TO DISTINGUISH USED TO DIE HERE

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
