# Bug Ledger

*Open bugs by severity (blocking > major > minor > cosmetic). Resolved bugs move to the
bottom with root cause and the export-repo commit that fixed them — a paper trail, never a
deletion. Maintained by the maintenance pass; humans welcome to add.*

## Open

> **MEASURED 2026-08-30 (run #39): 56 of the 108 labelled entries below say RESOLVED in their own
> label and were never moved to the paper trail — 52% of this section, 1,687 lines of a 4,269-line
> file. 52 are genuinely open.** This is the rot the header above forbids, and the rot
> `workorders.resolve` cites *by name* as the reason it deletes an order on close rather than
> trusting anyone to prune: "an order that is resolved but still listed is indistinguishable from
> an open one to the next reader, which is exactly how BUGS.md's Open section rotted."
>
> It was **not** bulk-moved, deliberately. Several entries carry PARTIALLY CLOSED notes — M38,
> M16, M42, m105, m133, m134 among them — where one limb shut and another did not, and run #38's
> reconciliation found ten of that kind. A regex that moved everything labelled RESOLVED would
> move those too and silently close live faults. Order **ca0a93856e2a** carries the remedy: move
> them one at a time, each verified against the source it cites, the way run #38 moved twenty and
> deliberately left ten.

### Major

- **[M64 — OPEN, RAISED run #41] WORK-ORDER TEXT PASSED THROUGH A SHELL IS EXECUTED.** Order
  `1c99df1f69c1`. A remedy field reading ``run `python src/chain.py` `` was passed to
  `workorders.py` as a Bash argument; command substitution **ran it**, starting a full chain
  pipeline (model calls, rewrites `data/CHAIN.json`) under Python314 rather than miniconda, which
  ran 16 minutes before being stopped. Nothing corrupted — `chain_harvest_idx.json` parses at
  271,129 rows, `CHAIN.json` untouched, no temp litter. Two other orders (`525dd7bbffed`,
  `7209d442c73e`) had words silently eaten by the same mechanism and cannot be repaired, the
  closed log being append-only. Order text is data; a remedy field is the field most likely to
  contain a command; routing it through a shell makes the queue an execution path. Remedy: text on
  stdin or from a file, or the Python API — never interpolated into a command line.

- **[M65 — OPEN, RAISED run #41] THE SWEEP'S OWN COVERAGE PROOF ACCEPTS ANY STRING.** Order
  `f307490add1e`. `sweep_plan.record()` validates nothing, so three spellings arrived from three
  batches of run41 (`drill.py`, `src/publish.py`, `foreman`) and only the first matched
  `missing()`, which then reported **26 of 116 modules as never read when every one had been read
  in full**. It fails in both directions: a name matching no module is also accepted silently —
  a batch could claim coverage it does not have and `missing()` would agree. Confirmed live: one
  shard held `catalogue_local.py`, which `sweep_plan` spells `deprecated/catalogue_local.py`, and
  nothing noticed. Shards were normalised onto names `sweep_plan` itself emits and only those.

### Resolved this run (paper trail, run #41 — 2026-09-02)

- **[M63 — RESOLVED 2026-09-02, owner ruling (a)] THE CHAIN DAMAGE IS ACKNOWLEDGED, STILL
  REPORTED, NEVER ERASED.** Order `be33a61be79f` closed on the owner's in-session choice.
  `ledger_guard` gained `state/ledger_chain_acknowledged.json` -- one record naming links
  947-949, both append-only ledgers, the order, the reason, who ruled and when. The named
  shrinks are carried (returned by `verify_chain(with_acknowledged=True)`, printed by `main()`
  every run and by `assert_intact()` every push); anything outside the range or ledger list
  still fails; a malformed record is refused and acknowledges nothing. Chain untouched: 955
  links verify. `assert_intact()` passes; publishing unblocked. Net: 'an acknowledged shrink is
  carried, still reported, and covers nothing beyond its name', watched red two ways.
  Root cause (a probe redirecting half of ledger_guard's paths) was fixed on 2026-09-01 and the
  helper now covers `ACKNOWLEDGED` too.

- **[m62b — RESOLVED run #41] `silence.append_line` WAS NEVER ATOMIC ON THIS PLATFORM.** m62
  landed `append_line` on 2026-08-24 reasoning that one `os.write` to an `O_APPEND` descriptor is
  a single syscall. That is a POSIX guarantee; the Windows CRT implements `_O_APPEND` as
  seek-then-write, so two processes seek to the same end offset and the second lands **on** the
  first. **Measured: eight processes × 400 sub-page JSON rows — 3,200 expected, 2,496 arrived,
  704 destroyed outright, 3 torn**, in `state/model_metrics.jsonl`, the ledger
  `standards.ollama_token_flow` grades from. Second defect in the same call: no `O_BINARY`, so the
  CRT rewrote every LF to CRLF (104,810 against 3 bare LF), meaning the "one syscall of exactly
  these bytes" comment described bytes that were not written. **Fixed** with an OS-level exclusive
  lock on a `<path>.applock` sidecar (`msvcrt.locking` / `fcntl.flock`, released by the OS on
  close or process death) plus explicit `O_BINARY`; bounded and best-effort, so a metrics failure
  still never costs a model call. Live ledger repaired: 104,807 rows kept, 2 unrecoverable torn
  fragments dropped, endings normalised. **Why nothing caught it, which is the more important
  half:** `verify_math` §19ag checks `append_line` by writing 50 rows *from one process*, and
  tearing is by definition what happens when there are two — the hazard the function exists for is
  the one thing its own check cannot produce, and it passed every run for eight days. Net:
  drill.py "a shared ledger keeps EVERY row when six processes append at once", watched red
  against the pre-fix function and green after. Order `7c9a1797d70e`.

- **[m66 — RESOLVED run #41] THE APPEND-ONLY GATE WAS INERT AND PRINTED `ok` FOR A DAY.** Order
  `fc7f5b371e6e`. `ledger_guard.seal()` flattens `handoff/HANDOFF.md` to `handoff__HANDOFF.md`;
  `_read_snapshot()` did not, so it opened a path the writer never writes, got `FileNotFoundError`,
  and `check_since_snapshot` read None as "nothing sealed yet" and answered True. Enforcement on
  that file was dead from the moment it joined `APPEND_ONLY` on 2026-08-31 — on the ledger whose
  own commentary records it having already lost 629 lines, and which gates `publish.push()`.
  Fixed with a shared `_snapshot_path()` used by writer and reader. Verified by watching it
  refuse: unchanged → ok, honest append → ok, truncation to half its lines → False naming the
  loss. Netted for every name in `APPEND_ONLY`, not just the one that was dark.

- **[m67 — RESOLVED run #41] `gpu_lane` COULD STRAND ITS OWN SLOT POOL.** Order `763b56061157`.
  `_read()` answers None to both "no such file" and "will not parse"; the reclaim guard read
  `if rec is not None and _expired(...)`, filtering out the corrupt case before asking — so
  `_expired`'s own "unreadable/corrupt: reclaim rather than strand" line was unreachable from its
  one call site, and `os.open(O_EXCL)` then skipped the file for ever. `MAX_SLOTS` such files put
  every model call in every standing job behind a pool that can never refill. **The obvious fix is
  worse than the fault** — a zero-byte slot is also what a slot looks like between `O_EXCL`
  creating it and the `json.dump` landing, so reclaiming on unreadability alone hands one slot to
  two callers and oversubscribes the card silently. Fixed with `_unreadable_and_stale()` using
  mtime as the fallback heartbeat against the same lease. Net attacks **both** directions and was
  watched red against each.


- **[M38 — OPEN, VERIFIED run #32] THE FAIL-CLOSED LAYER CAN FAIL OPEN.** `escalation.py:154-183`:
  `_raise_halt()` takes **no lock** and uses a non-disambiguated tmp filename, so two concurrent
  first-time OWNER halts can have the second **overwrite** the first rather than record it as
  corroboration — a lost fault in the one ledger that must never lose one. Worse, **if the
  halt-file write itself fails** (permissions, disk), the OWNER fault is only noted to
  stderr/`silence.note` and never persisted — every other process then reads "not halted" and
  proceeds. Silence authorising continued operation is the precise inversion of Hard Rule -1's
  FAIL CLOSED. Separately `escalation.py:97-106` appends the janitor log with buffered
  `open(path,"a")` instead of `silence.append_line` (the m62 torn-line class).

  **PARTIALLY CLOSED — run #38 reconciliation, 2026-08-29.** The write-verdict limb is closed by
  order `ESCALATE_DISCARDS_HALT_WRITE_VERDICT`. `escalate()`'s `level >= OWNER` arm bound nothing:
  `_raise_halt(rec)` then `return rec`, so the fix that stopped `_raise_halt` discarding its own
  verdict in run #34 stopped one frame short of its caller. It now binds
  `landed = _raise_halt(rec)`, puts it on the returned record as `rec["halt_landed"]`, and — because
  `_append_log(rec)` runs BEFORE the write is attempted, so the first janitor line predates the
  verdict — appends a SECOND janitor line coded `HALT_NOT_RAISED` when the halt did not appear;
  `halt_landed` was admitted to the `_FIELDS` whitelist so `brief()` does not drop it. That matters
  because the only durable trace before was a generic `silence.note` plus a stderr line, and every
  standing daemon here runs under `CREATE_NO_WINDOW`. The **non-disambiguated tmp filename** is
  also closed: `_raise_halt` lands through `silence.write_json`, whose tmp name carries PID and
  thread.

  **THE TORN-LINE LIMB IS CLOSED — run #40, 2026-09-01.** `escalation._append` no longer uses a
  buffered `open(path, "a")` + `f.write`; it goes through `silence.append_line`, one `os.write` to
  an `O_APPEND` descriptor, which is what m62's own fix used on `state/model_metrics.jsonl` and
  never carried into this file. The stakes here are higher than m62's: `state/escalation.log` is
  the janitor's rung, the one log this module's docstring says "always holds the whole story even
  when the top rung fires", and every standing job appends to it. The verdict is still returned
  truthfully — `append_line` answers True/False exactly as the old code did.

  **THE RACE LIMB IS NARROWED ~25×, MEASURED, AND STILL OPEN — run #40.** `_raise_halt` is now
  compare-and-swapped (digest taken *before* the read, landed through
  `silence.replace_if_unchanged`, retried) **and verified by read-back**, because the CAS alone
  was not enough: both writers could still report `halt_landed: True` with only one fault in the
  file, which is the original defect wearing the fix's clothes. A loser now goes round, reads the
  winner's halt, and appends itself to its `also`. **Measured on this machine, both versions built
  in memory and stressed through one harness, 25 trials each:** two concurrent first halts —
  ORIGINAL lost a fault in **25/25** trials, NOW **1/25**; four concurrent — ORIGINAL **25/25**
  trials and 75 faults, NOW **7/25** and 7 faults. It is **not closed**, because
  `replace_if_unchanged` re-reads its digest immediately before `os.replace` and that pair is not
  atomic, and because the retry is bounded at `STOP_CAS_ATTEMPTS`. The real fix is an
  **`O_CREAT|O_EXCL` lock** around the read-modify-write — the idiom `codewatch.py` already uses —
  with a staleness steal and a **fail-open** fallback, since a halt that cannot be raised because
  a lockfile is stuck is far worse than a lost corroboration entry. That is a design decision about
  the halt path and was deliberately not landed at the end of a shift. Carried as order
  `HALT_WRITE_RACE_NARROWED_25X_BUT_NOT_CLOSED` (OWNER), with the numbers.

  **A NOTE ON THE NET, because it is the more general lesson.** A threaded race net was written
  for this limb and then deliberately **replaced**. It failed about 1 run in 25 — and a net that
  flaky raises a spurious OWNER halt roughly every twenty-fifth battery, which is worse than no
  net at all, because it teaches people that a red drill means nothing. What is netted instead is
  the **conflict path**, deterministically: a competitor is landed exactly once between our digest
  and our rename, and our fault must end up in the winner's `also`. It was watched go red against
  the single-shot write and green against the fix.

- **[M39 — OPEN, VERIFIED run #32] `catalogue_web.py` WRITES RECORDS STRAIGHT THROUGH A STANDING
  HALT.** Its `main()` never imports `escalation` and never calls `assert_clear()`; batch 10
  traced that `pipeline.write_record_catalogue()` does not check either. A library-wide OWNER halt
  is supposed to mean nothing starts — this cataloguer does not ask.

- **[M42 — OPEN, VERIFIED run #32] `local_agent.py:526-535` PUTS AN UNVETTED MODEL-AUTHORED PATCH
  IN THE LIVE IMPORT PATH.** `t_propose_patch` writes the candidate **straight to the live `src/`
  file** before any gate runs, and holds no lock; batch 16 bounds the window at **~900 s**
  (pyflakes 120 + import 180 + verify_math 600), not the ~600 previously recorded. Any of the
  ~14 running jobs that imports that module during the window gets the unvetted code. Relatedly,
  `_safe` (`:293-331`) does no `realpath`/`islink` resolution, so the denylist protecting
  `data/records/`, the charter, `output/index/` and `state/` is a string-prefix test a symlink
  would walk around.

  **PARTIALLY CLOSED — run #38 reconciliation, 2026-08-29.** The `_safe` limb is closed. It no
  longer decides on the path as written: `src/local_agent.py:388-406` resolves with `realpath` on
  both sides (because `HERE` may itself sit under a link) and the resolved path is put to
  `_denied_target`, which asks all three questions — module denylist, `DENYLIST_PATHS`,
  `DENYLIST_PREFIXES` — rather than only the region prefixes. The junction bypass was found by the
  run-35 sweep; order `6e0127c4f3ed` closed its residue, where `handoff/cfg` → the repo root made
  `config.yaml` reachable and reproducibly rewrote `prose_enabled` on disk. Tonight order
  `deeb24037ede` separately fixed `_gates`' import gate importing a DIFFERENT file for any `.py`
  outside `src/`. **STILL OPEN, unchanged and verified at source:** `t_propose_patch` still writes
  the candidate straight to the live file and gates afterwards — `open(full, "w")` with the replaced
  text, then `fail = _gates(full, modname)` (`src/local_agent.py:775-780`) — and still holds no
  lock, so the window in which any running job that imports that module gets the unvetted code is
  exactly as this entry measures it.

- **[M44 — OPEN, and now also work order `07258ace3a09` (RUN, MAJOR), re-reproduced live by the run40 sweep on 2026-09-01: `spine_code_for("Alien Predator Doom Crossover") -> "II.N"`] `address.py:101-114` INVENTS ADDRESSES — HARD RULE 2, INSIDE
  THE MECHANISM THAT ENFORCES IT.** Live-confirmed: `spine_code_for("Alien Predator Doom
  Crossover")` returns `"II.N"` (Alien's code) instead of UNASSIGNED. Root cause is the coverage
  formula at `:110`, `overlap / min(len(target), len(name))`, which lets any single-word spine
  entry score 100%; the `>` tie-break then resolves by **JSON dict order** rather than refusing.

- **[M45 — OPEN, run #32] THE PARTITIONER IS A SNAPSHOT AND THE COMPLETENESS PROOF IS LIVE.**
  `binding_health.py` was created at 13:35, thirteen minutes after `sweep_plan --batches 16` ran,
  so no batch could be assigned it while `missing()` correctly counted it. A 17th agent closed the
  gap by hand this run. Not a defect in `missing()` — but a sweep should notice mid-run arrivals
  rather than depend on the supervisor reading the failure. **Also: nothing in `src/` imports
  `binding_health` at all.** See NEXT_STEPS §1 for the owner question about who wrote it.

  **PARTIALLY CLOSED — run #38 reconciliation, 2026-08-29.** The second half is no longer true:
  `binding_health` **is** imported from `src/` now — `dashboard.py:577` and three `drill.py` nets —
  and tonight's shift filed and closed several `BH_*` orders against it, so it is neither orphaned
  nor unowned. **STILL OPEN:** the first half, that a sweep should notice mid-run arrivals rather
  than depend on the supervisor reading the failure. Tonight's order `f42c55355431` fixed the same
  shape one level over without touching this one — `sweep_plan.modules()` and `allsweep.modules()`
  globbed `src/*.py` non-recursively while the docstring said *"Every module in src/, NO
  exclusions, deliberately"*, so `src/deprecated/catalogue_local.py` was a module `missing()` could
  never name, by construction. Both now walk `src/` with `os.walk`. The structural lesson is this
  entry's: the completeness proof cannot notice a gap in its own denominator.

### Major
- **[M35 — OPEN, OWNER ACTION NEEDED] FOUR PROVIDERS THAT CANNOT ANSWER ARE STILL BEING CALLED,
  ~40 TIMES AN HOUR, AND THE FAILURES COUNT AGAINST THE READER'S OWN THROTTLE.** Measured run
  #31 from `state/cascade_scratch.db` rather than inferred. Each bucket's `last_error` is a
  **permanent** refusal, and each is being re-claimed continuously:
  | bucket | provider's own words | calls/h | ok |
  |---|---|---|---|
  | `zai:free` | `Insufficient balance or no resource package. Please recharge.` | 14 | 0 |
  | `cohere:free` | `You are using a Trial key, which is limited to 1000 API calls` | 12 | 0 |
  | `cloudflare:free` | `HTTP 401 … Authentication error` | 7 | 0 |
  | `hyperbolic:free` | `HTTP 401 … Could not validate credentials` | 7 | 0 |
  **The classifier is not the fault, and this is worth stating because the ledger has blamed it
  before.** Tested against the live error text, `cascade_bridge`'s `permanent_words` correctly
  returns BENCH-4h for all three of zai/cloudflare/hyperbolic. Two things defeat it in practice:
  1. **`zai:free`'s refusal arrives as HTTP 429.** Z.AI answers an empty account with a
     rate-limit status, so `cascade/router.py:537` (the ENGINE, in `C:\Users\imarl\cascade` —
     **a different repository**) calls `record_rate_limit`, writes `usage.outcome='rate_limited'`
     and sets a **60-second** cooldown. The engine has a text heuristic for *daily* limits and
     none for *permanent* ones. Every one of zai's 14 calls/h is logged as a throttle.
  2. **The bench is per-process.** `_DEAD` is a module-level dict in memory, so a 4-hour bench
     binds only the process that set it; the ~15 processes in the stack each re-discover the
     same dead provider independently, and every new process starts clean.
  **Why this is not merely untidy:** `tuning.cloud_success_rate()` counts **every** usage row in
  the last 15 minutes, including calls to buckets that cannot succeed. Excluding these four moves
  the measured rate from **37% to 45%** against a `CLOUD_MIN_SUCCESS` floor of **0.35** — i.e.
  from oscillating across the threshold to clear of it. That threshold is what pins
  `tuning.regime()` to `local`, which is M19's 1-of-16-permit throttle on the whole reader.
  **Why NOT fixed here:** three of the four need an **account action only the owner can take**
  (recharge Z.AI, replace the Cloudflare and Hyperbolic keys, or retire the buckets), and the
  two code-side options — teaching the engine a permanent class in a *different repository*, or
  excluding dead buckets from the success sample — are both routing-policy changes with the same
  blast radius that keeps M19 unruled. **NEXT_STEPS §1.**

- **[M27 — RESOLVED, run #31] NINE PLANT-WIDE HALT INTERLOCKS FAILED **OPEN** ON A MISSING
  `escalation.py`, AND NOTHING WOULD HAVE SAID SO.** Found run #31 by batch 12, verified by
  measurement across all eight jobs. Every entry point carried
  `try: import escalation as _ESC; _ESC.assert_clear(...) except ImportError: pass` — nine sites
  in eight modules (`dashboard`, `feats`, `foreman`, `overnight` ×2, `overwatch`, `pipeline`,
  `publish`, `read`). If `escalation.py` were deleted, renamed, or left with a syntax error, the
  entire chain of command switched off **in silence** and every job carried on as though the
  library were running clear.
  **This is Hard Rule -1's own incident, generalised.** That incident began with an autonomous
  run deleting a safety it had concluded was unnecessary; the interlock meant to make such a
  thing survivable was itself deletable without a sound. FAIL CLOSED is one of the three
  non-negotiable properties, and this violated it in nine places at once.
  **Measured, not argued.** A probe blocked the `escalation` import and entered each job's
  `main()` in a fresh subprocess. **Before: 0 held, 8 BREACHED** — every job started, `dashboard`
  went as far as serving. **After: 8 held, 8 refused** with
  `REFUSING TO START: the escalation chain (src/escalation.py) could not be imported`.
  Pinned by `verify_math` §20p, which scans all eight files for the swallow and for the refusal.

- **[M28 — RESOLVED, run #31] THE DRILL THAT PROVES THE PROSE GATE COULD OPEN THE PROSE GATE.**
  Found run #31 by batch 11, verified at source and by execution. `drill._gates_agree` compared
  the two gate implementations by **writing five trial values of `prose_enabled` into the LIVE
  `config.yaml`** with a bare `open(real, "w")`, then restoring the original in a `finally`.
  Three faults, and the third is the one that matters:
  1. `open(w)` truncates before it fills, so a reader in the gap saw an empty or half-written gate.
  2. **The supervisor runs the drill every cycle**, so the window recurred every cycle.
  3. `finally` does not run when a process is killed — and the foreman SIGTERMs stalled jobs as
     routine (M15). A kill inside that window leaves the written value on disk permanently.
  **Which value matters, and it was measured rather than assumed.** Of the five trial values,
  four (`"false"`, `"true"`, `1`, `"no"`) are refused by the strict gate, because a quoted string
  is not `True`. The fifth, **`yes`, parses to boolean `True`** — so a kill in that one-in-five
  window leaves `prose_enabled: true` on disk and **the prose gate genuinely OPEN**, with nobody
  informed. The incident that gate exists to prevent is 145 unauthorised chapters.
  **Fixed without a disk write at all**: `prose_gate.gate_open` already took a `cfg` mapping;
  `overnight._prose_enabled` now takes one too (additive, mirrors its sibling exactly), so both
  layers are asked about the same in-memory dict. New drill net
  `and proving that never writes the owner's gate` reads config.yaml's bytes either side of the
  comparison and requires them identical. Pinned by `verify_math` §20p, **asked of the AST** —
  the first draft matched source text and went red against a docstring quoting the removed code.

- **[M29 — RESOLVED, run #31] `publish.py` RETURNED EXIT CODE 0 WHEN THE CREDENTIAL SCANNER
  REFUSED THE PUSH.** Found run #31 by batch 14, verified at source. `main()`'s `except Exception`
  caught every failure the publish loop can have — including `push()`'s own
  `RuntimeError("PUBLISH REFUSED: ...")`, raised when the pre-push scanner finds a credential-
  shaped value staged for the **public** repo — printed a line, and then `return 0` on the
  one-shot path. **A refused publish reported success to its caller, and that caller is every
  maintenance run's final step.** The scanner did exactly its job on 2026-08-25 at 12:04
  (`SECRET_IN_EXPORT`, two hits) and the exit code said nothing. Now tracks `rc` and returns it;
  the `--loop` daemon still keeps retrying, which is correct for a daemon. Pinned by §20p.

- **[M30 — RESOLVED, run #31] A DRILL NET RAISED AN OWNER HALT ON A COINCIDENCE, AND STOPPED THE
  WHOLE LIBRARY.** The net `the live colliding pairs get separate verdicts` compared
  `coverage.state_of()` for two name pairs that sanitise to one filename, and failed when the two
  answers were **equal** and not `NO PAGE` — inferring "these share one document" from "these
  report the same numbers". The state is a 3-tuple of small integers, so equality is ordinary
  coincidence. **Measured live:** `Ten Towns` and `Ten-Towns` on `forgottenrealms.fandom.com`
  both read `('READ', 0, 1)` while loading **two different files** —
  `Ten_Towns__e84ad6558f.json` (entity `Ten Towns`) and `Ten_Towns.json` (entity `Ten-Towns`).
  That is the M23 disambiguation working exactly as designed, and the net halted the library over
  it at 12:33. An alarm that sounds when nothing is wrong is furniture, not a safety.
  **Repaired by making it stricter about the right thing, never quieter**: it now asks for FILE
  IDENTITY and OWNERSHIP — two names must resolve to two documents, and each document must carry
  its own `entity` — neither of which a coincidence can satisfy. A companion net
  `and a real collision would still be refused` stages the pre-M23 world in a scratch tree and
  requires `load` to refuse to hand one entity's file to the other, so the loosening did not
  create a check that cannot fail. Drill: **113 nets, 113 held.**

- **[M31 — RESOLVED, run #31] THE SWEEP'S OWN COMPLETENESS PROOF WAS FROZEN ON RUN #29, BY A
  HARDCODED LITERAL.** `verify_math`'s `the live sweep proves its own completeness` called
  `sweep_plan.missing("run29")` — a run label written into the source. From run #30 onward it
  answered a question about a sweep that had already finished: **no later sweep could move it**,
  complete or skipped alike. It sat red through run #30 and half of #31 naming eight modules as
  unaudited while the agents that read them were filing their reports.
  **This is the third spelling of the same defect in three consecutive runs** — #28 found
  `record()` losing an update, #29 found `missing()` asking *"was run N the LAST to read X?"*
  instead of *"did run N read X?"*, and this is the instrument frozen on a past run. Standing
  lesson 25 keeps being right: the sweep audits the sweep, and that is where the best finding
  keeps being. New `sweep_plan.latest_run()` reads the newest shard and returns **None** when
  nothing has ever swept, so the check FAILS rather than proving the completeness of a sweep that
  never ran.

- **[M32 — RESOLVED, run #31] THE SWEEP'S IMPORT TIER CALLED EIGHT JOBS BROKEN FOR OBEYING THE
  HALT — AND WAS BLIND TO ITS OWN CORRUPTION GUARD.** Found run #31 by running the battery under
  a live halt, converging with batch 15's independent reading of the same function.
  `allsweep.check_import` runs each module with `--help` and separates "no CLI" from "cannot
  import" by looking for the word `Traceback` in stderr. Two failures, opposite directions:
  * With a halt standing, every job raises `SystemHalted` **on purpose**, which prints a
    traceback — so allsweep reported **"8 subsystem(s) in a bad state"** over eight subsystems
    doing precisely what they are built to do. This is the owner's own lesson of 2026-08-25 (*a
    safety that stops work must be told apart from a fault that stops work*), which was applied
    to `overnight.py` as M26 and **never carried to this file** — run #26's theme exactly.
  * In the other direction, `if "Traceback" not in stderr: ok = True` graded **anything dying via
    `raise SystemExit(msg)`** as importing cleanly — and every module in this tree carries a
    `_BAD_CHARS` guard that raises exactly that way when a regex escape is eaten in transit. The
    import tier could not see the project's oldest enemy.
  Both fixed and both watched: the eight halt refusals now read `refused: the library is halted
  (obeying the interlock)`, and a scratch module raising `SystemExit` is now **caught** where it
  was previously graded green. Pinned by §20p, including a check that the sentence allsweep
  matches on is the sentence `escalation.assert_clear` actually raises.

- **[M33 — RESOLVED, run #31] `retry_synthesis` RE-SCORED FAILED SOURCES BY A WEAKER METHOD THAN
  THEIR NEIGHBOURS, UNDER A DOCSTRING PROMISING IT DID NOT.** Found run #31 by batch 08,
  re-confirming batch 03's earlier reading; verified at source. `synthesise()` built
  `sorted(rec["entries"], key=-len(description))[:14]` — a single rank-then-truncate block that
  **never consulted a mined feat** — while its docstring claimed *"byte-identical prompt
  construction to phase_synthesis"*. `phase_synthesis` had been rewritten away from exactly that
  construction under the owner's m13 ruling of 2026-08-24 (*FIX IT ALL*): every feat-bearing
  entry nominated, fourteen per call, best band across blocks winning.
  So the module whose entire purpose is rescuing sources that failed for an **infrastructure**
  reason scored them by the method the library had already rejected — Hard-Rule-0-shaped, since a
  source's true ceiling could rank fifteenth and fall outside the window while the run reported
  success. **Fixed at the root rather than copied across**: the block rule and the prompt text now
  live once, in `pipeline.synthesis_blocks` / `pipeline.synthesis_prompt`, and both callers read
  them — because copying a fix is how m138/m139 happened. `save_side()` also moved off its
  hand-rolled fixed-name tmp onto `silence.write_json`.
- **[M26 — RESOLVED SAME DAY, kept here because the SHAPE recurs] A REMEDY CAUSED THE BREACH IT
  PREVENTS, TWICE IN ONE HOUR, AND THE SECOND ONE WAS THE NEW SAFETY LAYER ITSELF.**
  Found by the owner 2026-08-25, from the page: `read.py` dead since 10:59, all four library
  counters flat. Four jobs were down, not one. Two independent causes, and both are standing
  lesson 10 (*a guard fails by doing the thing it guards against*):
  1. **`foreman.kill_stalled_job` killed jobs nothing would restart, and said so while doing
     it.** Its own log: *"killed stalled read_auto:3592; read.py --run is NOT in the keeper's
     STANDING set -- nothing restarts it until the supervisor's next MAIN LAP, measured at 42-44
     min typically and 4h at worst."* The remedy for `every running job is advancing` directly
     breached `the library's counters are moving`. It had the horizon computed, printed it, and
     killed anyway. **FIXED:** `_restartable()` derives the answer from the keeper's STANDING
     roster (the single authority m49 established, so it cannot drift into a second hand-kept
     list) and **fails closed**; an unrestartable stalled job is now SPARED and escalated at
     SUPERVISOR rung. A stall costs one wedged unit; an unrestartable kill costs hours.
  2. **THE HALT CASCADE, and this one was self-inflicted by the safety layer added hours
     earlier.** A drill breach raised an OWNER halt. The halt interlock makes every job's
     `main()` exit immediately -- correct, and the point of it. But from the supervisor's seat
     that is indistinguishable from every job crashing on startup, so `overnight.py` hit its
     `IDLE_LIMIT`, logged *"That is not an idle library, it is a broken one"*, and **exited**.
     Nothing then restarted anything, so **clearing the halt did not bring the library back** --
     `read.py`, `pipeline.py` and `feats.py --roll` all stayed down. **FIXED:** the supervisor
     consults the halt BEFORE concluding breakage and WAITS, because the entire promise of a
     halt is that work resumes when a person clears it.
  **Both are drill nets now** (`a remedy never kills a job nothing would restart`, `STANDING
  jobs are still killable`, `a HALTED library does not read as a BROKEN one`). Recovery
  verified: nine jobs up, counters moving again (cited 12,737 -> 12,751, no_page 27,399 ->
  19,211 within the hour).
  *The lesson worth keeping: the newest guard in the tree caused the longest outage of the day.
  A safety that stops work must be told apart from a fault that stops work, by everything that
  watches for faults -- otherwise the safety reads as the emergency.*
- **[M21] `action=raw` DOES NOT FOLLOW REDIRECTS, AND AN ENTIRE SOURCE HAS MINED NOTHING.**
  Found run #28 by opening the cache instead of reasoning about it. Every one of dandwiki's 805
  cached entries holds ~40 characters reading `redirect SRD:<title>`: the RAW transport returns
  the literal redirect wikitext and nothing re-requests the target. The MediaWiki API follows
  redirects with `&redirects=1`; the RAW path has no equivalent. So `www.dandwiki.com` reports
  805 cached entries and has contributed **zero** evidence to the corpus, and this is the true
  cause of the standing `health --preflight` failure `feats/www_dandwiki_com: all 200 sampled
  entries empty`. **NOT the cause the ledger claimed** — see the correction under M22.
  Fix is in `endpoint.fetch_raw`: detect a redirect body and re-request the target, with loop
  protection and a hop bound. Touches the fetch path of every RAW host, so it wants care and a
  verification pass, not a quick patch.

- **[M22] A FALSE CAUSAL CLAIM SURVIVED TWO RUNS IN THE LEDGER BECAUSE NOBODY TESTED IT.**
  `NEXT_STEPS.md` §3 asserted, in bold, that `completeness.host_reachable()` **is** the standing
  `health --preflight` dandwiki failure. Run #28 fixed the reachability bug (real — see m173,
  dandwiki went `False` → `True`) and the preflight failure **did not move**, because
  `health.check_caches()` never consults reachability at all: it is a pure on-disk file-size
  check. Two unrelated code paths, joined only by both mentioning dandwiki. Recorded as a bug in
  the LEDGER, not the code: an inherited claim that is re-copied each run accumulates authority
  it never earned. **Rule for successors: a causal claim you did not test is a hypothesis, and
  the handoff should say which it is.**

- **[M19] THE READER THROTTLES THE WHOLE POOL THROUGH THE GPU CARD'S SEMAPHORE, AND NOTHING ON
  THE PAGE SAID SO.** Found run #27, measured end to end, and it is the answer runs #16, #18 and
  #26 all went looking for in the pool. `read._ask` (`read.py:327-337`) selects a gate with
  `read._gate()` and runs the **entire** transport ladder inside it — including the Cascade cloud
  attempt. When `tuning.regime()` returns anything but `"cloud"`, that gate is `_GATE_LOCAL`,
  whose width is `GATE_LOCAL_N` = the **card's** parallelism (`OLLAMA_NUM_PARALLEL`, 2 here), not
  `GATE_CLOUD_N` (16). So at most two model calls of any kind are in flight, and
  `tuning.profile()` drops the worker count to match.
  **Measured 2026-08-25 07:35:** `regime` = `local` because cloud success was **33.3% over 24
  calls** against `CLOUD_MIN_SUCCESS` = **0.35** — a 1.7-point loss. Ceiling = 900 × 2/16 =
  **112.5/h**; observed **112/h**, with all four pool sub-standards green and 29 buckets holding
  headroom. **At 07:47 the regime crossed back to `cloud` and throughput went 112 → 280** with
  nothing restarted: it binds and releases on its own.
  **Self-feeding:** a narrow gate makes few calls, few calls make a small noisy sample, and a bad
  sample keeps the gate narrow. Batch 06 adds that the sample is dominated by the one or two
  buckets `quality_first` ranking sends nearly all traffic to, so it is not really "the pool's"
  health being measured.
  **Now visible:** the new `the reader's gate is open` standard (m161) reports regime, permits and
  `regime.why`, and `model calls per hour`'s order text sends the reader there first (m162).
  **Why NOT patched:** acquiring the local gate only around the local call changes concurrency
  against a shared GPU *and* a free-tier pool at once. **Owner ruling needed — NEXT_STEPS §1.**

- **[M18] `axis_score()` RETURNS A FLAT 9.9 FOR EVERY INPUT AT M10, AND `ledger.py` RESOLVES THE
  SAME EDGE CASE A DIFFERENT, INCOMPATIBLE WAY.** Found by the run #21 `assay.py` audit (first
  end-to-end read of the file), **verified numerically before filing**: `A.axis_score(x, "M10",
  "ruin")` returns `9.9` for x = 1e30, 1e33, 1e36 and 1e40 alike — ten orders of magnitude
  collapsed to one number.
  ```python
  i = LADDER.index(band)
  if i + 1 >= len(LADDER):      # assay.py:221-223
      return 9.9
  ```
  The docstring states the rule as a log-interpolation between a band's floor and the next band's
  floor. At M10 there is no next rung, so the code returns a constant — discarding the log-scale
  discrimination every other band receives, with **no comment explaining the choice and no
  `verify_math` check exercising `axis_score` at M10** (all three existing checks use M3).
  **It is live, not latent.** `magnitude.py:244` calls it inside `quantity_scores()`, whose
  results overwrite `scores[ax]` in `assay_entity()` (`magnitude.py:706-707`) for measured feats
  — so a real M10-anchored entity with a measured quantity gets a constant 9.9 on that axis
  regardless of magnitude.
  **The same question, answered differently one file over.** `ledger.py:127-133` does
  `hi = BAND_EDGES[LADDER[min(i + 1, len(LADDER) - 1)]]["ruin"]`, which at M10 makes `hi == lo`,
  so `log(hi) - log(lo) == 0` and `joules` collapses to the M10 floor **regardless of
  `ruin_score`** — silently making the score parameter irrelevant. Two files, one missing edge
  case, two different silent resolutions, neither documented, neither tested. The project's
  signature failure class applied to the top of the ladder.
  **Why NOT patched by the maintenance pass:** either resolution changes computed magnitudes
  across the library, and which behaviour is correct at the top rung is a charter question, not a
  repair. **Owner ruling needed — NEXT_STEPS §1.**

- **[M15] THE FOREMAN KILLS THE READER FOR LOOKING STALLED WHEN THE POOL IS WHAT STALLED, AND
  THE READER THEN WAITS UP TO A FULL SUPERVISOR LAP TO COME BACK.** Found run #18. This is
  M14's downtime with its cause attached, and it is a loop that feeds itself:
  the pool refuses most calls → the reader completes few entities → it prints no progress line
  → it *looks* wedged → a foreman remedy SIGTERMs it (`rc=15`) → and because `read.py` is
  deliberately outside the keeper's `STANDING` set (`overnight.py:344-347`) nothing restarts it
  until the supervisor's hours-long main lap comes round → with the reader down, zero calls are
  made, so `model calls per hour` reads 0 and every counter is flat → which is precisely the
  condition that fires `restart_reader` again.
  **Measured live, matched timestamps, not inferred:** foreman remedy applied **20:35:04** →
  supervisor logged `read: finished rc=15 in 41m` at **20:35:58** → `read: starting` at
  **21:17:58**. **42.0 minutes down.** The lap that gated the restart was itself 42 minutes
  (`pipeline: finished rc=15 in 41m` at 21:17:22 closed cycle 9; cycle 10 opened at 21:17:32).
  **Two remedies produce this**, both ending their note with the words "supervisor restarts next
  cycle" — which is true for a STANDING job (keeper, 300s) and badly false for the reader:
  - `restart_reader` — `foreman.py:290-321`, wired at `foreman.py:679,685` to *"the library's
    counters are moving"* and *"corpus read is progressing"*
  - `kill_stalled_job` — `foreman.py:324-391`, wired at `foreman.py:662` to *"every running job
    is advancing"*
  **The remedy cannot fix the fault it fires on.** Killing a reader does nothing about a pool
  returning 429/401, and `kill_stalled_job`'s docstring premise — *"killing a wedged one loses at
  most the unit it was stuck on"* — is true about DATA and false about TIME: it costs a lap.
  **Why Major, and why it is NOT patched here:** the remedies are deliberate machinery with
  careful docstrings, and the fix is a design choice among at least three (teach the stall
  remedies to check pool refusal first and decline; put `read.py` in `STANDING`; or make the
  kill notes tell the truth about how long "next cycle" is for a non-STANDING job). **Owner
  ruling needed — NEXT_STEPS §2 B.** Mechanism pinned by `verify_math` §20a so it cannot be
  re-derived wrongly again.

- **[M16] `feats.py` CACHES A NETWORK TIMEOUT AS A VERIFIED "NOTHING HERE", PERMANENTLY.**
  Found by audit run #18, verified against source. `api()`'s bare `except Exception`
  (`feats.py:148-152`) returns `None` after retries — **the same value it returns for a clean
  HTTP 200 saying the page does not exist.** The 476 swallowed `URLError`s in the ledger are
  real transport failures (`state/failure_samples.json`: `TimeoutError(10060, ...)`), not
  probes. Two consequences, both permanent:
  - `evidence_for()` still writes a cache file on the empty path (`feats.py:772-774`) with **no
    fetch-failed flag**. A timeout produces a byte-identical evidence record to a genuine
    absence, and `evidence_for(cache=True)` — the default `roll()` uses — reads it back forever.
  - worse, `alive()` (`feats.py:155-156`, `retries=0`) feeds `resolve_hosts()`'s slug loop
    (`feats.py:260-266`); **one transient timeout writes `known[src] = None`** into
    `data/WIKI_HOSTS.json`, and the cache check is `if src in known: continue` — a *membership*
    test, so a `None` is never reconsidered. `roll()` then skips the whole source
    (`feats.py:807-809`). **An entire source is lost to one network blip, silently, forever.**
  **Not fixed:** the repair changes `api()`'s return contract across every caller, which is a
  public-signature change needing a review cycle. NEXT_STEPS §2.

  **PARTIALLY CLOSED — run #38 reconciliation, 2026-08-29.** The second bullet — the expensive one,
  where an entire source is lost to one network blip — is closed by order
  `FEATS_RESOLVE_HOSTS_FREEZES_A_FAILED_PROBE_AS_NO_WIKI`. Three changes, all in `src/feats.py`:
  the retry guard tests the VALUE (`if known.get(src): continue`, not `if src in known`, since a
  key whose value is None is still `in` the dict); `api()` gained an **additive** `outcome` dict
  stamped `ok` / `no-api` / `http-404` / `throttled` / `http-<code>` / `nonjson` / `network` at each
  return, with a pre-stamped `unknown` default so an unstamped path reads as undetermined rather
  than as a clean negative; and a new `alive_verdict(host)` has three answers, with only an explicit
  404 treated as settled — `no-api` deliberately is not, because `endpoint.detect()` reaches that
  answer by probing and can therefore reach it by failing. `resolve_hosts` writes `known[src] = None`
  only when every candidate returned a clean negative, and an undetermined source is left out of the
  map and printed uncapped. **Note the repair did NOT require the public-signature change this entry
  said blocked it:** `alive()` keeps its exact old contract as a one-line wrapper. **STILL OPEN:**
  the first bullet. `evidence_for()`'s record now carries `pages_refused` so a block page or
  rate-limit interstitial is legible, but a transport failure returning no pages at all still writes
  `pages_read: []`, `chars_read: 0`, `feats: []` with **no fetch-failed flag**
  (`src/feats.py:1412-1426`) — byte-identical to a genuine absence, and read back by
  `evidence_for(cache=True)`.

### Minor-but-new (run #26 — the fifth whole-tree sweep)

*95 modules, 40,431 lines, 16 parallel agents; `sweep_plan.missing("run26")` returned **0
uncovered** and all 16 reports are on disk (15.5–32.4 KB each) in `handoff/sweep26/`. As always:
**only findings I VERIFIED AT SOURCE MYSELF get bug numbers**; the agents' other credible findings
are cited in NEXT_STEPS §3 with file and line.*

*The run's shape: **a cap that outlived the owner ruling which abolished it.** Run #25's shape was
a guard matching one spelling of what it forbade. This is one step earlier — a ruling was made,
applied to the file in front of it, and the identical construction one module over was never
visited. In three of the four cases the sibling file carries a comment naming the ruling BY DATE
while the unfixed file sits beside it, which is what makes this shape survivable: the fix looks
done from every angle except the one nobody checked.*

- **[m138 — MAJOR, RESOLVED] THE UNRECOGNISED LEDGER COULD NOT TELL CASE FROM MEANING, SO ONE
  FAULT HELD TWO PERMANENT ROWS.** `every pool failure is recognised` was red. The ledger held
  eight buckets each carrying `Every model in this pool is rate limited or unconfigured.` AND the
  same sentence lowercased, as separate rows with separate counts. Root cause:
  `cascade_bridge.py:873` did `err = (box.get("error") or "").lower()` while
  `record_unrecognised` keyed on `bucket + "|" + text[:80]` — de-duplication on EXACT text — so a
  change that started folding split every pre-existing row from its own successor.
  **This is m132 one letter over.** m132 named the two engine wordings for "answered with
  nothing" and stopped; the thing that needed fixing was the KEY, not the vocabulary. The key now
  folds (`text[:80].lower()`) and the recorded text does not. Folding the text was separately
  lossy: `record_unrecognised`'s whole premise is "enough text to classify it", and a provider's
  complaint carries case-bearing `request_id` and `org_01KYDH…` identifiers a maintenance run may
  have to quote back to the provider. `raw` and `err` are now two variables with two jobs.
  Verified: two rows differing only in case now merge to one row with count 2, text verbatim.
  Pinned by `verify_math` §22 (two checks).

- **[m139 — MAJOR, RESOLVED] `endpoint.register()` OVERWROTE THE REGISTRY IT COULD NOT READ.**
  `except Exception: d = {}` followed by a whole-file write, so ANY read failure — a torn file
  from a concurrent writer (no lock, and the temp name was fixed so writers collided on it), a
  Norton object-lock, a truncated tail — silently republished `SOURCE_PAGES.json` holding ONE
  source and **erased every other source's registered pages**. Nothing restored them;
  `source_pages()` would answer "none" for ever after, and a source with no wiki and no
  registered pages is uncitable. **This is run #24's lesson 10 in a second file** — `write_record`
  overwriting the disk copy it could not read, same sentence, different module. Absent (write
  `{}`, correct) and unreadable (know nothing, refuse) are now distinguished, and the write goes
  through `silence.write_json`.

- **[m140/m141 — MAJOR, RESOLVED] `backfill.roster()` STOPPED LOOKING AT ≥40, AND CALLED A
  TIMED-OUT WALK COMPLETE.** Two faults in one function, in the module whose entire purpose is
  repairing missing casts.
  - `if len(out) < 40:` gated the subcategory walk, so a wiki with 40 characters at the top level
    and 6,000 under "Villains"/"Heroes"/"Kryptonians" returned the 40 and reported a complete
    roster. A Hard Rule 0 cap wearing a threshold's clothing. **The inner `< 12` cap on the same
    walk had already been found and fixed; the fix stopped one line short of the decision to loop
    at all.** `seen` already de-duplicates, so walking unconditionally changes no result.
  - `members()` did `d = F.api(host, q); if not d: return rows` — and `api()` answers `None` for a
    timeout and for an absent page alike (open bug M16). A network failure mid-pagination returned
    a roster stopping wherever the network died, unmarked, which `backfill_source` then wrote as
    the source's complete cast. Now raises `RosterIncomplete`, a named class; the caller already
    catches per source and prints the exception class, so the cost is one source's pass instead of
    that source's missing characters, permanently.

- **[m142/m143 — MAJOR, RESOLVED] `all_categories(hard_stop=6000)` TRUNCATED DC ALPHABETICALLY,
  UNDER A DOCSTRING SAYING IT DID NOT.** The docstring read *"`hard_stop` bounds the API walk, not
  the answer"*. `out` **is** the answer and `while len(out) < hard_stop` cut it. Measured run #26:
  DC runs past 10,000 categories at `min_pages=40`, and `allcategories` returns alphabetically —
  so every catalogue run on DC saw an alphabetical first 6,000. **DC sits at 0.5% catalogued and
  is the worst source on the page.** A comment that contradicts its code is how this survived
  twenty-five runs. Default is now `None`; the kwarg is kept so no signature breaks, and nothing
  in the tree passes it.
  Separately, the `except` below it broke out with a partial list which was then **memoised** —
  `find_categories` calls this once per canonical class, so one transient API error decided a
  wiki's size for all seven classes and the rest of the process. A failed or bounded walk is no
  longer cached.

- **[m144 — MAJOR, RESOLVED] THE ONE MEMBER OF THE `shared_sample` FAMILY NEVER BROUGHT IN LINE.**
  `cosmology_graph.py:86` did `if len(pair_shared[p]) < 8: pair_shared[p].append(name)`.
  `weave.py:478` and `pipeline.py:1795` write the same key and **both carry the comment `# WHOLE
  list -- Hard Rule 0, ruled 2026-08-24`**. `resonance.py:146` reads `shared_sample` back as the
  pair's actual shared evidence, so a ninth shared entity did not exist to anything downstream.
  Cap removed, key name kept exactly as the siblings keep it.

- **[m145 — MINOR, RESOLVED] `catalogue_models.py:146` CAPPED THE FIELD YOU READ TO FIX THE
  STANDARD.** `available_sample: r["models"][:8]`, persisted, in the record a person consults to
  replace a retired model name — while `model IDs their providers still serve` sits red at 8
  stale. If the provider's ninth model was the right substitute, nothing could see it.

- **[m146 — MAJOR, RESOLVED] THE FOREMAN SAID "REVERTED" WHEN THE REVERT HAD ALSO FAILED, ON LIVE
  SOURCE CODE.** `attempt_patch`'s outer handler tried `shutil.copy2(backup, path)`, swallowed a
  failure via `silence.note`, and returned `{"why": f"reverted after {type(e).__name__}"}`
  regardless. The worst place in the tree for an optimistic report: the file it could not restore
  holds a model's unverified patch, the round prints a line saying the patch was rolled back, and
  the next importer gets the patch. Now returns `reverted: False` and names the backup path to
  restore by hand.

- **[m147 — MAJOR, RESOLVED] THE MODEL-PATCH LANE ATTEMPTED THE TOP THREE FINDINGS FOR EVER.**
  `sorted(open_f, ...)[:3]` with no rotation, so the fourth-ranked open finding was never
  attempted in any round while three stayed open. Hard Rule 0's shape, and the same shape the
  owner abolished in the sweep rotation on 2026-08-25. Ranking survives (high severity first);
  the truncation does not. Each attempt now prints `(i/n)` so a long round announces itself rather
  than going silent and looking wedged to `kill_stalled_job` — saying what is happening, not
  weakening the detector, which is run #25's remedy pattern.

- **[m148/m149 — MAJOR, RESOLVED] THE MOVEMENT PANEL COULD NOT REPAIR ITSELF, AND READ A FALLING
  COUNTER AS PROGRESS.** `silent:dashboard.py:movement:JSONDecodeError` stood at **82 and
  climbing**.
  - The history read and write shared one `try`, so a torn `HISTORY` file threw on `json.load`,
    **skipped the write that would have replaced it**, and returned `[]` — which the panel renders
    as the cheerful "No history yet". Every five-second poll re-threw on the same bytes, so the
    only code that writes the file could never repair it, and the one instrument that can see
    "every counter flat while every job is up" was dark while reporting that it was merely new.
    The load is now isolated and the file self-heals.
  - `stalled` tested `delta == 0`, so a **negative** delta counted as movement. The page showed
    `chunks` at **−3689** with `stalled: false`. Cause is benign — `read.py`'s `done["chunks"]` is
    an in-process counter reset on launch and never persisted, so a reader restart makes the total
    fall — but the reporting was not: a restart READ AS MOVEMENT, which is exactly the condition
    `the library's counters are moving` exists to catch, so a restart could mask a real stall. Now
    carries an explicit `reset` flag; the delta stays honest.

- **[m150/m151/m152/m153 — RESOLVED] FOUR WRITES THE ATOMIC-WRITE SWEEPS MISSED.**
  - `sweep.py:233` truncate-then-filled `CHARACTER_SWEEP.json` while `hostcheck.py`,
    `magnitude.py` and `standards.py` read it live and unguarded — a half-written file parses as a
    shorter cast list rather than failing. The standard `the character sweep is newer than the
    catalogue` is red at 2.4h behind.
  - `rosetta.py:364,377` wrote `ROSETTA.json` with a bare `open(...,"w")` in both `--mine` and the
    **destructive** `--refine`. `scout.py`, `grounding.py` and `coverage.py` each carry a comment
    naming the 2026-08-25 sweep that fixed this exact pattern; `rosetta.py` already imported
    `silence` and never used it.
  - `chain.py:115,191` built `OUT + ".tmp"` and `HARVEST_IDX + ".tmp"` — the renames were already
    atomic and verdict-checked, but the temp NAMES were not unique, and `write_result` has two
    documented concurrent callers (`chain.main`, `pipeline.phase_chain`). That is the collision
    m100 closed at twelve sites; these two were missed.
  - `hosts.add()` did a bare read-modify-write plus `os.replace` on shared `SOURCE_HOSTS` extras,
    where an uncaught `PermissionError` took `discover()` down mid-walk. It also returned `False`
    for a denied write and for a duplicate host alike — **a lost host looked like a known one.**

- **[m154 — MAJOR, RESOLVED] CANDIDATE HOSTS WERE SCORED AGAINST AN ALPHABETICAL FIRST FORTY.**
  `hosts.py:143` `names = list(by.get(source) or [])[:40]`, undocumented. This roster is the
  evidence a candidate host is judged by, so a wiki holding the back half of a cast could not be
  told from one holding none of it — the CLAUDE.md canonical violation applied to the decision of
  where a source lives.

- **[m155 — MAJOR, RESOLVED] `anchors.py` COMPUTED ITS INVARIANT, PRINTED IT, AND EXITED 0.**
  `ok` was calculated, displayed, and discarded; `__main__` called `run()` and returned success
  whatever it said. `allsweep` lists this module under "the instrument" and judges it by exit
  code, so a violated floor→ceiling ordering read to every automated caller as a clean instrument.
  Lesson 9, in the one script whose whole job is to fail when the assay drifts; `audit.py` gets it
  right one file over. **It exits 1 today** — see the open owner question below.

- **[m156 — MAJOR, RESOLVED] `allsweep` RAN FOUR TIERS AND GRADED TWO.** `lint_bad` was computed,
  printed and dropped, so a real pyflakes undefined-name anywhere in `src/` left the integrity
  suite exiting 0 — and `ALLSWEEP.json` had no `lint` key at all, so nothing could even read it
  back. That includes the line `lint_bad` appends when pyflakes itself will not run: **the tier
  announces it is BLIND, and being blind scored identically to being clean.** LINT now counts and
  is persisted. RECONCILE deliberately still does not — see the reverted change in HANDOFF and
  NEXT_STEPS §2.

- **[m157 — MAJOR, RESOLVED] `retry_synthesis.do_merge()` WROTE RECORDS BEHIND THE TWO-WRITER
  CONTRACT.** A bare temp plus `os.replace` straight onto `data/records/*.json`, bypassing
  `pipeline.write_record` and therefore verify_math §18c's whole subject. Not merely procedural:
  `write_record` re-reads and MERGES precisely so a stale in-memory copy cannot be published over
  a fresher disk one, and this loop holds a `rec` taken before an unbounded number of model calls
  — so on a source re-catalogued meanwhile it wrote the OLD entry list back whole, which is the
  30,207-entries-to-1,051 revert `write_record`'s docstring names. The docstring's "run ONLY when
  the pipeline is stopped" was a convention nothing enforced.

- **[m158 — MINOR, RESOLVED] THE ONE RECORDER WHOSE OWN FAILURE WAS INVISIBLE.**
  `record_unrecognised`'s outer `except: pass` never called `silence.note`, so the function built
  to make failures visible was the single place whose failure left no mark anywhere — the ledger
  could quietly stop recording and the page would read "none".

- **[m159 — MAJOR, RESOLVED] THE `or True` DISARM GUARD MATCHED ONLY THE SINGLE-LINE SPELLING.**
  §20i's needle is assembled at runtime to avoid matching its own source — correct, and not
  enough. It searched the raw file text for a one-line spelling, while this file wraps the boolean
  expression and the `True,` want-argument onto separate lines in dozens of checks (2201-2202,
  2219-2220, 2911-2912, 3878-3879 among them). Disarming any of those was invisible to the one
  guard whose entire purpose is to notice it — **lesson 12 inside the file that exists to fail.**
  Now whitespace-normalised, with two alternate spellings, and — the part that matters — **the
  guard is now exercised rather than declared**: two new checks feed it a disarmed check in the
  wrapped spelling and require it to SEE that, then require it to leave an ordinary wrapped check
  alone. Asserting that a detector says False over a clean file proves nothing; it read green for
  nine runs doing exactly that.

### Minor-but-new (run #25 — the fourth whole-tree sweep)

*95 modules, 40,135 lines, 16 parallel agents; `sweep_plan.missing("run25")` returned **0
uncovered** and all 16 reports are on disk (13.9–23.4 KB each), recorded from ONE process gated
on the report files themselves — necessary, because batch 08 **empirically reproduced**
`sweep_plan.record()`'s cross-process lost-update with two real processes this run. Full detail
in `handoff/sweep25/AUDIT_batch01..16.md`. As before: **only findings I VERIFIED AT SOURCE
MYSELF get bug numbers**; the agents' other findings are credible, cited, and queued in
NEXT_STEPS §3.*

*The run's shape: **a guard that only recognises the unobfuscated spelling of what it forbids.**
Run #24's guards inverted on their error path; these never fire at all, are green on purpose,
and every alternative spelling is a fresh hole. Three of the seven had already been "fixed"
once, and the fix stopped one letter short.*

- **[m126 — MAJOR, RESOLVED IN THIS RUN] THE ONLY UNGUARDED SUBPROCESS SPAWN IN THE TREE WAS
  INSIDE `verify_math.py` ITSELF.** `verify_math.py:3034` spawned a real child on every run of
  the suite with no `creationflags`, popping a console window on the owner's desktop — a direct
  violation of the absolute no-console-windows rule. The suite runs from the foreman's patch
  lane, from allsweep and from every maintenance pass, so this fired several times an hour.
  Fixed with `CREATE_NO_WINDOW`, the same idiom the other 25 spawn sites use.

- **[m127 — MAJOR, RESOLVED IN THIS RUN] AND THE CHECK THAT FORBIDS EXACTLY THAT COULD NOT SEE
  IT.** §20e walks the AST rather than grepping, on purpose, and its comment argues the point
  well: *"a count is not a guarantee, so this check does not count — it PARSES."* It then
  identified the module with a literal string comparison, `_f20e.value.id == "subprocess"`.
  `verify_math.py` does `import subprocess as _sp20a` and spawns through that alias, so the
  check was structurally blind to the one violation in the tree — **and to the file it was
  written in.** Widened to resolve import aliases and `from subprocess import ...` names, which
  immediately surfaced **two further real violations**, both in `standards.py` via the same
  `import subprocess as _sp` idiom:
  - `standards.py:130` — a `tasklist` call.
  - `standards.py:1109` — a **PowerShell** call.
  `standards.check()` is what the dashboard polls every five seconds and what the foreman runs
  every round, so these two were popping windows continuously under a green check. Both fixed.
  Pinned by `verify_math` §20j, which now asserts the scan resolves aliases *and* from-imports.

- **[m128 — MAJOR / SECURITY-ADJACENT, RESOLVED IN THIS RUN] THE FOURTH BYPASS OF THE LOCAL
  MODEL'S WRITE GATE.** m113 case-folded the denylist. But `t_propose_patch` still derived
  `modname` through a **case-sensitive** `full.endswith(".py")`, so `src/foreman.PY` — the same
  file on NTFS, passing `os.path.isfile` — yielded `modname = None`, the folded denylist was
  never consulted, `DENYLIST_PATHS` holds only `config.yaml` so nothing caught it on the path
  side, and `_gates()` skipped the parse, lint and import checks for the same reason, leaving
  only the whole-suite `verify_math` run. **8 of 28 adversarial candidates ADMITTED**,
  reproduced before fixing, covering `foreman`, `silence`, `standards`, `verify_math` and
  `local_agent`. The extension test is now folded at all three sites. Verified: all 8 denied,
  the three earlier bypasses still denied, and `src/tells.py` still patchable. §20j pins all of
  it. *(8.3 short names are disabled on this volume, confirmed with `dir /x`; symlink variants
  were reasoned but not testable — none exist.)*

- **[m129 — MAJOR, RESOLVED IN THIS RUN] THE CATALOGUE WAS NEVER ALLOWED TO FINISH, WHICH IS WHY
  `every source is fully catalogued` SAT AT 17.2% WITH ITS BIGGEST SOURCES WORST.** DC 0.5%,
  Thomas 1.2%, SpongeBob 1.7% — starvation's shape, not slowness'. The loop:
  `--recatalogue --shortfall` orders work **largest gap first** and runs **three at once** (its
  own comment: *"puts DC, Gundam and SpongeBob in flight together"*), so every pass opens with
  the three biggest wikis → `catalogue()` printed **nothing** between the `wiki:` line and the
  completion of a whole canonical class → **MEASURED live: DC's `Persons` class is 360
  categories, the first listing 33,614 titles in 23.1s and taking ~3.8 min just to rank**, one
  of 360, in one class of 7 → `MAX_JOB_SILENCE_MIN` is 15 → `kill_stalled_job` kills it as
  wedged → `catalogue_web.py --recatalogue` is **not** in `STANDING`, so nothing restarts it
  until the supervisor's main lap. **Killed three times in the visible foreman log alone.** A
  sweep agent independently found DC's record still at exactly **377 entries, the old
  `MAX_PER_SOURCE=320`-era number**; this is why.
  **Note the irony:** removing the caps to obey Hard Rule 0 (`limit=None`, `top=None`, *"rank,
  never truncate"*) is what made the job slow enough to look dead. The detector was never told.
  **Fixed by saying what is happening, not by weakening the detector:** progress is emitted on
  every **completed unit of work** (categories listed, ranking batches returned, pages fetched),
  rate-limited to one line per 20s via `PROGRESS_EVERY_S`. `wiki_source.page_texts` and
  `rank_by_size` gained an additive `progress=` callback for the two longest silent stretches.
  **A wedged fetch completes nothing, so it still goes silent and is still killed.** Verified
  live against DC and then in the real job. §20j pins the cadence against the stall threshold.

- **[m130 — MAJOR, RESOLVED IN THIS RUN] `backfill.py` USED THE WRONG SIDE OF THE TWO-WRITER
  CONTRACT AND SO DISCARDED EVERY CHARACTER IT ADDED.** It appends missing characters to
  `r["entries"]` — its copy is the fresh authority — then called `pipeline.write_record`, which
  is documented to keep the **DISK** entry list on drift because the *pipeline's* copy is the
  stale side. The append itself guarantees a differing entry count, so drift was detected on
  exactly the runs that had done work, the merge took disk as the base, and the additions were
  dropped. A run that found nothing missing wrote correctly, so it never looked broken — **the
  module's entire purpose was defeated on every run that had something to do.** Reproduced by
  the sweep. Now `write_record_catalogue`, gated on the return; a denied write reports
  `added: 0` rather than a phantom count.

- **[m131 — RESOLVED IN THIS RUN] FOUR MORE CALLERS MARKED WORK DONE WITHOUT CHECKING WHETHER
  THE WRITE LANDED.** Run #24 made both record writers refuse and return `False`; this is the
  other half of that contract.
  - `catalogue_aurora.py:143-146` and `catalogue_codex.py:194-197` — called
    `write_record_catalogue`, discarded the verdict, then set `status = "catalogued"` with a
    real `entry_count`. Work selection is `entry_count == 0`, so a source so marked is **never
    revisited**: a denied write left the roll confidently claiming a record that is not on disk,
    permanently. `catalogue_web.py` already gates this identical call with a comment explaining
    exactly why; its siblings did not.
  - `recover_folder_records.py:149-151` — same shape through `silence.write_json`.
  - `repass_bands.py:78-80` — ignored `write_record`'s verdict and printed "APPLIED. N
    rewritten" for files it never touched. Reproduced against a torn file.
  All four now gated and loud. **This is four of the 32 `write_json` call sites that ignore the
  return tree-wide — the four that then marked work as done. The rest are in NEXT_STEPS §3.**

- **[m132 — RESOLVED IN THIS RUN] THE POOL HAD NO NAME FOR "THE PROVIDER ANSWERED WITH
  NOTHING", AND SAID IT TWO WAYS.** Ruling 3 puts the unrecognised ledger first, so it was read
  first: **13 rows against a handed-over baseline of 12**, and the extra was a genuinely new
  shape — `groq:groq/compound-mini: no answer text produced`, a string that appears nowhere in
  `src/`. Traced to Cascade's `engine.py:343`; its sibling `empty response` comes from
  `engine.py:277`. **One fault, two wordings, and `record_unrecognised` de-duplicates on exact
  text — so two permanent rows.** No predicate could name either.
  Named as `cascade_bridge.empty_content`, matched **exactly** (`err.strip().lower() in (...)`),
  never as a substring: a loose `"empty" in err` would turn naming a fault into a way of not
  seeing faults, which is the one thing this ledger exists to prevent. Verified narrow —
  `"empty response but the router also lost the pin"` is still an unknown. **Naming does not
  bench**, exactly as `named_transient` does not; whether an empty completion should cost a
  cooldown is the owner's open routing question. **13 rows → 12**, all now the single
  deliberately-loud `All 1 candidates failed` shape.
  *Also fixed while in there:* §20i's ledger fixture used `"empty response"` as *the genuine
  unknown that must survive*, so naming the class made that check fail — correctly. The fixture
  now carries a real unknown **and** two rows of the newly-named class, so it still asserts both
  halves. Naming a fault must never quietly delete the assertion that unnamed faults stay visible.

- **[m137 — RESOLVED IN THIS RUN] A HIGH-SEVERITY STANDARD DID NOT EMIT AT ALL, AND THE
  META-STANDARD REPORTED "ALL MEASURED".** Found in the closing diagnostic by diffing live
  standard *names* against the opening snapshot: the count was **40 → 39**, and the missing row
  was `the library's counters are moving`. `standards.py:739` gated the `out.append` itself
  behind `if span_min >= 40:`, so whenever `state/dashboard_history.json` holds under forty
  minutes of samples the standard is **absent** — it does not fail, it does not report itself
  unmeasured, it simply is not there. `every declared floor is measured` read **"all measured"**
  throughout, because it can only inspect rows that exist: **the check that exists to catch an
  unmeasured floor cannot see an absent one.** Not a rare state — the keeper restarts the
  dashboard routinely, and any restart blinds this standard for forty minutes.
  **Fixed:** it always appends now. Short history holds `True` (deliberately — firing a remedy on
  absent evidence would be crying wolf) but reports `not enough history yet (35m of 40)`. Count
  back to 40. Pinned in §20j three ways, including a behavioural check that `standards.check()`
  emits at least as many distinct rows as it declares.
  *This is the run's own lesson one level up: a guard that recognises only the plain spelling of
  what it forbids. It was caught only because the closing diagnostic diffed NAMES rather than
  reading the red list — a habit worth keeping.*

**Open, verified this run, NOT fixed — each needs more than a repair (full list in NEXT_STEPS §3):**

- **[m133 — MAJOR, OPEN] `overwatch.py`'s "0 high-severity findings open" IS AN UNDERCOUNT BAKED
  INTO THE INSTRUMENT.** Proved four ways by execution: a closed or retired finding can **never
  reopen** even if the identical defect returns (`:650-656`, fid-skip fires first);
  `last_verified` is bumped even when the verifying `_ask()` returned `None`, so the auto-triage
  queue advances on checks that never ran (`:486-487`); the reconcile filter **drops 10 of 17
  finding classes** before they can reach WATCH.md, including all seven of
  `allsweep.reconcile()`'s own exception handlers (`:326-329`); and WATCH.md's header count is
  uncapped while its printed list caps at 40 (`:570-573`). **All four bias toward undercounting,
  never over.** A zero from a broken auditor is indistinguishable from a clean tree, and this
  zero is on the page that opens every run. Not fixed here because repairing the auditor changes
  what the project believes about itself and deserves a deliberate pass, not a patch at the end
  of a run. **NEXT_STEPS §2.**

  **PARTIALLY CLOSED — run #38 reconciliation, 2026-08-29.** Two of the four proofs are closed.
  `last_verified` is no longer bumped when the verifying `_ask()` returned None (order
  `c6f64c1424fa`; the full account is under M41 in the paper trail). And WATCH.md's `[:40]` cap is
  gone — order `e8e095597f74` removed the slice while leaving the severity-then-recency sort
  untouched, and uncapped `broken[:4]` and `corrupt[:3]` beside it, which were WORK LISTS printed
  inline under a count that told the truth: the fifth module that will not import is a module
  somebody has to go fix, and it was invisible under a number saying there were nine. Verified by
  driving `write_report()` against a synthetic ledger of 45 open findings. Separately, order
  `97373afb2d5b` dropped `round_once`'s unstated `m not in ("overwatch", "allsweep")` exclusion, so
  the watching machinery is now read too — 115 eligible modules. **STILL OPEN, and both still bias
  toward undercount:** the fid-skip fires first (`if fid in led["findings"]: continue`,
  `src/overwatch.py:850-851`), so a closed or retired finding can never reopen even if the identical
  defect returns; and `structure()`'s reconcile filter is still a whitelist
  (`src/overwatch.py:392-395`: `r["finding"].isupper()` or three named substrings), so most of
  `allsweep.reconcile()`'s finding classes — its own exception handlers included — still cannot reach
  WATCH.md.

- **[m134 — MAJOR, OPEN] `dashboard.py:335-349` — CONCURRENT POLLERS CORRUPT THE HISTORY FILE
  AND THE MOVEMENT PANEL THEN GOES SILENTLY AND PERMANENTLY BLANK.** `ThreadingTCPServer` with
  `daemon_threads=True` and a 5s client poll race on a fixed `dashboard_history.json.tmp` name
  with no lock. **Reproduced live:** 8 threads hammering `movement()` corrupted the file
  (`JSONDecodeError: Extra data`), and once corrupted there is **no self-heal** — unlike
  `health.py`'s LEDGER. Related and also open: `:341-342`'s `HISTORY[-2000:]` retention drops
  below the 30-minute stall window at roughly 6 concurrent pollers (measured).

  **PARTIALLY CLOSED — run #38 reconciliation, 2026-08-29.** Both halves of the headline are closed.
  The write goes through `silence.write_json`, whose PID+thread-qualified tmp name ends the race two
  concurrent pollers had on the fixed `dashboard_history.json.tmp`, and the comment at the site says
  that is why. The load is isolated from the write, so a corrupt file self-heals rather than being
  re-thrown on every five-second poll; order `62286a6c018a` extended the guard to a list of
  NON-DICTS — `[1, 2, 3]` passed the `isinstance(hist, list)` test and then raised inside the try
  below, which returned `[]` and skipped the write that would have healed it, the one corrupt shape
  that still wedged the repair whose own comment reads *"A CORRUPT HISTORY FILE MUST HEAL, NOT
  WEDGE."* **STILL OPEN:** the retention limb this entry files as *related and also open*.
  `src/dashboard.py:425` trims `[h for h in hist if h.get("at", 0) > cutoff][-2000:]` against
  `MOVED_WINDOW_MIN = 30`, so on a five-second poll roughly six concurrent pollers still push the
  2,000-sample cap inside the stall window.

- **[m135 — OPEN] `hostcheck.adopt()` NEVER RECORDS THE "GENUINELY HOSTLESS" VERDICT ITS OWN
  DOCSTRING PROMISES**, so `sources with a reachable wiki` is permanently red and its remedy
  re-runs the full search from scratch for ever. Verified live: **0 adopted, 15 genuinely
  without a wiki** (1,479 entries) — all one-author homebrew or non-wiki media — with
  `data/HOST_UNFIT.json` empty after three days of the supervisor logging the identical result
  every ~10 minutes. `probe()`/`score()`/`candidates()` are correct; the gap is the memory.
  Needs new machinery **and** a floor question. **NEXT_STEPS §2.**

- **[m136 — OPEN] `wiki_source.py:352`'s `hard_stop=6000` CUTS ALPHABETICALLY AND IS LIVE.**
  Measured against the live MediaWiki API this run: **DC has 10,460 qualifying categories,
  4,460 past the cap**, cutting at "Joseph Sulman/Penciler" and starving `discover_categories()`
  for every non-Persons class on the largest wikis. Hard Rule 0. The fix is continuation to
  exhaustion — the pattern `category_members()` already uses — not a larger number. *(Note: this
  is a real cap but it is NOT the cause of m129; the two compound.)*

### Minor-but-new (run #24 — the third whole-tree sweep)

*95 modules, 39,865 lines, 16 parallel agents; `sweep_plan.missing("run24")` returned 0 uncovered
and all 16 reports are on disk (13.8–29.3 KB each), recorded from one process gated on the report
files themselves rather than on agent self-reports. Full detail in
`handoff/sweep24/AUDIT_batch01..16.md`. As last run: **only findings I VERIFIED AT SOURCE MYSELF
get bug numbers**. The agents' other findings are credible, cited, and queued in NEXT_STEPS §3.*

*The run's shape: **a guard that, on its failure path, performs the harm it exists to prevent.**
That is run #23's "a check that cannot fail" sharpened — these checks could fail, and failing is
exactly when they did the damage. Four of the eight are that shape.*

- **[m118 — MAJOR, RESOLVED IN THIS RUN] THE UNRECOGNISED LEDGER NEVER RE-ASKED ITS OWN
  QUESTION.** Ruling 3 makes the pool ledger the first job, so it was read first: **48 open rows**,
  up from the 11 run #23 left, which looked like m109 regressing. It was not.
  **"Unrecognised" is a statement about the CURRENT classifier, and nothing re-evaluated it.**
  `unrecognised_open()` aged rows at 24h but never re-triaged, so every row written before a
  classifier improvement stayed open forever — inside the window, red, unactionable. Measured:
  **36 of 48 were throttles `named_transient`/`pool_exhausted` already understood**, burying the
  one genuine unknown (`groq/compound-mini: empty response`) thirty-six rows deep.
  **Fix:** filter on READ, using the same predicates the write side uses. Doing it on the read
  side also makes the verdict independent of which process wrote the row and which classifier
  version it had imported — `feats.py --roll` has been up since 19:03 the previous day with a
  pre-m109 bridge, and a write-side-only fix would have left it refilling the ledger for hours.
  **48 rows → 12**, of which 11 are the deliberately-loud `All 1 candidates failed` shape and 1
  is the genuine unknown. Pinned by `verify_math` §20i.
  *Not a bug, confirmed while in there:* the case-duplicated rows (`Every model…` beside
  `every model…`) are m108→m109 fossils, not two writers — `cascade_bridge.py:822` lowercases
  `err` before recording, so today's writes are uniformly lowercase.

- **[m119 — MAJOR, RESOLVED IN THIS RUN] `write_record` OVERWROTE WHAT IT COULD NOT READ.**
  `merged = rec` initialises to the **stale in-memory copy** and only becomes the disk-merged
  version if the read succeeds. The `except Exception` swallowed the error and **fell through
  into the write**, putting the pipeline's hours-old copy over the disk file whole — the exact
  30,207-to-1,051 revert the docstring says the function was written to stop, performed by the
  guard. **The trigger is the condition the merge exists for:** the read fails most readily when
  the other writer is mid-write, because a torn or momentarily-empty file is a `JSONDecodeError`.
  **Fix:** refuse and return `False`, which is this module's own idiom — `_landed()` already
  argues a writer must SAY when it did not land so the caller leaves its unit open. Pinned by §20i.

- **[m120 — MAJOR, RESOLVED IN THIS RUN] `write_record_catalogue`, THE SAME FALL-THROUGH POINTING
  THE OTHER WAY.** Here `rec` is the authority for the entry list, so a swallowed read does not
  revert the cast — it does something quieter and just as permanent. The merge is what carries
  the disk copy's per-entry judgments forward and re-appends disk-only entries; skipping it
  **drops every disk-only entry and blanks every judgment already made**, one screen below a
  docstring promising "a merge never shrinks a cast". Same remedy. Pinned by §20i.

- **[m121 — MAJOR / SECURITY-ADJACENT, RESOLVED IN THIS RUN] THE LOCAL MODEL'S WRITE GATE, A
  THIRD ROAD IN: AN NTFS ALTERNATE DATA STREAM.** After m113 (case) and m114 (name prefix),
  `src/foreman.py::$DATA` is the **same bytes** as the denied file — `os.path.isfile` says True
  and the write lands in the real module — but the string does not end in `.py`, so `modname`
  came out `None`, the module denylist could not match, and `DENYLIST_PATHS` was tested against a
  name (`foreman.py::$DATA`) not in it either. **Reproduced on this machine before fixing.** For
  `health`, `allsweep`, `estate` and `local_agent` the loss was total: `verify_math` does not
  import those, so the parse/lint/import gates had nothing to say about them either.
  **Fix in `_safe()`**, which every tool funnels through, and reframed — the test is no longer
  "does this name look denied" but **"is this a plain name at all"**: a colon anywhere past the
  drive letter is refused. Trailing dots and spaces turn out to be normalised away by `abspath`
  before the denylist sees them, so `src/foreman.py.` correctly yields `modname == "foreman"` and
  is denied on the ordinary path — asserted too, so it cannot silently stop being true. Verified
  not to over-block (`src/tells.py` still patchable). Pinned by §20i.

- **[m122 — MAJOR, RESOLVED IN THIS RUN] A CHECK DISARMED WITH AN ALWAYS-TRUE DISJUNCT, IN THE
  FILE THAT EXISTS TO FAIL.** `verify_math.py:3086` read
  `"import overnight" in _fm19._restart_horizon.__doc__ or True`. The docstring says "STANDING is
  imported rather than copied" and has never contained that literal, so the assertion was
  **false** — and instead of correcting it, an always-true disjunct had been added, with a note
  conceding the real assertion was the two checks above. Now asserts against the **function
  body**, which genuinely does `import overnight` and reads `_ON.STANDING`. A self-check that no
  other check carries an always-true disjunct is pinned beside it — its needle assembled at
  runtime, because as a literal it matched its own source line and failed forever, which is the
  self-referential form of the bug it hunts.

- **[m123 — MAJOR, RESOLVED IN THIS RUN] THE SUITE COULD BE SILENCED BY THE DEFECT IT WAS POINTED
  AT.** `check()`'s float branch did `abs(got - want)` with no type guard. A non-numeric `got` —
  the commonest way for code under test to be broken — raised `TypeError`, and **nothing wraps
  this script**, so it escaped the whole run: every check after that point never executed and the
  `RESULT` line never printed. A suite that reports nothing resembles a suite still running.
  Now recorded as a failed check. Deliberately narrow: `bool` is an `int` subclass, so
  bool-against-float keeps its old arithmetic verdict and **no previously-passing check changes
  its answer** — confirmed against the 682-check baseline before the new section was added.

- **[m124 — MINOR, RESOLVED IN THIS RUN] THE TEST HARNESS FILED ITS OWN PASSES AS PRODUCTION
  FAULTS.** `_raises()` called `silence.note("verify_math.py:47")` on every **expected**
  test-triggered exception, flowing into `state/failures.json` — the ledger the dashboard polls
  and `standards` reads — where the "unexpected swallowed failures" standard counted them as
  genuine unrecognised production faults, the probe key not being in its allowlist. **87 rows had
  accumulated** (29 `ContextOverflow`, 58 `ValueError`) from that one line. The exception IS the
  expected result there, and this file already adopts exactly that exemption elsewhere.

- **[m125 — MAJOR, RESOLVED IN THIS RUN] `rc=<number>` IS NOT A DIAGNOSIS, AND THAT IS WHY
  `read.py`'s NEW CRASH SIGNATURE WENT UNREAD THREE TIMES.** The reader's exit history splits
  cleanly: **every exit up to 02:17 on 2026-08-25 was `rc=15`** (psutil's kill — a foreman
  remedy, i.e. M15), and **every exit after 02:30 is `rc=4294967295`**, three consecutively
  (02:41, 02:50, 03:47). Run #23 saw the first two, matched them to run #22b's commit times and
  filed them as a harmless process bounce; **the third disproves that**, nothing being bounced at
  03:47. Nor is it a crash — `read.py`'s `main()` returns only 0, and `4294967295` is
  `TerminateProcess(handle, -1)`, which no remedy here emits (they exit 15) and no Python error
  emits (those exit 1).
  **The structural fault:** the pool side has `record_unrecognised` and a standard that reddens
  on an unnameable refusal; the **job side had no vocabulary at all**, so the supervisor logged a
  bare integer and a guess about it was never testable. `overnight.name_rc()` now names what an
  exit code means and says `UNRECOGNISED exit code — investigate rather than assume` for anything
  it has no entry for. Pinned by §20i. **What actually kills the reader is still unidentified —
  it is NEXT_STEPS' top item, and it is a live outage, not a historical curiosity.**

### Minor-but-new (run #23 — the second whole-tree sweep)

*95 modules, 39,687 lines, 16 parallel agents; `sweep_plan.missing("run23")` returned 0 uncovered
and all 16 reports are on disk. Full detail in `handoff/sweep23/AUDIT_batch01..16.md`. As last
run: **only findings I VERIFIED AT SOURCE MYSELF get bug numbers**. The agents' other findings are
credible, cited, and queued in NEXT_STEPS §3 — not silently dropped.*

- **[m109 — MAJOR, RESOLVED IN THIS RUN] THE UNRECOGNISED-FAILURE LEDGER HELD 122 KNOWN FAILURES
  AND ONE UNKNOWN, BECAUSE THE CLASSIFIER HAD NO WORD FOR "BUSY".** Ruling 3 makes this the run's
  first job, so the ledger was read first: **44 open rows, 122 occurrences, exactly one genuine
  unknown** (`groq:groq/compound-mini: empty response`). Everything else was an ordinary throttle.
  **Root cause:** `_ask_call`'s classification was binary — `permanent_words` → 4h bench, else
  `record_unrecognised()`. There was no transient branch at all, so `Rate limit exceeded`, `429`,
  `tokens per day (tpd): limit 200000` and Cohere's trial-key cap were all filed as mysteries.
  m108 was a classifier that could never match; this is one that matched everything, and both
  produce a page nobody can read.
  **Fix:** `cascade_bridge.named_transient()` — phrase-matched, word-bounded on numeric codes,
  checked AFTER the permanent classifier so a billing complaint that also says "try again" is
  still benched. **Nothing is hidden:** a throttle is already counted in the throughput panel and
  as `usage.outcome='rate_limited'` in Cascade's `usage` table, which is where `model calls per
  hour` reads from. **44 rows → 11.** Pinned by `verify_math` §20h.

- **[m110 — MAJOR, RESOLVED IN THIS RUN] THE m108 UNWRAP DESTROYED THE ONE FACT THE CLASSIFIER
  NEEDED, AND COULD BENCH A BUCKET ON A NEIGHBOUR'S EVIDENCE.** Of the 23 rows surviving m109,
  **15 named more than one candidate** (`All 11 candidates failed: ...`). For those,
  `provider_error(pinned.bucket)` **cannot work by construction** — it reads the pinned bucket's
  row, but a multi-candidate call is not necessarily an attempt on the pinned bucket. Proven from
  the ledger itself: pin `groq:openai/gpt-oss-20b` against candidate label `Llama 3.3 70B (Groq)`.
  **Fix, part one:** `pool_exhausted()` recognises a multi-candidate aggregate as a statement
  about pool CAPACITY, not an unnameable provider fault. `All 1 candidates failed` deliberately
  stays unrecognised — pin and attempt agree there, and that row shape is what exposed m108.
  **Fix, part two, found by the sweep agent auditing this same session's code:** `pool_exhausted`
  was being evaluated AFTER the unwrap, which destroys the text it reads — and worse, the unwrap
  could pull a neighbouring bucket's `insufficient balance` into an aggregate and hand this bucket
  a **four-hour bench for a call that failed because the pool was empty**. That is m103's harm
  (shrinking the binding constraint) reached by a new road. Now decided on the RAW text before the
  unwrap; a multi-candidate aggregate can never drive a bench. The same agent objected to
  `"connection"` and `"capacity"` as bare substrings — `invalid connection string` is a config
  fault, not a throttle — both are now phrases. Pinned by §20h.

- **[m111 — MINOR, RESOLVED IN THIS RUN] `record_unrecognised()` USED THE PATTERN m100 RETIRED, IN
  CODE WRITTEN THE SAME SESSION AS m100.** Hand-rolled `UNRECOGNISED + ".tmp"` + `replace_retry`.
  `_UNREC_LOCK` is a `threading.Lock`, so it orders writers inside ONE process — but this file is
  written from every process importing `cascade_bridge` (read, pipeline, feats, overwatch), and
  those collide on the temp file itself. Converted to `silence.write_json`.

- **[m112 — MAJOR, RESOLVED IN THIS RUN] A HIGH-SEVERITY STANDARD READ GREEN OFF A FIFTY-EIGHT-
  HOUR-OLD SNAPSHOT.** `model IDs their providers still serve` did
  `len(pm.get("stale") or [])` against `data/PROVIDER_MODELS.json` **with no age check**. The file
  was stamped `2026-08-22 17:42` with `stale: []`, while `state/read_auto.log` showed the pool
  removing **five model IDs with HTTP 404 (no such model) on every reader start**.
  The project already ages `COVERAGE.json` before believing a coverage STALL. **This is the same
  lesson from the more dangerous side:** a stale file producing a false ALARM gets investigated and
  dismissed; a stale file producing a false ALL-CLEAR is never looked at again.
  **Fix:** `MAX_PROVIDER_MODELS_AGE_H = 12`; the standard now reports `UNMEASURED` rather than
  passing, with the refresh command in its order text. **Running that remedy found 8 stale Ollama
  references, with `qwen3:8b` the only installed model** — matching the standing-model ruling. The
  standard is now red on a real measurement. **The repair itself is m91 and is NOT in this repo**
  (`C:\Users\imarl\cascade\config.json`). Pinned by §20h.

- **[m113 — MAJOR/SECURITY-ADJACENT, RESOLVED IN THIS RUN] THE LOCAL MODEL'S WRITE GATE WAS
  DEFEATED BY ONE CAPITAL LETTER.** `local_agent.py`'s `DENYLIST` — which stops the local model
  patching `foreman`, `silence`, `standards`, `verify_math`, `health`, `allsweep`, `estate` and
  `local_agent` itself — is a **case-sensitive set**, matched against `modname` derived from the
  caller's own path string, on a **case-insensitive filesystem**. `path="src/Foreman.py"` passes
  `os.path.isfile` (Windows resolves it to the real file), yields `modname == "Foreman"`, and
  misses the set. **Reproduced on this machine before fixing.** Now folded on both sides; a
  denylist that errs toward denying is safe, one that errs toward allowing is the whole failure.
  Verified not to over-block (`src/tells.py` still patchable). Pinned by §20h.

- **[m114 — MAJOR, RESOLVED IN THIS RUN] `local_agent._safe()` TREATED A PREFIX AS A DIRECTORY
  BOUNDARY.** `full.startswith(HERE)` is true for any SIBLING whose name merely begins with this
  project's — including `panscriptum-export`, the copy this module is forbidden to touch. Now
  `full == HERE or full.startswith(HERE + os.sep)`. Pinned by §20h.

- **[m115 — MINOR, RESOLVED IN THIS RUN] A FAILED REVERT REPORTED ITSELF AS A SUCCESSFUL ONE.**
  `t_propose_patch()`'s exception path returned `"reverted": True` as a **literal**, emitted even
  when the restoring write had just raised — so the one outcome that leaves a **half-patched module
  on disk** was the outcome that claimed most confidently to have cleaned up. Now tracked, with an
  `ALARM` key naming the file when the revert genuinely failed. Pinned by §20h.

- **[m116 — MAJOR, RESOLVED IN THIS RUN] THE BUG QUEUE'S OWN REPORT RENDERED A CRASHED CHECK AS A
  CLEAN ONE.** `overwatch.structure()` records its failures in `struct["error"]` /
  `struct["estate_error"]`; `write_report()` **never read either key**. On a crash,
  `broken_modules` and `corrupt_files` were absent, `len([])` was 0, and WATCH.md printed
  *"modules that will not import: **0**"* — a clean bill of health from a check that never ran, in
  the file whose whole job is reporting what is wrong. The only tell was `of 0 inspected`.
  An error now **replaces** the number instead of sitting beside it. Both paths verified.
  **NOTE: this fixes only the crash-reporting half.** The reconcile FILTER at `overwatch.py:326-343`
  still drops real findings — see NEXT_STEPS §3, it is the top unworked item.

- **[m117 — MINOR, RESOLVED IN THIS RUN] SIX MORE OF THE m100 TAIL.** `genre.py` (read by
  `navtree` and `profile`, whose loader turns a failed read into a silent blanket-default
  catalogue — so a torn write here is invisible downstream), `navtree.py` (**no temp staging at
  all**, while already importing `silence`), `sevenfold.py`, `pantheon.py`, `zfighters.py` (read by
  `pantheon`), `halo.py`. Three now-unused `import json` lines removed with them; pyflakes clean.

### Minor-but-new (run #22b — the first whole-tree sweep)

*All 95 modules were read line-by-line by 16 parallel agents; full reports live in
`handoff/sweep22/AUDIT_batch01..16.md`. Only findings I VERIFIED AT SOURCE MYSELF are given
bug numbers below. The batch reports contain many more that are credible but unverified by me —
they are the next run's work, not silently dropped.*

- **[m100 — MAJOR, RESOLVED IN THIS RUN] EIGHTEEN SHARED-FILE WRITES ACROSS FOURTEEN MODULES WERE
  TRUNCATE-THEN-FILL, NOT ATOMIC LANDINGS.** `open(path, "w")` + `json.dump` empties the target
  before writing a byte. A reader in the gap sees an empty or half-written file; a crash in the
  gap makes it permanent. **Four scripts** (`catalogue_aurora`, `catalogue_codex`,
  `recover_folder_records`, `resync_roll`) were doing it to the SAME file,
  `data/SWEEP_ROLL.json` — the hazard `resync_roll.py`'s own docstring described in prose.
  Others hit `COVERAGE.json` (the library's headline figures), `SHELFMARKS.json`, `SCOPE.json`,
  `TIERS.json`, `WIKI_HOSTS.json`, `PROVIDER_MODELS.json`, `SHARED_STAGE_GRAPH.json`,
  `ONOMASTICON.json`, `GROUNDINGS.json`, `REFERENCE_ASSAYS.json`, `ENTITY_INDEX.json`,
  `ALLSWEEP.json`, `catalog.json`/`failures.json`, and `WATCH.md`. Three sites in `weave.py`
  were `json.dump(obj, open(path, "w"))` — truncating **and** leaking the handle.
  **Root cause:** there was no shared correct way to do it. `catalogue_web.save_roll()` had the
  atomic version and a comment saying an interrupted write "kills the next run of either script
  outright"; its siblings never got it. **Fix:** new `silence.write_json()` — atomic, with a
  **pid+thread-unique temp name**, which also closes the older `path + ".tmp"` collision race
  where two writers of one path fight over the temp file itself. All 18 sites converted.
  Pinned by 25 checks in `verify_math` **§20g**. Export commit `ea89738`.
- **[m101 — MAJOR, RESOLVED IN THIS RUN] A HARD RULE 0 CAP LABELLED AS HARD RULE 0 COMPLIANCE.**
  `weave.py:216` (and its idf twin at :170) capped the shared-entity evidence list at **8**:
  ```python
  if len(shared[p]) < 8:
      shared[p].append(k)
  ```
  while BOTH consumers — `weave.py`'s writer and **`pipeline.py:1761`, the production path that
  writes `data/RESONANCE_GRAPH.json`** — carried the comment `# WHOLE list -- Hard Rule 0, ruled
  2026-08-24` directly above the truncated data. The comment recorded the owner's ruling; the
  data had been cut eight entries earlier, in the live pipeline, ever since. **A cap wearing a
  compliance label is the worst shape a cap can take, because the label is what stops anyone
  looking.** Both builders uncapped. Export commit `ea89738`.
- **[m102 — MAJOR, RESOLVED IN THIS RUN] THE PAID LANE, ERASED.** Owner ruling 2026-08-25: *"the
  paid lane should be erased from the code."* Removed `PAID_PREFIX`, `PAID_LANE_RETIRED`,
  `paid_lane_open()`, `_PAID_LOCK`, the burst-cap file read, the spend counter, and `foreman`'s
  spend report. `widen_candidates()` lost its `paid_ok` parameter (public-signature change, the
  gate's last handle). `verify_math` §19h was rewritten to assert an **absence** — the erased
  names may not appear in `cascade_bridge.py` or `foreman.py` **even in comments**, which caught
  three surviving references in my own tombstone prose on the first run. `state/PAID_BURST.json`
  is deliberately kept, unread, as the sole record of the 598-call / ~$11.96 spend.
  Export commits `080f4f7`, `ea89738`.
- **[m103 — MINOR, RESOLVED IN THIS RUN] MY OWN 4-HOUR BENCH COULD FIRE ON A TRACE ID.** The
  `permanent` classifier added earlier in run #22 matched `"401"/"402"/"403"` as bare substrings,
  so a request id like `req_4403abc` would bench a **merely rate-limited** provider for four
  hours — shrinking the pool that is the system's binding constraint, i.e. the exact opposite of
  the bug the classifier was added to fix. Now `re.search(r"\b(401|402|403)\b", err)`; the prose
  markers stay substrings. Found by the sweep auditing the same session's own work.
- **[m104 — MINOR, RESOLVED IN THIS RUN] TWO BUGS IN `sweep_plan.py`, HOURS AFTER I WROTE IT.**
  (a) `record()` did an unguarded read-modify-write on `SWEEP_COVERAGE.json` — the one function
  whose entire purpose is to be called by sixteen concurrent batches; a lost update would make
  `missing()` report a gap that never happened or hide one that did. Now locked and landed
  atomically. (b) `modules()` turned an unreadable file into a **0-line module** with no note,
  which sorts last, packs into a bin as free weight, and reads exactly like an empty stub — a
  file silently dropped from a sweep whose whole purpose is that nothing is dropped. Now noted
  and flagged `unreadable`.
- **[m108 — MAJOR, RESOLVED IN THIS RUN] THE CLASSIFIER NEVER SAW A PROVIDER ERROR AT ALL, WHICH
  IS WHY THE BENCH STILL DID NOT FIRE AFTER m98 WAS "FIXED".** Found within the hour by the
  `every pool failure is recognised` standard added alongside it — the new standard went red on
  its first publish and named its own cause. Cascade's engine does not hand this code the
  provider's error; it hands back an AGGREGATE of its own: `All 1 candidates failed: GLM 4.7
  Flash (Z.AI)`, or `Every model in this pool is rate limited or unconfigured`. Neither carries a
  status code or any provider wording, so the permanent-refusal classifier repaired earlier the
  same day was judging a string that can never match — **`zai:free` went on being re-claimed
  forever while its real error, recorded in `bucket_state.last_error` at the same minute, read
  "Insufficient balance or no resource package".** Repairing m98's WORDING was necessary and, on
  its own, useless.
  **Fix.** `cascade_bridge.provider_error()` reads the pinned bucket's own last error from
  Cascade's scratch DB — read-only, single row, aged at 180s so a fossil cannot bench a live
  provider, and total so a diagnostic cannot kill the call it is trying to explain. The
  classifier unwraps before it judges, and the unrecognised ledger records the UNWRAPPED text so
  what reaches the page is a complaint someone can act on rather than the engine's aggregate.
  **Verified live against all six affected buckets:** `zai`, `cloudflare` and `hyperbolic` now
  classify as 4-hour permanent; `groq`, `sambanova` and `cohere` correctly stay transient.
  Pinned by 7 more checks in `verify_math` §20f. Export commit `e234107`.
  **The lesson worth keeping:** the standard that found this was added in the same session as
  the bug it exposed, and it fired on its first publish. Surfacing an unrecognised failure is
  not bookkeeping — it is what turns "the pool is slow" into a named, fixable fault in an hour.
- **[m105 — OPEN, VERIFIED, NOT FIXED] ~14 MORE NON-ATOMIC WRITES REMAIN (the m100 tail).**
  `build_terminal.py:572`, `burgs.py:227`, `genre.py:236`, `halo.py:170`, `module_index.py:75`,
  `navtree.py:260`, `overnight.py:462`, `pantheon.py:260`, `publish.py:262`, `render.py:245`,
  `rosetta.py:365` and `:377`, `sevenfold.py:266`, `foreman.py:996` (this last one writes a LIVE
  `src/*.py` during a model patch — it has a backup and an auto-revert, which is why it is not
  urgent, but a crash mid-write leaves a corrupt module). Mechanical now that
  `silence.write_json` exists; left undone rather than rushed at the end of a long session.

  **PARTIALLY CLOSED — run #38 reconciliation, 2026-08-29.** Ten of the fourteen are done and were
  verified at source this pass: `genre.py`, `halo.py`, `navtree.py`, `pantheon.py`, `rosetta.py`
  (both sites) and `sevenfold.py` now hold **no** bare `open(..., "w")` at all, and
  `build_terminal.py`, `burgs.py`, `module_index.py` and `overnight.py` build whole and land
  atomically. **STILL OPEN, three of them:** `render.py:245` (the SVG view writer), `publish.py:996`
  — `open(PAGE, "w")`, the published page itself — and `foreman.py:1370`, which is this entry's
  `foreman.py:996` after drift and is the one that writes a LIVE `src/*.py` during a model patch.
  This entry's own reason for ranking that last one non-urgent (it has a backup and an auto-revert)
  still holds, and so does its caveat that a crash mid-write leaves a corrupt module.

- **[m106 — OPEN, VERIFIED] `endpoint.py:200-233` IS THE SHARED ROOT OF M16, m93 AND m94.**
  `fetch_raw()` returns an identical `(t, None)` for a confirmed 404/410, an HTTP refusal, an
  exception, and an HTML error body — **no caller can distinguish "absent" from "request
  failed"**. Every downstream bug in this family is a symptom of that one return contract.
  `detect()` (`:143-172`) compounds it: it treats a timeout/DNS/5xx exactly like a clean negative
  and caches the merged verdict as `MODE_DEAD` for 24h, poisoning a host off one bad network
  window. **A ruling on M16 should settle all four at once.**

### Minor-but-new (run #22)

- **[m93 — HIGH IMPACT, VERIFIED AT SOURCE, NOT FIXED] `hostcheck.probe()`'s RAW-MODE BRANCH
  RETURNS A REAL `rate` OF 0.0 WHEN THE NETWORK FAILED — the exact defect the same function's
  API branch exists to prevent, committed twenty lines above it.**
  ```python
  if EP.detect(host)["mode"] == EP.MODE_RAW:          # hostcheck.py:134-139
      got = EP.fetch_raw(host, names[:12])
      n = min(len(names), 12)
      return {"host": host, "probed": n, "hits": len(got),
              "rate": round(len(got) / n, 3), ...}
  ```
  `endpoint.fetch_raw()` swallows every per-title exception (a DNS failure raises `URLError`) and
  returns `None` for that title, so a **total** network failure yields `got == {}` and this branch
  reports `hits=0, rate=0.0` **with no `error` key** — indistinguishable from "this wiki genuinely
  holds none of these names". The batched-API branch at `hostcheck.py:150-155` handles the same
  case correctly and its comment names the stakes: *"NOT a rate of zero... conflating them is
  precisely the defect this file exists to catch -- committed here, by the tool built to catch it.
  Seventy-four throttled probes came back as 0% and the repair pass unassigned
  `warhammer40k.fandom.com` from Warhammer 40,000."* Because `rate` is never `None` on this path,
  `score()` can never route it to `"UNREACHABLE — no judgement"`, so an outage on a raw-only wiki
  flows into a `"WRONG FICTION"` verdict and, under `--repair`/`--adopt`, gets written to
  `HOST_UNFIT.json`. **Not fixed deliberately:** the repair needs `fetch_raw` to distinguish
  "confirmed absent" (404/410) from "request never completed", which changes its return contract
  across callers — the same shape as **M16**, and a design call.
- **[m96 — MINOR, VERIFIED] A BUCKET THAT RETURNS UNPARSEABLE JSON HAS ITS STRIKES CLEARED
  ANYWAY.** `_clear(pinned.bucket)` runs on transport success (`cascade_bridge.py:673-681`)
  **before** `_extract_json` is attempted, so a bucket that reliably answers prose instead of JSON
  — a failure mode the module docstring itself calls out for cloud models — is never deprioritised
  and keeps winning claims. Deliberately left: benching on a parse failure is a routing-policy
  change, queued as a question in NEXT_STEPS §2 B.

### Minor-but-new (run #21)
- **[m90] `assay.interval_from_hands()` CARRIES A SECOND, UNCALIBRATED COPY OF THE ATTESTATION →
  UNCERTAINTY RULE, AND ITS NUMBERS BREAK THE FILE'S OWN CEILING.** Found by the run #21 audit.
  The calibrated table (`assay.py:308-316`) is deliberately rescaled so nothing can claim more
  certainty than `SIGMA_MAX = 9.9/√12 ≈ 2.8579` — the fix documented at length in the file's
  largest comment block ("Witnessed came out at 4.08 — larger than knowing nothing at all"). But
  `interval_from_hands` (`assay.py:630-631`) hardcodes its own floors:
  `{Witnessed 0.10, Instrumented 0.08, Transcribed 0.20, Reconstructed 0.40, Disputed 0.55}`.
  In decimal-band units the ceiling is `SIGMA_MAX/10 = 0.2858` (**verified live**), so
  `Reconstructed` and `Disputed` both exceed it — `Disputed` before any between-hand spread is
  even added in quadrature. It re-commits the exact defect the file documents fixing elsewhere.
  **Latent, not live: `interval_from_hands` is dead code** — grepped the whole repo, zero callers,
  and `verify_math` never exercises it, which is precisely how the bad table survived. The same
  five figures are also hand-copied into `custodes.py:229-230` (whose comment claims they are
  "DERIVED from assay()'s own attestation table" — they are not) and `verify_math.py:630`.
  **Not fixed:** deleting a public function needs a review cycle, and deriving the three copies
  from `SIGMA_BY_ATTESTATION` changes numbers. NEXT_STEPS §2.
- **[m91] THE POOL SPENT 695 CALLS IN 24 HOURS ON OLLAMA MODELS THAT ARE NOT INSTALLED.**
  `ollama:qwen2.5:14b` (357) and `ollama:llama3.1:latest` (338) failed **every** call in the last
  24h. Ollama holds exactly one model — `qwen3:8b`, the standing choice under the 2026-08-24
  GPU-only residency ruling — while the Cascade config defines **eight** `local-*` buckets, none
  of which names it; the reader 404s and removes five of them at every startup.
  **What this is NOT:** the GPU fallback is fine. The working bucket is `ollama:local`, is not one
  of the `local-*` entries, and ran **1,471 ok / 895 error** in the same window, so
  `overnight.py:655-656`'s "falls back to the GPU instead of stopping" still holds. Run #21 nearly
  filed the opposite and checked first.
  **Not fixed:** the config is `C:\Users\imarl\cascade\config.json`, which belongs to the Cascade
  project, not this repo. Owner. NEXT_STEPS §2.

### Minor-but-new (run #20)

*Its one entry, m86, moved to the paper trail in the run #38 reconciliation — its own body had
said FIXED since run #20 and nobody had moved it.*

### Minor-but-new (run #19)
- **[m85] `kill_duplicate_jobs` KEEPS THE OLDEST INSTANCE, WHICH IS THE ONE CARRYING THE STALEST
  CODE.** Verified at source (`foreman.py`, the `CreationDate` sort). Its reasoning is sound for
  its own purpose -- the oldest process is the one holding the work in progress. But combined
  with the fact that a long-lived job never re-reads its imports, the tie-break
  **systematically preserves the stalest code in the tree and discards the freshest.** Run #19
  hit this directly: the surviving foreman was 11 hours old and pre-dated run #15, while the
  accidental duplicate had started two minutes after the file was edited and carried every
  current fix. **Not a fix to make unasked** -- reversing the tie-break would kill running work
  -- but the interaction is worth a ruling. NEXT_STEPS section 2.

### Minor-but-new (run #18)
- **[m80] `feats.py:358-398` `resolve_title()` — the documented fix for a 17,148-entry loss has
  ZERO callers.** Verified by grep across all of `src/`: the only occurrence is its own `def`.
  Its docstring says it exists because *"the entity's catalogue name is not the wiki's page
  title"* cost 17,148 entries; `discover()`/`evidence_for()` use the raw catalogue name
  (`feats.py:313`) and never call it. **So that loss is, per the call graph, still unmitigated.**
  Same census found `_page_exists()` (350), `remine()` (778) and `axis_evidence()` (659) also at
  zero callers. Wiring or retiring is a decision — NEXT_STEPS §2.
- **[m83] `overnight.py:579` vs `605-608` — the post-reader pipeline pass can silently no-op.**
  Reported by audit, quoted from source: `start("pipeline")` fires background at 579, then
  `run("pipeline", timeout_h=2)` at 607 whose comment promises it *"runs after the reader so it
  sees the evidence the reader just produced"* — but `run()` opens `if running(...): return
  "already-running"` (`overnight.py:144-146`). If the 579 instance is still alive, the promised
  pass does not happen that cycle. `pipeline` is also in `STANDING`, so a third actor can start
  it. **Not verified by me at source beyond the quoted lines** — treat as high-confidence audit
  finding pending a read.

  **PARTIALLY CLOSED — run #38 reconciliation, 2026-08-29, and now read at source rather than
  quoted.** The *silently* is gone: `run()`'s already-running path logs `{name}: already running,
  left alone` and returns the distinct status `already-running`, deliberately *"so the cycle's
  summary line does not claim the stage was found already up"*, and a blind process probe returns
  `probe-blind` rather than either answer (`src/overnight.py:501-520`). **STILL OPEN:** the no-op
  itself. `start("pipeline", ...)` at `src/overnight.py:1342` and `run("pipeline", ...)` at `:1392`
  are both still in the cycle body, so if the backgrounded instance is alive the promised
  post-reader pass does not happen that cycle; `pipeline` is still in `STANDING` (`:778`), so a
  third actor can still start it.

- **[M14] THE PUBLIC PAGE REPORTS A DEAD READER'S NUMBERS AS LIVE, AND THE READER KEEPS DYING.**
  Found run #17. Two halves, and each is harmless-looking without the other.
  *The reader stops, and nothing brings it back.* `state/overnight.log` records the corpus read
  exiting **`rc=15` at 20:35:58 after 41 minutes, having printed no progress line in that time**
  — its log's last write was **19:55:16**, forty minutes before the process ended.
  **`rc=15` is NOT the finding and the next run should not chase it**: every one of the six
  recorded exits is `rc=15`, across durations of 6m, 57m, 61m, 13m, **490m** and 41m, so it is
  this reader's ordinary exit, not a crash signature. (`rc=1` ×10 and two hard Windows aborts
  sit further back in the same log.)

  > **CORRECTED, run #18 (2026-08-24). The paragraph above is wrong and this correction is the
  > reason it is kept rather than edited away.** The inference ran backwards: the durations
  > differ *because* `rc=15` is not an exit code at all. On Windows `os.kill(pid,
  > signal.SIGTERM)` is `TerminateProcess(handle, 15)`, so a killed process's returncode is the
  > signal number regardless of what it was doing or how long it had run — which is exactly why
  > it is invariant across 6m/13m/41m/57m/61m/490m. **Proven by experiment**: a child spawned and
  > SIGTERMed from Python on this machine returned exactly 15 (pinned now by `verify_math` §20a,
  > five checks). **The reader is being killed by the foreman**, via `restart_reader`
  > (foreman.py:315) or `kill_stalled_job` (foreman.py:385). The root cause and the loop it sits
  > in are **M15** below; M14 remains open as the *reporting* half (the page still cannot say a
  > reader is dead), which is unaffected by this correction.
  **The finding is the downtime.** `read.py` is deliberately **outside the keeper's `STANDING`
  set** — `overnight.py:344-347` says so explicitly: *"the keeper's STANDING set is the subset
  it can restart on its own; `read.py` and `feats.py --roll` hang off this supervisor's
  hours-long main lap."* So a reader that stops early waits for the next main lap. Measured from
  the log's own start/finish pairs, the gaps are **1 min, 8 min, 32 min, 37 min — and 4 hours**
  (16:02 finish on 08-23, 20:02 restart). It was still down **25+ minutes** when run #17 ended.
  The keeper noticed `publish` down twice in that same window and restarted it both times,
  because publish *is* in the standing set. **The project's bottleneck job is the one job the
  keeper cannot restore.**
  *The page cannot tell.* `dashboard.py:171-190` builds the corpus-read panel by regexing the
  **last matching line** out of `read_auto.log` and copying its fields verbatim —
  `"eta_h": float(r["eta"])`, nothing recomputed. That pass-through is deliberate and
  documented ("the dashboard can never disagree with the system it is reporting on"), and its
  cost is that a dead or silent reader renders as a working one, **with no staleness marker of
  any kind**. The library group has `coverage figures are current` for exactly this; the jobs
  panel has no equivalent.
  **Why Major:** it is the same shape as the completeness catastrophe and m75 — a panel
  rendering confidently off a source that has stopped answering — and it sits on the job the
  whole library is waiting for. **The remedy is a decision** (age the panel off the log's
  mtime, or have the reader stamp a heartbeat), so it is recorded, not patched. NEXT_STEPS §2 B.

- **[m79] `read.py`'s ETA READS `0.0h` ON 122 OF 122 PROGRESS LINES.** Found run #17,
  measured not inferred (`grep -o "eta [0-9.]*h" state/read_auto.log | sort | uniq -c` →
  `122 eta 0.0h`). The rolling-rate window at `read.py:1014-1024` was built to prevent this
  and its own comment names the old symptom — *"1,595 chunks per second and an ETA of 0.0 hours
  for eight hours of work — a number that is not merely wrong but reassuring, which is worse."*
  It is still reassuring. The printed "chunks/s" climbs monotonically **3,914 → 11,963** across
  the log; at the final two lines `dc = 20` chunks against a rate of 11,963.67 implies
  **dt ≈ 1.7 ms**, which is not network or GPU latency. The suspected mechanism is the eviction
  guard `while len(_rate_log) > 2 and ...` — it never trims below two samples, so a stall
  followed by two near-simultaneous cache-hit completions leaves a window of milliseconds.
  **Not fixed:** the reader was down and mid-restart, and the fix is design-adjacent — the
  fallback branch `crate = done["chunks"] / max(el, 1e-9)` needs a ruling too. Severity is
  minor as arithmetic and worse as reporting: `eta 0.0h` is what the public page prints for a
  job with 40,400 entities left.
- **[M12] THE LIVE MANIFEST CONTAINS NO FEATS CHAPTERS, SO 55,372 MINED FEATS REACH NO VOLUME.**
  Found run #16. `output/index/manifest.json` (built 2026-08-24 10:41, 88 MB) holds **9,153
  `chapter` jobs and 209 `frontmatter` jobs — and 0 of type `feats`**. The join itself is
  **healthy right now**: measured across all 210 catalogue records, `feats_index.feats_for_source`
  returns rows for **100 sources, 1,215 entity blocks**. So this is staleness, not a code defect
  — the manifest predates the reader's feats, and `manifest_builder` only emits a feats chapter
  `if feat_rows:`, which was empty for every source at build time.
  **Why it is Major rather than a chore:** it is invisible to every liveness check in the tree.
  `generate.py` is running, resumable, and correct; it is simply writing books from a manifest
  in which the feats chapter does not exist. Nothing reports a fault.
  **Remedy:** rebuild the manifest. **NOT done in run #16** — it is an 88 MB artifact feeding a
  live `generate.py`, and rebuilding underneath it is a decision, not a repair. See NEXT_STEPS
  §2 A. **Verified, not hypothesised**: both the job-type census and the 100/210 join were
  measured directly this run.

- **[M7] THE READER HAS BEEN DISCARDING ~95% OF ITS GPU WORK FOR 7.5 HOURS BEHIND A GREEN
  LIVENESS CHECK — 1,168 of 1,235 chunks handed to the card came back UNANSWERED and uncached.**
  Found run #13 by reading `state/read_auto.log` rather than a status summary; `allsweep`
  reported **nine `running` lines and 0 subsystems bad** at the same moment.

  > **UPDATE, run #15 (2026-08-24 18:30 local) — THE GATE FIX IS LIVE AND THE BLEEDING
  > CONTINUES.** Run #14 pre-registered "read one GPU-phase progress line" as the outstanding
  > verdict. It is now read, on real GPU traffic rather than cache replay:
  > `(29 to GPU, 22 UNANSWERED)` then `(44 to GPU, 41 UNANSWERED)` — **76% rising to 93%
  > discarded**, `dropped 5554` cumulative, with `ollama failed after 3 tries: TimeoutError`
  > in the log. The gate binds (read holds `GATE_LOCAL_N`=2) and it was **not sufficient**.
  > **One hypothesis was tested and REFUTED, so nobody re-runs it:** read.py does *not* share
  > the m66/m68 hardcoded-window defect — `read.config()` (`read.py:522`) reads
  > `cfg.get("num_ctx", 6144)` from `config.yaml` and therefore asks for the resident 12288.
  > The reader is not the evictor.
  > **What is left is contention and VRAM, and the physical numbers changed under us:** the
  > resident runner is now `qwen3:8b` at **12288 context occupying 8.0 GB of a 10 GB card**
  > (run #13 saw 4096 / 5.3 GB, and §2 F recorded that the 12288 window "STILL has not loaded"
  > — it has now). Against that sit `OLLAMA_NUM_PARALLEL=2`, read's gate of 2, **plus**
  > `pipeline` and `overwatch` each holding a live connection to 11434. Four claimants, two
  > slots, and a 360s deadline that a queued call cannot make.

  > **UPDATE, run #15b (2026-08-24 19:05 local) — THE MECHANISM IS FOUND, AND TWO OF THE THREE
  > LINKS ARE NOW CLOSED.** The contention was not merely "too many jobs". `gpu_lane._touch`,
  > the function that refreshes a held slot's lease, **was called from nowhere in the tree**, so
  > every call longer than `SLOT_LEASE_SECONDS` (900) had its slot reclaimed by a competitor
  > while still running — and `config.yaml`'s `request_timeout` is **1800**. `MAX_SLOTS` was
  > therefore violated by exactly the longest calls (**m54**, now fixed and pinned by §19ad).
  > Link 1 is closed too: `regime()` now requires a measured success rate, so a 4%-succeeding
  > pool no longer opens the gate to 16 (**§2 B**, pinned by §19ae). On landing, regime read
  > `local` with **2** workers.
  > **STILL OPEN: the physical ceiling.** The 12288 runner occupies **8.0 GB of a 10 GB card**
  > with `OLLAMA_NUM_PARALLEL=2`. Arbitration is now honest, but the card still serves two
  > requests at a time and the reader's own re-work grew: **M10's fix orphans 8,194 cached
  > chunk answers**, all of which must be re-asked. Expect the discard rate to move for TWO
  > reasons at once next run, and measure before attributing.
  **The chain, every link measured:**
  1. `tuning.regime()` answers `"cloud"` whenever `_answering_buckets() >= CLOUD_MIN_BUCKETS`.
     That is a REACHABILITY proof, not a capacity one — the lesson already in `NEXT_STEPS` §5
     ("the pool proof says 4 of 36 buckets answer and it is true; the live rate is 2.8%"). It
     read `"cloud"` this run while the measured cloud success rate over the previous hour was
     **4.1% (40 ok of 976)** and **18% lifetime over 26,094 calls**.
  2. So `read._gate()` handed every worker the wide `GATE_CLOUD_N = 16` gate.
  3. The ladder in `_ask_ungated` tries the pool twice, then falls to the GPU. At a ~4-18%
     cloud rate that means nearly every chunk lands on the card — **`read.py` (PID 17492) was
     observed holding 9 established connections to Ollama** against `OLLAMA_NUM_PARALLEL = 2`.
  4. Seven of nine therefore sit in the daemon's queue. Measured directly: a trivial 7-token
     call took **113s and 178s of pure queue wait** (`eval_count: 7` both times) against
     **0.58s** on the same window with the card unloaded.
  5. That exceeds `_local`'s **180s** timeout, which benches the card for `GPU_BENCH = 900` and
     **drops the chunk — "UNANSWERED, not cached"**, so no later pass knows to look again.
  **This is precisely the pile-up `GATE_LOCAL_N = 2` was written to prevent** ("the surplus
  workers WAIT at the gate instead of stacking onto the card") — it did not bind because the
  gate's width is chosen from what the regime is CALLED, not from where the traffic actually
  goes. First `ollama failed after 3 tries: TimeoutError` at **09:02:18**; **137 of them** in
  the log; unanswered rate **85-100% from the very first GPU handoff onward**.
  *(The high early "chunks/s" rows in that log are cache replay, not a healthy baseline — the
  honest constant is the discard rate, which was never good.)*
  **PARTIALLY FIXED run #13, NOT YET LIVE.** `read._local` now takes the card's gate
  unconditionally via a new `_card_gate()`, so only `GATE_LOCAL_N` calls touch the card whatever
  the regime is called. The permit is tracked **per thread**, because `_gate()` hands out that
  same semaphore when the regime reads `local` and a nested acquire of a `BoundedSemaphore` from
  a thread already holding it deadlocks every worker — that shape was caught before shipping and
  is pinned by verify_math §19t (4 checks: bounded + no-deadlock, in both regimes; 12 threads
  peak at 2, 0 stranded).
  **THE GATE IS NOW LIVE AND MEASURED BINDING IN PRODUCTION — run #14, 2026-08-24 17:42
  local.** `read.py` was **already down** when this run began (the supervisor's own lap ended
  it at 17:05:34, `rc=15 in 490m`, and the page flagged `every managed job is running =
  dashboard.py,read.py`). Its own lap could not restore it for ~3.5 more hours — it was blocked
  in `join(roll, timeout_h=4)` behind a roll with a 6.3h ETA — so run #13's "a bounce costs
  real downtime, it is the owner's call" no longer described the situation: **there was no
  running reader to interrupt.** Restarted with the supervisor's own arguments
  (`--run --workers auto`, via `overnight.start`, so the singleton guard still holds).
  **Measured immediately after: `read.py` holds exactly `2` established connections to Ollama,
  against the `9` run #13 measured.** That is `GATE_LOCAL_N`, binding, in the `cloud` regime —
  the first production evidence the fix does what the 12-thread harness said it would.
  **The discard rate is NOT yet re-measured** and this run could not do it: a restarted reader
  replays its cache first (`0 to GPU, 0 UNANSWERED` at 10,000+ chunks/s, which is exactly the
  cache-replay artefact this entry already warns is not a healthy baseline). **The verdict
  needs the next run to read a progress line from the GPU phase.**
  `read.py` remains NOT keeper-restored (see m56's restart topology), so if it exits again it
  stays down until the supervisor's lap comes round.
  **THE BLAST RADIUS IS NOT CONFINED TO `read.py` — it starves every other model consumer on the
  box, and this is what makes M7 the most expensive item on the ledger.** `read.py` saturates the
  card; everything else then finds it busy and falls to the same 4% cloud:
  - **`overwatch` produces nothing, slowly.** Its 16:40 round reported `0 raw 0 new` for EVERY
    module with the note `(GPU busy; 8 calls to the cloud)`, and `cascade_bridge` took
    **7,873 s (2.2 hours) to return zero findings**. **This is the honest explanation of m40's
    flat `70 rounds / 66 findings`:** the standing rule says only a number that goes DOWN is a
    bug, and this one is not going down — it is not going anywhere, because the rounds run and
    find nothing. **Flat is a SYMPTOM here, not an all-clear.**
  - **`ingest_doc` (Dragonlords) is alive but stalled** at chunk 22/252 — `no transport; napping
    300s (miss 2/60)`. It is no longer a GPU holder, which is the only reason the card was idle
    enough this run to take a control measurement at all.
  - **`pipeline`, `foreman` and `overwatch`** all log the same `ollama failed after 3 tries:
    TimeoutError`.
  So ~95% discard is the *measurable* cost; the *unmeasured* cost is every analysis job on the
  machine running at cloud-failure rates behind it.
  **STILL OPEN AND NOT THIS RUN'S TO DECIDE (link 1 of the chain):** should `regime()` decide on
  a measured success RATE rather than on reachability? That changes `profile()`/`workers()`
  globally, so it is a design question — see `NEXT_STEPS` §2 and m59, which is the same root.
- **[m60] 22 CHAPTER BLOCKS ARE STILL TOO LARGE FOR THE WINDOW — the bounded residue of M6.**
  After M6's fix (see paper trail) **17,557 of 17,579 chapter calls fit; 22 do not**, across 22
  jobs, worst needing **9,909 tokens more than the 12,288 window**. These are single
  `WRITE_CHUNK` groups whose eight entries are enormous — the largest rendered block prompt is
  **46,840 chars** against a p99 of 11,978, so this is a long tail, not a systemic fault.
  **The behaviour today is correct**: each raises `ContextOverflow` and is recorded rather than
  silently truncated. **The remedy that did NOT work for M6 now DOES work here** — M6 refused
  even an empty prompt, so shrinking the group could not help; these 22 refuse only because of
  content volume, so splitting the group further fixes them. Options: lower `WRITE_CHUNK`
  globally (**8 -> 4 would roughly double the call count for all 9,153 jobs to fix 0.13%** —
  poor trade), or split adaptively only when a block does not fit (better, but it is new
  machinery in `generate_job`'s loop and changes a deliberate constant — `config.yaml` records
  that `WRITE_CHUNK` was tuned 30 -> 10 -> 8 for instruction-following reasons, not context
  ones). **Filed rather than fixed: it needs the owner's call on which trade to take, and 22
  loud refusals are not costing anything while generation waits on the omniverse history.**
- **[m56] THE `gpu_lane` AND KEEP-WARM WORK LANDED AT 13:59-14:20 IS NOT LIVE IN A SINGLE
  RUNNING JOB, so the contention it was written to arbitrate is still completely
  unarbitrated.** A Python process does not re-read its own source: every standing job predates
  the code. Verified run #12 from process start times against file mtimes — `read.py` and
  `feats.py --roll` 08:55, `pipeline.py` 11:17, `foreman.py` 11:22, `overwatch.py` 11:37,
  `ingest_doc.py` (Dragonlords, still running after 17 h) 2026-08-23 21:32, `overnight.py`
  2026-08-23 21:30 — against `gpu_lane.py` created **13:59** and wired into
  `pipeline.ask` / `generate.call_ollama` / `local_agent` at **14:12**, and `overnight`'s
  keep-warm thread added at **14:19**.
  **Corroborated, not merely inferred:** `gpu_lane.status()` sampled six times over a minute
  reported **0 slots and 0 foreground holders** while `nvidia-smi` reported **99% GPU
  utilisation** and `pipeline.log`, `read_auto.log` and `overwatch.log` logged
  `ollama failed after 3 tries: TimeoutError` continuously.
  **What is actually contending:** three steady clients on the daemon across a 48 s sample —
  `ingest_doc` (17 h old), `overwatch`, `pipeline` — against `OLLAMA_NUM_PARALLEL = 2`.
  `read.py`'s load is NOT on the card; it is going to the cloud (see m59).
  **NOT BOUNCED THIS RUN, deliberately, and the reason is in the restart topology:** the keeper
  restores only the STANDING set (dashboard, publish, foreman, overwatch, pipeline) and only
  when it finds a job DOWN, so pipeline/overwatch/foreman will otherwise carry pre-lane code
  forever; but `read.py` and `feats.py --roll` hang off the supervisor's hours-long lap, and
  `ingest_doc` is a hand-launched job with no restarter at all. Bouncing only the cheap half
  puts the participants under a 2-slot cap while the actual GPU holders ignore it. **Also, a
  second Claude session was live in this repo during run #12** (its probe process was observed
  on the daemon), which is not a moment to restart nine jobs. Ordered recipe in `NEXT_STEPS.md`.
- **[m59] THE CLOUD LANE IS IN A HOT RETRY LOOP AT A 2.8% SUCCESS RATE, and the pool proof
  cannot see it because it measures reachability, not capacity.** Measured run #12 from
  `state/model_metrics.jsonl`: **1,571 cloud calls in the last 60 minutes, 44 succeeded
  (2.8%)**; over 3 hours, 4,778 calls / 152 ok (3.2%). That is ~26 calls per minute against
  free-tier providers, 97% failing, sustained. Meanwhile `data/POOL_PROOF.json` (written 14:01)
  says **4 of 36 buckets answer** — over the `>= 3` gate, so `ask_pool_first` keeps choosing the
  pool. Both readings are honest: the proof sends one trivial probe per bucket and certifies
  that a bucket ANSWERS, which is not a claim about throughput under a 26/min load. **This is
  the same shape as m51** — a check that is true and scoped to less than its name implies.
  The caller is `read.py`'s `_ask` (`read.py:335, 351`, `CB.ask` defaults to `pool="coding"`),
  whose own progress line reports the cost plainly: **989 of 1,012 chunks UNANSWERED** and a
  corpus-read ETA swinging between 59 h and 10,813 h. Unanswered chunks are recorded as "not
  cached", so this is waste and delay rather than data loss. **QUESTION, not a fix: should a
  bucket that fails N consecutive live calls be stood down until the next proof, and should the
  proof measure a rate rather than a single answer?** Filed rather than patched because backoff
  policy is a design decision and m24's paper trail shows how easily a bucket gets buried.
- **[m58] THE `folder-mechanical` ROUTER FILES RACES AND BACKGROUNDS UNDER "Places &
  Locations" — QUESTION, because the mode may be doing exactly what it says.** Found while
  root-causing the manifest's largest job (`NEXT_STEPS` run #11 item 3.4, now closed): the
  52,101-char outlier is `The Elements Beyond` `II.L.7.45/Places#1-10`, and its size is honest —
  three homebrew race writeups with ~11.6 KB `description` fields (Deepling 12,104, Crystalkin
  10,426, Fairy 8,064). **The anomaly is not the size, it is the contents:** all ten entries in
  that Places chapter are `type` Race, Sub Race, or Background, and not one is a place. Their
  `category` field is just the chapter label copied down, so it carries no independent signal.
  Scope: **42 sources are `folder-mechanical`** (760 chapter jobs); the `web` mode looks sane by
  comparison (Places chapters there hold Location 7,480, Place 260, Planet 165, City 142) though
  it files 647 `Character` entries under Places too. **Is folder-mechanical routing meant to be
  provisional — the entries land by file and a later pass re-shelves them — or is this a
  misroute?** The shelfmark says `[UNCHARTED -- Ladder-of-Being pass not yet done]`, which reads
  like the former, so this is a question and not a strike.
- **[m51] `health.py`'s "context budget" preflight does not cover the path that overflows —
  its `ok` is false assurance.** `check_context_budget()` (`health.py:168-190`) imports
  `read as R` and measures **`R.SYSTEM` (read.py's own 1,586-char feats-extraction prompt)** and
  `R.CHUNK` (read.py's 10,000-char wiki-passage size). That is the wiki-READING pass. It never
  touches `prompts/system_style.txt` or any `generate.py` job, so **the writing path measured in
  m52 has zero static coverage anywhere in the codebase** — and the preflight prints `ok
  context budget` while 94% of chapter jobs are over their window. The check is not wrong about
  what it measures (read.py's pass genuinely fits: 3,799 tok vs 6144, a 38% margin, and it
  passes under every divisor tested, so its result is not an artifact of the divisor). It is
  scoped to one of two paths and named as though it covered both.
  **Minor sub-finding, cosmetic:** the same sum uses two chars-per-token divisors —
  `len(R.SYSTEM) / 4` and `R.CHUNK / 3.7`. The 3.7 is sourced (`read.py:56-58, 67-68`, cited for
  English wiki prose); the `/4` for instruction text has no citation found. It does not change
  the outcome here — worth a comment, not a fix.
- **[M4] The paid burst counter stands at 598 against a cap of 500 — HUMAN CALL on what to do
  about it.** The enforcement bug is FIXED (run #6, see paper trail): no paid bucket is a
  candidate unless the lane is open, and both documented kill switches now genuinely kill. What
  remains is the owner's decision, and the reason this is filed Major rather than closed: ~98
  calls (~$1.96 at the file's own `est_usd_per_call`) were spent past a hard cap, the counter was
  **deliberately not reset** because it is the evidence, and the lane currently reads
  `enabled: true` with `used > cap` — so it is closed by the cap, not by intent. Raise `cap`,
  set `enabled: false`, or delete the file (deletion is now safe; before the fix it was the worst
  of the three, since it silenced the counter without stopping the spend).
- **[M3] fandom.com is dropping connections at the socket** — measured 2026-08-24 08:35:
  `marvel.fandom.com` api and html, `dc.fandom.com`, `onepiece.fandom.com` all HTTP 000 after
  20–21s; `en.wikipedia.org` answers in 0.25s from the same machine. A live probe run took 129s
  per probe, all 8 failing. NOT a code fault and not auto-fixable — an IP block or edge drop
  that has cleared on its own before. Everything fandom-facing is blocked behind it: page roll
  52%, reachable-wiki 90%, the completeness audit. `run_completeness_audit` and
  `run_catalogue_gap` are both now gated on `_fandom_reachable()` so neither dispatches into it.
- **[M1] dandwiki.com is API-blocked (HTTP 403 to every non-browser client)** — 4 homebrew
  sources unhosted; HTML answers a browser UA, so a design decision is needed: build an
  HTML-path reader with a browser UA (politeness/ToS question — HUMAN CALL) or leave the four
  sources owner-supplied. Noted in `data/SCOUT_BLOCKED.json`. Not auto-fixable.
- **[m42] BOUNCING A STANDING JOB ORPHANS ITS LONG-RUNNING CHILDREN, and the orphan then writes
  shared state from a stale snapshot.** Found live in run #9. `foreman.adopt_hosts()` shells out
  via `subprocess.run(..., timeout=1800)` to `hostcheck.py --adopt --go`. `subprocess.run` does
  kill its child on timeout — but only if the PARENT is still alive to do it. Run #8 bounced the
  foreman at 11:22 to ship the m40 fix; the foreman it replaced had launched a `--adopt` child at
  11:15:25 which was left with **parent PID 35128, a process that no longer exists**. Its killer
  was dead, so its 1800-second timeout could never fire, and at 12:20 it was still alive with
  2.9s of CPU over 65 minutes (blocked on fandom sockets, which are down — M3). `adopt()` ends in
  `hosts.update(found); _land(F.HOSTS, hosts)`, a **whole-file replace of `WIKI_HOSTS.json` from
  the snapshot it read at 11:15**, and the CURRENT foreman had meanwhile launched a second,
  legitimate `--adopt` (PID 17724, parent 5420, started 12:15:27). Two processes, each holding
  its own snapshot, each ending in a whole-file write: whichever landed last would silently
  discard the other's adoptions.
  **This is m40's exact shape one run later in a different module, and it was CREATED BY the act
  of shipping m40's fix** — every keeper bounce of a job that shells out to a slow child makes one.
  Damage this time was nil (`WIKI_HOSTS.json` was untouched since 08:55, md5 `451703b8…` before
  and after) because neither had finished; the orphan was killed and the ledger verified. **The
  instance is closed. The missing guard is the open bug**, and it has two candidate fixes, which
  is why it is filed rather than patched: either `_land` gains m40's digest-compare (write only
  if the file is as it was read, else re-read and merge), or long children are made to notice
  their parent is gone. `hostcheck._land` is atomic (`tmp` + `replace_retry`) but **atomicity is
  not the property that was missing** — a stale whole-file write lands perfectly intact.
- **[m43] Nothing in the kit detects an orphaned child**, which is the reason m40 and m42 were
  both found by hand. Run #8 said as much in prose; run #9 found the second instance 65 minutes
  later, so this is now a recurring cost rather than an observation. A check is cheap and
  self-contained: any `panscriptum` python process whose ParentProcessId names a dead process is
  an orphan by construction. Candidate home is `allsweep`'s RECONCILE block or `health
  --preflight`. **Not self-authorized in run #9** because it adds a new reported subsystem and
  the two runs that hit it disagree about the right remedy (kill vs. report).
  **RUN #10 REFINEMENT — the proposed rule is wrong at BOTH ends, and the evidence is M5.**
  (a) *It would have missed the orphan that actually cost this project anything.* The rule as
  written scopes to "a **panscriptum** python process whose parent is dead". M5 — the orphan
  holding 13,942 sockets to the Ollama daemon and starving the entire local rung for three runs
  — is `semsearch.cli watch`, which matches nothing in this repo. **The damaging orphan was a
  FOREIGN process contending for a SHARED resource.** Scoping the check by command line looks
  natural and encodes the assumption that only our own strays can hurt us.
  (b) *It false-positives on the root of our own tree.* `autostart.py --watch` (PID 28188)
  legitimately has a dead parent — it is the launcher, started at login by the VBS shim, and
  its parent exited by design. A naive "dead parent ⇒ orphan" check reports the supervisor's
  own root as an orphan on **every** run, forever.
  So the useful check is probably not "whose parent is dead" but "**what is holding the
  resources we need**" — clients on `11434`, handles on our state files — which is a different
  and more honest subsystem than the one m43 originally proposed. Still an owner call.
- **[M8] EVERY FANDOM CONTENT WIKI IS UNREACHABLE OVER IPv4 FROM THIS MACHINE, AND THE ONE
  STANDARD BUILT TO CATCH THAT READ GREEN THROUGHOUT.** Found run #14 from the page: three
  HIGH library standards were red at once (`every source is fully catalogued = UNMEASURED --
  164 rows, 0 measurable`, `sources with a reachable wiki = 90%`, plus preflight's `fandom API
  unreachable: aneurism.fandom.com`) while `fandom answers this machine` said **reachable**.
  **Measured, and the measurement is the whole finding:**
  - `community.fandom.com` connects in **0.05s**; `aneurism`, `forgottenrealms` and `marvel`
    all **time out at 16s**.
  - All four resolve to the **SAME two Cloudflare IPv4 addresses** (`162.159.142.170`,
    `172.66.2.166`) — so it cannot be a per-host fault.
  - Connecting to those literal IPv4 addresses times out **including for `community`**. What
    saved `community` is that it is the **only fandom host publishing AAAA records**: it was
    answering over **IPv6, in 0.02s**, and `create_connection` stops at the first family that
    works. Every content wiki is **A-record-only**, so IPv4 is the only path they have.
  - IPv4 is fine in general from here: Wikipedia, GitHub and 1.1.1.1 all answer in **<0.05s**.
  **THE STANDARD IS FIXED (`6fb290d`); THE OUTAGE IS NOT, AND IS THE OWNER'S CALL.** The probe
  is now `standards.fandom_ipv4_reachable()` — family pinned to `AF_INET`, aimed at
  `marvel.fandom.com` (a content host this corpus actually binds), and it now correctly reads
  **`holds=False — IPv4 connect fails: 172.66.2.166 TimeoutError`**. Pinned by verify_math
  **§19z** (4 checks driven off a stub network, so they pin the FAMILY and not the weather;
  the second reproduces the exact 2026-08-24 configuration and must come back False).
  **What this run did NOT do, deliberately: route around it.** The IPv6 path works, and
  forcing traffic onto it would evade a block the destination may have applied on purpose.
  Two readings fit the evidence and this run cannot separate them — (a) Fandom is blocking
  this machine's IPv4 address, the same shape it earned once before on 2026-08-23, or (b)
  something between here and Cloudflare's IPv4 edge is dropping SYNs. **Owner decision.**
- **[m65 — RESOLVED `6fb290d`] THE CATALOGUE'S FANDOM GATE HAD BEEN ANSWERING "OUTAGE" ON EVERY
  CALL IT EVER MADE, BECAUSE IT NEVER SENT A USER-AGENT.** Found run #14 while checking whether
  M8's fix would cascade into any automated remedy — it did not, but the gate it led to was
  broken in the opposite direction. `foreman._fandom_reachable` had been hardened that same
  morning from a TCP connect to a real API call, on the correct reasoning that **a socket is
  not an answer**. The rewrite called `urlopen` on a bare URL, so the request went out as
  `Python-urllib/3.13` and MediaWiki replied **403 Forbidden in 0.13 seconds** — from fandom
  **and from Wikipedia**, healthy or not. With the project's own `wiki_source.UA` the same two
  URLs return **200**. So `run_catalogue_gap` deferred the catalogue **every foreman round**
  while reporting "fandom.com is dropping connections (IP block or outage)".
  **A gate that always says "outage" is not conservative, it is off** — and it is invisible,
  because its false negative is phrased as a plausible diagnosis. Note the shape: the morning's
  fix was right about the defect and introduced its exact inverse, which is why both are now
  recorded in one docstring. Fixed to send `wiki_source.UA` and to ask
  `standards.FANDOM_PROBE_HOST` (a content wiki) rather than `community.fandom.com`, which
  cannot fail correctly. It now returns False in **16.1s** — the honest timeout — instead of
  False in 0.13s. Pinned by verify_math **§19aa** (5 checks driven off a stub opener: the UA is
  present and is not `python-urllib`, a 200 opens the gate, a 403 does not, and the URL names a
  content host).
### Minor
- **[m47] an exception inside the feats join silently becomes "this source has no feats."**
  `manifest_builder.py`'s Feats block wraps `feats_index.feats_for_source` in
  `except Exception: silence.note(...); feat_rows = []`, and the job-creating block below is
  gated on `if feat_rows:`. A source whose join RAISED is therefore indistinguishable from a
  source with genuinely nothing mined, and it loses its **entire** Feats chapter rather than
  the one entity that broke. Reachable via `feats_index`'s unguarded `.get()` calls on
  catalogue entries and feat items: one non-dict item anywhere in a source's `entries` or in
  one `readfeats` file raises `AttributeError` and takes the whole source down with it.
  **Verified DORMANT today** — scanned all `data/records/*.json` and all 1,241
  `data/readfeats/**/*.json`: zero non-dict items. Filed rather than patched because the fix is
  a contract choice (fail loud and lose the run, or record the skip somewhere the owner
  actually reads — `output/index/failures.json` is the file CLAUDE.md points at and manifest-
  build-time skips never reach it). This is the exact shape `silence.py`'s own header essay
  names as the project's recurring defect: the loss gets filed as a result.

  **PARTIALLY CLOSED — run #38 reconciliation, 2026-08-29.** The indistinguishability is gone. The
  Feats block's exception path now PRINTS as well as noting — *"feats lookup FAILED for X (…) --
  this volume will carry no Feats chapter, which is NOT the same finding as a source with no
  attested feats"* — so a raised join no longer reads as a source with nothing mined (found by the
  run-33 sweep, batch 15). **STILL OPEN:** the blast radius and the filing question, which is what
  this entry actually asked a ruling on. The job-creating block is still gated on `if feat_rows:`
  (`src/manifest_builder.py:359`), so one non-dict item anywhere in a source's entries or in one
  `readfeats` file still costs that source its ENTIRE Feats chapter rather than the one entity that
  broke, and the skip still never reaches `output/index/failures.json`, which is the file CLAUDE.md
  points at.

- **[m48] 70 sources carry catalogue entries whose names collide under `feats_index._norm`,
  and only the first survives the join map.** `entries_by_norm.setdefault(_norm(name), e)`
  keeps the first entry per normalised key. Measured across all 209 record files: **70 sources
  affected**, worst `dr-firestorm-s-engineering-corps.json` with **125 collisions**, then
  `adventurers-league` and `all-black-ops` at 75 each. Zero entries normalise to the empty
  string, so the degenerate case is absent. Two distinct causes are mixed in the count and they
  want different answers: exact duplicates (`Power Boots` vs `Power Boots`, `KGB` vs `KGB` —
  a catalogue-quality question about duplicate entries) and genuine spelling folds
  (`New Hampshire Darkmagics` vs `Newhamp Shire (Darkmagics)` — the join doing its job).
  **Not a data-loss bug as far as measured**: the feats still attach to the surviving twin and
  still reach the chapter. What is lost is the ability of the second entry to carry evidence.
  **Owner call** on whether duplicate catalogue entries should be merged upstream; do NOT
  "fix" this by loosening `_norm`, which §19o forbids for the reasons in m45's paper trail.
- **[m44] `hostcheck.null_rate` computes its sampling stride from the WRONG list — currently
  inert, deliberately not fixed.** `foreign = sorted(set(foreign))[::max(1, len(foreign) //
  sample)][:sample]`: the RHS is evaluated before the assignment, so `len(foreign)` is the length
  of the list WITH duplicates while the stride is applied to the DEDUPED one. Measured on the
  live corpus: raw 618, deduped 599, so the stride is 15 where it should be 14 — and both yield
  the full 40 names, because dedup only removes 19. **Fixing it would change the control sample
  for every host and therefore host-adoption verdicts, for no gain while it returns the right
  count.** Filed so the next reader who spots it knows it was measured and left alone on purpose;
  becomes live only if the roster ever dedups heavily.
- **[m26] the completeness audit structurally cannot see 46 of 210 sources** — `audit()`'s
  `todo` is filtered on `subdomain(h)`, which only resolves fandom hosts, so the 21
  Wikipedia-hosted and 25 other-hosted sources have never been in scope. Not widened silently
  this session: a measure called "completeness" that ignores a fifth of the corpus is a naming
  and design question (should it measure them, or should it be renamed to say what it measures?)
  rather than a bug to be patched. **Owner call.**
*(m23 -- job logs truncated on restart -- was fixed at 14:23 and its Open entry was removed by run #12; verified at source: `overnight.py` now opens each job log in append mode with a dated session separator. Paper trail below.)*

- **[m1] Marvel completeness row 25h stale** (0.4% vs 30,207 on disk) — re-measure was
  launched this run (`completeness.py --workers 6`); verify the row after it lands. If still
  wrong after a fresh run, the byslug matching in `completeness.py` becomes a real suspect.
- **[m2] `sources on the roll but never catalogued`: 6** (HAWX, Heaven's Lost Property, Lost
  Mines of Phandelver, Twilight Imperium, +2) and **16 catalogued sources with no host** —
  scout/adopt remedies keep retrying; some (music albums, board games) may be permanently
  hostless and deserve an owner ruling on whether they stay on the roll.
- **[m13] `pipeline.py phase_synthesis`'s 14-entity ceiling-nomination sample can silently
  clamp the whole source to a lesser band** — the sampled 14 (by feat-count then description
  length) may not include the source's true strongest entity; that entity's own later-mined M6
  feat then gets clamped down to whatever lesser ceiling was nominated. UNCERTAIN whether this
  is Hard-Rule-0-shaped; HUMAN CALL requested in NEXT_STEPS.
- **[m16] `weave.py`'s per-pair `shared_sample` field is capped (8, then re-sliced to 6)** —
  diagnostic evidence for why the weave linked two shelves, not a reader-facing catalogue
  listing, but Hard Rule 0's text says "no sample" without carving out diagnostics explicitly.
  HUMAN CALL requested in NEXT_STEPS rather than assumed out of scope.
- **[m24] `cascade_bridge.dead_forever` buries buckets for three undocumented reasons** — the
  docstring says exclusion is permanent-codes-only (401/402/404/410) and that "a timeout, a 429,
  or a silent minute excludes nothing", but the code also buries on the substrings `no such
  model`, `needs billing`, `bad key`. **Currently inert** — verified that no writer of `verdict`
  produces those strings today (`prove()` writes `answers`/`no answer`/`local`, an exception
  class name, or `provider disabled`/`no API key`). It becomes live the moment a verdict carries
  an exception *message* instead of its class name. Contract question rather than a defect:
  should those three be permanent exclusions (then document them) or not (then drop them)?
- **[m37] `data/CHAIN.json` is written every cycle and NOTHING reads it — CONFIRMED run #8,
  and now the only part of m37 still open.** Verified repo-wide, not just `src/`: the string
  `CHAIN.json` occurs in exactly two places outside documentation and this ledger — `chain.py:53`
  (`OUT`, the writer) and `chain.py:92` (its docstring). `pipeline.py:1255` imports chain and
  drives the WRITE side. No consumer exists in `src/`, in the dashboard, or in the published
  site. So `write_result` persists the edges, the Bradley-Terry strengths and the Ford's-condition
  `identified` verdict every cycle, and the cross-check the module's docstring calls its entire
  purpose ("the only one that checks the others") is never performed against the Assay.
  **HUMAN CALL — this is a design question, not a repair**: wire a consumer that actually runs
  the cross-check, or say plainly that CHAIN.json is an archival record and stop calling it a
  check. Deliberately not self-authorized in run #8: inventing a consumer invents a contract.
  *The audit agent's other three claims about this module were all verified true and are FIXED
  in run #8 — see the paper trail (`[:120]` dedup key, bare `open(OUT,"w")`, discarded
  `replace_retry`). The agent was right about WHERE and WHY on every one of the four.*
- **[m38] `foreman._function_source()` resolves a symbol by bare name with no uniqueness
  check.** `symbol.split("(")[0].split(".")[-1]` deliberately strips a class qualifier, then
  takes whichever same-named function `ast.walk` reaches first. A finding naming
  `ClassA.validate` can therefore hand `ClassB.validate`'s body to the model lane and, with
  `--patch` live, overwrite the wrong function with a fix meant for the other — syntactically
  valid, so `_checks_pass` need not catch it. Verified in source; not fixed this run because the
  right behaviour (refuse an ambiguous symbol? honour the qualifier?) is a contract choice.

  **PARTIALLY CLOSED — run #38 reconciliation, 2026-08-29.** The contract choice this entry left
  open was made, in favour of *honour the qualifier*. `foreman._function_source`
  (`src/foreman.py:1129-1153`) resolves a dotted symbol against the enclosing scope, so a finding
  naming `ClassA.validate` can no longer be handed `ClassB.validate`'s body — the harm this entry
  names, and the comment there cites `verify_math.py`'s five `__init__`s as the live surface.
  A qualifier naming no scope in the file falls through unchanged. **STILL OPEN:** the bare-name
  fallback at `:1155-1160` still takes whichever same-named function `ast.walk` reaches first, with
  no uniqueness check, so an UNQUALIFIED ambiguous symbol is still resolved by walk order.

- **[m29] `cleanup.py`'s `_EMPTY_MECHANIC` predicate cannot tell a rules construct from a real
  entity whose description failed to fetch.** It strikes an entry when the description is empty
  AND the name ends in `variant|feature|trait|slot|...`. But an empty description is a signal this
  project has repeatedly shown to be unreliable (`feats._unwrap_templates` turned 190KB pages into
  30 characters and it "read as CORRECT SILENCE"), and real entities do end in those words —
  Marvel's Loki *Variants* are the obvious case. **Relevant now in a way it was not before**: run
  #6 made exclusions durable, so a wrong strike is now permanent rather than being undone by the
  next entrypass. **Owner call before `cleanup.py --apply` is run again** — and note that the 149
  entries struck earlier have all since been flipped back, so re-running is what would re-strike
  them. Deliberately not re-run this session.

*Open items are now: two operational blocks that are not code faults (M3 fandom, M1 dandwiki),
one money decision (M4), three contract questions (m24, m25, m26), the standing HUMAN CALLs
(m12, m13, m16, m29 and M1), two contract choices raised by run #7's audits (m38, m39), one
CONFIRMED design question (m37 — CHAIN.json has no reader) and two watched states (m1, m2).
Run #7 resolved m27, m28 and m30 and added m31-m36. Run #8 confirmed m37's core claim, fixed
its three sub-findings, and added m40 (stale overwatch writer) and m41 (hash-seed-dependent
nav names) to the paper trail. **Nothing on the open list is a live data-loss risk; every
remaining item is either an outage, a decision, or a watched state.***

## Watching (not bugs — expected states with a clock on them)
- **`MAX_JOB_SILENCE_MIN = 15` is a live threshold as of run #3** — the stall detector could not
  previously reach it (see the Resolved entry). During run #3 a healthy `roll_auto.log` sat
  unchanged for 4.5 minutes; a page roll waiting on a slow host could plausibly cross 15 and
  trigger the AUTO kill remedy. Watch for false alarms; raise the constant if they appear.
- **Local model throughput is the live constraint.** Not a 503 any more (that was the run-#3b
  wedge, resolved) — the runner is up and measurably pegged at ~8 cores, but a 30B MoE at 8.5 GB
  on a 10 GB card means heavy CPU offload, and a phase-2 batch can sit for a long time. Run #4
  watched `units_done` hold at 3382 across a 40s sample with the state file freshly written:
  blocked inside one call, not broken. If phase 2 makes no measurable progress over a few hours,
  the question is model choice / offload split, not correctness.
- ~~`entries stranded in closed batches`~~ **CLEARED to 0 in run #4** — moved to the paper
  trail. `health --preflight` now reads `ok  state consistency`.
- Charter regression: `data/CHARTER_REGRESSION.json` **landed** (22:24, run #3 confirmed it on
  disk). Verify the `automation reproduces the charter` standard now takes a real reading.
- Dragonlords ingest miner: patient loop (60-miss ≈ 5h), waiting out the evening pool for the
  midnight free-tier window. Cursor at chunk 1/252 after the writer fix.
- Deferred assay backlog (heavyweights, Jace accessions, Infinity Gauntlet) self-requeues
  when the pool window rolls.

## Resolved (paper trail)

### Run #39 (2026-08-30) — the mutation tester was measuring its own sandbox

*A shift, not a reconciliation: this section records what run #39 closed in the WORK-ORDER queue,
because those closures are where the evidence is. The full resolutions, uncapped, are in
`state/workorders_closed.jsonl` under the ids below. Nothing was moved out of `## Open` this run;
see the marker at the top of that section and order `ca0a93856e2a` for why.*

**Root causes, not symptoms:**

- **`21ae41adc29c` — the mutation sandbox was never a copy of the library.** `state/` was walked
  one level deep, so `state/sweep_shards/` never arrived; and the six logs `dashboard` reads went
  out with the blanket `.log` exclusion. Five `verify_math` rows were therefore RED in the
  baseline of every mutation run this project has ever made, and a net that is red in the baseline
  is disabled as a detector. Baseline 1055/5 FAILED → **1063/0**. Fixed in `mutate.sandbox()`:
  recursive `os.walk` over `state/` for `.json`/`.jsonl` (whole payload 0.23 MB), plus the six
  logs derived from `lognames`' own constants rather than hand-kept (4.3 MB).
- **`5a24b2956be8` — `drill.denied()` counted "no such file" as a gate refusal**, so the one net
  proving the allowlist's fail-closed half against a name invented after the lists were written
  held over an agent with every gate deleted. Reproduced before fixing. Knock-on: six *more* nets
  in the same area were passing for the wrong reason inside every mutation sandbox, because the
  four junctioned trees resolve outside it. Sandbox drill **6 BREACHED → 0**.
- **`c24fcbb8a291` — 62.6% of the paper trail was the battery rehearsing itself.** Eight ids,
  1,852 of 2,960 rows, three of them recorded at MAJOR on the RUN rung. Rehearsals now go to
  `state/workorders_selftest.jsonl`. The existing rows were **not** rewritten — append-only
  history is not tidied. The drill's own litter net was widened to watch the closed log, and
  watched going red against the pre-fix behaviour.
- **`5905045ff433` — `publish.py --loop` asserted the halt once at startup and never again.** An
  OWNER halt raised while the daemon was up never reached it, and it kept pushing to the PUBLIC
  repo on its timer. `codewatch` does not cover this: it fingerprints `src/`, and a halt is stale
  STATE, not stale code. Now re-asserted every cycle, and it BREAKS rather than retrying.
- **`455e2ba51fcf` — the secret gate failed OPEN.** With the export tree absent the scan did not
  run, and both BLOCKING orders were then closed, `SECRET_IN_EXPORT` with the literal resolution
  "scanner is clean". Now gated on the scan having happened.
- **`82adb37c6cfc` / `7dd2672546b1` — the free rung could not do anything.** `t_grep` refused a
  file as `subtree` and the model burned 24 turns and 70 tool calls retrying the same rejected
  call; and a run producing neither a patch nor an answer reported `ok: true`.
- **`1d54acf05414` / `9b54659bc403` — 13 of 28 LOCAL orders (46%) were undeliverable**, addressed
  to a rung structurally forbidden to write their target. Re-addressed to RUN, and a detector
  added.
- **`fff84beb3e0f` — a confirmed non-equivalent mutant had no check behind it.** Two rows added to
  `verify_math` for `assay()`'s epoch field, watched going red against the exact mutation.
- **`07cb6bdabd36` — allsweep's daemon roster was a mention test.** It reported "publish.py: 2
  processes" against a process table holding one. Fixed to ask `_cmd_is_running` — and that helper
  was then found to have the same hole for `python -m <tool> <files>`, which is its own docstring's
  example. Both fixed; the helper is shared with `codewatch.twins()`, which halted the library
  over this class once.
- **`498dd8b128f7`, `2f679246a6e4`, `9ab5bfa26f14`, `97894a93eab5`, `2d6c9343cd32`,
  `32eaec248adf`, `21e2ad81de88`** — a vacuous halt-marker row made unconditional; two uncapped
  breached-net lists (in the file that enforces Hard Rule 0 on everybody else); a duplicate row
  label; a `tol=` that `check()` silently discarded; and two battery orders that recovered.

**One regression, introduced and closed in the same shift (`21e2ad81de88`):** the net added for
`5905045ff433` used `ast.walk` where every sibling uses `_live_walk`, so a `publish.py` with the
guard parked in a trailing `while False:` passed. Found by sweep39-batch02 with that incident's own
fixture; fixed and re-verified. **The net had been red-watched when it was added, and the red-watch
passed** — none of the three probes was dead code, so none could find it.

### Run #38 (2026-08-29) — the reconciliation shift: twenty entries the ledger outlived

*Not a sweep. Tonight's shift closed over 430 work orders straight from the queue, and the
agents that closed them had no reason to open this file — so `## Open` was reconciled against
`state/workorders_closed.jsonl` and, in every case below, against the source itself. **The
rule applied was verify-before-you-move**: a work-order resolution claiming a fix was treated
as a pointer, not as evidence, and the code it named was read. Twenty entries moved. Ten more
were found PARTLY closed and stay Open with a dated note saying which limb shut and which did
not — among them M16, M38, M42, m105, m133 and m134, each of which reads as fixed from the
work-order trail and is not. Eleven were confirmed STILL LIVE at the line they cite,
including M44, whose live symptom (`spine_code_for("Alien Predator Doom Crossover") -> II.N`)
reproduces today even though two orders hardened the branches either side of it.*

*Not everything below was fixed tonight, and the dates say so. Several were repaired days or
weeks ago — m54 was already recorded as fixed inside M7's own update in this ledger, m86's
body has said **FIXED** since run #20, and m25's said **CLOSED** this morning. The ledger was
simply never asked. That is the finding worth keeping from this pass: a bug list nobody
reconciles rots in the direction nobody watches, and the entry that says OPEN over code that
is fixed costs the next reader the same hour every time.*

*No commits are cited. This working repo has no commits of its own — it publishes from a
separate export tree — so the paper trail here is the work-order id and the module, which is
what a successor can actually follow.*

- **[M20 — RESOLVED, reconciled run #38] THE ENTRYPASS DONE-MARKER IS A POSITIONAL KEY OVER A LIST THAT ANOTHER WRITER
  MUTATES.** Found run #27 by `health --preflight`, which went from 1 problem to 2. `check_state`
  (`health.py:256`) counts entries with no `catalogued` flag sitting inside a batch already
  recorded done. **227 stranded, every one in a single source (`Gundam (all centuries, incl. G
  Gundam)`).** The marker is `f"{source}#{start}"` — an INDEX. Close `Gundam#0` over entries
  0-19, then let the cast-growing side insert or re-sort, and that key now claims a different
  twenty; whatever slid into a closed range is never entrypassed, because nothing re-opens a
  batch. Appending alone is harmless — new entries land in new, unclosed ranges — so this only
  bites on insertion or re-ordering, which is why it appeared in one source and not the corpus.
  Same class as the truncated/positional dict keys already fixed at m37 and still open at
  `chain.py:354`. **Why NOT patched:** re-keying by content invalidates every done-marker on disk
  and re-runs entrypass across the corpus — real model spend on a pool that is currently the
  binding constraint. **Owner ruling needed — NEXT_STEPS §1.**

  **UPDATE, run #29: THIS IS ACCRUING, NOT FROZEN — AND THE "ONE SOURCE" REASONING NO LONGER
  HOLDS.** `health --preflight` now reports **412 stranded, across TWO sources**: Gundam 227
  (unchanged) and **SpongeBob SquarePants 185 (new)**. The single-source containment was the main
  reason this looked cheap to defer — it read as one historical re-sort in one fiction. A second
  source appearing means the insertion/re-order path is still live and still closing entries out
  of reach, so the cost of deferring grows with every catalogue pass. The ruling is now more
  urgent than when it was filed, and the back-fill option is 412 entries rather than 227.

  **Root cause, and why the ruling this entry was waiting for was never needed.** The marker
  really is an INDEX — `phase_entrypass` still builds `key = f"{src}#{start}"` — but the harm
  named above does not follow from it any more, because nothing skips on the key alone.
  `pipeline.batch_settled` (`src/pipeline.py:1407-1425`) gates the skip on **membership AND a
  fully judged span**: `key in done_keys and all(entry_settled(e) for e in batch)`. So a span
  that acquired an unjudged entry by insertion, append or re-sort is REOPENED and re-judged on
  the next pass, and the comment above the call says so in as many words — *"the gate is
  therefore the work, not the bookkeeping."* The repair was taken on the work rather than on the
  key, which is exactly why the re-key this entry priced as an owner ruling (invalidating every
  done-marker on disk, re-running entrypass across the corpus, real model spend) was never
  required and never paid.
  **Measured tonight, and this is what closes it rather than the reading of the source.** Order
  `ENTRYPASS_DONE_KEYS_NAME_UNSETTLED_SPANS` was filed asking a person to authorise clearing the
  affected keys, on the stated premise that *"the pipeline will never revisit them on its own and
  no amount of running it will repair this."* It was **closed as a mistaken remedy on a real
  finding**: the residue is draining unaided. At filing, 1,496 of 4,559 recorded `done.entrypass`
  keys named spans unsettled on disk; now **1,124 of 5,389** — 372 fewer unsettled while 830 MORE
  keys were recorded, which is only possible if the pipeline is both advancing and repairing. The
  two sources this entry's successors quoted as evidence are the plainest: **DC 195 → 4, Final
  Fantasy 151 → 0.** Marvel's 677 has not moved and is the one thing here worth watching — it is
  the largest record, so the honest reading is that phase 2 has not reached it again, not that
  anything skips it. No export-repo commit: this working repo carries no commits of its own.

- **[M34 — RESOLVED, the owner ruled 2026-08-25] THE ASSAY DISAGREES WITH ITS OWN CALIBRATION LADDER, AND
  THE SWEEP HAS BEEN GRADING THAT GREEN.** Surfaced run #31 the moment M32's import-tier fix
  landed, converging with batch 09's independent reading of the same lines. `anchors.py` scores a
  fixed ladder of reference entities and asserts it ascends floor → ceiling. It does not:
  ```
    The Skate Guy              0.22
    A Sword                    0.10      <- below the floor anchor
    Yggdrasil                  6.18
    Goku                       5.42      <- below the anchor above it
    The Seat of the Creator   10.99
  ```
  The script exits non-zero and says so in plain words — *"the instrument disagrees with the
  ordering it was calibrated against. This is a reading about the ASSAY, not about this
  script."* — and **`allsweep` reported it as importing cleanly on every run**, because it exits
  via `SystemExit` and prints no traceback (M32). A live disagreement in the instrument every
  printed Magnitude depends on has been visible and unread.
  **Why NOT fixed here:** there are two different repairs and they mean opposite things. Either
  the declared `order` is wrong (Goku should sit above Yggdrasil, and the assay is right), or the
  assay is mis-scoring one of them against the charter's intent. **Which of a world-tree holding
  nine realms and a martial artist who moves planets ranks higher is a curatorial judgment the
  charter makes, not a bug a maintenance run may decide.** Two anchors are involved: `A Sword`
  (0.10) also sits below the floor anchor `The Skate Guy` (0.22). **NEXT_STEPS §1.**

  **Root cause: the instrument was right and the DECLARATION was wrong, at two of its four
  steps.** This entry framed the disagreement as *either* the declared `order` is wrong *or* the
  assay is mis-scoring, and correctly refused to pick. The owner picked, on 2026-08-25, and picked
  the same way twice — *"obviously the tree holds higher"* on the Goku/Yggdrasil pair, and *"the
  assay is right here for the sword vs skate guy."* Both rulings are recorded verbatim in
  `src/anchors.py` above the ladder, with the charter reasoning attached: Yggdrasil is a REACH and
  CONTINUITY object, a structure nine realms hang from, against Goku's RUIN and CELERITY, and the
  ladder's rungs are rung-threat scales rather than combat records. `order` now reads
  `["A Sword", "The Skate Guy", "Goku", "Yggdrasil", "The Seat of the Creator"]` and the invariant
  holds against the live scores.
  **The lesson the file keeps, and it is the better half of this bug:** the invariant had been red
  for weeks and was read as *the assay has drifted from its calibration*. A failing invariant says
  two things disagree; it does not say which is lying, and this script's own message — *"a reading
  about the ASSAY"* — quietly asserted that it did.
  **What tonight's shift added around it.** Order `237356c82d06`: `run()` computed an assay, an
  instrument reading, a college interval and a bit value for every anchor, printed all four, and
  gated the exit code on the monotone ordering alone — every anchor's `note` states a testable
  claim and none was tested. Each is graded now (saturation at the ceiling, floor completeness,
  the identified-theta case, the UNESTIMABLE case), printed HELD or VIOLATED with the values it
  was read from, and `ok` is all of them. Order `1618d9790f0d`: the ladder is asserted to name
  every anchor and only anchors, so adding a reference is no longer also the way to add an
  ungraded one, and a name in `order` with no ANCHORS row reports a violation instead of raising
  KeyError. **Live run today: seven verdicts, all HELD, exit 0.** The M10 saturation question that
  surfaced underneath — `INSTRUMENT_WINDOWS` is (30,30) for M5 through M10, so Goku at M5 prints
  every faculty at 30 — is not this script's call and was not made; it is PRINTED as an OWNER
  QUESTION on every run rather than filed here again.

- **[M40 — RESOLVED] `withdraw_chapters.py:66-98` HAS NO CHAPTER-SELECTION LOGIC AT
  ALL.** The docstring frames it as a targeted withdrawal of the 145 flagged chapters; `--go`
  actually iterates the **entire** `catalog.json`, moves every entry's files, and wipes the
  catalog to `{}` unconditionally. A destructive tool whose comment describes a selectivity the
  code does not implement. **Do not run it.**

  **Root cause: a one-occasion script left in the tree as a general tool.** It was written for the
  145-chapter withdrawal of 2026-08-25 and its `--go` was hardcoded to that occasion, which is why
  the docstring's selectivity and the code's behaviour disagreed. Order `cda7b9e2b4e1` gave it the
  selection the comment described: `select()` (`src/withdraw_chapters.py:115`) is a **pure**
  function of `--source` / `--addr`, matching exactly rather than fuzzily *because* this is the
  destructive step, and **the catalog is edited, not erased** — `remaining` is written back and
  anything that failed to move keeps its record.
  **Four of tonight's orders hardened the destructive step itself**, all in
  `src/withdraw_chapters.py`:
  * `8d14f0adda1b` — two withdrawals sharing a `--label` silently destroyed each other. `shutil.move`
    onto a full destination PATH skips its own exists-check (that branch runs only when dst is a
    directory), so `os.rename` raises on Windows and it falls through to copy2+unlink. The archive
    is the ONLY copy of a withdrawn chapter. A taken name is now a refusal, and the classifier only
    calls a name free on positive evidence (`FileNotFoundError`), never on a bare `exists()`.
  * `22394233dbad` — an entry whose file could not be STATTED lost its catalog record, because
    `os.path.exists` answers False for an unreadable path exactly as readily as for an absent one
    (measured, on a 300-char path and on one with an embedded NUL). `_file_state()` now separates
    *gone* from *unavailable*, and the module's stated contract — anything that failed to move
    keeps its record — holds for the stat half as well as the move half.
  * `1687ff8084b9` — a half-moved entry kept a record pointing at a file already in the archive.
  * `c8ac7dbab3c5` — an `--addr` matching nothing was ignored whenever any other selector matched,
    and the refusal branch whose whole purpose is naming a typo computed `unknown` from `--source`
    alone. Both selectors are checked independently now and either one unmatched stops the run.
  **The "Do not run it" warning is retired.**

- **[M41 — RESOLVED] `overwatch.py:369-378,421-430,647-648` MAKES PARTIAL COVERAGE
  INDISTINGUISHABLE FROM A FULL REVIEW.** Once the per-round `CLOUD_BUDGET` is spent, `_ask`
  returns None, `review()` swallows it as "no findings," and the module is **still marked seen
  with a fresh digest and timestamp** — so it goes to the back of the re-review queue and can be
  starved indefinitely while the system reports it reviewed. Same shape at `:485-497`, where
  `last_verified` is stamped even on a failed re-check. *(Batch 15 confirmed the finding-closing
  path itself is safe: only an explicit "refuted" verdict closes a finding.)*

  **Root cause: one value meaning two things — *nobody looked* recorded as *looked and found
  nothing*.** Both limbs of this entry are that sentence, and both are closed.
  * Order `a3ee0d1d2d4c`: `overwatch.review()` returns `(kept, complete)`, with `complete` going
    False the moment any slice's `_ask` comes back None, and `round_once` stamps
    `led["seen"][m]` **only when `complete` is True**. A yielded review leaves the module's old
    timestamp in place, so it stays near the front of `rotation()`'s stale queue instead of being
    sorted to the back as if it had just been read.
  * Order `c6f64c1424fa`: the identical treatment for `last_verified` in `verify_open`
    (`src/overwatch.py:598-605`). A finding the model never answered for is counted as **yielded**,
    keeps its old timestamp, and stays at the FRONT of the oldest-verification-first queue. The
    round no longer prints "N re-verified" for an N of zero.
  Module: `src/overwatch.py`. *(This does NOT cover the four undercount proofs in m133 — two of
  those are still open and m133 stays where it is with a dated note.)*

- **[M43 — RESOLVED] `assay.py:496-531` MUTATES `SIGMA_BY_ATTESTATION` UNLOCKED
  UNDER A THREADING SERVER.** `calibration_report()` mutates the global that every printed
  Magnitude's interval is built from, with no lock anywhere in `assay.py`/`dashboard.py`; two
  concurrent `/api/state` polls can leave it **permanently** shifted, because the restoring
  thread's "saved" value can itself be mid-sweep garbage from the other thread.

  **Root cause, and the fix is not the lock this entry expected.** `calibration_report()` sweeps
  ~800 trial sigmas to find the band that reproduces the charter's published ±0.12, and it did so
  by assigning each into the module-global `SIGMA_BY_ATTESTATION` and restoring it in a `finally`
  — correct alone, and silently wrong the moment anything else reads the table mid-sweep, which
  under `dashboard.py`'s threading server and `drill.py`'s battery it does. A lock would have
  serialised the window rather than removed it. Order `6797f36117ce` removed the mutation instead:
  `assay()` gained a per-call `sigma=` parameter, the same device `weights=` already was and
  introduced for the same reason, so a trial value travels with the call it belongs to and is
  invisible to every other caller by construction.
  **Verified at source rather than taken from the resolution:** `src/assay.py` now contains **not
  one assignment** into `SIGMA_BY_ATTESTATION` — only its definition at `:396` and three reads
  (`:416`, `:589`, `:633`). There is no window left to lock.

- **[m12 — RESOLVED] `thread_integrity.py`'s asymmetric-thread detection is structurally unreachable** —
  `implied_threads()` builds `pairs` symmetrically by construction, so `classify()`'s `back =
  pairs.get((b,a))` is always truthy and every implied thread reports RECIPROCAL; the
  ASYMMETRIC-LAWFUL/-SUSPECT branches (including the propagation-distance "lawful excuse"
  logic) can never fire. `DANGLING` is a documented output category that is never computed.
  This looks design-shaped rather than a one-line fix — HUMAN CALL: is the module meant to
  compare the weave's implied threads against a separately-recorded directed thread graph it
  currently isn't given? See NEXT_STEPS.

  **Root cause: the module was comparing its own input against itself.** `implied_threads` builds
  the pair map SYMMETRICALLY by construction, so every implied pair reported RECIPROCAL and the
  ASYMMETRIC classes were unreachable — it was measuring its own input's shape and calling it the
  omniverse's. The HUMAN CALL this entry asked for was answered by the owner on 2026-08-24 (*FIX
  IT ALL*), and `classify()`'s docstring in `src/thread_integrity.py` records the ruling by this
  bug's own number: asymmetry is real only against a DIRECTED record of which entries carry a
  Thread, and per Hard Rule 5 that graph does not exist until the Step 4 entanglement pass. So
  with `recorded=None` — every caller today — implied pairs classify as **IMPLIED-UNRECORDED**, an
  honest name for an obligation awaiting that pass rather than reciprocity nobody verified, and
  **DANGLING and PARTIALLY-DANGLING are computed for real** against the live records: this entry's
  "documented output category that is never computed" is now a measured one. Order
  `THREAD_INTEGRITY_DANGLING_CLASS_NEVER_PRINTED` (2026-08-27) then got it printed as well as
  counted, DANGLING first, because it is the worst class and was the one class never shown.
  **Tonight closed the last of it.** Order `7bffb5634d7a`: `classify()` deduped to one direction
  per unordered pair and then asked only `back = (b, a) in recorded`, never whether `(a, b)` was —
  so on the future directed graph the verdict would have been decided by the insertion order of
  the `pairs` dict rather than by the evidence, and the module's two most important classes were
  the ones it would get wrong. Reproduced before changing anything: reversing the dict's insertion
  order flipped the verdict with the evidence held constant. RECIPROCAL now requires both
  directions; exactly one is the asymmetric case and the pair is reported ORIENTED so the first
  name is the end that records the thread; neither is IMPLIED-UNRECORDED, because there is no
  direction to be asymmetric about and calling it one-way would invent one. Latency unchanged —
  every caller still passes `recorded=None` and the live run still reads 5,782 IMPLIED-UNRECORDED
  at 100.0%.

- **[m25 — RESOLVED] `scout.sweep` keeps only the last 40 run entries** (`prev[-40:]` into `SCOUT.json`).
  Judged NOT a Hard Rule 0 violation this run — a run history is not a roster, an entry list, a
  page list or a chunk list — but it is a truncation of an ordered listing and the rule's text
  does not carve out logs explicitly. **Question, not a fix.** Same family as m16's diagnostics
  ruling; one decision could settle both.
  **CLOSED 2026-08-29 (order e8cd908ce5e4) by removing the question rather than answering it.**
  The window survives — `SCOUT.json` is still the last `LOG_CYCLES` (40) cycles in readable
  form — but the cycles that fall out of it are now APPENDED to `data/SCOUT_ARCHIVE.jsonl`
  before the trim, and the trim only happens if every one of them landed. So there is no longer
  a truncation to rule on: nothing is dropped, and the ruling m25 was waiting for is only needed
  if someone wants the window changed. The archive path is derived from `LOG` rather than
  declared as its own constant, so `drill.py`'s two scout nets, which redirect `SC.LOG` into a
  temp directory, redirect the overflow with it. m16's diagnostics question is untouched and
  still open.

  **Root cause and fix are already stated in the body above; recorded here so the ledger's Open
  section stops carrying a closed question.** Order `e8cd908ce5e4` removed the question rather
  than answering it: cycles falling out of the 40-cycle window are APPENDED to
  `data/SCOUT_ARCHIVE.jsonl` before the trim, and the trim happens only if every one of them
  landed (`src/scout.py:565-568`, following the ledger's own house rule *"ARCHIVE FIRST, AND ONLY
  CLEAR IF THE ARCHIVE LANDED"*). Nothing is dropped, so there is no truncation left to rule on.
  The archive path is derived from `LOG` rather than declared as its own constant, so the drill's
  two scout nets — which redirect `SC.LOG` into a temp directory — redirect the overflow with it.
  *(m16's diagnostics question is untouched and still open; one decision no longer settles both.)*

- **[m54 — RESOLVED] `gpu_lane._touch` — the heartbeat refresh the module's own docstring calls essential —
  IS DEAD CODE.** Defined at `gpu_lane.py:271`, **zero call sites in the entire repo**
  (verified: the only other `_touch` hits are `foreman.regex_touched` and
  `rigor.adjudication_beta`'s `n_laws_touched`, unrelated names). So a heartbeat is written once
  at acquire and never updated, while `_expired()` (`gpu_lane.py:156-162`) checks heartbeat age
  **before** it checks whether the PID is alive. Any call outliving its lease has its own live
  lease judged stale: `CLAIM_LEASE_SECONDS` is **300 s** for a foreground claim against
  `config.yaml:106 request_timeout: 1800`, and `generate.py:151`'s own comment says a real prose
  call "legitimately runs for minutes". Consequences, in order of nastiness: a long foreground
  prose call stops advertising itself after 5 minutes so background callers stop yielding to it;
  and when it finally returns, its `finally: os.remove(slot)` deletes whatever now occupies that
  path — **possibly another process's live lease**. Latent with m56; same first-bounce trigger.

  **Root cause: a heartbeat that was written once and never refreshed, in front of an
  `_expired()` that checks heartbeat age BEFORE it checks whether the PID is alive.** So any call
  outliving its lease had its own live lease judged stale — `CLAIM_LEASE_SECONDS` is 300 s against
  a `request_timeout` of 1800 — and its `finally: os.remove(slot)` could then delete whatever now
  occupied that path. `_touch` is wired now: `src/gpu_lane.py:414` records the defect it closes by
  this bug's number (*"THE DEFECT THIS CLOSES (m54, measured 2026-08-24)"*), the refresh is called
  from the held-slot path at `:444`, and `_touch` additionally refuses to re-create a file the
  release path has already removed, so the fix cannot resurrect a released lease. **M7's own
  run-#15b update in this ledger already recorded m54 as fixed and pinned by `verify_math` §19ad;
  the Open entry was simply never moved.**

- **[m55 — RESOLVED] `gpu_lane` DELETES ITS LEASE FILES WITH AN UNRETRIED `os.remove`, and on Windows that
  is the one operation this project already knows fails under contention.** Six sites —
  `gpu_lane.py:195, 224, 253, 265, 326` and the foreground path — every one wrapped in a bare
  `contextlib.suppress(Exception)`; `grep -c replace_retry src/gpu_lane.py` is **0**. On Windows
  `os.remove` raises `WinError 32` while any concurrent `_read()` holds the file open, which is
  exactly the sharing violation `silence.replace_retry` exists to outwait. A release that
  silently fails leaves a lease that is neither held nor expired, and that slot index is then
  unavailable to everyone — including the process that thinks it released it — until the full
  `SLOT_LEASE_SECONDS` (900) ages out.
  **VERIFIED at source by this pass; the stranding was reproduced by a subagent** running 8
  real processes against a scratch-redirected lane dir: `os.remove` failed 2 of 20 releases,
  and once a slot stranded, 5 of 8 workers got no slot for the rest of the run. **Latent only
  because m56 means nothing uses the lane yet** — it would bite on the first bounce, under
  exactly the nine-process load the lane exists to serve. Fails open (a caller that never gets
  a slot still proceeds), so it degrades to "no arbitration", never to a deadlock.

  **Root cause: the project's own remedy applied to `os.replace` and never carried to
  `os.remove`.** Six release sites deleted lease files with a bare `os.remove` under
  `contextlib.suppress(Exception)`, and on Windows that raises `WinError 32` while any concurrent
  `_read()` holds the file — the same sharing violation `silence.replace_retry` exists to outwait.
  A silently-failed release left a slot neither held nor expired, and therefore unavailable to
  everyone including the process that thought it released it, until the full 900-second lease aged
  out. `src/gpu_lane.py:447` now holds `_remove_retry(path, attempts=4)`, reasoned from and citing
  `replace_retry`, and every release goes through it — `:214`, `:263`, `:343`, `:354`, `:546` —
  each carrying an `# m55` marker. Verified: the only bare `os.remove` left in the file is the one
  inside `_remove_retry` itself. It still fails open, which is right: a caller that never gets a
  slot proceeds unmetered, so the degradation is "no arbitration", never a deadlock.

- **[m57 — RESOLVED, code and corpus] A NAIVE SINGULARISER IS MANGLING ENTRY TYPES ACROSS THE CORPUS.**
  `catalogue_web.py:212` does `cats[0].rstrip("s")`, which (a) strips EVERY trailing `s`, not
  one, and (b) does not handle `-ies`. Measured over the live manifest's 85,882 entries:
  **`Abilitie` 205, `Citie` 139, `Countrie` 81** — 425 entries carrying a mangled type, plus
  `Valkyrie` 39 which is a false positive of my own detector (a genuine word ending in "ie",
  listed here so the next reader does not re-count it as damage). **Not fixed this run**
  because entry `type` feeds classification and matching, and this project's rule is that a
  matching-logic change is not verified until the whole corpus is diffed before and after —
  which is not a thing to start while another session is live in the repo. Small, real,
  self-contained; the fix is a proper singulariser plus a re-derive.

  **Root cause: `str.rstrip(chars)` removes a character SET, not a suffix.** So
  `cats[0].rstrip("s")` ate every trailing `s`, and the value went INTO the record rather than to
  a console — `Goddesses → Goddesse`, `Bosses → Bosse`, `Classes → Classe`, `Princess → Prince`,
  `Colossus → Colossu`, `Boss → Bo`.
  **The code**, order `0a5019b2527e`: both halves of `src/catalogue_web.py:410` now go through a
  module-level `_singular()`. It is deliberately NOT an English pluraliser — three ordered rules,
  and the middle one is the point: where the shape is genuinely undecidable the category name is
  left INTACT rather than guessed at, because a plural type is untidy while a mangled one is wrong
  (`Deities` and `Movies` stay plural; `Deities → Deity` cannot be told from `Movies → Movie`
  without a dictionary). The first draft of the function was worse than `rstrip` on the common
  case and the measurement caught it, which is why the sibilant rule exists.
  **The corpus**, order `2d9f78a0c4d5` — the repair pass this entry called for, and it was
  reported before it was performed. 10,876 entries across 14 record files, rewritten through
  `pipeline.write_record_catalogue`, the project's only sanctioned record writer, with every
  landed verdict checked: **Abilitie→Ability 9,337, Citie→City 1,052, Countrie→Country 486,
  Heroe→Hero 1.** Matched on those four exact values only, never a general re-singularisation. A
  dry run planned exactly 10,876 and the applied total was exactly 10,876, 0 denied, 0 unreadable.
  Typed entries stood at 282,790 before and after and a full type-histogram diff shows only those
  four pairs moved, summing to zero — a value rewrite, not an add or a delete. **The 58 legitimate
  look-alikes this entry warned the next reader not to re-count — `Valkyrie` 39 among them — were
  confirmed unchanged one by one.**

- **[m62 — RESOLVED] `state/model_metrics.jsonl` IS BEING TORN BY CONCURRENT APPENDS — 5 corrupt lines,
  and it is ONGOING, not a healed historical event.** Two writers (`cascade_bridge._metric`
  and `pipeline._metric`) share the file, and it is appended from at least five live processes
  (`read`, `feats --roll`, `pipeline`, `foreman`, `overwatch`), each with a plain
  `open(path, "a")` + `f.write(...)`. Three of the five bad lines are **record fragments split
  mid-write** — `'11657, "out_chars": 1353}'`, `'}'`, `'0}'` — and two are stray blanks. Dated
  by walking back to the nearest parseable neighbour: 08-23 20:38, 08-23 20:57, 08-24 07:17,
  and **08-24 13:07 and 13:08**, so it is still happening.
  **Exposure is low and worth stating honestly:** 5 of 26,970 lines (0.019%), and the one
  in-repo consumer (`dashboard.metrics()`) parses per line inside a `try`, so nothing crashes —
  the cost is the lost records plus any ad-hoc reader that assumes the file is clean. **The
  NEXT_STEPS m59 one-liner is exactly such a reader and dies on it** (`JSONDecodeError` on the
  first blank), which is how this was found.
  **Not fixed this run, deliberately:** the remedy is a single atomic append (one `os.write` to
  an `O_APPEND` handle, or the project's lock discipline) at both writers, and changing the
  write path of a hot ledger held open by five live processes is not a change to make in the
  same run as M7's. Fix pattern exists; needs its own quiet window.

  **Root cause: a buffered append is not one write.** Both `_metric` writers used
  `open(path, "a")` plus `f.write(...)`; Python may split one line into several underlying writes,
  and two of the five live appenders interleaving mid-line produce a row that parses as neither.
  The remedy is `silence.append_line` (`src/silence.py:245`), which names this bug in its own
  docstring and states its own limits honestly: one `os.write` to an `O_APPEND` descriptor is a
  single syscall in which the kernel does the seek-to-end and the write together — *"not a general
  atomicity guarantee for arbitrary sizes, but for a sub-page JSON line it is the difference
  between interleaved-and-corrupt and interleaved-but-whole."* Both `cascade_bridge._metric` and
  `pipeline._metric` go through it, each with a comment citing m62 and each still best-effort, so
  a metrics failure never costs a call. The quiet window this entry wanted was taken.

- **[m81 — RESOLVED] EVERY line-number `silence.note()` label in `feats.py` is stale, by 8 to 140 lines.**
  Verified: label `"feats.py:125"` sits at line 137 (its `except` is 133); `"feats.py:139"` at
  149 (except 148); `"feats.py:374"` at 425 (except 424); `"feats.py:695"` at **836** (except
  835). The labels are baked once by `silence.py --instrument` and never move as the file grows.
  **This bug bit this run's own task prompt**, which cited "feats.py:139" — 9 lines off. The
  same drift exists in `overnight.py` (5 labels, 60–260 lines off). Renaming splits the ledger's
  cumulative counts off their history, so it is a decision, not a chore — NEXT_STEPS §2.

  **Root cause: labels baked once by `silence.py --instrument` and never moved as the files
  grew.** The label IS the key `state/failures.json` aggregates on and the one `ledger_report()`
  prints every cycle, so a reader chasing a specific swallowed failure was sent to the wrong lines
  — this entry noted it had already misdirected a task prompt by 9 lines. The decision it flagged
  (renaming splits the ledger's cumulative counts off their history) was taken, in favour of
  **content labels**: `src/feats.py` and `src/overnight.py` between them now carry **zero**
  line-number `silence.note` labels. `overnight.py:656-662` records the change and its reasoning,
  names the five keys it replaced (`overnight.py:203`, `:229`, `:253`, `:124`, `:141` — line
  numbers from a version of the file that had not existed for two refactors), and cites this bug
  and m5 as the same drift already repaired in `dashboard` and `wiki_source`. Descriptive keys
  survive the next refactor; the numeric ones did not survive one.

- **[m82 — RESOLVED] `feats.py:327,334` — `aplimit=500` and `srlimit=50` with NO continuation handling.**
  Verified: no `apcontinue`/`sroffset`/`continue` token anywhere in the file. Both feed
  `discover()`'s title list, which `fetch()` then reads — **acted on, not display-only**, and
  unlogged when the cap binds. Hard Rule 0 question: an entity with more than 500 subpages or
  50 search hits is silently read in part. Nothing measures how often it binds.

  **Root cause, and the counter was mistaken for the cure.** `aplimit=500` and `srlimit=50` are
  the API's own per-request maxima, and a query with more results answers with a top-level
  `continue` object meaning *ask again from here*. The old code read that object only to INCREMENT
  A COUNTER — the very measurement this entry asked for, so that the cap could be ranked against
  Hard Rule 0 — and then iterated the first page it already had. `feats._api_list_all`
  (`src/feats.py:761`) now merges `continue` into the next request verbatim and walks to
  exhaustion, following whatever continuation the wiki offers without needing to know which list
  it is reading. Its docstring makes the distinction explicit: *"The tally is not the fix;
  measuring a truncation is not the same as not truncating."*
  **The one stop condition is not a cap.** A wiki returning the same continuation token twice is
  looping, not offering more, and that case — together with a mid-walk `api()` failure — increments
  `_CAP_BOUND`, because a partial list nothing recorded is exactly the silent smaller universe the
  rule exists to prevent. Order `051244c2628f` closed the last hole in that: the guard was
  `if rows:`, so a walk whose very FIRST request failed counted nothing and returned `[]` — which
  is byte-for-byte what "this entity has no pages" looks like, while the caller's *"discovery
  lists: complete"* banner still printed.

- **[m84 — RESOLVED] A SINGLE FAILED PROCESS PROBE READS AS "EVERY MANAGED JOB IS DOWN", AND A DUPLICATE
  CAN BE SPAWNED ON THE STRENGTH OF IT.** Observed live, run #19. `state/foreman.log` recorded
  `OWNER  every managed job is running: foreman.py (floor all up)` -- the foreman naming
  **itself** as down, in the file it was in the middle of writing -- and **four minutes later a
  second foreman process existed** (PID 50896 alongside the long-running PID 5420). No duplicate
  survived to the next check, so nothing was damaged this time.
  **Mechanism, verified at source:** `overnight.running()` opens `out = _proc_lines()` and
  `if not out: return False`. One failed or empty probe therefore answers "not running" for
  **every job at once**, and both the liveness standard and the keeper act on that answer.
  The page shows the same flapping from the other side: at 22:14 it reported `publish.py,read.py`
  down while `publish.py` (PID 38312) was demonstrably alive.
  **Why it is Minor and not Major:** the failure is transient and self-correcting, the keeper is
  idempotent for STANDING jobs, and `kill_duplicate_jobs` exists precisely to reap the loser.
  **Why it is worth recording anyway:** an empty probe result and a genuinely empty process table
  are the same value here, which is the exact shape of M16 (`api()` returning `None` for both a
  timeout and a real absence) and of the `preflight()` `(0, False)` fixed this run. A probe that
  cannot distinguish "I could not look" from "I looked and saw nothing" will eventually be
  believed. **No fix attempted** -- the repair is a return-contract change on a function the
  supervisor, the keeper and the standards tree all call. NEXT_STEPS section 2.

  **Root cause is the sentence this entry itself wrote:** a probe that cannot distinguish *I could
  not look* from *I looked and saw nothing* will eventually be believed. `running()` opened
  `out = _proc_lines()` and answered `if not out: return False`, so one failed or empty probe said
  *not running* for **every job at once**, and both the liveness standard and the keeper acted on
  it. Order `1d556b6ef535` gave `overnight.running()` a third answer: **`None` when the process
  table could not be read.** The return-contract change this entry said needed a review cycle was
  made additively — `None` is falsy, so the read-only callers that only ever ask `if running(x)`
  (the foreman's four repair gates, standards' roster) behave exactly as before, since a blind
  probe was already handing them False. It is the SPAWN sites that must not, and each of them in
  `src/overnight.py` now tests `is None` explicitly, logs through `_blind(...)` and returns the
  distinct status `probe-blind` rather than starting a duplicate on the strength of a probe that
  never saw anything.

- **[m86 — RESOLVED, run #19/#20] `overnight.foreman_report()` REPLAYS THE FOREMAN'S LAST ROUND UNDER THE SUPERVISOR'S
  CLOCK, MISDATING EVERY REMEDY IT PRINTS.** Found run #20 while investigating what looked like a
  kill against a recycled PID -- it was not; the timestamp was the lie. `foreman_report()` reads
  `FOREMAN.json`'s `rounds[-1]` and logs it when the supervisor's lap comes round, but `log()`
  prefixes each line with the supervisor's CURRENT time. A kill the foreman performed at
  **22:00:55** appeared in `state/overnight.log` as
  `[2026-08-24 22:39:04] ... kill_stalled_job: killed stalled read_auto:42972` -- **misdated by
  38 minutes**, up to a full lap in the general case.
  **Why it matters more than a cosmetic timestamp:** M15's entire evidence base is start/finish
  and remedy timestamps read out of this one file. A run reconstructing what killed the reader
  and when can attribute a kill to the wrong lap and therefore to the wrong cause. The header
  line always carried the true time (`applied at {last['at']}`); the indented lines people
  actually quote did not.
  **FIXED, run #20** -- each replayed line now carries the foreman's own timestamp in brackets.
  Same edit removed `did[:5]`, which truncated the list under a header announcing the true count
  ("6 remedy(ies) applied" above five lines). Nothing downstream parses that log.

  **Recorded here because the body above already says FIXED and the entry was never moved.**
  Confirmed at source: `overnight.foreman_report()` (`src/overnight.py:670`) stamps each replayed
  line with the foreman's own timestamp — *"STAMP EACH LINE WITH THE FOREMAN'S OWN TIME, AND SHOW
  ALL OF THEM"* — instead of letting `log()` prefix the supervisor's current time, and the
  `did[:5]` truncation printed under a header announcing the true count is gone. Root cause was a
  REPLAY rendered under the reader's clock rather than the event's, which matters here beyond
  cosmetics: M15's entire evidence base is start/finish and remedy timestamps read out of this one
  file, so a misdated kill attributes a cause to the wrong lap.

- **[m92 — RESOLVED] `assay.instrument()` HAS AN UNDOCUMENTED PRECONDITION THAT ITS OWN FILE'S CONTRACT
  INVITES YOU TO BREAK.** `assay.py:152-188` establishes four statuses available on EVERY axis
  (a number, `NONE`, `UNESTIMABLE`, `INAPPLICABLE`) as a load-bearing epistemic distinction. But
  `instrument()` (`assay.py:511-517`) special-cases only Python `None`; the other three are
  strings, so `s is None` is False and it falls through to `s / 10.0` and raises `TypeError`.
  **Not live-broken** — both callers (`anchors.py:186-188`, `verify_math.py`) pre-filter with
  `isinstance(v, (int, float))`. It is the natural trap for the next caller that passes the same
  `scores` dict used for `assay()` straight into `instrument()`. Fix is a docstring precondition
  plus an explicit raise; queued rather than done because it is a public-signature question.

  **Root cause, and it turned out to be worse than the trap this entry described.** The natural
  reading was that `instrument()` special-cases only Python `None` while the other three statuses
  are strings, so `s is None` is False and the value falls through to `s / 10.0`. True — but the
  deeper fault was that `_check_scores`, the module's own **LAYER 1**, had exactly ONE call site,
  inside `assay()`. `instrument()` is the other public entry that takes axis scores straight from
  a caller and PUBLISHES numbers from them, and it validated nothing: order `5f99aa19c059`
  reproduced `assay("M3", {"ruin": 99.0}, worksheet="w")` raising `AssayIntegrityError` while
  `instrument()` printed a Strength of exactly **30** for the same reading — the maximum the
  Instrument can print, and therefore indistinguishable from a legitimately maxed one — and a
  Dexterity of **−30**, outside the 1-30 range X.6 §6 Definition 4 declares.
  **Fixed at both doors.** `instrument()` calls `_check_scores(axis_scores)` immediately after the
  anchor check and before the H5 no-worksheet return, mirroring `assay()`'s ordering, and validates
  against the full `WEIGHTS` table rather than only the axes `FACULTY_READS` consumes — because
  real callers hand it the whole numeric score dict (`anchors.py:186` does), so the narrower table
  would refuse `reach` and `transgression` as nonexistent Measures. The faculty conversion is now
  bounded at both ends rather than capped only at the top. **Verified live this pass:** all three
  string statuses — `NONE`, `UNESTIMABLE`, `INAPPLICABLE` — now raise a named `AssayIntegrityError`
  naming the offending axis, which is the explicit raise this entry asked for, in place of a bare
  `TypeError`. Both public doors now give the same answer to the same reading.

- **[m94 — RESOLVED] `hostcheck.null_rate()` TURNS A FAILED
  CONTROL PROBE INTO A FABRICATED 0.0 BASELINE AND CACHES IT FOR THE WHOLE RUN.**
  ```python
  r = probe(host, foreign) or {}                      # hostcheck.py:418-422
  rate = r.get("rate")
  rate = 0.0 if rate is None else rate
  with _NULL_LOCK:
      _NULL_CACHE[host] = rate
  ```
  `probe()` legitimately returns `rate=None` on a failed request (and, via **m93**, sometimes a
  fake 0.0 instead). This line collapses "I don't know" into "this host answers 0% of foreign
  names" and locks it into `_NULL_CACHE` for the rest of the process, so every later `score()`
  call for that host uses a corrupt baseline. **Second-order effect worth the HIGH label:**
  `score()` only applies the aboutness veto when `base >= ABOUT_VETO_ABOVE` (0.25). A generous
  host like `en.wikipedia.org` (documented at `hostcheck.py:432` as ~50% baseline) whose control
  probe transiently failed gets cached at 0.0 — **silently disabling the aboutness veto for that
  host for the whole run**, which is the "Rocket League nearly adopted onto Wikipedia" failure the
  design exists to prevent. **Not fixed:** propagating `None` changes what `score()` must do with
  an unjudgeable baseline; ruling wanted.

  **Root cause: `rate = 0.0 if rate is None else rate` — *I don't know* collapsed into *this host
  answers 0% of names it has no reason to hold*, which is the most generous baseline available,
  and then cached for the whole process.** `src/hostcheck.py`'s `null_rate()` now returns `None`
  and **does not cache it**, with the reasoning written beside the branch: a failure is a fact
  about this moment, not about this host, and caching it would make one throttled probe stand as
  the host's baseline for the rest of the run. The docstring leads with the contract — *"RETURNS
  None WHEN THE CONTROL COULD NOT BE MEASURED ... None is not zero, and callers must not default
  it to zero"* — and the comment at the branch names the direction that made this HIGH: seventy-four
  throttled probes reading as 0% unassigned `warhammer40k.fandom.com`, and the same failure on the
  CONTROL side would silently ADOPT hosts instead, which is the worse direction. So the
  transiently-failed generous host that silently disables the aboutness veto — the
  "Rocket League nearly adopted onto Wikipedia" shape — can no longer arise.
  **Tonight finished the same question from the other side.** Order `4ff1db780b99`: `by` decides
  which rosters EXIST to draw the control from and was still outside the cache key, while
  `sweep()` draws from `data/CHARACTER_SWEEP.json` and `adopt()` from `weave_index.load_records()`
  — genuinely different universes, contained only by the fact that `main()` dispatches one mode per
  process, which is a property of today's CLI and not of the module. The key is now the foreign
  sample itself rather than a digest of the dict, which is exact in both directions.

- **[m95 — RESOLVED] `cascade_bridge.dead_forever()` CHECKS `PROOF_TTL` ONLY ONCE PER
  PROCESS.** `_PROVEN[0]` is memoised on first call (`cascade_bridge.py:303-319`), so a
  `POOL_PROOF.json` written later in a multi-hour run — recording a newly-proved 401/402/404/410
  — is never picked up. The TTL constant's own comment says *"a proof this old is no longer
  evidence about now"*; the memoisation makes the check vacuous after the first call.

  **Root cause: a memo in front of a TTL makes the TTL vacuous.** `_PROVEN[0]` was set on the
  first call and returned unconditionally thereafter, so a `POOL_PROOF.json` written later in a
  multi-hour run — recording a newly-proved 401/402/404/410 — was never seen, and `PROOF_TTL`'s own
  comment (*"a proof this old is no longer evidence about now"*) described a check that could not
  run. `src/cascade_bridge.py:368-413` now memoises on the proof file's **stamp** rather than on
  having answered once: `if _PROVEN[0] is not None and _PROVEN[0][0] == stamp: return
  _PROVEN[0][1]`, so a newer file re-reads and the TTL comparison at `:388` is reachable on every
  call.

- **[m97 — RESOLVED] `hostcheck.py:918-919`'s `--purge` HELP TEXT PROMISES A SAFETY
  CHECK THAT `purge()`'s OWN DOCSTRING SAYS NEVER EXISTED.** The help string still reads *"remove
  rosters the audit rejected AND whose host was independently rejected"*; the docstring at
  `hostcheck.py:642-647` records that *"it never did (the check was loaded and unused)"*. The
  docstring was corrected, the user-facing `--help` was not.

  **Root cause: the docstring was corrected and the user-facing string was not** — which is the
  whole of it, and the reason it was worth closing rather than leaving as decoration is that a
  help string overstating a safety is how an operator comes to rely on one that is not there.
  `src/hostcheck.py`'s `--purge` help now reads *"remove the roster for each source named with
  `--source`, after a human has read the audit shortlist; **no automated host check gates this**"*
  — it states the absence rather than promising the check, so `--help` and `purge()`'s docstring
  say the same thing about the same behaviour.

- **[m107 — RESOLVED] A FOURTH INSTANCE OF THE SAME CLASS: `scope.py:108-118`.** A
  transient network failure during `--build` permanently caches a host as "no scope", and
  `h not in out` never retries it.

  **Root cause: a failure written into the same map that decides what gets retried.** `build()`
  wrote `out[h] = None` in its exception handler while `todo` excluded every host already a KEY in
  `out` regardless of its value — so one network blip, one 500 from a wiki, one unparseable
  response permanently retired that host from scoping, and `data/SCOPE.json` then reported it as
  *attempted, nothing to score*, which is the one thing that had not happened.
  `src/scope.py:142-157` leaves a failed host **out of `out` entirely**, prints that the next build
  will retry it, and lets it simply reappear in the next `todo`. The comment at the site states the
  mechanism in this entry's own terms: *"A FAILURE IS NOT A VERDICT, AND IT MUST NOT BE CACHED AS
  ONE."*
  *(This does NOT settle the family. `m106` — `endpoint.fetch_raw`'s single `(t, None)` return for
  a 404, a refusal, an exception and an HTML error body alike — and M16's `evidence_for` half are
  both still open.)*


### Run #37 (2026-08-28/29) — the shift that found the pipeline was throwing away its own work

- **[M48 — RESOLVED] `pipeline.write_record` DISCARDED EVERY PER-ENTRY JUDGMENT ON ITS ORDINARY
  PATH AND RETURNED TRUE.** Work order `9ef51c36acea`, BLOCKING, found by the run-37 comprehensive
  sweep.

  **Root cause:** the per-entry field fold lived inside `if drift:` only. The `else` branch folded
  the top-level keys, set `merged = disk`, and returned `True` — so `category`, `scale_note`,
  `scale_note_rejected`, `magnitude`, `topic` and `catalogued`, every field the caller had just
  computed, were silently dropped.

  **Why it was the ordinary path, not a corner:** `drift` is decided by `_entry_digest`, which
  digests entry **names**, and `phase_entrypass` never changes a name — it fills in bands and
  notes on a cast whose names it leaves exactly as it found them. So phase 2 took the `else`
  branch essentially every time. Measured on a copy of a real record: 20 entries judged in
  memory, `write_record` returned True, **0 of 20 settled on disk**. After: 20 of 20, with
  drift-by-count and drift-by-content verified byte-for-byte unchanged.

  **Introduced by the run-36 top-key repair**, which shipped with a red-check that could not see
  it: the check exercises `write_record` with entries carrying **no judgment fields**, so a branch
  that drops judgment fields passes it. That half is filed separately as `776507b529c5` and is the
  more important lesson — *a fixture simpler than the data is a check that cannot fail in the one
  direction the code can break.*

  **The data damage is NOT repaired and is filed as `0b75182d495c`:** 1,496 of 4,559 recorded
  `done.entrypass` keys name spans that are unsettled on disk (677 Marvel, 195 DC, 151 Final
  Fantasy). Those model calls were spent and the answers thrown away while RUN_STATUS.md reported
  the progress as achieved, and because `phase_entrypass` skips anything already in its done-keys,
  **no amount of running the pipeline repairs it.**

  *Fix: hoisted the fold above the `if`/`else` so the two paths cannot drift apart again; only the
  drift log line remains conditional.*

- **[M49 — RESOLVED] HARD RULE 0 WAS BEING BROKEN INSIDE THE WORK-ORDER SYSTEM ITSELF.** Work
  orders `64f73abd3540` and, for the residual damage, `fc8e20f90ee9`.

  **Root cause:** `workorders.file_order` stored `what[:600]`, `where[:200]`, evidence `[:400]`
  and `found_by[:80]`; `resolve()` stored `resolution[:400]`. Silently, with no marker. **An
  order's remedy is written at the end**, so the cut fell precisely on the instruction, and a
  resolution's reasoning — including several that ruled a finding NOT a bug and said why — was cut
  from the paper trail a later run reads to avoid re-opening declined work.

  **Measured before the fix:** 51 open orders sitting at exactly 600 characters, cut mid-word, and
  66 of that shift's own closures truncated at 400.

  *Fix: all five caps removed. Round-trip verified — a 1,541-character `what` and a 942-character
  resolution store whole. Order identity is unaffected because `order_id` hashes the raw `where`
  argument rather than the stored copy. Two evidence lists in `battery_faults` were uncapped in
  the same pass and their prose now says the three shown are the first three. Display truncation
  stays at the console render site, where it is reversible.*

  **The already-destroyed text is unrecoverable** — it was cut at write time, not hidden. The
  sweep found 45 open orders still holding a 600-character `what`: **28 tails are recoverable
  verbatim from `handoff/`, 17 have lost their remedy permanently.**

- **[M47 — RESOLVED] A LONG MAINTENANCE SHIFT STRUCTURALLY GUARANTEED STALE DAEMONS.** Standing
  since run #35 as a design question, work order `ff3c67a67b92`; the mechanism was finally
  measured by run #37 and filed sharply as `838be29f9e58`.

  **Root cause, and it is not the one the open entry recorded.** The entry blamed the 180-second
  settle window against a shift that rewrites `src/` for hours — true, but not the whole thing.
  `codewatch.stale()` compared against the digest seen at the **previous poll**, so the effective
  window was `max(STABLE_SECONDS, poll interval)`, and a genuine 180-second lull inside a long
  poll gap was invisible. Demonstrated: twelve consecutive polls over six simulated hours all
  returned "changed, settling" and the daemon never restarted.

  *Fix: new `quiet_seconds()` measures wall time since the newest write under `src/` (every `.py`
  plus the directory's own mtime, so a created or deleted file is timed too); `held = max(seen,
  quiet)` so the new rule is never more conservative than the old, and `quiet` is trusted only
  when corroborated by a file newer than the process start, so an untimeable change falls back to
  the old behaviour. `quiet` can never exceed the true hold time, so it settles later than truth,
  never earlier. `BUDGET_PER_HOUR`, `_claim_restart_slot` and `_take_locked` untouched — no
  restart-storm surface. The drill net `a_change_must_settle_before_it_restarts_anything` still
  holds.*

  **Note for the next reader:** foreman (15:05) and overwatch (15:10) ran the whole of run #37 on
  pre-shift code, because they were holding the *old* codewatch in memory. They need one restart;
  after that they keep themselves current.

- **[M50 — RESOLVED] `silence.write_json` LEAKED A TEMP FILE ON EVERY DENIED REPLACE.** Work order
  `b464a0311775`.

  **Root cause:** the temp was removed only when the **dump** failed. When the dump succeeded and
  `replace_retry` was then denied — the ordinary Windows case, and the entire reason
  `replace_retry` exists — the function returned with `<path>.<pid>.<tid>.tmp` still on disk, and
  no cleaner anywhere in the tree. Because the name is pid- and thread-qualified, leaks
  **accumulate rather than overwrite**, so the hottest, most contended files littered most.

  *Fix: both cleanup paths route through a new `_discard_tmp()`, total by design like `note()` —
  a raise from the cleanup would replace a recorded, survivable denied write with an unhandled
  exception in a caller that, by `write_json`'s own promise, has no handler for it. Watched red
  then green across four cases including one where the removal itself is denied and the
  never-raises promise still holds. Four confirmed leftovers were found on disk and removed after
  verifying every owning PID was dead.*

- **[M51 — RESOLVED] A CRAWL FAILURE READ AS A GENUINE ZERO.** Work order `051244c2628f`.

  **Root cause:** `feats._api_list_all`'s mid-walk failure branch was guarded by `if rows:`, so a
  walk whose **first** request failed incremented nothing and returned `[]` — byte-for-byte what
  "this entity has no pages" looks like — while the caller's "discovery lists: complete" banner
  still printed. Hard Rule 0's smaller universe, arriving through the error path instead of
  through a cap.

  *Fix: any `api()` failure with the walk incomplete now counts. Five cases verified with `api()`
  stubbed: a failed first request is flagged; a genuine empty result is not, so the two zeros are
  now distinguishable; and the partial, complete and looping walks are unchanged.*

- **[TWO HALTS — BOTH RAISED AND LIFTED BY THIS SHIFT.]** Recorded here because the doctrine says
  a halt that fires against its author minutes after they wrote the defect is the system working.

  **`DRILL_BREACH` (22:44, lifted 23:31)** — order `a74678936964`. `blast_cap_bites` breached
  because order `528e5b07fded` correctly moved `local_agent`'s `_blast_ok` charge below the
  find-string-uniqueness check and the `--no-apply` return, and the drill's probe had been
  demonstrating the cap **through exactly that path** (`apply=False`, a find string occurring zero
  times). **The cap itself was never broken** — three agents reached that independently, and a
  fourth re-judged the charge point and found it correct. The probe was rewritten to drive the
  real path: a genuine unique find string with `apply=True` against a scratch file under
  `handoff/`, both bounds taken to zero so the refusal arrives before any write. Red with
  `_blast_ok` neutered, green against the real module.

  **`SECRET_IN_EXPORT` (23:53 and 00:03, lifted 00:2x)** — order `f0fe623a67c0`. `publish.py`
  refused two credential-shaped values staged for the **public** repo, in a sweep agent's scratch
  script under `handoff/` — which is a `COPY_DIRS` root, so everything written there is published.
  They were **fabricated fixtures**, written by the batch-14 agent because its brief asked it to
  prove the credential scanner actually catches credentials. Nothing leaked; nothing was pushed.
  Scratch scripts moved out of the published tree, the audit line redacted to the *shape* of each
  probe with a note saying so, and the process fault filed rather than just the symptom. Post-fix
  scan: **0 hits across every published root.** *On 2026-08-25 a push of deliberately-corrupted
  source reached a public repo and nothing refused it. This time something refused.*

- **[FIVE VACUOUS DRILL NETS AND THIRTEEN MORE — RESOLVED]** Orders `5737db3ce725`,
  `18612d60c3f2`, `adc3dc9c3fc6`, `07c7379597ba`, `f016ae5433b1`, then the run-37 sweep's
  `5eea5c20db8a`, `7cc460706efe`, `c54a22a4e6fc`, `8f4bb64503c2`, `78f04bec15ad`, `5ed81099fc49`,
  `18958aba2143`, `9ada7602a356`, `cf9ee9000be8`, `e2f44baedfdc`, `64dfe6bec15c`, `5c87268a388c`,
  `64c8827cc72b`.

  **The pattern, which is the finding:** nets asserted **presence** — a name, a string, an import
  appears somewhere in the module — where they needed to assert **reachability**, that the call
  actually runs on the path that matters. Fixtures doing the forbidden thing on the live path,
  with the required token parked after a `return` or inside `if False:`, passed. One net stayed
  green against the *real* `cascade_bridge.py` with its actual router guard deleted, answered
  instead by an unrelated `if` elsewhere in the file.

  **Two could false-halt the library rather than miss a fault:** `datasette_config_is_generated_not_copied`
  wrote `state/datasette.json` on every run and, since the run-36 fix returned `None` on a denied
  replace, did `open(None)` and escalated to OWNER; and two nets pinned to an **import alias**
  would have breached — and halted the library — on a rename of a correct import.

  *Every rewritten net was watched go RED against the fixture that defeated the old net and GREEN
  against the real tree, with the closures reached through their code objects so the thing
  watched refusing is the net itself. Final: 251 nets attacked, 251 held, 0 breached. Liveness
  fell 35 → 34: `_calls` and `_called_names` had no callers left after the rewrite and were
  removed, their lessons kept as comments where they stood.*

- **[THE SYSTEMIC DISCARDED-WRITE-VERDICT PASS — RESOLVED]** Order `e7b6dcc8d630`, worked as three
  parallel passes over **41 sites in 24 files** (the order said 46/30; the difference is sites
  other orders closed earlier in the same shift).

  **Outcome: 33 gated, 6 commented as genuinely best-effort with the reason recorded, 4 confirmed
  not-a-bug.** Each site was judged rather than mechanically gated, against one question: *if this
  write silently fails, does anything later give a wrong answer, or merely a slower one?*

  The strongest cases: `pipeline.save_state` (a resume point that `health.py` both reads and
  read-modify-writes, so silent staleness made a restart redo work **and** made a repair tool call
  settled batches stranded); `overwatch`'s `LEDGER → .corrupt` quarantine (the move was announced
  while the wreck sat under its own name, after which `save()` wrote over the only copy — `save()`
  now refuses while preservation has failed); `navtree` (printed "wrote N KB" by `stat`-ing the
  file already on disk — a receipt, at the old tree's size, for a write that never happened); and
  `health`'s preflight stamp (`battery_faults` **ages** whatever stamp is present, so a denied red
  stamp left yesterday's green one grading the battery).

  **One premise was refuted in source and is recorded so nobody re-gates it:** `sweep_plan`'s
  `SWEEP_COVERAGE.json` write cannot make an incomplete sweep look complete. `covered_by()` reads
  the shards and consults that file only as an **additive** fallback that never removes, so a
  refused write errs toward reporting a *gap*, and it self-heals by refolding from the shards on
  every `record()`. The shard write beside it **is** the completeness evidence, and that one was
  gated.


### Run #36 (2026-08-27) — the daily shift that found M46

- **[M46 — RESOLVED] `mutate.py --target all` DIED ON A MISSING SANDBOX TARGET, AND THE CAUSE WAS
  A REAPER WITH NO NOTION OF OWNERSHIP.** Three runs blamed three different things and all three
  were wrong: run #34 said concurrent edits during the copy (ruled out — it reproduced on a
  stable tree), run #35 said the `drill` gate, and run #36's own first two probes said `drill.py`
  generally.

  **Root cause:** `mutate.reap_orphans` deleted mutation sandboxes by **prefix and age only**. It
  had no idea who owned one, so it deleted sandboxes belonging to **other live processes**. The
  six-hour age gate was the *only* thing standing between a reap and somebody else's in-flight
  run — and an age gate is exactly what a caller lowers when it wants to watch reaping actually
  happen. So the drill net `abandoned_sandboxes_are_reaped`, **in the act of being made able to
  go red**, destroyed every concurrent sandbox on the machine. The sharpest form yet of this
  project's standing lesson: *the net that could not fail was harmless, and fixing it so that it
  could fail is what made it dangerous.*

  **How it was found, after three failures to find it:** the control nobody had run — build TWO
  sandboxes, run `drill.py` in only ONE, watch both. **Both died together at six seconds.** A
  bare sandbox with nothing running against it died too; decoy directories under other prefixes
  survived the same window untouched. That cleared `drill.py` and narrowed it to code matching
  `SANDBOX_PREFIX`. It had stayed invisible for three runs because **reaping was the one
  destructive operation here that reported nothing** — `removed` went to callers that discarded
  it, and the only `note()` covered the *failure* case, so an incomplete reap was recorded and a
  successful one was not. A reap ledger added this shift (`state/reap_ledger.jsonl`: pid, argv,
  paths, stack) named the call site on the first attempt.

  **Fix:** a sandbox records its owner pid in `_owner.json`, written *before* any module is
  copied. `reap_orphans` skips any sandbox whose owner is alive, at any age; the age gate becomes
  the fallback it should always have been. An ownership claim **expires** after 24h — the first
  cut did not, and the run #36 whole-tree sweep caught that within the hour: pids are recycled,
  so an unrelated long-lived process inheriting the number would have made the directory
  permanently undeletable, recreating the 154 MB leak the reaper exists to prevent. A fix whose
  failure mode is the bug it replaced is not a fix. Unknown or undated claims fall back to
  age-only.

  **Proven:** `handoff/run36/m46_fix_redcheck.txt`, seven arms — a live-owned sandbox survives
  `older_than=0`; *another live process's* sandbox survives it; an expired claim on a live pid is
  ignored; an undated claim is not trusted forever; a dead-owner sandbox is still reaped; an
  unowned old one is still reaped; and with the ownership check disabled arm 1 goes **RED as
  required**. Arm 1 failed on the first attempt (the rule exempted only *other* processes, so a
  self-owned sandbox was still deleted) and the rule is now "any live owner, including self".

  **Consequence:** the §3b mutation mandate is unblocked for the first time in three runs.

- **[R36.1 — RESOLVED] THE CANONICAL CORPUS HAD NO BACKUP, AND `.gitignore` SAID WHY.** `data/`
  is gitignored and `git ls-files data/` returns **zero**, so 219 canonical files — 214.7 MB,
  including the 217-source corpus every other file in `data/` is derived FROM — existed in
  exactly one place on one disk. The `.gitignore` comment justifying the exclusion called it
  "derived data", which is **false** for `data/records/`, `WIKI_HOSTS.json` and
  `CHARTER_SPINE_CODES.json`; that false half-sentence is the whole reason nobody ever asked what
  the rule was excluding. Root cause therefore recorded as a *documentation* defect with a data
  consequence. Fixed by `src/canon_backup.py` (verified by reading every archive member back
  before recording success; 214.7 MB → 50.9 MB in 6.6 s; restore proven byte-identical), wired
  into the supervisor twice a day, and the `.gitignore` comment rewritten to say what is
  genuinely derived and what is not. **Still the owner's:** this is a second copy on the same
  disk.

- **[R36.2 — RESOLVED] `pipeline.write_record` CARRIED THE UNGUARDED FORM OF THE BUG BEHIND THE
  STANDING BLOCKING ORDER.** Its sibling `write_record_catalogue` was fixed on 2026-08-25 after
  31 of 216 records lost their synthesis block; `write_record` was not. Both its paths were
  wrong: the drift branch overwrote every non-`entries` key from the pipeline's hours-old
  in-memory copy unconditionally, and the no-drift fast path never merged at all (`merged = rec`
  wrote that stale copy whole — equal entry lists do not mean equal records). Found by the run
  #36 whole-tree sweep, batch 3. Fixed by applying the same ruling to both writers: absent or
  `None` means unauthored and the disk value stands, an explicit empty value still clears.
  Proven in `handoff/run36/pipeline_merge_redcheck.txt` with the old merge restored as a control
  — arms 1 and 2 both go red.

### Run #35 (2026-08-27) — the first full daily shift

- **[R35.1 — RESOLVED] THE ASSAY'S ARITHMETIC COULD BE CORRUPTED WITHOUT THE BATTERY NOTICING.**
  Root cause: 24 places in `assay.py` where a single-token corruption survived the entire
  battery, because the function containing them was never CALLED by any check — the guards were
  read, not exercised. Fixed by `verify_math` section 34 (§20r, 69 checks) exercising
  `axis_score`, `band_for_quantity`, `_check_constants`, `interval_from_hands`, `regress_test`,
  `null_instrument`, `_rho_source`/`_rho_doc`, `_interval`, `instrument`, `calibration_report`
  and the promotion/ceiling flags. **Verified by re-applying each of the 24 mutations
  individually: 24/24 killed, `assay.py` byte-exact after every one.** Three needed sharper
  checks than the obvious ones: the ladder walk needed STRICT ordering (a non-strict comparison
  passes against a mutant where every quantity returns the top rung), the calibration margin
  needed a passing band exactly one step wide, and the correlation-provenance guard needed a
  forced reload rather than a forced fallback.

- **[R35.2 — RESOLVED] `local_agent` COULD REPORT SUCCESS HAVING ACHIEVED NOTHING.** Root cause:
  `ok` meant "the model stopped talking without breaking anything". Measured 2026-08-25: 6 turns,
  5 tool calls, every `propose_patch` refused, `{"ok": true, "patches": []}`. Fixed by
  `_achievement()`, which reads the outcomes `_settle` was already writing into the audit trail;
  a run that attempted patches and landed none is no longer `ok`, while an answer-only run keeps
  its verdict. Drill net put to all three shapes, watched red.

- **[R35.3 — RESOLVED, BLOCKING] THE MODEL'S WRITE LANE NEVER ASKED WHETHER THE LIBRARY WAS
  HALTED.** Root cause: `local_agent.run()` had no `escalation.assert_clear()` call while twelve
  other modules did — the actor most able to worsen a halted situation was the only one not
  asking, and `verify_math`'s own interlock roster did not list it either. Fixed. The drill net
  for it was FIRST written as a substring scan and **passed against a build with the call
  replaced by `pass`**, because the comment explaining the call still contained the word; it now
  walks the parse tree for a real Call node.

- **[R35.4 — RESOLVED, BLOCKING] SIXTH BYPASS OF THE `local_agent` WRITE GATE.** Root cause: every
  check in `_safe()` ran on `os.path.abspath`, which normalises a string and resolves nothing, so
  a directory junction under `src/` pointing at `state/`, `data/records/` or the charter
  satisfied the allowlist, matched no denylist, and the write followed the junction to the real
  file. Same family as the five earlier defeats (letter case, name prefix, NTFS alternate data
  stream, case-sensitive extension, unlisted directory). Fixed: the decision is made twice, on
  the path as written and on `os.path.realpath` of it, sharing one `_denied_region()` rule. Drill
  net stages a real junction and removes it.

- **[R35.5 — RESOLVED] THE BATTERY OPENED 19 LIVE TLS CONNECTIONS PER RUN, AND IT BLOCKED THE
  MUTATION MANDATE.** Root cause: `standards.check()` probes fandom over IPv4 and `verify_math`
  calls `check()` ~19 times; `getaddrinfo` takes no timeout, so nothing bounded the whole call.
  `mutate.py` refused to run at all — "verify_math TIMEOUT ... a gate that cannot finish on
  unmutated code cannot judge a mutant". Found with a socket tracer, not by reading. Fixed by
  memoising `fandom_ipv4_reachable` per process (stubbed calls bypass the memo so §19z's three
  synthetic networks still get three answers). 19 remote connections → 1; battery 87s.

- **[R35.6 — RESOLVED] FIVE UNFIXABLE ORDERS WERE ADDRESSED TO A BOT, FOREVER.** Root cause:
  `BINDING_SUSPECT` could not distinguish "the source is bound to the wrong wiki" from "the
  binding is right and the catalogued entry names are not article titles" — the second is not
  repairable by anything, and three of the five were that. Fixed by MEASURING it:
  `binding_health` reads each suspect host's own `sitename` and compares it to every source bound
  to that host (rapidfuzz, thresholds 85/65 with an UNCLASSIFIED band). Calibrated live —
  eberron/warthunder/aneurism 100, prime 50, starrealms 36. The two cases route to two OWNER
  codes and the old order is superseded. A hand-maintained roster of known-fine hosts was
  deliberately not used.

- **[R35.7 — RESOLVED] A PARTIAL CANARY RUN COULD SHRINK THE WHOLE-ESTATE REPORT.** Found by
  tripping it: `binding_health --host a --host b ...` wrote a `BINDING_HEALTH.json` with
  `"checked": 5`, and `workorders.sweep` reads that file AS the estate. Partial runs now merge
  into the standing report and mark themselves; an unreadable report refuses the merge rather
  than landing over it. Drill net drives the real `run()` with the network stubbed.

- **[R35.8 — RESOLVED] SIX WORK ORDERS DESCRIBED THREE SUBSYSTEMS THAT NEVER EXISTED.** Root
  cause: every escalation files a real order, and the rung-4 drill probes released their
  synthetic subsystem but never the `SUBSYSTEM_STOPPED`/`SUBSYSTEM_RESUMED` orders it filed —
  two more per battery run, `seen 15x`. Fixed by `_sweep_probe_litter()`, the discipline the
  DRILL_AREA probe already kept. New net stops and resumes a fresh synthetic subsystem and
  asserts the open-order ID SET is unchanged — by identity, not count, since an unrelated
  detector filing one while a probe leaks one nets to zero.

- **[R35.9 — RESOLVED] `roll.exclude(rows=...)` WROTE THE CALLER'S TEST ROWS ONTO THE LIVE
  ACQUISITIONS ROLL.** Root cause: `rows=` affected the read and not the write, so passing test
  data in order to avoid touching the real file was the way to overwrite it. It destroyed the
  live 216-source roll twice on 2026-08-27, with no backup of that file anywhere. Recovered from
  `data/records/*.json` plus two dated owner rulings, and **independently verified this run**:
  216 roll names against 216 record files, exact set match both directions, entry counts
  agreeing. Fixed — `rows=` now means "work on my copy" on the write too (no callers in `src/`
  depended on the old behaviour) — with a drill net that points `ROLL` at a throwaway file and
  proves both that a caller's rows do not land and that the ordinary path still persists. The
  standing gap it revealed (no backup for canonical data files) is filed at OWNER, not fixed.

- **[R35.10 — RESOLVED, A REGRESSION THIS RUN CAUSED] THE SECOND OPINION WAS TALKED OUT OF 96% OF
  ITS FINDINGS.** Root cause: the run's own second-opinion batch added BLE001, S110 and S112 to
  `NOT_FILED`, on the stated grounds that `silence.audit()` treats those handlers as "an accepted
  category". It does not — it prints "each of these can turn a failure into a plausible negative
  result", lists all 152, and exits 1. The BLE001 waiver additionally cited this module's own
  docstring as authority, a docstring which names BLE001 as the example of what must NOT be
  waived. 531 + 63 of 1,002 live findings would have stopped reaching the queue while the report
  went on looking healthy. All three reverted the same shift, with the reasoning kept in place of
  the waivers. Found independently by sweep35 batch 7, which is the sweep earning its cost.

- **[R35.11 — RESOLVED, A REGRESSION THIS RUN CAUSED] A WORKING TOOL REPORTED AS ABSENT.** Root
  cause: the returncode check added so a failed tool could not read as clean admitted only rc 0
  and 1, and **vulture exits 3 when it FINDS dead code** — so every run in which it did its job
  came back `TOOL ERROR (vulture rc=3)` and the report ended `ABSENT: vulture — install before
  treating this page as a second opinion`, about a tool that was installed, had run, and had just
  printed three findings. Exit codes measured on this machine rather than assumed; guard now
  admits 0/1/3 and still refuses a nonzero exit that parsed nothing.

- **[R35.12 — RESOLVED] A STANDARD THAT COULD NOT BE ASKED SIMPLY VANISHED.** Root cause:
  `standards.check()` emitted the "local model has a live runner" row only when the Ollama daemon
  answered, and fell through otherwise — so an 8s timeout against a busy daemon made the standard
  disappear and `N/N standards met` counted a smaller denominator. Measured: 44 declared / 44
  emitted, then 42 minutes later while an unrelated process held ~9,600 connections to Ollama.
  Fixed by appending to `_dropped`, the mechanism this module already had. Found by a check
  (declared-vs-emitted) that this same run had merged minutes earlier.

- **[R35.13 — RESOLVED] THE BATTERY USED ITSELF AS A FIXTURE.** Root cause: two checks drove
  `overnight.running()` off THIS PROCESS's command line, so one failed when the suite was run by
  import and the other failed whenever anything else on the machine had `verify_math.py` on its
  command line — a battery whose answer depended on who else was running. Fixed with a synthetic
  `pid|cmdline` listing exercising all three states (another process / only this one / nobody).
  The listing is deliberately UNQUOTED, matching a real row: a quoted path yields a token ending
  `.py"`, the resolver fails open on every row, and all six checks would have agreed vacuously.

- **[R35.15 — RESOLVED, A REGRESSION THIS RUN CAUSED] A BETTER BATTERY BROKE THE TIER THAT
  CHECKS MODULES LOAD.** Root cause: `verify_math.py` is a flat script, so `--help` ran the
  entire suite — survivable at ~44s, not at the 1,052 checks and ~87s run #35 grew it to.
  `allsweep`'s IMPORT tier probes every module with `--help` under a 120s timeout, so it began
  timing out and grading `verify_math` **BROKEN**. A tier that exists to answer "does this module
  load" was answering "did the whole battery finish in two minutes", and that answer was drifting
  toward no as the battery got better — the wrong direction for a check to move. Fixed with a
  `--help` short-circuit placed before the sibling imports, so it answers without loading
  anything: 120s timeout → 0.9s, full run unchanged at 1,052/0, allsweep imports clean again.

- **[R35.14 — RESOLVED] THE SWEEP'S OWN COUNT UNDER-REPORTED.** `workorders.sweep_detectors`
  discarded the result of three `file_order` calls in the binding block, so `swept: N filed`
  under-counted by exactly the binding orders and the `None` a refused queue write returns went
  the same way. Measured before/after on a real sweep: a run that filed five binding orders
  reported 2, and now reports 7.

### Run #34 (2026-08-25 late) — the first daily shift
- **[M37 — RESOLVED, run #34] `silence.py:133`'s SILENT-HANDLER DETECTOR IS A TAUTOLOGY, AND
  EVERY OTHER MODULE TRUSTS IT.** `uses_exc = bool(node.name) and node.name in body`, where
  `body = ast.dump(node)` — and `ast.dump` **always** contains the handler's own `name=` field.
  So `except X as e: pass` is classified "observed" every time, regardless of whether `e` is ever
  used. This is the canonical detector behind `local_agent.py`'s `run_check(check="silence")` and
  the failure-ledger triage. Batch 16 reproduced it with a script. Zero live false negatives in
  the current tree, which is exactly what a check that cannot fail looks like. **Fix wants the
  companion net that proves it still catches a genuinely unused binding.**

  **ROOT CAUSE (run #34):** `uses_exc` tested `node.name in ast.dump(node)`. For `except ValueError as e:` the dump always contains `name='e'`, so the substring was present whether or not `e` was ever read — every NAMED handler scored as observing its exception and only a bare `except:` could ever be caught. Replaced with a real check for an `ast.Name` load of the bound name inside the handler BODY. It reclassifies zero of the existing handlers today, which is the point: it closes a hole rather than correcting a count. A second instance one line above — the `records` test scanning the whole node, so the exception TYPE NAME counted as observation — was fixed in the same pass. Order `f939d1601734`. Drilled: net 9 asserts `replace_if_unchanged` reports an accurate reason, and the handler scan is exercised by `silence.audit()` in the battery.
- **[m39] `scout.sweep(limit=4)` can starve lower-ranked sources indefinitely.** `foreman`'s
  `scout_hostless` calls it with `limit=4`; `scout.sweep` sorts `todo` by page count and takes
  `[:limit]`. The ranking is deterministic and recomputed every round, so while the top four
  remain hostless the fifth and below are never attempted — round after round. Hard Rule 0's
  ranked-then-truncated shape, but removing the cap changes per-round load, so it is an owner
  call rather than a silent fix.

  **ROOT CAUSE (run #34):** confirmed exactly as filed, and worse than the entry states. `scout.sweep` ordered `hostless()` by entry count and took `order[:limit]`, with `foreman.scout_hostless()` calling `sweep(limit=4)` on a 30-second loop. Because a source leaves `hostless()` only when a scout SUCCEEDS, a source that keeps failing stays hostless, stays in the top four, and is re-scouted for ever — the window could not rotate, because the only thing that moved a source out of it was the very success that was not happening. Measured at the time of the fix: **15 hostless sources, of which 4 could ever be reached**. Now ordered LAST-ATTEMPTED FIRST (never-attempted sorts first), entry count demoted to the tie-break, attempts recorded in `data/SCOUT_ATTEMPTS.json` and stamped BEFORE the work so a crashing source cannot re-pin the window; `limit` survives as a RATE and the deferred sources are printed by name. Verified by simulating the rotation: **all 15 reached within 4 cycles.** Orders `a0c9c302016a` and its batch-04 duplicate `fc569423816c`. Drilled: nets 2a/2b prove the window rotates and that a newcomer sorts first, both watched red against the old ordering, with `SCOUT_ATTEMPTS.json` redirected so the drill never writes the live file.

- **[run #34 — OTHER FIXES LANDED THIS SHIFT, each with its own work order and paper trail in `state/workorders_closed.jsonl`]** 154 orders closed. The ones that changed behaviour rather than prose: the pipeline runner no longer exits 0 having done nothing (`8be1ca1878d8`); `write_record_catalogue` no longer lets a caller's `None` erase a key it did not author, which is what nulled 26 sources' synthesis blocks (`7292a1c3d84b`); `local_agent`'s whole-suite gate no longer passes `10 FAILED` by substring (`59f0f59d42c5`); `publish.scan_for_secrets` no longer skips files over 2 MB (`0eb5c97399b0`) and its third `except ImportError: pass` around a safety now fails closed (`92893f250570`); `mutate.py` now actually acquires the lock `publish.py` tests for (`d779f541cd0b`); `codewatch.twins()` no longer matches a foreign tree's namesake (`a5f68abd1142`); `escalation._raise_halt` and `clear()` no longer discard their write verdicts (`f34eb664741f`, `b1f8c01d12d1`); `workorders.json` is written under compare-and-swap (`c296dfc7ce1d`); and four Hard Rule 0 truncations were removed from `scout`, `cosmology_graph` (71% of pairs), `genre`/`grounding` (a truncated confidence denominator) and `policy` (a `--limit` that DEFAULTED to 40).


- **[M37 — RESOLVED, run #33] THE QUEUE WAS BLIND TO THE BATTERY, AND ITS BLINDNESS SPOKE IN THE
  WORDS OF A CLEAN RUN.** `workorders --sweep` opened this run printing *"no open work orders —
  the nets found nothing outstanding"* while `verify_math` was FAILING its own sweep-completeness
  check and `health --preflight` was FAILING on a host with 805 empty entries. **`drill.py` was
  the only battery member that escalated.** `verify_math`, `health`, `allsweep` and `liveness`
  never called `escalate()` and appeared in no detector, so a red battery filed nothing anywhere.
  **Root cause:** `allsweep` grades a verifier bad only if it CRASHED or TIMED OUT — deliberately,
  because `silence` and `audit` exit 1 to mean "I have findings". `health --preflight` also exits
  1, for a different reason, and fell into that exemption; it left no machine-readable trace at
  all. The owner's ruling that reorganised this project around *"the detectors file, the run works
  the file"* was resting on a queue that could not see two thirds of the battery.
  **Blast radius:** every run since the ruling read a reassuring sentence that was not evidence of
  anything. Both faults above were found the pre-ruling way — a run reading console output.
  **Fix:** `health.preflight()` stamps `state/preflight_last.json` (the pattern `drill_last.json`
  has used since run #29). `workorders.battery_faults()` — PURE, over that stamp plus
  `data/ALLSWEEP.json` — files and closes `PREFLIGHT_PROBLEM`, `PREFLIGHT_STALE`, `BATTERY_GRADED`,
  `BATTERY_STALE`. `BATTERY_GRADED` mirrors allsweep's own `bad` formula so the two cannot drift.
  **Absence and staleness fire rather than pass:** "nobody has run the battery since Tuesday" and
  "the battery is green" are different sentences.
  **Caught in review of the fix itself:** `resolve_code` closes `order_id(code, where)`, and the
  first version took `where` from the live fault dict — so a *cleared* fault had no `where` to pass
  and would have filed orders nothing could ever close. `BATTERY_WHERE` is now a pinned table.
  **Drill (9 new nets, behavioural, pure-function attacked):** a green battery files nothing; a red
  preflight files; a failed import, a dirty lint tier and a crashed verifier each file; a MISSING
  artifact and a STALE artifact each refuse to read as green; every code filed can also be closed;
  no code is unreachable. All HELD. **Watched firing for real:** on its first live sweep the tier
  filed `allsweep grades 1 subsystem(s) bad: import verify_math`.
  **Corroborated independently:** run #33 sweep batch 10 found the same grading gap from the
  `allsweep` side without knowing this was being fixed.

- **[M38 — RESOLVED, run #33] THE CANARY ASKED WIKIS FOR PAGES THAT CANNOT EXIST, THEN CONVICTED
  THE HOST.** Nothing had ever run the full host canary. Run #33 ran it and quarantined **20 of
  134 hosts**. Nineteen were healthy.
  **Root cause:** `_probe_present` probed exactly one title, from `known_present_title()`, which
  returns a **catalogue entry name** — and entry names carry the cataloguer's disambiguators:
  `Scout (Jeremy Willis)`, `Sweet Tooth (Marcus "Needles" Kane)`, `Cetana (the Synthetic Queen)`.
  No wiki has an article at that string. Worse, the canary was two-valued and had to force every
  failure into one of two outcomes, so *"this wiki is down"* and *"these entry names are not
  article titles on this wiki"* both came out as DEAD — two faults with opposite remedies.
  **Blast radius:** a quarantine STOPS MINING. Nineteen live wikis were taken out of service by a
  probe fault, and the sicker a host's cache looked the likelier the canary was to be asked about
  it. **Self-inflicted within the run and reported as such** — the library's host health was worse
  for about forty minutes than when the run started.
  **Fix, three parts, each measured:** (1) strip the trailing parenthetical — `Scout` returns
  12,169 chars; (2) try up to `PRESENT_CANDIDATES = 8` candidates and stop at the first hit, with
  **the bound named in the failure reason** rather than left implicit — stopping on success is
  short-circuit, not truncation; (3) a third probe, `_probe_reachable`, and a pure three-valued
  `verdict()`: `True` healthy, `False` the host is at fault, `None` the host is up but the binding
  is suspect. **`None` does not quarantine.** New code `BINDING_SUSPECT` (BOTS) carries that fault
  instead. Measured: 20 → 6 → **1**. The one is `www.dandwiki.com`, correctly: HTTP 403,
  "restricted to logged in users".
  **Drill (5 new nets, over the pure verdict table):** up-but-no-title is not quarantined; an
  UNREACHABLE host is still called dead (*without this, dandwiki's 403 would start reading as
  healthy*); a host answering yes to everything is dead however reachable; a good host is healthy;
  every unhealthy verdict carries a reason.
  **Related, same run:** `health.check_caches()` no longer re-reports empty caches on quarantined
  hosts as fresh problems — the fault is held once, by `binding_health`. A permanent red is not
  extra safety, it is how a preflight stops being read.

- **[M39 — RESOLVED, run #33] A DRILL NET THAT COULD NOT FAIL, INSIDE THE BATTERY WHOSE JOB IS
  FINDING CHECKS THAT CANNOT FAIL.** `drill.py:1037` read
  `lambda: "pages_refused" in F.evidence_for.__doc__ or True`. The `or True` made the whole
  expression unconditionally true. **The masked half was testing the wrong thing anyway:** it
  asked whether a *docstring* mentioned the key, and that docstring does not — so the net would
  have failed the instant anyone removed the `or True`. A net asserting a fact about prose, then
  defanged so the wrong assertion could not embarrass anyone.
  **Fix:** `_refusal_is_recorded()` asserts `feats.py` carries `"pages_refused": unreal` **and**
  populates it on the refusal branch — both halves, because either can be removed without the
  other looking wrong. **Watched going red twice** (key removed; branch gutted) and green again on
  restore, with `feats.py` restored byte-for-byte.
  **Deliberately untouched:** `drill.py:706`'s `(LA.blast_reset() or True) and ... == 0` is a
  legitimate sequencing idiom whose real assertion can fail.
  **Found by:** run #33 sweep batch 5, which had been told to hunt exactly this shape.

- **[M40 — RESOLVED, run #33] THE OVERLAP GUARD RACED THROUGH A SHARED TEMP FILENAME.** BLOCKING.
  `runguard._land()` wrote through a fixed `path + ".tmp"` — one temp name shared by every process
  that ever claims the guard — in the one file whose entire job is preventing two maintenance runs
  from running at once. This is the exact collision `sweep_plan`'s shard docstring warns about and
  `silence.write_json` (pid + thread in the temp name) exists to end. **Not hypothetical:**
  `runguard._land:PermissionError` has fired 99 times in production, which is direct evidence that
  multiple writers contend on this path live.
  **Fix:** `return silence.write_json(path, rec, indent=2)`. Verified: writes, reads back, leaves
  no stray `.tmp`. **Found by:** run #33 sweep batch 4.

- **[M41 — RESOLVED, run #33] THE DEAD-CODE SCANNER HAD A CHECK THAT CANNOT FAIL AT ITS OWN
  FOUNDATION.** `liveness._parse()` swallowed every parse exception and returned `None`; `scan()`
  then dropped that module with a bare `continue`. **A module that would not parse reported
  identically to a module with nothing wrong in it** — in the tool whose whole purpose is finding
  checks that cannot fail. The precondition is real, not theoretical: this project has hit literal
  control-character corruption more than once, and `local_agent` patches source under model control
  with a documented history of kill-mid-write.
  **Fix:** `scan()` returns an `unparsed` list, so an unparseable module raises the finding count
  the `drill.py` ratchet watches instead of quietly shrinking the corpus. 0 unparsed today.
  **Found by:** run #33 sweep batch 8.

- **[M42 — RESOLVED, run #33] A QUEUE THAT ONLY GREW: THE CLOSE PASS WAS A NO-OP STANDING WHERE
  THE CODE SHOULD HAVE BEEN.** `workorders` detector 3 files one `HOST_QUARANTINED` order per
  host and its comment promised *"one order per host, so each closes on its own recovery."* What
  stood in that place was `filed.extend([])`. Nothing ever closed them, and `file_order`'s results
  were discarded too, so the sweep under-reported what it had filed.
  **Made visible at scale by M38 in the same run:** 14 hosts released, 14 orders still open against
  healthy hosts. **Fix:** close every `HOST_QUARANTINED` order whose host is no longer in
  `binding_health.quarantined()`, and actually collect the filed orders. Verified live — the sweep
  closed **19** stale orders and BOTS fell from 20 to 6 (1 real quarantine + 5 binding-suspects).
  **Found by:** run #33 sweep batch 16, which read the promise and the no-op sitting next to each
  other — before the fault fired in production forty minutes later.

- **[M36 — RESOLVED, run #32] THE WRITE VERDICT NOBODY READ: A FIX THAT LANDED IN THE WRITER AND
  NEVER REACHED THE TWELVE CALLERS ITS OWN DOCSTRING DESCRIBED.** `pipeline._landed()` returns
  True/False deliberately, and says why in as many words — *"the writers now return the verdict
  and the callers gate their done-keys on it."* **All twelve `land_json` call sites discarded it**
  (`pipeline.py:1489,1516,1521,1536,1647,1759,1769,1840,1878,1880,1881,1893`) and then appended
  their phase's done-key unconditionally. A denied rename therefore left the phase marked COMPLETE
  over a **pre-write artifact**, and because the done-key was already recorded, no later run ever
  redid it — the exact silent permanent loss `_landed` was written to close, reintroduced at every
  caller it claimed to have fixed.
  **Not hypothetical:** `runguard._land:PermissionError` has fired **99 times** and sits on the
  page's own swallowed list, so denied renames are a live event on this machine. **Blast radius is
  wider than one lost cycle:** phase artifacts are read by a later phase *in the same run* (phase 6
  reads phase 5's `TIERS.json`), so a stale artifact is a wrong input the next phase reports as its
  own empty result.
  **Root cause:** the repair was made in the writer and the *sentence* describing the caller-side
  obligation was never carried across. Standing lesson 28 — a fix must reach every file that makes
  the same inference — in a new costume.
  **Fix:** `pipeline.gate_done(st, phase, landed)`; all 12 sites collect their verdicts and gate
  the done-key, and a phase whose write did not land stays open and logs why.
  **Regression (verify_math §20q, AST not source-text, per lesson 26):** no `land_json` sits as a
  bare `Expr`; the scan still finds ≥12 calls (the anti-vacuity companion lesson 30 demands); every
  function calling `land_json` also calls `gate_done`.
  **Drill (3 new nets, behavioural):** a False verdict leaves the phase open; an all-True verdict
  still closes it (*a gate that refuses everything is a wall*); a phase that correctly wrote nothing
  is not held open. **Watched going red** against the real pre-fix `pipeline.py` from export HEAD:
  12 discarded verdicts, 5 ungated phases, drill net BREACHED, companion still HELD.
  **Deliberately untouched:** four early-return done-key paths (`phase_chain` under ten contests,
  `phase_history` with no charted tiers, `phase_write` with nothing settled) land nothing and are
  correct outcomes; the check is scoped not to demand a verdict about writes that never happened.

- **[m172 — RESOLVED, run #29] THE CHARTER REGRESSION HAD NOT DRIFTED; IT WAS NEVER ALLOWED TO
  FINISH.** `the automation reproduces the charter` (HIGH) sat 35 hours stale while
  `magnitude.py --calibrate` ran near-continuously, and three runs read that as instrument drift.
  `calibrate()` wrote `CHARTER_REGRESSION.json` ONCE, after all six benchmarks
  (`magnitude.py:829-836`), while the foreman kills it on its next lap (M15). Six charter assays
  against a rate-limited pool do not finish inside one lap, so **every killed attempt discarded
  every benchmark it had completed** — the job did the work and threw it away, on a timer.
  **Root cause:** a long job that is routinely killed, written as if it would not be. Its sibling
  `run_batch()` has the correct pattern and says so: *"Written to be killed."*
  **Fix:** checkpoint after every benchmark; resume an unfinished pass rather than restart it;
  abandon a pass older than the standard's own 26h floor. **And the trap inside the fix:** the
  standard holds on `bool(scored) and not bad`, so a partial file would turn it GREEN on the
  first consistent benchmark with five references unrun — green-by-absence aimed at the
  instrument. So `at` is withheld until the pass completes, the partial state names itself
  (`pass IN PROGRESS: N of 6`), and the verdict became a pure function
  (`standards.charter_regression_verdict`) so the half-finished state is assertable on synthetic
  input. Regression: `verify_math` §20m, six checks. Verified live: the file advanced for the
  first time in 35h.

- **[m175 — RESOLVED, run #29] THE COMPLETENESS PROOF ANSWERED A DIFFERENT QUESTION THAN THE ONE
  IT WAS ASKED.** Two defects in one mechanism, the second found by the sweep auditing the fix
  for the first, in the same run. (a) `sweep_plan.record()` serialised sixteen concurrent batches
  behind a `threading.Lock` — the right lock for the wrong topology, since run #28 each batch
  records in its own SUBPROCESS, so they contended as if unlocked. (b) The replacement derived
  `missing(run)` from a **newest-wins** merge over every shard on disk, which converts *"did run
  N read module X?"* into *"was run N the LAST run to read module X?"*. Shards are never pruned,
  so those diverge permanently once a later run records the same module.
  **Root cause:** a membership question answered with a recency instrument.
  **Fix:** per-run/batch/pid shard files (no shared mutable file on the write path), and
  `covered_by()` answering membership directly. Regression: `verify_math` §20n. Proven this run:
  95 modules, 0 uncovered.

- **[m173 — RESOLVED, run #29] `UNMEASURED` READ AS GREEN, ONE LINE UNDER THE COMMENT WARNING
  ABOUT EXACTLY THAT.** `sentences that survive the verbatim check` (HIGH) computed
  `True if fab is None else fab <= MAX_FABRICATION`, so the one state its own order text names in
  capitals — *"IF THIS READS UNMEASURED, TREAT THAT AS THE FINDING"* — was the state that
  SATISFIED the standard. `work_orders()` reads the boolean, so the finding could never be
  dispatched. **Root cause:** run #28 fixed this standard's ABSENCE and left its EMPTINESS green
  — the same defect one layer in. **Fix:** `fab is not None and fab <= MAX_FABRICATION`.
  Regression pinned in `verify_math`.

- **[m174 — RESOLVED, run #29] `dead_forever()` MEMOISED THE POOL'S DEAD BUCKETS FOR THE LIFE OF
  THE PROCESS.** `if _PROVEN[0] is not None: return _PROVEN[0]` cached the first answer and never
  looked again, inside jobs that run for hours or days. Broken both ways: a key that dies at noon
  is proven dead by the next `prove()` but a reader that first asked at 09:00 keeps claiming it,
  burning a deadline per call until restart — the shape of `hyperbolic:free` and
  `cloudflare:free` sitting at 0 successful calls while still being claimed — and a key the owner
  ROTATES stays excluded until restart, so the fix does not take. **Root cause:** a
  process-lifetime memo silently overriding `PROOF_TTL`, which already said an hour-old proof is
  not evidence about now. **Fix:** cache keyed on the proof file's mtime.

- **[m176 — RESOLVED, run #29] THE AUTONOMOUS WRITER COULD PATCH THE CONTRACT-ENFORCEMENT CODE.**
  `local_agent.DENYLIST` held the machinery that JUDGES a patch (foreman, silence, health,
  allsweep, estate, standards, verify_math) but not the machinery that governs every WRITE:
  `pipeline` (the two-writer contract itself), `runguard` (claim discipline), `gpu_lane` (the
  card's arbitration), `sweep_plan` (the completeness proof). **Root cause:** the gate list was
  drawn around "things that check patches", not "things a patch must not be able to weaken" —
  and every gate below would still have passed, since they verify a patch parses, lints, imports
  and leaves `verify_math` green, not that it left the contract intact. **Fix:** all four added.
  Found by sweep batch 16.

- **[m177 — RESOLVED, run #29] `cleanup.py` MARKED THIN DESCRIPTIONS AND THREW THE MARK AWAY.**
  `cleanup.py:174-177` set `e["thin_description"] = True` without setting `changed`, so a record
  whose only edit was that mark was never handed to `write_record` — the flag was set on an
  in-memory dict and dropped when the loop moved on. The module's docstring says thin entries are
  "marked, not deleted"; for every entry with no other defect they were neither. **Root cause:**
  a missed line in one branch of three; its two siblings both set it. Found by sweep batch 05,
  reproduced.

- **[m160 — RESOLVED, run #27] THREE CAPS AT ONCE ON THE FIELD THE ORDER TEXT SAYS TO READ, AND
  A FALSE CLAIM THAT EVERY ROW WAS LIVE.** `standards.py:952` built the observed string for
  `every pool failure is recognised` from `sorted(...)[:3]` with each error cut at `[:60]` and no
  age. Fourteen rows were open; three were shown. **The cap hid a pattern, not just data:** all
  fourteen were `All 1 candidates failed: <label>` — one unnamed engine wrapper across fourteen
  buckets — and from three samples that is invisible, which is why run #26 chased the top row
  alone and recorded the rest as "genuinely unexplained". The order also ended "anything here is
  happening NOW", while rows live 24h; all fourteen predated the fix that resolved them and none
  had recurred since the 06:51 bounce. **Root cause:** the same sentence as m145
  (`available_sample: models[:8]`) in a second file — a cap on the field a person reads to act.
  **Fix:** every row, whole text, with its age; order text now says to read the age and to read
  the rows as a set. *Export commit: the `run #27` sync of 2026-08-25.*

- **[m163 — MAJOR, RESOLVED, run #27] AN EMPTY CITATION PASSED THE VERBATIM GUARD, ALWAYS, AND
  TOOK AN UNRELATED FEAT WITH IT AS ITS EVIDENCE.** `magnitude.py:356`'s guard 1 exists to refuse
  any citation that is not one of the sentences handed to the model. `_norm("")` is `""`, and
  `"" in t` is True for every non-empty `t`, so the match generator succeeded on its **first**
  iteration: a model returning a number with no citation at all — precisely what the guard is
  for — got `hit` = whichever feat happened to be first in `mined_norm`, and `text` became that
  unrelated sentence. Guards 2 and 3 then judged the wrong evidence, so if that arbitrary feat
  mentioned the axis and named the subject, an **uncited score entered the library wearing a
  citation the model never made**. Found by the run #27 sweep (batch 07), confirmed by direct
  test of `_norm`. **Root cause:** the "a check that cannot fail looks exactly like a check that
  passed" shape, in the one place where passing means fabricated provenance. **Fix:** blank
  citation is now its own rejection (`"no citation given"`) before the match is attempted.
  *Export commit: the `run #27` sync of 2026-08-25.*

- **[m164 — RESOLVED, run #27] A REGRESSION CHECK THAT FAILED BECAUSE THE CODE IT GUARDS WAS
  IMPROVED, SHIPPED UNDER A GREEN CLAIM.** `verify_math.py:3541` grepped module source for the
  literal `record_unrecognised(pinned.bucket, raw or box.get`. Run #26 added the wider
  explain-only lookup and renamed that argument to `_text` — a strictly better version of the
  behaviour the check protects — and the check went red on a correct fix. It shipped unseen
  because run #26 ran its battery **before** that final edit (`verify_math.py` mtime 06:31,
  `cascade_bridge.py` 06:38) and recorded "719 passed, 0 FAILED". **Two root causes, both worth
  more than the check:** a source-grep check false-fails on any equivalent rephrasing (batch 01
  found several more of these), and a battery result is only evidence about the tree as it stood
  when it ran. **Fix:** re-pinned to the contract rather than the wording, and widened from one
  check to three (the recorded text is not the engine's raw aggregate; it is the unwrapped text;
  the wider lookup is still wired in). *Export commit: the `run #27` sync of 2026-08-25.*

- **[m165 / m166 — RESOLVED, run #27] TWO MORE SIBLINGS OF ALREADY-RULED SHAPES, NEITHER EVER
  VISITED.** Lesson 14's exact pattern, twice. `wh40k.py:230` wrote `data/WH40K_ASSAYS.json` with
  a raw `open(...,'w')` + `json.dump` while its **twin** `zfighters.py:478` — same shape, same
  job, same `main()` ending in a hand-built assay dump — was made atomic as "the m100 tail" on
  2026-08-25; now `silence.write_json`. `tiers.py:271`'s `deliberate_joins` capped shared evidence
  at `[:3]` on the same `shared_sample` key that `weave.py:478` and `pipeline.py:1795` both carry
  `# WHOLE list -- Hard Rule 0, ruled 2026-08-24` on, and that `cosmology_graph.py:86` was brought
  in line on in run #26 (m144) — the fourth member of the family. It mattered more than the key
  name suggests: the function's own docstring calls that list *the evidence* a xenoverse is
  artificial, and its only caller prints it as the justification, so three was the number of
  reasons a person could ever see for a join built on nine. *Export commit: the `run #27` sync.*

- **[m167 — RESOLVED, run #27] A BARE COUNT THAT COULD NOT DISTINGUISH FORTY SOURCES DRIFTING
  FROM ONE SOURCE GROWING.** `health.check_state` reported `entries stranded in closed batches:
  227` and nothing else, so diagnosis began with re-deriving the breakdown by hand. It took one
  query and the answer changed the reading entirely: **all 227 in a single source.** Now names
  every affected source, worst first, and records in-code why entries strand. The underlying
  positional-key defect is filed open as **M20** — this fix is the instrument, not the repair.
  *Export commit: the `run #27` sync of 2026-08-25.*

*Run #21 (2026-08-25 ~00:50 local) resolved four items, one of them Major. Detail in HANDOFF.md.
Export commit: the `run #21` sync of 2026-08-25 (see `git -C %PANSCRIPTUM_EXPORT% log`).*

- **[m98 — MAJOR, RESOLVED, run #22] THE POOL'S PERMANENT-REFUSAL BENCH WAS STRUCTURALLY
  UNREACHABLE FOR A WHOLE CLASS OF FAILURE, AND BLIND TO SPENT ACCOUNTS THAT ANSWER 200.**
  **What it was.** `cascade_bridge._ask_call` benches a permanently-refusing provider for
  `AUTH_BENCH` (4h) so the rotation contains only providers that could plausibly answer. It was
  not firing. Two independent causes: (1) `pump()`'s `except Exception` set `box["failed"] = True`
  but never `box["error"]`, so any failure surfacing as an **exception** rather than a
  `type:"error"` event matched the empty string in the classifier and took **no bench at all**;
  (2) the classifier's substring list was HTTP-status-shaped (`401/402/Authentication/
  invalid_api_key/credentials`), so a provider returning **200 with a billing complaint in the
  body** matched nothing — `zai:free` answers `{"code":"1113","message":"Insufficient balance or
  no resource package. Please recharge."}` — and `403` was missing for the same reason.
  **How it was proved.** At 01:22 on 2026-08-25 the live `bucket_state` rows showed
  `cloudflare:free` and `hyperbolic:free` holding hard 401s **12 minutes old** and `zai:free`
  holding its balance error **7 minutes old**, all three still being claimed and all three still
  counted by the `buckets with headroom` standard (22) — the exact case that standard's order
  warns about. Direct refusal measurement over three hours: **187 rate_limited / 59 error / 82
  ok**, with `model calls per hour` at **64 against a floor of 900**.
  **Fix.** `pump()` now records `str(exc)[:300]`; the classifier is case-folded and covers `403`
  plus balance/billing wording. Verified against the live error strings after the change: it
  benches exactly the three dead accounts and leaves every genuinely rate-limited bucket (groq ×4,
  gemini ×3, sambanova, nvidia, openrouter, cohere) in rotation — it does not over-bench.
  Pinned by 16 new checks in `verify_math` **§20f**. Also repaired in the same pass: `ask()`'s
  metrics line did `(got or {}).get("_via")`, an `AttributeError` whenever `_extract_json`
  returned a list or bool from a fenced reply. Export commit: `a911805` (code) and `5e90f42` (ledgers), 2026-08-25.
- **[m99 — MAJOR, RESOLVED, run #22] THE GPU FALLBACK WAS WEDGED WHILE EVERY PROXY FOR IT READ
  GREEN.** `the local model produces tokens` reported *"probe completed in 0.8s"* on the 01:19
  page; six minutes later four consecutive trivial generates timed out (60s, 45s, 45s, 40s) with
  `qwen3:8b` showing 100% GPU-resident and the daemon listening on 11434 — the two-hour wedge
  `standards.py:1018-1032` documents. `ollama stop` was accepted then hung in `Stopping...`, and
  killing the runner (`llama-server.exe` 43612) did not clear it: **the wedge was in the daemon,
  not the runner.** Restarting `ollama.exe` (45636 → respawned by the tray app as 41592) restored
  it — http=200, 8 tokens, 150ms of real generation. **Root cause of the wedge itself is not
  established** and this will recur; the standard already fires correctly, and the remedy is
  documented. Kept in `Watching`, not closed as understood. Export commit: `5e90f42`, 2026-08-25 (no code change — remedy was a daemon restart).
- **[M17 — MAJOR, RESOLVED, run #21] EVERY RENDERER REPORTED ITSELF AS A DOWN JOB, AND THE FALSE
  NAME HID THE JOB THAT WAS GENUINELY DOWN.**
  **What it was.** `overnight.running()` excludes the caller's own PID — right for *"is anyone
  ELSE running this?"* (a stage about to launch; a job refusing a second copy of itself), wrong
  for *"is job X up?"*. The "every managed job is running" standard asked the second question with
  the first question's function, from inside whichever process was rendering the panel.
  **How it was proved** — one standard, one instant, three processes, three answers: the public
  page (computed by `publish.py:168-172` inside publish.py) said `publish.py,read.py`; the local
  page (computed by `dashboard.py` inside dashboard.py) said `dashboard.py,read.py`; `allsweep.py`,
  a neutral third process, saw both renderers up and only `read.py` down.
  **Why it mattered.** The standard has **no entry in `foreman.REMEDIES`**, so every round routed
  it to the owner's decision file carrying a permanently false name — and `read.py`, genuinely
  killed by an M15 remedy, was buried in the same string. The finding-as-decoration failure that
  `standards.MAX_JOB_SILENCE_MIN`'s comment exists to refuse, committed by the roster check itself.
  **Fix.** Additive `include_self` keyword on `running()`, default unchanged so no existing caller
  moved; passed at the one liveness call site. `one instance of each job` was checked and is
  unaffected — it runs its own enumeration and never self-excludes. Pinned by `verify_math` §20e,
  which uses the verifier's own process as the fixture.
- **[m87 — RESOLVED, run #21] ONE HANDLER PRODUCED 85% OF THE PROJECT'S ENTIRE SWALLOWED-FAILURE
  LEDGER, MAKING THE STANDARD THAT WATCHES IT USELESS.** `sweep.load()`'s only call site
  (`sweep.py:129`) does no existence check, so every character the reader has not yet reached
  raised `FileNotFoundError` there: **18,418 of 21,764 ledger entries**, holding "unexpected
  swallowed failures" red at 19,043 against a floor of 2,000 — permanently, so it reported nothing.
  **The fix is not concealment.** A *corrupt* cache (a truncated write, a `JSONDecodeError`) is a
  real fault and was landing in the same bucket as those 18,418 non-events, where it could never
  be picked out; splitting them is the only way the real one becomes visible. The genuine path is
  still recorded, under a semantic label rather than a line number that goes stale when anything
  above it moves. Pinned by `verify_math` §20e.
- **[m88 — RESOLVED, run #21] `rigor.py` PRINTED THE FACULTY WEIGHTS AND THEN ANNOUNCED, ONE LINE
  LATER, THAT THEY WERE ZERO.** `main()` emitted the literal string *"Int/Wis/Cha currently cannot
  affect a Magnitude at all"* unconditionally, directly beneath the line printing
  `A.FACULTY_WEIGHTS` — which `assay.py`'s ERRATUM (X.11) had already set to **1/11 each**
  (verified live: `0.0909…`). The same section labelled its matrix *"the charter's declared 8
  weights"* while `len(A.WEIGHTS)` is **11**, describing a different matrix from the one it built.
  Because `rigor.py` is a diagnostic report, stale narrative there is not a rotting comment — it
  is the module returning a wrong answer. Fixed by making both DERIVED: the finding is computed
  from the weights, the label counts them. Pinned by `verify_math` §20f.
- **[m89 — RESOLVED, run #21] `measure_bit_value`'s WORKED EXAMPLE QUOTED THE PRE-FIX NUMBER.**
  The docstring showed `7.0 * 13.23 = 92.6 bits`. **13.234 is `rung_description_length("M5")/10`**
  — the cumulative quantity the function deliberately abandoned, because cumulative content makes
  every M0 axis point worth zero bits (`tempus.py:182-186` split `band_resolution` out for exactly
  that reason). The code was corrected and pinned by `verify_math.py:382-384`; the worked example
  beside it was not, so the file went on quoting the figure its own code no longer used. True
  value **3.043 → 21.3 bits**, confirmed by running the module. §20f now pins the docstring's
  numbers to the function's own return value, so prose and data cannot drift apart silently again.

*Run #20 (2026-08-24 ~23:40 local) resolved seven items, one of them Major. Detail in HANDOFF.md.*

- **[MAJOR -- RESOLVED, run #20] `phase_entrypass` RE-ASKED THE MODEL ABOUT 66 BATCHES ON EVERY
  PASS, FOR EVER, BECAUSE THE SAME RULE WAS WRITTEN TWICE AND ONLY ONE COPY WAS FIXED.**
  **What it was.** `cleanup.py` strikes an entry by setting `excluded` and leaving `catalogued`
  false, and both loops in `phase_entrypass` that could set `catalogued` skip a struck entry --
  so `catalogued` is never written for one. Two separate gates decided whether a batch was
  finished: the **resume** gate (`batch_settled`) tested `catalogued OR excluded`, and the
  **write-completion** gate tested `catalogued` alone. Any batch holding a struck entry could
  therefore never satisfy the completion gate, so `done_keys.append(key)` never ran; the resume
  gate then failed on membership and the batch was resubmitted to the model on every pass.
  **Measured before the fix: 149 struck entries across 31 records, falling in 66 of 4,416
  batches -- 66 wasted model calls per full entrypass pass, permanently**, against a pool
  answering roughly a third of its calls. Worst record: `fire-emblem.json`, 57 struck entries.
  **Root cause.** Not the missing clause -- the rule existing in two places. `batch_settled`'s
  own docstring records this exact exclusion bug being found and fixed at length; that fix
  reached the resume gate and never reached the completion gate twelve lines further down.
  **The fix.** One predicate, `pipeline.entry_settled()`, called by both gates, so they cannot
  drift again. Pinned by `verify_math` section 20d with six behavioural checks plus two that
  assert the rule is spelled out exactly once and that the one copy is the definition.
- **[RESOLVED, run #20] THREE `foreman.py` ATOMIC WRITES DISCARDED THE BOOLEAN THEIR OWN COMMENTS
  WARNED ABOUT.** `_retire` (whose comment says "a torn or stale write here would silently
  discard its newest finding"), `restart_ollama`'s rate-limit stamp, and `round_once`'s
  operational log all called `silence.replace_retry` and threw the result away. Consequences,
  each specific: a denied `_retire` leaves a finding un-retired and its standard red for
  invisible reasons; a lost Ollama stamp makes the **30-minute restart guard fail open**, so the
  daemon can be killed again next round; a lost round log makes `foreman_report()` replay the
  previous round as if it were current. Same omission as `triage_swallowed`'s, fixed one run
  later in the same file.
- **[RESOLVED, run #20] `dashboard.jobs()` WAS THE ONE PANEL WITH NO FAULT ISOLATION.** Every
  sibling builder wraps its body and calls `silence.note`; `jobs()` did not, and `state()` calls
  it unguarded -- so one unexpected value in `read_auto.log` or `roll_auto.log` would raise
  through `state()` and be caught only at the HTTP layer, replacing the **entire** `/api/state`
  response with an error blob. The panel reporting on the project's bottleneck job should not be
  the one that can black out the page. Now isolated **per log** (`_read_row` / `_roll_row`), so a
  malformed reader line cannot also cost the roll its row.
- **[RESOLVED, run #20] `dashboard.py:362` CARRIED A STALE LINE-NUMBER LABEL** reading
  `dashboard.py:336` -- m81's drift, in a file not previously known to have it. Replaced with a
  descriptive tag, which cannot rot as the file grows.
- **[RESOLVED, run #20] `pipeline.py`'s ONE UNMARKED SILENT HANDLER.** `phase_shelve`'s absent
  `SHELF_RANKS.json` called neither `silence.note` nor `log` nor carried the exemption idiom,
  while its sibling three lines above notes the identical absent-file case. It **is** deliberate
  -- on a first run nothing is ranked and an empty prior is the correct starting state, unlike a
  corrupt one, which the very next handler refuses -- so it received the exemption string rather
  than a note. That is the difference between a silence that was decided and one that was
  forgotten.
- **[RESOLVED, run #20] THE CADENCE CLAIM IN `MAINTENANCE.md` AND `NEXT_STEPS.md` WAS WRONG
  AGAIN.** The owner moved the schedule to hourly; both files still said every 15 minutes.
  Corrected against `list_scheduled_tasks` (`11 * * * *`, 523s jitter, fires ~:19-:20), with the
  reasoning about overlap rewritten to match -- a fire now usually finds its predecessor
  finished. **The 15-minute heartbeat-staleness threshold in the overlap guard is a different
  number and was deliberately left alone**, now flagged in both files so it is not "fixed" to
  match. This line has been wrong twice in opposite directions, always because nothing read the
  cron back; both files now say to verify it with `list_scheduled_tasks`.
- **[WITHDRAWN, run #20 -- NOT A BUG, AND CARRIED SINCE RUN #2] "`pipeline.py`'s 9 shared
  cross-phase JSON writes use raw `open+json.dump`."** **They do not, and have not since run
  #4.** Verified by direct grep of every write site in the file: all four `json.dump` calls write
  to a `.tmp` and land through `_landed` / `land_json` / `silence.replace_retry`, and all eleven
  phase artifacts go through `land_json`. `BUGS.md`'s own m6 entry records this being done in run
  #4, to **eleven** artifacts rather than nine. The item survived seventeen runs of being copied
  forward, and run #19 promoted it to "the highest-value item in its section" while doing so.
  **A queue item never re-verified against source outlives the bug it describes and gains
  authority with every run that repeats it.** One genuine remainder, correctly scoped now:
  `update_handoff` writes `handoff/RUN_STATUS.md` via a bare `os.replace` rather than
  `silence.replace_retry` -- single-writer, machine-only, low exposure.

*Run #19 (2026-08-24 ~22:36 local) resolved eleven items. Full detail in HANDOFF.md.*

- **[M15's reporting half -- RESOLVED, run #19] BOTH KILLING REMEDIES UNDERSTATED THEIR OWN COST
  IN THE ONE LOG A HUMAN READS.** This is candidate (i) of the three in NEXT_STEPS section 2 B,
  and **only** (i); the design question (teach the remedies to check refusal, or put `read.py`
  in STANDING) is untouched and still the owner's.
  **What it was.** `restart_reader` and `kill_stalled_job` both ended their note with
  `"; supervisor restarts next cycle"`. True for a STANDING job -- the keeper re-asserts it every
  300 seconds. **False for `read.py` and `feats.py --roll`**, which hang off the supervisor's
  hours-long main lap. Every kill of the project's bottleneck job therefore reported itself as a
  five-minute inconvenience while costing 42-44 minutes, and once four hours.
  **Root cause.** One clause written for the common case and never revisited for the two jobs it
  was false about -- the same shape as every other comment-versus-code major here, except that
  the reader of the false statement was a human rather than a caller.
  **The fix.** A new `foreman._restart_horizon(frag)` **derives** the answer from
  `overnight.STANDING` instead of asserting one, keyed on the `lognames.OWNER` fragment the
  killer already matches processes with -- so it cannot drift from the roster it describes, which
  is the failure mode `overnight.py`'s own STANDING comment records (three partial copies of that
  roster once made a nine-job tree report as four). Pinned by `verify_math` section 20b,
  including a check that the bare false clause has not returned.
- **[RESOLVED, run #19] `restart_reader` COULD HAVE SIGTERMED A PROCESS THAT WAS NOT THE READER.**
  It tested `"read.py" in line` and `"--run" in line` as two **independent** substrings, so any
  command line containing both -- a shell running a grep that mentions them, a future
  `build_read.py --run-tests` -- was a valid kill target. `kill_stalled_job`'s docstring twenty
  lines below documents having fixed this exact loose-match class for its own matching and names
  the remedy. **That site had simply been left behind.** It now matches the single contiguous
  fragment `lognames.OWNER[READ]` (`"read.py --run"`). This is run #18's "kill by PID, not by
  pattern" lesson found inside the code that does the killing.
- **[RESOLVED, run #19] `triage_swallowed` HAD A THIRD FALSE-SUCCESS EXIT AND ONLY TWO WERE
  FIXED.** The comment above it already records that neither `replace_retry` return value was
  checked and that both failures *"reported the same cheerful 'swallowed and archived'"*. Those
  two were given honest returns; **the outer `except Exception` was missed**, so a corrupt
  `failures_archive.json` (JSONDecodeError on the read at the top) or any disk error still fell
  through to the success line while the ledger sat untouched. It now returns `False` and names
  the exception.
- **[RESOLVED, run #19] `FOR_OWNER.md` WAS THE ONE SHARED WRITE IN `foreman.py` NOT GOING THROUGH
  `silence.replace_retry`.** Every other write in the file uses tmp + atomic rename, citing m18.
  This one used a bare truncating `open()`, and it is **not** private to the foreman:
  `publish.py` copies it into the export tree on its own 10-minute loop, so a mid-write read
  could be published as a half file.
- **[RESOLVED, run #19] `foreman.py`'s DOCSTRING OVERSTATED THREE OF ITS SIX PATCH GATES.**
  Verified individually against source: there is **no standalone parse gate** (an unparseable
  patch is caught only by the later import check, after being written and reverted, and the
  refusal message blames a regex literal instead); `MAX_PATCH_LINES` is tested as `> MAX`, so
  exactly 40 is **allowed** where the doc said "fewer than"; and `allsweep --quick` is run **with
  no pre-patch baseline**, making the real test "no broken module at all", not "no *new* broken
  module" -- so one unrelated broken module silently refuses **every** patch from then on,
  blaming each one. **The gate was deliberately left strict** (loosening a safety check on
  model-authored writes to live source is not a change to make unasked); the docstring and the
  refusal message now say what the code actually does.
- **[RESOLVED, run #19] `gpu_lane._alive` CONTRADICTED ITS OWN DOCUMENTED POLICY.** The docstring
  states that unknown answers are treated as **ALIVE, deliberately**, because guessing dead lets
  two callers into one slot; an unparseable `pid` returned **False**. It now returns True, with
  the genuinely-absent case (`not pid`) left as False, because "no holder recorded" is a
  different fact from "a corrupt record". Only reachable via external corruption, but it is a
  direct comment-versus-code mismatch of the class behind this project's last four majors.
- **[RESOLVED, run #19] `gpu_lane._write_claim` AND `_touch` USED A BARE `os.replace`.**
  `_remove_retry`, in the same file, cites the Windows rename-denied race (m55) as its own reason
  to exist -- so the module already knew the hazard and two of its three writers did not use the
  remedy. `_write_claim` is the sharper of the two: a **new** foreground claim's first write has
  no beat margin to absorb a miss, and a dropped first write means the claim never appears and
  every background call proceeds straight through the yield the module exists to enforce.
- **[RESOLVED, run #19] `feats.py` FILED EXPECTED 404s IN THE SAME LEDGER BUCKET AS TRANSPORT
  FAILURES.** `silence.note()` was called **before** `e.code` was examined, so a wiki correctly
  answering "no such page" -- which the branch two lines below calls *"a real miss"* -- was
  counted alongside genuine 500s and timeouts, making that site's swallowed-error count
  unreadable. The 404 arm returns exactly what it returned before; only the counter changed.
- **[RESOLVED, run #19] `feats.roll()` COUNTED AN ENTITY THAT RAISED AS NOTHING AT ALL.**
  `done["n"]` incremented and every other counter was skipped -- not even `empty` -- so a
  systemic fault (a bug in `evidence_for`, a host refusing everything) would depress the roll's
  rate with **zero** visible signal and read as "these entities simply had nothing". `errored` is
  now a distinct counter and is printed in the summary. "Nothing found" and "we never got to
  look" are different facts.
- **[RESOLVED, run #19] `feats.mine()` TRUNCATED THE STORED CITATION AT 220 CHARACTERS.** The
  field is not a display string: `magnitude.py:249` copies it verbatim into the permanent
  instrument-tier citation, and `chain.py:217` uses it as a provenance **dedup key**, where a
  shared 220-character prefix collides two different sentences into one. `s` is already bounded
  by the file's own `20 < len(s) < 400` gate, so storing it whole costs at most 400 characters;
  `_show` already truncates separately for display, which is where truncation belongs.
- **[RESOLVED, run #19] THREE `overnight.py` FAILURES THAT LOOKED LIKE CLEAN RESULTS.**
  (i) `preflight()`'s handler returns `(0, False)`, which takes neither of `main()`'s branches --
  a health check that crashed, timed out after its 30 minutes, or could not launch read exactly
  like "checked, nothing wrong"; it now logs `preflight: DID NOT RUN` with the exception first.
  (ii) The keep-warm `gpu_lane` import handler was **the only `except` in the file that recorded
  nothing at all**, and its failure is **sticky for the process lifetime**, so it would silently
  turn keep-warm into the competitor its own docstring forbids. (iii) A crashed
  `coverage_snapshot()` returns a dict holding **only** an `error` key that nothing ever read, so
  `write_status()`'s numeric defaults rendered the cycle as a clean row of zeroes in STATUS.md.
  All three now say what happened. **No behaviour changed in any of the three.**

*Run #12 (2026-08-24 ~15:10 local) moved three items out of Open. Full detail in HANDOFF.md.*

- **[M13 — RESOLVED, run #17] THE STANDING PUBLISHER PUBLISHED THE PUBLIC PAGE INTO A DEAD
  CLAUDE SESSION'S TEMP DIRECTORY.** Export commit **`012dcb2`**.
  **What it was.** `publish.py --push --loop 10` had been syncing, committing and attempting to
  push into
  `C:\Users\imarl\AppData\Local\Temp\claude\C--\660495b7-...\scratchpad\panscriptum-export` —
  a complete second clone of the same GitHub remote, **160 commits ahead of `origin/main` and
  63 behind**. Every cycle logged `synced 14 files, wrote docs/state.json` and then
  `push held: rebase onto origin/main failed (could not apply e33153f...)`. The hold was
  honest and permanent: those 160 commits are a parallel history, so the retry could never
  succeed. **The public page moved only when a maintenance run published**, which is why the
  page's `generated` stamp tracked the maintenance cadence rather than the ten-minute loop.
  **Root cause, both faces.** (1) `SITE` fell back to `os.environ.get("TEMP")`, and the
  supervisor's process tree inherits a Claude session's per-session scratchpad as `TEMP`.
  (2) — found only after fixing (1) — `PANSCRIPTUM_EXPORT` is **itself set to that scratchpad
  path** in the supervisor's inherited environment; nothing in `src/` sets it. Correcting the
  fallback alone left the fault completely in place.
  **The fix.** The guard is on the **resolved** path rather than any one variable:
  `_is_throwaway()` rejects any `temp`/`tmp`/`scratchpad` segment; `export_root()` honours an
  explicit `PANSCRIPTUM_EXPORT` **unless** it names such a directory, falls back to the home
  export, and prints a loud stderr line every cycle when it refuses. The cycle log now names
  its destination.
  **How it was caught.** The page's own stale `generated` stamp, read as the opening
  diagnostic — then the destination-naming log line, which confessed face (2) on the very next
  cycle.
  **Verified live, end to end:** the real export was last written 19:43:11 when the run
  started; after the fix and a publisher bounce it logged
  `publish: REFUSING PANSCRIPTUM_EXPORT=...scratchpad... -- publishing to
  C:\Users\imarl\panscriptum-export`, then `synced 14 files ... -> C:\Users\imarl\panscriptum-export`
  and **`pushed`** at 20:43.
  **STILL OPEN, deliberately:** the stray 26 MB repo remains on disk (no deletions without a
  review cycle) and the poisoned environment variable is still in the running supervisor's
  process tree. Both are questions in NEXT_STEPS §2 A, not fixes.
  Regression: **verify_math §19aj, 12 checks**, all confirmed failing against the pre-fix
  resolver first.

- **[m78 — RESOLVED, run #17] 19 entries stranded in a batch recorded as done.** Export commit
  **`012dcb2`**. `health.py --preflight` returned a **third** FAIL where NEXT_STEPS §1.8 had
  pre-registered exactly two: `state consistency: entries stranded in closed batches: 19`,
  one batch, `Arcanum Worlds (Odyssey of the Dragonlords)#480`. Root cause is the shape
  `reopen_stranded`'s docstring already predicts — a stage interrupted between its work and its
  bookkeeping; `pipeline` was restarted at 19:55 and that source has had an `ingest_doc --mine`
  running against it for ~23 hours. Cleared with the tool built for it
  (`health.py --reopen --go`, `PIPELINE_STATE.json` backed up first, write landed through
  `silence.replace_retry` as the two-writer contract requires). Preflight returned to exactly
  the 2 known FAILs. Nothing deleted, nothing fabricated — a re-opened batch only becomes
  eligible again.

- **[M11 — RESOLVED, run #16] `gpu_lane`: THE FOREGROUND CLAIM WAS NEVER HEARTBEATED — m54's
  fix stopped one variable short.**
  **What it was.** m54 (run #15b) gave a held *slot* a heartbeat thread, because
  `SLOT_LEASE_SECONDS`=900 sat inside calls `config.yaml` permits 1800s. But `lane(priority=True)`
  also writes a **foreground claim** — the record that makes every background caller stand aside
  — and `lane()` started `_heartbeat` only `if slot:`, passing it only the slot path. The claim
  was written once at entry and never refreshed. Its lease, `CLAIM_LEASE_SECONDS`, is **300**,
  a third of the slot lease it had just been fixed alongside.
  **The measurement.** Across the recorded call history (28,979 timed calls), **14 ran longer
  than 300s, the longest 917.3s** — 0.05%, and every one of them a call that had already been
  granted priority precisely because it was expensive. Past 300s `foreground_active()` judged a
  live holder abandoned and swept its claim; `generate.py:155` is the only `priority=True`
  caller in the tree, so the module's rule 2 stopped applying to the exact call it was built for.
  **The subtler half.** `_BEAT_SECONDS` was `SLOT_LEASE_SECONDS / 3` = **300s, identical to
  `CLAIM_LEASE_SECONDS`**. Adding the claim to that beat would have refreshed a 300s lease at the
  moment it expired. It is now `max(5, min(SLOT_LEASE_SECONDS, CLAIM_LEASE_SECONDS) / 3)` = 100s
  — derived from the shortest lease kept, so a shorter lease added later tightens it automatically.
  **The fix.** `_heartbeat` accepts one path or several and refreshes each on the same beat (one
  thread per call, not per lease); `lane()` passes the slot and, for a foreground call, the claim.
  `_touch` needed no change — it rewrites the record it read, so `depth` and `label` survive and
  `foreground()`'s re-entrancy refcount is preserved; its never-resurrect guard already covers
  a claim removed by `fg.__exit__` before a straggling beat lands.
  **Verified.** Live, both directions: pre-fix the claim heartbeat does not move across a call,
  post-fix it does, with `depth`/`label` intact and clean release. **Regression:** verify_math
  §19ad, five checks, each confirmed FAILING against the pre-fix behaviour before landing.
  Export commit: see the run #16 sync.

- **[m75 — RESOLVED, run #16] A DEAD POOL REPORTED "100% ok" AND THE STANDARD HELD.**
  **What it was.** `standards.check()`'s `calls that succeed` computed `errs / max(calls, 1)`.
  The `max(..., 1)` was a div-by-zero guard; on a window with no calls at all it made the
  arithmetic 0 errors over a denominator of 1 — **a green light rendered off a pool that had
  not answered once.** The inverse of the `0.0% (0 of 0)` completeness catastrophe of the same
  day: that one invented a red from an empty file, this invented health. Symmetrically, a single
  failed call rendered "0% ok", and the live window that exposed this held **five calls** and
  printed "20% ok" as a rate.
  **The fix.** Below `MIN_CALLS_TO_JUDGE_RATE` the standard reports **UNMEASURED with its sample
  size** and declines to compute a rate — the idiom `completeness.py` already settled on for
  this exact shape. Reported as a breach, not a quiet hold, on the same principle as the `every
  source is fully catalogued` standard: a standard that cannot see is not one that is satisfied.
  The threshold mirrors **`tuning.MIN_CALLS_TO_JUDGE = 20`** rather than inventing a number. A
  measured rate now carries its denominator. No alarm is doubled: a window too thin to judge has
  already failed `model calls per hour` on volume.
  **Verified.** Reproduced in isolation before fixing (dead pool → `(True, '100% ok')`).
  **Regression:** verify_math §19ai, 8 checks, confirmed failing pre-fix — including the
  positive half, that a genuinely bad rate over a real sample still breaches, so the guard
  cannot silence the standard it protects.

- **[m76 — RESOLVED, run #16] `entity_match.candidates()` returned two different dict shapes.**
  The `EMPTY_NAME` and `NO_POOL` early exits omitted `blocked_by_qualifier`, which the normal
  return path always includes — a `KeyError` waiting for the first caller, on exactly the two
  degenerate inputs real data produces most. Both exits now carry it. Latent only because the
  module still has no production caller; fixed before it acquires one. Verified by execution;
  regression in §19r.

- **[m77 — RESOLVED, run #16] `entity_match`'s docstrings claimed a qualifier must match
  "EXACTLY" and the code never did.** Both the module header and `qualifier_compatible`'s own
  docstring said exact match; the implementation compares `feats_index._norm` forms, so
  `(Earth-2)` and `(Earth 2)` are the same continuity. `verify_math` §19r had the real behaviour
  documented correctly all along, which is what settled which half was wrong. Docstrings
  corrected and the normalising behaviour pinned by a check, so the next reader corrects the
  comment instead of "fixing" the code to match a sentence that was never true. Found by the
  run #16 audit of `entity_match.py`, verified at source.

- **[§3.3 — CLOSED, run #16] `pack_feats`'s `budget` argument is now required.** It defaulted to
  `FEATS_BLOCK_CHARS = 20000`, which is how two separate callers (an audit subagent, and run
  #12) silently got a constant where the derived context-window budget was intended. All callers
  were enumerated repo-wide first — none outside `src/` — the one test that omitted it now passes
  one, and a check asserts the signature so the default cannot return quietly. **Public-signature
  change, flagged.** The constant itself is retained, not deleted; the measurement documented
  above it is worth keeping, and its removal is a question in NEXT_STEPS.

- **[M9 — RESOLVED, run #15b] HARD RULE 0 WAS BEING BROKEN BY `read.priority()`: 668 ENTITIES
  WITH REAL EVIDENCE NEVER ENTERED THE QUEUE.**
  **What it was.** The function built exactly two lists — `have_page` (`own > 0`) and `no_page`
  (`not own and chars >= 2000`) — and returned `woven + no_page`. A row with no own page **and**
  under 2,000 characters belonged to neither and was silently absent from the queue. There was no
  flag, no later pass, and no log line: `queue()` rebuilds `rows` from the evidence cache every
  time and reapplies the same threshold, so the exclusion was permanent and repeatable.
  **The measurement.** Against the live `read_queue_index.json`: **40,884 rows → 36,260
  have_page + 3,956 no_page + 668 DROPPED**, and all 668 held evidence text.
  **Why it is a Rule 0 violation and not a ranking.** `CLAUDE.md` is explicit: "a cap on an
  ordered listing is not a sample, it is a TRUNCATION". This was a value threshold deciding
  MEMBERSHIP of the queue rather than POSITION in it — and the function's own comments say
  *"These are still read -- nothing here is dropped"* and *"the full list is still the full
  list"*. Code and comment had diverged and the comment was believed.
  **The fix.** A third bucket, `thin`, sorted by the same density key and appended last:
  `return woven + no_page + thin`. Ranking is preserved (an interrupted run still gets the
  richest material first); nothing is excluded. The literal `2000` is now `THIN_CHARS`.
  **Pinned by** `verify_math` §19ah, which asserts `priority()` returns every row it was given
  and that thin rows come last.

- **[M10 — RESOLVED, run #15b] THE CHUNK CACHE SERVED ONE ENTITY'S FEATS TO ANOTHER AND THE
  RESULT WAS FILED AS COMPLETE — the only permanent-loss path in `read.py`.**
  **What it was.** `_chunk_key(host, ch)` hashed the passage and the host only, on the explicit
  premise that "two entities attached to the same shared index page read the same passage, and
  there is no reason to pay for it twice -- so the key is the passage, not the pair." True of the
  passage; **false of the answer**. `SYSTEM` opens *"You are reading one page of a fiction wiki to
  collect POWER FEATS for an entity"*, the prompt carries `ENTITY: <name>`, and what returns is
  that entity's feats.
  **The mechanism, and why every existing guard missed it.** On a shared franchise index the
  first entity cached ITS feats under an entity-blind key. The next entity hit that key, got the
  first one's sentences, and `_names(s, name)` — working correctly — rejected them for not naming
  it. They were counted `generic_dropped`. Crucially the chunk was recorded as **answered**, so
  `unanswered` stayed 0, `read_entity`'s `if unanswered: return out` guard never fired, and the
  record was written. The entity is then cached forever as having no feats in a passage that
  describes its feats. **The "deferred, not lost" guarantee cannot catch this**, because nothing
  went unanswered — which is precisely what made it invisible.
  **The fix.** The entity is now part of the key. The sharing it removes was never legitimate;
  the sharing it keeps — the same entity retrying and re-asking only what is still missing, which
  was the documented reason the cache exists — is untouched.
  **The cost, recorded deliberately.** This orphans the **8,194** existing cached answers, which
  are written under the old key and stop being found. **They were NOT deleted**; those passages
  are simply re-asked per entity. That is real GPU cost on a saturated card and it was accepted:
  the cache held answers attributed to the wrong entity, and a smaller-but-wrong library is the
  outcome Hard Rule 0 exists to refuse.
  **Pinned by** `verify_math` §19ah: two entities on the same passage key differently, the same
  entity keys identically, and host/passage still discriminate.

- **[m54 + m55 — RESOLVED, run #15b] `gpu_lane` LOST HELD SLOTS MID-CALL, WHICH IS THE M7
  OVER-SUBSCRIPTION MECHANISM.**
  **m54, and it is the sharper half.** `_touch` — whose entire purpose is refreshing a held
  slot's lease — **was called from nowhere in the tree**, verified by grep across `src/`. A slot's
  heartbeat was written once at acquisition and never again. `config.yaml` sets
  `request_timeout: 1800` against `SLOT_LEASE_SECONDS = 900`, so **every prose call outlived its
  own lease by a factor of two**, was read as abandoned by `_take_slot`, and had its slot deleted
  and handed to a competitor while still running. `MAX_SLOTS` was violated by exactly the longest
  calls — the card over-subscribed precisely when it was busiest.
  **The fix.** A daemon heartbeat thread refreshes the lease every `SLOT_LEASE_SECONDS / 3` for
  as long as the call runs, stopped before release. `_touch` now refuses to write a record that
  is missing or belongs to another pid — necessary, because the beat thread is joined with a
  timeout and a late beat would otherwise **resurrect** a released slot as a lease held by
  nobody.
  **m55.** The six `os.remove` release sites now go through `_remove_retry` (backoff, treats
  "already gone" as released, never raises). A release that silently fails strands a slot for its
  whole lease, and `status()` and competing `_take_slot` calls both open these files.
  **Pinned by** `verify_math` §19ad — refresh, no-resurrect, no-foreign-touch, release, and a
  concurrency test asserting the peak holder count never exceeds `MAX_SLOTS`. **Verified
  non-vacuous**: with the beat disabled the heartbeat provably does not move.

- **[M7 link 1 / §2 B — RESOLVED, run #15b] "CLOUD" NOW MEANS SUCCEEDING, NOT MERELY REACHABLE.**
  **What it was.** `tuning.regime()` returned `"cloud"` on `_answering_buckets() >=
  CLOUD_MIN_BUCKETS` alone, and every job in the kit sizes itself from that one word. Measured:
  regime read `"cloud"` while the live cloud success rate was **4%**, so `_gate()` opened to 16
  and nearly every chunk fell through the ladder onto one card. **1,168 of 1,235 chunks were then
  handed to a GPU that could not serve them and destroyed.** This is the documented root of M7,
  m59, M8 and m66 — a check certifying reachability where the caller needs capacity — and this is
  the site where it was first named.
  **The fix.** `regime()` now requires enough answering buckets **and** a measured success rate
  ≥ `CLOUD_MIN_SUCCESS` (0.35), read from `state/cascade_scratch.db`'s `usage` table — the
  router's own record of what actually happened, and the same source the dashboard's throughput
  panel and the "calls that succeed" standard already use. Deliberately not a fresh probe: a
  probe measures whether a call can be made, and the question here is whether calls are working.
  **Guarded against overreacting**: under `MIN_CALLS_TO_JUDGE` (20) the rate gets no vote, and
  no evidence at all is never treated as a fault.
  **Live effect on landing.** Pool succeeding at **5% over 22 calls** → regime `local`, workers
  **2**, where it previously said `cloud` and opened the gate to **16**.
  **Pinned by** `verify_math` §19ae, including the exact measured condition (8 buckets, 4%).

- **[m62 — RESOLVED, run #15b] The shared metrics ledger could tear mid-line.** Five live
  processes appended to `state/model_metrics.jsonl` with a buffered `open(path, "a")`, which may
  be split into several underlying writes; two interleaving produce a row parsing as neither.
  Measured: 5 corrupt lines, three mid-record fragments (0.019%). Both `_metric` writers now use
  `silence.append_line` — one `os.write` to an `O_APPEND` descriptor. Exposure was low and the
  argument for fixing it is that the consequence is *quiet*: `standards.py` correctly `continue`s
  past unparseable rows, so tearing is invisible from the one place that reads them most — and
  that ledger now decides a standard (`ollama_token_flow`). **Pinned by** §19ag.

- **[m70 — RESOLVED, run #15b] `tuning._ollama_up` probed a hardcoded host.** `def _ollama_up(
  host="http://localhost:11434")`, called with no argument, while `read`, `magnitude`,
  `local_agent`, `overnight`, `standards`, `pick_model`, `pipeline` and `ingest_doc` all read
  `ollama_host` from `config.yaml`. Latent only because config names that same URL. The day the
  host moves, `regime()` would certify a local model at an address nobody calls. Same family as
  M7/m59/M8/m66; closed rather than filed a fifth time.

- **[m71 — RESOLVED, run #15b] `CLOUD_MIN_BUCKETS` had drifted into a second spelling.**
  `pipeline.py`'s pool-first routing tested `_pool_answering() >= 3` as a bare literal while
  `tuning.CLOUD_MIN_BUCKETS` held the same 3 **and** the comment arguing it may need to change.
  Two spellings of one policy; raising it in tuning left the call site on the old bar. Now read
  from tuning, with a fallback so routing never depends on the import.

- **[m72 — RESOLVED, run #15b] Template parameters leaked a brace into the evidence, and the
  evidence is what the fabrication check compares against.** `feats._unwrap_templates` matched
  wikitext's three-brace parameter syntax `{{{name|default}}}` with its two-brace template
  branch, consumed two of the three, scanned to the first `}}`, and left the third closing brace
  as literal text: `{{{1|just a param}}}` → `" just a param }"`, `prose {{{2}}} more` →
  `"prose   } more"`. **Not cosmetic**: this text is both what the reader hands the model and what
  `_norm_q(s) not in _norm_q(ch)` checks answers against, so an injected `}` makes a genuine
  quotation fail and be counted a **fabrication** — the thing this pipeline is most careful
  about. A parameter now renders as its default. Open since the run #5 audit. **Pinned by** §19af,
  including nested `{{{outer|{{{inner|deep}}}}}}`.

- **[m73 — RESOLVED, run #15b] `onomast.coin_well_formed`'s fallback abandoned both invariants at
  once.** After `max_tries` it did a bare `return coin_name(f"{base}|fallback", register)` — no
  `well_formed` check and, worse, no `taken` check. The one path taken when naming is hardest
  could return a malformed name **and** duplicate one already issued, and "shelfmarks are unique"
  is one of the 39 standards: this was the single code path able to break it silently. Filed by
  the run #5 audit. The deterministic walk now continues into a wider salt space (same rule, wider
  range, so determinism is preserved) and genuine exhaustion is recorded via `silence.note`
  rather than quietly duplicating a shelfmark.

- **[m74 — RESOLVED, run #15b] `_chunk_put` staged every write to one shared temp path.**
  `tmp = p + ".tmp"` derived only from the cache key, so two workers answering the same passage
  opened and truncated the same file, each writing over the other mid-dump before both renamed
  it. `silence.replace_retry` made the *rename* safe; nothing made the *write* safe. The staging
  name now carries pid and thread id, leaving the atomic rename as the only shared operation.

- **[m66 — RESOLVED `5400a97`] THE TOKEN-FLOW PROBE ASKED FOR A CONTEXT WINDOW NOBODY SERVES,
  AND PUBLISHED ITS OWN TIMEOUT AS A RED STANDARD — fixed run #15 (2026-08-24 18:25 local).**
  **What it was.** `standards.ollama_token_flow`'s live probe hardcoded `num_ctx: 512`
  (`standards.py:182`) while every real caller in the kit derives the window from `config.yaml`
  (12288). Ollama serves a resident model at ONE context size, so that request was never a
  small generation — it was a runner teardown and rebuild, which `gpu_lane.py:10-13`'s own
  measured table records as **"240 s+, never completed"** against a queue that never drains.
  Whenever the metrics ledger went quiet and the probe was actually reached, it timed out and
  the page went red with *"daemon up, generation TIMED OUT — queue is wedged"* while the 12288
  runner sat resident and served two other clients normally.
  **The measurement.** Same daemon, same machine, same load, minutes apart: **`num_ctx: 512`
  failed on a 180.1s deadline; `num_ctx: 12288` completed in 32.9s.** `ollama ps` showed the
  12288 runner still resident throughout — the rebuild never won. After the fix the function's
  live arm returns `(True, 1.5)` in **1.5 seconds**.
  **The half worth remembering.** The probe carries `keep_alive: -1`. A probe that ever *won*
  its rebuild would have pinned a 512-token runner **forever**, forcing every real 12288 caller
  to evict it back. This was not merely a check that lied; it was a diagnostic that
  manufactured the fault it reported and inflicted it on the jobs it was watching.
  **Pinned by** `verify_math` §19ab, which is structural rather than per-site: it walks every
  module's AST for the request-body shape (`num_ctx` inside an `options` dict) and refuses a
  bare integer literal, so a third site cannot appear quietly.

- **[m67 — RESOLVED `5400a97`] THE SAME PROBE JUDGED "DID TOKENS FLOW" BY PROSE RETURNED, WHICH
  IS THE WRONG QUESTION FOR THE MODEL THIS LIBRARY RUNS — fixed run #15.**
  **What it was.** The success test was `bool(response.strip())`. `qwen3` is a reasoning model:
  its first tokens land in `thinking` and `response` stays empty until the reasoning closes. At
  the probe's `num_predict: 8` a **healthy** generation therefore ends `done_reason: "length"`
  with `response: ""`. Measured 2026-08-24: `eval_count 8`, `thinking "Okay, the user just
  said"`, `response ""` — read by the old predicate as a dead daemon.
  **Why it mattered independently of m66.** Fixing the window alone would have moved the probe
  from *timing out* to *completing and still reporting a fault*. Two defects, one function, and
  only the first was visible from the symptom. Flow is now judged on `eval_count`, which is what
  the function's own docstring says it measures. **Pinned by** `verify_math` §19ab, including a
  check against the exact payload measured.

- **[m68 — RESOLVED `5400a97`] THE DELEGATION LADDER'S OWN SECOND RUNG CARRIED THE SAME DEFECT —
  fixed run #15.**
  **What it was.** `local_agent._chat` hardcoded `"num_ctx": 8192` (`local_agent.py:406`)
  against a daemon serving 12288, so **every local-agent task** named a non-resident window and
  paid for a runner rebuild. This is the documented reason the local-model rung has been
  unreliable in a way that kept getting attributed to the 8B's competence rather than to the
  request. Now derived from `config.yaml`, with the config read behind `silence.note` rather
  than a bare fallback.
  **How it was found.** By grepping the WRITERS after fixing m66 — the inverse of the standing
  lesson, and the second run in a row that "go find the other sites" paid out. Every other live
  call site (`pipeline`, `overnight`'s keep-warm, `generate`, `magnitude`, `read`, `ingest_doc`)
  already derived from config and was verified clean. **Pinned by** `verify_math` §19ab.

- **[m69 — RESOLVED `5400a97`] `tuning.workers()` INVERTED ITS OWN CONTRACT AT ZERO — fixed
  run #15.**
  **What it was.** The docstring promises *"a caller's request is treated as a CEILING, never a
  floor."* The code was `min(requested, n) if requested else n`, so `requested=0` — the single
  request that unambiguously means "run nothing here" — took the falsy branch and received the
  **full profile worker count**. The promised ceiling became a floor of `n` in exactly the case
  where the caller wanted none.
  **Exposure.** Dormant: `chain.py:295`, `magnitude.py:929` and `read.py:1031` all pass a
  positive int, and no caller passes 0 today. Fixed anyway, because a contract that reverses on
  a boundary value is a trap laid for the next caller. `None` still means "no request".
  **How it was found.** The first line-by-line audit of `tuning.py` (run #15's subagent, §4's
  named highest-yield unaudited surface). Six other findings from that audit were **not** acted
  on — they are recorded as questions in `NEXT_STEPS.md`, two of them marked unverified by the
  audit itself. **Pinned by** `verify_math` §19ac, which tests the ceiling at 0, `None`, below
  and above the profile.

- **[m63 — RESOLVED `6fb290d`] DUPLICATE SECTION LABELS IN `verify_math.py`, and there were
  FIVE pairs, not one — fixed run #14 (2026-08-24 17:30 local).**
  **What it was.** A ledger key that does not identify one thing: "§19r failed" was ambiguous
  in exactly the moment someone needs it not to be. **Filed as one pair (19r at lines 2031 and
  2134); the file actually held five** — `19f` (1412/1579), `19m` (1722/1782), `19r`
  (2031/2134), `19s` (2067/2163) and `19t` (2092/2183). Cosmetic in the sense that no check was
  skipped or double-counted, and not cosmetic at all in the sense that four of the five pairs
  were invisible to the ledger that filed the fifth.
  **How it was fixed, and the tie-break that mattered.** The SECOND occurrence of each pair was
  renamed, except where the current `NEXT_STEPS` cites a label as a live pin: it names **§19s**
  (the metrics timestamp) and **§19t** (the M7 gate), which are the *later* sections, so those
  two keep their letters and their older namesakes moved instead. Final: 1579 → **19w**,
  1782 → **19x**, 2067 → **19u**, 2092 → **19v**, 2134 → **19y**. Comment lines only; verified
  by re-running the suite (**473 passed, 0 FAILED**, unchanged) and by `grep ... | uniq -d`
  returning nothing.
  **`BUGS.md` had the same disease** — the Open list was split across THREE `### Major`
  headings (~9, ~204, ~249). Merged into one, pure formatting, no content moved.
- **[m64 — RESOLVED, and now permanently] PUBLISHING WAS STALLED FOR 100 MINUTES BY THE m61 TIMESTAMP BUG, THROUGH A STANDARD
  ADDED 20 MINUTES EARLIER — and the two were written by different authors who never met.**
  Found run #13 when `publish.py --push` hung twice; the export repo's last commit was **15:27**
  and it was **17:06** before one landed. **Not a push/credential problem** (no `git` process was
  ever spawned; the earlier `! [rejected] ... (fetch first)` lines in `publish.log` were stale
  and a plain `git fetch` showed local and origin **0/0 apart**).
  **The chain, each link timed:**
  1. The foreman's `--patch` lane added `standards.ollama_token_flow()` at **16:40** — a good
     standard, with a deliberately cheap path: prove token flow from the LEDGER (any local
     metrics row carrying a `tps` and newer than 900s) and only fall through to a live
     `/api/generate` probe, `timeout=300`, if the ledger is silent.
  2. **`tps` is written by exactly one writer — `pipeline._metric` — and those are precisely the
     rows that carried no `at` field (m61).** So `now - float(r.get("at", 0)) < 900` compared
     against **0**, i.e. 1970, and was False for **all 977** rows that had a `tps`. Measured:
     977 rows with `tps`, **1** with an `at`, and that one written after the m61 fix landed.
  3. The cheap path therefore could NEVER fire, and every call took the live probe — against the
     card M7 had saturated. **`standards.check()` measured 116.9 s**, against the **2.3 s** run
     #1 optimised it to.
  4. `standards.check()` is called by `dashboard.state()`, which is called by `publish.write()`,
     which is why `sync_tree()` and `render_page()` returned in 0.0 s and `write()` never
     returned inside a 240 s budget.
  **RESOLVED as a side effect of fixing m61**, and verified end to end: `ollama_token_flow()`
  now returns `(True, 'ledger')` in **0.0 s**, **`standards.check()` 116.9 s -> 1.4 s**, and
  `publish.py --push` completed and pushed (export `c3369f0`).
  **THE UNBLOCK IS TEMPORARY AND THIS IS THE PART TO CARRY FORWARD.** It rests on ONE fresh
  `tps`+`at` row, written by a short-lived process that happened to import the fixed
  `pipeline.py`. **`pipeline.py` (PID 3056, up since 11:17) is still running the unfixed code and
  writing unstamped rows.** When that single row ages past the 900 s window, if no fixed
  long-running writer has replaced it, the ledger goes silent again, the 300 s live probe
  returns, and **publishing stalls again.** Restarting `pipeline.py` makes it permanent —
  it is keeper-restored within 5 minutes, so it is the cheap half of m56's restart list.
  **Neither party was wrong on its own:** the standard is well designed and its author could not
  see that the field it keys on was unstamped; m61 was a silent omission that had been harmless
  for the ledger's whole life until something finally depended on it.
  **CLOSED run #14 (2026-08-24 17:20 local).** The temporary condition above is now met and
  measured: the keeper restarted `pipeline.py` at **17:12:54**, so the long-running writer is
  finally the fixed one and the ledger carries stamped `tps` rows on its own. `ollama_token_flow()`
  returns **`(True, 'ledger')` in 0.0s** and the export repo is current (`6fb290d`, `d2aeb20`).
  The standing `publish.py --push --loop 10` had also accumulated **120 `! [rejected] ... (fetch
  first)` lines** — that was the DOUBLED publisher the page reported at 17:10 racing itself, not a
  credential or rebase fault: after a plain `git fetch`, local and origin were **0/0 apart**. One
  publisher is running now and its push succeeds.

- **[m61] THE LOCAL HALF OF THE METRICS LEDGER CARRIED NO TIMESTAMP, so every time-windowed
  reading of model behaviour ever taken was silently CLOUD-ONLY — fixed run #13
  (2026-08-24 ~16:35 local), `pipeline.py:364`.**
  **What it was.** `state/model_metrics.jsonl` has two writers. `cascade_bridge._metric`'s row
  always opened with `"at": round(t0, 1)`; `pipeline._metric`'s row — the LOCAL lane, tags
  `entrypass`, `overwatch`, `ask`, `ingest`, `bench:*`, `repro` — never wrote an `at` field at
  all. Every consumer that windows by time filters on `at`, so all **913 local rows** were
  dropped from every such reading while **26,094 cloud rows** passed. Local call VOLUME had
  therefore never been measurable, from the first line of the ledger onward.
  **How it was found, and the near-miss worth recording.** The `m59` monitoring one-liner that
  `NEXT_STEPS` hands to each successive run crashed on this file (`JSONDecodeError`, m62). While
  fixing the reader, the tag histogram came back **100% `cascade:coding`** — which read as "the
  local lane is dead", a dramatic and wrong conclusion. It was the query's own `at` filter
  removing the rows. Re-running without the filter produced the 913. *Same shape as run #12's
  `fits()`-tuple all-clear: the surprising result was an artefact of how it was measured, and
  the measurement was mine.*
  **Consequence for the record:** m59's "1,571 calls/hour", "26/minute", and this run's
  "976/hour at 4.1%" are all **cloud-only figures**. They were never wrong about the cloud; they
  were silently not about the whole system. That mattered directly for M7, whose entire
  mechanism is local traffic those readings could not see.
  **Fix.** `"at": round(t0, 1)` added to pipeline's row (`t0` was already in scope, set just
  before the request). Additive; no signature change; historical rows stay unstamped and are
  simply older than the fix. Verified by exercising the real call path. Pinned by verify_math
  **§19s** (2 checks — both writers must stamp, read from source, because the symptom only
  appears in a file neither writer owns). **`pipeline.py` has not been restarted, so new local
  rows stay unstamped until it is** (same class as m56).

- **[M6] CHAPTER GENERATION REFUSED 100% OF ITS CALLS — fixed 2026-08-24 (owner-directed
  session), 17,370/17,370 refusing -> 22/17,579. Export commit: see the 15:2x sync.**
  **What it was.** At `num_ctx: 6144` every chapter call raised `ContextOverflow`, including a
  call with an EMPTY user prompt: the chapter system prompt (18,112 chars, charged 6,038 tok)
  plus `CHAPTER_RESERVE_TOKENS = 2048` came to 8,086 tokens before a single entry was added.
  Structural, not data-dependent. m46's remedy did not carry over because a chapter genuinely
  needs THE ENTRY TEMPLATE that feats jobs correctly drop.
  **Root cause, and it was TWO things — the second one had been guessed at for two runs.**
  (1) The window was too small for the real blocks. (2) **The scaffolding was being charged at
  the wrong rate.** `CHARS_PER_TOKEN = 3.0` was applied to *everything*, but that constant was
  chosen for entity JSON; the system prompt is ordinary instruction prose. Run #12 said
  explicitly: *"Do not fix this by lowering the reserve or raising `CHARS_PER_TOKEN` until
  someone has measured the real tokenizer ratio."*
  **So it was measured, against the live daemon, once the rung came back.** `prompt_eval_count`
  from `/api/generate` with `num_predict: 1` reports the tokens the runner actually evaluated —
  a real tokenizer reading with no new dependency. On 5,000-char slices sent well inside the
  resident window, minus a calibrated 10-token per-call overhead:

      system_style.txt, voice half      1,194 tokens  ->  4.19 chars/token
      system_style.txt, template half   1,080 tokens  ->  4.63 chars/token

  Instruction prose runs at ~4.2-4.6, not 3.0. The single global constant was overcharging the
  18,112-char system prompt by **1,510 tokens — 25% of a 6144 window — spent on nothing.**
  **The fix, in two parts.** The ratio is now SPLIT: `PROSE_CHARS_PER_TOKEN = 4.0` for the
  system prompt and templates, `CHARS_PER_TOKEN = 3.0` unchanged for entity JSON. Both sit
  BELOW their measured values so the refusal keeps its safety direction, and **the content
  ratio was deliberately left alone because that measurement timed out and remains a guess** —
  raising it too would have been the exact mistake run #12 warned against. Then `num_ctx`
  6144 -> **12288**, chosen from the real distribution rather than a round number: over all
  17,370 rendered blocks the content budget covers median (4,084 chars) and p99 (11,978) with
  headroom, where 8192 would have covered only 52% of calls.
  **Verified by replaying the real code path**, `build_prompt` per `WRITE_CHUNK` group through
  `context_budget.fits`, no sampling: **6144 -> 0 of 17,579 calls fit; 12288 -> 17,557 fit
  (99.87%).** The residue is **m60**, 22 oversized blocks, filed open.
  **Pinned by verify_math §19r** (5 checks), including one that asserts a p99-sized block fits
  the CONFIGURED window and a companion that asserts the same block does NOT fit 6144 — so the
  first check cannot pass for the wrong reason if someone lowers the window later.
  *Lesson: two runs treated `CHARS_PER_TOKEN` as a safety margin to be respected rather than a
  measurement to be taken. It was a placeholder wearing a margin's clothes, and the cost of not
  measuring it was 25% of every window.*

- **[M5] THE STARVED LOCAL RUNG — closed, WITH A CORRECTION TO ITS ROOT CAUSE.** The foreign
  orphan (`semsearch.cli watch`, PID 25188) was killed with the owner's authorisation in the
  13:35 session and it has stayed gone; established connections to the daemon are back to a
  handful. **But the diagnosis that the foreign CLIENT pinned the runner was wrong.** Run #12
  found a fresh runner (`llama-server.exe` started 13:29) resident again at
  `expires_at: 2318-12-04` hours after that pin was released with a `keep_alive: 0` unload, with
  semsearch long dead. The actual source is **machine-level daemon configuration**:
  `OLLAMA_KEEP_ALIVE = -1` is set as a USER environment variable, so *every* load gets an
  effectively infinite keep-alive no matter who issues it, and `OLLAMA_MAX_LOADED_MODELS = 1`
  means exactly one runner may be resident. That pair — not the foreign process — is the
  mechanism behind "a call at a non-resident `num_ctx` never completes": serving a different
  context size requires evicting the only permitted runner, which never expires on its own.
  (`OLLAMA_NUM_PARALLEL = 2`, which is also where `gpu_lane`'s `MAX_SLOTS = 2` should be read
  from rather than hardcoded.) **The num_ctx split could NOT be re-measured this run** — a
  5-arm interleaved probe (6144/4096/6144/8192/6144, identical 6-char prompt) returned nothing
  within 120 s on *every* arm including the three at the resident size, because the card was at
  99% with three of our own jobs on it. **A control that fails tells you nothing about the
  variable**, so M5's mechanism is closed on the env-var evidence, not on a re-run of the probe.
- **[m46] The feats prompt overflow — genuinely closed**, by the 14:23 session's derived budget,
  split system prompt and `assert_fits` refusal. Independently re-verified run #12: at the live
  derived budget of 2,987 chars, Warhammer 40,000 packs 638 blocks and Dragon Ball Z 467, with
  **zero feats lost** in both, max inflation 1.15x and 1.21x of budget.
  **One subagent number did not reproduce and is corrected here:** an audit reported
  `METADATA_INFLATION = 1.20` being breached at a nominal 20,000 budget (claimed median 23,441 /
  max 25,743, +17%/+29%). Re-measured through the real `pack_feats(rows, source_name, budget)`
  signature, Warhammer gives median **20,168** and max **21,993** — which reproduces the code
  comment's own "median 20,464, max 21,993" to the character. The margin IS tight (DBZ reaches
  1.21x at the live budget) but it is not breached as reported. *The audit's error and my own
  first attempt were the same error: passing the budget positionally into `source_name`.*
- **[m52] SUPERSEDED BY M6, NOT CLOSED.** The 14:23 entry closed "m46/m52" as a single item.
  The feats half is closed (m46 above); the chapter half is not, and measuring it at the real
  call granularity — per `WRITE_CHUNK` group rather than per job — moves it from "94% of jobs
  overflow" to **100% of 17,370 calls refuse**. See M6 in Open.

*Owner-directed session 2026-08-24 ~14:30 local. Ordered by the owner: the GPU lane first, then
entity matching, then feats.*

- **[m46/m52] A PROMPT ~1.9x LARGER THAN ITS WINDOW — closed by derivation, a split prompt, and
  a refusal.** Three defences, because one was not enough. (a) **The budget is derived**:
  `FEATS_BLOCK_CHARS = 20000` had no arithmetic relationship to `num_ctx`, so raising the window
  did not widen blocks and lowering it did not protect them. `context_budget.feats_block_budget`
  now computes what fits from the window, the measured scaffolding, a `JOB_OVERHEAD_CHARS` of
  2,000 (measured max 1,536 across 331 real blocks) and a `METADATA_INFLATION` of 1.20 (measured
  ~10%). (b) **Feats jobs stop carrying the chapter-only half of the system prompt**:
  `system_style.txt` is two documents, ground rules and voice (6,963 chars) then THE ENTRY
  TEMPLATE (11,149 chars). A feats chapter writes none of the template, and `feats_prompt.txt`
  explicitly FORBIDS the scoring The Instrument describes — so 11,149 characters of instruction
  were being countermanded by the user prompt. Split on the heading, never a line number.
  (c) **Overflow raises**: `context_budget.assert_fits` refuses to send an over-long prompt,
  naming the numbers, because Ollama truncates rather than refusing and `_covered` only checks
  the entity NAME.
  **Also fixed in passing:** `pack_feats`'s oversized slicer tested the budget AFTER appending,
  so every slice overshot by its last deed — measured, one Black Templars slice reached 5,414
  chars against a 2,987 budget. It now flushes before exceeding; a single deed larger than the
  whole budget still gets its own block and is never clipped.
  **Verified across five large sources: 1,370 blocks, 0 overflowing, 0 deeds lost** (Warhammer
  40,000 7,354/7,354, Dragon Ball Z 5,790/5,790, One Piece 1,464/1,464, Marvel 282/282, DC
  1,453/1,453). Tightest headroom +298 tokens. Pinned by verify_math §19t.
- **[m23] JOB LOGS NO LONGER TRUNCATED ON RESTART.** `overnight.start()` opened every job log
  `"w"`, so each keeper-driven restart destroyed that job's whole history — and the keeper
  restarts a standing job whenever it finds it down, which is the normal path. It cost two
  investigations (run #4's 59-503 Ollama-wedge record, erased minutes after being read; run #7
  again). Now `"a"` plus a dated session separator, deliberately NOT rotation: the dashboard's
  `_tail_match` readers assume one current file per job, and `<job>.N.log` would silently change
  what they read. Adopted from `trading_bot/log.py` and `rent_engine/scripts/weekly.py`.
- **[NEW — the contention m5 left behind] `gpu_lane`: nine processes, one card, an order of
  precedence.** Killing the foreign orphan freed the sockets but Panscriptum's own nine standing
  jobs still stampeded the daemon — measured, a 50 ms call took 0.057 s with a free slot and
  28-35 s without, and calls at a non-resident `num_ctx` never completed at all, which is how
  the library got pinned to one context size. Adapted from `motoko/discord_bot.py:256-298`,
  which recorded the identical problem on this same card ("96-149s with the life loop running vs
  ~10s without"). Motoko's is an `asyncio.Lock`; Panscriptum is nine separate processes, so this
  version arbitrates through file leases: `MAX_SLOTS` (2) concurrent calls, background work
  yields to any live foreground claim, every lease carries a PID and heartbeat, and **every
  failure path proceeds rather than blocks** — a lane that deadlocked nine standing jobs would
  be worse than no lane. Wired into all three call sites: `pipeline.ask` (which carries read,
  feats, magnitude and ingest_doc), `generate.call_ollama` (foreground), `local_agent`.
  Also added a keep-warm ping to `overnight` that holds the runner resident **at the configured
  `num_ctx`** — motoko's idea, plus the context-size half that is ours.
  **A REAL BUG WAS FOUND IN THIS CODE BY ITS OWN TESTS, and it is worth recording**: the first
  version used the POSIX idiom `os.kill(pid, 0)` and checked for `ESRCH`. On Windows a
  nonexistent PID raises **errno 22 / winerror 87**, so every dead process read as ALIVE and no
  lease was ever reclaimed — a ghost slot stranded the card for its full 900-second lease
  (measured 338.5 s in a test that should take under a second). Caught only because the
  concurrency test hung. Now uses `OpenProcess` + `GetExitCodeProcess`. Pinned by §19u.
  *(Citation corrected run #36: this had read §19s and had been dangling since run #14 — the
  GPU-lane check lives in §19u. Pre-existing, not caused by the run #36 §19s/§20x split.)*
- **[NEW] `entity_match`: near-miss name resolution that cannot merge two continuities.** Ranks
  catalogue entries for a name the exact fold missed, and is built around one absolute refusal —
  a parenthetical qualifier must match exactly or be absent from both sides. **Measured against
  the live corpus: 3 records / 240 deeds strand on bound hosts and the matcher recovers ZERO of
  them, which is the correct answer** — all three are `Wally West (New Earth)`, `(Prime Earth)`
  and `Brood`, and every one comes back with a typed reason (2 × `qualifier-conflict`, 1 ×
  `qualifier-missing`) instead of silence. So this recovers no evidence today; what it does is
  make the obvious wrong fix structurally impossible and give the 240 stranded deeds a name.
  Embeddings are supported but OFF: this machine has one model and no embedding model, and
  embedding 85,968 names would re-saturate the card `gpu_lane` was just written to protect.
  Reason codes adopted from `SAM/betting_suite/fetch.py` and `rent_engine/core/property_key.py`.
  Pinned by §19r.
- **[NEW] The local model lane can now VERIFY instead of only inferring.** `local_agent` gained
  `run_check` (a strict allowlist of the repo's own read-only verifiers — verify_math, pyflakes,
  compile, silence) and `find_symbol` (every definition of a name, with its enclosing class and
  an explicit ambiguity warning). The lane could read code and propose an edit but could not test
  anything, so every claim it made was inference from reading — and this project's most repeated
  finding is that a reading is not evidence. `find_symbol` is also the cheap half of **m38**:
  the lane cannot disambiguate a symbol nobody told it was ambiguous, and `main` has **74**
  definitions in `src/`. `propose_patch` keeps every existing gate; nothing new can write.

*Run #10 (2026-08-24 ~12:55 local, export commit = run #10's `publish.py --push` sync). Full
detail in HANDOFF.md's run #10 entry:*

- **[m49] `allsweep`'s "what is actually running" check reported 4 live jobs against a process
  table holding 9 — for four runs straight (#7, #8, #9, #10).** Root cause was NOT the process
  matching, which every run had assumed and which is why it stayed open: the block iterated a
  **hardcoded four-job tuple** `("read.py", "feats.py --roll", "pipeline.py", "overnight.py")`.
  Dashboard, publish, foreman, overwatch and autostart were never asked about. The roster was
  one of THREE partial copies of the same list — `overnight.main()`'s `STANDING` held five and
  `autostart`'s status display held six — none of them agreeing, none of them the source of
  truth. A job missing from a roster does not read as "not listed"; it reads as NOT RUNNING,
  and this is the reading a later run would have trusted to declare a job dead.
  **Fix:** hoisted `STANDING` from inside `overnight.main()` to module scope and added
  `overnight.ALL_JOBS` (the standing set plus `read.py`, `feats.py --roll`, `overnight.py`,
  `autostart.py`) as the single roster; `allsweep` now imports it instead of keeping its own.
  A job at zero is now reported as `NOT RUNNING` rather than silently omitted, and is
  deliberately NOT counted as a bad subsystem — the keeper restores a standing job within five
  minutes and a job between laps is not a fault. **Verified:** allsweep now reports all nine
  standing jobs, exit still `0 subsystem(s) in a bad state`. Pinned by verify_math §19p (4
  checks), including one that fails if a private copy of the job list grows back in `allsweep`.
- **[m50] `manifest_builder`'s `FEATS_BLOCK_CHARS` comment carried a false measurement and a
  false citation.** It claimed feats are "far denser than catalogue entries -- 137 characters
  each". Measured over all 39,862 feats on disk: **207.0 chars each**, and a feat is **0.30x**
  the size of a catalogue entry (683.6 chars), so the density comparison was backwards too. The
  comment's own worked example already refuted the figure — 121,299 / 569 = 213. It also
  credited the input-attention-thinning measurement to `generate.py`, which explicitly
  attributes it to `read.py` (the measurement is at `read.py:80`). **No code changed: the
  conclusion the comment supports was right the whole time** — the weight is per ENTITY, where
  ~7,079 chars of feats stand against 683 for a catalogue entry, 10.4x, exactly the "order of
  magnitude" the last sentence turns on. Corrected in place, with the per-entity arithmetic
  written out so the next reader can check it. The two other figures in the comment (569 feats
  / 121,299 chars for Goku's techniques; 39 entities over 30,000) verified **exact**.
  Also documented there: the budget is a floor, not a ceiling — `cost()` weighs only each
  entity's `feats` list while the emitted block also carries per-entity metadata, so measured
  blocks run ~10% over (Warhammer 40,000: 106 blocks, median 20,464, max 21,993 against a
  nominal 20,000). Still 8,000 clear of the 30,000 line, so the margin holds; it is narrower
  than the number suggests. `pack_feats` itself was audited and is **correct** — 7,354 feats in,
  7,354 emitted, genuine pagination, no cap.

*Run #9 (2026-08-24 12:30 local, export commit = run #9's `publish.py --push` sync). Full detail
in HANDOFF.md's run #9 entry:*

- **[m45] `feats_index._norm`'s docstring promised a fold it does not perform, and the module
  docstring blamed all 17 stranded records on one cause when they have two.** Both corrected in
  place; no code changed, because the code was right both times. (a) `_norm`'s docstring offered
  *"Zangetsu (Zanpakutou spirit)" vs "Zangetsu"* as a pair it folds together. It does not —
  alphanumeric-only folding yields `zangetsuzanpakutouspirit` against `zangetsu`. The STRICT
  behaviour is nonetheless correct and is now defended by three verify_math checks (§19o), because
  loosening it is the obvious fix for the stranded records and is a trap: `Wally West (New Earth)`
  and `Wally West (Prime Earth)` would both fold onto the catalogue's `Wally West (Earth-16)`,
  merging three DC continuities into one cast entry and attaching 177 deeds to the wrong one.
  Measured: 79 of 1,241 records carry a parenthetical and 76 join anyway, so strict costs almost
  nothing. (b) The module docstring, and `NEXT_STEPS` item C, said the 17 strays were all hosts
  missing from `WIKI_HOSTS`. Re-measured: **14 records / 222 feats** are missing hosts, but
  **3 records / 240 feats — 52% of the stranded evidence — sit on hosts that ARE bound**
  (`dc.fandom.com`→DC, `marvel.fandom.com`→Marvel). Binding the four missing hosts will never
  recover those; they are catalogue gaps. `audit()` and `main()` already reported the distinction
  correctly — only the prose was wrong. Root cause of both: a docstring written from the shape of
  the answer rather than from a re-measurement, in code less than an hour old.

*Run #8 (2026-08-24 12:00 local, export commit = run #8's `publish.py --push` sync). Full detail
in HANDOFF.md's run #8 entry:*

- **[m40] A STALE `overwatch.save()` writer silently erased a fresher ledger.** `save()` is a
  whole-file replace, and although this module is the ledger's only writer, it is not its only
  WRITING PROCESS: the standing `--loop` job plus any ad-hoc `verify_open` call a maintenance run
  leaves behind both hold it. Caught in the act — an orphaned diagnostic call launched **09:02**
  by an earlier session was still alive at **11:28** with 2.8 seconds of CPU across 2h26m (i.e.
  blocked on a model reply, not working), holding a 09:02 snapshot, one `return` away from
  replacing a 68-round / 64-finding ledger with it. Measured exposure: **4 findings destroyed**
  (3 open — `feats.roll`, `hostcheck.add`, `cascade_bridge.ask` — plus 1 retired), **1 retirement
  reverted**, and the round counter regressed. The write would have SUCCEEDED, which is why
  nothing would ever have reported it. Root cause: no writer checked whether the file had changed
  under it. Fixed — `load()` stamps the digest it read, `save()` compares and MERGES rather than
  replaces when they differ (union of findings, terminal verdicts win, `seen` keeps the later
  sighting, `rounds` takes the max). Merging is sound only because nothing in the module ever
  deletes a finding, and verify_math §19m now pins that premise too. Falsified against the real
  event before shipping: the pre-fix `save` drops both interloper findings and regresses rounds
  68 → 2; the new one keeps all three findings and both writers' work. §19m, 10 checks.
  The orphan was killed (it did no work anything depended on) and the live loop bounced onto
  the fix; the keeper re-asserted it at 11:37.
  **CONFIRMED WORKING IN THE FIELD — run #11, 2026-08-24 13:00.** Runs #8, #9 and #10 each read
  `OVERWATCH.json` at exactly **68 rounds / 64 findings** and each recorded the merge as a
  possible suspect for the freeze (#10 downgraded it to starvation after reading the log, but
  left it open). It was never frozen: the ledger now reads **69 rounds / 66 findings** — it grew
  in BOTH dimensions, and `state/overwatch.log` shows the round that did it completing via cloud
  fallback (`catalogue_web  2 raw  2 new  105s  (GPU busy; 3 calls to the cloud)`). The round was
  simply in flight across three consecutive reads, each ~25 minutes apart, because a round now
  takes 48-152 s PER MODULE under M5. **The merge is exonerated by observation, not by argument.**
  *Lesson: three runs read the same two numbers and inferred "stuck" from a repeated sample. A
  value that has not changed across N reads is only evidence of a freeze if the reads are spaced
  wider than the thing's natural period — and nobody had measured the period.*
- **[m41] Every `navtree --write` renamed a chunk of the tree — the Registry Terminal's node
  names depended on the PROCESS HASH SEED.** `register_for()` chose a node's naming register with
  `max(set(regs), key=regs.count)`, and `build()` chose a hyperverse's grounding type the same
  way. On a TIE — two registers equally common under one node, the ordinary case on a small
  branch — `max` keeps whichever the **set** yielded first, and string set order is randomized
  per process. The register is an input to `onomast.coin_well_formed`, so a flipped tie renames
  the node. Both the module's own comment ("seeded on the node's own key so the name is stable")
  and `coin_well_formed`'s docstring ("Deterministic: same input, same output") asserted the
  opposite of the behaviour. Measured: two consecutive `--write` runs on identical inputs renamed
  **75 of 734 nodes**; with `PYTHONHASHSEED=0` two separate processes agreed byte for byte, which
  is what identified the cause. NAVTREE.json feeds `build_terminal.py`, `reference.py` and
  `sweep.py`, so these are reader-facing names. Fixed by making the tie-break explicit
  (`key=lambda r: (regs.count(r), r)`); three processes with random seeds now agree exactly.
  The artifact was regenerated once to settle the names — **146 of 734 names changed, structure
  identical (734 nodes, 0 added, 0 removed, no non-name field changed)** — and a second `--write`
  is now a no-op. verify_math §19n, 5 checks. *Found only because a routine staleness check was
  diffed twice instead of once.*
- **[m37 sub-findings, all three verified true and fixed]**
  **`chain.harvest`'s dedup key was `sentence[:120]`** — a truncation that DECIDED WHICH CONTESTS
  EXIST, since wiki prose front-loads its subject and two different sentences about one entity
  routinely share a 120-character prefix; the second was dropped as a duplicate it was not.
  Hard Rule 0. Measured on the live index: **22 distinct contests were being discarded** (12 of
  them Khan Noonien Singh sentences diverging only after char 120), up from 2 when the index was
  smaller — the loss GROWS with the corpus. Now keyed on the full sentence, which can only make
  the dedup finer, never coarser. **`chain.write_result` used a bare `open(OUT,"w")`** on a
  published phase artifact — a torn CHAIN.json after a mid-dump death is indistinguishable from
  a fit that found fewer edges; now write-then-`replace_retry` with the verdict checked.
  **The harvest index discarded `replace_retry`'s boolean** — a denied rename silently costs the
  whole incremental cache, so the next cycle re-parses ~900MB and presents as "the pipeline is
  slow"; now reported. (Same family as m33–m35.)
- **`pick_model.save_config` reported a success it had not had, two ways.** It discarded
  `replace_retry`'s boolean, and its targeted `re.sub` could match nothing — a config with no
  top-level `model:` line wrote itself back byte-identical — while `main()` printed
  "config.yaml updated" unconditionally for both. Now returns a real verdict (`re.subn`, and the
  rename checked), and `main()` exits 1 rather than claiming a model switch that never happened.
- **`local_agent`'s pyflakes gate could not fail.** It tested `r.stdout` for "undefined name"
  only, so a pyflakes that never executed produced empty stdout and was read as a clean pass —
  waving a patch through one of the six gates that stand between a local model and live source.
  The very next gate checks `returncode`, which is what makes this an oversight. Now a code
  outside pyflakes' own (0, 1), or a stderr that looks like the tool failing, is a gate failure.

*Run #7 (2026-08-24 11:45 local). Full detail in HANDOFF.md's run #7 entry:*

- **[m31] `ask_pool_first` accepted any non-None cloud answer, so a cloud-first/local-second
  helper had no second.** The cloud path cannot constrain generation to the schema — it carries
  the schema in the prompt as a REQUEST (`cascade_bridge.py:18`) — so a bucket can return valid
  JSON of the wrong shape, `_extract_json` parses it, and the helper returns it on the sole test
  `got is not None`. Downstream that is indistinguishable from the model judging every entry and
  finding nothing: **four of four logged Marvel entrypass batches read `returned 0/20`** while
  the same batch put to the local model returned 20 valid results in 54s. Now an answer must
  carry the schema's `required` keys AND satisfy an optional caller predicate (`accept=`);
  entrypass supplies one requiring at least one result whose index it actually asked about. A
  failing answer is logged as an unusable shape and the local arm runs. verify_math §19l.
  **Mechanism confirmed by source and log; the incident itself was NOT reproduced** — the pool
  had collapsed to 2 of 36 answering by the time it was probed, below the `>= 3` gate.
- **[m27] The run guard had no implementation in `src/` at all.** Filed as "the heartbeat does
  not check whose record it is refreshing"; the root cause is that the protocol lived only in
  prose in `MAINTENANCE.md`, so every run re-improvised the read-modify-write and there was no
  single place for the ownership check to live. Now `src/runguard.py`: a run may only refresh or
  close a record carrying its own name. `beat()` refuses a foreign record loudly and leaves its
  heartbeat untouched, `release()` refuses to close one, a closed record cannot be reopened by a
  stray heartbeat, and taking over a stale record records whose it was. Falsified against the
  m27 scenario (the pre-fix helper moves the foreign heartbeat; this one does not).
  verify_math §19k.
- **[m28] `overwatch.load()` turned a corrupt ledger into an empty one.** Now copies
  `health.flush()`'s treatment — preserve the wreck as `.corrupt`, say so on stderr, start fresh
  only then — and additionally distinguishes ABSENT (ordinary first run, no `.corrupt` written)
  from DAMAGED, which the single `except` could not. Verified across absent / intact / torn.
- **[m32] `local_agent`'s six-gate discipline was skipped entirely for every non-Python file.**
  `t_propose_patch` set `modname = None` for anything not `.py` and then ran the gates only
  `if modname`, so a patch to `config.yaml`, a prompt file or any `data/*.json` was written and
  reported `applied: True` having passed no parse, lint, import or verify_math check — the exact
  opposite of the module docstring's promise. The same `None` also made the **denylist
  unanswerable for non-Python paths**. Fixed: gates run for every file type with a per-format
  parse check (`ast.parse` on YAML is a false rejection, not a check), verify_math runs
  unconditionally, and `DENYLIST_PATHS` covers non-module files with `config.yaml` in it.
- **[m33] `completeness.land()` claimed a write landed without checking.** Its docstring says
  "Returns True if the file now holds `rows`"; it discarded `replace_retry`'s boolean and
  returned True unconditionally. The two existing guards protect the CONTENT (empty, and the
  SHRINK_FLOOR added the same day); neither checks that the content reached the disk, and this
  file's own docstring names the readers that hold it open — on Windows a held handle is a denied
  rename. A run could measure correctly, report success, exit 0, and leave the stale file.
  Now returns False and names which measurement is actually on disk. verify_math §19m.
- **[m34] `foreman.reprove_pool()` discarded the same boolean and then invalidated the cache
  anyway.** Clearing `CB._PROVEN[0]` forces the next `_alive()` to re-read from disk, so a denied
  rename threw away the fresh in-memory proof AND pointed the router at the stale file, while
  reporting `did=True` — which makes `round_once` `break` and skip the remedy for a full cycle.
  Now reports the failure and leaves the cached proof standing.
- **[m35] `foreman.triage_swallowed()` discarded both of its write verdicts.** Those two writes
  are a MOVE, not two saves: clearing `state/failures.json` when the archive rename was denied
  destroys the counts outright. Now archive-first, clear-only-if-the-archive-landed, with a
  distinct message per failure.
- **[m36] `foreman.attempt_patch`'s size gate measured the wrong quantity.**
  `abs(len(new) - len(old))` is a net line COUNT, while the module docstring sells the gate as
  bounding how much of a function a model rewrite may change and the refusal message said "patch
  changes N lines". Falsified: a rewrite replacing **every line of an 80-line function**, landing
  on 82, scored **2** against a cap of 40 and passed. Now `foreman.lines_changed()` (difflib,
  stdlib) scores it 82 and refuses. One-line edit: old metric 0, new metric 1. verify_math §19m.
- **[Hard Rule 0] `foreman.owner_queue()` truncated the OWNER'S decision document.**
  `for u in urls[:3]` into `FOR_OWNER.md` — the file whose purpose is "everything nobody but the
  owner can decide, in one place". The rule's exact shape aimed at a human decision rather than a
  catalogue: three URLs read, ruled on, and a fourth never known to exist. Uncapped.
- **[m30] Two checks that could not fail — documented, not changed.** `custodes.convene`'s
  `covers_every_reading` and `sevenfold`'s `OVER SPAN` are enforced invariants published as
  checks, true by construction. Changing what they compute is design work, so each now says
  in-source that it states a guarantee, cannot catch a regression, and what would make it live
  again. The informative version of the custodes one is raised as a question in NEXT_STEPS.
- **[genre reaches production] Run #6's uncap was correct and inert.** `data/GENRES.json` has no
  automated writer — only the manual `genre.py --write`, last run 2026-08-20 — and
  `genre.classify_source` has zero runtime callers, unlike `grounding.classify_source` which
  `pipeline.py:1274` calls every phase. Regenerated: **12 of 209 sources changed genre and 11
  changed register** against the stale file (seven from run #6's uncap, five from corpus growth).
  Consumers are `profile.build_all` (genre and register encoded into every world profile) and
  `navtree` (tier naming). The missing-writer question is open in NEXT_STEPS.

*Run #6 (2026-08-24 15:35). Full detail in HANDOFF.md's run #6 entry:*

- **[M4-enforcement] The paid burst cap was never enforced at SELECTION, and ~$1.96 of real money
  went past it.** `paid_ok` only decided whether to PROMOTE `anthropic:paid` into the proven-
  answering set. The bucket is in `_ROUTER.models` unconditionally, is not local, and `_alive()`
  returns True for it — so a closed lane merely ranked it lower and the exhausted-pool fallback
  reached it anyway (free tier at 4% success, so reaching the list's bottom is the normal path).
  `enabled: false` failed identically, and deleting the file was worse still: `_pb is None`
  stopped the counter while the calls continued. Now `widen_candidates()` excludes paid buckets
  unless `paid_lane_open()`, and the counter re-reads from disk under a lock and lands atomically
  (the old snapshot-increment was a lost-update race that drifted the count BELOW true spend —
  the wrong direction on a money file). verify_math §19h, falsified against the pre-fix
  expression. The remaining owner decision stays open as M4.
- **[Hard Rule 0] `genre.classify_source(cap=120000)` was choosing genres off the front of a
  record.** Stored order, not ranked. Marvel: 18,765,902 characters, 0.64% read,
  `post_apocalyptic` (score 240) where the whole record says `mythology` (41,891). Whole-corpus
  diff, 210 records: **seven sources answered differently uncapped** (Marvel, KibblesTasty,
  Bleach, Yorviing's, Dr. Firestorm's, Crash Bandicoot, Digimon). `genre` sets `register` and
  `priors`, so each was dressing its prose in a voice chosen by scrape order. Uncapped; a numeric
  cap is now refused loudly. §19i — whose fixture was rebuilt after the first version proved
  vacuous (it fitted inside the old budget and passed against the buggy code).
- **[Hard Rule 0] `grounding.classify_source(cap=140000)`** — same shape, six sources over the
  cap. No verdict changed, but Marvel reported **153 origin entries instead of 5,012** and score
  95 instead of 930, understating its own attestation 33-fold on the field a reader would use to
  judge it. Uncapped; numeric cap refused.
- **`cleanup.py`'s exclusions were reverted in full — 149 of 149.** `excluded` was written by
  cleanup and read by nothing, while `batch_settled` demanded `all(catalogued)`, so a struck entry
  unsettled its batch, reopened it, and `phase_entrypass` set `catalogued = True` unconditionally.
  Measured: every one of the 149 had already been flipped back. Now an excluded entry settles its
  batch, is never sent to the model, and a result claiming its index is refused; a wholly-struck
  span costs no call. §19j. **See m29 before re-running `cleanup.py --apply`.**
- **`overwatch`'s `_LOCAL_BUSY` was a lifetime accumulator, not a per-round budget** — never reset
  anywhere, while `CLOUD_BUDGET`'s own comment says "in one round". The standing job had been up
  12.8 hours and every module read in its last rounds logged `budget spent`, with no cloud
  fallback at all; completeness "finished" in 6s having done nothing. Reset per round, job bounced,
  keeper restart confirmed by PID and creation timestamp (37188 → 41328).
- **`health.flush()` wrote `state/failures.json` non-atomically** — the exact writer
  `foreman.py:237` names ("EVERY process read-modify-writes it through health.flush()") and the
  one m18 did not fix. A torn write would trip the careful corrupt-read branch above it, which
  preserves the wreck as `.corrupt` and starts fresh — discarding all accumulated failure history.
  Atomic now, and `LEDGER` clears only if the rename landed (a denied replace used to discard the
  counts it had just failed to persist). `failure_samples.json` likewise, which needed it more,
  having no `.corrupt` recovery path.
- **`health.reopen_stranded` broke `PIPELINE_STATE.json`'s single-writer-atomic contract** — raw
  truncating write on the kit's most important state file, from the repair tool that runs
  precisely when a pipeline is live. Atomic now; absent vs. torn distinguished on read; a denied
  write reports and returns `[]` instead of a list that reads as "these were re-opened".
- **`catalogue_web` marked a source catalogued when the record write had been DENIED** — the one
  call site discarding `write_record_catalogue`'s landed verdict. Since work selection is
  `entry_count == 0`, such a source would never be picked up again. Gated. `save_roll` made
  atomic (two unguarded `json.load` readers); `overwatch.save`'s bare `os.replace` →
  `replace_retry`.

*Interactive session 2026-08-24 ~09:40 (owner-directed). Full detail in HANDOFF.md:*

- **COMPLETENESS.json was stuck at `[]` and could not recover.** Run #5 fixed the two bugs that
  emptied it, but neither could refill it: `land()`'s guard only protects a **non-empty** file,
  and `run_completeness_audit` was gated on `_fandom_reachable()`, so while fandom was blocked
  the only thing that could rewrite the file never ran. Emptied by one bug, frozen empty by the
  fix for another. Now **164 honest rows** where there were 2 bytes, and the standard reads
  `UNMEASURED -- 164 row(s), 0 measurable...` instead of a fabricated `0.0% (0 of 0)`.
- **Reachability was measured with a TCP socket, which is not the question.** Measured mid-block:
  the socket to `community.fandom.com` opened **instantly** while `GET marvel.fandom.com/api.php`
  returned nothing after **21.3s** — so `foreman._fandom_reachable`, written to detect exactly
  that outage, answered "reachable" throughout it. Both probes now ask the **API**, via
  `endpoint._get` (a bare `urllib.urlopen` is 403'd by both Wikipedia and Fandom on User-Agent)
  and `endpoint.api_url` (hardcoding `/api.php` called en.wikipedia.org unreachable while curl
  fetched it in 0.16s).
- **The block is PER-TENANT, not farm-wide.** In the same second: `community.fandom.com` 0.2s OK;
  `marvel` / `dc` / `onepiece` each failed at 42s. So `host_reachable()` is keyed per HOST, not
  per domain — asking the farm would have pronounced all 164 sources healthy and then walked each
  into eight 42s failures. One 8s question now replaces ~5.6 min of guaranteed per-source
  failure, and the foreman's all-or-nothing gate is gone because the audit handles a blocked host
  itself. verify_math §19d extended: 4 new checks (a row is still produced, marked, and **not
  probed even once**), and the 3 pre-existing probe checks now hold the gate open so they keep
  testing what they were written for.

*Run #5 (2026-08-24 08:55, export commits `2989776` / `85c5dba` and the closing sync). Full
detail in HANDOFF.md's run #5 entry:*

- **COMPLETENESS.json was wiped to `[]` and a HIGH standard reported `0.0% (0 of 0)` off it for
  two hours.** Two defects in series. (a) `work()` deleted any row it could not fully measure:
  m3's guard required UNANIMOUS probe failure, so 7 transport errors + 1 clean "no such
  category" scored 7 < 8 and dropped the row exactly as before the fix — and under a fandom
  socket-drop that is the normal shape, so all 164 rows vanished. Now any transport failure
  marks the row `unreliable`; genuine absence is `failed == 0 and not sizes`. (b) `main()` wrote
  the empty list over the good file with a raw truncating `open("w")`. New `land()`: tmp +
  `replace_retry`, and it REFUSES to replace a non-empty measurement with an empty one. `--only`
  is now read-only. verify_math §19d pins both halves.
- **`standards.py` reported a fabricated 0% instead of "unmeasured"** — with no denominator the
  arithmetic yields a clean-looking `0.0% (0 of 0)` on a HIGH standard, outranking every real
  fault while accusing the catalogue of holding nothing. Now says `UNMEASURED` and names which
  of the two failures it is, because the repairs point in opposite directions.
- **`read._names` matched by raw substring**, so MetalGarurumon's feats landed on GARURUMON and
  every Daily *Planet* sentence on LOIS LANE (via `lane`). Fixed to start-of-token matching,
  chosen by a whole-corpus diff (39,198 sentences, 1,219 files): plain tokenisation lost 265
  real inflected matches; start-of-token lost 0 and removed 37 suffix collisions. §19f.
- **`assay._interval` read the global WEIGHTS while using the override's denominator** — a
  custom-weighted assay's error bar was normalised against a table it did not come from.
  `custodes.py` builds such a table per Custos. §19e — and §19e itself was rewritten after the
  obvious relational checks were caught passing under the buggy code.
- **[Hard Rule 0] `feats.discover`'s `extra=25`** truncated the ranked evidence-page list for
  exactly the entities with the most written about them; **`scout`'s `[:8]`** truncated proposed
  URLs *before* verification, so the 9th was never tested; **`worldseed`'s `d[:200]`** windowed a
  plain in-memory regex against a 167-character median description. All three uncapped; the
  `extra` parameter now raises rather than capping silently. §19g.
- **`backfill` printed "absent 0" on every non-dry run** — the real path returned no `absent`
  key at all, only a post-cap `missing`, while `main()` prints `res.get("absent", 0)`. The
  completeness column read "nothing missing" precisely while characters were being added.
- **`foreman.kill_duplicate_jobs` could kill the instance it promised to keep** — an unreadable
  `CreationDate` defaulted to `"9" * 14`, sorting as the newest, so a garbled-timestamp process
  was always the one SIGTERMed even when it was the oldest. Now carries `None` and skips the job
  rather than choosing a victim it cannot age.
- **Eleven non-atomic writes to shared artifacts** routed through `silence.replace_retry`:
  `hostcheck` ×7, `scout` ×3, `feats` (WIKI_HOSTS), `identity` (DESIGNATORS), `magnitude`
  (CHARTER_REGRESSION — a standard reads it), `read` (`_save_qcache`'s bare `os.replace`).
  WIKI_HOSTS.json was the one that mattered: three writers, six readers, and a truncating write
  leaves every reader seeing an empty host map, which reads downstream as "no source has a wiki".
- **`read.py:queue()`'s unguarded `json.load` of WIKI_HOSTS** could have ended a multi-hour pass
  on a JSONDecodeError with nothing logged. Self-healing with a note now.
- **NEW: `run_completeness_audit` gated on `_fandom_reachable()`**, as `run_catalogue_gap` beside
  it already was. Ungated it cost ~47 minutes of pure failure per foreman round against a domain
  that has IP-banned this machine once already.
- **[M2] `publish.py --push` failed whenever a second session published concurrently** — five
  `! [rejected] main -> main (fetch first)` failures in one morning, visible only to somebody
  reading `state/publish.log`. Raised by this run as a flagged mechanism change rather than
  edited unilaterally; **fixed by the concurrent session within the hour** (export `fbcbe57`):
  publish now fetch-rebases before pushing, and a conflicting rebase is aborted and reported
  rather than forced. Verified end-to-end — this run's own closing push succeeded and left local
  and `origin/main` in sync.

*Run #4 (2026-08-24 00:45). Full detail in HANDOFF.md's run #4 entry:*

- **The stranded-batch fix is CLOSED end-to-end in production.** Live state first showed the
  gate firing (`failed.entrypass[...#280]` present while the same key was still in
  `done.entrypass` — impossible under the old gate); then, once the pipeline ran on the new code
  with Ollama serving, `Arcanum Worlds … done` at 00:46:40, the failure retired on success,
  **0 uncatalogued entries left in the tail batch**, and `health --preflight` flipped to
  `ok  state consistency` (stranded 5 → 0, preflight 3 problems → 2).
- **[m6] eleven phase artifacts made atomic** via the new `pipeline.land_json()` — the old
  `json.dump(obj, open(path,"w"))` truncates before serialising, so an unencodable value left
  the real file unparseable (reproduced). **And the second half**: `phase_history` treated absent
  and corrupt identically, reported both as "phase 5 has not run", and marked phase 6 **done with
  an empty result** so the corruption was never revisited. Absent and corrupt are now separate,
  corrupt leaves the phase open. Same fix in `phase_shelve`, which would otherwise have shelved
  the whole library tierless and marked itself done. verify_math §19c pins the write contract.
- **[m10] build_terminal escaping** — new JS `esc()` applied to every catalogue-derived
  interpolation (headings, endonym, roster, 4 SVG titles, `data-k`, 7 SVG text renders), and the
  `NAVTREE.json` splice now neutralises `<` as `<`, killing `</script>` / `<script` / `<!--`.
  Live-verified: 734 nodes still parse, and a name carrying `<img onerror=…>` renders as literal
  text with 0 injected nodes.
- **[m14] topicless entries** — a `topic` failing its enum check left no key while
  `catalogued=True` blocked revisiting, silently dropping the entry from `worldseed` and `weave`
  forever. Now an explicit `"unclassified"` sentinel plus `topic_rejected`, matching the
  `magnitude`/`scale_note` idiom. **Prophylactic: 0 of 55,653 catalogued entries are currently
  affected.**
- **[m15] `endpoint.fetch_raw` filed refusals as absences** — 403/429/500 were indistinguishable
  from 404 to the caller. Signature unchanged; the ledger now splits `fetch_raw-absent` from
  `fetch_raw-refused-<code>`, where the counts are what tell a block from a missing page.
- **[m20] dead loop deleted** with owner sign-off. Its comment is kept — the decision it records
  (counting instances belongs to the reconcile tier) is still true.
- **[m7] was already fixed; the entry was stale.** `handbuilt.py` writes through
  `tmp` + `silence.replace_retry` with a landed check.
- **NEW: `the local model has a live runner` standard added** (high, machine, OWNER lane) —
  `/api/ps` naming a resident model with no `llama-server.exe` process is a flat contradiction
  and was the exact shape of run #3b's 31-minute invisible outage. Fires on a simulated wedge,
  silent when it cannot tell, TTL-cached at 120s. No REMEDIES entry by design: restarting a
  service is not automation this pass will switch on unasked.

*Run #3b (2026-08-24 00:00, continuation pass). Full detail in HANDOFF.md's run #3b entry:*

- **Ollama was hard down and self-sustainingly wedged** — queue saturated (`maximum pending
  requests exceeded`) while `/api/ps` reported a resident model with **no `llama-server.exe`
  runner process in existence**, so nothing drained the queue and every call, including each
  attempt to load a model, failed instantly. The phase runner logged 59 unbroken 503s in 31
  minutes doing zero work. Fixed by restarting the daemon; a real runner now holds 8.5 GB VRAM
  and the 503 loop stopped dead. **This corrects run #3's diagnosis of "GPU contention"** — a
  wedge, not contention, and it would never have cleared by waiting.
- **[m18] `foreman.py`'s three shared-state writes** (`POOL_PROOF.json`, `FOREMAN.json`,
  `failures_archive.json` + the `failures.json` reset) now use `tmp` + `silence.replace_retry`,
  the pattern `_retire()` in the same file already used. Readers confirmed live in all three
  cases; the `failures.json` reset was the one that could lose a concurrent `health.flush()`.
- **[m19] `standards.report()` sorted work orders alphabetically** (`high < low < medium`, so
  every MEDIUM printed below every LOW). Now uses the rank dict `work_orders()` already defines.
  Verified live: HIGH, HIGH, MEDIUM×5, LOW, LOW.
- **[m21] `kill_duplicate_jobs` was registered as a bare lambda**, so it logged itself as
  `<lambda>` in the operational log. Unwrapped.
- **[m22] `catalog.py`'s docstring advertised a `PANSCRIPTUM://…` address form the code has
  never implemented.** Replaced with real `SpineCode/Chapter[#PageRange]` examples, both verified
  to answer.

*Run #3 (2026-08-23 23:06, export commit `cc42d0c`). Root causes one line each — full detail in
HANDOFF.md's run #3 entry:*

- **Doc-ingested entries stranded permanently by the entrypass resume gate** — the resume key
  `source#start` names a span `entries[start:start+B]` that GROWS when `ingest_doc` appends
  through `write_record_catalogue`, so the tail batch widened under a key already in
  `done_keys` (Arcanum Worlds: 292 → 297 entries, 5 never judged). Gate now reads the span, not
  the ledger (`pipeline.batch_settled`); verify_math §18d pins it.
- **`ingest_doc.mine()` advanced its resume cursor on a denied write** — `write_record_catalogue`'s
  landed-flag was discarded, so entities never written were skipped forever and `known` had
  already absorbed their names. Denied write now rewinds `known` and stops without advancing;
  state file also made atomic.
- **[m3] `completeness.py` dropped any source whose every category probe failed** — `work()`
  returned `None`, deleting the row from `COMPLETENESS.json`, where absence reads as "no wiki
  presence". New `category_size_probe()` returns `(n, error)`; all-probes-failed lands in
  `unreliable`. `category_size()` unchanged for other callers.
- **[m4] `wiki_source.page_text()` abandoned a page after one transient failure** — `return ""`
  instead of `continue` on a section-0 exception skipped the independent sections 1 and 2. High
  volume: 1,700–3,200 URLErrors per foreman round at this site.
- **[m5] duplicate `silence.note()` label `wiki_source.py:278`** across two unrelated sites —
  split into content labels; `:301` likewise.
- **[m8] Hard Rule 0: "Shelved here" roster sliced to 8** (node 6.6.6 hid 30 of 38) — uncapped,
  bounded by scroll rather than by a "+N more" that would still leave 30 names unreachable.
- **[m9] "contains" row undercounted** — `a||b||c` returns the first non-zero, so 6.6.6 showed
  7 instead of 45; 37 nodes affected. Now sums. m8/m9 live-verified in the browser.
- **[m11] `navtree.sources_under()` false-matched on a digit prefix** — `key.startswith(path)`
  lacked the `.` boundary its sibling arm has; `0.1.2` counted as above `0.1.20`.
- **[m17] `weave_index.designations()` cached forever** — now keyed on the same directory
  signature as `load_records()` (shared `_records_sig()`); explicitly-passed record lists are
  no longer cached at all, having no signature to key on.
- **`address.spine_code_for()` shelved two sources into DC Comics** — the index's two-letter
  `"DC"` matched raw letters with spaces stripped (`swor-d-c-oast`), so `Sword Coast
  Adventurer's Guide` and `Who Framed Roger Rabbit (…)` both returned II.D.2, and matching
  *wrong* kept them out of the unassigned report that would have caught it. Containment now
  runs on whole words, with letter-equality kept as its own tier for spacing variants
  (`Soulcalibur`/`Soul Calibur`). No volumes were mis-shelved; nothing to regenerate.
- **`manifest_builder.load_record()` missed truncated record slugs** — tested only `target in
  filename`, so a 304-entry catalogued record reported as "no matching record file". Reverse
  arm is prefix-anchored, candidates ranked by closeness.
- **`foreman._checks_pass` kept patches that broke a round number of checks** — `"0 FAILED" not
  in stdout` is satisfied by `"10 FAILED"`, `"20 FAILED"`, `"100 FAILED"`. Now parses the count
  numerically and fails closed on an unreadable result line.
- **`standards.py`'s stall detector could never fire, for any job** — the watch stamp was
  re-written every pass, so "how long silent" measured checker cadence; and jobs were derived
  from log filenames (`read_auto.py` has never existed), hiding the three live jobs while
  matching stale legacy logs as alive. Stamp now carried forward (`standards.job_stamp`); jobs
  taken from the new `lognames.OWNER` map, which `foreman.kill_stalled_job` also now uses.
  verify_math §19b pins both. **Its AUTO remedy is destructive and was previously inert — see
  the flagged item at the top of HANDOFF.md run #3.**

*Run #2 (2026-08-23 late, export commit pending as of this write). Root causes one line each —
full detail in HANDOFF.md's run #2 entry:*

- **`cascade_bridge._bury()` raised `UnboundLocalError` on every call, never benching a
  provider** — a dead `if _DEAD is None: _DEAD = {}` guard made `_DEAD` local-by-assignment for
  the whole function; removed, mutate the module-level dict directly.
- **Phase-1/phase-2 band gates laundered a fabricated Assay decimal into a clean band**
  (`re.match(...)\b` matches a `.`) — replaced with `pipeline.clean_band()` (full-match) at
  acceptance, `pipeline.ceiling_band()` (still lenient) at the clamp.
- **`write_record`/`write_record_catalogue` marked a unit done even when the write was denied**
  — both now return whether the rename landed (`pipeline._landed`); both call sites gate on it.
- **`handbuilt.py` crashed on its own `moth_number`'s Fraktur A before ever writing its
  artifact** (cp1252 console) — write now happens before the report loop; console reconfigures
  to UTF-8 after.
- **`rigor.bradley_terry()`'s `undefeated`/`winless` always empty once a prior was set** — the
  symmetric prior was folded into `W` before those two lists were read from it; now computed
  from a pre-prior copy.
- **`rigor.mathematical_resonance()`'s returned `load_bearing` field capped at 8** (Hard Rule 0)
  — uncapped; console print still slices for display only.
- **`render.children_of()`'s child-tier gate asserted a schema (`SF.TIERS`) instead of reading
  the actual tree** — changed to `child_tier is None`; the existing per-entry check does the
  honest work. (No behavior change today — SEVENFOLD.json doesn't chart past `universe` yet —
  but the old form would have silently stayed empty once it does.)
- **stale `silence.note()` label** `derivation.py:490` said `:488` — renamed to a content label.
- **disk pressure (BUGS M2)** — resolved itself between runs (~5 GB -> 135 GB free); no fix
  needed, moving straight to paper trail.

*Run #1 (2026-08-23, commits fc390a9…b16f631). Root causes one line each:*

- **ingest_doc used `write_record` (disk-wins merge) and its first 14 finds were discarded** —
  wrong side of the two-writer contract; → `write_record_catalogue`, cursor reset, both merge
  directions pinned by verify_math §18c (b16f631).
- **`os.replace` PermissionError killed an assay worker mid-batch** — Windows denies rename
  while a reader holds the target; → `silence.replace_retry` shared helper on every
  reader-raced state file (fc390a9).
- **standards' floors self-check blind to a dead floor** — substring match defeated by a
  comment mention and a prefix collision (`MAX_UNANSWERED[_RECORDS]`); → word-bounded,
  comment-stripped matcher; dead floor deleted (fc390a9).
- **Catalogue tools wrote records raw** (truncating, non-atomic, racing the pipeline) — →
  routed through the new catalogue-side merge writer (fc390a9).
- **feats/read evidence caches: truncated file = permanent silent entity loss** — unguarded
  json.load of a cache killed mid-write; → atomic writes + self-healing reads (fc390a9).
- **`_WIDEN_RR` rotation cursor raced by worker threads** — re-pinned the pool to one bucket;
  → locked (fc390a9).
- **`foreman._retire` truncating write on overwatch's ledger** — → atomic (fc390a9).
- **`restart_reader` never restarted anything** (both branches returned without acting) and
  **both foreman process-killers filtered `python.exe` only** (jobs run under pythonw) — →
  reader bounce implemented; filters widened (fc390a9).
- **standings jobs stayed down for hours after a mid-cycle death** — the cycle only re-asserts
  at its top, then blocks in run/join; → keeper thread re-asserts every 5 min (d4745fa).
- **`silence.py --instrument` resurrected the 5,672-row probe-noise ledger class** — the
  rewriter can't distinguish deliberate silence; → `silence-exempt` string markers honoured by
  both audit and instrumenter (fc390a9).
- **Epoch-mandate bypass through the split retry** (morning); **split-gate accepted fabricated
  wrappers**; **entry bands could exceed their source's ceiling** (Starkiller Base M5 in M4)
  — all gated/clamped; reconcile check added (earlier commits, same day).
- **~146 PowerShell spawns per standards.check** (dashboard polls it at 5s) — one shared
  enumeration, 3s TTL, invalidated on launch; check now 2.3s (d4745fa).
- **chain.harvest re-parsed 56k files/900MB per cycle** — incremental mtime index; 3.1s warm
  (fc390a9). **weave_index.load_records re-parsed 63MB per dashboard poll** — signature cache
  (fc390a9). **13MB sweep parsed twice per batch** — once (fc390a9).
