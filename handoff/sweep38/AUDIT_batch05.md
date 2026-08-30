# SWEEP 38 — AUDIT, BATCH 05

Agent: `sweep38-batch05`. Run: `run38`. 8 modules, 4,463 lines, all read in full.

Environment: `C:/Users/imarl/miniconda3/python.exe`, `PYTHONIOENCODING=utf-8`, repo root
`C:\Users\imarl\panscriptum-library-kit`. No file under `src/` was edited — this was an audit
pass. Reproductions were run from the repo root; helper script kept in the batch scratch
directory.

Orders filed: 14 (2 MAJOR, 9 MINOR, 3 INFO — one of the INFO rows is a QUESTION at OWNER).

---

## cascade_bridge.py — 1,767 lines — READ IN FULL — 6 findings + 1 INFO

The single largest module in the batch and the one carrying the most history in its comments.
Most of that history is correct and load-bearing; the faults below are all in the seams between
repairs rather than in the repairs themselves.

### FINDING (MAJOR) — the global engine/router build is unsynchronised
`order af50bab5a369` — `CASCADE_GLOBAL_ENGINE_BUILD_UNLOCKED`, `cascade_bridge.py:62-119`

`_BUILD_LOCK` is defined at `:55` and used only in `thread_engine()` (`:113`), guarding the
PER-THREAD Engine build — the half that needs no cross-thread coordination. The GLOBAL build in
`engine()` runs with no lock at all: `if _ENGINE is not None: return _ENGINE` at `:69-70`, then
`_ROUTER = R.Router(...)` at `:84`, `_ENGINE = E.Engine(...)` at `:85`, and `_CFG["cfg"] = cfg`
at `:88`.

Two consequences, and the readers run sixteen workers wide, all of which reach `thread_engine()`
→ `engine()` in the same instant on a cold start:

* **Two Routers.** Both threads see `_ENGINE is None`, both build, the second overwrites
  `_ROUTER`. Per-thread Engines already built at `:117` hold the first Router while every
  routing decision in the module (`_alive`, the claim loop, `widen_candidates`, `_bucket_of`,
  `pools`, `cloud_buckets`, `prove`, `try_disabled`) reads the global, now the second. That
  breaks the exact invariant `thread_engine`'s own docstring gives as the reason the Router is
  shared: *"the in-flight reservations that stop eight workers piling onto one meter only work
  if all eight consult the same counter."*
* **`KeyError: 'cfg'`.** `_ENGINE` is published at `:85`; `_CFG["cfg"]` is not written until
  `:88`. A second thread returning from `engine()` between those two statements falls into
  `E.Engine(_CFG["cfg"], st, _ROUTER)` at `:117` and raises. `_ask_call` calls `thread_engine()`
  bare at `:1146`, so it escapes `ask()` and takes the worker's call with it.

Not reproduced live (would need a cold multi-worker start against a real Cascade install), but
it is a plain read of the sequence and the remedy is standard double-checked locking with
`_ENGINE` published last.

### FINDING (MINOR) — the widen fallback never records which bucket it burned
`order d5012fbc73c1` — `CASCADE_WIDEN_PATH_NO_TRIED_ADD`, `cascade_bridge.py:1241-1250`

The ordinary claim loop calls `_tried_add(cand.bucket)` at `:1187`; the widened-fallback loop
reserves and pins without it. So a failure on the widen path leaves `_tried()` empty and the
metric row at `:1108-1110` writes `"model": ""`, `"tried": []` — the unattributable row the
comment at `:1095-1109` says was already fixed (*"426 cascade calls in six hours, every one a
failure, every one recorded as bucket `?`"*). The widen branch is not rare: its own comment
(`:1191-1213`) exists because the tagged pool is four buckets and all four were 402-ing, i.e.
under the conditions that motivated it, essentially every call goes through it.

### FINDING (MINOR) — `record_unrecognised` is a lost-update read-modify-write
`order 853aa8990132` — `CASCADE_UNRECOGNISED_LOST_UPDATE`, `cascade_bridge.py:775-817`

Whole-dict read at `:791-796`, whole-dict write at `:816`, serialised only by `_UNREC_LOCK`
(a `threading.Lock`, `:418`). The function's own comment at `:806-809` states the multi-process
fact — *"this file is written from every process that imports `cascade_bridge` (read, pipeline,
feats, overwatch)"* — and then closes only the temp-file half of it by moving to
`silence.write_json`'s pid+thread-unique temp name. Two processes racing still silently drop
each other's rows and `count` increments, concentrated exactly in a burst, which is when the
lost row is most likely to be the one that matters. `workorders._mutate` (`src/workorders.py:342-347`)
already implements the CAS-with-reapply pattern this needs.

### FINDING (MINOR) — reservation leaks if anything raises before the try/finally
`order e0b4a02c5133` — `CASCADE_RESERVE_OUTSIDE_TRY_FINALLY`, `cascade_bridge.py:1161-1267, 1516-1518`

`_ROUTER.reserve()` at `:1169` (pin path) and `:1245` (widen path); the matching `release` is in
the `finally` at `:1516-1518` whose `try` does not open until `:1364`. The unprotected span runs
`_pace`, `json.dumps(schema)` (`:1271`), the message build, and `Thread.start()` (`:1362`).
`json.dumps` raises on a non-serialisable schema and `Thread.start()` raises under thread
exhaustion — and order `f6c52ef7657f` records this host running out of ephemeral ports, so
resource faults here are not hypothetical. A leaked reservation permanently narrows the router's
view of a bucket's headroom, shrinking a pool the file repeatedly calls the binding constraint.

### FINDING (MINOR) — `selftest()` prints `ready[:12]`, undisclosed
`order c48c3de407d8` — `CASCADE_SELFTEST_READY_LIST_CAPPED`, `cascade_bridge.py:1535`

`len(ready)` is printed on the line above, so a reader can infer something was cut, but the
output never says so and never says which. The file's own comments record ~42 configured models
with ~26 holding working credentials, so the cap fires routinely — and `selftest` is the command
a person runs precisely to learn *which* providers are live. `cosmology_graph.main()`
(`src/cosmology_graph.py:173-176`) is the sibling that gets the disclosure right.

### FINDING (INFO) — `__main__` block sits above two thirds of the module
`order fa3900441022` — `CASCADE_MAIN_BLOCK_MID_FILE`, `cascade_bridge.py:1564-1582`

`prove()` (`:1587`) and `try_disabled()` (`:1701`) are defined after the `sys.exit(selftest())`,
so neither exists when the file runs as a script. Nothing is broken today; it is a trap primed
for whoever adds a `--prove` flag. Pure relocation fixes it.

### Verified and NOT filed
* `_extract_json` (`:132-165`) — fence-first then brace-matching; a parse failure at depth 0
  breaks the inner scan and correctly advances to the next `{`. Returns `None`, never `{}`, so
  an unparseable reply cannot read as "no feats". Correct as written.
* The classifier family (`local_transport`, `client_rejection`, `permanent_refusal`,
  `named_transient`, `pool_exhausted`, `empty_content`) — ordering is as the docstrings claim
  (`local_transport` first, then `client_rejection`, then permanent, then transient), word
  boundaries are on the numeric codes and substrings on the prose, and `_PERMANENT_CODES` is
  `\b(401|402)\b` with 403 correctly removed. The `cloudflare`-name-alone hole
  (order `62f4b7caae73`) is closed at both sites.
* `dead_forever()` mtime-keyed cache — correct in both directions, including the
  `stamp is None` case.
* `prove()` — `verdict` is bound on every path; the `by == ""` fail-open (order `fdebedb8d0ce`)
  is genuinely closed; `who` falls back to model id/label so the row can always name its subject.
* `try_disabled()` — the blank-`by` case *is* covered by `by != m.bucket` (an empty string is not
  equal to a non-empty bucket). It records no `reason` where `prove()` does, so a reader cannot
  tell "did not answer" from "a neighbour answered"; too thin to file, and `served: who` lets you
  infer it.
* `_bury` / `_alive` / `_clear` — the `UnboundLocalError` trap the comment at `:1000-1008`
  describes is genuinely gone, and no assignment to `_DEAD` remains in that scope.

---

## liveness.py — 532 lines — READ IN FULL — 1 finding (MAJOR)

### FINDING (MAJOR) — `dead_module` rows are counted and never printed
`order dded1fc0e664` — `LIVENESS_DEAD_MODULE_NEVER_PRINTED`, `liveness.py:499-527`

**Reproduced.** `python src/liveness.py --quiet`:

```
liveness: 47 finding(s) — 0 tautology, 0 phantom, 36 dead, 1 dead class, 0 unparsed
```

0+0+36+1+0 = **37**, not 47. The missing ten are the `dead_module` rows built at `:362-366` —
exactly the ten orphan modules `scan()`'s docstring names (chord_field, descending_ladder, halo,
handbuilt, module_index, pantheon, render, scale_theories, wh40k, zfighters). The print loop at
`:512-518` iterates a five-entry tuple that does not include `dead_module`, and the summary
format string at `:524-527` itemises the same five. `total` at `:510` sums `r.values()`, so the
rows exist only as an unexplained gap in an arithmetic that does not add up.

This is worse than an ordinary display bug because of why the limb exists. `scan()`'s docstring
argues that the per-symbol passes *cannot* see an orphan module by construction, that six of the
ten produced no row at all before this limb, and that `drill.LIVENESS_CEILING` had to be raised
41 → 52 in the same change to make room for it. The limb landed 2026-08-29 (order `209391b4f990`)
and the ratchet in `drill.py` reads `scan()` directly, so the gate is fine — it is the human
report, the only place a person would read these, that omits them. Remedy in the order includes
asserting that the itemised counts sum to `total`, so the next limb cannot vanish the same way.

### Verified and NOT filed
* `_stem` / `referenced` — self-reference correctly excluded (`g != me`), and all three legitimate
  reference routes (import, from-import, string naming the module or its filename) are counted.
* The scoping repair — bare names per-module via `used_local`, `self`/`cls` attributes per-class
  via `_self_attrs`/`scoped` with MRO approximated by simple name in both directions, everything
  else global. The `coverage._p()` worked example is genuinely reachable by this now.
* PHANTOM — `defined` seeds from `builtins` (not `dir(__builtins__)`), covers match-statement
  captures, and the condition walk covers `If`/`While`/`IfExp`/`Assert`/`match_case.guard`/
  bare `BoolOp` statements/comprehension filters.
* `_parse` returning `(tree, reason)` — the reason genuinely rides along into the `unparsed` row.

### Noted, not filed
`dead_module`'s exemption test is `_stem(n) not in EXEMPT` (`:366`), where `EXEMPT` is a dict of
**function** names with function-shaped reasons ("CLI entry point, called by `__main__`",
"constructor", "protocol"). A module named `main.py` or `log_message.py` would be exempted for a
reason that makes no sense about a module. No collision exists in the tree today and the fix is
cosmetic; recorded here rather than filed so the next reader is not surprised by it.

---

## estate.py — 449 lines — READ IN FULL — 2 findings + 1 QUESTION

### FINDING (MINOR) — an empty index JSON makes its row disappear
`order f856ff7445b0` — `ESTATE_EMPTY_INDEX_JSON_ROW_VANISHES`, `estate.py:342-357`

**Reproduced.** `output/index/catalog.json` exists and contains exactly `{}`. `estate.written()`
returns four rows and no "generation catalog" row:

```
chapters written              | 0 files under output/raw
sources on the roll           | 210
generation failures on record | 6 records
sources with no spine code    | 152 bytes
```

The `if d:` at `:352` suppresses the row, making an empty file indistinguishable on the page from
an absent one (`continue` at `:348`). This is the identical fault the handler twelve lines above
(`:330-341`) was repaired for **in the same function**, with the reasoning already written out:
*"a missing row reads exactly like a row that was never supposed to be there"*, and *"the
denominator disappearing is the worse half: `chapters written 0` next to nothing at all is
unreadable"* — which is exactly the page produced today, since chapters written is 0 and the
catalog row that would corroborate it is gone. Remedy: drop the guard, emit "0 records", keep it
`bad=False`.

### FINDING (MINOR) — `.jsonl` and the backup families are only size-checked
`order 19fc2fdda102` — `ESTATE_JSONL_AND_BACKUPS_ONLY_SIZE_CHECKED`, `estate.py:71, 102-139`

`inspect()` opens a file only when the extension is `.json` or in `TEXT_EXT`; everything else
gets `getsize` and a zero-byte test. The module header says *"every file, opened. No sampling"*
and `inspect()`'s docstring says *"One file, opened and actually read"* — both overstate what the
code does. Census over `data/` + `state/`: 5 `.jsonl`, plus `.presilence` (16), `.precatfix` (2),
`.corrupt` (2), `.postsweep`, `.prewiden`, `.precapfix`, `.new`, `.prev`, `.err`, `.out`. The
`.jsonl` files matter: `state/model_metrics.jsonl` is the live cloud-lane ledger written by five
processes, and `cascade_bridge._metric`'s own comment (`:1062`) explains the single-syscall append
exists *because* "a buffered append can be split mid-line". A torn line is neither zero bytes nor
a checked extension, so this battery cannot see the corruption mode its sibling module is
defending against. Binary files (`.db`, `.zip`, `.db-wal`) are correctly left alone.

### QUESTION (INFO, OWNER) — the spine-gap row names four of thirty-three
`order 189532cbf41a` — `ESTATE_SPINE_GAP_LISTS_ONLY_FOUR`, `estate.py:238-239`

Live output: `33 — e.g. Call of Duty Zombies, Dragon Ball Z, Eastern astrology (BaZi, jyotisha),
EndWar`. Reading one: the count is disclosed, "e.g." is honest, and the comment at `:232-237`
grades the row `bad=False` because Hard Rule 2 makes this owner work — the row exists to keep the
*number* visible, not to hand anyone a worklist. Reading two: Hard Rule 0 says no caps, 33 names
is nothing to print, and the artifact that would carry the full list —
`output/index/unassigned_sources.md` — currently reads "**None.** Every populated source on the
Acquisitions Roll resolves to a real spine code as of this manifest build", which is stale and
contradicts the 33 this function measures. On that reading there is today no place in the tree
where the twenty-nine missing names can be read. Filed as a question at OWNER.

*(Side observation, not filed as a code defect: `output/index/unassigned_sources.md` is stale.
It asserts zero unassigned sources while `charter()` measures 33 against the live spine file.)*

### Verified and NOT filed
* `charter()`'s errata block — each of the four rows genuinely tests what its text claims
  (the "Can threaten…" column of the parsed Magnitude table, not mere word presence), and the
  table-parse guard at `:273-280` correctly refuses to report four cleared rows when the tables
  cannot be read. Confirmed by execution: all four errata still fire, all `bad=False`, and the
  band comparison against `assay.LADDER` finds no gap.
* `inspect()`'s zero-byte log exemption, the two separate handlers for spine file vs. records,
  and every `silence.note` tag — all correct and all reach a visible row.
* `external()` grades OLLAMA UNREACHABLE / CASCADE NOT AVAILABLE red and benched buckets not-red,
  which matches the stated tiering.
* `terminal()` uses a non-recursive `os.listdir`, so a data file in a subdirectory would be
  missed — the reference viewer is flat today, so no live gap; noted, not filed.

---

## derivation.py — 664 lines — READ IN FULL — 2 findings (MINOR)

### FINDING (MINOR) — "deepest derivation chains" prints 6 of 112, undisclosed, mid-tie
`order 81410993cb8d` — `DERIVATION_DEEPEST_CHAINS_CUT_AT_SIX`, `derivation.py:639-646`

`sorted(LEDGER, key=lambda x: -depth(x))[:6]` — no count, no "and N more", no flag. Every other
panel in this `main()` reports its whole subject (the kind histogram covers all 112,
`check_graph()` prints every problem, the constants map walks every module). **Measured against
the live ledger:** the 6th row (`genre_priors`) and the 7th (`world_profile`) are both at depth 9,
as is `burg_population` — so the cut lands inside a tie and which equally-deep chains a reader
sees is decided by dict insertion order, not by the ranking the panel claims to show. 106 rows are
dropped silently.

### FINDING (MINOR) — a module that will not parse is printed as "(absent)"
`order 6baeeb468a24` — `DERIVATION_UNPARSED_REPORTED_AS_ABSENT`, `derivation.py:566-589, 650-655`

`scan_constants` returns `None` for both "file missing" (`:582`) and "SyntaxError" (`:589`), and
`main()` renders both as `(absent)` at `:653`. `SCAN_MODULES` is built at `:543` from
`os.listdir(HERE)` over the same directory `scan_constants` then reads, so the missing-file branch
is unreachable outside a race — every `(absent)` a reader ever sees on this map is really "will
not parse". The parse failure *is* recorded via `silence.note`, but that goes to the silence
ledger while the panel in front of the reader asserts the opposite. `liveness._parse`
(`src/liveness.py:89-103`) is the sibling that solved exactly this by carrying the reason.

### Verified and NOT filed
* `check_graph()` — the `kind` validation (order `72bc85d74ccf`) is real and reachable; DANGLING,
  ROOTLESS, UNSIGNED and CYCLE all test what they claim; the cycle walk's state machine is
  correct on unwind.
* `_target_names` / `scan_constants` — tuple, list, starred, `AnnAssign` and chained `A = B = v`
  targets are all handled; the per-statement literal count over-states rather than omits, and
  says so.
* `_address_total_bits()` — genuinely reads `address_space.TOTAL_BITS` rather than restating it,
  and its failure sentence ("an unreadable number of") reads correctly interpolated into the
  note.
* `main()` returns `1` when the graph has problems. Verdict is not discarded.

---

## pantheon.py — 339 lines — READ IN FULL — 1 finding (MINOR) + 1 INFO

### FINDING (MINOR) — WRITE DENIED prints, then `return 0`
`order a012b799a6c9` — `PANTHEON_WRITE_DENIED_EXITS_ZERO`, `pantheon.py:265, 331-335`

`write_ok = silence.write_json(...)` is captured and the denial is printed, and then `main()`
returns 0 regardless. Any script or sweep row shelling this module records a clean success for a
run in which `data/PANTHEON.json` was not written. The comment at `:261-264` documents exactly
this repair for the *printed* line and stops one step short of the exit code; its own named
sibling `cosmology_graph.main()` returns 1 in the identical situation
(`src/cosmology_graph.py:238-239`). One line.

### FINDING (INFO) — the band-label table holds 8 of the charter's 11 bands
`order 1e1d0ddea7f2` — `PANTHEON_BAND_LABEL_TABLE_MISSES_M0_M9_M10`, `pantheon.py:286-291`

The dict is introduced as "Charter Part Two's magnitude table" and holds M1–M8. `estate.charter()`
against the live document reports M0–M10. Nothing blanks today (there is a `.get` fallback and
GODS tops out at M8), but the repair that added M1/M5/M6 left M0/M9/M10 out, so the comment now
describes a table more complete than the one beneath it — in a file where the comments are
load-bearing.

### Verified and NOT filed
* The `--full` view's citation wrapping (order `9d24c8a5febf`) is genuine: `textwrap.wrap` with a
  hanging indent, no `[:58]` anywhere, no cap on `epoch`.
* `compute()` / `value()` are straightforward; the Z_FIGHTERS merge is guarded and the failure
  noted.

---

## context_budget.py — 296 lines — READ IN FULL — NOTHING FOUND

Read in full, nothing found. Checked specifically:

* The negative-budget contract. `content_budget_chars`'s docstring says callers must treat zero or
  negative as "this cannot be done at this window" rather than clamping. **Verified downstream:**
  `feats_block_budget({"num_ctx": 2048})` returns `-5216`, and the only production caller,
  `src/manifest_builder.py:369-374`, does `if budget <= 0: raise _CBUD.ContextOverflow(...)` with
  the reasoning restated. The contract is honoured; no order filed.
* `feats_block_budget({"num_ctx": 6144})` returns `5023` — positive and plausible at the live
  window.
* Both `except Exception` handlers around the prompt-file reads (`:249-256`, `:259-263`,
  `:279-289`) are the fail-open direction the module exists to refuse — and both record
  `silence.note` and set `""`, which is the *conservative* direction here only because an empty
  scaffold widens the budget. That widening is the SWEEP34 fault `96ebf36510b8` named; the note
  is what makes it visible rather than silent, which is what the comment claims. Correct as
  written, though a hard refusal would be stronger — not filed, because the current behaviour is
  documented, recorded, and deliberately chosen.
* `split_system_prompt` splits on the heading, not a line number, and degrades to a no-op when the
  heading is absent, exactly as documented.
* `window()`'s fallback is 6144, matching `read.config()` and `health.check_context_budget` as the
  comment claims.
* `estimate_tokens` ceilings (`+0.999`); both ratios sit below their measured values, keeping the
  pessimism the header argues for.
* `report()`'s `chapter_scaffold_chars` is `len(full)` and omits the chapter template, which is
  arguably narrow — but the key names the *system prompt* scaffold and the chapter template is
  not read by this function at all. Not a defect.

---

## cosmology_graph.py — 244 lines — READ IN FULL — NOTHING FOUND

Read in full, nothing found. Checked specifically:

* The write is complete and says so: every pair is emitted, `pairs_filtered: False`,
  `threshold_applies_to: "clusters"`, and `shared_sample` carries the WHOLE list with no `< 8`
  cap (the m144 repair is genuinely in place at `:115-122`).
* The write is gated: `landed = silence.write_json(...)`, the denial is printed with an explicit
  statement that the counts below describe memory rather than disk, and `main()` **returns 1**.
  This is the module the pantheon order above is measured against.
* `src_entities` is now actually written (`source_entities`, sorted, uncapped) rather than built
  and discarded.
* Console framing is disclosed on both panels: `--show` defaults to 16 with an explicit
  "… N further pairs not printed here … --show 0 prints them all, and --write emits every one",
  and the same for clusters.
* The docstring's weight formula (`1/log(n+1.5)`, ×0.15 above 12) matches `:107-109` exactly,
  including the 2026-08-25 correction note saying the prose was the thing that had been wrong.

One cosmetic note, not filed: at `:170-172` the shared-name sample is `names[:4]` joined and then
truncated again to 52 characters, while the `(+N more shared)` suffix counts only the names beyond
four. If the first four names are long, some of *them* are cut too and the suffix undercounts what
is hidden. Console framing only — `--write` emits every name — so this is a display nicety rather
than a Hard Rule 0 breach.

---

## ledger.py — 172 lines — READ IN FULL — NOTHING FOUND

Read in full, nothing found. Checked specifically:

* **The M10 ceiling repair (order `5082a529e937`) works.** Exercised across the whole ladder:
  M10 now spans `4.673e+90` → `4.673e+97` → `4.673e+104` for `ruin_score` 0 / 5 / 10, anchored at
  M10's own floor as the comment says, rather than the previous collapse to a single value.
  Every other band moves monotonically too.
* **No hand-copied constant.** `JOULES_PER_STANDARD` is imported from `physics.MATERIAL["rock"]["pulv"]`
  and evaluates to `214000000.0`, which matches the `2.14e8` the module docstring states — the
  prose has not drifted from the import.
* `currency_status` (order `e9167885aef6`) genuinely distinguishes unlisted from
  deliberately-non-convertible: `currency_status("quatloos")` → `(False, "unlisted")`, while
  `"poneglyph-grade favour"` → `(True, <the doctrinal sentence>)`. `to_standards` /
  `from_standards` keep their bare-`None` contract, as documented.
* `cross_rate("gil", "zenny")` = `0.7917`, which is `rb/ra` and matches the docstring's "how many
  units of b buy one unit of a".
* `assay_to_standards` guards `magnitude_band not in BAND_EDGES` before `LADDER.index`, and
  returns the caveat sentence about pricing deliverable work rather than the Anchor.

---

## COVERAGE

All eight modules in `brief05.json` were read in full and recorded against `run38`, batch 5:

`cascade_bridge.py`, `derivation.py`, `liveness.py`, `estate.py`, `pantheon.py`,
`context_budget.py`, `cosmology_graph.py`, `ledger.py`.

None skipped, none sampled.
