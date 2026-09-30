# Sweep68 (maintenance run #68, 2026-09-30) — audit brief

Repo: `C:\Users\imarl\panscriptum-library-kit`. Python: `C:/Users/imarl/miniconda3/python.exe` with
`PYTHONIOENCODING=utf-8` (never the bare `py` launcher). **Do not spawn subagents.**

## Rules

* **READ-ONLY for the project.** Never edit anything under `src/`, `data/`, `state/`, `output/`,
  `prompts/`, `config.yaml`. The only file you write in the repo is your own
  `handoff/sweep68/AUDIT_batchNN.md` (NN = your batch number, two digits).
* Reproductions are welcome, in a scratch directory under `%TEMP%` (e.g. `%TEMP%/aud68_NN`), importing
  modules with their write paths / `log` / `silence.note` redirected so nothing under `state/` or `data/`
  is touched. Never run a module's `main()` against the live tree, never run `drill.py`, `verify_math.py`,
  `pipeline.py`, `generate.py`, `publish.py`, `mutate.py` or anything that calls a model.
* Never pass code containing backslashes through a shell heredoc: write scratch scripts with the Write
  tool and run the file.
* Read `CLAUDE.md` first (Hard Rule -1 chain of command, Hard Rule 0 NO CAPS). A gate that looks
  unnecessary is what a working gate looks like; "this might be deliberate design" is a QUESTION, not a
  finding.

## The job

Read EVERY line of every module in your batch with the Read tool, in chunks, sequentially — no
skimming, no grep-only passes. Then read the previous audit of the same modules
(`handoff/sweep67/AUDIT_batch*.md` — grep for your module names) and say, per prior finding, whether it
still stands.

Look for real defects: wrong logic, off-by-one, inverted conditions, fail-OPEN paths (an unreadable /
missing / corrupt input that authorises work), swallowed exceptions that hide a fault, caps or
truncations of rosters (Hard Rule 0), writes to shared state that bypass `pipeline.write_record` /
`silence.replace_retry`, race windows, a check that cannot fail, dead guards, stale comments that now
lie about the code, and tests/nets that cannot go red.

Every finding needs: file:line, a quote (under 20 words), what is wrong, a CONCRETE failure scenario
(inputs/state -> wrong result), severity (HIGH/MEDIUM/LOW), and ideally a reproduction you actually ran.
Label anything you could not reproduce as UNVERIFIED. Do not pad: "nothing found in X, and here is what
I checked" is a valid result.

## Finishing

1. Write `handoff/sweep68/AUDIT_batchNN.md` (scope table with line counts, prior-audit cross-check,
   findings, questions).
2. Record coverage YOURSELF — only the modules you actually read in full:
   `cd C:/Users/imarl/panscriptum-library-kit && PYTHONIOENCODING=utf-8 C:/Users/imarl/miniconda3/python.exe -c "import sys; sys.path.insert(0,'src'); import sweep_plan; sweep_plan.record('run68', [<module basenames>], batch=NN)"`
3. Return ONLY a compact summary (under 200 words): modules read, finding counts by severity, and a
   one-line description of each HIGH/MEDIUM finding with file:line.
