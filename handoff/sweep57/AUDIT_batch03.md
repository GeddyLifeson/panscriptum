# Sweep57 batch03 audit — pipeline.py, identity.py, feats_index.py, scope.py, cosmography.py,
# roll.py, scale_theories.py, chord_field.py

Every module below was read in full, top to bottom, in successive chunks (pipeline.py at 3,493
lines was read in ~500-line windows; the rest were read whole in one pass each). No sampling.

Before starting, the open work-order queue was checked (`workorders.open_orders()`, 458 open
orders) and `handoff/sweep56/AUDIT_batch03.md`, `AUDIT_batch06.md` and `AUDIT_batch11.md` were
read — all eight of this batch's modules were fully audited by sweep56 (2026-09-11, two days
before this sweep) across those three batches, with pipeline.py/identity.py/feats_index.py/
roll.py/scale_theories.py in batch03, scope.py/cosmography.py in batch06, and chord_field.py in
batch11. This audit re-verifies every one of those findings against the CURRENT source (not
against the prior report) and reports only what is actually still true today, plus anything
sweep56 did not catch. Findings that are unchanged from sweep56 are marked KNOWN with the prior
report cited rather than re-argued in full.

---

## pipeline.py (3,493 lines)

### DEFECT (NEW) — a comment describes a bug as live that the code beside it has already fixed, pipeline.py:711-719

```
711  # AND `subroom`, WHICH WAS THE ONE FIELD ADDED AFTER THIS MECHANISM WAS WRITTEN
712  # (sweep43-batch03). The judging loop treats it identically to `topic` -- `:1718` pops
713  # `subroom_rejected` the moment a subroom passes `subroom_ok`, exactly as `:1707` pops
714  # `topic_rejected` -- and `subroom_rejected` is already declared in `MERGED_ENTRY_FIELDS` at
715  # :554. It was simply never added here, so the pop stayed in memory and could not reach disk:
716  # the per-entry fold can SET a field and never CLEAR one on absence, which is the whole reason
717  # this map exists. The result is the precise fault the comment above describes, on the newest of
718  # the three fields -- a corrected subroom sitting on disk beside a `subroom_rejected` note
719  # asserting the opposite, with no way for any later run to retract it.
720  ENTRY_REJECTION_COMPANIONS = {"scale_note": "scale_note_rejected",
721                                "topic": "topic_rejected",
722                                "subroom": "subroom_rejected"}
```

The comment (711-719) asserts, in the present tense, that `subroom` was "simply never added" to
the map that lets `write_record` CLEAR a stale `subroom_rejected` note when a corrected `subroom`
supersedes it, and that this is causing live, ongoing damage right now ("a corrected subroom
sitting on disk beside a `subroom_rejected` note asserting the opposite, with no way for any
later run to retract it").

That is false of the code it sits directly above: `ENTRY_REJECTION_COMPANIONS` (the map the
comment says lacks the entry) already contains `"subroom": "subroom_rejected"` at line 722, and
the generic loop that applies it in `write_record` (pipeline.py:1286-1288, `for fld, rej in
ENTRY_REJECTION_COMPANIONS.items(): if fld in se and rej not in se: de.pop(rej, None)`) therefore
already clears a stale `subroom_rejected` for `subroom` exactly as it does for `topic` and
`scale_note`. The mechanism this comment says is broken is not broken — it was fixed, and the
comment describing the break was never updated to say so.

This is a different, and in one way worse, defect than sweep56 batch03's finding at this same
location. That prior report (KNOWN, see below) flagged only that the comment's three line-number
citations (`:1718`, `:1707`, `:554`) have drifted. This finding is that the comment's *substantive
claim* — not merely its citations — is now factually wrong about the code immediately following
it, in a project whose entire second-person voice in this exact block is "found and fixed, and
here is why." A maintainer who trusts this comment (as the file elsewhere earns trust for exactly
this kind of first-person incident narrative) would go looking for a bug that is not there, or
worse, "fix" a working mechanism a second time under the belief it was never fixed once.

**Confidence: DEFECT** (verified directly: `ENTRY_REJECTION_COMPANIONS` at pipeline.py:720-722
already contains the `subroom` entry the comment says is absent, and `write_record`'s fold at
pipeline.py:1283-1288 applies it generically to all three companion pairs, `subroom` included).

### KNOWN (sweep56 batch03) — same comment block, stale self-referential line citations, pipeline.py:711-715

The three line-number citations in the same comment quoted above (`:1718` for the subroom_rejected
pop, `:1707` for the topic_rejected pop, `:554` for the MERGED_ENTRY_FIELDS declaration) remain
wrong today, drifted further than when sweep56 batch03 reported this. Re-verified against the
current file: the `topic_rejected` pop is now at line **2258**, the `subroom_rejected` pop is now
at line **2269**, and `MERGED_ENTRY_FIELDS`'s `"subroom_rejected"` entry is now at line **690** —
none of the three cited numbers. Unfixed since sweep56 batch03 (2026-09-11); no new finding, cited
here only because it sits inside the same lines as the DEFECT above.

### KNOWN (sweep56 batch03) — stale cross-file citation, pipeline.py:732

```
730  # (`catalogue_web.py:244-246` and `:456-458`, and the same shape in
731  # `catalogue_aurora`, `catalogue_codex`, `ingest_doc` and `backfill`). So `sv` was always truthy
```

Still cites `catalogue_web.py:244-246` / `:456-458` for a claim whose real per-entry dict literals
sit roughly 60-110 lines further down in that file (per sweep56 batch03's verification). Unchanged
since 2026-09-11.

### KNOWN — `subroom_rejected` bare-slice truncation is FIXED (was a DEFECT in sweep56 batch03; now closed)

Sweep56 batch03 flagged `pipeline.py:2273` writing `batch[i]["subroom_rejected"] = sub[:120]` — a
bare, undisclosed slice, unlike its sibling `topic_rejected` which used `_stored_cut`. Verified
against the current file: this is now

```
2273    batch[i]["subroom_rejected"] = _stored_cut(sub, 120)
```

Fixed (matches the task brief's note that run #56 changed this). **Nothing found** — recorded here
only so the next sweep does not re-flag it as still open.

### KNOWN (sweep56 batch03, QUESTION) — undisclosed 240-char truncation fed to the entrypass classifier, pipeline.py:2153-2157

```
2153  # 380 -> 240 chars. Classification needs the opening clause ("X is a city in
2154  # ...", "a technique used by ..."), not the whole lead paragraph. Feats, when
2155  # present, are almost always stated early too.
2156  d = re.sub(r"\s+", " ", e.get("description", ""))[:240]
```

Still a bare slice with no disclosure to the model, unlike this file's `_budgeted()` convention
used everywhere else for exactly this situation. Unchanged since sweep56 batch03; still a QUESTION
rather than a DEFECT for the same reason given there (a missed feat here fails safe to
`unassayed`, and `valid_scale_note`'s gates prevent a wrong band rather than merely an absent one).

### KNOWN (sweep56 batch03, QUESTION, cosmetic) — "median" is the upper-median, pipeline.py:~2792-2796

```
2792  for d in sorted(groups):
2793      known = [lags[x] for x in groups[d] if isinstance(lags.get(x), (int, float))]
2794      log("    depth %d: %4d shelves, %d with a measurable lag%s"
2795          % (d, len(groups[d]), len(known),
2796             (", median %.0f yr" % sorted(known)[len(known) // 2]) if known else ""))
```

Unchanged; still mislabels the upper-median as "median" for an even-length list. Log-line only, no
stored artifact affected.

### KNOWN — open work order 0aceab8473e1 (SCHEMA_FIELD_UNREAD), still live, pipeline.py:1901/1908/690

`ENTRY_SCHEMA` requires the model to return `physiology` on every entry (properties at line 1901,
`required` list at line 1908), and `MERGED_ENTRY_FIELDS` (line 690) does not carry it. Verified
directly: the entrypass result loop (pipeline.py:2191-2274) reads `category`, `scale_note`,
`magnitude`, `topic` and `subroom` out of each model result but never once reads
`res.get("physiology")` — grep for `physiology` in pipeline.py returns only the schema
declaration and its own comment, no assignment site. The model is asked for the field on every one
of ~52,000 entries and the answer is discarded unconditionally. Matches the open order exactly;
not re-filed.

### KNOWN — open work order 55d0be76b99b (SYNTHESIS_CEILING_WITHOUT_A_BAND), phase_synthesis

Confirmed structurally present: `phase_synthesis` (pipeline.py:1660-1786) can write a
`ceiling_entity` alongside `provisional_magnitude: "unassayed"` whenever `valid_scale_note`
rejects the evidence text after a non-empty entity name was nominated (the `if b != "unassayed"
and not valid_scale_note(_ev): b = "unassayed"` branch at line ~1733, which does not clear
`ceiling_entity`). Matches the open order's description; not re-filed.

### Nothing else found

The write-record two-writer contract (`write_record`, `write_record_catalogue`,
`_merge_top_keys`, the compare-and-swap watermark logic), `ask`/`ask_pool_first`/
`_pool_answer_usable`'s cloud-then-local routing, `valid_scale_note`'s four gates,
`_unassayable_verdict_is_stale`'s re-admission logic, all eight `phase_*` functions' absent-vs-
corrupt handling for their JSON inputs, `gate_done`/`_landed`/`land_json`'s landed-verdict gating,
and `main()`'s phase-pointer, exit-code and stale-code-fingerprint handling were all read in full
and traced by hand. All match their own extensive in-file incident documentation, and no further
tautological checks, new fail-open paths, new silent swallows, new undisclosed caps, or new dead
code were found beyond what is listed above.

---

## identity.py (753 lines)

Read in full. Byte-for-byte consistent with sweep56 batch03's read (753 lines then and now).
**Nothing found.** `_is_continuity`'s three-test branching, `load()`'s cache-staleness repair and
its refusal to overwrite a populated inventory with an empty mine, the `_STALE_REMINED` once-per-
process guard, and `epoch_of`'s documented `strict=False` fail-open default are all unchanged and
still correctly wired/disclosed.

---

## feats_index.py (574 lines)

Read in full. Byte-for-byte consistent with sweep56 batch03's read (574 lines then and now).
**Nothing found as DEFECT.** `host_to_sources`'s raise-rather-than-cache-empty, `load_index`'s
unreadable/collided fault counting, `feats_for_source`'s within-source collision reporting, and
`audit()`'s file-count-vs-index-count reporting all still hold up against their own stated
rationale.

QUESTION (KNOWN, sweep56 batch03, unchanged, low confidence): `_norm(e.get("name"))` in
`feats_for_source` still folds a missing/`None` entry name to `""`, which would collide multiple
nameless entries under one key. Still speculative — nothing in this batch establishes a catalogue
entry that actually lacks a `name`.

---

## scope.py (473 lines)

Read in full. Matches sweep56 batch06's read (474 lines there; 473 here — the one-line difference
is not substantive, content is identical). No new findings.

### KNOWN (sweep56 batch06) — stale citation, scope.py:383

```
383  # (magnitude.py:942), which reads SCOPE.json directly and reimplements the live-probe fallback.
```

`magnitude.host_ceiling` is now at **magnitude.py:1751** (re-verified today; it was 1721 when
sweep56 batch06 checked it two days ago, 942 in the comment — the drift is growing as
magnitude.py continues to grow). Still open, still unfixed.

### KNOWN (sweep56 batch06) — stale citation, scope.py:466

```
466  # ceilings. Same doctrine as catalogue_codex.py:315-331.
```

Re-checked: `catalogue_codex.py:315-331` is still mid-way through an unrelated duplicate-element
routine; the actual "return 1 on a denied write" doctrine is now around `catalogue_codex.py:
496-507`. Unchanged, still unfixed.

### Nothing else found

`ProbeUnread`'s not-read/read-and-empty distinction, `build()`'s contract-versioned re-probe
selection, and `mutate()`'s compare-and-swap (digest-before-read, per-attempt temp names,
re-read-and-reapply) were all re-traced and are still correctly wired.

---

## cosmography.py (376 lines)

Read in full. Byte-for-byte consistent with sweep56 batch06's read (376 lines then and now).
**Nothing found.** `validate()`'s Kardashev-ceiling and size-class-ceiling checks are still real,
non-tautological comparisons; `KARDASHEV_MIX` still sums to 1.0 (re-checked: 0.90000 + 0.08500 +
0.01499 + 0.00001 = 1.0 exactly); `SIZE_CLASS_MAX_GALAXIES`'s POCKET/MINOR ceilings still hold
against the current `SIZE_CLASSES` multipliers.

---

## roll.py (319 lines)

Read in full. Byte-for-byte consistent with sweep56 batch03's read (319 lines then and now).
**Nothing found as DEFECT.** `mutate()`'s compare-and-swap and `update_rows`'s "found vs changed"
`seen` tracking remain correct.

QUESTION (KNOWN, sweep56 batch03, unchanged): `in_scope()` (lines 70-79) still fails OPEN on an
unreadable roll, explicitly documented and reasoned as a deliberate exception to house doctrine.

KNOWN — open work order c9146abf92df (ROLL_LOST_UPDATE_REMAINING_WRITERS): `exclude()`
(lines 214-296) is still the one roll-writer not yet ported onto `mutate()`'s compare-and-swap;
the function's own comment (lines 260-296) names the order by id and explains at length why it is
deliberately left for a coordinated two-file change with `checks_L4.py` rather than landed here.
Matches the open order; not re-filed.

---

## scale_theories.py (216 lines)

Read in full. Byte-for-byte consistent with sweep56 batch03's read (216 lines then and now).
**Nothing found.** Confirmed-dead code (`bulk_export_beta`, `growth_strike`,
`penetration_pressure`, `surviving_theory` — zero callers, verified again by grep), held rather
than deleted per owner ruling, exactly as documented. `surviving_theory()`'s arity assertion is
real, reachable logic (exactly one `"falsified": False` entry in `THEORIES` today) and would
correctly raise if that changed.

---

## chord_field.py (211 lines)

Read in full. Matches sweep56 batch11's read (210 lines there; 211 here, not substantive).
**Nothing found.** Pure physics/reference-data module, no I/O, no exception handling, no rosters.
`ADJUDICATIONS`' six `beta_bits` values (64, 96, 8, 0, 128, 32) still sum to 328 and still match
`derivation.py:148`'s claimed beta-bit values for A1-A6 (spot-checked again).

---

## Summary

| Module | NEW DEFECT | KNOWN (unfixed since sweep56) | KNOWN (fixed since sweep56) | QUESTION (KNOWN) |
|---|---|---|---|---|
| pipeline.py | 1 | 3 (2 stale citations + physiology/ceiling orders) | 1 (subroom_rejected cut) | 2 |
| identity.py | 0 | 0 | 0 | 0 |
| feats_index.py | 0 | 0 | 0 | 1 |
| scope.py | 0 | 2 | 0 | 0 |
| cosmography.py | 0 | 0 | 0 | 0 |
| roll.py | 0 | 1 | 0 | 1 |
| scale_theories.py | 0 | 0 | 0 | 0 |
| chord_field.py | 0 | 0 | 0 | 0 |
| **Total** | **1** | **6** | **1** | **4** |

The one NEW finding (pipeline.py:711-719) is a documentation defect: a comment describing a bug
as currently live when the map it is complaining about, three lines below it, already contains
the fix. No new correctness defect, silent failure, fail-open-where-should-be-closed path, or
undisclosed stored-value truncation was found in any of the eight modules beyond what sweep56
already reported two days ago and what remains open in the work-order queue.
