# OVERWATCH

round 513  ·  last run 2026-09-14 09:50

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,675 inspected (deep scan as of round 511)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**16 open** (13 high). Newest first.

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
- **verify_math.py** `check` — [HIGH] collects all calls to escalation.clear() in src/ (excluding escalation.py and drill.py)
  - says: escalation.clear() has no caller anywhere in src/ -- by AST, not by grep
- **verify_math.py** `append_line` — [HIGH] returns True
  - says: correctly returns False
- **verify_math.py** `BG.burgs_for` — [HIGH] the code computes a value that is not the same as the expected value due to a re-spelled variable name
  - says: the k-th burg holds P1/k, independently recomputed
- **verify_math.py** `BG.burgs_for` — [HIGH] the k-th burg holds P1/k, but the code computes a value that is not the same as the expected value due to a re-spelled variable name
  - says: the k-th burg holds P1/k, independently recomputed
- **standards.py** `bool(refs) and inside >= len(refs)` — [HIGH] the condition is based on the length of refs, which may not be the correct denominator
  - says: the assay reading is valid
- **standards.py** `unans_files` — [HIGH] unans_files is initialized to 0 before the try block, and if any errors occur (like unreadable files or missing data directories), the count is not updated, leading to a cached zero value that is never corrected. This results in a false positive where the system believes there are no unanswered files, even when there are issues.
  - says: THIS ONE LEFT NO TRACE AT ALL (2026-08-28). `unans_files = 0` sat before the try and the only out.append sat after it, so a HIGH-severity evidence standard was emitted MET with an observed `0` in three separate unmeasurable cases
- **silence.py** `append_line` — [HIGH] Does not set O_BINARY flag on Windows, leading to CRLF line endings instead of LF
  - says: NOT BINARY. `os.open` without `O_BINARY` gives a TEXT-mode descriptor on Windows
- **silence.py** `append_line` — [HIGH] Implements a lock but does not handle the case where the lock cannot be acquired, leading to potential data corruption
  - says: NOT SERIALISED. Fixed by taking an OS-level lock on a sidecar for the duration of the write
- **workorders.py** `where_split_by_code` — [MEDIUM] reports on code with multiple where entries, but does not prevent merging
  - says: never auto-merge on this. See where_split_by_code's docstring.
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0
- **feats.py** `main` — [MEDIUM] returns 0 or 1 based on the roll's success, but the comment claims it should follow the same pattern as `--hosts` and `resolve_hosts` which return 1 if _HOSTS_DENIED else 0 and exit nonzero on failure
  - says: the sibling branches in this same file already do it: `--hosts` twenty lines up returns `1 if _HOSTS_DENIED else 0`, and `resolve_hosts`'s own docstring promises "main() exits nonzero on it". `--roll` was the one place the pattern was never applied, even though `roll()` has always returned exactly the counters needed.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
