# sweep63 batch15 — audit

Scope: every module below read in full, start to finish, in chunks. No sampling.

  - src/read.py              1691 lines — read in full (2 chunks)
  - src/escalation.py        1445 lines — read in full (2 chunks) [SAFETY-CRITICAL]
  - src/corpus_db.py         1053 lines — read in full (1 chunk)
  - src/ingest_doc.py         702 lines — read in full (1 chunk)
  - src/prose_gate.py         545 lines — read in full (1 chunk) [SAFETY-CRITICAL]
  - src/burgs.py              442 lines — read in full (1 chunk)
  - src/grounding.py          361 lines — read in full (1 chunk)
  - src/propagation.py        254 lines — read in full (1 chunk)
  - src/catalog.py            167 lines — read in full (1 chunk)

Total: 6,660 lines across 9 modules, all read.

## Prior-audit cross-check

Grepped `handoff/sweep61/` for these module names before reading, per instructions, so previously
resolved items are not re-filed:

- `sweep61/AUDIT_batch15.md` covered the same module SET MINUS ingest_doc.py/grounding.py/
  propagation.py/catalog.py (it had gpu_lane.py/catalogue_models.py/tempus.py instead). It filed
  one VERIFIED finding in `prose_gate.py:unearned_instrument` (a name-decoration stripping gap:
  `**Bold**` handled, `### Heading` / `_italic_` / `> blockquote` not). CHECKED: this is now fixed.
  `unearned_instrument` (prose_gate.py:539) now strips the full `[\s*_#>-]+` decoration set on
  both ends of the head line, matching every other label regex in the file, and the fix carries
  its own comment citing "sweep61 batch15". No re-file.
- `sweep61/AUDIT_batch04.md` read `propagation.py` and `catalog.py` in full and found 0 defects,
  confirming `propagation.ascension_years(1) == 0.0` and the observed_mark edge cases by direct
  execution. Re-read this run: unchanged, still correct.
- `sweep61/AUDIT_batch10.md` read `ingest_doc.py` in full; its one finding (SUSPECTED, about
  `publish.py`'s gh.exe PATH resolution) is in a module outside this batch and not re-checked here.
  Its QUESTION was about `generate.py:_covered()`, also outside this batch.
  Nothing in that report concerns `ingest_doc.py`'s own code.
- `sweep61/AUDIT_batch13.md` read `grounding.py` in full as part of an 8-module batch; its one
  VERIFIED finding was in `scout.py` (`--limit 0` treated as no-limit), not in `grounding.py`.
  Nothing filed against `grounding.py` itself.

`escalation.py`, `read.py`, `corpus_db.py`, `burgs.py` had no batch-specific prior findings
against them beyond the prose_gate cross-reference above (escalation.py and read.py were the
other two modules in sweep61 batch15's own set, and that report's "everything else" line
covers them with 0 findings).

## Method

All nine modules carry the same dense, numbered "order" comment style recording past defects and
their fixes, many spanning sweeps 22–61 and multiple owner rulings (2026-08-22 through
2026-09-09). The great majority of the priority list in this brief — tautological checks,
fail-open guards, caps/truncations, regex-escape corruption — is already found, fixed, and
commented in these files with a repro and a measurement. This pass hunted for what those comments
have not yet caught. One `python -c` script was run against pure, standalone logic extracted from
`read.py` (no import of the module itself, no mutation, no drill, no network, no GPU — same
discipline as sweep61 batch04's verification snippets) to confirm the one finding below by direct
execution rather than by reading alone.

## Findings

### 1. VERIFIED — `src/read.py:259-264`, `_names()`'s short-word fallback breaks on any entity
whose own name contains internal punctuation

```python
    if not parts:
        whole = [w for w in re.split(r'\W+', entity_f) if w]
        if whole:
            pattern = r'\b' + r'\s+'.join(re.escape(w) for w in whole) + r"(?:'s|s)?\b"
            if re.search(pattern, low, re.IGNORECASE):
                return True
```

This is the fallback for entities none of whose name-words exceed 3 letters (the module's own
comment at :228-237 names "Ash, Vi, Ike, Uub, 'The Six', 'Mr. Fox'" as the motivating examples).
`whole` is built by splitting the entity name on `\W+` — which throws away whatever punctuation
originally separated the words — and then the regex re-joins the surviving words with `\s+`,
i.e. it asserts the original separator was pure whitespace. For an entity like `Mr. Fox`, `Dr. J`,
`T.V.`, or `KS-2` — where the real separator is a period or hyphen, not a space — this assumption
is false, and the pattern can never match a sentence that quotes the entity's own name verbatim
in its own punctuated form, because `\s+` requires the very next character after "Mr" to be
whitespace and the real text has "." there instead.

Verified live by extracting the exact `_fold_diacritics`/`_names` logic and running it standalone
(no read.py import, no side effects):

```
_names("Mr. Fox digs an escape tunnel through solid rock in seconds.", "Mr. Fox")  -> False
_names("Mr Fox digs an escape tunnel through solid rock in seconds.", "Mr. Fox")   -> True
```

The only thing that differs between the two calls is whether the sentence spells the name with or
without the period the entity's own catalogued name carries — and the corpus spells it WITH the
period, because that is literally the entity's name. A sentence that plainly, verbatim names the
entity and contains no personal pronoun anywhere therefore falls through every branch of `_names`
to `False`, and `read_entity` (read.py:978-980) counts it as `generic_dropped` — the exact
"describes a definition/rulebook entry, not an act by this entity" bucket the function exists to
apply, applied here to a feat that genuinely is about the entity.

Scale: a corpus scan (read-only, no pipeline/drill run) for catalogued entity names where every
`\W+`-split word is 3 characters or fewer AND the name contains internal punctuation returns
**1,782 matching entries** across `data/records/*.json` — `Mr. Fox`, `Mr. Pig`, `Ms. Pig`, `Dr. J`,
`Mr. B`, `Mr. F`, `T.V.`, `M.A.R.G.L.E.S.`, `KS-2`, `Me-Mow`, `Kee-Oth`, `Key-per`, `Ele-fly`,
`Ng'Zot Aa`, and others. Not every one of these necessarily has affected sentences in its cached
evidence (a name split into a single `\W+`-token, like `KS-2` -> `KS`,`2`, hits the identical
`\s+`-join defect), but the class is real and not small.

**Why this is worse than an ordinary false negative in this file**: `read_entity` writes the
entity's record to its PERMANENT cache (`cachekey.write_path` / `silence.write_json`, read.py
:1005-1021) once every chunk has been answered, and on every later call `cachekey.load` returns
that cached document unchanged (read.py:840-842) without ever re-running `_names`. So a feat
dropped as `generic_dropped` by this bug is not merely mis-scored on one pass — once the entity's
record lands, the loss is permanent for that entity until someone deletes the cache file by hand,
which is exactly the "this project's signature failure" shape the file's own header and half its
comments are about, arriving through a case those comments did not test.

Suggested fix: derive `whole`'s join pattern from the entity's actual internal separators rather
than assuming whitespace — e.g. splitting on `\s+` only (leaving punctuation attached to the
adjacent word token) and joining with a pattern that accepts the SAME class of separator the
split removed (`[\W]*` or similar) between word-parts, or building the fallback pattern from
`re.escape(entity_f)` with only whitespace runs relaxed to `\s+`, rather than discarding all
non-word separators uniformly.

## Everything else

No other VERIFIED or SUSPECTED findings across `escalation.py`, `corpus_db.py`, `ingest_doc.py`,
`prose_gate.py`, `burgs.py`, `grounding.py`, `propagation.py`, or `catalog.py`, and no other new
finding in `read.py` beyond the one above. All eight of those files are, on this read, internally
consistent with their own extensive in-line defect history; the checks, guards, CAS loops, and
fail-closed paths described in their comments match what the code actually does.

## Questions (not findings)

- `read.py`'s own comment at :228-237 cites `Mr. Fox` by name as a case this exact code path was
  built to handle ("4,939 catalogued entities ... have no single word longer than three letters,
  so `parts` is empty and every sentence naming them outright, with no pronoun, fell through to
  `False`"). The fix that landed (order e61e1c8e9ac4) closed the "no candidate pattern at all"
  case but was apparently never measured against an entity from its own named example list whose
  separator isn't whitespace. Worth flagging to whoever owns this file: the measurement in that
  order's comment (976 pairs on the fallback, 0 regressions) evidently did not include a
  punctuated-name sentence in its cross-check sample, or it would have caught this.

## Coverage recorded

Recording via `sweep_plan.record('run63', [...], batch=15)` per the brief, for the nine modules
listed above, all read in full.
