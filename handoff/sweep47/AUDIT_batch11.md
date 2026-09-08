# SWEEP47 BATCH 11 AUDIT

Scope: 8 modules, 5,642 lines, all read in full, line by line, including every docstring.

  - src/foreman.py (1,810 lines)
  - src/silence.py (1,043 lines)
  - src/codewatch.py (763 lines)
  - src/endpoint.py (577 lines)
  - src/tiers.py (492 lines)
  - src/grounding.py (344 lines)
  - src/deprecated/catalogue_local.py (333 lines)
  - src/tells.py (280 lines)

No sampling. No module or line range was skipped.

## Special attention: silence.py `replace_retry` bare-call sites

Traced every call site of `silence.replace_retry` and `silence.replace_if_unchanged` across
`src/` (grep + read). Confirmed the two documented bare-call (return-value-discarded) sites and
re-checked their reasoning against current code:

  - **read.py `_chunk_put`** (`silence.replace_retry(tmp, p)` with no `if`) — the comment's
    reasoning holds: this writes a pure per-chunk model-answer memo, `_chunk_get` returns `None`
    for "not cached" distinctly from an empty `feats` list, and a failed land just means a
    re-ask next time. No wrong-answer path exists from ignoring the verdict here.
  - **gpu_lane.py `_touch`** (bare `silence.replace_retry(tmp, path)`) — reasoning holds: this is
    a heartbeat refresh at 1/3 of the shortest lease, so a missed beat is absorbed by the next
    one 100s later; a stall costing a lease is visible through `replace-denied:` in the failure
    ledger regardless.

Every other `replace_retry`/`replace_if_unchanged` call site in `src/` either checks the return
value directly (`if not ...:` / `landed = ...; if not landed:`) or is one of these two documented
exceptions. No new silent-discard site of this primitive was found.

`replace_retry`'s fail-closed-and-silent design itself (records via `note()`, returns `False`,
never raises) is intact and correctly documented; `write_json` and `replace_if_unchanged` both
build on it correctly, including cleaning up their own temp files on a refused replace.

## Findings filed this batch

1. **FOREMAN_RETIRE_STALE_OVERWRITE_OF_OVERWATCH** (MAJOR, RUN) — `foreman._retire()` does a raw
   read-modify-write of `data/OVERWATCH.json` that bypasses `overwatch.save()`'s own
   merge-based writer (`_merge_ledgers`/`_reconcile_with_disk`), landing a whole snapshot via
   `silence.write_json` with no digest and no merge. `overwatch.save()`'s own docstring (m40)
   explains at length why a plain overwrite of this specific file is unsafe — "two processes
   hold this ledger routinely" — and was hardened into a merge for exactly that reason.
   `_retire`'s own comment already names the hazard almost verbatim ("a torn or stale write here
   would silently discard its newest finding") but the fix that followed (run #19, pinned by
   `verify_math.py`) only checks that a *denied* replace is recorded — it does nothing for a
   write that *lands* on a stale snapshot, which is the actual case the comment describes. This
   runs every time `foreman.py --patch` retires a finding while `overwatch.py --loop` is
   standing (the ordinary operating condition per CLAUDE.md's STANDING set).

2. **SILENCE_AUDIT_BLIND_TO_CONTEXTLIB_SUPPRESS** (MAJOR, RUN) — `silence.py`'s own audit
   (`_handlers`/`audit`/`instrument`) walks `ast.ExceptHandler` nodes only. A
   `with contextlib.suppress(X): ...` block is semantically identical to `except X: pass` — the
   exact shape this module exists to find — but is structurally invisible to it (verified:
   `ast.walk` over a parsed `contextlib.suppress` block yields zero `ExceptHandler` nodes). 16
   live call sites across 5 modules (`gpu_lane.py` x5, `overnight.py` x5, `autostart.py` x2,
   `render.py` x2, `codewatch.py` x1) contribute nothing to the printed SILENT count and cannot
   be reached by `--instrument`, even though the module's own docstring claims to find "every
   handler in src/ that still returns without recording." Some of these are legitimate
   best-effort cleanup by the project's own conventions; the point is the audit currently cannot
   tell the difference because it never looks.

## Already-open work orders: re-verified against current code, all still live

None of the following were found fixed. Each was checked against the actual current source
(not just the order text) before being left alone:

  - `foreman.py` 850786a2fee4 (checks-pass fires no net before keeping a patch) — confirmed:
    `_checks_pass` still runs only `import`, `verify_math.py`, and `allsweep.py --quick`;
    `--quick` still skips VERIFY/ESTATE; `drill` still does not appear in `allsweep.py`.
  - `foreman.py` d2e44a766769 (`restart_reader` kills outside `_restartable` gate) — confirmed:
    `restart_reader()` still SIGTERMs on a `frag in line` match with no `_restartable()` check,
    unlike `kill_stalled_job()`'s explicit gate.
  - `foreman.py` 7ad10a229440 (pool-reprove pool-break skips restart_reader) — confirmed:
    `REMEDIES["the library's counters are moving"] = [reprove_pool, restart_reader]` and
    `reprove_pool` still returns `did=True` whenever the write lands, regardless of how many
    buckets answer, still triggering the non-`always` break.
  - `foreman.py` 5c962f306e58 (model-patch gate skips the VERIFY tier) — confirmed as above.
  - `foreman.py` c9146abf92df (roll lost-update, remaining writers) — this is about
    `data/SWEEP_ROLL.json`, specifically `foreman.py:189`-area whole-document landing and
    `roll.exclude()`; distinct file from the `OVERWATCH.json` issue found this batch. Confirmed
    still open (foreman.py's roll-landing code was not touched this shift per the order's own
    text, and no evidence in the read that it has been since).
  - `foreman.py`/`codewatch.py` f90795d5c6bd (`codewatch.stamp` ignores `who`) — confirmed:
    `stamp(who="?")` still never stores `who` anywhere; `_START` has no `who` key.
  - `codewatch.py` 13aee150e0dc (runguard downgrades an alarm's rung) — confirmed:
    `_maintenance_run_live()`'s boolean still picks both the rung (JANITOR vs MANAGER) and the
    escalation code in `_report_if_never_settling`, unchanged.
  - `endpoint.py` 570525d35825 (`MODE_HTML` unreachable via `detect()`) — confirmed: `detect()`
    can still only return `MODE_API`/`MODE_RAW`/`MODE_DEAD`; `MODE_HTML` is still reached only
    via the `pages:` host-prefix path in `feats.py`, never via `detect()`.
  - `tiers.py` 789f99f2a65f and 95f80c0ea860 (hyperverse DECLINED print contradicts `chart()`) —
    confirmed: `main()` line ~374 still prints `"hyperverse: DECLINED for all {len(srcs)}
    shelves"` while `chart()` fills `out[s]["hyperverse"]` from `xenoverse_grounding()`, and the
    SAMPLE STACKS block at ~447 still prints a concrete `H{c['hyperverse']}` on the same page.
  - `tiers.py` fe99e57e1993 (unmarked name cuts) — `tiers.py:403` (`_cut(a, 26)`/`_cut(b, 26)`)
    is part of this cluster; confirmed those two calls are still present and still marked with
    an ellipsis via `_cut`, matching the order's own description of that specific site as
    already using the marking helper (the order's complaint is about *other* files' unmarked
    cuts, not this one being unmarked — re-read and consistent with current tiers.py code).
  - `tiers.py` e866d1520c16 (stale cross-module line citations in `deliberate_joins`) —
    confirmed: docstring at `deliberate_joins()` still cites `weave.py:519`, `pipeline.py:2401`,
    `cosmology_graph.py:209`.
  - `grounding.py` 3eff62be6cc3 (inflated confidences still on disk) and 98f18453deaf (synthesis
    text scored outside the origin-entry filter) — both confirmed present in `classify_source()`
    exactly as described; the code-level fix for the *live* classifier is in place
    (`classify_text(top=None)`, full-field denominator) but the synthesis-outside-filter
    question is unchanged and is correctly left as a QUESTION, not re-filed.
  - `tells.py` 692f693c3900 and 382d3a1c387c (rule-of-three pattern narrower than its label, no
    comment explaining the asymmetry) — confirmed: `STRUCTURAL["rule of three"]` at line 97 is
    still `r"\b\w+, \w+,? and \w+ (?:alike|all|together)\b"` with no comment of the kind the
    "not merely X but Y" entry carries three lines above it.

## Modules with no new findings

- **src/deprecated/catalogue_local.py** — deliberately quarantined; the unconditional
  `raise SystemExit(_REFUSAL)` at import time (with the sole `--help` exemption) precedes every
  line of the six documented-but-not-repaired defects, so all of that code is confirmed
  unreachable in any code path except `--help`, which touches nothing. No live risk; nothing to
  file.
- **src/endpoint.py** — extensively hardened (compare-and-swap on both `_save()` and
  `register()`, pid+thread+attempt-qualified temp names, careful HTTP-status-vs-body-shape
  distinctions in `fetch_raw`/`fetch_html`). Only the one already-open `MODE_HTML` finding
  applies; no new issues found after a full read.

## Coverage

All 8 modules read in full, every line, per the brief's list. No module or line range was
skipped or sampled.
