# Sweep 41 — Batch 01 audit: src/drill.py

Auditor: sweep41-batch01. Scope per assignment: `src/drill.py` only (10,433 lines — the whole
batch). Read in full, top to bottom, in ~300-800 line chunks, with cross-reads into the modules
it drives (`silence.py`, `pipeline.py`, `publish.py`, `scout.py`, `mutate.py`, `ledger_guard.py`,
`escalation.py`, `prose_gate.py`, `workorders.py`) wherever a claim needed verifying against the
actual code rather than against drill.py's own comments about that code. This is an AUDIT: no
file under `src/` was edited.

## What this file is

`drill.py` attacks the library's safety nets (378 nets across 37 `drill_*` areas, per the battery
run cited in my brief) and reports HELD/BREACHED per net, rather than merely asserting the nets
exist. It is, by a wide margin, the most self-critical file I have ever audited: a very large
fraction of its own body is prose recording nets that were *previously found to be unfailable*
(via prior sweeps, numbered "run #NN", and named work orders), together with the fixed version and
an explanation of exactly how the fixed version differs from the broken one. Standing lesson 9
("a check that cannot fail looks exactly like a check that passed") is treated as the file's
entire reason for existing, and it shows: dozens of nets carry paragraphs of the form "THIS NET
COULD NOT FAIL UNTIL —" followed by the fix.

I verified that all 37 `drill_*` area functions defined in the file are actually included in
`main()`'s dispatch loop (lines ~10245-10255) — none is orphaned/unregistered, which would itself
be a "check that cannot fail" of the worst kind (an area whose nets never run at all). All 37
matched.

## Findings filed

Given how thoroughly this file already guards against "a net that cannot fail" and "a net whose
name is wider than what it measures" (both explicit hunting targets in my brief), I did not find
a fresh, unverified instance of either pattern that isn't already tracked by an existing order
number cited in the file's own comments (see "Considered and NOT filed" below). What I did find,
verified against the actual downstream source of each library module, is a cluster of five
instances of the **other** hunting target: probes that deliberately manufacture a failure inside
a real library function, where that function's failure path is a genuine `silence.note(...)` /
`health.record(...)` call (or, in one case, also a write to a live log file) — and the probe does
**not** use `_deliberately_failing`/`_quietly`/a stand-in `silence` object the way sibling probes
in the same file correctly do. Each of these leaves a real row in `state/failures.json` (and in
one case a line in `state/pipeline.log`) on every single drill run, which is exactly the shape
`_deliberately_failing`'s own docstring names as "worse than noise ... manufacturing the exact
signal it exists to prove the library can raise, in the file a person consults to find out
whether the library has raised it."

All five were verified by reading both the drill.py probe body and the exact line(s) of the
downstream module it drives, confirming the trigger condition the probe manufactures is the one
that reaches the `silence.note`/log call, and confirming no wrapper (`_deliberately_failing`,
`_quietly`, `PL.silence = _quiet(_S)`, a stand-in `silence` module, etc.) is present anywhere in
the enclosing function. Filed as five work orders, all under one code
(`DRILL_PROBE_LEDGER_LEAK`, since it is one class of defect with five independent, mechanically
identical fixes), handler LOCAL, severity MINOR — each is a self-contained one-line-or-so change
to drill.py itself, none touches library behaviour, and none affects the actual safety
properties under test.

1. **`630fe4529c51`** — `drill.py:reason_matches_verdict` (area `drill_stale_writer`, net "a
   DENIED rename gives back the reason it was denied, not 'landed'", ~line 4567). Drives
   `silence.replace_if_unchanged(t3, dst, expected, attempts=1)` into a genuine denied rename
   (held file handle on Windows / stand-in `PermissionError` elsewhere), unwrapped.
   `replace_if_unchanged`'s last-attempt `PermissionError` branch calls
   `note("replace-denied:" + basename(dst))`. Its sibling net immediately below it in the SAME
   function, `the_loser_of_a_race_is_refused_mid_backoff`, drives the same function's refusal
   path and *is* wrapped in `_deliberately_failing`, with a comment explaining exactly why
   ("the REFUSAL calls `silence.note` ... same reason as the two probes in
   `drill_recorders_and_lane`"). `reason_matches_verdict` was simply missed when that discipline
   was applied to its neighbour.

2. **`b53dd5b3f76f`** — `drill.py:_a_broken_maintenance_guard_fails_open` (area `drill_publish`,
   net "an absent, broken or dead maintenance guard still PUBLISHES", ~line 3477). One of its
   eight guard-file fixtures (`"not json"`, literal `"{ not json at all"`) hits
   `publish.maintenance_shift_live`'s `except Exception` branch (`publish.py` ~line 1435), which
   calls `silence.note("publish.py:maintenance-guard")`. None of the eight cases in this helper
   are run through `_deliberately_failing`.

3. **`31a946e96c69`** — `drill.py:_the_log_roll_off_archives_before_it_trims` (area
   `drill_scout`, net "a cycle rolling out of the log is ARCHIVED before the log is trimmed",
   ~line 8627). Its fourth assertion sets `_S.append_line = lambda *a, **k: False` and calls
   `SC.sweep(...)` to prove the log survives a failed archive write. `scout.sweep`'s roll-off
   code (`scout.py` ~line 701) calls `silence.note("scout.py:archive-unwritable")` on exactly
   that condition. The test redirects stdout/stderr (suppressing the printed warning) but that is
   not the same thing as suppressing `silence.note`/`health.record`.

4. **`5fa88a896c3f`** — `drill.py:denied_write_leaves_phase_open` (area `drill_two_writer`, net
   "a phase whose write did NOT land is left open", ~line 3850). Calls
   `PL.gate_done(st, "cosmology", [True, True, False, True])`. Every OTHER pipeline.py-driving
   net in this file (`_chain_done_key_follows_the_disk`,
   `_write_phase_stays_open_when_everything_refuses`,
   `_a_denied_batch_write_stays_on_the_failed_list`, `_a_done_marker_cannot_accumulate`,
   `_the_catalogue_cannot_erase_what_it_did_not_author`) stubs `PL.log = lambda *a, **k: None`
   and `PL.silence = _quiet(_S)` before touching pipeline.py. `drill_two_writer` stubs neither.
   `pipeline.gate_done`'s refusal branch (`pipeline.py` ~lines 739-741) both appends a real line
   to `state/pipeline.log` via the unstubbed `log()` AND calls
   `silence.note("pipeline.py:phase-not-marked-done")`. This is the most consequential of the
   five: it is the one function in this cluster whose sibling tests in the very same drill area
   already demonstrate the correct fix, and it writes to two live files rather than one.

5. **`247b173c78ee`** — `drill.py:_a_reap_never_takes_a_live_runs_sandbox` (area `drill_mutation`,
   net "a reap never deletes a sandbox whose owner is still running", ~line 9408). Its "expired"
   fixture (`started=time.time() - (M.OWNERSHIP_CEILING_SECONDS + 3600)`) deliberately exercises
   `mutate.py`'s ownership-expiry branch during `M.reap_orphans(older_than=0)`, which calls
   `silence.note("mutate.py:owner-claim-expired")` (`mutate.py` ~line 922-923). None of this
   helper's four fixtures are wrapped.

None of these five affect what the nets actually prove — every one of the underlying assertions
is correct and the refusal really is being exercised for real, which is the whole point of these
being *behavioural* rather than source-shaped nets. The defect is purely that the manufactured
failure is audible in the wrong place: the operational ledger a person consults to decide whether
the *library* has a real fault, rather than only in the drill's own report.

## Considered and NOT filed

- **The mixed feat-bearing/feat-less short-circuit in `drill_no_caps`** (docstring of
  `the_feat_bearing_path_really_is_untouched`, ~line 1706-1727): the docstring itself already
  poses this as an open OWNER question and names the tracking order (`a5de2dcb9447`) — "It may
  well be the intended selection rule ... and it is not a drill's place to decide it." Re-filing
  this would duplicate an order that already exists and is already framed correctly as a
  question, not a finding. Left alone.

- **`_page_is_real_gate`'s net name** ("a block page is refused before the model ever sees it")
  reads as an end-to-end claim about call ordering, but the function only unit-tests
  `feats.page_looks_real`'s classification, not that it is actually invoked ahead of the model
  call on every path. I considered filing this as a "net named wider than what it measures," but
  every other predicate-only net in this file (there are dozens, e.g. the whole of
  `drill_assay_engine`, `drill_resonance`) is named the same way and the project's own convention
  throughout is to name a net for the *property*, not for the calling context, so this reads as
  house style rather than a fresh instance of the named-too-wide defect. Not filed; low
  confidence it would be treated as a finding on review.

- **`exclusion_is_readable_and_reasoned` / `excluded_sources_keep_their_records` /
  `unreadable_roll_does_not_exclude_the_library`** (`drill_scope`): each of the first two returns
  `True` when nothing is currently excluded on the live roll. This looks at first glance like the
  "vacuous pass" shape the file elsewhere treats as a defect, but both are explicitly commented
  as deliberate ("nothing excluded is a lawful state") and this is the same pattern the file uses
  correctly and repeatedly elsewhere (e.g. `a phase that correctly wrote nothing is not held
  open`). Not a finding.

- **Broader sweep of every `silence.note`/`health.record` call site in `src/`** (I grepped all of
  them, ~48KB of hits across the tree) against every drill.py probe that might reach one: I did
  this systematically for the modules drill.py actually drives into a deliberate failure branch
  (`silence.py`, `pipeline.py`, `publish.py`, `scout.py`, `mutate.py`, `ledger_guard.py`,
  `gpu_lane.py`, `binding_health.py`, `compress_store.py`, `escalation.py`), and turned up the
  five above plus several I confirmed were already correctly handled (the whole of
  `drill_escalation_behaviour` stubs `health.record` directly at the sandbox level so no
  individual wrapping is needed there; `_esc_sandbox`'s `_H.record = lambda *a, **k: recorded
  .append(...)` catches every site in one place; `a_lost_release_reaches_an_escalation`,
  `a_competing_flush_cannot_clobber_the_recorder`, `a_misaddressed_blob_is_refused`, and
  `a_probe_leaves_the_failure_LEDGER_alone` in `drill_recorders_and_lane` are all correctly
  wrapped; `_quarantine_reports_the_disk_not_the_intention` stubs `silence.note` directly;
  `an_unparseable_chain_line_fails_the_chain` and the `verify_chain` net are wrapped). I did not
  exhaustively check every remaining site in modules drill.py touches only lightly (e.g.
  `binding_health.py`'s `load` calls, `autostart.py`, `axis_correlation.py`) — this is the one
  place I would flag as genuinely incomplete coverage if another pass wants to extend it, though
  I saw nothing in my reading of drill.py that drives a deliberate failure through those specific
  sites.

## Not re-reported (per brief)

`drill 378 nets / 0 BREACHED` and `verify_math`'s 2 known FAILED rows are the live battery state
per my brief and are not re-filed here. I did not find any drill.py-side cause for either — both
are already attributed elsewhere.

## Coverage

Recorded via `sweep_plan.record('run41', ['drill.py'], batch=1)`.
