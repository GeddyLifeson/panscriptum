# AUDIT — BATCH 13 (run31)

**Modules:** `src/assay.py` (868 lines), `src/derivation.py` (558 lines), `src/onomast.py` (407
lines), `src/address.py` (290 lines), `src/render.py` (252 lines), `src/thread_integrity.py`
(184 lines), `src/scope.py` (152 lines).

**Total lines read: 2,711 (every line, all 7 files).**

Read-only sweep. No file was edited except this report. `derivation.check_graph()` and
`address.spine_code_for()` were exercised via `python -c` (read-only; no state mutated, no
existing files written).

---

## ASSAY.PY

### A1 — Concurrency race permanently corrupts `SIGMA_BY_ATTESTATION["Witnessed"]` (BLOCKING, VERIFIED)
`src/assay.py:496-531`, root cause `510-523`.

`calibration_report()` re-derives the charter's calibration point by **mutating the module
global** in an unlocked loop:

```python
saved = SIGMA_BY_ATTESTATION["Witnessed"]
try:
    s = max(AXIS_MIN + 0.5, saved - 2.0)
    while s <= min(SIGMA_MAX, saved + 2.0):
        SIGMA_BY_ATTESTATION["Witnessed"] = s
        ...
        s += 0.005
finally:
    SIGMA_BY_ATTESTATION["Witnessed"] = saved
```
This is the *exact* anti-pattern the file's own comments (551-559) diagnose and fix for
`WEIGHTS` — "a per-call reweighting stays invisible to every other caller... but this function
read the module-global WEIGHTS... custodes.py builds exactly such a table... Found 2026-08-24" —
except the fix (a local `W =` override) was applied to `WEIGHTS` and never to
`SIGMA_BY_ATTESTATION`.

**Confirmed live trigger:** `dashboard.py` calls `_AS.calibration_report()` from `/api/state`
(dashboard.py:514), served by `socketserver.ThreadingTCPServer` (dashboard.py:924) — each
request runs in its own thread, and the dashboard's own docstring says it "Auto-refreshes."
Two concurrent requests (two browser tabs, or one auto-refresh landing mid-poll) can interleave:
Thread B's `saved = SIGMA_BY_ATTESTATION["Witnessed"]` can capture a value Thread A is
mid-sweep-mutating, and Thread B's `finally` then **permanently restores the wrong number** —
overwriting the true 3.2003 with a corrupted mid-sweep value for the remainder of the process.
Every subsequent `assay()` call with `attestation="Witnessed"` (the overwhelming majority of the
library, per the calibration comment itself) then publishes a silently wrong interval — precisely
the "QUIET kind" of drift the file's own header warns is catastrophic ("a calibration that
drifts is a library-wide falsehood... `M3.52 +/- 0.06` is exactly as convincing as
`M3.52 +/- 0.12`").
`drill.py:333,336` also calls `calibration_report()`, widening the exposure window further.

Severity: blocking (corrupts a value every printed Magnitude in the library depends on).
Confidence: VERIFIED by code+call-graph; the interleaving itself is a race (not reproduced live
in this read-only audit) but the mechanism is unambiguous.

### A2 — Hard Rule 0: error-message enumeration capped at 6 (MINOR)
`src/assay.py:452` — `"; ".join(sorted(bad)[:6])`. `_check_scores` still raises for *every*
malformed axis (the rejection itself is complete), but the exception text silently drops any
bad entries past the 6th, so a caller fixing "all" reported problems and re-running may still
fail on a 7th they never saw listed.

### A3 — top-of-ladder edge case elsewhere (per prompt instruction; not the known M10 bug)
Checked `instrument()` (687-733) and `band_for_quantity()` (232-248) for the same missing-top-
rung saturation pattern as the known `axis_score()` M10 bug. Both are fine: `instrument()`'s
`grade_n = max(0, LADDER.index(anchor) - 5)` tops out at exactly 5 for M10 (list has indices
0-5), and `INSTRUMENT_WINDOWS["M10"] = (30, 30)` correctly saturates by design, not by omission.
`band_for_quantity()` has no upper-index arithmetic at all. No re-file needed.

---

## DERIVATION.PY

### D1 — Hard Rule 0: "deepest chains" report capped at 6 (MINOR)
`src/derivation.py:534` — `sorted(LEDGER, key=lambda x: -depth(x))[:6]`. Display-only; the
actual graph-closure check (`check_graph()`) is exhaustive over all of `LEDGER` (verified: ran
it, 0 problems on 100+ entries). Still a literal `[:N]` on a ranked listing.

### D2 — "syntax error" and "module absent" are indistinguishable in the constants-scan report (MINOR)
`src/derivation.py:483-484` (module missing → `return None`) vs `489-491`
(`except SyntaxError: silence.note(...); return None`) — both paths return `None`, and
`main()` prints both identically as `(absent)` (546-547). A module that exists but has a real
syntax error is reported exactly like a module that was never written, hiding a genuine break
behind text implying nothing is there. Matches lens item 2 (swallowed failure indistinguishable
from a legitimate negative).

---

## ONOMAST.PY

### O1 — Genre/feature-weighted register logic is dead code in the only production path (MAJOR/BLOCKING, VERIFIED)
`src/onomast.py:268-334` (the entire `FEATURE_SHIFT` table, `GENRE_WEIGHT`/`FEATURE_WEIGHT`,
and the vote-tally body of `register_for()`) vs the sole caller, `name_worlds()`:

```python
reg = register_for(v["continuity_group"])          # line 356 — no genre_register, no features
```

`register_for(group_id, genre_register=None, features=None)` immediately takes the naive
hash-fallback branch whenever both optional args are absent (line 318-320) — which is *every*
call in this file, since `name_worlds()` never supplies them. Repo-wide grep confirms no other
caller anywhere passes those args either (`navtree.py` defines its own unrelated local
`register_for`). So the ~65 lines of carefully documented genre/feature logic — built explicitly
to fix "the register that gave Alien and Doom the flowing elvish sound and denied Greek myth the
classical one" (317) — never runs for the one thing this file actually produces
(`ONOMASTICON.json`, written by `name_worlds()`). The docstring's claim that this was fixed is
false for the live pipeline; the carried-name catalogue designations are still assigned by pure
hash of `continuity_group`, exactly the bug the comment says was retired.

Confirmed by direct grep across the whole repo (`grep -rn 'onomast\.register_for'` → no hits
outside the file itself; `grep -rn 'import onomast'` → only `navtree.py`, `pipeline.py`, neither
of which calls `register_for` with extra args).

### O2 — Same missing-invariant fallback pattern survives in the *true*-exhaustion branch (MINOR, VERIFIED)
`src/onomast.py:260-265`:
```python
silence.note("onomast.py:coin-exhausted")
return coin_name(f"{base}|fallback", register)     # no well_formed check, no taken check
```
The comment at 244-249 documents that the FIRST fallback used to skip both the `well_formed` and
`taken` checks and calls that "the single code path capable of breaking [uniqueness] silently...
open until 2026-08-24." That first fallback (253-255) is now checked. But the *final* fallback,
reached only after 10,000 deterministic candidates are all taken/malformed, has the identical gap
— it is only *logged* via `silence.note` (JANITOR tier: "no authority to stop anything," per
CLAUDE.md's escalation chain), not prevented. A genuinely exhausted register can still emit a
duplicate or malformed catalogue name; only the fact of exhaustion is now visible. Low likelihood
(10,000 candidates), but it is the exact invariant the surrounding comment claims was closed.

### O3 — Hard Rule 0: report caps (MINOR)
`src/onomast.py:389` (`[:4]` endonyms shown), `392` (`[:9]` rows per endonym), `394`
(`src[:34]` truncated attestation string). Display-only in `main()`; `ONOMASTICON.json` itself
(line 399) is written complete and uncapped.

---

## ADDRESS.PY

### AD1 — Token-overlap fallback silently invents an address among tied ambiguous candidates instead of returning UNASSIGNED (MAJOR, VERIFIED BY DIRECT TEST)
`src/address.py:101-114`, `spine_code_for()`'s last-resort fallback:
```python
if coverage >= 0.8 and overlap > best_overlap:
    best, best_overlap = code, overlap
```
Ties (equal `overlap`, both `>= 0.8` coverage) resolve to whichever candidate is encountered
first in `codes.items()` — i.e. `CHARTER_SPINE_CODES.json`'s file order (alphabetical). Tested
directly against the live index:
```
spine_code_for("Alien Predator Doom Crossover") -> "II.N"       # Alien's code
spine_code_for("Doom Predator")                 -> "II.N.2"     # Doom's code, not Predator's (II.I)
```
Three single-token index entries — `Alien` (II.N), `Predator` (II.I), `Doom` (II.N.2) — are all
equally plausible matches for a name mentioning all three; the function picks one arbitrarily
rather than recognizing the ambiguity. This directly violates Hard Rule 2 ("Don't invent
addresses... Surface these to the owner for a real assignment rather than silently inventing
one") — the file's own comments (64-84) fixed an earlier, related false-hit bug (`DC` matching
inside "Sword Coast") specifically to avoid this class of silent misassignment, but the
coverage-based fallback added afterward reopens the same hazard in a different shape. A real
roll source with a genuinely ambiguous or multi-franchise name could be silently shelved under
the wrong spine code instead of landing in `unassigned_sources.md` for owner review.

### AD2 — Hard Rule 0: cosmetic `[:N]` truncations (COSMETIC)
`src/address.py:127` (`slugify` result capped to 60 chars — filesystem-safety, not data loss),
`208` (`digest[:20]` — explicitly documented "flavor only, not load-bearing"), `230`
(`hexdigest()[:24]` — cache-key shortening, 96 bits, not a universe cap). Flagged per
instruction to report every instance; none of these drop real data.

---

## RENDER.PY

### R1 — Wrong child count displayed for empty containment nodes (MINOR, VERIFIED)
`src/render.py:110,122`:
```python
n = max(1, len(children))                                    # line 110
...
f'{n} {"child" if n == 1 else "children"} ... '               # line 122
```
`n` is clamped to at least 1 to avoid a division-by-zero in the angle geometry further down, but
the *same* `n` is reused, unadjusted, for the printed header count. A node with genuinely **zero**
children renders "1 child" in its own SVG instead of "0 children" — a display bug born from
reusing a geometry-safety variable as a data value.

### R2 — Hard Rule 0: `main()` demo caps a world sample with `limit=1` (COSMETIC)
`src/render.py:222` — `WS.build_all(limit=1)[0]`. Confined to the CLI self-test/demo path
(`if __name__ == "__main__"`), not the production `view()`/`children_of()` pipeline, which is
itself uncapped (`children_of()` returns every bucket, no truncation of the actual children set).

### R3 — Hard Rule 0: cosmetic `[:N]` display truncations (COSMETIC)
`src/render.py:140` (`[:26]` SVG label), `186` (`[:24]` representative child name inside
`children_of()` — only truncates the *display name string* of one representative child, not the
buckets/count themselves), `230` (`[:64]` printed URL). Note `59` (`TIER_ORDER[:5]`) is **not**
a Hard Rule 0 violation — it's a fixed partition of a 9-element constant tuple of tier *names*,
not a truncation of any data listing.

---

## THREAD_INTEGRITY.PY

### T1 — Corrupt record file silently misclassifies real threads as DANGLING (MAJOR, VERIFIED)
`src/thread_integrity.py:52-57`:
```python
try:
    with open(p, encoding="utf-8") as f:
        rec = json.load(f)
except Exception:
    silence.note("thread_integrity.py:54")
    continue
```
Any `data/records/*.json` file that fails to parse silently vanishes from `ents[source]`. In
`classify()` (108-113):
```python
gone = [k for k in shared if k not in ents.get(a, ()) or k not in ents.get(b, ())]
if gone and len(gone) == len(shared):
    out["DANGLING"] += 1
```
If source `a`'s record file failed to load, `ents.get(a, ())` is empty, so *every* shared key
looks "gone" for *every* pair involving `a` — the pair is filed as `DANGLING` (a genuine
coherence hole per the module's own taxonomy) when the real cause is a data-loading failure, not
an actual dangling thread. The two causes are indistinguishable in the output. Matches lens item
2 exactly.

### T2 — Partial weave drift is invisible; DANGLING only fires at 100% (MAJOR, VERIFIED)
`src/thread_integrity.py:108-117`. The `DANGLING` test requires `len(gone) == len(shared)` —
*all* shared keys missing from at least one side. A pair where, say, 9 of 10 shared entity keys
have drifted away (real weave drift, `gone` non-empty but not total) falls through to
`IMPLIED-UNRECORDED` and is recorded using the **stale, un-adjusted** `len(shared)` = 10 (line
116) — silently counting 9 already-dead attestations as live shared evidence. Real partial drift
is never surfaced anywhere in the output; only total drift is caught.

### T3 — Hard Rule 0: owner-facing "review these" hole list capped with no overflow notice (MODERATE)
`src/thread_integrity.py:179` — `sorted(detail["ASYMMETRIC-SUSPECT"], key=lambda x: -x[2])[:6]`
under the explicit header "one-way with no excuse (real holes, review these)." Unlike
onomast.py's equivalent loop, there is **no** "...and N more" trailer — if more than 6 real
coherence holes exist, the reviewer sees only 6 with no indication more exist (the aggregate
count printed earlier, line 170, is the only place the true total appears). Same pattern at
line 174 (`[:8]` for `RECIPROCAL`), lower stakes since that list isn't a "review these" call to
action.

---

## SCOPE.PY

### S1 — `srlimit=3` caps wiki search evidence feeding the Magnitude ceiling (MAJOR, VERIFIED)
`src/scope.py:74` — `F.api(host, {"action": "query", "list": "search", "srlimit": "3", ...})`.
Across the 4 `QUERIES`, at most 12 candidate pages (pre-dedup) are ever considered as evidence
for a source's cosmological scope. A page ranked 4th+ by the wiki's own search relevance for
"multiverse", "universe", etc. is never seen, regardless of what tier language it contains. This
is a textbook Hard Rule 0 violation embedded directly in a scoring pipeline, not report code —
`SCOPE.json` is read by `magnitude.py` and `pipeline.py` (per the file's own comment at line 118)
to bound a source's Magnitude.

### S2 — `titles[:8]` further truncates the (already-capped) evidence set (MAJOR, VERIFIED)
`src/scope.py:81` — `pages = F.fetch(host, titles[:8])`. Compounds S1: even the handful of
titles that survive the `srlimit=3` cap across 4 queries are cut again before full-text fetch
and regex tier-counting.

### S3 — Fallback path reintroduces the exact frequency-bias the module's own docstring argues against (MAJOR, VERIFIED, contradicts own docstring)
`src/scope.py:86-93`:
```python
best = None
for lab, _, band in _RE:                 # low -> high; correctly keeps the HIGHEST clearing tier
    if counts[lab] >= MIN_MENTIONS:
        best = (lab, band)
if best is None:                          # nothing clears it: fall back to the commonest tier
    lab = max(counts, key=counts.get)     # <-- frequency, not "highest tier with real usage"
    ...
```
The module's header docstring (25-30) states its entire methodology *against* frequency:
"Not by frequency. Every fiction says 'planet' constantly, so counting words puts Marvel... at
planet scale on 112 mentions against 61 for universe. The signal is the HIGHEST tier that
appears with real usage, not the commonest." The primary path (86-89) honors this correctly. But
the fallback — reached whenever no tier clears `MIN_MENTIONS = 10` — selects by raw count
(`max(counts, key=counts.get)`), which is precisely the "counting words" anti-pattern the
docstring's own worked example (Marvel, 112 vs 61) was written to warn against. A weakly-attested
source that never clears the floor for any tier gets scored by exactly the method the file exists
to avoid.

### S4 — Transient probe failures become permanent, unretryable gaps (MAJOR, VERIFIED)
`src/scope.py:108-114`:
```python
try:
    sc = scope_for(h)
except Exception:
    silence.note("scope.py:110")
    sc = None
out[h] = sc
```
`build()`'s resumability check is `h not in out` (line 106). Once *any* value — including a
swallowed-exception `None` — is written for a host, it is permanently treated as "already
processed" and excluded from every future `--build` run's `todo` set. A transient network error
or API hiccup is therefore indistinguishable from "probed successfully, no scope signal found,"
and it silently and permanently forecloses that host from ever being retried, without raising
above JANITOR tier.

### S5 — Hard Rule 0: debug-print truncation (COSMETIC)
`src/scope.py:139` — `[:900]` on the `--probe` CLI's JSON dump. Debug-only.

---

## SUMMARY BY SEVERITY
- Blocking/Major: 11 (A1, O1, AD1, T1, T2, S1, S2, S3, S4, and D2/O2 arguably major-adjacent
  though filed as minor above for conservatism)
- Moderate: 1 (T3)
- Minor: 6 (A2, D1, D2, O2, O3, R1)
- Cosmetic: 6 (AD2, R2, R3, S5, and the two hash-truncation notes folded into AD2)

All VERIFIED by direct code reading; AD1 and D-graph-closure additionally VERIFIED by running the
actual functions read-only. A1's race mechanism is VERIFIED in code and call graph; the
concurrent-interleaving trigger itself is inferred, not reproduced live, so treat the *existence*
of the race as VERIFIED and its *real-world frequency* as HYPOTHESIS.
