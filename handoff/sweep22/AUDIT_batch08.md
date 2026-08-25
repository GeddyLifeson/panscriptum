# Batch 08 audit — hostcheck.py, completeness.py, tiers.py, feats_index.py, propagation.py, scope.py

Full line-by-line read of all six files, top to bottom, no sampling. `hostcheck.py`'s two
already-confirmed bugs (m93: `probe()` RAW-mode branch returns `rate=0.0` on network failure at
~line 134-139; m94: `null_rate()` coerces a failed probe to a fabricated 0.0 baseline at
~line 418-422) are **not** re-reported below per instructions, but the hunt for a third instance
of the same class turned one up in `scope.py` — see scope.py H1.

---

## HIGH

### scope.py:108-118 — a transient network failure becomes a permanent "no scope" fact (the requested third instance)

VERIFIED.

`scope_for()` already conflates two different situations into one `None`: a wiki with genuinely
no clear cosmology signal, and a wiki where every `F.api()` call failed at the transport level.
`feats.api()` (imported as `F.api`) is documented at feats.py:121 to return `None` after
exhausting its retries on any transport failure — indistinguishable from an empty, legitimate
search result:

```python
def scope_for(host, verbose=False):
    titles, seen = [], set()
    for q in QUERIES:
        d = F.api(host, {"action": "query", "list": "search", "srlimit": "3", "srsearch": q})
        for row in (d or {}).get("query", {}).get("search", []):
            ...
    if not titles:
        return None
```

`build()` then writes this ambiguous `None` to disk regardless of cause, and adds a second,
independent way to produce the same `None` (an uncaught exception from `scope_for` is also
turned into `sc = None`):

```python
def build(records, hosts):
    out = {}
    if os.path.exists(OUT):
        out = json.load(open(OUT, encoding="utf-8"))
    todo = sorted({h for s, h in hosts.items() if h and h not in out
                   and not F.is_wikipedia(h)})
    for i, h in enumerate(todo, 1):
        try:
            sc = scope_for(h)
        except Exception:
            silence.note("scope.py:110")
            sc = None
        out[h] = sc                                    # <-- written unconditionally
        ...
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    return out
```

The critical part is `todo`'s membership test: `h not in out`. Once a host has *any* entry in
`out` — including `None` — it is **permanently excluded** from every future `--build` run. A
single throttled or dropped connection during one run therefore hardens into a durable "this
wiki has no scope" fact that nothing in the codebase will ever re-probe, unless an operator
manually edits `data/SCOPE.json`. This is exactly the failure class already confirmed in
`hostcheck.py` (m93/m94) — a failed request becoming a durable negative fact — located in a third
file, and arguably worse here because of the permanent no-retry mechanism (m93/m94 at least get
re-probed on the next `sweep()` run; this host never gets re-probed at all).

**Repair sketch:** distinguish "probed, no signal" from "probe failed" — e.g. store failures in a
separate key, or only add `h` to `out` when `sc is not None`, or store a `{"ok": False}` sentinel
that `todo`'s filter treats as retriable. `scope_for()` itself should also propagate a
transport-failure signal (e.g. raise, or return a distinguishable sentinel) rather than folding
"no titles found" and "no titles because the API never answered" into the same `None`.

### scope.py:118 — bare `open(path, "w")` on a shared, multi-reader data file

VERIFIED.

```python
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
```

`OUT` is `data/SCOPE.json`. It is read by `magnitude.py` and `pipeline.py` (confirmed by grep).
This is the exact m6-pattern write the rest of the tree (`hostcheck._land`, `pipeline.land_json`,
`completeness.land`) was built to stop doing: truncates before serialising, and races any reader
holding the file open on Windows. Should go through `silence.replace_retry` (tmp file + atomic
replace), the same as every other shared artifact in this project.

### feats_index.py:148 — directory→host reversal is not the inverse of the forward encoding; breaks the join for every hyphenated host, and produces a false diagnosis in the module's own docstring

VERIFIED, reproduced empirically.

```python
for host_dir in sorted(os.listdir(root)):
    p = os.path.join(root, host_dir)
    if not os.path.isdir(p):
        continue
    host = host_dir.replace("_", ".").lower()
```

The forward transform that produced these directory names (`read.py:535`, `feats.py:734`) is
`re.sub(r"[^A-Za-z0-9]+", "_", host)` — it collapses **every** run of non-alphanumeric characters,
including both `.` and `-`, into a single `_`. `load_index()`'s reversal assumes every `_` came
from a `.` and blindly maps it back, which is correct only for hosts with no hyphen.

Confirmed against real data — `data/WIKI_HOSTS.json` genuinely contains four hyphenated hosts:

```
'Date A Live'                 -> 'date-a-live.fandom.com'
'Sakamoto Days'                -> 'sakamoto-days.fandom.com'
'The Amazing Digital Circus'   -> 'the-amazing-digital-circus.fandom.com'
'Uncle Grandpa'                -> 'uncle-grandpa.fandom.com'
```

Their `data/readfeats/` directories exist on disk (`date_a_live_fandom_com`,
`sakamoto_days_fandom_com`, `the_amazing_digital_circus_fandom_com`, `uncle_grandpa_fandom_com` —
14 files total, matching exactly the "14 records" the module's own docstring cites), but running
the actual code shows `load_index()` reconstructs them as `date.a.live.fandom.com`,
`sakamoto.days.fandom.com`, `the.amazing.digital.circus.fandom.com`, `uncle.grandpa.fandom.com` —
none of which match the correct forms held (unmodified, straight from JSON) in
`host_to_sources()`. Only a fifth, non-hyphenated host in the same grep (`theamazingworldofgumball
.fandom.com`) reconstructs correctly, confirming the break is specific to hyphenated hosts.

The module's own docstring (lines 33-38) misdiagnoses this as a **data gap**:

> "14 records / 222 feats are hosts with no `WIKI_HOSTS` entry at all (the amazing digital
> circus, date a live, sakamoto days, uncle grandpa) -- sources whose host was never recorded."

That is factually wrong — `WIKI_HOSTS.json` has a valid entry for all four. `audit()`/`main()`
compound the false diagnosis by printing `"NOT IN WIKI_HOSTS"` for these hosts (line 257:
`known = "known host" if h in host_to_sources() else "NOT IN WIKI_HOSTS"` — using the
mis-reconstructed `h`, which is never a key in `host_to_sources()`).

**Real impact:** `manifest_builder.py:317` calls `feats_index.feats_for_source(source_name,
record)` per source when building chapter jobs. For these four sources the join silently returns
`[]` even though the mined evidence exists on disk and the host mapping is correct — their
generated volumes get zero attested feats, invisibly.

**Repair sketch:** stop trying to invert a lossy transform. Either (a) store the true host string
inside each readfeats record (many already carry `rec.get("host")` — check whether it is written
correctly at mining time and prefer it over the directory-name guess), or (b) change the forward
encoding to be reversible (e.g. escape `-` differently from `.`), or (c) build `host_to_sources()`
keyed by the *same* lossy transform on both sides instead of reversing one side.

### tiers.py:338-340 — bare `open(out, "w")` on TIERS.json; the exact bug already fixed elsewhere for the same file

VERIFIED.

```python
out = os.path.join(HERE, "data", "TIERS.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(charted, f, indent=2, ensure_ascii=False)
```

`TIERS.json` is read by `address_space.py`, `profile.py`, `sevenfold.py`, `verify_math.py`, and
`pipeline.py` (which reads phase 5's `TIERS.json` from phase 6, same run). `pipeline.py` itself
writes this identical file through `land_json()`, whose own docstring names this precise pattern
as an already-diagnosed-and-fixed defect:

> "The later phases wrote their artifacts as `json.dump(obj, open(path, "w"), ...)`: not atomic,
> and the handle never explicitly closed either... a crash or a slow reader mid-write does not
> just cost a cycle, it feeds the next phase a truncated file... (BUGS m6, 2026-08-24.)"

`tiers.py`'s own standalone `main()` entry point still carries the m6 pattern for the same file.
Anyone running `python tiers.py` directly (rather than through `pipeline.py`'s phase) reintroduces
the exact race pipeline.py went out of its way to close. Should call `silence.replace_retry` (or
`pipeline.land_json`) instead.

### completeness.py:71-119 — unguarded shared dict, mutated and JSON-serialised (iterated) concurrently across threads with no lock anywhere in the file

VERIFIED (structurally — no `threading` import or `Lock` exists in the file; `audit()` runs
`category_size_probe()` from up to `workers` (default 6) concurrent `ThreadPoolExecutor` workers,
each of which can call `category_size_probe()` for multiple category candidates per source).

```python
_CS_CACHE = {"loaded": False, "d": {}}
...
def category_size_probe(sub, category):
    ...
    cache = _cs_load()                 # returns the SAME dict object every time, not a copy
    cache[k] = {"at": time.time(), "n": got}
    try:
        tmp = _CS_CACHE_P + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache, f)        # iterates `cache` while other threads may be mutating it
        silence.replace_retry(tmp, _CS_CACHE_P)
    except Exception:
        silence.note("completeness.py:cs-cache")
    return got, None
```

`_CS_CACHE["d"]` is one process-global dict. `audit()`'s `work()` calls
`category_size_probe(sub, cand)` for up to 8 category candidates per source, and multiple sources'
`work()` calls run concurrently under `ThreadPoolExecutor(max_workers=workers)`. Every one of
those calls can both insert a new key into `cache` (`cache[k] = ...`) and serialise the whole
dict (`json.dump(cache, f)`) in the same brief window, with no lock protecting either operation.
`json.dump()` iterates the dict internally; a second thread inserting a **new** key into the same
dict object while that iteration is in progress raises `RuntimeError: dictionary changed size
during iteration` in CPython. This is a live, intermittent crash risk in a code path that runs
every audit pass ("the always-remedy runs this audit every foreman round" per the module's own
`category_size()` docstring), not merely a theoretical one.

**Repair sketch:** guard `_CS_CACHE["d"]` mutation and the read used for `json.dump()` with a
`threading.Lock` (the pattern `hostcheck.py`'s `_NULL_LOCK` already uses for a similar cache), or
snapshot `dict(cache)` before serialising while still holding a lock during the copy.

### completeness.py:298-331 — an uncatalogued source reads as a measured 0.0% coverage row, not as "not yet catalogued"

VERIFIED by code reading.

```python
rec = byslug.get(str(src).lower()) or byslug.get(str(src).lower().replace("-", " "))
got = (rec or {}).get("total")
persons = None
if rec:
    persons = sum(v for k, v in rec["by_category"].items() if k.startswith("Persons"))
cov = (persons / best) if (persons and best) else 0.0
why = None
if not sizes:
    why = (...)
elif shared[host] > 1 and (primary.get(host) or (None, None))[0] != src:
    why = (...)
elif cov > 1.0:
    why = (...)
return {"source": src, "host": host, "wiki_persons": best, "wiki_categories": sizes,
        "catalogued_total": got, "catalogued_persons": persons, "probe_failures": failed,
        "probes_run": len(probes), "coverage": cov, "unreliable": why}
```

`todo` (line 221) is built from `WIKI_HOSTS.json` — every source with a Fandom host — **not**
from `catalogued_counts()`, so a source can have a host but no record file yet in
`data/records/`. When that happens `rec` is `None`, `persons` stays `None`, and `cov` evaluates to
`0.0` (since `persons and best` is falsy). None of the three `why` branches trigger for this case
(sizes is non-empty because a real category size WAS found on the wiki; `shared[host]` and
`cov > 1.0` don't apply), so `why` stays `None` and the row is written to `COMPLETENESS.json` as
`unreliable: None` — i.e. reported as a *reliable, measured* 0.0% coverage source, identical in
shape to a source that really was catalogued and genuinely caught zero of its cast.

This is exactly the failure class the module's own docstring opens by describing at length (a
real absence reading as "not in that fiction" rather than "not yet measured/catalogued") — except
here it originates inside `completeness.py`'s own coverage computation rather than upstream in the
wiki-catalogue step. `main()`'s aggregate totals (`good = [r for r in rows if not r["unreliable"]]`,
then summed into `total_have`/`total_wiki`) would then quietly count a never-catalogued source as
"measured, 0 persons caught" and drag the corpus-wide coverage percentage down with a number that
is not actually a measurement of the library's completeness — it is a measurement of the library
not having gotten to that source yet.

**Repair sketch:** add a fourth `why` branch: `elif rec is None: why = "no catalogue record for
this source yet -- not measured"`.

### hostcheck.py:918-919 — `--purge` CLI help text asserts a safety check the function's own docstring says was removed

VERIFIED.

```python
ap.add_argument("--purge", action="store_true",
                help="remove rosters the audit rejected AND whose host was independently rejected")
```

`purge()`'s own docstring (lines 642-647) explicitly disclaims this:

> "The safety here is the HUMAN, not a second automated condition. An earlier docstring claimed
> the code also required the host to have been independently rejected; it never did (the check
> was loaded and unused), and pretending a safeguard exists is worse than naming the real one:
> nothing is purged except sources a person explicitly listed with `--source`, after reading the
> roster."

The `--help` text shown to an operator running `hostcheck.py --purge --help` (or reading
`ap.print_help()`) still makes the exact false claim the function's docstring was corrected to
stop making — that the tool independently double-checks host rejection before purging. An
operator relying on the CLI's own stated behavior, rather than reading the source, would believe
a safeguard exists that does not. This is a documentation bug with a real safety-adjacent
consequence: it advertises a check on a destructive, roster-emptying operation that isn't there.

**Repair sketch:** update the help string to match the corrected docstring, e.g. `"remove
rosters for exactly the --source names given, after a human has read the roster (the audit alone
never triggers a purge)"`.

### hostcheck.py:465-482 — a failed aboutness check (`about=None` from a network error) is indistinguishable from "aboutness veto not needed", silently permitting a "holds" verdict

VERIFIED by code reading; same general failure family as m93/m94 but inverted polarity (enables
a positive verdict rather than fabricating a negative one), so reported separately rather than as
the requested third instance.

```python
r["about"] = (relevance(host, r.get("titles") or [], source)
              if r["hits"] and base >= ABOUT_VETO_ABOVE else None)
...
elif r["about"] is not None and r["about"] < ABOUT:
    r["verdict"] = "NAMES ONLY"
elif r["lift"] >= GOOD_LIFT:
    r["verdict"] = "holds"
```

`relevance()` returns `None` in two situations that this code cannot distinguish: (1) the
aboutness check legitimately does not apply (handled explicitly above by the `base >=
ABOUT_VETO_ABOVE` guard), and (2) the check *was* required (`base >= ABOUT_VETO_ABOVE` was true)
but the page-body fetch inside `_bodies()` failed at the transport level — `_bodies()` swallows
its own exception and returns `[]`, and `relevance()` turns an empty body list into `None` (line
220-221: `if not bodies: return None`). Both paths produce the same `r["about"] = None`, and the
verdict logic at line 477 treats `None` as "no veto to apply" in both cases. A transient network
failure during the one check specifically designed to catch a generous-but-wrong host (a host
that answers for half of all names) can therefore let that host through as `"holds"` without the
veto that was supposed to gate it.

**Repair sketch:** give `relevance()`/`_bodies()` a way to signal "check failed" distinct from
"check not applicable", and treat a failed-but-required check as `"too few names to judge"` or
similar rather than silently skipping the veto.

---

## MEDIUM

### hostcheck.py:373-387 — bare `except Exception` on the master entity roster silently turns a load failure into an apparently-benign empty sweep

VERIFIED.

```python
def entities_by_source():
    path = os.path.join(HERE, "data", "CHARACTER_SWEEP.json")
    by = collections.defaultdict(list)
    try:
        with open(path, encoding="utf-8") as f:
            rows = json.load(f)
    except Exception:
        silence.note("hostcheck.py:entities_by_source")
        return by
    ...
```

If `CHARACTER_SWEEP.json` is missing, empty, or corrupt, `entities_by_source()` returns an empty
`defaultdict` with no visible error beyond a `silence.note` call. `sweep()`'s `todo` list is built
from `by.get(s)` being truthy, so an empty `by` makes `todo` empty and `unassigned` empty too
(since `unassigned` also requires `by.get(s)`). The run then prints `"0 hosts probed, 0 do not
hold their fiction"` — a misleadingly clean-looking result rather than a loud failure, for what is
actually a total inability to read the roll's own roster file.

**Repair sketch:** at minimum, print to stderr (not just `silence.note`, which is easy to miss)
when the roster file fails to load, since every downstream measurement in this module depends on
it.

### hostcheck.py:390-423 — `null_rate()` check-then-act race on `_NULL_CACHE` (duplicate work, not corruption)

VERIFIED — a genuine race, but benign in outcome (wasted network calls, not data corruption,
since the cache is protected during the actual read/write of individual keys by `_NULL_LOCK`).

```python
with _NULL_LOCK:
    if host in _NULL_CACHE:
        return _NULL_CACHE[host]
foreign = []
...
r = probe(host, foreign) or {}
...
with _NULL_LOCK:
    _NULL_CACHE[host] = rate
return rate
```

Two threads probing the same host at nearly the same time (plausible: `sweep()`/`adopt()` run
`score()` for many `(source, host)` pairs concurrently under `ThreadPoolExecutor`, and several
sources can legitimately share one host — the module's own docstring says so) can both miss the
cache check and both perform the full `probe()` call redundantly. Not incorrect, just wasted
network traffic against hosts this module is already careful to be polite to (see `_get()`'s own
extensive docstring about throttling).

### scope.py:90-93 — fallback path contradicts the module's own stated "not by frequency" design thesis

VERIFIED.

The docstring's "READING THE SIGNAL" section states as its central design claim:

> "Not by frequency... The signal is the HIGHEST tier that appears with real usage, not the
> commonest, because a story that discusses universes at all is a story where universes are in
> play."

But the fallback branch, which fires whenever no tier clears `MIN_MENTIONS`, is explicitly
frequency-based:

```python
if best is None:                       # nothing clears it: fall back to the commonest tier
    lab = max(counts, key=counts.get)
    band = dict((l, b) for l, _, b in _RE)[lab]
    best = (lab, band) if counts[lab] else None
```

For any source too sparsely attested to clear the floor on any tier, the tool reintroduces
exactly the frequency bias the docstring's own worked example (Marvel scoring "planet" over
"universe" on raw mention counts) uses to justify the whole "highest tier, not commonest"
design. The comment `# nothing clears it: fall back to the commonest tier` is at least honest
about what the code does — but the docstring above it does not disclose that this fallback exists
or that it inverts the stated principle.

---

## LOW

These are consistent, low-impact patterns; several recur identically across all six files.

- **Unclosed file handle in the bad-chars self-check**, present verbatim in every file in this
  batch: `hostcheck.py:59`, `completeness.py:44`, `feats_index.py:76`, `scope.py:45` (also present
  in `tiers.py` — no, checked: `tiers.py` does **not** have this block at all; see note below).
  `if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):` —
  the file object returned by `open()` is never closed (no `with`, no `.close()`). Harmless under
  CPython's refcounting GC in practice, but a real leak under any other Python implementation and
  bad practice for a pattern copy-pasted across the whole codebase.
- **`tiers.py` and `propagation.py` carry no `_BAD_CHARS` self-check block at all**, unlike the
  other four files in this batch (and unlike most of the rest of the tree, going by the pattern
  seen elsewhere). Not a functional bug — noted only because it is an inconsistency worth the
  owner knowing about if that check is meant to be universal.
- **hostcheck.py:489,651,756,862** — `json.load(open(F.HOSTS, encoding="utf-8"))` repeated four
  times, each a bare `open()` with no `with` and no exception handling. Resource-leak pattern;
  also means a corrupt `WIKI_HOSTS.json` crashes each of `sweep()`, `purge()`, `roster_audit()`,
  `adopt()` uncaught (arguably fine — loud failure — but inconsistent with `entities_by_source()`'s
  swallow-and-continue two functions away).
- **hostcheck.py:454-457** — dead code. `r.setdefault("host", host)`, `.setdefault("rate", 0.0)`,
  `.setdefault("hits", 0)`, `.setdefault("probed", 0)` are unreachable no-ops: every return path
  in `probe()` already populates all four keys, so `setdefault` never has anything to do.
- **hostcheck.py caps, all judgment calls (measurement/sample bounds, not catalogue truncation)**:
  `PROBE = 40` (line 83, justified by MediaWiki's own 50-title batch ceiling); `names[:12]` in the
  RAW-mode probe branch (line 135, no stated justification for exactly 12, unlike the documented
  50-title API limit for the batched path); `relevance()`'s `titles[...][:sample]` with
  `sample=12` default (line 199); `_bodies()`'s further `[:8]` cap on titles in RAW mode (line
  246, undocumented, inconsistent with the 12 already passed in by the caller); `toks[:3]` (line
  218); `found = [...][:5]` / `"examples": ...[:5]` display fields (lines 138, 158); `foreign.
  extend(names[:3])` per foreign source inside `null_rate()`'s control-sample construction (line
  414). None of these remove a source, entity, or roster item from the actual catalogue or from
  `candidates()`'s returned list (which is correctly, deliberately unbounded per Hard Rule 0 — see
  CLEAN note below).
- **completeness.py:44** — same unclosed-handle pattern as above.
- **completeness.py:152-208** — `_REACH` dict, check-then-act race in `host_reachable()`, no lock
  at all anywhere in the file (unlike `hostcheck.py`'s `_NULL_LOCK`-guarded equivalent). Same
  benign-duplicate-work class as hostcheck.py's `null_rate()` finding above, just with zero
  synchronization instead of partial synchronization.
- **tiers.py:338 write target, print-only caps**: `unaddressed[:6]` (line 298) truncates a
  *console print* of unaddressed-shelf names to 6; the full count (`len(unaddressed)`) is printed
  separately and `TIERS.json` itself carries every source's full assignment regardless — display
  cap, not a data-loss cap. `deliberate_joins()`'s `shared.get((a, b), [])[:3]` (line 273) caps
  the printed evidence-example list to 3 entities per deliberate join; the join itself (and its
  weight) is unaffected — display cap only.
- **feats_index.py:218** — `sys.path.insert(0, os.path.join(HERE, "src"))` inside `audit()` is a
  redundant duplicate of the module-level `sys.path.insert(0, os.path.dirname(os.path.abspath(
  __file__)))` at line 71 (both resolve to the `src/` directory, which is already on `sys.path`
  by the time `audit()` runs). Dead code, harmless.
- **feats_index.py `_CACHE`** (`{"hosts": None, "index": None}`) — check-then-act, unguarded by
  any lock, in `host_to_sources()`/`load_index()`. Not currently exploitable: the only caller
  found in the tree, `manifest_builder.py:317`, calls `feats_for_source()` in what appears to be a
  serial loop (no `ThreadPoolExecutor` in that file). Flagged only because the pattern is the same
  shape as the guarded/unguarded caches elsewhere in this batch, in case a future caller
  parallelizes chapter-job building.
- **propagation.py:158** — dead code. The final `return 0` in `observed_mark()` is unreachable:
  `ascension_years(1)` is always exactly `0.0` (`1.0 ** 1.35 - 1.0 == 0.0`, no floating-point
  slop since `1.0 ** x == 1.0` exactly), and by the time the loop reaches `rung == 1` the
  `lag < 0` case has already been excluded by the early return two lines above, so `lag >=
  ascension_years(1)` (`lag >= 0.0`) is always true and the function always returns at rung 1 or
  higher. Harmless — the fallback value (`0`) matches what the loop would have found anyway.
- **scope.py:45** — same unclosed-handle pattern as above.
- **scope.py:102** — `build(records, hosts)`'s `records` parameter is accepted but never
  referenced anywhere in the function body. `main()` still calls `P.records()` to produce the
  argument (line 143: `out = build(P.records(), hosts)`), so that work happens and is discarded
  for nothing every `--build` run.
- **scope.py:105,126,128,142** — `open(OUT, ...)`/`open(F.HOSTS, ...)` reads with no try/except
  (existence is checked first for `OUT` via `os.path.exists`, but that is a TOCTOU gap, not a
  parse-error guard, and `F.HOSTS` has no existence check at all). A corrupt file crashes
  uncaught rather than being reported as a measurement gap.
- **scope.py:74,81** — `srlimit: "3"` per query across 4 `QUERIES` (up to 12 candidate titles,
  deduplicated) and `titles[:8]` (line 81) are both measurement-sample bounds on which wiki pages
  get scanned for cosmology-tier keywords, not truncations of catalogued content — judgment call,
  not a Hard Rule 0 violation.
- **scope.py:76** — `row["title"]` uses direct dict indexing (would raise `KeyError` if a
  MediaWiki search row ever omitted `"title"`) immediately next to `row.get("size", 0)`'s
  defensive style on the same line — inconsistent, low risk given `title` is a standard field in
  `list=search` responses, but worth normalizing.

---

## CLEAN (per module)

- **hostcheck.py** — CLEAN apart from the findings above. In particular: `candidates()` correctly
  returns the full, unbounded `grounded + spec` list (its own docstring's worked Hard-Rule-0
  example is honored in the code); `_land()` is a fully correct tmp+`replace_retry` writer used
  consistently for every shared artifact this module owns (`HOST_FITNESS.json`, `HOST_UNFIT.json`,
  `ROSTER_AUDIT.json`, `ROSTER_PURGES.json`, `WIKI_HOSTS.json`, and individual record files in
  `purge()`); every consumer of `rate=None`/`about=None` downstream of `probe()`/`score()`
  correctly threads "unjudged" through `sweep()`, `adopt()`, and the repair loop (excluding
  unreachable hosts from being written as WRONG-FICTION/unfit) — the two already-known bugs
  (m93, m94) are real but narrowly scoped, and the surrounding machinery built to consume their
  output is otherwise careful about the exact distinction it exists to enforce.
- **completeness.py** — CLEAN apart from the findings above. `land()` in particular is exemplary:
  it independently guards against an empty-file overwrite, a partial-shrink overwrite
  (`SHRINK_FLOOR`), and a silently-failed atomic replace (checking `replace_retry`'s return
  value) — three separate, well-reasoned defenses against exactly the failure modes this batch
  was asked to hunt for elsewhere.
- **tiers.py** — CLEAN apart from the TIERS.json write. The clustering (`_components`), containment
  checking, and grounding-pooling (`xenoverse_grounding`) logic is correct and runs over the full
  roster with no caps; `GROUNDINGS.json` load is properly guarded with try/except.
- **feats_index.py** — CLEAN apart from the reversal bug and the two low findings.
  `feats_for_source()` genuinely honors its own "NO CAPS" docstring claim — no slicing anywhere in
  the join/return path.
- **propagation.py** — CLEAN. Pure computation, no shared-file writes, no threading, no caps, no
  swallowed exceptions anywhere in the module. One trivial, harmless dead-code line (noted above).

---

## Severity tally

| module | HIGH | MEDIUM | LOW |
|---|---|---|---|
| hostcheck.py | 2 | 2 | 4 |
| completeness.py | 2 | 1 | 1 |
| tiers.py | 1 | 0 | 2 |
| feats_index.py | 1 | 0 | 3 |
| propagation.py | 0 | 0 | 1 |
| scope.py | 2 | 1 | 4 |
| **total** | **8** | **4** | **15** |
