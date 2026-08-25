# Audit — Batch 01 — run #24 whole-tree sweep

**File audited:** `src/verify_math.py` (3,620 lines)
**Coverage:** Read in full, line 1 through line 3620, in ten sequential chunks (1-300, 300-650,
650-1000, 1000-1350, 1350-1700, 1700-2050, 2050-2400, 2400-2750, 2750-3100, 3100-3620). No
sampling or skimming — every `print()` section header and every `check(...)` call site was read.
The script was also executed against the live tree (`python src/verify_math.py`) to confirm
current pass/fail state (682 passed, 0 failed at time of audit) and to empirically reproduce two
of the findings below rather than reasoning about them only from source.

This file is the project's own regression suite: ~682 `check()` calls covering physics/assay/
census/propagation/tempus/ledger/derivation/rigor/custodes/address-space/profile/grounding/
sevenfold/burgs and roughly 30 lettered "maintenance run" regression sections (19a–19af, 20a–20h)
added since 2026-08-24. The lens applied here is on the verifier itself, per the task brief: is
the harness's own logic correct, are any of its checks structurally unable to fail, and does it
interact safely with the shared state files the rest of the project depends on.

---

## FINDING 1 — `check()`'s float-tolerance branch has no type guard; an unhandled TypeError
kills the whole run and silently truncates every check after it

**File:** `src/verify_math.py:56`
**Severity:** MAJOR
**Status:** VERIFIED (reproduced empirically)

```python
def check(label, got, want, tol=1e-6, note=""):
    ok = (abs(got - want) <= tol * max(1.0, abs(want))) if isinstance(want, float) else got == want
```

When `want` is a `float`, the branch unconditionally computes `abs(got - want)`. If `got` is
anything that doesn't support subtraction with a float — `None`, a `str`, a `dict`, a `list` —
this raises `TypeError`, uncaught. There is no top-level `try/except` around the script body (the
file has ~35 *local* `try/except` blocks scattered around specific fragile calls, but nothing
wraps the whole run), so the exception propagates straight out of the process. Confirmed by
direct reproduction:

```
>>> check('bad',  None,          1.0)   # TypeError: unsupported operand type(s) for -: 'NoneType' and 'float'
>>> check('bad2', 'not_a_number', 1.0)  # TypeError: unsupported operand type(s) for -: 'str' and 'float'
>>> check('bad3', {'a': 1},      1.0)   # TypeError: unsupported operand type(s) for -: 'dict' and 'float'
```

**Concrete failure scenario:** any future `check(label, got, <float>, ...)` call where `got`
turns out non-numeric (e.g. because a module-under-test regressed and started returning `None`
or a dict where it used to return a float) does not report as a `FAIL` in the ledger — it crashes
the interpreter mid-script. Every `check()` call written after that point in the file (there can
be hundreds — this is a 3,620-line file with roughly 30 lettered sections after the trigger point
could land anywhere) never executes, and the final `print(f"RESULT: {len(PASS)} passed, ...")` /
`sys.exit(1)` block at the very end never runs either. A caller parsing the script's output for
the `RESULT:` line, or relying on the FAIL-listing format, gets neither — just a raw traceback —
and silently loses coverage of everything after the crash point, which is exactly the "smaller
universe in the same shape as the real one" pattern this audit is hunting for, applied to the
verifier's own output.

**Current status:** dormant. All 682 present-day `check()` calls pass, so this path is not
currently triggered. It is a latent structural defect in the harness, not an active failure.

**Fix shape (not applied — audit only):** guard the float branch, e.g.
`isinstance(want, float) and isinstance(got, (int, float))`, and fall through to `got == want`
(which reports a clean, recorded `FAIL` rather than crashing) or explicitly record a harness-level
`FAIL` when `got` is the wrong type for a numeric comparison.

---

## FINDING 2 — a tautological check that cannot fail, using `X or True`

**File:** `src/verify_math.py:3085-3087` (the load-bearing line is 3086)
**Severity:** MAJOR
**Status:** VERIFIED

```python
check("the horizon is derived from overnight.STANDING, not a second hand-kept copy",
      "import overnight" in _fm19._restart_horizon.__doc__ or True, True,
      note="documented intent; the assertion that matters is the pair of checks above")
```

`X or True` evaluates to `True` regardless of `X`, provided `X` itself doesn't raise. Confirmed
by direct inspection of the live docstring: `"import overnight" in _fm19._restart_horizon.__doc__`
is actually `False` (the docstring does not contain that literal substring — it says "STANDING
is imported rather than copied" in prose, never the code snippet), so the check's `got` argument
is `False or True == True`, which trivially equals `want=True`. This check will print `OK` and be
appended to `PASS` no matter what the docstring says, what `_restart_horizon` does, or whether
the "horizon is derived from `overnight.STANDING`" claim is even true any more. It is exactly the
"check that cannot fail" shape called out as this project's recurring bug: it is inert, and if the
label ever went stale (e.g. `_restart_horizon` stopped importing/deriving from
`overnight.STANDING` and reverted to a hand-kept copy — the regression this whole section exists
to catch), this specific line would not notice.

The author's own `note=` half-admits this ("the assertion that matters is the pair of checks
above"), which means the true assertion lives in the two `check()` calls immediately preceding
this one (lines ~3079-3084, which test `_restart_horizon`'s *output* text for two specific jobs).
Those two are real and do assert something. This third one is decorative: it reads as a real,
independently-verified claim in the printed report and the PASS count, but verifies nothing. A
reader of the printed output (or anyone trusting "682 passed, 0 failed" as a coverage figure) has
no way to tell this apart from a genuine, currently-true assertion.

**Fix shape (not applied — audit only):** either delete the line (the two checks above it already
carry the real assertion, per the author's own note) or replace it with something that can
actually fail, e.g. asserting the substring is present without the `or True` escape hatch.

---

## FINDING 3 — the verifier's own "expect an exception" helper writes into the project's shared
production failure ledger, contaminating a monitored standard

**File:** `src/verify_math.py:44-50` (the `_raises` helper), specifically the `silence.note(...)`
call on line 49
**Severity:** MAJOR
**Status:** VERIFIED (reproduced against the live shared ledger, with exact counts)

```python
def _raises(fn):
    try:
        fn()
        return False
    except Exception:
        silence.note("verify_math.py:47")
        return True
```

`_raises` is used 3 times in this file as a positive-path helper: "assert that calling `fn()`
raises" (`AS.pack` with an out-of-range field at line 725, `PR.decode("PS-nonsense")` at line
799, `_CB.assert_fits(...)` with an over-budget prompt at line 2184). All three exercise
*expected, wanted* exceptions — the check is passing *because* the code correctly raised.

`silence.note(site)` is not a no-op logging call. Per `src/silence.py:290-320`, it calls
`health.record(f"silent:{site}", exc_name, sample=repr(exc))`, which accumulates in memory and is
flushed at process exit (via an `atexit` hook) into `state/failures.json`. Per
`src/health.py`'s own module docstring and `src/foreman.py:237` (quoted inside `health.py`),
this file is **"the highest-traffic shared file in the project — the dashboard polls it,
standards reads it"**, and it is cumulative until the foreman archives it after triage.

`standards.py`'s `unexpected swallowed failures` standard (medium severity, `MAX_SWALLOWED_NEW =
2000`, `src/standards.py:83,533-545`) sums every key in that ledger *except* an explicit allowlist
of "probe classes" where a failed request is understood to be the measurement itself
(`endpoint.py:detect`, `hostcheck.py:probe`, `scout.py:verify`, etc.). `silent:verify_math.py:47`
is **not** in that allowlist, so every entry recorded under it counts as an "unexpected swallowed
failure" in a genuine, monitored production health standard — indistinguishable from a real
upstream fault being silently tolerated.

**This is not hypothetical.** I read the live `state/failures.json` and it currently holds:

```
"silent:verify_math.py:47:ContextOverflow": 29
"silent:verify_math.py:47:ValueError": 58
```

87 entries, entirely produced by this test harness's *intentional, expected* exceptions,
sitting in the same shared ledger and counted by the same standard that is supposed to catch
genuine unrecognized production swallows. At 2,000 this doesn't currently breach the floor, but
it inflates the "real" figure the standard reports on every run of `python src/health.py
--failures` or the dashboard, and every additional run of `verify_math.py` that exercises these
three checks adds more.

**The project already solved this problem correctly elsewhere in the same file, and `_raises`
just never got the memo.** At several later call sites added in the "maintenance run" sections
(e.g. the `SystemExit`-catching helpers around `feats.discover(extra=25)` at ~line 1440,
`_MB.pack_feats([], "S")` at ~line 1943, and `_refuses_cap` for the classifier-cap checks at
~line 1697), the authors deliberately chose **not** to call `silence.note` and instead wrote:

```python
_ = "silence-exempt: catching the refusal IS the assertion; a note would file a pass"
```

— explicitly reasoning that noting a *wanted* exception would misrepresent it as a swallowed
failure. `_raises` (defined earlier in the file, at the top, and used by three of the older
checks) was never updated to follow this later, better-reasoned convention. It's the same
underlying design mistake the newer code explicitly identified and avoided, still live in the
older helper.

**Fix shape (not applied — audit only):** either drop the `silence.note(...)` call from `_raises`
entirely (mirroring the `silence-exempt` convention used later in the same file), or route it
through a distinct, allowlisted class (e.g. `silence.note("verify_math.py:expected-raise")`) so
`standards.py`'s probe-class exclusion can filter it the same way it filters `endpoint.py:detect`.

---

## FINDING 4 — duplicate section numbers in the script's own printed report

**File:** `src/verify_math.py:3239` and `:3307` (both print `"24. §20e ..."`); `:3366` and
`:3418` (both print `"25. §20f ..."`)
**Severity:** COSMETIC
**Status:** VERIFIED

```
3239: print("24. §20e  A LIVENESS REPORT MUST NOT DELETE THE REPORTER — each renderer was")
3307: print("24. §20e  NO CONSOLE WINDOWS, EVER — every child spawn must suppress its window")
3366: print("25. §20f  RIGOR'S PROSE MUST NOT OUTLIVE RIGOR'S DATA — a section that printed the")
3418: print("25. §20f  A PERMANENT REFUSAL MUST NOT BE FILED AS CONTENTION — the auth bench")
```

Four distinct topics share two section numbers in the printed output. This doesn't affect what
gets checked or how — it's purely a report-labeling defect — but the module's own opening
docstring frames the whole file around the "Moth test": *"can a stranger, given the citations,
get your number?"* A section number that names two unrelated topics is a citation that doesn't
resolve to one place, in a project whose stated ethic is precise citation. Worth a one-line fix
(renumber to 24/25/26/27) but not a functional bug.

---

## Note (not counted as a finding) — an explicitly-justified sample cap

**File:** `src/verify_math.py:774`

```python
_rows = PR.build_all(limit=400)
```

This is a numeric `limit=` on the corpus used to verify `profile.py`'s encode/decode
round-tripping. Flagged per the audit brief's mandate to note every `limit=`/`max_*`, but this
one is explicitly labeled and reasoned about in the adjacent comment ("A SAMPLE, and labelled as
one: 400 profiles is plenty to prove round-tripping ... If decode ever breaks it breaks on the
first row, not the 40,001st"). It bounds a *test's* sample size for a property (round-trip
correctness) that doesn't need the whole corpus to falsify, not the corpus itself — it doesn't fit
the "smaller universe in the same shape as the real one" pattern Hard Rule 0 forbids. Recorded for
completeness; not treated as a bug.

---

## Summary

Three MAJOR, verified structural defects in the verification harness itself, plus one cosmetic
labeling defect:

1. `check()` (line 56) can crash the entire suite on a type mismatch it doesn't currently
   encounter but has no guard against — a single bad future check would silently drop every
   check after it, not just fail cleanly.
2. Line 3086 is a tautological `check()` call (`X or True`) that is structurally incapable of
   failing, inflating the PASS count with an assertion that verifies nothing.
3. The `_raises` helper (lines 44-50) has been pouring the test suite's own *expected* exceptions
   into `state/failures.json` — the project's real, dashboard-polled, standards-monitored
   swallowed-failure ledger — for at least 87 recorded occurrences to date, contradicting a
   `silence-exempt` convention the same file adopts correctly elsewhere.
4. Duplicate section numbers (24/24, 25/25) in the printed report undermine precise citation.

No findings against the mathematical content of the ~682 checks themselves — the physics,
census, ledger, and derivation-graph arithmetic all recomputes independently and matches. The
issues found are entirely in the harness's own control flow, error handling, and interaction with
shared project state — which is exactly where this project's signature failure class tends to
hide.
