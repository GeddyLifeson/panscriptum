# AUDIT — sweep56, batch 12

Modules: src/magnitude.py, src/rigor.py, src/threads.py, src/manifest_builder.py,
src/zfighters.py, src/retry_synthesis.py, src/suppressions.py, src/context_budget.py

Each file was read in full, top to bottom, in successive chunks. This batch is unusually
heavily self-documented: nearly every file carries extensive comments recording defects that
were already found and fixed by earlier sweeps/orders. I verified a sample of those
"already fixed" claims against the current source rather than taking them on faith (see notes
below); all sampled ones check out as actually fixed in the code as it stands today.

No caps/truncation, fail-open path, tautological check, or lost-update race was found in this
batch that is not already disclosed and deliberate (see per-module notes). The only live
findings are four stale line-number citations in comments — accurate in spirit, wrong in the
specific line number cited, which matters because the project's own doctrine treats a citation
as something that "rots" and can mislead a reader who goes to check it.

## DEFECT — stale line-number citations (informational only, no functional impact)

### 1. src/magnitude.py:924-925, self-citation and citation into src/sweep.py

Quote (src/magnitude.py:923-925):
```
    THE `cap` PARAMETER IS GONE (order 7eee204672ce). This was `candidates(ev, cap=None)` ending
    in `sorted(...)[:cap] if cap else sorted(...)`, and neither of its two callers -- :1172 here
    and sweep.py:190 -- ever passed one, ...
```
Both line numbers are stale:
- The actual call site of `candidates(ev)` inside magnitude.py is now line **1207**
  (`cand = candidates(ev)`, inside `assay_entity`), not 1172. Line 1172 today falls inside the
  `_split_gate` docstring, unrelated to `candidates()`.
- The actual call site in sweep.py is now line **199** (`cand = M.candidates(ev)`), not 190.
  Line 190 today is a comment about `cachekey.load`'s `on_corrupt` parameter, unrelated to
  `candidates()`.

Why it matters: this is exactly the failure mode the codebase's own convention (see rigor.py's
`§20f` note, "a line drifts and a tag does not") exists to prevent — a citation that once was
right and has since drifted as the file grew, so a reader who goes to verify the claim at the
cited line finds something else and may doubt the (correct) claim itself, or waste time
searching. No functional effect since the removed `cap` parameter really is gone and both
callers really do call `candidates(ev)` with one argument.

Confidence: DEFECT (comment-accuracy defect, not a code-behaviour defect).

### 2. src/manifest_builder.py:171, citation into src/context_budget.py

Quote (src/manifest_builder.py:168-172):
```
# REPORTED DEAD, NOT DELETED (order db36d589713e, owner ruling 2026-09-08: "mark and keep,
# one line each, delete nothing"). THIS CONSTANT IS DOCUMENTATION AND IS READ BY NOTHING:
# a tree-wide grep finds three occurrences of the name -- this line and two comments
# (context_budget.py:20 and :366 below). ...
```
`context_budget.py:20` is correct (it does read "`FEATS_BLOCK_CHARS = 20000`... was a constant
with no arithmetic relationship..."). But `context_budget.py` is only **296 lines long** —
line 366 does not exist in that file at all. The second comment mentioning `FEATS_BLOCK_CHARS`
by name is actually in the *same* file, manifest_builder.py, at line **399**
(`# DERIVED, NOT DECLARED (m46). \`FEATS_BLOCK_CHARS\` had no arithmetic relationship to...`).
Verified via `grep -n FEATS_BLOCK_CHARS` across src/: exactly three hits total
(context_budget.py:20, manifest_builder.py:176 itself, manifest_builder.py:399) — none at
context_budget.py:366.

Why it matters: same class as #1 — a citation pointing at a location that cannot possibly hold
the claimed content (the target file is shorter than the cited line number), which is a stronger
signal of drift than a merely-wrong-but-plausible line number.

Confidence: DEFECT (comment-accuracy defect).

### 3. src/manifest_builder.py:139, citation into src/read.py

Quote (src/manifest_builder.py:137-139):
```
# Characters of feat JSON one generation call may carry. The measured lesson is `read.py`'s,
# not `generate.py`'s (generate.py cites it for OUTPUT attention; the input measurement is at
# read.py:80 -- 10,000 chars/5 chunks found 41 feats where 36,000 chars/2 chunks found 19).
```
The actual measurement table ("10,000 characters 5 chunks -> 41 feats" / "36,000 characters
2 chunks -> 19 feats") lives at src/read.py:**101-102**, not line 80. Line 80 of read.py today
is mid-paragraph prose about the fabrication-rate consequence of truncation, not the table
itself.

Confidence: DEFECT (comment-accuracy defect).

### 4. src/suppressions.py:247, citation into src/drill.py

Quote (src/suppressions.py:245-248):
```
    IT WAS INSIDE THE LOOP. `problems()` built the listing once PER WILDCARD ROW, so the entire
    repository -- ... -- was walked again for every wildcard suppression on file, and
    `drill.py:2515` calls `problems()` every cycle as a net. ...
```
The actual net that calls `SUP.problems()` is at src/drill.py:**4582**
(`lambda: SUP.problems() == [],` under `net(a, "no suppression is expired or dangling", ...)`).
Line 2515 of drill.py today falls inside an unrelated docstring
(`the_feat_bearing_path_really_is_untouched`) about `synthesis_blocks`' feat-bearing fallback,
nothing to do with suppressions. drill.py is 17,710 lines and clearly has grown substantially
since this comment was written (net insertions upstream shift everything below them), which is
the likely mechanism for all four of these drifts.

Confidence: DEFECT (comment-accuracy defect).

## QUESTIONS (deliberate-design candidates, flagged rather than asserted as bugs)

### Q1. src/threads.py — `_known_for_t4()` re-reads LAWS.json from disk on every `threads_for()` call

`threads_for()` (called once per entry, per its own docstring math "282,711 entries") calls
`asserts_a_magnitude(entry)` and, when true, `edge(MAGNITUDE_LAW, "T4", ..., rec["code"],
set(_known_for_t4()))` — and `_known_for_t4()` calls `law_codes()`, which opens and parses
`data/LAWS.json` from scratch every time (no caching, unlike `annex_codes()`/`law_codes()`'s
sibling functions which are explicitly documented as "not cached" but are only called once per
`build()` run). If `threads_for()` is ever driven over the full corpus (currently it is only
called from src/drill.py's test fixtures, not from the generation pipeline), this would mean
hundreds of thousands of redundant file opens/parses per run. This is a performance question,
not a correctness one — I did not find any evidence it is wired into a hot path today (grep
found no importer of `threads.threads_for` outside drill.py). Flagging rather than asserting a
defect since it may be deliberately deferred until T4 sees real per-entry traffic.

### Q2. src/suppressions.py — `add(..., ttl_days=DEFAULT_TTL_DAYS)` has no upper bound on `ttl_days`

`add()` validates that `reason` is non-empty and >= 12 characters, but does not validate
`ttl_days` — a caller passing an extremely large `ttl_days` (or a negative one) would not be
refused. The task brief specifically asks about "a suppression that ... can never expire", and
technically a sufficiently large `ttl_days` produces one that outlives any practical review
cycle. However: (a) `add()` has zero callers anywhere in src/ today (grep confirms), so this is
currently a theoretical API-shape question rather than a live path; (b) the module's own default
(180 days) and its header's whole argument is against silent/permanent suppression, so an
unbounded `ttl_days` would be contrary to the file's stated design intent if ever exercised.
Flagging as a QUESTION for whoever eventually wires a caller to `add()`, not as a live defect.

## Per-module "nothing else found" notes

- **src/magnitude.py** (1959 lines, read in full): the five guards (verbatim/relevance/subject/
  saturation/quantity) were traced through `verify()`, `_split_gate()`, `quantity_scores()`, and
  `assay_entity()`'s call ordering. All fail closed (bad citation/relevance/subject -> UNESTIMABLE
  + a recorded rejection, never a silently-passed score). `saturated()`'s six-axis floor is
  computed, not hardcoded, and documented as a stated ruling. `compose()`'s `budget` is always
  called with `None` (line 1234), so `evidence_dropped_to_fit` is always 0 — the code says so
  explicitly ("always 0 now; kept so a future budget cannot be silent"), so this is disclosed
  dead-weight, not a hidden cap. No bare `except:`, every `except Exception` calls
  `silence.note(...)`. No further defects found beyond citation issue #1 above.

- **src/rigor.py** (1132 lines, read in full): `_validate_reciprocal_matrix` refuses non-square /
  non-finite / non-positive / non-reciprocal matrices before any arithmetic runs (raises rather
  than clamps). `bradley_terry`'s Ford's-condition check was verified to be a real, reachable
  refusal (not a dead `elif`, per its own comment about that exact defect having been fixed and
  re-verified over 20,000 randomised tournaments). `main()`'s load-bearing display cut extends
  through tied entries and states the remainder rather than silently stopping at 6. Nothing
  further found.

- **src/threads.py** (895 lines, read in full): T1-T4 edge construction goes exclusively through
  `edge()`, which refuses (raises `ThreadRefused`) both a non-derivable class and a
  non-resolving address — so a dangling thread cannot be constructed by this module's own
  functions. `annex_codes()`/`law_codes()` fail closed to an empty set on any read/parse
  problem or a declared-count mismatch, which correctly degrades to "T3/T4 refused" rather than
  "T3/T4 to an unverified address." Cohort/category logic (`category_path`, `cohort_family`)
  matches its own extensively-argued design notes. See Q1 above for the one open question.
  No caps found beyond the one the module's own docstring names and defends
  (`parts[:2]` in `cohort_family`, which decomposes an address, not a listing).

- **src/manifest_builder.py** (670 lines, read in full): `pack_feats` never drops evidence —
  an entity larger than the budget is paginated across blocks, and a single deed larger than
  the whole budget still gets its own (oversized) block rather than being dropped, exactly as
  documented. Both `data/manifest.json` and `output/index/unassigned_sources.md` writes gate on
  `silence.write_json`/`replace_retry`'s return value and report a denied write rather than
  claiming success. `load_record`'s fuzzy filename matcher has an explicit length floor and
  exact-match-always-wins rule that was reasoned through carefully; no obvious way to make it
  mismatch on the described data. See citation issues #2 and #3 above; no other defects found.

- **src/zfighters.py** (536 lines, read in full): hand-authored data file (14 fighters x 11
  axes each = 154 axis entries, confirmed by count) plus a thin `compute()`/`main()` wrapper.
  The Son-Goku-sheet merge failure path is handled (caught, logged via `silence.note`, and
  explicitly surfaced on stdout with an "INCOMPLETE ROSTER" banner rather than silently omitting
  him). `--full` output no longer truncates citation text (`textwrap.wrap`, not `[:60]`, per its
  own comment about that fix). Output write gates on `silence.write_json`'s return value. No
  defects found.

- **src/retry_synthesis.py** (379 lines, read in full): does not touch
  `state/PIPELINE_STATE.json` or write records directly; `do_merge()` goes through
  `PL.write_record` (documented as a merge-on-write, not a blind overwrite) specifically to avoid
  the two-writer race the file's own comments describe having hit before. `save_side()`
  re-reads-and-merges the side file before each write and returns whether the write actually
  landed, and the caller in `main()` treats an unlanded save as "not written" rather than
  printing success. `stranded_sources()`'s selection is by condition (no synthesis + has
  entries) rather than by a specific failure cause, which the comment argues (and I agree) is
  the right generalisation over "selecting by symptom." No defects found.

- **src/suppressions.py** (353 lines, read in full): every suppression has a mandatory,
  length-checked reason and a computed `expires_at`; `active()` filters by `expires_at > now`
  on every call (no caching that could serve a stale/expired row); `problems()` reports both
  EXPIRED and DANGLING rows as faults rather than silently dropping them, and reports an
  unreadable suppressions file as a fault in its own right (not as zero problems). `suppressed()`
  and `problems()` both use `fnmatchcase` rather than `fnmatch` specifically to avoid
  case-insensitive over-matching on Windows, which is the correct fail-shut direction. See Q2
  above (theoretical, uncalled path) and citation issue #4 above; no other defects found.

- **src/context_budget.py** (296 lines, read in full): this is the module the task brief
  specifically flagged as a likely home for legitimate-looking truncation, and I traced every
  cut carefully. `content_budget_chars()` can return zero or negative and documents that callers
  must treat that as "cannot be done," never clamp it small and proceed; `feats_block_budget()`
  honors that by raising `ContextOverflow` rather than clamping. `pack_feats` (manifest_builder.py)
  then treats the returned budget as a pagination boundary, not a cap on total evidence — every
  slice is emitted, per Hard Rule 0, as verified when reading manifest_builder.py above. The two
  correction constants (`JOB_OVERHEAD_CHARS`, `METADATA_INFLATION`) are both documented as
  measured, and both push the budget *down* (conservative), which is the correct direction for a
  refusal gate. No defects found in this module itself.
