# AUDIT — batch 14 (run30)

Files: `src/overwatch.py`, `src/derivation.py`, `src/health.py`, `src/estate.py`,
`src/tempus.py`, `src/tells.py`, `src/physics.py`. Every line of every file was read top to
bottom. No repo file was edited or written to; reproductions ran against a scratch temp dir
(`.../scratchpad/health_repro/`) or as pure in-memory simulations of the exact code paths cited.

**Secrets: none found.** Grepped all seven files for api/secret/password/token/AWS-key/PEM
patterns — clean.

---

## 1. `src/health.py` — highest-traffic shared file in the project

### H1 [HIGH] [REPRODUCED] `flush()` (lines 85–144) holds NO LOCK across its read-merge-write-clear cycle — lost updates confirmed

`_LOCK` (a `threading.Lock`, line 62) is acquired only inside `record()` (line 76). `flush()`
itself (lines 85–144) never takes `_LOCK`: it reads `LEDGER_PATH` off disk, merges the in-memory
`LEDGER` Counter into it, writes the tmp file, replaces, and only then calls `LEDGER.clear()`
(line 123) — all *outside* any lock. Any `record()` call that lands between the merge and the
`clear()` is added to the shared `LEDGER` Counter, survives to be seen by `clear()`, and is wiped
with nothing ever persisted for it. This is true even within a *single process* across threads
(the lock only serializes `record()`'s own increment, not `flush()`'s compound operation), and
`_LOCK` gives **zero** protection at all between the "one-shot subprocesses" the file's own
docstring (lines 107–109) says call `flush()` "every 25 records and again at exit" — those are
separate OS processes with independent `threading.Lock` instances.

Reproduced with a scratch script (`health_repro/repro.py`) that monkeypatches
`health.LEDGER_PATH`/`SAMPLES_PATH` into a scratch dir and stalls `json.dump` mid-`flush()` via a
patched `json.dump`, then has a second thread call `health.record()` twice during the stall:

```
on disk: {'kindA:from-A': 1}
LEDGER in memory after both threads (should be empty if flush cleared everything): {}

REPRODUCED: thread B's 2 record() calls are on disk NOWHERE and LEDGER is now
empty -- flush()'s unconditional LEDGER.clear() discarded increments that arrived
during its own read-merge-write window.
```

**Why it matters:** this is the exact defect class the whole `silence`/`health` apparatus exists
to eliminate — a failure that gets recorded in memory and then silently vanishes, with the
counters and the evidence-bag samples both gone and nothing at all left to say it happened.

**Fix:** hold `_LOCK` across the *entire* body of `flush()` (not just the merge computation), and
for the cross-process case, either serialize flush via a lockfile, or adopt the same
digest-before-write / merge-on-conflict pattern `overwatch.py` already built for its own ledger
(`_reconcile_with_disk`/`_merge_ledgers`, see below) rather than a blind read-modify-write.

### H2 [HIGH] tmp filenames are not process/thread-qualified — exactly the collision class `silence.write_json` was built to fix

`flush()` writes `tmp = LEDGER_PATH + ".tmp"` (line 119) and `stmp = SAMPLES_PATH + ".tmp"`
(line 138); `reopen_stranded()` writes `tmp = path + ".tmp"` (line 361). None include the PID/
thread suffix. `silence.write_json`'s own docstring (`src/silence.py` ~lines 290–301) documents
that this *exact* pattern was found and fixed at twelve call sites across ten modules on
2026-08-25 specifically because "two writers of the same path otherwise collide on the temp file
itself, and the loser can replace the winner's target with a partial file." `health.py`'s three
writers of the two busiest state files in the kit (`failures.json`, `failure_samples.json`,
`PIPELINE_STATE.json`) were never converted and still use the pre-fix idiom. `replace_retry`
makes the *final rename* atomic, but does nothing about two writers racing to fill the *same*
`.tmp` path before that rename.

**Fix:** switch all three call sites to `silence.write_json(path, obj)`, which already does the
pid+thread-qualified tmp name plus `replace_retry`.

### H3 [HIGH] `reopen_stranded()` (lines 310–371) writes the whole `PIPELINE_STATE.json` back with no staleness check, while its own comment says it runs live against the pipeline

The function reads the entire state file, mutates only `st["done"]["entrypass"]`, and writes the
entire blob back (lines 361–369) — no digest comparison against what's currently on disk, no
merge. Its own comment (lines 358–360) says: *"it is invoked precisely when a pipeline may be
live, since that is when batches strand"* — i.e. the tool explicitly expects `pipeline.py` to be
writing the same file concurrently, yet does nothing to detect or merge a concurrent change, unlike
`overwatch.py`'s own ledger writer (`save()`/`_reconcile_with_disk`, added at m40 for this precise
reason — see O-section below). If `pipeline.py` records a new `done` key or a new `failed` entry
between this read and this write, that update is silently discarded by the stale full-snapshot
overwrite.

HYPOTHESIS — not reproduced (would require driving a live `pipeline.py` write concurrently with
`health.py --reopen --go`, which is out of scope for a read-only audit and risks corrupting real
state), but the mechanism is code-confirmed and structurally identical to the H1 race already
reproduced.

### H4 [HIGH] `flush()`'s SAMPLES write failure (lines 143–144) is completely unrecorded — verified via the project's own `silence.audit()`

```python
except Exception:
    pass          # the evidence bag must never break the ledger write
```

Ran `silence._handlers("src/health.py")` (the project's own instrumentation-gap detector) against
this file directly:

```
{'line': 143, 'type': 'Exception', 'silent': True}
{'line': 245, 'type': 'OSError', 'silent': True}   # false positive -- see note below
```

Line 143 is a genuine silent swallow: no print, no counter, no `silence.note()` call — nothing.
This is the one handler in the file whose entire mission statement is "make failures loud...
nothing raises, nothing counts, and so every one of them costs a full investigation" (lines
17–20) that does exactly that. It is also inconsistent with the file's *own* convention
elsewhere — the three other failure paths in this same file all correctly `print(..., file=sys.stderr)`
(lines 100–101 ledger-unreadable, 330–331 PIPELINE_STATE-unreadable, 369 write-denied).
`silence.py`'s `SKIP_FILES = {"silence.py", "health.py"}` (silence.py, the rewriter section)
deliberately excludes `health.py` from auto-instrumentation to avoid `health.record()` recursing
into itself — a legitimate reason not to call `silence.note()` here — but that doesn't excuse
skipping the plain `print(..., file=sys.stderr)` the file uses everywhere else.

(Line 245's `except OSError: unreadable += 1` inside `check_caches()` is flagged "silent" by
`silence.audit()`'s keyword heuristic because it doesn't call `record`/`print`/etc. literally, but
the count *is* surfaced downstream via the `f"{unreadable} files cannot be stat'd"` line — a false
positive in the audit tool, not a real gap. Noted for completeness, not filed as a finding.)

**Fix:** add a one-line `print(f"health: could not persist failure_samples.json ({...})",
file=sys.stderr)` inside that `except`.

### M1 [MEDIUM] `check_caches()` (lines 220–253): the `files[:200]` sample cap's stated performance rationale is stale, and it leaves a real blind spot

The comment (lines 234–238) justifies sampling 200 files per host by saying a full scan would mean
"reading gigabytes of page text" and "pushed a cycle past five minutes." That describes the *old*
parse-based check this replaced. The *current* code only calls `os.path.getsize()` — a metadata
stat, not a content read. Measured directly against the live corpus:

```
total files across feats+readfeats: 97314   hosts>=25files: 148
full getsize-all-files elapsed: 3.74s
```

Stat-ing every file in the entire corpus (not just the capped hosts) takes under four seconds
total. The 200-cap therefore buys negligible speed today, while creating a real detection gap:
a host directory whose first 200 files (in `glob`'s OS-dependent listing order) are healthy but
whose *later* entries are systematically empty (e.g. a partial re-scrape that only broke midway
through a large host) would report clean, exactly the class of "broken cache reads as honest
absence" defect this check exists to catch.

**Not the cause of the current preflight failure** — see verification below, that one is a true
positive. This is a latent risk, not an active bug. Given the measured cost, recommend dropping
the cap entirely (scan every file — ~4s for the whole tree) or at minimum reading a scattered
sample rather than only the head of the glob order.

### Verification of the two currently-failing preflight checks (as requested)

**`caches empty in a way that means broken` / `feats/www_dandwiki_com`: TRUE POSITIVE.**
Spot-checked five files on disk directly:
```
Ability_Score_Improvement.json: 185 bytes
Absolue_Focus.json: 173 bytes
Absolute_Destruction.json: 180 bytes
Absolute_Protection.json: 179 bytes
Absolute_Telepathy.json: 178 bytes
```
All well under `EMPTY_BYTES = 400`. The check is measuring exactly what its docstring says
(host directory is systematically holding empty entries) and is correct here, not a check bug.

**`state consistency` / 621 entries stranded: TRUE POSITIVE, and the check's own root-cause
comment is accurate.** `check_state()` keys batches as `f"{r['source']}#{start}"` over
`range(0, len(E), P.ENTRY_BATCH)` and tests `e.get("catalogued")` — grepped `src/pipeline.py`
directly and confirmed `phase_entrypass` uses the *identical* key construction
(`f"{r['source']}#{start}"`) and sets the *identical* field (`batch[i]["catalogued"] = True`,
pipeline.py:1244). The check is reading the same semantic the writer produces, not a mismatched
field name — its diagnosis (a positional done-marker over a list the cataloguing side mutates) is
technically sound, not a false alarm.

### Clean

`record()` itself is small and correct. `preflight()`'s per-check exception handling (lines
383–398) is a genuinely good pattern worth naming: a check that *raises* is reported as a FAIL
with the exception text, never silently read as "ok" — this is exactly the "a check that cannot
fail" trap done right, and it's worth pointing at as the model for the estate.py erratum-check
fix above. `check_control_chars()` and `check_api_paths()` are both correct and appropriately
scoped (the latter tests one representative host per *family*, which is the right unit given the
original defect was a whole-family wrong API path, not a per-host outage — not a Hard Rule 0
violation).

---

## 2. `src/overwatch.py`

### O1 [HIGH] [REPRODUCED] Confirms known open item — dedup at line 652 is by fingerprint KEY EXISTENCE, not state; a retired/closed finding can never reopen

```python
for f in found:
    fid = _fingerprint(m, f)
    if fid in led["findings"]:      # line 652 -- existence only, ignores current state
        continue
    f.update({"state": "open", "first_seen": time.time(), "digest": d})
    led["findings"][fid] = f
    fresh += 1
```

A finding is fingerprinted from `module|symbol|actual[:80]` (`_fingerprint`, line 208–210). Once
that key exists in `led["findings"]` — whether its current `state` is `"open"`, `"retired"` (file
changed since filing, round_once lines 623–629), or `"closed"` (auto-triage refuted it,
`verify_open` lines 490–494) — any future rediscovery of the identical defect is silently
dropped: the `continue` fires regardless of state, so the stale entry is never overwritten and
never reopened. Simulated the exact sequence in isolation:

```
fresh findings added on rediscovery: 0
current state of the fingerprint: retired
REPRODUCED: a still-real, rediscovered defect stays retired forever
```

**Why it matters:** a defect that gets *reintroduced* (a bad revert, a merge that undoes a fix) or
whose original "refuted" verdict was wrong (see O-below, the auto-triage model can be wrong even
though it can't silently read a failure as refuted) will never surface again through this
pipeline, permanently, with no error and no trace that anything was suppressed.

**Fix:** gate on state, not existence — e.g. only `continue` when the existing entry's state is
`"open"`; allow re-opening (perhaps incrementing a `rediscovered_n` counter) from `"retired"` or
`"closed"`.

### O2 [HIGH] `write_report()` caps the open-findings list shown in WATCH.md at 40, while stating the true (larger) count in the header — a Hard-Rule-0 "finding list" truncation

```python
lines.append(f"**{len(open_f)} open** ({len(hi)} high). Newest first.")
...
for f in sorted(open_f, key=lambda x: (-(x.get("severity") == "high"),
                                       -x.get("first_seen", 0)))[:40]:
```
(lines 570–573). `WATCH.md` is, by the module's own docstring, "written for a human to read in
ten seconds" and is the sole deliverable a human or downstream process reads to answer "what's up
and what should be fixing it." Findings 41+ are real, open, and simply never appear in that
artifact — recoverable only by opening the raw `data/OVERWATCH.json` ledger directly, which
defeats the point of having a report at all. This is precisely what Hard Rule 0 names as an
example: a "finding list" capped after ranking. Ranking here is fine (severity then recency,
matches the rule's explicit allowance); the truncation after it is not.

**Contrast, in the same file:** `main()`'s `--show` path (lines 697–702) prints *every* open
finding with no cap — proof the module already has a correct, uncapped precedent for the exact
same data, one function away.

**Fix:** drop `[:40]`.

### M2 [MEDIUM] `verify_open()` has no exception guard, unlike every per-module `review()` call in the same round

`round_once()` calls `verify_open(led, local=local, budget=limit)` at line 632 with nothing
wrapping it. Compare the per-module loop three lines later (641–646), which explicitly wraps
`review(m, ...)` in `try/except Exception` and `continue`s on failure. `verify_open()` itself
calls `_ask()` (line 485) with no guard of its own. If `P.ask`/`R._ask` raises inside a
re-verification call, the exception propagates uncaught through `round_once()` and `main()`'s
`while True:` loop (also unguarded, lines 704–711), killing the entire `--loop` standing sweep on
one bad response from a single auto-triage call — the "watcher that stops watching" failure mode
the file's own docstring (lines 371–378) says it exists to prevent, arriving via crash instead of
silent starvation.

**Fix:** wrap the `verify_open()` call the same way `review()` already is.

### Findings display truncation — lower severity, noted for completeness

`write_report()`'s `broken[:4]` (line 554) and `corrupt[:3]` (line 561) are illustrative examples
appended beside an always-accurate full count (`len(broken)`, `len(corrupt)`); nothing is hidden
from the *number* reported, only from the inline example list. Lower risk than O2, but same
category — flagged per the audit brief's instruction to check every ordered listing.

### Verified correct (per the audit brief's specific asks)

- **A model failure in auto-triage cannot be read as "refuted."** If `_ask()` returns `None`
  (GPU busy past `CLOUD_BUDGET`, or a call failure), `verdict = (got or {}).get("verdict")` is
  `None`; neither `if verdict == "refuted"` nor `elif verdict == "confirmed"` fires (lines
  490–497); the finding's `state` is left untouched (`"open"`), only `last_verified` advances.
  Confirmed by reading the branch logic directly — no path from a null response to `"closed"`.
- **A finding cannot be closed without a recorded verdict.** `state = "closed"` is set only in
  the same branch that also sets `f["verdict"] = "auto-triage refuted: " + why` (lines 491–492) —
  there is no other assignment to `"closed"` anywhere in the file.
- **`--modules` is legitimate pacing, not a Hard Rule 0 cap on a universe.** `rotation()` (lines
  504–521) persists a per-module `last seen` timestamp in the ledger (`led["seen"]`) and always
  schedules changed-then-oldest-unread modules first; nothing ever removes a module from
  eligibility. Given repeated invocation (the `--loop` mode this file is built around), every
  module cycles through — the cap only bounds how much gets read in *one* round, matching the
  file's own "pacing, not truncation" framing (line 462) for the analogous `verify_open` budget.

### Clean

Ledger merge logic (`_merge_ledgers`/`_reconcile_with_disk`, lines 236–304) is careful, monotone,
and correctly reasoned — a good model for the fix to H1/H3 above. `_anchored()`'s literal-symbol
requirement is a reasonable, correctly-implemented anti-hallucination filter. `_STATE_RANK` (line
225) lists `"stale"`/`"confirmed"`/`"refuted"` as possible states but the code only ever actually
sets `"open"`/`"retired"`/`"closed"` (`"confirmed"` is tracked via a separate `confirmed_n`
counter, not the `state` field) — cosmetic mismatch between the rank table and reality, not a
functional bug (`.get(..., 0)` defaults safely for any state string not in the table).

---

## 3. `src/derivation.py`

### D1 [MEDIUM-HIGH] [REPRODUCED] `SCAN_MODULES` omits `physics` — the module created specifically to hold the constants this scan exists to census

```python
SCAN_MODULES = ["assay", "feats", "cosmography", "propagation", "descending_ladder",
                "scale_theories", "chord_field", "resonance", "tempus", "ledger", "rigor",
                "custodes", "weave", "onomast", "worldseed", "address_space", "genre",
                "profile", "tiers", "grounding", "sevenfold", "burgs"]
```
(lines 476–477). `physics.py`'s own docstring explains it was created on 2026-08-22 *specifically*
because real-world physical constants had drifted into the wrong module and nothing caught it
until a full `--help` sweep found four broken imports — the same class of blind spot
`derivation.py`'s docstring says this scan exists to prevent ("so a reviewer can see exactly
where numbers live and catch a new undeclared one the day it is written rather than three volumes
later," lines 33–34). `physics` was never added to the list that scan reads from. Called
`derivation.scan_constants("physics")` directly:

```
physics in SCAN_MODULES: False
[('HERE', 0), ('_BAD_CHARS', 4), ('C', 1), ('RELATIVISTIC_ABOVE', 1), ('MATERIAL', 24), ('MODES', 0)]
```

`MATERIAL` alone carries 24 numeric literals (the per-material J/m^3 destructive-energy figures);
`RELATIVISTIC_ABOVE = 0.1` is a genuinely undeclared free parameter (no `LEDGER` entry anywhere
names it, unlike `material_strengths`, which *is* declared as `MEASURED`) — exactly the kind of
number the module's own MDL framing (lines 12–17) says "raises the omniverse's Transgression
score while buying nothing" if left unaccounted. None of this shows up in `main()`'s printed
"where constants live" table (lines 543–549) because the module is simply never scanned.

**Fix:** add `"physics"` to `SCAN_MODULES`.

### Minor

- **derivation.py:39** — `import silence` at module scope with no preceding
  `sys.path.insert(0, <src dir>)`, unlike every sibling file in this batch (health.py:47,
  overwatch.py:65, estate.py:40 all insert `src/` onto `sys.path` immediately before their own
  `import silence`). Works today only because everything that currently imports `derivation`
  already has `src/` on `sys.path` (or runs it directly, which self-adds its own directory) — not
  a live bug, but an inconsistency with the rest of the codebase's defensive convention. Low risk.
- **derivation.py:534** — `main()`'s "deepest derivation chains" printout is capped at
  `sorted(LEDGER, key=...)[:6]`. This is a ranked top-N console display of a fixed ~140-entry
  ledger, explicitly labeled as "deepest chains" rather than a claimed complete listing, and the
  underlying data (`LEDGER`, `check_graph()`'s `problems`) is printed in full elsewhere in the
  same function with no cap. Borderline under Hard Rule 0's letter; flagged for completeness, not
  treated as a real defect since nothing is hidden that the function claims to be showing in full.

### Clean

`check_graph()` (dangling parent / rootless DERIVED / unsigned OWNER / cycle detection) is
correctly implemented — ran it directly against the live ~140-entry `LEDGER`, it returns `[]`
(graph currently closes). The DFS cycle detector correctly memoizes visited nodes and would catch
a real cycle. `depth()`/`provenance()` both terminate correctly on cyclic or missing-parent input
via their `seen` sets.

---

## 4. `src/estate.py`

### E1 [HIGH] [REPRODUCED — confirms known open item] `charter()`'s erratum check (lines 208–212) tests for the rung NAME's presence, not the claimed defect, so it can never observe a fix

```python
for rung in ("Supercluster", "Filament", "Hyperverse"):
    if rung.lower() in text.lower():
        note("charter erratum (open)", rung + " is a rung with no Magnitude band")
```

The claimed defect is "this rung carries no Magnitude band." The test performed is "this rung's
*name* appears anywhere in the charter text." Those are different propositions, and the second
can never become false as a result of fixing the first: assigning Supercluster a Magnitude band
does not remove the word "Supercluster" from the document — the rung still exists and is still
discussed, so the name is still there, so the check still fires "open" forever, correct or not.

Verified live — the check currently fires on all three rungs:
```
{'finding': 'charter erratum (open)', 'detail': 'Supercluster is a rung with no Magnitude band'}
{'finding': 'charter erratum (open)', 'detail': 'Filament is a rung with no Magnitude band'}
{'finding': 'charter erratum (open)', 'detail': 'Hyperverse is a rung with no Magnitude band'}
```
And confirmed the check is tautological by running its exact logic against a synthetic "already
fixed" charter passage that assigns a band right next to the rung name:
```python
fixed_text = "Rung 10 is the Supercluster, assigned Magnitude band M9 as of this revision."
# -> STILL FLAGS AS OPEN ERRATUM even though a band (M9) is now present: Supercluster
```

**Fix:** test for the *absence* of an associated band token, e.g. no `\bM(?:10|[0-9])\b` within
some proximity window of the rung's mention, rather than presence of the rung name alone.

### Minor

- **estate.py:197** — `un[:4]` truncates the *display* of catalogued-sources-with-no-spine-code
  examples in the "e.g." note, while `len(un)` (the true count) is reported in full immediately
  before it. Low risk, explicitly labeled as an example, flagged for Hard-Rule-0 completeness.

### Clean

`artifacts()`/`inspect()` (lines 60–147) is the one place in this batch that most directly and
correctly implements the project's "no sampling" charter: every file under the configured roots is
actually opened, every `.json` is `json.load`'d, every text file is fully read and scanned for
control characters, every `.py` is `ast.parse`'d — no size or count cap anywhere in the walk or
the per-file inspection. `written()`, `terminal()`, `external()` are all straightforward, and
every `except` branch in the file either calls `note(...)` with the error or `silence.note(...)` —
none swallow silently.

---

## 5. `src/tempus.py`

No defects found. Full read, line by line — every docstring claim matches its implementation:
`apparent_lag_years` genuinely delegates to `propagation.arrival_years()` with no independent
mechanism (matching the "NO PER-SHELF TEMPO PARAMETER" design note at lines 49–66);
`contemporaneous`/`is_present_at`/`concordance_now` are simple, correct, and match their
docstrings; `loop_report`, `rung_description_length`, `prescience_horizon_bits`,
`retrocausality_beta` all compute exactly what they claim.

**Requested characterisation of `band_resolution()` (lines 182–210), for the owner's comparison
against `ledger.axis_score()` (not in this batch):**

- For any band with a defined successor (`i + 1 < len(LADDER)`): returns
  `log2(edge(band+1) / edge(band))` — the width of that band's own forward interval, in bits.
- At the ceiling (M10, no band above it): falls back to `lo, hi = edge(M9), edge(M10)` and
  returns `log2(hi / lo)` — i.e. it **reuses the topmost already-defined interval's width**
  rather than extrapolating or inventing an edge past the end of the Ladder. This exactly matches
  its own docstring ("M10 has no band above it, so it inherits the M9->M10 width; saturation at
  the ceiling is a property of the Ladder, not a licence to invent an edge," lines 199–200).
- Consequence: `band_resolution()` never divides by zero, never indexes `LADDER` out of range,
  and never looks up a `BAND_EDGES` key that doesn't exist — a fully bounded fallback for the
  ceiling case. This description is offered so the owner can directly compare it against whatever
  `ledger.axis_score()` does at the same M10/ceiling boundary; auditing `ledger.py` itself is
  outside this batch's scope.

---

## 6. `src/tells.py`

### T1 [MEDIUM-HIGH] [REPRODUCED] `STRUCTURAL["not merely X but Y"]` regex only requires the "but Y" reveal for one of its three phrases — over-fires on bare "not merely"/"not simply"

```python
"not merely X but Y": r"\bnot merely\b|\bnot simply\b|\bnot just\b.{0,40}\bbut\b",
```
(line 70). Regex alternation (`|`) binds looser than concatenation, so this compiles as three
independent alternatives: `\bnot merely\b`, OR `\bnot simply\b`, OR
(`\bnot just\b.{0,40}\bbut\b`). Only the third phrase is actually required to be followed by a
"but" within 40 characters to match; the other two match on their own, with no reveal
construction present at all. Confirmed with `tells.scan()` directly:

```
'The city was not merely large.'          -> {'not merely X but Y': 1}   # no "but" anywhere
'The city was not simply a ruin.'         -> {'not merely X but Y': 1}   # no "but" anywhere
'The city was not just old, but forgotten.' -> {'not merely X but Y': 1}  # correctly matches
```

This is the *only* pattern in the combined `STRUCTURAL`/`DISCOURSE` dict (44 patterns) with an
ungrouped top-level `|` — scripted a check across all of them (parenthesis-depth-aware pipe
scan) and confirmed no other pattern has this shape.

**Why it matters:** this dict is the shared enforcement mechanism the docstring (lines 5–10)
says both the writer-facing prompt and the audit are built from. A passage containing any bare
"not merely" or "not simply" — ordinary English, not the machine-tell reveal shape at all — is
misclassified as this specific structural tell by any code that calls `scan()` for scoring or
gating (not in this batch).

**Fix:** `r"\b(?:not merely|not simply|not just)\b.{0,40}\bbut\b"`.

### Clean

Everything else in the file reads correctly against its docstring: the sentence-boundary
anchoring rewrite (`_anchor()`/`_SENTENCE_START`, lines 127–131) correctly handles every
`^\s*`-prefixed discourse pattern; the escape-mangled-control-character self-guard is implemented
*twice* — once over the raw file source at import (lines 37–40) and again over every compiled
pattern's `.pattern` string (lines 139–141) — genuine defense in depth, not decorative;
`LEXICAL`/`LEXICAL_FICTION` word-boundary compilation and `prompt_section()`'s line-wrapping are
both straightforward and correct.

---

## 7. `src/physics.py`

No defects found. Full read, line by line. `kinetic()`'s Newtonian/relativistic switch at
`RELATIVISTIC_ABOVE * C` matches its docstring's stated threshold and reasoning; the `v >= C`
guard correctly raises rather than returning a fabricated large number (matching the project's
stated philosophy of never silently defaulting a physically-impossible input into a plausible-
looking value). `joules_for()` explicitly raises on an unknown material or mode rather than
defaulting to rock, exactly as its docstring promises. `binding_energy()`'s known divergence from
the literature Sun value is explicitly documented as intentional, and cross-checked against
`derivation.py`'s `sun_binding` ledger entry (line 73), which is correctly filed as `MEASURED`
rather than `DERIVED` from this formula for precisely the reason `physics.py` states (a uniform-
sphere model underestimates a centrally-condensed star) — the two files agree with each other.

The one issue involving this file is filed under **D1** above: `physics.py`'s own module-level
constants (`MATERIAL`, `RELATIVISTIC_ABOVE`) are invisible to `derivation.py`'s constant census
because `physics` is missing from `SCAN_MODULES` — a `derivation.py` bug, not a `physics.py` one.

---

## Summary table

| # | File | Severity | Status | Line(s) |
|---|------|----------|--------|---------|
| H1 | health.py | HIGH | REPRODUCED | 85–144 |
| H2 | health.py | HIGH | code-confirmed | 119, 138, 361 |
| H3 | health.py | HIGH | HYPOTHESIS | 310–371 |
| H4 | health.py | HIGH | REPRODUCED (via silence.audit) | 143–144 |
| M1 | health.py | MEDIUM | measured | 220–253 |
| O1 | overwatch.py | HIGH | REPRODUCED | 652 |
| O2 | overwatch.py | HIGH | code-confirmed + contrast | 566–577 vs 697–702 |
| M2 | overwatch.py | MEDIUM | code-confirmed | 453–501, 632 |
| D1 | derivation.py | MEDIUM-HIGH | REPRODUCED | 476–477 |
| E1 | estate.py | HIGH | REPRODUCED | 208–212 |
| T1 | tells.py | MEDIUM-HIGH | REPRODUCED | 70 |
