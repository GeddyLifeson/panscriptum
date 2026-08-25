# BATCH 01 — verify_math.py sweep (run28)

Module read in full, line by line, start to end, no sampling: `src/verify_math.py` — 3947 lines
(grew from 3923 lines at run27's read; the extra ~24 lines are in-place additions inside existing
Sections 25/§20f rather than a new top-level section — traced and confirmed no new section number
was added since run27).

This is the project's independent-verification suite itself (630+ `check()` calls across ~29
numbered sections), and it is by a wide margin the most heavily self-audited file in the repo:
every section carries a dated "found this defect here, here is the pinned regression check"
narrative going back ~27 maintenance runs, including several rounds where the suite audited *its
own* prior defects (the `check()` TypeError crash, the always-true disjunct disarm, the source-grep
false-fail class). Run27's batch01 already did a full line-by-line pass and filed 5 findings. I
re-verified every one of them against the CURRENT file: **all five are still present, unchanged,
line-for-line identical** — none were fixed and 3 of the 5 never made it into NEXT_STEPS.md's
tracked backlog (only the two Hard-Rule-0 caps did). Re-recording all five as KNOWN/STILL OPEN
below so the tracking gap is visible, plus one genuinely NEW finding this pass turned up.

---

## Finding 1 (KNOWN, STILL OPEN) — `_problems[:3]` truncates the diagnostic note on a FAIL

**File:line:** `src/verify_math.py:286`
**Severity:** LOW | **Status:** KNOWN (run27 batch01 Finding 1; also tracked in
NEXT_STEPS.md §3 "Silent truncation" list) — confirmed unchanged this run.

```python
_problems = D.check_graph()
check("the derivation graph closes (no dangling, rootless, or cyclic quantities)",
      len(_problems), 0, note="; ".join(_problems[:3]))
```

The pass/fail verdict (`len(_problems)`) is unaffected, but the human-facing diagnostic note caps
at 3 problems with no comment defending the cap — a literal `[:N]` inside the project's own
Hard-Rule-0-enforcing test suite. If `check_graph()` ever returns 40 dangling quantities, the FAIL
line shows 3 and silently drops 37.

---

## Finding 2 (KNOWN, STILL OPEN) — `PR.build_all(limit=400)` samples the profile corpus

**File:line:** `src/verify_math.py:811`
**Severity:** LOW | **Status:** KNOWN (run27 batch01 Finding 2; tracked in NEXT_STEPS.md §3) —
confirmed unchanged this run.

```python
# A SAMPLE, and labelled as one: 400 profiles is plenty to prove round-tripping...
_rows = PR.build_all(limit=400)
```

Honestly labelled as a sample in the comment (unlike Finding 1), but Hard Rule 0 as stated to this
sweep is unconditional, and this is the same file that rewrote `feats.discover`'s `extra=` and
`genre`/`grounding`'s `cap=` specifically so a "this cap is obviously fine" argument could no
longer be made in code (Sections 19g/19i, ~line 1459 and ~1584). The owner ruling requested in
NEXT_STEPS is still outstanding.

---

## Finding 3 (KNOWN, STILL OPEN, NOT in NEXT_STEPS backlog) — `_CB` bound to two different modules

**File:line:** `src/verify_math.py:1483` (`import cascade_bridge as _CB`) and `:2188`
(`import context_budget as _CB`)
**Severity:** LOW | **Status:** KNOWN (run27 batch01 Finding 3) — confirmed unchanged this run,
line numbers identical; **this finding was dropped from NEXT_STEPS.md's tracked backlog even
though it was never fixed.**

```python
# line 1483, Section 19h
import cascade_bridge as _CB                                            # noqa: E402
...                                                                       # _CB.* == cascade_bridge through line 1560
# line 2188, Section 19v
import context_budget as _CB     # noqa: E402
...                                                                       # _CB.* == context_budget from here on
```

Every current use of `_CB.` stays correctly scoped on one side or the other of the reassignment
(re-verified: no cross-boundary reads), so this is not producing a wrong answer today. It remains
a maintenance landmine: this file is edited by inserting whole dated sections, and a future
section inserted between 1560 and 2188 that reuses `_CB` out of habit for a new `cascade_bridge`
check would silently resolve to `context_budget` instead — or vice versa if 19v is ever moved
earlier. Every other section picks a section-qualified alias (`_CB22b`, `_cb20h`, `_cb20i`,
`_cb20j`, `_CBm`, `_GL` vs `_GLx`) specifically to avoid this; `_CB` is the one plain two-letter
alias reused for a second module.

---

## Finding 4 (KNOWN, STILL OPEN) — several regression checks verify by grepping source text

**File:line:** representative sites unchanged from run27: `:2093-2098` (Section 19q,
`"Return results for all {len(lines)} entries" in _pipe_src`), `:2264-2269` (Section 19s, the two
`_metric` timestamp checks against `_mx_src[...]`); the pattern recurs at many more sites
throughout Sections 19-29 (`:1496-1531`, `:3121-3141`, `:3186-3202`, `:3490-3514`, `:3654-3698`,
`:3869-3910`).
**Severity:** MED | **Status:** KNOWN (run27 batch01 Finding 4; the general shape is also flagged
in NEXT_STEPS.md's "Machinery worth building" section, citing this file by name and these two
line ranges) — confirmed unchanged this run.

The file's own header states: "Nothing here calls the modules' own helpers to check the modules'
own helpers — each assertion recomputes the quantity from first principles and compares." Most of
the file honors this. But the maintenance-run-added Sections 18 onward increasingly substitute
**presence-of-a-literal-substring-in-a-source-file** for a behavioral call:

```python
# :2093-2098 — no call to pipeline.phase_entrypass anywhere nearby
check("the entrypass prompt counts the entries it SHOWED, not the whole span",
      "Return results for all {len(lines)} entries" in _pipe_src, True, ...)
```

Two failure modes this creates, both already realized once in this same file (see the run #26
incident narrated at lines 3540-3567, where exactly this class of check false-failed on a correct
rename): a **false pass** if the substring survives in a comment/dead branch while the real
behavior regresses, and a **false fail** on any semantically-identical rephrasing. The file is
self-aware of this exact risk (it names it explicitly at ~line 2258 while writing the very check
that has it) but does not defend against it for its own checks.

---

## Finding 5 (KNOWN, STILL OPEN, NOT in NEXT_STEPS backlog) — duplicated/non-monotonic printed section numbers

**File:line:** `:3271` and `:3339` both print `"24. §20e ..."` for two unrelated topics (the
liveness-report fix vs the no-console-windows guard); `:3425` and `:3477` both print
`"25. §20f ..."` for two unrelated topics (rigor's stale prose vs the auth-bench permanent-refusal
fix). Section "19" is never printed as its own top-level banner — 19a-19z all run silently under
the "18. THE DAY'S JOINTS" banner at `:991`.
**Severity:** LOW | **Status:** KNOWN (run27 batch01 Finding 5) — confirmed unchanged, exact same
four line numbers; **dropped from NEXT_STEPS.md's tracked backlog, never fixed.**

Purely cosmetic (print-only, doesn't touch `PASS`/`FAIL`), but this is the file whose own
§20f/§20g/§20h sections exist specifically to catch "the machine's account of itself is wrong" —
this is a small instance of the same class, in the section most focused on stamping it out
everywhere else in the codebase.

---

## Finding 6 (NEW) — two self-test fixtures use fixed shared-directory filenames instead of a per-process temp dir, racing under the file's own documented concurrent-invocation pattern

**File:line:** `src/verify_math.py:1535` (`_CB.UNRECOGNISED = os.path.join(_here19h, "..",
"state", "_VM_UNRECOGNISED_TEST.json")`) and `:3592-3613` (`_probe20g = os.path.join(_here19,
"..", "state", "_VM_ATOMIC_PROBE.json")`, written/read/deleted across three separate `check()`
calls before being removed in a `finally`).
**Severity:** MED | **Status:** NEW

```python
# :3592
_probe20g = os.path.join(_here19, "..", "state", "_VM_ATOMIC_PROBE.json")
try:
    check("write_json lands the file and returns True",
          _sil20g.write_json(_probe20g, {"z": 1, "a": [1, 2]}, indent=2, sort_keys=True), True)
    check("write_json round-trips exactly",
          json.load(open(_probe20g, encoding="utf-8")), {"z": 1, "a": [1, 2]})
    check("write_json leaves no temp file behind",
          [f for f in os.listdir(os.path.dirname(_probe20g))
           if f.startswith("_VM_ATOMIC_PROBE") and f.endswith(".tmp")], [])
    ...
finally:
    try:
        if os.path.exists(_probe20g):
            os.remove(_probe20g)
    except Exception:
        pass
```

Both fixtures live under the real `state/` directory with a **fixed, non-unique filename** —
unlike every other test fixture in this file (dozens of sites), which correctly uses
`tempfile.mkdtemp()` to get a private, collision-proof directory per invocation (Sections 18c,
18d, 19d, 19k, 19u, 19x, 19ad, 20i all do this correctly). This file's own §20a/§20e commentary
states as fact that verify_math.py is invoked concurrently from multiple call sites: "the suite
runs from the foreman's patch lane, from allsweep, and from every maintenance pass" (~line
3344-3346), and separately warns (NEXT_STEPS lesson 18a) that two standing processes overlapping
on one machine is a live, previously-observed failure class for this project generally.

Concrete failure scenario: two `verify_math.py` invocations overlap (patch-lane run + a manual
maintenance run, or two foreman-triggered lint passes). Process A reaches the `write_json lands
the file` check and its own `write_json` call is mid-flight, having created its own
pid/thread-uniquely-named temp file (`silence.write_json`'s own temp-naming fix, verified earlier
in this same section) inside `state/`. Process B, running concurrently, executes its "leaves no
temp file behind" `os.listdir` scan at that exact moment and picks up **A's legitimate in-flight
temp file**, which also matches the `_VM_ATOMIC_PROBE*.tmp` glob — B's check FAILs on a temp file
that isn't even B's. Worse: if A's `finally: os.remove(_probe20g)` fires between B's `write_json`
call and B's subsequent `json.load(open(_probe20g, ...))` read-back, B's read raises
`FileNotFoundError` — an unhandled exception that (per this file's own §20i regression, lines
3762-3781) is exactly the class of defect that used to take the *entire remaining suite* down
silently, because nothing wraps `verify_math.py`'s top-level statements. The `_VM_UNRECOGNISED_TEST.json`
fixture at line 1535 has the identical fixed-path hazard one section earlier, minus the file-removal
race (it's cleaned up by reassigning `_CB.UNRECOGNISED` back, not by deleting a shared path, but
still writes/reads a fixed filename two concurrent processes would collide on).

**Fix shape:** give both fixtures a `tempfile.mkdtemp()`-scoped path (or at minimum suffix the
filename with `os.getpid()`), consistent with the rest of the file's own established pattern.

---

## Not re-flagged, reviewed and confirmed still clean (per run27's assessment, re-verified this run)

- `check()` itself (:63-81): float/non-float branching, `bool`-is-`int` carve-out, and the
  relative-tolerance formula are sound.
- `_tier_counts`/`_nesting_violations` (:26-41): parent/child direction re-traced against the
  charter's tier ordering (hyperverse coarsest -> multiverse finest); correctly oriented.
- The `_needle20i`/`_needles20i` self-referential disarm-detector (:3783-3849): re-traced, still
  correctly constructed, dogfoods both a true-positive and true-negative case.
- Two-writer-contract regression fixtures (Sections 18c, 19j, 20i) that use raw
  `open(...,'w')+json.dump`: all target files inside throwaway `tempfile.mkdtemp()` directories
  used purely as "what's already on disk" setup before calling the real `write_record`/
  `write_record_catalogue` under test — not a real shared production file. Not a violation.
- `_row` function (:1982) shadowed by an unrelated `_row` dict (:2211) in Section 19v: every
  functional use precedes the reassignment; harmless given the script runs once top-to-bottom.

## Summary

No high-severity live logic bug found in verify_math.py's own code this run. The file is
exceptionally well-audited already; the honest yield of a full line-by-line re-read is confirming
five prior findings are still unrepaired (two tracked in NEXT_STEPS, three quietly dropped from
that tracking despite being real and open), plus one new concurrency finding (Finding 6) that
follows directly from evidence already sitting in this file's own comments about how and how often
it gets invoked.
