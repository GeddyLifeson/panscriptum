# SWEEP 37 — BATCH 10 AUDIT

Agent: sweep37-batch10. Date: 2026-08-28.
Read IN FULL, every line, no skimming:

| module | lines |
|---|---|
| `src/mutate.py` | 1218 |
| `src/wiki_source.py` | 675 |
| `src/custodes.py` | 547 |
| `src/address_space.py` | 464 |
| `src/grounding.py` | 334 |
| `src/catalogue_models.py` | 285 |
| `src/tells.py` | 233 |
| `src/snapshot.py` | 210 |
| **total** | **3966** |

Constraints honoured: no source file edited; `prose_enabled`/`step4_enabled` untouched;
`mutate.py` never RUN (PID 16224 was mid-pass) — every mutate claim below is proved by calling
`_mutations()` on a STRING or on an in-memory `ast.parse` of a target, never by a pass; no
process started or stopped; no live network call; no sandbox under the temp tree touched; no
sandbox / ownership / restore / push interlock weakened or test-defeated. Two stray directories
created by the snapshot path-escape demonstration (F10 below) were deleted immediately —
`state/snapshots/AppData/` and `%TEMP%/AppData/` — and their absence re-verified.

Halt status at time of audit: **no halt standing** (`escalation.status()[0] is False`; the last
record is `DRILL_BREACH`, cleared under the self-caused clause).

---

## FINDINGS BY SEVERITY

MAJOR 5 · MINOR 6 · observations (not filed) 6

---

## MAJOR

### F1 — `mutate._mutations`: 55 of 93 comparison-operator sites in the targets generate no mutant (59%)
**Where:** `src/mutate.py:_mutations`, the `swap` table under `isinstance(node, ast.Compare)`.
**What is wrong.** The swap table covers six of the ten `ast.cmpop` types
(`Lt Gt LtE GtE Eq NotEq`) and the branch is additionally gated on `len(node.ops) == 1`.
`In`, `NotIn`, `Is`, `IsNot` and every operator inside a chained comparison therefore produce
**no mutant at all**.

Proved offline by generation only (`_mutations(ast.parse(src), src)`):

```
if x in y:        -> (no mutants generated)
if x not in y:    -> (no mutants generated)
if x is None:     -> (no mutants generated)
if x is not None: -> (no mutants generated)
if a < b < c:     -> (no mutants generated)
```

Counted against the live targets, by walking their own parse trees:

| target | comparison-operator sites | sites producing no mutant |
|---|---|---|
| `assay.py` | 57 | 32 (56%) |
| `prose_gate.py` | 16 | 10 (62%) |
| `escalation.py` | 20 | 13 (65%) |
| **total** | **93** | **55 (59%)** |

Breakdown of the excluded sites: 49 `In`/`NotIn`/`Is`/`IsNot` operators (assay 30, prose_gate 8,
escalation 11) plus the operators inside 3 chained-comparison nodes (one per target).

**Why it matters.** This is the same shape as the hole fixed earlier today
(`line.replace(old,new,1)`, 146 -> 187 mutants), one layer up: the tool that measures coverage
has an unreported coverage hole. `is None` -> `is not None` and `not in` -> `in` are guard
inversions — precisely the defect class the module says comparison operators are "the single
richest source of" — and in `escalation.py`, the module CLAUDE.md calls "the chain of command and
the halt", 13 of 20 operator sites are never attempted. Nothing in `--list` ("N mutant(s)"), in
the run summary, or in the survivor journal names the excluded classes, so a reader has no way to
tell 188 attempted from 93 attemptable. Extending `swap` with `In/NotIn` and `Is/IsNot`, and
handling `len(node.ops) > 1` per-op, is the repair; failing that, the excluded set must be
PRINTED beside the mutant count.
**Confidence:** certain (demonstrated by generation, twice, on strings and on the real targets).

### F2 — `mutate.run()` defaults to NO BASELINE, which scores every mutant KILLED
**Where:** `src/mutate.py:run` (`base=None`) -> `_run_mutation` (`base = {} if base is None else base`)
-> the gate loop `if sig != base.get(gname)`.
**What is wrong.** `run()`'s public signature defaults `base=None`, `_run_mutation` turns that
into `{}`, and the kill test is `sig != base.get(gname)`. `{}.get(name)` is `None`, and no gate
signature is ever `None`, so **the comparison is True for every gate on every mutant** — every
mutant is scored `killed`, `survivors` comes back empty, and the result dict reports a flawless
score. `unusable_gates()` and `flaky_gates()` are only ever called from `_session`, so a caller
that goes through `run()` gets neither guard.
**Why it matters.** This is verbatim the failure `_gate_result`'s own docstring was written to
end: *"the report would have read `146 killed, 0 survived` — a flawless score from a test that
never tested anything."* It is not fixed at the public entry point; it is fixed only on the CLI
path. `run()`'s own docstring names the callers this exposes: *"anything that imports this module
and calls it directly — the drill, a work-order reproduction, a future scheduler."* Today
`drill.py:4621/4629` calls `M.run("scope.py")` only to exercise the lock (it raises before
mutating), so nothing is currently producing a false perfect score — the defect is latent, and it
is latent in the one place the module invites new callers. `run()` should refuse a missing
baseline rather than default to a dict that cannot match.
**Confidence:** certain (pure arithmetic on the source; no run required).

### F3 — a gate that TIMES OUT or ERRORS on a MUTANT is counted as a kill
**Where:** `src/mutate.py:_run_mutation`, both gate loops; `_gate_result` returns `"TIMEOUT"` and
`"ERROR:<Type>"` as ordinary signatures.
**What is wrong.** `unusable_gates(base)` refuses to mutate when a gate cannot complete on
**clean** code, and its docstring reasons carefully about `TIMEOUT == TIMEOUT` producing false
survivors. The opposite direction is unguarded: once the baseline is healthy, a `TIMEOUT` or
`ERROR:` signature on a mutant differs from the baseline signature and is scored `died_at`, i.e.
a KILL, and `killed += 1` with no distinction recorded anywhere in the result dict or the journal.
**Why it matters.** `unusable_gates`'s own comment records that `verify_math` REACHES THE NETWORK
(section 19aa, live API calls to fandom and Wikipedia) and stalled past five minutes in a
sandbox under load; the confirm gate `drill` has a 1200 s timeout. A machine under load — this
one, tonight, with a foreign process cyclically exhausting ephemeral ports — therefore converts
"the gate could not finish" into "the safeties noticed", inside the number the whole module
exists to produce. False kills are the direction that HIDES holes, and they look exactly like
real kills. The fix is to score `TIMEOUT`/`ERROR:` on a mutant as INDETERMINATE and report those
separately from `killed`/`survived`, so the totals only ever contain mutants that were actually
judged.
**Confidence:** high (read from source; the failure requires load to observe, so it is not
demonstrated live — deliberately, since demonstrating it would mean running a pass).

### F5 — `custodes.convene`: the `dispersive` flag is REPORTED, not CONSULTED
**Where:** `src/custodes.py:convene`, the `dispersive = sorted(...)` line and `out["dispersive_custodes"]`;
comment block immediately above it.
**What is wrong.** The comment claims the flag "is now READ rather than merely declared… Deriving
the list from the table means a second dispersive Custos would be picked up here instead of
silently ignored." The derived list is used in exactly one place: it is put into the output dict.
The widening itself (`stale = staleness_widening(distance, years_since)`, then `half += stale`)
never consults it. A second Custos marked `dispersive=True` would be NAMED in
`dispersive_custodes` and would contribute nothing whatever to the interval — which is what the
comment says cannot happen any more.

Proved by flipping the flag in memory (no source edited), same inputs, `distance=1e6`,
`years_since=10`:

```
dispersive=True   -> staleness_widening=0.5  interval=0.6  dispersive_custodes=['Lumen']
dispersive=False  -> staleness_widening=0.5  interval=0.6  dispersive_custodes=[]
interval identical with the flag off: True
```

**Why it matters.** This module's own docstring names "a property asserted in the table and
enforced nowhere" as the defect in miniature that this line was written to close, and a comment
contradicting its code is the shape `address_space`'s docstring says "survived twenty-five runs".
The flag moved from unread to read-into-a-string; it is still not load-bearing.
*(Distinct from `bd673ceaaf31` — that order is about the two Custodes who cannot work on a default
call. This is about the flag's wiring on the path where they CAN.)*
**Confidence:** certain (demonstrated).

### F9 — `tells.prompt_section()` has no caller and no drift net: the single-source claim is not in effect
**Where:** `src/tells.py:prompt_section` (and the claims at `src/tells.py` module docstring
"the prompt section is GENERATED from it", `src/style_audit.py:30`, `src/pipeline.py:1673`).
**What is wrong.** `prompt_section()` is called from exactly one place in the repository:
`tells.py`'s own `__main__` under `--prompt`. Nothing writes `prompts/system_style.txt`, and no
drill net or `verify_math` check compares the generated block against the file. `system_style.txt`
is a static file that was generated once and pasted.
**Why it matters.** The module's WHY ONE FILE section states the exact failure this leaves open:
*"Kept in two places they drift, and a phrase banned in the prompt but absent from the checker
goes unnoticed for fifty thousand entries."* Adding a word to `LEXICAL` changes the audit and
leaves the model's instruction untouched, with nothing to say so. Verified TODAY: the generated
block IS currently present verbatim in the prompt file, so nothing has drifted yet — the safety is
simply not running. The cheap repair is a check (drill net or `verify_math`) asserting
`prompt_section() in open("prompts/system_style.txt").read()`.
**Confidence:** certain (`prompt_section` grep across the whole repo returns two hits, both in
`tells.py`; the in-sync state was verified by string comparison).

---

## MINOR

### F4 — `mutate._mutations` BoolOp: `found_any` suppresses the fallback for the connectives it missed
**Where:** `src/mutate.py:_mutations`, the `ast.BoolOp` branch, `if not found_any:`.
The per-pair loop skips any pair whose left operand ends on a different line from the right
operand's line. If ANY pair on the node succeeded, `found_any` is True and the whole-line fallback
is skipped for the ones that did not — so those connectives are never attempted. The docstring
says such nodes "fall back to the previous whole-line `replace(..., 1)` behaviour", which is true
only when EVERY pair failed.

Demonstrated on a string:

```
x = (aaaa
     and bbbb and cccc)      -> 1 mutant generated; the first `and` never attempted
```

Counted against the live targets (BoolOp connectives present vs `and`/`or` mutants generated):
assay.py 22 vs 20 (**2 missed**), prose_gate.py 14 vs 14 (0), escalation.py 24 vs 23 (**1 missed**).
Three connectives in total, sibling shape to F1 and to today's `replace(...,1)` fix.
**Confidence:** certain (demonstrated).

### F6 — `custodes` fails OPEN on an unrecognised attestation grade
**Where:** `src/custodes.py:_custos_reading`, `ATTESTATION_QUALITY.get(attestation, 0.4)`
(and the same shape at `src/assay.py:interval_from_hands`, `ATTESTATION_FLOOR.get(attestation, 0.30)`).
An attestation string outside the charter's five grades silently reads as a mid-quality grade and
a number is published. Nothing in the returned dict names the grade as unrecognised.

Proved:

```
attestation="Transcribed"      -> decimal=0.5   interval=0.11
attestation="TOTAL NONSENSE"   -> decimal=0.51  interval=0.12
fields naming the grade unrecognised: NONE
```

A lowercase `"witnessed"`, or a grade renamed in the charter, lands in this same branch. HARD
RULE -1's FAIL CLOSED property says an unreadable input must refuse, and this one answers. Note
the contrast with the work done today on `staleness_measured`/`currency_source`, which made an
ABSENT measurement impossible to read as a zero: an UNRECOGNISED one is still readable as a
measurement.
**Confidence:** certain (demonstrated).

### F7 — `evidence_sensitivity` is inert wherever `tilt` is zero
**Where:** `src/custodes.py:_custos_reading`,
`evidential_part = c["tilt"] * c["evidence_sensitivity"] * (1.0 - q)`.
The evidential term is a multiple of `tilt`, so a Custos with `tilt=0.0` has no response to
attestation quality however her `evidence_sensitivity` is declared. Threnody declares
`evidence_sensitivity=0.10` and gets exactly 0.0 on every reading; Lumen declares 0.0 and is
consistent. The CUSTODES table's own header says "High sensitivity means their disagreement IS
reducible by fieldwork" — for a zero-tilt standpoint that is a declared property with no
mechanism behind it, the same class as F5 in miniature. Either Threnody's 0.10 should be 0.0
(and say why), or the evidential term should not be scaled by `tilt`.
**Confidence:** certain (arithmetic; enumerated from the live table).

### F8 — `address_space.assign()` pre-wraps every tier, so `pack()`'s range guard cannot fire
**Where:** `src/address_space.py:assign`, `fit()`: `return (0 if v is None else int(v)) % (1 << WIDTHS[field])`.
`pack()`'s docstring: *"Raises rather than truncating: a silently wrapped address would name a
different world, which is the one failure mode worth being loud about."* `assign()` — the module's
only real address producer, the one `main()` uses for all 1,016 catalogued worlds — applies `%`
to every tier before handing it to `pack()`, so the out-of-range value `pack` promises to shout
about can never reach it.

Proved:

```
pack(multiverse=1e9)                     -> ValueError: multiverse=1000000000 does not fit in 8 bits
assign(..., {"multiverse": 1e9})         -> no raise; unpacked multiverse = 0   (silently wrapped)
```

A guard whose only production caller pre-satisfies it is a check that cannot fail. This is a
DIFFERENT fault from order `642a95fe9f3c` (which is about `fit()` mapping a MISSING/None tier to 0
with no marker): this is about a tier that is PRESENT and too large being wrapped rather than
refused. Live widths are `multiverse: 8 bits`, and order `60dc7c624c06` already records that
TIERS.json's hyperverse values contradict the prose — a census that moves is exactly the
circumstance in which this wrap fires.
**Confidence:** certain (demonstrated).

### F10 — `snapshot.before()` accepts a path outside the tree and writes the copy OUTSIDE the snapshot
**Where:** `src/snapshot.py:_rel` and `before()` (`src = p if os.path.isabs(p) else ...`),
`restore()`, `verify()`.
`_rel()` is `os.path.relpath(p, HERE)` with no containment check, so an absolute path outside the
repository yields a relative beginning `../`. `before()` then joins that onto the snapshot
directory and the copy lands OUTSIDE `state/snapshots/<sid>/`; `restore(sid, into=tmp)` joins it
onto the temp directory and writes OUTSIDE the temp directory; and `verify()` compares the two
escaped copies and returns **True**.

Demonstrated (and both stray trees deleted immediately afterwards):

```
_rel('C:/Users/imarl/some/other/file.txt') = '../some/other/file.txt'
before('sweep37-probe', [<abs path in %TEMP%>, ...]) -> id returned
manifest took: ['../AppData/Local/Temp/sweep37probe_.../real.txt']
verify() -> True  "1 path(s) restored and byte-identical"
files created: state/snapshots/AppData/...  and  %TEMP%/AppData/...   [both removed]
```

Two consequences: escaped copies from two different snapshots collide at one shared location
under `state/snapshots/` (the `<sid>` folder is escaped), and `verify()`'s `finally:
shutil.rmtree(tmp)` does not remove what was written outside `tmp`. `withdraw_chapters.py:114`
passes an in-tree relative path today, so this is latent — but `before()` documents absolute
paths as supported, and this module gates irreversible acts. `_rel` should refuse a path that
does not resolve under `HERE`.
**Confidence:** certain (demonstrated, cleaned up).

### F11 — `snapshot.before()` silently skips a requested path that does not exist
**Where:** `src/snapshot.py:before`, `if not os.path.exists(src): continue`, and the `if not took:` refusal.
Only the ALL-missing case raises. A snapshot asked for two paths where one is a typo, a renamed
directory or a path not yet created returns a snapshot id, `verify()` returns True, and the
manifest records no `skipped` list — so the caller proceeds with an irreversible step having
copied half of what it asked for.

Demonstrated: `before("sweep37-probe", [<real file>, <missing file>])` returned an id, manifest
`took` held 1 of 2 entries, nothing anywhere named the missing path, `verify()` -> `True, "1
path(s) restored and byte-identical"`.

The module's own words for the empty case apply unchanged to the partial one: *"An empty snapshot
is not a safe snapshot, it is a missing one wearing the same name."* At minimum the manifest
should carry `requested` and `skipped` and `before()` should refuse when `skipped` is non-empty
unless the caller opts in.
**Confidence:** certain (demonstrated).

### F12 — `wiki_source.clean_titles()` is O(n²) on the largest categories
**Where:** `src/wiki_source.py:clean_titles`, `if t not in out:` against a list.
Measured on this machine: n=2,000 -> 0.032 s; n=8,000 -> 0.537 s; n=16,000 -> 2.066 s — quadratic.
`catalogue_web.py:150` feeds it `category_members(..., limit=None)`, and the module's own comments
cite DC's Characters category at **33,614 titles** (~9 s per call, per category, per source). A
`set` alongside the list preserves order and the dedup for free. Not a correctness fault; filed
because Hard Rule 0 makes uncapped listings mandatory, so the input only grows, and "too slow" is
this project's stated route to somebody reaching for a cap.
**Confidence:** certain (measured).

---

## OBSERVATIONS — examined, NOT filed

* **`shelfmark()` omits the `star` field, so it is not injective over addresses.** Two worlds
  differing only in `star` produce the same shelfmark string and therefore the same
  `seed_from_card()`. Verified: `map_seed()` (address-based) still differs, and the real
  `data/SHELFMARKS.json` has **1,016 worlds, 1,016 distinct addresses, 1,016 distinct
  shelfmarks — zero collisions**. The omission also matches the charter's own quoted notation
  (`Ω › H? › X? › Mt.ASC › Mv.DRG › U-7 › G.North › P.Earth`, no star tier). Not filed:
  `citation_card()`/`seed_from_card()` are already filed as dead code under `596493b0b139`.
* **`custodes.convene`'s `covers_every_reading`** is a tautology — `half` is defined as
  `max(1.96*sd, max|v-consensus|)` and only widened afterwards. Not filed: the comment at that
  key says so explicitly, names it m30, and explains why it is kept.
* **`grounding`'s `verdict` is a constant per grounding type.** `A.regress_test(top, **spec["regress"])`
  reads only the static `GROUNDINGS` table, so all 210 sources classified `ex_nihilo` receive
  byte-identical `verdict`/`assayable`/`reasoning`, and `main()`'s verdict distribution is the
  grounding distribution regrouped. Not filed: `classify_source`'s comment states this honestly
  ("the cues only identify WHICH account is being told"), and `ex_nihilo`/`emanation` carry
  identical regress dicts by design.
* **`mutate`'s `_lock_acquire` is check-then-write (TOCTOU).** Two simultaneous starts could both
  pass `active()` and both write the lock. Narrow, and since the sandbox rewrite two concurrent
  runs corrupt nothing shared. Not filed as a fault; noted so it is on the record.
* **A mutant edit can land inside a string literal** (`if "==" == a:` mutates the literal and is
  labelled `== -> !=`). Measured against all three targets by token spans: **0 occurrences**.
  Theoretical only.
* **`survivors`/`_journal` store `was`/`became` at `[:120]`.** A `[:N]` on a stored field, against
  a docstring promising "its exact diff rather than a count". Measured across all 188 currently
  generatable mutants: **0** would be truncated today. Latent; recorded rather than filed.

## CAPS FOUND (Hard Rule 0), with the judgment on each

Every `[:N]` and `limit`/`top`/`cap` in the eight modules, and what it does:

| site | verdict |
|---|---|
| `mutate._run_mutation` `muts[:limit]` | ACCEPTABLE — CLI-only, reported as `capped` in the result and printed |
| `mutate` journal/order `was`/`became` `[:120]` | LATENT — 0 of 188 mutants affected today (observation above) |
| `mutate._lock_acquire` `json.dumps(rec)[:160]` | ACCEPTABLE — exception text only |
| `wiki_source.all_categories(hard_stop=None)` | HEALTHY — default removed, no caller passes one |
| `wiki_source.find_categories(limit=None)` | HEALTHY — no caller passes one (`catalogue_web.py:278`) |
| `wiki_source.category_members(limit=None)` | HEALTHY — both callers pass `limit=None` explicitly |
| `wiki_source.rank_by_size(top=None)` | HEALTHY — `catalogue_web.py:156` passes `top=None` with the comment "rank, never truncate" |
| `wiki_source.verify_wiki_matches` `words[:4]`, `srlimit: 8` | ACCEPTABLE — a search QUERY and its result window, not a stored roster |
| `wiki_source._paragraphs` `[:max_chars]` (900) | JUDGED ACCEPTABLE, flagged — a prose EXTRACT, not a list; the comment costs the alternative at ~420 KB/article. Raised here rather than filed because widening it is a data-volume decision for the owner, not a repair |
| `grounding.classify_text(top=None)` / `classify_source(cap=None)` | HEALTHY — `cap` now refuses a numeric value loudly |
| `grounding.main()` contested list | HEALTHY — uncapped and sorted most-contested-first |
| `catalogue_models` `available_sample` / alternatives line | HEALTHY — both `[:8]` and `[:10]` removed, whole list stored AND printed |
| `address_space.main()` `list(addrs.items())[:6]` | ACCEPTABLE — console preview beside an uncapped `worlds addressed` count |
| `snapshot` | none present |
| `tells` | none present |

## HEALTHY — verified, not merely read

* `mutate.sandbox()` / `reap_orphans()` / `_owner_pid()`: ownership beats age, the ownership claim
  EXPIRES at `OWNERSHIP_CEILING_SECONDS` (the pid-recycling repair), an undated or unreadable claim
  is treated as expired rather than eternal, junctions are `rmdir`'d before `rmtree`, and
  `os.path.isdir(p)` is re-checked after `ignore_errors=True`. The mkdtemp/claim window is left
  open deliberately under order `404d0ccf9df5`; re-read this run and the reasoning still holds —
  the only `older_than=0` call in the tree is a drill probe.
* `mutate` restore chain: `verify_restore()` proves the round trip on the sandbox copy BEFORE the
  first mutant; the `finally: _write(path, original)` is inside the mutation loop's own try;
  `restored_exactly` and `live_file_untouched` are both COMPUTED comparisons, and the live-tree
  verdict escalates at OWNER. `drill.py:mutation_never_touches_the_live_tree` asks the parse tree
  where the write sites are rooted rather than grepping for strings — the strongest net of its
  kind in this batch.
* `mutate.active()` fails CLOSED on an unreadable lock and on a lock written mid-truncation;
  `_pid_alive` errs toward ALIVE except for Windows `ERROR_INVALID_PARAMETER`, with a real ctypes
  fallback so an orphaned lock can still be called stale.
* `mutate._mutations` per-occurrence fix (today's repair) re-verified on a string:
  `if a < b and c < d:` yields **three** distinct mutants — `a >= b`, `c >= d`, and `and -> or` —
  and the dedup key `(lineno, new_src)` correctly keeps both `<` edits.
* `mutate._session` matches `gates + confirm` between `baseline()` and `flaky_gates()`, so
  `--no-confirm` no longer scores an unrun gate against `None`.
* `wiki_source.all_categories` never memoises a FAILED walk, and the cache key carries `min_pages`.
* `wiki_source.page_text` continues past a failed section instead of returning `""` (BUGS m4).
* `wiki_source.resolve_wiki` catches `ValueError` as well as `OSError` on the hosts file and guards
  `isinstance(_doc, dict)`; the explicit path construction avoids the `HERE` NameError it documents.
* `wiki_source._get` defers to the shared `feats._throttle` with `MIN_GAP` as a floor, and the
  rate lock is held across the sleep so threads cannot bunch.
* `custodes.dof_coverage()` is a real check: a shared dof leaves an unmanned direction and
  `one_to_one` goes False. Not tautological.
* `custodes.ATTESTATION_QUALITY` is genuinely derived from `assay.ATTESTATION_FLOOR` (the hoisted
  single table), not restated.
* `custodes` abstentions: `staleness_measured` / `comparability_measured` / `currency_source` /
  `comparability_source` ride on every non-degenerate result, `threnody_veto` is deliberately NOT
  set to False when unmeasured, and the stderr announcement is deduped per process. Verified by
  calling `convene()` both ways.
* `address_space._hash_offsets()` derives from `WIDTHS` with the historical literals as a FLOOR —
  today it reproduces `{universe:0, galaxy:8, star:48, planet:78}` exactly, so no world moves, and
  the offsets can no longer overlap as the census grows. `HASH_BYTES` is derived (16) with a hard
  refusal above 32.
* `address_space.pack`/`unpack` round-trip exactly across all eight fields; `main()`'s demo call is
  keyword-only.
* `address_space.main()` and `grounding.main()` and `catalogue_models.sweep()` all GATE on
  `silence.write_json`'s rename verdict and return non-zero on a denial — the discarded-write-verdict
  class is closed in all three, and `catalogue_models` carries it out to `main()`'s exit code for
  `foreman.recatalogue_models`.
* `grounding`'s and `tells`' and `catalogue_models`' eaten-escape guards are live: they read their
  own source at import, and `tells` additionally scans every COMPILED pattern (including the
  `re.escape`d lexical ones, where a raw `chr(8)` would survive escaping) for control characters.
* `tells._anchor` correctly rewrites `^\s*` to a sentence-boundary alternation; no key collides
  between `STRUCTURAL` and `DISCOURSE`; no duplicate or overlapping words across `LEXICAL` and
  `LEXICAL_FICTION` (92 patterns, 92 list entries); `pipeline.py`'s "138 machine-writing tells"
  matches `60 + 32 + 46`.
* `catalogue_models.ask_provider` distinguishes all four outcomes, and `sweep()` prints the
  DENOMINATOR — `unverified` providers by name with their unchecked model ids — so "N stale"
  cannot be read over a pool that was never asked.
* `catalogue_models` line `mid = m.get("id") or m.get("name") if isinstance(m, dict) else str(m)`
  parses as `(id or name) if dict else str(m)`, which is the intended reading. Checked because the
  precedence is easy to get wrong.
* `snapshot._dir_matches` walks the snapshot side and byte-compares with `shallow=False`, closing
  order `e5116f51c82a`; `verify()` restores into a temp directory, never the live tree.

## NOT RE-FILED (already on the queue, re-read and still accurate)

`bd673ceaaf31` (OWNER — Lumen/Threnody unwired), `404d0ccf9df5` (mutate mkdtemp window, accepted),
`6d7f88ffb76e` (junction write-through), `adba96551729` (verify_restore scope),
`642a95fe9f3c` (address_space `fit()` maps a MISSING tier to 0 unmarked),
`60dc7c624c06` (TIERS.json contradicts address_space prose), `1eb00a84225e` (`UNADDRESSED` dead),
`596493b0b139` (`citation_card`/`seed_from_card` dead), `692f693c3900` (tells rule-of-three narrow),
`ded8418c75a6` (convene band-only return omits the measured flags).

---

## ORDERS FILED (found_by = sweep37-batch10)

| id | severity | finding | code |
|---|---|---|---|
| `9a694b3ae227` | MAJOR | F1 | MUTATE_SKIPS_59PCT_OF_COMPARISON_OPERATOR_SITES |
| `91c1a581453d` | MAJOR | F2 | MUTATE_RUN_DEFAULTS_TO_NO_BASELINE_SCORING_EVERY_MUTANT_KILLED |
| `d2fb14ffa8c6` | MAJOR | F3 | MUTATE_COUNTS_A_TIMED_OUT_OR_ERRORED_GATE_AS_A_KILL |
| `7059872ef2b7` | MINOR | F4 | MUTATE_BOOLOP_FALLBACK_SUPPRESSED_BY_FOUND_ANY |
| `90eba4982972` | MAJOR | F5 | CUSTODES_DISPERSIVE_FLAG_IS_REPORTED_NOT_CONSULTED |
| `0aefdac4a26d` | MINOR | F6 | CUSTODES_FAILS_OPEN_ON_AN_UNRECOGNISED_ATTESTATION_GRADE |
| `39f19f7e646c` | MINOR | F7 | CUSTODES_EVIDENCE_SENSITIVITY_INERT_WHERE_TILT_IS_ZERO |
| `b6474eb0a258` | MINOR | F8 | ADDRESS_SPACE_ASSIGN_PREWRAPS_SO_PACKS_RANGE_GUARD_CANNOT_FIRE |
| `a08557925d87` | MAJOR | F9 | TELLS_PROMPT_SECTION_HAS_NO_CALLER_AND_NO_DRIFT_NET |
| `ca3452eb9d49` | MINOR | F10 | SNAPSHOT_ACCEPTS_A_PATH_OUTSIDE_THE_TREE_AND_ESCAPES_THE_SNAPSHOT_DIR |
| `f4193095edff` | MINOR | F11 | SNAPSHOT_SILENTLY_SKIPS_A_REQUESTED_PATH_THAT_DOES_NOT_EXIST |
| `33ba82dab55c` | MINOR | F12 | WIKI_SOURCE_CLEAN_TITLES_IS_QUADRATIC_ON_THE_LARGEST_CATEGORIES |

All 12 are new order ids (`seen: 1`, `first_seen == last_seen`), i.e. none refreshed an existing
order — checked against the queue after filing.

## COVERAGE RECORDED

`sweep_plan.record('run37', [...8 modules...], batch=10)` returned all eight at `run: 'run37'`:
`mutate.py`, `wiki_source.py`, `custodes.py`, `address_space.py`, `grounding.py`,
`catalogue_models.py`, `tells.py`, `snapshot.py`.

## POST-AUDIT STATE

No source file was modified (mtimes on all eight modules and on `prompts/system_style.txt`
unchanged from before this batch). No process started or stopped. No network call made. No
sandbox under the temp tree touched. The two directories created by the F10 demonstration were
removed and their absence re-verified.
