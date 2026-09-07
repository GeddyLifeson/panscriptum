# run46 / batch 01 — src/drill.py

**Module:** `src/drill.py` — 13,588 lines, read end to end (no sampling, no skipping).
**Method:** every finding judged on the EXECUTABLE line. Where a docstring or comment quotes a
defect (`or True` at :6132, `hasattr(...)` at :6310), the quoted text was checked against the live
code before being dismissed — both are prose recording a removed fault, not live faults. Every
line number cited below was re-read off the live file before it was written down.
**Constraint honoured:** nothing in `src/` was edited. `drill.py`, `mutate.py`, `allsweep.py` and
`publish.py` were not run. The live ledgers were read, never written.

**Orders filed:** 7 — `dad7b19b2136`, `2eabb417f58f`, `d015e0a139a8`, `749597eb95d4`,
`036d9ca295ad`, `0c7592915a48`, `93e73e0c59a6`.

---

## 1. Nets that cannot fail

### F1 (MAJOR) — `drill_codex_dedupe_is_typed` tests nothing its name claims

`src/drill.py:11667`, in `drill_recorders_and_lane`. Net name: *"two element types sharing a name
are two elements"*. Expectation: *"a Dragonmark and a Race Variant of the same name must not
collapse to one catalogue entry"*.

```
contents = [("Race", "Troglodyte"), ("Language", "Troglodyte"),
            ("Companion", "Mastiff"), ("Item", "Mastiff")]
seen = set()
for et, nm in contents:
    seen.add((_CC.norm(et), _CC.norm(nm)))
return len(seen) == 4
```

The net builds `seen` **itself**, out of a tuple list it wrote, folding it with its **own
reconstruction** of the pairing key. The only thing it takes from `catalogue_codex` is `norm`,
and `norm` was never the defect.

The real dedupe is `src/catalogue_codex.py:246-284`; the key is built at `:272`:

```
key = norm(name)
...
pair = (norm(etype), key)
if pair in seen: ... dupe_elements ... continue
seen.add(pair)
```

Revert `:272` to the pre-fix `pair = key` — the exact regression order `f4f3c1d15915` was filed
for, 88 dropped elements across 8 sections, Race *Troglodyte* kept while Language *Troglodyte*
vanished — and **this net stays green**, because `catalogue()`'s loop is never entered.

What the net *can* fail on is `norm` collapsing four distinct string literals to fewer than four.
That is not the guard its name and expectation describe.

Same class as `feat_bearing_path_unchanged` (order `a5de2dcb9447`), which this same file records
having renamed for promising more than its code delivered — except that one at least drove the
module under test.

Filed **`2eabb417f58f`** — SESSION, because the dedupe lives inside `catalogue()`'s per-section
loop and is not separately callable. Either factor the pairing into a named helper, or drive
`catalogue()` against a fixture manifest and assert four entries with the right categories and an
empty `dupe_elements`. Choosing between those is a judgement about how much of `catalogue()` is
worth making testable, not a mechanical edit.

### Checked and cleared

Suspicious on first read; **not** findings, verified against source:

* `_refusal_is_recorded` `:6132` `... or True` — inside the docstring, quoting the removed defect.
* `_throttle_hands_off` `:6310` `THROTTLE_STRIKES >= 1 and hasattr(...)` — likewise docstring.
* `_drill_never_writes_the_gate` — calls `_gates_agree()` for real; deleting `_gates_agree` breaks it.
* `the_covering_guarantee_holds_and_says_what_bought_it` — `covered_before_widening` is asserted in
  both directions, so the pair is a guarantee plus a datum, not two rubber stamps.
* `index_admits_when_it_is_behind` — the unfailable second assertion was already deleted
  (order `9e2fe6e222d9`); the surviving line can evaluate False.
* `_a_scan_can_tell_code_from_prose_about_code` — drives all seven call spellings for real.
* `the_reachability_primitive_understands_loop_else` — asserts both loop directions and would go
  red if `_live_walk` regressed either way.

---

## 2. Probe litter

### F2 (MAJOR) — the eleventh site: `abandoned_sandboxes_are_reaped`

`src/drill.py:11897`. The call at `:11974` is bare:

```
back = time.time() - (M.ORPHAN_AGE_SECONDS + 3600)
os.utime(aged, (back, back))
removed = M.reap_orphans()
```

The `fresh` fixture is deliberately claimed by `os.getpid()` — a **live** owner, and the net's own
docstring says so ("the fresh one by THIS process"). `mutate.reap_orphans` therefore takes the
live-owner branch at `src/mutate.py:1230-1233`:

```
owner = _owner_pid(p)
if owner is not None and _pid_alive(owner):
    silence.note("mutate.py:reap-skipped-live-owner")
    continue
```

`silence.note` (`src/silence.py:815-818`) resolves `health` out of `sys.modules` at call time and
calls `health.record`, so this writes `silent:mutate.py:reap-skipped-live-owner` into the LIVE
`state/failures.json`, once per drill run. Nothing wraps it.

**Corroborated by measurement, not by reading alone.** That key stands at **79** in the live
ledger. Eight keys retired today all stand at **39**, the drill-run count. Its sibling
`_a_reap_never_takes_a_live_runs_sandbox` drives the *same* branch with the *same* fixture shape
and names the *same* key in its own comment —

> the one signal that would settle it, `mutate.py:reap-skipped-live-owner`, is suppressed during
> this call by the `_deliberately_failing` wrapper added the same day

— and that one **is** wrapped. Two nets emitting one row each per run for 39 runs is 78; the
ledger says 79. Exactly one of the two was wrapped.

This is not cosmetic. `reap-skipped-live-owner` is the row a person reads to answer the question
order `f0a7…` leaves explicitly unproven — whether a drill run reaped somebody's live mutation
sandbox — and 39 of its occurrences are this rehearsal.

Filed **`dad7b19b2136`** — RUN, one wrapper around one call. Not LOCAL: `drill` is on
`local_agent.DENYLIST` (`src/local_agent.py:90`), so the free local model cannot patch this file
at all. Not to be applied while a mutation pass is live.

### F3 (MINOR) — two nets leak a temp directory each, per run

`safety_distinguishes_unreadable_drill` (`src/drill.py:12984`) and
`safety_distinguishes_unreadable_escalation` (`src/drill.py:13010`), both landed 2026-09-06.

```
d = tempfile.mkdtemp()
...
finally:
    DB.HERE = orig_here          # <- and nothing else
```

No `shutil.rmtree`. Two directories per drill run accumulate in the system temp directory,
permanently; they carry no `mutate.SANDBOX_PREFIX` so nothing reaps them. Every other
scratch-directory net in this file removes its root, and `abandoned_sandboxes_are_reaped` states
the rule in as many words: *"a net that leaves litter in TEMP is a net that reproduces the fault
it is testing for"*.

Filed **`d015e0a139a8`** (RUN). Remedy: `shutil.rmtree(d, ignore_errors=True)` in both `finally`
blocks — `ignore_errors=True` rather than a graded removal, per order `f5f01fe5f8ef`: a probe that
could not tidy up must not become a breach, because `main()` escalates a breached net to OWNER.

### F4 (MINOR) — a swallowed cleanup on a probe file that PUBLISHES

`an_empty_find_is_not_a_location`, `src/drill.py:3361`. It creates
`handoff/__drill_empty_find__.txt` and ends at `:3395-3398`:

```
finally:
    try:
        os.remove(full)
    except OSError:
        pass
```

`handoff` is in `publish.COPY_DIRS` (`src/publish.py:151`) and `publish._is_agent_scratch`
(`src/publish.py:209-215`) refuses only `.py`, `.pyw`, `.pyi` — a `.txt` is copied. So a denied
removal publishes a drill probe file to the PUBLIC repo on the next cycle with nothing anywhere
recording why.

That is verbatim the argument order `5442da43c9f8` made about `blast_cap_bites`' own
`handoff/__drill_blast_probe__.md` twenty lines up, which now records the failure with
`silence.note("drill.py:blast-probe-cleanup")`. Two probes, one directory, one consequence, two
different disciplines.

Filed **`749597eb95d4`** (RUN).

### Checked and cleared

* Every one of the sites fixed today is genuinely wrapped, and each wraps **only** the failing
  call. Verified individually: `_a_refused_landing_reports_that_it_was_refused` arms 1 and 2,
  `reason_matches_verdict`, `refused()` in `drill_stale_writer`,
  `the_loser_of_a_race_is_refused_mid_backoff`, `_a_broken_maintenance_guard_fails_open`,
  `an_acknowledged_shrink_is_carried_and_nothing_else_is` case (5),
  `an_unparseable_chain_line_fails_the_chain`, `the_floor_never_rises_to_go_green`,
  `a_denied_ledger_write_refuses_the_restart`, `_the_log_roll_off_archives_before_it_trims`
  (both sweeps — including the second one, which the comment records as the call that actually
  leaked), `_a_reap_never_takes_a_live_runs_sandbox`, `blast_cap_bites`,
  `denied_write_leaves_phase_open`, `a_control_too_thin_to_be_one_is_not_a_baseline`,
  `a_misaddressed_blob_is_refused`, `a_competing_flush_cannot_clobber_the_recorder`,
  `an_owner_queue_denial_is_reported_as_a_denial`, `history_heals_nonnumeric_at`,
  `safety_distinguishes_unreadable_*`, `sweep_plan_freeze_plan_refuses_a_broken_existing_file`,
  and both `wiki_source_*` nets.
* `silent:publish.py:agent-scratch-refused` (40) is **not** drill litter — the note is emitted from
  `sync_tree` at `src/publish.py:1086`, on real publish cycles. The drill calls only the pure
  predicate `_is_agent_scratch`.
* `paid_access_stays_switched_off` notes only when `PANSCRIPTUM_CASCADE_CONFIG` (default
  `~/cascade/config.json`) is absent or unreadable. It is present on this machine (30,161 bytes,
  2026-08-26), so no row is written, and none appears in the ledger.
* Work-order litter: `_sweep_probe_litter` (`:305`) and `area_fault_does_not_close_the_park`
  (`:2111`) both resolve with `where="__drill*__"`, which `workorders.SELFTEST_SUBJECT`
  (`^__drill[A-Za-z0-9_]*__$`, `src/workorders.py:81`) routes to `workorders_selftest.jsonl`.
  `blast_cap_bites` passes no `where` and therefore passes `synthetic=True` explicitly. Both
  correct — `a_probe_leaves_no_order_behind` would be red otherwise, and its assertion on
  `_rows_in(WO.CLOSED_LOG)` is what keeps them correct.

---

## 3. Blast radius — questions, not findings

These four touch real shared state. Each is documented and each has a defensible reading, so they
are recorded as questions rather than filed.

**Q1. `area_fault_does_not_close_the_park` (`src/drill.py:2111`) escalates for real.**
`ESC.escalate(ESC.SUPERVISOR, "DRILL_AREA", ..., source="__drill__")` runs against the live
`escalation.py` module constants, so it appends one row to `state/escalation.log` and one to
`state/escalations/__drill__.log` on every drill run, forever, besides filing and resolving a real
order.
*Reading A:* the net's claim is "a SOURCE-level fault does NOT change the PARK's halt state", and
under `_esc_sandbox` (`:7987`) the before/after `status()` would be about a scratch halt file, so
the question would stop being about the real park.
*Reading B:* the same `escalate` call is already driven inside `_esc_sandbox` by
`the_escalations_source_travels_to_the_failure_ledger`, and the per-source log growth is exactly
the permanent decoration `_sweep_probe_litter` exists to prevent one rung over.
I lean B; it is not a drill's place to decide it.

**Q2. `_sandbox_without_its_target_refuses` (`src/drill.py:5947`) tears down a real mutate sandbox
with a bare `shutil.rmtree`.** It monkeypatches `shutil.copy2` and `tempfile.mkdtemp`
process-globally, calls the real `M.sandbox()`, and cleans up with
`shutil.rmtree(r, ignore_errors=True)` — without the junction-unlink-first discipline
`src/mutate.py:1234-1245` names as *"the one place in the project where getting that wrong would
delete `data/` — 1.1 GB of mined corpus"*.
**It is safe today, and I verified why:** `sandbox()` creates the four junctions at
`src/mutate.py:1421-1424`, **after** the `absent` check this net forces, so the tree the drill
rmtree's has never held a junction. The safety is a property of the order of statements in a
different module. Nothing states that dependency and nothing checks it.

**Q3. Two probes write into the live tree.** `_junction_out_of_the_writable_surface`
(`src/drill.py:2811`) creates a real NTFS junction at `src/__drill_junction_probe__` — inside
`publish.COPY_DIRS`' `src` — and `cannot_edit_shared_run_state` (`src/drill.py:3132`) writes
`state/__drill_state_probe__.json`. Both note a failed cleanup rather than swallowing it, and both
argue that the filesystem has to be involved because the whole point is that the string and the
filesystem disagree. Recorded because they are the only two live-tree writers left in the file.

**Q4. `a_probe_leaves_the_failure_LEDGER_alone` (`src/drill.py:11283`) calls `health.flush()`
twice against the LIVE ledger** to get a stable before/after. That is what makes the byte
comparison meaningful; it is also a drill net writing `state/failures.json`. Deliberate, and worth
knowing.

---

## 4. Correctness, dead code, stale docstrings, drifted citations

### F5 (MINOR) — `_no_runtime_clear`'s docstring is now false

`src/drill.py:3450`:

> This is the one place in drill.py that calls `clear`, which is why `verify_math`'s AST check
> exempts this file by name.

Fifteen live call sites: `:2147`, `:2150`, `:3470`, `:3471` (twice — via the import alias and the
from-import), `:8505`, `:8511`, `:8512`, `:8995`, `:9007`, `:9055`, `:9077`, `:9090`, `:9192`,
`:9348`, plus three `exec`-compiled sources at `:2458`, `:8952`, `:9298`. `drill_park`'s two
`ValueError` nets are accounted for by this same docstring two paragraphs down; the twelve in
`drill_escalation_behaviour` are not, and that area landed after the paragraph was written.

The sentence reads as an enforceable property ("only here") and is not one — the same shape as
the `LIVENESS_CEILING` measurement-in-prose that orders `b99192e41488` and `f5549e17b43a` were
filed against, in the file that removed it.

Filed **`036d9ca295ad`** (RUN). Remedy: say what is true and checkable — drill.py is exempted from
`verify_math`'s programmatic-clear scan by name because it calls `clear` deliberately, in several
places, to prove each spelling is refused — and drop the count.

### F6 (MINOR) — roughly two-thirds of the external line citations have drifted

drill.py cites line numbers in other modules in 22 places. All 22 checked line by line on
2026-09-07.

**Accurate (6):** `liveness.py:12`, `coverage.py:53`, `feats.py:159`, `anchors.py:427`,
`withdraw_chapters.py:216-219`, `publish.py:205-214` (off by four — `_is_agent_scratch` is 209-215).

**Drifted (16):**

| citation | claimed to be | actually |
|---|---|---|
| `local_agent.py:849` | `out["ALARM"]` is set | a comment about the writable surface |
| `local_agent.py:868` | the SAFETY escalation | `_real_here = os.path.realpath(HERE)` |
| `local_agent.py:163` | `_BLAST` | a comment about gate bypasses |
| `local_agent.py:182-184` | `blast_reset` | a comment about gate bypasses |
| `dashboard.py:607` | reads `drill_last.json` | `v = sorted(v)` |
| `pipeline.py:988` | a comment naming cachekey | a comment about done-keys |
| `pipeline.py:2647` | states the P8 ban is enforced | `marks, m_bad = _phase_input(...)` |
| `feats.py:1370-1374` | a comment block naming cachekey | a comment about statblock gates |
| `cascade_bridge.py:317` | the `cloud_buckets` de-dup `if` | prose |
| `cascade_bridge.py:1060` | a COMMENT naming `LOCAL_PREFIX` | live code, `if _deep and not any(...)` |
| `cascade_bridge.py:1334-1336` | the router's local-bucket skip | a comment about timeouts |
| `cascade_bridge.py:1621-1622` | the four-hour bench branch | a comment about folded text |
| `scout.py:616` | `r["kept"] and r.get("registered") is True` | a comment |
| `assay.py:1392` | the `<=` -> `>` mutant | prose about Galactus |
| `escalation.py:601`, `:602` | the two fail-open mutants | comments |
| `escalation.py:939`, `:966`, `:984` | three named lines in `clear()` | comments / unrelated code |
| `corpus_db.py:597-610` | names the denied-replace case | a comment about `--rebuild` |
| `workorders.py:1086-1098` | grades the battery from `drill_last.json` | `for oid, o in list(_load().items()):` |

These citations are the evidence a reader uses to check that a net's story is true, and a wrong
one sends them to a line that argues against the paragraph citing it. The project has already
ruled on the shape twice: `mutate.py`'s teardown comment records correcting a citation that
pointed at an unrelated `ast.Compare` branch, and drill.py itself retired the whole `rfind` offset
apparatus in `drill_does_not_halt_during_a_mutation_run` because offsets in a file are the wrong
instrument.

Filed **`0c7592915a48`** (RUN). Remedy: cite the SYMBOL, not the line. A symbol survives an edit
above it; a line number does not. Correcting the numbers in place buys one shift and re-rots.

### F7 (INFO) — two smaller accuracy items, filed together

* `custodes_table_faults_is_empty` (`src/drill.py:2052`) returns `CU.table_faults() == []`, a bare
  boolean — while its own docstring says a breach *"names the entry and the exact reason in
  `error` via the normal `net()` failure path once `attack()` is made to return the fault list on
  breach"*, and then offers the reader a second way of doing it. That is a docstring describing
  work that was not done, in a file whose subject is prose outliving code. A breach today prints
  the net's name and nothing about which CUSTODES entry is at fault. The house pattern is next
  door at `src/drill.py:7136`, `no_open_order_sits_on_a_legacy_cap_boundary`, which raises
  `AssertionError` carrying the offending ids precisely so `net()` records them in `error` and
  `main()` prints them under the breach.
* Two dead parameters: `the_validator_is_what_refuses_it` (`src/drill.py:4999`) and
  `_status_reports_i_do_not_know_as_itself` (`src/drill.py:5609`) both take `src=None` and neither
  body references it. Both are behaviour-driven nets for which the `_srcdir` override has no
  meaning — `_srcdir`'s own docstring explains the parameter exists so SOURCE-SHAPE nets can be
  pointed at a defeat fixture and watched go red, which neither of these can be. Checked by AST
  over every `def` in the file: every other `src=`/`tmp=` parameter is used.

Filed **`93e73e0c59a6`** (RUN, INFO).

### Checked and cleared

* `_live_stmts` / `_live_walk` loop-`else` handling is correct in both directions (`while False:`
  contributes its `else`; `while True:`'s `else` is skipped in `_live_walk`), and
  `the_reachability_primitive_understands_loop_else` drives both.
* `_arm_leaves`, `_gate_precedes_spawn`, `_carries_result_of`, `_is_rooted`, `_write_targets`,
  `_filtered_names`, `_rooted_names` all read correctly against the defeats their comments
  describe. `_is_rooted`'s separator test (`not any(c in recv.value for c in "/\\")`) does what it
  says: `",".join(root)` is text, `os.sep.join(...)` is a path build.
* `an_unreadable_stop_ledger_stops_everything` is defined twice — `:7967` (nested in
  `drill_rung_four`) and `:8581` (nested in `drill_escalation_behaviour`). Different scopes, no
  shadowing, and they attack different arms (a scratch `STOPPED` path vs. the sandboxed
  wrong-shape read). Not a fault.
* `main()`'s area list contains all 39 `drill_*` area functions defined in the file; none is
  orphaned. Checked by name against every `def drill_*`.
* `main()`'s per-area `try/except` (order `5c87268a388c`) genuinely covers the call-time
  statements in `drill_snapshot`, `drill_two_writer` and `drill_stale_writer`.
* `drill_scope_refuses_an_unread_host` restores `F.fetch`, which it never changed. Harmless.
* `_esc_sandbox` restores `workorders.file_order` and `health.record` on every path, including the
  two nets that call it directly rather than through `_esc_probe`
  (`a_halt_that_loses_the_race_is_kept_as_corroboration`,
  `the_destructive_tool_asks_before_it_moves_anything`) — both have `finally: restore()`.
* `_deliberately_failing` stubs `health.record` only; `silence.note`'s `health.flush()` still runs,
  which adds nothing because `record` added nothing. Correct.

---

## Coverage

`src/drill.py`, lines 1-13,588, read in full. Recorded to `sweep_plan` under run46, batch 1.
