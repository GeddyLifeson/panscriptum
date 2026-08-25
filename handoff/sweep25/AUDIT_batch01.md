# Sweep #25 — Batch 01 Audit

**Scope:** `src/verify_math.py` only (3,760 lines, ~700 checks). Read every line, end to end,
in four passes (1-893, 894-1700, 1701-2500, 2501-3760). Then ran the file for real
(`C:/Users/imarl/miniconda3/python.exe src/verify_math.py`, `PYTHONIOENCODING=utf-8`) to
confirm baseline, and wrote a standalone AST probe to verify the headline finding rather than
inferring it from reading.

**Baseline confirmed:** `RESULT: 697 passed, 0 FAILED` — matches `NEXT_STEPS.md`'s recorded
baseline exactly (item 3 under "Verify first").

## Special focus per the brief: auditing run #24's own edits to this file

Run #24 is documented (NEXT_STEPS.md, this file's own §20i / "Section 19h-bis" region) as having
found and fixed three control-flow defects in this exact file:

1. A check disarmed with `... or True` in the `_restart_horizon` assertion (§20b region,
   ~line 3105-3111).
2. `check()` itself raising `TypeError` on a non-numeric `got` against a float `want`, which
   silently killed every check after the first occurrence.
3. `_raises()` filing its own deliberately-provoked exceptions into `state/failures.json` via
   `silence.note`, polluting the project's highest-traffic fault ledger with 87 rows of noise.

I re-verified all three are actually fixed and did not regress:

- `check()` (line 63-82): the `isinstance(want, float)` branch now guards the `abs(got - want)`
  arithmetic with `isinstance(got, (int, float))`, falling back to `ok = False` rather than
  raising. Confirmed live: the deliberate self-test at line ~3277 (`check("probe: a non-numeric
  got against a float want", None, 1.0)`) prints `FAIL` and is correctly scrubbed from the tally
  rather than crashing the run — verified by the actual run output.
- `_raises()` (line 44-58): no `silence.note` call remains; the comment at lines 45-53 documents
  why, and grepping the file confirms no residual note call anywhere near it. **VERIFIED.**
- The `or True` disarm: grepped the whole file for `or True\b` — the only two hits are inside
  prose comments describing the historical bug (lines 3108, 3110), neither of which contains the
  literal string the file's own regression guard (`_needle20i`, line ~3277) searches for. The
  live check "no check in this file is disarmed with a trailing always-true disjunct" passes for
  real, not vacuously. **VERIFIED.**

No regressions found in these three areas.

## NEW FINDING — VERIFIED: verify_math.py itself violates the owner's "no console windows" rule, and section 20e's own guard cannot see it

**`src/verify_math.py:3034`**
```python
import subprocess as _sp20a          # line 3032

_p20a = _sp20a.Popen([sys.executable, "-c", "import time;time.sleep(30)"])   # line 3034
```

This is the SIGTERM probe in "§20a rc=15 IS A KILL, NOT AN EXIT" — it spawns a real child
process to verify that `os.kill(pid, SIGTERM)` produces `returncode == 15` on this platform.
**It passes no `creationflags=` and no `startupinfo=`.** Per the owner's hard rule (recorded in
this machine's persistent memory: "hard rule: nothing may ever pop a command window;
CREATE_NO_WINDOW everywhere") and per this very file's own §20e commentary two hundred lines
below ("ONE missed kwarg is one black window popping up on the owner's desktop"), this is exactly
the shape of bug the project has already spent a whole audit section eliminating everywhere else
in `src/`.

**Compounding it:** §20e ("NO CONSOLE WINDOWS, EVER", ~line 3350-3384) is the AST-based
whole-tree scan built specifically to catch this shape of bug and stop it recurring silently.
Its module-matching logic is:

```python
_f20e = _n20e.func
if not isinstance(_f20e, _ast20e.Attribute) or not isinstance(_f20e.value, _ast20e.Name):
    continue
_mod20e, _fn20e = _f20e.value.id, _f20e.attr
...
elif _mod20e == "subprocess" and _fn20e in _SPAWNERS20e:
    if "creationflags" in _kw20e or "startupinfo" in _kw20e:
        _guarded20e += 1
    else:
        _unguarded20e.append(_where20e)
```

`_mod20e == "subprocess"` matches only the literal name `subprocess`. It does not resolve
aliased imports. Since `verify_math.py` itself imports `subprocess as _sp20a` (line 3032), the
scan — which walks `src/*.py` including `verify_math.py` itself — silently skips its own
`_sp20a.Popen(...)` call: it is counted as neither guarded nor unguarded, so the check "every
subprocess spawn in src/ suppresses its console window" reports **green** while a real,
unguarded `Popen` call sits three hundred lines above it in the same file.

**VERIFIED two ways:**

1. Ran the actual §20e scan logic standalone (reproduced the exact AST-walk code from the file)
   over every `.py` in `src/`, widening only the module-name match to also accept `_sp20a`, to
   surface what the real scan is blind to:
   ```
   ('verify_math.py:3034', '_sp20a', 'Popen', False)
   ```
   was the **only** unguarded `Popen`/`run`/`call`/`check_output`/`check_call` site found in the
   entire tree (24 sites total; the other 23 all carry `creationflags=True` already, matching
   `NEXT_STEPS.md`'s "23 of 24 spawn sites" figure from the original run).
2. Confirmed via `grep` that no other file in `src/` imports `subprocess` or `os` under an
   alias or via `from X import Y` — `verify_math.py` is the one file exercising the exact blind
   spot its own guard has.

**What goes wrong concretely:** every time `verify_math.py` runs to completion (which is
scheduled/automated per the project's cadence) and reaches §20a, it spawns a child process with
no console suppression. If the parent has no console of its own at that moment (a supervised /
scheduled-task launch, which is how this project's automated runs work), Windows allocates a
fresh console window for the child — the exact "black window popping up on the owner's desktop"
the owner's directive and §20e's own comment describe as unacceptable, produced by the test
suite that is supposed to be enforcing the rule, invisible to the one check built to catch it.

**Fix shape (not applied — this is a read-only audit):** either give `_sp20a.Popen(...)` its own
`creationflags=subprocess.CREATE_NO_WINDOW` (platform-guarded, since the probe likely also needs
to run in CI/non-Windows contexts), or resolve the AST scan's module names through the file's
own `import ... as` bindings before comparing, so an alias can't hide a spawn site from it. Given
this file demonstrates the exact aliasing gap, the second fix is the one that keeps the guard
honest against the next alias too, not just this one.

## Secondary finding — UNVERIFIED (soft, docstring/scope drift)

**`src/verify_math.py:1-10`**, the module docstring:
```python
"""
Independent verification of every number this project computes.

Nothing here calls the modules' own helpers to check the modules' own helpers -- each assertion
recomputes the quantity from first principles and compares. That is the Moth test applied to the
code itself: *can a stranger, given the citations, get your number?*

Run:  python3 src/verify_math.py
"""
```
This described the file accurately for its original ~17 sections (physics, the Assay, the
Census, propagation, etc. — genuine independent recomputation of numeric quantities). Sections
18 onward (added across runs #17-#24, roughly half the file by line count) are integration and
regression tests of *behavior*, not numbers: process-kill signal semantics (§20a), atomic-write
contracts (§18c/§18d/§26), GPU-lane concurrency under real threads (§19u/§19ad), AST scans for
coding-standard violations (§19ab, §20e), HTTP-status/error-string classification (§20f/§20h),
and console-window suppression (§20e). These are valuable regression tests, but they are not
"every number this project computes," and several of them (e.g. §19t/§19ad's threaded
concurrency probes, §20a's live subprocess spawn) actively *do* call the modules' own runtime
machinery rather than recomputing anything from first principles — the opposite of the second
paragraph's claim. The docstring was accurate once; it has not been updated to describe what the
file actually is now. Low severity (nothing reads this docstring programmatically), but it is
exactly the class of drift item 6 of the audit lens asks about, and a maintainer reading only the
header would materially misunderstand what ~40% of the file does.

Also minor: `Run: python3 src/verify_math.py` — `python3` does not resolve on this machine
(confirmed: `where python3` finds nothing; only a bare `python.exe` from a different Python
install and the project-mandated `C:/Users/imarl/miniconda3/python.exe` are present). Cosmetic,
matches a machine-specific constraint this project's own `CLAUDE.md`/memory already documents
elsewhere (never use the bare launcher, always miniconda's `python.exe` directly).

## Things checked and found NOT to be bugs (worth recording so the next run doesn't re-check them)

- Scanned every `except` block in the file (12 sites). All are either (a) best-effort cleanup of
  test-only temp files in a `finally`, explicitly non-load-bearing, or (b) explicitly
  `silence-exempt`-commented probes where catching the exception *is* the assertion being made
  (e.g. the `SystemExit` catches for `feats.discover`'s and `genre.classify_source`'s cap
  refusals, correctly excluded from `_raises()` because `SystemExit` is a `BaseException`).
  None swallow a real production failure.
- Scanned all `try/finally` monkeypatch blocks (MG.F/MG.candidates/_CBm.ask/MG.P.ask/MG._ask/
  MG._POOL in §18b; `_TUNx.profile`/`_answering_buckets`/`cloud_success_rate`/`_ollama_up` in
  §19ac/§19ae; `_RD.P.ask`/`fallback_model`/`_TRANSPORT`/`_CASCADE_OK` in §19t; `_GLx.LANE`/
  `_BEAT_SECONDS` in §19ad; `_OW.LEDGER` in §19x; `_CB.UNRECOGNISED` in §19h-bis; `_CP.OUT`/
  `HOSTS`/`RECORDS`/`category_size_probe`/`host_reachable` in §19d) — every patched attribute is
  correctly restored in its matching `finally`. One minor loose end: `_gl_probe` (§19t, line
  ~2300) sets `_RD._GPU_DOWN_UNTIL[0] = 0` unconditionally and never restores its prior value —
  but nothing else in the file reads that state afterward, and `read.py`'s module state doesn't
  outlive this one-shot process, so it has no observable effect. Not filing as a finding.
- Checked for tautological checks (`got` and `want` expressions textually identical, or a
  hardcoded `True, True` pattern) — none found. The apparent self-comparisons that do exist
  (`"shelving is deterministic"`, `"burg seeds are deterministic"`, `"the map seed is derived
  from the address, not stored"`) are legitimate: they call the same function twice with
  identical inputs specifically to prove determinism, which is exactly what that class of check
  should do.
- Checked Hard-Rule-0 cap patterns (`[:N]`, `limit=`, `hard_stop=`) throughout the file — every
  hit is either (a) a `note=` string truncated for readable console output only (doesn't affect
  the pass/fail comparison, e.g. `"; ".join(_problems[:3])`), (b) deliberately-small test fixture
  data constructed to exercise a real cap-refusal or shrink-floor guard in another module (e.g.
  `_CP.land(_rows[:3])` proving `completeness.land()`'s 98%-shrink refusal), or (c) a string
  literal being checked for absence in another module's source (`'"sentence": s[:220]' in _ft19`,
  checked against `False` — i.e. asserting the cap is gone). None of these are the file itself
  imposing a real cap on real output.
- Re-verified the two test-only `open(path, "w")` + `json.dump` sites in §18c (`_rp` under
  `tempfile.mkdtemp()`) are not Two-Writer-Contract violations — they are throwaway single-writer
  fixture files in an isolated temp directory that verify_math.py itself creates and owns for the
  duration of one check block, not shared production state.
- Traced the `_tier_counts`/`_nesting_violations`/`_branching`/`_mode_stable` helper functions
  (all locally defined in this file, not imported) for correctness against what they're described
  as testing (nesting/branching invariants of the address-space and sevenfold-order tiers) — all
  matched their stated intent on inspection.

## Coverage statement

Every line of `src/verify_math.py` (1-3760) was read. No other file was in this batch's scope,
so no other module is claimed clean or dirty here.
