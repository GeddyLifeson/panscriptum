# AUDIT batch05 — run54

Batch: `src/feats.py`, `src/ledger_guard.py`, `src/thread_integrity.py`, `src/autostart.py`,
`src/axis_correlation.py`, `src/sweep.py`, `src/entity_match.py`

All seven files were read in full, line by line, including every docstring and inline comment
(these modules are exceptionally heavily annotated with the reasoning behind past fixes — that
annotation was read, not skimmed). Cross-file claims (line citations to other modules) were
additionally verified against the cited files' actual current line numbers where the citation
was specific enough to check.

## `src/feats.py` (2,783 lines)

Read in full across five passes (transport/throttling, host resolution, page discovery/mining,
axis gates, the roll/CLI). This module is unusually self-audited: nearly every historical defect
it once had (truncating caps, swallowed 429s treated as absence, wikitext-eating a template
wrapper, exponents dropped from quantities, per-host vs per-domain rate limiting) is documented
in place with the order id that fixed it and a measurement. I traced the live code paths for
each rather than trusting the comments, specifically: `_throttle`/`note_throttled`/`note_ok`
locking on `registrable_domain`; `_QUANTITY`'s group numbering against `mine()`'s
`m.group(1..4)` reads; `discover()`'s uncapped title list; `evidence_for()`'s four
`mined_under_*` staleness predicates against what `evidence_for` actually stamps; `resolve_hosts`'s
None-vs-absent-key handling; and `roll()`'s exit-code propagation in `main()`.

### MINOR — stale line citations to `magnitude.py`
**Where:** src/feats.py:1741 and :1744
**What:** The comment reads: "magnitude.py:417 names both in terms as 'franchise-internal scales
with no conversion'... 'kili' is the worked example at magnitude.py:45 and :640".
**Why it is wrong:** In the current `src/magnitude.py`, the "franchise-internal scales" language
is at line 423, not 417; the "kili"/"power level" worked-example material the comment points at
sits at lines 17 and 51 (the ":45" citation), and 646 (the ":640" citation) — each citation is
off by roughly 5–6 lines from where the content actually is now. The content itself is present
and the paraphrase is accurate, so this is drift (magnitude.py was edited above these points
after the citation was written), not a fabricated claim — but a reader who jumps to feats.py:417
in the current file lands on unrelated code (a `_leads_a_verb` check inside a different guard).
**Confidence:** Verified directly — read the cited lines in the current `src/magnitude.py` and
confirmed the actual location of the quoted text via `grep -n` for the exact phrases
("franchise-internal", "3,000 kili"). Not filed as a fix, just as the documentation-drift finding
Hard Rule asks for (type 4).

Other specific cross-file citations in this batch were spot-checked and found accurate:
`reference.py:95` (feats.py:1744, matches the cited Reach evidence exactly),
`pipeline.py:36` (ledger_guard.py:534, matches "NEVER written here" for HANDOFF.md), and
`dashboard.py:77-80` (axis_correlation.py:420, matches the cited "a baked-in line number rots"
comment). No other MAJOR, MINOR or INFO findings in `feats.py` — I looked specifically for a
"check that cannot fail" (re-verified `_axis_independent_gates`'s single-definition hoist, the
`_units()` length-gate tallying, and the `mined_under_*` staleness predicates for the tautology
class this project's own doctrine warns about) and found none live; every instance of that shape
I could find is already named, fixed, and left as a comment describing the fix.

## `src/ledger_guard.py` (1,008 lines)

Read in full. Checked the append-only detection (`_one_insertion`, `check_append_only`), the
`_lost_fraction` multiset diff, the seal/snapshot/floor-ratchet mechanism in `seal()`, and the
hash-chain verification in `verify_chain()` including the acknowledged-shrink carve-out. Verified
`_snapshot_path`/`_floor_snapshot_path` use one shared spelling (the drift between writer and
reader this file's own comment describes as a past incident is not reproduced — both routes
through `_snapshot_path`). Verified `check_structure`'s Open/Resolved bug-id cross-check uses
`text.find` positions rather than an assumed section order (the earlier "check that cannot fail"
this file documents fixing). No findings — the module's own commentary already names and closes
every version of the several "check that cannot fail" incidents it has had, and I could not find
a new one on this pass.

## `src/thread_integrity.py` (722 lines)

Read in full. Checked `_charter_codes()`'s three-way absent/corrupt/wrong-shape handling,
`load_thread_graph()`'s fail-closed `ThreadGraphUnreadable` raising, `classify()`'s DANGLING/
PARTIALLY-DANGLING drift detection and its RECIPROCAL/ASYMMETRIC-SUSPECT branch (currently
unreachable in production since every caller passes `recorded=None` per Hard Rule 5, confirmed
by reading `main()`), and the `_floor_verdict` regression-floor state machine. Verified `main()`
actually returns a nonzero exit on every failure branch it prints (this was itself a fixed
tautology-shaped bug per the file's own order aa075aa80f5c comment; I traced all six branches —
DANGLING, unresolvable, and the five `_floor_verdict` states — and each one that prints "FAILED"
does set `failed = True` before the final `return`). One thing worth naming as a QUESTION rather
than a finding: `_charter_codes()` adds every one of `code`/`spine`/`spine_code` that is present
on a dict entry rather than stopping at the first hit (lines 116–119), so an entry carrying two
differently-spelled keys with different string values would contribute both to the address set.
I could not tell from this file alone whether `CHARTER_SPINE_CODES.json` rows ever carry more
than one of those three keys at once, so I am not filing this as a bug — it may never fire in
practice.

## `src/autostart.py` (565 lines)

Read in full. Reconstructed the VBScript command-line concatenation in `_vbs_body()` by hand
(the `q = ' & Chr(34) & '` splice is non-obvious) and confirmed it produces the intended
`"<pythonw>" -u "<autostart.py>" --watch` invocation with no stray quoting — this looked like the
most likely place for a live bug given the comment describing a previous broken version, but the
current concatenation is correct. Checked `installed_state()`'s current/stale/absent/unreadable
tri-state, `install()`'s temp-then-replace-then-readback sequence, `_twin_watchdog()`'s
retry-then-fail-open behaviour, and `watch()`'s start budget (`MAX_STARTS_PER_HOUR`) and its
tri-state `supervisor_alive()` handling (None is never treated as "dead"). No findings.

## `src/axis_correlation.py` (444 lines)

Read in full. Checked `_pearson()`'s formula against the standard Pearson-r definition (correct,
no double-normalization), `_scores_of()`'s two-shape handling (hand-built `axes` dict vs.
automated `result.scores` flat dict) including the `bool`-is-an-`int`-subclass exclusion, the
`_no_matrix()`/`MATRIX_FALLBACK_REASON` singleton-announcement plumbing, and `widening()`'s
covariance-term arithmetic against the formula stated in the module docstring
(`Var(C) = Σ(w_i σ_i)² + 2·Σ_{i<j} w_i w_j ρ_ij σ_i σ_j`). Confirmed via `drill.py:15355-15356`
that the single `sigma` argument to `widening()` is deliberately one attestation-tier value
applied uniformly across axes (matches `assay.SIGMA_BY_ATTESTATION`), not a per-axis vector that
got collapsed by mistake. No findings.

## `src/sweep.py` (375 lines)

Read in full. Checked `nested_run()`'s subset test (`sets[order[j]] <= sets[order[j-1]]`, correct
subset-or-equal semantics) and confirmed the historical negative-drop-arrow bug the module
docstring describes (`-{drop:,}` going negative) cannot recur because `chain` is now
constructed to be genuinely non-increasing before the print loop runs. Checked the `report()`
funnel/loose-population split and the uncapped BIGGEST GAPS / REACHED BUT SILENT listings.

### MINOR — three supporting-file loads in this module skip the fail-closed pattern the rest of the file (and codebase) uses
**Where:** src/sweep.py:162 (`sweep()`), :135 (`rosetta_index()`), :151 (`navtree_names()`)
**What:** `hosts = json.load(open(F.HOSTS, encoding="utf-8")) if os.path.exists(F.HOSTS) else {}`,
and the equivalent bare `json.load(open(p, encoding="utf-8"))` calls in `rosetta_index()` and
`navtree_names()`, have no try/except around the read or parse.
**Why it is wrong:** Every comparable load in this same file's sibling modules in this batch
(`axis_correlation.observations()`, `thread_integrity._charter_codes()`,
`feats.anomalous_empty_hosts()`) treats "file exists but is unreadable or unparseable" as a
distinct, recorded state (via `silence.note` plus a degraded-but-continuing return) rather than
letting the exception propagate — precisely because a corrupted supporting file is a different
fact from an absent one. Here, a truncated or mid-write `WIKI_HOSTS.json`, `ROSETTA.json` or
`NAVTREE.json` (all three are written elsewhere in the pipeline by concurrent processes this
project's own commentary describes racing on Windows) would raise an uncaught
`json.JSONDecodeError` and abort the whole character sweep rather than reporting a degraded run.
The direction is the safe one (main()'s final `write_json` never runs, so `CHARACTER_SWEEP.json`
itself is never corrupted — the previous good sweep survives on disk), so I am filing this as
MINOR rather than MAJOR: the failure is loud (a traceback) rather than silent, which is a
materially different risk from the silent-failure class Hard Rule -1 is mainly about. But it is
an inconsistency with the fail-closed-and-say-so discipline every other loader in this batch
uses for the identical class of input.
**Confidence:** Read the three call sites directly; confirmed the absence of any try/except by
reading the full function bodies (`sweep()` lines 160-206, `rosetta_index()` lines 123-144,
`navtree_names()` lines 147-157). Did not reproduce a corrupt-file crash by running the module
(read-only per the brief).

## `src/entity_match.py` (311 lines)

Read in full. This module is not yet called from anywhere in the tree (per its own header — it
is "the second pass" awaiting a caller), so I checked it primarily for internal consistency
rather than integration risk. Verified `qualifier_compatible()`'s three-way agree/conflict/missing
gate against the three worked Wally West continuities the header describes, `similarity()`'s
max-of-two-measures scoring, the `STRONG`/`WEAK` threshold ordering assertion (a defence against
exactly the "check that cannot fail" class this project's doctrine warns about — the assert would
catch a future misordering that would otherwise silently mislabel WEAK candidates as STRONG), and
`candidates()`'s four return-shape branches (empty name / empty pool / normal / normal-with-
rejections) for the "one return shape, always" contract the module's own comment says was needed
after an earlier KeyError/AttributeError incident. No findings.

## Summary

- MAJOR: none
- MINOR: 2 (feats.py:1741/1744 stale magnitude.py line citations; sweep.py's three unguarded
  JSON loads)
- INFO: 0 filed findings; 1 QUESTION noted under thread_integrity.py (`_charter_codes()`
  potentially adding more than one code per entry — not confirmed against real data shape)
