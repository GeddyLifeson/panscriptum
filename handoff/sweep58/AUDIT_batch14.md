# Sweep 58 — Batch 14 audit

Modules read in full (top to bottom, paging large files):

| module | lines |
|---|---|
| src/read.py | 1670 |
| src/health.py | 1318 |
| src/allsweep.py | 1024 |
| src/weave_index.py | 721 |
| src/policy.py | 582 |
| src/sevenfold.py | 441 |
| src/deprecated/catalogue_local.py | 333 |
| src/resonance.py | 298 |

Open queue checked first via `workorders.open_orders()` (458 open orders at time of read) and
cross-referenced against every finding below before it was written up as new.

---

## src/health.py (1318 lines)

This shift's rewrite lands `health.reopen_stranded`'s write through `_cas_land` (health.py:1159:
`ok, why = _cas_land(path, st, seen, indent=1, sort_keys=False)`), where `seen` is the digest taken
*before* the initial read (health.py:1033) — confirmed by reading the function end to end.

**KNOWN 26667ecd6543 (STATE_LOST_UPDATE) — NO LONGER ACCURATE, appears fixed.** The order's claim
is that `pipeline.save_state` whole-object-dumps PIPELINE_STATE.json and silently reverts any
concurrent edit from `health.reopen_stranded`, which CAS's its own write but is "completely
unprotected against the pipeline's next whole-object land." Verified against current source on
both sides:
- `health.reopen_stranded` (health.py:1011-1168) re-reads the raw text, refuses if it changed
  since the initial read (health.py:1130-1137), and lands via `_cas_land` with the pre-read digest
  (health.py:1159) — a real compare-and-swap.
- `pipeline.save_state` (pipeline.py:399-…) now does compare-and-swap-with-merge-on-mismatch: "COMPARE-AND-SWAP, MERGING ON A MISMATCH (order 26667ecd6543)" at pipeline.py:414, digesting the
  file and three-way-merging (`_merge_state`) rather than dumping whole.
Both halves the order names as missing are present. Recommend closing or re-verifying 26667ecd6543
against a live concurrent-writer test before resolving it, but nothing in either function
contradicts the fix being complete.

**KNOWN 8b3f2911fa0c / 32eaec248adf (dandwiki 403-vs-"did not answer") — STILL ACCURATE.**
`check_api_paths` (health.py:726) still emits the literal string `"{fam}: probed host did not
answer"` unconditionally, even when `klass` reflects an HTTP error class (e.g. `no-api`, a 403)
rather than a true non-answer. Order 8b3f2911fa0c already names this exact line and asks that
"whoever takes (b) should fix the sentence at health.py:726" — line number still matches today.
Filed as OWNER-rung already; no new finding, just confirms it is still live.

**QUESTION — `health.py --reopen --go` never calls `escalation.assert_clear`.** `main()`
(health.py:1254-1314) writes real, if reversible, state via `reopen_stranded(dry=False)` but has
no `import escalation` / `assert_clear` call anywhere in the file (grepped). Compare `read.py`,
whose `main()` refuses to start under a standing halt (read.py:1548-1561) before doing any work.
Low confidence this is a defect rather than intentional scope: `weave_index.py` and `policy.py`
and `sevenfold.py` — all also in this batch — show the identical pattern (no escalation import at
all), so the codebase appears to draw a line between STANDING production jobs (pipeline, feats,
read, overnight, publish, ingest_doc, hostcheck, threads, foreman, overwatch, dashboard,
local_agent — all fifteen call `assert_clear`, verified by grep) and small, hand-invoked,
cheaply-re-runnable repair/report tools, which do not. Filed as a QUESTION because both readings
are defensible and it is a cross-cutting design choice, not a health.py-specific rewrite defect.

Nothing else found in health.py beyond the two KNOWN items above. Checked: the `_flush_ledger` /
`_flush_samples` CAS retry loops (digest-before-read, re-read-and-re-merge on refusal, preserve
wreck before overwrite, re-take digest after a preserve), `check_state`'s backlog-vs-loss
distinction, `preflight()`'s stamp-write gating, and `main()`'s exit-code contracts for `--reopen`
and `--preflight` — all internally consistent with their own docstrings and with each other.

---

## src/read.py (1670 lines)

**KNOWN 1d45a56ae1d8 (STALE_CITATIONS_SWEEP57) — STILL ACCURATE.** read.py:232-234's comment
cites "read.py:731" for `read_entity`'s whole-name fallback; the real fallback is the
`or [name.lower()]` clause at read.py:835 (`keys = [w.lower() for w in re.split(...) if len(w) > 3]
or [name.lower()]`). Confirmed both line numbers against current source; order's account is
accurate as filed.

Read the rest of the transport ladder (`_ask` / `_ask_ungated` / `_local` / `_local_carded`), the
per-chunk cache keying (`_chunk_key`/`_chunk_get`/`_chunk_put`), `read_entity`'s cache-completeness
contract (`if unanswered: return out`), `priority()`'s three-bucket Hard-Rule-0 fix, and `main()`'s
escalation gate and exit-code propagation. No new defects found; every historical fix's own
before/after claim was checked against the code as it stands today and held up (e.g. the
`_FELL_BACK` counter now increments only on an actual GPU answer, the cascade-mode hard-`return
None` sits ahead of the unconditional `_local` fallback, `cap_chunks` is genuinely inert with a
`silence.note` rather than silently re-introduced).

---

## src/allsweep.py (1024 lines)

**KNOWN a724ec57e0d5 (TI_DANGLING_VERDICT_STOPS_SHORT_OF_THE_LADDER) — STILL ACCURATE in
substance, its own citations have rotted.** The order's behavioural claim still holds: the
`thread integrity` row is graded `RC_FINDINGS` (allsweep.py:241), so a run where every implied
thread is DANGLING still computes `failed = False` (the `rc_means == RC_BROKEN` conjunct at
allsweep.py:398 is false for an `RC_FINDINGS` row) and the uncapped DANGLING listing is suppressed
from the console because `verifier_console_lines` is only invoked `if r.get("failed") or
r["crashed"] or r.get("timeout")` (now allsweep.py:848, not the order's cited :719-723). The
order's own line citations — "allsweep.py:181 and :719-723" — have drifted: today's equivalents
are ~allsweep.py:220-241 (the `RC_FINDINGS` reasoning block) and allsweep.py:848. This is itself a
small, concrete instance of the standing complaint in **KNOWN dc9ffadae765**
(THE_QUEUE_CITES_LINE_NUMBERS_AND_NOTHING_CHECKS_THEM) — a filed order's own `where` has rotted
since it was written. Not re-filing a new order for the drift itself (dc9ffadae765 already covers
the class); noting the fresh line numbers here for whoever next works a724ec57e0d5.

Read `Verifier`'s deliberate `__iter__`/`__len__`/`__getitem__` tuple-compatibility shim,
`run_verifier`'s halt-refusal handling, `reconcile()`'s eight independent cross-checks (source/
host/roll agreement, coverage-vs-disk, quarantine-vs-cache-directory, purge ghosts, phase
implementation, over-band ceiling, live-process roster via `overnight._proc_lines`/`_cmd_is_running`
rather than a second hand-rolled probe), `estate_faults`' fail-closed `_row_is_fault`, and `main()`'s
final `bad` count (imports + lint + verify + estate artifacts + estate findings + write-denial).
All internally consistent; no new defects found.

---

## src/weave_index.py (721 lines)

**DEFECT MINOR — missing the standard `_BAD_CHARS` transit guard, and this module has live regex
escapes that make the gap real rather than moot.** ~50 other modules in `src/` (including three
others in this exact batch: `read.py`, `health.py`, `allsweep.py`) open their own source at import
time and refuse to run if it contains a bad control character (chr(8)/(11)/(12)/(7)) — the
self-inflicted defence against "a regex escape eaten in transit," which health.py's own docstring
says has happened **six times already** in this project, each time silently (e.g. `\b` becoming a
literal 0x08 backspace). `weave_index.py` has no such guard, and unlike `sevenfold.py` and
`resonance.py` (also in this batch, also missing the guard, but which import no `re` module at
all and carry zero backslash-escape literals — confirmed by grep, so the guard would be moot for
them), `weave_index.py` genuinely has the exposure: `_STRIP` (weave_index.py:43-46, `\s+`),
`_EARTH` (weave_index.py:98, `[\w']+`), and three call sites of `re.sub`/`re.findall` with `\s`,
`\(`, `\)` escapes inside `norm()` and `designations()` (weave_index.py:141-183). `policy.py`
(also in this batch, also missing the guard) was checked the same way and cleared: it imports `re`
but every pattern it evaluates is data supplied at runtime by a rule table, and grep confirms zero
backslash-escape literals in the file's own source.

**Concrete failure scenario:** if any tool or transit step ever mangles `weave_index.py`'s `\s+`
in `_STRIP` (weave_index.py:46) into a literal control character — the exact corruption class
already seen six times elsewhere — `norm()`'s title-stripping and whitespace-collapsing would
silently misbehave. `norm()` is the sole key function for cross-source identity matching
(consumed by `weave.load_index`, `cosmology_graph`, and `thread_integrity` via
`ENTITY_INDEX.json`/`WEAVE_CANDIDATES.json`), so a corruption here degrades entity resolution
across the whole weave rather than crashing loudly.

**Mitigating factor, why this is MINOR not MAJOR/BLOCKING:** `health.check_control_chars()`
(health.py:578-587) globs `src/*.py` (non-recursive, but `weave_index.py` is top-level so it IS
covered) every preflight cycle and would eventually flag the corruption and file a MAJOR order via
`workorders.sweep_detectors`. What is missing is the fail-FAST, per-module layer every regex-heavy
sibling carries — the corpus-wide sweep is a real but later and coarser backstop, and
`weave_index.py --write` could run at least once on corrupted regexes before the next preflight
catches it. Remedy: add the same four-line guard used by `read.py`/`health.py`/`allsweep.py` (and
~47 others) to `weave_index.py`.

**KNOWN d1709d8e757d (ENTITY_INDEX_NEVER_REBUILT_STALENESS_ANNOUNCED_BUT_UNACTED) — PARTIALLY
ADDRESSED.** The order's remedy (file/refresh a RUN-rung order when the index is stale) is now
implemented: `escalate_if_stale()` (weave_index.py:522-563) is called from `main()`
(weave_index.py:576). The order's underlying complaint — nothing schedules a *rebuild* — remains
true and is said so in the code's own comment: "Nothing schedules a rebuild (weave_index is absent
from overnight.STANDING and from every foreman remedy, verified by grep)" (weave_index.py:541).
So: the escalation half is done, the scheduling half is still open. Not closing the order.

**KNOWN 2cb442afd901 (staleness threshold QUESTION) — still open, unchanged.** `STALE_HOURS = 48.0`
(weave_index.py:429) and the `behind`/`stale` split (weave_index.py:468-519) match the order's
description exactly; still an explicit, un-ruled-on threshold question, not a defect.

---

## src/policy.py (582 lines)

**KNOWN fe99e57e1993 (UNMARKED_NAME_CUTS_SWEEP44) — the policy.py portion is FIXED.** The order
cites "policy.py:323,369 `str(e)[:70]`". Grepped current file for `[:70]`: zero hits. The two
unreadable-document handlers the order is describing are now at policy.py:356-363 (record read
failure) and policy.py:377-382 (coverage read failure), and both now store the full, uncapped
`"%s: %s" % (type(e).__name__, e)` with no truncation — matching the `_observed()` helper's own
discipline one function above, which is exactly the fix the order asked for. The order bundles nine
other files (backfill.py, catalogue_web.py, cleanup.py, weave.py, tiers.py, completeness.py,
repass_bands.py, overnight.py) that are outside this batch and were not re-checked here; only the
policy.py clause is confirmed resolved.

Read `OPS`'s closed operator set and the `TYPES`/`ARG_REQUIRED` load-time validation (both refuse
a malformed rule rather than mis-attributing its crash to "the document failed"), `evaluate()`'s
narrow `absent`-only vacuous-pass exemption, and `main()`'s three rule sweeps (records, coverage,
evidence) with their unreadable-file accounting and the two-exit-code contract (`1` = rules failed
or a document was unreadable, `2` = rules passed but the report write was denied). All internally
consistent; no new defects found.

---

## src/sevenfold.py (441 lines)

Nothing found. Read `affinity_order`, `_even_cuts`, `shelve`/`seams` (the window-plus-weaker-half
balancing fix for order 2a48315d26e6 — re-derived the arithmetic by hand against the docstring's
worked example and it holds), `build()`'s two-stage source/world shelving and its `UNSHELVED`
accounting, and `main()`'s write-gating (`silence.write_json` verdict propagated to both the
printed message and the exit code). No `re` import and no backslash-escape literals in this file,
so the missing `_BAD_CHARS` guard (also absent here) is moot — confirmed by grep, not assumed.

---

## src/resonance.py (298 lines)

Nothing found. `hodge_decompose`'s Gauss-Seidel convergence fix (order 6e1c72cddfeb) checked
against its own worked before/after numbers (STAR/BIPARTITE/PATH4 converging in 2/2/18 sweeps) and
the arithmetic is internally consistent; the `no_evidence`-vs-`eta=1.0` distinction is enforced at
every return path (empty node set, unconverged, and zero-flow-total all return `eta: None`
distinctly from a genuine `eta` value). The module's own "NO PRODUCTION CALLER" disclosure
(resonance.py:40-73) was verified structurally consistent with the rest of the file rather than
re-verified against every other module (out of batch scope) — it is documentation of a known gap,
not a code defect. No `re` import; the missing `_BAD_CHARS` guard is moot here too.

---

## src/deprecated/catalogue_local.py (333 lines)

Nothing found. Verified the module-level refusal is unconditional and fires before any of the
dangerous code the header describes (bare `data/records/` write bypassing
`pipeline.write_record_catalogue`, non-atomic whole-file rewrite of `data/SWEEP_ROLL.json`, the
`slug()` `[:60]` identity truncation, `main()` always returning 0): `raise SystemExit(_REFUSAL)`
sits at line 94, before `CATEGORIES`, `ENTRY_SCHEMA`, `SYSTEM`, `USER`, `GUIDANCE`, `load_cfg`,
`slug`, `call`, `catalogue_source`, and `main` are ever defined (lines 96-334) — so importing or
running this module for any argv other than `-h`/`--help` cannot reach any of them. The `--help`
exemption (lines 91-93) only prints the notice and exits 0, touching nothing. Matches the module's
own docstring claim exactly.

---

## Coverage stamp

Modules read in full and stamped via `sweep_plan.record`: `read.py`, `health.py`, `allsweep.py`,
`weave_index.py`, `policy.py`, `sevenfold.py`, `deprecated/catalogue_local.py`, `resonance.py`.
