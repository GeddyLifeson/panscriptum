# sweep42 batch 6 audit

Modules read in full: `src/mutate.py` (1957 lines), `src/generate.py` (788 lines),
`src/secondopinion.py` (623 lines), `src/autostart.py` (503 lines), `src/prose_gate.py`
(403 lines), `src/catalogue_aurora.py` (325 lines), `src/scope.py` (276 lines),
`src/scale_theories.py` (175 lines), `src/module_index.py` (117 lines).

General note: this is an unusually mature, heavily self-audited slice of the codebase --
almost every file carries multi-paragraph docstrings citing prior incidents and "order
<hash>" fixes for exactly the defect classes this sweep looks for (silent truncation,
swallowed exceptions, checks that can't fail, unverified writes). Most of the obvious
shapes have already been found and repaired by earlier sweeps. What follows is what is
still actually wrong, not a re-statement of the history already written into the comments.

## Confirmed defects

### 1. `src/generate.py:656-671` -- the meta-language check can crash the whole multi-hour run

```python
try:
    import pipeline as _PL
    _PL.assert_in_universe(text, where=job["address"])
except ImportError:
    silence.note("generate.py:meta-ban-unavailable")
except ValueError as _meta:
    fail_count += 1
    failures[job["address"]] = {...}
    save_json(cfg["paths"]["failures"], failures)
    continue
```

This sits inside the per-job loop in `main()`, immediately after the `generate_job(...)` call,
which *is* wrapped in a broad `except Exception as e:` for the explicit, documented reason that
"one bad chapter must not end a multi-hour pass" (the same rationale is repeated almost verbatim
at `save_raw`'s docstring and at the `compress_store.store()` call three blocks later, both of
which catch `Exception`). This block is the one place in the same loop that catches only
`ImportError` and `ValueError`. `pipeline.assert_in_universe()` today only ever raises
`ValueError` (via `meta_violations()`, which is a `re.finditer` over a string), so this does not
currently misfire -- but it is a live landmine: any future change to `pipeline.py` that makes
`meta_violations`/`assert_in_universe` raise anything else (an `AttributeError` from a refactor,
a `TypeError` from an unexpected `text` type, an import-time side effect) propagates straight out
of the `for job in tqdm(pending, ...)` loop with no enclosing handler, killing `main()` and every
still-pending job in the run -- the exact "OPERATOR, not MANAGER" failure this file's own
comments describe fixing everywhere else in this same loop.

Confidence: medium-high on the inconsistency (it plainly does not match the file's own stated
design rule for this loop); low that it fires today given `assert_in_universe`'s current body.

### 2. `src/scale_theories.py:23-27` -- five physics constants declared, never used, already flagged as this exact shape elsewhere

```python
C_LIGHT = 2.99792458e8
G_NEWTON = 6.67430e-11
HBAR = 1.054571817e-34
NUCLEAR_DENSITY = 2.3e17
PLANCK_LENGTH = 1.616255e-35
```

None of these five names appear anywhere else in `scale_theories.py` (verified by grep over the
whole file). The numbers they hold were clearly used by hand to compute the prose in `THEORIES`
(e.g. T2's "`m*c^2 = 6.3e18 J`" is `70 * C_LIGHT**2`, and T1's "past nuclear saturation
(2.3e17 kg/m^3)" is `NUCLEAR_DENSITY`) but the constants themselves are dead: nothing computes
those prose numbers from them, and nothing would notice if the constants and the prose strings
ever disagreed.

This is not a one-off oversight -- it is the identical defect shape this project already found
and fixed in a sibling module. `src/tempus.py:39-44` removed its own local `SECONDS_PER_YEAR`/
`C_LIGHT` with the comment: "This module used to declare its own SECONDS_PER_YEAR and C_LIGHT,
unused anywhere below and unread by anything that imports tempus -- a fifth and a fourth
hand-copied instance of quantities already declared in cosmography.py, chord_field.py,
descending_ladder.py **and scale_theories.py**." `descending_ladder.py:46` independently notes
"scale_theories.py names the same value as G_NEWTON." So a previous sweep (run35 batch 6, per the
tempus.py comment) already identified `scale_theories.py` as one of the modules holding a
hand-copied, drift-prone constant, cleaned up the sibling copy, and left this file's own
copy in place, unused.

Confidence: high. Verified by grep that none of the five names are referenced again in the file.

## Questions (possibly deliberate, not fixes)

- `src/mutate.py:226-227` -- `json.dumps(rec)[:160]` in the "a mutation run is already active"
  `RuntimeError` message has no ellipsis/`(+N more)` marker, unlike `secondopinion.py::_message()`
  and `prose_gate.assert_block_complete()`'s `missing[:6]` handling elsewhere in this same
  codebase, which always mark a display cut. This is consistent with how this file's own
  `TOOL ERROR (...)`-style diagnostic truncations are written elsewhere (e.g. `mutate.py:814`,
  `secondopinion.py`'s `[:200]` subprocess-error cuts), so it reads as house style for a
  diagnostic message rather than a Hard-Rule-0 "listing a person reads to decide" violation --
  flagging only because it is the one such cut in these nine files with no marker at all.

- `src/prose_gate.py:394-401` (`unearned_instrument`) extracts an entry's name from the first
  line of its `◈` block via `head.strip().strip("*").strip()` then strips a trailing
  `"(...)"` clause. This matches the entry template's stated header shape
  (`◈ ENTRY NAME (local name; ...)`, per `prompts/system_style.txt:105`) exactly, so it is very
  likely fine as written -- flagged only because it is the one name-matching heuristic in this
  batch that assumes one specific header shape with no fallback, unlike the looser `_covered()`
  check in `generate.py` it sits beside.

## Coverage

Recorded via `sweep_plan.record`.
