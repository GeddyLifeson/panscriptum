# Sweep 40 — Batch 12 audit

Modules: `src/workorders.py` (1,428 lines), `src/health.py` (931 lines), `src/custodes.py`
(684 lines), `src/ingest_doc.py` (543 lines), `src/sevenfold.py` (422 lines), `src/genre.py`
(338 lines), `src/runguard.py` (304 lines), `src/cosmology_graph.py` (245 lines). All eight
read in full, sequentially (workorders.py in two windows: 1-963, 964-1428). No sampling.

## Context

All eight modules are, individually, among the most heavily self-audited files in this tree.
Every one of them carries the project's now-standard defensive apparatus (compare-and-swap
read-modify-write over shared JSON state, `landed`-gated writes with the verdict checked and
reported rather than discarded, Hard-Rule-0 uncapped evidence with labelled `first N`/`... more`
console framing, fail-closed handling of unreadable/absent artifacts) and long comments that
name and pin specific historical defects by order id. Given that density, this pass assumed the
arithmetic and CAS logic in each module is correct as documented (it is; verified by reading,
not re-derived independently) and spent the time instead on the categories most likely to still
hide something in files this self-correcting: discarded return values, fail-open branches,
tautological guards, and — per the audit brief's own example category — stale `file.py:NNN`
cross-references inside comments, which were located by grep and checked one at a time against
the current source of every file they cite.

That last category is where this batch's findings are. No functional defect (wrong CAS, silent
truncation of stored/acted-on data, fail-open gate, discarded write verdict, do-nothing success
exit) was found in any of the eight modules. Two of the six criteria the brief lists produced no
hits at all in this batch: no tautological/unreachable check, no fail-open contradicting a
fail-closed docstring, no Hard Rule 0 violation on stored or acted-upon output (every `[:N]`
slice found by grep is either a labelled console/demo truncation with the uncapped data present
elsewhere, or an already-fixed and now-historical reference to a removed cap), no unguarded
read-modify-write, and no success-coded no-op run. Two modules (`custodes.py`, `sevenfold.py`)
each contain one `m30`-style comment explicitly labelling a guarantee-not-a-check
(`covers_every_reading`, the `children per parent` "OK"/"OVER SPAN" column) — these are already
self-documented as intentional, non-hidden, and not treated as new findings per audit rule 2.

## Findings

### 1. Stale cross-file line citation — `src/genre.py:316` cites `profile.py:129-138` (INFO)

**Where:** `src/genre.py:314-318`, the comment above the `--write` gate in `main()`:

```python
p = os.path.join(HERE, "data", "GENRES.json")
# ATOMIC. `GENRES.json` is read by `navtree.py` and `profile.py`; a truncate-then-fill
# leaves it empty for the length of the write, and `profile.py:129-138` turns a failed
# load into a silent `{}` fallback that produces a fully-populated, blanket-default
# catalogue indistinguishable downstream from real data. The m100 tail, 2026-08-25.
```

**Verified against the cited lines.** `src/profile.py:129-138` is the body of `galaxy_api()`,
an unrelated function that builds a URL for the external galaxy-generator service — it contains
no read of `GENRES.json`, no `try`/`except`, and no `{}` fallback:

```python
129: def galaxy_api(address, base="https://galaxy-generator.oogabooga.dev/api/galaxy"):
130:     """The star system, from a hierarchical galaxy service.
...
136:     """
137:     f = AS.unpack(address)
138:     return f"{base}?seed={f['galaxy']}", f"{base}/{f['galaxy']}/neighbourhood?seed={f['star']}"
```

The actual read-and-silently-fall-back-to-`{}` behaviour the comment describes lives at
`src/profile.py:142-147`, inside `build_all()`:

```python
142:     try:
143:         genres = json.load(open(os.path.join(HERE, "data", "GENRES.json"), encoding="utf-8"))
144:     except Exception:
145:         silence.note("profile.py:genres-unreadable")
146:         genres = {}
```

**Why it's wrong:** it is the exact shape the audit brief calls out — the comment cites a line
range that does not say what it claims, sending a future reader (or another agent trying to
verify the ATOMIC/GATED reasoning before touching this write) to the wrong function entirely.
`profile.py` has clearly been edited since this comment was written and the citation was never
re-pointed. The claim itself (that an unreadable `GENRES.json` silently becomes `{}` in
`profile.py`, which then produces a blanket-default catalogue) is *true* — it's the location
that's wrong, not the fact.

**Remedy:** change `profile.py:129-138` to `profile.py:142-147` in the comment at
`src/genre.py:316`.

**Filed:** `STALE_LINE_CITATION` at `genre.py:316->profile.py`, handler LOCAL, severity INFO.

---

### 2. Three stale cross-file line citations in one module — `src/cosmology_graph.py` (INFO)

**Where:** the module docstring and a comment inside `build_graph()` cite three call sites for
the `shared_sample` key this module writes to `data/SHARED_STAGE_GRAPH.json`, and all three
citations are wrong:

```
65: the file recorded `"threshold": 3.0`, a number that had selected nothing. `resonance.py:157`
115:  # WHOLE list, no cap -- Hard Rule 0, ruled 2026-08-24. `weave.py:478` and
116:  # `pipeline.py:1795` write this same `shared_sample` key and were both brought in
119:  # `resonance.py:146` reads `shared_sample` back as the pair's actual shared
```

**Verified against the cited lines.**

* `resonance.py:146` and `resonance.py:157` fall inside `hodge_decompose()`'s sweep loop (an
  isolated-node check unrelated to `SHARED_STAGE_GRAPH.json` or `shared_sample`):

  ```python
  148:    nbrs = collections.defaultdict(list)
  ...
  156:    _isolated = [n for n in nodes if not nbrs[n]]
  157:    if _isolated:
  ```

  The actual read of `SHARED_STAGE_GRAPH.json` and of the `shared_sample` key is in a different
  function, `resonance.py:290-295` (`related()`):

  ```python
  290:    path = graph_path or os.path.join(HERE, "data/SHARED_STAGE_GRAPH.json")
  291:    with open(path, encoding="utf-8") as f:
  292:        g = json.load(f)
  293:    for p in g["pairs"]:
  294:        if {p["a"], p["b"]} == {a, b}:
  295:            return {"weight": p["weight"], "shared": p.get("shared_sample", []),
  ```

* `weave.py:478` is inside `main()`'s continuity-group printing loop (`groups = components(...)`,
  `for g in multi[:12]: ...`) — no `shared_sample` write there. The actual write is at
  `weave.py:519`:

  ```python
  519:                            "shared_sample": shared[(a, b)]}   # WHOLE list (key name kept: resonance.py reads it) -- Hard Rule 0, ruled 2026-08-24
  ```

* `pipeline.py:1795` is inside the handoff-markdown write path (`_land`/`replace_retry` for
  `HANDOFF.md`) — unrelated to `shared_sample`. The actual write is at `pipeline.py:2375`:

  ```python
  2375:                          "shared_sample": shared[(a, b)]}   # WHOLE list -- Hard Rule 0, ruled 2026-08-24
  ```

**Why it's wrong:** same shape as finding 1 — all three of these files have visibly been edited
(comments and code added) since the citations were written, and none was re-pointed. This is
the more consequential of the two findings because it sits in the reasoning trail for the
`pairs_filtered`/uncapped-`shared_sample` fix (order 9861c18b8485) that this module's own
docstring documents at length — a reader trying to confirm "resonance.py really does read this
key back, and here's where" is sent to an unrelated loop in a different function twice over.

**Remedy:** update the three citations to `resonance.py:290-295`, `weave.py:519`, and
`pipeline.py:2375` respectively.

**Filed:** `STALE_LINE_CITATION` at `cosmology_graph.py:65,115-119->resonance.py/weave.py/pipeline.py`,
handler LOCAL, severity INFO.

## Coverage

`sweep_plan.record('run40', [workorders.py, health.py, custodes.py, ingest_doc.py,
sevenfold.py, genre.py, runguard.py, cosmology_graph.py], batch=12)` recorded.
