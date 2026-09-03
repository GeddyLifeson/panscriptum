# Sweep42 batch 1 — audit of src/drill.py

Auditor: sweep42 batch 1 (read-only; no files edited except this one).
Scope: `src/drill.py` (10,639 lines), read in full, end to end, in ~800-1000 line chunks.
Also read `CLAUDE.md` for house rules before starting.

## Method / context

`drill.py` is the library's own adversarial safety-net tester. It is exceptionally
self-critical: essentially every function's docstring documents a *previous* defeat of that
same net (an "order" number, a "run #NN sweep"), what the defeat exploited, and how the net
was rewritten to close it. The file explicitly tracks and ratchets its own dead-code /
unfailable-check count (`LIVENESS_CEILING`) and has clearly been through many prior audit
passes. Because of that history, most of what a first-pass audit would normally flag (bare
`except: pass`, truncation, checks pinned to prose instead of behaviour, checks that cannot
fail) has already been found and rewritten, with the reasoning for each fix left in place as a
paragraph. I read every one of those paragraphs against the code beneath it to check that the
current code still matches the claim, rather than assuming the narrative is up to date.

I did not have the other modules in this batch (`escalation.py`, `prose_gate.py`, `pipeline.py`,
etc.), so I could not re-verify drill.py's claims against their actual current behaviour — only
against drill.py's own internal consistency (docstring claims vs. code, test coverage vs. the
defeats a docstring says the code now prevents).

## Confirmed defects

**None found with high confidence.** After a full read I found one real, moderate-confidence
coverage gap (below) but no swallowed exception, no truncation, no tautological/unfailable
check, and no diagnostic cut short *in drill.py's own current code*. Every `except Exception`
site I checked (lines 328, 1319-1327, 1998-2000, 2949-2951, 5075-5076, 5244-5246, 6384-6385,
6477-6479, 6559-6561, 6580-6582, 6623-6625, 8059-8060, 8235-8239, 9321-9322, 10049-10050,
10276-10278, 10550-10570, 10597-10598) is either (a) a deliberate "any exception here is
evidence of refusal" pattern used consistently throughout the file, (b) wrapped with
`silence.note(...)` so the swallow is recorded rather than silent, or (c) best-effort cleanup of
a scratch/temp resource where failure is explicitly not meant to fail the net (and is itself
noted). All of the `[:N]`-shaped grep hits are **historical prose** describing an
already-fixed defect in a *different* module (pipeline.py, local_agent.py, policy.py) — not
live truncation in drill.py's current code or output. `main()`'s own report loop and halt
message were themselves already rewritten (per in-file history, orders 6e7ecf6b9fbd and
2f679246a6e4) to stop truncating the breached-net list and the "expected" text, and I confirmed
the current code (lines 10490-10511, 10609-10621) matches that: every breach is printed by name,
uncapped, with a non-empty expectation string or an explicit placeholder.

### 1. `_no_programmatic_clear`'s 5th (bound-name-alias) detection has no dedicated regression net — MEDIUM confidence

- **File:line**: `src/drill.py:3107-3212` (function `_no_programmatic_clear`), regression-tested
  by `src/drill.py:8684-8721` (`_a_scan_can_tell_code_from_prose_about_code`); the only caller is
  `src/drill.py:6018` (`drill_park`'s "no module in src/ clears the halt programmatically" net).
- **What I found**: `_no_programmatic_clear`'s own docstring (line 3130-3135) documents a fifth
  historical defeat, filed as order `f016ae5433b1`: `f = escalation.clear` followed by `f(ruling)`
  (and chains like `f = escalation.clear; g = f; g(...)`) walked past the first four spellings the
  function checked, so a fixpoint alias-tracking loop was added (lines 3183-3196) to bind a plain
  name to "the release function" when it is assigned the value of `escalation.clear`,
  `X.clear`, `from-import clear`, or `getattr(mod, "clear")`, and to catch calls through any name
  in that closure.

  `_a_scan_can_tell_code_from_prose_about_code` is the dedicated net that proves
  `_no_programmatic_clear` still refuses each of the spellings it claims to catch, built exactly
  because a plain substring scan can be fooled by a comment describing the rule. It drives four
  fixtures (lines 8707-8711):
  ```
  "import escalation\nescalation.clear('x')\n",
  "import escalation as X\nX.clear('x')\n",
  "from escalation import clear\nclear('x')\n",
  "import escalation as e\ngetattr(e, 'clear')('x')\n"
  ```
  There is no fifth fixture of the shape `f = escalation.clear\nf('x')\n` (or the two-hop chain
  the docstring itself names). I grepped the whole file for anything that drives this case
  (`f016ae5433b1`, `= escalation.clear`, `= ESC.clear`, `bound.*clear`) and the only two hits are
  the docstring's own two mentions of the historical order — nothing exercises the behaviour.

  `drill_park`'s net for this function (line 6018) just calls `_no_programmatic_clear()` against
  the real, current `src/` tree, which (correctly) contains no such bypass today — so that net
  cannot exercise the alias-tracking code path either; it can only ever pass or, if the tree
  genuinely gained a bypass, breach. It gives no evidence that the *detector* still recognises the
  bound-name shape if that detection logic regresses.
- **Why it's a defect under the house rules**: this is precisely the standing lesson the file
  itself states over and over — "a guard nobody has watched refuse is a guard nobody has evidence
  about." Four of the five documented bypass classes for the halt's release have a net proving
  the fix still refuses them; the fifth (and, per the docstring, "most serious" in spirit since it
  was the one requiring a fixpoint rather than a simple alias table) does not. If a future edit to
  the alias-fixpoint loop (lines 3183-3196) silently broke it — e.g. a refactor that stopped
  tracking `ast.Assign` chains — no net in this battery would go red, because nothing currently
  drives that code path with a fixture designed to defeat it.
- **Confidence**: medium. This is a coverage gap, not a currently-wrong verdict — the detection
  code as written today does appear to close the case its docstring describes (I traced the
  fixpoint loop and it does register a chain of assignments). The finding is that nothing proves
  it keeps closing it.

## Questions (possible deliberate design, not fixes)

### Q1. Mixed feat-bearing / feat-less source selection rule is explicitly left unresolved
- **File:line**: `src/drill.py:1733-1773` (`the_feat_bearing_path_really_is_untouched`, inside
  `drill_no_caps`).
- The docstring itself flags this as open: `pipeline.synthesis_blocks` takes
  `blocks = ([with_feats chunks] or [rest chunks])`, which short-circuits so that the moment *one*
  entry in a source has a mined feat, every feat-less entry in that same source is dropped from
  nomination entirely. The comment explicitly says "No net in this area states that rule, tests
  it, or distinguishes it from the ranked truncation this area exists to forbid... it is not a
  drill's place to decide it. Order a5de2dcb9447 stays open for that ruling." I confirmed by
  reading the code that this remains true as of the current file — there is still no net that
  drives the *mixed* case (some entries with feats, some without, in the same source) and checks
  whether the feat-less ones survive. I'm surfacing this because it directly touches Hard Rule 0
  (no caps / no smaller universe), and it is worth the owner's attention even though drill.py
  correctly declines to adjudicate it itself. Not a new finding — already tracked under order
  a5de2dcb9447 — but confirmed still open.

## Coverage record

