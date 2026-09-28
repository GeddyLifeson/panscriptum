# sweep66 batch 01 — AUDIT

## Scope

`src/drill.py`, 24,072 lines (`if __name__ == "__main__":` at 24071-24072). Read sequentially
with the Read tool in 1,000-1,150-line chunks from line 1 to line 24072, no chunk skipped and
no grep-driven skimming. Read-only: nothing under `src/`, `data/`, `state/`, `output/`,
`prompts/`, `reference/` or the repo root was edited. Three findings were reproduced with a
standalone script kept in the session scratchpad (`sweep66_b01_repro.py`). It imports `drill`
with `_REAL_RECORD`/`_REAL_FLUSH` stubbed out so nothing reaches the live ledger, and it writes
only under `%TEMP%`.

## Prior-audit cross-check

- `handoff/sweep65/AUDIT_batch01.md` reported 0 findings and 1 question. That question was
  `_catalog_matches_disk` resolving an absolute `raw_path` against the live filesystem. It is
  **still standing**: the code at 12548 is unchanged. It is **already open** as item 3 of the
  order "SMALL QUESTIONS FROM SWEEP64".
- Sweep63 questions 1 and 2 in the order "SMALL QUESTIONS FROM SWEEP63" are **still standing**
  and **already open**:
  - `_reread_the_breaches` retries once and drops the halt if the net then holds (23564-23628,
    unchanged).
  - `_live_watch`'s path list is hand-kept (14048-14080, unchanged apart from the chain
    singleton row).
- The open order about sandboxed probes defined as closures inside area functions is **still
  standing**. `_every_sandboxed_probe_is_driven_by_the_witness` restates that limit in its own
  docstring.
- The sweep65 "Cleared" items were re-read and still hold: `_live_stmts`/`_live_walk` loop
  handling, `_arm_leaves`, `_gate_precedes_spawn`, the sandbox/witness pair, and main()'s
  re-read ordering.

## Findings (defects)

### D1. A "declined measurement" note trips the ledger witness, so an unstageable probe HALTS the library. VERIFIED.

Several nets were rewritten under the ruling "a measurement that did not happen is NOTED and
returns True". Two examples:

- `_junction_out_of_the_writable_surface`, order ef0b67732a3b.
- `datasette_config_is_generated_not_copied`, order 5eea5c20db8a.

They note through `silence.note`. Later, the whole-run ledger witness was installed at import:
`_H.record = _spy_record` (drill.py:134). `silence.note` does `import health;
health.record(...)` (silence.py:1069-1072), so every such note lands in `_LEDGER_ESCAPES`. At
the end of the run, `no_probe_writes_into_the_live_failure_ledger` (23441-23450) raises on any
entry. The re-read re-asks the same net against the same non-empty list, so the breach
reproduces and `main()` escalates DRILL_BREACH at OWNER (24033).

Sites that note on a path documented as "not a breach":

- `paid_access_stays_switched_off`, 13366/13369/13372. Example:
  `_si.note("drill.py:paid-lane-config-absent"); return True  # not this machine`.
- `_junction_out_of_the_writable_surface`, 4717/4721.
- `_junction_to_an_unlisted_but_undenied_place`, 4794/4806/4810.
- `_twins_ignores_a_foreign_tree`, 13177/13193/13211.
- `_a_hardlinked_data_file_is_a_frozen_snapshot`, 20711.
- `datasette_config_is_generated_not_copied`, 22082.
- Every probe-cleanup note that its comment says must not fail the net: 4454, 4565, 4587, 5094,
  5144, 8166, and 22335/22372.

**Repro:** set `PANSCRIPTUM_CASCADE_CONFIG` to an absent path, then run `drill_no_top_ups()`.
The paid-access net reports HELD, and `_LEDGER_ESCAPES` gains
`drill.py:13366 [the cascade never switches paid access on] -> silent:drill.py:paid-lane-config-absent`.
The witness would then raise.

This is latent on this machine because `~/cascade/config.json` exists. It is live on any machine
without that file, without psutil, or without `cmd`/junctions. It also fires on any transient
cleanup lock, which this file itself says is ordinary on this machine (Norton, scanners holding
files).

The file already knows the right shape. `_verify_notices_a_member_missing_from_the_archive`
(20833) records its declined measurement in `_DECLARED_ESCAPES` "rather than the ledger". The
other sites were never moved to it.

Not already open: a search of `state/workorders.json` for `unstageable`, `paid-lane`,
`hardlink-unsupported`, `datasette-config-unwritable` and `probe-cleanup` finds nothing.

### D2. `_meta_ban_has_no_fall_through` is satisfied by a gate parked in dead code. VERIFIED.

At 9548-9555, the "gate must still be there" floor is found with `ast.walk` over the `try`
body, and the handler check at 9572 reads `h.body[-1]`. Neither is reachability-scoped. This is
the same defeat that orders 78f04bec15ad and c54a22a4e6fc removed from its siblings.

**Repro:** a scratch `generate.py` whose `try` body is `if False:
pipeline.assert_in_universe(...)`, with `except Exception: continue`. It returns **True**, so
the P8 gate is absent at run time and the net holds. The sibling net
`the_meta_language_ban_is_actually_enforced` does use `_reaches_call` from `main`. That makes
this a second layer with a weaker failure mode, not a hole in coverage today. It is still a net
whose printed claim ("no handler falls through to the write") cannot see the gate's deletion.

### D3. `overnight_prose_needs_a_clean_drill` is an exists-check, not a for-all. VERIFIED.

At 12707-12721, only `start("prose", ...)` statements that sit directly in the body of an `If`
are examined. An unguarded `start("prose", ...)` anywhere else (loop body, function body, an
`else` arm) is invisible, and the check returns True as long as one guarded start exists. This
is the quantifier defect this file has fixed twice elsewhere: orders 5ed81099fc49 and
8ab131910911.

**Repro:** a fixture with one guarded start plus a second start inside a `for` returns
**True**. The live `overnight.py` also returns True, so this is not a present fault in the
guarded code. The `drill_rc == 0` test is also a substring of `ast.unparse(test)`, so
`drill_rc == 0 or True` passes. It is the net the prose gate's drill interlock leans on.

### D4. `_scope_lands_key_wise` leaks a temp directory on every drill run. VERIFIED.

At 9904, `d = tempfile.mkdtemp()` has no `rmtree` anywhere in the function, and no prefix.
Measured now: **707** `%TEMP%\tmp*` directories contain a `SCOPE.json`, which is one per drill
run. Its sibling nets were repaired for exactly this under order d015e0a139a8 (see 22399-22403),
and this site was missed.

### D5. `gate_claim_matches_reality` prints a claim it can no longer test. VERIFIED by reading.

The net at 12574-12586 is titled "the gate says CLOSED and the library is genuinely empty of
prose". Its body returns True whenever `PG.gate_open()[0]`. `drill_dispatch` pins the gate OPEN
since 2026-09-16 (1982-1985), so the net currently cannot fail. The early return is deliberate;
the stale title is the defect.

The companion docstring of `_catalog_matches_disk` (12524-12536) likewise still says "the prose
gate is closed by owner ruling" and "holds once the gate is open again".

## Questions (possibly deliberate; owner decides)

- **Q1.** `_carries_result_of` (1546) runs its fixpoint for at most 8 passes, while its siblings
  (`_filtered_names`, `_rooted_names`, `_no_programmatic_clear`) iterate to a true fixpoint. A
  longer out-of-order binding chain yields a smaller set. That fails toward a false BREACH, not a
  pass. Deliberate bound, or align it with the siblings?
- **Q2.** Several source-shape nets read the live file directly rather than through
  `_srcdir(src)`, so `_SRC_OVERRIDE` does not reach them:
  - `_no_programmatic_clear` (5273), `_publish_never_swallows_a_missing_safety` (5751),
    `_withdrawal_takes_a_snapshot` (8302), `_counts_decided_by_substring` (18204),
    `_no_new_bare_kill0_probe` (18788) and `_a_module_claimed_wired_is_actually_imported`
    (18865).
  - `generate_lands_catalog_every_chapter`, `overnight_prose_needs_a_clean_drill` and
    `throttle_iterates_a_snapshot`, which use `HERE/src`.

  In a `prove_net` child, `HERE` is the scratch root, so proofs still work. Intentional, or
  should they all route through `_srcdir`?
- **Q3.** Two halt-interlock nets run outside `_esc_sandbox`:
  - `the_tool_that_deletes_mined_evidence_asks_about_the_halt` (14817) ends by calling
    `HC.sweep(repair=True)` for real with the halt removed.
  - `the_document_ingester_asks_about_the_halt` (14886) calls `ID.register(...)` for real with
    the halt removed.

  Their stubs redirect the obvious writes, but nothing audits what else those calls touch. Should
  they be in the sandbox so the audit hook watches them?
- **Q4.** "WHY 57 NETS MISSED IT" (5547) is the stale count CLAUDE.md already cites (ruling
  864a626a258e). Left as history on purpose, or should it be reworded?

## Coverage

Recorded via `sweep_plan.record('run66', ['drill.py'], batch=1)` after the full read.
