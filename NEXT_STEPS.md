# NEXT STEPS — written by the daily maintenance run of 2026-09-03 (run #43)

## 0. THE MUTATION PASS FINISHED, SCORED 100%, AND THAT IS THE PROBLEM

    state/mutate_2026-09-03.log        the run    (58,709s / 16.3h, finished 2026-09-04 14:55)
    state/mutate_flakycheck_20260904.log   the control this run started; read it

**Result: 299 mutants, 298 killed, ZERO survivors, 1 indeterminate** (assay.py 119/118/0/1,
prose_gate.py 62/62/0/0, escalation.py 118/118/0/0; the indeterminate is `assay.py:1343 > -> <=`,
a verify_math TIMEOUT, honestly excluded from both counts).

**Do not report that as coverage.** Order **`58a00e909217`** (RUN/MAJOR) records why. This was
**settled by experiment, not argument** — both suspect mutants were re-attacked directly in a
fresh sandbox and the result SPLIT, correcting one of this run's own claims along the way
(`state/equivalent_mutant_test_20260904.log`):

    escalation.py:409  False -> True    import SAME  verify_math SAME  drill SAME  => SURVIVED
    assay.py:228       or -> and        import SAME  verify_math 1129/1  drill SAME => KILLED

- **`escalation.py:409` is a CONFIRMED FALSE KILL.** It survives cleanly — every gate signature
  identical to baseline — and the 16.3-hour run called it killed. It is undetectable by
  construction: the success path reassigns both names, the `if not landed:` branch returns the
  reassigned `why`, the `except` arm returns the LITERAL `False, "raised"` rather than `landed`,
  and the closing return is reachable only after the reassignment. **So orders `a380a696d364`
  and `e5954a534604` are CORRECT and must not be closed.**
- **`assay.py:228` is genuinely killed, and the earlier "equivalent" ruling was wrong** — mine and
  order `d9c8aab72a2c`'s. Correction filed as `ASSAY_L228_SURVIVOR_1_IS_NOT_EQUIVALENT_AFTER_ALL`.
  The failing row names itself: `axis_score refuses a HALF-DEFINED band edge (floor present,
  ceiling missing): got 'RAISED TypeError', want None`. **The lesson is worth more than the fix:**
  the equivalence argument rested on the asymmetric case being unreachable because `BAND_EDGES` is
  complete (verified — 55/55 entries, and zero behavioural divergence over every reachable
  `(band, axis)` pair). But verify_math does not reach the guard through the table; it
  *synthesises* a half-defined edge and demands a refusal. **"Unreachable with today's data" is
  not "equivalent."** A guard exists for inputs that do not currently occur.

**One confirmed false kill is enough:** the score is not coverage, and the other 297 verdicts
inherit the doubt. A false survivor wastes your time; **a false kill hides a real gap and reports
it as covered.**

**Consequences for what you do next:**

- **Do NOT close the eleven `MUTANT_SURVIVED_*` orders** on the strength of this run. It did
  re-attempt every one of those exact lines (verified by enumerating `mutate._mutations`), and a
  trustworthy instrument would have retired most of them — the 2026-09-02 run that filed them took
  a **RED baseline with verify_math DISABLED** (its own log says so), which is precisely why
  `assay.py:228` survived that day and dies now. Most are probably false survivors. **Retire them
  one at a time by re-attack, never in bulk on the word of a run that also produced a false kill.**
  The method is in `state/equivalent_mutant_test_20260904.log`'s script and takes minutes per
  mutant.
- **Short-term flakiness is RULED OUT**, so do not spend the shift there:
  `mutate --target prose_gate.py --check-flaky --limit 2` reported **"all gates reproducible"**
  (`state/mutate_flakycheck_20260904.log`), and the escalation mutant survives cleanly in a
  minutes-long sandbox. The difference is something about a **sixteen-hour** run.
- **The leading hypothesis, still not proven:** `sandbox()` copies `src/` and `state/` but
  JUNCTIONS `data/` out to the live tree, which `feats.py --roll` and `pipeline.py` rewrite
  continuously, while judging is differential against a baseline taken once at launch. The tool's
  own banner says it: *"reproducible over seconds is not stable over the hours this run takes."*
  **Test it by re-taking the baseline periodically through a long run** (or snapshotting the
  `data/` subset the gates read), then re-run and check that `escalation.py:409` is correctly
  reported as a survivor.

## 1. THE THING TO FIX FIRST

**`0f815b38363f CLEAR_HALT_NOT_CAS`** (`escalation.py:900`, RUN/MAJOR). `clear()` writes
`state/HALT.json` with a plain `silence.write_json` — atomic, but NOT a compare-and-swap — while
every other writer of that same file (`_raise_halt`, `_write_stopped`) is CAS'd for exactly this
reason. A fault escalating to OWNER concurrently with a human's `--clear` can be silently dropped
from the halt record and the halt lifted anyway.

**It was left open for one reason only: `escalation.py` is a live mutation TARGET and `mutate`
asserts the target's digest is unchanged, so editing it mid-pass would have aborted the pass.**
Once the mutation run above has finished, this is unblocked and small.

## 2. THE OTHER TWO MAJORS LEFT OPEN, AND WHY NEITHER IS A QUICK PATCH

- **`a4b5ffc46f95 WRITE_RECORD_STALE_TOPKEY_CLOBBER`** (`pipeline.py:769-810,909`). The
  top-level-key fold treats any non-`None` key in the caller's in-memory `rec` as "authored this
  call", but `rec` is loaded once per phase and reused across every write for that source —
  `phase_entrypass` calls `write_record` ~1,500 times for a large source, each re-stamping the
  load-time snapshot back onto disk and reverting anything `write_record_catalogue` wrote in
  between. **This is the same incident class as the 31-nulled-synthesis bug, reintroduced via
  staleness rather than `None`.** The remedy is an explicit per-call allow-list of authored keys,
  which is a design decision. Do not rush it, and do not "fix" it mechanically.
- **`bf729d9664b1 CORPUS_DB_FRESHNESS_MISSES_DELETIONS`** (`corpus_db.py:440-448`). `freshness()`
  detects staleness only from the mtimes of records that still EXIST, so a deleted record file is
  invisible: the banner can say "no record has changed" while the index still holds ghost rows.
  Directly contradicts the module's "always admit how stale it is" contract. Needs `meta` to track
  source basenames, not just mtimes.

## 3. TWO BUGS IN `binding_health.py` THAT MUST BE FIXED TOGETHER, NOT SEPARATELY

This is the one piece of sequencing knowledge this shift can hand you that you would otherwise
have to rediscover:

- `cd7492eec3bc` — `binding_health.py:1027` `if limit:` reads `--limit 0` as "no limit" and runs
  the full ~200-host sweep (the same falsy-zero slip fixed in `burgs.py` this shift).
- `f1901d2178ba` — `binding_health.py:1091` the whole-estate-empty guard is
  `if not (only or limit) and not out:`, so when a FILTER matched zero hosts it falls through to
  the merge path and lands a re-stamped `BINDING_HEALTH.json` with `at` bumped to now, having
  verified nothing.

**Fixing the first alone makes the second newly reachable** — `--limit 0` would begin producing
an empty host list, which is precisely the input the second bug mishandles. That is why this
shift fixed neither. Take them as one change.

## 4. THE QUEUE — 416 OPEN, AND IT WILL NOT EMPTY IN ONE SHIFT

    LOCAL 144 · BOTS 24 · RUN 68 · SESSION 58 · OWNER 122   (at close, before mutation survivors)

**23 orders were closed this shift** (14 worked directly; 9 auto-closed the moment the inverted
`_fire` was corrected). Sweep 43 filed ~40 new ones, each with file, line and reasoning, and
`sweep_plan.missing('run43')` returns **0** — every module in `src/` was read in full. The audits
are in `handoff/sweep43/AUDIT_batch01..16.md` and carry far more detail than the orders do.

- **The RUN rung is still where the leverage is.** Verify every finding against source before
  acting — audits are wrong in both directions, and this shift caught one of its own: a scan
  reported 79 `subroom` contradictions and every one was the INTENDED state, because
  `subroom_ok()` returns True for `unclassified` by an early return.
- **LOCAL is workable again but slow.** Ollama's 503 is transient and `local_agent`'s retry rides
  it out (measured: a real task succeeded in 5m52s while the queue was saturated). Budget ~6
  minutes of backoff per call under contention. **Do NOT implement run #42's "refuse immediately
  on a saturated queue"** — see the correction in `BUGS.md` M67 and order `171ade4c7d27`; it would
  turn a slow success into a fast failure.
- **The queue carries TWINS.** The dedup key is `(code, where)`, so two sweeps describing one line
  differently create two orders. Work the concentrated files by reading all their orders together
  — one at a time, each verified against source. A bulk merge on similarity would close live
  faults.

## 5. STANDING, AND UNCHANGED

- **CORRECTION — THE GITHUB PUSH IS NOT HELD, AND HAS NOT BEEN FOR SOME TIME.** Runs #41 and #42
  both carried "the export commits locally; the push reads HELD. Not a fault to chase." That is
  stale, and believing it would mean not realising this repository is live. Measured 2026-09-03
  23:28: `publish.py --push` synced 36 files and **pushed to
  `https://github.com/GeddyLifeson/panscriptum.git`** — `git reflog show origin/main` records
  `update by push` for this shift's commit and for several before it, and
  `git log origin/main..HEAD` is empty. **Everything this shift wrote is public**, including the
  three ledgers and all sixteen `handoff/sweep43/AUDIT_batch*.md` files, which is the established
  design (`handoff/` is a `COPY_DIRS` root and earlier sweeps' audits are already there). The
  secret gate passed on the way out, with two independently-written scanners agreeing:
  `publish.scan_for_secrets` 0 and `detect-secrets` 0. **Treat every audit and ledger you write as
  publishable, because it is being published.**
- **Do not widen `state/ledger_chain_acknowledged.json`.** A second record needs a person, an
  order id and a reason.
- `c614f7c145fc` (the 2026-08-26 automated halt-lift) still wants an owner ruling.
- **Never open `prose_enabled` or `step4_enabled`.** A gate that looks unnecessary is what a
  working gate looks like.
- `publish.py:293`'s `_AMBIGUOUS` case-sensitivity was filed and **deliberately not taken**: the
  change makes the placeholder-credential test more permissive, i.e. it loosens the gate in front
  of a public push. It currently fails toward over-blocking, which is the safe direction. That is
  a review-cycle decision, not a night-shift one.

## 6. QUESTIONS WAITING ON A PERSON

- `88982cef258d` — every remote provider rate-limited at once while local Ollama is saturated.
  An account/quota condition, not a code fault, and the one non-green row in the battery.
- `171ade4c7d27` — `local_agent` returns `rc=0`/`ok:true` for an answer whose own text says it
  could not do the task. Detecting "the model said it could not" is a heuristic, and heuristics on
  that path are how a gate gets loosened. Wants a ruling, not a predicate.
- `codewatch`'s `runs_script`/`twins`/`claim_singleton` deliberately FAIL OPEN, reasoned in their
  own docstring but in tension with Hard Rule -1's "every layer answers 'I don't know' with STOP".
  Is twin-detection meant to be exempt?
- `runguard.read()`/`holder_is_live()` likewise fail OPEN on a corrupt guard record.
- `assay.py`'s `ATTESTATION_FLOOR` still has no monotonicity or ceiling guard while its sibling
  table is protected at import. These tables sit inside every published ± in the library.
- `scale_theories.py`'s five dead constants: verified dead, deliberately not deleted.

## 7. TWO PROCESS LESSONS WORTH CARRYING

1. **Never pass finding prose through a shell.** Two sweep agents independently had work-order
   text corrupted because backticks in the prose executed as shell command substitution under
   `bash -c`. Write the prose to a script file and run the file. Both caught it by re-reading the
   order from disk afterwards, which is the habit to keep.
2. **Close an order against the whole order, not the limb you happened to fix.** This shift closed
   `1bc825e806a9` on one of its three limbs because a selector matched too broadly; it was
   re-opened and finished properly, and the paper trail records both. A closed order that is
   indistinguishable from a completed one is the exact rot the queue exists to prevent.

## 8. HOUSEKEEPING

- **`foreman` and `overwatch` were bounced at the end of this shift** and are the ONLY two that
  needed it. Both had been up ~23 hours on pre-shift code and could not self-bounce, because the
  fix that makes them exit rc=17 postdated their start — the condition run #42 diagnosed as
  `838be29f9e58` and asked the next run to clear. This mattered beyond hygiene: the old `foreman`
  was still running the `LIKE '%"rpm": 1%'` remedy that wipes legitimate rate caps of 10, 15, 19
  and 100. **Confirm they are up and on the current fingerprint before trusting anything they
  report.**
- `dashboard` spent its restart budget (4/hour) during this shift's `src/` edits and may be
  deliberately running stale code; it self-corrects once the tree is quiet.
- `state/_queue_snapshot_20260903.json` is a working file this run left behind; safe to delete.
- `data/records/getter-robo.json.precatfix` is still a non-`.json` leftover in the records
  directory (carried from run #42).
