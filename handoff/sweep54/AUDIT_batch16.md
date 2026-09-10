# AUDIT batch16 — sweep run54

Read every line of all eight modules (hostcheck.py 1636 lines, binding_health.py 1545,
wiki_source.py 789, address_space.py 673, zfighters.py 536, genre.py 381, wh40k.py 350,
tempus.py 297). All eight are exceptionally heavily self-commented, each carrying long
narratives of past defects and their fixes ("order <hash>", "owner ruling ..."). Given that,
this audit's method for each module was: read every line and every docstring claim, then
specifically hunt for (a) numeric or line-number claims made in comments/docstrings that could
be checked against the live source or live data, and (b) logic that looked newly-introduced
or unguarded relative to the surrounding self-audit density. Several specific numeric claims
were verified by running the code / loading the referenced data files directly rather than by
inspection alone (noted per finding).

## hostcheck.py

Read in full, twice through the `score()`/`sweep()`/`adopt()`/`purge()`/`roster_audit()`
functions given their density. Traced the verdict branch order in `score()` (lines 819-892)
by hand against every combination of `rate`/`base`/`about` and found it internally consistent
(no unreachable or contradictory branch). Traced `_land_hosts`' compare-and-swap and
`null_rate`'s control-sample logic; both match their own extensive doc claims.

### MINOR — stale line citations in the module's own "dead code" comment about `GOOD`
**Where:** src/hostcheck.py:256-270 (the comment introducing `_PROSE_ONLY_GOOD_RATE`)
**What:** The comment asserts specific line numbers for where `GOOD`/`GOOD_LIFT`/`DEAD` are
referenced elsewhere in the file: "the module docstring at :37, and two historical comments
at :800 and :815 ... `DEAD` right below IS live (score(), :719-742); `GOOD_LIFT` at :219".
**Why it is wrong:** Checked every citation against the current file:
- `:37` — correct; that line does read "`GOOD` is now only the figure quoted in prose here."
- `:219` — wrong. Line 219 is inside `_land_hosts` (`silence.note("hostcheck.py:hosts-nondict")`),
  nothing to do with `GOOD_LIFT`. `GOOD_LIFT = 0.25` is actually defined at line 293.
- `:719-742` — wrong. That range is inside `null_rate()` (the control-rate-is-None handling),
  not `score()`, and has no reference to `DEAD` at all. `DEAD` is actually used at line 838
  inside `score()`'s verdict chain.
- `:800` and `:815` — wrong. Line 800 is inside a different comment about the
  warhammer40k.fandom.com incident, and line 815 is executable code
  (`relevance(host, r.get("titles") or [], source)`), not a "historical comment describing the
  selection path that USED to consult [GOOD]".
This is exactly the failure class this project's own CLAUDE.md names by example (the drill.py
"57 nets" citation going stale) — a comment's own provenance citations have drifted out from
under it, in the one file whose stated job is catching exactly this shape of thing. It causes
no runtime behavior change (the dead-but-not-deletable status of `_PROSE_ONLY_GOOD_RATE` is
still correctly reported by the surrounding code), so it is a documentation-only defect.
**Confidence:** Verified directly by reading each cited line number in the current file and
confirming it does not contain what the comment claims.

Everything else read clean: `probe()`, `relevance()`/`_bodies()`, `candidates_split()`,
`sweep()`, `purge()`, `roster_audit()`, `adopt()` all match their extensively-argued docstrings
on inspection, and the CAS/atomic-write helpers (`_land`, `_land_hosts`) are consistent with
their siblings in the other modules of this batch.

## binding_health.py

Read in full. Traced `verdict()` (the pure three-probe decision function) against every
combination of `(ok_present, ok_absent, ok_reachable)` by hand and confirmed it matches the
docstring's stated truth table with no unreachable/contradictory branch. Traced the
compare-and-swap logic in `quarantine()`/`release()`/`_land_cas`, the `_spread()` even-sampling
helper (checked the off-by-one/rounding for `want==1` and `n<=want`), and the whole-estate vs.
partial-pass merge logic in `run()` (the `filtered`/`not out`/`not filtered` guard combination).
Verified the `_BLOCKED_MARK = "refusal marker"` substring actually matches what
`feats.page_looks_real` produces (`"carries a refusal marker (...)"`, confirmed via grep of
feats.py) — no drift there despite it being a cross-module string-matching dependency.

No findings. Checked for: unmeasured-control defaulted to a confident value (none found — every
`None` case is threaded through, not defaulted); discarded write verdicts (none — every `_land`/
`_land_cas` call site's boolean is captured and reported, matching the file's own extensive
history of exactly that class of bug); truncation of a listing a person reads to act (none —
`_candidate_titles`/`known_present_titles` are correctly spread-not-front-cut per their own
documented fix, and `--titles`'/`--quarantined`'s printed rows are unbounded or explicitly
marked when cut).

## wiki_source.py

Read in full. Checked `resolve_wiki()`'s host-map short-circuit logic, `verify_wiki_matches()`,
`all_categories()`'s cache-key/hard_stop handling, and the three "raise on transport failure,
never return a partial listing" functions (`all_categories`, `category_members`, `extracts`)
against their docstrings' claims about Hard Rule 0 truncation bugs previously fixed. All
consistent. `clean_titles()`'s O(n) set-based dedup is correct. `_spread`-equivalent isn't used
here (this module still does front-truncation in a couple of controlled spots, e.g.
`rank_by_size`'s `[:top]`, but those are explicitly documented as post-ranking, which Hard Rule 0
permits).

No findings. One thing noted but not filed as a defect: `resolve_wiki()`'s candidate list can
contain the same subdomain twice (once from `WIKI_OVERRIDES`, once from a matching `known` host)
since the de-dup (`if c not in cands`) is only applied to the `subdomain_candidates()` batch, not
between `known` and `WIKI_OVERRIDES`. This wastes at most one redundant API call and never
changes the result, so it does not rise to a reportable finding under this sweep's criteria.

## address_space.py

Read in full, including `main()`'s live report. Verified several of the module's own
"measured on such-and-such date" numeric claims directly against the live data files, since this
module explicitly stakes its credibility on exactly these numbers not going stale (it has
already been burned by this twice per its own comments, order 60dc7c624c06).

### MINOR — stale "measured against the live census" figures in `assign()`'s comment
**Where:** src/address_space.py:477-480
**What:** "TIERS.json holds 209 rows with hyperverse 2..5, xenoverse 0..5, metaverse 0..7 and
multiverse 0..167 against field capacities of 8/8/8/256, and all 1,016 designations in
WORLDSEEDS.json address with zero out-of-range tiers."
**Why it is wrong:** Loaded `data/TIERS.json` and `data/WORLDSEEDS.json` directly. Actual:
208 rows (not 209); hyperverse ranges 1..5 (not 2..5); xenoverse ranges 0..2 (not 0..5, and at
today's derived width this means xenoverse's actual field capacity is 4, not the claimed 8);
metaverse ranges 0..5 (not 0..7); multiverse ranges 0..142 (not 0..167). WORLDSEEDS.json does
still hold 1,016 designations, so only that half of the sentence is current. This is the exact
failure this paragraph is itself warning about two lines later ("a tier can only fall outside
[a width] if TIERS.json moved after import") — the census has in fact moved since this comment
was written, and the comment's own numbers are now the stale artifact it was written to guard
against becoming. No behavioral impact: the module computes widths live from `_tier_counts()`,
so `fit()`/`pack()` still work correctly against the current census: it is a documentation-only
drift, but it is precisely the pattern (numeric doctrine going stale while still being reasoned
from) CLAUDE.md's own drill.py example calls out.
**Confidence:** Ran `data/TIERS.json` and `data/WORLDSEEDS.json` through
`C:/Users/imarl/miniconda3/python.exe` directly and computed the min/max/count per field.

### MINOR — stale counts in `shelfmark()`'s docstring about uncharted tiers
**Where:** src/address_space.py:296-298
**What:** "38 of 208 TIERS.json rows carry an uncharted hyperverse and xenoverse, 65 an
uncharted metaverse, and 16 of the 1,016 designations in data/SHELFMARKS.json are affected."
**Why it is wrong:** Measured directly against the live files: hyperverse-missing = 38 (matches),
xenoverse-missing = 38 (matches), metaverse-missing = 63 (claimed 65), and SHELFMARKS.json rows
carrying an `uncharted` field = 14 of 1,016 (claimed 16). Two of the four numbers have already
drifted by a small amount since this sentence was written. Same class as the finding above, at
lower severity since the drift is small and the row/hyperverse/xenoverse counts still check out.
**Confidence:** Same method — loaded `data/TIERS.json` and `data/SHELFMARKS.json` and counted
directly.

### MINOR — self-referential line citation in `seed_from_card()` points at the wrong function
**Where:** src/address_space.py:381 (inside `seed_from_card()`'s docstring)
**What:** "...it is written down here because this docstring has already been wrong once
(see :195-200) and the difference was in neither of them."
**Why it is wrong:** Lines 195-200 in the current file are `charted_gaps()`'s docstring
("Which of the four charted tiers this source's row leaves UNADDRESSED... Returns a tuple of
field names..."), which has nothing to do with a docstring having previously stated something
false about star-insensitivity or seeding. The actual "this docstring said the opposite" mea
culpa the sentence is presumably pointing at is `shelfmark()`'s own docstring a few dozen lines
above (which explicitly says "THIS DOCSTRING SAID THE OPPOSITE FOR THREE SWEEPS", starting
around line 277). This reads as the same class of drifted line-citation as the hostcheck.py
finding above: correct when written, now pointing at unrelated code after subsequent edits
shifted line numbers.
**Confidence:** Read lines 195-200 directly and confirmed their content does not match what the
citation claims to be pointing at.

Everything else in this module checked out on direct trace: `pack()`/`unpack()` round-trip
correctly (bit-order matches, confirmed by hand and by the module's own `main()` assertion),
`_hash_offsets()`/`_HASH_SPAN`/`HASH_BYTES` derivation is internally consistent and reproduces
the documented legacy 8/48/78 offsets exactly, and `fit()`'s no-modulo-raises-instead behavior
is consistent with `drawn()`'s modulo-reduces behavior (the two are deliberately different
because one handles untrusted external tier data and the other handles a hash draw that is
already guaranteed in-range).

## zfighters.py

Read in full, including every fighter's 11-axis worksheet (154 axis entries across 14 fighters
plus Goku carried in from another file). Checked axis-key consistency across all 14 local
roster entries (all carry the same 11 axis names) and traced `compute()`, `value()`, and the
`--full` printing path, including the documented fix for Goku's carried-in sheet not having a
`provenance` key. No findings — the computational wrapper (as opposed to the hand-authored
content, which is a curatorial judgment call outside this sweep's remit) is correct and
consistent with its own extensive fix history.

## genre.py

Read in full. Verified `classify_text()`/`classify_source()`'s Counter-based scoring (confirmed
the "no `not ranked` disjunct needed" claim is correct: every genre always gets a Counter entry,
so `ranked` can never be empty) and confirmed all 22 regex cue patterns across the 11 genres
compile without error (ran them through `re.compile` directly — no eaten-escape corruption).
No findings in the classification logic itself.

### QUESTION — missing the eaten-regex-escape self-check present in ~52 sibling modules
**Where:** src/genre.py (whole file; no `_BAD_CHARS` guard anywhere)
**What:** hostcheck.py, zfighters.py and wh40k.py (all three in this same batch) each open with:
```
_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")
```
`genre.py` — which is the single heaviest user of hand-written backslash-escaped regexes in this
batch (22 patterns across 11 genres, all using `\b`/`\w`) — has no such guard, nor do
wiki_source.py, binding_health.py, address_space.py or tempus.py in this batch.
**Why it might matter:** This is the exact corruption class CLAUDE.md's memory flags project-wide
("Never pass prose through a shell — backticks in prose get EXECUTED"; the sibling note about
regex escapes being eaten in transit). A grep across all of src/ shows 52 of 117 modules carry
this guard, so it is not a universal convention — it looks like it was added reactively to
specific files after specific incidents rather than applied as a blanket policy. Not filed as a
defect because (a) all of genre.py's regexes currently compile cleanly (verified by running them
through `re.compile`), so there is no live corruption today, and (b) it is plausible this guard
is deliberately scoped to files that were actually bitten by the corruption incident rather than
applied everywhere. Flagging as a question for the coordinator/owner: should genre.py (and the
other regex-bearing modules in this batch lacking the guard) get it too, given it is cheap and
this is precisely the kind of file the guard exists for?
**Confidence:** Grepped all of src/ for the guard (52/117 files carry it) and compiled every
regex in genre.py directly to confirm no current corruption.

## wh40k.py

Read in full, including all 55 axis entries across the five Chaos Gods / Emperor entries. This
module makes unusually precise, checkable numeric claims about itself ("MEASURED 2026-09-08: 13
wiki, 42 canon" and "NO MAGNITUDE MOVED... Tzeentch M7.86, Slaanesh M7.85, Nurgle M7.80, Khorne
M7.76, the Emperor M6.76") and both were verified by actually running the module:
- Counted `_provenance(v)` over all 55 axes: 13 "wiki", 42 "canon", 0 other — exact match.
- Ran `compute()` and ranked the resulting assays: Tzeentch M7.86, Slaanesh M7.85, Nurgle M7.80,
  Khorne M7.76, The Emperor of Mankind M6.76 — exact match to the docstring's claimed values.
No findings. This is the cleanest of the eight modules against its own stated claims.
**Confidence:** Ran `wh40k.compute()` and `wh40k._provenance()` directly via
`C:/Users/imarl/miniconda3/python.exe` with `PYTHONIOENCODING=utf-8`.

## tempus.py

Read in full. Traced `is_present_at()`'s `event_mark >= observer_rung` against its docstring's
stated semantics ("An event ratified to rung n is present to every registry at or below n") and
`concordance_now()`'s "lower-rung observers have a LARGER now" — both are consistent with the
formula on hand-worked examples. Traced `rung_description_length()`/`band_resolution()`'s
band-edge arithmetic (including the M10 ceiling-inherits-M9-M10-width special case) and
`apparent_lag_years()`'s now-uniform two-branch return shape (`{distance, lag_years, path,
note}` in both the path-found and no-path cases). `retrocausality_beta()`'s non-positive-years
short-circuit and `prescience_horizon_bits()`'s non-positive-lead-time raise are both correctly
guarded. No findings.

## Summary of severities

- MAJOR: none.
- MINOR: 4 (hostcheck.py:256-270 stale citations; address_space.py:477-480 stale TIERS.json
  figures; address_space.py:296-298 small stale-count drift; address_space.py:381 misdirected
  self-citation).
- INFO: 0.
- QUESTION: 1 (genre.py and four other modules in this batch lack the `_BAD_CHARS` eaten-escape
  guard that hostcheck.py/zfighters.py/wh40k.py carry — not filed as a defect, flagged for an
  owner call on whether the guard's scope should widen).

All four MINOR findings are documentation-only drift (comments/docstrings whose specific
numbers or line citations no longer match the source or data they describe) with no traced
effect on runtime behavior — every module's actual computation reads its inputs live rather than
trusting the stale prose. They are filed because this project's own stated doctrine (CLAUDE.md's
drill.py "57 nets" precedent) treats exactly this shape of drift as worth catching before it gets
reasoned from.
