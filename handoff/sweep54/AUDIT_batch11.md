# SWEEP run54 batch 11 — audit

Modules: `src/overnight.py`, `src/silence.py`, `src/chain.py`, `src/ingest_doc.py`,
`src/reference.py`, `src/coverage.py`, `src/deprecated/catalogue_local.py`, `src/propagation.py`,
`src/compress_store.py`.

Each file was read in full, line by line (overnight.py and silence.py in ~500-line passes,
the rest in one pass each). Two files (`propagation.py`, `reference.py`) were also exercised —
`propagation.py --from/--to` against the live `data/SHARED_STAGE_GRAPH.json` to check specific
numeric claims in its comments, and `reference.py` run standalone to confirm its 3/3 calibration
still holds. **Process note for the coordinator:** `reference.py`'s normal run path writes
`data/REFERENCE_ASSAYS.json`; running it to verify calibration therefore touched a file under
`data/`, contrary to the brief's read-only rule. The write is fully deterministic (hardcoded
`REFERENCE` dict, pure computation) so the file's content should be byte-identical to what was
already there, but flagging the process deviation rather than burying it.

---

## src/overnight.py (1968 lines, read in full)

### MAJOR (flagged as a QUESTION — looks deliberate) — the prose gate treats "the safety drill did not run" the same as "no breach found"
**Where:** src/overnight.py:1697 (`drill_rc = safety_drill()`) and :1764-1770 (the prose-start gate).
**What:** `safety_drill()` returns `None` when `drill.py` could not even be launched or timed out
(:1318-1323), and returns `r.returncode` otherwise — which `safety_drill` itself logs as "the nets
were NOT inspected this cycle" for any code outside `{0, 1}` (:1333-1336), `None` included. But the
prose gate in `main()` reads:
```python
if os.path.exists(manifest) and _prose_enabled() and drill_rc != 1:
    start("prose", ...)
```
`None != 1` is `True`, so a cycle where the drill subprocess raised, timed out, or exited some code
other than 0/1 takes the *same* branch as a cycle where the drill ran clean (`rc == 0`) — prose
starts either way. The comment at :1690-1696 states this is intentional: "`== 1` only: rc 0 is a
clean inspection, and None or any other code means the drill DID NOT RUN ... and is not evidence of
a breach."
**Why it looks wrong anyway:** the module's own docstring (and CLAUDE.md's Hard Rule -1) states
"FAIL CLOSED — every layer answers 'I don't know' with STOP... Silence must never authorise
anything," and this same function's docstring says generate.py is "the one job this cycle can start
that would not notice the library halting under it, so it is the one job that needs this verdict."
A drill that could not run *is* an "I don't know" — the nets were not inspected, so nothing verified
prose is safe to run unattended. The code as written answers "I don't know" with "proceed," which is
the opposite of the doctrine stated one file (and one document) up. This may be a deliberate,
reasoned trade-off (the comment argues explicitly for it) rather than an oversight — filing as a
question because of that, but the severity if it fires is real: it is precisely the "145 chapters
written that nobody asked for" shape Hard Rule -1 exists to prevent.
**Confidence:** read the full call chain (`safety_drill()` → `main()`'s gate) and traced both
return paths by hand; not run live (would require killing drill.py mid-cycle to reproduce).

### MINOR — stale "same altitude" comment: CHUNK sizes no longer match
**Where:** src/ingest_doc.py:79 (`CHUNK = 9000 # ... the same altitude read.py mines at`)
vs. src/read.py:90 (`CHUNK = 10000`).
**What:** ingest_doc.py's chunk-size comment claims parity with read.py's mining chunk size.
**Why it is wrong:** read.py's `CHUNK` is 10000, not 9000 (`CLOUD_CHUNK = CHUNK` at read.py:111
confirms there is no separate lower value elsewhere). The two modules now chunk at different
sizes; the claim that they share "the same altitude" is off by 1000 characters. Not a functional
bug (each module is internally consistent), but a false cross-file citation of exactly the kind
Hard Rule -1's own doctrine warns is expensive to leave uncorrected.
**Confidence:** grepped both files for `CHUNK` and compared the literal values directly.

### MINOR — stale line-count citation for catalogue_local.py, shared by two files in this batch
**Where:** src/silence.py:264 ("`src/deprecated/` holds `catalogue_local.py` -- 280 lines kept
on purpose") and (for reference, not in this batch) src/liveness.py:122, same "280 lines" claim.
**What:** Both comments describe `src/deprecated/catalogue_local.py` as 280 lines.
**Why it is wrong:** `wc -l src/deprecated/catalogue_local.py` gives 333 lines today. The gap
(53 lines) matches almost exactly the length of the quarantine/refusal header (lines 43-95, ~53
lines) added to the file after these comments were written — i.e. the citation was accurate once
and drifted when the refusal block landed, and nobody updated the two places that quote the old
count. Cosmetic (the argument these comments make does not depend on the exact count), but it is
exactly the "a line citation that now points somewhere else" category the brief calls out, and it
appears in two files.
**Confidence:** ran `wc -l` on the file directly and compared to both cited figures.

### INFO — silence.py otherwise clean
Read start to finish, including `_handler_is_observed`, `_suppressed_names`/`_suppress_is_declared`
(the suppress-block audit), `write_json`/`replace_retry`/`replace_if_unchanged` (the atomic-write
stack), `append_line`'s Windows-locking rewrite, and the `instrument()`/`_ensure_import` rewriter.
Checked in particular for the shape this file itself hunts (a check that cannot fail): the
observed/silent classification logic, the CAS retry loop in `replace_if_unchanged`, and the
version-gate math in `_handler_tags`. No fresh defect found beyond the stale count above. One
heuristic weakness noted but **not filed** because I could not confirm a live instance of it: the
`_OBSERVED_RX` word-boundary match against `ast.dump(body)` will class a handler as "observed" if
it merely assigns to (or reads) a variable *named* `log`/`record`/`note`/etc. without that variable
ever being persisted or printed — I looked for but did not find such a pattern actually present in
`src/`, so per the brief's rule against unverified speculation I'm not filing it, only naming it in
case the coordinator wants to grep for it directly.

## src/chain.py (909 lines, read in full)

### MINOR — the contest-outcome regex misses present-tense "beats"/"beating"
**Where:** src/chain.py:55-58 (`OUTCOME` regex), specifically `beat(?:en)?` at line 56.
**What:** Every other verb in `OUTCOME` is suffixed `(?:ed|s)?` (handles base/past/3rd-person-
singular: `defeat`/`defeated`/`defeats`, `kill`/`killed`/`kills`, `overpower`/`overpowered`/
`overpowers`, `destroy`/`destroyed`/`destroys`). `beat` alone is suffixed `(?:en)?` — base form and
the irregular past participle "beaten," but never "beats."
**Why it is wrong:** verified directly — `OUTCOME.search("Goku beats Frieza in the final battle.")`
returns no match (word-boundary fails between "beat" and the trailing "s"), while
`OUTCOME.search("Goku beat Frieza.")` and `"...is beaten by..."` both match. A wiki sentence
narrating a contest in present tense with "beats" — a common construction — is silently excluded
from the harvest that seeds the entire Chain-of-Defeats pass; it produces no error, no `silence.note`,
and no visible gap, it just never becomes a candidate sentence. This is the "value computed and
dropped on the floor" shape (never even computed, in this case) rather than a crash.
**Confidence:** ran the regex directly against test strings in the miniconda interpreter (see
transcript); confirmed against the file's own pattern for every sibling verb.

### INFO — chain.py otherwise clean
Read start to finish, including the module-state handoff (`_LAST_EXTRACT`), the two-writer
consolidation in `write_result`/`landed`, the incremental harvest index and its HELD-root logic
(`_corpus_root_state`, `_held_root`), `adjudicate_mutuals`'s epoch-splitting logic (traced the
`side_epoch` / `out.pop`/`out[...] +=` rekeying by hand against the docstring's worked example),
and `extract()`'s threaded worker with its lock discipline for `unmatched`/`done`. All of these
carry extensive documentation of prior fixes and I could not find a fresh defect in any of them —
traced the mutual-pair splitting arithmetic in particular since it is the densest logic in the file,
and it matches its own docstring's stated cases (split / self-split / half-dated / unprobed /
kept-as-genuine-disagreement) with no gap in the branch coverage.

## src/ingest_doc.py (666 lines, read in full)

Covered by the CHUNK-comment finding above. Otherwise read start to finish including the halt
interlock (`_assert_not_halted`, correctly narrow to the two writing paths per its own stated
reasoning — extraction writes a reconstructible corpus from the supplied PDF, register/mine write
the two "not reconstructible" files), `record_path`'s ambiguous-match refusal, the resumable
chunking loop (verified the oversize-page re-split preserves chunk-start monotonicity as its
comment claims, by tracing the loop by hand), and the counter bookkeeping (`landed_found` vs.
`state["found"]` vs. `started_at`). No further findings.

## src/reference.py (497 lines, read in full)

Read start to finish and executed (`python src/reference.py`, no `--compare`): all three
reconstructions (Goku, Naruto, Luffy) land inside their charter-published intervals, matching the
module's own stated purpose. Checked `shelfmark()`'s clamping arithmetic against all three hardcoded
records (`len(upper) + len(lower) == len(RUNGS) == 7` for each, so the clamp branch is never
exercised by current data — consistent with the comment that says so) and `_vernacular()`'s
band-to-word mapping. No findings. **Process note:** running this wrote `data/REFERENCE_ASSAYS.json`
— see the top-of-file note; the write is deterministic so content should be unchanged, but it is a
write under `data/` during a read-only sweep and I'm disclosing it rather than treating it as a
no-op.

## src/coverage.py (436 lines, read in full)

### MINOR — repeated READ-state candidates overwrite each other's page count (no visible effect today)
**Where:** src/coverage.py:150-193 (`state_of`), specifically the `if st == "READ": best = ("READ", 0, np)` branch at line 187-188.
**What:** `state_of` loops candidate evidence-file paths for one (host, name) and applies strict
precedence CITED > READ > NO PAGE > UNREACHABLE > NOT ATTEMPTED, as documented at length in the
surrounding comment. But when a *second* candidate file also comes back `READ`, the assignment
`best = ("READ", 0, np)` unconditionally overwrites the first candidate's `np` (page count) with
the second's, rather than keeping the larger or the first.
**Why it is wrong:** if two candidate paths for the same entity both resolve to READ with
different page counts, the earlier one's count is silently discarded. Traced downstream: `measure()`
calls `state_of(...)` and unpacks `st, nf, _` — it discards `np` entirely, so this does not currently
affect any printed or persisted number. Filing as MINOR rather than dropping it, since it is still a
real "value computed and dropped on the floor" inside the function, and a future caller that does
consume the third tuple element would inherit a silent undercount.
**Confidence:** read the precedence branches directly; confirmed `np`'s only consumer (`measure()`)
discards it via `_`, so there is no currently-observable symptom.

### INFO — coverage.py otherwise clean
Read start to finish, including the classifier-version cache-busting scheme (`_CLASSIFIER_VERSION`,
`_so_load`'s discard-and-recount logic), the 4-attempt retry on the host map load with its
fail-closed `SystemExit` on persistent failure, and `_empty_state`'s CITED/READ/NO PAGE/UNREACHABLE
classification against `feats.CLEAN_NEGATIVES`. No further findings.

## src/deprecated/catalogue_local.py (333 lines, read in full)

Read start to finish, including the code after the unconditional refusal (dead by construction —
the module-level `raise SystemExit(_REFUSAL)` fires before any of `main()`/`catalogue_source()`/
`call()` can ever run, whether the module is run directly or imported). Confirmed the `--help`
exemption is real and narrow (`set(sys.argv[1:]) & {"-h","--help"}` before any other work) and
matches `allsweep.check_import`'s actual mechanism, which is a **subprocess** invocation
(`subprocess.run([PY, path, "--help"], ...)`, verified by reading `allsweep.py:307-318`) — so the
module's claim that "importing this module stops as hard as running it" is accurate for every real
caller in the tree today (nothing does a literal in-process `import` of it). This file's own dead
code beyond the refusal is marked kept-on-purpose ("The file is kept as the record of a failure
mode... repairing it would make it look usable again") — noted and not re-litigated per the brief.
Only finding is the shared stale line-count citation reported under silence.py above.

## src/propagation.py (254 lines, read in full, and exercised live)

Read start to finish and run three ways against the live `data/SHARED_STAGE_GRAPH.json`
(`--from "Left 4 Dead" --to "Dragon Ball Z"`, `--from "Xanathar's Guide to Everything" --to "DMs
Guild: Heroes of Hell"`, and the bare default survey). Both specific numeric claims embedded in the
module's own comments (197 shelves / 3,753 edges; Left 4 Dead → Dragon Ball Z distance 1.126; the
graph diameter 4.9933 between the two named D&D shelves) matched the live output exactly — these
comments are accurate today, not stale. Traced `observed_mark`'s claimed-unreachable trailing
`return 0` by hand against `ascension_years(1) == 0.0`, confirmed it is indeed unreachable as
documented.

### QUESTION — ascension marks are effectively binary (0 or 17) for any realistic arrival delay
**Where:** src/propagation.py:83-86 (`YEARS_PER_UNIT_DISTANCE = 1000.0`, `RUNG_COST_EXPONENT = 1.35`)
interacting with :153-184 (`observed_mark`).
**What:** `ascension_years(rung)` ranges from 0 (rung 1) to only ~44.8 years (rung 17,
`17**1.35 - 1`), while `arrival_years(distance)` for any two shelves sharing little furniture runs
into the hundreds or thousands of years (the default survey prints arrivals of 175-1,126 years for
its six sample pairs). Since `observed_mark`'s loop checks `rung = 17` first and
`ascension_years(17) ≈ 44.8`, any `lag` (years-since minus arrival delay) that clears zero at all
almost always already clears 44.8 too, so the function returns either 0 (not yet arrived) or 17
(fully ascended) — verified live: none of the six default-survey probes ever showed an intermediate
mark [^1]-[^16] at the sampled years (100/500/1500).
**Why this might be worth asking about, not fixing:** this may be exactly the intended physics
(local ratification is fast; only the courier delay is slow), but it means the charter's 17-rung
Ladder is, in this module's numbers, doing very little work — an entry can really only ever cite
"hasn't heard yet" or "long since fully absorbed," never a plausible mid-ascension state, unless the
sampled year happens to land inside a narrow ~45-year window right after arrival. Reporting as a
question since I have no way to confirm whether that binary behaviour matches the owner's intent
for the Chain of Record.
**Confidence:** derived from the constants directly and confirmed against the live default-survey
output; not a code defect, a numeric-consequence observation.

## src/compress_store.py (149 lines, read in full)

Read start to finish, including the temp-name-with-pid-and-thread write path, the guarded
`os.unlink(tmp)` cleanup on a denied replace, and `load()`'s content-hash verification against the
filename it was stored under (`_address_in`). No findings — this module is short, the atomic-write
and verify-on-read logic is internally consistent, and I could not find a gap between what its
comments claim and what the code does.

---

## Summary of findings by severity

- MAJOR (flagged as QUESTION): 1 — overnight.py prose gate treats a non-running safety drill the
  same as a clean one.
- MINOR: 4 — ingest_doc.py stale CHUNK-parity comment; silence.py (+ catalogue_local.py) stale
  line-count citation; chain.py OUTCOME regex misses "beats"/"beating"; coverage.py READ-candidate
  np overwrite (currently inert).
- QUESTION (design, not filed as a defect): 1 — propagation.py's effectively-binary ascension marks.
- INFO / clean-with-what-was-checked: overnight.py (aside from the flagged item), silence.py,
  chain.py (aside from the regex), ingest_doc.py (aside from the comment), reference.py,
  coverage.py (aside from the np overwrite), catalogue_local.py, compress_store.py.
