# sweep61 batch12 audit

Scope: every module below was read in full, start to finish, no sampling.

  - src/magnitude.py       1989 lines
  - src/chain.py           1262 lines
  - src/threads.py         1022 lines
  - src/build_terminal.py   668 lines
  - src/handbuilt.py        518 lines
  - src/pantheon.py         432 lines
  - src/style_audit.py      342 lines
  - src/halo.py             219 lines
  - src/chord_field.py      210 lines

Read-only throughout. Nothing under src/, state/, data/, or config.yaml was edited. No drill,
verify_math, mutate, publish, escalation, workorders, allsweep, chain, local_agent, or anything
touching Ollama/GPU/network was run; the only executions were the coverage-recording call and a
grep sweep for uncommented `[:n]`-style truncations.

## Summary

All nine modules in this batch are unusually heavily pre-audited: essentially every guard,
truncation, and tautology risk already carries an inline comment citing a prior order/sweep that
found and fixed it (e.g. threads.py's four documented "quiet one" refusals, chain.py's ~25 named
orders on citation/mutual-pair/harvest-index correctness, magnitude.py's five numbered guards each
with its own failure history, pantheon.py/halo.py/handbuilt.py's per-axis provenance repairs). I
read every line looking for defects NOT already named by the code's own comments, per the brief's
instruction not to re-report what the code already records as known and handled.

**Findings by kind:**
- Tautologies / checks that cannot fail: 0 new (all pre-existing instances in this batch are
  already documented as fixed, e.g. threads.py `verify()`'s docstring on its own former
  tautologies).
- Fail-open guards: 0 new.
- Caps/truncations hiding data: 0 new (every `[:n]` site in this batch is either (a) already
  commented as a deliberate, reversible console-preview with the full data persisted elsewhere
  and the total count shown — chain.py's `unmatched.most_common(8)`/`inside[:14]`, style_audit's
  `_cut()`-wrapped rankings — or (b) not a listing at all — threads.py's `parts[:2]` decomposing
  an address into Collection.Set, style_audit's `[:8]`/`[:1]` word-shape sampling, a sha1 digest
  slice in chain.py, build_terminal.py's JS label trims which keep the untrimmed string in the
  tooltip/panel).
- Real bugs (wrong branch, off-by-one, crash, race, non-atomic write): 0 new. All writers in this
  batch (halo.py, pantheon.py, handbuilt.py, build_terminal.py, chain.py, threads.py) already
  route through `silence.write_json`/`replace_retry`/CAS helpers and check the landed verdict
  before claiming success.
- False comments/docstrings: 0 new.
- Dead code: 0 found (report only, no action taken).

**One QUESTION, not a finding:** threads.py `build()` computes `known = {source spine codes} |
annex_codes() | law_codes()` and then derives both `cats_at_code` and `siblings` (the T2 cohort
machinery) from that widened `known` set. I traced whether mixing Annex (`VIII.n`) and Law
(`X.n`) addresses into the cohort-family grouping could manufacture a false T2 sibling edge for a
source that happens to be shelved at a colliding code. It cannot: `cats_at_code` is populated only
from `code_of.items()` (real per-source codes), so `cats_at_code["VIII.9"]` or `cats_at_code["X.1"]`
stays empty unless an actual source's own spine code equals one of those (not the case for any
source shelved under Collections I-VIII proper). So the widening is inert today, verified by
reading `build()`'s full loop rather than assumed. Flagging only because the comment beside it
("widening known can only ever let more addresses resolve... T1 and T2 are untouched by this")
undersells that it also feeds `siblings`, not just T1/T2's own resolution check — worth a second
pair of eyes if Collection X or the Annex ever gets a source shelved under it, but not something
to act on now.

No other candidate findings survived verification. Given the density of prior audit work already
embedded in these nine files, I'd read this batch as substantively clean rather than under-audited.
