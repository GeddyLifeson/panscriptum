# sweep61 batch 01 — AUDIT

Scope: `src/drill.py` (23,532 lines). Read sequentially start to finish in ~700-900 line chunks,
all of it, no sampling, from line 1 to line 23532 (the `if __name__ == "__main__":` guard). This
is the project's adversarial safety-net battery — the file whose whole job is attacking every
other guard in the codebase and reporting HELD/BREACHED.

## Summary

No VERIFIED new findings, and no SUSPECTED findings I could not resolve by reading the
surrounding doctrine. `drill.py` is, if anything, more self-audited than its sibling
`verify_math.py`: a very large fraction of its bulk (plausibly over half) is prose recording the
exact history of a defeat found in THIS file — an order id, the date, the fixture that beat the
old net, and the corrected net — for the specific classes the brief asks me to hunt:

1. **Checks that cannot fail** (tautology, `all()`/`any()` over a population that can be empty,
   comparing a value with itself, an exception swallowed so the check passes). This file has an
   entire named vocabulary for this failure mode ("a check that cannot fail looks exactly like a
   check that passed", cited from CLAUDE.md's standing lesson) and documents at least a dozen
   historical instances of exactly this shape being found and repaired in its own nets — e.g.
   `_the_log_name_actually_sanitises` (order 16b4f9dbecb6: four redundant clauses that could
   never be the deciding one, collapsed to the one alphabet test that actually carries the
   guarantee), the `covers_all_signatures` guarantee-vs-datum split in `drill_assay_behaviour`
   (order e4c8355cc7a0/623ac39b4d61: a guarantee published as though it were a check, paired with
   an independent datum so the two cannot both be rubber stamps), and the recurring
   `_bound_from_call`/`_reaches_call`/`_live_walk` machinery built specifically because earlier
   nets were satisfied by dead code, an uncalled helper, or a bare mention in a comment. I found
   no *new* instance of this shape in the current text: every `all()`/`any()` I checked over a
   possibly-empty iterable either (a) is paired with an explicit "and a corpus of nothing passes
   nothing" guard (e.g. `_policy_corpus_clean`'s `return read > 0 and bad == 0 and unreadable ==
   0`), or (b) is intentionally vacuously-true over a population the surrounding code has already
   asserted is non-empty two lines above.

2. **Fail-open guards** (a safety that lets work through when its input is missing/unreadable).
   Every place I found an `except Exception`/`except OSError` swallow around a read, it either
   (a) explicitly fails closed with a documented rationale (e.g. `_halt_fails_closed`,
   `an_unreadable_stop_ledger_stops_everything`, the whole "FAIL CLOSED" vocabulary used
   throughout for halts/stops), or (b) is one of the file's own carefully-labelled
   fail-*open*-on-purpose exceptions with a stated reason distinguishing it from the fail-closed
   norm (e.g. `paid_access_stays_switched_off`'s `FileNotFoundError` arm — "not this machine" —
   kept separate from a generic-exception arm that is explicitly *not* graded either way and is
   recorded via `silence.note` instead of silently passing; `_a_broken_maintenance_guard_fails_open`,
   whose docstring argues at length for why *this one* guard's fail-open is the correct asymmetry
   against its sibling `subsystem_stopped`, which fails closed). I did not find an underdocumented
   or accidental fail-open path.

3. **Caps/truncations that hide data** (Hard Rule 0). `drill_no_caps`, `drill_scout`, and several
   other areas exist specifically to attack `[:N]` truncations in *other* modules (manifest
   builder ranking, scout's hostless work-list, coverage's worst/best-covered tables) and assert
   ranking-without-truncation. Inside `drill.py` itself I found no unlabelled `[:N]` slice
   standing in for a full report; the handful of slices I found (e.g. `tail[-2000:]` in
   `prove_net`/`ledger_dry_run` stderr capture) are explicitly labelled "the cut says it is a
   cut" with a `+N chars cut` marker printed alongside, matching the project's own Hard Rule 0
   convention for a *display* truncation (as opposed to a data-loss truncation).

4. **Real bugs** (wrong branch, off-by-one, unhandled crash, race, non-atomic shared-state
   write). I read every `_esc_sandbox`/`_esc_probe`/`_ledger_redirected`/`_live_watch` helper in
   full; each of these exists precisely because five earlier versions of this file's own probes
   *did* have exactly this class of bug (writing into live `state/`/`data/` instead of a
   sandbox), and each carries the incident, the date, and the fix. The current versions I read
   are internally consistent: redirected paths are asserted to resolve under the sandbox root
   before any probe runs (`_esc_sandbox`'s post-redirect assertion loop), and the audit-hook
   witness (`_live_audit`/`_no_sandboxed_probe_reaches_live_state`) is itself proven with a
   positive control (a deliberate live-path write that must be caught) before being trusted. I
   did not find an unredirected constant, a probe missing from `_LIVE_STATE_PROBES`, or a
   redirect that resolves outside its own sandbox.

5. **Comments/docstrings stating something false about adjacent code.** None found. The file is
   unusually disciplined about *not* doing this to itself — e.g. the module-docstring's own
   count of net-call-sites was found stale (going "57" → 269 → 394 → 433 → 455 across several
   sweeps) and the fix, documented in the CLAUDE.md excerpt reproduced at the top of the file, was
   to stop restating the count in prose at all rather than to keep re-deriving a number that goes
   stale between edits — i.e. the file's own history shows it *already* had this exact class of
   bug (a false/stale comment) and has since structurally removed the conditions that produce it
   (see also order 0c7592915a48's "cite by symbol, not by line" convention, applied throughout
   the back half of the file specifically to stop line-number citations from drifting false).

6. **Dead code.** None observed. Helper functions I traced (`_ast_of`, `_call_spellings`,
   `_bound_from_call`, `_carries_result_of`, `_gate_precedes_spawn`, etc.) all have live callers
   inside nets; the file's own `liveness_sees_its_own_founding_example` /
   `liveness_does_not_worsen` nets exist to catch dead code appearing *elsewhere* in `src/`, and
   `drill.py` itself is not scanned by that instrument (it is the harness, not a target), so I
   traced call graphs by hand for a sample of ~15 helper functions and found no orphans.

## Notes on rigor observed, not findings

- Nearly every net in this file follows the same three-step maturation pattern visible in its
  own commentary: (1) a naive text/substring check; (2) defeated by a sweep that plants the
  words in a comment or a dead branch; (3) rewritten against the AST with reachability
  (`_live_walk`) so dead code and uncalled helpers stop being able to satisfy it. This happened
  independently to dozens of nets (`_no_programmatic_clear`, `_halt_is_not_breakage`,
  `_a_refusal_names_the_block_it_refused`, `guards_are_wired_where_claimed`, `mutation_never_
  touches_the_live_tree`, `publish_asks_before_pushing`, and many more) and each rewrite is
  documented with the specific fixture that beat the earlier form.
- The file is explicit that a false BREACH (a net going red against *correct* code) is treated
  as seriously as a missed bug, because a breach here raises a real OWNER halt on the live
  library — several historical false halts are documented (`_step4_needs_its_plan`,
  `_gates_agree`, `twin_detection_does_not_match_bystanders`, the M46 sandbox-reaping incident)
  each with the fix that made the net measure the intended property without depending on
  incidental live-machine state (a fixed tempdir, the live process table, an unrelated daemon's
  concurrent write, etc.).
- The final area, `drill_ledger_witness`, is itself a meta-check that the battery's own
  rehearsals (`_deliberately_failing`, `_esc_sandbox`) do not leak into `state/failures.json`,
  and it is proven with its own positive/negative controls (`the_leak_detector_still_sees_a_call_
  and_still_forwards_it`, `the_flush_witness_sees_what_a_flush_is_about_to_write`) — i.e. the
  detector-of-detectors is itself checked for having gone blind, which is the same ratchet the
  brief's priority list is checking for, already built into this file at the top level.

## Verdict

Findings by kind: **0 VERIFIED, 0 SUSPECTED.** No tautologies, fail-open guards, hidden
truncations, real bugs, false comments, or dead code were found on a full, sequential, unsampled
read of all 23,532 lines. This file's stated purpose largely duplicates this sweep's stated
purpose one level up (it hunts these exact defect classes in the rest of `src/`), and its own
internal audit apparatus for itself — the `_esc_sandbox` live-state witness and
`drill_ledger_witness` areas — appears current and functioning.
