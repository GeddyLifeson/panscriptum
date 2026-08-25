# Batch 01 — run33
Modules read: verify_math.py (4497 lines)

## FINDINGS

### 1. verify_math.py:3388-3392 — the console-window guard silently skips files it cannot parse, with no record and no assertion that it skipped nothing  [severity: MAJOR]
Section "§20e NO CONSOLE WINDOWS, EVER" (the owner's strongest-worded directive, quoted at
line 3364: "no command windows may EVER open") scans every `src/*.py` file's AST for unguarded
`subprocess` spawns. Its parse loop is:

```python
for _p20e in sorted(_glob20e.glob(os.path.join(_here19, "*.py"))):
    try:
        _t20e = _ast20e.parse(open(_p20e, encoding="utf-8").read())
    except SyntaxError:
        continue                      # allsweep's LINT tier owns syntax; not this check's job
```

A file that fails to parse is silently dropped from the scan — no entry is appended anywhere,
and neither `check()` at the end asserts that the skip list is empty. So a syntactically broken
`src/*.py` file (this project's own `local_agent.py` patches source files under model control,
and §20g documents this codebase's repeated real history of mid-write corruption from
non-atomic writes) could contain an *unguarded* `subprocess.Popen(...)` and this check would
still print a clean PASS on both `"every subprocess spawn in src/ suppresses its console
window"` and `"no os.system / os.popen / os.startfile anywhere in src/"` — the exact "check
that cannot fail" class the brief calls out, and the exact hazard this file's own earlier
section already named and fixed once.

This is not speculative: an almost identical AST scan earlier in the *same file*
(§19ab, lines 2517–2555, the `num_ctx` literal scan) hit this precise failure mode and was
repaired with an explicit `_unparsed19ab` list plus a dedicated
`check("every module was readable by the context-window scan", _unparsed19ab, [], ...)`, whose
own comment states the reasoning verbatim: *"A module this scan cannot parse is a module the
scan cannot clear, and swallowing that would let an offending site hide inside a broken file --
the check would go green BECAUSE something was wrong."* §20e's loop, added later in the file,
does not carry that same guard — it relies instead on the unverified claim that "allsweep's
LINT tier owns syntax," which is also a violation of this project's own CLAUDE.md Hard Rule -1
("INDEPENDENT — no two layers may share a failure mode"): the console-window check is supposed
to hold on its own, not because a separate tier is assumed to have already caught corruption.

### 2. verify_math.py — section banner numbers are duplicated (24, 25, 26 each printed twice for different sections) and 30/31 are skipped entirely  [severity: MINOR]
The `print("NN. §NNx  ...")` banners are this file's index into 30+ separately-dated incidents,
and are referenced throughout the file's own comments as the way a reader locates a given fix.
The numbering has drifted:

- Line 3294: `print("24. §20e  A LIVENESS REPORT MUST NOT DELETE THE REPORTER ...")`
- Line 3362: `print("24. §20e  NO CONSOLE WINDOWS, EVER ...")` — same number, same §-tag, different section.
- Line 3448: `print("25. §20f  RIGOR'S PROSE MUST NOT OUTLIVE RIGOR'S DATA ...")`
- Line 3500: `print("25. §20f  A PERMANENT REFUSAL MUST NOT BE FILED AS CONTENTION ...")` — same collision.
- Line 3636: `print("26. §20g  A SHARED FILE IS LANDED ...")`
- Line 4424: `print("26. §20q  A WRITE VERDICT THAT NOBODY READS ...")` — same top-level number reused with a different §-tag, 800 lines later.
- After `print("29. §20j  ...")` (line 3919) the next top-level banner is `print("32. §20p  ...")` (line 4318) — numbers 30 and 31 never appear as banners at all (§20k/§20l/§20m/§20n exist only as inline comment headers with no `print()`).

None of this touches any `check()` call's truth value — it is purely the human-facing console
output — but it directly undermines the one property this file leans on hardest for
traceability (e.g. "these pin the boundary" / "run #NN" cross-references throughout). A reader
grepping console output for "§20q" or "run #30/#31" cannot use the printed numbering to find
them reliably.

### 3. verify_math.py:1508 — a comment claims the variable it sits on is "defined ~1600 lines later"  [severity: INFO]
```python
_here19h = os.path.dirname(os.path.abspath(__file__))   # _here19h is defined ~1600 lines later
```
This line *is* the definition of `_here19h`, on the spot — it is never redefined again (`grep`
confirms its only other appearances are four later reads of `os.path.join(_here19h, ...)`
within the same §19h/§19h-bis block, all downstream of this line). The comment appears to be a
stray copy-paste from documentation about a similarly-named variable, `_here19`, which genuinely
is defined ~1600 lines later at line 3119 and is used pervasively from there on. Harmless to
behavior, but misleading to a future reader trying to understand the file's variable lifetime.

## QUESTIONS
None that I could not resolve myself. I traced one candidate finding to ground before writing
this report and it turned out not to be a defect: `_MAXED` (lines 647-648, §12 "ANCHOR
VALIDATION") builds a 10-axis maxed-score dict that omits `"volition"`, unlike every other
full-axis fixture in the file (`_ks`, `_KEN`, both 8/11-axis). I read `assay.py`'s `assay()`
function to check whether an axis silently absent from `scores` (as opposed to explicitly
`NONE`/`UNESTIMABLE`/`INAPPLICABLE`) could dilute the composite score and understate the
ceiling test. It does not: `composite` is a weighted average taken only over axes present in
`used`, so omitting one maxed axis from the input dict still yields `composite == 10.0` and the
ceiling/promotion assertions the test makes remain correct regardless. Noted here only so a
future auditor does not have to re-trace the same path — this is not a finding.

## CLEAN
`verify_math.py` was read in full, sequentially, start to finish (all 4497 lines, all ~40
numbered/lettered sections). Aside from the three items above, I found no tautological checks
(comparisons of a literal to itself — the several `f(x) == f(x)` determinism checks are
legitimate double-evaluation idempotence tests, not tautologies), no phantom checks asserting
about removed functionality, and no `note=` text that contradicted its assertion. The file's
own helper functions (`check`, `_raises`, `_tier_counts`, `_nesting_violations`, `_mode_stable`,
`_json_try`, `_via_gets`, `_dict_guarded`, `_writes_the_config20p`, `_branching`) were traced by
hand and are correctly implemented against what their names and comments claim. The float/exact
comparison logic in `check()` itself (the single point of failure for the whole battery) is
sound. This is an unusually well-hardened file — the bulk of it is itself a record of 30+ prior
incidents each pinned with a regression check, several of them (§19ab, §20i, §20j, §20k) being
exactly the "a check that cannot fail" class the brief asks auditors to hunt for, already found
and fixed by the project's own prior maintenance runs. Finding #1 above is a recurrence of that
same class in a section added after the fix that should have generalized from it.
