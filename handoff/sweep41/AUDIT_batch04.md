# Sweep 41, batch 04 — audit

Modules read IN FULL: `src/standards.py` (2247 lines), `src/derivation.py` (744 lines),
`src/onomast.py` (582 lines), `src/policy.py` (477 lines), `src/pantheon.py` (373 lines),
`src/style_audit.py` (310 lines), `src/tuning.py` (273 lines), `src/repass_bands.py` (150 lines).
5,156 lines read (line-count total; sums to ~5,149 net of trailing newlines) against a batch of 8
files. No file in `src/` was edited. `src/drill.py` was not run.

## Overall impression

All eight modules in this batch carry a long, dense history of self-repair — nearly every
docstring documents a prior defect, its reproduction, and its fix, in the house style. This is
the most heavily-hardened batch I have read in this sweep: the specific failure modes the sweep
brief calls out (a standard computed from a source it cannot read; "unmeasurable" read as a
measured zero; a swallowed failure returning an honest-looking empty) have almost all already
been found and fixed in this code, with the fix's own reasoning left in place as a guard against
regression. Most of my reading time went to verifying that documented "already fixed" claims are
actually true of the CURRENT source (they are, with one exception below: a stale work order) and
hunting for a shape the existing repairs had not yet reached.

## Findings filed this batch

### 1. QUESTION for OWNER — `derivation.py` assay_dof lists 9 parents, but its own text and
   `custodes.py` both say ten (code `DERIVATION_ASSAY_DOF_NINE_NOT_TEN`, OWNER/MINOR)

`derivation.py:266-274`:

```python
"assay_dof":  Q(DERIVED, "the independent levers in the assay computation: ten "
                         "survive the test that varying one alone moves the output "
                         "and is not a function of the others",
               ["log_scoring_rule", "attestation_grades", "aperture_doctrine",
                "arrival_years", "chain_of_record", "parity_rate",
                "curl_fraction", "transgression_beta", "evt_ceiling"]),
"college_size": Q(DERIVED, "one Custos per degree of freedom", ["assay_dof"],
                  note="the count is derived, not chosen: a direction with nobody "
                       "standing in it is a direction nobody checks"),
```

The `assay_dof` prose says "ten survive the test" and `college_size`'s note says "why exactly
ten" — but the parents list holds exactly **nine** names (verified by direct count).
`src/custodes.py` (read for cross-reference only, not part of this batch) defines exactly **ten**
`CUSTODES` entries with ten distinct `dof=` labels: attestation, reduction, ratification,
nomination, applicability, commensuration, comparability, transgression, currency, scope
(`grep -c 'dof="' src/custodes.py` → 10). Matching each of `assay_dof`'s nine parents to a
Custos's `dof=` by content (attestation_grades↔attestation/Quill, log_scoring_rule↔reduction/Moth,
chain_of_record↔ratification/Avar, evt_ceiling↔nomination/Sable ["reads every ceiling as a sample
maximum"], aperture_doctrine↔scope/Vault ["an unaperture'd magnitude"], parity_rate↔commensuration
/Ordo, curl_fraction↔comparability/Threnody, transgression_beta↔transgression/Otto, arrival_years↔
currency/Lumen ["distance is age"]) accounts for nine of Lumen's/custodes.py's ten `dof=` labels
and leaves exactly one unmatched: **applicability** (Cassia — "category error; she will strike an
axis before she will score it badly"). The ledger already has a quantity that matches Cassia's
role by content: `applicability_mark` (`Q(DERIVED, "INAPPLICABLE excluded from the coverage
denominator", ["faculty_parity", "attestation_grades"])`), and it is not in `assay_dof`'s parents.

Two readings, and I cannot tell which from `derivation.py` and `custodes.py` alone:

  (a) `assay_dof` is missing `applicability_mark` as a tenth parent — a real gap, meaning
      `college_size`'s "derived, not chosen" claim is currently derived from nine dependencies
      while the actual College seated by `custodes.py` has ten members, one of them (Cassia)
      without a counterpart in the ledger that is supposed to justify her seat existing.
  (b) Applicability is deliberately excluded because it decides whether an axis counts at all
      rather than being a lever that "moves the output" the way the other nine do (an axis
      exclusion is a gate, not a scored dimension) — in which case the prose "ten" in both
      `assay_dof` and `college_size` is what has drifted, and should read "nine", with a separate
      sentence explaining why Cassia's seat is not counted among assay_dof's levers.

`derivation.check_graph()` cannot catch this either way: it verifies the graph closes (no
dangling parents, no cycles, no unsigned OWNER rows), never that a DERIVED count's parents list
actually numbers what its own prose and its dependent's prose both claim.

### 2. LOW/MINOR — `onomast.py` `well_formed()` docstring says "Four constraints", code runs six
   (code `ONOMAST_WELLFORMED_DOCSTRING_UNDERCOUNTS`, LOCAL/MINOR)

`onomast.py:171-210`. The docstring header reads:

> "Four constraints, all mechanical: length / echo / stutter / cluster"

The function body implements those four, then two more, each with its own explanatory comment
clearly added later (they cite specific ugly names the first four checks do not catch):

- consonant density cap ("Consonant density. Shessasha (s x4) and Goggournok (g x3) pass every
  repetition test above ... Capping each consonant at two occurrences catches what the sequence
  tests structurally cannot")
- vowel-run cap ("Aeeinna and friends")

plus the final `sum(... in _VOWELS) >= 2` minimum-vowel-count check, which the docstring also does
not enumerate. Not a functional bug — every check is doing real, deliberate work and each has its
own comment — just a header that undercounts its own function's constraints by two (really three,
counting the vowel minimum), which is the "stale commentary" shape the sweep brief asks after.
Low value on its own; filed because it is cheap to fix and a header that undersells what a
function checks is exactly the kind of drift that makes a later editor trust the count over the
code.

## Verified against source, NOT re-filed (already covered by open orders)

- **`repass_bands.py:73-77`** — `e["scale_note"] = ""` on demotion, with the rejected text
  preserved nowhere, exactly as the brief's own context note describes. I re-verified this against
  the CURRENT file (not just the brief's description): the code at those exact lines still clears
  `scale_note` unconditionally in the `--apply` branch, with no `scale_note_rejected` companion set
  (unlike `pipeline.phase_entrypass`, which the existing order cites as doing this correctly).
  Order `REPASS_BANDS_DISCARDS_REJECTED_SCALE_NOTE` (SESSION/MAJOR) already covers this in full,
  including the correct remedy (mirror `pipeline.py`'s `scale_note_rejected` field, which is
  already in `MERGED_ENTRY_FIELDS`) and a second-order hazard about `ENTRY_REJECTION_COMPANIONS`
  popping a disk-side rejection field. I did not duplicate it. Separately: the SOURCE-level
  demotion two loops up (`repass_bands.py:48-57`) is NOT affected — it already writes `demoted_by`
  and keeps the evidence string, confirmed by direct re-read.
- I checked whether the entry-level MAGNITUDE value itself (not just `scale_note`) should also be
  preserved on demotion (there is no `magnitude_rejected`-style field in
  `pipeline.MERGED_ENTRY_FIELDS`). I concluded this is NOT a finding: the module's own docstring
  states the demotion's purpose plainly — "Demotion is not data loss... it loses a claim nobody had
  earned" — an unearned magnitude is exactly what this pass exists to discard, unlike the
  evidence TEXT, which retains audit value (was the gate too strict?) the way the already-filed
  order's cited `pipeline.py` rationale explains. Preserving the discarded band would undercut the
  module's stated purpose rather than serve it.

## Stale open order found (informational, not resolved by me)

`standards-provider-denom-error-truncated` (RUN/MINOR) describes a `[:40]` truncation of provider
error text at `standards.py:604` inside `provider_pool_denominator`'s legacy/no-`counts` fallback
branch. I re-read that exact function in full (`standards.py:564-638` in the current file) and the
`[:40]` slice is **gone** — the current code reads:

```python
names = sorted("%s (%s)" % (r.get("provider") or "?",
                            " ".join(str(r.get("error") or "no model list").split()))
               for r in rows if not r.get("models"))
```

which collapses whitespace instead of truncating, exactly matching the batch brief's own note that
"a `[:40]` error cut w[as] removed" today. `grep -n '\[:40\]' src/standards.py` finds no live code
matching that shape any more — every remaining `[:40]`/`[:60]`/`[:80]`/`[:18]`/`[:120]` hit in the
file is inside a comment narrating a past fix. This order appears to have been closed out by
today's earlier work in this same file but not marked resolved. I did not call `resolve()` on it —
outside this batch's audit-only mandate — but flag it here so the owner or the next housekeeping
pass can close it without re-investigating.

## Considered and explicitly NOT filed

- **`standards.ollama_token_flow`'s use of `state/model_metrics.jsonl`**, per the batch brief's
  request to check for contamination from the ~22%-row-loss `O_APPEND` defect. This is the ONLY
  use of `model_metrics.jsonl` anywhere in this batch's eight files (verified by grep across all
  eight). The function reads only the tail of the file and asks whether ANY row within the last
  15 minutes carries a `tps` — a presence check over a live window, not a historical count or
  rate computed by aggregating rows. A silently-dropped write during that window would at worst
  make this probe fall through to the live `/api/generate` call slightly more often than
  necessary (extra cost, not a wrong verdict) — it cannot manufacture a false "flow is healthy"
  reading from missing rows, since a missing row just means no evidence was found, not fabricated
  evidence. No standard elsewhere in this batch aggregates `model_metrics.jsonl` over time. Not
  filed.
- **`style_audit.py`'s "MACHINE TELLS" block** (`report()`, around line 199-207) caps its printed
  list at 14 distinct tells via `[:14]` without routing through the file's own `_cut()` helper the
  way the other three rankings do (fixed under order `1cb7bd3ad0ce`). Considered under Hard Rule 0.
  Not filed: unlike the three rankings `_cut()` was written for, this block DOES separately print
  `({len(a['banned'])} distinct tells present)` right after the capped list, so the reader can see
  exactly how many were cut and by how much (a difference of a subtraction), and nothing on disk
  is capped — `data/` or `state/` artifacts this feeds are not touched by the `[:14]`. It is a
  minor style inconsistency with the module's own established convention, not a hidden truncation.
- **`tuning.regime()`'s `judged` gate** — when there is not yet enough call history to judge the
  cloud success rate (`judged=False`), the regime falls back to trusting bucket-answering alone
  rather than defaulting to "local"/"starved". This looks superficially like the exact "reachable
  is not the same as succeeding" mistake `CLOUD_MIN_SUCCESS`'s own docstring says this file exists
  to close. Not filed: the surrounding comment on `MIN_CALLS_TO_JUDGE` already states the
  trade-off explicitly ("a handful of failures during a provider blip must not flip the whole
  library to local"), i.e. the fallback direction (trust reachability when there is no rate
  evidence yet, rather than assume failure) is a documented, deliberate choice already reasoned
  about in the source, not an unconsidered gap.
- **Standards.py's `_dropped` / green-by-absence pattern** — I re-verified, by direct read of every
  `try/except` block in `check()`, that all ~24 file/probe-backed standards now either append a row
  or add their name to `_dropped`, and that `_dropped` itself is turned into a HIGH standard
  ("every standard could read its own input") at the end of `check()`. I found no remaining path
  where an exception silently drops a standard without being counted. No finding here — the
  pattern the sweep brief specifically asks about in this module appears to be fully closed.

## Coverage

`sweep_plan.record('run41', [...8 modules...], batch=4)` recorded.

## Work orders filed this batch

1. `DERIVATION_ASSAY_DOF_NINE_NOT_TEN` — OWNER / MINOR — `derivation.py:266-274` (question, both
   readings given)
2. `ONOMAST_WELLFORMED_DOCSTRING_UNDERCOUNTS` — LOCAL / MINOR — `onomast.py:171-183`
