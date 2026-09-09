# AUDIT — Panscriptum run #48, batch 03

Batch: 03
Modules assigned: `src/pipeline.py`, `src/thread_integrity.py`, `src/feats_index.py`,
`src/axis_correlation.py`, `src/scope.py`, `src/physics.py`, `src/cachekey.py`,
`src/repass_bands.py`

Lines read, all in full, sequential chunks, no sampling:
- `src/pipeline.py` — 3,447 lines (1–3448)
- `src/thread_integrity.py` — 721 lines (1–722)
- `src/feats_index.py` — 571 lines (1–572)
- `src/axis_correlation.py` — 443 lines (1–444)
- `src/scope.py` — 368 lines (1–369)
- `src/physics.py` — 312 lines (1–313)
- `src/cachekey.py` — 213 lines (1–214)
- `src/repass_bands.py` — 189 lines (1–190)

Cross-checks: `grep` over all eight files for `\[:[0-9]+\]` slice/truncation shapes (each hit
manually classified as live code vs. a docstring/comment quoting historical, already-fixed code);
`grep` for every stored-but-possibly-unread field name (`unassayable_digest`); `grep` across the
whole `src/` tree for who else reads/writes `data/SCOPE.json`; reading `src/silence.py`'s
`write_json`/`replace_retry` to confirm exactly what atomicity guarantee it does and does not
provide (atomic-against-torn-reads, **not** a lock against a second whole-document writer).

Both already-filed items named in my brief (`codewatch.exit_if_stale` phase-boundary latency,
`b67c5d98c91f`; `feats_index.feats_for_source`'s bare `[]` for an unbound source, `c8dc624e4e02`)
were re-encountered during the read and are not re-reported below.

These eight modules are, on the whole, exceptionally hardened — most of the "this looks wrong"
reactions I had while reading turned out to be a historical defect already fixed, with a
docstring recording the incident, the measurement, and the order number. The findings below are
the ones that survived checking against the current source.

---

## FINDING 1 — MAJOR — `pipeline.py:2227`: `subroom_rejected` is an unmarked truncation, unlike its sibling field 11 lines above it

**What is wrong.** In `phase_entrypass`'s per-result loop:

```
2213:                else:
2214:                    batch[i]["topic"] = "unclassified"
2215:                    if topic:
2216:                        batch[i]["topic_rejected"] = _stored_cut(topic, 120)
2217:                # The same shape for `subroom`, and CHECKED AGAINST THE ROOM rather than only
...
2224:                else:
2225:                    batch[i]["subroom"] = SUBROOM_UNCLASSIFIED if sub else SUBROOM_NONE
2226:                    if sub:
2227:                        batch[i]["subroom_rejected"] = sub[:120]
```

`topic_rejected` (line 2216) is written through `_stored_cut(topic, 120)` — the helper defined at
`pipeline.py:230-243` specifically so that "a value cut at the bound reads as a COMPLETE value
with nothing distinguishing it from one that simply ended there." `_stored_cut` appends
`"... (+N chars)"` when it actually truncates. `subroom_rejected` (line 2227), the comment's own
declared "same shape," instead does a bare Python slice `sub[:120]` with no marker at all — a
model-returned `subroom` string longer than 120 characters is silently truncated on disk with
nothing in the stored value (or anywhere else) telling a later reader that it continued. This is
Hard Rule 0's exact target: an unmarked cap on a stored diagnostic field.

**How I verified it.** Read both branches side by side in the same `if/else` block (lines
2209-2228); confirmed `_stored_cut`'s docstring and behavior at lines 230-243 (it is used
identically for `evidence`, `rationale`, `scale_note`, `scale_note_rejected`, and
`topic_rejected` elsewhere in this same file — five call sites, all consistent, per the comment
at `pipeline.py:233` naming "these five fields"). `subroom_rejected` is carried into
`MERGED_ENTRY_FIELDS` (line 669) and so is a genuinely persisted, two-writer-merged field, not a
throwaway. `subroom` is explicitly documented (lines 689-697) as "the one field added after this
mechanism was written" — the same class of catch-up gap that comment already flags for a
different companion (the `MERGED_ENTRY_FIELDS`/`ENTRY_REJECTION_COMPANIONS` wiring), just missed
for the truncation helper specifically.

**Proposed remedy.** Change line 2227 to `batch[i]["subroom_rejected"] = _stored_cut(sub, 120)`,
matching line 2216 exactly.

---

## FINDING 2 — MAJOR — `repass_bands.py`: per-source demotion detail is captured and then never printed anywhere

**What is wrong.** `main()` builds `demoted_sources` — a list of `(source, band,
evidence_snippet)` tuples, one per source whose ceiling magnitude is demoted for lacking valid
evidence:

```
38:    demoted_sources = []
...
53:            demoted_sources.append((src, band, (syn.get("evidence") or "")[:70]))
...
132:    print("\nSOURCE CEILINGS")
133:    print(f"  demoted to unassayed: {len(demoted_sources):,} of {len(recs):,}")
```

`demoted_sources` is referenced exactly three times in the file (lines 38, 53, 133) and the only
use of its content is `len(demoted_sources)` at line 133. There is no loop anywhere in `main()`
printing the individual `(source, band, evidence)` rows the way the sibling **ENTRY**-level
lists are (`SURVIVORS`, lines 156-159, and `DEMOTED`, lines 166-170, both explicitly uncapped per
Hard Rule 0). An operator running `--apply` sees "SOURCE CEILINGS demoted to unassayed: 12 of
215" with no way to learn *which* 12 sources without diffing `data/records/*.json` by hand — the
exact defect class `thread_integrity.py`'s own header (its DANGLING listing, `main()` around
lines 559-566) describes and was fixed for: "the most severe finding this module makes...
existed as a single number in the count block above and nowhere else."

**How I verified it.** `grep -n "demoted_sources" src/repass_bands.py` returns only the three
lines above; read the whole 189-line file end to end to confirm no later block iterates it.

**Proposed remedy.** Add a print loop for `demoted_sources` beside (or in place of) the bare
count, in the same uncapped idiom already used for `kept_entries`/`demoted_entries` two blocks
below it.

---

## FINDING 3 — MAJOR — `scope.py`: `SCOPE.json` is a whole-document read-modify-write with no drift detection, unlike this project's other shared-state writers

**What is wrong.** Two separate code paths in this file read the entire `data/SCOPE.json` into
memory, mutate it, and write the whole thing back, with nothing to detect that another `scope.py`
invocation changed the file in between:

- `build()` (the long crawl path): reads the whole file once at start (lines 224-226), holds it
  in memory across a loop that can run for a long time (the module's own comment at lines
  219-222 calls the full 155-host re-probe "a live crawl... not started by the run that did the
  withdrawal" because of how long it takes), mutates one key per probed host (line 269), then
  writes the entire `out` dict back in one `silence.write_json` call (line 278).
- `main()`'s `--host` path: reads the whole file (line 330), mutates a single key (line 338),
  writes the whole thing back (line 340).

`silence.write_json`/`replace_retry` (`src/silence.py:722-853`) make the *rename* atomic and
guard against a torn read of a half-written file — but they provide no protection at all against
two writers each holding their own complete, independently-stale snapshot of the document: the
second writer's whole-document write simply replaces the first writer's, discarding whichever
single-key update the first writer had already landed. If a `--host` fixup call is issued while a
long `--build` crawl is still in flight (or two `--build`/`--host` invocations otherwise
overlap), whichever finishes last silently erases the other's update. This is precisely the "lost
update" class of bug the brief calls out as this project's documented history on
`SWEEP_ROLL.json`/`PIPELINE_STATE.json` — and notably, `pipeline.py`'s own record writers
(`write_record`, `_merge_top_keys`) were specifically hardened against exactly this shape via a
content digest and a per-key watermark (`pipeline.py:1090-1153`, `1345-1360`) after being caught
doing the same whole-document overwrite; `scope.py`'s single writer has none of that.

**How I verified it.** Read `build()` (lines 200-279) and the `--host` branch of `main()` (lines
327-344) in full; confirmed via `grep -rn "SCOPE.json" src/*.py` that only `scope.py` itself ever
*writes* this file (`magnitude.py` and `pipeline.py` only read it), so the exposure is between
two `scope.py` processes, not cross-module; read `silence.write_json`/`replace_retry` in full
(`src/silence.py:700-853`) to confirm they solve torn-write safety only, not concurrent-writer
merge safety.

**Caveat.** I found no evidence this module is invoked as a standing/scheduled job elsewhere
(`grep` of `allsweep.py`/`overnight.py` finds only a comment mentioning it), so the practical
exposure window is "an operator runs `--host` by hand while a `--build` crawl they started
earlier is still running" rather than a routine automated collision. The mechanism is real and
unguarded either way.

**Proposed remedy.** Give `build()`/`--host` the same drift check `write_record` already uses
elsewhere in this project: re-read `SCOPE.json` immediately before the final write and merge any
keys that changed since the initial read, rather than writing the load-time snapshot whole.

---

## FINDING 4 — MINOR — `repass_bands.py`: printed evidence/scale-note previews are truncated at 70 characters with no cut marker

**What is wrong.** Three places build report rows carrying a preview of stored evidence text,
truncated with a bare Python slice and no indication that a cut happened:

```
53:            demoted_sources.append((src, band, (syn.get("evidence") or "")[:70]))
...
67:                    kept_entries.append((src, e.get("name"), b, sn[:70]))
...
69:                    demoted_entries.append((src, e.get("name"), b, sn[:70]))
```

These previews are drawn from fields (`synthesis.evidence`, `scale_note`) that this project
already has an established, named convention for cutting *with* a marker —
`pipeline._stored_cut()` (`pipeline.py:230-243`), which is what wrote these same fields to disk
in the first place (at up to 500-900 characters, itself marked with `"... (+N chars)"` when it
actually cuts). Slicing an already-possibly-marked string to another 70 characters can silently
swallow that marker too, so a reader of the `SURVIVORS`/`DEMOTED` report has no way to tell "this
is the whole note" from "this note was cut once at 500/600/900 on disk, then cut again here at
70, and I am seeing 70 characters of a much longer original."

**How I verified it.** Confirmed all three call sites via `grep -n "\[:70\]" src/repass_bands.py`;
confirmed the fields' at-rest truncation convention via `pipeline.py:230-243` and its call sites
at `pipeline.py:1726-1727` (`evidence`/`rationale`) and `2167` (`scale_note`).

**Proposed remedy.** Either drop the 70-char cap (these are report lines already printed one per
row, not packed into a fixed-width table the way `_namecol`'s aligned columns are), or cut with
the same `"... (+N chars)"` idiom used everywhere else in this codebase for exactly this purpose.

---

## FINDING 5 — MINOR — `feats_index.py:429-442`: `binding_report()` silently drops unreadable or source-less catalogue files from every bucket, including its own error bucket

**What is wrong.**

```
429:    import glob
430:    root = records_dir or os.path.join(HERE, "data", "records")
431:    hosts = host_to_sources()
432:    out = {"bound": [], "pages": [], "doc": [], "unbound": [], "unknown": []}
433:    for q in sorted(glob.glob(os.path.join(root, "*.json"))):
434:        try:
435:            with open(q, encoding="utf-8") as f:
436:                src = json.load(f).get("source")
437:        except Exception:
438:            silence.note("feats_index.py:binding-report-record")
439:            continue
440:        if src:
441:            out.setdefault(source_binding(src, hosts), []).append(src)
442:    return {k: sorted(set(v)) for k, v in out.items()}
```

A record file that will not parse (line 437-439) or that parses but carries no `source` key
(line 440's `if src:` guard) is dropped from the function entirely — it lands in none of
`bound`/`pages`/`doc`/`unbound`/`unknown`, and (for the missing-`source` case) not even a
`silence.note` is recorded. This is the one place in an otherwise very careful module (compare
`audit()`, which explicitly tracks `unreadable`/`collided` counts specifically so "each loss
SHRANK the denominator" cannot happen silently, per its own docstring) where a corpus-side fault
is simply invisible rather than counted. `main()`'s printed report (lines 545-559) has no line
that could ever reveal this population.

**How I verified it.** Read `binding_report()` end to end; confirmed no counter or return field
exists anywhere in the function for either failure path; confirmed `main()`'s consumption of
`binding_report()`'s output (lines 545-559) has no corresponding line.

**Proposed remedy.** Track and report (at minimum count, per Hard Rule 0 named) both the
unreadable-file case and the no-`source`-field case, the same way `load_index()`'s
`faults["unreadable"]`/`faults["collided"]` already do one function away.

---

## FINDING 6 — QUESTION / MINOR — `pipeline.py:1741`: `unassayable_digest` is written and never read anywhere

**What is wrong.** `phase_synthesis` stamps a content digest onto every source found unassayable:

```
1738:        if not _ceiling:
1739:            rec["synthesis"]["unassayable"] = True
1740:            rec["synthesis"]["unassayable_cast_size"] = len(rec.get("entries") or [])
1741:            rec["synthesis"]["unassayable_digest"] = _entry_digest(rec)
```

but the readmission gate that decides whether an unassayable verdict is stale,
`_unassayable_verdict_is_stale` (lines 1603-1636), only ever compares `unassayable_cast_size`
against the current entry count (`len(...) > was`, line 1635) — it never reads
`unassayable_digest`. A `grep -rn "unassayable_digest" src/*.py` finds only the one write site
above; nothing in the tree consults it. The digest would be exactly what is needed to catch a
**same-size** cast edit — a rename, a dedup-then-add, a description correction that changes what
phase 1 could plausibly see without changing the entry count — which is the identical
"count-blind, digest would have caught it" gap `write_record`'s own docstring describes fixing
for its own drift check two hundred lines later in this same file ("DRIFT IS A DIGEST OF THE
ENTRY NAMES, NOT A COUNT OF THEM", `pipeline.py:1170-1180`). I flag this as a QUESTION rather
than a firm finding because I cannot rule out that `unassayable_digest` is deliberately staged
for a not-yet-written second check, or is meant purely as a forensic breadcrumb for a human
diffing records by hand rather than as a machine-read gate input — nothing in the surrounding
comment says which.

**How I verified it.** `grep -rn "unassayable_digest" src/*.py` (one hit, the write site); read
`_unassayable_verdict_is_stale`'s full docstring and body (lines 1603-1636), which discusses only
cast size, never digest.

**Proposed remedy (if intended as a live check).** Have `_unassayable_verdict_is_stale` also
re-admit a source when `_entry_digest(rec) != syn.get("unassayable_digest")` even at unchanged
cast size — or, if it is deliberately a forensic-only field, a one-line comment saying so would
save the next reader the same trip through `write_record`'s drift-detection history that produced
this finding.

---

## FINDING 7 — MINOR / QUESTION — `pipeline.py`: source names are truncated in three progress-log lines with no continuation marker

**What is wrong.**

```
1665:            log("  re-nominating %s: unassayable verdict was reached against %s entries, "
...                  % (src[:44], ...))
1758:        log(f"  {src[:44]:46s} {band:10s} {rec['synthesis']['ceiling_entity'][:34]}")
2275:        log(f"  {src[:50]:52s} done")
```

Source names are cut to 44/50 characters for column alignment in `state/pipeline.log`, with no
`...`/count-of-remainder marker. This is the same shape `thread_integrity.py`'s own `_namecol`
fix (its docstring, lines 438-452) explicitly names and repairs: "THE NAMES USED TO BE SLICED...
main() is the ONLY reporting surface this module has... a clipped name cannot be pasted into
catalog.py." Here the mitigating fact is that `pipeline.log` is **not** the only place the name
is recorded — the same source's full, untruncated name is always present in `rec["source"]`
inside `data/records/*.json`, in the done-keys (`f"{src}#{start}"`, never truncated, line 2078),
and in `RUN_STATUS.md`'s corpus counts — so an operator who needs the exact name for e.g. a
source over 44 characters is not actually stranded, only inconvenienced. I am filing this as
MINOR/QUESTION rather than MAJOR for that reason, but it is the identical shape Hard Rule 0
names, in a file that otherwise enforces the rule with unusual care everywhere else (see e.g.
the fully-uncapped `refused`/`empty` lists in `phase_write`, lines 3010-3027).

**How I verified it.** `grep -noE "[A-Za-z_][A-Za-z_0-9.()]*\[:[0-9]+\]" src/pipeline.py` and
manually classified every hit; the three above are live code, the remaining hits at that pattern
(1351, 1454, 1479, 1561, 3010) are either a hash-digest slice (harmless) or inside a comment
quoting historical, already-fixed code.

**Proposed remedy.** Widen the column or drop the cap; if 44/50 is kept for log readability, note
in the format string (or beside it) that the name may continue, the same way `_stored_cut` does
for stored fields.

---

## What I read and found nothing wrong in

- **`physics.py`** (full file): every arithmetic function (`kinetic`, `joules_for`,
  `sphere_volume`, `binding_energy`) has matching, non-overlapping guards for non-positive,
  non-finite, and post-computation non-finite results; verified the NaN-vs-infinity asymmetry
  each docstring claims is actually resolved on both sides. No live gap found.
- **`cachekey.py`** (full file): `owns()`/`load()`/`write_path()`'s collision-disambiguation logic
  was traced through several concrete collision scenarios (name-only collision, host-and-name
  collision, three-way collision on one natural path) and each resolves correctly via the
  per-name SHA1 suffix. `_suffix()`'s dependence on `name` alone (not `host`) means two different
  entities sharing both a name and a host-dir would still need `owns()`'s host check to
  disambiguate, which it has; no scenario found where it doesn't.
- **`axis_correlation.py`** (full file): `measure()`, `_pearson()`, `widening()`, and the
  `_no_matrix()`/`MATRIX_FALLBACK_REASON` announce-once machinery were all traced against their
  documented histories and found to match. The `doc = doc or load()` pattern in `rho()`/
  `widening()` would mishandle an explicitly-passed empty dict (`doc={}`, which is falsy) as
  "no doc supplied" — but `grep`-ing every caller in `src/` (`assay.py:_rho`, `drill.py`) shows
  none ever passes a falsy-but-real `doc`, so this is a latent shape rather than a live bug and I
  am not filing it as a finding.
- **`thread_integrity.py`** (full file): the DANGLING/PARTIALLY-DANGLING/RECIPROCAL/
  ASYMMETRIC-* classification logic in `classify()`, the `_floor_verdict()` ratchet state
  machine, and `load_thread_graph()`'s directed-edge derivation were each traced by hand against
  worked examples; all matched their docstrings. This file's own extensive "already fixed"
  commentary (the DANGLING-never-printed fix, the `(b,a) in seen` dedup, the both-directions
  asymmetry test) was checked against current code, not taken on faith, and holds.
- **`scope.py`**: `scope_for()`'s `ProbeUnread`-vs-genuine-empty distinction, the `PROBE_VERSION`
  contract-bump re-probe mechanism, and `build()`'s per-host exception handling (never caching a
  transient failure as a verdict) were all traced and match their documentation. Only the
  cross-invocation write race (Finding 3) survived scrutiny.
- **`feats_index.py`**: the host-derivation-from-directory-name fallback (`by_dir`), the
  within-source entry-name-collision tracking (`_ENTRY_COLLISIONS`), and `load_index()`'s
  fault-counting (`faults["unreadable"]`/`faults["collided"]`) were traced and match their
  documentation. Only `binding_report()`'s narrower gap (Finding 5) survived scrutiny.
- **`pipeline.py`**: the two-writer contract (`write_record` / `write_record_catalogue`), their
  shared per-entry pairing logic (`_entry_pair_key`, the duplicate-name ordinal pairing in both
  writers), the top-level-key merge/watermark machinery (`_merge_top_keys`, `_TOP_SNAPSHOT`), the
  `_landed`/`gate_done` write-verdict gating used by every phase, and the `valid_scale_note`
  evidence-gate regex stack (`_MAGNITUDE`/`_ACT`/`_OBJECT`/`_PATIENT`/`_REPUTATION`/`_STATBLOCK`)
  were all read closely and traced against their documented incident histories; all matched.
  `main()`'s phase-loop exit-code handling (the `sys.exit(main())` fix, the stalled-phase `return
  1`, the `--phase` range validation) was checked and is correct. I did not find any check in
  this file that is structurally unable to fire, nor any exception handler that treats an
  unreadable shared file as "fine" — every fail-open path I found was already the subject of a
  fix documented in the surrounding comment and confirmed present in current code.
