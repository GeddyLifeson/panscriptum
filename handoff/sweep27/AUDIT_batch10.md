# Batch 10 sweep audit (run27)

Modules read in full, every line:
- src/rigor.py — 866 lines
- src/gpu_lane.py — 479 lines
- src/reference.py — 358 lines
- src/weave_index.py — 276 lines
- src/autostart.py — 218 lines
- src/catalogue_aurora.py — 171 lines
- src/lognames.py — 36 lines

Total: 2,404 lines (wc -l reports 2,403 newline-terminated lines across the 7 files).

---

## gpu_lane.py

### 1. `_take_slot` never reclaims a CORRUPT slot lease — permanently starves that slot index
**gpu_lane.py:267-273** (specifically the guard at line 270). Severity: HIGH. **CONFIRMED — reproduced live.**

```python
rec = _read(path)
if rec is not None and _expired(rec, SLOT_LEASE_SECONDS):
    _remove_retry(path)
```

`_read()` (line 163-168) returns `None` on any read/parse failure — i.e. exactly when the slot
file is corrupt/unreadable. The `rec is not None and ...` guard means `_expired()` (which would
correctly classify `None`/non-dict as expired, per its own `if not isinstance(rec, dict): return
True` at line 173-174) is **never called** when the file is corrupt, so the corrupt file is never
removed. `os.open(path, O_CREAT|O_EXCL|O_WRONLY)` then fails with `FileExistsError` and the loop
just `continue`s to the next index — every single call, forever.

`foreground_active()` one function up (line 194-217) handles the identical situation correctly:
it calls `_expired(rec, ...)` unconditionally (no `is not None` guard), so a corrupt foreground
claim file *is* reclaimed.

Failure scenario, reproduced directly: with `MAX_SLOTS=2` and `slot.0.json` containing invalid
JSON, `_take_slot()` returns `slot.1.json` on every one of 5 consecutive calls — slot 0 is
permanently out of rotation, i.e. the card is running at half its configured concurrency
(worse fractions at larger `MAX_SLOTS`) with no recovery short of manually deleting the file.
This directly contradicts the module's own "FAIL OPEN, ALWAYS" charter (lines 32-37).

This is the KNOWN-OPEN item for this batch; reconfirmed by direct code trace and by an actual
run of `_take_slot()` against an injected corrupt `slot.0.json`.

### 2. `MAX_SLOTS` env-var parse crashes the whole module at import time
**gpu_lane.py:66-67**. Severity: MEDIUM. **CONFIRMED — reproduced live.**

```python
MAX_SLOTS = max(1, int(os.environ.get("PANSCRIPTUM_GPU_SLOTS")
                       or os.environ.get("OLLAMA_NUM_PARALLEL") or "2"))
```

No try/except. `PANSCRIPTUM_GPU_SLOTS=abc python -c "import gpu_lane"` raises
`ValueError: invalid literal for int() with base 10: 'abc'` and aborts import — verified live.
Since every one of the nine standing processes this module exists to arbitrate does
`import gpu_lane`, a single malformed environment variable (typo, stray whitespace, a shell
quoting mistake) takes down the entire library rather than degrading. This directly contradicts
the module header's own claim: "A bug in it must never be able to stop the library from working
... every failure path here PROCEEDS rather than blocks" (lines 32-37) — the one failure path
that is not inside a function at all is exempt from that promise.

---

## weave_index.py

### 3. `description[:400]` truncation at write time blinds a downstream mechanic-detection gate
**weave_index.py:224**, consumed at **weave.py:195-198**. Severity: MEDIUM. **CONFIRMED by trace
across both files** (this is half of the KNOWN-OPEN item; traced the downstream consumer as
instructed).

```python
"description": (e.get("description") or "")[:400],   # weave_index.py:224
```

The only consumer of `data/ENTITY_INDEX.json` in the tree is `weave.py` (verified by grep — the
`OUT_INDEX` comment at weave_index.py:267 naming `cosmology_graph` and `thread_integrity` as
readers is imprecise: those two only read `WEAVE_CANDIDATES.json`, which is itself *derived from*
this same truncated `index`, so they inherit the effect one hop removed). `weave.py`'s
`filtered_index()` uses the description to gate out RPG mechanics ("Channel Divinity", "Extra
Attack" etc.) from being treated as in-universe entities:

```python
desc = hits[0].get("description") or ""
if (_MECHANIC.match(nm)
        or (_STATBLOCK is not None and _STATBLOCK.search(desc[:400]))
        or _RULES_VOICE.search(desc[:300])):
```

Because `weave_index.py` already cut the description to 400 chars *before* it ever reaches
`weave.py`, the `_STATBLOCK`/`_RULES_VOICE` regex gate is structurally blind to any
mechanic/rules-voice tell that appears after character 300-400 of the original text (e.g. a class
feature whose entry opens with a sentence or two of flavour text before the mechanical "You gain
..." sentence). Such an entry survives the gate and is treated as a real in-universe entity for
cross-source identity resolution, which is exactly the failure class the surrounding comments in
`weave.py` (lines 100-118) describe fixing for the *name*-based case but not for this
description-truncation case.

### 4. STOPNAME / short-key entries dropped from the master index entirely, not just from
candidate matching — design question
**weave_index.py:215**. Severity: LOW. **SUSPECTED — deliberate design tradeoff, flagged as a
question per instructions** (other half of the KNOWN-OPEN item).

```python
if not key or len(key) < 3 or key in _STOPNAMES:
    continue
```

This is inside `build()`, which populates `index` — the thing written verbatim to
`ENTITY_INDEX.json`. An entry whose normalized name collides with a stopword (`_STOPNAMES` at
line 48-53: "guard", "king", "father", "man", etc.) or normalizes to under 3 characters is
dropped from the index outright, not merely excluded from the `len(srcs) >= min_sources`
candidate filter in `main()`. Traced the only consumer (`weave.py`, `cosmology_graph.py` and
`thread_integrity.py` via `WEAVE_CANDIDATES.json`) and confirmed none of them have any other path
to see these entries. If a source genuinely has a character whose canonical name *is* one of
these stopwords (plausible for some fictions — "Boss", "Guard"), that entity is invisible to
every cross-source identity tool, permanently, with no escape hatch. This reads as intentional
noise-reduction (documented at length in the comment at lines 47-53, same rationale as the title
`_STRIP` regex), analogous to a stop-word list rather than a "top-N" truncation, so I am not
calling it a Hard Rule 0 violation — but it is worth the owner confirming this is the intended
scope of "no caps, ever," since it does silently erase specific named entities from the one
global index, not merely down-weight them.

### 5. `weave_index.py` lacks the `_BAD_CHARS` source-corruption self-check its sibling
`weave.py` carries
**weave_index.py** (no such block present; contrast **weave.py:73-76**, **reference.py:58-61**,
**rigor.py:88-91**, **autostart.py:41-43**). Severity: LOW. **CONFIRMED absent; file currently
clean** (verified byte-for-byte — no chr(7/8/11/12) present today).

`weave_index.py` defines several hand-written regexes (`_STRIP`, `_EARTH`) of exactly the kind
the project's own comments say have been silently corrupted by heredoc transport five times
before, and its own sibling module in the same weave/index pair (`weave.py`) already carries the
self-check guard that would catch this. `weave_index.py` does not. This is the "fix applied to
one file while the identical construction in a sibling module was never visited" pattern named in
the brief — not a live bug today, but an un-mirrored protection.

---

## reference.py

### 6. `shelfmark()` hardcodes a 3-upper-rung assumption; a `tier_key` of any other depth
produces a silently wrong (and, at more rungs, duplicate-marker) Shelfmark, not a crash
**reference.py:236-246**, specifically the offset `RUNGS[3 + i]` at line 245. Severity: MEDIUM
(currently masked by data; would misfire the moment a 4th reference entity is added with a
different-depth `tier_key`). **CONFIRMED — reproduced live.**

```python
for i in range(len(parts)):
    k = ".".join(parts[:i + 1])
    upper.append(nav["nodes"].get(k, {}).get("name", k))
...
marks = [f"{RUNGS[i]}{v}" for i, v in enumerate(upper)]
marks += [f"{RUNGS[3 + i]}{v}" for i, v in enumerate(lower)]
```

`lower`'s rung labels are hardcoded to start at `RUNGS[3]` ("Mv."), which is only correct if
`upper` always has exactly 3 elements. `upper`'s length is `len(rec["tier_key"].split("."))`,
which is data-dependent, not fixed. All three current REFERENCE entries happen to use a 3-part
`tier_key` ("1.6.1", "4.2.0", "1.2.5"), so the bug is currently invisible.

Reproduced directly against `reference.py`'s own `shelfmark()`:
- `tier_key="1.6"` (2 parts) → output silently **drops the "Mt." rung entirely**:
  `Ω › H.The Spoken › X.Venaellys › Mv.DRG › U-7 › G.North › P.Earth` (7 rungs shown where 8 are
  claimed; the world-tier rung between galaxy and metaverse just vanishes with no error).
- `tier_key="1.6.1.2.9"` (5 parts) → output **duplicates "Mv." and reuses indices already
  consumed by `upper`**: `Ω › H.The Spoken › X.Venaellys › Mt.Miirora › Mv.Ryanella › U-1.6.1.2.9
  › Mv.DRG › U-7 › G.North › P.Earth` — "Mv." appears twice, and one rung renders the literal,
  un-looked-up tier_key fragment "1.6.1.2.9" instead of a name (the navtree lookup fell through
  to its own `k` fallback at line 239).

No exception is raised in either case — this is a silent-wrong-output bug, not a crash, which is
the worse of the two under this project's own stated failure taxonomy. The fix is straightforward
(`RUNGS[len(upper) + i]` instead of the hardcoded `RUNGS[3 + i]`), but is a genuine finding as
shipped.

### 7. `shelfmark()`'s exception handler folds "navtree missing/corrupt" and "key just not
present" into the same silent fallback
**reference.py:232-242**. Severity: LOW. **SUSPECTED.**

```python
try:
    nav = json.load(open(os.path.join(HERE, "data", "NAVTREE.json"), encoding="utf-8"))
    ...
except Exception:
    silence.note("reference.py:232")
    upper = ["?", "?", "?"]
```

A missing/unreadable/malformed `NAVTREE.json` (a real data-integrity failure) and a `tier_key`
whose upper node just isn't in the tree yet (an expected, benign "not classified yet" case,
per the file's own "?" convention documented at lines 222-228) produce the identical `["?", "?",
"?"]` output. `silence.note()` is called so the event isn't fully invisible, but the caller of
`shelfmark()` cannot distinguish "the navtree file is broken" from "this entity's rung is
unknown" — the two are operationally very different (one needs an ops fix, the other is
expected data-entry state). Not calling this a hard bug since a `?` in either case is arguably
the correct charter-mandated placeholder either way, but it does mean a broken `NAVTREE.json`
would degrade silently into "everything shows `?`" rather than a loud failure.

---

## catalogue_aurora.py

### 8. `written` list — and therefore the printed "Wrote N records" summary — counts records
whose write was DENIED
**catalogue_aurora.py:140 vs 141-153**. Severity: MEDIUM. **CONFIRMED by direct trace.**

```python
written.append((r, record))                                    # line 140, unconditional
if not args.dry_run:
    import pipeline as _P
    if not _P.write_record_catalogue(
            os.path.join(RECORDS, slug(source_name) + ".json"), record):
        print(f"      -> WRITE DENIED {source_name}; roll left untouched", flush=True)
        continue                                                # only skips the entry_count/status update
    r["entry_count"] = len(entries)
    r["status"] = "catalogued"
...
print(f"{verb} {len(written)} records from Aurora XML:\n")
for r, rec in sorted(written, key=lambda x: -len(x[1]["entries"])):
    ...
    print(f"  {len(rec['entries']):5d} entries ({withtext} with description)  {r['name']}")
```

`written.append()` happens before the write is even attempted, and the `continue` on a denied
write only skips the roll-state update two lines later — it does **not** remove the entry from
`written`. So a source whose `write_record_catalogue()` call is denied (e.g. another writer holds
the record, or `pipeline`'s gate rejects it) still gets counted in the final "Wrote N records"
total and still gets a line in the per-source printout claiming it was written, immediately
after the console already printed "WRITE DENIED" for that same source in the same run. The roll
file itself (`SWEEP_ROLL.json`) is correctly protected — this is exactly the class of bug the
comment at lines 143-149 says was fixed for `catalogue_web.py`'s sibling pattern — but the fix
only protects the persisted roll, not the operator-facing run summary, which can still claim a
write succeeded when the console line two rows above says otherwise.

### 9. Silent per-folder name-collision dedup may drop legitimately distinct entries
**catalogue_aurora.py:83-86**. Severity: LOW. **SUSPECTED.**

```python
key = (etype.lower(), re.sub(r"[^a-z0-9]", "", name.lower()))
if key in seen:
    continue
seen.add(key)
```

Two XML `<element>`s of the same type whose names normalize to the same alphanumeric-only key
(e.g. differ only by punctuation, spacing, or an apostrophe) silently collapse to whichever one
was encountered first in `sorted(glob.glob(...))` order; the second is dropped with no note of
what was lost. Plausibly intentional (Aurora content packs can have literal duplicate
`<element>`s across overlapping files), but nothing distinguishes "true duplicate" from
"different entity, coincidentally same normalized key" the way `weave_index.py`'s continuity-tag
machinery does for the same class of problem elsewhere in this project. Not confirmed as an
actual data loss on the current corpus — flagged as a question, not a proven bug.

---

## autostart.py

### 10. `_twin_watchdog()` returns `False` (no twin) on ANY failure of its own detection
mechanism — re-opens the exact multi-watchdog failure the function exists to prevent
**autostart.py:121-145**, specifically the broad `except Exception` at line 131-133. Severity:
MEDIUM-HIGH. **CONFIRMED by trace.**

```python
def _twin_watchdog():
    try:
        out = subprocess.run(["powershell", ...], ...).stdout
    except Exception:
        silence.note("autostart.py:131")
        return False
    ...
```

The module's own docstring (lines 148-156) describes, in detail, a real incident where three
watchdogs ran concurrently, each restarting supervisors on independent clocks, causing foremen to
treat each other's stacks as duplicates and shoot them, producing a self-sustaining respawn loop
— and states that the fix is "a watchdog that finds a twin at startup exits." But the twin-finding
mechanism itself (a PowerShell `Get-CimInstance` call, with a 60s timeout) fails closed in the
dangerous direction: if PowerShell is unavailable, times out, or the CIM provider errors for any
reason, `_twin_watchdog()` reports "no twin" and `watch()` (line 148-179) proceeds to run as a
second (or third) watchdog exactly like the incident being guarded against. Given the function's
whole purpose is to prevent a documented, previously-occurring catastrophic failure, defaulting
to "proceed as if safe" on its own instrumentation failure is the dangerous-direction default the
sweep is specifically looking for — the safer failure mode here would be to log loudly and either
retry or refuse to start a second watchdog role, not silently assume the coast is clear.

### 11. `--install` does not start the watchdog immediately — the "supervisor survives its own
death" guarantee only takes effect after the next reboot
**autostart.py:194-200**. Severity: LOW-MEDIUM. **SUSPECTED design gap, framed as a question.**

```python
if a.install:
    path, why = install()
    print(f"{why}: {path}" if path else why)
    if not supervisor_alive():
        start_supervisor(a.read_hours)
        print("supervisor started")
    return 0
```

`install()` only writes the `.vbs` Startup-folder shortcut (which Windows runs at the *next*
logon) and starts the supervisor directly — it never launches `watch()` (the watchdog loop) in
the background. The module's stated purpose is explicitly "make the supervisor survive its own
death" (line 3, restated at lines 12-17), but between running `--install` today and the next
reboot, if the just-started supervisor dies, nothing restarts it — the exact "second gap" the
file exists to close is uncovered for however long it is until the next reboot. This may be an
accepted simplification ("coverage begins at next boot" is a common pattern for Startup-folder
installers), but it is worth the owner confirming, since the module's own framing implies
immediate coverage.

---

## rigor.py

Read in full (866 lines). This module is unusually heavily self-documented, with multiple
comments explicitly describing bugs already found and fixed in prior sweep runs (run #19, #21,
etc.), each cross-referenced against the specific line/behavior that was wrong. I traced each of
these claims against the current code and found the fixes described are actually present (e.g.
`measure_bit_value` genuinely uses `T.band_resolution` and not the cumulative
`rung_description_length` the docstring says was the old bug; the faculty-weight "muted" check at
lines 746-759 genuinely reads `A.FACULTY_WEIGHTS` live rather than hardcoding a verdict). The
iterative Tarjan SCC implementation (`_strongly_connected`, lines 262-313) and the Bradley-Terry
Ford's-condition refusal logic (lines 316-458) are both correct on inspection — no off-by-one or
inverted-condition found in either. No new CONFIRMED or SUSPECTED bugs were found in this file
beyond what its own comments already document as fixed. Everything downstream of it (`assay.py`,
`derivation.py`, `tempus.py`, `cosmography.py`) is out of this batch's scope and was not verified.

---

## lognames.py

Read in full (36 lines). Pure constant definitions (`READ`, `ROLL`, `PIPELINE`, `RECATALOGUE`,
`SWEEP`, `CALIBRATE` log filenames and their `OWNER` process-fragment map). Cross-checked every
entry in `OWNER` against how each script is actually invoked elsewhere in the tree
(`overnight.py`, `foreman.py`) to confirm the fragment strings are specific enough to
disambiguate — `pipeline.py` and `sweep.py` are invoked bare (no flags) everywhere in the tree,
so the lack of a distinguishing flag on those two entries (unlike `READ`/`ROLL`/`RECATALOGUE`/
`CALIBRATE`, which do carry flags) is not currently a collision risk. No bugs found.
