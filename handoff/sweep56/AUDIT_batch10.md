# Sweep run56, batch 10 — audit

Modules read in full, top to bottom: `src/publish.py`, `src/sweep_plan.py`, `src/scout.py`,
`src/weave_index.py`, `src/address.py`, `src/burgs.py`, `src/navtree.py`,
`src/cosmology_graph.py`, `src/compress_store.py`.

Audit only. No files were edited. `publish.py` was not run. Nothing in this batch instructs
Claude to do anything (checked — no embedded directives found in any of the nine files; where
a file's own text looked instructional, e.g. scout.py's SYSTEM prompt to a model, it is quoted
below as data, not acted on).

---

## DEFECT 1 — `sweep_plan.freeze_plan` has no compare-and-swap on the create path (confirmed)

**Module:** `src/sweep_plan.py`
**Lines:** 205 (`frozen_plan`'s absence check), 284–299 (`freeze_plan`'s create-if-absent path)

```python
205    if not os.path.exists(p):
206        return None, "absent"
```
```python
284    existing, reason = frozen_plan(run)
285    if existing is not None:
286        return existing
287    if reason != "absent":
...
292    table = modules()
293    rec = {"run": str(run), "at": time.time(), "n": max(1, int(n)),
294           "src_table_digest": _table_digest(table),
295           "modules": table, "batches": batches(n, snapshot=table), "frozen": True}
296    try:
297        import silence
298        os.makedirs(PLANS, exist_ok=True)
299        if not silence.write_json(plan_path(run), rec, indent=1):
```

`freeze_plan`'s own docstring states the property it must have: *"IDEMPOTENT: an existing frozen
plan is RETURNED, never recomputed and never overwritten. Re-running the dispatch command cannot
silently re-shuffle a run that is already underway."* That property is enforced against a second
call **after** a plan file already exists (the `reason != "absent"` branch correctly refuses to
recompute). It is not enforced at the moment the *first* plan for a run is created.

The create path is check-then-act with no atomicity between the two: `frozen_plan(run)` checks
`os.path.exists(p)` (line 205) and returns `"absent"`; the caller then computes `table = modules()`
(line 292, a fresh read of live line counts) and lands it with `silence.write_json` (line 299).
`silence.write_json` → `silence.replace_retry` is a plain atomic rename — it guarantees the file
is never torn, but it does not compare against what the writer read (unlike
`silence.replace_if_unchanged`, which `scout.py`'s own `_mutate` uses for exactly this shape —
see `scout.py:_mutate`'s docstring on "the compare and the swap must be adjacent").

So two callers racing to freeze the *same, not-yet-frozen* `run` both observe `"absent"`, both
compute `modules()` independently, and both write. `modules()` is explicitly a function of the
**live** line counts of `src/`, and the module's own docstrings (`batches()`, `freeze_plan()`)
document at length that this is exactly the window when `src/` is being edited concurrently by
sixteen agents plus foreman's unattended patch lane — "the NORMAL condition of the tree during a
sweep." Whichever write lands last wins silently; the loser's in-memory `rec` (returned to its
own caller with `"frozen": True`, since `write_json` reports its own bytes as landed regardless
of who wrote after it) no longer matches what is on disk. A coordinator that dispatched agent
briefs from the loser's `rec` is now dispatching from a plan that does not match
`plan_path(run)` — `check_briefs(assigned, run=run)` would read the *other* caller's plan back
and report spurious `dropped`/`added` entries against briefs that were, from each agent's own
point of view, followed exactly. This is the identical failure class `freeze_plan` itself was
written to close (orders 4d44a6363245 / 4d44a6363245's sibling), just moved from "no frozen plan
existed" to "two writers raced to create the first one."

**Why it matters:** this is a real, if narrow, TOCTOU race — it only fires when two processes
call `freeze_plan` for the same `run` before either has written the file (i.e., near the start
of a sweep's dispatch), but that is precisely when a coordinator script and a re-run of the same
dispatch command are most likely to overlap.

**Confidence: DEFECT.** This directly confirms the audit brief's flagged concern
("`sweep_plan.freeze_plan` is known to lack a compare-and-swap"). The fix shape is the one this
module already uses elsewhere (`scout.py:_mutate`, `silence.replace_if_unchanged`): take the
digest of `p` (None for absent) before computing `table`, and land through
`silence.replace_if_unchanged` rather than `silence.write_json`, refusing (not overwriting) if
the file appeared under the writer between the check and the swap.

---

## DEFECT 2 — a cluster of stale line-number citations in comments (confirmed, several instances)

Hard Rule 0 audits keep finding this shape in this project (the docstrings of `compress_store.py`
and `weave_index.py` both narrate earlier instances being caught and fixed). This batch has
several more that have not yet been caught. All were verified by grep against the cited file's
*current* line numbers.

### 2a. `src/cosmology_graph.py:131-132` cites `weave.py:519` / `pipeline.py:2401` — both wrong

```
131    # WHOLE list, no cap -- Hard Rule 0, ruled 2026-08-24. `weave.py:519` and
132    # `pipeline.py:2401` write this same `shared_sample` key and were both brought in
```

The actual `shared_sample` write sites are `src/weave.py:671` and `src/pipeline.py:3179`
(verified: `grep -n "shared_sample" src/weave.py src/pipeline.py`). Drift of 152 and 778 lines
respectively. `resonance.py:295`, cited two lines later in the same comment, is still accurate
(verified — it reads `shared_sample` back at that line).

**Confidence: DEFECT** (verifiable, wrong file:line pointing a future reader at unrelated code —
in `pipeline.py`'s case, at a markdown-table-row line with no relation to the claim).

### 2b. `src/sweep_plan.py:591` cites `silence.py:515-517` — wrong

```
591    # (silence.py:515-517, `except Exception: _discard_tmp(tmp); raise`), so the very
```

The `except Exception: _discard_tmp(tmp); raise` block in `silence.write_json` is actually at
`src/silence.py:833-835`. Drift of ~318 lines.

**Confidence: DEFECT.**

### 2c. `src/sweep_plan.py:789` cites `verify_math.py:5007-5028` — wrong

```
789  # verify_math.py:5007-5028, `_at20n`/`_batches20n`/`_run20n`. grep -rn 'latest_run(' src/*.py
```

The `_at20n`/`_batches20n`/`_run20n` machinery is actually at `src/verify_math.py:6808-6830`
(verified by grep). Drift of ~1,800 lines.

**Confidence: DEFECT.**

### 2d. `src/weave_index.py:656` cites `health.py:576-585` — wrong

```
656    # health.py:576-585, applied here (order 4cea367c9235). Eighteen of 8,000-odd candidates
```

The actual "RANKING plus a stated floor" ruling text in `health.py` is at line 866 (verified:
`grep -n "RANKING plus a stated floor" src/health.py`), not 576-585 (which is unrelated
ledger/control-char code in that file). Drift of ~285 lines.

**Confidence: DEFECT.**

### 2e. `src/address.py:318` cites `manifest_builder.py:247` — off by 8 lines

```
318    -- `chapter_slug()`'s fallback for a label not in CHAPTER_SLUGS, and manifest_builder.py:247
```

The actual `cat = slugify(roll_entry.get("category", "Uncategorized"))` call is at
`src/manifest_builder.py:255`, not 247.

**Confidence: DEFECT**, though low-impact (an 8-line drift, still findable by anyone reading
nearby code).

### 2f. `src/address.py:310` cites `catalogue_web.py:68-95` — off by ~19 lines

```
310    THE [:60] IS GONE (order 5d317e3e47f0). This function used to end `[:60]`, the same cap on
       the same kind of value that `catalogue_web.py:68-95` spends thirty lines documenting...
```

The actual slug-`[:60]` documentation block in `catalogue_web.py` runs lines 87-120 (verified),
not 68-95. The line COUNT cited ("thirty lines") is still roughly right (34 actual); only the
starting/ending line numbers have drifted.

**Confidence: DEFECT**, low-impact for the same reason as 2e.

### 2g. `src/publish.py:1388` cites `publish.py:1214-ish` for its own `git("add", "-A")` — wrong, but self-flagged as approximate

```
1388   # after `git add "-A"` (publish.py:1214-ish) has already staged and pushed the broken page to
```

The actual call is `git("add", "-A")` at `src/publish.py:1625` (drift of ~411 lines). This one
is explicitly hedged with "-ish" by its own author, so I am **not** filing it as a confident
DEFECT — it reads as an acknowledged approximation rather than an assertion of precision. Noted
as a **QUESTION**: is "-ish" this project's accepted convention for "approximate, don't rely on
this for navigation", or should it be tightened up like the others above?

### 2h. `src/publish.py:1330` cites `build_terminal.py:83` — off by 4 lines

```
1330   the only mention anywhere in src/ was a comment in build_terminal.py:83
```

The actual comment mentioning `render.py`'s `containment_svg()` is at
`src/build_terminal.py:87`. Small drift (4 lines); mentioned for completeness, **not** filed as
a defect on its own given how minor it is, but grouped here since it's the same shape as 2a-2f.

**Note on `compress_store.py:64` and `:82`:** these also name `generate.py:554` and
`generate.py:468`, but on inspection both are *historical* citations — the surrounding text is
explicitly about a **previous** drift that was already caught and is being narrated as the
reason the citation was changed to name the call by description rather than by number
("named rather than numbered ... the joke writing itself"). These are not live navigational
claims and are correctly labelled as history. **Nothing further to fix here** — flagging only so
the next sweep doesn't re-discover and re-file the same historical note as new.

---

## Everything else read and found clean

- **`compress_store.py`** — nothing found. `store()`/`load()` are a well-formed
  content-addressed pair: `store()` writes through a pid+thread-stamped temp name and
  `silence.replace_retry`, cleans up the temp on a denied replace, and raises (rather than
  returning a false success dict) when the rename never lands. `load()` re-hashes the
  decompressed text against the address the filename claims and refuses to return content that
  doesn't match. No caps, no bare excepts, no tautological checks.

- **`cosmology_graph.py`** — nothing found beyond the citation drift above. `build_graph()`
  writes the whole `shared_sample` list uncapped (Hard Rule 0 compliant, and the comment at
  line 131-138 explicitly documents why an earlier `< 8` cap was wrong). `main()`'s `--write`
  path gates on `silence.write_json`'s landed verdict and does not print "wrote X" over a
  denied replace. The weighting formula (`1/log(n+1.5)`, `x0.15` ubiquity penalty) matches its
  own docstring exactly (checked the arithmetic by hand at n=2, n=3).

- **`navtree.py`** — nothing found. `audit()` is genuinely load-bearing (it is checked in
  `main()` before `--write` is honoured, and the exit code reflects both a non-clean audit and
  a denied audit-record write — the module's own long comment about "the exit code is the
  number a scheduler actually looks at" is an accurate description of the code as it stands).
  The register/hyperverse-naming tie-break fix (`max(set(...), key=lambda r: (regs.count(r), r))`)
  is correctly deterministic (verified: ties break on secondary key `r`, not hash order).

- **`burgs.py`** — nothing found. The rank-size derivation (`burg_count`, `rank_population`,
  `_rank_at_or_above`, `class_histogram`) is internally consistent — `_rank_at_or_above`'s
  closed-form-then-correct-against-`rank_population` approach was spot-checked by hand at a
  floor boundary and agrees. `burgs_for`'s `--limit` handling correctly treats `limit=0` as "zero
  rows" (not falsy-fallthrough to "no limit") and cannot exceed `n` (`min(int(limit), n)`).
  `main()`'s per-world loop keys `per_world` by a list (not overwriting on duplicate
  designations) as its own comment claims.

- **`address.py`** — nothing found beyond the two citation drifts above. `spine_code_for`'s
  layered matching (exact → normalized-equality → word-boundary-contained-with-title-check →
  token-overlap fallback) was traced by hand against the docstring's own worked examples
  ("Sword Coast Adventurer's Guide DC Edition Reprint", "A Halo Around The Moon Documentary",
  "Alien Predator Doom Crossover") and each falls through to the branch the comments say it
  should. `promote()`/`tier_rank()` correctly treat an unrecognized `current` tier as
  unranked (`None`) rather than as rank 0, so a corrupt tier value is repaired upward rather
  than silently pinned at the floor forever, matching the docstring.

- **`weave_index.py`** — nothing found beyond the citation drift above. The `_records_sig`
  staleness memo, `designations()` cache invalidation, and `staleness()`'s `behind`/`stale`
  split were each traced against their own docstrings' worked truth tables (the A/B logic table
  in `staleness()`'s comment was checked row by row and matches the code:
  `stale = age_hours > STALE_HOURS`, `behind = newest > idx_mtime`, both reported, only `stale`
  raises the work order). `record()`'s per-batch-shard-then-lock-guarded-aggregate-fold design
  correctly treats the shards as authoritative and the aggregate as a non-load-bearing
  convenience view.

- **`scout.py`** — nothing found. `_mutate`'s compare-and-swap (digest-before-read,
  `replace_if_unchanged` at write) is exactly the primitive `sweep_plan.freeze_plan` (Defect 1
  above) is missing. `verify()`'s `needed = max(1, min(MIN_NAME_HITS, probeable))` correctly
  avoids the "check that cannot pass" shape for sources with exactly one probeable name, and
  separately reports `unverifiable` when `probeable == 0` rather than silently failing every
  such source forever. `sweep()`'s stamp-before-work / unstamp-on-never-reached logic was traced
  through both the `seen_ok` and `not seen_ok` branches and does not delete a real prior
  timestamp in either case.

- **`publish.py`** — nothing found beyond the citation drifts above (2g/2h). This is the module
  the brief specifically warns about ("this module once published deliberately-corrupted source
  twice"), so it got the closest reading. `push()`'s gate order was traced explicitly:
  `ledger_guard.assert_intact()` → mutation-interlock check (both the push-time reading AND the
  caller's earlier before-copy reading, either one being unsafe refuses) → secret scan of the
  actually-staged export tree → `git add -A` → commit → fetch/rebase (aborted, never forced, on
  conflict) → push → **post-push confirmation** via `_unpushed()` (a `git push` that reports
  rc=0 but whose commit still isn't on `origin/main` is treated as `PushHeld`, not success).
  Every one of these guards fails closed on an unimportable dependency
  (`ledger_guard`, `mutate`, `escalation` all raise/exit rather than silently proceeding) and
  the three-outcome design (`True` / `False` / raised `PushHeld`) means a caller cannot mistake
  a held push for a no-op. `main()`'s halt check (`escalation.assert_clear`) is re-asked at the
  top of every loop iteration, not just at daemon startup, and `SystemHalted` breaks the loop
  rather than being caught by the generic retry handler. I did not find a path that publishes
  while a halt stands, while `mutate.py` reports a non-sandboxed run active, or without the
  ledger/secret checks. `maintenance_shift_live()` fails **open** by explicit, argued design
  (contrasted in its own docstring against the fail-closed rule used elsewhere) — this reads as
  a deliberate, reasoned asymmetry rather than an oversight, so it is a **QUESTION**, not a
  defect: is failing open on an unreadable maintenance-guard file (only the fourth, most recently
  added interlock; loop-mode only) still the right call given how many other interlocks in this
  same file were hardened from fail-open to fail-closed after real incidents? I am not
  recommending a change — the reasoning given (a wedged publisher forever vs. one cycle of
  possibly-half-finished source that the next cycle overwrites) is coherent — just flagging it
  as the one asymmetric design choice in an otherwise consistently fail-closed file, in case the
  next sweep should weigh it against a fifth incident.

- No bare `except: pass`, no silent-except-with-no-note, and no tautological/undefined-name
  checks were found in any of the nine files (checked mechanically via an AST walk over every
  `except` handler in all nine files, then hand-verified each hit; every "except → pass" found
  is either explicit best-effort cleanup of a scratch/temp file whose failure costs nothing, or
  the "try to call `silence.note`, and if `silence` itself can't be reached, swallow that
  meta-failure" idiom used consistently project-wide).

- No undisclosed truncation/sampling/caps were found. Every `[:N]` slice in these nine files is
  either (a) a hash/digest computation, not data truncation, (b) a console-display cut that
  carries an explicit "(+N more)"/"... and N more" marker, or (c) bounded exception-message
  text for a console line (not a stored roster). All are consistent with Hard Rule 0 as the
  files' own extensive comments describe it.

---

## Summary of confirmed defects

1. `sweep_plan.py:205,284-299` — `freeze_plan` lacks compare-and-swap on the create-if-absent
   path; two concurrent first-callers for the same `run` can race and silently disagree about
   which batch plan is frozen.
2. `cosmology_graph.py:131-132` — stale citations to `weave.py:519` (actual: 671) and
   `pipeline.py:2401` (actual: 3179).
3. `sweep_plan.py:591` — stale citation to `silence.py:515-517` (actual: 833-835).
4. `sweep_plan.py:789` — stale citation to `verify_math.py:5007-5028` (actual: 6808-6830).
5. `weave_index.py:656` — stale citation to `health.py:576-585` (actual: 866).
6. `address.py:318` — stale citation to `manifest_builder.py:247` (actual: 255).
7. `address.py:310` — stale citation to `catalogue_web.py:68-95` (actual: 87-120).

## Questions (not defects)

- `publish.py:1388` — self-citation "publish.py:1214-ish" for `git("add", "-A")` (actual: 1625)
  is hedged with "-ish"; is that hedge this project's accepted way of marking an approximate
  citation, or should it be corrected like the others above?
- `publish.py:1735-1793` (`maintenance_shift_live`) — deliberately fails open on an unreadable
  guard file, the one asymmetric interlock in an otherwise fail-closed module. Reasoning is
  explicit and coherent in the docstring; flagged only for the next sweep's awareness, not as a
  recommended change.
