# AUDIT batch08 — sweep24

Files in scope, all read in full, line by line, start to end:

- `src/feats.py` — 992 lines, read in full (1 Read call, complete).
- `src/completeness.py` — 456 lines, read in full.
- `src/address_space.py` — 347 lines, read in full; also executed live against the real
  `data/TIERS.json` / `data/WORLDSEEDS.json` on disk to confirm several findings empirically
  (not just static reading — see findings 6-8).
- `src/tuning.py` — 264 lines, read in full. No findings beyond cosmetic; module reads as
  correct and its docstrings match its code.
- `src/style_audit.py` — 212 lines, read in full. One cosmetic finding only; otherwise clean.
- `src/cosmology_graph.py` — 154 lines, read in full; cross-checked against `src/resonance.py`,
  `src/propagation.py`, and `src/weave.py` to trace where its output is actually consumed.

Also read for cross-reference (not part of the batch, not separately audited): `src/silence.py`
(`replace_retry`, `write_json`, `note`), `src/resonance.py:120-150`, `src/weave.py:200-482`,
relevant slices of `src/tiers.py`, and prior audit notes in `BUGS.md` / `HANDOFF.md` /
`handoff/sweep22/AUDIT_batch07.md` where a finding overlapped a previously logged item (noted
inline).

---

## feats.py

### 1. `api()` bare-except / 404 both return `None` — genuine absence indistinguishable from transport failure, and the chain that follows from it
**`feats.py:120-174`**
```python
def api(host, params, retries=2):
    ...
        except urllib.error.HTTPError as e:
            if e.code == 404:
                silence.note("feats.py:api-404")
                return None
            silence.note("feats.py:125")
            if e.code == 429: ...
            if attempt == retries:
                return None
            time.sleep(2 + attempt * 4)
        except Exception:
            silence.note("feats.py:139")
            if attempt == retries:
                return None
            time.sleep(2 + attempt * 4)
```
A clean 404 ("this page genuinely does not exist") and an exhausted-retries transport failure
(timeout, DNS failure, TLS error, 500, anything caught by the bare `except Exception`) return the
exact same value: `None`. The two `silence.note()` calls do separate the *counters*, but the
**return value** every caller actually branches on is identical either way.

Traced forward:
- `alive(host)` (`:177-178`) calls `api(..., retries=0)` — a single attempt, no retry budget at
  all — and returns `bool(api(...))`. A single transient timeout on the very first (and only)
  attempt makes `alive()` report a live wiki as dead.
- `resolve_hosts()` (`:243-299`) uses `alive()` in its slug-guessing loop (`:282-288`): if every
  guessed slug's `alive()` check fails (including from a transient timeout), it writes
  `known[src] = None` and persists that to `data/WIKI_HOSTS.json` via `silence.replace_retry`
  (correct two-writer mechanics — the bug is not there).
- On every subsequent run, the top-of-function check `if src in known: continue` (`:265-266`) is
  a **membership test**, not a truthiness test. `src in known` is `True` even when
  `known[src] is None`, so a source that failed one transient probe is never reconsidered again,
  ever — not by `--hosts`, and `--roll`'s call (`:965`, `verify=False`) doesn't even attempt
  fresh guessing.
- `roll()` (`:833-846`) builds jobs from `hosts.get(r["source"])`; `if not h: continue` (`:843`)
  silently drops the entire source from the roll forever, with no distinguishing signal that
  this was a network blip rather than "this fiction really has no wiki."
- `evidence_for()` (`:732-808`): when discovery/fetch return nothing (whether because the page
  genuinely doesn't exist or because `api()` swallowed a persistent transport failure), the
  written cache file (`:800-807`, correctly atomic via `silence.replace_retry`) has
  `pages_read: []`, `feats: []`, `text: {}` — byte-for-byte identical to a real "this entity has
  no evidence" result. No `fetch_failed` / `transport_error` flag exists anywhere in the schema.

**Failure scenario:** one Wikipedia timeout during `resolve_hosts()`'s slug-verification pass
permanently removes a source's wiki host from every future roll; a transient failure inside
`evidence_for()` for an existing host writes a cache file that reads exactly like "this hero has
zero attested feats," and nothing downstream (assay, magnitude) can tell the difference without
re-fetching by hand.
**Severity: MAJOR.**
**VERIFIED** — read end-to-end; the `known[src] = None` / `if src in known: continue` sequence
and the `roll()`/`evidence_for()` consequences are exactly as described.

### 2. `discover()` — `aplimit=500` / `srlimit=50` still truncate; only the truncation is now *measured*, not fixed
**`feats.py:311-368`**, especially:
```python
ap = api(host, {"action": "query", "list": "allpages",
                "apprefix": f"{name}/", "aplimit": "500"})
if (ap or {}).get("continue"):
    _CAP_BOUND["aplimit"] = _CAP_BOUND.get("aplimit", 0) + 1
...
sr = api(host, {"action": "query", "list": "search", "srlimit": "50", ...})
if (sr or {}).get("continue"):
    _CAP_BOUND["srlimit"] = _CAP_BOUND.get("srlimit", 0) + 1
```
The docstring (`:315-323`) is candid that this is a live Hard Rule 0 violation and that a
`_CAP_BOUND` counter was added (m82) specifically to find out how often it bites — but no
continuation loop was added. When MediaWiki returns a `continue` token, that entity's page
discovery is still read in part and the run proceeds as if the list were complete; `_CAP_BOUND`
only gets printed in `roll()`'s summary after the fact (`:912-917`), which tells the operator
*after* a multi-hour roll that some unknown subset of entities were under-discovered, not which
ones, and does nothing to recover the missing pages on that run.
**Failure scenario:** an entity on a wiki with >500 subpages or >50 relevant search hits (exactly
the richest, most-written-about entities — the ones the whole project cares most about getting
right) is discovered in part, mines fewer feats than it has, and nothing short of reading the
printed `_CAP_BOUND` summary line reveals this happened.
**Severity: MAJOR** (Hard Rule 0 is explicit that measuring a cap does not satisfy the rule —
"the remedy... is only worth its cost if the cap ever binds," and the code stops one step short
of actually removing it).
**VERIFIED.**

### 3. `resolve_title()` / `_page_exists()` are fully-written, dead code — the documented fix for a 17,148-entry loss is never called
**`feats.py:376-424`**
`resolve_title(host, name)` carries a detailed, specific docstring describing a measured
production loss ("17,148 entries mined to nothing because the entity's catalogue name is not the
wiki's page title") and implements a careful ranked-candidate fix for it. Grepped every `.py`
under `src/` for `resolve_title(` and `_page_exists(`: the only occurrences are the definitions
themselves (`feats.py:376`, `feats.py:384`) — no caller anywhere, including `discover()`,
`fetch()`, `evidence_for()`, and `roll()`, all of which pass the catalogue's raw `name` straight
through instead.
**Failure scenario:** unchanged from what the docstring itself describes — "Hulk (Bruce Banner)"
still never resolves to the wiki's "Hulk," "Thor Odinson" still never resolves to its
Earth-designation title, and every such entity mines to zero.
**Severity: MAJOR.**
**VERIFIED** — and this one is not new: it is already logged as **m80** in `BUGS.md:428` and
`HANDOFF.md:860`, and was independently found by `handoff/sweep22/AUDIT_batch07.md`
(`feats.py:376-424`). Re-verified true as of this sweep; still unfixed.

### 4. `_RATE_LIMITED` / `_CAP_BOUND` module-level counters are incremented without a lock from `ThreadPoolExecutor` workers
**`feats.py:73, 85, 162, 351, 361`**
```python
_RATE_LIMITED[host] = _RATE_LIMITED.get(host, 0) + 1     # inside api(), called from N worker threads
...
_CAP_BOUND["aplimit"] = _CAP_BOUND.get("aplimit", 0) + 1  # inside discover(), same
```
Unlike `done` in `roll()` (which is correctly protected by `lock`, `:869/881-899`), these two
dicts are read-modify-written with no lock from every worker thread in `roll()`'s
`ThreadPoolExecutor(max_workers=workers)` (default 8). A `get()` + `+1` + `__setitem__` is not
atomic across threads; two workers racing on the same host/key can lose an increment.
**Failure scenario:** the "429s absorbed" and "discovery caps BOUND" counts printed at the end of
`roll()` (`:910-922`) undercount by a small, non-deterministic amount. Purely a diagnostic
statistic — no entity data is corrupted, no file is written from these dicts — but it is exactly
the kind of unlocked-shared-state pattern the project has hit before at real cost (see
`completeness.py` below, and `done`'s own comment at `:862-867` shows the author was aware
counters need care).
**Severity: MINOR** (diagnostic-only blast radius, but a genuine, easily-triggered race).
**VERIFIED.**

### 5. `silence.note()` site tags no longer match the lines they name
**`feats.py:159, 171, 451, 743, 878`** — tags like `"feats.py:125"`, `"feats.py:139"`,
`"feats.py:374"`, `"feats.py:695"` are literal strings baked in at authoring time; the file has
since grown/moved and none of those line numbers point at the call site anymore (e.g.
`"feats.py:125"` is emitted from what is now line 159). Doesn't change behavior — `silence.note`
just uses the string as an opaque bucket key for `health.record` — but it actively misleads
anyone using the failure ledger to jump to the actual code.
**Severity: COSMETIC.**
**VERIFIED.**

---

## completeness.py

### 6. `category_size_probe()` — shared global cache dict mutated *and* `json.dump`-iterated from unlocked `ThreadPoolExecutor` workers, over a fixed non-unique temp filename
**`feats.py` sibling bug, but in `completeness.py:71-119`**, most importantly:
```python
_CS_CACHE = {"loaded": False, "d": {}}
...
def category_size_probe(sub, category):
    ...
    cache = _cs_load()                       # returns the SAME dict object every call
    cache[k] = {"at": time.time(), "n": got}  # mutated from every worker thread
    try:
        tmp = _CS_CACHE_P + ".tmp"            # ONE shared path, no pid/thread differentiation
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache, f)               # iterates the SAME dict another thread may insert into
        silence.replace_retry(tmp, _CS_CACHE_P)
    except Exception:
        silence.note("completeness.py:cs-cache")
```
This is called from `audit()`'s `work()` (`:248-331`), run under
`ThreadPoolExecutor(max_workers=workers)` (default 6, `:333`), 8 probes per source
(`ws.CATEGORY_PROBES[PERSONS]`), across every source in `hosts` concurrently.

Two independent hazards, both live:
- **Dict mutated during iteration.** `cache` is the literal module-global dict
  (`_CS_CACHE["d"]`), not a copy. While thread A's `json.dump(cache, f)` is iterating it, thread
  B (a different source/category, same global dict) can execute `cache[k] = {...}` for a *new*
  key, which CPython detects as a size change during iteration and raises
  `RuntimeError: dictionary changed size during iteration`. This is caught by the surrounding
  `except Exception: silence.note(...)` so it doesn't crash the audit, but it silently drops that
  thread's cache write.
- **Fixed temp filename shared across threads.** `src/silence.py`'s own `write_json()` docstring
  (`silence.py:250-269`, added 2026-08-25) documents this *exact* pattern as a previously-found,
  now-fixed project-wide defect: "Two writers of the same path otherwise collide on the temp file
  itself, and the loser can replace the winner's target with a partial file" — which is precisely
  why `write_json()`'s temp name carries PID and thread ID
  (`"%s.%d.%d.tmp" % (path, os.getpid(), threading.get_ident())`, `silence.py:276`).
  `category_size_probe()` was never migrated to `silence.write_json()`; it still uses the bare
  `_CS_CACHE_P + ".tmp"` pattern `write_json` exists to replace. Two threads opening the same
  path for write concurrently can interleave/truncate each other's bytes, and
  `silence.replace_retry` only catches `PermissionError` (`silence.py:223-240`) — a
  `FileNotFoundError` from a source file that a *different* thread already renamed away would
  propagate up (caught by the outer `except Exception` here, but silently, via `silence.note`).
**Failure scenario:** under real concurrency (6 workers × 8 probes/source across many sources —
exactly the shape `audit()` runs every foreman round per this file's own docstring, `:22-28`),
`state/category_sizes.json` can end up truncated or fail to parse. `_cs_load()`'s own
`except Exception: pass` (`:76-77`, "no cache yet is the normal first state") then treats that
corruption identically to a legitimate first run and silently resets the in-memory cache to
`{}` — which forces the *next* audit to re-probe every category live against fandom's API, which
is exactly the traffic pattern this module's own docstring says got the machine IP-banned once
already (`:126-128`).
**Severity: MAJOR.**
**VERIFIED** — this matches the run's own "known suspects" note precisely; confirmed by direct
reading of `completeness.py:71-119` cross-referenced against `silence.py`'s documented rationale
for `write_json()`, which exists specifically to close this pattern and was not applied here.

### 7. `byslug` fallback key is not lowercased, while every lookup is
**`completeness.py:216-219`**
```python
byslug = {}
for src, v in have.items():
    byslug[str(src).lower()] = v
    byslug[v["file"][:-5].replace("-", " ")] = v      # <- no .lower() here
```
compared against every lookup site (`:260, 298`):
```python
rec0 = byslug.get(str(src).lower()) or byslug.get(str(src).lower().replace("-", " "))
```
If a record filename ever contains an uppercase character, the second `byslug` key stored for it
can never be matched by any lookup, since every lookup key is `.lower()`-ed first. Currently
non-triggering: every filename under `data/records/` is already lowercase kebab-case (checked —
zero uppercase characters across the whole directory), so this is latent rather than live.
**Severity: MINOR** (verified-present, currently non-triggering).
**VERIFIED.**

---

## address_space.py

### 8. `assign()`/`fit()` silently converts an *unknown* hyperverse into a real, printed "H0" — indistinguishable from a genuinely charted hyperverse zero
**`address_space.py:240-261`**, the load-bearing line:
```python
def fit(v, field):
    return (0 if v is None else int(v)) % (1 << WIDTHS[field])
```
called as `fit(tiers.get("hyperverse"), "hyperverse")` (`:254`). When a source's `TIERS.json`
row has `"hyperverse": None` (or the source is missing from `TIERS.json` entirely — `main()`
passes `tiers.get(src) or {}`, `:327`, which collapses to the same `None`), this silently emits
`0` rather than any "unknown" sentinel, and `shelfmark()` (`:171-183`) prints it as a completely
ordinary `H0`, with no marker distinguishing it from a source whose hyperverse really was
resolved to index 0.

This directly contradicts the file's own repeatedly-stated principle, quoted from the charter in
its own docstring at `:82-83`: *"hyperverse position is uncharted; the Custodes considered
guessing a form of lying."* Guessing `0` and printing it as fact is exactly that.

**Empirically confirmed against the real data on disk** (not just static reading):
```
total worlds in data/WORLDSEEDS.json:                              1016
worlds whose SOURCE has hyperverse=None in data/TIERS.json:           12
worlds whose printed shelfmark hyperverse field == 0:                 12
```
All 12 match exactly — every world whose hyperverse is genuinely unknown is printed with a
fabricated, unmarked `H0`. (Separately: no source in the real `TIERS.json` has a *genuine*
hyperverse of `0` — the observed values are `{4: 146, None: 53, 5: 6, 2: 2, 3: 2}` — so in the
current data, every `H0` in a shelfmark is, without exception, a fabricated placeholder wearing
the shape of a real answer.)
**Severity: MAJOR.**
**VERIFIED** (statically and empirically, against live project data).

### 9. `shelfmark()`'s own docstring says H/X print as `'?'`; the code prints real numbers
**`address_space.py:171-183`**
```python
def shelfmark(addr):
    """The charter's own notation. H and X print as '?' because they are uncharted.
    ...
    """
    f = unpack(addr)
    return (f"Ω › H{f['hyperverse']} › X{f['xenoverse']} › Mt.{f['metaverse']} › "
            f"Mv.{f['multiverse']} › U-{f['universe']} › G.{f['galaxy']:x} › P.{f['planet']}")
```
Confirmed by direct execution:
```
>>> shelfmark(pack(hyperverse=3, xenoverse=2, metaverse=5, multiverse=97, universe=11,
                    galaxy=0x2A1F3B, star=0x5C91D2, planet=1))
'Ω › H3 › X2 › Mt.5 › Mv.97 › U-11 › G.2a1f3b › P.1'
```
`H3` and `X2` are literal integers, not `?`. This docstring is stale relative to the file's own
later "CORRECTED against Part Two" section (`:75-105`), which explains that hyperverse/xenoverse
*are* now charted via `tiers.py`'s dendrogram cuts and prints real values on purpose — but
`shelfmark()`'s own docstring, sitting directly above the function, was never updated to say so,
and instead asserts the opposite of what the function does. Combined with finding 8, a reader of
this docstring would reasonably conclude an unresolved hyperverse can never appear as a
misleading concrete number in a printed shelfmark — the opposite of the truth.
**Severity: MAJOR** (a maintainer or the owner reading this function's contract would be
actively misled about the file's central epistemic-honesty guarantee).
**VERIFIED.**

### 10. Header docstring's "74 bits, 10 bytes" / 5-field layout is stale; live code produces 89 bits / 12 bytes across 8 fields
**`address_space.py:26-27`**
```
    [ hyperverse | universe | galaxy | star | planet ]
         3 bits     5 bits    38 bits  27 bits  1 bit     = 74 bits, 10 bytes
```
This is the file's own title claim ("A 74-BIT NAME FOR EVERY PLANET IN THE OMNIVERSE," `:3`) and
per-field derivation table (`:29-41`, "THE WIDTHS ARE DERIVED, NOT CHOSEN"). It describes a
five-field scheme that predates the "CORRECTED against Part Two" rewrite further down
(`:75-105`), which added `xenoverse` and `metaverse` as genuine fields and repurposed `universe`
away from "24 continuities" to a plain bit-budget constant. Executed against the live code and
the real data on disk:
```
WIDTHS   {'hyperverse': 3, 'xenoverse': 3, 'metaverse': 3, 'multiverse': 8, 'universe': 6,
          'galaxy': 38, 'star': 27, 'planet': 1}
TOTAL_BITS 89   (12 bytes, not 10)
```
Not merely off by a little — it's a different number of fields entirely (8 live fields vs. 5
described), and the byte count the title leads with is wrong by 2 bytes / 15 bits.
**Severity: MAJOR** (this is the file's own headline claim, in the first ten lines, actively
wrong about what the code computes — a reader relying on it to reason about collision odds or
serialization size gets a materially wrong number).
**VERIFIED** (executed live).

### 11. `universe` field width is a hardcoded literal, not derived — directly under a docstring insisting the opposite
**`address_space.py:130-140`**
```python
FIELDS = [
    ("hyperverse", max(2, _TC["hyperverse"])),
    ("xenoverse",  max(2, _TC["xenoverse"])),
    ("metaverse",  max(2, _TC["metaverse"])),
    ("multiverse", max(2, _TC["multiverse"])),
    ("universe",   1 << 6),                    # <- literal 64, not derived from anything
    ("galaxy",     C.GALAXIES_DEFAULT),
    ("star",       C.STARS_PER_GALAXY_MEAN),
    ("planet",     C.PLANETS_PER_STAR),
]
```
The module's own "THE WIDTHS ARE DERIVED, NOT CHOSEN" section (`:29-41`) claims every field
width traces to a measured census value (and specifically claims `universe` = 24, "continuities
per hyperverse, from the 168 the catalogue resolved" — itself now describing a role that field no
longer has, since `multiverse` is what carries the 168-continuity count today, per `_TC`). The
live `universe` field is simply `1 << 6`, a flat constant untouched by `_TC`, `_continuities()`,
or any other measured quantity in the file. `_continuities()` (`:66-72`) is defined and reads
real data, but its only caller is the `main()` printout comparison (`:278`) — it never feeds
`FIELDS`.
**Severity: MAJOR** (this is the exact known-suspect item — verified precisely as described:
a "derived, not chosen" claim sitting directly above a hardcoded value).
**VERIFIED.**

### 12. `# hyperverse and xenoverse are NOT fields` sits three lines above the code that makes them fields
**`address_space.py:127-134`**
```python
# hyperverse and xenoverse are NOT fields. They are not unknown values awaiting a survey -- they
# are positions the charter declines to state, and reserving bits for them would invite filling
# them in.
FIELDS = [
    ("hyperverse", max(2, _TC["hyperverse"])),
    ("xenoverse",  max(2, _TC["xenoverse"])),
    ...
```
The comment is a leftover from before the "CORRECTED against Part Two" rewrite (`:75-105`)
reversed this exact decision and started charting hyperverse/xenoverse on purpose. It now sits
immediately adjacent to, and directly contradicts, the code it comments on. This is the same
staleness as findings 9-11 — several docstrings in this file describe an earlier design that a
later, documented correction superseded, and none of the earlier passages were removed or
updated. Worth flagging as its own item because it is the most literal instance: the comment's
claim ("NOT fields") is falsified by the very next non-blank statement.
**Severity: MINOR** (subsumed in spirit by findings 9-11, but distinct enough textually to name).
**VERIFIED.**

---

## cosmology_graph.py

### 13. `pair_shared` capped at 8 per pair — Hard Rule 0 violation, and the project's own later fix for this exact pattern landed in a different, currently-unread file
**`cosmology_graph.py:66-88`**, specifically:
```python
pair_shared = collections.defaultdict(list)
...
for i in range(n):
    for j in range(i + 1, n):
        p = (sources[i], sources[j])
        pair_w[p] += w
        if len(pair_shared[p]) < 8:
            pair_shared[p].append(name)
```
The relationship-strength number itself (`pair_w`, which drives `components()`'s clustering and
therefore `tiers.py`'s dendrogram cuts) is **not** capped — it accumulates over every co-attested
entity, unboundedly. Only the human-readable *list* of which entities were shared is capped at 8,
written to `data/SHARED_STAGE_GRAPH.json` under the key `"shared_sample"` (`:141-148`) — a key
name that half-admits the cap by calling itself a sample, which Hard Rule 0 explicitly forbids
("no limit, no cap, no sample, no 'top N'").

Read by `src/resonance.py:133-149`:
```python
def resonance_strength(a, b, graph_path=None):
    path = graph_path or os.path.join(HERE, "data/SHARED_STAGE_GRAPH.json")
    ...
    for p in g["pairs"]:
        if {p["a"], p["b"]} == {a, b}:
            return {"weight": p["weight"], "shared": p.get("shared_sample", []),
                    "in_resonance": True}
```
`resonance_strength()`'s `"shared"` return value is this same capped-at-8 list, presented to a
caller with no signal that it is partial when the real number of co-attested entities exceeds 8.

**Important nuance found by tracing forward:** `src/weave.py` already recognized and fixed this
*exact* cap, with an explicit Hard Rule 0 citation, dated 2026-08-24:
```python
# weave.py:217 (comment)
# NO CAP. `if len(shared[p]) < 8` was the last cap standing in the weave, and it ...
# weave.py:478
"shared_sample": shared[(a, b)]}   # WHOLE list (key name kept: resonance.py reads it) -- Hard Rule 0, ruled 2026-08-24
```
But `weave.py` writes this uncapped version to **`data/SHARED_STAGE_GRAPH_IDF.json`**
(`weave.py:82`, `OUT_GRAPH`) — a *different file* from the one `resonance.py` and
`propagation.py` actually read by default, which is **`data/SHARED_STAGE_GRAPH.json`**
(`resonance.py:141`, `propagation.py:46`), produced only by `cosmology_graph.py`. The 2026-08-24
fix comment in `weave.py` literally says "key name kept: resonance.py reads it" — an explicit
intent for `resonance.py` to pick up the uncapped version — but `resonance.py`'s default path
still points at `cosmology_graph.py`'s capped output, not `weave.py`'s fixed one. The fix and the
bug are both live in the tree, pointed at two different files, and the consumer reads the wrong
one.

**Also checked:** `resonance_strength()` currently has zero callers anywhere else in `src/`
(grepped), so the capped-evidence field is not actively driving a wrong decision *today* — but
Hard Rule 0's text is explicit that a cap on an evidence listing is a bug regardless of whether
today's caller happens to ignore the tail, and the moment anything calls `resonance_strength()`
for a citation or a report, it will silently under-report shared evidence for any pair sharing
more than 8 entities.
**Severity: MAJOR** (Hard Rule 0 violation, confirmed still live in the file the real consumers
actually default to, with a documented but misdirected fix sitting one file over).
**VERIFIED.**

---

## tuning.py

Read in full. No correctness bugs, no swallowed-failure-as-legitimate-result patterns, no caps
on anything corpus-shaped (the `workers` clamps are resource-pool sizing, not data truncation —
out of scope for Hard Rule 0), and every docstring checked against its code matched. The
"ZERO IS A REQUEST, NOT AN ABSENCE" fix at `workers()` (`:226-244`) was verified correct:
`min(requested, n) if requested is not None else n` correctly treats `0` as a real ceiling
request rather than falling through to the profile default. **No findings.**

## style_audit.py

Read in full. One cosmetic-only observation:

### 14. `[◈◈]` — duplicate identical character in a character class
**`style_audit.py:44`**
```python
parts = re.split(r"^[◈◈]\s*", text, flags=re.M)
```
Confirmed via codepoint inspection: both characters are `U+25C8` (◈), not two different
lookalike glyphs — so this is functionally identical to `[◈]`, not a masked second delimiter that
got typo'd into matching the wrong symbol. Grepped `prompts/` and `src/generate.py`: `◈` is the
only entry-opening marker actually used anywhere in the template. Harmless, but worth a second
look by whoever wrote it — the doubled character reads as if a second delimiter was intended and
never added, or as a stray copy-paste.
**Severity: COSMETIC.**
**VERIFIED.**

No other findings in this file. `record_of()`'s section-boundary regex
(`Contradictions|Marginalia|▣|⌁`) was checked against the actual entry template in
`prompts/system_style.txt` and matches all four real section markers correctly.

---

## Summary of severities

- MAJOR: 10 (feats.py ×3 new-verified [#1,#2,#3-reconfirmed-m80], completeness.py ×1 [#6],
  address_space.py ×4 [#8,#9,#10,#11], cosmology_graph.py ×1 [#13])
- MINOR: 4 (feats.py #4, completeness.py #7, address_space.py #12, and the diagnostic-only
  framing of #4)
- COSMETIC: 2 (feats.py #5, style_audit.py #14)
- Clean: tuning.py (no findings)
