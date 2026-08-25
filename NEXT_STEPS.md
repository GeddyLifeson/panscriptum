# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #22 wrote this on 2026-08-25 ~01:50 local.*

**Read this first.** Five things shape what is worth doing next run:

1. **VERIFY THE CADENCE WITH `list_scheduled_tasks`. NEVER FROM A FILE, INCLUDING THIS ONE.**
   Run #22 read it back and it is **hourly, `11 * * * *` + 523s jitter, firing ~:19–:20**, with
   `lastRunAt` 06:19:54Z confirming. That matches MAINTENANCE.md — **the first run in a while
   where it did.** It has still been wrong twice in opposite directions, always because nobody
   read the cron back. It is one call. The **15 minutes in the overlap guard is the
   heartbeat-staleness threshold** — a different number answering a different question. Do not
   "fix" it to match the schedule. The guard does **NOT** see interactive sessions: before
   writing anything, check `git -C C:\Users\imarl\panscriptum-export log --oneline -5` and
   `ls -lt src/*.py | head`.
2. **A SHARED LOG IS NOT A LIVENESS SIGNAL, AND RUN #22 NEARLY FILED A GOOD STANDARD AS A BUG.**
   `every running job is advancing` watches `state/pipeline_auto.log` (the supervisor's stdout
   capture) while `pipeline.py:61` writes its run log to `state/pipeline.log`. The second was
   fresh while the first was stale, which looked exactly like run #21's "measurement taken from
   inside the thing measured" lesson — **and it was wrong.** `pipeline.log` is written by *any*
   process importing `pipeline.py`, so its freshness proves nothing; the job's own
   `PIPELINE_STATE.json` was **54.6 minutes** cold and the job really was stalled.
   **The generalisation, and it is the reusable part: before believing a freshness signal, ask
   who else can write that file.** Named candidates, unchecked: anything keyed on
   `state/pipeline.log`, `state/overnight.log`, or a `*_auto.log` stem.
   Run #21's separate question — *what else measures a system it is running inside?* — is still
   open and still unchecked for `dashboard.movement()`, `standards`' own age floors, and
   `allsweep`'s reconcile tier.
3. **THE PAGE OPENS THE RUN. CHECK ITS FRESHNESS AND ITS SELF-CONSISTENCY, NOT JUST ITS REDS.**
   Run #22's page was fresh (0.6 min) and **its green lines were the misleading ones**: all four
   pool sub-standards held while the pool was collapsing, and `the local model produces tokens`
   read *"probe completed in 0.8s"* six minutes before four consecutive generates timed out.
   When the top-level number is red and every cause beneath it is green, **the cause is the one
   the sub-standards cannot see** — for the pool that is call disposition, and the order says so.
4. **AGE `data/COVERAGE.json` BEFORE BELIEVING ANY COVERAGE STALL. IT BIT AGAIN, AND WAS AGAIN AN
   ARTIFACT.** `dashboard.py:338` flags `stalled` over a **30-minute** window while
   `allsweep.py:203-207` treats the file as fresh for **2 hours**, so a file not rewritten inside
   the window *cannot* produce a delta.
   ```
   python -c "import os,time;print('%.2fh'%((time.time()-os.path.getmtime('data/COVERAGE.json'))/3600))"
   ```
   Under 0.5h → the stall is real. Over 0.5h → artifact. **Run #22 measured 0.87h, so its flat
   `cited`/`settled`/`feats` were an artifact and correctly ignored** (as run #21's were at
   0.90h). `chunks` and `entities read` do **not** share this hazard — different sources.
5. **AGE EVERY `bucket_state.last_error` ROW AND READ THE ERROR TEXT, NOT JUST THE OK RATE.**
   This is what found run #22's headline. A 0% bucket is a symptom; the error string is the
   diagnosis, and **the age is what separates a live refusal from a fossil** — the four
   `Could not resolve host` rows (deepinfra, huggingface, cerebras, chutes) were **36 hours old**
   and are not evidence about now, while cloudflare/hyperbolic/zai were 7–12 minutes old and were
   the bug. `sambanova:free` still looks identical to a dead key and is actually rate-limited.

## 1. Verify first

1. **[DID THE m98 BENCH ACTUALLY RAISE THROUGHPUT? This is the run's one real measurement.]**
   Run #22 fixed the permanent-refusal bench but could only prove the *classifier* correct, not
   the *throughput* — the fix needs an hour of live traffic to show. Compare against run #22's
   baseline of **`model calls per hour` = 64 (floor 900)** and **187 rate_limited / 59 error / 82
   ok over 3h**:
   ```
   python -c "import sqlite3,time;c=sqlite3.connect('file:state/cascade_scratch.db?mode=ro',uri=True);t=time.time()-10800;print(list(c.execute('select outcome,count(*) from usage where ts>? group by outcome',(t,))))"
   ```
   **If refusal is still ~65%, the bench is not the binding constraint and the next suspect is
   worker count against bucket count** (the `no bucket pinned at rpm 1` order names this).
2. **[M15 — DID THE READER GET KILLED AGAIN? Still the first thing to check, every run.]**
   ```
   grep -nE "kill_stalled_job|restart_reader|read: (finished|starting)" state/overnight.log | tail -12
   ```
   Downtime series is now **1, 8, 19.9, 32, 37, 37.6, 42, 44 min, and once 4h**. Run #22 found
   `read.py` down again at 01:44 (`allsweep` caught it) and the supervisor restored it within the
   same bounce. **Eight measured downtimes is plenty of evidence — this needs a ruling, not
   another measurement.** Options unchanged: teach the stall remedies to check pool refusal first
   and decline; put `read.py` in `STANDING`; or accept the lap.
   **New evidence for the ruling:** run #22 showed the reader can be killed for being silent
   while the *real* reason it is silent is that the pool is refusing **and** the GPU fallback is
   wedged. Killing it does not fix either.
3. **[M17 REGRESSION — one command, and it must stay boring.]**
   ```
   python -c "import sys;sys.path.insert(0,'src');import overnight as ON;print(ON.running('publish.py'),ON.running('publish.py',include_self=True))"
   ```
   Run #22 got `True True` (publish.py genuinely running under the loop), which is the healthy
   shape. `verify_math` §20e pins it.
4. **[preflight — the baseline is 1 FAIL. A SECOND is the finding.]** Run #22 got exactly one:
   `caches empty ... feats/www_dandwiki_com` (**M1**). **`verify_math`'s baseline is now 629
   passed, 0 FAILED** — run #22 added 16 checks in a new §20f. Anything less is a regression.
5. **[Is the GPU lane still producing tokens?]** m99 was fixed by restarting the daemon but its
   **root cause is not established and it will recur.**
   ```
   curl.exe -s --max-time 45 http://localhost:11434/api/generate -d "{\"model\":\"qwen3:8b\",\"prompt\":\"ok\",\"stream\":false,\"options\":{\"num_predict\":4}}" -w " http=%{http_code} t=%{time_total}s\n" -o NUL
   ```
   `/api/ps` and `/api/tags` both read green through the whole wedge — **only a completed
   generation proves it.** If wedged: `ollama stop` will hang in `Stopping...`, and killing
   `llama-server.exe` will NOT clear it. Restart `ollama.exe`; the tray app respawns it.

## 2. Owner decisions — these are the queue's real content

**A. [M18 — MAJOR, LIVE, unchanged] `axis_score()` returns a flat 9.9 at M10 for every input.**
Verified across 1e30→1e40. Reachable through `magnitude.py:244` → `assay_entity()`, so real
M10-anchored entities with measured quantities get a constant axis score. `ledger.py:127-133`
answers the same top-rung question a different, incompatible way. **Either resolution changes
computed magnitudes across the library, which is a charter question, not a repair.** See BUGS M18.

**B. [NEW — ROUTING POLICY, and the natural follow-on to m98] Should an UNRECOGNISED failure
take a bench at all?** After run #22's fix, a failure that is neither a deadline timeout nor a
recognised permanent refusal still takes **zero bench** and is re-claimable immediately — this
includes a **fast 429** (only a 429 that hangs to the deadline gets the doubling ladder) and a
bucket that reliably returns prose instead of JSON (**m96**). The audit recommends a default
`_bury()` fallback. **Run #22 deliberately did not apply it:** it changes pool dynamics while the
pool is the binding constraint, and benching a provider for one transient blip is exactly how a
thin pool gets thinner. **This is a judgment call about routing, not a bug fix.**

**C. [THE PAID LANE IS OVER ITS CEILING — 598/500 calls, est. $11.96]** `foreman.py` has been
reporting this in `FOR_OWNER.md` across several runs with no ruling, and it is **the only item in
the ledger that spends money**. `PAID_LANE_RETIRED = True` is correctly enforced in
`widen_candidates()`, but the **primary claim loop (`cascade_bridge.py:455-473`) has no
`PAID_PREFIX` guard at all** — it filters only on `LOCAL_PREFIX` and `_alive()`, and relies on an
assumption stated in its own comment that Cascade's router config never offers the paid bucket to
a free-tier pool tag. Given this project's history of a "closed" gate that still passed 598/500
calls, **a defensive guard in the primary loop is cheap and was left unapplied only because it
touches the money path and deserves a ruling.**

**D. [m93/m94 — NEW, HIGH IMPACT, VERIFIED] `hostcheck.py` records failed network probes as real
0% rates, in two places.** Both are the **M16 shape**. m93: the raw-mode branch can never produce
`rate=None`, so an outage on a raw-only wiki becomes a `WRONG FICTION` verdict and can be written
to `HOST_UNFIT.json`. m94: `null_rate()` caches a fabricated 0.0 baseline for the whole run, which
**silently disables the aboutness veto** for generous hosts like `en.wikipedia.org`. **The repair
changes `endpoint.fetch_raw`'s return contract across callers** — same reason M16 is still open.

**E. [M16, unchanged] `feats.py` caches a network timeout as a verified "nothing here",
permanently.** The repair changes `api()`'s return contract across every caller. **m93/m94 are the
same defect in a second file — a ruling on M16 should probably settle all three at once.**

**F. [m90, unchanged] Three hand-copied copies of the attestation→uncertainty rule, one of them
uncalibrated and dead.** `assay.interval_from_hands` has zero callers and its floors breach the
file's own `SIGMA_MAX/10 = 0.2858` ceiling; the same figures are restated in `custodes.py:229-230`
(whose comment wrongly claims they are derived) and `verify_math.py:630`.

**G. [m91, unchanged] The pool spends calls on Ollama models that are not installed.** Config is
`C:\Users\imarl\cascade\config.json` (**the Cascade project, not this repo**). Run #22 confirmed
the startup banner still removes eight `local-*` buckets as `404 no such model` on every launch.
**The GPU fallback itself is FINE** — do not "fix" the fallback.

**H. [m92 / m79, unchanged] `assay.instrument()`'s undocumented precondition** (latent `TypeError`
on its own `NONE`/`UNESTIMABLE`/`INAPPLICABLE` statuses; both callers pre-filter today), and
**`read.py`'s rate window mixes cache hits with real model calls**, producing garbage `dt` at every
`to GPU` transition.

## 3. Audit rotation

**Audited, do not re-read unless changed:** `pipeline.py`, `dashboard.py`, `foreman.py`,
`feats.py`, `overnight.py`, `standards.py`, `read.py`, `tuning.py`, `gpu_lane.py`, the pool error
path, `rigor.py`, `assay.py`, **`cascade_bridge.py` and `hostcheck.py` (run #22 — both first-ever
reads, both produced verified findings; cascade_bridge's became the run's headline fix)**.

**Never audited, ranked by size × blast radius — take the top two:**
`derivation.py` (558), `manifest_builder.py` (478), `zfighters.py` (484), `rosetta.py` (408),
`reference.py` (357). **`endpoint.py` is now the highest-value unread file** — it is not the
largest, but `fetch_raw`/`api()`'s return contract is the shared root of **M16, m93 and m94**, and
a ruling on §2 D/E needs it read first.

**Method that worked three times now:** point the agent at ONE file, demand `file.py:LINE`
citations and an explicit VERIFIED/UNVERIFIED label per finding, and tell it a clean dimension is
worth reporting. Then **verify every finding at source before touching anything** — run #22's two
audits were right on every finding I checked, but **my own opening hypothesis about the silent-job
standard was wrong** (see §2 above) and would have been the run's headline if I had not checked it.
That is now three runs in a row where the agents were right and an unverified hypothesis of mine
was not.
