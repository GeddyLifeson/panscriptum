# sweep run54 — batch 14 audit

Modules read in full, every line: `src/read.py` (1671 lines), `src/health.py` (1307 lines),
`src/generate.py` (978 lines, owner-held prose gate — audited only, not edited, and no change to
`prose_enabled`/`step4_enabled` proposed or considered), `src/weave.py` (699 lines),
`src/catalogue_codex.py` (512 lines), `src/burgs.py` (433 lines), `src/style_audit.py`
(339 lines), `src/halo.py` (220 lines), `src/module_index.py` (193 lines).

Method: read top to bottom in the tool, cross-checked internal line citations against `grep -n`
of the actual defining lines, and traced the arithmetic/control-flow of the functions I flagged
by hand rather than trusting the surrounding comment. Where a comment already narrates a past
defect and its fix, I read the current code to confirm the fix is actually in effect rather than
re-filing history. I did not execute any code (per the brief's read-only rule) and did not touch
`data/`, `state/`, or any ledger.

---

## src/read.py

### MINOR — stale line citation: comment points at the wrong function
**Where:** src/read.py:70
**What:** The header comment on `CHUNK` says: "nothing anywhere would notice the two drifting
apart: health.check_context_budget (health.py:446-466) grades CHUNK against the CONFIG value
directly".
**Why it is wrong:** `health.check_context_budget` is actually defined at `src/health.py:590`
and its body runs to `:610` (confirmed by `grep -n "def check_context_budget"` and reading the
function). The citation is off by roughly 144 lines. A reader following the citation to verify
the claim lands inside `check_api_paths`'s docstring instead, which has nothing to do with
context budgeting. The claim itself (that `check_context_budget` reads the live config value and
would not notice a stale header comment) is still true on inspection of the real function at
:590-610 — only the pointer is wrong.
**Confidence:** Verified directly: read both files' actual line numbers and grepped the
definition.

### MINOR — stale self-citation: comment points at the wrong lines for its own claim
**Where:** src/read.py:558
**What:** The comment ends "...the "(%d to GPU)" figure counts what the GPU actually received --
which is the whole reason read.py:213-215 says the counter exists."
**Why it is wrong:** Lines 213-215 of this same file are inside the `_names()` function's
comment about word-boundary matching ("A NAME WORD MUST START A WORD OF THE SENTENCE...",
the MetalGarurumon/Lois-Lane example) — unrelated to the `_FELL_BACK` GPU counter. The actual
explanation of why the counter exists ("Lost updates understate the 'N to GPU' figure -- and
that figure is the only thing that distinguishes a run quietly served entirely from the slow
path from a run that is merely slow, which is the reason the counter exists.") is at
src/read.py:271-274, beside the `_FELL_BACK` and `_FELL_BACK_LOCK` definitions.
**Confidence:** Verified directly by reading both cited spans and the actual counter definition.

### Read but clean (with what was checked)
- `_names()`, `_fold_diacritics()`, `_norm_q()`: traced the word-boundary/diacritic-fold logic
  by hand against the worked examples in the comments (MetalGarurumon/Azulongmon, Lois
  Lane/Planet, Zanpakutō/Zanpakuto, the `parts` empty-fallback for short names like "Ash"/"Vi").
  All hold up against the stated failure cases.
- `_ask_ungated()`'s transport ladder (quick pool x2 -> local GPU once -> backoff ladder x5 ->
  local GPU again in `auto` mode): traced the control flow for `auto` and `cascade` modes. The
  apparent double call to `_local()` in `auto` mode (once before the backoff ladder, once after)
  is not a bug: the first failure sets `_GPU_DOWN_UNTIL`, so the second call returns `None`
  immediately via the bench check in `_local()`. Redundant but not incorrect.
  **Confidence:** traced by hand against `_local()`'s bench-check ordering.
- `read_entity()`'s cap_chunks-ignored path, per-chunk caching keyed on host+entity+text, and the
  "cached only when fully answered" gate (`if unanswered: return out`): read against the
  documented failure histories and confirmed the current code matches the stated fix (entity
  belongs in `_chunk_key`; an entity is never written to its permanent cache with any chunk
  unanswered).
- `priority()`'s three-bucket split (have_page / no_page / thin) and deep/light interleave:
  traced the loop; nothing is dropped, `thin` entries still sort and still get read, matching the
  Hard Rule 0 fix the comments describe.
- `queue()`'s host-map read-with-retry and refusal on an empty/unreadable map: confirmed the
  `raise SystemExit` path actually fires before any queue is built, so an unreadable host map
  cannot silently report "0 entries with pages" as success.
- `main()`'s exit-code propagation (`return done["errored"] == 0` from `run()`, `return 0 if ok
  else 1` from the one-shot path in `main()`): confirmed both paths.

---

## src/health.py

Read in full including the ledger flush compare-and-swap (`_flush_ledger`, `_flush_samples`),
the preflight checks (`check_control_chars`, `check_context_budget`, `check_api_paths`,
`check_caches`, `check_state`), and `reopen_stranded()`.

No new findings. What I specifically checked and confirmed matches the code:
- `_flush_ledger`/`_flush_samples`: the compare-and-swap digest is taken *before* the read on
  each retry attempt (not reused from the first iteration), so a refused round genuinely
  re-reads rather than re-submitting a stale digest.
- `check_state()`'s use of `P.entry_settled(e)` (a single shared predicate) rather than a
  hand-rolled `not e.get("catalogued")` check, both here and in `reopen_stranded()` — confirmed
  both call sites use the same import (`import pipeline as P`) and the same predicate name.
- `reopen_stranded(dry=False)`'s re-read-and-refuse-on-change before writing
  `PIPELINE_STATE.json`: confirmed the comparison is against the raw text read at the top of the
  function (`st_text`), not a re-serialization, so key-order differences can't produce a false
  "unchanged" positive.
- `preflight()`'s stamp-write verdict is checked (`landed = bool(silence.write_json(...))`) and a
  denied write is reported via `silence.note` and a stderr line, not silently accepted.

---

## src/generate.py (audited only — owner-held prose gate; no `prose_enabled`/`step4_enabled` change proposed)

Read in full including `strip_think()`, `call_ollama()`, `_covered()`, `_deed_traced()`/
`_deed_shortfall()`, `generate_job()`'s block-write loop, and `main()`'s evidence-floor and
manifest-loading guards.

No findings. Specifically traced:
- `strip_think()`'s three-shape stripping order (complete block, then stray close, then stray
  open) against the documented Ollama response shapes — the ordering is correct: a complete
  `<think>...</think>` pair is removed by `_THINK_BLOCK` first, so `_THINK_CLOSE`'s "everything
  up to the last close" only ever fires on an unpaired closing tag.
- `generate_job()`'s "once a block fails, subsequent blocks are marked unattempted rather than
  generated" logic (`if missing: unattempted.extend(...); continue`): confirmed `missing` is
  populated only from a block's own `lacking` list after its retry, and confirmed subsequent
  blocks never reach `call_ollama` once `missing` is non-empty.
- `main()`'s `--limit` truthiness fix (`if args.limit is not None:` rather than `if args.limit:`)
  and the evidence-floor `0.0`-coercion fix (`PG.floor_ok(floor)` gating before the loop) — both
  read as currently in effect, not just narrated.
- The `ChapterRefused` exception's `lists` payload and how `main()` merges it into `failures[...]`
  via `getattr(e, "lists", {})` — confirmed a plain `RuntimeError` (no `.lists` attribute) adds
  nothing rather than raising a second exception.

---

## src/weave.py

### QUESTION — mechanics filter fails open (not closed) on an import error
**Where:** src/weave.py:268-276 (`filtered_index()`)
**What:** 
```python
try:
    from pipeline import _STATBLOCK
except Exception:
    silence.note("weave.py:statblock-import")
    _STATBLOCK = None
...
if (_MECHANIC.match(nm)
        or (_STATBLOCK is not None and _STATBLOCK.search(desc))
        or _RULES_VOICE.search(desc)):
```
**Why it might matter:** If `from pipeline import _STATBLOCK` raises (e.g. `pipeline.py` has a
syntax error or the import genuinely fails), `_STATBLOCK` becomes `None` and the
`_STATBLOCK.search(desc)` arm is simply skipped for every entity for the rest of the run —
entities that look like stat blocks (the exact shape this module's own docstring says caused
"Ability Score Improvement" and "Extra Attack" to rank among the strongest cross-source
fusions) are no longer filtered on that basis, only on `_MECHANIC` (name-only) and
`_RULES_VOICE` (second-person voice). This is a fail-*open* degradation on an ImportError, which
is the opposite of the FAIL CLOSED property CLAUDE.md's Hard Rule -1 states for this project, and
`generate.py` in this same batch explicitly hardens an analogous case (the P8 meta-language
check) to fail closed on exactly an `ImportError` for exactly this reason. I am filing this as a
QUESTION rather than a bug because (a) it degrades one of three overlapping filters rather than
disabling all mechanics filtering, and (b) `pipeline.py` failing to import is a low-probability
event in practice, so this may be an accepted risk rather than an oversight — but it is the same
shape the project has separately hardened elsewhere, so it seemed worth surfacing rather than
silently passing.
**Confidence:** Read the code directly; did not attempt to trigger the ImportError.

### Read but clean (with what was checked)
- `idf_table()`, `name_surprisal()`, `pair_weights()`/`surprisal_pair_weights()`: confirmed the
  "superseded, not deleted" functions (`pair_weights`, `null_threshold`) are in fact uncalled —
  `main()` calls only `surprisal_pair_weights` and `null_threshold_surprisal`.
- `null_threshold_surprisal()`/`null_threshold()`: confirmed both raise
  `NullThresholdUnmeasured` rather than returning `0.0` when `trials<=0` or no trial produces a
  weight, and confirmed `components()` independently refuses `threshold<=0` — two separate
  guards against the "0.0 threshold merges everything" failure mode described in the comments.
- `components()`'s complete-linkage merge loop and its early-exit in `min_cross()`: traced by
  hand — the early exit only fires once a sub-threshold pair is found, at which point the
  cluster pair is already disqualified regardless of the true minimum, so returning early does
  not change the `m >= threshold` verdict.
- `main()`'s write gating (`silence.write_json` per-file, verdict checked, all three artifacts
  named individually on partial failure): confirmed.

---

## src/catalogue_codex.py

Read in full including `parse_codex()`'s manifest-count cross-check, `load_register_index()`'s
collision handling, and `main()`'s section-binding, per-element dedup, and roll compare-and-swap.

No findings. Specifically traced:
- The `pair = (norm(etype), key)` dedup key (rather than `norm(name)` alone), confirming the
  fix for the Troglodyte/Mastiff/Dragonmark type-collision loss the comment describes is in
  effect — two different `etype` values with the same `name` are both kept.
- The exact-match-wins-outright / ambiguous-substring-refuses-rather-than-guesses section
  binding logic in `main()`'s roll loop — confirmed an ambiguous match is appended to
  `ambiguous` and the source is skipped (`if not title: continue`), never bound to an arbitrary
  candidate.
- `roll_changes` is applied via `roll.update_rows(roll_changes, path=ROLL)` against a
  freshly-read roll rather than the `roll` list loaded at the top of `main()` — confirmed this
  is a compare-and-swap over changed rows only, not a whole-document overwrite.
- Exit code: confirmed `denied` (per-record write failures) and `not roll_landed` both propagate
  to `return 1`.

---

## src/burgs.py

Read in full including the rank-size derivation (`burg_count`, `largest_city`,
`rank_population`), the closed-form-plus-correction `_rank_at_or_above()`, and
`class_histogram()`.

No findings. Specifically hand-verified:
- `class_histogram()`'s reversed-CLASSES accumulation: walked the four class boundaries
  (city/town/village/hamlet) by hand against `_rank_at_or_above` and confirmed the
  `within - above` subtraction correctly partitions non-overlapping rank ranges for a
  concrete example set of boundaries.
- `_rank_at_or_above()`'s closed-form-then-correction: for `ZIPF_Q = 1.0`, the closed form
  `int((p1/lo)**1.0)` reduces to integer-truncated division, which exactly matches
  `rank_population`'s own `int(p1/k)` — so the "correct by at most a step or two" claim holds
  with margin at the current exponent, and the two correction `while` loops handle the
  boundary case honestly either direction.
- `burgs_for()`'s `--limit` clamp (`stop = n if limit is None else max(0, min(int(limit), n))`):
  confirmed this can only narrow (never fabricate ranks past `n`, never treat `limit=0` as "no
  limit").
- `main()`'s per-world accumulation into a list-valued `per_world[designation]` (handling
  non-unique designations) rather than a dict overwrite — confirmed no world is dropped.

---

## src/style_audit.py

Read in full including `entries()`, `record_of()`, `opener_shape()`, the `TURN_ENDING` regex,
and the `--self-test` fixtures/assertions.

No findings. Specifically checked:
- `TURN_ENDING`'s anchor is `\Z` (true end of string) with no `re.M` flag, confirmed against the
  documented regression (the old `re.M`-anchored `$` matching every paragraph break). The
  compiled pattern in the current file has no `re.M`.
- Ran the `--self-test` fixture text through the described logic by hand: the GAMMA fixture's
  turn ending ("...to the age. And so it remains.") is matched by `TURN_ENDING` because the
  preceding lowercase "and" ("it is a warning — and it stands...") does not match the
  case-sensitive `(?:And|But|Yet|Still|Which|That)\b` alternation, so only the true sentence-
  initial "And" is counted — consistent with the `turn_endings == 1` exact-count assertion.
- `_cut()`'s three call sites (`shapes`, `openers`, `banned`, `vocab`) all pass the true
  population size as `total`, not the post-`most_common(top)` slice — confirmed the Hard Rule 0
  fix (remainder always stated) is in effect for all four rankings, not just the ones the
  comments call out by name.

---

## src/halo.py

Read in full, including the `ROSTER` data and `compute()`'s per-axis provenance tagging.

Clean. Checked for the shape of defect `wh40k.py` is noted as still carrying (an unconditional
`"[wiki] "` provenance tag applied to every axis regardless of whether the citation is a real
quotation) — confirmed `halo.py`'s `compute()` reads `v[2]` (the per-axis tag: `"wiki"` or
`"canon"`) individually for each of the 33 worksheet lines rather than hardcoding one tag, so the
fix this module's own docstring claims is actually in the code, not just described.
Also confirmed the write-verdict gating in `main()` (`if not silence.write_json(...): return 1`)
and that `--full`'s citation wrapping (`textwrap.wrap(d["cited"], 54)`) prints every wrapped line
via the `for cont in body[1:]` loop rather than only the first.

---

## src/module_index.py

Read in full. Clean. Checked:
- `_modules()` walks `src/` recursively (`os.walk`, skipping `__pycache__`) rather than a
  non-recursive glob, confirmed against the stated `catalogue_local.py`-in-`deprecated/` failure
  case this was fixed for.
- The duplicate-group-name check (`seen_in`/`dupe_names`) and the stale-group-name check
  (`stale`) are both independent, both `return 1` on the *page-write* success path (i.e. the
  page is still written even when GROUPS itself is wrong, and the exit code still reports the
  GROUPS defect) — confirmed by reading the order of operations at the end of `main()`.
- The atomic write (pid+thread temp name, `silence.replace_retry`, verdict checked before
  printing a success line) — confirmed.

---

## Summary of findings

- MAJOR: none.
- MINOR: 2 (both stale line-citations in `src/read.py`, listed above with corrected targets),
  plus 1 QUESTION (fail-open mechanics filter on ImportError in `src/weave.py`).
- INFO: none beyond what is noted inline above as "clean, here is what was checked."
