# Sweep 30 — Batch 01 Audit: `src/verify_math.py`

Auditor: batch01 (read-only). File audited top to bottom, all 4269 lines, no sampling.
No committed secrets, API keys, or tokens found anywhere in the file (grepped for
`api_key|secret|token=|password|bearer` — the one hit is the string literal
`"invalid_api_key"` used as a *classifier vocabulary word* for recognising provider
refusals, not a credential).

## How this file reads

`verify_math.py` is not application code — it is a from-first-principles regression
suite (29 numbered sections, ~640 individual `check()` calls) that independently
recomputes every number the project's modules produce and pins ~130 previously-found
regressions with dated, narrated commit-style comments. It is unusually self-aware of
exactly the failure classes this audit's lens targets (tautological checks, caps,
swallowed exceptions, stale line-number labels) and already contains dedicated checks
*for its own file* guarding several of them (§20i's "no check in this file is disarmed
with a trailing always-true disjunct", §20e's AST scan for unguarded subprocess spawns
including its own aliased import). Given that density of prior self-correction, this
pass focused on (a) independently re-deriving several of the file's own arithmetic
checks to confirm they are not silently wrong, and (b) a mechanical sweep for the eight
lens categories rather than re-litigating already-documented history.

## Findings

### 1. Duplicate section labels / printed section numbers (LOW, REPRODUCED)

- `src/verify_math.py:2274` and `src/verify_math.py:4113` both open with
  `# ---- Section 19s: ...` for two entirely unrelated topics (the metrics-ledger
  timestamp fix vs. the prose-gate interlocks added on 2026-08-25).
- `src/verify_math.py:3294` and `src/verify_math.py:3362` both `print("24. §20e ...")`
  for two unrelated topics (the liveness-report self-exclusion bug vs. the
  no-console-windows sweep).
- `src/verify_math.py:3448` and `src/verify_math.py:3500` both `print("25. §20f ...")`
  for two unrelated topics (rigor.py's stale prose vs. the auth-bench permanent-refusal
  fix).

Reproduced by grep:
```
grep -oE '§[0-9]+[a-z]+' verify_math.py | sort | uniq -c | sort -rn | awk '$1>1'
      4 §20e
      3 §20a
      3 §19o
      2 §20k
      2 §20i
      2 §20f
grep -oE 'Section 19[a-z]+' verify_math.py | sort | uniq -c | sort -rn | awk '$1>1'
      2 Section 19s
```
(§20a/§19o/§20i/§20k's extra hits are legitimate forward-references inside later
notes/comments, not duplicate section headers — verified individually. Only the three
listed above are genuine duplicate headers/labels.)

Why it matters: this project's own §20c section (`src/verify_math.py:3227-3234`)
contains a dedicated check — `"dashboard.py carries no stale line-number silence
label"` — because a mislabeled reference cost real debugging time before. The
`verify_math.py` output itself is read by humans and by other tooling (the handoff
notes reference "run #N" and specific numbered sections when triaging); a reader told
"see section 24" or "see §20e" during triage has a 50/50 chance of landing on the wrong
one, and grep-by-label (`grep "Section 19s"`) returns two unrelated blocks.

Suggested fix: renumber the second occurrence of each duplicate (`Section 19s` at
line 4113 → `Section 19s-bis` or the next free letter; print headers at 3362 and 3500
→ `25.`/`26.` respectively, cascading the following headers by one).

### 2. `_CB` alias is rebound to a different module partway through the file (LOW–MED, REPRODUCED)

- `src/verify_math.py:1506` — `import cascade_bridge as _CB` (used through line 1583
  for `_CB.widen_candidates`, `_CB.UNRECOGNISED`, `_CB.record_unrecognised`,
  `_CB.unrecognised_open`).
- `src/verify_math.py:2211` — `import context_budget as _CB` (used from line 2216
  through 2271 for `_CB.system_for`, `_CB.feats_block_budget`, `_CB.assert_fits`,
  `_CB.measure`, `_CB.fits`, `_CB.PROSE_CHARS_PER_TOKEN`, etc.).

Every other alias reused more than once in the file (`_time`, `_tf`, `_STx`, `_RD`,
`_PL`, `_CP`) is a repeat `import X as _alias` of the *same* module — harmless. `_CB`
is the only alias in the file bound to two *different* modules. Confirmed by
cross-referencing every `import ... as _alias` occurring more than once:
```
grep -oE "import [a-z_0-9]+ as _[A-Za-z0-9_]+" verify_math.py | awk -F' as ' '{print $2}' \
  | sort | uniq -c | sort -rn | awk '$1>1'
```
only `_CB` resolves to two distinct module names on inspection of its two `import`
statements.

Currently this causes no wrong result — every actual `_CB.<attr>` reference in the file
falls strictly within the span where `_CB` means the module the author intended
(cascade_bridge before line 2211, context_budget after), and Python's straight-line
execution makes the second `import` shadow the first cleanly. But it is a live trap:
`cascade_bridge` already has half a dozen *other* short aliases scattered through the
file (`_CBm` at ~line 1073, `_cb20h`, `_CB22b`, `_cb20i`, `_cb20j`, `_cb20l`), so a
future maintainer adding a new cascade_bridge-related check anywhere after line 2211
and reaching for the already-established short name `_CB` (as every other alias in the
file invites you to do) will silently get `context_budget` instead — no ImportError,
just wrong-module attribute lookups that either raise `AttributeError` (if the names
don't happen to collide) or, worse, silently resolve to a same-named attribute on the
wrong module.

Why it matters: this is exactly the "one fact, multiple spellings, prone to drift"
shape the file's own commentary calls out repeatedly (e.g. the `entry_settled` /
`batch_settled` consolidation at §20d, the `ALL_JOBS` roster consolidation at §19p) —
except here it is the *test file itself* carrying the risk, in the one place nothing
downstream checks it.

Suggested fix: rename the `context_budget` alias at line 2211 to something distinct
from the already-heavily-used `_CB` family (e.g. `_CBX` or `_CTXB`), since
`cascade_bridge` is clearly the module family that owns `_CB`-shaped names in this
file.

### 3. Two "determinism" checks can only catch same-process non-determinism, not the class of bug the file itself demonstrates matters (LOW, structure REPRODUCED / effectiveness HYPOTHESIS)

- `src/verify_math.py:760-761`:
  ```python
  check("the map seed is derived from the address, not stored",
        AS.map_seed(_a), AS.map_seed(_a))
  ```
- `src/verify_math.py:786-787`:
  ```python
  check("assignment is deterministic",
        AS.assign("X::a", _T["Alien"]), AS.assign("X::a", _T["Alien"]))
  ```

Both call a pure function twice with identical arguments *within the same process* and
assert equality. Confirmed by AST-level scan (`find_tauto.py`, run in this session)
that these are the only two `check()` calls in the file whose second and third
arguments are textually identical after whitespace normalisation — i.e. they are not
literal `x == x` tautologies (the function really is called twice, so genuine per-call
entropy would be caught), but they are structurally incapable of catching the *specific*
failure mode this project has already been burned by once: `navtree.py`'s
`max(set(xs), key=xs.count)` tie-break, which was stable within any single process
(because `PYTHONHASHSEED` is fixed for the process's lifetime) and only diverged
*across* two separate process invocations — exactly the shape §19n
(`src/verify_math.py:1942-1972`) had to write a dedicated cross-invocation-style test
and a source-grep for, rather than a same-process double-call, to actually catch.

If `address_space.map_seed` or `address_space.assign`/`tiers.assign` build their
result from a `set(...)` or dict-iteration-order-dependent step the way `navtree.py`
used to, these two checks would read green forever in the same way the navtree bug did
before §19n — this file cannot see it, because it never spawns a second process to ask
the question the label ("deterministic", "not stored") actually promises to test. I did
not read `address_space.py` or `tiers.py` (out of this batch's scope) so I cannot say
whether they are currently at risk — flagging this as a structural gap in the *check*,
not a confirmed defect in the modules under test.

Suggested fix: either accept the narrower claim these checks actually make and rename
them (e.g. "map_seed has no incidental per-call side effect"), or — if cross-process
seed-independence is the property meant to be pinned — do what §19n did: assert against
the literal implementation shape (no unordered `set()`/dict iteration feeding the
result) via a source read, the same defence already used elsewhere in this file.

### 4. Two unlabeled `except Exception: pass` cleanup blocks (LOW, REPRODUCED)

- `src/verify_math.py:1577-1580` (cleaning up `_CB.UNRECOGNISED`'s test file in a
  `finally:` block).
- `src/verify_math.py:3632-3636` (cleaning up `_probe20g`'s atomic-write test file in a
  `finally:` block).

Both are:
```python
try:
    if os.path.exists(path):
        os.remove(path)
except Exception:
    pass
```
with no `silence.note(...)` call and no `"silence-exempt: ..."` comment — unlike every
other swallowed exception in this file (§`_raises`'s own header comment, the JSON-parse
guard at line 2523, `_json_try` at line 2822, the SIGTERM probe at line 3069), each of
which the file deliberately documents as an intentional, justified exemption from its
own "swallowed failures are noise in the one place that can't afford noise" standard.
These two are low-risk in practice (best-effort removal of the file's own throwaway
temp probes, in a `finally`, where a leftover temp file has no downstream consequence),
but they are the only two `except Exception: pass` sites in the file that don't follow
the file's own documented convention for justifying a swallow.

Suggested fix: either add the same `"silence-exempt: ..."` comment convention used
elsewhere for consistency, or replace with `os.remove(path)` guarded only by
`if os.path.exists(path)` and let a genuine `PermissionError` surface (Windows file
locks on a just-closed test artifact are the only realistic failure mode here, and a
failure to clean up a `_VM_*` probe file is itself worth seeing rather than hiding).

## Independently re-derived arithmetic (REPRODUCED clean)

Recomputed independently in a fresh Python process, matching the file's own stated
expectations exactly (not merely re-running the file, which would only prove
self-consistency):

- Earth binding energy `U=3GM²/5R` → 2.2418e32 J (want 2.24e32, tol 2%): matches.
- Sun uniform-sphere binding energy → 2.2772e41 J (want 2.3e41, tol 5%): matches, and
  correctly documented as the *wrong* (uniform-approximation) figure rather than the
  literature value the module actually uses.
- Relativistic γ at v=0.5c → 1.15470: matches.
- Continuous-Kardashev `K(1e16 W)` = 1.0 and `K(2e13 W)` = 0.7301: both match.
- Charter Kenshiro worksheet: `Σ = 5.214`, `𝔄 = 3.52`; erratum-revised
  `Σ₂ = 4.914`, `𝔄₂ = 3.49`: all four match exactly (line 147-154).

## Areas read and found sound (no findings)

- **`check()` itself** (line 63-81): the float/non-float branch correctly guards
  against `TypeError` on a non-numeric `got` against a float `want` (the exact defect
  §20i pins with a dedicated self-test at line 3788-3804, independently reproduced by
  inspection of the branch logic — `isinstance(got, (int, float))` gate before the
  `abs()` subtraction). `bool` correctly falls through the arithmetic path (it's an
  `int` subclass) rather than the identity path, matching the header comment's claim.
- **Hard Rule 0 compliance within this file**: every `limit=`/`cap=` occurrence
  (`PR.build_all(limit=400)` line 811, `BG.burgs_for(..., limit=3/200)` lines 982-985,
  `MG.candidates` stub's `cap=None` line 1075, `_rows[:3]` line 1856) is either an
  explicitly-labelled test-economy sample calling the *module's own* documented limit
  parameter for speed (not a truncation of a real listing the library would ship), or
  is itself a check that a numeric cap is *refused* (`_refuses_cap`, `feats.discover`,
  `genre.classify_source(cap=...)`, `grounding.classify_source(cap=...)` — all at
  §19g/§19i, asserting `SystemExit`). No production roster/page-list/chunk-list is
  silently truncated by this file. `_problems[:3]` at line 286 is display-only (feeds a
  human-readable `note=`; the real assertion is `len(_problems) == 0`).
- **The two-writer contract**: the only raw `open(path, "w")` + `json.dump` calls in
  this file target files inside `tempfile.mkdtemp()` throwaway directories (e.g. line
  1071, 1739, 2649, 2827) used purely as test fixtures to exercise `pipeline.write_record`
  / `write_record_catalogue` / `silence.write_json` / `silence.replace_retry` against
  synthetic "disk state" — never `data/records/*` or a real shared state file. This is
  the correct way to test a two-writer contract without becoming a third writer.
- **No bare `except:` clauses** anywhere in the file (`grep -n "^\s*except:\s*$"` —
  zero hits); every catch is at minimum `except Exception` or a specific exception type
  (`TypeError`, `SyntaxError`, `SystemExit`).
- **`_tier_counts`/`_nesting_violations`** (lines 26-41): independently traced the
  nesting-violation direction (grouping by the *lower* tier, checking it never spans
  more than one value of the *next-higher* tier) against the comment's claim ("one
  multiverse never spans two metaverses") — the grouping key/value order is correct
  for that claim.
- **Sections 1-17 (physics, assay, census, propagation, time, ledger, derivation,
  rigor, custodes, address space, world profile, hyperverse, sevenfold, burgs)**: read
  in full; every `check()` call recomputes its expected value from an independent
  formula or a hand-derived literal rather than calling back into the module's own
  helper, consistent with the file's stated "Moth test" methodology. No instance found
  of a check comparing a value to itself (only the two same-process double-calls in
  Finding 3, which are not literal self-comparisons).
- **Sections 18-29 (regression pins for run #9 through run #29)**: each pinned bug is
  narrated with a specific measured incident, and where the fix touches file contents
  the check reads the *actual source* of the module it claims to guard (via
  `open(...).read()` + substring/AST inspection) rather than asserting behaviour that
  could pass by coincidence. Spot-checked several of the source-grep guards
  (§19ab's num_ctx AST walk, §20e's subprocess-alias-resolving AST walk, §20i's
  disarm-guard self-test) for internal consistency; all correctly exercise both the
  positive and negative case (a disarmed sample must be caught, an ordinary sample must
  not).

## Summary

No HIGH or MEDIUM severity correctness bugs found in `src/verify_math.py`. No Hard
Rule 0 violations. No two-writer contract violations. No committed secrets. No bare
swallowed exceptions. The four findings above are all LOW (one borderline LOW–MED)
organizational/hygiene issues: duplicate section labels, one risky-but-currently-safe
variable alias reuse, two checks with narrower discriminating power than their labels
imply, and two unlabeled (but low-risk) exception swallows in test cleanup code.
