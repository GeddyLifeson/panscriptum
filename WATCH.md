# OVERWATCH

round 433  ·  last run 2026-09-07 23:49

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 299,507 inspected
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**10 open** (4 high). Newest first.

- **canon_backup.py** `verify` — [HIGH] appends notes about changed, added, and gone files but does not verify the archive's integrity
  - says: is the archive itself still intact and readable, AND WHICH CANONICAL FILES HAVE CHANGED since it was taken
- **backfill.py** `lead` — [HIGH] The function takes the first 420 characters of the stripped page, which is not the same as taking its lead.
  - says: The article's opening PROSE, which is the only description this file will write.
- **assay.py** `SIGMA_MAX` — [HIGH] a lower bound for the widest attestation grade
  - says: the ceiling for attestation sigmas
- **assay.py** `SIGMA_UNKNOWN` — [HIGH] a lower bound for the widest attestation grade
  - says: the widest attestation grade
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
- **assay.py** `scores` — [MEDIUM] The 'scores' key is defined as {k: used[k] for k in sorted(used)}, which maps each axis to its used score, not the variance. The claim says it never recorded the score itself, but the code actually does record the scores.
  - says: The dict is what a caller stores, and until today it recorded WHICH axes were scored and the weighted VARIANCE each contributed, but never the score itself. The numbers the whole assay is about were computed, folded into one composite, and dropped.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
