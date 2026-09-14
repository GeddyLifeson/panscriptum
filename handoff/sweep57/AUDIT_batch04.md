# Sweep 57, batch 4 — audit of mutate.py, wiki_source.py, address_space.py, tiers.py, recover_folder_records.py, grounding.py, tempus.py

Scope per the run57 batch-4 brief. All seven modules read in full, top to bottom, no
sampling (Hard Rule 0 applied to the audit itself). AUDIT ONLY — no file edited, `mutate.py`
not run, `drill.py`/`verify_math.py` not run. Open queue checked first via
`workorders.open_orders()`; matches below are marked `KNOWN(<id>)` with the verified quote.

Every finding was verified against the live source at the time of this audit (2026-09-13);
line numbers are exact as of that read.

---

## src/mutate.py (3197 lines, read in full)

This module is unusually self-documented — nearly every mechanism (the lock, the sandbox,
the differential judging, the hang-confirmation, the ruled-equivalent registry) carries a
paragraph naming the incident that produced it and the order that fixed it. A fresh read found
the LIVE-TREE-REACH and SURVIVOR-MISCOUNTING questions the brief specifically asks about
already closed by code, verified below, plus a small crop of genuinely new stale citations the
existing citation-rot orders do not cover.

### Can a mutation reach the LIVE tree? — checked, and refused

`_run_mutation` (mutate.py:2106-2115) explicitly refuses a `root` that resolves to `HERE` or to
`SRC`:

```
if root is not None:
    _abs = os.path.abspath(root)
    if _abs == os.path.abspath(HERE) or os.path.abspath(os.path.join(_abs, "src")) == SRC:
        raise RuntimeError(
            "refusing to mutate %s with root=%s: that is the LIVE tree. ...")
```

The only real entry point (`_session`, via `main()`) always calls `run()` with `root=None`,
which forces `sandbox()` to build a throwaway copy (mutate.py:2167-2168:
`own_sandbox = root is None; root = root or sandbox()`). The two drill nets that call `run()`
directly stub `_run_mutation` first (per the module's own comment at :2099-2100), so no live
caller passes `root=HERE` today. `sandbox()` itself junctions `data/`/`prompts/`/`reference/`
and hardlinks per-file under `data/`, and the module docstring is candid that a junction "is a
portal, not a wall" if a future gate ever wrote through one — but every current gate command in
`GATES`/`FAST_GATES` was verified by the module's own authors not to write there. Net: the
LIVE-tree-reach question is closed by an explicit guard plus a documented, currently-true
assumption about the gates. Nothing found beyond what the code already discloses.

### Could a survivor be miscounted as KILLED? — checked, and guarded on every axis I could find

- **Baseline required, not defaulted** (`_run_mutation`, mutate.py:2130-2135): `base=None`
  raises rather than defaulting to `{}`, closing the exact "every mutant scored killed because
  `{}.get(x) is None`" failure the module's own history names.
- **Ungauged gates refused** (:2136-2142): a gate present in `gates`/`confirm` but absent from
  `base` is refused rather than silently compared against `None`.
- **Unusable (timed-out/errored) baseline gates refused** (:2148-2153, via `unusable_gates`).
- **`could_not_judge`** (:2019-2037): a mutant whose gate times out or errors is INDETERMINATE,
  never KILLED, unless `hang_confirms_a_kill` (:1827-1894) independently proves the hang against
  a fresh, in-margin baseline re-read taken at the moment of judging.
- **Baseline drift re-photographed** (`_refresh_baseline`, :2235-2325) on a configurable
  interval, with drifted windows named and every verdict reached under a stale signature listed
  by line so it can be re-attacked — the fix for the confirmed false kill of 2026-09-03
  (`escalation.py:409`, order 58a00e909217 — **KNOWN**, still open; this module's own docstring
  and the `sandbox()` docstring's `data/`-hardlinking section are the fix for it, and the order
  appears to track the residual gap the docstring itself names: a file inside a *junctioned*
  subdirectory such as `data/records/` is still live and not re-photograph-proof between
  refreshes).
- **Live-file integrity checked, not just restore** (:2470-2512): `live_before`/`live_after`
  digests bracket the whole run and a mismatch voids that target's verdicts
  (`MUTATE_TOUCHED_LIVE_TREE`, SUPERVISOR-level) rather than being folded into the kill count.

I did not find a fresh way to make a survivor read as killed; every path I traced was already
the subject of a named repair with the repair present in the code I read.

### DEFECT — three stale `file.py:LINE` citations in mutate.py's own comments, not covered by the two standing citation-rot orders

The project already has two open orders for exactly this class over `src/` broadly —
`89503c58409f` (60 sites, sweep 48) and `386c0d66e31e` (sweep 54) — and both name sites inside
`mutate.py` itself (`:731-732` and `:472-476`, both **KNOWN** and already tracked). Grepping
every `[A-Za-z_]+\.py:[0-9]+` citation in the seven files of this batch and checking each
target line turned up three more inside `mutate.py` that neither order lists:

1. **mutate.py:886** — `` `aebfcf414477` (assay.py:593, `strict=True` -> `False`) has been
   closed three times on the same reading. `` Read `src/assay.py:588-598` today: it is mid-way
   through "THE SECOND GAP, closed 2026-08-26 (order b8a17bd503d3)", about a key-filter defect —
   no `strict=True` anywhere near it. `assay.py` has no `strict` parameter of its own; the only
   `strict=True` occurrences in that file today are two `zip(..., strict=True)` calls at
   `assay.py:795` and `:877`. The citation has drifted at least ~200 lines and no longer names
   content related to the ruling it is attached to.
2. **mutate.py:1264** — `` the reap ledger added this shift named the call site,
   `drill.py:4256 -> M.reap_orphans()`. `` Read `src/drill.py:4250-4262` today: it is the middle
   of an unrelated net, `the_cap_resets_per_run` (about `local_agent.py`'s blast-radius cap),
   with no mention of `reap_orphans`. The real `M.reap_orphans()` call sites in the current
   `drill.py` are at :15214 and :15382 — a drift of roughly 11,000 lines.
3. **mutate.py:1677** — `` reporting three escapes: `verify_math.py:3639 ->
   silent:tuning.py:cloud-success` ``. Read `src/verify_math.py:3634-3644` today: it is
   "Section 19z: the fandom probe", unrelated. The check this citation is actually about —
   `"no probe anywhere in this battery writes into the live failure ledger"` — lives at
   `verify_math.py:12045` today, a drift of roughly 8,400 lines.

Why it matters: this is the same class the project has already ruled on twice over (cite by
symbol, not by line — `a09a0e003c31`, `0c7592915a48`) and has already spent two sweeps
converting sites for; these three happen to sit in exactly the file whose own docstring is the
longest sustained argument in the codebase for writing things down precisely. A reader chasing
`assay.py:593` or `drill.py:4256` to understand a ruling or an incident lands on unrelated code
and has no signal that the citation rotted.

Severity: MINOR/documentation, matching the standing rulings' own severity for this class — not
filed as a fresh top-level order here since the two open umbrella orders (`89503c58409f`,
`386c0d66e31e`) are the established place this class is tracked; recorded here as three new
sites for whichever order is next revised, per the "STILL OPEN" roster format `386c0d66e31e`
already uses.

### QUESTION — read-modify-write on `state/MUTANTS_RULED_EQUIVALENT.json` (lost-update shape)

`rule_equivalent` (:1070-1095) and `unrule_equivalent` (:1098-1114) both do
`entries = dict(ruled_equivalent(path)); entries[...] = ...; _write_rulings(entries, path)` —
read the whole registry, mutate the in-memory dict, atomically replace. `_write_rulings` is
torn-write-safe (temp file + `os.replace`) but is not a compare-and-swap against the read taken
a few lines above, so two concurrent invocations (two `--rule-equivalent`/`--unrule` calls, or
one of each) could race and one write would silently clobber the other's. This is the identical
shape to `HOSTS_ADD_LOST_UPDATE` (order 3d000c4e482f) and `STATE_LOST_UPDATE`
(26667ecd6543) elsewhere in this codebase, and it is a genuine mechanism, not a false read.

**Already found**: `handoff/sweep56/AUDIT_batch04.md` (search: "same read-modify-write shape on
`state/MUTANTS_RULED_EQUIVALENT.json`") filed this as a QUESTION rather than a DEFECT, on the
grounds that `_write_rulings`'s own docstring says it is "only ever called from the two
human-driven CLI flags, never from inside a mutation run" — a human typing one command at a
time is a much lower-probability race than the automated-writer cases the sibling orders cover.
Re-verified against the current source: still true, still unfixed, still correctly a QUESTION
rather than a DEFECT at this priority. No new information changes that judgement this round.

### KNOWN — findings already on the open queue, re-verified against current source

- **KNOWN(58a00e909217)** `MUTATION_LONG_RUN_SCORED_AN_UNKILLABLE_MUTANT_AS_KILLED` — matches
  the differential-judging-over-a-long-run / `sandbox()` `data/`-junction material discussed at
  length in the class docstrings for `sandbox()` (:1378-1449) and in `_run_mutation`'s baseline
  section (:2204-2232). The `_refresh_baseline` mechanism is the code's answer to it; the order
  stays open because the docstring itself names a residual gap (junctioned `data/records/` is
  not covered by the per-file hardlink freeze).
- **KNOWN(d2d4ff880570)** `A_TWENTY_HOUR_JOB_IS_LAUNCHED_AS_A_CHILD_OF_A_ONE_HOUR_SHIFT` —
  matches the `--detach` implementation and its own comment at :2649-2694 ("A TWENTY-HOUR JOB
  MUST NOT BE A CHILD OF A ONE-HOUR SHIFT"), which states plainly that `mutate.py` is in neither
  `overnight.STANDING` nor `ALL_JOBS`, so nothing restarts a killed pass — `--detach` mitigates
  the launch-time symptom but does not close the underlying scheduling gap the order names.
- **KNOWN(89503c58409f, 386c0d66e31e)** — stale citations at mutate.py:731-732 (verify_math.py
  :7990→142, drill.py:9604→16696 per 386c0d66e31e's own re-measurement) and :472-476
  (prose_gate.py:201→232). Re-verified: both still present and still stale in the current file.
- **KNOWN(156c2e28f823)** `CHECKS_THAT_CANNOT_FAIL_SWEEP54` — filed against
  `drill.py:_sandbox_without_its_target_refuses`, which asserts a property of
  `mutate.sandbox()`'s cleanup that cannot go red because `mutate.sandbox()` always renames the
  `mkdtemp` path away before returning; the defect lives in `drill.py`, not in `mutate.py`
  itself, but the mechanism it is testing is `sandbox()`'s rename-then-claim sequence
  (:1481-1496), so noted here as directly touching this module's contract.

### Nothing else found

The lock (`_lock_acquire`/`_lock_release`/`_hold_lock`), the ruled-equivalent registry's read
path, `reap_orphans`'s ownership-vs-age logic, `hang_confirms_a_kill`'s two-reading requirement,
and the CLI's halt/registry/detach ordering were all read in full and matched their own
docstrings against the code exactly. No fail-open path was found where the house rule is
fail-closed (`active()`, `ruled_equivalent()`, `_owner_pid()` all fail toward the safer answer,
and each says so). No caps or truncation without disclosure (`limit`/`--limit` is reported with
`mutants_attemptable` beside it; `not_attempted` sites are named in full, never counted alone).

---

## src/wiki_source.py (790 lines, read in full)

### KNOWN(e7143aba1e9a) `WIKI_SOURCE_FLOOR_REPORT_HAS_NO_CALLER`

Matches exactly: `category_floor_report()` (wiki_source.py:402-418) is defined, documented at
length as the owner-ruled "report the dropped count" mechanism, and has **no caller anywhere in
the repository** — confirmed by `grep -rn "category_floor_report"` (only the pyc cache and prior
audit files match; no live `src/` caller). `_FLOOR_APPLIED`, the account it reads, is likewise
written by every `all_categories()` walk but never read outside this dead function. The order's
second half, "`:731-737` (rank_by_size fetch)", matches `rank_by_size`'s inner `fetch()`
(wiki_source.py:731-737 in the order's numbering; :731-737 corresponds to the current
`try/except Exception: silence.note(...); return {}` inside `fetch`) — a batch that fails to
retrieve `prop=info` for its 50 titles is silently scored as size-0 for all of them, which
biases the size-ranking (Hard Rule 0's "rank, never truncate" concern) without being reported as
a partial ranking anywhere in the return value. Both halves verified against current source;
nothing new to add.

### KNOWN(89503c58409f) — two stale citations, re-verified

- wiki_source.py:450: `` matching the comment at catalogue_web.py:257-259 `` — order's measured
  actual is `catalogue_web.py:~324`.
- wiki_source.py:665: `` `catalogue_composite`'s per-category `try/except`
  (catalogue_web.py:220-224) `` — order's measured actual is `catalogue_web.py:~274-279`.

Both citations are still present verbatim in the current file at the same lines; not re-verified
against `catalogue_web.py`'s current line numbers (out of this batch's scope, and the order
already carries the measurement).

### Nothing else found

`_get`'s retry/backoff, `verify_wiki_matches`'s anti-false-positive-resolution logic,
`resolve_wiki`'s host-map-first ordering (including the two silent-failure notes for a torn
`WIKI_HOSTS.json` and for a known-but-non-fandom host), `all_categories`'s raise-don't-truncate
walk and its cache-key-includes-`hard_stop` fix, `find_categories`'s uncapped `limit=None`
default, `page_text`/`page_texts`'s per-section retry logic, `category_members`'s
raise-on-transport-failure, and `clean_titles`'s O(n) dedup were all read in full and matched
their own extensive docstrings. No cap-without-disclosure, no fail-open-where-should-be-closed,
and no lost-update RMW pattern found (this module holds no shared mutable state files of its
own; `_ALLCATS`/`_FLOOR_APPLIED` are in-process caches guarded by `_ALLCATS_LOCK`).

---

## src/address_space.py (674 lines, read in full)

### KNOWN(89503c58409f) — stale cross-file citation, re-verified

address_space.py:643-644: `` since `pipeline.py:2138` (`_phase_input("SHELFMARKS.json")`) reads
this file as a phase input and `standards.py:1177` reads it on its own clock ``. Order's measured
actual: `pipeline.py:2799` and `standards.py:1264`. Citation still present verbatim at the same
lines in the current file.

### KNOWN(386c0d66e31e) — three more, re-verified against current source

- address_space.py:477-480 (the batch-16 measurement block): still reads "TIERS.json holds 209
  rows with hyperverse 2..5, xenoverse 0..5, metaverse 0..7 and multiverse 0..167" verbatim,
  which the order records as stale against a live TIERS.json of 208/1..5/0..2/0..5/0..142. Not
  re-measured here (would require reading data/TIERS.json, out of this batch's brief, and the
  order already carries the live figures).
- address_space.py:296-298: still reads "65 an uncharted metaverse, and 16 of the 1,016
  designations" verbatim; order's measured live figures are 63 and 14.
- address_space.py:381: still reads "(see :195-200)" verbatim; the order says the actual target
  is `shelfmark()`'s own docstring (the paragraph beginning "THIS DOCSTRING SAID THE OPPOSITE FOR
  THREE SWEEPS" a few lines above `shelfmark`'s definition, not a numeric range within this
  file's own numbering scheme).

### Nothing else found

`_tier_counts`'s fail-toward-a-documented-floor-not-a-census on a bad TIERS.json read,
`FIELDS`/`WIDTHS`/`TOTAL_BITS` being derived rather than hand-typed, `pack()`'s
raise-rather-than-truncate, `assign()`'s `fit()` no-modulo fix (already the subject of order
b6474eb0a258, closed — the comment records the fix and the proof, and the finding is not live),
the `_hash_offsets()` legacy-floor mechanism, and `main()`'s write-gate (checks
`silence.write_json`'s return and exits 1 on a denied replace rather than printing "wrote" over
a no-op) were all read and matched their docstrings. No new fail-open, cap, or lost-update
pattern found. (`main()`'s SHELFMARKS.json write is a full replace of a self-contained
computation, not a merge with other writers, so no RMW risk applies to it the way it does to
`mutate.py`'s ruled-equivalent registry.)

---

## src/tiers.py (548 lines, read in full)

Run #56 is recorded as having changed this file so the "SAMPLE STACKS" panel's charted name uses
`_cut` (tiers.py:502) instead of a bare slice — confirmed present and correct in the current
source (`print(f"   {_cut(s, 26):<28}H{c['hyperverse']} ...")`), closing what was previously
order `215f9e7b86ff`'s finding. Not re-flagged.

### KNOWN(89503c58409f) — two stale self-citations, re-verified

- tiers.py:386 (in the module's own current numbering, inside the `main()` docstring comment
  about `address_space` reading `TIERS.json` at import): the order's recorded citation is
  `address_space.py:129`; measured actual `address_space.py:142` / `:161`. Present verbatim.
- tiers.py:521 (current numbering; the order recorded it at :515-516, a small drift consistent
  with intervening edits): `` "a tier that does not contain its own members is not a tier"
  (:111 and again at :156-157) `` — order's measured actual is `tiers.py:142`/`:204`/`:524`.
  Present verbatim; the self-citations `:111` and `:156-157` do not correspond to the doctrine
  sentence in the current file (line 111 of the current file is inside the module docstring's
  "THE HYPERVERSE CANNOT BE CHARTED" discussion, not the doctrine line).

### KNOWN(fe99e57e1993) `UNMARKED_NAME_CUTS_SWEEP44`

This cross-file order lists `src/tiers.py:403` among its sites. That line, in the pre-run-56
file, was almost certainly the SAMPLE STACKS name-truncation the run-56 fix (`_cut`, above)
addressed — the current `tiers.py:403` is unrelated header-printing code
(`print(f"\n{'tier':<13}...")`), consistent with the fix having landed and the line having moved.
Recorded as KNOWN/apparently-resolved for the tiers.py portion of this order; the order also
names sites in `backfill.py`, `catalogue_web.py`, `cleanup.py` and `weave.py` that are outside
this batch's scope and were not checked.

### Nothing else found

`_cut`'s deliberate marking (matching the house shape named in its own docstring),
`xenoverse_grounding`'s per-xenoverse pooling and dissent-recording, `_load_groundings`'s
documented fail-open-at-compute/fail-closed-at-publish split (verified: `chart()` proceeds on an
unreadable `GROUNDINGS.json` per its own comment, and `main()` refuses to write `TIERS.json` in
that case at :390-396 — the two halves of the split are both present and consistent with the
docstring), the containment-scan refusal at :526-532 (a nesting violation blocks the write, not
merely the print), and the write-verdict-reaches-exit-code fix at :538-543 were all read and
matched. No new fail-open, cap, or lost-update pattern found.

---

## src/recover_folder_records.py (380 lines, read in full)

### KNOWN(386c0d66e31e) — stale self-citation, re-verified

recover_folder_records.py:123: `` The comment at line 168 already says the roll is a SNAPSHOT
and the record folder is the truth ``. Order's measured actual: line 206 (`# THE ROLL IS A
SNAPSHOT; THE RECORD FOLDER IS THE TRUTH.`, recover_folder_records.py:206). Confirmed: line 168
in the current file is inside the `mapped is None` docstring comment about
`FOLDER_SOURCE_MAP.json`, unrelated. Citation present verbatim; not re-fixed since the order was
filed.

### Nothing else found

`EXCLUDED_REGISTER_SOURCES`'s narrow, documented exemption; the `is None` vs falsy distinction
for an empty `FOLDER_SOURCE_MAP` mapping (:141); the declared-vs-yielded shortfall tracking
threaded into both the console report and the record's own `provenance` string (so the record
carries its own incompleteness rather than only the console, per Hard Rule 0); the
`record_path`-not-raw-slug lookup that prefers an existing file over the un-truncated name; the
`already`-populated guard that treats an unreadable existing record as populated (fails toward
not overwriting, the safe direction here); the write-gate on both the per-record write and the
roll update (`roll.update_rows`, a compare-and-swap-style merge rather than a whole-document
land, per order f818a77293fc, already closed and reflected in the code); and the final
`return 1 if denied else 0` were all read and matched their docstrings exactly. No fail-open, no
undisclosed cap, no lost-update RMW (the roll write goes through `roll.update_rows`, which per
its own docstring merges into a freshly-read roll rather than landing a startup-time snapshot —
the RMW risk this file used to have is the one order f818a77293fc already closed).

---

## src/grounding.py (362 lines, read in full)

No `file.py:LINE` citations exist anywhere in this module (confirmed by grep) — nothing in the
citation-rot class applies to it.

### Nothing found

The `_BAD_CHARS` self-scan at import (guards against an eaten regex escape, matching the same
guard's rationale as documented); `classify_text`'s corrected whole-field ranking (no `top`
truncation by default, confirmed `most_common(top)` with `top=None` at every real call site);
`classify_source`'s `cap` parameter refusing loudly rather than truncating (`SystemExit` at
:200-204, matching the sibling fix in `feats.discover`/`genre.classify_source`); the documented
synthesis-blob exemption from the `_ORIGIN` entry filter; and `main()`'s write-gate (checks
`silence.write_json`'s return, exits 1 on denial) were all read and matched their docstrings
exactly. No fail-open, no undisclosed cap, no stale citation, no lost-update pattern (this module
writes `GROUNDINGS.json` as a full self-contained replace, not a merge).

---

## src/tempus.py (298 lines, read in full)

No `file.py:LINE` citations pointing at other modules by number exist in this file (one
citation, tempus.py:75, points at `verify_math.py:861` — see `KNOWN` below for the associated
finding, not for citation staleness; I did not check whether `verify_math.py:861` is still the
right line, as `verify_math.py` is out of this batch's scope and the order below already covers
the finding this citation supports).

### KNOWN(7099a092abd3) `BATTERY_IS_THE_ONLY_CALLER_OF_THIRTEEN_PUBLIC_FUNCTIONS`

Confirmed by grep across `src/`: `contemporaneous` and `retrocausality_beta` (both named
explicitly in the order's `where` field) have exactly one caller each outside their own module —
`verify_math.py`. `retrocausality_beta` also appears in `derivation.py:196`, but only as a
citation string inside a formula-registry dict (`Q(DERIVED, "structural constant + log2(1 +
span)", [...])`), not an actual call. `is_present_at` is in the identical position (one caller,
`verify_math.py`) though not named individually in the truncated `where` field; recorded here
since it fits the order's own description exactly.

### KNOWN — `concordance_now` dead code, already marked and closed in-source

`concordance_now` (tempus.py:146-155) has no caller anywhere in the repository (re-confirmed by
grep; only its own definition and prior audit/digest files match). This is not a fresh finding:
the function's own preceding comment block (:138-145) already states "REPORTED DEAD, NOT
DELETED (order 1a9c237dda4d, owner ruling 2026-09-08)" and gives the reasoning for keeping it
(reference data with no `SECONDS_PER_YEAR`/`C_LIGHT`-style duplication problem). Order
`1a9c237dda4d` does not appear in the current open queue, consistent with it having been closed
by this in-source marking. No action needed; recorded for completeness since the brief asks
specifically about checks/dead code.

### Nothing else found

`DEGENERATE_TIME`'s documented dead-then-revived status (re-confirmed: `verify_math.py:861`
does walk `DEGENERATE_TIME.values()` per grep, though the exact line was not re-verified — out
of scope); `apparent_lag_years`'s one-return-shape fix (both branches return the same four keys,
confirmed); `rung_description_length`/`band_resolution`'s split (confirmed real production
callers in `rigor.py`, not battery-only, matching sweep33's prior finding); and
`prescience_horizon_bits`/`retrocausality_beta`'s raise-on-non-positive-input guards were all
read and matched their docstrings. No fail-open, no undisclosed cap, no stale citation beyond
the one noted above, no lost-update pattern (this module holds no shared state files at all).

---

## Summary

| Module | New DEFECT | New QUESTION | KNOWN (re-verified) |
|---|---|---|---|
| mutate.py | 3 stale citations (886, 1264, 1677) | 1 (ruled-equivalent RMW — already found sweep56) | 58a00e909217, d2d4ff880570, 89503c58409f, 386c0d66e31e, 156c2e28f823 |
| wiki_source.py | 0 | 0 | e7143aba1e9a, 89503c58409f |
| address_space.py | 0 | 0 | 89503c58409f, 386c0d66e31e |
| tiers.py | 0 | 0 | 89503c58409f, fe99e57e1993 |
| recover_folder_records.py | 0 | 0 | 386c0d66e31e |
| grounding.py | 0 | 0 | (none — clean) |
| tempus.py | 0 | 0 | 7099a092abd3, 1a9c237dda4d (closed, in-source) |
