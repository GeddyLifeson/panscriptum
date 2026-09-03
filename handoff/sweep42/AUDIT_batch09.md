# sweep42 batch 9 — audit

Modules read in full: `src/foreman.py`, `src/allsweep.py`, `src/rosetta.py`, `src/zfighters.py`,
`src/axis_correlation.py`, `src/grounding.py`, `src/resync_roll.py`, `src/chord_field.py`.

All eight modules are already heavily hardened — most carry extensive comments documenting past
bugs found and fixed by earlier sweeps (fail-closed rewrites, atomic-write gating, Hard Rule 0
truncation fixes, etc.). This audit looks for what is *still* wrong, not what has already been
fixed and annotated as such.

## Confirmed defects

### 1. `src/rosetta.py:112-113` — `_STAND` regex is dead code; Stand statistics can never be mined

```python
_STAND = re.compile(
    r"\b(power|speed|range|durability|precision|potential)\s*[:=|]\s*([A-E])\b", re.I)
```

The comment immediately above it (lines 96-100) asserts this is *how* the parser handles JoJo's
Bizarre Adventure Stand statistics: "Stand stats are read from their parameter block instead (see
`_STAND`)." But `_STAND` is referenced nowhere else in the file — grep confirms only its own
definition and the comment mention it:

```
$ grep -n "_STAND" src/rosetta.py
100:# from their parameter block instead (see _STAND).
112:_STAND = re.compile(
```

`SCALE_QUERIES` explicitly searches for `"stand stats"` and `"stand parameters"` pages, and
`_SCALE_TITLE` would happily match a title containing "stat"/"parameter". But once such a page is
fetched, `scales_for()` only ever calls `numeric_rows()` (which needs `[0-9]` sequences — Stand
grades are single letters A-E, so it yields ~0 rows) and then `ordinal_rows()` against
`ORDINAL_LADDERS`, which has no `"stand"` entry at all (only `disaster`, `hero_class`,
`curse_grade`, `ninja_rank`, `esper_level`). With `len(rows) < 8` on both attempts, the page is
silently `continue`d and never added to `found`. So the JoJo Stand-stat scale — explicitly named
in this module's own query list and explicitly documented as supported — is unreachable code: it
is queried for, fetched, and then thrown away with no error, no note, and no line in the printed
mining summary saying so. This is exactly the class of "a check that cannot fail looks exactly
like a check that passed" this project's own doctrine warns about, just on the acquisition side
rather than the verification side.

**Confidence: high.** Verified directly by grep (zero call sites) and by tracing `scales_for()`'s
only two parse paths, neither of which can produce a Stand-stat row.

### 2. `src/rosetta.py:572` — `--refine` summary table truncates the host list with no disclosure

```python
for host, scales in sorted(out.items(), key=lambda kv: -sum(v["n"] for v in kv[1].values()))[:12]:
    tot = sum(v["n"] for v in scales.values())
    print(f"   {tot:>5}  {host:<34}{', '.join(sorted(scales))[:44]}")
```

This is the `--refine` command's closing summary: it ranks refined hosts by total surviving rows
and then slices to the top 12 with `[:12]`, and there is no "... and N more" line anywhere after
the loop (compare `_head()` in `allsweep.py`, or this very module's own `--top` handling in
`axis_correlation.py`, both of which announce what they cut). This is precisely the shape Hard
Rule 0 names: "Ranking is still allowed and is encouraged... **Ranking then truncating is not.**"
The underlying `OUT` file written just above is NOT truncated (the full refined dict is written
to disk before this loop runs), so no corpus data is lost — but a person reading this console
report has no way to tell whether 12 hosts or 200 survived refinement, or which specific hosts
were dropped from the table.

**Confidence: medium-high.** The letter of Hard Rule 0 draws no line between "console diagnostic"
and "corpus data" — every other truncation this project has fixed under that rule was also "just"
a printed report. Confirmed by direct code read; low risk of being intentional given the
project's own established idiom (disclose every cut) is right next to it in `--mine`'s and
`--check`'s output in this same file.

### 3. `src/rosetta.py:574` — same print statement, scale-name list cut to 44 chars, no disclosure

```python
print(f"   {tot:>5}  {host:<34}{', '.join(sorted(scales))[:44]}")
```

Independent of finding #2: even for a host that *is* shown, the joined list of its surviving
scale names is sliced to 44 characters with a bare `[:44]` and no ellipsis or count of what was
cut. A host with many scale types (e.g. multiple ordinal ladders plus a numeric scale) will show
a silently truncated name list.

**Confidence: medium.** Same defect class as #2, same line; flagged separately because it is an
independent truncation site that would need its own fix (e.g. printing a count of scales instead
of, or in addition to, the joined names).

## Questions (possibly deliberate — not filed as fixes)

- **`src/rosetta.py:462`** (`--probe` command): `top = sorted(sc["values"].items(), key=lambda
  kv: -kv[1])[:6]` — same truncation shape as #2/#3, but this is a manual, interactive
  single-host preview command that writes nothing to disk. It may be intentionally a "look at the
  top few" eyeball tool rather than a corpus-completeness report. Flagging because it is the same
  code shape the rest of the project has been correcting, but not filing it as a confirmed
  Hard-Rule-0 defect since nothing downstream treats this output as authoritative.

- **`src/rosetta.py` `check()`, lines ~365-395**: `ambiguous_assay_names: len(collided)` is
  computed from the *global*, unscoped `a_by`/`collided` pass (built once at the top of `check()`
  from every assay's bare normalised name) and then attached to every row's report dict — even
  when `by_host` scoping is what actually drives the row's `known.get(...)` lookup (the path
  `main()`'s `--check` actually uses). So a row's printed `ambiguous_assay_names` count describes
  collisions in a lookup table that row did not use, while the *relevant* per-host collisions
  (from `assays_by_host()`) are computed and printed separately in `main()`, not attached to the
  row. This may be intentional (the field predates the host-scoping fix and was left as
  supplementary global context), but the naming makes it easy to misread as "collisions that
  affected this row." Flagging as a question rather than a defect since it doesn't affect the
  correlation numbers themselves, only a metadata field.

- **`src/axis_correlation.py`, `widening()`**: the function signature takes one scalar `sigma`
  applied identically to every axis (`indep = sum((w[k] * sigma) ** 2 for k in axes)`; likewise in
  the covariance loop), while the module's own docstring states the general propagation formula
  with a per-axis `sigma_i`. This may be a correct simplification if every caller only ever
  invokes this within a single worksheet/provenance tier that genuinely shares one sigma across
  all its axes (plausible, given `assay.py` — not in this batch's module list — likely assigns
  sigma by attestation tier rather than per-axis). Flagging because it can't be confirmed correct
  without reading `assay.py`, and because it silently assumes uniformity rather than either
  accepting a per-axis dict or asserting the caller's tiers are in fact uniform.

## Modules with no additional findings

`src/foreman.py`, `src/allsweep.py`, `src/zfighters.py`, `src/grounding.py`,
`src/resync_roll.py`, `src/chord_field.py` were read in full and, beyond the extensive
already-documented and already-fixed history recorded in their own comments, no new confirmed
defects or open questions were found. These files show a consistent, deliberate pattern of
fail-closed guards, gated atomic writes, uncapped diagnostic lists with explicit "and N more"
disclosure, and escalation-chain compliance (Hard Rule -1) that this audit did not find broken
anywhere new.
