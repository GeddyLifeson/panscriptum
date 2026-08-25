# AUDIT — batch 14 (sweep run #28)

Modules: `src/wiki_source.py` (652), `src/chain.py` (497), `src/identity.py` (423),
`src/pantheon.py` (308), `src/tempus.py` (254), `src/cleanup.py` (208), `src/resonance.py` (149).
**Total: 2,491 lines, all read in full.** `NEXT_STEPS.md` §3 read first; every item touching
this batch's files is called out as KNOWN below and re-verified live against current source.

---

## SPECIAL FOCUS ANSWER — does `wiki_source.py:549-568 category_members` explain DC at 0.5%?

**Yes, plausibly and specifically — KNOWN (NEXT_STEPS §3), STILL OPEN, re-verified at source.**

The `cmcontinue` pagination itself is **implemented correctly**: `category_members` (549-573)
loops `while limit is None or len(out) < limit`, sets `cmcontinue` from the previous response's
`continue.cmcontinue`, and stops only when the wiki reports no further continuation token — that
part is exhaustive and correct when the walk completes without error.

The defect is what happens on ANY exception mid-walk:

```python
# wiki_source.py:564-568
try:
    d = _api(subdomain, p)
except Exception:
    silence.note("wiki_source.py:376")
    break
out += [m["title"] for m in d.get("query", {}).get("categorymembers", [])]
```

`break` exits the `while` loop and the function `return out`s whatever was collected so far —
**there is no second return value, no `complete` flag, nothing that lets the caller distinguish
"the whole category" from "the walk died on page 4 of 68".** `all_categories` (352-406), right
above it in the same file, tracks a local `complete` bool and at least uses it to gate its own
*cache* — but it too only ever `return out`s the bare list, so even that flag never reaches a
caller. Neither function's caller can tell truncated from exhaustive.

**Why this lands hardest on DC specifically**, traced through the real call sites
(`catalogue_web.py:194-216`, not in this batch but read for context): for each of the seven
canonical categories, `find_categories` can return **many** matching wiki categories (DC's
"Persons" bucket alone plausibly matches "Characters", "Heroes", "Villains", "Male/Female
Characters", etc.), and `category_members(sub, c, limit=None)` is called **once per matching
category**, each with its own independent pagination walk with zero retry across the whole walk
and zero completeness propagation. DC's `Characters` category alone has 33,614 members, needing
~68 chained `cmcontinue` calls; multiplied across every matching category for every canonical
bucket, a DC catalogue run issues hundreds of sequential paginated calls, each one a chance for
`_get`'s already-documented failure mode to fire. `_get`'s own comments (wiki_source.py:148-157)
record that this exact module previously got the entire `fandom.com` domain IP-blocked
("every fandom.com host now drops our connections at the socket... HTTP 000") after an
overly-aggressive benchmark; `_get`'s retry ladder (3 attempts, `MIN_GAP`/backoff) helps with a
transient 429/503 but does **nothing** against a sustained connection-refused/timeout condition,
which fails identically on all 3 attempts and triggers the silent `break` on the very first
paginated call of whichever category is mid-walk when it happens. A large multi-category wiki
like DC has vastly more chances to hit this than a small single-category wiki, and once it hits,
that category's roster is silently capped wherever the walk happened to be — never retried, never
flagged, and (per `catalogue_web.py:104-105`'s "rank, never truncate" comment) fed straight into
`rank_by_size` as if it were the complete cast. This is fully consistent with DC sitting at 0.5%
while smaller-category wikis catalogue far more completely.

**Verdict:** the mechanism is real, the pagination logic is not the bug — the missing
completeness signal on a mid-walk failure is. Confirmed unchanged at source this run.

---

## src/wiki_source.py

### KNOWN — category_members partial roster on failure, no completeness flag (HIGH, STILL OPEN)
See special-focus section above. `wiki_source.py:549-573`.

### NEW — `resolve_wiki`'s hosts-file read only catches `OSError`, not JSON corruption (MED)
`wiki_source.py:275-284`:
```python
try:
    with open(_hosts_path, encoding="utf-8") as f:
        known = json.load(f).get(source_name)
except OSError:
    silence.note("wiki_source-hosts-read")
    known = None
```
`json.load` raises `json.JSONDecodeError`, which is a subclass of `ValueError`, **not**
`OSError`:
```
>>> json.JSONDecodeError.__mro__
(JSONDecodeError, ValueError, Exception, BaseException, object)
```
(confirmed live via the miniconda interpreter). `data/WIKI_HOSTS.json` is a shared state file
written from at least three call sites across two other modules (`hostcheck.py`, `scout.py` per
their own comments — "WIKI_HOSTS.json is written from THREE call sites in two modules"). If any
writer leaves it torn or truncated (a crash mid-write, a denied-then-retried replace, a reader
catching it between a truncating write and a rename on a writer that isn't using the atomic
path), `resolve_wiki` does not fail soft into the guess-list fallback the whole function exists
to provide — it raises an uncaught `JSONDecodeError` straight out of `resolve_wiki`, crashing
whatever catalogue run called it. This is the opposite of the module's own stated intent at
line 264 ("a resolver failing to resolve a host the library had already resolved... is not
tolerable... only the file operations sit inside the try") — the guard was written to be narrow
on purpose but is narrow in the wrong dimension: it protects against a missing file, not a
malformed one, and a malformed one is the more likely shared-state failure mode.

### NEW — `page_text`'s `max_chars=900` / `extracts`'s `chars=700` are evidence-text truncations (LOW, speculative)
`wiki_source.py:456, 481-484, 576-593`. Per-article prose fed to the model is hard-capped to
900/700 chars before any later regex/keyword logic sees it. This is presented in-file as a
deliberate cost/size tradeoff ("fetching the whole page... costs ~420KB per article... over tens
of thousands of pages is absurd"), and it is evidence text rather than a roster, so it does not
match Hard Rule 0's "no cap on a listing" language as squarely as `category_members` does. Flagged
low-confidence because the sibling pattern (`weave_index.py:224` / `weave.py:195-198`
`description[:400]` blinding downstream mechanic-detection regexes) is already a confirmed
Hard-Rule-0 finding elsewhere in the tree for the identical shape — worth a second look by whoever
owns the downstream consumers of `page_text`/`extracts` output, but not verified as causing a
concrete wrong result from inside this file alone.

### Re-verified FIXED (no longer bugs, confirm-only)
- `all_categories`'s `hard_stop` — now defaults to `None` (652-406, specifically line 352 and the
  `while hard_stop is None or len(out) < hard_stop:` loop condition at 385) with the cap fully
  removed by default; the docstring's account of the fix matches the code. **FIXED.**
- The hosts-read vs. category-probe `silence.note` label collision (BUGS m5) — now
  `"wiki_source-hosts-read"` (283) vs. `"wiki_source-category-probe"` (440), two distinct labels.
  **FIXED.**
- `page_text`'s per-section failure handling (BUGS m4) — now `continue`s past a failed section
  instead of `return`ing `""` early, so one section's transient failure does not poison the
  other two. **FIXED.**

---

## src/chain.py

### KNOWN — `unmatched.most_common(40)` truncates a field written into CHAIN.json (HIGH, STILL OPEN)
`chain.py:108`, inside `write_result`:
```python
"unmatched": (unmatched.most_common(40) if hasattr(unmatched, "most_common")
              else (unmatched or [])),
```
Confirmed present, unchanged. Any unmatched name beyond the top 40 by count never reaches the
persisted `CHAIN.json`, so a downstream reader auditing "what's missing from the library's index"
sees an artificially small list.

### KNOWN — `unmatched[side[:40]]` truncated string used as dict key (HIGH, STILL OPEN)
`chain.py:352-354`:
```python
for side, k in ((w, wk), (l, lk)):
    if k not in idx:
        unmatched[side[:40]] += 1
```
Confirmed present, unchanged — the same class of bug as the already-fixed m37
(`sentence[:120]` as a dedup key at line 218, which now correctly uses the *full* sentence).
Two distinct unmatched names sharing a common 40-character prefix collide into one counter
bucket, undercounting the true diversity of unresolved names and potentially misattributing a
count to the wrong (truncated, ambiguous) label.

### NEW — console diagnostic `unmatched.most_common(8)` and `order[...][:14]` cap the only visible
### summary of a run (LOW-MED)
`chain.py:456-458` prints only the 8 most common unmatched names to the terminal (separate from
the 40-cap written to disk above — this one caps the *interactive* view further), and
`chain.py:487-489` prints only the top 14 strongest entrants in the largest component. Per lesson
16 in `NEXT_STEPS.md` ("a cap on a diagnostic hides the pattern, not just the rows"), a human
running `chain.py` directly and reading only the console never sees more than these truncated
views — though the full `edges`/`unmatched` are written to `CHAIN.json` regardless (modulo the
:40/[:40] caps above), so this is a presentation-only gap, not a data-loss one on its own.

### Re-verified FIXED (confirm-only)
- Dedup key at `harvest()` line 218 now uses the full `(entity, sentence)` tuple, not a
  120-char prefix (m37's original class) — **FIXED** for this specific site.
- `write_result` / `harvest`'s incremental-index write both now route through
  `silence.write_json` (unique PID+thread temp name) rather than the old fixed-name
  `.tmp` — confirmed at lines 120 and 200. **FIXED**, matches the docstring's claim about the
  m100 collision closure.

---

## src/identity.py

### KNOWN — `_is_continuity` requires `n >= 2` bearers; a genuine single-bearer continuity like the
### module's own `(Fates)` example can never be recognised (HIGH, STILL OPEN)
`identity.py:180-207`:
```python
n = stat["bearers"] if isinstance(stat, dict) else stat
shared = stat.get("shared", 0) if isinstance(stat, dict) else 0
if n >= MIN_BEARERS:      # MIN_BEARERS = 3
    return True
return n >= 2 and shared >= max(2, 0.5 * n)
```
For `n == 1` (a designator worn by exactly one base name), the first branch is False
(`1 >= 3`) and the second branch's leading `n >= 2` guard is also False regardless of `shared`,
so the function **always** returns `False`. The docstring for this exact function says, in its
own words: *"(Fates) has one bearer and is obviously a continuity because that bearer exists in
three other branches. Either alone admits it."* — but the code as written cannot admit it: a
single-bearer designator is unconditionally rejected no matter how large `shared` is (and
`shared` cannot exceed `n` by construction in `mine()`, so for `n=1` the maximum possible
`shared` is 1, which is moot since the branch never runs). Confirmed unchanged; this is exactly
the docstring-contradicts-code shape the sweep watches for. Consequence per the module's own
framing: a young, thinly-mined continuity that has only one character written up so far gets
silently merged into the main line instead of kept separate — the specific error `identity.py`
exists to prevent, on exactly the case its own docstring uses to explain the design.

### NEW — `load()`'s cache write uses a fixed-name `.tmp` and a raw `open+json.dump`, not `silence.write_json` (MED)
`identity.py:217-223`:
```python
inv = mine()
os.makedirs(os.path.dirname(CACHE), exist_ok=True)
tmp = CACHE + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(inv, f, indent=1, sort_keys=True)
silence.replace_retry(tmp, CACHE)
```
This is precisely the anti-pattern `silence.write_json`'s own docstring describes fixing at
"twelve call sites across ten modules" on 2026-08-25 (see `silence.py:250-287`): a **fixed**,
not PID/thread-unique, temp filename. `DESIGNATORS.json` (`CACHE`) is read via `load()` from
multiple modules (`chain.py`'s `harvest()` calls `ID.load()`, the CLI calls it via `main()`,
and any future caller doing `identity.py --refresh`), so two processes racing to rebuild the
cache (e.g. cache missing, chain.py and a direct `identity.py --refresh` invocation both firing
near-simultaneously) would both write to the same `DESIGNATORS.json.tmp` path — the loser's
`os.replace` can rename a partially-written file over the winner's completed one, or vice versa,
producing a torn or stale `DESIGNATORS.json`. Additionally the return value of
`silence.replace_retry(tmp, CACHE)` is **discarded** here (compare `chain.py:120-124`, which
checks the return and logs to stderr on a denied replace) — a denied replace on Windows (readers
holding the file, per `replace_retry`'s own docstring) is silently swallowed with no signal that
the just-mined inventory was never actually landed.

### Re-confirmed correct (no bug)
- `identify()`, `node()`, `continuities()`, `_partials`-style short-form handling in `chain.py`'s
  `_partials`/`entity_index` (cross-file, reviewed together since `chain.py` imports `identity`
  directly) are internally consistent with the documented design.
- `MIN_BEARERS = 3` and the `n >= 2` branching combine as documented for the *population*/
  *branching* dual test **except** for the `n == 1` gap above, which is the one place the two
  tests' stated "either alone admits it" claim is false.

---

## src/pantheon.py

Hand-authored data module (11 divine-tier entries) plus a thin compute/print harness. No caps,
no swallowed failures of consequence, no concurrency writes beyond a single `silence.write_json`
call (line 261, already atomic).

### NEW — Z_FIGHTERS.json merge failure is silently absorbed with no visible signal (LOW)
`pantheon.py:264-271`:
```python
if not a.gods_only:
    for path in ("Z_FIGHTERS.json",):
        try:
            with open(os.path.join(HERE, "data", path), encoding="utf-8") as f:
                for k, v in json.load(f).items():
                    combined.setdefault(k, v)
        except Exception:
            silence.note("pantheon.py:merge")
```
A missing/corrupt `Z_FIGHTERS.json` means the combined "whole ladder" ranking printed at the end
silently prints gods-only with no visible indication to the operator that the Z Fighters half is
missing (only `silence.note`, no `print(..., file=sys.stderr)` the way `chain.py`/`identity.py`
do for their own denied-write cases). Low severity since `--gods-only` exists as the honest way
to get this same output deliberately, and `M18`/`axis_score` (the file's real cross-file
dependency risk, per `NEXT_STEPS.md` item 4) is out of this file's scope — `A.LADDER` was
confirmed to include `"M8"` (`assay.py:105`), so no crash risk from the M8 anchor used throughout
this file.

No Hard Rule 0 violations found — the `rank`/`out` loops that print results are never sliced;
only the `+N more` console summaries elsewhere in the tree apply that pattern, and pantheon.py
doesn't use it at all (it prints everything).

---

## src/tempus.py

Clean. Fully derived math module (no I/O, no caching, no writes) implementing the institutional-
simultaneity model. Read every line; found no correctness bugs, no caps, and no swallowed
failures — the one external call (`propagation.load_graph`/`shortest`/`arrival_years` in
`apparent_lag_years`) delegates without a `try/except`, which is consistent with the rest of the
module's "compute or raise" style and not flagged as a defect given `propagation.py` is outside
this batch.

### Re-confirmed correct (per NEXT_STEPS item 4)
`band_resolution()` (199-210) was named in `NEXT_STEPS.md` as already implementing the correct
M10-ceiling fallback (inherits the `M9→M10` window width rather than inventing an edge above the
Ladder) in contrast to `assay.py`'s `axis_score()`/`ledger.py`'s M18 flat-9.9 bug. Re-verified at
source this run: the `i + 1 < len(LADDER)` branch and its `else` (using `LADDER[i-1]`/`band` as
`lo`/`hi`) are exactly as documented and internally consistent with `rung_description_length()`'s
`L_r(M0) = 0` anchor case immediately above it. **Confirmed correct, unchanged.**

---

## src/cleanup.py

### NEW — the `_SETTING_META` guard entry is a phantom check that validates nothing (LOW-MED)
`cleanup.py:73-80`:
```python
for _n, _p in (("_NAV", _NAV), ("_EMPTY_MECHANIC", _EMPTY_MECHANIC),
               ("_SETTING_META", None)):
    if _p is not None and any(ord(c) < 32 for c in _p.pattern):
        raise SystemExit(f"{_n} contains a control character; the escape was mangled in transit")
```
`_SETTING_META` is never defined anywhere in this file (grepped — no other occurrence). The tuple
entry's `_p` is `None`, and the loop's own guard (`if _p is not None`) means this entry is
unconditionally skipped — it can never fail, and it never actually checks anything named
`_SETTING_META` because no such regex exists here to check. The module's docstring-adjacent
comment claims "**Three** regexes in this project have been silently broken by an escape being
eaten in transit," but only two real patterns (`_NAV`, `_EMPTY_MECHANIC`) are ever validated by
this loop; the third slot is a leftover reference to something that either moved to another module
or was deleted without removing its guard entry. This is exactly the lens's "a check that cannot
fail" shape (item 1) — it looks like three protections are active when only two are, and a reader
skimming the loop would reasonably (and wrongly) conclude `_SETTING_META` is a live, checked
pattern somewhere in this file.

### Observation — console example lists are capped but underlying counts/writes are not (LOW)
`cleanup.py:186-201`: `nav[:5]`, `ceil_fixed[:6]`, `ceil_unres[:4]`, `desc_fixed[:5]`, `thin[:5]`
only affect the terminal *examples* printed; the `len(...)` totals printed alongside them are
always the full, uncapped counts, and the actual mutations (`PL.write_record`) operate over every
matched entry with no cap. This does not lose data the way the KNOWN caps elsewhere in the sweep
do — flagged only because lesson 16 asks that every truncated diagnostic be checked, and this one
passes: the full counts are always visible next to the truncated examples.

No correctness bugs found in `clean_ceiling`'s three-strategy resolution (exact → head → prefix)
or in `clean_description`'s markup-stripping regex chain; both use `pipeline.write_record`
correctly (the two-writer contract is respected here).

---

## src/resonance.py

### NEW — the entire module is dead code, and a docstring elsewhere describes it as live (HIGH)
`grep -rn "import resonance" src/` returns **zero** hits anywhere in the tree except
`resonance.py` itself. `custodes.py:297`'s docstring for `convene()` states:

```
`eta` (from resonance.hodge_decompose) lets Threnody exercise her veto: where the contest
structure is substantially curl, no scalar is faithful and the college says so rather than
averaging harder.
```

and the veto logic genuinely exists in code (`custodes.py:352`:
`if eta is not None and (1.0 - eta) >= CURL_VETO_THRESHOLD: out["threnody_veto"] = True`) — but
`convene()`'s `eta` parameter (`custodes.py:290`) defaults to `None`, and **no caller anywhere in
`src/` ever computes an `eta` via `resonance.hodge_decompose` and passes it in**:
- `anchors.py:190` (the real, production instrument-validation call site) calls
  `CU.convene(a["anchor"], a["scores"], attestation=a["attestation"], worksheet="anchors.py")`
  — no `eta` argument at all.
- `verify_math.py`'s several `CU.convene(...)` calls pass **hand-typed literal** `eta=0.70` /
  `eta=0.99` for unit-test purposes only (lines 475, 478, 559) — not derived from any real contest
  graph.

So in the entire live pipeline, `eta` is always `None`, the veto branch at `custodes.py:352` is
permanently unreachable, and `resonance.py`'s `hodge_decompose` — the function the docstring
names as the mechanism that empowers it — is never invoked by anything. This is a docstring
promising a guarantee ("lets Threnody exercise her veto") the code does not deliver, in the
`custodes.py`/`resonance.py` pair together; from `resonance.py`'s own side, the file is a fully
orphaned module: `resonance_strength()` is likewise never called anywhere in `src/`.

### NEW — `hodge_decompose({})` crashes with `ZeroDivisionError` (MED, currently unreachable but a live landmine)
`resonance.py:71-79`:
```python
for _ in range(600):
    new = {}
    for n in nodes:
        ...
        new[n] = sum(theta[b] + f for b, f in nbrs[n]) / len(nbrs[n])
    shift = sum(new.values()) / len(new)          # gauge-fix: mean zero
    theta = {n: v - shift for n, v in new.items()}
```
Reproduced live:
```
>>> resonance.hodge_decompose({})
CRASH: ZeroDivisionError division by zero
```
When `edges` is empty, `nodes = []`, so the inner `for n in nodes` loop never populates `new`,
leaving `new = {}` and `len(new) == 0` at the `shift = sum(new.values()) / len(new)` line. Because
the module is currently dead code (see above), this cannot fire in production today — but it is
exactly the crash a caller would hit the moment `resonance.py` is wired up as its own docstring
and `custodes.py`'s docstring both describe it as being. A contest graph legitimately can be
empty for a source with zero recorded defeats, which is not a rare condition (`chain.py`'s own
`fit()` at line 432 explicitly special-cases `len(wins) < 3` for the same underlying reason).

### NEW — `resonance_strength()` has no error handling around a shared multi-writer JSON file (LOW)
`resonance.py:141-143`:
```python
path = graph_path or os.path.join(HERE, "data/SHARED_STAGE_GRAPH.json")
with open(path, encoding="utf-8") as f:
    g = json.load(f)
```
No `try/except` at all — a missing file (first run, before `cosmology_graph.py` has ever
produced it) or a torn read raises straight out of the function. `cosmology_graph.py`'s own
comments (line 144, read for cross-file context) say `SHARED_STAGE_GRAPH.json` is written
atomically specifically because `propagation.py` and `resonance.py` "both read
SHARED_STAGE_GRAPH.json live" — so the atomicity contract on the *write* side is honoured
elsewhere, but this *read* side still has zero defence against the file simply not existing yet,
which is a normal early-pipeline state, not a corruption case. Low severity because (a) the
write side is atomic per the cross-file comment, so a torn read specifically is unlikely, and
(b) like the rest of this module, it currently has no live caller.

---

## Summary of severities

| Severity | Count | Notes |
|---|---|---|
| HIGH | 5 | wiki_source.py category_members (KNOWN); chain.py ×2 (KNOWN); identity.py `_is_continuity` (KNOWN); resonance.py dead-module/veto-never-fires (NEW) |
| MED | 4 | wiki_source.py hosts-read JSONDecodeError (NEW); identity.py fixed-tmp cache write (NEW); chain.py console-diagnostic cap (NEW, LOW-MED); resonance.py `hodge_decompose({})` crash (NEW) |
| LOW | 5 | wiki_source.py page_text/extracts char caps (NEW, speculative); pantheon.py silent merge-failure (NEW); cleanup.py phantom `_SETTING_META` guard (NEW); cleanup.py console example caps (NEW, benign); resonance.py `resonance_strength` no error handling (NEW) |

tempus.py: clean, no findings (one item re-confirmed correct per NEXT_STEPS).
