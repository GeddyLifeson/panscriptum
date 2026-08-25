# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #28 wrote this on 2026-08-25 ~09:0x local.*

**THE THREE OWNER RULINGS OF 2026-08-25 STILL SHAPE THE RUN. Read these first.**

1. **EVERYTHING AMISS IS INVESTIGATED THE MOMENT IT IS SPOTTED** — worked on sight, never filed
   for later. What is allowed to survive into this file is what needs an **OWNER RULING** (a
   charter question, a routing-policy choice, a contract change with real blast radius), plus the
   sweep's verified-but-unrepaired tail in §3, which is REAL WORK, not a backlog of excuses.
2. **THEN, IMMEDIATELY: THE FULL COMPREHENSIVE SWEEP — every line of every module, every run.**
   `python src/sweep_plan.py --batches 16`, one sonnet-tier agent per batch, all launched
   together; each writes its full report to `handoff/sweep<N>/AUDIT_batchNN.md` and returns **only
   a compact summary**. Then `sweep_plan.missing("run<N>")` **proves** coverage.
   **Run #28's pass: 95 modules, 40,908 lines, 0 uncovered, 16 reports (344 KB).**
   **Launch the 16 agents FIRST and work the immediate queue while they run** — run #28 did, and
   the immediate queue and the sweep converged on the same pool bug from two directions.
   Note `sweep_plan.py --batches N` prints a trailing `# 95 modules...` comment after the JSON;
   use `sweep_plan.batches(16)` directly and read `x["batch"]`, `x["lines"]`, `x["modules"]`.
3. **AN UNRECOGNISED FAILURE IS A BUG, NOT WEATHER.** Still true — but run #28 changed what it
   costs you. The ledger now re-unwraps on **read**, so a red `every pool failure is recognised`
   is far more likely to be a real, named fault than a fossil wearing a wrapper.

**And the standing lessons. 19, 20 and 21 are new and 19 is the expensive one.**

4. **VERIFY THE CADENCE WITH `list_scheduled_tasks`. NEVER FROM A FILE, INCLUDING THIS ONE.**
   Believed hourly, `11 * * * *` + 523s jitter, firing ~:19–:20. The **15 minutes in the overlap
   guard is the heartbeat-staleness threshold** — a different number answering a different
   question. Run #28 did not re-read the cron and is therefore not a witness to it.
5. **BOUNCE WHAT YOU CHANGED — AND THE PAGE IS A JOB TOO.** STANDING =
   `{dashboard, publish, foreman, overwatch, pipeline}` (keeper restores in 300s); `read.py` and
   `feats.py --roll` are OUTSIDE it and cost a supervisor lap (M15). Check start times with
   `Get-CimInstance Win32_Process` before spending a run on a stale-import hypothesis.
19. **[NEW, RUN #28 — AND IT HAS NOW COST TWO RUNS IN A ROW] A MODULE ONLY THE *PAGE* IMPORTS
    STILL NEEDS A BOUNCE.** Run #27 changed `standards.py`, reasoned that no long-running job's
    *work* depended on it, and wrote "nothing needed bouncing". But `dashboard.py` and
    `publish.py` import `standards` at launch, so for the next **ninety minutes** the published
    page was rendered by pre-fix code — 40 standards where the tree had 42, no
    `the reader's gate is open` at all, unrecognised rows with no age, and an order text run #27
    had already deleted. **Run #28 opened its whole diagnostic on that fossil.** The page is the
    next run's first evidence; an un-bounced page is a photograph of the tree as it stood before
    the last run's fixes. **Test:** compare `len(dashboard.state()["standards"])` computed live
    against the published `state.json` — one command, and it settles it instantly.
20. **[NEW, RUN #28] A CHECK CAN BE ABSENT RATHER THAN GREEN, AND ABSENT LOOKS BETTER.**
    `sentences that survive the verbatim check` — a HIGH guard against the model inventing
    evidence — read a job-dict key nothing sets, so it was never appended to the page at all. Not
    red, not green: **not there**, for its entire life. Two meta-checks should have caught it and
    both failed for instructive reasons: `every declared floor is measured` greps `check()` for
    the constant's NAME (present, on an unreachable line — **a source-grep cannot tell a used
    constant from a dead one**), and `every standard the checker declares actually emits a row`
    compares against a **hardcoded 40** rather than the declared set, so a vanishing standard just
    lowers a number nobody reconciles. **Ask of every standard: have I seen this one PRINT?**
21. **[NEW, RUN #28] A CAUSAL CLAIM YOU DID NOT TEST IS A HYPOTHESIS — SAY WHICH IT IS.** §3 has
    asserted in bold for two runs that `completeness.host_reachable()` **is** the dandwiki
    preflight failure. Run #28 fixed that bug and the preflight did not move:
    `health.check_caches()` never consults reachability at all. The claim was inherited and
    re-copied until it read like a finding. **The real cause was three minutes away, by opening
    the cache file instead of reasoning about the code** (M21: `action=raw` does not follow
    redirects). Inherited claims accumulate authority they never earned.
6. **AGE `data/COVERAGE.json` BEFORE BELIEVING ANY COVERAGE STALL.** `cited`/`settled`/`feats`
   come from it (written once per supervisor cycle); `entities read`/`chunks` come from a live
   glob and log tail. `dashboard.movement()` cannot tell a real stall from the file's write
   cadence.
7. **AGE EVERY `bucket_state.last_error` ROW AND READ THE TEXT.** Run #28's whole pool result came
   from doing exactly this.
8. **AGE EVERY FILE A STANDARD READS — ESPECIALLY WHEN IT READS GREEN.**
9. **A CHECK THAT CANNOT FAIL LOOKS EXACTLY LIKE A CHECK THAT PASSED.** Run #28 adds two more:
   `profile.py:182-187`'s round-trip self-test compares a decoded field against the input it was
   passed (`d["profile"] != r["profile"]` is tautologically False), and `cleanup.py:77-80` guards
   on a regex that is never defined.
10. **A GUARD CAN FAIL BY DOING THE THING IT PREVENTS.**
11. **A BARE NUMBER IN A LOG IS NOT A DIAGNOSIS.**
12. **A GUARD THAT MATCHES ONLY THE UNOBFUSCATED SPELLING IS GREEN ON PURPOSE, FOR EVER.**
13. **DO NOT MATCH PROCESSES BY A LITERAL YOUR OWN COMMAND LINE CONTAINS.**
14. **AN OWNER RULING IS NOT APPLIED UNTIL EVERY FILE OF THAT SHAPE IS VISITED. GREP THE TREE.**
    Seven consecutive runs of findings. Run #28's instance: the truncated cache-path key is in
    **both** `pipeline.py:636` and `coverage.py:44-46`.
15. **ONE FRESHNESS WINDOW CANNOT SERVE TWO QUESTIONS.** Benching wants 180s; EXPLAINING wants
    hours. Run #28 applied this a third time, on the read side (m171).
16. **A CAP ON A DIAGNOSTIC HIDES THE PATTERN, NOT JUST THE ROWS.**
17. **A BATTERY RESULT IS EVIDENCE ONLY ABOUT THE TREE AS IT STOOD WHEN IT RAN.** Re-run after
    the LAST edit.
18. **WHEN A NUMBER WON'T EXPLAIN ITSELF, THE CAUSE MAY NOT BE IN THAT SUBSYSTEM AT ALL.**

## 1. OWNER RULINGS NEEDED — these are blocking real work

1. **[CREDENTIALS — DO THIS ONE FIRST, IT IS FREE THROUGHPUT] TWO DEAD KEYS AND A SPENT ACCOUNT.**
   Surfaced by m171 the moment the ledger re-asked its question. `hyperbolic:free` →
   `HTTP 401: Could not validate credentials`. `cloudflare:free` → `HTTP 401: Authentication
   error`. Both show **0 successful calls** in the live throughput panel while still being
   claimed and still consuming deadlines. `zai:free` → `Insufficient balance or no resource
   package`. **Rotate/remove — a maintenance run does not touch credentials.**
2. **[M19] SHOULD THE READER SQUEEZE CLOUD CALLS THROUGH THE GPU CARD'S SEMAPHORE?** Unchanged
   and still the binding throughput constraint. `read._ask` (`read.py:327-337`) runs the whole
   transport ladder — cloud attempt included — inside whichever gate `tuning.regime()` selects;
   on `local`/`starved` that is the **card's** parallelism (2), not `GATE_CLOUD_N` (16).
   900 × 2/16 = 112.5 against an observed 112. **Options:** (a) acquire the local gate only
   around the local call; (b) size it `max(GATE_LOCAL_N, some cloud width)`; (c) accept the
   ceiling. Also rule on `CLOUD_MIN_SUCCESS` = 0.35, which the loop self-feeds. Now visible on
   the page as `the reader's gate is open`. Batch 06 adds `tuning.py:203`: `regime()` skips the
   success-rate requirement entirely when `judged=False`, contradicting its own docstring.
3. **[M23, NEW — CORPUS-WIDE BLAST RADIUS] THE ENTITY CACHE PATH COLLIDES DISTINCT ENTITIES.**
   `pipeline.py:636` and `coverage.py:44-46` both build the cache filename by sanitising the
   entity name (`[^A-Za-z0-9]+` → `_`, then `[:80]`). Verified live by batch 02: `Magic 8 Ball`
   and `Magic 8-Ball` in the Pixar source share **one** file, so one entity's mined feats are
   read as the other's and `measure()`'s CITED counts are corrupted across both. Two collision
   sources — the sanitiser and the 80-char cap. **Re-keying invalidates every cache on disk and
   re-mines the corpus (real model spend on a constrained pool). Re-key, add a disambiguating
   suffix with a legacy-read fallback, or accept and document?**
4. **[M20] THE ENTRYPASS DONE-MARKER IS POSITIONAL AND ANOTHER WRITER MUTATES THE LIST.** 227
   entries stranded, all in `Gundam`. `f"{source}#{start}"` is an index. **Re-key, back-fill just
   the stranded entries, or accept and document?**
5. **[DECISION C] `publish._scrub()` CLAIMS TO REFUSE "ANYTHING CREDENTIAL-SHAPED" AND MATCHES 8
   VENDOR PREFIXES.** Batch 10 enumerated what passes into the **published** repo unredacted: AWS
   access/secret keys, Slack `xox*`, generic Bearer tokens, PEM blocks, JWTs, Stripe
   `sk_live_`/`sk_test_`, DB connection strings with embedded credentials, Discord/npm/Twilio/
   SendGrid tokens. The docstring is the dangerous part — it reads as a guarantee. **Widen it or
   correct the claim.**
6. **[M24, NEW] `local_agent.py` — THE AUTONOMOUS WRITER — HAS TWO HOLES IN ITS OWN GATE.**
   Batch 16, verified: `:406-407` sets `modname=None` for **any** non-`.py` file, which skips the
   denylist and all three content gates — so prompt templates, registry HTML/JS and the keystone
   charter `.md` are writable with no validation beyond an unrelated whole-suite `verify_math`
   pass. And `propose_patch` can write `data/records/*.json` **directly, bypassing
   `pipeline.write_record`** — a third writer against the two-writer contract. **Is the non-`.py`
   surface deliberate? If not, both are small fixes; the records bypass looks like a straight
   contract violation and could be closed without a ruling — say which.**
7. **[M18, CONFIRMED A FIFTH TIME] `axis_score()` RETURNS A FLAT 9.9 FOR EVERY INPUT AT M10.**
   `ledger.py:127-133` answers the same missing edge case a different, incompatible silent way
   (confirmed live by batch 13: identical price for ruin_score 0 through 9.9);
   `tempus.band_resolution()` already implements the correct fallback. **Charter question.**
8. **[THE INSTRUMENT] `assay._SCALE` DISCARDS THE CHARTER-CALIBRATED SIGMA — NOW MEASURED.**
   Batch 15 re-ran the exact Kenshiro shape through `assay()`: interval **0.06** against the
   charter's published **0.12**; substituting the raw 4.08 back in reproduces 0.12 exactly. Every
   printed `±` under every attestation grade inherits the same halving. Related and still open:
   `anchors.py` exits 1 because the floor→ceiling invariant is violated (`A Sword` 0.10 below
   `The Skate Guy` 0.22; `Goku` 5.42 below `Yggdrasil` 6.18).
9. **[M16] `feats.api()`'s RETURN CONTRACT** — a public-signature change needing a review cycle.
   `discover()`/`fetch()` share the shape.
10. **[OVERWATCH] ITS ZERO IS NOT EVIDENCE, AND NOW THERE ARE NUMBERS.** Batch 13, from the live
    ledger: **69 findings ever filed, 0 open, and only 12 (17.4%) closed by a real model
    verdict** — 51 retired by digest-change or `foreman._retire()` with no verdict at all, plus 6
    orphaned in states no current code path writes. `overwatch.py:652` dedups by fingerprint key
    **existence**, not state, so a retired finding can never reopen. Retirement policy is yours;
    the `foreman._retire()` second-writer bypass is arguably just a two-writer violation that
    could be fixed without a ruling — **say which.**
11. **[HARD RULE 0] `retry_synthesis.py:60`'s `sorted(...)[:14]`.** Batch 09 re-confirmed by
    direct comparison that the docstring's "byte-identical to phase_synthesis" is false —
    `synthesise()` ignores feats entirely and hard-caps, where `phase_synthesis` nominates every
    feat-bearing entity across chunks. Making it faithful multiplies model calls per retried
    source. **Rule on it and it takes ten minutes.**

## 2. Machinery worth building (no ruling needed, just time)

- **[M21 — THE BIGGEST ONE HERE] MAKE `action=raw` FOLLOW REDIRECTS.** `endpoint.fetch_raw`
  returns the literal redirect wikitext and nothing re-requests the target, so all 805 dandwiki
  entries hold ~40 characters of `redirect SRD:<title>` and the source has mined **zero**
  evidence. Detect a redirect body, re-request the target, bound the hops, refuse loops. Touches
  every RAW host — verify before trusting. **This is the true cause of the standing preflight
  failure; the reachability bug that the ledger blamed for two runs was a different bug entirely
  (now fixed, m173).**
- **[CLOSES A RED STANDARD] CHECKPOINT `magnitude.calibrate()` PER BENCHMARK.** It writes
  `CHARTER_REGRESSION.json` exactly once, after all six benchmarks (`magnitude.py:829-836`),
  while its sibling `run_batch()` writes after every completion *because it is written to be
  killed*. The foreman kills `--calibrate` roughly hourly (M15), so every attempt loses the whole
  pass — which is precisely why `the automation reproduces the charter` sits **34h stale**. Mirror
  the sibling. Low risk, closes a HIGH red standard, and the pattern is already in the file.
- **[SILENT 71% DATA LOSS] `cosmology_graph.py:151`'s undisclosed `w >= 1.0` write filter** drops
  2666 of 3753 computed source-pair edges with no count recorded; 25 of 197 sources with real
  shared-stage evidence become **fully absent** from `SHARED_STAGE_GRAPH.json` and read
  downstream (`propagation.py`) as total disconnection.
- **[EXPLAINS THE 18.5%] GIVE `wiki_source.category_members` A COMPLETENESS FLAG.** `:549-573`
  breaks out of its `cmcontinue` walk on any exception and returns a partial roster that callers
  cannot distinguish from a complete one. DC's Characters category alone needs ~68 chained calls
  and this module's own comments record a prior fandom IP-block under load. This is the most
  specific account yet of `every source is fully catalogued` at 18.5% with DC at 0.5%.
- **`sweep_plan.record()`'s cross-process lost update** — `_RECORD_LOCK` is a `threading.Lock`.
  Batch 08 independently re-derived that `missing()` can only over-report gaps, never fabricate a
  false "0 uncovered", so the coverage proof stands — and proposed the right fix: **per-batch
  shard files merged in `missing()`**, rather than a cross-process lock on a shared file.
- **Behavioural checks to replace `verify_math`'s source-greps.** Run #28 added four (§20k, §20l)
  as the pattern to copy. `every declared floor is measured` is the next candidate: it greps for a
  constant's name and cannot tell a used constant from an unreachable one — the exact reason the
  fabrication guard hid for its whole life. `every standard the checker declares actually emits a
  row` should compare against the DECLARED set, not a hardcoded 40.
- **Most data-file-backed standards VANISH on a read error instead of reporting UNMEASURED** —
  including three HIGH ones sharing one `ALLSWEEP.json` try block. A standard that disappears is
  green by absence. Run #28 applied the fix pattern to the fabrication standard; the rest remain.
- **`runguard.py:72-80`** — `_land()`'s fixed-name shared tmp makes `claim()`/`beat()`/`release()`
  raise uncaught `FileNotFoundError` under real concurrency (batch 10 reproduced: **7 of 8 threads
  crashed**), in the module whose entire purpose is safe claiming and whose docstring has a "WHY
  IT DOES NOT RAISE" section. `:98-121` `claim()` still has no atomic test-and-set.
- **`standards.py`'s probe/unexpected split is a hardcoded 6-substring match on SITE NAME**, and
  `"hostcheck.py:candidates"` in that list matches **zero** call sites today.
- **Four standards still have no staleness gate** while five siblings in the same file do.
- **Give `allsweep.reconcile()`'s `note()` a severity, so the tier can gate.** 16 ungraded rows.

## 3. Verified sweep findings I did not repair this run — real work, with file and line

**Checks that cannot fail / claims contradicted by their own code**
- `profile.py:182-187` — round-trip self-test's `d["profile"] != r["profile"]` is tautologically
  False (decode echoes its input param); genre/register/features/band are decoded and never
  compared. "N of N round-trip, 0 failures" would print with those fields corrupted.
- `cleanup.py:77-80` — a guard tuple entry references a regex never defined in the file and is
  unconditionally skipped: a check that checks nothing.
- `rosetta.py:402` — `--check` compares only the decimal fraction (dead `P._x`, always 0),
  discarding the M-band and scrambling cross-band correlation. `:90-92,104-105` `_STAND`, whose
  comment says it parses Stand stats, is never called — JoJo Stands have never been mined.
- `estate.py:209-211` — the charter erratum check tests for a rung NAME's presence, not the
  claimed defect, so it can never observe a fix.
- `sweep.py:20-22,169-189` — funnel docstring claims each stage is a strict subset of the one
  above; live run gives addressed (45,807) > catalogued (32,222), printing a garbled `--13,585`.
- `hostcheck.py:918-919` — `--purge` argparse help claims an automatic "host independently
  rejected" safety gate that `purge()`'s own docstring says never existed. **False documentation
  on an irreversible operation.**
- `descending_ladder.py:85-95` — Planck rung unreachable except at bit-exact equality; the whole
  1e-18→Planck gap misreports as Quark-confinement.
- `handbuilt.py:166-168` — comment claims Zalama's interval is "four times wider"; live is 1.33x.
- `address_space.py:171-183` — docstring claims H/X print as `?` when uncharted; verified live,
  no `?` is ever printed. `:27` "74 bits, 10 bytes" is stale; live `TOTAL_BITS` is 89.
- `context_budget.py:261` — `report()`'s docstring claims it is used by health/preflight; zero
  callers anywhere. `module_index.py:2` claims 87 modules; there are 95.
- `burgs.py:230` — `--write` prints "sample of 50 worlds" while correctly writing every world.
- `propagation.py:53` — names a constant `BASE_YEARS_PER_HOP` that does not exist.

**Correctness**
- `read.py:188-190` — `_names()`'s pronoun branch returns True for **any** entity when the
  sentence contains any pronoun, with no antecedent check (reproduced: a Batman sentence passes
  for Superman, Wonder Woman and Aquaman equally). `:635,647-648` chunk selection uses a raw
  substring test, not the tokenised `_names()` it already has ("Ares" matches "declares").
- `generate.py:163-176` — `_covered()` passes when an entry's first and last word appear anywhere
  in the block, untied to that entry; reproduced marking an unwritten entry "covered".
- `ingest_doc.py:116-126` — `record_path`'s unbounded substring fallback misroutes a new source's
  provenance and entities into an unrelated record (reproduced live: "Fire" →
  `dr-firestorm-s-engineering-corps.json`).
- `thread_integrity.py:108-116` — the DANGLING check fires only when **all** shared entity keys
  in a pair are dead; partial drift folds into IMPLIED-UNRECORDED with a stale `shared` count.
- `zfighters.py:474` — `--full` crashes `KeyError: 'provenance'` on Son Goku (reproduced, full
  traceback in batch 12's report). `:24-29`'s headline claim is false against its own output.
- `sevenfold.py:204` — world-level `shelve()` gets empty weights, degenerating `seams()` into
  k-1 singletons plus one giant block (reproduced: 50 members → [44,1,1,1,1,1,1]).
- `reference.py:245` — `shelfmark()` hardcodes `RUNGS[3+i]`, assuming `upper` has exactly 3
  elements; reproduced silent wrong output.
- `gpu_lane.py:270` — `_take_slot` skips `_expired()` when `rec is None`, so a corrupt slot lease
  starves that index forever (reproduced with an injected corrupt `slot.0.json`). `:66-67`
  unguarded `int(os.environ[...])` crashes module import for all 9 processes, contradicting the
  file's own "FAIL OPEN, ALWAYS" (reproduced).
- `identity.py:180-207` — `_is_continuity` requires n>=2 bearers, so a single-bearer designator
  (the module's own "(Fates)" example) can never be recognised; risks merging two continuities.
- `scope.py:106-114` — `build()` sets `out[h]=None` on failure then permanently skips `h`.
- `autostart.py:131-133` — `_twin_watchdog()` returns False on any failure of its own detection
  call, defaulting to "proceed", re-opening the multi-watchdog respawn loop its docstring fixes.
- `catalogue_aurora.py:140` vs `:150-155` — `written.append()` runs **before** the write-success
  gate, so a denied `write_record_catalogue` is printed in the final "Wrote N records" table
  immediately after being reported "WRITE DENIED".
- `resonance.py` is imported nowhere in `src/`; `custodes.convene()`'s `eta` always defaults None
  in production, so the documented "Threnody veto" never fires. `resonance.hodge_decompose({})`
  raises ZeroDivisionError (reproduced) for whenever it is wired up.
- `tells.py:127-131` — the sentence-start anchor fix dropped leading-whitespace tolerance, so a
  leading space before a discourse tell reads clean. `:44-66` three lexical pairs double-count.
- `style_audit.py:38-39` — `TURN_ENDING`'s `re.M` `$` matches mid-record line ends, inflating
  turn_rate (reproduced).
- `render.py:110,121-122` — `containment_svg` shows "1 child" for 0 children, live on today's
  `universe`-tier data.
- `pick_model.py:295` — `total_vram_gb() or 10.0` silently fabricates the GPU-only residency
  budget on any read failure, with no disclosure.
- `catalogue_models.py:72-106` — `ask_provider()` misattributes a 200-but-empty response to a
  stale exception from an earlier URL attempt (`last` leaks across retries). And per batch 10 the
  standard's only automated remedy, `foreman.recatalogue_models()`, re-probes the same external
  config forever and can never close its own loop.
- `hostcheck.py:534,549-562` — `judged_any` lets one wrong-but-reachable candidate justify fully
  unassigning a source whose real host merely timed out; `--repair` has no `--go` gate.
  `:390-423` `null_rate()`'s cache is keyed on host only, ignoring `exclude`, so the first
  caller's baseline is reused for every later source on that host. `:187,199` `relevance()`'s
  ABOUT veto samples only the first 12 of up to 40 hit titles, unsorted.
  **Investigated this run: these are real but do NOT explain `sources with a reachable wiki` at
  93%** — live `HOST_UNFIT.json` holds 3 plausibly-genuine rows and most of the 20 hostless
  sources look genuinely wiki-less.

**Silent truncation / data loss**
- `read.py:605-760` — `cap_chunks`/`--chunks` truncates before the ask loop; capped entities cache
  as "complete". `chain.py:108` `most_common(40)` into `CHAIN.json`; `:354` a truncated string as
  a dict key. `genre.py:135,182,187` truncates ranked genres **and** the confidence denominator
  (measured 59% inflation). `weave_index.py:224` + `weave.py:195-198` `description[:400]` at write
  time. `feats.py:348-361` `aplimit=500`/`srlimit=50`, no continuation. `ingest_doc.py:216`
  descriptions to 2000 chars. `scope.py:81` `titles[:8]`, `:74` `srlimit="3"` with no
  continuation. `rosetta.py:194` `srlimit:"5"` across 28 scale queries per wiki.
  `health.py:220-253` `files[:200]` per host dir. `dashboard.py:296` `swallowed[:6]` (hides 14 of
  20 tags, 415/5226 occurrences); `:294` finding text to 160 chars with no marker.
  `verify_math.py:286` `_problems[:3]` and `:811` `build_all(limit=400)`.
  `local_agent.py:561` `json.dumps(res)[:SLICE]` can emit invalid JSON.
  `audit.py:139-148` prints 4 examples per violation class under a docstring claiming exhaustive.
  `foreman.py:230-232` top-3 failure classes. `overnight.py:313-335` top-6 open findings.
  `allsweep.py:177-285` six-item example lists. `navtree.py:254-257` six problems.
  `backfill.py:176` builds "already held" from ALL entries, not just Persons.

**Swallowed / indistinguishable failures**
- `dashboard.py:284-305` — `_watch()` defaults before the try (verified this run that the current
  `0 open / 0 high` **is** a real measured value, not a swallowed read — but the code still cannot
  tell the two apart). `silence.py:115-138` — `uses_exc` always True; `records` substring-matches
  the whole ast dump; unparseable files silently return `[]` in two sibling places, inside the
  anti-silence module. `endpoint.py:327-334` — `fetch_html.one()` swallows everything; the sibling
  got the 404/410 split. `coverage.py:57-65` — `_so_load()` swallows any exception, resetting a
  corrupted cache with no log. `context_budget.py:242-271`, `cascade_bridge.py:225-234`
  (`_interval()` → 0.0, no pacing), `magnitude.py:688,492-493`, `hosts.py:44-50`,
  `wiki_source.py:278` (catches only OSError, not JSONDecodeError, on shared state),
  `pantheon.py:264-271`, `foreman.py:690-695` (the file's only fully unlogged except, and it can
  bypass a documented 30-minute cooldown).

**Concurrency / contract**
- `health.py:61-144` — `flush()` holds **no lock at all** (grep-confirmed by batch 06, correcting
  the earlier "threading.Lock only") on `state/failures.json`, the highest-traffic multi-process
  shared file. `:119,361` hand-rolled fixed-name tmp.
- `foreman.py` (six sites), `endpoint.py:83-94`, `magnitude.py:966-996`, `retry_synthesis.py:44`,
  `manifest_builder.py:436`, `worldseed.py:317`, `module_index.py:75`, `identity.py:218-222`,
  `ingest_doc.py:87-100`, `publish.py:283-290`, `compress_store.py:43-44` — fixed-name temps
  and/or raw writes to shared files.
- `resync_roll.py:33-68` — "Fixed 2026-08-25" made only the WRITE atomic; the read → full-scan →
  write clobber window is fully open. `recover_folder_records.py:86-164` is the same shape with
  the same "ATOMIC" comment, and writes records via `silence.write_json` rather than
  `pipeline.write_record_catalogue`.
- `scout.py:197-206` unlocked RMW of `WIKI_HOSTS.json`; `:207-218` `--dry` still writes.
  `hosts.py:78-97` unlocked RMW of `SOURCE_HOSTS.json`. `cascade_bridge.py:502-542`
  `record_unrecognised` RMW race. `pipeline.py:518-522` drift-merge gated on entry **count** only.
  `dashboard.py:349-369` `movement()` RMW under `daemon_threads=True`; `:150-168` `throughput()`
  never closes its sqlite connection. `completeness.py:110-119` unlocked shared-dict cache RMW
  across 6 workers. `feats.py:73-361` unlocked counter RMW; `:295,804` fixed-name tmp.
  `overnight.py:65-89` unsynchronised lazy lock init. `address_space.py:106-142,251-252`
  modulo-wraps overflow where `pack()` raises.

## 4. The pool, as it stands after run #28

- **Volume** is still gated by the reader (M19, §1.2) — unchanged, still a ruling.
- **Concentration** is the router's `quality_first` ranking in `C:\Users\imarl\cascade\cascade\router.py`
  (`nvidia:free` rank 89, `gemini:*` 85-88), which explains the near-monopoly. Inflight-based
  spreading only activates under real concurrency, which the gate above prevents.
- **Genuine dryness** is real: Groq at tokens-per-day, OpenRouter's free-models-per-day spent,
  Cohere on a 1000-call trial month.
- **And now: two dead keys and a spent account** (§1.1) — `hyperbolic:free` and `cloudflare:free`
  both 401, both at **0 successful calls**, `zai:free` out of balance. That is three buckets the
  pool has been claiming and burning deadlines on for hours. **This one is free to fix.**
