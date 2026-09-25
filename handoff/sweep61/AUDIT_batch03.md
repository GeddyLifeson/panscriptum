# sweep61 batch 03 audit

Scope, read start to finish, no sampling:

- `src/pipeline.py` (3656 lines) -- read in full (6 chunks)
- `src/weave_index.py` (730 lines) -- read in full
- `src/feats_index.py` (628 lines) -- read in full
- `src/reference.py` (497 lines) -- read in full
- `src/recover_folder_records.py` (380 lines) -- read in full
- `src/wh40k.py` (350 lines) -- read in full
- `src/cachekey.py` (217 lines) -- read in full
- `src/module_index.py` (192 lines) -- read in full

All eight files in the batch are documented start to finish. Per the brief, this codebase is
unusually self-auditing -- most historical defects are described at length in the surrounding
comments, with the fix already landed and the reasoning kept as a permanent record. Anything the
code's own comments already record as known and handled is not re-reported here.

## Findings

### 1. VERIFIED -- `pipeline.py`, `phase_entrypass`: the model-returned `physiology` field is
requested, required by schema, and then silently discarded; it never reaches a record.

`ENTRY_SYSTEM` (pipeline.py:1959-1964) instructs the model to return a `physiology` field for
every Peoples & Species entry ("what they are made of, how long they live, whether they eat,
breathe, sleep, age or reproduce, and what kills them"), and the docstring at the schema
(pipeline.py:2049-2054) explains at length why the field was added: "the field the library did
not have... asked only of a people, because that is where it is answerable from a catalogue
description." `ENTRY_SCHEMA` marks it `required` (pipeline.py:2055, 2061-2062), so every single
entrypass call -- the codebase's own comments elsewhere stress this runs across roughly 52,000+
entries and that "every wasted word is multiplied" by that count -- pays real output-token cost
for the model to answer it.

But in the results-processing loop that reads `got.get("results", [])` (pipeline.py:2345-2428),
every other schema field is extracted and written onto `batch[i]` --
`category` (2357), `scale_note` (2367/2369), `magnitude` (2399), `topic` (2411/2414/2416),
`subroom` (2422/2425/2427), `catalogued` (2428) -- but there is no `batch[i]["physiology"] = ...`
anywhere. `res.get("physiology")` is never read. The value the model was required to produce is
computed, paid for, and then dropped on the floor.

It is not merely mishandled by the merge layer either: `physiology` is absent from
`MERGED_ENTRY_FIELDS` (pipeline.py:841-846), the allow-list `write_record`'s and
`write_record_catalogue`'s per-entry folds both consult, so even if a future fix set
`batch[i]["physiology"]`, it would not survive a merge onto an existing disk entry without also
being added there.

Verified two ways: (1) read every line of the results-processing loop in `phase_entrypass` and
confirmed no assignment target exists for the key; (2) `grep -rn physiology src/` from the repo
root returns matches only in `pipeline.py` (the prompt text, the schema, and its own docstring)
and no other file in `src/` -- so nothing downstream ever reads a `physiology` value out of
`data/records/*.json` either, confirming the field cannot be reaching disk by another path.

This is a real bug, not a design choice: the docstring at the schema explicitly frames the field
as something the corpus was missing and needed, which is inconsistent with discarding every
answer to it.

## Summary of findings by kind

- Real bugs (category 4): 1 VERIFIED (`pipeline.py` physiology field discarded)
- Tautologies / fail-open guards / caps-that-hide-data / false comments / dead code: none found
  beyond what the code's own comments already record as fixed.

No other findings in this batch met the bar for reporting (verified against source, not already
documented as handled). The two smallest modules (`cachekey.py`, `module_index.py`) and the three
mid-sized ones (`recover_folder_records.py`, `wh40k.py`, `reference.py`) were read in full and
contain no unreported issues under the priorities in the brief.
