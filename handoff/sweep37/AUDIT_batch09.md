# SWEEP 37 — BATCH 09 AUDIT

Modules read IN FULL, every line, 3,968 lines total:

| file | lines |
|---|---|
| `src/read.py` | 1,266 |
| `src/corpus_db.py` | 648 |
| `src/weave.py` | 529 |
| `src/ledger_guard.py` | 427 |
| `src/address.py` | 355 |
| `src/context_budget.py` | 296 |
| `src/thread_integrity.py` | 243 |
| `src/scope.py` | 204 |

No source file was edited. `read.py`, `weave.py` and `corpus_db.py --rebuild` were NOT run;
functions were imported and exercised individually. No network or model call was made — the one
transport test stubs `cascade_bridge` into `sys.modules` before importing `read` and benches the
GPU, and asserts `P.ask` is never reached.

---

## FINDINGS BY SEVERITY

### MAJOR

**F1 — `src/read.py:738-739` (and the `--chunks` flag at `:1238`): a cap that also poisons the
cache permanently.**
`read_entity(..., cap_chunks=N)` does `chunks = chunks[:cap_chunks]` on the density-ranked chunk
list, and the resulting partial read is then written to the entity's permanent cache. The
"deferred, not lost" guard at `:825` is `if unanswered: return out` — and chunks removed by the
cap are never *unanswered*, they are never in `chunks` at all, so `unanswered == 0` and the
record lands. `read_entity` returns that cache on every later call and `queue()` never revisits
the entity, so the entity is filed as finished on a fraction of its own pages.
CLAUDE.md's Hard Rule 0 names this exact parameter in its own list of the four caps the rule was
written about: "`cap_chunks=12` decided on an entity's behalf that the rest of its own pages did
not count." `--help` presents it as an ordinary option ("omit to read every chunk of every page")
with no warning about the cache.
Verified: no caller in `src/` passes `cap_chunks` (`overnight.py:1081` runs `read.py --run
--workers N` only); the only route is a person typing `--chunks`. The precedent for the fix is in
this batch's own sibling: `corpus_db.rebuild`'s `evidence_limit` (order 97b39265457f) was kept for
signature compatibility, made INERT, and given a `silence.note`. Confidence: high.

**F2 — `src/thread_integrity.py:143`: RECIPROCAL is declared on one direction of a two-direction
question.**
`classify()` dedupes to one direction per unordered pair (`:119-121`) and then asks only
`back = (b, a) in recorded`. It never tests whether `(a, b)` is recorded. So a genuinely one-way
thread is classified RECIPROCAL — "both ends know each other -- the omniverse is joined here" —
whenever the recorded direction happens to be the mirror of the one the loop kept, and
ASYMMETRIC-SUSPECT when it is not. The verdict therefore depends on the insertion order of the
`pairs` dict, not on the evidence.
Demonstrated offline (no data files touched):

```
recorded = {('B','A')} only ->      {'RECIPROCAL': 1}
recorded = {('A','B')} only ->      {'ASYMMETRIC-SUSPECT': 1}
recorded = both directions   ->     {'RECIPROCAL': 1}
same recorded, pairs iterated B,A first -> {'ASYMMETRIC-SUSPECT': 1}
```

LATENT: every caller today passes `recorded=None` (Hard Rule 5 — the directed graph does not
exist until the owner's Step 4 pass), so the four asymmetry classes are unreachable and nothing
wrong is being printed. It becomes live the moment Step 4 lands, which is the one moment this
module is supposed to start being right. Confidence: high (executed).

### MINOR

**F3 — `src/weave.py:207`: the mechanics filter searches a 300-character window, and two live
D&D rules entities enter the weave through the gap.**
`_RULES_VOICE.search(desc[:300])` and `_STATBLOCK.search(desc[:400])`. Measured against the live
`data/ENTITY_INDEX.json` (46,103 keys): **54 entities carry rules voice only past character 300**
and survive `filtered_index` for that reason alone. Two of those 54 appear in 2 sources each, so
they are inside `surprisal_pair_weights`' `2 <= len(srcs) <= 60` band and are actively serving as
evidence that two shelves share a continuity:

* `Close Quarters Shooter` — *Dr. Firestorm's Engineering Corps* + *Unearthed Arcana*;
  the give-away is at char ~300: "Finally, you have a +1 bonus to attack rolls on ranged attacks."
* `Psionics` — *KibblesTasty (techno-psionic line)* + *Unearthed Arcana*; "…si Points.
  Additionally you can use your discipline…"

That is the module docstring's own named failure ("tied two D&D supplements together through
'Dexterity' and 'Channel Divinity'") arriving through the search window instead of through the
pattern. The `[:400]` statblock window is dormant *only* because the on-disk index is still
400-capped (open order 944274e8bfd8): 0 descriptions exceed 400 and 7,629 sit exactly at it.
This also corrects the reasoning recorded in closed order b974e9ed76de — "the one traced consumer
(weave.py:204) slices to [:400] and [:300] ITSELF for its own matching, so it is unaffected either
way". It is not unaffected; it is under-filtering now and will under-filter more once the index is
regenerated uncapped. Confidence: high (measured).

**F4 — `src/read.py:1029-1030`: the last inline copy of the entity cache-path formula, bypassing
`cachekey`.**
`queue()` builds `os.path.join(FF.CACHE, re.sub(r"[^A-Za-z0-9]+","_",h)[:40],
re.sub(r"[^A-Za-z0-9]+","_",e["name"])[:80] + ".json")` by hand. `cachekey.py` exists to be the
one spelling of that (its docstring: "ONE HELPER, NOT FOUR SPELLINGS"), and seven other sites were
migrated to it (closed orders for `sweep.py`, `feats_index.py`, `coverage.py`, `hostcheck.py`,
`health.py`, `drill.py`, `verify_math.py`). This one was missed — `read.py:584`'s `cache_path()`
delegates correctly, `queue()` does not. `grep -rn 'A-Za-z0-9]+", "_"' src/*.py` shows it is the
only remaining production copy that names an entity.
Two consequences, measured over all 282,059 catalogued entity/host rows:
* **29 natural-path slots on disk are shared by 2 distinct catalogued names each** (58 entities;
  NTFS folds case, so `Tag Der Toten`/`Tag der Toten` land on one file). In all 29, the file's
  stored `entity` is one of the two, so **29 entities are admitted to (or excluded from) the read
  queue and ranked on a different entity's `chars` / `own` / `axes` / `quantities` numbers**.
  8 of the 29 inherit the neighbour's `skip: True` memo (`:1061`) — the memo is keyed on the
  shared path — and are dropped from the queue on another entity's empty evidence file.
  Examples on disk: `Magic 8-Ball`/`Magic 8 Ball`, `NEMESIS`/`Nemesis`, `Ten-Towns`/`Ten Towns`,
  `What If? Vol 1 10`/`What If...? Vol 1 10`, `Aun'va`/`Aun'Va`.
* Structurally, `queue()` only `os.path.exists()`-tests the NATURAL path, never
  `cachekey.candidate_paths`. `feats.evidence_for` writes through `cachekey.write_path`, which
  sends exactly these 58 entities to the DISAMBIGUATED path. There are 0 such files today, so
  nothing is lost yet — but the first one that lands is an entity with cached source pages that
  the queue whose contract is "everything with cached source pages" cannot see.
Confidence: high (measured). Note the natural-path *string* is byte-identical to `cachekey`'s
today, so this is not a wrong path — it is a missing ownership proof.

**F5 — `src/corpus_db.py:185-191`: a failed spine lookup is written as the resolver's verdict.**
```
code = None
if _spine_for and src:
    try:    code = _spine_for(src)
    except Exception:  silence.note("corpus_db.py:spine-lookup")
    if code == "UNASSIGNED":
        code = None            # NULL means unshelved, and only the resolver may say so
```
On an exception `code` stays `None` and NULL is written anyway — the one thing the comment on the
next line forbids. `address._load_spine_codes()` raises if `data/CHARTER_SPINE_CODES.json` is
missing or unparseable, and `import address` would still have succeeded, so that single failure
makes **all 216 sources** report as unshelved in the derived index; the `unaddressed` canned query
and the Datasette page then present a whole-roll curatorial backlog. This module's own header is a
fifteen-line account of a wrong "36 sources with no spine code, 13,417 entries" figure that was
"nearly acted on as one". The only trace would be a `silence.note`. Confidence: high (read;
the rebuild was deliberately not run this shift).

**F6 — `src/corpus_db.py:276-277`: `meta.evidence_included` is written and never read.**
`rebuild()` records it "for any later reader of the database itself"; `grep` shows the only
consumer is `main()`'s own return dict in the same process (`:584`). A database built with
`--no-evidence` answers the `evidence` and `refused` canned queries with 0 rows, and
`_freshness_banner()` — the line printed above every result precisely so a caveat cannot be
missed — reports only staleness. The caveat travels with the index as intended and nothing ever
asks it. Fix is one lookup in `_freshness_banner()`. (Live DB checked: `evidence_included = '1'`,
257,052 evidence rows, so nothing is wrong right now.) Confidence: high.

**F7 — `src/corpus_db.py:642`: every printed cell is truncated at 40 characters with no marker.**
`" | ".join("" if v is None else str(v)[:40] for v in r)`. Verified against the live index:
`'Who Framed Roger Rabbit (incl. all content from its associated crossover-toon IPs)'` prints as
`'Who Framed Roger Rabbit (incl. all conte'` — the parenthetical that says what the source
actually covers is gone and nothing says so. 14 of 216 source names are cut in the canned outputs;
10,396 of 270,529 distinct entity names are cut on the `--sql` path. `CANNED`'s own comment block
(`:453-467`) removes six `LIMIT`s on the grounds that "a truncated table looks exactly like a
complete one" and then the renderer four functions down truncates every cell silently. House
doctrine (`workorders.py:_change`) accepts display-side truncation as legitimate *because it is
reversible* — so the cheap fix is a marker (`…`), not removal. Confidence: high (measured).

**F8 — `src/ledger_guard.py:411-423`: `main()` prints "ledgers: all intact" having run one of the
module's three mechanisms.**
The CLI calls `check_all()` only. It never calls `verify_chain()` (mechanism 3, the hash chain)
and never calls `check_since_snapshot()` (the append-only enforcement, the one that catches the
truncate-then-regrow this module was rebuilt for on 2026-08-27). A broken chain, or a HANDOFF.md
that has lost 90% of its lines since the last seal, both print `ledgers: all intact` and exit 0.
Verified live today — all three mechanisms currently pass (`check_all() == {}`, `verify_chain()`
True over 487 links, `check_since_snapshot('HANDOFF.md')` → "history preserved") — so no wrong
verdict is being printed, but the sentence the human reads claims more than the code checked.
Confidence: high (executed).

**F9 — `src/read.py:422-423`: the "(N to GPU)" counter counts chunks the benched GPU never
received.**
After the backoff ladder and the `if _TRANSPORT == "cascade": return None` guard,
`_FELL_BACK[0] += 1` fires unconditionally and control falls to `return _local(...)` at `:452`,
which returns `None` immediately when `_GPU_DOWN_UNTIL[0] > time.time()`. The sibling increment at
`:396-401` fires only `if got is not None`, so one counter carries two meanings.
Demonstrated offline with a stubbed `cascade_bridge`, a benched card and an asserting `P.ask`:
`_ask_ungated` returned `None` and `_FELL_BACK` went 0 → 1. The comment at `:414-419` states the
invariant this breaks ("a chunk that is NOT going to the GPU must not be counted as having gone
there") and cites order 6b7f51f8ec2e, which fixed the cascade-mode instance and left this one.
The figure matters because `:213-215` says it "is the only thing that distinguishes a run quietly
served entirely from the slow path from a run that is merely slow". Confidence: high (executed).

### OBSERVED, NOT FILED (no order — recorded so the next run does not re-derive them)

* `ledger_guard.check_since_snapshot(name)` cannot fail for any ledger not in `APPEND_ONLY`:
  `seal()` snapshots only `APPEND_ONLY`, so `_read_snapshot` is always None and the function
  returns the "no sealed snapshot yet" pass forever. Confirmed: `check_since_snapshot('BUGS.md')`
  → `(True, 'no sealed snapshot of BUGS.md yet…')`. No caller does this today; it is a trap for
  the next one, not a live fault.
* `ledger_guard.assert_intact():389` reports `problems[:6]` with no "and N more".
* `ledger_guard.seal():207` reads each ledger TWICE (`_digest(_read(n))` and `len(_read(n))`), so
  a file changing between the two reads records a digest and a byte count of different states.
* `thread_integrity.main()` itemises DANGLING, PARTIALLY-DANGLING, RECIPROCAL and
  ASYMMETRIC-SUSPECT but never ASYMMETRIC-LAWFUL or IMPLIED-UNRECORDED — the same shape as the
  DANGLING gap already fixed there. ASYMMETRIC-LAWFUL is unreachable today (F2's `recorded`);
  IMPLIED-UNRECORDED would be an enormous listing, so its omission is defensible.
* Display truncation of source names in `thread_integrity.main()` (`a[:24]`, `b[:26]`): 50 of 216
  source names are cut; **0 pairs of names collide** at 24 or 26 characters, so nothing is
  ambiguous today. Same for `weave.main()`'s `multi[:12]`, `g[:4]`, `[:8]`, `attestations[:3]`,
  `most_common(6)` — unlike `thread_integrity`, `weave` writes the complete data to its three
  JSON artifacts, so `main()` is not the only surface.
* `scope.py:187` prints `json.dumps(...)[:900]` for `--probe`, which cuts the `pages` list and can
  emit unparseable JSON. Diagnostic surface only.
* `corpus_db.age_seconds()` has no caller anywhere (`drill.py:5366` reads `freshness()`'s dict key
  of the same name). Dead; reported, not deleted, per house doctrine.
* `weave.pair_weights()` and the `idf, N` unpacked-and-unused in `weave.main()` are already
  order 25ec11447b4c — confirmed still dead, not re-filed.
* Two OPEN orders carry drifted line numbers, the idiom being a symbol: **4e92365b54f6** says
  `src/address.py:208` for `build_address`, now at `address.py:241` (still callerless outside its
  own `__main__` — confirmed — but its quoted return value no longer matches the source);
  **de43fe54feb7** says `src/scope.py:123` for `ceiling_for`, now at `scope.py:171` (still
  callerless — confirmed).
* `corpus_db.rebuild()` writes a NULL-named `source` row for a record with no `source` key (SQLite
  permits multiple NULLs in a TEXT PRIMARY KEY), and attributes its entries to a NULL source.
* `address.slugify():186` ends `[:60]`; only reachable for a category label not in
  `CHAPTER_SLUGS`, and `manifest_builder`'s categories are far shorter. Not a live cap.

---

## FOUND HEALTHY (genuinely read and checked, not skimmed)

**`address.py` — Hard Rule 2 holds on today's data.** Every branch was traced against the live
roll: of 216 sources, 181 hit the index exactly, 2 via letter-level equality
(`Soul Calibur`→`Soulcalibur`, `major fantasy pantheons`), 17 via most-specific-wins worded
containment, 16 via the token fallback, **0 UNASSIGNED**. Every containment and token assignment
was inspected by hand and every one is genuine (`Dragon Ball Z`→`Dragon Ball`; the six Tom Clancy
sub-franchises→the Tom Clancy entry; `all Battlefield`→`Battlefield (all)`; `Western astrology`→
the combined astrology entry). UNASSIGNED is still reachable (`Some Brand New Unlisted Thing` →
`UNASSIGNED`), and `Sword Coast Adventurer's Guide` → `II.L.7`, not DC. `Bone (Jeff Smith)` — the
one source `corpus_db`'s header names as genuinely unshelved — has since been added to the index
and resolves to `II.D.4` by exact match. The token branch's evidence rule (`overlap < 2 and
target_tokens != name_tokens → skip`) is correct as written and closes the one-shared-word hazard;
51 of the 220 index entries are a single token and 125 are two or fewer, so that rule is doing
real work. The known remaining hazard is the worded-containment branch, already order
**3b030216a138** — NOT re-filed. `promote()` is promotion-only, `tier_for` is a pure function of
the count, `recipe_hash` includes `content_hash`.

**`ledger_guard.py`.** `_one_insertion` was checked by hand on prefix-only, suffix-only,
middle-insertion, middle-deletion and repeated-character cases: the `s < n - p` bound prevents the
prefix and suffix runs from double-counting, a deletion cannot reach `p + s >= n` while `new` is
longer, and `len(new) < len(old)` short-circuits the rest. The `## Open`/`## Resolved` span logic
is bounded by found order, so a reordered BUGS.md cannot produce the empty-slice pass. The
`is not None` byte comparison in `verify_chain` correctly catches a ledger wiped to 0.
`read_chain()` fails closed on everything but `FileNotFoundError`. `assert_intact()` raises when
`seal()` returns None. `seal()` has exactly one caller (`assert_intact`), so nothing can silently
re-baseline the snapshot after a truncation. The citation `MAINTENANCE.md:143` in
`_one_insertion`'s docstring is **accurate today** — line 143 is
"`/HANDOFF.md` — dated run journal, newest on top". Live state: clean.

**`scope.py` — still the positive example.** The write verdict is carried end to end: `build()`
returns `(out, ok)`, `main()` prints `WRITE DENIED … rerun to retry` instead of a success line.
The below-floor branch returns `None` rather than the argmax it used to invent. A probe exception
`continue`s without writing a key, so a network blip cannot permanently retire a host. `srlimit`
is at the API maximum with a `continue`-key note. Nothing here truncates a title list.

**`context_budget.py`.** The budget is derived from the live window rather than declared;
`window()` falls back to the SMALL 6144; `content_budget_chars` is documented to return ≤0 and
callers are told not to clamp; the prose/content ratios are both set below their measured values,
keeping the pessimism in the safe direction; the system-prompt split is located by heading, not by
line number, and degrades to a no-op if the heading moves. `assert_fits` is genuinely IN EFFECT —
called from `generate.py:160` and exercised both ways by `verify_math.py:2442-2444`. The
unreadable-prompt paths `silence.note` rather than silently widening the budget.

**`read.py`, the two deliberately unguarded cache writes — re-judged fresh this run and the
reasoning still holds.** `_chunk_put` (`:656`) and `_save_qcache` (`:968`) discard their verdicts;
in both cases a miss costs a re-ask or a re-parse and can never be read as a fresh answer, because
`_chunk_get` returns `None` for "not cached" and `read_entity`'s `if got is None` branch counts it
as `unanswered` rather than recording an honest absence, and the qcache memo is keyed on the
evidence file's mtime AND size. The write that DOES matter — the per-entity record at `:839` — is
gated and notes a denial. `queue()` fails closed and LOUD on an empty or unreadable host map
(`SystemExit`, not `hosts = {}`). `priority()`'s third bucket (`thin`) is present, so no row is
dropped for being thin. `_local_carded`'s oversize path returns `None` on any piece failing rather
than `(got or {})`-ing a total failure into an empty answer.

**`corpus_db.py`.** `datasette_metadata()` returns `None` on a denied write and `--serve` refuses
to print a serve command (`:604-615`) — confirmed in source, matching this shift's note.
`connect(path=None)` reads `DB` at call time. The rebuild's temp name carries pid+thread and the
orphan is removed on a denied replace. `replace_retry`'s verdict reaches `main()`, which prints
`REBUILD DID NOT LAND` and returns 1. Unreadable records and evidence files are named in full, not
counted and cut, and the counts are written into `meta`. `evidence_limit` is inert with a note.
The spine column goes through `address.spine_code_for`, not a second lookup.

**`weave.py`.** All three `--write` verdicts are collected per file, a partial round prints
`DENIED`/`landed` per path plus the out-of-step warning, and `main()` returns 1. The
`shared[p].append(k)` cap is gone from both builders. `components()` is complete-linkage with an
early exit, so chaining cannot fuse two continuities. The `2 <= len(srcs) <= 60` band is a filter
on how much evidence a ubiquitous name may contribute, not a truncation of an output listing.
`resonance_graph` is live (`pipeline.py:2235`), not dead.

**`thread_integrity.py`.** `load_entities` folds keys through `weave_index.norm` with the
designation set hoisted once, so the key spaces match. DANGLING / PARTIALLY-DANGLING are exclusive
and computed against the live records, and all four printed lists are uncapped with their counts
in the header.

---

## COVERAGE

Recorded by this batch via `sweep_plan.record('run37', [...], batch=9)` — see the run log below
the findings in `state/SWEEP_COVERAGE.json`.

## ORDERS FILED

All nine are in `state/workorders.json` with `found_by = sweep37-batch09`.

| id | sev | code |
|---|---|---|
| `4f02ea2d7ecd` | MAJOR | READ_CAP_CHUNKS_FILES_A_TRUNCATED_READ_AS_COMPLETE (F1) |
| `7bffb5634d7a` | MAJOR | THREAD_INTEGRITY_RECIPROCAL_DECIDED_ON_ONE_DIRECTION (F2) |
| `543cec75ad02` | MINOR | WEAVE_MECHANICS_FILTER_SEARCHES_A_300_CHAR_WINDOW (F3) |
| `8c3d5e9aac87` | MINOR | READ_QUEUE_BUILDS_THE_CACHE_PATH_INLINE_BYPASSING_CACHEKEY (F4) |
| `25266fa8c2dc` | MINOR | CORPUS_DB_SPINE_LOOKUP_FAILURE_WRITTEN_AS_UNSHELVED (F5) |
| `b66146e38fb5` | MINOR | CORPUS_DB_EVIDENCE_INCLUDED_CAVEAT_HAS_NO_READER (F6) |
| `6160ef68b229` | MINOR | CORPUS_DB_CLI_TRUNCATES_EVERY_CELL_WITH_NO_MARKER (F7) |
| `418e83501f0f` | MINOR | LEDGER_GUARD_CLI_CLAIMS_ALL_INTACT_HAVING_RUN_ONE_OF_THREE_CHECKS (F8) |
| `6f95694b8143` | MINOR | READ_FELL_BACK_COUNTS_CHUNKS_THE_BENCHED_GPU_NEVER_GOT (F9) |

NOT re-filed, confirmed still open and still correct: **3b030216a138** (address.py's
worded-containment hazard), **944274e8bfd8** (ENTITY_INDEX.json still 400-truncated on disk),
**25ec11447b4c** (weave's dead `pair_weights` / unused `idf, N`), **4e92365b54f6** and
**de43fe54feb7** (callerless `build_address` / `ceiling_for` — both still callerless; their
`where` line numbers have drifted, see the observations above).
