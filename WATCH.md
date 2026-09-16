# OVERWATCH

round 564  ·  last run 2026-09-16 06:08

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 305,734 inspected (deep scan as of round 559)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**17 open** (9 high). Newest first.

- **catalogue_web.py** `_one` — [HIGH] the return value of write_record_catalogue is discarded, leading to potential incorrect status updates and data loss
  - says: GATE ON THE WRITE, like every other caller. write_record_catalogue returns whether the rename LANDED
- **catalogue_web.py** `roll_by_name` — [HIGH] roll_by_name is a dictionary that is modified in-place by multiple threads, leading to potential race conditions and data corruption
  - says: Record and roll writes are serialized under a lock; a source is still written atomically, whole.
- **catalogue_web.py** `save_roll` — [HIGH] does not limit the merge to those sources' rows; instead, it merges all rows of the caller's copy
  - says: -> True if the write landed. `names` limits the merge to those sources' rows.
- **cascade_bridge.py** `prove` — [HIGH] Send one tiny call to a single bucket (the pinned one) and record which actually answer.
  - says: Send one tiny call to EVERY bucket and record which actually answer.
- **binding_health.py** `F.api` — [HIGH] swallows its own network faults and returns None (handled below as a real answer)
  - says: what reaches here is a fault on OUR side -- a bug, a broken import inside the transport -- and with `retries=0` there is no cushion.
- **axis_correlation.py** `rho` — [HIGH] the default is zero
  - says: THE DEFAULT IS THE MEASURED MEAN, NOT ZERO
- **assay.py** `attestation_recognised` — [HIGH] the fault was the silence, not the substitution
  - says: the grade is the ONE operand of assay() with no Layer 1
- **assay.py** `attestation_sigma` — [HIGH] a bar that doubled because somebody typed a lowercase w
  - says: the interval IS the published claim about how much the library does not know
- **assay.py** `assay` — [HIGH] Computes a Moth Number but the formula is incorrect due to missing covariance terms and incorrect variance calculation
  - says: Compute a Moth Number: 𝔄 = M_a + (sum w_i * s_i) / 10
- **catalogue_web.py** `catalogue_composite` — [MEDIUM] Catalogues a cross-media source by merging named categories from several wikis, but the function does not actually merge categories; it processes each sub-wiki's categories separately and aggregates the results without merging them into a single unified list.
  - says: Catalogue a cross-media source by merging named categories from several wikis.
- **cascade_bridge.py** `ask` — [MEDIUM] ask is called with max_attempts=1 but the code does not ensure only one candidate is tested as the function may still process multiple candidates if they are available
  - says: ask is called with max_attempts=1 to ensure only one candidate is tested
- **cascade_bridge.py** `record_unrecognised` — [MEDIUM] record_unrecognised is called with a key and a message, but the key is a bucket name that may not be resolved, leading to incorrect categorization of unparseable replies
  - says: record_unrecognised is called with a key and a message
- **catalogue_codex.py** `roll_landed` — [MEDIUM] roll_landed is used to determine if a write was denied
  - says: the code says it does not matter if the roll is updated
- **catalogue_aurora.py** `update_rows` — [MEDIUM] the function is called but its return value is not used
  - says: COMPARE-AND-SWAP, BECAUSE ATOMIC WAS NEVER THE PROPERTY THIS NEEDED
- **binding_health.py** `release` — [MEDIUM] returns a reason saying it was not released, but does not actually attempt to release the host if the quarantine file is unreadable
  - says: Lift a quarantine. -> the reason it was lifted, or a reason saying it was NOT.
- **audit.py** `audit_invariants` — [MEDIUM] audit the invariants of the entries, but the code does not actually perform the audit as described in the comments and docstrings
  - says: audit the invariants of the entries
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
