# AUDIT — BATCH 07 (run31 comprehensive sweep)

Modules: `src/magnitude.py` (1109), `src/completeness.py` (482), `src/pick_model.py` (357),
`src/entity_match.py` (278), `src/coverage.py` (219), `src/audit.py` (177),
`src/withdraw_chapters.py` (112).

Total lines read: 2734 (every line of every listed file, read in full, plus cross-checks of
`silence.py:replace_retry/write_json`, `pipeline.py:records/write_record_catalogue`, and
`generate.py:save_json` to establish the project's canonical shared-file-write pattern).

Scope note: this batch is READ-ONLY. No file was edited. No long-running or state-mutating
script was executed; only greps and static reads.

---

## Findings, worst first

### 1. `withdraw_chapters.py:66-98` — withdrawal has no chapter-selection logic; wipes the WHOLE catalog
**Severity: blocking. Confidence: VERIFIED.**

The module's own docstring frames this as a *selective* withdrawal ("the 145 chapters written
while the prose gate was inverted are withdrawn"), implying other, unaffected chapters remain.
The code contains no such filter. `main()` loads the entire `output/index/catalog.json` into
`cat` (line 44) and then:

```python
for _addr, rec in cat.items():           # line 66 — every record, no criterion applied
    for key, sub in (("raw_path", "raw"), ("compressed_path", "compressed")):
        ...
        shutil.move(src, os.path.join(arch, sub, os.path.basename(src)))   # line 74
...
with open(tmp, "w", encoding="utf-8") as f:
    json.dump({}, f, indent=2)            # line 97 — the ENTIRE catalog, not a subset
silence.replace_retry(tmp, CATALOG)
```

There is no check anywhere in the file for citation rate, missing Threads section, or
uncited Instrument scores — the three criteria the docstring itself names as the reason the
145 chapters were bad. `--label` is the only argument besides `--go`; there is no source list,
no manifest of "which addresses are withdrawn."

**Failure scenario:** the catalog later holds a mix of good chapters (0.0%–100% cited, correctly
generated) plus a small new batch that needs withdrawing for an unrelated future reason. Running
`python src/withdraw_chapters.py --go --label <new-date>` per the file's own usage line moves
**every** raw/compressed file in the catalog to the archive and truncates `catalog.json` to `{}}`,
destroying the record for every good chapter along with the bad ones. Because `generate.py`'s
resume logic is keyed off `catalog.json`'s content-hash entries (per `CLAUDE.md`'s own
description of `generate.py`), the next `generate.py` run would treat every previously-generated
chapter — good and bad alike — as never having been generated, and regenerate the entire library
at real model-time cost. The underlying files are moved rather than deleted (recoverable from
`output/withdrawn_<label>/`), but the catalog's bookkeeping is not.

This may have been harmless on 2026-08-25 specifically (if the catalog held exactly the 145
tainted entries and nothing else at that moment), but the script is written to be reusable
(`--label` is a free parameter) and carries no safeguard against being run again against a mixed
catalog.

---

### 2. `withdraw_chapters.py:95-98` — direct write to `output/index/catalog.json`, bypassing the file's own canonical atomic writer
**Severity: major. Confidence: VERIFIED.**

`generate.py` (the module that owns `output/index/catalog.json`) writes it exclusively through
`save_json()` → `silence.write_json()` (`generate.py:53-58`), which uses a PID+thread-qualified
temp filename specifically to prevent two writers colliding on the same fixed tmp path
(`silence.py:290-327`, whose docstring documents this exact hazard being found live at twelve
call sites project-wide). `withdraw_chapters.py` instead hand-rolls:

```python
tmp = CATALOG + ".tmp"                                    # fixed name, not PID/thread-qualified
with open(tmp, "w", encoding="utf-8") as f:
    json.dump({}, f, indent=2)
silence.replace_retry(tmp, CATALOG)
```

`generate.py`'s own comment at that file's `save_json` says catalog.json "is rewritten
repeatedly across an hours-long generation run." If `withdraw_chapters.py --go` is ever run while
a `generate.py` pass is active (plausible — nothing in either script checks for the other), both
processes can target the identical `output/index/catalog.json.tmp` path at once; the loser's
in-flight write can be truncated and replaced by the other's temp file mid-write, per the
mechanism `silence.write_json`'s own docstring describes as the reason it exists.

---

### 3. `completeness.py:112-118` (`category_size_probe`) — unlocked multi-thread race writing `state/category_sizes.json`
**Severity: major. Confidence: VERIFIED (concurrent callers confirmed in this same file).**

`audit()` runs `work()` across `ThreadPoolExecutor(max_workers=workers)` (default 6,
`completeness.py:238,360`). Each `work()` call, for each of `ws.CATEGORY_PROBES[PERSONS]`, calls
`category_size_probe(sub, cand)` (`completeness.py:300`), which on a cache miss writes the shared
cache file with **no lock and a fixed tmp name**:

```python
cache = _cs_load()                    # returns the SAME shared dict for every thread
cache[k] = {"at": time.time(), "n": got}
tmp = _CS_CACHE_P + ".tmp"            # fixed name — every thread races the same path
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(cache, f)
silence.replace_retry(tmp, _CS_CACHE_P)
```

With 6 worker threads probing 8 categories per source, this function runs concurrently dozens of
times per `audit()` invocation. Two threads opening the same `tmp` path in `"w"` mode race:
whichever opens second truncates the first's in-progress write, and the interleaved output can
land as corrupt/partial JSON before either `os.replace` fires. Blast radius is contained (the
next `_cs_load()` catches the resulting `json.load` failure at `completeness.py:76` and silently
treats it as "no cache yet," rebuilding from scratch — so this degrades to extra API calls rather
than a hard failure), but it is a live instance of exactly the anti-pattern `silence.write_json`
was written project-wide to eliminate, in a file that already imports `silence` for other calls.

---

### 4. `pick_model.py:295` — VRAM-unmeasurable machines silently assumed to have a 9GB budget
**Severity: major. Confidence: VERIFIED.**

```python
budget = (total_vram_gb() or 10.0) - VRAM_RESERVE_GB
```

`total_vram_gb()` (`pick_model.py:173-187`) returns `None` whenever `nvidia-smi` is missing,
errors, or returns nonzero — i.e., exactly the case of no NVIDIA GPU present or an unreadable
driver. That `None` is silently replaced with a hardcoded `10.0`, and the `RESIDENT_ONLY` gate
(owner ruling 2026-08-24, "GPU-ONLY, AND STICK TO IT") then evaluates every model's fit against
this fictitious budget as if it had verified a real 9GB-effective card. No message is printed for
this fallback — contrast with the sibling `free_vram_gb()`, whose `None` case IS surfaced
(`pick_model.py:313-314`: `"(couldn't read free VRAM -- nvidia-smi not available)"`).

**Failure scenario:** on a machine with no working `nvidia-smi` (missing driver, WSL without GPU
passthrough, a laptop with an integrated GPU only), the tool silently proceeds as though it
verified an actual 10GB-class card, approves/refuses models against that guess, and reports a
"best available" model with no indication the residency check it's named for was never actually
performed against real hardware — directly contradicting the "GPU-only, and stick to it" ruling
this exact gate exists to enforce.

---

### 5. `magnitude.py:1050-1066` (`run_batch`/`work`) — hand-rolled ASSAYS.json write duplicates, and weakens, `silence.write_json`
**Severity: major. Confidence: VERIFIED.**

```python
tmp = OUT + ".tmp"                       # fixed name, no PID/thread qualifier
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(done, f, ensure_ascii=False)
for attempt in range(5):
    try:
        os.replace(tmp, OUT)
        break
    except PermissionError:
        ...
```

This whole block executes under `with lock:` in `work()`, so *in-process* thread races are
prevented. But it reimplements — worse — logic `silence.write_json`/`silence.replace_retry`
already provide (this same file already `import silence` at line 59 and correctly uses
`silence.replace_retry` in `calibrate()`'s `_land()` a few hundred lines away). The fixed tmp
name means two separate **processes** running `run_batch` concurrently (e.g. an accidental
double-launch, or an overlapping scheduled invocation — the file's own comments elsewhere
describe exactly this class of collision, "2026-08-23, WinError 5") would race on the identical
`ASSAYS.json.tmp` path, which is the specific hazard `silence.write_json`'s PID+thread-qualified
tmp name (`silence.py:316`) was introduced to close. Using `silence.write_json(OUT, done,
ensure_ascii=False)` here would get that protection for free.

---

### 6. `magnitude.py:848-850` (`calibrate`/`_land`) — same fixed-tmp-name pattern, same file
**Severity: minor. Confidence: VERIFIED.**

```python
with open(_cr + ".tmp", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
silence.replace_retry(_cr + ".tmp", _cr)
```

Uses `silence.replace_retry` (better than #5's hand-rolled retry) but still a fixed tmp name.
`calibrate()`'s own docstring says it is "dispatched roughly hourly and killed on the next lap,"
and that "six charter benchmarks against a rate-limited pool do not reliably finish inside one
lap" — i.e., overlapping invocations (a kill landing late, or two schedules drifting into each
other) are exactly the scenario this function's own prose anticipates. `silence.write_json` would
close the same gap #5 has. Lower severity than #5 because `CHARTER_REGRESSION.json` is a
regression-test artifact, not the primary assay record.

---

### 7. `magnitude.py:415-430` (`candidates`) — dead `cap` parameter is a live Hard-Rule-0 landmine
**Severity: minor/cosmetic. Confidence: VERIFIED (no current caller sets it).**

```python
def candidates(ev, cap=None):
    ...
    return {ax: sorted(v, key=lambda r: -len(r["feat"]))[:cap] if cap
            else sorted(v, key=lambda r: -len(r["feat"])) for ax, v in out.items()}
```

Grepped every call site in the repo (`magnitude.py:595`, `sweep.py:166`) — both call
`candidates(ev)` with no `cap`, so today this is inert. But the parameter exists, is wired
straight to a `[:cap]` slice on the evidence list, and needs no code change to reintroduce
exactly the truncation Hard Rule 0 forbids ("capping at six decided that an entity with forty
pieces of Ruin evidence had six" — this file's own header). Worth removing the parameter rather
than leaving a loaded gun with no current trigger.

---

### 8. `completeness.py:303` — a genuinely zero-sized category is scored the same as a transport failure
**Severity: minor. Confidence: HYPOTHESIS (plausible but not confirmed against live wiki data).**

```python
n, err = category_size_probe(sub, cand)
if err:
    failed += 1
if n:                              # n == 0 is falsy -> not recorded into `sizes`
    sizes[cand] = n
```

`category_size_probe` can legitimately return `(0, None)` for a category that exists but holds
zero pages (empty stub category). `if n:` treats that identically to "no answer," so a source
whose only probed category genuinely has 0 pages falls into `if not sizes and failed == 0: return
None` (`completeness.py:322-323`) and is **silently dropped from `COMPLETENESS.json` entirely** —
the exact "genuine absence vs. transport failure" conflation this file's own docstring and
`category_size_probe`'s docstring (BUGS m3) were written to eliminate for the failure case, just
reappearing for the zero-legitimate-count case instead.

---

### 9. `coverage.py:78-83` (`_so_save`) — same fixed-tmp-name pattern as #3/#5/#6
**Severity: minor. Confidence: HYPOTHESIS (no concurrent caller of `_so_save` found in-repo; risk is cross-process only).**

```python
tmp = _SO_CACHE_P + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(_SO["d"], f)
_sil.replace_retry(tmp, _SO_CACHE_P)
```

No in-repo caller runs `measure()` from multiple threads (confirmed via grep — the only other
caller of `coverage.state_of`, `drill.py`, never calls `_so_save`). Risk is limited to two
separate *processes* both running `coverage.py` (or something importing and calling `measure()`)
overlapping, which would race on the same fixed `state/coverage_cache.json.tmp` path. Flagged for
completeness as the fourth instance of the same pattern-family as #3/#5/#6; `state/` is a plain
performance cache here, not primary data, so a corrupted write self-heals via the same silent
`except Exception: pass` fallback noted in finding #3.

---

### 10. `coverage.py:170-186` (`report`) — unguarded division by total entry count
**Severity: cosmetic. Confidence: VERIFIED, low-impact edge case.**

```python
n = sum(r["entries"] for r in rows)
...
print(f"\n  CITED       {cited:>8,}  {cited/n:>6.1%} ...")
```

`measure()` itself guards every per-row division with `max(n, 1)` (`coverage.py:163-164`), but
`report()`'s headline totals divide by the unguarded `n`. If `rows` is empty or every source has
zero entries, this raises `ZeroDivisionError` and crashes the report rather than printing "no
data." Unlikely in a populated library but inconsistent with the rest of the file's own defensive
style.

---

## Modules with no material findings

- **`entity_match.py`** (278 lines) — clean. Proposer-only by design (never mutates), qualifier
  gate (`qualifier_compatible`) correctly absolute-not-scored per its own extensive
  documentation, `limit=None` used at every real call site so Hard Rule 0 is honored in practice,
  early-return shapes for empty name/pool carry the same keys as the main path (the bug the
  in-file comment says was fixed already checks out as fixed).
- **`audit.py`** (177 lines) — clean, read-only. `PL.records()` returns a real list (verified
  against `pipeline.py:398-409`), so the two consecutive iterations over `recs` (once inside
  `audit_invariants`, once for the sample pool) do not exhaust a generator — considered and ruled
  out as a false lead. Display truncation of failure examples (`v[:4]` per category) is
  disclosed inline ("...and N more") and does not affect the full-corpus counts, consistent with
  Hard Rule 0's carve-out for ranked display vs. silent data loss.
