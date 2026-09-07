# run46 — batch 13

Read-and-report only. No source file was edited. No battery tool (`drill.py`, `mutate.py`,
`allsweep.py`, `publish.py`) and no live fetcher (`scout.py`, `backfill.py`) was run.

## Coverage

Every line of every assigned module was read, start to finish, no sampling, no caps.

| module | lines | read |
|---|---:|---|
| `src/assay.py` | 1,621 | all (read directly) |
| `src/health.py` | 1,100 | all (read directly) |
| `src/scout.py` | 809 | all (subagent, spot-verified against source) |
| `src/onomast.py` | 640 | all (subagent, spot-verified against source) |
| `src/backfill.py` | 449 | all (subagent, spot-verified against source) |
| `src/pantheon.py` | 405 | all (subagent, spot-verified against source) |
| `src/entity_match.py` | 296 | all (subagent, spot-verified against source) |
| `src/chord_field.py` | 210 | all (subagent, spot-verified against source) |
| `src/lognames.py` | 52 | all (subagent, spot-verified against source) |
| **total** | **5,582** | **all** |

`assay.py` and `health.py` were read directly, top to bottom, given the stated weight of the
former (the scoring core) and the coupling of the latter (health/preflight) into what the
batch needed cross-checked. The other seven modules were each read in full by a dedicated
subagent; every finding reported back was then re-verified line-by-line against the live
source before being trusted or filed — several were, several were folded into existing open
orders instead of refiled, and one was left out of the queue as too speculative (noted below).

## Filed this batch (worst first)

### `85873effe631` — ASSAY_NEW_TRANSPARENCY_FIELDS_HAVE_NO_TEST_NET (RUN, MAJOR)

The task brief's own description of today's `assay.py` change — `assay()` now returns
`attestation_recognised`/`attestation_sigma`/`attestation_source`, and `interval_from_hands`
now returns `hands_recognised`/`unrecognised_hands`/`covered_before_widening`/`widening_added`/
`quadrature_interval` — is accurate and every one of those fields is wired correctly and
additively in the source. What is missing is the net. `grep -c` for each of the nine field
names against the live `src/verify_math.py` (10,475 lines) returns **zero** for six of them
(`attestation_recognised`, `attestation_sigma`, `attestation_source`, `hands_recognised`,
`unrecognised_hands`) and the other three (`covered_before_widening`, `widening_added`,
`quadrature_interval`) appear only inside a *filed work order's own text* in
`state/workorders.json`, never as an assertion in `verify_math.py` itself.

Their sibling field, `covers_all_signatures` — the one the task brief names as the
already-fixed "guarantee dressed as a check" — got exactly the remedy this project's own
doctrine calls for: `verify_math.py:6946-6955` asserts it directly on two fixtures **and**
re-derives it independently ("measured, not asserted"). The nine fields added in the same
pass, for the same reason (make an unrecognised grade or Hand *speak* rather than be silently
absorbed), got the declaration and the datum but not the net. Concretely, today, a mutation
that inverted `attestation_recognised`'s polarity, swapped which floor an unrecognised
attestation substitutes, computed `unrecognised_hands` with `in HANDS` instead of `not in`, or
broke `covered_before_widening`'s pre-widening comparison would run clean through the battery
— the exact "a check that cannot fail looks exactly like a check that passed" lesson this
file's own comments repeat, now applying to fields whose entire purpose is surfacing a bad
reading. `verify_math.py` is the module the task brief itself says "asserts against this
module, so an error here is an error in every published ± in the library" — this is a real gap
in that net, on the newest and least battle-tested code in it.

Remedy is additive only: mirror the existing `covers_all_signatures` block and the tri-state
`_sigma_table_verdict` pattern already in `verify_math.py` with a recognised/unrecognised pair
for the attestation fields, a recognised/unrecognised pair for the Hands fields, and a
tight-vs-widened pair for `covered_before_widening`/`widening_added` (the existing "a WIDE
disagreement is widened until it covers" fixture already supplies the widened case; a tight
case where `covered_before_widening` is `True` and `widening_added == 0.0` is the missing
control).

### `4e5df284d5fc` — SCOUT_LOG_READ_FAILURE_TREATED_AS_EMPTY (RUN, MAJOR)

`scout.py`'s own comment at the SCOUT.json write (`:725-730`) claims "THE SHAPE IS CHECKED,
NOT ONLY THE PARSE" and that unreadable-vs-wrong-shape is now fully covered (order
`b8547f32bef0`) — but the code only extends that discipline to the *wrong-shape* branch. The
*parse-failure* branch is `except Exception: silence.note("scout.py:log-unreadable"); prev =
[]` — a plain empty list, which **passes** the very next `isinstance(prev, list)` guard three
lines below and is therefore indistinguishable from "SCOUT.json never existed." Execution
proceeds straight to `prev.append(...)` and an unconditional whole-file overwrite via `_land`,
which this module's own docstring already says is "atomic against a torn read, but blind to
another writer's read-modify-write racing this one" — no compare-and-swap.

A single transient read failure (a Windows sharing violation — the exact class this tree's
ATOMIC comments exist to name) therefore silently truncates up to 40 archived scouting cycles
down to just the current one, **permanently**: the roll-off/archive logic a few lines further
down only fires on the current (already-truncated) list, so the lost history is never
recovered from the archive either. Nothing prints, nothing notes the distinction, nothing in
the returned dict says so. Contrast the adjacent `SCOUT_ATTEMPTS.json` read (`:591-601`),
which keeps its parse failure distinguishable and prints a warning. Verified directly against
current source, not taken on the subagent's word.

Remedy: set `prev = None` on the parse-exception branch too (mirroring the wrong-shape branch
three lines below it), with a message that says "could not be read" rather than reusing the
wrong-shape branch's "is not a JSON list" text, since the two are different faults with
different remedies.

### `9fcbe25a473b` — PANTHEON_INCOMPLETE_MARKER_PRINTS_BUT_DOES_NOT_FAIL_THE_RUN (OWNER, MAJOR)

`pantheon.py`'s Z_FIGHTERS merge handles two distinct failure shapes and treats them
asymmetrically. The *total*-merge-failure branch (`:284-309`) was explicitly repaired under
order `a8eb06d38216`: it appends to `merge_failed`, calls `silence.note`, prints a labelled
failure, and the closing block (`:385-401`) forces `return 1` on it, with the comment stating
the principle in so many words — "a run that printed a ranking holding six of twenty-one
entities is not a successful run, and rc=0 is how a scheduler records it as one." The
`_incomplete` branch four lines above it, which fires when `zfighters.py` writes
`Z_FIGHTERS.json` successfully but could not carry in one named entity (`_incomplete:
["Son Goku"]`), does not get the same treatment: it prints a NOTE and `continue`s — no
`merge_failed` append, no `silence.note`, and the same closing `return 1 if merge_failed else
(0 if write_ok else 1)` is blind to it. Verified directly: `merge_failed` is populated in
exactly one place in the function, and it is not the `_incomplete` branch.

A run provably missing a named entity from the ranking — the same "smaller universe wearing
the same shape as the real one" shape this exact function's comments warn about at length for
the total-failure case — returns a clean rc=0 with only a console line, no ledger trace. Filed
as an OWNER question rather than a definite defect: whether a single, already-diagnosed
missing entity should count the same as losing the whole roster is a policy call. But the
asymmetry reads as an unfinished repair rather than a deliberate distinction, because the file
already states "a printed note is not enough, the rc must carry it too" as a named principle
one branch over. If the owner rules it should count, the fix is mechanical.

### `929622118156` — BACKFILL_SOURCE_STOPITERATION_ON_UNMATCHED_NAME (LOCAL, MINOR)

`backfill_source`'s first line, `rec = next((p, r) for p, r in records if r["source"] ==
source)`, has no default, so an unmatched `source` raises a bare `StopIteration`. The `--all`
path wraps every call in try/except (Hard Rule -1: "a source is its own area of the park") and
is explicit about why; the explicit `--source name [name ...]` CLI path (`:441-444`) has no
such wrapper, so one typo'd name in a multi-name invocation kills the whole loop after
processing (and writing side effects for) any sources that preceded it, and runs none of the
sources listed after it. `scout.py`'s own analogous lookup already supplies a default and
degrades gracefully, which makes the omission here look like a specific oversight. Verified
directly against source at both the lookup and the unwrapped call site.

### `2caa35dc6a30` — ONOMAST_MERGED_DROPS_UNSCHEMAD_PRIOR_RECORD_SILENTLY (LOCAL, MINOR)

`name_worlds`'s closing merge (`onomast.py:548-550`) filters `prior.items()` on
`isinstance(rec, dict) and rec.get("catalogue_name") and cid not in out`. A prior record that
parses fine but is a dict lacking a truthy `catalogue_name` — a hand-edited entry, or one
written before a future schema change — is silently excluded: not carried forward, not marked
retired, no note, no print. This sits immediately downstream of this same module's own
carefully distinguished missing-vs-unreadable handling in `load_onomasticon` (order
`549069e9c298`), which is what makes the absence of an equivalent guard here notable rather
than academic. Not reachable under current writers (both `onomast.main()` and
`pipeline.phase_weave` only ever write records shaped by `name_worlds` itself, which always
sets `catalogue_name`) — only a hand-edited or externally-written file would trip it.

### `371140b9fb9d` — ONOMAST_PICK_NEVER_REPEAT_GUARANTEE_UNRATCHETED (LOCAL, INFO)

`coin_name`'s inner `pick(lst, avoid=None)` — `opts = [x for x in lst if x != avoid] or lst` —
sits under a comment stating an unconditional guarantee ("Never draw the morpheme just used").
The `or lst` fallback means that if filtering out `avoid` would empty the list (only possible
when a `REGISTERS[...]` sub-list has exactly one entry equal to `avoid`), the code silently
falls back to the original list, including `avoid`, and the guarantee breaks without a signal.
Verified: every onset/mid/coda/end list across all six registers (`onomast.py:116-153`) has
4+ entries today, so this is dormant, not live — the same "constant with no ratchet" shape
flagged below for `entity_match.py` and already flagged in `assay.py` for `BAND_EDGES` /
`ATTESTATION_FLOOR`.

### `6273d7103222` — ENTITY_MATCH_STRONG_WEAK_THRESHOLD_ORDERING_UNRATCHETED (LOCAL, INFO)

`STRONG = 0.90` / `WEAK = 0.72` (`entity_match.py:184-187`) gate both inclusion (`s >= WEAK`)
and labelling (`STRONG if s >= STRONG else WEAK`) in `candidates()`. Nothing asserts `WEAK <
STRONG`; a future edit crossing them would silently relabel every WEAK-or-better candidate as
STRONG, inflating confidence in a module whose stated purpose is refusing over-confident
identity merges. Dormant today (values correctly ordered, both exercised at fixed points by
`verify_math.py` §19r) but unratcheted.

## Corroborated — already open or already fixed, not refiled

* **`845dbaec182f`** (onomast.py, OWNER) — `coin_well_formed`'s exhausted path still returns a
  name from the identical deterministic call it may have just rejected. **The order's own text
  is now stale** relative to source: it describes the pre-`sweep42-batch16` code with no
  inspection at all. The live code (`onomast.py:296-317`) *does* now inspect the fallback name
  (`well_formed` + `taken`) and report the verdict loudly via `silence.note` and a labelled
  stderr line — that half of the order's remedy option (b) is done. What remains open is the
  other half of that same remedy: "stamp the record with `coined_under: 'exhausted'` so a
  reader can see which designations came from the degraded path" — `name_worlds` still writes
  the coined string straight into `catalogue_name` (`onomast.py:512-515`) with nothing in the
  persisted record distinguishing a degraded name from a clean one. Left open rather than
  refiled or corrected in place, since the order is an OWNER ruling and this shift does not own
  it; noted here so the next reader does not re-diagnose the already-fixed half.
* **`ae25c89f0179`** / **`5d8533bc1ed6`** (onomast.py, OWNER) — `register_for`'s genre+feature
  vote is still unreachable: the only production caller, `name_worlds:512`, calls it with one
  positional argument, so the whole `FEATURE_SHIFT`/`GENRE_WEIGHT`/`FEATURE_WEIGHT` body never
  runs. Re-confirmed by repo-wide grep this shift; unchanged.
* **`bc4156603071`** (assay.py, OWNER, INFO) — `ATTESTATION_FLOOR_UNRECOGNISED = 0.30` versus
  its own comment's stated intent. Re-verified against the live table (Instrumented 0.08,
  Witnessed 0.10, Transcribed 0.20, Reconstructed 0.40, Disputed 0.55): 0.30 sits between
  Transcribed and Reconstructed, and the comment (corrected 2026-09-06, the day before this
  audit) now says so accurately. The order's own text already reflects this correction and is
  still the right home for the ruling; nothing to add.
* **`12c457975677`** (assay.py, SESSION, INFO) — `REFERENCE_JOULES` (`assay.py:195-209`) has
  no reader anywhere in `src/` (confirmed again by grep, restricted away from `data/` which is
  too large to grep in one pass). Still open, still accurate.
* **`23dbbcd656f3`**, **`d47ea56cca29`**, **`92fd876c2f0e`**, **`7099a092abd3`**,
  **`76ab006d84b8`**, **`9b3e59aeeb19`** (assay.py, various rungs) — all still describe the
  live code accurately; none needed correction. `d47ea56cca29` in particular already notes
  that `covered_before_widening`/`widening_added`/`quadrature_interval` exist "as well as a
  hang to trip over" for a future mutation re-run — consistent with, but narrower than, the
  new finding `85873effe631` above (that order is about one specific historical mutant; this
  one is about the complete absence of a net for nine fields, six of which that order does not
  mention at all).
* **`9586cdf72b82`** (backfill.py, LOCAL, MINOR) — `lead()`'s fallback path
  (`backfill.py:145-152`) can return a mid-word cut with no marker. A related concern was
  raised independently this shift (the fallback also skips the *prose* checks the main path
  applies, so on an article that is entirely template residue it could return non-prose
  as a "lead") — close enough in location and shape to the open order that filing a second one
  on the same eight lines would be queue noise rather than signal. Recorded here instead: if
  `9586cdf72b82` is worked, the fix should also confirm the fallback text is prose-shaped, not
  only sentence-terminated.
* **`5c8c8b99e655`**, **`fe99e57e1993`** (backfill.py) — unaffected by this shift's reading;
  still accurate.
* **health.py's stale line-number comment** — the `SELFTEST_SUBJECT`/`subject=` note near the
  top of the file still says `subject=` "is the half proposed to `escalation.py:248`." It is
  not a proposal, it is done, and it is not at that line: `escalation.py:305` passes
  `subject=rec.get("source")` today. This exact staleness was already noted and deliberately
  left uncorrected by `sweep45`'s batch13 audit ("comment-only, and this codebase records
  history in comments, so it is noted rather than filed"). Re-confirmed unchanged; same
  treatment.
* **`health.check_api_paths`'s retry/outcome fix (order `f366f81f6ddc`)** — confirmed FIXED.
  The live function now passes `retries` through to `feats.api` implicitly via its default and
  supplies `outcome=why` per host family, and reports `http-404` vs `network` vs "answered
  without a `query` block" distinctly rather than collapsing every failure into one message.
  Not refiled.
* **`health.py`'s `check_state()` "unreachable reachability guard"** — the dead second call to
  `batch_settled()` that a prior sweep (run35 batch6) identified as unreachable has been
  removed from the live code, not merely commented out; the current function computes `n =
  sum(1 for e in batch if not P.entry_settled(e))` directly with no dead branch behind it.
  Nothing to file.

## Examined and deliberately not flagged

* **`assay.py`'s whole layered defence around `_check_constants`, `_check_scores`,
  `_check_weights`, `axis_score`, `instrument`, `regress_test`.** Read end to end. Every guard
  traced to the specific historical failure its comment names (99.0 axis scores, negative
  weights, the halved Witnessed sigma, the M3.-90 decimal, the -30 Dexterity) checks out
  against the current arithmetic. `denom = ... or 1.0` is dead code and is *labelled* as dead
  code kept as a structural backstop rather than cited as live cover — the correct way to keep
  an unreachable guard, and the opposite of a "check that cannot fail" being passed off as
  evidence.
* **`covers_all_signatures` itself** — the remedy the task brief describes (declared as a
  guarantee, `covered_before_widening` added beside it as the real datum) is exactly what the
  live code does, and `verify_math.py` tests both the guarantee's self-consistency and the
  real datum independently. This is the positive baseline the new finding above (missing net
  for its nine siblings) is measured against.
* **`instrument()`'s six-slot Grade literal** (`["", "I", "II", "III", "IV", "V"][grade_n]`) —
  the surrounding comment calls the `grade_n <= 5` guard a bounds check rather than a live
  branch, correctly; the Ladder has eleven rungs today so it cannot fire, and the comment says
  so rather than claiming it as coverage.
* **`health.py`'s CAS-based `_flush_ledger`/`_flush_samples`, the self-test ledger split, the
  preflight stamp-write failure path.** All read end to end against their own long inline
  histories (lost-update repro, fixed-temp-name hazard, denied-replace silence). All correct as
  written; no gap found.
* **`chord_field.py` in its entirety** — inert `ADJUDICATIONS` data plus five pure, branchless
  physics functions with no loops and no guards, so no tautological check is possible there.
  Formulas checked against their docstrings (relativistic energy, Landauer bound, Kerr
  self-focusing) and are correct; `C_LIGHT`/`K_BOLTZMANN` are both live-read by `rigor.py`,
  which is also where `ADJUDICATIONS`'s shape is independently ratcheted (every key audited or
  explicitly excused) — the ratchet exists, just in a different file than the data.
* **`entity_match.py`'s `qualifier_compatible()`** — the module's central gate, traced branch
  by branch: both-`None` compatible, both-present-and-equal compatible, otherwise a named
  conflict/missing reason. A real, failable check, independently exercised by
  `verify_math.py`'s §19r Wally West fixture. A minor edge case (a name literally ending in
  `"()"` folds to an empty-string qualifier that compares as present rather than absent) was
  considered and left unfiled as too speculative to be worth queue space — it requires
  degenerate catalogue input the pipeline does not appear to produce.
* **`entity_match.py`'s `candidates()` cap discipline** — `limit=None` default, `truncated`
  explicitly reported whenever a caller-supplied limit trims the list. Hard Rule 0 compliant,
  confirmed against `verify_math.py:3125`.
* **`lognames.py` in its entirety** — six log-name constants and one `OWNER` mapping. Every
  comment matches the executable line beneath it; nothing to flag.
* **`scout.py`'s `verify()`/`probeable` logic and three-state `registered` field**, and
  **`hostless()`/`_mutate()`'s fail-closed reads** — traced branch by branch; genuinely
  failable checks, not tautologies. `hostless()`/`_mutate()` are the positive baseline the new
  `SCOUT_LOG_READ_FAILURE_TREATED_AS_EMPTY` finding above is measured against: they got the
  "unreadable is not empty" treatment the SCOUT.json write claims but does not fully deliver.
* **`backfill.py`'s honest-marking of provisional records** (`catalogued: False`, `magnitude:
  "unassayed"`, `provenance: "backfill:<host>"`) — confirmed these fields are never upgraded to
  look like real Assay data; phase 2 re-judges them. No dishonest default found.
* **`pantheon.py`'s write-gating for the total-merge-failure and denied-write cases**
  (`:265-266`, `:385-401`) — both correctly wired to the return code, per their own inline
  history (orders `a012b799a6c9`, `a8eb06d38216`). This is precisely why the `_incomplete`
  branch sitting one step above them, unfixed the same way, stood out as the finding above.
