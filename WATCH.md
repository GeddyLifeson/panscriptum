# OVERWATCH

round 567  ·  last run 2026-09-16 08:52

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 305,767 inspected (deep scan as of round 565)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**5 open** (2 high). Newest first.

- **mutate.py** `reap_orphans` — [HIGH] Deletes sandboxes that are either abandoned (age > ORPHAN_AGE_SECONDS) and have no live owner, or are abandoned and have a live owner but the owner's pid is invalid or the started time is invalid or the claim is expired. Also deletes sandboxes that are not owned by any process (no owner file) and are older than ORPHAN_AGE_SECONDS.
  - says: Delete sandboxes abandoned by runs that were killed. -> [paths removed].
- **assay.py** `assay` — [HIGH] Computes a Moth Number but the formula is incorrect due to missing covariance terms and incorrect variance calculation
  - says: Compute a Moth Number: 𝔄 = M_a + (sum w_i * s_i) / 10
- **mutate.py** `base` — [MEDIUM] base is the baseline signatures
  - says: base is the baseline
- **endpoint.py** `source_pages` — [MEDIUM] returns [] when the file is absent and raises `PagesRegistryUnreadable` when the file is unreadable
  - says: RAISES `PagesRegistryUnreadable` WHEN THE REGISTRY CANNOT BE READ, and never answers [] for it
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
