# Sweep60 batch09 audit

Modules read in full, uncapped: src/foreman.py (2262), src/codewatch.py (1168), src/rosetta.py
(815), src/manifest_builder.py (671), src/zfighters.py (536), src/suppressions.py (425),
src/style_audit.py (342), src/tuning.py (286), src/lognames.py (52). Total 6,557 lines, matches
the assignment exactly; every file read start to end, no sampling.

## Overall impression

This batch is unusually clean. Every one of these nine files already carries dense, dated
"order xxxxxxxxxxxx" comments recording a prior bug, its measured impact, and the fix -- the
project has clearly been swept hard before. Most of the classic failure shapes the brief asks
about (substring checks standing in for counts, silent truncation, fail-open `except: pass`,
stale caches) are visibly *already fixed* in this batch, with the old bug preserved in a comment
as a warning. I looked for anything that slipped through those prior sweeps rather than re-finding
what the comments already document.

## Findings

### 1. `foreman.py:kill_duplicate_jobs` reports `did=True` (success) even when a real duplicate is left running -- MEDIUM/HIGH, VERIFIED

File: `src/foreman.py`, function `kill_duplicate_jobs()`, lines 830-891. The decisive lines:

```python
871	    for job, procs in seen.items():
872	        if len(procs) < 2:
873	            continue
874	        if any(stamp is None for stamp, _ in procs):
875	            silence.note("foreman.py:dedup-unstamped")
876	            unaged.append(job)
877	            continue
878	        procs.sort()                       # oldest first
879	        for _stamp, p in procs[1:]:
880	            try:
881	                os.kill(p, signal.SIGTERM)
882	                killed.append(job + ":" + str(p))
883	            except Exception:
884	                silence.note("foreman.py:dupes-kill")
885	    note = ("; left alone (creation time unreadable, so no victim can be chosen): "
886	            + ", ".join(unaged)) if unaged else ""
887	    if killed:
888	        return True, "ended duplicate " + ", ".join(killed) + note
889	    if unaged:
890	        return True, "no duplicate ended" + note
891	    return True, "no duplicates found now"
```

When a job name has two or more live processes (`len(procs) >= 2`) but at least one of their
creation timestamps could not be read, the function appends the job to `unaged`, kills nothing
for it, and then at line 890 returns **`True`** ("no duplicate ended..."). It never returns
`False` anywhere in this function except the earlier "could not enumerate processes" branch
(line 844).

Why this is wrong: `foreman.py`'s own doctrine, stated explicitly elsewhere in the same file for
`reprove_pool` (the "make did honest" ruling, order 7ad10a229440, "`did` MEANS 'THE PROBLEM THIS
STANDARD HAS WAS FIXED', NOT 'A MEASUREMENT COMPLETED'"), is that a remedy's `did` return value
must mean the standard is now actually satisfied. The standard this remedy exists to satisfy is
"one instance of each job." When `unaged` is non-empty, that standard is **not** satisfied --
there genuinely are two-or-more live processes for that job name, and the function deliberately
declined to kill any of them ("left alone ... no victim can be chosen"). Reporting `did=True` in
that case is a tautological success: the return value cannot distinguish "no duplicates exist"
from "duplicates exist and I could not touch them," and both print as an unqualified success in
the operational log (`state/FOREMAN.json`, read every cycle by `overnight.foreman_report()`) and
on the console (`print(f"   AUTO   {o['standard']} -> {fn.__name__}: {what}")`).

Contrast with the sibling remedy `kill_stalled_job` (lines 696-827), which handles the exact
analogous situation -- a real problem found but deliberately not acted on -- correctly:

```python
825	    if unrestartable or working:
826	        return False, "no job killed" + spared
```

`kill_stalled_job` treats "found the problem, chose not to act" as `False` (not fixed).
`kill_duplicate_jobs` treats the same shape of situation as `True` (fixed). That inconsistency
between two remedies in the same file, one of which explicitly documents the "did must be
honest" rule, is the tell.

**Effect / what state triggers it:** two or more `python.exe`/`pythonw.exe` processes running
the same `src/<job>.py` script where `psutil`'s `create_time()` cannot be parsed into the
expected 14-digit stamp for at least one of them (i.e. `_python_processes()`'s `started` field
comes back `None` for one of the group). This can happen for a process still very early in
startup, one whose `create_time()` raised, or any transient `psutil` read glitch. In that state,
`kill_duplicate_jobs` walks away leaving both processes running side by side (the exact hazard
the module's own docstring describes -- "Two supervisors is the worst duplicate of all: each
starts the jobs the other is already running") and reports the round as a success.

**Verification:** read directly, by tracing all three return paths against the `unaged`/`killed`
bookkeeping built earlier in the same function; no execution needed to see the branch is dead-end
`True`. I did not find a caller elsewhere in this batch that further inspects `did` for this
particular standard beyond the print/log lines and the `.always` remaining-remedies logic in
`round_once`, so the externally visible harm is specifically: the printed report and
`state/FOREMAN.json` say a round handled duplicate-process hygiene when it did not, for as long
as the timestamp read stays unreliable for that job.

## Not flagged as findings (checked, judged not to be bugs)

- `codewatch.runs_script`'s `return False  # cannot tell whose copy it is -- FAIL OPEN` (line
  386): the comment's "FAIL OPEN" is correct from the singleton-guard's perspective (returning
  False here means "not a match," which lets a second instance start) -- consistent with the
  rest of the module's stated fail-open posture for `claim_singleton`/`twins`. Not a defect.
- `rosetta.spearman`, `zfighters.value`, `tuning.workers/regime`, `suppressions._mutate`,
  `manifest_builder.load_record` scoring, `style_audit`'s self-test assertions: traced each
  fully against their docstrings' own worked examples and prior-bug write-ups; all matched.
- `foreman._catalogue_batch`'s `rate = max(1, min(rate, len(order)))` degenerate case (empty
  `gap`) produces an empty `batch` safely; the caller's `if not batch:` guard covers it.
- `foreman._contracts_pass` correctly skips `verify_math.py` in its own loop (it was already run
  in full by the caller three lines earlier) -- not a hole, as the docstring explains.

## Coverage note

I did not find any dead/unreachable functions, stale `file.py:NNN` citations, or new caps/
truncations in this batch -- the "Hard Rule 0" truncation-removal sweep appears to have already
covered these nine files specifically and thoroughly (many comments cite the exact prior cut and
its measured cost). The one finding above is a logic/reporting bug, not a truncation or cap.
