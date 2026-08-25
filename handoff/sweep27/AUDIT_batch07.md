# BATCH 07 AUDIT — sweep27

Modules read in full, every line:
- src/magnitude.py — 1026 lines (wc -l), read via Read tool (1027 lines reported incl. trailing)
- src/completeness.py — 455 lines
- src/address_space.py — 346 lines
- src/feats_index.py — 263 lines
- src/propagation.py — 214 lines
- src/cosmology_graph.py — 159 lines

Total: 2463 lines across 6 files.

Reference reads outside the batch, made only to verify a claim against a sibling module (not
audited themselves): src/silence.py (replace_retry/write_json, lines ~210-300), src/endpoint.py
(api_url/raw_url, lines ~176-190).

---

## src/magnitude.py

### 1. [HIGH] [CONFIRMED] Empty citation vacuously passes guard 1 VERBATIM — `verify()`, lines 341-364

```python
cn = _norm(cited)
hit = next((i for i, t in mined_norm.items()
            if t and (t in cn or cn in t or _overlap(t, cn) > 0.6)), None)
```

`cited = (got_ax.get("feat") or "").strip()` (line 344). If the model returns a numeric `score`
but an empty or whitespace-only `feat` string, `cn = _norm(cited)` is `""`. In Python, `"" in t`
is **always True** for any non-empty `t` — verified directly:

```
>>> "" in "goku punches the moon"
True
```

So `hit` resolves to the FIRST mined feat (dict-insertion order, i.e. feat `[1]`) for **any**
axis where the model supplies a number with an empty citation, regardless of what feat `[1]`
actually says. The score then only has to survive guard 2 (RELEVANCE, `AXIS_RE[ax].search(text)`
against feat `[1]`'s text) and guard 3 (SUBJECT) by coincidence — plausible, since feat `[1]` is
some real mined sentence and the axis lexicons are broad — to be published under `sheet[ax]`
citing a feat the model never actually cited. This directly defeats the guard the module's own
docstring calls "the easiest failure to catch and the most damaging to miss" (lines 28-29).

**Confirmed asymmetry**: the split-path equivalent, `_split_gate()` (line 561), explicitly
guards against this with `if isinstance(sc, (int, float)) and ft and any(ft in o for o in own):`
— the `and ft` clause rejects an empty citation before doing any containment check. `verify()`
has no equivalent floor.

**Failure scenario**: model returns `{"axes": {"ruin": {"score": 8.5, "feat": ""}}}` for an
entity whose mined feat `[1]` happens to be about, say, regeneration (matches `AXIS_RE["ruin"]`'s
broad "damage|wreck|kill" language somewhere in a longer sentence) and is written in active
voice. `scores["ruin"] = 8.5` lands in the published assay with `sheet["ruin"]` citing feat `[1]`
— a citation that does not exist in the model's actual output.

### 2. [HIGH] [CONFIRMED, known-open] `_split_gate()` never applies guard 3 SUBJECT — lines 553-571

Confirmed still true. `_split_gate()` checks verbatim containment only (`ft in o`); it never
calls `P._PATIENT.search` or `_HANDOFF.search` the way `verify()` does at line 373. Any
split-path entity (the DEFAULT path above `ONE_SHOT_MAX` = 30,000 chars, line 429, and the
default for evidence-heavy entities generally) can have an axis scored from a feat where the
entity is the PATIENT/handoff target rather than the doer, and nothing catches it. New context
found alongside it: the module's separate cross-axis-by-index check (lines 699-704,
`re.match(r"\s*\[(\d+)\]", cited)`) is also structurally a no-op for split-path results, because
`_one_axis()`'s prompt (lines 463-471) never numbers its candidate lines with `[n]` the way
`compose()` does — so split-path results get neither the SUBJECT guard nor a working cross-axis
index check, relying entirely on the "relevance by construction" assumption stated in
`_split_gate`'s docstring (lines 554-556). That construction assumption itself depends on
`feats.py`'s `F.by_axis()`, which is outside this batch and unverified here — flagging as a
question for whoever owns feats.py: does `by_axis()` actually filter as strictly as
`AXIS_LEXICON`/`AXIS_RE` do?

### 3. [MEDIUM] [CONFIRMED] Quality-failure retry trigger (`if not sheet`) is too narrow — lines 668-677

```python
scores, sheet, rejects = verify(entity, got, ev_v)
if not sheet and any(cand.values()):
    retry = _split_assay(...)
```

The intent (per the comment at 670-676) is: if a one-shot's citations ALL fail verbatim
verification, treat it as a quality failure and retry via the more careful split path. But
`sheet[ax] = cited or st` (line 350) is set for every axis the model answers with a STRING
status ("none"/"unestimable"/"n/a"), not only for verified numeric axes. The system prompt
explicitly tells the model most entities get "two or three [numeric] scores" and the rest
statuses (line 308 of SYSTEM prompt) — the common case. So an entity where 2-3 numeric axes are
attempted and ALL of them fail verbatim/relevance/subject, while the other 8 axes are honestly
returned as statuses, ends up with a non-empty `sheet` (populated entirely by status-axis
placeholders) and the retry never fires — even though the entity got zero genuine numeric
citations through the gate. This is exactly the "Jace one-shot three times... every axis
rejected" failure class the comment describes, just narrower than the check that's supposed to
catch it: the check should test whether `scores` contains any successfully-verified NUMERIC
value, not whether `sheet` is non-empty.

### 4. [MEDIUM] [CONFIRMED] Per-slice transport failures are silently dropped, not retried, in `_split_assay._one_axis` — lines 451-482

```python
got = _ask(c, SYSTEM, prompt, AXIS_SCHEMA)
if not got:
    continue
```

`i` has already been advanced past the failed slice's block before this check, so on a `None`
result the block is simply skipped — no retry, no note distinguishing "transport failed on this
slice" from "no evidence in this slice." If EVERY slice for an axis fails this way, `best` stays
`None` and the function returns `{"score": A.UNESTIMABLE, "feat": ""}` (lines 481-482) —
indistinguishable from a genuine absence-of-evidence axis. Because `settled()` (lines 885-908)
only treats `status == "DEFERRED"` as unfinished, an entity that scores successfully overall but
lost one or more axes to dropped slices is marked done and never revisited. This is the same
class of "transport failure wearing a result's clothes" the module's own `settled()` docstring
(lines 895-899) explicitly says was a defect worth rebuilding the function to avoid — but it
recurs here one layer down, per-axis-per-slice.

### 5. [HIGH] [CONFIRMED] `run_batch.work()` bypasses `silence.write_json`, uses a fixed-name tmp file — lines 966-983

```python
tmp = OUT + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(done, f, ensure_ascii=False)
for attempt in range(5):
    try:
        os.replace(tmp, OUT)
        break
    except PermissionError:
        ...
```

This is a raw `open()+json.dump()` write with a hand-rolled retry loop that duplicates
`silence.replace_retry`'s own logic, instead of calling `silence.write_json` (the canonical
helper `silence.py` documents — lines 250-287 there — as "the one correct way to write a shared
file in this project," fixed at "TWELVE call sites across ten modules" in the 2026-08-25
comprehensive sweep). Critically, the tmp filename here is FIXED (`OUT + ".tmp"`), not
PID/thread-tagged the way `silence.write_json` builds its tmp name (`"%s.%d.%d.tmp" %
(path, os.getpid(), threading.get_ident())`, silence.py:276) — silence.py's own docstring names
exactly this hazard: "Two writers of the same path otherwise collide on the temp file itself, and
the loser can replace the winner's target with a partial file." Within one process the
`with lock:` block (line 949/960) serializes writer threads safely, but if TWO `run_batch`
invocations are launched concurrently — plausible, since `main()`/`--host` supports splitting a
run by wiki (line 1006) — both processes race on the identical `data/ASSAYS.json.tmp` path with
no cross-process coordination at all.

### 6. [LOW] [CONFIRMED] `calibrate()` also bypasses `silence.write_json` — lines 814-817

Same pattern, lower severity: writes `data/CHARTER_REGRESSION.json` via raw
`open(tmp,'w')+json.dump` with a fixed-name tmp (`_cr + ".tmp"`), but at least calls
`silence.replace_retry(_cr + ".tmp", _cr)` for the atomic rename (line 817) — partial compliance.
Lower risk since `calibrate()` is normally run standalone, not from concurrent processes.

### 7. [LOW] [CONFIRMED] Stale diagnostic tag — line 235

`silence.note("magnitude.py:151")` inside `quantity_scores()`'s except clause (line 234) — the
literal string names line 151, but the code has moved; the actual call site is now at line 235.
Every other `silence.note(...)` call in this file uses a descriptive tag
("magnitude.py:pool_ready", "magnitude.py:_ask-cascade", etc.); this is the only one using a raw
line number, and it is now wrong, which will misdirect anyone using health/failure logs to find
the site.

### Known-open items confirmed still live (not re-litigated, cross-checked)

- Lines 224-251 (`quantity_scores`) calling `A.axis_score(x, anchor, axis)` at line 244, whose
  results overwrite `scores[ax]` at lines 709-711 (`for ax, q in quantity_scores(ev, anchor).items():
  scores[ax] = q["score"]`). Call path confirmed live; `assay.axis_score`'s own M10 behavior is
  out of scope for this batch per the task brief.

---

## src/completeness.py

### 8. [HIGH] [CONFIRMED, known-open] `host_reachable()` gates on API-mode-only `endpoint.api_url()` — lines 155-208, consumed at line 259

Confirmed via `endpoint.py`: `api_url(host)` (endpoint.py:176-179) returns `None` unless
`d["mode"] == MODE_API`. `host_reachable()` (completeness.py:193-198) does:
```python
base = EP.api_url(host)
if not base:
    _REACH[host] = False
    return False
```
So every RAW-mode wiki (any source that closed its API and only serves `index.php?action=raw`)
is unconditionally reported unreachable, regardless of whether it is actually up. Consumed at
`work()` line 259: `if not host_reachable(host): return {..."coverage": 0.0, "unreliable": "host
unreachable"...}` — every RAW-mode source in `COMPLETENESS.json` permanently reads 0% coverage
with an "unreachable" label that is never actually tested against the real (raw-mode) endpoint.

### 9. [HIGH] [CONFIRMED] Unlocked cross-thread race on the fixed-name cache tmp file — `category_size_probe()`, lines 110-118, called from a 6-worker `ThreadPoolExecutor`

```python
tmp = _CS_CACHE_P + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(cache, f)
silence.replace_retry(tmp, _CS_CACHE_P)
```

`state/category_sizes.json`'s tmp file is FIXED-NAME (no PID/thread tag), written via raw
`open()+json.dump` rather than `silence.write_json`. `category_size_probe()` is called from
`audit()`'s `work()` (line 273), which itself runs under `ThreadPoolExecutor(max_workers=workers)`
(default 6, lines 211/333) with **no lock** around the cache write. Any two worker threads probing
different `(sub, category)` pairs in the same run can call `category_size_probe` concurrently;
both open the identical `state/category_sizes.json.tmp` path, and one thread's `open(tmp,"w")`
(which truncates on open) can land between another thread's write and its `replace_retry` call,
corrupting or losing entries in the shared cache. This is the exact class of bug `silence.py`'s
`write_json` docstring says the project-wide 2026-08-25 sweep fixed elsewhere; this call site
still uses the old pattern.

### 10. [LOW] `land()`'s own write (lines 389-391, 401) — not `silence.write_json`

Uses a fixed-name tmp + raw `json.dump`, then explicitly calls `silence.replace_retry` — same
partial-compliance pattern as magnitude.py's `calibrate()`. Low risk here specifically: `land()`
runs single-threaded from `main()` after `audit()` has already returned, so there's no
concurrent-writer exposure within this module; the surrounding shrink-floor and prior-preservation
logic (lines 362-407) is otherwise careful and well-reasoned. Noting only for consistency with
findings 5/6/9 above — this is the fourth near-miss on the same helper in this batch alone.

---

## src/address_space.py

### 11. [MEDIUM] [CONFIRMED, known-open] `fit()` silently wraps overflow via modulo — lines 251-252, field widths at 106-142

Confirmed still true. `_tier_counts()` (106-116) and the `FIELDS`/`WIDTHS` block (130-142) size
each charted-tier field to exactly `max_value_seen_in_TIERS.json + 1`, computed once at import
time, with zero headroom. `assign()`'s `fit()` helper:
```python
def fit(v, field):
    return (0 if v is None else int(v)) % (1 << WIDTHS[field])
```
silently wraps any out-of-range tier value via modulo, in direct contrast to `pack()` (lines
145-159), which raises `ValueError` for the identical situation ("Raises rather than
truncating: a silently wrapped address would name a different world, which is the one failure
mode worth being loud about" — pack()'s own docstring, lines 147-148). Concrete scenario: a
longer-running process imports `address_space` once (caching `WIDTHS` for its lifetime), then
`TIERS.json` is updated elsewhere with a new, higher tier value (e.g. a 169th multiverse) before
that process re-imports the module — `assign()` would silently alias the new entity's address
onto an existing, wrong slot instead of raising the loud error `pack()` would give for the exact
same out-of-range value.

### 12. [MEDIUM] [CONFIRMED] `main()`'s field-derivation printout is broken by a length-mismatched `zip()` — lines 270-277

```python
srcs = ["weave.py: 8 divisions breaks the six-degree diameter",
        "168 continuities resolved by the weave",
        "Lauer et al. 2021 (New Horizons LORRI)",
        "dwarf-dominated mean stars per galaxy",
        "Cassan et al. 2012, Nature"]
for (name, n), s in zip(FIELDS, srcs):
    print(...)
```
`FIELDS` has 8 entries (hyperverse, xenoverse, metaverse, multiverse, universe, galaxy, star,
planet); `srcs` has only 5. `zip()` silently truncates to the shorter list, so the printed
"WIDTHS ARE DERIVED" table (the module's own showcase claim, lines 29-41 of the module
docstring) never shows galaxy, star, or planet at all — the three fields that actually carry
real literature citations (Lauer et al. 2021, Cassan et al. 2012). Worse, the five `srcs`
entries that DO print are misaligned against the fields they land next to: `srcs[1]` ("168
continuities resolved by the weave") prints against `xenoverse` (FIELDS[1]) when the 168 figure
is the `multiverse` count (FIELDS[3]); `srcs[2]` ("Lauer et al. 2021") prints against
`metaverse` when it belongs to `galaxy`; `srcs[3]` ("dwarf-dominated mean stars per galaxy")
prints against `multiverse` when it belongs to `star`. This is a display-only bug — the actual
`WIDTHS` computation (line 140) is unaffected, since it iterates `FIELDS` directly, not via
`srcs` — but the CLI's own explanatory output actively misattributes citations and drops the
three most citation-backed fields, directly undercutting the "not chosen, derived" claim it
exists to demonstrate.

### 13. [LOW] [CONFIRMED] Dead sentinel — line 120

`UNADDRESSED = None` (with explanatory comment) is defined but never referenced again anywhere
in this file or elsewhere in `src/` (grepped the whole tree). Orphaned constant, possibly a
half-wired feature.

---

## src/feats_index.py

### 14. [LOW] [SUSPECTED] Silent collision in `entries_by_norm` — line 188

`entries_by_norm.setdefault(_norm(e.get("name")), e)` inside `feats_for_source()`: if two
catalogue entries in the same source's `entries` list normalize to the same key, only the first
(by list order) survives, and any matching feats attach to that entry's data regardless of which
entry the mined material actually concerns. Not verified against real data (would need a source
with genuine normalized-name collisions to confirm impact); flagging as a plausible edge case
given `_norm()`'s own docstring (lines 90-111) already documents other near-miss collision
scenarios for the same folding function.

### 15. [LOW] [SUSPECTED] Underscore-to-dot host reconstruction may mis-derive hostnames — line 148

`host = host_dir.replace("_", ".").lower()` in `load_index()`. If a real subdomain label
legitimately contains an underscore, this blanket replace would produce a hostname string that
can never match `WIKI_HOSTS.json`, silently inflating the "NOT IN WIKI_HOSTS" stranded bucket
`audit()`/`main()` report (lines 253-258). Cannot confirm without reading `feats.py` (out of this
batch's scope) to see how `readfeats/<host_dir>/` directories are actually named upstream —
flagging as a question, not a confirmed bug.

---

## src/propagation.py

Read in full, no findings. The Dijkstra implementation (lines 85-112) is a correct standard
shortest-path; the two-clock model (`ascension_years` vertical vs `arrival_years` lateral,
lines 119-158) is internally consistent with its own documented correction history (the module's
comments describe a prior bug — summing lateral and vertical cost — and the current code matches
the fix as described); no caps, no bare excepts, no shared-file writes in this module at all
(`load_graph()` raises loudly on a missing/malformed file rather than swallowing). Nothing to
report.

---

## src/cosmology_graph.py

### 16. [MEDIUM] [SUSPECTED — may be deliberate, but undocumented and unreported] Undocumented hardcoded threshold silently excludes single-entity pair evidence from the written graph — line 151

```python
"pairs": [{"a": a, "b": b, "weight": round(w, 3), "shared_sample": pair_shared[(a, b)]}
          for (a, b), w in sorted(pair_w.items(), key=lambda kv: -kv[1])
          if w >= 1.0],
```

`w = 1.0 / math.log(n + 1.5)` (line 78), optionally `*= 0.15` if `n > UBIQUITOUS_CUTOFF` (line
80). For the strongest possible single-entity signal allowed by the code (`n = 2`, the minimum
group size after the `if n < 2: continue` filter at line 73), `w ≈ 1/ln(3.5) ≈ 0.798` — already
below the 1.0 cutoff. Since weight only decreases as `n` grows, **no single shared entity, no
matter how rare, can ever by itself cross the 1.0 threshold** — a source pair needs at least two
distinct shared entities before it appears in `SHARED_STAGE_GRAPH.json` at all. This sits three
lines below a comment (86-92) citing an explicit 2026-08-24 owner ruling against capping this
same function's `shared_sample` list, and a few lines below `UBIQUITOUS_CUTOFF` (line 59), which
IS explicitly commented as "kept explicit rather than purely threshold-based so the reasoning is
auditable" — the 1.0 pair-inclusion cutoff carries no equivalent comment, no CLI exposure (unlike
`components()`'s `--threshold`, which defaults to 3.0 and is a visible flag), and no reported
count of how many candidate pairs were silently dropped by it. Downstream, `propagation.py`
treats any pair absent from the graph as fully "DISCONNECTED (no shared furniture at any
remove)" — a much stronger claim than "below an unexplained threshold." Framing as a question for
the owner rather than a confirmed defect: requiring corroboration before persisting an edge is a
defensible design choice, but as written it is silent, unexplained, and unmeasured in a codebase
that is otherwise scrupulous about exactly this kind of cutoff.
