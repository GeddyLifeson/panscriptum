# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #21 wrote this on 2026-08-25 ~00:50 local.*

**Read this first.** Five things shape what is worth doing next run:

1. **VERIFY THE CADENCE WITH `list_scheduled_tasks`. NEVER FROM A FILE, INCLUDING THIS ONE.**
   As of run #20 it was hourly (`11 * * * *` + 523s jitter, firing ~:19–:20). That claim has been
   wrong twice in opposite directions, always because nobody read the cron back. It is one call.
   The **15 minutes in the overlap guard is the heartbeat-staleness threshold** — a different
   number answering a different question. Do not "fix" it to match the schedule.
   The guard does **NOT** see interactive sessions: before writing anything, check
   `git -C C:\Users\imarl\panscriptum-export log --oneline -5` and `ls -lt src/*.py | head`.
2. **RUN #21's LESSON GENERALISES, AND THE NEXT RUN SHOULD SPEND ITS FIRST TEN MINUTES ON IT.**
   The liveness roster was reporting its own author as a dead job, because it asked *"is job X
   up?"* with a function built to answer *"is anyone ELSE running this?"*. It was proved by
   reading **one standard off three processes at one moment** and getting three answers. That
   technique is cheap and it is the run's most reusable finding. **The general question: what
   else in this project measures a system it is running inside?** Named candidates, none checked:
   `dashboard.movement()` (computes deltas from files other panels in the same process wrote),
   `standards`' own age/staleness floors, `allsweep`'s reconcile tier, and anything reading
   `state/job_progress.json` while holding it open. **A measurement taken from inside the thing
   measured is guilty until it proves otherwise.**
3. **THE PAGE OPENS THE RUN — AND CHECK ITS FRESHNESS AND ITS SELF-CONSISTENCY, NOT JUST ITS REDS.**
   Run #21's page was fresh (4 min) and internally contradictory: `jobs` showed "corpus read"
   advancing at 1.54 chunks/s with an 18.8h ETA while `movement` showed `chunks` flat for 30
   minutes. **The contradiction was the finding** — the reader was dead and the rate was a stale
   historical average. When a panel's rate and its movement disagree, believe movement.
4. **AGE `data/COVERAGE.json` BEFORE BELIEVING ANY COVERAGE STALL. THIS BIT AGAIN.**
   `dashboard.py:338` flags `stalled` over a **30-minute** window while `allsweep.py:203-207`
   treats the file as fresh for **2 hours**, so a file not rewritten inside the window *cannot*
   produce a delta.
   ```
   python -c "import os,time;print('%.2fh'%((time.time()-os.path.getmtime('data/COVERAGE.json'))/3600))"
   ```
   Under 0.5h → the stall is real. Over 0.5h → artifact. **Run #21 measured 0.90h, so its flat
   `cited`/`settled`/`feats` were an artifact and correctly ignored.** `chunks` and `entities read`
   do **not** share this hazard (different sources) — run #21's were genuinely flat, and that was
   the dead reader.
5. **AGE EVERY `bucket_state.last_error` ROW AND READ THE ERROR TEXT, NOT JUST THE OK RATE.**
   A 0% bucket is a symptom; the error string is the diagnosis. `sambanova:free` still looks
   identical to a dead key and is actually rate-limited.

## 1. Verify first

1. **[M15 — DID THE READER GET KILLED AGAIN? Still the first thing to check, every run.]**
   ```
   grep -nE "kill_stalled_job|restart_reader|read: (finished|starting)" state/overnight.log | tail -12
   ```
   **The run #19 honest-note fix is CONFIRMED WORKING** — the 00:09:01 order names the MAIN LAP
   and its real horizon, not "next cycle". Do not re-fix it. Downtime series is now
   **1, 8, 19.9, 32, 37, 37.6, 42, 44 min, and once 4h** (run #21 added 37.6 and 19.9).
   **M15 itself is still open and still the owner's design choice** among: teach the stall
   remedies to check pool refusal first and decline; put `read.py` in `STANDING`; or leave it and
   accept the lap. **Eight measured downtimes is plenty of evidence — this needs a ruling, not
   another measurement.**
2. **[M17 REGRESSION — one command, and it must stay boring.]**
   ```
   python -c "import sys;sys.path.insert(0,'src');import overnight as ON;print(ON.running('publish.py'),ON.running('publish.py',include_self=True))"
   ```
   `verify_math` §20e pins this, but if anyone drops `include_self=True` from `standards.py` the
   symptom is subtle: the panel quietly names its own author as down again.
3. **[preflight — the baseline is 1 FAIL. A SECOND is the finding.]** Run #21 got exactly one:
   `caches empty ... feats/www_dandwiki_com` (**M1**). **M8 (`API paths per host family`) passed
   again.** `verify_math`'s baseline is now **613 passed, 0 FAILED** — anything less is a
   regression, anything more means someone added checks.
4. **[Are the four dead accounts still in rotation?]**
   ```
   python -c "import sqlite3,time;c=sqlite3.connect('file:state/cascade_scratch.db?mode=ro',uri=True);t=time.time()-10800;print(list(c.execute('select bucket,outcome,count(*) from usage where ts>? group by bucket,outcome order by 3 desc',(t,))))"
   ```
   Run #21's page showed **54 calls / 22 ok in 15 min (59% refusal)**, `model calls per hour` at
   **216 against a floor of 900**, and `reprove_pool` returning **17 of 36** and then **4 of 36**
   buckets in the same round. The pool is the system's binding constraint and has been for days.

## 2. Owner decisions — these are the queue's real content

**A. [M18 — NEW, MAJOR, LIVE] `axis_score()` returns a flat 9.9 at M10 for every input.**
Verified across 1e30→1e40. Reachable through `magnitude.py:244` → `assay_entity()`, so real
M10-anchored entities with measured quantities get a constant axis score. `ledger.py:127-133`
answers the same top-rung question a different, incompatible way (score parameter becomes
irrelevant). **Either resolution changes computed magnitudes across the library, which is a
charter question, not a repair.** Do not patch this without a ruling. See BUGS.md M18.

**B. [M15] The reader-kill loop.** As above — evidence is complete, ruling outstanding.

**C. [M16] `feats.py` caches a network timeout as a verified "nothing here", permanently.**
Unchanged. The repair changes `api()`'s return contract across every caller.

**D. [m90] Three hand-copied copies of the attestation→uncertainty rule, one of them
uncalibrated and dead.** `assay.interval_from_hands` has zero callers and its floors breach the
file's own `SIGMA_MAX/10 = 0.2858` ceiling; the same figures are restated in `custodes.py:229-230`
(whose comment wrongly claims they are derived) and `verify_math.py:630`. **Deleting a public
function needs a review cycle; deriving the three from `SIGMA_BY_ATTESTATION` changes numbers.**

**E. [m91] The pool spends calls on Ollama models that are not installed** — 695 failures in 24h
across `ollama:qwen2.5:14b` and `ollama:llama3.1:latest`. The config is
`C:\Users\imarl\cascade\config.json` (**the Cascade project, not this repo**), which defines eight
`local-*` buckets and names `qwen3:8b` in none of them. **The GPU fallback itself is FINE** —
`ollama:local` ran 1,471 ok / 895 error in the same window. Do not "fix" the fallback; it works.

**F. [m92] `assay.instrument()`'s undocumented precondition.** Latent `TypeError` on the file's
own `NONE`/`UNESTIMABLE`/`INAPPLICABLE` statuses. Both callers pre-filter today.

**G. [m79 / §2 E, unchanged] `read.py`'s rate window mixes cache hits with real model calls**,
producing garbage `dt` at every `to GPU` transition. `chunks_reused` is already computed for
exactly this distinction and then discarded. Evidence attached in run #20's entry. Owner's call.

## 3. Audit rotation

**Audited, do not re-read unless changed:** `pipeline.py`, `dashboard.py`, `foreman.py`,
`feats.py`, `overnight.py`, `standards.py`, `read.py`, `tuning.py`, `gpu_lane.py`, the pool error
path, **`rigor.py` and `assay.py` (run #21 — both first-ever reads, both produced verified
findings)**.

**Never audited, ranked by size × blast radius — take the top two:**
`hostcheck.py` (955), `cascade_bridge.py` (788) — *this one is the pool's own transport and the
pool is the binding constraint; it is the highest-value unread file in the tree* —
`derivation.py` (558), `manifest_builder.py` (478), `rosetta.py` (408), `reference.py` (357),
`zfighters.py` (484).

**Method that worked twice now:** point the agent at ONE file, demand `file.py:LINE` citations
and an explicit VERIFIED/UNVERIFIED label per finding, and tell it a clean dimension is worth
reporting. Then **verify every finding at source before touching anything** — run #21's audits
were right on all six findings, but one of *my own* opening hypotheses (that the GPU fallback had
disappeared) was wrong and would have been the run's headline if I had not checked it.
