# sweep64 batch 02 — AUDIT

Scope: `src/verify_math.py` (13,384 lines, the full file). Read sequentially from line 1 to line
13,384 in ~600-700 line chunks via the Read tool, no sampling, no grep-driven skimming. This is a
full independent read, not a diff against sweep61 or sweep63.

## Method

- Read-only throughout. Nothing under `src/`, `data/`, `state/` or `output/` was edited. The
  single `sweep_plan.record()` call at the end (run from the kit directory, per the brief) is the
  only write this session made, plus this report file.
- Nothing was executed except that one `python -c` invocation. `verify_math.py`, `drill.py`,
  `generate.py`, `pipeline.py` and no other job/script/mutation/publish action was run.
- No subagents were spawned.
- I consulted `handoff/sweep63/AUDIT_batch02.md` and `handoff/sweep61/AUDIT_batch02.md` (both
  cover this exact module) only after finishing my own read, per the brief's instruction not to
  trust a prior audit's self-report without verifying directly. Both reported 0 VERIFIED / 0
  SUSPECTED after a full read. My independent read reaches the same conclusion.

## What this file is

`verify_math.py` is the project's largest and most heavily self-auditing regression battery
(~1,050+ `check()` calls across 36 numbered sections plus a long tail of lettered sub-sections,
§18b through §20ae, appended over many maintenance runs). A very large fraction of its bulk is
not test logic but prose recording: the exact historical defect a row was written against, the
order id, the date, and — for nearly every scan that asserts a negative (`== []`) — a paired
positive-and-negative control proving the detector itself cannot silently regress to matching
nothing (the "order 873330d2e98d" canary pattern, applied dozens of times) or to matching
everything. Sections 20i, 20j, 20p, 20q, 20t, 20u, 20y, 20z, and 20ae are themselves meta-batteries
whose sole purpose is finding exactly the defect shapes this brief's priority list asks about
(tautologies, `f(x)==f(x)` comparisons, `or True` disarms, fail-open escalation guards, narrow/wide
drill stand-ins, discarded `tol=`, prose-backed assertions, section-tag collisions, self-citation
by line number, uncontrolled negative scans) inside this same file.

## What I specifically hunted, per the brief's priority list

1. **Tautological / unfalsifiable checks.** AST-swept by eye for `check(label, X, X)` patterns and
   `check(label, True, True)` literals while reading; found none live. The file documents at least
   five such defects already found and repaired (orders 3f86c571da58, fbdb7fe3bd4c, cc500a6cbf4b,
   96c4be60fb92, ff470a877ac5 — the last a "tested a copy of the algorithm, not the module" case),
   each now replaced with a cross-process/cross-module-load comparison (the `_asfresh` /
   `importlib.spec_from_file_location` device used at §13, §16, §17, §19ai) rather than a
   same-process self-comparison.

2. **Fail-open branches.** The `except ImportError: pass` class around `escalation` imports (§20p)
   is scanned by AST (`_interlock20p`), asserts a `raise` exists inside every handler, and is
   canary-tested against four attack shapes (bare pass, log-and-continue, docstring-only body,
   from-import spelling). `escalation.clear()`'s no-caller assertion (§20t) resolves import
   aliases, from-imports and `getattr` dynamic dispatch, not just the literal spelling. No
   uncaught fail-open shape found.

3. **Caps/truncations (Hard Rule 0).** The `_slices_of` AST scanner (top of file, reused at §1 and
   §22) catches `did[:N]` in all four base-spellings (bare name, attribute, dict key, `.get()`),
   is canary-tested both for true positives and for not matching prose/docstrings, and is asserted
   to return a loud sentinel (never `[]`) on an unparseable file. The one `[:N]` inside this file
   itself (`PR.build_all(limit=400)` at §14) is explicitly labelled as a speed sample for a
   round-trip proof, not a production listing, and does not violate Hard Rule 0 as stated.

4. **Real logic bugs (off-by-one, wrong variable, races, inverted conditions).** None found. Every
   place that looked at first glance like an inversion (the M10 top-rung early-return order, the
   `axis_score` refusal ordering, the `_pool19ai`/`_pool_answer_usable` shape-vs-caller gates, the
   `_TUNx.workers(0)` ceiling-vs-floor boundary, the `_cmd_is_running` quote/`-c`/`-m` tokeniser
   fixes) is accompanied by a positive control proving the fix is real and a negative control
   proving the old bug would have failed it.

5. **Comments/docstrings asserting something the code does not do.** None found uncorrected. Every
   "KNOWN DEFECT" annotation (M18 saturation at §12, "no resolution above M4", the
   `YEARS_PER_UNIT_DISTANCE` calibration note at the end of run35-batch6) is a live, charter-owned,
   already-flagged open question with its own `[control]` row pinning the *current* behaviour so a
   future silent fix is caught rather than endorsed.

6. **Regex/escape corruption.** The file's own `_BAD_CHARS` self-check at line 17 guards the file
   against an eaten regex escape at import time. No corrupted escape or mis-scoped regex found in
   any of the file's own scans.

7. **Silent exception swallowing.** Every bare-ish `except` I found is either wrapped in the file's
   own `_no_ledger_vm()`/`_no_ledger_for_vm()`/`_third_party_vm()` idiom (deliberately suppressing
   only the *echo* of a provoked or third-party failure into `state/failures.json`, never the
   assertion on the return value) or carries a `silence.note("verify_math.py:<site>")` label with
   a stated reason. §20z's own ledger-witness rows (a spy on `health.record`, a witness on
   `health.flush`, and a direct re-read of `state/failures.json`) assert nothing this battery does
   reaches the live ledger, and that witness is itself proven not to be a no-op via `[control]`
   rows.

8. **`prose_enabled` / `step4_enabled`.** Not touched, not recommended for change, per the brief.
   Both are pinned to exact owner-ruled values (`prose_enabled: True` per the 2026-09-16 Phase 4.5
   ruling; `step4_enabled: True` per the 2026-08-31 ruling) with citations to the ruling sessions,
   and the row asserting each is an exact-value pin (not an `isinstance` check), so either flag
   moving in *either* direction turns the row red. This is a design choice the file itself argues
   for at length (a type check cannot see a value change); I record it as intentional, not a
   finding.

## Findings

**0 VERIFIED, 0 SUSPECTED.** I did not find any new logic bug, fail-open branch, tautological
check, Hard-Rule-0 truncation, false comment, regex corruption, or unaccounted-for exception
swallow in this file, beyond what the file already documents as found-and-fixed. This matches both
prior full reads of this exact module (sweep61 batch02, sweep63 batch02).

## Questions (pre-existing, already tracked in-file — not new, not re-reportable as fixes)

These are the same three open items sweep63 batch02 recorded; I reproduce them because they are
genuinely unresolved by design, not because they are new:

- **M18** (§12, `assay.axis_score`): an in-range M10 quantity saturates at 9.9 rather than scaling
  continuously above the floor. Pinned as `[control] top rung: a quantity ABOVE the M10 floor
  still saturates (open M18, untouched)` — a positive control exists specifically so a future fix
  fails loudly here rather than drifting in silently.
- **Instrument resolution above M4** (§12): the Int/Wis/Cha window is fixed at `(30, 30)` for M5+,
  so no faculty score differentiates a dullard from a genius above that band. Marked "KNOWN
  DEFECT, charter-owned; needs owner sign-off" with its own regression row.
- **order 9736a5a73b02** (run35 batch6, propagation.py section): `YEARS_PER_UNIT_DISTANCE`'s
  calibration against the propagation graph's true measured diameter is printed as an INFO line
  every run and explicitly "LEFT FOR OWNER... not an auto-fail."

None of these are defects in `verify_math.py` itself — they are the module correctly refusing to
silently resolve a charter-level judgment call, and correctly re-measuring and printing the
current state of each open question on every run so it cannot go stale.

## Coverage note

Module read in full, and only this module: `src/verify_math.py`, all 13,384 lines, start to
finish. No other module was read this session.
