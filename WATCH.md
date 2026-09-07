# OVERWATCH

round 418  ·  last run 2026-09-07 10:11

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 298,873 inspected (deep scan as of round 415)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**24 open** (8 high). Newest first.

- **read.py** `priority` — [HIGH] Sorted purely by own-page size
  - says: Depth first, because depth is what the model is actually better at.
- **policy.py** `main` — [HIGH] not defined
  - says: entry point for the script
- **overnight.py** `preflight` — [HIGH] Returns (n_failing_checks, blocking) even when health.py crashes or cannot be launched, which contradicts the claim that it returns only when there are corrupted source blocks.
  - says: Returns (n_failing_checks, blocking). Only corrupted source blocks.
- **mutate.py** `indeterminate` — [HIGH] a list that is appended to but not written to disk
  - says: the permanent record of the diff
- **manifest_builder.py** `write_json` — [HIGH] discarded the verdict and printed "Wrote N jobs" regardless
  - says: returns whether the rename LANDED
- **hostcheck.py** `purge-record` — [HIGH] the function silently deletes files without recording the deletion
  - says: the gap it leaves is a recorded finding rather than a silence
- **health.py** `excluded_dirs` — [HIGH] A host is excused if any source on it is excluded
  - says: A host is only excused when EVERY source on it is excluded
- **generate.py** `failures.pop` — [HIGH] removes a failure entry from the failures list even if the chapter was successfully catalogued
  - says: A DEAD REFUSAL MUST NOT READ LIKE A LIVE ONE
- **read.py** `workers` — [MEDIUM] workers = 2
  - says: workers = max(2, min(16, _n + 2)) if _CASCADE_OK else 2
- **publish.py** `prune_export` — [MEDIUM] Returns None, but the code around it expects a count of removed files
  - says: Returns None on refusal, noted and explains
- **publish.py** `prune_export` — [MEDIUM] Returns None on refusal, but the code around it expects a count of removed files
  - says: Refuses to delete in export when necessary
- **policy.py** `evidence_unreadable_detail` — [MEDIUM] only the file names are included, but the error message is truncated to 40 characters
  - says: every failure, every vacuous pass and every unreadable file is named in full, here and in the report
- **policy.py** `ap.add_argument("--limit", ...)` — [MEDIUM] default is no limit, the whole corpus; --limit is for a partial run
  - says: evaluate only the first N of each set
- **policy.py** `--limit` — [MEDIUM] default is no limit, the whole corpus; --limit is for a partial run
  - says: evaluate only the first N of each set
- **policy.py** `main` — [MEDIUM] evaluates the whole corpus by default, with --limit for a partial run
  - says: evaluate only the first N of each set
- **overnight.py** `join` — [MEDIUM] join the roll process with a timeout
  - says: absorb the new feats into ceilings and per-entry judgements
- **overnight.py** `codewatch` — [MEDIUM] imported but not used
  - says: BOUND TO A VALUE, NOT LEFT UNDEFINED
- **overnight.py** `start` — [MEDIUM] The manager-rung gate is implemented, but the logic for handling the manager being stopped is different from run(), which may lead to inconsistent behavior
  - says: AND THE SAME MANAGER-RUNG GATE AS run() (order 4c1eaa9df7fa).
- **overnight.py** `start` — [MEDIUM] Returns None in multiple scenarios, including when the manager is stopped or the process is already running, which may not all indicate the subsystem is closed
  - says: Returns None when the subsystem is closed, which every caller already treats as "did not start".
- **overnight.py** `start` — [MEDIUM] Returns None if the job was already running, but also returns None if the manager is stopped or if the process is already running, which is inconsistent with the claim that it launches a job without waiting
  - says: Launch a job without waiting for it.
- **health.py** `preflight` — [MEDIUM] Writes a stamp file that may or may not be written, and returns the number of problems found
  - says: Run every preflight check. -> the number of problems found.
- **foreman.py** `restart_ollama` — [MEDIUM] This function does not handle the case where the service is already running, which could lead to errors or failed restarts
  - says: This function is supposed to restart Ollama
- **foreman.py** `restart_ollama` — [MEDIUM] This function attempts to restart Ollama but does not actually check if the service is running before attempting to restart it, which could lead to unnecessary restarts
  - says: This function is supposed to restart Ollama
- **foreman.py** `kill_stalled` — [MEDIUM] killed stalled but not the ones that cannot be restarted
  - says: killed stalled

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
