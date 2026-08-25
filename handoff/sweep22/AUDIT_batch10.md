# Batch 10 audit — cascade_bridge.py, manifest_builder.py, pick_model.py, sevenfold.py, autostart.py, catalogue_aurora.py

Full line-by-line read of all six files, current on-disk state as of this sweep. `cascade_bridge.py`
audited post-edit (paid lane erased, `record_unrecognised`/`unrecognised_open` present).

---

## HIGH

### H1 — `sevenfold.py:198-209` — worlds silently dropped, no logging, if a source has no `coords` match

```python
worlds = {}
for src, ws in by_source.items():
    base = coords.get(src)
    if base is None:
        continue
    names = [x["designation"] for x in ws]
    inner = shelve(names, {}, depth=len(WORLD_TIERS))
    for d in names:
        worlds[d] = dict(base)
        worlds[d]["multiverse"] = inner[d]["hyperverse"]
        worlds[d]["universe"] = inner[d]["xenoverse"]
return srcs, coords, w, worlds
```

`by_source` is keyed by `world["designation"].split("::")[0]`, i.e. the source name baked into
each world's designation by `worldseed.build_all()` (`desig = f"{src}::{nm}"`, where
`src = rec["source"]` from `pipeline.records()`). `coords` is keyed by `srcs`, the source list
`tiers._graph()` returns from `weave.idf_table(weave.filtered_index(...))`. If any source's name
doesn't appear in `srcs` — e.g. because `filtered_index` excluded every one of that source's
*other* catalogued entities as "mechanics" while its Places entries (which drive worldseed) survived,
or because of any other normalisation drift between the two pipelines — every world for that source
is silently dropped from the `worlds` dict with **zero counting, logging, or print output**. Nothing
in `main()` compares `len(by_source)` worlds-groups seen against `len(worlds)` groups actually placed.

This is precisely the failure shape Hard Rule 0 exists to forbid: "a cap does not fail, it returns a
smaller universe wearing the same shape as the real one." A dropped source's worlds would never
appear in `SEVENFOLD.json`, and the run would report success.

VERIFIED: the code path and its silence are confirmed by reading. UNVERIFIED: whether `srcs` and
the set of source names appearing in `by_source` are currently identical for the live corpus — I did
not execute `build()` against real data. Given the drop is silent either way, the finding stands
regardless of whether it is firing today.

**Suggested repair:** count `dropped = [src for src in by_source if src not in coords]` before the
loop and print/raise if non-empty — the same "report what's missing, never eat it" pattern already
used by `manifest_builder.py`'s `unassigned_sources.md` and `worldseed.py`'s own fixed "whole
description, not first 200 characters" bug (see its comment at `worldseed.py:272-277`, which fixed
exactly this class of silent-drop for the same module family).

---

### H2 — `cascade_bridge.py:686-691` — bare "401"/"402"/"403" substrings can false-positive on rate-limit text and mis-bench a live provider for 4 hours

```python
err = (box.get("error") or "").lower()
permanent = ("401", "402", "403", "authentication", "invalid_api_key",
             "credentials", "insufficient balance", "no resource package",
             "payment required", "needs billing", "depleted")
if pinned and any(code in err for code in permanent):
    _bury(pinned.bucket, AUTH_BENCH)
```

`box["error"]` is provider-supplied free text (an exception string or a stream's `type:"error"`
payload), truncated to 300 chars, with no other structure. `"401"`, `"402"`, `"403"` are matched as
**unanchored substrings**, not as status codes or word-bounded tokens. Any provider error text that
happens to contain the digits `401`, `402`, or `403` anywhere — inside a request ID, a trace ID, a
millisecond count in a rate-limit message ("retry in 402ms"), a timestamp, a model-version string,
or simply a longer number that contains that 3-digit run (e.g. a trace id like `...8114033221...`
contains `"403"`) — will match and trigger `AUTH_BENCH` (4 hours), even though the actual failure was
a transient 429/timeout that the file's own `dead_forever()` docstring explicitly calls "the most
temporary condition a provider has."

This is the exact class of bug `dead_forever()`'s docstring (lines 290-309) and the file's `GRADED,
NOT FLAT` comment (lines 161-170) both warn against — treating "busy right now" as "gone forever" —
except here it can happen even when the classifier's *intent* (permanent auth/billing failure) is
correctly scoped; the bug is purely in matching bare digits without a boundary.

VERIFIED by code inspection. `verify_math.py`'s own test suite (§20f, around line 3417-3441) tests
that each of these tokens correctly triggers the bench when literally present as recognisable HTTP
status language, but has **no test constructing a plausible rate-limit message and asserting it does
NOT trigger the bench** — the false-positive direction is untested.

**Suggested repair:** require a word/token boundary around the bare numeric codes, e.g. match
`r'\b40[123]\b'` or require the code adjacent to "http"/status-shaped context (`r'\b(?:http[ _-]?)?40[123]\b'`),
rather than plain substring containment. The word-only tokens (`"authentication"`, `"credentials"`,
etc.) don't have this problem and can stay as-is.

---

### H3 — `autostart.py:208-211` — `--status` uses a stale hardcoded job roster, not `overnight.ALL_JOBS`, and is missing `pipeline.py`

```python
try:
    import overnight as ON
    for job in ("dashboard.py", "publish.py", "foreman.py", "overwatch.py",
                "feats.py", "read.py"):
        print(f"  {job:<16}" + ("running" if ON.running(job) else "not running"))
except Exception:
    silence.note("autostart.py:status")
```

`overnight.py` itself documents this exact bug class and states it was fixed by centralising into a
single list (`overnight.py:366-371`):

> "THE STANDING SET — the jobs the keeper re-asserts every five minutes. Module-level, and
> deliberately so: this roster used to live inside main() while THREE other places carried their own
> partial copy of it (allsweep's process check knew four jobs, **autostart's status display knew
> six**, this knew five). A job missing from a roster does not read as "not listed", it reads as NOT
> RUNNING... One list, imported by its readers."

`overnight.py` now exposes `ALL_JOBS` (`overnight.py:387-389`) as that canonical list:
`["autostart.py", "overnight.py"] + [basename of each STANDING job] + ["read.py", "feats.py --roll"]`,
which currently includes `pipeline.py` (part of `STANDING`, `overnight.py:379`). **`autostart.py`'s
`main()` was never updated to import it** — it still carries its own independent, hardcoded 6-item
tuple, which is missing `pipeline.py` entirely (and doesn't self-report `autostart.py`/`overnight.py`).
If `pipeline.py`'s supervised process dies, `python src/autostart.py --status` will not show it as
down — the exact "reads as NOT RUNNING [when actually just not listed]" failure the `overnight.py`
comment describes having already bitten this project once (via `allsweep.py`).

VERIFIED: both files read directly; the mismatch between `autostart.py`'s literal tuple and
`overnight.ALL_JOBS` is exact and current.

**Suggested repair:** replace the hardcoded tuple with `ON.ALL_JOBS` (filtering out
`"feats.py --roll"`'s fragment-matching quirk if desired, or just passing it through — `ON.running()`
does substring matching so it works either way).

---

### H4 — `catalogue_aurora.py:148-150` — bare non-atomic write to the shared, multi-writer `data/SWEEP_ROLL.json`

```python
if not args.dry_run and written:
    with open(ROLL, "w", encoding="utf-8") as f:
        json.dump(roll, f, indent=2, ensure_ascii=False)
```

This is a direct truncate-then-fill write to `data/SWEEP_ROLL.json`, not routed through
`silence.write_json()` or `silence.replace_retry()`. The project's own `silence.write_json()`
docstring (`silence.py:250-266`) documents this precise file and this precise failure mode as
already found and only partially fixed:

> "Found by the 2026-08-25 comprehensive sweep: TWELVE call sites across ten modules were writing
> shared `data/` and `state/` files with a bare `open(path, "w")` + `json.dump`, which is not a write
> but a TRUNCATE-THEN-FILL. A reader arriving in the gap sees an empty or half-written file; a crash
> in the gap leaves it that way permanently. **Four of those sites were writing the SAME file --
> `data/SWEEP_ROLL.json` -- from four different scripts**... `catalogue_web.save_roll()` had the
> atomic version and a comment saying an interrupted write here "kills the next run of either script
> outright"; **its siblings did not.**"

`catalogue_web.py`'s sibling function (`catalogue_web.py:69-77`) was in fact fixed:

```python
def save_roll(roll):
    # Atomic for the same reason the record write beside it is: SWEEP_ROLL.json is written from
    # three worker threads here and read elsewhere by `load_roll` and `resync_roll.py`, BOTH of
    # which do an unguarded `json.load`. A truncating write interrupted mid-dump therefore does
    # not degrade anything gracefully -- it kills the next run of either script outright.
    import silence as _sil
    tmp = ROLL + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(roll, f, indent=2, ensure_ascii=False)
    _sil.replace_retry(tmp, ROLL)
```

`catalogue_aurora.py` is one of the never-fixed siblings: it has no `write_json`/`replace_retry` call
anywhere (confirmed by grep), and its write at line 148-150 is exactly the bare-`open(...,"w")`
pattern the sweep called out. `resync_roll.py`, `recover_folder_records.py`, and `catalogue_codex.py`
also write to the same path with no `write_json`/`replace_retry` call — this is a live, unfinished
cleanup, not fully specific to this file, but `catalogue_aurora.py` is squarely in the audited batch
and squarely one of the unfixed four.

VERIFIED by direct grep and read of both files.

**Suggested repair:** replace the write with `silence.write_json(ROLL, roll, ensure_ascii=False)` (or
the manual tmp+`replace_retry` pattern `catalogue_web.save_roll()` uses).

---

## MEDIUM

### M1 — `cascade_bridge.py:334-373` — `record_unrecognised`'s read-modify-write is only intra-process safe; concurrent OS-process writers can lose an update

```python
with _UNREC_LOCK:
    try:
        with open(UNRECOGNISED, encoding="utf-8") as f:
            rows = json.load(f)
    except Exception:
        rows = {}
    ...
    rows[key] = r
    tmp = UNRECOGNISED + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1, sort_keys=True)
    silence.replace_retry(tmp, UNRECOGNISED)
```

`_UNREC_LOCK` is a `threading.Lock()` — it only serialises threads inside one process. `foreman.py`
(`foreman.py:100`: `subprocess.run([PY] + args, ...)`) spawns multiple separate `python.exe`
processes that can each import `cascade_bridge` and call `record_unrecognised` concurrently. Two
processes can both read the same base `rows` snapshot, each add their own key (or update the same
key's count), and whichever calls `replace_retry` second silently overwrites the first's update —
`replace_retry` makes each individual write land atomically (no torn/unparseable JSON), but it does
not protect the read-modify-write cycle across processes, so a genuine lost update is possible. This
partially undercuts the owner's 2026-08-25 ruling that an unrecognised failure "should be immediately
investigated and resolved upon spotting it" — a lost row is one that was never surfaced at all.

VERIFIED: lock scope and multi-process spawn mechanism confirmed by reading both files. Not
independently reproduced under load.

**Suggested repair:** either accept this as a best-effort ledger (as `_metric`'s append-only sibling
already is, by design, for `model_metrics.jsonl`), or move to an append-only log format for this file
too and aggregate on read in `unrecognised_open()`/`standards.py`, which sidesteps the read-modify-write
entirely the same way `silence.append_line` does for the metrics ledger.

### M2 — `manifest_builder.py:436-437, 455-456, 463-464` — bare `open(path,"w")` on manifest.json / unassigned_sources.md

```python
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"jobs": all_jobs}, f, indent=2)
...
with open(report_path, "w", encoding="utf-8") as f:
    f.write(...)
```

Same non-atomic pattern as H4, applied to `output/index/manifest.json` (or `manifest.pilot.json`) and
`output/index/unassigned_sources.md`. Lower confidence than H4 that this is actively dangerous today:
`manifest_builder.py` is normally a one-shot CLI step run before `generate.py`, not something the
project's own comments document as multi-writer the way `SWEEP_ROLL.json` is. Flagging per the
audit's explicit instruction to catch every bare `open(path,"w")` on a shared/data/output file; the
risk is a torn `manifest.json` if `generate.py`, `catalog.py`, or `dashboard.py` happen to read it
while a rebuild is in flight, or if the process is killed mid-write.

**Suggested repair:** route through `silence.write_json()` for consistency with the rest of the
project's data-writing convention, even though the practical exposure is lower than H4.

---

## LOW

### L1 — `cascade_bridge.py:517` — the pinned-model reserve has no try/except, unlike the widen-path's reserve

```python
pinned = next((m for m in _ROUTER.models if m.id == pin), None)
if pinned is None:
    return None
_ROUTER.reserve(pinned)
```
vs. the widen-fallback path a few lines later:
```python
try:
    _ROUTER.reserve(m)
except Exception:
    silence.note("cascade_bridge.py:widen-reserve")
    continue
```
If `_ROUTER.reserve(pinned)` ever raises, it propagates out of `_ask_call`/`ask()` uncaught. Currently
harmless because the only callers that pass `pin=` (`prove()`, `try_disabled()`) already wrap their
`ask()` call in `try/except`, but it's an inconsistency against the rest of the file's defensive
style, and a future caller passing `pin=` directly (e.g. from `read.py`) would not be protected.

### L2 — `cascade_bridge.py:39` / `autostart.py:42` — self-scan opens the file and never closes it

```python
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")
```
Runs on every import; the file handle is never explicitly closed (CPython's refcounting GC closes it
essentially immediately once the expression is done, so this is not a practical leak, just not
idiomatic — `with open(...) as f: ...` would be cleaner). Identical pattern in both files.

### L3 — `cascade_bridge.py:787-827` (`try_disabled`) doesn't exclude `LOCAL_PREFIX` buckets the way every other selection path in the file does

Every other selection path (`cloud_buckets`, `widen_candidates`, `_alive`, the main claim loop) is
explicit about never letting a claim land on an `ollama:` bucket through Cascade — see `_alive`'s "The
GPU is read.py's own fallback... Never claim it." `try_disabled()` iterates `_ROUTER.models` with no
`LOCAL_PREFIX` check, and if a local model were ever config-disabled for a pool while its provider
carries `local: true`, it would be flipped `enabled=True` and pinned into a real `ask()` call, bypassing
the "never claim it" invariant. Currently latent: local buckets appear to be `enabled` (they show up in
the router's normal claim loop and get explicitly rejected/released there), so `model_status(m).get("available")`
should already be `True` for them, which makes `try_disabled`'s own `if st.get("available"): continue`
skip them today — but this depends on config state this audit did not independently verify, and the
file's own design principle ("never claim it") is not defended at this call site the way it is
everywhere else.

### L4 — `sevenfold.py:147-149` — likely-dead defensive padding

```python
for m in coords:                          # pad shallow branches with slot 0
    while len(coords[m]) < depth:
        coords[m].append(0)
```
Tracing `split()`/`seams()`: `bounds` is built from strictly-increasing, in-range cut indices, so
`chunk = block[lo:hi]` is never actually empty for a member that reached `split()`, and recursion
always continues until `level >= depth`, appending one coordinate per level. Every member therefore
already accumulates exactly `depth` entries through the recursion itself; this loop appears to be an
unreachable safety net (harmless, same style as the file's own acknowledged-dead `"OVER SPAN"` check
at line 245).

### L5 — `catalogue_aurora.py:83-86` — silent, uncounted dedup of `(type, name)` collisions

```python
key = (etype.lower(), re.sub(r"[^a-z0-9]", "", name.lower()))
if key in seen:
    continue
seen.add(key)
```
Drops a later element sharing the same normalised type+name as an earlier one, keeping only the
first (glob order = alphabetical path order), with no count of how many were dropped or which file
"lost." Likely correct for true duplicates across overlapping homebrew files, but two genuinely
different elements that happen to share a name+type (no description comparison is done) would also
silently collapse to one. Judgment call, not a clear Hard Rule 0 violation since it's deduplication
rather than sampling, but worth a print of the drop count for auditability.

### L6 — `pick_model.py` — minor, non-actionable notes

- `budget = (total_vram_gb() or 10.0) - VRAM_RESERVE_GB` (line 295): `total_vram_gb()` returning a
  literal `0` (not `None`) would be treated as falsy and silently replaced by the 10.0 GB fallback.
  Not realistic for `nvidia-smi`'s actual output on a working card; purely theoretical.
- `FAMILY_TIERS` (lines 55-62) has no entry for `llama3.2` — it falls through to the bare `"llama3"`
  tier-3 bucket rather than tier 5 alongside `llama3.1`/`llama3.3`. Data-completeness gap in a table
  the file's own comments already flag as needing periodic updates, not a logic bug.

---

## CLEAN

- **`pick_model.py`** — CLEAN. No correctness bugs, no swallowed-failure issues beyond appropriate
  best-effort fallbacks, no Hard Rule 0 violations (the only slices found are display-only sample
  caps and scoring-formula clamps, not content truncation), `save_config()` correctly uses
  `silence.replace_retry` and checks its boolean return. See L6 for two trivial, non-actionable notes.

- **`autostart.py` — console-window rule specifically CONFIRMED CLEAN.** Both real subprocess spawns
  in this file set `CREATE_NO_WINDOW` (plus `DETACHED_PROCESS` for the detached supervisor at
  `start_supervisor()`, line 114-115; and for the PowerShell probe in `_twin_watchdog()`, line 130),
  and the Startup `.vbs` launcher hides its console via `WScript.Shell.Run(cmd, 0, False)`
  (`_vbs_body()`, line 75) — window style `0` = hidden, which does suppress a console window for a
  console-subsystem `python.exe` child, not just for `pythonw.exe`. No spawn path in this file can pop
  a visible window. (Separately, H3 above is a real bug in this file, just not a console-window one.)

- **`manifest_builder.py`** — no Hard Rule 0 violations found. The `max_entries_per_call` chunking and
  `pack_feats()`'s oversized-entity slicing are both genuine pagination (every chunk/slice is emitted
  as its own job; nothing is dropped), matching the file's own extensive comments on exactly this
  point. `--pilot N` is an explicit, documented, opt-in CLI sampling flag for piloting, not a silent
  default truncation. See M2 for the one real finding (non-atomic output writes).

- **`cascade_bridge.py` — paid-lane erasure (audit point (a)) CONFIRMED CLEAN.** Grepped the full file
  for `paid`/`500`/`spend`/`burst`: every hit is inside a comment explaining the historical retreat;
  no live code references a paid bucket, prefix, cap, or counter. `widen_candidates()` takes only
  `models` (no `paid_ok` parameter survives). `cloud_buckets()` and the main claim loop both operate
  on all non-local buckets uniformly. This matches `verify_math.py`'s own independent test coverage
  (§19h) for the same claim. See H2 and M1 for the two real findings against points (b)/(c) of the
  audit brief.

---

## Summary table

| file | HIGH | MEDIUM | LOW |
|---|---|---|---|
| cascade_bridge.py | 1 (H2) | 1 (M1) | 3 (L1, L2, L3) |
| manifest_builder.py | 0 | 1 (M2) | 0 |
| pick_model.py | 0 | 0 | 1 (L6, two sub-notes) |
| sevenfold.py | 1 (H1) | 0 | 1 (L4) |
| autostart.py | 1 (H3) | 0 | 1 (L2 shared) |
| catalogue_aurora.py | 1 (H4) | 0 | 1 (L5) |
