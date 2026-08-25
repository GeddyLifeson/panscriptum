# Batch 13 audit — overwatch.py, handbuilt.py, custodes.py, backfill.py, sweep.py, thread_integrity.py, ledger.py

Every line of all 7 modules read in full (2,481 lines total: 707+487+418+300+249+184+136,
matching `wc -l` exactly). `NEXT_STEPS.md` §3 read first; findings cross-checked against it.

---

## 1. overwatch.py (707 lines)

### 1a. [HIGH, KNOWN — M8 in NEXT_STEPS] `overwatch.py:652` dedups by fingerprint KEY EXISTENCE
ONLY, not by state, so a retired finding can never reopen.

```python
650:            for f in found:
651:                fid = _fingerprint(m, f)
652:                if fid in led["findings"]:
653:                    continue
654:                f.update({"state": "open", "first_seen": time.time(), "digest": d})
655:                led["findings"][fid] = f
656:                fresh += 1
```

Confirmed exactly as described in NEXT_STEPS. `_fingerprint` (line 208-210) hashes
`module|symbol|actual[:80]`. The retirement loop at lines 623-629 sets `state="retired"`
on ANY digest change to the file, regardless of whether the specific defect was fixed:

```python
623:    for fid, f in list(led["findings"].items()):
624:        if f.get("state") != "open":
625:            continue
626:        d = _digest(os.path.join(SRC, f["module"] + ".py"))
627:        if d and d != f.get("digest"):
628:            f["state"] = "retired"
629:            f["retired_at"] = led["last_run"]
```

**Concrete failure scenario:** round N finds bug B in module X, fingerprint F stored with
`state="open"`. An unrelated edit anywhere in X (e.g. a comment, or an adjacent unrelated
fix) changes the file's digest. Round N+1's retirement loop sees the digest differs and
flips F's state to `"retired"` — this is NOT a verification the bug was fixed, only that
*something* in the file changed. Bug B is still present. Round N+2 re-reads X (it's
"changed", so `rotation()` prioritises it), the model rediscovers the same bug at the same
symbol with the same `actual` text, computes the identical fingerprint F, and line 652 sees
`F in led["findings"]` — already true, regardless of state — and discards the rediscovery.
The bug never reappears as `open` again. WATCH.md's own footer claims "A finding stays open
until the file it points at changes" — true only for the first cycle; after one retirement
the same live bug becomes permanently invisible.

### 1b. [HIGH, KNOWN — M8 in NEXT_STEPS, verified live against `data/OVERWATCH.json`]
**"Overwatch's zero is not evidence."** Full breakdown of the live ledger, computed directly:

```
total findings ever filed:  69
currently open:              0
state=retired:               51   (27 via digest-change [no verdict], 24 via foreman._retire
                                    [has retired_why, no model verdict])
state=closed:                12   (all carry "auto-triage refuted: ..." — genuine verify_open
                                    model verdicts)
state=refuted:                5   (no verdict field, no code path currently sets this state)
state=stale:                  1   (same — orphaned)
```

So **only 12 of 69 findings (17.4%) were ever closed by a real model re-check**; the other
57 (82.6%) were closed with zero verdict — 51 via digest-change/foreman bypass (both
mechanically distinct from a verification), plus 6 more in an orphaned state that no live
code path produces (see 1c below). `data/OVERWATCH.json` currently shows **0 open findings**,
which is the "no high-severity findings open" standard's evidence — but per the above, that
zero was not earned by re-verification in the overwhelming majority of cases.

**Is the auto-triage loop actually running?** Yes — confirmed by the 12 genuine `closed`
verdicts (which only `verify_open()`, lines 453-501, can produce) and by
`rounds=76, last_run="2026-08-25 06:51"` in the live ledger, which matches the known 06:51
restart time for the five STANDING processes (dashboard/publish/foreman/overwatch/pipeline,
NEXT_STEPS lesson 5). The loop is live; it is simply outnumbered roughly 5-to-1 by
non-verifying retirement paths.

### 1c. [NEW, LOW-MED] Orphaned `state="refuted"`/`state="stale"` findings with no live writer
Six findings in the ledger sit in states (`refuted` ×5, `stale` ×1) that `_STATE_RANK`
(line 225) still accounts for, but that no current code path in `overwatch.py` or
`foreman.py` sets — `verify_open()` only ever writes `state="closed"` (line 491) or leaves
`state="open"`; `foreman._retire()` only ever writes `state="retired"`. Grep across `src/`
for the literal `"refuted"` finds it nowhere as an assignment target except a unit-test
fixture in `verify_math.py:1872`. All six carry `first_seen` timestamps around 2026-08-19/20
and no `verdict`, `retired_why`, or `closed_at` field. This looks like residue from an
earlier version of `verify_open` (before the 2026-08-24 "CLOSER the findings lifecycle never
had" rewrite documented at lines 453-462) that once set `state=verdict` directly instead of
always `"closed"`. These six are invisible to every count in `write_report()` (not `open`,
not `retired`) — harmless bookkeeping debris rather than a live defect, but worth a note
since it means the ledger's own state vocabulary has entries no current writer produces.

---

## 2. handbuilt.py (487 lines)

### 2a. [NEW, MED] Docstring claim about Zalama's interval width is false against the live
computed output.

```python
162:  # The one sheet here that REFUSES most of its own axes. Zalama never acts on-page: his entire
...
166:  # Every other entity in this file scores eleven axes; this one scores five, and its
167:  # published interval is four times wider as a direct result. That is the instrument
168:  # being honest about a thin record rather than manufacturing a number to fill the row.
```

Ran `handbuilt.compute()` directly (miniconda python):

```
Zalama                    interval 0.08   (6 axes unestimable)
every other entity        interval 0.06   (0 axes unestimable)
```

0.08 / 0.06 = 1.33×, not 4×. The comment's specific, checkable numeric claim does not match
what the code it sits beside actually produces. (Not a data-corruption bug — `assay()`
itself is outside this batch — but it is a comment inside `handbuilt.py` making a false
factual claim about this module's own output, which is squarely lens item 6.)

No other findings in `handbuilt.py`: `compute()` and `main()` were read in full; the
`ROSTER` dict is static hand-authored data (out of scope for a logic audit), the write path
(lines 453-459) correctly writes-before-print with `silence.replace_retry` and checks its
return value, and the sort key at line 467-469 is a straightforward descending sort.

---

## 3. custodes.py (418 lines)

No correctness bugs found. Read in full and exercised via `python src/custodes.py`, output
matches the module's own internal claims (interval shrinks monotonically as attestation
quality improves across Instrumented→Witnessed→Transcribed→Reconstructed→Disputed;
`dof_coverage()` reports 10/10 one-to-one; Threnody's veto correctly nulls the decimal).
The one place a lens item 1 "check that cannot fail" pattern might apply —
`covers_every_reading` at line 344, which is true by construction because `half` is defined
as `max(1.96*sd, max|v-consensus|)` — is **already disclosed by the module's own comment**
(the "m30" note at lines 335-343 states plainly that this is a guarantee, not a check, and
names what a real check would need to report instead). Since the contradiction the lens is
looking for is exactly what that comment says out loud, this is not a new finding.

---

## 4. backfill.py (300 lines)

### 4a. [HIGH, KNOWN — listed in NEXT_STEPS §3] `backfill.py:176` — "already held" set is built
from ALL entries, not just Persons.

```python
176:    have = {re.sub(r"[^a-z0-9]+", "", e["name"].lower()) for e in r["entries"]}
177:    names = roster(host)
178:    missing = [t for t in names if re.sub(r"[^a-z0-9]+", "", t.lower()) not in have]
```

Confirmed unchanged at source. `have` is built over every entry in the source record
regardless of category, so a normalized-name collision with any Faction/Place/Vessel/Event
entry causes a genuinely-missing Person to be excluded from `missing` and never backfilled.
**STILL OPEN.**

No other new findings in `backfill.py`. `roster()`'s uncapped category walk (lines 68-123),
`lead()`'s prose-block detection, and `backfill_source()`'s write path (gated on
`P.write_record_catalogue`'s return value, lines 228-233) were all read line-by-line and are
sound. Note (not filed as a separate finding, too speculative to be actionable): normalized
matching between wiki page titles and catalogued names does not strip parenthetical
disambiguators from `have`, so e.g. a page titled `"Kratos (God of War)"` normalizes
differently from a catalogued `"Kratos"` — this can cause spurious *duplicate* additions
rather than data loss, the opposite direction from the §176 bug, and I did not verify it
happens on live data.

---

## 5. sweep.py (249 lines)

### 5a. [NEW, MED] The funnel's documented "each stage is a strictly smaller set than the one
above" invariant is false on live data, and the display code does not handle the violation —
it prints a garbled negative-of-a-negative count.

The module's own docstring (lines 20-22): *"Each stage is a strictly smaller set than the
one above, and the size of each drop is the real statement of where the project stands."*
But `catalogued`, `addressed`, `reachable`, etc. (lines 169-177) are each computed as an
**independent** boolean predicate over the same row set — nothing in `sweep()` or `report()`
enforces or checks that later stages are subsets of earlier ones:

```python
170:        "catalogued": sum(1 for r in rows if r["catalogued"]),
171:        "addressed": sum(1 for r in rows if r["shelfmark"]),
172:        "reachable": sum(1 for r in rows if r["host"]),
```

Ran the actual project data (`python -c` against `pipeline.records()` / `WIKI_HOSTS.json` /
`NAVTREE.json`, then confirmed against a full live run of `sweep.report()`):

```
n           45,883
catalogued  32,222   drop  13,661
addressed   45,807   drop -13,585   <-- NEGATIVE: addressed > catalogued
reachable   45,800   drop      7
read        40,240   drop  5,560
evidenced   25,198   drop 15,042
assayable   18,008   drop  7,190
```

`addressed` (45,807 — a source having a shelfmark in NAVTREE.json) is **not a subset** of
`catalogued` (32,222 — the individual entry having been judged by phase 2): most sources are
shelved before every one of their entries is individually catalogued, so far more entries
count as "addressed" than "catalogued." The actual `report()` print loop (lines 183-189)
was reproduced exactly against these numbers:

```
  catalogued     32,222   70.2%  ##########################   -13,661
  addressed      45,807   99.8%  #####################################   --13,585
  reachable      45,800   99.8%  #####################################   -7
```

Note the double-minus `--13,585` on the addressed line — `drop` is already negative
(`prev - f[k]` with `f[k] > prev`), and the format string at line 187-188 unconditionally
prepends a literal `-`: `f"   -{drop:,}"` becomes `-` + `-13,585` = `--13,585`. This is not
merely an aesthetic glitch: it is the visible symptom of the funnel model being wrong for
this pair of stages, printed as gibberish instead of the true story (that "addressed" is
actually *larger* than "catalogued" because the two measure unrelated things). Anyone
reading `CHARACTER SWEEP` output would see a nonsensical number rather than the real
finding, which is that catalogued-per-entry status lags shelving-per-source status by
13,585 entries.

### 5b. [NEW, LOW] Diagnostic caps in `report()`'s console output
`gap.most_common(10)` (line 215) and `bysrc.most_common(8)` (line 222) show only the top
10/8 sources for "unreachable" and "read but no axis found" respectively. Per this project's
own lesson 16 (a truncated diagnostic can hide that the un-shown rows share the exact same
cause), these are candidates for the same class of finding already fixed elsewhere in the
tree. Low severity here because the underlying full data is written uncapped to
`CHARACTER_SWEEP.json` (`silence.write_json`, lines 240-243, correctly gated on the return
value) — only the console preview is capped, not the record of state.

---

## 6. thread_integrity.py (184 lines)

### 6a. [NEW, MED] `classify()`'s DANGLING check only fires when EVERY shared key in a pair
has died on at least one side; partial drift is silently folded into the non-dangling
buckets with a stale, un-filtered `shared` count.

```python
108:        if ents is not None:
109:            gone = [k for k in shared if k not in ents.get(a, ()) or k not in ents.get(b, ())]
110:            if gone and len(gone) == len(shared):
111:                out["DANGLING"] += 1
112:                detail["DANGLING"].append((a, b, len(gone)))
113:                continue
114:        if recorded is None:
115:            out["IMPLIED-UNRECORDED"] += 1
116:            detail["IMPLIED-UNRECORDED"].append((a, b, len(shared)))
```

`gone` collects every shared entity key that no longer resolves on at least one side. The
DANGLING branch only triggers when `len(gone) == len(shared)` — i.e. when the pair's
evidence has died *completely*. If even one of several shared keys survives, the whole pair
falls through to `IMPLIED-UNRECORDED` (or, once a directed thread graph exists,
`RECIPROCAL`/`ASYMMETRIC-*`) carrying the **original, unfiltered** `shared` set — the dead
keys inside `gone` are never removed from it, and `len(shared)` (used for both the printed
count and the sort key at lines 174 and 179) still includes them.

**Concrete failure scenario:** sources "Marvel" and "Naruto" share 5 entity keys
`{a,b,c,d,e}` per `WEAVE_CANDIDATES.json`. A later catalogue pass renames or drops entities
`a`, `b`, `c` from `data/records/marvel.json`, so `ents["Marvel"]` no longer contains them
— real, exactly the kind of "weave drift" this module exists to catch (per its own module
docstring: *"DANGLING points at nothing that exists"*). `gone = [a, b, c]`,
`len(gone)=3 != len(shared)=5`, so the DANGLING branch is skipped entirely. The pair is
counted as `IMPLIED-UNRECORDED` with `shared=5` — as if all five links were still live
evidence for an omniverse connection — when 3 of the 5 point at entities that no longer
exist. Those three individually-dangling references are never reported anywhere: not in
DANGLING (pair-level check didn't fire), not filtered out of the surviving bucket. This
directly contradicts the module's own definition of what DANGLING is meant to catch, for the
(likely much more common) case of partial rather than total drift.

---

## 7. ledger.py (136 lines)

### 7a. [HIGH, KNOWN — M18 in NEXT_STEPS] `assay_to_standards()` collapses to a flat value at
the top rung M10, silently, the same missing-edge-case bug `axis_score()` (outside this
batch) answers a different, incompatible way.

```python
127:    from assay import BAND_EDGES, LADDER
128:    if magnitude_band not in BAND_EDGES:
129:        return None
130:    i = LADDER.index(magnitude_band)
131:    lo = BAND_EDGES[magnitude_band]["ruin"]
132:    hi = BAND_EDGES[LADDER[min(i + 1, len(LADDER) - 1)]]["ruin"]
133:    joules = math.exp(math.log(lo) + (ruin_score / 10.0) * (math.log(hi) - math.log(lo)))
```

At `magnitude_band = "M10"` (the last element of `LADDER`), `i = len(LADDER)-1`, so
`min(i+1, len(LADDER)-1) = i` — `hi` is looked up at the SAME index as `lo`, so `hi == lo`.
`math.log(hi) - math.log(lo) == 0`, so `joules = lo` regardless of `ruin_score`. Confirmed
live:

```
LADDER[-1] = 'M10'
ruin_score 0    -> joules 9.999999999999922e+98, standards 4.672897196261646e+90
ruin_score 3    -> joules 9.999999999999922e+98, standards 4.672897196261646e+90
ruin_score 5    -> joules 9.999999999999922e+98, standards 4.672897196261646e+90
ruin_score 7    -> joules 9.999999999999922e+98, standards 4.672897196261646e+90
ruin_score 9.9  -> joules 9.999999999999922e+98, standards 4.672897196261646e+90
```

Every M10 entity, regardless of its actual `ruin_score` (0 through the ceiling 9.9), prices
identically — same numeric symptom family as the already-known `axis_score()` flat-9.9
defect at M10, implemented via a different mechanism (index-clamp collapsing the log
interpolation range to zero rather than a hardcoded return). **STILL OPEN**, unchanged at
source. NEXT_STEPS already frames the fix as an owner-level charter question (what M10's
top-rung semantics should actually be), not a mechanical repair — so this is recorded here
as KNOWN/re-confirmed rather than a new finding.

No other issues found in `ledger.py`: `to_standards`/`from_standards`/`cross_rate` correctly
return `None` for the deliberately-inconvertible `"poneglyph-grade favour"` currency, and
`work_value()` is a pure one-line division against the imported (not restated)
`MATERIAL["rock"]["pulv"]` constant, exactly as the module's own comment (lines 38-42)
claims.
