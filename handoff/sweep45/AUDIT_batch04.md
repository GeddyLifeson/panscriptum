# sweep45 — batch 04

**Modules:** `mutate.py` (2,649), `derivation.py` (743), `manifest_builder.py` (598),
`worldseed.py` (473), `render.py` (358), `style_audit.py` (314), `halo.py` (219),
`lognames.py` (52). **5,406 lines, all read, no sampling.** (The brief said 5,384; `wc -l`
says 5,406. Nothing was skipped in either count.)

Read-only pass. No source file was edited. The DRILL_BREACH halt was left standing and no
battery tool was run.

---

## Read this before the mutation pass — mutate.py restore path and sandbox boundary

Three of the four mutate findings sit on the paths the brief named. Ordered by what they cost.

### 1. `f4af474dfc49` — the session crashes on an unusable baseline refresh (MAJOR, SESSION)

`_refresh_baseline` appends **two different record shapes** to one list:

* `mutate.py:1953-1956` — `{at, refresh_unusable, kept_previous_baseline, verdicts_since_last_good_baseline}`
* `mutate.py:1974-1977` — `{at, gates_that_moved, verdicts_now_in_doubt}`

Both leave through `result["baseline_drifts"]` (`mutate.py:2135`). `_session` reads only the
second shape — `mutate.py:2543` does `sorted(d["gates_that_moved"])` — with no discrimination.
The first shape carries neither key, so it is an unguarded `KeyError: 'gates_that_moved'` that
aborts the whole session.

It fires when any gate TIMES OUT or ERRORS during a mid-run re-photograph. `drill` runs against
a 1200 s limit at roughly 300 s of pristine wall clock, `--rebaseline-every` defaults to 1800 s,
and `--target all` holds that window open for about sixteen hours on a machine that also runs
the crawl, the model and the publisher. A run of minutes never re-photographs at all, which is
why it has not been seen.

The already-journaled survivors and filed orders for the target in flight survive; the remaining
targets are never attempted, and a traceback is the whole report.

### 2. `4f5fa3146cc4` — `live_file_untouched` halts the library on somebody else's edit (MAJOR, SESSION)

`live_before` (`:1866`) and `live_after` (`:2108`) digest `src/<target>.py` in the **live** tree.
Nothing between them opens that path for writing — every write goes to the sandbox copy. So the
comparison is not a check on this process; it is a check on every other process on the machine.

* **False positive, and it matters tonight.** A difference escalates at `escalation.OWNER`
  (`:2562-2570`), and rung 5 writes `state/HALT.json`. The three targets are `assay.py`,
  `prose_gate.py` and `escalation.py` — the files maintenance shifts edit most — and the window
  is sixteen hours. One repair agent landing one line halts everything, over a file the run never
  touched. The module already treats a concurrent editor as an *expected* condition in
  `tree_is_moving()`, where `_session` merely warns.
* **False negative, same two lines.** A before/after digest is blind to the window between them.
  The incident it commemorates — a `publish.py --loop` daemon pushing a corrupted `prose_gate.py`
  — was a *window* failure: corrupt for seconds, restored after, digests equal, check green.

The mechanical half of the remedy is to report a difference as *the sandbox snapshot has been
invalidated, stop this run*; whether `MUTATE_TOUCHED_LIVE_TREE` keeps the OWNER rung at all now
that the named failure is impossible by construction is the part filed for a person.

### 3. `19791681f257` — the red-gate caveat is rewritten retroactively on every survivor (MAJOR, SESSION)

`red_at_baseline` is built once (`:1861`). Each survivor stores **the same list object**
(`:2101`), and `:1992` does `red_at_baseline[:] = [...]` — an in-place slice assignment. So the
"these detectors were down" caveat on a survivor scored at hour two is silently replaced by the
reading taken at hour fifteen, and `file_orders` (`:2197`, `:2207`) pastes that into the
permanent work order.

The in-place form was chosen deliberately to stop a *stale* launch-time claim riding on a later
verdict. It closes that direction and opens the opposite one. `state/MUTANTS_SURVIVED.jsonl` is
unaffected — `_journal` serialises immediately — so where the JSONL and the work order disagree,
the JSONL is right and the order is wrong, which is the worse way round.

### 4. `a1aa2be36b7e` — `run()` never verifies its `root` is a sandbox (MINOR, SESSION, low confidence)

Filed as defence in depth, explicitly labelled low confidence. Nothing compares `root` against
`HERE` (`:1862-1864`). With `root=HERE`, `path` **is** the live file and `_write` (`:2003`)
corrupts real source once per mutant for hours — and all three guards report success:
`verify_restore` proves a round-trip on whichever file it is given; `live_file_untouched` is
equal because the `finally` at `:2102-2103` restores the bytes; `own_sandbox` is False so the
`rmtree` at `:2141-2142` correctly does not fire, which is the only thing between this and
deleting the repository.

**No live caller reaches it, verified.** `_session` passes `root=sandbox()` (`:2356`); the only
other `run()` callers are `drill.py:10572` and `:10580`, both of which stub `_run_mutation`
first. But `run()`'s own docstring advertises itself as the door for "the drill, a work-order
reproduction, a future scheduler", and "the live tree is never opened for writing" is currently
a property of the callers rather than of the code.

### Read with suspicion and found sound

* `verify_restore` (`:804-828`) — the `finally` restores before the return, the return re-reads,
  and a permission/disk error is deliberately allowed to raise rather than degrade to `False`.
  If it returns False the sandbox file may be left holding the probe, but `_run_mutation` raises
  immediately and the sandbox is discarded; nothing outside the throwaway root is reachable.
* The `finally: _write(path, original)` at `:2102-2103` covers every exit of the mutant loop,
  including `hang_confirms_a_kill`'s own `_write(path, original)` (which is always followed by a
  `break`, so no mutant is left half-restored).
* Every writer in the module was traced. Outside the sandbox root only four paths are written —
  `state/MUTATION_ACTIVE.json`, `state/MUTANTS_SURVIVED.jsonl`, `state/reap_ledger.jsonl` and
  `state/MUTANTS_RULED_EQUIVALENT.json` — all intended, and `_write_rulings` goes through
  `tmp` + `os.replace`.
* `reap_orphans` deletes only under `tempfile.gettempdir()` behind the `SANDBOX_PREFIX` match,
  unlinks the four junctions by name first, and skips any sandbox with a live owner.

---

## Other findings filed

| id | where | severity |
|---|---|---|
| `dab60fe3c2b5` | `derivation.py:737`, `:739` | MINOR |
| `ca1ed2be8c51` | `derivation.py:543` (`SCAN_MODULES`) | MINOR |
| `07d101ba4b90` | `manifest_builder.py:255-256` | MINOR |
| `61a15f94928a` | `worldseed.py:416`, `:417`, `:422` | MINOR |

* **`dab60fe3c2b5` — a verdict that cannot fail.** `derivation.main()` returns 1 at `:695`
  whenever `problems` is non-empty (the early return added by order `90516d53d696` so the
  non-terminating chain walk is never reached). Execution reaching `:737` therefore guarantees
  `problems == []`, so `f"{len(problems)} FAILURES"` is a dead arm and `return 1 if problems
  else 0` at `:739` is a constant 0. Neither is wrong today; both read as though the closing
  banner still adjudicates, and the second is the module's exit code.
* **`ca1ed2be8c51` — the constant map cannot see `src/deprecated/`.** `SCAN_MODULES` is
  `os.listdir(HERE)`, top level only, so `src/deprecated/catalogue_local.py` is unscanned by the
  map whose whole argument is that no new constant can hide. Note for whoever fixes it:
  `scan_constants_with_reason` rebuilds the path as `os.path.join(HERE, mod + ".py")` at `:586`,
  so a bare basename from a subdirectory would resolve to nothing and be reported `(absent)` —
  the one label order `6baeeb468a24` established must never appear for a module that exists. The
  comment at `:535` also still says "113 .py files".
* **`07d101ba4b90` — an empty record drops a source with no line anywhere.**
  `build_jobs_for_source` returns `[]` at `:255-256` when `record["entries"]` is empty, with no
  print and no accumulator. `main()` reports three other ways a source can drop out and not this
  one; the near miss is `skipped_empty`, computed from the **roll**'s `entry_count` (`:434`), so
  roll-versus-record disagreement is exactly the condition that lands here and exactly the one
  the report cannot express.
* **`61a15f94928a` — three unmarked cuts in `worldseed.main()`.** `w['designation'][:60]` is a
  mid-name cut on the identity string the collision report tells a reader to go and rename;
  `to_fmg_query(...)[:150]` cuts the URL mid-parameter in the only place it is printed;
  `worlds[:6]` is announced as a SAMPLE but with no denominator, one line under the population.
  The same function already had four other caps removed for this rule.

---

## Corroborated, not refiled

Verified still true against source this pass:

* **mutate.py** — `512864b65163` (`"capped"` false-positive, now `:2128`), `4e65c6aacf23`
  (unreadable lock), `c72431056a14` (`_TOKEN_ENV` written, never read), `3460ab179aa9`
  (`len(missed) or 1` in the absent-target refusal), `fe0dd6e4844f` (stale `:222` citation in
  `_lock_release`'s docstring), `2d8b96343896` (the `drill.py:4256` call-site citation),
  `fbc0930ae309`, `58a00e909217`.
* **worldseed.py** — `0bbf8ff1e3aa` (`ono = {}` is dead: `reg_by_group` is now built inside the
  `try`, so nothing reads `ono` after the handler), `ad681057369a` / `40e98eed6870`
  (`"primitive": 35` unreachable), `e68664e621bf` (`URL_SETTABLE` read by nothing —
  `to_fmg_query` builds its own dict), `c0384991bfc5` (`unreachable_by_url` has no callers),
  `82adeee9b7ee` (`if limit and ...`, so `--limit 0` means unlimited).
* **manifest_builder.py** — `00ef174b7495` (bare `open(report_path, "w")` at `:576`, still a
  truncate-then-fill beside a `silence.write_json` in the same function), `bd3f737f4241`
  (`str(e)[:110]`), `db36d589713e` (`FEATS_BLOCK_CHARS` defined and unused), `c8dc624e4e02`.
* **render.py** — `707fefc17465` (no module in `src/` imports `render`; grep confirms),
  `c738ca184269` (bare `open(p, "w")` per SVG in `--write`, `:351`).
* **style_audit.py** — `202f8429168b` (the `--self-test` checks list asserts nothing about
  `turn_endings`, `turn_rate` or `em_per_entry`, though the GAMMA fixture is built to move them).
* **derivation.py** — `ae1494dbc976` (bool counted as a numeric literal), `c9e6e50e792f` (the
  `assay_dof` note says ten degrees of freedom and the entry names nine parents),
  `01695fe3ef26`.

## Appear already remedied — candidates to close, not refile

Two open orders no longer describe the code:

* **`3b422bc17939`** (render `children_of` accepts a partial coordinate) — `render.py:219-225`
  now raises on **every** missing prefix key, not merely the fully empty coordinate.
* **`a9160ee5a8bf`** (`render.py:256` cuts the URL at 64 characters) — the line is now
  `rows.append((t, "url", v["url"]))` at `render.py:320`, uncut, with the argument in a comment.

Not closed by this pass; flagged so the queue is not worked twice.

## Deliberate design, judged and not filed

* **`halo.py:36-38`, the `_BAD_CHARS` self-read.** It is a guard that essentially cannot fire,
  and its comment ("a regex escape was eaten in transit") names something `halo.py` does not do —
  the module imports no `re` and contains no pattern. But the same three lines appear in roughly
  eighty modules across `src/`; it is a house idiom, and removing it here alone would desync it.
  Worth an owner's ruling on the whole idiom, not a per-module order.
* **`style_audit.py:229`, `_cut(len(heavy), len(heavy), ...)`.** Always takes the "all shown"
  arm by construction, so the line can never report a remainder. It is honest — the population
  *is* `heavy`, and every member prints — and the comment at `:220-226` argues the case
  explicitly. Noted rather than filed; the only improvement would be also naming how many
  distinct words `a["vocab"]` held, which the OPENING SHAPES heading does for its population.
* **`render.py:157`, `str(ch.get("name", ""))[:26]`.** A display cut inside the SVG, reversible
  because `children_of` now returns the whole name — which is the distinction order
  `d1a008863b02` drew when it removed the irreversible `[:24]` one level up.
* **`worldseed.py` `LAST_BUILD`** is module-global state mutated by `build_all`, which has six
  callers. In-process only, reset at the top of each call, and never written to disk; not the
  two-writer hazard this sweep looks for.
* **`mutate.py:2139`, `restored_exactly`.** Near-tautological — it compares a file just written
  from `original` against `original` in the same process — but it is a genuine filesystem
  read-back and it is what `_session:2554` acts on. Left alone.
* **`style_audit.py:34`, `_WATCHED`.** Checked against `tells.py`: `ALL_PATTERNS` is
  `{**STRUCTURAL, **DISCOURSE}` and does not include `LEXICAL` or `LEXICAL_FICTION`, so the sum
  is not double-counting and matches `tells.main()`'s own total at `tells.py:274`.

## Noted, below the filing bar

`mutate.journal_rows` (`:888-920`) returns the rows it has accumulated after a mid-file read
error, `silence.note`-ing but not marking the list as partial — so `survivors_on_record()` and
`_session`'s "on record from earlier runs" line would report a smaller universe in the same
shape as a complete one. The failure needs an I/O error part-way through an append-only JSONL,
and the note does reach the ledger. Recorded here rather than added to a 384-deep queue.
