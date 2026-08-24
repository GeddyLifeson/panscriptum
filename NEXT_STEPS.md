# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #15 wrote this on 2026-08-24 ~18:40 local.*

**Read this first.** Four things shape what is worth doing next run:

1. **THE SCHEDULE IS EVERY 15 MINUTES (`11,26,41,56 * * * *`), so you will routinely land on a
   live predecessor and that is the designed steady state.** The guard exits in seconds. It does
   **NOT** see interactive sessions — before writing anything, check
   `git -C C:\Users\imarl\panscriptum-export log --oneline -5` and `ls -lt src/*.py | head`. If
   either shows activity in the last few minutes you are not alone, and bouncing jobs or editing
   source is off the table. **Run #15 ended at `5400a97` (code) + the ledger commit after it.**
2. **M7 IS THE WHOLE JOB NEXT RUN, AND ITS VERDICT IS NO LONGER OUTSTANDING — IT IS BAD.**
   The gate binds and the reader still discards **76% rising to 93%** of handed chunks
   (`44 to GPU, 41 UNANSWERED`; `dropped 5554`). Run #15 **refuted** the tempting hypothesis:
   `read.config()` reads `num_ctx` from config correctly, so read does **not** share the m66/m68
   window defect. **Do not re-derive that.** What is left is contention against a physically
   tighter card — see §1.1, which is the highest-value thing you can do.
3. **WHEN A DIAGNOSTIC HANGS, THE DIAGNOSTIC IS A SUSPECT.** Run #15's whole finding came from
   an ad-hoc "is Ollama alive" one-liner that copied the standard's own shape, hung for three
   minutes, and had to be killed for competing with the card. It was not measuring the wedge; it
   *was* the wedge. **Your probes run on the same machine, under the same contention, as the
   thing you are measuring.** See §5.
4. **THE FOREMAN IS STILL RUNNING STALE CODE ON PURPOSE AND STILL HOLDS AN `--adopt` CHILD.**
   Verified run #15: pid **45432, parent 5420 (the foreman)**. §1.3's do-not-bounce condition is
   LIVE. Fandom is still blocked, so stale and fixed still return the same answer and nothing is
   lost — but the moment fandom answers, this matters.

## 1. Verify first

1. **[M7 — THE MEASUREMENT THAT DECIDES THE FIX. Do this before anything else.]** The question
   is no longer "is it bleeding" but "which of two causes". Read the reader's own log first —
   **ignore any line reading `0 to GPU`, that is cache replay**:
   ```
   tail -3 state/read_auto.log
   ```
   Then get the physical picture in one shot:
   ```
   ollama ps
   ```
   **Run #15 measured `qwen3:8b` at 12288 context occupying 8.0 GB of a 10 GB card** — run #13
   saw 4096 / 5.3 GB, so the resident window CHANGED and §2 F's long-standing question ("has the
   12288 window ever loaded?") is now answered **yes**. Against that sit `OLLAMA_NUM_PARALLEL=2`,
   read's `GATE_LOCAL_N=2`, **plus** `pipeline` and `overwatch` each holding a live connection:
   ```
   powershell -NoProfile -Command "Get-NetTCPConnection -RemotePort 11434 -State Established -ErrorAction SilentlyContinue | Group-Object OwningProcess | ForEach-Object { $p=Get-Process -Id $_.Name -ErrorAction SilentlyContinue; '{0,-8} {1,-16} conns={2}' -f $_.Name, ($(if($p){$p.ProcessName}else{'?'})), $_.Count }"
   ```
   **Four claimants, two slots, and read's 360s deadline.** The decisive experiment is cheap and
   nobody has run it: **time a probe at the resident window while the reader is in a GPU phase,
   and again after pausing `overwatch`.** Run #15 measured 32.9s for an 8-token generation under
   full load and 1.5s minutes later — *a 20x spread on the same call*, which is queue wait, not
   compute. If read's chunks are simply queueing past 360s, the fix is arbitration
   (`gpu_lane`, §2 H) or fewer standing claimants, **not** a longer timeout — a longer timeout
   buys the same discard later.
2. **[M7's other half — is a dropped chunk recoverable?]** Still §2 C, and now urgent rather than
   theoretical: **5,554 chunks** are logged `UNANSWERED, not cached` and no later pass knows to
   look at them again. **Even a perfect capacity fix does not get those back.** Whatever else
   happens, decide whether the drop should be *recorded* so a later pass can retry.
3. **[m65 — bounce the foreman ONLY when fandom is back, and check the child first.]** Unchanged
   and re-verified run #15 — **there IS a live `--adopt` child (45432 under 5420)**:
   ```
   powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*adopt*' } | ForEach-Object { '{0} parent={1}' -f $_.ProcessId, $_.ParentProcessId }"
   ```
   An `--adopt` child under the foreman's PID means **DO NOT BOUNCE** — the orphan rewrites
   `WIKI_HOSTS.json` from a stale snapshot (m42's paper trail; m42 has now held `202 / 191 /
   451703b8` for a **tenth** run — do not be the run that loses it).
4. **[M8 — is fandom back? Four seconds, TCP only, no politeness cost.]**
   ```
   python -c "import sys;sys.path.insert(0,'src');import standards as ST;print(ST.fandom_ipv4_reachable())"
   ```
   **`(True, '<ipv4>')` means it recovered — and that makes §1.3 urgent.** Run #15 got
   `(False, '172.66.2.166 TimeoutError')` in **16.0s**. **Read the latency, not just the
   boolean**: a slow False is a block; a fast False (<1s) is a THIRD answer meaning something new
   is wrong. That distinction caught m65.
5. **[m66/m67/m68 — the fixes are live; confirm they stayed live.]** Wants `(True, 'ledger')` in
   ~0.0s, or a **fast** number if the ledger is quiet. **A multi-minute answer means a hardcoded
   window is back:**
   ```
   python -c "import sys,time;sys.path.insert(0,'src');import standards as ST;t=time.time();print(ST.ollama_token_flow(),'%.1fs'%(time.time()-t))"
   ```
   `verify_math` §19ab now fails the whole battery if any module hardcodes a `num_ctx` inside an
   `options` dict, so this should be structurally impossible — **that check going red is the
   real alarm**, not this one-liner.
6. **[M4 — money]** Must print `598 False False True`:
   ```
   python -c "import sys;sys.path.insert(0,'src');import json,cascade_bridge as c;pb=json.load(open('state/PAID_BURST.json'));print(pb['used'],pb.get('enabled'),c.paid_lane_open(pb),c.PAID_LANE_RETIRED)"
   ```
7. **[m40 — the roster]** Run #15: **71 rounds / 68 findings**, flat against run #14. Flat is not
   a fault; **only a number going DOWN is a bug.**
   ```
   python -c "import json;d=json.load(open('data/OVERWATCH.json',encoding='utf-8'));print(d['rounds'],len(d['findings']))"
   ```
8. **[preflight — still exactly 2 FAILs, and both are owner-facing, not new bugs]**
   `API paths per host family` (**this is M8**) and `feats/www_dandwiki_com: all 200 sampled
   entries empty` (**this is M1**). Unchanged run #14 → #15. A THIRD FAIL is the finding.
9. **[the keeper — ANSWERED, do not re-investigate.]** Run #14 doubted it; run #15 caught it
   working: `state/overnight.log` shows `18:33:02 keeper: pipeline was down mid-cycle` followed by
   the restart. **The keeper thread is alive.** Run #14's seven-minute wait was a slow round, not
   a dead thread. Treat "restored within five minutes" as roughly true again.
10. **[the transient `publish.py` red — one look, no chase.]** The 18:12 page showed
    `every managed job is running: publish.py` red, but minutes later all five returned `True`
    from `overnight.running()` and publish had been up since 17:40 pushing normally. **Recorded
    as unexplained because it did not reproduce.** If it appears again, suspect `_proc_lines()`
    returning empty or truncated under load — but do not spend on a single non-reproducing blip.

## 2. Human decisions needed (owner)

A. **[M8 — STILL THE ONLY ONE BLOCKING REAL WORK] Is the fandom IPv4 outage a block we earned,
   or a network fault between here and Cloudflare?** Evidence that cannot separate them: all
   fandom content hosts share two Cloudflare IPv4 addresses and both time out; the same edge
   answers instantly over IPv6; other IPv4 destinations are fine. **Forcing IPv6 to get around it
   is a decision only you can make, and runs #14 and #15 both deliberately declined to take it.**
B. **[M7, link 1 — the fix for the CLASS] Should `tuning.regime()` decide on a measured success
   RATE instead of bucket reachability?** It returns `"cloud"` when
   `_answering_buckets() >= CLOUD_MIN_BUCKETS` while the live cloud rate is **42%** against a
   50% floor (page, run #15). Everything downstream inherits it. **Same root as m59, M8, and §5.
   Still nobody's decision but yours, and it is now the oldest open one.**
C. **[M7's other half] Should a dropped chunk be recoverable?** See §1.2 — **5,554 and counting.**
   Compare `write_record`'s `_landed` discipline: a write that does not land keeps the unit open
   rather than marking it done.
D. **[NEW — from the first `tuning.py` audit] Should `profile()`'s cloud worker count have a
   floor of 4 when the pool has collapsed?** `tuning.py:134` is
   `p["workers"] = max(4, min(16, n + 2))`. Because `regime()` caches for `RECHECK_SECONDS=180`
   while `profile()` re-reads the bucket count live, a *stale* `"cloud"` label can be paired with
   `n = 0` and still yield **4 workers against a dead pool** — structurally the "workers against
   one card" case the module exists to prevent. The clamp is documented ("clamped 4..16"), so
   **this is a question, not a fix.** Related, same audit: `"local"` and `"starved"` keep
   hardcoded `workers=2`/`1` and never derive from anything — deliberate (one card, one model) or
   oversight?
E. **[NEW — same audit] Two cache layers compound to pin a stale regime longer than either TTL
   advertises.** `tuning.RECHECK_SECONDS=180` and `read._GATE_STATE`'s `GATE_RECHECK_S=120` run on
   independent clocks, so read's gate width can be up to **240s** stale, not the 120s its constant
   implies. The audit verified this by reading both cache conditions; it did **not** instrument it
   live, so treat the 240s as arithmetic rather than observation. Also `read.py:285` defaults
   `_GATE_STATE["regime"]` to `"cloud"` — i.e. **open-wide before the first refresh**.
F. **[NEW — same audit] `tuning._ollama_up()` ignores `config.yaml`'s `ollama_host`.**
   `tuning.py:80` hardcodes `http://localhost:11434` as a default and line 119 calls it with no
   argument, while **every** other module reads the host from config. **Currently latent** —
   config.yaml names that same URL — so this is a small implementable item the day the host moves,
   and a trap until then. `tuning.py` imports no config module at all today, which may be
   deliberate dependency hygiene; that is the question.
G. **[NEW — same audit] `CLOUD_MIN_BUCKETS` has drifted into three reimplementations.**
   `pipeline.py:308` tests `_pool_answering() >= 3` with a **bare literal**, not
   `tuning.CLOUD_MIN_BUCKETS`, and `foreman.py:588` and `read.py:1018` each re-read
   `POOL_PROOF.json` on their own clocks. Change the constant and pipeline silently disagrees.
H. **[m54 + m55, one decision] Fix the two `gpu_lane` defects, then bounce — in that order.**
   **This is now M7-adjacent rather than housekeeping**: §1.1's four-claimants-two-slots picture
   is exactly what `gpu_lane` exists to arbitrate, and **m56 says it is arbitrating nothing**
   (`slots: []` while nine requests were in flight). m54: call `_touch` from inside `lane()`'s
   hold, or shorten the leases. m55: route the six `os.remove` sites through retry-with-backoff.
   **Read `gpu_lane`'s 13 silent handlers BEFORE bouncing it into service** (§3.2). Restart order,
   cheapest first: `overwatch` and `pipeline`; **`foreman` LAST and only per §1.3**; `read.py` and
   `feats.py --roll` are not keeper-restored.
I. **[§2 F, PARTLY ANSWERED — update it rather than re-asking] The `num_ctx` spread.** The
   machine still serves 4096 / 8192 / 12288 from different call sites, and with
   `OLLAMA_MAX_LOADED_MODELS=1` each switch evicts a runner. **What changed: the 12288 window HAS
   now loaded** (8.0 GB resident, run #15) and **the two sites that named a foreign window are
   fixed** (m66, m68) — so the remaining spread is between *config-derived defaults* in modules
   whose configs agree, not live disagreement. `pipeline.py:344` defends the small window on
   KV-cache grounds. **Still a question, but a much smaller one than when it was filed.**
J. **[m59 / m24] Should a bucket that fails N consecutive LIVE calls stand down until the next
   proof, and should the proof measure a rate rather than a single answer?** Same root as B.
   Also: `tuning.py:105` counts a **>1h stale** `POOL_PROOF.json` at full strength and only
   annotates the age ("Believe it, but say so"). Given m59 showed even a *fresh* proof certified
   4-of-36 while live calls ran at 2.8%, should age discount the count rather than caption it?
K. **[m58] Is `folder-mechanical` routing provisional?** Races and Backgrounds file under
   "Places & Locations" across 42 sources; the shelfmark says `[UNCHARTED]`, which suggests yes —
   in which case it is not a bug, and the answer belongs in the ledger so nobody files it again.
L. **[m57] The singulariser fix needs a corpus diff.** `catalogue_web.py:212` — 425 mangled
   types. Mechanical, but entry `type` feeds matching, so it needs a before/after diff of the
   whole corpus. Quiet-repo job.
M. **[the 240-char description truncation]** `pipeline.py:992` truncates every entry description
   to 240 chars before the model judges it; 50.6% of ~82,000 entries are longer. Still a
   QUESTION, **same shape as M6 and m13** — an input cap a downstream verdict treats as
   authoritative.
N. **[m25 / m16 / dashboard `findings` cap of 12] — ONE ruling, four sites: does Hard Rule 0 bind
   diagnostics and run logs, or only reader-facing listings?** Carried since run #5. **"Does
   anything downstream act on the truncated list?" is the workable test.**
O. **[the stale local buckets]** The reader logs **50 `REMOVED local-<model>: HTTP 404`** lines
   across five pruned models. Self-healing per process, so not a fault — but every consumer
   rediscovers the same five absences on every start. The roster lives **outside `src/`**, so
   pruning it is a question. Only `qwen3:8b` is installed (confirmed again run #15);
   `read.fallback_model()` still resolves to it, so "fall back to something smaller" is a
   **no-op rather than a bug**. Confirm the prune was intentional and let the ledger say so.
P. **[m51]** Should `check_context_budget` cover the generate path, or be renamed to say what it
   covers? **[m60]** Which trade for the last 22 oversized chapter blocks (largest **46,840**
   chars against a p99 of 11,978)? **[M4]** The burst lane — 598/500, retired structurally: raise,
   delete, or leave as evidence?
Q. **[m48] 70 sources collide under `_norm`**; **[m47]** what a failed feats join should look
   like; the 17 stranded feats records; the 87 hybrid Powers entries; should feats be their own
   VOLUME. **[m37]** Nothing reads `data/CHAIN.json`. **[M]** `GENRES.json` / `NAVTREE.json` have
   no automated writers. **[m29]** `cleanup.py`'s `_EMPTY_MECHANIC` predicate. **[m26]** the
   completeness audit cannot see 46 of 210 sources. **[m39]** `scout.sweep(limit=4)` can starve
   lower-ranked hostless sources. **[m38]** `foreman._function_source` resolves symbols by bare
   name (`main` has **74** definitions in `src/`). **[m12]**, **[m13]**, **[m30]**, **[M1]**,
   **[m43]** unchanged.
R. **Permanently hostless roll entries** — catalogued with no host **20**; on the roll but never
   catalogued **6**. The **91 DECIDED spine codes** from the 12:05 session are **still not written
   to `CHARTER_SPINE_CODES.json`**, which has no writer in `src/`. Rulings that never land in the
   charter appendix are erased on the next re-derive. Also **34 catalogued sources have no charter
   spine code** and three charter errata are open (Supercluster, Filament, Hyperverse are rungs
   with no Magnitude band).
S. **`site/state.json` is stale and nothing in `src/` references `site/`** — the live artifact is
   `docs/state.json`, written by `publish.py`. Dead directory, or something's input? **No deletion
   without a ruling.**

## 3. Small implementable items (no decision needed)

1. **[m62] Make the two `model_metrics.jsonl` appends atomic.** Five live processes append with a
   plain `open(path, "a")`; 5 lines are corrupt, three mid-record fragments. One `os.write` to an
   `O_APPEND` handle, at `cascade_bridge._metric` and `pipeline._metric`. Low exposure (0.019%).
   **Note `standards.py:186` is a downstream symptom** — it silently `continue`s past unparseable
   ledger lines, which is correct behaviour but means the tearing is invisible from there. (That
   line moved from 168; run #15's docstring grew above it.)
2. **35 silent exception handlers of 397** (`python src/silence.py`). **Run #15 added net zero** —
   one was introduced by the new §19ab scan and converted to a recorded, asserted failure before
   it landed, which is the pattern to copy. Concentration still matters: **`gpu_lane.py` 13**
   (105, 134, 140, 142, 144, 152, 169, 201, 256, 258, 321, 351 — **read these before §2 H**) and
   **`context_budget.py` 4** (246, 252, 265, 270 — fallback-to-empty-string when a prompt file
   cannot be read, which would generate against an EMPTY system prompt rather than fail). Also
   open: `entity_match.py:255`, `overnight.py:500` (**inside the keep-warm loop, so a keep-warm
   that never works is invisible**), `local_agent.py:157`/`475`, `publish.py:161`, `coverage.py:92`,
   `pipeline.py:1559`, `foreman.py:625`/`643`, `health.py:143`/`245`.
3. **`pipeline.py`'s 9 shared cross-phase JSON writes** still use raw `open+json.dump` rather than
   `_landed`/`replace_retry`. Medium surgery, 9 call sites, open since run #2. Same family as m62.
4. **The three run #5 audit findings, still un-actioned**: `hostcheck`'s `judgeable` flag is
   ignored by its own two consumers; `onomast.coin_well_formed`'s fallback skips both its quality
   and uniqueness checks; `feats._unwrap_templates` miscounts brace nesting on `{{{`.
5. **`FEATS_BLOCK_CHARS = 20000` still exists as `pack_feats`'s default third argument.** The
   manifest path derives the budget correctly, so this only bites a caller that forgets to pass
   one — exactly the mistake both an audit subagent and run #12 made when *calling* it. Make the
   parameter required.
6. **`JOB_OVERHEAD_CHARS`'s comment does not reproduce.** It cites "min 314, median 1,193, max
   1,536 across 331 blocks"; a re-measure across 3,386 real blocks gives min 115 / median 142 /
   max 368. The constant (2,000) errs conservative — the comment is wrong, not the code.
7. **[NEW, from the `tuning.py` audit — cosmetic]** `tuning.py:105` hardcodes `if age > 3600:`
   inside a module whose entire premise is "the settings that should never have been constants".
   Lift it to a named constant beside `RECHECK_SECONDS`. No behavioural consequence.
8. **[NEW, from the `tuning.py` audit — efficiency, benign]** A "print regime, then get workers"
   cycle re-reads `data/POOL_PROOF.json` up to **three** times within milliseconds
   (`profile(force=True)` then `workers()`, which re-enters `profile()` with its own
   `force=False`). Idempotent and mitigated by the atomic write, so **not** a correctness bug.
9. **DONE, do not redo:** m66 / m67 (the token-flow probe's window AND its success predicate —
   run #15, pinned by §19ab); m68 (`local_agent._chat`'s hardcoded 8192 — run #15, §19ab);
   m69 (`tuning.workers()`'s zero — run #15, §19ac); m63 and m65 (run #14); m64 (publishing,
   closed permanently); M8's *standard* (run #14, §19z/§19aa — **the outage itself is open**);
   m61 (§19s); the M7 gate fix (§19t — live, and **insufficient**, see §1.1); the 52,101-char
   manifest anomaly; m23's log truncation; the entrypass count mismatch (§19q).

## 4. Surface rotation for the next audit fan-out

**Run #15 spawned ONE subagent — `tuning.py`, §4's named highest-yield unaudited surface — and it
paid.** Seven findings; **one** verified into a fix (m69), **six** promoted to questions (§2 D, E,
F, G, J and §3.7, §3.8). That ratio is the point: the audit's job is to surface candidates, and
**verification against source is what separates them.** Two of its findings carried an explicit
"unverified" from the agent itself, and those stayed questions.

Covered, do **not** re-read unless the diff touched them: the round-1 full-codebase audit and
evening sweep (`handoff/AUDIT_*.md`); run #2's four surfaces; run #3's two; run #5's three;
run #6's four; run #7's five; run #9's `feats_index.py` and `hostcheck`; run #10's
`manifest_builder.pack_feats` + `generate.py`'s feats branch; run #11's `system_style.txt` and
`pipeline.py`'s `ask`/`ask_pool_first`/`phase_entrypass`; run #12's `gpu_lane.py` and
`context_budget.py`; run #13's `read.py` transport ladder (`_ask` / `_ask_ungated` / `_local` /
`_gate` only); **run #15's `tuning.py` (all 169 lines)**.

**Not yet audited line-by-line** — pick from here: **`read.py`'s chunking / caching / `_chunk_key`
paths** (now the highest-yield item, because M7's remaining cause lives near them and the
transport ladder above them is already covered), **`entity_match.py`** (still the only one of the
three new modules nobody has audited), `address_space.py`, `profile.py`, `burgs.py`, `tells.py`,
`style_audit.py`, `audit.py`, `descending_ladder.py`, `cosmography.py`, `genre.py`, `reference.py`,
`resync_roll.py`, `retry_synthesis.py`, `build_terminal.py`, `sweep.py`, `runguard.py`,
`compress_store.py`.

**Two open overwatch HIGHs were refuted at source by run #14** — `cosmography._fmt` (it IS defined
at `cosmography.py:256`) and `descending_ladder.compton_confinement_energy` (the code is
`p = HBAR / (2.0 * size_m)`, which IS hbar/(2r) as documented). **Do not spend on them again.**
The other two (`cleanup.clean_ceiling`, `silence.note`) read as observations rather than defects.

## 5. Lessons worth keeping

- **When a diagnostic hangs, the diagnostic is a suspect.** Run #15's headline finding was
  diagnosed by accidentally reproducing it: an ad-hoc "is Ollama alive" one-liner copied the
  standard's own `num_ctx: 512` shape, hung for three minutes, and had to be killed for competing
  with the card. The tool reaching for the answer *was* the bug. **Your probes run on the same
  machine, under the same contention, as the thing they measure.**
- **A check can manufacture the fault it reports — and inflict it on what it watches.** The
  512-token probe did not merely misread the daemon; with `keep_alive: -1` a probe that *won* its
  rebuild would have pinned a 512-token runner forever and forced every real caller to evict it
  back. **Ask what a diagnostic COSTS the system, not only whether it is accurate.**
- **One symptom can hide two independent defects, and fixing the visible one is not finishing.**
  The same probe had the wrong window *and* the wrong success predicate. Fixing the window alone
  would have moved it from "times out" to "completes and still reports a fault" — a change that
  looks like progress and is not.
- **Prove the fix by measuring the thing, not by reading the diff.** 512 → 180.1s timeout;
  12288 → 32.9s; the repaired function end-to-end → **1.5s**. Three numbers, one machine, minutes
  apart. **"A fix in the source is not a fix in the system" now has a companion: a fix asserted is
  not a fix measured.**
- **Refutations are findings and belong in the ledger.** Run #15 spent real effort on "does
  `read.py` share the window defect?" and the answer was **no**. Written down, that saves the next
  run the same hour. **An untested hypothesis and a refuted one look identical in a summary.**
- **Ranking the page's reds by whether they are ACTIONABLE beats working top to bottom.** Eleven
  reds; eight were known owner-facing states, one was transient and did not reproduce, and two
  were real. The page is a work-list, not a task-list.
- **A probe that lets the resolver choose is not measuring the path its callers are forced onto.**
  (M8's mechanism: a DNS record type.) **A check that certifies reachability is not a check on
  capacity.** Now the documented root of M7, m59, §2 B and M8 — **five sites, one mistake**, and
  m66 is its sixth cousin: a check that certified *the wrong window*.
- **When you flip a check red, go find its consumers before you ship** — and when you fix a call
  site, grep for the others. That is what turned m66 into m68 in one step, and it is the second
  consecutive run where that habit paid.
- **A fast failure and a slow failure are different findings.** m65 was caught because a gate that
  should time out against a block returned False in **0.13 seconds**. Applied again run #15: the
  fandom probe's **16.0s** False is what confirms M8 is still a block rather than something new.
- **Liveness is not progress.** `allsweep` says 0 subsystems bad and nine jobs running while the
  reader throws away 93% of its work. **The job's own log said so on every line.**
- **"The keeper restores it within five minutes" is a claim** — doubted by run #14, and **verified
  true by run #15** (`18:33:02 keeper: pipeline was down mid-cycle`). Claims in these ledgers are
  evidence, not proof; this one survived its test.
