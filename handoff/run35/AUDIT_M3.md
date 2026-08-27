# Batch M3 — run35, wave 2

Owner of: src/silence.py, src/health.py, src/resonance.py, src/identity.py,
src/descending_ladder.py, src/liveness.py, src/suppressions.py, src/policy.py, src/snapshot.py,
src/completeness.py, src/estate.py, src/profile.py, src/roll.py.

## FIXED

**26be3dba65cf — src/roll.py.** `exclude()` returned `changed` (whether the in-memory row
differed) regardless of whether `silence.write_json` actually landed the write, so a denied
write to `data/SWEEP_ROLL.json` reported a successful exclusion. Now returns the write's real
verdict on the direct-write path, and `True` (meaning "your copy changed, you persist it") only
on the `rows=` caller-supplied path, `False` when nothing changed. Verified against a temp ROLL
file (never the real one): denied/landed verdicts propagate correctly, `rows=` never touches the
real path, and a typo still raises. `python -m pyflakes` clean; bare import clean.

**40b61d3a8c68 — src/resonance.py.** `hodge_decompose({})` divided by zero
(`sum(new.values())/len(new)` with `len(new)==0`), and an all-zero-flow graph returned
`eta=1.0` -- identical to a genuinely perfectly-consistent ladder. Both now return
`eta=None, no_evidence=True`, distinguishing "no contest data" from "no contradiction found."
Verified live: `hodge_decompose({})` and `hodge_decompose({('a','b'): 0.0})` both return
`no_evidence: True` with no exception; a graph with real signal still returns a numeric eta.

**45b5e706e2d6 — src/profile.py.** Two stale numeric `silence.note` tags
(`profile.py:131`, `profile.py:135`) no longer pointed at their own handlers. Renamed to
`profile.py:genres-unreadable` / `profile.py:tiers-unreadable`, matching the file's own naming
style elsewhere.

**88964707a3f7 — src/estate.py.** All seven numeric `silence.note` tags in `inspect()` had
rotted out of sync with their handlers (two pointed at each other's lines). Renamed to
content-stable tags: `stat-failed`, `json-not-utf8`, `json-malformed`, `json-unreadable`,
`text-not-utf8`, `text-unreadable`, `py-will-not-parse`.

**92a07b4ba203 — src/identity.py.** `load()`'s cache write hand-rolled `CACHE + ".tmp"` (no
pid/thread, so two concurrent `--refresh` runs shared one temp path) and discarded
`replace_retry`'s verdict. Replaced with `silence.write_json(CACHE, inv, indent=1,
sort_keys=True)`. `load()`'s contract was always "return the fresh inventory," never "return
whether it was saved," so no caller-facing behaviour changed; any denial is still recorded
internally by `write_json` -> `replace_retry` -> `note()`.

**3c86a8d541b2 — src/identity.py.** `EPOCH_REQUIRED`, `epoch_directive()` and
`epoch_acceptable()` were defined AFTER `if __name__ == "__main__": sys.exit(main())`, so a
process running `python src/identity.py` directly did not have them. Moved the whole block above
the guard (pure relocation, no logic changed). Verified: `EPOCH_REQUIRED` now appears before the
literal `if __name__ == "__main__":\n    sys.exit(main())` guard text.

**53dcfb2bd48b — src/policy.py.** `report()` hand-rolled `REPORT + ".tmp"` + `json.dump` +
`replace_retry` instead of the pid/thread-unique `silence.write_json`. Replaced with a single
`silence.write_json(REPORT, {...}, indent=1, ensure_ascii=False)` call inside the existing
try/except.

**57acf43b339a — src/descending_ladder.py.** `schwarzschild_radius()` inlined `6.67430e-11`
95 lines below the file's own "real constants (SI, cited)" block. Added `G_NEWTON` to that
block and switched `schwarzschild_radius()` to use it. (`NUCLEAR_DENSITY`'s cross-file
duplication with `scale_theories.py`, also named in this order's evidence, is a separate
dedup/ownership judgment -- left alone; `scale_theories.py` is not an owned file and unifying
the two would be a design call, not a mechanical fix.)

**9a18068421c3 — src/suppressions.py.** `_load()` collapsed "never created" and "exists but
corrupt" to the same bare `[]`, so `problems()` reported a corrupt `SUPPRESSIONS.json` as ZERO
suppression problems -- the exact "unreadable reads as empty" failure this batch's general rule
names. `_load()` now returns `(rows, ok)`; `problems()` reports an `UNREADABLE:` finding when
`ok` is False (verified: a corrupt file now reports at least one problem, a genuinely missing
file still reports zero); `active()` still fails closed (no suppressions applied when
unreadable, so detectors run in full rather than under a state nobody can confirm); `add()` now
refuses to write on top of an unreadable file rather than silently replacing it with a
list missing everything that couldn't be parsed.

## DISPROVED / already fixed

**32eaec248adf — src/health.py.** Ran `health.preflight()` live: it reports 0 problems today.
`check_caches()` already exempts quarantined hosts (`binding_health.quarantined()` includes
`www.dandwiki.com`) and prints the empty-cache count as an `info` line rather than a problem --
this exemption mechanism (comment dates it to "run #33") post-dates whatever run produced this
order's evidence. No code change needed; resolving as already fixed.

**2b102b2b3c29 — src/resonance.py.** The `sweep33/batch08` finding said
`resonance_strength()`'s default `data/SHARED_STAGE_GRAPH.json` was the OLD raw-count graph
`weave.py`'s docstring calls broken, and that the corrected file was `weave.py`'s
`SHARED_STAGE_GRAPH_IDF.json`. Reading the current `cosmology_graph.py` (the actual writer of
`SHARED_STAGE_GRAPH.json`) shows it was independently fixed on 2026-08-25 (order 9861c18b8485)
to the same idf-plus-ubiquity-penalty weighting, and its docstring explicitly names
`resonance.py:157` as this file's intended reader. `weave.py`'s `SHARED_STAGE_GRAPH_IDF.json` is
a separate artifact for its own continuity-resolution use, not a replacement `resonance.py`
should switch to. No caller currently exercises `resonance_strength()` in production, so nothing
is live-broken; resolving as already fixed at the source (cosmology_graph.py), not something to
change here.

## LEFT (real fix lies elsewhere, or a design judgment call — not resolved)

**0ea638f01b03** — the real fix is in `resync_roll.py`'s `main()` (and its siblings
`worldseed.py`, `burgs.py`), none of which are owned files. Left open.

**220a0d0a1d70** — stale numeric `silence.note` tags in `pipeline.py`, not an owned file.
Left open.

**5a9a75916f94** — `coverage._so_save()`'s hand-rolled tmp write is in `coverage.py`, which is
on the explicit must-not-edit list. Left open.

**7ed8fb99bb4c** — `pick_model.save_config()`'s hand-rolled tmp write is in `pick_model.py`, not
an owned file. Left open.

**bd33dbbb362a** — stale numeric `silence.note` tags in `standards.py`, which is on the
explicit must-not-edit list. Left open.

**c3b5aba07f4a** — `coverage._p()` dead code lives in `coverage.py` (must-not-edit) and the
order itself says report, not delete, regardless. Left open, reported.

**cfb92f76ffb1** — `corpus_db.datasette_metadata()`'s bare `open()+json.dump` is in
`corpus_db.py`, which is on the explicit must-not-edit list. Left open.

**ed5434c0bc65** — stale numeric `silence.note` tags in `cascade_bridge.py`, not an owned file.
Left open.

**671d32878fa6** — three findings bundled under one order, mixed status:
  - `descending_ladder.py:129 'from_m'` (the unused-local vulture flagged): already fixed —
    re-ran `vulture --min-confidence 90` against `src/descending_ladder.py` and it reports
    nothing. `shrink_report()`'s docstring shows `from_m` is already echoed into the returned
    dict and used in `is_descent`. No action needed on the owned file.
  - `verify_math.py:2310 'kw'`, `verify_math.py:2399 'socktype'`: real per the evidence, but
    `verify_math.py` is on the explicit must-not-edit list. Left open.
  - The "gap" itself (liveness.py's DEAD check only walks `t.body`, i.e. module-level
    `FunctionDef`/`AsyncFunctionDef` nodes, and never descends into function bodies to find
    unused locals): confirmed by reading `scan()` — this is the file's stated, deliberate scope
    (its own docstring names exactly three mechanical shapes: DEAD, TAUTOLOGY, PHANTOM; unused
    local variables is a fourth, different check vulture already covers). Widening
    `liveness.py`'s scope to duplicate vulture's variable-level check is a judgment call about
    what this detector is for, not a bug fix — left open rather than done unilaterally.
  Order not resolved; reported here as mixed FIXED-elsewhere/LEFT rather than closed.

**c16499b0a50b — src/resonance.py.** Checked the WHOLE repo, not just `src/`: `grep -rn "import
resonance\|from resonance"` over the entire tree shows the module IS imported — by
`src/verify_math.py` (a test-check harness, `RES.incomparability_rate` exercised at lines
6668-6678 under "order 602bbb05ffae") and by `handoff/run35/checks_batch6.py`. So "entirely
unimported anywhere in src/" is not quite accurate — there is a real importer inside `src/`.
That said, the underlying finding still stands in a narrower form: zero PRODUCTION callers.
`custodes.py:302`'s docstring claims `eta` "lets Threnody exercise her veto," but `custodes.py`
never imports `resonance` (confirmed by grep) — a described safety mechanism that is not
actually wired. Wiring `resonance` into `custodes.py` (or elsewhere) is a design decision
outside this order's own file and outside owned files; per instructions, reporting rather than
deleting anything, and leaving the wiring decision to whoever owns `custodes.py`. Order left
open rather than resolved, since the module-level report ("entirely unimported") is disproven
but the deeper concern it points at is real and unaddressed.

## New checks

Appended to `handoff/run35/checks_M3.py`: nine `check_<name>()` functions (roll write-verdict,
resonance no-evidence, suppressions unreadable-is-a-problem, estate/profile symbolic tags,
identity write_json + epoch-block-position, policy write_json, descending_ladder G_NEWTON).
All nine pass standalone against the current tree (`python handoff/run35/checks_M3.py`).
