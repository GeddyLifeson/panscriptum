# sweep63 batch 01 — AUDIT

Scope: `src/drill.py` (23,728 lines). Read sequentially, start to finish, in ~1,000-line chunks,
line 1 through line 23728 (the `if __name__ == "__main__":` guard). No sampling. This is the
project's adversarial safety-net battery — the harness that attacks every other guard in the
codebase and reports HELD/BREACHED per net.

Previous audit of this module: `handoff/sweep61/AUDIT_batch01.md` (0 VERIFIED, 0 SUSPECTED, full
sequential read of the file as it stood at 23,532 lines). This sweep re-read the file in full
rather than trusting that verdict, per the brief's instructions, since ~200 lines have been added
since (new nets in `drill_hostcheck`, additional CLAUDE.md-cited orders, etc.).

## Method

Read every line via the Read tool in sequential offset/limit chunks (no `head`/`tail`/grep
sampling), cross-checked the `main()` area tuple against every `def drill_*` function actually
defined in the file (all 44 area functions are present in the tuple — none orphaned, none listed
twice), and specifically re-examined the code paths the brief's priority list calls out: tautological
checks, fail-open branches, caps/truncations, real logic bugs (races, off-by-one, wrong variable),
anything that could touch `prose_enabled`/`step4_enabled`, and regex/escape corruption.

## Findings

**0 VERIFIED, 0 SUSPECTED.**

No tautologies, fail-open guards, hidden truncations, real logic bugs, false comments, dead code,
or regex/escape corruption were found on this full, sequential, unsampled read. Every defect class
the brief asks for is one this file already hunts for elsewhere in `src/`, and — as the sweep61
audit already documented at length — the file's own construction history shows each of these
failure shapes being found and repaired inside `drill.py` itself, with the incident, the order id,
and the fixture that beat the earlier form recorded beside the fix:

1. **Checks that cannot fail.** Every `all()`/`any()` over a population I checked either asserts
   the population is non-empty first (e.g. `_policy_corpus_clean`'s `return read > 0 and bad == 0
   and unreadable == 0`, `no_open_order_sits_on_a_legacy_cap_boundary`'s hit-list raise instead of a
   bare bool) or is a closure whose control fixture is driven in the same net (the `[control]`
   nets throughout `drill_defect_classes`, `drill_citations`, `drill_inspector`, each proving the
   detector can still find the shape it exists to find, not only that it currently finds nothing).
   `net()` itself treats a raised exception as a breach, so a probe that silently swallowed its own
   subject would show up as HELD rather than as evidence.

2. **Fail-open guards.** Every `except Exception` swallow I traced around a read either fails
   closed with a stated reason (`_halt_fails_closed`, `an_unreadable_stop_ledger_stops_everything`,
   `_an_unreadable_config_closes_both_gates`, the halt-lock's `HALT LOCK NOT TAKEN` banner) or is
   one of the file's explicitly-labelled fail-open exceptions with the asymmetry argued for by name
   (`paid_access_stays_switched_off`'s `FileNotFoundError` arm vs. its generic-exception arm;
   `_a_broken_maintenance_guard_fails_open`'s docstring arguing the opposite-of-house-default
   direction is correct for that one guard). I did not find an unlabelled or accidental fail-open
   path.

3. **Caps/truncations (Hard Rule 0).** `drill_no_caps` and `drill_scout` exist specifically to
   attack `[:N]` truncations elsewhere in `src/` (`manifest_builder.py`'s nomination, `scout.py`'s
   hostless work-list rotation, `coverage.py`'s worst/best-covered tables) and assert
   ranking-without-truncation, with explicit "and it is not disclosed" framing for the one case
   where a floor is legitimate (`coverage_report_discloses_the_hosted_floor`). Inside `drill.py`
   itself every slice I found (`tail[-2000:]` in `prove_net`/`ledger_dry_run`, the stderr capture
   in `_reread_the_breaches`'s caller) is a *display* truncation explicitly labelled with a `+N
   chars cut` marker, matching the project's own convention for the difference between a display
   cut and a data-loss cut.

4. **Real bugs (races, off-by-one, wrong variable, resource leaks, corrupting exception paths).**
   The file's own concurrency-hazard probes (`_esc_sandbox`, `_ledger_redirected`,
   `_src_mtime_preserved`, THE LIVE-STATE WITNESS) are internally consistent: every redirected path
   is asserted to resolve under its sandbox root before a probe runs, and `_esc_sandbox.restore()`
   raises if the audit hook caught a live-path write during the sandbox's lifetime — verified
   against its own control (a deliberate write to a live-shaped path that must be caught) inside
   `_no_sandboxed_probe_reaches_live_state`. I checked the `_gate_precedes_spawn`/`_arm_leaves`
   family's reliance on `s.lineno > g.lineno` as a stand-in for "reachable and after the guard"
   (used by `the_keeper_asks_before_restarting`, `both_launchers_ask_before_spawning`,
   `_the_loop_asks_the_gate`, `the_copy_loop_actually_asks_the_gate`) — this is a real
   approximation (line order within one function body, not a full control-flow reachability
   proof), but every site scopes it to the single function it drives, and the docstrings record
   the two prior defeats (`07c7379597ba`, `5ed81099fc49`) that forced the current shape; I found no
   fixture or scope where this approximation currently produces a wrong verdict.

5. **`prose_enabled`/`step4_enabled`.** Both flags are pinned to their exact owner-ruled state
   (`the live prose gate stands where the owner ruled it -- OPEN since 2026-09-16`, `the gate
   stands where the owner ruled it -- OPEN since 2026-08-31`) by nets that read the real
   `gate_open()`/`step4_gate_open()` against the real `config.yaml`, with siblings pinning the
   disk-read path (`_an_unreadable_config_closes_both_gates`, `_the_gates_read_what_is_actually_in_
   config`) and the per-source evidence floor underneath the open gate
   (`_the_open_gate_still_holds_back_an_uncited_source`). No net writes to the live `config.yaml`
   or `STEP4_PLAN.md` — both `_gates_agree` and `_step4_needs_its_plan` were rewritten away from
   doing exactly that, with the incident (run #31, a live `config.yaml` truncate-then-fill) on
   record. I found nothing in this file that could lift either gate.

6. **Regex/escape corruption.** The `_BAD_CHARS` eaten-escape guard at the top of the file protects
   `drill.py` itself, and `weave_index_refuses_an_eaten_escape` /
   `_every_re_importer_carries_the_eaten_escape_guard` (with its own `[control]` sibling) prove the
   house guard actually fires and that the roster of modules requiring it is derived from the
   parse tree rather than typed by hand.

## Cross-check: area-tuple coverage

Every `def drill_*` area function defined in the file (44 total, listed by grep) appears exactly
once in `main()`'s production area tuple, in an order that places `drill_ledger_witness` last (the
witness can only see probes that ran before it — an area appended after it would be invisible to
its own coverage checks, which the file's own comment states as the reason for the ordering). No
orphaned area, no area listed twice.

## Questions

- `_reread_the_breaches` (order 71ae3fa7e55e) retries a breached net exactly once on a tree it has
  waited to "settle" (`codewatch.quiet_seconds() >= STABLE_SECONDS`), and drops the halt for any
  net that reads `True` on that second try. This is a deliberate, well-documented owner ruling
  aimed at a specific incident class (a drill reading a file mid-edit by a concurrent agent). It is
  not a defect — the fail-closed direction is asserted in three ways (unattackable net, raising
  net, and a net that breaches again all still halt) — but it is worth the owner's attention that
  the mechanism cannot distinguish "this net was reading a half-written file" from "this net is
  flaky for an unrelated reason (e.g. a genuine race in the code under test)". Both currently get
  the same one retry and the same benefit of the doubt. Not filing this as a finding because it is
  an explicit, reasoned design choice with its own coverage, not an oversight.
- `_live_watch()`'s live-path blocklist (used by THE LIVE-STATE WITNESS's audit hook) is a
  hand-maintained list of paths "a probe here has been found writing" rather than a derived
  roster. The file has its own mitigation for this (`_every_sandboxed_probe_is_driven_by_the_
  witness` re-runs every sandboxed probe with the witness armed and fails if any of them opens no
  sandbox), which meaningfully narrows the blind spot, but a brand-new probe that writes to a live
  path *not yet* on this list, via a code path the AST scanner's narrow definition of "opens the
  sandbox" doesn't recognize, would still not be caught by the blocklist itself. This is the same
  inherent limitation a blocklist always has; flagging it for awareness rather than as a defect,
  since I found no concrete instance of it being exploitable today.
