# sweep63 batch05 audit

Scope: read in full, start to finish, no sampling —

- `src/feats.py` — 2804 lines (read in 4 chunks: 1-700, 700-1400, 1400-2100, 2100-2804/end)
- `src/ledger_guard.py` — 1111 lines (read in 2 chunks: 1-600, 600-1111/end)
- `src/estate.py` — 723 lines (read whole)
- `src/autostart.py` — 613 lines (read whole)
- `src/coverage.py` — 456 lines (read whole)
- `src/snapshot.py` — 376 lines (read whole)
- `src/context_budget.py` — 319 lines (read whole)
- `src/scale_theories.py` — 215 lines (read whole)

CLAUDE.md skimmed first for doctrine (Hard Rule -1 escalation/halt, Hard Rule 0 no caps,
fail-closed, "a check that cannot fail looks exactly like a check that passed"). Every file
carries dozens of order-id comments documenting prior fixes; those are not re-reported below.

## Carried forward from sweep61 batch05 — VERIFIED FIXED, re-checked directly

sweep61 batch05 filed one VERIFIED finding: `ledger_guard.check_structure`'s BUGS.md block used
a substring test (`sec not in text`) to decide a section was "present," so a real `## Open`/
`## Resolved` heading could be deleted while the file's own prose mentions of those strings
survived, and the span-building code two lines below would then hit a bare `KeyError` on
`span["## Open"]`.

Re-read `src/ledger_guard.py:209-270` directly against the live file (not trusted from the prior
report). The fix is in place and is stronger than a narrow patch: `check_structure` now builds
`headed = {sec for sec in REQUIRED_SECTIONS.get(name, ()) if re.search(r"(?m)^" + re.escape(sec),
text)}` (an anchored-heading test, not substring) at line 224-225, and the BUGS.md span-building
block is gated on `{"## Open", "## Resolved"} <= headed` (line 231) before it ever touches
`span["## Open"]`/`span["## Resolved"]`. The KeyError path is now unreachable: `marks` cannot be
missing a key that `headed` didn't already prove is present as a real heading. No re-open.

## Findings

None. No VERIFIED and no SUSPECTED findings in any of the eight modules this batch.

This batch's modules are, as sweep61 batch05 also found, unusually heavily self-audited: nearly
every non-trivial function's docstring or inline comment documents a defect a prior sweep found
and fixed, with the measured evidence, the order id, and the failure scenario spelled out. I
specifically checked the classes of defect this project keeps re-finding against every function
in every file — checks that cannot fail, fail-open guards, unrecorded caps/truncations (Hard
Rule 0), off-by-one and unit-mix bugs, races on shared files not funneled through
`silence.replace_retry`/`silence.write_json`/`silence.append_line`, resource leaks, and exception
paths that could corrupt state or silently authorize a prose/step4/halt-lift condition — and did
not find a new instance of any of them. Specific things I traced and ruled out rather than took
on faith:

- `feats.py`'s `_QUANTITY` regex group numbering (mantissa/decimal-exponent/superscript-exponent/
  unit) against how `mine()` reads `m.group(1..4)` — matches; the exponent that was once
  silently dropped (order noted in the code) is correctly captured and folded in.
- `feats.py` `resolve_hosts()`'s override/cache/probe for-else logic (lines ~1105-1192) — traced
  every branch (override hit, cached hit, corpus-derived guess, verified guess, undetermined
  probe, no-candidate-slug) against what gets written to `known` vs `unprobed`; consistent with
  the docstring's claims.
- `feats.py` `_throttle`/`note_throttled`/`backoff_state`'s `tuple(_BACKOFF.items())` snapshot
  pattern — re-verified independently of the sweep61 note; still correct (the edge lock and the
  host-keyed ledger genuinely never collide at the point of mutation vs. iteration).
- `ledger_guard.py`'s `seal()` floor-ratchet (`_read_floor_snapshot`/`_floor_snapshot_path`) and
  its `except Exception: ... os.unlink(ftmp)` guard against `ftmp` being possibly undefined —
  correctly catches `(OSError, NameError)` for the case the exception fired before `ftmp` was
  ever assigned.
- `ledger_guard.py` `verify_chain()`'s bytes-vs-chars unit reconciliation across the legacy/
  current link-format boundary (lines 900-923) — the unit selection logic (`"bytes" if ("chars"
  in old_l and "chars" in cur_l) else "characters"`) is internally consistent and can't silently
  compare mixed units.
- `coverage.py` `state_of()`'s six-way state-precedence loop (CITED > READ > NO PAGE >
  UNREACHABLE > NOT ATTEMPTED across multiple candidate paths) — traced every state-transition
  pair (READ never downgraded by a later NO PAGE, NO PAGE never downgraded by UNREACHABLE, etc.)
  and it matches the documented precedence in every case.
- `snapshot.py` `_rel()`/`_safe_join()`'s path-containment refusals, and `restore()`'s
  missing-file accounting against the manifest — both refuse rather than silently reroot or
  under-restore, as documented.
- `context_budget.py`'s two-ratio arithmetic (`CHARS_PER_TOKEN` for content vs.
  `PROSE_CHARS_PER_TOKEN` for scaffolding) through `content_budget_chars()` and
  `feats_block_budget()`'s `METADATA_INFLATION` division — the direction of every conversion
  (tokens→chars vs. chars→tokens, and which ratio applies to which side) is conservative in the
  direction the module's own header argues for.
- `estate.py`'s TOCTOU-guarded stat/read paths (`inspect()`'s retry-then-distinguish-GONE-from-
  UNREADABLE, `written()`'s vanished-between-exists-and-stat handler) and `autostart.py`'s
  tri-state (`True`/`False`/`None`) `supervisor_alive()` propagation through `_start_decision()`,
  `watch()`, and the two nested-ternary status prints in `main()` — all correctly preserve the
  three-way distinction end to end; I specifically hand-traced the two chained ternaries in
  `autostart.py:main()` (`"running" if _up else ("UNKNOWN..." if _up is None else "not
  running")`) since that shape is an easy place to lose the `None` case, and both are correct.
- `scale_theories.py` — confirmed still intentionally unwired dead-but-authored content per owner
  ruling (order `01695fe3ef26`), consistent with its own header; not re-reported as dead code.

## Questions

None. No design questions arose that weren't already answered by the modules' own doctrine
comments (e.g. why `MAX_LOST_FRACTION` is shared unchanged between `check_since_snapshot` and
`check_since_floor` rather than given its own ruling — the code already states the reasoning and
it holds up).

## Coverage recorded

Ran `sweep_plan.record('run63', [...], batch=5)` for all eight module basenames listed above (see
command in the batch instructions).
