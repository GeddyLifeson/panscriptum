# Sweep 28 — Batch 09 Audit

Modules: `src/hostcheck.py` (955 lines), `src/manifest_builder.py` (478), `src/reference.py`
(358), `src/sevenfold.py` (274), `src/catalogue_codex.py` (215), `src/retry_synthesis.py` (164).
Total 2,444 lines, every line read.

---

## SPECIAL FOCUS ANSWER — does hostcheck.py explain the 93%/100% "reachable wiki" gap?

**Metric traced to source.** `standards.py:558-563` computes `frac = src["with_host"] / src["total"]`
against `MIN_HOST_COVERAGE = 1.0` (`standards.py:76`). `with_host` comes from
`dashboard.py:247`: `with_host = [s for s in recs if hosts.get(s)]` — i.e. the metric is **purely
"does this source have any string in `WIKI_HOSTS.json`"**, not "does `HOST_FITNESS.json` say the
host holds the fiction." So the 7-point gap is entirely about sources with **no host entry at
all**, and the mechanism that removes a host entry entirely is `hostcheck.sweep()`'s `--repair`
path (`hosts.pop(k, None)` at `hostcheck.py:581`) and `adopt()` simply never finding one.

**Live count today:** 216 catalogued sources, 196 with a host = 90.7% (close to the stated 93%,
different snapshot time). The 20 hostless sources were enumerated; several (`Clockwork Angels
(Rush)`, `The Elements Beyond`) are literally the module's own worked examples of hosts that were
correctly rejected as wrong-fiction (a periodic-table wiki, an unrelated board-game wiki), and
`the Witch Tradition` is one of only 3 rows currently in `HOST_UNFIT.json`, rejected at 0% about /
NAMES ONLY — a plausible correct rejection. The other two `HOST_UNFIT.json` rows (`Extra Life`,
`War Thunder …`) look similarly genuine (100% held, 0% about — classic wrong-fiction pattern).

**Can this code turn a reachable, correct wiki into "no host" (explaining the gap)? YES, by a
confirmed mechanism, though the present `HOST_UNFIT.json` snapshot (3 rows) does not show it
having fired wrongly yet:**

- `null_rate()` (`hostcheck.py:394-423`) folding a failed baseline probe to `0.0` **inflates**
  `lift` (`lift = rate - base`, and `base` is falsely low), which biases a host *toward* `"holds"`,
  not away from it — so on its own this does not explain hosts being wrongly rejected. It is a
  real, reproducible defect, but its risk is the opposite direction: false *adoption* of a wrong
  host, not false *unassignment* of a right one.
- The mechanism that DOES turn "right host, one noisy reading" into permanent "no host" is
  `judged_any` in `sweep()`'s repair loop (`hostcheck.py:534,538,549,559-562`), confirmed by code
  trace: a source enters the `wrong` list only if its current host got a real (non-UNREACHABLE)
  bad verdict. The repair loop then tries `candidates()`. `judged_any` is set True the moment
  **any single candidate**, however implausible, returns a real (reachable) verdict — even
  `"WRONG FICTION"` on an obvious squatter subdomain. If the real correct alternative (or a retry
  of the actual host) happens to be UNREACHABLE that pass (network blip, throttling), the loop
  still concludes `judged_any=True`, finds no candidate scoring above `DEAD`, and falls to the
  final `else`: **`fixed[src] = None`, unfitting and popping the source's host entirely**
  (`hostcheck.py:559-562,581`). This is a real path from "temporarily bad reading" to "permanently
  no host," which is exactly what would move a source from the numerator to the denominator-only
  side of the `with_host` metric.

**Verdict:** the code CAN explain the gap (mechanism confirmed, matches the already-filed NEXT_STEPS
item precisely), but the currently-recorded evidence (`HOST_UNFIT.json`, 3 rows, all plausible
correct rejections) does not currently prove it IS the dominant cause of today's ~7-9% gap — most
of the 20 present hostless sources read as genuinely wiki-less niche items per the tool's own
stated examples. The `judged_any` defect is real, unfixed, and is a live risk every time `--repair`
runs, particularly given `--repair` (unlike `--purge`/`--adopt`) has **no `--go` gate** — a single
`--repair` invocation writes `WIKI_HOSTS.json` and `HOST_UNFIT.json` immediately.

---

## src/hostcheck.py

### KNOWN — STILL OPEN — `null_rate()` folds a failed baseline probe to 0.0, caches process-wide
**hostcheck.py:394-423, esp. :419-420**
```python
r = probe(host, foreign) or {}
rate = r.get("rate")
rate = 0.0 if rate is None else rate
with _NULL_LOCK:
    _NULL_CACHE[host] = rate
return rate
```
`probe()` returns `rate=None` specifically to distinguish "the request failed" from "the host
answered nothing" (see `probe()`'s own comment at :150-155 about this exact conflation). This
function immediately re-commits the conflation it exists to avoid: a baseline probe that times out
is treated as "this host generously answers 0% of foreign names," cached under `_NULL_CACHE[host]`
for the rest of the process, and reused by every later `score()` call against that host. Confirmed
unchanged at source. As analyzed above, this biases `lift` upward (favoring false "holds"), the
opposite direction from unassignment — a real defect, but not, by itself, an explanation for hosts
losing their assignment.

### KNOWN — STILL OPEN — `judged_any` lets one wrong-but-reachable candidate justify unassigning
**hostcheck.py:534,538,549-562**
```python
judged_any = judged_any or not p["verdict"].startswith("UNREACHABLE")
...
elif not judged_any:
    print(f"  -> {src}: no candidate answered; keeping {r['host']} for now")
elif r["verdict"] == "partial":
    print(f"  -> {src}: nothing better; keeping {r['host']} ({r['rate']:.0%})")
else:
    print(f"  -> {src}: no host holds this fiction; left unassigned")
    fixed[src] = None
```
See the special-focus section above for the full trace. Failure scenario: source X's current host
scores `NAMES ONLY` this pass (real answer). Among `candidates()`, the true correct alternative (or
Wikipedia) is UNREACHABLE this pass, but one squatter subdomain answers with a real (bad) verdict.
`judged_any` becomes True on that one bad answer alone; `best` never clears `DEAD`; verdict is not
`"partial"`; falls to `else` → the source is fully unassigned (`hosts.pop`) and recorded in
`HOST_UNFIT.json`, even though nothing has actually proven no wiki holds the fiction — only that
one junk candidate and the real answer were both bad/unreachable this one pass.

### KNOWN — STILL OPEN — `--repair` has no `--go` gate
**hostcheck.py:916-917 vs :933,939 (`--adopt`/`--purge` both gate on `--go`)**
`--adopt` and `--purge` both require `--go` to actually write (`dry=not a.go`); `--repair` writes
`WIKI_HOSTS.json`/`HOST_UNFIT.json` unconditionally the moment `wrong` is non-empty
(`hostcheck.py:524` `if repair and wrong:`). Given the `judged_any` defect above, this means a
single `--repair` run can silently drop a source's host with no dry-run step to review first.

### NEW — MEDIUM — `null_rate()`'s cache key ignores `exclude`, contradicting its own determinism claim
**hostcheck.py:390-423**
```python
_NULL_CACHE = {}
...
def null_rate(host, by=None, exclude=None, sample=40):
    with _NULL_LOCK:
        if host in _NULL_CACHE:
            return _NULL_CACHE[host]
    foreign = []
    for src, names in (by or {}).items():
        if src == exclude:
            continue
        ...
    with _NULL_LOCK:
        _NULL_CACHE[host] = rate
    return rate
```
The cache is keyed on `host` alone; `exclude` (the calling source, so its own names are not counted
as "foreign") is silently dropped from the cache key. The docstring says: "Deterministic, not
random: the control must be reproducible, or two runs disagree about the same host for reasons
nobody can inspect" — but within a SINGLE run, the first source to score a given host commits that
host's baseline for every later source sharing it, computed with the WRONG source excluded.
Concrete scenario: `sweep()`'s `ThreadPoolExecutor` processes sources over shared hosts (e.g.
`forgottenrealms.fandom.com` serves many D&D sources); whichever source's `score()` call reaches
`null_rate()` first for that host permanently sets the baseline every other D&D source on that host
will use, computed while excluding the FIRST source's names rather than each subsequent source's
own. Numeric impact is small (≤3 of up to 40 sampled names differ per exclusion, and results are
sub-sampled by a stride), but it is a genuine, demonstrable violation of the stated contract and
worth a one-line fix (`_NULL_CACHE[(host, exclude)]`).

### NEW — MEDIUM — `relevance()`'s ABOUT veto samples only the first 12 of up to 40 hits
**hostcheck.py:187,199**
```python
def relevance(host, titles, source, sample=12):
    ...
    titles = [t for t in titles if t][:sample]
```
`probe()` returns up to 40 live titles (`titles` field, unlimited — only `examples` is capped to
5). `relevance()` is the function that decides the `about` veto (`score()`:465-466,477-478), which
can flip a host's verdict from `"holds"` to `"NAMES ONLY"` on generous hosts (`base >=
ABOUT_VETO_ABOVE`). It only ever reads bodies for the FIRST 12 titles in whatever order the
MediaWiki API's `pages` dict happened to return them (not guaranteed relevance-sorted). Per the
project's own Hard Rule 0 framing ("a cap on a diagnostic hides the pattern, not just the rows"),
this is exactly that shape: if the source-identifying content lives in hit #13-40, the aboutness
test never sees it and can wrongly veto a genuinely-held source into `NAMES ONLY`, which then feeds
the `judged_any`/unassignment path above. Speculative on real-world frequency (would need a probe
whose hit order buries the distinctive titles), but the mechanism is real and unguarded.

### NEW — LOW — RAW-mode probe judges hosts on 12 names, not 40
**hostcheck.py:128,134-139**
```python
names = [n for n in names if n and len(n) > 1][:PROBE]      # PROBE = 40
...
if EP.detect(host)["mode"] == EP.MODE_RAW:
    got = EP.fetch_raw(host, names[:12])
    n = min(len(names), 12)
```
API-mode hosts are judged on up to 40 names in one batched call; RAW-mode hosts (no batch query
available) are judged on only 12, each fetched individually. This halves-to-thirds the sample size
right at the point where `MIN_PROBE = 5` already treats small samples as noisy, so RAW-mode hosts
carry systematically weaker evidence for the same verdict categories. Reasoned in the code comment
as a cost tradeoff (one HTTP fetch per title vs one batched query), so likely deliberate, but it is
an inconsistency in evidentiary standard between the two host classes worth naming.

### NEW — MEDIUM — `--purge`'s `argparse` help text contradicts the function's own corrected docstring
**hostcheck.py:918-919 vs purge()'s docstring at :641-647**
```python
ap.add_argument("--purge", action="store_true",
                help="remove rosters the audit rejected AND whose host was independently rejected")
```
`purge()`'s own docstring, a few hundred lines above, explicitly says this exact claim used to be
FALSE and was corrected: *"An earlier docstring claimed the code also required the host to have
been independently rejected; it never did (the check was loaded and unused)... nothing is purged
except sources a person explicitly listed with `--source`."* The docstring fix was never propagated
to the `argparse` help string, so `python src/hostcheck.py --help` still tells an operator that an
automatic safety gate exists (independent host rejection) before a `--purge --go` deletes catalogue
entries — it does not. This is user-facing documentation for a destructive, irreversible-on-disk
operation, actively contradicting the very docstring that documents the correction.

---

## src/manifest_builder.py

### KNOWN — STILL OPEN — raw write to shared manifest file
**manifest_builder.py:436-437**
```python
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"jobs": all_jobs}, f, indent=2)
```
No tmp+`silence.replace_retry`/`silence.write_json`. Listed in NEXT_STEPS §3 among the raw-write
group (`worldseed.py:317-322, manifest_builder.py:436-437, burgs.py:226-229,
retry_synthesis.py:44-47, module_index.py:75`). Confirmed unchanged at source — the manifest is
written by a bare `open(path,"w")` + `json.dump`, no atomicity, and `generate.py` reads this same
path as a resumable job queue, so a kill mid-write truncates the file it depends on.

No other correctness bugs found in this module on a full read. `load_record()`'s substring-matching
(documented at :72-89 as already fixed once, by ranking on length-difference rather than match
order) was traced through with the concrete "DC" → sword-coast-adventurer's-guide false substring
match it names, and the ranking-by-closeness fix does correctly prefer an exact-length match when
one exists — confirmed as designed, not re-broken. `content_hash()`, `pack_feats()`,
`series_members`/`volume_code` numbering, and the `unassigned_sources.md` report-clearing logic
(:446-474) were all traced and are internally consistent with their own stated fixes.

---

## src/reference.py

### KNOWN — STILL OPEN — `shelfmark()` hardcodes `RUNGS[3+i]` assuming `upper` has exactly 3 elements
**reference.py:232-246**
```python
upper = []
for i in range(len(parts)):
    k = ".".join(parts[:i + 1])
    upper.append(nav["nodes"].get(k, {}).get("name", k))
...
marks = [f"{RUNGS[i]}{v}" for i, v in enumerate(upper)]
marks += [f"{RUNGS[3 + i]}{v}" for i, v in enumerate(lower)]
```
`len(upper) == len(rec["tier_key"].split("."))`. All three current `REFERENCE` entries use 3-part
`tier_key`s (`"1.6.1"`, `"4.2.0"`, `"1.2.5"`), so `RUNGS[3+i]` happens to line up. The offset is a
literal `3`, not `len(upper)`, so a `tier_key` with 2 or 4 dot-separated parts (or a NAVTREE lookup
failure falling back to the except-branch `upper = ["?", "?", "?"]`, which is always exactly 3 and
masks the general case) would silently misalign every lower rung — e.g. with `len(upper)==2`, the
mark for the third upper rung (`RUNGS[2]`, `"Mt."`) is skipped and the first lower rung is printed
under `RUNGS[3]` (`"Mv."`) instead of `RUNGS[2]`. Confirmed unchanged at source; reproduced-live
claim already stands from a prior run.

No other correctness issues found. `compute()`, `card()`, `citation()`, `_vernacular()`, and the
`--compare` branch in `main()` were all traced; the `A.LADDER.index(...)` lookups and the write at
:333 (`silence.write_json`, correctly atomic, comment references the same 2026-08-25 fix as
`sevenfold.py`) are consistent. Minor doc-drift only: `SOURCE_TIERS` comment in `sevenfold.py`
(below) says "209 sources" where the live corpus is 216 — not this file, noted there.

---

## src/sevenfold.py

### KNOWN — STILL OPEN — world-level `shelve()` call gets empty weights, degenerates into 1 giant
block + singletons
**sevenfold.py:204**
```python
inner = shelve(names, {}, depth=len(WORLD_TIERS))
```
Reproduced by direct trace of `shelve()`→`seams()`: with `weights={}`, every adjacent gap in
`seams()` scores `0.0` (`weights.get((a,b), weights.get((b,a), 0.0))` — always the default), so
`gaps.sort()` breaks every tie by index, keeping the list in its original (sorted) order; the first
`k-1` indices (0..5 for `span=7`) are always chosen as cuts, regardless of content. For a 50-member
block this produces child sizes `[1,1,1,1,1,1,44]` (six singleton leaves plus one 44-member giant
block) — the exact figures cited in NEXT_STEPS, reproduced by static trace (no execution needed;
the arithmetic is deterministic). This defeats the whole stated purpose of `shelve()`
("Balance is by construction… so no branch can swell into the giant component that wrecked every
discovered scheme" — :101-104) at the one call site that matters for WORLD shelving, because that
site is the one place `shelve()` is called without real weights.

No other correctness issues found. `affinity_order()`, `build()`'s two-stage source/world split,
`shelfmark()`, and the tier-balance printout in `main()` (including the self-aware dead-check at
:241-245, already flagged by its own comment as a guarantee rather than a discovery) were all
traced and are internally consistent. Doc-drift only: `SOURCE_TIERS` comment at :170 says "343
slots for 209 sources"; live corpus (`data/records/*.json`) is 216 sources today — stale by 7, not
a functional bug (343 still comfortably exceeds 216).

---

## src/catalogue_codex.py

No HIGH or MEDIUM findings. Full read confirms:
- `parse_codex()`'s per-line regex (`^\s{2,}(.+?)\s*\((\d+)\):\s*(.+?)$`) was checked against the
  live codex file at `C:\Users\imarl\Documents\5e Character Builder\custom\THE_PRIME_OMNIVERSE_CODEX.md`
  (64 sections parsed) — every "Type (N): item1; item2; …" line's declared count N matches the
  actual number of semicolon-separated items parsed, so the single-line-only regex is not currently
  truncating any wrapped manifest lines. **LOW / speculative**: the code never validates the
  declared N against the parsed count, so a future malformed line (stray semicolon, line wrap)
  would silently accept whatever the regex found rather than flagging a mismatch — no current
  evidence of this happening, noted for completeness only.
- The `--dry-run` gate, `write_record_catalogue()` usage (correct two-writer contract compliance),
  and the roll-file write at :205-209 (`silence.write_json`, comment confirms this was fixed
  2026-08-25, replacing a prior non-atomic write) were all traced and are consistent with their own
  documentation. `TYPE_CATEGORY` mapping and `norm()`/`slug()` helpers have no edge-case bugs found.

---

## src/retry_synthesis.py

### KNOWN — RECORDED IN NEXT_STEPS §1 (Owner Ruling #9) — STILL OPEN — `sample=[:14]` is not
"byte-identical" to `phase_synthesis`, and the divergence is a Hard Rule 0 cap
**retry_synthesis.py:56-67, verified against `pipeline.py:655-734` (`phase_synthesis`)**
```python
def synthesise(c, rec):
    """Byte-identical prompt construction to phase_synthesis, so a retried source is not
    scored by a different method than its neighbours."""
    sample = sorted(rec["entries"], key=lambda e: -len(e.get("description", "")))[:14]
```
Directly diffed against the real `phase_synthesis` (`pipeline.py:693-707`):
- `phase_synthesis` sorts feat-bearing entries FIRST (`with_feats`, ranked by mined-feat text
  length), and — critically — **every feat-bearing entity is nominated**, chunked 14-per-call
  across as many model calls as needed (`chunks = [with_feats[i:i+14] for i in
  range(0, len(with_feats), 14)] or [rest[:14]]`); only when there are ZERO feat-bearing entries
  does it fall back to one ranked chunk of description-only entries.
- `retry_synthesis.synthesise()` ignores feats entirely, sorts by description length only, and
  takes a single hard-capped top-14 slice — permanently discarding entities #15+ even when many of
  them carry mined feats that `phase_synthesis` would have shown the model in full.
This is a real, confirmed divergence (not speculative — directly diffed at source) and a genuine
Hard Rule 0 violation for any retried source with >14 feat-bearing entities: those beyond 14 (by
description length, an unrelated ranking) never reach the model at all in the retry path. Per
NEXT_STEPS, fixing it "multiplies model calls per retried source" — flagged there as needing an
owner ruling, not silently fixed.

### KNOWN — STILL OPEN — raw write to `SYNTHESIS_RETRY.json`
**retry_synthesis.py:43-47**
```python
def save_side(d):
    tmp = SIDE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    os.replace(tmp, SIDE)
```
Fixed-name `.tmp` + bare `os.replace` (no `silence.replace_retry` backoff). Listed in NEXT_STEPS
§3's raw-write group. The module's own docstring frames this file as exclusively owned by this
script ("appends results to `data/SYNTHESIS_RETRY.json`, which nothing else touches"), which limits
the real-world blast radius to two concurrent manual invocations of this same script racing each
other (no other module reads or writes this path) — genuinely lower risk than the multi-reader
shared files elsewhere in the tree, but still the pattern this project's shared-write contract
exists to standardize on, and still open at source.

### VERIFIED FIXED — `do_merge()` now writes through `pipeline.write_record`
**retry_synthesis.py:94-127, esp. :120**
The extensive comment at :109-119 documents a prior bug (bare truncating temp + `os.replace`
bypassing the two-writer contract, causing a 30,207→1,051 entry revert) and states it was fixed in
run #26. Confirmed at source: `do_merge()` now calls `PL.write_record(path, rec)` (:120) and
correctly handles a `False` return (denial) by skipping and logging rather than silently
proceeding. This one is resolved, not a re-opened "Fixed <date> comment hiding a still-open bug" —
included here only to record that it was checked and is clean.

No other correctness issues found in `failed_sources()`, `load_side()`, or `main()`'s to-do
selection loop (`r["source"] in want and r["source"] not in side and not r.get("synthesis")`),
which correctly excludes sources already retried or already carrying a synthesis block.
