# sweep37 / batch01 — src/verify_math.py (7,257 lines, 934 `check()` call sites, 1,055 checks)

Read **in full**, top to bottom, in slices, on 2026-08-28. Every finding below was verified
against source, and where possible demonstrated by running the predicate on a crafted input.
No source file was edited.

Battery as it stands this run: **1054 passed, 1 FAILED** (`PYTHONIOENCODING=utf-8
C:/Users/imarl/miniconda3/python.exe src/verify_math.py`). The single failure is finding **M2**
below and is a defect in the check, not in the library.

---

## FINDINGS BY SEVERITY

MAJOR: 6  ·  MINOR: 11  ·  INFO: 4

---

## MAJOR

### M1 — §20y's tag-uniqueness detector is blind to two thirds of the tags, including two of the three collisions it was written for
**Where:** `src/verify_math.py:7232-7248`
**Confidence:** certain (measured).

§20y was added in run #36 after three tag collisions (§20e, §20f, §19s) so that "the next one
cannot arrive silently". Its scanner reads only lines matching `# ---- Section <tag>:`.

Measured over the current file:

| header form | count | seen by §20y |
|---|---|---|
| `# ---- Section <tag>: ...` | 41 | yes |
| `print("NN. §<tag>  ...")` | 17 | **no** |
| `# ------- §<tag> <prose>` (inline dashed) | 4 | **no** |

So **21 of the 62 section tags in this file are invisible to the detector.** And the invisible
set is exactly where the historical collisions lived: §20e is a `print(` header at :3827, §20f
is a `print(` header at :3937. Neither has ever had a `# ---- Section` line. **§20y could not
have detected the two collisions it cites as its motivation, and cannot detect their
recurrence.** It would also miss a collision between a `# ---- Section 20e:` header and the
existing print-style §20e.

The 17 invisible print tags: 20a 20b 20c 20d 20v 20e 20f 20w 20g 20h 20i 20j 20p 20q 20r 20s 20u.
The 4 invisible inline tags: 20k 20l 20m 20n.

No duplicate exists *right now* across all three forms (41 + 17 + 4 = 62 distinct tags), so this
is a broken detector, not a live collision.

Related, same site: the companion canary `len(_tags20y) > 40` (:7246) currently evaluates
**41 > 40**. One header renamed to another form and the canary goes red; two and the whole scan
silently matches almost nothing. A floor with one unit of headroom is not a floor.

---

### M2 — §20n holds the *newest* sweep to completeness, so the SAFETY-tier battery is red for the entire duration of every sweep
**Where:** `src/verify_math.py:4637-4644`
**Confidence:** certain (this is the one live FAILED row).

```
_run20n = _SP20n.latest_run()
check("the live sweep proves its own completeness",
      _SP20n.missing(_run20n) if _run20n else ["<no sweep on record>"], [], ...)
```

`sweep_plan.latest_run()` returns the newest run label. `sweep_plan` has no notion of a run being
*finished*. So from the moment a sweep's first batch calls `record()` until its last batch does,
this row is red.

Measured now, mid-run37:

```
run33  covered=109  missing=5
run34  covered=113  missing=1   -> ['canon_backup.py']
run35  covered=113  missing=1   -> ['canon_backup.py']
run36  covered=114  missing=0
run37  covered=9    missing=105     <-- latest_run(), this sweep, in flight
```

Two consequences, both bad:

1. Run #34 and run #35 each *ended* with `canon_backup.py` unrecorded, so this row was red
   continuously from the end of run34 until run36 completed — days, on a HIGH-consequence
   battery. Nobody could distinguish that from a real regression.
2. Right now, and for the rest of run37, `verify_math.py` exits 1. Per Hard Rule -1 a failing
   battery is a **SAFETY** event: "No run may claim success while this stands." Every batch of
   this sweep, `allsweep`'s VERIFIERS tier, `drill`, and the foreman's patch lane all see the
   battery BROKEN — *because a sweep is running*, i.e. precisely when the most agents are
   reading it. This is the file's own "a battery that cries wolf gets read less carefully"
   (:3674) committed by the battery.

The run #31 comment at :4630-4636 correctly diagnosed the previous form (a hardcoded
`missing("run29")`) but the replacement swapped a permanently-stale question for a
permanently-unanswerable-while-working one. The right subject is the newest *completed* run, or
`latest_run()` excluding a run whose batches are still landing.

---

### M3 — order 495390283745's enforcement row cannot fail: its needle matches its own definition line
**Where:** `src/verify_math.py:6165-6172`
**Confidence:** certain (demonstrated).

```
_selfsrc_b3 = open(os.path.abspath(__file__), encoding="utf-8").read()
_want_b3   = "_STx.MIN_CALLS_TO_JUDGE_RATE, _TUNx.MIN_CALLS_TO_JUDGE"
_banned_b3 = "_STx.MIN_CALLS_TO_JUDGE_RATE, %d" % _TUNx_b3.MIN_CALLS_TO_JUDGE
check(..., (_want_b3 in _selfsrc_b3, _banned_b3 in _selfsrc_b3), (True, False), ...)
```

The comment three lines above says the needle is "ASSEMBLED AT RUNTIME rather than spelled out,
because a source-text check that contains its own forbidden string always finds itself and can
never go green." That reasoning was applied to `_banned_b3` and **not** to `_want_b3`, which is
a plain literal. The needle occurs on exactly two lines of the file:

```
3234       _STx.MIN_CALLS_TO_JUDGE_RATE, _TUNx.MIN_CALLS_TO_JUDGE,     <- the site under test
6166  _want_b3 = "_STx.MIN_CALLS_TO_JUDGE_RATE, _TUNx.MIN_CALLS_TO_JUDGE"   <- itself
```

Demonstrated by deleting the whole check at :3233-3236 from an in-memory copy:

```
site deleted entirely ->  want-half: True   banned-half: False
verdict of the check: True      (i.e. still GREEN)
```

Delete the row this exists to enforce and it reads green. The `banned` half still catches the one
specific reversion to the current literal, so the check is not entirely toothless — but the half
that asserts the site *exists and says the right thing* is a tautology. This is the exact fault
the row's own comment (:6156-6161) narrates having just repaired one row earlier.

---

### M4 — §20q's per-phase scan conflates nested `def`s: the §20p fault, unrepaired one section later
**Where:** `src/verify_math.py:5020-5032`
**Confidence:** certain (demonstrated); currently latent in `pipeline.py`.

§20p was repaired today with `_own_nodes20p` (:4883-4907), whose docstring explains that
`ast.walk` descends into nested `def`s and so credits a parent with everything its children do —
"this check fires on a CO-OCCURRENCE, so conflating two innocent siblings manufactures a guilty
parent." §20q, 90 lines below, is the same co-occurrence shape and still uses bare `ast.walk`:

```
_calls20q = {c.func.id for c in _ast20q.walk(_fn20q) if isinstance(c, ast.Call) ...}
if "land_json" in _calls20q and "gate_done" not in _calls20q:
```

Demonstrated on a synthetic phase whose *nested helper* calls `gate_done` while the phase itself
lands artifacts and never consults it:

```
walk-based flags it?  False      <- what §20q does: MISSES the violation
own-nodes flags it?   True       <- what §20p does
```

This is not hypothetical shape-hunting: `pipeline.py` already has three phase functions that both
touch these symbols **and** contain nested `def`s —

```
phase_cosmology  (pipeline.py:1803)  nested: _kind
phase_history    (pipeline.py:1881)  nested: depth
phase_shelve     (pipeline.py:1995)  nested: _phase_input, spine_of
```

Both scans return `[]` today, so nothing is currently hidden; one edit that moves a `gate_done()`
call into (or a `land_json()` call out of) a nested helper flips them apart silently, in either
direction. `_discarded20q` (:4994-4999) is whole-tree and is unaffected.

---

### M5 — seven source-grep rows are satisfiable today by a comment in the module they are checking
**Where:** `src/verify_math.py` — the seven rows named below.
**Confidence:** certain (measured against the target modules).

For each, I deleted every **code** occurrence of the needle from the target module in memory and
asked whether the row still passes. All seven do, because the target module carries the token in
a comment:

| verify_math line | target module | needle | code uses | comment uses | still green with all code uses deleted |
|---|---|---|---|---|---|
| 2319 | `allsweep.py` | `ALL_JOBS` | 1 | 1 (`allsweep.py:351`) | **yes** |
| 3528 | `feats.py` | `_CAP_BOUND` | 6 | 5 | **yes** |
| 4240 | `standards.py` | `MAX_PROVIDER_MODELS_AGE_H` | 4 | 1 (`standards.py:1699`) | **yes** |
| 4243 | `standards.py` | `UNMEASURED` | 6 | 4 (`:670`, `:937`, …) | **yes** |
| 4467 | `backfill.py` | `write_record_catalogue` | 1 | 1 (`backfill.py:250`) | **yes** |
| 4485 | `standards.py` | `not enough history yet` | 1 | 1 (`standards.py:1116`) | **yes** |
| 7062 | `catalogue_web.py` | `failed_cats` | 8 | 1 (`catalogue_web.py:143`) | **yes** |

:4243 is the weakest — `"UNMEASURED" in standards.py` would stay green if every UNMEASURED
verdict in the module were deleted, so long as one comment about them survived.

:2319 is the most consequential — its own note says "if this fails, a private copy of the job
list has grown back in allsweep", and it cannot fail while `allsweep.py:351`'s comment stands.

**The class, in full.** These seven are the ones that are *demonstrably* vacuous today. The
underlying class is much wider: **56 `check()` rows test a string literal against a whole raw
`.py` file read (comments and docstrings included)**, split

* **48 assert PRESENCE** of a code string (`"x" in src` want True, or `"x" not in src` want
  False) — these go **green off a comment**, silently, which is the dangerous direction;
* **8 assert ABSENCE** — these go **red off a comment**, which is loud but is exactly the
  false-failure the file has already been bitten by twice (:3443-3446, :3316-3317, :4098-4109).

The file *has* the correct idiom and uses it seven times — `_fm19code`, `_fm20code`, `_on20code`,
`_db20code`, `_pl20code`, `_code19aj`, `_rgcode21` are all built by stripping comment tails
before the test — but the other 56 rows read the raw text. Three further rows are the same class
over `inspect.getsource()` rather than a file read (`:2787`, `:2796`, `:4163`) and one over an
inline `open(...).read()` (`:2182`, navtree).

Full line list of the 56 is reproducible with the two scratch scripts named at the end of this
document; the ranked seven above are the ones where the fault is realised, not merely possible.

---

### M6 — six of run #35's twelve proposal files were never spliced and are not globbed by §20u: 59 proposed checks, invisible
**Where:** `src/verify_math.py:7164-7171` (the `checks_L*.py` glob)
**Confidence:** certain (measured).

`handoff/run35/` contains eighteen files. Their fates:

* `checks_batch1.py` … `checks_batch6.py` — **spliced** into this file (§20s, :5495-6914).
* `checks_L1.py` … `checks_L6.py` — **executed** by §20u's `checks_L*.py` glob.
* `checks_F1.py`, `checks_M1.py`, `checks_M2.py`, `checks_M3.py`, `checks_M4.py`,
  `checks_SO.py` — **neither**.

Those six hold **59 `def check_*` functions** covering **67 distinct order ids**:

```
checks_F1  13 check fns   checks_M1   6   checks_M2  16
checks_M3   9 check fns   checks_M4   7   checks_SO   8
```

Not one of the 67 order ids appears anywhere in `src/verify_math.py`. Searching all of `src/`,
only 11 of the 67 turn up — and every one of those 11 is in the *target* module (`roll.py`,
`identity.py`, `resonance.py`, `policy.py`, `pipeline.py`, `propagation.py`, `tempus.py`,
`suppressions.py`, `descending_ladder.py`, `corpus_db.py`), i.e. the **fix** landed and the
**check** did not. The other 56 order ids appear nowhere in `src/` at all.

The section header calls itself "THE RUN #35 LOCAL RUNG, RUN RATHER THAN TRUSTED" and its own
first check reasons that "a vanished file is coverage that silently left". Half the coverage left
silently before that check was written, and the glob is what makes it invisible.

(Each of the six is self-describing: "These are PROPOSALS for verify_math.py / drill.py to adopt
— this agent does not own those files and did not add them there." Whether they *should* be
adopted is a curatorial call; that they are silently unaccounted for is not.)

---

## MINOR

### m1 — §20r's "the refusals are not blanket" positive control passes on a blanket refusal
**Where:** `src/verify_math.py:5140-5143`. Confidence: certain (demonstrated).

```
_ax_valid = A.axis_score(1e9, "M3", "ruin")
check("and it still SCORES a well-formed quantity (the refusals are not blanket)",
      _ax_valid is None or (0.0 <= _ax_valid <= 10.0), True,
      note="a guard that refuses everything passes every refusal test ever written")
```

Evaluated directly: `None -> True`, `4.2 -> True`, `99.0 -> False`. An `axis_score` that returned
`None` for everything — the exact failure the note names — satisfies this row. It is the only
`or`-disjunct row in the file that is degenerate in this way (the other five OR rows at :5274,
:5350, :6641, :6644, :6647 were checked and are legitimate).

Impact is bounded: a blanket-refusing `axis_score` would still be caught by §2:141
(`A.axis_score(x,"M3","ruin") == 5.0`). So this is a positive control that is not one, not an
uncovered behaviour. Correct form: `isinstance(_ax_valid, float) and 0.0 <= _ax_valid <= 10.0`.

### m2 — the "UNMEASURED fabrication guard does not read as green" row fails on the state its own note calls healthy
**Where:** `src/verify_math.py:4646-4653`. Confidence: certain (demonstrated).

The predicate collects `r["holds"]` for every UNMEASURED row and requires `[]`:

```
measured + holds      got=[]        passes
UNMEASURED + red      got=[False]   FAILS      <- the note says this is fine
UNMEASURED + green    got=[True]    FAILS      <- correct
```

The note explicitly claims "The list is empty either because the guard is measured (the healthy
case) **or because UNMEASURED is red**." The second half is false. The row asserts the strictly
stronger "there is no UNMEASURED row at all", which §20k:4524 already asserts one way. If the
fabrication guard ever goes honestly UNMEASURED-and-red the battery reports two failures, one of
them mis-described. Correct form: filter on `... and r["holds"]`.

### m3 — two module-level import aliases are rebound to different modules
**Where:** `src/verify_math.py:1712` vs `:2426`; `:889` vs `:7121`. Confidence: certain.

```
1712  import cascade_bridge  as _CB     ->  used :1728-:1798
2426  import context_budget  as _CB     ->  used :2431-:2491
 889  import profile         as PR      ->  used  :894-:929
7121  import propagation     as PR      ->  used :7124-:7137
```

Both rebinds are at module level and neither breaks anything today, because every use of the
first binding precedes the rebind. This is precisely the hazard §19v documents and repairs at
:2448-2452 for `_row` and `_emitted` — "correct only by the accident that nothing calls either
helper after this point, so any check added below that reached for one would raise TypeError and
truncate the suite at that line — which in a battery reads as a crash, not as a failing check."
The `_CB` rebind is *in that same section*, at :2426, twenty-two lines above the paragraph
warning about it. (`R` at :6554/:6590 and `WS` at :6846 are function-local and are fine.)

### m4 — eleven of fifteen temp directories are never removed; 484 orphans measured
**Where:** `src/verify_math.py` :1248 :1353 :1394 :1911 :2046 :2087 :2919 :3108 :4269 :6317 :6322 :6847 :7082.
Confidence: certain (measured).

Fifteen `mkdtemp`/`mktemp` sites; four are cleaned (`:2848` rmtree, `:5871` rmtree, `:5831` and
`:6221` `TemporaryDirectory`). Counting only the two prefixed sites that can be attributed:

```
C:\Users\imarl\AppData\Local\Temp\panscript-ledger-*   336 orphaned directories
C:\Users\imarl\AppData\Local\Temp\panscript-lane-*     148 orphaned directories
```

§20a's own comment records that this suite "runs from the foreman's patch lane, from allsweep,
and from every maintenance pass" — several times an hour, for ever. 336 ledger directories is
336 battery runs of accumulation. The nine unprefixed `mkdtemp()` sites leak identically and
cannot be counted.

### m5 — four self line-number citations at :2349 and :4407 are stale
**Where:** `src/verify_math.py:2347-2354`, `:4405-4407`. Confidence: certain (checked).

Both comments offer "2201-2202, 2219-2220, 2911-2912 and 3878-3879" as examples of the wrapped
disarmed-check spelling. None of the four is that shape now:

```
2201-2202  a `note=` continuation string in §19o's chapter-routing check
2219-2220  a `# --- packing:` banner and `def _row(name, n, chars=100):`
2911-2912  a comment about the throwaway lane dir and `import tempfile as _tmp19ad`
3878-3879  two comment lines inside §20e's alias-resolution explanation
```

This is the drift the file's own :3802-3804 names ("the §-tags are NOT touched … they are the
stable identifier") applied to itself. Cite by symbol or tag, not by line.

### m6 — two cross-file line citations at :3745-3746 have drifted
**Where:** `src/verify_math.py:3742-3749`. Confidence: certain (checked).

The comment corrects an earlier stale citation and introduces two more:

* "`sweep.py:129` is `def sweep():`" — `sweep.py:129` is now a **blank line**.
* "the evidence-cache read … is `cachekey.load(F.CACHE, host, e["name"])` at `sweep.py:160`" —
  `sweep.py:160` is now `if not PERSON.search(e.get("category") or ""):`.

Checked and still accurate today: `drill.py:1461` (the `config.yaml` label lambda) and
`drill.py:1506` (the blast-probe write) cited at :4890-4892; `rigor.py:123` cited at :3812.
`cascade_bridge.py:18` cited at :1971 is approximately right (the schema-in-prompt paragraph).

### m7 — §20x's printed banner states something that is no longer true
**Where:** `src/verify_math.py:4662-4665` (printed every run) and `:4675-4679`. Confidence: certain.

The banner prints "prose_gate.py:34 cites this one as §19s" and the comment says the corresponding
edit "is staged in handoff/run36/crossmodule_batch03.md because prose_gate.py is not this shift's
to edit." `prose_gate.py:34` now reads:

```
PROVEN        Each layer has a check in verify_math §20x that goes red if the layer is removed
```

and `§19s` appears nowhere in `prose_gate.py`. The edit landed; the banner still describes it as
pending, and tells every reader of the console output something false about a file they can
check in one grep.

### m8 — the `>= 40` hardcoded standards floor that §20k names as a defect is still in place
**Where:** `src/verify_math.py:4487-4490`; diagnosis at `:4512-4515`; replacement at `:5685-5693`.
Confidence: certain.

§20k's comment says of this row: "compares the emitted count against a HARDCODED 40 rather than
against the declared set, so a standard that never emits just lowers a number nobody
reconciles." Order d9b895708c45's replacement (declared-vs-emitted, by name) was added at :5685
and describes itself as "replacing/supplementing" it — but the weak row was left in place, with
its four-standards-of-headroom problem intact. Redundant rather than harmful now that the
reconciliation exists, but it is a row this file's own prose calls broken.

### m9 — §20g's atomic-write helper check reads `inspect.getsource`, comments included
**Where:** `src/verify_math.py:4162-4165`. Confidence: certain.

`"os.getpid()" in _src20g and "get_ident()" in _src20g` over `getsource(silence.write_json)` —
a docstring or comment in that function mentioning either token satisfies it. Same class as M5,
different accessor. `:2787`, `:2796` (`getsource(standards.ollama_token_flow)`) and `:2182`
(inline `open(navtree.py).read()`) are the same shape.

### m10 — the calibration-margin row can silently not run, and is None-tolerant when it does
**Where:** `src/verify_math.py:5349-5353`. Confidence: certain.

```
_cal = A.calibration_report()
if isinstance(_cal, dict):
    check("the calibration margin is None unless a real passing band was bracketed",
          _cal.get("margin") is None or (...), True)
```

If `calibration_report()` ever returns a non-dict the row records nothing at all — it is one of
only seven `check()` calls in the file sitting inside an `if`, and the only one whose guard has
no companion row asserting the guard was taken. (The other six are correctly paired: :5277/:5282
are the two branches of one `if/else`; :6394 is paired with :6390; :7208/:7212/:7215 are the
run35 fold-back.) The predicate is additionally satisfied by `margin is None` — mitigated by the
pinned rows at :5454 and :5480-5485, so this is redundancy rather than a hole.

### m11 — `str(n) in doc` is a bare whole-docstring substring test
**Where:** `src/verify_math.py:6641`, `:6644`, `:6647`. Confidence: certain (measured).

Measured now: `earth=26 moon=15 mars=14`, and none of `"26"`, `"15"`, `"14"` appears in
`onomast.__doc__` — all three rows pass on the *spelled* form via `_b5_spelled` and the
hand-maintained `_NUM_WORDS_b5 = {14:…, 15:…, 26:…, 12:…}`. That works and the drift-detection
intent is sound. The weakness is the first disjunct: a bare `str(n) in doc` would be satisfied
by any incidental digit run in the docstring (a date, another count), and the number-word map is
hardcoded to the four values current when it was written, so the comment's claim that it
"re-measures live rather than hardcoding the expected numbers" is only half true.

---

## INFO

* **i1** — the printed ordinal sequence runs `1 … 18, 20 … 36`; **19 is missing**. This is known
  and deliberate — the comment at :3793-3804 explains that numbering the §19 run would repeat the
  collisions the run33 renumbering fixed, and says so explicitly. Recorded here so the next run
  does not re-derive it.
* **i2** — `src/verify_math.py:4952-4959` (§20p, the halt-marker agreement row) has `got` and
  `want` equal to the same string literal when no halt is standing, so it cannot fail on a
  healthy machine. Deliberate and documented in its own note; not counted as a fault.
* **i3** — three `all(...)` predicates iterate collections that would make them vacuously true if
  emptied: `:712` (`AN.ANCHORS`), `:1013` (`SF.SOURCE_TIERS`), `:5210` (`_iv["signatures"]`).
  Each is followed within a few lines by a row that would raise or fail on the same emptiness
  (`:715` `AN.ANCHORS["The Skate Guy"]`, `:1018`, `:5206`), so the risk is contained. Noted so a
  future edit that removes the companion knows what it is removing.
* **i4** — `check()`'s float path treats `bool` as `int` (deliberate, documented at :87-88).

---

## CHECKED AND HEALTHY — read, verified, nothing wrong

These were examined specifically and found sound. Recorded so the next run knows they were
actually read rather than skipped.

* **Literal-vs-literal rows: exactly three, exactly the three declared correct by design.** An
  AST scan for `check()` rows whose `got` **and** `want` are both built purely from literals
  (no Call/Name/Attribute/Subscript/Compare/comprehension anywhere) returns:
  * `:4331` `check("probe: a non-numeric got against a float want", None, 1.0)` — probes
    `check()`'s own TypeError handling; deliberately failing and scrubbed from the tally.
  * `:7212` and `:7215` — fold a foreign harness's reported failure into this battery.
  **No new tautological rows exist.**
* **`tol=` is never passed with a non-float `want`.** Scanned all 934 call sites: zero rows pass
  a tolerance that `check()` would silently ignore (`check()` only honours `tol` when
  `isinstance(want, float)`).
* **No second `check()` and no second `PASS, FAIL` anywhere.** Only `:40` and `:80`. The
  coordinator note at :6917-6928 claims batch6's standalone harness was stripped at merge; it
  was, and §20u's per-file namespace isolation at :7173-7217 is correctly written (missing file,
  unparseable file, `SystemExit`, and "defines nothing runnable" are each a FAILED row rather
  than a skip).
* **No section tag currently names two sections** — 62 distinct tags across all three header
  forms, verified by hand because §20y cannot do it (see M1).
* **§20i's disarm guard is correctly self-avoiding and is genuinely exercised.** All three
  needles are assembled at runtime (`:2346`, `:4354`) so neither the needle-assembly lines nor
  the fixture strings at `:4401-4404` self-match; the positive control (`:4405`) and the
  negative control (`:4408`) both exist and both discriminate.
* **§20p's `_own_nodes20p` narrowing is correct** and returns `[]` against the live `drill.py`;
  its docstring's account of the `drill_local_agent` false positive is accurate. It is §20q that
  did not get the fix (M4).
* **§19v's `_row`/`_emitted` → `_row19v`/`_emitted19v` rename is complete and correct** for those
  two names. (`_CB` in the same section is not — m3.)
* **§19h's `_here19h`** is defined at :1719 and used at :1730, :1741, :1765, :1769; the historical
  "defined ~1600 lines later" comment is correctly retired and the `_here19h`/`_here19` distinction
  is real.
* **§19d/§19m's completeness override chain is complete.** `HOSTS`, `RECORDS`,
  `category_size_probe`, `host_reachable` and `OUT` are all saved and restored (`:1401`, `:1419`,
  `:1480-1481`, `:1492`, `:1512`), and `:1513-1516` asserts `OUT` actually came back — the repair
  described at :1485-1491 is in place and holds.
* **The four "not silently matching nothing" canaries all exist**: `_guarded20e >= 20` (:3928),
  `len(_all_via) >= 1` (:4066), `_used20q >= 12` (:5006), `len(_tags20y) > 40` (:7246). §20s's
  batch1 block (:5540-5633) adds true positive controls for all four negative AST scans
  (`_ctx_literals`, `_failopen20p`, `_writes_the_config20p`, `_callers20t`), one of which
  (`_writes_the_config20p`) calls the real function rather than a copy.
* **`derivation.SCAN_MODULES`** (:7042-7046) is compared against a live `os.listdir` of `src/`,
  not a hand-typed list. Correct shape.
* **§18b's mocked-transport block** (:1155-1233) saves and restores six module attributes through
  a `finally`; the five routing paths (one-shot, split-retry, epoch refusal, no transport,
  split-first) are each driven through the real `MG.assay_entity`.
* **§20t's escalation-clear AST scan** resolves aliases, from-imports and `getattr` dispatch, and
  treats an unparseable module as a *caller* rather than a pass (:5069-5073) — correct fail-closed
  shape, and matched by §19ab (:2747-2752) and §20e (:3857-3876), which both list-and-assert
  unparsed modules.
* **Battery health**: 1054 passed, 1 FAILED, no crash, no truncation, no exception escaping any
  section. The one failure is M2.

---

## WHAT WAS NOT DONE

* No source file was edited (audit pass).
* `prose_enabled` and `step4_enabled` were not touched, read only.
* No supervisor, crawler or `mutate.py` was run. `src/verify_math.py` was run once.
* Coverage recorded: `sweep_plan.record('run37', ['verify_math.py'], batch=1)` — confirmed
  present in the returned map as `{'verify_math.py': {'run': 'run37', ...}}`.

## REPRODUCTION

Two scratch scripts were written to produce the M5 enumeration and the literal/tolerance scans.
They are throwaway analysis tools, not part of the tree, and live in this session's scratchpad
(`grepchecks.py`, `needles.py`, `shapes.py`, `disarm.py`). Each finding above states the
predicate and the measured result inline so nothing depends on them.

---

## ORDERS FILED (found_by: sweep37-batch01)

| id | handler | sev | code | finding |
|---|---|---|---|---|
| 9ef32bd37b95 | RUN | MAJOR | vm-20y-blind-to-print-headers | M1 |
| b18acbb35760 | RUN | MAJOR | vm-20n-red-for-the-whole-sweep | M2 |
| 67c692701386 | RUN | MAJOR | vm-495390283745-needle-self-matches | M3 |
| 6a8444cad673 | RUN | MAJOR | vm-20q-nested-def-conflation | M4 |
| 469b4db261ef | RUN | MAJOR | vm-source-greps-satisfiable-by-a-comment | M5 |
| 28c1f58f5e8a | OWNER | MAJOR | vm-run35-proposal-files-never-adopted | M6 |
| dbc2937118da | RUN | MINOR | vm-20r-blanket-refusal-control-vacuous | m1 |
| 8389720500a9 | RUN | MINOR | vm-unmeasured-fabrication-row-inverted | m2 |
| a05eb35ebe4f | LOCAL | MINOR | vm-module-level-alias-rebinds | m3 |
| af447d21d634 | LOCAL | MINOR | vm-temp-dirs-never-removed | m4 |
| a09a0e003c31 | LOCAL | MINOR | vm-stale-line-number-citations | m5, m6 |
| aaa4eb561cc0 | LOCAL | MINOR | vm-20x-banner-states-a-stale-fact | m7 |
| ba7b55d6465f | LOCAL | MINOR | vm-standards-emitted-floor-still-hardcoded | m8 |

Not filed as orders (recorded here only): m9 (getsource greps -- same class as the M5 order,
covered by it), m10 (calibration-margin if-guard, redundancy not a hole), m11 (bare digit
substring in the onomast doctrine rows), and all four INFO items.

Filing script: `handoff/sweep37/file_batch01_orders.py` (re-runnable; file_order refreshes
rather than duplicating).
