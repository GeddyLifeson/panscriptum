# OVERWATCH

round 523  ·  last run 2026-09-14 16:12

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,777 inspected
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**4 open** (0 high). Newest first.

- **hostcheck.py** `score` — [MEDIUM] Calculates a verdict based on various conditions, including lift and aboutness, but does not directly measure the host's baseline or lift as described in the docstring.
  - says: One host, fully judged: how much of this roster it holds, ABOVE ITS OWN BASELINE.
- **grounding.py** `classify_text` — [MEDIUM] The function is called but its behavior is not described in the code snippet, so it's unclear what it does.
  - says: Unranked-away: every grounding in GROUNDINGS is scored and every score is kept, so the denominator below is the whole field and `runners_up` is the whole field minus the winner.
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0
- **feats.py** `main` — [MEDIUM] returns 0 or 1 based on the roll's success, but the comment claims it should follow the same pattern as `--hosts` and `resolve_hosts` which return 1 if _HOSTS_DENIED else 0 and exit nonzero on failure
  - says: the sibling branches in this same file already do it: `--hosts` twenty lines up returns `1 if _HOSTS_DENIED else 0`, and `resolve_hosts`'s own docstring promises "main() exits nonzero on it". `--roll` was the one place the pattern was never applied, even though `roll()` has always returned exactly the counters needed.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
