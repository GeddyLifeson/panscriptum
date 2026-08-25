# Sweep 31 — Batch 01 Audit

**Modules covered:** `src/verify_math.py`
**Total lines read:** 4269 (entire file, read line-by-line in six sequential passes, plus targeted
greps for `except`, `open(`, `limit`, `[:N]`, `threshold`, `break`, `TODO`/`FIXME`)

## Context

`verify_math.py` is the project's independent verification harness — a single self-contained
script (no test framework) that recomputes every load-bearing number in the codebase from first
principles and diffs it against the module under test, and also runs a large and growing set of
regression checks that pin specific bugs the project has already found and fixed (each one
documented in-file with the date, the measured symptom, and the root cause). This is by a wide
margin the most heavily self-documented file I have ever swept: nearly every section carries a
multi-paragraph comment explaining what broke, how it was discovered, why the fix is shaped the
way it is, and why an "obvious" alternative fix would be wrong. The file also contains several
meta-checks that audit itself and sibling modules for the exact defect *classes* this sweep is
looking for (checks that cannot fail, guards that only recognise the unobfuscated spelling of the
thing they forbid, caps disguised as thresholds, two-writer races, non-atomic writes, swallowed
exceptions that read as "nothing here").

Because of that, the great majority of code patterns that would normally be flagged by the lens
(bare `except Exception`, raw `open(path, "w")` + `json.dump`, hardcoded numeric literals compared
against computed values, `_raises`/`_refuses_cap` catching broad exceptions) are already
individually justified in an adjacent comment, and in several cases the comment itself is the
project's record of a *previous* audit finding that was fixed. I have not re-reported those as new
findings; I traced each one against its comment and confirm the stated rationale holds. What
follows is only the set of items that either (a) are not already covered by the file's own
commentary, or (b) I can independently verify are inconsistent with a directly adjacent sibling
pattern in the same file.

## Findings

### 1. MAJOR — VERIFIED — silent, unaccounted-for narrowing of the "no console windows" guard on a syntax error

**File:** `src/verify_math.py:3388-3392`

```python
for _p20e in sorted(_glob20e.glob(os.path.join(_here19, "*.py"))):
    try:
        _t20e = _ast20e.parse(open(_p20e, encoding="utf-8").read())
    except SyntaxError:
        continue                      # allsweep's LINT tier owns syntax; not this check's job
```

This is the AST scan behind "every subprocess spawn in src/ suppresses its console window"
(checked at line 3437) and "no os.system / os.popen / os.startfile anywhere in src/" (line 3440) —
the enforcement mechanism for the owner's hard "NO CONSOLE WINDOWS, EVER" directive. If a `.py`
file in `src/` has a syntax error at the moment this suite runs (very plausible mid-edit, or if a
patch lane write is caught between a partial rewrite and the next lint pass), that file is
`continue`d out of the scan with **no record kept of which files were skipped, and no assertion
that the skipped set is empty**. An unguarded `subprocess.Popen(...)` sitting in that file — the
exact hazard this section exists to catch, and the exact thing found live in *this very file* at
run #25 (§20a/§20j, lines 3057-3063 and 3893-3899) — would sail through a full sweep undetected,
silently, with the suite reporting green.

This is the same failure *shape* the file repeatedly calls out by name elsewhere: a guard that
narrows its own coverage without saying so reads identically to a guard with nothing to find.
The immediately comparable scan 800 lines earlier — the `num_ctx` hardcoding check at
lines 2517-2555 — gets this exactly right: it also cannot parse every file (`except Exception:`
at line 2523), but it *records* the unparsed file (`_unparsed19ab.append(...)`) and then asserts
`check("every module was readable by the context-window scan", _unparsed19ab, [])` (line 2552),
so a file that becomes unparseable turns the suite red rather than silently shrinking scope.

**Why it's wrong:** `except SyntaxError: continue` with no bookkeeping is a fail-open path in a
scan whose entire purpose is exhaustive coverage of `src/*.py`; the comment's justification
("allsweep's LINT tier owns syntax") is an assumption about a *different* tool having *already*
run and passed, which this file has no way to verify and does not check.

**Concrete failure scenario:** a module is mid-save (e.g. a patch-lane edit interrupted, or a
manual edit left with an unclosed paren) when the sweep runs; that module contains a bare
`subprocess.Popen(...)` with no `creationflags`. The AST scan hits `SyntaxError`, `continue`s
past it silently, and `_unguarded20e` never sees the offending call. The suite reports "every
subprocess spawn in src/ suppresses its console window: PASS" while a console-window-popping
spawn sits live in the tree.

**Severity:** major (the hard rule it enforces is stated by the owner in the strongest terms, and
the failure mode is exactly the class of bug this project has repeatedly rediscovered and named).
**Confidence:** VERIFIED — traced directly in source; the asymmetry with the sibling check at
2517-2555 is unambiguous.

**Suggested fix (not applied — read-only audit):** mirror the `num_ctx` scan's pattern — collect
unparseable filenames into a list and assert it is empty (or explicitly cross-check against
`allsweep`'s LINT tier result), the same way section §19ab already does for the identical
"a file this scan cannot parse is a file this scan cannot clear" problem two thousand lines
earlier in the very same file.

---

### 2. MINOR / cosmetic — VERIFIED — the alias `_CB` is bound to two different modules across the file

**File:** `src/verify_math.py:1506` then `src/verify_math.py:2211`

```python
1506: import cascade_bridge as _CB          # noqa: E402
...
2211: import context_budget as _CB          # noqa: E402
```

`_CB` names `cascade_bridge` from line 1506 through its last use at line 1583, then is silently
rebound to `context_budget` at line 2211 and used as such through line 2271. I confirmed (by
grepping every `_CB.` use in the file) that no code after line 2211 relies on `_CB` still meaning
`cascade_bridge` — every later cascade_bridge reference uses a different alias (`_CB22b`,
`_cb20h`, `_cb20i`, `_cb20j`, `_cb20l`, etc.), so this does not currently produce a wrong-value
bug. It is a latent trap for the next edit, though: this file's own established convention is one
alias per module per section (`_CBm`, `_CB22b`, `_cb20h`...), and `_CB` is the one place that
convention is broken. A future check inserted between 1583 and 2211 that assumes `_CB` still means
`cascade_bridge` (matching the pattern used everywhere else) would either raise `AttributeError`
(if the attribute doesn't exist on `context_budget`) or, worse, silently resolve to a
same-named attribute on the wrong module.

**Severity:** cosmetic/minor. **Confidence:** VERIFIED (no live bug today, but a real footgun).

---

### 3. MINOR / cosmetic — VERIFIED — two Hard-Rule-0-shaped caps in test-only code, both self-justified in-line

**File:** `src/verify_math.py:811`, `982`, `984-985`

```python
811:  _rows = PR.build_all(limit=400)
982:  BG.burgs_for(424242, _f, limit=3)[2]["seed"], _bs[2]["seed"])
984-985: sum(b["coast"] for b in BG.burgs_for(7, dict(_f, landform="archipelago"), limit=200)) > ...
```

CLAUDE.md's Hard Rule 0 forbids any cap/limit/sample "for ANY reference," so per the sweep's
instruction to report every cap-shaped construct regardless of context, these are flagged. In
context, all three are test-fixture sizing, not library generation: line 811 is preceded by an
explicit comment ("A SAMPLE, and labelled as one: 400 profiles is plenty to prove round-tripping
and far cheaper than the full set") arguing this is a verification-harness performance trade-off
rather than a truncation of catalogued content, and the `burgs_for(..., limit=N)` calls at 982-985
are sizing a settlement-generation self-test, not filtering a real roster. I did not find evidence
these caps reach the actual generation pipeline (`profile.py`/`burgs.py` are outside this batch,
so I could not confirm whether `build_all`'s default, uncapped, call path is what production code
actually uses — worth a supervisor cross-check against whichever batch covers `profile.py` and
`burgs.py`).

**Severity:** cosmetic (test-only, already self-justified) but flagged per the sweep's "report
every one" instruction. **Confidence:** VERIFIED (locations and rationale), HYPOTHESIS on whether
production call sites elsewhere ever inherit an unintended default cap from these same functions
(out of scope for this batch).

## What I checked and found sound (no new finding)

- The `_raises`/`_refuses_cap` broad `except Exception`/`except SystemExit` patterns (lines 44-58,
  1482-1488, 1611-1618) are each accompanied by an explicit "silence-exempt" rationale explaining
  why the exception itself is the assertion, and I traced each site to confirm the surrounding
  `check()` call correctly turns a non-raise into a failed check rather than a false pass.
- `check()`'s tolerance formula (`tol * max(1.0, abs(want))`, lines 63-77) is a correct
  relative-tolerance-with-absolute-floor design; I re-derived several of the physics/Kardashev
  arithmetic checks (lines 88-114, 175-184) independently by hand and they are numerically correct
  against the stated formulas.
- The two-writer-contract tests (§18c/§18d, §19j, §20d) write their fixtures to `tempfile.mkdtemp()`
  paths, never to real `records/`/`state/` paths, so they are not themselves violations of the
  two-writer contract they are testing.
- The self-referential "no check is disarmed with a trailing always-true disjunct" guard
  (lines 3806-3872) is correctly built: the needle strings and the demonstration fixtures are
  assembled via string concatenation specifically so the guard's own source does not trip itself,
  and I confirmed by hand that the raw (pre-whitespace-collapse) source of the fixture-building
  lines does not contain the needle substrings, so the self-scan cannot false-positive there.
- Determinism-style checks that call a function twice and compare the two results to each other
  (e.g. `AS.map_seed(_a) == AS.map_seed(_a)` at line 761, `AS.assign(...)` at 787,
  `SF.build()[1]["Alien"] == _coords["Alien"]` at 935) are legitimate purity/determinism probes,
  not tautologies — each is capable of failing if the tested function had hidden unseeded
  randomness or mutable state.
- No instance found of a bare `except:`/`except Exception:` in this file that converts a real
  transport/read failure into a value indistinguishable from a verified absence; every such site
  either re-raises visibly via the surrounding `check()`, or is explicitly a test's own
  measurement of "does this parse" (e.g. `_json_try` at 2819-2824).
