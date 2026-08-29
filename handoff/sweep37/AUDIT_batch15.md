# SWEEP 37 — BATCH 15 AUDIT

Modules read IN FULL, every line, by one agent in one pass:

| module | lines | read |
|---|---|---|
| src/dashboard.py | 1038 | full (1-520, 520-1039) |
| src/overwatch.py | 869 | full (1-450, 450-870) |
| src/gpu_lane.py | 538 | full |
| src/sweep_plan.py | 418 | full |
| src/pick_model.py | 359 | full |
| src/retry_synthesis.py | 297 | full |
| src/cleanup.py | 264 | full |
| src/ledger.py | 172 | full |
| **total** | **3,955** | |

(The batch brief said 3,991 lines; the tree today is 3,955. The difference is drift in the
brief, not an unread file.)

Every finding below was reproduced or read off the source directly. Nothing here is a
line-number citation into a file I did not open, and nothing is reported from a grep.

---

## MAJOR

### 1. `overwatch.load` — a ledger that PARSES but is the wrong shape gets neither quarantine nor a fresh start, and takes the round down
`src/overwatch.py:167-196` (the `except` only fires for a parse failure; line 171 `return d`
returns whatever JSON held)

`load()`'s whole thesis is stated in its own docstring: *"An ABSENT file and a DAMAGED one are
not the same event and must not get the same response."* There is a third case it does not
have: a file that is valid JSON and not a ledger. `json.load` succeeds, so the `.corrupt`
preservation, the `_UNPRESERVED` refusal and the fresh-ledger fallback are all skipped, and the
object is handed straight to `round_once`, which dereferences it on the next two statements
(`led.get("rounds")`, `led["findings"].items()`).

Reproduced against temp copies (the real ledger was never touched):

```
good.json     load() ok, round_once-shape ok
torn.json     load() ok  -> quarantined correctly as .corrupt   (this half works)
null.json     load() ok BUT round_once RAISES AttributeError: 'NoneType' object has no attribute 'get'
list.json     load() ok BUT round_once RAISES AttributeError: 'list' object has no attribute 'get'
noflds.json   load() ok BUT round_once RAISES KeyError: 'findings'
str.json      load() ok BUT round_once RAISES AttributeError: 'str' object has no attribute 'get'
```

Why it matters: `overwatch --loop` is a STANDING job under the keeper's restart set. A ledger
in any of these shapes is an unhandled exception every round, forever, and the wreck is never
preserved — the exact loss the m28 quarantine was written to prevent, reached by the one door
it does not cover. One `isinstance(d, dict) and "findings" in d` check on line 170 routes it
into the path that already exists and already works.

Confidence: HIGH on the mechanism (demonstrated). MEDIUM on how often the shape arises — a
truncated write parses as an error, not as `{}`, so the realistic sources are an operator or a
tool resetting the file, or a foreign writer.

### 2. `overwatch.verify_open` — a finding the model never answered on is stamped as verified and rotated to the back of the queue
`src/overwatch.py:559-561`

```python
got = _ask(VERIFY_SYSTEM, prompt, VERIFY_SCHEMA, local=local)
f["last_verified"] = time.time()
checked += 1
```

`_ask` returns `None` on purpose when the GPU is busy and the round's cloud budget is spent —
that is "THE WATCHER YIELDS" at `overwatch.py:428-436`. The stamp and the counter do not know
that. Reproduced with `_ask` patched to return `None`:

```
verify_open with _ask->None: checked=1 closed=0  last_verified before=None after=1787978239.6
```

Two consequences. The round prints `auto-triage: N open finding(s) re-verified` when zero were
looked at. And `opens` is sorted oldest-verification-first, so a yielded finding is sent to the
BACK of the rotation as if it had just been checked — during a busy stretch the entire open set
can be stamped and cycled without one verification, and the closer that exists to stop the open
count growing quietly stops closing.

This is the SAME defect, one function over, as the one already fixed in `review`/`round_once`
under order a3ee0d1d2d4c: *"A slice skipped because the GPU was busy ... looks exactly like a
slice read and found clean ... stamping `seen` here regardless used to let an UNREVIEWED module
get sorted to the back of `rotation()`'s stale queue as if it had just been read."* The `seen`
half got a `complete` flag; the `last_verified` half did not. Guard both the stamp and the
counter on `got is not None`.

Confidence: HIGH (demonstrated).

### 3. `gpu_lane.lane` — the one failure path the module documents as "proceed unmetered" waits the full 900-second slot ceiling instead
`src/gpu_lane.py:326-327` (the verdict) and `src/gpu_lane.py:480-484` (the caller)

`_take_slot` returns `None` for TWO different situations and the caller cannot tell them apart:
every slot is live (wait), and *`except Exception: return None  # cannot arbitrate -- caller
proceeds unmetered`*. The caller does not proceed. It sits in
`while _now() < deadline: slot = _take_slot(label); ...; time.sleep(_POLL)` and only falls
through after `SLOT_LEASE_SECONDS`, which is **900 seconds**.

Reproduced with `LANE` pointed at a temp directory (the live lane was never touched) and the
ceiling shortened to 2 s:

```
gpu_lane: _take_slot can-not-arbitrate -> lane() delayed the call by 2.01s (ceiling was 2.0s)
```

Why it matters: this contradicts the file header's own mandate — *"FAIL OPEN, ALWAYS ... a
corrupt claim file, a permissions error, **a slot that cannot be created**, a wait that runs
past its ceiling -- all of them end in 'go ahead anyway'"* — and it contradicts `_take_slot`'s
own comment on the line that returns. `lane()` sits in front of every model call the library
makes, so a persistent `os.open` failure on `state/gpu_lane` (a permissions change, an
antivirus hold — Norton already blocks DuckDB and Python's TLS on this machine) turns every
model call in nine standing jobs into a 15-minute stall. That is the deadlock the header says
would be "far worse than no lane at all". Distinguishing the two answers costs one sentinel:
return `False` for "busy", `None` for "cannot arbitrate", and break out of the queue loop on
the latter.

Confidence: HIGH on the code path (demonstrated). MEDIUM on how likely a persistent `os.open`
failure is here.

---

## MINOR

### 4. `sweep_plan.modules` — "NO exclusions, deliberately" excludes 280 lines
`src/sweep_plan.py:45`

`glob.glob(os.path.join(SRC, "*.py"))` is not recursive. `src/deprecated/catalogue_local.py`
(280 lines) is a module in `src/` that no sweep has ever covered, that `allsweep.modules()`
(same glob shape) never import-checks, and that overwatch's model never reads. Verified:

```
sweep_plan.modules(): 114 modules;  catalogue_local.py in modules(): False
```

The structural half is what makes it worth filing rather than shrugging at: `missing()` is
`modules() - covered_by(run)`, so a module `modules()` cannot see is a module `missing()` can
never name. The completeness check cannot notice this class of gap by construction, which is
the one property this file exists to have. The docstring already writes the remedy — *"If a
module is genuinely not worth auditing, that is an argument for deleting it, not for skipping
it"* — so either delete `src/deprecated/` or make the glob recursive; nothing imports the file
(only a prose mention in `catalogue_web.py:5`).

Confidence: HIGH.

### 5. `sweep_plan.record` — the fallback that "MUST NOT BE THE THING THAT RAISES" can still raise
`src/sweep_plan.py:226-228`

```python
tmp = "%s.%d.tmp" % (COVERAGE, os.getpid())
with open(tmp, "w", encoding="utf-8") as f:      # <- outside every try
    json.dump(data, f, indent=1, sort_keys=True)
```

Today's repair correctly routed the bare `os.replace` below this through `replace_retry`, and
the comment claims the fallback can no longer take a sweep agent down. The `open`/`json.dump`
in front of it are still unguarded — and they are the LIKELIER raiser, because
`silence.write_json` (`silence.py:409-414`) explicitly re-raises a failed dump, so the
condition that reaches this fallback in the first place is usually the same condition that will
break it again two lines later. Wrap 226-241 in the `try/except` the block above already has.

Confidence: HIGH (read off both files).

### 6. `overwatch.write_report` — three silent truncations in the only human-facing report
`src/overwatch.py:654` (`[:40]` open findings), `:628` (`broken[:4]`), `:642` (`corrupt[:3]`)

The header line states the true count (`**N open** (M high)`) and the list beneath it stops at
40 with no "and N more". The identical caps have already been ruled truncations three times
elsewhere in this batch's own files — `dashboard.py:326` ("ALL open findings — a monitoring cap
ruled a truncation, 2026-08-24"), `dashboard.py:331-336` (swallowed failures), `dashboard.py:894`
(breached nets), `dashboard.py:917` (quarantined hosts). WATCH.md is the sibling that was never
visited. Latent today: 4 open findings, so the cap does not bind — but the report's whole job
is to be readable in ten seconds on the day it does.

Confidence: HIGH.

### 7. `overwatch.round_once` — the sweep over "every module" excludes two modules, silently
`src/overwatch.py:747-748`

```python
mods = [m for m in A.modules() if not m.startswith("_") and m not in ("overwatch", "allsweep")]
```

No comment says why. The CLI describes this job as *"a standing debug sweep over every module"*
(`overwatch.py:818`) and the owner's brief in the docstring is *"watches all modules for bugs"*.
The two excluded files are 869 and ~700 lines of the watching machinery itself — the modules
whose defects mean no watching happens — and `sweep_plan.modules` takes the opposite and
better-argued position for the same reason ("Not even this file"). Either read them or record
the reason in the code.

Confidence: HIGH.

### 8. `dashboard._num` — a drifted line-number tag in the file that documents why line-number tags drift
`src/dashboard.py:77`

`silence.note("dashboard.py:73")`, sitting on line 77. Four lines out already. This file
carries the lesson at `dashboard.py:482-486`: *"The old label said 'dashboard.py:336' while
sitting at 362 -- m81's drift ... every one of them rots; a stable tag cannot."* This is the
last numeric tag in all eight modules of this batch (verified by grep across them); the fix is
a descriptive tag such as `dashboard.py:num-parse`.

Confidence: HIGH.

### 9. `dashboard.movement` — the corrupt-history heal does not cover a list of non-dicts, and that case wedges forever
`src/dashboard.py:393-427` (the `h.get("at", 0)` at :396 raises inside the guarded block)

The isolation added for run #26 checks `json.load` and `isinstance(hist, list)`. It does not
check the ELEMENTS, so `[1, 2, 3]` passes the guard, `h.get` raises on the filter, the whole
try/except returns `[]` — and the write that would repair the file is skipped. Every later poll
repeats it, which is exactly the wedge the comment at :369-382 says was fixed. Reproduced on a
temp history file:

```
movement torn (unparseable)   -> rows=6  file healed=True
movement not a list           -> rows=6  file healed=True
movement list of non-dicts    -> rows=0  file healed=False   ('[1, 2, 3]')
```

One `and all(isinstance(h, dict) for h in hist)` on the existing guard closes it.

Confidence: HIGH (demonstrated). Reachability is the low half: a torn write usually fails to
parse rather than parsing as a list of scalars.

### 10. `retry_synthesis.do_merge` — exits 0 on a partially applied merge
`src/retry_synthesis.py:225`

`do_merge` counts `denied`, prints it, and then `return 0` unconditionally, so `main()`
`sys.exit(0)`s on a merge where records refused the write. Its own sibling path in the same
file gets this right (`return 0 if landed else 1`, :293), and `cleanup.py:260` was given the
same treatment today (`return 1 if unwritten else 0`). An automated caller cannot see the
difference between "12 merged" and "6 merged, 6 denied". `return 1 if denied else 0`.

Confidence: HIGH.

### 11. `cleanup.py` — the thin-description mark is not idempotent, so every `--apply` rewrites every record that has one
`src/cleanup.py:195-205`

```python
if len(cd) < _THIN:
    thin.append((src, nm, cd))
    if args.apply:
        e["thin_description"] = True
        changed = True
```

`changed` is set whether or not the flag was already there. The two sibling branches above it
cannot re-fire (`if not e.get("catalogued"): continue` skips an already-struck entry), but this
one fires on every run for every already-marked entry, so a second `--apply` re-writes every
record containing a thin description with no net change. That is unnecessary traffic through
`write_record` — the two-writer contract with a live pipeline, which this project has already
been burned by. Guard on `if not e.get("thin_description")`. Note this is the branch that was
FIXED in run #29 for the opposite fault (`changed` never set); the repair overshot by one step.

Confidence: HIGH.

---

## INFO / COSMETIC

12. `src/dashboard.py:396` — `[-2000:]` on the movement history makes the documented 24-hour
    cutoff on the line above unreachable: at the page's 5-second poll, 2,000 rows is about 2.8
    hours. Nothing breaks (`MOVED_WINDOW_MIN` is 30 minutes, comfortably inside it), but the
    24-hour filter is dead code and the comment reads as though a day of history is kept.
13. `src/pick_model.py:185` vs `:239` — the VRAM budget is GiB (`nvidia-smi` MiB / 1024) and
    the model weight is decimal GB (`size / 1e9`). The residency gate is therefore about 7%
    more permissive than it reads. Also `total_vram_gb() or 10.0` at `:297` silently assumes a
    10 GB card when `nvidia-smi` cannot be read, on a gate whose whole purpose is refusing
    models that will not fit.
14. `src/dashboard.py:513-521` — `safety()`'s docstring says *"Every field here is READ from a
    file, never computed by running the thing it reports on"*, and `:559-560` then re-derives
    `assay.calibration_report()` on every poll (measured 39 ms, so harmless; the claim is what
    is wrong, and its own inline comment at :556 admits it).
15. `src/dashboard.py:353` — a literal `\n` inside a non-raw docstring, mid-sentence.
16. `src/pick_model.py:288` — the `except` handler for an unreachable Ollama re-reads
    `cfg['ollama_host']`, so a `config.yaml` missing that key raises `KeyError` from inside the
    handler rather than printing the message.

---

## HEALTHY — verified, not assumed

* **`sweep_plan.batches()` cannot drop a module.** Exercised at n = 1, 3, 16 and 200 against
  the live tree: 114 modules in, 114 module slots out, no duplicates, set equality with
  `modules()` in every case. Bins that end up empty are dropped, batch ids are preserved, and
  no `[:N]` exists anywhere on the path.
* **`missing()` genuinely notices a drop.** Simulated a full 16-batch run with one module
  deliberately omitted from one batch's `record()` call: `missing()` returned exactly
  `['magnitude.py']`. Then recorded a LATER run covering everything and re-asked —
  `missing('runTEST')` still named the same module, i.e. the membership-vs-newest-wins fix from
  run #29 holds. `latest_run()` reported the newer run. (All of this against a temp
  `SHARDS`/`COVERAGE`; the real `state/sweep_shards` was never written by the probe — verified
  by listing it afterwards.)
* **The shard write in `record()` is correctly gated** and the aggregate fold's ungated verdict
  is correctly argued: `covered_by` reads shards and only ADDS from `SWEEP_COVERAGE.json`, so a
  refused aggregate write can make a complete sweep look short, never an incomplete one look
  complete. Confirmed by reading `covered_by`. Also confirmed that a re-`record()` for the same
  run+batch REPLACES that shard rather than unioning it — the fail-safe direction, since
  `covered_by` unions across shards.
* **overwatch's three gated writes are right.** `save()` refuses while `_UNPRESERVED["on"]`;
  `save()` gates `replace_retry` and does NOT re-stamp `_SNAPSHOT` on a denial; `write_report`
  gates and `round_once` prints "(NOT UPDATED -- see stderr)". The `load()` quarantine now asks
  the verdict and refuses to let a fresh ledger land over an unpreserved wreck — I confirmed
  the unparseable case takes that path and reports honestly. Today's repair is correct as far
  as it goes; finding 1 is the door it does not cover.
* **`_merge_ledgers`** is monotone as documented — union of findings by fingerprint with
  `_progress` deciding a contested key and ties to disk, `seen` by later `at`, `rounds` by
  `max`, `last_run` by string max on a zero-padded timestamp. Nothing in the module deletes a
  finding, so the union genuinely loses nothing.
* **`gpu_lane` is arbitrating in effect right now, not merely in a file.** `status()` on the
  live lane: `MAX_SLOTS 3` (correctly derived from `OLLAMA_NUM_PARALLEL`, not a third hardcoded
  copy), all three slots held by live PIDs (`pipeline:ask` x2, `pipeline:overwatch`), heartbeat
  ages 4.7 / 75.9 / 87.3 s against a 100 s beat and a 900 s lease. `_BEAT_SECONDS` is correctly
  derived from `min(SLOT_LEASE, CLAIM_LEASE)/3`. `_write_claim`'s returned verdict is checked
  at the entry claim and noted; the heartbeat's and the decrement's ungated verdicts are both
  argued correctly (a beat is re-sent ~100 s later and `replace-denied:` is already in the
  ledger; a depth left high errs toward yielding).
* **`_touch` never resurrects** a released slot (`_read` returning `None`, or another PID's
  record, is left alone) and `lane()` stops the beat before releasing. Both halves of that race
  are closed.
* **`retry_synthesis.save_side` returning `(merged, landed)` is correct and correctly used.**
  `landed` resets to True on a later successful save (right: every save rewrites the whole
  accumulated map), the per-source line says SAVE DENIED instead of printing a magnitude, the
  final line distinguishes memory from disk, and `main` returns 1. `stranded_sources()`
  selecting on the CONDITION rather than the cause is the right call and the docstring's
  reasoning checks out.
* **`cleanup.py` PARTIALLY APPLIED is correct**, including `return 1 if unwritten else 0` and
  listing refused records by name with an "... and N more" tail.
* **`dashboard`'s movement history left best-effort: two of the three stated reasons verified
  exactly, the third with a caveat.** (1) the return value does not depend on the write — true,
  `hist` holds the row in memory; (2) the next poll retries within seconds — true; (3) the
  stall detector does not go blind — true while frozen rows remain (`base` freezes, `span`
  grows, `delta == 0 and span >= 10` still fires), but once the 24-hour cutoff empties them the
  panel renders "no change yet" with `minutes: 0` rather than the "zero-length window" the
  comment implies. Not a defect; the third justification is a shade stronger than the code.
* **The `dropped` field is in effect, not just present.** `dashboard._read_row` captures it and
  `standards.py:948` reads `read.get("dropped")` to compute the fabrication rate against
  `MAX_FABRICATION`. The run #28 repair of the never-executing guard is real.
* **`dashboard`'s no-cap rulings hold** across `_watch` findings, swallowed failures, breached
  nets and quarantined hosts — all four render every element.
* **`ledger.py` is clean.** `JOULES_PER_STANDARD` is imported from `physics.MATERIAL` and
  equals the documented 2.14e8; `to_standards`/`from_standards` round-trip exactly for all
  seven convertible currencies; `cross_rate` is `rb/ra`, which is the ratio its docstring
  claims; `currency_status` distinguishes unlisted from deliberately non-convertible.
  `BAND_EDGES` keys equal `LADDER` (so `.index` after the `in BAND_EDGES` check cannot raise),
  no band floor is zero (so `math.log(lo)` is safe), and the M10 fix works as documented —
  `ruin_score` now moves the answer at M10 (1e99 -> 1e113) over the same 14 orders of magnitude
  M9 spans, anchored at M10's own floor.
* **`cleanup.py`'s mangled-escape guard** is complete: `_NAV`, `_EMPTY_MECHANIC`, the real
  `PL._SETTING_META` and every one of the nine `_MARKUP` patterns are on the roster, and the
  guard raises SystemExit rather than passing quietly. The `\b`-vs-`$` asymmetry in `_NAV` is
  deliberate and its comment says so in the right tense.

---

## Method notes / disclosure

* Nothing was edited. No module in this batch was run as a program. `overwatch`, `dashboard`,
  `gpu_lane`, `sweep_plan`, `ledger`, `retry_synthesis` were imported and exercised as
  functions against temp files, with `LEDGER`, `LANE`, `HISTORY`, `SHARDS` and `COVERAGE`
  repointed at a scratch directory first. `cleanup` and `pick_model` were read only.
* The probes DID leave counters in the shared failure ledger, because `silence.note` is
  global: `silent:overwatch.py:load:JSONDecodeError` +1,
  `silent:dashboard.py:movement-corrupt-reset:{JSONDecodeError,ValueError}` +1 each,
  `silent:dashboard.py:movement:AttributeError` +1, and one
  `silent:sweep_plan.py:record-aggregate-merge-failed:FileNotFoundError` (23:37-23:40 on
  2026-08-28). They are audit artifacts, not production faults, and I have left them in place
  rather than editing the ledger.
* Related, and worth a sentence because it looks alarming in `state/failures.json`:
  `silent:sweep_plan.py:record-write-json-fallback:RuntimeError` carries the sample
  `RuntimeError('boom')` timestamped 23:01:17 today, and `silent:sweep_plan.py:shard-write-denied`
  is from the same minute. Those are another sweep-37 batch's injected probe, not a real denied
  shard write. `state/sweep_shards/` holds only legitimate run36/run37 shards.

---

## Orders filed (found_by `sweep37-batch15`)

| id | severity | code | where |
|---|---|---|---|
| 302c7da84032 | MAJOR | overwatch-ledger-shape-bypasses-quarantine | src/overwatch.py:167 |
| c6f64c1424fa | MAJOR | overwatch-verify-open-stamps-unanswered | src/overwatch.py:559 |
| d316c46b67bd | MAJOR | gpu-lane-cannot-arbitrate-waits-full-ceiling | src/gpu_lane.py:326 |
| f42c55355431 | MINOR | sweep-plan-modules-misses-src-subdirs | src/sweep_plan.py:45 |
| 6794cb447987 | MINOR | sweep-plan-record-fallback-can-still-raise | src/sweep_plan.py:226 |
| e8e095597f74 | MINOR | watch-md-truncates-findings-silently | src/overwatch.py:654 |
| 97373afb2d5b | MINOR | overwatch-excludes-itself-unstated | src/overwatch.py:747 |
| d61b06dbe66d | MINOR | dashboard-num-linenumber-tag-drifted | src/dashboard.py:77 |
| 62286a6c018a | MINOR | dashboard-movement-history-wedge-nondict | src/dashboard.py:396 |
| 6c24b2297f40 | MINOR | retry-synthesis-merge-exits-zero-on-denial | src/retry_synthesis.py:225 |
| 2b83e058be3f | MINOR | cleanup-thin-mark-not-idempotent | src/cleanup.py:195 |

The six INFO/cosmetic items above were NOT filed as orders; they are recorded here.

Coverage recorded: `sweep_plan.record('run37', [the eight modules], batch=15)` landed with no
denial. `covered_by('run37')` now names all eight; run37 stands at 72 of 114 modules with 42
still to be recorded by other batches.

The order-filing script is kept beside this audit as `file_batch15_orders.py`.
