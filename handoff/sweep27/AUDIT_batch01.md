# BATCH 01 — verify_math.py sweep (run27)

Modules read in full, line by line, no sampling: `src/verify_math.py` (3923 lines — the entire file, start to end).

This file is itself the project's independent-verification test suite (600+ `check()` calls
across ~29 numbered sections). It is exceptionally heavily audited already — every section
carries a dated "found this defect, here is the pinned regression check" narrative going back
through ~26 maintenance runs. Almost every obvious defect class the six-lens brief asks for
(swallowed failures, caps, two-writer races, concurrency races, stale comments) has already been
hunted down and fixed *inside this very file*, with the fix pinned by a check that fails under
the old code. Because of that, this pass found no high-severity live bugs in verify_math.py's own
logic. What follows is what a full line-by-line read actually turned up: two Hard-Rule-0 policy
questions the file's own standard would flag if applied to itself, one dormant variable-aliasing
landmine, one recurring test-design weakness (verification-by-grep instead of verification-by-
execution) that partly undercuts the file's own stated philosophy, and a cosmetic labelling slip.

None of these change the pass/fail verdict of the suite as currently written; that is exactly why
they are worth recording rather than dismissing.

---

## Finding 1 — `_problems[:3]` truncates the diagnostic note on a FAIL (Hard Rule 0)

**File:line:** `src/verify_math.py:286`
**Severity:** low
**Status:** CONFIRMED

```python
_problems = D.check_graph()
check("the derivation graph closes (no dangling, rootless, or cyclic quantities)",
      len(_problems), 0, note="; ".join(_problems[:3]))
```

The check's pass/fail *verdict* uses `len(_problems)` — unaffected by the slice, so the test
itself is sound. But the diagnostic `note` shown to a human when this fails is capped to the
first 3 problems via `_problems[:3]`. If `D.check_graph()` ever returns, say, 40 dangling
quantities, the FAIL line prints 3 of them and silently drops the other 37 — exactly the kind of
truncation Hard Rule 0 names ("a cap is a violation EVEN IF it looks reasonable"), applied here
to this project's own verification tooling. It's a diagnostic-message cap, not a data-loss cap,
so the practical harm is small (a human debugging the failure sees an incomplete list and has to
re-run `D.check_graph()` directly to see the rest) — but it is a literal `[:N]` slice with no
comment acknowledging or defending it, unlike every other cap this file itself calls out
elsewhere (contrast with `PR.build_all(limit=400)` at Finding 2, which *is* defended in prose).

**Question for the supervisor:** is a diagnostic-note cap inside the verification suite itself
exempt from Hard Rule 0, or should this be `"; ".join(_problems)` (full list) same as the rest of
this file's notes do?

---

## Finding 2 — `PR.build_all(limit=400)` samples the profile corpus for round-trip testing

**File:line:** `src/verify_math.py:811`
**Severity:** low
**Status:** CONFIRMED (cap exists) / policy question (whether it's a violation)

```python
# A SAMPLE, and labelled as one: 400 profiles is plenty to prove round-tripping and far
# cheaper than the full set. If decode ever breaks it breaks on the first row, not the 40,001st.
_rows = PR.build_all(limit=400)
```

This is a real, explicit numeric cap on how much of the address-space profile corpus gets
round-trip verified, passed straight through to `profile.build_all`'s own `limit=` parameter.
The comment is honest about it being a sample (which is the good-faith opposite of the
"docstring denies the cap exists" pattern the brief calls out as highest-value) — but Hard Rule 0
as stated to this sweep is unconditional ("this project forbids ANY cap, sample, truncation, or
limit on anything... even if it looks reasonable"). Taken literally, a 400-of-N sample is still a
sample. The mitigating argument in the comment (decode either round-trips or it doesn't, and a
systematic decode bug will surface on early rows, not just the 40,001st) is reasonable — but that
is a judgment call about acceptable risk, which is precisely the kind of reasoning Hard Rule 0 is
written to foreclose elsewhere in this codebase (see feats.discover's `extra=` cap refusal at
verify_math.py:1955-1966, or the genre/grounding `cap=` refusals at :1978-2003, both of which
were rewritten specifically so that a "this cap is obviously fine" argument could no longer be
made in code).

**Question for the supervisor:** should this line be changed to `PR.build_all()` (no limit) for
full-corpus round-trip verification, consistent with how every other numeric cap in this file's
own recent sections (19g, 19i) was treated as something to *refuse*, not something to *defend*?

---

## Finding 3 — the local alias `_CB` is bound to two different modules in one script

**File:line:** `src/verify_math.py:1483` (bound to `cascade_bridge`) and `src/verify_math.py:2188`
(rebound to `context_budget`)
**Severity:** low
**Status:** CONFIRMED (the rebinding is real); currently dormant (no observed wrong-module read)

```python
# line 1483, Section 19h
import cascade_bridge as _CB                                            # noqa: E402
...
_cand = [m.bucket for m in _CB.widen_candidates(_models)]                # cascade_bridge
...                                                                       # (all _CB.* uses through line 1560 are cascade_bridge)

# line 2188, Section 19v
import context_budget as _CB     # noqa: E402
...
_CB.system_for("feats", ...)                                             # context_budget
```

`_CB` is used as the local name for `cascade_bridge` throughout Section 19h (lines 1483–1560),
then silently rebound to `context_budget` at line 2188 for Section 19v onward (lines 2188–2248).
Every current use of `_CB.` is correctly scoped on one side or the other of the reassignment (I
verified every occurrence — 22 hits total — none crosses the boundary), so this is not producing
a wrong answer today. It is a maintenance landmine: this file is edited by inserting whole dated
sections (the 19x/20x naming makes that obvious), and if a future section is inserted *between*
lines 1560 and 2188 that adds a new `cascade_bridge` check reusing the name `_CB` out of habit —
or if Section 19v's block is ever moved earlier in a refactor — the reference would silently
resolve to the wrong module. Because `cascade_bridge` and `context_budget` don't currently share
an attribute name that both branches call, today's failure mode would be a loud `AttributeError`
rather than a silently wrong value — but that's incidental, not structural, protection. Every
other section in this file picks a section-qualified alias (`_CB22b`, `_cb20h`, `_cb20i`,
`_cb20j`, `_CBm`, `_GL` vs `_GLx`, `_here19` vs `_here19h`) specifically to avoid this; `_CB` at
1483/2188 is the one place that plain two-letter alias got reused for a second module.

**Recommendation:** rename the Section 19h binding (or the 19v one) to a section-qualified alias
consistent with the rest of the file's own convention.

---

## Finding 4 — several regression checks verify by grepping source text, not by calling the function

**File:line:** representative sites: `src/verify_math.py:2262-2268` (Section 19s),
`src/verify_math.py:2094-2098` (Section 19q); the pattern recurs at many more sites throughout
Sections 19–29 (e.g. :1500-1507, :1521-1524, :1531, :3116-3126, :3184-3186, :3493-3502)
**Severity:** medium
**Status:** CONFIRMED (pattern exists as described); severity is a judgment call, framed below

The file's own header states the design principle it is built on:

> "Nothing here calls the modules' own helpers to check the modules' own helpers -- each
> assertion recomputes the quantity from first principles and compares."

Most of the file honors this rigorously — hundreds of checks call the real function and compare
against an independently-derived value. But a large and growing fraction of the later sections
(everything from Section 18 onward, i.e. the maintenance-run additions) instead do this:

```python
# Section 19s, :2262-2268 — no call to pipeline._metric or cascade_bridge._metric anywhere nearby
check("pipeline._metric's row carries a timestamp",
      '"at": round(t0, 1), "tag"' in _mx_src["pipeline"], True, ...)
check("cascade_bridge._metric's row carries a timestamp",
      '"at": round(t0, 1)' in _mx_src["cascade_bridge"], True, ...)
```

```python
# Section 19q, :2094-2098 — no call to pipeline.phase_entrypass anywhere nearby
check("the entrypass prompt counts the entries it SHOWED, not the whole span",
      "Return results for all {len(lines)} entries" in _pipe_src, True, ...)
check("the struck-entry skip that makes lines shorter than batch is still there",
      'if e.get("excluded"):' in _pipe_src, True, ...)
```

These are **presence-of-a-literal-substring-in-a-source-file** checks, not tests of behavior.
Concretely, each one has two independent failure modes the "first principles" standard is meant
to rule out:

1. **False pass:** the exact substring could exist inside a comment, a docstring, a dead
   `if False:` branch, or an earlier/later unreachable code path, and the check would still read
   green while the described defect is still live. (verify_math.py itself names this exact risk
   at :2262 in the m62 write-up, but does not defend against it for its own checks.)
2. **False fail:** a semantically-identical fix phrased with different whitespace, different key
   ordering, an f-string instead of `.format`, or building the dict incrementally instead of as
   one literal, would flip these specific checks red even though the underlying regression is
   genuinely fixed — which is a worse failure mode for a maintenance-facing suite than it sounds,
   because a red result here reads as "the m62/19q regression is back," sending the next
   maintenance run chasing a phantom.

This is not a uniform criticism — many nearby sections correctly pair a source-scan (to confirm
a fix landed at a specific site) with an adjacent behavioral check that actually exercises the
function (e.g. Section 19h pairs the `record_unrecognised(pinned.bucket` source-scan at :1500
with real calls to `_CB.record_unrecognised(...)` at :1538-1552). And for checks that assert
*absence* of a string (e.g. the erased-paid-lane checks at :1500-1507, or the "no bare TEMP
fallback" check at :2693-2696), grepping is the *right* tool — you cannot behaviorally prove a
code path was deleted, only textually prove it isn't there. The concern here is narrower: the
handful of sites (19s's two `_metric` checks and 19q's two entrypass-prompt checks are the
cleanest examples) that assert **presence** with **no accompanying behavioral check at all**,
where a call to the real function and an inspection of its actual output would give a strictly
stronger guarantee for the same or less code.

**Recommendation, framed as a question:** for the 19s (`_metric` timestamp) and 19q (entrypass
prompt count) checks specifically, would it be worth calling `pipeline._metric` /
`cascade_bridge._metric` and `pipeline.phase_entrypass` with a mocked transport (the file already
does exactly this kind of mocking in Section 18b for `assay_entity`) and asserting on the actual
emitted row / actual prompt text, rather than on the source string that produces them?

---

## Finding 5 — cosmetic: printed section numbers are duplicated / non-monotonic

**File:line:** `src/verify_math.py:3271` and `:3339` both print `"24. §20e ..."` for two
different topics ("A LIVENESS REPORT MUST NOT DELETE THE REPORTER" vs "NO CONSOLE WINDOWS,
EVER"); `:3425` and `:3477` both print `"25. §20f ..."` for two different topics ("RIGOR'S PROSE
MUST NOT OUTLIVE RIGOR'S DATA" vs "A PERMANENT REFUSAL MUST NOT BE FILED AS CONTENTION"). Section
"19" is never printed as its own top-level banner — the 19a–19z subsections all run under the
"18. THE DAY'S JOINTS" banner printed at :991.
**Severity:** low
**Status:** CONFIRMED

Purely a console-output / human-navigation issue (the numbers are print-statement labels only,
not used by any check or by `PASS`/`FAIL` bookkeeping), so it has zero effect on the suite's
verdict. Worth a one-line fix only because a reader scrolling `RESULT:` output or grepping
`grep '^print("2' src/verify_math.py` to jump to a section by number will land on the wrong one
for §20e/§20f, and because this file's own §20f/§20g/§20h sections exist specifically to catch
"the machine's account of itself is wrong" bugs elsewhere in the codebase — the numbering slip is
a small instance of the same class, in the file that is most focused on stamping it out
everywhere else.

---

## Not flagged, but noted as reviewed and clean

For the record (so a later pass doesn't re-spend time on these), the following areas received
close scrutiny and were found correct:

- `check()` itself (:62-79): the float/non-float branching, the `bool`-is-`int` carve-out, and
  the tolerance formula (`tol * max(1.0, abs(want))`) are all sound and match their comments.
- The `_needle20i`/`_needles20i` self-referential "disarmed check" detector (:3761-3826): the
  runtime string-concatenation trick that lets it scan for its own disarm pattern without
  matching its own definition line was traced character-by-character and is correctly
  constructed; the guard's own dogfood tests (`_disarmed20i` / `_ordinary20i`) correctly exercise
  both the true-positive and true-negative cases.
- `_tier_counts` / `_nesting_violations` (:27-42): the parent/child direction of the nesting
  check was traced against the charter's own tier ordering (hyperverse coarsest → multiverse
  finest) and is oriented correctly.
- `_row` (function, :1982) is later shadowed by an unrelated `_row` (dict, :2211) in Section 19v.
  This looked like a name-collision bug at first read but is harmless: every call to `_row(...)`
  as a function occurs before the reassignment, and the script runs once, top-to-bottom.
  Mentioned here only so it isn't re-flagged; not included as a numbered finding because,
  unlike Finding 3's `_CB`, this one's function-vs-value shadowing would raise an immediate
  `TypeError` on any accidental post-reassignment call, rather than silently resolving to a
  wrong module.
- Threading-based concurrency probes (Section 19t's `_gl_lock`, 19ad's `_lk19ad`) correctly guard
  their shared counters; no race in the test harness itself.
- The two-writer-contract regression tests (Section 18c, 19j, 20i) all write their "disk state"
  fixtures with a raw `open(...,'w')+json.dump` — this looked like a Two-Writer-Contract
  violation at first grep, but every such write targets a file inside a throwaway
  `tempfile.mkdtemp()` directory being used purely as test fixture setup (simulating "what's
  already on disk" before calling the real `pipeline.write_record`/`write_record_catalogue`
  under test), never a real shared production file under `state/` or `data/`. Not a violation.
