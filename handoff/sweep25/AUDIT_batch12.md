# AUDIT — batch 12 (run #25)

Files: `src/dashboard.py`, `src/weave.py`, `src/health.py`, `src/cosmography.py`, `src/sweep.py`,
`src/thread_integrity.py`, `src/compress_store.py`. Every line of every file read. Two hypotheses
in the brief were confirmed by running code, not just reading it.

---

## HEADLINE — the three "stalled" movement metrics: ARTEFACT, not a real stall

**VERIFIED.** `cited`, `settled`, `feats` are read at `dashboard.py:326-328` from
`(library().coverage)`, which `_library()` (`:239-263`) sources entirely from `data/COVERAGE.json`
(`:256`). That file is written **only** by `coverage.py` as a subprocess launched from
`overnight.py:coverage_snapshot()` (`:461-472`), called **once per full supervisor cycle**
(`overnight.py:717`, after the read/roll/pipeline stages, which run for hours — `read_hours` +
`join(roll, timeout_h=4)` + `pipeline timeout_h=2`).

`entities read` (`:271-274`, a live `glob.glob(data/readfeats/**/*.json)` count) and `chunks`
(`:196-205`, a live tail-match against `state/read_auto.log`, which `read.py` appends to
continuously) update on **every** dashboard poll. `cited/settled/feats` update only when
`COVERAGE.json`'s mtime moves — once per cycle.

Measured live:
```
COVERAGE.json age: 52.46 minutes
```
Per NEXT_STEPS.md lesson 6 ("under 0.5h -> real; over -> artifact"), 52 minutes is already past
the threshold — **this is the expected shape of a mid-cycle snapshot, not a stopped pipeline.**
The 31-minute stall the owner is seeing is fully explained by `COVERAGE.json`'s refresh cadence,
not by any of the three metrics' underlying computation being stuck.

**The bug is that `movement()` doesn't know this.** `stalled: delta==0 and span>=10` (`:362`)
applies the identical rule to all six metrics regardless of how often their source file is
actually rewritten, and the Movement panel (`panelMovement`, `:520-538`) renders `cited`/`settled`
/`feats` as red **"NO CHANGE in 31 min"** with no indication that this is normal for a file that
refreshes once per multi-hour cycle. The one piece of staleness context that exists —
`library().coverage.age_h` — is computed (`:262-263`) and *is* shown, but only in the separate
**Library** panel (`panelLibrary`, `:627-628`, "measured Xh ago"), not next to the Movement row a
person is actually looking at when they read "stalled."

**Read path per metric, for the record:**
| metric | source | refresh cadence |
|---|---|---|
| `cited` | `data/COVERAGE.json` via `_library()` | once/supervisor cycle (hours) |
| `settled` | `data/COVERAGE.json` via `_library()` | once/supervisor cycle (hours) |
| `feats` | `data/COVERAGE.json` via `_library()` | once/supervisor cycle (hours) |
| `entities read` | live glob of `data/readfeats/**/*.json` | every poll (live filesystem) |
| `chunks` | tail-match of `state/read_auto.log` | every poll (live log, written continuously by `read.py`) |
| `standards met` | `standards.check(s)` computed in-process | every poll (live, but see finding below) |

---

## NEW — dashboard.py `movement()`: concurrent /api/state requests CORRUPT `dashboard_history.json`

**VERIFIED by direct reproduction.** `dashboard.py:335-349`:
```python
try:
    hist = []
    if os.path.exists(HISTORY):
        with open(HISTORY, encoding="utf-8") as f:
            hist = json.load(f)
    hist.append(row)
    cutoff = time.time() - 24 * 3600
    hist = [h for h in hist if h.get("at", 0) > cutoff][-2000:]
    tmp = HISTORY + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(hist, f)
    silence.replace_retry(tmp, HISTORY)
except Exception:
    silence.note("dashboard.py:movement")
    return []
```
This read-modify-write has no lock, and the temp filename (`HISTORY + ".tmp"`) is **fixed, not
thread- or PID-qualified**. `dashboard.py` serves requests via `Server(socketserver.ThreadingTCPServer)`
with `daemon_threads=True` (`:708-710`) — every `GET /api/state` runs `movement()` on its own
thread, and the client JS polls every 5 seconds (`tick();setInterval(tick,5000)`, `:677`) — so any
two concurrently-open dashboard tabs (or any second poller hitting `/api/state`) race on the same
`dashboard_history.json.tmp`.

Reproduced directly — 8 threads each calling `dashboard.movement()` 30 times against a shared
scratch `HISTORY` path:
```
json.decoder.JSONDecodeError: Extra data: line 1 column 12486 (char 12485)
```
Two threads' `json.dump()` calls landed in the same `.tmp` file, producing two concatenated JSON
arrays; `silence.replace_retry` then atomically renamed that **corrupt** file over `HISTORY`.

**This is worse than a lost update.** Once `dashboard_history.json` is corrupted this way, every
subsequent `movement()` call's `json.load(f)` at `:339` raises, which is caught by the *same*
outer `except Exception` at `:347-349` — so it just prints a `silence.note` and returns `[]`
**forever**, because nothing in the except path ever rewrites a fresh `HISTORY`. Unlike
`health.py`'s `LEDGER_PATH`, which self-heals a corrupt file to `.corrupt` and starts fresh
(`health.py:90-101`), `movement()` has no equivalent — the Movement panel goes silently and
permanently blank (`"No history yet"`, `:523`) until someone manually deletes the file. Given the
project already runs multiple dashboard-adjacent processes and the owner routinely has the page
open, this is a live, reachable failure mode, not a hypothetical.

---

## NEW — sweep.py:233-234: non-atomic write of a 13MB file three other modules read

**VERIFIED.** `sweep.py` writes its output with a bare truncating write:
```python
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False)
```
`OUT = data/CHARACTER_SWEEP.json`. On disk right now:
```
13M  data/CHARACTER_SWEEP.json
```
This is not a private scratch file — `hostcheck.py:375,763`, `magnitude.py:827`, and
`standards.py:828` all read it (`standards.py:838` calls it "the assay queue, the host fitness
roster, the chain's..."), and `foreman.py:600-611`'s `run_character_sweep()` launches `sweep.py`
as an **independent OS process** on a schedule ("Rebuild CHARACTER_SWEEP.json so downstream stages
see the re-catalogued cast"). A 13MB `json.dump` is not instantaneous — any of the three readers
hitting this file mid-write gets a truncated/invalid JSON, which is exactly the TWO-WRITER
CONTRACT this project's `silence.write_json`/`replace_retry` exist to prevent. `sweep.py` should
use one of them instead of the bare `open(OUT, "w")`.

---

## NEW — dead code: weave.py's superseded IDF-only pair-weighting is still shipped, unused

**VERIFIED by grep.** `weave.py`'s own docstring explains at length why raw source-IDF pairing was
replaced by name-surprisal weighting (it welded Cowboy Bebop to Thomas the Tank Engine via
"Gordon", Alien to pro wrestling via "Australia/Mexico/Iran"). But the old, known-buggy
`pair_weights()` (`:156-173`) and `null_threshold()` (`:249-273`) are still fully defined in the
file. Confirmed neither is called anywhere:
```
grep -rn "pair_weights\b|null_threshold\b" src/*.py   # only defs in weave.py; no callers
```
`weave.py`'s own `main()` (`:436-438`) and both production callers (`pipeline.py:1776-1778`,
`tiers.py:194-199`) use only `surprisal_pair_weights`/`null_threshold_surprisal`. Not a live bug,
but dead code that reproduces a documented-as-wrong algorithm sitting right next to its
replacement is exactly the shape of thing that gets copy-pasted back into use by a future patch
that doesn't read the docstring. Low severity, worth deleting.

Also (very low severity, same investigation): `pipeline.py:1774` unpacks `idf` from
`W.idf_table(index)` and never uses it in that function — dead value, not a bug.

---

## CONFIRMED / KNOWN — health.py

- **`health.py:124-144` (SAMPLES bare `except: pass`) — KNOWN.** Confirmed at source:
  ```python
  143        except Exception:
  144            pass          # the evidence bag must never break the ledger write
  ```
  Matches NEXT_STEPS.md §3 verbatim. The comment even states the intent (never break the LEDGER
  write) but the cost is that a torn `failure_samples.json` write drops the evidence bag
  permanently with no `.corrupt` self-heal, unlike `LEDGER_PATH` two blocks above it.

- **`health.py:179-181` (chars-per-token `/4`, `/3.7` vs `context_budget.py`'s real `4.0`/`3.0`)
  — KNOWN, confirmed at source both sides.** `check_context_budget()`:
  ```python
  sys_toks = len(R.SYSTEM) / 4
  body_toks = R.CHUNK / 3.7
  ```
  `context_budget.py` (the module whose values preflight is supposed to be checking against) sets
  `PROSE_CHARS_PER_TOKEN = 4.0` (matches the `/4`, close enough) but `CHARS_PER_TOKEN = 3.0` for
  content — the *smaller* ratio is the conservative/pessimistic one (fewer chars per estimated
  token → larger estimate → earlier refusal). `health.py`'s `3.7` is measurably more permissive
  than the real `3.0` the runtime budget actually enforces, so this preflight check can read
  "ok" on a chunk size the real `context_budget.assert_fits()` would refuse. Also omits
  `JOB_OVERHEAD_CHARS`/scaffolding-split logic (`context_budget.system_for`/`reserve_for`)
  entirely — it's a hand-rolled parallel estimate of a budget that already has a canonical,
  more-accurate implementation two imports away.

- **NEW, minor — `health.py:241` `files[:200]` cache-emptiness sample is unsorted.**
  `files = glob.glob(os.path.join(root, host, "*.json"))` is **not** `sorted()` (unlike
  `check_control_chars`'s glob two functions above, which is). The 200-file sample is therefore
  whatever order the OS directory enumeration happens to return — not alphabetical, not random,
  undocumented. The check only fires when **all** sampled files are empty, so this is a low-risk
  heuristic (advisory preflight signal, not a data truncation), but it's still a `[:N]` sample
  over an unordered listing in a project whose Hard Rule 0 is written with zero exceptions.
  UNVERIFIED as a live false-negative/positive (would need a host with >200 files and a
  order-correlated emptiness pattern to prove it fires wrong), flagged for completeness.

---

## CONFIRMED / KNOWN — dashboard.py (remaining items from the brief)

- **`dashboard.py:332,420-425` — standards-crash renders as a fabricated "-N" regression — KNOWN,
  confirmed at source.** `state()` (`:416-427`) wraps `standards.check(s)` in try/except; on
  exception `s["standards"] = []` (`:425`). `movement()`'s `keys["standards met"]` (`:332`) is
  `sum(1 for x in (...) if x.get("holds"))` over that same list — an exception silently becomes
  `0`, indistinguishable in the Movement panel from every standard genuinely failing at once. If
  standards were previously holding N, the next reading shows `delta = -N`, rendered in red as a
  real regression (`panelMovement` `cls='down'`, `:531`).

- **`dashboard.py:150-168` `throughput()` — KNOWN, confirmed at source.** On any exception
  (bad `cascade_scratch.db`, missing table, etc.) it falls through to the same
  `{"window_min":…, "calls":0, "per_hour":0, "buckets":[]}` shape a genuinely idle system
  produces — no error field, unlike its sibling `quotas()` (`:143-146`), which appends an explicit
  `{"bucket": f"quota read failed: ..."}` row on failure. `panelSpend` (`:598-607`) renders both
  cases identically as "Nothing has called out recently."

- **`dashboard.py:341-342` `HISTORY[-2000:]` retention — KNOWN, now quantified.** Poll interval is
  fixed in the page's own JS: `tick();setInterval(tick,5000)` (`:677`) — 5 seconds. Each
  `/api/state` hit appends one row. For **one** open dashboard client: 2000 rows ÷ (1 row/5s) =
  10,000s = **166.7 minutes (2.8h)** of retention — safely above the 30-minute `MOVED_WINDOW_MIN`
  stall threshold. Retention is inversely proportional to the number of concurrent pollers hitting
  `/api/state` (browser tabs, curl loops, monitors): retention_minutes ≈ 166.7 / N. **At N≈6
  concurrent pollers, retention drops to ~27.8 minutes — below the 30-minute stall window** — at
  which point `older = [h for h in hist if h.get("at",0) <= window]` (`:352`) can come up empty
  and `base` falls back to `hist[0]` (`:353`), silently changing what "the delta" is measured
  against without any indication in the UI that the window degraded. (This is now compounded by
  the concurrency-corruption finding above — concurrent pollers hit both bugs from the same
  cause.)

---

## Modules read end to end and found CLEAN this run

- **`cosmography.py`** (282 lines, full read). Pure computation module, no writes, no caching, no
  caps. `validate()` correctly refuses physically-impossible censuses (Type III > galaxies, etc.);
  `KARDASHEV_MIX` sums to exactly 1.0 and is checked. No findings. Matches prior-run CLEAN listing.
- **`thread_integrity.py`** (184 lines, full read). The asymmetric-vs-reciprocal classification
  logic is careful and internally consistent with its own documented caveats (Hard Rule 5,
  `recorded=None` today). `load_entities()` and `implied_threads()` have appropriate per-file
  exception handling. No findings. Matches prior-run CLEAN listing.
- **`compress_store.py`** (65 lines, full read). `store()`'s `open(path, "wb")` write is
  technically non-atomic, but paths are content-hash-addressed (`content_hash()`) and the sole
  caller (`generate.py:386`, one call per generated chapter) writes distinct content to distinct
  paths — no realistic collision/concurrent-writer scenario found. A crash mid-write could leave
  an unreadable blob at that hash with no self-heal, but this is low-probability and low-blast-
  radius (one chapter re-generates). Not escalated to a finding. Matches prior-run CLEAN listing.
- **`weave.py`** (487 lines, full read) — clean of live bugs; the one item raised above is dead
  code, not a live defect. The `max_sources=60` cap (`:161`, `:210`) matches the already-KNOWN
  NEXT_STEPS.md item and is explicitly documented/deliberate. The three `write_json` calls at
  `:472-481` are correctly atomic (fixed from a prior `json.dump(obj, open(path,"w"))` bug per the
  comment at `:469-471`).

## Not fully clean but no new finding beyond what's logged above

- **`sweep.py`** — `:20-22` docstring "strict funnel" claim is KNOWN (confirmed: `addressed`
  (has a shelfmark) is not actually a subset of `catalogued`, since shelving and cataloguing are
  independent). New finding filed above (`:233-234` non-atomic write).
- **`health.py`** — see KNOWN items above; `flush()`'s LEDGER write itself (`:119-123`) is
  correctly atomic via `silence.replace_retry` and correctly gates `LEDGER.clear()` on the rename
  landing — only the SAMPLES path (`:138-144`) and the context-budget estimate are defective.
- **`dashboard.py`** — see all items above.
