# Sweep 59 -- AUDIT batch 15

Modules read in full: | module | lines | read (top to bottom? mtime) |
| --- | --- | --- |
| src/local_agent.py | 1650 | yes, top to bottom (2 Reads) -- mtime 2026-09-13 21:33:37 |
| src/escalation.py  | 1445 | yes, top to bottom (2 Reads) -- mtime 2026-09-09 17:20:35 |
| src/corpus_db.py   | 1053 | yes, top to bottom (1 Read)  -- mtime 2026-09-13 23:41:26 |
| src/gpu_lane.py    | 684  | yes, top to bottom (1 Read)  -- mtime 2026-09-01 23:09:33 |
| src/worldseed.py   | 536  | yes, top to bottom (1 Read)  -- mtime 2026-09-14 22:14:57 |
| src/sevenfold.py   | 441  | yes, top to bottom (1 Read)  -- mtime 2026-09-06 22:39:48 |
| src/navtree.py     | 335  | yes, top to bottom (1 Read)  -- mtime 2026-08-29 23:45:38 |
| src/resonance.py   | 298  | yes, top to bottom (1 Read)  -- mtime 2026-09-09 23:04:26 |

All eight mtimes were re-checked after every module was read, immediately before writing this
report, and none had changed.

## Overall

No new DEFECTs found in this batch. All eight modules are among the most heavily audited files
in this tree -- `escalation.py` and `local_agent.py` in particular carry dozens of named,
dated, order-numbered prior fixes for exactly the failure classes this brief asks to prioritise
(fail-open gates, tautological checks, caps/truncations, lost updates, windows popping). I read
every one of those historical fixes against the current source rather than trusting the
docstrings, and did not find a regression or a new hole of the same shape.

## src/local_agent.py

### New findings
None.

### Known (already open orders)
**de265a105279 -- still accurate.** "ADDING ANY NEW MODULE TO src/ FAILS A HARD-RULE--1 SAFETY
ROW ... AND `local_agent._gates` DEMANDS verify_math AT ABSOLUTE ZERO, SO THE LOCAL MODEL LANE
REVERTS EVERY PATCH IT PROPOSES." The mechanical half (the row can now say
skipped/added_since/undetermined via `missing_detail()`) was fixed 2026-09-09 per the order's own
shift note. The owner's half -- "should an `added_since` gap fail a Hard-Rule-1 safety at all"
-- is explicitly left open in the order text with three named options, none selected. I did not
re-file it; `_gates()` at src/local_agent.py:848-878 still enforces the absolute-zero bar exactly
as the order describes, so the finding is current.

### Checked and clean
- `_safe()` (lines 445-539) and `_denied_target()`/`_protected_identities()`/`_identity_denied()`
  (542-635): all eight previously-found bypass classes (case, name-prefix, ADS, case-sensitive
  extension, unlisted directory, junction, incomplete junction fix, hard link) are closed as
  described, and `t_propose_patch` still runs the identity check (953-958) independently of
  `_safe`'s junction-only re-ask, which is the correct division of labour for a hard link (no
  spelling difference for `_safe` to notice).
- `_gates()` (740-878): the `RESULT:\s*\d+\s+passed,\s*(\d+)\s+FAILED` regex still matches on the
  captured group rather than substring-testing "0 FAILED", so "10 FAILED"/"20 FAILED" cannot
  false-pass.
- `_tool_message()` (1243-1318): every exit path re-serialises and re-checks length before
  returning; the shrink loop is bounded at 40 iterations and falls back to a named "could not be
  reduced" error rather than ever emitting unparseable JSON.
- `_achievement()`/`run()`'s four "looks like success but is not" arms (empty answer, unpaged
  truncation, zero tool calls, attempted-but-none-landed) are each gated on a mechanical
  predicate, not a reading of the model's prose, matching what their docstrings claim.
- `MAX_TURNS`/blast-radius (`_blast_ok`, 237-250): budget is charged only once a patch is about to
  actually write (line 1061), after uniqeness and `--no-apply` are resolved, matching the
  docstring's claim (order 528e5b07fded).

## src/escalation.py

### New findings
None.

### Checked and clean
- `_raise_halt`/`_land_halt`/`clear()`: compare-and-swap plus `_halt_lock()` (exclusive-create,
  fails OPEN on a stuck lock as documented) plus read-back verification
  (`_halt_file_records`/`_halt_file_cleared`) all agree with their docstrings' claimed sequencing.
  `clear()` does not retry across a digest mismatch (deliberately, unlike `_raise_halt`) -- checked
  this asymmetry against its stated reasoning and it is internally consistent.
- `escalate()`'s level-name/level-float/unrecognised-level handling (223-284) lands unknown input
  at MANAGER, never OWNER -- checked `isinstance(level, float) and not level.is_integer()` really
  is evaluated before the bare `int(level)` cast that would otherwise silently truncate it.
- `_by_a_person_at_the_cli()` frame-depth check: verified against both call sites that invoke it
  (`clear()` and `resume_subsystem_verdict()` called directly from `main()`) -- `sys._getframe(2)`
  lands on `main()` in both cases as the docstring requires, and the public `resume_subsystem()`
  wrapper is correctly excluded (an extra frame) rather than accidentally passing.
- `stop_subsystem`/`resume_subsystem_verdict`/`_write_stopped`: CAS with `STOP_CAS_ATTEMPTS`
  retries, the false-`SUBSYSTEM_STOPPED`-order cleanup on an unlanded stop, and the
  fail-closed `__unreadable__` handling in `_read_stopped` (including the "wrong shape, not just
  unparseable" fix) all read correctly against their own documented history.

## src/corpus_db.py

### New findings
None.

### Checked and clean
- `rebuild()`'s three-sentinel scheme (`SPINE_LOOKUP_FAILED`, `HOST_LOOKUP_FAILED`, and the
  numeric-column caveat routed through `meta` instead) -- verified the `source` INSERT's 10
  placeholders line up 1:1 with the 10-column schema, and `entry`/`evidence` inserts likewise (9
  and 7 columns respectively).
- `freshness()`'s deletion-check (`record_files` in meta vs. current glob) and its "unavailable"
  vs. "compared" distinction: every return path sets both `deletion_check` and `deleted_records`,
  none silently default to "no deletions".
- `CANNED`'s nine queries: confirmed none carries a `LIMIT` and the `worst_cited` /
  `below_floor_cited` split correctly avoids NULL-sorts-first by testing `cited IS NOT NULL`
  explicitly rather than relying on the floor alone.
- `connect()`'s `path=None` late-binding fix: `DB` is read at call time via the default arg
  pattern, not captured at import.

## src/gpu_lane.py

### New findings
None.

### Checked and clean
- `_alive()`'s Windows `OpenProcess`/`GetExitCodeProcess` path distinguishes
  ERROR_INVALID_PARAMETER (dead) from ERROR_ACCESS_DENIED (alive, not ours) from any other
  failure (alive, per the documented "unknown -> alive" fail-open policy).
- `_take_slot()`'s three-way return (path / False-busy / None-unarbitrable) is honoured
  correctly by `lane()`'s queue loop (605-618): `None` breaks immediately rather than polling out
  the full `SLOT_LEASE_SECONDS`.
- `foreground_active()`'s unconditional removal of an unreadable claim file (no mtime-staleness
  gate, unlike `_take_slot`'s handling of unreadable slot files) is safe rather than a bug: `fg.*`
  claims are written via `_write_claim`'s temp-file-plus-`replace_retry`, which is atomic, so
  there is no window in which a partially-written claim file exists on disk to be mistaken for a
  fresh one -- unlike slot files, which are written via a direct `os.open(O_CREAT|O_EXCL)` +
  `json.dump` with a real partial-write window that `_unreadable_and_stale`'s mtime check exists
  to protect. Confirmed by re-reading both write paths side by side.
- `_slot_count()`'s `auto`/`0`/negative handling: `n <= 0` falls through to the next source
  rather than being clamped up to 1, matching the docstring's claim that `max(1, 0)` used to
  silently serialise the whole lane.

## src/worldseed.py

### New findings
None.

### Known concurrent activity (per brief)
The `_BAD_CHARS` module-level guard (lines 67-69) is one of tonight's run #59 insertions named in
the brief ("Known concurrent activity tonight") -- present, placed after the stdlib imports and
before `HERE`/`sys.path` setup, does not appear to break anything (it reads its own `__file__`,
which resolves correctly whether run as a script or imported).

### Checked and clean
- `to_options()`'s band-parsing three-way (`ok`/`unparsed`/`out_of_range`, each with its own
  `band_provenance` value) -- confirmed the `unparsed` arm no longer shares a `tier=0` with a
  genuinely-unassayed world without a distinguishing field, per order 475a06c19374.
- `build_all()`'s `limit is not None` guard (vs. the old falsy-`limit=0` bug) checks before the
  append it guards, not after.
- `_first()`'s seeded-fallback hashing and the ONOMASTICON/CONTINUITY_GROUPS read-failure
  reporting into `LAST_BUILD` (module-level diagnostic, not a second return value) -- confirmed
  `reg_by_group` is built row-by-row inside the try so one malformed row costs only its own
  group's register, not the whole read.

## src/sevenfold.py

### New findings
None.

### Checked and clean
- `shelve()`/`seams()`'s window-plus-weaker-half-of-median cut rule -- re-derived by hand against
  the docstring's three-row measurement table (old / window-only / window+median) and the logic
  in the function matches the description (candidates restricted to `g[0] <= ceiling` before the
  per-boundary window search).
- `build()`'s `UNSHELVED` accounting: sources present in `by_source` (from `worldseed.build_all()`
  over `pipeline.records()`) but absent from the resonance graph's `coords` are counted and named
  via stderr rather than silently dropped by the old bare `continue`.
- `main()`'s write-denial handling for `SEVENFOLD.json`: `landed` is checked and a non-zero exit
  code follows a denied replace, matching the sibling fixes cited in the comment.

## src/navtree.py

### New findings
None.

### Checked and clean
- `sources_under()`'s digit-prefix bug (order re: "0.1.2" vs "0.1.20") -- confirmed both
  `startswith` arms now require the `.` separator on both sides.
- `register_for()`/hyperverse-grounding tie-breaks: both now use `(count, name)` as the `max()`
  key rather than a bare `max(set(...), key=count)`, closing the hash-order non-determinism the
  comment describes (measured "75 of 734 nodes renamed" before the fix).
- `audit()`'s child-sum check skips (rather than KeyErrors on) a child key absent from `nodes`,
  and separately reports that same absence as its own problem line.
- `main()`'s exit-code paths: a denied audit-record write, a denied tree write, and a read-only
  run reporting problems all correctly return 1 rather than always 0.

## src/resonance.py

### New findings
None.

### Known (already open orders)
**f467f662be4b -- still accurate, and stated in the module's own docstring rather than filed
separately here.** `hodge_decompose` and `resonance_strength` have zero production callers;
`incomparability_rate`/`dominates` are exercised only by `verify_math`'s unit tests. The module
docstring (lines 40-73) already carries this finding in full, including the consequence that
`custodes.convene()`'s Threnody curl-veto never actually fires because nothing supplies it an
eta. Not re-filed as a new finding.

### Checked and clean
- `hodge_decompose()`'s Gauss-Seidel convergence fix (in-place per-node update within a sweep,
  `tol`-gated stop, `converged: False` returning `eta: None` rather than a wrong number) -- traced
  the docstring's STAR/BIPARTITE/PATH4 measurements against the loop body and they are consistent
  with Gauss-Seidel semantics as implemented.
- The "no evidence" vs. "perfectly consistent" distinction (`no_evidence` flag) is preserved on
  both the empty-`nodes` and the `total == 0` (all-zero-flow) paths.
- `incomparability_rate()`'s UNMEASURED/TIED/INCOMPARABLE three-way split, and the uncapped
  `examples` list (no `[:5]` truncation) -- confirmed against Hard Rule 0.

QUESTIONS: 0
