# AUDIT — batch 13, run29

Modules: `overwatch.py`, `handbuilt.py`, `custodes.py`, `backfill.py`, `sweep.py`,
`thread_integrity.py`, `scope.py`. All read in full. Every module was read line-by-line;
findings below are only what survives the seven lenses. Where I could reproduce a claim against
real repo data with the miniconda python, I did — those are marked REPRODUCED.

Known items (per assignment, not re-derived, not re-listed per-lens below):
- `overwatch.py:652` dedups by fingerprint key existence, so a retired finding can never reopen.
- `foreman._retire()` is a second writer into overwatch's ledger (foreman.py not in this batch).

---

## sweep.py — TOP FINDING OF THE BATCH

### 1. [HIGH] The funnel's "strictly smaller set" claim is false; the printed drop numbers are
   wrong, and one of them renders as a garbled double-negative. **REPRODUCED.**

`sweep.py:20-22` (module docstring): "Each stage is a strictly smaller set than the one above,
and the size of each drop is the real statement of where the project stands." `report()` (lines
167-189) computes `drop = prev - f[k]` for each successive funnel stage and prints
`f"   -{drop:,}"`.

The bug: `catalogued` (line 146, `row["catalogued"] = bool(e.get("catalogued"))`) is a genuine
**per-entry** flag set by phase-2 review. `addressed`/`shelfmark` and `reachable`/`host` (lines
134-149) are **per-SOURCE** properties computed once outside the entry loop and stamped onto
every entry of that source regardless of whether that entry has been catalogued. Nothing in the
code makes "addressed" a subset of "catalogued" — they are orthogonal booleans at different
granularities, despite the funnel treating them as strictly nested.

Reproduced against the live repo (`data/records/*.json`, `data/NAVTREE.json`,
`data/HOSTS.json` via miniconda python, 49,532 Person entries):

```
n 49532  catalogued 32303  addressed 49456  reachable 49449
addressed but NOT reachable: 82
reachable but NOT addressed: 75
catalogued but NOT addressed: 76
addressed but NOT catalogued: 17229
```

17,229 of 49,532 Person entries (35%) are counted as "addressed" despite never having been
catalogued — flatly contradicting "strictly smaller set." Running `report()`'s exact
line-formatting code against these real counts produces:

```
  catalogued     32,303   65.2%  ########################   -17,229
  addressed      49,456   99.8%  #####################################   --17,153
  reachable      49,449   99.8%  #####################################   -7
```

Two distinct consequences:
- The "size of each drop" the docstring calls "the real statement of where the project stands"
  is actively wrong for the catalogued→addressed step: it reports a drop of -17,229 (a loss)
  when what really happened is 17,229 *entries were gained* into the "addressed" bucket that
  were never in "catalogued" to begin with, netted against a much larger true loss. The number
  on screen does not describe any real population of entries.
- `f"-{drop:,}"` has no handling for a negative `drop`. With `drop = 32303 - 49456 = -17153`,
  the formatted string is literally `--17,153` — a garbled double-negative on the actual output
  of `sweep.py` today, visible to anyone running it.

Consequence: the funnel is the project's own instrument for answering "what fraction of
characters clears each stage" (docstring line 8-10). It is currently printing an impossible
99.8% "addressed" rate immediately after a 65.2% "catalogued" rate with a nonsensical negative
gap between them, which undersells exactly the stage (catalogued→addressed) the whole file
exists to make legible.

Fix direction (not applied — audit only): either gate every later stage on `catalogued` first
(so the funnel is genuinely nested), or stop presenting `addressed`/`reachable`/`read` as later,
narrower funnel stages under `catalogued` and report them as the independent per-source axis
they actually are, and guard the drop formatting against a negative value.

### 2. [LOW] `report()`'s per-list previews are DISPLAY truncation, not data loss — noted, not a
   finding. `best = sorted(...)[:top]` (line 206, default `top=18`), `gap.most_common(10)` (215),
   `bysrc.most_common(8)` (222) only affect what's printed to the terminal; the full `rows` list
   written to `data/CHARACTER_SWEEP.json` via `silence.write_json(OUT, rows, ...)` (line 240) is
   never truncated. Correctly labelled to itself as a preview in each case. No HARD RULE 0
   violation.

### Everything else in sweep.py: no further findings.
`load()`'s FileNotFoundError-as-expected-path handling (lines 63-91) is a deliberate, well
-reasoned exception to "swallowed failures" — it distinguishes an absent evidence cache
(the overwhelming, expected majority) from a genuinely corrupt one, which it still routes to
`silence.note`. The two-writer contract is respected: sweep.py only reads records via
`pipeline.records()` and writes its own derived artifact via `silence.write_json`, never
touching a record file directly. `main()`'s guard on `silence.write_json`'s return value
(lines 240-243) correctly refuses to claim success when the replace didn't land.

---

## thread_integrity.py

### 1. [MEDIUM] `classify()`'s DANGLING test requires *every* shared entity key in a pair to have
   drifted before it fires; a pair that lost all but one of its shared keys is silently folded
   into the healthy bucket with a stale, un-adjusted count. **REPRODUCED.**

`thread_integrity.py:108-113`:
```python
if ents is not None:
    gone = [k for k in shared if k not in ents.get(a, ()) or k not in ents.get(b, ())]
    if gone and len(gone) == len(shared):
        out["DANGLING"] += 1
        ...
        continue
```

The module's own docstring defines DANGLING as "points at nothing that exists" (line 32), and
the inline comment at `classify()`'s docstring (lines 96-97) says "DANGLING is computed for
real, against the live records: a candidate key whose source no longer holds that entity (weave
drift)" — phrased per-key. The code instead requires **all** of a pair's shared keys to have
drifted (`len(gone) == len(shared)`) before the pair is marked DANGLING at all. Any pair that
lost some but not all of its shared entities falls through to `IMPLIED-UNRECORDED` (the current
live branch, since `main()` never passes `recorded=`) carrying `len(shared)` — the ORIGINAL,
pre-drift count, not the number of keys that actually still exist on both sides.

Reproduced with a minimal driver (`import thread_integrity as T`): a pair sharing 5 candidate
keys where source A has since lost 4 of the 5 from its live entity set:

```python
pairs = {('A','B'): {'k1','k2','k3','k4','k5'}, ('B','A'): {'k1','k2','k3','k4','k5'}}
ents = {'A': {'k5'}, 'B': {'k1','k2','k3','k4','k5'}}   # A only still holds k5
T.classify(pairs, None, 300.0, ents=ents)
# -> counts: {'IMPLIED-UNRECORDED': 1}
# -> detail: {'IMPLIED-UNRECORDED': [('A', 'B', 5)]}
```

80% of the evidentiary basis for that thread obligation is gone (4 of 5 keys no longer exist in
A's records), yet the pair is reported as a healthy 5-shared-entity implied thread, not flagged
as any degree dangling, and the printed "5" is simply false — only 1 shared key still verifiably
exists on both ends.

Consequence: `main()`'s DANGLING count (and detail list) systematically understates weave drift,
and the `IMPLIED-UNRECORDED` "shared" counts it prints instead (`detail["IMPLIED-UNRECORDED"]`,
used at line 116 and in the loop at 174-175/179-180 for RECIPROCAL/ASYMMETRIC-SUSPECT once
`recorded` is supplied) are inflated for any partially-drifted pair.

### Everything else in thread_integrity.py: no further findings.
The RECIPROCAL / ASYMMETRIC-LAWFUL / ASYMMETRIC-SUSPECT branches (lines 118-134) are
unreachable from `main()` today because `recorded` is never supplied — this is honestly
documented in the `classify()` docstring and in `main()`'s own printed banner ("no directed
thread graph exists yet -- Hard Rule 5"), not a bug. `load_entities()` correctly reads every
`data/records/*.json` file with no cap. No two-writer violations (the module never writes
records; it has no `data/` writer at all).

---

## custodes.py

### 1. [MEDIUM] `_ATT_BASE`'s "DERIVED... moves automatically if the charter revises a grade"
   claim is false: the table is a hand-copied literal from a piece of DEAD code in `assay.py`,
   numerically unrelated to the live attestation table `assay()` actually uses. **REPRODUCED.**

`custodes.py:221-234`:
```python
# DERIVED from assay()'s own attestation table rather than restated. A second hand-written table
# of evidence quality would be a duplicate mechanism for a quantity the charter has already fixed
# -- the same error as the withdrawn tempo table (X.10 §4), and it would drift the moment either
# copy was edited. ...
#     quality(g) = 1 - base(g) / max(base)
# Monotone by construction, and it moves automatically if the charter revises a grade.
_ATT_BASE = {"Witnessed": 0.10, "Instrumented": 0.08, "Transcribed": 0.20,
             "Reconstructed": 0.40, "Disputed": 0.55}
```

This dict has no import linkage to `assay.py` at all — it is a plain literal. `assay.py`'s
**live** attestation table, the one `A.assay()` (called by `custodes._custos_reading` at line
240) actually uses to compute the interval, is `SIGMA_BY_ATTESTATION` (`assay.py:308-316`),
built from `_RAW_SIGMA = {"Instrumented": 2.70, "Witnessed": 4.08, "Transcribed": 5.30,
"Reconstructed": 7.00, "Disputed": 8.50}`, rescaled by `SIGMA_MAX / max(...)`. The values in
`custodes._ATT_BASE` (0.10/0.08/0.20/0.40/0.55) are instead byte-identical to a **local literal
inside `assay.interval_from_hands()`** (`assay.py:630-631`), a function I confirmed by repo-wide
grep is **called from nowhere in this codebase** — dead code.

Reproduced (miniconda python, `import assay as A, custodes as C`):
```
assay.py live SIGMA_BY_ATTESTATION (used by assay()):
  {'Instrumented': 0.9078, 'Witnessed': 1.3718, 'Transcribed': 1.782, 'Reconstructed': 2.3536,
   'Disputed': 2.8579}
custodes.py _ATT_BASE:
  {'Witnessed': 0.1, 'Instrumented': 0.08, 'Transcribed': 0.2, 'Reconstructed': 0.4,
   'Disputed': 0.55}
custodes._ATT_BASE == the dead interval_from_hands() floor dict?  True
custodes._ATT_BASE == the live table assay() actually uses?       False
```

So: (a) `custodes.py` did not "derive" anything — it independently hardcoded a second copy of
numbers that live in a different, unused function; (b) if the charter's live attestation grades
in `assay.py` are ever revised (the surrounding comment there says they were "CALIBRATED AGAINST
THE CHARTER'S OWN PUBLISHED BARS," i.e. a plausible future edit target), `custodes.ATTESTATION_QUALITY`
will **not** move — directly contradicting "it moves automatically if the charter revises a
grade." This is exactly the duplicate-mechanism drift risk the comment claims to have avoided.

Consequence is bounded but real: `ATTESTATION_QUALITY` only feeds `q` in `_custos_reading`
(line 254), which sets how much of each Custos's `tilt` is "evidential" vs. "prior" (lines
255-259) — it does not affect `assay()`'s own `decimal`/`interval` (confirmed by reading:
`assay()`'s `decimal` composite is attestation-independent; only `interval` uses attestation,
via `SIGMA_BY_ATTESTATION`). So the College's `prior_divergence_share` / `attestation_floor_share`
split in `convene()` is computed against a quality scale that is silently disconnected from the
one the rest of the pipeline actually measures uncertainty against.

### 2. [LOW] `dof_coverage()`'s "one_to_one" check is a static self-consistency assertion
   between two hardcoded dicts in the same file, not a check against any external or computed
   fact. VERIFIED-BY-READING, not flagged as a lens-4 "cannot fail" defect in the deceptive
   sense — it will genuinely go False if someone edits `CUSTODES` or `DEGREES_OF_FREEDOM`
   out of sync — but worth noting it is not evidence that the *mechanisms* behind each DOF are
   real, only that the labels match. In particular "Lumen" (`dof="currency"`) has `tilt=0.0,
   evidence_sensitivity=0.0` (line 204) — his individual reading contributes nothing
   currency-specific; the actual currency/staleness effect (`staleness_widening()`, called from
   `convene()` at lines 282-287 and 322-323) is a flat term added to `half` from `distance`/
   `years_since` directly, completely independent of whether Lumen exists in `CUSTODES` at all.
   Removing Lumen from the college would not remove the currency mechanism, and Lumen's presence
   does not implement it — `dof_coverage()`'s "manned" check cannot see this because it only
   compares label strings.

### 3. [LOW, self-documented] `convene()`'s `"covers_every_reading"` field
   (`custodes.py:344`) is a tautology by construction — `half` is defined a few lines above as
   `max(1.96 * total_sd, max(abs(v - consensus) for v in vals))` and only ever widened
   afterward, so the check can never be False for any input. This matches lens 4 exactly, but
   the code's own comment (lines 335-343) already says so explicitly ("this is a GUARANTEE being
   published, not a check being run... it must not be mistaken for verification") and proposes
   the genuinely informative version as a `NEXT_STEPS` item. Reported for completeness per the
   audit brief, not as an undiscovered defect.

### Everything else in custodes.py: no further findings.
The Lumen tilt-zero erratum (lines 199-208) is itself a documented, already-applied fix, not a
bug. The private-weight-table fix (`w = {k: v * emph.get(k, 1.0) ...}`, lines 244-252) correctly
avoids mutating the shared `A.WEIGHTS` global.

---

## scope.py

### 1. [MEDIUM] `scope_for()` samples at most 8 pages (via `srlimit=3` across 4 fixed queries)
   to determine the Magnitude **ceiling** written to `data/SCOPE.json`, which `magnitude.py`
   reads to cap what Magnitude every character of that source can be assayed at.
   VERIFIED-BY-READING; downstream consumption confirmed by grep.

`scope.py:68-99`:
```python
QUERIES = ["cosmology universe world setting", "multiverse", "universe", "world"]
...
def scope_for(host, verbose=False):
    titles, seen = [], set()
    for q in QUERIES:
        d = F.api(host, {"action": "query", "list": "search", "srlimit": "3", "srsearch": q})
        ...
    pages = F.fetch(host, titles[:8])
```

`srlimit` is one of the literal smells this audit was told to hunt for, and `titles[:8]` caps
the accumulated, deduplicated title list a second time regardless of how many distinct titles
the four searches turned up. The tier counts that decide a whole fiction's ceiling (`TIERS`,
lines 52-61, e.g. `"multiverse"` → `M8`) are computed only over the text of those ≤8 pages
(`text = " ".join(F.strip_wikitext(v) for v in pages.values())`, line 82). If the real
multiverse/cosmology discussion for a wiki lives on pages the four fixed queries don't surface
in their respective top 3 hits, the fiction is silently scoped to whatever lower tier the sampled
pages happen to mention ≥`MIN_MENTIONS` (10) times.

This is DATA truncation, not display: confirmed by grep that `magnitude.py` imports `scope as
SCOPE` and calls `SCOPE.scope_for(host)` / reads `data/SCOPE.json` directly (`magnitude.py:870,
940-959`) to gate the Magnitude ceiling assigned to entities of that source — so an under-sampled
scope determination for one host constrains the assayed Magnitude of every character from every
source on that host, permanently, until `scope.py --build` is re-run and happens to sample
differently (unlikely, since the queries and `srlimit` are fixed and MediaWiki search is
largely deterministic for a stable corpus).

The tier-selection logic itself (pick the *highest* tier clearing the floor, not the most
frequent — lines 85-93) is correct and does what its comment claims; the defect is specifically
in how narrow the page sample feeding that logic is.

### Everything else in scope.py: no further findings.
`build()`'s incremental cache (`out = json.load(...)`, only processing hosts `not in out`) is a
legitimate resumability feature, not a truncation — every host not yet scoped is still queued
with no cap (`todo = sorted({...})`, no `[:N]`). Writes go through `silence.write_json`. See the
concurrency note below for a related but distinct issue with this same read-modify-write.

### 2. [LOW-MEDIUM] `build()` is an unlocked read-modify-write on shared `data/SCOPE.json` with
   no merge-on-save, unlike the ledger pattern `overwatch.py` was hardened to use (m40).
   VERIFIED-BY-READING.

`scope.py:102-120`:
```python
def build(records, hosts):
    out = {}
    if os.path.exists(OUT):
        out = json.load(open(OUT, encoding="utf-8"))
    todo = sorted({h for s, h in hosts.items() if h and h not in out
                   and not F.is_wikipedia(h)})
    for i, h in enumerate(todo, 1):
        ...
        out[h] = sc
        ...
    silence.write_json(OUT, out, indent=1, ensure_ascii=False)
    return out
```

`out` is read once at the top, mutated in memory across a `todo` loop that makes live network
calls per host (so a full `--build` run can take a long time), then written once at the end as a
whole-file replace via `silence.write_json`. If a second `scope.py --build` (or any other writer
of `data/SCOPE.json`) runs concurrently and finishes first, the first process's final write —
built from its stale in-memory snapshot — silently drops every host the second process added in
between, exactly the failure mode `overwatch.py`'s own `_merge_ledgers`/`_reconcile_with_disk`
(m40) was written to prevent for `data/OVERWATCH.json`. `scope.py` has no equivalent
reconciliation. Given `--build` is normally run ad hoc rather than as a standing loop, the
window is narrower than overwatch's, but the hazard is the same shape and currently unguarded.

---

## backfill.py

No new findings. This module is thoroughly hardened already, with multiple documented and
fixed historical bugs recorded in its own comments (`RosterIncomplete` distinguishing a
transport failure from an empty roster; the `absent`-before-cap fix; the switch from
`write_record` to `write_record_catalogue` to stop backfilled characters being dropped by the
two-writer merge). Checked specifically and found clean:
- `roster()` has no cap on the real run path (`backfill_source` calls `roster(host)` with no
  `limit`); the `--cap` CLI flag is explicit, opt-in, documented as "omit for everything, which
  is the intended use," and only affects the ranked-by-size `missing` list, never the roster
  enumeration itself. Category-listing pagination via `cmcontinue` is walked to completion.
- Two-writer contract respected: writes only via `P.write_record_catalogue` (the cast-growing
  side), gated on its return value.
- `lead()`'s 420-character description cap is the module's stated, deliberate scope ("a name and
  the opening sentences... and nothing else," per the module docstring) rather than a listing
  truncation — not a Hard Rule 0 violation.
- Minor, not flagged as a finding: `main()`'s `--all` path catches `Exception` per source and
  continues; the explicit `--source` path does not, so one bad source aborts the whole run there.
  Inconsistent, but arguably intentional (an explicitly-named source failing should be loud), and
  low-stakes enough that I'm noting rather than filing it.

---

## handbuilt.py

No findings. This is a curated, static per-entity assay dataset (`ROSTER`, ~10 entries) plus a
`compute()`/`main()` that renders it — there is no scan, crawl, or listing to truncate, and the
one print-time truncation (`d["cited"][:58]` at line 481, under `--full`) is plainly a terminal
display convenience, not a data write. Spot-checked the ROSTER data against its own claims (e.g.
Zalama's comment claiming "this one scores five [axes]" against the actual tuple contents — axes
that are numeric vs. `"unestimable"` — and it is accurate: reach, transgression, sustain, acumen,
suasion are numeric; the other six are `"unestimable"`). The write-before-print ordering fix
(`OUT` written before any console output, lines 444-465) is correctly implemented and matches
its own comment. Tuple-unpacking order (`score, cited_text, provenance`) is consistent across
all ten ROSTER entries and matches how `compute()` reads `v[0]`/`v[1]`/`v[2]`.

---

## overwatch.py

No new findings beyond the two items already given as known (`:652` dedup-by-key-existence,
and `foreman._retire()` as a second ledger writer, foreman.py out of this batch's scope). Read
in full and specifically checked:
- `_LOCAL_BUSY` reset at the top of `round_once()` (line 600) is a real, already-applied fix for
  a documented prior bug (the budget used to be lifetime-not-per-round in `--loop` mode);
  confirmed the reset actually executes before any `_ask()` calls in the same round.
- `write_report()`'s open-findings listing is capped at `[:40]` (line 573) and the structure
  section's `broken[:4]` / `corrupt[:3]` (lines 554, 561) — all three are DISPLAY truncation of
  `WATCH.md` only; the header line above them (`f"**{len(open_f)} open** ({len(hi)} high)"`,
  line 570) reports the true, untruncated count, and the full findings persist untruncated in
  `data/OVERWATCH.json` via `save()`. Not a HARD RULE 0 violation.
- `_merge_ledgers()` / `_reconcile_with_disk()` (the m40 fix): re-read carefully, the per-key
  merge rules (findings by `_progress` rank, seen by later `at`, rounds by max, last_run by max
  string) are each genuinely monotone as claimed, and I did not find a case where re-applying the
  merge twice changes the result. No new bug found here.
- `verify_open()`'s auto-triage only ever moves a finding from `open` to `closed`
  (on `"refuted"`) or leaves it `open` with a `confirmed_n` bump; it never sets `state` to the
  `"confirmed"` value that exists in `_STATE_RANK` (line 225) — that rank value looks currently
  unreachable in practice (no code path assigns `f["state"] = "confirmed"`), which is harmless
  (the rank still resolves ties correctly for the states that do occur) but is worth a note in
  case a future change assumes `"confirmed"` is a live state.

---

## Summary table (severity-ordered)

| Severity | Module:line | Claim | Status |
|---|---|---|---|
| HIGH | sweep.py:167-189 (report) | funnel stages are strictly nested / drop is meaningful | REPRODUCED |
| MEDIUM | thread_integrity.py:108-113 (classify) | DANGLING catches any drifted shared entity | REPRODUCED |
| MEDIUM | custodes.py:221-234 (_ATT_BASE) | quality table is derived from assay.py and auto-updates | REPRODUCED |
| MEDIUM | scope.py:68-99 (scope_for) | wiki-scope ceiling reflects the fiction's real scale | VERIFIED-BY-READING |
| LOW-MED | scope.py:102-120 (build) | SCOPE.json read-modify-write is race-safe | VERIFIED-BY-READING |
| LOW | custodes.py:360-366 (dof_coverage) | Lumen implements the currency degree of freedom | VERIFIED-BY-READING |
| LOW | custodes.py:344 (convene) | covers_every_reading is a live check | VERIFIED-BY-READING (self-documented in code) |
| — | backfill.py | — | clean |
| — | handbuilt.py | — | clean |
| — | overwatch.py | — | clean beyond known items |
