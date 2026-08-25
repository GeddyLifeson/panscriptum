# Sweep #24 — Batch 05 Audit

Files in scope, all read in full, line by line:
- `src/read.py` (1136 lines) — read completely.
- `src/identity.py` (423 lines) — read completely.
- `src/worldseed.py` (327 lines) — read completely.
- `src/wh40k.py` (238 lines) — read completely.
- `src/thread_integrity.py` (184 lines) — read completely.
- `src/scale_theories.py` (148 lines) — read completely.

Cross-referenced against consumers outside the batch (`src/address_space.py`, `src/pipeline.py`,
`src/silence.py`, and briefly `src/foreman.py` for the stall-detection claim in the special-focus
brief) only far enough to confirm or refute a finding — those files were not audited in full.

---

## 1. `identity.py:180-207` — `_is_continuity()` cannot ever satisfy its own worked example

```python
def _is_continuity(desig, stat):
    ...
    n = stat["bearers"] if isinstance(stat, dict) else stat
    shared = stat.get("shared", 0) if isinstance(stat, dict) else 0
    if n >= MIN_BEARERS:                       # MIN_BEARERS = 3
        return True
    return n >= 2 and shared >= max(2, 0.5 * n)
```

The module docstring (lines 57-61) and the function's own docstring (lines 190-196) both cite
the BRANCHING test with the worked example:

> `(Fates)` has **one bearer** and is obviously a continuity because that bearer exists in three
> other branches. Either [population or branching] alone admits it.

But the code's branching path is gated by `n >= 2`. For n=1 (exactly the Fates example), that
guard is false and the function falls through to `return False` — it is *impossible* for a
single-bearer designator to be recognised as a continuity no matter how many other designators
that bearer also appears under, because `MIN_BEARERS` (population path) also requires n>=3. The
branching path, as written, only ever contributes anything at exactly n==2 (n=0/1 fail the
`n>=2` guard; n>=3 is already caught by the first `return True`), so it can never do the one job
the docstring says it exists to do: recognise a young continuity with only one character written
up.

**Failure scenario:** a franchise's alternate timeline with exactly one character page so far
(a brand-new source, or a niche continuity) is silently merged into the main line instead of
kept separate — the exact "wrong merge" the module's own comments call irreversible and worse
than the opposite mistake ("the cost of the opposite mistake is only that two records stay
separate that could have been one, which is recoverable; a wrong merge is not").

Severity: **MAJOR**. **VERIFIED** — traced by hand against the stated MIN_BEARERS=3 and the
exact n=1 worked example the docstring supplies.

---

## 2. `identity.py:291-320` — `epoch_of()` returns `""` for both "no marker" and "call failed"

```python
def _ask(prompt, system=EPOCH_SYSTEM):
    try:
        import read as R
        R.ensure_transport(verbose=False)
        return R._ask(R.config(), system, prompt, EPOCH_SCHEMA)
    except Exception:
        silence.note("identity.py:_ask")
        return None

def _json(raw):
    if isinstance(raw, dict):
        return raw
    m = re.search("[{].*[}]", raw or "", re.S)
    if not m:
        return {}
    ...

def epoch_of(sentence):
    d = _json(_ask(sentence.strip()[:1200]))
    if not d.get("explicit"):
        return ""
    return str(d.get("epoch") or "").strip()[:60]
```

If `_ask` raises (transport exception) or every transport in `R._ask`'s ladder declines
(`R._ask_ungated` returning `None` when `_TRANSPORT == "cascade"`, or a benched GPU with no
cascade), `_ask` returns `None`. `_json(None)` → `raw or ""` is `""`, no `{...}` match, returns
`{}`. `epoch_of` then sees `d.get("explicit")` is falsy and returns `""` — **identical** to the
legitimate case where the model was actually asked, actually answered, and explicitly reported
"this sentence carries no epoch marker" (`{"epoch": "", "explicit": false}`).

This is the exact defect class `EPOCH_SYSTEM`'s own prompt text warns against ("An absent marker
is a real answer. Do not guess one.") — except here the ambiguity is not the model guessing, it's
the caller being unable to tell "the model said no" from "nobody was asked." Since `chain.py:381`
calls `epoch_of()` directly to resolve mutual-pair contradictions (per the maintenance-log comment
at identity.py:323-328), a transport outage during that adjudication call silently resolves as
"no epoch, don't split the timeline" rather than "retry me" — which is this project's signature
failure (a check that cannot distinguish empty-because-absent from empty-because-broken).

Severity: **MAJOR**. **VERIFIED** by tracing the None → `{}` → `""` chain exactly.

---

## 3. `worldseed.py:317-322` — non-atomic write of a file two other modules read-and-silently-empty on failure

```python
if args.write:
    path = os.path.join(HERE, "data", "WORLDSEEDS.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({w["designation"]: {"address": address(w), **w} for w in worlds},
                  f, indent=2, ensure_ascii=False)
```

Direct `open(path, "w")` + `json.dump`, no `.tmp` + `silence.replace_retry`/`silence.write_json`
(both exist in `src/silence.py` and are used elsewhere in this same file for `DESIGNATORS.json`-
style caches). A reader that opens this path while the write is in flight — or a process killed
mid-`json.dump` — gets a truncated/invalid JSON file.

This compounds with the two real consumers:

```python
# src/address_space.py:300-304
try:
    with open(os.path.join(HERE, "data", "WORLDSEEDS.json"), encoding="utf-8") as f:
        ws = json.load(f)
except Exception:
    silence.note("address_space.py:293")
    ws = {}

# src/pipeline.py:1399-1402
try:
    seeds = json.load(open(os.path.join(HERE, "data/WORLDSEEDS.json"), encoding="utf-8"))
except Exception:
    silence.note("pipeline.py:phase_cosmology-seeds")
    seeds = {}
```

Both readers silently substitute `{}` on any parse failure. So a torn read caused by the
non-atomic write above is **indistinguishable from "no worldseeds have been generated yet"** —
`pipeline.py`'s cosmology phase would silently stamp zero worlds with shelfmarks/map seeds
instead of erroring or retrying, exactly the "check that cannot fail" shape this audit is
looking for.

Severity: **MAJOR** (already flagged as a known suspect; confirmed and the blast radius traced
to two real downstream readers that make it a silent-empty-corpus risk, not just a theoretical
atomicity nit). **VERIFIED**.

---

## 4. `wh40k.py:230-231` — same non-atomic-write pattern, currently lower blast radius

```python
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
```

Same class of bug as #3: hand-rolled `open(path,"w")` + `json.dump` on `data/WH40K_ASSAYS.json`
instead of `silence.write_json`/`replace_retry`. Unlike `WORLDSEEDS.json`, a repo-wide grep found
no other module in `src/` currently reads `WH40K_ASSAYS.json`, so today a torn write only risks
corrupting the file for the next invocation of `wh40k.py` itself (which would then need to
re-run, not silently misreport). Still a genuine two-writer-contract violation and worth fixing
before anything is wired to read it.

Severity: **MINOR**. **VERIFIED**.

---

## 5. `read.py:1097-1098` — the final "done" line drops the one number that distinguishes success from catastrophe

```python
print("done in %.2fh  %d feats kept, %d fabrications dropped"
      % ((time.time() - t0) / 3600, done["feats"], done["fab"]))
```

`done["unanswered"]`, `done["chunks"]`, and `_FELL_BACK[0]` are all tracked throughout `run()`
(accumulated at line 987, printed in the periodic progress line at 1026-1030) but **none of them
appear in the final summary**. The periodic line is the only place `chunks_unanswered` is ever
surfaced, and it is only visible to someone tailing the live log during the run.

The file's own docstrings describe two separate incidents where this exact number was the only
signal that a run had silently thrown away almost all of its work while looking healthy: "4,755
of 6,706 chunks... counted as read" (comment above `read_entity`'s cache-write guard) and "1,235
chunks handed to the GPU, 1,168 of them UNANSWERED... 94.6% of the work thrown away by a job that
looked healthy" (comment on `_local`). A run that completes with a large fraction of its chunks
unanswered — pool fully declined and the GPU repeatedly benched, but not zero throughput, so
`work()` never raises — still ends with a banner that reads exactly like a clean, complete pass:
`"done in 7.50h  312 feats kept, 40 fabrications dropped"`, with no hint that thousands of chunks
went unanswered and their entities were never cached. Anyone reading only the completion banner
(a supervisor script grepping the tail of the log, or a person checking in later) cannot tell
this pass apart from a fully healthy one without re-deriving the number from the periodic lines.

**Failure scenario:** exactly the two incidents already documented in this file's own comments,
except discovered only by someone who happened to scroll back through the live log instead of
trusting the final line.

Severity: **MAJOR**. **VERIFIED** — the tracked variables exist and are simply omitted from the
final `print`.

---

## 6. `read.py:385,402` — `_FELL_BACK[0] += 1` raced across worker threads

```python
_FELL_BACK = [0]
...
            if _TRANSPORT != "cascade" and _GPU_DOWN_UNTIL[0] <= time.time():
                got = _local(c, system, prompt, schema)
                if got is not None:
                    _FELL_BACK[0] += 1          # line 385
                    return got
            ...
            _FELL_BACK[0] += 1                  # line 402
```

`_ask_ungated` runs concurrently in up to `GATE_CLOUD_N` (16) worker threads. `_FELL_BACK[0] += 1`
is a load-increment-store on a plain shared list element with no lock, unlike `done` in `run()`
which is correctly protected by `lock`. Two threads incrementing at once can race and lose an
update (classic non-atomic RMW under the GIL, which only guarantees each bytecode op is atomic,
not the three-op sequence `LOAD/ADD/STORE`).

Consequence is limited to `_FELL_BACK[0]` under-reporting the "N to GPU" figure in the progress
line and (now, per finding #5) nowhere in the final summary either — a cosmetic accuracy issue,
not a data-correctness one, since it does not affect which chunks get cached or what feats are
kept.

Severity: **MINOR**. **VERIFIED**.

---

## 7. `read.py` — progress reporting is per-entity only; a deep-entity-only tail of the queue can go quiet

`read_entity()`'s chunk loop (`for title, ch in chunks: ... got = _ask(...)`) is strictly
sequential per entity — there is no progress line emitted from inside it. `work()`'s progress
print fires only when the *global* count of finished entities crosses a multiple of 5. The queue
is deliberately front-loaded and interleaved (`priority()`'s `WEAVE=4` weaving of one deep entity
against four light ones), which normally keeps completions frequent. But on a long run, once the
`no_page`/`thin`/light buckets are exhausted or already cached (a resumed run skips cached
entities near-instantly, so a second pass can burn through the easy tail fast and leave mostly
deep, uncached entities), a stretch of the queue can be dominated by entities whose own pages run
"three to twenty chunks at 10,000 characters" each, sequentially, with each chunk potentially
paying the full quick-attempt + backoff ladder (`CASCADE_TRIES=5`, `BACKOFF` up to 30s) before
falling to a possibly-benched GPU (up to a 360s local timeout). In that regime the run can go
silent — no new stdout line — for the full duration of however many such entities it takes to
next cross a multiple of 5 completions, which is exactly the shape the special-focus brief warns
looks like a stall to a foreman that SIGTERMs jobs for producing no output. This module is
deliberately outside the keeper's `STANDING` restart set, so a mis-timed SIGTERM here is not
auto-recovered for a long time.

I could not fully verify the actual stall-detection *window* foreman.py uses (that file is
outside this batch); the code fact above — no chunk-level progress, only every-5th-entity — is
directly verified. Whether it actually trips a SIGTERM in practice depends on that window versus
realistic per-chunk latency under a starved pool, which I did not measure live.

Severity: **MINOR** (code fact solid; real-world trigger condition unverified).
**VERIFIED** (the code shape) / **UNVERIFIED** (that it actually causes a foreman SIGTERM in
practice).

---

## 8. `read.py:639` — chunk-size heuristic in `read_entity()` can read `_CASCADE_OK` before it's resolved

```python
size = CLOUD_CHUNK if _CASCADE_OK else CHUNK
```

`_CASCADE_OK` starts as module-level `None` and is only set by `ensure_transport()`. `run()`
correctly calls `ensure_transport()` before the worker pool starts (line 1038), so the normal
`--run` path is fine. But the `--one HOST ENTITY` CLI path (`main()`, around line 1115-1116)
calls `read_entity(config(), a.one[0], a.one[1], cap_chunks=a.chunks)` directly, without ever
calling `ensure_transport()` first. At that point `_CASCADE_OK` is still `None` (falsy), so `size`
resolves to `CHUNK` regardless of which transport actually ends up serving the request (transport
routing itself is still correct inside `_ask`, which calls `ensure_transport()` internally — only
the *chunk-sizing* decision is made blind).

This is currently inert because `CLOUD_CHUNK = CHUNK` (both 10000, per the deliberate "the
measurement said no" decision documented at the top of the file) — so today the two branches
compute the same number. But the surrounding comment ("Sized for whichever transport will
actually carry it") is not true for the `--one` path as written, and if `CLOUD_CHUNK` is ever
changed back to a larger cloud-sized value (the file's own docstring discusses exactly that
trade-off), `--one` would silently under-size cloud calls with no error.

Severity: **MINOR** (zero current impact, latent once CLOUD_CHUNK diverges from CHUNK again).
**VERIFIED**.

---

## Clean

- `scale_theories.py` — no file I/O, no caps, no swallowed failures, no docstring/code
  contradictions found. Pure reference data and small physics helper functions; read in full,
  nothing to report.
- `thread_integrity.py` — read in full. The one place it does *not* wrap a shared-file read in
  try/except (`implied_threads()`'s `open(WEAVE_CANDIDATES.json)`) is a hard crash on a bad file
  rather than a swallow — the safer failure mode per this project's own stated priorities, not a
  defect. `classify()`'s DANGLING/RECIPROCAL/ASYMMETRIC logic was traced against its own
  docstring (including the 2026-08-24 m12 correction) and is internally consistent with the
  documented `recorded=None` (today) behavior.
- `identity.py` — `NEVER` set, `MIN_BEARERS`, `split()`, `node()`, `EPOCH_REQUIRED`,
  `epoch_directive()`, `epoch_acceptable()`: no additional issues found beyond findings 1-2 above.
- `worldseed.py` — `features()`/`_first()` seeded-fallback logic, `to_options()`,
  `build_all()`'s full-description regex scan (already fixed per its own 2026-08-24 comment, and
  re-verified here — no `[:200]` truncation remains): no additional issues found beyond finding 3.
- `wh40k.py` — `compute()`/`main()` ranking and printing logic: no additional issues found beyond
  finding 4. (Assay score judgments themselves are curatorial content, not code logic, and were
  not second-guessed.)
