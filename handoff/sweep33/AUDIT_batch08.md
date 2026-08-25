# Batch 08 — run33
Modules read: feats.py (1161 lines), weave.py (487 lines), reference.py (358 lines), cosmography.py (282 lines), grounding.py (245 lines), liveness.py (188 lines), resonance.py (149 lines)

## FINDINGS

### 1. liveness.py:72-87 — a module that fails to parse vanishes from every check with no trace  [severity: BLOCKING]
`_parse()` catches `Exception` broadly and returns `None` on any failure (syntax error, encoding
issue, or — per this project's own repeated incident history — a literal control character from
an eaten regex escape). `scan()` then does `if t is None: continue`, silently omitting that module
from `trees`. There is no counter, no printed list of skipped files, nothing in the returned dict
that says a module could not be read. A module this tool cannot parse is reported identically to a
module with zero findings — which is exactly the "a check that cannot fail looks exactly like a
check that passed" failure this file's own docstring is about, now applied to the tool itself. If
the exact corruption this project keeps rediscovering (0x08 backspace from a heredoc-eaten `\b`)
ever lands in a module liveness.py has not yet been taught to skip loudly, that module goes dark
in every future sweep with no signal anywhere.
```python
def _parse(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return ast.parse(fh.read(), filename=path)
    except Exception:
        return None
```

### 2. feats.py:923-937 — `page_looks_real()` requires wiki markup even for non-wiki sources  [severity: MAJOR]
`evidence_for()` calls `page_looks_real(wt, t)` unconditionally for every page, including the two
non-wiki corpora this same function reads a few lines earlier: `doc:` (owner-ingested plain-text
books via `ingest_doc.py`) and `pages:` (HTML pages fetched via `EP.fetch_html`). `page_looks_real`
requires the text to contain at least one of `_WIKI_MARKERS` (`"[["`, `"{{"`, `"=="`, `"categor"`,
`"reflist"`, `"infobox"`, `"cite "`, `"'''"`) or it is filed under `pages_refused` as a block page:
```python
for t, wt in pages.items():
    clean = wt if plain else strip_wikitext(wt)
    ok, why = page_looks_real(wt, t)
    if not ok:
        unreal[t] = why
        continue
```
Real prose from a book or an HTML page is very unlikely to contain wiki markup syntax. If that is
so for these two source types, every page from them gets classified as a refusal and dropped from
mining — silently, and via the exact "looks like an honest absence" failure mode this whole file
exists to prevent, just recreated at the content-shape layer instead of the HTTP layer. I could
not fully verify `EP.fetch_html`'s output shape (`endpoint.py` is outside this batch); recommend
checking `pages_refused` counts for `doc:`/`pages:` hosts specifically.

### 3. feats.py:712-741 — scientific-notation exponent is parsed and then discarded  [severity: MAJOR]
`_QUANTITY` captures three groups: the mantissa, an optional `x 10^N` exponent, and the unit.
`mine()` stores only the mantissa and unit:
```python
_QUANTITY = re.compile(
    r"\b(\d[\d,\.]*)\s*(?:x\s*10\^?(\d+)\s*)?"
    r"(tons?|...)\b", re.I)
...
quants.append({"value": m.group(1), "unit": m.group(3), "sentence": s, "page": page})
```
`m.group(2)` (the exponent) is captured by the regex and never read anywhere. A sentence citing
"5 x 10^44 joules" — an entirely ordinary way to state a large energy figure in this material — is
recorded with `value: "5"`, silently dropping the 10^44 multiplier. Whatever downstream consumer
(`assay.band_for_quantity`, per the module docstring) reads `value` alone gets a number off by up
to 44 orders of magnitude. `sentence` is stored too, so a consumer that re-parses the full sentence
independently would be unaffected — but the `value`/`unit` fields as written are wrong for any
scientific-notation citation.

### 4. resonance.py — the whole module is unimported anywhere in src/, contradicting its own docstring  [severity: MAJOR]
`grep -rn "import resonance\|from resonance" src/*.py` returns nothing. Every function in this
file — `hodge_decompose`, `dominates`, `incomparability_rate`, `resonance_strength` — has zero
callers in the codebase, despite the module's docstring stating it is load-bearing: "Everything
downstream -- propagation delay, cosmological clustering, entity resolution -- is this quantity
wearing a different hat." `custodes.py:297` (outside this batch) describes a live mechanism in its
own docstring — "`eta` (from resonance.hodge_decompose) lets Threnody exercise her veto" — but
`custodes.py` never imports `resonance` either (`grep -n "import resonance" custodes.py` is empty).
Either Threnody's veto is implemented some other, duplicated way, or a described safety mechanism
does not actually exist as wired code. Worth settling directly against `custodes.py`.

### 5. reference.py:337-353 — `--compare`'s advertised "axes differing" column is never populated  [severity: MAJOR]
```python
print(f"\n{'entity':<20}{'reference':>12}{'automated':>12}{'delta':>8}  axes differing")
...
print(f"{name:<20}{r['moth_number'][2:10]:>12}{got['moth_number'][2:10]:>12}"
      f"{abs(rv - gv):>8.2f}")
```
The header promises a fifth column listing which axes diverge between the hand-built reference and
the automated pass. The per-row print statement has only four fields — nothing computes or prints
any axis-level diff anywhere in `main()` (the whole function was read; this is all of it). Given
this file's stated purpose is "to calibrate the automated pass against" the reference sheets, the
one diagnostic that would actually show WHERE the automated scoring goes wrong is silently absent
from its own comparison report.

### 6. grounding.py — the only file in this batch with `\b`-heavy regexes and no eaten-escape guard  [severity: MAJOR]
feats.py, weave.py and reference.py all open with the same self-check:
```python
_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding='utf-8').read() for c in _BAD_CHARS):
    raise SystemExit(...)
```
guarding against a specific, repeatedly-observed corruption: a `\b` word-boundary escape written
through a shell heredoc arriving as a literal 0x08 backspace, which "read as a tuning problem...
most recently in the axis gates" (feats.py's own words). `grounding.py` has dozens of `\b`-anchored
cues in `GROUNDINGS` and in `_ORIGIN` — exactly the pattern that has bitten this project five times
by weave.py's count — but carries no such guard. Confirmed no corruption is present today (checked
directly), so this is not a live bug, but it is the one file in this batch that qualifies for the
established defence and does not have it.

### 7. liveness.py:89-99, 114 — DEAD detection's "used" set is far broader than its own justification  [severity: MAJOR]
```python
for node in ast.walk(t):
    if isinstance(node, ast.Name):
        used.add(node.id)
    elif isinstance(node, ast.Attribute):
        used.add(node.attr)
    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
        used.add(node.value.strip())
...
if fn not in used:
    dead.append(...)
```
The docstring justifies the string-constant branch as covering dispatch-table lookups ("a function
called through getattr or a dispatch table still shows up as a string constant"). But the
`ast.Attribute` branch adds `node.attr` for **every** attribute access in the whole 95-module tree,
regardless of the receiver's type — `response.json()`, `f.read()`, `path.parent` all register
`json`, `read`, `parent` as "used" project-wide. A module-level function sharing a name with any
common stdlib/builtin method (`get`, `read`, `write`, `close`, `run`, `load`, `save`, `parse`,
`fetch` — `fetch` is itself a real function name in this very batch's `feats.py`) can never be
flagged dead by this scanner, no matter how uncalled it actually is. This is a materially wider
false-negative surface than the dispatch-table case the docstring defends, in exactly the file the
sweep depends on to surface dead code.

### 8. weave.py:156-173, 424-483 — `pair_weights()` (and the `idf_table()` output it consumes) is dead  [severity: MINOR]
```python
def pair_weights(occ, idf, min_sources=2):
    ...
```
`grep -rn "pair_weights" src/*.py` shows it defined once and never called — `weave.py`'s own
`main()`, `pipeline.py:1918` and `tiers.py:199` all call `surprisal_pair_weights()` instead. `idf`
(from `idf_table()`) is likewise computed in `main()` and never used for weighting, only unpacked
and discarded. The module's own docstring explains why the idf approach was superseded (`"Gordon"`
is rare as an entity, common as a word, so idf over-weights it) — this isn't a mystery function,
it's a superseded implementation nobody removed.

### 9. feats.py:1015-1076 — the WAF/block-page count `page_looks_real()` computes is never aggregated or printed  [severity: MINOR]
`evidence_for()` writes `pages_refused` (from `page_looks_real`'s rejections) into each entity's
cache file, but `roll()`'s `done` counters (`n`, `feats`, `quant`, `pages`, `chars`, `empty`,
`errored`) never total it, and `_show()`'s CLI display never prints it either — both were read in
full. `_RATE_LIMITED` and `_CAP_BOUND` get exactly this treatment ("a measurement nobody prints is
not a measurement," in the module's own words) but the refusal count — the mechanism this module
introduces specifically to distinguish "no page" from "we were served a block page" — does not. A
run hitting mostly interstitials on a WAF-protected host looks, in the printed summary, identical
to a run that legitimately found nothing.

### 10. resonance.py:133-149 — `resonance_strength()`'s default path reads the graph weave.py's own docstring calls broken  [severity: MINOR]
```python
path = graph_path or os.path.join(HERE, "data/SHARED_STAGE_GRAPH.json")
```
`weave.py`'s docstring (lines 32-35) states the raw co-occurrence graph "linked Greek and Roman
myth through 'Tartarus (LV-797)' -- a Weyland-Yutani planetary designation" and "tied two D&D
supplements together through 'Dexterity' and 'Channel Divinity'," and that module now writes its
corrected, surprisal-weighted graph to a *different* filename, `SHARED_STAGE_GRAPH_IDF.json`
(`weave.py:82`, with an explicit comment that `resonance.py` is meant to read the `shared_sample`
key from it). `cosmology_graph.py` (outside this batch) still writes the old, uncorrected
`SHARED_STAGE_GRAPH.json`, and that is what `resonance_strength()` defaults to reading. Currently
inert because nothing calls `resonance_strength()` (see Finding 4), but the documented-broken
linkage is what a caller would get the moment the function is wired up as its own docstring implies
it should be.

### 11. feats.py:372-428 — `resolve_hosts()` has an unreachable override check  [severity: MINOR]
```python
ov = _override(src)
if ov and known.get(src) != ov:
    known[src] = ov
    continue
if src in known:
    continue
seen = collections.Counter(...)
if seen:
    known[src] = seen.most_common(1)[0][0]
    continue
ov = _override(src)
if ov:
    known[src] = ov
    continue
```
`_override(src)` is a pure function of `src` (regex matching against `_HOST_OVERRIDES`). If the
first call returns truthy, the flow already `continue`s (either directly, or via `src in known`
since `known[src]` was just set to `ov`). The only way to reach the second `ov = _override(src)`
call is for the first call to have returned falsy — in which case the second call, being
deterministic, is guaranteed to also return falsy. The bottom `if ov: known[src] = ov; continue`
block can never execute.

### 12. reference.py:232-246 — `shelfmark()`'s rung indexing assumes exact, unchecked shapes  [severity: MINOR]
```python
marks = [f"{RUNGS[i]}{v}" for i, v in enumerate(upper)]
marks += [f"{RUNGS[3 + i]}{v}" for i, v in enumerate(lower)]
```
This is outside the function's own `try/except`. `upper`'s length is `len(rec["tier_key"].split
("."))` and `RUNGS` has exactly 7 entries; the code silently assumes `tier_key` always splits into
3 parts and `lower_rungs` always has exactly 4 entries, matching the 3+4=7 rungs `RUNGS` provides.
True for all three current hardcoded entries, so nothing misbehaves today. A future reference entry
with a differently-shaped `tier_key` or `lower_rungs` would either mislabel a rung or raise an
uncaught `IndexError` (e.g. `lower_rungs` with 5 elements reaches `RUNGS[7]`, out of range) rather
than fail through the guard immediately above it.

### 13. feats.py:240-303 — a WAF-served non-JSON 200 response and a genuine network fault share one silence-ledger key  [severity: INFO]
`api()` gives 404 and 429/503 their own dedicated branches and counters (`_RATE_LIMITED`), with a
comment explaining exactly why that separation matters ("mixed 'the network is failing' with 'the
page does not exist'... made the ledger's count for this site unreadable"). A `json.loads` failure
— which is what happens if a wiki serves an HTML challenge/login page with a 200 status to an
`/api.php` call — falls into the generic `except Exception: silence.note("feats.py:139")` branch,
the same tag used for a plain connection timeout. The file's own stated principle argues this
distinction should be visible too; right now it is not.

### 14. liveness.py:117-129, 131 — two smaller gaps in the same two passes  [severity: INFO]
TAUTOLOGY flags any two syntactically identical subexpressions, including calls that can return
different values on each evaluation (`time.time() == time.time()`, anything touching mutable or
random state) — a false-*positive* risk in the opposite direction from the file's stated concern,
but still a place where "CANNOT FAIL" is not quite the right claim. Separately, PHANTOM seeds
`defined` with `set(dir(__builtins__))` (line 131); when a module is *imported* rather than run as
`__main__`, CPython binds `__builtins__` to the builtins **dict**, and `dir()` on a dict returns
dict methods (`get`, `items`, `update`, `keys`...) rather than real builtin names. This is masked
here by the later `import builtins; defined |= set(dir(builtins))`, which supplies the correct
names regardless — so real builtins are never missed — but if liveness.py is ever imported (versus
invoked as a subprocess), the dict-method names leak into `defined` as extra, spurious exemptions,
marginally suppressing PHANTOM findings whose guard happens to be named `get`, `items`, etc.

### 15. resonance.py:50-96 — docstring claims Gauss-Seidel, implementation is Jacobi  [severity: MINOR]
```python
"""...Implemented as plain Gauss-Seidel on the graph Laplacian..."""
...
for _ in range(600):
    new = {}
    for n in nodes:
        ...
        new[n] = sum(theta[b] + f for b, f in nbrs[n]) / len(nbrs[n])
    ...
    theta = {n: v - shift for n, v in new.items()}
```
Every neighbor read in a sweep comes from `theta`, the *previous* sweep's fully-settled state; none
of a sweep's own updates are used until the next sweep. That is Jacobi iteration. Gauss-Seidel
updates each node in place and uses already-refreshed neighbors within the same sweep, and
converges markedly faster on this kind of system. Both converge to the same fixed point in the
limit, so this is not a wrong-answer bug, but the fixed 600-iteration budget was presumably sized
for the faster method the docstring describes, not the slower one actually running — `eta` may be
less converged than intended, especially on a well-connected graph.

## QUESTIONS

- **cosmography.py:145-166**, `kardashev_to_magnitude()`: for an energy budget below the lowest
  Magnitude band's floor, the loop never updates `reached` from its initial `ladder[0]`, so a
  civilization far under the lowest band is reported as sitting IN the lowest band rather than as
  "below all measurable bands." This may be intentional (a floor convention consistent with how
  `assay.py`'s ladder is meant to behave at its low end) or an oversight; `assay.py` is outside
  this batch so I could not check how the lowest band's semantics are defined elsewhere. Settled by
  reading `assay.BAND_EDGES`/`LADDER` and whether M0/the lowest rung is meant as an open-ended
  catch-all.
- **resonance.py / custodes.py**, tied to Finding 4: does `custodes.py` implement "Threnody's veto"
  through a duplicate of `hodge_decompose`'s math, or is the mechanism its own docstring describes
  simply not wired to anything? `custodes.py` is outside this batch; settled by reading it directly
  and checking for a local reimplementation of the Hodge decomposition or an actual import of
  `resonance`.

## CLEAN
- **cosmography.py** — read in full. The census chain (galaxies → stars → planets → habitable →
  life → complex life → civilizations → Kardashev mix) is internally consistent, every declared
  constant is cited or labelled FICTIONAL with a stated reason, `validate()`'s physical-impossibility
  checks are sound arithmetic and the current `KARDASHEV_MIX` sums to 1.0 and passes every ceiling
  check under the default STANDARD-universe constants, and `kardashev_K` is confirmed exercised by
  `verify_math.py`. Nothing beyond the one item above under QUESTIONS.

## Coverage
Recorded via `sweep_plan.record('run33', ['feats.py','weave.py','reference.py','cosmography.py','grounding.py','liveness.py','resonance.py'], batch=8)`.
