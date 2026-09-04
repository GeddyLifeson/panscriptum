# Sweep 43, Batch 04 — audit

Files read in full: `src/standards.py` (2247 lines), `src/completeness.py` (753 lines),
`src/onomast.py` (608 lines), `src/withdraw_chapters.py` (479 lines), `src/snapshot.py`
(376 lines), `src/cleanup.py` (321 lines), `src/tempus.py` (274 lines), `src/compress_store.py`
(149 lines).

General note: `standards.py`, `completeness.py`, `onomast.py`, `withdraw_chapters.py` and
`snapshot.py` are exceptionally heavily self-documented with prior audit fixes (dozens of named
"order" hashes each describing a found-and-fixed defect). Most of the obvious defect classes in
those five files have already been closed by earlier sweeps; this pass looked specifically for
what those prior passes had not yet caught. `cleanup.py`, `tempus.py` and `compress_store.py`
carry much less of that history and are correspondingly less picked-over.

---

## src/cleanup.py

### FINDING 1 — SEVERITY: MAJOR
`src/cleanup.py:101-102` (the `_MARKUP` list, second entry)

```python
(re.compile(r"\s*\(\s*[^()]*?,\s*[A-Za-z]+\s*\?\s*\)"), ""),   # "(フランス, Furansu ? )"
```

**What actually happens.** This regex was written to strip the MediaWiki ruby-annotation
shape `(フランス, Furansu ? )` — foreign name, comma, romanisation, romaji-uncertainty `?`,
all inside one parenthetical — by deleting the whole parenthetical outright (replacement is
`""`). It has no check that the matched text is actually non-Latin/ruby. Any plain-English
aside of the shape `(<anything without parens>, <one word>?)` matches identically and is
silently deleted whole. Verified live against the regex:

```
'a character (Bob, right?) who appears once'          -> 'a character who appears once'
'the plan (or so we thought, really?) failed'          -> 'the plan failed'
'a device (see below, why?) that explodes'             -> 'a device that explodes'
```

I then searched `data/records/*.json` for descriptions where this pattern currently matches
ASCII-only text (i.e., plausible plain English, not ruby) and found three live, unrepaired
examples already sitting in the corpus today, none of them yet run through `--apply`:

```
Marvel        / Thor Annual Vol 4 1  -> " (and, uh, Hawkeye?)"
Transformers  / Ranger               -> " (odd for someone who likes trees, no?)"
Transformers  / Mister Flappy        -> " (Strange, huh?)"
```

**Why it matters.** This is the exact failure class the module's own docstring for
`_ruby_question_mark` (lines 63-96, immediately below this pattern) spends 30+ lines describing
and fixing — for a *sibling* pattern (the bare `?`-before-`)` stripper), which was found to have
silently deleted 55 real English question marks (`(Q Who?)` -> `(Q Who)`, etc.) before it was
given an explicit non-ASCII check (`any(ord(c) > 127 for c in s[j:i])`). Pattern 2 does the
*same job* (recognising the ruby shape) with *no* such check, and is *more* destructive than the
bug already fixed next to it: it deletes the entire parenthetical aside, not just a punctuation
mark. `clean_description` runs over every catalogued description under `--apply`, and this
module's own docstring calls the description "the evidence every later volume quotes from" —
text destroyed this way cannot be reconstructed without going back to the wiki.

**Suggested remedy.** Give pattern 2 the same non-ASCII guard `_ruby_question_mark` already has
— e.g. turn it into a function replacement that only deletes the match when the text inside the
parens contains a non-ASCII character (as the real ruby shape always will), and leaves plain
English text untouched. This is a mechanical, well-scoped fix (RUN-tier, given it touches a
regex whose behaviour needs re-verifying against the corpus afterward, as the docstring already
does for its sibling).

### FINDING 2 — SEVERITY: MAJOR (Hard Rule 0 / self-contradiction)
`src/cleanup.py:299-309`

```python
if unwritten:
    print(f"\nNOT WRITTEN — {len(unwritten):,} record(s) refused the write ...")
    for s in unwritten[:12]:
        print(f"     {s}")
    if len(unwritten) > 12:
        print(f"     ... and {len(unwritten) - 12:,} more")
```

**What actually happens.** The `unwritten` list — the sources whose corrections were computed
but never landed on disk because `PL.write_record` refused the write — is capped to the first 12
entries when printed, with a "... and N more" summary for the rest.

**Why it matters.** This directly contradicts the block's own sibling comment eighteen lines
above it, `cleanup.py:272-280`:

> "FIVE ROSTERS, ALL OF THEM UNCAPPED (Hard Rule 0, sweep42-batch03). Every one of these was cut
> to four, five or six rows with nothing said about the remainder, **while the `unwritten` list
> twelve lines below has always been printed in full with its own comment explaining why
> summarising it would be dishonest.**"

That claim is false as the code stands: `unwritten` *is* capped, at exactly 12. There is no
other record of which sources beyond the first 12 failed to write (unlike the other four
rosters in this file, which are printed in full) — `NOT WRITTEN` records are not persisted
anywhere else the way `output/withdrawn_<date>/catalog.withdrawn.json` persists a withdrawal
manifest in `withdraw_chapters.py`. An operator debugging a `--apply` run with more than 12
refused writes sees only the first 12 names and has no way, short of re-running the tool and
diffing catalog state, to learn which other sources still hold uncommitted corrections. This is
Hard Rule 0's exact shape: a smaller universe (12 names) returned wearing the same shape ("NOT
WRITTEN — N record(s)...") as the real one.

**Suggested remedy.** Remove the `[:12]` cap and the "and N more" line; print every name in
`unwritten`, matching the discipline the other four rosters in this same function already follow
(and matching what the comment already claims this list does). LOCAL-tier: mechanical, one-line
change (`for s in unwritten:` and delete the two lines below it).

---

## src/standards.py

No new correctness or safety-detector defects found beyond what the file's own extensive
"order ..." comments already document as fixed. This file has clearly been through many prior
audit passes; every cap, every silent-drop path, and every discarded-verdict shape I checked was
already covered by an explanatory fix comment and verified against the surrounding code to
actually be fixed as claimed (e.g. the `_dropped`/aggregate-standard mechanism at the bottom of
`check()`, the three-valued `ollama_runner_up()` handling at :1784-1823, the `job_stamp()`
carry-forward logic at :403-412, `provider_pool_denominator()` at :564-638). I did not find a
place where the fix comment's claim and the code that follows it actually disagree.

## src/completeness.py

No new correctness defects found. The `audit()`/`work()`/`land()` pipeline's three-state
handling (measured / unreliable / genuinely-absent) and the shrink-floor + atomic-write guards in
`land()` were checked line by line and match their docstrings. One console-only, low-risk
formatting truncation is noted below under Questions/INFO.

## src/onomast.py

No new correctness defects found. `well_formed()`'s four phonotactic constraints, the
GENRE_WEIGHT/FEATURE_WEIGHT tie-break arithmetic in `register_for()`, `coin_well_formed()`'s
three-tier fallback, and the append-only retire/standing logic in `name_worlds()` were traced by
hand and checked against the constraints their comments claim; all held.

## src/withdraw_chapters.py

No new correctness defects found. `_file_state()`'s three-way live/gone/unavailable
classification, `_archive_name_free()`'s FileNotFoundError-only "free" answer, the per-entry
`entry_left`/`amended` partial-withdrawal bookkeeping, and the final `bad` / return-code
computation at the end of `main()` were checked and are internally consistent with their
docstrings.

## src/snapshot.py

No new correctness defects found. `_rel()`'s containment check, `_safe_join()`'s independent
containment check on the restore side, `_dir_matches()`'s file-by-file byte comparison, and the
nanosecond+pid snapshot-id collision guard in `before()` were all checked and match their stated
purpose.

## src/tempus.py

No defects found. This module is pure/derived arithmetic (no I/O, no mutable state) built on
`assay.BAND_EDGES`/`LADDER`. Checked `rung_description_length()`, `band_resolution()` (including
its top-of-ladder inheritance branch), `is_present_at()`'s inequality direction against its own
docstring, and `retrocausality_beta()`'s zero-cost boundary at `<= 0`. All consistent.

## src/compress_store.py

No defects found. `store()`'s pid+thread-qualified temp name, `replace_retry`-then-raise
discipline, and `load()`'s content-hash re-verification against the filename it was loaded from
were all checked and are correct and consistent with their docstrings.

---

## QUESTIONS (for the owner — not filed as work orders)

**Q1 — `completeness.py:293`, `catalogued_counts()`: `c[str(e.get("category") or "?")[:40]] += 1`.**
Category names are truncated to 40 characters when building the per-source `by_category` count
dict. This is used only as a Counter key for a `catalogued_total`/`by_category` summary, not as
an ordered listing subject to Hard Rule 0's truncation concern in the same way a roster is — but
it could, in principle, silently merge two distinct category names that happen to share a
40-character prefix. I found no such collision in the current data, and it is a much smaller
practical risk than the finding at `standards.py:1401` (already fixed) that motivated checking
this. Flagging only because it is the same shape at a shorter width; whether it is worth
tightening is a curatorial judgment about a corpus-internal key, not a clear fault.

**Q2 — `completeness.py:727,743`, `main()`'s console printer: `str(r["source"])[:33]`.**
Source names are truncated to 33 characters for column alignment when printing the coverage
table. I checked all 208 sources in `data/WIKI_HOSTS.json`: 19 exceed 33 characters, and none
of them currently collide on their first 33 characters, so this is presently cosmetic only (the
full name is preserved untouched in `COMPLETENESS.json`; only the console table's column is
narrowed). Given that `standards.py` already had — and fixed — the identical shape at 18
characters after it caused a *real* collision ("every source of the form 'Warhammer Fantasy *'
folded onto one string"), this is worth the owner's awareness as a near-miss of the same class,
even though it is not currently causing a collision.
