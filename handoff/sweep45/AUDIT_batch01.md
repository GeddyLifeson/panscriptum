# sweep45 — batch 01 — `src/drill.py`

Read-and-report audit. **No source file was edited by this batch.** The standing
`DRILL_BREACH` halt was not touched, and no battery tool (`drill.py`, `verify_math.py`,
`allsweep.py`, `publish.py`) was run.

---

## 0. Coverage, stated honestly

**The whole file was read, end to end, with one caveat about line numbers that is worth
stating precisely because this project's whole discipline is not letting a partial reading
look like a complete one.**

`src/drill.py` was **11,785 lines when this batch started and 11,824 lines when it
finished.** A worker added 39 lines to `drill_profile` (the new
`the_validator_is_what_refuses_it` net, current lines 4776–4813) part-way through my read.
Concretely:

| what I read | file version |
|---|---|
| lines 1 – 6800 | the **pre-edit** file (11,785 lines) |
| lines 6801 – 11,825 | the **post-edit** file (11,824 lines) |
| lines 4755 – 4824 (re-read) | the **post-edit** file, to cover the new 39 lines |

The edit was a pure insertion inside `drill_profile`. Verified by anchor diffing: every
top-level `def` after the insertion point moved by **exactly +39** and by nothing else
(`_partial_canary_merges` 5219 → 5258; `_guards_are_wired_where_claimed` 6703 → 6742;
`drill_inspector` 6766 → 6805). So content before line 4775 and after line 4814 is
identical in both versions, and the inserted block was read separately. **There is no
unread region.** All line numbers quoted below are **post-edit / current**.

I did not re-read the whole file after the edit. If a second, non-insertion edit landed in
the same window, I would not have seen it — but the uniform +39 offset across four widely
separated anchors is strong evidence against one.

**Measured:** 394 `net()` call sites in the source. Several sit in loops (8 credential
fixtures in `drill_publish`, 4 struck-off buckets in `drill_cascade`), so the runtime net
count is higher — consistent with the ~403 the brief names.

---

## 1. Findings filed

Ranked worst first. Every one was verified against source (and, where it depends on
another module, against that module) before filing.

### 1.1 `76e870e21631` — MINOR / RUN — a net pinned to the current **length** of `APPEND_ONLY`

`an_acknowledged_shrink_is_carried_and_nothing_else_is` (in `drill_ledgers`, ~4182–4235)
hard-codes six literal counts that are all a direct function of `len(ledger_guard.APPEND_ONLY)`:

```
if ok or len(probs) != 2                       # one shrink link x 2 ledgers
if not ok or probs or len(carried) != 2
if ok or len(probs) != 2 or len(carried) != 2
if ok or len(probs) != 2 or len(carried) != 2
if ok or len(probs) != 4                       # 2 ledgers x 2 shrink links
return ok and not probs and len(carried) == 4
```

**Verified:** `ledger_guard.APPEND_ONLY == ('HANDOFF.md', 'handoff/HANDOFF.md')` — exactly
two. `verify_chain()` appends **one problem per ledger per shrinking link** (the inner
`for name, cur in (rec.get("ledgers") or {}).items()` loop guarded by `name in APPEND_ONLY`).
With a third append-only ledger every count becomes 3 / 3 / 3 / 6, and **every one of the
six assertions fails at once.** The net returns `False`, `net()` records `held=False`, and
`main()` escalates `DRILL_BREACH` at **OWNER** — the library halts over a correct change.

**That this list grows is not hypothetical.** `drill.py`'s own sibling net twelve lines up,
`the_writer_and_the_reader_of_a_snapshot_agree`, records in its docstring that
`handoff/HANDOFF.md` **joined** `APPEND_ONLY` on 2026-08-31, and its entire argument is
that a net here must be *"THE SHAPE, NOT THE ONE FILENAME … what must hold is that the two
functions agree for EVERY name in `APPEND_ONLY`, whatever those names become."* Its
neighbour does the opposite.

This is the class of orders `7cc460706efe` and `8ee268ce32cc` — a net pinned to an
incidental spelling blocking correct code — arriving through a *length* instead of a name.

Remedy is mechanical and loses no property: `n = len(LG.APPEND_ONLY)`, then `!= n`, `!= n`,
`!= 2 * n`, `== 2 * n`, plus `if n < 2: return False` so the net cannot go vacuous if the
list ever shrinks.

### 1.2 `fe3dc98ca42e` — MINOR / RUN — the singleton net's roster is typed, not derived

`singleton_guard_is_wired_into_the_daemons` (in `drill_codewatch`, ~9738) prints
**"every standing daemon refuses to run beside a twin"** and loops the literal
`("publish.py", "foreman.py", "overwatch.py")`.

**Measured:**

- `overnight.STANDING` holds **five** jobs: `dashboard`, `publish`, `foreman`,
  `overwatch`, `pipeline`.
- `grep -rn claim_singleton src/*.py` finds call sites in exactly three files:
  `foreman.py:1730`, `overwatch.py:971`, `publish.py:1711`.
- `dashboard.py` and `pipeline.py` call it **nowhere**, and carry no other twin guard.

This is the same defect the sibling net **forty lines above** was corrected for. That one
carries a paragraph headed *"THE ROSTER IS DERIVED, NOT TYPED (order 1f172f5acc6f, run
#37)"* saying it *"looped over the literal `("publish.py", "foreman.py", "overwatch.py")`
while its own title promised 'every standing daemon'"* — the identical three-name literal.
It now reads `STANDING` out of `overnight.py`'s parse tree. The singleton net kept the
literal.

The order names two things and is explicit that they must not be done in one step:

- **(a) the claim** — rename the net to what it checks, *or* derive from `STANDING`.
  **Deriving now takes the net red, and a red drill net halts the library.**
- **(b) the possible gap** — a design call, not a drill matter. Two dashboards contend for
  port 8777; two pipelines are a two-writer hazard on `state/PIPELINE_STATE.json` and its
  done-keys, which `drill_two_writer` and `drill_done_keys` exist to defend.
  `autostart.py:395` records a deliberate ruling that `claim_singleton` is the *wrong*
  instrument there (a concurrent `--status` run would read as a twin); whether the same
  reasoning covers `dashboard` and `pipeline` is not recorded anywhere I could find, and
  this order does **not** decide it.

### 1.3 `5156478c4583` — MINOR / RUN — the comment justifies a floor, the code enforces an exact count

`_meta_ban_has_no_fall_through` (~5353–5404). The comment at ~5390 reads:

> THE GATE MUST STILL BE THERE. An empty list is the "absence read as clean" shape: delete
> the call and every handler check below is vacuously true.

That argues for `if not guarded: return False`. The line under it is:

```python
if len(guarded) != 1:
    return False
```

which also refuses **two or more**. Nothing in the docstring or the comment says why a
second gated call to `pipeline.assert_in_universe` — a *strictly stronger* P8
meta-language ban — should be a fault, and structurally it is not one: the invariant the
net is named for ("no handler falls through") is a for-all over handlers and holds fine
across several `try` blocks. The loop below already reads only `guarded[0]`, so the fix is
to iterate every guarded node rather than to demand there be one.

`drill.py` states this hazard in its own words at `_publish_never_swallows_a_missing_safety`
— *"a net that goes red when a guard is improved teaches people to stop improving guards"* —
and that net had its own census (`return arms >= 3`) **removed** for exactly this shape.
This is the same edit one file over, in the net standing between the charter's P8 ban and
every published chapter.

**Latent, not live:** `generate.py` has exactly one such `try` today, so the net is green.

### 1.4 `57ab902a45ae` — INFO / RUN — two small stale things

1. **A docstring that no longer matches its return.** `_esc_sandbox` (~7539) says
   *"RETURNS a (dir, restore) pair"* and returns a **three**-tuple, `return d, filed,
   restore`. Every caller unpacks three, and the middle element `filed` is load-bearing —
   it is the collected work-order calls that
   `an_escalation_reaches_the_queue_addressed_and_graded` asserts on. Item 4 of the brief
   (a guard whose comment no longer matches its code) in its mildest form.
2. **A dead import with a dead delete.** `_call_clear_from` (~8413) opens with
   `import io as _io` and its `finally` ends with `del _io`. `_io` is never read between
   them. Harmless, but it is dead code inside the probe that proves a forged frame cannot
   lift the halt, and `liveness.py` does not see statement-level dead code inside a nested
   `def`.

**Handler note for all four:** `drill` is in `local_agent.DENYLIST`, so the free local
model is structurally forbidden to write this file. Routing any of these to LOCAL would
reproduce order `9b54659bc403`. RUN is the lowest rung that can honestly close them.

---

## 2. Corroborated — already open, deliberately not refiled

Ten open orders name `drill.py` or a net in it. Everything below was met during this read
and confirmed still standing; none is refiled.

| order | what I confirmed |
|---|---|
| `a34f10a87483` | `there_is_no_paid_lane` (~6358) still ends `return not named and "THERE IS NO PAID LANE" in text`. Open as an owner question, correctly. |
| `71ae3fa7e55e` | The standing `DRILL_BREACH` in `state/HALT.json` is `publish refuses to push while a mutation run is active` — `publish_asks_before_pushing` (~10951). Consistent with a tree read mid-edit. **The tree moved under me too** (§0), which is the same phenomenon, so this is corroboration rather than a new finding. |
| `247b173c78ee` | `_a_reap_never_takes_a_live_runs_sandbox` (~10788) unchanged. |
| `31a946e96c69` | `_the_log_roll_off_archives_before_it_trims` (~9965) unchanged. |
| `5fa88a896c3f` | `denied_write_leaves_phase_open` still drives `gate_done(st, 'cosmology', ...)`. |
| `630fe4529c51` | `reason_matches_verdict` (~5099) unchanged. |
| `b53dd5b3f76f` | `_a_broken_maintenance_guard_fails_open` (~3823), eight cases as described. |
| `a5de2dcb9447` | `drill_no_caps` — the mixed feat/feat-less short-circuit is still unstated and the net still says so in its own docstring. Owner ruling still pending. |
| `06b7f22484df` | `restarts_are_budgeted` / `the_live_claim_path_runs_out_and_refills` both present, as the order describes. |
| `864a626a258e` | `CLAUDE.md` still says "attacks all 57 nets"; the real figure is 394 `net()` call sites (more at runtime). Corroborated. |

---

## 3. Deliberate design — examined and **deliberately not filed**

Each of these looks like a finding under a mechanical reading and is, on the evidence in
the file, a considered choice. Recorded so the next sweep does not spend its budget
re-deriving them.

1. **`sweep_fire_polarity` (~6524) is pinned to a parameter *name*.** It requires
   `fire.args.args[0].arg == "ok"`, requires the branch test to be a bare `ast.Name`
   (`if ok:`, not `if ok is True:`), and takes the **first** `ast.If` in `_fire`'s body — so
   a rename, a reformulation, or an added guard clause all breach → OWNER halt. The
   docstring names this explicitly: *"Pinned this way so that swapping the two bodies,
   negating the test, or renaming the parameter all read as BREACHED rather than as a
   passing rewrite"*, and calls the parameter name *"a contract change, not a refactor"*.
   It is the closest thing in the file to orders `7cc460706efe` / `8ee268ce32cc`, and it is
   the one place where the author argued for the pin rather than arriving at it by
   accident. **Left to the owner as a judgment call rather than filed as a defect.**

2. **`paid_access_stays_switched_off` (~7232) returns `True` on `FileNotFoundError`.** On
   any machine without `~/cascade/config.json` the net cannot fail. The docstring works
   through this at length (fault 2 of four) and separates "not this machine" from
   "unreadable" deliberately, noting each into the health ledger under its own name.
   Correct, and the alternative (breaching on another project's absent file) is the outage
   the same paragraph describes.

3. **`gate_claim_matches_reality` (~6817) returns `True` early when the prose gate is
   open**, and `catalog_matches_disk` returns `True` when `catalog.json` is absent. Both
   are documented soft edges, and the prose gate is pinned CLOSED by a separate net in
   `drill_dispatch`, so the early return is unreachable today.

4. **`_the_retry_loop_runs_at_least_once` (~2545) asserts a constant** —
   `ESC.STOP_CAS_ATTEMPTS >= 1` — which is the exact shape this file has cut out of itself
   three times (`_throttle_hands_off`, `_backoff_stops_at_its_ceiling`,
   `restarts_are_budgeted`). Here the docstring makes the case that the constant is what
   four separately-recorded "equivalent" mutants silently rest on. That is a real reason,
   and the net is cheap.

5. **`daemons_actually_check_their_own_source`'s `if len(names) < 3: return False`** is a
   hard floor against a derived roster. Documented (*"a roster that shrank proves
   nothing"*) and deliberately unsatisfiable by an absence.

---

## 4. Classes searched and found clean

Reported so the absence is on the record rather than merely unmentioned.

- **Tautological comparisons.** AST scan for `Compare` nodes whose two sides unparse
  identically: **none**.
- **`or True` / `and False` defanging.** AST scan for constant operands inside `BoolOp`:
  20 hits, every one a legitimate `x or ""` / `x or {}` coalesce (e.g. `r.stdout or ""`,
  `(rec or {}).get(...)`). **No defanged assertion.** (`_refusal_is_recorded`'s historical
  `or True`, named in its own docstring, is long gone.)
- **Unmarked truncation (Hard Rule 0).** AST scan for constant-bounded slices across the
  whole file: **one hit**, `seed[:3]` in `_the_log_roll_off_archives_before_it_trims`,
  which is a fixture *expectation* (the three cycles that must roll off), not a cap on an
  output. `main()`'s breach reporting is uncapped in all three places (`print`, the halt
  `what`, and `evidence`), per order `2f679246a6e4`.
- **Call-free `net()` lambdas** (the "asserts a constant" shape): **one**,
  `BH.BINDING_MISBOUND_BELOW < BH.BINDING_CONFIRMED_AT`, which is a deliberate band check
  with its own written expectation.
- **`except Exception:` that returns without recording.** 35 handlers examined. Every one
  either re-raises, returns a *verdict* the net acts on, or calls `silence.note` /
  `escalate`. The two bare `pass` handlers (`~7123` killing a child process in a `finally`,
  `~11755` a last-resort nested `silence` import) are cleanup, not verdicts. **The
  project's signature defect is not present in this file.**
- **Vacuous `all(...)` over a possibly-empty collection.** Every source-shape net that
  quantifies is guarded by a `bool(...)` on the collection first —
  `_halt_is_not_breakage`, `_identity_probe_is_gated`,
  `_local_buckets_excluded_from_cloud_claims`, `resync_cannot_revert_an_exclusion`,
  `generator_actually_skips_an_excluded_source`, `mutation_never_touches_the_live_tree`.
  The one unguarded quantifier is `an_acknowledged_shrink_is_carried_and_nothing_else_is`
  over `APPEND_ONLY`, which is finding 1.1.
- **Area coverage.** All 37 `drill_*` area functions are present in `main()`'s dispatch
  tuple; none is defined-but-never-run. Checked by set comparison against the file's
  top-level `def` list.
- **Symbols with no caller.** No orphaned top-level helper found: every `_`-prefixed
  module-level function in the file is reached from at least one `net()` attack or from
  another helper that is.

---

## 5. One process observation, not a code finding

The tree did not hold still. `src/drill.py` gained 39 lines while this batch was reading
it. That is the same condition order `71ae3fa7e55e` records as the cause of the standing
halt, and it is why §0 above is written the way it is rather than as a bare "read the whole
file". A sweep agent that had not noticed would have filed line numbers that were wrong by
39 from `drill_profile` onward — which is, precisely, an audit that looks complete and is
about a different file.
