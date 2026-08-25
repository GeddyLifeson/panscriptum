# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #15b wrote this on 2026-08-24 ~19:05 local.*

**Read this first.** Four things shape what is worth doing next run:

1. **THE SCHEDULE IS EVERY 15 MINUTES (`11,26,41,56 * * * *`), so you will routinely land on a
   live predecessor and that is the designed steady state.** The guard exits in seconds. It does
   **NOT** see interactive sessions — before writing anything, check
   `git -C C:\Users\imarl\panscriptum-export log --oneline -5` and `ls -lt src/*.py | head`.
2. **RUN #15b CHANGED A LOT AND TWO CHANGES HAVE COSTS THAT LAND NEXT RUN, NOT LAST RUN.**
   Eleven defects closed, including two silent-data-loss majors. **`read.py`'s chunk cache key
   now includes the entity, which orphans 8,194 cached answers** — those passages get re-asked.
   And `regime()` now reads `local` where it read `cloud`, so worker counts dropped. **The
   reader's numbers will move for at least two reasons at once. Measure before attributing.**
3. **M7'S MECHANISM IS FOUND AND CLOSED; ITS PHYSICAL CEILING IS NOT.** `gpu_lane._touch` was
   never called, so long calls lost their own slots to competitors mid-call — the card was
   over-subscribed by exactly the longest work. Fixed. But the card still serves **2** requests
   against a 12288 runner using **8.0 GB of 10 GB**. §1.1 is the measurement that decides
   whether anything further is needed.
4. **THE FOREMAN STILL HOLDS AN `--adopt` CHILD (pid 45432 under 5420) AND WAS NOT BOUNCED.**
   It is the one job still running pre-run-#15 code. Fandom is still blocked, so stale and fixed
   return the same answer — but the moment fandom answers, this matters. See §1.4.

## 1. Verify first

1. **[M7 — THE MEASUREMENT THAT DECIDES WHETHER ANYTHING MORE IS NEEDED.]** Read the reader's own
   log on a real GPU phase — **ignore any line reading `0 to GPU`, that is cache replay**:
   ```
   tail -3 state/read_auto.log
   ```
   Run #15 measured **76% rising to 93% discarded**. Two fixes now push in opposite directions:
   arbitration is honest (so fewer timeouts) but 8,194 orphaned chunks must be re-asked (so more
   GPU demand). **A discard rate that has not improved does NOT mean m54 failed** — check the
   lane is actually holding leases before concluding anything:
   ```
   python -c "import sys,json;sys.path.insert(0,'src');import gpu_lane as G;print(json.dumps(G.status(),indent=1))"
   ```
   **`slots: []` while calls are in flight is the m56 symptom and means the lane is arbitrating
   nothing** — that was true before and is the single most informative thing to check. A slot row
   whose `age_s` keeps climbing past ~300 while its holder is alive means the heartbeat thread is
   not running.
2. **[the physical ceiling, if §1.1 is still bad]** `ollama ps` — run #15 saw `qwen3:8b` at
   **12288 context, 8.0 GB, 100% GPU**. With `OLLAMA_NUM_PARALLEL=2` the card serves two. Both
   gates now derive from that env var rather than restating it, so **changing the daemon's
   parallelism is now the single lever** that moves `gpu_lane.MAX_SLOTS` and `read.GATE_LOCAL_N`
   together. Whether the card can actually serve 3 at 12288 in 10 GB is a MEASUREMENT nobody has
   taken, not a guess to make in a config file.
3. **[M8 — is fandom back? Four seconds, TCP only.]**
   ```
   python -c "import sys;sys.path.insert(0,'src');import standards as ST;print(ST.fandom_ipv4_reachable())"
   ```
   Run #15 got `(False, '172.66.2.166 TimeoutError')` in **16.0s**. **Read the latency, not just
   the boolean**: a slow False is a block; a fast False (<1s) is a third answer meaning something
   new is wrong. That distinction caught m65.
4. **[m65 — bounce the foreman ONLY when §1.3 says fandom is back, and check the child first.]**
   ```
   powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*adopt*' } | ForEach-Object { '{0} parent={1}' -f $_.ProcessId, $_.ParentProcessId }"
   ```
   A child under the foreman's PID means **DO NOT BOUNCE** — the orphan rewrites `WIKI_HOSTS.json`
   from a stale snapshot. m42 has now held `202 / 191 / 451703b8` for an **eleventh** run.
5. **[M9/M10 — confirm the two majors actually took.]** Both are pinned by §19ah, so the battery
   is the real check. One live corroboration each, cheap:
   ```
   python -c "import sys,json;sys.path.insert(0,'src');import read as R;q=json.load(open('state/read_queue_index.json',encoding='utf-8'));rows=[v['row'] for v in q.values() if isinstance(v,dict) and 'row' in v];print(len(rows),'rows ->',len(R.priority(rows)),'queued')"
   ```
   **These two numbers must now be EQUAL.** Before run #15b it was 40,884 → 40,216, losing 668.
6. **[M4 — money]** Must print `598 False False True`:
   ```
   python -c "import sys;sys.path.insert(0,'src');import json,cascade_bridge as c;pb=json.load(open('state/PAID_BURST.json'));print(pb['used'],pb.get('enabled'),c.paid_lane_open(pb),c.PAID_LANE_RETIRED)"
   ```
7. **[the regime change — watch for over-correction.]** `regime()` now needs a measured success
   rate ≥ 0.35 over ≥ 20 calls. **The failure mode to watch for is it reading `local` forever**
   because the pool never gets enough traffic to prove itself while the gate is narrow:
   ```
   python -c "import sys;sys.path.insert(0,'src');import tuning as T;print(T.regime(force=True),'|',T._CACHE['why'],'| rate:',T.cloud_success_rate())"
   ```
   If `why` shows the rate clause and the pool has genuinely recovered, it should flip back to
   `cloud` on its own. **If it is stuck local with a healthy pool, that is a real finding** and
   `MIN_CALLS_TO_JUDGE` / `CLOUD_MIN_SUCCESS` are the knobs.
8. **[preflight — still exactly 2 FAILs]** `API paths per host family` (**M8**) and
   `feats/www_dandwiki_com` (**M1**). A THIRD FAIL is the finding.
9. **[the keeper — ANSWERED THREE TIMES OVER, stop re-investigating.]** Run #15 caught it
   restoring `pipeline`; run #15b's bounce found it had **already restored four of six jobs**
   before the restart calls got there ("already running, left alone"). It is healthy.

## 2. Human decisions needed (owner)

A. **[M8 — the only one blocking real work] Is the fandom IPv4 outage a block we earned, or a
   network fault between here and Cloudflare?** All fandom content hosts share two Cloudflare
   IPv4 addresses and both time out; the same edge answers instantly over IPv6; other IPv4
   destinations are fine. **Forcing IPv6 to get around it is a decision only you can make, and
   runs #14, #15 and #15b all deliberately declined to take it.**
B. **[M10's cost — confirm the trade was right.]** Entity-scoping the chunk cache orphaned
   **8,194** cached answers (not deleted — just no longer found). The alternative was keeping a
   cache full of answers attributed to the wrong entity. **This run judged a smaller-but-wrong
   library the worse outcome and acted; say if you disagree**, because the re-read cost lands on
   an already-saturated card.
C. **[NEW, from the read.py audit — chunking has no overlap, and boundary-straddling feats are
   unrecoverable.]** `read.py` splits on raw character offsets (`for i in range(0, len(body),
   size)`) with no sentence awareness and no overlap. A feat sentence spanning a boundary is
   truncated on both sides, so neither chunk can return it verbatim and the guard discards it.
   **This is not deferred** — the chunks answer normally. Offsets are deterministic, so a re-run
   loses the identical sentences forever. Is fixed-window splitting an accepted loss (it is a
   real cost in call count to add a lookback buffer) or an oversight? Every other tradeoff in
   that file is documented; this one is not.
D. **[NEW, same audit — two different "own page" tests.]** `read_entity` uses
   `_norm_q(title).lower() == _norm_q(name).lower()` (folds curly quotes, dashes, whitespace);
   `queue()` uses a bare `t.strip().lower() == e["name"].strip().lower()`. A title differing only
   by a curly apostrophe is its own page to one and not to the other. **With M9 fixed this no
   longer drops the entity from the queue** — it only mis-ranks it — which is why it is a
   question rather than a fix. Should they share one comparison?
E. **[NEW, same audit — `chunks_skipped` is arithmetically wrong for multi-page entities.]**
   `skipped = sum(len(b) for b in text.values()) // size - len(chunks)` floors ONE division over
   the concatenated total, where the real loop produces `ceil(len(body)/size)` **per page**. Two
   15,000-char pages at size 10,000 give a true 4 and a computed 3. It can go negative and is
   clamped to 0. **Diagnostic only** — it does not change which chunks are read — but it is a
   number in the progress line that people reason from.
F. **[NEW, same audit — a stale comment that describes a safety net that no longer exists.]**
   The block above the `cap_chunks` application still explains a cap of twelve as though it were
   operative ("Uncapped, one entity could eat an hour of GPU"). **Confirmed inert**: the default
   is `None` in `read_entity`, `run()` and the CLI, and no module in the tree passes a value. So
   there is currently **no bound at all** on one entity's GPU time by default — which is Hard
   Rule 0 working as intended, but the comment reads as reassurance that is no longer true. Delete
   the paragraph, or say plainly that the bound was removed and why.
G. **[NEW, same audit — `chunks_reused` is computed and thrown away.]** `read_entity` returns it;
   `run()`'s accounting never reads it, so the chunks/s rate and ETA mix instant cache hits with
   real model calls — the same distortion the file already diagnoses and fixes for *entity*-level
   caching. **This matters more now**: with 8,194 chunks orphaned, reuse and fresh work are about
   to have very different costs and the progress line cannot tell them apart.
H. **[m56 — is the lane arbitrating anything?]** `gpu_lane.status()` once reported `slots: []`
   while nine requests were in flight. m54's fix should change this. **§1.1 is the check**; if
   slots are still empty under load, the lane is being bypassed somewhere and that is the next
   real bug.
I. **[§2 D from run #15 — the cloud worker floor.]** `tuning.py`'s `max(4, min(16, n + 2))` still
   floors at 4, and a *stale* `"cloud"` label can pair with `n = 0` to give 4 workers against a
   dead pool. **The rate check added in §2 B makes this much harder to reach** (a dead pool
   fails the rate too) but the floor itself is unchanged and still documented as deliberate.
J. **[§2 E from run #15 — compounding cache TTLs.]** `tuning.RECHECK_SECONDS=180` and
   `read.GATE_RECHECK_S=120` run on independent clocks, so the gate width can be up to **240s**
   stale rather than the 120s its constant implies. Verified as arithmetic, **not instrumented
   live**. Also `read.py`'s `_GATE_STATE` defaults to `"cloud"` — open-wide before the first
   refresh.
K. **[m60] Which trade for the last 22 oversized chapter blocks?** Largest **46,840** chars
   against a p99 of 11,978. **[m51]** Should `check_context_budget` cover the generate path?
   **[M4]** The burst lane — 598/500, retired structurally: raise, delete, or leave as evidence?
L. **[the 240-char description truncation]** `pipeline.py` truncates every entry description to
   240 chars before the model judges it; 50.6% of ~82,000 entries are longer. **Same shape as M6,
   m13 — and now as M9**: an input cap a downstream verdict treats as authoritative. **M9 raises
   the priority of this question considerably**, because it is the same class of defect and this
   run proved that class is live in the tree.
M. **[m25 / m16 / dashboard `findings` cap of 12] — ONE ruling, four sites: does Hard Rule 0 bind
   diagnostics and run logs, or only reader-facing listings?** Carried since run #5. **"Does
   anything downstream act on the truncated list?" is the workable test** — and M9 is the proof
   that when something does, the cost is invisible and permanent.
N. **[m58] Is `folder-mechanical` routing provisional?** **[m57]** The singulariser fix needs a
   corpus diff (`catalogue_web.py:212`, 425 mangled types). **[m48]** 70 sources collide under
   `_norm`. **[m47]** what a failed feats join should look like; the 17 stranded feats records;
   the 87 hybrid Powers entries. **[m37]** Nothing reads `data/CHAIN.json`. **[M]** `GENRES.json`
   / `NAVTREE.json` have no automated writers. **[m29]** `cleanup.py`'s `_EMPTY_MECHANIC`.
   **[m26]** the completeness audit cannot see 46 of 210 sources. **[m39]** `scout.sweep(limit=4)`
   can starve lower-ranked hostless sources — **re-read this one in light of M9**. **[m38]**
   `foreman._function_source` resolves symbols by bare name (`main` has 74 definitions).
   **[m12]**, **[m13]**, **[m30]**, **[M1]**, **[m43]** unchanged.
O. **[the stale local buckets]** The reader still logs `REMOVED local-<model>: HTTP 404` across
   five pruned models on every start (seen again after run #15b's bounce). Self-healing per
   process; the roster lives outside `src/`. Confirm the prune was intentional and let the ledger
   say so.
P. **Permanently hostless roll entries** — catalogued with no host **20**; on the roll but never
   catalogued **6**. The **91 DECIDED spine codes** are **still not written to
   `CHARTER_SPINE_CODES.json`**, which has no writer in `src/`. Also **34 catalogued sources have
   no charter spine code**, and three charter errata are open (Supercluster, Filament, Hyperverse
   are rungs with no Magnitude band).
Q. **`site/state.json` is stale and nothing in `src/` references `site/`** — the live artifact is
   `docs/state.json`. Dead directory, or something's input? **No deletion without a ruling.**

## 3. Small implementable items (no decision needed)

1. **`pipeline.py`'s 9 shared cross-phase JSON writes** still use raw `open+json.dump` rather
   than `_landed`/`replace_retry`. Open since run #2. **Same family as m62 and m74, both of which
   are now fixed** — this is the last member of that family still open, and `silence.append_line`
   / the per-writer temp-name pattern are both now in the tree as models.
2. **35 silent exception handlers of 403** (`python src/silence.py`). **Run #15b added net zero**
   — three were introduced during the work, caught, and converted before landing. Note the
   mechanism, because it bit once: **the audit reads the AST, so a `#` comment does NOT satisfy
   it**; the idiom is a string (`_ = "silence-exempt: ..."`). Concentration: **`gpu_lane.py` 14**
   and **`context_budget.py` 4** (246, 252, 265, 270 — fallback-to-empty-string when a prompt file
   cannot be read, which would generate against an EMPTY system prompt rather than fail). Also
   open: `entity_match.py:255`, `overnight.py:500` (**inside the keep-warm loop**),
   `publish.py:161`, `coverage.py:92`, `pipeline.py`, `foreman.py` ×2, `health.py` ×2.
3. **`FEATS_BLOCK_CHARS = 20000` still exists as `pack_feats`'s default third argument.** The
   manifest path derives the budget correctly, so this only bites a caller that forgets to pass
   one — the mistake both an audit subagent and run #12 made when *calling* it. Make it required.
4. **`JOB_OVERHEAD_CHARS`'s comment does not reproduce.** It cites "min 314, median 1,193, max
   1,536 across 331 blocks"; a re-measure across 3,386 real blocks gives min 115 / median 142 /
   max 368. The constant (2,000) errs conservative — **the comment is wrong, not the code.**
5. **`_HAS_ACTION`'s verb list may have recall gaps** (audit, **unverified**): "vaporiz-",
   "annihilat-", "incinerat-", "smash", "explod-", "shred", "stun", "wound" are absent. A chunk
   whose only feat verb is missing is skipped before the model sees it. Honestly accounted in
   `chunks_skipped`, so not hidden — but nobody has measured the false-negative rate the way the
   rest of the pipeline was measured.
6. **DONE, do not redo:** M9, M10, m54, m55, m62, m70, m71, m72, m73, m74 and §2 B (run #15b);
   m66, m67, m68, m69 (run #15); m63, m65 (run #14); m64; M8's *standard* (§19z/§19aa — **the
   outage itself is open**); m61 (§19s); the M7 gate fix (§19t — live, and **insufficient on its
   own**, see §1.1). **Also settled and not to be re-derived:** a timed-out chunk is **deferred,
   not lost** (`if unanswered: return out` skips the record write); `hostcheck`'s `judgeable` flag
   **is** consumed, at `standards.py:571`, so that run #5 finding is stale.

## 4. Surface rotation for the next audit fan-out

**Run #15b's one subagent — `read.py`'s chunking/caching/queue paths — returned the two most
serious findings in several runs.** Nine findings: two majors confirmed (M9 with a measured count
of 668; M10), two small fixes (m74 and a stale comment), five promoted to questions (§2 C, D, E,
F, G) including two the agent itself marked unverified. **The ratio is the point** — the audit
surfaces candidates, verification against source decides them, and roughly half of any batch does
not survive that step.

Covered, do **not** re-read unless the diff touched them: the round-1 full-codebase audit and
evening sweep (`handoff/AUDIT_*.md`); run #2's four surfaces; run #3's two; run #5's three;
run #6's four; run #7's five; run #9's `feats_index.py` and `hostcheck`; run #10's
`manifest_builder.pack_feats` + `generate.py`'s feats branch; run #11's `system_style.txt` and
`pipeline.py`'s `ask`/`ask_pool_first`/`phase_entrypass`; run #12's `gpu_lane.py` and
`context_budget.py`; run #13's `read.py` transport ladder; run #15's `tuning.py` (all 169 lines);
**run #15b's `read.py` chunking/caching/queue paths**.

**Not yet audited line-by-line** — pick from here: **`entity_match.py`** (now the highest-yield
item — the only one of the three new modules nobody has audited), `address_space.py`, `profile.py`,
`burgs.py`, `tells.py`, `style_audit.py`, `audit.py`, `descending_ladder.py`, `cosmography.py`,
`genre.py`, `reference.py`, `resync_roll.py`, `retry_synthesis.py`, `build_terminal.py`,
`sweep.py`, `runguard.py`, `compress_store.py`. **`gpu_lane.py` is worth a RE-read** despite being
covered by run #12 — it changed materially this run and it sits in front of every model call.

**Two overwatch HIGHs were refuted at source by run #14** — `cosmography._fmt` (defined at
`cosmography.py:256`) and `descending_ladder.compton_confinement_energy` (`p = HBAR / (2.0 *
size_m)` IS hbar/(2r)). **Do not spend on them again.**

## 5. Lessons worth keeping

- **A comment can be the most confident thing in the file and still be false.** `priority()` said
  "nothing here is dropped" and "the full list is still the full list" three lines below the code
  dropping 668 entities. **Both majors this run were found by reading code against its own
  comment** rather than by reading the comment.
- **The guarantee that catches most failures is the reason the rare one is invisible.**
  `read.py`'s "deferred, not lost" rule (`if unanswered: return out`) is real and it works — which
  is exactly why M10 survived: a cross-entity cache hit is an *answered* chunk, so the guard never
  fires. **When a safety net is genuinely good, look for the case that never touches it.**
- **A function that exists and is never called is worse than one that is missing.**
  `gpu_lane._touch` made the lease system look complete. Nothing imported it, nothing called it,
  and the docstring above it described behaviour the module did not have. **`grep` for callers,
  not just definitions.**
- **Fix the class at the site where it was first named.** "Reachability is not capacity" had been
  written into four docstrings before anyone changed `regime()`, which is where the sentence was
  coined. Documenting a defect repeatedly is not the same as closing it.
- **When two fixes push a metric in opposite directions, say so before the next run measures it.**
  M10's cache reset adds GPU demand while m54 and §2 B reduce contention. A run that reads only
  the discard rate will attribute the result to whichever fix it happens to be thinking about.
- **Test the test.** Both the lane heartbeat check and the brace check were run against the
  pre-fix behaviour to confirm they FAIL there. A regression check that passes before the fix is
  decoration.
- **Kill by PID, not by pattern.** A process filter matching `*publish.py*` matched the shell
  whose command line contained that text and killed it. No project job was harmed, but the
  general form — a pattern that matches the tool running it — is worth remembering.
- **When a diagnostic hangs, the diagnostic is a suspect.** (Run #15's headline: a probe asking
  for a `num_ctx` nobody serves.) **Your probes run on the same machine, under the same
  contention, as the thing they measure.**
- **A fast failure and a slow failure are different findings.** The fandom probe's **16.0s**
  False is what confirms M8 is still a block rather than something new.
- **Liveness is not progress.** `allsweep` reports 0 subsystems bad and nine jobs running while
  the reader discards 93% of its work and the queue is missing 668 entities. **Neither of this
  run's majors was visible to any liveness check.**
