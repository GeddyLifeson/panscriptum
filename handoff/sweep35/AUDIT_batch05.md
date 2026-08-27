# SWEEP35 batch 05 — foreman.py, silence.py, onomast.py, worldseed.py, coverage.py, propagation.py, audit.py

Read all 7 modules in full (3,579 lines). foreman.py in particular is extraordinarily
well-hardened already — nearly every category-1..5 shape I checked (discarded write verdicts,
swallowed failures, wrong-precondition remedies, tautological guards, silent caps) had already
been found and fixed in a prior run, with the fix and the original defect both documented at
length in comments. Cross-checked every `REMEDIES` dict key against `standards.py` standard
names — all match, no orphaned remedy mappings. propagation.py and audit.py had nothing new;
their one open finding each (propagation.py:62-64, none for audit.py) already exists or wasn't
warranted. worldseed.py's two open findings (era/condition vocabulary table, dead
`unreachable_by_url`) were re-verified as accurate and not re-filed.

## Findings filed (5)

1. **silence.py:120-125,477-480** (RUN/MAJOR) — `_handlers()` and `instrument()` both wrap
   `ast.parse()` in `except Exception:` and swallow it (`return []` / `continue`) with no
   `note()`, no print, nothing recorded. A file that cannot be read or fails to parse is
   silently indistinguishable from a file with zero exception handlers — the exact "unreadable
   must never look like empty" defect this module's own docstring exists to end, found inside
   the module itself.

2. **onomast.py:428-429** (LOCAL/MAJOR) — `main()` discards `silence.write_json()`'s return
   and unconditionally prints `"wrote {OUT}"`. A denied replace (reader holding
   ONOMASTICON.json open) is reported as a successful write. `worldseed.py:332-335` checks the
   identical call correctly — onomast.py is the sibling that was missed.

3. **coverage.py:251-253** (LOCAL/MAJOR) — same shape: `silence.write_json()`'s return is
   discarded, `"per-source table -> {OUT}"` prints unconditionally, and `main()` returns 0
   regardless. COVERAGE.json is read by the dashboard, standards and the published page per
   the comment immediately above the call.

4. **coverage.py:234-237** (LOCAL/MINOR) — `BEST COVERED` hard-caps to `[:10]` with no
   disclosure, unlike the `WORST COVERED` section 11 lines above it, which explicitly reports
   "showing N of M; K more not shown, --show to raise" and exposes a flag to lift the cap.

5. **onomast.py:311-334,385** (OWNER/MAJOR) — `register_for()`'s documented genre+feature
   blend (`FEATURE_SHIFT`/`GENRE_WEIGHT`/`FEATURE_WEIGHT`) is unreachable from its only
   production call site. `name_worlds()` calls `register_for(v["continuity_group"])` with no
   `genre_register`/`features` argument, so the function's first branch (hash-of-group-id
   fallback) fires every time — the exact defect the docstring says was already fixed
   ("gave Alien and Doom the flowing elvish sound and denied Greek myth the classical one").
   `RESOLVED_ENTITIES.json` (the sole input to `name_worlds`) carries no genre/features field
   at all, so the gap is structural, not a missed keyword.

## Coverage recorded

`sweep_plan.record('run35', [foreman.py, silence.py, onomast.py, worldseed.py, coverage.py,
propagation.py, audit.py], batch=5)`
