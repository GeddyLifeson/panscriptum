# run46 batch 12 -- AUDIT

Modules read end to end, every line: `src/workorders.py` (1774), `src/rigor.py` (1052),
`src/codewatch.py` (763), `src/autostart.py` (564), `src/anchors.py` (457), `src/pick_model.py`
(417), `src/roll.py` (289), `src/propagation.py` (254). 5,570 lines. Also read, for the two
assigned context questions, the relevant sections of `src/escalation.py` (`escalate()`, in
full) and `src/drill.py` (the `DRILL_BREACH`/`DRILL_COMPLETE` escalation call sites) -- not
part of the batch and not included in the coverage call below, but necessary to answer the
brief's own questions from source rather than from the comments in this batch's files.

## FILED

### WORKORDER_WHERE_IDENTITY_UNDISCOVERABLE -- MAJOR -- RUN -- order `fb5ac415e249`

**This answers the brief's first assigned question.** `order_id(code, where)` deliberately
makes `where` part of a fault's IDENTITY -- `order_id`'s own docstring: "content-addressed
... the same net finding the same fault on the next cycle must UPDATE one order, not file a
second." **So yes, this is intended**: `where` is a KEY, not a description, and the
`BATTERY_WHERE` table comment says as much in capitals ("THE `where` IS PART OF THE FAULT'S
IDENTITY"). Widening or reformatting `where` between two filings of what a caller considers
"the same" fault is, by the letter of the contract, filing a DIFFERENT fault-identity --
which is exactly what happened today.

**And no, it is not discoverable.** Nothing in `workorders.py`:

- warns a caller, at filing time, that a code already has an open order under a *different*
  `where` (which would flag "did you mean to widen `where`, or is this a duplicate?");
- surfaces, in `--twins`, `main()`'s report, or any `sweep_detectors()` check, a listing of
  "codes open under more than one `where`" as a thing worth a human's attention;
- documents the FAILURE MODE anywhere. `order_id`'s docstring and the `BATTERY_WHERE` comment
  explain the mechanism (content-addressing) but never say what happens when a caller gets it
  wrong: the old order is never resolved (nothing re-fires `resolve_code(code, where=<the old
  string>)`), so it sits open forever, invisibly, beside the new one.

So an operator who widens `where` gets no warning, no report, and has to notice the duplicate
by eye -- which is what happened.

**Concrete illustration that this is not hypothetical, verified against current source (not
currently broken, but held together only by coincidence):** `drill.py`'s OWNER-level
`DRILL_BREACH` escalation (`src/drill.py:13567-13569`) calls
`ESC.escalate(ESC.OWNER, "DRILL_BREACH", ..., who="drill.py")` with **no `source=` argument**.
`escalation.escalate()` files the resulting work order at `where=rec.get("source") or ""`
(`src/escalation.py:322-324`) -- i.e. `where=""`, because `source` was never supplied.
`workorders.sweep_detectors()`'s own auto-close for `DRILL_BREACH`
(`src/workorders.py`, section 6 "ORDERS FILED BY THE ESCALATION CHAIN", ~line 1295) calls
`resolve_code("DRILL_BREACH", ..., by="workorders.sweep")` with **no `where` argument
either**, so it also defaults to `where=""`. The two sides currently agree *only* because both
independently leave `where` at its default, and nothing in either file asserts that agreement
or would notice its loss. If `drill.py` were ever changed to pass `source=<net name>` -- a
reasonable improvement in its own right, to distinguish which net breached -- `DRILL_BREACH`
orders would silently stop auto-closing: `order_id("DRILL_BREACH", "")` would keep matching an
increasingly stale order while every real breach mints `order_id("DRILL_BREACH", <net
name>)`, and the close-on-clean-rerun code would never touch either. A permanently open
OWNER-severity order sitting beside orders that keep refiling and never closing is exactly the
"alarm that always sounds is furniture" shape Hard Rule -1 warns about -- and it would arrive
in total silence, because nothing flags a code open under more than one `where` as worth a
second look.

Filed at RUN rather than OWNER/SESSION: the remedy is a docstring addition plus a new
diagnostic report, not a curatorial judgment call, and doesn't touch `prose_enabled` or
`step4_enabled`.

## ANSWERED, NOT FILED (context question 2 -- `codewatch.py`)

**"A job that exhausts its budget runs STALE on purpose... DO look for whether anything tells
a person it happened."** It does, and the mechanism checks out end to end:
`exit_if_stale()`, on a refused restart, calls `escalation.escalate("MANAGER",
"CODEWATCH_BUDGET", why, ..., source=who, who="codewatch")` (src/codewatch.py:717-725).
`escalation.escalate()` (`src/escalation.py:308-326`, read in full to answer this) turns
**every** escalation into a work order unconditionally: `WO.file_order(rec["code"],
rec["what"], handler, severity, where=rec.get("source") or "", ...)`, with MANAGER mapping to
`handler="RUN"`, `severity="MAJOR"`. Since `source=who` here is the stable job name (e.g.
`"dashboard"`), repeated `CODEWATCH_BUDGET` escalations for the same job correctly *refresh*
one open order (`seen` climbs, `last_seen` advances) rather than minting duplicates -- this is
the same `order_id(code, where)` machinery as the finding above, used correctly because
`source` here is a fixed string. So: yes, a person reading the RUN rung of the work-order
queue is told, by name, which job ran out of restart budget and why. Confirmed this is not
conflated with the "ledger write was denied" case either: `exit_if_stale` computes
`spent = used >= BUDGET_PER_HOUR` from the ledger-read count returned by `_take_locked`
*before* the write attempt, so a denied write (which also returns `used_before` under
`BUDGET_PER_HOUR`) reads as `CODEWATCH_LEDGER_DENIED`, not `CODEWATCH_BUDGET` -- the two
incidents the brief asked to keep distinguishable stay distinguishable through to the queue.

One real but minor gap, not filed as an order because it's a nice-to-have rather than a bug:
`codewatch.py`'s own CLI (`python src/codewatch.py`, no flags) can only ever report the
restart *ledger* (ticks per job in the rolling hour) -- it has no way to say "job X is
*currently* stale right now," because `stale()`'s state (`_START`, `_PENDING`) lives in the
daemon's own process memory and is never written to disk. A fresh `--status`-style invocation
genuinely cannot see it. This is covered end-to-end by the work-order path above, so it isn't
a silent gap in the "does a person get told" sense the brief asked about -- just a limit on
what the CLI alone can show without also checking the queue.

## READ, NO FINDING

- **`src/workorders.py`** -- full read, 1774 lines, beyond the finding above. `_mutate`'s
  compare-and-swap, `resolve()`'s land-then-append ordering, `ghost_orders()`'s time-based
  (not disjointness-based) separation of recurrence from restore, `cap_boundary_scan()`'s
  exact-length ratchet, and every `sweep_detectors()` section's `_fire`/`_detector` polarity
  all check out against their own docstrings' claims, verified on the executable line rather
  than the comment. No unmarked caps found (`main()`'s 70-char per-row summary explicitly
  marks the cut and points at the full order). `shell_active()`/`SHELL_ACTIVE` matches the
  brief's description of today's widening (backtick, `$`, backslash, both quote marks, `;`,
  `|`, `&`, `>`, `<`, newline, `!`) and is only consulted on the `--how` (argv) path, correctly
  skipped for `--how-file` and `--how -`.
- **`src/rigor.py`** -- full read, 1052 lines. The module header's own "CLOSED" claim about the
  faculty-weight erratum is verified live rather than asserted (`main()` derives `_muted` from
  `assay.FACULTY_WEIGHTS` at runtime). `bradley_terry`'s two independent refusal conditions
  (disconnected graph / unbounded MLE) are evaluated separately as the comment claims, not
  chained. `mathematical_resonance()`'s display cut in `main()` correctly extends through tied
  fanout values rather than splitting a tie. No unmarked caps.
- **`src/codewatch.py`** -- full read, 763 lines, beyond the answered question above.
  `fingerprint()`/`quiet_seconds()` both fail closed (return `None`) rather than treating an
  unreadable file as unchanged; `_take_locked` fails closed on a denied ledger write rather
  than granting an unrecorded restart; `twins()`'s self-exclusion is additive, not
  replacing. `fingerprint()`/`quiet_seconds()` only scan `.py` files directly under `src/`
  (not `src/deprecated/catalogue_local.py`, one level down) -- consistent with the rest of the
  module treating `src/` as the flat, live tree, and `deprecated/` is (by its name and
  location) exactly the code this daemon-restart mechanism has no reason to watch.
- **`src/autostart.py`** -- full read, 564 lines. `installed_state()`'s three-way byte compare,
  `install()`'s temp-then-readback-verify, `supervisor_alive()`'s and the job-roster loop's
  tri-state (`True`/`False`/`None`, tested with `is`, never bare truthiness) all check out.
  `_twin_watchdog()`'s retry-then-fail-open-and-log matches its docstring.
- **`src/anchors.py`** -- full read, 457 lines. Every invariant `run()` claims to check (ladder
  coverage, decimal-produced, monotone ordering, and each anchor's own stated claim from its
  `note`) is actually graded into `verdicts` and gates the exit code; none of the five is a
  printed-and-discarded assertion.
- **`src/pick_model.py`** -- full read, 417 lines. `save_config()`'s atomic replace-with-
  readback, the VRAM-measured-vs-assumed provenance carried through `_budget_note()`, and the
  `refused`/`excluded`/`scored` three-way split (VRAM-refused vs. not-a-text-model vs. usable)
  all check out against the printed diagnosis. `FAMILY_TIERS` ordering (more specific strings
  before their own prefixes, e.g. `"qwen3"` before the bare `"qwen"` catch-all) is correct
  given the tier-major iteration order.
- **`src/roll.py`** -- full read, 289 lines. `mutate()`'s pre-read digest and re-apply-on-
  refusal, `exclude()`'s required-note guard and honest write-verdict return, and
  `update_rows()`'s `seen`-means-found-not-changed fix all check out. `main()`'s uncut
  name/reason printing matches the "RETURNS THE REASON, NOT JUST THE NAME" doctrine stated in
  `out_of_scope()`'s docstring.
- **`src/propagation.py`** -- full read, 254 lines. `observed_mark()`'s claim that the
  trailing `return 0` is unreachable was re-derived independently (`ascension_years(1) == 0.0`
  once `RUNG_COST_EXPONENT` and the loop range are applied, so the `rung=1` iteration of the
  countdown loop always matches once `lag >= 0`) rather than taken on the comment's word.
  `load_graph()` and `shortest()` raise/return `inf` rather than fabricating a distance on a
  missing or malformed graph file; every caller found via `grep` across `src/` that actually
  invokes `load_graph()`/`shortest()` (`thread_integrity.py`) wraps it in its own
  try/except with a named failure message, so the unguarded raise here is the correct contract
  for a leaf function, not a gap.

## QUESTIONS

None beyond the two the brief asked outright, both answered above (one filed as a finding, one
answered inline because the mechanism checks out).

## COVERAGE

Recorded via `sweep_plan.record('run46', [...], batch=12)` for all eight assigned modules
(`workorders.py`, `rigor.py`, `codewatch.py`, `autostart.py`, `anchors.py`, `pick_model.py`,
`roll.py`, `propagation.py`) -- each read end to end. `escalation.py` and `drill.py` were also
read (the specific sections needed to answer the brief's two questions from source) but are
not included in the coverage call since they were not part of this batch's assignment.
