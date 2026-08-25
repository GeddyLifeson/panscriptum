# Comprehensive code sweep — run31 — BATCH 05

Modules audited (every line read):

| module | lines |
|---|---|
| src/cascade_bridge.py | 1181 |
| src/manifest_builder.py | 478 |
| src/address_space.py | 346 |
| src/navtree.py | 272 |
| src/catalogue_codex.py | 215 |
| src/catalogue_aurora.py | 171 |
| src/compress_store.py | 65 |
| **Total** | **2728** |

Read-only audit. No files touched other than this report.

---

## Finding 1 — `assign()` silently wraps out-of-range tier indices, defeating `pack()`'s own no-silent-truncation guarantee

**File:** `src/address_space.py:251-252` (`fit()`, called from `assign()` at 254-261), vs. `pack()`'s stated contract at `src/address_space.py:147-148`.

**Claim:** `pack()`'s docstring states the module's core safety promise: *"Raises rather than truncating: a silently wrapped address would name a different world, which is the one failure mode worth being loud about."* `pack()` itself honours this — it raises `ValueError` if any field value doesn't fit its bit width (lines 156-157). But `assign()`, the function that actually produces addresses for catalogued worlds, never lets `pack()` see an out-of-range value: its local helper `fit()` pre-clamps every tier value with `% (1 << WIDTHS[field])` *before* calling `pack()`:

```python
def fit(v, field):
    return (0 if v is None else int(v)) % (1 << WIDTHS[field])
```

This is exactly the silent-wrap failure mode `pack()` exists to refuse — it just happens one call frame earlier, where `pack()`'s guard can never see it.

**Why it is wrong / concrete failure:** `WIDTHS` is fixed at import time from `_TC = _tier_counts()`, which reads `data/TIERS.json` once. `assign()` is called later (per-world, inside `main()`) using a **separately, freshly re-read** `tiers` dict (`src/address_space.py:316-322`) — not the same snapshot `_TC` came from. If `TIERS.json` is regenerated with a new, higher-indexed hyperverse/xenoverse/metaverse/multiverse between module import and the `assign()` calls (a realistic case in a long-running batch, or on a re-run after the weave discovers a new tier), the new index no longer fits the stale `WIDTHS`. `fit()` then reduces it modulo the old width instead of raising, and two genuinely different tiers alias onto the same address bits — "a silently wrapped address... name[s] a different world," which is the exact scenario `pack()`'s docstring calls the one failure mode worth being loud about.

**Severity:** major (silent data corruption of the library's own addressing scheme, contradicts a design guarantee stated three functions above in the same file).
**Confidence:** VERIFIED by tracing `fit()` → `pack()` and the two independent reads of tier data (`_tier_counts()` at import vs. the `tiers` load inside `main()`).

---

## Finding 2 — `main()`'s field/source-citation table is silently truncated and mis-paired (`zip` length mismatch)

**File:** `src/address_space.py:270-276`

**Claim:** `FIELDS` has 8 entries (hyperverse, xenoverse, metaverse, multiverse, universe, galaxy, star, planet), but `srcs` — the list of citation strings printed beside each field — has only 5 entries, left over from an earlier 5-field version of the address (hyperverse/universe/galaxy/star/planet, per the docstring's own "THE WIDTHS ARE DERIVED" section at lines 33-38):

```python
srcs = ["weave.py: 8 divisions breaks the six-degree diameter",
        "168 continuities resolved by the weave",
        "Lauer et al. 2021 (New Horizons LORRI)",
        "dwarf-dominated mean stars per galaxy",
        "Cassan et al. 2012, Nature"]
for (name, n), s in zip(FIELDS, srcs):
    print(f"{name:<14}{n:>14.3e}{WIDTHS[name]:>7}   {s}")
```

**Why it is wrong:** `zip()` truncates to the shorter iterable. The printed table silently drops **galaxy, star, and planet** entirely (3 of 8 fields never printed), and the 5 rows that do print pair the wrong field with the wrong citation: xenoverse gets "168 continuities..." (that's the multiverse count's source), metaverse gets the galaxy citation (Lauer et al.), multiverse gets the star citation, and universe gets the planet citation (Cassan et al.). Only `hyperverse`'s row is accidentally still correct.

**Concrete failure:** running `python src/address_space.py` prints a derivation table that both hides most of the address space's fields and cites the wrong source for four of the five it does show — actively misinforms a reader trying to verify the derivation the module's whole docstring is built around.

**Severity:** minor (diagnostic `main()` output only; does not affect `WIDTHS`/`TOTAL_BITS`/`CAPACITY` or any written data). But it is precisely the "field count changed, demo not updated" bug class this very file already documents catching twice (the positional `pack()` call and the `assign()` tier-stack argument, both noted in comments at lines 284-289 and 311-315) — a third instance of the same staleness, missed by those two prior fixes.
**Confidence:** VERIFIED (list-length mismatch is directly countable in source).

---

## Finding 3 — `shelfmark()`'s docstring directly contradicts its own return statement

**File:** `src/address_space.py:171-183`

**Claim:** The docstring says: *"H and X print as '?' because they are uncharted... This renders them the same way [as '?'] rather than inventing positions nobody has surveyed."* The function's actual return statement:

```python
return (f"Ω › H{f['hyperverse']} › X{f['xenoverse']} › Mt.{f['metaverse']} › "
        f"Mv.{f['multiverse']} › U-{f['universe']} › G.{f['galaxy']:x} › P.{f['planet']}")
```

prints the real integer values of `hyperverse` and `xenoverse` (e.g. `H3`, `X2`), never `?`.

**Why it is wrong:** this is a leftover docstring from before the file's own documented 2026-08-20 "CHARTED" change (module header, lines 75-105), which explicitly retired the `?`-printing behaviour once the weave started measuring these tiers. The function's own inline comment three lines below the docstring (line 181) even says outright: *"It printed '?' through two earlier passes... Neither is true any more"* — directly admitting the docstring above it is stale, without the docstring itself ever having been fixed.

**Severity:** cosmetic/minor (documentation only; the code's actual behaviour — printing charted values — is correct per the rest of the file's design). But a maintainer reading only the docstring (the normal way to understand a function) will believe the opposite of what the code does.
**Confidence:** VERIFIED.

---

## Finding 4 — Stale comment claims hyperverse/xenoverse are "NOT fields" three lines above the code that defines them as fields

**File:** `src/address_space.py:127-139`

**Claim:**

```python
# hyperverse and xenoverse are NOT fields. They are not unknown values awaiting a survey -- they
# are positions the charter declines to state, and reserving bits for them would invite filling
# them in.
FIELDS = [
    ("hyperverse", max(2, _TC["hyperverse"])),
    ("xenoverse",  max(2, _TC["xenoverse"])),
    ...
```

**Why it is wrong:** the comment is describing the module's *pre-charting* design (from before the 2026-08-20 change documented at the top of the file), where hyperverse/xenoverse were refused and printed as `?`. The code immediately below it does the opposite of what the comment says: both are listed in `FIELDS`, given real bit widths in `WIDTHS`, packed/unpacked like every other field, and (per Finding 3) printed with real numeric values in `shelfmark()`. A maintainer relying on this comment to decide whether it's safe to add a 9th field, or to remove hyperverse/xenoverse from `FIELDS` "since the comment says they aren't fields," would be acting on directly false information about the current code.

**Severity:** cosmetic/minor (doc-only).
**Confidence:** VERIFIED — comment and the immediately following code assert opposite things about the same two names.

---

## Finding 5 — `record_unrecognised()` has a cross-process lost-update race on the shared ledger's `count`/`error` fields

**File:** `src/cascade_bridge.py:504-561`, specifically the read-modify-write at 534-555.

**Claim:** The function reads `state/POOL_UNRECOGNISED.json` into `rows`, mutates one entry (`count += 1`, refreshes `last_seen`/`error`), and writes the whole dict back with `silence.write_json` (atomic replace):

```python
with _UNREC_LOCK:
    try:
        with open(UNRECOGNISED, encoding="utf-8") as f:
            rows = json.load(f)
    except Exception:
        rows = {}
    ...
    r["count"] = int(r.get("count", 0)) + 1
    rows[key] = r
    silence.write_json(UNRECOGNISED, rows, indent=1, sort_keys=True)
```

**Why it is wrong:** `_UNREC_LOCK` is a `threading.Lock`, scoped to one process. The function's own comment at lines 551-554 states plainly: *"this file is written from every process that imports `cascade_bridge` (read, pipeline, feats, overwatch), and those collide on the temp file itself."* `silence.write_json`'s atomic replace fixes the *file-corruption* half of that (no reader ever sees a torn/half-written file, and no two writers' temp files collide on the same name). It does **not** fix the *logical* race: the read-modify-write cycle above is unsynchronized across processes. Two processes hitting the same failure at nearly the same moment each read the pre-increment `rows`, each compute `count = old + 1` independently, and whichever writes last simply overwrites the other's write with the same (or a stale) value — one real occurrence is lost from the tally, silently, with no error anywhere.

**Concrete failure scenario:** worker threads in two different long-running processes (e.g. `feats.py` and `pipeline.py`, both importing `cascade_bridge`) each hit an unrecognised failure on the same bucket within milliseconds of each other. Process A reads `count: 5`, computes 6. Process B reads `count: 5` (before A's write lands), also computes 6. Both write `count: 6` (or A's write is clobbered by B's later write of a stale 6). The ledger now shows 1 fewer occurrence than actually happened. Given the module's own stated purpose — *"an unrecognised failure should be immediately investigated and resolved upon spotting it"* (owner ruling quoted at line 507) — an undercounted, intermittently-clobbered ledger can make a real, recurring provider fault look rarer or newer than it is, or (in the worst case) lose the *only* record of a failure whose `error` text differs between the two racing writes (the loser's specific error text is discarded, not merged).

**Severity:** major (silently drops data from the diagnostic ledger this file was built specifically to make trustworthy; not a hypothetical — the comment in the same function already documents that multiple processes write this exact file concurrently).
**Confidence:** VERIFIED (race is structural — no cross-process synchronization exists around the read-modify-write; only the final file write is atomic).

---

## Finding 6 — `catalogue_codex.py` / `catalogue_aurora.py`: whole-roll read-modify-write races if the "four scripts" ever run concurrently

**File:** `src/catalogue_codex.py:120-209` and `src/catalogue_aurora.py:107-159`, both operating on `data/SWEEP_ROLL.json`.

**Claim:** Both scripts (per their own comments — "Four scripts write this roll", `catalogue_codex.py:208`, `catalogue_aurora.py:158`) load the *entire* `SWEEP_ROLL.json` list into memory at start (`roll = json.load(f)`), mutate individual row dicts in place across a loop that may run for a while (parsing XML / codex text and, for `catalogue_aurora.py`, calling `pipeline.write_record_catalogue` per source), and only at the very end write the *entire* `roll` list back in one shot via `silence.write_json(ROLL, roll, ...)`.

**Why it is wrong:** `silence.write_json` makes that final write atomic *as a file operation* (no torn read), but the update it lands is a full-list snapshot taken from whenever `roll` was first loaded. If `catalogue_codex.py` and `catalogue_aurora.py` (or `catalogue_web.py` / `resync_roll.py`, the other two writers named in the comments) are ever invoked concurrently — plausible for a project explicitly designed around parallelism (per this codebase's own `use-full-machine-resources` convention) — each process's in-memory `roll` diverges from disk the moment the *other* process's write lands, and whichever process's `silence.write_json` call happens last **silently discards every row change the other process made** (its own `entry_count`/`status` updates for a completely different set of sources), because it's writing back its own stale full copy of `roll`, not just the rows it touched.

**Concrete failure:** run `catalogue_aurora.py --force` and `catalogue_codex.py` back to back with even a slight overlap window; whichever finishes writing last wins the whole file, and the other's newly-catalogued `entry_count > 0` rows revert to `0` on disk — which (per `manifest_builder.py`'s own `entry_count == 0` selection logic) would make `manifest_builder.py` treat those sources as still un-catalogued and skip them, even though real record JSON files were in fact written to `data/records/`.

**Severity:** major if the two scripts (or any pair of the four named writers) are ever run in the same window; the atomic-write fix already applied (2026-08-25, per both files' comments) addresses file corruption but not this logical race.
**Confidence:** VERIFIED that the code pattern (full-snapshot read, full-snapshot write, no locking/merge) is present in both files as described. HYPOTHESIS on whether concurrent invocation actually happens in this project's current orchestration (not visible from these two files alone).

---

## Finding 7 — `navtree.py` truncates its own audit-problem printout to 6 lines — the exact anti-pattern the file's docstring says it exists to prevent

**File:** `src/navtree.py:254-257`

**Claim:**

```python
problems = audit(data)
print(f"\nAUDIT: {len(problems)} problems")
for p in problems[:6]:
    print("   " + p)
```

**Why it is wrong:** the module's own header (lines 15-24) names, as bug #2 this file exists to never repeat: *"WORLD LISTS WERE TRUNCATED AT FORTY. One universe claimed 157 worlds and listed 40. The count in the panel was right and the bubbles were a subset, which is the worst combination: it looks complete and is not."* `problems[:6]` reproduces that exact shape in a different part of the same file: `len(problems)` (the count) is printed accurately, but the listing beneath it silently shows only the first 6 of however many problems exist. If `audit()` finds, say, 40 problems, an operator watching the console sees "AUDIT: 40 problems" followed by 6 lines and no indication that 34 more exist unlisted.

**Why it doesn't corrupt the write gate:** the write gate itself (`if args.write and not problems:`, line 259) correctly uses the full, untruncated `problems` list, so a dirty manifest is still correctly blocked from being written regardless of the print cap. The bug is confined to what the operator can *see* while diagnosing why the write was blocked.

**Severity:** major under this project's Hard Rule 0 (`[:N]` truncation of a result list is explicitly named as always-a-violation regardless of whether anything downstream also happens to be correct), though its practical blast radius is limited to console diagnostics rather than data written to disk.
**Confidence:** VERIFIED — literal `[:6]` slice on a list whose true length is reported separately and truncated in the following loop.

---

## Finding 8 (lower confidence) — `catalogue_codex.py`'s section-title matching is an unranked substring match, first-hit-wins

**File:** `src/catalogue_codex.py:130-136`

```python
for k, t in sec_by_norm.items():
    if n and (n in k or k in n):
        title = t
        break
```

**Claim:** unlike `catalogue_aurora.py`'s `sources_under()` (which was hardened in `navtree.py`'s own history — see BUGS m11 comment there — against exactly this class of accidental substring collision by requiring a `.`-anchored boundary), this loop matches a roll entry's normalized name against codex section titles by **unanchored** containment (`n in k or k in n`), and takes the *first* match in dict-insertion (i.e. document) order rather than the closest/most-specific one.

**Why it could be wrong:** two codex sections whose normalized titles both contain (or are contained by) a roll entry's normalized name would resolve non-deterministically with respect to document reordering, and — more concretely — a short source name could be swallowed by an unrelated longer section title purely because it appears as a substring (the same class of accident `manifest_builder.py`'s own comment describes happening with `"DC"` matching inside `"sword-coast-adventurer's-guide"`, and that `address.py` is on record for making that exact mistake).

**Concrete failure (hypothetical, not confirmed against real data):** if the codex ever contains two section titles where one's normalized form is a substring of the other's, or where a roll source name is a substring of an unrelated section's title, that source's entries would be silently attributed to (and catalogued under) the wrong codex section, with no ranking or warning.

**Severity:** minor (guarded by the fact this only fires when both `sec_by_norm` and roll-entry names actually collide, and the file's mechanism otherwise looks correct).
**Confidence:** HYPOTHESIS — the matching logic as written is real and unranked, but I did not have live `THE_PRIME_OMNIVERSE_CODEX.md` / `SWEEP_ROLL.json` data in scope to confirm an actual collision occurs.

---

## Finding 9 (lower confidence) — `manifest_builder.py`: non-deterministic tie-break in fuzzy record-file matching, and non-atomic manifest/report writes

**File:** `src/manifest_builder.py:90-104` (tie-break), `436-437` and `455-472` (writes).

**Claim A (tie-break):** `load_record()` ranks candidate record files by `score = abs(len(norm_fname) - len(norm_target))`, keeping the file with the lowest score:

```python
if best_score is None or score < best_score:
    best_name, best_score = fname, score
```

On an exact tie between two candidate files, the first one encountered in `os.listdir(records_dir)` iteration order wins — an order Python does not guarantee to be stable or reproducible across environments/filesystem-state changes (this file's sibling `navtree.py` explicitly documents an equivalent hazard, m41, where hash-set iteration order flipped 75 of 734 node names between two consecutive runs, and fixed it with an explicit secondary sort key).

**Concrete failure (hypothetical):** two record files whose filename lengths differ from a source's normalized name by exactly the same amount could, on different machines or after unrelated filesystem changes, resolve to different files — silently building a manifest chapter from the wrong source's catalogue entries with no warning, since `best_name`/`best_score` give no visibility into whether a tie occurred.

**Claim B (non-atomic writes):** the actual manifest (`output/index/manifest.json`, read downstream by `generate.py`) and the unassigned-sources report are both written with a plain `open(path, "w") + json.dump(...)` / `f.write(...)`, not through `silence.write_json`/`silence.replace_retry`:

```python
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"jobs": all_jobs}, f, indent=2)
```

This is exactly the truncate-then-fill pattern `silence.write_json`'s own docstring (in `src/silence.py`) says was found and fixed at twelve other call sites across ten modules for `data/` and `state/` files. `output/index/manifest.json` isn't literally inside `data/records/` or `state/`, so it falls outside the letter of the two-writer contract, but it is the job queue a downstream generation stage reads — a crash or interrupt mid-write would leave it truncated/invalid for that reader, the same hazard class the project has already paid to fix everywhere else it occurs.

**Severity:** minor/hypothesis on the tie-break (real code pattern, unconfirmed real-world collision); minor on the non-atomic manifest write (real gap, but `manifest.json` is regenerated wholesale on every run rather than incrementally updated, so the exposure window is only "process killed mid-write," not a multi-writer race).
**Confidence:** VERIFIED for the code patterns themselves; HYPOTHESIS for whether either has caused an observed incident.

---

## Summary of findings by severity

- **Major:** 4 (Findings 1, 5, 6, 7)
- **Minor:** 4 (Findings 2, 8, 9a, 9b combined as one entry)
- **Cosmetic:** 2 (Findings 3, 4)

No findings in `compress_store.py` beyond a noted-but-not-flagged hash truncation (32 hex chars of sha256 for content-addressed filenames — astronomically low collision risk, not reported as a defect).
