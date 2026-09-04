# SWEEP 43 — BATCH 03 AUDIT

Files read in full: `src/pipeline.py` (2,814 lines), `src/estate.py`, `src/address_space.py`,
`src/prose_gate.py`, `src/catalogue_models.py`, `src/roll.py`, `src/ledger.py`.

All seven files carry a heavy density of prior-sweep commentary describing bugs already found
and fixed. This audit looked past that record for defects that are still live. Two verified
findings survived; both are in `pipeline.py`'s two-writer record contract. `estate.py`,
`address_space.py`, `prose_gate.py`, `catalogue_models.py`, `roll.py` and `ledger.py` are
reported CLEAN for this pass — no new defect could be verified against the source in any of
them beyond what their own comments already document as fixed.

---

## src/pipeline.py

### FINDING 1 — MAJOR: `write_record`'s top-level-key fold reasserts a stale in-memory
snapshot on every call, not only the first, silently reverting concurrent writes by
`write_record_catalogue`

**file:line:** `src/pipeline.py:769-810` (`_merge_top_keys`), called unconditionally from
`write_record` at `src/pipeline.py:909`.

```python
def _merge_top_keys(disk, rec, label):
    ...
    kept = []
    for key, val in rec.items():
        if key == "entries":
            continue
        if val is None and disk.get(key) is not None:
            kept.append(key)          # unauthored by this caller; the disk value stands
            continue
        disk[key] = val
```

**What actually happens.** The fold's whole safety argument (stated in its own docstring and in
`write_record_catalogue`'s) is: *"did not compute this field" (None) and "means to clear this
field" are different acts... `None` means unauthored.* That argument is sound for a value built
fresh inside the current call. It is not sound here, because `rec` is not built fresh per call —
it is the single in-memory record object `records()` returned once at the top of the *phase*,
reused across every write that phase makes for that source. In `phase_entrypass`
(`src/pipeline.py:1562-1773`), `allrecs = records()` is loaded exactly once
(`src/pipeline.py:1565`), and the loop below calls `write_record(path, rec)` once per
`ENTRY_BATCH` (20 entries) — for `marvel.json`'s 30,207 entries that is ~1,500 separate
`write_record` calls against the same `rec` object, over however long the phase takes to reach
and finish that source (the module's own docstrings describe multi-day, unattended runs).

Every one of those ~1,500 calls re-runs `_merge_top_keys(disk, rec, ...)`, and for every
non-`entries` top-level key that was non-`None` at *load time* (`synthesis`, `ceiling_entity`
inside it, `purged_roster`, anything else `write_record_catalogue`/`ingest_doc` authored before
this phase started), the loop unconditionally does `disk[key] = val` — stamping the load-time
value back over whatever is currently on disk, on every single call, for as long as the phase
holds that `rec`. If `write_record_catalogue` (run by the cataloguer, documented elsewhere in
this same file as running concurrently with the pipeline) updates `synthesis`,
`ceiling_entity`, or `purged_roster` for that source at any point after `phase_entrypass` loaded
its snapshot, the very next `write_record` call for that source — batch 2, 3, ... 1,500 — will
silently revert it back to the stale value, without a `kept` log line, because the key is
non-`None` and therefore reads as "authored."

**Why it matters.** This is exactly the incident class the file's own docstrings extensively
document and treat as the project's signature defect (`write_record_catalogue`'s docstring:
"31 of 216 records carry a null synthesis... It does not self-heal"). That earlier bug was fixed
for `write_record_catalogue`'s handling of `None`. This is the same failure shape surviving in
`write_record`'s twin function, via a different mechanism: not a `None` clobbering a value, but
an *stale-but-present* value clobbering a fresh one, repeatedly, for the entire lifetime of a
long-running phase's held snapshot. The fold cannot tell "I computed this just now" from "this
was sitting in the record when I loaded it hours ago and I never touched it" — presence alone is
not proof of authorship when the caller object outlives a single unit of work.

**Suggested remedy (OWNER/RUN judgment, not mechanical):** the fold needs to distinguish
"keys this specific write actually intends to author" from "keys merely present because the
whole record was loaded once." One option: track which top-level keys a phase actually assigns
during this call (e.g. `phase_synthesis` only ever assigns `synthesis`) and pass an explicit
allow-list into the fold rather than folding every non-`None` key in `rec`. This is a design
change to the two-writer contract, not a mechanical patch — filed as RUN, not LOCAL.

---

### FINDING 2 — MAJOR: `subroom_rejected` is missing from `ENTRY_REJECTION_COMPANIONS`, so a
corrected `subroom` judgment cannot clear its own stale rejection note on disk

**file:line:** `src/pipeline.py:572-573` (the table itself); the field pair it is missing is
declared together at `src/pipeline.py:553-556` (`MERGED_ENTRY_FIELDS`, which *does* include both
`"subroom"` and `"subroom_rejected"`); the write-side companion-clear that should use it is at
`src/pipeline.py:893-898`; the read-side pop this is supposed to mirror is at
`src/pipeline.py:1716-1720`.

```python
ENTRY_REJECTION_COMPANIONS = {"scale_note": "scale_note_rejected",
                              "topic": "topic_rejected"}
```

**What actually happens.** `phase_entrypass` judges `subroom` exactly the same way it judges
`topic` — with a rejection note kept when the model's answer isn't legal for the entry's room,
and popped when a later pass corrects it:

```python
sub = (res.get("subroom") or "").strip()
if sub and subroom_ok(batch[i].get("category"), sub):
    batch[i]["subroom"] = sub
    batch[i].pop("subroom_rejected", None)   # <- in-memory clear, correctly done
else:
    batch[i]["subroom"] = SUBROOM_UNCLASSIFIED if sub else SUBROOM_NONE
    if sub:
        batch[i]["subroom_rejected"] = sub[:120]
```

That in-memory pop is correct. But `write_record`'s per-entry fold onto the disk copy is
presence-gated and, by its own documented design, "can SET a field and can never CLEAR one" —
which is exactly why `ENTRY_REJECTION_COMPANIONS` exists: to let two *specific* qualified
fields (`scale_note`, `topic`) clear their rejection companion on disk when the qualified field
is present and the rejection is deliberately absent from the fresh judgment. `subroom` was added
as a third axis on 2026-09-01 (`src/pipeline.py:127-166`), well after
`ENTRY_REJECTION_COMPANIONS` was written (order `2f248e854b58`) to fix precisely this problem
for the first two fields — and `subroom`/`subroom_rejected` was never added to the table.

The result: once a `subroom_rejected` note lands on a disk entry, a later pass that corrects the
subroom to a legal value pops `subroom_rejected` from its own in-memory judgment, but
`write_record`'s fold only ever *sets* `de["subroom"]` from `se["subroom"]` (since `"subroom" in
se`) — `de["subroom_rejected"]` is left untouched on disk forever, because it is absent from
`se` and the fold cannot clear on absence, and no companion rule tells it to. The entry is left
holding a corrected `subroom` sitting beside a `subroom_rejected` note that describes a verdict
that no longer stands — the exact "two contradictory claims about one judgment" failure the
docstring immediately above `ENTRY_REJECTION_COMPANIONS` (`src/pipeline.py:560-571`) says was
the whole reason the mechanism was built, reproduced for the one field it forgot to cover.

**Why it matters.** Silent, permanent, and growing every run: any subroom correction is
indistinguishable on disk from an uncorrected rejection, which pollutes exactly the shelving
data (`Vessels & Things`'s finer shelves) that `SUBROOMS`'s own header calls out as the reason
the whole axis was added — "42,485 entries, half of them typed literally `Item`."

**Suggested remedy (LOCAL — mechanical, one-line):**
```python
ENTRY_REJECTION_COMPANIONS = {"scale_note": "scale_note_rejected",
                              "topic": "topic_rejected",
                              "subroom": "subroom_rejected"}
```

---

## src/estate.py — CLEAN

Read in full. `inspect()`'s extension-routing (`_effective_ext`), the transient/zero-byte
handling, the `.jsonl` torn-line check, `charter()`'s table-driven errata tests, `written()`'s
and `terminal()`'s row-emission guarantees, and `external()`'s four-way condition split were all
traced against their stated behaviour and found to do what they claim. No cap violations, no
detectors that cannot fire, no contradicted docstrings found.

## src/address_space.py — CLEAN

Read in full. Verified `WIDTHS`/`TOTAL_BITS` are genuinely derived (not hand-copied), `pack()`
raises rather than truncates, `assign()`'s hashed-field offsets are computed from `WIDTHS` with
the legacy floor correctly preventing today's addresses from moving, and `main()`'s
`SHELFMARKS.json` write is properly gated on `silence.write_json`'s verdict. No defect found.

## src/prose_gate.py — CLEAN

Read in full. All four in-module layers (`gate_open`/`step4_gate_open` fail closed on every
unreadable/malformed input; `floor_ok` refuses a floor at or outside `(0, 1]`; `evidence_ok`
fails closed on an unmeasured source; `section_shortfall`/`assert_block_complete` charge both
ghost and extra (invented) entries into the denominator so neither can reach 100% by omission or
padding; `unearned_instrument`'s `cited_names_for` fails closed to "nothing is cited" on any
read error) were traced and each behaves as documented. `prose_enabled`/`step4_enabled` were not
evaluated for whether they *should* open — per instructions, that is an owner-held gate and out
of scope for this audit regardless of how the code reads.

## src/catalogue_models.py — CLEAN

Read in full. The `LISTED`/`EMPTY_LIST`/`UNREACHABLE`/`UNCONFIGURED` four-way outcome, the
`live`/`stale`/`unverified` accounting, and the `LAST_WRITE_LANDED` gate on `main()`'s return
code were all verified against the surrounding narrative comments and found consistent. No Hard
Rule 0 caps found (`available_sample` and the printed alternatives list are both confirmed
uncapped).

## src/roll.py — CLEAN

Read in full. `mutate()`'s compare-and-swap (digest taken before read, re-applied on retry
rather than retried verbatim), `exclude()`'s required-note and caller-supplied-rows write
routing, and `in_scope()`'s fail-open-on-unreadable-roll behaviour (explicitly and correctly the
opposite of this project's usual fail-closed convention, with the reasoning given) were all
traced and found sound.

## src/ledger.py — CLEAN

Read in full, small module (173 lines). `assay_to_standards`'s M10 ceiling handling (anchored at
M10's own floor rather than shifted to M9's, matching its own comment) was checked arithmetically
and is correct. `currency_status` vs. bare `to_standards`/`from_standards` returning `None` for
both "unlisted" and "deliberately non-convertible" is a documented, deliberate simplification,
not a defect.

---

## QUESTIONS FOR OWNER

None. Both findings above are code-behaviour questions with a definite answer (traced against
the source, not curatorial judgment calls), so they are filed as work orders rather than raised
here.
