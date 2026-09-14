# SWEEP 57 — BATCH 01 AUDIT

Run: `run57`, batch 1. Module in scope: `src/drill.py`, **17,928 lines, read in full, top to
bottom, in eighteen consecutive chunks.** Nothing was sampled or skipped.

Method: a full read, then each candidate checked against the source of the module it concerns
(`runguard.py`, `profile.py`, `cascade_bridge.py`, `coverage.py`, `binding_health.py`,
`deprecated/catalogue_local.py`, `mutate.py`, `feats.py`, `anchors.py`, `foreman.py`,
`verify_math.py`) and, where it could be measured, against state on disk (read-only). Every
`file.py:NNN` citation in drill.py was resolved by script. `pyflakes src/drill.py` is clean
(rc=0). drill.py and verify_math.py were NOT run. Nothing was written except this file and the
sweep_plan coverage record.

The open queue was checked before anything was labelled new. Sweep 56 batch 01 filed three
orders (5d686329771b, 1c7c2c2c8b00, 247586e57b61); its other seven findings are still in the
source with **no open order**, and are listed under CARRIED so they are not lost a second time.

---

## NEW DEFECTS

### N1 — DEFECT (latent, with a measured past occurrence). Two binding_health nets drive `run()` with the LIVE quarantine file and the LIVE work-order queue still wired in

`src/drill.py:6752-6801` (`_partial_canary_merges`) and `src/drill.py:7402-7482`
(`_binding_health_filters`).

Both redirect `BH.OUT`, `BH.canary`, `BH.known_present_titles` and `BH._load`, and nothing else.
`binding_health.QUARANTINE` stays `os.path.join(HERE, "data", "HOST_QUARANTINE.json")`
(`binding_health.py:52`), and `run()` calls the real `quarantine()` for any host whose canary
comes back `healthy is False` (`binding_health.py:1319`):

```python
            rec["quarantined"] = bool((quarantine(h, rec.get("reason") or "canary failed")
                                       or {}).get("landed"))
```

`quarantine()` writes that file through `_land_cas` and then calls
`ESC.escalate(ESC.SUPERVISOR, "HOST_QUARANTINED", ...)`, which files a real work order.
`_deliberately_failing` only swaps out `health.record`, so it covers the failure ledger and
leaves both of the other writes alone.

This already happened. `state/workorders_closed.jsonl` holds two rows that came from these nets:

```
"id": "5b6a89c02b87", "code": "HOST_QUARANTINED", "what": "probed.example.invalid quarantined: canary raised TypeError", first_seen 1788903370 (2026-09-08)
"id": "7147d4ffae96", "code": "HOST_QUARANTINED", "what": "a.example.invalid quarantined: canary raised TypeError", "seen": 4
```

Both were resolved with the text "host is no longer quarantined". For that resolution to be
written, the fixture hosts had to be in the live `data/HOST_QUARANTINE.json` first. The repair
that followed (`**kw` on the stubs, 6772-6782 and 7433-7436) removed the TypeError that triggered
it. It did not remove the exposure. The next stub drift, or any `run()` change that turns a
stubbed canary into `healthy: False`, writes the live quarantine file and files live orders again.

Two in-file comments make it worse, because they present the ledger wrap as the fix: 6787-6791
says "a stubbed canary makes `binding_health` quarantine this fixture host for real, and a
quarantine escalates", and 7469-7470 says "the fixture host is quarantined for real". Under the
current stubs (`healthy: None` / `True`) neither statement is true, so both comments are stale
too. The safe pattern already exists in this file: `_quarantine_reports_the_disk_not_the_intention`
(8210-8287) redirects `BH.QUARANTINE` and stands in an `escalation` module for this exact reason
("the real one files a work order and the drill is not allowed to leave one in the queue for a
host that does not exist").

Measured today: 0 occurrences of `example.invalid` in `data/HOST_QUARANTINE.json`,
`state/workorders.json` and `state/failures.json`. Latent now; it has happened before.

### N2 — DEFECT. `_unparseable_reply_is_benched_and_ledgered` drives its own copy of the rule, not cascade_bridge's

`src/drill.py:7032-7159`.

The docstring says it is "DRIVEN for the rule". The driven half is a local function in drill.py:

```python
        def fail(bucket):
            key = bucket or "<bucket unresolved>"
            with CB._DEAD_LOCK:
                n = CB._UNPARSEABLE.get(key, 0) + 1
                CB._UNPARSEABLE[key] = n
            CB.record_unrecognised(key, "x")
            if bucket and n >= CB.UNPARSEABLE_STRIKES_BEFORE_BENCH:
                CB._bury(bucket)
```

That is a line-for-line copy of the production branch at `cascade_bridge.py:2004-2011`
(`_strikes = _UNPARSEABLE.get(_key, 0) + 1 ... if _bucket and _strikes >= UNPARSEABLE_STRIKES_BEFORE_BENCH: _bury(_bucket)`).
The real branch is never executed. The only thing read from the module under test is the
constant, so the four "ledger sees the first / bench waits / reset / unresolved bucket" assertions
test drill.py against itself. The expected value and the actual value come from the same code.

The structural half does not cover the gap either:
* `called = {n.func.id for n in _ast.walk(branch) ...}` uses `ast.walk`, not `_live_walk`, so a
  `_bury` in dead code after a `return` inside the branch satisfies it. That is the defeat this
  file has removed from roughly twenty other nets.
* Nothing asks whether `_bury` is guarded by the strike threshold. Mutants such as
  `if _bucket and _strikes >= 1:` or `if _bucket:` (bench on the first reply, which is "the fluke
  fault" the net's own `< 2` check names) or `_strikes = 1` (a count that never grows) all
  survive: `record_unrecognised` and `_bury` are still called in the branch, a `_UNPARSEABLE.pop`
  still exists elsewhere, the constant is still ≥ 2, and `fail()` still behaves.

Minor, same site: the source is read with `open(os.path.join(HERE, "src", "cascade_bridge.py"))`
instead of `_srcdir()`, so the net cannot be pointed at a scratch tree to watch it go red, and the
file handle is never closed.

### N3 — DEFECT (minor). `_coverage_reaches_unreachable`'s "reportable" clause can be satisfied by prose

`src/drill.py:7386-7399`

```python
    if "UNREACHABLE" not in (CV.report.__doc__ or "") and "UNREACHABLE" not in _cv_report_src():
        return False                  # producible but unreportable is the same fault one layer on
```

`_cv_report_src()` is `inspect.getsource(CV.report)`, which includes comments. The first arm is
the docstring. So a `report()` whose UNREACHABLE row has been deleted still passes, provided a
comment or docstring in the function mentions the word. This is the "a word is not a call" shape
the file's own paragraph at 653-668 is written against. `report()` currently prints the row
(`coverage.py:360`), so nothing is wrong today. `_says(node, "UNREACHABLE", reachable=True)` over
the parsed `report` def is the instrument the file already has for this.

### N4 — DEFECT (latent). `the_deprecated_cataloguer_still_refuses` runs the quarantined third writer against the live tree

`src/drill.py:5445-5506`

```python
        mod = os.path.join(_srcdir(src), "deprecated", "catalogue_local.py")
        ...
            r = subprocess.run([sys.executable, mod] + list(argv), capture_output=True,
                               text=True, errors="replace", cwd=HERE, timeout=300, ...)
        ...
        for argv in ([], ["--dry-run"], ["--limit", "3"], ["--only", "Bleach"]):
```

The docstring names the attack: "somebody deleting the refusal because six lines at the top of a
deprecated file nobody reads look exactly like dead code". The only thing between this net and a
real run is that refusal (`catalogue_local.py:91-94`, a module-level `raise SystemExit`), and that
is the guard the net exists to test. On the day it is deleted, the first probe runs the script
with **no arguments**, which its usage line calls "catalogue every remaining source". It runs
against the live `HERE`/`ROLL`/`RECORDS` (`catalogue_local.py:100-102`), writing
`data/records/<slug>.json` with a bare `open(path, "w")` and rewriting `data/SWEEP_ROLL.json`
non-atomically inside its loop, as the docstring above it says. The `timeout=300` then kills it
partway through, which is the truncated-roll case the same docstring warns about. After that,
`_reread_the_breaches` runs the attack a second time.

The docstring's closing claim, "Nothing is written by any of these five runs -- that is the claim",
only holds while the guard under test holds. This is the class order 1c7c2c2c8b00 records for
`the_destructive_tool_asks_before_it_moves_anything`, in a different net that the order does not
name. A scratch copy (`_srcdir(src)` pointed at a `mutate.sandbox()`-shaped tree, or `prove_net`'s
world) would give the same verdict without live data behind it.

### N5 — DEFECT (minor). `run_actually_holds_the_lock` leaks a temp directory every run

`src/drill.py:14977-14997`

```python
        d = tempfile.mkdtemp(prefix="drill_mut_held_")
        M.LOCK = os.path.join(d, "LOCK.json")
        ...
        finally:
            M.LOCK, M._run_mutation, M._HELD = saved_lock, saved_body, saved_held
```

There is no `shutil.rmtree(d)`. All three siblings in `drill_mutation` remove theirs
(`lock_is_exclusive` 14955, `unreadable_lock_counts_as_HELD` 15016,
`dead_holder_does_not_block_forever` 15034). The prefix is not `mutate.SANDBOX_PREFIX`, so
`reap_orphans` never collects it. This is the leak order d015e0a139a8 closed for the two
dashboard nets at 16790-16794 and 16820-16822. If the lock release failed, the leaked directory
also holds a stray `LOCK.json`.

---

## NEW QUESTIONS

### QA — QUESTION. drill_run_guard (new in run #56): the incident it cites is one the netted arm cannot prevent for any real caller

`src/drill.py:6061-6072`, expectation string:
*"run #53 was working with a 101.7-minute-old heartbeat; run #54 read that as dead and both
edited src/drill.py inside twenty minutes"*.

The net builds a record with **this drill process's** pid and start time. That is a long-lived
process, so `holder_is_live`'s stale-but-alive arm (`runguard.py:286-294`) returns True. In the
tree, though, the only callers of `claim()` and `beat()` are the CLI (`runguard.py --claim/--beat`,
`runguard.py:527-541`). A grep of `src/` finds no in-process caller. Each call is a short-lived
interpreter, so the pid written is dead within seconds. Three places say so: `beat()`'s own
comment ("for the ordinary holder of this guard -- a session driving many short-lived
interpreters -- the pid written at claim time is dead within seconds"), the sibling net
`the_detector_does_not_fire_on_an_ephemeral_holder` (6130-6152, "measured on run #56's own
record ... pid 26924, gone"), and the area docstring. So for the run #53/#54 shape the arm
returns False and the successor walks in, exactly as before. The net proves the mechanism is
correct. Its printed expectation says the incident is covered, and it is not. A reader who sees
this net HELD would conclude the overlap is fixed. Could be deliberate, since the mechanism is
there for a future long-lived holder, so this is a QUESTION. Either way the expectation should
not name an incident the code cannot stop.

### QB — QUESTION. drill_run_guard breaches, rather than declining, on a machine where the probe cannot be staged

`src/drill.py:6055-6065` (and 6091-6093, 6118-6120, 6158-6160)

```python
        pid, created = _mine()
        if created is None:
            return False                     # the probe must work on the machine it runs on
```

`runguard._process_signature` returns `(alive, None)` on its no-psutil ctypes path, and
`holder_is_live`'s docstring says a machine without psutil must behave exactly as before. Four
nets here then return False, which is a breach and an OWNER halt. `_twins_ignores_a_foreign_tree`
(9492-9500) got a ruling for exactly this case (orders ef0b67732a3b, 3e65d8657462: "a probe that
could not be staged is not an alarm"), and it notes and returns True. psutil 7.2.2 is installed
here, so the case is latent. The comment reads like a deliberate choice, hence QUESTION.

### QC — QUESTION. No net anywhere watches `claim()` REFUSE a live predecessor

`runguard.py:413` (`if holder_is_live(prior): return False, ...`) is the line that actually
prevents the overlap. drill_run_guard exercises `holder_is_live` and `guard_fault` on synthetic
records, and its only `claim()` call (6171-6182) is against an empty scratch guard, where it
checks that pid and pid_started are recorded. verify_math's runguard rows (2905-2960, 11095-11125)
cover claim-on-free, beat/release ownership, takeover of a stale record and the CAS race. None of
them claims over a live predecessor and expects a refusal. The predicate is proven and its one call
site is not, which is the "a predicate nothing calls is a comment" gap `_the_loop_asks_the_gate`
(5000-5018) exists for elsewhere.

### QD — QUESTION. `_rows_in` turns an unreadable ledger into zero rows, so the paper-trail half of `a_probe_leaves_no_order_behind` cannot fail

`src/drill.py:630-634`

```python
    try:
        with open(path, encoding="utf-8") as fh:
            return sum(1 for line in fh if token is None or token in line)
    except OSError:
        return 0
```

The docstring gives "0 if it is not there yet". A `PermissionError` or a lock also returns 0, and
the only caller compares before against after (10023, 10043). If `WO.CLOSED_LOG` cannot be read,
`0 == 0` holds whatever the probe wrote. This is a fail-open in a net whose subject is litter in
that exact file.

### QE — QUESTION. The snapshot area's cleanups against LIVE `state/` fail silently, and the note that claims to record them cannot fire

`src/drill.py:6517-6525`

```python
    try:
        import shutil as _sh0
        for _new in (set(os.listdir(SNAP.ROOT)) - _empty_before ...):
            if _new.startswith(_EMPTY + "-"):
                _sh0.rmtree(os.path.join(SNAP.ROOT, _new), ignore_errors=True)
    except OSError:
        import silence as _si0
        _si0.note("drill.py:empty-snapshot-cleanup")
```

`rmtree(..., ignore_errors=True)` never raises, so the note only fires when `os.listdir` fails and
never for the failed removal it is named after. The same silent `ignore_errors=True` is at 6538 (the
per-run `drill-*` snapshot), 6349-6353 and 6396-6399 (`drilldir_*`/`drillvfy_*` scratch trees made
inside live `state/`), and 6455. The comment at 6529-6536 records a measured result of exactly this
leak: 151 orphaned `drill-*` directories. Every other live-tree cleanup in `drill_local_agent`
notes its failures (4112-4116, 4199-4203, 4298-4302, 4348-4352).

### QF — QUESTION. `prove_net` swallows a failed junction unlink right before removing a tree whose `data/` is the corpus

`src/drill.py:856-863`

```python
            for shared in ("data", "prompts", "reference", os.path.join("output", "index")):
                try:
                    link = os.path.join(root, shared)
                    if os.path.isdir(link):
                        os.rmdir(link)
                except OSError:
                    pass
            shutil.rmtree(root, ignore_errors=True)
```

The comment says "this is the one place in this file where getting that wrong would delete it"
(the 1.1 GB mined corpus), and the one step that can go wrong is a bare `pass`. Python 3.13's
`shutil.rmtree` removes a junction without going into it, so the delete is contained on this
interpreter. The failure still leaves nothing behind for anyone to find.

### QG — QUESTION (low). `index_spine_agrees_with_the_resolver` passes with no index and with an empty one

`src/drill.py:16443-16453`: `if not os.path.exists(corpus_db.DB): return True`, and an index with
zero `source` rows also returns True. Its sibling `index_admits_when_it_is_behind` treats a missing
index as maximally stale. When there is no derived view there is arguably nothing to disagree with,
so this may be deliberate. It is recorded because "an empty roster proves nothing" is applied
elsewhere in the file (6916-6917, 12957-12958, 13211-13212).

---

## CARRIED — sweep 56 batch 01 findings still in the source, with NO open order

Each was re-verified against today's source. None matches an open order: the full open queue was
searched for each marker.

* **D4 — DEFECT, carried.** `src/drill.py:8295`: "the clamp it is named after is `feats.py:159`".
  `feats.py:159` is still `h = h.split("/")[0].split(":")[0].rstrip(".")`. The clamp
  `_BACKOFF[host] = min(BACKOFF_MAX, ...)` is at `feats.py:238`.
* **D6 — DEFECT, carried.** `src/drill.py:10744-10746`: "HOSTS points into the temp tree and the
  record writer is stubbed". The net body (10749-10785) redirects only `ESC.HALT_FILE` and
  `ID.HOSTS`, and nothing stubs the record writer.
* **D7 — DEFECT, carried.** `src/drill.py:7907-7917`, `_policy_corpus_clean`: an absent or empty
  `data/records/` still returns `bad == 0 and unreadable == 0` → True, with no floor.
* **Q1 — carried.** `src/drill.py:16174`, `return unreadable == 0 and (bool(had) or not names)`.
* **Q3 — carried.** `src/drill.py:838`, undisclosed `(p.stderr or "")[-2000:]`.
* **Q4 — carried.** `src/drill.py:1586-1588`, `_write_targets` does not see a non-literal mode.
* **Q5 — carried.** `src/drill.py:7345-7348`, `hits is None` (unreadable process table) passes.
* **Q6 — carried.** Fixed probe names in shared trees, unchanged: 3696, 3784-3785, 4097, 4148,
  4288, 4326, 13252.
* **Q7 — carried.** `src/drill.py:16311` `standards.py:604`, `16316` `address_space.py:381`
  (historical citations inside the citecheck area; neither target is the shape described).
* **Q8 — carried.** `src/drill.py:16713` and `16747`, `tempfile.mktemp(...)` with an unrecorded
  `except OSError: pass`.
* **Q9 — carried.** `liveness.scan()` still runs at 9261, 9278 and 17737, plus twice more through
  `_a_verdict_that_did_not_land_returns_nonzero`'s two `main()` drives.

---

## KNOWN (open orders)

* KNOWN(5d686329771b): `_the_report_says_how_long_ago_each_job_ASKED` still grades its cleanup of
  live `state/codewatch_poll/` and swallows the removal failure, 13252-13266.
* KNOWN(1c7c2c2c8b00): `the_destructive_tool_asks_before_it_moves_anything` still drives
  `withdraw_chapters --go` against live `WC.HERE`/`WC.CATALOG`, 10632-10659.
* KNOWN(247586e57b61): `_esc_sandbox` still stubs only `file_order` and `health.record`,
  10194-10199. Probes still reaching `resolve_code`: 10858-10866, 11091-11097.
* KNOWN(89503c58409f): stale `anchors.py:427` at 12126 and 12147 (sweep 56's D5), and
  `foreman.py:115` at 17698, both listed in that order.
* KNOWN(156c2e28f823): `_sandbox_without_its_target_refuses`, 7656-7700, unchanged.
* KNOWN(400d5c76e6f8): nothing enforces the `_deliberately_failing` wrap. N1 above is a case where
  the wrap is used and the probe still writes live state through a channel the wrap does not cover.
* KNOWN(e727ab804c5b): stand-ins wider than their subject go unseen. The `**kw` stubs in N1 are
  instances.

---

## READ AND FOUND CLEAN

* **`drill_profile`'s new feature-digit net**, `a_feature_digit_past_its_own_table_is_refused_readably`
  (6249-6290). Checked against `profile.py:157-200`. `B32[len(tbl)]` is exactly the first digit a
  table cannot reach, since `decode` refuses `i >= len(tbl)`. The refusal message
  (`profile.py:191-194`) carries both `%r` of the profile and the axis name, so the
  `repr(bad) not in str(e) or axis not in str(e)` test can tell the per-axis refusal from the
  alphabet refusal (`not a world profile: {profile!r}`, which carries no axis). `except Exception:
  return False` correctly grades the old IndexError as a breach. The hard-coded four digits fail
  closed if `AXES` grows (strict `zip` → ValueError without the axis name → False). The one
  vacuous case, an empty `AXES`, is covered by the sibling "a well-formed profile still decodes"
  (6206-6208). No stdlib `profile` shadowing: nothing in `src/` imports `cProfile`. Nothing found.
* **`drill_run_guard`'s mechanics** (6016-6186), apart from QA-QC. `_dead_pid` measures rather than
  guesses, the recycled-pid net checks start-time identity, the no-pid record keeps its original
  verdict, the ephemeral-holder silence is pinned, and `claim()` is only run against a scratch path.
  No net touches `state/MAINTENANCE_RUN.json`. The area is registered in `main()`'s production
  tuple (17577), so its nets do run.
* The ledger witness (45-208, 17291-17421), the reachability core (984-1483), `_write_targets`
  apart from carried Q4, `drill_queue`/`dispatch`/`train`/`assay`/`assay_engine`/`no_caps`/`cache`,
  `drill_park` and the 2026-08-31 survivor nets, `drill_local_agent` apart from carried Q6,
  `drill_publish`, `drill_ledgers`, `drill_two_writer`, `drill_done_keys`, `drill_snapshot` apart
  from QE, `drill_stale_writer`, `drill_policy` apart from carried D7, `drill_binding_identity`
  apart from N1-N3, `drill_fetch`, `drill_cascade`, `drill_workorders`, `drill_inspector`,
  `drill_no_top_ups`, `drill_probe_honesty`, `drill_rung_four` apart from QD,
  `drill_escalation_behaviour` apart from the KNOWN items, `drill_assay_behaviour`,
  `drill_threads`, `drill_codewatch` apart from KNOWN 5d686329771b, `drill_defect_classes`,
  `drill_scout`, `drill_recorders_and_lane`, `drill_mutation` apart from N5, `drill_scope` apart
  from carried Q1, `drill_correlation`, `drill_citations` apart from carried Q7, `drill_outside`
  apart from QG, `drill_resonance`, `drill_identity_dashboard` apart from carried Q8,
  `drill_hostcheck`, `drill_weave_plan`, `drill_agent_scratch_gate`, `_wait_for_a_settled_tree`,
  `_reread_the_breaches` and `main()`. The re-read fails closed in every direction, an area that
  dies is recorded as a breach, the halt carries each net's error and a kept copy of the rows, and
  rc=3 cannot mask a breach or `--to-halt`.
* Citations resolved correctly by script: `liveness.py:12`, `context_budget.py:276`,
  `generate.py:552`, `withdraw_chapters.py:216-219`, `coverage.py:53`, `anchors.py:37-40` (banner
  plus comment). `autostart.py:395` (13364) and `escalation.py:409` (15645) are explicitly
  historical.
* Structural: `pyflakes` clean; 502 lines containing a `net(` call.

## NOTE ON UNTRUSTED CONTENT

Nothing in `src/drill.py` or the modules consulted addressed an instruction to a reading agent.
The imperative sentences are ordinary maintainer commentary.

## COVERAGE

`src/drill.py`: read in full (17,928 / 17,928 lines). New: 5 DEFECTs, 7 QUESTIONs. Carried from
sweep 56 without an order: 3 DEFECTs, 8 QUESTIONs. KNOWN: 7. Recorded to `sweep_plan` under
`run57`, batch 1.
