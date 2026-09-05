# Audit batch 08 — run44

Modules read in full, top to bottom: `src/magnitude.py` (1826 lines), `src/chain.py` (838
lines), `src/secondopinion.py` (643 lines), `src/weave_index.py` (522 lines), `src/sevenfold.py`
(422 lines), `src/render.py` (337 lines), `src/resync_roll.py` (312 lines),
`src/propagation.py` (236 lines). 5,436 lines total.

**General note on this batch.** All eight modules carry an unusually high density of in-line
prose documenting *previously found and fixed* defects — order IDs, measured before/after
numbers, and explicit "this used to do X, which was wrong because Y" comments. That made this
audit slower than a typical batch (verifying that a described fix is actually present and
complete took longer than finding a fresh defect), but it also means most of the obvious fault
classes (naked truncation, swallowed exceptions, non-atomic writes) have already been through at
least one repair pass here. The findings below are what is left after checking the fixes hold
and looking past them for anything the fix comments don't mention.

---

## magnitude.py

### Finding M1 — `isinstance(x, (int, float))` admits booleans as scores (low severity, low-to-medium confidence)

Three sites gate "is this a real numeric score, or a status string" on `isinstance(raw,
(int, float))`:

- `verify()`, line 806: `if not isinstance(raw, (int, float)): scores[ax] = A.UNESTIMABLE`
- `_split_assay._one_axis`, line 975: `if isinstance(sc, (int, float)):`
- `_split_gate`, line 1131: `if isinstance(sc, (int, float)) and source is not None:`

In Python, `bool` is a subclass of `int`, so `isinstance(True, (int, float))` is `True`. If a
model ever returned JSON `{"score": true, "feat": "..."}` for an axis — a malformed but
schema-adjacent answer (the JSON Schema declares `"score": {"type": ["number", "string"]}`,
which technically excludes booleans, but Ollama's structured-output enforcement is not
guaranteed to reject a boolean the way a strict JSON Schema validator would) — the code would
treat `True`/`False` as a legitimate numeric score of `1.0`/`0.0` rather than routing it through
`_status_score()` the way every other non-numeric answer is (correctly) required to. This
bypasses the "a status is not provenance" fix at line ~787 for exactly the input shape that fix
was written to catch, for one specific value shape.

I could not find evidence this has actually happened (no boolean scores in `data/ASSAYS.json`
were checked as part of this pass — that would require running the pipeline), so I'm filing
this as a real but probably-dormant gap rather than an observed defect. The fix, if wanted,
is `isinstance(raw, (int, float)) and not isinstance(raw, bool)` at all three sites.

### Finding M2 — `children_of`-style partial-coordinate question (see render.py R1, same shape)

Not in this file, cross-referenced from render.py below because the root cause is a coordinate
dict that can be legitimately partial.

### Confirmed correct (no finding, worth recording as checked)

- `_resolve_citation`, `subject_refusal`, `quantity_scores`, `_split_gate`'s guard-3
  application, `_status_score`'s three-way sentinel mapping, `saturated()`, `candidates()`
  (uncapped by default, `cap` parameter unused by any caller in the tree — verified by grep),
  the anchor-clamp / DEFERRED-vs-M0 logic in `assay_entity`, and the split-vs-one-shot sizing
  thresholds (`LOCAL_FITS`, `ONE_SHOT_MAX`, `SPLIT_SLICE`) were all read closely against their
  docstrings' claims and found to do what they say.
- The cross-axis citation check in `assay_entity` (lines 1329–1335) is correctly skipped for
  the split path per its own comment, and correctly re-derives `flat`'s numbering from the same
  `compose()` call that produced the prompt (verified `mined` in `verify()` is built from
  `ev_v["feats"]`, which is `[flat[k][1] for k in sorted(flat)]` — same order, same numbering).

---

## chain.py

No new defects found. This module's `adjudicate_mutuals` (the epoch-based mutual-pair
adjudication, the most complex logic in the file) was checked branch-by-branch against its own
docstring's four cases (unprobed / self-split / both-dated-differently / one-dated) and matches;
the `probed_a and probed_b` gate, the `conf_a or conf_b` self-disagreement check, and the
`ea and eb and ea != eb` vs `bool(ea) != bool(eb)` split are all mutually exclusive and jointly
correct for the cases the docstring claims to handle.

`extract()`'s thread-safety fix (`local_unmatched` tallied per-worker, merged once under the
lock) and `write_result`'s/`harvest()`'s atomic-write-with-verdict-checked pattern were both
read and are sound. `entity_index()`'s partial-name clash handling (a surname shared by two
catalogued entities resolves to neither) is correct.

---

## secondopinion.py

No new defects found. The returncode-aware wrappers around `ruff`/`vulture`/`detect-secrets`
(`_ruff`, `_vulture`, `_detect_secrets`) correctly distinguish "tool ran and said nothing" from
"tool never ran," and `_vulture`'s Windows-drive-letter-safe regex (`^(?P<path>.+?):(?P<line>
\d+):\s*(?P<message>.*)$`, non-greedy path) is right — it will not misparse `C:\...\foo.py:123:`
as filename `"C"`. The `report()` function's fingerprint-before-and-after check for a tree that
changed mid-scan, and the three-way secrets comparison (`UNMEASURED` vs `AGREEMENT` vs
`DISAGREEMENT`, keyed on `mine["secrets"] is None` rather than `== 0`) are both correct.

One thing worth flagging as a **question, not a defect**: `NOT_FILED`'s test ("would fixing
every instance make the codebase worse or merely different") is applied by a human/agent
judgment call each time a new waiver is added, and nothing in the code enforces that a waiver
actually satisfies its own stated test — the file's own history (the BLE001/S110/S112 waivers
added and reverted the same day) shows this has gone wrong before. That's a process gap, not a
logic bug, and the module already documents the failure and its own correction candidly.

---

## weave_index.py

No new defects found. `designations()`'s cache-invalidation-on-failure fix (the failure path
does *not* poison `_DESIGNATIONS`, only returns an uncached empty set to the one caller) is
correct. `_records_sig`'s handling of an unstattable file mid-enumeration (finish the walk,
return a `None` signature but the full readable file list) was checked against `load_records()`'s
consumption of it and is consistent — a `None` sig suppresses the cache without truncating the
file list. `build()`'s exclusion accounting (`excluded` Counter, separate from `short_keys`/
`short_hits`) correctly keeps "not indexed at all" apart from "indexed but held out of candidate
matching," matching the printed report.

`main()`'s `TOP_N = 18` console preview and the `spread` per-source-count table are both
correctly labelled previews with the full data pointed at `WEAVE_CANDIDATES.json` — not a Hard
Rule 0 violation, since the persisted file (`--write`) is uncapped and the console output says
so.

---

## sevenfold.py

No new defects found. `seams()`'s two-part fix (window around the even-split boundary, plus
"only the weaker half of the joins may be cut") was checked arithmetically against its own
worked example and holds: `_even_cuts` produces gap indices correctly clamped to
`[0, n_members-2]`, and the median-based `ceiling`/`eligible` restriction is applied before the
window search, not after, so a strong kin-pair seam inside the window is correctly protected.
`build()`'s two-population accounting (`coords` from the resonance graph vs `by_source` from
`worldseed.build_all()` over every record) and its `UNSHELVED` reporting are consistent with
each other.

---

## render.py

### Finding R1 — `children_of`'s coordinate guard checks "any prefix key present," not "the whole prefix" (question, not a confirmed defect)

`children_of()` (lines 180–226) raises `ValueError` when `coord` shares **no** key with the
tier's prefix (the `order 3270e0172391` fix, confirmed correct for the case it was written for:
an empty or wildly mismatched `coord`). But the actual filter two lines later,

```python
if any(c.get(t) != coord.get(t) for t in prefix if t in coord):
    continue
```

only compares the prefix keys that `coord` *does* supply. So a caller asking for
`children_of("metaverse", {"hyperverse": 3}, tree)` — a `coord` that names one prefix key
(passing the guard) but not all of them (`xenoverse`, `metaverse` itself) — would not raise, and
would silently return every metaverse-tier node under hyperverse 3, from every xenoverse,
pooled together as if they were one node's children. That's the same "aggregate across an
unspecified dimension" shape the `order 3270e0172391` fix was written to close for the
zero-prefix-keys case; it just doesn't close it for the some-but-not-all-prefix-keys case.

I'm filing this as a question rather than a defect because every call site in this file and its
one known caller (`main()`, via `sample = next(iter(tree["worlds"].values()))`, and `view()`
always forwarding a full coordinate) passes a complete coordinate for the tier being queried, so
this may never be reachable in practice. But the guard's own comment ("a caller that wants a
specific node's children must say which node") reads as though it intends to enforce
completeness, and it does not fully do so. Worth a `all(t in coord for t in prefix)` instead of
`any(...)` if the intent is what the comment says.

### Confirmed correct

`containment_svg`'s child-count-vs-layout-divisor split (`n = max(1, len(children))` for
geometry, `_kids = len(children)` for the caption) is correctly kept apart, per its own
comment. The whole-name-not-`[:24]` fix in `children_of`'s return value was verified: the
function returns `v[0].split("::")[0]` unsliced, and `containment_svg` applies its own separate,
marked `[:26]` only when drawing the label — the right layer for a display cut.

---

## resync_roll.py

### The previously-filed issue (order 64ffa3ba30df) — appears fixed in the current source, not wider

The known issue names "main()'s write-denied branch (lines ~260-265) discards or mis-reports the
verdict." In the version read for this audit, the write-denied branch sits at lines 285–296 (the
line numbers have clearly drifted under the accumulated fix-commentary — lines 260–265 in this
version are an unrelated `isinstance(rec, dict)` guard). The branch as it stands:

```python
if not dry and not landed:
    print(f"\nWRITE DENIED {ROLL} -- replace refused; roll is UNCHANGED on disk, "
          f"the fixes above did not land and will retry next run")
    print(f"\nroll unchanged: {have_on_disk}/{len(roll)} sources catalogued (pre-fix figures)"
          + caveat)
    return 1
```

correctly (a) prints an explicit WRITE DENIED line, (b) reports `have_on_disk`, a count snapshotted
*before* the repair loop mutated `roll` in place (line 64), so the "pre-fix figures" label is
honest, and (c) returns 1, which `sys.exit(main())` at the bottom of the file correctly propagates.
I did not re-file this. Per the instructions, I'm noting it here as apparently already resolved
rather than silently dropping it.

### Finding RR1 — a residual, low-probability race between the console summary and the actual write (very low confidence)

On the success path (`landed = True`, or `dry` mode), the closing summary —

```python
have = sum(1 for r in roll if r.get("entry_count", 0) > 0)
total = sum(r.get("entry_count", 0) for r in roll)
print(f"\nroll now: {have}/{len(roll)} sources catalogued, {total:,} entries" + caveat)
```

— reads off the **local**, already-repaired `roll` list, whose per-row `status` was set
unconditionally inside the repair loop (`r["status"] = want`) once that row's *originally-loaded*
status was not `_roll.OUT_OF_SCOPE`. The value actually persisted to disk goes through a
different path: `_roll.mutate(_apply, path=ROLL)` re-reads the file fresh and re-checks
`r.get("status") != _roll.OUT_OF_SCOPE` against that fresh read before applying the status half
of `repairs`. If a row is marked out-of-scope by another process in the window between this
script's initial load and `_roll.mutate`'s fresh read, the file on disk correctly keeps it
excluded, but this script's own closing "roll now: N/M sources catalogued" line was computed
from the local copy, which does not know about that concurrent exclusion and may report a status
that no longer matches what was actually written. This requires a genuine race (another process
re-marking a source out-of-scope in a narrow window) and is consistent with the module's own
stated design — I flag it only because the module goes to unusual lengths elsewhere to make sure
printed summaries match what landed, and this one path is the one place I could construct where
they might not, however rarely.

---

## propagation.py

### Finding P1 — `main()` is not wrapped in `sys.exit()`, unlike every sibling module in this batch (question / low severity)

```python
if __name__ == "__main__":
    main()
```

Every other module audited in this batch (`chain.py`, `weave_index.py`, `sevenfold.py`,
`render.py`, `resync_roll.py`) ends with `sys.exit(main())`, and `resync_roll.py`'s own
docstring/comments explicitly call out "the exit code here must mean the same thing the standard
it feeds does" as a recurring, previously-real defect class in this project (order 8605c2ed6061,
citing `generate.py, weave_index.py, sweep.py, feats.py and handbuilt.py` by name as modules that
already learned this lesson). `propagation.py`'s `main()` currently has no `return` statement
that carries a value (its early-return branches — e.g. the `DISCONNECTED` case — are bare
`return`, i.e. `None`), so today this is harmless: `main()` always implicitly returns `None`
either way, and `sys.exit(None)` and a bare fall-through both exit 0. But it is the one module in
this batch that does not follow the pattern the project has repeatedly had to retrofit elsewhere,
and the `DISCONNECTED` branch in particular (`if not path: print(...); return`) is exactly the
shape ("this run found something the caller needed to know was NOT clean") that the project's
own doctrine says must reach the exit code. If a future change adds a meaningful return value on
that branch (a natural thing to want, since "no shared furniture at any remove" is a real
negative finding for a script whose purpose is to answer "how far apart are these two shelves"),
the missing `sys.exit()` would silently swallow it, repeating the exact defect class this project
has already paid for five times. Low severity today; flagging because it is the specific latent
shape the project has a standing rule against.

---

## Summary of what to file

- **M1** (magnitude.py, three sites: lines 806, 975, 1131) — `isinstance(x, (int, float))`
  admits Python `bool`, letting a boolean model answer for `score` slip past the status-vs-number
  gate as a numeric 1.0/0.0. Low severity, not observed in practice, easy fix
  (`and not isinstance(x, bool)`).
- **R1** (render.py, `children_of`, lines ~205–215) — the coordinate-completeness guard accepts
  a `coord` that names *some* but not all of the tier's prefix keys, which would (if ever called
  that way) silently pool children across an unspecified dimension rather than raising the way
  a fully-empty `coord` does. Not observed to be reachable from any current caller; flagged as a
  question about whether the guard fully delivers on its own stated intent.
- **P1** (propagation.py, final two lines) — `main()` is called bare instead of via
  `sys.exit(main())`, the one module in this batch that doesn't follow that convention. Harmless
  today (no code path returns a non-None value), but is exactly the latent-exit-code-loss shape
  the project has fixed five times elsewhere per resync_roll.py's own citation list.
- **RR1** (resync_roll.py) — a narrow, race-dependent mismatch between the script's own closing
  summary (built from a locally-mutated in-memory `roll`) and what a concurrent OWNER-exclusion
  change would actually cause to land on disk. Very low confidence/severity; noted rather than
  filed as a hard defect.
- Confirmed the previously-filed resync_roll.py write-denied issue (order 64ffa3ba30df) already
  reads correctly in the current source and is not wider than described — not re-filed.
- No new findings in chain.py, secondopinion.py, weave_index.py, or sevenfold.py after a
  line-by-line read; each module's extensive in-line "this used to be wrong" commentary was
  spot-checked against the surrounding code and found to accurately describe fixes that are
  actually present.
