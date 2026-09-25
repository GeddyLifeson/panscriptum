# sweep63 batch 11 — audit

Auditor for maintenance run #63 (2026-09-24), batch 11. Read-only on `src/`, `data/`, `state/`
except the `sweep_plan.record` call at the end. Did not run the pipeline, drill, verify_math,
mutate, publish, or anything that writes state. Did not spawn subagents.

## Scope (every line read, start to finish, in chunks; no sampling)

- `src/overnight.py` — 2026 lines
- `src/dashboard.py` — 1248 lines
- `src/scout.py` — 835 lines
- `src/custodes.py` — 714 lines
- `src/policy.py` — 611 lines
- `src/axis_correlation.py` — 443 lines
- `src/descending_ladder.py` — 362 lines
- `src/cosmology_graph.py` — 261 lines
- `src/whoruns.py` — 159 lines

Total: 6,659 lines across 9 modules, all read in full. `CLAUDE.md` (Hard Rules -1 and 0) read
first for context.

## Prior audit cross-check

These nine modules were previously covered, split differently, across sweep61 batches 06
(`cosmology_graph.py`, `whoruns.py`), 09 (`whoruns.py` mentioned as the fix for a `codewatch.py`
defect), 11 (`overnight.py`, `dashboard.py`), 13 (`scout.py`, `custodes.py`, `policy.py`), and 16
(`axis_correlation.py`, `descending_ladder.py`). All five prior audit files were read before this
pass, specifically to avoid re-reporting resolved items and to re-verify the ones left open.

Two previously-filed findings were re-verified against the CURRENT source and are now **CLOSED,
FIXED** — not re-reported as findings:

1. **sweep61 batch11 Finding A** (`overnight.py`'s prose-start gate fail-open on a drill result
   outside `{0, 1}`, i.e. `drill_rc != 1`). Current code (`overnight.py:1814-1825`) now reads
   `drill_rc == 0` to start prose, a distinct `elif drill_rc == 1` branch to log the halt, and a
   third `elif` catching every other value (`None` or anything unrecognised) that refuses to
   start and logs "the safety drill did not complete this cycle ... whether a net is breached is
   unknown." The in-file comment cites this exact fix ("AND IT NOW FAILS CLOSED: `== 0`, NOT
   `!= 1` (maintenance run #61, sweep61 batch11)"). Confirmed fail-closed on all three arms.
2. **sweep61 batch11 Finding B** (`overnight.py`'s startup halt interlock raising an uncaught
   `SystemHalted` instead of the per-cycle interlock's graceful handling). Current code
   (`overnight.py:1487-1492`) now catches `_ESC.SystemHalted` explicitly, logs the halt reason
   and a clear message, then raises a `SystemExit` with an explanatory string — no longer an
   uncaught traceback. The in-file comment cites the fix by name ("sweep61 batch11").

One previously-filed finding was also re-verified as fixed:

3. **sweep61 batch13 Finding 1** (`scout.py: sweep()`, `--limit 0` treated as "no limit" via a
   truthiness test). Current code (`scout.py:613-617`) uses `if limit is not None:` with an
   in-file comment citing "sweep61 batch 13" by name. Confirmed correct at `--limit 0`.

No other prior finding in the five source audits applied to code that has since changed in a way
that would revive it, and none of the "questions" or "not filed" items from those audits are
re-litigated here per the brief.

## Findings

### 1. VERIFIED — `dashboard.py`: the `movement()` panel computes a `reset` flag that the page's own renderer never reads, so a counter that just fell (benign restart or a genuine regression) displays identically to a metric that has never been measured before

`movement()` (`dashboard.py:385-569`) computes, per metric, a `reset` flag distinguishing "this
counter just fell" from "this is the first reading":

```python
# dashboard.py:562-568
reset = delta is not None and delta < 0
if reset:
    delta = None
out.append({"metric": k, "now": v, "delta": delta,
            "minutes": round(span),
            "reset": reset,
            "stalled": delta == 0 and span >= 10})
```

The surrounding comment states the intent explicitly: *"Named rather than smoothed: `reset` says
what happened, the delta stays honest, and nothing downstream has to guess whether -3689 was
progress."*

That promise is false for the one consumer that exists. `reset` is set exactly once in the whole
file (`dashboard.py:567`) and never read again — confirmed by `grep -n "reset" src/dashboard.py`,
which returns only the docstring prose and this one assignment. The front-end renderer,
`panelMovement()` (`dashboard.py:856-874`, inside the `PAGE` string served at `/`), branches
purely on `m.delta`:

```javascript
if(m.delta===null||m.delta===undefined){txt='first reading'}
else if(m.delta>0){txt='+'+m.delta.toLocaleString()+' in '+m.minutes+' min';cls='up'}
else if(m.delta<0){txt=m.delta.toLocaleString()+' in '+m.minutes+' min';cls='down'}
else{txt=m.stalled?('NO CHANGE in '+m.minutes+' min'):'no change yet';cls=m.stalled?'down':''}
```

Because Python already nulled `delta` whenever `reset` is true, the JS's first branch
(`m.delta===null`) fires for BOTH a true first reading (no prior sample exists yet) and a reset
(a prior sample existed and this one is lower) — both render the identical string "first
reading". `m.reset` is present in the JSON payload `/api/state` returns but the page that is
supposed to be the one consumer of it never inspects it.

**Concrete failure scenario.** The comment at `dashboard.py:549-561` documents the benign case
this was built for — `read.py`'s in-process `chunks` counter resets to 0 on every reader
restart, so `chunks` legitimately falls and should read as "reset", not "-3689 in N min". That
part is handled correctly (the misleading negative number is suppressed). But the SAME mechanism
applies uniformly to every key in `movement()`'s `keys` dict, including `cited`, `settled`,
`feats`, and `standards met` — quantities that are expected to be monotonically non-decreasing in
normal operation (cumulative counts pulled from `data/COVERAGE.json`, and a passing-standards
count). If one of those genuinely falls — data corruption, a bad rewrite of `COVERAGE.json`, a
real regression in how many standards hold — the panel this project built specifically to answer
"is something actually wrong" (its own docstring: *"the difference between an instrument and a
decoration"*) reports "first reading" instead of surfacing the fall in any way. A real regression
in a monotonic counter is currently indistinguishable, on the one page a person or the dashboard's
own doctrine would look at, from the dashboard simply not having measured that metric before.

**Verified by:** reading `movement()`'s full body and the complete `panelMovement()` JS function
inside the `PAGE` string, and confirming by exact-string grep that `reset` has no other reader
anywhere in the file (server-side Python or the served JS/HTML).

**Suggested fix (not applied — read-only batch):** either render `m.reset` distinctly in
`panelMovement()` (e.g. "RESET (was N)" versus "first reading"), or omit the fabricated
`delta: None` substitution and instead pass the true negative delta alongside `reset: true` so the
JS can choose how to label it — either closes the gap between what the comment claims and what the
page shows. Left as a work-order candidate rather than an edit, per this sweep's read-only rule.

## Everything else in the batch

The other eight modules — `overnight.py` (beyond the two now-fixed items above), `scout.py`
(beyond the now-fixed `--limit 0` item), `custodes.py`, `policy.py`, `axis_correlation.py`,
`descending_ladder.py`, `cosmology_graph.py`, and `whoruns.py` — were read in full and no new
instance of the priority classes (checks that cannot fail, fail-open guards, Hard-Rule-0
caps/truncations, real logic bugs, prose/step4 gate weakenings, regex/escape corruption) was
found beyond what each file's own in-line history already records as found-and-fixed or
found-and-deliberately-held. Specific things checked and ruled out, beyond the CLOSED items above:

- `overnight.py`'s `_manager_stopped`, `_guarded_popen`, `run()`/`start()`/`join()` singleton
  guards, `coverage_snapshot()`, `preflight()`'s pinned-label lookup, `safety_drill()`'s
  `{0,1}`-only branch, and the idle-vs-halt arithmetic in `main()`'s cycle loop were all traced
  and are fail-closed / correctly excluding "already-running", "manager-stopped", "probe-blind",
  and "rc=17" from the idle counter as documented.
- `scout.py`'s `_mutate` compare-and-swap, `hostless()`'s fail-closed unreadable-host-map raise,
  and the stamp-before-work / unstamp-on-never-asked logic in `sweep()` were traced end to end;
  no wrong-branch or lost-update path found.
- `custodes.py`'s degrees-of-freedom table and `convene()`'s abstention/veto wiring match their
  own extensive documentation (Threnody's veto still never fires in production, `table_faults()`
  still has no battery hook — both already recorded as open in the source, not new).
- `policy.py`'s `OPS`/`TYPES`/`ARG_REQUIRED` closed sets, `check_rule`'s malformed-rule-vs-
  document-failure separation, and the two-exit-code contract in `main()` were all consistent
  with their documentation.
- `axis_correlation.py`'s `rho()`/`widening()` fallback-to-mean-vs-fallback-to-0.0 distinction,
  the once-per-site `_no_matrix()` announcement, and `write()`'s gated verdict were traced and
  hold.
- `descending_ladder.py`'s `rung_for_length` boundary loop was hand-traced against the monotonic
  `length_m` column (the U-shaped `binding_J` column is explicitly not used as a lookup key, per
  its own extensive comment) and returns the correct rung at both domain edges and mid-table.
  This module is explicitly HELD/unwired by design (order `66f96febdb3a`) — not itself a finding.
- `cosmology_graph.py`'s inverse-frequency weighting, uncapped pair/cluster writes, and gated
  `write_json` verdict match the module's own record of the 2026-08-25 undeclared-filter fix.
- `whoruns.py`'s `script_of()` already correctly special-cases `-X`/`-W`/`--check-hash-based-pycs`
  (the flags-that-eat-a-value class that sweep61 batch09 found UNFIXED in `codewatch.py`'s
  sibling `runs_script` — that finding is about `codewatch.py`, out of scope for this batch, and
  is not re-filed here).

## Questions

None met the bar for a separate question section this batch — the design questions already on
record in the source (Threnody's veto, `resonance.py`'s absent production caller,
`descending_ladder.py`'s held-not-wired status, `policy.py`'s "at load" wording nuance) are
pre-existing and already named as open in the code itself, not new territory this batch surfaced.

## Coverage

Recorded via `sweep_plan.record('run63', [...], batch=11)` for all nine modules listed above.
