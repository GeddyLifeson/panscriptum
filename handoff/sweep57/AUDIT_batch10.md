# Sweep57 batch10 audit

Modules: `src/foreman.py`, `src/sweep_plan.py`, `src/completeness.py`, `src/secondopinion.py`,
`src/zfighters.py`, `src/genre.py`, `src/descending_ladder.py`, `src/resonance.py`.

Every module read in full, top to bottom (foreman.py in three chunks: 1-1000, 1000-1500,
1500-1992; the others each in one pass). Open queue checked first via `workorders.open_orders()`
before writing anything below, to avoid re-deriving known work.

---

## DEFECT 1 — foreman.py's plant-wide OWNER halt is checked once at process start, never again inside its own `--loop`, and none of this batch's other five modules check it at all

**Where:** `src/foreman.py:1924-1988` (`main()`), specifically the single `_ESC.assert_clear(...)`
call at **line 1941**, which sits *before* the `while True:` loop begins at line 1962 and is never
called again inside it.

**Quoted code** (`src/foreman.py`):

```
1924  def main():
1925      # PLANT-WIDE INTERLOCK. The top rung of the escalation chain (escalation.py). If a
1926      # library-wide invariant has been violated, nothing starts until a person rules on it.
1927      # Placed first in main() so there is no path into this job that skips it.
...
1941      _ESC.assert_clear(os.path.basename(__file__))
1942      ap = argparse.ArgumentParser(description="read the work orders and act on them")
...
1959      if a.loop:
1960          codewatch.claim_singleton("foreman")
1961          codewatch.stamp("foreman")
1962      while True:
...
1970          try:
1971              round_once(dry=not a.go, patch=a.patch)
...
1987          codewatch.exit_if_stale("foreman")
1988          time.sleep(a.loop * 60)
```

`round_once()` (called every iteration of that loop) makes no escalation call of its own — a
full-text grep confirms `assert_clear` appears exactly once in the file, at line 1941.

**What is wrong:** the comment claims "Placed first in main() so there is no path into this job
that skips it," but that guarantee is true only of a single invocation. Under `--loop` (the
foreman's own standing mode — CLAUDE.md and this file's own STANDING roster entry run it that
way), the process starts once, checks the halt once, and then runs `round_once()` — which starts
jobs, kills processes and rewrites live source — every `a.loop` minutes for as long as the process
lives, with no further ask of `escalation.assert_clear()`. If an OWNER halt (Hard Rule -1 rung 5,
"HALT EVERYTHING. Nothing starts until a person rules on it") is raised by a different process
*after* this foreman's loop has already started, this foreman will not notice for the rest of its
run.

This is not a hypothetical asymmetry — it is a direct regression against the sibling process that
performs the same job. `src/overnight.py` runs the identical "long-lived loop that starts jobs"
shape, and it **does** re-assert the halt every cycle:

```
overnight.py:1668:            _ESC.assert_clear("overnight.py cycle %d" % cycle)
```

That call sits inside `overnight.py`'s own `while True:` cycle body, not only before it. The
`sweep56/AUDIT_batch15.md` precedent (Finding 4, on `local_agent.py`) explicitly treats
"`assert_clear()` once per invocation... **or once per outer loop cycle**" as the established,
acceptable house pattern, citing `pipeline.py` and `overnight.py` as the modules that do it that
way. `foreman.py --loop` does neither — it checks once per *process*, not once per *cycle* — which
is the one shape that same precedent did not bless.

**Why it matters, concretely:** four of `foreman.py`'s own AUTO remedies start new jobs mid-round
via `overnight.start()`:

```
REMEDIES["every source is fully catalogued"]        = [run_catalogue_gap, run_completeness_audit]
REMEDIES["the character sweep is newer than ..."]   = [run_character_sweep]
REMEDIES["the automation reproduces the charter"]   = [run_charter_regression]
```

`run_completeness_audit` is additionally marked `.always = True` (line 1096-1097), so it is
attempted on **every round with no way to suppress it**. `overnight.start()` does carry its own
gate (`_manager_stopped()`, `src/overnight.py:645-681`) — but that gate asks
`escalation.subsystem_stopped(name)` only, i.e. the **MANAGER rung (4)** stop ledger. It never asks
`escalation.assert_clear()` / reads the OWNER-rung (5) halt file. Verified by reading
`_manager_stopped()` in full: its only escalation call is `_esc.subsystem_stopped(n)` (line 674).
So a job started through `foreman.py --loop --go` mid-round is protected against a MANAGER-level
"close this one subsystem" stop, but **not** against an OWNER-level "halt everything" — the two
rungs this project's own doctrine (CLAUDE.md, Hard Rule -1) is explicit about keeping separate.

The other AUTO remedies in this file are worse off: `clear_learned_caps`, `reprove_pool`,
`adopt_hosts`, `scout_hostless`, `restart_reader` (a SIGTERM), `kill_stalled_job` (a SIGTERM),
`kill_duplicate_jobs` (a SIGTERM), `restart_ollama` (kills and respawns a service),
`recatalogue_models`, `refresh_coverage` — none of these call `overnight.start()`/`run()` at all
(they call `_run()`, a bare `subprocess.run` of a script, or act directly), so they are gated by
**neither** rung. Every one of them can fire on a round after an OWNER halt has been raised, for
as long as the loop keeps running.

**And it compounds with a second gap in this same batch:** none of `completeness.py`,
`genre.py`, `secondopinion.py`, `zfighters.py`, `sweep_plan.py`, or `descending_ladder.py` import
`escalation` or call `assert_clear()` at all (`grep -n "escalation\|assert_clear" src/<file>` for
each returns nothing but prose/comments referencing the word, verified individually). This is
consistent with the established house pattern that *dispatched* jobs rely on the dispatcher's own
halt check (the `sweep56/AUDIT_batch15.md` Finding 1 precedent, `generate.py`) rather than
carrying their own — but that pattern's entire safety argument is that the dispatcher (there,
`overnight.py`) *does* re-check the halt at the top of the cycle it dispatches from. Verified that
`overnight.py` never dispatches `completeness.py` at all (`grep -n completeness src/overnight.py`
returns nothing) — its **only** dispatcher anywhere in `src/` is `foreman.run_completeness_audit()`
via `overnight.start()`. So `completeness.py`'s one and only path into execution runs through
exactly the gap this finding identifies: a dispatcher (`foreman.py --loop`) whose own halt check
is stale by the time a later round fires it, calling a start function
(`overnight.start`/`_manager_stopped`) that checks a different, lower rung, dispatching a module
that trusts the dispatcher to have asked.

**Confidence / classification:** DEFECT. This is a verified, reproducible gap in Hard Rule -1's
top rung, not a design choice with a stated reason (unlike `restart_reader`'s deliberately-absent
`_restartable()` gate, or `descending_ladder.py`'s deliberate HELD-not-wired status, both of which
carry an explicit owner ruling in the source). No comment anywhere in `foreman.py` argues that
per-round re-assertion was considered and rejected; the module's own docstring instead asserts the
opposite ("no path into this job that skips it"), which is the "a check that cannot fail looks
exactly like a check that passed" shape Hard Rule -1 names, aimed at the plant-wide interlock
itself rather than at a downstream detector. Not filed as a QUESTION because the comparison against
`overnight.py`'s own per-cycle re-check is direct, mechanical, and not a matter of interpretation.

**Suggested remedy (not applied — audit only):** add `_ESC.assert_clear("foreman.py round %d" %
n)` (or equivalent) at the top of the `while True:` body in `main()`, mirroring
`overnight.py:1668` exactly, so a halt raised mid-loop is caught at the start of the very next
round rather than only at the next process restart.

---

## Per-module notes

### `src/foreman.py` (1992 lines, read in full)

Beyond DEFECT 1 above, this file is the most heavily self-audited module in the tree — nearly
every function carries an inline "order NNNN" writeup of a bug already found and fixed by a prior
sweep (substring-matching gates, `[:3]`-style Hard Rule 0 caps, lost-update races on shared JSON,
discarded `write_json`/`replace_retry` verdicts, the regex-mutation gate, the `_restartable`/
`_restart_horizon` kill-safety pair, etc.). I traced the ones the task brief calls out by name:

- **"a keeper that restarts something a safety deliberately stopped"**: see DEFECT 1. Separately,
  `kill_duplicate_jobs()` correctly excludes the whole supervision chain and `NEVER_DEDUPED` from
  being treated as a duplicate target (lines 744-751), and `restart_reader()`'s lack of a
  `_restartable()` gate is an explicit, documented owner ruling (lines 545-561), not an omission.
- **"kills a job that cannot be restarted"**: `kill_stalled_job()` (lines 598-715) is correctly
  gated — `_restartable(frag)` (lines 463-497) is asked before every SIGTERM, and an unrestartable
  stalled job is escalated to SUPERVISOR rather than killed (lines 693-706). `_restartable` and
  `_restart_horizon` are both derived from the single `_standing_cmds()` source (lines 447-461),
  which is the fix for a prior sibling-disagreement bug documented in the same block. No new
  finding here.
- Line citations to other modules I spot-checked (`standards.py:1511-1512` at foreman.py:638-639,
  `escalation` rung structure) are accurate against current source.
- KNOWN(c9146abf92df) `ROLL_LOST_UPDATE_REMAINING_WRITERS` — the order's own shift notes (dated
  2026-09-05 and 2026-09-08) already confirm the `foreman.py` half does not reproduce: `grep -n
  SWEEP_ROLL src/foreman.py` returns zero hits, and the only write near the order's cited line 189
  is the unrelated `POOL_PROOF.json` write inside `reprove_pool()`. Re-verified against current
  source; still does not reproduce. Left open as filed (the `roll.py` half is real and separate
  from this batch).
- KNOWN(d9328fe1ee38) `STALL_STANDARD_WATCHES_THE_LOG_NOT_THE_WORK` cites `foreman.py:598`, which
  is `kill_stalled_job`'s current `def` line — citation still accurate.
- KNOWN(e45618de083f, ee92bc6f9b0a) `CODEWATCH_RESTART`/`CODEWATCH_STALE_THROUGH_SHIFT` for
  foreman — these concern the `codewatch.exit_if_stale`/rc=17 restart mechanics at the bottom of
  `main()` (lines 1981-1988), which read correctly against `codewatch`'s documented contract;
  nothing new to add.

### `src/sweep_plan.py` (1117 lines, read in full)

- KNOWN(762fadb8c4c9, bf316bbb7f89) `SWEEP_PLAN_FREEZE_HAS_NO_CAS_ON_CREATE` /
  `SWEEP_PLAN_FREEZE_PLAN_HAS_NO_COMPARE_AND_SWAP` — verified against current source.
  `freeze_plan()` (lines 249-315) checks `frozen_plan(run)` for `reason == "absent"` and, only
  then, computes and writes a fresh plan (lines 284-299). Between the `not os.path.exists(p)`
  check inside `frozen_plan()` (line 205) and the `silence.write_json(plan_path(run), rec, ...)`
  write in `freeze_plan()` (line 299), two callers racing to freeze the same run's plan can both
  observe "absent" and both compute+write, with no compare-and-swap on the create path — the
  second write silently wins and the two callers' agents can be dispatched from two different
  module/batch partitions for the same nominal `run`. Matches the order exactly; no new variant
  found. Everything else in this file (`record()`'s per-shard-not-shared-file write path, the
  three-way `frozen_plan()` reason taxonomy, `normalise_module`'s refuse-rather-than-guess
  matching, `missing_detail()`'s `undetermined` bucket) is deliberately hardened against exactly
  the class of bug this batch was told to look for, and I did not find a gap in any of it.
- Nothing found beyond the above KNOWN order.

### `src/completeness.py` (866 lines, read in full)

- Contributes to DEFECT 1 above (no `escalation.assert_clear()` anywhere in the file, and its sole
  dispatcher does not re-check the halt per round either).
- KNOWN(f5b8e4afb558) `PRIMARY_HOST_ONLY_EVER_FANDOM` — `primary` (lines 442-449) is built by
  matching a source's name against `subdomain(h)`, which is `None` for every non-`*.fandom.com`
  host, so a shared non-fandom host (`en.wikipedia.org`, `www.dandwiki.com`) can never resolve a
  primary. Current code already reports this honestly rather than silently ("Reporting only", the
  order's remedy (a)) at lines 664-671; matches the order's description exactly.
  `_unmeasured`/`land()`'s three-outcome design (`True`/`False`/`SKIPPED_ONLY`) and the
  `SHRINK_FLOOR` guard are all correctly wired together; nothing found there.
- `byslug`'s second index key (`v["file"][:-5].replace("-", " ")`, line 404) is not explicitly
  `.lower()`'d before being stored, while `_rec()`'s lookups (line 454, 619) always lowercase the
  query. This is not a live bug — every filename under `data/records/` is already lowercase by
  convention (spot-checked) — but it is fragile: a hand-added record file with any uppercase in
  its filename would silently fail this alias and fall back to the `str(src).lower()` alias only.
  QUESTION, low confidence, not filed as a defect since no failing input exists today.
- Nothing else found.

### `src/secondopinion.py` (693 lines, read in full)

- The task brief's specific concern — "a tool reporting NOT INSTALLED must never count as a pass
  on any path" — is this module's central design point and I traced it end to end:
  `ran_clean(got)` (line 410-412) requires `v["status"] == "RAN"` for *every* tool, so an absent
  tool (`status="NOT INSTALLED"`) can never contribute to a clean verdict; `missing(got)` (line
  415-417) reports anything not `"RAN"`; `report()`'s "ALL THREE RAN AND ALL THREE FOUND NOTHING"
  line (line 654-656) is gated on `ran_clean(got)`, not on an absence of findings. `_ruff`,
  `_vulture` and `_detect_secrets` each verify the tool's own returncode contract before trusting
  its stdout (documented fixes for exactly the "placeholder JSON on a CLI-usage error" failure
  mode, lines 260-268). I did not find a path where an absent or failed tool's status folds into a
  pass.
- Nothing found.

### `src/zfighters.py` (536 lines, read in full)

- This module is almost entirely hand-authored assay data (the `ROSTER` dict) plus a thin
  `compute()`/`main()` wrapper; the only executable logic of note is the atomic-write-with-checked-
  verdict pattern at the end of `main()` (lines 516-529), which correctly gates on
  `silence.write_json`'s return value. Nothing found.

### `src/genre.py` (381 lines, read in full)

- KNOWN(f646c1c5f1d0) `GENRE_DEAD_DISJUNCTS_AFTER_UNCAPPING` — the order's cited lines (216, 219,
  221, 233) have drifted with edits since it was filed, but the fault it describes is the same
  code the order names, and it is already fully addressed in the current source: `classify_source`
  explicitly reasons through why a `not ranked` disjunct would be dead code (current lines 223-229:
  "`ranked` can therefore never be empty, and a disjunct that cannot be true is the shape Hard
  Rule -1 names"), and the `genres_scored` invariant question the order raised is answered in place
  (current lines 253-260, "IT IS INVARIANT, AND THAT IS AN OPEN QUESTION FOR THE OWNER (order
  f646c1c5f1d0)") rather than silently resolved. Nothing new to add; still open exactly as filed
  (an owner schema decision, not a mechanical fix).
- Nothing else found.

### `src/descending_ladder.py` (357 lines, read in full)

- This module is explicitly HELD-not-wired by owner ruling (order `66f96febdb3a`, discussed at
  length in the module docstring, lines 37-69), and is KNOWN via the same order plus
  `3fb312a72435`. I verified the arithmetic claims the docstring makes on its own behalf
  ("monotonic in length," "`rung_for_length` guards its domain at both ends," "`PLANCK_ENERGY`
  agrees with `m_P c^2`") against the code: `DESCENDING` is indeed strictly decreasing in the
  length column (index 3) across all 15 rows; `rung_for_length()` (lines 186-214) correctly
  refuses both `metres <= 0` and `metres > DESCENDING[0][3]` with `(None, None)` rather than
  rounding into a wrong rung, and correctly returns the Fold below `PLANCK_LENGTH`;
  `PLANCK_ENERGY = PLANCK_MASS * C_LIGHT ** 2` (line 89) is a derivation, not a duplicated literal.
  Traced `rung_for_length`'s bracket-assignment loop by hand against several boundary and
  between-rung values; it correctly assigns an in-between size to the coarser (larger-length)
  bracket rather than mis-binning it. No arithmetic fault found.
- Nothing else found.

### `src/resonance.py` (299 lines, read in full)

- This module documents its own unwired status in detail (module docstring, "WHAT IS ACTUALLY
  WIRED... This module has NO PRODUCTION CALLER"), and the Jacobi-vs-Gauss-Seidel convergence
  defect it describes fixing (order `6e1c72cddfeb`) is present in the code as the fix, not the
  bug: `hodge_decompose()` (lines 89-224) uses in-place Gauss-Seidel updates (line 173-174,
  `theta = dict(theta)` then updated per-node using already-refreshed neighbours within the same
  sweep) with an explicit convergence test (line 181) and returns `converged: False` /
  `eta: None` rather than a confident-looking wrong number when the sweep budget is exhausted
  (lines 184-193). The `_isolated` dead-branch check (lines 148-163) is correctly documented as
  unreachable-by-construction and kept as a defence rather than deleted. `incomparability_rate`'s
  UNMEASURED/TIED/INCOMPARABLE three-way split (lines 237-277) is internally consistent and
  matches its own docstring. No arithmetic or fail-open fault found.
- Nothing else found.

---

## Summary of findings

| # | Module(s) | Classification |
|---|---|---|
| 1 | `foreman.py` (+ gap shared by `completeness.py`, `genre.py`, `secondopinion.py`, `zfighters.py`, `sweep_plan.py`, `descending_ladder.py`) | **NEW DEFECT** — OWNER halt checked once per process, not once per `--loop` round; no dispatched module in this batch re-checks it either |
| — | `sweep_plan.py` freeze-on-create race | KNOWN(762fadb8c4c9, bf316bbb7f89) |
| — | `completeness.py` primary-host-only-fandom | KNOWN(f5b8e4afb558) |
| — | `completeness.py` `byslug` case-sensitivity fragility | QUESTION (low confidence, no live failure) |
| — | `genre.py` dead disjuncts / invariant field | KNOWN(f646c1c5f1d0) |
| — | `foreman.py` roll lost-update | KNOWN(c9146abf92df) — re-verified still does not reproduce on the `foreman.py` half |
| — | `foreman.py` stall-standard / codewatch-restart citations | KNOWN(d9328fe1ee38, e45618de083f, ee92bc6f9b0a) |
| — | `descending_ladder.py` held-not-wired | KNOWN(66f96febdb3a, 3fb312a72435) |
| — | `secondopinion.py`, `zfighters.py`, `resonance.py` | nothing found |
