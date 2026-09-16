# SWEEP 60 — BATCH 13 AUDIT

Modules assigned: `src/assay.py` (1946 lines), `src/silence.py` (1313), `src/scout.py` (833),
`src/custodes.py` (714), `src/tiers.py` (555), `src/citecheck.py` (455), `src/cosmography.py`
(375), `src/entity_match.py` (319). Total 6510 lines, all read in full, uncapped, no sampling.

## Summary

This batch is largely clean. All eight modules carry an unusually high density of prior
self-audit: nearly every "check that cannot fail," tautological guard, and silent-catch shape a
sweep would normally hunt for is already identified, explained, and either fixed or deliberately
retained-with-justification in the module's own comments (citing specific prior orders/rulings).
I read every one of those self-critiques against the live code rather than taking the comment's
word for it, and in every case I checked, the code matched what the comment claimed.

I found two genuine issues, both low severity, both VERIFIED by reading the surrounding source.
I did not find a new instance of the batch's headline failure mode (a check that cannot fail
being mistaken for a check that passed) in live, reachable code.

## Findings

### 1. `silence.py:222-224` — `_block_reaches_sink` does not treat an `AnnAssign` to an
   attribute/subscript as a sink, unlike the parallel `Assign` case a few lines above. LOW
   confidence on real-world impact, VERIFIED by reading the code.

Compare the two branches inside `_block_reaches_sink` (`src/silence.py`):

```python
215  elif isinstance(stmt, ast.Assign):
216      if _expr_uses_names(stmt.value, tainted):
217          for t in stmt.targets:
218              if isinstance(t, (ast.Subscript, ast.Attribute)):
219                  observed = True
220              else:
221                  tainted.update(_assign_target_names(t))
222  elif isinstance(stmt, ast.AnnAssign):
223      if stmt.value is not None and _expr_uses_names(stmt.value, tainted):
224          tainted.update(_assign_target_names(stmt.target))
```

For a plain `Assign`, a target that is a `Subscript` or `Attribute` (`obj.attr = ...`,
`d[k] = ...`) is correctly treated as an observable sink — "a write into an existing structure IS
the observation," per the module's own doctrine at line ~174. The `AnnAssign` branch has no such
check: it only ever calls `tainted.update(...)`, and `_assign_target_names` (line 176-182) yields
names only for `ast.Name`/`Tuple`/`List`/`Starred` targets — for an `Attribute` or `Subscript`
target it yields nothing at all. So a handler shaped like:

```python
except Exception as e:
    self.last_error: str = str(e)
```

is classified SILENT by `_handler_is_observed`, while the un-annotated equivalent
(`self.last_error = str(e)`) is correctly classified OBSERVED via the `Assign` branch. This is
exactly the class of asymmetry the module's own header warns about ("a check that cannot fail
looks exactly like a check that passed") — here inverted into "an observed handler can be
misread as silent" because one of two structurally similar branches is missing a case the other
one has.

I did not find evidence this fires on any handler currently in `src/` (annotated assignment to
an attribute inside an `except:` body is a stylistically rare shape), so I cannot say this is
costing the project a currently-mis-counted handler today — only that the logic is inconsistent
between the two branches and would misclassify that shape if it occurred. Flagged as a real gap,
not as a demonstrated live miscount.

### 2. `citecheck.py:414-433` — `main()` rebinds the loop variable `s` to a per-skip dict after
   already having used `s` for the findings-summary dict. VERIFIED, currently harmless, but a
   latent shadowing hazard.

```python
414  s = summary(found)
415  print("CITECHECK ...")
...
420  print("  %d finding(s): %s" % (
421      s["total"],
422      ...))
...
432  by_why = {}
433  for s in skipped:
434      by_why.setdefault(s.get("why") or OTHER_TREE, []).append(s)
```

`s` is first bound to `summary(found)` (a `{reason: count, "total": N}` dict) and is read via
`s["total"]` at line 421. Immediately after, the `for s in skipped:` loop at line 433 rebinds the
same name `s` to each per-citation skip dict. I traced every use of `s` after that point and
confirmed nothing in `main()` reads the summary dict again after the loop starts, so today this
does not print a wrong number — the read at line 421 happens strictly before the rebind. It is,
however, a latent hazard: any future edit that moves the `%d finding(s)` print below the
`by_why`/`skipped` loop (or that adds a second reference to the summary dict later in the
function) would silently start reading a citation-skip dict where a summary dict was expected,
with no error (both are plain dicts, so `s["total"]` would raise `KeyError` rather than fail
silently — so a future collision would at least be loud, not silent, which limits how bad this
class of mistake could get here). Purely a readability/maintenance finding, not a live bug.

## What I looked for and did not find

- No tautological `_check_constants()` assertions in `assay.py` beyond ones the module's own
  comments already name and defend as deliberate structural backstops against future edits
  (e.g. the `max(vals) > SIGMA_MAX` check at `assay.py:832-835`, which is currently unfalsifiable
  because `SIGMA_MAX` is derived from the same table `vals` is built from — the module's own
  docstring at `_check_constants` already discusses this exact shape, citing two real past edits
  it caught, and asks explicitly that it not be deleted as "unreachable." I verified the claim
  that both cited edits (`SIGMA_UNKNOWN = 0.5`, `SIGMA_MAX = SIGMA_UNIFORM_PRIOR`) would in fact
  trip the guard, by reading the arithmetic; I did not re-run them.)
- No fail-open exception handling in the write paths I read (`silence.write_json`,
  `replace_retry`, `replace_if_unchanged`, `scout._mutate`, `citecheck._lines`) — every one fails
  closed on an unreadable or wrong-shape file and records via `silence.note`/`health.record`
  rather than treating absence-of-signal as permission.
- No dead/unreachable functions beyond the ones already marked `REPORTED DEAD, NOT DELETED` with
  an owner ruling citation (`assay.band_for_quantity`, `assay.null_instrument`,
  `assay.interval_from_hands`, `assay.REFERENCE_JOULES`) — I did not re-verify their call-site
  counts against the live tree (that would require a full-tree AST scan, out of scope for a
  single-batch read), so I am taking the modules' own measured claims on faith for that specific
  count, not re-deriving it myself.
- No caps/truncations on anything that should be uncapped in this batch — `stale_citations`,
  `citations_in_text`, `candidates()`, `deliberate_joins()`, `scout.verify()`'s name list, and
  `sweep()`'s deferred-source list are all explicitly and correctly uncapped (several carry
  comments recording a *previous* cap that was removed, e.g. `citecheck.py`'s own docstring
  citing sweep 44/48/54, `scout.py`'s PROBE_NAMES-vs-verify-list split, `tiers.py`'s
  `deliberate_joins()` whole-list fix). I did not find a new one.
- `citecheck.py`, read as it stands today per the task instructions (edited earlier today): the
  logic for OTHER_TREE / MENTION_QUOTED_TAG / MENTION_SYMBOL_DISCLAIMER classification is
  internally consistent, and `_classify`'s PAST_EOF/BLANK_LINE/BARE_BRACKET resolver is correctly
  1-based and matches its own docstring. One low-confidence observation, not filed as a finding
  above: `_mention_kind`'s `SYMBOL_NOT_LINE` disclaimer exemption is scoped to citations on the
  *same source line* as the disclaimer phrase (the function receives one `line` at a time from
  its caller's per-line loop). If a real disclaimer comment ever wraps across a line break before
  the citation it is exempting, the exemption would not apply and that citation would be checked
  normally. I did not find an actual instance of this in the batch; noting it as a design-scope
  boundary I am unsure is intentional versus an edge case nobody has hit yet.

## Coverage note

All eight files were read top-to-bottom via the `Read` tool (no `head`/`tail`/sampling), including
every docstring and comment. `silence.py` and `assay.py` were each read across two/three
sequential page fetches due to their length; I confirmed line-number continuity between pages
(silence.py 1-1044 then 1045-1314; assay.py 1-848, 849-1398, 1399-1947) so no interior lines were
skipped.
