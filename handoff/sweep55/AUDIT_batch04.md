# AUDIT — sweep run55, batch 04

Modules: `mutate.py`, `catalogue_web.py`, `gpu_lane.py`, `withdraw_chapters.py`, `hosts.py`,
`catalogue_models.py`, `resonance.py`, `lognames.py` (6,270 lines, all read line by line).

Nothing under `src/`, `data/`, `state/` or any ledger was executed or written. Every citation
that pointed outside this batch was checked by READING the cited file, and each such
cross-batch check is labelled as one below so the coordinator can confirm it against the batch
that owns the file.

---

## 1. `mutate.py` (3,197 lines)

Read in full, top to bottom. Traced by hand: the lock lifecycle (`active` / `_lock_acquire` /
`_lock_release` / `_hold_lock`), the mutation generator (`_mutations`, `_spot`, `_between`,
`_col`, `_token_pos`, `_fallback_spot`), the sandbox builder, the reaper, the baseline/drift
machinery (`baseline`, `_refresh_baseline`, `red_gates`, `unusable_gates`, `could_not_judge`,
`hang_confirms_a_kill`), the per-mutant judging loop, `file_orders`, and both CLI paths
(`main`, `_session`). The two specific questions in the batch brief are answered first.

---

### ANSWER TO THE BRIEF'S FIRST QUESTION — order `e4caaebcbe18` is HALF right, and its
### conclusion is WRONG for `publish.py` and RIGHT for `drill.py`

**The half that is right.** `active()` (src/mutate.py:207-233) genuinely never looks at
`sandboxed`. It returns `(False, None)` on FileNotFoundError, `(True, {"unreadable": True})` on
an unparseable or non-mapping record, `(False, rec|stale)` when the recorded pid is an int and
dead, and `(True, rec)` otherwise. The word `sandboxed` appears nowhere in it. That is by
design: `_lock_acquire` writes the key at src/mutate.py:271 under a comment that explicitly
tells *readers* to fail closed on it, i.e. the decision is delegated to the consumer.

**The half that is wrong — `publish.py` DOES consult it, so a sandboxed pass does NOT block
publishing.** (Cross-batch check: `publish.py` is not in batch 04; I read it to settle the
citation.) `publish._mutation_unsafe` is

    src/publish.py:1461:  return bool(busy) and not (isinstance(rec, dict) and rec.get("sandboxed") is True)

and `push()` gates on that, not on `active()[0]`, at src/publish.py:1583-1594. Since
`_lock_acquire` writes `"sandboxed": True` unconditionally (src/mutate.py:271) and the live tree
is never opened for writing, **no run of the current code can make `publish.py` refuse for
mutation reasons.** So the order's stated harm ("a sandboxed pass ... still blocks publishing
for hours") is not reproducible against `src/` as it stands. The order is stale, not live.

**But the same question has a live answer one module over, in `drill.py`.** (Cross-batch: file
belongs to another batch; reported, not filed.) `drill.py:17539-17551` does

    import mutate as _MUT
    _busy, _ = _MUT.active()
    ...
    if _busy:
        print("\n%d net(s) did not hold — but a MUTATION RUN IS ACTIVE ... NOT halting.")
        return 1

It discards the record and never asks about `sandboxed`. A LIVE `drill.py` run (outside the
sandbox) that finds a genuinely breached net during the ~16-20 hours a sandboxed pass is running
therefore **withholds a real OWNER halt** on the theory that the source might be deliberately
corrupt — when since the sandbox rewrite it provably cannot be. That is the order's described
failure shape, in the opposite direction (a suppressed safety rather than a suppressed publish),
and it is the one that is still live. It needs a coordinator ruling because `drill.py` is not
mine to edit or file against.

### MINOR — `mutate.py`'s own comment still asserts the unconditional refusal `publish.py` no longer makes
**Where:** src/mutate.py:124-125
**What:** "This lock is how they know, and `publish.py` refuses to push while it is held."
**Why it is wrong:** `publish.py` refuses only when the lock is held AND the record does not say
`sandboxed: true` (src/publish.py:1461). Every lock this module writes says `sandboxed: true`
(src/mutate.py:271), so the sentence describes a refusal that cannot occur. A reader reasoning
from this comment (as order `e4caaebcbe18` did) reaches the wrong conclusion about whether a
mutation pass is costing the library its publisher.
**Confidence:** high — read both sites; the `sandboxed` key is written at one place only and
consulted at one place only, both quoted above.

---

### ANSWER TO THE BRIEF'S SECOND QUESTION — a run that loses a gate partway is honest ON DISK and NOT honest ON THE CONSOLE, and it never checks its own last window at all

The drift machinery is real and mostly careful. `_refresh_baseline` (src/mutate.py:2235-2325)
restores pristine code, re-photographs every gate with fresh row identities and fresh timings,
DISCARDS an unusable refresh rather than adopting it, journals the event immediately, updates
`base`, and re-derives `red_at_baseline` in place (src/mutate.py:2323). Survivors scored after
the drift each take their own `list(red_at_baseline)` copy (src/mutate.py:2450, :2455), and
`file_orders` pastes that caveat into the permanent work order. That much is honest.

Two gaps make the run's own *report* less honest than its journal:

### MAJOR — the final rebaseline window is never re-photographed, and its verdicts are silently dropped from the drift accounting
**Where:** src/mutate.py:2329-2330 (the only `_refresh_baseline()` call) and src/mutate.py:2456-2457
(the loop's `finally`, with no refresh after it)
**What:** `_refresh_baseline()` is called only at the TOP of a mutant iteration, gated on
`if rebaseline_every and (time.time() - last_base) >= rebaseline_every`. When the mutant loop
ends there is no closing refresh; `judged_since` — the list whose entire job is naming the
verdicts a stale photograph casts doubt over — is still populated and is simply discarded when
`_run_mutation` returns.
**Why it is wrong:** with the default `--rebaseline-every 1800`, every target ends with up to 30
minutes of verdicts (on a multi-hour target, typically tens of mutants) that were judged against
a photograph that is never re-confirmed. If a gate drifted inside that tail window, the run
reports zero drift for it and prints "baseline re-photographed every 1800s and never disagreed
with itself" (src/mutate.py:3040-3042) — the exact all-clear the drift feature exists to prevent.
The module's own argument for the feature ("a false kill hides a real gap and reports it as
covered", src/mutate.py:2216-2222) applies verbatim to this window. `judged_since` being carried
across an unusable refresh (`verdicts_since_last_good_baseline`) shows the mechanism was designed
to survive exactly this; it just has no terminal flush.
**Confidence:** high — read the whole loop body and its `finally`; the only call site is line 2330,
and nothing between line 2456 and the `return` at 2481 touches `judged_since` or `drifted`.

### MAJOR — a gate lost mid-run is never named beside the score, and `red_gates_disabled_at_end` is computed and dropped on the floor by the only production caller
**Where:** src/mutate.py:2486 (the value is built) and src/mutate.py:2981 (`_session` prints only
`red_gates_disabled_at_launch`)
**What:** `_run_mutation` returns both `red_gates_disabled_at_launch` and
`red_gates_disabled_at_end`. `_session` — the only production caller — prints the launch list and
never the end list. The console survivor listing (src/mutate.py:3123-3126) prints
`SURVIVED <target>:<line> <mutation> <was[:70]>` identically whether the survivor was scored with
the battery whole or with a detector down. A grep of `src/` finds `red_gates_disabled_at_end`
read in exactly one other place, `drill.py:15475`, inside a net's fixture.
**Why it is wrong:** this is the reported case. A pass that printed
`*** BASELINE DRIFTED on clean code (drill). N verdict(s) ... M of them KILLS ***` correctly
casts doubt on the KILLS judged *before* the refresh — and says nothing about the SURVIVORS
judged *after* it, which are precisely the ones scored with `drill` matching every mutant's
signature and killing nothing. So the console reads: some earlier kills are suspect, and here is
a clean list of survivors. The caveat exists (`red_gates_disabled` on the journal row and in the
work order's `NOTE:` text, src/mutate.py:2553-2561) but only reaches a reader who opens
`state/MUTANTS_SURVIVED.jsonl` or who ran with `--file-orders`, which is off by default.
**Why I am filing it as MAJOR rather than MINOR:** the module's own standard for this is written
at src/mutate.py:2916-2933 — "A run reporting survivors while a detector is switched off reads
exactly like a run reporting survivors while it is not, which is the failure this whole module
exists to measure, arriving inside the measurement." That paragraph was the fix for the LAUNCH
case. The same defect stands, unfixed, for the mid-run case.
**Mitigations the coordinator should weigh before acting:** the fact is not lost — it is on the
survivor row and in the order — and the drift banner does name the gate that moved. This is a
reporting gap, not a data loss.
**Confidence:** high — read `_session` end to end; grepped `red_gates_disabled_at_end` tree-wide.

### MAJOR — an unparseable lock file wedges both mutation AND publishing permanently, with no automatic recovery, in the function whose docstring says staleness is handled
**Where:** src/mutate.py:222-227 (`active()` returns `(True, {"unreadable": True})`) and
src/mutate.py:245-248 (`_lock_acquire` raises before it can clear anything)
**What:** `active()` treats an unreadable or non-mapping lock as HELD. `_lock_acquire` asks
`active()` first and raises `RuntimeError("a mutation run is already active ...")` when `held` is
true — *before* reaching the `if rec is not None: os.remove(LOCK)` stale-clearing branch three
lines down. `_lock_release` can remove an unreadable record, but only the holder ever calls it.
**Why it is wrong:** `_lock_acquire` writes the record with `os.fdopen` + `json.dump(..., indent=2)`,
which is not atomic. A process killed mid-dump leaves partial JSON. From that instant: every
future `mutate.py` run raises "already active" forever, and `publish._mutation_unsafe` answers
True forever (`isinstance(rec, dict) and rec.get("sandboxed") is True` is False for
`{"unreadable": True}`), so **every push is refused until a person deletes
`state/MUTATION_ACTIVE.json` by hand**. That contradicts this module's own stated contract at
src/mutate.py:118-121: "STALENESS IS HANDLED, because a lock that outlives its holder is an
outage." The pid-death path is handled; the torn-write path is not, and `active()`'s own comment
at src/mutate.py:215-222 names "a partial/interrupted write mid-json.dump" as the reachable
scenario, so reachability is asserted by the code itself.
**QUESTION rather than a fix instruction:** failing closed here is deliberate and correct. What
is missing is a *recovery*, e.g. an age ceiling on an unparseable lock analogous to
`OWNERSHIP_CEILING_SECONDS`, or letting `_lock_acquire` clear an unreadable record older than
some bound. That is a design call for the owner, not something to patch from an audit.
**Confidence:** high — traced both functions; verified `_lock_release`'s unreadable branch is
holder-only and `_lock_acquire` cannot reach its own clearing code on this path.

### MINOR — three load-bearing cross-file line citations in `mutate.py` now point at unrelated code
**Where / what / where it actually is** (each verified by reading the cited file; all three cited
files are outside batch 04 and are named as cross-batch checks):

| citation in `mutate.py` | claims | actual location |
|---|---|---|
| src/mutate.py:731 — `verify_math.py:7990` | `  FAILED <label>: got ..., want ... <note>` | verify_math.py:142 (line 7990 is a `check(` about the attestation ladder) |
| src/mutate.py:732 — `drill.py:9604` | `  BREACHED  <net name>` | drill.py:17386 (line 9604 is inside `the_person_check_is_not_defeated_by_choosing_a_name`) |
| src/mutate.py:472 — `prose_gate.py:201` | `re.split(r"(?m)^◈\s", text or "")` | prose_gate.py:232 (line 201 is the `THE FLOOR HAS A FLOOR` comment) |

**Why it is wrong:** these are not decorative. The first two are the justification for `_row_ids`
matching on a bare `FAILED `/`BREACHED ` prefix; a maintainer checking that reasoning lands on
code that has nothing to do with it. The third is the worked example for the UTF-8 byte-offset
fix in `_col`. **The FORMATS themselves are all still correct** — I verified
`print(f"  FAILED {_lbl_vm}: got {_got_vm!r}, want {_want_vm!r}  {_note_vm}")` at
verify_math.py:142 and `print("  %s  %s" % (mark, r["net"]))` with `mark = "BREACHED"` at
drill.py:17386, and both survive `_row_ids`' `.strip().startswith(...)` test. Only the line
numbers have drifted. The one in-file citation, `mutate.py:33`, is still exact.
**Confidence:** high — read each cited line and grepped for the real construct.

### INFO — `restored_exactly` verifies the write it made one statement earlier
**Where:** src/mutate.py:2456-2457 (`finally: _write(path, original)`) and src/mutate.py:2512
(`"restored_exactly": _digest(_read(path)) == _digest(original)`)
**What:** the `finally` writes `original` to `path`; the very next executed statement reads
`path` back and compares it to `original`.
**Why it is worth naming:** this is close to the brief's category-1 shape ("a comparison against a
value the code itself just set"). It is not *fully* tautological — a silently failed or partial
write would show — but it cannot detect anything that happened during the mutant loop, which is
what "restored exactly" reads as. `live_file_untouched` beside it already carries an explicit
comment admitting its own blind window (src/mutate.py:2459-2472, and again at src/mutate.py:3071-3081);
`restored_exactly` carries no such admission. Not filed as a defect.
**Confidence:** high — read the statement ordering.

### INFO — the sandbox teardown paths skip the junction-unlink hygiene the reaper insists on
**Where:** src/mutate.py:2513-2515 (`_run_mutation`'s `finally`) and src/mutate.py:3191-3193
(`_session`'s `finally`), against src/mutate.py:1288-1316 (`reap_orphans`)
**What:** `reap_orphans` explicitly `os.rmdir`s each junction (`prompts`, `reference`,
`output/index`, and every top-level directory under `data/`) before `shutil.rmtree`, under a
comment calling this "the one place in the project where getting that wrong would delete `data/`
-- 1.1 GB of mined corpus". The two other places that delete the same kind of sandbox call
`shutil.rmtree(root, ignore_errors=True)` bare.
**Why it is worth naming:** the same comment states the unlinking was "proven UNNECESSARY by
direct test this shift", so this is an inconsistency in defence-in-depth rather than a live data
hazard. Filed as INFO so the coordinator can decide whether the belt-and-braces belongs in all
three places or none.
**Confidence:** high — read all three sites.

### Marked-and-kept code seen and not filed
`_TOKEN_ENV` / the `os.environ[_TOKEN_ENV] = token` write (src/mutate.py:141, :366) — retained
under the owner ruling of 2026-09-08 ("mark and keep, delete nothing"), order `c72431056a14`.
Confirmed by grep that the tree still has no reader; the comment already says so. The
`if got is None: _skip(...)` arm in `_mutations` (src/mutate.py:632-636) is likewise marked
unreachable-today-and-kept-on-purpose.

---

## 2. `catalogue_web.py` (785 lines)

Read in full. Checked: the two tripwires, `_singular`'s three rules against real Fandom plurals,
the `first_cat` provenance maps in both `catalogue()` and `catalogue_composite()`, the `seen`
dedup key, the `no_text` accounting, `save_roll`'s compare-and-swap, the thread pool's write
serialisation, and every exit code.

### MINOR — two load-bearing cross-file citations in `save_roll`'s docstring point at unrelated lines
**Where:** src/catalogue_web.py:194-196
**What:** the docstring argues that "every roll writer now lands through `roll.update_rows` /
`roll.mutate` (catalogue_codex.py:361, resync_roll.py:211)".
**Why it is wrong:** (Cross-batch check — both files belong to other batches; I read them.)
`catalogue_codex.py:361` is `"entries": entries,` inside a record dict; the real
`_roll.update_rows(roll_changes, path=ROLL)` call is at catalogue_codex.py:480.
`resync_roll.py:211` is a comment header; the real `_roll.mutate(_apply, path=ROLL)` call is at
resync_roll.py:248. The CLAIM is still true — both writers do go through the roll module — only
the addresses have drifted.
**Confidence:** high — read both cited lines and grepped for the real call sites.

### INFO — the composite path ranks only above 40 titles; the single-wiki path ranks unconditionally
**Where:** src/catalogue_web.py:287 (`if len(titles) > 40: titles = ws.rank_by_size(...)`) against
src/catalogue_web.py:480-486 (unconditional `rank_by_size(..., top=None)`)
**What:** the single-wiki path's own comment states ranking "is unconditional now, which is what
it should always have been, because ranking without truncating costs nothing and buys ordering".
The composite path keeps a bare `40` threshold.
**Why it is worth naming:** not a Hard Rule 0 violation — `top=None` never truncates, so nothing
is lost either way — but the composite path's interrupt-resilience argument ("the richest
material lands first if a run is interrupted") does not hold for its small categories. Reported
as a QUESTION: the 40 may be a deliberate saving of a size query on tiny categories.
**Confidence:** high — read both loops.

### Deliberate tripwires seen and not filed
`MAX_PER_SOURCE = None` with `if MAX_PER_SOURCE is not None: raise SystemExit(...)`
(src/catalogue_web.py:53-67) is a statically-false condition, i.e. formally a check that cannot
fail today. It is explicitly kept as a re-introduction tripwire under order `b248f8f706d3` /
owner ruling 19 of 2026-09-08, and its own comment records the still-OWED drill net pinning the
constant to `None`. Marking seen; not filed. Same for `MAX_PER_CATEGORY` and
`CATEGORY_SCAN_DEPTH` (src/catalogue_web.py:76-82), marked dead-and-retained under order
`47067a8f0ad5`.

### Clean otherwise
`_singular` was checked against the exact cases in its own docstring plus `Buses`/`Analysis`/
`Heroes`; behaviour matches the documented three rules. `save_roll`'s `names` filter, the
`_wlock`-serialised writes, the gated `write_record_catalogue` verdict, and the partial-failure
exit code at src/catalogue_web.py:781 all do what their comments say.

---

## 3. `gpu_lane.py` (684 lines)

Read in full. Traced: `_slot_count`'s precedence and its auto/zero handling, `_alive` on both
platforms, `_expired`, the `_take_slot` three-state return and its reclaim ordering, the
refcounted `foreground()` under `_DEPTH_LOCK`, the heartbeat thread lifecycle, `_remove_retry`,
`lane()`'s two ceilings, and `status()`'s `partial` flag.

### MINOR — a live foreground claim is destroyed by a single transient read failure; the identical hazard on the slot side was fixed and the fix was not carried across
**Where:** src/gpu_lane.py:283-286
**What:**

    rec = _read(path)
    if _expired(rec, CLAIM_LEASE_SECONDS):
        _remove_retry(path)
        continue

`_read` (src/gpu_lane.py:207-212) catches EVERY exception and returns `None` — a sharing
violation, a permissions denial, Norton holding the file — and `_expired`'s first line
(src/gpu_lane.py:249-250) answers `True` for any non-dict. So one unlucky open on a claim held by
a LIVE prose call deletes it.
**Why it is wrong:** the consequence is exactly the m54 defect this module's own `_heartbeat`
docstring measures (src/gpu_lane.py:520-530): once the claim is gone, `foreground_active()`
answers False and "rule 2 of this module's header — background yields to foreground — quietly
stopped applying to the one call it exists for." The slot side was hardened against precisely
this under order `763b56061157`: `_take_slot` does NOT delete what it cannot read, it asks
`_unreadable_and_stale(path)` and requires the mtime to be past the same lease first
(src/gpu_lane.py:400-420). `foreground_active` has no such guard.
**Why I am not certain this is a defect:** `_write_claim` lands through
`silence.replace_retry(tmp, path)`, which is atomic, so there is no zero-byte creation window on
the fg side — which is what the slot-side guard was *primarily* written for. The residual case is
a transient read denial on a well-formed file, which the slot-side guard also covers and this one
does not. Reported as an asymmetry for the coordinator to rule on rather than as a confirmed bug.
**Confidence:** high on the code paths (read all four functions); medium on severity.

### INFO — `lane()` has no `except`, so an unexpected exception in the arbitration block fails the model call the module promises can never be blocked
**Where:** src/gpu_lane.py:585-635 (`try: ... finally:` with no `except`)
**What:** the header mandates "FAIL OPEN, ALWAYS ... every failure path here PROCEEDS rather
than blocks". Almost every helper honours it: `_read`, `_remove_retry`, `_write_claim`,
`_unreadable_and_stale`, `_ensure_dir` and `foreground_active` all swallow. `_expired` does not:
`float(rec.get("heartbeat") or 0)` raises `ValueError`/`TypeError` on a record whose `heartbeat`
is a string or a list, and `int(rec.get("depth") or 0)` in `foreground()` (src/gpu_lane.py:313)
is the same shape. From `_take_slot` or `foreground()` such an exception propagates out of
`lane()`'s `try` — which has only a `finally` — and out to the caller, aborting the model call.
**Why it is only INFO:** every writer in this module writes `_now()` (a float) and an int depth,
so reaching it needs a hand-edited or foreign-written lane file. Named because the module's whole
contract is that no failure here can stop a call, and this is the one gap in it.
**Confidence:** high on the control flow; low on real-world reachability.

### Clean otherwise
`_slot_count`'s `0`-is-auto handling, `_alive`'s Windows `OpenProcess` + `GetExitCodeProcess`
pair and its unknown-means-alive rule, `_touch`'s never-resurrect guard, `_heartbeat`'s
`_BEAT_SECONDS = max(5.0, min(SLOT_LEASE, CLAIM_LEASE)/3)`, the stop-then-join-then-release
ordering in `lane()`'s `finally`, and the `partial` honesty flag in `status()` were each checked
against their stated reasoning and hold.

---

## 4. `withdraw_chapters.py` (519 lines)

Read in full. Traced by hand: `_file_state`'s three-way answer, `_archive_name_free`,
`select()`'s exactness, the per-selector refusal, the per-path/per-entry unit split, `entry_left`
and the record amendment, the stray sweep's `claimed_raw` filter, the manifest merge, and the
exit code.

### INFO — the snapshot taken before the irreversible step covers the catalog only, not the chapters
**Where:** src/withdraw_chapters.py:217-227
**What:** the comment reads "A COPY BEFORE THE IRREVERSIBLE STEP. This script moves rather than
unlinks, which was the right instinct when it was written -- but the instinct was the ONLY thing
standing behind 145 chapters." The call taken is
`SNAP.before("withdraw-chapters", ["output/index/catalog.json"], ...)`.
**Why it is worth naming:** the snapshot is of `catalog.json` and nothing else. After the run the
archive directory is still the only copy of every chapter file, exactly as before — which is what
the move-not-unlink design intends, so the behaviour is right. The comment's framing invites a
reader to believe a copy of the CHAPTERS was taken. Reported as a wording question, not a fix.
**Confidence:** high — read the call and `SNAP.before`'s argument list.

### INFO — two cross-file citations in the comments point at unrelated code
**Where:** src/withdraw_chapters.py:147 (`publish.py:1385-1398`) and src/withdraw_chapters.py:502
(`address_space.py:467-480`)
**What / why it is wrong:** (Cross-batch check — both files belong to other batches; I read them.)
The fail-closed `import escalation` + `REFUSING TO START` pattern this module says it copied from
`publish.py:1385-1398` is actually at publish.py:1800-1814; lines 1382-1400 are the atomic
`docs/index.html` write. The "exit nonzero ... a shelfmark read as fresh while it is stale"
argument attributed to `address_space.py:467-480` is at address_space.py:650; lines 460-485 are
`fit()`'s no-modulo comment. Both quoted ARGUMENTS are still present and still support the
reasoning; only the addresses drifted.
**Confidence:** high — read each cited range and grepped for the quoted sentence.

### Clean otherwise — and unusually well repaired
Every hazard this module's own history names was checked against the code and holds:
`_file_state` asks twice and keeps the record on "unavailable" (src/withdraw_chapters.py:53-87);
`_archive_name_free` refuses on anything but FileNotFoundError (src/withdraw_chapters.py:90-111);
the per-selector refusal at src/withdraw_chapters.py:196-208 checks `--source` and `--addr`
independently; `moved[sub] += 1` sits in the per-path loop and outside `if a.go`, which is the
correct dry-run preview semantic; `withdrawn` excludes `stuck` and `remaining` is `cat` minus
`withdrawn`, so a failed move keeps its record; `entry_left` + the amendment at
src/withdraw_chapters.py:289-298 mutate the same `rec` object `remaining` carries, so the
amendment does land; `claimed_raw` is built from the WHOLE catalog rather than from this run's
selection, which closes the (a)/(b)/(c) cases its comment names; the manifest merge's
`new_from_existing` arithmetic is correct; and `bad` at src/withdraw_chapters.py:516-518 folds
every printed refusal into the exit code. Nothing filed.

---

## 5. `hosts.py` (396 lines)

Read in full. Traced `_load`'s absent-vs-corrupt split, `primary_host`'s list tolerance,
`hosts_for`'s sentinel filter, `add`'s three-state return, `discover`'s four distinguishable
outcomes and the grounded/speculative split, `coverage`, and `main`.

### MINOR — `--discover` returns 0 even when every source failed to be probed or every discovered host was lost to a denied write
**Where:** src/hosts.py:365-378
**What:** `main()`'s `--discover` arm prints the rows, prints `hosts added: N`, and
`return 0` unconditionally. `discover()` already writes two loud stderr blocks — "N DISCOVERED
HOST(S) WERE NOT RECORDED" (src/hosts.py:317-320) and "N SOURCE(S) COULD NOT BE PROBED"
(src/hosts.py:335-339) — and escalates both via `silence.note`, but neither reaches the return
value, so neither reaches the exit code.
**Why it is wrong:** this is the same shape `catalogue_web.py` was repaired for twice (orders
`1e45fae97848` and `ea1a063d75d6`, quoted at src/catalogue_web.py:770-780): "rc 0 is the only
thing a shell `&&`, a scheduled job or a keeper restart looks at." A walk in which candidate
generation raised for every source, or in which every host found was lost to a denied
`SOURCE_HOSTS.json` write, exits 0 and reads as a successful refresh. `add()` was deliberately
given a third state (`None`) so this loss could be distinguished — and the distinction stops at
stderr.
**Mitigating fact the coordinator should weigh:** grep finds NO importer or subprocess invoker of
`hosts.py` anywhere in `src/` (confirmed independently by descending_ladder.py:43,
scale_theories.py:27, onomast.py:450 and drill.py:13447, which all record the same measurement),
so nothing currently reads this rc. It is a latent defect on a module nothing calls.
**Confidence:** high — read `main()` and both stderr blocks; grepped for importers.

### INFO — `hosts_for(include_primary=False)` has no caller anywhere
**Where:** src/hosts.py:93
**What:** the parameter is never passed as `False` — the three call sites (src/hosts.py:349, :384,
:386) all use the default, and there are no callers outside this module at all.
**Why it is worth naming only as INFO:** the module-wide "no importer" fact is already recorded in
four other modules and has a drill net behind it (drill.py:13310-13311); this is one more corner
of the same known state, not a new finding. Flagged so a future reader does not re-derive it.
**Confidence:** high — grepped `hosts_for(` tree-wide.

### INFO — the import-time tripwire leaks its own file handle
**Where:** src/hosts.py:37 (identically at src/catalogue_models.py:48)
**What:** `if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):`
— the file object is never closed and is left to the garbage collector.
**Why it is only INFO:** CPython refcounting closes it immediately in practice, and the tripwire
itself (a real check that CAN fire, unlike the `MAX_PER_SOURCE` one) is sound. Named for
completeness.
**Confidence:** high.

### Clean otherwise
`_load` raising on a corrupt-but-present map (src/hosts.py:49-83), the `pages:`/`doc:` sentinel
filter in `hosts_for`, `add`'s True/False/None contract, and `discover`'s four outcomes
(`_PROBE_FAILED`, `None` for a thin roster, `[]` for probed-and-nothing-held, a populated list)
all behave as documented. `add()` is called only from the main thread inside
`for res in ex.map(...)`, so its read-modify-write of `SOURCE_HOSTS.json` is not racing the six
workers — I checked this specifically, since it would be a lost update if it were. The
deliberately-kept unreachable `if not res:` arm at src/hosts.py:281-287 is marked as such.

---

## 6. `catalogue_models.py` (339 lines)

Read in full. Checked `_key_of`/`_base_of`, the `/v1` double-prefix guard, the four-outcome
contract, the `LISTED`/`EMPTY_LIST` membership of `live`, the `verified` denominator, the
`LAST_WRITE_LANDED` tri-state, and `main`'s exit code.

### INFO — the "current alternatives" console block prints an empty line for an `EMPTY_LIST` provider
**Where:** src/catalogue_models.py:254-264
**What:** `for name in sorted({s["provider"] for s in stale}): r = live.get(name); if r:
print(f"  {name}: " + ", ".join(r["models"]))`. An `EMPTY_LIST` provider is in `live` (correctly,
per the sweep42-batch14 fix) with `r["models"] == []`, and every model the config asks it for is
in `stale`, so this prints `  <provider>: ` with nothing after the colon.
**Why it is wrong (mildly):** the block's heading is "Current alternatives, per provider:", and a
blank line under it reads as a truncated or failed listing rather than as the definite finding
that the provider serves nothing. The record on disk is correct; only this console line is
ambiguous. Not a correctness bug.
**Confidence:** high — traced `live`, `stale` and the print.

### Clean otherwise
The subtle precedence in `mid = m.get("id") or m.get("name") if isinstance(m, dict) else str(m)`
(src/catalogue_models.py:120) was checked explicitly: the conditional binds loosest, so it reads
`(m.get("id") or m.get("name")) if isinstance(m, dict) else str(m)`, which is the intent.
`LAST_WRITE_LANDED = None` as the default, with `main()`'s `return 0 if LAST_WRITE_LANDED else 1`
treating `None` as failure, is correct as its comment claims. `verified` and `live` use the same
`(LISTED, EMPTY_LIST)` membership test, so the printed denominator and the recorded `counts`
cannot disagree. Every uncut-string comment (`available_sample`, the `why` field, the console
alternatives) matches the code beside it. Nothing filed.

---

## 7. `resonance.py` (298 lines)

Read in full. Hand-traced the Gauss-Seidel sweep, the gauge fix, the convergence test, all four
return shapes of `hodge_decompose`, `dominates`, `incomparability_rate`'s three-way split, and
`resonance_strength`.

### Clean — nothing filed. What was checked:
* The sweep at src/resonance.py:169-181 is genuinely Gauss-Seidel: `prev = theta` then
  `theta = dict(theta)` then in-place per-node updates, so later nodes in the same sweep read
  refreshed values. The Jacobi-on-bipartite failure the docstring measures cannot recur.
* The convergence test uses the MAX per-node shift, measured after the gauge fix on both sides,
  so the gauge fix itself cannot register as movement. `used` is initialised to 0 before the loop,
  so `sweeps=0` returns `converged: False, sweeps: 0` rather than raising on an unbound name.
* All four exits (`no nodes`, `not converged`, `total == 0`, `converged`) carry `converged` and
  `sweeps`, and the three "no measurement" exits return `eta: None` rather than a number. The
  "no evidence" / "perfectly consistent" conflation the module is about does not exist in it.
* `total == 0` provably implies every flow is zero (`total = grad_sq + res_sq`, both sums of
  squares), so the comment at src/resonance.py:203-205 is exact.
* `dominates` and `incomparability_rate` recompute `shared` identically; the UNMEASURED / TIED /
  INCOMPARABLE split is consistent and `decidable = total - unmeasured` is the right denominator.
  `examples` is uncapped, as its comment claims.
* The `_isolated` guard at src/resonance.py:157-163 is a genuine check that is unreachable today;
  its own comment says so and states why it is kept rather than deleted. Marking seen.
* Citations INTO this file from elsewhere were verified and are all correct:
  `resonance.py:290` (cosmology_graph.py:65) is the `graph_path or ...` line;
  `resonance.py:295` (cosmology_graph.py:135) is the `shared_sample` read;
  `resonance.py:89` (liveness.py:420) is `def hodge_decompose`.
* The docstring's "NO PRODUCTION CALLER" claim holds: `hodge_decompose` is called only by
  drill.py:16352-16399, `incomparability_rate` only by verify_math.py:10906-10916, and
  `resonance_strength` by nothing. `custodes.py:431-467` and `anchors.py:208-210` independently
  record the same gap. The docstring is honest about its own module.

---

## 8. `lognames.py` (52 lines)

### Clean — nothing filed.
Six constants and one `OWNER` mapping, no logic. Checked that every key of `OWNER` is one of the
six constants (all six appear exactly once as a key), that the `PIPELINE` value carries `--run`
as its comment requires, and that `SWEEP` is deliberately bare with the reason given. Cross-checked
the consumer in my own batch: `mutate.sandbox()` (src/mutate.py:1671-1678) derives its gate-log
list from this module by `dir()` + `isupper()` + `.endswith(".log")`, which picks up exactly the
six string constants and correctly excludes `OWNER` (a dict, filtered by the `isinstance(..., str)`
test). Its hardcoded fallback tuple matches the six current values, so a log added here travels to
the sandbox automatically and the fallback only goes stale if `lognames` becomes unimportable.

---

## Summary of findings

| # | severity | module:line | title |
|---|---|---|---|
| 1 | MAJOR | mutate.py:2329 | final rebaseline window never re-photographed; `judged_since` dropped |
| 2 | MAJOR | mutate.py:2486 | `red_gates_disabled_at_end` computed and never printed; mid-run detector loss invisible in the run's own report |
| 3 | MAJOR | mutate.py:222 | an unparseable lock wedges mutation and publishing permanently, no recovery |
| 4 | MAJOR (cross-batch) | drill.py:17541 | `drill.py` withholds a real halt for a sandboxed pass because it ignores `sandboxed` |
| 5 | MINOR | mutate.py:124 | comment asserts a `publish.py` refusal that can no longer occur |
| 6 | MINOR | mutate.py:731/732/472 | three stale cross-file line citations (formats verified still correct) |
| 7 | MINOR | catalogue_web.py:194 | two stale cross-file line citations in `save_roll` |
| 8 | MINOR | gpu_lane.py:283 | a live foreground claim is swept on a transient read failure; slot-side guard not carried across |
| 9 | MINOR | hosts.py:365 | `--discover` returns 0 despite lost hosts and unprobed sources |
| 10 | INFO | mutate.py:2512 | `restored_exactly` verifies the write made one statement earlier |
| 11 | INFO | mutate.py:2513 / :3191 | sandbox teardown skips the reaper's junction-unlink hygiene |
| 12 | INFO | gpu_lane.py:585 | `lane()` has no `except`; `_expired`'s `float()` can escape the fail-open contract |
| 13 | INFO | catalogue_web.py:287 | composite path ranks only above 40 titles (QUESTION: deliberate?) |
| 14 | INFO | withdraw_chapters.py:217 | the pre-withdrawal snapshot covers the catalog, not the chapters |
| 15 | INFO | withdraw_chapters.py:147 / :502 | two stale cross-file line citations |
| 16 | INFO | hosts.py:93 | `hosts_for(include_primary=False)` has no caller |
| 17 | INFO | hosts.py:37 / catalogue_models.py:48 | import-time tripwire leaks its file handle |
| 18 | INFO | catalogue_models.py:254 | empty "alternatives" line for an `EMPTY_LIST` provider |

Clean with an account of what was checked: `resonance.py`, `lognames.py`, and the bulk of
`withdraw_chapters.py` and `catalogue_models.py` (see each section).

Findings 4, 6, 7 and 15 required reading files outside batch 04 (`publish.py`, `drill.py`,
`verify_math.py`, `prose_gate.py`, `catalogue_codex.py`, `resync_roll.py`, `address_space.py`).
Each is labelled as a cross-batch check in its own entry; the coordinator should confirm 4 in
particular with whichever batch owns `drill.py`, since the remedy is not mine to propose.
