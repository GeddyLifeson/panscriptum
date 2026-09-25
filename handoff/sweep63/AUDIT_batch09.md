# sweep63 batch 09 audit

Auditor scope for run63, batch 9. Read in full, start to finish, no sampling:

- `src/foreman.py`         2279 lines
- `src/codewatch.py`       1180 lines
- `src/derivation.py`       816 lines
- `src/build_terminal.py`   668 lines
- `src/zfighters.py`        536 lines
- `src/hosts.py`            424 lines
- `src/resync_roll.py`      332 lines
- `src/tuning.py`           286 lines
- `src/lognames.py`          52 lines

Total 6,573 lines, all nine read completely via the Read tool, no grep-sampling. Read-only
throughout: nothing under `src/`, `data/`, or `state/` was edited. No drill, verify_math, mutate,
publish, allsweep, or anything touching Ollama/GPU/network was run; the only execution was the
mandated `sweep_plan.record()` call at the end.

## Prior-sweep context read first

`CLAUDE.md` (Hard Rule -1, Hard Rule 0, fail-closed doctrine) was read before the modules. Then,
per the brief, `handoff/sweep61/` was grepped for these nine module names and every match was read
in full before starting: `AUDIT_batch09.md` (foreman, codewatch, derivation, manifest_builder,
zfighters, suppressions, deprecated/catalogue_local, tuning, lognames — an overlapping but not
identical roster to this batch's), `AUDIT_batch08.md` (hosts.py, resync_roll.py, among others), and
`AUDIT_batch12.md` (build_terminal.py, among others).

**The one VERIFIED finding sweep61-batch09 recorded against this roster is now FIXED.**
`codewatch.py:runs_script` (lines 374–392 in the current file) now steps over `-X`, `-W` and
`--check-hash-based-pycs` by advancing two tokens (`i += 2; continue`), matching
`whoruns.script_of`'s handling — the sweep61 finding's exact "sweep61 batch09" citation is in the
comment at line 374. No re-report; recorded here only so the fix is on record as landed.

## Overall

This is, again, an extraordinarily heavily pre-audited batch. Nearly every function in all nine
files carries a paragraph-or-more comment citing the specific prior order/sweep that found and
fixed the shape I went looking for: checks that cannot fail, fail-open guards, Hard Rule 0
truncations, races on shared files, and false comments. I read every line looking for a defect the
code's own comments do NOT already name, per the brief's instruction not to re-report a shape the
code already handles.

**No new VERIFIED or SUSPECTED findings survived verification in this batch.** Candidates I
chased down and ruled out as either already-documented or non-reproducible are listed below so the
next auditor does not re-walk the same ground.

## Findings

None. (The sweep61-batch09 finding above is closed, not open; it is not counted here as a new
finding.)

## Candidates traced and ruled out

- `foreman.py round_once()`'s "always"-remedy handling (`if did and not getattr(fn, "always",
  False): ... break`) — traced against the live `REMEDIES` table entry-by-entry. For
  `"the library's counters are moving": [reprove_pool, restart_reader]` (`restart_reader.always =
  True`), `restart_reader` runs exactly once per round regardless of whether `reprove_pool`
  succeeds: once via the "remaining always" sweep if `reprove_pool` returns `did=True`, or once as
  the next item in the ordinary `for fn in remedies` walk if it returns `did=False`. No double-call,
  no skip. Not a finding.
- `foreman.py _catalogue_batch()` — traced the `universe_size` / `off_roll` / `unnameable` /
  `frags` / `order` / `rate` pipeline against its own docstring end to end (capture universe size
  before pops; pop off-roll; pop unnameable computed over the reduced gap; rank by last-attempt
  then gap size; rate floored at 1 and ceilinged at `len(order)`). Matches the docstring's claims
  exactly; the Hard Rule 0 rotation it replaced is already the subject of the comment block above
  it. Not a finding.
- `derivation.py main()`'s deepest-chain walk and the early-return-on-cycle fix (order
  90516d53d696) — confirmed the early `return 1` on non-empty `problems` is reached before the
  non-terminating `while [p for p in LEDGER[cur]["parents"] ...]` walk can run, so a cyclic ledger
  can no longer hang the module. Matches the comment's claim. Not a finding.
- `hosts.py discover()`'s `if not res: continue` after `ex.map(work, todo)` — `work()` now returns
  a 3-tuple on every code path (confirmed by reading every `return` in `work`), so this branch is
  unreachable by construction; the comment beside it says so explicitly and calls it deliberate.
  Same conclusion sweep61-batch08 reached. Not a finding.
- `resync_roll.py`'s final "roll now: X/Y sources catalogued" line (main(), near the end) sums over
  the **local in-process** `roll` list, which this run mutated in place before calling
  `_roll.mutate()` (which re-reads the file fresh and re-applies only this run's `repairs` by
  key). In the ordinary case (this is the only writer) the local copy and the post-CAS disk state
  agree. I could not construct or observe a case where a genuinely concurrent writer would make
  them disagree without live concurrent execution, which is out of scope for a read-only audit — so
  this is filed under Questions, not as a finding.
- `tuning.py regime()`/`profile()`'s buckets-cache coupling (`_CACHE["buckets"]` read by `profile()`
  after `regime()` has just run or just served its own cache) — traced that both always come from
  the same `_CACHE` write inside `regime()`, so the label and the worker count cannot be sized from
  two different readings. Matches the comment's claim exactly (this was itself sweep61-era's fix
  for the opposite bug). Not a finding.
- `zfighters.py main()`'s Son-Goku-sheet fallback and the `--full` worksheet printer — both already
  carry their own "this used to crash / used to truncate" comments with the fix in place
  (`d.get("provenance", "")` rather than `d["provenance"]`; `textwrap.wrap` rather than `[:60]`).
  Read and confirmed present as described. Not a finding.
- `build_terminal.py`'s `esc()` discipline — checked every innerHTML sink in the `<script>` block
  (`panel()`, `selectSource()`, `selectWorld()`, `shelfmark()`) for a value that reaches the DOM
  without going through `esc()` first. All catalogue-derived strings I traced (`cat`, `endo`,
  `f.landform`, `f.climate`, `f.condition`, `f.tech`, node names via `shelfmark()`) are escaped,
  matching the two "order 3b37494e20db" / "order c000fbc3c378" comments that record these sinks
  having been closed. Not a finding.
- `codewatch.py`'s `_ledger_lock`/`_take_locked`/`_claim_restart_slot` compare-and-claim path —
  traced for a TOCTOU gap between the budget check and the ledger write; the whole point of
  `_claim_restart_slot` taking the lock around both (order stated in its own docstring, "the run
  #36 sweep") holds up under re-reading. Not a finding.

## Questions

1. **`resync_roll.py`, main(), the closing summary line** (`roll now: {have}/{len(roll)} sources
   catalogued, {total:,} entries`) — sums over the local, in-memory `roll` list rather than
   re-reading the file after `_roll.mutate()`'s compare-and-swap lands. In the single-writer case
   this is correct by construction (the local copy mirrors what `repairs` just applied on disk).
   If a second writer (another cataloguer, another resync) lands an unrelated row's `entry_count`
   change in the window between this process's initial `open(ROLL)` and its `_roll.mutate()` call,
   the printed "roll now: X/Y" figure would reflect this process's own before/after view rather
   than the true post-merge disk state — a cosmetic drift in the summary line only, since the
   actual write is the correct key-wise CAS. Worth a second pair of eyes if concurrent resync runs
   are ever scheduled close together; not something to act on from a static read.
2. **`hosts.py discover()`'s specialist test** (`r.get("verdict") in KEEP` where `KEEP = ("holds",
   "partial")`) depends on `hostcheck.score()` — a module outside this batch's scope — actually
   emitting exactly those two strings as verdicts. I did not read `hostcheck.py` in this pass to
   confirm the vocabulary still matches; if `hostcheck.score()`'s verdict spelling has drifted
   (e.g. a rename), `specialist` would silently and permanently read `False` for every candidate,
   which is the "check that cannot fail" shape Hard Rule -1 is about, and it would be invisible
   from inside `hosts.py` alone. Flagging for whoever next audits `hostcheck.py` to cross-check the
   two files' vocabularies agree.

## Summary of findings by kind

- Real bugs: 0 new (1 pre-existing VERIFIED finding from sweep61-batch09, in `codewatch.py`, is
  now fixed and confirmed fixed).
- Tautologies / checks that cannot fail: 0 new.
- Fail-open guards: 0 new.
- Caps/truncations (Hard Rule 0): 0 new.
- False comments/docstrings: 0 new.
- Dead code: 0 new.
- Questions raised: 2 (see above), neither actionable from a static read alone.
