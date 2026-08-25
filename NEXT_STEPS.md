# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #24 wrote this on 2026-08-25 ~05:1x local.*

**THE THREE OWNER RULINGS OF 2026-08-25 STILL SHAPE THE RUN. Read these first.**

1. **EVERYTHING AMISS IS INVESTIGATED THE MOMENT IT IS SPOTTED** — worked on sight, never filed
   for later. **What is allowed to survive into this file is what needs an OWNER RULING**
   (a charter question, a routing-policy choice, a contract change with real blast radius), plus
   the sweep's verified-but-unrepaired tail in §3, which is REAL WORK, not a backlog of excuses.
2. **THEN, IMMEDIATELY: THE FULL COMPREHENSIVE SWEEP — every line of every module, every run.**
   `python src/sweep_plan.py --batches 16`, one sonnet-tier agent per batch, all launched
   together; each writes its full report to `handoff/sweep<N>/AUDIT_batchNN.md` and returns **only
   a compact summary**. Then `sweep_plan.missing("run<N>")` **proves** coverage.
   **Run #24's pass: 95 modules, 39,865 lines, 0 uncovered, 16 reports on disk.**
3. **AN UNRECOGNISED FAILURE IS A BUG, NOT WEATHER.** If `every pool failure is recognised` is
   red, it is the run's first job. **Read the ledger before believing its size** — see lesson 8.

**And the standing lessons. 10 and 11 are new and 11 is this run's whole spine.**

4. **VERIFY THE CADENCE WITH `list_scheduled_tasks`. NEVER FROM A FILE, INCLUDING THIS ONE.**
   Hourly, `11 * * * *` + 523s jitter, firing ~:19–:20 (read back 2026-08-25). The **15 minutes in
   the overlap guard is the heartbeat-staleness threshold** — a different number answering a
   different question. Do not "fix" it to match the schedule. **The guard does NOT see interactive
   sessions**: check `git -C C:\Users\imarl\panscriptum-export log --oneline -5` and
   `ls -lt src/*.py | head` before writing anything.
5. **A SHARED LOG IS NOT A LIVENESS SIGNAL — ASK WHO ELSE CAN WRITE THAT FILE.**
6. **AGE `data/COVERAGE.json` BEFORE BELIEVING ANY COVERAGE STALL.** Under 0.5h → real; over →
   artifact. `dashboard.py`'s stall flag is at **:362**.
7. **AGE EVERY `bucket_state.last_error` ROW AND READ THE TEXT.** Rows 27–37 HOURS old are not
   evidence about now. `provider_error()`'s 180s window exists for exactly this.
8. **AGE EVERY FILE A STANDARD READS — ESPECIALLY WHEN IT READS GREEN.** A stale file producing a
   false ALL-CLEAR is never looked at again (m112). **Ask of every green high-severity standard:
   how old is the evidence?**
9. **A CHECK THAT CANNOT FAIL LOOKS EXACTLY LIKE A CHECK THAT PASSED.** When something has never
   once failed, that is the finding.
10. **[NEW, RUN #24] A GUARD CAN FAIL BY DOING THE THING IT PREVENTS.** Lesson 9 sharpened, and
    four of this run's eight fixes are this shape. These checks *could* fail — and on the failure
    path they performed the exact harm they existed to stop: `write_record` overwrote the disk
    copy it could not read (m119), `write_record_catalogue` dropped the cast it could not merge
    (m120), the unrecognised ledger buried the unknown it was built to surface (m118), the
    denylist admitted the file it was built to deny (m121). **A guard that merely does nothing is
    visible eventually; a guard that INVERTS on its error path is invisible forever, because the
    damage looks like ordinary operation.** Read every `except` above a write and ask what the
    variable being written still holds.
11. **[NEW, RUN #24] A BARE NUMBER IN A LOG IS NOT A DIAGNOSIS, AND A GUESS ABOUT ONE IS NOT
    TESTABLE.** Run #23 filed `read.py`'s `rc=4294967295` as a harmless process bounce on
    timestamp correlation; the third occurrence disproved it. The pool side had a vocabulary for
    unnameable failures and the JOB side had none. `overnight.name_rc()` now supplies one.
    **Anywhere the code prints a raw code, ask whether anything can say what it MEANS.**

## 1. Verify first

1. **[TOP ITEM — LIVE, UNIDENTIFIED, AND IT IS AN OUTAGE.] WHAT IS KILLING `read.py` WITH
   `TerminateProcess(-1)`?** Three consecutive exits (02:41, 02:50, 03:47 on 2026-08-25) after an
   unbroken history of `rc=15`. **Not a foreman remedy** (those exit 15), **not a Python crash**
   (those exit 1, and `read.py`'s `main()` returns only 0). The supervisor now NAMES the code, so
   the next occurrence is legible — read `state/overnight.log` for
   `read: finished rc=... (TerminateProcess(-1) from OUTSIDE this supervisor`.
   ```
   grep "read: finished\|read: starting" state/overnight.log | tail -20
   ```
   **Candidates not yet excluded:** something in the tree calling `TerminateProcess` with -1; an
   external watchdog; an OS/AV kill (Norton is known to intercept on this machine); a Job Object
   teardown when a parent console dies. **Do not file it as weather again.**
2. **[IS THE POOL LEDGER STILL 12, AND STILL THE RIGHT 12?]** m118 filters on read, so the count
   is now meaningful. Baseline: **12 open — 11 deliberate `All 1 candidates failed` rows + 1
   genuine unknown (`groq:groq/compound-mini: empty response`)**.
   ```
   python -c "import sys;sys.path.insert(0,'src');import cascade_bridge as C;r=C.unrecognised_open();print(len(r),'rows');[print(' ',x['bucket'],'|',x['error'][:90]) for x in r]"
   ```
   **A row that is neither of those two shapes is new and is the run's first job.**
3. **[preflight baseline is 1 FAIL. A SECOND is the finding.]** `caches empty ...
   feats/www_dandwiki_com` (**M1**). **`verify_math`'s baseline is now 697 passed, 0 FAILED.**
4. **[Is the GPU lane still producing tokens?]** m99's root cause is NOT established and it will
   recur. `/api/ps` and `/api/tags` read green through the entire wedge — **only a completed
   generation proves it.** The mechanism that lets it persist is `gpu_lane.py:326-455` (§3).
5. **[M15 is still open and still costs laps.]** `read.py` is outside the keeper's `STANDING` set
   (`overnight.py:372-389`), so a fast death leaves it down until the supervisor's main lap —
   **measured up to ~6h** (roll 4h + pipeline 2h) by run #24's sweep, worse than the 42 min
   previously recorded. Run #24 bounced the supervisor to recover a 75-minute outage.

## 2. Owner decisions — these are the queue's real content

**A. [M18 — MAJOR, LIVE, unchanged] `axis_score()` returns a flat 9.9 at M10 for every input.**
Live through `magnitude.py:244` → `assay_entity()` (`magnitude.py:706-711`), re-confirmed twice
more this run against real numbers (1 through 1e150 all return 9.9). `ledger.py:127-133` answers
the same question incompatibly — at the last band `hi == lo`, so `joules` collapses to the floor
**regardless of `ruin_score`** (run #24 executed it: identical joules for ruin_score 0/5/10).
**Either resolution changes computed magnitudes across the library — a charter question, not a
repair.** Same shape, and run #24 widened it: `assay.INSTRUMENT_WINDOWS` collapses to `(30, 30)`
for **M5–M9 as well as M10**, so `instrument()` prints a flat 30 for scores 0.5 and 9.9 alike.

**B. [ROUTING POLICY] Should a refusal cost a bucket a cooldown?** Unchanged from run #23: a
recognised throttle takes **zero** cooldown and is instantly re-claimable. Sub-questions: a
**daily or monthly exhaustion** is not a passing 429 and will refuse until the window rolls; a
bucket that reliably returns prose instead of JSON (m96) is never benched at all. Benching on one
transient blip is how a thin pool gets thinner. **Your call.**

**B2. [NEW — NOT A RULING, AN ACTION: THREE BUCKETS HOLD DEAD CREDENTIALS.]** Chased out of the
ledger as its order text instructs, all rows fresh: `cloudflare:free` → `HTTP 401 Authentication
error`; `hyperbolic:free` → `HTTP 401 Could not validate credentials`; `zai:free` →
`Insufficient balance or no resource package` (1113). These cannot fix themselves. **Config is
`C:\Users\imarl\cascade\config.json` — the Cascade project, not this repo. Re-key or remove.**

**C. [SECURITY-ADJACENT — unchanged, re-verified run #24] `publish.py` scrubs only `state.json`.**
`sync_tree()`'s bulk copy of `src/`, `prompts/`, `reference/`, `registry_terminal/`, `handoff/`
and `config.yaml` — all `git add -A`'d and pushed to a **public** repo — has **zero content
scrubbing**, while the docstring's "carries no keys" reads as though it covers everything. **A
run #24 agent re-scanned every synced path and found no live secret.** Either extend the scrub to
the whole synced tree or narrow the docstring's claim.

**D. [m106 — THE ROOT OF FOUR BUGS] `endpoint.py:200-233`'s return contract.** `fetch_raw()`
returns an identical `(t, None)` for a confirmed 404/410, an HTTP refusal, an exception, and an
HTML error body, so **no caller can tell "absent" from "request failed"**. M16, m93, m94 and m107
are symptoms. `detect()` (`:126-173`) compounds it by caching a timeout as `MODE_DEAD` for 24h.
Misled callers, re-confirmed run #24: `feats.py:437`, `hostcheck.py:135`, `:246` for `fetch_raw`;
`feats.py:345,436` and `hostcheck.py:134,245` for `detect`. **One ruling settles all four.**

**E. [m90, unchanged] Four hand-copied copies of the attestation→uncertainty rule.**
`custodes.py:229-230`'s `_ATT_BASE` **claims to be derived** and is a byte-for-byte hand-typed
copy of `assay.py:630-631`, no import linking them. **Values still identical as of run #24** —
checked, because the day they drift silently is the day this becomes a live bug.

**F. [Hard Rule 0 — open caps, each needing a judgment call]** `wiki_source.py:352`
`all_categories(hard_stop=6000)` caps **alphabetically** — run #24 confirmed the alphabetical
ordering against the **live MediaWiki API**, and 6000 is the number that once lost Superman;
`feats.py:311-368` `aplimit=500`/`srlimit=50` truncate when MediaWiki signals `continue` and the
continuation loop was never added (now *measured* via `_CAP_BOUND`, still not fixed);
`hosts.py:152-157` ranks candidate hosts then truncates at `per_source=24` **before verification**;
`cosmology_graph.py:86-87` caps `pair_shared` at 8 and `resonance.py:146` consumes it as **real
evidence** — note `weave.py` fixed this same cap but wrote the result to a *different* file
(`SHARED_STAGE_GRAPH_IDF.json`) that `resonance.py` does not read; `scope.py:68-81` `srlimit=3`×4
plus `titles[:8]` feeding the fiction-wide Magnitude ceiling; `retry_synthesis.py:60`
`sorted(...)[:14]`; `pipeline.py:673` `rest[:14]`; `weave.py:205-226` `max_sources=60`;
`ingest_doc.py:216` `description[:2000]`; `rosetta.py:194` `srlimit=5`;
`foreman.py:1205` `sorted(...)[:3]` patch selection with no rotation (findings ranked 4th+ starve
forever); `foreman.py:192` `SC.sweep(limit=4)` re-attempts the same top-4 sources every round.

**G. [m91 — NOT IN THIS REPO, AND STILL LIVE] The pool spends calls on Ollama models that are not
installed.** 8 stale references, `qwen3:8b` the only installed model. `state/read_auto.log`
confirms the reader 404-removing `llama3.1:latest`, `qwen2.5:14b`, `gemma3:12b`,
`qwen3:30b-a3b-*` on **every start**. Config is `C:\Users\imarl\cascade\config.json`.
**The GPU fallback itself is FINE — do not "fix" the fallback.**

## 3. The sweep's unworked findings — verified by agent, unverified by me, and this is next run's work

*Full detail with quoted code in `handoff/sweep24/AUDIT_batch01..16.md`. Ordered by blast radius.
**Verify at source before touching anything** — the agents were right on every finding I checked
this run, including three in code written within the previous two hours, but they are not
infallible and have been wrong in both directions before.*

**The ones I would take first:**

- **`local_agent.py:407-438` — the backup the docstring promises is NEVER WRITTEN TO DISK.** It
  lives only in a Python variable, so a hard process kill mid-gate leaves the patched module
  corrupt with **no recoverable backup anywhere**. This is the one module where a gap means
  unreviewed model-written code lands in `src/`; m121 closed the third bypass, this is the next.
- **`overwatch.py:650-656` — a closed or retired finding can NEVER REOPEN**, even if the identical
  defect returns, because the fid-already-in-ledger skip fires first. Combined with `:486-487`
  (`last_verified` bumped even when the verifying `_ask()` returned **None**, i.e. the check
  failed), the auto-triage queue can starve itself on no-op "checks".
- **`overwatch.py:326-329` — the reconcile filter still DROPS REAL FINDINGS.** The whitelist
  discards orphan-hosts, stale-coverage, orphan-cache-dirs and ghost-roster findings **and all
  seven of `allsweep.reconcile()`'s internal exception handlers** before they reach WATCH.md.
  (Batch 07 read `allsweep` itself and found those handlers DO record visible findings — so the
  loss is entirely in overwatch's filter, not in allsweep.) Also `:570-573`, WATCH.md's header
  count is uncapped while the printed list caps at 40, so the two diverge.
- **`feats.py:376-424` — `resolve_title()`/`_page_exists()` are fully written and NEVER CALLED.**
  The documented 17,148-entry fix is dead code (= known m80). Verify the call site was lost, not
  deliberately withheld.
- **`gpu_lane.py:326-455` — a wedged call can hold a GPU slot forever.** The heartbeat thread
  refreshes the lease independently of the wrapped model call, so a hung-but-alive Ollama request
  never trips staleness or PID-death. **This is the mechanism behind m99's persistence.** Also
  `:66-67`: unguarded `int(os.environ.get(...))` raises at import, contradicting the module's own
  "fail open, always". `generate.py` holds `gpu_lane.lane(...)` across every model call and is
  live right now.
- **`build_terminal.py:468,487,503,524` — `nd.name` spliced into `innerHTML` UNESCAPED** at three
  call sites, contradicting the file's own m10 `esc()` invariant.
- **`autostart.py:103-200` — `start_supervisor()` never re-verifies the start.** "supervisor
  started" is logged unconditionally even if `overnight.py` dies on startup. This is the process
  that brings the whole stack up, and run #24 relied on it to restore a bounced supervisor.
- **`sweep_plan.record()` — the lost-update race its docstring claims to have fixed is NOT fixed
  for real usage.** `_RECORD_LOCK` is a `threading.Lock`; the 16 batches run as **separate OS
  processes**. Run #24 worked around it by recording coverage from ONE process gated on the report
  files themselves, which is a better proof anyway — but fix the function or delete its claim.
- **`completeness.py:71-119`** unguarded global dict mutated and `json.dump`-iterated across
  ThreadPoolExecutor workers (live `RuntimeError` risk), **plus `:110-118` a fixed, non-unique
  temp filename shared across those same workers** — m100's anti-pattern again.
- **`standards.py:560-586`** — the unanswered-records scan has no per-file `try/except` in its
  glob loop, so ONE file error (e.g. `read.py`'s own corrupt-cache self-heal deleting a file
  mid-scan — the race precondition was confirmed live) aborts the loop and **caches a partial
  undercount as the true value** for a HIGH-severity zero-tolerance standard.
- **`standards.py:670-682`** — the assay-band check builds "mine" from the charter's own band
  digit rather than from the computed `reference.magnitude`, so it **cannot detect a band-level
  drift at all**, only ever the decimal.
- **`dashboard.py:332,420-425`** — a `standards.check()` crash renders in `movement()` as a
  fabricated **"-N" regression** rather than as a computation failure. This is the page that opens
  every run. Also `:150-168`, `throughput()` returns the same zero-calls dict for a broken DB as
  for genuine quiet, unlike its sibling `quotas()`.
- **`address_space.py:251-252`** — `fit()` silently maps an unknown/None hyperverse to 0 and
  prints it as a real **"H0"**; confirmed live, 12/12 unknown-hyperverse worlds. Also `:172-177`
  the docstring says H/X print as `?` while the code prints real numbers, and `:3,26-27` the
  header claims 74 bits / 10 bytes / 5 fields while the code computes **89 bits / 12 bytes / 8**.
- **`cleanup.py:174-177`** — `thin_description` sets the flag but never sets `changed`, so if it
  is the only qualifying change, `--apply` **reports the record as marked and never writes it**.
- **`catalogue_codex.py:159` — 70 codex elements silently miscategorised**, verified against real
  data by running `parse_codex()` on the owner's actual file: 35 "weapon property", 28 "race
  variant", 7 "background variant" land in THINGS via a default fallback instead of POWERS.
- **`feats_index.py:148` — hyphenated hosts stranded, four confirmed live by running the real
  join** (`date-a-live`, `sakamoto-days`, `the-amazing-digital-circus`, `uncle-grandpa`).
  `host_dir.replace("_", ".")` is irreversible; the correct host is **already in `rec["host"]`**.
  The module's docstring misdiagnoses this as "hosts with no WIKI_HOSTS entry" — all four are bound.
- **`retry_synthesis.py:60`** — beyond the `[:14]` cap, the docstring's "byte-identical to
  `phase_synthesis`" claim is **false**: the real one ranks by feats-present and paginates ALL
  feat-bearing entries; this sorts by raw description length and takes one slice. Affects a dozen
  already-failed sources, merged permanently and never revisited. `:43-47,109-112` also write
  `data/records/*.json` directly with no runtime guard enforcing "pipeline must be stopped".
- **`health.py:124-144`** — `flush()`'s SAMPLES write ends in a bare `except: pass` with no
  self-heal, permanently dropping the evidence bag, in the module whose purpose is "no silent
  failures". **`:179-181`** hardcodes chars-per-token as `/4` and `/3.7` instead of importing
  `context_budget.py`'s `3.0`/`4.0`, and omits `JOB_OVERHEAD_CHARS`/`METADATA_INFLATION` entirely
  — **the 3.7 is more permissive than the real 3.0, so preflight can pass jobs the real budget
  refuses.**
- **`overnight.py:414-455`** — `coverage_snapshot()`/`preflight()` never check subprocess
  `.returncode`, so a crashed `coverage.py` or `health.py` re-reports stale data as a fresh pass.
- **`backfill.py:84-94`** — `roster()` skips the entire subcategory walk whenever the top-level
  listing already has ≥40 members, **silently dropping subcategory-only characters** — the exact
  bug class this file exists to fix.
- **`sevenfold.py:198-202`** — a silent `continue` drops a source's entire world list when
  `weave`'s filtered index and `pipeline.records()`'s source names diverge (two independently
  built name sets).
- **`anchors.py:215`** — the `order` list puts Yggdrasil (M6) before Goku (M5), so the
  monotonicity check fires **every run regardless of instrument health**.
- **`foreman.py:801-808`** — `_function_source()` matches a symbol by **bare name** via
  `ast.walk`, discarding class qualification, so a model patch can land on the wrong same-named
  function. Also `:996` writes a LIVE `src/*.py` non-atomically during a model patch, and
  `:989-991`'s backup filename can collide within the same second.
- **`onomast.py:311-356`** — `register_for()`'s genre/feature voting is **dead**; the sole caller
  passes only `group_id`, so every world uses the hash fallback the docstring says was replaced.
- **`endpoint.py:83-94` and `:356-370`** — `_save()`/`register()` do unguarded read-modify-writes
  on shared `ENDPOINTS.json`/`SOURCE_PAGES.json` with bare `.tmp` names and unretried
  `os.replace`; `register()`'s uncaught write exception **aborts scout.py's whole sweep loop**.
- **`magnitude.py:911-996`** — cross-process lost-update on `data/ASSAYS.json`, **plus** a fixed
  non-PID-qualified tmp name that can collide across processes and raise an uncaught
  `FileNotFoundError`, crashing the batch.
- **`silence.py:250-287` / `:223-240`** — on a persistent lock `write_json` returns **False**, and
  every one-shot caller in batch 06 ignores the return (`navtree.py:263`, `catalogue_codex.py:203`,
  `scope.py:119`), so the process reports success while the file never lands. **The m119/m120
  lesson generalises: audit every ignored `write_json` return in the tree.**
- **`coverage.py:16-18` vs `:82-115`** — the docstring promises an `UNREACHABLE` state
  distinguishing fetch failure from real absence; **the code never implements it** and a transient
  read exception folds silently into `"NO PAGE"`.
- **`read.py:1097-1098`** — the final "done" summary omits `unanswered`/chunks/`_FELL_BACK`, so a
  catastrophically incomplete run prints the same banner as a healthy one.
- **`rosetta.py:364-366,377-378`** — direct `open(w)`+`json.dump` on shared `data/ROSETTA.json`;
  the file already lost a 3,514-row mine once to exactly this.
- **`pipeline.py:397-408`** — `records()` silently drops any record file that fails to parse; that
  source then vanishes from every phase and from `coverage.py`/`grounding.py` with no trail.
- **`hosts.py:44-50`** — `_load()` resets to `{}` on any read failure, indistinguishable from
  genuinely empty; `:78-91` fixed tmp name + no retry + read-modify-write race.
- **`scout.py:107-114`** (`_ask()` swallows all exceptions to `None`, indistinguishable from "no
  URLs known"), `:200-206` (race on `WIKI_HOSTS.json`), `:256-262` (corrupt `SCOUT.json` →
  `prev=[]` → permanent history loss on the next write).
- **`profile.py:129-138`** — a failed `GENRES.json`/`TIERS.json` load silently defaults **every**
  world's genre, indistinguishable from real data.
- **`derivation.py:476-477`** — `SCAN_MODULES` omits `pantheon.py` and `zfighters.py`, both of
  which hold free-parameter dicts invisible to the "where constants live" scan.
- **`tells.py:70`** — regex alternation precedence: the trailing `but` requirement applies to only
  one alternative, so bare "not merely"/"not simply" false-positive. Verified by testing the regex.
- **Non-atomic shared writes still open:** `build_terminal.py:571-573`, `burgs.py:227`,
  `module_index.py:75-76`, `overnight.py:462`, `publish.py:261-263` and `:283-290`,
  `render.py:245`, `generate.py:382-384` (**live process, and `catalog.py`'s reader can hit it
  mid-truncate**), `worldseed.py:317-322`, `wh40k.py:230-231`, `manifest_builder.py:436,455,463`,
  `catalogue_web.py:70-79`, `pipeline.py:1293` (bare `os.replace`, unlike every other writer there).
- **Unguarded read-modify-write on `data/SWEEP_ROLL.json` (five writers):** `resync_roll.py:33-68`
  (now atomic, still racy; its "safe to run at any time" conflates the two), `catalogue_aurora.py:107-150`,
  `catalogue_codex.py:122-203`.
- **Smaller, verified:** `identity.py:180-207` (`_is_continuity()` requires n≥2 so its own worked
  example can never classify) and `:291-320` (`epoch_of()` returns `""` for both "no marker" and
  "call failed"); `chain.py:353` (unguarded `Counter` increment outside the lock two lines below);
  `burgs.py:230` (message says "sample of 50 worlds", code writes all); `sweep.py:20-22` (docstring
  claims a strict funnel the code does not produce); `address_space.py:130-140` ("widths are
  derived, not chosen" above a hard-coded 64); `repass_bands.py:91` (hardcoded `"of 211"`);
  `standards.py:966-982` (`fandom_ipv4_reachable()` does a live TCP connect, up to 8s, with no TTL
  cache, on a path the dashboard polls every 5s); `recover_folder_records.py:143-150` (bypasses
  `write_record_catalogue`'s merge; half-fixed already); `zfighters.py:434-440` (Goku silently
  drops from the roster on any presence-file load failure); `custodes.py:254` (unknown attestation
  grade defaults to MID quality 0.4, not worst-case, unlike `assay.py`'s own defensive pattern);
  `halo.py:146-174` (prints `moth_number` before `silence.write_json` with no
  `stdout.reconfigure` — the UnicodeEncodeError-before-write bug `handbuilt.py` already fixed);
  `resonance.py:71-79` (fixed 600-iteration Gauss-Seidel with no convergence check);
  `pick_model.py` (`total_vram_gb() or 10.0` silently assumes a 10GB card when nvidia-smi is
  unreachable, undisclosed, undermining the GPU-only ruling); `dashboard.py:341-342`
  (`HISTORY[-2000:]` can shrink retention below the 30-min stall window under load);
  `manifest_builder.py:316-320`, `entity_match.py:272`, `stale silence.note() line tags` across
  `foreman.py`, `feats.py`, `scout.py`.

**Modules read end to end and found CLEAN this run** (a clean module is a real result):
`scale_theories.py`, `thread_integrity.py`, `context_budget.py`, `descending_ladder.py`,
`entity_match.py`, `tuning.py`, `rigor.py`, `audit.py`, `address.py`, `tempus.py`, `lognames.py`,
`catalogue_models.py`, `chord_field.py`, `propagation.py`, `tiers.py`, `estate.py`, `catalog.py`,
`grounding.py`, `cosmography.py`, `physics.py`, `handbuilt.py`, `compress_store.py`.

## 4. Audit rotation — ABOLISHED

No rotation. `state/SWEEP_COVERAGE.json` records which run last read each module and
`sweep_plan.missing(run)` is the completeness proof — **but see §3, its cross-process race means
the proof should be corroborated against the report files on disk until that is fixed. Run #24
did exactly that: coverage was recorded from ONE process, gated on each report's existence and
size, which is a stronger proof than the agents' own claims.**
**Method that has now worked six times:** bound the file set, demand `file.py:LINE` citations and
an explicit VERIFIED/UNVERIFIED label, tell the agent a clean module is a worthwhile result, and
make it write the long report to disk and return only a summary. **Point at least one agent at the
code the supervisor wrote that same session** — that instruction has now caught real defects in
the supervisor's own work three runs running.
