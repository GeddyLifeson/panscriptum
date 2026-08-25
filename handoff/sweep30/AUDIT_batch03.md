# Sweep 30 — Batch 03 Audit: `standards.py`, `reference.py`, `context_budget.py`, `burgs.py`, `halo.py`, `module_index.py`, `lognames.py`

Auditor: batch03 (read-only). All 7 files read top to bottom in full (2,678 lines total,
no sampling). No committed secrets, API keys, tokens, or passwords found in any of the
seven files.

Severity counts: **6 HIGH, 6 MED, 5 LOW** (17 numbered findings total).
Hard-Rule-0 cap findings: **0 real violations** — one false alarm cleared (`burgs.py`
message text lies about a cap that does not exist in the actual write path).

---

## `src/standards.py` (1,510 lines)

This file is the project's declared-floor instrument, and it is unusually self-aware —
its own comments narrate roughly a dozen previously-found instances of exactly the
"green on absent/unmeasured data" failure class this audit is asked to hunt for
(MAX_FABRICATION, the zero-denominator COMPLETENESS.json case, the PROVIDER_MODELS
staleness gate, the "counters moving" short-history fix, the charter-regression
in-progress state). That density of prior self-correction is real, and several of
those fixes are genuinely good. But the fixes were applied standard-by-standard, not
structurally — and the structural defect they were each independently patched around
is still present almost everywhere else in the file.

### 1. Nearly every standard silently VANISHES on a read/compute error instead of
   reporting UNMEASURED (HIGH, REPRODUCED)

`check()` builds `out` by appending one `_s(...)` dict per standard. In ~25 of the
~40 blocks, the `out.append(_s(...))` call sits **inside** a `try:` whose matching
`except Exception:` does nothing but `silence.note(...)` — no fallback append, no
`UNMEASURED` row, nothing. On any error (missing file, corrupt JSON, a KeyError in the
arithmetic, an import failure) that standard is not marked failed or unmeasured — it
simply does not exist in `out` for that call, which on a page of green rows is
indistinguishable from "everything is fine." This is the *exact* failure mode named
repeatedly in this file's own comments (e.g. the block starting `src/standards.py:880`:
"A STANDARD THAT DOES NOT EMIT IS WORSE THAN ONE THAT FAILS... The check that exists to
catch an unmeasured floor cannot see an absent one").

Confirmed by isolated reproduction (structural mirror of the `SHELFMARKS.json` block,
run in the scratchpad, no repo file touched):

```
silence.note('standards.py:shelfmarks') fired -- error was swallowed here
rows appended: 0
'shelfmarks are unique' present in output: False
```

Affected blocks (file:line of the `try:`, standard name(s), current severity):

- `standards.py:761` — "rosters that name their own fiction" (medium)
- `standards.py:786` — "shelfmarks are unique" (high)
- `standards.py:806` — "hand-built assays match the charter" (high)
- `standards.py:905` — "files that parse" AND "verifiers all run" AND **"the full audit
  is recent"** (all three high/medium — note the audit's own freshness gate is itself a
  casualty of the same failure it exists to catch)
- `standards.py:934` — "every source is fully catalogued" (high)
- `standards.py:981` — "the character sweep is newer than the catalogue" (high — see
  finding 2 below, which is worse than a vanish)
- `standards.py:1006` — "every running job is advancing" (high) — the file's own
  flagship standard, the one the docstring calls "the failure this whole library is
  built to refuse"
- `standards.py:1090` — "every pool failure is recognised" (high)
- `standards.py:1182` — "promotions have their spine codes amended" (medium) — has a
  correctly-handled `except FileNotFoundError` for the known "phase 7 hasn't run" case,
  but any *other* exception (e.g. corrupt JSON) still vanishes via the outer
  `except Exception`
- `standards.py:1203` / `1236` — the two Ollama liveness standards (high)
- `standards.py:1252` / `1284` — "every managed job is running" / "one instance of each
  job" (medium/high)
- `standards.py:1315` — "the published panel is fresh" (low)
- `standards.py:1328` — "model IDs their providers still serve" (high) — ironic: this
  block's whole design point (see its own comment) is "say when you can't measure," but
  that only covers the *stale-file* case; an unreadable/missing file still vanishes via
  the outer `except`
- `standards.py:872` — "the library's counters are moving" (high) — the short-history
  case was explicitly fixed to always emit, but a genuinely missing/corrupt
  `dashboard_history.json` still vanishes via the outer `except`

The one block that gets this right end-to-end is `standards.py:843-861`
("the automation reproduces the charter"): the file-read failure is caught by an
*inner* try that sets `reg = None`, and `charter_regression_verdict(None)` returns a
proper `(False, "never run")` pair that still gets appended. That is the correct
pattern and it should be applied to the ~13 blocks above (and any new ones): catch the
read/parse step only, and on failure append `_s(name, False, "UNMEASURED -- <reason>",
floor, order, ...)` instead of falling through to a bare `except` around the whole
block.

Suggested fix: split every wide `try: ... out.append(...) ... except: silence.note()`
block into an inner parse-only try (feeding a well-defined `UNMEASURED` fallback) and
an unconditional append, the same shape `charter_regression_verdict` and the
`MAX_FABRICATION`/COMPLETENESS-zero-denominator fixes already use elsewhere in this
same file.

### 2. "the character sweep is newer than the catalogue" reads GREEN on an empty input,
   not just absent (HIGH, REPRODUCED)

`standards.py:981-997`:

```python
sweep_m = os.path.getmtime(sweep_p)
newest_rec = max((os.path.getmtime(f) for f in
                  _g.glob(os.path.join(HERE, "data", "records", "*.json"))),
                 default=0.0)
lag_h = (newest_rec - sweep_m) / 3600.0
out.append(_s("the character sweep is newer than the catalogue", lag_h <= 1.0, ...))
```

If the glob matches nothing (empty/missing `data/records/`, or the glob pattern ever
stops matching after a directory restructure), `newest_rec` silently defaults to
`0.0`. `sweep_m` is a real epoch timestamp, so `lag_h` becomes a huge **negative**
number, which passes `lag_h <= 1.0` and reports `"fresh"` — a clean, HIGH-severity
green, generated from zero real evidence. Today `data/records/` holds 216 files so this
is currently dormant, but it is a live landmine: any future migration, a wiped
`records/` directory mid-repair, or a path typo turns "no data" into "definitely fresh"
rather than "UNMEASURED."

Reproduced arithmetically (read-only, current `CHARACTER_SWEEP.json` mtime, simulated
empty glob):

```
lag_h = -496574.53
holds (lag_h <= 1.0) = True
```

This is a second, distinct instance of green-by-absence layered on top of finding 1 —
even if the whole block were made to always emit (fixing finding 1), the arithmetic
itself would still need an explicit `if not glob_matches: UNMEASURED` guard, because
`default=0.0` is doing exactly what a `max(x, 1)` div-by-zero guard was already called
out (in this same file's own comments, `standards.py:440-455`) as the wrong shape for
exactly this reason.

Suggested fix: `default=None`, then branch to an explicit UNMEASURED row when
`newest_rec is None`.

### 3. Four more standards vanish via a truthiness guard, not an exception (HIGH,
   REPRODUCED by inspection)

Same defect family as finding 1, different code shape — an `if <thing>:` wraps the
`out.append(...)` calls, so an empty/missing input skips the append instead of
reporting UNMEASURED:

- `standards.py:538` `if read:` gates **four** standards at once: "chunks nobody
  answered" (high), "corpus read finishes inside a day" (medium), "feats per chunk"
  (medium), and **"corpus read is progressing"** (high — the file's own headline
  reader-liveness check). If `jobs.get("corpus read")` is `None` (reader never logged a
  progress line — crashed at start, never launched, config broken) all four vanish
  together instead of any one of them going red.
- `standards.py:571` `if roll:` gates "page roll complete" (low).
- `standards.py:582-583` `if cov:` gates "coverage figures are current" (low) and
  "entries settled" (low).
- `standards.py:597` `if src.get("total"):` gates "sources with a reachable wiki"
  (medium).

Why it matters: this is the same class of bug the file's docstring devotes several
paragraphs to (`standards.py:880-903`, the "counters moving" fix), applied nowhere else
in the file despite the pattern recurring at least four more times.

Suggested fix: same shape as finding 1 — replace the truthiness guard with an
unconditional append that reports `UNMEASURED -- no "<job>" job seen yet` (etc.) when
the input is absent, instead of skipping the row.

### 4. `every declared floor is measured` self-check cannot see any of findings 1-3
   (MED, REPRODUCED by inspection)

`standards.py:1415-1436` greps the file's own source for each `MIN_/MAX_` constant name
appearing (word-bounded, comment-stripped) inside `check()`'s body, and reports a
constant "measured" if the name is referenced anywhere. This proves a constant is
*read*, not that the row built from it is *unconditionally appended*. Every constant
implicated in findings 1-3 above (`MAX_SHELFMARK_COLLISIONS`, `MIN_CATALOGUE_COVERAGE`,
`MAX_SWEEP_AGE_H`, `MAX_JOB_SILENCE_MIN`, etc.) passes this self-check today, because
the code path that vanishes the row still mentions the constant by name on the way to
vanishing it. The file's own comment already says as much about the closely-related
MAX_FABRICATION bug ("A source-grep cannot tell a used constant from an unreachable
one") but the lesson was applied only to that one constant, not generalized into the
self-check itself.

Suggested fix (behavioural, not textual): replace or supplement the source-grep with
what `verify_math.py`'s own stated NEXT_STEPS direction already calls for — call
`check()` against a synthetic/empty `state` and assert every declared standard name
still appears in the output (as UNMEASURED if need be), the same technique
`charter_regression_verdict` is already unit-tested with.

### 5. `JOB_WATCH` (`state/job_progress.json`) read-modify-write uses a fixed-name
   temp file on a file with multiple concurrent writers (HIGH, REPRODUCED —
   confirms and sharpens the flagged open item at standards.py:1018-1022)

`standards.py:1008-1062`:

```python
prev = {}
if os.path.exists(JOB_WATCH):
    with open(JOB_WATCH, encoding="utf-8") as f:
        prev = json.load(f)
...
cur[job] = {"size": size, "at": stamp}
...
tmp = JOB_WATCH + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(cur, f)
silence.replace_retry(tmp, JOB_WATCH)
```

`standards.check()` is called from `dashboard.py`, `publish.py`, and `foreman.py`
(confirmed by grep — `src/dashboard.py:551`, `src/publish.py:271`,
`src/foreman.py:402/567/1134`) — three independent, concurrently-running processes per
the project's own supervision architecture. This is precisely the shape
`silence.write_json`'s own docstring (`src/silence.py:290-309`) says was fixed
project-wide on 2026-08-25: "THE TMP NAME CARRIES PID AND THREAD, which the older
hand-rolled `path + '.tmp'` sites did not. Two writers of the same path otherwise
collide on the temp file itself, and the loser can replace the winner's target with a
partial file." The `JOB_WATCH` block here still uses that exact older hand-rolled
`path + ".tmp"` shape rather than `silence.write_json`, so it was apparently missed by
(or added after) that sweep. There is also a genuine read-modify-write race on top of
the temp-file collision: two processes can both read the same `prev` snapshot, compute
different `cur` dicts from their own timing, and the loser's write overwrites the
winner's — which can reset or corrupt the "how long has this job been silent" clock the
`job_stamp()` carry-forward logic (`standards.py:286-295`) exists specifically to make
correct. Read-modify-write races don't crash; they intermittently make a stalled job
look freshly-stamped, silently defeating `MAX_JOB_SILENCE_MIN`.

Suggested fix: `silence.write_json(JOB_WATCH, cur)` in place of the three lines above —
it is a straight drop-in replacement (same shared-file, same atomic-replace intent)
and eliminates both the temp-file collision and, via the PID/thread-qualified tmp name,
most of the practical impact of the read-modify-write race.

### 6. The probe/unexpected swallowed-failure split is a hardcoded 6-substring list, and
   one entry matches zero call sites today (MED, REPRODUCED)

`standards.py:644-647`:

```python
probe = sum(v for k, v in ledger.items()
            if any(t in k for t in ("endpoint.py:detect", "endpoint.py:fetch",
                                    "hostcheck.py:probe", "hostcheck.py:candidates",
                                    "hostcheck.py:relevance", "scout.py:verify")))
```

Grepped every `silence.note(...)` call site in `endpoint.py`, `hostcheck.py`, and
`scout.py` today. Five of the six substrings correctly match real call sites via
substring containment (`"endpoint.py:detect"` matches both `detect-api` and
`detect-raw`; `"endpoint.py:fetch"` matches `fetch_raw`, `fetch_raw-absent`, etc.;
`"hostcheck.py:relevance"` matches `relevance-wikitext`). `"hostcheck.py:candidates"`
does not match anything: `hostcheck.py`'s `candidates()` function
(`hostcheck.py:267-369`) contains no `try`/`except` and calls `silence.note` nowhere,
so this entry in the classification list is currently dead weight. It is harmless
today (matching nothing changes no count either way), but it demonstrates the
classification list has already drifted out of sync with the code it is meant to
describe, and nothing enforces the two staying in sync — a future refactor could add a
genuinely-probing failure path under a name this list doesn't cover, and it would
silently count as a "real" swallowed failure (or vice versa, a real fault could get
misclassified as probe noise if it happens to share a substring).

Suggested fix: derive the probe-class list from the actual call sites (e.g. a small
shared tuple imported by both the instrumented modules and this classifier) rather than
duplicating site names as free-floating string literals in a third file.

### Clean

`ollama_runner_up`, `ollama_token_flow`, `fandom_ipv4_reachable`, `job_stamp`, and
`charter_regression_verdict` are all well-isolated, testable pure/near-pure functions
with the fail-closed (`None`/`False`-not-reported-as-fault) discipline the file's
docstring asks for, and each is backed by a narrated, dated incident in its own
docstring. The severity-ranking (`work_orders`, `report`'s `_rank` dict) is correct and
consistent between the CLI report and the dashboard. No Hard-Rule-0 cap violations
found anywhere in this file — every roster/list operation found (`sorted(...)`,
`", ".join(...)`) is either unbounded or an explicitly-labelled display truncation on a
short summary string (e.g. `_pending` names joined then `[:120]` at
`standards.py:1188`, or `err_text[:80]` style excerpts), never a slice on the
underlying data that a floor's boolean is computed from.

---

## `src/hostcheck.py` cross-reference (not in batch, read only to verify finding 6)

Confirmed no `silence.note("hostcheck.py:candidates")` call site exists anywhere in the
file; `candidates()` (`hostcheck.py:267`) has no exception handling at all. Not part of
this batch's deliverable, cited only as evidence for standards.py finding 6.

---

## `src/reference.py` (359 lines)

Clean. Hand-built reference Assay sheets for Goku/Naruto/Luffy used to calibrate the
automated pass, with narrated provenance per axis line. Writes `REFERENCE_ASSAYS.json`
via `silence.write_json` (`reference.py:333`) — the correct atomic pattern, and it's
explicitly commented as such ("ATOMIC: standards.py and zfighters.py both read
REFERENCE_ASSAYS.json"). `compute()` iterates every axis in `rec["axes"]` (11 fixed
axes, no slicing). No caps on any roster (the `REFERENCE` dict is 3 fixed, deliberately
hand-curated entities — not a mined/derived roster, so a fixed size is correct here,
not a violation).

### 7. `shelfmark()`'s except-all fallback can mask a real bug as "unknown" (LOW,
   HYPOTHESIS — not tested)

`reference.py:232-242`:

```python
try:
    nav = json.load(open(os.path.join(HERE, "data", "NAVTREE.json"), encoding="utf-8"))
    ...
except Exception:
    silence.note("reference.py:232")
    upper = ["?", "?", "?"]
```

Any exception — missing file, corrupt JSON, but also a genuine `KeyError`/`TypeError`
from malformed `NAVTREE.json` structure — degrades to `["?", "?", "?"]`, which is
indistinguishable on the printed card from the intentional "the fiction does not name
this rung" case the file's own comment describes as correct behavior. A structural bug
in `NAVTREE.json` (e.g. from the `module_index.py`-adjacent staleness issues found
elsewhere in this batch) would silently read as "unknown cosmography" rather than as a
loud parse failure. Low severity because the blast radius is cosmetic (one shelfmark
line reads as unattested rather than wrong), and this is explicitly the designed
degrade-to-`?` behavior for the *expected* failure mode (missing file); it just doesn't
distinguish that from an *unexpected* one.

### Clean (rest of file)

`compute`, `citation`, `card`, `_vernacular`, and `main` are otherwise straightforward
and correctly derive every printed number from `A.assay()`'s real output rather than
recomputing or duplicating it.

---

## `src/context_budget.py` (279 lines)

Clean — no findings. This module computes a token/character budget derived from the
live `num_ctx` window rather than a hardcoded constant, exactly the shape Hard Rule 0
prefers (measure and adapt rather than cap). `content_budget_chars()` can legitimately
return zero or negative and its own docstring insists callers must treat that as "raise,
don't clamp" — and `assert_fits` (`context_budget.py:191-206`) does exactly that,
raising `ContextOverflow` rather than silently truncating or proceeding. Verified this
is actually wired to a raise, not a log-and-continue, at the one production call site
(`generate.py:132-133`, `_CBUD.assert_fits(...)` called unconditionally, no
try/except around it there). The two calibration constants (`JOB_OVERHEAD_CHARS`,
`METADATA_INFLATION`) both round *up*/*conservative* per their own measured-data
comments, consistent with the file's stated pessimism-on-purpose design. No caps on any
roster or listing.

---

## `src/burgs.py` (236 lines)

### 8. `--write` prints "sample of 50 worlds" while writing every world — the message
   is stale/wrong, not the data (MED, REPRODUCED — confirms and clarifies the flagged
   open item)

`burgs.py:190-230`:

```python
worlds = WS.build_all()          # every world; Hard Rule 0
...
for w in worlds:
    seed = AS.map_seed(w["seed"])
    bs = burgs_for(seed, w["features"])
    per_world[w["designation"]] = bs
    total += len(bs)
...
if args.write:
    p = os.path.join(HERE, "data", "BURGS_SAMPLE.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(per_world, f, indent=2,          # every world; Hard Rule 0
                  ensure_ascii=False)
    print(f"\nwrote {p} (sample of 50 worlds; the rest regenerate on demand)")
```

`worlds` is unsliced (`WS.build_all()`, commented "every world; Hard Rule 0"), the loop
that builds `per_world` is unsliced, and the `json.dump` call writes the entire
`per_world` dict with no `[:N]` anywhere. This is **not** a Hard-Rule-0 violation — the
actual write is fully compliant, every world's burgs land in the file. The bug is that
the printed confirmation message is factually wrong and describes a cap that does not
exist in the code path it is printed from (almost certainly a leftover from an earlier
version of this script that did write only a sample of 50, before it was fixed to write
every world per Hard Rule 0). This is actively misleading in the wrong direction for a
project this deliberate about caps: a future reader (human or another auditor) trusting
the console output over the code would falsely conclude a cap still exists here, or
conversely, if the write path later regresses to a real cap, the message would keep
reading as an innocuous, already-known, intentional sample rather than a new
regression.

Suggested fix: `print(f"\nwrote {p} ({len(worlds):,} worlds, {total:,} burgs)")` or
similar — report the real count, not a stale literal.

### 9. `BURGS_SAMPLE.json` write is not atomic (LOW)

`burgs.py:226-229` writes directly with `open(p, "w")` + `json.dump`, bypassing
`silence.write_json`/`replace_retry`. Confirmed single-writer (grepped the whole `src/`
tree — nothing else references `BURGS_SAMPLE.json`, and this file is only ever invoked
manually via `--write`, not from the supervisor stack), so this is not a live race like
standards.py finding 5 — but it is inconsistent with the project's own stated
"the one correct way to write a shared file" convention, and a crash mid-write (or a
future automated caller) would leave a truncated file with no atomic-replace safety
net. Low severity given the current single-writer, manual-invocation-only usage.

### Clean (rest of file)

`burg_count`, `largest_city`, `classify`, `burgs_for`, and `burg_link` are all pure
functions with clearly-derived (not invented) numbers, correctly documented rationale
for the rank-size-rule approach, and no caps on the settlement roll itself (`range(1,
(limit or n) + 1)` — `limit` defaults to `None`, so `main()`'s only use of it
(`burgs.py:218`, console preview) is an explicit, opt-in, display-only `--limit` CLI
flag, not a silent truncation of stored data).

---

## `src/halo.py` (179 lines)

Clean — no findings. Structurally near-identical to `reference.py`: three hand-curated
entities (Precursors, Gravemind, Ur-Didact — a fixed, deliberately-curated roster, not
a mined one, so no Hard-Rule-0 concern), each Assay fully cited per axis, correctly
computed via `A.assay()`. Writes `HALO_ASSAYS.json` via `silence.write_json`
(`halo.py:171`) — correct atomic pattern, explicitly commented "ATOMIC -- the m100
tail, 2026-08-25." The one truncation in the file, `d["cited"][:54]` at `halo.py:169`,
is an explicit `--full` CLI console-table column width limit on a print statement, not
a write path — display-only per the lens's own carve-out.

---

## `src/module_index.py` (84 lines)

### 10. Docstring claims "87 modules" / "eighty-seven headers"; `src/` holds 103 today
   (LOW, REPRODUCED — confirms and updates the flagged open item)

`module_index.py:2,6`:

```
"""MODULE_INDEX — the map of the 87 modules, generated from their own first lines.
...
`handoff/MODULE_INDEX.md`, grouped by the stage of the machine they serve, so onboarding is a
read of one page instead of eighty-seven headers.
```

`ls src/*.py | wc -l` → **103** today (the flagged open item said 101; the count has
grown further since that item was filed, which is itself evidence of how quickly this
kind of stale-count docstring drifts). This has no functional effect — `main()`
computes `len(mods)` dynamically at `module_index.py:52-53,77` and prints/generates the
real count every run, so the generated `handoff/MODULE_INDEX.md` output itself is
always accurate. The defect is purely in the two hardcoded numbers inside the
docstring, which will keep drifting every time a module is added or removed and were
apparently never updated after the first write.

Suggested fix: either drop the number from the docstring entirely (say "the modules,"
matching the generated page's own title, which correctly avoids hardcoding a count) or
compute it (`len(glob.glob(...))`) into an f-string docstring note — though the latter
is unusual for a module docstring and probably not worth the complexity versus simply
removing the stale number.

### Clean (rest of file)

`first_line()` fails closed to `"(unparseable)"` on a parse error rather than crashing
or silently omitting the module, and correctly logs via `silence.note`. `GROUPS`
membership and the "Everything else" fallback (`module_index.py:68-74`) together
guarantee every module in `src/` appears exactly once in the generated page — verified
by inspection: `placed` accumulates every named module actually found, `rest = sorted(
set(mods) - placed)` catches everything not in a named group, so no module can be
silently dropped even if a `GROUPS` list drifts out of sync with `src/`'s real
contents (which finding 10 shows it currently has, at least in the docstring's stated
count — though the `GROUPS` *membership* lists were spot-checked against `ls src/*.py`
and every named module in every group still exists).

---

## `src/lognames.py` (37 lines)

### 11. Two of six job log filenames are still hardcoded string literals at their write
   sites instead of importing the shared constant, defeating the module's own stated
   purpose (MED, REPRODUCED)

The file's docstring states the whole reason it exists: "They used to be string
literals repeated in overnight.py and dashboard.py independently — one rename in one
place and the whole observability chain went quietly blind... A constant shared by
writer and reader cannot drift." That guarantee does not actually hold for two of the
six jobs it defines:

- `lognames.PIPELINE = "pipeline_auto.log"` — but `overnight.py:407` (the `STANDING`
  table), `overnight.py:772` (`start("pipeline", ...)`), and `overnight.py:808`
  (`run("pipeline", ...)`) all pass the **literal string** `"pipeline_auto.log"`
  directly, never importing `LN.PIPELINE`.
- `lognames.RECATALOGUE = "recatalogue.log"` — but `foreman.py:594`
  (`ON.start("catalogue gap", ..., "recatalogue.log")`) passes the **literal string**
  directly.

By contrast, the `READ` and `ROLL` jobs in the same two files correctly import and use
`LN.READ` / `LN.ROLL` (`overnight.py:790,802`). The values happen to match today (no
active bug), but the coupling the module exists to provide is broken for these two
jobs: `standards.py`'s stall-detector loop
(`standards.py:1021`, `for fn, owner in sorted(LN.OWNER.items())`) and
`dashboard.py`'s panel both read the filename **from `lognames.py`**, while the actual
writers for `pipeline` and `recatalogue` do not — so if either constant is ever renamed
in `lognames.py` (the one place the docstring says is now safe to edit), the stall
detector and dashboard would silently start watching a file the real process never
writes, reintroducing precisely the "quietly blind" regression this module's own
docstring says was fixed. `SWEEP` and `CALIBRATE` were checked too and are correctly
imported (`foreman.py:608,665`), so this is specifically a `PIPELINE`/`RECATALOGUE`
gap, not a file-wide one.

Suggested fix: `overnight.py:407,772,808` should use `LN.PIPELINE` and
`foreman.py:594` should use `LN.RECATALOGUE`, matching the pattern already used for
`READ`/`ROLL`/`SWEEP`/`CALIBRATE`.

### Clean (rest of file)

`OWNER`'s command-line fragments were checked against `overnight.running()`'s matching
semantics (`fragment in cmd` substring match against the live command line) and are
each specific enough to avoid the false-positive collision the file's own comment
warns about (e.g. `"feats.py --roll"` vs. a bare `"feats.py"` invocation for a
different purpose).

---

## Summary table

| # | File:line | Standard/function | Severity | Status |
|---|---|---|---|---|
| 1 | standards.py: ~25 blocks | (see list above) | HIGH | REPRODUCED |
| 2 | standards.py:981-997 | character sweep freshness | HIGH | REPRODUCED |
| 3 | standards.py:538,571,582,597 | 4 truthiness-guarded blocks | HIGH | REPRODUCED (inspection) |
| 4 | standards.py:1415-1436 | "every declared floor is measured" self-check | MED | REPRODUCED (inspection) |
| 5 | standards.py:1008-1062 | JOB_WATCH fixed-tmp race | HIGH | REPRODUCED |
| 6 | standards.py:644-647 | probe-class substring list, 1 dead entry | MED | REPRODUCED |
| 7 | reference.py:232-242 | shelfmark() except-all masks bugs as "unknown" | LOW | HYPOTHESIS |
| 8 | burgs.py:230 | "sample of 50" message vs. full write | MED | REPRODUCED |
| 9 | burgs.py:226-229 | non-atomic write, single-writer today | LOW | REPRODUCED (inspection) |
| 10 | module_index.py:2,6 | stale "87 modules" (actually 103) | LOW | REPRODUCED |
| 11 | lognames.py (via overnight.py/foreman.py) | PIPELINE/RECATALOGUE literals not imported | MED | REPRODUCED |

context_budget.py and halo.py: clean, no findings.

### Answering the explicit ask: "does every declared floor get measured and emitted,
and can any standard read green on unmeasured/absent input?"

No, and yes, respectively. Findings 1-3 show roughly 20 of the ~40 standards in
`check()` can fail to emit a row at all on absent/corrupt input (never mind reading
green — they simply vanish, which the file's own docstring already argues is worse).
Finding 2 shows at least one standard (character-sweep freshness) does not merely
vanish but actively computes and reports a HIGH-severity **green** from a
zero-evidence input, reproduced with real numbers. The self-check meant to catch
exactly this (finding 4) cannot, because it verifies a constant is referenced in
source text, not that its row is unconditionally emitted.
