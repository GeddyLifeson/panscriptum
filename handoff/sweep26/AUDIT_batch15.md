# AUDIT batch15 — run26

Modules (full line-by-line read, all 2,473 lines):
wiki_source.py (635) · derivation.py (558) · rosetta.py (408) · scout.py (287) ·
grounding.py (245) · coverage.py (191) · resonance.py (149)

---

## wiki_source.py

### MAJOR — `all_categories()` hard_stop=6000 truncates large wikis' category listing alphabetically, before keyword filtering (wiki_source.py:352-389)
```python
def all_categories(subdomain, min_pages=40, hard_stop=6000):
    ...
    out, cont = [], None
    while len(out) < hard_stop:
        p = {"action": "query", "list": "allcategories", "aclimit": 500,
             "acmin": min_pages, "acprop": "size"}
        ...
```
`list=allcategories` is returned by MediaWiki in alphabetical order by category name.
`hard_stop` cuts the walk off once 6000 categories (meeting `min_pages`) have been
collected — before any canonical-keyword matching happens in `discover_categories`.
This is exactly the "capped a category listing and got the letter A" anti-pattern the
file's own comments elsewhere warn about (`category_members`'s docstring, the DC/33,614
example). Empirically verified live against dc.fandom.com during this audit:

```
pages fetched: 20   total categories (min_pages=40): 10000   more remain: True
```

DC alone has 10,000+ categories at `min_pages=40` within the first 20 API pages, with
more still remaining — i.e. `hard_stop=6000` is hit and the walk stops roughly halfway
through DC's alphabet, silently. DC is one of the three sources the task brief names as
starved (0.5% cited). This cap does not affect the FIXED `CATEGORY_PROBES` list (those
are probed directly by name, independent of `all_categories`), so it is not proven to be
the sole or even primary cause of DC's low coverage — the IP-block/throughput history
documented earlier in this same file (MIN_GAP/WORKERS comments) is likely the dominant
factor — but it is a confirmed, live, real Hard Rule 0 violation for the *supplementary*
category-discovery path on any sufficiently large wiki (DC, and plausibly Thomas the Tank
Engine / SpongeBob given their category depth), and should be fixed (page fully, or rank
by size like `rank_by_size` does elsewhere in this same file, never truncate
alphabetically).

### MEDIUM — `verify_wiki_matches()` threshold is weak for short source names (wiki_source.py:224-253)
```python
distinctive = [w.lower() for w in words if len(w) > 3]
...
matched = sum(1 for w in distinctive if w in blob)
return matched >= max(1, len(distinctive) // 2), len(hits)
```
For a 2-distinctive-word source name (common: "Curse of Strahd" -> "curse","strahd"),
`len(distinctive)//2 == 1`, so only ONE of the two words needs to appear anywhere across
up to 8 search-result titles/snippets for the wiki to be accepted as verified. This is the
exact class of false-positive this function exists to prevent (per its own docstring,
`curse.fandom.com` is a live Roblox wiki that would plausibly contain the word "curse").
Sources reached only through `subdomain_candidates()` guessing (not the `WIKI_OVERRIDES`
list, which routes known-tricky 2-word names to the correct host already) are the ones
exposed to this weak bar. Recommend requiring the majority (not floor-half) of distinctive
words, or a minimum absolute match count of 2 regardless of `len(distinctive)`.

### MINOR — `resolve_wiki()` swallows only `OSError` on the hosts-file read, not `json.JSONDecodeError` (wiki_source.py:275-284)
```python
try:
    with open(_hosts_path, encoding="utf-8") as f:
        known = json.load(f).get(source_name)
except OSError:
    silence.note("wiki_source-hosts-read")
    known = None
```
The docstring immediately above this block says "a missing hosts file is tolerable" — but
`json.load` can raise `json.JSONDecodeError` (a `ValueError`, not an `OSError`) if
`WIKI_HOSTS.json` is ever malformed (partial hand-edit, an old non-atomic writer, etc.),
and that exception is NOT caught here — it propagates uncaught out of `resolve_wiki`,
crashing the whole catalogue run instead of degrading to "no known host, fall back to
guessing" as the surrounding prose implies is the intended behaviour.

### MINOR — `find_categories(limit=0, ...)` treats 0 the same as None (wiki_source.py:436)
```python
return found[:limit] if limit else found
```
`limit=0` is falsy, so this returns the FULL list instead of an empty one. Low real-world
impact (nobody calls it with `limit=0` today) but is an inconsistency with the documented
contract ("`limit` defaults to `None`. It was 6...").

### QUESTION — `_ALLCATS` cache has a double-checked-locking gap (wiki_source.py:364-389)
Two threads racing on the same `(subdomain, min_pages)` key before either has populated
the cache will both perform the full network walk. Wasteful, not incorrect (both produce
the same answer and the second write just overwrites with an identical value) — flagged
only because `find_categories` is the kind of call plausibly issued concurrently across
sources on the same wiki.

---

## derivation.py

### MAJOR — `SCAN_MODULES` (the module's own "reviewer's map" of where constants live) is missing at least 5 live modules that carry the exact class of constant the scanner exists to catch (derivation.py:476-477)
```python
SCAN_MODULES = ["assay", "feats", "cosmography", "propagation", "descending_ladder",
                "scale_theories", "chord_field", "resonance", "tempus", "ledger", "rigor",
                "custodes", "weave", "onomast", "worldseed", "address_space", "genre",
                "profile", "tiers", "grounding", "sevenfold", "burgs"]
```
Confirmed absent, and confirmed each carries module-level UPPERCASE numeric constants:

- `physics.py` — `RELATIVISTIC_ABOVE = 0.1`, and the `MATERIAL = {...}` dict whose own
  comment says it IS the anchor the ledger already cites: *"Rock's pulverisation figure is
  the anchor the Ledger Standard reuses"*. `derivation.LEDGER["material_strengths"]` is
  `Q(MEASURED, "engineering fracture and vaporisation enthalpies")` — i.e. the ledger
  entry names the very numbers `scan_constants()` can never see because `physics` isn't in
  `SCAN_MODULES`.
- `cosmology_graph.py` — `UBIQUITOUS_CUTOFF = 12` (a bare tunable threshold).
- `magnitude.py` — `LOCAL_FITS = 20000`.
- `address.py` (distinct from `address_space.py`, which IS scanned) —
  `TIER_FLOORS = (("volume", 0), ("series", 400), ("grand", 900), ("set", 3000))`.
- `pantheon.py` — `GODS = {...}` (superseded in spirit by `grounding.py` per that file's own
  docstring, but still live code with declared constants, still untracked).

This directly undercuts the file's own stated purpose: *"a reviewer can see exactly where
numbers live and catch a new undeclared one the day it is written rather than three
volumes later."* For these five modules that day has already passed and the scanner still
reports `(absent)` or simply never looks.

### Legitimate bound (reported per Hard Rule 0 instruction, not a real cap)
`derivation.py:534` — `sorted(LEDGER, key=lambda x: -depth(x))[:6]` in `main()`'s
"deepest derivation chains" printout. Stdout report sample only; `LEDGER` itself and
`check_graph()` walk every entry with no cap.

No correctness bugs found in `check_graph()`, `depth()`, or `provenance()` — cycle
detection, dangling-parent detection, and rootless-derivation detection were all traced
and are sound (standard grey/black DFS with `state` dict).

---

## rosetta.py

### MAJOR — `--mine` / `--refine` write ROSETTA.json non-atomically, unlike every sibling shared-state write in this batch (rosetta.py:364-366, 377-378)
```python
for path in (OUT, OUT.replace(".json", ".raw.json")):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
...
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
```
`rosetta.py` already `import`s `silence`, and `silence.write_json()` exists specifically
for this (per its own docstring: *"Found by the 2026-08-25 comprehensive sweep: TWELVE
call sites across ten modules were writing shared `data/` and `state/` files with a bare
`open(path, "w")` + `json.dump`..."*). `scout.py` (`_land`), `grounding.py`
(`silence.write_json`), and `coverage.py` (`silence.write_json` / `replace_retry`) were
all fixed to the atomic pattern, several explicitly dated "2026-08-25" in their comments —
`rosetta.py` was missed by that same sweep and still truncates-then-fills `ROSETTA.json`
and `ROSETTA.json.raw.json` directly. A crash mid-write, or a reader (`--check`,
`--refine`) racing a concurrent `--mine`, sees a truncated/unparseable file. `--refine`'s
own comment even names the exact failure mode this bug reproduces ("`--refine` is
destructive and was run against a stale raw copy once, which silently discarded a good
3,514-row mine").

No other issues found. `numeric_rows`' row-scoped pairing (vs. the documented
120-char-window regression), `spearman`'s tie-averaging, and `refine`'s per-host name
scoping were all traced against their own docstrings and are correct as described. All
count-shaped literals present (`[:6]`, `[:12]`, `[:4]`, `>= 8`, `< 4`, `< 100`) are either
stdout display samples or documented statistical/quality filters, not row-count
truncations of the mined data itself.

---

## scout.py

scout.py is a documented probe source (proposes URLs, fetches to verify) — its many
`except Exception: silence.note(...)` blocks around `verify()`'s network calls are the
tolerated probe shape, not swallowed real faults; each classifies its outcome (`ok`,
`why`, `code`) rather than returning something indistinguishable from success.

### MAJOR (concurrency) — read-modify-write of shared `WIKI_HOSTS.json` (F.HOSTS) with no lock, across at least 4 call sites in 2 files (scout.py:200-206)
```python
hosts = json.load(open(F.HOSTS, encoding="utf-8"))
hosts[source] = "pages:" + source
_land(F.HOSTS, hosts)
```
`_land`'s own docstring says: *"WIKI_HOSTS.json in particular is written from here AND
from two call sites in `hostcheck.py`"* — i.e. up to 4 read-modify-write sequences across
2 files can interleave. `_land`'s atomic `replace_retry` guarantees no reader ever sees a
half-written file, but it does NOT prevent a lost update: if two writers both read the map
before either replaces it, the second `_land()` call overwrites the first writer's added
key entirely. No lock (in-process or file-level) coordinates the read+mutate+write across
these sites.

### MEDIUM — HTTP 429 (rate limit) is conflated with 401/403 (access denial) as a permanent "block" (scout.py:158-165, 208-218)
```python
kind = "exists but declines readers" if e.code in (401, 403, 429) else f"HTTP {e.code}"
...
blocked = [c for c in checked if c.get("code") in (401, 403, 429)]
```
`verify()`'s own docstring draws a sharp distinction between "403 ... a real finding" and
transient conditions, but the code groups 429 in with 401/403 and files it into
`SCOUT_BLOCKED.json` as if consent were withheld — with a single fetch attempt and no
retry/backoff for 429 specifically (unlike `wiki_source._get`, which does retry 429/503).
A transient rate-limit gets permanently recorded as "material behind a storefront /
consent withheld" rather than retried.

### MINOR — `PROBE_NAMES=25` samples the first 25 names in caller order, not a representative sample (scout.py:176-178)
```python
sample = [n for n in names if n and len(n) > 3][:PROBE_NAMES]
```
`names` typically arrives from `weave_index.load_records()` entries, which for
wiki-sourced rosters trace back to `wiki_source.category_members()`'s alphabetical
MediaWiki ordering. The 25-name verification sample is therefore biased toward
early-alphabet names — the same "alphabetical-order-as-sample" trap this codebase
explicitly names and fixes elsewhere (`wiki_source.rank_by_size`'s docstring, the DC
"Abin Sur through Adolf Hitler" example). Low severity here since the sample only needs 2
hits (`MIN_NAME_HITS`) to pass, but worth ranking or shuffling rather than taking the
prefix.

### Legitimate bounds (reported per Hard Rule 0 instruction)
`scout.py:262` `prev[-40:]` — SCOUT.json is an operational run-log, not catalogue data;
rolling retention of the last 40 sweep runs is a reasonable log-rotation bound.
`scout.py:178` `sample[:18]` — only trims what's shown in the model PROMPT text; the full
25-name `sample` is still what gets used for verification (`verify(u, sample)`).
`scout.py:241` CLI `--limit` — user-supplied, defaults to None (no cap).
`scout.py:280` `[:2000]` on a `--source` single-run print — stdout only.

---

## grounding.py

Already hardened by a recent pass: `classify_source`'s `cap` parameter is explicitly
refused with a `SystemExit` documented as the fix for exactly the Hard Rule 0 violation
this batch is hunting for (*"Marvel's `origin_entries` read 153 instead of 5,012 ...
understated its own attestation 33-fold"*), and the `--write` path uses
`silence.write_json` with an explicit "ATOMIC ... 2026-08-25 whole-tree sweep" comment.
`main()` iterates `PL.records()` with no cap. Clean.

### QUESTION — `classify_text(text, top=3)` caps to 3 of the 5 possible grounding types before the confidence denominator is computed (grounding.py:112-117, 169-179)
```python
def classify_text(text, top=3):
    scores = collections.Counter()
    ...
    return scores.most_common(top)
...
top, score = ranked[0]
total = sum(s for _, s in ranked) or 1
...
"confidence": round(score / total, 3),
```
Literal "top N" shape per Hard Rule 0, and the excluded 2 of the 5 `GROUNDINGS` types'
scores are dropped from `total` too, not just from the printed runners-up — so
`confidence` is computed as a share of the top-3 total, not the full 5-type distribution.
With only 5 categories total this is very likely an intentional, benign classification
parameter rather than a catalogue-data cap (no entity or citation is ever dropped by it),
but flagging per the audit's literal Hard Rule 0 criteria for a human to confirm intent.

---

## coverage.py — SPECIAL FOCUS

**Does it count every entry?** Yes. `measure()` iterates `P.records()` (no cap) and, for
every record, every `e in r["entries"]` (no cap) — no discovery step skips files; the four
buckets (CITED/READ/NO PAGE/NO HOST) partition every entry with no `[:N]` anywhere in the
counting path.

**Can a partial run write a COVERAGE.json that looks complete?** No observed mechanism for
this. `main()` fully builds `rows` in memory via `measure()` before the single
`silence.write_json(OUT, rows, ...)` call; if `P.records()`, `json.load(open(F.HOSTS))`,
or anything else inside `measure()` raises, the exception propagates out of `main()`
uncaught and **no file is written at all** — a hard, loud failure rather than a
partial/misleading one.

**Is the write via silence.replace_retry?** Yes, both writes: the headline
`OUT`/COVERAGE.json via `silence.write_json` (which itself wraps `replace_retry`,
confirmed in silence.py) at coverage.py:185, and the perf cache
(`state/coverage_cache.json`) via `_sil.replace_retry` directly at coverage.py:76. Both
explicitly commented "ATOMIC ... 2026-08-25" / matching that sweep.

### MINOR — a transient per-file read failure silently downgrades a possibly-CITED entry to NO PAGE for that run (coverage.py:88-104)
```python
for base in (READ_CACHE, F.CACHE):
    fp = _p(base, host, name)
    try:
        mt = os.path.getmtime(fp)
    except OSError:
        continue
    ...
    else:
        try:
            with open(fp, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            silence.note("coverage.py:60")
            continue
        ...
```
If `getmtime` succeeds but the subsequent `open`/`json.load` fails (e.g. the documented
Windows "rename denied while a reader holds the file open" collision from
`silence.replace_retry`'s own docstring, hitting the *reader* side here instead of the
writer side), the bare `except Exception: continue` leaves `best` at its un-upgraded
default `("NO PAGE", 0, 0)` for that entry, which then gets counted into `c["NO PAGE"]`
and rolled into that source's `no_page`/`settled` figures for this run. This is a
transient, non-sticky effect — the entry isn't cached (`cache[rel]` is only set on
success), so the next `coverage.py` run re-reads it — but for the run in which it occurs
it silently reproduces the exact failure mode this file's own docstring calls out as the
whole reason it exists: *"The distinction between READ and NO PAGE is the whole point of
the file. Collapsing them is what made every silent failure in this project look like an
honest absence."* Recommend distinguishing "file present but unreadable this instant" from
"genuinely NO PAGE" (e.g. a short retry, or a distinct `UNREACHABLE`-like transient state)
so a read race can't quietly move an entry's headline bucket.

### Noted, not a bug
`_p()`'s `[:40]` / `[:80]` filename-sanitizing truncation (coverage.py:44-46) is the exact
same convention used at the write side in `feats.py:734-735` and `read.py:535-536,
916-917` — reader and writer agree, so this is not a coverage/discovery gap, just a shared
naming scheme (collision risk between two 80+ char names sharing the same 80-char prefix
is theoretically possible but pre-existing and out of this module's control).

**On the starvation question:** `coverage.py` does not itself order, gate, or throttle
which sources/entries get crawled — it only measures what other processes have already
written into `data/feats/` and `data/readfeats/`. No ordering/priority logic for
cataloguing work was found in this module; the DC/Thomas the Tank Engine/SpongeBob
starvation pattern is not explained by anything in coverage.py itself. (See wiki_source.py
`hard_stop=6000` above for one confirmed, real contributor on the discovery side; the
throughput/IP-block history documented in wiki_source.py's own module docstring is
independently a plausible dominant factor and lives outside this batch's scope.)

---

## resonance.py

Clean. Pure math module (HodgeRank least-squares decomposition, Proposition-1
incomparability rate, shared-stage resonance-strength lookup). No writers, no subprocess
calls, no shared mutable state, no two-writer contract exposure.

- `incomparability_rate`'s `examples` list caps at 5 (`len(examples) < 5`) — a diagnostic
  sample for the returned dict, not a truncation of `inc`/`total` (both counted over every
  pair via `itertools.combinations`, no cap). Legitimate.
- `hodge_decompose` runs a fixed 600 Gauss-Seidel iterations with no convergence check —
  an algorithmic choice (not a data cap); flagged only as a QUESTION since a
  pathological/large graph could in principle need more or fewer iterations than 600 and
  nothing checks residual convergence, but this is outside Hard Rule 0's scope.
- `resonance_strength()` has no exception handling around its `open`/`json.load` of
  `SHARED_STAGE_GRAPH.json` — raises loudly on a missing/malformed file, which is the
  correct (non-silent) behaviour for a read-only diagnostic function.

---

## Summary table

| File | MAJOR | MEDIUM | MINOR | QUESTION |
|---|---|---|---|---|
| wiki_source.py | 1 | 1 | 2 | 1 |
| derivation.py | 1 | 0 | 0 | 0 |
| rosetta.py | 1 | 0 | 0 | 0 |
| scout.py | 1 | 1 | 1 | 0 |
| grounding.py | 0 | 0 | 0 | 1 |
| coverage.py | 0 | 0 | 1 | 0 |
| resonance.py | 0 | 0 | 0 | 1 |
