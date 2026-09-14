# AUDIT — run57, batch 13

Modules read in full, top to bottom, no sampling: `src/assay.py` (1914 lines), `src/dashboard.py`
(1248), `src/derivation.py` (811), `src/custodes.py` (698), `src/withdraw_chapters.py` (519),
`src/pick_model.py` (443), `src/events.py` (336), `src/propagation.py` (254), `src/module_index.py`
(192). Audit only — no file was edited, no destructive tool was run, `prose_enabled`/
`step4_enabled` were not touched, no halt was raised or cleared.

Before reading, the open work-order queue was checked (`workorders.open_orders()`), and prior
audit trails for these exact nine modules were read in full: `handoff/sweep56/AUDIT_batch03.md`
(module_index.py), `AUDIT_batch04.md` (withdraw_chapters.py), `AUDIT_batch09.md` (custodes.py),
`AUDIT_batch11.md` (pick_model.py), `AUDIT_batch13.md` (assay.py, dashboard.py, derivation.py),
`AUDIT_batch15.md` (propagation.py), `AUDIT_batch16.md` (events.py). All nine modules were already
read in full by at least one, and in several cases two, prior sweeps (48, 54, 56), each finding the
same small set of defects. This batch's job was therefore to (a) verify each previously-reported
finding is still live against the CURRENT source rather than trust the citation, (b) confirm or
correct the two items the brief named explicitly (`custodes.py`'s Lumen docstring, `events.py`'s
unmarked cuts), and (c) hunt independently for anything the three prior passes missed. One new
defect was found (in `withdraw_chapters.py`); everything else confirmed as already known.

---

## src/assay.py

**KNOWN(89503c58409f)** — three stale self-citations, all re-verified against the current file
and all still exactly where the order describes:

- **assay.py:811** — quote: `` when they cross. axis_score already refuses that -- and the mutation survivor at L228 is``. The guard actually being described (`axis_score`'s `if not hi or hi <= lo: return None`) is at **assay.py:348**, not L228.
- **assay.py:890-891** — quote: `` here is refused by a sentence that names it as acceptable. anchors.py:427 is worse: it`` / `` indexes INSTRUMENT_WINDOWS[b] for every b in LADDER with no guard at all``. Per the order, the unguarded lookup this describes is actually at assay.py:1544-1549 (`instrument()`'s `lo, hi = INSTRUMENT_WINDOWS[anchor]`), a citation `drill.py:10731,10753` independently copied wrong.
- **assay.py:1868** — quote: `` this is. The mutation survivor at :1392 (`<=` flipped to `>`) is what exposed it:``. The actual `<=` comparison is at **assay.py:1872** (`"covers_all_signatures": all(abs(v - centre) <= interval for v in vals)`).

All three verified byte-for-byte against the order text quoted in `dc9ffadae765`'s sibling order
`89503c58409f` (`LINE_CITATIONS_IN_SRC_COMMENTS_HAVE_ROTTED_AT_SCALE`). Not re-filing.

**KNOWN(carried QUESTION, sweep56 batch13)** — `_check_constants()` (assay.py:772-846) still does
not verify that each `INSTRUMENT_WINDOWS` `(lo, hi)` pair is internally sane (`lo <= hi`), unlike
every other constant table in this file. Confirmed the live table is still well-ordered
(`"M5"`-`"M10": (30, 30)` etc.) so this remains dormant, not a live bug.

**Nothing new found.** Re-verified independently, per the brief's specific asks:
- **A score that cannot vary**: none found. `axis_score`'s three RAISE branches (off-Ladder band,
  non-energetic axis, misspelt Measure) are all evaluated before the quantity, and the two
  remaining `None` branches (`x is None or x <= 0`; degenerate band edges, refused at import by
  `_check_constants`) leave the M0-M9 log-scaled formula (assay.py:350-351) the only live scoring
  path, and it is a continuous function of `x`.
- **An unreachable band boundary / outcome**: the M10 top-rung clamp (assay.py:344-346) is
  reachable only after axis/band validation (traced and confirmed, matching sweep56 batch13's own
  trace) and is documented as the known-open M18 saturation, not silent.
- **A default silently substituting for a missing measurement**: `_rho()`'s independence fallback
  (rho=0.0 when `data/AXIS_CORRELATION.json` is unavailable, assay.py:1115-1128) is the one
  candidate, and it is NOT silent — it sets `RHO_FALLBACK_REASON` once, prints to stderr, and
  stamps `correlation_source` on every returned assay dict (confirmed both call sites,
  assay.py:1040-1112 and 1457). `denom = ... or 1.0` (assay.py:1352) is confirmed unreachable given
  `_check_weights`'s refusal of negative/zero-sum tables, kept as a documented backstop only — same
  conclusion sweep56 batch13 and sweep34's own order 0d5ab3aab8ff reached.

---

## src/dashboard.py

**Nothing found.** Re-confirms sweep56 batch13's "nothing found." Every panel builder
(`quotas`, `throughput`, `jobs`, `library`, `watch`, `movement`, `metrics`, `safety`) is
individually try/excepted with a distinct `silence.note` tag; no bare `except: pass` anywhere.
`main()` fails closed on an unimportable `escalation` (raises `SystemExit`), and correctly treats
"read-only instrument" as the reason it does NOT refuse to start under a standing halt (traced the
argument at dashboard.py:1178-1211 against `escalation.assert_clear`'s actual behaviour — the
process still calls `assert_clear`, still reads the answer, and renders it as the page's headline
rather than converting it into an absent instrument; confirmed it writes nothing outside
`state/failures.json` and `state/CODEWATCH.json`, matching the criterion the comment cites).
`movement()`'s corrupt-history healing, the three-shape guard on stored history rows, and the
`hist[:-1]` baseline-exclusion logic were traced by hand and match their documenting comments.

---

## src/derivation.py

**KNOWN(89503c58409f)** — the self-contradicting `SCAN_MODULES` docstring, re-verified present at
both cited spots:

- **derivation.py:628-630** (inside `scan_constants_with_reason`'s docstring): `` SCAN_MODULES is built from `os.listdir(HERE)` over the same directory this function then reads (order ca1ed2be8c51 notes this listing is still flat and misses `src/deprecated/`, left open this shift...) ``
- **derivation.py:790-792** (inside `main()`): `` SCAN_MODULES is built from os.listdir of this same directory, so "absent" is a race and "will not parse" is the only thing a reader realistically sees. ``

Both still assert `os.listdir`, top-level-only. The actual `_scan_modules()` (derivation.py:584-593)
uses `os.walk(HERE)` recursively with `__pycache__` pruned — confirmed unchanged since sweep56
batch13's reading, and the comment block immediately above `_scan_modules` (derivation.py:565-583)
still correctly describes the `os.walk` fix. The contradiction is cosmetic (the code is correct;
only the two docstrings elsewhere in the same file are stale) but still live. Not re-filing.

**Nothing else found.** `check_graph()`'s `kind`-taxonomy validation, `_target_names`'s
tuple/starred-target unwrapping, `scan_constants_with_reason`'s absent-vs-SyntaxError distinction,
and `main()`'s early-return-on-cycle fix (avoiding the non-terminating deepest-chain walk) were all
re-traced and match their comments. The `_chains` and "where constants live" panels remain
genuinely uncapped.

---

## src/custodes.py

**KNOWN(360c6b8c68e5)** — CONFIRMED, per the brief's specific request. The Lumen-abstention
docstring still contradicts its own caller:

- **custodes.py:355-357**: `` both were then wired to a keyword argument that no production caller supplies -- `anchors.py:190`, the single real call site, passes neither `eta` nor `distance`/`years_since`. ``
- **custodes.py:438-440** (`convene`'s docstring): `` `distance`/`years_since` are what Lumen reads, via `propagation.observed_mark`. No caller supplies them either, so `staleness_widening` contributes exactly 0.0 to every real interval. ``

Both quotes verified byte-for-byte against the current file at exactly those line numbers — the
text has not moved or changed since order `360c6b8c68e5` was filed (sweep56 batch09, corroborated
by that run's own `allsweep` output). I did not re-read `anchors.py` myself (outside this batch's
module set), but the order's own remedy — "re-read `anchors.py`'s call, state what it actually
passes" — is unchanged as an open action item; nothing in `custodes.py` itself has been touched to
reflect it. Confirming KNOWN rather than re-deriving.

**KNOWN(5bb12b398783)**, item 3 — the `prior_share = 1.0` default on exact-zero variance, still
present verbatim at **custodes.py:508-509**:
```python
prior_share = (prior_var / total_var) if total_var > 0 else 1.0
prior_share = max(0.0, min(1.0, prior_share))
```
Structurally hard to reach (requires every one of the ten Custodes' readings to be numerically
identical), and already filed as a QUESTION rather than a defect. Confirmed still open, not
re-filing.

**Nothing else found.** `_transit_widening`'s per-dispersive-Custos accumulation was checked for
double-counting if two future Custodes both declared `dispersive=True` with `dof="currency"` — the
loop would sum `staleness_widening(...)` once per such Custos rather than once per mechanism, which
would silently double the widening. No live instance today (only Lumen carries the flag), and the
function's own docstring already reasons about "a Custos flagged dispersive in any other direction"
as a named edge case, so this reads as the same class of "no check refuses this future pairing yet"
gap the file already names for zero-tilt/non-zero-sensitivity Custodes (`table_faults()`'s own
docstring) rather than a fresh, unacknowledged shape. Filed as a QUESTION rather than a defect for
that reason — no live consequence, and the module's own established pattern is to name such gaps
rather than guard every one pre-emptively.

---

## src/withdraw_chapters.py

**KNOWN(89503c58409f)** — stale self-citation, confirmed unchanged:
- **withdraw_chapters.py:511**: `` that matched nothing already raised SystemExit at :184 and never reaches here. `` — the actual `raise SystemExit("part of that selection matches nothing...")` is at **withdraw_chapters.py:209**, not :184 (which is now a comment line inside an unrelated block).

**KNOWN(d7efd67caa6f)** — stale cross-file citation (auto-detected by `citecheck.stale_citations`,
`seen: 6`, i.e. still currently detected), confirmed unchanged:
- **withdraw_chapters.py:146**: `` FAIL CLOSED ON THE IMPORT, copied from publish.py:1385-1398 and NOT wrapped in a bare `` — `publish.py:1385` is a blank line per the detector; not independently re-verified against `publish.py` (outside this batch), but the citecheck detection is current as of the last recorded `seen`.

**NEW DEFECT — lost-update race on `output/index/catalog.json` and the archive manifest, no
compare-and-swap across two `--go` invocations.**

`main()` reads the whole catalog once, near the top:
```python
179	    arch = os.path.join(HERE, "output", "withdrawn_" + a.label)
180	    with open(CATALOG, encoding="utf-8") as f:
181	        cat = json.load(f)
```
does all of its selection and file-moving against that in-memory snapshot, then near the bottom
computes and writes back `remaining` — the snapshot minus this run's own withdrawals — with no
re-check that the on-disk file is still the same document it read:
```python
370	    withdrawn = {k: v for k, v in sel.items() if k not in stuck}
371	    remaining = {k: v for k, v in cat.items() if k not in withdrawn}
...
437	        catalog_landed = silence.write_json(CATALOG, remaining, indent=2)
```
`silence.write_json` makes this individual write atomic (a torn write cannot land), but atomicity
is not compare-and-swap: it guarantees the bytes that land are whole, not that they are still
correct against a catalog that changed underneath the read at line 180-181.

**Why this is live, not theoretical, in this specific tool.** The module's own `--label` default
(today's date) and its extensive collision-guard comments (`_archive_name_free`, order
`8d14f0adda1b`) already establish that two `--go` runs close together is a scenario this file's
author explicitly anticipated and partly engineered against — "a re-run on the same day... walks
straight into it" (withdraw_chapters.py:96-98). That guard closes the FILE-collision half (two
runs writing chapter bytes to the same archive path). It does not close the CATALOG half: if
process A and process B both start (each reading the same `cat` at line 181), and each withdraws a
disjoint selection (e.g. `--source "Song of Syx"` vs `--source "Deep Rock Galactic"`, both entirely
plausible as two operators or two scripted follow-ups clearing separate bad sources), both compute
their own `remaining` from the SAME stale `cat`, and whichever writes `CATALOG` second silently
overwrites the first's write — resurrecting the first process's already-withdrawn entries back
into `catalog.json`, even though their files have genuinely and successfully moved to the archive.
This is the exact "a chapter still sitting in output/raw lost its catalog record anyway" failure
class the module's own top-of-file docstring names as the reason `--source`/`--addr` selection
exists at all (withdraw_chapters.py:13-22) — reached here from the opposite direction: not a
record wrongly dropped, but a correct withdrawal wrongly un-recorded by a second writer.

The identical shape recurs one write later, on the archive's own manifest:
```python
404	        existing_manifest = {}
405	        try:
406	            with open(record_path, encoding="utf-8") as f:
407	                existing_manifest = json.load(f)
408	        except FileNotFoundError:
409	            pass
...
413	        merged_manifest = dict(existing_manifest)
414	        merged_manifest.update(withdrawn)
...
422	        record_landed = silence.write_json(record_path, merged_manifest, indent=2)
```
The surrounding comment (order `959ac19ac3f7`) already fixed the SEQUENTIAL case — a second run on
a later day correctly merges with the first day's manifest rather than replacing it — but the
merge itself is still read-then-write with no CAS, so two genuinely concurrent processes racing on
this same read-modify-write can still lose one side's manifest rows the same way `hosts.add()` was
found to (sweep56 batch04, DEFECT on `src/hosts.py:114-145`) — this is the same shape, on a file
whose own module docstring calls it "the tool whose one job is preserving the record of what was
withdrawn."

**Severity note, matching the house convention for this class of finding**: bounded but real. The
chapter FILES themselves are never lost — they are safely in the archive directory either way, and
`_archive_name_free` prevents the file-level overwrite. What can be lost is only the CATALOG's/
MANIFEST's record of that fact, which is recoverable by a person cross-checking the archive
directory's actual contents against the printed run report, but nothing in the tool detects or
reports the collision automatically the way the file-move collision does. Confidence: **DEFECT** —
the mechanism is real and mechanically reproducible (two concurrent invocations, no lock, no CAS,
one process's write silently discarding the other's), verified by reading the code rather than by
running it (per the rules, `withdraw_chapters.py` was not executed).

**Nothing else found.** `_file_state`'s live/gone/unavailable three-way, `_archive_name_free`'s
FileNotFoundError-only "free" determination, the per-file (not per-entry) `stuck`/`entry_left`/
`amended` bookkeeping, and the dry-run/`--go` counter symmetry were all re-traced and match
sweep56 batch04's own findings — no regression. `main()`'s `assert_clear()` interlock sits above
the argparse block as documented, so there is no path into a `--go` run that skips the halt check.
Every `shutil.move` for both catalogued chapters and unclaimed strays remains correctly gated
behind `if a.go:`, and no destructive path was found reachable without that flag.

---

## src/pick_model.py

**Nothing found.** Re-confirms sweep56 batch11's "nothing found." `save_config`'s atomic replace
via `silence.replace_retry` (with the boolean actually threaded through, not discarded) and the
targeted `re.sub` failure-to-match check were both re-traced and are unchanged. `total_vram_gb()`
vs `free_vram_gb()` remain two clearly-distinguished budgets (by-class vs right-now), each with its
own `is not None` (not truthiness) guard so a genuine `0.0` GB is never confused with an unreadable
instrument — re-verified at both `vram_measured` (pick_model.py:334-336) and the `vram_gb <= 0`
branch (pick_model.py:378-381). `RESIDENT_ONLY`'s hard GPU-only gate and the `refused`/`excluded`
split (two distinct reasons a model is absent from `scored`) are unchanged and correctly reported.

---

## src/events.py

**KNOWN (sweep56 batch16 AUDIT_batch16.md, DEFECT 2) — CONFIRMED, per the brief's specific
request.** Both unmarked console truncations are still present verbatim:

- **events.py:319**: `` print("  %-16s %s" % (e["code"], (e["heading"] or "(cited without a heading)")[:58])) `` — a Chronicle event heading longer than 58 characters is still cut with no ellipsis or "+N chars" marker on the `main()` console report. `EVENTS.json` itself keeps the whole heading (confirmed: `heading` is stored unsliced in `parse()`, events.py:214), so this is console-display-only, not a data loss — but the console reader has no way to know a line was clipped.
- **events.py:326**: `` print("    %-16s %-46s (%s)" % (r["event"], r["span"][:46], r["rule"])) `` — the `--refused` listing (the one view whose entire purpose is letting a person verify a refusal was reasonable) still cuts the bolded span at 46 characters with no marker.

I checked whether either has since been promoted from the sweep56 audit document into the open
work-order queue (`workorders.open_orders()`) and found no dedicated order — `fe99e57e1993`
(`UNMARKED_NAME_CUTS_SWEEP44`) lists a different set of files and does not include `events.py`.
Recording this here as **KNOWN** against the sweep56 batch16 audit trail (its own DEFECT 2), not
re-deriving it as new, but noting it has not yet been filed as a standing work order the way the
`citecheck.py`/`whoruns.py` siblings from the same finding have not been either.

**Nothing else found.** `_looks_like_a_sentence`'s two mechanical shape rules (terminal
punctuation, word count), the deliberate absence of a third grammar-guessing rule (confirmed the
function still returns `False, None` after the two checks, matching the comment's account of what
was removed and why), `_fragments`'s joiner-based splitting (both halves re-checked against the
same shape rules the whole span faced), and `shelf_positions`'s header-match fix (the dead
`.replace("Now ", "")` removed, confirmed absent) were all re-traced and match their documenting
comments. `candidates_refused` and `spans_split` remain uncapped in the written `EVENTS.json`.

---

## src/propagation.py

**Nothing found.** Re-confirms sweep56 batch15's "nothing found." Re-traced `observed_mark()`'s
loop direction and its claim that the trailing `return 0` is unreachable: confirmed
`ascension_years(1) == 0.0`, so the loop's last iteration (rung 1, counting down from
`LADDER_HEIGHT`) always matches once `lag >= 0`, and the `lag < 0` guard is what actually produces
the honest `[^0]`. This is a read-only module (no writes), so no CAS/lost-update question applies.
The `YEARS_PER_UNIT_DISTANCE` comment's own worked numbers (diameter 4.99, Left 4 Dead -> Dragon
Ball Z at 1.126) are explicitly self-disclaimed as a point-in-time measurement of a live graph that
"cannot be frozen into a comment and stay correct" — not treated as a stale-citation defect, since
the comment itself tells the reader not to trust the number and to re-measure via the CLI.

---

## src/module_index.py

**Nothing found.** Re-confirms sweep56 batch03's "nothing found." `_modules()`'s recursive
`os.walk` (correctly including `src/deprecated/`, unlike `derivation.py`'s still-stale docstring
above), the duplicate-group-name check (`seen_in`/`dupe_names`), the stale-group-name check, and
the atomic write via `silence.replace_retry` with a real non-zero exit code on denial were all
re-traced and are unchanged. No `file.py:NNN` citations exist in this file to go stale (deliberate,
per its own docstring, for exactly the reason this sweep exists).

---

## Coverage recorded

```
C:/Users/imarl/miniconda3/python.exe -c "import sys; sys.path.insert(0,'src'); import sweep_plan; print(sweep_plan.record('run57', ['assay.py','dashboard.py','derivation.py','custodes.py','withdraw_chapters.py','pick_model.py','events.py','propagation.py','module_index.py'], batch=13))"
```
run from the repo root with `PYTHONIOENCODING=utf-8`; result recorded in the summary below.

## Summary

| Module | NEW DEFECT | QUESTION | KNOWN |
|---|---|---|---|
| assay.py | 0 | 0 | 4 (3 stale citations under 89503c58409f + 1 carried QUESTION) |
| dashboard.py | 0 | 0 | 0 |
| derivation.py | 0 | 0 | 1 (89503c58409f) |
| custodes.py | 0 | 1 (dispersive double-count, no live instance) | 2 (360c6b8c68e5, 5bb12b398783) |
| withdraw_chapters.py | 1 (catalog/manifest lost-update race) | 0 | 2 (89503c58409f, d7efd67caa6f) |
| pick_model.py | 0 | 0 | 0 |
| events.py | 0 | 0 | 1 (sweep56 batch16 DEFECT 2, both sites) |
| propagation.py | 0 | 0 | 0 |
| module_index.py | 0 | 0 | 0 |
| **Total** | **1** | **1** | **10 citations/findings across 5 modules** |
