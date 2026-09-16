# OVERWATCH

round 563  ·  last run 2026-09-16 05:17

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 305,734 inspected (deep scan as of round 559)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**11 open** (6 high). Newest first.

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
- **corpus_db.py** `rebuild` — [HIGH] Rebuilds the index but does not actually process the canonical JSON data as described, instead handling WIKI_HOSTS.json and COVERAGE.json files and attempting to connect to a temporary database without fully implementing the described index rebuilding logic.
  - says: Rebuild the index from the canonical JSON. -> counts.
- **binding_health.py** `release` — [MEDIUM] returns a reason saying it was not released, but does not actually attempt to release the host if the quarantine file is unreadable
  - says: Lift a quarantine. -> the reason it was lifted, or a reason saying it was NOT.
- **audit.py** `audit_invariants` — [MEDIUM] audit the invariants of the entries, but the code does not actually perform the audit as described in the comments and docstrings
  - says: audit the invariants of the entries
- **assay.py** `_rho_source` — [MEDIUM] The function returns a string indicating degradation, but the actual implementation does not directly reference the 'degraded' key from the doc dictionary.
  - says: DEGRADED IS NAMED HERE TOO, NOT JUST MEASURED-VS-FALLBACK
- **assay.py** `RHO_FALLBACK_REASON` — [MEDIUM] The variable is assigned a value when a fallback occurs, but the code does not explicitly guard against the absence of the matrix at import time.
  - says: A guard cited in a comment and absent from the code is worse than no guard, because the next reader stops looking.
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
