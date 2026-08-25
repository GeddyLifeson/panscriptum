# AUDIT — batch 09 (run29)

Modules: `src/hostcheck.py`, `src/gpu_lane.py`, `src/tiers.py`, `src/weave_index.py`,
`src/autostart.py`, `src/catalogue_aurora.py`

Every line of all six was read. Two bugs were reproduced with driver scripts (kept in the
scratchpad, not the repo). Findings below are grouped by module, then by lens category.
Categories with nothing found are stated explicitly rather than omitted.

---

## src/hostcheck.py

### 1. Correctness bugs

**FINDING H1 — `sweep(repair=True)` selects the replacement host by raw hit RATE, not by
LIFT, reproducing the exact bug pattern `adopt()`'s own docstring says was found and fixed.**
`src/hostcheck.py:539` (inside the `repair` branch, ~527-548):

```python
best = (0.0, None)
...
if ok and p["rate"] is not None and p["rate"] > best[0]:
    best = (p["rate"], h)
...
if best[0] >= GOOD:
    break
```

`score()` itself argues at length (lines 426-451) that raw hit rate is meaningless without
subtracting a host's own baseline generosity — that's the whole point of `lift`. `adopt()`'s
`one()` function (line 871-874) explicitly fixed this same defect: *"the first slot is LIFT and
only lift — an earlier version stored the RATE there and then compared other candidates' lift
against it, so ... a worse-lift host could win."* The `sweep()` repair loop never received that
fix — it still ranks by `p["rate"]`. Among candidates that already cleared the lift-based
verdict bar (`ok = verdict in ("holds","partial")`), it can and will prefer a generous
low-lift "partial" host (e.g. an encyclopedia with high raw hit rate but only 20-point lift)
over a genuine "holds" match with a lower raw rate but much higher lift. This directly repoints
`WIKI_HOSTS.json` — read by feats, read, completeness, ingest_doc, wiki_source — to a worse
host.

Consequence: `--repair` runs can silently swap a source onto a weaker-evidence host than the
one `--adopt` would have chosen for the same candidate set, because the two functions disagree
on what "best" means despite sharing the exact same `score()` output.

**Status: REPRODUCED (isolated logic).** Live end-to-end reproduction needs real wiki network
calls; instead the exact comparison lines were extracted verbatim and run against two synthetic
`score()`-shaped records (Host A: rate 0.90, lift 0.20, verdict "partial"; Host B: rate 0.45,
lift 0.40, verdict "holds"). Raw-rate selection picked Host A; lift-based selection (the logic
`adopt()` uses) picked Host B. Script: `repro_repair_rate.py` in the session scratchpad.
Output:
```
sweep()-repair selection (ranks by RAW RATE): (0.9, 'generic-encyclopedia.example')
adopt()-style selection (ranks by LIFT):         (0.4, 0.45, 'specific-wiki.fandom.com', 'holds')
Disagreement -- sweep() repointed the source to a worse-matching host: True
```

### 2. Swallowed failures

No bare `except: pass` found. Every `except` either calls `silence.note(...)` (the project's
audited escape hatch) or returns an explicit, honestly-labeled sentinel (e.g. `probe()`'s
network-failure path returns `rate: None` rather than `rate: 0`, which the code's own comment
correctly identifies as the fix for a real historical bug — verified present and correct).

### 3. Hard Rule 0 caps

`PROBE = 40` (line 83), `relevance(..., sample=12)` (line 187), `_bodies()`'s `list(titles)[:8]`
(line 246) and `body[:8000]` (lines 246, 258), and `null_rate()`'s `foreign[...][:sample]`
(line 417) are all **truncations of a statistical fitness measurement**, not of catalogued
data — they bound how many names/articles a host-fitness *probe* samples, and the resulting
`rate`/`lift`/`about` numbers are what get written to `HOST_FITNESS.json`, never the sampled
names/text themselves. This is different in kind from truncating an entity roster or a page
list: the "universe" being measured is a statistical estimate by design (the docstrings for
`PROBE`, `MIN_PROBE`, and `null_rate` all reason explicitly about sample-size trade-offs). Flagged
for the record per the lens's instruction to hunt every `[:N]`/`sample`, but **not** treated as
a Hard Rule 0 violation — no catalogue entry list, page list, or roster is shortened here.
VERIFIED-BY-READING; not a HARD RULE 0 finding.

No caps found on `entities_by_source()` (full CHARACTER_SWEEP.json, no slicing), `candidates()`
(explicitly fixed in this file to return the whole `grounded + spec` list — see the file's own
"EVIDENCE FIRST, SPECULATION AFTER" comment at line 358), or `roster_audit()`/`purge()`'s
iteration over `by[src]` / `glob.glob(...)` (both unbounded).

### 4. Checks that cannot fail

None found. Verdict logic in `score()` branches on live-computed `lift`/`about`/`hits`, not on
tautologies or hardcoded expected counts.

### 5. Two-writer contract

**FINDING H2 — `purge()` writes catalogue record files directly, bypassing
`pipeline.write_record_catalogue`.** `src/hostcheck.py:698-707`:

```python
if not dry:
    r["entries"] = []
    r["purged_roster"] = {"mined_from": mined, "reason": "wrong fiction", "removed": n_entries}
    _land(fp, r, sort_keys=False, ensure_ascii=False)
```

This writes directly into a `data/records/*.json` catalogue record — the exact class of file
the two-writer contract reserves for `pipeline.write_record`/`write_record_catalogue`. The
code is explicit and reasoned about why: `write_record_catalogue` "merges and never shrinks an
entry list, which is exactly right for a cast-growing pass and exactly wrong for a purge whose
whole purpose is to empty one." The write is at least atomic (`_land()` → `silence.replace_retry`),
so this is not a concurrency hazard — it is a **deliberate, documented exception** to the
two-writer rule rather than an oversight. Flagging per the lens's instruction ("any other writer
is a violation") for the supervisor to confirm this exception is accepted policy rather than a
gap that should route through a dedicated purge-writer function instead.
VERIFIED-BY-READING.

All other writes in this file (`OUT`, `UNFIT`, `F.HOSTS`, `ROSTERS`, `PURGED`) are shared-state
JSON artifacts correctly routed through `_land()`/`silence.replace_retry`, matching the
contract's other half.

### 6. Concurrency races

**FINDING H3 — `null_rate()`'s memoization cache is keyed on `host` only, ignoring the
`by`/`exclude` arguments that also determine its return value.** `src/hostcheck.py:390-423`:

```python
_NULL_CACHE = {}
...
def null_rate(host, by=None, exclude=None, sample=40):
    with _NULL_LOCK:
        if host in _NULL_CACHE:
            return _NULL_CACHE[host]
    foreign = []
    for src, names in (by or {}).items():
        if src == exclude:
            continue
        ...
```

`score()` calls `null_rate(host, by=by, exclude=source)` (line 460) once per `(host, source)`
pair — and the same host (especially universal candidates like `en.wikipedia.org` or
`www.dandwiki.com`) is scored against dozens of different sources in one `sweep`/`repair`/`adopt`
run, each with a *different* `exclude`. Because the cache key is only `host`, the first source
to score a given host locks in that source's baseline for every other source that scores the
same host for the rest of the process's life — the `exclude` parameter of every later call is
silently ignored. This defeats the stated purpose of `exclude` (keeping a source's own real
names out of its own control sample) for every caller but the first.

**Status: REPRODUCED live**, script `repro_nullrate.py`:
```
call 1 (exclude SourceA): probe() called 1 times; sample= [...Beta/Gamma names...] -> rate 0.12
call 2 (exclude SourceB): probe() called 1 times total; new call made: False -> rate 0.12
BUG CHECK: exclude changed (SourceA -> SourceB) but result unchanged and no new probe() call issued: True
```
`probe()` was monkeypatched so the sample composition would be visible; the second call, with a
different `exclude`, made no new network call at all and returned the first call's cached value
verbatim.

Practical severity: bounded but non-zero. `foreign` pools from every source in `by` (often
hundreds), so excluding one source's ~3-15 names before the final 40-item subsample usually
shifts the result only slightly — but "usually only slightly" is exactly the kind of drift this
project's own `weave_index.py` docstring (m17) warns is invisible until it silently misreads
something. The lock (`_NULL_LOCK`) does correctly protect the dict itself from corruption; this
is a semantic staleness bug, not a data race in the traditional sense.

No other concurrency issues found in this file: `sweep`/`roster_audit`/`adopt` all use
`ThreadPoolExecutor.map`, which serializes results back to the main thread; no shared
mutable state is written from worker threads except through `_NULL_CACHE` (covered above) and
`_land()` (which is only called from the main thread after `ex.map` returns).

### 7. Comments/docstrings that contradict code

None found in this file — the docstrings are unusually rigorous and each historical-bug claim
checked out against the current code (verified: `probe()`'s error path returns `rate: None`
not `0`; `candidates()` returns the full `grounded + spec` list, not an interleaved/truncated
one; `purge()`'s docstring correctly says the "host was independently rejected" safety check
"never did" exist and names the real safeguard as `--source`+human review, matching the code).

---

## src/gpu_lane.py

### 1. Correctness bugs

**FINDING G1 — `foreground()`'s refcounted claim file has an unguarded read-modify-write race
between threads of the same process, letting a shorter-lived foreground call delete the claim
out from under a longer-lived one still in progress.** `src/gpu_lane.py:219-239`:

```python
@contextlib.contextmanager
def foreground(label="foreground"):
    path = _claim_path()                       # same path for every thread of this process
    rec = _read(path) or {}
    depth = int(rec.get("depth") or 0) + 1
    _write_claim(path, depth, label)
    try:
        yield
    finally:
        cur = _read(path) or {}
        d = int(cur.get("depth") or 1) - 1
        if d <= 0:
            _remove_retry(path)
        else:
            _write_claim(path, d, label)
```

The docstring frames the refcount as protection against *sequential nesting* within one call
stack ("a foreground call may nest inside another... the inner call's exit cleared the outer
call's flag"). It does not account for two *concurrent* threads of the same process each
calling `foreground()` — both read the same `path`, both compute their own `depth` from a
stale read, and both write, without any lock serializing the read-modify-write. If thread B's
whole `with foreground():` block starts and finishes while thread A is still between its own
read and write, B's exit can decrement the depth to zero and delete the claim file entirely —
while A is still inside its block believing itself to be the (or an) active foreground holder.
From that point on, `foreground_active()` reports no live foreground claim, and rule 2 of this
module's own header — "background work yields to any live foreground claim" — silently stops
applying for the remainder of A's still-running call.

Whether this is reachable in production depends on whether any caller invokes `lane(priority=True)`
/ `foreground()` from more than one thread of the same process concurrently; `generate.py` is
named in this file's own docstring as the sole `priority=True` caller and its threading model
is outside this batch, so real-world reachability is a **HYPOTHESIS** pending that check — but
the race itself, and its consequence (an active foreground claim silently vanishing), is
**REPRODUCED**, script `repro_fg_race.py`:
```
claim file right after B exits, while A is still inside its with-block: None
('B', 'claim visible while still inside:', True)
('A', 'claim visible while still inside:', False)
BUG: claim file was gone/absent while a foreground() call was still active: True
```
(Test used an isolated `LANE` directory, not the real project state, and monkeypatched
`_write_claim` only to insert a delay to force the interleave — the read-modify-write logic
itself is untouched, real code.)

### 2. Swallowed failures

None beyond the deliberate, well-reasoned fail-open pattern the module's header describes
(every failure path in `lane()`, `_take_slot`, `_touch`, `_remove_retry` proceeds rather than
blocks, and every one of them is commented with why). This is the module's stated design goal,
not an unintentional swallow.

### 3. Hard Rule 0 caps

None — this module manages lease files, not catalogue data. Not applicable.

### 4. Checks that cannot fail

None found.

### 5. Two-writer contract

Not applicable — this module writes only its own lease/claim state files (`slot.N.json`,
`fg.PID.json`), which are the shared-state class of artifact, and every write goes through
`silence.replace_retry` (`_write_claim`, `_touch`) or the atomic `O_CREAT|O_EXCL` primitive
(`_take_slot`). No catalogue records are touched here.

### 6. Concurrency races

Covered under Correctness (G1) above, since the race's *consequence* is the interesting bug.
Beyond G1: `_take_slot()` correctly uses `O_CREAT|O_EXCL`, the right cross-process primitive
(verified — this is the one piece of code in the module actually contended across *processes*,
and it does not use `threading.Lock`, correctly). `_touch()`'s "never resurrects" guard was
read carefully and is correct: it checks the record exists and belongs to `os.getpid()` before
writing, which is exactly what prevents the heartbeat thread from recreating a lease file after
`_remove_retry` has legitimately deleted it (the "ORDER MATTERS" comment at the end of `lane()`
is accurate, and the guard makes it belt-and-braces rather than load-bearing on ordering alone).

### 7. Comments/docstrings that contradict code

None found — this module's docstrings are detailed and each checked out (the Windows
`_alive()` errno story, the `_touch`-never-called history for m54, the `MAX_SLOTS` /
`OLLAMA_NUM_PARALLEL` unification). One nuance: the `foreground()` docstring's account of
re-entrancy ("Re-entrant by refcount...") describes only the sequential-nesting case it was
built to fix, and does not mention (nor guard against) the concurrent-thread case found as G1 —
not a contradiction, but an incompleteness worth noting alongside the finding.

---

## src/tiers.py

### 1. Correctness bugs

None found. The multiverse/metaverse/xenoverse threshold nesting was checked for the failure
mode the file's own comments describe (a tier not containing its members) — `_components()`
uses simple connectivity/reachability with a fixed edge-weight dict `w`, so a looser threshold's
adjacency graph is guaranteed to be a superset of a tighter threshold's; this makes
`metaverse != None ⟹ xenoverse != None` for every source by construction, which is exactly what
the file's own runtime "containment violations" check (see Checks-that-cannot-fail below) is
built to verify. No inconsistency found between the two clustering methods used (single-linkage
`_components()` for the CUTS tiers vs. complete-linkage `W.components()` for the multiverse,
gated tighter by the `MULTIVERSE_THRESHOLD >= CUTS[0][1]` assert).

### 2. Swallowed failures

The `GROUNDINGS.json` load failure at line 246 correctly falls back to `{}` via `silence.note`,
which only degrades `own_grounding`/hyperverse assignment to "ungrounded" rather than crashing
the whole tier computation — a reasonable fail-soft, not a silent miscount.

### 3. Hard Rule 0 caps

`deliberate_joins()` (lines 271-287) was specifically checked because its own docstring
describes a `[:3]` cap that was removed project-wide in a prior run (m144/run #27, cited in the
comment) — **confirmed removed**: the current code returns the full `shared.get((a,b), [])`
list with no slicing. `for s in unaddressed[:6]:` in `main()` (line 311) is console-preview
output only (the 6-item sample is never written to `TIERS.json` — only `charted` is, via
`silence.write_json` with no slicing anywhere in it). DISPLAY truncation, correctly so.

### 4. Checks that cannot fail

**FINDING T1 — the containment self-check in `main()` is diagnostic-only: a violation is
printed but never blocks the write or signals failure to anything upstream.**
`src/tiers.py:320-332`:

```python
ok = all(counts[i] >= counts[i + 1] for i in range(len(counts) - 1))
print(f"   monotone: {ok}")
bad = 0
for s in srcs:
    ...
print(f"   containment violations (a lower group split across two higher ones): {bad}")
```

Neither `ok` nor `bad` is asserted, raised, or fed into the process's exit code — `main()`
proceeds unconditionally to `silence.write_json(out, charted, ...)` regardless of what either
check found. Given the file's own extended discussion of how seriously it takes this exact
invariant ("A tier that does not contain its own members is not a tier... A first attempt put
the metaverse at 150 while the multiverse sat at 102.3 ... and five of them were" split), a
regression that reintroduces that failure would print `monotone: False` and a nonzero violation
count to a console log and then write `TIERS.json` anyway, indistinguishable at a glance from a
clean run to anything not reading stdout closely. This is not a tautological check (it computes
over live data, not constants), but it is functionally inert — nothing acts on its result.
VERIFIED-BY-READING.

The two `assert` statements at lines 119-120 (`cuts must loosen downward`,
`multiverse must be tighter than metaverse`) are over hardcoded constants only — they are
legitimate import-time sanity guards on configuration, not runtime checks masquerading as
validation of computed data, so they are not flagged as "cannot fail" in the problematic sense.

### 5. Two-writer contract

Not applicable — only shared-state artifact `TIERS.json`, written via `silence.write_json`
(confirmed atomic per its own comment referencing the m6 fix). No catalogue records touched.

### 6. Concurrency races

None — single-threaded, no shared mutable state across processes.

### 7. Comments/docstrings that contradict code

None found. The long prose justification for why the hyperverse is declined rather than
charted matches the code exactly: `hyperverse` is filled solely from `xenoverse_grounding()`
(no separate pantheon-seeded path remains — confirmed, the removed code is only referenced in a
comment, not present).

---

## src/weave_index.py

### 1. Correctness bugs

None found. `norm()`/`continuity_of()`/`designations()` were traced end to end; the
corpus-derived designation-learning logic (frequency ≥ `DESIGNATION_MIN_NAMES`, plus `_SEED`,
plus `_EARTH` regex) is internally consistent with `norm()`'s use of it.

### 2. Swallowed failures

`load_records()` and `designations()` both catch broad exceptions around file I/O and call
`silence.note(...)` before falling back to an empty/cached result — consistent with the
project's audited discipline, not a bare swallow.

### 3. Hard Rule 0 caps

**FINDING W1 — entity `description` is truncated to 400 characters before being written into
`ENTITY_INDEX.json` and `WEAVE_CANDIDATES.json`.** `src/weave_index.py:224`:

```python
index[key].append({
    ...
    "description": (e.get("description") or "")[:400],
})
```

This dict is exactly what `build()` returns and what `main()` writes verbatim (unsliced, full
dict) to `OUT_INDEX`/`OUT_CAND` under `--write` (lines 268-270) — so the 400-character cap is a
**DATA truncation**, not a display one: every reader of `data/ENTITY_INDEX.json` and
`data/WEAVE_CANDIDATES.json` sees only the first 400 characters of each entity's description,
permanently, in the written artifact. The module's own docstring frames description text as
load-bearing for the *next* stage: "Only the model, reading both descriptions, may adjudicate
that [whether two candidates are the same entity]" — identity adjudication (e.g. is Thor-in-
Marvel the same Office-seatholder as Thor-in-Norse-myth) is exactly the kind of judgment a
truncated first-400-characters excerpt can get wrong for a long entry whose distinguishing
detail sits later in the text.

Whether the downstream adjudicator (not in this batch — presumably `weave.py` or an identity
pass) re-reads the full record from `data/records/*.json` rather than trusting this 400-char
excerpt is unknown from this file alone; if it does, this cap is harmless (the index is then
only a lightweight pointer). If it does not, this is a Hard Rule 0 violation on data that feeds
a real identity ruling. **Flagging for the supervisor to trace the consumer(s) of
`WEAVE_CANDIDATES.json`.** VERIFIED-BY-READING (the slice and its write path are unambiguous);
the downstream-impact question is a HYPOTHESIS.

No other caps found: `build()`'s iteration over every record/entry is unbounded; the `[:18]`
"most cross-attested entities" list (line 259) and the `[:10]` "attested in N sources" spread
table (line 255) are both purely console-preview printouts (`main()`'s report section), never
written to `OUT_INDEX`/`OUT_CAND` — correctly DISPLAY truncation, not flagged.

### 4. Checks that cannot fail

None found.

### 5. Two-writer contract

Not applicable — only shared-state artifacts (`ENTITY_INDEX.json`, `WEAVE_CANDIDATES.json`),
both via `silence.write_json`. No catalogue records written by this file.

### 6. Concurrency races

`_REC_CACHE` and `_DESIGNATIONS` are process-global dicts/tuples updated without a lock
(unlike hostcheck's `_NULL_CACHE`, which at least has `_NULL_LOCK`). This module itself never
spawns threads, so a race requires some *other* caller to invoke `load_records()`/
`designations()` from multiple threads of one process concurrently. If that happens, the
check-then-recompute-then-store sequence in both functions is not atomic across the whole
function (only individual dict operations are, via the GIL), so two threads could both
cache-miss and both redo the (potentially expensive, 63MB) reload simultaneously — wasted work,
not data corruption, since both would compute the same answer for the same on-disk state.
Low-severity; noted as HYPOTHESIS since no concurrent caller was found in this batch.

### 7. Comments/docstrings that contradict code

None — the m17 stale-cache history cited in `designations()`'s docstring matches the
`_records_sig()`-keyed invalidation actually present in both `load_records()` and
`designations()`.

---

## src/autostart.py

### 1. Correctness bugs

None found. The VBScript quote-escaping in `_vbs_body()` was traced character-by-character
(the `Chr(34) & "..." & Chr(34) & ...` concatenation) and correctly produces
`"<python.exe>" -u "<autostart.py>" --watch` as a properly double-quoted VBScript `Run` command
— this is the kind of string-building code that looks exactly like the sort of thing that
silently breaks, so it was checked in full rather than skimmed, and it is correct.

### 2. Swallowed failures

All broad `except Exception` blocks (`supervisor_alive`, `_twin_watchdog`, the `watch()` loop,
the `main()` status block) call `silence.note(...)` and fail toward a safe default (treat as
not-running / not-a-twin / log-and-continue) rather than crashing the watchdog — consistent
with this file's own stated purpose (the watchdog must never itself become the single point of
failure it exists to catch).

### 3. Hard Rule 0 caps

None — this module manages process lifecycle, not catalogue data. Not applicable.

### 4. Checks that cannot fail

None found.

### 5. Two-writer contract

Not applicable — no catalogue records or shared JSON state written; only plain append-mode log
files (`autostart.log`, `overnight_stdout.log`, `overnight_stderr.log`), which are not
read-modify-write shared state and don't need atomic replace.

### 6. Concurrency races

`_twin_watchdog()` is a one-shot check at the top of `watch()`, not a continuously-held lock —
if two `--watch` processes started within the same PowerShell-CIM-query window, both could see
no twin and both proceed. The file's own docstring describes this exact failure mode having
happened before ("Three of these once ran at once") and the fix installed is this best-effort
startup check, not a true mutex. Given the Startup folder only invokes one `--watch` process
per login by design, the realistic trigger for a second `--watch` process is a manual restart
racing the Startup-launched one, which is a narrow window. Noted as a **HYPOTHESIS**, not
elevated — the existing single-check mitigation matches what the docstring claims it does, it
just is not airtight against a simultaneous manual start.

Minor: `start_supervisor()` (lines 103-118) opens `out`/`err` log file handles and passes them
to `Popen` without an explicit `close()` in the parent process afterward. On CPython these are
typically closed promptly by refcounting when the local variables go out of scope, so this is
unlikely to be a real leak in practice, but it is not explicit. LOW severity, VERIFIED-BY-READING.

### 7. Comments/docstrings that contradict code

None found.

---

## src/catalogue_aurora.py

### 1. Correctness bugs

None found. `parse_folder()`'s per-folder `seen` dedup key is `(type.lower(), normalized-name)`,
correctly scoped to reset per folder (no cross-folder or cross-source contamination, and no
`FOLDER_SOURCE` folder maps to more than one source name).

### 2. Swallowed failures

`ET.parse(path)` failures at line 74-76 are caught, logged via `silence.note`, and the file is
skipped rather than aborting the whole source's catalogue pass — documented as deliberate
("a malformed homebrew file should not abort the whole source"), consistent with the project's
discipline.

### 3. Hard Rule 0 caps

None found. `root.iter("element")` walks every descendant element with no cap; `text_of()`
uses `"".join(d.itertext())` to capture the full description text (all descendant text nodes,
not just the first), so no content is silently dropped. The only slicing present,
`slug(s)[:60]` (line 59), bounds a generated *filename*, not catalogued content — a reasonable
filesystem constraint, not a Hard Rule 0 violation.

### 4. Checks that cannot fail

None found.

### 5. Two-writer contract

Correct: catalogue records are written exclusively via `pipeline.write_record_catalogue`
(line 150), and — importantly — the write's return value **is** checked (`if not
_P.write_record_catalogue(...): ... continue`), which the code's own comment identifies as a
fix for a real historical bug (run #25, where a denied write left a stale record on disk beside
a roll confidently claiming N entries). Confirmed present and correct: on a denied write, the
roll row is explicitly left untouched (`continue` skips the `r["entry_count"] = ...` /
`r["status"] = "catalogued"` lines). The roll file itself (`SWEEP_ROLL.json`) is written via
`silence.write_json`, the correct shared-state path.

### 6. Concurrency races

None — single-threaded, sequential per-folder processing, no shared mutable state beyond the
roll dict which is written once at the end from the same (only) thread.

### 7. Comments/docstrings that contradict code

None found. The module docstring's claim about codex vs. XML richness (1,159 vs. 123 elements)
is a factual claim about external data, not verifiable from the code alone, and not contradicted
by anything in it.

---

## Summary of findings by severity

| # | Severity | Module:line | Finding | Status |
|---|----------|-------------|---------|--------|
| H1 | HIGH | hostcheck.py:539 | `sweep(repair=True)` ranks replacement hosts by raw rate, not lift — reintroduces the exact bug `adopt()` fixed | REPRODUCED (isolated logic) |
| G1 | HIGH | gpu_lane.py:219-239 | `foreground()` claim refcount races across threads of one process; a shorter call's exit can delete a longer call's still-active claim | REPRODUCED |
| H3 | MEDIUM | hostcheck.py:390-423 | `null_rate()` cache keyed on `host` only, ignoring `by`/`exclude` — later callers silently get an earlier caller's stale baseline | REPRODUCED |
| W1 | MEDIUM | weave_index.py:224 | entity `description` truncated to 400 chars in written ENTITY_INDEX.json/WEAVE_CANDIDATES.json, feeding identity adjudication | VERIFIED-BY-READING (downstream impact HYPOTHESIS) |
| H2 | MEDIUM | hostcheck.py:698-707 | `purge()` writes catalogue records directly, not via `pipeline.write_record_catalogue` (deliberate, documented, atomic) | VERIFIED-BY-READING |
| T1 | LOW-MEDIUM | tiers.py:320-332 | containment/monotonicity self-check is diagnostic-only; a violation prints but never blocks the write | VERIFIED-BY-READING |
| — | LOW | autostart.py:111-118 | log file handles not explicitly closed after `Popen` in `start_supervisor()` | VERIFIED-BY-READING |
| — | INFO | hostcheck.py (PROBE/sample constants) | statistical sampling for host-fitness measurement, not catalogue-data truncation — reviewed, not a violation | VERIFIED-BY-READING |

Modules with no findings beyond the above: **tiers.py** (aside from T1), **catalogue_aurora.py**
(clean across all seven lens categories), **autostart.py** (clean aside from the minor log-handle
note).
