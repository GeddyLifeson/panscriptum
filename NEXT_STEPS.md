# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #13 wrote this on 2026-08-24 ~16:45 local.*

**Read this first.** Four things shape what is worth doing next run:

1. **THE SCHEDULE IS HOURLY (`11 * * * *`).** Expect to be alone; if the overlap guard says a
   maintenance predecessor is live, a run hung — check the heartbeat age. **The guard does NOT
   see interactive sessions.** Before writing anything, check
   `git -C C:\Users\imarl\panscriptum-export log --oneline -5` and `ls -lt src/*.py | head`. If
   either shows activity in the last few minutes you are not alone, and bouncing jobs or editing
   source is off the table.
2. **M7 IS THE WHOLE QUEUE UNTIL SOMEONE DECIDES IT.** `read.py` spent 7.5 hours discarding
   **1,168 of 1,235** chunks it handed to the GPU, while every status surface read green. A
   narrow fix is in the source and **is executing nowhere** because `read.py` has not restarted.
   Do not "re-find" this by reading code — read `state/read_auto.log` and check the live numbers
   in §1.1. Full chain in BUGS.md [M7].
3. **THE READINGS YOU INHERIT ARE CLOUD-ONLY IF THEY PREDATE THIS RUN.** `pipeline._metric` wrote
   no `at` field for the life of the ledger, so every time-windowed model measurement ever
   recorded — m59's "1,571 calls/hour", "26 a minute", "976/hour at 4.1%" — silently counted
   **only cloud rows** and dropped all 913 local ones. Fixed (m61), but **`pipeline.py` has not
   restarted, so new local rows are still unstamped.** Until it does, any local-vs-cloud split
   you compute is still cloud-only. Do not compare a post-restart number to a pre-restart one.
4. **THE 12288 WINDOW STILL HAS NOT LOADED.** `/api/ps` reads `context_length: 6144`; the runner
   has been up since 13:29 and nothing has forced a reload. Run #12's question is untouched, not
   answered — see §1.3. **Only one model is installed now** (`qwen3:8b`), where the ledgers say
   nine; disk went 5 GB → 212 GB free. Looks like a deliberate prune, no fault found, but
   nothing records it.

## 1. Verify first

1. **[M7 — is the reader still throwing work away? Three numbers, two minutes.]** The discard
   rate is the whole diagnosis; everything else is commentary.
   ```
   powershell -NoProfile -Command "Get-NetTCPConnection -RemotePort 11434 -State Established -ErrorAction SilentlyContinue | Group-Object OwningProcess | ForEach-Object { $p=Get-Process -Id $_.Name -ErrorAction SilentlyContinue; '{0,-8} {1,-20} conns={2}' -f $_.Name, ($(if($p){$p.ProcessName}else{'?'})), $_.Count }"
   ```
   Then the reader's own log — **not a status summary, which said "0 subsystems bad" throughout**:
   ```
   tail -3 state/read_auto.log
   ```
   The progress line ends `(N to GPU, M UNANSWERED, not cached)`. **M/N was 94.6% and anything
   above ~20% means it is still bleeding.** Run #13's last reading: `1235 to GPU, 1168
   UNANSWERED`. More than 2 established connections from the `read.py` PID means the gate is
   still not binding (i.e. the fix is still not live, or did not take).
2. **[M7's decision — the fix is inert until `read.py` restarts, and that is the owner's call.]**
   `read.py` is **NOT keeper-restored** (the keeper re-asserts only dashboard, publish, foreman,
   overwatch, pipeline every 5 min); it hangs off the supervisor's hours-long lap, so a bounce
   costs real downtime and a restart discards nothing but does not recover the 1,168 dropped
   chunks either — those are gone from this pass and no later pass knows to look. **Do not
   restart it unprompted.** If it HAS restarted, confirm the fix took by re-reading §1.1: the
   connection count should sit at `GATE_LOCAL_N` (2), not 9.
3. **[the 12288 window — still the unobserved half of M6.]** When a runner next loads at 12288:
   ```
   curl.exe -s --max-time 20 http://127.0.0.1:11434/api/ps
   nvidia-smi --query-gpu=memory.used,memory.free --format=csv
   ```
   **`context_length` should read 12288 and the model should still be fully on GPU.** Predicted
   ~+0.8 GB from the measured KV rate (~0.127 GB/1k, and note `OLLAMA_KV_CACHE_TYPE = q8_0`
   already halves it), **but `OLLAMA_NUM_PARALLEL = 2` may allocate the window PER SLOT and
   double it.** Run #13 read 7,482 MiB used / 2,572 MiB free with the 6144 runner resident, so
   the headroom is real but not generous. If it spills to CPU, the honest move is 8192 plus
   trimming the chapter system prompt — **not leaving it spilled.**
4. **[the local rung — it was ALIVE and fast this run, which is new.]** Run #12's five dead probe
   arms were GPU contention, not a wedged daemon. Control at an idle card: **0.58 s**. The same
   call while `read.py` was saturating it: **113-178 s of pure queue wait.** So the rung's
   health is not a property of the daemon, it is a property of **who else is on the card** —
   measure the connections (§1.1) before concluding anything about Ollama itself.
   The known wedge is still worth knowing: `/api/ps` naming a resident model while NO
   `llama-server.exe` process exists means nothing drains the queue and every call 503s forever;
   restart `ollama.exe`. That was NOT the shape this run.
5. **[m59 — the cloud storm, and now with the correct denominator.]** This one-liner **crashes on
   the real file** (m62 tears it); this version tolerates that and separates the two lanes,
   which the old one silently could not:
   ```
   python -c "import json,time,collections;now=time.time();c=collections.Counter();n=0;
   [ (c.update([(d.get('tag'),bool(d.get('ok')))]) if isinstance(d.get('at'),(int,float)) and now-d['at']<=3600 else None) for d in (json.loads(l) for l in open('state/model_metrics.jsonl',encoding='utf-8') if l.strip() and l.strip()[0]=='{') ];print(c)"
   ```
   Run #13: **976 calls/hour, 40 ok = 4.1%**, all `cascade:coding`. Local rows will only start
   appearing here once `pipeline.py` restarts (see the preamble, item 3).
6. **[m56 — still true, still nine jobs behind the code.]** All nine standing jobs predate
   `gpu_lane.py` (13:59). Corroborated a second way this run: `gpu_lane.status()` reported
   `slots: []` while **nine requests were in flight**. The lane is arbitrating nothing.
   ```
   python -c "import sys;sys.path.insert(0,'src');import gpu_lane;print(gpu_lane.status())"
   ```
7. **[m40 — the "flat is fine" rule DOES NOT APPLY right now, and run #13 nearly filed it wrong.]**
   Held at **70 rounds / 66 findings**. The standing rule is that only a number going DOWN is a
   bug — but one glance at `state/overwatch.log` showed the 16:40 round reporting **`0 raw
   0 new` for EVERY module**, note `(GPU busy; 8 calls to the cloud)`, with `cascade_bridge`
   taking **7,873 s (2.2 h) to find nothing**. **The number is not going down, it is going
   nowhere — the rounds run and produce nothing, because M7 has the card and the cloud is at
   4%.** So m40 flat is a SYMPTOM of M7, and it will un-flatten on its own when M7 is fixed. **Do
   not re-file it as an overwatch bug.**
   ```
   python -c "import json;d=json.load(open('data/OVERWATCH.json',encoding='utf-8'));print(d['rounds'],len(d['findings']))"
   tail -6 state/overwatch.log
   ```
8. **[M4 — money]** Must print `598 False False True`:
   ```
   python -c "import sys;sys.path.insert(0,'src');import json,cascade_bridge as c;pb=json.load(open('state/PAID_BURST.json'));print(pb['used'],pb.get('enabled'),c.paid_lane_open(pb),c.PAID_LANE_RETIRED)"
   ```
9. **[m42 — hosts]** `WIKI_HOSTS.json` should still hold **202 bindings, 191 non-empty**, md5
   `451703b8`. Held for an eighth run. A DROP means a stale writer won.
10. **[m49 — the roster]** `allsweep` must report **nine** `running` lines. Held. **But note what
    run #13 proved about this check: nine green lines and "0 subsystems bad" were true while the
    reader discarded 95% of its work.** Liveness is not progress.
11. **[preflight's third FAIL is a thermometer, not a bug.]** "entries stranded in closed
    batches" **steady at 4**, not climbing. Climbing = saturation worsening; 0 = the rung
    recovered.

## 2. Human decisions needed (owner)

A. **[M7, link 1 — the one that actually fixes the class, not the instance] Should
   `tuning.regime()` decide on a measured success RATE instead of bucket reachability?** It
   returns `"cloud"` when `_answering_buckets() >= CLOUD_MIN_BUCKETS`, and that was TRUE this
   run while the live cloud rate was **4.1%**. Everything downstream inherits the error:
   `_gate()` opens to 16, `profile()` and `workers()` size every job in the kit from it. Run #13
   fixed only the local leg's concurrency — the narrowest change that stops the bleeding —
   because changing `regime()` changes worker counts everywhere. **This is the real fix and it
   is a design decision.** Same root as m59 and as §5's reachability-vs-capacity lesson, which
   has now been written down for three runs and has started costing measurable work.
B. **[M7's other half] Should a dropped chunk be recoverable?** A chunk that times out is logged
   `UNANSWERED, not cached` and **no later pass knows to look again** — 1,168 of them are simply
   gone from this reading pass. Even with the gate fixed, timeouts will happen. Should the
   unanswered set land somewhere a later pass can re-read, the way an unfinished batch already
   stays open? (Compare `write_record`'s `_landed` discipline: a write that does not land keeps
   the unit open rather than marking it done.)
C. **[m60] Which trade for the last 22 oversized chapter blocks?** Largest rendered block
   **46,840 chars** against a p99 of 11,978. Either lower `WRITE_CHUNK` globally (8 → 4 roughly
   doubles the call count for all 9,153 jobs to fix 0.13% — poor trade) or split adaptively only
   when a block does not fit (better, but new machinery in `generate_job`'s loop, and
   `WRITE_CHUNK` was tuned 30 → 10 → 8 for instruction-following reasons, not context ones).
D. **[the `num_ctx` spread] Should every call site use ONE window?** The machine serves 4096
   (`pipeline.py:660`, `1026` — both explicit, so raising the config did NOT change them), 8192
   (`magnitude.py:628`) and 12288 (generate). With `OLLAMA_MAX_LOADED_MODELS = 1` and
   `KEEP_ALIVE = -1`, **each switch evicts and reloads a 5.3 GB runner.** `pipeline.py:344`
   defends the small window on KV-cache grounds, which was sound before the daemon was pinned to
   one resident runner and is arguably inverted now. **Deliberate design with a stated rationale
   — a QUESTION, not a fix.**
E. **[the `OLLAMA_*` environment variables — and one of them is now load-bearing for M7.]**
   `OLLAMA_NUM_PARALLEL = 2` is the real source of truth for both `gpu_lane`'s hardcoded
   `MAX_SLOTS = 2` **and** `read.GATE_LOCAL_N = 2`. Three constants, one physical fact, no link
   between them: if you ever raise `NUM_PARALLEL`, two files silently keep throttling to 2.
   Should they read it? Also `KEEP_ALIVE = -1` + `MAX_LOADED_MODELS = 1` are user environment
   variables, so the infinite expiry returns on every load no matter who issues it — **do not
   re-file that as a bug.**
F. **[m54 + m55, and they are one decision] Fix the two `gpu_lane` defects, then bounce — in that
   order.** m54: call `_touch` from inside `lane()`'s hold, or shorten the leases to match real
   call durations. m55: route the six `os.remove` sites through retry-with-backoff (the
   `replace_retry` pattern, adapted — that helper wraps `os.replace`, not `os.remove`). Restart
   order, cheapest first: **`overwatch` and `pipeline`** (keeper restores both within 5 min);
   **`foreman` LAST and carefully** (bouncing it while it holds an `--adopt` child orphans a
   process that then writes `WIKI_HOSTS.json` from a stale snapshot); **`read.py` and
   `feats.py --roll` are NOT keeper-restored** — but note M7 and m61 both need exactly those two
   restarts to take effect, so the calculus has changed since run #12 wrote this.
G. **[m59] Should a bucket that fails N consecutive LIVE calls stand down until the next proof,
   and should the proof measure a rate rather than a single answer?** Same root as A. Mind m24's
   paper trail on how easily a bucket gets buried.
H. **[m58] Is `folder-mechanical` routing provisional?** Races and Backgrounds file under
   "Places & Locations" across 42 sources; the shelfmark says `[UNCHARTED -- Ladder-of-Being pass
   not yet done]`, which suggests yes — in which case it is not a bug, and the answer belongs in
   the ledger so nobody files it again.
I. **[m57] The singulariser fix needs a corpus diff.** `catalogue_web.py:212` — 425 mangled
   types. Mechanical, but entry `type` feeds matching, so it needs a before/after diff of the
   whole corpus. Quiet-repo job.
J. **[the 240-char description truncation]** `pipeline.py:992` truncates every entry description
   to 240 chars before the model judges it; 50.6% of ~82,000 entries are longer. Still a
   QUESTION, still unanswered, **same shape as M6 and m13** — an input cap a downstream verdict
   treats as authoritative.
K. **[m25 / m16 / dashboard `findings` cap of 12] — ONE ruling, four sites: does Hard Rule 0 bind
   diagnostics and run logs, or only reader-facing listings?** Carried since run #5. **"Does
   anything downstream act on the truncated list?" is the workable test.**
L. **[m51]** Should `check_context_budget` cover the generate path, or be renamed to say what it
   covers? **M6 made this sharper: it printed `ok context budget` while 100% of chapter calls
   refused.** Preflight still prints `ok context budget` today.
M. **[M4] The burst lane** — 598/500, retired structurally. Raise, delete, or leave as evidence.
N. **[m48] 70 sources collide under `_norm`**; **[m47]** what should a failed feats join look
   like; the 17 stranded feats records; the 87 hybrid Powers entries; should feats be their own
   VOLUME.
O. **[m37]** Nothing reads `data/CHAIN.json`. **[M]** `GENRES.json` / `NAVTREE.json` have no
   automated writers. **[m29]** `cleanup.py`'s `_EMPTY_MECHANIC` predicate — exclusions are
   permanent.
P. **[m26]** the completeness audit cannot see 46 of 210 sources. **[m39]** `scout.sweep(limit=4)`
   can starve lower-ranked hostless sources. **[m38]** `foreman._function_source` resolves symbols
   by bare name (`main` has **74** definitions in `src/`). **[m12]**, **[m13]**, **[m30]**,
   **[M1]**, **[m43]** unchanged.
Q. **Permanently hostless roll entries** — catalogued with no host **20**; on the roll but never
   catalogued **6**. The **91 DECIDED spine codes** from the 12:05 session are **still not
   written to `CHARTER_SPINE_CODES.json`**, which has no writer in `src/`. Rulings that never
   land in the charter appendix are erased on the next re-derive. Also **34 catalogued sources
   have no charter spine code** and three charter errata are open (Supercluster, Filament,
   Hyperverse are rungs with no Magnitude band).
R. **`site/state.json` is stale and nothing in `src/` references `site/`** — the live artifact is
   `docs/state.json`, written by `publish.py`. Dead directory, or something's input? **No
   deletion without a ruling.**
S. **[new] Only one Ollama model is installed** (`qwen3:8b`), where the ledgers record nine, and
   disk went 5 GB → 212 GB free. Almost certainly a deliberate prune that also closed BUGS M2.
   **No fault found** — `read.fallback_model()` still resolves, to `qwen3:8b`, which is also the
   config model, so the "fall back to a smaller model that fits the card" design is now a no-op
   rather than a bug. Confirm it was intentional, then let the ledger say so.

## 3. Small implementable items (no decision needed)

1. **[m62] Make the two `model_metrics.jsonl` appends atomic.** Five live processes append with a
   plain `open(path, "a")`; 5 lines are corrupt, three of them mid-record fragments, most recent
   **13:07 today**, so it is ongoing. One `os.write` to an `O_APPEND` handle, at
   `cascade_bridge._metric` and `pipeline._metric`. Low exposure (0.019%, and the dashboard
   parses per-line in a `try`) — **but do it in a quiet window, not alongside a `read.py` change.**
2. **[m63] Two different `verify_math` sections are both labelled "Section 19r"** (lines 2031 and
   2134). Rename one. Run #13 used 19s/19t rather than renaming a predecessor's label unasked.
   **`BUGS.md` likewise has two `### Major` headings** (the Open list is split across them).
3. **32 silent exception handlers of 386** (`python src/silence.py`) — steady at 32 for two runs,
   so the tripling is accounted for, not ongoing. The concentration still matters: **`gpu_lane.py`
   13** (105, 134, 140, 142, 144, 152, 169, 201, 256, 258, 321, 351) and **`context_budget.py` 4**
   (246, 252, 265, 270 — fallback-to-empty-string when a prompt file cannot be read, which would
   generate against an EMPTY system prompt rather than fail). **Read the `gpu_lane` 13 BEFORE
   bouncing it into service** (§2 F): thirteen swallow-and-continue sites in an unproven resource
   arbitrator that has never taken real load. Also open: `entity_match.py:255`,
   `overnight.py:491` (**inside the keep-warm loop, so a keep-warm that never works is
   invisible**), `local_agent.py:463`, and `pipeline.py:321`, which records to
   `state/failures.json` but writes **nothing to `state/pipeline.log`**, the file an operator
   actually watches.
4. **`pipeline.py`'s 9 shared cross-phase JSON writes** still use raw `open+json.dump` rather than
   `_landed`/`replace_retry`. Medium surgery, 9 call sites, open since run #2. Same family as m62.
5. **The three run #5 audit findings, still un-actioned**: `hostcheck`'s `judgeable` flag is
   ignored by its own two consumers; `onomast.coin_well_formed`'s fallback skips both its quality
   and uniqueness checks; `feats._unwrap_templates` miscounts brace nesting on `{{{`.
6. **`FEATS_BLOCK_CHARS = 20000` still exists as `pack_feats`'s default third argument.** The
   manifest path derives the budget correctly, so this only bites a caller that forgets to pass
   one — which is exactly the mistake both an audit subagent and run #12 made when *calling* it.
   Make the parameter required.
7. **`JOB_OVERHEAD_CHARS`'s comment does not reproduce.** It cites "min 314, median 1,193, max
   1,536 across 331 blocks"; a re-measure across 3,386 real blocks gives min 115 / median 142 /
   max 368. The constant (2,000) errs conservative — the comment is wrong, not the code.
8. **DONE, do not redo:** m61 (the metrics timestamp, run #13, pinned by §19s); the M7 gate fix
   itself (run #13, pinned by §19t — but it is NOT LIVE, see §1.2); the 52,101-char manifest
   anomaly (run #12 — honest); the pyflakes warning; m23's log truncation; the entrypass count
   mismatch (§19q); the `allsweep` roster (§19p).

## 4. Surface rotation for the next audit fan-out

**Run #13 spawned no subagents, and that was a choice rather than an omission** — the queue's own
top item turned into a live outage (M7) worth more than a rotation audit, and the local rung was
healthy enough to measure directly. The rotation is therefore **unchanged from run #12** except
that `read.py`'s transport ladder is now **partly** covered: M7 traced `_ask` / `_ask_ungated` /
`_local` / `_gate` end to end with live evidence, but **`read.py`'s chunking, caching and
`_chunk_key` paths were never read** and the "highest-yield, never audited" label still applies
to the rest of the file.

Covered, do **not** re-read unless the diff touched them: the round-1 full-codebase audit and
evening sweep (`handoff/AUDIT_*.md`); run #2's four surfaces; run #3's two; run #5's three;
run #6's four; run #7's five; run #9's `feats_index.py` and `hostcheck`; run #10's
`manifest_builder.pack_feats` + `generate.py`'s feats branch; run #11's `system_style.txt` and
`pipeline.py`'s `ask`/`ask_pool_first`/`phase_entrypass`; run #12's `gpu_lane.py` and
`context_budget.py`.

**Not yet audited line-by-line** — pick from here: **`entity_match.py`** (still the only one of
the three new modules nobody has audited), `tuning.py` (**newly interesting: it is link 1 of
M7's chain and nobody has read it**), `address_space.py`, `profile.py`, `burgs.py`, `tells.py`,
`style_audit.py`, `audit.py`, `descending_ladder.py`, `cosmography.py`, `genre.py`,
`reference.py`, `resync_roll.py`, `retry_synthesis.py`, `build_terminal.py`, `sweep.py`,
`runguard.py`, `compress_store.py`.

## 5. Lessons worth keeping

- **Liveness is not progress, and this run finally priced it.** `allsweep` said nine running
  lines and 0 subsystems bad while `read.py` threw away 94.6% of its work for seven and a half
  hours. **The job's own log said so on every line.** When a job's output matters, read the
  output, not the roster.
- **A surprising result from a measurement you just changed is evidence about the measurement
  first.** Fixing the metrics reader produced "100% cloud, the local lane has never run" — a
  tidy, dramatic, wrong conclusion caused by my own `at` filter. One run after `fits()`'s truthy
  tuple reported 0 overflows out of 17,370. **Two runs, same shape, both self-inflicted.**
- **Ask what the fix does in the OTHER branch before shipping it.** The first version of M7's
  gate would have deadlocked every worker, because `_gate()` hands out the same semaphore when
  the regime reads `local`. It cost one question to find and would have cost the whole reader to
  miss. Then it was proved with 12 real threads, not reasoned about.
- **A fix in the source is not a fix in the system.** A Python process does not re-read its own
  file. **Both** of this run's fixes are currently executing nowhere, and so are run #11's and
  run #12's. When a ledger says a fix landed, ask what is EXECUTING it — one process start time
  against one file mtime answers it.
- **A control that fails tells you nothing about the variable.** Run #12 could not measure the
  local rung because all five probe arms failed. That was not evidence the rung was broken; it
  was GPU contention, and when the contention cleared the control returned in 0.58 s.
- **A check that certifies reachability is not a check on capacity.** Written down for three
  runs; it is now the documented root of M7, m59, and §2 A. `regime()` reads "cloud" at a 4.1%
  live success rate, and every worker count in the kit is derived from that word.
- **Three constants, one physical fact, no link between them.** `OLLAMA_NUM_PARALLEL = 2`,
  `gpu_lane.MAX_SLOTS = 2`, `read.GATE_LOCAL_N = 2`. Change the environment variable and two
  files keep silently throttling to the old number.
