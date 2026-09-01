# Sweep40 batch08 audit

Modules read in full: `src/magnitude.py` (1763 lines), `src/corpus_db.py` (767 lines),
`src/secondopinion.py` (601 lines), `src/handbuilt.py` (514 lines), `src/prose_gate.py` (402
lines), `src/catalogue_aurora.py` (324 lines), `src/tells.py` (280 lines), `src/propagation.py`
(235 lines). All eight read start-to-finish, no sampling.

This is a mature, heavily self-auditing codebase -- the great majority of what looks alarming on
first read is a long comment documenting a defect that was already found and already fixed in a
prior sweep. Findings below are real, currently-live defects verified against the source and, where
practical, against a live run. `prose_gate.py` was checked for the mutation-run corruption warning
(re-read, `ast.parse` succeeded) and is clean.

---

## FINDING 1 -- MAJOR -- `--calibrate` exit code is weaker than the standard it claims to match

**File:** `src/magnitude.py`
**Lines:** 1518, 1523, 1736-1741 (work order `b68c9523874e`)

```python
1518:        band_hits += (got_band == band)
...
1521:        row.update({"status": "SCORED", "got_band": got_band, "got": round(got_val, 2),
1522:                    "got_ci": got_ci, "band_match": got_band == band,
1523:                    "consistent": got_band == band and abs(got_val - val) <= ci + got_ci})
...
1736:        # `calibrate()` returns band_hits, 0-len(BENCHMARKS), not a pass/fail flag -- `if
1737:        # calibrate()` was truthy on ANY nonzero count, so one benchmark out of six reproducing
1738:        # its band exited 0. `standards.py`'s own `charter_regression_verdict` (the check behind
1739:        # "the automation reproduces the charter") requires EVERY scored row consistent, zero
1740:        # `bad`; the exit code here must mean the same thing the standard it feeds does.
1741:        return 0 if calibrate() == len(BENCHMARKS) else 1
```

`calibrate()` returns `band_hits`, which only counts rows where the integer band matched
(`got_band == band`, line 1518/1498). It never looks at `consistent`, which is the stricter
field (band match **and** the two confidence intervals overlapping,
`abs(got_val - val) <= ci + got_ci`, line 1523). `consistent` is a strict subset of
`band_match` by construction.

`src/standards.py:519-552`, `charter_regression_verdict()`, reads the exact same persisted
`CHARTER_REGRESSION.json` and computes:

```python
541:    bad = [r for r in scored if not r.get("consistent")]
...
550:    holds = bool(scored) and not bad and age_h <= CHARTER_REGRESSION_MAX_AGE_H
```

i.e. it requires every scored row to be **consistent**, not merely band-matched.

Consequence: a calibration run where all six benchmarks land in the right integer band, but one
of them has a decimal/interval that falls outside the combined confidence interval (a real,
measurable disagreement with the charter), makes `calibrate() == len(BENCHMARKS)` true, so
`python src/magnitude.py --calibrate` exits **0** ("the automation reproduces the charter" --
success) on the same run for which `standards.py`, reading the file this exact invocation just
wrote, reports `holds=False`. The comment directly above the return statement asserts this
should not be able to happen ("the exit code here must mean the same thing the standard it feeds
does") -- it currently can.

**Remedy:** change the exit-code check in `main()` to test that every `status == "SCORED"` row in
`calibrate()`'s own `rows` is `consistent` (mirroring `standards.charter_regression_verdict`
exactly), rather than `band_hits == len(BENCHMARKS)`. Simplest fix: have `calibrate()` also return
(or let `main()` recompute from) a `consistent_count`, and gate on
`consistent_count == len(BENCHMARKS)`.

---

## FINDING 2 -- MINOR -- stale numeric claim: Zalama's interval is not "four times wider"

**File:** `src/handbuilt.py`
**Lines:** 162-168 (work order `9f9f19d77791`)

```python
162: # The one sheet here that REFUSES most of its own axes. Zalama never acts on-page: his entire
163: # record is 2,310 characters, and everything known about him is known through the thing he
164: # built. Charter Part Three's answer to that is a STATUS, not a guess -- an axis with no
165: # evidence takes `unestimable` and the interval widens to say so. Every other entity in this
166: # file scores eleven axes; this one scores five, and its published interval is four times
167: # wider as a direct result. That is the instrument being honest about a thin record rather
168: # than manufacturing a number to fill the row.
```

Ran `handbuilt.compute()` live (which is exactly what produces `data/HANDBUILT_ASSAYS.json`):

```
Zalama            interval 0.19
Getter Emperor    interval 0.15   (an ordinary 11-axis entry in the same file)
The Undertaker    interval 0.15
Molecule Man      interval 0.15
Rune King Thor    interval 0.15
The Black Winter  interval 0.15
Mister Mxyzptlk   interval 0.15
The Sentry        interval 0.15
The Internal Revenue Service  interval 0.15
```

Zalama's interval is 0.19 against 0.15 for every 11-axis entry in the same ROSTER -- a ratio of
about **1.27x**, not four times. The underlying per-axis-variance covariance term is 2.676 vs
1.644, about 1.63x. Neither number is close to 4x by any reading. This is a comment asserting a
specific, checkable multiplier that the module's own live computation does not support -- exactly
the kind of claim a reader would trust as evidence the scoring is behaving honestly.

**Remedy:** either drop the specific multiplier from the comment (the qualitative point --
fewer scored axes widens the interval -- is true and doesn't need a number), or recompute and
correct it to "about 1.3x".

---

## FINDING 3 -- MINOR -- stale `file.py:NNN` self-citation inside `corpus_db.age_seconds()`

**File:** `src/corpus_db.py`
**Lines:** 348-350 (work order `9edeb89d01fa`)

```python
346:    Say that first because five separate sweep audits have now re-derived it from scratch
347:    (sweep33 batch17, sweep34 batch04, sweep36 batch09, sweep37 batch09, sweep38 batch10 ->
348:    order a25e919309cb). `grep -rn 'age_seconds()'` over the repo finds this def, two prose
349:    mentions in comments at :96 and :722, and nothing else; every real reader takes the value
350:    off `freshness()`'s dict instead -- `_freshness_banner()` at :478 and :491, `main()` at :728
351:    and :733, and drill.py.
```

Ran the literal check the docstring describes:

```
$ grep -n "age_seconds" src/corpus_db.py
96:    `corpus_db.DB` at a temp database then left `query`, `age_seconds` and `freshness` all   <- no parens
321:    # rebuild printed full counts ... `age_seconds()` went                                   <- HAS parens
343:def age_seconds():                                                                            <- the def
348:    order a25e919309cb). `grep -rn 'age_seconds()'` over the repo finds this def, two prose   <- self-reference
742:        # ABSENT AND UNREADABLE ARE DIFFERENT DATABASES. `age_seconds()` answers None for three <- HAS parens
```

Line 96 is a bare word (`age_seconds`, no parentheses) inside a backtick-quoted list --
it would not match the literal grep pattern `'age_seconds()'` the docstring itself specifies.
Line 722 is `return 0`, with no mention of `age_seconds` at all -- confirmed by direct read. The
two actual comment matches carrying `age_seconds()` are at lines **321** and **742**, not 96 and
722.

This is functionally harmless (the module still behaves correctly; `freshness()` is still the
one real reader, as the surrounding claim says) but it is the exact stale-line-number defect
class this project's own doctrine warns about elsewhere in this same batch
(`catalogue_aurora.py:151-157`: *"A line number is a citation with a decay rate"*), landing inside
the one docstring whose entire point is arguing against exactly this kind of drift.

**Remedy:** fix the two numbers to 321 and 742 (they will drift again), or drop them in favour of
the content-label convention the project already uses elsewhere for this reason.

---

## Reviewed and NOT filed (deliberate design / already self-documented / no defect found)

- `src/propagation.py` -- `observed_mark()`'s trailing `return 0` after the `range(17, 0, -1)`
  loop is provably unreachable (the loop always terminates via `ascension_years(1) == 0.0`,
  and `lag >= 0` is guaranteed by the guard above it) -- the module's own docstring already says
  so explicitly and correctly. Not a finding.
- `src/tells.py` -- `prompt_in_sync()`'s docstring narrates a historical defect (the generated
  banned-phrase block was never actually wired into `prompts/system_style.txt`). Verified this is
  now wired: `src/standards.py:959` calls `_TL.prompt_in_sync()`. Already fixed, narrated as
  history, not a live defect.
- `src/catalogue_aurora.py` -- extensively self-documents three already-fixed defects (silent
  cap on `slug()`, silent dedup collisions in `parse_folder`, discarded write verdicts in
  `main()`). Verified `main()` correctly propagates refusals to `sys.exit(main())` today. No
  live defect found.
- `src/secondopinion.py` -- ran live (`python src/secondopinion.py`): completed cleanly, ruff
  1114 findings / 231 waived under `NOT_FILED`, vulture 2, detect-secrets 0, house detectors
  agree on secrets. `NOT_FILED` waiver reasons were spot-checked against `RUFF_RULES` and hold.
  No live defect found; the module's own historical narrative about a since-reverted BLE001/
  S110/S112 waiver is exactly that -- history, and the waiver is confirmed reverted (BLE001 and
  SIM115 both appear as live findings in the current run, not in `NOT_FILED`).
- `src/prose_gate.py` -- re-read after the file changed on disk mid-batch (per the known
  mutation-run warning); `ast.parse` confirmed the version reviewed here parses cleanly. Five
  layers (gate config, tool assertion, evidence floor, block validator, assay-honesty check)
  read consistently with the module's stated INDEPENDENT/FAIL CLOSED/PROVEN design. No
  `prose_enabled`/`step4_enabled` changes suggested, per instructions.
- `src/magnitude.py` -- the bulk of the file is five stacked, well-documented guards (verbatim
  citation, axis relevance, subject/doer check, saturation, quantity arithmetic) each carrying a
  detailed "this used to fail this way" comment. Traced guard 3 (`subject_refusal`), guard 1
  (`_resolve_citation`), the split-path gate (`_split_gate`), and the quantity-guard wiring
  (`quantity_scores`) end to end against their call sites in `assay_entity` and confirmed each is
  actually invoked on the path its docstring claims (no "safety in a file, not in effect" gaps
  found beyond the one filed above).

## Coverage recorded

`sweep_plan.record('run40', [...8 modules...], batch=8)` -- see tool output below.
