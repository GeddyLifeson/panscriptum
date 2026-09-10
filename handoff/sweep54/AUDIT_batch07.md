# SWEEP run54 — batch 07 audit

Batch: `src/cascade_bridge.py`, `src/corpus_db.py`, `src/onomast.py`, `src/anchors.py`,
`src/backfill.py`, `src/recover_folder_records.py`, `src/grounding.py`, `src/profile.py`

Every module read in full, line by line (not skimmed). Where a module makes a checkable
factual or cross-file claim, I verified it against the cited source rather than trusting the
comment — see each finding's Confidence line for what was actually done (grep, direct
execution, or reading the cited file at the cited line).

---

## src/cascade_bridge.py (2,317 lines)

Read in full across four passes. This module is already exceptionally heavily self-audited —
nearly every non-trivial line carries a comment naming a prior defect, the order that fixed it,
and how it was measured. I traced the control flow for `engine()`/`thread_engine()`'s locking,
`_ask_call`'s pin/widen/claim logic, every classifier (`permanent_refusal`, `named_transient`,
`client_rejection`, `local_transport`, `pool_exhausted`, `retry_after_seconds`,
`_size_refusal_permanent`), `dead_forever()`'s memo/TTL logic, `record_unrecognised`'s
compare-and-swap, and `prove()`/`try_disabled()`'s isolation guards. I did not find a new defect
in any of it.

Two verifications worth recording because they were the most promising leads and both came back
clean:

- The docstring's claim that `is_dead()` has a fourth branch at `cascade/engine.py:545` yielding
  "model rejected by the provider", and that "401/403 mean a bad key" sits at `engine.py:225` —
  both checked directly against `C:\Users\imarl\cascade\cascade\engine.py` and both are exactly
  right, present at those exact lines.
- `provider_error()`'s read-only SQLite connection opens `SCRATCH_DB` (a Windows path with
  backslashes) as a `file:...?mode=ro` URI without forward-slash conversion, unlike
  `corpus_db.connect()` which does convert. Tested directly: this sqlite3 build tolerates
  backslashes in the URI path fine (confirmed with a live `sqlite3.connect("file:...\\...db",
  uri=True)` against both a relative and an absolute drive-letter path). Not a bug on this
  machine; flagging as INFO only in case the sqlite build ever changes.

### INFO — untested assumption on SQLite URI backslash tolerance
**Where:** src/cascade_bridge.py:1009 (`provider_error`)
**What:** Opens `"file:%s?mode=ro" % SCRATCH_DB` where `SCRATCH_DB` is an unconverted Windows
path (backslashes), via `sqlite3.connect(..., uri=True)`.
**Why it might matter:** `corpus_db.connect()` explicitly does `path.replace("\\", "/")` before
building the same kind of URI, suggesting the project's own house rule is to convert. This one
site doesn't. It works today (verified below) but is inconsistent with the sibling module's
practice and would break silently (probably `OperationalError: unable to open database file`,
then swallowed by the bare `except Exception` two lines down) if a future Python/sqlite3 build
enforces the stricter URI spec.
**Confidence:** ran a live test — `sqlite3.connect("file:C:\\Users\\imarl\\panscriptum-library-kit\\state\\test_scratch.db?mode=ro", uri=True)` opened and queried correctly on this machine's Python (miniconda 3.x). Not reproducible as a live failure; reported as a fragility, not a bug.

---

## src/corpus_db.py (1,041 lines)

Read in full. Traced `rebuild()`'s whole-file compare-and-swap, the `SPINE_LOOKUP_FAILED` /
`HOST_LOOKUP_FAILED` sentinel handling, `freshness()`'s deletion-arm logic, `drift()`, and the
`CANNED` query dict (checked each query against the Hard-Rule-0 no-truncation history in its own
comments — confirmed none of the nine carries a `LIMIT`).

### MINOR — stale line citations in `age_seconds()`'s own docstring
**Where:** src/corpus_db.py:428-431
**What:** The docstring says: "`grep -rn 'age_seconds()'` over the repo finds this def, a
self-reference inside this docstring's own grep pattern, and two prose mentions in comments --
the rebuild's stale-`built_at` warning (`replace_retry`'s comment, :321) and the no-SQL branch's
ABSENT/UNREADABLE note in `main()` (:742)".
**Why it is wrong:** Neither line number matches its described content any more. Line 321 is
`if evidence_limit: silence.note("corpus_db.py:evidence-limit-ignored")` inside the evidence-scan
block — nothing to do with `replace_retry` or `built_at`. Line 742 is inside `_cell()`'s
docstring ("A MARKER, NOT REMOVAL...") — nothing to do with `main()`'s ABSENT/UNREADABLE branch.
The comment the docstring is actually pointing at ("rebuild printed full counts and exited 0 over
an unchanged database, `age_seconds()` went on reporting the OLD `built_at`") is now at line 395;
the "ABSENT AND UNREADABLE ARE DIFFERENT DATABASES" comment in `main()` is now at line 1000. The
file has grown since this docstring was written and the citations were never re-derived.
**Confidence:** read both cited lines directly (`sed -n '318,324p'` and `'738,746p'`) and
grepped for the actual matching text, which is at lines 395 and 1000 respectively.

### MINOR — stale line citation in `drift()`
**Where:** src/corpus_db.py:635
**What:** A comment reads: "Same shape as `rebuild()`'s list at :190 -- basename plus the
exception class, so the two halves of this CLI report an unreadable record identically."
**Why it is wrong:** Line 190 is inside the "THE RESOLVER, NOT THE RAW TABLE" comment block about
`address.spine_code_for()`, unrelated to basename/exception formatting. The actual matching line
— `unreadable_records.append("%s (%s)" % (os.path.basename(p), type(e).__name__))` — is at line
236.
**Confidence:** read both lines directly and grepped for the matching `.append(` pattern.

### INFO — inaccurate column count in a schema-migration comment
**Where:** src/corpus_db.py:89
**What:** The comment on the `unreachable` column addition says: "a database built before today
keeps the old five columns and the INSERT below would fail on arity".
**Why it is wrong:** Counting the columns actually declared above that comment (`name, host,
spine, entries, cited, read, no_page, not_attempted, no_host`) gives nine, not five. The
underlying point (an old DB predates the new column and the INSERT's 10-value tuple would fail
arity against it) is correct and doesn't depend on the exact number; only the stated count is
wrong.
**Confidence:** read the `CREATE TABLE` statement directly and counted the declared columns.

---

## src/onomast.py (774 lines)

Read in full. Traced `well_formed()`'s seven constraints against the named counter-examples
(verified each rejects for the reason claimed, per the function's own corrected attribution
table), `coin_well_formed_stamped()`'s ordinary/exhausted/digest-tail fallback ladder, and
`name_worlds()`'s append-only carry-forward / retired-vs-standing logic.

### MINOR — a non-dict prior record is dropped from the onomasticon with no trace at all
**Where:** src/onomast.py:668-683 (the `merged` construction inside `name_worlds()`)
**What:**
```python
for cid, rec in prior.items():
    if cid in out:
        continue
    if not (isinstance(rec, dict) and rec.get("catalogue_name")):
        if isinstance(rec, dict):
            silence.note("onomast.py:merge-dropped-unschemad-prior")
        continue
    merged[cid] = {**rec, "retired": cid not in resolved}
```
**Why it is wrong:** The outer `if not (isinstance(rec, dict) and rec.get("catalogue_name")):`
catches two different cases — (a) `rec` is a dict with no truthy `catalogue_name`, and (b) `rec`
is not a dict at all (e.g. `null`, a string, a list — any malformed entry in a hand-edited or
externally-written `ONOMASTICON.json`). The `continue` fires for both, but the `silence.note`
only fires for case (a), because it sits inside `if isinstance(rec, dict):`. Case (b) drops the
record from the append-only onomasticon completely silently — no note, no print, no trace
anywhere. The comment directly above this code describes fixing exactly this failure shape ("used
to vanish from `merged` right here with nothing anywhere saying so ... the drop is now visible
instead of a silent shrink") but the fix only covers the dict-without-catalogue_name case, not
the non-dict case the same sentence's own reasoning applies to equally. This is the identical
defect class (a silently-dropped record in an append-only ledger) the surrounding 100 lines of
comments in this same function were written to eliminate.
**Why it matters is bounded:** the docstring for the sibling case already notes this "is not
reachable by either current writer" — both writers of `ONOMASTICON.json` always emit dicts with a
`catalogue_name` — so it only bites a hand-edited or externally-corrupted file. But that is
exactly the scenario `load_onomasticon()`'s `OnomasticonUnreadable` machinery two functions up
was built to guard against for the *unparseable* case; this is the *parses-but-malformed* case,
and it has no equivalent guard.
**Confidence:** read the code directly and traced the indentation — the `continue` is a sibling
of the `if isinstance(rec, dict):` block, not nested inside it, so it executes unconditionally
for both branches of the outer `if`, while `silence.note` executes only for one of them.

### MINOR — stale cross-file line citations
**Where:** src/onomast.py:754
**What:** A comment says: "Every sibling repaired by that sweep does the opposite
(genre.py:327-331, sevenfold.py:412-415, wh40k.py:290-295)."
**Why it is wrong:** None of the three citations point at the described write-denied/silence.note
pattern any more. The actual matching code (a `write_json` call, a `silence.note("<file>:main-write-denied")`, and a `print("WRITE DENIED ...")`) is at genre.py:371-373, sevenfold.py:423
and 432-433, and wh40k.py:338-341 respectively — all three have moved since this comment was
written.
**Confidence:** grepped all three sibling files for `write_json`/`WRITE DENIED`/`main-write-denied` and read the matching blocks; none appear anywhere near the cited line ranges.

---

## src/anchors.py (577 lines)

Read in full, then **executed** (`python src/anchors.py`) to check its own invariants live
rather than only reading them. Result: exit code 0, all eleven graded invariants HELD, including
the monotone floor-to-ceiling ordering and the college/bit-value checks the file's own history
says were previously ungraded. I also independently recomputed `rigor.measure_bit_value(b)` for
every band in `A.LADDER` and it matches the specific figures the file's comment cites
verbatim (M0 1.66 ... M10 4.65) — a genuinely checkable numeric claim that held up exactly.

No findings. Checked for: check-that-cannot-fail shapes (the file itself names and explains eight
`if pinned:`-style always-true guards elsewhere in the codebase; anchors.py's own equivalent —
the `if pinned:` sequence isn't present here, but I looked for an analogous "graded but
untestable" invariant and found none: every verdict in `verdicts` has a real failure mode I could
trace), silent failure, and stale citations (none found via grep).

---

## src/backfill.py (475 lines)

Read in full. Traced `roster()`'s category-walk pagination and `RosterIncomplete` handling,
`lead()`'s paragraph-selection heuristic, and `backfill_source()`'s size-based ranking
(specifically re-verified the `(t in sizes, -sizes.get(t, 0))` sort key: an unmeasured title has
`t in sizes == False`, and `False < True` in Python, so unmeasured titles sort to the *front* of
the ascending sort — i.e. they are prioritized to survive a `--cap`, exactly as the surrounding
comment claims). Cross-checked that `F.strip_wikitext`, `F.fetch`, `F.api`, `F.is_wikipedia`,
`F.HOSTS`, `P.records`, `P.write_record_catalogue`, and the `scout.py:main()` analogous-lookup
claim all still exist with the described shape.

No findings. Checked for: cap/truncation violations (none — every cap in this file is either
opt-in `--cap` on the QUEUE, not the roster, or explicitly named in the output), silent failure
(the `write_denied` / `not_fetched` / `dropped_as_stub` / `size_lookup_failed` counters are all
threaded through to the final report), and stale citations (none found).

---

## src/recover_folder_records.py (380 lines)

Read in full. Traced the `EXCLUDED_REGISTER_SOURCES` skip, the `shortfalls` accumulation (checked
for double-counting across the try/except and the following `if _want is not None` — confirmed
each register_source can only be appended to `shortfalls` once per mapping entry), the
`already`-populated guard, and the two write gates (per-record `silence.write_json` and the
roll's `roll.update_rows` compare-and-swap), both of which correctly propagate `denied=True`
through to a nonzero exit.

### MINOR — stale line citation, own file
**Where:** src/recover_folder_records.py:122
**What:** A comment says: "The comment at line 168 already says the roll is a SNAPSHOT and the
record folder is the truth."
**Why it is wrong:** Line 168 is inside the earlier `except (TypeError, ValueError):` block
("A MAPPING THAT DECLARES NOTHING USABLE IS NOT A MAPPING THAT AGREES..."), not the "THE ROLL IS
A SNAPSHOT; THE RECORD FOLDER IS THE TRUTH" comment, which is now at line 206.
**Confidence:** read line 168 directly and grepped for "THE ROLL IS A SNAPSHOT", which is at 206.

---

## src/grounding.py (362 lines)

Read in full, then exercised `classify_source()` directly (a source with a clear "created the
world in the beginning" origin sentence classifies `ex_nihilo` at confidence 1.0 with 5 groundings
scored; a source with no entries classifies `ungrounded` at confidence 0.0, also with 5 groundings
scored) to confirm the full-field-denominator fix described in `classify_text`'s docstring is
actually in effect and not merely claimed. Also confirmed the `_ORIGIN` and `GROUNDINGS` cue
regexes all compile and the module's own `_BAD_CHARS` corruption guard passes.

No findings. Checked for: truncation (the docstring's own history of the `top` parameter's
Hard-Rule-0 fix is corroborated by the current code — `classify_text`'s default is `top=None`,
which returns the whole field), the `dist[UNGROUNDED]` `Counter` lookup (confirmed this cannot
KeyError — `collections.Counter` returns 0 for a missing key), and stale citations (none found).

---

## src/profile.py (296 lines)

Read in full, then **ran the whole module end to end** (`python src/profile.py`) against the
live corpus: `worldseed.build_all()` produced 10,433 worlds, and every single one round-tripped
exactly through `encode`/`decode`/re-`encode` (`10,433 of 10,433 round-trip exactly failures: 0`,
exit code 0). This is the strongest evidence available for a codec module and it passed
completely.

### MINOR — stale line citation, own file
**Where:** src/profile.py:263
**What:** A comment inside the round-trip check says: "`d["profile"]` is decode()'s own argument
echoed back (line 125 above) -- comparing it to `r["profile"]` compares that string with itself
and can never fail."
**Why it is wrong:** Line 125 is `def encode(address, genre, register, features, band="unassayed",
attested=0):` — the start of the *encode* function, not the point inside `decode()` where the
`profile` argument is echoed back into the output dict. That line (`"profile": profile,`) is now
at line 174; `def decode(profile):` itself starts at line 157. Both are well after line 125.
**Confidence:** read line 125 directly and grepped for `"profile": profile` and `def decode`,
which are at 174 and 157 respectively. The underlying claim about the check being tautological is
still correct — the round-trip fix that follows it (re-encoding and comparing) is real and does
work, as the live run above confirms — only the line pointer is wrong.

---

## Coverage note

I did not find any check-that-cannot-fail, lost-update, or claimed-success-on-error defects in
this batch beyond the one silent-drop path in `onomast.py`. The dominant finding shape in this
batch is **stale line citations in self-documenting comments** — five separate instances across
four different files (`corpus_db.py` x2, `onomast.py` x1 cross-file, `recover_folder_records.py`
x1, `profile.py` x1), all independently verified against the files they cite. None affect
runtime behaviour; all of them would send a future maintainer chasing the wrong line while
debugging exactly the kind of history-dependent logic this codebase relies on comments to
explain. Given how many of these turned up in one batch of eight files, this may be worth a
dedicated pass (a script that extracts every `<file>.py:<line>` / `:<line>` citation across
`src/` and checks whether the cited line still contains recognizable matching content) rather
than relying on sweep batches to find them one at a time.
