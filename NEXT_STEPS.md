# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #25 wrote this on 2026-08-25 ~06:0x local.*

**THE THREE OWNER RULINGS OF 2026-08-25 STILL SHAPE THE RUN. Read these first.**

1. **EVERYTHING AMISS IS INVESTIGATED THE MOMENT IT IS SPOTTED** — worked on sight, never filed
   for later. **What is allowed to survive into this file is what needs an OWNER RULING**
   (a charter question, a routing-policy choice, a contract change with real blast radius), plus
   the sweep's verified-but-unrepaired tail in §3, which is REAL WORK, not a backlog of excuses.
2. **THEN, IMMEDIATELY: THE FULL COMPREHENSIVE SWEEP — every line of every module, every run.**
   `python src/sweep_plan.py --batches 16`, one sonnet-tier agent per batch, all launched
   together; each writes its full report to `handoff/sweep<N>/AUDIT_batchNN.md` and returns **only
   a compact summary**. Then `sweep_plan.missing("run<N>")` **proves** coverage.
   **Run #25's pass: 95 modules, 40,135 lines, 0 uncovered, 16 reports on disk.**
   **Launch the 16 agents FIRST and work the immediate queue while they run** — run #25 did this
   and the sweep cost no wall-clock at all; the first batch reported back before the opening
   diagnostics were finished.
3. **AN UNRECOGNISED FAILURE IS A BUG, NOT WEATHER.** If `every pool failure is recognised` is
   red, it is the run's first job. **Read the ledger before believing its size** — see lesson 8.

**And the standing lessons. 12 and 13 are new; 12 is this run's whole spine.**

4. **VERIFY THE CADENCE WITH `list_scheduled_tasks`. NEVER FROM A FILE, INCLUDING THIS ONE.**
   Hourly, `11 * * * *` + 523s jitter, firing ~:19–:20. The **15 minutes in the overlap guard is
   the heartbeat-staleness threshold** — a different number answering a different question. Do
   not "fix" it to match the schedule. **The guard does NOT see interactive sessions**: check
   `git -C C:\Users\imarl\panscriptum-export log --oneline -5` and `ls -lt src/*.py | head`
   before writing anything.
5. **A SHARED LOG IS NOT A LIVENESS SIGNAL — ASK WHO ELSE CAN WRITE THAT FILE.**
6. **AGE `data/COVERAGE.json` BEFORE BELIEVING ANY COVERAGE STALL.** Under 0.5h → real; over →
   artefact. **Run #25 proved the general case:** `cited`/`settled`/`feats` come from
   `COVERAGE.json` (written once per full supervisor cycle) while `entities read`/`chunks` come
   from a live glob and a live log tail. `dashboard.movement()`'s stall flag at **`:362`** applies
   ONE rule to all six regardless of source cadence, so the three coverage-derived metrics read
   "stalled" on every run where a cycle has not closed. **That is not a stall. Check the file age
   before opening an investigation.**
7. **AGE EVERY `bucket_state.last_error` ROW AND READ THE TEXT.** Rows 27–37 HOURS old are not
   evidence about now. `provider_error()`'s 180s window exists for exactly this.
8. **AGE EVERY FILE A STANDARD READS — ESPECIALLY WHEN IT READS GREEN.** A stale file producing a
   false ALL-CLEAR is never looked at again. **Ask of every green high-severity standard: how old
   is the evidence?** Run #25's case: `no high-severity findings open` reads 0 from an auditor
   with four proven blind spots (m133).
9. **A CHECK THAT CANNOT FAIL LOOKS EXACTLY LIKE A CHECK THAT PASSED.** When something has never
   once failed, that is the finding.
10. **A GUARD CAN FAIL BY DOING THE THING IT PREVENTS.** Run #24's shape: `write_record`
    overwrote the disk copy it could not read; the unrecognised ledger buried the unknown it was
    built to surface. **Read every `except` above a write and ask what the variable being written
    still holds.**
11. **A BARE NUMBER IN A LOG IS NOT A DIAGNOSIS.** `overnight.name_rc()` now supplies a
    vocabulary for process exit codes — and run #25 verified it against live codes, it is
    correct. **Anywhere the code prints a raw code, ask whether anything can say what it MEANS.**
12. **[NEW, RUN #25] A GUARD THAT MATCHES ONLY THE UNOBFUSCATED SPELLING IS GREEN ON PURPOSE,
    FOR EVER — AND EVERY ALTERNATIVE SPELLING IS A FRESH HOLE.** Lesson 9 sharpened, and worse
    than lesson 10: an inverting guard at least fires. Three of this run's seven fixes are this
    shape and **all three had already been "fixed" once, stopping one letter short**:
    - §20e forbade unguarded spawns by matching the literal name `subprocess`; the one unguarded
      spawn in the tree was in `verify_math.py` itself via `import subprocess as _sp20a`, plus
      two more in `standards.py`. Nine runs of green. (m126/m127)
    - m113 case-folded `local_agent`'s denylist but left `modname` deriving through a
      case-SENSITIVE `.endswith(".py")`, so `src/foreman.PY` skipped it entirely. **Bypass four.**
      (m128)
    - The pool ledger had no name for "answered with nothing", and Cascade says it two ways, so
      one fault held two permanent rows. (m132)
    **Ask of every guard: what are the OTHER spellings of the thing this forbids?** Case, alias,
    encoding, separator, wording. And when you fix one, check the test that decides whether the
    guard runs at all — that is where all three of these survived.
13. **[NEW, RUN #25] DO NOT MATCH PROCESSES BY A LITERAL YOUR OWN COMMAND LINE CONTAINS.**
    I bounced two jobs by matching command lines against a list holding `"dashboard.py"` and
    `"foreman.py"` — strings my own `python -c` command line also contained, so the script
    SIGTERMed itself. No project job was lost, but **`foreman.kill_stalled_job` documents having
    fixed this exact class in its own matching, and the remedy — `lognames.OWNER`'s declared
    per-job fragment — was sitting right there.** Assemble the needle at runtime (`'CW.' +
    'cat' + 'alogue'`) or use `lognames.OWNER`. Never a bare literal.

## 1. Verify first

1. **[THE `TerminateProcess(-1)` MYSTERY IS NOW A PROVEN NEGATIVE INSIDE THIS REPO. TAKE IT
   OUTSIDE.]** Run #24's top item is closed as far as `src/` can close it. **Verified by direct
   experiment on this machine:** `Popen.kill()` → rc 1, `taskkill /F` → rc 1,
   `psutil.Process.kill()` → rc 15, `os.kill(pid, SIGTERM)` → rc 15. **Only a raw
   `ctypes.TerminateProcess(h, 0xFFFFFFFF)` reproduces `4294967295`, and no such call exists
   anywhere in the tree.** `read.py` spawns no children at all, its `main()` returns only 0, and
   there is no Job Object code. **The two remaining candidates are both external:**
   - AV/EDR (Norton is known to intercept on this machine).
   - **A console-control-event propagating to children** spawned with `CREATE_NO_WINDOW` but no
     `DETACHED_PROCESS` and no new process group — `overnight.py:187,238`. **This is the one to
     test next, and it is testable.** If it is right, the fix is a process-group flag.
   ```
   grep "read: finished\|read: starting" state/overnight.log | tail -20
   ```
2. **[IS THE POOL LEDGER STILL 12, AND STILL THE RIGHT 12?]** **New baseline: 12 open, ALL of
   them the deliberately-loud `All 1 candidates failed` shape.** m132 named the empty-completion
   class, so the genuine-unknown slot is now empty — **any row that is not that shape is new and
   is the run's first job.**
   ```
   python -c "import sys;sys.path.insert(0,'src');import cascade_bridge as C;r=C.unrecognised_open();print(len(r),'rows');[print(' ',x['bucket'],'|',x['error'][:90]) for x in r]"
   ```
3. **[BASELINES — a second failure is the finding.]** `verify_math` is now **716 passed, 0
   FAILED** (was 697; §20j added 19). **And COUNT THE STANDARDS: 40 is the number.** Run #25
   found 39 with `every declared floor is measured` still reading "all measured" (m137) — a
   HIGH standard that did not emit is invisible to the meta-standard that audits floors.
   **Diff the standard NAMES against the previous snapshot, not just the red list** — that
   comparison is the only thing that caught it. `health.py --preflight` baseline is **1 FAIL**, `caches
   empty ... feats/www_dandwiki_com` (**M1**). `allsweep` baseline is **0 subsystems in a bad
   state**. pyflakes clean.
4. **[DID THE CATALOGUE FIX HOLD?]** m129's whole point is that the pass now survives its biggest
   sources. **Check that `recatalogue` is UP and that DC/Marvel/Gundam are progressing**, and
   that `every source is fully catalogued` has moved off 17.2%:
   ```
   tail -20 state/recatalogue.log
   grep -c "kill_stalled_job" state/foreman.log
   ```
   **If `recatalogue` is being killed again, the cadence is wrong or a new silent stretch
   exists** — find which phase went quiet before touching `PROGRESS_EVERY_S`.
5. **[Is the GPU lane still producing tokens?]** m99's root cause is still not established and it
   will recur. `/api/ps` and `/api/tags` read green through the entire wedge — **only a completed
   generation proves it.** Run #25 measured the mechanism: `gpu_lane`'s heartbeat proves the
   wrapping thread is alive, not that the call is progressing, and **a 1-byte/sec trickle defeats
   a `timeout=2` urllib call entirely** because Python socket timeouts are per-`recv()`
   inactivity, not a total deadline. See §3.
6. **[M15 is still open and still costs laps.]** `read.py` is outside the keeper's `STANDING` set
   (`overnight.py:372-389`); worst-case downtime **re-measured at ~6h** this run (roll 4h +
   pipeline 2h, `:707` and `:711-712`). **And it is not only the reader:** `catalogue_web.py
   --recatalogue` and `magnitude.py --calibrate` are outside `STANDING` too, and run #25 found
   both being killed repeatedly (m129).

## 2. Owner decisions — these are the queue's real content

**A. [M18 — MAJOR, LIVE, unchanged] `axis_score()` returns a flat 9.9 at M10 for every input.**
Live through `magnitude.py:244` → `assay_entity()`. `ledger.py:127-133` answers the same question
incompatibly — at the last band `hi == lo`, so `joules` collapses to the floor **regardless of
`ruin_score`**. Same shape: `assay.INSTRUMENT_WINDOWS` collapses to `(30, 30)` for **M5–M10**, so
`instrument()` prints a flat 30 for scores 0.5 and 9.9 alike. **Run #25 widened the inventory to
9 silent ladder-edge resolutions in `assay.py`** (§3), including `band_for_quantity()`'s
bottom-of-ladder collapse where ruin 1, 50 and 100 all print "M0". **Either resolution changes
computed magnitudes across the library — a charter question, not a repair.**

**B. [ROUTING POLICY] Should a refusal cost a bucket a cooldown?** Unchanged. A recognised
throttle takes **zero** cooldown and is instantly re-claimable. **Run #25 adds a third case to
the same question:** `empty_content` is now a named class that also does not bench. Sub-questions:
a **daily or monthly exhaustion** is not a passing 429 and will refuse until the window rolls; a
bucket that reliably returns prose instead of JSON (m96) is never benched at all; a bucket
returning empty completions repeatedly (`groq/compound-mini`) is now named but unpenalised.
Benching on one transient blip is how a thin pool gets thinner. **Your call.**

**B2. [ACTION, NOT A RULING: THREE BUCKETS HOLD DEAD CREDENTIALS.]** Unchanged from run #24, all
rows fresh: `cloudflare:free` → `HTTP 401 Authentication error`; `hyperbolic:free` → `HTTP 401
Could not validate credentials`; `zai:free` → `Insufficient balance or no resource package`.
**Config is `C:\Users\imarl\cascade\config.json` — the Cascade project, not this repo.**

**B3. [NEW — EXTERNAL BUG, NOT IN THIS REPO] CASCADE MISATTRIBUTES WHICH BUCKET FAILED.**
The ledger holds `gemini:models/gemini-2.5-flash | all 1 candidates failed: llama 3.3 70b (groq)`
— a Gemini bucket naming a Groq model. Traced to Cascade's `router.py:327-338`: `candidates()`
appends the whole pool as fallback even for a pinned model, and drops the pin entirely if it is
not `provider_ready()` at that instant, so the engine silently substitutes another provider while
`cascade_bridge` records the failure under the bucket it *reserved*. **This falsifies
`cascade_bridge.py:398-402`'s own stated assumption** that pin and attempt always agree on those
rows — worth a comment there even though the fix is in Cascade.

**C. [SECURITY-ADJACENT — unchanged, re-verified independently run #25] `publish.py` scrubs only
`state.json`.** `sync_tree()`'s bulk copy of `src/`, `prompts/`, `reference/`,
`registry_terminal/`, `handoff/` and `config.yaml` — all pushed to a **public** repo — has **zero
content scrubbing**, while the docstring's "carries no keys" reads as though it covered
everything. **A run #25 agent re-scanned every synced path against 8 key-shaped patterns, AWS
keys, PEM headers and URL credentials and found no live secret**, independently of run #24.
Either extend the scrub to the whole synced tree or narrow the docstring's claim.

**D. [m106 — THE ROOT OF FOUR BUGS] `endpoint.py:200-233`'s return contract.** `fetch_raw()`
returns an identical `(t, None)` for a confirmed 404/410, an HTTP refusal, an exception, and an
HTML error body, so **no caller can tell "absent" from "request failed"**. M16, m93, m94 and m107
are symptoms. `detect()` (`:126-173`) compounds it by caching a timeout as `MODE_DEAD` for 24h.
Misled callers, re-confirmed run #25 with **one newly traced**: `feats.py:437`,
`hostcheck.py:135`, `:246`; `feats.py:345,436`, `hostcheck.py:134,245`; and **NEW —
`completeness.py:194-203,259,268`, where `host_reachable()` gates on `endpoint.api_url()` which
is API-mode-only, so every RAW-mode host reports `coverage: 0.0` / "unreachable" even when
perfectly readable** (reproduced live against `www.dandwiki.com`). **One ruling settles all five.**

**E. [m90, unchanged] Four hand-copied copies of the attestation→uncertainty rule.**
`custodes.py:229-230`'s `_ATT_BASE` **claims to be derived** and is a byte-for-byte hand-typed
copy of `assay.py:630-631`, no import linking them. **Values re-checked numerically run #25 and
still identical** — checked, because the day they drift silently is the day this becomes live.

**F. [Hard Rule 0 — open caps, each needing a judgment call]** `wiki_source.py:352`
`all_categories(hard_stop=6000)` — **now MEASURED against the live API: DC has 10,460 qualifying
categories, 4,460 past the cap, cutting alphabetically at "Joseph Sulman/Penciler" and starving
discovery for every non-Persons class on the largest wikis** (m136). The fix is continuation to
exhaustion, the pattern `category_members()` already uses, not a bigger number.
Also: `feats.py:311-368` `aplimit=500`/`srlimit=50` truncate when MediaWiki signals `continue`
and the continuation loop was never added; `hosts.py:152-157` truncates candidate hosts at
`per_source=24` **before verification**; `cosmology_graph.py:86-87` caps `pair_shared` at 8 and
`resonance.py:146` consumes it as **real evidence** (note `weave.py` fixed this same cap but wrote
to a *different* file `resonance.py` does not read — and run #25 found a **third** consumer,
`propagation.py:46`); `scope.py:68-81` `srlimit=3`×4 plus `titles[:8]`; `retry_synthesis.py:60`
`sorted(...)[:14]`; `pipeline.py:673` `rest[:14]`; `weave.py:205-226` `max_sources=60`;
`ingest_doc.py:216` `description[:2000]`; `rosetta.py:194` `srlimit=5`; `wiki_source.py:392-406`
`min_pages=40` silently hides small real categories from discovery on every wiki;
`foreman.py:1205` `sorted(...)[:3]` patch selection with no rotation (findings ranked 4th+ starve
forever); `foreman.py:192` `SC.sweep(limit=4)` re-attempts the same top-4 sources every round.

**G. [m91 — NOT IN THIS REPO, AND STILL LIVE] The pool spends calls on Ollama models that are not
installed.** 8 stale references, `qwen3:8b` the only installed model. `state/read_auto.log`
confirms the reader 404-removing `llama3.1:latest`, `qwen2.5:14b`, `gemma3:12b`,
`qwen3:30b-a3b-*` on **every start**. Config is `C:\Users\imarl\cascade\config.json`.
**The GPU fallback itself is FINE — do not "fix" the fallback.**

**H. [NEW — m133, MAJOR] REPAIRING THE AUDITOR CHANGES WHAT THE PROJECT BELIEVES ABOUT ITSELF.**
`overwatch.py` reports **0 high-severity findings open** over 75 rounds and that zero is an
undercount baked in four ways, each proved by execution (see BUGS.md m133). Fixing any of them
will surface a backlog of real findings at once, and the reconcile filter's whitelist encodes
someone's judgment about what belongs on WATCH.md. **That is a deliberate pass with a decision in
it — "how much do we want to see?" — not an end-of-run patch. Your call on when.**

**I. [NEW — m135] SHOULD `sources with a reachable wiki` HAVE A 100% FLOOR AT ALL?**
Verified live: **15 sources are genuinely without a wiki anywhere** (1,479 entries) — one-author
homebrew, a Rush album, a screenplay, Kobold Press books. The standard therefore **cannot** reach
its floor, and its remedy re-runs the full search from scratch every ~10 minutes for ever, because
`adopt()` never records the "genuinely hostless" verdict its own docstring promises
(`hostcheck.py:846-910`; `data/HOST_UNFIT.json` is empty after three days). **Two questions:**
(a) build the memory so a settled negative is recorded and the search stops repeating — this is
new machinery; (b) should the floor exclude sources with no wiki anywhere, so the standard can go
green when the work is genuinely done? **A permanently-red standard is noise, and noise is how a
real breach gets missed.**

## 3. The sweep's unworked findings — verified by agent, unverified by me, and this is next run's work

*Full detail with quoted code in `handoff/sweep25/AUDIT_batch01..16.md`. Ordered by blast radius.
**Verify at source before touching anything** — the agents were right on every finding I checked
this run, including two that contradicted my own opening hypothesis in useful ways, but they are
not infallible and have been wrong in both directions before.*

**The ones I would take first:**

- **`dashboard.py:335-349` — concurrent pollers corrupt the history file and the Movement panel
  then goes SILENTLY AND PERMANENTLY BLANK** (m134 — **reproduced live**, 8 threads,
  `JSONDecodeError`, no self-heal). This is the page that opens every run. Also `:341-342`,
  `HISTORY[-2000:]` drops below the 30-min stall window at ~6 concurrent pollers (measured);
  `:332,420-425`, a `standards.check()` crash renders as a fabricated **"-N" regression** rather
  than a computation failure; `:150-168`, `throughput()` returns the same zero-calls dict for a
  broken DB as for genuine quiet, unlike its sibling `quotas()`; and **`:362`'s stall flag
  applies one rule to six metrics with different source cadences** (lesson 6).
- **`gpu_lane.py:326-455` — a wedged call can hold a GPU slot forever.** `_heartbeat()` refreshes
  the lease off a wall-clock timer with **zero connection to whether the wrapped call is
  progressing** — it proves only that the wrapping thread has not exited. **Measured this run:**
  a server trickling 1 byte/sec for 20s defeated a `timeout=2` urllib call entirely, because
  Python socket timeouts are per-`recv()` inactivity and not a total deadline — so anything
  keeping a byte moving (proxy, AV TLS interception, keepalive) holds a slot for the caller's
  full timeout, **up to 30 min**, with every probe green. **This is the mechanism behind m99.**
  **Minimal fix:** stream the response and touch the lease on each received chunk, so the lease
  is evidence the CALL is progressing; failing that, bound the heartbeat's own duration
  independently of the caller's HTTP timeout. Also `:66-67`, unguarded
  `int(os.environ.get(...))` raises at import, contradicting the module's own "fail open,
  always" — **and `read.py:283-284` has the identical bug.**
- **The 32 `write_json` call sites tree-wide that IGNORE THE RETURN VALUE** (full list in batch
  06's report), plus ~14 more ignoring `replace_retry`'s. **Run #25 fixed the four that then
  marked work as done** (m131); the rest still print success for writes that never landed.
  Newly named instances: `coverage.py:185-186`, `grounding.py:239-240`, `zfighters.py:478`,
  `pantheon.py:261`, `genre.py:241`, `cosmology_graph.py:141-149`, `resync_roll.py:68`,
  `navtree.py:263`, `scope.py:119`.
- **`local_agent.py:407-438` — the backup the docstring promises is NEVER WRITTEN TO DISK.** It
  lives only in a Python variable, so a hard process kill mid-gate leaves the patched module
  corrupt with **no recoverable backup anywhere**. This is the one module where a gap means
  unreviewed model-written code lands in `src/`; m128 closed the fourth bypass, **this is the
  next thing wrong with the same file.**
- **`foreman.py:990-997` — the model-patch write to a LIVE `src/*.py` is non-atomic**, and this
  run **reproduced a concurrent reader hitting `SyntaxError` on 129 of 300 polls** during a
  simulated write. Also `:801-808`, `_function_source()` matches a symbol by **bare name** via
  `ast.walk`, discarding class qualification — **reproduced**: requesting `"B.compute"` returned
  `A.compute`'s body. And `:990`'s backup filename is 1-second granular and can collide.
- **`overwatch.py`'s four blind spots** — see m133 / §2 H.
- **`standards.py:560-586`** — the unanswered-records glob loop has no per-file `try/except`, so
  ONE file error (e.g. `read.py`'s own corrupt-cache self-heal deleting a file mid-scan) aborts
  the loop and **caches a partial undercount as the true value** for a HIGH-severity
  zero-tolerance standard. **`:670-682`** — the assay-band check builds "mine" from the charter's
  own band digit rather than the computed `reference.magnitude`, so it **cannot detect band-level
  drift at all** (reproduced: a simulated M7→M8 drift reads as "inside interval").
  **`:904-907`** — the job-progress write uses a fixed tmp name from multiple concurrent
  processes on a 5s poll. **`:829-836`** — an empty glob defaults `newest_rec=0.0`, reading as a
  false "fresh".
- **`runguard.py:72-80`** — `_land()`'s fixed tmp filename lets two racing processes crash the
  loser with an **uncaught `FileNotFoundError`**, contradicting the module's own "never raises"
  docstring (**reproduced live**; `replace_retry` catches only `PermissionError`). Not covered by
  verify_math's 15 §19k checks, which are single-process. **The same `FileNotFoundError`-through-
  `except PermissionError` hole is live in `magnitude.py:911-996`.**
- **`feats.py:376-424` — `resolve_title()`/`_page_exists()` are fully written and NEVER CALLED**
  (grepped tree-wide). The documented 17,148-entry fix is dead code (= known m80). Circumstantial
  reading favours LOST over withheld. **`feats.py:120-299`** — `api()`/`alive()` return `None`
  for both absence and timeout and `resolve_hosts()` caches it via a MEMBERSHIP test, so one blip
  loses a source for ever: **`data/WIKI_HOSTS.json` currently holds 7 null entries.**
- **`assay.py`'s 9 silent ladder-edge resolutions** (§2 A), of which these are new: `:226`'s
  unscored-collapse guard is dead code; `:502-503`'s `else "V"` branch is unreachable given
  LADDER; `:424`'s `denom = ... or 1.0` is unreachable; `:242-248`'s `band_for_quantity()`
  collapses at the BOTTOM (ruin 1, 50 and 100 all print "M0"); `:630-631` vs `:343` default an
  unknown attestation to 0.30 rather than the safe ceiling `_interval()` uses.
- **`sweep_plan.record()`'s cross-process lost-update, now EMPIRICALLY REPRODUCED** with two real
  processes: `missing(run)` **can never fabricate coverage but can silently under-report**, so a
  "nothing missing" result is trustworthy and a non-empty one is not, on its own. **Keep
  recording coverage from ONE process gated on the report files** until `record()` uses a
  cross-process lock or an append-only log — or delete the docstring's claim.
- **`sweep.py:233-234`** — bare `open(OUT,"w")+json.dump` on `data/CHARACTER_SWEEP.json`, a live
  **13 MB** file read by `hostcheck`, `magnitude` and `standards` and rebuilt as an independent
  OS process by `foreman.py:600-611`.
- **`health.py:124-144`** — `flush()`'s SAMPLES write ends in a bare `except: pass` with no
  self-heal, in the module whose purpose is "no silent failures". **`:179-181`** hardcodes
  chars-per-token as `/4` and `/3.7` instead of importing `context_budget.py`'s `3.0`/`4.0` —
  **the 3.7 is more permissive than the real 3.0, so preflight can pass jobs the real budget
  refuses.** `:241`'s cache sample uses an unsorted glob, unlike its sibling.
- **`overnight.py:414-455`** — `coverage_snapshot()`/`preflight()` never check subprocess
  `.returncode`, so a crashed `coverage.py` or `health.py` re-reports stale data as a fresh pass.
  **`:410`** — `name_rc()`'s docstring misattributes SIGTERM-15 to psutil; the real mechanism is
  `os.kill` in `foreman.py`.
- **`autostart.py:103-200`** — `start_supervisor()` logs "supervisor started" unconditionally even
  if `overnight.py` dies on startup; this is the process that brings the whole stack up. **A 1.5s
  poll would catch an immediate crash where 0s does not** (measured). **`:121-145`** —
  `_twin_watchdog()` fails OPEN ("no twin") on any process-query error, defeating the exact
  multi-watchdog storm its own docstring warns about.
- **`build_terminal.py:468,487,503,524`** — `nd.name` spliced into `innerHTML` UNESCAPED at
  multiple call sites, contradicting the file's own `esc()` invariant. Data is wiki-sourced, not
  live-attacker — **which is still arbitrary text from the public internet.**
- **`catalogue_codex.py:159` — 70 codex elements silently miscategorised**, verified against the
  owner's real file; **`catalogue_aurora.py:92` inherits the same fallback: 49 of 5,861 Aurora
  elements land in THINGS** (36 companion action, 7 weapon property, 5 race variant, 1 background
  variant). One root cause, two files.
- **`completeness.py:66-119`** unguarded global dict mutated and `json.dump`-iterated across
  ThreadPoolExecutor workers, plus a fixed non-unique temp filename shared across those workers.
  (`land()` at `:342-407` is correctly guarded — worth noting.)
- **`backfill.py:84-94`** — `roster()` skips the entire subcategory walk whenever the top-level
  listing already has ≥40 members, **silently dropping subcategory-only characters** — the exact
  bug class this file exists to fix. (m130 fixed its *writer*; this is still open.)
- **`feats_index.py:148` — hyphenated hosts stranded, four confirmed live** (`date-a-live`,
  `sakamoto-days`, `the-amazing-digital-circus`, `uncle-grandpa`). `host_dir.replace("_", ".")`
  is irreversible; the correct host is **already in `rec["host"]`**.
- **`ingest_doc.py:record_path()`** — ambiguous containment match silently misroutes (verified
  live: "Fallout" → `all-fallout.json`). **`:98-99`** non-atomic pages.json write.
- **`style_audit.py:38-39`** — `TURN_ENDING` compiled with `re.M` so `$` matches any internal
  line end, inflating the "ending on a turn" metric (reproduced).
- **`descending_ladder.py:85-95`** — `rung_for_length()` silently returns "Continental" (rung 0)
  for ANY length above 1e6 m, **including 1e30 m** (verified live). Currently dormant — no caller
  yet — and **marked CLEAN by run #24**, which is a useful reminder that "clean" is per-reader.
- **`coverage.py:16-18` vs `:82-115`** — the docstring promises an `UNREACHABLE` state
  distinguishing fetch failure from real absence; the code never implements it.
- **`read.py:1097-1098`** — the final "done" summary omits `unanswered`/chunks/`_FELL_BACK`, so a
  catastrophically incomplete run prints the same banner as a healthy one.
- **`pipeline.py:397-408`** — `records()` silently drops any record file that fails to parse; that
  source then vanishes from every phase and from `coverage.py`/`grounding.py` with no trail.
- **`retry_synthesis.py:56-60`** — the docstring's "byte-identical to `phase_synthesis`" claim is
  **false** (the real one ranks by feats-present and paginates ALL feat-bearing entries; this
  sorts by raw description length and takes one slice). `:43-47,109-112` also write
  `data/records/*.json` directly with no runtime guard enforcing "pipeline must be stopped".
- **`hosts.py:44-50`** — `_load()` resets to `{}` on any read failure, indistinguishable from
  genuinely empty; `:78-91` fixed tmp name + no retry + read-modify-write race.
- **`scout.py:107-114`** (`_ask()` swallows all exceptions to `None`, indistinguishable from "no
  URLs known"), `:200-206` (race on `WIKI_HOSTS.json` — **confirmed the same file as
  `feats.HOSTS`, ≥4 write sites across two modules**), `:256-262` (corrupt `SCOUT.json` →
  `prev=[]` → permanent history loss on the next write).
- **`profile.py:129-138`** — a failed `GENRES.json`/`TIERS.json` load silently defaults **every**
  world's genre, indistinguishable from real data.
- **`sevenfold.py:198-202`** — a silent `continue` drops a source's entire world list when
  `weave`'s filtered index and `pipeline.records()`'s source names diverge.
- **`onomast.py:311-356`** — `register_for()`'s genre/feature voting is **dead**; the sole caller
  passes only `group_id`.
- **`endpoint.py:83-94` and `:356-370`** — `_save()`/`register()` do unguarded read-modify-writes
  on shared JSON with bare `.tmp` names and unretried `os.replace`; `register()`'s uncaught write
  exception **aborts scout.py's whole sweep loop**.
- **`derivation.py:476-477`** — `SCAN_MODULES` omits `pantheon.py` and `zfighters.py`, both of
  which hold free-parameter dicts (`GODS`, `ROSTER`) invisible to the "where constants live" scan.
- **`anchors.py:215`** — the `order` list puts Yggdrasil (M6) before Goku (M5), so the
  monotonicity check fires **every run regardless of instrument health**.
- **`tells.py:70`** — regex alternation precedence: the trailing `but` requirement applies to only
  one alternative, so bare "not merely"/"not simply" false-positive (re-verified by execution).
- **Non-atomic shared writes still open:** `build_terminal.py:572-573`, `burgs.py:227`,
  `module_index.py:75-76`, `overnight.py:462`, `publish.py:261-263` and `:283-290`,
  `render.py:245`, `generate.py:382-384` (**live process, and `catalog.py:92-94` reads it
  mid-write**), `worldseed.py:317-322`, `wh40k.py:230-231`, `manifest_builder.py:436,455,463`,
  `catalogue_web.py:70-79`, `pipeline.py:1327`, `rosetta.py:364-366,377-378` (**this file already
  lost a 3,514-row mine once to exactly this**), `sweep.py:233-234`.
- **Unguarded read-modify-write on `data/SWEEP_ROLL.json` (five writers):** `resync_roll.py:33-68`
  (now atomic, still racy; its "safe to run at any time" conflates the two),
  `catalogue_aurora.py:107-150`, `catalogue_codex.py:122-203`.
- **Smaller, verified:** `identity.py:180-207` (`_is_continuity()` requires n≥2 so its own worked
  example can never classify), `:219` and `coverage.py:73` (fixed tmp names);
  `chain.py:353` (unguarded `Counter` increment outside the lock two lines below);
  `burgs.py:76` (`GENERATORS` dict is dead code) and `:230` (message says "sample of 50 worlds",
  code writes all); `sweep.py:20-22` (docstring claims a strict funnel the code does not produce);
  `address_space.py:127-139` (comment says hyperverse/xenoverse are NOT fields, the FIELDS list
  one line below makes them the first two) and `:3,26-27` (header claims 74 bits / 10 bytes / 5
  fields; live run gives **89 / 12 / 8**) and `:172-183` (docstring says H/X print as `?`, code
  prints real ints — an untiered world prints "H0 › X0");
  `repass_bands.py:91` (hardcoded `"of 211"`); `module_index.py:2` (docstring says 87 modules,
  actual 95); `standards.py:966-982` (`fandom_ipv4_reachable()` does a live TCP connect, up to
  8s, with no TTL cache, on a path the dashboard polls every 5s);
  `recover_folder_records.py:143-150` (bypasses `write_record_catalogue`'s merge — m131 fixed the
  *gating*, the routing question remains); `zfighters.py:434-440` (Goku silently drops from the
  roster on any presence-file load failure); `custodes.py:254` (unknown attestation grade defaults
  to MID quality 0.4, not worst-case); `resonance.py:71-79` (fixed 600-iteration Gauss-Seidel with
  no convergence check) and `:74-76` (unreachable dead code, proven by instrumentation);
  `pick_model.py:295` (`total_vram_gb() or 10.0` silently assumes a 10GB card when nvidia-smi is
  unreachable, undermining the GPU-only ruling); `weave.py:156-273` (`pair_weights()`/
  `null_threshold()` are dead code); `rosetta.py:394` (`P.__dict__.get("_x", 0)` is a vestigial
  no-op); `catalogue_codex.py:130-136` (loose two-way substring section matching) and `:75`
  (60-char slug truncation with no collision guard, currently AT the cap);
  `cleanup.py:174-177` (`thin_description` sets the flag but never `changed`, so `--apply`
  reports the record as marked and never writes it); **stale `silence.note()` line tags** across
  `pipeline.py:404,539,629,646`, `foreman.py`, `feats.py:159,171,451,743,878`, `scout.py`,
  `magnitude.py:235`, `weave_index.py:197`, `catalogue_web.py:97,274`.

**Modules read end to end and found CLEAN this run** (a clean module is a real result):
`tuning.py`, `propagation.py`, `context_budget.py`, `tiers.py`, `catalog.py`, `address.py`,
`estate.py`, `allsweep.py`, `rigor.py`, `reference.py`, `handbuilt.py`, `physics.py`,
`cosmography.py`, `thread_integrity.py`, `compress_store.py`, `weave.py`, `tempus.py`,
`chord_field.py`, `scale_theories.py`, `catalogue_models.py`, `lognames.py`, `entity_match.py`,
`audit.py`.

## 4. Audit rotation — ABOLISHED

No rotation. `state/SWEEP_COVERAGE.json` records which run last read each module and
`sweep_plan.missing(run)` is the completeness proof — **but see §3: its cross-process race is now
empirically reproduced, so record coverage from ONE process gated on the report files' existence
and size, which is a stronger proof than the agents' own claims.** Run #25 did exactly that:
16/16 reports on disk, 13.9–23.4 KB each, 95 modules recorded, `missing("run25")` → 0.

**Method that has now worked seven times:** bound the file set, demand `file.py:LINE` citations
and an explicit VERIFIED/UNVERIFIED label, tell the agent a clean module is a worthwhile result,
and make it write the long report to disk and return only a summary. **Point at least one agent
at the code the supervisor wrote that same session** — that has caught real defects in the
supervisor's own work four runs running, and this run it was batch 01 catching the console-window
spawn inside `verify_math.py` and batch 02 catching the un-gated callers of run #24's own fix.
**Give the agents the live red standards as questions**, not just files: run #25 asked "why is
this standard red?" of four batches and got four causal answers, three of which no single-module
read would have produced.
