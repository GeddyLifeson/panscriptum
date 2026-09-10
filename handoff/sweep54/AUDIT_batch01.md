# SWEEP run54 — AUDIT batch 01

**Module in this batch:** `src/drill.py` (16,971 lines, 467 `net(` call sites — two of them
inside `for` loops, so the runtime figure is higher).

## How I read it

Whole file, top to bottom, in nine passes of ~1,000 lines each — every line, including the
docstrings, because in this file the docstring is where the claim lives and the brief asks for
claims the code no longer honours. I then went back out to the modules the nets name and checked
the specific facts the findings below rest on, by reading source rather than by inference:

* `mutate.sandbox()` (mutate.py:1481-1560) — how the sandbox root is created, renamed and
  cleaned up on the refusal path;
* `codewatch.fingerprint()` and `codewatch.quiet_seconds()` (codewatch.py:208-279) — what each
  one actually reads, which is the difference between the two;
* `silence.note()` (silence.py) and `health.record` / `health.is_selftest` (health.py:66-152) —
  whether an abstention note reaches the recorder the ledger witness watches;
* signatures for every stand-in the drill installs, against the real function it replaces:
  `wiki_source._api`, `chain.extract/fit/write_result`, `pipeline.phase_chain`'s calls into
  them, `hostcheck.probe/null_rate/relevance`, `binding_health._load/canary/
  known_present_titles`, `gpu_lane._take_slot`, `feats.api/fetch`, `scout.scout/sweep`,
  `manifest_builder.build_jobs_for_source`, `silence.replace_if_unchanged/replace_retry/
  append_line/write_json`, `escalation._land_halt/_land_clear/_write_stopped/_read_stopped`,
  `publish._scan_units/scan_for_secrets`, `prose_gate.*`;
* `overnight.ALL_JOBS` and `autostart.main()`'s `--status` rendering;
* `wiki_source._ALLCATS`'s cache key shape against the key the drill pops.

I also enumerated every `net(` name statically (AST, read-only, script in the session scratchpad)
to check for two nets sharing an `(area, name)` key — `_ATTACKS` is keyed on that pair and the
second would silently win the re-read. **There are none**; every literal name is distinct.

I ran nothing from `src/`. Nothing under `src/`, `data/`, `state/` or any ledger was written.

---

### MAJOR — the abstention discipline and the ledger witness contradict each other; any declined measurement now halts the library

**Where:** `src/drill.py:81` / `:92-112` / `:16380-16394`, against the ~20 abstention sites listed
below.

**What:** `_spy_record` is installed over `health.record` at import (`drill.py:129`) and appends
**every** call to `_LEDGER_ESCAPES`. `drill_ledger_witness`'s net
`no_probe_writes_into_the_live_failure_ledger` then raises if that list is non-empty, and a
breached net in this file escalates to OWNER and halts the library.

Separately, this file has an explicit, twice-ruled discipline that a probe which could not be
staged is **NOTED, not graded** — orders ef0b67732a3b (`_junction_out_of_the_writable_surface`)
and 5eea5c20db8a (`datasette_config_is_generated_not_copied`), quoted in the file as "a path that
could not be written is a measurement that did not happen, and a measurement that did not happen
must not be graded either way". Every one of those abstentions is spelled `silence.note(...)`.

`silence.note(site)` calls `health.record(f"silent:{site}", ...)` **unconditionally** — it does
not require an active exception; with none, it records `name = "None"` and proceeds
(silence.py, `note()` body). So each abstention is, to the spy, a probe site reaching
`health.record`.

The abstention/cleanup notes in this file, none of them declared:

```
drill.py:534   %s-order-cleanup            drill.py:3620  surface-probe-unstageable
drill.py:2696  drill-area-cleanup          drill.py:3628  surface-probe-unstageable
drill.py:3534  junction-probe-cleanup      drill.py:3632  surface-probe-unstageable
drill.py:3543  junction-probe-unstageable  drill.py:3642  surface-probe-readback
drill.py:3547  junction-probe-unstageable  drill.py:3833  state-probe-cleanup
drill.py:3606  surface-probe-cleanup       drill.py:3920  blast-probe-cleanup
drill.py:3612  surface-probe-cleanup       drill.py:3942  blast-cap-cleanup
drill.py:4019  unlisted-probe-cleanup      drill.py:6024  empty-snapshot-cleanup
drill.py:8998  twins-probe-unstageable:no-psutil      drill.py:9014  :no-child
drill.py:9032  twins-probe-unstageable:child-gone
drill.py:9187  paid-lane-config-absent     drill.py:9190/9193 paid-lane-config-unreadable
drill.py:9284  rung4-cleanup               drill.py:9313  rung4b-cleanup
drill.py:9423  litter-probe-cleanup        drill.py:15572 datasette-config-unwritable
```

`_not_a_leak` (`drill.py:174-207`) is the declared-exemption mechanism built for exactly this,
and it is applied to **one** call site in the whole file (`a_rehearsal_is_not_filed_as_a_fault`,
`drill.py:13743`).

**Why it is wrong:** inputs → wrong result. Take any one of: `~/cascade/config.json` absent (a
different machine — `CASCADE_CONFIG` at `drill.py:322` is written precisely to tolerate that
case and `paid_access_stays_switched_off` returns True for it *on purpose*); `psutil` not
importable; `cmd` absent (not Windows); a `datasette` process holding `state/datasette.json`
open, which `corpus_db`'s own docstring names as the **expected** Windows case; an antivirus
scanner denying one `os.remove` of a probe file. Each of those makes a net correctly and
deliberately decline to grade — and each fills `_LEDGER_ESCAPES`, which makes
`no_probe_writes_into_the_live_failure_ledger` raise, which halts the whole library at OWNER
rung over a measurement that was declined rather than failed.

The two rulings are individually right and jointly unworkable as written: one says an
undeliverable attack must be recorded in the health ledger, the other says nothing this battery
does may reach the health ledger.

**Confidence:** high on the mechanism, traced by reading `silence.note`, `health.record`,
`health.is_selftest` (the keys carry no `__drill…__` marker, so they route to the real ledger,
not `_SELFTEST`) and `_spy_record`/`_LEDGER_ESCAPES`/the witness net. **Latent on this machine**,
not live: none of the abstention paths is taken on the happy Windows path here, which is why the
witness is green today. I did not run the drill.

---

### MAJOR — `_sandbox_without_its_target_refuses`'s "does not leave the half-built sandbox behind" clause cannot fail, and can only ever produce a FALSE halt

**Where:** `src/drill.py:7185-7199` (the `finally` and the `return`).

**What:**

```python
finally:
    shutil.copy2, tempfile.mkdtemp = real_copy, real_mkdtemp
    for r in roots:
        shutil.rmtree(r, ignore_errors=True)
# And it must not leave the half-built sandbox behind while refusing.
return refused and not any(os.path.isdir(r) for r in roots)
```

**Why it is wrong:** the second conjunct is a claim about `mutate.sandbox()`'s own cleanup, and
it is decided by the drill instead, twice over.

1. The `finally` runs **before** the `return` expression is evaluated and has already
   `rmtree`d every path in `roots`. Whatever `sandbox()` did or did not delete, `isdir` is False
   by the time it is asked.
2. `roots` is filled by the `remember()` wrapper around `tempfile.mkdtemp`, and
   `mutate.sandbox()` (mutate.py:1481-1486) does
   `staging = tempfile.mkdtemp(prefix=BUILDING_PREFIX)` and then `os.rename(staging, root)` —
   the recorded path is renamed away, so `os.path.isdir(staging)` is False before the drill's
   own cleanup even matters.

Concretely: delete `mutate.py:1549`'s `shutil.rmtree(root, ignore_errors=True)` — the exact
cleanup this clause claims to police, sitting immediately above the `RuntimeError` the net's
first conjunct reads — and this net still reports HELD.

It also runs the other way. `shutil.rmtree(..., ignore_errors=True)` does not raise but does
leave the directory when a handle is held; on this machine an antivirus scanner holding a
directory for a moment is documented elsewhere in this very file
(`drill.py:3557-3566`, order f5f01fe5f8ef). In that case `isdir` is True, the net returns False,
and `main()` escalates a breached net to OWNER. That is precisely the fault order f5f01fe5f8ef
removed from `_junction_out_of_the_writable_surface` — "the cleanup is not part of the verdict",
because "a full stop caused by a probe that could not tidy up" is not a finding — reintroduced
here inverted.

**Confidence:** high. Traced against `mutate.py:1481-1486` (mkdtemp under `BUILDING_PREFIX`, then
`os.rename`) and `mutate.py:1547-1562` (the `absent` branch rmtrees `root` and then raises the
`"Nothing was mutated"` RuntimeError the first conjunct matches). Not executed.

---

### MAJOR — the two junction probes reset `src/`'s directory mtime, which is the instrument the drill uses to decide whether its own breach is real

**Where:** `src/drill.py:3512` (`src/__drill_junction_probe__`) and `src/drill.py:3593`
(`src/__drill_surface_probe__`); consumed at `src/drill.py:16472-16500`
(`_wait_for_a_settled_tree`).

**What:** both probes `mklink /J` a junction **inside the live `src/`** and remove it again on
every battery run. `blast_cap_bites` (`drill.py:3858-3862`) states the hazard as its own reason
for putting its probe under `handoff/` instead: "`codewatch` fingerprints `src/`, and a battery
that adds and removes a module there would bounce every standing daemon onto rc=17 every cycle."

The digest is safe — `codewatch.fingerprint()` (codewatch.py:215-232) walks `os.listdir(root)`
and skips anything not ending `.py`, so a junction *directory* changes nothing. That is almost
certainly why this was read as settled. But the other instrument is not safe:

```python
# codewatch.py:262-264
newest = os.path.getmtime(root)          # <-- the src/ DIRECTORY's own mtime
for name in os.listdir(root):
    if not name.endswith(".py"): continue
```

`quiet_seconds()`'s own docstring says the directory mtime is included deliberately, "because a
file CREATED or DELETED in `src/` changes the digest while every surviving file's mtime stays
old". Creating and deleting a junction there does exactly that to the mtime — and nothing at all
to the digest.

**Why it is wrong:** every drill run makes `src/` read as "written just now" to
`codewatch.quiet_seconds()`, and two consumers act on that number.

* `drill.py`'s **own** `_wait_for_a_settled_tree()` (`drill.py:16496`) waits for
  `quiet_seconds() >= STABLE_SECONDS`, and `_reread_the_breaches` uses the answer to decide
  whether a breach was "a photograph of a file mid-write". That is the whole of order
  71ae3fa7e55e's fix. The battery disturbs the measurement it then uses to grade itself, and the
  disturbance is unattributable — `drill_local_agent` is the 8th of 40 areas, so the reset is
  minutes old by the time the re-read runs, and lands inside the 180-second window whenever the
  remaining areas run fast.
* `codewatch.stale()` / `_report_if_never_settling` — the daemon-restart machinery. A drill on a
  ~10-minute cadence keeps re-arming the settling clock for every polling daemon, which is
  exactly the "a daemon that can never settle" condition
  `_a_never_settling_daemon_is_reported_not_silent` (`drill.py:12976`) was written for.

**Confidence:** high on the code path (both `codewatch` functions read directly; the two probe
sites read directly). The one step I did not execute is the filesystem behaviour — I am relying
on NTFS updating a directory's last-write time on entry creation/deletion, which is standard but
is worth one `os.path.getmtime` before and after if the coordinator wants it nailed down. If that
holds, the finding is live on every run, not latent.

---

### MINOR — the two `wiki_source` nets grade ANY exception as HELD, so a drifted stub signature reads as a pass

**Where:** `src/drill.py:7916-7926` and `src/drill.py:7958-7965`.

**What:** both end

```python
try:
    _deliberately_failing(lambda: WS.category_members(...))
    return False   # no exception -- BREACH
except Exception:
    return True    # the failure propagated -- HELD
```

**Why it is wrong:** the property is "the injected `TimeoutError` reached the caller", and the
assertion is "something raised". The stub is `_fake_api(subdomain, params, timeout=25)`, pinned
to `wiki_source._api(subdomain, params, timeout=25)` (wiki_source.py:203) as it stands today. The
day that function grows a keyword — the exact class this file records twice, at
`_cited_names_for_can_credit_a_name` (`drill.py:2025-2044`, `cachekey.load` gaining
`on_corrupt=`) and at `_partial_canary_merges` (`drill.py:6271-6279`, `canary` gaining
`available=`) — the stub raises `TypeError`, the `except Exception` catches it, and the net
reports HELD while never reaching the code under test. An `ImportError`, an `AttributeError` or a
typo in the fixture do the same. Assert `except TimeoutError`, or check the exception carries the
injected message.

**Confidence:** high; signature confirmed against `wiki_source.py:203`, and the cache key the
second net pops (`(subdomain, min_pages, hard_stop)`) confirmed against wiki_source.py:462 — that
half is correct. Not executed.

---

### MINOR — `_a_verdict_that_did_not_land_returns_nonzero`'s `not os.path.isfile(landed_file)` clause cannot fail

**Where:** `src/drill.py:8907` (fixture) and `src/drill.py:8912` / `:8920` (the clause).

**What:** the fixture deliberately creates `<blocked>/state` as a **regular file** so
`silence.write_json`'s `os.makedirs` raises. The net then asserts
`not os.path.isfile(os.path.join(blocked, "state", "drill_last.json"))`.

**Why it is wrong:** a path whose parent component is a regular file cannot be a file on any
platform, so that conjunct is True whatever `main()` does. It reads as "and the stamp really did
not land", and it is not capable of saying otherwise. The clause carrying the actual weight is
`rc_bad != 0 and said_so`; the other three (`rc_ok == 0`, `stamped`, `ok_quiet`) do real work.
Same shape as the five-clause alphabet test order 16b4f9dbecb6 collapsed to one at
`drill.py:2978-2991`.

**Confidence:** high, read directly. Not executed.

---

### MINOR — `_status_reports_i_do_not_know_as_itself` asserts over the lines that matched, not over the roster

**Where:** `src/drill.py:6413-6419`.

**What:**

```python
jobs = [j for j in ON.ALL_JOBS if j not in ("autostart.py", "overnight.py")]
if not jobs: return False
lines = [ln for ln in out.splitlines() if any(ln.strip().startswith(j) for j in jobs)]
return bool(lines) and all("UNKNOWN" in ln for ln in lines)
```

The docstring's claim is "Every roster job must be reported as UNKNOWN, and none of them as a
confident negative."

**Why it is wrong:** the universal runs over `lines`, which is whatever the output happened to
produce. A job that produces no matching line is silently dropped from the assertion, and
`bool(lines)` is satisfied by one. That is not hypothetical bookkeeping: `autostart.main()`'s
per-job loop (autostart.py:550-559) sits inside `except Exception: silence.note(
"autostart.py:status")`, so a raise partway through truncates the report — and the drill would
grade the lines printed before it and pass. Today it holds (`ON.ALL_JOBS` is
`["autostart.py", "overnight.py"] + [basename(args[0]) for STANDING] + ["feats.py --roll"]`,
rendered as `f"  {job:<16}"`, so `strip().startswith(job)` matches each one). The fix is one
clause: `len(lines) == len(jobs)`.

This is order 5ed81099fc49 / 8ab131910911's quantifier finding — "the property was never 'a gate
exists somewhere'" — arriving on the output side.

**Confidence:** high; `ALL_JOBS` and the `--status` rendering read directly. Not executed.

---

### MINOR — a docstring understates the net it describes (`FOUR ROWS`, six asserted)

**Where:** `src/drill.py:15942` (the claim) against `src/drill.py:15958-15963` (the code).

**What:** `zero_readable_bodies_is_the_thinnest_evidence_and_buys_the_least`'s docstring reads
"FOUR ROWS, because three of them are what stops this being a one-directional change" and then
names four. The return asserts **six** rows: the two extra are
`row(None, 0, rate=0.31, base=0.30)` and `row(1.0, None)`.

**Why it is wrong:** exactly the fault order b99192e41488 was filed for one net over —
`_a_broken_maintenance_guard_fails_open`'s "THE COUNT IS STATED BECAUSE IT IS CHECKABLE, and it
was wrong: this paragraph said 'Six' and listed six while `cases` below held eight". Same
direction (prose understating the code), same consequence: a reader counting the list against the
sentence concludes one arm is stale and has no way to tell which.

**Confidence:** high, both read directly.

---

### MINOR — `_coverage_reaches_unreachable`'s first clause can only decide the case where the answer comes from a docstring

**Where:** `src/drill.py:6885`.

**What:** `if "UNREACHABLE" not in (CV.report.__doc__ or "") and "UNREACHABLE" not in
_cv_report_src(): return False`, where `_cv_report_src()` is `inspect.getsource(CV.report)`
returning `""` on `OSError`.

**Why it is wrong:** `getsource` output **contains** the docstring, so whenever the second clause
is False the first is False too — it can never be the deciding clause on the normal path. The one
case where it does decide is `getsource` raising, i.e. the source could not be read at all — and
there the whole test is answered by the docstring, which is prose about code. `_code_strings` /
`_says` (`drill.py:1410-1437`) exist in this file specifically to stop prose counting as evidence
about a guard, and this net's own subject is a state that "was documented for months and
implemented nowhere". Either drop the first clause, or make a failed `getsource` an abstention
rather than a fall-back onto the docstring.

**Confidence:** medium-high. The redundancy is certain; whether the `OSError` path is worth
treating as an abstention is a judgement, so this may be a QUESTION rather than a fix.

---

### MINOR — `_a_probe_never_counts_itself` abstains silently where its sibling abstains loudly

**Where:** `src/drill.py:6844-6847`.

**What:** `hits = W.running("drill.py"); if hits is not None and any(pid == os.getpid() ...)`.

**Why it is wrong:** when `running()` answers `None` — the probe could not read the process
table, e.g. no `psutil` — the second half of the net does not run and the net returns True with
nothing recorded to say the measurement was declined. Eight fixed strings are still graded, so
the net is not empty; but the half named in the comment ("AND THE ASKER IS NEVER THE ANSWER") is
skipped in silence. `_twins_ignores_a_foreign_tree` handles the identical condition four screens
away by noting `drill.py:twins-probe-unstageable:no-psutil` first (`drill.py:8997-8999`) under a
long ruling about why an undeliverable attack must leave a record. Same condition, two
disciplines.

Note this interacts with the first MAJOR: adopting the sibling's discipline here would add
another undeclared `health.record` call and another way to halt the library.

**Confidence:** high, read directly.

---

### MINOR — several source-shape nets bypass `_SRC_OVERRIDE`

**Where:** `src/drill.py:4198` (`_no_programmatic_clear`), `:4551`
(`_publish_never_swallows_a_missing_safety`), `:8556` (`_guards_are_wired_where_claimed`),
`:12636` (`_counts_decided_by_substring`), `:12831` (`_no_new_bare_kill0_probe`), `:12908`
(`_a_module_claimed_wired_is_actually_imported`), `:15927` (`_withdrawal_takes_a_snapshot`).

**What:** each resolves `src/` as `os.path.dirname(os.path.abspath(__file__))` (or the
equivalent) rather than through `_srcdir()`.

**Why it is wrong:** `_srcdir`'s docstring (`drill.py:609-621`) presents `_SRC_OVERRIDE` as *the*
way a source-shape net can be pointed at a scratch copy of `src/` and watched refuse — "a net
nobody has ever seen refuse is not evidence of anything; it is a green light of unknown
provenance" — and `_guards_are_wired_where_claimed`'s own docstring (`drill.py:8550-8554`) says
it was lifted to module level for exactly that reason. Setting `_SRC_OVERRIDE` does not reach any
of these seven. In practice each takes a `src=`/`path=` argument so it *is* provable, and
`_a_scan_can_tell_code_from_prose_about_code` drives `_no_programmatic_clear(src=…)` that way —
so this is a stale claim about the mechanism rather than an unprovable net. One line each
(`src = _srcdir(src)`) would make the documented mechanism true.

**Confidence:** high, read directly.

---

### INFO — "WHY 57 NETS MISSED IT" still stands on the retired figure

**Where:** `src/drill.py:4346`.

CLAUDE.md's Hard Rule -1 already names this: "`drill.py` still argues 'WHY 57 NETS MISSED IT' off
the figure this sentence used to carry." Recording that I saw it and it is still there.
Measured now, statically: **467** `net(` call sites, two of which are inside `for` loops, so the
runtime count is higher again. The reasoning in the paragraph is sound independent of the number
(the fixture was two lines long, so the big-file branch was never on its path) — the number is
the only stale part, and CLAUDE.md's own remedy for this class was to stop carrying counts in
prose rather than to update them.

---

### INFO — `_ledger_redirected`'s containment assertion is a string-prefix test

**Where:** `src/drill.py:435-440`.

`if not got.startswith(os.path.abspath(root)) or got.startswith(real + os.sep)`. A sibling
directory whose name extends `root` (`/tmp/x` vs `/tmp/xy`) would satisfy the first clause. Not
reachable through `tempfile.mkdtemp`, which is why this is INFO and not a fix: `os.path.commonpath`
or a trailing-separator comparison would close it if anyone ever hands this helper a caller-chosen
root.

---

### INFO — stand-in signatures checked, all correct today

Recorded because the brief asked for it and a negative result is worth writing down. I compared
every stub the drill installs against the live function and, where it mattered, against the
actual call site:

* `chain` stubs in `_chain_done_key_follows_the_disk` (`drill.py:5258-5263`) — `extract`, `fit`
  and `write_result` all have wider real signatures than the stubs, **but** `pipeline.phase_chain`
  calls them `CH.extract(rows, workers=...)`, `CH.fit(edges, prior=0.5)`,
  `CH.write_result(edges, res, unmatched)`, which the stubs accept exactly. Correct today,
  brittle to a new keyword on any of the three.
* `collides_once(tmp, dst, expected, attempts=5)` vs
  `silence.replace_if_unchanged(tmp, dst, expected_digest, attempts=5)` — parameter *name*
  differs; all three `escalation` call sites pass positionally (escalation.py:578, 855, 1314), so
  it holds.
* `P._scan_units = refusing(path, cap)` — `scan_for_secrets` calls
  `_scan_units(p, max(1, int(max_bytes)))`, positional. Holds.
* `fake.sweep(limit=None)` vs `scout.sweep(limit=None, register=True)` — `foreman` calls
  `SC.sweep(limit=4)` (foreman.py:293). Holds today; a future `register=` would raise TypeError
  out of `FM.scout_hostless()`, which `net()` records as a breach — fails loud, not silent.
* `BH.canary` / `BH.known_present_titles` / `CK.load` stand-ins all carry `**kw` and are safe
  against new keywords, which is the repair those three sites already document.
* `HC.probe`/`null_rate`/`relevance`, `GL._take_slot`, `F.api`, `BH._load`,
  `MB.build_jobs_for_source`, `escalation._land_halt`/`_land_clear`/`_write_stopped` — exact
  matches.

### INFO — no two nets share an `(area, name)` key

`net()` stores the attack in `_ATTACKS[(area, name)]` and `_reread_the_breaches` looks it up
there; a collision would silently re-read the survivor rather than the loser, which the comment
at `drill.py:368-372` names as the hazard. Enumerated all 467 call sites by AST: every literal
name is unique, and the two computed names (inside the credential-fixture loop and the struck-off
provider loop) are unique by construction.
