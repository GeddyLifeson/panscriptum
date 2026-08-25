# Sweep run33 — auditor brief (2026-08-25)

You are one of 16 auditors reading `C:\Users\imarl\panscriptum-library-kit`. Fifteen others are
reading other modules at the same time. Your batch is named in your task prompt.

## Rules that are not negotiable

- **AUDIT ONLY. Do not edit, create or delete anything under `src/`.** Sixteen agents editing at
  once corrupts the tree. Your output is a report; the maintenance run applies fixes.
- The only writes you make are your own `handoff/sweep33/AUDIT_batchNN.md` and your
  `sweep_plan.record(...)` call.
- **Never open `prose_enabled` or `step4_enabled`.** They are owner-held gates. A gate that looks
  unnecessary is what a working gate looks like. Do not propose opening them.
- Python is `C:/Users/imarl/miniconda3/python.exe` with `PYTHONIOENCODING=utf-8`. **Never** the
  bare `py` launcher.
- Never run anything from `C:\Users\imarl\panscriptum-export` (the publish copy).
- **Never write regexes or backslashes through a shell heredoc** — use the Write/Edit tools.
  Eaten escapes are the oldest bug in this project.
- **NO CAPS EVER.** Rank your findings if you like; never truncate the list. If you found
  eleven things, report eleven.

## What you are looking for

Real defects, verified against the source you actually read:

1. **Correctness** — logic that is wrong, not merely surprising. Off-by-one, inverted condition,
   wrong variable, unreachable branch, a `try` that swallows the failure it was meant to report.
2. **Silent failure** — an `except: pass`, a return value nobody checks, a write whose verdict is
   discarded, a check that cannot fail (tautology) or that tests nothing that exists (phantom).
3. **Concurrency** — read-modify-write on shared state, a lock of the wrong topology (threading
   lock across processes), a file written without `silence.replace_retry`.
4. **Contract drift** — a docstring or comment that describes behaviour the code no longer has;
   a caller using an API that changed.
5. **Dead code** — functions nothing calls. Report them; do not assume they are safe to delete.

## What is NOT a finding

- Style, naming, formatting, line length, comment density.
- "This could be faster" with no measurement.
- **Anything that might be deliberate design.** This codebase is full of guards that look
  redundant and are not — several were paid for in incidents documented in the comments. If you
  cannot tell whether something is a bug or a deliberate safety, write it under **QUESTIONS**,
  not under findings. A safety that stops work is not a fault.
- A long comment explaining why something is the way it is, is evidence it was thought about.
  Read it before calling the code wrong.

## Your deliverable

Write `handoff/sweep33/AUDIT_batchNN.md` (NN = your zero-padded batch number) shaped like:

```
# Batch NN — run33
Modules read: a.py (N lines), b.py (N lines), ...

## FINDINGS
### 1. <module>:<line> — <one-line claim>  [severity: BLOCKING|MAJOR|MINOR|INFO]
What the code does, what it should do, and the concrete failure: inputs/state -> wrong result.
Quote the 1-3 lines you are talking about.

## QUESTIONS
Things that may be deliberate. Say what would settle it.

## CLEAN
Modules you read carefully and found nothing in. Say so explicitly — a silent module is
indistinguishable from an unread one.
```

If a module is clean, say it is clean. An empty FINDINGS section with a populated CLEAN section
is a complete and honest audit.

## Recording coverage — you must do this yourself

You are the only thing that knows which files you actually opened and read. When your report is
written, run (substituting your real batch number and the modules you genuinely read):

```
cd C:\Users\imarl\panscriptum-library-kit
PYTHONIOENCODING=utf-8 C:/Users/imarl/miniconda3/python.exe -c "import sys; sys.path.insert(0,'src'); import sweep_plan; print(sweep_plan.record('run33', ['a.py','b.py'], batch=NN))"
```

**List only modules you actually read.** A false record is worse than a gap: it retires a module
from auditing for ever on a promise nobody kept.

## Your reply to the orchestrator

Return ONLY a compact summary — under 25 lines. Counts by severity, the single most serious
finding in one sentence, and confirmation that you recorded coverage. Do not paste your report
back; it is on disk.
