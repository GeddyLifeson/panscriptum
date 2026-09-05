# Audit batch 10 — run44

Modules read in full, top to bottom: `src/publish.py`, `src/rigor.py`, `src/build_terminal.py`,
`src/ingest_doc.py`, `src/anchors.py`, `src/pantheon.py`, `src/entity_match.py`,
`src/chord_field.py`, `src/module_index.py` (5,225 lines total).

## Overall finding

These nine modules are, at the time of this sweep, in unusually good shape. Every one of them
already carries extensive first-person documentation of prior defects found and fixed — several
citing prior sweep orders by hash — and the remaining code largely holds up under a line-by-line
re-check. I looked specifically for the classes named in the brief (inverted conditions,
falsy-zero slips, tautological guards, Hard Rule 0 caps, docstring/code mismatches, swallowed
failures, non-atomic shared-state writes) and did not find a new instance of any of them with
high confidence in this batch. What follows is the record of what was checked and the small
number of items worth a human's attention, graded honestly by confidence — most of them are
QUESTIONS, not confirmed defects.

I did not re-file the `publish.py:293` `_AMBIGUOUS` case-sensitivity item — the batch brief
already records that it was found and deliberately kept as-is (it fails toward over-blocking,
the safe direction for a gate in front of a public push), and I confirm on reading it that this
is still true: `_AMBIGUOUS = re.compile(r"^(sk-|[a-z+]+://)")` (publish.py:293) is
case-sensitive while the vendor pattern it screens (`_SECRET`, e.g. the `(?i:postgres|...)`
alternative at publish.py:212) is case-insensitive, so a capitalized scheme like
`Postgres://user:pass@host` fails the `_AMBIGUOUS` match and is treated as an unambiguous,
always-real secret (publish.py:302-303) rather than being entropy-gated or checked against the
placeholder-credential pattern. That is strictly more conservative than the current behavior
would be if it were fixed, so it is not a new finding, just confirmation of the standing one.

## src/publish.py (1,619 lines)

This is the file the batch brief calls out for the heaviest scrutiny, since it is the last gate
in front of a public GitHub push. I read every function: the vendor/entropy secret patterns,
`_scrub`/`scrub_text`/`_scan_units`/`scan_for_secrets` (the three independent locks), `git()`,
`_unpushed()`, `_same_dir()`/`_live_root_state()`/`_live_file_state()`/`_may_delete_in_export()`
(the delete-path guards), `prune_export()`, `sync_tree()`, `_write_text_atomic()`, `_swap()`/
`render_page()`, `ensure_site()`, `write()`, `_mutation_unsafe()`/`_mutation_observation()`,
`PushHeld`, `push()` (the four interlocks: ledger guard, mutation interlock, secret scan,
push-confirmation), `maintenance_shift_live()`, and `main()` (including the `--loop` cycle and
its halt/codewatch handling).

Every shared-state write in this file (`docs/state.json`, `docs/index.html`, `.gitignore`,
`.nojekyll`, `.is-export-copy`) goes through `silence.write_json` or the module's own
`_write_text_atomic`, both of which land through `silence.replace_retry` and both of which have
their return value checked and reported — I did not find an unguarded `open(path, "w")` against
a shared or published target anywhere in the file (the only bare `open(tmp, "w", ...)` calls
target a pid+thread-qualified scratch file, per the pattern documented at line 994).

**No new defect found.** Two low-confidence notes, offered as questions rather than findings:

1. **`_scan_units` can yield one very long line unsplit across a block boundary** (publish.py:
   368-395). The intended behavior (stated in the docstring at line 354 and the block-size
   comment at line 343) is that no more than `_SCAN_BLOCK` (256 KiB) plus a small overlap is ever
   held for one line, with a line exceeding `line_cap` (`max_bytes`, default 2,000,000) chopped
   into overlapping segments. That chopping only triggers when an entire 256 KiB *block read*
   contains no newline at all (`if len(parts) == 1:` at line 378). If a line has been
   accumulating across several such no-newline block reads (so `buf` is already close to
   `line_cap`) and then a later block *does* contain a newline, the code falls through to
   `yield lineno, carry + buf` (line 387) and emits the whole accumulated line — potentially up
   to roughly `line_cap` plus one more block's worth of characters — as a single unit, rather
   than continuing to chop it. This does not create a scanning gap (the regex still runs over
   every character, so no secret is missed), it just means the "how much of one file is held in
   memory at a time" bound the docstring states is not quite exact at this boundary. Given this
   is a defensive-memory concern rather than a coverage or security concern, and given the file's
   own drill (`_secret_scan_reads_every_staged_file`, referenced at line 445) already exercises
   oversized files, I am flagging this as a minor question rather than a finding. Confidence:
   low — I have not run the drill to see whether it happens to already cover this exact boundary
   case.

2. **`git status --porcelain` line-parsing in the commit-message builder assumes a fixed
   3-character prefix** (publish.py:1335-1341: `p = ln[3:].strip().strip('"')`). Porcelain v1's
   normal 2-status-char-plus-space format makes this correct for an ordinary modified/added/
   deleted file, but a rename entry is reported as `R  old -> new`, which this slice does not
   parse specially — `p` would come out as `"old -> new"`, which then fails the
   `p.startswith("src/") and p.endswith(".py")` test and is counted under `other` instead of
   `code` even when the rename is a `src/*.py` file. This only affects the cosmetic
   "sync <time> — code: a, b, c; N data/site file(s)" commit message (line 1349), never the
   actual `git add -A` / commit contents, so I am not filing it as a defect — it is at most a
   commit-message accuracy nit, and I note it only because it is the one place in this file where
   a string offset is asserted rather than derived.

## src/rigor.py (961 lines)

Read in full: the commensuration functions (`measure_bit_value`, `faculty_parity_weights`),
the AHP/HodgeRank/Bradley-Terry trio and Theorem 1 check (`perron_weights`, `logrank_weights`,
`theorem_1_check`, `consistent_matrix`, `_strongly_connected`, `bradley_terry`), the MDL section
(`mdl_bits`, `_log2_choose`, `adjudication_beta`), the uncertainty-propagation section
(`lognormal_product`, `prob_at_least_one`), the extreme-value section (`ceiling_confidence`,
`gumbel_return_level`), `mathematical_resonance()`, and `main()`.

I specifically checked Ford's-condition handling in `bradley_terry` (the strongly-connected-graph
refusal, the undefeated/winless divergence refusal, and the prior-regularisation carve-out that
suppresses both refusals) against the MM iteration and the deviance computation, and checked
`main()`'s two guarded-verdict blocks (the faculty-weight "muted" check at line 798 and the
MDL-underpriced check at line 862) to confirm both are now genuinely derived from live data
rather than the hardcoded assertions the surrounding comments say they replaced. Both check out:
`_muted` is computed from `A.FACULTY_WEIGHTS` at print time, and `_underpriced` is appended
inside the same loop that prints each row's floor/declared comparison, so neither branch can
diverge from what was just printed above it.

I also checked the "ranked, never truncated" load-bearing display at the end of `main()` (lines
933-953): it slices to 6 only after extending the cut through every tie at the 6th value's own
fanout count (`while _cut < len(_lb) and _lb[_cut][1] == _lb[_cut-1][1]: _cut += 1`), and prints
an explicit "... and N more" line with a pointer to the full uncapped field
(`mathematical_resonance()['load_bearing']`) whenever the cut is short of the full list — this is
the tie-respecting, marked, uncapped-underneath pattern Hard Rule 0 asks for, not a violation of
it.

**No defect found.**

## src/build_terminal.py (655 lines)

Read in full, including the embedded JS template (the SVG radial-tree layout, panning/zooming,
the panel rendering for a node/source/world selection) and `main()`'s write path.

I checked one thing closely enough to be worth recording even though it turned out clean: the
JS `panel()` function's `holds` computation (line 495-496) reads `nd.k.length` unguarded while
the adjacent `nd.w`/`nd.s` reads on the same lines are defensively guarded
(`nd.w?nd.w.length:0`). I traced this against `src/navtree.py` (the generator of
`data/NAVTREE.json`, the file this template's `DATA` is spliced from): every serialized node
there always carries a `"k"` key — `sorted(v["k"])`, possibly an empty list, but never omitted
(navtree.py:205) — whereas `"w"` and `"s"` are only added to a node's dict when non-empty
(navtree.py:207-210). So the asymmetric guard in the JS is intentional and correct, not a defect:
`nd.k` is guaranteed present. Not filing this — recorded so a future sweep does not spend time
re-checking the same asymmetry.

`main()`'s write path is atomic and its denial is reported through the exit code (return 1 on a
denied `replace_retry`, per the comment block at line 630 citing the same pattern
`catalogue_codex.py` and `generate.py` already use) — matches its own documentation.

**No defect found.**

## src/ingest_doc.py (543 lines)

Read in full: `slug`, `_clean`, `extract` (PDF → page-keyed corpus, raises rather than
report-and-continue on a denied write), `register` (host binding, returns the landed value or
None), `_slug_words_contain`/`record_path` (the ambiguous-match refusal), `_ask` (pool-then-local
transport), `mine` (the resumable chunked entity-extraction loop, including the oversize-page
re-splitting and the cursor/record two-writer discipline), and `main`.

Checked the chunking loop (lines 288-304) for an off-by-one or duplication bug directly, since it
is a correctness-sensitive algorithm rather than a display concern: pages are processed in sorted
order, an oversized page flushes the pending accumulator first and then is emitted as its own
run of `CHUNK`-sized, individually page-labelled segments, and a normal page that would overflow
the accumulator flushes it before being added. I did not find a gap or an overlap in the page
coverage.

Checked the two-writer discipline around `write_record_catalogue` and the resume cursor
(lines 373-434): a denied record write rewinds `known` and stops the loop *without* advancing
`state["next"]`, so nothing already merged is silently skipped on the next run and nothing
un-landed is treated as landed; a denied cursor write is reported but does not stop the loop
(documented and correct, since the record write is the one that must not race ahead of disk).
The `landed_found` vs `state["found"]` bookkeeping at the end (lines 441-450) correctly reports
the gap when a cursor write was denied rather than letting the two numbers disagree silently.

**No defect found.**

## src/anchors.py (458 lines)

Read in full: the `NON_ENERGETIC_AXES` table, `vector_score`, the five `ANCHORS` records (Skate
Guy, Goku, Seat of the Creator, A Sword, Yggdrasil), and `run()`'s full invariant suite (the
declared-ladder-grades-every-anchor check, the decimal-produced check, the monotone
floor-to-ceiling check, and the five per-anchor `CLAIMS` tests), plus the reported-not-graded
`INSTRUMENT_WINDOWS` saturation question at the end.

This file is itself a hardening exercise from a prior sweep (its own trailing comment records
that until run #26 the whole invariant suite was computed and discarded rather than gated on).
I re-verified that the current code actually gates the exit code on `ok = all(p for p, _l, _d in
verdicts)` (line 385) and that `sys.exit(0 if _ok else 1)` at the bottom uses that same `_ok`,
not a stale or shadowed name. It does.

**No defect found.**

## src/pantheon.py (373 lines)

Read in full: the `GODS` data table (Zeno, Vados, Whis, Beerus, Champa, Grand Minister),
`compute()`, `value()`, and `main()` (the ranked-by-magnitude table, the `--full` uncapped detail
view with wrapped, unclipped citations, the `Z_FIGHTERS.json` merge with its `_incomplete`
marker handling, and the gated write with its exit code).

Checked the `--full` view's citation printing (lines 335-355) specifically for a reintroduced cap
since the surrounding comments describe two previous truncations (`[:58]` on citations,
`epoch[:40]`) that were removed — confirmed the current code prints the full `d["cited"]` string
via `textwrap.wrap` with continuation lines, no slice.

**No defect found.**

## src/entity_match.py (297 lines)

Read in full: `MatchReason`, `split_qualifier`, `qualifier_compatible` (the continuity-safety
gate the whole module exists to enforce), `_bigrams`/`_dice`/`similarity` (with its own
documented rejection of a faster `rapidfuzz` swap on calibration grounds), `candidates()`,
`best()`, and `embed_available()`.

This module is pure proposal/no-mutation by design (stated in its own header and true of every
function read — nothing here writes to a catalogue or a join). Checked `candidates()`'s two early
exits (empty name, empty pool) for the exact defect its own comment says was fixed — a missing
`blocked_by_qualifier` key that would `KeyError` a caller reading it unconditionally — and both
early-return dicts do carry that key.

**No defect found.**

## src/chord_field.py (211 lines)

Read in full: the `ADJUDICATIONS` table (six named laws, each with `ki_demands`,
`shrink_demands`, `already_permitted`, `must_declare`, `experiment`, `beta_bits`) and the small
set of physics helper functions (`total_beta`, `per_system_beta_without_unification`,
`landauer_floor`, `recoil_momentum`, `recoil_velocity`, `critical_power_self_focus`). This is
mostly narrative/reference data plus straightforward formula implementations; I checked each
formula against the physics it claims (Landauer bound, `p = E/c` recoil, Kerr critical-power
expression) and found no arithmetic or sign errors.

**No defect found.**

## src/module_index.py (117 lines)

Read in full: `first_line()` (AST-based docstring-first-line extraction, fails closed to
"(unparseable)" rather than raising), and `main()` (the grouped module listing, the
stale-group-name warning, the "everything else" catch-all, and the atomic write with its exit
code gated on `silence.replace_retry`'s verdict).

Checked the specific thing this file's own docstring is proudest of — that no module count is
hardcoded in prose anywhere in the generated page or in this module's own docstring — and
confirmed the count is only ever computed live from `glob.glob` at lines 62 and 110-111.

**No defect found.**

## Summary of findings by severity

- **Confirmed defects: 0**
- **Questions worth a second pair of eyes (not filed as work orders — informational only):**
  1. `publish.py:387` (`_scan_units`) — a very long logical line assembled across multiple
     newline-less block reads can be yielded whole rather than chopped into `line_cap`-bounded
     segments at the moment a newline finally arrives; no scanning gap results, only a
     memory-bound overshoot of the stated "one block plus overlap" design. Low confidence this
     is worth anyone's time; noted for completeness per the brief's instruction to report
     anything found even as a question.
  2. `publish.py:1338` (`push()`'s commit-message builder) — assumes a fixed 3-character
     `git status --porcelain` prefix, which mis-files a renamed `src/*.py` file's name into the
     "N data/site file(s)" count instead of the "code:" list. Cosmetic only (does not affect what
     is staged, committed or pushed); not filed as a work order.

No caps/truncations violating Hard Rule 0 were found in these nine modules. No tautological or
always-true/always-false guards were found. No falsy-zero slips were found (every numeric
"found"/"next"/"score" field checked uses `is not None` or explicit arithmetic comparisons, never
bare truthiness, in the paths I traced). No swallowed verdicts were found — every gated write in
these nine modules (`docs/state.json`, `docs/index.html`, `PANTHEON.json`, `MODULE_INDEX.md`,
`registry_terminal.html`, `pages.json`, `WIKI_HOSTS.json`, `ingest_state.json`, the record
catalogue) checks the return value of its write primitive and reports the denial rather than
assuming success. No non-atomic shared-state read-modify-write was found — every write goes
through `silence.write_json`, `silence.replace_retry`, or an equivalent pid+thread-tmp-then-
replace idiom local to the module.
