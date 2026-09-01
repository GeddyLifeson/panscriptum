# Sweep 40, batch 03 — audit

Modules read in full: `src/pipeline.py` (2648 lines), `src/onomast.py` (581), `src/reference.py`
(480), `src/backfill.py` (387), `src/cleanup.py` (311), `src/tempus.py` (274), `src/ledger.py`
(172), `src/module_index.py` (116). Every line of every file was read; no sampling.

General note: this is a genuinely mature codebase. The overwhelming majority of what a first pass
flags as suspicious turns out, on reading the surrounding comment, to be a bug that was already
found and fixed, with an `order <hex>` tag and a reproduction. Everything below survived a check
against that standard: each is either not yet mentioned anywhere in the file, or contradicts a
fix the file itself already made elsewhere.

---

## Finding 1 — stale `file.py:NNN` cross-reference in cleanup.py's escape-corruption guard

**File:** `src/cleanup.py`, lines 130–136
**Severity:** MINOR
**Handler:** LOCAL

```python
125  # GUARD. Three regexes in this project have been silently broken by an escape being eaten in
...
130  # THE ROSTER USED TO CARRY `("_SETTING_META", None)`, which `_p is not None` always skipped --
131  # `_SETTING_META` is not a name in this file at all, it lives at `pipeline.py:1204` (imported
132  # above as `PL`) and is exactly the `\b`-fenced shape this guard exists to catch. And `_MARKUP`
...
135  for _n, _p in (("_NAV", _NAV), ("_EMPTY_MECHANIC", _EMPTY_MECHANIC),
136                 ("_SETTING_META", PL._SETTING_META),
```

The comment cites `pipeline.py:1204` as where `_SETTING_META` is defined. It is not. Line 1204 of
`src/pipeline.py` is inside the `ENTRY_SYSTEM` prompt string (the `topic` field documentation:
`* \`topic\` - which encyclopedia series...`). The actual definition is:

```
src/pipeline.py:1366:_SETTING_META = re.compile(r"\b(campaign|adventure path|session|the table|module|sourcebook"
src/pipeline.py:1367:                           r"|players?|DMs?|game master)\b", re.I)
```

Confirmed by direct grep — `_SETTING_META` appears at pipeline.py:1366 (definition) and :1406
(one use site), nowhere near :1204.

This does not affect runtime behaviour: the guard loop reads `PL._SETTING_META` as a live
attribute, not by line number, so the check itself still works correctly. The defect is purely in
the comment, which is exactly the class of finding the sweep brief asks for ("a stale `file.py:NNN`
cross-reference in a comment"), and `reference.py:shelfmark`'s own docstring (lines 241-244) shows
this project already treats a wrong line number in a comment as a real defect worth an entry:
*"this was tagged 'reference.py:232', which is `def shelfmark(rec):` itself... A stale number
costs a grep every time someone diagnoses it."* This is the same defect, unfixed, in a different
file.

**Remedy:** update the comment to cite `pipeline.py:1366` (or drop the specific line number and
just say "see `pipeline.py`'s own `_SETTING_META`" so it can't go stale again the next time
pipeline.py grows a paragraph above it).

---

## Finding 2 — `phase_write` can mark phase 8 done after building nothing, with no diagnostic

**File:** `src/pipeline.py`, `phase_write`, lines 2286–2332 (the closing gate at 2313–2331)
**Severity:** MAJOR
**Handler:** LOCAL

```python
2286    names = sorted({s for _, s in ready if s})
...
2292    jobs, refused = [], []
2293    for src in names:
2294        try:
2295            rec = MB.load_record(cfg, src)
2296            spine = MB.spine_code_for(src) or MB.provisional_spine(src)
2297            jobs += MB.build_jobs_for_source(cfg, roll.get(src) or {"source": src},
2298                                             rec, spine) or []
2299        except Exception as e:
2300            silence.note("pipeline.py:phase_write-jobs")
2301            refused.append("%s (%s)" % (src, type(e).__name__))
...
2313    landed = []
2314    if jobs:
2315        ...
2317        landed.append(land_json(out, jobs))
2318        log("  -> output/index/manifest.json   (run generate.py against it)")
2319    elif refused:
2320        # VACUOUS TRUTH, AND THE TWO HISTORIES IT CONFLATES. ...
2329        log("  every ready source refused to build; phase 8 stays open rather than "
2330              "recording an empty manifest as a finished one")
2331        landed.append(False)
2332    ok = gate_done(st, "write", landed)
```

The comment at 2320-2328 already identifies and closes the exact "vacuous truth" hazard for one
case — every ready source raising inside `build_jobs_for_source` — by appending an explicit
`False` so `gate_done`'s `all(landed)` cannot vacuously succeed on an empty list. But there is a
third disposition the `if/elif` does not cover: a source that raises **no exception** and also
contributes **no jobs**.

Look at `MB.build_jobs_for_source` (`src/manifest_builder.py:251-256`):

```python
251 def build_jobs_for_source(cfg, roll_entry, record, spine):
252     jobs = []
253     source_name = roll_entry["name"]
254     entries = record.get("entries", [])
255     if not entries:
256         return jobs
```

It returns `[]` — cleanly, no exception — whenever `record.get("entries", [])` is empty, and
otherwise it *always* appends at least a frontmatter job unconditionally (line 282 in that file),
so this is the only path that yields an empty result. `phase_write` selects `names` from
`ready`, which is built at lines 2271-2275 from `data/COVERAGE.json`:

```python
2271    ready, thin = [], []
2272    for r in rows:
2273        n = max(r.get("entries", 0), 1)
2274        settled = (r.get("cited", 0) + r.get("read", 0)) / n
2275        (ready if settled >= WRITE_SETTLED_MIN else thin).append((settled, r.get("source")))
```

`ready` membership is decided from a `COVERAGE.json` snapshot, not from `MB.load_record`'s
current view of `data/records/*.json` — the same class of stale-artifact-vs-live-data gap this
file spends several other phases (5, 6, 7) explicitly guarding against ("ABSENT AND CORRUPT ARE
DIFFERENT ANSWERS", repeated at three other phases). If a source's coverage row is stale relative
to its record (e.g. a re-catalogue pass or `cleanup.py --apply` emptied or reduced its entry list
after `COVERAGE.json` was last computed, or the row's `cited`/`read` counts do not correspond to
`entries: 0`), that source can be `ready` yet `build_jobs_for_source` returns `[]` for it with no
exception.

If **every** source in `names` hits this — plausible on a run where `COVERAGE.json` is stale and
several thin/emptied sources cluster together — then both `jobs` and `refused` stay empty,
`landed` is never appended to, and `gate_done(st, "write", [])` sees `all([]) == True` and marks
phase 8 **permanently done**: no `manifest.json` is written, no log line explains why, and (per
the comment's own words about the sibling case) "no later run redoes it."

This is exactly the failure category Hard Rule -1 names as the one to guard against project-wide
("a check that cannot fail looks exactly like a check that passed") and that this exact function
had already partially fixed one instance of. The one case it left open is the one where nothing
raised at all.

**Remedy:** track dispositions explicitly instead of inferring them from which of two lists ended
up non-empty, e.g.:

```python
built = set()
for src in names:
    try:
        ...
        got = MB.build_jobs_for_source(...) or []
        jobs += got
        if got:
            built.add(src)
    except Exception as e:
        refused.append(...)
if jobs:
    ...
elif refused or len(built) < len(names):
    # covers "every source refused" AND "every/some source built nothing, quietly"
    landed.append(False)
```
or more simply: after the loop, if `not jobs`, append `False` to `landed` unconditionally (the
`elif refused:` branch already logs the more specific "refused" case first; a bare `else:` after
it would catch the silent-empty case too) — the point is that `landed` must never come out of
this block still `[]` when `names` was non-empty.

---

## Finding 3 — cleanup.py's own report truncates 5 of 6 lists with no "and N more", unlike its neighbour three lines down and this project's own established fix for the identical shape

**File:** `src/cleanup.py`, `main()`, lines 268–299
**Severity:** MINOR
**Handler:** LOCAL

```python
268    print("=" * 96)
269    print("CLEANUP — presentation defects from the backscan")
270    print("=" * 96)
271    print(f"\n1. wiki navigation removed from the catalogue : {len(nav):,}")
272    for s, n in nav[:5]:
273        print(f"     {s[:26]:<28}{n}")
274    print(f"\n2. ceiling entities reduced to a name        : {len(ceil_fixed):,}")
275    for s, before, after, how in ceil_fixed[:6]:
...
278    print(f"   still unresolved (left alone, not guessed) : {len(ceil_unres):,}")
279    for s, ce in ceil_unres[:4]:
...
281    print(f"\n3. descriptions with markup stripped         : {len(desc_fixed):,}")
282    for s, n, b, a in desc_fixed[:5]:
...
285    print(f"\n4. descriptions too thin to write from       : {len(thin):,}  (marked, not deleted)")
286    for s, n, d in thin[:5]:
...
293        print(f"\nNOT WRITTEN — {len(unwritten):,} record(s) refused the write ...")
296        for s in unwritten[:12]:
297            print(f"     {s}")
298        if len(unwritten) > 12:
299            print(f"     ... and {len(unwritten) - 12:,} more")
```

Five report sections (`nav`, `ceil_fixed`, `ceil_unres`, `desc_fixed`, `thin`) each print a
silently truncated head (`[:5]`, `[:6]`, `[:4]`, `[:5]`, `[:5]`) with no "and N more" trailer —
the count printed on the header line is correct, but nothing tells a reader that the list under
it stopped short. The sixth list in the same function, `unwritten` (lines 296-299), gets the
"and N more" treatment right next to them.

This is not a hypothetical concern in this codebase — it is the *precise* defect shape three
sibling modules already found and fixed, on the record:

* `onomast.py:538-541` (order `89fc2eaf23f1`, Hard Rule 0): *"This was `[:4]` with nothing
  announcing it, four lines above an inner list that prints its own '... and N more' -- two
  disciplines in one function, and the silent one on the outer list."* — the exact same
  "count is right, but nothing marks the cut" pattern, in a report, not corpus data.
* `backfill.py:312-320` (order `03c0fe609e89`, Hard Rule 0): *"the exact shape run #33 removed
  from `pipeline.phase_write`'s `refused[:5]`... Ranking is kept... and the count moves into the
  header, where it says what is being looked at instead of what is being withheld."*
* `pipeline.py:2304-2310` (run #33): the `refused` roster in `phase_write` was uncapped for the
  identical reason.

None of `cleanup.py`'s corrections are lost on disk — every entry in `nav`/`ceil_fixed`/etc. that
triggers `changed = True` is still applied to its record and written via `write_record` regardless
of what the console prints, so this is a report-visibility gap, not a data-loss one (which is why
it is filed as MINOR and not MAJOR). But it is the one console report in the file that does not
follow the file's own established discipline, sitting a few lines above `unwritten`, which does.

**Remedy:** either uncap these five lists (the corpus is bounded — cleanup runs over the whole
catalogue in one pass, same order of magnitude as `backfill --audit`'s ~215 rows) or, at minimum,
add the same `"... and N more"` trailer `unwritten` already uses, so a reader can tell how much
was withheld from the ones actually shown.

---

## Reviewed and NOT flagged (deliberate design / already covered)

* `ledger.py`'s `assay_to_standards` M10 ceiling handling, `currency_status` reason-vs-None split,
  and `to_standards`/`from_standards` returning bare `None` — all explicitly reasoned through in
  their own docstrings with `order` tags; correct as written.
* `tempus.py`'s lack of a per-shelf tempo parameter, `band_resolution`'s M10 saturation, and
  `prescience_horizon_bits`'s positive-lead-time guard — all deliberate, argued at length, and
  verified against `assay.BAND_EDGES`/`LADDER` usage; no defect found.
* `onomast.py`'s `coin_well_formed` fallback widening, the retired/standing split (order
  `e5001f0b0153`), and `load_onomasticon`'s missing-vs-unreadable split (order `549069e9c298`) —
  all read in full; the logic matches what the docstrings claim, including the `naming`-set
  exclusion from `taken` that keeps determinism across reruns.
* `backfill.py`'s ranking-not-alphabetical roster cap removal, the `t in sizes` sort-key
  inversion history (order `d673aa4d609a`), and the pre/post-cap `absent` reporting fix — all
  checked against the surrounding code; the fixes described are actually in effect.
* `reference.py`'s dual exit-code coupling of "write landed" and "calibration inside interval"
  (order `d049dbbfed6e`) — checked; both conditions are genuinely required for `rc=0`, and the
  ASSAYS.json pairing-key fix (host+entity rather than a bare name) matches how `ASSAYS.json` rows
  are actually read elsewhere.
* `pipeline.py`'s two-writer contract (`write_record` / `write_record_catalogue`), the drift
  digest fix (order `1c2ea97cdc36`), `MERGED_ENTRY_FIELDS`/`ENTRY_REJECTION_COMPANIONS` (orders
  `4866dfb2d9fc`, `2f248e854b58`), `gate_done`/`_landed`/`land_json` gating across every phase,
  and the absent-vs-corrupt handling repeated at phases 5/6/7/8 — read in full; all internally
  consistent and match their docstrings' claims against the actual code around them.
* `module_index.py` — small, entirely self-consistent; the "no count in prose" discipline in its
  own docstring is honoured by the code (the module count is computed live via `glob`, never
  hand-written).

## Coverage

`sweep_plan.record('run40', [pipeline.py, onomast.py, reference.py, backfill.py, cleanup.py,
tempus.py, ledger.py, module_index.py], batch=3)` — recorded.
