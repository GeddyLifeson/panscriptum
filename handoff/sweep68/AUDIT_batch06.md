# AUDIT batch 06 -- sweep68 (run68)

## Scope

Read-only. Every line of each module was read with the Read tool in sequential chunks. No subagents.

| module | lines | chunks read |
|---|---|---|
| src/standards.py | 2,609 | 1-650, 650-1300, 1300-1950, 1950-2609 |
| src/rigor.py | 1,155 | 1-600, 600-1155 |
| src/thread_integrity.py | 847 | 1-430, 430-847 |
| src/endpoint.py | 658 | 1-340, 340-658 |
| src/zfighters.py | 536 | whole |
| src/catalogue_models.py | 409 | whole |
| src/descending_ladder.py | 362 | whole |
| src/physics.py | 313 | whole |

Nothing under src/, data/, state/, output/, prompts/ or config.yaml was edited. No `main()`, drill, verify_math,
pipeline, generate, publish or mutate was run, and `standards.check()` was never called (it fires a live GPU
generation, a tasklist, a Get-CimInstance and a TCP connect). Probes live in `%TEMP%/aud68_06` (probe1-4.py).
probe3 pointed `weave_index.RECORDS` at a temp dir; probe4 pointed `endpoint.CACHE` at a temp dir.

**One disclosed side effect:** probe3 loaded a deliberately torn record through `weave_index.load_records()`, whose
`silence.note("weave_index.py:load_records-unreadable")` is not redirected by that module's path variable, so
`state/failures.json` took one +1 on that class. Nothing else was touched.

## Prior-audit cross-check (handoff/sweep67)

- **b07 F1 (`every module imports` tautology)**: FIXED. `dashboard._watch()` now fills `broken` from ALLSWEEP's import
  rows and, when ALLSWEEP.json is unreadable, from a marker row (dashboard.py:374-378). standards.py:1226 is now live.
- **b07 F2 (`phases implemented` green by absence)**: FIXED (`phases_standard`, 714-731, UNMEASURED when no list).
- **b07 F6 (check() twice)**: FIXED (main builds rows once, 2582-2605).
- **b07 F8 (shelfmark uniqueness counted addresses only)**: FIXED (`shelfmarks_standard` counts both, empty is UNMEASURED).
- **b07 Q1 (SHELF_RANKS.json absent silently exempt, 2045-2046)**: STANDS as a question, unchanged.
- **b07 Q6 (an unstattable log turns the advancing standard red even for a job that is not running, 1816-1829)**: STANDS,
  unchanged. All six `LN.OWNER` logs exist today, so it is not red now.
- **b07 Q8 (`age_h` tested at 99, printed at 0, 1190-1191)**: STANDS, cosmetic.
- **b07 Q4 (hand-run writers zfighters / catalogue_models / endpoint.register have no halt interlock)**: STANDS.
  thread_integrity gained `_assert_not_halted` (530-551) and only its floor write asks it; the other three still write
  `data/` with no halt read (grep `assert_clear|_assert_not_halted` over the three: no hits).
- **b07 zfighters Q5a (Tien's `continuity` quotes Chiaotzu's line)**: STANDS, zfighters.py:324-325. See Q3 below.
- **b07 catalogue_models Q7 (raw `~/cascade/config.json`, Cascade DEFAULT_CONFIG providers/models invisible)**: STANDS
  (catalogue_models.py:241-249). `cascade.config.load()` merges DEFAULT_CONFIG providers, this does not.
- **b06 endpoint F1 (`html_text` 8 entities, double-decodes `&amp;`)**: FIXED (endpoint.py:475-476, `html.unescape`).
- **b06 thread_integrity F4 (malformed thread rows skipped, corrupt graph verifies clean)**: FIXED (196-215; a bad T1/T2
  entry is now an `unresolvable` row, a list-typed T2 raises `ThreadGraphUnreadable`).
- **b06 endpoint Q2 (`detect(force=True)` can demote a live host to DEAD for 24 h)**: STANDS (223-273, no guard).
- **b06 endpoint Q3 (`fetch_html` drops pages of <= 400 chars)**: STANDS (498-506), noted in the ledger, still a floor.
- **b05 rigor F5 (`bradley_terry` accepted self-contests and bad counts)**: FIXED (481-491).
- **b05/b06 rigor `adjudication_beta` charging one law for zero**: FIXED (688-692). New sibling gaps in F8 below.
- **b11 physics F7 (docstring "about a third")**: FIXED (line 86-88 now says a fifth, 19 percent; measured 0.808).
- **b10 descending_ladder Q5 (`is_descent` False for `from_m=None`, line 309)**: STANDS, unchanged (module is held).
- **b05 catalogue_models four-way outcome, secrets merge, `enabled:false`**: re-verified, correct. Cascade itself lets a
  key still in config.json win over secrets.json (config.py:374-398), which is what `_merge_keys` does, so the code
  agrees with Cascade even though its docstring lists the precedence in a different order.

## Findings

### F1 (MEDIUM, VERIFIED) standards.py:1848 -- a blind process-table probe reads as "no job is running", so `every running job is advancing` holds over zero jobs
Quote: `alive = bool(_ON.running(owner))`. Since order 1d556b6ef535, `overnight.running()` returns `None` when
`_proc_lines()` could not read the process table (spawn raised, non-zero rc, or empty stdout: overnight.py:111-161,
182-221). `bool(None)` is `False`, so the job takes `if not alive: continue` at :1857 on the same path as a job that has
finished. The `except` right above it (:1849-1856) was written for exactly this ("A PROBE THAT THREW IS NOT A JOB THAT IS
DOWN") and does not see the None. Scenario: Get-CimInstance times out (the code's own comments call that "ordinary" on
this machine) while the reader and roll are wedged: every one of the six `LN.OWNER` jobs is skipped, `watched == 0`,
`stalled == []`, `unmeasurable == []`, and the HIGH row reads `0 running, all advancing`, MET. The stall detector is silent
in the one state where it cannot see.
Repro (`probe2.py`, `_proc_lines` stubbed to None): `running(...)` returns None for all six owners, `bool()` False for
all six, and the standards.py:1846-1859 logic yields `holds = True | observed = 0 running, all advancing`.
Fix: `_r = _ON.running(owner); if _r is None: unmeasurable.append("%s (process table unreadable)" % job); continue`.
(The sibling roster at :2279-2282 uses `not v`, so a blind probe there names all five jobs "down": a false alarm rather
than a false all-clear, so the safe direction.)

### F2 (MEDIUM-LOW, VERIFIED by logic) standards.py:2303-2317 -- the duplicate-job probe never checks its return code or an empty listing
Quote: `capture_output=True, ... ).stdout or ""`. Only an exception (the 60 s timeout) reaches the `except`/`_dropped` arm.
A Get-CimInstance that exits non-zero, or that returns nothing (the same blind states overnight.py:156 names), gives
`lines == []`, `dupes == []` and `one instance of each job` HOLDS with observed `one each`. The caller is itself a python
process matching `%python%`, so a working probe cannot return empty: an empty listing is proof the probe was blind.
overnight.py fixed this shape for its own copy of the probe ("AN EMPTY LISTING IS ALSO UNKNOWN"); this second, independent
copy of the same enumeration did not get the fix. Fix: treat `returncode != 0` or `not lines` as UNMEASURED
(`_dropped.append("duplicates")`). Not run against a live blind probe; the empty-listing arithmetic is the whole defect.

### F3 (MEDIUM, VERIFIED) thread_integrity.py:322-332 -- one unreadable record file manufactures DANGLING and SUPERVISOR refusals against healthy sources
Quote: `for rec in WI.load_records():`. Since sweep67 F3, `weave_index.load_records()` returns the readable subset and
reports what it skipped through `WI.LAST_UNREADABLE` (weave_index.py:366). `load_entities()` never reads it (no caller
outside weave_index does). A record that is torn or held by Norton during the read is therefore absent from `ents`, and
`classify()` (:396-407) calls every pair that touches that source DANGLING, because every shared key is "gone".
`main()` then prints `THREAD INTEGRITY FAILED`, exits 1, and `_escalate_dangling` (:487-527) refuses **both ends of every
such pair at SUPERVISOR**, so a source whose record was fine has its area closed for a read fault in a neighbour.
Repro (`probe3.py`): three sources sharing three entities; healthy -> `{IMPLIED-UNRECORDED: 3}`; SrcB's file truncated ->
`ents` loses SrcB, `WI.LAST_UNREADABLE == ['SrcB.json']`, classify -> `{DANGLING: 2, IMPLIED-UNRECORDED: 1}`, and the
escalations are `SUPERVISOR THREAD_DANGLING` for SrcA, SrcB and SrcC. It fails closed, but on the wrong sources for the
wrong reason ("escalating everything is the same failure as escalating nothing"). Fix: in `load_entities` (or `main`), if
`WI.LAST_UNREADABLE` is non-empty, print it and return 1 before classifying (or exclude those sources from DANGLING and
report them as unmeasured), and record at JANITOR rather than SUPERVISOR.

### F4 (LOW) standards.py:1793-1795 -- a corrupt `job_progress.json` is never healed, so the advancing standard is dropped for good
Quote: `prev = json.load(f)`. The load sits inside the standard's single `try`; a torn or non-dict file raises, the block
jumps to `_dropped.append("job-advance")`, and the only `write_json(JOB_WATCH, cur)` (:1889) is after the raise, so the file
is never rewritten and every later `check()` drops the standard again until a person deletes it. `READ_WATCH` (:1114-1120)
handles the same fault correctly (unreadable -> `None` -> re-stamp). It is fail-closed (the aggregate row goes red), so LOW.
Not run (needs `check()`); by inspection of the control flow.

### F5 (LOW) standards.py:1768-1771 -- a missing or empty `data/records` reads as "fresh"
Quote: `default=0.0`. With no record globbing, `newest_rec = 0.0`, `lag_h = (0 - sweep_m)/3600` is hugely negative,
`lag_h <= 1.0` is true and the HIGH row `the character sweep is newer than the catalogue` reads `fresh`. Every sibling
standard that reads the records store raises on a missing directory (`unanswered-records`, :1350-1351). Only reachable if
the records directory is gone, which would trip other alarms, hence LOW. Fix: `raise FileNotFoundError` when the glob is empty.

### F6 (LOW) standards.py:1659, 1666 -- `files that parse` and `verifiers all run` default to "nothing wrong" on missing keys
`(sweep.get("estate") or {}).get("artifacts") or {}).get("bad") or []` and `sweep.get("verifiers") or []`. An ALLSWEEP.json that
parses but lacks those blocks reads 0 corrupt files and 0 crashed verifiers, MET. Today the file always carries both
(`keys: at, imports, verifiers, lint, reconcile, estate, ...`; verifiers 11 rows), so this is a structural-absence gap only,
the same class as sweep67 F1/F2. Fix: `if "verifiers" not in sweep` -> raise into `_dropped`.

### F7 (LOW, VERIFIED) descending_ladder.py:206-219, 284-316, 348-362 -- NaN passes every guard and reads as a lawful, free, "Continental" trajectory
`rung_for_length(nan)` -> `(0, 'Continental')`; `shrink_report(70, 1.7, nan)` and `shrink_report(nan, 1.7, 1e-10)` ->
`mass_conserved_is_lawful=True, objections=[], input_error=None`; `transgression_bits(nan, 1e-10)` and `(70, nan)` -> `0.0`.
Every guard is `<= 0`, which NaN fails. This is the exact defect physics.py fixed with `not x > 0.0` (order 7909342fefa4), and
the docstrings claim the "priced at zero for garbage" and "silent mislabel" classes are closed. Module is held and unwired,
so nothing reads it today. Fix: write the guards as `not metres > 0.0` and `not (to_m > 0.0 and mass_kg > 0.0)`.

### F8 (LOW, VERIFIED) rigor.py:661-706, 713-742, 782-816 -- three functions accept inputs that produce a plausible wrong number
- `adjudication_beta(1, 0, -3)` -> `beta_floor_bits = -20.42` (a negative description length; `n_parameters` and
  `param_precision_bits` are not validated); `n_regimes` <= 0 is clamped silently to 1 (line 694).
- `lognormal_product(f, {("a","b"): -1.5})` -> `sigma_dex = 0.0`: an out-of-range correlation makes the variance negative and
  `max(var, 0.0)` (line 734) collapses the interval to a point, the opposite of what the function exists to report. Listing both
  `("a","b")` and `("b","a")` double-counts the covariance (sd 2.0 vs 1.73 for one).
- `ceiling_confidence(10, -5)` -> `p_true_max_seen_if_random = -0.5`.
All are callable with attacker-free, ordinary mistakes, and the module's stated doctrine (`_validate_reciprocal_matrix`,
`RigorIntegrityError`) is to raise. Live callers pass valid values, so LOW.

### F9 (LOW, VERIFIED by interleaving) endpoint.py:170-179 -- `_save` can erase a fresher in-memory verdict for a host that was already dirty
`_DIRTY.difference_update(mine)` runs after the swap and the fold-back loop then sets `_MEM[h] = disk[h]` for every host no
longer dirty. If another thread finishes a fresher probe of the SAME host while the save is in flight, `_DIRTY.add(h)` (line
271) is a no-op because `h` is already a member, so the fresher verdict is un-dirtied and overwritten by the one that just landed.
Repro (`probe4.py`, `replace_if_unchanged` wrapped to run the second probe's `_MEM`/`_DIRTY` update mid-save): after the save
`_MEM['h.example']` is the older `dead` verdict, `h.example` is not dirty, and disk holds `dead`. A host that was just found live can
read DEAD for the 24 h TTL. Needs two threads probing one host inside one save; the comment at :173-176 promises the opposite.
Fix: snapshot `(host, id(verdict))` in `mine` and only clear `_DIRTY` for hosts whose `_MEM` entry is still that object.

### F10 (LOW) standards.py:1149-1152, 1167-1170, 1416-1420 -- comments say read.py is "legitimately DOWN between supervisor laps"; it is now STANDING
Those blocks justify routing an absent corpus-read / page-roll job to `_dropped` instead of a red row that would dispatch
`restart_reader`. `overnight.STANDING` has carried `read.py --run --loop` since 2026-09-08 (overnight.py:1100-1131, owner ruling
question 14), and the keeper restarts it in 300 s. The comments now describe a state the code base deliberately ended. The
behaviour (dropped, aggregate red) is still fail-closed; what is stale is the reasoning, and with it the answer to "should an
absent reader raise the restart remedy". UNVERIFIED that a dispatch gap results. Owner call, see Q1.

### F11 (LOW, latent) standards.py:293, 2085 -- the token-flow probe and the /api/ps read restate what the docstrings forbid
`int(cfg.get("num_ctx", 6144))` and `cfg.get("model")` (no default, so `null`) sit two paragraphs under a docstring saying a probe
must never carry a window nobody serves and that `cfg_num_ctx()` never defaults. A config with no `num_ctx` sends a 6144 window
with `keep_alive: -1`, which is the runner-rebuild-and-pin failure that docstring describes. Separately `/api/ps` is fetched from a
literal `http://localhost:11434` (line 2085) while the probe uses `cfg["ollama_host"]`. config.yaml has all three keys today
(lines 4, 37, 82), so nothing is wrong now.

### F12 (LOW, VERIFIED numerically) descending_ladder.py:224-238, 305 -- non-relativistic confinement energy is used where p exceeds mc
`E = p^2/2m` is only valid for p << mc. For a proton confined to the Planck length, `compton_confinement_energy` returns 3.18e27 J
and `shrink_report` prints "confinement energy ... exceeds the Planck energy"; the relativistic value (p*c) is 9.78e8 J, half of
`PLANCK_ENERGY` (1.956e9), so the objection is wrong for any mass with hbar/(2 r m) > c (r*m < 1.76e-43 kg m). Module is held and
unwired, and its own docstring says the formula is the "honest physical objection"; flagged because a wrong objection sets
`mass_conserved_is_lawful=False`, which the same docstring reserves for laws that had to be patched.

### F13 (LOW) rigor.py:944-1151 -- `main()` returns 0 whatever it found
`_underpriced`, a false `both_say_consistent` and a non-empty `_unaccounted` adjudication list are printed as FINDING/WARNING lines
and the function ends `return 0`. allsweep's IMPORT tier executes it through `--help` (sweep67 b12 F1) and reads the exit code
only, so a BELOW FLOOR adjudication or an unaudited seventh one cannot turn anything red; only an exception can. Same defect
`allsweep` records as fixed for rosetta.py. Whether pinned elsewhere (drill/verify_math rows on those quantities) was not checked.

## Questions

1. **standards.py:1149-1152 and overnight.STANDING (F10).** With the reader now a standing job, should an absent `corpus read`
   entry raise the `corpus read is progressing` red row (which carries `restart_reader`) rather than being dropped?
2. **endpoint.py:223-273 (carried, b06 Q2).** Is `detect(force=True)` meant to be able to replace a live verdict with a 24 h DEAD one
   during an outage?
3. **zfighters.py:324-325 (carried, b07 Q5a).** Tien's `continuity` cites, as `[wiki]` verbatim, "Killed along with Tien when Kid Buu
   blows up the Earth ...", which reads as another character's article (Chiaotzu's own line is quoted correctly at :385-386). The
   header stakes provenance on the sentence being in the mined cache verbatim for that entity; should the Tien row be re-sourced or
   re-marked `[canon]`?
4. **descending_ladder.py:309 (carried).** `is_descent` is False for `from_m=None` while the invalid-input branch returns None; still
   the module is held.
5. **zfighters.py:436-451, catalogue_models.py, endpoint.register (carried, b07 Q4).** Do the "hand-run tool that writes ... refuses under
   a halt" rulings reach derived `data/` files (Z_FIGHTERS.json, PROVIDER_MODELS.json, SOURCE_PAGES.json)? None of the three consults
   the halt.
6. **standards.py:1816-1829 (carried, b07 Q6).** A log that cannot be statted turns `every running job is advancing` red before the
   alive test. Intended for a job that has legitimately never logged?
7. **rigor.py:688-694.** `n_laws_touched > 12` is clamped to the catalogue size (`k = min(...)`), which prices "excepts more laws than
   exist" as "excepts all of them" (0 bits). Deliberate?

## Cleared (examined closely, found correct)

- standards.py: `job_stamp`/`read_progress_verdict` (tri-state, cold start, complete exemption, stamp persisted on hold), `job_stall_verdict`
  and `output_age_min` (narrows positives only, unreadable -> None -> unmeasurable), `charter_regression_verdict` (an in-progress pass
  never holds; `at` only lands on a complete pass, matched against magnitude.py:1597-1602), `provider_pool_denominator`,
  `context_verdict`/`resident_context`/`model_matches`, `phases_standard`/`shelfmarks_standard`, the `_dropped` aggregate, the
  declared-floor self-check, the `sentences that survive the verbatim check` UNMEASURED handling, and the conditional-expression
  precedence in the model-ID standard (2408-2424).
- rigor.py: `_validate_reciprocal_matrix` (five refusals), `perron_weights`/`logrank_weights` (two-sided `abs(cr)`, `eta` None),
  `theorem_1_check`, `bradley_terry` (MM update, deviance, Ford refusals evaluated independently, prior branch), SAATY_RI values.
- thread_integrity.py: `load_thread_graph` refusal ladder, `_charter_codes` absent/corrupt/wrong-shape split, both-direction test in
  `classify`, `_floor_verdict` eight states, `_escalate_dangling` per source and uncapped, the exit-code path.
- endpoint.py: `_save` CAS and retry, `detect` API-then-raw order, `fetch_raw_verdict` tally, `source_pages`/`register` absent-vs-unreadable.
- catalogue_models.py: outcome arithmetic (EMPTY_LIST counts as verified), MalformedModelList branch, orphan-provider rows, exit code
  follows `LAST_WRITE_LANDED`.
- physics.py: every guard ordering and result-finiteness test; the relativistic switch (1.2376 vs Newtonian at 0.5c, 0.808 inverse).
- descending_ladder.py: `rung_for_length` finest-covering walk and both-ended domain guard (hand-traced), `PLANCK_ENERGY` derived.
- zfighters.py: all 14 sheets carry the eleven axes; `_incomplete` is honoured by pantheon.py:279-280.
