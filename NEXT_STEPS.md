# NEXT STEPS — written by run #41 (2026-09-02) for the run that follows it

Overwritten every run, on purpose. The queue in `state/workorders.json` is the memory; this file
is only the ordering.

---

## 0. STATE AT THE OWNER SESSION OF 2026-09-02 -- READ BEFORE THE REST

**Publishing is UNBLOCKED.** The owner ruled option (a) on `be33a61be79f`: the three chain
shrinks from run #41's probe are ACKNOWLEDGED in `state/ledger_chain_acknowledged.json`,
still printed on every run and every push, never erased. `assert_intact()` passes. **Do not
widen that registry**; a second record needs a person, an order id and a reason.

**GitHub push is DEFERRED by the owner** ("ignore github for now"). The export commits
locally and the push reads HELD until `GITHUB_TOKEN` is unset for the daemons or the PAT is
granted write access. Not a fault to chase; not yours to fix autonomously.

**Still open and wanting a ruling:** `c614f7c145fc` (the 2026-08-26 automated halt-lift).

**PHASE 4.2 IS DONE (ruling F, STEP4_PLAN.md section 7).** `thread_integrity` reads
`data/THREADS.json`; the release gate (a thread resolving to no address) holds at 0 over
1,508,653 threads; RECIPROCAL 711 / IMPLIED-UNRECORDED 5,071 / ASYMMETRIC 0; five nets and
five battery rows, all watched red. **4.3 is the next subphase and is NOT authorised.** Two
things its ruling must address before anyone writes a line: (1) the ASYMMETRIC-SUSPECT
baseline is **0** because T1/T2 are sibling-symmetric by construction, so the first one-way
T3 thread trips the regression floor -- 4.3 needs a deliberate re-baseline, recorded, not a
quiet edit; (2) 87.7% of implied pairs are unrecorded and that is CORRECT for T1/T2 -- they
are the entity-shared cross-verse obligations T3 exists to record. Ruling B also stands:
a T5 refusal net must exist before 4.3 (it does: drill_threads).

---

## 1. THE MUTATION RUN FROM #41 SHOULD HAVE FINISHED — READ IT FIRST

`mutate.py --target all --file-orders` was relaunched 2026-09-01 22:46 and was still running when
#41 closed, ~2 hours in, with nothing journaled. **Read `state/mutate_2026-09-01.log` and
`state/MUTANTS_SURVIVED.jsonl` before anything else**, and check the lock is not still held by a
dead pid. Two caveats when you do:

- Its baseline records `drill` at **371** nets. Eleven more landed after it started, so its
  results describe the battery as it stood at 22:46, not as it stands now.
- Every survivor row it writes this run carries `tree_was_moving` — a maintenance shift held the
  guard throughout — so weigh survivors accordingly rather than taking the count at face value.

Then relaunch it against the current battery, early, as the card instructs.

## 1b. STEP 4 POSITION, MEASURED 2026-09-02 10:59 (post-shift scrub)

- **Phase 4.0 is closed** by three independent measurements: `address.spine_code_for` resolves
  215/215 roll sources (0 unassigned, 0 provisional); `output/index/unassigned_sources.md` says
  none; `data/THREADS.json` records `unaddressed: []`. allsweep's "33 with NO charter spine code"
  is a different thing -- estate.py's own docstring calls it a known and accepted standing
  condition: 33 sources sit outside the charter's LITERAL appendix by decision (Hard Rule 2 makes
  extending it owner work) while `CHARTER_SPINE_CODES.json`, the owner-extended index, addresses
  all of them. Not a blocker; the charter document lags the JSON index by 33 sources.
- **Phase 4.1 is complete as an emitter.** `data/THREADS.json` (2026-09-01 11:34): 210 sources,
  282,822 entries, T1 282,822 / T2 1,225,831 / 1,508,653 threads, 5.334 per entry, stored
  per source-category (6,558 source-level edges) and expanded per entry. Measured directly:
  **DANGLING = 0**, self-loops 0, no source with zero threads. `drill_threads` holds the
  by-construction attacks (points-at-nothing, UNASSIGNED, T5 refusal, phase lock), all green.
- **The verifier cannot see it, and that is Phase 4.2 by definition.** `thread_integrity.py`
  never loads THREADS.json; `classify(..., recorded=None)` reports IMPLIED-UNRECORDED for 100%
  of 5,782 source pairs. 4.1's "verify with thread_integrity, which finally has its graph" is
  therefore unmet -- and it is exactly the work the plan assigns to 4.2. THREADS.json has ONE
  reader today (threads.py itself): the m37 shape.
- **4.2 is NOT authorised.** STEP4_PLAN.md §7E: "PHASE 4.0 AND 4.1 ONLY ... 4.2 through 4.5 are
  not authorised by this ruling and need their own." A ruling F, recorded in §7 and in
  config.yaml's SCOPE comment, is the prerequisite. 4.2 emits no prose and nothing to publish,
  so the publish block (`be33a61be79f`) does NOT gate it.
- **What 4.2 is, concretely:** feed `recorded={(from,to)...}` from THREADS.json into
  `thread_integrity.classify`; make DANGLING == 0 a release gate (SUPERVISOR per source, OWNER
  on a corrupt/unreadable THREADS.json, per §8); floor ASYMMETRIC-SUSPECT; report ASYMMETRIC
  as count+list, never a failure (ruling C); a drill net and a verify_math row; a `tol`/floor
  that can only ratchet.

## 2. THE NETS RUN #41 OWES

Fixes that landed with nothing in the battery behind them. Full list with reproduction steps in
`handoff/sweep41/` and in the orders themselves; the ones that matter most:

1. **`mutate`** — a missing gate document must make the run refuse *and name which* (orders
   `2461a04d8849` / `21ae41adc29c`). Without it a disabled gate scores every mutant SURVIVED,
   which looks exactly like a finished run.
2. **`custodes.table_faults()`** — a working detector with no caller outside its own module
   (`d27e95a57233`, `00a85c511b53`). One line in the battery closes it.
3. **`codewatch`** — repoint the restart-budget net at `_claim_restart_slot`, add a fail-closed
   net (`06b7f22484df`, parts a and b; c and d are already done).
4. **`catalogue_local`'s quarantine refuses** (`ee3d4404718a`) — verified by hand twice now, still
   unpinned.
5. Five more named by batch M: `stop_subsystem`'s unrecordable arm, `tiers.main()` refusing on a
   containment violation, `gpu_lane.status()` setting `partial`, `dashboard.movement()` omitting
   an unmeasurable row, `hostcheck.score()` not firing the veto below `ABOUT_MIN`.

## 3. THE SWEEP41 FINDINGS WORTH DOING FIRST

Thirty orders were filed by run41's sweep. Ranked by what they actually cost:

1. **`f7b611d107cb` (done) / the loss mode it names (not done).** `ledger_guard.seal()` now routes
   through `append_line`, but note *why* it mattered: a cleanly lost whole link passes
   `verify_chain()` because the survivor's `prev` still points at its true predecessor. There is
   no net for that. Torn lines are caught; **lost** ones are not.
2. **`aeeba9364147` + `d7620dd893fa`** — `liveness.py` and `silence.py` both list `src/`
   non-recursively, so the check-that-cannot-fail detector and the silent-handler auditor are both
   blind to `src/deprecated/`. Third occurrence of a class fixed twice elsewhere and never
   propagated.
3. **`5bbbb65e7787`** — `drill.py`'s park nets call the real `escalate()` against synthetic
   subjects and `escalation.py:248` forwards every escalation into `health.record()` with no
   self-test filter. 7 of 67 keys / 42 of 4,054 events in `state/failures.json` are rehearsal
   noise, growing every run, shaped exactly like real MANAGER-rung faults. The `SELFTEST_SUBJECT`
   convention already exists in `workorders.py` and was never applied here.
4. **`b9584c782d95`** — `feats.py --roll` silently skips sources absent from the resolved-host map
   and counts the exclusion nowhere. 9 sources, 727 entries, invisible to the live crawler.
5. **`556c1b8fda9f`** — a seventh `local_agent` write-gate bypass: NTFS hard links are not
   resolved by `realpath` the way junctions are. Verified experimentally, not reachable today.
6. **`0a45c595655b`** — `write_record_catalogue`'s fold reverts corrected `category` and
   re-introduces raw markup into `description` on any re-catalogue.
7. **`e3c220e87d57`** — `codewatch.stamp()` can stick at `None` and then treat every later check
   as "nothing changed", silently, across all six standing daemons.
8. **`f307490add1e`** — make `sweep_plan.record()` validate; see §4.
9. Five `DRILL_PROBE_LEDGER_LEAK` sites (`5fa88a896c3f`, `630fe4529c51`, `31a946e96c69`,
   `b53dd5b3f76f`, `247b173c78ee`). One of the five is fixed; four remain. Each is a probe that
   should use `_deliberately_failing` / `_quietly` and does not.

- **`8aaddf34adf3` (MAJOR) is the one to read first in this list.** The ledger-escape
  detector added at the very end of run #41 (verify_math §20z, an in-process spy on
  `health.record`) reports clean while two `custodes.py:abstained-*` classes grow by +1
  each on every battery run. Proven by control: a 140s window with no battery running
  changed nothing. The agent that built the spy concluded the opposite from the spy
  itself. Fix the detector before trusting anything it says: compare
  `state/failures.json` before and after the run, which is what caught it.

## 4. THE QUEUE AND THE RUNGS

**376 open at close** (OWNER 111, LOCAL 127, SESSION 59, RUN 57, BOTS 22). RUN fell 129 → 57 and
BOTS 40 → 22; the total is higher than mid-shift because the sweep filed 30 new findings
and the post-close verification filed one more.

- **LOCAL (127) was not worked at all this shift** and is the single biggest opportunity for the
  next one. It is unmetered. Run #41 measured that **0 of them are addressed to a rung that cannot
  reach them** (the "13 of 28" claim in `9b54659bc403` is stale — the last 2 stragglers were
  re-addressed and the detector self-closed `1d54acf05414`). The blocker was practical, not
  structural: the GPU sat at 97% with the pipeline's own work, and one round trip took >400s, so
  feeding 127 orders through it while thirteen agents were editing `src/` would have collided.
  **Do it when the tree is quiet**, a few lanes wide, and verify with the battery afterwards.
- **`9b54659bc403` stays open** for its design half only: `file_order()` should refuse or re-route
  a LOCAL order whose `where` is entirely denied, by asking `local_agent._denied_target(rel)` —
  the predicate `t_propose_patch` itself uses — rather than re-deriving the denylist. Whether it
  refuses or silently re-addresses is an owner call.

## 5. HOUSEKEEPING THAT IS CHEAP AND KEEPS BITING

- **Never put backticks in `--how` or `what` text, and never pass order text as a shell argument.**
  See `1c99df1f69c1`. It cost a 16-minute unsanctioned pipeline run this shift and two permanently
  garbled entries in the append-only closed log.
- **`sweep_plan.record()` takes bare `foo.py`,** as `batches()` emits it. Five of fifteen batches
  got the spelling wrong in run41 and their coverage read as never-read.
- **`state/failures.json` carries 6 synthetic counts from run #41's own verification** —
  `append_line-unlocked:None` ×1, `append_line-unlocked:OSError:None` ×2, and 3 of the
  `append_line:FileNotFoundError` total. Attributed here rather than removed: `triage_swallowed`
  deliberately no longer clears that ledger, and racing its merge is worse than six known counts.
- One order (`f5fdaab825a6`) is worth more than its MINOR rung suggests: `publish.git()` clipping
  git's diagnostic at 220 characters is what disguised a 403 as a missing `gh.exe` for days.

## 6. BATTERY AS RUN #41 LEFT IT

`verify_math` **1125 passed / 0 FAILED** · `drill` **378 nets / 0 BREACHED** · pyflakes clean ·
`liveness` 47 · `health --preflight` all pass · `secondopinion` all three tools RAN, secrets **0**
by two independent scanners · `axis_correlation` n=45, unchanged, no `--write` owed ·
`corpus_db` rebuilt at shift open (216 sources, 282,822 entries) · sweep41 coverage **116/116,
`missing()` empty**.
