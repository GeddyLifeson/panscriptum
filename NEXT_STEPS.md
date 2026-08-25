# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #22b wrote this on 2026-08-25 ~02:55 local.*

**THREE OWNER RULINGS LANDED ON 2026-08-25 AND THEY CHANGE HOW A RUN IS SHAPED. Read these first.**

1. **EVERYTHING AMISS IS INVESTIGATED THE MOMENT IT IS SPOTTED.** Not filed for later, not carried
   forward as a fresh observation next run — worked, on sight. **What is allowed to survive into
   this file is what needs an OWNER RULING** (a charter question, a routing-policy choice, a
   contract change with real blast radius), never something that was merely inconvenient to chase.
2. **THEN, IMMEDIATELY: THE FULL COMPREHENSIVE SWEEP — every line of every module, every run.**
   `python src/sweep_plan.py --batches 16`, one sonnet-tier agent per batch, all launched
   together; each writes its full report to `handoff/sweep<N>/AUDIT_batchNN.md` and returns **only
   a compact summary** (never the full report — one agent's output will otherwise eat your
   context). Then `sweep_plan.missing("run<N>")` **proves** coverage. **The old "top two
   never-audited files" rotation is abolished — it was a Hard Rule 0 cap wearing a schedule's
   clothing.** Run #22b's first full pass: 95 modules, 39,518 lines, none skipped.
   **THE ONLY ACCEPTABLE QUIET RESULT** is that nothing bad was found and the only thing left is
   work *waiting* — the cloud pool out of free quota for the window, or the local model simply
   grinding its queue. "No findings" because nobody looked hard enough is not a clean run.
3. **AN UNRECOGNISED FAILURE IS A BUG, NOT WEATHER.** Anything the code cannot NAME is recorded
   with its text by `cascade_bridge.record_unrecognised()` and shown by the
   **`every pool failure is recognised`** standard. **If that standard is red, it is the run's
   first job**: read the error text, and either add its wording to the `permanent` tuple in
   `cascade_bridge._ask_call` (if it is a permanent refusal) or file it as a bug.
   **It went red on its first publish and named a bug the same session had just "fixed" (m108):
   the classifier was judging Cascade's aggregate wrapper, never a provider error.
   `provider_error()` now unwraps it out of the scratch DB before classifying. If a row ever
   appears whose text is STILL an engine aggregate (`All N candidates failed`, `Every model in
   this pool`), the unwrap failed for that bucket -- check the scratch-DB row's age against the
   180-second window before assuming the provider is at fault.**

**And four standing lessons that keep proving themselves:**

4. **VERIFY THE CADENCE WITH `list_scheduled_tasks`. NEVER FROM A FILE, INCLUDING THIS ONE.**
   Read back 2026-08-25: hourly, `11 * * * *` + 523s jitter, firing ~:19–:20. The **15 minutes in
   the overlap guard is the heartbeat-staleness threshold** — a different number answering a
   different question. Do not "fix" it to match the schedule. **The guard does NOT see interactive
   sessions**: check `git -C C:\Users\imarl\panscriptum-export log --oneline -5` and
   `ls -lt src/*.py | head` before writing anything.
5. **A SHARED LOG IS NOT A LIVENESS SIGNAL — ASK WHO ELSE CAN WRITE THAT FILE.** `pipeline.log`
   is written by *any* process importing `pipeline.py`, so its freshness proves nothing about the
   pipeline job; the job's own `PIPELINE_STATE.json` is the real signal. This nearly cost run #22
   a good standard, filed as a false positive.
6. **AGE `data/COVERAGE.json` BEFORE BELIEVING ANY COVERAGE STALL.** Under 0.5h → real; over →
   artifact. It has now been an artifact three runs running (0.90h, 0.87h).
   **`dashboard.py`'s stall flag is at :362, not :338** — run #22b's audit corrected the line
   number the last three queues had been repeating.
7. **AGE EVERY `bucket_state.last_error` ROW AND READ THE TEXT.** The four `Could not resolve
   host` rows were **36 hours old** and are not evidence about now; cloudflare/hyperbolic/zai were
   7–12 minutes old and were the bug.

## 1. Verify first

1. **[DID THE m98 BENCH RAISE THROUGHPUT? Still unmeasured — it needs an hour of live traffic.]**
   Baseline to beat: `model calls per hour` **64** against a floor of 900, and **187 rate_limited
   / 59 error / 82 ok** over 3h.
   ```
   python -c "import sqlite3,time;c=sqlite3.connect('file:state/cascade_scratch.db?mode=ro',uri=True);t=time.time()-10800;print(list(c.execute('select outcome,count(*) from usage where ts>? group by outcome',(t,))))"
   ```
   A 15-minute sample right after the fix showed 63 calls / 13 ok (vs 16 / 2 before) — **promising,
   not proof**, and it is confounded with the GPU-lane restart. If refusal is still ~65%, the next
   suspect is **worker count against bucket count**.
2. **[FINISH THE m100 TAIL — ~14 non-atomic writes, now mechanical.]** `silence.write_json()`
   exists; the pattern is `open(X, "w")` + `json.dump` → `silence.write_json(X, obj, ...)`.
   Sites listed in BUGS m105. **`foreman.py:996` is the interesting one** — it writes a LIVE
   `src/*.py` during a model patch; it has a backup and auto-revert, so it is not urgent, but a
   crash mid-write leaves a corrupt module. Add each converted file to §20g's `_REPAIRED_20g` list.
3. **[preflight baseline is 1 FAIL. A SECOND is the finding.]** `caches empty ...
   feats/www_dandwiki_com` (**M1**). **`verify_math`'s baseline is now 666 passed, 0 FAILED.**
4. **[Is the GPU lane still producing tokens?]** m99's root cause is NOT established and it will
   recur. `/api/ps` and `/api/tags` read green through the entire wedge — **only a completed
   generation proves it.** If wedged: `ollama stop` hangs in `Stopping...` and killing
   `llama-server.exe` will NOT clear it; restart `ollama.exe` and the tray app respawns it.
5. **[M15 — and the last three queues pointed the investigation at the wrong file.]** Run #22b's
   audit established that **`overnight.py` has no stall-detection logic at all** — its only kill
   path is wall-clock `TimeoutExpired`. The `kill_stalled_job` line in its log is a **replayed
   FOREMAN.json line**. **The mechanism lives in `foreman.py`. Look there.**

## 2. Owner decisions — these are the queue's real content

**A. [M18 — MAJOR, LIVE, unchanged] `axis_score()` returns a flat 9.9 at M10 for every input.**
Live through `magnitude.py:244` → `assay_entity()`. `ledger.py:127-133` answers the same question
incompatibly. **Either resolution changes computed magnitudes across the library — a charter
question, not a repair.** Related, same shape, found this sweep: `assay.INSTRUMENT_WINDOWS`
collapses to `(30, 30)` for M5–M10.

**B. [ROUTING POLICY] Should an UNRECOGNISED failure take a bench at all?** Ruling 3 made them
*visible*; it did not say they should be *absorbed*. Today such a failure takes **zero** cooldown
and is instantly re-claimable — including a **fast 429** (only one that hangs to the deadline gets
the doubling ladder) and a bucket that reliably returns prose instead of JSON (**m96**). Adding a
default bench is a routing change while the pool is the binding constraint, and benching on one
transient blip is how a thin pool gets thinner. **Your call.**

**C. [SECURITY-ADJACENT — no live secret found, but the guarantee is overstated] `publish.py`
scrubs only `state.json`.** `_scrub()` covers the generated snapshot; `sync_tree()`'s bulk copy of
`src/`, `prompts/`, `reference/`, `registry_terminal/`, `handoff/` and `config.yaml` — all
`git add -A`'d and pushed to a public repo — has **zero content scrubbing**, while the docstring's
"carries no keys" reads as though it covers everything. **Nothing leaked today.** Worth either
extending the scrub to the whole synced tree or narrowing the docstring's claim.

**D. [m106 — THE ROOT OF FOUR BUGS] `endpoint.py:200-233`'s return contract.** `fetch_raw()`
returns an identical `(t, None)` for a confirmed 404/410, an HTTP refusal, an exception, and an
HTML error body, so **no caller can tell "absent" from "request failed"**. M16, m93, m94 and m107
are all symptoms. `detect()` compounds it by caching a timeout as `MODE_DEAD` for 24h. **One
ruling settles all four**; the repair changes a contract every caller depends on.

**E. [m90, unchanged] Three hand-copied copies of the attestation→uncertainty rule.** Now
confirmed to be **four**: `custodes.py:229-230`'s `_ATT_BASE` claims to be *derived* and is a
third hand-typed copy of a table that already exists and is used in `assay.py:630-631`.

**F. [Hard Rule 0 — still-open caps the sweep surfaced, each needing a judgment call]**
`feats.py:348-368` `aplimit=500`/`srlimit=50` truncate when MediaWiki signals `continue` (the
module's own docstring says this was deliberately left as "measure it", not "eliminate it");
`wiki_source.py:352` `all_categories(hard_stop=6000)` caps alphabetically while its docstring
claims it only bounds the API walk — **6000 is the same number that once lost Superman**;
`rosetta.py:194` `srlimit=5`; `retry_synthesis.py:60` `sorted(...)[:14]` reverts the m13 fix for
exactly the sources it exists to retry; `weave.py`'s `len(srcs) > 60` skip.

**G. [m91, unchanged] The pool spends calls on Ollama models that are not installed.** Config is
`C:\Users\imarl\cascade\config.json` (**the Cascade project, not this repo**). **The GPU fallback
itself is FINE** — do not "fix" the fallback.

## 3. The sweep's unworked findings

**Not a backlog of excuses — these are verified-by-agent, unverified-by-me, and they are next
run's work.** Full detail with quoted code in `handoff/sweep22/AUDIT_batch01..16.md`. The ones I
would take first, by blast radius:

- `overwatch.py:326-343` — the reconcile filter **drops real findings** (stale coverage, orphan
  hosts, ghost entries) and every internal exception before they reach `WATCH.md`, and
  `write_report` never reads the `error`/`estate_error` keys, so a **crashed** structural check
  renders as "0 broken, 0 corrupt". The bug queue's own reporting is lying by omission.
- `completeness.py:71-119` — an unguarded global dict mutated and `json.dump`-iterated across
  `ThreadPoolExecutor` workers with no lock: a live `RuntimeError` crash risk.
- `pipeline.py:487-530` — `write_record`'s drift check is **length-only**, so a concurrent
  same-count writer is silently clobbered; and both merge field lists omit `"excluded"`, so a
  deliberate `catalogued: False` strike can be flipped back to `True`.
- `health.py:124-144` — `flush()`'s SAMPLES write ends in a bare `except: pass`, permanently
  dropping the evidence bag, **in the module whose whole purpose is "no silent failures"**.
- `feats_index.py:148` — `host_dir.replace("_", ".")` mis-reconstructs any hyphenated host
  (`date-a-live.fandom.com`), silently breaking the join and producing a false diagnosis the
  module's own docstring states as fact.
- `tells.py:70` — regex alternation precedence makes the `but Y` requirement apply to only the
  third alternative; verified false positives.
- `onomast.py:311-356` — `register_for()`'s genre/feature voting is **dead**; the sole caller
  passes only `group_id`, so every world uses the hash fallback the docstring says was replaced.
- `sevenfold.py:198-209`, `anchors.py:215`, `autostart.py:208-211`, `overnight.py:416-455`
  (two missing `returncode` checks that let a crashed subprocess re-report stale numbers as fresh).

## 4. Audit rotation — ABOLISHED

There is no rotation any more; see ruling 2. `state/SWEEP_COVERAGE.json` records which run last
read each module, and `sweep_plan.missing(run)` is the completeness proof. **Method that has now
worked four times:** point one agent at a bounded set of files, demand `file.py:LINE` citations
and an explicit VERIFIED/UNVERIFIED label, tell it a clean module is a worthwhile result, and make
it write the long report to disk and return only a summary. **Then verify at source before
touching anything** — this sweep's agents were right on every finding I checked, and they also
caught two real bugs in code I had written an hour earlier plus a false-positive risk in my own
classifier. **They are a better check on my work than I am.**
