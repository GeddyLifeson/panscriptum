# Sweep 43 — Batch 08 Audit

Files read in full: `src/magnitude.py`, `src/chain.py`, `src/catalogue_web.py`,
`src/weave_index.py`, `src/axis_correlation.py`, `src/navtree.py`, `src/context_budget.py`,
`src/profile.py`.

Method note: every file in this batch already carries a heavy layer of self-documented prior
fixes ("order xxxxxxxxxxxx"). Findings below are things that survived a fresh read against the
actual runtime behaviour, not restatements of what the comments already say was fixed. Several
candidate readings that turned out to be correct-as-written on closer inspection (e.g.
`magnitude.saturated()`'s numeric-only filter against the string sentinels `A.NONE` /
`A.UNESTIMABLE` / `A.INAPPLICABLE`; `axis_correlation.rho()`'s "no matrix" vs "matrix with no
measured pairs" distinction, which turns out never to diverge because `measure()` guarantees
`mean_r` is non-`None` exactly when `pairs` is non-empty) are omitted rather than reported, per
the instruction to verify before writing anything down.

## magnitude.py

No findings. Read start to finish, including the five-guard verification pipeline (`verify`,
`_split_gate`, `subject_refusal`, `_resolve_citation`, `quantity_scores`), the split-vs-one-shot
transport selection in `assay_entity`, `saturated()`, `calibrate()`'s resumable checkpointing,
and `run_batch()`. Spot-checked the specific things the task brief asked about: the string
sentinels are excluded correctly from `saturated()`'s numeric filter; guard 3 (SUBJECT) is now
called on all three paths (one-shot `verify`, split `_split_gate`, and instrument
`quantity_scores`), matching the module's own account of when it used to be skipped; the
cross-axis citation check is correctly scoped to only the paths where `flat`'s indexing is
meaningful. This module's own docstrings are unusually reliable guides to its actual behaviour.

## axis_correlation.py

No findings. `_pearson`, `measure`, `rho`, `widening` all check out against their own claims.
One thing worth naming for the record since the task brief specifically asked about it:
`widening()` (in this file) uses a single scalar `sigma` for every axis, which looks at first
glance like it contradicts the file's own header derivation (`Var = SUM (w_i sigma_i)^2 + ...`,
written with a per-axis `sigma_i`). It is **not** a defect: `widening()` is not what the
library's published intervals are computed from. `assay._interval` (src/assay.py, outside this
batch but checked to resolve the question) implements the real covariance term itself, with a
genuinely per-axis `_s[k]` and its own loop calling `axis_correlation.rho()` directly — it never
calls `widening()` at all. `widening()`'s only caller anywhere in `src/` is `drill.py`'s
`correlation_actually_widens_the_bar` net, where a uniform sigma is an acceptable simplification
for a "does the covariance term move the bar at all" sanity check, not a production computation.

## navtree.py

No findings. `build()`'s two-pass (sources, then worlds) node accumulation, the `sources_under`
ancestor/descendant matching (post-m11 `+"."`-on-both-arms fix), the `register_for`/hyperverse
naming hash-order tie-breaks (post-m41 fix), and `audit()` all check out arithmetically against
what they claim to compute.

## context_budget.py

No findings. The derived-budget arithmetic in `content_budget_chars` / `feats_block_budget`
correctly applies the prose ratio to scaffolding and the content ratio to entity JSON, matches
the header's measured numbers, and the two correction constants (`JOB_OVERHEAD_CHARS`,
`METADATA_INFLATION`) are applied at the stage the header says they should be. One inefficiency,
not a correctness issue: `content_budget_chars` builds a throwaway `"x" * int(scaffold_chars)`
string (potentially tens of thousands of characters) purely to hand its length back to
`estimate_prose_tokens`. Harmless but wasteful; not filed as a work order since it's neither a
fault nor a Hard Rule 0 issue.

## catalogue_web.py

No findings. `_singular()` was checked against every example in its own docstring by hand
(Goddesses→Goddess, Bosses→Boss, Classes→Class, Boxes→Box, Witches→Witch, Princess/Colossus/
Analysis unchanged, Species/Deities/Movies/Heroes unchanged, Characters→Character, Places→Place,
Vehicles→Vehicle, Gods→God) and every one is correct. The category/provenance bookkeeping in
`catalogue()` and `catalogue_composite()`, the MAX_PER_SOURCE/MAX_PER_CATEGORY dead-cap guards,
and the `--shortfall`/`--recatalogue` selection logic all check out.

## weave_index.py

No findings. `designations()`'s cache-invalidation-on-failure behaviour, `_records_sig`'s
finish-the-walk-on-unstattable-entry handling, `build()`'s exclusion counting (empty key /
stopname), and `main()`'s candidate-matching short-key cutoff (correctly scoped to matching only,
not to the stored index) all check out.

## chain.py

No confirmed defects. One design question worth raising — see QUESTIONS below.

## profile.py

### MINOR — `decode()`'s address/feats character classes are looser than the actual B32 alphabet,
so a malformed profile string crashes with an unhelpful `ValueError` instead of the function's
own intended "not a world profile" message.

`src/profile.py:109`
```python
m = re.fullmatch(r"PS-([0-9a-z]+)-([a-z]{2})([a-z])-([0-9a-z]{4})-([0-9au])([0-4])", profile)
```

`B32` (line 66) is the 32-symbol Crockford alphabet with `i`, `l`, `o`, `u` deliberately excluded
(the comment directly above it explains at length why `u` in particular must not be a legal
address digit). But the address group (`[0-9a-z]+`) and the feats group (`[0-9a-z]{4}`) both
accept the full 36-character `0-9a-z` range, i.e. they also accept `i`, `l`, `o`, `u` — characters
that are not in `B32`. A string that passes this regex with one of those characters in the
address or feats position then reaches `_unb32()` / the `B32.index(ch)` lookup in `decode()`'s
features comprehension, which raises a bare `ValueError: substring not found` rather than the
`ValueError(f"not a world profile: {profile!r}")` the function raises for a regex mismatch.
Verified directly:

```
>>> profile.decode('PS-i23-myc-0000-u0')
ValueError: substring not found
```

Contrast with the **band** character group two positions later, `[0-9au]` — that one *is*
correctly scoped to exactly the encodable band values (digits 0-9 for M0-M9, `a` for M10, `u` for
unassayed), so the fix pattern already exists in the same regex; the address/feats groups were
just not given the same treatment.

Practical impact is low today: `decode()` has exactly two callers in `src/` (`drill.py`,
`verify_math.py`), both self-test contexts working with strings this module's own `encode()`
just produced, and the profile string is documented as never being persisted anywhere. So nothing
currently feeds `decode()` untrusted or corrupted input. It is filed because it is the same bug
shape the comment immediately above `B32` was written to warn against ("an alphabet that can
read what it cannot write is a decoder that cannot say 'this is not one of mine'") — just not
fully closed for two of the six regex groups — and because if a profile string is ever persisted
or exchanged (the module's own docstring frames that as the eventual point of the format), this
becomes a real crash-on-load path rather than a clean rejection.

**Remedy:** replace `[0-9a-z]` in the address and feats groups with the literal B32 class
(`[0-9a-hj-km-npqrst-z]`, i.e. `0-9a-z` minus `i`, `l`, `o`, `u`) so the regex can only ever match
what `B32.index()` can resolve.

## QUESTIONS (for the OWNER)

### Q1 — `chain.adjudicate_mutuals()`'s epoch split re-keys only the WINNING side of each
direction, leaving the losing side bare. Is that the intended semantics?

`src/chain.py:713-718`, inside the "both sides dated, and dated differently" branch:
```python
for (x, y), ep in (((w, loser), ea), ((loser, w), eb)):
    n = out.pop((x, y))
    out[(ID.node(x, epoch=ep), y)] += n
```

`ea`/`eb` come from `ID.epoch_of()` reading a single provenance *sentence* — a sentence that
names both combatants at one shared moment in the narrative ("Once he becomes serious, he
casually overpowers Glorio..."). When a mutual pair is split by epoch, this loop re-keys only
`x` — the winner of that direction — onto an epoch-suffixed node (`ID.node(x, epoch=ep)`); `y`,
the loser of that direction, is left as a bare, epoch-less node. Concretely, for the Goku/Tao
example the module's own docstring uses, the split produces edges `Tao@pre-training → Goku` and
`Goku@post-training → Tao`, not `Tao@pre-training → Goku@pre-training` and
`Goku@post-training → Tao@post-training`.

This does still dissolve the specific 2-node cycle that made the pair "mutual" — after the split
there are four distinct node identities (`Tao@ea`, `Goku` bare, `Goku@eb`, `Tao` bare), and none
of them has both a recorded win over and a recorded loss to the same opponent — so the stated
purpose of the function (stop feeding Bradley-Terry an unresolved contradiction) is met either
way. What is not obviously intended is that the *loser's* strength estimate in each split edge
is attributed to a bare node that can also accumulate wins/losses from every other unrelated,
epoch-unspecified mention of that same character elsewhere in the corpus — diluting exactly the
entity whose evidence this split was supposed to disambiguate, on the side that lost.

This is a judgment call about what "each dated side" (the docstring's own phrase) was meant to
mean — the direction of the edge, or both combatants named by the dated sentence — and not
something this audit can settle from the code alone, so it is filed as a question rather than a
finding. If the intended reading is "both combatants," the fix is to also key `y` with the same
`ep` on each iteration.
