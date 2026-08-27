# run35, wave 2, batch M1 -- audit notes

Fifteen orders worked. Owned files touched: `src/overnight.py`, `src/autostart.py`,
`src/dashboard.py`, `src/allsweep.py`. Nine had their real fix in an owned file and were closed;
one was closed as DISPROVED (`binding_health.py`, not owned regardless -- an earlier batch had
already fixed the exact defect); one more was closed as DISPROVED after a direct grep of the
current source (`autostart.py`'s silence.note tags -- already content-labelled, no numeric tags
remain); four were verified true against current source and left open because their real fix
lives in a file this batch does not own or may not edit (`scout.py`, `feats.py`,
`verify_math.py`, `local_agent.py`) or because the fix is a design decision the orders and this
batch's own rules say not to make unilaterally (the redundant `pipeline` start/run in
`overnight.py`). One of the four (`scout.py`) was accidentally closed via `--resolve` mid-session
and re-filed through `workorders.file_order()` with a fresh id (`e5a4928f2ae9`, same code/where)
so the queue would not silently lose a real, unfixed finding -- see that order's paragraph below.

**1cdbdbc3d4fa**. FIXED. `overnight.watch_report()` counted high-severity findings with
`.lower() == "high"` but sorted with a case-sensitive `== "high"` three lines later, so a finding
the model stored as `"High"` (overwatch.py does not normalise severity on write) would be counted
into the `(N high)` headline and simultaneously sort as not-high. Fixed the sort key to lower the
same way the count does (overnight.py, in `watch_report()`). The root cause -- `overwatch.py`
storing un-normalised severity -- is in a file this batch does not own and is unfixed; the
internal count/sort inconsistency that made it visible is closed.

**3493d9074fd1**. DISPROVED. `binding_health.run()` truncated `hosts[:limit]` and landed a
partial result over the whole-estate report with no marker, per the evidence. Read the current
`run()` (src/binding_health.py:522-598): when `only`/`limit` narrow the sweep it now merges each
probed host's fresh record into the PRIOR `BINDING_HEALTH.json`, keeps every unprobed host's old
verdict, sets `checked` to the length of the merged whole file, and writes a `partial_pass`
marker naming exactly which hosts were probed. Comment dated 2026-08-26 -- an earlier batch had
already landed this fix. Not an owned file regardless; verified only, no edit.

**43d5bcfcdd19**. FIXED. `autostart.py --status` printed a hand-kept six-job tuple that had
already drifted from `overnight.STANDING`/`ALL_JOBS` -- no entry for `pipeline`, and
`"feats.py"` where the roster's own entry is `"feats.py --roll"`. Replaced the tuple with a loop
over `overnight.ALL_JOBS`, skipping `autostart.py`/`overnight.py` since the report already names
those two lines above as the launcher and supervisor. Confirmed `overnight.running()`'s
`_cmd_is_running` already treats a fragment-with-argument like `"feats.py --roll"` correctly.

**4f99eb0f78f1**. LEFT OPEN (real fix not owned). `scout.py`'s LOG-read except handler carries
`silence.note("scout.py:241")`, and line 241 today is unrelated code, not the swallow it names --
every sibling handler in the same file already uses a content label. `scout.py` is outside this
batch's owned-file list. Accidentally closed via `--resolve` mid-session (an early-session
mistake, caught immediately); re-filed through `workorders.file_order()` with the same
code/where, landing as a fresh id `e5a4928f2ae9` so the finding stays in the open queue for
`scout.py`'s owner. The correct fix is a one-line rename to a content label, e.g.
`scout.py:log-history-unreadable`.

**5d14e90b5043**. LEFT OPEN (design decision). Confirmed live: `pipeline` is in `STANDING`, the
keeper re-asserts it every 300s, it is started backgrounded at the top of the cycle, and `run()`'s
basename guard means the LATER, ordered `run("pipeline", ...)` call (whose comment promises it
"sees the evidence the reader just produced") almost always finds pipeline already running and
returns `"already-running"` without ever blocking. The order itself says "decide which of [the
two invocations should survive]" -- exactly the kind of deliberate-design judgment call this
batch's rules say not to make. Left open with the finding confirmed true.

**6f8a12503285**. FIXED. `overnight.py`'s module docstring still stated the GPU-serial rule
("only one GPU stage runs at a time") as one of the supervisor's three rules, while the body
starts `pipeline` backgrounded next to the reader under a comment saying the rule is obsolete.
Rewrote the docstring paragraph to state the current reality (reader cascade-first since
2026-08-25, GPU-serial no longer enforced) instead of the stale rule.

**71aef747c9e7**. LEFT OPEN (real fix not owned). Confirmed: `feats.py`'s `_RATE_LIMITED[host]`
(line ~299) and `_CAP_BOUND["aplimit"]` (line ~518) are read-modify-written with no lock held,
unlike the `done` dict in the same function which the existing `lock` does guard, and `roll()`
launches with `--workers 12` by default from `overnight.py`. `feats.py` is not in this batch's
owned-file list.

**873900f156d1**. LEFT OPEN (real fix not owned/editable). Confirmed: `verify_math.py` still
cites `foreman.py:315`/`foreman.py:385` for `restart_reader`/`kill_stalled_job`; the real
definitions are at different lines today (368/413 or later, having moved again since the order
was filed) and 315/385 point at unrelated code. `verify_math.py` is on this batch's explicit
do-not-edit list.

**8d0ec897cb0b**. LEFT OPEN (real fix not owned). Confirmed: `local_agent.py`'s patch audit log
entry is only constructed and appended after six early-return refusal paths (denylist,
writable-surface allowlist, protected-region prefix, blast cap, find-count check), so a model
that only ever gets refused produces an empty `patches` list -- no record that anything was even
attempted. `local_agent.py` is on this batch's explicit do-not-edit list.

**c1f5ad96dfbe**. FIXED. `dashboard.RE_READ` still matches `read.py`'s current progress line
exactly (tested with a synthetic line) -- the defect is the fragility itself: a future format
change makes `_tail_match` return `None`, indistinguishable from the reader being idle. Gave
`_tail_match` an optional `hint` substring; when the tail contains the hint but no line matches
the full regex, it calls `silence.note("dashboard.py:tail-format-mismatch:<logfile>")` instead of
returning `None` silently. Wired `_read_row` with `hint="chunks/s"`. Also corrected the
line-56 comment that had called the silent-vanish failure mode "safe."

**c49e3871ac60**. FIXED, same edit as 1cdbdbc3d4fa. `watch_report()` announced
`len(open_f)` findings then printed only `sorted(...)[:top]` with `top=6` and no "N more" line --
the identical defect already removed from `foreman_report`'s `did[:5]` earlier in the same file.
Dropped the `[:top]` slice (now prints every open finding, ranked high-first) and removed the
now-unused `top=` parameter since `watch_report` has exactly one caller and it used the default.

**cb9cc3267474**. DISPROVED. The evidence cited stale numeric `silence.note("autostart.py:131")`
/ `:139` / `:174` tags. `grep -n 'silence.note("autostart.py:[0-9]' src/autostart.py` returns
nothing: all seven call sites already use content labels (`log`, `alive`, `twin-import`,
`twin-query`, `twin-cmdline`, `watch`, `status`) -- matching the proof text already recorded
against the closed order `da8939f1ebc2`, which shows `silence.note('autostart.py:alive')` at the
same site. An earlier, unrelated fix (the `supervisor_alive` tri-state rework) had already
renamed these. No edit made.

**d0ff339b7138**. FIXED. `allsweep.py`'s module docstring said "Three tiers" (IMPORT, VERIFY,
RECONCILE) and closed "Nothing here writes," while `main()` actually runs five tiers (IMPORT,
LINT, VERIFY, ESTATE, RECONCILE, confirmed by reading every tier's print banner) and lands
`data/ALLSWEEP.json` via `silence.write_json`. Rewrote the "WHAT IT DOES" section to list all
five tiers -- naming that LINT gates the exit status alongside VERIFY, since
`foreman._checks_pass` depends on that list -- and replaced the writeless claim with an accurate
one.

**d757d03bef8b**. FIXED. Confirmed `feats.py`'s roll progress line still matches `dashboard.
RE_ROLL` exactly, and the "refused" counter is deliberately printed on its own separate line
rather than folded into the matched line -- confirming the order's premise that the two files
cannot see each other's format strings. Since `feats.py` is not owned, applied the same
decoupling used for c1f5ad96dfbe entirely inside `dashboard.py`: `_roll_row` now calls
`_tail_match(..., hint="M chars")` so a future break in `RE_ROLL` gets its own ledger entry
instead of reading as the roll being idle.

**fef23be535cf**. FIXED. `dashboard._watch()` ranked and truncated the swallowed-failure table
with `sorted(...)[:6]`, five lines below the `findings` list that had already been fixed for the
identical cap on 2026-08-24. `state/failures.json` held 25 distinct tags at filing time (18
today); either way, rank 7+ had no identity on the page though `swallowed_total` still published
the magnitude. Dropped the `[:6]` slice, keeping the ranking. Checked the page's JS renderer
(`w.swallowed.forEach`) has no hard-coded length assumption.

## Checks proposed

`handoff/run35/checks_M1.py` -- six standalone `check_*` functions, all run and passing against
the fixed source: the watch_report count/sort/no-cap behaviour, the autostart status roster,
the overnight docstring/body agreement on GPU-serial, the dashboard `_tail_match` format-mismatch
note (with an explicit before/after `health.LEDGER` cleanup so the check itself leaves no test
artifact in the live `state/failures.json`), and the allsweep docstring/tier-list agreement plus
the uncapped swallowed table.

## Incident: two orders briefly mis-resolved and self-corrected

Mid-batch, `4f99eb0f78f1` (scout.py) was closed via `--resolve` before recognizing it was a
"real fix lives in a non-owned file" case rather than a "fixed" or "disproved" one. Caught
immediately, before any further orders were processed. Recovered by reading the closed record
back out of `state/workorders_closed.jsonl` and calling `workorders.file_order()` with the
identical `code`/`where` (which content-addresses to the same fault), landing a fresh id
(`e5a4928f2ae9`) back in the open queue rather than hand-editing `state/workorders.json`.
Also worth recording: an early debugging pass of the `_tail_match` hint fix (run directly via
`python -c`, before the formal `checks_M1.py` existed) left two test-artifact keys in the live
`state/failures.json` (`silent:dashboard.py:tail-format-mismatch:bad.log:None` and one with a
tempfile name) because `silence.note()`'s `atexit`-registered flush fired on the debug process's
own exit. Found by re-reading the file before writing the checks script, removed with a
read-modify-write through `silence.write_json` (never a bare truncate), and the checks script
itself was then written to pop its own test key back out of `health.LEDGER` before returning, so
running it again leaves nothing behind.
