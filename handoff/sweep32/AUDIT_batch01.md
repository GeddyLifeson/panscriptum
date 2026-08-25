# Audit — Batch 01 — run32

**Module read:** `src/verify_math.py` — 4,430 lines, read in full end to end (line 1 through the
final `sys.exit(1)` at EOF), in 13 sequential chunks. No section was skimmed or sampled.

**Scope note:** verify_math.py is itself the test suite, so the lens was applied with maximum
suspicion per the task brief: hunting for assertions that cannot fail, vacuous-on-empty-input
checks, source-text-literal checks standing in for AST/behavioural checks, and any of this
project's known recurring defect classes (Hard Rule 0 truncation, the two-writer contract,
swallowed failures, concurrency races) inside the verifier's own code.

## Overall finding

This file is unusually self-aware: a large fraction of its ~2,700 `check()` calls exist
specifically because an earlier version of *this same file* was found to contain exactly the
defect classes named in the audit brief (tautological checks, vacuous-on-empty checks,
literal-in-source checks defeated by a comment or a reflow, a check disarmed by an
always-true disjunct, a check blind to an import alias, etc.), each with a "run #NN" note
documenting when it was found and fixed. I read every one of these self-referential fixes
looking for a fix that was itself incomplete or for a new instance of the same pattern, and
did not find one that still has the flaw its own comment describes. I did not take any of
these self-assessments on faith — each was traced to the actual code (the `check()` function,
the `_raises` helper, the AST-walking scans in §19ab/§20e/§20f/§25f, the PASS/FAIL
save-restore in §20i) to confirm the fix is real and not merely narrated.

I found **no BLOCKING or MAJOR defects**. The two findings below are both MINOR/cosmetic.

## Findings

### MINOR — src/verify_math.py:3294 and src/verify_math.py:3362 — duplicate section number "24. §20e"

```
3294:print("24. §20e  A LIVENESS REPORT MUST NOT DELETE THE REPORTER — each renderer was")
3362:print("24. §20e  NO CONSOLE WINDOWS, EVER — every child spawn must suppress its window")
```

Two unrelated sections (the `overnight.running()` self-exclusion fix, and the
subprocess-console-window AST scan) are both labelled "24. §20e" in their `print()` headers.
The same collision recurs one section later:

```
3448:print("25. §20f  RIGOR'S PROSE MUST NOT OUTLIVE RIGOR'S DATA — a section that printed the")
3500:print("25. §20f  A PERMANENT REFUSAL MUST NOT BE FILED AS CONTENTION — the auth bench")
```

Purely a print-label typo — the section numbers are informal narration only, not used by any
`check()` call, by `sweep_plan`, or by any downstream reader, so this does not affect
correctness of the test suite or its RESULT line. Flagged only because a reader (or a future
audit) trying to jump to "§20e" in the console output or in this file by number will find two
different fixes answering to it. Trivial one-line renumber (`24`→`24`/`25` and one of the pair
to the next integer) would resolve it.

### NOTE — src/verify_math.py:811 — `PR.build_all(limit=400)` is a `limit=` inside the module under Hard Rule 0's own vocabulary

```python
_rows = PR.build_all(limit=400)
check("every profile round-trips to its own address", ...)
```

This is a `limit=` argument, which the audit brief calls out by name as the project's #1 defect
class when it truncates a roster that should be verified whole. I traced this one and consider
it **not a violation**: it is not ranking-then-truncating production output, and not writing a
partial record anywhere — it is the test suite choosing to round-trip-verify 400 of
`address_space`'s addressable profiles rather than the full (much larger, ~40,000+ per its own
comment) space, on the reasoning (stated in the adjacent comment) that `encode`/`decode` is a
pure structural function of its inputs and a defect would surface on the first malformed row,
not specifically on a late one. That reasoning is sound for a *structural* round-trip property
(not data-dependent in the way a records/roster truncation would be), so I am not raising this
as MAJOR. Recording it as a NOTE only because the brief explicitly asks for suspicion of every
`limit=` without exception, and a future reader tightening Hard Rule 0 enforcement should know
this site exists and was reasoned about, not overlooked.

## Things I checked specifically and ruled out

- **Tautological / self-comparing checks (lens item 7):** AST-scanned every `check(label, got,
  want, ...)` call for `got` and `want` being textually identical expressions. Found three
  hits (`AS.map_seed(_a)` vs itself at line 760, `AS.assign(...)` vs itself at 786,
  `_ck19ah(...)` vs itself at 2881) — all three are legitimate **determinism checks** (call a
  function twice with identical input, assert the same output), which is a valid test pattern
  and not a vacuous tautology: a function seeded by wall-clock time, PID, or hash-randomised
  set/dict order would fail it. Not findings.
- **Checks gated behind a condition that can never be true:** enumerated every `if` at module
  scope; none guards a `check()` call in a way that could make it unreachable. The two
  save/restore blocks that temporarily clear `PASS`/`FAIL` (§18c/§20i) both correctly restore
  the prior tally afterward and record the probe's own outcome in a separate assertion.
- **Vacuous-on-empty-input (`if refs else True` shape):** the only `else True`/`else False`
  fallbacks in the file (lines 74, 1280, 1345) all fall back to a value that **disagrees** with
  the check's `want`, so an empty/falsy case fails loudly rather than passing vacuously.
- **Literal-in-source-text checks defeated by a comment or reflow:** the file itself documents
  three prior instances of this exact bug in its own checks (the STANDING-horizon check, the
  always-true-disjunct disarm-guard, and the `_via` metrics-line check) and replaced each with
  an AST-based check. I verified the current AST-based replacements (`_via_gets`/
  `_dict_guarded` at ~3563, the alias-resolving spawn scanner at ~3403, the
  `_writes_the_config20p` function-body scanner at ~4368) actually walk the parse tree rather
  than grepping text, and are exercised against both a positive and a negative fixture
  (e.g. `_disarmed20i`/`_ordinary20i` at ~3878) rather than merely asserted on a clean file —
  satisfying the brief's warning that "a detector nothing ever trips is not a detector."
- **Swallowed failures / bare except:** every `except Exception` in the file (lines 57, 1581,
  2523, 2822, 3069, 3679) is either the documented `_raises`/silence-exempt probe pattern or a
  `finally`-block best-effort temp-file cleanup; each is commented and none discards a result
  that should have been recorded.
- **The two-writer contract:** §18c, §19j, §20d, §20i directly exercise
  `pipeline.write_record`/`write_record_catalogue` merge directions and the torn-file refusal
  path with real temp files; no hand-rolled `path + ".tmp"` + bare `os.replace` appears
  anywhere in this module.
- **`silence.replace_retry` return-value discard:** §19m explicitly stubs `replace_retry` to
  return `False` and asserts `completeness.land()` propagates that as failure rather than
  claiming success — the exact hazard named in the brief is under direct test here, not
  swallowed.
- **Concurrency races:** the threaded probes (`_gl_probe` in §19t, the GPU-lane concurrency
  probe in §19ad) use a `threading.Lock` around every shared counter mutation; no unguarded
  shared-state mutation across threads found.
- **Mutation during iteration:** no `for x in collection: collection.mutate(...)` pattern found;
  the one place a global is mutated mid-test (`CU.CUSTODES.clear()`/`.update()` in §9) is
  wrapped in try/finally and happens between, not during, any iteration over it.

## Coverage confirmation

`record()` was run from the repo root as specified:

```
C:/Users/imarl/miniconda3/python.exe -c "import sys; sys.path.insert(0,'src'); import sweep_plan; sweep_plan.record('run32', ['verify_math.py'], batch=1)"
```

Exit code 0, no output (silent success is `sweep_plan.record`'s normal behavior — see command
output confirmation in the session transcript).
