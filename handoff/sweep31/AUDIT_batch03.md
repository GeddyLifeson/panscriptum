# SWEEP 31 — BATCH 03 AUDIT

Modules: `src/standards.py` (1510 lines), `src/reference.py` (358 lines),
`src/context_budget.py` (278 lines), `src/burgs.py` (235 lines), `src/halo.py` (178 lines),
`src/cosmology_graph.py` (159 lines).

Total lines read: **2,718** (every line of all six files, confirmed against `wc -l`).

Read-only audit. No files edited except this report. No scripts run beyond read-only greps.

---

## FINDING 1 — VERIFIED, HIGH severity, HIGH confidence
**`src/standards.py:826-828`** — "hand-built assays match the charter" standard is vacuously
TRUE (green) when `data/REFERENCE_ASSAYS.json` parses as an empty dict `{}`.

```python
out.append(_s(
    "hand-built assays match the charter", inside >= len(refs) if refs else True,
    f"{inside}/{len(refs)}", "all of them", ...
```
Python's conditional-expression precedence makes this `(inside >= len(refs)) if refs else True`
— i.e. when `refs` is falsy (`{}`), the whole boolean collapses to the literal `True`,
independent of `inside`. Failure scenario: `REFERENCE_ASSAYS.json` is written empty (truncated,
cleared, or written before first population) → this HIGH standard, whose own surrounding comment
says "If its arithmetic drifts, everything shelved under it is wrong in a way no amount of
correct mining can rescue," reports `0/0 — all of them` and holds green, exactly the
"validator satisfied by trivially-empty input" this project already fixed for the sibling
COMPLETENESS.json standard nearby (see its own "NO DENOMINATOR IS NOT ZERO COVERAGE" comment at
~line 944) — but missed here. Note this can only fire when the file is present, valid JSON, and
literally `{}`; if the file is absent/corrupt the surrounding `except Exception` swallows it into
Finding 5 instead (row disappears rather than reads falsely green).

## FINDING 2 — VERIFIED, MAJOR severity, HIGH confidence
**`src/burgs.py:225-230`** — two-writer contract violation: `BURGS_SAMPLE.json` is written with
a raw, non-atomic `open(p, "w")` + `json.dump`, not `silence.write_json`/`silence.replace_retry`.
```python
p = os.path.join(HERE, "data", "BURGS_SAMPLE.json")
with open(p, "w", encoding="utf-8") as f:
    json.dump(per_world, f, indent=2, ensure_ascii=False)
```
Every sibling data-writer read in this batch (`reference.py:333`, `halo.py:171`,
`cosmology_graph.py:147`) uses `silence.write_json`, and `cosmology_graph.py`'s own comment at
that call site explains exactly why atomicity matters ("a truncate-then-fill here hands them an
empty graph they would silently trust"). `burgs.py` is the outlier in this batch. No current
downstream reader of `BURGS_SAMPLE.json` was found (grepped `src/`), so no live race today —
but a reader started concurrently with `--write`, or a second `--write` invocation racing the
first, would be exposed to a truncated/partial file. Verified by direct source read; no
downstream consumer found, which is why severity is "major" rather than "blocking."

## FINDING 3 — VERIFIED, MINOR/MEDIUM severity, HIGH confidence
**`src/burgs.py:148`** — settlement-population floor is decoupled from the module's own declared
constant. `HAMLET_FLOOR = 40` (line 85, documented as "The smallest thing the record still calls
a burg. Below this it is a farmstead and the catalogue has nothing to say about it") is used to
derive the settlement *count* `n` in `burg_count()` (line 106), but the actual per-rank
population floor in `burgs_for()` is a separate, hardcoded `30`:
```python
pop = max(30, int(p1 / (k ** ZIPF_Q)))
```
Under normal conditions this clamp is dead code (n is derived so that P_n ≈ HAMLET_FLOOR ≥ 30).
But `burg_count()`'s condition factor for `"thriving"` worlds is `1.15` (line 108), applied
*after* the HAMLET_FLOOR-based count is computed — inflating `n` beyond the natural
floor-derived cutoff. For a thriving world this pushes the tail rank's population below the
documented 40-floor, down toward the unrelated 30 constant, so thriving-world burg rolls can
contain settlements the module's own docstring says shouldn't be catalogued as burgs at all. The
30 should either be `HAMLET_FLOOR` or removed once `n` is guaranteed ≥ the floor; as written the
two constants can silently diverge.

## FINDING 4 — VERIFIED, MODERATE severity (comment contradicts code, Lens 6), HIGH confidence
**`src/burgs.py:230`** — the printed message after `--write` is stale/wrong:
```python
print(f"\nwrote {p} (sample of 50 worlds; the rest regenerate on demand)")
```
but the data actually written (`per_world`, built at lines 197-201) comes from iterating over
`worlds = WS.build_all()` with **no** `limit` argument. `worldseed.build_all(limit=None)` (its
own signature, confirmed by reading `src/worldseed.py:244`) with no limit passed returns every
world — the module's own docstring cites "1,521" worlds. So the file written is the **full**
Hard-Rule-0-compliant roster, but the console message tells the operator it's a 50-world sample
— exactly backwards, and liable to make a reader distrust or discount a complete file, or trust
a stale claim about size.

## FINDING 5 — VERIFIED PATTERN, HIGH severity, HIGH confidence
**`src/standards.py` — recurring "a standard that does not emit" defect**, in ~15 more places
than the three the file's own history documents as fixed. The file's docstring and inline
comments explicitly identify this exact failure mode as the project's most expensive repeated
mistake, and record three specific fixes: the fabrication standard (~695-758), catalogue
coverage (~944-971), and "the library's counters are moving" (~880-901, whose comment reads: "A
STANDARD THAT DOES NOT EMIT IS WORSE THAN ONE THAT FAILS: it does not appear on the page at all,
so nobody can even see that it went unmeasured"). That principle was **not** applied to the many
other `try: ... out.append(_s(...)) ... except Exception: silence.note(...)` blocks in the same
function, where the `out.append` sits *inside* the `try`, so any exception mid-block — a missing
file after the phase that creates it has run once then stopped, a JSON parse error, a transient
subprocess/network failure — makes the whole standard's row silently vanish from `check()`'s
output rather than reporting "UNMEASURED", exactly the shape already shown to be dangerous.
Representative instances (file:line, standard name): sweep-freshness (981-999), roster-audit
(760-784), shelfmarks (786-799), reference-assays (806-834, compounds with Finding 1),
charter-regression (843-861), job-advance (1006-1076), unrecognised-pool (1090-1135),
fandom-reachable (1148-1164), disk (1166-1174), ollama-runner-standard (1202-1231),
token-flow-standard (1236-1250), jobs-alive (1252-1278), duplicates (1284-1313, explicit
`_dup = None` then conditional append), publish-age (1315-1325), provider-models (1328-1407),
self-check (1415-1436). Not claiming each is currently firing — only that none of them has the
guard the file's own lesson calls for, and the file demonstrates it already knows how to add it
(see the "always emits" fix on the counters-moving standard).

## FINDING 6 — VERIFIED, MEDIUM severity, MEDIUM-HIGH confidence
**`src/standards.py:669-693`** — "cached records that were fully read" standard can silently
under-report on partial failure. `unans_files = 0` is initialized *before* the try block, and
`out.append(...)` happens *unconditionally after* the try/except — not inside it:
```python
unans_files = 0
try:
    ...
    for fp in _g.glob(os.path.join(HERE, "data", "readfeats", "**", "*.json"), recursive=True):
        with open(fp, encoding="utf-8") as f:
            head = f.read(700)
        if ...: unans_files += 1
        elif ...: unans_files += 1
    _UNANS_CACHE.update({"at": now_m, "n": unans_files})
except Exception:
    silence.note("standards.py:unanswered-records")
out.append(_s("cached records that were fully read", unans_files <= MAX_UNANSWERED_RECORDS, ...))
```
If the glob loop raises partway through (e.g. a file locked by a concurrent writer, a
`UnicodeDecodeError` on a mid-write JSON file — plausible given `read.py` is writing these files
concurrently per the file's own commentary elsewhere about read/write races) the partial count
accumulated so far is reported as the complete measurement — a silent undercount presented as a
clean reading, not as "unmeasured." `_UNANS_CACHE` is also never updated on this path (the
`.update()` call is unreached), so the same partially-failing file can suppress the count on
every subsequent cycle too, each time re-scanning and stopping at the same point.

## FINDING 7 — HYPOTHESIS, LOW/MEDIUM severity, MEDIUM confidence
**`src/context_budget.py:152` vs `src/standards.py:206`** — inconsistent fallback default for
the same config key. `context_budget.window()` defaults `num_ctx` to `8192` when absent from
`cfg`; `standards.ollama_token_flow()`'s probe defaults the same key to `6144`. Both modules'
comments emphasize deriving everything from the live `num_ctx` rather than hardcoding it — but
they'd derive *different* windows from an identically missing key. `config.yaml` currently sets
`num_ctx` (12288 per standards.py's own comment), so this is dormant; it would only bite a
caller that passes a `cfg` dict missing the key, or if the config file's key were ever dropped.

## FINDING 8 — HYPOTHESIS, LOW severity, LOW-MEDIUM confidence
**`src/cosmology_graph.py:151`** — unexplained hard cutoff on graph output.
```python
"pairs": [... for (a, b), w in sorted(pair_w.items(), ...) if w >= 1.0], ...
```
Unlike `UBIQUITOUS_CUTOFF` a few lines above (explicitly commented: "Kept explicit rather than
purely threshold-based so the reasoning is auditable"), this `w >= 1.0` filter on the written
`SHARED_STAGE_GRAPH.json` pairs has no justifying comment. Because per-shared-entity weight for
the rarest possible case (an entity shared by exactly 2 sources, n=2) is
`1/log(3.5) ≈ 0.80` — below 1.0 — two sources that share exactly *one* maximally rare,
maximally diagnostic entity are excluded from the graph entirely; a pair needs at least two
distinct shared entities to clear the bar. This may be a deliberate noise-reduction / corroboration
requirement rather than a Hard-Rule-0 violation, but as written it silently drops the single
strongest evidentiary case the module's own IDF reasoning identifies as most diagnostic, with no
comment explaining the tradeoff the way its sibling threshold does. Flagged for owner judgment,
not asserted as a confirmed violation.

## FINDING 9 — HYPOTHESIS, LOW severity, LOW confidence
**`src/reference.py:232-246`** (`shelfmark()`) — the mapping from `tier_key`'s dot-split parts
and `lower_rungs` onto the fixed 7-tuple `RUNGS` assumes exactly 3 upper parts + 4 lower parts
(`RUNGS[3 + i]` offset is hardcoded). True for all three current `REFERENCE` entries (verified:
`"1.6.1"`, `"4.2.0"`, `"1.2.5"`, all 3-part; all `lower_rungs` 4-element) but unguarded — a
future reference entity with a `tier_key` of different depth would silently misalign rung labels
(or raise `IndexError` if `len(parts) > 7`). Not currently exercised; not a live bug.

---

## Not flagged after investigation
- `src/burgs.py`'s `limit=` kwarg on `burgs_for()` was checked against Hard Rule 0. It is used
  only for display slicing (`main()`'s `[:args.limit]` on already-fully-built data) and by
  `verify_math.py`'s regression tests for speed — both already adjudicated as compliant test-economy
  use in prior sweeps (sweep24-sweep30 `AUDIT_batch01.md`/`AUDIT_batch04.md` reference this same
  code). No production roster is truncated by it in this batch.
- `src/halo.py` — no caps, no bare excepts, atomic write via `silence.write_json`, hardcoded
  three-entity roster with no dynamic truncation. Clean.
- No bare `except:` (class-less) found in any of the six files (`grep -n "^\s*except:\s*$"`
  returned nothing).
