# sweep45 — batch 08 audit

**Modules (frozen plan, run=sweep45, batch 8, 5,377 lines):** `magnitude.py`, `sweep_plan.py`,
`gpu_lane.py`, `zfighters.py`, `axis_correlation.py`, `sweep.py`, `physics.py`, `tuning.py`.

**Coverage of the read.** All eight read end to end, no sampling. Two files moved under the
audit and were re-read to the live text: `sweep_plan.py` (908 → 917 lines during the session;
the delta is a `silence-exempt` comment added in `frozen_plan`'s `FileNotFoundError` branch by
sweep45-batch02 — regions 145–296, 296–535 and 890–917 re-read after the edit) and `sweep.py`
(346 in the frozen plan, 365 live; read whole at 365). `magnitude.py` 1912, `gpu_lane.py` 684,
`zfighters.py` 536, `axis_correlation.py` 415, `physics.py` 304, `tuning.py` 272 — all
unchanged since the freeze. Coverage recorded via `sweep_plan.record('sweep45', …, batch=8)`;
zero unknown claims.

Read-only pass. No source file in the tree was edited. `drill.py` / `verify_math.py` /
`allsweep.py` / `publish.py` / `mutate.py` were not run and the DRILL_BREACH halt was not
touched.

---

## Filed, worst first

### 9508f9322b4c — MAJOR / LOCAL — `freeze_plan` silently recomputes and overwrites a frozen plan
`src/sweep_plan.py:158-184` (`frozen_plan`), `:188-241` (`freeze_plan`)

`freeze_plan`'s docstring promises, in capitals, that an existing frozen plan is "RETURNED,
never recomputed and never overwritten" and that "Re-running the dispatch command cannot
silently re-shuffle a run that is already underway". It does exactly that whenever the plan
file exists but cannot be used.

`frozen_plan(run)` collapses three conditions into one bare `None`:

| condition | trace left |
|---|---|
| file absent (`FileNotFoundError`) | none, marked silence-exempt — correct |
| file present, will not parse / cannot be opened | `silence.note` + stderr: *"Recomputing would reshuffle the batches this run was dispatched from; fix or remove the file instead"* |
| file parses but is not a dict (`return rec if isinstance(rec, dict) else None`) | **nothing at all** |

`freeze_plan` tests only `if existing is not None`, so in the second and third cases it falls
through, repacks `batches(n)` against the **live** tree, and lands the new record over
`plan_path(run)`. The advice `frozen_plan` prints is contradicted four lines later in the same
call, and the original plan is destroyed. `main()` then prints
`# plan for run=%s is FROZEN at %s` over a run that has just been re-shuffled.

The not-a-dict case is reachable through this module's own CLI: `--batches N --out PATH` writes
a bare JSON **list**, and `PATH` pointed at `state/sweep_plan/<run>.json` leaves a file that
parses, is not a dict, and is replaced without a word on the next freeze.

Measured at 22:59 tonight: `state/sweep_plan/sweep45.json` (frozen 22:51, digest `1035bcd46de2`)
records `sweep_plan.py` at 908 lines and `sweep.py` at 346; live they are 917 and 365. A
recompute now returns a different packing from the one the sixteen batches were dispatched
from — the run39 failure that orders 44c420f80448 / b86d79c574e3 / 4d44a6363245 record and that
`freeze_plan` exists to end.

Second mouth of the same hole: `freeze_plan` returns `existing` without checking it carries a
`batches` key. A dict-shaped plan without one raises `KeyError` in `main()`, and makes
`check_briefs` build `plan = {}` — which reports every module in `src/` as `uncovered` and
`NOT CLEAN`, a verdict about the coordinator's briefs caused entirely by the plan file.

Remedy: only `FileNotFoundError` may license a fresh freeze. An existing path that will not
parse, is not a dict, or carries no `batches` must be refused — `frozen: False` with a reason
naming the file, nothing written over it, non-zero rc — and `frozen_plan` should return a
distinguishable value rather than one `None` for three causes.

### 9861001e9137 — MAJOR / LOCAL — `axis_correlation`'s source-shrink safeguard has no reader
`src/axis_correlation.py:161-194`, `:209-233`, `:236-262`, `:363-411`

`observations()` exists to make a shrinking matrix visible — "THE MISSING LIST IS THE POINT …
the matrix could silently shrink … while looking exactly as authoritative as before. Every entry
in SOURCES exists today; this is what would catch it the day one of them does not." Nothing
reads it, so it catches nothing.

`sources_missing` / `sources_read` are produced, carried through `measure()`, and persisted by
`write()`. A grep over all 116 modules including `src/deprecated/` finds **zero** consumers
outside the module. `main()` — the only caller of `write()` in the tree — prints `n_entities`,
the ranked pairs, `measured_pairs` and `mean_r`, and never either field. A rebuild that read one
of the eight `SOURCES` prints and lands identically to one that read all eight.

A degraded matrix is not the announced case. `_no_matrix()` covers only a wholly
missing/unreadable/`pairs`-less matrix; a matrix with even a handful of pairs loads cleanly,
`rho()` answers from it, `widening()` widens by it, and `assay._rho_source()` stamps every
affected assay `measured: data/AXIS_CORRELATION.json`. `MIN_N` is 4, so four rows mint pairs.
`observations()` also notes only the *unreadable* branch — an **absent** source leaves no ledger
row at all.

The path resolution makes the whole-tree version easy: `HERE =
dirname(dirname(abspath(__file__)))`, so `SOURCES` and `OUT` resolve against this file's
grandparent and a flat sandbox loses all eight sources at once. That particular end state is
loud (`load()` rejects a `pairs`-less doc, `_no_matrix` fires), but a **partial** read is not,
and it is the same door.

Only `drill.drill_correlation.measures_are_not_independent` (`mean_r > 0.1` and
`n_entities >= 20`) stands against it, and it runs at drill time — the identical gap
`assay._rho_doc` already records for the missing-matrix case: "a batch could publish a full run
of too-narrow bars between two green rounds."

Remedy: `write()` refuses (returns `None`, the shape it already uses for a denied landing) or
stamps a `degraded` key when `sources_missing` is non-empty; `main()` prints both lists,
uncapped; the absent branch gets a note. The fallback **value** is owner ruling c00cab9d0412 and
is deliberately untouched by this order.

### ca9b07305f99 — MINOR / LOCAL — `_scores_of` admits booleans into the covariance matrix
`src/axis_correlation.py:137-158`; upstream `src/assay.py:949-950`

Both filters are `isinstance(x, (int, float))`, and `bool` subclasses `int`, so a stored axis
score of JSON `true`/`false` enters the correlation matrix as 1.0 / 0.0 — a fabricated numeric
observation in the one table inside every published ±. This is the defect `magnitude._is_score`
was written for one module over, and that function's own docstring states the rule this site
breaks: "the correct behaviour is the same at all six sites and a rule that lives in one place
cannot drift between them."

Stated honestly: nothing produces a boolean score today — `verify()` and `_split_gate()` refuse
them, the hand-built sheets carry literal floats. The upstream that would carry one is
`assay.py:949-950`, whose `used` filter admits bools where `assay.py:486` and `:549` exclude
them, and `used` is persisted verbatim as `result["scores"]` — the exact automated shape
`_scores_of` reads. Front and back of one unguarded path.

---

## Already open — corroborated, not refiled

- **2b695c192470** `sweep.load` has no caller. Still true: the live path is `cachekey.load`
  inside `sweep()`; the only hits are its own docstring and comments.
- **d411f780d347** `coverage_map()` has no caller. Still true — grep returns the `def` at
  `sweep_plan.py:531` and one docstring mention at `:558`.
- **b24ab7ac275f** `physics.py:50` binds `HERE` and never uses it. Still true — the only other
  occurrence of the token is the word "HERE" in a docstring heading.
- **9eb6a45e5a46** `tuning.py:177` rebuilds the cascade scratch-DB path itself. Still true.
- **019d1aae1df4** `sweep_plan.modules()` says "newest-largest first"; the sort key is
  `-m["lines"]` only. Still true.
- **b57e23204f66** An owner ruling is owed on `rho()`'s no-matrix return value. Still open, and
  order 9861001e9137 above is deliberately about the *announcement*, not the value.
- **44c420f80448 / b86d79c574e3 / 4d44a6363245** `batches()` unstable under live edits — now
  addressed in principle by `freeze_plan`, and 9508f9322b4c is the hole left in that fix.

## Appears fixed in the tree (not closed in the queue)

- **18187cb13de7** — both permanent-record returns in `assay_entity` now carry `"host": host`.
- **e9ff72c7eb48** — guard 3 now reads the entity: `subject_refusal(entity, text, ax)` on the
  one-shot path and, since order e22f29b8e4df, on the split path and in `quantity_scores` too.
- **4da7238657a3** — `run_batch`'s tally is now four-way (scored / refused / deferred /
  unlanded), keyed on `settled()`.
- **4f66afc16fbd, 9e5c04e01d74** — `sweep.report()`'s DEEPEST EVIDENCE row now **pads**
  (`{r['name']:<30}{r['source']:<26}`) instead of cutting.

## Looked at and deliberately not filed

- **`physics.py`** — clean. Every entry point refuses non-positive, NaN, infinite *and*
  overflowing-result arguments, each with a named domain error rather than an arithmetic one.
  Nothing to report.
- **`zfighters.py`** — the Goku carry-in failure is announced on stdout, marked `_incomplete` in
  the written JSON, and skipped by every ranker; the write is gated on `write_json`. Correct.
- **`gpu_lane.py`** — fails open at every path as its header mandates; `_take_slot`'s three-way
  answer, `_unreadable_and_stale`'s mtime fallback and `_touch`'s never-resurrect rule are all
  reachable and correct. One observation, not a defect: after the 900 s slot deadline `lane()`
  proceeds **unmetered** with no note, unlike the unarbitrable path which is documented. Left as
  design.
- **`tuning.py`** — `cloud_success_rate()` returning `(None, 0)` means "no evidence" and cannot
  veto; that is stated and deliberate. `_answering_buckets()` fails to `0`, which is the
  fail-safe direction.
- **`magnitude.py`** — the five guards are all reachable on both transports and both paths;
  `saturated()` is safe because `A.NONE` / `UNESTIMABLE` / `INAPPLICABLE` are *strings*, so
  `_is_score` excludes them; the cross-axis `[N]` check is skipped on the split path
  deliberately and says why. One near-unreachable silent drop noted and not filed:
  `quantity_scores` drops a reading with no `rejections` entry when `A.axis_score` returns
  `None`, which today needs a measured value of 0 (every band in `BAND_EDGES` carries both
  `ruin` and `reach`).
- **`sweep_plan.record()`** — I could not construct a name it counts that it should reject.
  `normalise_module` strips `src/` once, adds `.py` once, and resolves a bare basename only on a
  unique hit; everything else returns `None` and lands in `unknown`, where nothing counts it.
  The one softness is that a path escaping the tree (`../src/magnitude.py`) resolves by
  basename — but it still names a real module, so it is not invented coverage.
- **`sweep.py`** — `nested_run()` tests nesting against the rows in hand rather than asserting
  it, and both long lists print uncapped with their own counts. Correct.
