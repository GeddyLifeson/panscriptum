# Sweep 58 — batch 11 audit

Modules read in full, top to bottom (line counts from `wc -l` at read time):

- `src/overnight.py` — 2004 lines
- `src/codewatch.py` — 1146 lines
- `src/generate.py` — 977 lines
- `src/address_space.py` — 673 lines
- `src/worldseed.py` — 532 lines
- `src/hosts.py` — 424 lines
- `src/navtree.py` — 335 lines
- `src/tempus.py` — 297 lines

Open queue checked first via `workorders.open_orders()` (458 rows) before any file was read, per
the brief's method. Every KNOWN tag below was independently re-verified against the source
actually on disk, not assumed from the order text.

---

## src/overnight.py (2004 lines) — this shift's changes audited hard

**KNOWN 633832bdae90 (OVERNIGHT_RC17_RESTARTS_COUNT_TOWARD_IDLE_LIMIT) — FIXED, verified.**
`BUSY_STATUSES = ("already-running", "manager-stopped", "probe-blind", "rc=17")` (line 995) and
`busy_statuses()` (998-1002) now include `"rc=17"`. In `main()`'s cycle loop, `statuses` from
`run("read", ...)` and `join(roll, ...)` are filtered through `busy_statuses(statuses)` (line
1926) before the idle-vs-busy branch at 1927. A cycle where `read` exits `rc=17` (a designed
codewatch restart) now lands in `busy`, resets `idle = 0`, and does not count toward
`IDLE_LIMIT`. This is exactly the fix the order asked for and it is wired into the one branch
that matters.

**DEFECT MINOR — overnight.py:main(), the halt-unreadable arm, line 1984 — a `str(e)[:120]`
cut survived the very cleanup this shift did six times over in this same file.**
```python
except Exception as _halt_unreadable:
    silence.note("overnight.py:halt-status-unreadable")
    _halted = True
    _rec = {"code": "HALT UNREADABLE (%s: %s)"
                    % (type(_halt_unreadable).__name__,
                       str(_halt_unreadable)[:120])}
```
This is inside the `IDLE_LIMIT` branch, reached when `escalation.status()` itself raises while
the supervisor is deciding whether an idle library is broken or halted (line ~1976-1988). Every
other `except ... as e` site in this file that used to write `str(e)[:N]` was UNCUT this shift —
grep confirms six `# UNCUT (Hard Rule 0, order fe99e57e1993)` markers at lines 752, 847, 1213,
1240, 1351 and 1447, and zero remaining `str(e)[:` patterns anywhere else in the file. This is a
seventh site of the identical shape that the sweep's own remedy missed: `str(_halt_unreadable)`
is truncated at 120 characters before it is folded into `_rec["code"]`, which is then the whole
of what the single log line at 1986-1988 tells a person about why the halt status could not be
read — in the one branch whose entire job is diagnosing why the plant-wide interlock is
unreadable. **Failure scenario**: `escalation.status()` raises an exception whose `str()` is
longer than 120 characters (e.g., a JSON parse error naming a long malformed fragment, or a
chained exception's default `str()`); the log line and the evidence dict both carry only the
first 120 characters, silently dropping the rest of the only diagnostic available for what is
otherwise a very rare, high-stakes code path. **Remedy**: drop the `[:120]`, matching the six
sibling sites already fixed this shift.

**KNOWN fe99e57e1993 (UNMARKED_NAME_CUTS_SWEEP44), overnight.py-specific sites — FIXED.** All
six of this file's `str(e)[:N]` cuts (previously at old-numbering :569, :658, :940, :965, :1056,
:1150) are now whole, each marked `# UNCUT (Hard Rule 0, order fe99e57e1993)` at `run()`,
`join()`, `coverage_snapshot()`, `preflight()`, `safety_drill()`, `write_status()`. (The order
also names sites in backfill.py, catalogue_web.py, cleanup.py, weave.py, tiers.py, policy.py,
completeness.py, repass_bands.py — outside this batch and not re-verified here.)

**KNOWN d2d4ff880570 (A_TWENTY_HOUR_JOB_IS_LAUNCHED_AS_A_CHILD_OF_A_ONE_HOUR_SHIFT) — still
open, unchanged.** `mutate.py` is still named nowhere in `overnight.STANDING` or `ALL_JOBS`
(grep confirms zero hits of "mutate" in overnight.py outside two unrelated comments about
sandboxed process detection). `codewatch.py`'s `EXEMPT` dict now documents the reasoning in full
(see below), but overnight.py itself is unchanged: the mutation pass still is not scheduled,
restarted, or made a citizen of any roster here.

**KNOWN 5bb12b398783 (SWEEP54_QUESTIONS_FOR_A_RULING), item 1 — still present, unchanged.**
The prose gate at line ~1798 (`if os.path.exists(manifest) and _prose_enabled() and drill_rc !=
1:`) still treats `drill_rc is None` (drill did not run this cycle) the same as `drill_rc == 0`
(drill ran and found nothing breached) — both let prose start. This is the same question sweep
54 filed; not re-argued here since nothing here changed it.

Nothing else found in this module beyond the one DEFECT above and the KNOWN items. Checked:
every `except` arm for silent/fail-open shapes, every spawn site's singleton guard, the
compare-and-swap-shaped `_ledger`-adjacent logic (none in this file — the restart ledger lives
in codewatch.py), all `[:N]` slices (only the six now-fixed sites plus the one still-capped
site above), and the full main() cycle/idle loop.

---

## src/codewatch.py (1146 lines) — this shift's changes audited hard

**KNOWN 5d0fa30e4b09 item 1 (the watch did not descend into subdirectories) — FIXED, verified.**
`_py_tree()` (236-265) now `os.walk`s `root` at any depth, pruning `__pycache__`, and raises the
first collected `OSError` if any directory could not be listed (so an unlistable subtree refuses
the whole fingerprint rather than silently omitting it — consistent with `fingerprint()`'s
existing "None is not unchanged" rule). Both `fingerprint()` (268-290) and `quiet_seconds()`
(293-337) now walk the same tree via `_py_tree`, so `src/deprecated/catalogue_local.py` and any
other nested file is now covered by the fingerprint and the settle-time calculation. Confirmed
by reading `_py_tree`'s `os.walk(root, onerror=errors.append)` call and the post-walk
`if errors: raise errors[0]`.

**KNOWN 093a35335c68 (POLL_STAMP_CONTAMINATED) — the measured failure mode is FIXED; one
residual edge is a QUESTION, not demonstrated.** `last_polled()` (972-985) now returns the poll
age only when `last_poll_record()`'s `_poll_pid_alive(pid, at)` (892-948) reports the writing
pid is alive AND started at-or-before the stamp time (guards a recycled pid). This closes the
measured incidents the order describes ("pipeline read 'last polled 9 min ago' off the drill's
own pid while no pipeline ran" — the drill's pid is dead by the time such a report is read, so
`_poll_pid_alive` now correctly returns `False`/`None` and `last_polled` returns `None`,
rendering "not known" instead of a false-fresh reading).

**QUESTION** — the fix checks only pid liveness and start time, not process identity (e.g. its
command line). If a probe that deliberately calls `codewatch._stamp_poll("pipeline")` (or
`exit_if_stale("pipeline")`) under the real job's name is READ from `last_polled("pipeline")`
**while that probing process is still alive** (in-process, before it exits), the stamp would
still read as a live, fresh poll — because the pid genuinely is alive, just not actually running
the pipeline job. I could not establish from this batch's modules whether such a window is
reachable in practice (the calling probe's identity and lifetime are drill.py's concern, which
is out of this batch and is being edited by other agents this shift per the brief). Filed as a
question because the consequence is plausible but not demonstrated against source I was able to
read this shift.

**KNOWN d2d4ff880570 — EXEMPT gained mutate.py this shift, documentation only.** `EXEMPT["mutate.py"]`
(165-172) now records, with full reasoning, that a mutation pass is one-shot, detached,
~20 hours, sandboxed, and on no roster, so `rc=17` would kill a pass nothing relaunches. This is
a register entry (the module's own docstring: "THIS IS A REGISTER, NOT A GUARD... exits nothing
and refuses nothing") and does not change the underlying gap the order names — see the
overnight.py entry above.

Nothing else found in this module. Checked: `coverage()`'s roster union logic for double-
counting or drops (none — `feats.py`/`autostart.py`/`overnight.py` all resolve to exactly one
state row each, traced by hand), the ledger's file-lock-based mutual exclusion in
`_ledger_lock`/`_take_locked`/`_claim_restart_slot` (correctly serialised, fails safe toward
"proceed unlocked" only when the lock cannot be obtained at all, matching its own documented
trade-off), `runs_script`'s `-m`/`-c` handling, and `stamp()`'s retry-then-escalate shape. No new
`[:N]` caps; the one truncation in the file (`h.hexdigest()[:16]` in `fingerprint()`) is a hash
used purely for equality comparison, not a disclosed roster or listing, so it is not a Hard
Rule 0 cut.

---

## src/generate.py (977 lines)

**KNOWN 1e6f99e54b25 (CORPUS_WRITERS_WITHOUT_A_HALT_INTERLOCK) — still open, verified.** `grep
-n "escalation\|assert_clear" src/generate.py` returns zero hits. `main()` checks only the prose
gate (`prose_gate.assert_gate_open`, layer 2) and depends on `overnight.py` calling this script
only when `drill_rc != 1` (layer 3, the mitigation `overnight.py`'s own comment names at
~1724-1731) — but nothing inside `generate.py` itself asks `escalation.assert_clear`, so a
hand-run or a stale caller still reaches a model call with no halt interlock of its own. Order
still accurate as written.

**QUESTION** — `catalog.json`'s read-modify-write in `main()` (loaded once near the top, mutated
in memory, written incrementally every 5 completions and again at the end) has no compare-and-
swap and no singleton lock of its own; it relies entirely on `overnight.start()`'s `running()`
guard to prevent two `generate.py` processes from running at once. A hand-run started alongside
the supervisor's own "prose" job (or a `running()` false-negative, several of which this same
sweep's `overnight.py` docstrings document as historical incidents for other jobs) would let two
processes each read an earlier `catalog.json`, generate different chapters, and have the
later-finishing process's periodic/final save silently discard the other's newer entries — a
classic lost update. I could not demonstrate this is currently reachable (no known `running()`
gap for `generate.py`/`"prose"` specifically), so this is a question rather than a defect.

Nothing else found. Checked: `strip_think()`'s three-shape stripping, `ChapterRefused`'s full-
list-plus-short-sentence split (a disclosed cut, not a Hard Rule 0 violation — full lists always
survive under their own keys), the P8 meta-language gate's fail-closed `ImportError` handling,
`save_raw`/`compress_store.store` atomic-write-and-report paths, and the final-write exit-code
logic.

---

## src/address_space.py (673 lines)

Nothing found. This module is heavily self-documenting about its own past defects (five stale-
docstring/hand-typed-number incidents, all now sourced live from `TIERS.json`/`_tier_counts()`);
checked `_bits()`, `FIELDS`/`WIDTHS`/`TOTAL_BITS` derivation, `pack()`/`unpack()` round-trip
(raises rather than wraps), `_hash_offsets()`'s floor-preserving derivation and the `HASH_BYTES`
overflow guard, `shelfmark()`'s charted-vs-drawn field handling, and `main()`'s atomic
`SHELFMARKS.json` write with its denied-write exit code. No new caps, no swallowed exceptions
that report a false positive, no stale citations found (the file states citations as function
names rather than line numbers by design).

---

## src/worldseed.py (532 lines)

Nothing found. Checked `_first()`'s attested-vs-seeded provenance tagging, `to_options()`'s band
parsing (unparsed vs out-of-range vs ok, each separately provenance-tagged per order
475a06c19374), `build_all()`'s onomasticon/continuity-group failure reporting (both loudly
distinguished from a genuinely uniform catalogue, per order ef19733afaa7), the `limit is not
None` fix, and `main()`'s atomic `WORLDSEEDS.json` write with duplicate-designation reporting
and denied-write exit code. `KNOWN 40e98eed6870`-referencing marker at line 237 (the "primitive"
tech tier, mark-and-keep ruling) reconfirmed present and consistent with the ruling it cites.

---

## src/hosts.py (424 lines)

**KNOWN 3fb312a72435 (SWEEP35_FINDING: hosts.py has no caller anywhere in the pipeline) — still
open, reconfirmed.** `grep -rln "hosts_for(\|hosts\.primary_host\|^import hosts\b"` across
`src/*.py` outside `hosts.py` itself returns `descending_ladder.py`, `drill.py`, `onomast.py`,
`scale_theories.py` — but reading each hit shows all four are either PROSE describing that
`hosts.py` is unwired (descending_ladder.py:41-45, onomast.py:449-451, scale_theories.py:25-29,
all measured "2026-09-08" and explicitly naming order `3fb312a72435` as still open) or drill.py's
own test fixtures/comments about testing `hosts.add`'s CAS behaviour and a past incident where
"hosts.py was imported NOWHERE" (drill.py:15653-15654). None is a real production import of
`hosts.hosts_for`/`primary_host`. The order is still accurate.

Nothing else found. Checked `add()`'s compare-and-swap (`digest_of` taken before `_load`, and
`replace_if_unchanged` against that digest, retried up to 5 times — a stale pre-read digest can
only cause a spurious retry, never a lost update, since a concurrent write makes the later CAS
check fail and loop back to a fresh read), `_load()`'s absent-vs-corrupt distinction, and
`discover()`'s per-source candidate-count bound (already fixed in a prior sweep per its own
comments, re-verified against source: the bound applies only to `spec`, never to `grounded`).

---

## src/navtree.py (335 lines)

Nothing found. Checked `sources_under()`'s path-prefix matching (the `+ "."` fix on both arms,
order-referenced m11, re-verified correct), `register_for()`/the hyperverse-naming loop's
deterministic tie-breaks (order m41, both now keyed on `(count, name)` rather than raw
`max(set(...))`), `audit()`'s child-sum/world-count cross-check, and the write/no-write exit
code logic (`--write` refused when `problems` is non-empty; a denied audit-record write forces
exit 1 even with no problems, matching its own stated reasoning). The module documents itself as
currently unreachable from any other script in `src/` ("LATENT today") — this is the module's
own accurate self-report, not a new finding.

---

## src/tempus.py (297 lines)

**KNOWN 7099a092abd3 (BATTERY_IS_THE_ONLY_CALLER_OF_THIRTEEN_PUBLIC_FUNCTIONS), tempus.py's
four named functions — still accurate, reconfirmed.** `grep` across `src/*.py` for
`retrocausality_beta`, `contemporaneous`, `is_present_at`, `prescience_horizon_bits` shows
callers only in `verify_math.py` (the battery) plus one hit for `retrocausality_beta` in
`derivation.py:196` — read and confirmed to be a documentation table entry
(`"retrocausality_beta": Q(DERIVED, "structural constant + log2(1 + span)", [...])`), not a
function call. All four functions remain called only from the test harness.

**KNOWN 1a9c237dda4d and 0291835411d9 (dead-code mark-and-keep rulings for `concordance_now`
and `DEGENERATE_TIME`) — reconfirmed accurate.** `concordance_now` has zero hits anywhere
outside its own definition (fully dead, marked and kept per ruling). `DEGENERATE_TIME` now has
exactly one reader, `verify_math.py:861`, matching the module's own comment that the order's
premise ("only this definition") is out of date but the underlying drift (its two closed-shelf
names are separately re-stated in `loop_report()`'s prose) still stands.

Nothing else found. Checked `apparent_lag_years()`'s uniform return shape (order e3a52d3f20b5),
`rung_description_length()`/`band_resolution()`'s derivation from `BAND_EDGES` with no invented
constants, and `prescience_horizon_bits()`/`retrocausality_beta()`'s non-positive-input guards.

---

## Coverage stamp

Recorded via `sweep_plan.record("run58", [...], batch=11)` for exactly the eight modules listed
at the top of this file, all read in full.
