# Batch 09 audit — rigor.py, weave.py, reference.py, navtree.py, tells.py, retry_synthesis.py

Full line-by-line read of all six files, top to bottom, no sampling. All line numbers cite the
files as they stand at audit time (2026-08-25).

Summary counts:

| module | high | medium | low |
|---|---|---|---|
| rigor.py | 0 | 0 | 2 |
| weave.py | 2 | 1 | 1 |
| reference.py | 1 | 1 | 1 |
| navtree.py | 0 | 0 | 2 |
| tells.py | 1 | 0 | 0 |
| retry_synthesis.py | 2 | 1 | 1 |

---

## HIGH severity

### retry_synthesis.py:60 — stale sampling reintroduces the exact Hard-Rule-0 bug the owner ordered fixed elsewhere (VERIFIED)

```python
def synthesise(c, rec):
    """Byte-identical prompt construction to phase_synthesis, so a retried source is not
    scored by a different method than its neighbours."""
    src = rec["source"]
    sample = sorted(rec["entries"], key=lambda e: -len(e.get("description", "")))[:14]
```

This is a flat "top 14 by description length" sample over **all** of a source's entries. It is
**not** byte-identical to `phase_synthesis` in `pipeline.py`, which was patched under an explicit
owner ruling:

```python
# pipeline.py:664-673
# EVERY feat-bearing entry is nominated, fourteen per call, best band across chunks
# wins. The fixed sample-of-14 could silently clamp a whole source to a lesser
# ceiling whenever the true strongest entity ranked fifteenth by feat-count -- and
# the clamp then cut that entity's own later evidence down to the wrong band (BUGS
# m13, Hard-Rule-0-shaped, ruled by the owner 2026-08-24: FIX IT ALL). ...
chunks = [with_feats[i:i + 14] for i in range(0, len(with_feats), 14)] or [rest[:14]]
best = None
for ci, sample in enumerate(chunks):
    ...
    if best is None or r_ > best[0]:
        best = (r_, g, b)
```

`phase_synthesis` sorts feat-bearing entries first, chunks them 14-at-a-time, calls the model
once per chunk, and keeps the **best** band across **every** chunk — specifically so that a
source with, say, 40 feat-bearing entries never has its ceiling silently capped by whichever 14
happened to have the longest descriptions. `retry_synthesis.py` never imports or calls
`_mined_feats`/`feats_for`/`with_feats` at all (confirmed absent by grep) — it is running the
exact pre-fix version of this computation, against precisely the sources named in its own module
docstring as needing the retry (Dragon Ball Z and Dune "among them" — both long-running,
feat-rich franchises where this matters most).

This is a genuine Hard Rule 0 violation: it silently returns a smaller evidence universe (14 of
however many feat-bearing entries exist) wearing the same shape as a full nomination, for exactly
the sources the module exists to rescue.

**Repair**: port the feats-first, all-chunks, best-band-wins logic from `phase_synthesis`
verbatim (or better, factor it into a shared function both call), rather than re-deriving a
simplified version that has drifted from the fix.

### retry_synthesis.py:74 — band-cleaning regex is the lax "clamp-only" pattern, not the strict acceptance gate (VERIFIED)

```python
m = re.match(r"^(M(?:10|[0-9]))\b", band)
band = m.group(1) if m else "unassayed"
```

`pipeline.py` deliberately maintains **two** band regexes with an explicitly documented asymmetry:

```python
# pipeline.py:136-139
_CLEAN_BAND = re.compile(r"M(?:10|[0-9])")
def clean_band(value):
    """The band a value actually is, or "unassayed". Never a prefix of one."""
    text = str(value or "").strip()
    return text if _CLEAN_BAND.fullmatch(text) else "unassayed"

# pipeline.py:142-150
def ceiling_band(value):
    """A source's ceiling read for CLAMPING only, where a legacy dirty value is still usable.
    Deliberately laxer than `clean_band` ... Acceptance is strict, clamping is forgiving;
    the asymmetry is the point."""
    m = re.match(r"^(M(?:10|[0-9]))\b", str(value or "").strip())
    return m.group(1) if m else None
```

`phase_synthesis` uses the **strict** `clean_band` (fullmatch) to accept a fresh LLM nomination
(pipeline.py:692). `retry_synthesis.py` instead reimplements the **lax**, clamp-only regex for
the same accept-a-fresh-nomination purpose. Verified empirically:

```
'M7.62'        clean_band -> 'unassayed'   retry_synthesis -> 'M7'
'M7 (approx)'  clean_band -> 'unassayed'   retry_synthesis -> 'M7'
'M10 tier'     clean_band -> 'unassayed'   retry_synthesis -> 'M10'
```

So a dirty/decimal-contaminated model output that the main phase would correctly refuse as
`unassayed` is silently accepted as a clean band by the retry path. This directly undermines the
"no feat, no band" invariant the codebase treats as critical elsewhere (pipeline.py:693-695: "an
unevidenced source ceiling does not misplace one entity, it tilts a whole shelf") — for exactly
the sources being retried.

**Repair**: import and use `pipeline.clean_band` instead of reimplementing the regex.

### weave.py:216-217 vs weave.py:467 — the "WHOLE list" comment is false; the list is capped at 8 (VERIFIED)

```python
# weave.py:204-218
def surprisal_pair_weights(occ, sur, min_sources=2, max_sources=60):
    ...
    for k, srcs in occ.items():
        ...
        for i in range(len(srcs)):
            for j in range(i + 1, len(srcs)):
                p = (srcs[i], srcs[j])
                w[p] += s
                if len(shared[p]) < 8:
                    shared[p].append(k)
    return w, shared
```

```python
# weave.py:465-469 (main(), --write)
json.dump({"threshold": thr, "metric": "name-surprisal, bits",
           "pairs": [{"a": a, "b": b, "weight": round(v, 2),
                      "shared_sample": shared[(a, b)]}   # WHOLE list (key name kept: resonance.py reads it) -- Hard Rule 0, ruled 2026-08-24
                     for (a, b), v in sorted(kept.items(), key=lambda kv: -kv[1])]},
          open(OUT_GRAPH, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
```

The comment claims the list is now whole per a Hard Rule 0 ruling, but the function that actually
produces `shared` still caps every pair's evidence list at 8 entries (`if len(shared[p]) < 8:`).
The comment and the code directly contradict each other. This is not confined to weave.py's own
demo path either — `pipeline.py`'s production phase 3 (`pipeline.py:1758-1762`) carries the
identical false comment ("WHOLE list -- Hard Rule 0, ruled 2026-08-24") over the same capped
`shared` dict, and `resonance.py:146` reads the field (`p.get("shared_sample", [])`) as evidence
for how two shelves relate. The **weight** used for thresholding is not affected by the cap (it
sums over all `k` regardless), but the **evidence list** that is supposed to justify the
relationship to a reader is silently truncated past the 8th shared entity, despite the code
comment asserting otherwise.

**Repair**: either remove the `if len(shared[p]) < 8` cap (make the comment true), or fix the
comment to say "sample" honestly and stop calling it Hard-Rule-0-compliant.

### weave.py:461-469 — bare `open(path, "w")` on shared data files the pipeline also writes (VERIFIED)

```python
if args.write:
    json.dump({"threshold": thr, "groups": groups},
              open(OUT_GROUPS, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    json.dump(resolved, open(OUT_RESOLVED, "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    json.dump({...}, open(OUT_GRAPH, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
```

`OUT_GROUPS` = `data/CONTINUITY_GROUPS.json` and `OUT_RESOLVED` = `data/RESOLVED_ENTITIES.json`
are the **same files** `pipeline.py`'s phase 3 writes via `land_json` — the atomic
write-then-verify helper whose own docstring exists specifically to describe and fix this exact
pattern:

```python
# pipeline.py:468-478
def land_json(path, obj, indent=1, default=None):
    """Write a phase artifact atomically. Returns whether it landed.
    The later phases wrote their artifacts as `json.dump(obj, open(path, "w"), ...)`: not
    atomic, and the handle never explicitly closed either, so a reader could see a
    half-serialised file ... Several of these are read by a LATER PHASE IN THE SAME RUN ...
    a crash or a slow reader mid-write does not just cost a cycle, it feeds the next phase a
    truncated file. (BUGS m6, 2026-08-24.)"""
```

`weave.py`'s standalone `--write` path was never updated to use `land_json`/
`silence.replace_retry`; it still performs the exact non-atomic, unclosed-handle write that
`land_json`'s own docstring documents as a fixed bug elsewhere. Running `python weave.py --write`
by hand while the pipeline (or any other reader) touches these files reintroduces the
half-serialised-file risk on files another phase reads mid-run.

**Repair**: route these three writes through `pipeline.land_json` (or `silence.replace_retry`
directly) instead of bare `open(path, "w")`.

### tells.py:70 — regex alternation precedence makes half the pattern unconditional; false positives confirmed (VERIFIED)

```python
STRUCTURAL = {
    "not merely X but Y": r"\bnot merely\b|\bnot simply\b|\bnot just\b.{0,40}\bbut\b",
```

`|` has the lowest precedence in regex, so this is three independent alternatives:
`\bnot merely\b`  OR  `\bnot simply\b`  OR  `\bnot just\b.{0,40}\bbut\b`. Only the third
alternative requires the "but Y" half of the reveal; the first two fire on the bare phrase alone.
Confirmed by direct test against the compiled pattern:

```
'This was not merely a battle.'              -> True   (no "but" anywhere in the sentence)
'This was not simply a battle.'              -> True   (no "but" anywhere in the sentence)
'This was not just a battle.'                -> False  (correctly requires "but")
'This was not merely a battle, but a war.'   -> True
```

The tell is documented as "sentence shapes used as a reveal: 'not merely X but Y'" — a completely
ordinary sentence using "not merely" with no reveal at all is scored as a machine tell. Given this
audit is described as governing tens of thousands of entries, this produces systematic false
positives across the corpus for two of the three "not X" starter phrases.

**Repair**: `r"\b(?:not merely|not simply|not just)\b.{0,40}\bbut\b"` (group the alternation so
the "but" requirement applies to all three).

### reference.py:331 — bare `open(OUT, "w")` on a data file read by two other modules (VERIFIED)

```python
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
```

`OUT` = `data/REFERENCE_ASSAYS.json`, which `standards.py` and `zfighters.py` both read (confirmed
by grep). This is the same non-atomic write pattern flagged above for weave.py, on a file that is
a genuine cross-module dependency rather than a private scratch file. It does at least use a
`with` block (closes its own handle, unlike the weave.py instances), but it is still not atomic —
a reader mid-run of `standards.py`/`zfighters.py` could observe a partially-written file.

**Repair**: route through `pipeline.land_json` or an equivalent tmp+`os.replace` pattern.

---

## MEDIUM severity

### retry_synthesis.py:94-115 — `do_merge()` bypasses `write_record`'s drift protection (VERIFIED)

```python
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

`pipeline.write_record` exists specifically to protect `data/records/*.json` against a stale
in-memory copy clobbering a concurrently-modified disk copy (its own docstring: "the pipeline
loads its records at phase start and holds them for hours; the re-catalogue rewrites the same
file in the meantime ... Writing the pipeline's stale in-memory copy over that would silently
revert twenty-nine thousand entries"). `do_merge()` reads records via `PL.records()` and then
writes them back with a hand-rolled tmp+`os.replace` (atomic against torn writes, but with no
drift check), skipping that protection entirely. The only actual safeguard is the docstring
instruction "Run ONLY when the pipeline is stopped" — unenforced in code (no PID check, no state
flag check). If that instruction is ever not followed, this file reintroduces exactly the failure
mode `write_record` was written to prevent.

**Repair**: call `PL.write_record(path, rec)` instead of the manual tmp+replace, so the same
drift-merge protection applies here too.

### weave.py:156-172, 241-265 — dead code duplicating the live surprisal-based functions (VERIFIED)

`pair_weights()` (idf-weighted) and `null_threshold()` (its matching permutation-null function)
are never called anywhere in `src/` (confirmed by grep) — `main()`, `pipeline.py`, and `tiers.py`
all use `surprisal_pair_weights()`/`null_threshold_surprisal()` instead. Both dead functions
duplicate the same 8-item-per-pair cap discussed above with no comment claiming otherwise, so they
are at least internally honest, but they are unreachable code maintaining a second copy of logic
that has already diverged from the one actually in use (idf-based weighting vs. name-surprisal
weighting — two different methodologies, only one of which the module's own docstring argues for).

Separately, `OUT_GRAPH` (`data/SHARED_STAGE_GRAPH_IDF.json`) — the file weave.py's own `--write`
path produces — is not read by any other module in `src/`. The module's docstring frames its
whole purpose as fixing the flawed raw-count graph (`cosmology_graph.py`'s
`data/SHARED_STAGE_GRAPH.json`, still the file `resonance.py`'s only caller-default points at),
but `resonance_strength()` in resonance.py is itself never called from anywhere in `src/`, so
neither the old flawed graph nor weave's corrected one is actually wired into a live consumer
today. Worth the owner's attention as an integration gap, not a correctness bug in weave.py
itself.

### reference.py:232-246 — `shelfmark()` hardcodes a 3-segment `tier_key` assumption (VERIFIED, currently dormant)

```python
RUNGS = ("H.", "X.", "Mt.", "Mv.", "U-", "G.", "P.")

def shelfmark(rec):
    try:
        nav = json.load(...)
        parts = rec["tier_key"].split(".")
        upper = []
        for i in range(len(parts)):
            k = ".".join(parts[:i + 1])
            upper.append(nav["nodes"].get(k, {}).get("name", k))
    except Exception:
        silence.note("reference.py:232")
        upper = ["?", "?", "?"]
    lower = rec.get("lower_rungs", ["?", "?", "?", "?"])
    marks = [f"{RUNGS[i]}{v}" for i, v in enumerate(upper)]
    marks += [f"{RUNGS[3 + i]}{v}" for i, v in enumerate(lower)]
```

The lower-rung marks are built with a hardcoded `RUNGS[3 + i]` offset, which is only correct if
`upper` always has exactly 3 elements — i.e. only if `tier_key` always splits into exactly 3
dot-separated segments. The exception fallback bakes the same assumption in explicitly
(`upper = ["?", "?", "?"]`, always length 3, regardless of how many parts the real `tier_key` had).
All three entries currently in `REFERENCE` (Goku, Naruto, Luffy) do use 3-part tier keys
(`"1.6.1"`, `"4.2.0"`, `"1.2.5"`), so this does not currently misfire, and `tier_key` is not
referenced anywhere else in `src/`. But nothing asserts or guards the 3-part assumption, so a
future hand-added reference entry with a differently-shaped `tier_key` would silently misalign
`RUNGS` indices — producing a wrong-but-plausible-looking shelfmark rather than an error, which is
exactly the failure mode this project treats as worst-case.

**Repair**: derive the lower-rung offset from `len(upper)` rather than the literal `3`, and/or
assert `len(parts) == 3` when building the record.

---

## LOW severity / notes

- **rigor.py:89, weave.py:74, reference.py:59, tells.py:38** — the shared `_BAD_CHARS`
  control-character guard opens the module's own source file (`open(os.path.abspath(__file__), ...)`)
  and never closes the handle explicitly (relies on refcounting). Harmless in practice (import-time,
  short-lived), but inconsistent with the atomic/explicit-close discipline the codebase otherwise
  insists on elsewhere (see `land_json`'s docstring, which specifically calls out "the handle never
  explicitly closed either" as part of a bug it fixed). Same pattern repeats identically in all four
  files audited here that carry the guard; navtree.py also carries it in spirit via other unguarded
  `open()` reads, though it does use `with` blocks throughout.

- **rigor.py:436-444** — `bradley_terry`'s `prior > 0` branch always attaches the caveat "strengths
  exist because every entrant was given symmetric virtual contests, NOT because the recorded
  outcomes connect them," even in the (rare, but possible) case where `identified` is independently
  already `True` from the raw data — i.e. a caller who passed a prior "just in case" would get a
  caveat overstating how little the raw data supports the result, even though `out["identified"]`
  itself is correctly `True` in that case. The returned numbers are unaffected; only the
  natural-language caveat can be misleading. Cosmetic, not a data-correctness issue.

- **navtree.py:63-68, 117-128** — ONOMASTICON.json / GROUNDINGS.json / GENRES.json load failures
  are caught with a bare `except Exception:`, logged via `silence.note`, and default to `{}`. This
  degrades gracefully (source names fall back to their raw designation, groundings default to
  "ungrounded") rather than crashing, and is logged rather than silently swallowed — consistent
  with the project's established `silence.note` convention used throughout this whole file family.
  Flagged only because a genuine parse error (malformed JSON from a real bug) is treated identically
  to "file legitimately absent," so a real data-corruption bug upstream would show up as degraded
  naming rather than a hard failure. Not a violation of the two-writer contract or Hard Rule 0.

- **navtree.py:256** — `for p in problems[:6]:` caps the console-printed audit-problem examples at
  6. This is a display-only truncation of a diagnostic list, not catalogued content: the full count
  is printed separately (`AUDIT: {len(problems)} problems`), and the `--write` gate
  (`if args.write and not problems`) checks the complete, unsliced list. Judgment call, not a
  violation.

- **retry_synthesis.py:83-91** — the dict `synthesise()` returns omits the `"assessed_at"`
  timestamp field that `pipeline.py`'s `phase_synthesis` always writes into `rec["synthesis"]`
  (pipeline.py:717). No code in `src/` currently reads `assessed_at` (confirmed by grep), so there
  is no live functional impact today, but it is a further concrete way in which the "byte-identical"
  claim in this file's docstring does not hold — synthesis records produced via the retry path are
  schema-incomplete relative to records produced by the main phase.

---

## Per-module verdicts

- **rigor.py** — CLEAN of correctness bugs, Hard Rule 0 violations, and swallowed failures. Two
  low-severity notes only (shared unclosed-handle idiom; one cosmetic caveat-message edge case in
  `bradley_terry`). The module is unusually self-auditing — most of its docstrings document and
  correct prior bugs in the same breath, and those corrections check out on inspection
  (`measure_bit_value`'s switch to `band_resolution`, `bradley_terry`'s Ford's-condition refusal,
  `mathematical_resonance`'s explicit no-truncation `load_bearing` field).

- **weave.py** — 2 high, 1 medium, 1 low. The headline issue is the false "WHOLE list" comment over
  a genuinely-capped 8-item evidence sample, echoed verbatim in pipeline.py's production path; the
  second is a two-writer-contract bypass in the standalone `--write` CLI path. The core
  entity-resolution logic itself (complete-linkage clustering, permutation-null threshold,
  resonance-graph BFS, `resolve()`) was read in full and is correct.

- **reference.py** — 1 high, 1 medium, 1 low. The high is a two-writer-contract bypass on a file
  two other modules read; the medium is a dormant hardcoded-offset fragility in `shelfmark()`. The
  calibration data itself (the three hand-built Assay sheets) and the `compute`/`citation`/`card`
  machinery are correct.

- **navtree.py** — CLEAN of correctness bugs and Hard Rule 0 violations; two low notes only. This
  file is the strongest evidence of the family's self-correcting discipline: all three
  historically-documented bugs (unreachable hyperverse, world lists truncated at 40, invisible
  sources) were traced through the current code and are genuinely fixed — world lists are written
  in full (`No cap: a universe lists every world it holds`, verified at the `touch(path)["w"].append`
  call site and the final `sorted(v["w"], ...)` with no slice), and the two hash-order
  nondeterminism bugs (m41) have real, verified deterministic tie-breaks.

- **tells.py** — 1 high, otherwise clean. The regex precedence bug is narrow (one pattern out of
  ~30) but concrete and verified by direct execution; the rest of the anchoring logic
  (`_anchor`/`_SENTENCE_START`, the control-character guard, `prompt_section`'s full-list word-wrap)
  is correct and Hard-Rule-0-compliant (no truncation of the banned-phrase lists anywhere).

- **retry_synthesis.py** — 2 high, 1 medium, 1 low. This file has drifted from the `phase_synthesis`
  it claims to mirror byte-for-byte: it is missing the owner-mandated feats-first/all-chunks fix
  (Hard Rule 0 shaped), it uses the wrong (lax) band-acceptance regex, its merge path skips the
  established record-write safety net, and its output schema is missing a field the main phase
  always writes. The read-only/side-file discipline this module is built around (never touching
  `PIPELINE_STATE.json` or `data/records/*.json` during the collection pass, appending only to its
  own private `SYNTHESIS_RETRY.json`) is itself sound and correctly implemented — the problems are
  all in how faithfully it reproduces the main phase's *scoring* logic, not in its concurrency
  design.
