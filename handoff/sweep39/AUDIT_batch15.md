# run39 — comprehensive source audit, BATCH 15

Modules owned (obtained programmatically from `sweep_plan.batches(16)[14]["modules"]`, not from
any typed list):

    hostcheck.py       1302 lines   read in full
    dashboard.py       1089 lines   read in full
    build_terminal.py   634 lines   read in full
    weave_index.py      516 lines   read in full
    tiers.py            426 lines   read in full
    genre.py            337 lines   read in full
    resonance.py        298 lines   read in full
    halo.py             219 lines   read in full

No sampling, no caps (Hard Rule 0). Read-only: nothing under `src/` was edited.

None of the eight is in today's maintenance-shift set (verify_math, drill, mutate, workorders,
publish, local_agent, escalation, allsweep), so nothing here was re-read for half-finished work.

**That list is the one `batches(16)[14]` returned at the START of this batch. It is not the one
it returns now — see F16, which is a defect in the sweep's own planner and was hit by this
batch. The eight above are what was actually read, and the coverage shard has been corrected to
say exactly that.**

---

## FINDINGS

### F1 — MAJOR — the shortlist that gates an irreversible purge ignores the audit's own "cannot judge" flag

`src/hostcheck.py:948-951` (the `purge()` shortlist a person reads before running
`--purge --go`) and `src/hostcheck.py:1162` (the `roster_audit` console marker) both select
purely on `r["rate"] < 0.10`.

`roster_audit` computes a `judgeable` field at `src/hostcheck.py:1153-1154` for exactly this
purpose. Its own comment three lines above says why:

> A source whose title names a PRODUCT rather than a world cannot be judged this way at all: a
> homebrew class page has no reason to say "Unearthed Arcana" ... Marked so the finding reads as
> "not judgeable" rather than "foreign".

The field is consumed — `src/standards.py:1163` filters on `v.get("judgeable", True)` with the
comment "Four were being reported: two already purged, and two sourcebooks the test cannot speak
to. A standard that counts findings nobody can act on is a standard nobody reads." So the
MACHINE-facing standard has the filter and the two HUMAN-facing outputs in hostcheck do not.

Verified against `data/ROSTER_AUDIT.json` (43 rows). Every single row below the 0.10 bar is
`judgeable: False`:

    0.0   judgeable=False   Explorer's Guide to Wildemount
    0.0   judgeable=False   Extra Life
    0.0   judgeable=False   Player's Handbook

So today the shortlist is 3-for-3 false positives, and `roster_audit` prints
`<-- ROSTER FROM ANOTHER FICTION` beside all three. `purge()`'s docstring says the safety here
"is the HUMAN, not a second automated condition" and that "the audit shortlists; the reading
decides" — which makes the shortlist's accuracy the whole safety, and the purge it feeds empties
a record's `entries` and `os.remove()`s every cached page under `data/feats/<host>/` and
`data/readfeats/<host>/`.

`Explorer's Guide to Wildemount` is the sharpest case: `candidates_split`'s own docstring
(`src/hostcheck.py:410-413`) cites it as the pass's SUCCESS story — "Wildemount IS Critical
Role's setting" at 90% — and the roster shortlist proposes it for purge.

**Remedy.** Filter both sites on `r.get("judgeable", True)`. Do not drop the non-judgeable rows:
print them under their own heading ("shortlisted by rate, but this test cannot speak to a
product title — read, do not purge") so the count stays whole per Hard Rule 0. The marker at
:1162 should say `<-- LOW RATE, NOT JUDGEABLE` for those rows rather than accusing them.

---

### F2 — MINOR — the aboutness veto has no minimum-sample floor and is published without its denominator

`relevance()` at `src/hostcheck.py:336-338`:

    bodies = _bodies(host, titles)
    if not bodies:
        return None
    about = sum(1 for b in bodies if any(t in b for t in toks))
    return round(about / len(bodies), 3)

There is no floor on `len(bodies)`. The hit rate next door has one — `MIN_PROBE = 5`, with the
comment "under five names, a hit rate is noise -- 1/2 reads as 50% and means nothing"
(`src/hostcheck.py:200`) — and it is enforced at `src/hostcheck.py:688`. The aboutness rate,
which is the other half of the same judgement, has none.

The veto fires at `src/hostcheck.py:693`:

    elif r["about"] is not None and r["about"] < ABOUT:
        r["verdict"] = "NAMES ONLY"

Bounded honestly: `src/hostcheck.py:690` runs first and requires `hits >= 2`, so `titles` and
therefore `bodies` hold at least 2 (not 1). But a two-article aboutness rate deciding NAMES ONLY
is the exact shape `_bodies`' own docstring records as a past defect:

> Twelve titles came back with a single extract, so aboutness was computed over one article and
> reported as a rate. Polynesian myth scored 98% held and 0% about that way.

The prop=revisions fix removed the `exlimit` cause; no floor was added, so the shape can recur
whenever a generous host returns few readable bodies.

Second half: the sample size is never recorded. `score()` at `src/hostcheck.py:674-676` stores
only `r["about"]`, and `r.pop("titles", None)` at :676 discards the titles. The API path samples
up to 12 (`relevance(..., sample=12)`, :302/:314) and the RAW path up to 8
(`src/hostcheck.py:361`, `EP.fetch_raw(host, list(titles)[:8])`), so two rows of
`HOST_FITNESS.json` can carry the same `about: 0.5` off different denominators with nothing
saying which.

**Remedy.** Return `(rate, n)` from `relevance` (or set `r["about_n"] = len(bodies)` in
`score`), write `about_n` into HOST_FITNESS.json, and add an `ABOUT_MIN` below which the veto
ABSTAINS — leaving the verdict to lift alone — rather than firing on a sample too small to mean
anything. Abstaining is the fail-safe direction here: the veto's job is to demote a generous
host, and demoting one on two articles is the reading that unassigns a correct wiki.

---

### F3 — INFO — `GOOD` is a constant nothing reads

`src/hostcheck.py:196`, `GOOD = 0.35`. Verified by grep across `src/`: the only occurrences are
the definition, the module docstring at :37, and two historical comments at :751 and :766 that
describe the code that USED to read it. No module imports it either.

This is documented rather than hidden — the module docstring at :33-38 says so outright: "The
two rate constants survive: `DEAD` separates 'WRONG FICTION' from 'NAMES ONLY' inside `score`,
and `GOOD` is now only the figure quoted in prose here." (`DEAD` at :197 is genuinely live, at
:692.) Filed only so the constant is either deleted or folded into the prose paragraph that is
now its only consumer; a live-looking module constant that nothing reads is the shape
`liveness.py` exists to count.

---

### F4 — INFO — a documented tautological floor in the repair pass

`src/hostcheck.py:792`:

    if best[2] and best[2] != r["host"] and best[0] > LIFT_MIN:

Verified: `best` is only ever assigned at :779-780 from a candidate whose `p["verdict"]` is
"holds" or "partial", and `score()` reaches either of those verdicts only after
`elif r["hits"] < 2 or r["lift"] <= LIFT_MIN` (:690) has NOT fired — i.e. only when
`lift > LIFT_MIN`. So `best[0] > LIFT_MIN` cannot refuse anything once `best[2]` is set.

Its own comment at :787-791 states this in those terms and keeps it deliberately: "Nothing that
passed `ok` can fail it -- the verdict already required it -- and it is kept for the same reason
`adopt()` keeps its floor: the gate should state the bar even when the bar is already met."

Not a defect. Filed so that this one is NAMED with its justification rather than rediscovered
each sweep as an unexplained can't-fail comparison, and so `liveness.py`'s ratcheted count can
carry it as sanctioned.

---

### F5 — INFO — the UNFIT artifact gets a no-op write on a repoint-only repair pass

`src/hostcheck.py:857` calls `_land(UNFIT, unfit)` whenever `fixed` is non-empty. `unfit` is
only mutated in the loop at :821-826, and only for entries where `v is None`. A repair pass that
repointed hosts and rejected none therefore re-lands a byte-identical `HOST_UNFIT.json`.

`_land_hosts` twelve hundred lines up argues against exactly this for its own target
(`src/hostcheck.py:136-140`): "A NO-OP MERGE MUST NOT WRITE. Re-landing an unchanged map is not
free on this file: it invalidates every other writer's in-flight digest ... a write with no
content behind it is pure exposure." The UNFIT writer has no such guard.

Consequence when the replace is denied — the ordinary case on this machine — the message at
:868-871 prints "0 rejection(s) from this pass are not on file, so the sources they dropped from
the host map now read as sources nobody has got to yet", which is a sentence about nothing.

**Remedy.** Gate the write on `any(v is None for v in fixed.values())`, and make the failure
message report the actual rejection count it is about.

---

### F6 — INFO — `purge()` overwrites its entry count per record file instead of accumulating

`src/hostcheck.py:993`, inside `for fp in sorted(glob.glob(...))`:

    n_entries = len(r.get("entries") or [])

Assignment, not `+=`. If a source ever had two record files, the log written to
`ROSTER_PURGES.json` at :1033 and the operator lines at :1036-1044 would report only the last
one's count while emptying both.

Measured today: 216 record files, 216 distinct sources, zero sources with more than one file. So
this CANNOT currently misreport. Filed as latent-only, at INFO, against a file whose whole
purpose (:930-931) is that "the gap it leaves is a recorded finding rather than a silence".

---

### F7 — MAJOR — `tiers.py`'s report says the hyperverse is declined for every shelf while the file it writes assigns one to most of them

`src/tiers.py:357`:

    print(f"\nhyperverse: DECLINED for all {len(srcs)} shelves — uncharted by cause, not omission")

`chart()` fills the field. `src/tiers.py:296-302`:

    xg = xenoverse_grounding(tiers["xenoverse_groups"], _groundings)
    for s in srcs:
        xi = out[s]["xenoverse"]
        if xi is not None and xi in xg:
            out[s]["hyperverse"] = xg[xi]["index"]
            out[s]["hyperverse_type"] = xg[xi]["grounding"]

and `xenoverse_grounding`'s own docstring opens with "THE HYPERVERSE. A grounding is answered per
XENOVERSE, not per shelf" (`src/tiers.py:152`), under a section header that says "The hyperverse
therefore comes from grounding.py and from nowhere else" (`src/tiers.py:138`).

Verified against the artifact this function writes, `data/TIERS.json`, 208 rows:

    (0, 'ex_nihilo')     166
    (None, None)          38
    (5, 'ungrounded')      2
    (3, 'demiurgic')       2

170 of 208 shelves carry a real grounding-derived hyperverse index and type. The report says
none do.

The same report then contradicts itself thirty-nine lines later: `src/tiers.py:396` prints
`H{c['hyperverse']}` in the SAMPLE STACKS block, so an operator reads "DECLINED for all 208
shelves" and then reads `H0 › X0 › Mt3 › Mv7` for Alien on the same page.

The module docstring carries the same stale claim in three places — the summary line at :44
(`168 multiverses -> 8 metaverses -> 6 xenoverses -> H declined`), the whole "THE HYPERVERSE
CANNOT BE CHARTED FROM INSIDE ONE" section at :61-90, and "So H stays '?'" at :87. All of it is
true of the LINK-GRAPH hyperverse that was removed at :128-138 and none of it is true of the
grounding-derived one that replaced it. The removal note itself says why this matters: "two live
definitions of one tier is worse than either of them" — and one live definition plus a report
describing the dead one is the same fault.

**Remedy.** Replace :357 with the real counts (`N shelves carry a grounding-derived hyperverse,
M carry none because they sit in no xenoverse`), and rewrite the docstring's summary and its H
section to say that the LINK-GRAPH hyperverse is declined by cause and the published H comes from
`grounding.py`. This is partly a curatorial call about what the tier now means, so it is filed at
SESSION rather than at BOTS.

---

### F8 — MINOR — `tiers.py`'s containment check is computed, printed, and thrown away

`src/tiers.py:368-380` computes two invariants and gates on neither:

    ok = all(counts[i] >= counts[i + 1] for i in range(len(counts) - 1))
    print(f"   monotone: {ok}")
    bad = 0
    ... (containment scan) ...
    print(f"   containment violations (a lower group split across two higher ones): {bad}")

Then `src/tiers.py:412` REASSIGNS the same name: `ok = silence.write_json(out, charted, ...)`,
so the monotone verdict is not even readable after that line, and `return 0 if ok else 1` at
:422 is the WRITE verdict, not the nesting one. A run with `bad > 0` publishes `TIERS.json` and
exits 0.

The module states the invariant as doctrine twice, in the same words both times:

* `src/tiers.py:111` — "A tier that does not contain its own members is not a tier."
* `src/tiers.py:156-157` — "A tier that does not contain its members is not a tier, and the same
  rule caught a bad metaverse cut earlier."

And `main()` already knows how to refuse: :408-411 declines to write when
`groundings_readable` is false, with "every row above is a guess". A containment violation is
the same class of statement about the same rows. `data/TIERS.json` is read by `address_space` at
import (`src/tiers.py:329-330`), so a bad write "silently re-charts the top of the Ladder of
Being" — the file's own phrasing.

Second, smaller point: `bad` is mislabelled. The scan `break`s at :379 after the first violating
`(lo, hi)` pair for a source, so it counts SOURCES with at least one violation, not violations.

**Remedy.** Refuse the write when `bad > 0`, in the same shape as the groundings refusal, and
name the violating sources (Hard Rule 0 — a count without the roster is not actionable). Rename
the printed label to "sources whose lower group is split across two higher ones". Give the
nesting verdict its own variable so the write verdict cannot shadow it.

---

### F9 — INFO — a hardcoded percentile printed beside a live count

`src/tiers.py:387`:

    print(f"   (99.5th percentile of all {len(w):,} links is 365 — these are not statistical)")

`len(w)` is measured from this run. `365` is a figure from the docstring's original measurement
(`src/tiers.py:55`) and is not recomputed. The two sit in one sentence, so a reader takes both
for this run's numbers, and `DELIBERATE_JOIN = 2000.0` (:122) — the threshold the whole
"artificial join" claim rests on — is justified by that 365 in the docstring at :50-59.

**Remedy.** Compute the percentile from `w` at print time, or attribute the constant ("365 as
measured on the 3,638-link graph of 2026-08-xx").

---

### F10 — MINOR — `designations()` caches under a signature that means "this pass was not clean", where its sibling refuses to

`src/weave_index.py:111-112`:

    sig = _records_sig()[1] if cacheable else None
    if cacheable and _DESIGNATIONS is not None and _DESIGNATIONS[0] == sig:
        return _DESIGNATIONS[1]

and `src/weave_index.py:144-145`:

    if cacheable:
        _DESIGNATIONS = (sig, out)

There is no `sig is not None` test on either side. `_records_sig` returns `sig=None` precisely
when a record file could not be stat'd mid-enumeration — `src/weave_index.py:271`,
`val = (files, None if unstattable else (len(files), newest))` — which is exactly the case where
the file list, and therefore the designation set computed from it, may be short.

`load_records()` guards this correctly at `src/weave_index.py:289`:

    if sig is not None and sig == _REC_CACHE["sig"]:

and its own docstring explains the asymmetry it is preserving: "The None only suppresses the
cache, which is what it was always for." In `designations()` the None does not suppress the
cache; it becomes a cache key that a later unclean pass matches.

The cost is already priced in this very function. Order 75307186e12a's fix at
`src/weave_index.py:119-133` covers the neighbouring case (do not cache a LOAD FAILURE) and says
what a short designation set does: "With no designations '(Earth-616)' reads as a gloss rather
than a continuity and Earth-616 Thor folds onto Earth-1610 Thor, which the header above prices
as the expensive direction: merging INVENTS a composite being and fuses two universes' evidence
into one worksheet." The unstattable path reaches the same place by a different door.

**Remedy.** Add `sig is not None` to both the hit test at :112 and the store at :144, matching
`load_records`.

---

### F11 — INFO — `_records_sig(fresh=...)` has no caller

`src/weave_index.py:195`, `def _records_sig(fresh=False)`. Verified by grep: the only call sites
anywhere in `src/` are `weave_index.py:111` and `weave_index.py:288`, both bare. Nothing passes
`fresh=True`.

The parameter is documented at :211 as the memo bypass ("`fresh=True` bypasses it"), so the
docstring promises an escape hatch that is not wired to anything. **Remedy.** Either use it where
per-call freshness genuinely matters or delete it and the sentence promising it.

---

### F12 — INFO — three conditions in `genre.classify_source` that can no longer be false

All three are consequences of `classify_text`'s `top` default having been correctly changed to
`None` (order bc0b85ea353b). `scores[g] += w * len(...)` at `src/genre.py:170` creates a Counter
key for EVERY genre whether or not it matched, so `most_common(None)` always returns the whole
field.

Measured: `classify_text("")` returns 11 entries, all zero; `len(GENRES) == 11`.

* `src/genre.py:216` — `if not ranked or ranked[0][1] == 0:` — the `not ranked` disjunct can
  never be true.
* `src/genre.py:221` — `total = sum(s for _, s in ranked) or 1` — the `or 1` is unreachable:
  :216 has already returned when the top score is zero and no cue weight is negative, so the sum
  is always positive here.
* `src/genre.py:219` and `:233` — `"genres_scored": len(ranked)` is invariantly `len(GENRES)`.
  The comment at :232 tells the reader this field exists "so a reader can tell at a glance that
  the margin was taken over the full field" — but the value carries no per-record information
  and cannot distinguish one record from another.

None of these is a wrong answer; they are dead disjuncts in the module that was rewritten to
stop truncating the field, in a codebase whose Hard Rule -1 says "a check that cannot fail looks
exactly like a check that passed".

**Remedy.** Drop the `not ranked` disjunct and the `or 1`. For `genres_scored`, either drop it
or change it to count the genres that actually scored above zero — which IS a per-record fact —
and rename it so the two readings cannot be confused.

---

### F13 — INFO — two disagreeing retention bounds on the dashboard's movement history

`src/dashboard.py:424-425`:

    cutoff = time.time() - 24 * 3600
    hist = [h for h in hist if h.get("at", 0) > cutoff][-2000:]

The page polls every 5 s (`src/dashboard.py:999`, `setInterval(tick,5000)`) and `movement()`
runs on every `/api/state` request, so a browser left open for 24 h produces 17,280 samples and
the `[-2000:]` cap — not the 24 h cutoff — is what binds, giving roughly 2.8 h of history.

Measured on `state/dashboard_history.json` today: 231 samples spanning 23.98 h, so the 24 h
cutoff IS the binding bound in current practice, because the page is not left open continuously.
Both readings are therefore defensible depending on usage, which is why this is INFO and not
higher.

What is not defensible is that the reasoning written into the module assumes only one of them.
The comment at `src/dashboard.py:446-447` justifies not gating the history write on this: "once
the 24h cutoff empties the frozen rows it reports a zero-length window rather than a false clean
bill." Under a continuously-open page the 2000-sample cap empties them roughly eight times
sooner, and that argument is about a window the code may not have.

**Remedy.** Make the two bounds agree, or state in the comment which one binds under which usage
and check that the stall detector's conclusion holds in both.

---

### F14 — MINOR — a standards read failure renders on the dashboard as a benign counter reset

`src/dashboard.py:389`:

    "standards met": sum(1 for x in (now_state.get("standards") or []) if x.get("holds")),

Every other key in that dict can be `None` and is then dropped from the sample by the filter at
:391 (`{k: v for k, v in keys.items() if v is not None}`). This one always yields an int.

`state()` at `src/dashboard.py:639-644` sets `s["standards"] = []` on any exception out of
`standards.check`. So an unreadable/failed standards pass records `standards met: 0`.

Against the previous sample's real count that is a negative delta, and :481-483 then does:

    reset = delta is not None and delta < 0
    if reset:
        delta = None

`reset` was introduced (comment at :468-480) for a benign cause — "read.py's `done['chunks']` is
an in-process counter reset to zero on every launch". A standards subsystem failure is not that,
and it lands under the same label. The same comment says a restart "READS AS MOVEMENT, which is
precisely the 'every counter flat while every job is up' condition the `the library's counters
are moving` standard exists to catch" — this path routes a real fault into that same blind spot.

**Remedy.** Carry `None` for `standards met` when `now_state["standards"]` is missing or empty,
so the existing `if v is not None` filter drops the row the way it does for every sibling metric.
Distinguishing "unmeasured" from "zero" is the module's own stated rule at :57-60 and :91-99.

---

### F15 — MINOR — three silent name truncations in the Registry Terminal, beside one that is done correctly

All in `src/build_terminal.py`'s embedded SVG renderer:

* `:245` — `esc((root.node.name||rootKey).slice(0,24))` — the nucleus title, cut mid-word at 24.
* `:295` — `const nm=(p.node.name||k).slice(0,22);` — shell-2 ring labels.
* `:351` and `:356` — `(w.cat||w.d.split("::").pop()||"").slice(0,22)` — world labels, in both
  the `wn` measurement array and the drawn label.

None carries an ellipsis or any marker. `:326` in the same function does it correctly:
`ss.map(n=>n.length>18?n.slice(0,17)+"…":n)`, and the file already carries a Hard Rule 0
correction at `:56-58` that removed a slice-to-8 from the shelved-here roster ("it used to be
sliced to 8, which hid 30 of node 6.6.6's 38 sources behind no indication at all").

Mitigating, and it is why this is MINOR not MAJOR: the untruncated string is in the `<title>`
tooltip beside each of the three, and the aside panel prints names in full. So nothing is
unreachable — it is a cut that does not announce itself.

**Remedy.** Use the `+"…"` form from :326 at all three sites. At :351/:356 compute the display
string once rather than twice with the same slice.

---

### F16 — MAJOR — `sweep_plan.batches()` is not stable across a run, and the coverage ledger inherits it

Not one of this batch's eight modules. It is a defect this batch hit directly, in the machinery
that assigns the batches, and it can make any run39 agent record coverage for modules nobody
opened.

`modules()` at `src/sweep_plan.py:69-99` reads the LIVE line count of every file under `src/` and
sorts by `-lines`. `batches()` at `:102-115` then greedy-packs longest-first into n bins. So any
edit anywhere in `src/` that changes a line count can reorder the sort and cascade through every
bin placed after the changed file.

Measured. `batches(16)[14]["modules"]` returned, at the start of this batch:

    hostcheck.py  dashboard.py  build_terminal.py  weave_index.py
    tiers.py      genre.py      resonance.py       halo.py

and about twenty minutes later:

    hostcheck.py  dashboard.py  build_terminal.py  estate.py
    canon_backup.py  navtree.py  scope.py  cosmology_graph.py

Three in common, five different. Cause confirmed: eight `src/` files were written during that
window by the concurrent maintenance shift — and their sizes are the point:

    drill.py        7,602 lines     5.0 min before the second call
    workorders.py   1,405           6.8
    local_agent.py  1,212          24.2
    publish.py      1,534          26.6
    verify_math.py  7,947          28.4
    allsweep.py       850          35.7
    escalation.py     820          35.8
    mutate.py       1,772          40.4

`verify_math.py` and `drill.py` are the two largest files in the tree, so they are the first two
items the greedy packer places — a change in either shifts everything after them.

**The harm is to the coverage ledger, not only to the plan.** An agent that reads its first list,
audits those modules, and then records `batches(16)[14]` at the end stamps run coverage on five
modules it never opened, and leaves the five it DID read stamped as the previous run. `missing()`
then reports a clean sweep over a real gap. Both lists are well-formed, plausible, and the same
length, so nothing looks wrong. That is Hard Rule -1's "a check that cannot fail looks exactly
like a check that passed" applied to the audit's own bookkeeping.

**What this batch did.** It committed exactly that error at `at: 1788148985` and then corrected
it. The shard `state/sweep_shards/run39.15.38772.json` was rewritten in place — atomically, via
`silence.write_json` — to the eight modules actually read, carrying a `corrected` field recording
why. Verified afterwards through `sweep_plan._read_shards()`: the eight read are stamped run39,
and `estate.py`, `canon_backup.py`, `navtree.py`, `scope.py`, `cosmology_graph.py` are back at
run38, so the gap is honest again. No file under `src/` was touched.

**Other run39 batches may have made the same mistake without noticing.** Their shards should be
checked against what their audit `.md` files actually discuss before run39 is called complete — a
batch that recorded a list it did not read leaves no other trace.

**Remedy.** FREEZE THE PLAN: compute `batches()` once at run start, write it to
`state/sweep_plan.<run>.json`, and have every agent read its batch from that file rather than
recompute it. `record()` should then take the frozen batch id and derive the module list itself,
so an agent cannot record a list that differs from the one it was handed. Cheaper interim guard:
have `record(run, covered, batch=...)` compare `covered` against the frozen plan's batch and
REFUSE — fail closed — on a mismatch. Do NOT fix this by making `modules()` ignore line counts;
the longest-first packing is load-bearing and its reason is stated at `src/sweep_plan.py:103-107`.

---

## NOT FINDINGS — verified and cleared, recorded so the next sweep does not re-open them

* **`halo.py --full` cannot KeyError.** `:191-192` iterates `A.WEIGHTS` and indexes
  `rec["axes"][ax]`. Verified by running against the live modules: `assay.WEIGHTS` holds exactly
  eleven axes (acumen, celerity, continuity, discernment, reach, ruin, suasion, sustain,
  transgression, vector, volition) and all three ROSTER entries carry exactly those eleven, with
  no extras and none missing. The write verdict is gated and reaches the exit code (`:207-215`).
  Nothing to file against this module.

* **`resonance._isolated` is a check that can never fire, and that is deliberate and stated.**
  `src/resonance.py:157-163`. Verified: `nodes` is built from the edge keys at :129 and `nbrs`
  is appended for BOTH endpoints of every edge at :144-146, so every member of `nodes`
  necessarily has a neighbour. Its own comment at :148-156 says exactly this, names the
  measurement ("Verified across three edge sets"), and keeps it on purpose: "if the construction
  above ever changes, the alternative to this line is a ZeroDivisionError from inside the sweep
  with no name on it." Correctly handled; not filed.

* **`resonance`'s dead functions are already on file.** Grep confirms the module docstring's
  claim at :40-73 is still exactly true: `resonance_strength` has zero callers anywhere;
  `hodge_decompose` is called only from `drill.py:7330-7377`; `incomparability_rate` only from
  `verify_math.py:7634-7644`; `dominates` only from `incomparability_rate`. This is declared in
  the module's own docstring and left as an OPEN order (order f467f662be4b) with the wiring named
  as an `anchors.py` change. Not re-filed.

* **The `read.py` fabrication guard is genuinely fixed on both sides.** `dashboard.py:250` now
  carries `"dropped": _num(r["dropped"])` into the job dict, and `standards.py:1116` reads
  `read.get("dropped")` — not the `read.get("raw")` key that never existed. Both halves verified
  in the current source; the comment at `dashboard.py:236-249` describing the old defect is
  accurate history, not a stale claim.

* **`drill_last.json` really carries `ceiling`.** `dashboard.safety()` at `:610-613` maps
  `d.get("ceiling")` to `liveness_ceiling`, and the dashboard's "checks that cannot fail" row
  compares against it. Verified that `drill.py:7492` writes `"ceiling": LIVENESS_CEILING`
  alongside `"liveness": _lv`, so that indicator can actually go red. Not a can't-fail guard.

* **`hostcheck.probe`'s `PROBE = 40` is not a Hard Rule 0 truncation.** `src/hostcheck.py:243`,
  `names = [...][:PROBE]`. It is a statistical sample for a hypothesis test, not a listing, its
  denominator is published in the result (`"probed": len(names)`) and printed on every line as
  `hits/probed`, and the constant carries its own reason at :198 ("One API call takes 50; forty
  leaves room for redirects"). Ranking-then-truncating a roster is the banned act; sampling with
  a stated n is not. Recorded so it is not re-filed each sweep.

## QUESTIONS — two defensible readings, not filed as findings

* **`score(host, names, source, by=None)` with `by=None` judges on the raw rate.**
  `src/hostcheck.py:666`: `base = null_rate(...) if by else 0.0`, so with no corpus the baseline
  is 0.0 and `lift == rate`. Every caller in `src/` passes `by` (sweep :720, repair :776,
  adopt :1216, and `hosts.py:150`'s use goes through `adopt`), so this is unreachable today.
  Two readings: (a) it is a latent trap in a public function whose whole docstring is a sustained
  argument that the raw rate must not decide, and the honest default is `None` propagating to
  `UNREACHABLE — no baseline`; (b) it is a deliberate degenerate mode for a caller with no
  corpus, and changing it would make `score` unusable standalone. I could not resolve which was
  intended from the source, so it is a question and not a finding.

* **`sweep()` names no unassigned sources.** `src/hostcheck.py:711-714` prints
  "(N sources carry no host at all and are not probed)" as a bare count. Hard Rule 0's usual
  reading wants the roster. But `adopt()` is the instrument built for exactly that population and
  names every one of them (`:1230-1236`), so the count here is a pointer rather than a
  truncation. Left as a question.

## Trivia noted, not filed

* `src/tiers.py:332` — `_g, readable = _load_groundings()`; `_g` is never used (the map is
  re-read inside `chart()`, deliberately, per the comment at :405-407). Harmless.
* `src/tiers.py:257` — `chart()`'s docstring says "Returns per-source dicts"; it returns
  `(out, tiers, multi)`.
* `src/dashboard.py:535` — `round(pct(secs, 0.5) or 0, 1)` renders "no latency data" and "0.0 s"
  identically as `0`. Cosmetic on a metrics panel.
