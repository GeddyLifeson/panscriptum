# AUDIT batch07 — sweep30

Files: `src/magnitude.py`, `src/completeness.py`, `src/pick_model.py`, `src/weave_index.py`,
`src/runguard.py`, `src/catalogue_models.py`, `src/compress_store.py`

Method: every line read top to bottom in all 7 files. Reproductions run against scratch temp
dirs under `C:\Users\imarl\AppData\Local\Temp\claude\...\scratchpad\rg_test\` — never against
repo state. No `--calibrate`, no `generate`/`prose`, no repo file edited. `state/`, `data/` in
the real repo were never touched by any test in this audit.

No committed secrets found in any of the 7 files (checked for API-key/token/password patterns).

---

## 1. `src/runguard.py` — HIGH, REPRODUCED (the single most important item in the batch)

### Finding 1.1 — `_land()` uses a fixed-name temp file shared by every concurrent claimant
**`runguard.py:73`** — `tmp = path + ".tmp"`. Every call to `claim()`, `beat()`, and `release()`
writes to this exact same temp path. This is the identical anti-pattern `silence.write_json`'s
own docstring (`silence.py:262-265`) was written to eliminate project-wide ("Two writers of the
same path otherwise collide on the temp file itself, and the loser can replace the winner's
target with a partial file") — but `runguard._land()` does not use `silence.write_json`; it
hand-rolls the unsafe version right next to the module whose entire job is exclusive claiming.

### Finding 1.2 — `claim()` has a classic read-then-write TOCTOU with no lock and no atomic
compare-and-swap
**`runguard.py:98-121`**. `claim()` reads `prior` (line 105), decides locally that no live
predecessor exists, then writes its own record via `_land()`. Nothing between the read and the
write is atomic or exclusive — `os.replace` makes the *file landing* atomic but does nothing to
prevent two processes from both reading "free" and both proceeding to land a record, each
convinced it is the sole claimant.

**REPRODUCED.** Two-way concurrent `claim()` against a fresh scratch `GUARD` file, 200 trials:
- **double-claim rate: 125/200 = 62.5%** (both threads returned `ok=True` — exactly the shape
  m27 exists to prevent, now happening on the "fixed" module)
- **uncaught `FileNotFoundError` crash rate: 75/400 calls = 18.8%** — see finding 1.3

At higher concurrency (40 threads/trial, 20 trials) the double/multi-claim rate rose to
**19/20 trials (95%)** with as many as 13 of 18 completing threads claiming simultaneously, and
**621 uncaught crashes** were thrown across the run.

Repro script: `scratchpad/rg_test/test_claim_race.py` and `test_claim_race2.py` (both call
`runguard.claim()` directly with `path=` pointed at a scratch file — the real
`state/MAINTENANCE_RUN.json` was never touched).

### Finding 1.3 — the crash: `_land()`'s call to `replace_retry` is OUTSIDE its own try/except,
and `replace_retry` only catches `PermissionError`
**`runguard.py:72-80`**:
```python
def _land(rec, path):
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=2)
    except Exception:
        silence.note("runguard._land")
        return False
    return silence.replace_retry(tmp, path)   # <-- not inside the try
```
When two claimants race on the shared `tmp` name (finding 1.1), one of them can find its own
`tmp` file already consumed by the other's `os.replace` by the time it calls
`silence.replace_retry(tmp, path)` — `os.replace` then raises `FileNotFoundError: [WinError 2]`.
`silence.replace_retry` (`silence.py:225-238`) only catches `PermissionError` in its retry loop;
`FileNotFoundError` is not caught there either, and propagates all the way out of `claim()` /
`beat()` / `release()` uncaught. **This is exactly the crash the docstring's opening story (m27,
"the guard was checked but the refresh never was") set out to end, reintroduced by the write path
it left unguarded.** Under 2-way contention this fired on 18.8% of calls in the reproduction
above; under 40-way contention it fired hundreds of times per run.

Severity: **HIGH**. Fix: give every writer a unique temp name (pid+thread, exactly the pattern
`silence.write_json` already establishes) and route `_land()` through `silence.write_json`
instead of hand-rolling the write; and/or hold an OS-level exclusive lock (e.g. `msvcrt.locking`
or a lockfile) across the read-decide-write section of `claim()` so the TOCTOU closes entirely —
a unique temp name alone fixes the crash but not the double-claim, since two processes can still
each observe "free" and each successfully land a record (whichever lands last wins, silently,
and the loser's `ok=True` is a lie).

### Finding 1.4 — `beat()` and `release()` share the same fixed-temp hazard
**`runguard.py:124-172`**. Both call `_land()` and inherit findings 1.1/1.3. Lower practical
risk than `claim()` because they're gated by an ownership check first (`owner != agent`), but if
two *different* processes both currently and correctly believe they own the same record (which
finding 1.2 shows can happen) and both heartbeat concurrently, they hit the identical fixed-tmp
race.

### Clean in this file
- `holder_is_live()`, `read()`'s FileNotFoundError-vs-Exception split, and the ownership checks
  in `beat()`/`release()` are all correctly reasoned and not tautological.
- The m27 fix itself (refusing to refresh/close a record you don't own) is real and correctly
  implemented — the regression here is a different bug (the write path), not a reopening of m27.
- No callers of `runguard` exist anywhere in `src/` except `local_agent.py` and
  `verify_math.py` (grepped); `magnitude.py`'s own `run_batch()` and `generate.py` do **not**
  call `runguard.claim()` at all (see magnitude.py finding 5 below).

---

## 2. `src/magnitude.py`

### Finding 2.1 — HIGH, REPRODUCED — `_split_gate()` omits Guard 3 (SUBJECT), confirming the
open item exactly
**`magnitude.py:572-590`**. `verify()` (the one-shot path, `:335-400`) applies five guards:
verbatim, relevance (`AXIS_RE`), subject (`P._PATIENT` / `_HANDOFF`), saturation, quantity.
`_split_gate()` (the split path used by design for the library's **largest, most-evidenced**
entities — anything whose one-shot prompt exceeds `ONE_SHOT_MAX` = 30,000 chars, `:448`) applies
only verbatim containment. Its docstring claims relevance is "by construction" (true, because
each axis's candidate list is pre-bucketed by `F.by_axis`) but says nothing about subject, and
the code contains no call to `P._PATIENT` or `_HANDOFF` anywhere in the function.

**REPRODUCED** with the file's own motivating example. Script:
`scratchpad/rg_test/test_split_gate.py`. Fed the identical sentence
`"Goku used the button to summon Future Zeno, who immediately proceeded to erase the rogue Kai."`
into both gates as a citation for the `transgression` axis at score 9.0:

```
=== one-shot verify() ===
transgression score: unestimable
rejects: [('transgression', 'entity is not the actor: Goku used the button to summon Future Zeno, who immediately ')]

=== split path _split_gate() ===
transgression score: 9.0
rejects: []
```

`verify()` correctly rejects the sentence (guard 3 fires, exactly as designed). `_split_gate()`
accepts it at face value, zero rejections. Since the split path is the ONLY path ever used for
the library's largest entities (Jace Beleren-scale evidence, ~140k chars, explicitly named in
the file's own docstring at `:456-462`), this means the entities most likely to have a
Zeno-shaped handoff sentence in their evidence are also the ones scored by the gate that cannot
catch it.

Severity: **HIGH**. Fix: add the same `P._PATIENT.search(text) or _HANDOFF.search(text)` check
to `_split_gate()`'s accept branch, exactly as `verify()` does at `:392-395`.

### Finding 2.2 — CLEAN / open item REFUTED — `calibrate()`'s partial-pass handling
**`magnitude.py:782-901`**. Re-read against the concern that a resumable calibration would let a
HIGH standard hold on partial data. Current code:
- `_land(rows, complete)` (`:837-850`) stamps `"at"` **only** when `complete=True`
  (`:843-844`), and every incremental checkpoint inside the loop calls `_land(rows, False)`
  (`:880`, `:892`) — `complete` is never true until every benchmark has a row.
- The resume guard (`:822-833`) only resumes a prior pass that is itself `not old.get("complete")`,
  from the same model, and younger than 26h — an abandoned or foreign-model pass is discarded and
  restarted, matching the docstring exactly.
- `main()` calls `calibrate()` and treats its return (`band_hits`) as the exit-code signal;
  nothing reads the file mid-pass and reports it as settled.

This concern is **addressed in the current source** — not a live bug. (Whether the downstream
consumer, `standards.py`, correctly reads `complete: false` as "in progress" rather than as an
age is outside this batch; the producer side here is correct.)

### Finding 2.3 — HYPOTHESIS, not tested — the same fixed-temp cross-process hazard as
runguard, present in `run_batch()`'s own write path
**`magnitude.py:1050-1066`**:
```python
tmp = OUT + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(done, f, ensure_ascii=False)
for attempt in range(5):
    try:
        os.replace(tmp, OUT)
        break
    except PermissionError:
        ...
```
This block IS correctly serialized against races **within one process** — it sits inside
`with lock:` in `work()`, and `lock` is a single `threading.Lock()` shared by every worker in
that `ThreadPoolExecutor`. So intra-process this is safe. But the temp name is still fixed
(`ASSAYS.json.tmp`), and only `PermissionError` is retried — exactly the same shape proven to
crash in runguard.py finding 1.3. If a **second, independent `magnitude.py --batch` process**
is ever launched concurrently against the same `data/ASSAYS.json` (accidental double-launch, a
foreman overlap, a retry-storm) the two processes' fixed `.tmp` names collide with no
cross-process lock at all, and a `FileNotFoundError` from the losing process's `os.replace`
would propagate out of `work()`, through `ex.map`, and crash the entire batch (killing all
still-queued entities for that invocation, though already-completed ones remain persisted).
Note that `magnitude.py` never calls `runguard.claim()` — nothing in this file enforces
single-writer discipline against a second invocation of itself. Not reproduced here (would
require two real OS processes plus mocking `assay_entity`/Ollama, which is out of scope for a
read-only audit), but the mechanism is identical to the proven runguard.py bug and the
docstring at `:1053-1057` already acknowledges *part* of the hazard (the `PermissionError`
case) without covering `FileNotFoundError`.

Severity: **MEDIUM** (real mechanism, unconfirmed real-world trigger frequency). Fix: either
route through `silence.write_json` (unique temp per writer) or gate `run_batch()` behind
`runguard.claim()`.

### Finding 2.4 — LOW / style — `except FileNotFoundError: pass` at `:832` doesn't follow this
project's own "silence-exempt" marking convention
```python
except FileNotFoundError:
    pass
except Exception:
    silence.note("magnitude.py:calibrate-resume")
```
Functionally correct (no prior `CHARTER_REGRESSION.json` on the first run is the normal state,
same as `completeness.py`'s identical case). But `completeness.py` marks its equivalent cases
with `_ = "silence-exempt: ..."` specifically so the token `silence` appears in the handler body
and `silence.py`'s own `_handlers()` AST audit (which greps for `health/record/log/print/raise/
swallow/silence/LEDGER` inside the handler) recognizes it as deliberate rather than flagging it
as a silent handler. This bare `pass` will be counted as SILENT by `python src/silence.py`
despite being legitimate — a false positive in the project's own audit tooling, easily fixed by
adding the same one-line marker used elsewhere in this exact file.

### Clean in this file
- Guard 1 (verbatim, empty-citation) at `:356-376` is exactly as documented — the historical
  "empty citation always passes" bug (run #27) is genuinely fixed; `if not cn: rejects.append(...)`
  fires before the `next(...)` search, so an empty citation can no longer fall through to an
  arbitrary first-mined-feat match.
- `candidates()` (`:415-430`) and `compose()` (`:524-569`) correctly never truncate:
  `candidates(ev, cap=None)` is only ever called with `cap` unset (`:595`), and `compose()` is
  only ever called with `budget=None` (`:610`), so `dropped` is provably always 0 — matches the
  inline comment at `:749`.
- `_split_assay()`'s per-axis slicing (`:451-521`) iterates every candidate row with no cap
  (`while i < len(rows)`), consistent with Hard Rule 0.
- `queue(host=None, limit=None)`'s `[:limit]` (`:931`) is an explicit opt-in CLI flag defaulting
  to `None` (unlimited), the same accepted shape used elsewhere in this codebase for spot-checks
  — not a silent violation.
- `saturated()` (`:409-412`) is not tautological: requires `len(nums) >= 6` (guards the
  `min()` call) and a real ceiling check.
- `pool_ready()`'s resolve-once-before-any-worker-starts pattern is sound and matches its stated
  rationale.
- No committed secrets.

---

## 3. `src/completeness.py`

### Finding 3.1 — MEDIUM, REPRODUCED (partially) — `category_size_probe()`'s disk cache write
uses a fixed-name temp shared across concurrent worker threads
**`completeness.py:112-119`**:
```python
tmp = _CS_CACHE_P + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(cache, f)
silence.replace_retry(tmp, _CS_CACHE_P)
```
`audit()` runs `work()` (which calls `category_size_probe()` for every probe) inside
`ThreadPoolExecutor(max_workers=workers)` (default 6, `:238`, `:360`) — multiple sources are
probed concurrently, and every thread that takes a cache miss writes to the **same**
`state/category_sizes.json.tmp` path. This is the identical anti-pattern as runguard.py finding
1.1, hand-rolled instead of routed through `silence.write_json`.

**Tested** (`scratchpad/rg_test/test_completeness_cache_race.py`, 30 threads/trial x 15 trials,
`ws._api` mocked so no real network/Fandom traffic occurred): **0 uncaught exceptions**. Unlike
`runguard._land()`, this call site wraps the ENTIRE write-then-replace sequence (including the
`replace_retry` call) inside one `try/except Exception: silence.note(...)` block
(`:112-118`), so a `FileNotFoundError` from a losing `os.replace` in this race is caught and
recorded, not raised. Net effect: the race is real (two threads can genuinely stomp each other's
`tmp` file) but the consequence is a **silently-dropped-but-observed** cache write (recorded via
`silence.note`, satisfying this project's own silence discipline) rather than a crash — the
worst outcome is one thread's category-size lookup gets re-fetched from the network next call,
which is cheap and does not corrupt `COMPLETENESS.json` itself (that file's own writer, `land()`,
is separately and correctly hardened — see below). Downgraded from HIGH to MEDIUM because the
blast radius is a disposable 12h TTL cache, not the audit's actual output.

Fix: same as runguard — unique temp name per writer, or route through `silence.write_json`.

### Clean in this file
- `land()` (`:369-434`) is the standout of the batch: three independently-reasoned guards
  (refuse-on-empty, refuse-on->50%-shrink via `SHRINK_FLOOR`, and check `replace_retry`'s return
  value rather than discarding it) each targeting a distinct, previously-real failure mode
  (2026-08-24 incidents cited by file/line in its own docstring), and each one is loud on stderr
  with a non-zero exit rather than silent. This is the two-writer contract done right elsewhere
  in the same file that has finding 3.1 — worth noting as the contrast.
- `--only` correctly bypasses the write (not a partial-corpus overwrite) rather than being
  silently exempted from the shrink guard in the dangerous direction.
- `--top` (`:441`, `:454`) is explicitly documented as print-only ("the file always holds every
  row") and the code confirms it — `land()` writes the full `rows` list before any `[:a.top]`
  slicing occurs in the print loop. No Hard Rule 0 violation.
- `host_reachable()`'s three-mode (`DEAD`/`RAW`/normal) handling is correctly reasoned against
  its own cited history (RAW hosts previously misread as dead).
- `category_size_probe()` vs `category_size()` correctly distinguishes "no such category"
  (`None, None`) from "transport failed" (`None, err`), and `audit()`'s `work()` correctly acts
  on that distinction (`:322` unanimity fix, `:336-339` "unreliable" vs genuine absence) — this
  is the m3 fix described in the docstring and it is real in the current code.
- No committed secrets.

---

## 4. `src/pick_model.py`

No HIGH or MEDIUM findings. The residency ruling is enforced correctly:

- `resident()` (`:190-192`) gates every candidate on `weight_gb(m) + KV_GB <= budget`, and
  `budget` is computed from `total_vram_gb()` (actual `nvidia-smi` total, not a config value) —
  a model that doesn't fit is moved to `refused` (`:301-303`) and is never scored or selected,
  just listed with its reason. Correct, and matches the "never silently hidden" claim in the
  comment at `:89`.
- `save_config()` (`:104-134`) correctly checks both failure modes it claims to check: a
  no-op `re.subn` match (`n == 0`) and a denied `replace_retry` — both now return `False` and
  print a reason rather than falsely claiming success, matching the docstring's account of the
  two bugs it fixes.
- `pick_model.py` never calls `ollama pull` itself anywhere in the file (`print_pull_suggestions()`
  only prints strings) — it cannot silently pull a different model; that part of the open item's
  concern is unfounded.

### Finding 4.1 — LOW / observational — no hard affinity for the "standing choice"
`qwen3:8b` beyond generic tier-and-size ranking
**`pick_model.py:55-62`, `:258-270`**. `FAMILY_TIERS` ties `qwen3` with nine other families at
tier 5 (llama3.3, llama3.1, gemma3, mistral-small3, mistral-large, command-r-plus, gpt-oss,
deepseek-v3). `score_model()` breaks ties by `min(log2(params+1), 6)`. If a second tier-5 model
of similar or larger (but still VRAM-resident) size is ever installed alongside `qwen3:8b`, the
scorer can rank it above `qwen3:8b` and `--write` would silently switch `config.yaml`'s `model:`
away from it — the residency gate (correctly) only enforces "fits on the GPU", not "is
`qwen3:8b` specifically". This matches the letter of the 2026-08-24 ruling ("GPU-only, and stick
to it" — a residency constraint) but not necessarily its spirit if the owner meant "stick to
`qwen3:8b` the specific tag." Not a functional bug against the documented contract; flagged
because the open item asked specifically whether the logic could silently pick a different
model, and under this scenario it can. No reproduction attempted (would require installing a
second model on the real machine, out of scope for a read-only audit).

### Finding 4.2 — LOW — `is_instruct_tuned()` is a near-tautological "yes" check
**`pick_model.py:164-170`**. Returns `True` for every model name except those containing
`-base`, `-text`, or `-pt`. Its own docstring is honest about this ("most Ollama chat models are
instruct-tuned by default even without the word in the tag"), and its contribution to
`score_model()` is capped at +1 point — small enough that it rarely changes a ranking. Not a
Hard Rule 6 violation in the "check that cannot fail and hides a real risk" sense (it's honestly
weak, not deceptively strong), but worth naming since it is, in practice, nearly always `True`.

### Clean in this file
- `EXCLUDE_PATTERNS` correctly filters vision/embedding models before they can ever be scored.
- `weight_gb()`'s fallback chain (`KNOWN_WEIGHT_GB` -> live `size` field from `/api/tags` ->
  crude param-count estimate) prefers the real reported size in the common case; the crude
  estimate is a last resort only reached if Ollama's own API omits `size`, which it does not in
  practice.
- No committed secrets.

---

## 5. `src/weave_index.py`

No HIGH, MEDIUM, or Hard-Rule-0 findings.

- `designations()` (`:96-133`) and `load_records()` (`:181-202`) both correctly key their caches
  off `_records_sig()` (file count + newest mtime) and both correctly refuse to cache a
  caller-supplied `records` list (`:109`, matches the m17 fix described in the docstring — the
  historical bug was a bare uninvalidated global, and the current code invalidates on every
  directory change).
- The corpus-learned `DESIGNATION_MIN_NAMES` threshold (`:80`) plus the small hand `_SEED`
  (`:86-91`) is a reasonable, documented design — not a brittle hand-list, not a Hard Rule 0
  violation (it decides what counts as a *continuity marker*, not what counts as an *entity*;
  nothing is dropped from any listing by this logic).
- `main()`'s `top = ...[:18]` (`:259`) and `spread`'s `[:10]` (`:255`) are both print-only
  summary slices in the CLI report; the actual write path (`--write`, `:266-272`) uses
  `silence.write_json` on the full, untruncated `index` and `candidates` dicts — correctly
  routed through the mandated shared-state writer (Hard Rule 4 satisfied).
- `norm()`'s title-stripping loop (`:157-160`) correctly iterates to a fixed point
  (`while prev != s`) rather than assuming one pass suffices — not a check that can silently
  under-strip nested titles.
- No committed secrets.

---

## 6. `src/catalogue_models.py`

No HIGH or MEDIUM findings. The Hard Rule 0 fix described in the file's own comment (run #26,
`available_sample` no longer actually sampled) is real: `stale.append({..., "available_sample":
list(r["models"])})` at `:151` carries every model, and the field is only written to
`data/PROVIDER_MODELS.json` via `silence.write_json(OUT, payload, ...)` at `:162` — correctly
routed, correct data (Hard Rule 4 and Hard Rule 0 both satisfied on the persisted artifact).

### Finding 6.1 — LOW — one remaining console-only truncation without a "…and N more" disclosure
**`catalogue_models.py:158`**: `", ".join(r["models"][:10])` in the "Current alternatives, per
provider" print block. This is print-only (the persisted `payload` is unaffected — full lists
land in `stale[*]["available_sample"]` and `rows[*]["models"]`), so it is not a Hard Rule 0
violation of the data itself. But unlike other truncated print loops in this same codebase
(e.g. `generate.py`'s `refused_src` loop, which prints "... and %d more" when it clips), this
one gives no indication to someone reading the console output that the list was cut, which is a
minor readability regression given this is exactly the screen a person reads to pick a
replacement model name.

### Clean in this file
- `ask_provider()`'s fallback chain (`v1/models` vs `/models`, `.rstrip("/")` handling of
  `.../v1` bases) is correctly reasoned; the `locals().get("last", "no model list endpoint")`
  guard at the end correctly avoids an `UnboundLocalError` in the case where every URL in `tries`
  returns zero-length `models` without ever raising (verified by trace: `tries` is provably
  non-empty for every `base`, since `"/models"` never starts with `"/v1"` and is therefore never
  filtered out).
- No committed secrets (the printed provider error strings are exception messages, not keys;
  `Authorization` headers are built from config-supplied values, never logged).

---

## 7. `src/compress_store.py`

### Finding 7.1 — HIGH, REPRODUCED — `store()` writes directly to the final content-addressed
path with no temp file, no atomic rename, and no writer registered with the project's shared-
state contract; a concurrent `load()` crashes uncaught on a torn read
**`compress_store.py:43-44`**:
```python
with open(path, "wb") as f:
    f.write(blob)
```
No `.tmp` staging, no `silence.write_json`, no `silence.replace_retry` — `path` (the final
`{hash}.zst`/`{hash}.gz` file that `catalog.py` and `generate.py` both read via `load()`) is
opened directly in `"wb"` mode, which truncates it to zero bytes at `open()` time before any
bytes are written. `load()` (`:55-65`) has no exception handling at all — a caller (`catalog.py:97`,
`generate.py:462`) that hits this window gets a raw, uncaught decompression exception.

**REPRODUCED**: `scratchpad/rg_test/test_compress_race.py` — 4 threads calling `store()` with
identical content plus 4 threads polling `load()` on the resulting path, 30 trials in a scratch
`compressed/` directory (never the repo's real `output/compressed/`):
- **24/30 trials (80%) produced at least one uncaught reader exception**
  (`ZstdError('error determining content size from frame header')` — the signature of a
  reader opening the file mid-truncate/mid-write)
- **60 total uncaught reader exceptions** across the run, against 21,258 successful reads
- 0 writer-side exceptions, 0 silently-wrong-content reads (content-addressing means every
  concurrent writer of the *same* text writes the *same* bytes, which is why corruption shows up
  as a crash-on-torn-read rather than a wrong-content read — cold comfort, since the crash still
  reaches an unguarded caller)

This is realistically triggered whenever two processes materialize the same chapter concurrently
— e.g. two overlapping `generate.py` invocations (nothing in `generate.py` or `compress_store.py`
gates against that; `generate.py` runs its own job loop single-threaded, so the risk is strictly
cross-process, the same class of gap as magnitude.py finding 2.3) — or whenever `catalog.py read`
is run against an address `generate.py` is actively (re)writing.

Severity: **HIGH**. Fix: write to a unique temp path (pid+thread suffix, or just route through
`silence.write_json`'s binary equivalent / `silence.replace_retry` directly since content-hash
naming already gives a natural target name) and atomically rename into place; content-addressing
means the rename is always safe to skip-if-exists, too, which the current code does not exploit
(`store()` unconditionally rewrites even if `path` already holds identical bytes).

### Clean in this file
- `content_hash()` is a plain SHA-256 truncated to 32 hex chars (128 bits) — no realistic
  collision risk for a chapter-count corpus; not a finding.
- The zstd-then-gzip fallback (`:12-17`) is honestly reasoned and the one `except ImportError`
  correctly calls `silence.note` — not a swallowed failure.
- `load()`'s `codec` dispatch (`:58-65`) correctly raises on an unknown codec rather than
  silently returning something wrong.
- No committed secrets.

---

## Summary of severities

| # | File | Finding | Severity | Status |
|---|------|---------|----------|--------|
| 1.1-1.3 | runguard.py | fixed-tmp race + TOCTOU double-claim + uncaught crash | **HIGH** | **REPRODUCED** |
| 1.4 | runguard.py | beat/release share the hazard | HIGH (lower likelihood) | REPRODUCED (mechanism) |
| 2.1 | magnitude.py | `_split_gate()` omits SUBJECT guard | **HIGH** | **REPRODUCED** |
| 2.2 | magnitude.py | calibrate() partial-pass handling | — | REFUTED (already fixed) |
| 2.3 | magnitude.py | run_batch() fixed-tmp cross-process hazard | MEDIUM | HYPOTHESIS |
| 2.4 | magnitude.py | silence-exempt marker missing at :832 | LOW | — |
| 3.1 | completeness.py | category cache fixed-tmp race | MEDIUM | REPRODUCED (race real, no crash — caught) |
| 4.1 | pick_model.py | no hard qwen3:8b affinity | LOW | — |
| 4.2 | pick_model.py | is_instruct_tuned near-tautology | LOW | — |
| 6.1 | catalogue_models.py | undisclosed print truncation | LOW | — |
| 7.1 | compress_store.py | non-atomic direct write, uncaught reader crash | **HIGH** | **REPRODUCED** |
