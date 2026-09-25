# sweep61 batch05 audit

Scope: read in full, start to finish, no sampling —

- `src/feats.py` — 2805 lines (read in 4 chunks: 1-911, 912-1611, 1612-2311, 2312-2804/end)
- `src/ledger_guard.py` — 1105 lines
- `src/estate.py` — 723 lines
- `src/autostart.py` — 613 lines
- `src/coverage.py` — 456 lines
- `src/snapshot.py` — 376 lines
- `src/context_budget.py` — 319 lines
- `src/scale_theories.py` — 215 lines

Also specifically re-checked the coordinator's tonight's change to `feats.py`'s `_throttle()`
and `backoff_state()` (order 549e7df722a0, iterating a `tuple()` snapshot of `_BACKOFF`).

## Coordinator's change — VERIFIED, correct

`_throttle()` (feats.py:187-231) takes `_HOST_LOCKS[dom]` and then does
`for h, m in tuple(_BACKOFF.items()): ...` to find the slowest multiplier on the shared edge.
`backoff_state()` (feats.py:287-290) does `{h: round(m,2) for h, m in tuple(_BACKOFF.items())
if m > 1.0}`. Both are read-only snapshots taken specifically because `note_throttled()` can
insert a *new* key into `_BACKOFF` under a *different* edge's lock while `_throttle` is mid-walk
under this edge's lock — a live `.items()` iteration could raise "dictionary changed size during
iteration". `tuple()` copies the view in one C call, matching the comment's own reasoning. No
defect found; verified by reading the full call graph (`note_throttled`, `_HOST_LOCKS` keying by
registrable domain) and confirming the two never share a lock for the same key at the point of
mutation vs. iteration.

## Findings

**1 VERIFIED — unhandled crash / silent-pass pair in `ledger_guard.check_structure` (BUGS.md
section check), src/ledger_guard.py:219-263**

Two linked defects in the same block:

(a) The `REQUIRED_SECTIONS` presence check is a plain substring test:
```python
for sec in REQUIRED_SECTIONS.get(name, ()):
    if sec not in text:
        problems.append("%s has no '%s' section" % (name, sec))
```
`sec not in text` is true if `"## Open"` or `"## Resolved"` appears *anywhere* in the file,
including inside a backtick-quoted mid-sentence mention — which this exact BUGS.md already does
dozens of times (e.g. live file lines 14, 4750, 4752, 5068: `` `## Resolved (paper trail)` ``,
`` `## Open` `` in prose, never at line-start). So if the real `## Open`/`## Resolved` heading
were ever renamed or lost while these prose mentions survived, this check would NOT flag the
missing section — the exact "a check that cannot fail" class this file's own comments describe
fixing for the *sibling* span-building check a few lines below (the `text.find` → anchored-regex
fix, order noted in the comment above the `marks =` line).

(b) The BUGS.md-specific block a few lines down assumes that if the substrings are present, the
anchored-regex heading search will also succeed:
```python
if name == "BUGS.md" and "## Open" in text and "## Resolved" in text:
    marks = sorted((m.start(), s) for s in ("## Open", "## Resolved", "## Watching")
                   for m in [re.search(r"(?m)^" + re.escape(s), text)] if m)
    span = {}
    for n, (at, sec) in enumerate(marks):
        span[sec] = text[at:(marks[n+1][0] if n+1 < len(marks) else len(text))]
    op, res = span["## Open"], span["## Resolved"]   # <-- KeyError if no real heading matched
```
If `"## Open"` (or `"## Resolved"`) exists only as a substring and never as a line-anchored
heading, `marks` has no entry for it, and `span["## Open"]` raises a bare `KeyError`. Neither
`check_structure`, nor its caller `check_all()`, nor `assert_intact()` wraps this in a
try/except, so the exception propagates uncaught out of `publish.push()`'s pre-flight gate
instead of the intended `LedgerViolation` with an actionable message.

VERIFIED by direct execution against a minimal repro (not the live file, which currently has
real headings for both and is unaffected today):
```
$ python -c "... LG.check_structure('BUGS.md', text=fake_text_with_only_prose_mentions)"
CRASHED: KeyError '## Open'
```
This is a latent fragility rather than a live outage — today's `BUGS.md` has real `^## Open`,
`^## Resolved` and `^## Watching` headings (confirmed by grep) — but it sits in the one function
whose entire subject is "a check that cannot fail looks exactly like a check that passed," and a
future edit that renames/loses one of the three real headings while leaving any of the file's
own many prose references intact would turn a reportable structure fault into an unhandled crash
of the ledger gate itself.

## Not filed as findings (already handled / documented in the code)

- feats.py's dozens of "order NNNN" comments describing past fixes (429 handling, host
  registrable-domain keying, `mined_under_*` staleness predicates, Hard Rule 0 cap removals,
  `_UNIT_DROPS` accounting) were read and cross-checked against the code beside them; all match
  what the comments claim.
- ledger_guard.py's `MAX_LOST_FRACTION` ratchet (`seal()`'s floor-snapshot), `_lost_fraction`'s
  multiset diff, and the chain's acknowledged-shrink mechanism were read end to end and are
  internally consistent with their own docstrings.
- estate.py, autostart.py, coverage.py, snapshot.py, context_budget.py, scale_theories.py are
  extremely heavily self-audited (nearly every function's docstring documents a defect already
  found and fixed by a prior sweep/order). No tautologies, no fail-open guards, no new caps, and
  no false docstring claims were found in any of these six files after a full read.
- `scale_theories.py` is intentionally unwired dead-but-authored content per owner ruling
  (order 01695fe3ef26) — not re-reported as dead code since the module's own header already
  records this.

## Coverage recorded

Ran `sweep_plan.record('run61', [...], batch=5)` for all eight module basenames listed above.
