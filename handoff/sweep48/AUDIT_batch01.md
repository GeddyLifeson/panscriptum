# AUDIT — Panscriptum run #48, batch 01

Batch: 01
Modules assigned: `src/drill.py`
Lines read: all 16,145 lines, in full, sequential chunks from line 1 to line 16145 (no sampling).
Cross-checks: `grep` passes over the whole file for `except.*pass` (bare-swallow shapes), `TODO/FIXME/XXX`,
`net(` call-site counts (454-479, consistent with CLAUDE.md's stated ~455 call sites), and every
`\.py:[0-9]` line-number citation embedded in the file, each verified against the actual line contents
of the file it names.

## Context

`src/drill.py` is this project's mutation-attack battery: ~479 `net()` calls across ~90 area
functions, each one deliberately trying to defeat a specific safety elsewhere in `src/`. The file is
extraordinarily self-documented — nearly every net's docstring records a real incident, the exact
mutation that defeated an earlier version of the net, and the order that fixed it. This makes it a
genuinely hard sweep target: the overwhelming majority of "this looks wrong" reactions while reading
turn out to be a *historical* defect that is fully described, fixed, and now guarded against by the
net sitting right there. I verified every finding below against the actual current source (of
`drill.py` and, where a citation named another file, that file too) rather than trusting the
docstring's own account of itself.

I found no live instances of categories 1-4 (checks that cannot fail, blind instruments, fail-open
silence, unmarked caps) that are not already covered by an existing net or explicitly reasoned about
in the surrounding docstring. What I did find is two verified instances of category 5 (stale
citations) — notable specifically because this file has an explicit, named policy (order
`0c7592915a48`) of citing other modules' code *by symbol rather than by line number*, precisely
because "a line drifts the first time something is edited above it." Both findings below are cases
where that policy was not followed and the raw line number is now wrong.

---

## FINDING 1 — MINOR — stale/incorrect citation: `drill.py:10731` and `drill.py:10753` ("anchors.py:427")

**What is wrong.** The docstring of `a_ladder_rung_with_no_instrument_window_refuses_to_load` (in
`drill_assay_behaviour`, around line 10729) says:

> "Worse, anchors.py:427 indexes INSTRUMENT_WINDOWS[b] for every b in LADDER with no guard, so
> the same divergence arrives as a KeyError raised from inside production code."

and the `net()` expectation string at line 10753 repeats the same citation:

> "...and is an unguarded KeyError out of anchors.py:427; a window row off the Ladder is numbers
> nothing can ever score against"

**How I verified it.** `src/anchors.py` is 576 lines total. Line 427 there is inside a completely
unrelated function (`verdict(...)` reporting a missing named reference in a Ladder cross-check) and
contains no reference to `INSTRUMENT_WINDOWS` at all — `grep -n "INSTRUMENT_WINDOWS" src/anchors.py`
returns nothing. The code the docstring is actually describing — an unguarded `INSTRUMENT_WINDOWS[anchor]`
lookup inside `instrument()` — lives in **`src/assay.py`**, at lines 1544 and 1549 (`def instrument`
starts at `assay.py:1505`). `assay.py` itself carries the identical wrong citation in its own
in-source comment at line 891 ("anchors.py:427 is worse: it indexes INSTRUMENT_WINDOWS[b]..."), which
is presumably where the citation in `drill.py` was copied from.

So the citation in `drill.py` is wrong on two counts: wrong file (`anchors.py` instead of `assay.py`)
and wrong line (427 vs. ~1544-1549). It's cosmetic — the net itself does not depend on the citation,
it drives the real `ASSAY._check_constants()` — but it is exactly the "prose about code outlives and
outdrifts the code" shape this file's own doctrine (order `0c7592915a48`) exists to prevent, and a
reader chasing the citation to fix the underlying unguarded lookup would open the wrong file.

**Remedy.** Change both citations to name `assay.py`'s `instrument()` function (by symbol, per the
project's own convention, e.g. "`assay.instrument()`'s `INSTRUMENT_WINDOWS[anchor]` lookup") rather
than a line number in a different file. The same correction is needed in `assay.py:891`, which is
outside my assigned module but is the apparent source of the error.

---

## FINDING 2 — MINOR — stale/incorrect citation: `drill.py:15973` ("foreman.py:115")

**What is wrong.** In `main()`'s long comment block explaining why a drill rc of 3 needs no special
handling in `mutate.py`'s baseline signature, one bullet reads:

> "* `foreman` does not run `drill.py` at all (foreman.py:115 records the decision not to)."

**How I verified it.** `src/foreman.py` line 115 is `# just a file under src/), so the IMPORT tier
does smoke-check that drill.py still imports and` — part of a comment (lines ~103-124) about why
`drill.py` is on `foreman.DENYLIST` (the model-patch-safety list), which is a different topic from
"does foreman ever launch drill.py as a job." The actual passage that supports the claim in
`drill.py:15973` is `foreman.py`'s `_contracts_pass()` docstring, specifically the paragraph beginning
"THE DRILL STAYS OUT, per the same ruling" at **`foreman.py:1426`**, which explicitly states the
standing rule that a daemon must not fire the drill on every kept patch.

**Remedy.** Repoint the citation to `foreman.py`'s `_contracts_pass()` (by symbol) rather than line
115.

---

## QUESTION — `escalation.py:409` citation in `a_baseline_that_moves_mid_run_is_recorded_and_the_caveats_do_not_move_with_it` (~line 14102)

This docstring cites "a 16.3-hour pass scored `escalation.py:409` as KILLED" as a historical example
of a confirmed false-kill from a specific mutation run. I did not flag this as a stale-citation finding
because it reads as an identifier from a specific past mutation run's log (which line was mutated in
that run), not a claim about what the code at that line does today — so the "cite by symbol, it drifts"
argument that applies to the other two findings doesn't obviously apply here. Raising as a question
rather than a finding: if this is meant to be a durable pointer for a future reader to go re-examine,
it will drift the same way finding 1 and 2 did, and a symbol-based citation (or none at all) would be
safer.

---

## What I read and found nothing wrong in

- The entire self-test infrastructure at the top of the file (the `_LEDGER_ESCAPES` / `_FLUSHED` /
  `_LEDGER_UNREADABLE` whole-run witness, `_not_a_leak`, `_deliberately_failing`, `_quietly`,
  `_sweep_probe_litter`, `_rows_in`, `_quiet`) — all internally consistent, and the ledger-witness area
  at the end of the file (`drill_ledger_witness`) includes explicit `[control]` nets proving the spy
  and flush wrappers are still installed and still forwarding, which is exactly the right shape to
  stop this instrumentation itself from silently going blind.
- The whole AST-reachability toolkit (`_live_stmts`, `_live_walk`, `_breaks_out_of`, `_arm_leaves`,
  `_call_spellings`, `_reaches_call`, `_gate_precedes_spawn`, `_bound_from_call`,
  `_carries_result_of`, `_rooted_names`/`_is_rooted`, `_write_targets`, `_filtered_names`) — read in
  full; the logic for `if False:`/`if True:`/`while False:`/`while True:` liveness, and the
  `_arm_leaves` continue/break/return/raise scoping, is correct as written and each corner case
  (documented at length as having been wrong in earlier revisions) matches Python's actual runtime
  semantics.
- `LIVENESS_CEILING = 52` and the surrounding ~100-line justification — the stated headroom
  reasoning (not zero, not as large as one orphaned module's ~10) is internally consistent and the
  history of raises is accounted for and dated.
- Every area function from `drill_queue` through `drill_resonance`, `drill_identity_dashboard`,
  `drill_hostcheck`, `drill_weave_plan`, `drill_agent_scratch_gate`, `drill_outside`, and
  `drill_ledger_witness` (the full production `main()` area tuple) — read line by line. No bare
  `except Exception: pass`/`except: pass` exists anywhere in *live* code; every occurrence of that
  string in the file is inside a docstring narrating a *historical, already-fixed* defect.
  `grep -n "except.*:\s*pass"` confirms all 8 hits are in comments/docstrings.
  Cap-related slicing (`grep` for `[:N]`) likewise turns up nothing live in the drill's own report
  paths — every hit is either a legitimate non-report operation (`dirs[:] = ...` filtering
  `os.walk`'s traversal, `del raised[:]` clearing a list) or, again, a docstring describing a
  historical Hard-Rule-0 violation elsewhere that this file's nets now catch.
- `main()`'s own reporting path (the `state/drill_last.json` stamp via `silence.write_json`, the
  rc=3 "verdict did not land" path, the mutation-run-active suppression of the halt, and the
  `_reread_the_breaches`/`_wait_for_a_settled_tree` re-read-before-halting logic added under the
  2026-09-08 owner ruling) is internally consistent: a breach during an active mutation run is
  printed and returned but not escalated to a halt; a breach on a settled tree is escalated with the
  full uncapped list of breached net names (explicitly fixed from an earlier 5-name cap, per its own
  comment at "order 2f679246a6e4").
- Every `net()` call site's `expected` string is non-empty except where the file's own comment
  documents that gap as a found-and-left-visible issue (order `6e7ecf6b9fbd`'s fix printed "(no
  expectation was recorded for this net)" rather than silently nothing).

## Coverage record

Recorded via `sweep_plan.record('run48', ['drill.py'], batch=1)` per the task instructions.
