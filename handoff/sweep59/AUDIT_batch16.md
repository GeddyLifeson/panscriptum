# Sweep 59 -- AUDIT batch 16

Modules read in full:

| module | lines | read (top to bottom? mtime at read time) |
|---|---|---|
| src/hostcheck.py | 1636 | yes, full (2026-09-08 17:28) |
| src/binding_health.py | 1601 | yes, full (2026-09-14 22:14) |
| src/scout.py | 833 | yes, full (2026-09-13 22:44) |
| src/secondopinion.py | 704 -> 708 while under review | yes, full; re-diffed after mtime moved to 2026-09-14 22:26 (see note below) |
| src/canon_backup.py | 549 | yes, full (2026-09-13 22:25) |
| src/pick_model.py | 449 | yes, full (2026-09-14 22:14) |
| src/catalogue_models.py | 364 | yes, full (2026-09-13 22:49) |
| src/entity_match.py | 319 | yes, full (2026-09-14 22:14) |

**Note on secondopinion.py**: mid-review its mtime moved from 2026-09-13 22:37 (704 lines) to
2026-09-14 22:26 (708 lines). Re-read the diff region (lines 84-110): the change is exactly the
house eaten-escape guard (`_BAD_CHARS` block) being inserted at module top, moved 4 lines down
from where `HERE = ...` used to sit. Correctly placed after `os` is imported (line 87), before
any other module code runs. Not in run #59's own list of 24 modules that got this guard tonight,
but the insertion itself is the same mechanical, correctly-ordered change as the other 23 -- no
functional code changed underneath it. Rest of the file matches my earlier full read.

## src/pick_model.py

### Checked and clean
- The eaten-escape guard (lines 24-27) is correctly placed: `os` is imported immediately above it
  (line 24) before `os.path.abspath(__file__)` is used, and the guard runs before any other
  module code (including the `_NO_WIN` line and the second `import os` at line 31). It does not
  run as a script anywhere that would give `__file__` a different meaning; `os.path.abspath`
  normalises either way.
- `import os` appears twice (line 24 and line 31). Harmless -- a second `import os` is a no-op
  cache hit via `sys.modules`, not a NameError risk or a behavioural change -- but it is a leftover
  from the guard insertion and worth tidying if anyone touches this file again. Not filed as a
  DEFECT since it changes no behaviour.
- `resident()` / `fit_note()` / `total_vram_gb()` / `free_vram_gb()` "BY CLASS" vs "RIGHT NOW"
  budget split (order 2f38b3e5258d) is internally consistent; `vram_measured` provenance flows
  correctly into both the refusal gate and the printed budget note.
- `save_config()`'s targeted `re.sub` + `silence.replace_retry` + verdict-return chain is correct;
  a no-match substitution and a denied rename are both reported truthfully rather than as success.

## src/binding_health.py

### New findings
(none beyond what is already filed -- see Known below)

### Known (already open orders)
- **30854f11f322** (MAJOR, `binding_verdict`, lines 901-982 at mtime 2026-09-14 22:14) -- still
  accurate. Verified against current source: `score = max(s for s, _ in scored)` at line 953 still
  reaches CONFIRMED (>=85) purely on `rapidfuzz.fuzz.token_set_ratio` containment, and the record
  now carries `containment`/`tight`/`tied_with` exactly as the order's last shift-note describes.
  This is an OWNER ruling question (where to draw the line between a wiki genuinely named after
  its source and a short generic sitename that happens to be a word-subset), not a repair; correctly
  left open.

### Checked and clean
- Eaten-escape guard (lines 47-49) correctly placed: after `os`/`json`/`re`/`sys`/`threading`/
  `time` imports, before `HERE`/`silence` import, using already-imported `os`.
- `quarantine()` / `release()` compare-and-swap (digest-before-read, `_land_cas`, re-read-and-retry
  loop) is internally consistent; both fail closed on an unreadable `HOST_QUARANTINE.json` rather
  than defaulting to an empty map.
- `verdict()`'s three-valued present/absent/reachable truth table (lines 1001-1049) traced by hand
  against all reachable branches; no case falls through to an unintended default, and `ok_absent is
  None` is handled before any other test can see it (matches the docstring's stated priority).
- `run()`'s whole-estate-vs-partial-pass guards (empty hosts map, zero-host result, filtered-empty
  result, CAS-merge failure) each refuse to land rather than silently producing a smaller-universe
  report; verified each of the four guards actually returns before reaching `_land`/`_land_cas`.
- `_spread()`'s "+0.5 not round()" comment checked against Python 3 banker's rounding -- correct,
  `round()` would produce uneven steps at exact halves.

## src/hostcheck.py

### New findings

**DEFECT MINOR -- `probe()`'s API-branch exception handler truncates a persisted diagnostic field with no cut marker**
where: src/hostcheck.py `probe` (lines 353-360, mtime 2026-09-08 17:28)
evidence:
```
    except Exception as e:
        silence.note("hostcheck.py:probe")
        # NOT a rate of zero. A request that failed is not a wiki that holds nothing, ...
        return {"host": host, "probed": len(names), "hits": 0, "rate": None,
                "error": f"{type(e).__name__} {str(e)[:60]}"}
```
failure: `probe()`'s returned dict flows unchanged through `score()` into `sweep()`'s `results`
dict, which is persisted to `data/HOST_FITNESS.json` via `_land(OUT, results)` (line ~1130). Any
exception whose `str(e)` exceeds 60 characters (routine for a wrapped `HTTPError`/`URLError` with
a URL and a reason clause) is silently cut mid-sentence with no ellipsis or `+N` marker -- the
exact Hard Rule 0 shape ("a display cut must say it cut") this same codebase has fixed at least
three times elsewhere on the identical field type: `catalogue_models.ask_provider` (order
6d354a508b96, "these are single-line exception reprs, not documents ... the cut was landing on the
reason itself"), and `binding_health._fetch_chars`/`_probe_reachable`/`_probe_identity` (orders
ecc355769a41 / d6ca84486153, "THE REASON IS STORED WHOLE"). This site predates all of those fixes
(hostcheck.py's mtime, 2026-09-08, is the oldest of the eight files in this batch) and was not
swept up by any of them.
remedy: drop the `[:60]`, or collapse whitespace and keep the whole string the way
`catalogue_models.ask_provider`'s exception branch now does (`" ".join(str(e).split())`).

**DEFECT MINOR -- `scout.scout()`'s registration-failure notes truncate a persisted field with no cut marker**
where: src/scout.py `scout` (lines 450-451 and 476-477, mtime 2026-09-13 22:44)
evidence:
```
            reg_note = ("%d page(s) verified but NOT registered (%s: %s)"
                        % (len(kept), type(e).__name__, str(e)[:120]))
...
                reg_note = ("%d page(s) registered but host adoption failed (%s: %s)"
                            % (len(kept), type(e).__name__, str(e)[:120]))
```
failure: `reg_note` becomes part of the returned `note` field (`_note = reg_note + ...`), which is
appended into `results` and persisted whole into `data/SCOUT.json` via `sweep()`'s
`prev.append({"at": ..., "results": results})` / `_land(LOG, window, ...)`. The exceptions that
reach these two sites come from `endpoint.register()` (which itself raises re-raised
`RuntimeError`s from CAS refusals, per `endpoint.register`'s own contract described a few lines
above at 428-432) and from `_mutate`'s failure path, both of which are exactly the kind of
multi-clause, file-naming message likely to exceed 120 characters -- and this same module has
fixed the identical "cut a field a person reads to diagnose a failure" shape at least four times
elsewhere in this file (orders e8cd908ce5e4, d57377577891 area comments: "WHOLE NAMES", "the
reason is the whole product of this line"), but these two sites were not touched.
remedy: same as above -- drop the `[:120]` or collapse whitespace and keep the whole message.

### QUESTION -- is `probe()`'s RAW-mode branch missing the same crash-isolation the API branch has?

The API branch of `probe()` (lines 351-360) wraps its `_get()` call in `try/except Exception`, so
a network failure degrades to `rate: None` rather than propagating. The RAW-mode branch three
lines above it (338-344) has no such guard around `EP.fetch_raw(host, names[:12])` -- if
`endpoint.fetch_raw` ever raises rather than swallowing its own transport errors, that exception
would propagate out of `probe()`, out of `score()`, and into `sweep()`'s
`ThreadPoolExecutor.map(one, todo)`, which re-raises on `.result()` and would abort the whole
sweep rather than recording one host as unreachable -- the exact "one bad host must not cost the
other N their check" property this batch's other modules (`binding_health.run`, `scout.sweep`)
explicitly re-affirm at every call site that can fail per-item. Two readings: (1) `endpoint.py`
(out of this batch's module list) already catches everything internally and this asymmetry is
cosmetic; (2) it does not, and a single RAW-mode host with a transport fault taking down an entire
`hostcheck.py --repair`/`--adopt` pass is a real, unfiled exposure. I did not read `endpoint.py` in
this batch (out of scope for batch 16's module list) so I cannot settle which reading holds; a
ruling needs a read of `endpoint.fetch_raw`'s own exception contract.

### Known (already open orders)
- **a8e02f3bbf76** (MINOR, `HOSTCHECK_EXAMPLES_PERSISTED_CAP`, `probe` lines 342-344 and 361-366 at
  mtime 2026-09-08 17:28) -- still accurate. Verified against current source: the RAW branch still
  writes `"examples": sorted(got)[:5]` beside the whole `"titles": sorted(got)`, and the API branch
  still writes `"examples": found` (itself `[p.get("title") for p in live][:5]`) beside the whole
  `"titles"` list. `score()` correctly reads `about`/`about_n` off the whole `titles` list before
  popping it (line 817), so nothing downstream is ACTED on a smaller universe -- only the display
  field is an unmarked cut, exactly as the order states.

### Checked and clean
- Eaten-escape guard (lines 68-70) correctly placed after all stdlib imports and before
  `cachekey`/`silence` sibling imports.
- `_land_hosts`'s compare-and-swap (digest-before-read, re-read-per-attempt, halt re-checked
  immediately before the CAS per owner ruling 2026-09-08) traced and internally consistent.
- `null_rate`'s dedupe-then-stride control-sampling (`sorted(set(foreign))[::stride][:sample]`,
  order cb8bc5afa58f) is correct: for `len(uniq) <= sample` the stride is 1 and the slice returns
  every unique name, never fewer than exist.
- `score()`'s branch order (rate None -> base None -> probed<MIN_PROBE -> hits/lift floor ->
  about_n==0 -> about thin -> about low -> lift -> partial) traced by hand; the "zero bodies read
  buys more permission than two bodies read" defect the comments describe as already-fixed is in
  fact fixed -- `about_n == 0` is caught by its own UNREACHABLE branch above the generic
  about-too-thin branch.
- `_spread`-equivalent-shape checks (candidates_split's grounded/speculative split, `sweep`'s
  lift-based `best` tuple, `adopt`'s identical tuple) all correctly rank on lift, never on raw
  rate, matching order e2f0b13c766f.

## src/scout.py

(new finding filed above, under hostcheck.py's section per the shared theme -- see
`scout.scout()` reg_note finding)

### Checked and clean
- Eaten-escape guard: **absent**, correctly so -- scout.py is not one of the 24 modules run #59
  named for tonight's insertion, and it was not present before either. No defect.
- `_mutate`'s CAS (digest-before-read, wrong-shape fails closed, thread+attempt in temp name) is
  internally consistent and matches the pattern used by `hostcheck._land_hosts` and
  `binding_health._land_cas`.
- `sweep()`'s stamp-before-work / unstamp-on-never-asked logic traced by hand: `_stamp` marks
  exactly the sources in `order` (post-limit); `_unstamp` only reverts a source whose current
  stamp still equals this pass's `now` (so a concurrent stamp from another process is not
  clobbered), and correctly distinguishes "seen read failed, don't unstamp" from "seen read fine,
  restore prior value or pop if there was none."
- `verify()`'s `needed = max(1, min(MIN_NAME_HITS, probeable))` floor correctly keeps the bar at 2
  for any source with 2+ probeable names and only lowers it to 1 when exactly one usable name
  exists; the `probeable == 0` case is handled separately as `unverifiable` rather than silently
  requiring `needed=1` against a structurally-always-zero `hits`.

## src/secondopinion.py, src/canon_backup.py, src/catalogue_models.py, src/entity_match.py

Read in full; no new findings. All four are extensively self-audited already (each file carries
multiple dated `order ...` comments documenting past defects and their fixes) and I could not find
a live defect distinct from what those comments already describe as fixed. Specific things traced
by hand and found correct:
- `secondopinion.py`: `_vulture`'s `:<digits>:` regex correctly avoids matching a Windows drive
  letter's colon; `report()`'s tree-fingerprint-before-and-after guard correctly refuses to file
  orders when the tree moved mid-scan; `NOT_FILED` waiver table only lists codes actually inside
  `RUFF_RULES`.
- `canon_backup.py`: `members(strict=True)` refuses rather than shrinks on any missing canonical
  path; `verify()`'s `unreadable`/`changed`/`added`/`gone` sets are correctly kept apart (a locked
  file is not reported as "changed"); `restore()` opens the zip member before creating the
  destination file, so a bad `--restore REL` cannot leave a 0-byte file at the real destination.
- `catalogue_models.py`: `EMPTY_LIST` outcome is correctly folded into `live`/`verified` rather than
  falling through to the `unverified`/unreachable path (order from sweep42-batch14); `ask_provider`
  tries the shorter `/models` path before `/v1/models` when `base` already ends in `/v1`.
- `entity_match.py`: `qualifier_compatible` gate is absolute (never overruled by a similarity
  score) and correctly separates "both bare", "both qualified, tokens match", "both qualified,
  tokens differ", and "one qualified, one bare"; the `WEAK < STRONG` ratchet is a raised
  `ValueError` at import time, not an `assert` (so it survives `python -O`).

QUESTIONS: 1
record(): ok
