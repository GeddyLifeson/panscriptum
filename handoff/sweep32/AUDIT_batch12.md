# Batch 12 audit — run32

Modules read in full (every line):
- `src/overnight.py` — 909 lines
- `src/chain.py` — 497 lines
- `src/identity.py` — 423 lines
- `src/pantheon.py` — 308 lines
- `src/tempus.py` — 254 lines
- `src/propagation.py` — 214 lines
- `src/catalog.py` — 127 lines

Total: 2,732 lines.

---

## BLOCKING

None found in this batch. (The two findings closest to BLOCKING — the `chain.py:354` race and
the `identity.py` continuity-recognition gap — are filed as MAJOR because each has a real but
bounded blast radius: one undercounts a diagnostic field, the other silently over-merges a
narrow class of single-bearer branch continuities rather than corrupting the whole graph.)

---

## MAJOR

### 1. `src/chain.py:354` — shared `Counter` mutated OUTSIDE the lock under 8 concurrent workers (CONFIRMED, the tasked headline bug)

```python
def work(chunk):
    ...
    for o in (got or {}).get("outcomes", []):
        ...
        if wk in idx and lk in idx:
            local.append(...)
        else:
            for side, k in ((w, wk), (l, lk)):
                if k not in idx:
                    unmatched[side[:40]] += 1        # <-- line 354, NOT under `lock`
    with lock:
        done["n"] += len(chunk)
        done["pairs"] += len((got or {}).get("outcomes", []))
        for e, src in local:
            edges[e] += 1                            # correctly locked
            prov[e].append(src)                       # correctly locked
            done["kept"] += 1
        ...
...
with ThreadPoolExecutor(max_workers=workers) as ex:
    list(ex.map(work, chunks))
```

`unmatched` is a `collections.Counter()` (line 305) shared by every worker thread. `edges`,
`prov`, and `done` are all mutated only inside `with lock:` (lines 358–362) — correctly
serialized. `unmatched[side[:40]] += 1` at line 354 is mutated *before* that `with lock:` block,
i.e. with no synchronization at all, while up to 8 threads (`--workers 8` default, line 440) run
`work()` concurrently. `Counter.__getitem__`/`__setitem__` under `+=` is a read-modify-write
across multiple bytecode ops; CPython can switch threads between them, so concurrent increments
on the same key are lost updates (classic race). The undercounted `unmatched` Counter is then
**persisted**: `write_result()` (line 91) writes `unmatched.most_common(40)` straight into
`data/CHAIN.json` (line 108). This is a genuine correctness bug reaching a published artifact,
not just a log line — confirmed exactly as briefed.

Audited the rest of chain.py's locking for the same shape: `edges[e] += 1` (359) and
`prov[e].append(src)` (360) are correctly inside the lock; `done` fields (356–357, 362) are
correctly inside the lock. No other unlocked shared-state mutation found in the threaded path.
The fix shape used elsewhere in the same function (accumulate to a thread-local, e.g. `local`,
merge under lock) was simply not applied to `unmatched`.

### 2. `src/chain.py:108` — `unmatched.most_common(40)` truncates a persisted list (HARD RULE 0)

```python
"unmatched": (unmatched.most_common(40) if hasattr(unmatched, "most_common")
              else (unmatched or [])),
```

`write_result()` is the sole writer of `data/CHAIN.json` (a "THE ONE WRITER" per its own
docstring). Before persisting, it hard-caps the "names that match nothing the library
catalogues" list to the top 40 by frequency. This is not console/log display formatting (the
console print at `main()` line 457 is separately, and legitimately, capped to 8 for the
terminal) — this is the field written into the permanent data file. Any unmatched name outside
the top 40 by count is silently absent from the record, which is exactly Hard Rule 0's
"truncation of ... an entry list... is a BUG unless pure display formatting." A low-frequency
unmatched name (e.g. a real entity spelled slightly differently, or a genuinely new/unindexed
character) that would flag a coverage gap is dropped from the on-disk artifact rather than kept
in full.

### 3. `src/identity.py:180-207` — `_is_continuity()`'s single-bearer BRANCHING case is unreachable, contradicting the function's own docstring example (PARTIALLY CONFIRMS the lead)

```python
def _is_continuity(desig, stat):
    ...
    n = stat["bearers"] if isinstance(stat, dict) else stat
    shared = stat.get("shared", 0) if isinstance(stat, dict) else 0
    if n >= MIN_BEARERS:          # MIN_BEARERS = 3
        return True
    return n >= 2 and shared >= max(2, 0.5 * n)
```

Worked the arithmetic precisely rather than taking the lead's "shared <= n always holds" claim
at face value — that part is true (in `mine()`, `shared = sum(1 for x in b if len(seen[x]) > 1)`
is a count of a subset of `b`, and `n = len(b)`, so `0 <= shared <= n` structurally) but it does
**not** make the whole final `return` unreachable. Since the `n >= MIN_BEARERS` branch already
returns True for `n >= 3`, only `n` in `{1, 2}` ever reach the final line:

- **`n == 2`**: condition becomes `shared >= max(2, 1.0) = 2`, i.e. `shared` must equal 2 (its
  structural max at `n=2`). Reachable — not vacuous — but requires *both* bearers of a
  2-bearer designator to be shared elsewhere, stricter than the docstring implies.
- **`n == 1`**: `n >= 2` is `False` unconditionally, so the whole expression is `False`
  regardless of `shared`. **This branch is dead.** A designator with exactly one mined bearer
  can never be recognized as a continuity via BRANCHING or POPULATION, no matter how many other
  branches that one character is independently known to appear in.

This directly contradicts the function's own docstring, which uses a single-bearer case as its
worked justification for why "branching is sufficient": *"`(Fates)` has one bearer and is
obviously a continuity because that bearer exists in three other branches. Either alone admits
it."* Given `n=1`, the code as written returns `False` for exactly this example — the docstring
describes a case the code cannot produce. Concretely: the first time a franchise's newest branch
has only one character mined into the feats cache, `identify()` (line 237) will return
`(base, None)` for it — the branch designator is silently discarded and that entity's record is
folded into the base/undifferentiated node, which is precisely the "silent merge of a real
timeline split" the module exists to prevent (per the file's own owner-ruling epigraph: "each
continuity ... should be their own, not resolved into one, it's timelines not retcons"). Rated
MAJOR rather than BLOCKING because it only fires for single-bearer branch designators (a
transient state that a franchise usually grows out of as more of its pages are mined), not for
established continuities.

### 4. `src/identity.py:210-223` (`load()`) — hand-rolled `path + ".tmp"` write with a non-unique temp name (CONFIRMED reported instance)

```python
def load(refresh=False):
    if not refresh and os.path.exists(CACHE):
        try:
            with open(CACHE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            silence.note("identity.py:load")
    inv = mine()
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    tmp = CACHE + ".tmp"                      # <-- fixed, non-unique temp name
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(inv, f, indent=1, sort_keys=True)
    silence.replace_retry(tmp, CACHE)
    return inv
```

This is a genuine instance of the class `chain.py`'s own comments describe as "the collision
m100 closed at twelve sites on 2026-08-25... chain.py's two were missed" — except here it's
`identity.py` that was missed. The *rename* step correctly uses `silence.replace_retry(tmp,
CACHE)` (partial compliance with the two-writer contract), but the *write* step bypasses
`silence.write_json` entirely and builds `tmp = CACHE + ".tmp"` — a fixed path, not a
uniquified one (e.g. pid/uuid-suffixed, which is what `silence.write_json` provides and what the
`chain.py` comments at lines 111-119 describe as the actual fix for this exact bug class). Only
one caller in `src/` reaches this with `refresh=False` today (`chain.py:148`'s `ID.load()`), so
the write path only fires on first build or on a corrupt/missing cache — but `identity.py`'s own
CLI (`main()`, line 339, `load(refresh=a.refresh)`) can trigger it directly, and nothing prevents
a second process (a person running `python src/identity.py --refresh` while a supervised pipeline
cycle is also mid-harvest) from writing the same `DESIGNATORS.json.tmp` concurrently — one
process's rename can then clobber the CACHE with the other's half-written or stale dump. This is
the exact mechanism (not just the shape) of the "costliest recurring defect" the brief named.

---

## MINOR

### 5. `src/overnight.py:180` (`running()`) — fragment matching is unanchored substring containment; can false-positive on an unrelated file name (CONFIRMED via cross-file evidence)

```python
if fragment in cmd.replace("\\", "/").split("/")[-1] or fragment in cmd:
    return True
```

The second clause (`fragment in cmd`, tested against the *raw, full* command line) is
necessary — not redundant — for fragments that include a file-path argument containing a slash
(e.g. `start("prose", [generate.py, "--manifest", ".../output/index/manifest.json"], ...)`
breaks the first clause's `.split("/")[-1]` heuristic, since the last `/`-delimited segment of
that command line is `manifest.json`, not `generate.py --manifest ...`). But that same clause
does plain substring containment with no word-boundary anchoring, so `running(X)` returns True
for any live process whose *entire* command line happens to contain `X` as a substring anywhere,
not just as the invoked script name. Verified this is not hypothetical: `"sweep.py"` is a literal
substring of `"allsweep.py"` (confirmed programmatically against the actual `src/` file list —
the only collision among the job-name fragments used in this codebase). `foreman.py:669`'s
`run_character_sweep()` remedy calls `ON.running("sweep.py")` before starting the character
sweep; when `allsweep.py` (a real, frequently-invoked process in this project) happens to be
running at that moment, `running("sweep.py")` returns True even though the actual `sweep.py`
process is not running. The remedy then takes the early-return branch and reports
`(True, "character sweep already running")` — a false positive recorded as success — and never
calls `ON.start(...)`, so `CHARACTER_SWEEP.json` silently fails to be rebuilt whenever the
foreman's check coincides with an `allsweep.py` run. This is a swallowed no-op wearing the shape
of a healthy outcome, in the file most directly responsible for singleton-job correctness.
(Root-cause fix belongs in `overnight.py`'s `running()`; the concrete symptom lives in
`foreman.py`, outside this batch, so filed here as MINOR since no other collision exists in the
current file set and the fragments involved are mostly literal, non-colliding filenames.)

### 6. `src/overnight.py:503,521,318,360,385` and `src/chain.py:169,276,283,332` — stale line-number labels in `silence.note()` calls, undermining the failure-class ledger they feed

Confirmed by direct comparison of the literal label string against the line it actually sits on
today:

| call site (current line) | label says | 
|---|---|
| `overnight.py:318` | `"overnight.py:203"` |
| `overnight.py:360` | `"overnight.py:229"` |
| `overnight.py:385` | `"overnight.py:253"` |
| `overnight.py:503` | `"overnight.py:124"` |
| `overnight.py:521` | `"overnight.py:141"` |
| `chain.py:169` | `"chain.py:91"` |
| `chain.py:276` | `"chain.py:155"` |
| `chain.py:283` | `"chain.py:161"` |
| `chain.py:332` | `"chain.py:252"` |

Every one of these has drifted from its authoring-time line number as the surrounding code was
edited (some by 100+ lines). These strings are the *keys* aggregated into `state/failures.json`,
which `overnight.py`'s own `ledger_report()` (line 373) prints every cycle specifically so that
"5,590 identical HTTPErrors show up as one loud line instead of as 5,590 entities that look like
they honestly have no page" — i.e. the whole point of these labels is to tell a person at-a-
glance which call site is failing. A label reading `overnight.py:124` when the actual failure is
at line 503 sends triage to the wrong function. Contrast with the *semantic* labels used
elsewhere in the same files (`"overnight.py:prose-gate"`, `"overnight.py:keep_warm"`,
`"chain.py:tuning"`, `"chain.py:harvest-idx-denied"`) which don't go stale under editing — the
fix pattern already exists in the same files, just wasn't applied at these 9 sites.

### 7. `src/overnight.py:496-510` (`coverage_snapshot()`) — subprocess exit code is never checked before trusting `COVERAGE.json`

```python
def coverage_snapshot():
    try:
        subprocess.run([PY, os.path.join(SRC, "coverage.py")], cwd=HERE,
                       capture_output=True, text=True, timeout=1800, ...)
        rows = json.load(open(os.path.join(HERE, "data", "COVERAGE.json"), encoding="utf-8"))
    except Exception as e:
        silence.note("overnight.py:124")
        return {"error": f"{type(e).__name__} {str(e)[:60]}"}
    ...
```

`subprocess.run(...)` is called without `check=True` and its `returncode` is never inspected. If
`coverage.py` exits non-zero without raising on the Python side (e.g. it fails partway but still
exits cleanly, or crashes before rewriting `COVERAGE.json` but a *prior* successful run's
`COVERAGE.json` is still on disk), this function will happily `json.load()` the **stale** file
and return it as though it were this cycle's fresh measurement — no exception, no `"error"` key,
nothing distinguishing it from a real snapshot. That result flows straight into
`write_status()` (STATUS.md) and the per-cycle log line ("coverage: N cited (...%)..."), i.e. the
exact mechanism the module's own top docstring promises ("MEASURE EVERY CYCLE... the morning
question is answered by a file rather than an archaeology session") silently breaks in precisely
the failure mode (a stale measurement presenting as fresh) the file elsewhere goes out of its way
to guard against (e.g. `preflight()`'s explicit "DID NOT RUN" logging at line 529, or the
"measurement failure wearing the shape of a measured zero" comment at line 838-843 for the
`snap.get("error")` case — that comment only helps when an exception WAS raised).

---

## NOTE

- `overnight.py:44-76` (`_prose_enabled`) — audited per the brief's specific concern. This is
  **already fixed**: it now delegates to `prose_gate.gate_open(cfg)[0]` rather than
  re-implementing the check, and the extensive docstring documents the exact historical bug
  (`bool()` truthy-string gate, `"false"` opening it) as the reason for the delegation. No
  second, looser gate re-implementation was found anywhere else in `overnight.py` — grepped for
  every `cfg.get(`, `yaml.safe_load(`, and `enabled`/`gate` occurrence in the file; the only other
  config read is the unrelated `_keep_warm()` Ollama-ping config block (`ollama_host`, `model`,
  `num_ctx`), which touches no gate value. `overnight.py` never references `step4_enabled` at
  all — that gate, if it exists, is enforced entirely outside this module (presumably in
  `generate.py`/`prose_gate.py`, outside this batch), so nothing to confirm or refute here.
- `overnight.py:369,392` (`watch_report`, `ledger_report`) and `write_status:591` — `[:top]`,
  `[:6]`/`[:8]`/`[-12:]` truncations are all console/`STATUS.md` *display* summaries of data that
  remains fully intact in its source-of-truth files (`OVERWATCH.json`, `state/failures.json`, the
  in-memory `history` list); each prints the true total count alongside the truncated detail
  list. Fits the Hard Rule 0 "pure display formatting" exemption — not flagged as a violation.
- `chain.py:302` (`--limit`) — an explicit, user-opt-in CLI flag (default `None`, no truncation
  unless a person passes `--limit N`), not a silent cap. Not a Hard Rule 0 violation.
- `catalog.py:61-67` (`cmd_stats`'s "Populated sources with NO books yet") — truncates the
  printed list to 30 names but reports the true `len(missing)` and an explicit "...and N more"
  line; console-only, source data (`missing` list) computed in full beforehand. Not a violation.
- `propagation.py`, `tempus.py` — pure-math/read-only modules, no I/O writers, no `except:`
  swallowing, no truncation. Read every line; no findings. `propagation.py:shortest()`'s Dijkstra
  and `observed_mark()`'s rung search were hand-checked against their docstrings' claimed
  invariants (monotonicity of `ascension_years`, early-exit correctness) and are correct.
- `pantheon.py` — mostly a hand-authored data table (`GODS`) plus a thin compute/print layer;
  its one writer (`silence.write_json(OUT, ...)`, line 261) is fully compliant with the
  two-writer contract. No findings.
- `identity.py:210` write path — see MAJOR #4 above; this note just confirms the *rename* half
  (`silence.replace_retry`) is compliant, isolating the defect to the write-to-tmp half only.

---

## Summary of severities

- BLOCKING: 0
- MAJOR: 4 (`chain.py:354` unlocked Counter race — the tasked headline bug, confirmed;
  `chain.py:108` persisted-list truncation; `identity.py:180-207` unreachable single-bearer
  branching case; `identity.py:210-223` hand-rolled tmp-write, confirmed reported instance)
- MINOR: 3 (`overnight.py:180` running() substring false-positive, evidenced via
  `sweep.py`/`allsweep.py` collision; 9 stale diagnostic labels across `overnight.py`/`chain.py`;
  `overnight.py:496-510` unchecked subprocess exit code before trusting cached coverage data)
- NOTE: 6
