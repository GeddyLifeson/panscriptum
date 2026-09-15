# OVERWATCH

round 534  ·  last run 2026-09-15 01:17

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,847 inspected (deep scan as of round 529)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**14 open** (4 high). Newest first.

- **completeness.py** `host_reachable` — [HIGH] returns a message about host unreachability but does not actually check reachability
  - says: checks if a host is reachable
- **codewatch.py** `escalation.escalate` — [HIGH] escalate is called with a value that is not escalation.MANAGER
  - says: MANAGER EITHER WAY -- see the docstring. The run guard describes; it does not rank.
- **chain.py** `write_result` — [HIGH] only persists `names` and `strengths` if the fit was successful
  - says: persist `names` and `strengths` whole
- **catalogue_web.py** `first_cat` — [HIGH] first_cat is used to store the first category a title was found in, but the code later uses `first_cat.get(title) or canon.split(" (")` to determine the type, which may not be the actual category the title came from.
  - says: Keyed on the RAW title, deliberately: `clean_titles` only filters and de-duplicates and `rank_by_size` only reorders, so every string that survives into `wanted` below is one of these exact strings. Nothing normalises them in between, so nothing can drift.
- **cleanup.py** `low_pref` — [MEDIUM] filter entries starting with the ceiling entity but return the shortest one as 'prefix' when there's exactly one match
  - says: filter entries starting with the ceiling entity
- **chain.py** `changed` — [MEDIUM] Seeded at 1, not 0, when the recipe itself just changed above: that write belongs in this cycle's land even on an empty corpus (no file loop iteration would otherwise set `changed`)
  - says: Seeded at 1, not 0, when the recipe itself just changed above: that write belongs in this cycle's land even on an empty corpus (no file loop iteration would otherwise set `changed`)
- **chain.py** `live` — [MEDIUM] Seeded at 1, not 0, when the recipe itself just changed above: that write belongs in this cycle's land even on an empty corpus (no file loop iteration would otherwise set `changed`)
  - says: Seeded at 1, not 0, when the recipe itself just changed above: that write belongs in this cycle's land even on an empty corpus (no file loop iteration would otherwise set `changed`)
- **catalogue_web.py** `tally` — [MEDIUM] tally is a dictionary that is modified in a non-atomic way, leading to potential race conditions when multiple threads access it concurrently.
  - says: Record and roll writes are serialized under a lock; a source is still written atomically, whole.
- **cascade_bridge.py** `try_disabled` — [MEDIUM] Attempts to enable models and test them, but the code does not actually verify if they have a working key as described.
  - says: Test models that are switched off in config but DO have a working key.
- **cascade_bridge.py** `_bury` — [MEDIUM] a call to `_bury` is made with a bucket name, but only if the bucket is not empty and strikes are above a threshold
  - says: a call to `_bury` is made with a bucket name
- **catalogue_codex.py** `roll_landed` — [MEDIUM] roll_landed is used to determine if a write was denied and to decide the exit code
  - says: the code says it does not matter if the roll is updated
- **catalogue_aurora.py** `roll_landed` — [MEDIUM] used as a flag to determine if the roll was successfully updated, but the code does not properly handle the case where the update might have failed
  - says: COMPARE-AND-SWAP, BECAUSE ATOMIC WAS NEVER THE PROPERTY THIS NEEDED
- **binding_health.py** `F.api` — [MEDIUM] returns None for network faults, which is UNMEASURED, not a verdict
  - says: what reaches here is a fault on OUR side -- a bug, a broken import inside the transport -- and with `retries=0` there is no cushion.
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
