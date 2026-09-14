# AUDIT — sweep run57, batch 07

Modules read in full, top to bottom, in chunks: `src/cascade_bridge.py` (2317 lines, read in 4
passes), `src/corpus_db.py` (1040 lines), `src/onomast.py` (773 lines), `src/endpoint.py` (577
lines), `src/reference.py` (497 lines), `src/hosts.py` (396 lines), `src/wh40k.py` (350 lines),
`src/context_budget.py` (296 lines).

Open queue checked first (`workorders.open_orders()` and the full `state/workorders.json`,
including resolved/closed entries, grepped for module names). Known already, per the brief:
`hosts.add()` lost update = order `3d000c4e482f`. Prior-audit files named in the brief
(`handoff/sweep56/` batches 04, 07, 12, 15) were read and cross-checked; in addition, two of
these eight modules turn out to have ALSO been fully read by sweep56 batches not named in the
brief — `reference.py` in batch11, `wh40k.py` in batch14 — and those were checked too, so nothing
below re-derives a finding already on record in any of those four extra batches.

All eight modules in this batch are part of the project's most heavily self-audited stratum:
nearly every non-obvious branch already carries an in-line comment naming the order that found
and fixed the exact defect class this sweep is looking for (fail-open, checks that cannot fail,
undisclosed caps, lost updates). Every such claim below was checked against the current source,
not taken on the comment's word.

---

## DEFECT (new) — lost-update read-modify-write on `data/ONOMASTICON.json`, no compare-and-swap

**Module:** `src/onomast.py` (the read-modify-write logic), with the second writer in
`src/pipeline.py` (out of this batch's module list, cited only to establish the race exists)

**The two writers:**

1. `src/onomast.py` `main()`, line 761:
   ```python
   if not silence.write_json(OUT, named, indent=2, ensure_ascii=False):
   ```
2. `src/pipeline.py` `phase_weave`, line 3202:
   ```python
   landed.append(land_json(os.path.join(HERE, "data/ONOMASTICON.json"), named, indent=2))
   ```
   `land_json` (pipeline.py:1093-1109) calls `_landed` (pipeline.py:1013-1028), which calls
   `silence.replace_retry(tmp, path)` — a plain atomic rename with Windows-denial retry, **not**
   `silence.replace_if_unchanged`.

Both writers reach that write through the identical read path, `onomast.name_worlds()`
(onomast.py:545-685), which:

- reads the current file whole via `load_onomasticon()` (onomast.py:506-537, a plain
  `json.load`, no digest taken),
- computes `merged` by folding this run's new namings over the prior dict in memory
  (onomast.py:667-685),
- returns the WHOLE onomasticon, which the caller then writes back whole.

Neither writer takes a digest of `OUT` at read time and neither passes it through
`silence.replace_if_unchanged` before landing. `silence.write_json`'s own docstring (verified at
`src/silence.py:773-788`) says only that it makes the individual write atomic and
torn-write-proof; it explicitly performs no staleness check against what was read. This is the
exact "m42" shape the project's own doctrine describes and has fixed elsewhere in this same
codebase — quoting `endpoint.py:108-121` (in this batch's module list), which fixed the identical
problem for `ENDPOINTS.json`:

> "ATOMIC WAS NOT ENOUGH... `_MEM` was not [given a compare-and-swap], and `_MEM` is worse,
> because it is a read-ONCE cache. A long-running miner loads `ENDPOINTS.json` at its first
> `detect()` and then writes that whole snapshot back after every probe... Two such processes...
> each land a complete, consistent, atomic file that predates every host the OTHER one probed.
> Nothing fails and nothing is torn; verdicts simply disappear..."

`endpoint.py`'s `_save()` (line 91 onward) and `register()` (line 485 onward) were both given a
real digest-based CAS (`silence.digest_of` + `silence.replace_if_unchanged`, with retry-on-
mismatch) for exactly this reason. `cascade_bridge.py`'s `record_unrecognised()` (line 1046
onward, in this batch too) does the same, with an added read-back verification because even
`replace_if_unchanged` is not instruction-atomic. `onomast.py`'s write to `ONOMASTICON.json` —
which by the module's own docstring (onomast.py:552-562, "APPEND-ONLY... it used to survive
exactly ONE cycle") is explicitly a file with two independent writers reading and re-writing the
whole document — never received the same treatment. It is the same shape already recorded as
`hosts.add()`'s lost update (order `3d000c4e482f`, this batch's other module), reached in a
different file that this project's own comments elsewhere identify as the general failure
pattern ("`scout._mutate`, `workorders._mutate` and `runguard._land_claim` were all moved onto
the same day; this call site was simply missed" — `endpoint.py:516-517`).

**Concrete race:** process A (say, a `pipeline.py` full run) and process B (a standalone
`onomast.py --main` re-run, or a second concurrent pipeline invocation touching the weave phase)
both call `name_worlds(resolved)` around the same time. Both read the same prior `ONOMASTICON.json`.
Both compute their own `merged` dict (identical if `resolved` is unchanged, but NOT identical if
one process's `resolved` differs even slightly — e.g. a resolution pass mid-flight, or one
process running against a just-refreshed `data/RESOLVED_ENTITIES.json` the other has not picked
up yet). Whichever process's `write_json`/`land_json` call lands its rename last wins outright;
the other's designations — including any first-time namings it just coined via
`coin_well_formed_stamped`, which is NOT idempotent across processes racing on the same `taken`
set read from two different snapshots of the prior file — are silently discarded, with **no
error, no note, and a `landed=True` result on both sides**. Given `coin_well_formed_stamped`'s own
docstring stakes ("Shelfmarks are unique... a duplicate here silently reassigns already-published
citations: two beings merged under one designation"), a lost update here is not merely a wasted
write, it can silently reintroduce the exact duplicate-designation hazard `coin_well_formed_stamped`
was hardened against on 2026-09-08 (order `845dbaec182f`) — just from the outside, at the file
level, instead of inside one process's `taken` set.

**Why it matters:** this is squarely one of the sweep's named hunt categories ("lost-update
read-modify-write on shared state files"), on a file the module's own docstring already
identifies as having exactly two writers and an append-only contract that depends on every write
correctly seeing every prior write. Severity is medium — the collision window is the time between
`load_onomasticon()`'s read and the writer's rename landing, which is short (see `endpoint.py`'s
own comment that this window is normally survivable "by luck of the cache's mtime alone" until it
isn't) — but the failure mode when it does land is a silent, undetectable data loss exactly like
the one `9309a040f208` and `549069e9c298` were filed to close for the *single-writer-across-runs*
version of this same file. Nothing here closes the *concurrent-writer* version.

**Confidence: DEFECT.** Verified directly: `silence.write_json` → `replace_retry` (no CAS,
confirmed against `silence.py:773-788` and `:722-737`); `land_json` → `_landed` → `replace_retry`
(no CAS, confirmed against `pipeline.py:1093-1109` and `:1013-1028`); both writers call
`onomast.name_worlds()`, whose only guard against staleness is the in-process `taken` set built
from one `load_onomasticon()` read, not a file-level compare-and-swap.

---

## KNOWN — `hosts.py:add()` lost update, `data/SOURCE_HOSTS.json`

**Module:** `src/hosts.py`, lines 114-145.

Re-verified directly against current source: `add()` (line 114) does
`data = _load(EXTRA, {})` (line 130, a plain read, no digest), mutates `rows` in memory (lines
131-134), and lands the whole document through `silence.write_json` (line 142) — atomic, not
compare-and-swapped. This is precisely order `3d000c4e482f`, named in the sweep brief as already
open. No change since it was filed; still present exactly as described there.

**Confidence: KNOWN(3d000c4e482f).**

---

## KNOWN — stale line-number citations, `corpus_db.py`

**Module:** `src/corpus_db.py`.

Re-verified both of sweep56 batch07's findings directly against the current file — both citations
are still stale, unchanged since that audit:

- `age_seconds()` docstring (lines 428-429) still reads:
  ```
  the rebuild's stale-`built_at` warning (`replace_retry`'s comment, :321) and the no-SQL
  branch's ABSENT/UNREADABLE note in `main()` (:742)
  ```
  Line 321 today is `if evidence_limit:` / the evidence-limit-ignored note — unrelated. The
  actual `replace_retry` comment is at lines 392-397 ("THE VERDICT OF THE FINAL WRITE HAS TO
  REACH THE CALLER..."). Line 742 today is inside `_cell()`'s docstring; the actual no-SQL
  ABSENT/UNREADABLE comment is at lines 1000-1004.
- `drift()` (line 634-636) still cites `:190` for "the same shape as `rebuild()`'s list"; line
  190 today is prose inside the spine-resolver comment block. The actual matching line
  (`unreadable_records.append(...)`) is at line 236.

**Confidence: KNOWN**, matching sweep56 batch07's "DEFECT — two more stale self-referential line
citations in `corpus_db.py`" verbatim. No new corpus_db.py findings beyond this. Checked
separately and found clean: no unparameterised SQL that could write (`--sql`/`--canned` both
route through `connect(readonly=True)`, i.e. `sqlite3.connect('file:...?mode=ro', uri=True)`,
which SQLite itself refuses to write through regardless of the query text); no new caps (the
`CANNED` block and `_cell()`'s ellipsis-marked truncation are both already-disclosed, deliberate,
and reversible via `--sql`); `rebuild()`'s whole-file replace via `replace_retry` is not a
lost-update hazard because it is a pure derived rebuild from canonical JSON, not a
read-modify-write of accumulated state.

---

## KNOWN — stale sibling citation, `onomast.py:754`

**Module:** `src/onomast.py`, line 754 (inside `main()`'s comment explaining the gated write):
```python
# Every sibling repaired by that sweep does the opposite
# (genre.py:327-331, sevenfold.py:412-415, wh40k.py:290-295). The stake here is that
```
Matches sweep56 batch07's "DEFECT — stale cross-file line citations in `onomast.py:754`" exactly
(same three citations, same file). Re-verified `wh40k.py:290-295` against the current file in
this batch: line 290-295 today sits inside the `--full` per-entity print loop's provenance-mark
comment, not a write-denial branch; the actual gated write in `wh40k.py` is at lines 338-343
(`if not silence.write_json(OUT, out, ...)`). Still stale, unchanged.

**Confidence: KNOWN**, sweep56 batch07.

---

## KNOWN — off-by-one self-citation, `reference.py:374`

**Module:** `src/reference.py`, line 374:
```python
# (`silence` is imported at module level and used at :245; the re-import that stood here was
```
The actual first `silence.note(...)` call in this file is at line 246
(`silence.note("reference.py:shelfmark-navtree")`), not 245 — line 245 is the closing
`except Exception:` line above it. Matches sweep56 batch11's "QUESTION — `src/reference.py:374`
— citation off by one line" exactly (that audit was not one of the four named in this batch's
brief, but was found and cross-checked here to avoid re-deriving it). Still present, unchanged.

**Confidence: KNOWN**, sweep56 batch11.

---

## KNOWN — `onomast.py:732` possible IndexError on empty `attestations`

**Module:** `src/onomast.py`, line 732 (`main()`'s report loop):
```python
src = v["attestations"][0]
```
This is open order `5d0fa30e4b09` item 6 ("SWEEP48_OPEN_QUESTIONS_NEEDING_A_READING"), filed as a
QUESTION rather than a defect: "`v["attestations"][0]` would IndexError on an empty list; no
in-file guarantee it is non-empty was found. Likely an upstream resolver invariant." Re-verified:
line and code are unchanged, and no in-file guarantee was found in this pass either.

**Confidence: KNOWN(5d0fa30e4b09, item 6) — QUESTION**, not re-filed.

---

## KNOWN — `endpoint.py:475-482` `source_pages()` collapses ABSENT and UNREADABLE

**Module:** `src/endpoint.py`, lines 475-482:
```python
def source_pages(source):
    """The URLs registered for a source that has no wiki. [] when it has none."""
    try:
        with open(PAGES_FILE, encoding="utf-8") as f:
            return (json.load(f) or {}).get(source) or []
    except Exception:
        silence.note("endpoint.py:source_pages")
        return []
```
This is open order `5d0fa30e4b09` item 3: "`source_pages()` collapses 'absent' and 'unreadable'
into the same `[]`, while its sibling `register()` deliberately distinguishes them." Re-verified:
code unchanged from what that order describes. `register()` a few lines down (line 485 onward)
does distinguish the two states and raises on unreadable, which is the asymmetry the order names.

**Confidence: KNOWN(5d0fa30e4b09, item 3) — QUESTION**, not re-filed.

---

## KNOWN — `cascade_bridge.py` local roster names an uninstalled model

**Module:** `src/cascade_bridge.py`, lines 49-69 (module-level comment, re-affirmed
2026-09-08): Cascade's `config.json` (outside this repo) names three `ollama:local` entries
none of which match the one model actually resident in the local Ollama daemon
(`qwen3:8b`), so "every local bucket 404s [and] `allsweep` grades this subsystem bad on every
run." This is order `9fb8a6b10c1f` ("CASCADE_BRIDGE_HAS_NO_REACHABLE_MODEL"), explicitly named as
already known in the sweep brief. The file's own comment states it was "RE-MEASURED 2026-09-08,
and unchanged since the order was filed" — still true today; the remedy is a config edit outside
this repository (`<CASCADE_HOME>/config.json`), which this project's own doctrine says it will
not reach out and make.

**Confidence: KNOWN(9fb8a6b10c1f).**

---

## KNOWN (documented, deliberately not filed) — `context_budget.py:276-296` `report()` is dead code

**Module:** `src/context_budget.py`, `report()` (lines 276-296).

Grepped `src/` for every spelling of a caller (`.report(`, `context_budget import`,
`import context_budget`, `_CBUD.report`): the only production imports of `context_budget` are in
`generate.py` (`assert_fits` only) and `manifest_builder.py` (`feats_block_budget` only).
`report()`'s own docstring claims "Used by health/preflight and by the ledgers" — that claim is
false today; no caller exists anywhere in `src/`. This is not a new finding: `liveness.py:428`
and `drill.py:306` both already name this exact function ("`context_budget.py:276 report()`... is
GENUINE: no caller of any spelling exists in `src/`, confirmed by grep as well as by this pass")
and record, in the same breath, that it is deliberately **not** hand-filed as a work order,
"because the point of the order was the DETECTOR, and a hand-filed instance is what having no
instrument looks like." Recording it here only to confirm the docstring's "used by health/
preflight" claim is still stale and the dead-code finding is still current — not re-filing it,
per the standing ruling already on record in those two files.

**Confidence: KNOWN (documented in liveness.py:428 / drill.py:306; deliberately unfiled).**

---

## Checked and found clean

- **`src/hosts.py`** — no caps (the file's own history is a running argument against `[:40]`-style
  rosters and none remain: `discover()`'s `names` and `spec` lists are explicitly uncapped except
  for the disclosed, reported `per_source` speculative-guess bound, which prints its own withheld
  count). `_load()` fails closed (raises on a corrupt or non-dict host map rather than returning
  `{}`). `discover()`'s three-state result handling (`None` / `_PROBE_FAILED` / a list) is
  internally consistent and each branch is counted and named on stderr, not swallowed. Aside from
  `add()`'s already-KNOWN lost update above, no new finding.
- **`src/context_budget.py`** — the module is essentially a worked example of Hard Rule 0
  discipline: `content_budget_chars()` explicitly documents that a caller must treat a
  zero-or-negative budget as "cannot fit," and its one caller (`manifest_builder.py:408-414`)
  does exactly that, raising `ContextOverflow` rather than clamping. `assert_fits()` raises
  rather than silently truncating. No fail-open path, no undisclosed cap, no lost-update
  (nothing here is a shared read-modify-write). No SQL. Aside from the already-documented dead
  `report()` above, nothing else found.
- **`src/wh40k.py`** — read in full; almost entirely literal roster data plus `compute()` and
  `main()`. `_provenance()` defaults to `"unattributed"`, not `"wiki"`, which is the fail-closed
  direction the module's own docstring argues for. The main-write gate (`silence.write_json` at
  line 338, `silence.note` on denial, `return 1`) is correctly wired, matching the fix already
  recorded in its own comment (lines 324-337) for the "gated write, discarded verdict" class of
  bug. No new finding.
- **`src/endpoint.py`** — read in full. Both shared-state writers (`_save()` for
  `ENDPOINTS.json` and `register()` for `SOURCE_PAGES.json`) already implement a full
  digest-based compare-and-swap with retry (`silence.digest_of` + `silence.replace_if_unchanged`),
  which is the correct pattern the onomast.py finding above is missing. `detect()`'s DEAD_TTL
  re-probe logic, `fetch_raw`'s/`fetch_html`'s refusal-vs-absence distinction (404/410 vs other
  HTTP errors, and the 200-with-HTML-body block-page case) are all already fixed and disclosed in
  the file's own history. Aside from the already-KNOWN `source_pages()` QUESTION above, no new
  finding.
- **`src/reference.py`** — read in full. `shelfmark()`'s NAVTREE-unreadable path distinguishes a
  genuinely-unknown rung from a could-not-measure one and marks the artefact itself, not just an
  internal note (lines 263-271) — a good example of the fail-closed-and-say-so pattern. `main()`'s
  exit code is gated on BOTH the write landing and the calibration holding (lines 388-403,
  correctly distinguishing the two fault classes). Aside from the already-KNOWN `:374` citation
  above, no new finding.
- **`src/onomast.py`** — read in full. `load_onomasticon()` fails closed on a corrupt file
  (raises `OnomasticonUnreadable` rather than returning `{}`) — correct per the module's own
  history (order `549069e9c298`). `coin_well_formed_stamped()`'s exhaustion fallback is provably
  unique (digest-tail extension) rather than merely deterministic, correctly implementing owner
  ruling `845dbaec182f`. `name_worlds()`'s `retired` vs `standing` distinction is correctly wired
  per order `e5001f0b0153`. The one new, and one further already-KNOWN, finding are both above.
- **`src/corpus_db.py`** — read in full; see the KNOWN citation findings above. No SQL injection
  or unparameterised-write path found (confirmed `connect(readonly=True)` uses SQLite's own
  `mode=ro` URI enforcement, which refuses writes at the engine level regardless of query text).
  No undisclosed caps (`CANNED` deliberately carries no `LIMIT`s, and the file's own header
  explains why at length). `rebuild()`'s handling of a corrupt `WIKI_HOSTS.json`/`COVERAGE.json`/
  `CHARTER_SPINE_CODES.json` all correctly distinguish "no value" from "could not ask" via the
  `*_LOOKUP_FAILED` sentinels and `meta` rows, and `_freshness_banner()` surfaces every one of
  those caveats above the numbers, unconditionally.
- **`src/cascade_bridge.py`** — read in full, in four passes (all 2317 lines). This is the most
  heavily self-hardened file in the batch: `record_unrecognised()`'s compare-and-swap (with
  read-back verification, since even `replace_if_unchanged` is not instruction-atomic across a
  denied-rename retry) is the correct pattern; `_ask_call()`'s reservation lifecycle (reserve
  before the try, release in `finally`, invariant documented and checked at line 1666-1671),
  the graded bench (`FIRST_BENCH`/`MAX_BENCH`/`AUTH_BENCH`), and the permanent-vs-transient
  classifier vocabulary are all extensively cross-checked against measured provider text in their
  own comments. Verified the two "checked and found NOT stale" self-citations sweep56 batch07
  already cleared (`:2291-2292`, the `__main__`-block relocation note; `:416/427/779`, the
  cross-project citations into `C:\Users\imarl\cascade\cascade\engine.py`) are both still
  accurate against current source. Aside from the already-KNOWN `9fb8a6b10c1f` roster-mismatch
  finding above, no new finding.

---

## Confidence summary

- 1 NEW DEFECT (medium confidence): lost-update read-modify-write on `data/ONOMASTICON.json`,
  `src/onomast.py` (read path) / `src/pipeline.py` (second writer, out of batch scope), no
  compare-and-swap on either writer.
- 0 NEW QUESTIONs raised to a level worth recording — everything else odd on first read was
  already explained, and checked against current source rather than trusted.
- 7 KNOWN findings reconfirmed present, unchanged, against current source: `hosts.py:add()` lost
  update (`3d000c4e482f`); two stale citations in `corpus_db.py` and one in `onomast.py:754`
  (sweep56 batch07); one off-by-one citation in `reference.py:374` (sweep56 batch11); the
  `onomast.py:732` IndexError question and the `endpoint.py:475-482` absent/unreadable question
  (both `5d0fa30e4b09`); the cascade local-roster mismatch (`9fb8a6b10c1f`); and the deliberately
  unfiled `context_budget.py:276` dead-code finding (documented in `liveness.py`/`drill.py`).
