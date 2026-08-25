# AUDIT — BATCH 11 (run32)

Auditor read every line of all seven assigned modules directly (no delegation). Line counts
(via `wc -l`, includes trailing newline count as reported):

| module | lines |
|---|---|
| src/hostcheck.py | 953 |
| src/generate.py | 497 |
| src/onomast.py | 407 |
| src/backfill.py | 300 |
| src/grounding.py | 245 |
| src/profile.py | 201 |
| src/ledger.py | 136 |

Also read (for cross-reference / confirmation only, not scored): src/silence.py (465 lines,
full), src/assay.py lines 71-260 (BAND_EDGES, LADDER, axis_score), src/prose_gate.py lines
1-139 (gate_open/assert_gate_open), src/pipeline.py lines 1880-1899 and around 1471-1520,
src/genre.py lines 1-40 and around 135-235, src/verify_math.py lines 800-844, src/tiers.py /
src/navtree.py grep context for onomast.register_for and grounding usage.

---

## BLOCKING

### 1. `hostcheck.py:67-80` (`_land`) discards `silence.replace_retry`'s return value — a persistently denied write reports success at all 7 call sites

`_land()`:
```python
def _land(path, obj, sort_keys=True, ensure_ascii=True):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=sort_keys, ensure_ascii=ensure_ascii)
    silence.replace_retry(tmp, path)          # <-- line 80, return value discarded
```
`silence.replace_retry` (src/silence.py:263-280) returns `True` on a landed rename and `False`
after all retry attempts are exhausted on a persistent `PermissionError` — the exact "reader is
holding the target open" scenario `_land`'s own docstring (lines 70-76) names as the reason this
function exists, and which silence.py's own docstring cites as having actually happened
(2026-08-23, WinError 5). `_land` never inspects that boolean, never raises, and has no return
value of its own, so **every caller has no way to know the write failed** — the `tmp` file is
left orphaned on disk and the target (`WIKI_HOSTS.json`, `HOST_UNFIT.json`, `HOST_FITNESS.json`,
a catalogue record file, `ROSTER_PURGES.json`, `ROSTER_AUDIT.json`) is left holding its old
content, unchanged.

Confirmed exactly 7 call sites of `_land(...)` in this file, each followed by an unconditional
success message:
- `hostcheck.py:591` `_land(F.HOSTS, hosts)` → line 593 prints `"WIKI_HOSTS.json updated: N repointed..."` regardless.
- `hostcheck.py:592` `_land(UNFIT, unfit)` → line 595 prints `"-> {UNFIT}   (every rejection kept...)"` regardless.
- `hostcheck.py:598` `_land(OUT, results)` (in `sweep()`) → line 599 prints `"-> {OUT}"` regardless.
- `hostcheck.py:708` `_land(fp, r, ...)` (in `purge()`, per catalogue record, inside the file loop) → line 720 prints `"removed: {src} <- {mined}  {n_entries} entries..."` regardless. This is the worst instance: `r["entries"]` was already cleared to `[]` in memory (line 700) before the write is attempted; if the rename is denied, the on-disk record keeps its full un-purged roster, but the run reports the purge as done and later writes that false claim into `ROSTER_PURGES.json` via the next call site.
- `hostcheck.py:731` `_land(PURGED, prev)` → line 732 prints `"-> {PURGED}"` regardless.
- `hostcheck.py:839` `_land(ROSTERS, {...})` → line 840 prints `"-> {ROSTERS}"` regardless.
- `hostcheck.py:906` `_land(F.HOSTS, hosts)` (in `adopt()`) → line 907 prints `"-> " + F.HOSTS` regardless.

**Concrete failure scenario:** any of the documented long-running readers of `WIKI_HOSTS.json`
(feats, read, completeness, ingest_doc, wiki_source — named explicitly in this file's own
docstring, lines 73-74) holds the file open across a `--repair` or `--adopt` run. `os.replace`
is denied 5 times, `replace_retry` returns `False` and records a `note()`, and `sweep()`/`adopt()`
still print "WIKI_HOSTS.json updated" / exit 0 with no indication anything was refused. The next
run reads the stale host map, silently repeats the same "repair," and nothing in the printed
output or exit code ever surfaces the denial — a finding that should have been a JANITOR-level
`silence.note()` visible in `health.py --failures` is instead invisible unless someone greps that
ledger by hand, and the operator-facing output actively asserts success.

This is the discarded-return-value bug named in the audit brief, confirmed at all seven sites.

### 2. `onomast.py:268-334` — the genre/feature-weighted register system is entirely dead code; names are still assigned by pure hash, exactly the bug the docstring claims was fixed

`register_for()` (onomast.py:311-334):
```python
def register_for(group_id, genre_register=None, features=None):
    """The naming register: what the source gives, bent by what the world is.

    Falls back to a hash of the group id ONLY when neither a genre nor features are known. That
    fallback used to be the whole function, and it produced the register that gave Alien and Doom
    the flowing elvish sound and denied Greek myth the classical one.
    """
    if not genre_register and not features:
        return REGISTER_ORDER[int(hashlib.sha256(str(group_id).encode()).hexdigest(), 16)
                              % len(REGISTER_ORDER)]
    votes = {}
    if genre_register in REGISTERS:
        votes[genre_register] = GENRE_WEIGHT
    for axis, value in (features or {}).items():
        ...
```
The docstring claims the pure-hash path is now only a fallback, reached only when neither a
genre nor features are known, and that the real path (lines 322-334, backed by
`FEATURE_SHIFT`/`GENRE_WEIGHT`/`FEATURE_WEIGHT`, lines 268-308) is what runs normally.

Traced every caller in `src/`:
- **`onomast.py:356`**, inside `name_worlds()` — the *only* place `register_for` is called from
  within this module: `reg = register_for(v["continuity_group"])`. Positional-only, one
  argument. `genre_register` and `features` are never supplied. `v` (the per-entity dict from
  `resolved`) is only read for `canonical_name`, `key`, `continuity_group`, and `attestations`
  (lines 347, 356-364) — no `genre` or `features` field is ever read off it, so there is not even
  unused data on hand to pass through.
- **`pipeline.py:1888-1895`** — the only external caller of anything in this module for this
  purpose: `import onomast as O; named = O.name_worlds(resolved)`. It calls `name_worlds`
  directly, not `register_for`, and `name_worlds`'s own signature (`def name_worlds(resolved):`,
  line 337) has no parameter through which a genre or feature map could even be threaded in from
  outside.
- **`navtree.py:157-192`** defines its own *local* `register_for(key)` (single positional arg,
  hash-based tie-break per its own comment at line 178) — a same-named but unrelated function
  that shadows nothing and does not call `onomast.register_for` either.
- Grepped `genre_register` and `onomast` across all of `src/`: no other call site exists anywhere.

So `if not genre_register and not features:` is true on **every single invocation that occurs in
the running system**, and the hash fallback at line 319-320 is not a fallback — it is the whole
function, unconditionally, in production. The 60+ lines of `FEATURE_SHIFT` (269-300),
`GENRE_WEIGHT`/`FEATURE_WEIGHT` (301-308), and the voting logic in `register_for` (322-334) are
unreachable from any real call graph. The docstring's claim — that this fixed "Alien and Doom
[getting] the flowing elvish sound and [Greek myth being] denied the classical one" — is false as
currently wired: every world still gets its register from `hashlib.sha256(continuity_group)`,
the identical defect the docstring says is now only a corner case.

Corroborating cross-reference (not part of this batch, `genre.py` is out of scope, mentioned only
for context): `genre.py`'s own module docstring (lines 12-31) independently claims to have fixed
this same problem ("the register... was being assigned by hashing the continuity group id... A
genre classifier can [fix it]... register -> culture set and naming (onomast.py, worldseed.py)")
but `genre.py` is imported nowhere except `verify_math.py` (a test/checker), never by
`onomast.py`, `pipeline.py`, or `worldseed.py`. Two separate docstrings assert the same fix
happened; neither wiring exists. This is VERIFIED, not suspected — traced every call site.

---

## MAJOR

### 3. `grounding.py:112-117` and `169-179` — confidence is computed only over the top-3 grounding scores, inflating it; this is a cap deciding an answer

```python
def classify_text(text, top=3):
    scores = collections.Counter()
    for name, spec in GROUNDINGS.items():
        for pat, wt in spec["cues"].items():
            scores[name] += wt * len(re.findall(pat, text, re.I))
    return scores.most_common(top)          # line 117 — truncates to the top 3 of 5 types
```
`GROUNDINGS` has 5 keys (`ex_nihilo`, `emanation`, `eternal_cycle`, `demiurgic`, `immanent`); a
sixth outcome, `UNGROUNDED`, is handled separately and isn't in this dict. `classify_text`'s
default `top=3` means whenever a source's text scores nonzero on 4 or 5 of the 5 real types
(plausible — cue regexes overlap: e.g. "world-tree" fires under both `demiurgic` and, via
different cues, could contribute elsewhere), the bottom 1-2 scores are silently dropped from the
returned list before `classify_source` ever sees them.

```python
ranked = classify_text(" ".join(parts))          # line 162, already truncated to <=3 rows
...
top, score = ranked[0]                            # line 169
total = sum(s for _, s in ranked) or 1            # line 170 — sums only the surviving <=3 rows
...
"confidence": round(score / total, 3),            # line 179
```
`confidence` is defined as the winning type's share of scored evidence — but the denominator
(`total`) is the sum of only the top 3 candidates' scores, not all 5. Any score mass on the 4th-
and 5th-ranked types (evidence for competing cosmogony readings) never enters `total`, so
`confidence` is systematically inflated whenever more than 3 types score. Worked example: scores
`{ex_nihilo: 10, emanation: 8, eternal_cycle: 6, demiurgic: 5, immanent: 5}` — true confidence
over all 5 is `10/34 = 0.294`; what the code reports is `10/24 = 0.417` (top-3 only), a swing of
12 points. `runners_up` (line 185, `ranked[1:]`) is likewise built from the pre-truncated list, so
even the "contested cosmogonies" diagnostic in `main()` (lines 228-233, filters
`confidence < 0.5`) can miss a genuinely 4- or 5-way-contested source because the truncation
already inflated its reported confidence above the flagging threshold.

This is not display formatting — `confidence` is a stored field in `GROUNDINGS.json`
(`grounding.py:239`, `silence.write_json(p, out, ...)`), consumed downstream by whatever reads
that file to judge how well-attested a grounding classification is (the "contested cosmogonies"
gate in this file's own `main()` is the clearest consumer traced). Downstream shelving itself
(`tiers.py`'s `hyperverse_of`/`xenoverse_grounding`) only reads the winning `grounding` string, not
`confidence`, so the blast radius is the confidence/contested-flagging signal specifically, not
the type assignment itself. Sibling function `genre.classify_source` (not in this batch) has an
analogous `cap`/`floor` history documented in this very docstring (lines 128-141) describing an
almost identical truncation bug that was fixed there by refusing a numeric `cap` outright — that
fix was applied to the origin-*entries* cap, not to `classify_text`'s `top=3`, which the docstring
never mentions or defends.

### 4. `ledger.py:116-136` (`assay_to_standards`) resolves the missing top-of-ladder edge case in a way that silently disagrees with `assay.axis_score()`, and ignores its own `ruin_score` parameter for every M10 entity

`assay.py:211-229` (`axis_score`) handles "no band above this one exists" explicitly:
```python
i = LADDER.index(band)
if i + 1 >= len(LADDER):
    return 9.9                      # assay.py:222-223 — explicit, documented special case
```
At the top of the 11-rung ladder (`LADDER[-1] == "M10"`, assay.py:105), `axis_score` cannot form
an `(lo, hi)` interval to interpolate within, so it deliberately short-circuits and returns a
fixed near-ceiling score, 9.9, for any input — i.e. it treats "M10, can't measure further" as
"assume maximal."

`ledger.py:127-134` (`assay_to_standards`) has no such guard:
```python
from assay import BAND_EDGES, LADDER
if magnitude_band not in BAND_EDGES:
    return None
i = LADDER.index(magnitude_band)
lo = BAND_EDGES[magnitude_band]["ruin"]
hi = BAND_EDGES[LADDER[min(i + 1, len(LADDER) - 1)]]["ruin"]
joules = math.exp(math.log(lo) + (ruin_score / 10.0) * (math.log(hi) - math.log(lo)))
```
At `magnitude_band = "M10"`: `i = 10` (last index of an 11-element list), so
`min(i + 1, len(LADDER) - 1) = min(11, 10) = 10 = i`, and `LADDER[10]` is `"M10"` again — the same
band as `lo`. So `hi = BAND_EDGES["M10"]["ruin"] == lo` (both `1e99` J, assay.py:86). With
`hi == lo`, `math.log(hi) - math.log(lo) == 0.0`, and the interpolation collapses to
`joules = math.exp(math.log(lo) + ruin_score/10 * 0) = lo = 1e99` **for every value of
`ruin_score` from 0 through 10, including the function's own default `ruin_score=5.0`**. The
parameter that is this function's entire reason for taking an argument beyond the band has no
effect whatsoever at the top of the ladder.

**The disagreement, precisely:** given the same "M10, near-maximal" situation, `axis_score`
resolves the missing-ceiling case by returning a value near the TOP of its 0-10 range (9.9) —
i.e. "assume this reads as almost-maximal." `assay_to_standards`, fed that same situation, instead
collapses to the FLOOR of the M10 band (`lo = 1e99` J) and stays there regardless of how high the
input `ruin_score` is — i.e. it behaves as though every M10 entity is at the *minimum* of the top
band, never scaling upward no matter what score is passed in. The two functions were clearly meant
to compose (`axis_score` produces a 0-10 score; `assay_to_standards`'s signature
`(magnitude_band, ruin_score=5.0)` is shaped to accept exactly that score as input), but they
resolve the identical "ladder has no rung above this one" case in opposite directions — one
saturates near the ceiling, the other saturates at the floor — and neither the code nor the
docstring (lines 116-126) acknowledges that M10 is even a special case. This is the "check that
cannot fail" pattern applied to a monetary computation: for the single highest tier of the entire
power ladder, `assay_to_standards` returns a constant regardless of its input, silently, with no
comment marking the degeneracy.

Concrete failure scenario: two M10 entities, one scored `ruin_score=0.5` (barely qualifies for the
top band) and one scored `ruin_score=9.9` (near the ceiling `axis_score` itself would report),
price identically in Standards — `1e99 J / 2.14e8 J ≈ 4.67e90 §` for both — because the interval
they're meant to be interpolated across has zero width. Any Ledger-derived price comparison,
market listing, or Position-Paragraph "what it would fetch at the Freeport" text for the
omniverse's most powerful tier of entities is uninformative by construction.

---

## NOTES (confirmed correct / non-bugs, worth recording)

- **`generate.py:341-354`** — the prose gate is consulted correctly. `main()` calls
  `prose_gate.assert_gate_open(cfg)` (line 349) *before* the manifest is even loaded (line 356),
  so there is no code path through this file that reaches a model call without passing the gate.
  Traced `prose_gate.gate_open()` (prose_gate.py:68-87): unreadable config → `except Exception`
  returns `(False, ...)`; non-dict parse → refused; `cfg.get("prose_enabled", False) is not True`
  is a **strict identity check**, so a missing key, `False`, `1`, or the string `"false"` (the
  exact truthy-but-wrong value named in the brief) all fail closed. Re-reads `config.yaml` fresh
  on every call rather than caching a stale `True`. This gate is sound; no changes proposed or
  made, per the standing instruction not to touch it.
- **`hostcheck.py`** overall shows a project-wide repair history (candidates(), roster/purge,
  null_rate baseline) that is now internally consistent with Hard Rule 0 — no remaining
  authoritative-roster truncation was found in this file outside the discarded-return-value bug
  above. `probe()`'s RAW-mode fetch (`names[:12]`, line 136) and `relevance()`'s `sample=12`
  (line 200) and token-selection `[:3]` (line 219) are statistical-sample sizing for a hit-rate
  *measurement*, consistent with the file's own documented `PROBE=40` sampling methodology, not
  truncation of an authoritative listing — flagged for awareness, not scored as a defect.
- **`backfill.py:250-251`** (`--cap`) and **`generate.py:335,421-422`** (`--limit`) both default to
  `None` (uncapped) and require an explicit operator flag to truncate; not silent defaults.
  `backfill.py:228` correctly checks `P.write_record_catalogue(path, r)`'s return value and
  reports `write_denied: True` rather than claiming success on a denied write — this is the
  *correct* two-writer-contract pattern, in direct contrast to finding #1 in this same batch.
- **`profile.py:127`** (`build_all(limit=None)`) — default unlimited; the one call site with a
  cap (`verify_math.py:811`, `limit=400`) is explicitly labelled "A SAMPLE, and labelled as one"
  for a round-trip test, not a production truncation.

---

## Coverage

`sweep_plan.record('run32', ['hostcheck.py','generate.py','onomast.py','backfill.py',
'grounding.py','profile.py','ledger.py'], batch=11)` was run from the repo root after this
report was written; see final message for confirmation of success.
