# sweep63 batch14 — audit report

Scope (all under `src/`, read start to finish, in full, no sampling):

| module | lines |
|---|---|
| hostcheck.py | 1735 |
| health.py    | 1319 |
| liveness.py  | 1089 |
| weave.py     |  709 |
| tiers.py     |  555 |
| cleanup.py   |  452 |
| sweep.py     |  374 |
| tells.py     |  303 |

Total 6,536 lines, all read in full, no edits made under `src/`, `data/`, or `state/`.

## Method and prior-sweep cross-check

CLAUDE.md was read first (Hard Rule -1 escalation chain, Hard Rule 0 no-caps, fail-closed
doctrine, "a check that cannot fail looks exactly like a check that passed").

`handoff/sweep61/` was grepped for these eight module names. Four of the eight (hostcheck.py,
health.py, liveness.py, tiers.py) were covered together in `sweep61/AUDIT_batch14.md`; the other
four (weave.py, cleanup.py, sweep.py) in `sweep61/AUDIT_batch11.md` and tells.py in
`sweep61/AUDIT_batch16.md`. All four were read before starting, and their findings were checked
against the current source rather than re-filed:

- `sweep61/AUDIT_batch14.md` finding 1 (`liveness.py`, `_function_line_ranges()` keyed by bare
  function name, SUSPECTED/latent) — **FIXED**. The function now keys every def by a
  class-qualified `Outer.name` label, keeps a bare-name alias only when it is unique, and maps
  the bare name to `None` (excusing nothing) when several defs share it. The fix is dated and
  cited in-line: "QUALIFIED, AND A BARE NAME ONLY WHEN IT IS UNIQUE (sweep61 batch14)" at
  `liveness.py:829`. Confirmed by reading `_function_line_ranges` and its caller `reachability()`
  end to end.
- `sweep61/AUDIT_batch14.md` finding 2 (`hostcheck.py`, `probe()` API branch undercounting hits
  when two probed names redirect to the same page, SUSPECTED/unverified) — **FIXED**. `probe()`
  now walks `normalized` and `redirects` per probed name (bounded iteration against cycles) and
  counts hits per input name rather than per returned `pages` entry, cited in-line: "HITS ARE
  COUNTED PER PROBED NAME, NOT PER RETURNED PAGE (sweep61 batch14)" at `hostcheck.py:442`.

Both prior-sweep items are therefore closed and not re-filed. This batch's own module-internal
commentary was likewise cross-checked line by line (order IDs, "sweep61 batch14", "sweep42",
"run36" etc. citations) before treating anything as a candidate finding — this is one of the most
heavily self-audited stretches of the codebase, and the overwhelming majority of what looks odd
on first read is already a documented, fixed, or deliberately-kept-and-explained historical
defect (dead-but-retained functions under the owner's "mark and keep, delete nothing" ruling,
asymmetric regexes defended by measurement, etc.).

## Findings

**0 VERIFIED. 0 SUSPECTED (new).**

No tautology, no fail-open guard, no new Hard-Rule-0 cap/truncation, no off-by-one/unit-mix/race/
resource-leak, and no regex/escape corruption was found in any of the eight modules beyond what
each module's own in-line history already records as found-and-fixed. Both items surfaced by the
previous sweep against this same module set are now fixed, as detailed above, and no replacement
defect of the same shape was found in the code that replaced them (verified `_function_line_ranges`
against its only caller `reachability()`, and `probe()`'s hop-following against `score()`/`sweep()`
which consume its `hits`/`rate`).

Specifically checked and ruled sound, not re-filed:
- `health.py`: the ledger/samples compare-and-swap (`_flush_ledger`, `_flush_samples`), the
  thread-local re-entrancy guard on `flush()`, `check_api_paths`'s per-registered-domain family
  bucketing plus quarantine exemption, `check_caches`'s quarantine/exclusion/25-file-floor logic,
  and `reopen_stranded`'s re-read-before-write compare-and-swap are all sound and internally
  consistent with their extensive in-line history.
- `hostcheck.py`: `_land_hosts`'s compare-and-swap and re-ask-the-halt-before-writing discipline,
  `null_rate`'s None-vs-zero handling and control-sample floor, `score()`'s lift/aboutness verdict
  ladder (including the `about_n == 0` vs `about is None` distinction), `sweep(--repair)`'s
  lift-based selection, and `purge()`'s gate-then-write ordering all check out.
- `liveness.py`: the receiver-aware DEAD pass (`_credit_attrs`/`_scope_aliases`), the DEAD-CLASS
  and PHANTOM passes (including the widened guard/assert/match-guard/short-circuit coverage), and
  `reachability()`'s subprocess-only coverage measurement (avoiding the `src/coverage.py` shadow)
  are all as documented.
- `weave.py`: `components()`'s complete-linkage agglomeration (including its `threshold <= 0`
  refusal), `surprisal_pair_weights`'s uncapped shared-evidence lists, and the superseded
  idf-weighted `pair_weights`/`null_threshold` functions (kept per owner ruling, not called) are
  all consistent with their docstrings.
- `tiers.py`: the CUTS/MULTIVERSE_THRESHOLD raised invariants, the grounding-derived hyperverse
  vs. the declined link-graph hyperverse (kept as two clearly-separated measurements), and the
  containment (`split_sources`) gate before `TIERS.json` is written are all correct.
- `cleanup.py`: `_ruby_question_mark`/`_ruby_parenthetical`'s non-ASCII guards (idempotent, and
  verified against the three real-English false-positive cases named in-line), and the five
  uncapped report rosters are all as documented.
- `sweep.py`: `nested_run()`'s tested-not-assumed funnel nesting, and the uncapped BIGGEST
  GAPS/REACHED BUT SILENT rosters are as documented.
- `tells.py`: `prompt_in_sync()`'s CRLF-folded comparison and the asymmetric structural-pattern
  regexes (deliberately uneven, defended by measurement) are as documented; confirmed wired via
  `standards.py`/`style_audit.py` imports, not dead code.

## Questions

1. **`liveness.py:984-990`, `reachability()`'s `DECLARED_UNREACHABLE` lookup** — not a finding,
   a documentation gap. If a name in `DECLARED_UNREACHABLE[module]` does not match any def at all
   (a typo, or a function since renamed/removed), the loop takes neither the `ambiguous` branch
   (`fn_name in ranges` is False) nor the `span` branch (`ranges.get(fn_name)` is falsy) — it
   silently contributes nothing to `declared_lines` and prints nothing to flag the stale
   declaration. This fails in the SAFE direction (the ruling simply stops excusing anything, so
   the lines it used to cover fall into `unreached_undeclared` and get surfaced, never hidden),
   so it is not filed as a finding — but it means a stale/typo'd ruling in `DECLARED_UNREACHABLE`
   degrades silently into "ruling no longer applies" rather than raising or printing "declared
   function `_land_clear` not found in escalation.py". Worth an explicit "declared but not found"
   row in the report if the owner wants staleness in this table to be as loud as staleness
   elsewhere in this file's own doctrine.

No other design questions arose in this batch.
