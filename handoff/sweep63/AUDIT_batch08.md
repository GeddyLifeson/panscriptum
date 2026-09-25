# sweep63 batch 08 — audit report

Scope (every line read start to finish, in chunks, no sampling):

- src/cascade_bridge.py    2333 lines
- src/sweep_plan.py        1150 lines
- src/rosetta.py            815 lines
- src/runguard.py           660 lines
- src/catalogue_codex.py    515 lines
- src/suppressions.py       425 lines
- src/navtree.py            335 lines
- src/roll.py               313 lines

Total 6,546 lines, all 8 modules read in full.

## Prior-sweep context consulted

`handoff/sweep61/AUDIT_batch08.md` audited this exact set of five modules (cascade_bridge,
sweep_plan, rosetta, runguard, catalogue_codex) plus four others and found zero VERIFIED
defects. `handoff/sweep61/AUDIT_batch09.md` covered suppressions.py (clean; its one VERIFIED
finding that run was in codewatch.py, out of this batch's scope). `handoff/sweep61/AUDIT_batch06.md`
covered navtree.py (clean). `handoff/sweep61/AUDIT_batch11.md` covered roll.py (clean, notes the
compare-and-swap migration as already fixed). This run re-read all eight modules from scratch
against the current source rather than assuming sweep61's verdict still holds, per the brief's
"do not re-report shapes the code already names and handles" instruction — the check below is for
defects NOT already named in the surrounding docstrings/comments.

## Summary

**No VERIFIED or SUSPECTED defects found in this batch.** These eight modules remain the most
heavily self-documented files in the tree: essentially every non-obvious branch carries a
multi-paragraph comment citing the order number, the incident that motivated it, and the
measurement that proved the fix (e.g. cascade_bridge.py's `dead_forever()`, `permanent_refusal()`
and `_ask_call`'s widen-fallback; sweep_plan.py's compare-and-swap shard writer and
`normalise_module`'s exact-match refusal; runguard.py's `holder_is_live`/`guard_fault` pid-identity
pair; roll.py's `mutate()`/`exclude()` compare-and-swap). Reading closely for cases where a
"deliberate design" comment did not match the code beside it, or where a documented fix was
incomplete, turned up nothing new.

Checked specifically against the priority list:

1. **Checks that cannot fail** — none found beyond what's already flagged. Traced
   `cascade_bridge._ask_call`'s eight `if pinned:` guards past the single non-None exit point
   (already documented "INVARIANT, STATED ONCE", order 8b0338b019ce — not re-filed).
2. **Fail-open guards** — `runguard.claim()`'s corrupt-guard fail-open is deliberate and
   owner-ruled (order 70f66fbd98aa) and escalates at SAFETY rather than staying silent.
   `roll.in_scope()`'s fail-open on an unreadable roll is explicitly argued in its own docstring
   (an unreadable-roll fail-closed would silently exclude the entire library, which is worse).
   Both traced end to end; both match their documentation.
3. **Caps/truncations (Hard Rule 0)** — every listing checked in this batch is explicitly
   uncapped: `cascade_bridge.selftest()`'s provider list, `rosetta --probe`/`--mine`/`--refine`'s
   value dumps, `sweep_plan`'s `--missing`/`unknown_claims`/`check_briefs` output,
   `catalogue_codex.main()`'s four collision reports, `suppressions.problems()`, `navtree.main()`'s
   audit listing, `roll.main()`'s excluded-source listing — all carry a comment citing the order
   that removed a prior cap, and none reintroduces one.
4. **Real logic bugs** (wrong variable, off-by-one, unit mix, races, resource leaks, exception
   paths that corrupt state) — none found. Specifically traced for new races: `cascade_bridge`'s
   `record_unrecognised` compare-and-swap-with-readback, `sweep_plan.record()`'s per-shard write
   plus best-effort aggregate fold, `runguard._land_claim`'s digest-before-read ordering in
   `claim`/`beat`/`release`, `suppressions._mutate`'s re-apply-on-lost-race, and `roll.mutate`'s
   identical shape — all landed through `silence.replace_if_unchanged`/`replace_retry` with the
   digest taken before the read, which is the correct order and matches every sibling in this
   tree already hardened this way.
5. **Anything that could open `prose_enabled`/`step4_enabled` or lift a halt** — none of these
   eight modules reference either flag. `runguard.py` never calls `escalation.clear()` (grepped);
   its only escalation call is `escalate(_ESC.SAFETY, ...)` on a corrupt guard, which fails the
   battery rather than lifting anything.
6. **Regex/escape corruption** — `cascade_bridge.py`, `rosetta.py` and `catalogue_codex.py` all
   carry the `_BAD_CHARS` control-character self-check at import time; all three passed (the
   check itself would raise `SystemExit` on failure, and none did). Manually re-verified the
   trickier regexes by hand: `rosetta._STAND`'s `[:=|!]+` separator class, `rosetta._SCALE_TITLE`
   stems with no trailing `\b` (both already documented fixes, re-confirmed still applied, not
   re-filed), and `cascade_bridge._SIZE_REFUSAL`'s Limit/Requested arithmetic gate.

## Verification method

Read every module top to bottom via the Read tool in large chunks (no grep-sampling). For the
handful of places that looked initially suspicious, traced callers/definitions rather than
assuming intent from a local read:

- `cascade_bridge._ask_call`'s widen-fallback round-robin: confirmed by hand that
  `ranked = ranked[off:] + ranked[:off]` followed immediately by a stable re-sort on the same
  `(bucket not in answering)` key does NOT undo the rotation — Python's `sort()` is stable, so the
  re-sort only re-partitions the already-rotated order into "answering" and "not answering"
  groups while preserving each group's rotated relative order. Matches the comment's claim that
  "the offset spreads consecutive calls across the alive set; the sort still puts proven
  answerers ahead of unproven ones."
- `cascade_bridge._bury`/`_clear` interaction on the unparseable-reply path: `_clear(pinned.bucket)`
  fires as soon as the stream succeeds (before the JSON parse is attempted), so a subsequent
  `_bury()` call on the third consecutive unparseable reply computes its backoff from a
  freshly-reset strike count (n=1, `FIRST_BENCH`), not from whatever strike count preceded the
  successful stream. Confirmed this is consistent with the two counters being deliberately
  separate (`_STRIKES`/`_DEAD` for transport/auth failures vs. `_UNPARSEABLE` for schema
  failures) rather than a double-count bug.
- `sweep_plan.py` main()'s `if a.batches: ... elif a.check_briefs: ... elif a.missing: ... elif
  a.coverage:` — ordinary mutually-exclusive CLI flags, not a data-loss bug (same conclusion as
  sweep61 batch08, re-verified rather than assumed).
- `runguard.guard_fault()`'s single-direction detector (only "stale heartbeat, pid provably
  alive" fires; the mirror "fresh heartbeat, pid gone" case was deliberately removed) — read the
  docstring's own measured justification (pid 26924, gone, heartbeat 0.8 min old, run healthy)
  and confirmed the removed arm would indeed fire on the ordinary case of an ephemeral-interpreter
  holder, which is ~every real holder of this guard.
- `roll.update_rows`'s `seen.add(name)` placement (order 60cb4e0e3595) — confirmed the fix is
  correctly outside the `if ch:` block, and confirmed by grep that the one live caller
  (`catalogue_web.py`) never passes an empty change dict, matching the docstring's own caveat
  that this is a latent-not-live correction.

No code was modified, restarted, or executed. All verification was by reading source and tracing
call graphs; no live model calls, roll mutations, or guard claims were made.

## Questions

None arising from this batch beyond what the modules' own comments already pose as open
questions (e.g. `cascade_bridge.py`'s NEXT_STEPS-routing-decision-B on whether an unrecognised
failure should also cost a bench — already flagged in the source as an owner question, not
re-raised here).
