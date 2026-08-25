# Batch 12 audit — run29

Modules: `overnight.py`, `weave.py`, `onomast.py`, `scout.py`, `grounding.py`,
`recover_folder_records.py`, `compress_store.py`

Every line of every module was read. Findings below are grouped by module, then by lens
category. Each finding states file:line, what the code does, what it claims/implies, the
consequence, and whether it is REPRODUCED, VERIFIED-BY-READING, or HYPOTHESIS.

---

## overnight.py

### [HIGH] 1. Correctness bug / swallowed failure — `coverage_snapshot()` ignores the subprocess return code, so a crashed measurement is reported as a clean one

**`overnight.py:461-469`**

```python
def coverage_snapshot():
    try:
        subprocess.run([PY, os.path.join(SRC, "coverage.py")], cwd=HERE,
                       capture_output=True, text=True, timeout=1800,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"), creationflags=_NO_WIN)
        rows = json.load(open(os.path.join(HERE, "data", "COVERAGE.json"), encoding="utf-8"))
    except Exception as e:
        silence.note("overnight.py:124")
        return {"error": f"{type(e).__name__} {str(e)[:60]}"}
```

`subprocess.run(...)`'s return value (a `CompletedProcess`, carrying `.returncode` and the
captured stdout/stderr) is never assigned to anything — `capture_output=True` is set and then
thrown away. The function then unconditionally opens `data/COVERAGE.json` and treats whatever
is there as this cycle's fresh measurement. If `coverage.py` crashes, hangs past nothing (it
would raise `TimeoutExpired`, which IS caught), or exits nonzero while still leaving the
previous cycle's `COVERAGE.json` on disk untouched, this function returns that **stale** data
with no `"error"` key and no indication anything went wrong.

This directly defeats the module's own stated purpose ("MEASURE EVERY CYCLE... so the morning
question is answered by a file rather than an archaeology session", lines 27-28) and its own
already-partially-applied fix at `main()` (lines 721-729), which only prints "SNAPSHOT FAILED"
when `snap.get("error")` is truthy — a condition this code path never sets for a nonzero exit.
The stale/failed cycle is written into `history` and `STATUS.md` indistinguishably from a real
measurement, every cycle, for as long as `coverage.py` keeps failing.

**REPRODUCED.** Driver script at
`…/scratchpad/test_coverage_snapshot.py` reproduces `coverage_snapshot()`'s exact logic
against a stub `coverage.py` that `sys.exit(1)`s immediately, with a stale `data/COVERAGE.json`
left from a prior "success" on disk. Output:

```
overnight.coverage_snapshot() returned: {'entries': 100, 'cited': 90, 'read': 5, 'feats': 3, 'cited_pct': 90.0}
```

No `"error"` key — the crash is completely invisible to the caller.

**Fix direction:** capture the `CompletedProcess`, check `.returncode != 0` (and/or compare
`COVERAGE.json`'s mtime against the subprocess start time) and return an `"error"` dict in that
case rather than falling through to stale data.

---

### [HIGH] 2. Correctness bug — `running()`'s basename-match clause is dead code; the effective test is a bare substring match over the whole command line, reintroducing the exact false-positive class the file's own docstrings say was fixed

**`overnight.py:145`** (inside `running()`, used by both `run()` and `start()` as the
"already running, don't duplicate" singleton guard):

```python
if fragment in cmd.replace("\\", "/").split("/")[-1] or fragment in cmd:
    return True
```

`cmd.replace("\\","/").split("/")[-1]` is, by construction, always a **substring of `cmd`
itself** (it's the tail segment after the last separator). Therefore `fragment in <tail>`
*implies* `fragment in cmd` in every case — the first clause can never be true while the second
is false. The `or` is dead weight: the whole expression reduces to `fragment in cmd`, i.e. a
bare substring test over the **entire command line**, including every argument.

That is precisely the failure class `run()`'s own comment at lines 163-166 says this code
exists to prevent ("Matched on BASENAME... a substring test on the full path never matches...
That is how a second roll got launched against a live one") and the class the module-level
docstring (lines 92-100) discusses at length for the self-pid case. As written, any OTHER
process whose command line happens to *mention* a stage's filename anywhere — as a log path,
a `--deny`/`--exclude` argument, part of a longer filename, etc. — will make `running()` report
that stage as already active. Concretely: `run()`/`start()` would then skip launching that
stage ("already running, left alone") indefinitely, which is exactly the silent-degradation
failure mode the module's own philosophy section calls out ("duplicates do not fail, they
degrade everything quietly and look like slowness" — except this is the inverse: a stage that
should run, never does, and looks the same as a healthy "someone else has it").

**REPRODUCED** (the redundancy itself, and the resulting false positive). Driver script at
`…/scratchpad/test_running_match.py`:
- Constructs `fragment="read.py"` against `cmd = '...foreman.py --deny read.py --loop 30'`
  (an unrelated process whose argument merely mentions `read.py`) → `running()`'s predicate
  evaluates `True`, misreporting `foreman.py` as `read.py` being active.
- 20,000 randomized trials confirm clause A (`fragment in tail`) is *never* true while
  clause B (`fragment in cmd`) is false — i.e. clause A is provably inert and the check is
  just `fragment in cmd`.

**Fix direction:** the basename check should be `fragment == cmd.replace("\\","/").split("/")[0's first token's basename]` — i.e. extract the executed script path (the token *after* the interpreter) from `cmd`, take its basename, and compare that for exact equality against `fragment`, not `in`.

---

### [LOW] 3. Concurrency — benign but real lock-creation race in `_proc_lines()`

**`overnight.py:61-88`**

```python
_PROCS_LOCK = None
def _proc_lines(ttl=3.0):
    global _PROCS_LOCK
    if _PROCS_LOCK is None:
        import threading
        _PROCS_LOCK = threading.Lock()
    with _PROCS_LOCK:
        ...
```

The lazy lock creation is itself unguarded. `overnight.py`'s `main()` starts two daemon threads
(`_keep`, `_keep_warm`) plus the main thread, all of which can reach `_proc_lines()` /
`running()`. If two threads race the `if _PROCS_LOCK is None` check before either assignment
completes, both may construct separate `Lock` objects, and the loser's lock discards the
winner's — defeating the mutual exclusion the code exists to provide, letting two threads
mutate `_PROCS["out"]`/`_PROCS["at"]` concurrently. The window is a few bytecode ops wide and
this is a **threading** (not process) race confined to one Python process, so real-world impact
is low, but it is exactly the "lazy-init shared lock" anti-pattern. VERIFIED-BY-READING, not
reproduced (the window is too narrow to force reliably without instrumentation, and the
consequence — a stale process table read once — is minor). **Fix direction:** create the Lock
at module import time instead of lazily.

---

No further findings in `overnight.py`. The rest of the file (job start/join/tail, `name_rc`,
`foreman_report`, `watch_report`, `ledger_report`, `preflight`, `write_status`, the keeper/
keep-warm threads, `main()`'s cycle loop) reads correctly against its own stated intent, and the
append-vs-truncate log fixes, timeout handling, and `already-running`-is-not-idle distinction
are all sound.

---

## weave.py

### [MEDIUM] 4. Swallowed failure — `filtered_index()`'s `except Exception` around the `pipeline` import silently disables one of two mechanics filters on ANY import-time exception, not just a missing module

**`weave.py:186-191`**

```python
try:
    from pipeline import _STATBLOCK
except Exception:
    silence.note("weave.py:187")
    _STATBLOCK = None
```

`filtered_index()` is the gate that drops "mechanics" (stat blocks, rules text) from the entity
index before any cross-source continuity math runs — the module's own comment two lines below
frames this as necessary because the name-regex approach alone under-filters ("caught 'Channel
Divinity' and missed 'Ability Score Improvement'... which then ranked among the strongest
cross-source fusions"). But the `except Exception` here catches not just `ImportError` (module
genuinely absent) — it catches a syntax error in `pipeline.py`, a circular-import failure, or
any exception `pipeline.py`'s own module-level code raises during import (this repo has an
automated code-patcher, `foreman.py --patch`, that rewrites modules unattended). Any of those
degrades weave.py to running with the `_STATBLOCK` gate permanently off for that entire run,
letting stat-block text back into the entity-resolution corpus — silently, and in the same
output shape as a correctly-filtered run (a smaller effective universe of exclusions, wearing
the same shape as the real one). It is recorded to the silence ledger, so it is not fully
invisible, but nothing in `weave.py`'s own console output or written artifacts signals the
degraded mode.

**VERIFIED-BY-READING.** **Fix direction:** narrow the except to `ImportError`, or check that
the pipeline module actually contains `_STATBLOCK` and log at `log`/print level (not just the
silence ledger) when it doesn't, since this changes the semantics of the whole run.

No caps, no two-writer violations, and no other bugs found in `weave.py`. The module has
already been through at least one prior audit pass (the "NO CAP" comments at lines 170-172 and
217-225, and the atomic-write fix noted at lines 469-474) and those fixes are real and correct
as written — `main()`'s `--write` path uses `silence.write_json` for all three outputs, and the
`shared[p].append(k)` lists in both `pair_weights()` and `surprisal_pair_weights()` are
genuinely uncapped. `components()`'s complete-linkage clustering and `resonance_graph()`'s BFS
diameter computation are both correct against their stated intent.

---

## onomast.py

No correctness bugs, swallowed failures, hard-rule-0 violations, or two-writer violations
found. Specific things checked and cleared:

- `coin_well_formed()`'s fallback ladder (lines 238-265) is the documented, already-fixed
  version — it now checks both `well_formed()` and `taken` at every fallback tier, and only the
  final, genuinely-exhausted-namespace path (after 10,000 deterministic candidates) can return
  an unchecked name, and that path is loud (`silence.note("onomast.py:coin-exhausted")`). This
  is an acknowledged, documented last resort, not a hidden bug.
- `main()`'s console prints truncate for display only (`by_endonym[...][:4]`, `rows[:9]` at
  lines 389/392) — the actual write to `ONOMASTICON.json` (line 399) uses the full `named` dict,
  uncapped. Correctly DISPLAY, not DATA, truncation.
- `register_for()`'s genre/feature voting and tie-break logic (lines 311-334) is deterministic
  and internally consistent with its own documented weights (3 vs 2).
- The write at line 399 uses `silence.write_json`, compliant with the shared-state-write
  contract.

---

## scout.py

### [MEDIUM] 5. Hard Rule 0 — `PROBE_NAMES = 25` caps the pool of catalogued names used to VERIFY a candidate page, biasing rejection against large/well-documented sources

**`scout.py:78` (constant), used at `scout.py:176`:**

```python
PROBE_NAMES = 25
...
sample = [n for n in names if n and len(n) > 3][:PROBE_NAMES]
```

`sample` is used for two things: (a) the first 18 of it go into the LLM prompt (reasonable —
prompt-length economy, and the model only needs a taste of what's catalogued), and (b) **the
full 25-item `sample` is the only pool `verify()` checks a fetched candidate page against**
(`scout.py:193`, `verify(u, sample)` → `_names_in(text, sample)` at `scout.py:169`). For a
source with more than 25 catalogued entities, `sample` is the first 25 items of `names` in
whatever order the record stores them (`hostless()` at `scout.py:230-233` builds `names` from
`r["entries"]` in stored order — not ranked by anything). A real, on-topic page about that
source that happens to cover a slice of entries outside the first 25 (an index page split
alphabetically past "C", a "recent additions" page, a wiki category page for a different
letter/arc) scores zero or near-zero against the capped sample and is marked `"ok": False,
"why": "N catalogued name(s) present"` with N below `MIN_NAME_HITS` — indistinguishable from a
page that is genuinely about something else. This is the same shape of error Hard Rule 0's own
examples describe: a cap on a roster, applied silently, that decides on the source's behalf
that everything past the cutoff does not count as evidence.

**REPRODUCED.** Driver script at `…/scratchpad/test_scout_probe_cap.py` builds a 200-name
synthetic source and a genuine page covering entries #100-#160 (nowhere near the first 25):

```
Genuine page about this source, but covering entries #100-#160, scores against the
first-25 sample: hits = 0 (MIN_NAME_HITS = 2)
-> verify() would mark this real, on-topic page REJECTED as 'about something else'.
Same page scored against the FULL 200-name catalogue instead: hits = 61
```

The consequence is concrete and matches the module's own stated purpose: `scout.py` exists
specifically to find hosts for large, currently-hostless sources (`sweep()` sorts candidates by
`-len(todo[s])`, i.e. **largest sources first**, `scout.py:239`) — so the cap bites hardest on
exactly the sources the module is prioritizing. A source can keep coming back "hostless" cycle
after cycle even after a correct URL was proposed and fetched, because verification checked it
against an arbitrary 25-name slice of a much larger catalogue.

Note this is a DATA-decision truncation (it gates what gets registered/written via
`EP.register()` and `_land(F.HOSTS, ...)`), not merely a display truncation — the already-fixed
`urls` cap removal (documented at `scout.py:181-186`, "Uncapped 2026-08-24") addressed the
model-proposal side of this same pipeline but left the verification-pool side capped.

**Fix direction:** verify against the full `names` list (or a much larger/representative
sample chosen by more than list order — e.g. don't drop entries past position 25, since the
fetch-and-check cost is what's already been paid for the page; only the string comparison
pool needs to grow, which is cheap).

No two-writer or concurrency violations found — `_land()` (lines 55-65) correctly uses
tmp-file + `silence.replace_retry`, matching the shared-state-write contract, for `SCOUT.json`,
`SCOUT_BLOCKED.json`, and (indirectly, via `F.HOSTS`) the hosts map.

---

## grounding.py

### [HIGH] 6. Correctness bug / Hard-Rule-0-shaped cap — `classify_text(text, top=3)`'s default silently drops 2 of the 5 possible grounding types from the confidence denominator, inflating the stored `"confidence"` field

**`grounding.py:112-117`, called from `classify_source` at `grounding.py:162`:**

```python
def classify_text(text, top=3):
    scores = collections.Counter()
    for name, spec in GROUNDINGS.items():
        for pat, wt in spec["cues"].items():
            scores[name] += wt * len(re.findall(pat, text, re.I))
    return scores.most_common(top)
```

```python
ranked = classify_text(" ".join(parts))            # top defaults to 3
...
total = sum(s for _, s in ranked) or 1
...
"confidence": round(score / total, 3),
```

There are exactly 5 grounding types in `GROUNDINGS` (`ex_nihilo`, `emanation`,
`eternal_cycle`, `demiurgic`, `immanent`). `classify_text`'s default `top=3` means
`classify_source` always discards the two lowest-scoring types before computing `total` — so
`confidence = score / total` is computed against a **truncated** denominator whenever 4 or 5 of
the 5 types register any nonzero score, which is exactly the "contested cosmogony" case the
module cares most about getting right (`main()`'s own `low = [...]` filter at line 228 exists
specifically to surface sources where "two accounts run close"). The dropped mass makes
`total` smaller than the true sum, which makes every reported `confidence` an *overestimate* —
the module is least accurate exactly where it claims to be flagging uncertainty. This
`"confidence"` value is written verbatim into `data/GROUNDINGS.json` via `silence.write_json`
at `grounding.py:239` — it is stored data, not a print-only value.

This is the same shape of bug the module's own docstring at lines 128-141 describes fixing for
the *entries* cap ("the record understated its own attestation 33-fold on the very field a
reader would use to judge how well-founded the claim is") — but that fix addressed the
entry-reading cap and missed this separate, smaller cap living one level down in the scoring
helper.

**REPRODUCED.** Driver script at `…/scratchpad/test_grounding.py` constructs text hitting cues
from 4 of the 5 grounding types with distinct weights:

```
FULL (top=5):      [('emanation', 20), ('ex_nihilo', 13), ('eternal_cycle', 12), ('demiurgic', 8), ('immanent', 0)]
TRUNCATED (top=3, the default used by classify_source): [('emanation', 20), ('ex_nihilo', 13), ('eternal_cycle', 12)]
confidence if computed on FULL total: 0.377
confidence if computed on TRUNCATED total (what classify_source actually does): 0.444
```

An ~18% relative inflation in this example; the effect scales with how many types register
real cue hits, which for genuinely-contested/syncretic cosmogonies (the case the code is trying
hardest to catch) is precisely when it's largest. A source whose true confidence is, say, 0.48
(below the `< 0.5` "contested" cutoff at line 229) can be pushed above 0.5 by this truncation
and silently dropped from the `low`/"contested cosmogonies" report — the exact opposite of
what that report is for.

**Fix direction:** either call `classify_text(text, top=len(GROUNDINGS))` (i.e. don't truncate
at all — there are only 5 possible types, keeping all of them costs nothing) from
`classify_source`, or compute `total` from the full `Counter` before truncating for display/
`runners_up` purposes.

No other findings in `grounding.py`. The `cap` parameter's hard refusal (lines 143-147) is
already the fixed, correct version of the entries-cap bug the docstring describes, and
`classify_source`'s own entry-scan loop (lines 153-159) is genuinely uncapped.

---

## recover_folder_records.py

Per instructions, the known finding (the "ATOMIC" comment at lines 145-157 covering only the
per-record write while the read→full-scan→write clobber window over `SWEEP_ROLL.json` stays
open across the whole loop, and writing records via `silence.write_json` directly rather than
`pipeline.write_record_catalogue`) is not re-derived here. One adjacent issue found nearby:

### [LOW] 7. The in-memory `roll` mutations are batched to a single write at the very end of the loop, so a mid-loop crash silently loses already-applied roll bookkeeping for sources whose record files were already written successfully

**`recover_folder_records.py:98-164`**

For each `name` in `empty`, the loop writes the record file first (gated correctly on
`silence.write_json`'s return value, per the already-fixed "GATE ON THE WRITE" comment at
lines 149-154), then updates `roll_entry["entry_count"]`/`["status"]` **in the in-memory `roll`
list** (lines 158-159) — but `SWEEP_ROLL.json` itself is only written once, after the entire
`for name in empty` loop finishes (line 162-164: `if not args.dry_run and written:
silence.write_json(ROLL, roll, ...)`). If the process is killed, crashes on an unexpected
record shape, or is interrupted partway through a long `empty` list (100 sources is exactly the
scale this script targets, per its own docstring), every record file written before the crash
is correctly on disk with real entries — but `SWEEP_ROLL.json` never learns about any of them,
because the single terminal write never runs. Because work-selection is
`entry_count == 0` (line 94), a re-run will re-process and re-write those same already-fixed
sources (harmless — the record content is deterministic from `LOCAL_REGISTER.json` +
`FOLDER_SOURCE_MAP.json`, so this is self-healing rather than corrupting), but it means the
"Wrote N records" accounting from a crashed run is misleading, and a monitoring process reading
`SWEEP_ROLL.json` between the crash and the next successful re-run would see 100
still-`entry_count: 0` sources when some already have real, correct record files on disk. This
is the mirror image of the already-fixed "phantom record" bug (run #25): that one made the roll
falsely claim success; this one can make the roll falsely deny already-real success.

VERIFIED-BY-READING (not reproduced — would require killing the process mid-loop against real
`LOCAL_REGISTER.json`/`FOLDER_SOURCE_MAP.json` data, which the audit scope doesn't warrant
given the low severity/self-healing nature). **Fix direction:** write `ROLL` incrementally
(e.g. every N sources, or immediately after each successful record write) rather than only
once at the end — same rationale as the per-record atomicity fix already applied.

---

## compress_store.py

### [LOW] 8. `store()` writes the compressed blob directly, not via the project's established atomic-write pattern (tmp file + `silence.replace_retry`)

**`compress_store.py:43-44`:**

```python
with open(path, "wb") as f:
    f.write(blob)
```

Every other shared-artifact writer in this batch (`overnight.py`'s log files — append-only, not
this pattern's concern; `weave.py`, `onomast.py`, `grounding.py`, `scout.py`'s `_land()`) uses
tmp-file-then-`silence.replace_retry`/`silence.write_json` specifically because a bare
`open(path, "w"/"wb")` truncates the destination before the write completes, so a reader or a
crash mid-write can observe a zero-byte or partially-written file at a path other code treats
as present-and-valid. `compress_store.store()` does exactly the bare-open pattern this project
has repeatedly had to fix elsewhere (see `scout.py:56-61`'s own comment describing this exact
failure mode for `WIKI_HOSTS.json`).

The blast radius here is smaller than a typical shared-JSON case: the path is content-addressed
by `content_hash()` (`compress_store.py:20-21`), `generate.py` is the only writer found in this
codebase (`grep` across `src/` — used only by `generate.py:386`), and `catalog.py`'s reads
(`catalog.py:97`) go through paths already recorded in a catalog/manifest that itself should
only be updated after `store()` returns successfully — so a live concurrent-reader race
requires unusual timing. But a **process kill or crash mid-write** (Windows box, per this
project's own recurring failure history with orphaned/killed processes — see the Ollama VRAM
note and `overnight.py`'s extensive foreman-kill machinery) leaves a permanently corrupt file
at a valid-looking, content-hash-named path. `load()` (`compress_store.py:55-65`) has no
integrity check against `content_hash()` on read, so a corrupt blob is only discovered when
`gzip.decompress`/`zstd` decompression itself raises — an exception a caller may or may not be
expecting at that call site (not traced further in this batch, since `catalog.py` and
`generate.py` are outside the assigned module list).

VERIFIED-BY-READING / HYPOTHESIS for the crash-corruption scenario specifically (not
reproduced — would require killing the process at the exact `f.write(blob)` instant).
**Fix direction:** write to `path + ".tmp"` then `silence.replace_retry(tmp, path)`, matching
every other shared-artifact writer in this codebase.

No other findings — `content_hash()`'s use of a 32-hex-char (128-bit) SHA-256 truncation is not
a meaningful collision risk at this corpus's scale, and the zstd/gzip fallback logic is sound
and loud (`silence.note` on missing `zstandard`, `RuntimeError` on trying to decode `.zst`
without it installed).

---

## Summary table

| # | Severity | File:line | Status |
|---|----------|-----------|--------|
| 1 | HIGH | overnight.py:461-469 | REPRODUCED |
| 2 | HIGH | overnight.py:145 | REPRODUCED |
| 6 | HIGH | grounding.py:112-117, 162 | REPRODUCED |
| 5 | MEDIUM | scout.py:78, 176, 193 | REPRODUCED |
| 4 | MEDIUM | weave.py:186-191 | VERIFIED-BY-READING |
| 3 | LOW | overnight.py:61-88 | VERIFIED-BY-READING |
| 7 | LOW | recover_folder_records.py:98-164 | VERIFIED-BY-READING |
| 8 | LOW | compress_store.py:43-44 | VERIFIED-BY-READING / HYPOTHESIS |

`onomast.py`: no findings.

Reproduction scripts used, left in scratch space (not part of the repo):
- `test_coverage_snapshot.py`
- `test_running_match.py`
- `test_scout_probe_cap.py`
- `test_grounding.py`
all under `C:\Users\imarl\AppData\Local\Temp\claude\C--\6506ea5e-fab3-47bb-9894-93c3e97a3ee0\scratchpad\`.
