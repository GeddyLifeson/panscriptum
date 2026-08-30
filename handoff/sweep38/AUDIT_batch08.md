# SWEEP 38 — AUDIT, batch 08

Agent: `sweep38-batch08`. Nine modules, 4,568 lines, all read in full. No file under `src/` was
edited. Reproductions were run with `C:/Users/imarl/miniconda3/python.exe` out of the batch's own
scratch directory.

| module | lines | verdict |
|---|---:|---|
| magnitude.py | 1707 | 4 findings (1 MAJOR published-data cap, 1 MAJOR path divergence, 1 MAJOR print cap, 1 MINOR) |
| completeness.py | 709 | 2 findings (MINOR, INFO) |
| codewatch.py | 554 | 2 findings (MAJOR test-coverage gap, INFO) |
| policy.py | 429 | 2 findings (both MINOR) |
| tiers.py | 367 | 3 findings (MAJOR fail-open, MINOR, INFO) |
| entity_match.py | 296 | read in full, nothing found |
| style_audit.py | 231 | 2 findings (both MINOR) |
| roll.py | 144 | read in full, nothing found |
| repass_bands.py | 131 | 1 finding (MINOR) |

---

## magnitude.py — read in full (1,707 lines)

### MAG_WORKSHEET_CUT — MAJOR — the published worksheet and the stored rejection list are cut

`assay_entity` writes the instrument worksheet line as

    sheet[ax] = f"INSTRUMENT {q['measured']} = {q['si']:.3g} SI  <- {q['feat'][:120]}"

`sheet` is what reaches `A.assay(worksheet=sheet)` and is published on the record. The model path
in `verify()` writes `f"[{hit}] {text}  ({page})"` — the WHOLE sentence, plus the page. So the
strongest evidence class in the instrument (Instrumented, above Transcribed on the Attestation
ladder) is the only one whose published citation is truncated, and it is also the only one that
loses its page.

Measured against `data/ASSAYS.json`: **31 of the 51 published `INSTRUMENT` worksheet lines are
exactly 120 characters long** — i.e. cut mid-word, no marker.

The same slice runs through the stored `rejections` list at four sites (`quantity_scores`
`sentence[:60]`, `verify` `text[:60]` twice, `_split_gate` `source[:60]`). **574 of the 607 stored
rejection lines that quote a feat are exactly 60 characters long.** A rejected feat is not recorded
anywhere else on the record, so the refusal's evidence exists on disk only as its first 60
characters.

### MAG_SPLIT_STATUS_COLLAPSE — MAJOR — the default path throws away `none` and `n/a`

`verify()` (one-shot/local) maps a model status onto `A.NONE`, `A.UNESTIMABLE` or
`A.INAPPLICABLE`. The split path does not, in two places:

* `_split_assay._one_axis`: a string score falls to `elif best is None: best = (A.UNESTIMABLE, "")`
  — the model's own `n/a` or `none` is discarded before the gate ever sees it;
* `_split_gate`: the `else` branch assigns `A.UNESTIMABLE` with no mapping at all.

`assay.py:930` removes `INAPPLICABLE` from the coverage denominator and keeps `UNESTIMABLE` in it,
and `NONE` earns full coverage credit. Split is the DEFAULT for anything over `ONE_SHOT_MAX`, i.e.
the heaviest and best-documented entities. Reproduced (same anchor, same numeric scores, only the
statuses differing between the two paths):

    one-shot (statuses preserved)   𝔄 M4.46 ± 0.20   coverage 0.42
    split    (all UNESTIMABLE)      𝔄 M4.56 ± 0.21   coverage 0.25

and `_split_gate({"acumen": {"score": "n/a"}, "vector": {"score": "none"}}, ...)` returns
`{'acumen': 'unestimable', 'vector': 'unestimable'}`.

The published decimal differs, not just the interval.

### MAG_ONE_PRINT_4K — MAJOR — `--one` prints `[:4000]`

`main()`: `print(json.dumps(r, indent=1, ensure_ascii=False)[:4000])`. Measured over the 507
records on disk: **148 (29.2%) exceed 4,000 characters**. The cut lands mid-string, so the output is
not parseable JSON, and on the largest record (`warhammer.fandom.com|Horus Lupercal`, 9,533 chars)
the keys never reached are `rejections`, `candidates`, `quantities_seen`, `prompt_chars`,
`evidence_dropped_to_fit`, `transport`, `pages` — the refusal list among them, which is the main
thing `--one` exists to show.

### MAG_ONE_NO_CEILING — MINOR — `--one` runs unclamped

`run_batch` passes `ceiling=host_ceiling(h)`; `main()`'s `--one` calls
`assay_entity(config(), a.one[1], a.one[0])` with no ceiling. `host_ceiling`'s own docstring records
what that costs: "Jace Beleren came back at M10.77 against the charter's published 𝔄 M2.88, and
Silver Surfer at M10.93". `--one` is the hand-check path, so it is the one most likely to be read as
authoritative.

### Read and found sound
`pool_ready` (resolve-once), `_resolve_citation` and its exactness-first ordering, `subject_refusal`
guards a–d and its openly-declared pronoun limit, `slice_census`, `compose`'s round-robin budget,
`settled()`, `calibrate()`'s checkpointing and `_published`, `queue()`'s `search()` fix,
`run_batch`'s `unlanded` tally, and the `--calibrate` exit code (`== len(BENCHMARKS)`). `queue(limit)`
and `candidates(cap)` are opt-in parameters, not defaults, and `candidates` is never called with a
cap — consistent with Hard Rule 0.

---

## completeness.py — read in full (709 lines)

### COMP_PHANTOM_PROBE_FAILURES — MINOR — 8 failures against 0 probes run

The unreachable-host branch calls
`_unmeasured(src, host, "host unreachable: ...", probe_failures=len(probes))` and `_unmeasured`
defaults `probes_run=0`. The row therefore says eight probes failed while zero were run — and the
whole point of that branch, stated in the comment above it and asserted by
`verify_math.py:1511` ("its probes_run is honestly zero"), is that the host is deliberately NOT
probed. On disk right now, **196 of the 216 rows in `data/COMPLETENESS.json` carry
`probe_failures: 8, probes_run: 0`** — 1,568 transport failures that never happened.
`verify_math` checks `probes_run` for this case and does not check `probe_failures`.

### COMP_CATEGORY_SIZE_DEAD — INFO — dead function, and a docstring about callers that do not exist

`category_size()` has zero callers anywhere in `src/` (grep: only its own `def` and three docstring
mentions). Its closing line — "`category_size` stays as it was for every caller that only wants the
number" — describes a set of callers that is empty. `liveness.py` already reports it
(`completeness.py:197 category_size()`).

### Checked and clean
`_cs_put`'s lock-and-snapshot, `land()`'s three guards plus the gated `write_json`,
`host_reachable`'s three-mode answer, `wiki_host`'s sentinel refusal, the `todo` union of hosts and
records. The `--top 40` print cap is declared on the following line ("rows printed: N of M (the
file holds every row)") and the unreliable rows are printed in full below it, so it is not a Hard
Rule 0 breach. `coverage: 0.0` on an unmeasured row is a positive claim about an unmeasured thing,
but both consumers (`foreman._catalogue_batch`, `catalogue_web --shortfall`) skip on
`if c.get("unreliable")` first, so nothing misreads it today — recorded here rather than filed.
`catalogued_counts`'s `[:40]` on the category key cannot change any `startswith("Persons")` sum.

---

## codewatch.py — read in full (554 lines)

### CODEWATCH_BUDGET_UNTESTED — MAJOR — both budget tests aim at code no daemon runs

Since the run #36 fix, `exit_if_stale` enforces the budget through
`_claim_restart_slot` → `_take_locked(who, enforce=True)`. The two harnesses that watch the budget
both point somewhere else:

* `drill.py:4966-4984`, net "source-change restarts are budgeted per job per hour", drives
  `_budget_left` — and its docstring still says "`exit_if_stale` reads `left <= 0`", which stopped
  being true when `_claim_restart_slot` was written;
* `verify_math.py:6165-6191`, check `d99b11ec050e`, hammers `_record_restart` for the shared-ledger
  race.

`_budget_left` and `_record_restart` have no production caller left; the only code path that can
actually refuse a restart is covered by neither. The fail-closed-on-denied-write behaviour
(order f06ba4c82363) and the check-and-take atomicity are the two properties the run #36 fix
added, and no net observes either. This is the doctrine's own PROVEN property missing on the
guard that was just repaired.

### CODEWATCH_JOINED_LINE — INFO — an eaten newline

Line 204 is a single statement carrying a run of ~16 spaces where a line break used to be:
`return os.path.normcase(...) ==                os.path.normcase(...)`. Valid Python, over the line
budget, and the exact shape the module tree's `_BAD_CHARS` guard exists to catch a harsher version
of.

### Checked and clean
`fingerprint`'s None-is-not-unchanged contract, `quiet_seconds` and its stamp corroboration in
`stale()`, `runs_script`'s purity and its three named false-positive cases, `twins`' additive
self-exclusion, `claim_singleton`'s exit-0 and fail-open, `_ledger_lock`'s `O_CREAT|O_EXCL` and its
stale-lock steal, and the two distinct refusal reasons in `exit_if_stale`. `escalate("MANAGER", ...)`
as a string is accepted by `escalation.escalate` (name lookup added deliberately) — not a fault.
`stamp(who="?")` never reads `who`; harmless, not filed.

---

## policy.py — read in full (429 lines)

### POLICY_OBSERVED_CUT — MINOR — the observed value is stored `[:120]` with no marker

The module's stated purpose is "**it records the OBSERVED VALUE of every rule, every run**", and
`check_rule` stores `repr(value)[:120]` on both the normal and the error return. A long list or a
long string is cut mid-repr with nothing saying so, in the one field the module exists to preserve.
The console renderers already trim independently (`r["observed"][:34]`), which is where a display
cap belongs — `workorders.file_order`'s own comment makes exactly this argument about the queue.

### POLICY_REPORT_RC — MINOR — the report's landed verdict is not in the exit code

`report()` returns whether the atomic replace landed and says so on stderr; `main()` calls it
positionally and drops the result, then `return 1 if failed else 0`. A run whose rules all pass but
whose report did not land exits 0, leaving `state/policy_report.json` holding an earlier run's
`evaluations`, `at` and `scope` — which is precisely the stale-scope failure the `scope` block was
added after. Same shape `completeness.land` and `roll.exclude` already gate on.

### Checked and clean
`resolve`'s (value, found) split, `TYPES` as a closed set, the `BadRule`-at-load ordering ahead of
the `except`, the `absent`-only vacuous exemption, the unreadable-record accounting, the
whole-corpus default with `--limit` labelled PARTIAL in both the print and the stored scope, and the
uncapped FAIL/VOID listings. `ok = False` on line 123 is dead (the next statement returns) —
cosmetic, not filed.

---

## tiers.py — read in full (367 lines)

### TIERS_GROUNDINGS_FAIL_OPEN — MAJOR — an unreadable GROUNDINGS.json publishes "ungrounded" for every shelf

`chart()`:

    except Exception:
        silence.note("tiers.py:248")
        _groundings = {}

With `_groundings == {}`, `xenoverse_grounding` finds no votes for any group and returns
`best = "ungrounded"` for all of them, and `hyperverse_of` returns the `ungrounded` index for every
source. `chart()` then writes `data/TIERS.json` with `hyperverse: 5` and
`hyperverse_type: "ungrounded"` on every row, and `main()` prints "wrote ...". That file is read by
`address_space.py` **at import** (`address_space.py:129`) and its widths are derived from it, so an
unreadable input file becomes a positive published cosmological claim about all 209 shelves. This is
the "unreadable file cached as empty" shape on a file that is written today (`data/TIERS.json`,
2026-08-29 22:56). The module's own doctrine elsewhere — "H stays '?' ... the Custodes considered
guessing a form of lying" — is the argument against it.

### TIERS_WRITE_RC — MINOR — `main()` returns 0 after "WRITE DENIED"

`ok = silence.write_json(...)` is computed, printed as `WRITE DENIED: ... did not land this round`,
and then `return 0`. The verdict exists and is discarded by the exit code.

### TIERS_NOTE_LINENO — INFO — a silence key that is a line number

`silence.note("tiers.py:248")` is correct today and will be wrong after the next edit above it.
Every other note in this tree is keyed by what failed (`magnitude.py:pool_ready`,
`completeness.py:category_size`); this one should be `tiers.py:groundings-read`.

### Checked and clean
The `CUTS` monotonicity asserts, `MULTIVERSE_THRESHOLD` vs the metaverse cut, `deliberate_joins`
returning the WHOLE shared list (the run #27 Hard Rule 0 fix holds), the containment audit in
`main()`, and the unaddressed-shelf listing, which is printed in full. The module asserts at import
time (stripped under `-O`), but nothing here runs under `-O`.

---

## entity_match.py — read in full (296 lines)

Read in full, nothing found. `qualifier_compatible` is the absolute gate the header claims and is
never overridden by a score; `candidates()` has no default cap and flags `truncated` when a caller
opts into `limit`; both early exits carry the full return shape (the fix `tempus.py:94` records);
the sort is deterministic; `best()` refuses a WEAK hit. `similarity`'s rapidfuzz note is a measured
rejection, not a stale comment. `embed_available` has no caller, but its own docstring declares it
as a closed seam and `liveness.py` already lists it; not filed.

One imprecision, too small to file: `candidates`' docstring says "Returns a list of
{name, score, reason} ... plus the reason" where the function returns a dict whose `matches` key
holds that list.

---

## style_audit.py — read in full (231 lines)

### STYLE_SELFTEST_BLIND — MINOR — the self-test passes with the shape detector fully broken

`--self-test` asserts `ok = (a["banned"] and max(a["shapes"].values()) >= 2)`. Reproduced by
monkey-patching `opener_shape` against the module's own fixture:

    as shipped                              ok = True   shapes {'NAME is a city': 2, 'NAME is not merely': 1}
    opener_shape() -> '' for every entry    ok = True   shapes {'': 3}
    opener_shape() -> unique per entry      ok = False  shapes {3 singletons}

The degenerate detector not only passes, it reports MORE repetition (3) than the working one (2) —
and over-collapsing is the exact failure `opener_shape`'s own docstring records ("reported 27%
repetition where there was none"). There is also no negative control: a detector that flags
everything passes. Remedy: assert the specific expected shape strings rather than a max count, and
add a second fixture of three deliberately varied entries that must come back with no banned tell
and no shape collision.

### STYLE_REPORT_CAPS — MINOR — printed rankings cut with no remainder

`report(a, top=8)`: OPENING SHAPES `.most_common(8)`, EXACT OPENERS `.most_common(8)`, MACHINE TELLS
`[:14]`, VOCABULARY `.most_common(10)`. The tells list declares its remainder
(`({len(a['banned'])} distinct tells present)`); the other three do not, and this is the report a
person reads to decide whether the corpus is converging. `repass_bands.py` already carries the house
idiom for this ("showing X of Y; Z more not shown").

### Checked and clean
`TURN_ENDING`'s `\Z` anchor and the reasoning for it, the single-codepoint `entries()` split,
`opener_shape`'s NAME collapse, `TEMPLATE_WORDS`, and `_WATCHED` — verified against `tells.scan`,
which does compile and scan `ALL_PATTERNS`, `LEXICAL` and `LEXICAL_FICTION`, so the "N patterns
watched" figure is honest.

---

## roll.py — read in full (144 lines)

Read in full, nothing found. `exclude()`'s `caller_supplied` split now honours "work on my copy" on
the write as well as the read, the required note is enforced, a missing name raises rather than
returning the ambiguous False, and `write_json`'s verdict is returned. `in_scope`'s fail-open is
declared and argued. `main()`'s `why[:150]` and `name[:45]` are display trims in a two-line-per-row
listing; the reasons on the live roll are all well under 150 characters, so nothing is being cut
today — noted, not filed.

---

## repass_bands.py — read in full (131 lines)

### REPASS_DENIED_RC — MINOR — "APPLIED. N rewritten" alongside uncounted denials

The write is correctly gated (`if PL.write_record(path, rec)`) and a denial prints
`WRITE DENIED <src>; left as it was` — but the denial is not counted, does not appear in the closing
summary, and `main()` returns 0 either way. A run that demoted 400 entries and landed 350 of them
prints "APPLIED. 350 record files rewritten." and exits clean; the 50 records still carrying an
unearned Magnitude are visible only as scrollback. Remedy: count the denials, print them beside the
APPLIED line, and return non-zero when any write was refused — the same treatment `completeness.land`
gives the identical failure.

### Checked and clean
The survivors listing carries its "showing X of Y; Z more not shown" remainder (order 89fc2eaf23f1
held). The DEMOTED `[:8]` is labelled "a sample of" and its total is printed two lines above it
(`demoted to unassayed: N`) with a per-band breakdown, so the reader can see how much is off the
page — not filed, though the survivors' idiom would read better there too.

---

## Questions, not findings

1. **completeness.work(): genuine absence still returns `None` and drops the row.**
   `if not sizes and failed == 0: return None`. The comment argues this is deliberate ("every probe
   answered, none of the categories exist"), but the same function's own reasoning two paragraphs
   up is that an absent row reads downstream as "this source has no wiki presence". The two readings
   are: (a) a source whose wiki genuinely has none of the eight probe categories has nothing to
   measure and should not occupy a row; (b) it is exactly the `_unmeasured` case with a different
   cause, and dropping it makes it indistinguishable from a source that was never in the audit at
   all. Filed as a question at OWNER because it is a call about what the "every source is fully
   catalogued" standard is supposed to measure.

2. **magnitude `_split_assay`: an axis with no candidate rows returns UNESTIMABLE.**
   `_one_axis` returns `A.UNESTIMABLE` for `not rows`, which keeps the axis in the coverage
   denominator. For a place, an institution or a treasure, "no acumen candidates" may be a category
   error (`n/a`, out of the denominator) rather than an open question. Related to
   MAG_SPLIT_STATUS_COLLAPSE but a separate judgment about what silence means, so it is not folded
   into that order.
