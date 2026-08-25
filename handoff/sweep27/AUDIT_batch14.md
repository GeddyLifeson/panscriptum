# BATCH 14 AUDIT — run27, sweep agent

Modules read in full, every line:
- src/wiki_source.py — 652 lines
- src/chain.py — 497 lines
- src/generate.py — 421 lines
- src/pantheon.py — 308 lines
- src/tempus.py — 254 lines
- src/chord_field.py — 203 lines
- src/scope.py — 152 lines

Total: 2,487 lines.

No files were edited. This is a find-only pass.

---

## wiki_source.py

### W1. `category_members` silently returns a partial roster on any transient API failure — [HIGH][CONFIRMED]
`src/wiki_source.py:549-573`, specifically the `except Exception: silence.note(...); break` at lines 566-568.

```python
try:
    d = _api(subdomain, p)
except Exception:
    silence.note("wiki_source.py:376")
    break
out += [m["title"] for m in d.get("query", {}).get("categorymembers", [])]
```

The pagination loop walks `cmcontinue` pages of 500 until MediaWiki stops handing back a
continuation token. `_get()` already retries each individual HTTP call twice with backoff before
raising, so by the time this `except` fires the request has already failed persistently (not a
single dropped packet). When it fires mid-walk — e.g. on page 40 of a 68-page walk over DC's
33,614-member Characters category — the function does not retry the walk, does not raise, and
does not flag the result as partial. It returns exactly the titles collected so far as `out`,
which is bit-for-bit indistinguishable to every caller from "this category genuinely has 20,000
members." `catalogue_web.py` (not in this batch) calls this with `limit=None` expecting the
honest full list and has no way to know it got a truncated one.

This is functionally the same failure Hard Rule 0 forbids — a smaller universe wearing the shape
of the real one — except the mechanism is a transient/persistent network error rather than a
hardcoded number. Given the multi-hour walk times documented in this same file's own comments
(rate limiting at 0.15s/request, tens of thousands of titles for one DC category), the cumulative
probability of hitting at least one such failure during a full run is not small. This is a
concrete, previously undocumented candidate for why DC sits at 0.5% catalogued: a category walk
that stops early looks exactly like a category that was small to begin with, with silence.note
the only trace.

Failure scenario: DC's `Characters` category walk hits one persistent 503/timeout at page 40/68.
`category_members` returns ~20,000 of 33,614 titles, no error surfaces, and the catalogue run
proceeds as if that were the whole category.

### W2. `all_categories` returns (and uses) a partial category listing for the CURRENT call even though it no longer caches it — [MEDIUM][CONFIRMED]
`src/wiki_source.py:384-406`, especially:
```python
except Exception:
    silence.note("wiki_source.py:all_categories")
    complete = False
    break
...
if complete and hard_stop is None:
    with _ALLCATS_LOCK:
        _ALLCATS[key] = out
return out
```
The m143 fix (confirmed present and correct) stops a partial result from being memoized as if it
were the truth for the rest of the process — that part of the fix is complete. But the function
still `return out` unconditionally, so the *caller of this specific invocation* — e.g.
`discover_categories`, called once per canonical class inside `find_categories` — still receives
and acts on a truncated category list, with no `complete` flag exposed to it. A source can
therefore still be undercatalogued for the entirety of one run even though the next run gets a
clean slate. This is the same class of bug as W1, one file over, and the two share exactly the
mechanism the EXTRA FOCUS question was asking about ("a sibling construction in the same file
still truncates").

### W3. `resolve_wiki`'s except clause doesn't catch the exception a malformed WIKI_HOSTS.json actually raises — [MEDIUM][CONFIRMED]
`src/wiki_source.py:275-284`:
```python
try:
    with open(_hosts_path, encoding="utf-8") as f:
        known = json.load(f).get(source_name)
except OSError:
    silence.note("wiki_source-hosts-read")
    known = None
```
`json.load()` raises `json.JSONDecodeError` (a `ValueError` subclass, not an `OSError`) on a
truncated or malformed file. The comment directly above this block states the design intent in
plain language: "A missing hosts file is tolerable; a missing variable is not, so only the file
operations sit inside the try" — i.e. the intent is that any file-read failure should degrade
gracefully to guessing. The code only delivers that for a missing/unreadable file, not for a
present-but-corrupt one; a JSONDecodeError propagates uncaught and crashes `resolve_wiki`
entirely (and by extension the cataloguing run for every source still to be resolved).

This is not hypothetical: `WIKI_HOSTS.json` is confirmed to be written from three separate call
sites across two modules (`hostcheck.py`'s own comments say so directly: "WIKI_HOSTS.json is
written from THREE call sites in two modules"). It is exactly the kind of file that is more likely
than most to occasionally be read mid-update by another process. If any of those three writers is
not fully atomic, or if the file is ever manually edited and left invalid, `resolve_wiki` does not
degrade — it crashes, which is a worse outcome than the "missing file" case the code was written
to guard against.

### W4. `min_pages=40` default filters out small legitimate categories reached only via keyword discovery — [LOW][SUSPECTED]
`src/wiki_source.py:352, 409-423, 426`. `discover_categories`/`find_categories`'s discovery half
filters `all_categories(subdomain, min_pages=40)` results by size, so a genuinely small wiki whose
cast lives in a category under 40 pages, under a name not on the `CATEGORY_PROBES` list, is never
surfaced at all. The direct-probe half of `find_categories` (checking literal names like
"Characters") is unaffected since it doesn't go through `all_categories`. This mainly hurts thin
wikis' recall, not DC-scale sources; flagging as a question rather than a confirmed defect since a
40-page floor may be a deliberate noise filter (many wikis have dozens of trivial stub categories).

### W5. `rank_by_size`'s `top=` parameter is a live truncation capability — [LOW][CONFIRMED, unused]
`src/wiki_source.py:596-633`, `return ranked[:top] if top else ranked`. Every call site found in
the tree (`catalogue_web.py:105,213`) passes `top=None` with an explicit "rank, never truncate"
comment, so this is not presently firing. Noting only because the capability exists and a future
caller passing a real value would silently reintroduce a Hard Rule 0 violation with no guard.

---

## chain.py

### C1. `write_result` truncates `unmatched` to the top 40 before writing CHAIN.json — [HIGH][CONFIRMED — KNOWN-OPEN, reconfirmed]
`src/chain.py:108`:
```python
"unmatched": (unmatched.most_common(40) if hasattr(unmatched, "most_common")
              else (unmatched or [])),
```
Still present exactly as described in the known-open list. Confirmed this only fires on the
`collections.Counter` branch (chain.main's own call, line 491); a caller that already hands in a
plain list (per the docstring, `pipeline.phase_chain` may) skips the truncation via the `else`
branch, so the cap is asymmetric between the two documented writers of this file — one caller's
data gets cut to 40, the other's doesn't.

### C2. Unmatched-name diagnostic uses a truncated string as its counting key — [MEDIUM][CONFIRMED — NEW]
`src/chain.py:352-354`:
```python
for side, k in ((w, wk), (l, lk)):
    if k not in idx:
        unmatched[side[:40]] += 1
```
This is the identical bug class as m37 (the `sentence[:120]` dedup key in `harvest()`, already
fixed and explained at length in the comment at lines 210-217 of this same file): truncating a
string before using it as a dict/Counter key lets two different values collide. Here, two
distinct unmatched names that share the same first-40-characters (a long title/epithet, or a name
with a long parenthetical) get merged into a single diagnostic bucket, undercounting how many
distinct unresolved names actually exist. Lower severity than C1 because this only corrupts the
*diagnostic* unmatched-name counts, not the edges themselves (the graph keys off `WI.norm(w)` and
`WI.norm(l)` in full, untruncated, at line 340) — but it is the exact pattern the sweep brief
calls out ("a fix applied to one file while the identical construction... was never visited"),
reappearing in the very file where the sibling bug was already found and fixed.

### C3. `adjudicate_mutuals` mis-handles a mutual pair where only one side's sentence self-dates — [MEDIUM][SUSPECTED]
`src/chain.py:405-420`:
```python
ea, eb = ID.epoch_of(sa), ID.epoch_of(sb)
if ea != eb:
    for (x, y), ep in (((w, l), ea), ((l, w), eb)):
        if not ep:
            continue
        n = out.pop((x, y))
        out[(ID.node(x, epoch=ep), y)] += n
    split += 1
    ...
else:
    ...  # left standing: genuine disagreement
```
The docstring frames this as a two-case decision: both sides dated differently -> split by
epoch; neither dates itself -> left standing as a genuine disagreement. The code as written has
a third, unaddressed case: one side dates itself and the other doesn't (`ea` truthy, `eb` falsy,
or vice versa). `ea != eb` evaluates True there too (comparing a string to `None`/`""`), so the
code takes the "split" branch — but only the dated side actually gets re-keyed (`if not ep:
continue` skips the undated side), leaving the undated edge under its original, un-epoched node.
The effect: the code silently assumes the undated sentence describes a *different* point in the
subject's history than the dated one, with no evidence for that — it could just as easily be the
same moment, in which case this is a real contradiction being hidden behind a re-key rather than
surfaced, which is precisely the fabrication the docstring says the "left standing" path exists to
avoid. I could not fully verify `ID.epoch_of`'s exact contract (it lives in `identity.py`, outside
this batch) so I'm marking this SUSPECTED rather than CONFIRMED, but the gap is visible from
`chain.py`'s own control flow regardless of what `epoch_of` returns.

---

## generate.py

### G1. `catalog`/`failures` dicts are read once, then written back periodically with no cross-process lock — [MEDIUM][CONFIRMED (code pattern); impact depends on whether concurrent invocation happens]
`src/generate.py:322-323` loads `catalog` and `failures` into memory once at start; `save_json`
(line 53-58, itself atomic via `silence.write_json`) writes the *whole in-memory dict* back every
5 completions (line 409) and on every failure (line 379) and at the end (line 412). If two
`generate.py` processes are ever running at once — e.g. a user re-running against a different
manifest without noticing a prior run is still active, or a supervisor restart racing a still-
live process — the second process's periodic save overwrites the first process's on-disk
progress with its own (older, from-the-first-load) copy of every job the first process wrote
after the second process started. The individual `save_json` writes are atomic (no torn file),
but the read-modify-write cycle across the two processes is not exclusive, so this is a genuine
lost-update race, not a corruption race. Severity is capped at MEDIUM because I found no evidence
in this batch that concurrent `generate.py` invocations are an expected or common operating mode
— flagging because nothing in the code guards against it either.

### G2. Raw chapter `.md` files are written with a bare `open(...,'w')`, not the atomic pattern used everywhere else in this file — [LOW][CONFIRMED, currently low-impact]
`src/generate.py:382-384`:
```python
raw_path = os.path.join(raw_dir, safe_filename(job["address"], "md"))
with open(raw_path, "w", encoding="utf-8") as f:
    f.write(f"<!-- {job['address']} -->\n\n{text}")
```
Contrasts with `save_json`'s explicit comment two lines above it in the same file about why
truncate-then-fill is dangerous for files other code reads mid-run. Traced the actual risk:
`catalog.py`'s `read` command (`src/catalog.py:89-95`) only opens `raw_path` after looking it up
in `catalog.json`, and the catalog entry for a given address is only written (line 389) *after*
this raw-file write completes, with `catalog.json` itself saved atomically and only periodically
— so under the current call sequence a reader going through `catalog.py` cannot observe a torn
raw file. Flagging as LOW/a latent hazard rather than a live bug: it deviates from the file's own
stated principle, and would become a real torn-read risk the moment any future code reads
`output/raw/*.md` directly (by globbing the directory, for instance) rather than exclusively via
`catalog.json`.

### G3. `_covered()`'s loose first/last-word match can register an absent entry as present — [LOW][SUSPECTED]
`src/generate.py:163-176`. Documented as deliberately loose. For a short (two-word) entry name,
if both words happen to appear elsewhere in the block for unrelated reasons, `_covered` returns
True for an entry that was never actually written, silently defeating the retry-then-fail
mechanism `generate_job` relies on to guarantee no entry goes missing. Noted as a design
trade-off the code itself acknowledges ("Loose on purpose"); flagging only because it is the one
place in this file where the anti-silent-omission machinery could itself be fooled.

---

## pantheon.py

### P1. Band-label lookup in `main()`'s print loop is missing several bands — [LOW][CONFIRMED, cosmetic only]
`src/pantheon.py:282-286`:
```python
label = {"M8": "multiverses", "M7": "a universe", "M4": "a stellar system",
         "M3": "a planet", "M2": "a continent"}.get(b, "")
```
No entries for M0, M1, M5, M6, M9, M10. Since `main()` merges in `Z_FIGHTERS.json` (line 263-269)
whose entries can plausibly land at M5/M6 (galaxy-tier) or M1 (Ladder floor), a band header for
those prints with an empty label — cosmetic gap only (`  --- M6                  ----...`), no
data loss, no crash. Confirmed by reading the dict literal directly against the `A.WEIGHTS`/
`LADDER` range implied by the CLAUDE.md's stated M0-M10 scale.

No correctness bugs, no caps, no shared-file writes with racing writers, and no
two-writer-contract issues found elsewhere in this file — it is a small hand-authored static
dataset plus a compute/print pass, and the axis set used in `--full` printing (11 keys) was
checked against `assay.WEIGHTS` (8 physical + 3 faculty = 11) and matches for all six entries, so
no `KeyError` risk there.

---

## tempus.py

No new findings. Read every function; all the arithmetic (Bradley-Terry is chain.py's, not this
file's) is internally consistent, and cross-checked against its own docstrings:
- `is_present_at` and `concordance_now`'s stated "lower-rung observers have a LARGER now" claim
  is consistent with the `event_mark >= observer_rung` comparison both functions actually use.
- `band_resolution()` (lines 182-210) — the known-open item asked me to confirm, not
  re-litigate. Confirmed: it correctly reuses the M(n-1)->M(n) width for the top-of-Ladder band
  (`i + 1 < len(LADDER)` else-branch, lines 206-209) rather than attempting a same-band ratio
  that would degenerate to `log2(1) == 0`. This is the fallback `assay.axis_score` is reported to
  lack (per the batch brief); tempus.py's own version is present and matches its docstring.
- `rung_description_length`'s `L_r(M0) == 0` degenerate case is explicitly named by its own
  docstring as the reason `band_resolution` exists as a separate function — consistent, not a
  contradiction.

No file writes, no caps on any listing, no shared state — this module is pure computation over
static tables imported from `assay.py`.

---

## chord_field.py

No findings. Static physics-adjudication reference table (`ADJUDICATIONS`) plus five small pure
functions. Checked the two formulas that could plausibly be wrong:
- `landauer_floor`: `bits * k * T * ln2` — correct per-bit Landauer limit, scaled linearly, no
  off-by-one.
- `critical_power_self_focus`: `3.77 * L^2 / (8*pi*n0*n2)` — matches the standard Marburger
  critical-power formula for Kerr self-focusing.
No caps, no writes, no concurrency, no two-writer surface.

---

## scope.py

### S1. `titles[:8]` caps the pages that contribute to a wiki's scope signal — [HIGH][CONFIRMED — KNOWN-OPEN, reconfirmed]
`src/scope.py:81`: `pages = F.fetch(host, titles[:8])`. `titles` can hold up to 12 deduped
candidates (4 queries x srlimit 3, minus duplicates). This is a straightforward Hard Rule 0 cap
on an evidentiary listing — pages 9-12, when they exist, never contribute their word counts to
the tier signal at all. In practice this caps out more often on well-documented (large) wikis,
which is the opposite end of the spectrum from the thin-wiki problem S2 below describes — both
are real, and they are two different symptoms of the same file.

### S2. The no-signal fallback reintroduces the exact frequency bias the module's docstring names as wrong — [HIGH][CONFIRMED — KNOWN-OPEN, reconfirmed with mechanism]
`src/scope.py:86-93`:
```python
best = None
for lab, _, band in _RE:
    if counts[lab] >= MIN_MENTIONS:
        best = (lab, band)
if best is None:                       # nothing clears it: fall back to the commonest tier
    lab = max(counts, key=counts.get)
    band = dict((l, b) for l, _, b in _RE)[lab]
    best = (lab, band) if counts[lab] else None
```
The module's own header (lines 25-30) states the design principle in italics: scope must be read
"Not by frequency... The signal is the HIGHEST tier that appears with real usage, not the
commonest." The fallback branch directly contradicts that: `max(counts, key=counts.get)` selects
whichever tier has the single highest raw mention count, with **no floor at all** — it can fire
on a count as low as 1 (the `if counts[lab] else None` guard only excludes the all-zero case).
This branch fires precisely when no tier reaches `MIN_MENTIONS=10`, which is systematically more
likely for a thin wiki: fewer search hits pass the `size > 1200` filter (line 76), fewer than 8
survive to line 81, less total text is fetched, and an absolute threshold of 10 mentions becomes
much harder to clear regardless of which tier is actually load-bearing in the setting. So the
exact sources this function is least equipped to read correctly (thin wikis) are the ones most
likely to fall through to the one behavior its own docstring calls out by name as wrong.

### S3. `build()` permanently poisons a host after one failed or empty scope lookup — [HIGH][CONFIRMED — NEW]
`src/scope.py:102-120`:
```python
todo = sorted({h for s, h in hosts.items() if h and h not in out
               and not F.is_wikipedia(h)})
for i, h in enumerate(todo, 1):
    try:
        sc = scope_for(h)
    except Exception:
        silence.note("scope.py:110")
        sc = None
    out[h] = sc
    ...
```
`out[h] = sc` runs unconditionally, including when `sc` is `None` — whether from the exception
branch or from `scope_for` itself returning `None` (line 79-80, when the search step finds zero
qualifying titles; this can be a genuine "no signal" result or a transient search-API hiccup
inside `feats.api`, which I could not fully verify since `feats.py` is outside this batch). Once
that happens, `h` becomes a *key* in `out` with a `None` value, and every subsequent run's
`todo` computation (`h not in out`) treats that host as already handled — it is skipped forever,
with no retry path short of manually editing `data/SCOPE.json` to delete the key. This is the
identical failure-memoization pattern the batch brief's own known-open list credits `all_categories`
(m143, `wiki_source.py`) with having already fixed — "a failed walk is never memoised" — and it
reappears here, unfixed, in a sibling file one directory over. Concretely: the very first time
`scope_for(h)` hits a slow network day and its search calls come back empty, that source is
locked out of ever receiving a Magnitude ceiling from this mechanism again, for the life of
`SCOPE.json`.

---

## Summary of severities

- HIGH: W1, C1 (known-open), S1 (known-open), S2 (known-open), S3
- MEDIUM: W2, W3, C2, C3 (suspected), G1
- LOW: W4 (suspected), W5, G2, G3 (suspected), P1
