# BATCH 03 audit — run #25

Modules: `src/standards.py` (1292 lines), `src/catalogue_web.py` (362), `src/weave_index.py` (276),
`src/runguard.py` (219), `src/catalogue_models.py` (171), `src/scale_theories.py` (148).
Every line of every file was read. Two suspicions from run #24 were confirmed at source, with
live reproductions where the code allowed it.

---

## 1. `runguard.py:72-80` — `_land()` uses a FIXED tmp filename; two racing writers can crash the loser with an uncaught exception, contradicting the module's own "WHY IT DOES NOT RAISE" promise

**NEW — VERIFIED by reproduction.**

```python
def _land(rec, path):
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=2)
    except Exception:
        silence.note("runguard._land")
        return False
    return silence.replace_retry(tmp, path)
```

`tmp = path + ".tmp"` is not PID/thread-qualified — exactly the anti-pattern `silence.write_json`'s
own docstring says was fixed everywhere else in the tree ("THE TMP NAME CARRIES PID AND THREAD...
Two writers of the same path otherwise collide on the temp file itself, and the loser can replace
the winner's target with a partial file"). `runguard.py` does not call `silence.write_json`; it
hand-rolls this write and inherits the exact hazard that function exists to close.

Worse: `silence.replace_retry()` only catches `PermissionError`. If two processes race to
`claim()`/`beat()`/`release()` the SAME guard file — which is the entire reason this module
exists: arbitrating between potentially-overlapping maintenance runs — the loser's
`os.replace(tmp, dst)` can raise `FileNotFoundError` (the winner already consumed/renamed the
shared tmp file) with nothing in `_land()` or `replace_retry()` catching that exception class.
That propagates out of `claim()`/`beat()`/`release()` uncaught — a full crash with a traceback,
not the `False` return the module's docstring explicitly promises ("`beat()` returns False and
says so on stderr rather than raising").

**Reproduction** (real production `claim()`/`_land()`/`silence.replace_retry()`, only wrapped
with an artificial `time.sleep(0.5)` between write and replace to widen the race window
deterministically — no logic was changed):

```
agentB -> True claimed
Traceback (most recent call last):
  ...
  File "...\src\runguard.py", line 119, in claim
    if not _land(rec, path):
  File "...\race_worker.py", line 17, in slow_land
    return runguard.silence.replace_retry(tmp, path)
  File "...\src\silence.py", line 233, in replace_retry
    os.replace(tmp, dst)
FileNotFoundError: [WinError 2] The system cannot find the file specified:
  '...\rg_test.json.tmp' -> '...\rg_test.json'
```

Final file on disk correctly held `agentA`'s record — the *content* landed fine — but the
`agentA` process itself crashed with an unhandled traceback instead of getting `(False, ...)`
back. Any caller of `claim()` that doesn't wrap the call in its own try/except (the documented
contract says it never needs to) dies instead of gracefully losing the race.

This is a genuinely new gap: `verify_math.py:1671-1725` (§19k, 15 checks, written for the m27
ownership-invariant fix) exercises only single-process ownership semantics — never two processes
racing on the physical tmp file — so nothing currently guards against it. The module description
(`runguard.py:27-33`, "WHY IT DOES NOT RAISE") is a docstring promise the code does not keep
under contention.

**Fix shape:** either call `silence.write_json(path, rec)` directly (it already does the
PID+thread-qualified tmp name and the retry), or replicate that naming in `_land()`, and widen
`replace_retry`'s except clause (or `_land`'s) to catch `FileNotFoundError` alongside
`PermissionError`.

---

## 2. `standards.py:670-682` — the assay-band check builds "mine" from the CHARTER's own band digit, never from the computed magnitude, so it cannot detect a band-level drift at all

**KNOWN (flagged in the task prompt from run #24 suspicion) — VERIFIED with a concrete
false-positive reproduction using real `data/REFERENCE_ASSAYS.json` data.**

```python
ch = v.get("charter") or []
got = (v.get("reference") or {})
if len(ch) >= 3 and got.get("magnitude"):
    band = str(ch[0])                                        # <- CHARTER's own band, e.g. "M7"
    published, tol = float(ch[1]), float(ch[2])
    mine = float(str(band)[1:]) + float(got.get("decimal", 0))   # <- band never comes from `got`
    if abs(mine - published) <= tol:
        inside += 1
```

`got.get("magnitude")` (the *computed* band, e.g. `"M8"` after a real drift) is checked for
truthiness only — its value is never used in the `mine =` line. `mine`'s integer part is always
taken from `ch[0]`, the charter's own published band, so `mine` and `published` share their
whole-number part BY CONSTRUCTION. Only the decimal remainder (from `got.get("decimal")`) is
ever actually compared.

Reproduced with `data/REFERENCE_ASSAYS.json`'s real Goku row (`charter: ["M7", 7.62, 0.41]`):
injecting a drifted computed reference of `magnitude: "M8", decimal: 0.50` (i.e. the instrument
now genuinely computes M8.50 = 8.50, nowhere near the charter's `[7.21, 8.03]` interval) still
yields `mine = 7.50` (band borrowed from the charter's "M7") and the check reports **"inside
interval": True** — a false PASS that completely hides the band-level drift. This is a HIGH
severity "instrument" standard (`"the instrument has drifted... check assay.SIGMA_BY_ATTESTATION
and the axis weights before trusting any new Magnitude"`) that is structurally blind to the one
failure mode (a whole-band shift) it would matter most to catch.

---

## 3. `standards.py:560-586` — the unanswered-records glob loop has no per-file try/except; one file error mid-scan caches a partial undercount as the answer for a HIGH-severity, zero-tolerance standard

**KNOWN (explicitly named in the task prompt and in `NEXT_STEPS.md` §3) — VERIFIED by code
reading; confirmed the exact mechanism.**

```python
unans_files = 0
try:
    ...
    for fp in _g.glob(os.path.join(HERE, "data", "readfeats", "**", "*.json"), recursive=True):
        with open(fp, encoding="utf-8") as f:
            head = f.read(700)
        if '"chunks_unanswered": 0' not in head and "chunks_unanswered" in head:
            unans_files += 1
        elif "chunks_unanswered" not in head:
            unans_files += 1
    _UNANS_CACHE.update({"at": now_m, "n": unans_files})
except Exception:
    silence.note("standards.py:unanswered-records")
```

One `try/except` wraps the entire loop. A single file raising mid-scan (deleted concurrently by
`read.py`'s own corrupt-cache self-heal — the precondition run #24 confirmed live — a permission
error, a decode error) aborts the `for` loop immediately; whatever partial `unans_files` count had
accumulated up to that point (commonly `0`, if the failure lands early) is the value used for the
rest of this call, because it falls straight through to `out.append(...)` after the `except`.
`MAX_UNANSWERED_RECORDS = 0` is zero-tolerance and severity `"high"`, so a scan that died after
one file reads as a clean "0 unanswered" pass. Confirmed via live run (`python src/standards.py`,
this session) that the check currently reports `0` cleanly on a healthy corpus — the bug is
latent, triggered only by the file-vanishes-mid-glob race, but the code path is exactly as
described.

---

## 4. `standards.py:904-907` — `standards.check()`'s job-progress cache write uses a fixed tmp filename and a raw `open+json.dump`, from a function documented to run inside multiple separate OS processes concurrently

**NEW — UNVERIFIED (inferred from code + the function's own cross-process documentation; not
reproduced live, but the mechanism is identical to finding #1, which was reproduced).**

```python
tmp = JOB_WATCH + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(cur, f)
silence.replace_retry(tmp, JOB_WATCH)
```

`JOB_WATCH = state/job_progress.json`. This is a raw truncate-then-fill write with a
non-PID-qualified tmp name — it does not call `silence.write_json`. The surrounding code's own
comment 30 lines below (`standards.py:1030` area) states plainly that `standards.check()` "runs
inside whichever process is rendering the panel -- `publish.py` for the public page, `dashboard.py`
for the local one," and the module's top docstring says this exact check is "on a check the
dashboard polls every 5 seconds." So this write is executed repeatedly, on a 5-second cadence, by
at least two independent OS processes racing on the same fixed `state/job_progress.json.tmp` path
— the identical hazard proven live for `runguard.py` in finding #1 (interleaved/clobbered tmp
writes, and a `replace_retry` that only catches `PermissionError` so a `FileNotFoundError` from
the losing process's `os.replace` is uncaught). The entire block is wrapped in an outer
`try/except Exception: silence.note("standards.py:job-advance")` (visible further down the same
function), so a race here silently drops the "every running job is advancing" standard for that
one 5-second cycle rather than crashing the whole dashboard process — lower blast radius than
finding #1, but the same root defect and the same fix (`silence.write_json` instead of the
hand-rolled tmp+replace).

---

## 5. `standards.py:829-836` — "the character sweep is newer than the catalogue" can read a false "fresh" if `data/records/*.json` ever matches zero files

**NEW — UNVERIFIED (edge case; the directory currently holds 217 files so this is latent, not
observed live).**

```python
newest_rec = max((os.path.getmtime(f) for f in
                  _g.glob(os.path.join(HERE, "data", "records", "*.json"))),
                 default=0.0)
lag_h = (newest_rec - sweep_m) / 3600.0
out.append(_s(
    "the character sweep is newer than the catalogue", lag_h <= 1.0, ...
```

If the glob ever returns no files (wrong path, directory moved, a transient empty-directory
state during a records rebuild), `newest_rec` silently defaults to `0.0`. `lag_h` then becomes a
large *negative* number (`(0 - sweep_m)/3600`), which passes `lag_h <= 1.0` and reports `"fresh"`
— the exact "no denominator is not zero" failure shape this same file explicitly guards against
elsewhere (see its own comments at the `COMPLETENESS.json` coverage check and the `calls that
succeed` rate check, both of which explicitly special-case an empty/too-thin sample as
`UNMEASURED` rather than let the arithmetic report a clean pass). This one check does not have
that guard. Low priority given current data, but the pattern is exactly what the file's own
authors have twice called out as the project's most expensive standards mistake.

---

## 6. `catalogue_web.py:70-79` (`save_roll`) — fixed, non-PID-qualified tmp filename on a five-writer shared file

**KNOWN** — already listed in `NEXT_STEPS.md` §3 under "Non-atomic shared writes still open:
... `catalogue_web.py:70-79`". Confirmed still present:

```python
def save_roll(roll):
    import silence as _sil
    tmp = ROLL + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(roll, f, indent=2, ensure_ascii=False)
    _sil.replace_retry(tmp, ROLL)
```

Within *this* process the three `ThreadPoolExecutor` workers are correctly serialized by
`_wlock` (verified: `save_roll(roll)` at `catalogue_web.py:350` sits inside the same
`with _wlock:` block that gates the record write), so no in-process race. The residual risk is
cross-process: `data/SWEEP_ROLL.json` is also written by `resync_roll.py`, `catalogue_aurora.py`
and `catalogue_codex.py` per the existing finding, and `catalogue_web.py`'s `roll` is loaded ONCE
at `main()` start (`load_roll()`, line 256) and mutated/saved repeatedly over a long run — any
concurrent external writer's update made after this process's initial load is silently
overwritten by this process's next `save_roll(roll)`. Same class as the already-known finding;
noted for completeness since `catalogue_web.py` specifically wasn't named in the "five writers"
sub-bullet (only in the separate "non-atomic" list).

---

## 7. Stale `silence.note()` line tags (misleading diagnostics, not behavioral bugs)

**NEW, minor.** The project has an established finding class for this (`NEXT_STEPS.md` §3: "stale
`silence.note()` line tags across `foreman.py`, `feats.py`, `scout.py`") but these two instances
in this batch aren't in that list:

- `weave_index.py:197` — `silence.note("weave_index.py:155")`; the actual `except` is at line 197,
  42 lines away from the string it logs.
- `catalogue_web.py:97` — `silence.note("catalogue_web.py:79")`; actual `except` is at line 96/97.
- `catalogue_web.py:274` — `silence.note("catalogue_web.py:266")`; actual `except` is at line 273/274.

None of these affect behavior — `health.py`'s failure ledger just files the count under a
line number that no longer matches the source, costing whoever investigates a `grep` for the
wrong location. Low severity, easy fix (re-run `silence.py --instrument` or hand-correct the
strings).

---

## 8. Checked and refuted: `weave_index.py:224` description truncated to 400 chars

Investigated as a possible Hard-Rule-0 violation (`"description": (e.get("description") or
"")[:400]` feeding `data/ENTITY_INDEX.json` / `data/WEAVE_CANDIDATES.json`). Traced every
downstream reader in `src/`: `weave.py` (`filtered_index()`) re-truncates to `desc[:400]` /
`desc[:300]` for its own mechanic/rules-voice heuristic anyway, so the 400-char cap upstream
changes nothing there; `thread_integrity.py` and `cosmology_graph.py` never read the
`description` field at all. **No finding** — the truncation is real but currently inert; flagging
here only so a future reader doesn't re-open it without checking the same trace.

---

## Clean modules

- **`scale_theories.py`** (148 lines) — read end to end. Self-contained physics-flavoured module,
  no file I/O, no writes, no caps. `bulk_export_beta`, `growth_strike`, `penetration_pressure`,
  `surviving_theory` all checked by hand; arithmetic and edge guards (`resident_mass_kg <= 0`,
  `max(growth_time_s, 1e-6)`, `max(contact_area_m2, 1e-30)`) are correct. Matches run #24's
  "found CLEAN" list.
- **`catalogue_models.py`** (171 lines) — read end to end, and exercised its request-building and
  `sweep()` control flow by hand. Two-writer contract respected (`silence.write_json` at line
  157). `ask_provider`'s per-URL `except Exception: silence.note(...)` correctly tries the next
  candidate path rather than swallowing silently; `locals().get("last", ...)` fallback is safe
  because `tries` is provably never empty (`/models` is always appended). The `[:8]`/`[:10]`
  slices at lines 146/153 are informational print samples only — the actual `missing` /
  `stale` detection lists used for the standards check are computed from the FULL `have` set,
  never sliced. Matches run #24's "found CLEAN" list.
- **`standards.py`** — every other standard not called out above was read and checked against a
  live run (`python src/standards.py`, this session, 32/40 met, self-check "every declared floor
  is measured" passed "all measured"). No other swallowed-failure, inverted-guard, or
  cannot-fail pattern found beyond items 2-5 above. The "probe failures (reported, not judged)"
  line (`holds=True` unconditionally) is explicitly self-documented as informational with "no
  floor," not a check — not a finding.
- **`catalogue_web.py`** and **`weave_index.py`** — otherwise clean beyond items 6-7. Hard Rule 0
  is honored throughout `catalogue_web.py`: `MAX_PER_SOURCE`/`MAX_PER_CATEGORY`/
  `CATEGORY_SCAN_DEPTH` are all `None` with a `raise SystemExit` guard against reintroduction,
  and every `category_members`/`rank_by_size` call passes `limit=None`/`top=None`.
  `weave_index.py`'s `load_records()` correctly wraps EACH file's open/parse in its own
  try/except inside the loop (contrast with finding #3's bug in `standards.py`) — a positive
  example of the right pattern in the same codebase.
