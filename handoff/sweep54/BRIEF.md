# SWEEP run54 — batch brief (2026-09-09 daily maintenance run)

You are one of sixteen auditors reading `src/` in parallel. Read **every line of every module in
your batch**. A module the sweep never read is not a module with nothing wrong in it.

## Ground rules

* **Read-only.** Do not edit any file under `src/`, `data/`, `state/`, or any ledger. You report;
  the coordinator decides and acts. The one file you write is your own audit page (below), plus
  the one coverage call at the end.
* **Never run anything from `C:\Users\imarl\panscriptum-export`** (the publish copy).
* Python is `C:/Users/imarl/miniconda3/python.exe` with `PYTHONIOENCODING=utf-8`. Never the bare
  `py` launcher.
* Working directory is `C:\Users\imarl\panscriptum-library-kit`.
* **NO CAPS** (project Hard Rule 0). Rank your findings by severity, but never truncate the list.
  If you found nineteen things, report nineteen.
* **Do not write regexes or backslashes through a shell heredoc.** Use the Write/Edit tools.

## What counts as a finding

Look for defects that a reader of the code can be *shown*, with a file and a line:

1. **A check that cannot fail.** A condition that is always true or always false; a counter that
   latches; a comparison against a value the code itself just set; an `except` that swallows the
   only way the thing under test could report trouble. This project's most expensive faults have
   all been this shape — a gate that looks like a gate and refuses nothing.
2. **Correctness bugs.** Wrong operator, off-by-one, a lost update (read-modify-write on shared
   state that another process also writes), a signature that drifted from its caller or from a
   test stand-in, an error path that returns success.
3. **Silent failure.** A swallowed exception that turns a failure into a plausible negative
   result; a value computed and dropped on the floor; a "recorded" fault that reaches no ledger.
4. **A claim in a comment or docstring that the code no longer honours**, including a line
   citation (`foo.py:1234`) that now points somewhere else. Cite the evidence both ways.
5. **Dead or unreachable code** — but see below: much of it here is deliberate and marked.

## What is NOT a finding

* Style, formatting, naming, length of comments. This codebase is deliberately heavily commented;
  long docstrings are the house style, not a defect.
* Code marked kept-on-purpose by an owner ruling ("mark and keep, delete nothing"). Say you saw
  the marking and move on.
* Anything that might be a deliberate design decision. **Report that as a QUESTION, not a fix.**
* Speculation you could not confirm against the source. If you did not verify it, do not file it.

## What to write

Write **`handoff/sweep54/AUDIT_batch<NN>.md`** (two digits, e.g. `AUDIT_batch03.md`) containing,
for each module you read: the module name, roughly how you read it, and each finding as

    ### <severity: MAJOR | MINOR | INFO> — <one-line title>
    **Where:** src/<file>.py:<line>
    **What:** what the code does now, quoted or paraphrased exactly.
    **Why it is wrong:** the failure it produces, concretely — inputs or state -> wrong result.
    **Confidence:** how you verified it (read the call sites / ran it / traced the parse tree).

If a module is clean, say so in one line and say what you checked for. "Nothing found" with no
account of what was looked for is not an audit.

## Then record that you read it

**You** make this call — you are the only thing that knows you actually read the files:

```
cd C:\Users\imarl\panscriptum-library-kit
PYTHONIOENCODING=utf-8 C:/Users/imarl/miniconda3/python.exe -c "import sys; sys.path.insert(0,'src'); import sweep_plan; sweep_plan.record('run54', ['a.py','b.py'], batch=<NN>)"
```

with the exact basenames of the modules in your batch. Record only what you actually read.

## What to return to the coordinator

A **compact** summary only — do not paste your audit page back. At most:

* one line per MAJOR finding: `file:line — title`
* counts of MINOR and INFO
* the path of the audit page you wrote
* confirmation that `sweep_plan.record` returned without error

The coordinator verifies every finding against source before acting. Audits are wrong in both
directions, so a finding you are unsure of should say so rather than be dropped or inflated.
