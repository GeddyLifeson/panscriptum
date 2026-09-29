# sweep67 (run67) AUDIT batch 10

## Scope

Read-only. Every line of each module read sequentially with the Read tool. No subagents, no
pipeline phase, generate, publish, mutate, verify_math or drill was run. Scratch scripts only under
%TEMP%/aud10 (imports of `entity_match` and `rosetta`, pure functions; a corpus name scan).

| module | lines |
|---|---|
| src/publish.py | 2253 |
| src/dashboard.py | 1249 |
| src/rosetta.py | 846 |
| src/custodes.py | 731 |
| src/canon_backup.py | 561 |
| src/pick_model.py | 465 |
| src/descending_ladder.py | 362 |
| src/entity_match.py | 319 |

## Prior-audit cross-check (handoff/sweep66)

- publish.py `_package_store_facts` (sweep65 finding, closed in sweep66): still fixed (825-841).
  STANDS AS CLOSED.
- publish.py scratch `.py` under `handoff/` order: the code-side refusal (`CODE_FREE_DIRS`,
  `_is_agent_scratch`, `gitignore_lines`) is still correct. Nothing new.
- dashboard.py: movement() heal/cold-start guards, safety() absent-vs-unreadable, read-only
  exemption from halt: all unchanged and still correct. STANDS CLEAN. (But see finding 2, a CSS gap
  in the page body that sweep66 did not examine.)
- rosetta.py / navtree.py "writes without a halt check" owner question (orders 5bb12b398783,
  1e6f99e54b25, 21c075e5e2d6): NOW ANSWERED IN CODE. `_assert_not_halted` (571-595) is called on the
  `--mine` (647) and `--refine` (754) writing paths; read-only `--check`/`--probe` stay open. CLOSED
  for rosetta.
- custodes.py sweep54 item 3 / order 5bb12b398783 item 3 and order 34ec8a90c42f item 4: now decided
  and implemented (`divergence_share_defaulted`, once-per-mechanism `_transit_widening`). Threnody
  curl veto still never fires on a real being (no production `eta`), documented as open order
  f467f662be4b. STANDS AS A KNOWN OPEN ORDER, not re-filed.
- canon_backup.py:274 `prune()` no-op on `--keep 0`/negative (sweep61 question, carried through
  sweep66): FIXED. `prune()` now raises ValueError for `keep < 1` (274-276) and `main()` refuses
  with `ap.error` first (528-530). CLOSED.
- pick_model.py VRAM unit fix (`_mib_to_gb`): still in place, still correct.
- descending_ladder.py sweep66 low-confidence observation (`shrink_report` `is_descent` False when
  `from_m is None`, line 309): unchanged, still present. Carried as Question 5.
- entity_match.py: sweep66 batch 11 cleared `qualifier_compatible`'s normalised-equality gate. That
  reading is right about what the gate does and wrong about what it covers; see finding 1.

## Findings

### 1. entity_match.py:94-131, 185, 209-294 -- the continuity gate sees only a TRAILING parenthetical, and digits are fuzzy-scored; `best()` returns STRONG for different entities. MEDIUM (latent: no production caller yet)

`_QUAL` matches only a parenthetical at the end of the name. Anything else is "part of the name" and
goes to the fuzzy scorer, so the module's absolute rule ("a qualifier conflict is never overruled by
a similarity score") does not hold for a marker that is not last, or for a differing number.
Reproduced with the live module (`%TEMP%/aud10/r1.py`, `r3.py`):

    best("Adventure Time (2025) Issue 1", ["Adventure Time (2012) Issue 1"])
        -> match, score 0.9565, reason 'strong'      (qualifier_compatible -> True)
    best("Adventure Time (2025) Issue 1", ["Adventure Time (2025) Issue 11"])
        -> match, score 0.9787, reason 'strong'
    candidates("Superman (Earth-2) Prime", ["Superman (Earth-1) Prime"]) -> 'strong', 0.9474
    candidates("Wally West (New Earth) (Comics)", ["Wally West (Prime Earth) (Comics)"])
        -> 'weak' 0.8333 (the two-parenthetical form of the Wally West trap is listed, not blocked)

This is real data shape, not a contrivance: 5,609 of 282,853 corpus entry names have a
non-trailing or second parenthetical (e.g. `Adventure Time (2025) Issue 10`). Issue 1 vs Issue 11 is
the worse case, because there the identity is the digit and Dice/SequenceMatcher barely register it.
Today only `drill`, `verify_math`, `liveness`, `sevenfold`, `tempus`, `threads` mention the module
and nothing acts on `best()`, so nothing is mis-merged yet. It becomes a merge the day the second
join pass is wired.

Suggested fix: (a) apply the qualifier gate to EVERY parenthetical group (compare the ordered list of
normalised groups, not just the last); (b) add a second absolute gate: the multiset of digit runs in
the two names must be equal, before any score is computed. Add both to `verify_math` §19o/19r style
checks with the three examples above.

### 2. dashboard.py:798 (CSS) vs 986-1064 (JS) -- `.value.ok / .value.warn / .value.bad` have no style rule, so every Safety-panel severity is invisible. LOW-MEDIUM

The JS sets `class="value bad"` for the halt code, `value bad` for a DRIFTED assay calibration, a
BREACHED drill and a liveness overrun, `value warn` for an OPEN prose gate/Step-4 gate and a stale
drill, `value ok` for the healthy states. The stylesheet defines `.value` (colour `--ink-dim`) and
`.pill.ok/.low/.dry/.unknown`, `.bar>i.good/.warn/.bad`, `td.up/.down`, but no `.value.*` rule and no
bare `.ok/.warn/.bad` (grep: only `.pill.ok` at 817 and `.bar>i.*`). So "THE LIBRARY IS HALTED" and a
BREACHED net render in the same dim grey as "running -- no halt standing". The comment at 980 says the
halt is "rendered first, loud"; it is first, not loud. `publish.render_page()` reuses `dashboard.PAGE`,
so the published GitHub Pages page has the same gap.
Suggested fix: add `.value.ok{color:var(--good)} .value.warn{color:var(--warn)}
.value.bad{color:var(--bad);font-weight:600}` (the tokens already exist).

### 3. rosetta.py:305-306 -- the acquisition search is `srlimit=50` with no continuation. LOW-MEDIUM (Hard Rule 0 shape)

`scales_for` issues 31 relevance-ranked searches with a fixed `srlimit` of 50 and never follows
`continue`/`sroffset`. The comment records that 5 was raised to 50 as "audited not to truncate", but a
fixed page size is still a cut at rank 50 on a relevance-ordered list: on a large wiki, "power level",
"rank system" and "classification system" easily have more than 50 hits, and a genuine scale page
ranked 51+ (and passing the `size >= 1500` and `_SCALE_TITLE` filters) is never fetched. Ranked and
then truncated. The result is reported as "this wiki published N scales".
Suggested fix: loop on `d.get("continue")` until absent, as `feats.discover` should for its own
listing.

### 4. rosetta.py:312, 329, 662 -- exception messages cut with no marker (`str(e)[:60]`, `[:70]`). LOW

Same class this project has ruled on repeatedly for exception text (publish.py:759-769, 921-927:
"the subprocess/`e` is gone, the clipped copy is the only surviving account"). Here `failed[h]`
(662) and the `errors` entries (312, 329) are the only record of why a wiki yielded nothing, printed
by `--mine`/`--probe` as the whole reason. A 429 body or a long URL error loses its tail.
Suggested fix: drop the slices.

### 5. rosetta.py:392 -> 810-828 -- an all-tied scale is reported as "needs 4 overlapping names". LOW

`spearman` returns None when `len(pairs) < 4` OR when either side has zero variance (`dx and dy`
false). `check()` files the row as unscored either way and `main()` prints `UNSCORED (needs 4
overlapping names)` and "(fewer than four names overlap the Assay)". Reproduced (`r1.py`): 5 overlapping
names, every assay decimal identical -> `overlap: 5, rho: None`, printed as if under four overlapped.
The real cause (the Assay gives all of them the same decimal, which is itself a finding about the
Assay) is mislabelled as a coverage gap.
Suggested fix: distinguish the two Nones (return a reason, or have `check()` set `rho_reason =
"tied" | "too few"`) and word the printout accordingly.

### 6. pick_model.py:138-146 -- `save_config` leaves `config.yaml.<pid>.<tid>.tmp` in the repo root when the replace is denied or the write fails. LOW

`silence.replace_retry` returns False and never removes the temp (verified at silence.py:905-946); the
denied case is, per the function's own docstring, "the normal case on a working machine". The
sibling `publish._write_text_atomic` (1438-1473) and `silence.write_json` both delete the temp on a
denial; this one does not, and does not clean up if `f.write` raises. The stray `.tmp` sits beside
config.yaml (publish skips `.tmp`, so it is not published, but it accumulates).
Suggested fix: `os.remove(tmp)` in the denied branch and in an `except` around the write.

### 7. Stale comments contradicting or mis-pointing at the code. LOW (cosmetic)

- custodes.py:189-191: "Nothing in the tree refuses that pairing; see the order for the check that
  would." `table_faults()` (617-648) now is that check and `main()` returns 1 on a fault (727). The
  half that is still true (not wired into the battery) is not what the sentence says.
- canon_backup.py:223 "`verify()` fails CLOSED with no manifest (:312-320)" (now 360-368) and
  canon_backup.py:496 "LIKE LINE 188" (the `replace_retry` call is now line 208).
- publish.py:1566 "(publish.py:1214-ish)" for the `git add -A` line (now 1805).

## Questions (owner's call; not filed as defects)

1. rosetta.py:180 `if tabular and len(row) > 600: continue` silently drops any wikitable row over 600
   characters as "prose between tables". A bounty/power row with references and notes can be that long
   and its figure is then absent from the ground truth with no count. Deliberate parse heuristic, but
   nothing reports how many rows it skipped. Want a counter in `scales_for(verbose)`?
2. canon_backup.py:162-183 digests every file, then zips, then re-hashes the archive members against
   the FIRST digests. `data/records/*.json` is rewritten atomically by the live crawl, so a record
   replaced between the digest and the `z.write` makes verification fail ("digest differs from
   source"), the archive is deleted and the snapshot raises. Loud and safe, but a busy crawl can make
   `canon_backup_cycle` fail repeatedly for a reason that is not corruption. Hash the bytes that were
   zipped instead (hash while writing), or accept and retry?
3. entity_match.py:283-294 `best()` returns the alphabetically-first of several equal top scores
   without saying the top was tied. Two catalogue entries at the same STRONG score is an ambiguity
   the module's own purpose ("cannot merge two continuities") says should refuse. Intended?
4. pick_model.py:270-277 `weight_gb` returns 0.0 for an entry with no `size` and no parsable
   parameter count, which `resident()` then admits (0 + KV <= budget). Ollama always supplies `size`,
   so unreachable today, but an unknown weight is being treated as "fits" on a gate whose doctrine is
   fail closed. Also `--write` writes config.yaml with no halt check (rosetta's `--mine/--refine` now
   do); config.yaml is not corpus/output, so possibly out of the ruling's scope.
5. descending_ladder.py:309 (carried from sweep66) `is_descent` is `False` for `from_m=None`, while the
   invalid-input branch returns `None`; "unknown start" and "not a descent" share an answer. Module is
   held and unwired, so no reader.
6. publish.py:722-728 `standards_unavailable` is written to state.json and read by nothing
   (`dashboard.PAGE` never surfaces it, as the comment itself asks). A failed standards check on the
   published page therefore still shows "Standards not readable." only when the list is empty, which is
   not distinguishable from an unset one. Wire it into `panelStandards`?

## Cleared

- **publish.py**: `_scrub` (dict-key/tuple/set collision suffixes), per-line `scrub_text`, streaming
  `_scan_units` (block/overlap/line_cap arithmetic re-traced for lines spanning blocks and for
  over-cap lines; secret straddling a block boundary is carried), `scan_for_secrets` fail-closed
  UNSCANNABLE arm and suppressed-but-reported arm, `_is_real_secret` gate, `export_root` /
  `_is_throwaway`, `sync_tree` root classification + walk_errors hold, `prune_export` refusal-returns-None,
  root-file sweep after marker write, `_unpushed` tuple precedence at 972, `push()` ordering (ledger
  guard, mutation readings both sides of the copy, scan, add/status, stranded-commit retry, confirmation
  by `_unpushed`), `maintenance_shift_live` fail-open (deliberate, documented), one-shot verdict,
  `main()` halt re-ask per cycle and rc handling. Only the stale comment in finding 7. One non-defect
  note: `scan_for_secrets` descends `.git` (only skips its files), a per-push cost, not a fault.
- **dashboard.py**: `quotas` worst=None, `throughput` read-only URI, `_tail_match` hint ledger,
  `movement` (`hist[:-1]` baseline, reset-on-negative, numeric-`at` guard; the 2000-sample and 24 h
  bounds are a display history, argued in the file; concurrent poll read-modify-write can drop a
  sample but never corrupts, since it goes through `write_json`), `safety` absent-vs-unreadable, server
  bound to 127.0.0.1, codewatch loop. Only finding 2 (CSS).
- **rosetta.py**: `numeric_rows` first-number rule and 1000x-median cut (documented), `ordinal_rows`
  original-text offsets, `stand_rows`, `assays_by_host` partition fix, `check()` host scoping,
  `refine` counting arithmetic (kept + dropped reconciles), `MINE_FLOOR` refusal and unreadable-prior
  refusal, `--mine` write verdicts, halt check placement (writing paths only). Findings 3-5 and Q1.
- **custodes.py**: private weight table (no shared mutation), tilt/evidential arithmetic, quality map
  derived from `assay.ATTESTATION_FLOOR`, `_transit_widening` once-per-mechanism, `convene` early-return
  carries attendance, interval covers every reading by construction, zero-variance share flagged,
  veto arithmetic, `table_faults`. Finding 7 only.
- **canon_backup.py**: `members(strict)` refuses on any missing declared path, verified-by-readback
  snapshot, pid+thread stamp/temp, manifest via `write_json`, prune pair-deletion and orphan reaping by
  age, verify fail-closed on no manifest / absent members / gone files, unreadable != changed, restore
  opens source before destination and lands atomically. Finding 7 and Q2.
- **pick_model.py**: tier substring ordering (qwen3 above qwen, gemma3 above gemma, phi3.5 above phi3),
  `_mib_to_gb`, residency gate on total-minus-reserve vs free-now note, unmeasured-VRAM warning,
  `is not None` handling of 0.0. Finding 6 and Q4.
- **descending_ladder.py**: `rung_for_length` domain guards and finest-covering walk (hand-traced at
  1e6, 1e-9, sub-Planck), table lengths monotonic, `shrink_report`/`transgression_bits` input refusals,
  `NUCLEAR_DENSITY` single constant, `PLANCK_ENERGY` derived. Held/unwired by doctrine. Q5 only.
- **entity_match.py**: threshold ordering raise, empty-name/empty-pool return shape, deterministic
  sort, `limit` flags truncation. Finding 1 and Q3.
