# SWEEP35 batch 6 audit

Modules (3,611 lines, read complete, no edits made per audit-only mandate):
src/cascade_bridge.py, src/generate.py, src/identity.py, src/prose_gate.py,
src/context_budget.py, src/wh40k.py, src/chord_field.py, src/catalog.py

## New findings filed

- **134188eb2296** (RUN/MAJOR) `src/generate.py:396-401` -- when `data/COVERAGE.json` is
  unreadable, `main()` correctly refuses every job ("REFUSING EVERYTHING") but `return 0`,
  so `sys.exit(main())` reports success. Sibling of the missing-manifest bug already fixed
  this shift (which now returns 1 for that case) -- a run that generated nothing because its
  safety data was broken looks identical, on exit code, to a clean cycle.

- **70563ce550eb** (RUN/MAJOR) `src/identity.py:300-329` -- `_ask()` swallows every exception
  (transport failure, bad response) and returns `None`; `epoch_of()` then returns `""`,
  identical to the real, meaningful answer "the sentence carries no epoch marker." The two
  cases are indistinguishable downstream. `chain.adjudicate_mutuals` (chain.py:422-436)
  prints a failed probe as "neither sentence dates itself" -- a false claim about the
  evidence -- and for the EPOCH_REQUIRED hosts (mtg, forgottenrealms) a transient call
  failure silently reads as a genuine absence of epoch evidence, refusing the assay for the
  wrong stated reason.

## Checked and left alone (already covered by open orders, verified still accurate)

- `src/cascade_bridge.py` -- 9fb8a6b10c1f (no reachable model). Re-read the full 1,410 lines;
  no new fail-open/swallowed-failure defect found. The paid-lane removal, bench/pace logic,
  and unrecognised-failure classification are all internally consistent and fail closed.
- `src/prose_gate.py` -- b1f561587b19 (OWNER: the "extra entries" penalty never reaches
  `required`, so an invented entry does not move the refusal fraction). Reproduced by
  reading `section_shortfall`/`assert_block_complete` again; still present, still OWNER-held,
  untouched. No second defect found in the gate logic itself -- ghost-entry accounting,
  the evidence floor, and `unearned_instrument` all fail closed correctly.
- `src/context_budget.py` -- 96ebf36510b8 (four bare `except Exception` swallow file-read
  errors toward a larger, wrong-direction budget). Confirmed still present at the same
  lines; no additional defect found.
- `src/wh40k.py` -- 1770c2b84786 (every worksheet line stamped `[wiki]` unconditionally,
  including editorial synthesis). Confirmed still present at line 197.
- `src/chord_field.py` -- 7e360eaec3a6 (dead module, no importers). Re-verified by grep:
  only a comment in `tempus.py` mentions the module name; nothing imports it.
- `src/catalog.py` -- no open findings, none filed. Small, straightforward CLI query tool;
  not invoked as a subprocess anywhere in src/, so its exit code is not scheduler-relevant.

## Method note

Two apparent leads were checked against source and NOT filed:
- `prose_gate.unearned_instrument`'s name-stripping (`strip("*")` only, not `#`/`_`) can
  false-positive on markdown-headed entity names, but the failure direction is stricter
  (blocks generation that should have passed), not fail-open -- not filed.
- `generate.py`'s console-truncated print lists (`refused_src[:20]`, `missing[:8]`,
  `catalog.py`'s `missing[:30]`) all carry an honest "+N more" count and never affect which
  jobs are processed -- distinguished from a Hard-Rule-0 truncation and not filed.
