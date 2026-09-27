# sweep65 auditor brief (maintenance run #65, 2026-09-26)

You are one of 16 auditors in the Panscriptum daily comprehensive sweep, working on
`C:\Users\imarl\panscriptum-library-kit`. Your batch number and module list are in your prompt.

## What to do

1. Read EVERY line of EVERY module in your batch under `src/`, start to finish. Use the Read tool
   with offset/limit chunks for large files. No sampling, no grep-only skimming. A module you did
   not read in full must not be recorded as covered.
2. Audit for real defects: wrong logic, off-by-one, inverted conditions, exceptions swallowed
   where the code claims to fail closed, a guard that cannot fail, races on shared files,
   truncation or caps of any roster/list (Hard Rule 0: no caps; ranking is fine, ranking then
   truncating is not), comments that state something the code no longer does, dead branches,
   wrong units, Windows-specific breakage (this machine is Windows 11; WMIC is gone; use psutil).
3. VERIFY every finding before you write it down: quote the exact lines, trace the path, and where
   it is cheap and safe, reproduce it by EXECUTION in a scratch copy outside the repo (for example
   under %TEMP%). Mark each finding CONFIRMED (reproduced or traced beyond doubt) or SUSPECTED.
4. Anything that may be deliberate design is a QUESTION, not a finding. Put it in its own section.
5. Check your modules' earlier audits in `handoff/sweep64/` (and older sweepNN folders if useful)
   so you do not re-file something already fixed. Do not re-file anything that already has an open
   order: search `state/workorders.json` for the file name or function before writing a finding.

## Hard limits

* READ-ONLY. Do not edit, create or delete anything under `src/`, `data/`, `state/`, `output/`,
  `prompts/`, `reference/` or the repo root. Your only writes are your audit file and the
  `sweep_plan.record` call below.
* Do not spawn subagents.
* Do not run the pipeline, generate, publish, the crawl, overwatch, foreman, mutate, drill or
  verify_math, and never call anything that clears a halt or touches `prose_enabled` or
  `step4_enabled`. Small read-only python snippets are fine.
* Python is `C:/Users/imarl/miniconda3/python.exe` with `PYTHONIOENCODING=utf-8`. Never use `py`.
* Never put regexes or backslashes through a shell heredoc; write scratch scripts with the Write
  tool.

## Output

1. Write `handoff/sweep65/AUDIT_batchNN.md` (NN = your two-digit batch number) with:
   - Scope: each module, its line count, how you read it (chunks).
   - Findings: for each, `file:line`, severity (CRITICAL / MAJOR / MINOR / COSMETIC), CONFIRMED or
     SUSPECTED, the evidence (quoted lines), the failure scenario (concrete input -> wrong result),
     and a proposed fix.
   - Questions (possible deliberate design), each with the two readings.
   - Cleared: anything you examined closely and found correct, one line each.
2. Only after you have read every module in full, record coverage by running this with the
   miniconda python (edit the list to the modules you actually read in full):

   ```
   import sys; sys.path.insert(0, r"C:\Users\imarl\panscriptum-library-kit\src")
   import sweep_plan
   sweep_plan.record("run65", ["module_a.py", "module_b.py"], batch=NN)
   ```
   Write that snippet to a scratch .py file with the Write tool and run it; do not pass it through
   `python -c`.
3. Your final reply must be SHORT (at most 15 lines): counts by severity, one line per finding
   with `file:line` and CONFIRMED/SUSPECTED, and whether `record` succeeded. The detail lives in
   the audit file, not in your reply.
