# Audit batch 01 — src/verify_math.py

Full line-by-line read: all 3560 lines (this run's `read23` batch was `['verify_math.py']`).

## Context

This file is the project's own independent-verification harness ("the Moth test applied to
the code itself"): ~380-400 `check(label, got, want, tol, note)` calls, organised into ~35
numbered sections, each recomputing a quantity from first principles or pinning a previously
found-and-fixed regression with a real repro. It is extraordinarily self-documenting — nearly
every section carries a comment naming the exact historical bug it exists to catch, with dates,
measured numbers, and file:line citations into the modules under test. This is evidence the
file itself has already been through many audit/fix cycles; my pass found very little new.

## Findings

### 1. `check()`'s float-tolerance branch can crash instead of reporting a clean FAIL

`verify_math.py:56`

```python
def check(label, got, want, tol=1e-6, note=""):
    ok = (abs(got - want) <= tol * max(1.0, abs(want))) if isinstance(want, float) else got == want
```

When `want` is a `float` literal, the branch unconditionally computes `abs(got - want)`. If the
function under test regresses so that `got` comes back `None` (or any other non-numeric value)
on some edge case — which is exactly the class of regression many sections here are written to
catch (e.g. a `.get("decimal")` on a deferred/failed result) — this raises an unhandled
`TypeError` inside `check()` itself rather than recording a `FAIL` entry. Because `PASS`/`FAIL`
are accumulated in module-level lists and only summarised at the very end of the file (lines
3553–3560), a single such crash aborts the run and discards every one of the (potentially
hundreds of) checks that would have run afterward — the opposite of what a "verify every
number, never go quiet" harness is for. It is not silent (a traceback prints), but it does
silently *truncate the report* to "everything before the crash," which for an audit tool is a
real coverage gap.

Most call sites correctly guard against this by unwrapping with `(x.get("result") or {}).get(...)`
before comparing, or by comparing to `None`/a string/bool (which takes the `==` branch and never
subtracts). I did not find a concrete call site that triggers the crash under the code as it
stands today — this is a structural fragility in the harness, not a currently-firing bug.

Severity: low-to-moderate (robustness of the audit tool, not of the product). **UNVERIFIED** —
traced the mechanism in `check()`, did not exhaustively confirm every one of ~400 call sites is
immune.

### 2. Two bare `except Exception: pass` blocks in cleanup code

`verify_math.py:1535-1539` and `verify_math.py:3521-3526`

```python
finally:
    try:
        if os.path.exists(_CB.UNRECOGNISED):
            os.remove(_CB.UNRECOGNISED)
    except Exception:
        pass
    _CB.UNRECOGNISED = _unrec_tmp
```

and

```python
finally:
    try:
        if os.path.exists(_probe20g):
            os.remove(_probe20g)
    except Exception:
        pass
```

Both are best-effort deletion of a throwaway test-probe file (`_VM_UNRECOGNISED_TEST.json`,
`_VM_ATOMIC_PROBE.json`) inside a `finally:` block. They do swallow any real error a failed
`os.remove` might represent (e.g. a permissions problem), with no `silence.note()` call, which
is a literal instance of the pattern Rule 2 asks to be flagged. In practice the consequence is
bounded — these are private, uniquely-named scratch files the test itself created a few lines
earlier, not shared project state, so a failed cleanup leaves at most an orphaned temp file, not
a corrupted or misread artifact. Flagging per the letter of the rule; **VERIFIED present**,
severity low given the blast radius.

## Explicitly checked and CLEAN

- **HARD RULE 0 (caps):** No `[:N]`/`limit=` in this file truncates a real ordered listing of
  entities/sources being *measured*. The one `limit=` (`PR.build_all(limit=400)`, line 791) is
  explicitly labelled "A SAMPLE... 400 profiles is plenty to prove round-tripping" — a bounded
  smoke-test of a pure function's round-trip property, not a production data pass, and the file
  says so in the same breath. `note="; ".join(_problems[:3])` (line 266) truncates only a
  diagnostic string appended to a FAIL printout, not the underlying `len(_problems) == 0` check.
  Numerous sections (19g, 19i, 19r, etc.) exist specifically to *pin the refusal* of caps
  elsewhere in the codebase (`feats.discover`, `genre.classify_source`,
  `grounding.classify_source`, `entity_match.candidates`) — this file is itself part of the
  project's caps defence, not a violator of it.
- **Two-writer contract:** Every `open(path, "w")` / `json.dump(..., open(path, "w"))` site in
  this file (lines 1151, 1164, 1177, 1252, 1265, 1293, 1662, 1701, 1848, 2605, 3296) writes to a
  file inside a `tempfile.mkdtemp()` sandbox or a uniquely-named `_VM_*` scratch file under
  `state/`, created and torn down within the same test, specifically to construct a fixture that
  the real writer (`pipeline.write_record`, `silence.write_json`, `overwatch.save`, etc.) is
  then exercised against. None of them touch genuine shared project state directly. Clean.
- **Concurrency races:** The file spawns real threads in several sections (18b's mocked
  `assay_entity` calls are single-threaded; 19t's `_gl_probe`, 19ad's `_holder19ad`) specifically
  to *test* other modules' concurrency guards. Shared counters inside those worker functions
  (`_gl_peak`, `_peak19ad`) are lock-protected; `check()` itself is only ever called from the
  main thread after `Thread.join()`, so there is no race on the module-level `PASS`/`FAIL` lists.
  Clean.
- **Comments contradicting code:** Read every inline comment/docstring in the file against the
  code it describes (including the long historical write-ups in sections 18–26). All match. No
  instance found of a comment claiming behaviour the adjacent code does not have.
- **Swallowed failures (beyond the two noted above):** Every other `except` in the file catches
  a specific exception type and/or is explicitly justified with a `"silence-exempt: ..."` comment
  explaining why the catch itself IS the assertion (e.g. `_raises()` at line 44, the `SystemExit`
  catches at lines 1442 and 1572, the `TypeError` catch at line 2004, the `SyntaxError` skip at
  line 3336 which is explicitly deferred to a different tier's job). The one genuinely broad
  catch used for real measurement (`except Exception` around `ast.parse` at line 2480) records
  the failure via `silence.note()` and asserts `_unparsed19ab == []` afterward, so a parse
  failure surfaces as a check FAIL rather than being silently absorbed.
- **Correctness of the arithmetic/logic itself:** Spot-verified a representative sample of the
  recomputations against their stated formulas (Earth/Sun binding energy, relativistic KE,
  Sagan's continuous Kardashev K, MDL combinatorics via `math.comb`, log-variance addition vs.
  Monte Carlo, Bradley-Terry MLE recovery, AHP/Perron consistency). All formulas as written match
  the cited derivation in the surrounding comment; no transcription errors found.

## Overall

`src/verify_math.py` is CLEAN against Rules 1, 3, 4, 5, and 6 as I read it. Two minor swallowed
exceptions (Rule 2, low severity, cleanup-only) and one structural robustness gap in the `check()`
harness itself (could truncate its own report on a crash) are the only findings, both minor.
