# Batch L4 — run35 — address_space.py / roll.py / resync_roll.py / tiers.py / navtree.py / endpoint.py

Eleven orders worked. Seven fixed, one dead-code finding confirmed but deliberately left for an
owner call, one disproved-as-currently-scoped (the real fix is outside this batch's files), and
**one incident**: this batch accidentally destroyed `data/SWEEP_ROLL.json` twice while verifying
a fix, and both times recovered it. That incident is reported in full below because it is more
important than any single order.

## THE INCIDENT — `data/SWEEP_ROLL.json` was overwritten twice during verification, and had no backup

`roll.py`'s `exclude(name, note, rows=None)` accepts a `rows=` argument that looks like a safe
sandbox for testing — pass your own list, get your own answer back — but the function still
calls `silence.write_json(ROLL, rows, ...)` against the **module-level, hardcoded** `ROLL` path
whenever `changed` is true, regardless of what `rows` was. The first time this batch called
`roll.exclude()` with a throwaway `rows=[{"name": "X", ...}]` to sanity-check the fix for
11020c99f0f9, it silently overwrote the real `data/SWEEP_ROLL.json` — 216 real sources — with
that one-row test fixture. **No backup of this file existed anywhere** (`state/backups/` only
ever held `.presilence` copies of `.py` files, never `data/`).

Recovery: `data/records/*.json` is canonical (216 files, one per source, each carrying its own
`source` name and `entries` list), so entry counts and the full source list were rebuilt
directly from disk — nothing was guessed. The one field records don't carry is *exclusion
status*, so the eight sources actually marked out-of-scope were identified from two independent,
dated, already-written owner rulings: `handoff/AUTONOMOUS_PLAN.md` §6b.2 (2026-08-20 — HAWX,
Heaven's Lost Property, major live-action Disney films, Twilight Imperium, all confirmed
`entries: 0`) and `HANDOFF.md`'s 2026-08-25 entry (the four `dandwiki` sources — Dr. Firestorm's
Engineering Corps, Mage Hand Press, Savant, Yorviing's Arcane Grimoire — whose entry counts,
425/22/8/478, match `data/records/*.json` exactly). The reconstructed file's notes say plainly
that they're a reconstruction citing which document and ruling they come from, rather than
pretending to be the lost original wording. A copy was saved to
`state/backups/SWEEP_ROLL.json.reconstructed-20260826` immediately after rebuilding it — the
backup this file should have had from the start.

Then, while writing this batch's `checks_L4.py`, the **same mistake happened a second time**
using the exact same `rows=` footgun in a standalone test for the same order — confirming the
hazard is real and easy to re-trigger, not a one-off. Caught immediately (the `roll now: N/1`
line in the test's own printed output was the tell) and restored from the just-made backup
within the same turn. `checks_L4.py`'s test for 11020c99f0f9 now also monkeypatches `roll.ROLL`
to a temp path before calling `exclude()`, with a comment warning the next person off the same
trap, and every other live-file test in this batch (`resync_roll.py`) was run only against
files under `tempfile.TemporaryDirectory()`.

**`data/SWEEP_ROLL.json` currently holds 216 reconstructed rows and should be spot-checked by
the owner against their own memory of the roll** — the entry counts and source list are exact
(machine-verified against `data/records/`), but the exact original phrasing of the eight
exclusion notes is not recoverable and was written as a cited paraphrase instead.
`roll.exclude()`'s `rows=` hazard itself was not fixed (out of this batch's ordered scope) and
is worth its own order.

## 05e21ca7f404 — FIXED — `navtree.py`'s audit findings were truncated on screen and recorded nowhere

Verified against source: `audit()` (navtree.py:210-224) returns a list of every containment
problem; `main()` printed `f"AUDIT: {len(problems)} problems"` truthfully, then `for p in
problems[:6]:` — so a tree with 7+ problems showed a correct count above a silently short list,
and `NAVTREE.json` is only ever written when `problems` is empty, so a broken tree's findings
existed nowhere but that scrolled console. Fixed: removed the slice (prints every problem now),
and added an unconditional `silence.write_json` to a new `state/NAVTREE_AUDIT.json`
(`{count, problems}`) on every run, including a clean run (which correctly records `{count: 0,
problems: []}` rather than leaving a stale file from the last broken run). Verified: `python
src/navtree.py` runs clean today (0 problems, 734 nodes), and `state/NAVTREE_AUDIT.json` now
holds the matching `{"count": 0, "problems": []}`; pyflakes and a clean-interpreter
`spec_from_file_location` load both pass.

## 06ab9dec6fb6 — FIXED — `tiers.py` imports `silence` before the `sys.path.insert` that resolves it

Verified against source: line 100 was `import silence`, line 103 was the `sys.path.insert`
three lines later — dead for that import, matching the proof's own live repro
(`ModuleNotFoundError` from a clean interpreter). Fixed: moved `import silence` below the
`sys.path.insert`, matching `rosetta.py`/`hosts.py`. Verified: the same clean-interpreter
`spec_from_file_location` load that used to raise now succeeds; pyflakes clean.

## 11020c99f0f9 — FIXED — `roll.py`'s `exclude()` had two indistinguishable silent-no-op paths

Verified against source exactly as reported: an already-excluded source given a corrected
`note` set `r["note"]` in memory but never flipped `changed` to `True`, so the file was never
rewritten and the correction was discarded; a `name` matching no row fell through the loop
returning the same `False`. Fixed: the matching row is now found once via `next()`; the write
now fires whenever status *or* note actually changed; and an unmatched name now raises
`ValueError` naming the source rather than returning a silent `False`. See THE INCIDENT above
for how this order's own verification went wrong the first time, and how `checks_L4.py`'s test
for it is now written safely.

## 18649050748c — FIXED — `tiers.py` printed only 6 of the "13 unaddressed shelves" its own docstring names as the finding

Verified against source: `for s in unaddressed[:6]:` (line 311) against a docstring explicitly
calling the full list "the honest residue" of the analysis. Fixed: removed the slice. Verified:
`python src/tiers.py` now lists all 13 current unaddressed sources by name.

## 229259ca01f4 — FIXED (deleted) — `endpoint.py`'s `exists_raw()` has no callers anywhere

Verified: repo-wide grep (`src/`, `handoff/`, `docs/`, `reference/`, `registry_terminal/`) finds
only the definition and prior audit reports referencing the finding, never a call. `hostcheck.py`
(lines 136, 247) and `feats.py` (line 604) both call `fetch_raw()` directly instead of this
2-line wrapper. No `__all__`, no CLI entry, no JS bridge references it. Per this batch's
dead-code standard (verify reachability across the *whole* repo, delete only if unambiguously
unreachable and nothing outside `src/` could call it) — this cleared the bar where
596493b0b139 (below) did not, so it was deleted rather than left standing. Verified: pyflakes
clean, clean-interpreter import succeeds, `hasattr(endpoint, "exists_raw")` is now `False`.

## 596493b0b139 — LEFT OPEN (reported, not deleted) — `citation_card()`/`seed_from_card()` dead-code finding confirmed, deletion declined

Verified: repo-wide grep (including `handoff/`) confirms zero callers of either function outside
their own definitions and prior audit prose. **Not deleted**, unlike 229259ca01f4 above, because
this one does not clear the same bar: `seed_from_card()`'s own docstring says `map_seed()` should
be preferred "over" it, framing it as a documented, not-yet-adopted alternative rather than
orphaned code, and `citation_card()` carries a known, unfixed decimal-clamp bug (sweep33 #7,
`decimal=0.996` → `"100"` instead of a two-digit field) that would need a ruling on whether to
fix-then-keep or delete-and-drop, either of which is a judgment call this batch was told not to
make unilaterally. Left standing for the owner; flagged in `checks_L4.py` so a future deletion
pass re-confirms reachability first rather than trusting this note indefinitely.

## b3da16ddfe64 — FIXED — `roll.py`'s `SWEEP_ROLL.json` writer was the only one of five missing `ensure_ascii=False`

Verified against source: `roll.py:98` (now within `exclude()`) called
`silence.write_json(ROLL, rows, indent=2)` with no `ensure_ascii` argument, while
`resync_roll.py`, `recover_folder_records.py`, `catalogue_aurora.py` and `catalogue_codex.py` all
pass `ensure_ascii=False` at their equivalent call sites. Fixed: added `ensure_ascii=False`.
This call site is also the one this batch's own accident (see THE INCIDENT) exercised for real —
the reconstructed 216-row file confirms the option now round-trips real non-ASCII characters
(en/em dashes in source names) without escaping.

## b9fe73c30bd2 — FIXED — three stale numeric `silence.note` tags in `address_space.py`

Verified against source exactly as reported: lines 84/128/342 carried `"address_space.py:69"`,
`"address_space.py:112"`, `"address_space.py:293"` — all 15-49 lines above the `except` blocks
that actually raise into them — while line 358 already used the correct symbolic form,
`"address_space.py:tiers"`. Chose **stable content labels over fresh line numbers**, per this
run's standing instruction that a new number just rots again on the next edit: `84 →
"address_space.py:continuity-groups"` (guards `_continuities()`'s `CONTINUITY_GROUPS.json`
read), `128 → "address_space.py:tier-counts"` (guards `_tier_counts()`'s `TIERS.json` read — kept
distinct from the pre-existing `:tiers` tag, which guards a *different* `TIERS.json` read inside
`main()`), `342 → "address_space.py:worldseeds"` (guards `main()`'s `WORLDSEEDS.json` read).
Verified: all four `silence.note()` tags in the file are now distinct, content-based strings;
pyflakes and clean-interpreter import both pass.

## c170b202b0d6 — FIXED — `resync_roll.py` let `entry_count: 0` coexist with `status: "catalogued"`

Verified against the report's reasoning and against current source (the OUT_OF_SCOPE guard from
the 2026-08-25 fix is already in place around this line, so the exact line number has moved, but
the rule itself — `"catalogued" if n else r.get("status", "catalogued")` — is unchanged and
exactly as described): a source resynced down to zero entries (the `hostcheck.purge()` scenario
named in the order) kept whatever status it already had, letting a purged, previously-catalogued
source persist as `entry_count: 0, status: "catalogued"` indefinitely. Fixed: the rule is now a
real three-way — an owner exclusion is left alone; `n > 0` sets `"catalogued"`; `n == 0` sets a
new `"uncatalogued"` status rather than preserving history. Verified end-to-end against isolated
scratch roll/record files under `tempfile.TemporaryDirectory()` (real data never touched for this
test): a row with `entry_count: 50, status: catalogued` whose record now has 0 entries correctly
resyncs to `entry_count: 0, status: uncatalogued`; an out-of-scope row with 12 real records on
disk is left untouched; an unaffected row is untouched. `python src/resync_roll.py --dry-run`
against the real (now-reconstructed) roll reports 0 drift, which is expected since the
reconstruction was built directly from the same record files.

## 3a48ca598e7f — FIXED — `navtree.py` imports `silence` before the `sys.path.insert` that resolves it

Same defect class and same fix as 06ab9dec6fb6, in the sibling file: `import silence` at line 30
sat three lines above `sys.path.insert` at line 33. Moved it below. Verified: clean-interpreter
`spec_from_file_location` load succeeds; pyflakes clean; `python src/navtree.py` still runs
end-to-end (734 nodes, 0 audit problems).

## e3a69ceb5857 — DISPROVED AS SCOPED / LEFT OPEN — real fix is outside this batch's owned files

The order names two siblings of `address_space.py` (already fixed, confirmed printing
`TOTAL_BITS`) still restating the address as "74 bits": grep found them at `derivation.py:333`
and `profile.py:20`. **Neither file is in this batch's owned list** (L4 owns `address_space.py`,
`roll.py`, `resync_roll.py`, `tiers.py`, `hosts.py`, `navtree.py`, `endpoint.py`, `address.py`,
`genre.py`, `grounding.py`). Left open per this run's rule that a fix outside the owned set gets
reported, not attempted. Note for whoever does own it: by the time this batch finished,
`profile.py:20` had *already* been corrected by a concurrent worker (now reads "the 89-bit
shelfmark") — only `derivation.py:333` ("74 bits total.") still needs the same "print
`TOTAL_BITS`, don't restate the number" treatment.
