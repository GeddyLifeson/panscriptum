# Sweep68 — verify-and-fix brief (one agent per audit batch)

Repo: `C:\Users\imarl\panscriptum-library-kit`. Python: `C:/Users/imarl/miniconda3/python.exe` with
`PYTHONIOENCODING=utf-8`. **Do not spawn subagents.** Read `CLAUDE.md` (Hard Rules -1 and 0) first.

## What you own

You own ONLY the modules listed in your prompt (the modules of your audit batch). You may edit those
files and nothing else under `src/`. **Never edit `src/drill.py` or `src/verify_math.py`** (the
coordinator splices nets into them). Never edit `data/`, `state/`, `output/`, `prompts/`,
`config.yaml`. Never run `drill.py`, `verify_math.py`, `pipeline.py`, `generate.py`, `publish.py`,
`mutate.py`, any `main()` against the live tree, or anything that calls a model. Never restart a
process. Never write code containing backslashes through a shell heredoc -- use Write/Edit and run
the file. Scratch goes under `%TEMP%/fix68_NN`.

## The job

1. Read your batch's audit `handoff/sweep68/AUDIT_batchNN.md`.
2. **Verify every finding against the source yourself** (audits are wrong in both directions).
   Reproduce where you can, in scratch, with write paths redirected.
3. For each finding decide: `fixed`, `refuted` (say why), or `question` (it might be deliberate design,
   needs an owner/curatorial ruling, or the fix would break a public signature / add a dependency /
   delete something -- do NOT fix those; describe the options).
4. Fix what is verified and yours to fix, with the SMALLEST change at the root cause. Match the
   surrounding style: this codebase explains every guard in a comment saying what broke and why
   (cite "sweep68" and the finding). Fail CLOSED. NO CAPS (Hard Rule 0). Records go through
   `pipeline.write_record*`; shared state through `silence.replace_retry` / `silence.write_json`.
   Keep function signatures compatible with every caller (grep for callers in all of `src/`,
   including drill.py and verify_math.py, and make sure existing stubs there still fit).
5. **For every fix, write a drill net** that fails on the old code and passes on the new:
   * `handoff/sweep68/nets/<key>.py` -- ONE top-level function `def _net_<key>():` returning True
     when the fix holds. It will be pasted into drill.py, so it may use drill's module globals:
     `os, sys, json, re, shutil, tempfile, time, HERE, _srcdir(), _deliberately_failing(fn)`
     (runs fn with silence/ledger writes suppressed; returns fn's result). Import project modules
     inside the function. Redirect every write path into a `tempfile.mkdtemp()` and restore every
     monkeypatch in `finally`. No network, no model, under ~20 s.
   * `handoff/sweep68/nets/<key>.meta.json` -- `{"name": "<one-line net name>", "expected":
     "sweep68 bNN <finding id>: <what goes wrong if the net fails>"}`
   * `handoff/sweep68/nets/<key>_revert.json` -- `[{"module": "<file>.py", "old": "<text in the FIXED
     module>", "new": "<text that restores the bug>"}]`. `old` must occur EXACTLY ONCE in the fixed
     module. Build this file with a small Python script using json.dump so escapes are right, then
     check: applying it to a scratch copy of the module and running your net function there returns
     False, and on the real fixed module returns True. Say in your results that you ran both.
   * `<key>` = `b<NN>_<short_slug>` (lowercase, underscores).
6. `python -m pyflakes` every file you touched; it must be clean.

## Deliverable

`handoff/sweep68/FIX_batchNN.json` -- a list, one object per audit finding (and question):
`{"id": "F1", "file": "...", "line": 0, "severity": "HIGH|MEDIUM|LOW", "verdict":
"fixed|refuted|question", "what": "<one sentence>", "how": "<what you changed, or why refuted, or the
options>", "net": "<key or null>", "red_green_checked": true|false}`.

Return ONLY a compact summary (under 150 words): counts by verdict, the files you changed, and every
`question` in one line each.
