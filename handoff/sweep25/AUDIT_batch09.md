# BATCH 09 — sweep run #25

Files: `src/hostcheck.py`, `src/manifest_builder.py`, `src/pick_model.py`, `src/navtree.py`,
`src/style_audit.py`, `src/cosmology_graph.py`. Every line of every file read end to end.
`src/endpoint.py` also read in full as supporting context for the hostcheck investigation (not
part of the batch, no findings claimed against it beyond what NEXT_STEPS already records).

## SPECIAL TASK: why is "sources with a reachable wiki" red at 93%?

**Quantified.** `data/SWEEP_ROLL.json` has 209 populated sources (`entry_count > 0`).
`data/WIKI_HOSTS.json` gives a truthy host for 194 of them. **15 are hostless** — 8 absent from
the map entirely, 7 present with an empty-string value. 194/209 = **92.8%**, which rounds to the
dashboard's reported 93%. `standards.py:76` sets `MIN_HOST_COVERAGE = 1.0` — a 100% floor — and
`standards.py:490-496` computes exactly this fraction as `"sources with a reachable wiki"`.

**Verdict: (b), genuinely-hostless, for essentially all 15 — not a hostcheck.py code defect,
and the endpoint.py contract ambiguity is not what's poisoning this number.** Live evidence:

- **VERIFIED, run just now, real network, read-only (`hostcheck.adopt(dry=True, workers=4)`,
  no `--go`, nothing written):** all 15 hostless sources probed against every candidate
  `candidates()` can generate (D&D Wiki, token/pair Fandom guesses, Fandom disambiguation
  suffixes, neighbour hosts, Wikipedia) — **0 adopted, 15 genuinely without a wiki, holding
  1,479 catalogued entries.**
- **VERIFIED, from `state/overnight.log`:** the supervisor has been running this exact remedy
  (`foreman.adopt_hosts` → `hostcheck.py --adopt --go`) every ~10 minutes since at least
  2026-08-22. 14 consecutive runs that evening logged **"0 adopted, 17 genuinely without a
  wiki"** — the identical count, run after run. By 2026-08-24 the number had dropped to 15 (one
  run logged "4 adopted host(s)"), so the mechanism **does** work and **has** made real
  progress — just not on what's left.
- The 15 names are overwhelmingly one-author/homebrew or non-wiki media: `JMBrew`,
  `aurora_mods (Way of the Inkmaster)`, `swecky's Nature Traditions`, `swordmeow's Atavist`,
  `the Sex Worker background`, `the Weaveshaper Ateliers`, `Curious DM Investigations (the
  Sharkin)`, `Genuine Fantasy Press (Forgotten Secrets)`, `KBP Unlikely Heroes`, `Kobold Press
  (Midgard Heroes Handbook, Midgard Worldbook)`, `Super Energy Apocalypse 1 & 2`, `The Amethyst /
  Cockroach King screenplay (Chroma Wastes)`, `Song of Syx`. Two — `Clockwork Angels (Rush)` and
  `The Elements Beyond` — are named in hostcheck.py's own opening docstring (lines 10-16) as
  exactly the case this file was built to catch: a same-named wiki exists but is about something
  else, and the honest answer for these two is "no wiki holds this fiction," not "hostcheck
  failed to find one."
- `probe()` and `candidates()` themselves read as correct: every prior bug class documented in
  the file's own extensive inline history (truncated candidate lists, encyclopedia
  generosity, CrossWiki 404s, throttling collapse) has a corresponding fix in the current code,
  and `roster_audit()`/`purge()`'s cross-checks (read separately, see below) show the mechanism
  catching real wrong-fiction hosts elsewhere on the roll. I found no logic defect in `probe`,
  `score`, `candidates`, or `null_rate`.

**The actual code-level defect (NEW, VERIFIED) is why this never converges cheaply:**
`hostcheck.py:846-910`, `adopt()`. Its docstring (853-857) says: *"Some are genuinely hostless
... and recording that is a real finding rather than a gap."* The code does not do this. `found
= {}` (893) only ever accumulates **successes**; a source that exhausts every candidate with no
hit is only ever `print()`-ed (900-901) and then forgotten — there is no negative-result write
anywhere in the function, unlike `sweep()`'s `--repair` path, which writes rejected hosts to
`data/HOST_UNFIT.json` (563-594) for exactly this reason. **Confirmed empirically**: I checked
`data/HOST_UNFIT.json` (3 rows total, none of the 15) and `data/SOURCE_PAGES.json` (0 entries
for any of the 15) — despite this exact "genuinely without a wiki" verdict being reached
**dozens of times over three days** for the same 15(-17) sources, nothing durable records it.
Every ~10-minute supervisor cycle re-runs the full candidate search from scratch for sources
that will never resolve, and the order text pointed at by `standards.py:495`
(`python src/hostcheck.py --adopt --go`) can never close this gap no matter how many times it is
run, because the sources it is chasing do not have a wiki to find. `MIN_HOST_COVERAGE = 1.0` has
no comment marking it deliberately-unsatisfiable the way its sibling `MIN_CATALOGUE_COVERAGE`
does (`standards.py:296-297`, "DELIBERATELY 1.0 AND DELIBERATELY UNSATISFIABLE, like
MIN_HOST_COVERAGE") — so the intent is stated only on the OTHER constant, one screen away,
not on this one. This is a real, fixable gap (give `adopt()` a `HOST_UNFIT`-style ledger, or an
owner-confirmed "no wiki, checked N times, stop searching" marker) but it is not what most of
the 7% represents; most of the 7% is genuinely-uncitable homebrew, which is itself the honest
finding the whole file exists to produce.

**Secondary, KNOWN, not re-detailed:** `foreman.py:192`'s `scout_hostless()` calls
`SC.sweep(limit=4)` — the model-assisted URL-search fallback for exactly this homebrew case is
capped at 4 sources a cycle with no rotation (already flagged in NEXT_STEPS §1/F), so most of
the 15 may never get a scout attempt at all. Outside this batch's files; not re-verified here
beyond confirming `data/SOURCE_PAGES.json` holds 0 rows for all 15, consistent with the cap.

**Endpoint contract ambiguity (m106/D, KNOWN, already in NEXT_STEPS):** `hostcheck.py:134-135`
(`EP.detect(host)`/`EP.fetch_raw`) and `:245-246` (same, inside `_bodies`) are two of the four
call sites NEXT_STEPS item D names as misled by `endpoint.fetch_raw`/`detect`'s inability to
distinguish "confirmed absent" from "request failed." Real, and could shave a false negative off
an individual candidate probe on a bad network day, but it is not the dominant force behind the
93% figure — the live re-run above shows the same 15 failing with a clean network right now.

---

## Findings

### `hostcheck.py`

- **`hostcheck.py:846-910` `adopt()` — docstring promises a "genuinely hostless" verdict is
  recorded; the code never writes one anywhere.** VERIFIED (code read + `data/HOST_UNFIT.json`
  and `data/SOURCE_PAGES.json` both empty for all 15 repeatedly-reconfirmed-hostless sources).
  See the special-task section above for full detail. This is the actual mechanism keeping the
  standard red under repeated, wasted, identical work.
- `hostcheck.py:134-135`, `:245-246` — `endpoint.detect`/`fetch_raw` return-contract ambiguity.
  **KNOWN** (NEXT_STEPS item D names these exact four call sites).
- `hostcheck.py:128` `names = [...][:PROBE]` (PROBE=40), `:135` `names[:12]`, `:199`
  `titles[...][:sample]` (sample=12), `:246` `list(titles)[:8]` — all statistical sampling for a
  hit-rate/aboutness TEST, not a listing of the roster itself; considered against Hard Rule 0 and
  cleared — these don't decide what's in the library, only whether a candidate host passes a
  threshold test, and the file's own docstrings argue this explicitly (PROBE's comment, ABOUT's
  sample reasoning). Not filed as a finding.
- `hostcheck.py:87` `_land()` — correctly atomic (tmp + `silence.replace_retry`), with a docstring
  explaining exactly why (m100-class history). Clean pattern, used consistently at every write
  site in this file (`sweep()`, `purge()`, `roster_audit()`, `adopt()`'s host-map update).

### `manifest_builder.py`

- `manifest_builder.py:436,455,463` — non-atomic `open(path,"w")+json.dump` direct writes
  (manifest, `unassigned_sources.md`). **KNOWN** (NEXT_STEPS §3 "Non-atomic shared writes").
- `manifest_builder.py:316-320` — `feats_index.feats_for_source()` exception swallowed to an
  empty list, silently dropping the entire Feats & Attested Deeds chapter for that source on any
  error. **KNOWN** (NEXT_STEPS §3 "Smaller, verified").
- `manifest_builder.py:66-104` `load_record()` — VERIFIED CLEAN by direct execution: ran it
  against all 209 populated sources on the real roll. 0 missing records, 0 name/file mismatches.
  The fuzzy substring-matching logic (bidirectional containment + closeness scoring) that a prior
  run's comment describes fixing works correctly across the whole real dataset today.
- `pack_feats()` (146-217) — correctly paginates oversized entities across blocks rather than
  truncating (Hard Rule 0 compliant); "flush before exceeding" logic matches its own worked
  comment. Read closely, no defect found.

### `pick_model.py`

- `pick_model.py:295` `budget = (total_vram_gb() or 10.0) - VRAM_RESERVE_GB` — silently assumes a
  10GB card when `nvidia-smi` is unreachable, undermining the owner's 2026-08-24 GPU-only
  residency ruling with no error or warning surfaced to the operator. **KNOWN** (flagged directly
  in the batch prompt; also in NEXT_STEPS §3 "Smaller, verified"). VERIFIED at source: confirmed
  `total_vram_gb()` returns `None` (not raises) on any `nvidia-smi` failure (176-187), and the
  `or 10.0` fallback at 295 is the only place that result is consumed for the residency budget —
  nothing downstream distinguishes "measured 10GB" from "assumed 10GB."
- Everything else in this file — `save_config()`'s atomic-write-with-verified-return pattern,
  `family_tier()`'s tier ordering, `resident()`/`weight_gb()`/`fit_note()`, the MoE-disqualified
  residency gate — read correctly and consistently with their documented intent. No further
  findings.

### `navtree.py`

- `navtree.py:263` `silence.write_json(OUT, data, ...)` — return value not checked; a persistent
  Windows lock denial reports success anyway (the process exits after "wrote {OUT}"). **KNOWN**
  (NEXT_STEPS §3 explicitly names `navtree.py:263` under the `silence.write_json`-ignored-return
  generalisation).
- `touch()`/the tier-aggregation logic (80-109), the `audit()` self-check (210-223), and the
  "branches holding sources but no catalogued worlds" report (250-252) were traced by hand
  against the source/world loop structure: every node the audit's `empty` list can report is
  guaranteed to have `src >= 1` by construction (both loops increment ancestor counts at every
  tier they touch), so the printed claim is accurate. No defect found.
- `register_for()`/hyperverse-naming tie-breaks (157-194) correctly use the `(count, name)`
  secondary key the m41 comment describes; read and matches its own fix.

### `style_audit.py`

- **`style_audit.py:38-39` `TURN_ENDING` — compiled with `re.M`, so `$` matches end of ANY line
  in the record, not end of the record.** NEW, VERIFIED by direct execution:
  ```python
  r = 'It was gone. And so nothing remained of the old order.\nThe city rebuilt itself over decades...'
  TURN_ENDING.search(r)   # -> matches, even though the record does NOT end on a turn
  ```
  `record_of()` returns a record as one multi-paragraph blob, and `TURN_ENDING` is meant to
  measure whether an entry's **final** sentence turns ("And so...", "But...", etc — Ground Rule
  6). Because `$` under `re.M` matches before every `\n`, any internal line that happens to end
  in a turn-shaped sentence — a perfectly fine mid-paragraph construction — gets counted as the
  entry "ending on a turn," inflating `turn_rate` and the printed `OVER (target <= 25%)` flag.
  This only ever over-counts (a genuine end-of-record match still fires), so the tool
  systematically overstates this one metric. Fix is either drop `re.M` from this compile (use
  `\Z` explicitly, which already appears as an alternative in the record-boundary regex two
  functions up) or search only the trailing slice of the record.
- `entries()`'s `[◈◈]` character class (line 44) — both characters are the identical codepoint
  U+25C8 (confirmed via `ord()`), so the duplicate is inert; behaves exactly like `[◈]`. Checked
  whether a second distinct delimiter glyph was intended and lost in transit (this file has its
  own literal `_BAD_CHARS` self-check for exactly that failure mode in `hostcheck.py`/`endpoint.py`,
  though `style_audit.py` doesn't carry that guard) — scanned every prompt/reference file for
  other diamond-family glyphs and found only this one U+25C8 in actual use throughout the
  project. Cosmetic redundancy, not a functional bug; not filed as a finding.
- Ran the module against the 105 real files under `output/raw/`: 894 entries parsed cleanly,
  `record_of()`/`entries()` correctly segment real generated chapters (this is what surfaced the
  `TURN_ENDING` bug above — `em_per_entry` and `banned` counts on real data both look sane and
  non-degenerate).
- `opener_shape()` (59-86) — the NAME-collapsing fix its own comment describes is present and
  correct; re-verified rather than just trusted, by construction against the FUNCTION-word set.

### `cosmology_graph.py`

- `cosmology_graph.py:86-87` `pair_shared[p]` capped at 8 examples, consumed as real evidence
  by `resonance.py:146` via a different output file. **KNOWN** (NEXT_STEPS §2.F, verbatim).
- **NEW, VERIFIED-by-code-reading:** `cosmology_graph.py:141-149` — `silence.write_json(OUT,
  ...)` return value discarded, then `print(f"\nwrote {OUT}")` runs unconditionally. `write_json`
  (confirmed by reading `silence.py:250-287`) returns `False` on a denied Windows rename without
  raising — so on a persistent lock this prints "wrote" for a file that was never replaced. Same
  shape as the `navtree.py:263`/`catalogue_codex.py:203`/`scope.py:119` instances NEXT_STEPS
  already generalises the lesson from, but this specific call site was not in that list.
- `build_graph()`'s IDF weighting (62-88) and `components()`'s connected-components clustering
  (91-112) read correctly against the module's own worked reasoning (rare co-attestation binds,
  ubiquitous doesn't; `UBIQUITOUS_CUTOFF` softens rather than drops). No further findings.

---

## Modules read end to end and found otherwise CLEAN this run

`pick_model.py` (aside from the one KNOWN finding), `navtree.py` (aside from the one KNOWN
finding), `manifest_builder.py`'s `load_record`/`pack_feats`/`build_jobs_for_source` core logic,
`cosmology_graph.py`'s graph-building and clustering core logic, `hostcheck.py`'s `probe`,
`score`, `candidates`, `null_rate`, `relevance`, `roster_audit`, `purge` (all read in full; no
new logic defects beyond the `adopt()` recording gap above).
