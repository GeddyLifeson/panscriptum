# Batch 15 audit — run #25

Files: `src/wiki_source.py`, `src/derivation.py`, `src/rosetta.py`, `src/address.py`,
`src/render.py`, `src/profile.py`, `src/resync_roll.py`. Every line of every file read end to
end. All quoted line numbers verified against the files as they stand on disk right now.

---

## (a) THE HEADLINE QUESTION — does `wiki_source.py:352`'s `hard_stop=6000` explain the 17.2%
red "every source is fully catalogued" standard (DC 0.5%, Thomas 1.2%, SpongeBob 1.7%)?

**VERDICT: NO, not for the Persons numerator that standard actually measures. It is a real,
live, latent Hard Rule 0 cap, but it is not what is currently producing DC/Thomas/SpongeBob's
catastrophic numbers. Those three are stale records from before a DIFFERENT cap
(`MAX_PER_SOURCE`, already removed from `catalogue_web.py`) was fixed, and simply have not been
re-catalogued since.**

Chain of evidence, all VERIFIED by running real queries against the live wikis and reading
`data/COMPLETENESS.json` / `data/records/`:

1. `all_categories(hard_stop=6000)` (`wiki_source.py:352-389`) is only reached through
   `discover_categories()` (`:392-406`), which is itself only reached from `find_categories()`
   (`:409-436`) as a **supplement** to a fixed list of eight direct category-title probes
   (`CATEGORY_PROBES`, `:311-331`) that are queried by exact title (`Category:Characters`,
   `Category:People`, ...) and are **not** subject to `hard_stop` at all — MediaWiki answers a
   direct `list=categorymembers` query on an exact title regardless of how many other
   categories the wiki has.
2. `category_members()` (`:520-544`), the function that actually harvests the page titles once
   a category is chosen, has **no cap of its own** — `limit=None` means it pages via
   `cmcontinue` until MediaWiki itself says there is no more continuation. So once a category is
   found (by either path), the harvest of its members is already uncapped.
3. Live-queried `dc.fandom.com`: `Category:Characters` exists and has **33,619 direct (ns0)
   pages** (`categoryinfo`, confirmed live). It is matched by the very first entry in
   `CATEGORY_PROBES["Persons..."]` (`"Characters"`), so `find_categories` returns it via the
   **direct-probe path**, never needing `discover_categories`/`all_categories` at all. The same
   held for SpongeBob (`Characters`: 2,809, `People`: 1,031) and Thomas the Tank Engine
   (`People`: 2,571 — its `Characters` category is a near-empty meta-category with only 6
   pages, but `People` is also in the fixed probe list and catches it). **All three franchises'
   Persons roster is reachable through the uncapped, hard_stop-independent direct-probe path.**
4. Read `data/COMPLETENESS.json` and `data/records/dc.json` directly: DC's current on-disk
   record is **still exactly 377 total entries / 163 persons** — the identical number
   `completeness.py`'s own docstring (lines 11-19) cites as the **`MAX_PER_SOURCE=320`-era**
   baseline (`"dc.fandom.com Category:Characters 33,615 pages catalogued 377 1.1%"`).
   `catalogue_web.py` now raises `SystemExit` if `MAX_PER_SOURCE` is set to anything but `None`
   (confirmed reading `catalogue_web.py:187-190`) — the per-source ceiling that caused the
   historical 377-entry catalogue **has already been removed from the code**. DC has simply
   never been RE-catalogued since that fix landed; its record on disk predates the fix.
5. Contrast case, same live file: **Marvel** — the one giant franchise that HAS been
   re-catalogued post-fix (30,207 entries, matching `CLAUDE.md`'s own count of the corpus max)
   — sits at **21.5% coverage** (22,235 persons / 103,607), an order of magnitude above DC's
   0.48%, SpongeBob's 1.7%, and Thomas's 1.2%. That gap is the signature of "fixed but not
   re-run" vs. "already re-run," not of a live enumeration cap, because the SAME hard_stop=6000
   sits in front of Marvel's even-larger category list and did not stop Marvel from reaching
   21.5%.

**So what IS the hard_stop cap actually doing, and does it matter at all?** Yes — it is a real,
currently-live Hard Rule 0 violation, just not the one explaining this specific standard's
numerator. VERIFIED live: after the `_META_CATEGORY` meta-category filter, `dc.fandom.com` has
**10,460 distinct categories with ≥40 pages** — 4,460 more than the 6,000-item cap.
`list=allcategories` is confirmed alphabetical (my manual sort of the raw API response matched
the API's own paging order exactly), and the cutoff at item 6,000 lands at `"Joseph
Sulman/Penciler"` — meaning **every category from roughly "Joseph S..." through "Z..." (~43% of
DC's qualifying categories) is never even fetched**, let alone keyword-matched. This can never
touch Persons on DC (caught by the direct probe), but it silently starves
`discover_categories()` for any canonical class — Places, Factions, Vessels & Things, Powers,
Events, Media — whose real category names (1) don't appear in the eight-item
`CATEGORY_PROBES` list for that class and (2) sort late in the alphabet on a wiki this large. It
will also matter on any wiki, of any size once past 6,000 qualifying categories, whose Persons
category itself is NOT one of the eight probed names (an idiosyncratic wiki that calls its cast
something `CATEGORY_PROBES` doesn't guess) — for such a wiki the Persons roster too would depend
entirely on the capped discovery path.

**What the uncapped implementation needs:** not a bigger number — the same fix
`category_members()` already has one function below it. Replace the `while len(out) <
hard_stop:` loop condition with `while True:` and rely solely on the existing `if not cont:
break` (the natural end-of-continuation signal MediaWiki itself provides). `hard_stop` should be
deleted entirely, matching the pattern the file's own `category_members()` docstring at line
523 already argues for ("Hard Rule 0: a cap on a category listing is a truncation... MediaWiki
returns categories ALPHABETICALLY").

`data/completeness.py`'s remedy text is exactly right for the practical next step: DC, Thomas,
SpongeBob (and by extension every source whose `COMPLETENESS.json` row still matches an old
`MAX_PER_SOURCE`-era count) need `catalogue_web.py --recatalogue --shortfall 100`, largest gap
first — **this is an owner/operator action item, not a code bug**, separate from the genuine
`hard_stop` cap fix above.

---

## (b) Every other cap in this batch, cited

- **`rosetta.py:194`** — `srlimit=5` in `scales_for()`'s `SCALE_QUERIES` loop (28 queries per
  wiki, 5 search hits kept per query before the `_SCALE_TITLE`/size filter). **[KNOWN —
  NEXT_STEPS.md §2F]**
- **`rosetta.py:239` (`verify_wiki_matches`-style, but actually in wiki_source.py:239)** — see
  below; not part of this file. (Cross-checked — no additional numeric cap in `rosetta.py`
  beyond the one above; the `len(out) >= 8` guard at `:169` and `>= 8` checks at `:207/213/315`
  are quality FLOORS — refusing to score with too little data — not truncations of a larger
  universe, so not Hard Rule 0 violations.)
- **`wiki_source.py:352`** — `all_categories(hard_stop=6000)`. Detailed above. **[KNOWN —
  NEXT_STEPS.md §2F — but this run adds the concrete live measurement: DC has 10,460 qualifying
  categories, 4,460 over the cap, cutoff lands at "Joseph Sulman/Penciler."]**
- **`wiki_source.py:239`** — `verify_wiki_matches()`'s `srlimit=8`. NEW, not previously listed.
  This is a confidence check ("does this wiki plausibly contain the source"), not a roster
  harvest, and it deliberately only needs a handful of hits to test for a distinctive word —
  arguably not a Hard Rule 0 violation in spirit, but it is a numeric limit on a MediaWiki
  `list=search` call and belongs in the inventory the task asked for. UNVERIFIED as a defect
  (functions as designed); flagged for completeness only.
- **`wiki_source.py:392-406` `discover_categories(min_pages=40)`** — NEW observation, not a
  slice/limit but a **floor**: any category holding fewer than 40 pages is invisible to
  discovery on every wiki, forever, regardless of `hard_stop`. A character who exists only in a
  genuinely small, real category (e.g. a 12-member "Founding Titans" category) and is not
  separately tagged into the wiki's broad Characters/People category would never be surfaced by
  the discovery path. Distinct from Hard Rule 0's "truncate a listing" pattern (this is "ignore
  a whole listing under a size floor"), but has the same practical effect of erasing part of the
  real universe. UNVERIFIED as currently costing real entities (most named characters are also
  tagged into the broad Characters category and are caught by the direct probe instead), but
  worth the owner's attention since it compounds with the `hard_stop` gap on large wikis.
- **`wiki_source.py:439-467` `page_text(max_chars=900)` and `:547-564` `extracts(...,
  chars=700)`** — per-PAGE prose truncation (not a roster truncation). Explicitly reasoned about
  in the file's own docstring (fetching whole pages costs ~420KB/article across tens of
  thousands of pages). This is truncating the evidence text handed to the model for one entity,
  not deciding which entities exist, so it does not fit Hard Rule 0's "smaller universe" framing
  the same way the roster caps do. Noted for completeness, not flagged as a new violation.
- No other numeric `limit=`/`[:N]`/`hard_stop=` caps found in `derivation.py`, `address.py`,
  `render.py`, `profile.py`, or `resync_roll.py` — those five files contain no roster/listing
  enumeration at all (derivation.py is a static dependency ledger; address.py does string
  matching against a fixed small JSON; render.py draws SVGs from an already-materialized tree;
  profile.py encodes/decodes a fixed-width string; resync_roll.py reconciles two files already
  on disk). `address.py:127` `slugify()`'s `[:60]` is a filename-length safety cap on a single
  generated slug, not a data truncation — not a Hard Rule 0 finding.

---

## Other findings, by lens

### 4. Two-writer contract violations

- **`rosetta.py:364-366` and `:377-378`** — direct `open(path, "w")` + `json.dump` on the
  shared `data/ROSETTA.json` (and its `.raw.json` sibling) in `main()`'s `--mine` and `--refine`
  branches:
  ```python
  for path in (OUT, OUT.replace(".json", ".raw.json")):
      with open(path, "w", encoding="utf-8") as f:
          json.dump(out, f, indent=1, ensure_ascii=False)
  ```
  and
  ```python
  with open(OUT, "w", encoding="utf-8") as f:
      json.dump(out, f, indent=1, ensure_ascii=False)
  ```
  Truncate-then-fill on a shared data file; the module's own comment at `:361-363` says this
  file "already discarded a good 3,514-row mine once" from exactly this class of hazard, then
  the code goes on using the unsafe pattern anyway. Fix is `silence.write_json(path, out,
  indent=1, ensure_ascii=False)`. **[KNOWN — NEXT_STEPS.md §3]**

- **`resync_roll.py:33-68`** — unguarded read-modify-write on `data/SWEEP_ROLL.json`. The write
  at `:68` is now atomic (`silence.write_json`, confirmed reading `silence.py:250-287`), but the
  read at `:33-34` and the write at `:68` are two separate operations with no lock across them,
  and the module's own docstring says four other cataloguers (`catalogue_web.py`,
  `catalogue_aurora.py`, `catalogue_codex.py`, `recover_folder_records.py`) can all write the
  same file concurrently. The atomicity fix stops torn/truncated reads; it does not stop a
  lost-update if another writer lands between this script's read and its write. The docstring
  ("safe to run at any time and changes nothing else about the roll") does not distinguish
  atomicity from race-freedom. **[KNOWN — NEXT_STEPS.md §3, "five writers"]**

- **`resync_roll.py:68`** — `silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)`'s
  **return value is never checked**. `write_json` returns `False` on a persistent lock
  (confirmed reading `silence.py:267-268,287`), and on that path this script still prints
  `"Fixed N roll entries..."` and the summary counts as though the write landed, when the file
  was never actually updated. VERIFIED by reading both call site and the documented return
  contract; this specific call site is not named in NEXT_STEPS.md's existing "audit every
  ignored `write_json` return" list (`navtree.py:263`, `catalogue_codex.py:203`, `scope.py:119`)
  — this is a new instance of the same generalized, already-flagged lesson.

### 6. Comments/docstrings that contradict their code

- **`resync_roll.py:14`** — "It is safe to run at any time and changes nothing else about the
  roll." As above, "safe to run at any time" reads as a race-freedom claim the code does not
  back up — the read-modify-write window is real and the docstring doesn't say so. **[KNOWN]**

### 3 / caps-adjacent, structural

- **`derivation.py:476-477`** —
  ```python
  SCAN_MODULES = ["assay", "feats", "cosmography", "propagation", "descending_ladder",
                  "scale_theories", "chord_field", "resonance", "tempus", "ledger", "rigor",
                  "custodes", "weave", "onomast", "worldseed", "address_space", "genre",
                  "profile", "tiers", "grounding", "sevenfold", "burgs"]
  ```
  `pantheon.py` and `zfighters.py` are absent. VERIFIED both exist and both hold module-level
  UPPERCASE dicts that are exactly the shape `scan_constants()` is built to find: `GODS = {...}`
  in `pantheon.py:50` and `ROSTER = {...}` in `zfighters.py:53`. Both are free-parameter data the
  "where constants live" report in `derivation.main()` silently never shows a reviewer.
  **[KNOWN — NEXT_STEPS.md §3]**

### Minor / dead code

- **`rosetta.py:394`** —
  ```python
  assays = {k: v["result"]["decimal"] + P.__dict__.get("_x", 0)
            for k, v in json.load(open(path, encoding="utf-8")).items()
            if v.get("result") and v["result"].get("decimal") is not None}
  ```
  `P` is the imported `pipeline` module. VERIFIED by grep: `pipeline.py` never defines, sets, or
  documents an attribute named `_x` anywhere in the tree — the only occurrence of `_x` in the
  whole `src/` directory is this one read site. `P.__dict__.get("_x", 0)` therefore always
  evaluates to `0` and this line is permanently equivalent to plain
  `v["result"]["decimal"]`. Harmless (adds a no-op zero, doesn't corrupt anything) but it's dead,
  confusing vestigial code — reads like a debugging hook that was never wired up or never
  cleaned up — in the one function (`--check`) that actually validates the Assay against
  independent ground truth. Worth deleting or explaining.

### Non-atomic shared write

- **`render.py:245`** —
  ```python
  with open(p, "w", encoding="utf-8") as f:
      f.write(v["svg"])
  ```
  in `main()`'s `--write` branch, writing `output/views/{tier}.svg`. Bare `open(w)`, no
  `silence.write_json`/`replace_retry` equivalent for text output. **[KNOWN — NEXT_STEPS.md §3,
  "Non-atomic shared writes still open"]**. Lower severity than the JSON-file cases above since
  these are per-tier diagram files regenerated wholesale each run and not read mid-write by
  anything in this batch, but it is the same pattern and is on the open list.

---

## Modules read end to end and found CLEAN this run

- **`address.py`** — re-read in full; no new findings. Confirms the prior run's clean verdict
  (`NEXT_STEPS.md §3` already lists it clean). The `_normalize`/`_worded`/`_token_set` matching
  cascade in `spine_code_for()` is careful and well-commented about its own past false-positive
  history (the "dc" substring bug); `tier_for`/`promote`'s promotion-only, never-demotion logic
  is sound and its rationale (measurements can transiently hit zero) is consistent with what
  this batch saw in `resync_roll.py` and `completeness.py`.
- **`derivation.py`** — the dependency-graph checker (`check_graph`, `depth`, `provenance`) is
  correct: cycle detection, dangling-parent detection, and rootless-DERIVED detection all do
  what they claim. Only defect is the known `SCAN_MODULES` omission above.
- **`profile.py`** — the base32 encode/decode round-trip (`encode`/`decode`) is correct and
  internally consistent (`B32`/`_b32`/`_unb32`, `GENRE_CODE`/`GENRE_FROM`,
  `REG_CODE`/`REG_FROM` are all built as true inverses; verified by inspection that `decode`'s
  regex `PS-([0-9a-z]+)-([a-z]{2})([a-z])-([0-9a-z]{4})-([0-9au])([0-4])` matches exactly what
  `encode` emits). Only defect is the known silent-default-on-load-failure at `:129-138`.

No file in this batch was entirely free of findings; `address.py` is the one module with zero
new or known issues on this pass.
