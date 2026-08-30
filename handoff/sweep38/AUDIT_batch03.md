# SWEEP 38 — AUDIT, batch 03

Agent: `sweep38-batch03`. Modules assigned: `pipeline.py`, `onomast.py`, `sevenfold.py`,
`genre.py`, `wh40k.py`, `descending_ladder.py`, `catalog.py` (4,479 lines).
**All seven read in full.** Nothing under `src/` was edited.

Python used for every reproduction: `C:/Users/imarl/miniconda3/python.exe`, `PYTHONIOENCODING=utf-8`.
Scratch: `…/scratchpad/sweep38/batch03/`.

---

## pipeline.py (2,545 lines) — READ IN FULL

Two findings, both **reproduced**, both the same shape and both contradicted by this module's
own written doctrine a few hundred lines away.

### F1 (MAJOR, RUN) — `phase_write` marks phase 8 DONE on an unreadable COVERAGE.json

`pipeline.py:2182-2200`. The COVERAGE.json read is one `except Exception: rows = []`. With
`rows == []`, `ready` is empty, and the phase logs

> `nothing is ready, and that is a correct outcome rather than a failure:`
> `the library does not write about entities nobody has read.`

then calls `mark_done(st, "write")` and returns True. The done-key is permanent, so no later
run redoes phase 8. The phase publishes a *positive verdict about the corpus* on the strength
of a file it could not read.

Reproduced (`scratchpad/sweep38/batch03/repro_phase_write.py`, no live state touched — HERE
redirected at a sandbox, `save_state`/`log`/`update_handoff` stubbed):

```
CASE A (COVERAGE.json absent)                 -> returned True, done = {"write": ["all"]}
CASE B (COVERAGE.json truncated mid-write)    -> returned True, done = {"write": ["all"]}
CONTRAST phase_history, corrupt TIERS.json    -> returned False, done = {}
        "TIERS.json EXISTS BUT WILL NOT PARSE (JSONDecodeError) -- ... Leaving phase 6 open"
```

`phase_history` (l.1948-1966) and `phase_shelve` (l.2054-2075, 2093-2111) both split
`FileNotFoundError` from a parse error and both refuse. `phase_write` is the one phase that
did not get the ruling. CLAUDE.md Hard Rule -1 names this case by name: *"an unreadable config,
a missing COVERAGE.json … all refuse."*

### F2 (MAJOR, RUN) — `phase_cosmology` writes an EMPTY SHELFMARKS.json over a good one, then marks itself done

`pipeline.py:1905-1918`. `seeds = json.load(open(data/WORLDSEEDS.json))` under one
`except Exception: seeds = {}`; `marks` is then `{}` and `land_json(data/SHELFMARKS.json, marks)`
writes it **unconditionally**, returning True. `gate_done(st, "cosmology", landed)` sees all
True and closes phase 5.

Measured on the live corpus: SHELFMARKS.json holds 1,016 world shelfmarks, and all 1,016
shelfmarks currently in SHELVES.json come from it. Phase 7 then reads the emptied file, parses
it fine, shelves every entry with `shelfmark: None`, and marks itself done too — because
phase 7's corrupt-input guard only fires when a file *will not parse*, and `{}` parses.

Same absent-vs-corrupt conflation as F1, in a function that sits 40 lines above the phase-6
comment arguing at length that the two are different answers.

### Read and judged sound (no order filed)

* `clean_band` / `ceiling_band` (l.143-162) — the strict/lax asymmetry is right and the
  `fullmatch` reasoning holds.
* `valid_scale_note` and the `_ACT`/`_OBJECT`/`_PATIENT`/`_REPUTATION` conjunction (l.1261-1380).
* `write_record` / `write_record_catalogue` / `_merge_top_keys` / `MERGED_ENTRY_FIELDS` —
  the two-writer contract, its refusal paths, and the stamp/`verify_record_provenance` detector.
* `mark_done`, `gate_done`, `phases_never_closed`, `_chain_landed`, `land_json`, `_landed`,
  `save_state` — every verdict is read by its caller.
* `update_handoff`'s handoff write is now gated (l.1755-1761); `_metric`'s deliberately-ungated
  write is argued correctly.
* `main()`'s `--phase` range validation, the pointer-past-end branch, and the
  fail-closed `escalation` import.
* `_kind` at l.1892-1896 correctly absorbs both shapes this module and `grounding.py` write into
  GROUNDINGS.json; `kinds.most_common(6)` cannot truncate — the taxonomy is 5 positive types
  plus `ungrounded`, measured live as exactly 6 kinds.
* `_SCALE_PATTERNS` / `_SCALE_EVIDENCE` (l.1305-1312) are dead, and the comment says so and says
  why they are kept. Correct as written; not filed.

### F3 (MINOR, LOCAL) — a stale hand-maintained row in the owner-facing status file

`pipeline.py:1706` publishes into `handoff/RUN_STATUS.md`:
`| verify_math.py | 237 independent checks across 17 sections; recomputes, never re-calls |`.
`src/verify_math.py` today prints numbered sections 1 through 36 and carries ~967 `check(`
call sites. The `tells.py` row's 138 in the same table is still exact (60+31+15+32), which is
what makes the stale one hard to spot. The comment 45 lines above (l.1656-1658) argues the
phase ladder must be derived rather than hand-written precisely because *"a stale table here is
published continuously"* — the table below it is still hand-written.

### Already filed, re-verified as still true (not re-filed)

`2f248e854b58` (the merge fold cannot clear a rejected field), `5c8a7bc883e7` (`synthesis_blocks`'
`or`), `f2b06f8c9476` (`synthesis_prompt`'s `fl[:3]`).

---

## onomast.py (523 lines) — READ IN FULL

### F4 (MAJOR, RUN) — a corrupt ONOMASTICON.json silently empties the append-only record

`onomast.py:337-347`. `load_onomasticon()` answers a parse error with `{}` — the same answer it
gives a missing file — after a `silence.note` that stops nothing. `name_worlds()` then carries
nothing forward, `taken` is unseeded, and **both** writers of the file (`main()` at l.513 and
`pipeline.phase_weave` at l.2300) write that shortened return value straight back over it.

Reproduced (`scratchpad/sweep38/batch03/repro_onomast.py`, `O.OUT` pointed at scratch files):

```
run 1 (fresh)        : {'cid_a': 'Veneiliel', 'cid_b': 'Venamwen'}
run 2 healthy prior  : {'cid_a': ('Veneiliel', False), 'cid_b': ('Venamwen', True)}
run 2 corrupt prior  : {}                      <-- the whole onomasticon
designations lost    : ['cid_a', 'cid_b']
```

`cid_a` is still in `resolved` and merely no longer collides, so it is not in `out`; the prior
that would have carried it is unreadable, so it is not in `merged` either. One torn read empties
the file. That is the exact reservation order `9309a040f208` exists for, and the docstring at
l.362-372 ("A safety that holds for one cycle and then forgets is worse than none, because it
reads as protection") applies verbatim to its own loader.

### F5 (MINOR, LOCAL) — `main()` reports a denied write and exits 0

`onomast.py:512-519`. `if silence.write_json(...)` … `else: print("WRITE DENIED …")` and then
`return 0`, with no `silence.note`. Every sibling fixed in the run #36 discarded-verdict sweep
returns 1 and notes: `genre.py:327-331`, `sevenfold.py:403-415`, `wh40k.py:277-282`. The
sevenfold comment states the rule this site breaks — *"A line only a person reads is not a
verdict; it is a hope that a person was reading."*

### Read and judged sound

`is_carried`, the syllabary, `_stream`, `well_formed`, `coin_name`,
`coin_well_formed`'s widened deterministic salt walk and its loud exhaustion note, `is_retired`,
the standing-vs-retired split in `merged`, and `main()`'s announced `[:4]` / `[:9]` with their
"… and N more" lines.

Already filed, still true, **not re-filed**: `ae25c89f0179` / `5d8533bc1ed6` — `register_for`'s
genre+feature voting is unreachable because `name_worlds` l.426 calls
`register_for(v["continuity_group"])` with nothing else. `verify_math.py:6756` records that this
is deliberately parked at OWNER as a cross-module design decision.

---

## sevenfold.py (421 lines) — READ IN FULL, nothing found

Checked in detail: `affinity_order`'s greedy walk; `_even_cuts`' clamp arithmetic (verified
by hand for n=7,k=7 → gap indices 0..5, seven singleton chunks, and for the general
`min(max(round(step*j),1), n-1)-1` bound of `[0, n-2]`); the two-rule `seams()` (window +
median ceiling) against the three measured alternatives in its comment; `split`'s recursion and
the slot-0 padding; the deliberately-unequal `zip(TIERS, c)`; `shelfmark`'s stop-where-the-
coordinate-stops; `build`'s two-stage shelving and the `UNSHELVED` count printed to stderr;
`main`'s members-per-branch table, its gated write and its rc=1.

The `ok = "OK" if hi <= SPAN else "OVER SPAN"` display at l.374 is a guarantee, not a check —
and its own comment says so, so it is not filed. The `[:8]` sample-shelfmark lists at l.389/394
are labelled "sample" and are the only truncations here.

## genre.py (337 lines) — READ IN FULL, nothing found

`classify_text`'s `top=None`, `classify_source`'s loud refusal of `cap`, the whole-field
confidence denominator, `_project_pipeline`'s interpreter diagnosis, the uncapped
low-confidence roster, and the gated `--write` with rc=1 all check out. Cross-checked that
every `register` named in `GENRES` (classical, liquid, guttural, sibilant, compact, long) is a
real key in `onomast.REGISTERS` — all six are.

## catalog.py (138 lines) — READ IN FULL, nothing found

`cmd_stats`' missing-source roster is uncapped and carries the Hard-Rule-0 note explaining why.
`cmd_search` prints every hit. `load_catalog` returns `{}` only for a genuinely absent
catalog.json; a corrupt one still raises, which is the right direction here.
Order `1cdc2f8cd2f3` cites `catalog.py missing[:30]` — that slice is **gone** from the current
file; the order stands only as the general owner question about announced console truncation.

## wh40k.py (289 lines) — READ IN FULL

### F6 (MINOR, LOCAL) — `--full` cuts the citation it exists to show

`wh40k.py:263`: `print("   %-15s%5.1f  %s" % (ax, d["score"], d["cited"][:56]))`. Measured over
the live ROSTER: **47 of 55 axis citations exceed 56 characters** and are cut mid-quotation with
no ellipsis and no marker. Longest is 234 characters. Example (Nurgle / ruin):

```
full   : Plague as a method: 'a choking plague to wipe out an Ork infestation on Hurax, a
         planet that Nurgle coveted' -- a world cleared as a favour to a lieutenant
printed: Plague as a method: 'a choking plague to wipe out an Ork
```

`--full` is the only view that shows the evidence behind a score, so this is a truncation of the
evidence itself. Same shape in the two sibling modules, at three different widths:
`halo.py:192` `[:54]`, `zfighters.py:482` `[:60]`.

Everything else here is sound: the control-character self-check, `_provenance`'s honest
`unattributed` default, `compute()`'s per-axis marks, the `A.WEIGHTS`-driven `--full` loop
(verified all 11 weighted axes are present on all five ROSTER entries, so it cannot KeyError),
and the gated write with rc=1. Order `82fc93f056d4` (the curatorial provenance pass) is still
correctly open.

## descending_ladder.py (226 lines) — READ IN FULL

### Q1 (QUESTION → OWNER, MINOR) — the binding-energy column is discontinuous and non-monotonic

Not filed as a defect; two readings and I cannot settle it from the file. The header declares
*"the characteristic length is the rung edge for Reach; the binding energy is the rung edge for
Ruin."* The length column is strictly monotonic. The binding column is not:

```
rung   0  Cn 1e26   -1 Rg 1e22   -2 Ct 1e17   -3 St 1e10   -4 So 1e8   -5 Og 1e5
rung  -6  Cl 1e-11  -7 Or 1e-14  -8 Mc 1e-17  -9 Ml 8e-19  -10 At 2.2e-18
rung -11  Nu 1.3e-12  -12 Nc 1.5e-10  -13 Qk 1.6e-10  -14 Pk 1.956e9
```

Two things stand out. (a) Organic → Cellular drops **sixteen orders of magnitude** across three
orders of length, where every neighbouring step is 1e2–1e3. (b) Below rung -9 the column turns
around and rises, so Ruin band edges do not order by rung.

Reading one: this is honest physics — a cell really is easier to disrupt than a nucleus — and
a Ruin axis that is U-shaped in scale is a true statement about the world.
Reading two: a band edge that is not monotonic in the rung index cannot order anything, and the
Og→Cl step is a units/regime slip (mechanical disruption energy above, molecular binding below)
rather than a finding.

Everything else read clean: the CODATA constants (PLANCK_ENERGY verified as
PLANCK_MASS·c² = 1.956e9 J), the hoisted `NUCLEAR_DENSITY` and `G_NEWTON` with their
one-constant-two-values history, `rung_for_length`'s bounded-at-both-ends domain and its
`(None, None)` refusals, `compton_confinement_energy` (the docstring's "70 kg to 1e-10 m costs
~1e-51 J" recomputes to 1.98e-51 J), `shrink_report`'s reported-not-enforced `is_descent`, and
`transgression_bits`' 2026-08-20 correction from uncertainty to degeneracy.

Order `66f96febdb3a` (this module has no consumers anywhere in `src/`) is still true and is not
re-filed.

---

## Orders filed

| id | code | sev | handler |
|---|---|---|---|
| `3aaeb798551e` | PIPELINE_PHASE8_MARKS_DONE_ON_UNREADABLE_COVERAGE | MAJOR | RUN |
| `80204a4f87f8` | PIPELINE_PHASE5_EMPTY_SHELFMARKS_OVER_A_GOOD_FILE | MAJOR | RUN |
| `549069e9c298` | ONOMASTICON_CORRUPT_PRIOR_EMPTIES_THE_APPEND_ONLY_RECORD | MAJOR | RUN |
| `dc5c92aad5c1` | ONOMAST_MAIN_REPORTS_A_DENIED_WRITE_AND_EXITS_ZERO | MINOR | LOCAL |
| `2a69b226863d` | ASSAY_FULL_VIEW_TRUNCATES_THE_CITATION_IT_EXISTS_TO_SHOW | MINOR | LOCAL |
| `4c4c8c24e34c` | RUN_STATUS_HAND_MAINTAINED_TABLE_IS_STALE_ON_VERIFY_MATH | MINOR | LOCAL |
| `38c51153243c` | DESCENDING_LADDER_BINDING_ENERGY_NOT_MONOTONIC_IN_RUNG (a QUESTION) | MINOR | OWNER |

`2a69b226863d` reaches outside this batch on purpose: the identical slice is at `halo.py:192`
and `zfighters.py:482`, and fixing one of three is the shape those modules keep being cited for.

## Coverage

`sweep_plan.record('run38', [pipeline.py, onomast.py, sevenfold.py, genre.py, wh40k.py,
descending_ladder.py, catalog.py], batch=3)` returned without error; all seven now carry
`run38`. All seven were read in full — no module was sampled, grepped or skimmed.
