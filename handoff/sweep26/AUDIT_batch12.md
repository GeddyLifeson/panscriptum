# BATCH 12 audit — run26

Modules (2,463 lines total, read in full, no sampling):

| module | lines |
|---|---|
| dashboard.py | 731 |
| weave.py | 487 |
| catalogue_web.py | 403 |
| cosmography.py | 282 |
| sweep.py | 240 |
| thread_integrity.py | 184 |
| ledger.py | 136 |

---

## SPECIAL FOCUS A — dashboard.py `movement()` swallowing JSONDecodeError (82x and counting)

**Confirmed, and it is self-perpetuating.**

`movement()` (dashboard.py:314-363) does a single try/except around the ENTIRE read-modify-write
of `state/dashboard_history.json` (`HISTORY`):

```python
try:
    hist = []
    if os.path.exists(HISTORY):
        with open(HISTORY, encoding="utf-8") as f:
            hist = json.load(f)                 # <-- raises JSONDecodeError on a corrupt file
    hist.append(row)
    ...
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(hist, f)
    silence.replace_retry(tmp, HISTORY)
except Exception:
    silence.note("dashboard.py:movement")
    return []
```

Because the `json.load(f)` call sits *inside* the same try block as the write-back, a
`JSONDecodeError` aborts the whole function before `hist.append(row)`, before the tmp file is
written, and before `silence.replace_retry` ever runs. **The corrupt file is never repaired.**
Every subsequent call — and `/api/state` is polled every 5 seconds by the page's own `setInterval`
— hits the identical `JSONDecodeError` on the identical bytes, forever. That is exactly the growth
pattern of a ledger entry sitting at 82 (and climbing at ~12/minute while the dashboard tab stays
open).

**Label match confirmed against `silence.note`/`health.record`:** `silence.note(site)` at
silence.py:290 calls `health.record(f"silent:{site}", name, ...)` where `name = exc.__name__`.
With `site="dashboard.py:movement"` and `name="JSONDecodeError"`, the ledger key is built as
`f"{kind}:{detail}"` = **`silent:dashboard.py:movement:JSONDecodeError`** — exactly the key named
in the brief.

**What the caller sees:** `state()` (dashboard.py:416-427) does `s["movement"] = movement(s)`
unconditionally — no flag, no error field, nothing distinguishes this return from any other `[]`.
The only *other* path that can return `[]` is a first-ever run before `HISTORY` exists — but that
path does NOT actually return `[]` (a fresh file writes fine and falls through to the delta
computation, producing entries with `delta: 0`, not an empty list). So in practice **an empty
`movement` array now means, structurally, only one thing: the read/write pipeline threw.** The
front end (dashboard.py:520-538, `panelMovement`) can't tell that apart from "no history yet" and
prints the wrong message: *"No history yet. Deltas appear after the second reading."* — which is
false; there is plenty of history, it's just wedged.

**Fix:** isolate the read from the write so a decode failure resets rather than aborts:

```python
hist = []
if os.path.exists(HISTORY):
    try:
        with open(HISTORY, encoding="utf-8") as f:
            hist = json.load(f)
    except (json.JSONDecodeError, OSError):
        silence.note("dashboard.py:movement:corrupt-history")
        hist = []          # self-heal: next successful write replaces the corrupt file
hist.append(row)
... (write unconditionally, as before)
```
This lets the very next tick produce a fresh, valid `HISTORY` file instead of failing identically
forever. Optionally surface a `"history_reset": true` flag in the returned movement data so the
panel can say "history file was corrupt; reset" instead of silently reading as day-one.

## SPECIAL FOCUS B — the stall rule and the −3689 chunks delta

**The stall rule, dashboard.py:361-362:**
```python
out.append({"metric": k, "now": v, "delta": delta,
            "minutes": round(span), "stalled": delta == 0 and span >= 10})
```

Confirmed: **one rule, one window (`MOVED_WINDOW_MIN = 30`), one threshold (`span >= 10` minutes),
applied identically to all six metrics** (`cited`, `settled`, `feats`, `entities read`, `chunks`,
`standards met`) regardless of how often their sources actually update. Per the file's own
`_library()`/`jobs()` code (verified directly, not just by comment):

- `cited` / `settled` / `feats` come from `data/COVERAGE.json` (dashboard.py:255-265), a file
  written once per supervisor cycle (confirmed: only `coverage.py` writes it, from `overnight.py`
  / `allsweep.py` / `pipeline.py` all treat it as a periodic, not live, artifact).
- `entities read` comes from a live recursive glob over `data/readfeats/**/*.json`
  (dashboard.py:271-276).
- `chunks` comes from a live tail-match against `state/read_auto.log` (dashboard.py:196-206,
  `_read_row`/`RE_READ`).

So the claim in the brief is correct, and the bug is real: a supervisor-cycle metric that hasn't
updated in 10+ minutes is *expected* to read `delta == 0` between cycles (that's normal cadence,
not a stall), while the same rule applied to a live log-tail metric is a meaningful signal. One
threshold conflates the two — coverage-derived metrics will read `stalled: true` as a matter of
routine between supervisor cycles, and that false alarm has the same visual weight (red "NO
CHANGE") as a genuinely wedged corpus reader.

**Does a negative delta count as "moved"?** Yes — `stalled` requires `delta == 0` exactly, so
`delta == -3689` trivially satisfies `stalled: False`. The rule has no floor/direction check; any
nonzero delta, including a large regression, reads as "moved" (and the front end just colors it
red and prints the raw negative number — dashboard.py:531, class `down`).

**Is chunks actually monotonic, and is the fall a real bug or a mis-compared metric?**
Traced into `src/read.py`: `run()` (read.py:968) initializes `done = {"n": 0, ..., "chunks": 0,
...}` (read.py:974) as a **local variable, fresh on every call to `run()`**. `CHUNK_BUDGET` is
likewise recomputed fresh per run (read.py:1043-1045). Neither value is persisted to disk or
carried across process restarts — `done["chunks"]` is a purely in-process, per-invocation counter
that the log line prints as `chunks X/Y` (matched by `RE_READ`, dashboard.py:58-62).

**Verdict: this is a metric that must not be compared this way, not an upstream bug in read.py.**
`done["chunks"]` is monotonic *only within one continuous run of the `read.py --run` process*. If
the supervisor restarts the reader (crash, redeploy, manual kill) between two dashboard samples,
the new process's counter starts back at 0 and climbs from there — a completely healthy restart
produces exactly the shape reported: a large negative delta with no corruption anywhere.
`movement()` has no run-id, no process-start timestamp, and no restart detection; it diffs the raw
log-tail value across time unconditionally. The fix belongs in `movement()`/`_read_row`, not in
`read.py`: either (a) have `read.py` print a run-start timestamp or PID in its progress line so
`movement()` can detect a restart and report "job restarted, N chunks into this run" instead of a
raw negative delta, or (b) at minimum, treat `delta < 0` on a monotonic-per-run counter as "reset"
rather than "regression" in the stall/movement classification (`stalled` should never be computed
from a negative delta on this metric the same way it is on a level metric like `cited`).

**Bonus finding while tracing this — quota panel has the identical failure shape as Focus A.**
`quotas()` (dashboard.py:101-147) initializes `worst = 1.0` per bucket (dashboard.py:131) and only
lowers it inside the `for name, v in (st.get("remaining") or {}).items(): ... windows.append(...)`
loop. If `router.model_status(m)` succeeds (no exception, so nothing is noted) but returns an
empty or partially-populated `remaining` dict — e.g. a transient read failure inside Cascade's own
accounting that doesn't raise — `windows` stays `[]` and `worst` stays at its initial `1.0`. The
front end reads `worst` of `1.0` as **"100% left" / pill "ok"** (dashboard.py:587-588): a quota
read that silently produced no data is indistinguishable from a bucket that is genuinely fully
funded. This is the exact "swallowed failure indistinguishable from success" pattern named in the
audit brief, and it defeats the dashboard's own stated purpose (its docstring opens by describing
exactly this failure mode: a bucket silently exhausted with "nothing in any log to say why").
Recommend: default `worst = None` (or add a `no_data: true` marker) rather than `1.0`, and have
the front end render "no data" distinctly from "unlimited"/"exhausted".

---

## SPECIAL FOCUS — ledger.py M18 (top-rung `hi == lo` collapse)

**Confirmed still present, exactly as described.** `assay_to_standards()`, ledger.py:116-136:

```python
i = LADDER.index(magnitude_band)
lo = BAND_EDGES[magnitude_band]["ruin"]
hi = BAND_EDGES[LADDER[min(i + 1, len(LADDER) - 1)]]["ruin"]
joules = math.exp(math.log(lo) + (ruin_score / 10.0) * (math.log(hi) - math.log(lo)))
```

`LADDER = ["M0", ..., "M10"]` (assay.py:105) — 11 rungs, `LADDER.index("M10") == 10 ==
len(LADDER) - 1`. For `magnitude_band = "M10"`: `min(i+1, len(LADDER)-1) = min(11, 10) = 10 = i`,
so `hi = BAND_EDGES["M10"]["ruin"] == lo`. Then `math.log(hi) - math.log(lo) == 0.0`, and:

```
joules = exp(log(lo) + (ruin_score/10) * 0) = exp(log(lo)) = lo
```

for **every** value of `ruin_score`. At the top rung the function silently returns the M10 floor
regardless of the score passed in — `assay_to_standards("M10", ruin_score=0.1)` and
`assay_to_standards("M10", ruin_score=9.9)` return identical `joules`/`standards`. No exception,
no warning; the parameter is accepted and discarded. **M18 is still open.**

Fix needs a real upper bound for the top rung — e.g. extrapolate using the same per-rung
log-spacing as the M9→M10 interval (`hi = lo * (BAND_EDGES["M10"]["ruin"] /
BAND_EDGES["M9"]["ruin"])`) rather than reusing `lo` itself, or document M10 as open-ended and
raise/require an explicit `hi` override instead of silently flattening.

---

## SPECIAL FOCUS — catalogue_web.py progress emission / no per-source cap

**No cap confirmed.** `MAX_PER_SOURCE = None`, `MAX_PER_CATEGORY = None`,
`CATEGORY_SCAN_DEPTH = None` (catalogue_web.py:53-58), and the code actively guards against
reintroduction: `if MAX_PER_SOURCE is not None: raise SystemExit(...)` (catalogue_web.py:226-229).
Traced every call beneath `catalogue()`: `ws.category_members(sub, c, limit=None)`,
`ws.rank_by_size(sub, titles, top=None, ...)`, `ws.page_texts(sub, wanted, ...)`,
`ws.find_categories(sub, canon)` (default `limit=None`) — none truncate. Confirmed clean.

**Progress emission is NOT on every long path — `catalogue_composite()` was missed by the fix.**
`catalogue()` (the single-wiki path) wires `_beat()` progress callbacks through
`ws.category_members` (after each category), `ws.rank_by_size(..., progress=lambda d,t:
_beat(...))`, and `ws.page_texts(..., progress=lambda d,t: _beat(...))` — confirmed both
`rank_by_size` and `page_texts` in wiki_source.py actually invoke their `progress` callback
per-batch/per-completion (wiki_source.py:495-496, 613-614), which is what stops
`kill_stalled_job` from killing a big source.

`catalogue_composite()` (catalogue_web.py:87-148) — used for `ws.COMPOSITE_SOURCES` (currently
just `"major fantasy pantheons"`, 13 sub-wikis) — calls the exact same slow primitives but
**without any progress plumbing at all**: `ws.category_members(sub, c, limit=None)` (line 100,
no beat before/after), `ws.rank_by_size(sub, titles, top=None)` (line 105, **no `progress=`
argument passed**), `ws.page_texts(sub, wanted)` (line 113, **no `progress=`argument passed**).
The only output is one `print(f"      {sub:24s} {got:4d}")` per whole sub-wiki, after every
category, rank, and fetch for that sub-wiki has already finished. If any of this source's 13
sub-wikis has a large "Gods"/"Deities" category, this path can go silent for the same multi-minute
stretches the run-#25 fix was written to eliminate, and — because it's dispatched through the
same `catalogue()`/`--recatalogue` process and log as the fixed path — `kill_stalled_job` can
still kill it. In current practice the pantheon categories are modest (tens to low hundreds of
members, not DC's 33,614), so the exposure is smaller than the primary path's was, but the
starvation-loop fix is structurally incomplete: it was applied to one of the two catalogue
functions, not both. Fix: thread the same `_beat` callback through `catalogue_composite()`'s
`category_members`/`rank_by_size`/`page_texts` calls exactly as `catalogue()` does.

---

## Other findings, by module

### dashboard.py

- **MAJOR — unlocked concurrent read-modify-write on `state/dashboard_history.json`.**
  `Server` is a `socketserver.ThreadingTCPServer` with `daemon_threads = True`
  (dashboard.py:708-710): every `/api/state` request runs in its own thread, and `Handler.do_GET`
  calls `state()` → `movement()` synchronously per request with **no lock** around the
  read-`HISTORY`-append-write-`replace_retry` sequence (dashboard.py:335-349). Two overlapping
  requests (e.g. two open dashboard tabs, or a script polling `/api/state` alongside a browser,
  both firing within the same ~5s window) can both read the same `hist`, both append their own
  row, and the second `silence.replace_retry(tmp, HISTORY)` clobbers the first — one sample is
  silently lost. Worse, both threads write to the **same fixed tmp path** (`HISTORY + ".tmp"`,
  dashboard.py:343) with no per-thread/per-pid suffix, so one thread's write can be
  read-back-then-overwritten by the other before its own `os.replace` lands, risking a torn
  intermediate state being promoted to `HISTORY` proper. Given the dashboard's own docstring
  explicitly anticipates multiple simultaneous consumers ("this page cannot disagree with the
  system it is reporting on"), this is a real, not hypothetical, race. Fix: guard the
  read-modify-write with a `threading.Lock()` (module-level, same pattern used elsewhere in this
  codebase, e.g. `sweep_plan._RECORD_LOCK`).

- **MINOR — `_TTL_MEMO` (dashboard.py:219-232) is read/written from multiple request threads with
  no lock.** In CPython this won't corrupt the dict, but two threads can both miss an expiring TTL
  and both call the (moderately expensive) `fn()` concurrently, defeating part of the point of the
  memo. Low severity — worth a lock only if `library()`/`watch()` grow more expensive.

- **QUESTION — `watch()`'s `swallowed` table caps to the top 6 offenders**
  (`sorted(f.items(), key=lambda kv: -kv[1])[:6]`, dashboard.py:301) while `swallowed_total`
  (line 302) reports the true sum. This is a display cap on a panel, not a Hard-Rule-0 data cap
  (nothing about the library's own catalogue), and the true total is preserved — but on a
  dashboard whose entire purpose is surfacing failures that would otherwise go unnoticed, a
  moderate-frequency-but-real failure sitting at rank 7 stays invisible on the page indefinitely.
  Worth confirming this is the intended tradeoff.

### weave.py

- **MINOR — dead code.** `pair_weights()` (weave.py:156-173) and `null_threshold()`
  (weave.py:249-273), the original idf-weighted pair-scoring functions, are unused anywhere in the
  repo — `main()`, `pipeline.py:1778`, and `tiers.py:199` all call `surprisal_pair_weights()` /
  `null_threshold_surprisal()` instead (confirmed via repo-wide grep). The module's own docstring
  even explains why idf was superseded by name-surprisal (weave.py:124-139: "Source-level idf
  cannot answer that"). Neither function is exported for external use either. Candidate for
  removal, or at least a comment marking them superseded/retained-for-reference.

- **QUESTION — `filtered_index()` (weave.py:176-202) gates an entity's presence in the whole
  corpus on `hits[0]` alone.** `index[key]` is a list of occurrences across every source that uses
  that name; the mechanic/statblock/rules-voice filters only inspect `hits[0]["name"]` and
  `hits[0]["description"]`. If the *first* occurrence (order is whatever `ENTITY_INDEX.json`
  happens to store) reads as a stat block or instructional voice, the entity is dropped
  (`dropped += 1`, `continue`) for **every** source that shares the key — including sources whose
  own hit is clean prose about a genuine character. Given the whole module's thesis is "a shared
  name is not an identity," gating on one arbitrary occurrence's phrasing rather than any
  per-source vote seems worth confirming is intentional rather than an oversight.

- **MINOR — statblock/rules-voice detection windows description text at 400/300 chars**
  (`desc[:400]`, `desc[:300]`, weave.py:197-198). A description whose stat-block/instructional
  markers appear after the first 300-400 characters (e.g. flavor prose first, mechanics appended
  later) would pass the gate undetected. Likely fine in practice (both regexes are meant to catch
  openers) but worth a note since it's a silent false-negative window, not a hard cutoff on data
  actually retained.

### catalogue_web.py

- **MINOR — `slug()` (catalogue_web.py:66-67) truncates to 60 characters for the on-disk record
  filename** (`RECORDS/slug(name)+".json"`, line 385). Two different, sufficiently long source
  names that share the same normalized 60-character prefix would collide and one record would
  silently overwrite the other. Given ~215 sources on the current roll this is unlikely to have
  fired yet, but it's an unguarded collision surface with no check.

### sweep.py

- **MAJOR — non-atomic write to `data/CHARACTER_SWEEP.json`, which is read live by three other
  modules.** `main()` (sweep.py:227-236) writes the output with a plain
  `open(OUT, "w", encoding="utf-8")` + `json.dump(rows, f, ...)` — no tmp file, no
  `silence.replace_retry`. Confirmed by repo-wide grep that `CHARACTER_SWEEP.json` is read,
  unguarded, by `hostcheck.py` (:375, :763), `magnitude.py` (:827), and `standards.py` (:842) —
  exactly the pattern this codebase's own comments elsewhere flag as dangerous (see
  `catalogue_web.py:76-79`'s `save_roll()` note: "A truncating write interrupted mid-dump
  therefore does not degrade anything gracefully — it kills the next run of either script
  outright," and `weave.py:469-471`'s recent fix for the identical issue on
  `CONTINUITY_GROUPS.json`/`RESOLVED_ENTITIES.json`/`SHARED_STAGE_GRAPH_IDF.json`). Any reader
  that opens `CHARACTER_SWEEP.json` while `sweep.py` is mid-write (large file — the tool prints
  its own size at the end, routinely tens of MB for ~45,000 person entries) can read a truncated
  JSON document and raise, or — depending on the reader's own error handling — silently treat a
  parse failure as "no data." Fix: switch to `silence.write_json(OUT, rows, ensure_ascii=False)`,
  matching every other writer in this codebase.

- **MINOR — `cache_path()` (sweep.py:58-60) duplicates `feats.py:733-734`'s cache-path formula
  by hand instead of importing it.** Currently byte-for-byte identical (`re.sub(r"[^A-Za-z0-9]+",
  "_", host)[:40]` / `[:80]` on both sides — verified against feats.py directly), so reads
  correctly today, but it's a second, unlinked copy of a path-construction rule; a future change
  to `feats.py`'s cache layout would silently desync this reader (the "second silently-drifting
  source of truth" pattern this codebase explicitly names elsewhere — see `ledger.py:38-41`).

- Report-only truncations (`report()`'s `top=18` deepest-evidence table, `most_common(10/8)` gap
  tables, `[:29]`/`[:60]` column widths) are legitimate display bounds — the full `rows` table is
  written to `CHARACTER_SWEEP.json` unconditionally and unsliced. Not Hard Rule 0 violations.

### thread_integrity.py

- **MINOR — duplicated magic constant instead of calling the shared conversion.**
  `classify()` (thread_integrity.py:127) computes `d * 1000.0 > event_age_years` inline rather
  than calling `propagation.arrival_years(d)` (propagation.py:130-132), which does
  `distance * YEARS_PER_UNIT_DISTANCE` where `YEARS_PER_UNIT_DISTANCE = 1000.0` — confirmed the
  values currently agree, but `main()` already does `import propagation as P` in the very same
  scope (thread_integrity.py:152), so calling `P.arrival_years(d)` instead of re-deriving the
  same formula by hand costs nothing and removes exactly the drift risk this codebase's own
  comments elsewhere warn about (ledger.py:38-41, same pattern).

- No caps found in `load_entities()`, `implied_threads()`, or `classify()` — all iterate full
  sets; the only `[:N]` slices are in `main()`'s console summary printing, which is display-only
  (the underlying `counts`/`detail` dicts used by any caller of `classify()` directly are never
  truncated).

### cosmography.py

- Clean. No caps, no bare excepts, no subprocess calls, no mutable shared state. `validate()`'s
  physical-impossibility checks (galaxies/stars/habitable-world ceilings, `KARDASHEV_MIX` summing
  to 1.0) are real invariant checks that can actually fail and do raise
  (`census()` at cosmography.py:206-209) — not a guard that can never fire. No `main()`/CLI in this
  module; it's a pure library imported by other tools (`kardashev_to_magnitude` is used against
  `assay.BAND_EDGES`/`LADDER` the same way `ledger.py` does — no drift observed between the two
  call sites' understanding of the ladder shape).

### ledger.py

- Beyond M18 (above): `assay_to_standards()` takes `ruin_score` with no bounds check — values
  outside roughly `[0, 10]` extrapolate past the rung's own `[lo, hi]` band silently rather than
  clamping or raising. Low severity (the function is a `𝔄`-to-currency helper, not part of the
  scoring pipeline itself, and out-of-range inputs would be a caller bug), but worth a comment or
  an assert given how easy the M10 collapse above was to miss for the same "silently returns a
  number" reason.

---

## Summary

Two-writer-contract violations found in this batch: **sweep.py's `CHARACTER_SWEEP.json` write**
(non-atomic, read live by 3 other modules). dashboard.py's own `HISTORY` write already uses
`silence.replace_retry` correctly but has no cross-thread lock around the read-modify-write,
which is a distinct (concurrency, not atomicity) bug given the server is explicitly threaded.

Confirmed open: ledger.py M18 (top-rung score-irrelevance), catalogue_web.py's progress-emission
fix not extended to `catalogue_composite()`, dashboard.py's `movement()` JSONDecodeError
self-perpetuation, and the chunks-metric cross-restart comparison bug plus its twin in the quota
panel's silent-empty-defaults-to-healthy behavior.
