# Batch 09 audit — hostcheck.py, manifest_builder.py, pick_model.py, feats_index.py, propagation.py, retry_synthesis.py

Files read: all six, every line, in full (hostcheck.py 956 lines, manifest_builder.py 479
lines, pick_model.py 358 lines, feats_index.py 264 lines, propagation.py 215 lines,
retry_synthesis.py 153 lines). Also read `src/endpoint.py` (371 lines) and `src/silence.py`
(426 lines) in full as supporting context since hostcheck.py, retry_synthesis.py and
manifest_builder.py all depend on their contracts. Also ran live verification against the
real `data/WIKI_HOSTS.json` and `data/readfeats/` on disk (read-only) and grepped for
non-atomic write patterns across the batch.

---

## 1. feats_index.py:148 — hyphenated hosts silently mis-mapped back from directory names

```python
host = host_dir.replace("_", ".").lower()
```

`load_index()` reconstructs a hostname from a `readfeats/` directory name by turning every
underscore back into a dot. But the directory name was produced elsewhere (see
`hostcheck.py:710`, `re.sub(r"[^A-Za-z0-9]+", "_", host)`) by turning **every** non-alphanumeric
character — both `.` and `-` — into `_`. That transform is not invertible: `date-a-live.fandom.com`
and a hypothetical `date.a.live.fandom.com` both become `date_a_live_fandom_com`, and
`.replace("_", ".")` always picks the dot reading.

**Live-verified** (ran against the real files on disk, read-only):

- `data/WIKI_HOSTS.json` binds `"Date A Live": "date-a-live.fandom.com"` (also confirmed for
  Sakamoto Days, The Amazing Digital Circus, Uncle Grandpa — all four hyphenated).
- `data/readfeats/date_a_live_fandom_com/` holds 4 real feats files (Kurumi Tokisaki, Origami
  Tobiichi, Shido Itsuka, Tohka Yatogami).
- `load_index()` on that directory produces the key `date.a.live.fandom.com` — confirmed by
  direct call.
- `host_to_sources()` (built straight from WIKI_HOSTS.json) has the key
  `date-a-live.fandom.com` → `["Date A Live"]`.
- In `feats_for_source()`, the match loop is `if h != host: continue`, comparing
  `date.a.live.fandom.com` (from the index) against `date-a-live.fandom.com` (from
  `host_to_sources`, used to build the `hosts` list to search). They never match. All four
  entities' feats — and the whole of Date A Live, Sakamoto Days, The Amazing Digital Circus and
  Uncle Grandpa's mined feats — are unreachable by any volume.

**The module's own docstring is wrong about the diagnosis.** Lines 36–38 claim:

> "14 records / 222 feats are hosts with no `WIKI_HOSTS` entry at all (the amazing digital
> circus, date a live, sakamoto days, uncle grandpa) ... A gap in that file rather than in this
> join, and binding those four hosts fixes them."

All four hosts **are** bound in WIKI_HOSTS.json (verified above), under their correct
hyphenated hostnames. Binding them again would do nothing — the stranding is caused entirely by
the lossy `_` round-trip in `load_index()`, i.e. it is a gap in *this join*, exactly the
category the docstring says it isn't. `audit()`'s "known host" vs "NOT IN WIKI_HOSTS" label
(line 257) would also misreport these as "NOT IN WIKI_HOSTS" for the same reason, since it
performs the identical `host_to_sources()` lookup against the mangled key.

**Fix direction** (not applied — audit only): `_norm`-style folding should be applied
consistently on both sides of the comparison (normalize the WIKI_HOSTS hostname the same lossy
way before comparing), or the directory-naming scheme in `hostcheck.py` should preserve `-` as
`-` and only fold other separators, so the round-trip is actually invertible.

Severity: **MAJOR**. Status: **VERIFIED** (live-verified against real data on disk).

---

## 2. retry_synthesis.py:60 — sampling method contradicts its own "byte-identical" claim, plus a Hard Rule 0 cap

```python
def synthesise(c, rec):
    """Byte-identical prompt construction to phase_synthesis, so a retried source is not
    scored by a different method than its neighbours."""
    src = rec["source"]
    sample = sorted(rec["entries"], key=lambda e: -len(e.get("description", "")))[:14]
```

Compared directly against `pipeline.py`'s real `phase_synthesis` (`src/pipeline.py:621` on),
which:

- Loads mined feats per entity (`_mined_feats(rec)`).
- Ranks entities with feats first, longest feat text first, and **every** feat-bearing entity is
  put into a chunk of 14 — `chunks = [with_feats[i:i+14] for i in range(0, len(with_feats), 14)]`
  — i.e. it paginates across as many calls as needed and takes the best band across all chunks.
- Only falls back to `sorted(..., key=lambda e: -len(description))[:14]` (a single, single-slice
  chunk) when there are **no** feat-bearing entities at all — and the surrounding comment
  explicitly names this exact bug: "The fixed sample-of-14 could silently clamp a whole source to
  a lesser ceiling whenever the true strongest entity ranked fifteenth by feat-count... BUGS m13,
  Hard-Rule-0-shaped, ruled by the owner 2026-08-24: FIX IT ALL."

`retry_synthesis.synthesise()` never consults feats at all. It **always** sorts by raw
description length and takes exactly one slice of 14, unconditionally — precisely the
already-diagnosed-and-fixed-elsewhere bug, reintroduced in this one retry path. Its docstring
calling this "byte-identical to phase_synthesis" is false: the two methods produce different
rankings whenever a source has feat-bearing entities that are not also its longest-description
entities (the exact scenario `pipeline.py`'s own comment says caused wrong ceilings before), and
`phase_synthesis` never truncates a feat-bearing pool to 14 while this always does.

This affects "Twelve sources -- Dragon Ball Z and Dune among them" per this file's own module
docstring (line 5) — sources that failed during a memory-thrashing window and are retried
through this exact, silently-different, capped path. Once merged via `--merge`, the result is
written permanently into `data/records/*.json` (`rec["synthesis"] = side[src]`) and the merge
skips any source that already has a `synthesis` block, so a wrong-method result, once merged,
is never revisited.

Severity: **MAJOR**. Status: **VERIFIED** (direct code comparison against `src/pipeline.py:621-690`,
confirming both the ranking-method mismatch and the unconditional `[:14]` slice against
`phase_synthesis`'s pagination-over-all-feat-bearing-entities).

### retry_synthesis.py:43-47, 109-112 — two-writer-contract breach, no runtime guard

```python
def save_side(d):
    tmp = SIDE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    os.replace(tmp, SIDE)
...
def do_merge():
    """Fold the side file into the records. Run ONLY when the pipeline is stopped."""
    ...
    for path, rec in PL.records():
        ...
        rec["synthesis"] = side[src]
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
```

This project's own established pattern for shared-file writes is `silence.write_json` /
`silence.replace_retry` — verified by reading `src/silence.py:223-287` in full. Two specific
guarantees that pattern provides and this code lacks:

1. **PID+thread-suffixed temp names.** `silence.write_json`'s docstring (line 262) explicitly
   calls this out: "THE TMP NAME CARRIES PID AND THREAD... Two writers of the same path
   otherwise collide on the temp file itself, and the loser can replace the winner's target
   with a partial file." `save_side()` and `do_merge()`'s per-record write both use a bare,
   fixed `path + ".tmp"` — the exact pattern `silence.py` names as the hazard. Nothing in this
   script prevents two invocations (e.g. the owner running it twice to parallelize across the
   twelve failed sources) from racing on the identical temp file.
2. **Retry-on-PermissionError instead of crash.** `silence.replace_retry`'s docstring explains
   that on Windows, `os.replace` is DENIED while any reader holds the destination open, and this
   project's readers "poll on their own clocks." A bare `os.replace(tmp, path)` — used here
   instead of `replace_retry` — will raise an uncaught `PermissionError` and kill the retry run
   mid-loop if any reader (e.g. the dashboard, or `pipeline.py` itself) has the target file open
   at that instant.

Separately, `do_merge()`'s docstring says "Run ONLY when the pipeline is stopped," and
`main()`'s help text repeats the same warning — but there is **no code** that checks
`PIPELINE_STATE.json` (or any other signal) for an idle pipeline before proceeding. The safety
is a comment and a printed reminder, not an enforced precondition, for a function that directly
read-modify-writes the exact `data/records/*.json` files `pipeline.py` phase 2 also
read-modify-writes.

Severity: **MAJOR** (matches the pre-flagged known suspect). Status: **VERIFIED** (direct
comparison against `silence.py`'s documented contract; confirmed no runtime guard exists in
`do_merge()` by reading the full function body).

---

## 3. hostcheck.py:134-135, 245-246 — RAW-mode probe silently conflates "request failed" with "page absent"

The module's own thesis (its docstring, and the fix visible at `probe()`'s API-mode branch,
lines 146-155) is that a failed request must never be scored as a zero hit rate — that exact
conflation is what stranded 74 throttled probes as "WRONG FICTION" and mis-repointed
`warhammer40k.fandom.com`. The API-mode branch honors this: on exception it returns
`{"rate": None, "error": ...}`, and `score()` treats `rate is None` as `"UNREACHABLE — no
judgement"`, explicitly not a verdict.

The RAW-mode branch does not apply the same discipline:

```python
if EP.detect(host)["mode"] == EP.MODE_RAW:
    got = EP.fetch_raw(host, names[:12])
    n = min(len(names), 12)
    return {"host": host, "probed": n, "hits": len(got),
            "rate": round(len(got) / n, 3), "examples": sorted(got)[:5],
            "titles": sorted(got)}
```

and, in `_bodies()`:

```python
if EP.detect(host)["mode"] == EP.MODE_RAW:
    return [b[:8000].lower() for b in EP.fetch_raw(host, list(titles)[:8]).values()]
```

`EP.fetch_raw()` (`src/endpoint.py:190-233`) returns `{title: wikitext}` **only** for titles
that actually succeeded. For a title where the fetch failed for a reason other than a genuine
404/410 — a 403 (this is literally the shape of D&D Wiki's block, per `endpoint.py`'s own
module docstring), a 429 rate-limit, or a 500 — `fetch_raw`'s inner `one()` returns `(t, None)`
and the title is simply missing from the returned dict, indistinguishable from "the wiki does
not have this page." `endpoint.py:206-221` even distinguishes these cases internally for its own
health-ledger bookkeeping (`fetch_raw-absent` vs `fetch_raw-refused-<code>`), but that
distinction is thrown away at the return-value boundary — the caller only ever sees "present" or
"missing."

Both `probe()`'s RAW branch and `_bodies()` compute their result unconditionally from
`len(got)`/`.values()` with no equivalent of the API branch's `rate: None` / `error` escape
hatch. If a raw-only host (D&D Wiki-shaped: closed API, browser-UA-only, throttled) is being
rate-limited or blocked during a probe, `rate` reads as a low or zero number exactly as if the
wiki held none of the probed names, which `score()` will then read as `"WRONG FICTION"` or
`"NAMES ONLY"` and feed straight into `--repair`'s host-rewriting logic. This is the same
failure class the surrounding docstrings spend several paragraphs warning against, reintroduced
in the one code path (RAW mode — D&D Wiki, the project's single most important homebrew host)
that the module explicitly built to cover hosts too closed for the ordinary API test.

Severity: **MAJOR**. Status: **VERIFIED** (traced the full data flow from
`endpoint.fetch_raw`'s per-title try/except through to `probe()`/`_bodies()`'s unconditional
rate computation; confirmed the API-mode branch a few lines above has the escape hatch this
branch lacks).

---

## 4. manifest_builder.py:436, 455, 463 — non-atomic writes to files with concurrent readers

```python
436: with open(out_path, "w", encoding="utf-8") as f:
437:     json.dump({"jobs": all_jobs}, f, indent=2)
...
455: with open(report_path, "w", encoding="utf-8") as f:
...
463: with open(report_path, "w", encoding="utf-8") as f:
```

All three are bare `open(path, "w")` + write, with no temp-file-plus-`os.replace` step at all
(not even a non-PID-suffixed one) — the plainest form of the truncate-then-fill hazard
`silence.write_json`'s docstring describes. `out_path` (`manifest.json` /
`manifest.pilot.json`) is read by `generate.py`, which per this project's own CLAUDE.md is
meant to be run right after this script and is resumable/re-runnable — a reader opening the
manifest mid-rewrite (e.g. an owner re-running `manifest_builder.py` while a previous
`generate.py` pass is still consuming the old one) would see a truncated or empty JSON file.
Confirmed via grep that these are the only three `open(..., "w")` sites in this file and none
of them route through `silence.write_json`/`replace_retry`, even though `silence` is already
imported (line 37) and used nowhere in `main()`.

Severity: **MAJOR** (matches the pre-flagged known suspect). Status: **VERIFIED**.

### manifest_builder.py:316-320 — swallowed feats-index failure is indistinguishable from "no feats"

```python
try:
    feat_rows = feats_index.feats_for_source(source_name, record)
except Exception:
    silence.note("manifest_builder.py:feats")
    feat_rows = []
if feat_rows:
    ...  # emit the Feats & Attested Deeds chapter
```

This is written in the project's officially-sanctioned "observed" form (`silence.note(...)`
does get counted in `health.py`'s ledger, and would not show up in `silence.py --instrument`'s
audit of silent handlers, since the handler body literally contains the string `"silence"`).
But from the manifest-build's own console output and from the generated manifest itself, a
genuine bug or transient failure inside `feats_index.feats_for_source()` (e.g. a `KeyError`,
an `OSError` reading one `data/readfeats/*.json` file, or any regression in the module audited
above) produces **exactly** the same visible outcome as a source that legitimately has zero
mined feats: no Feats chapter, no count, no line in any of this script's printed summaries
(`missing_records` and `unassigned` both get explicit tallies and a report file; a feats-index
exception gets neither). Given finding #1 above (feats_index.py:148) already proves this
module's own join has live, silent-to-the-manifest failure modes, this except-and-continue is
the second half of the same signature bug: a real fault surfaces only in `health.json`'s
ledger, not in anything an operator building the library would normally look at.

Severity: **MINOR** (compliant with the project's own silence-audit convention, but still an
operational blind spot for the actual generated output). Status: **VERIFIED** (read the
try/except directly; cross-referenced against `silence.py`'s own audit criteria to confirm it
would pass that audit while still hiding the failure from the manifest build's own reporting).

---

## 5. pick_model.py — GPU-only residency ruling: enforcement is real for installed models, but silently degrades under an unverifiable assumption

Audited specifically per the task's request: "can [the GPU-only enforcement] be silently
bypassed or can it pick a model that is not installed."

**Cannot pick an uninstalled model.** `scored`/`refused` are built only from `models`, which
comes from `list_installed_models()` (a live `/api/tags` call). `best = scored[0]` can only be
a model Ollama actually reports as installed. No bypass found here.

**Cannot be bypassed for models it does evaluate.** `RESIDENT_ONLY = True` is unconditional (no
CLI flag disables it); `resident(m, budget)` is checked for every candidate before it can enter
`scored`, and non-resident models are only ever placed in `refused` (displayed, never selectable).
Verified this holds regardless of `is_moe()` — the comment at lines 85-91 states MoE status is
"STILL DISQUALIFYING under the residency mandate," and confirmed `resident()`'s actual
implementation (line 190-192) checks total weight + KV against budget with no MoE exemption
anywhere in the comparison itself.

**But the enforcement silently degrades when VRAM cannot be measured:**

```python
budget = (total_vram_gb() or 10.0) - VRAM_RESERVE_GB
```

`total_vram_gb()` shells out to `nvidia-smi`; on any failure (not installed, no GPU, a
transient error) it returns `None` and `budget` silently falls back to `10.0 - 1.0 = 9.0` GB —
the size of *this specific machine's* card, hardcoded as a fallback with no way for
the picker to know it's guessing. Contrast with the neighboring `vram_gb = free_vram_gb()`
block a few lines later, which **does** print an explicit warning when it can't be read:
`"(couldn't read free VRAM -- nvidia-smi not available)"` — but that print is tied only to the
`free_vram_gb()` display value used for `fit_note()`'s cosmetic annotations, not to `budget`,
which drives the actual residency gate and gets no corresponding warning at all. On a machine
with a card smaller than 9 GB usable (or one where `nvidia-smi` genuinely isn't reachable but a
GPU exists via a different query path), this would silently mark a model "resident" that is not,
directly undermining the "GPU-only, and stick to it" ruling the module exists to enforce — with
no printed indication that the 9 GB figure is an assumption rather than a measurement.

Severity: **MAJOR**. Status: **VERIFIED** (read the fallback expression and confirmed, by
tracing every consumer of `budget` vs. every consumer of `vram_gb`, that only the latter's
failure path is surfaced to the operator).

No other correctness issues found in this file: `family_tier`'s substring-match ordering is
self-consistent (longer/more-specific family strings are placed in the higher tier that is
checked first, so e.g. `"qwen3"` matches before the tier-1 catch-all `"qwen"` is ever reached),
`save_config()`'s two previously-fixed silent-success bugs (discarded `replace_retry` return
value, byte-identical no-op rewrite) are both correctly guarded now, and `weight_gb()` prefers
Ollama's own reported `size` field (accurate) over the parameter-count estimate, which is only
used as a last resort.

---

## 6. propagation.py — clean

Read in full. No bare `except` blocks at all in this module (any JSON/graph-load failure is
loud, not silent — consistent with the project's stated discipline). Traced `load_graph()`
(multi-edge consolidation via `min` distance), `shortest()` (a standard, correctly-implemented
Dijkstra: `seen` guard against stale heap entries, correct early-break on reaching `dst`,
correct path reconstruction via `prev`), `hops()`, `ascension_years()`, `arrival_years()`, and
`observed_mark()` (confirmed the rung-threshold loop is monotonic and always resolves to at
least rung 1 whenever `lag >= 0`, so it can't produce an inconsistent result). No caps, no
truncation, no shared mutable state, no file writes at all (this module is read-only against
`data/SHARED_STAGE_GRAPH.json`). Nothing to report.

---

## Summary of severities

- MAJOR: feats_index.py:148, retry_synthesis.py:60 (+docstring), retry_synthesis.py:43-47/109-112,
  hostcheck.py:134-135/245-246, manifest_builder.py:436/455/463, pick_model.py (VRAM-fallback gap)
- MINOR: manifest_builder.py:316-320
- Clean: propagation.py
