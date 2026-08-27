# Run35 batch 1 audit (agent scope: src/assay.py, src/custodes.py, src/rigor.py)

## 005ae867941c -- rigor.py's ceiling-confidence prose was stale against pipeline.py

Confirmed real by reading `pipeline.synthesis_blocks` (pipeline.py:837-889) directly: the
2026-08-25 owner ruling removed the `rest[:14]` cap, so the fallback path now blocks *every*
entry (`rest[i:i+14] for i in range(0, len(rest), 14)`) and `phase_synthesis` (pipeline.py:907
`for ci, sample in enumerate(chunks)`) iterates every block rather than reading only the first.
`rigor.ceiling_confidence`'s docstring and its `"sampling"` string still asserted a fixed
"14 LONGEST descriptions" sample, and `main()`'s section 5 print block repeated the same stale
claim. Fixed in `rigor.py`: rewrote the docstring to describe the current mechanism (full
coverage on a completed pass, `n_scored` a genuine partial-sample count only on an interrupted
one), made the returned `"sampling"` string reflect `complete = n_scored >= n_entries` instead
of a hardcoded constant, and rewrote the `main()` section 5 header/prints to stop claiming 14 is
what a completed pass does. Verified `verify_math.py:429-430`'s two existing checks
(`"NOT random" in sampling` and `supports_decimal is False`) still pass unchanged against
`ceiling_confidence(900, 14)` -- confirmed by direct call, not by running verify_math.py. No
edit to verify_math.py was needed or made.

## 02277646a783 -- assay.py's `_check_constants` ceiling branches -- LEFT FOR OWNER

Confirmed the arithmetic claim exactly: `SIGMA_MAX = SIGMA_BY_ATTESTATION["Disputed"]`,
`SIGMA_UNKNOWN = SIGMA_MAX`, and the monotonicity check just above (`vals != sorted(vals)`)
already forces `Disputed` (last in `order`) to be the maximum of the five values before either
of the two ceiling branches runs. So `SIGMA_UNKNOWN < max(vals)` and `max(vals) > SIGMA_MAX`
cannot be made True by editing `_RAW_SIGMA` -- exactly as the order states. But this is not a
simple dead-code deletion: the long comment immediately above (`SIGMA_MAX`'s definition)
explains at length *why* the ceiling was deliberately re-derived from the attestation table
instead of kept as the old independent `9.9/sqrt(12)` uniform-prior bound -- that old,
independent ceiling is the exact bug the 2026-08-25 rewrite fixed (it made the charter's own
calibration point unreproducible). The two branches in `_check_constants` are therefore not
protecting against `_RAW_SIGMA` drift (monotonicity already does that); they read as a
regression guard against `SIGMA_MAX`/`SIGMA_UNKNOWN` ever being reassigned to an independent
value again -- the specific historical bug this file already had. The identical tautology is
also asserted a second and third time, unowned by this agent, in `drill.py:671` and
`verify_math.py:1583` (`A.SIGMA_UNKNOWN >= max(A.SIGMA_BY_ATTESTATION.values())`). Deciding
whether to delete/restructure/re-target these checks is a safety-net design call in a file
CLAUDE.md's Hard Rule -1 already treats with special caution (the rule exists *because* an
autonomous run once deleted a safety it judged unnecessary) and it spans three files, two of
which this agent does not own. Left open for a person; no edit made to assay.py for this order.

## 6475cb78e185 -- custodes.py's `_ATT_BASE` was the forbidden second copy

Confirmed: `custodes._ATT_BASE` (was a literal dict) was a character-for-character copy of the
`floor` dict inline inside `assay.interval_from_hands`, directly under a comment in custodes.py
claiming it was "DERIVED from assay()'s own attestation table rather than restated" -- it was
not derived, and could not have been, because the values lived only inside the function body,
never as a module-level name. Fixed by hoisting the dict out of `interval_from_hands` into a new
module constant `assay.ATTESTATION_FLOOR` (assay.py, just above `interval_from_hands`), with
`interval_from_hands` reading `ATTESTATION_FLOOR.get(attestation, 0.30)` instead of the inline
literal, and changing `custodes._ATT_BASE` to `A.ATTESTATION_FLOOR` (a real import, not a
restatement). Verified `custodes._ATT_BASE is assay.ATTESTATION_FLOOR` (same object), that
`ATTESTATION_QUALITY` and `interval_from_hands` still produce identical output to before the
change, and both files import clean and pass pyflakes.

## 873330d2e98d -- verify_math.py's four ungated negative scans -- queued, not applied

Confirmed by reading each of the four scans directly: `_ctx_literals` (S19ab), `_failopen20p`
and `_writes_the_config20p` (S20p), `_callers20t` (S20t) are each asserted `== []` with only a
parse/read-coverage net beside them, unlike the three "is actually finding X, not silently
matching nothing" positive-control checks this same file already uses elsewhere. A typo in any
of the four matchers' attribute names, string constants, or AST node types would leave all four
green forever, indistinguishable from a genuinely clean tree. This agent does not own
verify_math.py and did not edit it. Nine canary checks (one per matcher, three for the three
call-shapes `_callers20t` looks for) are appended to `handoff/run35/checks_batch1.py`, each
proving its target matcher still recognises a synthetic instance of the exact violation it was
written to catch. Where the real matcher is already a standalone function
(`_writes_the_config20p`), the canary calls that function directly. Where it is an inline loop
with no reusable entry point (`_ctx_literals`, `_failopen20p`, `_callers20t`), the canary
reimplements the identical predicate against a synthetic snippet -- a close substitute, not a
call to the production code; the comment in checks_batch1.py flags this and suggests the
coordinator factor those three inline scans into functions the same way `_writes_the_config20p`
already is. All nine were smoke-tested standalone (stubbing `check`/`os`/`_writes_the_config20p`)
and pass. Order left open pending the coordinator's merge.

## d9b895708c45 -- verify_math.py's "every standard emits a row" hardcoded floor -- queued, not applied

Confirmed: the check asserts `len(emitted) >= 40` with no reconciliation against the declared
set, exactly as the order states, and the file's own comment 25 lines later already names the
fix ("compare the emitted count against the declared set"). Measured directly (read-only, no
verify_math.py/drill.py run): `standards.py` statically declares 44 distinct standard names via
its `_s(name, ...)` call sites (one name, "calls that succeed", is legitimately reused across
two mutually-exclusive branches); `standards.check(dashboard.state())` on this checkout emits 43
of them. The one gap, `"promotions have their spine codes amended"`, is a documented, legitimate
absence -- that `_s()` call is wrapped in `try: ... except FileNotFoundError:` because it reads
`data/SHELF_RANKS.json`, and the source's own comment marks the omission
`"silence-exempt: phase 7 has not run yet"`. This agent does not own verify_math.py. Appended a
replacement check to `handoff/run35/checks_batch1.py` that statically collects the declared set
by AST (not grep, so a name split across lines or built by string formatting is flagged rather
than silently missed), diffs it against the live emitted set, subtracts the one named legitimate
exemption, and fails loud by NAME on anything else missing -- plus a companion check that the
exemption list itself has no stale entries. Smoke-tested standalone against the real
standards.py/dashboard.py; currently green with the one documented exemption. Order left open
pending the coordinator's merge.
