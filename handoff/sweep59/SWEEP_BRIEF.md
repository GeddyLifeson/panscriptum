# Sweep 59 brief (maintenance run #59, 2026-09-14) -- read all of this before starting

You are ONE batch of a sixteen-batch comprehensive audit of `C:\Users\imarl\panscriptum-library-kit\src`.
Your batch number and module list are in the message that pointed you here.

## Rules
- Python: `C:/Users/imarl/miniconda3/python.exe` with `PYTHONIOENCODING=utf-8`. Never the bare `py` launcher.
- **Read-only on src/.** Do not edit any file under src/, state/ or data/. Your only write is `handoff/sweep59/AUDIT_batchNN.md` (NN = your two-digit batch number) plus scratch files under `C:\Users\imarl\AppData\Local\Temp\claude\C--\21809c3d-0532-4862-b1b9-c94f245080f5\scratchpad\sweep59_bNN\`.
- **Do NOT run** `drill.py`, `verify_math.py`, `allsweep.py`, `mutate.py`, `publish.py`, `generate.py`, `pipeline.py`, `feats.py`, `read.py`, or anything that writes live state. Small scratch scripts that import a module to measure something are fine if that import has no side effects (check first).
- **Do NOT spawn subagents.**
- Never pass prose or regexes through a shell argument. Backticks in a Bash argument get executed. Write text to a file with the Write tool.
- Read `CLAUDE.md` first: Hard Rule -1 (escalation chain, fail closed, in effect) and Hard Rule 0 (NO CAPS: a truncation of an ordered roster is a defect; ranking is fine).

## Method
1. Read EVERY module in your list IN FULL, top to bottom. Page through big files with offset/limit. A module you did not read end to end must not be recorded as covered.
2. Before calling something a bug, read the surrounding docstring and comments. This codebase documents deliberate design at length, and something that looks unnecessary may be doing its job (the prose gate was once deleted for looking like an instruction to a human). A plausible deliberate design is a QUESTION, not a DEFECT.
3. Read the open work orders that touch your modules first, so you do not re-file them: `python -c "import json;d=json.load(open('state/workorders.json',encoding='utf-8'));o=d if isinstance(d,list) else d.get('orders',d);o=list(o.values()) if isinstance(o,dict) else o;[print(x['id'],x['handler'],x['code'],str(x.get('where'))[:120]) for x in o]"` and pull the full text of any whose `where` names your modules. If your finding is already an open order, say so under "Known" with the id and whether it is still accurate. Do not re-file it.
4. Verify every finding against source: quote the exact lines (with current line numbers) and state the concrete input or state that produces the wrong output. No quote means no finding.
5. What to look for, most important first:
   - a safety or gate that FAILS OPEN (an exception swallowed into "allowed", an unreadable file read as clear, a missing import silently disabling a check)
   - checks that cannot fail (tautologies, a net that holds when its subject is absent, a comparison against itself)
   - caps and truncations of rosters, lists or evidence (Hard Rule 0)
   - lost updates: read-modify-write of shared state not through `silence.replace_retry` or a merge; records not written through `pipeline.write_record`
   - wrong results: off-by-one, inverted conditions, wrong variable, stale cache keys, units
   - windows popping (subprocess without CREATE_NO_WINDOW), bare `python` over `pythonw` for daemons
   - comments or docstrings asserting something the code no longer does (a false claim, not a drifted line number: line-citation drift is already filed as orders 89503c58409f / 1d45a56ae1d8 / d7efd67caa6f, so do not file single drifted citations)
6. **Sweep the code the last two shifts wrote.** Run #58 (2026-09-13) and tonight's run #59 changed a lot. Nine of run #58's own fixes were found defective by its own sweep, every one having passed its author's tests.

## Known concurrent activity tonight. Do not report these as findings.
- Run #59 inserted the house eaten-escape guard (`_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))` + self-read `SystemExit`) at module level in 24 modules: address audit binding_health cachekey catalogue_aurora catalogue_codex catalogue_web citecheck cleanup drill entity_match feats generate genre ledger_guard onomast pick_model policy profile style_audit wiki_source workorders worldseed prose_gate. pick_model gained an `import os` for it. DO check the insertion did not break anything (e.g. placed before something it needs, a module run as a script where `__file__` differs).
- `workorders.where_targets` and `file_order` now normalise backslashes (order 5b00f9d39b94). `publish.py` gained `_credential_probe` (display only).
- Other agents are editing right now: `drill.py` (prove stderr output, index-spine net, a guard roster net), `generate.py` (failures.json merge), `chain.py` (harvest index pattern digest), `read.py`/`handbuilt.py` (comment citations only). A file may change under you. If it does, note the mtime you read and re-grep the regions you cite before writing.

## Output
Write `handoff/sweep59/AUDIT_batchNN.md` in this shape:

```
# Sweep 59 -- AUDIT batch NN
Modules read in full: | module | lines | read (top to bottom? mtime) |
## <module>
### New findings
**DEFECT <CRITICAL|MAJOR|MINOR> -- <one-line title>**
where: src/x.py <symbol> (lines A-B at mtime HH:MM)
evidence: quoted lines
failure: concrete state -> wrong result
remedy: smallest correct fix
**QUESTION -- <title>** (two readings, and why this needs a ruling)
### Known (already open orders): id -- still accurate? one line
### Checked and clean: the notable things you verified as correct, one line each
```

Then record coverage. **Only list modules you actually read in full:**
`python -c "import sys; sys.path.insert(0,'src'); import sweep_plan; sweep_plan.record('run59', [<basenames exactly as in your list, e.g. 'deprecated/catalogue_local.py'>], batch=NN)"`
(Pass the list with the Write tool into a scratch .py file and run that, if quoting is awkward.)

## Return value
Return ONLY a compact summary, at most 20 lines: each finding as `SEVERITY | src/file.py symbol | title | one-line failure`, then `QUESTIONS: n`, then `record(): ok/failed`. No preamble.
