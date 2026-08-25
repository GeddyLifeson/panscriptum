# Sweep run31 — BATCH 10 audit

Modules (src/, read every line, read-only):
hostcheck.py (953), handbuilt.py (487), catalogue_web.py (403), sweep_plan.py (285),
genre.py (247), descending_ladder.py (186), physics.py (149)

Total lines read: 2,710

No files were edited. No long-running or state-mutating script was executed; all checks were
read-only greps, `cat -n`, and side-effect-free `python -c` calls against pure functions
(`genre.classify_text`, `descending_ladder.rung_for_length`) that write nothing to disk.

---

## FINDING 1 — genre.py:135-141, 173-197 — `classify_text(top=3)` computes `confidence` over a
truncated score set, silently overstating it. VERIFIED, MAJOR.

`classify_text` returns only the top 3 genres via `scores.most_common(top)` (default `top=3`).
`classify_source` then does:

```python
ranked = classify_text(" ".join(parts))          # at most 3 (genre, score) pairs
...
top, score = ranked[0]
total = sum(s for _, s in ranked) or 1
"confidence": round(score / total, 3),
```

`total` sums only the top-3 scores, not all 11 genres in `GENRES`. For any source whose
vocabulary triggers more than 3 genres non-trivially (a crossover/mixed-genre source — exactly
the case this metric exists to catch, per the docstring "A source that scores 40 for grimdark and
38 for horror is NOT confidently either"), `confidence` is inflated because the excluded
lower-ranked genres' scores are dropped from the denominator.

Verified with a synthetic mixed-genre text (mythology+high_fantasy+grimdark+cosmic_horror+
space_opera+cyberpunk cues combined):
```
all 11 genres:  [('cosmic_horror',12),('cyberpunk',12),('mythology',9),('high_fantasy',9),
                 ('space_opera',9),('grimdark',6), ...5 zeros]
top-3 only:     [('cosmic_horror',12),('cyberpunk',12),('mythology',9)]
confidence (top-3 denominator):  0.364
confidence (full 11-genre denominator): 0.211
```
A ~73% relative overstatement. This directly feeds `main()`'s low-confidence report
(`v["confidence"] < 0.45`, "genre is genuinely mixed, flagged not forced") — a genuinely 6-way
mixed source can score confidence above the flag threshold purely because of the top-N cutoff,
and register/priors (which drive naming and world-defaults downstream per this file's own header)
are then applied with false certainty. This is the "top N" cap Hard Rule 0 explicitly names,
silently deciding an answer (the confidence score and the low-confidence flag), not merely
display. `ranked[0]` (which genre wins) is unaffected — `Counter.most_common` scans all genres
internally — only the confidence math is wrong.

Fix direction: compute `total` from a full, untruncated scoring pass (`top=len(GENRES)` or a
separate full-score call), independent of how many results are returned for `runners_up` display.

---

## FINDING 2 — hostcheck.py:67-77 and all 7 call sites — `_land()` discards
`silence.replace_retry`'s return value; a persistently denied write is silent success. VERIFIED,
MAJOR/BLOCKING.

```python
def _land(path, obj, sort_keys=True, ensure_ascii=True):
    """Write a shared artifact whole or not at all. ..."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=sort_keys, ensure_ascii=ensure_ascii)
    silence.replace_retry(tmp, path)
```

`silence.replace_retry` (src/silence.py:263-280) never raises; on persistent `PermissionError`
across all retry attempts it calls `note(...)` and returns `False`, leaving `path` unchanged and
the `.tmp` file behind. `_land()` ignores that return value entirely, so every caller proceeds as
if the write landed:

- `sweep()` line 591-592, 598: prints `"WIKI_HOSTS.json updated: N repointed..."` and
  `"-> " + OUT` unconditionally after `_land(F.HOSTS, hosts)` / `_land(OUT, results)`.
- `purge()` line 708: `_land(fp, r, ...)` clears a record's `entries` and stamps
  `purged_roster`; if the write is denied, the console still prints `"removed: SRC <- HOST N
  entries"` while the on-disk record is untouched (worse: the *log* at line 731
  (`_land(PURGED, prev)`) can still record the purge as done).
- `roster_audit()` line 839, `adopt()` line 906: same pattern.

This is precisely the failure class this very file's own comments describe having caused real
damage elsewhere ("a bare `open('w')` truncates... which is how COMPLETENESS.json came to hold
zero rows on 2026-08-24") and that `handbuilt.py` (same batch) demonstrates fixing correctly:
```python
if not silence.replace_retry(tmp, OUT):
    silence.note("handbuilt.py:write-did-not-land")
    print("WRITE DID NOT LAND: " + OUT)
    return 1
```
`hostcheck.py`'s dedicated "write it safely" helper is the one place in this batch that omits
that check.

Fix direction: `_land()` should return `silence.replace_retry(...)`'s result and every call site
should act on `False` (at minimum log via `silence.note` and print a "WRITE DID NOT LAND"
message; `purge()` and `sweep()`'s repair path should probably abort rather than report success).

---

## FINDING 3 — catalogue_web.py:96-103 — `catalogue_composite`'s per-category bare
`except Exception: continue` swallows a transport failure and undercounts a composite source
permanently. VERIFIED, MAJOR.

```python
for c in cats:
    try:
        titles = ws.clean_titles(ws.category_members(sub, c, limit=None))
    except Exception:
        silence.note("catalogue_web.py:79")
        continue
```

A network/API failure fetching one category's member list is indistinguishable here from "this
category is genuinely empty" — both result in `continue`, contributing zero entries for that
category to the merged record. The record is still written with `"status": "catalogued"`, and
`main()`'s default source selection is `entry_count == 0` (line 306), so once *any* entries land
from other categories/sub-wikis, this source's `entry_count` is non-zero and it will never be
re-picked without an operator manually passing `--recatalogue`. This is the exact "transport
failure cached forever as a verified absence" pattern the lens warns about, and it is materially
weaker than the sibling `catalogue()` path for ordinary (non-composite) sources: there, a
category-fetch failure is *not* caught locally — it propagates out of `catalogue()` and is caught
only at the top level in `main()._one()`, which marks the whole source as failed/`SKIPPED` rather
than silently publishing a partial merge. Composite ("Pantheon: <culture>"-style, cross-wiki)
sources get systematically weaker failure handling than every other source.

(Minor, same block: the `silence.note("catalogue_web.py:79")` tag references line 79, which is
stale/wrong — the call is actually around line 102. Cosmetic, but it means anyone grepping the
note log for the offending line won't find it.)

---

## FINDING 4 — hostcheck.py:917 vs 644 — `--purge` CLI help text contradicts the function's own
corrected docstring. VERIFIED, MINOR/MODERATE.

```
line 917: ap.add_argument("--purge", ...,
              help="remove rosters the audit rejected AND whose host was independently rejected")
```
But `purge()`'s docstring (lines ~640-650) says, in so many words:
```
The safety here is the HUMAN, not a second automated condition. An earlier docstring
claimed the code also required the host to have been independently rejected; it never did
(the check was loaded and unused), and pretending a safeguard exists is worse than naming
the real one: nothing is purged except sources a person explicitly listed with --source...
```
The function docstring was corrected; the `argparse` help string for the same flag, read by
anyone running `hostcheck.py --help`, still asserts the disproven "independently rejected" safety
condition. For a destructive operation (`--purge --go` deletes catalogued entries), the CLI help
is the most likely thing an operator actually reads, and it currently overstates the safeguard.

---

## FINDING 5 — hostcheck.py:27-31 vs :443-483 — module-level docstring describes the wrong
verdict mechanism. VERIFIED, MINOR.

The file's opening docstring states the test as an absolute rate:
```
    hit rate >= GOOD    the host holds the fiction
    hit rate <= DEAD    the host answers to the name and holds something else
```
But `score()`'s actual "holds" verdict (line 480-481) is driven by **lift over baseline**
(`r["lift"] >= GOOD_LIFT`), not by the raw `GOOD` constant — and `score()`'s own docstring
explains at length why an absolute rate was abandoned ("An absolute hit rate is meaningless on
its own... LIFT is the measurement"). `GOOD` (0.35) survives only as an early-break threshold on
raw `rate` inside `sweep()`'s repair search (line 545) and is never used to decide a verdict. The
top-of-file description of the methodology is therefore stale relative to the code it introduces.

---

## FINDING 6 — hostcheck.py:462-467, 219-260 — `relevance()`/`_bodies()` use the same `None`
sentinel for "nothing to check" and "the fetch failed," letting a transient failure silently skip
the aboutness veto. HYPOTHESIS, MODERATE.

`_bodies()` returns `[]` both when there is genuinely no revision content and when `_get(...)`
raises (caught, `silence.note`d, falls through to `return out` with whatever was accumulated,
often empty). `relevance()` then does `if not bodies: return None`, identical to its earlier
`if not titles or not toks: return None` (genuinely nothing to evaluate). In `score()`:
```python
r["about"] = (relevance(...) if r["hits"] and base >= ABOUT_VETO_ABOVE else None)
...
elif r["about"] is not None and r["about"] < ABOUT:
    r["verdict"] = "NAMES ONLY"
```
A transient network failure fetching article bodies on a "generous" host (`base >=
ABOUT_VETO_ABOVE`) produces `r["about"] = None`, which *skips* the aboutness veto entirely rather
than erroring or retrying — the same host, if its lift also clears `GOOD_LIFT`, can be verdicted
`"holds"` even though the veto that exists specifically to catch a wrong-fiction match on a
generous host never ran. Mechanism verified in source; not verified against live traffic, hence
hypothesis.

---

## FINDING 7 — descending_ladder.py:85-95 — `rung_for_length` has no upper-bound guard; sizes
above the top rung (1e6 m) are silently mislabelled "Continental" instead of erroring.
VERIFIED (code + live test), MINOR (currently unreached — no other assigned-batch module or grep
hit calls this function with live data; `derivation.py` only lists the module name in a scan
list).

```python
def rung_for_length(metres):
    if metres <= 0:
        return None, None
    if metres < PLANCK_LENGTH:
        return FOLD_RUNG, "Below the Fold"
    best = DESCENDING[0]
    for r in DESCENDING:
        if metres <= r[3]:
            best = r
    return best[0], best[2]
```
Confirmed live:
```
rung_for_length(5e10)  -> (0, 'Continental')   # solar-system-scale distance
rung_for_length(1.5e6) -> (0, 'Continental')   # just above the top rung's own threshold
```
There is a floor guard (`metres <= 0`) and a below-Planck guard, but no matching ceiling guard:
any value larger than the largest rung length (`DESCENDING[0][3] == 1.0e6`) silently returns
`DESCENDING[0]` (initialized before the loop and never disqualified) rather than `None`/an error
signalling "out of this ladder's range, use the ascending Ladder instead." A future caller feeding
a planet-or-larger size (this module's own docstring is explicit that its scope is "the rungs
BELOW Planet") would get a wrong, unflagged answer rather than a loud failure.

---

## FINDING 8 (minor cluster) — early-`break` "good enough" search termination may accept a
worse host than a later untried candidate. HYPOTHESIS, MINOR — flagged per Hard Rule 0's explicit
"early break" language, but plausibly an intentional, documented efficiency tradeoff rather than
a true violation (unlike the removed `MAX_PER_SOURCE`/`MAX_PER_CATEGORY` caps in this same file's
sibling module, this doesn't shrink the catalogued universe — it can only affect *which* already-
adequate host is chosen).

- hostcheck.py:545 (`sweep()`'s `--repair`): `if best[0] >= GOOD: break` — stops scanning
  `candidates(...)` once a host clears the flat 0.35 rate, even if a much better-fitting candidate
  sits later in the list.
- hostcheck.py:887 (`adopt()`): `if best[0] >= GOOD_LIFT: break` — same shape, against lift.

---

## FINDING 9 (minor) — hostcheck.py:672-717 `purge()` writes `records/*.json` directly via
`_land()`, not through `pipeline.write_record_catalogue`. Deliberate and documented (the sanctioned
writer "merges and never shrinks an entry list," which is wrong for a purge), but it is a literal
instance of the two-writer contract's forbidden pattern ("any module that opens a records/ file
and writes it directly"), and it performs an un-locked read-modify-write against a file that
`catalogue_web.py` writes concurrently via the pipeline writer during a live catalogue run — a
TOCTOU race is structurally possible if `--purge --go` is ever run while a catalogue pass touches
the same source. HYPOTHESIS/MINOR — `purge()` is a rare, manually-invoked operation, so the
practical exposure is low, but nothing in the code prevents the overlap.

---

## FINDING 10 (minor) — sweep_plan.py:145-151 — `record()`'s per-process shard write uses a
hand-rolled `open(tmp,"w")` + `os.replace(tmp, p)` under `state/sweep_shards/`, not
`silence.write_json`/`silence.replace_retry`. Functionally equivalent (atomic tmp+rename, and
each shard's filename is unique per run/batch/pid so there is no actual multi-writer collision on
this specific path), but it is a literal deviation from "shared state files must land via
silence.replace_retry / silence.write_json." Cosmetic/minor — no corruption or race is actually
possible given the unique-filename design, but the code doesn't use the project's sanctioned
helper to get there.

---

## FINDING 11 (minor, unconfirmed) — genre.py:188-197 `classify_source` returns direct
references to `GENRES[top]["priors"]` and `GENRES[top]["register"]` (not copies). If any consumer
mutates `rec["priors"]` in place (e.g. filling in an unattested axis), it would permanently
corrupt the shared `GENRES` module global for every subsequent classification of that genre. No
mutator was found within this batch's modules or in a grep of the other files that reference
`priors`; flagged as a latent hazard, not a confirmed live bug.

---

## Findings reviewed and NOT flagged as Hard Rule 0 violations

- `hostcheck.py` `PROBE=40`, `MIN_PROBE=5`, `null_rate`'s `sample=40` downsampling, and
  `relevance`'s `sample=12` are sample sizes for a statistical fitness/signal test (hit-rate vs.
  baseline), not truncations of the catalogued corpus — the file explicitly reasons about this
  ("a hit rate is noise" below `MIN_PROBE`). Different in kind from the `MAX_PER_SOURCE` /
  `MAX_PER_CATEGORY` caps this same file's sibling (`catalogue_web.py`) correctly removed.
- `genre.py:220-222` `low[:5]` truncates only a console report line (`for s, v in low[:5]`); the
  reported count `len(low)` is exact and untruncated. Display-only, not a universe-shrinking cap.
- `sweep_plan.py` was independently re-audited in prior runs (per its own inline history:
  run #28/29, dated 2026-08-25) and the module-lines/shard-topology bugs it documents fixing were
  verified fixed in the current source; no new Hard Rule 0 cap was found in `modules()`,
  `batches()`, `missing()`, or `covered_by()`.

---

## Summary by severity

- BLOCKING: 0
- MAJOR: 3 (Findings 1, 2, 3)
- MINOR/MODERATE: 8 (Findings 4, 5, 6, 7, 8, 9, 10, 11)
- COSMETIC: stale `silence.note` line-tag in catalogue_web.py:102 (bundled into Finding 3)
