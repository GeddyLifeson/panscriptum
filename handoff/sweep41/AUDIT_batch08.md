# Sweep 41 — Batch 08 audit

Modules read IN FULL: `src/magnitude.py` (1813), `src/chain.py` (837), `src/catalogue_web.py`
(633), `src/weave_index.py` (516), `src/catalogue_codex.py` (404), `src/grounding.py` (334),
`src/resync_roll.py` (295), `src/chord_field.py` (210). 5,042 lines, zero skipped, zero sampled.

No edits made to any file in `src/` (audit only). No `drill.py`, no `chain.py`, run against the
live tree.

## Findings filed

| id | code | handler | severity | one-line |
|---|---|---|---|---|
| `4da7238657a3` | MAGNITUDE_RUNBATCH_TALLY_HIDES_DEFERRED | SESSION | MINOR | `run_batch()`'s progress tally conflates real "band-only" findings with DEFERRED (retriable transport failures) under one bucket, even though `settled()` three screens up already knows how to tell them apart. |
| `18187cb13de7` | MAGNITUDE_ASSAY_ENTITY_MISSING_HOST_FIELD | SESSION | MINOR | Two of `assay_entity()`'s terminal return paths ("no axis cleared its gate", "sheet saturated") omit the `host` field every sibling return carries; verified no current consumer breaks (all three readers of ASSAYS.json derive host from the dict key, not the row), but it's a latent trap for a future one. |
| `5f1dc97d5216` | WEAVE_INDEX_RECORDS_SIG_DIR_UNREADABLE_READS_AS_EMPTY | OWNER | MAJOR | QUESTION: `_records_sig()`'s per-file OSError handler was hardened to refuse a signature on a stat failure (order f70e87058f66); the top-level `os.scandir(RECORDS)` OSError handler was not, and silently returns the CLEAN, cacheable "corpus is empty" signature `(0,0)` on a directory-level read failure — so a transient lock during exactly a `--write` run could overwrite `ENTITY_INDEX.json`/`WEAVE_CANDIDATES.json` with near-empty files. Both readings given; owner's call on whether this is the accepted "preserved" behaviour or a real gap. |

## Detail

### magnitude.py (1813 lines) — the Assay engine

This is by far the densest module in the batch: 25+ numbered/named orders already landed in it,
each with a full postmortem comment. The five guards (VERBATIM, RELEVANCE, SUBJECT, SATURATION,
QUANTITY) described in the module docstring were checked one at a time against their call sites:

- **Guard 1 (verbatim / `_resolve_citation`)**: exact-equality-first, then number-anchored,
  then containment/overlap with a length floor — checked on both the one-shot (`verify`) and
  split (`_split_gate`) paths, with `numbered=False` on split correctly making containment
  one-directional. No gap found.
- **Guard 2 (relevance / `AXIS_RE`)**: applied identically on both paths. No gap found.
- **Guard 3 (subject / `subject_refusal`)**: all four branches (passive-with-agent,
  passive-without-agent, handoff, rival-leads-verb) read against the entity's own name via
  `entity_forms`/`_is_entity`; called from `verify`, `_split_gate`, and `quantity_scores`. No
  gap found — this is the guard the module's own history says was missing twice before and it
  is now asked everywhere a score can reach publication.
- **Guard 4 (saturation)**: `len(nums) >= 6 and min(nums) >= 9.0` — straightforward, no bypass.
- **Guard 5 (quantity)**: `quantity_scores` now asks guard 3 before a measured reading can
  overwrite an axis; rejections are returned rather than dropped. No gap found.
- Checked `_status_score`'s three-sentinel mapping (NONE/UNESTIMABLE/INAPPLICABLE) is applied
  identically on all three call sites (`verify`, `_split_assay._one_axis`, `_split_gate`) per
  order d2f89bfe967d's fix. Consistent.
- Checked every return path out of `assay_entity` for field-shape consistency against the task's
  "return path missing a field its siblings carry" hint — found the two `host`-omitting paths
  above (filed, low actual impact, verified).
- Checked `run_batch`'s tally against `settled()`'s three-way classification per the task's
  "binary tally hides a third outcome" hint — found the conflation above (filed).
- Considered whether `isinstance(raw, (int, float))` in `verify()` could let a JSON boolean
  (`True`/`False` are `int` subclasses in Python) slip through as a fabricated 1.0/0.0 score
  instead of failing to UNESTIMABLE. **Decided not to file**: even if a transport returned a
  boolean for `score` (no evidence any provider does — schema declares `["number","string"]`),
  the axis would still need a valid, guard-1/2/3-passing citation in `feat` to be credited, so
  this could at most mis-score an axis that already had real evidence, not manufacture evidence
  from nothing. Too speculative to file without a reproduction.
- `calibrate()`'s resumable-checkpoint logic, the `_land`/`_published` helpers, and the
  band-vs-verdict distinction (order f4171126348f) were all read and are internally consistent.
- `queue()`, `host_ceiling()`, `settled()`, `compose()` (round-robin budget allocation) — read in
  full, no new findings.

### chain.py (837 lines) — the contest graph

Not re-reporting `refresh_continuity()` (added today) or the `sig is not None`-style guards
already in place. Read `harvest()`, `write_result()`, `extract()`, `adjudicate_mutuals()`,
`entity_index()`, `fit()`, `main()` in full.

- Noted, **did not file**: `harvest()`'s `_corpus_root_state()` protects only the two TOP-LEVEL
  roots (`data/readfeats`, `data/feats`) against an unreadable-directory-reads-as-deleted
  failure. The subsequent `glob.glob(..., recursive=True)` walks every subdirectory beneath
  those roots, and CPython's `glob` module silently swallows `OSError` per-subdirectory during a
  recursive walk (verified against stdlib `glob._iterdir`'s `try/except OSError: return`) — so a
  permission blip on one host directory several levels down would silently return fewer files
  than actually exist, and `harvest()`'s prune loop (`for rel in [... if k not in live ...]`)
  would then delete that host's cached rows from `chain_harvest_idx.json` as though the files
  were genuinely gone. This is the same *class* of bug as the filed `weave_index.py` finding
  (directory-level failure not given the same protection as file-level failure), one layer
  deeper in the tree. Not filed because I have not reproduced or measured it in this repo (no
  evidence a Norton lock has ever actually hit a subdirectory here, unlike the top-level case
  `_corpus_root_state`'s own docstring was written to address), and the consequence is milder
  than the weave_index case — no destructive `--write` of a shared, widely-read artifact; only a
  temporary loss of one host's incremental-harvest cache, which self-heals the next time that
  host's files are listed successfully (they'd simply be re-mined, at some I/O cost). Flagging
  here for the record rather than filing a speculative order.
- `write_result`'s single-writer contract, the `unmatched`/`unanswered` uncapped provenance
  fields, `adjudicate_mutuals`'s epoch-splitting logic (self-split / half-dated / unprobed /
  split / kept, all five outcomes distinct and none conflated) — read in full, no new findings.
  This function in particular is a good example of the *opposite* of a binary tally: five
  distinct outcomes, each counted and printed separately.

### catalogue_web.py (633 lines) — the wiki cataloguer

Specifically checked the "stopped at MANAGER rung for nulling synthesis blocks, 26 sources in 24
hours" incident this batch was briefed on. Traced it fully: `catalogue()` and
`catalogue_composite()` both unconditionally build `"synthesis": None` (correctly — a wiki lead
paragraph is not an Assay), and the only write path is
`_P.write_record_catalogue(record_path(name, RECORDS), record)` in `pipeline.py` (not in this
batch, but load-bearing here so traced anyway). Confirmed `write_record_catalogue`'s docstring
and code (orders 7292a1c3d84b / 3c7c8a6e9102) already fix this exactly: a key **absent** from
the caller's record OR present as **`None`** now falls back to the disk value instead of
overwriting it, so `catalogue_web.py`'s `synthesis: None` no longer erases a disk-side
`ceiling_entity`/`provisional_magnitude`. **The incident is closed upstream; not re-filed.**
Checked there is no second, bypassing write path in this module — there is only the one call
site. Read `MAX_PER_SOURCE`/`MAX_PER_CATEGORY` Hard-Rule-0 removal, `_singular()`, `save_roll()`
(compare-and-swap via `roll.update_rows`), `main()`'s `--shortfall`/`--recatalogue` selection
logic — no new findings.

### weave_index.py (516 lines) — entity index / collision detector

Not re-reporting the `sig is not None` guard added to `designations()` today. Read `designations`,
`continuity_of`, `norm`, `_records_sig`, `load_records`, `build`, `main` in full. Found and filed
the directory-level-OSError-reads-as-empty gap above — this is the module's one real finding, and
it sits in exactly the pattern the batch brief asked about ("a cache keyed on a signature that
means this pass was not clean is a cache that serves bad data forever"), except inverted: the
signature here means "clean" when it should mean "not clean." The per-entry version of this exact
failure was already fixed in the same function; the directory-level version was not.

### catalogue_codex.py (404 lines) — the owner's homebrew codex

Not re-reporting the "two dead mutations" fix from today. Read `parse_codex`, `load_register_index`
(the every-item-under-a-key fix for order 096f6efc33d2), `main`'s section-binding
(exact-then-ambiguous-refuses, order 5da00dda2c8e), the roll compare-and-swap, and the exit-code
propagation (order 0e8ef2e30f2b) in full. This module is thoroughly hardened; no new findings.
Considered `parse_codex()`'s unguarded `text.index("## PART TWO")` (raises uncaught `ValueError` if
the owner's codex file's structure ever changes) — decided not to file: this is a hard dependency
on a fixed, owner-authored file format that the module's whole design already assumes, not a
maintenance-detectable defect class.

### grounding.py (334 lines) — hyperverse-grounding classifier

Read in full. No persistent cache in this module (unlike weave_index/chain), so the batch brief's
cache-staleness concern doesn't apply here. Checked the UNGROUNDED early-return in
`classify_source()` against the SCORED return for field-shape parity (same hint as magnitude.py):
the UNGROUNDED branch omits `assayable`/`reasoning` that the scored branch includes. **Decided
not to file**: grepped every reader of `data/GROUNDINGS.json` (`navtree.py`, `pipeline.py`,
`tiers.py`) for `.get("assayable")`/`["assayable"]`/`.get("reasoning")`/`["reasoning"]` — zero
hits. No consumer touches either field today, so this shape mismatch has no current effect;
noting it here rather than filing a work order with no verified consequence. `classify_text`'s
Hard-Rule-0 full-field-denominator fix and `classify_source`'s uncapped-origin-entries fix were
both read and confirmed already landed and correct.

### resync_roll.py (295 lines) — roll/record reconciliation

Not re-reporting the pre-fix-snapshot fix (`have_on_disk`) landed today. Read the whole file:
argparse hard-error on unrecognised flags (order eb4a87793c19), the `by_source` dupe/sort logic,
the label-repair-independent-of-count-move fix (order 2ab24aeb63f7), the compare-and-swap `_apply`
closure with its bare-`!=` exclusion guard (kept unfolded deliberately so a drill net can read the
parse tree), and the exit-code propagation (order 8605c2ed6061). No new findings — this module is
thoroughly self-documented and every failure mode I could construct is already named and handled
in its own comments.

### chord_field.py (210 lines) — the Chord-as-field physics adjudication

Read in full. Pure lore/physics-constants module: no file I/O, no cache, no persistence, no
guards, no return-path branching to speak of — six `ADJUDICATIONS` dict entries plus four small
pure functions (`landauer_floor`, `recoil_momentum`, `recoil_velocity`,
`critical_power_self_focus`). Spot-checked the physics formulas against their named real-world
sources (Landauer's principle, p=E/c, Marburger self-focusing formula) — all correctly stated. No
findings; this module is out of scope for the batch's stated concerns (no assay numbers, no
synthesis/scale blocks, no cache, no repair-reporting) and none were found regardless.

## Summary for the return line

- Lines read per module: magnitude.py 1813, chain.py 837, catalogue_web.py 633, weave_index.py
  516, catalogue_codex.py 404, grounding.py 334, resync_roll.py 295, chord_field.py 210 — 5,042
  total, all in full.
- Findings filed: 2 MINOR (both magnitude.py, both SESSION), 1 MAJOR (weave_index.py, OWNER,
  filed as a QUESTION with both readings).
- Most serious, one line each:
  1. `5f1dc97d5216` — weave_index.py's directory-level read failure can silently pass as "corpus
     is empty" and a `--write` in that window could null two shared, widely-read index files.
  2. `4da7238657a3` — magnitude.py's batch progress tally hides DEFERRED (retriable) entities
     inside "band-only or refused," though nothing downstream parses the printed line.
  3. `18187cb13de7` — two `assay_entity` return paths omit `host`; verified harmless today via
     every consumer's key-based fallback, filed for consistency only.
- Decided NOT to file, with reasons: (a) the boolean-as-score edge case in `magnitude.verify()`
  — no evidence any transport produces it, and guards 1-3 would still gate it; (b) chain.py's
  `harvest()` glob-subdirectory-OSError swallow — same bug class as the filed weave_index
  finding, one directory level deeper, unreproduced and lower-consequence (cache-only, self-heals);
  (c) grounding.py's UNGROUNDED branch missing `assayable`/`reasoning` — verified zero consumers
  read either field; (d) catalogue_web.py's MANAGER-rung synthesis-nulling incident — confirmed
  already fixed upstream in `pipeline.write_record_catalogue`, traced end to end, not re-filed.
- The catalogue_web.py MANAGER-rung incident this batch was specifically briefed to check was
  investigated in full and confirmed closed at its actual source (`pipeline.py`, not this batch's
  files) rather than re-reported.
