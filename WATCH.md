# OVERWATCH

round 574  ·  last run 2026-09-16 16:37

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 305,795 inspected (deep scan as of round 571)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**10 open** (4 high). Newest first.

- **hosts.py** `discover` — [HIGH] probe alternative hosts for every source and keep all that hold
  - says: probe alternative hosts for every source and keep all that hold
- **feats_index.py** `load_index` — [HIGH] unhandled exceptions are silently noted and the record is skipped
  - says: WHAT IT COULD NOT INDEX IS COUNTED, not merely skipped
- **feats_index.py** `host_to_sources` — [HIGH] returns an empty map when the host file cannot be read and caches it
  - says: RAISES rather than returning an empty map when the host file cannot be read, and does NOT cache that emptiness
- **assay.py** `assay` — [HIGH] Computes a Moth Number but the formula is incorrect due to missing covariance terms and incorrect variance calculation
  - says: Compute a Moth Number: 𝔄 = M_a + (sum w_i * s_i) / 10
- **magnitude.py** `anchor` — [MEDIUM] assigned based on conditions involving ceiling and A.LADDER.index
  - says: that, at the one place that knows nothing rescued it.
- **local_agent.py** `rel_real` — [MEDIUM] used in a comparison with rel_written, which is the written path, but the check is only performed if the filesystem disagrees with the string
  - says: compare the two project-relative spellings, and only interrogate the resolved one when the filesystem disagrees with the string.
- **local_agent.py** `rel_written` — [MEDIUM] used in a comparison with rel_real, which is the resolved path, but the check is only performed if the filesystem disagrees with the string
  - says: compare the two project-relative spellings, and only interrogate the resolved one when the filesystem disagrees with the string.
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if reopen_stranded(...) is None else 0
  - says: return 1 if reopen_stranded(...) is None else 0
- **worldseed.py** `WORLD` — [MEDIUM] matches words related to worlds in descriptions or names but may miss some cases due to regex limitations
  - says: matches words related to worlds in descriptions or names
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
