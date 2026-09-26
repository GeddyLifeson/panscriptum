# sweep64 batch15 — audit

Scope: every module below read in full, start to finish, sequentially, in chunks. No sampling,
no grep-only skimming.

  - src/read.py              1713 lines — read in full (5 chunks)
  - src/escalation.py        1445 lines — read in full (5 chunks) [SAFETY-CRITICAL]
  - src/corpus_db.py         1053 lines — read in full (4 chunks)
  - src/ingest_doc.py         702 lines — read in full (3 chunks)
  - src/prose_gate.py         545 lines — read in full (3 chunks) [SAFETY-CRITICAL]
  - src/burgs.py              442 lines — read in full (1 chunk)
  - src/grounding.py          361 lines — read in full (1 chunk)
  - src/halo.py               219 lines — read in full (1 chunk)
  - src/module_index.py       192 lines — read in full (1 chunk)

Total: 6,672 lines across 9 modules, all read.

## Prior-audit cross-check

`handoff/sweep63/AUDIT_batch15.md` covered exactly this module set (batch 15 carried the same
nine files last sweep, with `propagation.py`/`catalog.py` swapped for `halo.py`/`module_index.py`
this time). Its one VERIFIED finding was `read.py`'s `_names()` fallback (:259-264 as it stood
then): the whitespace-only join broke on any entity whose own name is joined by punctuation
("Mr. Fox", "T'Pol", "X-Men"). That is exactly the fix this brief's own M119 note describes
(2026-09-24, "AND EACH GAP ACCEPTS THE NAME'S OWN PUNCTUATION, AND ONLY THAT (sweep63 batch15)",
read.py:260-269) — so last sweep's finding is fixed, and this sweep's job was fresh eyes on that
exact fix, per the brief.

## Method

All nine modules carry this project's usual dense, numbered "order" comment style recording past
defects and fixes across sweeps 22-63 and multiple owner rulings. The great majority of the
priority list in this brief is already found, fixed, and commented in these files with a repro
and a measurement. This pass hunted for what those comments have not yet caught, with the two
brief-flagged fresh-eyes items given direct behavioral verification (small `python -c` scripts
run against pure, standalone logic extracted from the module — no import of the module itself, no
mutation, no drill, no network, no GPU) plus corpus queries against `data/records/*.json`
(read-only) to measure real-world scope. No file under `src/`, `data/`, `state/`, or `output/` was
edited, created, or deleted.

## Findings

### 1. VERIFIED — `src/read.py:270-286`, the M119 punctuation fallback matches only the entity's
own literal separator character, not any spelling a wiki might use for the same punctuation mark

The 2026-09-24 fix (M119) that closed last sweep's finding builds its match pattern by lifting the
literal separator characters straight out of the catalogued entity's own name:

```python
toks = [t for t in re.split(r'(\W+)', entity_f) if t]
...
for t in toks:
    if re.match(r'\w', t):
        body += re.escape(t)
    else:
        own = "".join(sorted(set(c for c in t if not c.isspace())))
        body += r'[\s' + re.escape(own) + r']+'
pattern = r'\b' + body + r"(?:'s|s)?\b"
```

This is a real improvement over the whitespace-only join it replaced, and its own comment
correctly measured "1,441 matches added across 172 names, 0 removed" plus 5 initialism
collisions from over-matching. But the fix has no counterpart for the *other* direction: it
assumes the sentence being tested spells the separator identically to the catalogue's own
spelling of it. This module already has a tool for exactly the opposite assumption —
`_norm_q()`, whose own docstring says it exists to "fold the punctuation a wiki and a model
disagree about" (curly quotes, en/em dashes, ellipses) — but `_names()`'s new fallback branch
builds `entity_f` and tests `low` without ever routing the *separator* through it; only whole-name
comparisons elsewhere in this file (`_queue_row`, the verbatim check) use `_norm_q`.

Verified live by extracting the exact logic standalone (no read.py import, no side effects):

```
entity = 'MSM-07N Ram Z’Gok'   # catalogued with a CURLY apostrophe (U+2019)
same-style curly apostrophe  -> True
ascii straight apostrophe    -> False   # "Z'Gok" with a plain ASCII apostrophe
apostrophe dropped entirely  -> False
```

A sentence that names the entity by its ordinary ASCII spelling — the overwhelmingly common way a
scraped wiki page renders an apostrophe — falls through to `False`, and `read_entity` (read.py
:1000-1002) counts it as `generic_dropped`, exactly the "generic subject" bucket the function
exists to distinguish from a genuine act by the entity. Since `read_entity`'s cache is permanent
once every chunk is answered (:1016-1043), a feat lost this way is lost for that entity for good,
the same "signature failure" shape recorded elsewhere in this file's own comments.

**Scale, measured against the live corpus** (`data/records/*.json`, all 216 files, 282,822
entries, no sampling): catalogued entity names containing a curly quote or en/em-dash number 406,
but only 2 of those also have every `\W+`-split word at length ≤3 (the precondition for reaching
this fallback branch at all): `MSM-07N Ram Z'Gok` (curly apostrophe) and `T'yog` (curly
apostrophe). Both are genuinely small numbers today — but the underlying assumption (wiki
punctuation matches catalogue punctuation exactly) is the same one `_norm_q` was written to
reject everywhere else in this file, and the count of qualifying entities can only grow as more
sources are catalogued. It is a real gap in an otherwise carefully-measured fix, not a
hypothetical.

Suggested direction (not prescribed): route the separator's `own` character set through the same
fold `_norm_q` applies (translate curly quotes/dashes to their ASCII equivalents before building
the character class), or build the whole fallback comparison over `_norm_q`-folded copies of both
`entity_f` and `low`, matching how `_queue_row` and the verbatim check already treat this class of
mismatch.

### 2. VERIFIED — `src/pipeline.py:3639-3650` (location correction: NOT in prose_gate.py), the
2026-09-25 P8 meta-language widening bans the ordinary English word "stub" outright

The brief asked for fresh eyes on "prose_gate.py's P8 meta ban, widened 2026-09-25 to also refuse
`*wiki*`, `stub(s)` and `this/the article`." That ban is not in `prose_gate.py` — `prose_gate.py`
(all 545 lines, read in full above) contains no P8/meta-language code at all; the five layers it
implements are the supervisor/tool gates, the evidence floor, the block validator, and the
Instrument-section check. The actual P8 meta-language ban lives in `src/pipeline.py:3639-3650`
(`_META_TERMS`, `meta_violations`, `assert_in_universe`), which is **outside this batch's assigned
module list** and was not read in full as part of this pass — only the specific regex block the
brief pointed at was inspected and tested, on the theory that a mislocated pointer in the brief is
still worth chasing down given how explicitly "fresh eyes" was requested for it.

The live regex:

```python
_META_TERMS = re.compile(
    r"\b(?:DMs?|dungeon master|game master|GMs?|player characters?|players?|PCs?|NPCs?"
    r"|tier of play|at your table|the table|adventuring party|session|campaign"
    r"|d20|saving throws?|hit points?|armou?r class|proficiency bonus|initiative"
    r"|challenge rating|CR \d+|stat block|5e|fifth edition|homebrew|sourcebook"
    r"|roll(?:s|ed)? (?:a )?d\d+|advantage on the roll"
    r"|\w*wiki\w*|stubs?|(?:this|the) article)\b", re.I)
```

The commit's own comment shows it was aware of exactly this over-matching risk for one of its
three new terms — "`article` only with this/the, so an article of clothing is still in-world" —
but applied no equivalent scoping to `stubs?`, even though "stub" is at least as common an
ordinary noun (a cigarette stub, a candle stub, a ticket/cheque stub, the stub of a tail or a
tower) as "article" is. Verified live:

```
['stub']         <- 'He crushed the cigarette stub beneath his boot.'
['stub']         <- 'All that remained of the tower was a blackened stub.'
['stubs']        <- 'She kept the ticket stubs in a drawer.'
['wikiup']       <- 'The wikiup stood at the edge of the camp.'   # real word, an unrelated hut
['digimonwiki']  <- 'As catalogued by the DigimonWiki, the creature evolves twice.'  # intended catch
['this article'] <- 'This article describes the ritual in full.'                    # intended catch
[]               <- 'He wore an article of clothing marked with the sigil.'         # correctly spared
```

Any of the first three lines, if it occurred in otherwise-legitimate generated prose (a fantasy
volume mentioning a candle stub or a ticket stub is entirely plausible), would trip
`assert_in_universe` and refuse the whole chapter as meta-language leakage — a false refusal, not
a false pass, so it costs a wasted regeneration rather than letting a real defect through, but it
is the opposite failure from what P8 exists to prevent and the same class of over-matching the
`article` scoping was deliberately added to avoid one line above it. `\w*wiki\w*` has the same
shape (catches the real, unrelated word "wikiup") but is lower-frequency in practice.

Recommend flagging this to whoever owns `pipeline.py` for the same narrowing `article` already
got — e.g. requiring "wiki" as a name-suffix (`\w+Wiki\b` or similar) and "stub" only in a
"is/was a stub" / "stub article" construction — since `pipeline.py` is outside this batch's scope
to fix or file further against.

## Questions (not findings)

- `src/escalation.py:1274` (`clear()`): the `landed = False` assignment after the CAS loop's
  success check is never read afterward — the function always returns the literal `True` (inside
  the `if` above it) or falls through to the literal `False` at the end. This matches the brief's
  note that it is already on record as an owner question; not re-litigated here, and no other
  reachability issue was found near it (the surrounding retry loop, digest checks, and
  `_halt_identity` comparison all behave as documented).
- `src/prose_gate.py`'s `prose_enabled` / `step4_enabled` gates were read but not touched or
  recommended for change, per the brief.

## Everything else

No other VERIFIED or SUSPECTED findings across `read.py`, `escalation.py`, `corpus_db.py`,
`ingest_doc.py`, `prose_gate.py`, `burgs.py`, `grounding.py`, `halo.py`, or `module_index.py`.
Traced in particular and found sound: `escalation.py`'s compare-and-swap halt/stop/resume/clear
write paths and their fail-open lock vs. fail-closed read logic; `corpus_db.py`'s three-state
sentinel handling (`SPINE_LOOKUP_FAILED`/`HOST_LOOKUP_FAILED`/unreadable) and its freshness/
deletion-check banners; `ingest_doc.py`'s resumable chunk cursor and its cursor-vs-record
lag-only-never-lead invariant; `prose_gate.py`'s layer 4/4b/4c section, Instrument, and unearned-
axis checks; `burgs.py`'s rank-size derivation (`_rank_at_or_above` / `class_histogram` verified
by hand to partition ranks correctly and sum to the total burg count with no off-by-one at class
boundaries); `grounding.py`'s uncapped, full-field confidence denominator; `halo.py`'s per-axis
provenance tagging; and `module_index.py`'s duplicate-group and stale-group detection with its
accumulate-then-fail-on-exit-code discipline.

## Coverage recorded

Recorded via `sweep_plan.record('run64', [...], batch=15)` per the brief, for the nine modules
listed above, all read in full.
