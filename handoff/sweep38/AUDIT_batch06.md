# SWEEP 38 — AUDIT, batch 06

Agent: `sweep38-batch06`. Run `run38`. 9 modules, 4,555 lines, **all read in full**.
Audit pass only — nothing under `src/` was edited.

Verification scripts live in this agent's scratch directory
(`.../scratchpad/sweep38/batch06/`): `repro_ref_rc.py`, `verify_truncations.py`,
`verify_pages_attribution.py`, `file_orders.py`.

One note on a side effect and its repair: `repro_ref_rc.py` calls `reference.main()` with a
deliberately-broken charter value, and `main()` writes `data/REFERENCE_ASSAYS.json`
unconditionally. That file was therefore briefly written with a wrong published value for Goku.
It was restored immediately by re-running `python src/reference.py` clean, and the restored
contents were verified: `{'Goku': ['M7', 7.62, 0.41], 'Naruto Uzumaki': ['M4', 4.31, 0.3],
'Monkey D. Luffy': ['M4', 4.08, 0.55]}`. Recorded here because an audit that quietly perturbs a
benchmark file is the thing this library least wants happening unremarked.

---

## `feats.py` (1,735 lines) — read in full

Two findings filed, one of them the batch's most serious.

### FILED — `FEATS_PAGES_HOST_EVIDENCE_NOT_NAME_MATCHED` (MAJOR, RUN, `127ec13af78a`)

`evidence_for`'s two non-wiki arms make the same claim in their comments — "the registered URLs
ARE the corpus, and the reader's name-matching does the attribution" — and only the `doc:` arm
honours it. `doc:` (1352-1364) filters `all_pages` through a local `_mentions(txt)` test.
`pages:` (1366-1374) does `pages = EP.fetch_html(urls)` and mines the lot, unfiltered. Nothing
downstream re-filters: `magnitude.assay_entity` (magnitude.py:1100) consumes `evidence_for`'s
output directly as this entity's own evidence, and its no-evidence reason string even says "this
entity's own source pages".

Reproduced against the live cache — counting distinct `provenance` digests per `pages:` host
directory under `data/feats/`:

| host dir | entities | distinct page-text digests |
|---|---:|---:|
| `pages_KibblesTasty_techno_psionic_line_` | 1,290 | **1** |
| `pages_all_Creeper_World` | 364 | **1** |
| `pages_Guildmasters_Guide_to_Ravnica` | 117 | **1** |
| `pages_A_Plethora_of_Paladins` | 116 | **1** |

Every entity in each directory holds a byte-identical evidence document. "Aasimar", "Aberrant
Life" and "Abhorrent Life" are each recorded as having mined the same four pages and produced the
same two feats. This is `page_looks_real`'s own stated failure — "verbatim provenance against the
wrong source is still wrong, and it looks exactly like success" — with the wrong source being a
sibling entity's page rather than a block page, so no gate in the file can see it. Five sources
are bound `pages:` in `data/WIKI_HOSTS.json`.

Remedy (in the order): hoist `_mentions` out of the `plain` branch and apply it to both arms;
invalidate `data/feats/pages_*`, because `cachekey.load` will otherwise keep the fix out of
effect. The order also states the expected honest consequence — most of those ~1,887 entities
will drop to zero feats, and that drop is the defect being removed.

### FILED — `FEATS_DIAGNOSTIC_STRINGS_CUT_AGAINST_THEIR_OWN_COMMENTS` (MINOR, LOCAL, `b0e69b869473`)

Two diagnostics cut the strings their own comments promise whole.

* `resolve_hosts`:738-748 — comment: "EVERY SOURCE WHOSE PROBE COULD NOT BE COMPLETED, BY NAME.
  Uncapped". Print: `%-44s % _src[:44]`. Measured on the live 215-source roll: 11 names exceed 44
  chars and are cut mid-word ("Kobold Press (Midgard Heroes Handbook, Midga"). **No two roll
  sources currently collide on their first 44 characters**, so nothing is ambiguous today; stated
  as such in the order rather than overclaimed.
* `_show`:1647-1652 — comment: "Listed in full and not truncated ... a cap on a diagnostic hides
  exactly the tail you opened it to read". Print: `{t[:60]} -- {why[:80]}`. The list is uncapped;
  each row is not. Called `page_looks_real` directly: its three refusal reasons are 95, 97 and 124
  characters and **all three are cut mid-sentence at 80**. Only the 50-char "no wiki markup" one
  survives. The half that is cut is the half explaining why the distinction matters.
* `ev['feats'][:6]` / `ev['quantities'][:4]` in the same function are unmarked previews. Defensible
  — the true counts print on the line above — but they are the caps the 1647 comment points at, so
  the order asks for a "6 of N" marker if they stay.

### Read and judged clean, with reasoning

* `_api_list_all` genuinely follows `continue` to exhaustion; the only stop conditions are a
  repeated token and a mid-walk API failure, both counted into `_CAP_BOUND` including the
  first-request-failed case. `discover()`'s `extra` refuses a numeric value loudly. `resolve_title`
  asks `srlimit=50` through `_api_list_all` and ranks without cutting. No live cap here.
* `api()`'s outcome stamping covers every return path; `alive_verdict`'s three-way answer and
  `resolve_hosts`'s `known.get(src)` value test (not `src in known`) are both correct as written.
* `_units`' floor/ceiling tallies are per-gate and under `_COUNTS_LOCK`; the `mine`/`by_axis`
  distinction is real, not pedantry, since `evidence_for` runs both over the same page.
* `_unwrap_templates`' `{{{` arm, the superscript-exponent handling in `_QUANTITY`, and the
  `||`/`!!` cell-boundary rule all match their comments; I checked the group numbering
  (`m.group(4)` is the unit) rather than assuming.
* `roll()`'s `jobs[:limit]` is the CLI `--limit`, opt-in and off by default.

### Not re-filed (already open, but the citation has drifted)

Open order `SWEEP34_FINDING` (MINOR, OWNER) cites `src/feats.py:542,550,876,1026` for four
callerless functions. Re-grepped the whole tree: `resolve_title`, `_page_exists` and
`axis_evidence` still have zero callers anywhere (`remine` is documented as deliberately
callerless). **The line numbers in that order have drifted** — they are now 895, 887, 1263 and
1445. Not re-filed under a new `where`, because `order_id` hashes `code + where` and that would
open a duplicate rather than correct the original; flagged here for whoever works the queue.

---

## `chain.py` (683 lines) — read in full

### FILED — `CHAIN_MAIN_TOP14_STRENGTHS_IS_AN_UNLABELLED_PREVIEW` (MINOR, LOCAL, `01df9304f918`)

`main()` prints the strongest entrants as `[...][:14]` with no total and no "this is a preview",
thirty lines below the *other* preview in the same function that was explicitly corrected to carry
both ("Commonest 8 (all of them are in CHAIN.json)"). It is a genuine preview — `write_result`
persists `names` and `strengths` whole — so the fault is only that a reader cannot tell, which is
exactly what the earlier comment argues is worth fixing. Same block also cuts `n[:50]` (node names
carry ID.node's continuity/epoch suffixes and are longer than bare names) and the fit's refusal
text at `[:240]`.

### FILED — `CHAIN_MUTUAL_EPOCH_PROBE_READS_ONLY_THE_FIRST_SENTENCE` (MINOR, RUN, `0d71cb2b08df`)

`adjudicate_mutuals` dates each side of a mutual pair from `prov[...][0]` only, but `prov[e]` holds
one row per recorded win. The docstring's "each mutual pair's two sentences are dated" is true only
for single-win edges. **Latent, not live, and filed as such**: measured against `data/CHAIN.json`
today — 25 edges (22 with one win, 3 with two), exactly one mutual pair, both sides n=1. Reachable,
not currently firing.

### Read and judged clean

`write_result`'s `most_common()` is uncapped; `harvest()`'s three-way root classification
(`live`/`gone`/`unavailable`) and its `_held_root` slash-normalisation are sound; the dedup key is
the full sentence, and the unmatched key is the full name (both truncations already removed and
the reasoning is correct); `unanswered` is set unconditionally so a zero is a measurement;
`extract`'s `local_unmatched` merge under the lock is right, and the model-supplied `index` is
bounds-checked before use. The `except Exception: idx = {}` at 212 is genuinely safe — the index
rebuilds whole and says so.

---

## `weave.py` (546 lines) — read in full — **nothing filed**

Read closely for the cap shapes this module has a history of. Both `pair_weights` and
`surprisal_pair_weights` now append to `shared[p]` uncapped, and the write path's `shared_sample`
carries the whole list. `filtered_index` reads whole descriptions (the `[:400]`/`[:300]` windows
are gone). `components()`'s complete-linkage early exit is a correctness optimisation, not a cap.
The three `--write` verdicts are tracked per file and the out-of-step warning is correct and
specific. `main()` returns 1 on any denial.

Console previews (`multi[:12]`, `[:8]`, `most_common(6)`) all print their totals on the preceding
line, so they are legible as previews; not filed. `pair_weights`, `null_threshold` and
`resonance_graph` have no callers and `idf`/`N` are unpacked-and-unused in `main()` — all three
already carry "reported, not deleted" comments citing order `25ec11447b4c` / sweep33 batch08, so
they are known and deliberately standing.

---

## `reference.py` (448 lines) — read in full

### FILED — `REFERENCE_CALIBRATION_MISS_NEVER_REACHES_THE_EXIT_CODE` (MAJOR, RUN, `d049dbbfed6e`)

The module's stated purpose is three hand-built worksheets that must land inside intervals they
were not fitted to. `main()` computes `inside`, prints it, prints "OUTSIDE - investigate" per
entity — and then both `return` statements are `return 0 if landed else 1`, where `landed` is only
the verdict on writing `REFERENCE_ASSAYS.json`. `inside` never reaches rc.

That is the only channel out: `allsweep.py:172` registers
`Verifier("calibration assays", ["reference.py"], RC_BROKEN)`, and its own comment at line 171
already notes the rc means "a denied write, not a finding".

Reproduced. Live and unmodified: **3/3 inside, rc 0** — the calibration genuinely holds today.
With Goku's published charter moved to `("M7", 2.00, 0.10)` in scratch:

```
CHARTER  M7.00 ± 0.10   delta 5.44   OUTSIDE - investigate
2/3 reconstructions land inside the charter's published interval
main() returned rc = 0
```

A 5.44-band miss on the library's own benchmark exits clean. A check that cannot fail looks
exactly like a check that passed.

### Read and judged clean

`shelfmark()`'s RUNGS clamp is a real guard with a real failure mode behind it; the `--compare`
path's `(host, entity)` indexing fixes a real key-shape bug and its fallback is honest; the
"pre-dates b03f2ab9951a" branch correctly refuses to read a missing `scores` key as a zero. The
unused `name` parameter on `compute`/`citation`/`card` is cosmetic; not filed.

---

## `backfill.py` (338 lines) — read in full

Three findings, all MINOR/LOCAL.

* **FILED — `BACKFILL_SLEEPS_02S_PER_PAGE_WITH_NO_REQUEST_IN_FLIGHT`** (`23039b81bec0`).
  `time.sleep(0.2)` sits inside `for title, wt in pages.items()`, i.e. *after* `F.fetch` has
  already made all 40 requests for the batch. It delays a dict append. 8.0s dead per 40-page
  batch; the module's own docstring names DC's 6,000+ roster, which is **20 minutes** of sleeping
  at nothing. `feats._throttle` is the actual rate limiter and already paces the fetches.
* **FILED — `BACKFILL_ALL_DISCARDS_WRITE_DENIED_AND_ERROR_TALLIES`** (`f57f145468f7`).
  `backfill_source` returns `write_denied`, `size_lookup_failed` and `entries_now`; `main()`'s
  `--all` loop reads only `roster`/`absent`/`added` and returns 0 unconditionally. A run in which
  every catalogue write was locked prints "added 0" everywhere — the same output as a run with
  nothing to add, which is the confusion the module is written against. The per-source
  `except Exception` containment is correct under Hard Rule -1 and should stay; it is the *tally*
  that is missing, and a denied write is infrastructure, not a per-source fiction fault.
* **FILED — `BACKFILL_COMMENTS_COLLAPSED_ONTO_SINGLE_LINES`** (`9b0e13d89de4`). Lines 179 (336
  cols), 197 (189), 199 (**780**), 217 (226) and 234 (167) are multi-line comments flattened into
  one line with the interior `# ` markers left embedded mid-sentence. Line 199 is the paragraph
  arguing why `--cap` is *not* a Hard Rule 0 violation — the single most important thing in the
  file to be able to read. No other module in this batch has more than one line over 100 columns.

Judged clean: `roster()`'s subcategory walk is unconditional (the `< 40` gate is gone),
`RosterIncomplete` is raised rather than returned, `t in sizes` is the correct sort key direction
(the run #36 inversion is fixed), `absent` is the pre-cap count on both paths, and `lead()`'s
prose-block walk is the right fix for the template-residue problem. `--cap` is opt-in, off by
default, and recomputed fresh each run — not a Hard Rule 0 cap, and the (unreadable) comment at
199 makes that case correctly.

---

## `resonance.py` (298 lines) — read in full — **nothing filed**

The Gauss-Seidel switch is correct: I checked the update rule against the least-squares normal
equations (∂/∂θ_a of Σ(F_ab − (θ_a − θ_b))² = 0 ⇒ θ_a = mean over neighbours of (θ_b + F_ab)),
and the in-place update, the mean-zero gauge fix, and the max-per-node-shift convergence test
(taken *after* the gauge fix, so the fix cannot register as movement) all do what the docstring
says. All three zero-signal cases — empty `nodes`, unconverged, `total == 0` — return `eta: None`
with distinguishing flags rather than sharing an answer with a perfect ladder. `_isolated` is
documented as a construction-bug guard that has never fired and is kept deliberately.

`incomparability_rate`'s unmeasured/tied/incomparable split is correct and `examples` is uncapped.
`resonance_strength`'s default path `data/SHARED_STAGE_GRAPH.json` **does exist** (726 KB, written
by `cosmology_graph.py`) — I checked, because `weave.py` writes the `_IDF` variant and the two
names invite a stale-path finding. Not a defect.

The module's "no production caller" state is fully and accurately documented in its own docstring
and is already an open order; not re-filed.

---

## `recover_folder_records.py` (243 lines) — read in full

### FILED — `RECOVER_FOLDER_RECORDS_MAIN_HAS_NO_EXIT_CODE` (MINOR, LOCAL, `aff81a1f1029`)

`main()` has no `return` statement anywhere and the entry point is bare `main()`, not
`sys.exit(main())`. So the file always exits 0 — including when every per-record write and the
roll write were both denied. This is striking given how carefully the same function gates those
two writes and explains, at length, why dropping the verdict is unrecoverable. Every other module
in this batch uses `sys.exit(main())`.

Folded into the same order: `skipped_no_map` and `skipped_no_items` are printed as bare counts
while `skipped_populated` is printed by name. Order `37d3d588847a` separated those two buckets
precisely because they prescribe different work; a count names neither the sources nor the remedy.

Judged clean: the `mapped is None` vs empty-list distinction, `record_path`'s prefer-the-existing-
file behaviour, the "unreadable counts as populated" direction, and the roll-is-a-snapshot guard
are all correct and correctly argued.

---

## `scale_theories.py` (148 lines) — read in full

### FILED — `SCALE_THEORIES_SURVIVOR_DECIDED_BY_A_PROSE_PREFIX` (INFO, LOCAL, `e7dc70db782b`)

`surviving_theory()` selects on `t["falsified_by"].startswith("Nothing attested")`. Any rewording
of T3's prose makes it return `{}` — "no theory survives" — silently, and nothing asserts that
exactly one should. Filed at INFO only because the module has no production caller at all (already
recorded by open order `SWEEP34_FINDING`), so nothing today reads the wrong answer; it becomes real
the moment that order is closed by wiring the module in.

The physics and arithmetic themselves read correctly. `bulk_export_beta`'s guard, `growth_strike`'s
v = size/time and `penetration_pressure`'s impulse form all match their docstrings; `G_NEWTON` is
consistent with `descending_ladder.py`'s copy, which that file's own comment cross-references.

---

## `module_index.py` (116 lines) — read in full — **nothing filed**

The docstring's "NO COUNT IS WRITTEN DOWN HERE" argument is honoured — the count is computed live
from `glob`. The tmp name carries pid and thread; `replace_retry`'s verdict is checked and returns
1. `first_line`'s `(unparseable)` fallback notes to the silence ledger rather than vanishing.

One judgement call I decided *against* filing: a stale `GROUPS` entry (a name no longer in `src/`)
prints to stderr, notes to silence, and then `main()` still returns 0. Arguable, but the page is a
navigation aid rather than a safety, the message is loud and names the stale entries, and the
generated page is still correct — I could not talk myself into calling a non-zero exit the right
answer for a documentation generator. Recorded here so the decision is visible rather than absent.

---

## Summary

| module | lines | filed |
|---|---:|---|
| `feats.py` | 1,735 | 1 MAJOR, 1 MINOR |
| `chain.py` | 683 | 2 MINOR |
| `weave.py` | 546 | — clean |
| `reference.py` | 448 | 1 MAJOR |
| `backfill.py` | 338 | 3 MINOR |
| `resonance.py` | 298 | — clean |
| `recover_folder_records.py` | 243 | 1 MINOR |
| `scale_theories.py` | 148 | 1 INFO |
| `module_index.py` | 116 | — clean |
| **total** | **4,555** | **10 orders** (2 MAJOR, 7 MINOR, 1 INFO) |
