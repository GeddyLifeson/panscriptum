# Batch 03 Audit — run32

Modules read, every line: `standards.py` (1510 lines), `tiers.py` (360), `scout.py` (287),
`genre.py` (247), `descending_ladder.py` (186), `cosmology_graph.py` (159). Total 2749 lines.

---

## KNOWN LEADS — disposition

### 1. `standards.py:826-828` — vacuous green on empty `REFERENCE_ASSAYS.json`
**VERIFIED.**
```python
inside = 0
for v in refs.values(): ...            # 0 iterations if refs == {}
out.append(_s(
    "hand-built assays match the charter", inside >= len(refs) if refs else True,
    f"{inside}/{len(refs)}", ...))
```
If `refs` loads as `{}` (valid JSON, empty), `inside >= len(refs)` is `0 >= 0` but the code
doesn't even evaluate that — the `if refs else True` short-circuits straight to `True`. The row
reads "0/0" and HOLDS. Confirmed exactly as reported. Severity: BLOCKING (this is the
instrument-integrity standard for the library's one original scoring method, and it is HIGH
severity in `check()`).

### 2. Sibling standards with the "drop the row on exception" shape instead of UNMEASURED
**VERIFIED, and the count is materially larger than "~18 siblings, 3 fixed."** `check()` builds a
list of standard-rows across ~24 `try/except` blocks that read a JSON file or probe the machine.
Only a few were repaired to *always* emit (append even when the input can't be read); the rest
still have `out.append(...)` inside the `try` and nothing in the matching `except` — meaning an
unreadable/missing/corrupt input makes the whole standard **vanish from the page**, which is
worse than reporting UNMEASURED because a reader cannot tell "this held" from "this never ran."

**Confirmed GOOD shape (append unconditionally, or at least degrade to an explicit UNMEASURED
string) — 3, matching the "3 fixed" claim:**
- `sentences that survive the verbatim check` (~717-758) — genuinely unconditional; the `out.append`
  is *outside* any try/except.
- `the library's counters are moving` (~872-901) — comment states "It now always emits," and it
  does for the *short-history* case (`_enough` false → still appends `holds=True`,
  "not enough history yet").
- `every source is fully catalogued` (~934-969) — has explicit UNMEASURED handling for the
  "no denominator" (`wiki==0`) case.

**But all three of those "fixed" ones are still wrapped in an outer `try/except` that silently
drops the row on any OTHER exception** (file missing entirely, corrupt JSON, an unrelated
`AttributeError`) — e.g. `dashboard_history.json` absent makes `open()` raise before the
"always emits" logic is ever reached, at which point the *fixed* standard reverts to exactly the
bad shape it was fixed for. Same for `COMPLETENESS.json` totally missing (vs. present-but-empty,
which is handled). This is worth flagging on its own: the fix closed one failure mode (bad/empty
data) but not the other (unreadable file), on standards whose own commit messages claim it's
solved.

**Confirmed BAD shape — standard silently vanishes with no UNMEASURED row on ANY exception in
its `try` block, including plain file-not-found (20 standards found, listing name — file:line
of the `try:`/`except:` pair):**

| # | standard name | try at | except at |
|---|---|---|---|
| 1 | `the reader's gate is open` | 512 | 534-535 |
| 2 | `rosters that name their own fiction` | 760 | 783-784 |
| 3 | `shelfmarks are unique` | 786 | 798-799 |
| 4 | `hand-built assays match the charter` | 806 | 833-834 |
| 5 | `files that parse` | 905 | 930-931 |
| 6 | `verifiers all run` | 905 (same block) | 930-931 |
| 7 | `the full audit is recent` | 905 (same block) | 930-931 |
| 8 | `the character sweep is newer than the catalogue` | 981 | 998-999 |
| 9 | `every running job is advancing` | 1006 | 1075-1076 |
| 10 | `every pool failure is recognised` | 1090 | 1134-1135 |
| 11 | `fandom answers this machine` | 1148 | 1163-1164 |
| 12 | `disk space` | 1166 | 1173-1174 |
| 13 | `promotions have their spine codes amended` | 1182 | 1199-1200 (FileNotFoundError deliberately exempted at 1197-1198; every OTHER exception still drops the row) |
| 14 | `the local model has a live runner` | 1203 | 1230-1231 (also drops on `resident` falsy by design, undocumented as a standards-file convention) |
| 15 | `the local model produces tokens` | 1236 | 1249-1250 (also drops when `flow is None` by design) |
| 16 | `every managed job is running` | 1252 | 1277-1278 |
| 17 | `one instance of each job` | 1284 | 1309-1311 (`_dup = None`, then `if _dup: out.append`) |
| 18 | `the published panel is fresh` | 1315 | 1324-1325 |
| 19 | `model IDs their providers still serve` | 1328 | 1406-1407 (has UNMEASURED text for the *stale-snapshot* case, but a totally missing/corrupt `PROVIDER_MODELS.json` still drops the row via the outer except) |
| 20 | `every declared floor is measured` | 1415 | 1435-1436 (the self-check whose entire job is catching exactly this defect class can itself go silent) |

Severity: **MAJOR**, project-wide (this is the batch's single largest finding by volume). Item
#20 is the sharpest instance — the standard designed to catch "a floor nothing measures" can
itself disappear without a trace if its own regex/read fails, which is a textbook "checks that
cannot fail" mirror-image (here: a check that can vanish).

**Related, separate bug — vacuous green (not row-drop) on unreadable ledger, same file:**
`standards.py:638-661`. `ledger = {}` is set before the try; on `state/failures.json` being
missing/corrupt, `ledger` stays `{}`, and the code falls through (this block, unlike the ones
above, has the `out.append` calls *outside* the try) to compute `real = sum({}.values()) - 0 = 0`.
`"unexpected swallowed failures"` then reads `0 <= MAX_SWALLOWED_NEW(2000)` → **HOLDS**, i.e. a
missing failure ledger reads as a clean pool rather than as an unmeasured one. Same failure shape
as the REFERENCE_ASSAYS lead and as the (already-fixed) `COMPLETENESS.json` 0/0 case, just not yet
given the same UNMEASURED treatment. Severity: MAJOR.

A second, milder instance of the same pattern: `standards.py:669-693` (`unans_files`, feeding
`"cached records that were fully read"`). `unans_files = 0` is set before the try; on an
exception mid-glob the counter is left at whatever partial value it reached (silently
undercounted, not clearly flagged) rather than reporting UNMEASURED. A `data/readfeats/` directory
that simply doesn't exist yet legitimately yields `0` via `glob()` returning `[]` with no
exception, which is a fine reading — but a permission error or a corrupt-file read mid-scan is
indistinguishable from "all records fully read." Severity: MINOR/SUSPECTED (lower confidence;
requires a specific I/O failure mid-scan to manifest).

### 3. `scout.py:55` — hand-rolled tmp+`os.replace` instead of `silence`
**REFUTED as literally stated, but a real and closely related defect exists nearby.**

`_land()` (scout.py:55-65) already calls `silence.replace_retry(tmp, path)`, not a bare
`os.replace`:
```python
def _land(path, obj, sort_keys=True):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=sort_keys)
    silence.replace_retry(tmp, path)
```
So the specific claim ("hand-rolled tmp+`os.replace`") does not hold against the current source —
this already uses the shared retry primitive. This part of the lead is REFUTED.

**However**, `silence.write_json`'s own docstring (silence.py:290-327) documents the exact
adjacent hazard this code still has: *"THE TMP NAME CARRIES PID AND THREAD, which the older
hand-rolled `path + ".tmp"` sites did not. Two writers of the same path otherwise collide on the
temp file itself, and the loser can replace the winner's target with a partial file."*
`scout.py:_land()` builds `tmp = path + ".tmp"` — no PID, no thread id — exactly the pattern
`write_json` was written to replace, and `_land()` does not use `write_json`. Its own docstring
(scout.py:58-61) says `WIKI_HOSTS.json` (via `feats.HOSTS`, scout.py:200-204) "is written from
here AND from two call sites in `hostcheck.py`" — i.e. this is a *documented* multi-writer file.
If `scout.py` and `hostcheck.py` (or two `scout.py` invocations) write at overlapping instants,
both open the *same* `WIKI_HOSTS.json.tmp` path; one's partial/complete content can be replaced
onto the target by the other's `replace_retry` call, landing whichever writer wins the race —
possibly the earlier, staler one — rather than either writer's caller ever finding out. This is
the two-writer contract violation, just one level more subtle than the raw claim: it isn't a
missing `silence` call, it's a `silence` call fed a collision-prone temp name.

Also: `_land()`'s callers (scout.py:197-206 for `F.HOSTS`, scout.py:210-218 for `BLOCKED`) each
do read-modify-write: `json.load` the whole file, mutate one key, then `_land()` the whole dict
back. Even with an atomic replace, a second writer's read-modify-write racing the first loses the
first writer's update entirely (classic lost-update), independent of the tmp-naming issue above.

Severity: **MAJOR** (confirmed code pattern; the concrete race requires two near-simultaneous
writers, which the file's own docstring says is a real, documented deployment shape for
`WIKI_HOSTS.json`).

**A second instance of the identical unqualified-tmp-name pattern, same batch:**
`standards.py:1059-1062` (writing `state/job_progress.json` / `JOB_WATCH`):
```python
tmp = JOB_WATCH + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(cur, f)
silence.replace_retry(tmp, JOB_WATCH)
```
Same shape: uses `replace_retry` correctly, but the tmp filename has no PID/thread
disambiguation. `standards.check()` is called from multiple long-running processes per the file's
own comments (`dashboard.py`, `publish.py`, `overwatch.py` all plausibly poll it), so concurrent
`check()` calls racing on `state/job_progress.json.tmp` is the same collision shape as above.
Severity: MAJOR/SUSPECTED (same mechanism, not independently confirmed to have fired in
production logs).

### 4. `genre.py:135-197` — `confidence` computed over only the TOP 3 scores
**VERIFIED, still present.**
```python
def classify_text(text, top=3):
    scores = collections.Counter()
    for g, spec in GENRES.items():
        for pat, w in spec["cues"].items():
            scores[g] += w * len(re.findall(pat, text, re.I))
    return scores.most_common(top)          # <-- caps to top 3, ranked-then-truncated

def classify_source(rec, cap=None):
    ...
    ranked = classify_text(" ".join(parts))      # default top=3
    ...
    top, score = ranked[0]
    total = sum(s for _, s in ranked) or 1        # sum over the TOP-3 ONLY, not all 11 genres
    return {..., "confidence": round(score / total, 3), ...}
```
`GENRES` has 11 entries; `classify_text`'s default `top=3` discards every genre's score past the
3rd-highest before `classify_source` ever sees it, and `total` (the confidence denominator) is
summed over that truncated list. Any signal the source carries for the other 8 genres is
excluded from the denominator, inflating `confidence` for every source whose vocabulary spans
more than 3 genres. This is functionally the same class of bug the file's own docstring
diagnoses and fixes for the *`cap` parameter* (lines 150-177, "cap... was DECIDING ANSWERS")
— but that fix addressed a different cap (truncating the entry list fed into `classify_text`);
it left the `top=3` ranking-then-truncation inside `classify_text`/`classify_source` itself
untouched. `confidence` gates the "low-confidence (genre is genuinely mixed, flagged not forced)"
report at line 218 (`threshold 0.45`) — a source that's genuinely split across 4+ genres can
score above 0.45 on the truncated denominator and silently avoid being flagged as mixed, even
though the flagging logic exists specifically to catch this case. Severity: **MAJOR** (confirmed
mechanism; matches the reported 0.556-vs-0.405 magnitude claim in shape — a cap deciding an
answer, not a display, per Hard Rule 0's own framing).

---

## OTHER FINDINGS

### `standards.py:1090-1097` and `:1315-1325` and elsewhere — undocumented silent-drop is now
the majority shape, not the exception
Given finding #2 above lists 20 of ~24 try/except-wrapped standards with the bad shape, this is
less "a few stragglers" and more "the fix was applied to a minority." Flagging this framing
explicitly since the task description's own estimate ("3 of ~18") undercounts by roughly the same
margin the project's own docstrings warn happens with informal counts ("contamination-detection
regexes always undercount, plan for iterative broadening" — matches the project's known pattern
from other audits). NOTE.

### `standards.py:1188` — display truncation of a pending-promotions list
```python
(", ".join(_pending)[:120] if _pending else "none outstanding"),
```
Truncates the printed status string for `"promotions have their spine codes amended"` to 120
chars. This is pure display formatting of a status line (the underlying `data/SHELF_RANKS.json`
is untouched, and the remedy text tells the operator to open that file directly), so it does not
meet the Hard Rule 0 bar of "truncation of a roster/page/chunk/entry list" — it's closer to the
rule's own carved-out exception. NOTE, not a violation.

### `descending_ladder.py:85-95` — `rung_for_length` silently mislabels out-of-domain sizes as
"Continental" rather than erroring or returning `None`
```python
def rung_for_length(metres):
    if metres <= 0:
        return None, None
    if metres < PLANCK_LENGTH:
        return FOLD_RUNG, "Below the Fold"
    best = DESCENDING[0]                # rung 0, "Continental", edge 1.0e6 m
    for r in DESCENDING:
        if metres <= r[3]:
            best = r
    return best[0], best[2]
```
The loop only ever *tightens* `best` when `metres <= r[3]` holds; for any `metres` **larger**
than the widest edge in the table (1.0e6 m, i.e. anything planet-scale or bigger — which is
exactly the regime this ladder explicitly says it does not cover, since rung 1 = Planet is the
pivot into the ascending Ladder), the loop body never executes and the function returns the
*initial* `best = DESCENDING[0]` — "Continental" — as if that were a real classification, with no
signal that the input was out of the descending ladder's domain. Currently only called internally
from `shrink_report()` (line 134) with a shrink target that's presumably always sub-planetary, so
this has not been observed to misfire in the current call graph, but it is a live landmine for any
future caller (e.g. a batch classification pass over arbitrary attested sizes) that doesn't
pre-filter to sub-planetary inputs. Severity: MINOR/SUSPECTED — correctness bug in shape (silent
wrong default standing in for an error condition), no confirmed live trigger in this batch's code.

### `cosmology_graph.py:151` — unexplained magic-number filter on persisted graph edges
```python
"pairs": [{"a": a, "b": b, "weight": round(w, 3), "shared_sample": pair_shared[(a, b)]}
          for (a, b), w in sorted(pair_w.items(), key=lambda kv: -kv[1])
          if w >= 1.0],
```
Every pair below weight 1.0 is excluded from `SHARED_STAGE_GRAPH.json` entirely — not the
`shared_sample` evidence list inside a pair (that one is correctly uncapped per the adjacent
comment, matching the Hard Rule 0 fix already applied here in run #26), but the *pair itself*.
Unlike `UBIQUITOUS_CUTOFF` a few lines up (which has three lines of rationale), this `1.0`
threshold is undocumented. `propagation.py` and `resonance.py` are named as live readers of this
file (comment at line 144-146); if either ever needs weak-evidence pairs (e.g. to detect a
borderline cluster merge), they cannot, because those pairs were never written. Given `build_graph`
already inverse-frequency-weights and additionally down-weights ubiquitous entities (`w *= 0.15`),
a `w < 1.0` pair is very weak evidence and cutting it may be entirely correct — but it's a
threshold decision made without the file's usual practice of explaining *why* the number is what
it is, in a project that has repeatedly found undocumented caps to be exactly where bugs hide.
Severity: NOTE/SUSPECTED — plausibly correct signal-filtering, not a roster/list truncation in the
Hard Rule 0 sense, but flagged for the owner to confirm the threshold is intentional and not a
leftover.

### `scout.py:176-196` — `PROBE_NAMES = 25` caps the evidence set used to *verify* every
candidate URL
```python
sample = [n for n in names if n and len(n) > 3][:PROBE_NAMES]   # PROBE_NAMES = 25
...
for u in urls:
    r = verify(u, sample)   # every URL checked against the SAME 25-name sample
```
Unlike `sample[:18]` (used only in the model prompt — pure display/context-window truncation,
fine), this 25-name `sample` is also the evidence set `verify()` uses to decide whether a fetched
page is "about this material" (`hits >= MIN_NAME_HITS` where `MIN_NAME_HITS = 2`). For a source
with hundreds or thousands of catalogued names, only 25 of them are ever checked against a
candidate page — a real page about the source's homebrew that happens not to mention any of
those particular 25 names (plausible for a long-tail cast) would be scored `hits: 0` and rejected
as `"ok": False`, even though it is a genuine hit. This directly gates whether a source ever gets
registered as having "somewhere to read from" (`scout()`'s `kept` list feeds `endpoint.register`
and `F.HOSTS`), which is a real downstream decision, not a display. It is more defensible than a
straightforward roster truncation (2 hits out of a reasonable 25-name sample is a fairly low bar,
and a genuinely-relevant page usually surfaces at least one recognizable name), so I'm not
calling this BLOCKING — but it is the same shape (a cap sampling the evidence that decides an
answer) as the confirmed `genre.py` finding above, just with a much higher bar to actually flip an
outcome. Severity: MINOR/SUSPECTED.

### `standards.py` general — three additional standards silently omit rather than emit
UNMEASURED, by explicit but undocumented-as-convention design
`the local model has a live runner` (1203-1231) and `the local model produces tokens`
(1236-1250) both skip `out.append` entirely when the underlying probe returns `None` ("could not
tell" — commented as deliberate, "never reported as a fault"). That's a defensible choice for a
probe that costs a real network call and where "couldn't tell" is common and cheap to re-probe
next cycle — but it is the exact "does not emit" shape the file's own `#880` comment block calls
"worse than one that fails," applied inconsistently: elsewhere in the same file (`the library's
counters are moving`) the fix was to always emit and say "not enough evidence" in the observed
text, specifically so an absent row is never confused with a held one. These two standards were
not brought in line with that principle. Severity: MINOR (documented intent, but inconsistent
with the file's own stated fix pattern) — folded into the count in finding #2 above (items 14-15).

---

## SUMMARY OF SEVERITIES

- BLOCKING: 1 (`standards.py:826-828`, empty-REFERENCE_ASSAYS vacuous green — confirmed known lead)
- MAJOR: 5
  - `standards.py` — 20 standards with silent-row-drop-on-exception instead of UNMEASURED (finding #2)
  - `standards.py:638-661` — vacuous green on unreadable `failures.json` ledger
  - `scout.py:55-65` / `WIKI_HOSTS.json` — collision-prone unqualified tmp name + read-modify-write race across scout.py/hostcheck.py (known lead partially refuted, real adjacent defect confirmed)
  - `standards.py:1059-1062` — same unqualified-tmp-name pattern on `state/job_progress.json`
  - `genre.py:135-197` — `confidence` denominator computed over only the top-3 genre scores (confirmed known lead)
- MINOR: 4 (`standards.py:669-693` partial-count-on-exception; `descending_ladder.py:85-95` out-of-domain mislabel; `cosmology_graph.py:151` undocumented weight-1.0 pair filter; `scout.py` PROBE_NAMES=25 evidence cap)
- NOTE: 2 (`standards.py:1188` display-only truncation, not a violation; general framing note on undercounted "~18" estimate)

## MODULES READ (confirming full-line coverage)
- `src/standards.py` — 1510 lines, read in full (offsets 1-400, 401-800, 801-1200, 1201-1510)
- `src/tiers.py` — 360 lines, read in full (single read)
- `src/scout.py` — 287 lines, read in full (single read)
- `src/genre.py` — 247 lines, read in full (single read)
- `src/descending_ladder.py` — 186 lines, read in full (single read)
- `src/cosmology_graph.py` — 159 lines, read in full (single read)
- Also read for context (not part of the batch, cited by findings above): `src/silence.py` lines 255-360 (`replace_retry`, `write_json`, `note`)

No writes made to `data/records/`, `reference/keystone_volumes/`, `output/index/`, or `state/`.
