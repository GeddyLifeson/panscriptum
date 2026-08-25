# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #26 wrote this on 2026-08-25 ~07:0x local.*

**THE THREE OWNER RULINGS OF 2026-08-25 STILL SHAPE THE RUN. Read these first.**

1. **EVERYTHING AMISS IS INVESTIGATED THE MOMENT IT IS SPOTTED** — worked on sight, never filed
   for later. **What is allowed to survive into this file is what needs an OWNER RULING**
   (a charter question, a routing-policy choice, a contract change with real blast radius), plus
   the sweep's verified-but-unrepaired tail in §3, which is REAL WORK, not a backlog of excuses.
2. **THEN, IMMEDIATELY: THE FULL COMPREHENSIVE SWEEP — every line of every module, every run.**
   `python src/sweep_plan.py --batches 16`, one sonnet-tier agent per batch, all launched
   together; each writes its full report to `handoff/sweep<N>/AUDIT_batchNN.md` and returns **only
   a compact summary**. Then `sweep_plan.missing("run<N>")` **proves** coverage.
   **Run #26's pass: 95 modules, 40,431 lines, 0 uncovered, 16 reports on disk (15.5–32.4 KB).**
   **Launch the 16 agents FIRST and work the immediate queue while they run** — run #26 did this
   and the first batch reported back before the opening diagnostics were finished.
3. **AN UNRECOGNISED FAILURE IS A BUG, NOT WEATHER.** If `every pool failure is recognised` is
   red, it is the run's first job. **Read the ledger before believing its size** — see lesson 8.

**And the standing lessons. 14 and 15 are new; 14 is this run's whole spine.**

4. **VERIFY THE CADENCE WITH `list_scheduled_tasks`. NEVER FROM A FILE, INCLUDING THIS ONE.**
   Hourly, `11 * * * *` + 523s jitter, firing ~:19–:20. The **15 minutes in the overlap guard is
   the heartbeat-staleness threshold** — a different number answering a different question. Do
   not "fix" it to match the schedule.
5. **BOUNCE WHAT YOU CHANGED, OR YOU CANNOT SEE THAT YOU FIXED IT.** Run #26's opening diagnostic
   showed `every pool failure is recognised` red on two rows run #25 had ALREADY classified — the
   process rendering the page carried a launch-time import from before that commit. **A long-lived
   job is a photograph of the code at its launch.** Run #25 shipped the fix and did not bounce the
   readers, so the page reported a fixed system's pre-fix answer for an hour. STANDING =
   `{dashboard, publish, foreman, overwatch, pipeline}` (keeper restores in 300s); `read.py` and
   `feats.py --roll` are OUTSIDE it and cost a supervisor lap — do not kill them casually (M15).
6. **AGE `data/COVERAGE.json` BEFORE BELIEVING ANY COVERAGE STALL.** Under 0.5h → real; over →
   artefact. `cited`/`settled`/`feats` come from `COVERAGE.json` (written once per supervisor
   cycle); `entities read`/`chunks` come from a live glob and a live log tail.
7. **AGE EVERY `bucket_state.last_error` ROW AND READ THE TEXT.** Rows 27–37 HOURS old are not
   evidence about now — but see lesson 15: too NARROW a window has its own failure mode.
8. **AGE EVERY FILE A STANDARD READS — ESPECIALLY WHEN IT READS GREEN.** A stale file producing a
   false ALL-CLEAR is never looked at again. **Ask of every green high-severity standard: how old
   is the evidence?**
9. **A CHECK THAT CANNOT FAIL LOOKS EXACTLY LIKE A CHECK THAT PASSED.** When something has never
   once failed, that is the finding. Run #26 found four: `anchors.py` printing its invariant and
   exiting 0 (m155), `allsweep` grading two of four tiers (m156), the `or True` guard blind to the
   wrapped spelling (m159), and overwatch's 0-open reading off 51-of-69 unverified retirements.
10. **A GUARD CAN FAIL BY DOING THE THING IT PREVENTS.** `endpoint.register()` this run: it
    overwrote the registry it could not read (m139), the same sentence as run #24's `write_record`
    in a second file. **Read every `except` above a write and ask what the variable being written
    still holds.**
11. **A BARE NUMBER IN A LOG IS NOT A DIAGNOSIS.** Anywhere the code prints a raw code, ask whether
    anything can say what it MEANS.
12. **A GUARD THAT MATCHES ONLY THE UNOBFUSCATED SPELLING IS GREEN ON PURPOSE, FOR EVER.**
    Case, alias, encoding, separator, wording — **and now line-wrapping** (m159). Ask of every
    guard: what are the OTHER spellings? And check the test that decides whether the guard runs.
13. **DO NOT MATCH PROCESSES BY A LITERAL YOUR OWN COMMAND LINE CONTAINS.** Assemble the needle at
    runtime or use `lognames.OWNER`. Never a bare literal.
14. **[NEW, RUN #26] AN OWNER RULING IS NOT APPLIED UNTIL EVERY FILE OF THAT SHAPE IS VISITED.**
    One step earlier than lesson 12. The ruling gets made, applied to the file in front of it, and
    the identical construction one module over is never opened. **In three of run #26's four cases
    the sibling file carries a comment naming the ruling BY DATE while the unfixed file sits
    beside it** — which is what makes the shape survivable: it looks done from every angle except
    the one nobody checked. `cosmology_graph.py` kept an `< 8` cap on the same `shared_sample` key
    `weave.py` and `pipeline.py` were both fixed on (m144); `rosetta.py` kept a bare write while
    `scout.py`/`grounding.py`/`coverage.py` all name the sweep that fixed theirs (m151);
    `chain.py` kept two of m100's twelve temp names (m152); `backfill.py`'s subcategory cap was
    fixed at the inner loop and left standing one line up (m140).
    **When you fix a shape, GREP THE TREE FOR IT and fix every instance in the same run.**
15. **[NEW, RUN #26] ONE FRESHNESS WINDOW CANNOT SERVE TWO QUESTIONS.** `provider_error`'s 180s
    gate is exactly right for BENCHING — claiming a stale row benches a live provider for four
    hours (m103's harm) — and far too narrow for EXPLAINING, because during a burst the engine's
    aggregate arrives minutes after the provider row that explains it. The biggest open
    unrecognised row (`gpt-oss-120b`, x30, holding a HIGH standard red) had its cause sitting in
    `bucket_state` the whole time: a Groq tokens-per-day limit. **Ask of every age gate: which
    question is it answering, and is something else quietly asking the other one?**

## 1. OWNER RULINGS NEEDED — these are blocking real work

1. **[M18, CONFIRMED A THIRD TIME] `axis_score()` RETURNS A FLAT 9.9 FOR EVERY INPUT AT M10.**
   Two independent agents re-confirmed it this run, one by live numeric test: `assay.py:221-223`
   returns `9.9` for x = 1e30, 1e33, 1e36 and 1e40 alike, ten orders of magnitude collapsed to one
   number, while the docstring states a log-interpolation. It is LIVE: `magnitude.py:244` calls it
   inside `quantity_scores()`, whose results overwrite `scores[ax]` at `magnitude.py:706-707`.
   `ledger.py:127-133` answers the same missing edge case a **different, incompatible** silent way
   (`hi == lo` → `joules` collapses to the M10 floor regardless of `ruin_score`).
   **New this run:** `tempus.band_resolution()` (`tempus.py:199-210`) already implements the
   correct fallback for this exact edge case — "inherits the M9→M10 width" — so the repair exists
   in the tree and simply was not reused. The bottom rung M0 has no equivalent bug (its clamp is
   documented, deliberate and tested). **Which behaviour is correct at the top rung is a charter
   question. Either resolution changes computed magnitudes across the library.**
2. **[NEW] THE INSTRUMENT'S FLOOR→CEILING INVARIANT IS CURRENTLY VIOLATED, AND `anchors.py` NOW
   SAYS SO OUT LOUD.** Measured run #26: `A Sword` (0.10) sits BELOW `The Skate Guy` (0.22), and
   `Goku` (5.42) below `Yggdrasil` (6.18). The script used to print this and exit 0; it now exits
   1 (m155), so `allsweep`'s instrument tier will start reporting it. **Whether the ordering or the
   scores are wrong is an assay question, not a script fix.** Related and probably the same
   subject: `assay.py:302-322`'s `SIGMA_BY_ATTESTATION` rescale (`_SCALE`) silently discards the
   raw sigma (4.08) the adjacent comment says was calibrated to reproduce the charter's Kenshiro
   `±0.12` — live-verified, `A.assay()` on that scenario now returns interval `0.06`, **half the
   claimed calibration**. A likely direct contributor to `the automation reproduces the charter`
   sitting red.
3. **[M15, STILL OPEN] THE FOREMAN KILLS THE READER FOR LOOKING STALLED WHEN THE POOL IS WHAT
   STALLED.** Unchanged and re-confirmed at source this run (`foreman.py:342-384,387-460`). Three
   possible fixes, all design choices: teach the stall remedies to check pool refusal first and
   decline; put `read.py` in `STANDING`; or make the kill notes tell the truth about how long
   "next cycle" is for a non-STANDING job. **Additionally found this run:** `reprove_pool`
   (`foreman.py:161-162,753`) returns True even when **zero** buckets answer, deadening its own
   escalation into `restart_reader`.
4. **[NEW] OVERWATCH'S ZERO IS NOT EVIDENCE.** Of 69 findings ever filed, **51 were retired with
   no model verdict**: 27 by `overwatch.py:623-629`'s whole-file digest (any edit anywhere in the
   file retires every open finding in it, unthrottled, before `verify_open` runs) and 24 by
   `foreman._retire()` (`foreman.py:1016-1038`), a **second, unguarded writer to OVERWATCH.json**
   that bypasses overwatch's own merge contract and matches by `(module, symbol)` rather than
   fingerprint. Only 12 (17%) were genuinely re-checked. `_ask`→None is correctly NOT treated as
   refuted. **Retirement policy is a routing decision; the second-writer bypass is arguably just a
   two-writer-contract violation and could be fixed without a ruling — say which.**
5. **[M16, STILL OPEN] `feats.api()`'s RETURN CONTRACT.** Re-verified line by line this run, holds
   exactly as described, no drift. The repair changes the contract across every caller — a
   public-signature change needing a review cycle. **New this run:** `discover()`/`fetch()`
   (`feats.py:311-368,427-453`) share the identical shape and fire on **every** `roll()` entity via
   `evidence_for()`, a broader blast radius than M16's own text names.
6. **[NEW] `retry_synthesis.py:60`'s `sorted(...)[:14]` IS A HARD RULE 0 CAP AND THE FIX HAS A
   COST.** Its docstring claims "byte-identical prompt construction to phase_synthesis", which is
   false: `pipeline.phase_synthesis` chunks ALL feat-bearing entries in groups of 14 and takes the
   best band across chunks (the m13 fix the owner ruled on 2026-08-24); this truncates to 14.
   **I did not fix it this run on purpose.** Making it faithful multiplies model calls per retried
   source — on a pool currently at 32 calls/hour against a floor of 900, that is a routing decision
   with blast radius, not a mechanical repair. **Rule on it and it takes ten minutes.**

## 2. Machinery worth building (no ruling needed, just time)

- **Give `allsweep.reconcile()`'s `note()` a severity, so the tier can gate.** Run #26 tried
  summing `len(findings)` into `bad` and a green machine reported 16 bad subsystems — because the
  same undifferentiated list holds `catalogued sources with no host` (a real disagreement) beside
  `phases implemented 8` and `running 1 dashboard.py` (healthy facts). Reverted and documented in
  the code. Until a severity exists the tier prints as explicitly **ungraded**.
- **`standards.py`'s probe/unexpected split is a hardcoded 6-substring match on SITE NAME, not on
  exception type.** A future genuine bug inside `detect()`/`fetch()`/`probe()` falls into "probe"
  and never trips the standard. (batch 11)
- **Four standards have no staleness gate** while five siblings in the same file do:
  `rosters that name their own fiction`, `shelfmarks are unique`, `hand-built assays match the
  charter`, `every source is fully catalogued`. Lesson 8's exact subject. (batch 03/13)
- **`sweep_plan.record()`'s cross-process lost update** — `_RECORD_LOCK` is a `threading.Lock`,
  which gives zero cross-process exclusion; reproduced with two real processes in run #25.
  `missing()` is verified safe (both failure paths over-report gaps, never a false "0 uncovered"),
  so the coverage proof still stands. Fix: per-writer coverage fragments unioned at read time.

## 3. Verified sweep findings I did not repair this run — real work, with file and line

**Silent truncation / data loss**
- `read.py:605-760` — `cap_chunks`/`--chunks` truncates before the ask loop, so those chunks never
  count toward `unanswered` and the write guard misses the path entirely: a pilot run's capped
  entity is cached "complete" and never self-heals. Not hit by `overnight.py` (no `--chunks`).
- `hostcheck.py:419-420,538` — `null_rate()` folds a failed baseline probe to `0.0` and caches it
  process-wide; `judged_any` treats ANY reachable candidate as proof the search was adequate, so a
  source's real host can be evicted when only the correct candidate failed transiently. M16's
  shape, and likely part of why `sources with a reachable wiki` sits at 93%. `--repair` also has no
  `--go` gate, unlike `purge`/`adopt`.
- `local_agent.py:561` — `json.dumps(res)[:SLICE]` reuses the 12000-char read window as the
  tool-message cap, silently cutting the `chars_after_slice`/`total_chars` disclosure fields off
  the end of every large read, contradicting the module's own "never a truncation" docstring.
- `chain.py:108` — `unmatched.most_common(40)` truncates a field **written into CHAIN.json**.
- `scope.py:86-93` — no-signal fallback reintroduces the frequency bias the docstring calls wrong,
  precisely for thin wikis; `titles[:8]` cap on scope-signal pages.
- `weave_index.py:215,224` — STOPNAME/short-key entries dropped from `index` entirely, and
  `description[:400]` persisted. **Trace the downstream consumer before calling it a violation.**
- `feats.py` — `aplimit=500`/`srlimit=50` with no continuation (m82), now instrumented via
  `_CAP_BOUND` but still unfixed.

**Swallowed / indistinguishable failures**
- `endpoint.py:327-334` — `fetch_html`'s `one()` swallows every exception identically with no
  404/410 split; the same bug already fixed in `fetch_raw` (m15) in the same file, on the
  highest-value fetch path.
- `catalogue_models.py:88-106` — a provider answering 200-but-empty and a provider unreachable
  collapse to the same `{"error": ...}`; no "confirmed serves nothing" vs "unknown" distinction.
  `last` also leaks a stale exception message across independent URL retries.
- `completeness.py:194-268` — `host_reachable()` gates on API-mode-only `endpoint.api_url()`, so
  RAW-mode wikis (dandwiki) always read unreachable/0%. **This explains the standing `health
  --preflight` failure `feats/www_dandwiki_com: all 200 sampled entries empty`.**
- `silence.py:115-138` — `uses_exc` is always True for any `except X as name:` because
  `ast.dump(node)` includes the handler's own `name=` field; `records` substring-matches "log"/
  "record" against the whole dump. **The silence detector under-counts silence, both ways.**
- `context_budget.py:242-253` — prompt-file read failure silently defaults to `""`, inflating the
  budget in the dangerous direction; live via `manifest_builder.py:331`.

**Concurrency / contract**
- `runguard.py:98-121` — `claim()` has no atomic test-and-set; two callers can both believe they
  hold the guard. Reintroduces the m27-class race this module exists to fix.
- `scout.py:200-206` — unlocked RMW of shared `WIKI_HOSTS.json` across ≥4 call sites.
- `resync_roll.py:65-68` — comment says "Fixed 2026-08-25" but only the WRITE was made atomic; the
  read→full-scan→write clobber window the docstring describes is unchanged. **A fix comment now
  hides an open bug** — the most dangerous kind of stale comment.
- `retry_synthesis.py:44-47` — `save_side` uses fixed-name temps with no retry and no `silence`.
- `pipeline.py:1327` — `update_handoff` uses raw `os.replace`, not `silence.replace_retry`.
- `wh40k.py:230` — direct `open(...,'w')`+`json.dump` to `data/WH40K_ASSAYS.json`.
- `address_space.py:106-142` — charted-tier fields sized with zero headroom and cached; `fit()`
  silently wraps overflow via modulo instead of raising like `pack()` does. `pipeline.py:1396-1442`
  computes a possibly-larger tier stack in the same phase before calling `assign()` — a silent
  tier alias means an **ambiguous shelfmark**, which `shelfmarks are unique` may not catch.

**Reproduced-live crashes and false claims**
- `zfighters.py:474` — `--full` crashes `KeyError: 'provenance'` on Son Goku.
- `zfighters.py:24-29` — the module's headline claim is false against its own computed output.
- `magnitude.py:553-571` — `_split_gate()` never applies guard 3 SUBJECT (`_HANDOFF`); the split
  path is the default for evidence >30k chars, i.e. the heaviest entities (Goku, Jace), so it can
  reintroduce the exact Zeno-attributed-to-Goku bug the guards exist for.
- `allsweep.py:98-119` — `check_import()` has no try/except around `subprocess.run(timeout=120)`;
  one hung module's `--help` crashes `main()` via `ex.map()`, skipping LINT/VERIFY/ESTATE/RECONCILE
  and leaving `ALLSWEEP.json` stale. Same gap at `:397`.
- `allsweep.py:78-88` — `VERIFIERS` omits `style_audit.py` and `hostcheck.py` despite the module's
  own docstring claiming both are unified here.
- `overnight.py:145` — `running()`'s `or fragment in cmd` fallback is an unconstrained whole
  command-line substring match, reopening the false positive the docstring says was fixed.
- `catalogue_web.py:87-148` — `catalogue_composite()` never got run #25's progress fix and is still
  structurally killable by `kill_stalled_job` on a large sub-wiki category.
- `local_agent.py:407` — `.pyw` yields `modname=None`, so denylist and all three gates skip. **Gate
  bypass number five in shape**, latent only because no `.pyw` file exists in the repo.
- `derivation.py:476-477` — `SCAN_MODULES` omits `physics.py`, `cosmology_graph.py`,
  `magnitude.py`, `address.py`, `pantheon.py`, all of which hold live module-level constants — and
  `physics.MATERIAL`'s own comment calls itself "the anchor the Ledger Standard reuses".
- `tells.py:70` — `"not merely X but Y"` regex alternation precedence bug, reproduced live.
- `style_audit.py:38-39` — `TURN_ENDING` uses `re.M`, so `$` matches every internal line break,
  overcounting against a hard 25% threshold. `main()` also always exits 0.
- `gpu_lane.py:267-273` — `_take_slot` never reclaims a **corrupt** slot lease, permanently
  starving that slot index; `foreground_active()` handles the identical case correctly one
  function over.

## 4. The pool, for whoever reads the page next

`model calls per hour` is 32 against a floor of 900, with **one bucket (nvidia:free) serving every
call while 27 have headroom**. Two candidate causes were narrowed this run and neither is
confirmed:
- `cascade_bridge.py:697-716` — the primary claim loop takes `_ROUTER.claim(pool,1)`'s first alive
  candidate and breaks; **no rotation exists outside the widen-fallback path.** `bucket_state`
  shows 21 of 23 buckets untouched for 30–49 minutes while nvidia was reclaimed repeatedly.
- `read.py:264-337` + `tuning.py:98-101` — both the worker cap and `_gate()`/`_card_gate()` throttle
  to 1–2 concurrent callers whenever `tuning.regime()` reads "local"/"starved", and `_gate()` forces
  even cloud attempts through that local-sized semaphore. `regime()` keys off a 15-minute measured
  success rate, **not** bucket quota or headroom — so low concurrency means the cascade never needs
  to try past the first bucket that answers, which would produce exactly this picture.
**These two would produce the same symptom and could both be true. Instrument before fixing.**
Note also that the pool is genuinely part-dry: Groq is at its tokens-per-day limit, OpenRouter's
free-models-per-day is spent, and Cohere's trial key is a 1000-call month.
