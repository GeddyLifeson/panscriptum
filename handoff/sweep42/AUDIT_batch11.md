# sweep42 batch 11 — audit

Modules read in full: src/overnight.py (1556 lines), src/rigor.py (957), src/custodes.py (684),
src/weave.py (548), src/sevenfold.py (422), src/feats_index.py (370), src/context_budget.py (297),
src/profile.py (223).

General note: this is an unusually heavily self-audited set of files — most of the classic
failure classes (swallowed exceptions, unfailable checks, truncated rosters) have already been
found and fixed by prior sweeps, with the fix and the old defect both left in the docstrings.
Several of the findings below are the SAME class of defect the surrounding code already fixed
elsewhere in the same file, just not applied consistently to every print site.

## CONFIRMED DEFECTS

### 1. `src/weave.py:476-477` — ranked list truncated with no disclosure (Hard Rule 0)
```python
    for g in multi[:12]:
        print(f"   {len(g):>3}  {[x[:26] for x in g[:4]]}{' ...' if len(g) > 4 else ''}")
```
`groups` (and therefore `multi`) is returned by `components()` already sorted `-len(g)` (largest
first), so `multi[:12]` is rank-then-truncate on the size ranking — exactly the pattern Hard Rule
0 names as forbidden ("Ranking then truncating is not [allowed]"). Nothing before or after this
loop states how many multi-source groups were not printed (`len(multi)` is never shown). Compare
to `rigor.py`'s `main()` printing of `load_bearing` a few files over, which extends the display
cut through ties and prints `"... and N more"` — the fix pattern already exists in a sibling
module and was not applied here. Confidence: high.

### 2. `src/weave.py:488-490` — same pattern, "strongest genuine fusions"
```python
    for v in sorted(resolved.values(), key=lambda x: -x["n_attestations"])[:8]:
        print(f"     {v['canonical_name'][:30]:<32}{v['n_attestations']:>3}  "
              f"{[x[:18] for x in v['attestations'][:3]]}")
```
Ranks `resolved` by attestation count descending and truncates to 8 with no "and N more" and no
statement of how many entities exist above the cutoff. `fused` (the total count of genuinely-fused
entities) is printed a few lines earlier but is never connected to this list as "showing 8 of
`fused`". Confidence: high.

### 3. `src/weave.py:493-496` — same pattern, "most-split homonyms"
```python
    byk = collections.Counter(v["key"] for v in resolved.values())
    print("\n  most-split homonyms (one name, many universes):")
    for k, n in byk.most_common(6):
```
`Counter.most_common(6)` is a ranked-then-truncated list of homonym keys with no disclosure of how
many keys exist beyond the top 6. Same class as findings 1-2, same file. Confidence: high.

### 4. `src/rigor.py:467-473` — component list in a refusal message sliced without disclosure
```python
    out["refusal"] = (
        f"comparison graph is not strongly connected: {len(comps)} components "
        f"{[c[:3] for c in comps][:4]}. Ford (1957) — the MLE is identified only within a "
        ...
```
`comps` is the list of strongly-connected components computed by `_strongly_connected()`. The
message states `len(comps)` (so the count is honest) but then shows only the first 4 components,
each truncated to its first 3 members, with no "…and N more" for either cut. The module's own
docstring for `bradley_terry()` cites a real case with "38 entrants in 36 components" — on data
like that, this line would show 4 of 36 components and 3 of however-many entrants in each, and a
reader has no way to tell from the message itself that anything was dropped. This is precisely
"a list sliced before printing" as named in the audit brief. Confidence: high.

### 5. `src/custodes.py:661` — abstention note truncated with `...` and no length disclosed
```python
    for _dof in sorted(ABSTENTIONS):
        print(f"   ABSTAINED [{_dof}] — {ABSTENTIONS[_dof][:76]}...")
```
`ABSTENTIONS[_dof]` is a full, carefully-written explanation of why a Custos could not read (see
`_ABSTAIN_NOTE`, ~400-500 chars each). This demo print always appends `...` regardless of whether
the text was actually cut, and shows only the first 76 characters of a paragraph whose entire
point is to explain *why* a measurement is missing — the cut removes most of the reasoning the
note exists to state. Confidence: medium-high (this is in `main()`'s demo output, not a
production write path, but the module's whole purpose is that an absence must not be swallowed,
and here the *explanation* of the absence is what gets swallowed).

### 6. `src/custodes.py:638` — descriptive field truncated for table alignment
```python
    print(f"{n:<11}{c['dof']:<17}{c['charter']:<16}{c['refuses'][:44]}")
```
`c["refuses"]` is a full sentence in the `CUSTODES` table describing what each standpoint refuses
to do; this print silently drops anything past 44 characters with no ellipsis or remainder marker,
so a reader of the printed report cannot tell the field was cut at all. Matches the audit brief's
named pattern "`[:N]` on a printed/written string." Confidence: medium (single descriptive string,
not a roster/entry list, and the full text is recoverable from `CUSTODES` itself — but the printed
report is silently incomplete with no indication of that).

## QUESTIONS (possibly deliberate, flagging rather than fixing)

### Q1. `src/sevenfold.py:389-394` and `src/profile.py:185` — "sample" sections cut with no count
```python
    for s in sorted(coords)[:8]:              # sevenfold.py
    for d in sorted(worlds)[:8]:               # sevenfold.py
    for r in rows[:8]:                          # profile.py, under a "SAMPLE" header
```
All three are explicitly headed "sample"/"SAMPLE" rather than presented as a ranking or a complete
listing, and the true totals (`len(coords)`, `len(worlds)`, `len(rows)`) are printed a few lines
above each in the same function. Given the explicit "sample" framing this reads more like an
accepted illustrative-example convention than the roster-hiding failure Hard Rule 0 targets, but
raising it because it is the same `[:N]` shape as the confirmed findings above and none of the
three states "8 of N shown" the way `overnight.write_status`'s `STATUS_CYCLES_SHOWN` disclosure
does. Is a bare "sample" header considered sufficient disclosure, or should these follow the
"and N more" convention too?

### Q2. `src/profile.py:109-114` — `decode()`'s regex accepts characters outside the actual B32 alphabet
```python
m = re.fullmatch(r"PS-([0-9a-z]+)-([a-z]{2})([a-z])-([0-9a-z]{4})-([0-9au])([0-4])", profile)
...
address = _unb32(addr)          # _unb32 does B32.index(ch) per character
```
`B32 = "0123456789abcdefghjkmnpqrstvwxyz"` deliberately excludes `i`, `l`, `o`, `u` (Crockford's
convention, and the module's own header explains exactly this exclusion was tightened in run #33
so the alphabet "cannot read what it cannot write"). But the validating regex for the address and
feature groups is the much looser `[0-9a-z]+` / `[0-9a-z]{4}`, which still accepts `i`, `l`, `o`,
`u` in those positions. A profile string containing one of those letters in its address or
feature segment would pass the `re.fullmatch` check (so `decode()` does not raise its clean
`"not a world profile"` `ValueError`) and then crash a few lines later inside `_unb32` with a bare
`ValueError: substring not found` from `B32.index(ch)` — the exact "decoder that cannot say this
is not one of mine" failure the module's own header names as the reason `z` was removed from the
alphabet, just reappearing at the regex layer instead of the encoder. Low real-world impact since
the header also states no profile string is ever persisted (every one is rebuilt from
`worldseed`/`address_space` per run), so this only matters against a hand-crafted or corrupted
string. Is tightening the regex to the literal `B32` character class worth doing, or is this
edge case not worth the maintenance (the alphabet would then have to be kept in sync with the
regex by hand)?

## COVERAGE

Recorded via `sweep_plan.record('run42', [...], batch=11)` after this file was written.
