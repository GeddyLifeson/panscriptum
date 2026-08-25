# Sweep 29 — Batch 01 Audit

**Module:** `src/verify_math.py` (4000 lines, read in full, line by line)
**Run:** run29, batch 1
**Method:** Full read of every line, plus execution of the file with the miniconda interpreter
(`PYTHONIOENCODING=utf-8 C:/Users/imarl/miniconda3/python.exe src/verify_math.py`), plus targeted
greps for the seven lens categories and hand-verification of several arithmetic checks and AST
scans against the actual source they inspect (`address_space.py`, and a repo-wide grep for
patterns that would evade two of the file's own structural guards).

## Summary

`verify_math.py` is the project's independent verification suite — it recomputes every quantity
the project's modules produce from first principles and compares. It is not itself a data
pipeline: it does not write catalogue records, does not touch `data/` or `output/`, and is not
subject to the two-writer contract (it *exercises* `pipeline.write_record` /
`write_record_catalogue` as the SUT in section 18c, correctly, using temp files it creates and
cleans up itself).

The file is unusually self-aware: roughly the back half (sections 18b onward, ~2600 lines) is a
chronologically ordered set of regression tests, each one pinning a real defect the project found
in *other* modules on a specific date, several of them defects found in earlier drafts of
**this very file** (e.g. §20i/§20j document and then guard against three separate instances of
"a check that cannot fail" that had crept into verify_math.py itself: a `... or True,` disarmed
assertion, a source-scan blind to import aliases, and a case-sensitive denylist check). This
means many of the classic failure modes the audit lens is built to find have already been found
and fixed, in this file, by the file's own prior maintenance runs.

**Full suite run (reproduced):** `725 passed, 0 FAILED`. No currently-failing assertion.

I did not find any live correctness bug, swallowed failure, hard-rule-0 violation, tautological
check, two-writer violation, concurrency race, or contradicted docstring that is currently
producing a wrong verdict in this file. The findings below are two low-severity items worth the
supervisor's attention, plus two structural (non-exploited) limitations noted for completeness.

## Findings by lens

### 1. Correctness bugs
None found. Spot-verified several of the physical/statistical computations by hand (Earth binding
energy, Sagan continuous-Kardashev K at Type I and Earth's 2e13 W, the relativistic-KE gamma
check, the Monte Carlo log-variance check) — all match. The `check()` helper's own float/exact
dual-path comparator (lines 63–81) is intentionally narrow (`bool` deliberately excluded from the
float-tolerance path, per its own comment) and behaves correctly for every call site inspected.

### 2. Swallowed failures
Six `except Exception` sites total (lines 57, 1558, 2500, 2799, 3046, 3612). All six are either:
(a) the deliberately-documented `_raises()` helper where the exception IS the expected result
(line 44–58, extensively commented, silence-exempt by design and consistent with how the rest of
the project treats expected-exception probes); (b) benign temp-file cleanup in a `finally` block
(1558, 3612); or (c) explicitly measured and asserted against, not silently dropped (2500 records
into `_unparsed19ab` and is checked non-empty==false at line 2529; 2799 is `_json_try`, whose
whole job is reporting whether a line parses, checked at 2810–2811; 3046 is the subprocess-probe
except, which deliberately lets `_rc20a` stay `None` so the following check fails loudly rather
than hiding the problem — commented "the failure is reported by the check itself, not swallowed").
No bare `except: pass` on a path that discards a real result. **VERIFIED-BY-READING.**

### 3. Hard Rule 0 — caps / truncation
Grepped for `limit=`, `[:N]`, `most_common(`, `.head(`, `srlimit`, `aplimit`. Found:
- **`src/verify_math.py:811`** — `_rows = PR.build_all(limit=400)`. This *is* a numeric cap, and
  it is used to compute the pass/fail verdict for "every profile round-trips" (not merely a
  printed preview) — so by the letter of Hard Rule 0 it is worth flagging. However it is
  explicitly labelled in the adjacent comment as "A SAMPLE, and labelled as one," used only to
  prove a round-tripping property of a pure encode/decode function on a subset, not to compute or
  report a real corpus quantity, and it is inside the verification harness rather than the
  pipeline that produces or writes the library's data. **Recommend the supervisor decide whether
  this crosses the "no caps, ever" line as written or is an acceptable test-only sample** — I did
  not find it hiding a defect (a bug affecting only profile #401+ specifically would not be
  caught), which is the actual risk of leaving it in. **VERIFIED-BY-READING, LOW severity.**
- Lines 982/984/985 (`BG.burgs_for(..., limit=...)`), 1833 (`_CP.land(_rows[:3])`), 286
  (`_problems[:3]` in a note string only) are all deliberate test-input construction or
  display-only truncation, not data-truncation affecting a verdict. Not findings.
- Lines 3158/3165/3192/3493 are source-grep string literals that *check other modules for the
  presence/absence of a cap* (feats.py's `s[:220]`, overnight.py's `did[:5]`, etc.) — these are
  the audit's own Hard-Rule-0 enforcement, not violations.

### 4. Checks that cannot fail
- **`src/verify_math.py:760-761`** —
  `check("the map seed is derived from the address, not stored", AS.map_seed(_a), AS.map_seed(_a))`
  compares the same function call to itself with identical input. This is tautological with
  respect to its own label: it cannot distinguish "computed fresh from the address" from "read
  from a memoised/cached/global value that happens not to have changed between the two calls in
  the same process" — a cache would pass this check identically to a pure function. I verified
  `address_space.map_seed` (src/address_space.py:235-237) is in fact a pure `sha256(str(addr))`
  hash with no caching, so the check is not currently hiding a real defect, but as written it
  provides no protection against a future edit that introduces one. Contrast with the file's own
  more careful handling of an adjacent hazard class in §19n (navtree tie-break), where it
  deliberately tests *two different orderings* rather than *the same call twice*, for exactly this
  reason. **VERIFIED-BY-READING, LOW severity.**
- The file's own "disarm guard" (lines 3783–3849, `_needle20i`/`_needles20i`) that scans
  verify_math.py's own source for a check having been silently defanged only recognizes the
  `... or True,` family of bypasses (three specific string spellings, chosen to catch both
  single-line and the two-line-wrapped forms). It would not catch other disarming techniques —
  e.g. inflating a `tol=` value to something enormous, or wrapping an assertion in `if False:`.
  I grepped for anomalously large `tol=` values across the file and found none, so this is not
  currently exploited; it is a structural limitation of the same kind the file's own history
  (§20e→§20j) shows it has repeatedly had to widen after finding a narrower guard blind to a new
  spelling. **HYPOTHESIS, not currently exploited, informational only.**
- Similarly, the "no Ollama request hardcodes num_ctx" AST scan (lines 2494–2532) only recognizes
  the literal-dict-inside-a-dict shape `{"options": {"num_ctx": <int literal>}}`; an equivalent
  hardcoded value written as `options["num_ctx"] = 6144` or `options.update(num_ctx=6144)` would
  not be caught by this AST walk (it only inspects `ast.Dict` nodes). I grepped the rest of `src/`
  for both patterns and found none in use, so again this is not currently exploited.
  **HYPOTHESIS, not currently exploited, informational only.**

### 5. The two-writer contract
Not applicable to this file as a violator — `verify_math.py` writes nothing to `data/` or
`output/`. Section 18c (`write_record`/`write_record_catalogue`) and §20i correctly *exercise*
the two writers as the system under test, entirely inside `tempfile.mkdtemp()` directories that
are never the real records tree. No stray third writer introduced. Clean.

### 6. Concurrency races
Not applicable as a violator. Sections 19t, 19ad, and 19ae deliberately spin up real
`threading.Thread` pools against `gpu_lane.py`/`read.py` to *prove* the modules under test bound
concurrency correctly (peak-holder counting via a `threading.Lock`-protected counter, which is
appropriate here since the contention is threads within this one test process, not the
multi-process contention `gpu_lane.py` itself defends against on the live system). No fixed-name
temp file collisions found — every temp artifact in this file goes through
`tempfile.mkdtemp()`/`tempfile.gettempdir()` with a unique subdirectory, and the one place a
literal `.tmp` filename convention is asserted (§20g, `write_json`'s pid+thread-qualified temp
name) is asserted as a property of the *target* module, not a temp file this test writes itself.

### 7. Comments/docstrings contradicting code
None found contradicting *this* file's own code. (The file spends several of its later sections,
e.g. §20f, specifically hunting for and fixing exactly this defect class in *other* modules —
`rigor.py`'s stale docstring quoting a superseded constant — which is a different module, not this
one, and outside this batch's assignment.) One purely cosmetic oddity: line 1485's comment
`# _here19h is defined ~1600 lines later` sits directly beneath the line that *defines* `_here19h`
— the comment is stale/confusing (there is no such later definition; `_here19h` is used, not
redefined, at lines 1496/1507/1531/1535) but it is inert prose with no behavioural effect.
Not worth a fix ticket on its own; noting for completeness only.

## Reproduction log

```
cd C:/Users/imarl/panscriptum-library-kit
PYTHONIOENCODING=utf-8 C:/Users/imarl/miniconda3/python.exe src/verify_math.py
...
RESULT: 725 passed, 0 FAILED
```

```
grep -n "except:" src/verify_math.py                    -> no bare excepts
grep -n "except Exception:" src/verify_math.py           -> 6 sites, all reviewed above
grep -n "limit=\|\[:[0-9]\|most_common(\|\.head(\|srlimit\|aplimit" src/verify_math.py
grep -n "def map_seed" -A 15 src/address_space.py        -> pure sha256, no caching
grep -rn "\[.options.\]\s*=\|options\.update\|options\[.num_ctx.\]" src/*.py  -> no hits (not exploited)
grep -n "tol=" src/verify_math.py | grep -v <normal ranges>  -> no anomalously large tolerances
```
