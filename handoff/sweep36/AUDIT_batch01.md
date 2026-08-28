# AUDIT batch01 — run #36

Module (1 of 1, largest single file in tree): `src/verify_math.py` (7,144 lines, 1,053 total
assertions at runtime: 1,052 pass + 1 expected fail)

Read-only audit. No edits made. File was confirmed edited twice today by other agents before
this read; the version read is whatever was on disk at audit time.

Method: (1) full read of the file header/docstring and the `check()`/`_raises` harness
(lines 1–100); (2) a complete AST scan of every `check()` call site in the file (932 static
call sites covering the ~1,053 runtime assertions, since some call sites execute inside loops
and the run #35 sub-batches contribute additional assertions folded back through `check()` in
§20u) for tautologies, self-comparisons, and source-substring pins; (3) a complete grep-based
census of every `§`-tagged and `# ---- Section 19x` section header for duplicate labels;
(4) an actual run of the suite (`PYTHONIOENCODING=utf-8 .../python.exe src/verify_math.py`,
exit 1, ~1 min) to confirm the live pass/fail state; (5) targeted reads of ~15 sections flagged
by the scans as suspicious, plus spot reads of sections 1–18, 20u/§20u (36), and the
`checks_L*.py` delegation machinery in §20u.

## Live run result

`1052 passed, 1 FAILED`. The one failure is exactly the expected/being-closed-elsewhere one:

```
FAILED the live sweep proves its own completeness: got ['canon_backup.py'], want []
```

**No other failure.** Nothing else is red right now.

## Findings

### 1. MAJOR — duplicated section tag: `Section 19s` used twice

`grep -n "^# ---- Section" src/verify_math.py` shows exactly one label collision (all other
`19x`/`20x` letters are unique, confirming the §20e/§20f collisions from earlier today are
fully and correctly resolved — see §24/§27's own renumbering notes at lines 3628–3629 and
3971–3972).

- Line 2494: `# ---- Section 19s: both writers of the metrics ledger stamp a timestamp -----`
  — a ~20-line section (added run #13) checking that `pipeline._metric` and
  `cascade_bridge._metric` both stamp an `"at"` field on `model_metrics.jsonl` rows.
- Line 4642: `# ---- Section 19s: THE PROSE INTERLOCKS, AT EVERY LAYER, INCLUDING THE OPERATORS -`
  — a ~150-line section (added 2026-08-25, owner ruling) covering the prose-generation gate's
  five interlock layers, running up to the printed banner at line 4792
  (`print("32. §20p ...")`).

Any existing citation to "§19s" (BUGS.md, other modules, prose) is now ambiguous between the
metrics-timestamp check and the prose-interlock battery — the exact failure mode Hard Rule
about duplicate tags exists to prevent. This needs the same treatment already applied to
§20e/§20f: rename one (the later, larger, more load-bearing "PROSE INTERLOCKS" section is the
better candidate to keep `19s`, since it is the one likely already cited by BUGS.md given its
size and owner-ruling status; the smaller metrics-timestamp section is the better candidate to
renumber) and leave a forwarding note the way §20e/§20f did.

### 2. MAJOR — check's own label promises a comparison against `tuning.py`; the code does not perform it

Line 3229:
```python
check("the threshold itself is the one tuning.py already settled on",
      _STx.MIN_CALLS_TO_JUDGE_RATE, 20,
      note="tuning.MIN_CALLS_TO_JUDGE=20 answers this same question for regime()")
```
This compares `standards.MIN_CALLS_TO_JUDGE_RATE` against the **literal `20`**, not against
`tuning.MIN_CALLS_TO_JUDGE`. The label claims it verifies the two are "the one ... already
settled on" (i.e., derived from the same source), but as written it would stay green even if
`standards.py` and `tuning.py` diverged, as long as `standards.py`'s value happened to still
equal 20 — the exact tautology-shaped risk this whole audit category is about.

The file already contains, at lines 6057–6087 (`order 495390283745`), a self-diagnosis of
precisely this defect ("which compares against a literal and would stay green if tuning.py and
standards.py diverged"), a correct fix applied to *a different, newer check* (`_STx_b3` /
`_TUNx_b3`, lines 6070–6079, which does compare identity against `tuning.MIN_CALLS_TO_JUDGE`
directly and additionally greps `standards.py`'s source for the derivation assignment), and an
explicit note that the original check at line 3229 was **not** touched
("PROPOSED EDIT for the coordinator (this agent does not own verify_math.py)", line 6083,
documentation-only, `check(..., True, True)`). That proposed edit was never applied — line 3229
still reads exactly as quoted above. This is a live, currently-unfixed instance of the project's
most-repeated defect shape, already diagnosed by a prior agent but not landed.

### 3. MINOR — a genuine tautology `check(label, True, True)`, self-labeled as intentional

Line 6083–6087, inside the `order 495390283745` block:
```python
check("[495390283745] verify_math.py's existing '...already settled on' check should compare "
      "against tuning.MIN_CALLS_TO_JUDGE directly, not the literal 20 -- PROPOSED EDIT for the "
      "coordinator (this agent does not own verify_math.py): "
      "check(\"the threshold itself is the one tuning.py already settled on\", "
      "_STx.MIN_CALLS_TO_JUDGE_RATE, _TUNx.MIN_CALLS_TO_JUDGE, note=...)",
      True, True,
      note="documentation-only row; the two lines above already give the coordinator a real, "
           "runnable version of this same intent that cannot be fooled by a coincidence")
```
This is a literal `check(x, True, True)` — the exact shape flagged as "the project's single
most-repeated finding." It is explicitly self-aware ("documentation-only row") and is backed by
two real, non-tautological checks immediately above it in the same block, so it is not hiding a
false green about any *quantity* — but it is still one more line counted into "1052 passed"
that cannot fail, and it is a message from one agent to a "coordinator" role embedded as
executable code rather than as a comment. Flagging as a QUESTION/MINOR rather than requiring
action: is this the intended long-term way for one audit batch to hand a same-file-restricted
proposal to another? If so it should probably be a comment, not a `check()` call, since
`check()` calls are exactly what future AST-scan audits (like this one) exist to distrust.

### 4. MINOR / QUESTION — several source-substring checks pin on a single generic word

The AST scan found 27 checks of the shape `"<literal>" in <other_module>_src` (reading another
module's `.py` file as text and searching for a substring). Most are well-justified in
surrounding comments (closure-scoped code that cannot be called directly, e.g. lines 6941–6947
for `completeness.py`, or a symptom "only visible in a file neither writer owns", line 2501).
A few pin on a single common identifier rather than a structural fragment, which is exactly the
fragility this audit's guidance calls out ("go red when the other module merely gets renamed,
go green when a comment happens to contain the string"). Verified currently correct (not false
greens today), but structurally thin:
- Line 2319: `"ALL_JOBS" in _allsweep_src` — currently backed by real code
  (`allsweep.py:358: for job in _ON.ALL_JOBS:`), but a comment at `allsweep.py:351` also
  contains the literal `ALL_JOBS`, so the check does not by itself distinguish "real use" from
  "mentioned in a comment"; it would stay green if line 358 were ever renamed or removed while
  the comment survived.
- Line 2783/2792: `'num_ctx' in _probe_src19ab` and `'eval_count' in _probe_src19ab` — single
  common words, not verified further here for comment-vs-code placement.

Not reporting these as false positives (they are not, right now) — reporting as a pattern
worth a follow-up pass: tighten to a code-shaped fragment (e.g. `_ON.ALL_JOBS` or
`for job in _ON.ALL_JOBS`) rather than the bare identifier, the same tightening already applied
elsewhere in this file (e.g. line 2507's `'"at": round(t0, 1), "tag"'`, which pins a whole
literal dict-key fragment, not just `at`).

### 5. Reviewed, no issue — `limit=`/`cap=` occurrences inside this file

Grepped every `limit=`/`cap=` in the file (guidance point 2, Hard Rule 0). All are either:
(a) an explicitly-labeled **test sample**, not a delivered roster — line 894,
`PR.build_all(limit=400)`, commented directly above as "A SAMPLE, and labelled as one: 400
profiles is plenty to prove round-tripping"; or (b) a parameterized call into another module's
own API for a specific micro-check (`BG.burgs_for(..., limit=3)` at line 1065 to check seed
determinism at one index, `limit=200` at lines 1067–1068 to compare coastal fractions) where
the un-limited call (`_bs = BG.burgs_for(424242, _f)`, line 1037) is what every roster-shape
check actually runs against; or (c) a positive test that another module's own `cap=` parameter
correctly keeps the *true, uncapped* count visible in a sibling field (lines 6688–6693,
`backfill.py`'s `cap=`, asserting `absent` "stays the UNCAPPED figure, so the truncation is
visible"). None of these truncate a roster this file itself reports as complete. No violation.

### 6. Reviewed, no issue — `silence.note()` tags inside this file

All 6 `silence.note()` calls in `verify_math.py` use symbolic labels
(`"verify_math.py:unrecognised-probe-cleanup"`, `"verify_math.py:S19ab-parse"`,
`"verify_math.py:S20e-parse"`, `"verify_math.py:atomic-probe-cleanup"`,
`"verify_math.py:S36-exec:" + name`) rather than bare line numbers, consistent with the
project's own rule against numeric tags (a rule this very file tests other modules against,
e.g. the `"none of address_space.py's silence.note tags are bare line numbers"` check). No
drift risk from line movement.

### 7. Reviewed, no issue — §20 lettered tags and the numbered `print()` banners (1–36)

Full census of every `print("N. ...")` banner (1 through 36) and every `# ----------- §20x`
inline tag (20a–20w, including the unprinted 20k/20l/20m/20n/20o-skipped/20t/20u/20v/20w):
all unique. The §20e/§20f collision documented at lines 3794–3806 as fixed earlier today by
another agent (m127/M17/m87/m88/m89/m108/m98 citations reassigned) is in fact fully resolved —
confirmed by direct grep, not by trusting the file's own claim.

### 8. Reviewed, no issue — `_raises()` and `check()` harness themselves (lines 1–95)

Both are carefully guarded against the exact failure classes named in this audit's guidance:
`check()` explicitly handles a non-numeric `got` against a float `want` (documented regression
from run #24, where an unguarded `abs(got - want)` TypeError silently truncated the whole
battery after the first such failure — verified the guard is in place and matches the fix
description). `_raises()` is explicitly exempted from `silence.note()` tagging with a
documented reason (its own deliberately-provoked exceptions were polluting
`state/failures.json` with 87 rows before run #24's fix). Both read as intentional, documented
design, not defects.

### 9. Reviewed, no issue — §20u / section 36 delegation machinery (lines 7061–7144)

The mechanism that execs the six `handoff/run35/checks_L*.py` files into isolated namespaces
(rather than splicing their source into this file) is explicitly engineered against the same
"check that cannot fail" risk: its own header comment (lines 7065–7080) documents that two of
the six sub-files carry their own `PASS, FAIL = [], []` and `def check(...)`, which — if pasted
in directly — would have silently reset this file's own accumulators mid-run. Fails closed on
missing file / parse error / no checks defined / sub-harness `sys.exit`. This also explains why
the live run prints 1,074 `OK`/`FAIL` lines total but the summary reads
"1052 passed, 1 FAILED": the sub-files' own internal `check()` calls print their own lines
(their own separate function, same output format) but are folded back into this file's
PASS/FAIL only as summarized/per-check-function rows, not one-for-one. Not a discrepancy, not a
defect — confirmed by reading the folding logic.

## Not found

- No `check(x, x)` self-comparison where both sides are literally the same non-boolean
  expression (checked by AST diff of the `got`/`want` argument text across all 932 call sites).
- No `or 1.0` / `or 1)` division-guard pattern anywhere in the file.
- No bare `except: pass` that swallows the exact condition a check exists to detect (all
  `except Exception` blocks read either raise-and-note or are themselves the subject of a
  check, per §20i/§20r's own hardening of this file's arithmetic).
- No stale hardcoded hit against a moved literal (`TODO`/`FIXME`/`XXX`/`HACK` grep: one hit,
  line 6941, an honestly-labeled TODO about `completeness.py`'s closure-scoping, not this
  file's own debt).

## Could not read

None — the full 7,144-line file was covered by the combination of direct reads (sections 1–18,
19s ×2, 20e–20w banners, 20u/36, and ~15 flagged spots) and exhaustive automated scans (every
`check()` call site via AST; every `§`/`Section 19x` tag via grep).
