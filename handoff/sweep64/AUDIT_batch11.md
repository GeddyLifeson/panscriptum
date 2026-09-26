# sweep64 batch 11 — audit

Auditor scope, read in full, start to finish, in chunks (no sampling, no grep-only passes):

- `src/overnight.py`          2026 lines
- `src/chain.py`              1262 lines
- `src/onomast.py`             844 lines
- `src/custodes.py`            714 lines
- `src/policy.py`              611 lines
- `src/axis_correlation.py`    443 lines
- `src/descending_ladder.py`   362 lines
- `src/cachekey.py`            217 lines
- `src/repass_bands.py`        214 lines

Total 6,693 lines, all read. Read-only throughout: nothing under `src/`, `data/`, `state/` or
`output/` was edited, created or deleted, except this report and the one permitted
`sweep_plan.record` call. Did not run drill.py, verify_math.py, generate.py, the pipeline,
publish, overnight, chain, mutate, or any job. Did not spawn subagents.

## Method

`CLAUDE.md` read first for doctrine (Hard Rule -1 escalation/halt, Hard Rule 0 no caps, fail
closed). Then `handoff/sweep63/` was grepped for all nine module names before reading any source;
four prior audits turned up and were read in full: `AUDIT_batch03.md` (repass_bands.py, cachekey.py
elsewhere in that sweep's batch12 pairing — see below), `AUDIT_batch11.md` (overnight.py,
custodes.py, policy.py, axis_correlation.py, descending_ladder.py — all filed as clean beyond two
now-superseded fixes), `AUDIT_batch12.md` (chain.py, cachekey.py — 0 VERIFIED, 0 SUSPECTED), and
`AUDIT_batch13.md` (onomast.py — no module-specific findings). None of those reports left an open,
unresolved finding against any of these nine files. Prior reasoning was re-verified against the
CURRENT source rather than re-derived, and nothing pre-recorded as fixed is re-reported here.

Special attention was paid, per this batch's brief, to `chain.py`'s `_RECIPE_KEY` mechanism
(order 058fa19d4e65), tracing it end to end: digest computation (`_harvest_recipe_digest`),
invalidation check and whole-index reset (`harvest()` lines ~372-387), exclusion from the prune
loop and the row-collection loop (lines 456, 472-474), and exclusion from `refresh_continuity`'s
patch loop (line 551). The mechanism is sound on its own — but see Finding 1 below for an
interaction it does not account for.

## Findings

### 1. SUSPECTED — `chain.py`, `harvest()`: a recipe-invalidation reset permanently (until the
root is next reachable) discards a currently-unavailable corpus root's cached rows, while the
pass's own stderr message claims those rows are held and reused

`_corpus_root_state()`'s whole purpose, per its own docstring, is that "one unreadable mount ...
[must not read] as 'the whole feats corpus was deleted'" — an unavailable `data/readfeats` or
`data/feats` root has its index entries HELD rather than pruned (lines 401-412), and the pass
prints:

```python
print(f"chain: data/{base} could not be listed this pass (locked? offline mount?). "
      f"Its index entries are HELD rather than pruned, and this harvest re-uses the "
      f"rows cached for them; nothing under it was re-read.", file=sys.stderr)
```

That promise depends on `idx` still holding those rows when the prune loop runs. But when the
extraction recipe has just changed (`_RECIPE_KEY` mismatch, lines 379-387), `harvest()` discards
the ENTIRE index first:

```python
if idx.get(_RECIPE_KEY) != recipe:
    if idx:
        ...
    idx = {_RECIPE_KEY: recipe}
    updates[_RECIPE_KEY] = recipe
```

This runs *before* the per-root loop that checks `_corpus_root_state(base)`. So if the recipe
changed on the same pass that one of the two corpus roots happens to be transiently unlistable
(a Norton lock, an offline mount — exactly the scenario `_corpus_root_state` exists for), the
"held" root's message is printed over an `idx` that no longer contains any rows for that root at
all — they were erased by the reset three dozen lines earlier, not preserved. The prune loop
(line 456) then has nothing to hold for that base (there is nothing left to prune), and
`_land_harvest` writes the reset-and-rescanned `idx` back to `state/chain_harvest_idx.json` with
that root's contribution silently absent from the returned `rows` for this pass — indistinguishable
from the exact "whole feats corpus deleted" failure mode the held/unavailable state was built to
prevent, and it will read as such in `data/CHAIN.json`'s contest graph until the next pass in
which that root is reachable (which would then repopulate it on a mtime cache-miss).

**Concrete failure scenario.** OUTCOME's pattern is widened again (as it was in run #58 and the
2026-09-09 `beat` fix) at the same moment `data/feats` sits on a locked/offline mount for one
harvest pass. That pass: (1) sees the recipe mismatch, resets `idx` to `{_RECIPE_KEY: recipe}`;
(2) finds `data/feats` unavailable, appends it to `held`, and prints that its rows are "HELD ...
and this harvest re-uses the rows cached for them" — false, there are now zero cached rows for it
in `idx`; (3) globs only `data/readfeats` successfully and rebuilds from that; (4) `_land_harvest`
persists the reset index, which has no entries under `data/feats/**` at all. `data/CHAIN.json`'s
contest graph for that cycle is missing every `data/feats`-sourced contest, silently, under a
console/stderr message asserting the opposite. Self-heals the next time `data/feats` is listable
(cache miss on every file re-populates it), so this is a transient-but-silent gap rather than
permanent corruption — but it is the one gap this module's own `_corpus_root_state` mechanism was
purpose-built to make impossible, reopened at the specific intersection with a recipe change.

**Not triggered on an ordinary pass.** When the recipe is unchanged, `idx` is loaded from disk
intact and the held-root's rows survive in it exactly as documented; the interaction requires both
conditions (a recipe change AND a corpus root unavailable) on the same invocation, and `changed`
is what gates whether a write happens at all — on a plain recipe change with no unavailable root,
nothing is lost.

**Verified by:** tracing `harvest()` line by line (373-489), confirming the reset at 384-387 runs
unconditionally before the per-root loop at 400-412, and confirming the prune loop at 456 and
`_land_harvest`'s CAS write have no mechanism to recover rows already dropped by the reset.

**Suggested fix (not applied — read-only batch):** capture which roots are unavailable BEFORE
resetting `idx` on a recipe change, and re-seed the reset index with that root's PRIOR entries
(under the old recipe, clearly marked stale) rather than dropping them outright — or, more simply,
have the stderr message for a held root under a fresh recipe-reset say so explicitly ("held, but
this pass's recipe reset means there is nothing to hold") instead of asserting preservation that
did not happen.

## Everything else in the batch

No other new instance of the priority classes (checks that cannot fail, fail-open guards,
Hard-Rule-0 caps/truncations, real logic bugs, `prose_enabled`/`step4_enabled` gate weakenings,
regex/escape corruption, silent exception swallowing that manufactures a negative, dead code
claimed live) was found in any of the nine modules, beyond what each file's own inline history
already records as found-and-fixed. Specific things traced and ruled out:

- `overnight.py`: the prose-start gate (`drill_rc == 0` starts, `== 1` logs a halt, anything else
  — including `None` — refuses and logs "whether a net is breached is unknown") is fail-closed on
  all three arms, matching sweep63 batch11's verified fix. `_manager_stopped`, `_guarded_popen`'s
  spawn-lock serialisation, `running()`/`_cmd_is_running()`/`_in_this_tree()`'s quote-aware,
  run-vs-mention distinction, the keeper thread's blind-probe/manager-stop exclusions, and the
  cycle loop's idle-vs-halt arithmetic (including the "halted is not broken" branch and its
  fail-closed `except` around `escalation.status()`) were all hand-traced and hold as documented.
- `chain.py`: beyond Finding 1, the `_RECIPE_KEY` mechanism is otherwise sound — the digest
  excludes itself correctly from both the prune loop and `refresh_continuity`'s patch loop, and a
  missing key is correctly treated as a mismatch (never a coincidental match). `_land_harvest`'s
  compare-and-swap re-read/re-apply, `adjudicate_mutuals`'s four-way epoch disposition, and
  `extract()`'s malformed-model-output guards (non-dict outcome, bad index, out-of-range index)
  were traced and are correct.
- `onomast.py`: `name_worlds`'s append-only carry-forward, the standing-vs-retired distinction,
  `land_onomasticon`'s compare-and-swap with re-run-on-conflict, and `coin_well_formed_stamped`'s
  three-tier fallback (ordinary walk, extended salt space, digest-tail-suffixed last resort) all
  match their documented behaviour. `register_for`'s weighted-voting tie-break is correct but
  confirmed still unreached in production (one positional argument from `name_worlds`), as the
  module's own docstring already states — not re-filed as a finding.
- `custodes.py`: `_custos_reading`'s private per-call weight table (no shared-state mutation),
  the abstention/attendance plumbing for Lumen and Threnody, and `convene()`'s interval
  construction (`half = max(1.96*sd, max|v-consensus|)`, widened by transit dispersion only
  through the one dof that has a mechanism for it) were traced and hold.
- `policy.py`: `OPS`/`TYPES`/`ARG_REQUIRED` remain closed sets with malformed-rule refusal at
  load, `check_rule`'s absent-vs-null distinction, and the two-exit-code contract (`1` for a rule
  failure or unreadable document, `2` for a landed-report denial) in `main()` are all consistent
  with their documentation.
- `axis_correlation.py`: `_scores_of`'s bool-exclusion on both stored shapes, `observations()`'s
  missing-vs-unreadable source tracking, `rho()`/`widening()`'s single-`load()`-per-call sentinel
  doc (no longer re-firing `_no_matrix` 55 times), and `write()`'s gated verdict were traced and
  hold.
- `descending_ladder.py`: confirmed still HELD/unwired by design (order `66f96febdb3a`) with no
  caller anywhere in `src/`, exactly as its own docstring states. `rung_for_length`'s domain
  guards at both ends and the U-shaped (non-monotonic) `binding_J` column's documented
  not-a-lookup-key status were re-verified by hand-tracing the boundary loop.
- `cachekey.py`: `load()`'s verify-before-trust (entity, optionally host), `write_path`'s
  collision-vs-unreadable-vs-free disambiguation, and `provenance_ok`'s three-way
  proven/changed/unverifiable return were traced and are correct.
- `repass_bands.py`: the write-then-gate-on-`write_record()` pattern (denials counted, not just
  printed), and the preserve-not-destroy handling of a demoted `scale_note` (setting the
  `scale_note_rejected` companion rather than silently blanking it) match their documented intent.

## Questions

None met the bar this batch. The design questions already on record in the source
(`descending_ladder.py`'s held-not-wired status, `onomast.py`'s `register_for` not yet receiving
genre/feature arguments, `custodes.py`'s Threnody veto never firing in production, `policy.py`'s
unfired `ARG_REQUIRED`/`is_type` landmine-for-the-next-table framing) are pre-existing and already
named as open in the code itself, not new territory this batch surfaced. No `prose_enabled` /
`step4_enabled` gate was touched, recommended for change, or found weakened in any of the nine
modules.

## Coverage

Recorded via `sweep_plan.record('run64', ['overnight.py', 'chain.py', 'onomast.py',
'custodes.py', 'policy.py', 'axis_correlation.py', 'descending_ladder.py', 'cachekey.py',
'repass_bands.py'], batch=11)`.
