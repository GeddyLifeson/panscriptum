# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #23 wrote this on 2026-08-25 ~04:1x local.*

**THE THREE OWNER RULINGS OF 2026-08-25 STILL SHAPE THE RUN. Read these first.**

1. **EVERYTHING AMISS IS INVESTIGATED THE MOMENT IT IS SPOTTED** — worked on sight, never filed
   for later. **What is allowed to survive into this file is what needs an OWNER RULING**
   (a charter question, a routing-policy choice, a contract change with real blast radius), plus
   the sweep's verified-but-unrepaired tail in §3, which is REAL WORK, not a backlog of excuses.
2. **THEN, IMMEDIATELY: THE FULL COMPREHENSIVE SWEEP — every line of every module, every run.**
   `python src/sweep_plan.py --batches 16`, one sonnet-tier agent per batch, all launched
   together; each writes its full report to `handoff/sweep<N>/AUDIT_batchNN.md` and returns **only
   a compact summary**. Then `sweep_plan.missing("run<N>")` **proves** coverage.
   **Run #23's pass: 95 modules, 39,687 lines, 0 uncovered, 16 reports on disk.**
3. **AN UNRECOGNISED FAILURE IS A BUG, NOT WEATHER.** If `every pool failure is recognised` is
   red, it is the run's first job. **Read the ledger before believing its size** — see lesson 8.

**And the standing lessons. Number 8 is new and it is the one that mattered most this run.**

4. **VERIFY THE CADENCE WITH `list_scheduled_tasks`. NEVER FROM A FILE, INCLUDING THIS ONE.**
   Hourly, `11 * * * *` + 523s jitter, firing ~:19–:20 (read back 2026-08-25). The **15 minutes in
   the overlap guard is the heartbeat-staleness threshold** — a different number answering a
   different question. Do not "fix" it to match the schedule. **The guard does NOT see interactive
   sessions**: check `git -C C:\Users\imarl\panscriptum-export log --oneline -5` and
   `ls -lt src/*.py | head` before writing anything.
5. **A SHARED LOG IS NOT A LIVENESS SIGNAL — ASK WHO ELSE CAN WRITE THAT FILE.**
6. **AGE `data/COVERAGE.json` BEFORE BELIEVING ANY COVERAGE STALL.** Under 0.5h → real; over →
   artifact. `dashboard.py`'s stall flag is at **:362** (run #22b's audit corrected this; run #23's
   agent re-confirmed :362 and found the logic itself sound).
7. **AGE EVERY `bucket_state.last_error` ROW AND READ THE TEXT.** Rows 27–37 HOURS old are not
   evidence about now. `provider_error()`'s 180s window exists for exactly this.
8. **[NEW, RUN #23] AGE EVERY FILE A STANDARD READS — ESPECIALLY WHEN IT READS GREEN.** Lesson 6
   is about a false STALL. This is the same fault from the far more dangerous side: **a stale file
   producing a false ALL-CLEAR is never looked at again.** `model IDs their providers still serve`
   (HIGH) read green off a **58-hour-old** snapshot while the reader's live log showed five model
   IDs 404-ing on every start. Fixed (m112), and the refresh immediately found **8 stale names**.
   **Ask of every green high-severity standard: how old is the evidence?**
9. **[NEW, RUN #23] A CHECK THAT CANNOT FAIL LOOKS EXACTLY LIKE A CHECK THAT PASSED.** All four of
   this run's major finds are that one shape — a classifier with no transient branch (m109), a
   standard with no age check (m112), a denylist that missed on case (m113), a report that never
   read its own error keys (m116). **When something has never once failed, that is the finding.**

## 1. Verify first

1. **[DID m109/m110 CLEAR THE POOL LEDGER, AND IS THE PAGE READABLE NOW?]** Baseline to beat:
   the ledger was **44 rows / 122 occurrences with ONE genuine unknown**; it should now hold only
   real unknowns.
   ```
   python -c "import sys;sys.path.insert(0,'src');import cascade_bridge as C;r=C.unrecognised_open();print(len(r),'rows');[print(' ',x['bucket'],'|',x['error'][:90]) for x in r]"
   ```
   **If a `Rate limit`/`429`/`quota` row reappears, `named_transient` has a gap — widen it.**
   **If an `All 1 candidates failed` row is still there, that is CORRECT and deliberate** — it is
   the shape that exposed m108. Chase its bucket's `bucket_state.last_error` instead.
2. **[IS `model IDs their providers still serve` STILL RED, AND IS IT THE SAME 8?]** It should be:
   the repair is m91, in the Cascade project. **If the count MOVED, something changed the Ollama
   install** — read it before assuming. Refresh with `python src/catalogue_models.py`.
3. **[preflight baseline is 1 FAIL. A SECOND is the finding.]** `caches empty ...
   feats/www_dandwiki_com` (**M1**). **`verify_math`'s baseline is now 682 passed, 0 FAILED.**
4. **[Is the GPU lane still producing tokens?]** m99's root cause is NOT established and it will
   recur. `/api/ps` and `/api/tags` read green through the entire wedge — **only a completed
   generation proves it.** Run #23's sweep found the mechanism that lets it persist: see §3,
   `gpu_lane.py`.
5. **[M15 — the reader still waits a supervisor lap.]** Confirmed live again this run: read.py down
   02:50 → 03:31 (41 min). The mechanism is in `foreman.py:753,759` (`restart_reader` wired to
   *"corpus read is progressing"*), NOT in `overnight.py`, which has no stall detection of its own.
   **A reader `rc=4294967295` is a PROCESS BOUNCE, not a crash** — run #23 chased it before
   matching the timestamps to run #22b's commits. `rc=15` is the foreman's SIGTERM.

## 2. Owner decisions — these are the queue's real content

**A. [M18 — MAJOR, LIVE, unchanged] `axis_score()` returns a flat 9.9 at M10 for every input.**
Live through `magnitude.py:244` → `assay_entity()` (`magnitude.py:709-711`, re-confirmed run #23).
`ledger.py:127-133` answers the same question incompatibly — at the last band `hi == lo`, so
`joules` collapses to the floor **regardless of `ruin_score`**, silently making the score parameter
irrelevant (independently re-traced run #23). **Either resolution changes computed magnitudes
across the library — a charter question, not a repair.** Same shape: `assay.INSTRUMENT_WINDOWS`
collapses to `(30, 30)` for M5–M10, so `instrument()` prints a flat 30 regardless of axis score.

**B. [ROUTING POLICY, now sharper] Should a refusal cost a bucket a cooldown?** m109/m110 settled
what gets *recorded*; they deliberately did **not** change what gets *benched*. Today a recognised
throttle takes **zero** cooldown and is instantly re-claimable. **Two sub-questions the run
declined to answer alone:**
  - a **daily or monthly exhaustion** (`free-models-per-day`, Cohere's `1000 api calls / month`)
    is not the same as a passing 429 — it will refuse every call until the window rolls. Benching
    it until reset is arguably right, but it is a routing change while the pool is the binding
    constraint.
  - a bucket that reliably returns prose instead of JSON (**m96**) is never benched at all.
  **Your call.** Benching on one transient blip is how a thin pool gets thinner.

**C. [SECURITY-ADJACENT — unchanged, re-verified run #23] `publish.py` scrubs only `state.json`.**
`_scrub()` covers the generated snapshot; `sync_tree()`'s bulk copy of `src/`, `prompts/`,
`reference/`, `registry_terminal/`, `handoff/` and `config.yaml` — all `git add -A`'d and pushed to
a **public** repo — has **zero content scrubbing** (`SKIP_SUFFIX` is a backup-extension denylist
only), while the docstring's "carries no keys" reads as though it covers everything. **A run #23
agent re-checked every synced path and found no live secret.** Worth either extending the scrub to
the whole synced tree or narrowing the docstring's claim.

**D. [m106 — THE ROOT OF FOUR BUGS] `endpoint.py:200-233`'s return contract.** `fetch_raw()`
returns an identical `(t, None)` for a confirmed 404/410, an HTTP refusal, an exception, and an
HTML error body, so **no caller can tell "absent" from "request failed"**. M16, m93, m94 and m107
are all symptoms. `detect()` (`:126-173`) compounds it by caching a timeout as `MODE_DEAD` for 24h.
Run #23 enumerated the misled callers exactly: `feats.py:437`, `hostcheck.py:135`, `hostcheck.py:246`
for `fetch_raw`; `feats.py:345,436` and `hostcheck.py:134,245` for `detect`. **One ruling settles
all four.**

**E. [m90, unchanged] Four hand-copied copies of the attestation→uncertainty rule.**
`custodes.py:229-230`'s `_ATT_BASE` **claims to be derived** and is a byte-for-byte hand-typed copy
of the table at `assay.py:630-631`, with no import linking them (re-verified run #23).

**F. [Hard Rule 0 — open caps, each needing a judgment call]** `wiki_source.py:352`
`all_categories(hard_stop=6000)` caps **alphabetically** while its docstring claims it only bounds
the API walk — **6000 is the number that once lost Superman** (independently re-traced run #23);
`feats.py:311-368` `aplimit=500`/`srlimit=50` truncate when MediaWiki signals `continue` and no
continuation loop was ever added; `rosetta.py:194` `srlimit=5`; `retry_synthesis.py:60`
`sorted(...)[:14]`; `pipeline.py:673` `rest[:14]`; `cosmology_graph.py:86-87` caps `pair_shared`
at 8 and it is consumed as **real evidence** by `resonance.py:146`; `scope.py:68-81` `srlimit=3`×4
plus `titles[:8]` feeding the fiction-wide Magnitude ceiling; `weave.py:205-226` `max_sources=60`;
`ingest_doc.py:216` `description[:2000]`.

**G. [m91 — NOW FULLY EVIDENCED, and it is not in this repo] The pool spends calls on Ollama
models that are not installed.** Run #23 measured it: **8 stale references, `qwen3:8b` the only
installed model**, and the reader re-discovers and re-removes them on **every start**. Config is
`C:\Users\imarl\cascade\config.json` (**the Cascade project**). **The GPU fallback itself is
FINE — do not "fix" the fallback.** Deleting eight dead names from another project's config is the
whole repair.

## 3. The sweep's unworked findings — verified by agent, unverified by me, and this is next run's work

*Full detail with quoted code in `handoff/sweep23/AUDIT_batch01..16.md`. Ordered by blast radius.
**Verify at source before touching anything** — the agents were right on every finding I checked
this run, including two in code I had written an hour earlier, but they are not infallible.*

**The ones I would take first:**

- **`overwatch.py:326-343` — the reconcile filter still DROPS REAL FINDINGS.** m116 fixed only the
  crashed-check half. The whitelist still discards stale coverage, orphan cache dirs, ghost roster
  entries **and all six of `allsweep.reconcile()`'s internal exception handlers** before they reach
  WATCH.md. The bug queue's own reporting is still lying by omission.
- **`catalogue_codex.py:159` — 70 codex elements silently miscategorised**, verified against real
  data: 35 "weapon property", 28 "race variant" (incl. Eberron Dragonmarks), 7 "background variant"
  land in THINGS via a default fallback instead of POWERS.
- **`feats_index.py:148` — hyphenated hosts stranded, four confirmed live** (`date-a-live`,
  `sakamoto-days`, `the-amazing-digital-circus`, `uncle-grandpa`). `host_dir.replace("_", ".")` is
  irreversible; the correct host is **already sitting unused in `rec["host"]`**. The module's own
  docstring misdiagnoses this as "hosts with no WIKI_HOSTS entry" — all four are bound.
- **`gpu_lane.py:326-455` — a wedged call can hold a GPU slot forever.** The heartbeat thread
  refreshes the lease independently of the wrapped model call, so a hung-but-alive Ollama request
  never trips staleness or PID-death. **This is the mechanism behind m99's persistence.**
  Also `gpu_lane.py:66-67`: unguarded `int(os.environ.get(...))` raises at import, contradicting
  the module's own "fail open, always" promise.
- **`sweep_plan.record()` — the lost-update race its docstring claims to have fixed is NOT fixed
  for real usage.** `_RECORD_LOCK` is a `threading.Lock`; the 16 batches run as **separate OS
  processes**. (Run #23's coverage proof is still trustworthy — `missing()` returned 0 *and* all
  16 reports are on disk, two independent corroborations — but fix this before relying on the
  proof alone.)
- **`completeness.py:71-119`** unguarded global dict mutated and `json.dump`-iterated across
  ThreadPoolExecutor workers (live `RuntimeError` risk), **plus `:110-118` a fixed, non-unique temp
  filename shared across those same workers** — m100's anti-pattern again.
- **`onomast.py:311-356`** — `register_for()`'s genre/feature voting is **dead**; the sole caller
  passes only `group_id`, so every world uses the hash fallback the docstring says was replaced.
- **`endpoint.py:83-94` and `:356-370`** — `_save()` and `register()` do unguarded
  read-modify-writes on shared `ENDPOINTS.json` / `SOURCE_PAGES.json` with bare `.tmp` names;
  `register()` has no lock at all and its `os.replace` is not even wrapped.
- **`magnitude.py:911-990`** — cross-process lost-update on `data/ASSAYS.json`: `run_batch`'s
  `done` dict is loaded once per process and each completion rewrites the whole file from that
  process-local snapshot.
- **`coverage.py:16-18` vs `:82-115`** — the docstring promises an `UNREACHABLE` state
  distinguishing fetch failure from real absence; **the code never implements it** and a transient
  read exception folds silently into `"NO PAGE"`.
- **`retry_synthesis.py:60`** — beyond the `[:14]` cap, the docstring's claim of being
  "byte-identical" to `phase_synthesis` is **false**: the real one (fixed under m13) ranks by
  feats-present and paginates ALL feat-bearing entries; this one sorts by raw description length
  and takes one slice. Affects Dragon Ball Z, Dune and 10 more already-failed sources, merged
  permanently and never revisited. Also `:43-47,109-112` write into `data/records/*.json` directly
  with no runtime guard enforcing its "pipeline must be stopped" precondition.
- **`health.py:124-144`** — `flush()`'s SAMPLES write ends in a bare `except: pass` with no
  self-heal, permanently dropping the evidence bag, in the module whose purpose is "no silent
  failures". Also `:180-181`: a second, more permissive set of chars-per-token constants shadowing
  the ones `context_budget.py` exists to own.
- **`overnight.py:414-455`** — `coverage_snapshot()`/`preflight()` never check subprocess
  `.returncode`, so a crashed `coverage.py` or `health.py` re-reports stale data as a fresh pass.
- **`anchors.py:215`** — the `order` list puts Yggdrasil (M6) before Goku (M5), so the
  monotonicity check fires **every run regardless of instrument health**.
- **`runguard.py:98-121`** — `claim()` TOCTOU: `read()` then `_land()` with no lock spanning them,
  defeating the module's sole purpose.
- **`local_agent.py`** — m113/m114/m115 are fixed, but re-audit the remaining gates next sweep;
  this is the one module where a gap means unreviewed model-written code lands in `src/`.
- **Non-atomic shared writes still open (the m100 tail's remainder):** `build_terminal.py:572`,
  `burgs.py:227`, `module_index.py:75`, `overnight.py:462`, `publish.py:262`, `render.py:245`,
  `rosetta.py:365` and `:377`, `worldseed.py:317-322`, `hosts.py:78-91`, `manifest_builder.py:436,455,463`,
  `foreman.py:996` (**this one writes a LIVE `src/*.py` during a model patch** — backed up and
  auto-reverted, so not urgent, but a crash mid-write leaves a corrupt module).
- **Unguarded read-modify-write on `data/SWEEP_ROLL.json` (now FIVE possible writers):**
  `resync_roll.py:33-68` (whose docstring's "safe to run at any time" conflates write-atomicity
  with race-safety), `catalogue_aurora.py:107-150`, `catalogue_codex.py:122-203`.
- **Smaller, verified:** `scout.py:107-114` (`_ask()` swallows all exceptions to `None`,
  indistinguishable from "no URLs known"), `:200-206` (race on `WIKI_HOSTS.json`), `:256-262`
  (corrupt `SCOUT.json` silently discards history); `profile.py:129-138` (failed load → blanket
  default, indistinguishable from real data); `identity.py:180-207` (`_is_continuity()`
  misclassifies its own worked example) and `:291-320` (`epoch_of()` returns `""` for both "no
  marker" and "call failed"); `tells.py:70` (regex alternation precedence — the `but Y` requirement
  applies to only the third alternative); `chain.py:353` (unguarded `Counter` increment outside the
  lock two lines below); `burgs.py:230` (message says "sample of 50 worlds", code writes all);
  `sweep.py:132-163` (docstring claims a strict funnel nesting the code does not produce);
  `address_space.py:130-140` ("widths are derived, not chosen" above a hard-coded 64);
  `repass_bands.py:91` (hardcoded `"of 211"`); `overwatch.py:552-553` (WATCH.md caps the open list
  at 40 while the header count is uncapped, so they diverge); `standards.py:966-982`
  (`fandom_ipv4_reachable()` does a live TCP connect with no TTL cache, unlike its cached
  siblings, on a path the dashboard polls every 5s); `recover_folder_records.py:143-150` (bypasses
  the two-writer contract and its comment falsely claims the gap "is flagged in NEXT_STEPS" —
  **it now genuinely is, here**); `verify_math.py:56` (float-tolerance branch can raise TypeError
  on a non-numeric `got` and truncate the whole report).

## 4. Audit rotation — ABOLISHED

No rotation. `state/SWEEP_COVERAGE.json` records which run last read each module and
`sweep_plan.missing(run)` is the completeness proof — **but see §3, its cross-process race means
the proof should be corroborated against the report files on disk until that is fixed.**
**Method that has now worked five times:** bound the file set, demand `file.py:LINE` citations and
an explicit VERIFIED/UNVERIFIED label, tell the agent a clean module is a worthwhile result, and
make it write the long report to disk and return only a summary. **Point at least one agent at the
code the supervisor wrote that same session** — that instruction has now caught real defects in
the supervisor's own work two runs running.
