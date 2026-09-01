# OVERWATCH

round 249  ·  last run 2026-09-01 03:24

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 286,381 inspected (deep scan as of round 247)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py
- NOT RUNNING: **0** read.py

## What the model found in the code

**19 open** (4 high). Newest first.

- **allsweep.py** `run_verifier` — [HIGH] the code does not call `run_verifier`
  - says: Run one verifier and PUBLISH ITS GRADE, not just its exit code.
- **allsweep.py** `check_import` — [HIGH] the code does not call `check_import`
  - says: Does it import, and does its CLI parse?
- **allsweep.py** `sweep_plan.modules()` — [HIGH] the code does not call `sweep_plan.modules()`
  - says: had (order f42c55355431). Both consumers below join `SRC` with the name plus `.py`
- **drill.py** `a_raised_halt_reads_back_as_halted` — [HIGH] returns True only if the halt is marked as cleared, which contradicts the claim that it reads back as standing
  - says: a halt that was raised reads back as standing
- **anchors.py** `vector_score` — [MEDIUM] Returns a value derived from the LADDER_RUNGS constant, which is 17, but the comment says it's derived from the Ladder's own height. The function is named 'vector_score' but the comment says it's derived from the Ladder's own height, which is not the same as the LADDER_RUNGS constant.
  - says: Vector on the 0-10 decimal scale, derived from the Ladder's own height. No new quantity.
- **allsweep.py** `bad` — [MEDIUM] counts some subsystems but excludes reconcile findings and some estate findings
  - says: count the number of bad subsystems
- **allsweep.py** `allsweep.Verifier.__iter__` — [MEDIUM] returns an iterator over (label, argv)
  - says: it would have broken verify_math.py:6824-6825
- **allsweep.py** `allsweep.VERIFIERS` — [MEDIUM] a list of Verifier objects
  - says: A plain three-tuple was the obvious shape
- **address_space.py** `HASH_BYTES` — [MEDIUM] Hardcoded to 16 bytes, but the calculation attempts to derive it from _HASH_SPAN
  - says: Derived from the offsets, floored at the historical 16 bytes so today's addresses are unchanged.
- **drill.py** `the_verdict_travels_on_the_record` — [MEDIUM] returns True if the halt_landed is True, but the comment suggests it's about whether the halt was successful, which may not be the same
  - says: the record says whether the halt actually landed
- **drill.py** `net` — [MEDIUM] net runs a test that is not properly scoped to the function it's testing
  - says: net runs a test
- **drill.py** `brief_drops_none_but_keeps_falsey` — [MEDIUM] brief keeps falsey fields and drops only the absent ones
  - says: brief keeps present fields and drops only the absent ones
- **drill.py** `coverage_totals_never_exceed_their_entry_count` — [MEDIUM] Checks if the sum of states (cited, read, no_page, no_host) exceeds the entry count, returning False if it does.
  - says: No source's states may sum PAST its own entry count.
- **derivation.py** `band_edges_ruin` — [MEDIUM] X.2 §4 band edges
  - says: X.2 §4 band edges
- **cascade_bridge.py** `key` — [MEDIUM] the key is folded to lowercase, while the text is stored verbatim
  - says: folding here cannot hide anything: `text` -- the thing a person reads and classifies -- is stored verbatim
- **cascade_bridge.py** `key` — [MEDIUM] the key is derived from the bucket and text.lower()
  - says: the key is derived from the bucket and text
- **cascade_bridge.py** `client_rejection` — [MEDIUM] It is used in a condition to skip entries where the `v` string matches `local_transport` or `client_rejection`.
  - says: A FAULT ON THIS MACHINE IS NOT EVIDENCE ABOUT A PROVIDER'S ACCOUNT, and now that the provider's raw text reaches this line, it can arrive carrying one.
- **cascade_bridge.py** `local_transport` — [MEDIUM] It is used in a condition to skip entries where the `v` string matches `local_transport` or `client_rejection`.
  - says: A FAULT ON THIS MACHINE IS NOT EVIDENCE ABOUT A PROVIDER'S ACCOUNT, and now that the provider's raw text reaches this line, it can arrive carrying one.
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
