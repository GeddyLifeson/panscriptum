# SWEEP35 batch 03 audit

Modules read in full, paging with offset reads, no sampling: `src/pipeline.py` (2,328 lines),
`src/estate.py` (348), `src/feats_index.py` (289), `src/hosts.py` (253), `src/style_audit.py`
(211), `src/ledger.py` (136). 3,565 lines total, matching the assignment.

## Findings filed (4)

1. **pipeline.write_record uses a length-only drift check** (pipeline.py:655) — the merge-vs-
   overwrite decision compares only `len(disk.entries) != len(rec.entries)`; a same-count,
   different-content drift from a concurrent writer is invisible to it and gets silently
   overwritten by the stale in-memory copy, even though the module's own `_entry_digest` /
   `stamp_record` machinery (built for exactly this file) could have caught it. Confirmed
   verify_math.py's Section 18c tests only the count-differs case in both directions, never
   same-count drift. Filed RUN/MAJOR.

2. **estate.written() swallows a report line instead of noting it** (estate.py:245-250) — the
   `weave_index.load_records()` probe is the only failure path in the whole file that calls
   `silence.note()` without also calling the local `note()` that populates the human-facing
   report; every sibling handler in charter(), terminal(), and written()'s own next block
   reports failures visibly. Filed RUN/MINOR.

3. **src/hosts.py has no caller anywhere in the pipeline** — a complete, working module built to
   fix the "single-host assumption" cap, with real discovered data already on disk
   (`data/SOURCE_HOSTS.json`, non-trivial size, dated 2026-08-22), but nothing else in src/
   imports the module, calls `hosts_for()`/`primary_host()`, or reads `SOURCE_HOSTS.json` —
   `feats.py` mines only from `WIKI_HOSTS.json`. Same shape as the project's own documented
   phase_chain gap. Filed OWNER/MAJOR (deletion vs. wiring-in is a judgment call).

4. **src/ledger.py (De Pretio currency) has no caller outside its own tests** — internally
   tested and self-consistent (verify_math.py:266-284), but no production module
   (manifest_builder.py, generate.py, prose_gate.py, catalogue_*.py) imports it, and the
   Position-Paragraph / Freeport clause its own docstring says it exists to serve has no
   currency wiring anywhere in the generation path or prompts. Filed OWNER/MAJOR.

One filing hazard hit and corrected in-flight: an evidence string built through a bash-quoted
python -c call picked up a literal backspace (chr(8)) from a `\b` word-boundary escape eaten in
transit — the exact corruption pattern pipeline.py and estate.py both guard their own source
against. Caught before this report was written, patched directly in `state/workorders.json` for
that one order (`3fb312a72435`) so the findings ledger doesn't carry the same defect it's
reporting on.

## Checked, not filed (already open elsewhere)

* `hosts.py:158` omitting `hosts=` on the `HC.candidates()` call — already filed as
  `6a83762ab9bb` (SWEEP34).
* `ledger.assay_to_standards` collapsing the top band's interpolation range to zero — already
  filed as `5082a529e937` (SWEEP34).
* `ledger.to_standards`/`from_standards` conflating "unlisted currency" with "deliberately
  non-convertible" — already filed as `e9167885aef6` (SWEEP34).
* `style_audit.BANNED` dead assignment — already filed as `ed7df12bf429` (SWEEP34).
* The standing `3c7c8a6e9102` re-catalogue-nulls-synthesis bug — read in full; the docstring and
  code in `write_record_catalogue` (pipeline.py:442-520) already carry the fix (the
  absent/None-vs-explicit-empty key handling), so this is the known, already-being-worked
  defect, not a new one. Did not re-file.

## Considered and deliberately NOT filed

* `pipeline.py`'s `_SCALE_PATTERNS`/`_SCALE_EVIDENCE` (around line 1160) — dead, but the comment
  immediately above it already explains it is kept deliberately as a record of the rejected
  approach, not a live alternative. Filing it as "dead code" would be noise on something the
  module already documents about itself.
* `style_audit.py`'s `re.split(r"^[◈◈]\s*", ...)` — the character class repeats the same
  codepoint (U+25C8) twice, which looked like a missed second delimiter. Checked against the
  canonical splitter in `prose_gate.py:201` (`^◈\s`, single character) — confirms `[◈◈]` is
  functionally identical to `[◈]`. Cosmetic duplication, not a behavioural bug; not filed.
* `pipeline.write_record_catalogue`'s per-entry field-merge and `hosts.py`'s `per_source` /
  `discover()` truncations — both are explicitly ranked-then-bounded over already-decided
  candidate lists (or explicitly documented as intentional), not reports of a complete set being
  silently cut. Not Hard-Rule-0 violations.
* `style_audit.report()`'s `most_common(top)` displays — console diagnostics that disclose their
  own full counts alongside the truncated top-N display (e.g. `({len(a['banned'])} distinct
  tells present)`); not a case of a truncated list being presented as the complete answer.
* `pipeline.py` shelve phase's `shelved[key]` keyed by `source::name` — a same-source duplicate
  name would overwrite silently, but no evidence was found that duplicate names within one
  source's entry list actually occur; too speculative to file without a measured casualty.

## Coverage recorded

`sweep_plan.record('run35', [pipeline.py, estate.py, feats_index.py, hosts.py, style_audit.py,
ledger.py], batch=3)` — done.
