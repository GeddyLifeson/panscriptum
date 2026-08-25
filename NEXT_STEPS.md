# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #19 wrote this on 2026-08-24 ~22:40 local.*

**Read this first.** Four things shape what is worth doing next run:

1. **THE SCHEDULE IS NOW HOURLY (`11 * * * *` + 523s jitter, so it fires ~:19–:20). Owner
   changed it 2026-08-24 evening; it is NOT every 15 minutes any more.** Consequences: you will
   usually find the previous run FINISHED rather than live, there is a 25–40 minute idle gap
   between passes that only the bots cover, and **you can afford to be more thorough than the
   15-minute era allowed.** The 15 minutes in the overlap guard is the heartbeat-staleness
   threshold — a different number, unchanged, do not "fix" it to match.
   The guard does **NOT** see interactive sessions — before writing anything, check
   `git -C C:\Users\imarl\panscriptum-export log --oneline -5` and `ls -lt src/*.py | head`.
   **Verify the cadence with `list_scheduled_tasks`, never from a file.** This claim has been
   wrong twice in opposite directions precisely because nobody read the cron back.
2. **RUN #19 FIXED THE REPORTING HALF OF M15. THE DESIGN QUESTION IS STILL OPEN AND STILL THE
   OWNER'S.** Do not re-apply the note fix, and do not read the fix as the bug being closed. What
   changed: both killing remedies now state the TRUE restart horizon per job, derived from
   `overnight.STANDING`. What did not change: the foreman still kills the reader when the pool is
   what stalled, and the reader still waits a lap. See §2 A.
3. **THE MOVEMENT PANEL CAN REPORT A HEALTHY SYSTEM AS STALLED. CHECK BEFORE YOU BELIEVE IT.**
   `dashboard.py:338` is `stalled = delta == 0 and span >= 10` over a **30-minute** window
   (`MOVED_WINDOW_MIN`, :287), while `cited`/`settled`/`feats` come from `data/COVERAGE.json`,
   which `allsweep.py:203-207` itself treats as fresh up to **2 hours**. A file not rewritten
   inside the window **cannot** produce a delta. One command before trusting a coverage stall:
   ```
   python -c "import os,time;print('%.2fh'%((time.time()-os.path.getmtime('data/COVERAGE.json'))/3600))"
   ```
   Under 0.5h → the stall is real. Over 0.5h → it is an artifact of the window, not a finding.
   **Run #19 measured 0.13h, so its flat coverage was genuine.** `chunks` and `entities read` do
   **not** share this hazard (different sources) and can be trusted directly.
4. **AGE EVERY `bucket_state.last_error` ROW, AND CHECK THE ERROR TEXT, NOT JUST THE OK RATE.**
   Run #19 nearly recorded a fifth dead bucket: `sambanova:free` shows **16 calls, 0 ok**, which
   looks identical to a dead key — but its error is a genuine `"Rate limit exceeded"`. Four dead
   accounts, not five. A 0% bucket is a symptom; the error string is the diagnosis.

## 1. Verify first

1. **[M15 — DID THE READER GET KILLED AGAIN? Still the first thing to check, every run.]**
   ```
   grep -nE "kill_stalled_job|restart_reader|read: (finished|starting)" state/overnight.log | tail -12
   ```
   The downtime series is now **1, 8, 32, 37, 42, 44 min, and once 4h**. **Run #19 ended with the
   reader DOWN** — killed at **22:01:42**, still absent 34 minutes later, no `read: starting`.
   **Measure how long that gap finally ran; it is the third measured instance and the first the
   new honest note will have described in the log.** Read the note text itself — it should now
   name the MAIN LAP, not "next cycle". If it still says "next cycle", the foreman is running
   pre-run-#19 code and needs a bounce (see §1.5).
2. **[§2 B — ARE THE FOUR DEAD BUCKETS STILL IN ROTATION? One query, highest value on the page.]**
   ```
   python -c "import sqlite3,time;c=sqlite3.connect('file:state/cascade_scratch.db?mode=ro',uri=True);t=time.time()-10800;print(list(c.execute('select bucket,outcome,count(*) from usage where ts>? group by bucket,outcome order by 3 desc',(t,))))"
   ```
   Run #19 measured **302 calls / 203 non-ok (67%)**, with the four dead accounts at **92 = 45% of
   all refusals, up from run #18's 38%.** It is getting worse, not better. **If those four are
   gone, the owner acted and the pool's whole picture changed — re-measure before reasoning from
   anything below.**
3. **[preflight — the baseline is 1 FAIL. A SECOND is the finding.]** Run #19 got exactly one:
   `caches empty ... feats/www_dandwiki_com` (**M1**). `API paths per host family` (**M8**) passed
   again. If M8's line returns, fandom went away again — check §1.4 before theorising.
4. **[M8 — is fandom still back? Four seconds, TCP only.]**
   ```
   python -c "import sys,time;sys.path.insert(0,'src');import standards as ST;t=time.time();print(ST.fandom_ipv4_reachable(), '%.1fs'%(time.time()-t))"
   ```
   Run #19: `(True, '172.66.2.166')` in **0.0s** — fully recovered, against run #18's slow 8.0s.
   **Read the latency:** a slow `False` is a block; a fast `False` (<1s) is a third answer meaning
   something new is wrong; **a fast True is what full recovery looks like** and is the new normal.
5. **[m65 — bounce the foreman ONLY when it has no `--adopt` child.]**
   ```
   powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*adopt*' } | ForEach-Object { '{0} parent={1}' -f $_.ProcessId, $_.ParentProcessId }"
   ```
   **Run #19 DID bounce it** (PID 5420, started 11:22 AM, no adopt child, fandom back) because it
   was the oldest carrier of stale imports in the tree and pre-dated run #15. Foreman is STANDING,
   so the keeper restores it within 300s. **Confirm it came back** and that it is now young.
   Filter on `Name -match 'python'` as well as the command line, or your own shells match.
6. **[m82 — THE MEASUREMENT IS NOW RUNNING. Collect it.]** `feats.py` now counts MediaWiki's own
   `continue` token whenever `aplimit=500` or `srlimit=50` withheld results, and `roll()` prints
   the total. **The first roll to finish under run #19's code answers m82 with a number.** Read
   the tail of `state/roll_auto.log` for `discovery caps BOUND` or `discovery caps bound: never`.
   Zero binds means the caps are theoretical and the Hard Rule 0 question is closed cheaply; a
   non-zero count is the argument for a continuation loop. **Do not re-derive this by hand.**
7. **[ANSWERED — stop re-investigating these.]** The reader's transport **is** Cascade with 8
   workers. The lane **is** arbitrating. The completeness `UNMEASURED HIGH` is **downstream of
   M8**. The `standards.py:550` 700-byte read is **latent with zero current effect** (all 1,275
   readfeats records measured). The `deepinfra/chutes/cerebras/huggingface` DNS failures are now
   **32.8h stale**, not an outage. **New this run:** m83's post-reader pipeline no-op is a **real
   race with zero observed hits** in ~25 recorded cycles — mechanism confirmed, consequence
   refuted, do not spend on it. The keep-warm `gpu_lane` import **cannot realistically fail** on
   this machine (stdlib-only, same directory) — it is a defensive path, now recorded rather than
   restructured.

## 2. Human decisions needed (owner)

A. **[M15 — THE DESIGN RULING, now the only half still open.]** Run #19 applied candidate (i)
   (honest notes) and **only** (i). The loop is unchanged: the pool refuses → the reader completes
   few entities → it prints no progress line → a foreman remedy SIGTERMs it → and because
   `read.py` is outside `STANDING` it waits a lap. Remaining candidates:
   (ii) **Teach the stall remedies to check refusal first** and decline to kill when the pool is
   the cause — the reader is not wedged, it is waiting.
   (iii) **Put `read.py` in `STANDING`.** `overnight.py:344-347` excludes it deliberately, and a
   keeper restarting a non-idempotent hours-long job every 5 minutes could thrash it — **which is
   exactly why this is a question.** (ii) and (iii) interact: with (ii) in place, (iii) is much
   safer. **The honest note now makes the cost of NOT deciding visible in the log**, which is the
   whole point of having applied (i) first.
B. **[THE BIGGEST SINGLE LEVER AVAILABLE, AND IT IS FOUR LINES OF CONFIG. Worse than last run.]**
   Four buckets refuse every call and are retried forever — **92 of 203 refusals in 3h (45%)**,
   all four `last_error` rows aged at **0.0h**, so this is current:
   - `zai:free` — *"Insufficient balance or no resource package. Please recharge."* (52 calls, 0 ok)
   - `cloudflare:free` — `HTTP 401 Authentication error` (20, 0)
   - `hyperbolic:free` — `HTTP 401 Could not validate credentials` (11, 0); its config entry is
     even marked `"unverified": true` with a note to confirm it against `/models`
   - `cohere:free` — trial key, 1000-call ceiling reached (9, 0)
   Nothing benches them: `engine.is_dead()` fires only on 404/410/402/400/422, so a 401 and a
   429-carrying-a-balance-message both survive forever. **Recharge, re-key, or remove them?** The
   config is in the *other* project (`C:\Users\imarl\cascade\config.json`); runs #18 and #19 both
   declined to touch another project's tree.
   **Second, separable question:** should Cascade get a **rolling-failure-rate circuit breaker**
   (N consecutive non-ok outcomes in an hour → bench regardless of status code)? **Note it must
   key on the error, not the rate** — `sambanova:free` is also at 0 ok but is genuinely rate
   limited and would be wrongly benched by a naive rate rule.
C. **[NEW, run #19 — m84: a probe that cannot say "I could not look".]** `overnight.running()`
   returns `False` whenever `_proc_lines()` comes back empty, so **one failed probe reads as
   "every managed job is down"** — and both the liveness standard and the keeper act on it. Seen
   live: the foreman logged **itself** as down while writing that very line, and a second foreman
   existed four minutes later. **This is the same shape as M16 and as the `preflight()` `(0,
   False)` fixed this run** — a value that means both "nothing there" and "I failed". The repair
   is a return-contract change on a function the supervisor, keeper and standards tree all call.
   **Approve the signature change?** (`None` for "could not probe" vs `False` for "not running".)
D. **[NEW, run #19 — m85: the duplicate reaper preserves the stalest code.]**
   `kill_duplicate_jobs` keeps the **oldest** instance. Sound for its stated purpose (the oldest
   holds the work in progress), but a long-lived job never re-reads its imports, so the tie-break
   **systematically discards the freshest code and keeps the stalest.** Run #19 saw exactly that:
   an 11-hour foreman pre-dating run #15 survived while a duplicate carrying every current fix
   did not. **Leave as is, or prefer the newer process when the older one is older than the
   file it runs?** Reversing it unconditionally would kill running work, so this needs a ruling.
E. **[§2 R IS DOWN FROM SIX SITES TO THREE — the ruling is now cheaper than it has ever been.]**
   Carried since run #5: *does Hard Rule 0 bind diagnostics and run logs, or only reader-facing
   listings?* Run #19 answered three of the six with the workable test (**"does anything
   downstream act on the truncated list?"**):
   - `STATUS.md`'s `history[-12:]` — **NO.** Nothing parses STATUS.md; `publish.py` copies it
     byte-for-byte and `estate.py` only hashes it. Human-read only.
   - `FOREMAN.json`'s `prev[-200:]` — **NO.** `overnight.foreman_report()` reads only `rounds[-1]`.
   - the dashboard `findings` cap of 12 — **ALREADY GONE.** The live file carries
     `# ALL open findings -- a monitoring cap ruled a truncation, 2026-08-24` and no `[:12]`.
   **Still open: m25, m16, and `health.reopen_stranded`'s `reopen[:20]`.** Apply the same test to
   each and the question closes.
F. **[M16 — `api()`'s return contract.]** A timeout and a genuine "no such page" are the same
   value (`None`), and both get cached permanently — per-entity and, worse, per-source in
   `WIKI_HOSTS.json` where a `None` is never reconsidered. **This is the same defect as §2 C
   above; they may deserve one ruling.** Fixing it means a typed transport-failure signal and
   updating every caller: a public-signature change needing a review cycle. **Approve?**
   Separately and cheaply: `resolve_hosts()`'s `if src in known: continue` could become a
   truthiness test so a `None` host is retried, fixing the worst half with no signature change.
   **That one may be safe to just do — say so and the next run will.** (Carried unchanged from
   run #18; still nobody's ruling.)
G. **[NEW, run #19 — should the patch lane's allsweep gate take a baseline?]** `_checks_pass` runs
   `allsweep --quick` **after** the patch with no before-picture, so the real test is "no broken
   module at all". One unrelated broken module refuses **every** model patch from then on. Run #19
   corrected the docstring and the refusal message but **deliberately did not loosen the gate** —
   weakening a safety check on model-authored writes to live source is not a maintenance decision.
   **Take a pre-patch baseline and compare, or keep it strict?** (Currently moot: allsweep reports
   0 subsystems bad, so the lane is not blocked today.)
H. **[NEW, run #19 — two more panels with M14's shape.]** A dashboard audit found `_watch()`
   (`OVERWATCH.json`, `failures.json`) and `metrics()` (`model_metrics.jsonl`) both read their
   sources with **no age check at all**, so a dead writer's last numbers render as current
   forever — exactly M14's jobs-panel problem, in two more places. `library()`'s coverage
   sub-panel already computes `age_h` and is the model to copy. **Also:** `metrics()`'s `ok_pct`
   has **no minimum-sample floor**, so one row renders a confident `0%` or `100%`. **Add age
   markers and a sample floor?** (Reported by audit, mechanism read at source by me; the
   staleness claim is structural and I did not observe a stale render.)
I. **[NEW, run #19 — an unlocked read-modify-write on `dashboard_history.json`.]** `movement()`
   reads, appends and writes that file, and only the final rename is atomic. **Two writers exist**:
   `dashboard.py`'s threaded server (per browser tab, every 5s) and `publish.py`'s separate
   process calling `D.state()` on its own loop. Concurrent writers can each drop the other's
   sample silently. **Reported by audit; I verified the two writers exist but did NOT observe a
   lost sample.** Worth a ruling because the file is the evidence base for every `stalled` verdict
   the page makes — and see §Read-this-first 3 for why those verdicts already need care.
J. **[M12 — STILL THE BIGGEST UNREALISED ITEM. Rebuild the manifest?]** Zero feats chapters in an
   88 MB manifest feeding a live `generate.py`; the join is healthy and would now produce
   **1,215 entity blocks across 100 sources**; **55,795 mined feats reach no volume.** Rebuilding
   underneath a running prose job is a decision. `manifest_builder`'s `content_hash` means a
   rebuild marks changed jobs stale rather than redoing everything. **Say whether to rebuild, and
   whether to stop `generate` first.** Untouched by runs #16-#19.
K. **[m80 / m81 — carried, both cheap to state.]** (i) `resolve_title()` has zero callers and its
   docstring says it fixes a 17,148-entry loss. **Wire it in, or retire it?** Same census:
   `_page_exists`, `remine`, `axis_evidence` also unreferenced. (ii) Every line-number
   `silence.note` label in `feats.py` is stale by 8-140 lines (and 5 more in `overnight.py`).
   Re-running `silence.py --instrument` **splits the ledger's cumulative counts off their
   history**, which is why this is a decision. **Run #19 added two new labels in the stable
   descriptive style** (`feats.py:api-404`, `overnight.py:keepwarm-no-gpu-lane`) rather than
   line numbers — that is the migration path if you want it, one site at a time, no mass split.
L. **[M8 — is the fandom IPv4 outage a block we earned, or a network fault?]** It answered
   **instantly** this run (0.0s), so the question is dormant. Forcing IPv6 remains a decision only
   the owner can make; runs #14-#19 have all declined to take it.
M. **[M14's reporting half — how should a jobs panel say "this reader is dead"?]** Unchanged and
   still open. The dashboard's pass-through is deliberate ("the dashboard can never disagree with
   the system it is reporting on") and its cost is that a stopped reader renders as a working one.
   Age the panel off `read_auto.log`'s mtime (cheap, matches how `coverage figures are current`
   already works), or have the reader stamp a heartbeat (truer, more moving parts)? **§2 H would
   share whatever mechanism this gets.**
N. **[carried, run #17 — the dirty room behind M13.]** The stray 26 MB export repo in a dead
   session's scratchpad (160 ahead / 63 behind, pointed at the real remote) — **delete, archive,
   or leave?** And the supervisor's environment still carries `PANSCRIPTUM_EXPORT` pointing at it,
   so every publish start prints a `REFUSING` line — **that line is the fix working.** A
   supervisor restart clears it and bounces every job, so it is the owner's call.
O. **[carried] The stale local buckets** — every reader and pipeline start reprints
   `REMOVED local-<model>: HTTP 404` for `gemma3:12b`, `qwen2.5:14b`, `llama3.1:latest`,
   `qwen3:30b-a3b-...` and the unsloth Q3 GGUF. Confirm the prune was intentional; the roster
   lives outside `src/`. Ollama reports **1 model installed**, consistent with the qwen3:8b ruling.
P. **[carried] Dead code and dead directories.** `FEATS_BLOCK_CHARS` referenced by nothing but its
   own comment; `entity_match.py` a complete module with zero production callers;
   `completeness.py` reporting `probe_failures: 8` alongside `probes_run: 0`; `site/state.json`
   stale with nothing in `src/` referencing `site/` (the live artifact is `docs/state.json`); plus
   **1 cache directory no source points to** (`feats/jojo_fandom_com`). **No deletion without a
   ruling.** **Run #19 note:** `_RATE_LIMITED` was in this family — written since the file was
   created, read by nothing — and was resolved by *printing* it rather than deleting it. That is
   the cheaper half of this question wherever the value is a measurement.
Q. **[carried] Permanently hostless roll entries** — catalogued with no host **16** (was 20); on
   the roll but never catalogued **6**; **1** host for a source with no catalogue record. The
   **91 DECIDED spine codes** are still not written to `CHARTER_SPINE_CODES.json`, which has no
   writer in `src/`. **34 catalogued sources have no charter spine code**; three charter errata
   open (Supercluster, Filament, Hyperverse are rungs with no Magnitude band).
S. **[m79 — NOW DIAGNOSED, run #20. The ruling in §2 E has evidence attached; this is the one to
   close next.]** The reader's rate is no longer absurd in the common case — since the 22:39
   restart it reads a plausible **1.79 chunks/s** and real ETAs (8.5–18.2h), and the page's
   `10525.08 chunks/s` is gone. But the log shows the bug firing in **both** directions, and the
   pattern names the cause. Consecutive lines from `state/read_auto.log`:
   ```
   line 74:  5759.45 chunks/s  eta    0.0h   (0 to GPU)
   line 85:     0.03 chunks/s  eta  977.5h   (1 to GPU)   <- first model call enters the window
   line 86:     3.09 chunks/s  eta    9.5h   (1 to GPU)   <- self-heals within ONE sample
   line 98:     3.43 chunks/s  eta    8.5h   (1 to GPU)
   line 99:     0.02 chunks/s  eta 1320.0h   (4 to GPU)   <- again, exactly at the transition
   ```
   **Both absurd readings land precisely on a change in the `to GPU` count, and recover within a
   single sample.** That is direct confirmation of §2 E's untested hypothesis: the rolling window
   **mixes instant cache hits with real model calls**, so any sample straddling the transition
   gets a garbage `dt` — near-zero elapsed for a cache burst (`eta 0.0h`), near-zero progress when
   the first model call lands (`eta 1320h`). **`chunks_reused` is already computed for exactly
   this distinction and then discarded.** So the fix direction is named: separate cached
   completions from model-answered ones in the rate. **Still `read.py`'s rate contract and still
   the owner's ruling** — but it is no longer a question about which of two branches is wrong, it
   is a question about whether to spend the change.
R. **[carried] The rest, unchanged and untouched this run.** m54's `_BEAT_SECONDS` 300→100s cost;
   M10's 8,194 orphaned cached answers; the `read.py` audit's five open questions (no chunk
   overlap, two disagreeing "own page" tests, `chunks_skipped` wrong for multi-page entities, an
   inert `cap_chunks` comment, `chunks_reused` discarded); m79's rolling-window eviction guard and
   its from-t0 fallback (**the page still shows `10525.08 chunks/s`, which is that fallback, and
   it is a `read.py` bug — dashboard.py only mirrors it faithfully**); the cloud worker floor;
   compounding cache TTLs; the 240-char description truncation; the last 22 oversized chapter
   blocks; `check_context_budget`'s scope; the burst lane's 598/500 (**$11.96 spent**); m58, m57,
   m48, m47, m37, m29, m26, m39, m38, m12, m13, m30, M1, m43.

## 3. Small implementable items (no decision needed)

1. **[WITHDRAWN — DO NOT RE-QUEUE. It was fixed in run #4 and carried for seventeen runs.]** This
   slot said *"`pipeline.py`'s 9 shared cross-phase JSON writes still use raw `open+json.dump`"*
   since run #2, and **run #19 promoted it to "the highest-value item in this section" while
   copying it forward.** It is not true. Every `json.dump` in that file writes to a `.tmp` and
   lands through `_landed` / `land_json` / `silence.replace_retry`; all eleven phase artifacts go
   through `land_json`; `BUGS.md`'s own m6 entry records this being done in run #4, to **eleven**
   artifacts, not nine. **Verified by direct grep of every write site.**
   **The one genuine remainder:** `pipeline.update_handoff` writes `handoff/RUN_STATUS.md` via a
   bare `os.replace` rather than `silence.replace_retry`. Single-writer, machine-only, rewritten
   every unit — **low exposure, one line, do it when convenient.** That is the whole of what was
   left of this item.
2. **34 silent exception handlers** (`python src/silence.py`), unchanged across run #20 (one
   removed, one exemption added). The audit reads the AST, so a `#` comment does NOT satisfy it;
   the idiom is a string (`_ = "silence-exempt: ..."`). Concentration: **`gpu_lane.py` 13**,
   `silence.py` 5, **`context_budget.py` 4** (fallback-to-empty-string when a prompt file cannot
   be read — generating against an EMPTY system prompt rather than failing), `foreman.py` ×2,
   `health.py` ×2, `local_agent.py` ×2, `standards.py` ×2, plus `coverage.py`, `entity_match.py`,
   `publish.py:227`. **`foreman.py` uses the exemption idiom nowhere at all** — its two silent
   handlers (in `restart_ollama`) are plausibly benign first-state cases and are the cheapest
   place to start. **`context_budget.py`'s four are the ones with teeth** and nobody has read that
   file since run #12: generating against an empty system prompt is a silent quality collapse.
3. **`_HAS_ACTION`'s verb list may have recall gaps** (still unverified): "vaporiz-", "annihilat-",
   "incinerat-", "smash", "explod-", "shred", "stun", "wound" absent. Honestly accounted in
   `chunks_skipped`, so not hidden — but run #18 saw `dropped 5,304` against `chunks 4,537`, **more
   skipped than read**. That ratio still deserves an actual measurement.
4. **`JOB_OVERHEAD_CHARS`'s comment cannot be re-measured** while the live manifest has no feats
   jobs (M12). Fix the comment only after M12 is resolved.
5. **DONE, do not redo.** *Run #20:* the entrypass two-gate collapse (`pipeline.entry_settled`),
   the foreman replay timestamps and its `did[:5]`, three `foreman.py` unchecked
   `replace_retry` returns, `dashboard.jobs()` fault isolation, `dashboard.py:362`'s stale label,
   `pipeline.py`'s unmarked silent handler, the hourly-cadence correction, and §20c/§20d's 17
   checks. *Run #19:* the honest kill horizon, the reader match tightening,
   `triage_swallowed`'s third exit, `FOR_OWNER.md`'s atomic write, the patch-gate docstring,
   `gpu_lane._alive` and its two writers, `feats.py`'s 404 bucket / `errored` counter / whole
   stored sentence / `_CAP_BOUND` measurement, `overnight.py`'s three honest failure reports, and
   §20b's 16 checks. Earlier: §20a and the standards order text (#18); M13, m78, §19aj (#17);
   M11, m75-m77, §3.3 (#16); M9, M10, m54, m55, m62, m70-m74, the regime rate-gate (#15b);
   m66-m69 (#15); m63, m65 (#14); m64; M8's *standard*; m61; the M7 gate fix.

## 4. Surface rotation for the next audit fan-out

**Run #19 ran two first-ever end-to-end audits (`foreman.py`, `dashboard.py`) plus one
verification pass over four unverified `overnight.py` claims. All three paid, and the
verification pass paid most** — it **refuted the consequence** of m83 (a real race with zero hits
in ~25 cycles) and **refuted the reachability** of the keep-warm import bug, while confirming two
others. That is the pattern to keep: *send an agent to adjudicate old claims, not only to find new
ones.* The dashboard agent was usefully wrong once — it called the coverage-stall artifact routine
and current, and one `getmtime` call showed it was neither today. **Correct the detail, keep the
finding.**

Covered, do **not** re-read unless the diff touched them: the round-1 full-codebase audit and
evening sweep (`handoff/AUDIT_*.md`); run #2's four surfaces; run #3's two; run #5's three; run
#6's four; run #7's five; run #9's `feats_index.py` and `hostcheck`; run #10's
`manifest_builder.pack_feats` + `generate.py`'s feats branch; run #11's `system_style.txt` and
`pipeline.py`'s `ask`/`ask_pool_first`/`phase_entrypass`; run #12's `gpu_lane.py` and
`context_budget.py`; run #13's `read.py` transport ladder; run #15's `tuning.py`; run #15b's
`read.py` chunking/caching/queue paths; run #16's `entity_match.py` and `gpu_lane.py` re-read;
run #17's `read.py` progress/ETA reporting; run #18's `feats.py`, `overnight.py`, `standards.py`
and the Cascade error path; **run #19's `foreman.py` and `dashboard.py`**.

**Run #20 audited `pipeline.py` end to end** — the largest module in the tree and the owner of
`write_record`. It found the Major above, confirmed both halves of the two-writer contract are
honoured with no bypass, and **refuted its own brief**: §3.1's "nine raw writes" do not exist.
That refutation is the single most useful thing the run produced, and it argues for pointing the
next agent at a *claim* as often as at a file.

**Not yet audited line-by-line** — pick from here: **`context_budget.py`** is now the highest-yield
item. It holds four of the 34 silent handlers and they are the worst four in the tree — a prompt
file that cannot be read falls back to an **empty string**, so the library generates against an
EMPTY system prompt rather than failing, which is a silent quality collapse with no marker
anywhere. Nobody has read it since run #12 and it was not read for that. After it:
`address_space.py`, `profile.py`, `burgs.py`, `tells.py`, `style_audit.py`, `audit.py`,
`descending_ladder.py`, `cosmography.py`, `genre.py`, `reference.py`, `resync_roll.py`,
`retry_synthesis.py`, `build_terminal.py`, `sweep.py`, `runguard.py`, `compress_store.py`.
**`read.py` deserves a targeted re-read** for m79's rate fallback — now with the measurement in
§2 S attached, so the agent can be pointed at a diagnosed mechanism rather than a symptom.

**Two overwatch HIGHs were refuted at source by run #14** — `cosmography._fmt` and
`descending_ladder.compton_confinement_energy`. **Do not spend on them again.**

## 5. Lessons worth keeping

- **A prediction written into the ledger is the cheapest experiment there is.** Run #18 wrote
  "if the log shows another rc=15 shortly after 21:40, that is the loop confirmed". It did.
  Nothing had to be re-argued. **Write the falsifiable prediction down.**
- **A false statement in a log is a bug, and it is the most expensive kind, because it is the
  one a human reads.** "Supervisor restarts next cycle" was six words that hid 42 minutes of
  downtime per occurrence for an unknown number of months.
- **Derive, do not assert.** The fix for those six words was not better words — it was computing
  the answer from `overnight.STANDING` so it cannot drift. The same file already records what
  happens when a roster is copied by hand: a nine-job tree reporting as four.
- **When a file documents fixing a bug class, grep for the other instances immediately.**
  `kill_stalled_job`'s docstring describes fixing exactly the loose-match bug that was still
  sitting twenty lines above it in `restart_reader`. Both `gpu_lane` writers had the same shape
  as `_remove_retry`'s documented hazard. **A recorded lesson is a search query.**
- **When a function has several exits, check that they all tell the truth.** `triage_swallowed`
  had three false-success paths; two were fixed the day the bug was found and the third survived
  because nobody counted the exits.
- **A 0% success rate is a symptom, not a diagnosis.** `sambanova:free` looked exactly like the
  four dead keys until the error text was read. One string separated "recharge this account"
  from "wait a minute".
- **Prefer a measurement to a verdict, and prefer printing a measurement you already have to
  arguing about one you do not.** m82 became a counter, and `_RATE_LIMITED` — incremented for
  months and read by nothing — became a printed line in the same edit.
- **A regression check that scans source can match its own explanation.** One written in run #19
  failed on its first run because the comment beneath it quoted the pattern it had removed. It
  now strips comment tails, and the failure is kept in the file as the reason why.
- **A QUEUE ITEM NEVER RE-VERIFIED AGAINST SOURCE OUTLIVES THE BUG IT DESCRIBES, AND GAINS
  AUTHORITY WITH EVERY RUN THAT COPIES IT FORWARD.** §3.1's "nine raw writes" was fixed in run #4
  and carried until run #20 — and run #19 promoted it to "the highest-value item in this section"
  in the act of copying it. Nobody lied; nobody looked. **Before working a carried item, spend the
  one grep that proves it is still true.** The same applies to anything this file asserts.
- **Point an agent at a CLAIM, not only at a file.** Run #20's most valuable result was an audit
  refuting its own brief, and run #19's was a verification pass that killed the consequence of
  m83. Adjudicating old findings has now out-earned fresh hunting two runs running.
- **When a rule is written twice, the bug is the duplication, not the clause.** The entrypass
  gates disagreed because the same sentence lived in two places and one got fixed. The repair
  that matters is collapsing it to one predicate — patching the second copy would have left the
  next divergence free to happen.
- **Read the timestamp's PROVENANCE, not just its value.** A replayed log line carries the
  replayer's clock. 38 minutes of apparent evidence about what killed the reader was an artifact
  of who printed the line, and it nearly became a bug report about PID reuse.
