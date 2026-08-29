# SWEEP 37 — BATCH 02 — `src/drill.py` (5,623 lines, 251 nets)

Read completely, in eleven slices, top to bottom. No source file was edited. Every claim below
was put to the real function with a fixture built in a scratch directory; the fixture scripts
ran under `PYTHONIOENCODING=utf-8 C:/Users/imarl/miniconda3/python.exe` and the verbatim verdicts
are quoted. Where a net is accused of being vacuous, the defeat was BUILT AND RUN. Where a net
was suspected and turned out to bite, that is recorded too — a false accusation costs the next
run more than a missed finding.

The dominant fault class in this file, again, is the one run #37 named this morning: a net that
asserts PRESENCE (a call node exists somewhere in the module) where the claim is REACHABILITY
(the call runs on the path that matters). Orders `07c7379597ba`, `18612d60c3f2`, `5737db3ce725`
and `adc3dc9c3fc6` fixed six such nets. **Fourteen more were left behind, and eleven of them are
provably defeated below.** The instrument to fix them already exists in this file
(`_live_walk`, `_calls_within(..., reachable=True)`, `_defn`, `_bound_from_call`); the nets
below simply were not converted.

---

## PROVEN VACUOUS — a fixture that does the forbidden thing and the net still reports HELD

### F1. `_local_buckets_excluded_from_cloud_claims` — drill.py:3133-3155 — MAJOR
Defeated **three independent ways.** The net requires only that *some* `if` in
`cascade_bridge.py` has `<x>.bucket.startswith(LOCAL_PREFIX)` in its test. It never asks what
the branch DOES, never asks whether the branch is reachable, and never asks whether it is the
router's branch.

| fixture | net verdict |
|---|---|
| the guard's body is `pass`, and an ollama bucket is handed straight out below it | `True` |
| the guard parked in dead code after a `return`; every bucket served | `True` |
| **the REAL `cascade_bridge.py` with the actual router guard (lines 1118-1120) deleted** | `True` |

The third is the one that matters. Deleting
```
        if cand.bucket.startswith(LOCAL_PREFIX):
            _ROUTER.release(cand)
            continue
```
leaves the net green, answered instead by the unrelated `if` at `cascade_bridge.py:282`
(`m.bucket.startswith(LOCAL_PREFIX) or m.bucket in seen`), which is a *catalogue de-duplication*
line, not a claim guard. The net's own expectation is "the router handing out ollama buckets
flooded a 10GB card with its own queue" — the exact regression it cannot see.
This is also the "depends on there being exactly one occurrence" hazard, arrived at from the
other side: there are already five `LOCAL_PREFIX` sites, so any one of them answers for the rest.
Confidence: **certain** (three fixtures, one of them the live file).

### F2. `_withdrawal_takes_a_snapshot` — drill.py:2550-2569 — MAJOR
`return _calls(p, "snapshot.before") and _calls(p, "snapshot.verify")`. `_calls` →
`_called_names` → `_call_spellings(tree)` with `reachable=False`, i.e. plain `ast.walk` over the
whole module. Fixture: a `withdraw_chapters.py` whose `main()` calls `shutil.move` on the
chapters with no snapshot at all, and whose `snapshot.before` / `snapshot.verify` calls sit
after the `return` and inside an `if False:` in a function nothing calls.
Net verdict: **`True`.** A file with no mention at all correctly returns `False`, so the net has
teeth against deletion and none against relocation.
This net's own docstring says it was rewritten in run #34 because "prose about a guard outlives
the guard". Dead code is prose that happens to parse, and it now outlives the guard here too.
Confidence: **certain**.

### F3. `guards_are_wired_where_claimed` — drill.py:3674-3697 — MAJOR
Six files, six `_calls` — same whole-file walk. Fixture: all six modules doing the ungated thing
on the live path, with `prose_gate.assert_gate_open()`, `_prose_enabled(cfg)` and `cachekey.load()`
each parked after a `return` or inside `if False:`.
Net verdict: **`True`** for all six simultaneously.
The expectation printed beside this net is "the last incident was a guard DELETED, not a guard
that failed" — and a guard moved into dead code is a guard deleted, with the parse tree left
behind as an alibi. Confidence: **certain**.

### F4. `the_meta_language_ban_is_actually_enforced` — drill.py:3702-3727 — MAJOR
Its behavioural halves (the refusal fires on meta-language, does not fire on in-universe prose)
are sound. The wiring half is `_calls(generate.py, "assert_in_universe")`. Fixture: a
`generate.py` that renders without ever checking, with the call in a dead `if False:`.
Net verdict: **`True`**. Confidence: **certain**.

### F5. `_supersession_is_called` — drill.py:2804-2813 — MAJOR
`_calls(workorders.py, "_supersede_binding_suspect")`. Fixture: a `workorders.py` where
`file_order` never supersedes anything and the only call is in a dead `if False:` inside an
uncalled helper. Net verdict: **`True`**. Confidence: **certain**.

### F6. `_failed_revert_is_escalated` — drill.py:1265-1298 — MAJOR (two faults)
**(a) dead code.** `_calls_within(tree, n, "_ESC.escalate")` is called WITHOUT `reachable=True`
(drill.py:1287), and the SAFETY-rung search below it is a bare `ast.walk(n)`. Fixture: a
`local_agent.run()` whose ALARM branch does nothing but set `out["ALARM"]`, with
`_ESC.escalate(_ESC.SAFETY, ...)` inside an `if False:` in that same branch.
Net verdict: **`True`** — a half-written module left on disk, the run reporting success, and the
net green.

**(b) pinned to one spelling of an import alias.** `_spellings_of_call` resolves
`X.escalate` to `{"escalate", "X.escalate", "escalation.escalate"}`, so asking for
`"_ESC.escalate"` matches ONLY if the alias is literally `_ESC`. Fixture: a **correct**
`local_agent.py` — real, reachable `ESC.escalate(ESC.SAFETY, ...)` in the ALARM branch — whose
only difference is `import escalation as ESC`.
Net verdict: **`False`.** A correct module fails the net. This is the "pinned to an
IMPLEMENTATION rather than the PROPERTY" shape that order `8ee268ce32cc` was filed for elsewhere
in this file; a rename of an import is enough to breach the drill, and a drill breach halts the
library. The fix is to ask for `"escalation.escalate"`, which the resolver already produces for
every alias. Confidence: **certain** (both halves).

### F7. `_run_marks_a_landless_run_failed` — drill.py:1301-1312 — MAJOR
`_subscript_assigns(run, "out", "ok")` walks `run` with `ast.walk`. Fixture: a `run()` that
returns `{"ok": True, "patches": []}` and carries `out["ok"] = False` on the line AFTER the
return. Net verdict: **`True`**.
This is the reachability half of `_landing_nothing_is_not_success`, whose whole subject is a
run that landed nothing being recorded as work done. Confidence: **certain**.

### F8. `_write_lane_checks_the_halt` — drill.py:1402-1420 — MAJOR (two faults)
Parses `inspect.getsource(LA.run)` and accepts any `ast.Call` whose func is named
`assert_clear`, anywhere in the tree.
* Fixture A: `run()` patches `src/` and then `return`s; `_ESC.assert_clear(...)` sits after the
  return. Verdict **`True`**.
* Fixture B: `logging.getLogger('x').assert_clear()` — an unrelated object's method of the same
  name — with no halt check anywhere. Verdict **`True`**.
The net's own docstring says it was rewritten off a substring scan "because the paragraph
explaining WHY the call is there still contained the word". A method name on an arbitrary object
is the same evidence a word is. Confidence: **certain**.

### F9. `_refusal_is_recorded` — drill.py:3091-3130 — MAJOR
Two whole-file `ast.walk` searches with no branch scoping. `records` is satisfied by ANY
assignment whose target is a subscript of a name `unreal` — any key, anywhere, in any function.
Fixture: a `feats.evidence_for` whose refusal branch is `pass` (the refusal is DROPPED, which is
the fault), carrying `unreal['unrelated'] = ...` on an unrelated line and returning
`{'pages_refused': unreal}`. Net verdict: **`True`**.
The distinction this net exists to protect — "no evidence" vs "we were blocked" — is not tested
by either half. It should require the assignment to be inside the refusal branch and keyed by
the title. Confidence: **certain**.

### F10. "the cap resets per run, not per process" — drill.py:1560-1562 — MAJOR
`lambda: (LA.blast_reset() or True) and LA._BLAST["patches"] == 0`.
`local_agent._BLAST` is `{"files": set(), "patches": 0}` and `blast_reset()` clears both
(local_agent.py:157-159). The net reads only `patches`. Fixture: `_BLAST` charged to
`{"files": {"a.py","b.py"}, "patches": 5}` and `blast_reset` replaced by one that clears
`patches` and forgets `files`. Net verdict: **`True`** — with two of `MAX_FILES_PER_RUN = 8`
permanently spent at the start of every subsequent run, which is verbatim the outcome the net's
own expectation names ("a cap that never resets turns into an outage on a long-lived process").
Secondary: at the moment this net runs, `blast_cap_bites`' `finally` has already called
`blast_reset()`, so on the `patches` half the net is comparing `0 == 0` in the common case.
Confidence: **certain**.

### F11. The two `cascade_bridge` TEXT nets — drill.py:3407-3414 — MAJOR
`src = open(cascade_bridge.py).read()` at drill.py:3407, then:
* "burial is documented as permanent-codes-only" — `all(c in src for c in ("401","402","404","410")) and "429" in src`
* "there is no paid lane to spend" — `"THERE IS NO PAID LANE" in src`

Fixture: a `cascade_bridge.py` whose entire content is a two-line COMMENT naming 401/402/404/410
and "THERE IS NO PAID LANE", a `permanent_refusal()` that `return True` for every error string
(so a 429 is buried permanently — the exact thing the expectation forbids), and a live
`PAID = {'enabled': True, 'cap': 500}`. Both nets verdict: **`True`**.
These are the last raw substring-over-file-text nets in the module; every comparable one was
converted in runs #34-#37. `permanent_refusal` is already driven behaviourally in
`drill_no_top_ups` (drill.py:3845-3880), so the burial net can simply be deleted or re-pointed
there; the paid-lane net needs a real predicate. Confidence: **certain**.

### F12. `_identity_probe_is_gated` — drill.py:2764-2790 — MAJOR
Order `07c7379597ba` scoped this to the gated ARM this morning, which was right, but the claim
is still EXISTENTIAL: "there is a `_probe_identity` call inside a `healthy is None and sources`
guard". It says nothing about the other call sites. Fixture: a `binding_health.sweep()` that
calls `_probe_identity(h)` **unconditionally for every host** and then also calls it inside the
gate. Net verdict: **`True`** — a network round trip per host per sweep, which is precisely the
cost this net exists to prevent, with the net green.
Its neighbour `resync_cannot_revert_an_exclusion` (drill.py:5151-5196) already states the
correct universal form ("every REACHABLE write is inside the guard"); this one needs the same
shape: every reachable `_probe_identity` call is inside a gated arm. Its own docstring even says
"It was unexploitable only because `binding_health.py` happens to contain exactly one call site
today" — that remains true of the *ungated* direction. Confidence: **certain**.

### F13. `_halt_is_not_breakage` — drill.py:1176-1239 — MAJOR
The loop `for n in ast.walk(tree)` finds `if idle >= IDLE_LIMIT`, does its checks, and
unconditionally `return`s at the end of the first match (drill.py:1237). A SECOND
`idle >= IDLE_LIMIT` branch is never examined. Fixture: an `overnight.py` with a correct first
branch (status bound, guarded `continue`, give-up outside) followed by a second
`if idle >= IDLE_LIMIT:` that prints "it is a broken one" and returns 1 with no halt check at all.
Net verdict: **`True`.**
This is this project's longest outage — a halted library read as a broken one — and the net is
one added `elif` away from missing it again. Confidence: **certain**.
(The net DOES correctly refuse the run-#37 dead-code defeat it was rewritten for: verified
`False` against that fixture. The fix is to require the property of EVERY matching branch.)

### F14. `generator_actually_skips_an_excluded_source` — drill.py:5116-5148 — MINOR→MAJOR
Order `07c7379597ba` upgraded this to "the answer is bound and FILTERS something", which is
right, but the comprehension may live anywhere in the module. Fixture: a `manifest_builder.py`
whose `build_jobs_for_source` queues every source unconditionally, plus
`_a_helper_nothing_calls(rows)` that binds `roll.out_of_scope()` and filters on it.
Net verdict: **`True`** — a builder that queues every excluded source, with the net green,
which is literally the five-day fault the net is named after ("a value produced where nobody
acts on it"). Should be scoped to `build_jobs_for_source` / the reachable job path.
Confidence: **certain**.

### F15. `drill_does_not_halt_during_a_mutation_run` — drill.py:5064-5093 — MINOR
Pinned to the alias `_MUT`, exactly like F6(b). Fixture: a **correct** `drill.py` with the
`if breached:` interlock intact, differing only in `import mutate as MUT`.
Net verdict: **`False`** — a correct file breaches. Also uses `_calls_within` and `_says` without
`reachable=True`, so the interlock could sit in dead code inside the `if breached:` block.
Ask for `"mutate.active"`. Confidence: **certain**.

---

## SCOPE HOLES — the scan does not cover what its name claims

### F16. `_no_programmatic_clear` and `_counts_decided_by_substring` never enter subdirectories — drill.py:1608-1690 and 4349-4394 — MAJOR
Both iterate `sorted(os.listdir(src))` and take only `f.endswith(".py")`. `src/deprecated/`
exists and holds `catalogue_local.py`. Fixture: a scratch `src/` with a clean top-level file and
`src/deprecated/lifter.py` containing a real, reachable
`import escalation; escalation.clear('a ruling long enough to pass')`.
`_no_programmatic_clear` verdict: **`True`** — "No module in src/ CALLS the halt's release" while
a module in `src/` calls it. `_counts_decided_by_substring` is blind the same way (returned `[]`).
The live `src/deprecated/catalogue_local.py` was inspected and does NOT call `clear`, so this is
a latent hole, not a live breach. Confidence: **certain**.

---

## SIDE EFFECTS AND FALSE-HALT HAZARDS

### F17. `datasette_config_is_generated_not_copied` writes to the live tree, and a DENIED write halts the library — drill.py:5441-5452 — MAJOR
```
p = corpus_db.datasette_metadata()
with open(p, encoding="utf-8") as fh:
```
`corpus_db.datasette_metadata()` (corpus_db.py:488-539) WRITES
`state/datasette.json` through `silence.write_json` and, since the run #36 fix, returns **None**
when the atomic replace is denied — which a running `datasette` holding the file is enough to
cause on Windows, and which `corpus_db`'s own docstring names as the expected case.

Fixture: `silence.write_json` stubbed to refuse only that path (exactly what a live datasette
produces). Result, through the real `net()` wrapper:
```
held=False error=TypeError: expected str, bytes or os.PathLike object, not NoneType
```
`net()` records a raised attack as a BREACH, and `main()` then calls
`ESC.escalate(ESC.OWNER, "DRILL_BREACH", ...)` — **an ordinary Windows file lock halts the whole
library.** That is the false-halt shape `_twins_ignores_a_foreign_tree` and
`live_reads_are_separated` were each rewritten for, arriving by a third route.

Two things are wrong and they are separable:
1. the net WRITES a real file in `state/` on every run, in a module whose header says "It never
   writes to the corpus... Every attack is constructed in memory or in a scratch directory";
   `datasette_metadata(path=...)` already takes a path, so a scratch path is a one-line fix (the
   same fix order `38ce9cb3b499` applied to `index_query_cannot_write` two nets above);
2. `p is None` must be handled as "could not measure" rather than as a breach — or, better, the
   scratch path removes the denial condition entirely.

Confidence: **certain** (reproduced through `drill.net()` itself).

### F18. Setup code outside `net()` aborts the entire battery instead of reporting a breach — MAJOR
Five statements execute at area-function call time, outside any `net()` wrapper, so an exception
in them is an uncaught traceback out of `main()`'s `for fn in (...)` loop: **all 251 nets go
unreported, `state/drill_last.json` is never written, and `workorders.py` then grades the
PREVIOUS run's verdict as current** — the failure `main()`'s own "WARNING: this run's verdict did
NOT land" paragraph was written against, reached by a route that never gets as far as that
warning.
* drill.py:2575 — `sid = SNAP.before("drill", ["config.yaml"], ...)` — takes a REAL snapshot;
  raises `SnapshotFailed` if `config.yaml` is locked or `state/snapshots/` is unwritable
* drill.py:2591 / 2597-2599 — the `os.listdir(SNAP.ROOT)` difference and its `rmtree`
* drill.py:1986 — `PL.stamp_record(rec, "pipeline.write_record")`
* drill.py:2621 — `tempfile.mkdtemp(prefix="stale_")`
* drill.py:3407 — `open(.../cascade_bridge.py).read()`

Confidence: **certain** (structural; read off the parse tree of `drill.py` itself).

### F19. The snapshot-litter cleanup can delete a CONCURRENT process's snapshot — drill.py:2591-2599 — MINOR
`_empty_before = set(os.listdir(SNAP.ROOT))`, then one `net()` runs, then every directory that
appeared in the interval is `rmtree`d. Anything else that calls `snapshot.before()` in that
window — `withdraw_chapters.py` is the caller this area exists for — has its backup deleted by
the drill, on the theory that "found by difference so nothing older is touched". The comment
directly above says the 151 pre-existing snapshots are left alone because "deleting a backup
somebody may be keeping is the owner's call"; the difference-based cleanup can do exactly that
to a backup created one second ago. Fix: remember the name `before()` actually returned (the
`drill-empty-*` prefix is known) and delete only that. Confidence: **high** (window is narrow;
the hazard is structural, not reproduced).

---

## READ AND FOUND GENUINELY SOUND

Each of these was suspected on reading, put to a defeat fixture, and **refused it.** Recorded so
the next run does not re-litigate them.

* `publish_asks_before_pushing` (drill.py:5004-5060) — the four-part interlock. Fixture: a
  `push()` importing `mutate` and raising "REFUSING TO PUSH: the ledgers are not intact" with
  zero interlock logic → **`False`**; a correct one → `True`. This is the strongest source-shape
  net in the file and the model the others should be rewritten against.
* `daemons_actually_check_their_own_source` (drill.py:4116-4150) — fixture with
  `exit_if_stale` called once at startup and never inside the loop → **`False`**; inside the
  loop → `True`. The reachable-inside-a-loop form is correct.
* `singleton_guard_is_wired_into_the_daemons` (drill.py:4294-4316) — reachable in `main`;
  same shape, sound.
* `resync_cannot_revert_an_exclusion` (drill.py:5151-5196) — fixture with ONE escaping
  `r["status"] = ...` in a second function → **`False`**; correct one → `True`. The universal
  ("every reachable write is protected") form. This is the pattern F12 needs.
* `_halt_is_not_breakage` against the run-#37 dead-code defeat (call, `continue` and string in
  an `if False:` after a `break`) → **`False`**. The `_live_walk` conversion held; only the
  first-match-wins loop (F13) is still open.
* `mutation_never_touches_the_live_tree` (drill.py:4679-4772) — the four-part write-rooting
  check reads correctly and fails CLOSED when the write sites are more than one delegation deep
  (`wrote` stays False → `return False`). Not defeated.
* `the_keeper_asks_before_restarting` (drill.py:4029-4076) — binds the answer, requires a
  reachable guarded `continue`, and requires every reachable `start` to be outside and after it.
  A `start` before the guard makes it refuse. Sound.
* `_no_runtime_clear` (drill.py:1571-1605) — drives four real spellings against the real
  `clear()` and requires `PermissionError`. Behavioural; sound.
* `_a_scan_can_tell_code_from_prose_about_code` (drill.py:4396-4432) — drives the rewritten
  scan over a scratch tree in five shapes. Sound.
* `_the_scanner_reads_files_over_two_megabytes`, `_an_unreadable_staged_file_is_a_hit`,
  `_scanner_finds_a_planted_secret`, `_publish_never_swallows_a_missing_safety` — all
  behavioural or AST-with-a-count; sound.
* `_policy_corpus_clean` (drill.py:3055-3088) — uncapped, and an unparseable record fails the
  net rather than being skipped. Sound.
* `_chain_done_key_follows_the_disk`, `_write_phase_stays_open_when_everything_refuses`,
  `_a_denied_batch_write_stays_on_the_failed_list`, `_the_pointer_stops_at_the_open_phase`,
  `_a_done_marker_cannot_accumulate`, `_the_catalogue_cannot_erase_what_it_did_not_author` —
  all driven against the real `pipeline` phases with the disk stood in for. Sound, and the
  strongest area in the file.
* `_a_reap_never_takes_a_live_runs_sandbox`, `abandoned_sandboxes_are_reaped`,
  `run_actually_holds_the_lock`, `_a_canonical_snapshot_refuses_when_it_cannot_verify_itself` —
  real processes, real directories, both directions. Sound.
* `_quarantine_reports_the_disk_not_the_intention` (drill.py:3243-3320) — the run-#37 fix that
  removed the `_land` stub in favour of an unwritable target is correct and is now pinned to the
  PROPERTY rather than to a helper. Sound, and the right model for F6(b).
* `blast_cap_bites` (drill.py:1475-1556) — the rewritten probe genuinely drives the charge path
  (`apply=True`, a find string occurring once, both bounds to zero) and reads the file back.
  Sound. Only its neighbour at 1560 (F10) is weak.
* `_twins_ignores_a_foreign_tree`, `twin_detection_does_not_match_bystanders`,
  `restarts_are_budgeted` — deterministic, no dependence on the live process table. Sound.
* `paid_access_stays_switched_off` (drill.py:3882-3891) — the literal
  `r"C:\\Users\\imarl\\cascade\\config.json"` LOOKS like an eaten-escape bug (a raw string with
  doubled separators). **It is not.** Verified: `os.path.exists` is `True` and `open()` succeeds
  on that exact literal — Windows collapses repeated separators after the drive. The net reads
  the real config and the `except: return True` arm is not being taken on this machine. No
  finding. (Worth a comment in the source so the next sweep does not re-flag it.)
* `_step4_needs_its_plan`, `_gates_agree`, `_drill_never_writes_the_gate` — the run #31/#34
  fixes hold; nothing in this file opens `config.yaml` or `STEP4_PLAN.md` for writing.
* `LIVENESS_CEILING = 41` — the raise from 38 is documented as a detector sharpening, not a
  green-washing, and `liveness_sees_its_own_founding_example` pins the case by NAME so the count
  cannot re-lose it. Correct discipline; left alone.

---

## SUMMARY

| severity | count | ids |
|---|---|---|
| MAJOR | 16 | F1-F14 (F14 upgraded), F16, F17, F18 |
| MINOR | 3 | F15, F19, and the F13 second-branch note where a tree has only one branch |

Eleven nets were **proved vacuous with a fixture that does the forbidden thing**: F1, F2, F3,
F4, F5, F6a, F7, F8, F9, F10, F11 (two nets), F12, F13, F14, F16. Two nets (F6b, F15) **fail
against correct code** because they are pinned to an import alias rather than to the module —
the same class as order `8ee268ce32cc`, and each is one breach away from halting the library
over a rename.

The single mechanical fix that closes F2, F3, F4, F5 is to give `_calls` a `reachable=` argument
and a scope, and to point each of the four at the function that actually does the work — the
`_calls_within(tree, defn, want, reachable=True)` form `daemons_actually_check_their_own_source`
already uses. F6a, F7, F8, F15 are the same conversion one level down. F1, F9, F12, F14 need the
universal form `resync_cannot_revert_an_exclusion` already demonstrates.

Nothing in this batch was edited. `python src/drill.py` was NOT run end to end (the
`_suppressed_still_visible` net scans the whole repo root); every finding was reproduced by
importing `drill` and calling the individual net function, which is how each verdict above was
obtained.

---

## WORK ORDERS FILED (found_by `sweep37-batch02`)

| order id | code | severity | findings |
|---|---|---|---|
| 8f4bb64503c2 | DRILL_NET_VACUOUS_LOCAL_PREFIX | MAJOR | F1 |
| 78f04bec15ad | DRILL_CALLS_IS_NOT_REACHABILITY | MAJOR | F2, F3, F4, F5 |
| 7cc460706efe | DRILL_NET_PINNED_TO_IMPORT_ALIAS | MAJOR | F6b, F15 |
| c54a22a4e6fc | DRILL_LOCAL_AGENT_NETS_WALK_DEAD_CODE | MAJOR | F6a, F7, F8 |
| 18958aba2143 | DRILL_REFUSAL_NET_UNSCOPED | MAJOR | F9 |
| 9ada7602a356 | DRILL_BLAST_RESET_NET_HALF_BLIND | MAJOR | F10 |
| 64dfe6bec15c | DRILL_CASCADE_NETS_ARE_TEXT_SCANS | MAJOR | F11 |
| 5ed81099fc49 | DRILL_NET_EXISTENTIAL_NOT_UNIVERSAL | MAJOR | F12, F14 |
| e2f44baedfdc | DRILL_HALT_NET_FIRST_MATCH_ONLY | MAJOR | F13 |
| cf9ee9000be8 | DRILL_SRC_SCANS_SKIP_SUBDIRECTORIES | MAJOR | F16 |
| 5eea5c20db8a | DRILL_DATASETTE_NET_WRITES_AND_CAN_FALSE_HALT | MAJOR | F17 |
| 5c87268a388c | DRILL_SETUP_OUTSIDE_NET_ABORTS_THE_BATTERY | MAJOR | F18 |
| 64c8827cc72b | DRILL_SNAPSHOT_CLEANUP_RACES_A_CONCURRENT_BACKUP | MINOR | F19 |

The filing script is `handoff/sweep37/file_batch02_orders.py` (run once, 2026-08-28).
Coverage recorded: `sweep_plan.record('run37', ['drill.py'], batch=2)` -> `drill.py` now stamped
`run37`.

NO SOURCE FILE WAS EDITED by this batch. `prose_enabled` and `step4_enabled` were not touched.
No halt was raised or cleared. `mutate.py`, the supervisors and the crawlers were not run.
