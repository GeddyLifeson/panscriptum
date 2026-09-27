# sweep65 batch 01 — AUDIT

Scope: `src/drill.py` (24,019 lines as of this read, `if __name__ == "__main__":` at line
24018-24019). Read sequentially, start to finish, via the Read tool in ~1,000-line chunks from
line 1 through line 24019. No sampling, no grep-driven skimming; every line passed through the
context window in order.

Previous audits of this module: `handoff/sweep64/AUDIT_batch01.md` (0 CONFIRMED/SUSPECTED
findings, 1 QUESTION, full sequential read at 23,831 lines), `handoff/sweep63/AUDIT_batch01.md`
and `handoff/sweep61/AUDIT_batch01.md` (both 0/0, full sequential reads at 23,728 and 23,532
lines respectively). This sweep re-read the file in full end to end rather than trusting any of
those verdicts, per the brief's instructions.

## Method

Read every line via the Read tool in sequential offset/limit chunks (no chunk skipped, no
line range re-derived from a diff). Cross-checked the module's own reasoning against its
described history (the many `order <hex>` citations, the "watched go red" claims, the fixture
shapes) for internal consistency rather than assuming the prose is accurate. Paid particular
attention to the classes of defect the brief names: inverted conditions, off-by-one, swallowed
exceptions where the code claims fail-closed, guards that cannot fail, truncation/caps, stale
comments, dead branches, wrong units, Windows-specific breakage, and races on shared files —
this file's own stated purpose is finding exactly these in the rest of the codebase, and it
carries an unusually large amount of documented history of having had each of these mistakes
made and repaired inside itself, which is both reassuring (many classes are covered) and a
reason to look harder rather than skip on the strength of the prose.

Traced a sample of the reachability/AST-walking primitives this file's ~350 nets are built on
(`_live_stmts`, `_live_walk`, `_arm_leaves`, `_gate_precedes_spawn`, `_carries_result_of`,
`_is_rooted`, `_rooted_names`) against their own docstrings, the fixtures that exercise them
(`the_reachability_primitive_understands_loop_else` and neighbours), and their call sites, and
found them internally consistent with the properties claimed for them. Checked `state/workorders.json`
for existing open orders before writing anything down, per the brief.

## Findings

**0 CONFIRMED, 0 SUSPECTED.**

I did not find a new defect in `drill.py` in any of the classes the brief lists: no inverted
condition, no off-by-one, no exception silently swallowed where the code claims to fail closed,
no guard that cannot fail, no truncation/cap on a roster or list, no comment asserting something
the code no longer does, no dead branch reachable in a way that matters, no wrong unit, and no
Windows-specific breakage (the file is itself unusually careful about `CREATE_NO_WINDOW`,
`psutil` vs. bare `os.kill(pid, 0)`, and WMIC's absence — see `_liveness_probes_answer_correctly`,
`_the_process_listing_sees_its_own_process`, and the `_KNOWN_KILL0_SITES` ratchet).

This matches all three prior sweeps of this file.

## Questions (possible deliberate design)

- **Already open, not re-filed** — `drill.py:_catalog_matches_disk` (~line 12496), the
  `os.path.isabs(p)` branch: if a `catalog.json` entry's `raw_path` were ever absolute,
  `_catalog_matches_disk(root=<sandbox>)` would check that entry against the live filesystem
  instead of the sandbox it was asked about. Not reachable today — the only production writer of
  `raw_path` (`generate.py:1215`) always writes a relative path via `os.path.relpath`. This exact
  question is item 3 of the open order "SMALL QUESTIONS FROM SWEEP64" in `state/workorders.json`
  ("drill._catalog_matches_disk resolves an ABSOLUTE raw_path against the live filesystem
  whatever `root` is ... Resolve against root, or drop the branch?"), so it is not re-filed here.
  Re-verified against today's source: unchanged since sweep64.

No new questions found beyond that one.

## Cleared

Examined closely and found correct (a representative sample of the ~350 nets and the shared
machinery, not an exhaustive list — the whole file was read, this is what stood out as worth
naming):

- `_live_stmts` / `_live_walk`'s handling of `if True:`/`if False:`, `while True:`/`while False:`
  fall-through and `else` reachability (lines ~1130–1305) — matches its own documented history of
  three separate repairs (sweep36, sweep43-batch01, order 7baa1527f69c) and the fixtures at
  `the_reachability_primitive_understands_loop_else` exercise all four shapes correctly.
- `_arm_leaves`'s per-exit-type loop/function scoping (Continue/Break bound to the innermost
  loop, Return to the innermost function, Raise propagating through both) — line 1312-1355,
  correct per its own worked example and order 515eb8cae3c2's fixture.
- `_gate_precedes_spawn` (three-part interlock check: answer bound, guarded `if` leaves by the
  right exit, every spawn strictly after and outside the guard) — used consistently by the
  keeper/launcher nets and by `the_copy_loop_actually_asks_the_gate`'s sibling reasoning; the
  ordering check `s.lineno > g.lineno` combined with the `inside` id-set correctly excludes a
  spawn nested inside the guard itself.
- `_esc_sandbox` / `_esc_probe` and THE LIVE-STATE WITNESS (`_no_sandboxed_probe_reaches_live_state`,
  `_every_sandboxed_probe_is_driven_by_the_witness`) — the redirect table, the assertion that
  every redirected constant actually lands under the sandbox root before any probe runs, and the
  audit-hook-based leak detector are consistent with each other and with the two-witness design
  (ledger-record spy + ledger-flush spy) described at the top of the file.
- `main()`'s exit-code / halt / re-read-before-halting sequencing (`_reread_the_breaches`,
  `_wait_for_a_settled_tree`, the mutation-active check, the maintenance-guard exclusion) — the
  ordering of checks (mutation-active first, then re-read on settle, then halt) matches the
  documented incidents (run #45, run #46, 2026-08-25) it was built to stop recurring, and the
  maintenance guard is genuinely never consulted in that path (verified by reading
  `_reread_the_breaches` and `_wait_for_a_settled_tree` in full — neither mentions
  `maintenance_run` or `MAINTENANCE_RUN` anywhere in their bodies).
- The eaten-escape guard (`_BAD_CHARS` check at the top of the file, lines 34-36) and the
  `_eaten_escape_roster` / `_carries_eaten_escape_guard` AST-based ratchet — self-consistent, and
  `drill.py` itself carries the guard it enforces on other modules.

## Coverage

Recorded via `sweep_plan.record('run65', ['drill.py'], batch=1)` with the miniconda python after
this file was read in full, start to finish.
