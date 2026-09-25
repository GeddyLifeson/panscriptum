# sweep63 batch 03 audit

Scope (read start to finish, in chunks, no sampling), all under `src/`:

- `pipeline.py` (3,656 lines) — read in full (5 chunks: 1-700, 700-1400, 1400-2100, 2100-2600,
  2600-3150, 3150-3656)
- `weave_index.py` (730 lines) — read in full, one pass
- `endpoint.py` (654 lines) — read in full, one pass
- `backfill.py` (494 lines) — read in full, one pass
- `retry_synthesis.py` (379 lines) — read in full, one pass
- `catalogue_aurora.py` (328 lines) — read in full, one pass
- `halo.py` (219 lines) — read in full, one pass
- `repass_bands.py` (214 lines) — read in full, one pass

Total 6,674 lines, all read. Read-only throughout: nothing under `src/`, `data/`, `state/` was
edited (the one permitted `sweep_plan.record` call is not an edit to any of those).

CLAUDE.md skimmed first for doctrine (Hard Rule -1 escalation/halt, Hard Rule 0 no caps, fail
closed, "a check that cannot fail looks exactly like a check that passed").

## Prior audit cross-check

`handoff/sweep61/` was grepped for these eight module names. Four prior batches cover them:
`AUDIT_batch03.md` (pipeline.py, weave_index.py — no findings except the physiology bug below),
`AUDIT_batch06.md` (endpoint.py — one observation, not filed as a finding, still true and not
re-filed here), `AUDIT_batch07.md` (backfill.py, retry_synthesis.py, catalogue_aurora.py,
repass_bands.py — no findings in these four specifically), `AUDIT_batch12.md` (halo.py — no
findings). All prior reasoning was checked against the current source rather than re-derived;
nothing pre-recorded as fixed is re-reported here.

## Findings

### 1. VERIFIED — `pipeline.py`, `phase_entrypass`: an out-of-range or wrong-typed `category`
answer is silently discarded, with no rejection marker and no count, and the entry is still
marked `catalogued: True` — permanently settled on a category that was never corrected.

`ENTRY_SCHEMA` (pipeline.py:2029-2067) declares `category` as a bare `{"type": "integer"}` —
unlike its two siblings in the same object, `topic` and `subroom`, both of which carry an
`"enum"` constraint plus an explicit `"unclassified"`/`"none"` fallback value and a companion
`*_rejected` field (`topic_rejected`, `subroom_rejected`) that the corpus can be queried against.
`category` has none of that. The result-processing loop is:

```python
ci = res.get("category")
if isinstance(ci, int) and 1 <= ci <= len(CATEGORIES):
    batch[i]["category"] = CATEGORIES[ci - 1]
...
batch[i]["catalogued"] = True
```
(pipeline.py:2355-2357, 2428)

If `ci` is anything else — `0`, `9`, `-1`, a float, a numeral-as-string, or absent — the `if`
simply does not fire, the entry's existing `category` (whatever the original crawl assigned,
which `ENTRY_SYSTEM`'s own prompt text says is wrong often enough to be "the commonest error to
fix") is left untouched, and nothing records that a correction was attempted and rejected.
`catalogued = True` is then set unconditionally two lines later regardless of whether the
category branch fired, so `entry_settled()`/`batch_settled()` count the entry as done and it is
never re-sent to the model.

This is the identical failure shape `pipeline.py`'s own comments call out and fix twice over in
the same function, for `topic` ("AN UNREADABLE TOPIC IS RECORDED, NOT DROPPED... A sentinel can
be counted; an absent key cannot. (BUGS m14.)", pipeline.py:2401-2416) and for `subroom`
(pipeline.py:2417-2427) — but the fix was never applied to `category`, the field the fix's own
justifying comment ("BUGS m14") was originally about. There is no `category_rejected` field
anywhere in the module (`MERGED_ENTRY_FIELDS`, `ENTRY_REJECTION_COMPANIONS`, and a grep of
`src/pipeline.py` for `category_rejected` all confirm zero occurrences), so even a future fix to
the read side would have nowhere on disk to land the rejected value.

This is more exposed than it would have been a year ago, not less: `phase_entrypass` now routes
every batch through `ask_pool_first` (cloud pool first, local Ollama second), and
`_pool_answer_usable`'s own docstring explains at length that the cloud arm is NOT schema-
constrained the way local Ollama is ("Cloud endpoints do not all offer that, so the schema is
carried in the prompt... a cloud model can return perfectly valid JSON of entirely the wrong
shape"). `_pool_answer_usable` only checks that every `required` key is *present*, never that its
value is well-typed or in range, so a cloud answer with `"category": "3"` (string) or
`"category": 12` passes that gate untouched and reaches this loop. Local Ollama's JSON-schema
constrained decoding cannot be relied on to keep `category` in range either, because the schema
itself sets no `minimum`/`maximum`/`enum` on it — only the prompt text says "1-8", and a model is
free to ignore prose the schema does not enforce.

Verified by: reading the schema (no enum/bounds on `category`, unlike `topic`/`subroom` four
lines below it), the full result-processing loop (no `category_rejected` write path, no
`silence.note` call on the rejection branch, `catalogued = True` unconditional), and
`MERGED_ENTRY_FIELDS`/`ENTRY_REJECTION_COMPANIONS` (no `category_rejected` entry in either, so
disk has no field to receive one even if the read side were fixed). Not previously reported:
sweep61 batch03 read this exact function and filed only the `physiology` finding (below); this
gap in the same loop was not named there.

Severity: data-quality / visibility, not corruption — a wrong category is retained (never
manufactured from nothing), but silently and permanently, on a field the correction pass exists
specifically to fix, and with none of the auditability its two sibling fields were given for the
identical risk.

Suggested fix (not applied — read-only batch): give `category` the same treatment as `topic`/
`subroom` — record a `category_rejected` value when `ci` fails the range/type check, add
`category_rejected` to `MERGED_ENTRY_FIELDS` and to `ENTRY_REJECTION_COMPANIONS` (companion of
`category`), and count/log the rejection the way the topic branch already does, so the rate is
visible rather than silently absorbed.

## Carried-over open item (not re-filed as a new finding)

`pipeline.py`, `phase_entrypass`: the model-returned `physiology` field is still requested
(`ENTRY_SYSTEM`, pipeline.py:1959-1964), still `required` in `ENTRY_SCHEMA`
(pipeline.py:2055, 2061-2062), and is still never assigned onto `batch[i]` anywhere in the
results-processing loop (pipeline.py:2345-2428), and is still absent from `MERGED_ENTRY_FIELDS`
(pipeline.py:841-846). This is exactly the VERIFIED finding sweep61 batch03 filed in full detail
(see `handoff/sweep61/AUDIT_batch03.md` §1) — re-verified here by grepping `src/pipeline.py` for
`physiology` (four hits: the prompt text, the schema, and the schema's own required-list; zero
assignment sites) and confirmed it remains unfixed as of this sweep. Not re-derived at length
per the brief's instruction not to repeat resolved items — this one is simply not yet resolved,
so it is flagged here by reference rather than left implicitly "checked and clean."

## Everything else

The eight modules in this batch are, without exception, unusually heavily self-documented —
nearly every non-trivial branch carries a comment naming the incident, the order id, and the fix,
often with a measured count from the live corpus. Read against that standard, both `weave_index.py`
and `halo.py` (matching sweep61 batch03's and batch12's own verdicts) show no new tautologies,
fail-open guards, unmarked truncations, or false doc/code mismatches. `endpoint.py`,
`backfill.py`, `retry_synthesis.py`, `catalogue_aurora.py` and `repass_bands.py` were checked line
by line against their own extensive incident comments and against the two-writer contract
(`write_record` / `write_record_catalogue`) they all call through, and every write site gates on
the landed verdict as documented; no unguarded write, no bare `except: pass` swallowing a real
fault, and no cap/truncation without a disclosed count was found beyond what the code's own
comments already record as fixed.

No fail-open guards, no lifted/openable `prose_enabled`/`step4_enabled` gates, and no regex/escape
corruption were found in any of the eight modules (all eight carry the same `_BAD_CHARS` self-check
at import time, and none of the seven that define their own regexes showed a pattern that looked
mis-escaped against its stated intent).

## Questions (not findings)

1. `retry_synthesis.py`, `main()`: the run path's exit code (`return 0 if landed else 1`,
   retry_synthesis.py:375) tracks only whether the last *save* to `SYNTHESIS_RETRY.json` landed,
   not whether every source was actually rescued — a run in which several sources print
   "STILL FAILING" (the model genuinely returned nothing usable) but every save lands still exits
   0. This may be intentional (matching `phase_synthesis`'s own treatment of a per-source model
   failure as routine and non-fatal, to be picked up next run), and the "STILL FAILING" line is
   printed for each such source, so nothing is silent — but it means a wrapper script checking
   `$?` alone cannot tell "0 to do" from "several still failing, but the file save you don't care
   about landed." Flagged as a question, not a defect, since the printed line already carries the
   information a human reader needs.

## Coverage

Recorded via `sweep_plan.record('run63', [...], batch=3)` for all eight modules listed above.
