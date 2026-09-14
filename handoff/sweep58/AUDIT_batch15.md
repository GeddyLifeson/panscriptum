# Sweep 58 — Audit batch 15

Modules read in full, top to bottom (offset-paged where needed):

| module | lines |
|---|---|
| local_agent.py | 1650 |
| escalation.py | 1445 (LIVE MUTATION TARGET — read only, never mutated) |
| threads.py | 993 (Agent R editing concurrently, order 9245eb5f6f76) |
| ingest_doc.py | 678 |
| prose_gate.py | 537 (LIVE MUTATION TARGET — read only, never mutated) |
| burgs.py | 442 |
| wh40k.py | 350 |
| tuning.py | 286 |
| lognames.py | 52 |

Open queue checked first via `workorders.open_orders()` (703-line dump), before any module was
read, so findings below are cross-referenced against it.

---

## prose_gate.py

### DEFECT MINOR — missing the project's own eaten-regex-escape guard, in a regex-heavy safety gate

Every module that uses `re` in this tree (52 of them — feats.py, threads.py, endpoint.py,
publish.py, local_agent.py, ingest_doc.py, wh40k.py, tuning.py, … ) opens with:

```python
_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")
```

threads.py's own comment calls this "this project's oldest bug; every module carries the guard."
`prose_gate.py` imports `re` and defines six compiled patterns central to Hard Rule 3 enforcement
(`_AXIS_RE`, `_INSTRUMENT_MARK`, `_INSTRUMENT_NOT_APPLICABLE`, `_INSTRUMENT_UNINSTRUMENTED`,
`_CLASS_LINE`, `_AXIS_LABEL`) but carries no such guard anywhere in the file.

**Failure scenario:** if a transfer or edit tool eats a control character out of one of these regex
literals — the exact class of corruption the guard exists to catch — `unearned_instrument`,
`instrument_shortfall` or `assert_instrument_present` could silently stop matching real axis lines
or Instrument markers. These are the FAIL-CLOSED checks built specifically to catch the
2026-08-25 incident's two headline symptoms (fabricated axis scores, missing Instrument sections);
a silently-broken regex here is a silent fail-open in the one module whose whole job is to prevent
that class of incident.

**Remedy:** add the same six-line guard, verbatim, near the top of `prose_gate.py`, matching the
other 52 modules. (Not applied — this file is a live mutation target and read-only for this audit.)

Checked against: `escalation.py`, `burgs.py`, `lognames.py` are the other three modules missing
this guard, but none of the three imports `re` at all (confirmed by grep — no `import re`, no live
`re.` calls, only prose mentioning `re.search` in comments), so their omission is consistent and
not a finding.

### Nothing else found in prose_gate.py

Read in full. `gate_open`/`step4_gate_open`/`floor_ok`/`evidence_ok` all fail closed correctly
(floor-has-a-floor, unmeasured-source refusal). `section_shortfall`/`assert_block_complete`'s
ghost/extra accounting is internally consistent (both charged into the denominator, per the
2026-08-28 fix recorded in the file itself). `instrument_shortfall`'s being/non-being branching
was traced against its own docstring term by term and matches. `cited_names_for`/
`unearned_instrument` fail closed on an unreadable host map or cache. No new console-cap,
lost-update or tautological-check pattern found.

---

## threads.py

### KNOWN 5a0f3925442a (THREADS_VERIFY_SKIPS_T3) — appears RESOLVED, not still accurate

The order says `verify()`'s edge loop covered T1/T2 only and never visited T3. Current `verify()`
(lines ~760-767, 789-812, 825-832) now reads `annex_codes()` and checks every T3 edge's `class`,
`from` and `to` against it, plus a fail-closed refusal ("the Chronica Annex address space could
not be read... refusing rather than passing them unchecked") when T3 edges exist but the Annex is
unreadable. This matches remedy option 1 in the order text and the brief's own note that
"threads.verify: now checks T3 against annex_codes()". Recommend closing 5a0f3925442a.

### KNOWN 9245eb5f6f76 (THREADS_ANNEX_JOIN_SILENT_PATHS, Agent R's concurrent order) — appears RESOLVED in the copy read

Both silent paths the order names look closed in the code as I read it:
1. `annex_join()` (lines 289-329) now distinguishes absent (`FileNotFoundError` → `{}`, noted) from
   unreadable/malformed (raises `AnnexJoinUnreadable`, which `build()` does not catch — it
   propagates as a `ThreadRefused` subclass, caught by `main()`'s `except ThreadRefused`).
2. `build()` (lines 611-628) now reports every join key with no matching source under
   `annex_join_unmatched`, uncapped, and `main()` prints all of them (lines 953-956).

Since Agent R may still be mid-edit on this file, I report this as KNOWN/apparently-resolved
rather than asserting it closed.

### DEFECT MINOR — `annex_join()` validates the join's top-level shape but not each source's entries, so a malformed per-source value crashes `build()` uncaught

`annex_join()` validates that `doc["join"]` is a dict, but not that each value in it is a list of
edge-dicts. `build()` then does:

```python
event = [edge(e["to"], "T3", e["why"], code, known)
         for e in joined.get(src, ())]
```

**Failure scenario:** if `data/ANNEX_JOIN.json`'s `"join"` object ever maps a source that IS in the
corpus to something other than a well-formed list of `{"to":..., "why":...}` dicts — e.g. a bare
string, or a list containing a non-dict item — `e["to"]` raises `TypeError: string indices must be
integers` (iterating a string yields characters). This is not a `ThreadRefused`, so `main()`'s
`except ThreadRefused:` (around line 894) does not catch it, and the module's own "REFUSING TO
DERIVE — ..." contract is broken by a raw traceback instead.

Not known to be reachable today — the builder of `ANNEX_JOIN.json` (outside this batch) is
documented as verifying every `why` before writing — but `annex_join()` already hardens the
absent-vs-unreadable distinction one level up and stops one level short of doing the same for the
per-source shape it hands to a caller with no further checking.

**Remedy:** inside `annex_join()`, validate each value under `join` is a list of dicts each
carrying `to`/`why`, raising `AnnexJoinUnreadable` on a violation — the same fail-closed shape the
function already uses for the top-level object.

### QUESTION — `annex_codes()`/`law_codes()`: the declared-count cross-check is skipped when `declared == 0`

```python
declared = ((doc.get("declared") or {}).get("canons"))
if declared and len(out) != declared:
    ...
    return set()
```

`declared and ...` is false when `declared == 0`, so a file whose `declared.canons` is (corruptly)
0 but whose `canons` list actually parses to N > 0 entries would NOT be flagged, defeating the
purpose of the declared-count self-check. Same "falsy zero" shape this project has repeatedly
fixed elsewhere (`burgs.burg_count`'s old `--limit 0` bug, `hostcheck`, `binding_health`), but I
could not construct a plausible way for a real charter's declared Canon/Law count to legitimately
be 0, so this is filed as a QUESTION rather than a DEFECT.

### Nothing else found

`edge()`, `_resolves`, `category_path`, `cohort_family`, `build()`'s cohort/T2 construction,
`counts()`, `threads_for()`, `recorded_pairs()` and `main()` were all traced against their own
docstrings and each other; no new tautology, cap, or lost-update pattern found. The `parts[:2]` in
`cohort_family` is the one documented `[:n]` in the file and is address decomposition, not a
listing cut, per the module's own header note.

---

## escalation.py (live mutation target, read only)

### KNOWN escalation.py:303, :1297, :1324, :1379 — MUTANT_SURVIVED_ESCALATION_L303/L1297/L1324/L1379 (orders befe73801f6f, 17242f0e3f39, aa9522fcec35, 3c85cdc4e5ee)

All four line numbers match the current file exactly as the orders describe:
- `:303` `if not recorded:` (the ESCALATION NOT RECORDED stderr branch)
- `:1297` `return isinstance(cur, dict) and bool(cur.get("cleared", False))` (`_halt_file_cleared`)
- `:1324` `return False, "raised"` (`_land_halt`'s exception arm)
- `:1379` `ok, reason = resume_subsystem_verdict(a.resume, a.ruling, by=(a.by or "cli"))`

Still open and still accurate. Each is a branch that is genuinely hard to synthesize a real
trigger for in the battery (a real log-append failure, a real halt-file-write exception, a
malformed `--resume` caller with `a.by` falsy) rather than a code defect; I found no new evidence
narrowing the "equivalent vs. uncovered" question these orders already leave open.

### KNOWN escalation.py:409 — order 5d0fa30e4b09 item 10, already filed as a QUESTION, not re-derived

Line-based mutation attribution into a 25-80-line-docstring-heavy file "will silently remap after
any edit" — already the order's own conclusion. Not re-verified further; no new finding here.

### Nothing else found

Read in full (1445 lines, four sequential offset reads). `_halt_lock`'s FAIL-OPEN is a documented,
ruled-on design decision (owner ruling 2026-09-08), not a defect. The CAS loops in `_raise_halt`,
`stop_subsystem`, `resume_subsystem_verdict` and `clear()` all take their digest before the read,
matching the project's own stated discipline. `_by_a_person_at_the_cli`'s `sys._getframe(2)`
frame-counting was traced against both call sites (`clear()` and `resume_subsystem_verdict()`
called directly from `main()`) and is consistent with its own docstring in both directions. No new
fail-open, tautology, or cap found.

---

## ingest_doc.py

### DEFECT MINOR — absent and unreadable `ingest_state.json` are treated identically, silently restarting a multi-hour mining run from chunk 0

```python
try:
    with open(state_p, encoding="utf-8") as f:
        state = json.load(f)
except Exception:
    silence.note("ingest_doc.py:ingest-state")
    state = {"next": 0, "found": 0}
```

**Failure scenario:** a present-but-corrupt `ingest_state.json` (a torn read, an AV lock, hand
inspection gone wrong) is read exactly like "no prior run" and the resume cursor silently resets
to chunk 0 — for a book this module's own comments describe running to hundreds of chunks and up
to ~5 hours of napping through transport misses. Because `known` is rebuilt from the record on
every run (not from `state`), no duplicate entries would land — so the cost is wasted model calls,
time and (on the cloud arm) money, not corrupted data. This is the same absent-vs-unreadable
conflation this project has repeatedly treated as a defect elsewhere: `threads.annex_join` (order
9245eb5f6f76, this same batch) and `endpoint.source_pages` (order 54db4a3baec8, agent R's
territory) both draw exactly this line for exactly this reason.

**Remedy:** distinguish `FileNotFoundError` (absent — `{"next": 0, "found": 0}` is correct) from
any other exception (unreadable — refuse and ask the operator to inspect/repair the file, per
`endpoint.register`'s own precedent, rather than silently re-mining from scratch).

### Nothing else found

Read in full. The chunk-splitting re-derivation (oversized-page re-split), `record_path`'s
ambiguous-match refusal, the `write_record_catalogue`-verdict-driven cursor rewind on a denied
write, and the `landed_found`/`state["found"]` bookkeeping were all traced against their own
extensive in-file commentary and are internally consistent. `extract()`'s pages.json write is NOT
gated behind `_assert_not_halted`, but the module's own docstring for `_assert_not_halted`
explicitly reasons through this as a deliberate, narrower scope ("Extraction ... [is a]
MEASUREMENT ... Whether the whole module should be gated is an owner question, not one this module
may settle") — already a self-documented open question, not re-filed here.

---

## burgs.py

### KNOWN 0182eb4ff49c (SMALL_DEFECTS_SWEEP57), the burgs.py half — appears RESOLVED, not still accurate

The order says the owner-ruled marking comment for the unreachable `"primitive"`/`"settled"` dict
keys (order 40e98eed6870) "was never written." Current code carries it in full: lines ~125-129 in
`burg_count` ("the 'settled' entry here is the same unreachable-key marking as largest_city's
below (owner ruling 2026-09-08...)") and lines ~134-141 in `largest_city` ("UNREACHABLE KEYS,
MARKED NOT DELETED (owner ruling 2026-09-08, question 1... order 40e98eed6870...)"). The
rosetta.py half of that same order was not checked — rosetta.py is outside this batch.

### QUESTION — `main()`'s `--write` path never calls `escalation.assert_clear()`

Neither `burgs.py` nor `wh40k.py` (below) checks the plant-wide halt before writing its artifact.
Flagged as a QUESTION rather than a DEFECT: both artifacts are documented as fully regenerable
from a world's seed with no downstream reader (burgs.py's own comment: "Nothing in the tree reads
this artifact at all"), which parallels the reasoning `ingest_doc._assert_not_halted`'s own
docstring gives for narrowing its own gate to two specific files and leaving extraction ungated —
an explicit, in-code acknowledged trade-off elsewhere in this same batch, not obviously an
oversight here.

### Nothing else found

Read in full. `burg_count`/`largest_city`/`class_histogram`/`_rank_at_or_above`/`burgs_for`'s
`--limit` handling (uncapped by default, floors and narrows correctly on 0 and on over-large
values) all match their own extensive documentation of prior fixes. The per-designation list
(not dict-overwrite) in `main()`, and the numerator/denominator-from-the-same-pass fix for the
class-histogram percentages, were both traced and are consistent.

---

## wh40k.py

Read in full. `compute()`'s per-axis provenance tagging (`wiki`/`canon`/`unattributed`),
`_provenance`'s default-to-unattributed, and `main()`'s gated, verdict-checked atomic write were
all traced against their own documentation of prior fixes (the blanket `[wiki]` stamp bug, the
`[:56]`-cut-mid-quotation bug, the discarded-write-verdict bug) and are consistent with it.

Same QUESTION as burgs.py above applies (no `assert_clear()` before the write) — not repeated as a
separate finding.

Nothing else found.

---

## tuning.py

Read in full. `regime()`/`profile()`/`workers()` all match their own documentation: the
cached-`buckets`-vs-freshly-read-buckets bug is fixed (workers derive from the same `_CACHE`
reading that produced the label), and `workers(requested=0)` is correctly treated as a real
request rather than falling through to the profile count (the docstring's own worked example).
No writer in this module, so no halt-check question applies. Nothing found.

---

## lognames.py

Read in full (52 lines, all constants and commentary). Nothing to find — no logic, no writes, no
regex.

---

## Summary counts

- DEFECT MINOR: 3 (prose_gate.py eaten-regex-escape guard; threads.py `annex_join` malformed-value
  crash; ingest_doc.py absent-vs-unreadable state file)
- QUESTION: 3 (threads.py `declared == 0` falsy check; burgs.py/wh40k.py missing `assert_clear`
  before `--write`, counted once)
- KNOWN: 6 (escalation.py ×4 survived mutants at :303/:1297/:1324/:1379; escalation.py :409 stale
  citation; threads.py 5a0f3925442a — resolved; threads.py 9245eb5f6f76 — appears resolved;
  burgs.py 0182eb4ff49c half — resolved)

No caps applied to this list — every finding from this batch is above.
