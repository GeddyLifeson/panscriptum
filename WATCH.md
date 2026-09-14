# OVERWATCH

round 515  ·  last run 2026-09-14 10:54

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,675 inspected (deep scan as of round 511)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**14 open** (7 high). Newest first.

- **escalation.py** `clear` — [HIGH] clear() is not properly handling the case where the halt file is not cleared, leading to incorrect state reporting
  - says: clear() is supposed to clear the halt and record the ruling
- **escalation.py** `landed` — [HIGH] a boolean that is set to False when the read fails, but the code continues to attempt writes
  - says: the condition its sentence has always claimed to describe
- **workorders.py** `filed.append(...)` — [HIGH] filed.append(...)
  - says: filed.append(...)
- **withdraw_chapters.py** `main` — [HIGH] returns 1 if (a.go and bad) else 0
  - says: Every refusal above was printed and discarded. `main()` had no `return` on any path and the entry point was a bare `main()`, so this tool exited 0 unconditionally
- **withdraw_chapters.py** `_catalog_merge` — [HIGH] returns remaining entries without modifying the current catalog, which contradicts the comment about editing the catalog
  - says: edits the catalog by removing entries whose files have been moved
- **withdraw_chapters.py** `_manifest_merge` — [HIGH] overwrites existing entries with the new withdrawals without considering the union at landing time
  - says: merges the existing manifest with the new withdrawals
- **withdraw_chapters.py** `select` — [HIGH] Returns all entries if no sources or addrs are provided, but the docstring says it should return the whole catalog only when no filters are applied. The code returns all entries even when filters are applied, which contradicts the docstring's claim that it should return exactly what it names.
  - says: The entries this run will withdraw. -> {addr: rec}.
- **escalation.py** `clear` — [MEDIUM] clear() returns False for two entirely different worlds
  - says: PermissionError is caught alongside ValueError because `clear()` raises it for a non-person caller
- **escalation.py** `landed` — [MEDIUM] is the halt, after a successful write, accepted by the system
  - says: is the fault actually in the halt file now
- **escalation.py** `landed` — [MEDIUM] is the halt file written successfully
  - says: is the fault actually in the halt file now
- **axis_correlation.py** `weights` — [MEDIUM] used without definition
  - says: weights for each axis
- **axis_correlation.py** `sigma` — [MEDIUM] used without definition
  - says: standard deviation of the axes
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0
- **feats.py** `main` — [MEDIUM] returns 0 or 1 based on the roll's success, but the comment claims it should follow the same pattern as `--hosts` and `resolve_hosts` which return 1 if _HOSTS_DENIED else 0 and exit nonzero on failure
  - says: the sibling branches in this same file already do it: `--hosts` twenty lines up returns `1 if _HOSTS_DENIED else 0`, and `resolve_hosts`'s own docstring promises "main() exits nonzero on it". `--roll` was the one place the pattern was never applied, even though `roll()` has always returned exactly the counters needed.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
