# AUDIT — batch 13, sweep run44

Modules read in full, top to bottom: `src/read.py` (1,457 lines), `src/overwatch.py` (980
lines), `src/scout.py` (749 lines), `src/manifest_builder.py` (599 lines), `src/backfill.py`
(444 lines), `src/snapshot.py` (377 lines), `src/resonance.py` (299 lines), `src/halo.py` (220
lines), `src/lognames.py` (53 lines).

**Context for the reader of this file:** every one of these nine modules already carries an
unusually high density of self-documented, previously-fixed defects (each cited by an order id
in its own comments). This batch's job was to verify those claims are accurate and to find
anything real that is *not* already on file. The following are already known and filed, and are
**not** re-filed below (confirmed accurate on inspection, and no wider than described unless
noted):

- `read.py` — the two different "is this the entity's own page" tests (`_norm_q`-normalised at
  read.py:801 vs. plain `.strip().lower()` at read.py:1154) — order fc08e056e1ab. Confirmed:
  exactly two such tests exist in the file, no third.
- `read.py:run()`'s closing summary line (`"done in %.2fh ..."`, near the end of `run()`)
  omitting chunks-read/unanswered while the periodic progress line during the run reports them —
  order 05294ca33e1f. Confirmed as described.
- Two load-bearing comments in `read.py` contradicting the code beneath them — order
  a693102e217a.
- `overwatch.structure()` folding distinct failure causes (the import/reconcile try block vs.
  the estate try block) into `out["error"]`/`out["estate_error"]` — order e8c81999530d.
- `overwatch.verify_open()`'s three unmarked cuts — order 92a9017a5d14. Confirmed: `claim[:400]`
  and `actual[:400]` (overwatch.py:606-607) plus `why[:300]` (overwatch.py:620) are the three.
- `overwatch.py:303` `_STATE_RANK` — order 464cc4e12fbc.
- `manifest_builder.py:570-577` unassigned_sources write, `:357` `str(e)[:110]`, `:168`
  `FEATS_BLOCK_CHARS` — orders 00ef174b7495 / bd3f737f4241 / db36d589713e.
- `backfill.lead()` truncation (`chars=420` default) — order 9586cdf72b82.

Below are findings from this pass that are **not** on that list.

---

## 1. `backfill.py` — `--audit`'s source-name column is truncated with no marker, right next to the fix that removed the sibling cap

**File:** `src/backfill.py`
**Line:** 364 (inside `main()`, the `if a.audit:` branch)

```python
360    print(f"{len(rows):,} source(s) with a non-Wikipedia host, thinnest Persons share "
361          f"first -- all of them:")
362    print(f"{'share':>7}{'persons':>9}{'entries':>9}   source")
363    for x in rows:
364        print(f"{x['share']:>7.1%}{x['persons']:>9,}{x['entries']:>9,}   {x['source'][:52]}")
```

**What is wrong:** the comment sitting directly above this block (lines 351-359) documents that
`rows[:26]` was removed as an uncapped-list fix under order 03c0fe609e89, explicitly citing Hard
Rule 0 and the sibling fix in `pipeline.phase_write`'s `refused[:5]`. That fix removed the cap on
*which rows* get printed. It left behind an untouched `[:52]` on the *source name field of every
row that does get printed* — a silent truncation with no ellipsis, no "(truncated)" marker, and
no file that carries the full name elsewhere: `--audit` only ever prints to the console, it
writes nothing to disk. A source name longer than 52 characters is exactly the shape this
project has hit before — e.g. "Who Framed Roger Rabbit (incl. all content from its associated
crossover-toon IPs)" (cited elsewhere in this same codebase, in `manifest_builder.py`'s
`load_record` docstring, as a real catalogued source name) — would print as "Who Framed Roger
Rabbit (incl. all content from its" with the rest silently gone and no way for the reader to
know it was cut.

This is the identical *shape* of defect the comment two lines up says was just fixed one level
up (a truncation on a diagnostic-only report, no cap marker, Hard Rule 0's territory), on the
same line, in the same function — it was simply not caught by that pass because the fix's
attention was on the list length, not the field width.

**Confidence:** high. Verified against the current source; the `[:52]` is unconditional and
unmarked, and no other code path in `backfill.py` prints or persists the un-truncated name from
this branch.

---

## 2. `read.py` — `--limit` on `read.py --run` truncates the read queue with no partial-run marker, and the queue is ranked deterministically, so a bounded run never reaches the tail

**Files/lines:** `src/read.py:1238-1242` (`run()`), `src/read.py:1410-1411` (`main()`'s argparse)

```python
1238  def run(limit=None, workers=2, cap_chunks=None, all_entries=True):
1239      c = config()
1240      todo = queue(all_entries=all_entries)
1241      if limit:
1242          todo = todo[:limit]
```

```python
1409  ap = argparse.ArgumentParser()
1410  ap.add_argument("--run", action="store_true")
1411  ap.add_argument("--limit", type=int)
```

**What is wrong:** `queue()` (read.py:1165-1235) returns every entity with cached evidence,
ranked by `priority()` — a function that sorts on stable, already-captured stats (`chars`,
`own`, `axes`, `quantities`) rather than on anything that changes as a result of *reading* an
entity. Because `read_entity()` (not `queue()`) is what checks the per-entity cache and returns
instantly for anything already fully mined, the design elsewhere in this same file assumes a
full, unbounded pass over `todo` every time — cheap for what is already done, real work only for
what is not. `--limit` breaks that assumption: it slices the *ranked* list down to its first
`limit` entries before any of that cache-cheapness comes into play, so on a second invocation
with the same `--limit`, the exact same top-N entities are selected again (the ranking has not
changed), all of which are now cache-hits, and every entity ranked below N is never attempted —
not once, no matter how many times the command is re-run with that same `--limit`.

This is precisely the "smaller universe wearing the same shape as the real one" pattern Hard
Rule 0 is written against, and this codebase has already fixed the identical shape in a sibling
module: `scout.sweep(limit=...)` (src/scout.py:543-561) explicitly rotates on
last-attempted-first and prints the deferred sources by name so "what a `--limit` run left out"
is never silent. `read.py`'s `--limit` has none of that: no rotation, no deferred-count, no
"PARTIAL RUN" marker of the kind this same codebase prints elsewhere for exactly this situation
— compare `policy.py`'s `"*** PARTIAL RUN (--limit %d) ***"` and `mutate.py`'s `"(capped at
--limit %d; this is NOT the whole set)"`. The `--limit` flag in `read.py` also carries no help
text at all (contrast every other module's `--limit` in this tree, all of which document what it
does), suggesting it was not given the review pass its siblings were.

**Mitigating factor, stated plainly:** the standing production invocation (confirmed by reading
`overnight.py:1438-1440`, which builds the actual command line via
`[..."read.py", "--run", "--workers", str(a.read_workers)]`) never passes `--limit`, so this does
not affect the standing nightly read. The exposure is to a hand-run `read.py --run --limit N`,
which is a plausible thing for an operator to type for a quick manual pass (the flag exists,
after all) and would quietly never converge on the full corpus if repeated.

**Confidence:** medium-high on the mechanism (verified against the actual ranking/caching code);
medium on whether this rises to a "must-fix," since it requires deliberate operator use of a flag
that is not exercised by any standing job. Flagging as a real gap given how consistently this
exact shape is treated as a defect everywhere else in this codebase.

---

## Question, not a defect — `overwatch.py` error-message truncation appears in two places

**Lines:** `src/overwatch.py:410` and `:420`

```python
410    out["error"] = f"{type(e).__name__}: {str(e)[:90]}"
...
420    out["estate_error"] = f"{type(e).__name__}: {str(e)[:90]}"
```

Both `structure()` failure paths (the import/reconcile try, and the estate/artifact-scan try)
truncate the exception's own message to 90 characters with no marker. `write_report()` does
correctly surface whichever of these keys is set (that part is the already-filed fix under order
e8c81999530d), but if that filed order's scope was written against only one of these two
call sites, note that the identical unmarked `[:90]` shape exists at both — raising it here in
case the existing filing only covers the first.

**Confidence:** low on novelty (this may already be inside the scope of e8c81999530d; I could
not confirm the exact text of that filed order against this file alone). Recorded as a
"widen the fix if not already" note rather than a new finding.

---

## Coverage note

No new logic-inversion, tautological-guard, or swallowed-exception defects were found beyond
what is already filed in `read.py`, `overwatch.py`, `scout.py`, or `manifest_builder.py` — these
four in particular are unusually heavily self-audited already (nearly every non-trivial branch
carries a comment citing the order that fixed it, with measured before/after numbers). `backfill.py`,
`snapshot.py`, `resonance.py`, `halo.py` and `lognames.py` were read with the same scrutiny;
`snapshot.py` and `resonance.py` in particular hold up well under a close read (the Gauss-Seidel
convergence fix in `resonance.hodge_decompose` and the containment checks in
`snapshot._rel`/`_safe_join` were independently re-verified line by line against their own
docstrings' claims and found accurate). `halo.py` and `lognames.py` are small, low-risk data/
config modules with no logic defects found.
