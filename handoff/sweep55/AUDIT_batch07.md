# AUDIT — sweep55, batch 07

Modules read in full, line by line, in this order: `tuning.py` (286), `catalogue_aurora.py` (324),
`sevenfold.py` (441), `anchors.py` (576), `backfill.py` (474), `onomast.py` (773),
`corpus_db.py` (1,040), `cascade_bridge.py` (2,317). 6,231 lines total.

Nothing under `src/`, `data/`, `state/` or any ledger was written. No module in the batch was
executed. Two files OUTSIDE the batch were read to settle citations and contracts
(`src/assay.py`, `src/custodes.py`, plus greps of `drill.py`, `verify_math.py`, `genre.py`,
`wh40k.py`, `roll.py`, `silence.py`, `feats.py`, `pipeline.py`), and one tree outside the
repository (`C:/Users/imarl/cascade/cascade/engine.py`, `router.py`) was read to check
`cascade_bridge`'s four external line citations. Reading only; nothing there was run.

## The citation pass this batch was asked for

Every `file.py:NNN` in the batch was opened at both ends. Result, up front:

| citation | in | lands on | should be | verdict |
|---|---|---|---|---|
| `engine.py:545` | cascade_bridge.py:416 | `return True, "model rejected by the provider"` | — | **LIVE** |
| `engine.py:225` | cascade_bridge.py:427 | `# 401/403 mean a bad key -- a long cooldown...` | — | **LIVE** |
| `cascade/engine.py:277` | cascade_bridge.py:779 | the `empty response` failover yield | — | **LIVE** |
| `:343` | cascade_bridge.py:779 | `record_failure(model, "no answer text produced", ...)` | — | **LIVE** |
| `genre.py:327-331` | onomast.py:754 | the `sources classified` / genre-distribution print | 370-375 | **ROTTED** |
| `sevenfold.py:412-415` | onomast.py:754 | the sample-WORLD-shelfmarks print loop | 425-435 | **ROTTED** |
| `wh40k.py:290-295` | onomast.py:754 | the `--full` per-entity print loop | 337-343 | **ROTTED** |
| `:321` | corpus_db.py:428 | `if evidence_limit:` | ~392-398 | **ROTTED** |
| `:742` | corpus_db.py:429 | `_cell`'s docstring | 1000-1004 | **ROTTED** |
| `:190` | corpus_db.py:635 | comment prose in `rebuild()` | 236 | **ROTTED** |
| `catalogue_aurora.py:74` | catalogue_aurora.py:151 | — | — | historical; the citation was already replaced by a content label. No finding. |

The six ROTTED ones are already on the books: work order **`386c0d66e31e`**
(`STALE_LINE_CITATIONS_SWEEP54`, MINOR, filed by sweep54's own batch 07) lists all six under
"STILL OPEN, verified by the sweep and NOT fixed this shift". I re-measured every target
independently rather than trusting the order, and my numbers agree with sweep54's to within the
usual block-boundary ambiguity. **Still open, still unfixed.** None of the six would be caught
by `src/citecheck.py`: every one lands on real, non-blank, non-bracket source.

Four MORE rotted citations were found, all NEW (not in `386c0d66e31e`), all pointing INTO this
batch from files OUTSIDE it. **The defective line is outside batch 07 in every case** — the
coordinator has to route them — but the target end is `anchors.py`, which IS mine, so the
verdict is definitive, not a guess. They are filed under `anchors.py` below.

Also checked and found LIVE: `tuning.py:263`'s "Pinned by verify_math S19ac" —
`verify_math.py:3921` is `# ---- Section 19ac: a worker request is a ceiling at every value,
including zero`. The claim holds.

---

## src/tuning.py

Read line by line. Checked: the `regime()` verdict logic against both its constants, the
`_CACHE` label/count coherence argument (the whole premise of the module), `workers()`'s
zero-is-a-request contract, `cloud_success_rate`'s SQL and its "path comes from the module that
owns the file" note, `_ollama_host`'s config read, and `_answering_buckets`' stale-proof
handling.

The module is substantially clean. One finding.

### INFO — a clamp in `profile()` whose lower half cannot bind
**Where:** src/tuning.py:243
**What:** `p["workers"] = max(4, min(16, _CACHE["buckets"] + 2))`, reached only inside
`if r == "cloud":`.
**Why it is wrong:** `regime()` returns `"cloud"` only when `n >= CLOUD_MIN_BUCKETS`
(line 224, `CLOUD_MIN_BUCKETS = 3`), and the whole point of the `_CACHE` note at lines 106-110
is that `buckets` is the SAME reading that produced the label. So on this branch
`_CACHE["buckets"] >= 3`, the expression is `>= 5`, and `max(4, ...)` can never select the 4.
The comment at lines 93-95 advertises a clamp of "4..16"; only the 16 is a live bound.
This costs nothing today and is genuinely defensive if `CLOUD_MIN_BUCKETS` is ever lowered —
it is filed because the brief's category 1 is "a check that cannot fail", and this is that
shape in its most harmless form. **Not a fix request; a QUESTION about whether the stated
4-floor was meant to survive `CLOUD_MIN_BUCKETS` being raised to 3.**
**Confidence:** read both constants and both call paths; arithmetic, no execution needed.

---

## src/catalogue_aurora.py

Read line by line. Checked specifically: that every write verdict is gated (the record write at
:261, the roll compare-and-swap at :296, and the exit code at :315-320); that `written` is
appended only AFTER a landed write on the real path and only in the dry branch otherwise; that
`roll_changes` is populated only for landed writes; that `roll.update_rows`' real signature
(`src/roll.py:165`, `-> (landed, why)`) matches the call; that `parse_folder`'s dedup key
carries the description (so the 442-element silent drop stays fixed) and that `dropped` is
reported; that `slug()` is uncapped and `record_path()` resolves the legacy 60-char shape;
and that `silence` is actually used (it is, at :157).

**Clean.** No finding. The `LEGACY_SLUG_CAP` constant is a named historical shape, not a live
cap, exactly as its comment says.

---

## src/sevenfold.py

Read line by line, including the full `seams()` commentary. Checked: `_even_cuts`' clamp
against its own docstring (`min(max(int(round(step*j)),1), n-1) - 1` does land in
`[0, n_members-2]`, so no empty chunk is possible — verified by hand at n=2, n=3, k>n);
that `eligible` at :203 can never be empty (the median is always attained, and the `or gaps`
tail covers the rest); that `cuts` cannot repeat a position (:208 `g[1] not in cuts` plus the
`sorted(set(...))`); that `split()` advances `child` only for a non-empty chunk; that the
zip at :239 is deliberately unequal-length (stated at :235-238 and true — `SOURCE_TIERS` is a
prefix of `TIERS`); and that `build()`'s two populations (`coords` from the resonance graph,
`by_source` from `worldseed`) really do get counted separately with `UNSHELVED` reported rather
than `continue`d away.

**Clean.** No finding.

Marked-and-kept seen, not filed: `ok = "OK" if hi <= SPAN else "OVER SPAN"` at :377 is a
display of a guarantee `seams()` enforces by construction, and its own comment (:373-376) says
so, names the m30 precedent, and states the condition under which it would become a real check.
Saw the marking; moving on.

Note for the coordinator: `onomast.py:754` cites `sevenfold.py:412-415` as a write-denied
branch. It is not — the real branch is :425-435. Filed under onomast.

---

## src/anchors.py

Read line by line, including all five ANCHORS blocks and the whole invariant section. Checked
against `src/assay.py` directly: `INSTRUMENT_WINDOWS` (M5..M10 are all `(30, 30)`, so the
OWNER QUESTION at :546-554 is factually correct), `FACULTY_READS` (no faculty reads `volition`,
so the M10 ceiling's six faculties are all populated), and `instrument()`'s return shape.

Two things I expected to be findings and confirmed are NOT, recorded so the next sweep does not
re-derive them:

* `all(str(v).startswith("30") ...)` at :390 looks like a weak stand-in for `== 30`. It is
  correct and `== 30` would be wrong: `assay.instrument` returns `f"{value} (Grade {grade})"`
  whenever a grade exists (`assay.py:1622`), so at M10 each faculty is the STRING
  `"30 (Grade V)"`. `value` is `max(1, min(30, ...))`, so nothing can start with "30" other
  than 30 itself.
* `bad_interval` at :461-464 short-circuits correctly — `float(c["interval"])` is never reached
  for a non-numeric interval.

### INFO — `NON_ENERGETIC_AXES` is a second spelling of `assay.NON_ENERGETIC_AXES`
**Where:** src/anchors.py:42-51
**What:** the dict is duplicated verbatim from `assay.py:248-257` and is never read inside
`anchors.py`.
**Why it is wrong:** it is not, today. `assay.py:243-247` files the duplication as deliberate
cross-file debt and says what the one-line repair is, and `verify_math.py:7848` holds the two
dicts EQUAL and reds if either side moves. I diffed them: byte-identical. **Saw the marking,
saw the guard, filing as INFO only so it is not re-derived a fourth time.**
**Confidence:** read both dicts and the verify_math check.

### MINOR — `custodes.py:355` cites `anchors.py:190` and the CLAIM has rotted, not just the number
**Where:** the defective comment is **src/custodes.py:355 — OUTSIDE BATCH 07.** The target,
`src/anchors.py:190` and the real call site `src/anchors.py:236-237`, are inside it.
**What:** custodes.py:355 reads *"both were then wired to a keyword argument that no production
caller supplies -- `anchors.py:190`, the single real call site, passes neither `eta` nor
`distance`/`years_since`."*
**Why it is wrong:** two ways.
(1) `anchors.py:190` is comment prose (`"  ANCHOR_DISTANCE = 0.0 -- an anchor is read AT ZERO
REMOVE..."`), not a call site. The call is at :236-237.
(2) The substantive claim is now FALSE. Order `bd673ceaaf31` (owner ruling 2026-09-08) wired
exactly that pair: `anchors.py:237` reads `worksheet="anchors.py", distance=_dist,
years_since=_since`, fed by `_anchor_vantage()` at :214-217. `anchors.py` even GRADES the
arrival now — the verdict *"Lumen measured staleness at every anchor rather than abstaining"*
at :500-502. Only `eta` (Threnody) is still unpassed, and `anchors.py:207-213` explains at
length why it must stay that way. So a maintainer reading custodes.py is told the whole
Lumen wiring is still missing when half of it landed and is under test.
**Confidence:** read custodes.py:350-360 and anchors.py:175-217 and :495-502; the keyword
arguments are present in the source.

### INFO — three files cite `anchors.py:427` for the unguarded `INSTRUMENT_WINDOWS` index
**Where:** defective comments at **src/assay.py:890, src/assay.py:900 (message text),
src/drill.py:11887 and src/drill.py:11908 — ALL OUTSIDE BATCH 07.** The target is inside it.
**What:** all four say *"anchors.py:427 ... indexes INSTRUMENT_WINDOWS[b] for every b in LADDER
with no guard"*.
**Why it is wrong:** `anchors.py:427` is `verdict(_label, False,` — the missing-reference arm of
the CLAIMS loop, which touches no window table. The real unguarded index is
`anchors.py:546`: `collapsed = [b for b in A.LADDER if A.INSTRUMENT_WINDOWS[b][0] ==
A.INSTRUMENT_WINDOWS[b][1]]`. The underlying claim is still TRUE (that line really is
unguarded), so only the number rotted — but it rotted in four places including a
`drill.py` net's own failure message, which is the text a reader gets when the net fires.
**Confidence:** opened all four sites and anchors.py:427 and :546.

### INFO — `assay.py:1538` cites `anchors.py:186`
**Where:** defective comment at **src/assay.py:1538 — OUTSIDE BATCH 07.**
**What:** *"callers hand this the whole numeric score dict (anchors.py:186 does)"*.
**Why it is wrong:** `anchors.py:186` is comment prose. The `instrument()` call that actually
does this is `anchors.py:231-234`. Claim true, number rotted.
**Confidence:** read both.

### INFO — `assay.py:226` cites `anchors.py:41`, off by one
**Where:** **src/assay.py:226 — OUTSIDE BATCH 07.** *"HOISTED HERE FROM anchors.py:41"*.
`anchors.py:41` is the closing `# ====` rule; the dict opens at :42. Trivial, recorded for
completeness only.

---

## src/backfill.py

Read line by line. Checked: `roster()` really is uncapped on the production path
(`backfill_source` passes no `limit`); that the subcategory walk is unconditional (:115) and not
gated on a thin top level; that `RosterIncomplete` is raised rather than returned; that the
`missing` ranking key `(t in sizes, -sizes.get(t, 0))` puts unmeasured titles FIRST (`False`
sorts before `True`) as :236-248 claims; that `absent` is pre-cap on both return paths; that
the write is gated at :337; and that `F.api` sets `formatversion=2` (`feats.py:845`), so
iterating `query.pages` as a LIST of dicts at :222 is correct and not the classic
dict-keyed-by-pageid bug.

Two findings, both on the explicit `--source` CLI path, both the house's own favourite shape.

### MINOR — the `--source` path discards every verdict `backfill_source` is careful to produce
**Where:** src/backfill.py:467-470
**What:**
```
for s in a.source:
    print(json.dumps(backfill_source(s, recs, hosts, cap=a.cap, dry=a.dry), ensure_ascii=False))
return 0
```
**Why it is wrong:** `backfill_source` can return `{"error": "no such source"}` (:195),
`{"error": "no wiki host"}` (:199), or `{"write_denied": True, "added": 0, ...}` (:338-344).
All three exit 0. The `--all` path thirty lines above does the opposite and argues for four
lines why (`:457-461`: *"a caller could not tell a run that added nothing from a run whose every
result was thrown away by a lock. A denied write is an INFRASTRUCTURE fault"*) and returns
`1 if denied else 0`. The named-source path is the one a person runs to repair ONE source; a
scheduled wrapper or a shell `&&` reading rc is told a denied catalogue write succeeded, and the
JSON line carrying the truth goes to stdout where only a human sees it. This is the identical
finding `catalogue_aurora.py:204-211` records as fixed in its own `main()` (order
`3cc35f54b235`), unfixed one file over.
**Confidence:** read all three return sites in `backfill_source` and both `main()` paths; no
execution.

### MINOR — a transport failure on the `--source` path still kills the whole invocation
**Where:** src/backfill.py:467-469, against the comment at src/backfill.py:188-192
**What:** the comment says *"The `--all` path wraps every call to this function in try/except
(Hard Rule -1: a source is its own area of the park), but the explicit `--source name [name
...]` CLI path does not, so one typo'd name used to kill the whole invocation and run none of
the sources listed after it"* — and then fixes only the lookup, by returning a dict instead of
raising `StopIteration` (order `929622118156`).
**Why it is wrong:** the consequence the comment describes is still reachable by a different
cause. `roster()` → `members()` raises `RosterIncomplete` (:90-93) on any `F.api` returning
`None`, which the class's own docstring says happens for a timeout as well as for an absent
page. On `--source A B C`, a timeout while walking A's category listing propagates out of the
unwrapped loop, B and C are never attempted, and the process dies on a traceback. `--all`
catches and counts exactly this (`:424-434`). So "one source is its own area of the park" holds
on the scheduled path and not on the interactive one, and the comment reads as though the whole
class were closed.
**Confidence:** traced `roster` → `members` → `F.api` and both `main()` loops; `feats.api`
returns `None` on failure (`src/feats.py:821`).

---

## src/onomast.py

Read line by line, including the whole doctrine header. Checked: `_stream`'s refill arithmetic;
all seven `well_formed` constraints against the seven the docstring now claims (they match, and
the three corrected attributions at :195-200 are accurate — I re-derived Shessasha and
Goggoktok); `coin_well_formed_stamped`'s salt space (400 + 400..9,999 = the 10,000 the comment
claims) and its digest-tail loop (`range(3,17)` = the fourteen candidates :365 claims); that
`taken` is seeded from `prior` EXCLUDING `naming` and that `naming` is computed before seeding;
and that `merged[cid]["retired"] = cid not in resolved` really does separate STANDING from
RETIRED as order `e5001f0b0153` claims.

### MINOR — `onomast.py:754`'s three sibling citations have all rotted
**Where:** src/onomast.py:753-754
**What:** *"Every sibling repaired by that sweep does the opposite (genre.py:327-331,
sevenfold.py:412-415, wh40k.py:290-295)."*
**Why it is wrong:** none of the three points at a write-denied branch.
`genre.py:327-331` is the `sources classified` / genre-distribution print block; the real branch
is `genre.py:370-375` (`silence.note("genre.py:main-write-denied")` at :372).
`sevenfold.py:412-415` is the sample-WORLD-shelfmarks print loop; the real branch is
`sevenfold.py:425-435` (`silence.note("sevenfold.py:main-write-denied")` at :432) — verified
directly, `sevenfold.py` is in this batch.
`wh40k.py:290-295` is the `--full` per-entity print loop; the real branch is
`wh40k.py:337-343` (`silence.note("wh40k.py:main-write-denied")` at :339).
The paragraph's argument is unaffected; the three pointers a reader would follow to check it are
all wrong, in a comment whose subject is that a verdict must reach somewhere a person can find.
**Confidence:** opened all three targets and located each real branch by grepping
`main-write-denied`. **Already filed under order `386c0d66e31e` and still open.**

### MINOR — `main()` indexes carried-forward records the merge deliberately does not validate
**Where:** src/onomast.py:710, :733, :740
**What:** `by_endonym[v["endonym"]].append(v)`, then `src = v["attestations"][0]` and
`v['catalogue_name']` / `v['register']`, over `live` — which includes records carried forward
from the prior file by `merged[cid] = {**rec, ...}` at :683.
**Why it is wrong:** `name_worlds`' merge explicitly anticipates a foreign or hand-edited
ONOMASTICON.json — :672-681 adds a `silence.note` for *"a prior record that PARSES ... but is a
dict with no truthy catalogue_name -- a hand-edited entry, or one written before some future
schema change"* — and guards exactly one key, `catalogue_name`. A hand-edited record that HAS a
`catalogue_name` and lacks `endonym` (or `register`, or has an empty `attestations`) passes the
merge, reaches `main()`, and takes it down with a bare `KeyError`/`IndexError` AFTER
`name_worlds` has succeeded. Nothing is lost — the crash happens before the write at :761 — but
the module that goes to great length to turn every other failure into a named refusal with an
exit code (`OnomasticonUnreadable` at :497-503, the write-denied branch at :761-765) answers
this one with a traceback. `load_onomasticon`'s whole argument is that a file that exists and is
wrong must be REFUSED, not crashed through.
**Confidence:** read the merge, the three indexing sites, and the two named-refusal paths; not
reproduced (would require writing a scratch ONOMASTICON.json, and the batch is read-only).

---

## src/corpus_db.py

Read line by line. Checked: the pid+thread temp name and its pre-delete scope; that the final
`replace_retry` verdict reaches the caller AND the exit code (:398, :920-925); that all three
"lookup failed" sentinels travel into `meta` and back out through `freshness()` and
`_freshness_banner()`; that the `""` vs `None` distinction on `host_lookup_failed` really does
separate "asked, fine" from "could not be asked" (rebuild writes `hosts_failed or ""`, so `None`
occurs only for a pre-migration index — the `elif` at :680-687 is reachable and correct); that
`deletion_check` is present on every return path of `freshness()`; that `CANNED` carries no
`LIMIT`; and that `datasette_metadata` is gated.

The module is in good shape. Findings are the citation set plus three low-severity notes.

### MINOR — three stale self-citations
**Where:** src/corpus_db.py:428, :429, :635
**What:** `age_seconds`' docstring cites *"the rebuild's stale-`built_at` warning
(`replace_retry`'s comment, :321)"* and *"the no-SQL branch's ABSENT/UNREADABLE note in `main()`
(:742)"*; `drift()` cites *"Same shape as `rebuild()`'s list at :190"*.
**Why it is wrong:** `:321` is `if evidence_limit:` (the inert-limit note); the `replace_retry`
comment is :392-397. `:742` is inside `_cell`'s docstring; the no-SQL ABSENT/UNREADABLE note is
:1000-1004. `:190` is comment prose inside `rebuild()`; the `unreadable_records.append` it means
is :236. The rot is 75, ~260 and 46 lines respectively, and `age_seconds`' docstring exists
specifically to stop a sixth sweep re-deriving it — a docstring whose own pointers do not
resolve is the fifth sweep's work made unfollowable.
**Confidence:** opened each target line. **Already filed under order `386c0d66e31e` and still
open.** None would be caught by `citecheck.py`: all three land on real, non-blank source.

### INFO — sweep54's "`the old five columns`" call at corpus_db.py:89 is AMBIGUOUS, not clearly wrong
**Where:** src/corpus_db.py:88-91
**What:** order `386c0d66e31e` lists *"b07 src/corpus_db.py:89 'the old five columns'; the
pre-migration count is nine"* as still open.
**Why I am not confirming it as filed:** the sentence sits directly under
*"UNREACHABLE joined the STATE SET ... split out of no_page"*, and the coverage state set really
is five columns — `cited, read, no_page, not_attempted, no_host`. Read that way, "five" is
correct. Read as the table's total column count it is nine and sweep54 is right. The clause
*"and the INSERT below would fail on arity"* argues for the total reading. I am reporting this
as an ambiguity for the coordinator to rule on rather than seconding a rewrite that might
replace a correct sentence with a different correct sentence.
**Confidence:** counted both sets against the `CREATE TABLE source` body and the ten-placeholder
INSERT at :279.

### INFO — a canned query against a pre-migration database raises past the guard that was just added
**Where:** src/corpus_db.py:783 (the `coverage` query selects `unreachable`) and :1029
**What:** `--canned coverage` runs `SELECT ... unreachable ... FROM source`. On a database built
before order `1d55458779fd`, that column does not exist, and `query(sql)` at :1029 raises
`sqlite3.OperationalError` uncaught.
**Why it is worth a line:** :1014-1022 records that this exact branch was given a NOT-USABLE
guard (order `7e81ccefa1c6`) precisely because *"very likely the FIRST command a fresh
checkout's user runs (`--canned coverage` before ever running `--rebuild`)"* left SQLite raising
uncaught. The guard covers a missing/locked/corrupt file; it does not cover a schema-mismatched
one, which is the state the SCHEMA comment at :88-91 says every pre-existing database is in.
The remedy is already written down there (*"Rebuild after pulling this change"*), so this is a
sharp edge rather than a defect, and is reported as such.
**Confidence:** read the CANNED entry, the CREATE TABLE comment, and both `main()` branches.

### INFO — the records glob runs twice, and `cols` is bound unused twice
**Where:** src/corpus_db.py:225-227 (two identical `glob.glob` calls, one for
`meta.record_files` and one for the loop) and :525, :622 (`cols, rows = query(...)` with `cols`
never read).
**Why it is worth a line:** harmless in both directions — a record appearing between the two
globs is indexed but absent from `meta.record_files`, which `freshness()` then simply does not
flag as deleted, and the mtime arm catches it anyway; a record vanishing between them fails
closed. Recorded so a future reader does not mistake the second glob for a different set.
**Confidence:** read; not executed.

---

## src/cascade_bridge.py

Read line by line, all 2,317. Checked against the live cascade tree at `C:/Users/imarl/cascade`:
`Engine.is_dead`'s four wordings (all four ARE in `_DEAD_WORDS`), both `empty response` /
`produced no answer text` / `no answer text produced` sites (all three ARE in `_EMPTY_CONTENT`),
`Router.claim` / `reserve` / `release` semantics, and `Router.candidates`' "a pinned model still
gets the rest of the pool as backup" (which is what `max_attempts=1` exists to cap).

Traced every reserve/release pair by hand: the pin path (`reserve` :1556 → `finally release`
:1957), the claim loop (`claim` reserves, released at :1576 for a local bucket, :1582 for a
benched one, else in the `finally`), and the widen path (`reserve` :1638 → `finally` :1957).
**No leak.** The gap between the reserve sites and the `try:` at :1688 contains only attribute
reads and a zero-iteration loop, so the comment at :1675-1687 is substantively right even
though its headline ("THE TRY OPENS AT THE RESERVE") is literally an overstatement — both
faults it names (`json.dumps(schema)` at :1693, `Thread.start()` at :1784) are inside the try.
Not filed.

Marked-and-kept seen, not filed: the eight `if pinned:` guards below :1666 are declared
unreachable-as-False by the invariant note at :1666-1671 and kept deliberately as documentation
of which branches touch the pinned bucket.

### MINOR — the unparseable-strike counter latches for the `<bucket unresolved>` key
**Where:** src/cascade_bridge.py:2002-2007 against src/cascade_bridge.py:2019-2028
**What:** when `_bucket_of` cannot resolve the answering model, strikes are counted under the
sentinel key `_key = _bucket or "<bucket unresolved>"` (:2002) and the ledger row is written as
`"unparseable reply (%d consecutive from this bucket): %s"` (:2006). The reset at :2024-2028 is
`_reset = _bucket_of(...)` — a REAL bucket only — so the sentinel's count is never cleared.
**Why it is wrong:** the comment immediately above the reset states the invariant the reset
exists to keep: *"`_UNPARSEABLE` counts CONSECUTIVE failures; a cumulative count would bench any
long-lived bucket eventually, whatever its success rate, which is the latching-counter fault
this project has now filed against `standards`' progress row as well."* For
`<bucket unresolved>` the counter IS cumulative and monotonic for the life of the process, so
the number written into `POOL_UNRECOGNISED.json` says "N consecutive" while meaning "N ever".
It cannot cause a wrong bench — :2010 requires a truthy `_bucket` — so the harm is confined to
the ledger text, which is exactly the text order `5448a236b884` added the counter for a reader
to act on. A long-lived worker whose engine `model` events stop resolving would report a
steadily climbing "consecutive" figure that no success ever resets.
**Confidence:** read both blocks and `_bucket_of` (:371-391, returns `""` on no match); traced
the only two writers of `_UNPARSEABLE`.

### INFO — `ask()`'s comment names `_LAST_TRIED`, which does not exist
**Where:** src/cascade_bridge.py:1465
**What:** *"`_LAST_TRIED` is filled by `_ask_call` with the buckets it actually claimed"*.
**Why it is wrong:** the thread-local is `_TRIED` (:1401), filled by `_tried_add` and read by
`_tried()`. `grep -rn "_LAST_TRIED" src/` returns this comment line and nothing else. The
mechanism described is correct; only the name is a fossil of an earlier spelling.
**Confidence:** grepped the whole tree.

### INFO — `dead_forever()`'s enumeration of `prove()`'s verdict vocabulary is now short by one
**Where:** src/cascade_bridge.py:460-462 against src/cascade_bridge.py:2156
**What:** *"`prove()` has only ever written a five-word vocabulary into `verdict`: `local`,
`provider disabled`, `no API key`, `answers`, `no answer`, or an exception's class name."*
**Why it is wrong:** `prove()` also writes `"model disabled"` (:2156), added with the
disabled-model branch. The paragraph's CONCLUSION is untouched — `"model disabled"` no more
contains a status code or a provider's wording than the other five do, so the argument for
reading `reason` as well as `verdict` still holds exactly. Filed as INFO because it is an
enumeration in a docstring that the code overtook, in the one function whose whole subject is a
classifier that could not see what it classified.
**Confidence:** read `prove()`'s five `out.append` sites and the `provider_ready` branch in
`cascade/router.py:139-145` that supplies `provider disabled` / `no API key`.

---

## Summary of what was looked for and not found

No module in this batch showed: a swallowed exception that converts a failure into a plausible
negative result (every `except` in the batch either notes, raises a named type, or is explicitly
argued as total on a diagnostic path); a read-modify-write on shared state without a
compare-and-swap (`catalogue_aurora` uses `roll.update_rows`, `cascade_bridge.record_unrecognised`
uses `replace_if_unchanged` plus a read-back, `corpus_db.rebuild` is whole-file with a
pid+thread temp); a signature drifted from its caller (checked `roll.update_rows`,
`pipeline.write_record_catalogue`, `silence.write_json` / `replace_retry` /
`replace_if_unchanged` / `digest_of` / `append_line`, `feats.api` / `fetch` / `strip_wikitext`,
`assay.instrument` / `axis_score`, `custodes.convene`, `Router.claim` / `reserve` / `release` /
`limits_for` / `provider_ready` / `model_status`); or an error path returning success — except
the one at `backfill.py:470`, filed above.
