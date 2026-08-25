# Sweep 29 — Batch 06 Audit

**Modules:** `src/read.py` (1135 lines), `src/health.py` (428 lines), `src/estate.py` (338 lines),
`src/hosts.py` (253 lines), `src/profile.py` (201 lines), `src/ledger.py` (136 lines) — all read
in full, line by line.
**Run:** run29, batch 6
**Method:** Full read of every line in every module, plus targeted reproduction scripts run with
`PYTHONIOENCODING=utf-8 C:/Users/imarl/miniconda3/python.exe` against a scratch directory, plus
live queries against the real corpus (`pipeline.records()`, `feats.HOSTS`) to confirm that
mechanisms found by reading actually fire on production data, not just in theory.

## Headline

Two of the six modules (`estate.py`, `profile.py`) and one lore module (`ledger.py`) show no
correctness bugs. `read.py` has one **critical, fully reproduced** correctness bug (distinct
entities silently sharing a cache file and inheriting each other's feats), one **reproduced**
concurrency race in a cache write the codebase's own sibling function was explicitly hardened
against, and one **reproduced** systematic false-negative in name-matching that affects a
measured 2.0% of the entity corpus. `health.py` has one **reproduced** cross-process lost-update
race in the failure ledger itself — the file whose entire purpose is to make sure counts are
never silently lost. `hosts.py` has one unlocked read-modify-write of the same shape, unconfirmed
as currently exploited (HYPOTHESIS).

---

## src/read.py

### 1. Correctness bugs

**[CRITICAL] `cache_path()` collapses distinct entity names into the same file; `read_entity()`
trusts whichever one got there first — feats are silently misattributed between different
entities.**
File: `src/read.py:534-537` (`cache_path`), `src/read.py:605-620` (`read_entity` cache-hit path).

```python
def cache_path(host, name):
    return os.path.join(CACHE, re.sub(r"[^A-Za-z0-9]+", "_", host)[:40],
                        re.sub(r"[^A-Za-z0-9]+", "_", name)[:80] + ".json")
...
def read_entity(c, host, name, cap_chunks=None):
    path = cache_path(host, name)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)          # <-- never checks cached["entity"] == name
        except Exception:
            ...
```

`cache_path` sanitizes the entity name with `[^A-Za-z0-9]+` -> `"_"` before building the on-disk
path. That sanitizer is not injective: punctuation-only differences between two *different* real
entities collapse to the identical filename, and `read_entity`'s cache-hit branch returns whatever
is at that path without ever comparing `cached["entity"]` to the `name` argument it was called
with. Whichever entity's read finishes first "wins" the cache slot permanently; every later call
for the *other* entity silently receives the first entity's feats as if they were its own.

**REPRODUCED against the live corpus.** Queried every `(host, name)` pair the pipeline actually
produces and found 6 real collisions, including cases in `data/`:

```
('forgottenrealms_fandom_com', 'Ten_Towns')  <-  'Ten-Towns'  AND  'Ten Towns'
('en_wikipedia_org', 'V_r')                  <-  'Vár'        AND  'Vör'
('pixar_fandom_com', 'Magic_8_Ball')         <-  'Magic 8 Ball' AND 'Magic 8-Ball'
('bindingofisaac_fandom_com', 'Infested_')   <-  'Infested!'  AND  'Infested?'
```

Confirmed directly:
```python
>>> R.cache_path('forgottenrealms.fandom.com', 'Ten-Towns') == \
    R.cache_path('forgottenrealms.fandom.com', 'Ten Towns')
True
```
"Ten-Towns" and "Ten Towns" are plausibly two distinct catalogued entries (a settlement and a
faction/place variant is exactly the shape Forgotten Realms sources produce); "Vár" and "Vör" are
two different figures. Whichever is queued first in a `run()` pass writes the cache file; the
second one's `read_entity()` call sees `os.path.exists(path)` true and returns the *first*
entity's full feats record, unmodified, under the second entity's name. This produces a
fully-shaped, plausible-looking record that is simply wrong — the worst version of this project's
signature defect, because unlike an empty/dropped result it does not even look suspicious.
**REPRODUCED.**

### 2. Swallowed failures

No bare `except: pass` that discards real results. Every `except` in this file routes through
`silence.note(...)` (compliant with the project's own audit discipline) except the one
documented, deliberate exemption at line 620 (`_ = "silence-exempt: removing an already-gone
corrupt cache needs no record"`), which is correctly reasoned: removing a file that is already
gone is not a failure to record. **VERIFIED-BY-READING.**

### 3. Hard Rule 0 caps

- `cap_chunks` (`read_entity` line 605, `chunks[:cap_chunks]` line 666-667) defaults to `None`
  everywhere it is threaded through (`run(cap_chunks=None)` line 968, `main()`'s `--chunks`
  argparse default `None` line 1105) — uncapped is the normal path; the cap is strictly opt-in via
  CLI flag. **Not a violation** — verified the default flows through unmodified end-to-end.
- `discover`... not in this file (see hosts.py below).
- `run()`'s `if limit: todo = todo[:limit]` (line 971) is the same shape: `--limit` is an opt-in
  CLI flag for manual/test runs, defaults `None`. **Not a violation.**
- No other `[:N]` on a write or computed universe found. `chunks[:12]` sample prints in `main()`
  (line 1119, `for f in out["feats"][:12]`) are DISPLAY truncation of an already-complete
  in-memory result, not a data cap.

### 4. Checks that cannot fail

None found. The verbatim check (`_norm_q(s) not in _norm_q(ch)`, line ~710) and the round-trip
guards elsewhere in the file compare real derived values, not tautologies.

### 5. Two-writer contract

`read.py` does not write catalogue records at all (it writes only its own caches:
`data/readfeats/*` via `read_entity`, `data/chunkfeats/*` via `_chunk_put`, and
`state/read_queue_index.json` via `_save_qcache`), so `pipeline.write_record` /
`write_record_catalogue` do not apply here. All three cache writers use the
tmp-file-plus-`silence.replace_retry` pattern, which is the sanctioned way to land a shared state
file. **Compliant in principle — but see the race below, where one of the three writers does not
follow the pattern its own sibling was hardened to use.**

### 6. Concurrency races

**[HIGH] `read_entity`'s final cache write uses a non-unique temp filename, unlike its sibling
`_chunk_put`, which the file's own docstring says was hardened against exactly this race.**
File: `src/read.py:754-756`.

```python
os.makedirs(os.path.dirname(path), exist_ok=True)
tmp = path + ".tmp"                                    # <-- fixed name, no pid/thread
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
silence.replace_retry(tmp, path)
```

Compare `_chunk_put` (`src/read.py:592-599`), whose own docstring explains the fix:

> "A PER-WRITER TEMP NAME. This was `p + ".tmp"`, derived only from the cache key, so two workers
> answering the same passage at once opened and truncated ONE file — each writing over the other
> mid-dump, then both renaming it... The pid and thread id make the staging file private."

`read_entity`'s own final write (the per-entity `data/readfeats/<host>/<name>.json` cache) still
uses the un-hardened `path + ".tmp"` pattern the sibling function was fixed to move away from.

This is exploitable in the current corpus, not merely theoretical: `queue()` (line 863) builds one
row per `(source, entry)` pair with no dedup on `(host, name)`, and `run()` maps `work()` over that
list with a `ThreadPoolExecutor`. **REPRODUCED that the trigger condition exists**: querying the
real pipeline records for `(host, name)` pairs claimed by more than one source found **647
collisions** (e.g. `('forgottenrealms.fandom.com', 'Order of the Gauntlet')` claimed by both
"Acquisitions Incorporated" and "Adventurers League"). Any two such rows landing in the same
`ThreadPoolExecutor` pass call `read_entity()` for the identical `(host, name)` concurrently, and
both target the identical `path + ".tmp"`.

**REPRODUCED the failure mode itself** with a driver script replicating the exact write pattern
under two threads with a widened interleave window: one thread's `os.replace(tmp, dst)` raised
`FileNotFoundError` because the other thread's `os.replace` had already consumed the shared tmp
file. That exception is **not** caught by `silence.replace_retry`, which only retries
`PermissionError` — so under this exact race the write raises out of `read_entity` entirely
(caught upstream by `run()`'s own `try/except` around the call and recorded as a generic failure,
wasting that worker's read rather than corrupting data outright in the case observed; a
same-fd-different-timing interleaving without the `FileNotFoundError` would instead produce the
"one writer's dump truncated by another's" torn-write outcome `_chunk_put`'s docstring describes).

### 7. Docstring/comment contradictions

**[LOW]** `src/read.py` (comment above `CASCADE_TRIES`, near line 208): "Attempts through the pool
before a chunk is handed to the local GPU. Each attempt claims a different bucket, so **three is
three providers, not one provider three times**." but `CASCADE_TRIES = 5`. The comment reads as
left over from an earlier value of the constant. Cosmetic only — the code itself (`for attempt in
range(CASCADE_TRIES)`) is correct regardless of what the comment says. **VERIFIED-BY-READING.**

### Additional finding (lens 1, correctness) — systematic false negative in name-matching

**[MEDIUM] `_names()` cannot ever match a name-based hit for an entity whose designation has no
word longer than 3 characters; it silently falls back to pronoun-only matching, discarding real,
verbatim, on-page feat sentences.**
File: `src/read.py:171-172` (word filter), used at `src/read.py:706-709` inside the keep/drop
loop, where a failed `_names()` check routes a verified, verbatim sentence to
`generic_dropped` and it is never retried (the chunk is marked answered and cached).

```python
parts = [w for w in re.split(r'[^A-Za-z]+', entity) if len(w) > 3]
...
if any(t.startswith(w.lower()) for t in re.split(r'[^a-z0-9]+', low) if t for w in parts):
    return True
words = set(re.split(r'[^a-z]+', low))
return bool(words & {'he', 'she', 'they', 'his', 'her', 'their', 'him',
                     'himself', 'herself', 'themselves'})
```

If every word of `entity` is 3 characters or shorter, `parts` is empty, `any(...)` over an empty
iterable is `False`, and the function can only return `True` via a pronoun in the sentence. A real
feat sentence that names the character directly and contains no pronoun ("Vi punched through the
reinforced concrete wall without slowing down.") is therefore always rejected as "generic" for
such entities, indistinguishable downstream from a genuine rulebook-style non-feat.

**REPRODUCED, directly:**
```python
>>> R._names('Kai defeated the ancient dragon in single combat.', 'Kai')
False
>>> R._names('Vi punched through the reinforced concrete wall without slowing down.', 'Vi')
False
>>> R._names('Goku shattered the mountain with a single punch.', 'Goku')   # control, passes
True
```

**REPRODUCED at corpus scale** — queried every catalogued entry's `name` field: **1,969 of 98,145
entries (2.0%)** have no word over 3 characters, including real characters with combat feats
(`Vi`, `Ash`, `BMO`, `Dek`, `Rex`-shaped names among them, plus many catalogue/location codes).
Every one of them is subject to this systematic under-count for as long as the entity is read.

---

## src/health.py

### 1. Correctness bugs

None found beyond the race below. `check_state()`'s stranded-batch detection and
`reopen_stranded()`'s repair logic were read closely and both correctly implement what their
extensive docstrings claim (positional done-marker over a mutating list; report-only vs.
`--go`-gated write). Spot-checked `check_context_budget()`'s arithmetic (`sys_toks + body_toks +
reply` vs `ctx`) against `read.py`'s actual `CHUNK`/`SYSTEM` values — consistent.

### 2. Swallowed failures

All `except` blocks route through `silence.note(...)`, a `print(..., file=sys.stderr)`, or are the
explicitly-reasoned catch-all in `note()`/`flush()`'s sample-write path (`except Exception: pass
# the evidence bag must never break the ledger write`, line 143-144) — deliberate, documented,
and low-consequence (best-effort samples, not the ledger itself). **VERIFIED-BY-READING.**

### 3. Hard Rule 0 caps

**[LOW, borderline]** `check_caches()` (`src/health.py:220-253`) samples only the first 200 files
per host directory (`for fp in files[:200]`, line 241) via `glob.glob` order, which is not
guaranteed to be a representative/random order, to decide whether "all sampled entries [are]
empty" (line 251-252). This is a genuine sample of a shared directory used to feed a pass/fail
verdict, though it is a **diagnostic health check**, not a data write or a computed universe that
gets persisted — the comment explicitly and reasonably justifies it on wall-clock grounds ("parsing
200 records for each of 147 hosts... pushed a cycle past five minutes before any work began").
Direction of the resulting error is the safer one for the check's purpose (declares "broken" only
if literally every sampled file up to 200 is empty), but a host directory where the *first* 200
files (in glob order) happen to be empty and the remainder are not (e.g., an early API-path bug
later fixed, files added over time) would still misreport as fully broken. Flagging for the
supervisor's judgment rather than as a hard violation, since it inspects rather than writes.
**VERIFIED-BY-READING.**

### 4. Checks that cannot fail

None found. All five `CHECKS` entries do live, real comparisons.

### 5. Two-writer contract

`health.py` writes only shared *state* files (`state/failures.json`, `state/failure_samples.json`,
and, in `reopen_stranded()`, `state/PIPELINE_STATE.json`), all via the
tmp-file-plus-`silence.replace_retry` pattern — the sanctioned path for shared state per the
contract. `reopen_stranded()`'s own docstring (line 356-360) explicitly notes it used to be the
one writer breaking the atomic-write contract on `PIPELINE_STATE.json` and has since been
corrected to land the same way `pipeline.py` does. **Compliant**, modulo the race below, which is
a synchronization gap rather than a wrong writer.

### 6. Concurrency races

**[HIGH] `flush()` performs an unsynchronized cross-process read-modify-write of
`state/failures.json`; the `threading.Lock` at line 62 protects only the in-process `Counter`,
not the file, and the module's own docstring says every one-shot subprocess in the kit calls this
exact function.**
File: `src/health.py:61-62` (`LEDGER = collections.Counter()`, `_LOCK = threading.Lock()`),
`src/health.py:85-123` (`flush()`).

```python
LEDGER = collections.Counter()
_LOCK = threading.Lock()          # protects LEDGER (in-process) only
...
def flush():
    ...
    prev = {}
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, encoding="utf-8") as f:
                prev = json.load(f)          # READ
        except Exception as e:
            ...
    for k, v in LEDGER.items():
        prev[k] = prev.get(k, 0) + v          # MODIFY (in memory, per-process)
    tmp = LEDGER_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(prev, f, indent=1, sort_keys=True)
    if silence.replace_retry(tmp, LEDGER_PATH):          # WRITE (atomic, but too late)
        LEDGER.clear()
```

The comment at line 104-109 states plainly: *"state/failures.json is the highest-traffic shared
file in the project — the dashboard polls it, standards reads it, and EVERY process
read-modify-writes it through health.flush()."* The final write is atomic (`replace_retry`), which
prevents a *torn* file, but atomicity of the write does not make the READ-MERGE-WRITE sequence
atomic across processes: two processes can both read the same "before" state, each merge their
own counts on top of it, and the second process's write silently overwrites the first process's
persisted counts — a classic lost-update race, happening to the one file whose entire purpose is
to guarantee failure counts are never silently lost.

**REPRODUCED** with a driver script replicating `flush()`'s exact read/merge/write logic under two
threads with a widened interleave window (one thread sleeps between its read and its write to
force the interleaving that two independent processes could produce naturally under load):

```
final ledger on disk: {'existing:key': 100, 'wikipedia:404': 12}
expected if both counts had survived: existing:key=100, wikipedia:404=12, fandom:Timeout=8
LOST counts: ['fandom:Timeout']
```

The second process's entire 8-count contribution (`fandom:Timeout`) vanished from the persisted
ledger with no error, no exception, and no trace — silently, which is precisely the failure mode
`health.py` exists to make impossible. Given `note()` is armed via `atexit` and also flushes every
`FLUSH_EVERY=25` records from *inside* long-running jobs (line 145-150), and this project runs
many concurrent workers/subprocesses (`hosts.discover()`'s `ThreadPoolExecutor`, `read.py`'s own
multi-worker `run()`, supervisor-launched one-shot stages), the window for two flushes landing
close together is realistic, not contrived.

### 7. Docstring/comment contradictions

None found; the file is unusually candid about its own history and the current code matches what
its comments claim, apart from the race above (which the comments do not claim is solved — they
describe the write's atomicity, never the read-modify-write cycle's).

---

## src/estate.py

No correctness bugs, swallowed failures, cap violations, tautological checks, writer-contract
violations, or races found. This module is deliberately the project's "check nothing is sampled"
auditor and it holds itself to that standard: `artifacts()` opens and parses **every** file under
`data/`, `src/`, `state/`, `output/`, `prompts/`, `reference/`, `registry_terminal/`, `handoff/`
with no `[:N]` anywhere in the walk or the result collection (`bad.append(r)` at line 146 appends
every failing record, not a sample). `inspect()`'s zero-byte/log-extension exemption (lines 69-78)
is explicitly reasoned in its own comment and correctly scoped to `.log/.tmp/.out/.err`. `charter()`,
`written()`, and `terminal()` all perform genuine existence/parse/count checks against real files,
none are tautological. `external()`'s live Ollama/Cascade/disk checks are real network/filesystem
probes, not simulated. **VERIFIED-BY-READING**, module is clean.

One label-only nit, not worth a severity tier: the hardcoded `silence.note("estate.py:83")` /
`":85"` / `":87"` / `":93"` / `":96"` / `":107"` site labels (lines 85, 88, 91, 98, 102, 114) are
off by 1-2 from the `except` lines they actually sit under (drift from prior edits). Purely
cosmetic — these are free-text labels for the failure ledger, not line numbers anything resolves
programmatically, so it costs nothing but a moment's confusion when grepping the ledger by
site name. **VERIFIED-BY-READING**, not listed as a scored finding.

---

## src/hosts.py

### 1-4. Correctness / swallowed failures / caps / tautologies

No bugs found. `hosts_for()` correctly orders primary-then-extras and dedups (`if h and h not in
out`). `discover()`'s `per_source=24` truncation of the *candidate* list (line 166-167) is applied
only to speculative candidates *after* `HC.candidates()` has already ordered grounded hosts first
— explicitly reasoned in the comment ("the bound sits AFTER the evidence, never through it, and
what it drops is guesses rather than known hosts") and does not truncate the roster being scored
against (the file's own comment at line 149-152 calls out that exact prior bug — capping the
*roster* at `[:40]` — as already found and fixed in run #26). Reviewed and considered
**not a Hard Rule 0 violation**: it bounds network probes of invented URLs, not the evidence a
verdict is computed from.

### 5. Two-writer contract

`add()` (line 78-97) writes `data/SOURCE_HOSTS.json` via `silence.write_json`, the sanctioned
atomic-write path for shared state, and explicitly never touches `WIKI_HOSTS.json` (the primary,
owned elsewhere). **Compliant.**

### 6. Concurrency races

**[LOW, HYPOTHESIS]** `add()` performs an unlocked read-modify-write of `data/SOURCE_HOSTS.json`
(`data = _load(EXTRA, {})` at line 82, mutated, then `silence.write_json(EXTRA, data, ...)` at
line 94) — the same shape as the `health.py` race proven above. Within a single `discover()`
process this is not currently exploitable: `discover()`'s `ThreadPoolExecutor` (line 190) only
parallelizes the scoring work in `work()`; every `add()` call happens serially in the main thread
as `ex.map()` results are consumed (line 191-199), so there is no in-process race. The exposure
would require two *separate* `discover()` invocations (or `hosts.add()` calls from unrelated code
paths) running concurrently against the same `SOURCE_HOSTS.json`. I found no evidence in this
batch that two `discover()` runs are ever launched concurrently in practice, so this is
**HYPOTHESIS**, not reproduced — flagging because the code has no guard against it and the module's
own docstring already acknowledges concurrent *readers* ("SOURCE_HOSTS extras are read live while
discover() walks"), which suggests concurrent access to this file is an anticipated condition the
writer side does not fully account for.

### 7. Docstrings

None contradicted; the module's prose about the lift-vs-substance judgment (lines 100-121) matches
`specialist`/`substantial` logic exactly (lines 181-184).

---

## src/profile.py

No correctness bugs, swallowed failures, cap violations, tautologies, writer-contract violations,
or races found.

- `encode()`/`decode()` round-trip is exercised by `main()` against every built row (lines 182-187)
  with a real comparison (`d["address"] != r["address"] or d["profile"] != r["profile"]`), not
  tautological.
- `build_all(limit=None)` (line 127) passes `limit` straight through to `WS.build_all(limit)`;
  confirmed by reading `worldseed.build_all()` that `limit=None` is honored as unlimited
  (`if limit and len(out) >= limit: return out`) and the default flows through uncapped end to
  end — **not a violation**.
- The two `try/except Exception` blocks loading `GENRES.json`/`TIERS.json` (lines 129-138) both
  route through `silence.note(...)` before defaulting to `{}` — observed, not swallowed.

---

## src/ledger.py

This module is a self-contained fictional currency-conversion utility (in-world "Standard" unit
derived from `physics.MATERIAL["rock"]["pulv"]`); it performs no file I/O, no catalogue writes,
and is not part of the two-writer contract or the concurrent pipeline surface, so most lenses do
not apply.

- `to_standards()`/`from_standards()`/`cross_rate()` correctly guard the `None`-rate
  ("not convertible") case for every lookup, including the deliberately-unconvertible
  `"poneglyph-grade favour"` entry — verified by hand-tracing the rate arithmetic.
- **[LOW, cosmetic]** `assay_to_standards()` (line 116-136): when `magnitude_band` is the last
  entry of `LADDER`, `hi = BAND_EDGES[LADDER[min(i+1, len(LADDER)-1)]]["ruin"]` resolves to the
  same value as `lo`, collapsing `math.log(hi) - math.log(lo)` to `0` — so `ruin_score` has no
  effect at the top band and every score in `0-10` returns the same `joules` value at that one
  boundary. **VERIFIED-BY-READING**, not reproduced against real `assay.BAND_EDGES`/`LADDER` data
  (out of scope for this batch), and low-consequence: it affects only the single highest band and
  degrades gracefully (returns the band floor rather than erroring or fabricating).

---

## Coverage confirmation

Recorded via `sweep_plan.record('run29', ['read.py','health.py','estate.py','hosts.py',
'profile.py','ledger.py'], batch=6)`.
