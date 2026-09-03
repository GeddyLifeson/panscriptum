# sweep42 batch 4 audit

Modules read in full: `src/standards.py` (2248 lines, read across 3 passes covering
1-922/923-1844/1845-2248 — full coverage confirmed), `src/completeness.py`,
`src/manifest_builder.py`, `src/withdraw_chapters.py`, `src/pantheon.py`, `src/style_audit.py`,
`src/tuning.py`, `src/repass_bands.py`.

General note: these eight files are exceptionally heavily self-audited already — the majority of
`standards.py`, `completeness.py`, `manifest_builder.py` and `withdraw_chapters.py` consists of
inline docstrings/comments recording specific prior defects (found-and-fixed, with order IDs) in
exactly the categories this sweep looks for (green-by-absence, swallowed exceptions, Hard Rule 0
caps, discarded write verdicts). Most of the obvious instances of those shapes have already been
repaired and the repair is narrated in place. The findings below are the residue: places where
the exact same defect shape the file's own comments describe elsewhere was *not* applied
consistently within the same file.

## Confirmed defects

### 1. `src/style_audit.py:199-205` — MACHINE TELLS ranking still truncated with no disclosed remainder

```python
print(f"\nMACHINE TELLS  ({_WATCHED} patterns watched, style prompt Rule 7)")
if a["banned"]:
    for k, c in sorted(a["banned"].items(), key=lambda kv: -kv[1])[:14]:
        rate = c / max(1, n)
        flag = "  OVERUSED" if rate > 0.05 else ""
        print(f"   {c:>5}  {rate:>6.2%}/entry  {k}{flag}")
    print(f"   ({len(a['banned'])} distinct tells present)")
```

This hard-caps the printed ranking at 14 rows via `[:14]`. The same `report()` function has a
purpose-built helper, `_cut()` (lines 156-171), whose own docstring says:

> "THREE OF THE FOUR RANKINGS IN `report` WERE CUT WITH NO REMAINDER (order 1cb7bd3ad0ce).
> OPENING SHAPES, EXACT OPENERS and VOCABULARY printed a `most_common(...)` window under a
> heading that describes the CORPUS ... with no count of how many shapes or openers there were in
> total ... ranking is fine and stays, the REMAINDER has to be visible (Hard Rule 0)."

OPENING SHAPES, EXACT OPENERS and VOCABULARY were all retrofitted to call `_cut()` and print
"showing X of Y; Z more not shown." MACHINE TELLS — the fourth ranking in the same function — was
left on the plain `[:14]` slice with only a bare "(N distinct tells present)" line after it,
which requires the reader to do the subtraction themselves rather than being told the remainder
directly, and never states how many watched-pattern rows were cut off the ranked list itself.
This is the identical shape the surrounding comment names as the defect Hard Rule 0 forbids, in
the one place in this function it was not applied.

Confidence: high. The file's own comment identifies "four rankings" and documents fixing three of
them; this is the fourth, unfixed, in the same commit's blast radius.

### 2. `src/repass_bands.py:126-130` — DEMOTED list truncated to 8 with no remainder count, labeled "a sample"

```python
print("\n  DEMOTED — a sample of what was carrying a Magnitude:")
by_band = collections.Counter(b for _, _, b, _ in demoted_entries)
print(f"     by band: {dict(sorted(by_band.items()))}")
for s, n, b, sn in demoted_entries[:8]:
    print(f"     [{b}] {str(n)[:30]:<32}{sn}")
```

Directly above this, the SURVIVORS block was fixed for exactly this shape (order 89fc2eaf23f1),
and the fix's own comment says so explicitly:

> "THE HEADING SAID 'every one of these' OVER A SLICE OF FOURTEEN (order 89fc2eaf23f1). That is
> Hard Rule 0's exact shape ... The sibling DEMOTED list below has always said 'a sample of';
> this one now says what it is AND what it is a sample of ... so the reader knows how much is off
> the page."

That comment names the DEMOTED list as the unrepaired sibling and it remains unrepaired: it
prints 8 of `len(demoted_entries)` (which can be in the hundreds — this is the re-pass that
"demotes to unassayed every band whose evidence does not survive the corrected reading," expected
to be large) with no "showing 8 of N; N-8 more not shown" line, and CLAUDE.md's Hard Rule 0 bans
the word this heading uses by name: "No limit, no cap, no sample, no 'top N' ... Ranking is still
allowed and is encouraged ... Ranking then truncating is not." The total count is printed earlier
in the run in the "SOURCE CEILINGS"/"ENTRY BANDS" summary (`len(demoted_entries)`), so a careful
reader could cross-reference it, but the DEMOTED block itself does not, unlike its SURVIVORS
sibling three lines above it.

Confidence: high. Same reasoning as finding 1 — the file's own adjacent comment names this exact
list as the known-unfixed twin of a bug it just fixed one block up.

### 3. `src/manifest_builder.py:414-424` — owner-exclusion reasons truncated in the one report whose entire job is preserving them

```python
import roll as _roll
_excluded = _roll.out_of_scope(roll)
if _excluded:
    print("excluded by owner ruling (records kept, work stopped):")
    for _n, _why in sorted(_excluded.items()):
        print("   %-44s %s" % ((_n or "?")[:43], _why[:90]))
```

`roll.out_of_scope()` (src/roll.py:55-67) is explicitly documented as existing to carry the
reason, not just the name:

> "RETURNS THE REASON, NOT JUST THE NAME. An exclusion with no reason attached is how a real
> source gets quietly dropped and nobody can reconstruct why ... Every caller that skips a source
> can therefore say what it is skipping and on whose authority."

`manifest_builder.py` is a caller of exactly this function, and it cuts the source name to 43
characters and the reason (`note`) to 90 characters with no ellipsis, no "N more not shown," and
no total-length disclosure — silently discarding whatever text falls past those limits. This is
the same shape already fixed at least twice elsewhere in this codebase for the identical
"reason cut mid-sentence" failure (`standards.py:616`, "A `[:40]` slice cut the REASON, not the
name ... forty is tighter than the seventy already found too short," and
`catalogue_models.py:130-138`, cited from that same comment). Real notes on the roll can run long
("owner ruling," "on whose authority" implies attribution + justification), and a source name can
exceed 43 characters too (this same file's `load_record()` docstring cites a 67-character real
source name, "Who Framed Roger Rabbit (incl. all content from its associated crossover-toon
IPs)"). The cut is silent — there is no marker showing text was dropped — on the one governance
line CLAUDE.md's Hard Rule 2 points an operator at to understand why a source was excluded.

Confidence: high. This is printed-only (not written to any file), so the underlying data is not
lost from disk, but the operator-facing report of *why an owner stopped work on a source* is
exactly the kind of accountability text the project's own precedent treats as un-cuttable.

## Questions (possibly deliberate, not fixes)

### Q1. `src/tuning.py:61-66` — `PROOF_STALE_SECONDS` staleness policy is explicitly unresolved

```python
# Past this age a pool proof is annotated as stale but still counted at full strength. ...
# Whether a stale proof should be DISCOUNTED rather than merely captioned is a live question
# (m59: even a FRESH proof once certified 4-of-36 while live calls succeeded at 2.8%) and is
# not settled here.
PROOF_STALE_SECONDS = 3600
```

The code's own comment says this is an open question the author declined to settle. Flagging per
the audit brief's instruction to raise (not resolve) anything that reads as deliberately
unfinished design — this is a candidate for the owner to rule on, not a defect to patch.

### Q2. `src/completeness.py:293` — category label truncated to 40 chars as a dict key

```python
c[str(e.get("category") or "?")[:40]] += 1
```

Cuts a record's `category` field to 40 characters when building the per-source `by_category`
breakdown used throughout `COMPLETENESS.json`. In practice this causes no observed collision
today because every real category string (`"Persons (named individual characters, real or
fictional)"`, `"Vessels & Things (...)"`, `"Events (...)"`, etc.) differs within the first few
characters, so no two fold onto the same 40-char prefix on the current category vocabulary. Not
raised as a confirmed finding because there is no demonstrated harm and the categories are a
small, closed, owner-defined set — but it is the same *shape* of cut (`str(name)[:N]` used as a
grouping key) that this project has treated as a defect elsewhere purely on the theoretical
collision risk (`standards.py`'s fixed 18-char source-name cut, "eighteen-character prefixes
COLLIDE: every source of the form 'Warhammer Fantasy *' folded onto one string"). Worth a second
look if the category vocabulary is ever extended with two categories sharing a long common
prefix.

### Q3. `src/completeness.py:723-728, 743` — printed-table column width truncates source names to 33 chars

`main()`'s console table (`str(r["source"])[:33]` for both the ranked coverage rows and the
"NOT MEASURED" list) is a disclosed partial view — the function already states "rows printed: N
of M (the file holds every row)" and the underlying `COMPLETENESS.json` holds full names — so
this is lower-severity than findings 1-3 above. Flagged only because the identical column-cut
shape was found and fixed elsewhere in this same codebase for exactly this field (the
"worst-covered sources" list in `standards.py`, which removed an 18-char cut on `r["source"]` for
the stated reason that real source names collide past that length). 33 characters is roomier than
18, but the underlying hazard (two long, similarly-prefixed source names rendering identically in
this one column) is the same risk class, just less likely to trigger today.

## Coverage recorded

Ran (or will run) the sweep_plan recorder for run42, batch 4, covering: standards.py,
completeness.py, manifest_builder.py, withdraw_chapters.py, pantheon.py, style_audit.py,
tuning.py, repass_bands.py.
