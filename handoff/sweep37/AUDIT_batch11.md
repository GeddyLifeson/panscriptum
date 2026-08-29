# Sweep 37 — batch 11 audit

Modules read IN FULL, every line (3,966 lines total):

| module | lines |
|---|---:|
| src/overnight.py | 1,186 |
| src/completeness.py | 709 |
| src/manifest_builder.py | 546 |
| src/reference.py | 448 |
| src/policy.py | 345 |
| src/catalogue_aurora.py | 286 |
| src/tuning.py | 263 |
| src/cachekey.py | 183 |

Method: read complete, then every finding demonstrated offline. No source file edited, no
process started/stopped/killed, no network or model call, no live config touched
(`prose_enabled` / `step4_enabled` were read only). `overnight.py`, `manifest_builder.py` and
`completeness.py` were never run as programs — individual functions were imported and exercised
with `subprocess` stubbed and `overnight.STATE` redirected into the scratchpad so nothing wrote
into `state/`. All eight modules import cleanly and `pyflakes` is silent on all eight.

---

## MAJOR

### M1. A MANAGER-rung stop is honoured by the keeper and defeated by the cycle it runs inside
`src/overnight.py` — `main()`'s cycle body, sites at lines **1021, 1027, 1040, 1046, 1053, 1103**
(and 1068, 1070, 1081). Confidence: **high — reproduced offline.**

`_manager_stopped()` (line 867) exists and is correct. It has exactly ONE call site in the whole
file, line **905**, inside `_keep`. AST enumeration of `main()`:

```
   start  line 911   job=?            inside _keep=True
   start  line 1021  job=dashboard    inside _keep=False
   start  line 1027  job=publish      inside _keep=False
   start  line 1040  job=foreman      inside _keep=False
   start  line 1046  job=overwatch    inside _keep=False
   start  line 1053  job=pipeline     inside _keep=False
   start  line 1068  job=prose        inside _keep=False
   start  line 1070  job=roll         inside _keep=False
   run    line 1081  job=read         inside _keep=False
   run    line 1103  job=pipeline     inside _keep=False
   _manager_stopped call sites in main(): [905]  (inside _keep: [True])
```

`start()` (line 431) and `run()` (line 386) check `running()` and nothing else. So every member of
`STANDING` that a person or a maintenance run closes at rung 4 is re-launched by the supervisor's
own cycle top on the next lap. Demonstrated with `subprocess.Popen` stubbed and `overnight.STATE`
redirected:

```
escalation.subsystem_stopped('pipeline') -> (True, '... closed by a maintenance run')
cycle-top standing start, exactly as overnight.main() line 1053 calls it:
[..]   pipeline: starting (background)
      *** SPAWN ATTEMPTED: ['python.exe', '-u', 'src\pipeline.py']
  start() returned: a live job handle
VERDICT: MANAGER STOP DEFEATED
```

`escalation.subsystem_stopped` has exactly two callers in the tree — `overnight.py:877` and
`drill.py`. Nothing else in `src/` reads the stop ledger, so `start()`/`run()` are the whole
enforcement surface and they do not touch it.

**And the drill net holds green over the gap.** `drill.py:4038 the_keeper_asks_before_restarting`
parses `overnight.py`, takes `_defn(tree, "_keep")`, and asserts the gate inside **that function
only**. Its own docstring calls this "The half that matters" — it is half. The net cannot fail
when the other half is missing, which is standing lesson 9 applied to the wrong scope. This is the
still-live remainder of open order **4e7f1e47d0a0** (`KEEPER_REASSERTS_A_JOB_A_RUN_STOPPED`,
handler OWNER): that order's remedy landed at the keeper and stopped there.

Why it matters: the incident this replays is the 22:5x `catalogue_web --recatalogue` stop that was
undone 25 minutes later, having nulled synthesis blocks on 26 sources including DC at 44,958
entries. The rung-4 stop is the only rung between OPERATOR and the OWNER halt that can close a
subsystem; if the supervisor re-opens it every lap, the chain still has exactly one enforceable
rung.

Filed: **4c1eaa9df7fa** (MAJOR, RUN).

### M2. `coverage_snapshot()` reports a stale COVERAGE.json as this cycle's measurement
`src/overnight.py:720-734` (`coverage_snapshot`). Confidence: **high — reproduced offline.**

```python
subprocess.run([PY, os.path.join(SRC, "coverage.py")], ...)      # return code never read
rows = json.load(open(os.path.join(HERE, "data", "COVERAGE.json"), encoding="utf-8"))
```

The subprocess verdict is discarded. A `coverage.py` that exits nonzero — a crash, an internal
refusal, a denied write of its own output — leaves the PREVIOUS `COVERAGE.json` readable, so
`json.load` succeeds and the last run's numbers are returned with no `error` key. `main()` then
takes the else-branch at line 1124 and logs them as this cycle's coverage; `write_status()` writes
them into STATUS.md as a fresh row; `history` records them as a measurement.

Proved with `subprocess.run` stubbed to `rc=1, stdout=""`:

```
COVERAGE.json on disk, mtime: 2026-08-28 23:22:16
coverage.py rc=1, wrote nothing. coverage_snapshot() ->
   {'entries': 282822, 'cited': 24693, 'read': 207890, 'feats': 102708,
    'cited_pct': 8.73, 'settled_pct': 82.24}
'error' key present: False
```

Only the *timeout* and *unreadable-file* paths reach the `except` and produce `{"error": ...}`.
The run #19 comment at lines 1115-1120 fixed the reporting of a crashed snapshot; it did not
notice that a snapshot can fail while still looking perfectly measured. The module docstring's
fifth rule is "MEASURE EVERY CYCLE", and a repeated identical row in STATUS.md is exactly the
"measurement failure wearing the shape of a measurement" the same comment names.

Filed: **a37032c3f36a** (MAJOR, RUN).

### M3. A preflight that CRASHED still passes for a pass
`src/overnight.py:737-761` (`preflight`). Confidence: **high — reproduced offline.**

The `except` arm (added run #19) covers only "health.py could not be launched / timed out". If
`health.py` starts and then dies mid-run, `subprocess.run` returns normally with a nonzero
`returncode`, a traceback on **stderr** (which is captured separately and never read), and a
**partial** stdout. `preflight()` never inspects `r.returncode`; it parses stdout only, so:

```
(a) health.py crashed: rc=1, stdout truncated after two 'ok' lines
    overnight.preflight() -> (0, False)
    main() would take: NEITHER BRANCH -- reads exactly like a clean preflight
```

`n = out.count("FAIL")` is 0 and `blocking` is False, so neither the halt branch (line 1007) nor
the "N problem(s) noted" branch (line 1012) fires and the cycle proceeds silently. `health.py`'s
contract is `return 1 if n else 0`, so a nonzero rc is not by itself a fault — but rc nonzero
**with no `FAIL` line in stdout** is a contradiction of that contract and is the crash signature.
The run #19 comment states the intent in capitals ("it no longer passes for a pass") and the
statement is currently true of one of the two ways this can fail.

Verified NOT a defect while checking: the blocking predicate
`"control characters in source" in out and "FAIL  control" in out` is reachable —
`health.py:718` prints `f"  FAIL  {label}"` and `CHECKS[0]`'s label is
`"control characters in source"`, so both substrings appear together. Not a check that cannot fail.

Filed: **6761a8e56280** (MAJOR, RUN).

### M4. Volume numbering is derived from the FILTERED build pool, so `--pilot` / `--only` build a different address than the full run
`src/manifest_builder.py:460-473` (`series_members` / `volume_code`). Confidence: **high — reproduced against live data.**

`series_members` is built from `build_pool`, which lines 437-441 have already narrowed by
`--only` or `--pilot`. A Series with one member in the pool gets the **bare** Series code; the
same source in a full build gets `code.N`. Measured on today's roll:

```
populated: 205   assigned: 205
series holding >1 source: 26
sources whose address carries a volume suffix in a FULL build: 139
   Baki               full -> II.A.1     --only -> II.A
   Bleach             full -> II.A.2     --only -> II.A
   Killer Instinct    full -> II.A.7.1   --only -> II.A.7
   ... 139 sources total change address when built alone
--pilot 3 addresses vs the full build:
   aurora_mods (Way of the Inkmaster)   pilot -> II.L.7   full -> II.L.7.48   DIFFERENT
   ROOT (the board game)                pilot -> II.P     full -> II.P.4      DIFFERENT
```

And two single-source builds inside one Series produce **identical job ids**. Calling
`build_jobs_for_source` directly with the spine each would receive under `--only`:

```
Baki      73 jobs, first five ids: ['II.A/Frontmatter', 'II.A/Persons#1-10', ...]
Bleach   161 jobs, first five ids: ['II.A/Frontmatter', 'II.A/Persons#1-10', ...]
job_ids produced by BOTH sources under a single-source build: 67
```

`generate.py` keys both its resume catalog (`catalog[job["address"]]`, line 569) and its output
filenames (`safe_filename(job["address"], "md")`, line 543) on that address. So the exact failure
the comment at lines 448-458 says it fixed — "the sources silently overwrote each other, and
resume never converged (two jobs sharing an address with different content_hashes each mark the
other stale, forever)" — is fully reproduced by any filtered build, and the same comment's claim
that "the address of a given book is stable across rebuilds" is false for 139 of 205 assigned
sources.

This is not a corner case: CLAUDE.md hard rule 6 makes `--pilot 3` the documented first step, and
the README's pilot recipe is the first command a new operator runs.

Filed: **372168774ee7** (MAJOR, RUN).

### M5. `policy.EVIDENCE_RULES` is a rule table nothing evaluates
`src/policy.py:211-218`. Confidence: **high — grep-proven, and the table exercised by hand.**

`RECORD_RULES` and `COVERAGE_RULES` are consumed by `policy.main()` (lines 276, 291) and
`RECORD_RULES` again by `drill.py:3081`. `EVIDENCE_RULES` has **zero** consumers anywhere in
`src/` — `grep -rn "EVIDENCE_RULES" src/*.py` returns only its own definition. The three
invariants it declares are therefore not red and not green; they are absent:

* `evidence.entity` / **BLOCKING** — "M23: a cache file that does not name its entity cannot be
  proved to be its own". This is the invariant the whole of `cachekey.py` exists to enforce at
  read time, and there is no corpus-wide sweep of it.
* `evidence.host` / MINOR.
* `evidence.feats` / **MAJOR** — "feats must be a list; a dict here silently mines to zero".

This is the module's own opening thesis committed inside the module: "a HIGH guard reading a
job-dict key nothing sets, so it never appeared on the page at all — not red, not green, ABSENT
for its whole life." I exercised the table by hand over a random sample of **5,000 of the 255,855**
evidence files (seed 37, 16 threads) — 0 unreadable, 0 rule failures, 0 vacuous passes — so the
corpus is not currently in breach. The finding is the absent evaluation, not a corpus fault.

Filed: **ab820740fb85** (MAJOR, RUN).

### M6. `cachekey`'s "ONE HELPER, NOT FOUR SPELLINGS" is not in effect — there is a fifth spelling, and it reads without verifying
`src/cachekey.py` module docstring §3, against `src/read.py:1029-1030`. Confidence: **high — grep-proven and quantified on live data.**

`cachekey.py`'s docstring names four sites (`pipeline.py`, `coverage.py`, `feats.py`,
`hostcheck.py`) and argues "A rule applied at some of its sites is not applied (standing lesson
14)". `read.py` honours the helper in three places (`read.py:584, 694, 838`) and re-spells the
formula by hand in a fourth, inside `queue()`:

```python
path = os.path.join(FF.CACHE, re.sub(r"[^A-Za-z0-9]+", "_", h)[:40],
                    re.sub(r"[^A-Za-z0-9]+", "_", e["name"])[:80] + ".json")
if not os.path.exists(path):
    continue
```

Two consequences, both of them the M23 defect in miniature:

1. The file is opened and its `chars_read` / `own` / `axes` / `quantities` are used to rank the
   read queue, **without `cachekey.owns()`** — so a contested slot ranks one entity on its
   neighbour's evidence. Worse, `if not ev.get("text")` marks `skip: True` in the queue cache and
   drops the entity from the read queue entirely, on the strength of a file that is not its own.
2. It only ever looks at the natural path, so an entity whose evidence lives at a
   `__<sha1>` disambiguated sibling is invisible to the queue.

Measured on the live corpus (282,059 entity names across all records, joined to WIKI_HOSTS):

```
natural-path slots contested by >1 distinct entity name: 14
contested slots that HAVE a cache file on disk today:    14
disambiguated sibling cache files on disk:               21
```

The 14, in full:

| host dir | stem | entities folded together |
|---|---|---|
| en_wikipedia_org | `V_r` | Vár, Vör |
| en_wikipedia_org | `Midheaven_Medium_Coeli_MC_` | Midheaven (Medium Coeli / MC), Midheaven (Medium Coeli, MC) |
| forgottenrealms_fandom_com | `Ten_Towns` | Ten Towns, Ten-Towns |
| pixar_fandom_com | `Magic_8_Ball` | Magic 8 Ball, Magic 8-Ball |
| dc_fandom_com | `JSA_All_Stars_Vol_1_8` | JSA All-Stars Vol 1 8, JSA: All Stars Vol 1 8 |
| dc_fandom_com | `Teen_Titans_Go_TV_Series_Episode_The_Self_Indulgent_` | ...Spectacular! Pt 1, ...Pt 2 (an 80-char `NAME_CAP` fold) |
| marvel_fandom_com | `What_If_Vol_1_44` | What If...? Vol 1 44, What If? Vol 1 44 |
| marvel_fandom_com | `What_If_Vol_1_28` | What If...? Vol 1 28, What If? Vol 1 28 |
| marvel_fandom_com | `What_If_Vol_1_10` | What If...? Vol 1 10, What If? Vol 1 10 |
| marvel_fandom_com | `Wolverine_Vol_2_1` | Wolverine Vol 2 -1, Wolverine Vol 2 1 |

(4 further slots beyond the 10 printed by the probe's own head; the count of 14 is complete.)

**And the drill net enumerates four files.** `drill.py:3695-3696`:
`{"coverage.py": "cachekey.", "feats.py": "cachekey.", "pipeline.py": "cachekey.",
"hostcheck.py": "cachekey."}` — `read.py` is not in the set, so
`guards_are_wired_where_claimed` holds green while the fifth spelling stands.

Blast radius is bounded (≤ 28 entities of 282,059, plus 21 invisible siblings) and the effect is
on queue ranking and the queue's skip decision, not on citation text. Filed at MAJOR because the
invariant is stated absolutely and the fix is one line.

Filed: **c812e8db852f** (MAJOR, RUN).

---

## MINOR

### m1. `safety_drill()` treats every exit code except 1 as "not breached"
`src/overnight.py:789`. `if r.returncode == 1:` is the only breach branch. `drill.py` exiting 2
(argparse), or with a Windows NTSTATUS, or any other nonzero, logs only
`"safety drill: <line>"` or `"produced no summary line"` and the cycle proceeds. `name_rc` in this
same file exists precisely because an unrecognised exit code is a bug and not weather; the
inspection that runs before every stage does not use it. Confidence: high (read).

### m2. `write_status()` is a truncate-then-fill write on a published file
`src/overnight.py:798-822`. `open(p, "w")` on `STATUS.md` — the m6 pattern this project retired
repo-wide. `publish.py` copies STATUS.md verbatim to the public repo and `estate.py` hashes it, so
an exception part-way through the 20-odd writes leaves a truncated STATUS.md that gets published.
Nothing here is atomic and there is no verdict to gate on. Confidence: high (read).

### m3. `catalogue_aurora.main()` carries no exit status
`src/catalogue_aurora.py:286` — `main()` (no `sys.exit`). The function is otherwise a careful
essay on not discarding write verdicts: it gates `write_record_catalogue` (line 246), gates the
summary roster on it (line 256), and gates the `SWEEP_ROLL.json` write (line 271). It then
returns `None` and `if __name__ == "__main__": main()` exits 0 — so a denied roll write, a folder
with no roll entry, and a folder that parsed nothing all exit success. `manifest_builder.main()`
does the opposite two files away (`return 0 if manifest_landed else 1`). Confidence: high (read).

### m4. An unreachable-host row records N probe failures out of 0 probes run
`src/completeness.py:473-478`. `_unmeasured(..., probe_failures=len(probes))` while `probes_run`
keeps its default of 0. The comment two lines up says "Not probed further, deliberately" — so
zero probes were attempted and eight failures are recorded. On disk right now:

```
(probe_failures, probes_run) counts: {(8,0): 196, (0,0): 19, (0,8): 1}
rows claiming N failures out of 0 probes run: 196 of 216
```

`verify_math.py:1478` pins `"its probes_run is honestly zero"` for exactly this row, so the shape
is deliberate — but the two fields on one row contradict each other and any reader computing a
failure rate divides by zero. **Reported, not filed** (pinned as intended by the battery).
Confidence: high (measured).

### m5. `tuning.profile()` derives the cloud worker count outside the regime cache
`src/tuning.py:215-223`. `regime()` caches its verdict for `RECHECK_SECONDS` (180s), but
`profile()` then calls `_answering_buckets()` again, unconditionally and uncached. A regime cached
as "cloud" from a 5-bucket reading can hand out `max(4, min(16, 0+2)) = 4` workers when
POOL_PROOF.json now shows zero answering. Bounded by the floor of 4, but the label and the number
come from two different moments. Confidence: high (read).

### m6. `completeness.work()`'s `unreliable` reason is an elif chain, so one row states only its first defect
`src/completeness.py:554-574`. A source that is both uncatalogued (`rec is None`) and a non-primary
host-sharer reports only "no catalogue record on disk". Each branch's text is written as if it
were the whole story. Confidence: high (read).

### m7. `_cmd_is_running` / `_in_this_tree` tokenise a command line with `.split()`
`src/overnight.py:207, 243-253`. A quoted interpreter or script path containing a space makes
`toks[0]` `'"C:/Program'`, whose basename contains no `"python"`, so `_cmd_is_running` returns
False and the job reads as not running — the ONE OF EACH guard silently off. Latent on this
machine (`sys.executable` is `C:\Users\imarl\miniconda3\python.exe`, tree is
`panscriptum-library-kit`; neither has a space). Confidence: high (read); dormant.

### m8. `running()` fails OPEN when the process probe itself fails
`src/overnight.py:163-165`. `_proc_lines()` returns `""` if the PowerShell/CIM call throws (its
handler only notes and returns the stale `_PROCS["out"]`, which starts as `""`), and `running()`
answers `False` for every fragment on an empty listing. Every stage guard, the `_guarded_popen`
authoritative second check, and the twin-supervisor check at line 853 all read that same `False` —
so a probe outage does not degrade the guard, it removes it, and line 850's comment describes what
happens next ("Two watchdogs once launched two of these twenty seconds apart"). `_in_this_tree`'s
docstring argues for failing open at the *per-process* level, which is a different and defensible
choice; there is no equivalent reasoning for failing open when the whole listing is missing.
Confidence: high (read). Reported rather than filed because the remedy (refuse to start on an
empty listing) needs a judgment about which direction is cheaper, which is the same trade
`_in_this_tree` already argues in the opposite direction.

---

## INFO / cosmetic

* `src/overnight.py:815` — `for h in history[-12:]` in the STATUS.md Cycles table. A tail rather
  than a truncated head, no count is announced, and `history` is in-memory only, so nothing
  durable is being hidden. Noted because it is the same shape as the `did[:5]` and `[:top]` slices
  removed elsewhere in this file.
* `src/policy.py:123` — `ok = False` immediately before a `return`; the name is never read.
* `src/reference.py:50 and :355` — `silence` imported twice, once at module scope and once inside
  `main()`.
* `src/reference.py:320` — `f"{band}.{round((val % 1) * 100):02d}"` renders `M4.100` for a charter
  value of 4.995 or higher. No such value exists in `REFERENCE` today.
* `src/cachekey.py:19` — the docstring's "59 entities sitting at the 80-char cap" is a measurement
  of record from fix time; today it is 144 files at the cap. Not stale as a claim (it is dated),
  noted so the next reader does not treat it as current.

---

## VERIFIED HEALTHY

Everything below was checked and is correct. Recorded because an audit that reports only faults
cannot be told from an audit that stopped early.

**`reference.py` — the benchmark is NOT stale.** All three reconstructions land inside the
charter's published intervals, computed in memory (no write):

```
Goku            ref=7.440  charter=7.62 ±0.41  delta=0.180  INSIDE
Naruto Uzumaki  ref=4.560  charter=4.31 ±0.30  delta=0.250  INSIDE
Monkey D. Luffy ref=4.480  charter=4.08 ±0.55  delta=0.400  INSIDE
```

axis_coverage 1.0 for all three (11/11 axes scored), interval 0.15 each — consistent with the
module docstring's claim that these are tighter than the charter's because inter-hand dispersion
is not reproduced. `shelfmark()` renders all seven RUNGS correctly against the live NAVTREE
(`Ω › H.The Spoken › X.Venaellys › Mt.Miirora › Mv.DRG › U-7 › G.North › P.Earth`), and its
length clamp is correct for the 3+4 shape all three entries have.

**`reference.py --compare`'s key indexing works and its per-axis diff is live, not dead.** The
`(host, entity)` index finds all three rows in the 507-row `ASSAYS.json`. Zero of 507 rows carry
a `scores` key, so the axis diff currently prints "not recorded on this row (pre-dates
b03f2ab9951a)" for every row — which is exactly what the code says it should do, and is a fact
about the file's age, not a dead branch: `assay.assay()` emits `"scores"` at `assay.py:915`, so
the branch fires the moment the automated pass is re-run. The comment's claim is accurate.

**`catalogue_aurora.slug()` / `record_path()` — today's cap removal holds.** All ten
`FOLDER_SOURCE` sources resolve through `record_path` to a file that **EXISTS**
(`dr-firestorm-s-engineering-corps.json`, `unearthed-arcana-incl-the-planeshift-documents.json`,
etc.). Nothing was stranded by removing the 60-character cap, and `LEGACY_SLUG_CAP` is used only
to *find* an existing file, never to mint a new identity.

**`manifest_builder.load_record()` — the resolution claim is exactly true today.** Over all 215
roll rows: **214 resolve by exact normalised equality, 1 inexact (the documented Roger Rabbit
truncation), 0 unresolved.** `MIN_INEXACT_LETTERS = 12` strands nothing.

**`manifest_builder.pack_feats()` is pagination, not truncation.** Every slice is emitted, spans
are contiguous (`start += len(slice_)`), the flush happens *before* the budget is exceeded, and a
single deed larger than the whole budget still gets its own block rather than being clipped —
it is left to fail loudly at `assert_fits`. `budget` is a required argument, so the
`FEATS_BLOCK_CHARS` constant cannot leak back in as a default.

**`policy.py`'s evaluator refuses everything it claims to refuse.** Ten behaviours exercised, ten
correct: unknown op refused; a rule missing `id`/`path`/`op` refused; `is_type` with no `arg`
refused; `is_type` with an unknown `arg` refused; `resolve` distinguishes a held null from an
absent field; `not_matches` on an absent field is reported VACUOUS; `absent` on an absent field is
NOT reported vacuous and does not fail; `nonempty` on an int returns an error record rather than
raising; a malformed regex returns an error record rather than raising; a dotted path indexes
through a list. The `TYPES` closed set and the `is_type`-arg pre-check both do what their comments
say.

**`policy.main()`'s scope reporting is honest.** `--limit` defaults to `None`, the whole corpus is
the default, `partial` is stated in the printed banner and stored in the report's `scope` block,
and every skipped record is named. All failures and all vacuous passes are printed, uncapped.

**`completeness.py`'s three land() guards and the write verdict are all real.** The `--only`
exemption, the `[]` refusal, the `SHRINK_FLOOR` refusal and the `silence.write_json` return value
are each gated and each returns False to a caller that exits 1. `verify_math.py:1490-1515` drives
all four against a redirected `_CP.OUT` in a tempdir and puts the real path back, so the battery
does not damage the live artifact.

**Every consumer of `COMPLETENESS.json` honours the `unreliable` field**: `standards.py:1164`
(`good = [c for c in comp if not c.get("unreliable")]`), `foreman.py:707`,
`catalogue_web.py:428`. An unmeasured row's `coverage: 0.0` is therefore never folded into an
aggregate. (Live state right now: 215 of 216 rows unreliable, 196 of them "host unreachable" —
that is a transport observation tonight, not a code finding, and the module records it exactly as
designed.)

**`cachekey.py`'s own caps are safe caps.** No `HOST_CAP(40)` fold exists among the 140 real hosts
(longest sanitised host is 45 chars, `doc:arcanum-worlds-odyssey-of-the-dragonlords`, and it does
not collide with anything). 0 host/directory mismatches in 692 sampled cache files. 21
disambiguated siblings on disk prove `write_path`'s collision branch is live and working. The
`NAME_CAP` fold is real (144 files at the cap) but is handled correctly *by this module* —
`owns()` turns a fold into a MISS and `write_path` diverts the loser. The gap is at the
unconverted caller (M6), not here.

**`overnight.name_rc` names rc=17 correctly** as `"rc=17 (ON PURPOSE — source changed, restarting
to run the current code)"` and lists it before the codes it must not be confused with. And rc=17
**cannot currently trip the idle halt**: a job exiting 17 makes `statuses` contain `"rc=17"`, which
is not `"already-running"` — but the serial `run("pipeline")` at line 1103 reliably *is*
`"already-running"`, so `busy` is non-empty, the cycle takes the wait branch, and `idle` is reset
to 0. That is order **5d14e90b5043**'s own argument for why deleting the call is not neutral, and
it is correct: deleting it re-arms the idle halt against a codewatch bounce.

**No second instance of the unreachable-work shape.** All ten `start()`/`run()` sites in `main()`
were enumerated by AST (table under M1). The only job appearing twice per cycle is `pipeline`
(backgrounded at 1053, serial at 1103) — the already-filed case. `dashboard`/`publish`/`foreman`/
`overwatch` appear once in the cycle and once in the keeper, which is bootstrap plus re-assertion,
not duplicate work.

**Every `[:N]` slice in all eight modules was enumerated and classified.** 35 slices total: 22 are
single-string display truncations in log/print formatting; 4 are hex-digest truncations
(`content_hash`, `_suffix`, `text_digest`) which are hashes, not rosters; `overnight.py:606`
(`[:top]`) and `completeness.py:681` (`good[:a.top]`) both announce the true count beside the
printed subset; `policy.py:272/288` (`[:a.limit]`) defaults to no limit and labels itself PARTIAL;
`manifest_builder.py:441` (`[:args.pilot]`) is the documented opt-in pilot;
`catalogue_aurora.py:112` (`LEGACY_SLUG_CAP`) reads an existing file and never writes a truncated
identity; `cachekey.py:58/63` are filename caps with verification and disambiguation behind them.
**No Hard Rule 0 violation found in these eight modules.** `catalogue_aurora.slug()` is confirmed
uncapped.

**`overnight._prose_enabled` delegates** to `prose_gate.gate_open(cfg)[0]` and fails closed on any
exception. Read only; not exercised against the live config, per instruction. `drill` and
`verify_math:4705-4711` both pin it.

**Both escalation interlocks fail closed as documented** — the startup one at line 829 and the
per-cycle one at line 986 each raise `SystemExit` on `ImportError` rather than passing, and
`_manager_stopped` returns `(True, ...)` on any exception. (What is missing is not the fail-closed
behaviour but the number of places that ask — see M1.)

**Static health**: `pyflakes` clean on all eight modules; all eight import without side effects
beyond their `_BAD_CHARS` self-check, which passes.

---

## Orders filed

| id | severity | where |
|---|---|---|
| 4c1eaa9df7fa | MAJOR | src/overnight.py:1021,1027,1040,1046,1053,1103 |
| a37032c3f36a | MAJOR | src/overnight.py:720-734 |
| 6761a8e56280 | MAJOR | src/overnight.py:737-761 |
| 372168774ee7 | MAJOR | src/manifest_builder.py:460-473 |
| ab820740fb85 | MAJOR | src/policy.py:211-218 |
| c812e8db852f | MAJOR | src/cachekey.py docstring §3 vs src/read.py:1029-1030 |
| b66a8b1acf50 | MINOR | src/overnight.py:789 |
| 3fdf445e7c0d | MINOR | src/overnight.py:798-822 |
| 3cc35f54b235 | MINOR | src/catalogue_aurora.py:286 |
| ac55ed089e96 | MINOR | src/tuning.py:215-223 |

Reported but deliberately NOT filed: m4 (pinned as intended by `verify_math:1478`), m6, m7
(dormant on this machine), m8 (the remedy is a direction judgment, not a defect fix), and every
INFO item.
