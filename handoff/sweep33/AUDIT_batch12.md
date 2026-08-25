# Batch 12 — run33
Modules read: overnight.py (909 lines), chain.py (497 lines), identity.py (423 lines), worldseed.py (327 lines), tuning.py (263 lines), propagation.py (214 lines), recover_folder_records.py (180 lines)

## FINDINGS

### 1. recover_folder_records.py:94-158 — a partial recovery can overwrite a genuinely-populated record on stale roll data  [severity: MAJOR]
`empty = [r["name"] for r in roll if r.get("entry_count", 0) == 0]` selects candidates purely from the in-memory snapshot of `data/SWEEP_ROLL.json` loaded once at process start. For every name in that list the script then writes straight to `data/records/<slug>.json` via `silence.write_json(path, record, ...)` with no `os.path.exists(path)` check and no re-read of the file's *current* content beforehand — the only gate is the roll's `entry_count` field as it stood when the script started.

```python
roll_entry = roll_by_name[name]
record = {... "mode": "folder-mechanical", "entries": entries, ...}
path = os.path.join(RECORDS, slug(name) + ".json")
if not args.dry_run:
    if not silence.write_json(path, record, indent=2, ensure_ascii=False):
```

If `SWEEP_ROLL.json` is stale relative to `data/records/` at the moment this script runs — e.g. another process (the cloud session, `resync_roll.py`, `ingest.py`, or a concurrent run of this very tool) wrote real entries to that source's record after the roll snapshot was taken but before its `entry_count` was refreshed — this script will silently replace a real, already-researched record with the lower-fidelity "folder-mechanical" transcription pulled from `LOCAL_REGISTER.json`, with no warning that anything was clobbered. The docstring only guarantees the roll accurately reflected reality *at the time it was built*; nothing in this script re-verifies that against the live directory it is about to write into. This is exactly the "records two-writer hazard" this project's own history already documents having happened once (`resync_roll.py`'s docstring, referenced in the ATOMIC comment at line 164, names this very script as a past roll-clobber source).

### 2. worldseed.py:317-322 — `WORLDSEEDS.json` is written non-atomically, unlike every sibling artifact  [severity: MAJOR]
```python
if args.write:
    path = os.path.join(HERE, "data", "WORLDSEEDS.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({w["designation"]: {"address": address(w), **w} for w in worlds},
                  f, indent=2, ensure_ascii=False)
```
This is a bare truncating `open(path, "w")` + `json.dump`, not `silence.write_json`/write-then-rename. Every other cross-cycle artifact this batch touches (`data/CHAIN.json` in chain.py, `data/DESIGNATORS.json` in identity.py, `data/SWEEP_ROLL.json` and `data/records/*.json` in recover_folder_records.py) goes through the atomic path specifically because a bare `open(path,"w")` leaves a torn file if the process dies mid-dump or a reader opens it at the wrong moment — chain.py's `write_result` docstring spells this out at length as a fixed incident class (m100). `worldseed.py --write` was missed. A kill mid-write (this file can run under `overnight.py`/`pipeline.py`-adjacent tooling) leaves `WORLDSEEDS.json` truncated/invalid JSON for the next reader.

### 3. recover_folder_records.py:162-164 — the final roll write's success/failure is discarded  [severity: MINOR]
```python
if not args.dry_run and written:
    # ATOMIC: `resync_roll.py`'s docstring names THIS script as a roll-clobber source.
    silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)
```
The return value of `silence.write_json` is checked and reported for every per-record write eleven lines above (`if not silence.write_json(path, record, ...): print("WRITE DENIED ...")`), but the final write of the whole roll ignores it entirely. If this call fails (lock contention, denied replace — the exact failure class `silence.write_json` returns `False` for, per its own contract used elsewhere in this file), the individual record files were written successfully but `SWEEP_ROLL.json`'s `entry_count` for those sources is never updated off `0`. The next run of this script (or anything else that selects work by `entry_count == 0`) will see those sources as still-empty and attempt to "recover" them again, re-running the same overwrite risk in Finding 1 against records that are now already good.

### 4. chain.py:351-354 — `unmatched` counter incremented outside the lock, across threads  [severity: MINOR]
`extract()` runs `work(chunk)` inside a `ThreadPoolExecutor(max_workers=workers)`. Inside `work`, matched pairs are appended to `edges`/`prov` only under `with lock:`, but the unmatched-name tally is not:
```python
else:
    for side, k in ((w, wk), (l, lk)):
        if k not in idx:
            unmatched[side[:40]] += 1
with lock:
    done["n"] += len(chunk)
    ...
```
`unmatched` is a single `collections.Counter()` shared by every worker thread, and `counter[key] += 1` is a read-modify-write (get, add, set) that is not atomic across threads. Under real concurrency (workers is commonly 8) this can lose increments, silently undercounting the "most common names that match nothing" diagnostic printed at the end of `main()` and written into `CHAIN.json`'s `unmatched` field. It does not corrupt the graph itself (`edges`/`prov` are correctly locked), only this diagnostic.

### 5. overnight.py — five `silence.note()` ledger keys carry stale hardcoded line numbers  [severity: MINOR]
```python
# foreman_report(), line 318:
silence.note("overnight.py:203")
# watch_report(), line 360:
silence.note("overnight.py:229")
# ledger_report(), line 385:
silence.note("overnight.py:253")
# coverage_snapshot(), line 503:
silence.note("overnight.py:124")
# preflight(), line 521:
silence.note("overnight.py:141")
```
None of these line numbers match where the calls actually sit in the current file (e.g. `coverage_snapshot()`'s exception handler is at line 503, not 124; `preflight()`'s is at 521, not 141). These labels are the keys `state/failures.json`'s ledger aggregates on and the ones `ledger_report()` itself prints as "top swallowed failures" every cycle — the exact mechanism the file's own docstring says exists so "5,590 identical HTTPErrors show up as one loud line instead of [looking like] entities that honestly have no page." A label that no longer points at the code it names defeats that purpose for a reader chasing down a specific swallow. Contrast with `overnight.py:keepwarm-no-gpu-lane` and `overnight.py:prose-gate` elsewhere in the same file, which use descriptive (and therefore refactor-stable) keys instead of a line number.

## QUESTIONS

1. **overnight.py:744 — `safety_drill()`'s return code is never used to gate the current cycle.** `main()` calls `safety_drill()` (which can find a BREACHED net and have `drill.py` raise an OWNER-level halt as a side effect) but does not branch on its return value; execution falls straight through to `preflight()` and then to starting all of that cycle's stages (dashboard, publish, foreman, overwatch, pipeline, prose, roll, then a `read_hours`-long `run("read")`, a 4h `join(roll)`, a 2h `run("pipeline")`). Only the *next* cycle's `_ESC.assert_clear()` at the top of the loop would notice the halt raised mid-cycle. The docstring frames this check as "before any stage is started," which reads as gating intent that the code doesn't enforce. This may be intentional — if `read.py`, `pipeline.py`, and `feats.py --roll` each independently call `escalation.assert_clear()` at their own startup (consistent with the file's stated INDEPENDENT-layers philosophy), the supervisor-level omission is harmless defense-in-depth rather than a gap. Settled by reading those three modules (not in this batch) to confirm they self-check escalation.

2. **overnight.py — `pipeline.py` is launched twice per cycle sharing one singleton guard.** It is started once early via `start()` (parallel with the network roll, since "the GPU-serial rule is obsolete") and again later via `run("pipeline", ..., timeout_h=2)` explicitly "after the reader so it sees the evidence the reader just produced." Both share the same `running(os.path.basename(args[0]))` guard. If the early instance is still alive when the second call is reached (plausible if `read.py` finishes quickly, or the early pipeline run is unusually slow), the second call just returns `"already-running"` and never re-triggers the post-read absorb step the comment describes. Whether this matters depends on whether `pipeline.py` is idempotent/resumable enough that the next keeper restart (every 5 min) or the next full cycle picks up the missed work — `pipeline.py` isn't in this batch.

3. **overnight.py:535 — `preflight()`'s halt condition depends on exact substring matching against `health.py`'s printed text.** `blocking = "control characters in source" in out and "FAIL  control" in out` (note the double space before "control"). This is the one condition that halts the whole night's run. It is coupled to `health.py`'s exact output phrasing, which is not in this batch to verify still matches. If `health.py`'s wording ever drifts, this specific halt goes silently permissive — which would be ironic given it exists to catch exactly that class of silent corruption. Settled by reading `health.py --preflight`'s current output format.

## CLEAN
- **identity.py** — read carefully, including the designator-inventory heuristics, the epoch-on-demand model call, and the dead-code note for the deleted `adjudicate()`. Cross-checked the claim that `chain.py` still calls `epoch_of()` directly — confirmed. No defects found.
- **tuning.py** — read carefully, including the `workers()` zero-vs-None fix (`ZERO IS A REQUEST, NOT AN ABSENCE`) and the cloud/local/starved regime logic. No defects found.
- **propagation.py** — read carefully; pure computation, no I/O writes beyond a single read of `SHARED_STAGE_GRAPH.json`, no concurrency. Dijkstra implementation, ascension/arrival-year math, and `observed_mark()`'s rung search all check out. No defects found.

Coverage recorded separately per the brief.
