# AUDIT — sweep30, batch 05

Scope: `src/cascade_bridge.py`, `src/manifest_builder.py`, `src/address_space.py`,
`src/navtree.py`, `src/catalogue_codex.py`, `src/retry_synthesis.py`. Every line read
top to bottom in each file. No secrets found in any of the six files.

Severity counts: **HIGH 5, MED 4, LOW 2** (11 findings total).

---

## 1. `src/retry_synthesis.py`

### 1.1 `synthesise()` is NOT byte-identical to `phase_synthesis` and reintroduces the exact Hard-Rule-0 cap `phase_synthesis` was fixed to remove — HIGH — REPRODUCED

`retry_synthesis.py:56-60`:
```python
def synthesise(c, rec):
    """Byte-identical prompt construction to phase_synthesis, so a retried source is not
    scored by a different method than its neighbours."""
    src = rec["source"]
    sample = sorted(rec["entries"], key=lambda e: -len(e.get("description", "")))[:14]
```
Compared against `pipeline.py`'s `phase_synthesis` (`src/pipeline.py:713-800`): that function
calls `_mined_feats(rec)`, sorts feat-bearing entries first, and explicitly chunks **every**
feat-bearing entry into blocks of 14 with **none excluded** — the surrounding comment names this
exact behaviour as a prior Hard-Rule-0 violation that was deliberately fixed ("BUGS m13,
Hard-Rule-0-shaped, ruled by the owner 2026-08-24: FIX IT ALL... no feat-bearing entry is ever
excluded from nomination"). `retry_synthesis.synthesise()` never calls `_mined_feats` at all — it
sorts by raw description length and hard-truncates to `[:14]`, ignoring feats entirely and
silently reintroducing the pre-m13 cap for every retried source. The docstring's claim of being
"byte-identical" to `phase_synthesis` is false in exactly the two ways flagged as open items.
**Fix**: call `pipeline._mined_feats` and chunk feat-bearing entries the same way `phase_synthesis`
does, or explicitly document the divergence and drop the "byte-identical" claim.

### 1.2 Band-acceptance regex is deliberately-lax `ceiling_band`, not strict `clean_band` — MED — REPRODUCED

`retry_synthesis.py:73-75`:
```python
band = (got.get("magnitude") or "").strip()
m = re.match(r"^(M(?:10|[0-9]))\b", band)
band = m.group(1) if m else "unassayed"
```
This is a verbatim copy of `pipeline.ceiling_band()` (`src/pipeline.py:143-153`), whose own
docstring says: *"Deliberately laxer than `clean_band`... Acceptance is strict, clamping is
forgiving; the asymmetry is the point."* `phase_synthesis` accepts bands only through
`clean_band()` (`src/pipeline.py:137-140`), which requires `_CLEAN_BAND.fullmatch` (exact string,
nothing after). `retry_synthesis.py` uses the clamp-only regex for *acceptance*, so a value like
`"M4 (approx)"` that `phase_synthesis` would reject as `"unassayed"` is silently accepted by the
retry path as `"M4"`. **Fix**: use `pipeline.clean_band()` here instead of hand-rolling the
`ceiling_band` regex.

### 1.3 `save_side()` bypasses the project's own atomic-write contract — HIGH — REPRODUCED (by code comparison)

`retry_synthesis.py:43-47`:
```python
def save_side(d):
    tmp = SIDE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    os.replace(tmp, SIDE)
```
`SIDE` (`data/SYNTHESIS_RETRY.json`) is exactly the kind of shared state the two-writer contract
covers. The project's own `silence.write_json()` (`src/silence.py:250-280`) exists specifically to
fix this pattern: it names the temp file with **PID + thread id** so two writers never collide on
the same temp path, and it calls `silence.replace_retry()` so a Windows `PermissionError` from a
concurrent reader holding the file open (documented at `silence.py:223-229` as an already-measured
hazard) gets a short backoff instead of an unhandled crash. `save_side()` uses the fixed-name
`path + ".tmp"` idiom the project explicitly retired ("m100... eighteen truncate-then-fill
writes... closed the fixed-temp-name collision race", `cascade_bridge.py:531-538`) and has no
retry around `os.replace`, so a reader (or a second `retry_synthesis.py` invocation) holding the
file open at the wrong instant raises unhandled. `save_side` is called once per successfully
retried source inside `main()`'s loop (`retry_synthesis.py:154-155`), so this window is hit on
every source, not just once at exit. **Fix**: replace `save_side` with
`silence.write_json(SIDE, d, indent=2, ensure_ascii=False)`.

### 1.4 `do_merge()` — clean, already fixed

The docstring/comment block at `retry_synthesis.py:108-119` reads as if it's describing a
currently-live bug ("this loop... wrote the OLD entry list back whole... performed by the one
caller that had opted out of the guard"), but the code beneath it (`retry_synthesis.py:120`)
already calls `PL.write_record(path, rec)` — the sanctioned two-writer-contract merge path — and
correctly treats a `False` return as "leave the record alone, don't count it as merged"
(`retry_synthesis.py:121-124`). Read `pipeline.write_record` (`src/pipeline.py:504-560`) to
confirm it re-reads and merges on drift rather than overwriting; it does. **This is a historical
post-mortem comment describing a fixed incident (run #26), not a live bug** — worth flagging only
because a future reader skimming the comment could mistake it for an open issue.

---

## 2. `src/catalogue_codex.py`

### 2.1 `load_register_index()` ignores the `source` field and causes real cross-source misattribution — HIGH — REPRODUCED (with live data)

`catalogue_codex.py:104-112`:
```python
def load_register_index():
    with open(REGISTER, encoding="utf-8") as f:
        reg = json.load(f)
    idx = {}
    for item in reg:
        key = norm(item.get("name"))
        if key and key not in idx:
            idx[key] = item
    return idx
```
`LOCAL_REGISTER.json` (14,576 rows) carries a `source` field on every row (e.g.
`{"name": "A Cold Wind", ..., "source": "Deep Magic: Winter Magic", ...}`), but `load_register_index`
keys purely on the normalized `name`, globally, first-occurrence-wins. Measured directly against
the live file: **453 normalized name keys collide across genuinely different `source` values,
covering 993 register rows** out of 13,602 unique keys. Then ran `parse_codex()` against the real
codex at `C:\Users\imarl\Documents\5e Character Builder\custom\THE_PRIME_OMNIVERSE_CODEX.md` and
matched every section's "Full Contents" element against this index exactly as `main()` does:
4,401 elements resolve to a register hit, and **229 of those have genuinely different candidate
sources**, so `main()`'s choice of description is an accident of file order, not of relevance to
the section being catalogued. Concrete, severe examples reproduced live:

- Section **"The Player's Handbook (Core Rules)"**, element **"Dwarf"** — the register's first
  match for that name is `5th Edition D&D x Final Fantasy XIV - Classes an[d...]`, whose `desc`
  reads *"In the land of Norvrandt, the Lalafells came to be known as Dwarves..."* — a totally
  unrelated crossover homebrew — instead of the actual Player's Handbook race description that
  also exists in the register under the same key.
- Same section, element **"Elf"** — first match is `KibblesTasty's Races` (an undead-elf homebrew
  variant), not `Player's Handbook`.
- Section **"Eberron: Rising from the Last War"**, element **"Repeating Shot"** — first match is
  `Unearthed Arcana: The Artificer Returns`'s generic item text, not the actual Eberron RFTLW
  magic weapon entry that also exists in the register.

This directly contradicts `load_register_index`'s only caller comment
(`catalogue_codex.py:148-149`, "Prefer the register's transcribed text... rather than inventing a
description") — the text preferred is frequently the wrong source's text, which reads as
"transcribed and correct" while actually being cross-contaminated. **Fix**: key
`load_register_index` (or filter at lookup time in `main()`) by `(norm(name), source)` or at least
prefer a candidate whose `source` string matches/overlaps the codex section `title`, falling back
to the honest "no transcribed description" message used for a true miss rather than a wrong-source
hit.

### 2.2 Title-matching in `main()` is first-match, not closest-match — LOW — HYPOTHESIS, not currently triggered

`catalogue_codex.py:130-135`:
```python
for k, t in sec_by_norm.items():
    if n and (n in k or k in n):
        title = t
        break
```
This is the same shape of bug `manifest_builder.load_record()` documents having fixed elsewhere in
this codebase ("DC" matching "Sword Coast Adventurer's Guide" by luck of dict/listdir order,
`manifest_builder.py:85-89`) — plain substring containment with first-match-wins instead of
closest-match. Checked live: **zero roll entries with `entry_count == 0` currently have more than
one candidate codex section**, so this is dormant against the current roll, not a reproduced
misattribution. Worth the same closeness-ranking fix as `load_record()` uses, as a preventive
measure, but not urgent.

### 2.3 Otherwise clean

`parse_codex()`'s regex block-splitting and `Full Contents:` parsing were traced against the real
file and produce sane `(type, name)` pairs; no entry cap anywhere (dedup is by `seen` set on
normalized name, not a count limit); `main()` gates on `write_record_catalogue`'s return value
before marking a roll row catalogued (run #25 fix, present and correct); the roll write uses
`silence.write_json` (atomic, present and correct).

---

## 3. `src/manifest_builder.py`

### 3.1 `manifest.json` is written with a bare truncating `open(...,"w")`, not `silence.write_json` — MED/HIGH — REPRODUCED (by code comparison; not a read-modify-write, but the same shared-file-torn-read hazard the project has fixed everywhere else)

`manifest_builder.py:434-437`:
```python
out_path = os.path.join(HERE, cfg["paths"][out_key])
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"jobs": all_jobs}, f, indent=2)
```
`output/index/manifest.json` is read by `generate.py` via `load_json()` (`src/generate.py:45-50`),
which does a plain `json.load` with **no exception handling** — a reader that lands mid-write sees
a truncated file and crashes with `JSONDecodeError`. `generate.py` itself already documents the
correct pattern for this exact class of shared file at `generate.py:53-58` ("ATOMIC: catalog.json
and failures.json are rewritten repeatedly across an hours-long generation run while estate.py and
catalog.py read them; a truncate-then-fill here hands those readers an empty or half-written
file... `silence.write_json`"). `manifest.json` is the same kind of shared file (rebuilt by
re-running `manifest_builder.py` while a long `generate.py` run may be reading it) and was not
fixed alongside its siblings. **Note**: this is a non-atomic *overwrite*, not literally a
read-modify-write (no read happens here) — flagging the "known open item" description as slightly
imprecise, but the underlying hazard (crash-on-torn-read for a long-lived concurrent reader) is
real and directly comparable to the bug class this project has fixed at a dozen other sites.
**Fix**: `silence.write_json(out_path, {"jobs": all_jobs}, indent=2)`.

The `output/index/unassigned_sources.md` report (`manifest_builder.py:455-456, 463-464`) has the
same raw-write pattern and is read by `estate.py:243-255`, but that reader only calls
`os.path.getsize()` on the `.md` file rather than parsing its content, so the practical exposure
there is a momentarily-wrong byte count, not a crash — noted as LOW, not raised as its own finding.

### 3.2 `pack_feats()` — clean, verified Hard Rule 0 compliant

Read the whole function (`manifest_builder.py:146-217`) end to end: an oversized entity is sliced
across as many blocks as its feats require (`manifest_builder.py:200-214`) and every slice is
appended to `blocks`; nothing is dropped, and a single feat larger than the whole budget still gets
its own block per the explicit comment at lines 207-210. This is genuine pagination, not
truncation-with-a-cap.

### 3.3 `--pilot N` — explicit opt-in sampling, not a Hard Rule 0 violation

`manifest_builder.py:389-390` does `sorted(build_pool, key=...)[:args.pilot]`, but this only fires
behind an explicit `--pilot` CLI flag documented in the module's own usage banner as "small
manifest, N cheapest sources" for piloting — an intentional, visible, user-requested subset, not a
silent default cap on a roster.

---

## 4. `src/address_space.py`

### 4.1 `shelfmark()`'s docstring and its own module-level design comment both claim H/X print as `'?'` — the code does not; it prints real numbers — HIGH — REPRODUCED

`address_space.py:171-177`:
```python
def shelfmark(addr):
    """The charter's own notation. H and X print as '?' because they are uncharted.

    Part Two is explicit that the Custodes "considered guessing a form of lying", and the charter's
    worked citation for Son Goku prints H? and X? for exactly that reason. This renders them the
    same way rather than inventing positions nobody has surveyed.
    """
```
and the return statement two lines later:
```python
return (f"Ω › H{f['hyperverse']} › X{f['xenoverse']} › Mt.{f['metaverse']} › " ...)
```
Live check:
```
>>> shelfmark(pack(hyperverse=3, xenoverse=2, ...))
'Ω › H3 › X2 › Mt.5 › Mv.97 › U-11 › G.64 › P.1'
```
It prints `H3`/`X2`, not `H?`/`X?`. The same contradiction runs through the module-level comment
block at lines 127-129 ("hyperverse and xenoverse are NOT fields. They are not unknown values
awaiting a survey... reserving bits for them would invite filling them in") — yet `FIELDS`
(`address_space.py:130-139`) lists `"hyperverse"` and `"xenoverse"` as the first two real,
bit-width-assigned fields, and `_tier_counts()` (`address_space.py:106-116`) reads real
per-source `hyperverse`/`xenoverse` values out of `data/TIERS.json`. Checked the live file: of 209
sources, hyperverse values are `{4: 146, None: 53, 5: 6, 2: 2, 3: 2}` and xenoverse values include
`{0: 146, None: 53, 1: 2, 2: 2, ...}` — real, varying, charted data, including a
`hyperverse_contested_by` list on at least one row showing genuine dispute between grounding
theories. So the code's actual behaviour (chart H/X from real per-source data, when available) is
almost certainly the *intended*, later design — but the docstring and the "NOT fields" comment
describing the earlier "leave them as '?'" design were never updated to match, and now flatly
misdescribe what a reader will see on the page. A maintainer trusting the docstring would believe
`shelfmark()` never emits a real hyperverse/xenoverse number; it always does when `TIERS.json` has
one. **Fix**: rewrite the `shelfmark()` docstring and the lines 127-129 comment to describe the
current charted-when-known behaviour (and decide/document what should print when
`TIERS.json` has `None` for a source, since `unpack`'s numeric field will print `0` in that case,
not `?`, which is a separate small correctness question worth a look).

### 4.2 Module-header bit-width table is stale — LOW — REPRODUCED (documentation only)

`address_space.py:26-27`:
```
    [ hyperverse | universe | galaxy | star | planet ]
         3 bits     5 bits    38 bits  27 bits  1 bit     = 74 bits, 10 bytes
```
lists only 5 fields and claims 74 bits / 10 bytes. Live computation from the actual `FIELDS`/
`WIDTHS` (8 fields: hyperverse, xenoverse, metaverse, multiverse, universe, galaxy, star, planet)
gives **89 bits / 12 bytes**, and universe alone is 6 bits (`1 << 6` needs 6 bits), not the 5 shown.
This predates the "CORRECTED against Part Two" xenoverse/metaverse/multiverse addition documented
immediately below it (`address_space.py:75-105`) and was never updated. Purely a documentation
staleness issue — `main()`'s printed output (`address_space.py:264-279`) computes the real numbers
correctly at runtime. (Matches a prior sweep's independent finding, sweep29/AUDIT_batch07.md
§3.2/#7 — reconfirmed still present.)

### 4.3 `citation_card()`'s decimal formatting has no upper clamp — MED — REPRODUCED (independently, matches prior sweep29 finding)

`address_space.py:206`:
```python
f"𝔄 {band}" + (f".{int(round(decimal*100)):02d}" if decimal is not None else "")
```
`citation_card("Test", 12345, band="M4", decimal=0.996)` prints `"𝔄 M4.100"` — a malformed
three-digit decimal — because nothing clamps `decimal` below 1.0 before formatting. Already found
and reproduced independently by sweep29/AUDIT_batch07.md §3.1; reconfirmed live in this pass with
the same result. Not fixed since that report.

### 4.4 `citation_card()` and `seed_from_card()` have zero callers anywhere in the tree — MED — REPRODUCED

`address_space.py:186` (`citation_card`) and `address_space.py:216` (`seed_from_card`). Searched
all of `src/*.py` (every module, not just this batch) plus `handoff/`, `docs/`, `reference/`,
`site/`: the only hits for either name are their own definitions in `address_space.py` and two
prior audit reports discussing them — no production caller anywhere. `map_seed()` (the function
`seed_from_card`'s own docstring says to prefer *over*, `address_space.py:236`) IS used elsewhere
(`burgs.py`, `derivation.py`, `navtree.py`, `pipeline.py`, `profile.py`, `render.py`,
`verify_math.py`), so the intended replacement never actually got wired in anywhere, and the
"prefer `seed_from_card()`" docstring note is aspirational, not descriptive of current usage. This
is exactly the "dead code with zero callers" category the audit brief calls highest-value: either
this is genuinely unused surface area that should be wired into whatever downstream consumer
prints/generates a citation card, or it should be removed. Given §4.3's live bug sits inside this
exact unused function, it's also currently untested by any real call path.

### 4.5 Otherwise clean

`pack()`/`unpack()` round-trip verified live and raise (not silently wrap) on an out-of-range
field; `assign()` reads real per-source tier data and hashes the remaining fields deterministically
from the designation; `SHELFMARKS.json` write uses `silence.write_json` (atomic, correct).

---

## 5. `src/navtree.py`

No new findings. Full read top to bottom. The three historical bugs the module's own docstring
describes (unreachable hyperverse branch, 40-world truncation, invisible sourceless branches) are
all verifiably absent from the current code: world listing has an explicit "No cap" comment
(`navtree.py:99`) and the loop iterates every entry in `worlds.items()`/`sources.items()` with no
slicing anywhere in the file. The `m41` register/grounding tie-break
(`navtree.py:162-168, 178-190`) correctly uses `(count, name)` as a deterministic sort key rather
than the previously-broken `max(set(...))`. `audit()`'s roll-up invariants
(`navtree.py:210-223`) are real structural checks, not tautologies, and `main()` refuses to write
(`navtree.py:259-267`) unless `audit()` returns zero problems. The write at `navtree.py:263` uses
`silence.write_json`. **Clean.**

---

## 6. `src/cascade_bridge.py`

### 6.1 A parsed-but-unparseable cloud reply is a completely silent, unrecognised failure — bypasses the entire pool-failure disposition system this file exists to build — HIGH — REPRODUCED (by code tracing)

`cascade_bridge.py:1057-1066`:
```python
if pinned:
    _clear(pinned.bucket)
answered = box["answered"]
...
got = _extract_json("".join(out))
if got is None:
    return None
```
When the stream completes with **no** `type: "error"` event (`box["failed"]` stays `False`), the
bucket is marked healthy via `_clear()`, and only *then* is the accumulated text run through
`_extract_json()`. If the provider's reply has no parseable JSON in it — the module's own docstring
calls this an expected, common cloud-model failure mode ("Cloud models wrap JSON in prose or a
fence far more often than a schema-constrained local one") — `_extract_json` returns `None` and
`_ask_call` returns `None` with **zero** trace anywhere: no `silence.note`, no
`record_unrecognised`, nothing in `POOL_UNRECOGNISED.json`, nothing in the metrics ledger beyond
`"ok": False`. Every one of the elaborate, heavily-commented dispositions built into the
`box["failed"]` branch above (lines ~995-1055: permanent-bury / recognised-transient /
`record_unrecognised` catch-all) is completely bypassed, because from the stream's point of view
nothing failed — it produced *something*, just not valid JSON. This is precisely the class of bug
`record_unrecognised` and its owner ruling ("an unrecognised failure should be immediately
investigated and resolved upon spotting it," `cascade_bridge.py:504-511`) exist to close, and it
directly contradicts this same module's own opening docstring: *"A reply that does not validate is
a failure, not a result -- which is the rule this project keeps having to relearn."* Every caller
of `cascade_bridge.ask()` (`chain.py`, `ingest_doc.py`, `magnitude.py`, `pipeline.py`, `read.py`,
`standards.py`, `verify_math.py`) sees this indistinguishably from "no bucket was available" —
there is no way downstream to tell "provider is down" from "provider answered garbage."
**Fix**: when `_extract_json` returns `None` after a stream that did *not* set `box["failed"]`,
route it through the same disposition logic as a failure — at minimum `record_unrecognised(pinned.bucket, "unparseable reply: " + preview)` — since a bucket that keeps answering with unparseable text is exactly the kind of thing this ledger is supposed to surface, not a bucket that should stay marked healthy indefinitely via `_clear()`.

### 6.2 Every named pool-failure disposition IS exhaustive — verified clean

Traced the `box["failed"]` branch fully (`cascade_bridge.py:995-1056`): by the point this code
runs, `pinned` is always non-`None` (the function already returned `None` earlier if it wasn't), so
the three-way `if / elif / elif` (permanent 401/402/403 or `permanent_words` → `_bury` /
`exhausted or named_transient` → recognised, pass / else → `record_unrecognised`) is exhaustive —
no failure text can fall through all three arms unrecorded. This is the part of item 6 in the audit
brief that is **not** a bug; §6.1 is a different, upstream gap the same doctrine misses. Also
verified: `dead_forever()`'s proof-cache is correctly keyed on the proof file's mtime rather than
memoised for process lifetime (already fixed per its own "run #29, batch 05, reproduced" comment —
confirmed present and correct in current source, not a live bug); `record_unrecognised` writes via
`silence.write_json` under `_UNREC_LOCK` (correct); `_bury`'s "no `_DEAD = {}` guard" UnboundLocalError
trap is genuinely absent from current code (confirmed by reading — no such guard line exists).

### 6.3 No Hard Rule 0 violations, no secrets

All `[:N]` slices in this file are diagnostic-text previews (300/400-char error-message truncation
for the ledger, `selftest()`'s 12-line model preview) — none of them touch a roster, page list, or
ordered listing that the pipeline depends on. No API keys or secrets are embedded; `permanent_words`
and `prov.get("api_key")` are pattern/field names, not values.

---

## Summary table

| # | File | Finding | Severity | Status |
|---|------|---------|----------|--------|
| 1.1 | retry_synthesis.py:56-60 | `synthesise()` drops feats-first ranking and reintroduces the pre-m13 flat `[:14]` cap `phase_synthesis` was fixed to remove | HIGH | REPRODUCED |
| 1.2 | retry_synthesis.py:73-75 | Band acceptance uses lax `ceiling_band`-style regex instead of strict `clean_band` | MED | REPRODUCED |
| 1.3 | retry_synthesis.py:43-47 | `save_side()` uses fixed-name temp + unguarded `os.replace`, bypassing `silence.write_json` | HIGH | REPRODUCED |
| 1.4 | retry_synthesis.py:94-127 | `do_merge()` comment reads like a live bug but code already uses `PL.write_record` correctly | — | Clean (stale-sounding comment only) |
| 2.1 | catalogue_codex.py:104-112 | `load_register_index()` ignores `source`, causing real cross-source description misattribution (453 colliding keys / 993 rows; 229 live ambiguous codex elements) | HIGH | REPRODUCED |
| 2.2 | catalogue_codex.py:130-135 | Title match is first-match not closest-match (same shape as a bug already fixed elsewhere in this codebase) | LOW | HYPOTHESIS, not currently triggered |
| 3.1 | manifest_builder.py:434-437 | `manifest.json` written with bare `open(...,"w")`, not `silence.write_json`; `generate.py` reads it unguarded | MED/HIGH | REPRODUCED (comparison) |
| 3.2/3.3 | manifest_builder.py | `pack_feats` and `--pilot` verified Hard-Rule-0 compliant | — | Clean |
| 4.1 | address_space.py:171-183, 127-129 | `shelfmark()` docstring + design comment claim H/X print `'?'`; code prints real charted numbers | HIGH | REPRODUCED |
| 4.2 | address_space.py:26-27 | Module-header bit table stale (5 fields/74 bits vs. actual 8 fields/89 bits) | LOW | REPRODUCED (docs only) |
| 4.3 | address_space.py:206 | `citation_card()` decimal has no clamp; `decimal=0.996` prints `"𝔄 M4.100"` | MED | REPRODUCED |
| 4.4 | address_space.py:186, 216 | `citation_card()`/`seed_from_card()` have zero callers anywhere in the tree | MED | REPRODUCED (dead code) |
| 5 | navtree.py | Full re-read, no findings | — | Clean |
| 6.1 | cascade_bridge.py:1057-1066 | Unparseable-but-not-error-flagged cloud reply returns `None` with zero trace, bypassing the entire failure-disposition system | HIGH | REPRODUCED |
| 6.2 | cascade_bridge.py:995-1056 | Failure disposition tree is otherwise exhaustive | — | Clean |
| 6.3 | cascade_bridge.py | No Hard Rule 0 violations, no secrets | — | Clean |

**Totals: HIGH 5 (1.1, 1.3, 2.1, 4.1, 6.1) · MED 4 (1.2, 3.1, 4.3, 4.4) · LOW 2 (2.2, 4.2)**
