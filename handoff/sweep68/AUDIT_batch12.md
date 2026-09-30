# AUDIT batch 12 -- sweep68 (run68)

## Scope

Read in full, sequentially, in chunks with the Read tool:

| module | lines |
|---|---|
| src/magnitude.py | 2036 |
| src/silence.py | 1327 |
| src/allsweep.py | 1116 |
| src/custodes.py | 732 |
| src/address.py | 543 |
| src/suppressions.py | 460 |
| src/grounding.py | 361 |
| src/context_budget.py | 320 |

Read-only for the project. Scratch scripts are under `%TEMP%\aud68_12` (s1..s9). They import modules and
call pure functions with write paths redirected (`magnitude.OUT`, `suppressions.FILE`) into a temp dir;
`run_batch` was driven with `assay_entity` / `queue` stubbed. No module `main()` ran against the live tree,
nothing under src/, data/, state/, output/, prompts/ or config.yaml was written.

## Prior-audit cross-check (handoff/sweep67, batches 04, 09, 10, 12, 13, 15)

sweep67 batch 12 (magnitude, silence, allsweep):
- F1 (IMPORT tier runs `main()` of argparse-less modules): FIXED. `check_import` now loads such modules under
  a non-`__main__` name (`allsweep.py:358-370`). Scan of src/: no module mentions `ArgumentParser` without
  building one, so the `"ArgumentParser" in source` test has no false positive today.
- F2 (no TimeoutExpired/OSError handler, `E.artifacts` unwrapped): FIXED (`:374-383`, `:943-949`).
- F3 (quantity-only entity anchors from memory): FIXED (`magnitude.py:1260`, keyed on `cand`).
- F4 (guard 5 relevance): FIXED for relevance and ton-as-mass (`quantity_scores:521-526`). The unconditional
  replace of a model score by an instrument reading is documented as deliberate.
- F5 (calibrate carried DEFERRED rows / stamped complete): FIXED (`:1583-1590`, `:1712`).
- F6 (host_ceiling cached None on generic exception): PARTLY. No longer cached, but it now returns None
  uncached, which every caller reads as "no clamp" -- see F5 below.
- F7 (NaN/Infinity scores): FIXED (`_is_score` `math.isfinite`, `:836-837`).
- F8 (`--limit` banner): FIXED (`run_batch:1909-1914`).
- F12 (append_line docstring), F13 (`swallow` eats BaseException), F16 magnitude stale citations
  (`6,144`, `assay.py:174`): FIXED. `swallow` is still dead code (no caller).
- Q1 (max over slice scores in `_one_axis`, upward-biased): STILL STANDS (`:1073-1074`).
- Q2 (`run_batch` rewrites the whole dict per result, no CAS): STILL STANDS, and see F1 below.
- Q4 (`silence.instrument` bare `open("w")`, `.presilence` overwritten on a second run): STILL STANDS
  (`silence.py:1318-1321`).
sweep67 batch 04 F7 (suppressions wrong element type raises): FIXED (`suppressions.py:106-118`).
sweep67 batch 09 F8 (context_budget quoting measurements of a since-changed prompt): PARTLY. Figures are now
labelled "as measured 2026-08-24" (`:29-31`, `:87`); live figures are system 22,882 chars, template heading at
line 149 (`context_budget.report`). Still stale, still harmless.
sweep67 batch 10 F7 (custodes comment at :189-191): rewritten, but now stale the other way, see F13.
sweep67 batch 13 (address) and batch 15 (grounding): cleared then, re-read now; new findings below.

## Findings

### F1 -- HIGH: `run_batch` treats an unreadable ASSAYS.json as empty, then overwrites it (fail-open, destroys settled records)
`magnitude.py:1898-1904`: `except Exception: silence.note("magnitude.py:resume"); done = {}`, and the first
completed result runs `silence.write_json(OUT, done, ...)` at `:1968`. A read that fails for a reason other than
corruption (Windows denies the open while another writer's `os.replace` is landing, an AV lock, a torn file
from a killed run) authorises "nothing is assayed yet", and the next write replaces the whole file with only
this run's results.
Scenario: ASSAYS.json holds 500 settled records; `--batch --host h` starts while the file is momentarily
unreadable; `done` is `{}`; one result lands; the file now holds 1 record.
Reproduction (`s4.py`, OUT redirected, `open` made to raise PermissionError on the first read of OUT):
`records before: 500 ; after: 1 ['h|A']`. With `--fresh` this is intended; without it the operator asked to
RESUME. Fix: on an unreadable-but-existing file refuse to start (or retry) instead of continuing with `{}`;
same doctrine `suppressions._load` already follows ("UNREADABLE MUST NOT LOOK LIKE EMPTY").

### F2 -- MEDIUM: `allsweep.py --quick` overwrites ALLSWEEP.json with a report that has no VERIFY or ESTATE tier, and consumers read it as green
`allsweep.py:910-911, 937-938, 1035`: in `--quick` mode `verifiers = []` and `est = {}`, and the file is still
landed with a fresh `at`, `"verifiers": []`, `"estate": {}`, `"estate_faults": []`. Nothing in the file says the
tiers were skipped. `foreman._checks_pass` runs `allsweep.py --quick` on every model-patch check, so a quick run
replaces the last full sweep's red verifier and estate rows.
Consumers: `workorders.battery_faults` (`:272-327`) only iterates what is present; `standards.py:1663-1675`
"verifiers all run" is `not crashed` over an empty list and "the full audit is recent" reads the file mtime.
Reproduction (`s7.py`, pure function): a quick-shaped report gives `BATTERY_GRADED: False`; the same shape with
one failed verifier and one estate fault gives `BATTERY_GRADED: True`. So: full sweep red (verify_math FAILED),
foreman checks a patch, the artifact is now green for up to `ALLSWEEP_MAX_AGE` (24h) and the standard says
"the full audit is recent". Fix: stamp `"quick": true` (or `"tiers": [...]`) and have battery_faults and
standards treat a quick report as not covering VERIFY/ESTATE, or do not land ALLSWEEP.json from `--quick`.

### F3 -- MEDIUM: the `emanation` cue `the One\b` matches ordinary "the one" (case-insensitive), so it decides real classifications
`grounding.py:91` inside `GROUNDINGS["emanation"]["cues"]`, weight 5, scored with `re.I` at `:173`. In prose
"the one who ...", "the one that ..." fires it. Repro: `classify_text("origin: it was the one who did it. the
one that stayed.")` -> `emanation 10`.
Measured on all 210 records (`s6.py`, only that token made case-sensitive via `(?-i:the One\b)`): the GROUNDING
of 12 sources changes: Marvel (emanation 1485 -> ex_nihilo 735), DC (830 -> ex_nihilo 506), Dragon Ball Z, Gears of
War, Ghost Recon, One Piece, Rosario + Vampire, Soul Calibur, StarCraft, the Lovecraftian mythos, all the Fate
series, Who Framed Roger Rabbit; the contested count moves 14 -> 8. The `_ORIGIN` filter does not help (a
"creat..." or "origin..." entry containing "the one" passes it). The module's own comment at `:97` says a
cosmogonic cue "must name the COSMOS, not merely repeat"; this one names nothing. Fix: make the cue
case-sensitive, or require a cosmogonic neighbour ("the One from which", "the One, source of").
The other capitalised-noun cues in the same table (`the Force`, `the Weave`, `the current`) are the same shape
(UNVERIFIED for impact; the measurement above isolates only `the One`).

### F4 -- MEDIUM: guard 2's lexicon and the candidate generator's lexicon are two different tables, and they contradict each other
`magnitude.py:214-240` (`AXIS_LEXICON`/`AXIS_RE`, used by `verify` at `:911`, `quantity_scores`) versus
`feats.py:1987-2022` (`AXIS_ACT`, which decides which sentences are OFFERED to the model under each axis at
`magnitude.candidates`). A sentence the generator offers under axis X can fail guard 2 for X, and the axis then
drops to `unestimable`.
Measured on data/ASSAYS.json (507 records, `s2.py`): 607 rejections read "feat does not bear on <axis>"; in 169
of them (28%) the rejected sentence matches `feats._AXIS_ACT_RE[<same axis>]`, i.e. our own pipeline classed it as
that axis's evidence. Examples: "Future Trunks was also able to best Goku Black" (volition), "Realizing that he
must destroy Cell completely" (acumen), "As Tieria headed out ... to intercept ..." (celerity), "...extends his
hand forward" (reach). Synthetic: "He hurled a boulder at the tank" is a Reach candidate and fails AXIS_RE
Reach; "He intercepted the strike" is a Celerity candidate and fails AXIS_RE Celerity.
Consequence: every such axis is thrown away although the sheet is exactly what the pipeline built, which lowers
coverage and widens intervals across the library. The split path skips guard 2 entirely ("by construction"), so
the same evidence is accepted there and refused in one-shot: same input, different outcome by transport.
The other direction is over-broad: unanchored stems (`range` matches "Strange", `tons?` matches "Newton",
`time` matches "sometimes", `plan` matches "planet", `kill` matches "skill"); the comment at `:210` says
"deliberately narrow". Fix: one table (guard 2 = the generator's own regexes, plus word boundaries) so a
candidate can never fail its own axis.

### F5 -- MEDIUM: `host_ceiling` turns any non-ProbeUnread failure into "no ceiling" and the entity is assayed unclamped
`magnitude.py:1837-1842`: `except Exception: ...; return None`. The sweep67 fix stopped CACHING that None, but the
value returned is the same one `assay_entity` reads as "this host has no ceiling" (`if anchor and ceiling and`
at `:1375`), so the entity is scored and published with no clamp. The ProbeUnread arm three lines above raises
precisely because "a refusal is not 'this host has no ceiling'"; the generic arm is the same fault with a
different exception class (a KeyError on a malformed search row, a TypeError).
Reproduction (`s3.py`, `SCOPE.scope_for` patched to raise TypeError): `host_ceiling("nonexistent-host...")` ->
`None`, no raise. Failure scenario: a throttled/garbled scope probe -> a Jace-shaped M10.77 anchor is not clamped
and lands in ASSAYS.json as a `settled()` record that is never recomputed. Fix: re-raise (or return a sentinel
the caller refuses), as the ProbeUnread arm does.

### F6 -- MEDIUM: `_resolve_citation` accepts a fabricated citation that merely CONTAINS a short mined line
`magnitude.py:776-789`. The length bar (`_substantial`) is applied to the CITATION only; the containment test
`t in rn` runs against every mined line however short (the file itself says 171 of 37,285 mined feats are under
the bar), at character level. A model-written sentence that contains a short heading resolves to that heading.
Reproduction (`s3.py`): mined `{1: "Speed", 2: "Goku destroyed a mountain range ..."}`, citation "Goku moves at
unbelievable speed across whole galaxies in seconds" -> `(1, None)`. With a 2-letter heading "Ki", the citation
"Goku killed everything in the whole universe instantly" -> `(1, None)` (substring of "killed").
Consequence: guard 1 passes on a citation that is not in the mined list; guards 2 and 3 then judge the heading
(no agent, so guard 3 cannot refuse), and the model's number stands on a one-word "feat". If a real long
sentence is also contained, the pool has two distinct lines and the citation is (safely) refused, so the hole is
exactly the fabricated case. Fix: in the numbered pool require `t` to be `_substantial` too, or contain at word
level only.

### F7 -- MEDIUM: guard 3(d) treats any rival that shares one name token with the entity as the entity
`magnitude.py:342-345` (`entity_forms` adds every name token >= 3 letters) and `:363-370` (`_is_entity` accepts a
span if any of its tokens is in `forms`). Reproduction (`s3.py`): entity "Captain America", sentence "Captain
Marvel destroyed the alien ship with a blast." -> `subject_refusal` is `None`; likewise "Iron Man" / "Iron Fist",
"Doctor Strange" / "Doctor Doom". The rival span is classed `mine`, so rule (d) never sees a rival and the
bystander's deed is credited. Shared title words (Captain, Doctor, Iron, Lord, Black, Green, Lady, King) are
common in the Marvel/DC/fantasy sources this library is built from. The comment at `:339` argues the
parenthetical and surnames must count; the defect is that a shared title word is not evidence of identity. Fix: a
span whose tokens include a non-entity capitalised name token (Marvel, Doom, Fist) is a rival unless the whole
span is one of the forms.

### F8 -- MEDIUM (UNVERIFIED): the split path asks the ANCHOR question over citations that have not passed any guard
`magnitude.py:1094-1103`: `cites = [v["feat"] for v in axes_out.values() if v.get("feat")]` are the model's raw
`feat` strings, put into the anchor prompt before `_split_gate` (`:1380`) has verified, relevance-checked or
subject-checked any of them. A citation guard 1 later refuses as fabricated, or guard 3 refuses as a
bystander's deed, has already informed the integer band, which scales every decimal. The ceiling clamp bounds
the damage only where a ceiling exists (F5). Not run (needs a model). Fix: run the gate first and pass only
surviving citations to the anchor call.

### F9 -- LOW: an exact two-way tie is classified silently and not flagged as contested
`grounding.py:313` flags `confidence < 0.5`; `:240-261` picks `ranked[0]`, which on equal scores is the first in
GROUNDINGS dict order. Two groundings at 15/15 give confidence exactly 0.5, which is not `< 0.5`. Live:
data/GROUNDINGS.json holds "Who Framed Roger Rabbit (...)" as `emanation`, score 15, confidence 0.5, runner-up
`immanent 15` (`s9.py`); it is absent from the contested list and its verdict is dict-order luck. Fix: `<= 0.5`,
or flag any exact top tie.

### F10 -- LOW: `silence._handler_is_observed` credits a handler for a sink that uses a DIFFERENT variable of the same name
`silence.py:374-394`: `tainted = {node.name}` is carried into the statements after the `try`
(`_stmts_after`), where a later `except ... as e:` or `for e in ...` rebinds the name; a Return/Expr using that
new `e` counts as this handler's observation. Measured (`s1.py`): of 1,359 handlers, 32 are observed only via the
code after the try; in 7 the name is rebound later. Live case: `drill.py:2325`, `except PG.ProseRefused as e: if
label not in str(e) ...: return False` (falls through silently on the match branch, the "genuine article" the
docstring at `:359-365` says stays SILENT) is classified observed because the next `try` has `except ...
ProseRefused as e: return label in str(e)`. The direction is the hiding one. Fix: stop taint propagation at the
first rebinding of the name.

### F11 -- LOW: suppressions bounds are enforced only at the `add()` door
`suppressions.py:53-64` refuses non-finite / >365-day TTLs and `problems()` (`:379-418`) never re-checks. A row
with `"expires_at": Infinity` (Python's `json` accepts it) or one 4,000 days out is `active()` for ever and
`problems()` reports `[]` (`s5.py`, both rows). And nothing bounds breadth: `add("secret", "*", ...)` is accepted
and `suppressed("secret", "data/records/a.json")` is then True, against the header's "THE RULE THAT MATTERS
MOST: a suppression narrows a detector for a NAMED case. It never turns a detector off." Live rows are fine
(3 rows, 145-159 days, none blanket). Fix: `problems()` flags expiry past `added_at + MAX_TTL_DAYS` or
non-finite, and flags a pattern that is `*`/`**`/`*/*`.

### F12 -- LOW: `custodes.convene` does not validate `eta`
`custodes.py:488-494, 601`. `eta=float("nan")`: `(1.0 - eta) >= 0.10` is False, no veto, and
`comparability_measured` is True (`s5.py`). `eta=1.7` reports "measured ... curl fraction -0.7000". A NaN from a
future `hodge_decompose` would read as a measured, non-vetoing curl -- the exact "absent measurement read as a
zero" that this module's abstention machinery exists to prevent. No production caller passes `eta` today, so
inert. Fix: refuse non-finite or outside [0, 1].

### F13 -- LOW: stale comments
- `custodes.py:189-193` ("not yet part of the battery") and `:725-727` ("nothing invokes this module as a
  subprocess yet ... order 00a85c511b53, still open"): `drill.py:3083-3109` and `verify_math.py:1376-1386` now
  consult `table_faults()`, and allsweep's IMPORT tier loads this module every sweep.
- `magnitude.py:122-123` ("one 6,144-token context") and `:210` ("deliberately narrow", see F4).
- `context_budget.window()` comment calls 8192 "a third window nobody measured" but `generate.call_ollama` still
  sends `cfg.get("num_ctx", 8192)`; the budget is the smaller number, so the direction is safe.

### F14 -- LOW (latent): `address.spine_code_for` resolves a target that sits inside several index names by file order
`address.py:248-257`. The direction "target inside index name" is deliberately un-guarded, and ties keep the first
entry (`evidence > best_evidence`). 33 single-word titles are contained in index names carrying more than one
distinct code and all 33 resolve to a real code rather than UNASSIGNED (`s7.py`), e.g. "Dragon" -> II.A.1 with
II.L.7 also a candidate, "Angels" -> II.C.2 with III.11 also. Against the live roll (215 names) there is no such
case (`s8.py`: 215 assigned, 0 ambiguous), so this is a hazard for the next roll addition, not a current
mis-shelving. Hard Rule 2 says an ambiguous placement is UNASSIGNED. Fix: when two candidates tie on evidence with
different codes, return UNASSIGNED.

### F15 -- LOW (UNVERIFIED): `grounding.main --write` will land an empty GROUNDINGS.json
`grounding.py:279-281, 337-356`: `out` is built from `PL.records()`, which skips a record it cannot open
(`pipeline.records` swallows and continues, noted in sweep67 F11). If every record is momentarily unreadable, or
`data/records` is empty, `out` is `{}` and `write_json` lands `{}` over the real file with rc 0. Not run (would
write). Fix: refuse when `len(out)` is below the record-file count.

## Questions

1. `magnitude.settled()` (`:1870`) makes "no axis cleared its gate" and "sheet saturated" permanent findings that
   are never recomputed. Both depend on the model's behaviour on the day (the docstring's own account of
   saturation: "evidence about the SCORER"). Is a scorer-day artifact meant to bury the entity for good?
2. Is `--quick` meant to replace ALLSWEEP.json (F2)? foreman.py's comment calls the gate a patch check, not a
   battery answer; the file is read as the battery's answer.
3. `silence.instrument` (Q4 from sweep67): still writes source and `.presilence` with bare `open("w")` and a
   second run that finds new silent handlers stores the already-instrumented file as the "pristine" backup.
   One-shot tool, or worth a guard?
4. `magnitude._one_axis` keeps the highest slice score (sweep67 Q1). Unchanged; still an upward-biased estimator.
5. `allsweep.run_verifier:471` and `check_import:405` grade "refused" when the halt sentence appears ANYWHERE in the
   output, with no check that a halt is actually standing. A verifier that fails (rc=1) while merely printing the
   sentence would be graded not-failed. Deliberate (the ruling is about children that obey the interlock)?
   UNVERIFIED that any verifier prints it outside a refusal.

## Cleared (examined closely, found correct)

- magnitude: `_status_score`, `_is_score` (bool + finite), `verify` ordering (status / non-score / empty
  citation / resolve / relevance / subject / clamp), `saturated` width floor, `_split_gate` guards 1+3 and status
  mapping, `slice_census` arithmetic, epoch and anchor DEFERRED returns and the retry re-validation,
  `quantity_scores` (relevance, mass-ton, guard 3, strongest-per-axis), `calibrate` resume / `_land` /
  `complete` semantics, `queue` dedupe and NOT_AN_ENTITY search, `settled` for DEFERRED and exception records,
  `run_batch` tally and lock.
- silence: `_block_reaches_sink` / `_stmts_after` (only the F10 rebinding hole), `_OBSERVED_RX` (no handler is
  observed solely through a string constant today: 0 of 1,359 apart from the `silence-exempt` marker),
  `_suppressed_names` / `_suppress_is_declared`, `write_json` (tmp naming, fsync, discard on refusal),
  `replace_retry` vs `replace_if_unchanged` (re-digest per attempt, UNREADABLE distinct from absent),
  `note()` totality, `instrument` bottom-up insertion and re-parse, `_ensure_import`, `append_line` lock /
  fallback / finally.
- allsweep: `check_import` halt and no-traceback grading, `run_verifier` grading and GPU pause row, `dangling_count`,
  `reconcile` uncapped `names`, tri-state process probe, `_row_is_fault` fail-closed, `estate_faults`, lint BLIND
  paths, the `bad` sum and landed gate.
- custodes: private weight table, tilt / evidential arithmetic, quality map from `assay.ATTESTATION_FLOOR`,
  `_transit_widening` once-per-mechanism, attendance on the band-only return, interval-covers-every-reading,
  zero-variance flag, `table_faults`. 4,000 random sheets: published decimal stayed inside [0.01, 0.84].
- address: exact / letter-equality / most-specific containment / one-token-remainder guard / token-overlap
  fallback (215 of 215 roll names assigned, none by an ambiguous tie), `promote` never demotes, `tier_rank`
  None for unknown, `slugify` uncapped.
- suppressions: `_load` wrong-shape refusals, CAS `_mutate` re-apply, `_land` verdict, `fnmatchcase`,
  `_repo_listing` built once.
- grounding: `classify_text` full-field denominator, `cap` refusal, synthesis exemption as documented, uncapped
  contested list, gated `write_json`.
- context_budget: fail-closed `_read_scaffold`, zero/negative budgets not clamped, split by heading (heading at
  line 149 of prompts/system_style.txt), `feats_block_budget` 17,985 chars at num_ctx 12,288.

## Coverage recorded

`sweep_plan.record('run68', ['magnitude.py', 'silence.py', 'allsweep.py', 'custodes.py', 'address.py',
'suppressions.py', 'grounding.py', 'context_budget.py'], batch=12)` run after this file was written.
