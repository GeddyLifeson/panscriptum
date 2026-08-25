# Batch 18 — run33 — `secondopinion.py`, read by the maintenance run itself

Modules read: `secondopinion.py` (312 lines), in full.

**Why this exists as an eighteenth batch, and why it matters more than the seventeenth.** This
module landed in `src/` at **15:41**, from the same concurrent session that added `corpus_db.py`
at 15:38 — after the run33 sweep partition, after the seventeenth batch, and after the drill had
already been launched. It carries **one dead function**, `ran_clean()` at line 185, and that
single finding took the project's liveness count from **38 to 39 against a ratchet ceiling of
38**. `drill.py` breached on `no NEW dead code or unfailable check has appeared` and **raised
`DRILL_BREACH`, halting the library.**

That halt is correct behaviour and is documented at the top of `HANDOFF.md`. Nothing in this
report proposes lifting it.

## FINDINGS

### 1. secondopinion.py:185 — `ran_clean()` has no callers  [severity: MINOR]

```python
def ran_clean(got):
    """-> True only if every tool RAN and found nothing. Absent is not clean."""
    return all(v["status"] == "RAN" and not v["findings"] for v in got.values())
```

`grep -rn "ran_clean" src/` returns exactly one line: the definition. Its sibling `missing()`
directly below it is used; this is not.

**This is almost certainly an in-flight module rather than a defect.** It is minutes old, it is a
natural public helper for the shape the module is building, and it encodes the module's own
central doctrine — *absent is not clean*. The likeliest resolution is that the session writing it
adds the caller and the count returns to 38 by itself.

**Not fixed by run #33, deliberately.** Editing a file another session is actively authoring
risks clobbering their work, and the two candidate fixes — wire up the caller, or delete the
helper — are both decisions for its author. **Do not raise `LIVENESS_CEILING` to clear this.**
The drill's own expectation line says it outright: *"the ceiling is a ratchet: lower it when you
clean up, never raise it to go green."*

## VERIFIED, NOT A FINDING

The module's stated purpose is sound and unusually well aimed at this project's actual blind
spot: every detector in `src/` was written by one author in one week from one theory of what a
defect looks like, so `liveness.py`, `silence.py` and `publish.scan_for_secrets` are three layers
sharing one failure mode. Running `ruff`, `vulture` and `detect-secrets` beside them buys genuine
independence rather than a fourth restatement of the same opinion. That directly serves the
INDEPENDENT property Hard Rule -1 demands and which this project has been bitten by before (the
`overnight.py` prose gate reimplemented with `bool()`).

`run()` returning a `status` of `NOT INSTALLED` rather than an empty finding list is the correct
and non-obvious choice — an absent tool producing no findings is indistinguishable from a clean
bill of health, which is this project's single most repeated bug. `missing()` and the loud
`report()` treatment make absence a third answer. Correct as written.

The disagreement doctrine — *theirs-not-mine* is a blind spot to file, *mine-not-theirs* is
either a sharper check or a false positive and is filed at INFO rather than auto-suppressed —
is the right reading in both directions.

## CLEAN

The three tool wrappers, the per-tool exception isolation in `run()` (one tool erroring cannot
cost the other two their answer, the same error-resilience `binding_health.run` uses), and the
`mine_says()` comparison path all read correctly.
