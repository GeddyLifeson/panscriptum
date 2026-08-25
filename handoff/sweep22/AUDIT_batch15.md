# Batch 15 audit — wiki_source.py, local_agent.py, generate.py, worldseed.py, sweep.py, thread_integrity.py, ledger.py

Every line of every assigned module read top to bottom. Findings grouped by severity, per module.
No files edited. `C:/Users/imarl/miniconda3/python.exe` was available but not needed for this pass
(read-only, static audit).

---

## HIGH

### H1 — `wiki_source.py:352-389` `all_categories()`: `hard_stop` truncates the answer, and the docstring's own defence of it is false

```python
def all_categories(subdomain, min_pages=40, hard_stop=6000):
    """...
    `hard_stop` bounds the API walk, not the answer: it exists so a wiki with a hundred thousand
    year-buckets cannot spin here forever.
    """
    ...
    out, cont = [], None
    while len(out) < hard_stop:
        p = {"action": "query", "list": "allcategories", "aclimit": 500,
             "acmin": min_pages, "acprop": "size"}
        if cont:
            p["accontinue"] = cont
        try:
            d = _api(subdomain, p)
        except Exception:
            silence.note("wiki_source.py:all_categories")
            break
        for c in d.get("query", {}).get("allcategories", []):
            name = c.get("*") or ""
            if name and not _META_CATEGORY.search(name):
                out.append((c.get("pages", 0), name))
        cont = d.get("continue", {}).get("accontinue")
        if not cont:
            break
```

`list=allcategories` is walked in ascending alphabetical order by category name (MediaWiki's own
ordering; `accontinue` is a category-name cursor). The loop condition is `len(out) < hard_stop` —
that tests the size of `out`, the **filtered, kept answer**, not the number of raw API pages
walked. The docstring's claim ("bounds the API walk, not the answer") is contradicted by the code
directly beneath it: the moment `out` reaches 6000 *kept* categories, the walk stops, mid-alphabet,
and every category whose name alphabetically follows the 6000th surviving one is never seen by
`discover_categories()` or `find_categories()`.

This is exactly the shape of failure this file's own comments cite as the reason Hard Rule 0
exists: `roster(limit=600)` lost Goku, `roster(limit=6000)` lost Superman and Wonder Woman, and the
professional-wrestling case cited at `wiki_source.py:102` (a whole cast living only under "Male
wrestlers"/"Female wrestlers", categories no fixed probe list would guess). A large wiki
(Marvel-, DC-, or wrestling-scale) can plausibly carry more than 6000 categories with ≥40 pages
once talk/meta noise is filtered; if the one category a source's roster actually lives under sorts
alphabetically past the 6000th survivor, `discover_categories` never sees it and that canonical
class silently resolves to whatever the fixed `CATEGORY_PROBES` guessed (or nothing).

**Verdict: violation, not a judgment call.** The comment explicitly disclaims truncating the
answer; the code truncates the answer. Either the docstring is wrong about what `hard_stop`
protects, or the implementation needs to count raw API results seen (not categories kept) against
the stop condition — as written, the two disagree and the code decides.

VERIFIED (read both the loop and the MediaWiki `list=allcategories` ordering contract; not
independently re-run against a live wiki as part of this audit).

---

### H2 — `generate.py:53-57` (`save_json`), used for `output/index/catalog.json` and `output/index/failures.json`: bare `open(path, "w")` on files this project's own convention writes atomically

```python
def save_json(path, obj):
    full = os.path.join(HERE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
```

Called at `generate.py:378` (on every job failure), `:409` (every 5 successes), and `:411/:413`
(end of run) to rewrite `output/index/catalog.json` and `output/index/failures.json` — files a
generation run keeps open and rewrites for *hours* (per this kit's own `CLAUDE.md`: "Local
generation of hundreds of chapters takes a while"). This is a bare `open(path, "w")` directly on
the destination, not a write-to-`.tmp`-then-`os.replace` — the exact pattern `pipeline.py`'s
`_landed`/`write_record`/`write_record_catalogue` and `silence.replace_retry` exist to enforce
project-wide, per `silence.py:223-240`:

> `os.replace` with a short retry, because on Windows the rename is DENIED while any reader holds
> the target open — and this project's state files all have readers on their own clocks (the
> dashboard polls records and ASSAYS, standards scans readfeats).

`output/index/catalog.json` and `output/index/failures.json` are not private to `generate.py`:
`catalog.py` reads `catalog.json` for every `catalog.py stats`/`search`/`read` call, and
`estate.py:236-252` opens both files directly (`("catalog.json", "generation catalog")`,
`("failures.json", "generation failures on record")`) — with a try/except that reports the file as
`"... UNREADABLE"` on a `json.JSONDecodeError`, which is exactly what a reader landing mid-`write`
on a multi-hundred-KB catalog produces. `json.dump` is not one syscall; a reader opening the file
in that window sees a truncated document, not a lock.

Contrast with `pipeline.write_record` (`pipeline.py:487+`), which explicitly re-reads the disk
copy and merges on drift specifically because "the pipeline loads its records at phase start and
holds them for hours" — the same shape of long-lived process `generate.py` is. `generate.py`
instead loads `catalog`/`failures` once at start (`:321-322`) and blind-overwrites on every save,
with no re-read-and-merge — so a concurrent writer to either file (not observed in this batch, but
nothing prevents one) would also lose its update silently, the same failure `write_record`'s
docstring names by number ("marvel.json went from 1,051 entries to 30,207 ... writing the
pipeline's stale in-memory copy over that would silently revert twenty-nine thousand entries").

**Suggested repair:** route both through `silence.replace_retry` (write `path + ".tmp"`, then
`silence.replace_retry(tmp, path)`), matching `pipeline.py`'s own `_landed` helper.

VERIFIED (code read directly; confirmed `estate.py` and `catalog.py` as live concurrent readers of
the exact same paths via `paths["catalog"]`/`paths["failures"]` in `config.yaml:166-167`).

---

## MEDIUM

### M1 — `worldseed.py:317-322` bare `open(path, "w")` on `data/WORLDSEEDS.json`, a file with other readers

```python
if args.write:
    path = os.path.join(HERE, "data", "WORLDSEEDS.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({w["designation"]: {"address": address(w), **w} for w in worlds},
                  f, indent=2, ensure_ascii=False)
```

`data/WORLDSEEDS.json` is read directly by `address_space.py` and `pipeline.py` (confirmed by
grep). Same class of issue as H2, lower severity because this is a single one-shot CLI write
(`worldseed.py --write`) rather than an hours-long incrementally-updated file, so the torn-read
window is much shorter — but it is still a bare overwrite of a file this project's own convention
(`silence.replace_retry`) exists specifically to protect, and a reader that hits the file in the
few-hundred-millisecond write window on a ~5,200-world dump gets a corrupt read, not a clean
failure. Route through `silence.replace_retry`.

VERIFIED.

### M2 — `sweep.py:233-234` bare `open(OUT, "w")` on `data/CHARACTER_SWEEP.json`, read by four other modules

```python
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False)
```

`data/CHARACTER_SWEEP.json` is read by `foreman.py`, `hostcheck.py`, `magnitude.py`, and
`standards.py` (confirmed by grep). Same pattern as M1: single CLI-run write, not
`silence.replace_retry`-wrapped, and this file can be large (the module prints its own KB size
after writing, so a reader hitting mid-write on a many-MB dump is a real torn-read risk, however
brief the window).

VERIFIED.

### M3 — `thread_integrity.py:104-113` DANGLING classification only fires when *every* shared key has drifted, contradicting its own docstring's per-key description

```python
if ents is not None:
    gone = [k for k in shared if k not in ents.get(a, ()) or k not in ents.get(b, ())]
    if gone and len(gone) == len(shared):
        out["DANGLING"] += 1
        detail["DANGLING"].append((a, b, len(gone)))
        continue
```

The `classify()` docstring (lines 93-97) says:

> DANGLING is computed for real, against the live records: a candidate key whose source no longer
> holds that entity (weave drift).

— singular, per-key language: "a candidate key whose source no longer holds that entity" reads as
"any drifted key is a dangling thread." The code, however, only marks the *entire pair* DANGLING
when **all** of its shared keys have drifted (`len(gone) == len(shared)`). If a pair shares 5
candidate keys and 4 have drifted out of one side's record but 1 genuinely still holds, `gone` is
computed (non-empty, length 4) but then thrown away — the branch is not entered, and the pair
falls through to `IMPLIED-UNRECORDED` (or the future `recorded`-graph branches) reporting the
*original* `len(shared)` of 5, silently including the 4 keys that no longer exist on one end. The
partial-drift information the code computed is discarded rather than surfaced.

Whether "one pair, all-or-nothing" or "one entry per drifted key" is the *intended* semantics is a
judgment call the audit can't make for the owner — but as written, the code and its own docstring
describe two different things, and the practical effect is that partial weave drift (the much more
common case — one source's entry gets renamed or removed, not the whole pair's worth) is never
counted or reported anywhere in this module's output.

VERIFIED (docstring and code both quoted verbatim above; the mismatch is direct).

### M4 — `sweep.py:187,190,192` unguarded division by `n` in `report()`; every other rate in the same function guards against `n == 0`

```python
prev = n
for k in ("catalogued", "addressed", "reachable", "read", "evidenced", "assayable"):
    drop = prev - f[k]
    bar = "#" * int(38 * f[k] / max(n, 1))
    print(f"  {k:<12}{f[k]:>9,}{f[k]/n:>8.1%}  {bar}"
          + (f"   -{drop:,}" if drop else ""))
    prev = f[k]
print(f"\n  {'ranked':<12}{f['ranked']:>9,}{f['ranked']/n:>8.1%}   "
      f"(own fiction publishes a scale position)")
print(f"  {'banded':<12}{f['banded']:>9,}{f['banded']/n:>8.1%}   "
      f"(carries a Magnitude today)")
```

`n = len(rows)` (line 168), and `rows` comes from `sweep()`, which only appends a row when
`PERSON.search(e.get("category") or "")` matches (line 142). If a manifest/records snapshot with
zero Person-classed entries is ever swept (a plausible state early in a fresh catalogue, or when
testing against a filtered/partial `data/records/`), `n == 0` and every `f[k]/n` above raises
`ZeroDivisionError`, crashing the report after it has already printed the header. The `bar =`
line on the same loop iteration *does* guard with `max(n, 1)` — so the author was clearly aware of
the zero case in this exact function — but the percentage computed one expression later is not
guarded the same way. Low likelihood in the current ~17,444-entry corpus, but a real, easily
triggered crash on a smaller or filtered run.

**Suggested repair:** `f[k]/max(n,1)` at all three sites, matching the `bar` computation's own
guard.

VERIFIED.

---

## LOW

### L1 — Stale/uninformative `silence.note()` site labels that no longer match their line numbers (systemic, several modules)

`wiki_source.py:190,196,241,295,378,538,557,584` and `generate.py:370` all call
`silence.note("modulename.py:NNN")` with a line-number literal baked into the string. Several of
these numbers no longer correspond to the line they're called from (e.g. `wiki_source.py:190` is
labelled `"wiki_source.py:155"`, `:196` is labelled `"wiki_source.py:160"`, `generate.py:370` is
labelled `"generate.py:166"`). `wiki_source.py` itself documents, in the fix for a *different*
stale-label bug at line ~279-283, exactly why this matters:

> this label was shared with the live category probe ... so the ledger reported one class where
> two unrelated things were failing ... That defeats the whole point of the ledger.

The same failure mode (a label that drifts and stops meaning what it says) is still present at the
sites listed above; it just hasn't yet caused two *different* failure classes to collide under one
label the way the documented m5 bug did. Not urgent — these are diagnostic labels, not correctness
bugs — but worth a follow-up sweep to replace remaining line-number labels with the semantic-label
convention the project has already adopted elsewhere in this same file (`"wiki_source-hosts-read"`,
`"wiki_source-page_text-section"`, `"wiki_source-category-probe"`).

UNVERIFIED as to whether any of these specific stale labels have yet caused a real ledger
collision (no evidence found in this batch that they have — flagging as a latent recurrence of a
pattern the codebase has already fixed once).

### L2 — `local_agent.py:282,283,286` (`t_grep`) and `sweep.py:100,116,127` (`rosetta_index`, `navtree_names`, `sweep`): files opened without `with` or explicit `close()`

```python
for i, ln in enumerate(open(fp, encoding="utf-8", errors="replace"), 1):
```
```python
for host, scales in json.load(open(p, encoding="utf-8")).items():
```

Relies on CPython reference counting to close the handle once the generator/expression is done;
not guaranteed by the language, and `t_grep` in particular can open many files across a whole
subtree in one call. Low practical severity — CPython's refcounting GC does close these promptly
in practice, and both are short-lived CLI/tool-call processes, not long-running servers — but
worth switching to `with open(...) as f:` for correctness rather than relying on implementation
detail. Explicitly *not* the case CPython documents as guaranteed (only `del`/scope-exit under
CPython's refcounting is "usually" prompt; PyPy or a future CPython GC change would leak these for
real).

VERIFIED (pattern present as quoted; not observed to cause an actual failure in this audit).

### L3 — `wiki_source.py:275-284` `resolve_wiki()` only catches `OSError` reading `WIKI_HOSTS.json`; a corrupt (not just missing) hosts file raises uncaught

```python
try:
    with open(_hosts_path, encoding="utf-8") as f:
        known = json.load(f).get(source_name)
except OSError:
    silence.note("wiki_source-hosts-read")
    known = None
```

The comment immediately above this block explains, at length, why *only* the file-open/read is
inside the `try` (a prior version's whole block was wrapped and a `NameError` from a missing
`HERE` constant got silently swallowed and misdiagnosed as "no hosts file"). That reasoning is
sound for guarding against catching too much — but the `except` clause itself only catches
`OSError`, not `json.JSONDecodeError` (which is a `ValueError`, not an `OSError`). A corrupted
`data/WIKI_HOSTS.json` — a real possibility given this exact file was flagged mid-audit as the one
the library depends on for DC/Marvel resolution — would raise `JSONDecodeError` here uncaught,
crashing `resolve_wiki()` (and by extension anything that calls it) instead of falling back to
`known = None` and continuing with the guess-and-verify path the rest of the function already
implements. This may be intentional ("fail loud on corrupt canonical data" is a defensible choice)
but it sits awkwardly next to a docstring about this exact function's history of masking failures
as silent resolution misses.

UNVERIFIED as a bug (could be deliberate fail-loud behaviour); flagged because the failure mode is
real and untested by this audit.

---

## Informational — not a fresh finding, reported per instructions

### `ledger.py:127-133` `assay_to_standards()` — top-band (`M10`) edge case, `hi == lo`

```python
i = LADDER.index(magnitude_band)
lo = BAND_EDGES[magnitude_band]["ruin"]
hi = BAND_EDGES[LADDER[min(i + 1, len(LADDER) - 1)]]["ruin"]
joules = math.exp(math.log(lo) + (ruin_score / 10.0) * (math.log(hi) - math.log(lo)))
```

`LADDER = ["M0", ..., "M10"]` (`assay.py:105`). At `magnitude_band == "M10"`, `i == 10 ==
len(LADDER) - 1`, so `min(i + 1, len(LADDER) - 1) == 10 == i`, so `LADDER[10] == "M10" ==
magnitude_band` — `hi` resolves to `BAND_EDGES["M10"]["ruin"]`, the same value as `lo`. With
`hi == lo`, `math.log(hi) - math.log(lo) == 0`, so the interpolation term vanishes and
`joules == lo` for every `ruin_score` from 0 through 10 at the top band — `assay_to_standards`
returns the M10 floor regardless of how high within M10 the actual score is. This matches the
described open bug (M18); reported as observed, not re-litigated or proposed a fix per the task
brief.

VERIFIED by direct trace of `LADDER`/`BAND_EDGES` (`assay.py:71-105`) against this code.

---

## Hard Rule 0 sweep — every cap found in this batch, and its verdict

| Site | Cap | Verdict |
|---|---|---|
| `wiki_source.py:352` `all_categories(hard_stop=6000)` | truncates alphabetically-ordered category list | **VIOLATION** — see H1 |
| `wiki_source.py:409` `find_categories(limit=None)` | default `None` = uncapped | not a violation (already fixed per the file's own comment, confirms Hard Rule 0 compliance) |
| `wiki_source.py:520` `category_members(limit=None)` | default `None` = uncapped, explicit anti-truncation docstring | not a violation |
| `wiki_source.py:567` `rank_by_size(top=None)` | default `None` = uncapped; ranks, doesn't truncate unless caller opts in | not a violation by default |
| `generate.py:271` `WRITE_CHUNK = 8` | batches a chapter's entries for the model call, never drops any — missing entries retry once then fail the whole job loudly | not a violation (batching, not truncation; verified against `generate_job`'s retry/raise logic) |
| `generate.py:345` `pending[: args.limit]` | explicit opt-in `--limit` CLI flag, documented as "only run the first N pending jobs" | not a violation (explicit, documented, opt-in partial run — not a silent default) |
| `generate.py:297` `missing[:8]` in an error message | truncates only the printed list of names in a raised exception's text; the full `missing` list still fails the whole job | not a violation (diagnostic text, not catalogued content) |
| `worldseed.py:244` `build_all(limit=None)` | default `None` = uncapped over every catalogued Place entry | not a violation |
| `worldseed.py:168` `states = min(40, ...)` | bounds a *generated* procedural-map parameter (political fragmentation), not a roster/entry list | not a violation — judgment call over a synthetic generation parameter, no real catalogued content involved |
| `sweep.py:167` `report(rows, top=18)` | display-only sample of "deepest evidence" characters printed to console | not a violation — the full `rows` table is written to `data/CHARACTER_SWEEP.json` unfiltered (line 234); only the console preview is capped |
| `sweep.py:215,222` `.most_common(10)`, `.most_common(8)` | display-only Counter samples in console report | not a violation, same reasoning |
| `thread_integrity.py:174,179` `[:8]`, `[:6]` | display-only samples of strongest/most-suspect thread pairs | not a violation — `counts` (the real totals) are computed and printed in full above these; only the itemised examples are capped |

No cap in this batch was found silently applied to a roster, page list, or catalogued-content list
that gets *persisted* as the final answer, **except** H1 (`wiki_source.py`'s `all_categories`
`hard_stop`), which is the one place a cap gates which categories a wiki's roster can even be
discovered under.

---

## Per-module summary

- **wiki_source.py** — 1 HIGH (H1), 3 LOW-adjacent notes (L1 partial, L3). Otherwise clean: the
  three explicitly-uncapped functions (`find_categories`, `category_members`, `rank_by_size`) show
  real, documented Hard Rule 0 remediation from prior audits, and `_get`'s retry/backoff logic,
  `verify_wiki_matches`'s anti-false-resolution check, and `_paragraphs`'s HTML-to-prose extraction
  were all read in full and found sound.
- **local_agent.py** — 0 HIGH, 0 MEDIUM, 1 LOW (L2, `t_grep` unclosed handles). The write-gating
  this file exists to provide was checked specifically per the task brief: `t_propose_patch` is the
  only write path, it is denylist-checked (both by module name and by repo-relative path, per the
  fix documented at lines 363-368), requires an exact-once `find` match, writes a backup before
  patching, runs `_gates()` (parse/lint/import/whole-suite `verify_math`) unconditionally for every
  file type including non-`.py`, and reverts on any gate failure or exception. This is genuinely
  gated — no bypass found.
- **generate.py** — 1 HIGH (H2), 0 MEDIUM, 0 additional LOW beyond L1's one site. The Hard Rule 0
  discipline in `generate_job`'s chunked-write-with-retry-and-loud-failure design is sound and
  matches its own docstring precisely.
- **worldseed.py** — 0 HIGH, 1 MEDIUM (M1). Everything else read clean: `build_all` is genuinely
  uncapped by default, the "seeded, never defaulted" fallback in `_first()` is a real fix for a
  documented prior bug (900 worlds looking alike), and the FMG query-parameter emission was
  empirically re-verified against a real generator version rather than assumed.
- **sweep.py** — 0 HIGH, 1 MEDIUM (M2), 1 MEDIUM (M4 — division-by-zero). `load()`'s
  FileNotFoundError-vs-real-corruption split is a clean, well-reasoned fix for a documented
  85%-of-the-ledger noise problem.
- **thread_integrity.py** — 0 HIGH, 1 MEDIUM (M3). The RECIPROCAL/ASYMMETRIC-LAWFUL/
  ASYMMETRIC-SUSPECT/DANGLING framework and the documented 2026-08-24 fix for the
  self-comparison bug (m12) are otherwise sound and the classify() dedup-by-unordered-pair logic
  is correct.
- **ledger.py** — 0 HIGH, 0 MEDIUM, 0 LOW beyond the informational M10 note (not re-litigated per
  instructions). `to_standards`/`from_standards`/`cross_rate` correctly short-circuit on
  unconvertible currencies; `JOULES_PER_STANDARD` importing from `physics.MATERIAL` rather than
  restating the figure is exactly the single-source-of-truth discipline the module's own comment
  claims.

CLEAN modules (no HIGH or MEDIUM findings): **local_agent.py**, **ledger.py**.
