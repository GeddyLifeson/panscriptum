# AUDIT — batch 04, run29

Modules: `src/foreman.py`, `src/endpoint.py`, `src/context_budget.py`, `src/burgs.py`,
`src/halo.py`, `src/module_index.py`. Every line of each was read. Reproductions were run with
`PYTHONIOENCODING=utf-8 C:/Users/imarl/miniconda3/python.exe`, driver scripts kept in scratch
space, no file under `src/` was edited.

Severity key: CRITICAL/HIGH/MEDIUM/LOW. Confidence key: REPRODUCED / VERIFIED-BY-READING /
HYPOTHESIS.

---

## endpoint.py

### 1. [HIGH] `_save()`/`_load()` use a fixed-name temp file and an un-retried `os.replace` — REPRODUCED data corruption and full-cache wipe under concurrent writers

`src/endpoint.py:83-94` (`_save`) and `src/endpoint.py:70-80` (`_load`):

```python
def _save():
    with _LOCK:
        if _MEM is None:
            return
        try:
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            tmp = CACHE + ".tmp"                      # <- fixed name, no PID/thread
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(_MEM, f, indent=1, sort_keys=True)
            os.replace(tmp, CACHE)                     # <- no retry on PermissionError
        except Exception:
            silence.note("endpoint.py:save")            # <- silently dropped, no retry
```

```python
def _load():
    ...
        try:
            with open(CACHE, encoding="utf-8") as f:
                _MEM = json.load(f)
        except Exception:
            silence.note("endpoint.py:load")
            _MEM = {}                                    # <- whole cache reset on ANY failure
```

`_LOCK` is a `threading.Lock`, which only serialises callers **within one process**
(lens 6: "`threading.Lock` used where processes … contend"). `endpoint.py` is imported and its
`detect()`/`_save()` path is exercised by every separate process that probes a host —
`hostcheck.py --workers N` (which `foreman.adopt_hosts` launches), `feats.py`, `scout.py`, and
any other job reading a wiki. Two such processes writing `data/ENDPOINTS.json` around the same
time both target the same `ENDPOINTS.json.tmp` path.

Compare to `silence.write_json` (`src/silence.py:250-269`), whose own docstring says: *"Found by
the 2026-08-25 comprehensive sweep: TWELVE call sites across ten modules were writing shared
`data/` and `state/` files with a bare `open(path, 'w')` + `json.dump` … THE TMP NAME CARRIES PID
AND THREAD, which the older hand-rolled `path + '.tmp'` sites did not. Two writers of the same
path otherwise collide on the temp file itself, and the loser can replace the winner's target
with a partial file."* This is exactly `endpoint.py:_save()`'s pattern, and it was **not**
migrated — even though the very same module's own `register()` function (`endpoint.py:356-394`,
for `SOURCE_PAGES.json`) *was* fixed and correctly calls `silence.write_json`. The inconsistency
is within one file: one shared-state writer in `endpoint.py` got the 2026-08-25 fix, the other
did not.

**Reproduced.** Driver script (kept at
`…/scratchpad/repro_endpoint_race.py`, not in the repo): 8 OS processes, each looping 60 times,
each building its own `_MEM` and calling the real `endpoint._save()` against a shared scratch
`CACHE` path (never touching the real `data/ENDPOINTS.json`), then immediately trying to
`json.load()` the file back (what any other process's `_load()` would do next). Result across
480 concurrent `_save()` calls:

```
PermissionError: [Errno 13] Permission denied: '...\ENDPOINTS_race_test.json'   (repeated, once per worker)
9 corruption/error events across 8 workers x 60 iters (480 _save calls)
  worker7 iter0: landed CACHE file is NOT VALID JSON (torn write): Expecting property name enclosed in double quotes: line 182 column 1 (char 8040)
  worker7 iter1: landed CACHE file is NOT VALID JSON (torn write): Extra data: line 352 column 2 (char 15492)
  ...
```

Two distinct failure modes both fired: (a) `os.replace` raising `PermissionError` because another
worker had the shared `.tmp` path open at the same instant — swallowed silently by `_save()`'s
broad `except Exception`, no retry, write simply lost that round; (b) an actually **corrupted,
unparseable JSON file landing on disk** (a torn/interleaved write from two processes writing the
same `.tmp` name), which the next `_load()` anywhere in the project would hit and respond to by
**silently resetting the entire endpoint cache to `{}`** — discarding every previously-probed
host verdict (the module's own docstring: *"2,958 dead entries are on file"* — a full re-probe of
that scale after one bad race). This is both a concurrency race (lens 6) and a swallowed failure
on shared state (lens 2): the exact defect class `silence.write_json` exists to close, still open
in this file.

**Fix direction (for the supervisor):** replace `_save()`'s body with
`silence.write_json(CACHE, _MEM, sort_keys=True)`, matching `register()` in the same file.

### 2. [LOW-MEDIUM] `fetch_raw` still tells its callers "refused" and "absent" apart only in the *ledger*, not in the data — VERIFIED-BY-READING (self-documented partial fix)

`src/endpoint.py:206-221`. The `except urllib.error.HTTPError` branch now classifies 404/410 as
`endpoint.py:fetch_raw-absent` and everything else (429, 403, 500…) as
`endpoint.py:fetch_raw-refused-<code>` for `silence.note`'s sake — but **both branches still
`return t, None`**. The docstring is explicit that this is a conscious partial fix: *"The
signature is unchanged (callers in feats.py and hostcheck.py read only presence), so the fix is
to make the two cases legible in the ledger."* That means a host that is merely rate-limiting a
raw-mode probe (429) or briefly 500ing still gets every title in the batch filed as "this page
does not exist" by any caller of `fetch_raw`/`exists_raw`, exactly the "transient wearing the
face of settled fact" failure the same docstring names as BUGS m15's shape. Only the `silence`
ledger, not the actual host-adoption or coverage data, can currently tell the difference. Flagging
because the consequence (a rate-limited host being recorded as *not carrying* a source) can feed
real downstream decisions (`hostcheck.py --adopt`), not because the fix is wrong as far as it
goes.

### No other issues found in `detect()`, `api_url()`, `raw_url()`, `html_text()`, `fetch_html()`, `main()`.
`detect()`'s DEAD_TTL re-probe logic, the API-then-raw fallback order, and the UA override for
dandwiki were all read closely and match their docstrings.

---

## foreman.py

### 3. [HIGH] `attempt_patch()` writes live source code with a plain truncating `open(path, "w")` — the one write in this file that is *not* atomic — VERIFIED-BY-READING

`src/foreman.py:989-1002`:

```python
os.makedirs(BACKUPS, exist_ok=True)
backup = os.path.join(BACKUPS, f"{module}.{int(time.time())}.py")
shutil.copy2(path, backup)
try:
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    lines[start:end] = [new]
    with open(path, "w", encoding="utf-8") as f:      # <- truncate-then-fill, no .tmp/replace
        f.writelines(lines)
    good, why = _checks_pass(module)
    if not good:
        shutil.copy2(backup, path)
        return {"ok": False, "why": f"reverted: {why}", "backup": backup}
    return {"ok": True, "why": "patched and verified", "delta": changed, "backup": backup}
except Exception as e:
    ...
    try:
        shutil.copy2(backup, path)
    except Exception:
        ...
```

Every *other* shared write in this same file — `POOL_PROOF.json`, `state/failures.json`,
`state/failures_archive.json`, `data/OVERWATCH.json`, `FOR_OWNER.md`, `data/FOREMAN.json`,
`state/OLLAMA_RESTARTS.json` — goes through a `.tmp` file plus `silence.replace_retry`, and the
module's own comments repeatedly insist on checking the return value ("run #19" appears six
times in this file for exactly that reason). The single riskiest write of all — a model's
unverified patch landing directly in `src/*.py`, which every other process (including
`_checks_pass`'s own `import <module>` a few lines later) will read within seconds — is the one
write that skips that discipline entirely.

If the process is killed **between** the two `open()` calls — e.g. by a Windows shutdown, by the
user, or in principle by this very file's own `kill_duplicate_jobs`/`kill_stalled_job` sending
SIGTERM to a wedged sibling — `path` is left truncated or half-written, `except Exception` is
never reached, the `except`'s own restore-from-`backup` never runs, and `src/<module>.py` stays
on disk in a broken, unimportable state with no built-in recovery. That is precisely the failure
class this file's own `attempt_patch` comment at line 1005 calls "the worst place in the tree for
an optimistic report" — but for the *write*, not the *revert*, no such guard exists.

I did not reproduce this by actually corrupting a `src/` file (out of scope per the task's rules,
and unsafe against a live project file); the non-atomicity is directly visible in the code and
the contrast with every sibling write in the same module is exact.

**Fix direction:** write the patched `lines` to `path + ".tmp"` then `silence.replace_retry(path
+ ".tmp", path)`, checking the return value before running `_checks_pass`.

### 4. [MEDIUM] `DENYLIST` is silently doing double duty — model-lane edit exclusion *and* process-dedup exclusion — VERIFIED-BY-READING, judgement call flagged for the supervisor

`DENYLIST = {"foreman", "silence", "health", "allsweep", "estate", "standards", "verify_math"}`
is introduced at `foreman.py:90` and documented only as: *"Files a model may never edit. Each is
either the thing that would have to be working to detect a bad patch, or the thing doing the
patching."* — a MODEL-lane concept.

It is then reused, unremarked, in `kill_duplicate_jobs()` at `foreman.py:498`:

```python
if job in ("overnight", "autostart"):
    continue
if p == os.getpid() or job in DENYLIST:
    continue
```

This means a duplicate `foreman` **process** (not just a duplicate module edit) can never be
reaped by the "one instance of each job" remedy, because `job == "foreman"` is always skipped via
`DENYLIST`. The docstring immediately above spends a full paragraph on exactly the scenario of
two duplicate foreman processes fighting ("two supervisors spawned two foremen, and each
foreman … shot the other stack's members … The stacks killed each other every three minutes for
half an hour") and argues self-preservation is deliberate ("a repair tool that can kill its own
dispatcher is a repair tool that can dismantle the system it repairs") — so exempting *foreman
itself* may well be intentional. But the mechanism used to encode that decision is a constant
whose one documented purpose is unrelated (which files a model may edit), and the other six
names on it (`silence`, `health`, `allsweep`, `estate`, `standards`, `verify_math`) get the same
kill-exemption with **no stated reason** tied to process duplication at all — if any of those
ever runs as its own long-lived process, a genuine duplicate of it would silently never be
cleaned up by this remedy, and nothing at the call site says that trade-off was considered. Worth
the supervisor's judgement: either split this into two separately-justified constants, or add a
comment at the `kill_duplicate_jobs` site explaining why `DENYLIST` is the correct set to exempt
from dedup too.

### 5. [LOW] Five `silence.note()` tags carry stale line numbers, defeating `triage_swallowed`'s own stated precision — REPRODUCED (grep-verified)

```
foreman.py:661   silence.note("foreman.py:497")    -- off by 164 lines
foreman.py:827   silence.note("foreman.py:595")    -- off by 232 lines
foreman.py:1099  silence.note("foreman.py:824")    -- off by 275 lines
foreman.py:1242  silence.note("foreman.py:942")    -- off by 300 lines
foreman.py:1275  silence.note("foreman.py:967")    -- off by 308 lines
```

`triage_swallowed()` (`foreman.py:214-283`) exists specifically because, in its own words,
*"the class names the module and the line, and a class that is 90% of the total is a single fault
wearing thousands of hats."* These five note-call sites were evidently tagged once and then the
file grew around them without the tags being updated, so for any failure logged under these five
class names, the "line" half of that promise is now false — a human chasing the top class in
`triage_swallowed`'s output for one of these five would be sent to the wrong function. Purely
cosmetic to program behaviour (the ledger still counts correctly), but it directly undermines the
one feature `triage_swallowed` advertises. Lens 7 (comment/design claim contradicted by the code
that's supposed to satisfy it).

### 6. [LOW] Dry-run preview does not reflect what a live run would actually do

`round_once()`, `foreman.py:1156-1161`: in dry mode, `for fn in remedies:` prints **every**
remedy in a standard's list as `"would run {fn.__name__}"`, via `continue` before any execution
logic. In a live run (`--go`), the same loop stops at the first remedy that returns `did=True`
(the `break` at `foreman.py:1207`, guarded by the `always` exception already documented in the
file). So for any standard with more than one remedy (e.g. `"calls that succeed": [clear_learned_
caps, reprove_pool]`), a dry run prints both remedies as "would run" when a real run would very
likely only execute the first. Minor, display-only, but a dry-run whose whole purpose is to
preview the live behaviour should not overstate what will execute.

### No other issues found in `clear_learned_caps`, `reprove_pool`, `adopt_hosts`, `scout_hostless`,
`rerun_roll`, `triage_swallowed`'s archive logic, `recatalogue_models`, `refresh_coverage`,
`_restart_horizon`, `restart_reader`, `kill_stalled_job`'s owner-resolution, `_fandom_reachable`,
`run_catalogue_gap`, `run_character_sweep`, `run_completeness_audit`, `run_charter_regression`,
`restart_ollama`'s 30-minute rate limit, `_function_source`, `_literals`, `lines_changed`,
`regex_touched`, `_checks_pass`'s verify_math/allsweep parsing, `_retire`, `_pool_has_room`,
`owner_queue`, or `main()`'s loop guard. All of these carry extensive documentation of prior
fixes (run #19, run #26, m15, m18) and reading them against their own claims found the claims
true of the current code.

---

## burgs.py

### 7. [HIGH] `main()` keys the per-world output by `w["designation"]`; duplicate designations silently drop worlds from a write the code itself labels "every world; Hard Rule 0" — REPRODUCED

`src/burgs.py:187-201`:

```python
worlds = WS.build_all()          # every world; Hard Rule 0
...
total = 0
per_world = {}
for w in worlds:
    seed = AS.map_seed(w["seed"])
    bs = burgs_for(seed, w["features"])
    per_world[w["designation"]] = bs      # <- dict keyed by designation, last write wins
    total += len(bs)
```

`json.dump(per_world, f, ...)` at line 227 then writes whatever survived the dict. **Reproduced**
against the live `worldseed.build_all()`:

```
worlds processed: 4440
per_world keys:   4368
total burgs:      70,520,920
```

`WS.build_all()` returns 4440 world records, but 72 of them collapse into 69 designation groups
that share a string (e.g. `'Acquisitions Incorporated::Nentir Vale'` appears twice — and in this
case with the *identical* seed `135859882` both times, confirmed by direct inspection). Because
`per_world` is a plain dict keyed by `designation`, the later occurrence in iteration order
silently overwrites the earlier one, and 72 worlds' entire settlement rolls never make it into
`per_world` at all — even though the loop iterated over all 4440 and `total` (accumulated before
the overwrite) counts burgs from worlds that are no longer present in the structure actually
written to disk. This is precisely the shape Hard Rule 0 forbids: *"a cap does not fail, it
returns a smaller universe wearing the same shape as the real one."* No slice or limit appears
anywhere in this code path — the loss is a keying bug, not a truncation, but the *effect* on the
written data is identical to one.

The root duplication (why `worldseed.build_all()` emits two records with the same designation and
same seed) sits in `worldseed.py`, which is outside this batch's module list — flagging it here
because the visible harm lands in `burgs.py`'s output. Fix direction for `burgs.py` itself: key
`per_world` by something guaranteed unique per emitted record (e.g. `(w["designation"], i)` or the
loop index), so a future duplicate at the source is preserved rather than silently dropped, and
raise/log instead of overwriting when a key collision is detected.

### 8. [MEDIUM] The `--write` sample message is false for the current code, and the current code would try to serialise ~70.5 million records to one JSON file — VERIFIED-BY-READING + REPRODUCED (arithmetic/timing)

`src/burgs.py:225-230`:

```python
if args.write:
    p = os.path.join(HERE, "data", "BURGS_SAMPLE.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(per_world, f, indent=2, ensure_ascii=False)
    print(f"\nwrote {p} (sample of 50 worlds; the rest regenerate on demand)")
```

No slicing of `worlds` or `per_world` happens before this write (confirmed by `grep -n
"\[:" src/burgs.py` — the only slices in the file are the printed CLI sample table and a
docstring hash-truncate, both display-only). The on-disk `data/BURGS_SAMPLE.json` (dated 2026-08-
20, 50 worlds / 2,180 burgs) was evidently produced by an earlier version of this script that did
slice to 50 worlds; that limit has since been removed (correctly, per Hard Rule 0), but the print
string and the filename were never updated to match, so the message is now a straightforward
false claim about what the code just did.

More importantly, re-running `--write` today is not a "sample" operation at all: it is
attempting to write **70,520,920** burg records (measured directly — `burg_count()` alone, summed
over all 4440 worlds via `_stream`/rank-size arithmetic, before any JSON encoding) to a single
`indent=2` JSON file. Distribution (measured):

```
min 13   median 962   p90 43,430   p99 178,516   max 193,089 burgs in one world
worlds with >100,000 burgs: 267
worlds with >10,000 burgs:  1,072
```

Just computing this in pure Python (no I/O) took over two minutes in the reproduction run; the
full `json.dump` on top of it was not attempted here because it would very likely exhaust disk
space or run for a very long time, and this batch's brief is "propose, don't touch production
data" beyond what's needed to demonstrate the bug. Whether uncapped settlement counts of this
scale are themselves a modelling defect in `burg_count`/`largest_city` (a single "thriving
spacefaring" world generating 193,089 named settlements) is a judgement call for whoever owns the
rank-size model; flagging here because it makes the `--write` flag, whose own output filename and
message claim to produce a lightweight "sample", operationally closer to a footgun than a
convenience.

### No other issues found in `_stream`, `HAMLET_FLOOR`, `burg_count`, `largest_city`, `classify`,
`burgs_for`'s coastal-bias logic, or `burg_link`. The rank-size derivation, the era/condition
factor tables, and the "population derives burg count, not the reverse" design all check out
against their own stated math.

---

## context_budget.py

Read in full; no correctness bugs, swallowed failures, caps, tautological checks, writer-contract
issues, races, or comment/code contradictions found. This module is unusually well self-audited
already (`m46`/`m52`, the 2026-08-24 measured-ratio pass) and every claim in its docstring was
checked against the code:

- `split_system_prompt`'s heading-based split: the heading `"THE ENTRY TEMPLATE"` was confirmed
  present at `prompts/system_style.txt:103`, matching the docstring's claimed line range
  (103-245) and the fallback-to-whole-file behaviour when absent is a documented, deliberate
  degrade rather than a silent one.
- `content_budget_chars`'s "return a number that can be zero or negative and never clamp it" is
  honoured — no clamping code path exists.
- `assert_fits`'s `ContextOverflow` is a real `raise`, not a logged-and-continued path.
- The two calibration corrections (`JOB_OVERHEAD_CHARS`, `METADATA_INFLATION`) are applied in the
  direction the comments claim (both push the budget down, not up).

One micro-inefficiency, not a finding: `content_budget_chars` builds a literal `"x" *
int(scaffold_chars)` string purely to measure its length via `estimate_prose_tokens`, which only
uses `len(text)`. Harmless (tens of KB at most) but could pass the integer directly.

---

## halo.py

Read in full, including the ROSTER's axis-score data. One coincidence was investigated and
**ruled out** as a bug: The Precursors and The Gravemind both compute to the identical `𝔄 M6.84 ±
0.06`, despite having entirely different per-axis scores. Hand-computing the weighted composite
against `assay.WEIGHTS` (`ruin` 0.145, `continuity` 0.109, `celerity` 0.087, `transgression`
0.131, etc.) for both rosters independently gives 8.427 and 8.4145 respectively — both round to
decimal `.84` under the module's weighting scheme. This is a genuine, if striking, coincidence in
the input data the ROSTER author chose, not a bug in `compute()`, `assay.assay()`'s clamping (the
`_dec >= 1.0` ceiling logic in `assay.py:439-444` never triggers here — composite tops out well
under 10 for both), or in `halo.py`'s own arithmetic. `assay.py` is outside this batch and was not
otherwise audited.

No other issues found in `compute()`'s per-entity assay assembly, the `main()` ranking
(`A.LADDER.index(...) + decimal`), the `--full` display truncation of `cited` text to 54 chars
(confirmed DISPLAY-only — `compute()`'s own `"cited"` field and the written `HALO_ASSAYS.json`
carry the full, untruncated citation text), or the atomic `silence.write_json` call at the end.

---

## module_index.py

Read in full. No correctness bugs, caps, or writer-contract issues. The hardcoded `GROUPS` module
lists are a curation aid, not a data restriction — any module in `src/*.py` not named in `GROUPS`
still appears, filed under "Everything else" (`module_index.py:68-74`), so no module is ever
silently dropped from the generated index. `first_line()`'s broad `except Exception` only ever
degrades a single row's text to `"(unparseable)"`; it does not drop the row or abort the run.

---

## Summary of files/lines touched by this audit (read-only)

- `C:\Users\imarl\panscriptum-library-kit\src\foreman.py` (1287 lines, full read)
- `C:\Users\imarl\panscriptum-library-kit\src\endpoint.py` (395 lines, full read)
- `C:\Users\imarl\panscriptum-library-kit\src\context_budget.py` (278 lines, full read)
- `C:\Users\imarl\panscriptum-library-kit\src\burgs.py` (235 lines, full read)
- `C:\Users\imarl\panscriptum-library-kit\src\halo.py` (178 lines, full read)
- `C:\Users\imarl\panscriptum-library-kit\src\module_index.py` (83 lines, full read)
- `C:\Users\imarl\panscriptum-library-kit\src\silence.py` (partial read: `replace_retry`,
  `write_json`, for corroborating finding 1)
- `C:\Users\imarl\panscriptum-library-kit\src\assay.py` (partial read: `assay()`, `WEIGHTS`,
  `LADDER`, to rule out the halo.py coincidence)
- `C:\Users\imarl\panscriptum-library-kit\src\worldseed.py` (queried via `build_all()` only, not
  read line-by-line — out of batch scope, flagged as the likely root cause of finding 7)

No file under `src/` was modified. Reproduction driver scripts were written to
`C:\Users\imarl\AppData\Local\Temp\claude\...\scratchpad\` only, against scratch data paths, never
against `data/ENDPOINTS.json` or `data/BURGS_SAMPLE.json`.
