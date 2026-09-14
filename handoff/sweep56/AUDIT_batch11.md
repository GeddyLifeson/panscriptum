# Sweep56 batch11 audit

Modules read in full, top to bottom (all in `src/`): `overnight.py` (1968 lines),
`silence.py` (1122 lines), `chain.py` (915 lines), `build_terminal.py` (667 lines),
`reference.py` (497 lines), `pick_model.py` (443 lines), `style_audit.py` (338 lines),
`ledger.py` (220 lines), `chord_field.py` (210 lines).

No file was sampled; each was read in successive chunks covering every line. Every
finding below was verified against the current on-disk source at the time of this audit
(2026-09-11), not reasoned from a docstring's own claim about itself.

---

## DEFECT — `src/overnight.py:1686-1688` — stale line-number citations, all seven wrong

```python
        # starts afterwards opens `main()` with `escalation.assert_clear` -- dashboard.py:1068,
        # publish.py:1594, foreman.py:1711, overwatch.py:922, pipeline.py:2876 (the whole of
        # STANDING), plus read.py:1408 and feats.py:1813, the two long jobs that hang off this
```

Verified each cited line against the actual file on disk, and separately located the real
`_ESC.assert_clear(os.path.basename(__file__))` call site in each module by grep:

| cited in comment | what's actually there | real `assert_clear` call site |
|---|---|---|
| dashboard.py:1068 | unrelated JS about quarantine labels | dashboard.py:1206 |
| publish.py:1594 | unrelated code about `scan_for_secrets` leaks | publish.py:1814 |
| foreman.py:1711 | unrelated `pool_has_room` handler | foreman.py:1941 |
| overwatch.py:922 | unrelated `corrupt_files`/`prev` handling | overwatch.py:1044 |
| pipeline.py:2876 | unrelated ranking-prior comment | pipeline.py:3256 |
| read.py:1408 | unrelated "estimate is in chunks" comment | read.py:1561 |
| feats.py:1813 | unrelated `_UNIT_DROPS` comment | feats.py:2668 |

All seven citations are off (drift of 130-380 lines each), every one in the same direction
(the real call site is further down than cited), consistent with code having grown above
these calls since the comment was written. This is exactly the "stale line-number citations
in comments" defect class the sweep brief calls out by name, and it sits inside the very
paragraph arguing that the halt-interlock mitigation is "CHECKED, not assumed" — the citations
that were supposed to be the checking are themselves unchecked and wrong.

Confidence: DEFECT (mechanically verified, not a judgment call).

## QUESTION — `src/overnight.py:202` — approximate citation now off by ~98 lines

```python
    would have skipped every stage it was built to run.
    ...
    `publish.py` computes the published page in its own process (`publish.py:render_page()`, ~line 1266),
```

`render_page` is actually defined at `publish.py:1364`, not "~line 1266" — a drift of about
98 lines. The comment itself hedges with `~`, so this may be considered acceptable
"approximate" pointing rather than a precision claim; flagging as a QUESTION rather than a
DEFECT because the author explicitly marked it as inexact, but the drift is large enough
(98 lines, roughly a full screen) that a reader following it would land in the wrong
function entirely.

## DEFECT — `src/build_terminal.py:647` — two more stale cross-file citations

```python
        # below turns into a clean exit for a run whose only product is not on disk -- exactly what
        # `catalogue_codex.py:315-331` and `generate.py:700-706` already settle the other way in
        # this same tree, both citing `module_index.py` as the shape: return 1 on a denied write.
```

Checked both citations:
- `catalogue_codex.py:315-331` is mid-function code about `norm()` collisions and duplicate
  detection — nothing to do with a denied write or a return code. The actual "return 1 on a
  denied write" reasoning in that file is at `catalogue_codex.py:488-496`
  (`WRITE DENIED: SWEEP_ROLL.json did not land...` plus the comment "return 1 on a denied
  write, ... the shape copied here").
- `generate.py:700-706` is unrelated evidence-cache/recipe-hash code inside a job loop. The
  actual denied-write handling this comment is describing is at `generate.py:130-147`
  (`WRITE DENIED -> {path}: the replace was refused...`).

Both citations are wrong by a wide margin (170+ lines for the first, 550+ lines for the
second) and point at code with no relationship to the write-denial behavior being cited.

Confidence: DEFECT (mechanically verified).

## DEFECT — `src/ledger.py:43` — stale citation to verify_math.py

```python
THE MEASUREMENT IT IS HELD AGAINST. This file is finished, self-consistent and arithmetically
exercised (`verify_math.py:266-284` drives `to_standards`, `from_standards`, `cross_rate`,
`work_value` and `assay_to_standards`), and it has **no caller in the generation pipeline at all**:
```

`verify_math.py:266-284` is unrelated code (a `_wrote_to_the_ledger_vm` helper and a comment
about `silence.note()` exemption doctrine, nothing to do with `ledger.py`'s functions). The
actual battery checks for `to_standards`, `from_standards`, `cross_rate`, `work_value` and
`assay_to_standards` are at `verify_math.py:909-922` (confirmed by grep: `check("work_value
inverts the definition", ...)` at 909 through the `assay_to_standards` caveat check at 922).

This one matters slightly more than the others because the surrounding paragraph is making an
evidentiary claim ("arithmetically exercised") and citing the wrong lines undermines a reader's
ability to go verify that claim quickly — though the claim itself (that the battery exists and
exercises these functions) is true, just mis-cited.

Confidence: DEFECT (mechanically verified).

## QUESTION — `src/reference.py:374` — citation off by one line

```python
    # (`silence` is imported at module level and used at :245; the re-import that stood here was
```

The actual first `silence.note(...)` call is at `reference.py:246`, not `:245` — line 245 is
the tail end of the comment block immediately above it. This is a one-line drift, most likely
because the citation was written against the comment/code boundary rather than the call
itself. Too small a drift to be confident it will mislead anyone in practice, so flagged as a
QUESTION rather than a DEFECT.

---

## Nothing found — clean modules / clean aspects

- **`src/silence.py`** — read in full. This is the module that polices silent failure
  elsewhere in the tree, and I specifically hunted for a silent failure inside it. Every
  `except` block either calls `silence.note`/`health.record`, re-raises, or is one of two
  explicitly-documented total-swallow sites (`swallow.__exit__`'s recorder-of-last-resort at
  line 133, and `_unlock`'s at line 565-568) — both are commented as deliberate ("the recorder
  itself must never be the thing that breaks a run" / "the OS drops the lock at close anyway").
  Atomic-write correctness (`write_json`, `replace_retry`, `replace_if_unchanged`,
  `append_line`'s Windows-specific locking and O_BINARY handling) all checked out against
  their own stated invariants — the digest-then-immediately-rename loop in
  `replace_if_unchanged` genuinely re-digests on every attempt rather than digesting once and
  sleeping before the swap, and `UNREADABLE` vs `None` (absent) are kept distinct throughout.
  No caps, no truncation of any roster (the `swallow.detail` truncation and `most_common(40)`
  types of bug this module's own comments describe as historical are already fixed, and I
  confirmed the current code keeps the full value in every case checked). No tautological
  checks or guards on undefined names found.

- **`src/chain.py`** — read in full. Atomic-write pattern for `CHAIN.json` and the harvest
  index both go through `silence.write_json` / `silence.replace_if_unchanged` with unique
  pid+thread temp names, matching the documented m100/run#26 fix. `write_result` is unconditionally
  called on every code path in `main()` including both refusal paths (fit error, no strengths),
  matching the module's own stated fix for order `0ced896514e7`. No caps found — `unmatched`,
  `edges`, and the strengths list are all persisted with `most_common()` (unbounded) rather
  than a capped slice; only the *console* previews are capped (8 and 14 rows respectively),
  and both are explicitly labelled as previews with a pointer to the uncapped file. The
  mutual-pair epoch adjudication logic in `adjudicate_mutuals` (the unprobed/self-split/half-dated
  cases) reads as internally consistent with its own docstring's stated cases.

- **`src/build_terminal.py`** — read in full, aside from the two stale citations above. The
  atomic-write pattern for the terminal HTML page is present and correct (unique pid+thread
  temp name, `silence.replace_retry`, denied-write returns rc 1 rather than swallowing).
  `<script>` injection is neutralized before splicing JSON into the inline script
  (`data.replace("<", "\\u003c")`). JS-side label truncation (`trimmed()`, the source-shelf
  and world-name slicing) always carries an ellipsis marker and keeps the full name in the
  tooltip/panel — this is UI-label sizing, not a Hard-Rule-0 roster cap, and no underlying data
  is dropped.

- **`src/pick_model.py`** — read in full. `save_config`'s atomic replace and its two "used to
  falsely claim success" fixes (discarded `replace_retry` boolean; a `re.sub` matching nothing)
  both check out against the current code, which threads the real boolean through to the
  caller. The VRAM-budget-vs-measured distinction (`total_vram_gb()` vs `free_vram_gb()`,
  and the `is not None` vs truthiness fix for 0.0 GB free) is applied consistently. No caps or
  silent failures found.

- **`src/style_audit.py`** — read in full, and its own `--self-test` was run (read-only,
  writes nothing) to confirm the self-test the module claims passes actually does. Output
  matched the docstring's claims exactly (3-entry fixtures, correct shape/tell/turn-ending
  counts, self-test PASSED). The `_cut()` helper used across all four rankings (opening
  shapes, exact openers, machine tells, vocabulary) does report the true population and the
  "not shown" remainder rather than silently truncating, consistent with the module's own
  stated Hard Rule 0 fixes.

- **`src/ledger.py`** — read in full, aside from the one stale citation above. The
  `assay_to_standards` M10-edge-case fix (avoiding `hi == lo` collapsing the log-range to a
  point) is internally consistent with the stated tempus.py precedent. `CURRENCIES` and
  `CONDENSATES` are fixed reference tables, not rosters subject to a cap. `to_standards`/
  `from_standards`/`cross_rate` correctly propagate `None` for a non-convertible currency
  without guessing.

- **`src/chord_field.py`** — read in full. Pure physics/reference-data module, no I/O, no
  exception handling, no rosters. Cross-file citations checked: `tempus.py:45` does name
  `chord_field.py` as claimed, and `derivation.py:148`'s claimed beta-bit values (64, 96, 8, 0,
  128, 32 for A1-A6) match `ADJUDICATIONS` exactly. Nothing found.

---

## Summary

- 3 DEFECT findings (all stale line-number citations, all mechanically verified against
  current source): `overnight.py:1686-1688` (7 wrong citations in one comment),
  `build_terminal.py:647` (2 wrong citations), `ledger.py:43` (1 wrong citation).
- 2 QUESTION findings (low-confidence / hedged citations): `overnight.py:202` (~98-line drift
  on an already-approximate citation), `reference.py:374` (1-line drift).
- No fail-open gates, no re-implemented safety checks, no tautological/undefined-name guards,
  no undisclosed caps/truncation, and no silent failures were found in any of the nine
  modules. `silence.py` and `chain.py` in particular — the two modules where a silent failure
  or a broken tamper-evidence chain would be most serious — were read with that specifically
  in mind and came back clean.
