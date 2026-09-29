# sweep67 batch 01 -- AUDIT

## Scope

`src/drill.py`, 26,856 lines (`if __name__ == "__main__":` at 26855-26856). Read sequentially with
the Read tool in 1,000-line chunks, line 1 to 26856, none skipped. Read-only: nothing under `src/`,
`data/`, `state/`, `output/`, `prompts/`, `reference/` or the repo root was edited or run. `drill.py`
was NOT imported or run. Findings were reproduced with two scratch scripts under `%TEMP%\s67\`
that extract the relevant functions from the file by `ast` and exec them in isolation (a.py: area
roster and duplicate net names; b.py: the `_static_truth`/`_live_walk` and prose-gate fixtures).
Roster check: every top-level `drill_*` area is named in `main()`'s tuple; no duplicate net names
(704 `net(` call sites, so `_ATTACKS` keys cannot collide).

## Prior-audit cross-check (handoff/sweep66/AUDIT_batch01.md)

- D1 (declined-measurement notes trip the ledger witness): **partly fixed, still stands for the
  cleanup half.** The decline sites now append to `_DECLARED_ESCAPES` (4757, 4762, 4836, 4849,
  4854, 14513-14722, 22415, 23863) and net `a_declined_measurement_is_declared_not_recorded`
  guards them. The cleanup-failure notes the prior audit also listed were NOT moved -- see F1.
- D2 (`_meta_ban_has_no_fall_through` dead-code): **fixed** (10069-10077, direct statements of the try body).
- D3 (`overnight_prose_needs_a_clean_drill` exists-check): **quantifier fixed** (13834, every prose
  start must be guarded, control at 13861), **substring weakness remains** -- see F2.
- D4 (`_scope_lands_key_wise` temp leak): **fixed** (rmtree in `finally`, 10702).
- D5 (stale gate-closed title/docstrings): **fixed** (`_gate_closed_shelf_holds`, 13535).
- Q1 (`_carries_result_of` 8-pass bound): **fixed** (true fixpoint, 1550).
- Q2 (source-shape nets ignoring `_srcdir`): **still stands**: `_no_programmatic_clear` (5318),
  `_publish_never_swallows_a_missing_safety` (5798), `_withdrawal_takes_a_snapshot` (8820),
  `_counts_decided_by_substring` (19647), `_no_new_bare_kill0_probe` (20231),
  `_a_module_claimed_wired_is_actually_imported` (20308), `_guards_are_wired_where_claimed` (13501),
  and the `HERE/src` readers `generate_lands_catalog_every_chapter` (13755),
  `overnight_prose_needs_a_clean_drill` (13823), `throttle_iterates_a_snapshot` (13883),
  `every_ollama_call_site_takes_a_lane_turn` (20976). No ruling seen.
- Q3 (two halt-interlock nets outside the sandbox): **fixed** (16182, 16256, both under `_esc_probe`).
- Q4 (stale "57 nets"): **fixed** as history text (5593).
- Sweep65 carry-overs: `_catalog_matches_disk` absolute path now refused (13623); the re-read now
  needs THREE holding readings (25861), not one; `_live_watch` list is still hand-kept (15398);
  closure probes now have the shape net `every_sandboxed_closure_still_runs_inside_the_sandbox`
  (17486).

## Findings

### F1. Probe-CLEANUP notes still reach the ledger witness, so a transient lock on a scratch file halts the library. MINOR (latent; live under this machine's Norton/scanner locks). VERIFIED by reading.
Sweep66 D1 named these sites; only the "declined measurement" ones were moved to
`_DECLARED_ESCAPES`. The pattern in `a_declined_measurement_is_declared_not_recorded` (23917)
matches only `unstageable|absent|unreadable|unsupported|unwritable`, so `-cleanup` notes are out
of its reach. These run OUTSIDE any sandbox, so `silence.note` -> `health.record` is the spied
`_spy_record` and lands in `_LEDGER_ESCAPES`; `no_probe_writes_into_the_live_failure_ledger`
(25682) then raises, the re-read reproduces it from the same non-empty list, and `main()`
escalates DRILL_BREACH at OWNER:
`drill.py:junction-probe-cleanup` (4741), `surface-probe-cleanup` (4822, 4828),
`surface-probe-readback` (4866), `unlisted-probe-cleanup` (5139), `empty-find-probe-cleanup`
(5189), `_remove_scratch_in_live_state` sites (8684 -> snapshot-*/empty-snapshot-cleanup; 8918),
`history-probe-cleanup` (24243, 24280), `prove-net-cleanup` (907-920, `--prove` only).
Contradicts the comments at 4485-4489 and 4773-4781, which say a failed tidy-up "is not a reason to
FAIL the net" and that killing the battery over a permissions error would be wrong: the note does
exactly that, one net later, at OWNER rung.
Suggested fix: route these through `_DECLARED_ESCAPES` (or `_not_a_leak`) the way the decline sites
were, and widen `_decline_notes` to `cleanup|readback` so a new one is caught.

### F2. `overnight_prose_needs_a_clean_drill` is decided by a substring of `ast.unparse(test)`. MINOR. REPRODUCED (b.py).
13839-13841 accepts any guard whose unparsed test contains `drill_rc == 0`. All of these return
True: `drill_rc == 0 or True`, `drill_rc == 0 or drill_rc is None` (a crash/timeout, None, opens
prose -- the exact fail-open the net was written against), and `not drill_rc == 0` (inverted). The
control at 13853 only defeats the old `!= 1` spelling. Fix: require an `If` whose test is a
`Compare` of Name `drill_rc` with Constant 0 (or an `And` BoolOp containing one and no `Or`).

### F3. `_static_truth` does not fold an all-False `or` (or an all-True `and`), so a gate in `if False or False:` reads live. MINOR. REPRODUCED (b.py).
1143-1149 returns None unless one operand decides the whole expression. `if False or False:
gate()` stays in `_live_stmts`/`_live_walk`, so every "the call is reachable" net (`_reaches_call`,
`_gate_precedes_spawn`, `_calls_within(reachable=True)`) accepts a gate parked there -- the defeat
`_live_stmts`'s own docstring says it exists to stop. Same for `if 0 == 1:` (Compare not folded).
Fix: `Or` -> False when every operand is False; `And` -> True when every operand is True;
optionally fold constant Compare.

### F4. `unreadable_roll_does_not_exclude_the_library` does not drive an unreadable roll. MINOR (net overclaims). VERIFIED by reading roll.py.
23349 calls `roll.in_scope(name, rows=[])`. `rows=[]` is an EMPTY roll (`out_of_scope` calls
`load()` only when `rows is None`), so the fail-open path in `roll.load()` (unreadable -> `[]`,
noted) is never entered; a mutation making an unreadable roll exclude everything would survive.
Fix: point `roll.ROLL` at a torn scratch file (inside `_deliberately_failing`) and assert True.

### F5. `coverage_totals_never_exceed_their_entry_count` passes vacuously on a wrong-shape COVERAGE.json. MINOR.
13980-13982: `rows = json.load(...)`; `for r in rows: if not isinstance(r, dict): continue`. A
COVERAGE.json that parses to a dict (iterates keys, all skipped) reads True. The absent-file pass is
documented (13973); the wrong-shape one is not. Sibling nets (`_policy_corpus_clean`) fail on
unreadable. Fix: require `isinstance(rows, list)` and at least one dict row.

### F6. Stale docstrings. TRIVIAL.
`_reread_the_breaches` (25810) says it returns `(reproduced, note)`; it returns the 3-tuple
`(reproduced, recovered, note)` (25887, used at 26734). `_catalog_matches_disk` (13601-13604) says
`gate_claim_matches_reality` is "two nets up"; that net is defined below it, inside `drill_inspector`.

## Questions (possibly deliberate; owner decides)

- **Q1.** Sweep66 Q2 still open: ~11 source-shape nets read the live file, not `_srcdir()`, so
  `_SRC_OVERRIDE` cannot reach them in a scratch tree. Intentional (`prove_net` children have
  `HERE` = scratch), or route them through `_srcdir`?
- **Q2.** `every_ollama_call_site_takes_a_lane_turn` (20976) globs only top-level `src/*.py` and
  `HERE`. `src/deprecated/catalogue_local.py:211` posts to `/api/generate` with no lane. It refuses
  to run, so moot today, but `_src_py_files`'s own doctrine says a deprecated directory is where a
  bypass would be least looked at. Exempt on purpose (like `_eaten_escape_roster`), or walk it?
- **Q3.** `_gate_closed_shelf_holds` (13535) writes `state/drill_gate_closed_shelf.json` through
  plain `silence.write_json` (atomic, not compare-and-swap) and the path is not in `_live_watch()`.
  Only reachable while the prose gate is CLOSED (it is open now); two concurrent drills on the first
  closed sighting could record different baselines. Acceptable, or CAS it?
- **Q4.** `_live_watch()` (15398) is still a hand-kept list (sweep63/66 question); a state file a
  probe writes that is not on it is invisible to the audit hook.

## Cleared (read in full, no defect)

Import-time witness (`_spy_record`, `_spy_flush`, `_LEDGER_BEFORE`, `_not_a_leak`, 47-212);
`net()` / `_ATTACKS` / `_CURRENT_NET` stack; `_ledger_redirected`; `_src_mtime_preserved`;
`prove_net` / `ledger_dry_run` / `_remove_scratch_tree`; `_live_stmts` loop/else handling,
`_breaks_out_of`, `_live_walk`, `_arm_leaves`, `_gate_precedes_spawn`, `_carries_result_of`,
`_rooted_names`, `_filtered_names`; `_esc_sandbox` / `restore()` ordering and escape check;
`_live_audit` event coverage (open flags, os.rename incl. os.replace, `_winapi.CopyFile2`, Popen cwd
rule); `_LIVE_STATE_PROBES` roster and roster net; all `drill_escalation_behaviour` probes (each
restores its stubs in `finally`); `_reread_the_breaches` (fail-closed on missing attack, raise, or
any failing reading); `main()` verdict/exit-code paths (breach > unlanded stamp > `--to-halt`),
the `_busy` mutation branch, halt evidence kept under `drill_breach_<ts>.json`; the
`_HALT_WRITERS` gate matcher and its planted controls.

## Coverage

Recorded via `sweep_plan.record('run67', ['drill.py'], batch=1)` after the full read.
