# BATCH 01 — verify_math.py — full line-by-line audit (run26)

Module: `src/verify_math.py` (3893 lines, read in full, offsets 1-1000 / 1000-2000 / 2000-3000 /
3000-3893).

## Context

This file is the project's independent verification suite — it recomputes every number the
project's modules claim, from first principles, and separately pins ~150 historical regressions
found by prior audit runs (run #17 through run #25), each documented in-line with the incident
that produced it. It is unusually mature: nearly every category the audit lens asks about
(swallowed failures, caps, two-writer violations, concurrency races, self-contradicting guards,
subprocess windows) has already been hunted down and fixed at least once inside this very file,
with the fix and the regression check both present. The findings below are what remains after a
full read against that same lens, applied to verify_math.py's *own* code (not re-auditing the
correctness of the modules it tests, which is out of scope for this file).

---

## MAJOR

### 1. `verify_math.py:3757` / `verify_math.py:3790-3795` — the "no check is disarmed with `or True`" guard only catches the one-line spelling of the bug it exists to catch

```python
# needle assembled at runtime: written as a literal it would match its OWN source line and
# fail forever -- the self-referential version of the bug it is checking for.
_needle20i = " or " + "True, " + "True,"
...
check("no check in this file is disarmed with a trailing always-true disjunct",
      _needle20i in open(os.path.join(_here19, "verify_math.py"), encoding="utf-8").read(),
      False,
      note="§20i's third case: the STANDING-horizon check asserted against a docstring that "
           "never contained the string, so an always-true disjunct had been added to keep it "
           "quiet -- a check that cannot fail, in the file that exists to fail")
```

This is a whole-file guard against a documented real regression (line 3116-3119: a check was
once silently disarmed with `... or True`). But the needle `" or True, True,"` requires the
disjunct and the `True,` want-argument to sit on the *same physical line with no line break
between them*. That is true of the one specific historical incident this needle was written to
catch (its boolean expression and `True,` want-arg are on one line, lines 3117-3119), but it is
**not** the file's general style. Grep confirms multiple checks elsewhere in this same file wrap
the boolean expression and the `True,` want-argument onto separate lines, e.g.:

```
verify_math.py:2201-2202   True, note="the old constant had no arithmetic relationship..."
verify_math.py:2219-2220   True, note="the packer used to test the budget AFTER appending..."
verify_math.py:2911-2912   True, note="the live 2026-08-24 19:08 window..."
verify_math.py:3878-3879   True, note="Cascade engine.py:277 and :343, two wordings..."
```

For any check written in that (very common) shape, disarming it with `expr or True,` on the line
*before* `True,` produces:

```
      ... or True,
      True, note="...")
```

which does **not** contain the contiguous substring `" or True, True,"` (a newline + 6-space
indent sits between them), so the guard would read this file as clean while a check sat
permanently, silently disarmed. This is exactly the failure shape the file's own run #25 section
(§20j, lines 3798-3822) names as the worst version of this bug class: *"a guard that only
recognises the unobfuscated spelling of the thing it forbids... is green on purpose, forever, and
every new spelling is a fresh hole."* The guard whose entire job is to catch that shape is itself
an instance of it.

**Failure scenario**: A future edit (accidental merge artifact, or a "quick fix to stop this
check failing" under time pressure) appends ` or True` to the boolean expression of any
multi-line check whose `True,`/`False,` want-argument is on its own line — several such checks
exist right now — and `verify_math.py` continues to report 100% green while that check has
stopped testing anything.

**Suggested fix direction**: normalize whitespace (e.g. `re.sub(r"\s+", " ", source)`) before
the substring search, so line-wrapping cannot hide the pattern; or better, walk the AST for a
`BoolOp(op=Or, values=[..., Constant(value=True)])` anywhere inside a `check(...)` call's second
positional argument, which cannot be defeated by reformatting at all.

---

## MINOR

### 2. `verify_math.py:647-648` — `_MAXED` fixture silently omits one of the eleven axes it claims to max out

```python
_MAXED = {k: 10.0 for k in ("ruin", "celerity", "reach", "sustain", "continuity",
                            "transgression", "vector", "acumen", "discernment", "suasion")}
_top = A.assay("M10", _MAXED, attestation="Witnessed", worksheet="x")
_mid = A.assay("M4", _MAXED, attestation="Witnessed", worksheet="x")
check("the ceiling SATURATES instead of overflowing its notation",
      _top["decimal"] <= 0.99, True, ...)
check("and says it has reached the ceiling", _top["at_ladder_ceiling"], True)
check("a maxed non-top band flags promotion rather than auto-promoting",
      _mid["promotion_due"], True, ...)
```

`assay.py`'s `WEIGHTS` table (confirmed by reading `src/assay.py:112-143`) has eleven axes: the
eight physical Measures — `ruin, continuity, celerity, reach, transgression, sustain, vector,
volition` — plus the three faculties `acumen, discernment, suasion`. The tuple above lists ten
of them; **`volition` is missing**. The variable name `_MAXED` and every comment around it
("the ceiling SATURATES", "a maxed non-top band") assert this is an entity with *every* axis at
10.0, but `volition` is never scored on it at all.

This happens not to break the four checks that currently read `_top`/`_mid`, because
`assay.assay()` renormalises `composite` over only the *scored* axes (`used`), so
`composite == 10.0` regardless of which subset of axes is present, as long as everything present
is 10.0 — the ceiling-saturation arithmetic is insensitive to this omission. But it does mean:

- `_top`/`_mid`'s `axis_coverage` is not actually 1.0 for this fixture (volition lands in
  `assay.py`'s `unscored` list, which widens the interval and is counted against `applicable`/
  `denom` but not `wsum`) — the fixture is quietly "10 axes maxed, 1 axis never asked about,"
  not "every axis maxed" as its name and the surrounding comments claim.
- Any future check added to this section that reads `_top["interval"]` or
  `_top["axis_coverage"]` expecting a fully-saturated, fully-covered entity would get a silently
  wrong answer, in the file whose entire purpose is to catch exactly that class of drift.

**Fix**: add `"volition"` to the tuple.

---

## QUESTION

### 3. Source-text / `getsource()` regression guards are a structurally fragile pattern (several sites, not just Finding 1)

Beyond Finding 1, this file relies heavily elsewhere on scanning `open(...).read()` or
`inspect.getsource(...)` output for literal substrings to pin a fix in place, e.g.
`verify_math.py:3113-3119` (the `"import overnight" ... and "_ON.STANDING" in ...` check, whose
own comment records that it *already* went through exactly this failure mode once — "It read
`... in __doc__ or True` until run #24"), and the many `_src in <module>` checks throughout
§20a-§20j. These are legitimate and mostly well-hardened (comment-stripping is applied before
several of them, e.g. `verify_math.py:3129`, `3187`, `3196`, `3258`), but the pattern as a whole
remains inherently brittle against reformatting, renaming, or refactors that preserve behavior
while changing text — which is precisely the failure class this project's own history (documented
repeatedly in this file) shows keeps recurring. Not a new bug beyond Finding 1, but worth a
periodic pass specifically looking for guards of this shape whenever the modules they inspect are
refactored.

---

## Hard Rule 0 (caps) — everything found, and disposition

Grepped for `[:N]`, `head`, `LIMIT`, `top N`, `.head(`:

| Site | What it is | Verdict |
|---|---|---|
| `verify_math.py:286` `_problems[:3]` | Truncates only the **diagnostic note string** shown on failure; the actual assertion is `len(_problems) == 0` over the **full**, untruncated list. | Legitimate — cosmetic message truncation, not a data cap. The check itself sees every problem. |
| `verify_math.py:811` `PR.build_all(limit=400)` | Explicitly labelled: *"A SAMPLE, and labelled as one: 400 profiles is plenty to prove round-tripping and far cheaper than the full set."* Used only to test a structural property (round-tripping), not to report or generate real content. | Legitimate test-sampling bound, self-declared as such per Hard Rule 0's own carve-out for ranking/sampling that doesn't silently stand in for the whole universe. |
| `verify_math.py:982,984-985` `BG.burgs_for(..., limit=N)` | `burgs_for`'s own `limit` kwarg, used here to keep statistical-comparison test fixtures a manageable size (coastal-proportion comparison, seed determinism check). | Legitimate test bound — not exercising or masking a production truncation. |
| `verify_math.py:1833` `_rows[:3]` | Deliberately-shrunk **copy** of a test fixture, used to *simulate* a 98%-shrink scenario so the "shrink refused" guard can be exercised. | Legitimate — test input construction, not a real cap. |
| `verify_math.py:3158,3493` `s[:220]`, `str(exc)[:300]` | Source-text checks asserting a bounded-length **diagnostic/log field** exists (or doesn't) in another module. Bounding an error-message field length is a buffer-size decision, not a truncation of a data set. | Legitimate bound (verified as such, not flagged as a violation). |
| `verify_math.py:3192` checks *absence* of `did[:5]` in `overnight.py` | Verifies a previously-fixed cap stays fixed. | N/A — this is itself an anti-cap regression check. |

No occurrence found where `verify_math.py` itself truncates, samples-then-reports, or silently
shrinks a real data set under test. Clean on Hard Rule 0.

---

## Two-writer contract

All direct `open(path, "w")` / `json.dump(...)` calls in this file write to `tempfile.mkdtemp()`
fixtures created and torn down within the test (e.g. lines 1165-1202, 1681-1722, 1849-1917,
2804-2814, 3688-3705, 3725-3732) — these are constructing the "disk state" a function under test
(`pipeline.write_record`, `pipeline.write_record_catalogue`, `runguard`, `overwatch.save`, etc.)
is then exercised against, not writes to real project record/state files. This is the correct and
expected way to unit-test those contracts. No violation found. Clean.

## Swallowed failures / bare except

Every `except Exception` / `except SystemExit` / `except TypeError` in this file was checked
individually:

- `_raises()` (lines 44-58) and the `_refuses_cap`/manual-`SystemExit` helpers (lines 1459-1465,
  1588-1594, 2021-2029) are explicitly documented as intentional, with `silence-exempt` comments
  explaining exactly why noting them would be the bug (a passing assertion filed as a production
  failure). Verified the reasoning is sound in each case: the exception **is** the expected
  result being probed.
- `verify_math.py:2500` (the AST parse-failure branch in §19ab) does **not** silently skip — it
  calls `silence.note(...)`, appends to `_unparsed19ab`, and that list is asserted empty
  afterward (line 2529). Correctly non-swallowing.
- `verify_math.py:2799` (`_json_try`) intentionally converts a parse failure into `None` as the
  measurement itself (does a line parse or not), consistent with its stated purpose.
- `verify_math.py:3046` (SIGTERM-child probe) explicitly documents that leaving `_rc20a = None`
  on any mishap makes the following `check(..., _rc20a, 15)` fail loudly rather than hiding
  anything.
- Cleanup-only `except Exception: pass` blocks in `finally:` teardown (lines ~1554-1560,
  ~3580-3585) are best-effort temp-file removal after the real assertions have already run;
  standard and low-risk.

No unaccounted-for swallowed failure found.

## Concurrency / atomicity

Every monkeypatch of module-level state (`MG.F.evidence_for`, `MG.candidates`, `_CBm.ask`,
`CU.CUSTODES`, `_CP.HOSTS/RECORDS/category_size_probe/host_reachable`, `_RD.P.ask` /
`_RD._GATE_STATE` / `_RD._TRANSPORT`, `_TUNx.profile` / `_TUNx._answering_buckets` /
`_TUNx.cloud_success_rate` / `_TUNx._ollama_up`, `_GLx.LANE` / `_GLx._BEAT_SECONDS`,
`_OW.LEDGER`) was traced from its `_saved = ...` capture to its `finally:` restore. All are
correctly paired — verified no leaked monkeypatch that could corrupt a later section's result.
This matters here specifically because a leaked patch would make a *later, unrelated* check pass
or fail for the wrong reason, which is a subtler version of the "check that cannot fail" problem
the lens asks about. Clean.

## Subprocess spawn (CREATE_NO_WINDOW)

One real spawn in this file, `verify_math.py:3041-3042`:

```python
_NO_WIN20a = getattr(_sp20a, "CREATE_NO_WINDOW", 0)
_p20a = _sp20a.Popen([sys.executable, "-c", "import time;time.sleep(30)"],
                     creationflags=_NO_WIN20a)
```

Correctly guarded (`getattr` degrades to `0` off-Windows rather than raising). This is also the
spawn that the file's own §20e/§20j AST-based whole-tree scan (lines 3358-3423, 3814-3822) had to
be specifically fixed to *detect*, because it goes through the import alias `_sp20a` rather than
the literal name `subprocess` — confirmed the alias-resolution logic (`_alias20e`/`_direct20e`,
lines 3377-3401) does correctly resolve `import subprocess as _sp20a` and would flag this site if
`creationflags` were ever dropped. Clean.

## Comments contradicting code / "green on purpose" checks

Beyond Finding 1 (which *is* this failure class), every other place the file itself calls out a
past instance of this pattern (the `... or True` STANDING-horizon fix at 3113-3119, the alias-blind
spawn scan at 3370-3376, the case-sensitive `.py` extension check at 3809-3811, the
`community.fandom.com` IPv6 probe at 2337-2350) was checked against its current, fixed form and
found consistent with what the surrounding comment claims. No new instance of a guard matching
only one spelling was found other than Finding 1.

## Correctness spot-checks (arithmetic / logic reviewed line-by-line)

`_tier_counts`/`_nesting_violations` (lines 26-41), the `check()` float/bool comparison rule
(lines 63-81, including the documented deliberate `bool`-is-`int`-subclass narrowness), the
Kardashev/census chain arithmetic (156-184), the `_mode_stable` tie-break helper and its four
checks (1929-1949), the rank-size burg checks (950-987), and the PASS/FAIL global scrub-and-
restore self-test in §20i (3737-3753) were all traced by hand against their stated intent and
found to compute what they claim to compute. No off-by-one, inverted condition, or wrong-variable
bug found in any of these.

## Clean / sound

- `check()`'s core comparison logic (float-vs-non-numeric-got guard, the reason it exists,
  documented at lines 63-81) is correct and the file's own self-test of it (§20i, 3737-3753)
  actually exercises the branch rather than merely asserting the comment.
- No caps found in this file's own logic beyond the legitimate/self-labelled ones tabulated above.
- No two-writer-contract violation.
- No un-restored monkeypatch found across ~20 save/finally pairs checked.
- The one subprocess spawn in this file is correctly guarded and is itself the fixture that
  proves the whole-tree spawn-guard scan works.
