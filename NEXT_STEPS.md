# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #31 wrote this on 2026-08-25 ~13:0x local.*

## 0. BEFORE ANYTHING — THE LIBRARY MAY STILL BE HALTED

Run #31 ended with a standing `DRILL_BREACH` halt that **it could not lift and that was a false
alarm**. Check first: `python src/escalation.py --status`.

* If it is still halted with `what: … the live colliding pairs get separate verdicts`, **the
  defect is already repaired** (M30) and the drill re-runs 113/113. It needs an owner ruling to
  clear, nothing more. The suggested ruling text is at the top of run #31's HANDOFF entry.
* **If it is halted for any OTHER reason, that is the run's whole business.** Do not work around
  it, and do not clear it — you may raise a halt, never lift one.

**THE OWNER RULINGS OF 2026-08-25 STILL SHAPE THE RUN. Read these first.**

1. **EVERYTHING AMISS IS INVESTIGATED THE MOMENT IT IS SPOTTED** — worked on sight, never filed
   for later. What survives into this file is what needs an **OWNER RULING** (a charter question,
   a routing-policy choice, an account action, a contract change with real blast radius), plus
   the sweep's verified-but-unrepaired tail in §3, which is REAL WORK, not a backlog of excuses.
2. **THEN, IMMEDIATELY: THE FULL COMPREHENSIVE SWEEP — every line of every module, every run.**
   `python src/sweep_plan.py --batches 16`, one sonnet-tier agent per batch, all launched
   together; each writes its full report to `handoff/sweep<N>/AUDIT_batchNN.md` and returns
   **only a compact summary**. Then `sweep_plan.missing("run<N>")` **proves** coverage.
   **Run #31's pass: 103 modules, 45,053 lines, 0 uncovered, 16 reports (313 KB).**
   **Launch the 16 agents FIRST and work the immediate queue while they run** — runs #28–#31 all
   did, and every time the two converged on the same defect from opposite directions. Run #31's
   clearest case: batch 09 read the anchors invariant in source while the allsweep repair
   surfaced the same violation live, within the hour.
   **[NEW, RUN #31 — MY OMISSION, DO NOT REPEAT IT] TELL EACH AGENT TO CALL `record()`.** The
   prompts did not, so `sweep_plan.missing("run31")` reported all 103 modules uncovered until I
   recorded them myself from the batch plan. Add to every batch prompt: *"when your report is
   written, run `python -c "import sys; sys.path.insert(0,'src'); import sweep_plan;
   sweep_plan.record('run<N>', [<your modules>], batch=<N>)"`."* Record from the AGENT, which is
   the only thing that knows it actually read the file — and verify the report exists on disk
   before believing any coverage claim.
3. **AN UNRECOGNISED FAILURE IS A BUG, NOT WEATHER.** Still true.
4. **THE SAFETY LAYER BINDS YOU.** CLAUDE.md **Hard Rule -1**, MAINTENANCE.md **Rule Zero**.
   `drill.py` is part of the battery (**113 nets now**, must end `0 BREACHED`). Check the halt
   with the overlap guard. **Never open `prose_enabled` or `step4_enabled`.** When you add a
   guard, add the attack that defeats it and **watch it go red once**.

## 1. NEEDS AN OWNER RULING — nothing below this line is a bug a run may decide

**A. [M34, NEW AND NEWLY VISIBLE] The assay disagrees with its own calibration ladder.**
`anchors.py` prints **INVARIANT VIOLATED**: the scored ladder does not ascend.
```
  The Skate Guy              0.22
  A Sword                    0.10     <- below the floor anchor
  Yggdrasil                  6.18
  Goku                       5.42     <- below the anchor above it
  The Seat of the Creator   10.99
```
The script's own words: *"a reading about the ASSAY, not about this script."* Either the declared
order is wrong or the assay mis-scores against the charter's intent — **and which of a world-tree
holding nine realms and a martial artist who moves planets ranks higher is a curatorial judgment
the charter makes.** It has been reported on every run and graded green by `allsweep` until run
#31 fixed M32. Two anchors are involved, not one.

**B. [M35, NEW, MEASURED] Four providers that cannot answer are called ~40×/hour, and it is what
pins the reader's throttle.** `zai:free` (account empty), `cohere:free` (trial spent),
`cloudflare:free` and `hyperbolic:free` (both HTTP 401). Zero successes between them.
**Three need an account action only the owner can take.** The code-side halves are both
routing-policy: Z.AI answers an empty account with **HTTP 429**, so the engine — in
`C:\Users\imarl\cascade`, **a different repository** — files it as a throttle with a 60-second
cooldown; and `cascade_bridge`'s 4-hour bench lives in a per-process dict, so ~15 processes each
re-discover the same dead provider. Excluding these four moves `cloud_success_rate` from **37% to
45%** against a 0.35 floor — which is the threshold holding M19's 1-of-16-permit throttle on.

**C. [M19] The reader throttles the whole pool through the GPU card's semaphore.** Unchanged and
still the binding constraint. Read M35 first — it may be most of the cause rather than a
neighbour of it. `FOR_OWNER.md` shows `local, 1 of 16 permits`.

**D. [M20] The entrypass done-marker is a positional key, and it is ACCELERATING.**
`health --preflight` now reports **874 stranded across FOUR sources** — Mario 253 (new),
Gundam 227, Thomas the Tank Engine 209 (new), SpongeBob 185. Run #29 measured 412 across two.
**It doubled in a day.** The "one historical re-sort, cheap to defer" reading is dead; the
insertion/re-order path is live and closing entries out of reach continuously.

**E. [M18] `axis_score()` returns a flat 9.9 for every input at M10**, and `ledger.py` resolves
the same missing top-of-ladder edge case a different, incompatible way. Unchanged.

**F. [M21] `action=raw` does not follow redirects** — dandwiki's 805 cached entries all hold
`redirect SRD:<title>`, and the source has contributed zero evidence. Still the standing
`health --preflight` failure. Touches the fetch path of every RAW host.

**G. [NEW, RUN #31] Is `rest[:14]` in `pipeline.synthesis_blocks` a cap or a decision?** Two
independent readers flagged it. The description-only fallback keeps 14 ranked lead paragraphs
when a source has **no** feat-bearing entries. The written justification — *a lead paragraph
cannot carry a ceiling feat* — cannot be fully true and also justify keeping fourteen of them:
if descriptions cannot carry a ceiling, the count is irrelevant; if they can, this is Hard Rule
0. Changing it multiplies model calls across every feat-less source, so it wants a ruling rather
than a patch.

## 2. THE VERIFIED-BUT-UNREPAIRED TAIL FROM RUN #31'S SWEEP — this is work, not a backlog

**Only findings I verified at source myself carry bug numbers.** These are the agents' credible
findings with file and line, unverified by me unless marked. **Verify before fixing** — the
record shows agents are wrong in both directions, as are the supervisor's own hypotheses.

**Blocking-or-major, verified by the agent and worth doing first:**
- `overwatch.py:369-378,647-648` — once the per-round `CLOUD_BUDGET` is spent, every remaining
  module contributes zero findings but is still marked "seen" with a fresh digest, so partial
  coverage is indistinguishable from a full review and goes to the back of the queue.
- `assay.py:496-523` — `calibration_report()` mutates global `SIGMA_BY_ATTESTATION` unlocked, and
  `dashboard.py`'s threading server can call it concurrently. Corrupts the constant every printed
  Magnitude depends on.
- `onomast.py:268-334` — the entire genre/feature-weighted register logic is **dead**: the only
  caller never passes `genre_register`/`features`, so names are still assigned by pure hash, the
  exact bug the docstring says was fixed.
- `pipeline.py:1408-1413` — `phase_chain` discards all harvested contest rows when `len(rows)<10`
  and marks itself permanently done. Real evidence lost.
- `withdraw_chapters.py:66-98` — no chapter-selection logic despite a docstring framing it as
  selective; truncates `catalog.json` unconditionally.
- `foreman.py:864-871` — `_function_source` strips class qualifiers and patches the **first** AST
  match by bare name, in the unsupervised model-patch lane.
- `foreman.py:192` — `SC.sweep(limit=4)` ranks hostless sources then truncates to four; ranks 5+
  starve permanently. **Hard Rule 0.**
- `ledger_guard.py:224` — `assert_intact()` discards `seal()`'s return, so a failed chain-append
  still reports "ledgers intact" to publish. *(Same shape as M29 — worth doing together.)*
- `drill.py:110-115` — the "COVERAGE.json unreadable" net never makes the file unreadable; both
  disjuncts pass via the ordinary "source not found" path. **A net that cannot fail.**
- `drill.py:853-864`, `drill.py:676-680` — two more nets that check a token's *presence in the
  file* rather than that it is called or ordered. Evadable by a comment.
- `allsweep.py` IMPORT tier — M32 fixed two directions; batch 15's reading of the same function
  is worth re-reading for a third.
- `publish.py:33,17-19,133` — the credential scanner's bearer-token charset excludes `+` and `/`,
  its vendor list omits GitHub `ghu_`/`ghr_`, and `scan_for_secrets` skips any staged file over
  2 MB — which is exactly the free-text `handoff/` files Lock Three exists to catch.
- `local_agent.py:526-557` — `t_propose_patch` writes the candidate straight to the live file and
  leaves it importable by other processes for the whole gate window (up to 600 s) before
  reverting.
- `custodes.py:267,290-357` — Threnody's veto is computed and never read; the only production
  caller never supplies the `eta` the real veto needs. *"The only standpoint that can refuse the
  output"* refuses nothing.
- `standards.py:826-828` — `inside >= len(refs) if refs else True` reads vacuously green on an
  empty `REFERENCE_ASSAYS.json`. Same trivially-empty-input bug this file fixed for a sibling.
- `standards.py` (~15 standards) — the "a standard that does not emit is worse than one that
  fails" fix was applied to 3 of ~18 siblings; the rest silently drop the row on an exception
  instead of reporting UNMEASURED.
- `identity.py:180-207` — `_is_continuity()`'s branching test is mathematically unreachable
  (`shared <= n` structurally), risking silent merges of real timeline splits.
- `chain.py:354` — `unmatched[side[:40]] += 1` mutates a shared Counter outside the lock under
  8 workers, and the count is persisted into `CHAIN.json`. **Known, still open.**
- `address_space.py:251-252` — `fit()` modulo-wraps out-of-range tier indices, defeating
  `pack()`'s stated guarantee that it raises rather than naming a different world.
- `address.py:101-114` — `spine_code_for()` breaks ties by dict order rather than returning
  UNASSIGNED. **Tested live:** `"Alien Predator Doom Crossover"` → `II.N`. Hard Rule 2.
- `genre.py:135-197` / `grounding.py:112-117` — both compute a source's `confidence` over only
  the **top 3** scores, inflating it (measured 0.556 vs 0.405 true). A "top N" cap deciding an
  answer, not a display.
- `scope.py:74,81` — `srlimit="3"` and `titles[:8]` cap the wiki evidence feeding the Magnitude
  ceiling. **Hard Rule 0 in a scoring path, not report code.**
- `read.py:627,776-780` — `read_entity()` computes its cache write path once at entry and writes
  to it minutes later with no re-check: a TOCTOU window that can reintroduce M23.
- `endpoint.py:327-334` — `fetch_html()` swallows every exception under one tag, the exact
  "refusal filed as absence" bug `fetch_raw()` was rewritten to fix 40 lines above. **Related to
  M21 and to the 4,947 swallowed `fetch_raw-absent:HTTPError` on the page.**
- `escalation.py:97-106,154-183` — the janitor log uses buffered `open(path,"a")` rather than
  `silence.append_line` (m62 torn-line class), and `_raise_halt()` has no lock, so concurrent
  first-time halts can lose one fault instead of recording it as corroboration.
- `hostcheck.py:67-77` — `_land()` discards `silence.replace_retry`'s return at all 7 call sites;
  a persistently denied write reports success.
- `retry_synthesis.py`, `catalogue_models.py:158` (`[:10]`, reintroducing a cap the comment two
  lines above says was removed), `navtree.py:254-257`, `dashboard.py:316` — assorted Hard Rule 0.

**The systemic one, and it is mechanical enough to sweep in one pass:** roughly **fifteen**
modules still write shared state with a hand-rolled `path + ".tmp"` + bare `os.replace` instead
of `silence.write_json` / `replace_retry` — `identity.py:210`, `magnitude.py:1050,848`,
`coverage.py:78`, `withdraw_chapters.py:95`, `scout.py:55`, `publish.py:107`, `endpoint.py:83`,
`burgs.py:225`, `worldseed.py:317`, `module_index.py:75`, `build_terminal.py:571`,
`manifest_builder.py:436`, `dashboard.py:377`, `snapshot.py`. `silence.write_json`'s own docstring
names this as the project's costliest recurring defect. **Do them as one batch with one check.**

## 3. STANDING LESSONS — 26 and 27 are new

26. **[NEW, RUN #31] A LITERAL CANNOT TELL CODE FROM PROSE ABOUT CODE.** A check that matches
    source text fails on an honest reflow **and passes on a comment**. Both halves bit in one
    run: `the metrics line reads _via only from a dict` went red because the guarded expression
    grew a second branch and wrapped, and my first replacement for the M28 pin went red against
    **my own docstring quoting the removed code**. Both are AST checks now. If you are asserting
    something about behaviour, ask the AST or exercise the code — never `"..." in source`.
27. **[NEW, RUN #31] A PATH IS A HYPOTHESIS TOO — lesson 23, one step over.** I ran
    `cd …/panscriptum-export` for a single `git log` and the shell **stayed there**. The next
    `ls state/` returned the publish copy's five-file stub, which reads exactly like every state
    file having been destroyed. Use absolute paths for everything; `git -C <dir>` for git.
28. **[RUN #31] A SAFETY THAT STOPS WORK MUST BE TOLD APART FROM A FAULT THAT STOPS WORK** — and
    the fix must be carried to **every** file that makes the same inference, not just the one in
    front of you. M26 taught the supervisor this; `allsweep` was one file over and never visited,
    so it spent the day calling eight obedient jobs broken (M32).
29. **A PROCESS QUERY IS A HYPOTHESIS UNTIL IT MATCHES SOMETHING YOU CAN NAME.** Several managed
    jobs launch with a **relative** path, so any filter on the repo path systematically hides the
    foreman-dispatched jobs you are most likely chasing. Enumerate `python.exe`/`pythonw.exe` and
    match on the SCRIPT name. Read `state/overnight.log` before concluding anything about the
    keeper.
30. **A CHECK THAT CANNOT FAIL LOOKS EXACTLY LIKE A CHECK THAT PASSED.** When you loosen a check
    that raised a false alarm, add the companion net proving it still refuses the real thing —
    run #31 did this for M30 and it is the only reason loosening it was safe.
31. **VERIFY THE CADENCE WITH `list_scheduled_tasks`, NEVER FROM A FILE, INCLUDING THIS ONE.**
    The 15 minutes in the overlap guard is the heartbeat-staleness threshold, a different number
    answering a different question; do not "fix" it to match the cadence.
32. **AGE EVERY FILE A STANDARD READS — ESPECIALLY WHEN IT READS GREEN**, and age every
    `bucket_state.last_error` row before believing it is a fire. But note run #31's counter-case:
    the unrecognised-pool rows were 9.5 h old **and the underlying providers were still failing
    every few minutes**. A stale row is not proof the fault is stale — check the live table.
33. **BOUNCE WHAT YOU CHANGED.** `dashboard`, `publish` and `foreman` import `standards`; nothing
    running imports `magnitude`, `sweep_plan` or `verify_math` except the foreman-dispatched jobs.
    **Run #31 changed `pipeline`, `read`, `feats`, `overnight`, `foreman`, `dashboard`,
    `publish`, `overwatch`, `drill`, `allsweep`, `sweep_plan`, `verify_math`, `retry_synthesis`**
    — the whole standing set. They will pick the changes up when the halt is cleared and the
    keeper restarts them; if the halt has been cleared and any of them is still running old code,
    bounce it.
34. **THE SWEEP AUDITS THE SWEEP, AND THAT IS WHERE THE BEST FINDING KEEPS BEING.** Four runs
    running. #28: `record()`'s lost update. #29: `missing()` answering the wrong question. #31:
    the completeness check frozen on a hardcoded `"run29"`. Never exempt the instrument.
