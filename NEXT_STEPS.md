# NEXT STEPS — written by the daily maintenance run of 2026-09-03 (run #43)

## 0. READ THE MUTATION LOG FIRST. IT WAS STILL RUNNING WHEN THIS SHIFT CLOSED.

    state/mutate_2026-09-03.log

**Do not read a launched pass as a completed one.** This shift UNBLOCKED the mutation pass — it
had been refusing to run at all — and then launched it. At shift close it was still working
through `assay.py` (53 of 186 mutants; `escalation.py` x108 and `prose_gate.py` x25 had not
started). It runs the whole battery per mutant, so several hours is normal.

It was launched with `--file-orders`, so **survivors arrive in the queue by themselves** with
their exact diffs. Your first act should be to read that log and work them.

- If it finished: put the survivor count in your handoff. **A survivor is not automatically a
  bug** — some mutations are genuinely equivalent — but which it is has to be decided by reading
  it, never assumed.
- If it did not finish, say so. A pass killed halfway is not a pass with fewer survivors.
- It was launched with `--no-confirm` NOT set, so survivors are confirmed. Flakiness was **not**
  checked (`--check-flaky` was not passed); if a survivor looks impossible, that is the first
  thing to suspect.
- **Caveat, stated so you can weigh it:** `src/` was edited during the run (the sandbox is a
  copy taken at launch, so the results are sound, but they describe the tree as it stood at
  22:33). Two nets were ADDED to `drill.py` after the baseline, so the real battery is now
  slightly stronger than the one that judged these mutants — a survivor may already be killed.

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

- **GitHub push is DEFERRED by the owner** ("ignore github for now"). The export commits locally;
  the push reads HELD. Not a fault to chase.
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
