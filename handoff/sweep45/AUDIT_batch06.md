# sweep45 — batch 06

**Modules:** `cascade_bridge.py` (2,053) · `chain.py` (837) · `build_terminal.py` (654) ·
`weave_index.py` (521) · `cleanup.py` (413) · `navtree.py` (335) · `resonance.py` (298) ·
`descending_ladder.py` (226). **5,337 lines, all of them read.** No sampling, no skimming;
`weave_index.py` was read through a persisted tool-output file rather than inline, which is the
same bytes by a different route.

Read-and-report only. No source file in the tree was modified. The standing DRILL_BREACH halt was
left alone and none of `drill.py` / `verify_math.py` / `allsweep.py` / `publish.py` / `mutate.py`
was run.

---

## Filed

### 1. `91cbbd5e4d24` — LOCAL / MAJOR — `cleanup.clean_description` is not idempotent

`_MARKUP` rule 5, `re.compile(r"\s*\?\s*(?=\))")` with the `_ruby_question_mark` replacement
(`cleanup.py:138`, `:63-96`), only requires a closing paren and allows zero whitespace on both
sides. After the pass has deleted the question mark nearest the `)`, the next question mark
becomes the one nearest the `)`, and the rule fires again on the following pass.
`_ruby_question_mark`'s non-ASCII test does not stop it: the test scans back to the enclosing `(`
and answers on the whole parenthetical, which still holds the same non-ASCII characters it did the
first time.

**Measured over the whole corpus** — 282,749 non-empty descriptions across all 216 files in
`data/records/`, no sampling. 184,965 change under one pass; exactly one is non-idempotent today:

| | |
|---|---|
| file / entry | `all-final-fantasy.json` — *Pandora's Box* |
| raw | `... ( なんとか？？？ , Nantoka??? ? , lit. Something??? ) is a recurring ability ...` |
| `clean(raw)` | `... lit. Something??)` |
| `clean(clean(raw))` | `... lit. Something?)` |

A third pass gives `Something)`. The raw form is still on disk, so no `--apply` run has reached it
yet — the loss is prospective, not already taken.

The measurement was made by copying cleanup's regex surface verbatim into a scratchpad script. No
project module was imported and nothing in the tree was written.

**Why it is more than one entry.** `pipeline._is_cleaned_twin` (`pipeline.py:693-706`) decides
whether the catalogue writer may keep the disk's cleaned description or must let a fresh raw cast
overwrite it, and its entire test is `cleanup.clean_description(sv) == dv`. That identity holds
only while `clean()` is idempotent. After a **second** `--apply`, the disk holds `clean(clean(raw))`
while the fresh cast still emits `raw`, the twin test answers False, and `write_record_catalogue`
writes the raw description back over the cleaned one — the exact regression order `0a45c595655b`
added that gate to prevent. The state then flaps between the two forms, one `--apply` and one
catalogue pass at a time, and cleanup's own report lists the entry under "descriptions with markup
stripped" on every run for ever, which is a standing false positive in the report a person reads to
decide the pass is finished.

Same family as the two faults `_ruby_question_mark` and `_ruby_parenthetical` were already repaired
for (55 English question marks eaten, 3 authored English parentheticals deleted): a destructive
pass that does not fail and hands back a slightly smaller universe wearing the shape of the real
one. Both of those repairs were verified with single-pass tests, which is why this class survived
them; the order asks for an idempotency assertion alongside whichever regex fix is chosen.

### 2. `0ced896514e7` — LOCAL / MAJOR — `chain.main()` drops the edges *and* the transport tally when the fit refuses

`chain.fit` (`chain.py:740-745`) returns `{"error": "too few edges to fit"}` below three distinct
edges. The two documented callers of `write_result` then disagree about what that means:

* `pipeline.phase_chain` (`pipeline.py:2242-2251`) logs `no fit: ... -- the edges stand as the
  result` and calls `write_result` anyway, with the comment *"Refusing is the correct answer, and
  it is a RESULT -- the edges are kept and the graph is the finding."*
* `chain.main()` (`chain.py:788-790`) prints the error and returns 1. No write at all.

The same argument is already written into `main()` forty lines lower for the strengths-is-None case
(`chain.py:801-813`: *"The edge list is still the finding, so it is written either way"*), so the
module holds both spellings of one rule.

What is lost is not only the edges. `write_result`'s `unanswered` field exists precisely so a
starved pass says so on disk (`chain.py:132-138`, *"a pass that lost a third of its chunks to HTTP
503 wrote a third-smaller contest graph and said nothing"*), it is carried out of `extract()`
through `_LAST_EXTRACT`, and `write_result` is the only thing that persists it. A pass in which the
model pool is entirely down yields few or no usable edges — which *is* the `len(wins) < 3`
condition — so on a total transport failure the tally built to record transport failure is never
written at all. The field is most valuable on the one path that discards it. `fit_error`
(`chain.py:117`) is likewise unreachable from `main()`, because `main()` returns before writing on
the only path that sets it.

`data/CHAIN.json` carries no timestamp and no corpus size, so a reader has nothing on disk to tell a
refused run from a successful one. (The live file is dated 2026-08-22, holds 25 edges and still
carries the pre-unification key set — no `fit_error`, `unmatched`, `unmatched_distinct`,
`unmatched_mentions` or `unanswered`. That staleness is separately known and is **not** what the
order is about.)

Open order `e8466cd6ed14` asks for `main()` to gate its rc on whether the write landed. The two
changes touch the same three lines and should be worked together.

### 3. `2d6252e03485` — LOCAL / MINOR — `transgression_bits` prices a non-physical trajectory at beta 0.0

`descending_ladder.py:214-217` returns `0.0` when `density_at_scale` returns `None`, i.e. for
`to_m <= 0`. A non-positive **mass** is not screened at all: `mass_kg = 0` gives `rho = 0.0`, which
clears the saturation test, and `schwarzschild_radius(0) = 0.0`, which no positive `to_m` is below —
so beta is `0.0` again by a second route. The two neighbours in the same file answer the same
arguments with `None` (`compton_confinement_energy` guards both, `:138-141`; `density_at_scale`
guards the size, `:144-148`). Zero is a positive claim here, not an absence: per X.2 §4, beta = 0
means the charter files the event as Vector or Praxis rather than hax, and it is byte-identical to
the answer for a lawful mass-shedding shrink.

Same family as open order `cc52ba746849` (`shrink_report:176`), but a different function that a fix
to `shrink_report` will not reach.

---

## Already open — corroborated, not refiled

* **`d04244f63e71`** — `build_terminal.py:245,295,351,356`, unmarked `.slice(0,24)` / `.slice(0,22)`
  on the nucleus title, shell-2 ring labels and world labels, beside the correctly marked
  `n.slice(0,17)+"…"` at `:326`. Confirmed at all four sites, including that `:351` and `:356`
  repeat the identical slice expression in the measurement array and in the drawn label.
* **`fe99e57e1993`** — the gathered Hard Rule 0 order names `cleanup.py:231,233,261`. Those sites
  are now `cleanup.py:301`, `d[:46]` / `cd[:46]` in the `desc_fixed` row, and the two ceiling cuts
  it names are gone. The `d[:46]`/`cd[:46]` pair survives, still under the comment at `:342-350`
  claiming *"The per-name character cuts in the same statements go with them."* Still open, still
  true, line numbers have moved.
* **`e8466cd6ed14`** — `chain.main()` returning 0 over a denied `write_result`. Both call sites
  (`chain.py:812`, `:831`) still discard the return; `write_result`'s `return out` at `:153` is
  still unconditional. See filed order 2 above, which is adjacent.
* **`423e35500033`** — `adjudicate_mutuals.side_epoch`'s `for row in (prov.get(e) or [{}])`.
  Confirmed at `chain.py:668`: a side with no provenance row iterates one empty dict and, if
  `epoch_of("")` does not raise, is recorded `probed=True` and undated, i.e. as a genuine
  disagreement. Unreachable from `main()`, where `prov` always covers every edge.
* **`cc52ba746849`**, **`66f96febdb3a`**, **`8dae7cda3e2e`**, **`38c51153243c`** — the four standing
  `descending_ladder.py` orders. All still accurate; the no-consumer claim re-verified this pass
  (only `drill.py`, `liveness.py`, `secondopinion.py` reference it, plus one comment in
  `tempus.py:46`).
* **`ed6e66c0c12d`**, **`18f7673b77ce`**, **`c3eb0a80bb8a`** — the `cleanup.py` ceiling and
  two-exclusions orders. The code now carries the `prefix-ambiguous` split and the separate `mech`
  roster the remedies asked for; the orders read as closed-in-code but are still open in the queue.
* **`5f1dc97d5216`**, **`dae0f99306db`**, **`8f50f37255b5`**, **`e0f9da6e9466`** — the standing
  `weave_index.py` questions. Nothing in this read disputes any of them.

## Checked and judged deliberate — not filed

* **`resonance.hodge_decompose`'s `_isolated` guard** (`:157-163`). Genuinely cannot fire — `nodes`
  is built from the edge keys and the adjacency loop appends for both endpoints of every edge — but
  it is documented as such under order `9803b72711b3`, it *raises* rather than passing quietly, and
  the alternative is an unnamed `ZeroDivisionError` inside the sweep. Kept deliberately, correctly.
* **`resonance.resonance_strength` returning `shared_sample` under the key `shared`** (`:295`).
  Looked like an unmarked truncation. It is not: `pipeline.py:2799` and `weave.py:530` both write
  that key as the **whole** list, with the key name kept only because `resonance.py:295` reads it
  (ruled 2026-08-24). Verified in the live `data/SHARED_STAGE_GRAPH.json` — samples run up to 235
  entries and are not capped.
* **The eight `if pinned:` guards in `cascade_bridge._ask_call`** below `:1465`. None of them can be
  False; the file says so itself in the invariant note under order `8b0338b019ce` and asks that they
  be read as documentation of which branches touch the pinned bucket. Agreed.
* **`weave_index.build()`'s "main() is its only caller anywhere in the tree (grepped)"** — re-grepped
  across all of `src/` including `src/deprecated/`. True.
* **`chain.write_result`'s "THE ONE WRITER for data/CHAIN.json"** — re-grepped. True; `drill.py`
  points a stub at a temp directory and does not write the real path.
* **`navtree.py`** — nothing filed. All three `except Exception:` handlers note by symbol and
  subject rather than by line; both writes go through `silence.write_json` and are gated; the audit
  record and the tree write both reach the exit code; the two hash-order tie-breaks are explicit.
  The one thing worth stating: no world in the live `data/NAVTREE.json` is missing its seed or
  feature metadata (1,569 of 1,569 carry both), so the `seeds.get(desig, {})` fallback at `:115` is
  not silently degrading anything today.
* **`cascade_bridge.py`** — no new order. Every `except Exception:` records through
  `silence.note`; `record_unrecognised` and `provider_error` are compare-and-swap and read-only
  respectively; the reservation is released from a `finally` that opens at the reserve; the widen
  path names its bucket. The repeated `[:300]` cuts on provider error text are real unmarked cuts,
  but they are consistent, load-bearing for the ledger's de-duplication key, and reach the
  persisted row rather than a roster — I judged that a policy question for the owner rather than a
  defect to file behind the three orders already open against this file
  (`2239a87c57f5`, `af47010df391`, `d3acbb793ef2`, `9fb8a6b10c1f`).
