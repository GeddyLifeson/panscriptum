# Sweep 43 — Batch 07 audit

Files read in full: `src/feats.py` (1900 lines), `src/generate.py` (803 lines),
`src/threads.py` (630 lines), `src/handbuilt.py` (516 lines), `src/catalogue_codex.py`
(404 lines), `src/grounding.py` (334 lines), `src/recover_folder_records.py` (286 lines),
`src/chord_field.py` (210 lines).

**Context for the reader of this report.** All eight files are unusually heavily
self-audited already — most carry extensive inline comments documenting a previous defect,
the order that filed it, and the exact fix, including several Hard Rule 0 cap removals, the
roll/compare-and-swap migration, and multiple exit-code-reaches-the-process-boundary fixes.
The great majority of candidate faults I considered while reading turned out to already be
fixed and documented as such. What follows is what survived verification against the actual
source, not a restatement of the in-file history.

---

## src/feats.py

No BLOCKING or MAJOR findings. The module is internally consistent: `_api_list_all`'s
continuation-following is correct and its two `_CAP_BOUND` increments are reached only on a
genuine partial read; `discover()`'s `extra` refusal, `resolve_title`'s uncapped `srlimit`
walk, `_units`/`_UNIT_DROPS` tallying, and the three-way `alive_verdict` (True/False/None)
all do what their docstrings say when traced against the code around them.

**MINOR — `axis_evidence()` is dead code.**
`src/feats.py:1301` — `def axis_evidence(sentence, axis):`
Verified with `grep -rn "axis_evidence" src/*.py` (excluding `__pycache__`): the only match
in the entire `src/` tree is the definition itself. `by_axis()` (the function that actually
runs per axis during a roll) does not call it — its own comment at line ~1367 says the
identical three-gate check (statblock / patient / object-or-magnitude-or-comparative) was
"hoisted" out of a per-axis loop and inlined there instead, i.e. `axis_evidence`'s logic was
duplicated rather than reused, and the function itself now has no caller anywhere. Not a
correctness bug — it isn't wired into any check that could silently no-op — but this
codebase's own stated concern (Hard Rule -1's coda: "a check that cannot fail looks exactly
like a check that passed — dead code, tautological comparisons...") is exactly the shape of
an unused, never-exercised predicate sitting beside the one that matters. Remedy: either
delete `axis_evidence` (nothing depends on it) or wire `by_axis` to call it instead of
duplicating its body, whichever the owner prefers — a genuine judgment call, not a mechanical
fix, since deleting a public function is covered by this sweep's "review cycle" rule.

Everything else examined in this file (the `_HOST_LOCKS`/`_COUNTS_LOCK` split, `_throttle`/
`note_throttled`/`note_ok` backoff arithmetic, `page_looks_real`'s three layers,
`mined_under_superseded_gate` / `mined_without_name_matching` staleness predicates,
`_unwrap_templates`'s brace/param handling, the `_QUANTITY` regex's group numbering used in
`mine()`, `resolve_hosts`'s null-vs-undetermined handling, `resolve_title`'s ranking) traced
correctly against a hand-run of the logic. `backoff_state()` looked like dead code in
isolation but has a live caller in `src/dashboard.py:610` — not a finding.

---

## src/generate.py

No BLOCKING or MAJOR findings. `generate_job`'s block-retry logic for both the "feats" job
type and the ordinary entries path re-derives `lacking` against whichever text (original or
retry) was actually kept, in both branches — traced line by line, no stale-`lacking`-after-
retry bug. `ChapterRefused`'s two truncated-sentence-but-full-`lists` sites (`missing[:8]`,
`_unearned[:5]`) match the class's own docstring and `main()`'s `.update(getattr(e, "lists",
{}))` handling. The prose-gate ordering (Hard Rule -1's plant-wide interlock, then the P8
meta-language ban with the broadened `except Exception`, then `save_raw`, then
`compress_store.store`) is sequenced so a failure anywhere in that chain lands in
`failures.json` and does not end the run, and the final `catalog`/`failures` writes correctly
gate the process exit code. No cap on any listing was found in this file.

No findings to report.

---

## src/threads.py

No BLOCKING or MAJOR findings. `cohort_family`, `_resolves`, `edge()`'s two refusals,
`category_path`'s `subroom`-then-`topic` fallback, `build()`'s per-room sibling matching, and
`counts()`'s T2 arithmetic all check out against the numbers their own comments cite. The
`verify()` round-trip design (checking the *serialized-and-reparsed* graph rather than the
in-memory one `build()` just returned) is sound and its own docstring's account of why the
four original checks were tautologies is accurate. The one `[:2]` in the file
(`cohort_family`'s `parts[:2]`) is a Collection.Set decomposition, not a truncation of a
listing, exactly as the module docstring says.

No findings to report.

---

## src/handbuilt.py

This file is almost entirely hand-transcribed data (nine hand-built Assay sheets) plus a
thin `compute()`/`main()` harness. The harness is short and correct: `compute()` iterates
`rec["axes"].items()` (all eleven axes present on every sheet), `main()` writes the JSON
artifact before printing (documented reason: a `cp1252`-console crash on the Fraktur "𝔄"
character must not cost the file), and the `--full` score formatter correctly branches on
`isinstance(score, (int, float))` to handle Zalama's six `"unestimable"` string sentinels
without a `TypeError`. No cap, no truncation, no inverted predicate found.

No findings to report.

---

## src/catalogue_codex.py

No BLOCKING or MAJOR findings. `parse_codex`'s per-section regex, `sec_by_norm`'s collision
reporting (keeps first, reports the rest as unreachable — uncapped), the exact-match-first /
ambiguous-substring-refuses-rather-than-guesses section binding, and
`load_register_index`'s all-collisions-kept index all match their documented intent.
`record_path`/`slug` are correctly deferred imports from `catalogue_aurora` to avoid the
circular-import the comment describes. The roll-write path (`roll.update_rows` compare-and-
swap, gated per-record write, denied-write reaching the exit code) is consistent with the
sibling fix already applied in `recover_folder_records.py` (see below) — this file got the
"don't mutate the in-memory roll row any more" fix (order `09f3105df988`) that the sibling
file did not.

No findings to report (see the cross-file finding below, filed under
`recover_folder_records.py`, which this file's own comment is the evidence for).

---

## src/grounding.py

No BLOCKING or MAJOR findings. `classify_text`'s uncapped ranking, `classify_source`'s
refusal of a numeric `cap`, the whole-field confidence denominator, and `A.regress_test`
being called with `spec["regress"]` (which correctly omits `claims_to_be_the_ground` for the
two grounding types where `assay.regress_test`'s own default of `False` is the right value)
all check out.

**MINOR — diagnostic print can truncate a source name mid-word with no indication.**
`src/grounding.py:308` — `print(f"   {s[:28]:<30}{v['grounding']:<15}{v['confidence']:.2f}  vs {ru}")`
`s` here is `r["name"]` from the live corpus (not the fixed nine-item SAMPLE list at line
~288, whose entries are all short by construction). The "contested cosmogonies" diagnostic
loop (`low`, built at line 295) is explicitly documented one paragraph above as deliberately
**uncapped as a list** ("NOTHING IS CAPPED HERE... the runners-up on each line are uncapped
too") — but the per-row *name* is still sliced to 28 characters with no marker, which is the
identical defect this same codebase already found and fixed once, in `feats.py` (order
`b0e69b869473`, `_show()`'s `t[:60]`/`why[:80]` and the host-probe printer's `_src[:44]`):
"a truncated NAME is worse than a truncated list, because it still looks like an entry the
operator can act on." Measured against the corpus: source names run past 28 characters in
the wild (`feats.py`'s own comment cites 11 names over 44 characters, e.g. "Kobold Press
(Midgard Heroes Handbook, Midga..."), so a genuinely contested long-named source's row would
print with its name cut mid-word and no `...` or count to say so. This is cosmetic (the
underlying `low` list and `runners_up` are not truncated, only the printed column), but it is
the exact pattern the project's own precedent treats as worth fixing. The sibling line at
line 293 (`s[:26]` in the fixed SAMPLE loop) is not a finding — every name in that literal
tuple is well under 26 characters, so it cannot truncate in practice.
Remedy (mechanical): drop the `[:28]` slice and keep the `:<30` left-pad, the way
`feats.py`'s own fix did — a `LOCAL` fix.

---

## src/recover_folder_records.py

**MINOR — dead mutation of the in-memory roll row (same defect already fixed once in this
tree, uncorrected here).**
`src/recover_folder_records.py:226-227`:
```python
roll_entry["entry_count"] = len(entries)
roll_entry["status"] = "catalogued"
```
`roll_entry` (`= roll_by_name[name]`, bound at line 189) is a row from the `roll` list read
once at the top of `main()` (line 101). Verified with `grep -n "roll\b|roll_entry|roll_by_name|roll_changes"`:
after these two lines, `roll_entry` and the enclosing `roll`/`roll_by_name` structures are
never read again — persistence goes exclusively through `roll_changes[name] = {...}` (the
very next line, 228) and `roll.update_rows(roll_changes, path=ROLL)` at line 242, which reads
a **freshly-loaded** copy of `SWEEP_ROLL.json` from disk and merges only `roll_changes` into
it. So lines 226-227 mutate an object that is discarded without ever being written or read
again — they do nothing.

This is not a fresh bug (nothing downstream is fooled; the compare-and-swap write is
correct), but it is the identical shape of a defect this same codebase already diagnosed and
fixed, in the sibling file `catalogue_codex.py:343-349`, whose comment reads almost word for
word: *"`r["entry_count"] = ...` / `r["status"] = ...` any more (order 09f3105df988)... `r`
is a row of the in-memory `roll` list read once at the top of this function; since the
compare-and-swap migration... persistence goes exclusively through `roll_changes`... so
mutating `r` was a leftover of the whole-document write this function used to do and was
never read again — it made the in-memory roll look like it was still the thing being
persisted, which is exactly the misreading that migration was filed to end."* That fix was
applied to `catalogue_codex.py` and never carried over to this file, which does the same
compare-and-swap migration two lines below (line 236's own comment: *"ATOMIC: ... AND A
COMPARE-AND-SWAP RATHER THAN A WHOLE-DOCUMENT LAND"*) while still carrying the exact leftover
mutation the sibling module named and removed.

Severity kept at MINOR rather than MAJOR because nothing downstream reads the mutated object
— it is misleading dead code, not a live data-corruption path. Remedy: delete the two lines,
mirroring `catalogue_codex.py`'s own fix.

---

## src/chord_field.py

No findings. Pure data table (`ADJUDICATIONS`) plus four short formula functions
(`landauer_floor`, `recoil_momentum`, `recoil_velocity`, `critical_power_self_focus`). Spot-
checked the physics: Landauer's bound (`bits * k_B * T * ln 2`), momentum-energy relation
(`p = E/c`), and the Kerr self-focusing critical-power formula (`3.77 λ² / (8π n0 n2)`) are
all textbook-standard and correctly transcribed. No cap, no truncated list (there is no list
in this file), no dead code — `C_LIGHT` and `K_BOLTZMANN` are both used by name; the file's
own comment already documents removing `G_NEWTON`/`HBAR` for being unused.

---

## Questions for the owner

None raised in this batch — every candidate ambiguity I found while reading (e.g.
`grounding.py`'s SAMPLE-list truncation at line 293, which is harmless in practice) resolved
cleanly to either "not a finding" or a mechanical fix, not a curatorial judgment call. The one
item that is a genuine judgment call — whether to delete `feats.axis_evidence` or wire it into
`by_axis` — is filed as an OWNER work order below rather than asked here, since it is a small,
self-contained decision with no live consequence either way.
