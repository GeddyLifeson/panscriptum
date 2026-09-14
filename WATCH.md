# OVERWATCH

round 516  ·  last run 2026-09-14 11:49

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,675 inspected (deep scan as of round 511)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**16 open** (4 high). Newest first.

- **escalation.py** `clear` — [HIGH] clear() is not properly handling the case where the halt file is not cleared, leading to incorrect state reporting
  - says: clear() is supposed to clear the halt and record the ruling
- **escalation.py** `landed` — [HIGH] a boolean that is set to False when the read fails, but the code continues to attempt writes
  - says: the condition its sentence has always claimed to describe
- **workorders.py** `filed.append(...)` — [HIGH] filed.append(...)
  - says: filed.append(...)
- **withdraw_chapters.py** `main` — [HIGH] returns 1 if (a.go and bad) else 0
  - says: Every refusal above was printed and discarded. `main()` had no `return` on any path and the entry point was a bare `main()`, so this tool exited 0 unconditionally
- **cascade_bridge.py** `ask` — [MEDIUM] ask is called with max, but the code allows neighbor buckets to answer because the max_attempts=1 is not sufficient to prevent it
  - says: ask is called with max_attempts=1 to prevent neighbor buckets from answering
- **cascade_bridge.py** `_bury` — [MEDIUM] is called with a bucket name, but the code uses it to put a cooldown on a key no selector ever asks about
  - says: bench a bucket
- **cascade_bridge.py** `record_unrecognised` — [MEDIUM] is called with a key that is either an empty string or a bucket name, but the code uses it to log unparseable replies and benching
  - says: records unrecognised failures
- **cascade_bridge.py** `_bucket_of` — [MEDIUM] returns empty string when nothing matches, but the code uses it to determine if a bucket is unresolved and logs it as a separate case
  - says: returns the bucket name from an answered ID or answer
- **cascade_bridge.py** `unrecognised_open` — [MEDIUM] The function filters out rows that should be re-evaluated, but the code's logic may not correctly handle all cases of unrecognised failures due to the complexity of the re-triage logic and the potential for stale data.
  - says: The unrecognised failures seen recently, newest first. Read by `standards`.
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
