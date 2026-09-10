# SWEEP run54 — batch 10 audit

Modules: `src/publish.py`, `src/sweep_plan.py`, `src/scout.py`, `src/weave_index.py`,
`src/prose_gate.py` (owner-held — audited, not edited, no proposal to open `prose_enabled` or
`step4_enabled`), `src/retry_synthesis.py`, `src/descending_ladder.py`, `src/tells.py`.

All eight read in full, line by line, in the working tree at `C:\Users\imarl\panscriptum-library-kit`.
This codebase's own house style is to leave a dense trail of prior fixes in comments; where a
comment already names and fixes a defect I traced the current code and confirmed the fix holds,
rather than re-filing history as a new finding. Findings below are only things I could not find
already marked as fixed or as a kept-on-purpose decision.

---

## src/tells.py

Read in full (296 lines): the LEXICAL/STRUCTURAL/DISCOURSE pattern tables, the `_anchor` /
`_COMPILED` / `_LEX` machinery, `scan()`, `prompt_section()`, and `prompt_in_sync()`. Checked the
module's own `__main__` self-check passage against every pattern it claims should fire, and
traced `_anchor`'s `^\s*` rewrite against every DISCOURSE/STRUCTURAL entry that uses it. Confirmed
by grep that `prompt_in_sync()` — which the module's own docstring says was the "safety this
module claimed was not running" — now has a live caller (`standards.py:1128`), so that repair is
in effect, not just written down.

No findings. Clean, checked for: regex correctness against the self-test fixture, the
control-character corruption guard at the top of the file, and whether the documented
prompt-generation-vs-checker sync claim is actually wired to a caller.

---

## src/descending_ladder.py

Read in full (357 lines). This module is explicitly marked HELD by the owner (order 66f96febdb3a,
2026-09-08): built, correct, and deliberately not wired into the Reach axis pending a
re-derivation with a before/after table. Verified the arithmetic claims the docstring makes:
`PLANCK_ENERGY = PLANCK_MASS * C_LIGHT ** 2` is computed, not hand-entered; `rung_for_length`'s
table walk is correct given the length column's claimed monotonicity (traced by hand against
several `metres` values, including the domain edges at `PLANCK_LENGTH` and `DESCENDING[0][3]`);
`transgression_bits` and `shrink_report` both refuse non-positive `to_m`/`mass_kg` rather than
returning a false-lawful verdict, as claimed. Confirmed by grep that none of its seven public
functions has a live caller in `src/` (only comments/docstrings elsewhere mention them) — the
HELD status is real, not stale.

### MINOR — a factual claim in the docstring ("three lines") is now stale
**Where:** src/descending_ladder.py:50-55
**What:** The docstring says: "Excluding this file, a grep for `descending_ladder|DESCENDING|
rung_for_length|shrink_report|transgression_bits|rung_table|FOLD_RUNG|FOLD_GLYPH|
compton_confinement_energy|density_at_scale|schwarzschild_radius` returns three lines:
`derivation.py`'s `SCAN_MODULES` list, `anchors.py:43` ... and a historical note in
`secondopinion.py`."
**Why it is wrong:** Running that same grep today (excluding descending_ladder.py itself) returns
hits in **8** files, not counting the three named: `drill.py`, `scale_theories.py`, `onomast.py`,
`liveness.py`, `assay.py`, `secondopinion.py`, `anchors.py`, `tempus.py`. `derivation.py` itself
now has **zero** hits for the pattern — `SCAN_MODULES` there is built dynamically by
`_scan_modules()` walking `src/` with `os.walk`, so the literal string `descending_ladder` no
longer appears anywhere in `derivation.py`'s source; the docstring's claim about that file is
false as written today (it may have been true at an earlier revision of `derivation.py`, before
`_scan_modules()` replaced whatever hard-coded list generated it). None of the additional hits are
actual callers — I checked, and they are all comments in other modules discussing this same
HELD status, consistent with the "no live caller" conclusion the docstring draws — so the
functional finding (module is unwired) is still correct. Only the specific "three lines" citation
is stale. This is exactly the class of defect the project's own `CLAUDE.md` calls out for
`drill.py`'s "57 nets" line: a count in a doctrine comment goes stale and then gets reasoned from
by the next reader who trusts it without re-running the grep.
**Confidence:** Ran the exact grep pattern quoted in the docstring against `src/` and read the
matching lines in each file; separately confirmed `derivation.py` has no occurrence of
`descending_ladder` or `DESCENDING` and read `_scan_modules()` to see why.

---

## src/prose_gate.py (owner-held — audit only)

Read in full (538 lines): all four/five layers (`gate_open`/`step4_gate_open`, `evidence_ok`/
`floor_ok`, `assert_block_complete`/`section_shortfall`, `assert_instrument_present`/
`instrument_shortfall`, `unearned_instrument`/`cited_names_for`). Per the brief, I did not
propose opening `prose_enabled` or `step4_enabled`, and made no edits to this file.

Traced the boolean logic of `instrument_shortfall`'s being/non-being branches by hand against all
combinations of `marked`/`scored`/`excused`/`being`, and it matches the docstring's stated rule
exactly (a being-class entry needs the marker AND a score-or-excuse; a non-being entry needs the
marker OR the excuse sentence). Confirmed by grep in `generate.py` that all four gate functions
this file exports (`assert_block_complete`, `assert_instrument_present`, `cited_names_for`,
`unearned_instrument`) are actually called on the live generation path (lines 544, 552, 562-563),
so the "layer 4c is landed but the fixture proof is owed" note at lines 427-436 is an honestly
self-reported gap, not a silent one.

No new findings. One thing worth naming as a QUESTION rather than a fix: `unearned_instrument`
(line 520) extracts an entry's display name from the first line of its block and strips only
leading/trailing `*` characters (`head.strip().strip("*").strip()`) before comparing it against
`cited_names_for`'s cited-name set. If a model ever wraps the entry name in other markdown (a
header `#`, or `__underscores__`) rather than the plain `◈ NAME (...)` shape the template asks
for, the stripped name would fail to match a genuinely cited entity and the axis score would be
flagged as unearned when it was not. I could not confirm this actually happens in generated
output (not in this batch, and speculative), so I am not filing it as a defect — the entry
template in `prompts/system_style.txt` does not itself ask for markdown decoration on the name
line, so the mismatch may never occur in practice.

---

## src/weave_index.py

Read in full (721 lines): `designations()`/`continuity_of()`/`norm()`, the `_records_sig`/
`load_records` cache pair, `build()`, `staleness()`/`escalate_if_stale()`, and `main()`'s
candidate-matching and reporting loop. Specifically re-verified the `staleness()` boolean-algebra
fix documented at lines 468-496 (`stale = age_hours > STALE_HOURS`, `behind` reported separately,
not folded into the verdict) — the current code matches what the comment says it was corrected
to; I worked through the truth table by hand and it is right.

No findings. Checked for: the two-writer race on `ENTITY_INDEX.json`/`WEAVE_CANDIDATES.json` at
write time (both go through `silence.write_json` and the pair's landing is checked and reported
together, not independently); off-by-one and boundary conditions in `_records_sig`'s memo window;
and whether `main()`'s "most cross-attested entities" ranking and its stated floor
(`ranked[TOP_N-1]`) actually bound the unlisted remainder (they do, since `ranked` is sorted
descending by source count).

---

## src/retry_synthesis.py

Read in full (379 lines): `save_side`'s merge-then-CAS-write, `stranded_sources()`'s
condition-based (not cause-based) selection, `synthesise()`'s five documented drift-closures
against `pipeline.phase_synthesis` (prompt construction, transport, acceptance-gate strictness,
evidence validation before truncation, and the marked-cut helper), and `do_merge()`'s per-source
merge/skip/deny/unmerged accounting. Traced the `rank = int(band[1:]) if band != "unassayed"
else -1` / `best` selection across chunks and it correctly keeps the highest-ranked scored chunk.
Verified `do_merge()`'s exit code (`1 if (denied or unmerged) else 0`) actually reflects a
partially-applied merge, matching its own comment.

No findings. Checked for: the read-modify-write race on `SYNTHESIS_RETRY.json` (closed via
`save_side`'s reload-and-merge, matching its own docstring); whether `--merge` could clobber a
fresher on-disk record (it goes through `pipeline.write_record`, which the comment says
re-reads and merges); and whether a save denial could be reported as a landed result (it can't —
`landed` gates the per-source success print and the final summary line both).

---

## src/scout.py

Read in full (827 lines): `_mutate`'s CAS write with digest-before-read and the
unreadable/wrong-shape refusal, `verify()`'s name-hit threshold including the
`min(MIN_NAME_HITS, probeable)` floor-of-one fix and its separate zero-probeable-names branch,
`scout()`'s ranked-but-uncapped prompt sample vs. uncapped verification-against-every-name split,
and `sweep()`'s last-attempted-first rotation with its stamp-before-work / unstamp-on-no-answer
logic. Worked through `sweep()`'s `_unstamp` three-way branch (mine, someone-else's,
never-attempted) by hand against the described race window.

No findings. Checked for: the specific case the module's own docstring calls "the mirror case
`MIN_NAME_HITS` did not close" (zero probeable names) — confirmed `verify()` now reports that
case as `unverifiable` rather than an ordinary miss; and whether `_names_in`'s 4-character name
floor and `scout()`/`verify()`'s shared `len(n) > 3` probeable definition actually agree (they
do: both admit names of length ≥ 4).

---

## src/sweep_plan.py

Read in full (1,118 lines) — including this being the module whose `record()` I am calling at
the end of this audit. Traced `_shard_path`/`record()`'s per-process shard write, `_read_shards`/
`covered_by`/`missing`/`missing_detail`'s skipped-vs-added-since-vs-undetermined split, and
`frozen_plan`/`freeze_plan`'s three-way refusal (absent/unreadable/not-a-dict/missing-batches),
matching each against the order numbers cited for their fixes.

One low-confidence observation, filed as a QUESTION rather than a finding: `_shard_path(run,
batch)` (line 374) names its temp/shard file from `run`, `batch` and `os.getpid()` only — it does
not include `threading.get_ident()`, unlike the equivalent shard/lock-file helpers in
`scout.py._mutate`, `workorders.py` and `silence.py`, which were each given a thread-id fix after
a measured same-process, multi-thread filename collision (scout.py's own comment names this
history). `record()`'s own docstring frames its concurrency model purely at the process level
("sixteen subagents each running `python -c \"sweep_plan.record(...)\"`"), and I found no caller
anywhere in `src/` (including `drill.py`'s two test fixtures that touch `sweep_plan`) that invokes
`record()` from more than one thread in one process, so I could not confirm this is live rather
than academic — hence a question, not a filed defect.

---

## src/publish.py

Read in full (1,979 lines): the three-lock secret scanner (`_SECRET`/`_SECRET_ASSIGN`/entropy
gate/`_is_real_secret`/`scrub_text`/`_scrub`), the streaming line scanner (`_scan_units`/
`scan_for_secrets`), `export_root`'s throwaway-directory refusal, `sync_tree`/`prune_export`'s
live/gone/unavailable three-state classification for both directories and files, and `push()`'s
full interlock stack (ledger guard, mutation interlock read on both sides of the copy, secret
scan, fetch-rebase, push-then-confirm via `_unpushed()`). This is the most heavily
self-documented file in the batch; the large majority of what looks like a candidate finding on
first read is already named, dated and fixed in a comment beside it. Two things were not:

### MINOR — `_scrub()` does not recurse into tuples (or other non-list/dict/str containers)
**Where:** src/publish.py:346-377 (`_scrub`)
**What:** `_scrub(obj)` recurses into `dict` and `list` and redacts `str`; anything else —
including a `tuple` — falls through to the final `return obj` unchanged, so no element inside it
is walked or scrubbed.
**Why it is wrong:** The module's own docstring (line 31-33) and `_scrub`'s own docstring promise
it "refuses anything credential-shaped even if a future edit puts one in the state dict by
accident." That promise is false for a tuple: if a future `dashboard.state()` field is ever a
tuple (or set) containing a credential-shaped string rather than a list, `_scrub` returns it
untouched into the snapshot dict, and the redaction lock never sees the string at all. In
practice this is very likely caught rather than leaked — `json.dump` turns a tuple into a JSON
array in `docs/state.json`, and LOCK THREE (`scan_for_secrets(SITE)`, called from `push()` at
line 1593) reads that rendered file's actual bytes and would still flag a real secret there,
refusing the push and raising an OWNER halt (`SECRET_IN_EXPORT`) rather than silently leaking —
but that is a much louder and more disruptive failure than the quiet redaction the docstring
promises, and it is the specific "second lock catches what the first missed" design the module
already argues for keys living in dict values — the same argument was not carried through to the
container-type check itself. I could not find any current `dashboard.state()` field that is
actually a tuple (dashboard.py is outside this batch), so I cannot say this is live today; it is
a real gap in the function as written regardless.
**Confidence:** Read `_scrub`'s isinstance checks directly (dict/list/str only); confirmed
`scan_for_secrets`'s LOCK THREE reads the rendered file on disk (line 1593,
`scan_for_secrets(SITE)`) rather than the in-memory snapshot, which is why this fails safe rather
than leaking. Did not find a live tuple-valued field to prove exploitability.

### MINOR — `_scan_units`'s per-block "mid" lines are not bounded by `line_cap` when `line_cap` < the read-block size
**Where:** src/publish.py:466-510 (`_scan_units`), block-size constants at lines 462-463
**What:** `_scan_units(path, line_cap)` only chunks a logical line to `line_cap`-sized segments
when the *entire* 262,144-byte (`_SCAN_BLOCK`) read contains no newline (the `if len(parts) == 1`
branch). Any "mid" line fully contained within one block read (`for mid in parts[1:-1]: yield
lineno, mid`) is yielded whole, with no length check against `line_cap` at all.
**Why it is wrong:** The function's own docstring says it "STREAMS. Nothing here reads a whole
file, so SIZE IS NEVER A REASON TO SKIP" and frames `line_cap` as the bound on "how much of one
file is held in memory at a time." That bound only holds today because every actual caller uses
the default `max_bytes=2_000_000`, which is larger than `_SCAN_BLOCK` (262,144) — so a "mid" line,
capped at the block size by construction, can never exceed `line_cap`. If any future caller
passed `max_bytes` smaller than 262,144 (there is no guard preventing this, and the CLI/tests
already parametrize this value — `drill.py`'s seam-straddle test at line 4439 passes `cap=300_000`
as `max_bytes`), a "mid" line up to ~262 KB could be yielded and scanned as one unit against
`line_cap`'s stated, smaller promise. I confirmed by grep that no current caller in `src/`
actually passes a `max_bytes` below `_SCAN_BLOCK` (the one test that parametrizes it uses
300,000, which is still above the block size), so this does not fire today. It is a latent
precondition (`line_cap > _SCAN_BLOCK`) that is relied on but neither asserted nor documented.
**Confidence:** Traced `_scan_units`'s branch logic by hand against the block/newline splitting;
confirmed via grep (`scan_for_secrets(` / `_scan_units(` across `src/`) that every live call site
and the one parametrized drill test keep `max_bytes` above `_SCAN_BLOCK`, so this is dormant, not
firing.

### QUESTION — commit-message porcelain parsing does not account for rename lines
**Where:** src/publish.py:1662-1668 (inside `push()`)
**What:** When building the commit message from `git status --porcelain`, each line is sliced as
`ln[3:].strip().strip('"')` to get the path, which is correct for ordinary status codes (`M `,
`A `, `??`, etc.) but not for a rename line (`R  old -> new`), where `ln[3:]` yields the whole
`"old -> new"` string rather than just the new path.
**Why it might matter:** A renamed `src/*.py` file would not be recognised by
`p.startswith("src/") and p.endswith(".py")` (since the string reads `"old/path.py -> new/
path.py"`) and would instead be counted under the generic `other` bucket, producing a slightly
misleading commit-message summary (undercounting `code:` and overcounting the data/site count) on
a cycle that includes a rename. This affects only the informational commit message text, never
what is staged or pushed, so I am filing it as a question rather than a correctness finding — it
may already be judged not worth the complexity for a decorative summary line.
**Confidence:** Read the porcelain-parsing loop directly; did not construct a live rename to
observe the miscount, so this is inferred from the porcelain format rather than run.

---

## Coverage call

`sweep_plan.record('run54', ['publish.py','sweep_plan.py','scout.py','weave_index.py',
'prose_gate.py','retry_synthesis.py','descending_ladder.py','tells.py'], batch=10)` was called
after writing this file (see the coordinator summary for confirmation it returned without error).
