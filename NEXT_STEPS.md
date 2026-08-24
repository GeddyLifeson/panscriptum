# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #14 wrote this on 2026-08-24 ~17:50 local.*

**Read this first.** Four things shape what is worth doing next run:

1. **THE SCHEDULE IS EVERY 15 MINUTES (`11,26,41,56 * * * *`), so you will routinely land on a
   live predecessor and that is the designed steady state.** The guard exits in seconds. It does
   **NOT** see interactive sessions — before writing anything, check
   `git -C C:\Users\imarl\panscriptum-export log --oneline -5` and `ls -lt src/*.py | head`. If
   either shows activity in the last few minutes you are not alone, and bouncing jobs or editing
   source is off the table. **Run #14 ended at `6fb290d` (code) + the ledger commit after it.**
2. **[M8] FANDOM IS UNREACHABLE OVER IPv4 AND THAT IS THE OWNER'S DECISION, NOT YOURS.** Every
   content wiki (`marvel`, `forgottenrealms`, `aneurism` — all A-record-only) times out at the
   socket; `community.fandom.com` answers only because it is the one host with AAAA records.
   **Do not route around it by forcing IPv6** — that evades a block the destination may have
   applied on purpose. The *standard* is fixed and now reads red honestly. Re-measure with §1.1,
   do not re-derive.
3. **THE FOREMAN IS RUNNING STALE CODE ON PURPOSE, AND THERE IS A DEADLINE ON IT.** Run #14 fixed
   `foreman._fandom_reachable` (m65) but did **not** bounce the foreman, because it was holding a
   live `hostcheck.py --adopt` child — §2 F's exact hazard. **While the block lasts, stale and
   fixed return the same answer, so nothing is lost.** The moment fandom answers again, the stale
   foreman keeps the catalogue switched off for the wrong reason. See §1.2.
4. **M7'S GATE IS FINALLY LIVE AND ITS VERDICT IS STILL OUTSTANDING.** `read.py` restarted 17:42
   and holds **2** Ollama connections (was 9) — the gate binds. **But the discard rate is not yet
   re-measured**, because a restarted reader replays cache first (`0 to GPU` at 10,000+ chunks/s
   is that artefact, not health). **Reading one GPU-phase progress line is the single highest-value
   thing you can do next run.** See §1.3.

## 1. Verify first

1. **[M8 — is fandom back? Four seconds, and it is unambiguous.]** No politeness cost, TCP only:
   ```
   python -c "import sys;sys.path.insert(0,'src');import standards as ST;print(ST.fandom_ipv4_reachable())"
   ```
   **`(True, '<ipv4>')` means it recovered — and that makes §1.2 urgent.** `(False, '... TimeoutError')`
   means it has not. **A fast `False` (<1s) is a THIRD answer and means something new is wrong**, not
   a block: a block times out, it does not answer instantly. That distinction is exactly what
   caught m65. If it recovered, the corroborating numbers are `every source is fully catalogued`
   and `sources with a reachable wiki` on the page, and `probe_failures` in `data/COMPLETENESS.json`
   (run #14: **164 of 164 rows unmeasurable**).
2. **[m65 — bounce the foreman ONLY when §1.1 says fandom is back, and check the child first.]**
   ```
   powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*adopt*' } | ForEach-Object { '{0} parent={1}' -f $_.ProcessId, $_.ParentProcessId }"
   ```
   **An `--adopt` child under the foreman's PID means DO NOT BOUNCE** — the orphan rewrites
   `WIKI_HOSTS.json` from a stale snapshot (m42's paper trail, and m42 has held `202 / 191 /
   451703b8` for nine runs; do not be the run that loses it). No child = bounce is safe; the
   keeper restores the foreman within 5 minutes.
3. **[M7 — the verdict. Read the reader's OWN log, never a status summary.]**
   ```
   tail -3 state/read_auto.log
   ```
   The progress line ends `(N to GPU, M UNANSWERED, not cached)`. **Ignore any line reading
   `0 to GPU` — that is cache replay.** Wait for N to be non-trivial, then M/N is the verdict:
   run #13 measured **94.6%** and anything above ~20% means it is still bleeding. Corroborate
   with the connection count, which must sit at `GATE_LOCAL_N` (2), not 9:
   ```
   powershell -NoProfile -Command "Get-NetTCPConnection -RemotePort 11434 -State Established -ErrorAction SilentlyContinue | Group-Object OwningProcess | ForEach-Object { $p=Get-Process -Id $_.Name -ErrorAction SilentlyContinue; '{0,-8} {1,-16} conns={2}' -f $_.Name, ($(if($p){$p.ProcessName}else{'?'})), $_.Count }"
   ```
   **`read.py` is NOT keeper-restored.** If it is down, check WHY before restarting: run #14's
   restart was justified because the supervisor's own lap had ended it (`rc=15 in 490m`) and was
   blocked in a 4-hour roll join, so there was no live reader to interrupt and no downtime cost.
   That reasoning is the precedent — **not** a standing licence to bounce a working reader.
4. **[the keeper did not fire within its five minutes, and that is worth one look.]** Run #14
   bounced `dashboard` and `publish` at ~17:33 and the keeper had not restored them by 17:40,
   though it logged normally at 17:07 and 17:12. The keeper is a daemon thread on a flat
   `time.sleep(300)` loop (`overnight.py:462`), so it should have. **Is the supervisor's keeper
   thread still alive, or did it die inside a `start()` while the main lap sits in
   `join(roll, timeout_h=4)`?** Cheap check — bounce nothing, just watch:
   ```
   tail -6 state/overnight.log
   ```
   A `keeper:` line newer than the last job death means it is alive. **If it is dead, every
   "the keeper restores it within 5 minutes" claim in these ledgers is false** and a lot of
   run-planning rests on it. Note also: `overnight.start()` inherits `sys.executable`, so jobs
   restarted from a maintenance run appear as `python.exe` where the supervisor's are
   `pythonw.exe`. Cosmetic — `running()` matches the command line — but do not read it as a double.
5. **[M4 — money]** Must print `598 False False True`:
   ```
   python -c "import sys;sys.path.insert(0,'src');import json,cascade_bridge as c;pb=json.load(open('state/PAID_BURST.json'));print(pb['used'],pb.get('enabled'),c.paid_lane_open(pb),c.PAID_LANE_RETIRED)"
   ```
6. **[m42 — hosts]** `WIKI_HOSTS.json` should still hold **202 bindings, 191 non-empty**, md5
   `451703b8`. Held for a **ninth** run. A DROP means a stale writer won (see §1.2).
7. **[m40 — the roster, and it is MOVING again]** Run #14: **71 rounds / 68 findings**, up from
   70/66. **Run #13's call was right**: flat was a symptom of M7, not an overwatch bug, and it
   un-flattened as soon as the reader stopped holding the card. Only a number going DOWN is a bug.
   ```
   python -c "import json;d=json.load(open('data/OVERWATCH.json',encoding='utf-8'));print(d['rounds'],len(d['findings']))"
   ```
8. **[preflight — 2 FAILs now, not 3]** "entries stranded in closed batches" is **GONE**, which
   §1.11 of the last queue pre-registered as "0 = the rung recovered". The remaining two are
   `API paths per host family` (**this is M8, not a separate bug**) and `feats/www_dandwiki_com:
   all 200 sampled entries empty` (that is M1, the dandwiki 403).
9. **[m64 — publishing]** CLOSED and now permanent (`pipeline.py` restarted 17:12:54). Wants
   `(True, 'ledger')` in ~0.0s; **a multi-second answer means the live probe is back**:
   ```
   python -c "import sys,time;sys.path.insert(0,'src');import standards as ST;t=time.time();print(ST.ollama_token_flow(),'%.1fs'%(time.time()-t))"
   ```
   The 120 `! [rejected] ... (fetch first)` lines in `publish.log` were the **doubled publisher
   racing itself**, now resolved to one — not a credential fault. A gap of more than ~20 minutes
   between export commits means the standing `--loop 10` is wedged again.

## 2. Human decisions needed (owner)

A. **[M8 — THE NEW ONE, AND THE ONLY ONE THAT BLOCKS REAL WORK] Is the fandom IPv4 outage a
   block we earned, or a network fault between here and Cloudflare?** Evidence that cannot
   separate them: all fandom content hosts share two Cloudflare IPv4 addresses and both time
   out; the same edge answers instantly over IPv6; other IPv4 destinations are fine. If it is a
   block, the standard's own order applies (stop fandom-facing jobs, let it age out, check
   `wiki_source.MIN_GAP`). If it is a route fault, that is a router/ISP/Norton question.
   **Either way, forcing IPv6 to get around it is a decision only you can make, and this run
   deliberately did not take it.**
B. **[M7, link 1 — still the fix for the CLASS rather than the instance] Should `tuning.regime()`
   decide on a measured success RATE instead of bucket reachability?** It returns `"cloud"` when
   `_answering_buckets() >= CLOUD_MIN_BUCKETS` while the live cloud rate is **4%** (the page's
   `calls that succeed` standard is red at `4% ok` against a 50% floor). Everything downstream
   inherits it: `_gate()` opens to 16, `profile()` and `workers()` size every job in the kit from
   that word. **M8 is the same lesson in a second place** — reachability certified over a path
   the callers cannot use. Same root as m59 and §5.
C. **[M7's other half] Should a dropped chunk be recoverable?** A chunk that times out is logged
   `UNANSWERED, not cached` and no later pass knows to look again. Even with the gate fixed,
   timeouts will happen. Compare `write_record`'s `_landed` discipline: a write that does not
   land keeps the unit open rather than marking it done.
D. **[new — the stale local buckets]** The reader logs **50 `REMOVED local-<model>: HTTP 404`**
   lines across **five** pruned models (`qwen3-30b`, `qwen3-30b-q3`, `gemma3-12b`, `qwen25-14b`,
   `llama31`). Self-healing per process, so not a fault — but every consumer rediscovers the same
   five absences on every start. The roster lives **outside `src/`** (Cascade's config /
   `state/cascade_scratch.db`), so pruning it is a question, not a fix. Related: only `qwen3:8b`
   is installed where the ledgers record nine; `read.fallback_model()` still resolves, to
   `qwen3:8b`, so "fall back to a smaller model that fits the card" is now a **no-op rather than a
   bug**. Confirm the prune was intentional and let the ledger say so.
E. **[m60] Which trade for the last 22 oversized chapter blocks?** Largest rendered block
   **46,840 chars** against a p99 of 11,978. Lower `WRITE_CHUNK` globally (8 → 4 roughly doubles
   the call count for all 9,153 jobs to fix 0.13% — poor trade) or split adaptively only when a
   block does not fit (better, but new machinery in `generate_job`'s loop, and `WRITE_CHUNK` was
   tuned 30 → 10 → 8 for instruction-following reasons, not context ones).
F. **[the `num_ctx` spread] Should every call site use ONE window?** The machine serves 4096
   (`pipeline.py:660`, `1026`), 8192 (`magnitude.py:628`) and 12288 (generate). With
   `OLLAMA_MAX_LOADED_MODELS = 1` and `KEEP_ALIVE = -1`, each switch evicts and reloads a 5.3 GB
   runner. **The resident runner currently reads `context_length: 4096`, `-np 1`** — so the 12288
   window STILL has not loaded and run #12's question is still unanswered, not answered. VRAM at
   the 4096 runner: **8,552 MiB used / 1,502 MiB free**, which is tighter than the 7,482/2,572
   run #13 saw. `pipeline.py:344` defends the small window on KV-cache grounds — deliberate
   design with a stated rationale, so a QUESTION, not a fix.
G. **[the `OLLAMA_*` variables — three constants, one physical fact]** `OLLAMA_NUM_PARALLEL = 2`
   is the real source of truth for both `gpu_lane.MAX_SLOTS = 2` and `read.GATE_LOCAL_N = 2`, with
   no link between them. **And the live runner is now `-np 1`**, so the environment and the runner
   already disagree — the gate lets 2 through a card serving 1 slot. Should they read it?
   `KEEP_ALIVE = -1` + `MAX_LOADED_MODELS = 1` are user environment variables, so the infinite
   expiry returns on every load — **do not re-file that as a bug.**
H. **[m54 + m55, one decision] Fix the two `gpu_lane` defects, then bounce — in that order.**
   m54: call `_touch` from inside `lane()`'s hold, or shorten the leases. m55: route the six
   `os.remove` sites through retry-with-backoff (`replace_retry`'s pattern, adapted — that helper
   wraps `os.replace`, not `os.remove`). **Read `gpu_lane`'s 13 silent handlers BEFORE bouncing it
   into service** (§3.3). Restart order, cheapest first: `overwatch` and `pipeline`; **`foreman`
   LAST and only per §1.2**; `read.py` and `feats.py --roll` are not keeper-restored.
I. **[m56] Nine jobs still predate `gpu_lane.py` (13:59)** and `gpu_lane.status()` reported
   `slots: []` while nine requests were in flight — the lane is arbitrating nothing.
J. **[m59 / m24] Should a bucket that fails N consecutive LIVE calls stand down until the next
   proof, and should the proof measure a rate rather than a single answer?** Same root as B.
K. **[m58] Is `folder-mechanical` routing provisional?** Races and Backgrounds file under
   "Places & Locations" across 42 sources; the shelfmark says `[UNCHARTED -- Ladder-of-Being pass
   not yet done]`, which suggests yes — in which case it is not a bug, and the answer belongs in
   the ledger so nobody files it again.
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
O. **[m51]** Should `check_context_budget` cover the generate path, or be renamed to say what it
   covers? Preflight still prints `ok context budget`.
P. **[M4] The burst lane** — 598/500, retired structurally. Raise, delete, or leave as evidence.
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
   **Note `standards.py:168` is a downstream symptom** — it silently `continue`s past unparseable
   ledger lines, which is correct behaviour but means the tearing is invisible from there.
2. **32 → 35 silent exception handlers of 395** (`python src/silence.py`). **Run #14 added none**;
   the +3 arrived with the foreman's own `--patch` commits at 17:06–17:10, which is worth knowing:
   **the model lane can raise this count unattended.** Concentration still matters: **`gpu_lane.py`
   13** (105, 134, 140, 142, 144, 152, 169, 201, 256, 258, 321, 351) and **`context_budget.py` 4**
   (246, 252, 265, 270 — fallback-to-empty-string when a prompt file cannot be read, which would
   generate against an EMPTY system prompt rather than fail). Also open: `entity_match.py:255`,
   `overnight.py:500` (**inside the keep-warm loop, so a keep-warm that never works is
   invisible**), `local_agent.py:463`, `publish.py:161`, `coverage.py:92`, and `pipeline.py:1559`.
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
7. **DONE, do not redo:** m63 (five duplicate `verify_math` section labels + `BUGS.md`'s three
   `### Major` headings — run #14, all renamed/merged); m64 (publishing, closed permanently once
   `pipeline.py` restarted); m65 (the foreman's missing User-Agent — run #14, pinned by §19aa);
   M8's *standard* (run #14, pinned by §19z — **the outage itself is open**); m61 (§19s); the M7
   gate fix (§19t, and it is now LIVE); the 52,101-char manifest anomaly; the pyflakes warning;
   m23's log truncation; the entrypass count mismatch (§19q); the `allsweep` roster (§19p).

## 4. Surface rotation for the next audit fan-out

**Run #14 spawned no subagents, and like run #13 that was a choice rather than an omission** —
the page's own opening work-list turned into two live, verified defects (M8 and m65) that were
worth more than a rotation audit, and both were found by direct measurement rather than by
reading code. **Rotation therefore unchanged from run #12.** One surface did shrink: `standards.py`
and `foreman.py`'s network gates are now read line-by-line and pinned, but only those two
functions.

Covered, do **not** re-read unless the diff touched them: the round-1 full-codebase audit and
evening sweep (`handoff/AUDIT_*.md`); run #2's four surfaces; run #3's two; run #5's three;
run #6's four; run #7's five; run #9's `feats_index.py` and `hostcheck`; run #10's
`manifest_builder.pack_feats` + `generate.py`'s feats branch; run #11's `system_style.txt` and
`pipeline.py`'s `ask`/`ask_pool_first`/`phase_entrypass`; run #12's `gpu_lane.py` and
`context_budget.py`; run #13's `read.py` transport ladder (`_ask` / `_ask_ungated` / `_local` /
`_gate` only).

**Not yet audited line-by-line** — pick from here: **`tuning.py`** (link 1 of M7's chain, §2 B,
and still nobody has read it — the highest-yield item on this list), **`entity_match.py`** (still
the only one of the three new modules nobody has audited), **`read.py`'s chunking / caching /
`_chunk_key` paths** (the transport ladder is covered, the rest of the file is not),
`address_space.py`, `profile.py`, `burgs.py`, `tells.py`, `style_audit.py`, `audit.py`,
`descending_ladder.py`, `cosmography.py`, `genre.py`, `reference.py`, `resync_roll.py`,
`retry_synthesis.py`, `build_terminal.py`, `sweep.py`, `runguard.py`, `compress_store.py`.

**Two open overwatch HIGHs were refuted at source by run #14** — `cosmography._fmt` ("used but
never defined" — it is defined at `cosmography.py:256`, and pyflakes is clean) and
`descending_ladder.compton_confinement_energy` ("uses HBAR instead of hbar/2" — the code is
`p = HBAR / (2.0 * size_m)`, which IS hbar/(2r), exactly as documented). Not hand-closed in
`data/OVERWATCH.json`, because overwatch owns that file and auto-triage re-verifies each round.
**Do not spend on them again.** The other two highs (`cleanup.clean_ceiling`, `silence.note`)
read as observations rather than defects and remain unverified.

## 5. Lessons worth keeping

- **A probe that lets the resolver choose is not measuring the path its callers are forced onto.**
  M8's whole mechanism was a DNS record type: `community.fandom.com` publishes AAAA, every content
  wiki does not, and `create_connection` stops at the first family that answers. Nothing in the
  code or its comment could have revealed that — it took `getaddrinfo`. Generalise it: when a
  check picks ONE representative, ask what makes that one representative, and measure the answer.
- **A fast failure and a slow failure are different findings.** m65 was caught because a gate that
  should time out against a block returned False in **0.13 seconds**. The verdict was "correct",
  and correct-for-the-wrong-reason is how a permanently-off gate survives. **Read the latency, not
  just the boolean.**
- **When you flip a check red, go find its consumers before you ship.** That search is what
  surfaced m65 — a second gate with the same host choice and a worse defect. The inverse of the
  lesson already on the books ("when you add a consumer of a shared file, grep the WRITERS").
- **A fix can introduce its own exact inverse, and both belong in the same docstring.**
  `foreman._fandom_reachable` went from "a socket is not an answer" (right) to a bare `urlopen`
  that 403s on every call (wrong in the opposite direction), inside one morning. Neither author
  was careless. The record is only legible if both halves sit together.
- **Liveness is not progress.** `allsweep` said nine running lines and 0 subsystems bad while
  `read.py` threw away 94.6% of its work for seven and a half hours. **The job's own log said so
  on every line.** When a job's output matters, read the output, not the roster.
- **A surprising result from a measurement you just changed is evidence about the measurement
  first.** Two runs in a row were caught by this shape; run #14 avoided a third by checking
  `curl.exe` against Python before blaming Norton's TLS interception — the machine's most
  plausible-sounding culprit, and the wrong one.
- **A fix in the source is not a fix in the system.** A Python process does not re-read its own
  file. M7's gate sat inert for two runs; it took a restart, and the proof was a connection count,
  not a code review. **When a ledger says a fix landed, ask what is EXECUTING it.**
- **"The keeper restores it within five minutes" is a claim, not a guarantee** — run #14 waited
  seven and restored two jobs by hand. See §1.4.
- **A check that certifies reachability is not a check on capacity.** Now the documented root of
  M7, m59, §2 B **and M8**. Four sites, one mistake.
