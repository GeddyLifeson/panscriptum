# Audit batch 15 — run44

Modules read in full, top to bottom: `src/assay.py` (1374 lines), `src/dashboard.py` (1105),
`src/derivation.py` (743), `src/weave.py` (557), `src/canon_backup.py` (453), `src/cleanup.py`
(357), `src/wh40k.py` (302), `src/suppressions.py` (254). 5,145 lines total, no sampling.

No file was edited. All line numbers below were checked against the source as read.

---

## src/assay.py

This module has clearly been through many prior audit rounds — nearly every load-bearing branch
carries a comment naming the order that found and fixed it, and the three items flagged as
already-filed in the work order (the parallel five-grade tables at order 6d132aa1e8aa, the
`ATTESTATION_FLOOR` monotonicity question, and the settled `axis_score:228` `or`/`and` mutant)
are all present exactly as described. I read the whole file looking for anything past those and
found nothing new to report. Specific things I checked and ruled out, for the record:

- `ATTESTATION_FLOOR` (line 1296) is currently monotonic in the same order as
  `SIGMA_BY_ATTESTATION` (Instrumented 0.08 < Witnessed 0.10 < Transcribed 0.20 < Reconstructed
  0.40 < Disputed 0.55), so today's table does not itself misbehave — consistent with the open
  question being "no *guard*", not "currently wrong."
- The `or 1.0` backstop at line 967 and the floor/ceiling clamps in `assay()` (972–1007) are
  correctly gated behind `_check_weights`/`_check_scores`, as their own comments claim.
- `_interval`'s covariance loop (840–857) and the `_rho` fallback-to-independence path (690–763)
  match their docstrings.

No findings filed from this module this round.

---

## src/dashboard.py

Also heavily hardened already (the "UNCUT" comments at lines 340, 613, 1031 all check out against
the current code — none of those caps are actually present any more). One thing worth a QUESTION
rather than a defect:

**`movement()`'s history buffer is capped at 2,000 rows** (`src/dashboard.py:437`):

```python
hist = [h for h in hist if h.get("at", 0) > cutoff][-2000:]
```

This *is* a `[-N:]` slice on a growing list, which is the shape Hard Rule 0 warns about. I traced
every consumer of `state/dashboard_history.json`: `dashboard.movement()` itself only ever looks
back `MOVED_WINDOW_MIN = 30` minutes, and `standards.py:1324` (the other reader) only looks back
45 minutes. At the 5-second poll interval this file runs on, 45 minutes is about 540 samples —
comfortably inside the 2,000-row cap, which covers roughly 2.7 hours. So the cap does not
currently truncate anything either consumer needs; it is closer to the "cutoff, not a cap" the
24-hour `cutoff` filter one line earlier already provides, and reads as a sane memory bound on an
operational log rather than a truncation of library content. Confidence: this is not a
Hard-Rule-0 violation in the sense the rule targets (rosters/entity lists), but it is a numeric
`[-2000:]` with no comment explaining the choice of 2000, so a future consumer that wants a wider
lookback (a "how has this stalled over the last day" report, say) would silently get a shorter
history than the 24-hour cutoff implies. Low severity; flagging as a question rather than a
defect.

No other findings from this module.

---

## src/derivation.py

One confirmed, low-severity finding:

**`scan_constants_with_reason()` counts booleans as numeric literals** (`src/derivation.py:608–610`):

```python
lits = 0 if node.value is None else sum(
    1 for s in ast.walk(node.value)
    if isinstance(s, ast.Constant) and isinstance(s.value, (int, float)))
```

`bool` is a subclass of `int` in Python, so `isinstance(True, (int, float))` is `True`, and
`ast.Constant(value=True)` (or `False`) is counted as a literal. Verified directly:

```
>>> ast.parse("DEBUG = True").body[0]... -> Constant(True), isinstance(..., (int,float)) == True
```

So a module-level flag like `DEBUG = True` inflates the "N literals" count printed by
`main()`'s "where constants live" panel (line 734) by one, exactly as if it were a numeric
constant. The function's own docstring only claims to count "the count of numeric literals",
and this over-counts booleans as numeric. Impact is real but small: this panel is explicitly
"a reviewer's map, not a verdict" (line 725), so nothing downstream keys a decision off the
count. Confidence: high that the miscount exists; low severity given its advisory-only role.

Everything else in this module checked out: `check_graph()`'s new `kind`-validation, cycle
detection via `visit()`'s open/done states, and `main()`'s early-return-on-cycle (so the
non-terminating `depth()`-driven chain walk at 716–722 is provably unreached whenever a cycle
exists) all match their extensive documenting comments.

---

## src/weave.py

The three items named in the work order as already filed — `components()`/`resolve()`
(order e0f9da6e9466), `main()`'s four now-fixed console cuts (order 357e24fa2fa1), and
`null_threshold()` being dead code orphaned from its now-marked-dead sibling `pair_weights()`
(order e637c67ab438) — are all present and match the description; I did not re-file them. I
confirmed independently that `null_threshold()` (line 276) still has zero callers anywhere in
`src/` (only `null_threshold_surprisal` is called, from `pipeline.py:2535` and `weave.py:467`),
so the "undisclosed dead code" shape is real and matches the filed order.

One additional very-low-severity item, not previously named:

**`main()`'s surprisal demo print still truncates a name with no marker** (`src/weave.py:464`):

```python
print(f"   {names[k][:34]:<36} {sur[k]:7.1f} bits")
```

This is a `[:34]` slice with no ellipsis, in the same file whose own `main()` was rewritten three
times over to remove exactly this shape of cut from its other reports (lines 476–481, 492–496,
500–506, all marked "UNCUT... Hard Rule 0"). This one iterates over a fixed set of five
hardcoded demonstration keys (`"gordon", "russia", "knife", "ellenripley",
"weylandyutanicorporation"`), not an ordered roster, so it is not the same class of defect as the
three that were fixed (it cannot silently drop entities past a cutoff — there are always exactly
five). But it is the same textual shape (a bare `[:N]` slice on user-facing text, no marker), in
the one file that has otherwise been swept clean of it, so I'm noting it for completeness rather
than as a headline finding. Confidence: high that the slice exists as shown; low that it matters.

---

## src/canon_backup.py

The two items named as already filed — `snapshot()`'s two-snapshots-same-second collision on
`stamp` (order 61037867dc5d, documented in the code itself at lines 209–212 as a known,
deliberately-deferred gap) and `verify()`'s docstring promise (order 323703189931) — are present
as described. Two further observations, offered as a QUESTION and a possible-widening of the
`verify()` item respectively, since I can't be certain either is new:

**1. `prune(keep=0)` silently keeps everything instead of pruning everything** (`src/canon_backup.py:255`):

```python
for f in snaps[:-keep] if keep > 0 else []:
```

I verified the arithmetic directly: for `keep = 0`, `snaps[:-keep]` is `snaps[:-0]`, and since
`-0 == 0` in Python, that slice is `snaps[:0]` — the empty list — as does the explicit `else []`
guard, so `--keep 0` on the CLI (`main()`'s `--keep` argument, default `KEEP=7`) results in *zero*
snapshots being removed, not all of them. A reasonable operator reading "keep 0" as "keep none,
delete all the history" gets the opposite: everything is kept, silently, with no message
explaining that their `--keep 0` didn't do what it sounds like it should. This is very plausibly
*deliberate* — the guard exists specifically to dodge the `-0` slicing footgun and err toward
never mass-deleting backups by accident, which is the right instinct for a backup tool — but as
written there is no comment recording that choice, unlike literally every other edge case in this
file. Reporting as a QUESTION: either document that `--keep 0` is a no-op by design (and consider
having it say so), or, if `--keep 0`/negative should actually mean "prune everything," this is a
real bug. Confidence: high that the behaviour is as described; unresolved on intent.

**2. `verify()`'s `changed` computation folds "unreadable" into "changed"** (`src/canon_backup.py:345–346`):

```python
live = {rel: digest(p) for rel, p in members(strict=False)}
changed = [r for r, d in live.items() if recorded.get(r) and d != recorded[r]]
```

`digest()` (line 62) returns `None` when a live file exists but could not be *read* (an `OSError`
— e.g. a lock, a permissions problem, a transient share violation). When that happens, `d` is
`None`, which differs from any recorded hex digest, so the file is reported as one of the
"N canonical files changed since the snapshot" (line 350) — indistinguishable from a file whose
*content* actually changed. An operator reading "12 files changed" as "12 files were edited" is
told something subtly wrong when one of those twelve is actually just unreadable right now. This
may be exactly what "verify()'s docstring promise" (order 323703189931) already covers — the
docstring's claim is specifically about what "changed" means — so I'm flagging it as a possible
widening of that filed item rather than a new one, in case it is not. Confidence: high that the
code behaves as quoted; medium that it's actually distinct from the already-filed issue.

---

## src/cleanup.py

**Confirmed, unfixed truncation with no marker, contradicted by the comment sitting directly
above it** (`src/cleanup.py:231, 233, 261`):

```python
if how == "unresolved":
    ceil_unres.append((src, ce[:70]))
elif fixed != ce:
    ceil_fixed.append((src, ce[:52], fixed, how))
    ...
cd = clean_description(d)
if cd != d:
    desc_fixed.append((src, nm, d[:46], cd[:46]))
```

The comment immediately above these lines (302–310) reads:

> "FIVE ROSTERS, ALL OF THEM UNCAPPED (Hard Rule 0, sweep42-batch03). ... The per-name character
> cuts in the same statements go with them."

The roster-level caps genuinely are gone — none of the five `for` loops over `nav`, `ceil_fixed`,
`ceil_unres`, `desc_fixed`, `thin` truncate the *list*, and every row is printed. But the
per-string character cuts the comment appears to describe as fixed alongside them are still
present and unchanged: `ce[:70]`, `ce[:52]`, `d[:46]` and `cd[:46]` all cut the actual ceiling
text / description text to a fixed width **before it is ever stored in the reporting list**, with
no ellipsis and no "cut here" marker, and the values are then printed with `!r` (lines 316–317,
320, 323–324) — so a reader sees what looks like a complete quoted string that has in fact been
silently shortened. This is the exact shape (mid-value cut, no marker) that this same file's own
docstring calls out as defect #3 ("WIKI MARKUP inside descriptions... the description is the
evidence every later volume quotes from") and that its sibling caps in this very comment block
were rewritten to fix. Whether "go with them" was meant to claim these were *also* fixed, or
merely that they're "the same *kind* of cut, listed alongside" the ones that were fixed, the code
itself still truncates the stored text at append time, not just at print time — so even a
consumer other than the console report (there isn't one today, but nothing prevents one) would
only ever see the shortened string. Confidence: high — verified by direct reading of both the
comment and the three truncating lines; the discrepancy is either a stale/overclaiming comment or
an incomplete fix, and either way the truncation itself is real and unmarked.

---

## src/wh40k.py

No findings. This module (the presence-thesis assay for the four Chaos Gods and the Emperor) has
already had its provenance-tagging bug fixed (the `_provenance()`/2-tuple-vs-3-tuple handling at
194–238 matches its docstring exactly), its citation-wrapping fixed (`textwrap.wrap`, not a
`[:56]` cut, at line 272), and its write gated and atomic (288–295). `compute()`'s score dict and
`A.WEIGHTS` iteration line up on all eleven axes for every entry in `ROSTER`. Nothing new found.

---

## src/suppressions.py

No findings. This is a small, carefully built module and every truncation in it is the marked,
reversible kind (`_preview()`, line 45–56, appends an ellipsis and is only ever used for a
*display* preview of a reason whose full text is still on disk) — the one place a truncation was
previously stored rather than displayed (the `[:300]` on the stored `reason` in `add()`) has
already been removed per the comment at lines 123–132, and I confirmed the current code stores
`str(reason).strip()` whole. `fnmatchcase` (not `fnmatch`) is used deliberately and correctly in
both `suppressed()` and `problems()` to avoid Windows case-folding silently widening a
suppression's scope. `_load()`'s wrong-shape and unreadable-vs-missing distinctions match their
docstrings.

---

## Summary of findings by severity

- **High confidence, filed as work orders:** 1
  - `cleanup.py:231,233,261` — ceiling/description text is silently truncated (46–70 chars, no
    marker) at append time into the report lists, despite an adjacent comment that reads as
    claiming this was fixed alongside the roster-level caps it sits next to.
- **Medium confidence:** 1
  - `canon_backup.py:345-346` — `verify()`'s "changed" count includes live files that are merely
    unreadable right now, not actually changed; possibly the same thing already filed under
    order 323703189931 ("verify()'s docstring promise") — flagged in case it's a distinct,
    wider instance.
- **Low confidence / minor:** 2
  - `derivation.py:608-610` — `scan_constants_with_reason()` counts `True`/`False` as numeric
    literals (bool is an int subclass); affects only an advisory "N literals" count.
  - `weave.py:464` — a bare `[:34]` name-truncation with no marker survives in a five-key demo
    print, in a file otherwise swept clean of exactly this shape.
- **Questions (not filed as defects; both readings given):** 2
  - `canon_backup.py:255` — `prune(keep=0)` keeps everything rather than pruning everything;
    plausibly deliberate (avoids a `-0` slicing footgun) but undocumented as such.
  - `dashboard.py:437` — `movement()`'s history buffer caps at 2,000 rows; harmless today (both
    consumers need ≤45 minutes of samples) but uncommented and could bite a future, longer-window
    consumer.

## Already-filed items confirmed present, not re-filed

- `assay.py` — parallel five-grade attestation tables (order 6d132aa1e8aa); `ATTESTATION_FLOOR`
  no monotonicity/ceiling guard (open question); `axis_score:228` `or`→`and` mutant (settled,
  genuinely killed).
- `weave.py` — `components()`/`resolve()` continuity resolution (order e0f9da6e9466); `main()`'s
  four now-fixed console cuts (order 357e24fa2fa1); `null_threshold()` dead code
  (order e637c67ab438) — independently reconfirmed it has zero callers.
- `canon_backup.py` — `snapshot()` two-snapshot collision on `stamp` (order 61037867dc5d);
  `verify()`'s docstring promise (order 323703189931).

No file under `src/` was modified in the course of this audit.
