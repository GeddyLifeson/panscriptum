# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #18 wrote this on 2026-08-24 ~21:50 local.*

**Read this first.** Four things shape what is worth doing next run:

1. **THE SCHEDULE IS EVERY 15 MINUTES (`11,26,41,56 * * * *`), so you will routinely land on a
   live predecessor and that is the designed steady state.** The guard exits in seconds. It does
   **NOT** see interactive sessions — before writing anything, check
   `git -C C:\Users\imarl\panscriptum-export log --oneline -5` and `ls -lt src/*.py | head`.
2. **RUN #18 REVERSED TWO STANDING INSTRUCTIONS. Do not re-apply them from memory.**
   (i) *"Do not chase rc=15, it is the reader's ordinary exit"* — **false.** `rc=15` is
   `TerminateProcess(handle, SIGTERM)`; the reader is being **killed by the foreman**. Proven by
   experiment and pinned by `verify_math` §20a. See **M15**.
   (ii) *"The pool red is refusal, and the lever is providers"* — **half false.** 38% of the
   refusals are four accounts that are out of credit or holding dead keys. **The lever is four
   config entries, not more providers.** See §2 A.
3. **THE PAGE'S OPENING DIAGNOSTIC IS SOUND AND ITS GUIDANCE IS NOW LESS WRONG.** The
   `model calls per hour` order text no longer ends "the reader is not asking" — it names
   refusal as the co-equal candidate and gives the SQL. **The dashboard AND the publish loop
   were both bounced to adopt it, and the publisher is the one that counts:**
   `publish.py:171-172` imports `standards` and calls `ST.check(s)` itself to build
   `docs/state.json`, so **the page's text comes from the publisher's module cache** — bouncing
   the dashboard alone would have changed nothing the public can see. **Remember this the next
   time you edit `standards.py`.** The **foreman still carries the OLD text** (it must not be
   bounced while it has an `--adopt` child), so `FOR_OWNER.md` will quote the old wording until
   the foreman restarts on its own.
4. **`bucket_state.last_error` HAS NO HISTORY — AGE EVERY ROW BEFORE BELIEVING IT.** Run #18
   nearly reported a live 4-provider DNS outage that turned out to be 31.9 hours stale.
   `select bucket,last_error,updated_at from bucket_state` and subtract.

## 1. Verify first

1. **[M15 — DID THE READER GET KILLED AGAIN? This is now the one to check first, every run.]**
   ```
   grep -nE "kill_stalled_job|restart_reader|read: (finished|starting)" state/overnight.log | tail -12
   ```
   Each `read: finished rc=15` is a **kill**, and the gap to the next `read: starting` is the
   downtime it cost. Run #18 measured **42.0 min** (killed 20:35:04, noticed 20:35:58, restarted
   21:17:58). **Record the new gap** — the series so far is 1m, 8m, 32m, 37m, 42m, 4h. If a run
   ever sees a gap under ~5 min, the reader was restarted by something other than the main lap
   and that is itself news.
2. **[§2 A — ARE THE FOUR DEAD BUCKETS STILL IN ROTATION? One query, highest value on the page.]**
   ```
   python -c "import sqlite3,time;c=sqlite3.connect('file:state/cascade_scratch.db?mode=ro',uri=True);t=time.time()-10800;print(list(c.execute('select bucket,outcome,count(*) from usage where ts>? group by bucket,outcome order by 3 desc',(t,))))"
   ```
   Expect `zai:free` and `cohere:free` still topping `rate_limited`, `cloudflare:free` and
   `hyperbolic:free` still topping `error`. **If those four are gone, the owner acted and the
   pool's whole picture changed — re-measure before reasoning from anything below.**
3. **[preflight — the baseline is now 1 FAIL, not 2. A SECOND is the finding.]** Run #18 got one:
   `caches empty ... feats/www_dandwiki_com` (**M1**). `API paths per host family` (**M8**)
   **passed** because fandom answered IPv4. If M8's line returns, fandom went away again — check
   §1.4 before theorising.
4. **[M8 — is fandom still back? Four seconds, TCP only.]**
   ```
   python -c "import sys,time;sys.path.insert(0,'src');import standards as ST;t=time.time();print(ST.fandom_ipv4_reachable(), '%.1fs'%(time.time()-t))"
   ```
   Run #18 got `(True, '172.66.2.166')` in **8.0s** — reachable but slow. **Read the latency:** a
   slow `False` is a block; a fast `False` (<1s) is a third answer meaning something new is
   wrong; a *slow True* is what recovery looked like this run.
5. **[m65 — bounce the foreman ONLY when fandom is back AND it has no child.]**
   ```
   powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*adopt*' } | ForEach-Object { '{0} parent={1}' -f $_.ProcessId, $_.ParentProcessId }"
   ```
   A child under the foreman's PID means **DO NOT BOUNCE**. Run #18 saw `hostcheck.py --adopt`
   (PID 47096) under foreman PID 5420 and left it alone. The foreman is still running
   pre-run-#15 code (started 11:22, now 10h+ old) and is the **oldest carrier of stale imports
   in the tree** — it will not pick up the corrected standards text until it restarts.
6. **[m79 — the ETA finally moved off zero, twice. Is it a trend?]**
   ```
   grep -o "eta [0-9.]*h" state/read_auto.log | sort | uniq -c
   ```
   Run #18: **119 × `0.0h` and 2 × `0.1h`** — the first non-zero ETAs the log has carried. Weak
   evidence for the eviction-guard mechanism in §2 E. A fresh log all-zero again strengthens it.
7. **[ANSWERED — stop re-investigating these.]** The reader's transport **is** Cascade with 8
   workers. The lane **is** arbitrating. The completeness `UNMEASURED HIGH` is **downstream of
   M8**, correct behaviour. **New this run:** the `standards.py:550` 700-byte read is a **latent**
   hazard with **zero** current effect — all **1,275** readfeats records carry
   `chunks_unanswered` inside the first 700 bytes, measured. **Do not re-measure it; re-measure
   only if the record shape changes.** And the `deepinfra/chutes/cerebras/huggingface` DNS
   failures are **31.9h stale**, not a live outage.

## 2. Human decisions needed (owner)

A. **[NEW, run #18 — THE BIGGEST SINGLE LEVER AVAILABLE, AND IT IS FOUR LINES OF CONFIG.]** Four
   buckets refuse every call and are retried forever, together **83 of 218 refusals in 3h (38%)**:
   - `zai:free` — *"Insufficient balance or no resource package. Please recharge."* (46 refusals)
   - `cohere:free` — trial key, 1000-call ceiling reached (9)
   - `cloudflare:free` — `HTTP 401 Authentication error` (18 errors)
   - `hyperbolic:free` — `HTTP 401 Could not validate credentials` (10 errors); its config entry
     is even marked `"unverified": true` with a note to confirm it against `/models`
   Nothing benches them: `engine.is_dead()` fires only on 404/410/402/400/422, so a 401 and a
   429-carrying-a-balance-message both survive forever. **Recharge, re-key, or remove them?**
   The config is in the *other* project (`C:\Users\imarl\cascade\config.json`) — run #18
   deliberately did not touch another project's tree.
   **Second, separable question:** should Cascade get a **rolling-failure-rate circuit breaker**
   (N consecutive non-ok outcomes in an hour → bench regardless of status code), so a dead key
   cannot cost 38% of the pool's attempts for days? That is a design change in that project.
B. **[M15 — THE REAL M14 DECISION, now with the cause attached. Three candidate fixes.]** The
   foreman kills the reader for looking stalled when the **pool** is what stalled, and the kill
   costs a full lap because `read.py` is outside `STANDING`. Candidates, in rising order of
   invasiveness:
   (i) **Make the kill notes honest** — `restart_reader` and `kill_stalled_job` both say
   "supervisor restarts next cycle", true for a STANDING job (300s) and badly false for the
   reader (a lap). Cheapest, changes no behaviour, and would have exposed this years earlier.
   (ii) **Teach the stall remedies to check refusal first** and decline to kill when the pool is
   the cause — the reader is not wedged, it is waiting.
   (iii) **Put `read.py` in `STANDING`.** `overnight.py:344-347` excludes it deliberately, and a
   keeper that restarts a non-idempotent hours-long job every 5 minutes could thrash it — **which
   is exactly why this is a question.** Note (ii) and (iii) interact: with (ii) in place, (iii)
   becomes much safer.
   **Also open:** a subagent traced the *code* ceiling on the restart gap at **~7h10m**
   (join(roll) 4h + pipeline 2h + coverage 0.5h + sleep + next preflight 0.5h) — **wider than the
   4h worst case ever observed**. I did not verify this beyond the quoted timeouts. Confirm it.
C. **[NEW, run #18 — should the standards tree be able to see refusal at all?]** §2 C from run
   #17, now with the arithmetic named. The three sub-standards read `worst` (quota headroom) and
   `cap` (shape) — `buckets with headroom` keys on `worst > 0.05`, `buckets not exhausted` on
   `worst <= 0.001`, `no bucket pinned at rpm 1` on `cap == 1`. **A bucket 429ing every call while
   holding a full daily allowance clears all three.** The order text now SAYS so (run #18's fix),
   but saying it is not measuring it. Candidates: a fifth pool standard on refusal share, or
   widening the window `calls that succeed` judges over. **The 20-call minimum is deliberate**
   (`standards.py:58-60` cites `tuning.MIN_CALLS_TO_JUDGE`); **the 15-minute window is not** —
   `tp.get("window_min", 15)` is a bare default with no comment defending it. Neither is a repair
   to make unasked.
D. **[NEW, run #18 — M16: `api()`'s return contract.]** A timeout and a genuine "no such page"
   are the same value (`None`), and both get cached permanently — per-entity and, worse,
   per-source in `WIKI_HOSTS.json` where a `None` is never reconsidered. Fixing it means giving
   `api()` a typed transport-failure signal and updating **every** caller: a public-signature
   change needing a review cycle. **Approve the signature change?** Separately and cheaply:
   `resolve_hosts()`'s `if src in known: continue` could become a truthiness test so a `None`
   host is retried, which fixes the worst half without touching any signature. **That one may be
   safe to just do — say so and the next run will.**
E. **[m79's fix still needs a ruling on both branches.]** The rolling window's eviction guard
   never trims below two samples, so a stall plus two cache-hit completions gives a millisecond
   `dt`. The **fallback** branch, `crate = done["chunks"] / max(el, 1e-9)`, is the from-t0
   average the rolling window was introduced to replace. **Which rate should the page show while
   the queue works through cached entities?** Related: `chunks_reused` is computed and thrown
   away, so the rate mixes instant cache hits with real model calls either way.
F. **[m80 / m81 — two decisions the audit surfaced, both cheap to state.]**
   (i) **`resolve_title()` has zero callers and its docstring says it fixes a 17,148-entry loss.**
   Wire it in, or retire it? Per the project's own lesson, a function that exists and is never
   called is worse than one that is missing. Same census: `_page_exists`, `remine`,
   `axis_evidence` also unreferenced.
   (ii) **Every line-number `silence.note` label in `feats.py` is stale by 8–140 lines** (and 5
   more in `overnight.py`). Re-running `silence.py --instrument` **splits the ledger's cumulative
   counts off their history** (the 476 stays under the old key), which is why this is a decision.
   Alternative: move those five sites to stable descriptive tags like the file's other three
   (`feats.py:corrupt-cache`), accepting the same split once, deliberately.
G. **[M12 — STILL THE BIGGEST UNREALISED ITEM. Rebuild the manifest?]** Zero feats chapters in an
   88 MB manifest feeding a live `generate.py`; the join is healthy and would now produce
   **1,215 entity blocks across 100 sources**; **55,795 mined feats reach no volume.** Rebuilding
   underneath a running prose job is a decision. `manifest_builder`'s `content_hash` means a
   rebuild marks changed jobs stale rather than redoing everything. **Say whether to rebuild, and
   whether to stop `generate` first.** Untouched by runs #16, #17, #18.
H. **[M8 — is the fandom IPv4 outage a block we earned, or a network fault?]** It **answered this
   run** (slow True, 8.0s), so the question is dormant but not closed. Forcing IPv6 remains a
   decision only the owner can make; runs #14–#18 have all declined to take it.
I. **[NEW, run #18 — `catalogue_models.py:135-137` skips a provider whose own model-list probe
   fails.]** `data/PROVIDER_MODELS.json` is dated **2026-08-22 17:42** (2 days stale) and records
   probe failures for **cloudflare (405)** and **hyperbolic (401)** — the two dead-key buckets.
   Because the probe failed, they are **skipped, not marked stale**, so `model IDs their
   providers still serve` reports **zero** while two of its subjects were never checked. **Should
   an unverifiable provider count as its own breach**, rather than passing through as no finding?
   Also: that snapshot has no freshness check, unlike the sweep/publish ages in the same file.
J. **[NEW, run #18 — a config entry that names two different models.]**
   `cascade/config.json`'s `groq-llama31-8b` has `"model": "groq/compound-mini"`, so the bucket
   key derives to `groq:groq/compound-mini` while `usage.model_id` records `groq-llama31-8b`.
   Every row for that bucket is self-contradictory. It reads as a half-finished edit after Groq
   retired the original model. **Rename the id/label, or set an explicit `bucket` key?** (Other
   project's file.) Note this bucket is **intermittent, not dead** — it answered `ok` mid-run.
K. **[m82 — Hard Rule 0 question with a real number attached.]** `feats.py:327,334` use
   `aplimit=500` / `srlimit=50` with **no continuation handling anywhere in the file**, and both
   feed the title list that gets fetched. **Nothing measures how often the cap binds** — that
   measurement is the first step and needs no ruling. Then: continuation loop, or an explicit log
   when a result set is capped?
L. **[m83 / overnight.py's other findings — audit-reported, not yet verified at source by me.]**
   The post-reader pipeline pass can silently no-op (`overnight.py:579` vs `607`); `preflight()`'s
   handler returns `(0, False)` — indistinguishable from "checked, clean" (`overnight.py:400-402`);
   a failed `gpu_lane` import permanently disables keep-warm's busy-check, making it the
   competitor its docstring says it must never become (`overnight.py:498-506`);
   `coverage_snapshot()`'s captured `"error"` key is never logged, so a snapshot crash writes a
   **zeroed coverage row into STATUS.md** (`overnight.py:613-618`). **Verify each at source before
   fixing** — that is the rule that has caught agent errors in both directions.
M. **[M14's reporting half — how should a jobs panel say "this reader is dead"?]** Unchanged and
   still open, but now separable from M15: the dashboard's pass-through is deliberate ("the
   dashboard can never disagree with the system it is reporting on") and its cost is that a
   stopped reader renders as a working one. Age the panel off `read_auto.log`'s mtime (cheap,
   matches how `coverage figures are current` already works), or have the reader stamp a
   heartbeat (truer, more moving parts)?
N. **[carried, run #17 — the dirty room behind M13.]** The stray 26 MB export repo in a dead
   session's scratchpad (160 ahead / 63 behind, pointed at the real remote) — **delete, archive,
   or leave?** And the supervisor's environment still carries `PANSCRIPTUM_EXPORT` pointing at it,
   so every publish start prints a `REFUSING` line — **that line is the fix working.** A
   supervisor restart clears it and bounces every job, so it is the owner's call.
O. **[carried] The stale local buckets — still the noisiest thing in the logs.** Every reader and
   pipeline start reprints `REMOVED local-<model>: HTTP 404` for `gemma3:12b`, `qwen2.5:14b`,
   `llama3.1:latest`, `qwen3:30b-a3b-...` and the unsloth Q3 GGUF, several times each. Confirm
   the prune was intentional; the roster lives outside `src/`.
P. **[carried] `FEATS_BLOCK_CHARS`** referenced by nothing but its own comment — delete or keep as
   the measurement of record? **`entity_match.py`** is a complete module with zero production
   callers — wire in or retire? **`completeness.py`** reports `probe_failures: 8` alongside
   `probes_run: 0` — rename, zero it, or leave? **`site/state.json`** is stale and nothing in
   `src/` references `site/` (the live artifact is `docs/state.json`) — dead directory? Plus **2
   cache directories no source points to**. **No deletion without a ruling.**
Q. **[carried] Permanently hostless roll entries** — catalogued with no host **20**; on the roll
   but never catalogued **6**; **1** host for a source with no catalogue record. The **91 DECIDED
   spine codes** are still not written to `CHARTER_SPINE_CODES.json`, which has no writer in
   `src/`. **34 catalogued sources have no charter spine code**; three charter errata open.
R. **[m25 / m16 / dashboard `findings` cap of 12 / `health.reopen_stranded`'s `reopen[:20]` /
   `overnight.py:428`'s `history[-12:]` in STATUS.md] — ONE ruling, now SIX sites: does Hard Rule
   0 bind diagnostics and run logs, or only reader-facing listings?** Carried since run #5. Run
   #18 added the sixth, and it is the sharpest yet: STATUS.md is the file the docstring calls the
   answer to "the morning question", and it shows only the last 12 cycles however long the run.
   **"Does anything downstream act on the truncated list?" is the workable test.**
S. **[carried] The rest, unchanged and untouched this run.** m54's `_BEAT_SECONDS` 300→100s cost;
   M10's 8,194 orphaned cached answers; the `read.py` audit's five open questions (no chunk
   overlap, two disagreeing "own page" tests, `chunks_skipped` wrong for multi-page entities, an
   inert `cap_chunks` comment, `chunks_reused` discarded); the cloud worker floor; compounding
   cache TTLs; the 240-char description truncation; the last 22 oversized chapter blocks;
   `check_context_budget`'s scope; the burst lane's 598/500 (**$11.96 spent**); m58, m57, m48,
   m47, m37, m29, m26, m39, m38, m12, m13, m30, M1, m43.

## 3. Small implementable items (no decision needed)

1. **`pipeline.py`'s 9 shared cross-phase JSON writes** still use raw `open+json.dump` rather than
   `_landed`/`replace_retry`. Open since run #2, **the last member of its family**.
   `health.reopen_stranded` was fixed to use `replace_retry` and run #17 exercised it live against
   a running pipeline — a working model to copy.
2. **`gpu_lane._write_claim` and `_touch` use a bare `os.replace`**, not `silence.replace_retry`.
   `_remove_retry` in that same file cites the Windows rename-denied race (m55) as its own
   justification, so the module already knows the hazard and two of its writers do not use the
   remedy. **A new foreground claim's FIRST write has no beat margin to absorb a miss.**
3. **35 silent exception handlers** (`python src/silence.py`). Run #18 added **net zero**. The
   audit reads the AST, so a `#` comment does NOT satisfy it; the idiom is a string
   (`_ = "silence-exempt: ..."`). Concentration: **`gpu_lane.py` 13**, **`context_budget.py` 4**
   (fallback-to-empty-string when a prompt file cannot be read — generating against an EMPTY
   system prompt rather than failing). Also `standards.py` ×2, `entity_match.py:272`,
   `overnight.py:500`, `pipeline.py:1570`, `foreman.py` ×2, `health.py` ×2, `coverage.py:92`,
   `publish.py:227`, `local_agent.py` ×2.
4. **`gpu_lane._alive` contradicts its own documented policy** — docstring says unknown answers are
   treated as ALIVE deliberately; an unparseable `pid` returns `False`. **Verified.** Only
   reachable via external corruption, but it is a direct comment-versus-code mismatch of the class
   that has produced this project's last four majors.
5. **`feats.py:137` logs the HTTPError note BEFORE checking `e.code`**, so an expected 404 — which
   the code two lines below calls *"a real miss"* not worth retrying — lands in the same ledger
   bucket as a genuine 500. Cheap, self-contained, no signature change. **Probably just do it.**
6. **`feats.py:835-837`'s `work()` swallows entity-level exceptions into no bucket at all**:
   `done["n"]` increments but every other counter is skipped, so a systemic `evidence_for` bug
   would depress the roll's rate with **zero** visible signal. Add an `errored` counter distinct
   from `empty`. Self-contained.
7. **`feats.py:578`'s `s[:220]`** truncates the stored quantity sentence that `magnitude.py:249`
   uses as the permanent **instrument-tier citation** — scoring is unaffected (it uses the
   untruncated `value`/`unit`), but the stored evidence text can be cut mid-sentence. Store the
   full sentence; truncate only the display copy.
8. **`JOB_OVERHEAD_CHARS`'s comment cannot be re-measured** while the live manifest has no feats
   jobs (M12). Fix the comment only after M12 is resolved.
9. **`_HAS_ACTION`'s verb list may have recall gaps** (still unverified): "vaporiz-", "annihilat-",
   "incinerat-", "smash", "explod-", "shred", "stun", "wound" absent. Honestly accounted in
   `chunks_skipped`, so not hidden — but run #18 saw `dropped 5,304` against `chunks 4,537`,
   **more skipped than read**. That ratio deserves an actual measurement.
10. **DONE, do not redo:** §20a's rc=15 pinning and the `standards.py` order-text correction (run
    #18); M13, m78, §19aj (run #17); M11, m75, m76, m77, §3.3 (run #16); M9, M10, m54, m55, m62,
    m70–m74, the regime rate-gate (run #15b); m66–m69 (run #15); m63, m65 (run #14); m64; M8's
    *standard*; m61; the M7 gate fix.

## 4. Surface rotation for the next audit fan-out

**Run #18 ran four subagents — `feats.py`, `overnight.py`, `standards.py` (re-read), and a
cross-project trace of the pool's error path — and all four paid.** The pool agent was the most
valuable and also the one that needed correcting: it reported three buckets at "100% error", but
`groq:groq/compound-mini` had answered `ok` 279 seconds before I checked. **Its diagnosis of the
other two (401s, dead keys) was exactly right and is now §2 A, the run's biggest finding.** The
`standards.py` agent's 700-byte hazard was real in principle and **zero in practice** — measuring
it took one command and closed it. **Both outcomes argue the same thing: verify at source, and
prefer a measurement to a verdict.**

Covered, do **not** re-read unless the diff touched them: the round-1 full-codebase audit and
evening sweep (`handoff/AUDIT_*.md`); run #2's four surfaces; run #3's two; run #5's three; run
#6's four; run #7's five; run #9's `feats_index.py` and `hostcheck`; run #10's
`manifest_builder.pack_feats` + `generate.py`'s feats branch; run #11's `system_style.txt` and
`pipeline.py`'s `ask`/`ask_pool_first`/`phase_entrypass`; run #12's `gpu_lane.py` and
`context_budget.py`; run #13's `read.py` transport ladder; run #15's `tuning.py`; run #15b's
`read.py` chunking/caching/queue paths; run #16's `entity_match.py` and `gpu_lane.py` re-read;
run #17's `read.py` progress/ETA reporting; **run #18's `feats.py`, `overnight.py`,
`standards.py` and the Cascade error path**.

**Not yet audited line-by-line** — pick from here: **`foreman.py`** is now the highest-yield item
by some distance — it is the thing that **kills the reader** (M15), it holds three separate
`os.kill` sites, it is the oldest running process in the tree (10h+, pre-run-#15 code), and no run
has ever read it end to end. After that: `address_space.py`, `profile.py`, `burgs.py`, `tells.py`,
`style_audit.py`, `audit.py`, `descending_ladder.py`, `cosmography.py`, `genre.py`, `reference.py`,
`resync_roll.py`, `retry_synthesis.py`, `build_terminal.py`, `sweep.py`, `runguard.py`,
`compress_store.py`. **`dashboard.py` is worth a first read** — it computes the page everything
starts from, and M14's reporting half lives in it.

**Two overwatch HIGHs were refuted at source by run #14** — `cosmography._fmt` and
`descending_ladder.compton_confinement_energy`. **Do not spend on them again.**

## 5. Lessons worth keeping

- **An invariant across wildly different conditions is evidence the number is not measuring
  those conditions.** Six reader exits, durations from 6 minutes to 8 hours, every one `rc=15`.
  Three runs read that as "so it is the ordinary exit". It is the opposite: the code could not
  vary with runtime because it was never the reader's code to give. **When a value refuses to
  move, ask what it is actually a function of.**
- **A one-command experiment beats a plausible reading.** Spawning a child and SIGTERMing it
  settled in two seconds a question that three runs had reasoned about and got backwards.
- **Age every row in a table that keeps only the latest value.** `bucket_state.last_error` made a
  32-hour-old DNS failure look like a live 4-provider outage. The timestamp was right there.
- **A subagent that is wrong about one item can still be right about the finding that matters.**
  The pool agent's "100% error" was wrong for one of three buckets and its 401 diagnosis was the
  most valuable thing found this run. **Correct the detail; keep the finding.**
- **Measure the hazard before ranking it.** The 700-byte read could misclassify records into a
  delete-them remedy. One loop over 1,275 files said: zero, today. That is a better answer than
  either "it's fine" or "it's a bug", and it cost one command.
- **A floor is an opinion; guidance is a factual claim.** That is the line run #18 used to decide
  it could correct the order text without touching the threshold — and it is the line to hold
  when the next run is tempted to "fix" a standard by moving its number.
- **Kill by PID, not by pattern.** A filter matching `*publish.py*` once matched the shell whose
  command line contained that text.
