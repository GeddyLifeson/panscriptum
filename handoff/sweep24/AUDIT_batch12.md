# Audit batch 12 — run #24 whole-tree sweep

Files in this batch and read completeness:

- `src/overnight.py` (720 lines) — read in full, every line.
- `src/weave.py` (487 lines) — read in full, every line.
- `src/health.py` (403 lines) — read in full, every line.
- `src/context_budget.py` (278 lines) — read in full, every line.
- `src/burgs.py` (235 lines) — read in full, every line.
- `src/descending_ladder.py` (186 lines) — read in full, every line.
- `src/ledger.py` (136 lines) — read in full, every line.

Cross-referenced against `src/assay.py` (LADDER/BAND_EDGES) and `src/silence.py`
(`write_json`/`replace_retry`) to verify claims, and ran `ledger.assay_to_standards`
directly against the live source to confirm the M10 finding numerically.

---

## overnight.py

### MAJOR — overnight.py:414-428 `coverage_snapshot()` never checks subprocess returncode — VERIFIED

```python
def coverage_snapshot():
    try:
        subprocess.run([PY, os.path.join(SRC, "coverage.py")], cwd=HERE,
                       capture_output=True, text=True, timeout=1800, ...)
        rows = json.load(open(os.path.join(HERE, "data", "COVERAGE.json"), encoding="utf-8"))
    except Exception as e:
        ...
        return {"error": ...}
    n = sum(r["entries"] for r in rows)
    ...
```

`subprocess.run(...)` does not raise on a non-zero exit (no `check=True`); the function goes
straight to reading `data/COVERAGE.json` regardless of whether `coverage.py` actually ran
successfully this cycle. If `coverage.py` crashes, is killed, or exits non-zero without
touching the file, `COVERAGE.json` still holds whatever the *previous* successful run wrote,
`json.load` succeeds, and `coverage_snapshot()` returns those STALE numbers as if they were
freshly measured. Only a case where the file is literally missing/corrupt/unparseable trips
the `except` branch. A crash that leaves the file intact is indistinguishable from a clean
pass. This snapshot is appended to `history` and rendered into `STATUS.md`'s per-cycle table
(`write_status`) — so a morning read of "citation coverage" can be silently re-reporting a
number from hours or cycles earlier while claiming to be current, with no distinguishing mark
in the file itself (only a difference from what the log line would say, if anyone diffed it).

### MAJOR — overnight.py:431-455 `preflight()` never checks subprocess returncode — VERIFIED

```python
def preflight():
    try:
        r = subprocess.run([PY, os.path.join(SRC, "health.py"), "--preflight"], ...)
        out = r.stdout
    except Exception as e:
        ...
        return 0, False
    for ln in out.splitlines():
        if ln.strip().startswith("FAIL"):
            log(f"    preflight {ln.strip()}")
    blocking = "control characters in source" in out and "FAIL  control" in out
    n = out.count("FAIL")
    return n, blocking
```

Same shape as `coverage_snapshot()`. `r.returncode` is read nowhere. If `health.py --preflight`
crashes (uncaught exception, import error, etc.) after printing partial or no output but before
Python raises anything `subprocess.run` itself would catch, `r.stdout` is simply whatever was
flushed before the crash — commonly empty or truncated. Empty stdout means zero `"FAIL"` lines
and `blocking=False`, `n=0` — which is exactly the return value `main()` treats as a clean pass
("all checks pass", no halt). A `health.py` that died on line one is thus indistinguishable from
a library with nothing wrong. The `except Exception` branch (subprocess launch failure, timeout)
is explicitly and correctly instrumented with a "DID NOT RUN" log line per an m-run comment
already in the file — but a crash *inside* a spawned-and-returned subprocess (rc != 0, stdout
short) takes neither path and is silently graded a pass. This is precisely the "crashed
coverage.py or health.py re-reports STALE/absent data as a fresh pass" defect on record.

### MAJOR — overnight.py — `read.py` excluded from the keeper's STANDING set; no stall detection — VERIFIED

`STANDING` (overnight.py:372-380) contains only `dashboard`, `publish`, `foreman`, `overwatch`,
`pipeline`. `read.py` (and `feats.py --roll`) are listed only in `ALL_JOBS`
(overnight.py:387-389), which nothing acts on to restart — it exists purely as the "what
should be up" answer for other tools (per its own comment). The `_keep()` thread
(overnight.py:509-522) wakes every 300s and restarts anything in `STANDING` found down; `read.py`
is invisible to it by construction.

Mechanism and gap size, traced through `main()`'s cycle body (overnight.py:586-713):
- `read.py` is launched synchronously via `run("read", ..., timeout_h=a.read_hours)`
  (overnight.py:657-659, default `--read-hours 3.0`). `run()` blocks on `p.wait(timeout=...)`.
- If `read.py` **crashes** (raises/exits non-zero) quickly, `p.wait()` returns as soon as the
  child exits, `run()` logs `finished rc=...`, tails the log, and the cycle proceeds immediately
  to `join(roll)` and then `run(pipeline, ..., timeout_h=2)` — `read.py` is NOT relaunched until
  the next cycle's top, which does not begin until: `join(roll)` (up to 4h), `run(pipeline)`
  (up to 2h), plus `foreman_report`/`watch_report`/`ledger_report`/`coverage_snapshot()`
  (bounded 1800s) all complete. Worst case measured against the code's own timeouts: a `read.py`
  crash near the start of its window can leave it down for **up to roughly 6 hours** (4h roll +
  2h pipeline + preflight/coverage overhead) before the next cycle's `start`/`run` call for
  `read` fires again.
- If `read.py` **hangs** (wedges without exiting) instead of crashing, nothing notices until
  `run()`'s own `timeout_h` (default 3.0h) expires, at which point `run()` kills it — this is
  the *only* stall detection `overnight.py` has for `read.py`, and it is a fixed wall-clock cap
  on the subprocess call, not a liveness/progress check. There is no heartbeat, no output-rate
  check, no "no new pages in N minutes" watchdog for the reader anywhere in this file.

So: confirmed mechanism (STANDING excludes read.py; keeper never restarts it), confirmed gap
size (hours, bounded above by roll+pipeline timeouts, not by any stall detector), and confirmed
`overnight.py` carries no stall/liveness detection of its own for `read.py` beyond the blunt
per-call timeout that only fires on true hangs, never on fast crashes followed by cycle-shaped
silence.

### MINOR — overnight.py:462 non-atomic write of STATUS.md, read by a concurrent process — VERIFIED

```python
def write_status(cycle, history):
    p = os.path.join(HERE, "STATUS.md")
    cur = history[-1] if history else {}
    ...
    with open(p, "w", encoding="utf-8") as f:
        f.write(...)   # multiple .write() calls follow, building the file incrementally
```

Plain truncate-then-fill, not `silence.write_json`/`replace_retry`. `STATUS.md` is in
`publish.py`'s `COPY_FILES` tuple (`publish.py:135`) and is copied to the public export tree
every 10 minutes by the standing `publish` job (`start("publish", ..., "--loop", "10", ...)`,
overnight.py:610-611) — a separate OS process from the supervisor. A copy landing mid-write can
pick up a torn/partial `STATUS.md` (e.g. only the header and half the coverage table). Lower
severity than the ledger/samples writes below because `STATUS.md` is regenerated wholesale every
cycle (a torn copy self-heals at the next publish tick, and nothing parses it for control flow
per the file's own comment at overnight.py:678), but it is still the exact write pattern the
project's own `silence.write_json` docstring was created to eliminate, on a file with a
confirmed concurrent reader.

### Clean / not a bug — the `running()` self-exclusion and basename-matching logic

Read fully; the `include_self` design, the pid-vs-basename matching, and the `_proc_lines()` TTL
cache are consistent with their extensive docstrings and I found no discrepancy between the
documented failure modes (already fixed per the docstrings) and the current code.

---

## weave.py

### MINOR — weave.py:205-226 `max_sources=60` filter excludes high-frequency entities from all pair evidence — VERIFIED (design tension with Hard Rule 0, not a truncation bug)

```python
def surprisal_pair_weights(occ, sur, min_sources=2, max_sources=60):
    for k, srcs in occ.items():
        if not (min_sources <= len(srcs) <= max_sources):
            continue
        ...
```

Any entity attested in more than 60 of ~211 sources is skipped entirely — it contributes zero
weight to every pair it could otherwise connect, and never appears in any `shared[pair]` list on
its own account. This is a real, present cutoff (confirmed at both `pair_weights` line 161 and
`surprisal_pair_weights` line 210, and reused identically as the `keys` filter in
`null_threshold`/`null_threshold_surprisal`). It is justified in-line as a stopword-style filter
("a common noun by any reasonable reading") rather than as a sampling truncation of a roster, and
it does not drop entities from the entity index itself (`ENTITY_INDEX.json`) or from
`RESOLVED_ENTITIES.json` — only from *evidentiary weight* in continuity clustering. That is a
materially different thing from the roster/page/chunk-list truncations Hard Rule 0 names, but it
is still an un-overridable ceiling ("60") baked into a statistical judgment that CLAUDE.md's Hard
Rule 0 says should never exist without being surfaced for sign-off ("no cap... ever"), and it is
not documented anywhere outside a code comment. Recommend flagging to the owner for an explicit
ruling rather than treating this as pre-cleared, since the two known-fixed truncations elsewhere
in this exact file (the `shared[p]` list caps at weave.py:171 and :217-225) were found and fixed
specifically because a stopword-shaped filter had been mistaken for compliance before.

### Clean — the two previously-flagged `shared[p]` truncations are fixed

Both `pair_weights` (line 170-172) and `surprisal_pair_weights` (line 217-225) now append the
whole `shared[p]` list with no cap, and both carry a comment dated 2026-08-25 explaining the
prior `if len(shared[p]) < 8` truncation and its discovery. Confirmed no residual truncation.

### Clean — atomic writes

`main()`'s `--write` path (weave.py:468-482) uses `silence.write_json` for all three outputs
(`CONTINUITY_GROUPS.json`, `RESOLVED_ENTITIES.json`, `SHARED_STAGE_GRAPH_IDF.json`), each with a
comment dated 2026-08-25 noting the prior `json.dump(obj, open(path, "w"))` leaked-handle bug.
Confirmed fixed, not a live finding.

---

## health.py

### MAJOR — health.py:124-144 `flush()`'s SAMPLES write self-heal is missing on the READ side — VERIFIED, matches known suspect

```python
if _SAMPLES:
    try:
        old = {}
        if os.path.exists(SAMPLES_PATH):
            with open(SAMPLES_PATH, encoding="utf-8") as f:
                old = json.load(f)
        for k, ring in _SAMPLES.items():
            merged = (old.get(k) or []) + ring
            old[k] = merged[-SAMPLES_KEEP:]
        stmp = SAMPLES_PATH + ".tmp"
        with open(stmp, "w", encoding="utf-8") as f:
            json.dump(old, f, indent=1, sort_keys=True, ensure_ascii=False)
        if silence.replace_retry(stmp, SAMPLES_PATH):
            _SAMPLES.clear()
    except Exception:
        pass          # the evidence bag must never break the ledger write
```

The WRITE half is correctly atomic (`.tmp` + `replace_retry`, matching the counts-ledger fix
just above it). But the whole block — including the READ of a possibly-torn
`failure_samples.json` — sits inside one `try` whose `except Exception: pass` has no self-heal
path. The counts ledger (`LEDGER_PATH`, lines 90-101) explicitly handles an unreadable file by
renaming it to `.corrupt` and starting fresh, with a `print(..., file=sys.stderr)` saying so.
`SAMPLES_PATH` has no equivalent: if `json.load(old)` throws on a torn/corrupt samples file, the
whole block — read AND write — is abandoned silently, `_SAMPLES` is never cleared (so the ring
retries next flush, at least), but if the corruption is durable (the file itself is permanently
bad, e.g. truncated to 0 bytes by an old crash), every subsequent flush hits the same exception
forever and the evidence bag ("the last few concrete examples" behind every failure class) is
permanently and silently lost, in the one module whose stated purpose (health.py:3, 17-20) is
"no silent failures." The comment on line 133-137 already describes this exact scenario as a
live risk ("Once torn, every future flush hits the blanket `except` below... the evidence bag
going quietly empty and staying that way, with nothing recorded anywhere") — confirming this is
a known, still-open gap, not a resolved one. Severity: MAJOR because it is a documented,
self-acknowledged silent-failure path inside the project's own anti-silent-failure module.

### MAJOR — health.py:179-181 `check_context_budget()` uses its own chars-per-token constants that shadow and disagree with context_budget.py — VERIFIED, matches known suspect

```python
def check_context_budget():
    ...
    ctx = cfg.get("num_ctx", 6144)
    sys_toks = len(R.SYSTEM) / 4
    body_toks = R.CHUNK / 3.7
    reply = 700
    total = sys_toks + body_toks + reply
    if total > ctx:
        return [("chunk overflows context", ...)]
    return []
```

`context_budget.py` — the module the CLAUDE.md-adjacent header block explicitly says exists to
"own" this arithmetic — defines `CHARS_PER_TOKEN = 3.0` (content, deliberately pessimistic,
documented as unmeasured) and `PROSE_CHARS_PER_TOKEN = 4.0` (scaffolding, measured against the
live daemon 2026-08-24), plus `JOB_OVERHEAD_CHARS = 2000` and `METADATA_INFLATION = 1.20`
corrections layered on top (context_budget.py:214-257). `health.py`'s preflight check imports
neither `context_budget` nor its constants. It instead hardcodes `/ 4` for system-prompt tokens
(coincidentally close to `PROSE_CHARS_PER_TOKEN=4.0`, but not sourced from it — an edit to that
constant will not propagate here) and, more consequentially, `/ 3.7` for body/content tokens —
**more permissive** than `CHARS_PER_TOKEN = 3.0`, i.e. it estimates *fewer* tokens per character
of content than the module that owns this number, in the direction that makes overflow LESS
likely to be flagged. It also omits `JOB_OVERHEAD_CHARS` (up to 2,000 chars measured, real
per-job template overhead) and `METADATA_INFLATION` (a further ~20% the real `feats_block_budget()`
budgets for) entirely. Net effect: this preflight check — whose entire job is to catch exactly
the class of bug `context_budget.py`'s header describes (a 41,469-char prompt silently truncated
into a 6144 window) — can report "ok" for a job that the real, measured budget arithmetic in
`content_budget_chars()`/`feats_block_budget()` would refuse. It uses `R.CHUNK` (from `read.py`)
rather than the feats-block-specific sizing at all, so it is checking a related but different
number from what actually ships in a feats call. This is a second, silently-drifting,
more-permissive source of truth for the exact quantity the project already fixed a real incident
over — the shadow the known-suspect note predicted.

### Clean — LEDGER counts write path (lines 85-123)

Fully atomic (`.tmp` + `silence.replace_retry`), with an explicit `.corrupt`-preserving self-heal
on an unreadable prior ledger, and `LEDGER.clear()` gated on the replace actually landing.
Confirmed correct and does not share the SAMPLES-path defect above.

---

## context_budget.py

No correctness bugs, swallowed failures, or caps found. This module is the "budget owner" the
known-suspect note in `health.py` refers to, and reading it end to end confirms its own
arithmetic is internally consistent: `CHARS_PER_TOKEN`/`PROSE_CHARS_PER_TOKEN` are clearly
labelled with their measurement provenance, `content_budget_chars()` can legitimately return
zero/negative and callers are told not to clamp it, and `assert_fits()` raises rather than
truncates. Exception handling around reading the prompt files (`feats_block_budget`, `report`)
degrades to an empty string on failure rather than crashing the caller, which is reasonable for
optional-file defaults and is not a "swallowed correctness failure" in the sense the lens
targets — an empty prompt file would still show up as an obviously wrong (too-generous) budget
number rather than a plausible fake result. No findings against this file itself; its problem is
that `health.py` doesn't use it (reported above under health.py).

---

## burgs.py

### MINOR — burgs.py:227 non-atomic write of BURGS_SAMPLE.json — VERIFIED, matches known suspect

```python
if args.write:
    p = os.path.join(HERE, "data", "BURGS_SAMPLE.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(per_world, f, indent=2, ensure_ascii=False)
```

Plain truncate-then-fill against a `data/` file, not `silence.write_json`. Lower severity than
the `health.py`/`ledger.py` cases because this is a `--write`-gated, manually-invoked report path
(`burgs.py`'s own `main()`), not a file written every cycle by a standing job — but it is still
the exact two-writer-contract violation pattern the sweep exists to catch, on a file under
`data/` that other tools could plausibly read.

### MINOR — burgs.py:230 message contradicts the code — VERIFIED, matches known suspect

```python
print(f"\nwrote {p} (sample of 50 worlds; the rest regenerate on demand)")
```

`per_world` is built at line 196-201 by iterating `for w in worlds:` over the FULL result of
`WS.build_all()` (line 190, itself commented `# every world; Hard Rule 0`), with no slicing
before the dict is assembled. The `json.dump` call two lines above the print (line 228) is also
commented `# every world; Hard Rule 0`. The printed message — "sample of 50 worlds; the rest
regenerate on demand" — is simply false for the current code: the file written contains every
world, not a 50-world sample. This is a stale docstring/message left over from an earlier version
of the module (or copy-pasted from a different report), and is exactly the "comment contradicts
code" class this audit's lens prioritizes. Low severity because the code path itself is correct
(Hard Rule 0 is honored) and the discrepancy is cosmetic to anyone reading the actual JSON, but
it actively misinforms anyone who reads only the console output/log and assumes the file was
capped.

### Clean — settlement math (`burg_count`, `largest_city`, `classify`, `burgs_for`)

Traced the rank-size arithmetic (`P_k = P_1 / k^q`), the floor-driven `burg_count`, and the
`classify()` boundary logic; no off-by-one or inverted-condition found. Noted but not flagging:
`burgs_for(..., limit=None)`'s `range(1, (limit or n) + 1)` would silently ignore an explicit
`limit=0` (falls back to `n`) — but `limit` is never passed as anything but `None` by the only
caller in this file (`main()` uses `args.limit` solely to slice the already-built list for
display, not as an argument to `burgs_for`), so this has no live effect; recorded for
completeness, not raised as a finding.

---

## descending_ladder.py

No correctness bugs, swallowed failures, caps, concurrency issues, or comment/code
contradictions found. This module is pure physics/math (constants, `rung_for_length`,
`compton_confinement_energy`, `density_at_scale`, `schwarzschild_radius`, `shrink_report`,
`transgression_bits`) with no file I/O, no subprocess calls, and no shared state. Manually
traced `rung_for_length()`'s "keep overwriting `best` while `metres <= r[3]`" loop against the
monotonically-decreasing `DESCENDING` length column and confirmed it correctly resolves to the
smallest-length rung whose threshold still covers the input, including boundary cases at each
`r[3]` and the Planck-length/Fold cutoff. The module's own docstring explicitly documents and
explains a prior bug (`transgression_bits`, corrected 2026-08-20, priced against the wrong
physical law) — current code matches the corrected description. Clean module.

---

## ledger.py

### MAJOR — ledger.py:116-133 `assay_to_standards()` at the top band ignores `ruin_score` entirely — VERIFIED NUMERICALLY

```python
def assay_to_standards(magnitude_band, ruin_score=5.0):
    from assay import BAND_EDGES, LADDER
    if magnitude_band not in BAND_EDGES:
        return None
    i = LADDER.index(magnitude_band)
    lo = BAND_EDGES[magnitude_band]["ruin"]
    hi = BAND_EDGES[LADDER[min(i + 1, len(LADDER) - 1)]]["ruin"]
    joules = math.exp(math.log(lo) + (ruin_score / 10.0) * (math.log(hi) - math.log(lo)))
    return {"joules": joules, "standards": work_value(joules), ...}
```

`LADDER = ["M0", ..., "M10"]` (assay.py:105). At `magnitude_band = "M10"` (the last rung),
`i = LADDER.index("M10") = 10 = len(LADDER) - 1`, so `min(i + 1, len(LADDER) - 1)` clamps back to
`10` — `hi` is computed from `LADDER[10]`, i.e. the SAME band as `lo`. `hi == lo` exactly, so
`math.log(hi) - math.log(lo) == 0` and the `ruin_score` term is multiplied by zero regardless of
its value. `joules` collapses to `math.exp(math.log(lo)) == lo`, the band's floor value, for
every possible `ruin_score` from 0 through 10.

Confirmed by direct execution against the live module (miniconda python,
`ledger.assay_to_standards('M10', ruin_score=X)` for X in {0, 5, 10}):

```
M10 ruin=0  -> joules=9.999999999999922e+98, standards=4.672897196261646e+90
M10 ruin=5  -> joules=9.999999999999922e+98, standards=4.672897196261646e+90
M10 ruin=10 -> joules=9.999999999999922e+98, standards=4.672897196261646e+90
```

All three identical. For contrast, `M5` (a mid-ladder band) correctly varies:

```
M5 ruin=0 -> joules=6.900000000000044e+41, standards=3.224299065420581e+33
M5 ruin=5 -> joules=2.626785107312724e+46, standards=1.227469676314357e+38
```

Effect: any entity assayed at the library's own top magnitude band (M10 — the band the Assay
scale exists to describe the most extreme entities with) gets a Standards price that is
completely insensitive to its actual `ruin_score` within that band — a 0/10 and a 10/10 M10
entity price identically, silently understating the top of the scale by the entire width of the
band (in this run, `hi` for M10 would need `LADDER[11]` which doesn't exist — there is no data
to define what "M10 at ruin_score=10" should cost, which is the root cause, not just a clamp
artifact). No exception, no warning; the function returns a normal-looking dict every time.
Severity MAJOR: this is a silent, permanent loss of the score parameter's effect at exactly the
top of the scale, in a module whose entire purpose is turning Assay scores into a meaningful
price.

### Clean — everything else in ledger.py

`to_standards`/`from_standards`/`cross_rate` correctly return `None` for unconvertible/unlisted
currencies (the `poneglyph-grade favour` sentinel is handled as intended, `rate is None` guards
present in all three). `work_value` is a straightforward division, imports `JOULES_PER_STANDARD`
from `physics.MATERIAL` rather than restating it (matches the module's own stated anti-drift
design). No file I/O, no subprocess calls, no caps. The M10 finding above is the only defect.

---

## Summary of severities

- MAJOR: overnight.py coverage_snapshot() returncode; overnight.py preflight() returncode;
  overnight.py read.py keeper-exclusion/stall gap; health.py SAMPLES self-heal gap; health.py
  shadow chars-per-token constants; ledger.py M10 ruin_score collapse.
- MINOR: overnight.py STATUS.md non-atomic write; weave.py max_sources=60 evidence filter (design
  tension with Hard Rule 0, not a truncation of the entity/roster data itself); burgs.py
  non-atomic write; burgs.py stale "sample of 50" message.
- Clean: context_budget.py, descending_ladder.py, and the previously-fixed portions of weave.py
  (shared[p] caps) and health.py (LEDGER counts write path).
