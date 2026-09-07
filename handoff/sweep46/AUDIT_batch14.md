# AUDIT — run46, batch 14

Modules read in full, no sampling: `hostcheck.py` (1,572), `escalation.py` (1,151),
`rosetta.py` (793), `thread_integrity.py` (654), `catalogue_codex.py` (457), `genre.py` (361),
`resync_roll.py` (332), `suppressions.py` (254). 5,573 lines.

`escalation.py` read first and in full per the chain-of-command context, including the full
`clear()`/`_by_a_person_at_the_cli()`/`_land_halt` path and the OWNER-halt and MANAGER-stop CAS
loops. Confirmed by grep across `src/`: the only occurrences of `escalation.clear(`/`ESC.clear(`
outside `escalation.py` itself are in `drill.py` (dynamically-synthesised probe strings that
`_no_programmatic_clear` and `verify_math`'s AST scan are built to catch) and `verify_math.py`'s
own commentary about the guarantee. No real caller exists. `verify_math.check("escalation.clear()
has no caller anywhere in src/ -- by AST, not by grep", ...)` is present and matches the claim in
this batch's brief.

## 1. Orders filed this batch

| id | handler | sev | subject |
|---|---|---|---|
| `58cfc2b6dbc4` | OWNER | MAJOR | `hostcheck.py`: halt check goes stale across a long network probe before the destructive write |
| `d56c041a8f4d` | RUN | MINOR | `thread_integrity.py`: corrupt charter file reads identically to an absent one |

### `58cfc2b6dbc4` — the most important finding in this batch

`hostcheck.sweep(repair=True)` and `hostcheck.adopt()` both call `_assert_not_halted()` exactly
once, at function entry (`:864-865`, `:1460-1461`), before anything else happens. Both then run a
rate-limited network probe over a `ThreadPoolExecutor` against every candidate host on the roll —
`sweep`'s repair branch probes every `candidates()` host for every failing source, `adopt` does
the same for every hostless source — and only after that probing finishes does either function
reach its actual destructive write, `_land_hosts()`, which is a compare-and-swap onto
`WIKI_HOSTS.json`, one of the two files this project has ruled not reconstructible from anything
else on disk. `feats._throttle` deliberately paces some hosts (Wikipedia named explicitly)
"far slower" than others, so this window is not a formality — on the live roll (~200 sources) it
can run for many minutes.

The gate's own comment (`:860-863`) justifies the placement by analogy to `withdraw_chapters.py`:
"it asks BEFORE the probe rather than beside the write, exactly as withdraw_chapters asks before
it moves anything." Read `withdraw_chapters.main()` (`:131-156`) to check the analogy: its
`assert_clear()` sits above the argparse block, and everything between the check and the actual
`shutil.move()` calls is local filesystem work — no network I/O, a window of seconds. `hostcheck`'s
check-to-write window is qualitatively different: live, rate-limited HTTP against dozens to
hundreds of hosts. A halt raised by another process during that window — plausible on this
machine, which runs long-lived scheduled jobs (`foreman.py` runs `adopt`/`sweep --repair` on a
schedule per the module's own comment at `:1457-1459`) — is never re-checked before the write
lands.

Filed as a QUESTION FOR THE OWNER with both readings, per this batch's instructions, rather than
as a proposal to change the gate unilaterally:
  * (a) deliberate — the withdraw_chapters analogy was judged close enough and the narrow race
    is an accepted cost;
  * (b) a real gap in the plant-wide interlock for exactly the shape Hard Rule -1 exists to
    close — the check does not cover the risk window it is meant to cover.

If (b), the mechanical fix is small and does not touch `escalation.py` itself: re-call
`_assert_not_halted()` immediately before the CAS write in `_land_hosts` (both call sites), or
periodically inside the probe loop.

### `d56c041a8f4d`

`thread_integrity._charter_codes()` (`:76-98`) returns an empty set on `FileNotFoundError` (the
honest "no charter loaded yet" case) and on any other exception (a corrupt or wrong-shape
`data/CHARTER_SPINE_CODES.json`) alike — the two are told apart only by which `silence.note` key
fires internally; nothing surfaces the distinction to a reader. This is the inverse of the
doctrine this same tree applies everywhere else that matters: `escalation._read_halt_raw`
(`:502-532`) and `suppressions._load` (`:59-89`) both deliberately treat "exists but unreadable"
as strictly worse than "absent" and say so loudly — `_unreadable_halt`/`SystemHalted` in one case,
an `UNREADABLE:` line in `problems()` in the other.

Consequence: a corrupted `CHARTER_SPINE_CODES.json` silently narrows the address space
`load_thread_graph()` checks thread targets against (`addresses = _charter_codes() |
set(code_to_sources)`, `:136`), which can manufacture false `THREAD_UNRESOLVABLE` SUPERVISOR
escalations against threads that legitimately point at a childless charter Set with no source of
its own yet. This fails toward caution, not toward a silently-accepted false pass, so it is not
the top-priority fails-open shape this batch was hunting for — but it is a silent measurement
corruption feeding a release-gate module (STEP4_PLAN.md §8), and it should be visible the way
every sibling loader in this file's own neighbourhood already makes itself visible.

## 2. Everything else examined and NOT filed

**`hostcheck.py`** — the rest of the module is unusually well-defended already (many prior
`order <hash>` fixes are visible in the comments, all consistent with the code as it stands
today). Checked specifically and found sound:
  * `_assert_not_halted()` itself: fails closed on `ImportError` with a bare `except ImportError`
    (not a swallowing `except Exception`), matching `withdraw_chapters.py`'s precedent exactly.
  * `probe()`, `null_rate()`, `score()`: a failed or throttled request is `rate=None`/`base=None`
    and propagates to `UNREACHABLE`, never defaulted to `0.0` — this is the fix for the exact
    "throttle reads as a wiki that holds nothing" class of bug the module's own header describes,
    and it is applied consistently at every call site I checked (`null_rate`'s "NOT CACHED"
    comment, `score`'s `rate is None` / `base is None` branches, the `about_n == 0` branch).
  * `_land`, `_land_hosts`, all writes in `purge()` and `sweep()`: every write's boolean verdict
    is checked and a denied replace is reported as such rather than printed as success. Confirmed
    by reading every `_land(...)`/`_land_hosts(...)` call site — none discard the return.
  * `--purge --go` and `--adopt --go`/`--repair`'s halt gate placement relative to *local* file
    work (record rewrites, cache deletion) is fine — the gap identified above is specific to the
    two functions with a long network phase between the gate and the write.

**`escalation.py`** — the module the whole batch's context centres on. Read start to finish
including the parts truncated by the tool's page limit. No caller of `clear()` outside itself
(confirmed above). The CAS loops on `HALT.json` and `STOPPED.json` (`_raise_halt`/`_land_halt`,
`stop_subsystem`/`_write_stopped`, `resume_subsystem_verdict`) all read-back and verify identity
rather than trusting the CAS return alone (`_halt_file_records`, `_halt_file_cleared`), which is
correctly stronger than `replace_if_unchanged`'s own guarantee (documented as the fix for the
"both reported halt_landed: True while the file held only one fault" race). The
`escalate("OWNER", ...)`-vs-`escalate(OWNER, ...)` string/int acceptance defaults an unrecognised
level to MANAGER rather than OWNER, with the reasoning spelled out (`:243-268`) — a typo must not
be able to halt the whole library, and MANAGER is still a real, loud refusal. `resume_subsystem`'s
20-vs-`clear`'s 12-character ruling-length asymmetry is explicitly flagged in the module's own
comment as an open, undecided question rather than a documentation bug — correctly left alone
here, since resolving it either way is a behavioural change to a tested safety, not an audit
finding.

**`rosetta.py`** — no destructive, non-reconstructible write: `--mine` writes `ROSETTA.json`
*and* a `.raw.json` sibling that `--refine` (the one destructive pass) reads nothing from
directly but which lets the refined file be rebuilt by re-running `--refine` — so no halt gate is
needed by this project's own stated doctrine ("a bare sweep... is a measurement," "the writing
paths that can't be reconstructed" are what need the gate). `MINE_FLOOR` correctly guards against
a throttled pass silently shrinking the standing mine; an unreadable prior file refuses to compare
rather than treating "can't compare" as "safe to overwrite" (`:663-673`). `null`/`None`
propagation through `score`/`check`/`refine` is handled the same carefully-distinguished way as
`hostcheck.py`.

**`thread_integrity.py`** — besides the filed finding, the escalation wiring is correct: an
unreadable `THREADS.json` (wrong shape, not merely absent) raises `ThreadGraphUnreadable` and is
escalated at OWNER (`:452-465`) — matches STEP4_PLAN.md §8's own ruling, "an unreadable graph is
not an empty one," and is the fail-closed direction. Per-source `THREAD_UNRESOLVABLE` escalates
at SUPERVISOR, correctly scoped per source rather than closing the whole library. The
`_floor_verdict` ratchet (asked about explicitly in this batch's brief) correctly distinguishes
`UNRECORDABLE` (first-baseline write denied — fails the run, since every future run would
otherwise re-take the `FileNotFoundError` arm and REGRESSED could never fire) from
`held-unrecorded` (a ratchet-down write denied — does NOT fail, since the higher bar simply
stands and nothing false is claimed). Verified against `main()`'s handling of both states
(`:635-649`) — this is the write-gated-with-UNRECORDABLE-states change the batch context named,
and it is implemented correctly.

**`catalogue_codex.py`** — every `norm()` collision class (section titles, register
descriptions, manifest `(type, name)` pairs) is reported uncapped rather than silently resolved
by file order; every write (`_P.write_record_catalogue`, `_roll.update_rows`) checks its verdict
and the process exit code carries both write failures. No irreversible action in this module
(the codex source file is read-only input; the roll and record writes are both idempotent re-runs
of the same parse).

**`genre.py`** — the `top`/`cap` parameters that used to silently truncate are both now refused
(`cap is not None` raises `SystemExit` with the measured 7-source impact named) rather than
quietly accepted with a smaller default. One thing worth a future batch's attention, not filed
here because it names a module outside this batch: the comment at `:338-342` describes
`profile.build_all`'s `GENRES.json` load as falling back to a silent `{}` on a failed load,
"indistinguishable downstream from real data" — phrased as a historical defect ("the m100 tail,
2026-08-25") but I have not read `profile.py` to confirm it was actually fixed there. Flagging for
whichever batch covers `profile.py` to verify directly rather than trust the comment.

**`resync_roll.py`** — every skip class (unreadable record, wrong-shape record, record with no
`source`, roll row with no `name`, roll row with no matching record) is counted and named in the
output rather than silently dropped from the closing tally; the roll write goes through
`roll.mutate`'s compare-and-swap (key-wise merge) rather than landing a stale whole-document copy,
which is the specific defect this script exists to repair in the first place.

**`suppressions.py`** — deliberately the strictest fail-closed module in the batch: `active()`
returns nothing on an unreadable file (a detector that cannot confirm an exception is narrowed
still applies in full), while `problems()` treats that same unreadable state as a reported FAULT
rather than a silent pass — the two functions have different failure directions for a documented
reason (`active()`'s docstring: "the safe direction to be wrong in"). `suppressed()` matches
paths case-sensitively (`fnmatchcase`) specifically so a mis-cased pattern fails to match rather
than silently over-matching on Windows. No caps on stored reason text (`add()`'s comment records
the historical defect where a stored 300-char cap cut off the one clause — a scope caveat — that
mattered).

## 3. Coverage recorded

`sweep_plan.record('run46', ['hostcheck.py', 'escalation.py', 'rosetta.py',
'thread_integrity.py', 'catalogue_codex.py', 'genre.py', 'resync_roll.py', 'suppressions.py'],
batch=14)` — all eight read end to end.
