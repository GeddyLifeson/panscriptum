# AUDIT — BATCH 05 (run29)

Modules: `src/cascade_bridge.py`, `src/generate.py`, `src/ingest_doc.py`, `src/tuning.py`,
`src/cleanup.py`, `src/repass_bands.py`

Every line of all six files was read. All six are heavily hardened by prior sweeps (extensive
in-code comments cite run #22-#28 findings), so this pass concentrated on what those passes had
not yet reached. Findings are reported per module, by lens category. Every finding not marked
REPRODUCED was reasoned from the code but not executed.

Reproduction scripts were written to `%TEMP%/pl_repro/` (this session's scratch temp dir) and
executed with the miniconda interpreter; none of them touch `src/`, `data/`, or `state/` — only
scratch copies. No file in `src/` was modified.

---

## src/cleanup.py

### FINDING C1 — `thin_description` flag is set in memory and never written to disk (SEVERITY: HIGH)
**File:line:** `src/cleanup.py:174-177`, inside `main()`'s per-record loop.
```python
if len(cd) < _THIN:
    thin.append((src, nm, cd))
    if args.apply:
        e["thin_description"] = True
```
Every other `if args.apply:` block in this function (nav removal :143-146, empty-mechanic
exclusion :154-157, ceiling fix :163-166, description markup fix :171-173) sets `changed = True`
immediately after mutating the record. This block is the only one of five that does not. `changed`
gates the write at the bottom of the loop:
```python
if changed:
    PL.write_record(path, rec)
```
So when a record's ONLY defect is one or more thin descriptions (no nav names, no ceiling prose,
no markup to strip), `changed` stays `False`, `write_record` is never called, and the
`thin_description` flag that was just set in memory is discarded when the loop moves to the next
record. The CLI still prints "APPLIED." and reports the entry under "descriptions too thin to
write from ... (marked, not deleted)" — the count is real (computed independent of the write
bug) but the persisted state is not: on disk, nothing changed at all.

This is a direct contradiction of the module's own docstring, item 4: "they are simply not
enough to write from, and they should be marked rather than silently carried as though they
were." The bug makes them silently carried exactly as though they were never marked.

**Consequence:** repeated `cleanup.py --apply` runs will re-detect and re-report the same thin
descriptions forever, and no downstream consumer of the catalogue (any code that checks
`entry.get("thin_description")`) will ever see the flag for a record whose only defect was this.

**Status: REPRODUCED.** Driver script monkeypatched `pipeline.records()` to yield one synthetic
record with a single thin-but-otherwise-clean entry, monkeypatched `pipeline.write_record` to
count calls, and ran `cleanup.main(["--apply"])`. Output: `write_record call count: 0` while the
in-memory entry showed `thin_description: True` and the CLI printed "4. descriptions too thin to
write from : 1 (marked, not deleted)" and "APPLIED." — i.e. the tool claims success while writing
nothing.

**Fix shape:** add `changed = True` inside the `if args.apply:` block at line 176-177, matching
the other four blocks.

---

### FINDING C2 — cleanup.py's per-entry edits are silently dropped by `pipeline.write_record`'s merge path under concurrent drift (SEVERITY: MEDIUM-HIGH, cross-module)
**File:line:** root cause is `src/pipeline.py:527-529` (outside this batch), but the entries it
drops are exactly the ones `cleanup.py` writes: `description` (`src/cleanup.py:172`), `excluded`
(`src/cleanup.py:156,165`), and `thin_description` (`src/cleanup.py:177`, see C1).

`write_record`'s docstring says it protects against a concurrent catalogue-growing writer by
merging instead of overwriting when the on-disk entry count has drifted since `cleanup.py` (or
any pipeline-side script) loaded its copy. But the merge only copies six named per-entry fields
from the in-memory copy onto the disk copy:
```python
for fld in ("category", "scale_note", "scale_note_rejected",
            "magnitude", "topic", "catalogued"):
    if fld in se:
        de[fld] = se[fld]
```
`description`, `excluded`, and `thin_description` are not in that list. So if a catalogue-growing
process (e.g. `ingest_doc.py --mine`, or a re-catalogue pass) touches the same record file while
`cleanup.py` is mid-run, `cleanup.py`'s markup-stripped description, its "wiki navigation, not an
entity of any fiction" / "rules construct with no description; not an entity" exclusion reasons,
and its thin-description marks are all silently lost — `write_record` still returns `True` (a
successful write), and the record's `catalogued=False` flag (which IS merged) survives without
the `excluded` reason that explains it.

**Status: REPRODUCED.** Driver script created a one-entry disk record, took an in-memory copy
with `description` changed to a cleaned string and `thin_description=True` added, then appended a
second entry directly to the disk file to simulate a concurrent writer (forcing the entry-count
drift `write_record` checks for), then called `PL.write_record(path, mem_rec)`. Result:
`write_record returned: True`; on disk, `description survived cleanup's edit? -> False`,
`thin_description flag survived? -> False`.

**Fix shape:** this is a pipeline.py fix (outside this batch's remit to edit), but from
`cleanup.py`'s side the finding is that `cleanup.py` cannot currently trust `write_record` to
preserve its own output under real-world concurrency with the catalogue side. Either the merge
allowlist in `pipeline.write_record` needs `description`, `excluded`, and `thin_description`
added, or `cleanup.py` needs to accept and act on `write_record`'s return value the way
`repass_bands.py` already does (see below — `repass_bands.py` at least reports write denial;
`cleanup.py` doesn't check the return value at all, see C3).

---

### FINDING C3 — `cleanup.py` ignores `write_record`'s return value entirely (SEVERITY: LOW, consistency gap)
**File:line:** `src/cleanup.py:179-180`
```python
if changed:
    PL.write_record(path, rec)
```
`repass_bands.py:84-87` (this same batch) explicitly checks the return value and prints
`WRITE DENIED ... left as it was` when the write is refused — with a comment explaining exactly
why that check matters (a run that silently discarded the return value once reported writes that
never landed). `cleanup.py` does not perform the same check, so a denied write (torn file, or a
failed merge inside `write_record`'s own exception handler) is invisible here in the same way
`repass_bands.py`'s comment describes having already been burned by. This does not lose data
beyond what C2 already describes, but it means an operator running `cleanup.py --apply` has no
way to know from its output whether any of the reported fixes actually landed on disk.
**Status: VERIFIED-BY-READING** (straightforward comparison against the sibling script in the
same batch that already fixed this exact gap).

---

### cleanup.py — other lenses
- **Correctness / regexes:** `_NAV`, `_MARKUP`, `_EMPTY_MECHANIC`, `clean_ceiling` were read
  closely and traced against their stated examples; all behave as documented (checked, not just
  read — traced `re.match` semantics for `_NAV`'s `characters?\b` anchor change, and the
  `min(low_pref, key=len)` prefix-resolution tie-break in `clean_ceiling`). No bug found.
- **HARD RULE 0:** the `[:70]`, `[:52]`, `[:46]`, `[:5]`/`[:6]`/`[:4]` slices in `main()`'s report
  section (lines 140, 142, 170, 186-201) are all **display truncation** of already-fully-computed
  lists (`nav`, `ceil_fixed`, `ceil_unres`, `desc_fixed`, `thin`) — every record is still
  processed and, modulo C1/C2 above, written. No data-truncation cap found.
- **Two-writer contract:** only writer used is `PL.write_record` — correct side for a pipeline-
  side per-entry-judgment script. No violation found (see C2 for a downstream problem with that
  writer, not a misuse of it).
- **Swallowed failures:** none found beyond C1/C2/C3.

---

## src/repass_bands.py

No new findings. This script has clearly already been through a hardening pass (its own docstring
at lines 79-83 documents a prior "write ignored return value" bug being fixed, matching the exact
class of bug found fresh in `cleanup.py` as C3 above). Checked specifically:
- The write-gate (`if PL.write_record(path, rec): touched.append(...) else: print(WRITE DENIED)`)
  is correct and matches the pattern `cleanup.py` should also have.
- `changed = True` is set on every mutating branch (source-level demotion, entry demotion,
  scale-note clearing) — no missing-flag bug of C1's shape here.
- Display truncations (`kept_entries[:14]`, `demoted_entries[:8]`) are report previews only; the
  full-count computations (`total_banded`, `by_band = collections.Counter(...)` over the whole
  `demoted_entries` list) are not sampled. No Hard Rule 0 violation.
- **Note:** `repass_bands.py` and `cleanup.py` both write the same record files via
  `PL.write_record`, so C2 (the merge-allowlist gap) applies to `repass_bands.py`'s own fields
  too in principle — but `magnitude`, `scale_note`, and `catalogued` (the three fields
  `repass_bands.py` mutates) ARE all in `write_record`'s merge allowlist, so `repass_bands.py`'s
  writes are NOT at risk from C2. This is `cleanup.py`-specific because `description`,
  `excluded`, and `thin_description` happen to be the fields left off the allowlist, and those
  are exactly what `cleanup.py`, not `repass_bands.py`, writes.

---

## src/tuning.py

No new correctness findings. This module is unusually self-aware — its own docstring documents
the exact HTTP-503/zero-score incident that motivated it, and the code visibly implements the
fixes it describes (workers-as-ceiling with 0-is-a-request handling at `workers()`:242-244;
regime re-read on `RECHECK_SECONDS` at `regime()`:194-196; `CLOUD_MIN_SUCCESS` gating cloud
classification on measured success rate, not just reachability, at `regime()`:203).
Checked specifically:
- `workers(requested=0)` returns `0`, not the profile count — traced the boolean logic; correct
  per the docstring's own claim ("Pinned by verify_math S19ac").
- `_ollama_host()` falls back to the same hardcoded literal used as the config default, so a
  broken config read never silently disagrees with the config-driven default elsewhere in the
  project — correct per its own reasoning.
- No caps, no truncation of any counted quantity.
- `profile()`'s `workers` override for the cloud regime (`max(4, min(16, n + 2))`) matches the
  comment above `PROFILES["cloud"]` describing the same formula.

---

## src/generate.py

No HIGH findings. Checked specifically and found correct:
- `_deed_shortfall` iterates every deed of every entity in the block — "Never a sample" per its
  own docstring, and the loop has no early exit or slice. Confirmed by reading: two nested `for`
  loops over `ents` and each entity's full `feats` list, no truncation.
- The chunked-write-and-verify logic in `generate_job` (`WRITE_CHUNK=8`) raises loudly
  (`RuntimeError`) rather than silently omitting entries when a block still lacks an entry after
  one retry — traced both the `entries` (chapter) and `feats` branches; both raise rather than
  return partial text. `missing[:8]` in the final error message (line 298) is a **display**
  truncation of the error string only — the full `missing` list drove the `if missing: raise`
  decision, and the message appends `(+{len(missing) - 8} more)` so the reader knows more exist.
- `pending[:3]` in `--dry-run` (line 352) and `pending[: args.limit]` (line 346) are both
  explicit, user-requested, disclosed truncations (dry-run preview says "showed 3 of N"; `--limit`
  is a documented CLI flag), not silent caps.
- Catalog/failures persistence is atomic (`silence.write_json` via `save_json`), and failures are
  saved immediately on each exception, not batched — no swallowed-failure gap found.

### FINDING G1 — `_covered()`'s retry-acceptance criterion silently prefers the ORIGINAL text over an equally-improved retry (SEVERITY: LOW, design nuance not a functional bug)
**File:line:** `src/generate.py:289-292` and the equivalent feats block at `:249-252`.
```python
if retry.strip() and len([e for e in g if not _covered(e.get("name", ""), retry)]) \
        < len(lacking):
    text = retry
    lacking = [e for e in g if not _covered(e.get("name", ""), text)]
```
The retry is only adopted if it covers **strictly more** entries than the original (`<`, not
`<=`). If a retry fixes a different entity but drops the one that was covered before (net
unchanged count), the code keeps the ORIGINAL text and the ORIGINAL `lacking` list — even though
the retry might have been objectively different, not worse. This cannot cause silent data loss
(the eventual `if missing: raise` still fires correctly either way, using the correct `lacking`
for whichever text was kept), so it's not filed as a correctness bug, just noted as a slightly
surprising tie-break. **Status: VERIFIED-BY-READING.**

---

## src/ingest_doc.py

### FINDING I1 — `mine()` crashes uncaught (`AttributeError`) if a cloud reply parses to a non-dict JSON value (SEVERITY: MEDIUM)
**File:line:** `src/ingest_doc.py:207`, consuming the return of `_ask()` (`:129-146`), which
calls `cascade_bridge.ask()`.
```python
got = _ask(SYSTEM, "PASSAGE (%s):\n\n%s" % (...), SCHEMA)
if got is None:
    ...  # napping/retry logic
    continue
misses = 0
fresh = []
for e in (got.get("entries") or []):   # <-- .get() assumes dict
```
`cascade_bridge._extract_json` (see cascade_bridge finding B1 below) can and does return a bare
JSON **list** when a cloud model wraps its answer in an array instead of the requested object
shape — nothing downstream validates the shape against `SCHEMA`. `cascade_bridge._ask_call` only
special-cases `dict` (adding `_via`) and returns whatever `_extract_json` produced otherwise, so
`ingest_doc._ask()` can hand `mine()` a list. `got.get("entries")` on a list raises
`AttributeError`, which is not caught anywhere in `mine()` or `main()`, so the whole `--mine` run
dies with a traceback instead of treating the chunk as a soft miss (the "napping 300s" path that
handles `got is None`). The resume cursor is not corrupted (nothing in this iteration reached the
`state["next"] = ci + 1` line), so the run is safely resumable — but it stops hard rather than
continuing past one malformed reply, which is a real availability/robustness gap given the module
runs unattended for hours against a rotating cloud pool the docstring itself describes as
occasionally producing exactly this kind of malformed reply.

**Status: REPRODUCED.** Fed `cascade_bridge._extract_json` a fenced bare-array reply
(`` ```json\n[{"name":"Someone"}]\n``` ``); it returned a `list`. Simulated `_ask_call`'s own
dict-only special-case (confirmed by reading `src/cascade_bridge.py:1108-1110`) — the list passes
through unchanged. Then called `.get("entries")` on it exactly as `mine()` does:
`AttributeError: 'list' object has no attribute 'get'`.

**Fix shape:** `mine()` (or `_ask()`) should treat a non-dict return the same as `got is None` —
a failed/unusable call that gets the same nap-and-retry treatment, not a crash.

---

### FINDING I2 — `description` is silently truncated to 2000 characters with no marker (SEVERITY: LOW)
**File:line:** `src/ingest_doc.py:216`
```python
"description": (e.get("description") or "").strip()[:2000],
```
Unlike `cleanup.py`'s `thin_description` flag (marking a defect rather than hiding it — see the
module's own stated philosophy: "they should be marked rather than silently carried as though
they were"), an over-length description from a cloud extraction is cut at 2000 characters with no
equivalent marker (no `description_truncated` flag, nothing in the merged entry that says this
happened). This is a per-field length cap rather than a Hard-Rule-0 universe-count cap (it does
not shrink the number of entities or the number of chunks mined — every chunk is still mined,
every entity still gets an entry), so it is filed at LOW severity rather than as a Hard Rule 0
violation proper. But it is the same shape of problem in miniature: a smaller version of the real
content, silently wearing the shape of the whole thing. **Status: VERIFIED-BY-READING.**

---

### FINDING I3 — fixed-name temp file for the resume cursor, inconsistent with this project's own established fix for the same bug class (SEVERITY: LOW, HYPOTHESIS)
**File:line:** `src/ingest_doc.py:256-259`
```python
tmp_state = state_p + ".tmp"
with open(tmp_state, "w", encoding="utf-8") as f:
    json.dump(state, f)
silence.replace_retry(tmp_state, state_p)
```
This correctly protects against a crash mid-write (the accompanying comment explains exactly
that), by writing to a temp file and doing an atomic rename via `silence.replace_retry`. But the
temp filename is fixed (`ingest_state.json.tmp`), not pid/thread-unique. `cascade_bridge.py`, in
this same batch, explicitly rejected this exact pattern for `record_unrecognised` (comment at
`src/cascade_bridge.py:517-524`): "`silence.write_json`, NOT a hand-rolled `path + '.tmp'`... The
pid+thread-unique name makes that unavailable to get wrong." `ingest_doc.py`'s `mine()` is
normally invoked once per source (one process, one thread, sequential while-loop — no
`ThreadPoolExecutor` anywhere in this file), so the realistic exposure is low: it would only
matter if two `--mine` invocations against the *same source* ran concurrently (e.g. an operator
or supervisor accidentally double-launching the same command), at which point both processes'
writes to the identical `ingest_state.json.tmp` could interleave before either renames.
**Status: HYPOTHESIS** — flagged for consistency with the project's own documented standard
(`silence.write_json`) rather than for a demonstrated concurrent-invocation scenario.

---

### ingest_doc.py — other lenses, no findings
- **Two-writer contract:** `mine()` correctly uses `P.write_record_catalogue` (the cast-growing
  side, matching the module's own extensive comment at :228-245 explaining why, citing the
  2026-08-23 incident where using `write_record` instead discarded 14 entities). `main()`'s
  provenance-note path correctly uses `P.write_record` instead (a single scalar field update, the
  pipeline side) at :293. Both choices are correct for what they do.
- **HARD RULE 0:** the chunk-and-mine loop (`while ci < len(chunks)`) processes every chunk;
  `misses >= 60` stops the run but does not skip or sample chunks — it stops at the CURRENT
  chunk and is resumable, matching the docstring. No universe-shrinking cap found.
- `extract()` reads `for i in range(len(doc))` — every page, no cap.

---

## src/cascade_bridge.py

### FINDING B1 — `dead_forever()`'s result is cached once per process and never refreshed, defeating its own purpose during a long run (SEVERITY: HIGH)
**File:line:** `src/cascade_bridge.py:282` (`_PROVEN = [None]`), `:311-326` (`dead_forever()`)
```python
def dead_forever():
    if _PROVEN[0] is not None:
        return _PROVEN[0]
    out = set()
    try:
        if time.time() - os.path.getmtime(PROOF) <= PROOF_TTL:
            ...
    except Exception:
        ...
    _PROVEN[0] = out
    return out
```
`PROOF_TTL = 3600` and the surrounding comments ("A proof this old is no longer evidence about
now... a bucket that was busy an hour ago is not a bucket that is broken") clearly establish the
intent that this function's answer should track the current state of `POOL_PROOF.json`, which is
periodically rewritten by `prove()` during a run (per `tuning.py`'s own comment: "`POOL_PROOF.json`
is written by `cascade_bridge.prove()`"). But `_PROVEN[0]` is memoized on the FIRST call and never
invalidated for the rest of the process's lifetime — there is no code path anywhere in the file
that resets `_PROVEN[0]` to `None`. `_alive(bucket)` (line ~654) calls `dead_forever()` on every
single claim, so this cache decides, for the entire life of a long-running process, whether
recently-proven-401/402/404/410 buckets are excluded.

Two concrete failure directions:
1. If `dead_forever()` happens to be called early while the proof file is missing or stale (>1h
   old — plausible at the very start of a multi-hour run, before the first `prove()` has run),
   the cache freezes at an EMPTY set. Any bucket that a later `prove()` call proves permanently
   dead (bad key, no balance, retired model) is never excluded for the rest of the run — the
   claim loop keeps trying it, wasting a claim and a deadline on every attempt, silently, for
   hours.
2. Conversely, if the cache freezes on a set of dead buckets early, and a human fixes the
   underlying account/key problem mid-run (plausible on an hours-long run), the bucket stays
   excluded regardless — though this direction is lower-cost (a fixed bucket sits idle rather
   than a broken one wasting claims).

**Status: REPRODUCED.** Pointed `CB.PROOF` at a scratch file. First call with bucket `x` reported
`"answers"` → `dead_forever()` returned `set()` (correct). Rewrote the same scratch file with
bucket `x` reporting `"HTTP 401"` (a should-be-permanent exclusion) and called `dead_forever()`
again in the same process: it still returned `set()` — the second, fresher, worse state was
completely invisible to the cache.

**Fix shape:** either re-check the proof file's mtime against a remembered "last loaded" mtime
and reload when it changes (matching the pattern `tuning.regime()` already uses correctly with
`RECHECK_SECONDS`), or drop the memoization and accept the cost of a stat+read per claim (the
file is small and local).

---

### FINDING B2 — module docstring claims schema validation that does not exist anywhere in the file (SEVERITY: MEDIUM)
**File:line:** docstring at `src/cascade_bridge.py:18-19`:
> "the schema is carried in the prompt and the reply is parsed and VALIDATED here. A reply that
> does not validate is a failure, not a result"

versus the actual implementation: `_extract_json` (`:104-134`) only finds and `json.loads()`s the
first parseable JSON blob in the reply; `_ask_call` (`:739-...`) passes `schema` into the prompt
text (`:862-865`, `json.dumps(schema)` embedded in the system message asking the model to match
it) but never checks the parsed result's shape, required keys, or types against that schema
anywhere before returning it to the caller. There is no `jsonschema` import, no manual
required-keys check, nothing. A syntactically-valid JSON object that satisfies none of the
schema's `required` fields is returned to the caller exactly as if it were correct — the only
thing that makes a call a "failure" here is unparseable JSON (`_extract_json` returning `None`),
which is a much weaker guarantee than "validated" as the docstring states it.

**Consequence for this batch specifically:** `ingest_doc.py`'s `SCHEMA` requires
`"required": ["entries"]`, but nothing enforces that; a reply missing the `entries` key parses
successfully as a dict, `got.get("entries")` returns `None` → `or []` → an empty list, and that
chunk is silently recorded as having found nothing — indistinguishable from a chunk that
genuinely contained no named entities. This is the exact failure mode `_extract_json`'s own
docstring warns against for the *unparseable* case ("never as an empty result -- an empty result
would silently read as 'this page has no feats'") but the guard only covers unparseable text, not
wrong-shaped-but-parseable text.

**Status: REPRODUCED.** Fed `_extract_json` a fenced reply
`{"totally_unrelated_field": 42, "no_entries_key": true}` against a schema requiring `entries`;
it returned the dict unchanged, `"entries" in got` is `False`, and nothing in the call chain
would have rejected it.

---

### FINDING B3 — `engine()` builds the shared Router/Engine with no lock, unlike its sibling `thread_engine()` (SEVERITY: LOW-MEDIUM)
**File:line:** `src/cascade_bridge.py:47-68` (`engine()`)
```python
def engine():
    global _ENGINE, _ROUTER
    if _ENGINE is not None:
        return _ENGINE
    if not available():
        return None
    ...
    _ROUTER = R.Router(cfg, st)
    _ENGINE = E.Engine(cfg, st, _ROUTER)
    ...
    _CFG["cfg"] = cfg
    return _ENGINE
```
This is a classic check-then-act race: no lock guards the gap between the `if _ENGINE is not
None:` check and the assignment. `thread_engine()` (`:75-92`) explicitly uses `_BUILD_LOCK` for
its own per-thread build and its docstring even explains why shared mutable engine state matters
here ("SQLite connections are not shareable across threads at all"). `engine()` itself has no
equivalent protection.

This is currently NOT exploited by every caller: `read.py`'s `ensure_transport()` and
`magnitude.py`'s `pool_ready()` both explicitly wrap their first call to `CB.engine()` in their
own lock/once-only guard, with comments describing having been burned by exactly this kind of
race before ("resolved once, before any worker starts"). But `chain.py`'s `_ask()` (line 270,
outside this batch) calls `CB.engine()` directly with **no** such guard, from inside `work()`,
which runs under a `ThreadPoolExecutor(max_workers=workers)` (`chain.py:367`) with no warm-up
call to `cascade_bridge.engine()` before the pool starts. If the first batch of chunks dispatches
before any single call to `engine()` has completed, multiple worker threads can each pass the
`if _ENGINE is not None:` guard simultaneously and each build their own `Store`/`Router`/`Engine`,
racing to leave the wrong one as the shared global — precisely the failure mode `thread_engine()`
was written to avoid for its own layer.

**Status: VERIFIED-BY-READING**, with the race pattern itself independently confirmed: a
structurally faithful replica of `engine()`'s exact guard-then-build-then-assign shape (same
control flow, an injected delay standing in for the real Router/Engine construction cost) was run
with 8 concurrent first-callers; the "expensive build" step executed 8 times instead of once, and
8 distinct objects were handed back to the 8 callers. This was not run against the real Cascade
package to avoid touching live provider/router state; it demonstrates that the pattern in
`engine()` is racy, which — given `chain.py` calls it exactly this way with no external
serialization — makes this a real, currently-reachable gap, not just a theoretical one.

**Fix shape:** wrap `engine()`'s body in a lock (e.g. reuse `_BUILD_LOCK`), matching
`thread_engine()`.

---

### cascade_bridge.py — other lenses, no findings
- **HARD RULE 0:** every `[:N]` slice in the file (grep'd exhaustively — lines 478, 503, 514, 882,
  895, 1061, 1072) is either an error-message length cap (300/80 chars, for ledger/log storage,
  not a count of buckets or calls) or, in `selftest()`, a manual diagnostic CLI preview
  (`ready[:12]`, `[:400]` on a pretty-printed dict) — never a cap on the actual claim/route/proof
  loop, which iterates every model and every bucket unconditionally (`prove()`'s
  `for bucket, m in sorted(seen.items())`, `try_disabled()`'s `for m in _ROUTER.models`). No
  violation found.
- **Two-writer contract:** N/A — this file writes only its own diagnostic/ledger state
  (`UNRECOGNISED`, `_METRICS`, `PROOF` is read-only here), never a `data/records/*.json` file.
  `record_unrecognised`'s write correctly uses `silence.write_json` with a threading lock for
  in-process ordering and relies on `silence.write_json`'s own pid+thread-unique temp naming for
  cross-process safety — this is the pattern the project's own comments hold up as correct, and
  it is followed correctly here.
- **Swallowed failures:** extensively and deliberately engineered (the whole
  `_TRANSIENT_WORDS`/`_MULTI_CANDIDATE`/`provider_error`/`record_unrecognised` apparatus exists
  specifically to stop failures from being swallowed); read closely and found internally
  consistent with its own stated design across several iterations of self-correction visible in
  the comments. No new gap found beyond B1/B2/B3 above.
- **Comments vs. code:** the "THERE IS NO PAID LANE" section (`:210-230`) was checked against the
  rest of the file — confirmed no `paid`/`burst`/cap-counter code exists anywhere in the file,
  consistent with the comment's claim.

---

## Summary table

| # | Module | Severity | Status |
|---|--------|----------|--------|
| C1 | cleanup.py:174-177 | HIGH | REPRODUCED |
| B1 | cascade_bridge.py:282,311-326 | HIGH | REPRODUCED |
| C2 | cleanup.py writes / pipeline.py:527-529 merge | MEDIUM-HIGH | REPRODUCED |
| B2 | cascade_bridge.py:18-19 vs. actual code | MEDIUM | REPRODUCED |
| I1 | ingest_doc.py:207 | MEDIUM | REPRODUCED |
| B3 | cascade_bridge.py:47-68 | LOW-MEDIUM | VERIFIED-BY-READING (+pattern repro) |
| C3 | cleanup.py:179-180 | LOW | VERIFIED-BY-READING |
| I2 | ingest_doc.py:216 | LOW | VERIFIED-BY-READING |
| I3 | ingest_doc.py:256-259 | LOW | HYPOTHESIS |
| G1 | generate.py:289-292 | LOW (not a bug) | VERIFIED-BY-READING |

`tuning.py` and `repass_bands.py`: no findings of any severity. Both read as clean and
consistent with their own stated design.
