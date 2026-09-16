# sweep60 batch 14 — audit

Modules read in full, uncapped: `src/read.py` (1691 lines), `src/health.py` (1319 lines),
`src/liveness.py` (1058 lines), `src/thread_integrity.py` (721 lines), `src/policy.py` (611
lines), `src/pick_model.py` (449 lines), `src/grounding.py` (361 lines), `src/tells.py` (303
lines). Total 6,513 lines, all read start to finish, no sampling.

## Overall impression

This batch is unusually hard to find live findings in. All eight modules are already written in
the project's own "narrate every past defect at the site of its fix" style, and most of the
mechanical shapes the sweep is hunting for (tautologies, fail-open guards, dead caps) are already
present in the text as *documented, fixed* history rather than as live bugs. I verified several of
those historical claims against the current source rather than taking them on faith (see below).
I did not find any live tautology, fail-open guard, or truncation in these eight files. I did find
one confirmed, verifiable finding, in `liveness.py` itself, plus one unverified/speculative note.

## Finding 1 (MINOR, verified) — `liveness.py`'s own docstring contradicts the code it sits beside

**Location:** `src/liveness.py:432`, inside `scan()`'s docstring.

**Quote:**
```
430    The one new finding, `context_budget.py:276 report()`, is GENUINE: no caller of any spelling
431    exists in `src/`, confirmed by grep as well as by this pass. It was already suspected before
432    this landed (see the order's own text) and is left standing rather than filed by hand,
433    because the point of the order was the DETECTOR, and a hand-filed instance is what having no
434    instrument looks like.
```

This is now false, and I verified it three ways:

1. **Ran the tool.** `python src/liveness.py` (miniconda python) today reports 38 DEAD functions,
   and `context_budget.py`'s `report()` is **not** among them.
2. **Found the caller.** `src/drill.py:2169` does `import context_budget as CB` inside the nested
   function `an_unmeasurable_scaffold_never_yields_a_budget` (itself registered as a `net(...)`
   test, sweep58-batch04), and `src/drill.py:2194` calls `CB.report(cfg)` inside that same scope.
   That is exactly the per-function-aliased-import shape `_credit_attrs`/`_scope_aliases` in this
   same file are built to resolve, and it does resolve it: `context_budget.report` now lands in
   `used_by_module["context_budget"]`, which is why the live scan no longer flags it.
3. **Checked the line number too.** `def report(cfg):` is at `src/context_budget.py:305` today,
   not `:276` as the docstring still says — the function has moved since this paragraph was
   written, on top of having gained a caller.

So the docstring's citation is stale in both the fact it asserts (dead vs. alive) and the location
it cites (276 vs. 305), and the assertion sits directly beside the code whose current output
contradicts it. This is exactly the shape `liveness.py`'s own opening thesis warns about — "a
check that cannot fail looks exactly like a check that passed" — turned into "a claim of a
finding that no longer holds looks exactly like a still-valid one," inside the file whose entire
job is catching stale/contradicted claims. It does not affect the detector's *behavior* — `scan()`
computes the real answer fresh every run regardless of what its own docstring says — so this is a
documentation-only defect, not a functional one. But given CLAUDE.md's standing lesson and this
file's explicit self-appointed role, I'm flagging it as the most on-theme finding in the batch.

**Fix shape (not applied, per audit rules):** either drop the paragraph (it was "kept as the
record of the order," not load-bearing) or update it to say the finding was real *at the time*
and has since been resolved by a later commit (order landed in drill.py), rather than asserting
present tense "is GENUINE" with a line number that no longer matches.

## Finding 2 (unsure / speculative, not verified live) — `liveness.py`'s `EXEMPT_PREFIXES` is a blanket exemption with no per-entry reason

**Location:** `src/liveness.py:82-83`:
```
82  # Prefixes for tool callbacks dispatched by name through a table rather than called directly.
83  EXEMPT_PREFIXES = ("t_", "test_", "cmd_", "phase_", "check_", "drill_")
```

Every other exemption table in this file (`EXEMPT`, and the `EXEMPT_MODULES`/`EXEMPT_CLASSES`
tables added later) carries a reason *per entry*, with the file's own stated policy being "a bare
skip-list rots into a place to hide findings; a reason makes each entry answerable." This table is
the one exception: six prefixes, one collective comment, no per-prefix justification. A
module-level or class function anywhere in `src/` named e.g. `check_something_nobody_calls` would
be silently exempted from the DEAD pass by prefix alone, with no verification that it is actually
a dispatch-table callback rather than genuinely dead code. I checked the files in *this* batch
(`health.py`'s five `check_*` functions are all real entries in its own `CHECKS` list, so they'd
be correctly credited as used even without the exemption) and found no live instance of this gap
firing wrongly in this batch. I did not check the rest of `src/` for a `check_`/`phase_`/`cmd_`/
`drill_`-prefixed function with zero real callers, so I cannot say this is currently hiding
anything — flagging it as a structural false-negative surface worth a targeted grep
(`grep -rn "^def \(check_\|phase_\|cmd_\|drill_\|t_\|test_\)" src/*.py` cross-referenced against
real call sites) rather than as a confirmed finding.

## What I checked closely and found clean (no live instance, but worth recording so it isn't re-asked)

- **`liveness.py`'s own worked-example bugs** (the `if seen else set()` conditional that could
  never take its else branch, the `(a,b) in seen` check that could never be true) are both already
  fixed in the current source — verified by reading the code at the cited locations, not just
  trusting the comment.
- **`thread_integrity.py`'s `classify()`** — the historical "asymmetry decided by dict iteration
  order" bug (order 7bffb5634d7a) is fixed; both `(a,b) in recorded` and `(b,a) in recorded` are
  tested. The `recorded=None` branch that makes ASYMMETRIC-LAWFUL/SUSPECT permanently unreachable
  today is deliberate (Hard Rule 5 — no directed thread graph exists yet) and is stated as such.
- **`policy.py`'s `OPS` table** — `is_type` correctly excludes `bool` from `int`/`float` matches;
  `absent` correctly tests `found` rather than `value is None`; `nonempty` no longer raises
  `TypeError` on an unsized truthy value. All three were named as historical bugs and are fixed.
- **`read.py`'s transport ladder, gate/semaphore logic, and chunk caching** — read start to end;
  the nested-acquire re-entrancy guard (`_card_gate`), the per-writer temp-file naming, and the
  entity-in-cache-key fix are all consistent with their own docstrings and with each other.
- **`pick_model.py`'s `FAMILY_TIERS` matching** — order-dependent substring matching is correct
  because tiers are checked outer-to-inner (5 before 4 before 3...), so a more-specific string in
  a *lower* tier list can never incorrectly out-rank a real match already found in a higher tier;
  verified by hand-tracing `qwen2.5:14b`, `phi3.5`, `llama3.3` against the table.
- **`grounding.py` and `tells.py`** — both fully uncapped per Hard Rule 0 (verified: no `[:N]`
  slicing anywhere in the reporting paths; `classify_text`'s `top` parameter defaults to `None`
  and the one place it's still a number, it's clearly a diagnostic display cap not a computation
  cap). No live tautologies or phantom guards found by hand-reading (the actual `liveness.py`
  scanner independently confirms 0 tautologies and 0 phantoms tree-wide, for what that's worth as
  corroboration, not proof, of these two files specifically).

## Coverage note

I ran `python src/liveness.py` (no flags) once as a live cross-check while auditing `liveness.py`
itself — read-only, no `--reachability`, no writes to `state/`. No files under `src/` were
modified.

## Summary of findings by severity

- MINOR (verified): 1 — stale self-contradicting docstring citation, `liveness.py:432`
  (`context_budget.py:276 report()` claim is now false; function has a caller and moved to line
  305).
- UNSURE (not verified live): 1 — `liveness.py:82-83` `EXEMPT_PREFIXES` is an unreasoned blanket
  exemption; no confirmed live instance found in this batch's files.
- No fail-open guards, no dead caps/truncations, no other tautologies or ordinary bugs found in
  these eight files.
