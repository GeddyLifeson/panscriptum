# Cross-module changes needed — RUN batch 5 (run #36)

Batch 5 owns `custodes.py`, `feats.py`, `genre.py`, `halo.py`, `secondopinion.py`. The changes
below land in modules this batch does not own and were NOT made. Both orders stay OPEN.

---

## 1. `src/anchors.py:190` — Lumen's staleness input (order `2af7ca515157`)

**Verified true.** `custodes.staleness_widening(distance, years_since)` returns `0.0` whenever
either argument is None (custodes.py:288-289); `convene()` defaults both to None
(custodes.py:295-296); and the sole production caller passes neither:

```
src/anchors.py:190:  col = CU.convene(a["anchor"], a["scores"], attestation=a["attestation"],
src/anchors.py:191:                   worksheet="anchors.py")
```

Every other `convene(` call in the tree is in `custodes.main()`'s own demo or in
`verify_math.py`. `verify_math.py:591-593` DOES pass `distance=1.126, years_since=300` and
asserts the interval widens — so the mechanism is unit-tested and works. It is simply never
reached in production, and `half += stale` (custodes.py:328) adds exactly 0.0 on every real
reading. Lumen, whose entire dasein is "the world shows up as LIGHTCONE", silently asserts that
every reading is perfectly current.

Also confirmed: `CUSTODES["Lumen"]["dispersive"] = True` (custodes.py:204) is never read
anywhere — only the definition and a comment at line 326 mention it. It is a declared flag with
no consumer.

**Why no code was written.** This is not a mechanical wiring job, and that is the finding.
`ANCHORS` entries carry `kind`, `anchor`, `note`, `scores`, `attestation` — and no notion of
remove or elapsed time. `propagation.observed_mark(distance, years_since)` wants a shelf
separation in the Concordance's own distance units and years since the event. **Nobody has
decided what those values ARE for a calibration anchor.** The Skate Guy and Goku are instruments
for reading the scale, not shelved entities observed from a stated vantage. Supplying a number
to make the code path fire would be inventing the measurement, which is worse than the current
honest 0.0.

**Proposed change, for whoever owns `anchors.py` — and it needs an owner ruling first:**
either (a) add explicit `distance` / `years_since` to each `ANCHORS` entry and pass them
through at anchors.py:190, or (b) rule that anchors are read AT ZERO REMOVE by definition, and
make that explicit rather than accidental — pass `distance=0.0, years_since=<anything>` so
`staleness_widening` returns a real 0.0 it computed, instead of the sentinel 0.0 it returns for
"nobody told me". Option (b) costs one line and converts a silent gap into a stated convention.
**Recommend (b) plus an owner question on (a).** See OWNER QUESTIONS below.

---

## 2. `src/anchors.py` + `src/resonance.py` — Threnody's curl veto (order `f467f662be4b`)

**Verified true.** `resonance.hodge_decompose` and `resonance.resonance_strength` have ZERO
callers anywhere in `src/`. `resonance.py` is imported in exactly one place — `verify_math.py:6787`
— and only `incomparability_rate` is exercised there (lines 6789-6799). `custodes.convene`'s
docstring (custodes.py:302) claims "`eta` (from resonance.hodge_decompose) lets Threnody exercise
her veto", and the veto branch is real and correct (custodes.py:350+, threshold `CURL_VETO_THRESHOLD
= 0.10`, derived from Saaty's CR bar via Theorem 1). But `eta=` is passed in only two places, both
non-production: `custodes.main()`'s own demo (custodes.py:415, literal 0.70) and
`verify_math.py:507,510`. The one production caller, anchors.py:190, passes no `eta`.

So Threnody's veto is SAFETY IN A FILE, NOT IN EFFECT — the third property from Hard Rule -1,
and the module docstring asserts the opposite.

**Why no code was written.** `hodge_decompose(edges)` needs a pairwise CONTEST FLOW graph —
`(a, b) -> "a beats b by this much"`. No such data exists. `data/SHARED_STAGE_GRAPH.json` exists
and is what `resonance_strength` reads, but it holds CO-ATTESTATION weight (how much furniture
two shelves share), which is a different quantity and must not be fed to `hodge_decompose` as if
it were a flow. Wiring the veto means first deciding where contest edges come from — plausibly
`rosetta.py`'s franchise rank data, which is the only ranked pairwise material in the tree.
That is a design decision, not a repair.

**Proposed change:** none yet. This needs the input question answered before any module is
edited. Do NOT wire `resonance_strength`'s graph into `eta` as a stopgap — the two quantities
are not interchangeable and a plausible-looking eta would make the veto fire (or not) on the
wrong evidence, which is worse than a veto that never fires.

---

## 3. Not an order — noticed in passing, `src/wh40k.py:197`

`wh40k.py:197` still carries the unconditional `"[wiki] " + v[1]` worksheet stamp (order
`1770c2b84786`, already filed and still open). `halo.py` had the identical defect and was fixed
this shift under order `2345e4b431fe` using the per-axis 3-tuple pattern `zfighters.py` already
uses. Whoever picks up `1770c2b84786` can copy the halo fix directly: add a third element to each
axis tuple (`"wiki"` / `"canon"`), change the sheet comprehension to `"[" + v[2] + "] " + v[1]`,
and add `"provenance": v[2]` to the emitted axes dict. In halo's case 24 of 33 axes turned out to
be `canon`, i.e. nearly three quarters of the provenance tags were false.

---

# OWNER QUESTIONS

1. **What is an anchor's remove?** Do calibration anchors have a distance/years_since at all, or
   are they read at zero remove by definition? Until this is answered, Lumen contributes nothing
   to any production interval.
2. **Where do contest edges come from?** `hodge_decompose` needs a pairwise flow graph that does
   not exist in the tree. Without one, Threnody's veto cannot ever fire in production, and
   `resonance.py` has no production caller at all.
3. **Should `secondopinion`'s waived share be capped by a net?** See `handoff/nets/batch05.md`
   NET 1b. Waived findings are currently 400 of 1,004 (39.8%). A share-based net cannot be walked
   around by picking a new rule code, but its threshold would be a fresh parameter.
