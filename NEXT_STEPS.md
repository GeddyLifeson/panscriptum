# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #27 wrote this on 2026-08-25 ~08:2x local.*

**THE THREE OWNER RULINGS OF 2026-08-25 STILL SHAPE THE RUN. Read these first.**

1. **EVERYTHING AMISS IS INVESTIGATED THE MOMENT IT IS SPOTTED** — worked on sight, never filed
   for later. **What is allowed to survive into this file is what needs an OWNER RULING**
   (a charter question, a routing-policy choice, a contract change with real blast radius), plus
   the sweep's verified-but-unrepaired tail in §3, which is REAL WORK, not a backlog of excuses.
2. **THEN, IMMEDIATELY: THE FULL COMPREHENSIVE SWEEP — every line of every module, every run.**
   `python src/sweep_plan.py --batches 16`, one sonnet-tier agent per batch, all launched
   together; each writes its full report to `handoff/sweep<N>/AUDIT_batchNN.md` and returns **only
   a compact summary**. Then `sweep_plan.missing("run<N>")` **proves** coverage.
   **Run #27's pass: 95 modules, 40,728 lines, 0 uncovered, 16 reports (12.9–29.0 KB, 336 KB).**
   **Launch the 16 agents FIRST and work the immediate queue while they run.** Note `sweep_plan.py
   --batches N` prints a trailing `# 95 modules...` comment line after the JSON — strip from the
   last `]` before parsing, or use `sweep_plan.batches(16)` directly.
3. **AN UNRECOGNISED FAILURE IS A BUG, NOT WEATHER.** If `every pool failure is recognised` is
   red, it is the run's first job — but see lesson 16: **read the AGE column before believing it.**

**And the standing lessons. 16, 17 and 18 are new.**

4. **VERIFY THE CADENCE WITH `list_scheduled_tasks`. NEVER FROM A FILE, INCLUDING THIS ONE.**
   Hourly, `11 * * * *` + 523s jitter, firing ~:19–:20. The **15 minutes in the overlap guard is
   the heartbeat-staleness threshold** — a different number answering a different question.
5. **BOUNCE WHAT YOU CHANGED, OR YOU CANNOT SEE THAT YOU FIXED IT.** STANDING =
   `{dashboard, publish, foreman, overwatch, pipeline}` (keeper restores in 300s); `read.py` and
   `feats.py --roll` are OUTSIDE it and cost a supervisor lap (M15). **Run #27 confirmed the
   converse is checkable in one command:** `Get-CimInstance Win32_Process` start times showed all
   five restarted 06:51, after run #26's 06:42 commit — so the page was trustworthy that hour.
   Check start times before spending a run on a stale-import hypothesis.
6. **AGE `data/COVERAGE.json` BEFORE BELIEVING ANY COVERAGE STALL.** `cited`/`settled`/`feats`
   come from it (written once per supervisor cycle); `entities read`/`chunks` come from a live
   glob and log tail. Batch 11 confirms `dashboard.movement()` cannot tell a real stall from the
   file's write cadence — `settled` and `standards met` read `stalled` on the run #27 page purely
   because `COVERAGE.json` had not been rewritten.
7. **AGE EVERY `bucket_state.last_error` ROW AND READ THE TEXT.**
8. **AGE EVERY FILE A STANDARD READS — ESPECIALLY WHEN IT READS GREEN.**
9. **A CHECK THAT CANNOT FAIL LOOKS EXACTLY LIKE A CHECK THAT PASSED.** Run #27's m163 is the
   sharpest instance yet: `"" in t` is True for every `t`, so an empty citation passed the
   VERBATIM guard **always** and took an unrelated feat as its evidence.
10. **A GUARD CAN FAIL BY DOING THE THING IT PREVENTS.**
11. **A BARE NUMBER IN A LOG IS NOT A DIAGNOSIS.** m167: `stranded: 227` became actionable the
    moment it said *which source*.
12. **A GUARD THAT MATCHES ONLY THE UNOBFUSCATED SPELLING IS GREEN ON PURPOSE, FOR EVER.**
13. **DO NOT MATCH PROCESSES BY A LITERAL YOUR OWN COMMAND LINE CONTAINS.**
14. **AN OWNER RULING IS NOT APPLIED UNTIL EVERY FILE OF THAT SHAPE IS VISITED.** Run #27 found
    two more: `wh40k.py` (twin of the already-fixed `zfighters.py`) and `tiers.py`'s
    `deliberate_joins` (fourth member of the `shared_sample` family). **When you fix a shape,
    GREP THE TREE FOR IT.** It has now produced findings in six consecutive runs.
15. **ONE FRESHNESS WINDOW CANNOT SERVE TWO QUESTIONS.** `provider_error`'s 180s gate is right
    for BENCHING and far too narrow for EXPLAINING.
16. **[NEW, RUN #27] A CAP ON A DIAGNOSTIC HIDES THE PATTERN, NOT JUST THE ROWS.** This is why
    Hard Rule 0 covers the page and not only the data. `standards.py:952` showed 3 of 14
    unrecognised rows; **all 14 were the same shape**, and from three samples that is invisible —
    run #26 read the top row, chased it alone, and recorded the rest as "genuinely unexplained".
    Uncapped, one glance settles it. **Ask of every truncated diagnostic: could the thing I most
    need to notice only be visible in the part that was cut?** Sibling caps still open are
    listed in §3; batch 01 found two inside `verify_math` itself.
17. **[NEW, RUN #27] A BATTERY RESULT IS EVIDENCE ONLY ABOUT THE TREE AS IT STOOD WHEN IT RAN.**
    Run #26 ran `verify_math`, made one more edit, and recorded "719 passed, 0 FAILED"; the run
    ended red and nobody knew for an hour. **Re-run after the LAST edit, not the last interesting
    one**, and treat a predecessor's green as a claim to re-test, not a fact to inherit.
18. **[NEW, RUN #27] WHEN A NUMBER WON'T EXPLAIN ITSELF, THE CAUSE MAY NOT BE IN THAT SUBSYSTEM
    AT ALL.** Three runs worked `model calls per hour` from the pool while the constraint was a
    semaphore in the reader — and the ceiling was derivable all along by multiplying two numbers
    nothing on the page multiplied. **When every sub-standard is green under a red headline, stop
    subdividing the headline and go looking for a limiter OUTSIDE it.**

## 1. OWNER RULINGS NEEDED — these are blocking real work

1. **[M19, NEW — THE BIGGEST ONE] SHOULD THE READER SQUEEZE CLOUD CALLS THROUGH THE GPU CARD'S
   SEMAPHORE?** Measured run #27, end to end. `read._ask` (`read.py:327-337`) runs the *whole*
   transport ladder — cloud attempt included — inside whichever gate `tuning.regime()` selects.
   On `local`/`starved` that is `GATE_LOCAL_N` = the **card's** parallelism (2), not
   `GATE_CLOUD_N` (16), and `tuning.profile()` drops workers to match. **900 × 2/16 = 112.5;
   observed 112.** The gate's stated purpose is to stop over-subscribing the card, and a cloud
   call never touches the card — so it is also *starving the local calls the gate exists to
   reserve*. Regime flipped to `cloud` twelve minutes later and throughput went **112 → 280**.
   **Three options, all policy:** (a) acquire the local gate only around the local call;
   (b) keep the ladder gated but size it `max(GATE_LOCAL_N, some cloud width)`; (c) leave it and
   accept the ceiling on a starved machine. Also worth ruling on the trigger:
   `CLOUD_MIN_SUCCESS` = 0.35 lost by **1.7 points** on a 24-call sample, and the loop is
   self-feeding — narrow gate → few calls → noisy sample → narrow gate. Batch 06 adds that the
   sample is dominated by the one or two buckets `quality_first` ranking sends the traffic to.
   **The state is now visible on the page** (`the reader's gate is open`), so a ruling can be
   checked the moment it lands.
2. **[M20, NEW] THE ENTRYPASS DONE-MARKER IS POSITIONAL AND ANOTHER WRITER MUTATES THE LIST.**
   227 entries stranded, all in `Gundam`. `f"{source}#{start}"` is an index; insertion or
   re-ordering slides entries into a range already marked done and nothing re-opens a batch.
   Re-keying by content invalidates every marker on disk and re-runs entrypass across the corpus
   — real model spend on the constrained pool. **Rule: re-key, back-fill just the stranded
   entries, or accept and document?**
3. **[DECISION C, NOW MEASURED] `publish._scrub()` CLAIMS TO REFUSE "ANYTHING CREDENTIAL-SHAPED"
   AND MATCHES 8 VENDOR PREFIXES.** (`publish.py:145-164`, batch 03.) AWS keys, Slack tokens,
   generic bearer tokens and PEM blocks pass through unredacted into the **published** repo. The
   docstring is the dangerous part: it reads as a guarantee. **Either widen it or correct the
   claim — but this one is about what leaves the machine, so it wants your call, not mine.**
4. **[M18, CONFIRMED A FOURTH TIME] `axis_score()` RETURNS A FLAT 9.9 FOR EVERY INPUT AT M10.**
   Re-confirmed unchanged at source this run (batch 15). `ledger.py:127-133` answers the same
   missing edge case a different, incompatible silent way; `tempus.band_resolution()`
   (`tempus.py:199-210`) already implements the correct fallback and was re-verified correct this
   run. **Which behaviour is right at the top rung is a charter question.**
5. **[STILL OPEN] THE INSTRUMENT'S FLOOR→CEILING INVARIANT IS VIOLATED AND `anchors.py` EXITS 1.**
   Re-run live this run: `A Sword` (0.10) below `The Skate Guy` (0.22); `Goku` (5.42) below
   `Yggdrasil` (6.18). Related: `assay.py:302-322`'s `_SCALE` rescale discards the raw sigma the
   adjacent comment says was calibrated to the charter's Kenshiro `±0.12`.
6. **[M15, STILL OPEN — AND IT IS NOW COSTING A SECOND RED STANDARD] THE FOREMAN KILLS JOBS FOR
   LOOKING STALLED WHEN THE POOL IS WHAT STALLED.** Batch 15 traced `the automation reproduces
   the charter` sitting **33h stale** to exactly this: `foreman` re-dispatches
   `magnitude.py --calibrate` roughly hourly (01:38/02:32/03:49/05:27/06:30 in `state/foreman.log`)
   and **`kill_stalled_job` kills every attempt before it reaches its final write**. The producer
   never stopped; it is being killed. Batch 04 adds that `run_charter_regression` has an explicit
   pool-health gate and the `corpus read is progressing` remedy has **none**, and that
   `reprove_pool` returning True at zero answering buckets silently disables its own paired
   `restart_reader` fallback.
7. **[M16, STILL OPEN] `feats.api()`'s RETURN CONTRACT.** Re-verified unchanged (batch 08). A
   public-signature change needing a review cycle. `discover()`/`fetch()` share the shape.
8. **[STILL OPEN] OVERWATCH'S ZERO IS NOT EVIDENCE.** 51 of 69 findings ever filed were retired
   with no model verdict. Batch 13 adds a **compounding** defect: `overwatch.py:652` dedups by
   fingerprint **key existence only, not state**, so a retired finding can never reopen — the same
   live bug rediscovered later is silently swallowed. Retirement policy is a routing decision;
   the `foreman._retire()` second-writer bypass is arguably just a two-writer violation and could
   be fixed without a ruling — **say which.**
9. **[STILL OPEN] `retry_synthesis.py:60`'s `sorted(...)[:14]` IS A HARD RULE 0 CAP WITH A COST.**
   Batch 09 confirmed by direct diff that the docstring's "byte-identical to phase_synthesis" is
   false. Making it faithful multiplies model calls per retried source. **Rule on it and it takes
   ten minutes.**

## 2. Machinery worth building (no ruling needed, just time)

- **Give `allsweep.reconcile()`'s `note()` a severity, so the tier can gate.** Still ungraded and
  still honestly printed as such (16 rows this run, "read them, they are not all faults").
- **Behavioural checks to replace `verify_math`'s source-greps.** m164 is the proof they
  false-fail; batch 01 lists more (`verify_math.py:2262-2268`, `2094-2098`, others). Each one
  that greps a literal is a check that will go red the next time someone improves the code.
- **`standards.py`'s probe/unexpected split is a hardcoded 6-substring match on SITE NAME.**
  Batch 03 adds that `"hostcheck.py:candidates"` in that list matches **zero** call sites today.
- **Four standards still have no staleness gate** while five siblings in the same file do.
- **[NEW, batch 03] Most data-file-backed standards VANISH on a read error instead of reporting
  UNMEASURED** — including three HIGH ones sharing one `ALLSWEEP.json` try block. A standard that
  disappears is green by absence. The fix pattern already exists in the same file (lines 739-750),
  applied to exactly one standard.
- **[NEW, batch 03] `every declared floor is measured` slices `src[idx("def check("):]` with no
  end bound**, so it scans `report()`/`main()` too — a constant used only outside `check()` reads
  as measured.
- **`sweep_plan.record()`'s cross-process lost update** — `_RECORD_LOCK` is a `threading.Lock`.
  `missing()` is verified safe (both failure paths over-report gaps, never a false "0 uncovered"),
  so the coverage proof stands. Run #27 side-stepped it by recording all 16 batches from one
  process after verifying the reports on disk; that is a workaround, not the fix.

## 3. Verified sweep findings I did not repair this run — real work, with file and line

**Reproduced-live crashes and false claims**
- `zfighters.py:474` — `--full` crashes `KeyError: 'provenance'` on Son Goku (merged-in
  `REFERENCE_ASSAYS_PRESENCE.json` axes lack the key ROSTER-built axes always have). `:24-29`'s
  headline claim is false against its own output: Vegito outranks Goku 7.63 vs 7.60.
- `sevenfold.py:204` — world-level `shelve()` gets empty weights, degenerating `seams()` into
  k-1 singletons + one giant block; reproduced (50 members → [44,1,1,1,1,1,1]).
- `reference.py:245` — `shelfmark()` hardcodes `RUNGS[3+i]` assuming `upper` has exactly 3
  elements; reproduced silent wrong output with non-3-part tier_keys.
- `gpu_lane.py:270` — `_take_slot` skips `_expired()` when `rec is None`, so a **corrupt** slot
  lease starves that index forever; reproduced live with an injected corrupt `slot.0.json`.
  `:66-67` `int(os.environ[...])` with no try/except crashes module import for all 9 processes,
  contradicting the file's own "FAIL OPEN, ALWAYS".
- `coverage.py:10-18 vs :82-115` — docstring promises 5 states incl. UNREACHABLE ("the only state
  that is purely a defect"); `state_of()` returns 4, and fetch-failed collapses into NO PAGE.
- `autostart.py:131-133` — `_twin_watchdog()` returns False on any failure of its own detection
  call, defaulting to "proceed" — re-opens the multi-watchdog respawn loop its docstring fixes.
- `scope.py:106-114` — `build()` sets `out[h]=None` on failure then permanently skips `h`
  thereafter: m143's failure-memoisation bug, unfixed here.
- `identity.py:180-207` — `_is_continuity` requires n>=2 bearers, so a single-bearer designator
  (the module's own "(Fates)" example) can never be recognised; risks merging two continuities.

**Silent truncation / data loss (lesson 16's list)**
- `read.py:605-760` — `cap_chunks`/`--chunks` truncates before the ask loop; capped entity caches
  "complete". `skipped` now also conflates mention-filtered with cap-excluded.
- `hostcheck.py:419-420,538` — `null_rate()` folds a failed baseline probe to `0.0` and caches it
  process-wide; `judged_any` lets one wrong-but-reachable candidate justify unassigning a source
  whose real host merely timed out. `--repair` still has no `--go` gate.
- `chain.py:108` — `unmatched.most_common(40)` truncates a field written into `CHAIN.json`.
  `:354` uses a truncated string as a dict key (m37's class, unfixed).
- `local_agent.py:561` — `json.dumps(res)[:SLICE]` can produce invalid JSON and cuts the
  disclosure fields off every large read. `:406-407` `modname=None` for ANY non-`.py` extension
  skips the denylist and all three gates. `:446-476` no lock around write/gate/revert.
- `genre.py:135,182,187` — `most_common(top=3)` truncates ranked genres AND the confidence
  denominator, inflating confidence; sibling cap already fixed in the same file.
- `backfill.py:176` — "already held" set built from ALL entries, not just Persons, so a name
  collision with any Faction/Place/Vessel hides a real missing character.
- `wiki_source.py:549-568` — `category_members` returns a partial roster on transient API failure
  with no completeness flag; a plausible live cause of DC under 1%.
- `weave_index.py:224` + `weave.py:195-198` — `description[:400]` at write time blinds the
  mechanic-detection regex to any tell later in the text. Downstream consumer traced.
- `feats.py:348-361` — `aplimit=500`/`srlimit=50`, no continuation (m82).
- `ingest_doc.py:216` — entity description hard-truncated to 2000 chars, no disclosure.
- `dashboard.py:296 vs 301` — `swallowed[:6]` is an unfixed twin of the findings-list cap the
  adjacent comment says was fixed 2026-08-24.
- `health.py:220-253` — `check_caches()` samples `files[:200]` per host dir with no justification.
- `scope.py:81` — `titles[:8]`; `:86-93` no-signal fallback reintroduces frequency bias.
- `verify_math.py:286` (`_problems[:3]`) and `:811` (`build_all(limit=400)`) — the suite's own two.

**Swallowed / indistinguishable failures**
- `dashboard.py:284-305` — `_watch()` defaults to `{open:0, high:0}` **before** the try, so an
  `OVERWATCH.json` read failure is indistinguishable from zero findings; sibling `movement()` was
  hardened against this exact class and `watch()` was not.
- `silence.py:115-138` — `uses_exc` always True; `records` substring-matches the whole ast dump.
  `:115-122` and `:378-381` silently return `[]` for any unparseable file — the audit undercounts
  invisibly, in two sibling places.
- `endpoint.py:327-334` — `fetch_html`'s `one()` swallows every exception; `fetch_raw` got the
  404/410 split (m15) and this did not.
- `completeness.py:194-268` — `host_reachable()` gates on API-mode-only `api_url()`, so RAW-mode
  wikis always read unreachable. **This is the standing `health --preflight` dandwiki failure.**
  `:110-118` writes a shared cache via fixed-name tmp from a 6-worker pool.
- `catalogue_models.py:88-106` — 200-but-empty and unreachable collapse; `last` leaks a stale
  exception across retries. `:158` `r["models"][:10]` is the unfixed half of m145.
- `context_budget.py:242-271` — prompt-file read failure defaults to `""` with no log, in both
  `feats_block_budget()` and `report()`; live via `manifest_builder.py:331`.
- `cascade_bridge.py:225-234` — `_interval()` returns `0.0` (no pacing) on any exception.
- `magnitude.py:668-677` — retry-on-all-citations-failed doesn't fire when honest status axes
  coexist with all-failed numeric axes. `:451-482` per-slice transport failures silently skipped.

**Concurrency / contract**
- `runguard.py:98-121` — `claim()` has no atomic test-and-set (the module exists to fix this).
- `publish.py:283-290` — shared `docs/state.json` written with a fixed `.tmp` + bare `os.replace`;
  the file's own `push()` docstring admits two concurrent writers.
- `foreman.py:150/158,255-267,715,1041,1126,1247` — **every** shared JSON write uses a fixed-name
  temp, reopening the race `silence.write_json`'s docstring says was closed repo-wide.
  `:794-806` `_function_source` drops class qualifiers and walks by bare name — `endpoint.py` has
  two functions named `one` today, so the model could be asked to fix the wrong one.
- `health.py:61-144` — `flush()`'s read-merge-write on `state/failures.json` has a
  `threading.Lock` only, on explicitly the highest-traffic multi-process shared file.
- `endpoint.py:83-94` — `_save()` fixed temp name + `threading.Lock`, never migrated.
- `cascade_bridge.py:502-542` — `record_unrecognised` RMW race across processes; the comment
  declares the hazard closed but only the write-collision half is fixed.
- `resync_roll.py:65-68` — "Fixed 2026-08-25" made only the WRITE atomic; the
  read→full-scan→write clobber window is fully open. **A fix comment hiding an open bug.**
- `scout.py:200-206` unlocked RMW of `WIKI_HOSTS.json`; `:208-218` `--dry` still writes
  `SCOUT_BLOCKED.json`.
- `magnitude.py:966-983` — `run_batch` writes `ASSAYS.json` raw, fixed-name tmp.
- `pipeline.py:521` — `write_record`'s drift-merge is gated on entry **count** only; same-count
  content drift takes the fast path and overwrites disk with the stale in-memory copy, silently.
  `:1327` `update_handoff` uses raw `os.replace`.
- `worldseed.py:317-322`, `manifest_builder.py:436-437`, `burgs.py:226-229`,
  `retry_synthesis.py:44-47`, `module_index.py:75` — raw writes to shared files.
- `dashboard.py:349-369` — `movement()` RMW on `dashboard_history.json`, no lock, under
  `daemon_threads=True`. `:150-168` `throughput()` never closes its sqlite connection.
- `address_space.py:106-142,251-252` — `fit()` modulo-wraps overflow where `pack()` raises; a
  silent tier alias means an ambiguous shelfmark.

## 4. The pool, for whoever reads the page next — NOW ANSWERED

Run #26 left two candidate causes, "neither confirmed", and said instrument before fixing. Run #27
instrumented, and **both are true and they compound**:
- **The volume ceiling is the reader's gate (M19).** `regime` → `local` → 2 permits, not 16.
  900 × 2/16 = 112.5 against an observed 112. This is the binding constraint.
- **The concentration is the router's ranking.** Batch 06 traced it into
  `C:\Users\imarl\cascade\cascade\router.py`: strategy is `quality_first` (config.json:6), which
  ranks by static config rank with a headroom tie-break. `nvidia:free` is rank 89 and
  `gemini:*` 85-88, which is exactly the observed near-monopoly. Inflight-based spreading only
  activates under real concurrency — and the gate above ensures there is none. Rotation exists
  **only** in the widen-fallback (`cascade_bridge.py:763-789`, verified correct by hand), which
  is gated behind the primary pool fully failing and is therefore essentially unreached.
  Also: `cascade_bridge.py:259-266`'s "sixteen buckets / five local" comment is stale — the
  coding pool has 40 models across 27 buckets.
- The pool is **also** genuinely part-dry: Groq at tokens-per-day, OpenRouter's free-models-per-day
  spent, Cohere on a 1000-call trial month. That is real and unrelated to the two above.
