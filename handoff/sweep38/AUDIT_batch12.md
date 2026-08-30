# SWEEP 38 — AUDIT, BATCH 12

Agent: `sweep38-batch12`. Modules assigned: 8, 4,447 lines. **All 8 read in full.**
Repo read-only; nothing under `src/` was edited.

Orders filed: 12 (11 findings + 1 question). Every `file_order` return value was checked; all
twelve returned an order id.

| code | severity | handler | id |
|---|---|---|---|
| READ_LOCAL_PATH_CITATION_DRIFT | MINOR | LOCAL | ce9735ec93ba |
| READ_CHUNKS_SKIPPED_UNDERCOUNT | MINOR | RUN | 7265801f9528 |
| READ_ONE_FEATS_PRINT_CAP | MINOR | LOCAL | a84c002fb0e3 |
| HEALTH_SUMMARY_STANDARDS_CITATION_DRIFT | MINOR | LOCAL | f467390925c5 |
| HEALTH_REOPEN_BATCH_LIST_CAP | MINOR | LOCAL | b749bcf87350 |
| MANIFEST_UNASSIGNED_REPORT_NAMES_NONE | MINOR | LOCAL | 90cefdab8da8 |
| WEAVE_SPREAD_TABLE_HIDES_BULK | MINOR | LOCAL | 987bf4088026 |
| WEAVE_RECORDS_SIG_PARTIAL_FILE_LIST | MINOR | RUN | f70e87058f66 |
| SNAPSHOT_SID_COLLISION_AND_MANIFEST_WRITE | MINOR | RUN | da72c19bef09 |
| AUDIT_SYNTHESIS_RATE_WRONG_DENOMINATOR | MINOR | LOCAL | 220a0e95b471 |
| AUDIT_SAMPLE_TRUNCATES_WHAT_IT_PRINTS | MINOR | LOCAL | 01eff1b24759 |
| TELLS_RULE_OF_THREE_PATTERN_SCOPE (question) | INFO | OWNER | 382d3a1c387c |

Three findings carry a reproduction, run in the batch scratch directory
(`.../scratchpad/sweep38/batch12/repro.py`): the `chunks_skipped` arithmetic, the weave spread
table, and the audit rate denominator. Output is quoted inline below.

---

## read.py — 1,358 lines, read in full

The transport ladder, the gate, the per-chunk cache and the queue all hold up on re-reading.
Specifically checked and found sound:

* `cap_chunks` is genuinely inert (`silence.note("read.py:cap-chunks-ignored")` and nothing
  else touches `chunks`), and the banner at :1294 says so rather than reporting a cap that is
  not applied. The `--chunks` help text agrees.
* `priority()` builds three buckets and returns `woven + no_page + thin` — the thin bucket that
  used to be no bucket is present and populated; nothing is dropped.
* `_chunk_key` carries host + entity + chunk text; `_chunk_put` stages to a pid+thread temp.
* `read_entity` returns before caching when `unanswered`, and checks `silence.write_json`'s
  verdict on the entity write.
* `queue()` refuses outright (SystemExit) on an unreadable or empty host map after four retries.
* `_FELL_BACK` increments sit beside the two `return got` paths that actually received an answer
  from the card, and are taken under `_FELL_BACK_LOCK`.
* `cache_path()`'s docstring claim "It has no callers left" — **verified**, grep over `src/`
  finds only the definition (and an unrelated same-named helper in `sweep.py`).
* `run(limit=...)` truncating `todo` is NOT filed. Unlike `cap_chunks` it does not write a
  permanently-incomplete record: every entity it does reach is read whole, and the entities it
  skips are simply not visited this pass. It is a "do fewer" flag, not a smaller universe.

### FINDING — `chunks_skipped` is computed with the wrong denominator (order 7265801f9528, RUN)

`read.py:771`

    skipped = sum(len(b) for b in text.values()) // size - len(chunks)

The chunk loop above it is per PAGE, so the real number of chunks generated is
`sum(ceil(len(body)/size))`, not `floor(sum(len(body))/size)`. The two disagree whenever a page
is not an exact multiple of `size`, and the error grows with the page COUNT. The `max(0, ...)`
at :840 clamps away the negative results, so the error is always in the flattering direction:
the reader reports discarding less of the page than it did. Reproduced:

    pages [9000, 9000, 9000], all filtered out -> true skipped 3, reported 2
    pages [500, 500, 500, 500], all filtered out -> true skipped 4, reported 0
    page  [25000],             all filtered out -> true skipped 3, reported 2

Not lost evidence — the filtering itself is correct — but `chunks_skipped` is stored in every
entity record and summed into the progress line, and it is the number an operator reads to judge
whether the action/mention filters are too aggressive.

### FINDING — drifted line citation in `_local_carded` (order ce9735ec93ba, LOCAL)

`read.py:568` cites "the ordinary chunk path (:521-524 above)". Lines 521-524 are `def _local`
and the opening of its docstring. The path meant is `read.py:554-564`, inside `_local_carded`.

### FINDING — `--one` prints `out["feats"][:12]` with no marker (order a84c002fb0e3, LOCAL)

`read.py:1343`. The total is disclosed on the preceding line, so this is not a hidden universe;
it is still a bare slice on the one interactive inspection path, and `audit.py:158-159` in this
same tree shows the house pattern (`... and N more`).

### Checked, not filed

* `size = CLOUD_CHUNK if _CASCADE_OK else CHUNK` when `_CASCADE_OK` is still `None` (the `--one`
  path never calls `ensure_transport`). Harmless: `CLOUD_CHUNK == CHUNK`.
* `for quick in range(2)` — loop variable unused. Cosmetic; `pyflakes` does not flag it.
* The comment block at :1230-1234 about `cap_chunks` printability sits ~60 lines above the
  `chunks_note` it describes. Awkward placement, not misleading.

---

## health.py — 907 lines, read in full

The compare-and-swap flush machinery is correct as written: the digest is taken before the read
in both `_flush_ledger` and `_flush_samples`, both re-take it after preserving a wreck, both
re-merge rather than settle on a refusal, and `_flush_samples` settles by object identity so
samples recorded during the write are not discarded. The `flush()` re-entrancy guard is checked
before the lock is acquired, which is what makes the `note -> flush -> replace_retry -> note`
cycle terminate. `preflight`'s stamp checks `write_json`'s verdict and says so on stderr when it
is denied. `check_caches` walks every file (no `files[:200]`) and its two exemption paths both
route through `cachekey.host_dir` and `roll.OUT_OF_SCOPE` rather than re-spelling them.

### FINDING — drifted citation to standards.py (order f467390925c5, LOCAL)

`health.py:397` cites "dashboard.py:331-339, standards.py:797-800" as the two external readers
of `failures.json` that wrap their read. The dashboard citation is right (guarded read at
`dashboard.py:332-341`, **verified**). `standards.py:790-805` is the reader's-gate standard and
reads no ledger; the actual guarded read is `standards.py:1000-1004` (**verified** by grep),
about 200 lines below the citation.

### FINDING — `reopen_stranded` prints `reopen[:20]` with no marker (order b749bcf87350, LOCAL)

`health.py:777`. The dry run's listing is the review step before `--reopen --go`, and given this
function's own history (149 entries had their `excluded` reason reverted by an over-broad
reopen), showing the first twenty of an unordered list is the weakest possible version of that
review.

### Checked, not filed

* `check_caches` and `check_state` print unconditionally, ignoring `preflight(verbose=...)`.
  No caller passes `verbose=False` today (grepped: `health.py:901` is the only call, and
  `overnight.py` has its own separate `preflight`). Latent, cosmetic.
* `str(a)[:200]` / `str(b)[:300]` on the stamp rows and the various `str(e)[:60]` are exception-
  message truncations, not data caps. Filing them would be noise.
* `_flush_samples`'s trailing `except Exception: pass` is deliberate and documented ("the
  evidence bag must never break the ledger write").

---

## manifest_builder.py — 573 lines, read in full

The volume-numbering fix holds: `numbering_pool` is built before `--only`/`--pilot` narrows
`build_pool`, and `build_pool ⊆ numbering_pool` in every flag combination, so `volume_code[...]`
cannot KeyError. `load_record`'s two inexact arms are both floored at `MIN_INEXACT_LETTERS` with
equality exempt, and the reverse arm is prefix-anchored as its comment claims. `pack_feats`
paginates an oversized entity rather than dropping the tail, flushes before exceeding, and emits
a single over-budget deed on its own block rather than clipping it. The manifest write's verdict
is checked and the failure message names what is actually on disk; `main()` returns 1 when it did
not land. `--pilot N` is a documented operator flag (CLAUDE.md hard rule 6) and not filed.

### FINDING — the unassigned report names nobody under `--include-unassigned` (order 90cefdab8da8, LOCAL)

`manifest_builder.py:544-551`. With the flag set and unassigned sources present, the report is
rewritten to "Generated with `--include-unassigned`: provisional codes were used, so nothing was
skipped. **These still need real assignments.**" — and then lists none of them. The per-source
bullet list exists only in the no-flag branch at :561-562. So the one run after which somebody
must go and assign real spine codes is the run whose report has no antecedent for "these".
CLAUDE.md Hard Rule 2 points the operator at this file by name. The block's own comment two lines
above is about not leaving a stale confident answer in it.

### Checked, not filed

* `print("   %-44s %s" % ((_n or "?")[:43], _why[:90]))` at :424 truncates excluded-source names
  to 43 characters in a console column. Cosmetic; the same names are in `roll.py`.
* Duplicate source names in the roll would double-assign a volume number. No duplicates exist and
  the roll is owner-curated.

---

## weave_index.py — 472 lines, read in full

`norm()`'s conditional return parses as `(s + "@" + keep) if keep else s`, which is what is
intended. `designations()` does not cache the failure path and does not cache caller-supplied
records. `build()` counts what it excludes by reason rather than dropping silently, keeps the
`len<3` rule out of the stored index, and stores the description uncapped. The `--write` path
checks both verdicts, calls out the half-landed case on stderr, and `__main__` propagates the
exit code. `build()`'s docstring claim that `main()` is its only caller anywhere in the tree —
**verified**, grep for `WI.build` / `weave_index.build` across `src/` returns nothing.

### FINDING — the spread table hides the bulk of the distribution (order 987bf4088026, LOCAL)

`weave_index.py:417`, `for n in sorted(spread, reverse=True)[:10]`. `spread` maps
source-count -> entity-count, so sorting the KEYS descending and slicing ten keeps the rare
wide-attestation tail and drops the head. Reproduced with buckets present for 2..24:

    buckets printed       : 24 23 22 21 20 19 18 17 16 15
    buckets never printed : 2 3 4 5 6 7 8 9 10 11 12 13 14

The 2-source bucket — which by construction holds most cross-source candidates — is never shown.
The heading is "attested in N sources:", with no "top" in the label and no "and N more" line, so
it reads as the distribution. (The `[:18]` leaderboard below it is *not* filed: it is honestly
labelled "most cross-attested entities" and marks its inner `srcs[:5]` slice with ' …'.)

### FINDING — `_records_sig` returns a partial file list on a stat failure (order f70e87058f66, RUN)

`weave_index.py:231-242`. The `except OSError` inside the scandir loop returns immediately with
whatever `files` had accumulated, abandoning the rest of the directory. Refusing the SIGNATURE is
correct and is enough for the cache (`load_records` guards on `sig is not None`), but the file
list is the other half of the return value and is consumed unconditionally — `load_records()`
parses it as the whole corpus, `build()` indexes only that, and `--write` would land a smaller
`ENTITY_INDEX.json` / `WEAVE_CANDIDATES.json` over the complete ones.

Reachability is honestly low and I have said so in the order: on Windows `os.scandir` carries
stat data from the enumeration so `de.stat()` normally does not syscall, and the sanctioned
record writer stages under `.tmp` (already filtered) before an atomic `os.replace`. This is a
latent wrong shape in the function every hot caller depends on, not an observed incident.

---

## feats_index.py — 369 lines, read in full, nothing found

Checked and sound:

* `host_to_sources` raises rather than caching an empty map, and the raise is what lets
  `manifest_builder`'s WARNING at :355 actually print.
* `_CACHE` is keyed by the path/root argument, not by function, so a non-default argument cannot
  be served another path's answer.
* `load_index` counts unreadable files and key collisions into `index_faults` instead of letting
  them shrink the denominator, and `audit()`'s `files_seen` is `len(idx) + unreadable + collided`
  with the join rate taken against it.
* `main()` prints every unreadable file and every collided key with no cap.
* The docstring's cross-reference "manifest_builder.py:342-358" — **verified** accurate (the
  "AND A FAILED LOOKUP SAYS SO, OUT LOUD" comment starts at :342 and the guarded call ends at
  :358). This is the only citation in my batch that has not drifted.
* `_norm`'s docstring was corrected in an earlier pass to stop claiming it strips parentheticals,
  and the code agrees with the corrected text.
* `feats_for_source` is uncapped and ranked, as the module header promises.

Considered and rejected as a finding: `load_index`/`host_to_sources` cache for the life of the
process with no signature invalidation (the shape that bit `designations()` in weave_index).
Traced the importers — `manifest_builder` (one-shot), `entity_match` (uses `_norm` only),
`verify_math`. No long-lived daemon calls `load_index`, so there is no live staleness exposure to
file against.

---

## snapshot.py — 300 lines, read in full

`_rel` refuses out-of-tree paths rather than re-rooting them, and handles the Windows cross-drive
`ValueError` separately. `_safe_join` closes the write half on both `restore` targets.
`_dir_matches` walks the snapshot side with `filecmp.cmp(shallow=False)`, so a directory snapshot
is actually compared rather than merely existence-checked. `before()` refuses a partial capture as
well as an empty one, writes `requested`/`skipped` into the manifest before raising, and leaves
the evidence on disk.

### FINDING — snapshot ids collide, and the manifest is the one unhardened write (order da72c19bef09, RUN)

Two related weaknesses, filed as one order because the remedy is in the same three lines.

1. `snapshot.py:109` builds the id from label + `int(time.time())` and `:113` does
   `os.makedirs(dest, exist_ok=True)`. Two `before()` calls with the same label inside one second
   share a directory; the second `_manifest.json` replaces the first's, and the manifest is the
   sole input to both `restore()` and `verify()` — so the first snapshot's files become present
   but invisible, while both callers were handed an id.
2. `snapshot.py:133-134` writes the manifest with a plain truncating `open(..., "w")`, not
   `silence.write_json`. Every other state writer in `src/` was migrated off that formula (see
   `health.py`'s own "A bare `open("w")` truncates BEFORE serialising"). An interrupted manifest
   write leaves a snapshot whose files are all present and whose index is 0 bytes: `manifest()`
   raises, `verify()` returns `(False, "manifest unreadable")`, `restore()` raises. That is the
   copy-before-an-irreversible-act failing in exactly the way this module exists to prevent.

Note for whoever works this: `silence.write_json` returns False rather than raising, so the
existing `except Exception -> raise SnapshotFailed` wrapper will not catch a denied write — the
verdict has to be checked explicitly, same shape as `health.py:846-876`.

---

## tells.py — 280 lines, read in full

The control-character self-check runs twice (source scan at :38, compiled-pattern scan at
:157-159) and the second is built from `chr()` codes so it cannot be disarmed by the corruption
it detects. `_anchor`'s `pat[4:]` correctly strips the four literal characters of `r"^\s*"`.
`prompt_in_sync` returns three-valued `True/False/None` and `__main__` exits non-zero on both
`False` and `None`, so an unreadable prompt file is not read as agreement. The `not merely /
not simply / not just` asymmetry at :70-79 is deliberate and defended, and I confirmed the
uneven completion is what keeps "not just yet" from firing.

No findings.

### QUESTION — "rule of three" tests less than its label claims (order 382d3a1c387c, OWNER, INFO)

`tells.py:97` matches only a three-item list closed by `alike`/`all`/`together`. The module
docstring names "rule-of-three lists" unqualified, and `prompt_section` hands the model the bare
label "rule of three", so the instruction and the checker describe different scopes in the one
file whose premise is that they cannot. Reading A: deliberate, because an unqualified pattern
would fire on ordinary English constantly, and all that is missing is a comment of the kind
:70-79 already carries. Reading B: a real gap, invisible to `prompt_in_sync` because that
compares text and cannot see a label whose pattern under-covers it. It is a house-voice and
false-positive-tolerance call, and it is not urgent — the prose gate is not open.

---

## audit.py — 188 lines, read in full

The invariants pass is the tightest reporting in my batch: `for x in v[:4]` is followed by an
explicit `... and N more`, which is the pattern three other modules here are missing. `fails` is
a `defaultdict` only ever written by `append`, so `if not fails` cannot be fooled by an empty
key, and `main()` returns 1 when anything failed. `_JUNK`'s per-alternative anchoring (`$` for
whole-name furniture, `\b` for prefixes) matches the shape its comment describes.

### FINDING — synthesis-level failures get an entry-level denominator (order 220a0e95b471, LOCAL)

`audit.py:153` divides every class by `stats["entries_catalogued"]`, including the four
`synthesis:` classes at :62-73, which append once per SOURCE. Reproduced against corpus scale:

    synthesis fault on 20 of 215 sources = 9.30% of sources
    audit.py prints it as                  0.01% of catalogued entries

Three orders of magnitude, in the reassuring direction, in the report whose premise is checking
the pipeline "from outside rather than trusting the code that enforces them". A source-level
fault can never read as more than a rounding error here. `stats["sources_with_synthesis"]` is
already counted at :58 and is the denominator those four classes need.

### FINDING — the sample pass truncates the fields it exists to show (order 01eff1b24759, LOCAL)

The module docstring says the sample is "printed in full so a person can read actual rows". Every
field is sliced with no marker: `desc[:150]`, `name[:44]`, `src[:26]`, `category[:34]`,
`scale_note[:110]` and `[:120]`. The last one is the one that costs something — the BANDED SAMPLE
is headed "every one of these makes a claim" and prints exactly one evidence line per row, so a
feat whose measurement sits past character 120 is cut mid-sentence, and the reader is shown less
than `PL.valid_scale_note` and `PL.meta_violations` saw. Ten lines earlier the same file does it
right.

---

## Coverage

All eight modules read in full. `sweep_plan.record('run38', [...], batch=12)` called with all
eight basenames; see the run log below the table at the top of this file for the confirmation.
