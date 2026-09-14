# AUDIT — sweep run56, batch 07

Modules read in full, top to bottom: `src/cascade_bridge.py` (2317 lines), `src/corpus_db.py`
(1040 lines), `src/onomast.py` (773 lines), `src/anchors.py` (576 lines), `src/backfill.py`
(474 lines), `src/sevenfold.py` (441 lines), `src/catalogue_aurora.py` (324 lines),
`src/tuning.py` (286 lines).

General note before the findings: every one of these eight modules is already extremely
heavily self-audited — nearly every non-obvious line carries a comment citing a prior
`order <hash>`, a numbered `run #NN` sweep, or a named bug (m103, m108, m132, M36, etc.) that
already found and fixed the shape of defect this pass is looking for (fail-open paths, checks
that cannot fail, silent swallowing, undisclosed caps). Most of what would normally read as
suspicious on a first pass is explained, with the history of the actual bug and its fix, in the
surrounding comment. I verified a sample of those historical claims against the current code
(not just trusted the prose) and did not find any where the fix described no longer matches
what the code does. The two findings below are both in the "stale line-number citation" category
explicitly called out in the sweep brief — a category that by nature will not have been caught
by the project's own `silence.note()`-based content-label convention, because these are plain
prose citations to *other* files' line numbers, not `silence.note` keys.

---

## DEFECT — stale cross-file line citations in `onomast.py:754`

**Module:** `src/onomast.py`
**Line:** 754
**Quoted text** (from `main()`, the paragraph explaining why the write below is gated):

```
    # AND THE EXIT CODE HAS TO CARRY THE DENIAL TOO (order dc5c92aad5c1, the run #36
    # discarded-verdict ruling 3e65dbed45a6). This branch printed and then fell through to
    # `return 0`, and called no `silence.note`, so a denied replace reached neither the exit
    # code nor state/failures.json -- its only trace was a line on a console nobody watches
    # during an unattended run. Every sibling repaired by that sweep does the opposite
    # (genre.py:327-331, sevenfold.py:412-415, wh40k.py:290-295). The stake here is that
```

**What is wrong:** all three cross-file citations now point at unrelated code.

- `genre.py:327-331` is currently `print("GENRE — classify the source once...")` and two
  `Counter`/loop lines — the report header, not the gated write. The actual gated-write block
  (`if not silence.write_json(p, out, ...): silence.note("genre.py:main-write-denied"); ...`)
  is at `genre.py:355-374` (the `# GATED:` comment itself starts at line 363).
- `sevenfold.py:412-415` is currently the "sample WORLD shelfmarks" print loop
  (`_wsample = sorted(worlds)` / `for d in _wsample[:8]:`). The actual gated write
  (`if args.write:` / `# GATED:` / `silence.write_json(...)`) is at `sevenfold.py:416-436`.
- `wh40k.py:290-295` is currently inside the `--full` per-entity print loop
  (`if a.full: for n, rec in rank: ...`), nothing to do with a write. The actual gated write
  (`# GATED, and note that the twin cited above had the IDENTICAL defect...` /
  `if not silence.write_json(OUT, out, ...)`) is at `wh40k.py:333-341`.

I verified all six locations (three cited, three actual) directly against the current file
contents before writing this down.

**Why it matters:** this is exactly the class of citation this sweep is asked to catch — a
comment sending the next reader (human or agent) to the wrong ten-to-forty lines of a sibling
file when they go to check "does every write-denial sibling actually gate its exit code the way
this one does." It is low severity (prose only, no behavioural effect — the gating logic in
`onomast.py` itself is correct and unaffected), but it is the exact kind of drift the project's
own `silence.note()` keys were converted to content-labels to avoid (see `catalogue_aurora.py`'s
own comment on this, quoted below) — this particular reference just never got the same
treatment because it is a plain prose cross-file citation, not a `silence.note` call site.

**Confidence: DEFECT.** Verified directly; not a matter of interpretation.

---

## DEFECT — two more stale self-referential line citations in `corpus_db.py`

**Module:** `src/corpus_db.py`

### (a) `age_seconds()` docstring, line 428-429

**Quoted text:**
```
    (sweep33 batch17, sweep34 batch04, sweep36 batch09, sweep37 batch09, sweep38 batch10 ->
    order a25e919309cb). `grep -rn 'age_seconds()'` over the repo finds this def, a self-
    reference inside this docstring's own grep pattern, and two prose mentions in comments --
    the rebuild's stale-`built_at` warning (`replace_retry`'s comment, :321) and the no-SQL
    branch's ABSENT/UNREADABLE note in `main()` (:742) -- and nothing else; ...
```

**What is wrong:**
- `:321` is cited as "the rebuild's stale-`built_at` warning (`replace_retry`'s comment)". Line
  321 today is inside the `evidence_limit`-is-inert comment block (`if evidence_limit:
  silence.note("corpus_db.py:evidence-limit-ignored")`), unrelated to `replace_retry` or
  `built_at`. The actual comment being cited — "`replace_retry` returns False rather than
  raising when a reader holds `corpus.db` open ... `age_seconds()` went on reporting the OLD
  `built_at`" — is at `corpus_db.py:392-398`.
- `:742` is cited as "the no-SQL branch's ABSENT/UNREADABLE note in `main()`". Line 742 today is
  inside `_cell()`'s docstring ("A MARKER, NOT REMOVAL..."), a display-truncation helper with no
  relation to `main()`'s no-SQL branch. The actual comment — "ABSENT AND UNREADABLE ARE
  DIFFERENT DATABASES. `age_seconds()` answers None for three unrelated reasons..." — is at
  `corpus_db.py:1000-1004`.

### (b) `drift()`, line 635

**Quoted text:**
```
        except Exception as e:
            silence.note("corpus_db.py:drift-record")
            # Same shape as `rebuild()`'s list at :190 -- basename plus the exception class, so
            # the two halves of this CLI report an unreadable record identically.
            unreadable.append("%s (%s)" % (os.path.basename(p), type(e).__name__))
```

**What is wrong:** `:190` is cited as `rebuild()`'s list of `"%s (%s)" % (basename, exception
class name)` entries. Line 190 today is inside the spine-resolver docstring block ("THE
RESOLVER, NOT THE RAW TABLE..."), unrelated. The actual matching line —
`unreadable_records.append("%s (%s)" % (os.path.basename(p), type(e).__name__))` — is at
`corpus_db.py:236`.

**Why it matters:** same category as the `onomast.py` finding above — these are exactly the
kind of citation a reader (or another sweep agent) would follow to cross-check that the two
halves of this module ("rebuild" and "drift") report an unreadable file identically, and both
citations now land on unrelated prose. All three of `corpus_db.py`'s numeric citations I found
in this module are stale (the module has grown/shifted since these docstrings were written);
none of its `silence.note()` calls carry a numeric line reference (they are all already
content-labels per the project's own convention), so the exposure is confined to these two
prose docstrings.

**Confidence: DEFECT.** Verified directly against current line contents.

---

## Checked and found clean

- **`catalogue_aurora.py:151`** cites `catalogue_aurora.py:74` — but read the surrounding
  comment: it is explicitly describing a *prior* state ("This said `catalogue_aurora.py:74`...
  already stale before this pass, and staler after it") as the reason the label was converted
  from a line number to a content label (`silence.note("catalogue_aurora.py:folder-xml-unparseable")`,
  the actual line 157 today). This is a correctly-historical citation, not a live stale one —
  checked and is fine.
- **`cascade_bridge.py:2291-2292`** ("This block sat at :1564 with `prove()` (:1587) and
  `try_disabled()` (:1701) defined BELOW it") is past-tense, describing where the `__main__`
  block and the two functions used to sit before a fix relocated the block to the foot of the
  file (order `fa3900441022`). Not a live citation — nothing to verify it against. Fine.
- **`cascade_bridge.py:416, 427, 779`** cite `engine.py:545`, `engine.py:225`, `engine.py:277`
  and `:343` — all in the *separate* `cascade` project at `C:\Users\imarl\cascade\cascade\engine.py`
  (outside this repo, referenced via `CASCADE_HOME`). I located that file and checked all four
  line numbers directly: all four match the quoted wording exactly (`"model rejected by the
  provider"` at 545, the 401/403 bad-key comment at 225, the two `"empty response"`/`"produced
  no answer text"` failover sites at 277 and 343). Not stale.

**No caps, truncations, or undisclosed slicing found** beyond the ones already flagged and
explained in-line as deliberate and disclosed (e.g. `sevenfold.py`'s `sample`/`_sample[:8]`
blocks, which print an explicit "(first 8 of N)" header and are display-only with the full data
written to `SEVENFOLD.json`; `onomast.py`'s `_endonyms[:4]` with an "and N more" trailer;
`backfill.py`'s `--cap`, which is opt-in, off by default, and does not shrink the roster it
recomputes each run). None of these are undisclosed per Hard Rule 0's own test.

**No fail-open paths found.** Every unreadable-file / unparseable-config path I traced in these
eight modules (`onomast.load_onomasticon`, `corpus_db.rebuild`'s hosts/coverage/spine-resolver
reads, `catalogue_aurora`'s per-file XML parse, `backfill.roster`'s category-walk, `tuning`'s
`_ollama_host`/`_answering_buckets`/`cloud_success_rate`) refuses or degrades to "no evidence"
rather than silently asserting success, and all are already the *product* of a previously-fixed
fail-open bug (each carries its own "order" comment describing the prior defect and the fix).

**No new "check that cannot fail" found.** `anchors.py`'s `run()` grades five real invariants
(ladder-covers-every-anchor, decimal-produced, monotone ordering, five per-anchor CLAIMS, and
four college/bit-value properties) and explicitly documents, by name, the three things it
*deliberately* does not grade because they are tautological by construction
(`prior_divergence_share + attestation_floor_share == 1`, `covers_every_reading`, bit-value
monotonicity) — I checked that none of the five graded checks is itself vacuous (each can and
historically did fail; see the `2026-08-25` and `2026-09-08` rulings cited in the file).
`sevenfold.py`'s "children per parent ... OK" table is explicitly labelled in-line as "a
GUARANTEE being published, not a check being run" and is not gated on for exit code, so it does
not masquerade as a check.

**No SQL injection / unparameterised writes found in `corpus_db.py`.** All `INSERT`/`INSERT OR
REPLACE` statements use `?` placeholders with tuple args; column counts match `SCHEMA` exactly
(source: 10, entry: 9, evidence: 7). The one place raw SQL text is executed unparameterised is
`query(sql, args=())` on the `--sql`/`--canned` CLI path, which is a deliberately-provided
ad-hoc query tool for an operator who already knows SQL, and it opens the database
`mode=ro` (`connect(readonly=True)`) — a malicious or malformed string cannot write regardless
of what it contains. No read path was found that could write.

**No lost-update/race-on-shared-state issues found.** `cascade_bridge.record_unrecognised`,
`corpus_db.rebuild`'s temp-file naming (pid+thread), `sevenfold.py`'s and
`catalogue_aurora.py`'s writes all go through `silence.write_json` / `silence.replace_retry` /
`silence.replace_if_unchanged` and gate their exit codes on the landed verdict, matching house
doctrine, and each was already the site of a previously-fixed race (documented in-line).

**No dead code / unreachable branches found** beyond what is already flagged and justified
in-line as intentional (e.g. `anchors.py`'s eight `if pinned:` guards below the "INVARIANT,
STATED ONCE" comment, explicitly documented as belt-and-braces rather than reachable branches;
`cascade_bridge.py`'s `_bad_chars` self-check at the top of several files).

**Modules with no findings at all (clean read, nothing to add):** `tuning.py`.

---

## Confidence summary

- 2 DEFECTs (stale line citations), both low-severity/comment-only, both verified directly
  against current file contents on both ends (the citing comment and the cited target).
- 0 QUESTIONs raised to a level worth recording — everything else that looked odd on first read
  was already explained by an in-line comment whose claim I checked and found still true.
