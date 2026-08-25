# Batch 14 audit — assay.py, chain.py, onomast.py, ingest_doc.py, grounding.py, chord_field.py, resync_roll.py

Full top-to-bottom read of all seven files. No sampling. Per-module findings below, grouped by
severity, each cited `file.py:LINE` with quoted code and labelled VERIFIED/UNVERIFIED.

Excluded per instructions (pre-known, not re-reported as new): assay.py's `axis_score()` flat 9.9
at top band (M18), and `interval_from_hands` zero-callers / floor-breach (m90).

---

## HIGH

### onomast.py:398 — bare `open(..., "w")` on a shared data file (two-writer contract violation)
```python
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(named, f, indent=2, ensure_ascii=False)
```
`OUT = data/ONOMASTICON.json`, read by `navtree.py`, `pipeline.py`, and `worldseed.py` — a
genuinely shared artifact. This is a bare truncating write with no write-then-rename, unlike the
established convention this project uses everywhere else for shared JSON artifacts (see
`chain.py:111-118`'s own explanation: "a bare open() leaves a TORN CHAIN.json if the process dies
mid-dump or a reader holds it... every other phase artifact in the kit lands this way"). A crash
or a concurrent reader mid-write leaves `ONOMASTICON.json` torn/truncated for the three consumers.
**VERIFIED.** Fix: write to `OUT + ".tmp"` then `silence.replace_retry(tmp, OUT)`, matching
`chain.py:write_result`.

### onomast.py:311-334 (call site 356) — `register_for`'s genre/feature logic is dead; docstring's claimed fix doesn't apply to the one real caller
```python
def register_for(group_id, genre_register=None, features=None):
    """... Falls back to a hash of the group id ONLY when neither a genre nor features are known.
    That fallback used to be the whole function, and it produced the register that gave Alien and
    Doom the flowing elvish sound and denied Greek myth the classical one.
    """
    if not genre_register and not features:
        return REGISTER_ORDER[int(hashlib.sha256(str(group_id).encode()).hexdigest(), 16)
                              % len(REGISTER_ORDER)]
    votes = {}
    if genre_register in REGISTERS:
        votes[genre_register] = GENRE_WEIGHT
    for axis, value in (features or {}).items():
        ...
```
and the sole call site:
```python
# onomast.py:356
reg = register_for(v["continuity_group"])
```
`register_for` is called exactly once anywhere in the repo (grepped whole `src/`), and it's called
with only `group_id` — no `genre_register`, no `features`. Every invocation therefore takes the
`if not genre_register and not features:` branch and returns the pure SHA256-hash fallback. The
~65-line `FEATURE_SHIFT` / `GENRE_WEIGHT` / `FEATURE_WEIGHT` voting mechanism (lines 268-334),
which is the entire stated purpose of the function and the docstring's claimed fix for "Alien and
Doom" sounding wrong, is unreachable dead code for the one place that assigns catalogue-facing
registers to real worlds. (Root cause: at the pipeline stage `name_worlds()` runs, genre/feature
data for a world doesn't exist yet — it's produced later by `worldseed.py`/`profile.py`, which
read `register` back **out** of `ONOMASTICON.json` rather than the other way around — so there is
no data available to pass in, architecturally.) Confirmed no other caller anywhere in `src/`
passes `genre_register`/`features` (navtree.py has its own unrelated local `register_for`).
**VERIFIED.** Either wire real genre/feature data into `name_worlds()`'s call, or update the
docstring to stop claiming the fallback-only bug was fixed.

### ingest_doc.py:105-113 — `register()`: bare `open(HOSTS, "w")` + unguarded read-modify-write on a shared, widely-read data file
```python
def register(source):
    with open(HOSTS, encoding="utf-8") as f:
        hosts = json.load(f)
    cur = hosts.get(source)
    if cur and not cur.startswith("doc:"):
        return cur
    hosts[source] = "doc:" + slug(source)
    with open(HOSTS, "w", encoding="utf-8") as f:
        json.dump(hosts, f, indent=1, ensure_ascii=False, sort_keys=True)
    return hosts[source]
```
`HOSTS = data/WIKI_HOSTS.json`, read/written by nine other modules. This is both (a) a bare
truncating write with no atomic replace, and (b) an unguarded read-modify-write — classic
lost-update shape if another process touches `WIKI_HOSTS.json` between the read at line 105-106
and the write at line 111-112. The project has already found and fixed this *exact* bug class on
this *exact* file: `hostcheck.py:69` states outright "Every write in this module was a bare
`open(path, "w")` + `json.dump`, which truncates the [file]...", and `feats.py:298` writes
`WIKI_HOSTS.json` correctly via `silence.replace_retry(tmp, HOSTS)`. `ingest_doc.py` was not
updated to match. **VERIFIED.**

### grounding.py:236-239 — bare `open(p, "w")` on a shared data file; no `silence` import at all
```python
if args.write:
    p = os.path.join(HERE, "data", "GROUNDINGS.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\nwrote {p}")
```
`GROUNDINGS.json` is read by `navtree.py`, `pipeline.py`, and `tiers.py`. `grounding.py` doesn't
even `import silence` (confirmed against the file's import block, lines 43-53) — it has no access
to `replace_retry` without adding the import. Same torn-write risk as the other three findings
above. **VERIFIED.**

### resync_roll.py:66 — bare `open(ROLL, "w")`, on the exact file the module's own docstring says was corrupted by an unsafe concurrent write
```python
if changed and not dry:
    with open(ROLL, "w", encoding="utf-8") as f:
        json.dump(roll, f, indent=2, ensure_ascii=False)
```
The module docstring (lines 3-11) is *specifically about* `data/SWEEP_ROLL.json` being clobbered
because "every cataloguer... rewrites the whole roll after each source, so two of them running
concurrently will have one clobber the other's counters with a stale copy read minutes earlier."
`resync_roll.py` exists to repair that damage — and then repairs it with the identical unsafe
pattern: a bare truncating `open("w")` with no write-then-rename. `silence` is already imported
(line 19) and already used for `silence.note` (line 46) in this same file, so `replace_retry` is
one line away and simply wasn't used for the write that matters most. If this script runs while
any cataloguer is mid-write to `SWEEP_ROLL.json`, it can either overwrite a fresher roll with its
own stale in-memory read, or leave the roll torn if interrupted mid-dump — reintroducing the exact
failure this script was written to fix. **VERIFIED.**

---

## MEDIUM

### assay.py — `INSTRUMENT_WINDOWS` collapses to a constant for M5 through M10 (same shape as the excluded M18 bug; already tracked internally, not new)
```python
INSTRUMENT_WINDOWS = {
    "M0": (1, 18), "M1": (8, 22), "M2": (12, 26), "M3": (16, 28), "M4": (18, 30),
    "M5": (30, 30), "M6": (30, 30), "M7": (30, 30), "M8": (30, 30), "M9": (30, 30),
    "M10": (30, 30),
}
```
For every anchor M5-M10, `span = hi - lo == 0` (assay.py:501), so
`value = min(30, round(lo + (s / 10.0) * span))` (assay.py:517) returns exactly `30` for *any*
axis score `s`, discarding it entirely. This is the same "band-edge collapses a range to a
constant" shape as the excluded M18 `axis_score` bug, but manifesting in `instrument()` across six
bands instead of one. I confirm it is a real, live behavior (not hypothetical) — **and** that it
is already known and pinned as a regression test in `verify_math.py:682-694`:
```python
# KNOWN DEFECT, charter-owned. Pinned as a test so that fixing it fails here loudly...
_dull = A.instrument("M5", {"acumen": 1.0}, worksheet="x")["faculties"]["Intelligence"]
_sharp = A.instrument("M5", {"acumen": 10.0}, worksheet="x")["faculties"]["Intelligence"]
check("KNOWN DEFECT: the Instrument has NO resolution above M4", _dull == _sharp, True, ...)
check("KNOWN DEFECT: M5 caps the window but earns no Transcendence Grade", ...)
```
**VERIFIED, but already tracked / charter-owned per the codebase's own test suite** — flagged here
only because the task asked specifically for other instances of this shape; not a new discovery.

### chain.py:351-353 — unguarded shared-dict mutation across worker threads (lost-update race)
```python
def work(chunk):
    ...
    for o in (got or {}).get("outcomes", []):
        ...
        if wk in idx and lk in idx:
            local.append(...)
        else:
            for side, k in ((w, wk), (l, lk)):
                if k not in idx:
                    unmatched[side[:40]] += 1        # <-- OUTSIDE the lock
    with lock:
        done["n"] += len(chunk)
        ...
```
`extract()` (chain.py:286-368) runs `work()` concurrently across up to `workers` threads via
`ThreadPoolExecutor`. `edges`, `prov`, and `done` are all correctly mutated only inside
`with lock:` (line 354 onward). But `unmatched` — a single shared `collections.Counter()` created
once in `extract()` (line 304) — is incremented at line 353 *outside* the lock, from every worker
thread concurrently. `Counter[key] += 1` is not atomic (read, add, write across three steps), so
concurrent increments from multiple threads can lose updates. Impact is scoped to the diagnostic
"names that match nothing the library catalogues" report (console output at line 456-457 and the
`unmatched` field persisted into `CHAIN.json` at `write_result` line 108) — the actual graph
(`edges`/`prov`, which feed Bradley-Terry) is unaffected. **VERIFIED** (by direct code inspection);
undercounts are probabilistic and won't reproduce every run.

### chain.py:167,274,282,331 — `silence.note()` site tags are stale line numbers, degrading triage of the failures ledger
```python
167:                silence.note("chain.py:91")
274:        silence.note("chain.py:155")
282:        silence.note("chain.py:161")
331:                silence.note("chain.py:252")
```
Four of `chain.py`'s six `silence.note()` calls use a **literal line-number string** as the site
tag (the other two use descriptive labels: `"chain.py:tuning"`, `"chain.py:harvest-idx"`, etc.).
None of the four numeric tags matches its actual current line — they're stale by 76-120 lines,
presumably accurate when first written but not updated as the file was edited since.
`silence.note`'s whole design (per `silence.py:250-276`) is to let someone diagnose a recorded
failure from `state/failures.json` by its site tag; a diagnostician grepping for "chain.py:155"
today lands on the `tuning` import's except block context, not the `cascade_bridge` failure it was
meant to mark, while "chain.py:91" (actual line 167) lands nowhere near either. **VERIFIED** by
line count; purely an observability defect, not a runtime bug. Fix: switch these four to
descriptive labels like their two siblings, so they can't go stale again.

### ingest_doc.py:98-99 — `extract()`: bare `open(..., "w")` on a document corpus read by other pipeline stages
```python
with open(os.path.join(d, "pages.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=0, ensure_ascii=False)
```
`data/docs/<slug>/pages.json` is read by `feats.py` and referenced in `manifest_builder.py`.
Same bare-write pattern as the HIGH findings above, on a file with real downstream readers, though
lower risk than `WIKI_HOSTS.json`/`GROUNDINGS.json`/`ONOMASTICON.json` since it's written once per
`--pdf` invocation rather than repeatedly from many call sites. **VERIFIED.**

### ingest_doc.py:116-126 — `record_path()`: non-deterministic fallback match when slugs overlap
```python
def record_path(source):
    p = os.path.join(RECORDS, slug(source) + ".json")
    if os.path.exists(p):
        return p
    want = slug(source)
    for fn in os.listdir(RECORDS):
        base = fn[:-5]
        if want in base or base in want:
            return os.path.join(RECORDS, fn)
    return p
```
When no exact-slug record file exists, this falls back to a substring match against every record
filename, in `os.listdir()` order — which Python does not guarantee sorted, and which can vary
between platforms/filesystem states. If two record filenames both satisfy `want in base or base in
want` for a given `source` (plausible in a 215+-source catalogue with prefix-sharing names, e.g.
franchise + sub-franchise pairs), whichever one `os.listdir` happens to return first silently
wins, with no tie-break and no warning. This is the same defect family the project has already
found and fixed once: `navtree.py:157-166`'s own comment (bug m41) describes `os.listdir`/`set()`
hash-order non-determinism flipping node names across consecutive runs, with a documented
measured impact ("two consecutive runs renamed 75 of 734 nodes"). Here a wrong pick means
document-derived entities get silently merged into (and their provenance-write in `main()` land
against) the wrong source's record. **VERIFIED** as written; whether any current slug pair
actually collides is data-dependent and not verified here. Fix: sort `os.listdir(RECORDS)` and/or
require exact/unique match, raising rather than guessing on ambiguity.

### grounding.py:113-118, 163-171 — `classify_text(top=3)` truncates the score set that only has 5 members, skewing `confidence` and `runners_up`
```python
def classify_text(text, top=3):
    scores = collections.Counter()
    for name, spec in GROUNDINGS.items():
        for pat, wt in spec["cues"].items():
            scores[name] += wt * len(re.findall(pat, text, re.I))
    return scores.most_common(top)
...
ranked = classify_text(" ".join(parts))
...
total = sum(s for _, s in ranked) or 1
...
"confidence": round(score / total, 3),
...
"runners_up": ranked[1:],
```
`GROUNDINGS` has exactly 5 keys (`ex_nihilo`, `emanation`, `eternal_cycle`, `demiurgic`,
`immanent`). `classify_text`'s default `top=3` throws away the bottom 2 of those 5 categories'
scores *before* `classify_source` computes `total` and `confidence` from the result. Whenever the
4th- or 5th-place grounding type has a nonzero cue-match score, `total` is undercounted, so
`confidence = score/total` is systematically inflated relative to the true 5-way distribution —
directly feeding the "contested cosmogonies" report at `grounding.py:229-234`
(`confidence < 0.5`), which will under-flag genuinely contested sources. `runners_up` also can
never surface more than 2 alternate readings even though up to 4 exist. The top-1 pick itself
(`ranked[0]`, which decides `grounding`/`verdict`) is unaffected, since `most_common(3)` always
includes the true top match. **VERIFIED** as a code-level fact; numeric impact is data-dependent
(depends on how often 2+ of the 5 categories score nonzero on the same source) and was not run
here. Fix: since there are only 5 possible types, drop the `top` cap for this call (or raise it to
`>= len(GROUNDINGS)`).

### chord_field.py — the entire module (all 6 functions) has zero callers anywhere in the codebase
```python
def total_beta(): ...
def per_system_beta_without_unification(n_systems): ...
def landauer_floor(bits, temperature_K=300.0): ...
def recoil_momentum(energy_J): ...
def recoil_velocity(energy_J, emitter_mass_kg): ...
def critical_power_self_focus(wavelength_m, n0=1.0003, n2=3e-23): ...
```
Grepped the whole `src/` tree: nothing imports `chord_field` as a module (`import chord_field` /
`from chord_field import ...` appears nowhere), and nothing calls any of its six functions. The
only reference anywhere is a bare string `"chord_field"` inside `derivation.py`'s `SCAN_MODULES`
list (derivation.py:477), which only scans the file's *module-level UPPERCASE constants*
(`C_LIGHT`, `G_NEWTON`, `HBAR`, `K_BOLTZMANN`) for the derivation ledger — it never imports or
executes the module's functions. Same "zero callers" shape as the excluded m90
(`interval_from_hands`), just for a whole module rather than one function. The formulas
themselves are correct (Landauer's bound, `p = E/c`, and the Marburger self-focusing critical
power formula `P_cr = 3.77 λ² / (8π n0 n2)` were checked against their standard forms and match).
**VERIFIED (dead code); the module's own physics is CLEAN.**

### resync_roll.py:38-50 — `by_source` index silently last-wins on a normalized-source-name collision
```python
by_source = {}
for fn in os.listdir(RECORDS):
    ...
    src = rec.get("source")
    if src:
        by_source[norm(src)] = (rec, fn)   # last write wins, silently
```
Iterated in `os.listdir()` order (not guaranteed sorted or stable). If two record files' declared
`source` fields normalize to the same key (plausible among 215+ closely-named catalogue sources),
whichever file the OS lists last silently overwrites the earlier entry with no warning, and the
roll's `entry_count` for that source name is then resynced from the wrong record file. Same
non-determinism family as the `navtree.py` m41 bug and the `ingest_doc.py:record_path` finding
above. **VERIFIED** as written; whether an actual collision exists in the current `data/records/`
was not tested.

### resync_roll.py:59-63 — resync doesn't downgrade `status` when a source's on-disk entry count drops to zero
```python
if r.get("entry_count", 0) != n:
    changed.append((r["name"], r.get("entry_count", 0), n, fn))
    if not dry:
        r["entry_count"] = n
        r["status"] = "catalogued" if n else r.get("status", "catalogued")
```
When `n > 0` the fix actively sets `status = "catalogued"`. When `n == 0` (the record file's own
`entries` list is now empty), the `else` branch is `r.get("status", "catalogued")` — i.e. it just
reads back whatever `status` already was (or defaults to `"catalogued"` if the key were somehow
absent). So a source whose record legitimately went to zero entries, and whose `entry_count` this
script correctly corrects down to 0, can be left with `status: "catalogued"` — a roll entry that
now says "catalogued, 0 entries," which is exactly the kind of roll/disk disagreement this script
exists to eliminate. **VERIFIED** by reading the ternary; whether `status` values other than
"catalogued" are ever meaningfully consumed downstream was not checked in this pass.

---

## LOW

### assay.py:502-503 — unreachable dead branch in `instrument()`
```python
grade_n = max(0, LADDER.index(anchor) - 5)
grade = ["", "I", "II", "III", "IV", "V"][grade_n] if grade_n <= 5 else "V"
```
`LADDER` has 11 entries (`M0`-`M10`), max index 10, so `grade_n` is capped at `10 - 5 = 5` by
construction — `grade_n <= 5` is always true and the `else "V"` arm can never execute under the
current `LADDER`. Harmless defensive code, but dead. **VERIFIED.**

### assay.py:49, chain.py:50, ingest_doc.py:32 — self-integrity file read has no context manager
```python
if any(c in open(os.path.abspath(__file__), encoding='utf-8').read() for c in _BAD_CHARS):
```
No `with`; the file object is only implicitly closed by CPython's refcounting once the expression
finishes. Harmless under CPython (which all three modules' own docstrings target) but not
guaranteed by the language and would leak a handle under e.g. PyPy. **VERIFIED**, trivial.

### chain.py:108 — `unmatched.most_common(40)` caps what's persisted into CHAIN.json's diagnostic field
```python
"unmatched": (unmatched.most_common(40) if hasattr(unmatched, "most_common") else (unmatched or [])),
```
Truncates the unmatched-name-frequency table to the top 40 before writing it into
`data/CHAIN.json`. Per Hard Rule 0 this is worth flagging explicitly: it *is* a cap on a list
written into a persisted, catalogued artifact. Judgment call, not a clear violation — the list in
question is *names that failed to match anything the library catalogues* (i.e. not itself
catalogued content, and nothing downstream currently reads the `unmatched` field back out of
`CHAIN.json` besides `chain.py`/`pipeline.py`'s own writer — grepped, no other reader). Flagging
per instructions rather than asserting it's wrong.

### grounding.py — missing the `_BAD_CHARS` self-integrity check present in its regex-heavy siblings
`assay.py:42-51`, `chain.py:49-51`, and `ingest_doc.py:31-33` all carry the same guard against a
regex escape silently arriving as a literal control character (the project's own documented
history: "arrived here as a 0x08 backspace five separate times"). `grounding.py` has no such
check, despite being the single most regex-saturated file in this batch — `_ORIGIN` plus every
`cues` pattern across all five `GROUNDINGS` entries (grounding.py:57-108) is exactly the kind of
hand-authored regex the check exists to protect, and a corrupted pattern here would fail exactly
as described: silently matching nothing, misreading as "this source has no origin account" rather
than as corruption. **VERIFIED absent** by inspection of the import block; not proof any corruption
has occurred, only that the safety net other similar modules in this batch carry is missing here.

### ingest_doc.py:216 — per-entity `description` truncated to 2000 characters
```python
"description": (e.get("description") or "").strip()[:2000],
```
A `[:2000]` slice on one field of one catalogued entry. The module's own docstring states "HARD
RULE 0 APPLIES. The whole document is extracted, the whole corpus is chunked, every chunk is
mined" — this doesn't cap the roster of entities or chunks (verified clean: chunking at
ingest_doc.py:164-172 covers every page, no page or chunk is dropped), but it does cap the
*content* of an entry's description field, which is catalogued content. Borderline: a single
model-generated description exceeding 2000 characters from a ~9000-character source chunk would
be unusual but not impossible. **VERIFIED** as written; flagged per instructions to flag every cap
and let severity be judged — leaning toward "worth tightening or removing" rather than "clear
violation," since it bounds one field rather than a roster/list.

---

## CLEAN

- **chord_field.py**: every formula in the file (Landauer floor, `p = E/c` recoil momentum,
  Marburger self-focusing critical power) is correct against its standard physical form. No file
  I/O, no shared state, no caps on any roster. Its only issue is the dead-code finding above — the
  physics and arithmetic are clean.
- **grounding.py**: the previously-flagged `classify_source(cap=140000)` issue is confirmed FIXED
  — the current signature is `classify_source(rec, cap=None, floor=6)` and it now raises
  `SystemExit` loudly if `cap is not None` (grounding.py:144-148), refusing rather than truncating.
  No numeric cap on the origin-entries scan remains; `main()`'s `for _, rec in PL.records():`
  iterates every record with no slicing.
- **onomast.py**'s syllable/name-generation logic (`_stream`, `well_formed`, `coin_name`,
  `coin_well_formed`) was read in full and is internally consistent, deterministic, and its
  documented fixes (the m-numbered "fallback abandoned both invariants" bug) are genuinely fixed
  in the current code.
- **assay.py**'s core scoring math (`axis_score`'s clamp/log formula, `assay()`'s composite and
  weight renormalization, `_interval`'s variance propagation, the M18/m90 exclusions aside) is
  internally consistent and its extensive self-documentation matches the executable behavior
  everywhere else it was checked.
