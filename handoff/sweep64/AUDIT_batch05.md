# sweep64 batch05 audit

Scope, read in full, start to finish, no sampling, no grep-only skimming:

- `src/feats.py` — 2804 lines (read in 5 chunks: 1-700, 700-1400, 1400-2100, 2100-2804/end, plus
  a targeted re-read of 1602-1690 to pin exact line numbers for the finding below)
- `src/ledger_guard.py` — 1111 lines (read in 2 chunks: 1-600, 600-1111/end)
- `src/estate.py` — 723 lines (read whole)
- `src/autostart.py` — 613 lines (read whole)
- `src/citecheck.py` — 458 lines (read whole)
- `src/snapshot.py` — 376 lines (read whole)
- `src/context_budget.py` — 319 lines (read whole)
- `src/scale_theories.py` — 215 lines (read whole)

Total 6,619 lines across 8 modules. Read-only: nothing under `src/`, `data/`, `state/` or
elsewhere was edited; nothing was run except a standalone reproduction of `_unwrap_templates`'s
exact source (copied verbatim into a scratch file outside the repo, no imports of project modules,
no network, no writes to the repo) to verify the finding below by execution rather than by hand
tracing alone, and the final `sweep_plan.record` call.

## Prior-audit cross-check

`handoff/sweep63/AUDIT_batch05.md` covers seven of these eight modules (it audited `coverage.py`
instead of `citecheck.py`) and reported zero findings, describing this batch's modules as the most
heavily self-audited part of the codebase. `handoff/sweep63/AUDIT_batch13.md` covers `citecheck.py`
and filed one SUSPECTED cosmetic finding (`report()`'s `[:160]` console truncation with no "+N"
marker). Re-checked directly: `src/citecheck.py:397-400` now reads

    txt = f["text"]
    out.append("           %s%s" % (txt[:160], " ... (+%d chars; --json has it whole)"
                                     % (len(txt) - 160) if len(txt) > 160 else ""))

with an inline comment "A console cut says that it is one (sweep63 batch13); `--json` carries it
whole." The fix is in place and correct (verified the operator precedence: the `%` substitution
binds inside the ternary's true-branch, so it is never evaluated when `len(txt) <= 160`). Not
re-filed.

`src/feats.py`'s `_unwrap_templates` was explicitly reviewed and cleared with no findings by three
earlier sweeps (`handoff/sweep43/AUDIT_batch07.md`, `handoff/sweep48/AUDIT_batch05.md`,
`handoff/sweep58/AUDIT_batch05.md`), all describing its "brace/param-brace handling" as "traced
correctly" / "consistent with documentation." Those sweeps' own commentary (and the function's own
extensive comments at feats.py:1628-1642) show they checked the STANDALONE case — a bare
`{{{name|default}}}` appearing directly in text, which was a real, fixed bug of its own. None of
them appears to have tested a triple-brace PARAMETER nested as an ARGUMENT of an outer
double-brace TEMPLATE CALL, which is a structurally different code path (it runs through the
non-recursive top-level pipe-splitter at lines 1668-1680 before the recursive call is even made).
That is where the finding below lives.

## Findings

### 1. VERIFIED — `src/feats.py:1656-1690` (`_unwrap_templates`), a `{{{param|default}}}` nested
inside a `{{template|...}}` call corrupts the extracted text: drops trailing characters and leaks
a stray `}` into the mined prose

**The mechanism.** `_unwrap_templates` has two brace-walking scanners that are meant to agree on
where brace pairs begin and end:

- The outer "`{{`" scanner (feats.py:1657-1666) advances `j` by exactly 2 on every match, so it
  cannot double-count an overlapping run of braces. It counts ONLY `{{`/`}}`, never `{{{`/`}}}`.
- The inner top-level-pipe splitter (feats.py:1668-1680) walks `inner` ONE CHARACTER AT A TIME
  with `enumerate(inner)` and tests `inner.startswith("{{", ch_i)` / `startswith("}}", ch_i)` at
  every position without skipping ahead on a match. Over a run of three braces (`{{{`), this tests
  positions `ch_i` and `ch_i+1` both as `"{{"`, so a single triple-brace open is counted as TWO
  nested-level increments instead of one — and the same doubling happens on `}}}` closes.

When a `{{{1|default}}}` parameter reference sits as the trailing argument of an outer
`{{Template|...}}` call, these two disagreements compound: the outer scanner's own 2-char-stride
walk (feats.py:1657-1666) matches the triple-open's first two braces as one `{{` (nesting +1) and
the triple-close's first two braces as one `}}` (nesting -1), so it treats the parameter's OWN
closing pair as satisfying part of what should have been the outer template's close — and hands
back an `inner` string that is missing the parameter's third, final closing brace. That truncated
`{{{1|default}}` fragment (two closes, not three) is then handed to the recursive
`_unwrap_templates` call. On the recursive call, `c.startswith("{{{", i)` matches at the top of
the function (line 1628) and its own triple-brace scanner (line 1643-1652) never finds a
terminating `}}}` — because the fragment only has two — so the `while j < n and level` loop
(line 1644) runs off the end of the string with `level` still 1, and `c[i+3:j-3]` at line 1653
then slices with `j` pinned at `n`, silently dropping the last few characters of the default text.

**Demonstrated by execution.** The exact function body (feats.py:1602-1690, copied verbatim into
an isolated scratch script with no other project dependencies) was run against:

    input:  '{{Infobox|power={{{1|Unknown}}}}}'
    output: '  Unknow  }'

The word "Unknown" loses its final "n" and a bare, unmatched `}` is injected into the output text.
A second case confirms the shape generalizes:

    input:  '{{Outer|{{{1|foo}}}}}'
    output: '  fo  }'

("foo" loses its final "o"; same stray `}` leaks through.) A control case with a sibling parameter
AFTER the nested triple-brace does not trigger it:

    input:  '{{Infobox|power={{{1|Unknown}}}|other=fine}}'
    output: '  Unknown  fine '

— confirming the defect is specifically in how the trailing edge of a nested `{{{...}}}` interacts
with its enclosing template's own closing `}}` when the two closes are adjacent.

**Why this matters for what this module promises.** `strip_wikitext`/`_unwrap_templates` output is
literally what `mine()` gate-checks and what the verbatim-quotation check (referenced in this same
function's own comment at feats.py:1637-1640, "`_norm_q(s) not in _norm_q(ch)`") compares a
model's citation against. The comment at those lines already states the general risk in this exact
class of bug: "The stray brace is not cosmetic... makes a genuine quotation fail the verbatim check
and be counted as a FABRICATION." This is that same failure shape, in a case the prior three
sweeps' review of this function did not include.

**Scope / exposure, stated honestly.** `{{{param|default}}}` syntax is ordinarily written and
consumed inside a TEMPLATE's own definition, not typically typed literally into an article's raw
wikitext (which is what `prop=revisions` returns). Whether or how often this triggers over the
live 275,000+-record `data/feats/` cache is not measured here — I did not grep the cache for the
byte shape that would trigger it, and doing so would require deciding what search would reliably
find it. Reported as VERIFIED for the code defect itself (traced against the source and confirmed
by direct execution, not merely suspected), with the real-world trigger frequency named as an open
question rather than assumed either way.

**Suggested direction**, not prescribed: the inner pipe-splitter at feats.py:1668-1680 should
advance its scan by 2 (or 3, when it recognizes a triple-brace opener) the same way the outer
scanner already does at feats.py:1657-1666, rather than testing every single character position
independently — that is the actual disagreement between the two scanners that lets this corrupt.

## Traced and ruled out (no new finding)

- `feats.py`'s `_throttle`/`note_throttled`/`note_ok`/`backoff_state` per-domain locking and the
  `tuple(_BACKOFF.items())` snapshot pattern — re-traced against the current source; the edge lock
  and the host-keyed ledger still do not collide at the point of mutation vs. iteration.
- `feats.py` `resolve_hosts()`'s override/cache/probe for/else logic (~1089-1244) — every branch
  (override hit, cached hit, corpus-derived guess, verified guess, undetermined probe, no-candidate
  slug) traced against what lands in `known` vs. `unprobed`; consistent with the docstring.
- `feats.py` `_api_list_all`'s continuation-following and `_CAP_BOUND` accounting (1256-1310) —
  the one-stop-condition (repeated continuation token) and the "ran out of answer" partial-walk
  path both count rather than silently truncate.
- `feats.py` `mine()`'s exponent capture (group 2/3 of `_QUANTITY`) against how the three exponent
  shapes are folded into one `exponent` field (1848-1887) — matches the group numbering the
  function's own comment claims.
- `feats.py roll()`'s counter bookkeeping (`done`, `deferred`, `_UNCACHED`, `_STALE_GATE`,
  `_CAP_BOUND`, `_RATE_LIMITED`) and the deferred-tail re-run at the end of `roll()` — all traced;
  nothing is counted into a total twice or dropped from one silently.
- `ledger_guard.py`'s `check_structure`'s heading-vs-substring section detection (224-231, the
  sweep61/sweep63-verified fix) — re-checked directly against the live file; still anchored on
  `^` and still gates the `## Open`/`## Resolved` span-slicing on both headings actually being
  found, so the `KeyError` this was originally filed for is still unreachable.
- `ledger_guard.py`'s `seal()` floor-ratchet (`_read_floor_snapshot`/`_floor_snapshot_path`) and
  the `except Exception: ... os.unlink(ftmp)` guard catching `(OSError, NameError)` for `ftmp`
  possibly being unassigned — correct.
- `ledger_guard.py verify_chain()`'s bytes-vs-chars unit reconciliation across the legacy/current
  link-format boundary (900-923) — internally consistent, cannot silently compare mixed units.
- `estate.py inspect()`'s TOCTOU-guarded stat/read paths (retry-then-distinguish-GONE-from-
  UNREADABLE) and `written()`'s own independent vanished-between-exists-and-stat handler — both
  refuse rather than silently authorize, and both correctly distinguish a benign race from a real
  fault.
- `autostart.py`'s tri-state (`True`/`False`/`None`) `supervisor_alive()` propagation through
  `_start_decision()`, `watch()`, and the two chained ternaries in `main()`
  (`"running" if _up else ("UNKNOWN..." if _up is None else "not running")`) — hand-traced again;
  both preserve the three-way distinction end to end.
- `citecheck.py`'s `_classify`/`_mention_kind`/`_in_tree_lead` resolver, shared unmodified between
  `stale_citations()` (reads `src/` off disk) and `citations_in_text()` (checks arbitrary text) —
  confirmed it is genuinely one resolver, not two copies that could drift.
- `snapshot.py`'s `_rel()`/`_safe_join()` path-containment refusals and `restore()`'s
  missing-file accounting against the manifest — both refuse rather than under-restore silently.
- `context_budget.py`'s two-ratio arithmetic (`CHARS_PER_TOKEN` vs. `PROSE_CHARS_PER_TOKEN`)
  through `content_budget_chars()` and `feats_block_budget()`'s `METADATA_INFLATION` divide — the
  direction of every conversion is conservative in the direction the module argues for.
- `scale_theories.py` — confirmed still intentionally unwired dead-but-authored content per owner
  ruling `01695fe3ef26`; not re-reported as dead code.

## Questions

None. No design or policy question arose in this batch that the modules' own doctrine comments do
not already answer (e.g. why `MAX_LOST_FRACTION` is shared unchanged between
`check_since_snapshot` and `check_since_floor` — already argued for in the code itself). Nothing
in this batch touches `prose_enabled`/`step4_enabled`; not opened, per instructions.

## Summary of findings by kind

- Checks that cannot fail: 0
- Fail-open guards: 0
- Caps/truncations hiding roster/entry-list data (Hard Rule 0): 0
- Real logic bugs (wrong variable, off-by-one, race, inverted condition, regex/escape corruption):
  1 VERIFIED (`feats.py:1656-1690`, above)
- Comments/docstrings asserting behavior the code does not have: 0 new (the one already-fixed
  citecheck.py truncation from sweep63 is confirmed fixed, not re-filed)
- Suppressed exceptions turning a failure into a plausible negative: 0 new

## Coverage recorded

Ran `sweep_plan.record('run64', ['feats.py', 'ledger_guard.py', 'estate.py', 'autostart.py',
'citecheck.py', 'snapshot.py', 'context_budget.py', 'scale_theories.py'], batch=5)` from the kit
directory after this file was written.
