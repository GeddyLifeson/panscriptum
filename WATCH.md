# OVERWATCH

round 568  ·  last run 2026-09-16 09:57

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 305,767 inspected (deep scan as of round 565)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**6 open** (1 high). Newest first.

- **assay.py** `assay` — [HIGH] Computes a Moth Number but the formula is incorrect due to missing covariance terms and incorrect variance calculation
  - says: Compute a Moth Number: 𝔄 = M_a + (sum w_i * s_i) / 10
- **policy.py** `ev_unreadable` — [MEDIUM] used in a condition to return 1 when unreadable or ev_unreadable are present
  - says: A RECORD THAT COULD NOT BE READ IS NOT A PASS
- **policy.py** `unreadable` — [MEDIUM] used in a condition to return 1 when unreadable or ev_unreadable are present
  - says: A RECORD THAT COULD NOT BE READ IS NOT A PASS
- **pick_model.py** `fit_note` — [MEDIUM] returns a note that is not shown when VRAM is unavailable
  - says: reports if a model fits in VRAM
- **mutate.py** `base` — [MEDIUM] base is the baseline signatures
  - says: base is the baseline
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
