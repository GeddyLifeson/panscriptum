# AUDIT — sweep run56, batch 08

Modules read in full, line by line, this run: `workorders.py` (2,139 lines), `liveness.py`
(1,054), `wiki_source.py` (789), `address_space.py` (673), `canon_backup.py` (536),
`recover_folder_records.py` (379), `grounding.py` (361), `profile.py` (295).

AUDIT ONLY. Nothing under `src/`, `data/`, or `state/` was written. Two read-only measurements
were taken: `python src/liveness.py --quiet` (pure AST scan; writes nothing) and a scratch
`python -c` snippet importing `profile` to exercise `decode()` on hand-built strings (no disk
writes; confirmed by reading the function before running it).

A near-identical audit of this exact batch already exists at
`handoff/sweep55/AUDIT_batch08.md` (dated 2026-09-10, one day old). Several findings below were
first surfaced there; every one reused here was independently re-verified against the live
source in this session (re-read the cited lines, re-ran the measurement, or both) before being
restated — none is included on the strength of the prior document alone. New findings this run
are marked as such.

---

## workorders.py

Read all 2,139 lines. Traced `_load`/`_mutate`'s compare-and-swap, `file_order`'s LOCAL
door-check, `resolve`/`resolve_code`/`reroute`'s three-way return dispositions, and all twelve
`_fire(...)` call sites in `sweep_detectors` for polarity.

**Nothing found wrong in the CAS/write path, `resolve`'s land-then-exist ordering, or the
`_fire` polarity.** Checked each of the twelve `_fire` predicates by hand against what it
watches: `not bad` (1216), `chain_ok` (1220), `n <= _D.LIVENESS_CEILING` (1234), `bh_age <=
BINDING_HEALTH_MAX_AGE` (1300), `not hits` (1421, gated on `scanned`), `f is None` (1456, in a
loop over `BATTERY_CODES`), `not stranded` (1509), `not scratch` (1608), `not _cap["open_hits"]`
(1651), `not _ghosts` (1704), `not _stuck` (1764), `not _cites` (1816). Every one is TRUE only
when the watched condition is healthy — `ok` correctly means "resolve", not "file".

### QUESTION — `file_order`'s LOCAL door-check fails open (by design, with a stated backstop) when `local_agent` cannot be imported

**Where:** src/workorders.py:512-525.

```python
if handler == "LOCAL":
    try:
        import local_agent as _LA
        targets = sorted(set(m for m, _ in WHERE_TARGET.findall(str(where or ""))))
        if targets and all(_LA._denied_target(t) for t in targets):
            found_by = ...
            handler = "RUN"
    except Exception:
        # Cannot tell whether the target is denied -- file as addressed. The post-hoc
        # detector still catches this on the next sweep if `local_agent` stays unreachable.
        pass
```

**What:** if `import local_agent` raises (module missing, broken, or import-time exception),
the order is filed at LOCAL exactly as asked, with no re-address and no note that the check
could not run.

**Why it is a question, not a defect:** the comment states the tradeoff explicitly and names
the compensating control — `ORDER_ADDRESSED_TO_A_RUNG_THAT_CANNOT_REACH_IT` in
`sweep_detectors` (workorders.py:1749-1786) re-scans every open LOCAL order against the same
denylist on the next sweep and re-flags it. So a bad import here degrades "caught at filing
time" to "caught one sweep later", not "never caught" — a genuine but bounded and independently
covered gap. Flagged because it is a fail-open in a safety-adjacent path; not filed as a defect
because the redundancy is real and deliberate.

**Confidence:** verified by reading both sites; not exercised (would require breaking
`local_agent` on disk).

### Nothing else found in workorders.py

The historical `file.py:NNN`-shaped citations inside this file (lines 806-807, 838) name
`src/workorders.py`, `workorders.py`, `deprecated/catalogue_local.py`, `manifest_builder.py:424`,
`roll.main()`, and `audit.py:190-193` as illustrative/historical examples ("twins closed on
2026-09-02..."), not live pointers a reader is meant to follow today. Checked
`manifest_builder.py:424` and `audit.py:190-193` directly — neither matches what the sentence
describes, but the sentence is dated, past-tense, and about a specific historical closure, not a
present-tense "see line X" pointer, so this is not filed as a STALE_CITATION-shaped defect.

---

## liveness.py

Read all 1,054 lines. Traced `_modules → _parse → _credit_attrs/_scope_aliases → scoped →` the
five `scan()` passes, then `reachability()`'s four subprocess gates. Ran
`python src/liveness.py --quiet`: **48 findings today (dead 39, dead_module 9, dead_class 0,
tautology 0, phantom 0, unparsed 0)**, against `drill.LIVENESS_CEILING = 52` — within ceiling,
no ratchet breach.

### DEFECT — the "profile.py's round trip" citation in the module's own founding docstring is stale

**Where:** src/liveness.py:7-9.

```
  * `profile.py`'s round trip -- FIXED, now at `profile.py:196-208`: it used to compare a decoded
    field against the input it was handed, so `d["profile"] != r["profile"]` was tautologically
    False, green for ever. It now re-encodes what `decode()` extracted and compares THAT.
```

**Why it is wrong:** read live `profile.py:196-208` — it is inside `build_all()`
(`silence.note("profile.py:genres-unreadable")` at 196 through `register =
gspec.get("register", "classical")` at 208), nothing to do with the round trip. The actual
re-encode-and-compare logic (`re_encoded = encode(d["address"], ...)`, `if d["address"] !=
r["address"] or re_encoded != r["profile"]`) is at **profile.py:268-271**, inside `main()`. The
claim ("it now re-encodes...") is true of the current code; the line citation naming where to
find it is not.

**Confidence:** high. Read both cited ranges directly this session; this is the module's own
worked example of the class of bug it exists to find, and the citation naming its fix has
rotted. (Matches a finding in `handoff/sweep55/AUDIT_batch08.md`; independently re-verified here
against current `profile.py`.)

### Nothing else found in liveness.py

Ran the scan live and manually inspected the `scale_theories`/`resonance` receiver-resolution
example the docstring uses to justify the per-function alias scoping (order 6c479972e838) —
`R.hodge_decompose` did not appear in the live DEAD list, matching the docstring's claim that the
receiver-aware pass resolves it correctly. The `EXEMPT_MODULES`/`EXEMPT_CLASSES` empty-dict
conjuncts (lines 98, 114) are marked by their own comments as deliberately-empty starting
content with a written reason each (orders e3451d1e056d, 962bc293ec32) — not filed. The `if seen
else set()`-shaped tautology the file itself once had (referenced in the comment at 548-551) is
gone from the current code (line 552 is a plain `set().union(...)`, no conditional) — the
comment is now describing a fixed-away shape in the present tense, which is a documentation
staleness rather than a code defect; not filed separately since it does not point at a wrong
line number (no `file.py:NNN` citation there, just prose).

---

## wiki_source.py

Read all 789 lines. Traced `_get`'s retry/throttle, `resolve_wiki`'s hosts-map-first path, the
`all_categories → discover_categories → find_categories` chain and its `CATEGORY_MIN_PAGES`
floor, and the four walkers converted to raise-on-failure under order de0681cb9edc
(`all_categories`, `category_members`, `extracts`, and NOT `rank_by_size`, below).

### DEFECT — `category_floor_report()` has no caller anywhere in the repo, so the owner-ruled "report the dropped count" half of the category floor is declared but not in effect

**Where:** src/wiki_source.py:402-418 (the function), :399 and :490-491 (`_FLOOR_APPLIED`,
written but never read outside this file's own report function).

**What:** the constant above it states the ruling this function exists to satisfy — "order
4d78c426afb3; owner ruling 2026-09-08 ... the 40-page MediaWiki category floor is declared and
its dropped count reported" — and `category_floor_report()`'s own docstring says it "reports
what IS known -- the floor that was applied and how many categories cleared it, per wiki."

**Why it is wrong:** `grep -rn "category_floor_report"` across the whole repo returns only its
own definition, its two internal mentions in this file, and one line in an old audit doc
(`handoff/sweep48/AUDIT_batch13.md`) — no caller anywhere, including `catalogue_web.py`, which
is the only module that drives `find_categories`/`all_categories`. Confirmed independently:
`python src/liveness.py` reports `wiki_source.py:402 category_floor_report()` as DEAD. The
ruling's reporting half exists in a file and never runs — the same shape Hard Rule -1's fourth
property names for safeties ("a safety that exists in a file is not a safety that is running"),
applied here to a report rather than a guard.

**Confidence:** high — grepped the whole repo, cross-checked with `liveness.scan()` output
independently produced this session, and read the only write site of `_FLOOR_APPLIED`.

### DEFECT — `rank_by_size`'s batch fetcher swallows a transport failure and returns `{}`, unlike its three siblings which were deliberately converted to raise

**Where:** src/wiki_source.py:731-737.

```python
def fetch(batch):
    try:
        return _api(subdomain, {"action": "query", "prop": "info",
                                "titles": "|".join(batch), "redirects": 1}, timeout=40)
    except Exception:
        silence.note("wiki_source.py:rank-by-size-api")
        return {}
```

**Why it is wrong:** `all_categories` (line 476-477), `category_members` (line 681-683), and
`extracts` (line 708-710) all `silence.note(...)` **then re-raise**, and each carries a comment
explaining that a caught-and-swallowed partial result used to read as a smaller-but-complete
answer (the exact Hard Rule 0 shape: "a failed walk RAISES; it is never returned as the answer").
`rank_by_size`'s own `fetch` is the one walker in this file that still notes and returns `{}` —
a batch that fails to fetch contributes no `length` for its 50 titles, so `sizes.get(t, 0)`
scores all of them 0 and `sorted(titles, key=lambda t: -sizes.get(t, 0))` silently sinks them to
the bottom of the ranking rather than surfacing the failure. Not a live truncation today: both
call sites in `catalogue_web.py` (lines 288 and 482, read directly) pass `top=None`, so nothing
is actually cut from the returned list — but the *ranking itself*, which Hard Rule 0 explicitly
carves out as encouraged ("rank the richest material first ... if a run is interrupted"), is
silently corrupted by an unreported transport failure, and it becomes a real truncation the
moment any future caller passes `top=`.

**Confidence:** high — read all four fetch/walk functions side by side and both call sites in
`catalogue_web.py`.

### Nothing else found in wiki_source.py

`CATEGORY_MIN_PAGES = 40` is a declared, owner-ruled floor (order 4d78c426afb3) with its
rationale and its cost stated in the same comment block — not a hidden cap. `find_categories`'s
`limit` defaults to `None` and both real call sites pass `top=None`/no limit. `clean_titles`'s
O(n) dedup and `category_members`'s pagination were read and are correct. `verify_wiki_matches`'s
threshold arithmetic (`matched >= max(1, len(distinctive) // 2)`) is not a tautology.

---

## address_space.py

Read all 673 lines. Verified `FIELDS`/`WIDTHS`/`TOTAL_BITS` are derived from `_tier_counts()`
and `cosmography` constants, never hand-typed; traced `pack`/`unpack`/`assign`/`shelfmark`'s
uncharted-tier handling.

### DEFECT — two stale cross-file line citations in the same comment, both pointing past their targets

**Where:** src/address_space.py:643-644.

```python
        # Windows case here, since `pipeline.py:2138` (`_phase_input("SHELFMARKS.json")`) reads
        # this file as a phase input and `standards.py:1177` reads it on its own clock, and
```

**Why it is wrong:** checked both targets directly.
- `pipeline.py:2138` today is inside an unrelated comment about batches acquiring unjudged
  entries after closing ("nothing reopened a batch that acquired unjudged entries afterwards").
  The actual `marks, m_bad = _phase_input("SHELFMARKS.json")` call is at **pipeline.py:2845**
  (`grep -n SHELFMARKS src/pipeline.py` confirms this is the only `_phase_input` call on that
  file).
- `standards.py:1177` today sits inside the swallowed-failure ledger's probe-label tuple
  (`"hostcheck.py:probe", "hostcheck.py:candidates", ...`), unrelated to SHELFMARKS. The actual
  read (`open(os.path.join(HERE, "data", "SHELFMARKS.json"), ...)`) is at **standards.py:1375**.

**Confidence:** high — read both cited lines and grepped both files for the real call sites this
session.

### QUESTION — `citation_card()`/`seed_from_card()` are dead code, but this is a known, already-decided standing question, not a new finding

**Where:** src/address_space.py:330 (`citation_card`), :360 (`seed_from_card`).

**What:** `python src/liveness.py` reports both as DEAD (no caller anywhere in `src/`), confirmed
by `grep -rn "citation_card\|seed_from_card"` across the repo, which turns up only the
definitions and a note in `handoff/run35/checks_L4.py`.

**Why this is a QUESTION and not a defect:** `handoff/run35/checks_L4.py:196-207` already records
this exact pair as "confirmed dead (zero callers in src/, handoff/, docs/, reference/) but were
NOT deleted -- map_seed() is the documented 'prefer this' alternative and IS used elsewhere, and
citation_card() carries an unfixed decimal-clamp bug (sweep33 #7) that would need resolving
either way before deletion is a clean call. This is a standing owner question." Restated here
only because it surfaced independently via this run's own `liveness.py` execution, not as a new
finding — the disposition is already on record as "left for owner call."

### Nothing else found in address_space.py

`pack()` raises rather than wraps on overflow; `assign()`'s `fit()` correctly uses no modulo
(confirmed the comment's claim that a modulo would silently truncate an out-of-range tier); the
`UNADDRESSED`/`charted_gaps()`/`shelfmark(addr, uncharted=...)` blank-printing path was traced
end to end and behaves as documented — an uncharted tier prints `?` rather than a fabricated
zero. `main()`'s SHELFMARKS.json write is gated on `silence.write_json`'s return value and exits
1 on a denied replace, matching its own comment.

---

## canon_backup.py

Read all 536 lines. Traced `members(strict=)`'s all-or-nothing refusal, `snapshot()`'s
write-verify-rename-manifest sequence, `prune()`'s two loops, `verify()`'s comparisons, and
`restore()`'s open-source-before-create ordering.

**The module's stated invariants hold on reading:** `members(strict=True)` refuses (raises)
rather than silently returning a partial inventory if any declared `CANON_FILES`/`CANON_DIRS`
entry is missing; `snapshot()` re-hashes every archive member against the source before
renaming into place and deletes the temp file on any digest mismatch; `verify()` fails closed
(returns `False`) with no manifest, with an unparseable manifest, and when the manifest records
a member the archive does not contain; `prune()` counts a half-deleted pair (zip + manifest) as
NOT removed; `restore()` opens the zip member before creating the destination file, so a bad
`rel` cannot leave a plausible-looking empty file behind.

### DEFECT — a self-referencing line-range citation for `verify()`'s fail-closed arm is stale

**Where:** src/canon_backup.py:223.

```python
    # than an absent one: `verify()` fails CLOSED with no manifest (:312-320) but a present one
```

**Why it is wrong:** lines 312-320 today are the tail of `newest()` (`return os.path.join(ROOT,
snaps[-1]) if snaps else None`), the `def verify(path=None):` line, and the opening lines of its
docstring — not the fail-closed check. The actual `if not recorded: ... return False, notes +
[...]` arm this comment is pointing at is at **canon_backup.py:348-356**.

**Confidence:** high — read lines 306-356 directly this session.

### QUESTION — `verify()` returns `ok=True` when a canonical file recorded in the snapshot is GONE from the live tree

**Where:** src/canon_backup.py:404, 436-442.

**What:** `gone = [r for r in recorded if r not in live]` is appended to `notes` when non-empty,
but the function unconditionally `return True, notes` — so `main()` prints `VERIFY: ok` and
exits 0 even when a canonical record file the snapshot preserved has since vanished from
`data/records/`.

**Why this is a question, not a clear defect:** the same docstring states "Divergence is NOT a
failure. The live tree moves constantly..." as a deliberate design stance, while the same
function's own comment calls a `gone` file "the single most actionable thing this module can
tell anyone" — the two statements pull in different directions for this specific case. Read as a
design decision worth the owner's attention (whether a vanished canonical file should flip the
exit code) rather than an unambiguous bug, since both readings are defensible and changing it
changes an exit code a supervisor may already be gating on.

**Confidence:** verified by reading `verify()` in full; not exercised against a real missing
file.

### Nothing else found in canon_backup.py

`snapshot()`'s empty-items guard (`if not items: raise ...`) cannot currently fire given
`members(strict=True)`'s own refusal-on-any-gap behavior and non-empty `CANON_FILES`/
`CANON_DIRS` tuples — harmless dead guard, not filed as a defect since it is belt-and-braces
rather than a check standing in for a real one. `prune(keep=0)` prunes nothing (documented
"retain none" reading, errs safe). The stamp-collision fix (pid+thread in both the temp name and
the final snapshot name) was traced and is correctly applied to both.

---

## recover_folder_records.py

Read all 379 lines. Re-verified the header's dated measurements against live data:
`data/SWEEP_ROLL.json` holds 215 rows with exactly 6 at `entry_count == 0`; `LOCAL_REGISTER.json`
holds 14,576 items; the `"ME"` bucket holds 7 items mapped from exactly 7 roll sources, matching
`EXCLUDED_REGISTER_SOURCES`'s comment byte for byte.

### DEFECT — the "SHORT AGAINST THEIR OWN MAPPING" report asserts every listed source landed as a record, which is false for two of the three exit paths that can populate it

**Where:** src/recover_folder_records.py:193-194 (where `short_sources[name]` is recorded)
against :217-225 (`already`/`skipped_populated` exit) and :290-299 (`WRITE DENIED` exit), and
the report text at :356-359.

**What:** `short_sources[name] = list(shortfalls)` is recorded deliberately early in the loop —
before the record is even built — specifically so a source that yields nothing at all is still
reported (the comment at :190-192 says so explicitly). But the loop can still exit afterward via
`if already: skipped_populated.append(name); continue` (nothing written — an existing populated
record was left alone) or via a denied `silence.write_json` (`denied = True; continue` — nothing
written). The report at the end of `main()` nonetheless says, for every name in `short_sources`
without exception:

> These landed as records and were stamped 'catalogued', and work selection is entry_count == 0,
> so nothing will revisit them on its own

**Why it is wrong:** for a source that is both short and already-populated, nothing landed —
the pre-existing (better) record was correctly left untouched, which is precisely the outcome
that must NOT be revisited, the opposite of what the sentence claims. For a source that is short
and denied, nothing landed either, and the roll is deliberately left at `entry_count: 0` so a
future run WILL revisit it — again the opposite of the sentence. The claim is stated
unconditionally in the one bucket whose own surrounding comment already flags it as "the one
bucket whose members otherwise look like successes" — exactly where an inaccurate "this landed"
claim is most likely to be trusted at face value.

**Confidence:** high — traced all three ways a name can reach `short_sources` and still leave the
loop without writing, and read the unconditional report sentence.

### Nothing else found in recover_folder_records.py

The `mapped is None` vs. falsy-empty-list distinction (line 141, order 37d3d588847a) is correct
and was re-verified against `FOLDER_SOURCE_MAP.json`: 'Lost Mines of Phandelver' and 'the Witch
Tradition' are present with `[]`, the other 4 empty sources are genuinely absent from the map.
The write-then-roll-update sequencing (per-record `silence.write_json` gated at :290, followed
by a separate compare-and-swap `roll.update_rows` merge at :318 rather than a whole-document
land) is correct and matches its own extensive commentary. `EXCLUDED_REGISTER_SOURCES = {"ME"}`
is applied before the shortfall/entry loop for every mapped register source — a source whose
mapping names only excluded register sources would land in `skipped_no_items` ("mapped, but the
register holds no items for them"), which is not exactly accurate (the register does hold items,
they are deliberately excluded) but is NOT live today: measured directly, none of the 6 current
`entry_count == 0` sources maps at `"ME"`, so this path is dormant rather than active. Noted here
for completeness but not filed as a live defect.

---

## grounding.py

Read all 361 lines. Traced the `_BAD_CHARS` self-check, `_ORIGIN`, the five `GROUNDINGS` cue
tables, and the uncapped `classify_text`/`classify_source` path.

**Verified clean:** `cap` is refused loudly (`raise SystemExit`) rather than honoured, matching
its docstring; `top` in `classify_text` defaults to `None` so `most_common(None)` returns the
whole field, and `classify_source`'s `total = sum(s for _, s in ranked)` is therefore a
full-field denominator, not a truncated one; every diagnostic loop in `main()` is uncapped and
explicitly sorted for meaning rather than scrape order; `_BAD_CHARS` correctly reads its own
source file to guard against the control-character-corruption failure mode this project has hit
repeatedly.

### Nothing found wrong in grounding.py

No caps, no fail-open paths, no tautologies or checks-that-cannot-fail located. The one
mechanically-interesting shape — `classify_text` always returns exactly 5 rows because
`Counter.__setitem__` inserts a key even at value 0, so `classify_source`'s `if not ranked`
disjunct at line 240 can never actually fire — is genuinely a dead branch, but it is pure
defensive code around a working codepath (the reachable half, `ranked[0][1] < floor`, is the one
doing the work) and is not a check standing in for a real safety; not filed as a defect.

---

## profile.py

Read all 296 lines. Traced `B32`/`_B32_CLASS`/`_PROFILE_RE`'s construction, `_b32`/`_unb32`,
`encode`'s band-degrade path, `decode`'s five reconstructions, and `main()`'s round trip.

### DEFECT (MAJOR) — `decode()` validates the alphabet of each feature character but not its per-axis range, so a string that passes the regex validator crashes with a bare, unhelpful `IndexError` instead of the intended `ValueError`

**Where:** src/profile.py:91-92 (the pattern), :104-105 (`AXES`), :163 (the lookup).

```python
_PROFILE_RE = re.compile(r"PS-(%s+)-([a-z]{2})([a-z])-(%s{4})-([0-9au])([0-4])"
                         % (_B32_CLASS, _B32_CLASS))
...
AXES = [("landform", WS.LANDFORM), ("climate", WS.CLIMATE),
        ("condition", WS.CONDITION), ("tech", WS.TECH)]
...
features = {axis: tbl[B32.index(ch)][0] for (axis, tbl), ch in zip(AXES, feats, strict=True)}
```

**What:** the feature group in the validating regex accepts any 4 characters from the full
32-symbol `B32` alphabet in each of the 4 positions, but each position's actual table
(`WS.LANDFORM`, `WS.CLIMATE`, `WS.CONDITION`, `WS.TECH`) is far shorter. Measured directly from
`src/worldseed.py`: **LANDFORM has 6 entries, CLIMATE 6, CONDITION 3, TECH 4.** `encode()` can
therefore only ever emit `B32[0..5]`, `B32[0..5]`, `B32[0..2]`, `B32[0..3]` respectively, but
`decode()`'s validator will accept `B32[0..31]` in every one of those four positions.

**Reproduced directly this session** (read-only; imports `profile`, writes nothing):

```
>>> profile.decode("PS-1-myc-000z-u0")
IndexError: list index out of range
>>> profile.decode("PS-1-myc-0000-u0")
{'address': 1, ... 'features': {'landform': 'archipelago', ...}, ...}   # ok
```

**Why it is wrong:** the comment block immediately above the pattern (lines 72-89) explains, at
length and citing three prior filings (`ed46a60bc2dc`, `559b09f35e5c`, `6f1652a21efb`), that this
exact class of bug was fixed once already — a profile string with an out-of-alphabet character
used to sail past the regex and crash with a bare `ValueError: substring not found` inside
`_unb32`, "naming neither the profile nor the offending character," and the fix was to build
the validator's alphabet from `B32` itself so nothing invalid could reach the decoder. That fix
narrowed the *alphabet* check and left the *per-axis range* check unguarded — which is the
larger hole by count (26 of 32 admitted symbols are out-of-range for landform, 26 for climate,
29 for condition, 28 for tech) and produces exactly the failure mode the comment says was
already closed: a crash from inside a private helper (here, the dict-comprehension's `tbl[...]`
lookup) that names neither the profile string nor which character was wrong.

**Confidence:** high — read the pattern, `AXES`, the lookup, and `worldseed.py`'s four table
definitions; reproduced both the crash and the success case by running `profile.decode()`
directly (read-only, no state touched).

### DEFECT — a self-referencing citation for `decode()`'s echoed-argument line points at a blank/unrelated line

**Where:** src/profile.py:263 (comment) citing "line 125".

```python
        # `d["profile"]` is decode()'s own argument echoed back (line 125 above) -- comparing it
```

**Why it is wrong:** line 125 is `def encode(address, genre, register, features,
band="unassayed", attested=0):` — the start of an unrelated function, not the echo. The actual
echo this comment means (`"profile": profile,` inside `decode()`'s return dict) is at **line
174**.

**Confidence:** high — read both lines directly this session.

### QUESTION — the format mnemonic's fourth letter names a field the code does not have

**Where:** src/profile.py:18, 27 (the grammar and gloss) against :104-105 (`AXES`) and the
`decode()` return key.

**What:** the profile grammar is documented as `PS-<address>-<gr><rg>-<lcce>-<band><att>`, glossed
"landform, climate, condition, **era**: what the world IS LIKE." The actual fourth axis, per
`AXES` and `decode()`'s own returned dict key, is `tech` (`WS.TECH`, values like `spacefaring`,
`medieval`), not an era/age field.

**Why this matters:** this module's own stated purpose is that the profile string is a
specification two people can exchange and decode identically ("a NAME WITH STRUCTURE is a thing
you can hand over"). A reader building or checking a profile string from the docstring's own
grammar line would look for a chronological/era digit and find a technology-level digit instead.

**Confidence:** high — read the grammar comment, `AXES`, and confirmed `decode()`'s output key is
literally `"tech"`.

### Nothing else found in profile.py

`B32` is exactly 32 unique symbols with `i`, `l`, `o`, `u` correctly absent; `_PROFILE_RE`'s
address and feature-group character classes are built from `B32` itself rather than retyped, so
those two cannot drift independently again. The band encode/decode/clamp path
(`"M3.52 ± 0.12" -> '3' -> "M3"`, `"M12" -> 'a' -> "M10"`) was traced and is correct. The round
trip logic at lines 260-271 genuinely re-encodes what `decode()` extracted and compares that
against the original string (rather than comparing `decode()`'s echoed argument to itself) — so
the tautology `liveness.py:7-9` describes as fixed **is** in fact fixed; only that citation's
line-number address is wrong (see the `liveness.py` finding above).

---

## Summary of findings, this run

**DEFECTs (verified against current source, several by direct execution):** 9
1. liveness.py:7-9 — stale citation to profile.py:196-208 for the round-trip fix
2. address_space.py:643-644 — two stale citations (pipeline.py:2138, standards.py:1177)
3. wiki_source.py:402-418 — `category_floor_report()` has no caller anywhere; owner-ruled
   reporting requirement declared but not in effect
4. wiki_source.py:731-737 — `rank_by_size`'s `fetch()` swallows transport failures unlike its
   three converted-to-raise siblings
5. canon_backup.py:223 — stale self-citation (:312-320) for `verify()`'s fail-closed arm
6. recover_folder_records.py:193-194/217-225/290-299/356-359 — "SHORT AGAINST THEIR OWN
   MAPPING" report claims every listed source landed as a record; false for two of three exit
   paths
7. profile.py:91-92/104-105/163 — `decode()` validates alphabet but not per-axis range; crashes
   with bare `IndexError` on a regex-valid-but-out-of-range profile string (MAJOR, reproduced)
8. profile.py:263 — stale self-citation ("line 125") for `decode()`'s echoed-argument line

**QUESTIONs:** 4
1. workorders.py:512-525 — LOCAL door-check fails open on `local_agent` import failure
   (compensating detector exists)
2. address_space.py:330/360 — `citation_card()`/`seed_from_card()` dead code (already a
   standing, documented owner question per handoff/run35, not new)
3. canon_backup.py:404/436-442 — `verify()` returns ok=True despite a gone canonical file
4. profile.py:18/27 — format mnemonic names "era", code has "tech"

**Clean (nothing found):** grounding.py in full. No new caps, truncations, or fail-open paths
found anywhere in workorders.py's write/CAS machinery, address_space.py's bit-packing, or
canon_backup.py's verify/snapshot/restore invariants.
