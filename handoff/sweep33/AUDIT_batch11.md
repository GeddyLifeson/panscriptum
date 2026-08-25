# Batch 11 — run33
Modules read: hostcheck.py (953 lines), generate.py (497 lines), onomast.py (407 lines), pantheon.py (308 lines), tempus.py (254 lines), tells.py (215 lines), catalogue_aurora.py (171 lines), resync_roll.py (81 lines)

## FINDINGS

### 1. onomast.py:356 — register_for's genre/feature voting is unreachable; every call falls back to the naive hash it was written to replace  [severity: MAJOR]
`register_for(group_id, genre_register=None, features=None)` has a documented fix: "Falls back to a hash of the group id ONLY when neither a genre nor features are known. That fallback used to be the whole function, and it produced the register that gave Alien and Doom the flowing elvish sound and denied Greek myth the classical one." But the only call site in this file's actual pipeline is:

```python
reg = register_for(v["continuity_group"])
```

No `genre_register` or `features` argument is ever passed — `v` (a `RESOLVED_ENTITIES.json` row) is never queried for either. Since both parameters default to `None`, this call always takes the `if not genre_register and not features:` branch, i.e. the pure hash fallback. Checked for other callers: `navtree.py` has its own separate, locally-defined `register_for(key)` and does not call into `onomast.py` at all. So the genre/feature-weighted logic (lines 311-334, `GENRE_WEIGHT`/`FEATURE_WEIGHT`/`FEATURE_SHIFT`) is dead code from production's perspective — every disambiguated world (Earth, Moon, Mars, etc. under the Doctrine of Carried Names) is named with the exact bug the docstring says was already fixed.

### 2. resync_roll.py:39 — unsorted `os.listdir(RECORDS)` makes the fix non-deterministic when two record files share one source  [severity: MAJOR]
The module's own docstring explains why it matches by declared `source` field rather than filename: "which is more reliable than the filename slug (slugging rules differ between the cataloguers)" — i.e. it explicitly expects that the same source can have more than one record file on disk under different slugs, a scenario documented elsewhere in this batch (`catalogue_aurora.py` uses its own `slug()`, other cataloguers use their own). When that happens:

```python
for fn in os.listdir(RECORDS):
    ...
    by_source[norm(src)] = (rec, fn)
```

`os.listdir` makes no ordering guarantee, and every other file in this batch that needs a stable order calls `sorted(glob.glob(...))` (e.g. `hostcheck.py:purge`, `catalogue_aurora.py:parse_folder`). Here, whichever of the two record files happens to be visited last on a given filesystem silently wins the dict slot and its `len(entries)` becomes the roll's new `entry_count` — the other file's data is discarded from consideration with no note, and which one wins can differ between machines or between runs after any filesystem operation that reorders directory entries. A tool whose entire job is "make the roll agree with reality again" (line 13) can write a different, unreproducible "reality" each time it runs against exactly the split-file case its own docstring calls out.

### 3. resync_roll.py:63 — a source resynced to zero entries keeps its stale "catalogued" status  [severity: MINOR]
```python
r["status"] = "catalogued" if n else r.get("status", "catalogued")
```
When `n` (the freshly-read entry count) is 0 — the exact case produced by `hostcheck.py`'s `purge()`, which empties a record's `entries` list but never touches `SWEEP_ROLL.json` — this line leaves `status` exactly as it already was, which for a previously-catalogued, now-purged source is still `"catalogued"`. The roll row ends up with `entry_count: 0, status: "catalogued"`, contradicting the file's stated purpose of making the roll "agree with reality." (If the row had no status at all, the fallback default is also `"catalogued"` — a strange default for a 0-entry source.) `entry_count == 0` is treated elsewhere in this codebase (`generate.py`'s evidence floor, `hostcheck.py`'s unassigned-source printing) as meaningfully different from a catalogued source; this line is the one place that lets the two states coexist in the persisted roll.

### 4. catalogue_aurora.py:140 — a denied write is still reported as "Wrote" in the run summary  [severity: MAJOR]
```python
written.append((r, record))
if not args.dry_run:
    import pipeline as _P
    if not _P.write_record_catalogue(...):
        print(f"      -> WRITE DENIED {source_name}; roll left untouched", flush=True)
        continue
    r["entry_count"] = len(entries)
    r["status"] = "catalogued"
```
`written.append((r, record))` runs unconditionally, before the write is even attempted. The comment immediately above this block (citing the run #25 sweep) explains in detail why `write_record_catalogue`'s return value must be checked before touching the roll row — and it correctly is, for `r["entry_count"]`/`r["status"]`. But the same discipline was not applied to `written`, so the end-of-run report:
```python
verb = "Would write" if args.dry_run else "Wrote"
print(f"{verb} {len(written)} records from Aurora XML:\n")
for r, rec in sorted(written, ...):
    print(f"  {len(rec['entries']):5d} entries (...)  {r['name']}")
```
lists a source as "Wrote N entries" in the same run whose console output, seconds earlier, printed "WRITE DENIED ... roll left untouched" for that exact source. The write's verdict is checked for the data that persists (the roll) but discarded for the summary a human actually reads to decide whether the run succeeded.

### 5. tells.py:70 — "not merely X but Y" tell fires on bare "not merely"/"not simply" with no accompanying "but"  [severity: MINOR]
```python
"not merely X but Y": r"\bnot merely\b|\bnot simply\b|\bnot just\b.{0,40}\bbut\b",
```
`|` has the lowest precedence in a regex, so this parses as `(\bnot merely\b) | (\bnot simply\b) | (\bnot just\b.{0,40}\bbut\b)`. Only the third alternative requires the "but" completion; the other two are named and intended as the "not merely X but Y" reveal construction (consistent with the sibling entry `"not only ... but also": r"\bnot only\b.{0,60}\bbut also\b"`, which correctly keeps the suffix attached) but in fact match "not merely"/"not simply" standing completely alone anywhere in the text. This skews `scan()`'s count for this one tell name upward versus what the label claims to measure — every other alternation in `STRUCTURAL`/`DISCOURSE` was checked and keeps its shared suffix inside a `(?:...)` group correctly; this is the only one with the bug.

### 6. generate.py:447 — silence-ledger location tag names the wrong line by 281 lines  [severity: MINOR]
```python
silence.note("generate.py:166")
```
This call is at line 447 (inside `main()`'s per-job except handler); line 166 is inside the docstring of `_covered()`, an unrelated function. Anyone using the silence ledger to locate where a swallowed exception in `generate.py` actually occurs would be sent to the wrong code entirely. `catalogue_aurora.py:76` (tagged `"catalogue_aurora.py:74"`) and `resync_roll.py:46` (tagged `"resync_roll.py:45"`) carry the same kind of drift on a much smaller scale (1-2 lines, plausibly from a small edit shifting the file) — noted together since they're the same defect class, but the `generate.py` one is the one actually capable of misleading a reader.

## QUESTIONS

1. **hostcheck.py — MODE_RAW hosts that refuse every request grade as "WRONG FICTION" rather than "UNREACHABLE."** In `probe()` (lines 132-140), the `EP.MODE_RAW` branch calls `EP.fetch_raw(host, names[:12])` and treats whatever comes back as a definitive rate — it can never return `rate: None`, only `rate: 0.0` in the worst case. I traced `endpoint.py`'s `fetch_raw` (out of this batch, but directly called from here): it explicitly distinguishes a real HTTP refusal (403/429/500) from a genuine absence (404/410) in which `silence.note()` tag it logs, per its own comment ("A REFUSAL IS NOT AN ABSENCE... the fix is to make the two cases legible in the ledger") — but its *return value* is `(t, None)` in both branches, so the distinction never reaches the caller. In `hostcheck.py`, a raw-mode host that refuses all 12 probed titles therefore gets `rate: 0.0`, `lift: 0.0` (since the null-rate baseline probe fails identically), and verdict `"WRONG FICTION"` — which lands it in `sweep()`'s `JUDGED` tuple, eligible for `--repair`, which can call `hosts.pop(k, None)` and permanently drop a working host that was merely being throttled or blocking bot traffic (e.g. `www.dandwiki.com`, which is hardcoded as a candidate in this same file and has a documented history of blanket 403s to bot UAs). I confirmed the **primary MODE_API path is correct**: any non-JSON response (HTML error page, JSONDecodeError) or HTTP error status raised by `urlopen` is caught by `probe()`'s `except Exception` and correctly returns `rate: None` → verdict `"UNREACHABLE — no judgement"`, which `sweep()` explicitly excludes from repair. So the specific case the brief asked about (a host that refuses every request grading as *healthy*) does not happen on either path — the MODE_RAW path's failure mode is a different misjudgement (graded *wrong* rather than *unjudged*), with real consequences via `--repair`/`--adopt --go`. This spans two files (the collapsing happens in `endpoint.py:fetch_raw`, the consequence is felt in `hostcheck.py:probe`/`score`/`sweep`), so I'm flagging it as a question rather than asserting which file "owns" the fix, since another auditor may be covering `endpoint.py` directly.

2. **onomast.py — coined designations are only checked for collision against names coined within the same run.** `name_worlds()`'s `taken` set starts empty and only accumulates names as `coin_well_formed` issues them; it is never seeded with catalogue designations that already exist elsewhere (e.g. unrelated worlds with real, non-coined names). Whether that matters depends on whether the wider catalogue namespace can collide with these coined names at all (spine-code addressing vs. bare name matching) — I don't have visibility into that from this batch. Worth confirming whether "Shelfmarks are unique" (cited in this file's own comments as one of the 39 standards) is enforced anywhere upstream/downstream of this module.

3. **catalogue_aurora.py:83-86 — cross-file dedup by (type, normalized name) silently drops later matches within a folder.** If the same homebrew element name+type legitimately appears in two different XML files under one folder (not implausible for a large homebrew corpus with overlapping or superseding files), only the first (by sorted path) is kept and the rest vanish with no count or note — unlike the rest of this file, which is careful to record what it drops (`silence.note` on a malformed file, at least). Given the project's Hard Rule 0 stance on "no caps, no smaller universe," I flag this rather than assert it's wrong, since same-name-and-type could equally mean "this actually is the same content, filed twice" — which is a legitimate reason to dedup.

## CLEAN

- **pantheon.py** — read in full. Mostly hand-authored, cited data (Zeno, Vados, Whis, Beerus, Champa, Grand Minister) plus `compute()`/`value()`/`main()`. The `Z_FIGHTERS.json` merge (`combined.setdefault(k, v)`) correctly lets `GODS` win on any name collision. No logic defects found.
- **tempus.py** — read in full, including the derivation chain `rung_description_length` -> `band_resolution` -> `prescience_horizon_bits`. Checked the apparent "missing /10" in `band_resolution`'s docstring against its actual callers (`rigor.py`, `verify_math.py`) — both divide by 10 themselves as the docstring says they should; the function is correctly per-band, not per-decimal. `is_present_at`/`concordance_now`'s "lower rung = larger now" logic checked against the `>=` comparison and is internally consistent. No defects found.
- **generate.py** — read in full beyond the one location-tag issue above (finding 6). Specifically verified per the task brief: the prose gate (`prose_gate.assert_gate_open`) is called at the very top of `main()`, before the manifest is even loaded, and any `ProseRefused` halts the run with nothing generated — there is no path from `main()` to a model call that skips it. `assert_block_complete` (Layer 4) and `unearned_instrument` (Layer 4b) are both consulted per written block in the entries loop. Retry/coverage logic for both `feats` and `entries` blocks (`_covered`, `_deed_shortfall`, `DEED_TRACE_FLOOR`) traced through several edge cases (empty first response, non-improving retry, all-entities-missing) and always resolves to either accepted-and-verified text or a loud `RuntimeError` filed to `failures.json` — never a silent partial success.
- **hostcheck.py** — read in full beyond the raw-mode question above (Question 1). The `score()`/`sweep()`/`purge()`/`roster_audit()`/`adopt()` verdict logic, the `_land()` atomic-write pattern, and the lift/baseline/aboutness veto math were all traced and are internally consistent with their extensive inline documentation.
- **onomast.py** — read in full beyond finding 1. `well_formed()`'s four mechanical constraints (echo, stutter, consonant run, consonant density, vowel run) were each traced by hand against the examples the docstring cites (Shiashiathasha, Goggoktok, Zgournazhun, Shessasha) and correctly reject them. `coin_well_formed`'s escalating-fallback logic preserves both the `well_formed` and `taken` invariants at every stage, including the final "genuinely exhausted" branch.
- **catalogue_aurora.py** — read in full beyond findings 4 and question 3.
- **resync_roll.py** — read in full beyond findings 2 and 3; nothing else found.
- **tells.py** — read in full beyond finding 5; the `_anchor()`/`_SENTENCE_START` sentence-boundary fix and the control-character self-check guard were both verified against their stated purpose and found correct.
