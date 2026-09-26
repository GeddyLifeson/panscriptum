# OVERWATCH

round 577  ·  last run 2026-09-25 10:56

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 308,357 inspected  — reference\owner_source_material\rodais\Diathir_Atlas\fmg\libs\jszip.min.js — 2 control character(s) where an escape should be
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** publish.py

## What the model found in the code

**6 open** (1 high). Newest first.

- **chain.py** `singleton_release` — [HIGH] releases a claim unconditionally, which can lead to data loss in race conditions
  - says: releases a claim
- **completeness.py** `host_reachable` — [MEDIUM] returns a message indicating host unreachable but does not actually check reachability
  - says: checks if a host is reachable
- **codewatch.py** `escalation.escalate` — [MEDIUM] escalate is called with a manager, but the comment says it does not rank
  - says: MANAGER EITHER WAY -- see the docstring. The run guard describes; it does not rank.
- **assay.py** `_interval` — [MEDIUM] Calculates the half-width of the error bar using variance propagation, which matches the claim, but the function's name and docstring suggest it should decompose the variance into components, which it does, so no defect of fact is found here.
  - says: Half-width of the honest error bar, in BAND units, by variance propagation.
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if reopen_stranded(...) is None else 0
  - says: return 1 if reopen_stranded(...) is None else 0
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
