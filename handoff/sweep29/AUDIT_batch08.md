# BATCH 08 AUDIT — run29

Modules: `feats.py` (991 lines), `manifest_builder.py` (478), `reference.py` (358),
`sevenfold.py` (274), `tells.py` (215), `sweep_plan.py` (235).

Method: every line read; several findings reproduced with a live miniconda-python driver
against real `data/` cache files or synthetic shard files. Each finding is labelled
REPRODUCED, VERIFIED-BY-READING, or HYPOTHESIS.

---

## sweep_plan.py

The supervisor asked for this file to be audited hard: `record()` was rewritten this run to
use per-batch shard files instead of a cross-process `threading.Lock`. Six sub-questions were
posed: shard collision safety, `_read_shards()` newest-wins merge correctness, and whether
`missing()` can now under- or over-report.

### FINDING 1 — CRITICAL — `missing()` can falsely report a covered module as missing
(REPRODUCED)

`_read_shards()` (line 95-119) merges every shard ever written, for every run, keyed only by
module name, with "newest wins" decided purely by **wall-clock `at` timestamp**
(line 118-119: `if prev is None or (at or 0) >= (prev.get("at") or 0): out[m] = {"run": run, "at": at}`).
It does **not** prefer the shard belonging to the run being asked about. `missing(run)`
(line 194-198) then reports a module as missing whenever `coverage_map()[module]["run"] !=
run` — i.e. whenever some *other* run's shard happens to have a later timestamp.

Reproduced directly:

```
sim2.run_new.*.json   {"run": "run_new", "at": 1000.0, "modules": ["address.py"]}
sim2.run_old.*.json   {"run": "run_old", "at": 2000.0, "modules": ["address.py"]}   # written LATER in wall clock

>>> "address.py" in sweep_plan.missing("run_new")
True
```

`address.py` genuinely was covered by `run_new` — its own shard says so — but because
`run_old`'s shard for the same module happens to carry a later `at`, `coverage_map()` reports
`address.py` as belonging to `run_old`, and `missing("run_new")` therefore lists it as
never covered by `run_new`. This is a real over-report: a sweep can be **complete** and still
have `missing()` claim it is not.

Consequence: any operational replay of an older run id after a newer run has already executed
— a supervisor manually re-running a stale batch command for a spot-check, a retried job that
was invoked with a copy-pasted old `run` argument, or simply two runs' shards colliding because
shard files are never cleaned up (see Finding 2) — permanently corrupts the coverage view for
every module the stale run touches, in a way that is silent and does not self-heal until an
even-later write for that module occurs. Since the whole reason this file exists is "the check
that proves nothing was dropped" (its own docstring), a check that can produce false positives
on "was this covered" defeats that purpose.

Root cause: coverage identity is tied to *recency of write*, not to *run identity*. A correct
merge for `missing(run)` needs to ask "does a shard exist whose `run == run`", not "what is the
single newest shard for this module across all runs, and does its `run` field match".

Fix direction (not applied — audit only): `missing(run)` should check `any(shard.run == run and
module in shard.modules for shard in all_shards)`, independent of what any other run's shard
says, rather than routing every check through a single global newest-wins reduction that only
tracks one `(run, at)` per module.

### FINDING 2 — MEDIUM — shard directory grows forever; increases exposure to Finding 1
(VERIFIED-BY-READING)

`_shard_path()` (line 85-91) never deletes old shards, and nothing else in this file does
either. Every run of every batch, forever, leaves a `.json` file in `state/sweep_shards/`.
This is not itself a correctness bug, but it is what makes Finding 1 a live operational hazard
rather than a lab curiosity: the longer the project runs, the larger the pool of old-run shards
sitting around with old (but not necessarily *older-than-everything*) timestamps, any one of
which can resurface via Finding 1 if ever rewritten (e.g. a module gets swept again under an
old run id by mistake, or a filesystem `mtime`/clock skew produces a later `at` on an
objectively older write).

### FINDING 3 — shard collision safety and concurrent-process write correctness — GOOD, verified
sound (REPRODUCED)

Fired six concurrent OS processes (`ThreadPoolExecutor`-free, real separate `python.exe`
invocations) at `sweep_plan.record("TESTRUN_A", ..., batch=1..6)` with disjoint module lists
and confirmed via `coverage_map()` that all twelve modules landed correctly with no lost
writes and no corrupted shard files. `_shard_path()`'s `run.batch.pid.json` naming
(line 85-91) is sufficient to prevent two different OS processes from colliding on the same
shard file, which was the specific hazard the previous `threading.Lock` version could not
prevent (a threading lock does not hold across processes). This part of the rewrite is a real
fix and works as intended.

One residual, low-probability, unexploited edge case worth noting for the record: the shard's
own `tmp` file (`"%s.tmp" % p`, line ~156) is *not* pid/thread-qualified beyond what's already
in `p` — if the exact same process (same pid) called `record()` twice concurrently from two
threads for the exact same `run`+`batch`, the two `.tmp` writes would collide. Not observed in
practice (this run's own harness calls `record()` once, single-threaded, per process), but note
it does not carry the same protection `silence.write_json` gives its own tmp names
(`path.pid.threadid.tmp`).

### FINDING 4 — the aggregate `SWEEP_COVERAGE.json` fold-in race — correctly reasoned as
harmless (VERIFIED-BY-READING, no bug)

`record()`'s tail (line ~148-165) still uses `threading.Lock` around a read-`SWEEP_COVERAGE.json`
-merge-write of the aggregate file, which *is* a cross-process race (the lock doesn't help
across processes). The docstring is explicit that this is known and accepted because
`coverage_map()` and `missing()` never trust `SWEEP_COVERAGE.json` for any module that has a
shard (`data.setdefault(m, r)` only fills gaps, line 183-189 / 199). I checked this claim by
reading `coverage_map()` and `missing()` directly and confirms it holds: even if two processes'
writes to `SWEEP_COVERAGE.json` race and one clobbers the other, the shards remain the source of
truth for every module that has one, so the aggregate file's staleness cannot itself cause
Finding 1 or a missed module. Agreed with the file's own reasoning here — not a bug.

### Module verdict
sweep_plan.py has one real, reproduced, supervisor-relevant defect (Finding 1) in the exact area
flagged for scrutiny. The pid-based shard-collision fix itself (the headline change this run)
is sound and verified. The remaining threading.Lock use on the aggregate file is correctly
scoped as best-effort and does not undermine correctness.

---

## feats.py

### FINDING 5 — HIGH — `roll()` silently drops sources with no resolved wiki host, with zero
counter (REPRODUCED)

`roll()`'s job-building loop (line 841-844):

```python
for _, r in records:
    h = hosts.get(r["source"])
    if not h or (only and only not in r["source"]):
        continue
```

skips a source entirely — no job, no print, no counter — whenever `hosts.get(source)` is falsy.
`main()`'s `--roll` path calls `resolve_hosts(recs, verify=False)` (line ~965), and
`resolve_hosts()` with `verify=False` **skips the guess-and-verify loop entirely** for any
source not already in `data/WIKI_HOSTS.json` and not covered by a `_HOST_OVERRIDES` regex
(line 277-278: `if not verify: continue`). So a source added to the corpus since the host map
was last built with `--hosts` (verify=True) never gets a host, never gets flagged, and silently
never appears in the roll's job list at all.

Reproduced against the live repo:

```
sources in data/records (P.records()):      210
sources present in data/WIKI_HOSTS.json:    203
sources with NO entry at all in the map:      8
  ['Clockwork Angels (Rush)', 'Curious DM Investigations (the Sharkin)',
   'Genuine Fantasy Press (Forgotten Secrets)', 'KBP Unlikely Heroes', 'Song of Syx',
   'Super Energy Apocalypse 1 & 2', 'The Elements Beyond', "swecky's Nature Traditions"]
```

If `python feats.py --roll` were run right now, these 8 sources would be entirely absent from
the mining pass with no visible signal in the printed summary (`roll: N entities across M
wikis...` only counts jobs that were built) — exactly the "smaller universe, same shape"
failure this project's own Hard Rule 0 exists to name. Consequence: a source can sit unmined
indefinitely and every roll summary looks complete.

Fix direction: `roll()` (or `main()`'s `--roll` branch) should count and print
`len({r["source"] for _,r in records}) - len({j[1] for j in jobs})` — sources present in the
corpus that produced zero jobs — the same way `done["empty"]` and `done["errored"]` were split
apart specifically because "a systemic fault ... would depress the roll's feats-per-entity rate
with no visible signal anywhere" (the file's own words at line ~864, about a *different*
silent-loss class it already fixed once).

### FINDING 6 — MEDIUM — `mine()` / `by_axis()` drop ~1/3 of split sentence fragments with zero
tracking, contradicting the module's own stated design (REPRODUCED)

The module docstring states: "it keeps everything it gathers, including what the gate turned
down, because the previous pass discarded its rejections and left the rejection rate
unauditable." In practice, `mine()` (line 591-613) and `by_axis()` (line 704-723) both apply a
hard length filter before any sentence ever reaches the evidence gate or the `gate_rejected`
bucket:

```python
for s in _SENT.split(text):
    s = s.strip()
    if not (20 < len(s) < 400):
        continue          # <- dropped here, never counted, never in `rejected`
```

Sentences failing this check are not added to `kept`, not added to `rejected`, and there is no
counter anywhere (`grep` confirms `too_short`/`too_long` do not exist in the file). Reproduced
by re-splitting 5 real cached Dragon Ball pages from `data/feats/dragonball_fandom_com/`
through the module's own `_SENT` regex:

```
total sentence-split fragments:                    19,306
dropped purely for length, untracked:                6,529   (33.8%)
  of which  too short (<=20 chars):                  6,512   (mostly table/list noise)
            too long  (>=400 chars):                    17   (potential real evidence)
```

The great majority of the drop is short junk fragments from wikitext table/list remnants and is
plausibly correct behaviour to discard — but it is discarded *without being counted*, unlike
every other rejection path in this file, which the docstring specifically brags about auditing.
The smaller "too long" tail (17 of 19,306 here) is the more concerning share: this file already
fixed one real bug of exactly this shape once (`_unwrap_templates`'s docstring: Bruce Wayne's
190,687-character page reduced to 30 characters and recorded as an honest absence) — an
unsplit, newline-poor block of prose landing at or past 400 characters is silently thrown away
here with no trace, the same failure mode in miniature. Neither bucket is visible in
`evidence_for()`'s output (`feats`, `quantities`, `gate_rejected`) or in `roll()`'s summary.

Fix direction: increment a `length_dropped` (or split `too_short`/`too_long`) counter alongside
`rejected`, and surface it the same way `gate_rejected` is surfaced in `_show()` and the roll
summary.

### FINDING 7 — MEDIUM — fixed-name temp file on a file with genuinely concurrent writers
(VERIFIED-BY-READING; mechanism reproduced generically, not against live traffic)

`resolve_hosts()` (line 290-296) writes `data/WIKI_HOSTS.json` via:

```python
tmp = HOSTS + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(known, f, indent=1, ensure_ascii=False, sort_keys=True)
silence.replace_retry(tmp, HOSTS)
```

The comment directly above this (line 288-292) explicitly reasons about *readers* racing this
write and is why `replace_retry` is used at all — but the `tmp` name itself is the exact
anti-pattern `silence.write_json`'s own docstring says was fixed at twelve call sites across the
project on 2026-08-25: *"THE TMP NAME CARRIES PID AND THREAD ... Two writers of the same path
otherwise collide on the temp file itself, and the loser can replace the winner's target with a
partial file."* `resolve_hosts()` was apparently missed by that pass. `WIKI_HOSTS.json` is a
single shared file every caller of `resolve_hosts()` writes to — `feats.py --hosts`, `feats.py
--roll`, and any other script that imports and calls it — so two such invocations running at
once (plausible: this project's own guidance is to parallelise independent work across the
16-core machine) can interleave writes to the same `WIKI_HOSTS.json.tmp` path before either
`os.replace` runs, and the loser's `replace_retry` can install a torn or stale file over the
winner's. `evidence_for()`'s own per-entity cache write (line 803-807, same `path + ".tmp"`
pattern) has the identical issue but is lower-risk since each entity's cache lives at its own
path — collision there requires two processes mining the *same* entity at once.

Fix direction: use `silence.write_json(HOSTS, known, indent=1, ensure_ascii=False,
sort_keys=True)` in place of the hand-rolled tmp+replace_retry at both sites; it already exists,
is already imported (`import silence` at the top of the file), and is already used correctly
elsewhere in this very file (`remine()`, line 826).

### FINDING 8 — LOW — `discover()`'s `aplimit=500`/`srlimit=50` are real per-request caps with
no continuation loop; disclosed, not fixed (VERIFIED-BY-READING; not a new discovery, the file
already flags it)

`discover()` (line 348-361) requests at most 500 `allpages` results and 50 `search` results per
MediaWiki call and does not follow the `continue` token MediaWiki returns when more exist. This
is a genuine Hard Rule 0-shaped truncation (an entity with a very rich wiki presence could be
discovered "in part"), but unlike Finding 5/6/7 it is **not silent**: `_CAP_BOUND` counts every
time either cap actually binds, and `roll()`'s summary prints "discovery caps BOUND: ... (no
continuation is handled)" or "never bound" (line 911-917). The file's own comment frames this as
an open, deliberately-deferred question ("the remedy ... is only worth its cost if the cap ever
binds"), and per its own m82 measurement it had bound zero times as of run #19. I did not find
a way to independently re-measure this without a live network roll, so I report it at face value
as a disclosed, monitored limitation rather than a hidden one — flagged here only because the
prompt asks explicitly for any `aplimit`/`srlimit`, and it is worth the supervisor knowing it
remains structurally uncapped-but-unfixed, just visible.

### Other feats.py notes (no separate finding)
- `api()`'s 404 handling (line 132-135) correctly distinguishes "page absent" from other
  failures and records via `silence.note`, matching the module's stated discipline — verified
  correct, not a bug.
- `_unwrap_templates()` and `strip_wikitext()` were read in full; both match their extensive
  docstrings and no discrepancy was found between what they claim and what they do.
- Two-writer contract: `feats.py` never touches `data/records/*.json`; it only reads via
  `pipeline.records()` and writes to its own dedicated cache namespace
  (`data/feats/*`, `data/WIKI_HOSTS.json`). No violation of the pipeline/catalogue two-writer
  rule.

---

## manifest_builder.py

### FINDING 9 — MEDIUM — non-atomic write to a manifest file with a known concurrent reader
(VERIFIED-BY-READING)

`main()` writes the job manifest with a bare truncate-then-fill (line 436-437):

```python
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"jobs": all_jobs}, f, indent=2)
```

`out_path` is `output/index/manifest.json` (or `manifest.pilot.json`), which
`generate.py:load_json()` reads with a plain `json.load` and no fallback-on-parse-failure
(confirmed by reading `generate.py:45-50` — a `JSONDecodeError` there is not caught, so a reader
that lands mid-write crashes rather than silently substituting a default; this at least avoids
the worse "phantom empty manifest" failure mode, but it is still a crash any time
`manifest_builder.py` is rerun to refresh the manifest while `generate.py` (or `pipeline.py`,
which also reads/writes `output/index/manifest.json` per `pipeline.py:1749`) is active). This is
exactly the class of bug `silence.py`'s own docstring says was fixed at twelve other call sites
the same day this file was last touched ("TWELVE call sites across ten modules were writing
shared data/ and state/ files with a bare open(path, 'w') + json.dump ... A reader arriving in
the gap sees an empty or half-written file"). `manifest_builder.py` was not among the sites
fixed. The `report_path` writes (`output/index/unassigned_sources.md`, line 455 and 463) share
the pattern but are lower risk — markdown status text, not a file another live process parses
as JSON mid-run.

Fix direction: `silence.write_json(out_path, {"jobs": all_jobs}, indent=2)` in place of the bare
`open`+`json.dump` at line 436-437 (the module already has no `silence` import — would need
`import silence` added at the top alongside the existing `feats_index`/`address` imports it
already has, or reuse the existing `import silence` if present — checked: `manifest_builder.py`
does not currently import `silence` at all despite calling `silence.note` inside
`build_jobs_for_source` (line ~317), so it must already import it somewhere — confirmed at
line 32: `import silence`. So the fix is a one-line change, no new import needed.)

### Other manifest_builder.py notes (no separate finding)
- `pack_feats()` (line 155-207) is a genuinely correct pagination implementation: every
  oversized entity is sliced across multiple blocks and every slice is emitted, matching its
  extensive Hard-Rule-0 docstring. Verified by reading; no truncation found.
- `load_record()`'s slug-matching (line 66-101) was already hardened against a prior bug (the
  file's own comment documents it); re-derivation matches the stated ranking logic
  (bidirectional containment, closeness-ranked, prefix-anchored reverse arm). No new issue
  found.
- `max_per_call` (default 30, from config) chunks catalogue entries into multiple `chapter` jobs
  rather than dropping any — legitimate pagination, not a cap.
- `--pilot N` and `--only` are explicit, opt-in CLI narrowing flags, not silent truncation.

---

## reference.py

No correctness bugs, swallowed failures, or Hard Rule 0 violations found. This file is small,
hand-authored reference data plus rendering, and already uses `silence.write_json` for its one
shared output (`data/REFERENCE_ASSAYS.json`, with an explicit "ATOMIC" comment citing the
2026-08-25 fix). One minor robustness note:

### FINDING 10 — LOW — `shelfmark()`'s exception fallback hardcodes a 3-element list regardless
of the real `tier_key` length (VERIFIED-BY-READING; not currently triggered)

```python
try:
    ...
    for i in range(len(parts)):
        ...
except Exception:
    silence.note("reference.py:232")
    upper = ["?", "?", "?"]
```

If `NAVTREE.json` fails to load/parse, the fallback always produces exactly 3 `"?"` entries,
regardless of how many dot-separated parts `rec["tier_key"]` actually has. All three current
`REFERENCE` entries (Goku, Naruto, Luffy) use 3-part tier keys (`"1.6.1"`, `"4.2.0"`,
`"1.2.5"`), so this is not live-broken, but it is fragile: a future reference entity with a
4-part `tier_key` would silently render one fewer upper rung than it should on the (rare)
NAVTREE-load-failure path, with the failure already recorded via `silence.note` but the wrong
*shape* of fallback data going out regardless. Trivial fix: `upper = ["?"] *
len(rec["tier_key"].split("."))`.

---

## sevenfold.py

### FINDING 11 — HIGH — duplicate world designations silently overwrite each other in the final
shelving output, dropping ~1.6% of worlds with zero notice (REPRODUCED)

`build()`'s world-shelving stage (line 194-208):

```python
by_source = {}
for world in WS.build_all():
    by_source.setdefault(world["designation"].split("::")[0], []).append(world)

worlds = {}
for src, ws in by_source.items():
    base = coords.get(src)
    if base is None:
        continue
    names = [x["designation"] for x in ws]
    inner = shelve(names, {}, depth=len(WORLD_TIERS))
    for d in names:
        worlds[d] = dict(base)
        worlds[d]["multiverse"] = inner[d]["hyperverse"]
        worlds[d]["universe"] = inner[d]["xenoverse"]
```

`worldseed.build_all()` derives each world's `designation` as `f"{source}::{name}"`
(`worldseed.py:271`). Two different catalogue "Places" entries under the same source can
legitimately have the same `name` (e.g. "Candy Kingdom" mentioned as its own catalogue entry
more than once for the same source) and therefore the same designation string. Because `worlds`
is a plain dict keyed by `d` (the designation), the second world with a duplicate designation
silently overwrites the first — dict-key collision, no warning, no count.

Reproduced against the live repo:

```
total world entries from worldseed.build_all():   4,440
unique designations among them:                    4,368
distinct duplicated designations:                     69
extra (silently-overwritten) copies:                  72

>>> SF.build()'s `worlds` dict ends up with exactly 4,368 entries — 72 fewer than exist.

sample colliding designations:
  'Acquisitions Incorporated::Nentir Vale'  (x2)
  'Adventure Time::Candy Kingdom'           (x2)
  'Adventure Time::Ice Kingdom'             (x2)
  'Adventure Time::Fire Kingdom'            (x2)
  'Adventure Time::Wildberry Kingdom'       (x2)
```

`main()`'s `--write` path (line 264-269) writes this `worlds` dict straight into
`data/SEVENFOLD.json` via `silence.write_json` — atomically, correctly — but the *content*
being written has already silently lost 72 worlds by the time it gets there. The output is in
exactly the same shape (a `{designation: coords}` JSON object) whether it holds 4,440 or 4,368
entries, so nothing downstream can tell the difference from the file alone. This is a textbook
Hard Rule 0 violation even though no `[:N]` or `limit=` appears anywhere in this file — the cap
is an implicit dict-key collision rather than an explicit slice.

Fix direction: designations are not guaranteed unique by `worldseed.build_all()`'s own
construction (`src::name`, with no disambiguator for repeated names within one source); either
`worldseed.py` should make designations unique (append an index or the catalogue entry's page/id
for repeats), or `sevenfold.build()` should detect the collision (`if d in worlds:` before
overwriting) and record it via `silence.note`, folding both worlds into the same shelf slot
rather than dropping one, or giving the second copy a disambiguated key.

### FINDING 12 — LOW/INFORMATIONAL — a check that cannot fail, already self-flagged by the code
(VERIFIED-BY-READING — not a new finding, listed for completeness)

`main()`'s per-tier balance table (line 232-238) prints `"OK"` vs `"OVER SPAN"` based on
`hi <= SPAN`, but the code's own comment immediately above it states this plainly: *"`seams()`
already clamps every child count to SPAN, so 'OVER SPAN' cannot print for any input. This
displays a GUARANTEE, not a discovery."* I independently traced `seams()` (line 108-121) and
confirm the clamp is real (`k = max(1, min(span, len(block)))`, at most `k-1` cuts, so at most
`span` children) — the self-assessment is accurate. Recorded here only because the audit brief
asks specifically for tautological checks; this one is already disclosed in-repo as such and
needs no fix, only for the supervisor to know it was checked and confirmed accurate.

### Other sevenfold.py notes (no separate finding)
- `affinity_order()` and `shelve()`'s general balancing logic were read in full and match their
  docstrings; the empty-`weights` fallback to `sorted(members)` for the world-tier shelving is
  deliberate (no resonance weights exist at world granularity) and correctly implemented.
- `--write` output uses `silence.write_json`, atomic, correctly labelled "the m100 tail,
  2026-08-25" — no issue.

---

## tells.py

No correctness bugs, swallowed failures, caps, or contradictions found. This is a pure
detection/lint module (no writes, no network, no shared state) — its only job is producing
regex patterns and scanning text against them.

- `_anchor()`'s `pat[4:]` stripping of a literal `r"^\s*"` prefix was checked against every
  pattern in `STRUCTURAL` and `DISCOURSE`: every pattern that starts with `^\s*` is exactly
  4 characters of literal prefix (`^`, `\`, `s`, `*`), so the slice is correct for all current
  entries. This is fragile (a future pattern author who writes `r"^\s+"` or `r"^ *"` instead of
  the exact literal `r"^\s*"` would silently get the wrong split point rather than an error) but
  is not currently broken. Not raised as a numbered finding since no live incorrect behavior was
  found — mentioned for the supervisor's awareness only.
- The control-character self-check (line 33-37, mirrored in `feats.py` and `reference.py`) was
  verified to actually run at import time and correctly raises `SystemExit` if triggered; not
  re-tested for false negatives since it's a straightforward substring check.
- `scan()`, `prompt_section()`, and the demo self-check in `__main__` were traced end-to-end;
  behavior matches the docstrings.

---

## Summary table

| # | Severity | File:line | One-line description | Status |
|---|----------|-----------|------------------------|--------|
| 1 | CRITICAL | sweep_plan.py:95-119,194-198 | `missing(run)` can falsely report a genuinely-covered module as missing when another run's shard for that module has a later wall-clock timestamp | REPRODUCED |
| 5 | HIGH | feats.py:841-844, 277-278 | `roll()` silently drops sources with no resolved wiki host (8/210 right now) with zero counter | REPRODUCED |
| 11 | HIGH | sevenfold.py:194-208 | Duplicate world designations silently overwrite each other in the final shelving dict — 72/4,440 worlds (1.6%) dropped with zero notice | REPRODUCED |
| 6 | MEDIUM | feats.py:591-613, 704-723 | `mine()`/`by_axis()` drop ~34% of sentence fragments purely for length, untracked, contradicting the module's "keeps everything, including rejections" claim | REPRODUCED |
| 7 | MEDIUM | feats.py:293-296, 803-807 | Fixed-name (no pid/thread) temp file on `data/WIKI_HOSTS.json`, a file with genuine multi-process writers — the exact anti-pattern the project already fixed elsewhere | VERIFIED-BY-READING |
| 9 | MEDIUM | manifest_builder.py:436-437 | Bare `open("w")`+`json.dump` truncate-then-fill on `output/index/manifest.json`, read concurrently by generate.py/pipeline.py — same bug class fixed at 12 other sites project-wide but missed here | VERIFIED-BY-READING |
| 2 | MEDIUM | sweep_plan.py:85-91 | Shard files in `state/sweep_shards/` are never cleaned up, which is what makes Finding 1 an ongoing operational hazard rather than a one-off | VERIFIED-BY-READING |
| 8 | LOW | feats.py:348-361, 911-917 | `discover()`'s `aplimit=500`/`srlimit=50` per-request caps have no continuation loop; disclosed and measured (bound 0 times through run #19) but not fixed | VERIFIED-BY-READING |
| 10 | LOW | reference.py:226-232 | `shelfmark()`'s exception fallback hardcodes a 3-element `upper` list regardless of the real tier_key depth | VERIFIED-BY-READING |
| 12 | LOW/INFO | sevenfold.py:232-238 | "OVER SPAN" balance check is tautological by construction — already self-disclosed in the code's own comment, confirmed accurate | VERIFIED-BY-READING |
| — | GOOD | sweep_plan.py:85-91 | Shard-file collision safety across concurrent OS processes verified sound under real 6-process concurrent load | REPRODUCED (no bug) |
| — | GOOD | sweep_plan.py:148-165 | Aggregate `SWEEP_COVERAGE.json` fold-in race is real but correctly scoped as harmless — shards remain authoritative | VERIFIED-BY-READING (no bug) |

No two-writer-contract violations found in any of the six modules (none of them write to
`data/records/*.json` directly). No `threading.Lock`-on-shared-process-state issues beyond the
one already acknowledged and reasoned through in sweep_plan.py Finding 4.
