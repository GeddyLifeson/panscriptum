# SWEEP 56 — BATCH 01 AUDIT

Run: `run56`, batch 1.
Module in scope: `src/drill.py` — **17,711 lines, read in full, top to bottom, in nine
successive chunks. No sampling, no skipping.**

Method: whole-file read, then targeted verification of every claim I intended to file against
the actual source of the cited module (`feats.py`, `anchors.py`, `codewatch.py`,
`withdraw_chapters.py`, `escalation.py`, `workorders.py`, `ingest_doc.py`, `cascade_bridge.py`,
`overnight.py`, `binding_health.py`, `resync_roll.py`, `manifest_builder.py`, `coverage.py`,
`generate.py`, `liveness.py`, `standards.py`, `address_space.py`, `publish.py`) and, where a
claim was measurable, against live state on disk. Nothing was written to the library. `pyflakes`
was run read-only over `src/drill.py` and is CLEAN.

Two candidate findings were **dropped after measurement** rather than filed — they are recorded
at the end under DISPROVED, because a finding I nearly filed and could not sustain is worth as
much to the next run as one I did.

---

## DEFECTS

### D1 — DEFECT. `_the_report_says_how_long_ago_each_job_ASKED` grades its own cleanup of a LIVE state file, and swallows the failure with no record

`src/drill.py:13033-13048`

```python
        probe = "__drill_poll_probe__"
        try:
            if _CW.last_polled(probe) is not None:
                return False              # a name nothing has stamped must read as not known
            _CW._stamp_poll(probe)
            age = _CW.last_polled(probe)
            if age is None or age > 60:
                return False              # a fresh stamp must read back as fresh
        finally:
            try:
                os.remove(os.path.join(_CW.POLLS, probe + ".json"))
            except OSError:
                pass
        if _CW.last_polled(probe) is not None:
            return False                  # and removing it must go back to "not known"
```

Verified: `codewatch.POLLS = os.path.join(HERE, "state", "codewatch_poll")` (`codewatch.py:96`)
— the LIVE state directory, currently holding six real job stamps
(`dashboard/foreman/overnight/overwatch/pipeline/publish.json`). `_stamp_poll` writes
`<POLLS>/__drill_poll_probe__.json` there for real.

Three things are wrong, and they compound:

1. **The cleanup outcome IS the verdict.** A denied `os.remove` — an antivirus scanner holding
   the file for a moment is enough on this machine, which this file says in as many words
   elsewhere — leaves the stamp on disk, so the final `if _CW.last_polled(probe) is not None:
   return False` fires. `net()` records False as `held=False` and `main()` escalates a breached
   net to OWNER. **A probe that could not tidy up halts the library.**
2. **It LATCHES.** The leftover `__drill_poll_probe__.json` also fails the FIRST assertion on
   every subsequent run (`last_polled(probe) is not None → return False`). Once the removal
   fails, this net is permanently red — and raises a permanent OWNER halt every cycle — until a
   person deletes a file nothing points them at.
3. **The failure is recorded nowhere.** `except OSError: pass`. Every other probe cleanup in
   this file notes: `drill.py:state-probe-cleanup` (4114-4116), `drill.py:blast-probe-cleanup`
   (4201-4203), `drill.py:unlisted-probe-cleanup` (4300-4302),
   `drill.py:empty-find-probe-cleanup` (4350-4352), `drill.py:junction-probe-cleanup` (3717-3718),
   `drill.py:surface-probe-cleanup` (3796-3803). This one does not.

**Why it matters:** this is verbatim the shape order `f5f01fe5f8ef` removed from
`_junction_out_of_the_writable_surface`, whose own comment (`drill.py:3748-3757`) reads: *"This
used to end `and not os.path.exists(link)`, which graded the net's OWN litter: a denied
`os.rmdir` … turned a held net into a breached one, and `main()` escalates a breached net to
OWNER. A full stop caused by a probe that could not tidy up is precisely the failure order
`ef0b67732a3b` already records this net causing once."* The ruling exists, is written down 9,000
lines above, and this net does not follow it.

Measured today: `state/codewatch_poll/` holds no `__drill_poll_probe__.json`, so the removal is
succeeding at present. This is latent, not live.

Confidence: **DEFECT.**

---

### D2 — DEFECT. `the_destructive_tool_asks_before_it_moves_anything` drives `withdraw_chapters --go` against the LIVE tree with no second line of defence

`src/drill.py:10414-10446`

```python
        import withdraw_chapters as WC
        d, filed, restore = _esc_sandbox()
        argv = sys.argv
        try:
            ESC.silence.write_json(ESC.HALT_FILE, { ... "code": "DRILL_SYNTHETIC_HALT" ... })
            sys.argv = ["withdraw_chapters.py", "--go"]
            return _refuses(WC.main, ESC.SystemHalted)
        finally:
            sys.argv = argv
            restore()
```

`_esc_sandbox()` redirects `escalation`'s four paths only. `withdraw_chapters` reads its own
module globals (`withdraw_chapters.py:42-43`):

```python
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(HERE, "output", "index", "catalog.json")
```

Neither is redirected. The ONLY thing standing between this net and a real `--go` withdrawal is
`_ESC.assert_clear(...)` inside `WC.main()` — **which is the exact guard this net exists to
test.** On the day the guard is broken, i.e. the day the net earns its keep, the net itself
`shutil.move`s every catalogued chapter out of `output/raw` into `output/withdrawn_<today>`
(a MOVE, so the archive becomes the only copy) and rewrites `output/index/catalog.json`.

`_reread_the_breaches` (`drill.py:17280-17292`) then re-runs the breached attack — so the
destructive run happens **twice**.

This is the class this same file was repaired out of twice, both times with the reasoning
written out:
* order `9495caa65d06` — `_no_runtime_clear` "called the REAL `clear()` four times against the
  LIVE `state/HALT.json`, and the only thing between it and lifting a standing halt was the very
  guard it exists to test" (`drill.py:4373-4393`);
* sweep55 batch 01 on `a_resume_is_refused_to_a_program` — "the mutant this net exists to catch
  is PRECISELY the one that does not raise, so on the day the net earns its keep it would walk
  on into the write path against a real name" (`drill.py:9665-9681`).

The safe pattern already exists in this file for this very module: the sibling net
`withdraw_dry_run_does_not_count_catalogued_chapters_as_strays` (`drill.py:14635-14696`)
redirects `WC.HERE` and `WC.CATALOG` to a scratch tree. The two other halt-interlock nets in the
same area also carry a second line of defence —
`the_tool_that_deletes_mined_evidence_asks_about_the_halt` stubs `HC._land`, `HC._land_hosts`,
`HC.entities_by_source`, `HC.ROSTERS` and `WI.load_records` (`drill.py:10478-10483`) and says so.
This one is the odd member of a set of three.

**Blast radius measured today: zero.** `output/raw` holds 0 files and
`output/index/catalog.json` holds 0 entries (prose gate closed). That is a property of today's
corpus, not of the net; it becomes real the moment the prose gate opens.

Confidence: **DEFECT** (latent).

---

### D3 — DEFECT. `_esc_sandbox` stops two side effects and names two; `workorders.resolve_code` is a third, and it reaches the live queue

`src/drill.py:9943-9989` (the sandbox), `10640-10652` and `10873-10884` (the two probes that
reach it).

`_esc_sandbox`'s docstring enumerates what it stops:

> "AND THE TWO SIDE EFFECTS ARE STOPPED AS WELL … `escalate()` calls `health.record` and
> `workorders.file_order` through a late `import`, so both resolve out of `sys.modules` at call
> time and both write real files"

and the code replaces exactly `_WO.file_order` and `_H.record`. It does **not** replace
`_WO.resolve_code`. Verified in `escalation.py` that two sanctioned paths call it:

* `escalation.py:771` — `stop_subsystem`'s post-write recheck, reached when `landed` is False and
  the ledger positively reports the name NOT stopped;
* `escalation.py:1065` — `resume_subsystem`'s successful path, unconditionally.

Two nets in `drill_escalation_behaviour` reach them:

* `a_resume_lifts_the_stop_and_leaves_the_others_standing` (`drill.py:10640-10652`) stops
  `sub-a`/`sub-b` and successfully resumes `sub-a`. (Inside the sandbox `ESC.STOPPED !=
  ESC._REAL_STOPPED`, so `_a_probe_release` returns True for any name by its own condition (1) —
  the file states this at `drill.py:9617-9621` — so the resume is admitted and reaches
  `escalation.py:1065`.) → real `WO.resolve_code("SUBSYSTEM_STOPPED", …, where="sub-a")`.
* `a_stop_whose_temp_copy_failed_is_not_recorded` (`drill.py:10873-10884`) makes
  `_write_stopped` raise. `_read_stopped` is real and the scratch `STOPPED.json` is absent, which
  `escalation._read_stopped` answers `{}` for (verified), so `subsystem_stopped("probe-sub")`
  returns `(False, "")`, `_still_stopped` is False, and `escalation.py:771` fires. → real
  `WO.resolve_code("SUBSYSTEM_STOPPED", …, where="probe-sub")`.

`workorders.resolve_code` → `resolve` → `_mutate`, and `_mutate` **unconditionally** writes a
temp file and compare-and-swaps it over `state/workorders.json` whether or not `change` found
anything (`workorders.py`, `_mutate`). So each drill run performs two live CAS rewrites of the
shared work-order queue from inside a sandbox whose stated contract is that its writes land in a
list.

The file already knows this exact hazard and stubbed it — for ONE net only.
`a_stop_that_was_never_recorded_closes_only_a_FALSE_order` (`drill.py:10938-10941`):

> "`workorders.resolve_code` is stood in for and its calls collected. **It is not one of the two
> side effects `_esc_sandbox` already stops (`file_order` and `health.record`), so without the
> stand-in this probe would reach the real queue** — and reaching the real queue to close orders
> is the one thing a net about closing orders wrongly must not do."

Two siblings drive the identical branch without it.

**Measured severity, honestly:** `resolve()` returns before touching the paper trail when the
order does not exist, and there is no open order keyed `(SUBSYSTEM_STOPPED, "sub-a")` or
`(SUBSYSTEM_STOPPED, "probe-sub")`. I counted `state/workorders_closed.jsonl` and
`state/workorders_selftest.jsonl`: **zero** rows for either name in either file. So this is not
paper-trail litter today. What it is: (a) two unnecessary CAS rewrites of the highest-contention
shared file in the kit per drill run; (b) a probe that would genuinely close a real order the
day one of those two names is ever used, and neither name carries a reserved `__drill…__`
marker, so `health.is_selftest` would NOT recognise the closure as synthetic and the row would go
to `CLOSED_LOG` — the permanent trail `a_probe_leaves_no_order_behind` exists to protect;
(c) if `_mutate` hits `QueueUnreadable` it calls `silence.note("workorders.py:queue-unreadable")`
→ `health.record`, which inside `_esc_sandbox` is captured by the sandbox stub and is therefore
**invisible to THE LEDGER WITNESS**.

Confidence: **DEFECT** (the hazard is named in the file; the fix was applied to one of three
sites).

---

### D4 — DEFECT. Stale line citation: `feats.py:159`

`src/drill.py:8077`, in `_backoff_stops_at_its_ceiling`:

> "the clamp it is named after is `feats.py:159`,
> `min(BACKOFF_MAX, _BACKOFF.get(host, 1.0) * BACKOFF_GROWTH)`, and deleting the `min(...)`
> leaves the constant exactly as it was."

Verified: `feats.py:159` is `    h = h.split("/")[0].split(":")[0].rstrip(".")` — part of host
normalisation, nothing to do with backoff. The real clamp is **`feats.py:238`**:

```
238:        _BACKOFF[host] = min(BACKOFF_MAX, _BACKOFF.get(host, 1.0) * BACKOFF_GROWTH)
```

A drift of 79 lines. Order `0c7592915a48`'s rule (cite by symbol, not by line) is applied
throughout this file and was not applied here. Confidence: **DEFECT.**

---

### D5 — DEFECT. Stale line citation: `anchors.py:427` (twice)

`src/drill.py:11908` and `src/drill.py:11929`, in
`a_ladder_rung_with_no_instrument_window_refuses_to_load`:

> "Worse, anchors.py:427 indexes INSTRUMENT_WINDOWS[b] for every b in LADDER with no guard, so
> the same divergence arrives as a KeyError raised from inside production code."
>
> "…is an unguarded KeyError out of anchors.py:427"

Verified: `anchors.py:427` is
`                    "%r is named by this check and absent from ANCHORS, so the claim could not "`
— a verdict string in an unrelated check. The only `INSTRUMENT_WINDOWS[b]` indexing in
`anchors.py` is at **546** (`collapsed = [b for b in A.LADDER if A.INSTRUMENT_WINDOWS[b][0] ==
A.INSTRUMENT_WINDOWS[b][1]]`) and **551**.

This citation is load-bearing: it is the evidence for *why* the net is worth having, and it
appears in the net's printed expectation, which is what a person reads under a breach.
Confidence: **DEFECT.**

*(Checked and CORRECT, for the record, so the next run need not re-check them:
`anchors.py:37-40`, `generate.py:552`, `liveness.py:12`, `withdraw_chapters.py:216-219`,
`coverage.py:53`, `foreman.py:115`, and the seven `escalation.py` `_halt_lock` survivor lines
`416/419/421/428/438/444/447` — every one of those resolves exactly as claimed.)*

---

### D6 — DEFECT. `the_document_ingester_asks_about_the_halt` claims a second line of defence that does not exist

`src/drill.py:10526-10529`:

> "THE SECOND LINE OF DEFENCE IS THE SAME ONE THE NET ABOVE USES: with the gate removed, neither
> call can actually move anything, because HOSTS points into the temp tree and **the record
> writer is stubbed**."

The net body (`drill.py:10531-10567`) redirects `ESC.HALT_FILE` and `ID.HOSTS` and **nothing
else**. `pipeline.write_record_catalogue` is not stubbed, and neither is `ingest_doc.RECORDS` or
`ingest_doc.DOCS`.

What actually protects `ID.mine("__drill_source__")` is a different thing entirely: `mine()`
raises `ValueError("no corpus at …")` because `data/docs/__drill_source__/pages.json` does not
exist (`ingest_doc.py`, `mine()`), and `refuses()` in the net treats any non-`SystemHalted`
exception as a failure. So the protection is real but comes from the absent corpus, not from a
stub.

This is a comment asserting a completed action — the exact class this file nets in
`_a_module_claimed_wired_is_actually_imported` (`drill.py:13461-13495`): *"A comment asserting a
COMPLETED ACTION is load-bearing: the next reader takes it as settled and stops looking."* A
maintainer reading this docstring would believe the write path is stubbed and could safely delete
the corpus guard.

Confidence: **DEFECT** (documentation, not behaviour — the net is safe today).

---

### D7 — DEFECT. `_policy_corpus_clean` passes vacuously on an absent or empty `data/records/`

`src/drill.py:7663-7699`

```python
    root = root or os.path.join(HERE, "data", "records")
    bad, unreadable = 0, 0
    for p in sorted(glob.glob(os.path.join(root, "*.json"))):
        ...
    return bad == 0 and unreadable == 0
```

`glob.glob` on a missing directory returns `[]`. So a `data/records/` that has been deleted,
renamed, or is empty gives `bad == 0 and unreadable == 0` → **True**, and the net printed as
*"the live corpus passes its structural rules"* reports HELD over a corpus it never opened.

The docstring is at length about two other holes it closed — the `[:40]` cap and the
`except Exception: continue` swallow — and ends: *"it now fails the net, and it is **the ONLY
thing** that can fail it that is not a rule verdict."* An empty roster is a third thing that
cannot fail it, and the sentence claims otherwise.

This file's own house rule is explicit and applied elsewhere in the same module:
* `_status_reports_i_do_not_know_as_itself` — `if not jobs: return False  # an empty roster
  proves nothing` (`drill.py:6698-6699`);
* `daemons_actually_check_their_own_source` — `if len(names) < 3: return False  # a roster that
  shrank proves nothing` (`drill.py:12739-12740`);
* `a_covered_job_that_never_restarted_is_still_named_in_the_report` — `if not covered: return
  False  # an empty roster must never read as a clean pass` (`drill.py:12993-12994`);
* `_local_buckets_excluded_from_cloud_claims` — `return bool(loops) and …` (`drill.py:17880`);
* `the_ignore_file_names_the_same_class` — `return refused > 0` (`drill.py:17027`).

`_policy_corpus_clean` has no such floor. Confidence: **DEFECT.**

---

## QUESTIONS

### Q1 — QUESTION. `excluded_sources_keep_their_records` has an explicit empty-corpus escape

`src/drill.py:15956`

```python
        return unreadable == 0 and (bool(had) or not names)
```

If `data/records/` yields no files at all, `names` is empty and `not names` rescues the return.
The net's whole subject is *"an excluded source keeps its records on disk"*, so a corpus with
zero records reading HELD is the same shape as D7. Unlike D7 the escape is **written out
deliberately** (`or not names`) rather than falling out of a glob, so it may be a considered
allowance for a fresh clone. Filed as a QUESTION rather than a defect for that reason: if it is
deliberate, the reason belongs in the docstring beside the two swallows it already discusses.

### Q2 — QUESTION. `drill_clean_description_is_idempotent` on an empty records directory

`src/drill.py:14522-14542`. `_os.listdir(recs)` **raises** if the directory is absent (and
`net()` correctly grades a raise as a breach), so the absent case is closed. An *empty* directory
returns `unreadable == 0` → True. Same class as D7/Q1, weakest instance.

### Q3 — QUESTION. `prove_net` truncates the only diagnostic it has

`src/drill.py:836-838`

```python
            return {"held": None, "found": 0, "error": "the scratch run printed no verdict",
                    "area_error": None, "root": root, "rc": p.returncode,
                    "expected": None, "stderr": (p.stderr or "")[-2000:]}
```

An undisclosed `[-2000:]`, on the one field that says *why* a scratch run produced no verdict —
which is exactly the situation in which the whole traceback matters. Not a roster/page/entry
truncation, so not a plain Hard Rule 0 breach, and the last 2000 characters are the right end to
keep. Filed as a QUESTION because it is undisclosed: the docstring documents every other key of
the returned dict and not this one.

### Q4 — QUESTION. `_write_targets` cannot see a write whose mode is not a literal

`src/drill.py:1580-1589`

```python
                m = mode.value if isinstance(mode, ast.Constant) else ""
                if isinstance(m, str) and any(c in m for c in "wax+"):
```

`open(p, mode_var)`, `open(p, "w" if x else "r")`, or a mode built by concatenation yields
`m = ""` and the call is **not collected**. `mutation_never_touches_the_live_tree`
(`drill.py:14821-14914`) requires every collected write target to be sandbox-rooted, so a write
the collector cannot see is a write the net cannot refuse — a fail-open in the detector that
guards "mutation testing cannot corrupt the real source". `os.makedirs`, `os.mkdir`,
`pathlib.Path(...).open("w")` and `shutil.copytree` are likewise outside `_WRITE_CALLS` /
`_WRITE_METHODS`. May be deliberate scoping to the shapes `mutate.py` actually uses (the comment
above `_WRITE_METHODS` shows that reasoning being applied once already), hence a QUESTION.

### Q5 — QUESTION. `_a_probe_never_counts_itself` fails open on an unreadable process table

`src/drill.py:7127-7130`

```python
    hits = W.running("drill.py")
    if hits is not None and any(pid == os.getpid() for pid, _cmd in hits):
        return False
    return True
```

`hits is None` means "the probe could not read", and the net passes. The eight synthetic
`script_of` cases above carry most of the net's weight, so this is a soft edge on the last
clause rather than the whole net — but the tri-state fail-open is unremarked, in a net whose
sibling `_status_reports_i_do_not_know_as_itself` exists precisely to punish rendering a
tri-state `None` as a confident answer.

### Q6 — QUESTION. Eight probes use FIXED artefact names inside a shared tree

`state/__drill_state_probe__.json` (4097), `handoff/__drill_blast_probe__.md` (4148),
`handoff/__drill_empty_find__.txt` (4326), `__drill_unlisted_probe__.txt` at the repo root
(4288), `data/__drill_surface_probe__.txt` (3785), `src/__drill_junction_probe__` (3696),
`src/__drill_surface_probe__` (3784), `state/codewatch_poll/__drill_poll_probe__.json` (13034).

`_step4_needs_its_plan` was repaired out of exactly this (`drill.py:2284-2292`): *"A UNIQUE ROOT,
BECAUSE A FIXED ONE IS SHARED WITH EVERY OTHER DRILL ON THIS MACHINE … Two drills running at
once — which is exactly what a mutation harness with parallel sandboxes does, **and what two
maintenance agents do without noticing** — take turns deleting each other's stand-in plan, and
this net then BREACHES on a plan that was removed by a neighbour."* Two concurrent drills over
the *same* tree (supervisor cycle + a hand-run `python src/drill.py`) reproduce that word for
word: one probe's `finally` deletes the other's artefact mid-net, and a false breach here is an
OWNER halt.

Filed as a QUESTION rather than a defect because the window is small and because the same file
demonstrably *did* think about this elsewhere — `abandoned_sandboxes_are_reaped` qualifies its
fixtures with `os.getpid()` (`drill.py:14983-14984`) and several probes use `mkdtemp`. The
inconsistency, not the hazard, is what I am reporting.

### Q7 — QUESTION. Two historical citations in `drill_citations` now point at unrelated lines

`src/drill.py:16093` — *"standards.py:604 was exactly this"*; `standards.py:604` is
`    return a == b or a == b + ":latest" or b == a + ":latest"`.
`src/drill.py:16098` — *"address_space.py:381 was exactly this"*; `address_space.py:381` is
docstring prose.

Both are past tense and describe findings the detector was built from, so they are history
rather than live claims — but they are stale line citations sitting inside the area whose
subject is stale line citations, and a reader checking them finds nothing. (`verify_math.py:7990`
at 16087 is explicitly framed as a historical defect and is fine.)

### Q8 — QUESTION. `tempfile.mktemp()` in the two dashboard history nets

`src/drill.py:16495` and `16529` (`history_heals_nonnumeric_at`,
`movement_survives_nonnumeric_metric`). `mktemp` is deprecated and race-prone, and the removal
is `except OSError: pass` with no note, so a failed removal leaves an unprefixed `.json` in the
system temp dir that no reaper matches — which is the leak order `d015e0a139a8` closed for the
two `mkdtemp` nets 40 lines below (`drill.py:16572-16576`, `16602-16604`). Unlike D1 the cleanup
here is **not** part of the verdict, so it cannot halt anything.

### Q9 — QUESTION. `liveness.scan()` runs five times per drill run

`drill.py:9043` (`liveness_sees_its_own_founding_example`), `9060` (`liveness_does_not_worsen`),
`17519` (the stamp in `main()`), plus `17519` twice more via
`_a_verdict_that_did_not_land_returns_nonzero`'s two real `main()` drives
(`drill.py:9192`, `9196`). Five full parses of `src/` per run. `_suppressed_still_visible`
(`drill.py:5085-5093`) records the house position: *"One net dominating the runtime of the whole
battery is a safety cost, not a performance one: a battery that is expensive to run is a battery
that gets run less often."* A single memoised scan per run would serve all five.

---

## DISPROVED — candidates I nearly filed and could not sustain

Recorded so the next run does not spend a lane on them.

* **"The drill's rehearsal closures still litter the permanent paper trail."**
  `state/workorders_closed.jsonl` holds 424 `__drill_litter_probe__`, 419 `__drill_rung4__`,
  419 `__drill_rung4b__` and 282 `__drill__` rows — 1,544 rehearsal rows in the trail. **They are
  historical.** Newest closed-log row for each of those names: `2026-09-09T17:31:18`. The
  self-test log `state/workorders_selftest.jsonl` is current — newest rows `2026-09-11T22:19:52`,
  `22:19:51`, `22:19:51`, `22:16:12`. Order `c24fcbb8a291`'s routing works and
  `a_probe_leaves_no_order_behind` is doing its job. The 1,544 rows are the pre-fix backlog and
  are append-only history.

* **"The `health.record` spy is defeatable by a module holding a direct reference."**
  Checked: `grep -rn "from health import"` over `src/` and `src/deprecated/` returns **zero**
  hits. Every call site in the tree — including `silence.py:132`, `silence.py:889` and
  `escalation.py:320` — goes through a `health.record(...)` attribute lookup at call time, so the
  spy installed at `drill.py:130` catches all of them despite being installed *after*
  `escalation`/`health` are imported at `drill.py:37-41`. THE LEDGER WITNESS's coverage claim
  holds.

---

## READ AND FOUND CLEAN

Everything below was read line by line and I found nothing to file.

* **THE WHOLE-RUN LEDGER WITNESS** (`drill.py:45-208`) and `drill_ledger_witness`
  (`17073-17203`). The two witnesses are genuinely independent (call-spy vs. flush-bytes), both
  carry `[control]` nets that drive the detector in the positive direction and additionally
  assert it is still *installed*, the witness area is genuinely last in `main()`'s tuple
  (`17381`), and the control's escape is removed by index rather than by value. Nothing found.
* **`_live_stmts` / `_live_walk` / `_breaks_out_of` / `_arm_leaves` / `_static_truth`**
  (`984-1210`). The reachability core. The `while True:` else, the `while False:` else and the
  `while True:` fall-through are all handled in the correct directions, and
  `the_reachability_primitive_understands_loop_else` (`9066-9128`) drives all four fixtures
  including the control. Nothing found.
* **`_spellings_of_call` / `_name_spellings` / `_import_maps` / `_bound_from_call` /
  `_carries_result_of` / `_filtered_names` / `_rooted_names` / `_is_rooted` /
  `_gate_precedes_spawn`** (`922-1483`, `1592-1710`). Nothing found.
* **`drill_queue`, `drill_dispatch`, `drill_train`, `drill_assay`, `drill_assay_engine`,
  `drill_no_caps`, `drill_cache`** (`1715-2716`). Nothing found. In particular
  `_gates_agree`/`_drill_never_writes_the_gate` no longer touch the owner's `config.yaml`, and
  `_step4_needs_its_plan` no longer moves `STEP4_PLAN.md`.
* **`drill_park` and the twelve 2026-08-31 mutation-survivor nets** (`2844-3414`). Nothing found;
  `_no_runtime_clear` and `_a_borrowed_main_is_not_a_person` both run against scratch halt files
  and both assert the file is byte-identical afterwards.
* **`drill_local_agent`** (`3419-4357`) apart from Q6. `denied()`'s `no such file` disambiguation
  through `LA._safe` is correct, and every probe cleanup here notes its failures.
* **`drill_publish`, `drill_ledgers`, `drill_two_writer`, `drill_done_keys`, `drill_profile`,
  `drill_snapshot`, `drill_stale_writer`** (`4548-6530`). Nothing found.
* **`drill_policy`, `drill_binding_identity`, `drill_fetch`, `drill_cascade`,
  `drill_workorders`, `drill_inspector`** (`6534-9210`) apart from D7. Verified independently
  that `_supersession_is_called`'s subject (`workorders.py:999/1342/1352`),
  `_identity_probe_is_gated`'s (`binding_health.py:942/1037-1038`), `_refusal_is_recorded`'s
  (`feats.py:2196`), `_halt_is_not_breakage`'s (`overnight.py:1902`),
  `_local_buckets_excluded_from_cloud_claims`'s (`cascade_bridge.py:1564`, inside a `for` with the
  `LOCAL_PREFIX` guard and a `continue`), `resync_cannot_revert_an_exclusion`'s
  (`resync_roll.py:199/244`, both the `!=` spelling the net was widened for) and
  `generator_actually_skips_an_excluded_source`'s (`manifest_builder.py:459`) all still exist —
  none of these nets is silently vacuous.
* **`_twins_ignores_a_foreign_tree`, `drill_no_top_ups`, `drill_probe_honesty`,
  `drill_rung_four`, `drill_codewatch`, `drill_scout`, `drill_defect_classes`**
  (`9213-13836`) apart from D1. `daemons_actually_check_their_own_source`'s derived roster was
  verified live: `overnight.STANDING` names `dashboard/foreman/overwatch/pipeline/publish/read.py`
  and all six carry both `codewatch.stamp` and `codewatch.exit_if_stale`.
* **`drill_recorders_and_lane`, `drill_mutation`, `drill_scope`, `drill_correlation`,
  `drill_resonance`, `drill_threads`** (`13839-15968`, `12301-12647`) apart from Q1. The three
  `tempfile.tempdir` redirections that contain `reap_orphans` are all restored FIRST and
  unconditionally in their `finally`.
* **`drill_escalation_behaviour`** (`10006-11560`) apart from D2/D3.
* **`drill_assay_behaviour`, `drill_citations`, `drill_outside`, `drill_identity_dashboard`,
  `drill_hostcheck`, `drill_weave_plan`, `drill_agent_scratch_gate`** (`11576-12298`,
  `16048-17070`) apart from Q7/Q8.
* **`_wait_for_a_settled_tree`, `_reread_the_breaches`, `main()`** (`17206-17711`). The re-read
  fails closed in every direction, the maintenance guard is genuinely never consulted, the
  breaching verdict is copied out from under the next run, the halt sentence and evidence are
  uncapped, and the rc=3 path is unreachable when a breach or `--to-halt` is in play. Nothing
  found beyond the re-read's interaction with D2, noted there.
* **Structural checks over the whole file:** `pyflakes` clean; **no** function defined in
  `drill.py` is unreferenced anywhere in it (no dead code); **no** duplicate `net()` name within
  any area function; **no** duplicate area string across area functions (so `_ATTACKS`'
  `(area, net)` key cannot silently collide and make `_reread_the_breaches` prove the wrong net);
  493 literal `net(` call sites; the only slice expression in live code is the `[-2000:]` of Q3.

---

## NOTE ON UNTRUSTED CONTENT

Nothing in `src/drill.py` contained text addressed to a reading agent as an instruction. Every
imperative sentence in the file is ordinary house commentary addressed to a future maintainer
("read this before you write a net that drives a refusal path", "New areas go ABOVE this line").
Recorded because the work order asks for it, not because anything looked like an injection.

## COVERAGE

`src/drill.py` — read in full (17,711 / 17,711 lines). 7 DEFECTs, 9 QUESTIONs, 2 disproved
candidates. Recorded to `sweep_plan` under `run56`, batch 1.
