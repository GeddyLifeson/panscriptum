# AUDIT — batch 16 (run #36)

Modules: `rigor.py`, `publish.py`, `zfighters.py`, `estate.py`, `policy.py`,
`axis_correlation.py`, `recover_folder_records.py`, `withdraw_chapters.py`

Read in full (not from docstrings). All line numbers are as of the read; they will drift —
quoted text is the anchor.

---

## publish.py (880 lines) — adversarial read of `prune_export`, per the brief

### MAJOR — `prune_export` can be handed an empty or partial `wanted` set and will delete
everything it doesn't recognise, with no floor check and no warning that a directory was
missing

`sync_tree()` builds `wanted` directory-by-directory:

```python
for d in COPY_DIRS:
    root = os.path.join(HERE, d)
    if not os.path.isdir(root):
        continue
```

If `HERE/prompts` (or any `COPY_DIRS` entry) is transiently unavailable when `sync_tree()`
runs — renamed mid-edit, a network/antivirus lock (this project's own docstrings document
Norton locking files under this project repeatedly), a half-finished git operation — this
`continue` is silent: no print, no `silence.note`, nothing distinguishing "this project
genuinely has no `prompts/` directory" from "I couldn't see it this one time." `wanted` then
simply has zero entries with that prefix. `sync_tree()` still finishes successfully (no
exception raised) and calls `prune_export(wanted)` at line 580, which walks
`SITE/prompts/**` and deletes every file in it, because none of them are `rel in wanted`
(line 513: `if rel in wanted: continue` — else `os.remove(p)`). In the limiting case where
*every* `COPY_DIRS` entry is transiently missing, `wanted` is empty and the entire published
`src/`, `prompts/`, `reference/`, `registry_terminal/`, `handoff/` subtree of the export copy
is wiped on the next cycle — the PUBLIC GitHub Pages repo.

There is no minimum-count sanity check anywhere in `prune_export` or its caller (e.g.
"refuse to prune a subtree that would delete more than X% of what's there" or "refuse if
`wanted` is suspiciously smaller than SITE's existing file count"). The module's own header
DOES have a guard for this shape of fault elsewhere (`_is_throwaway`'s structural
temp-directory check in `export_root`), which suggests the pattern is known here — it just
was not applied to this function.

I confirmed the *other* half of the brief's question is NOT reachable as feared: a mid-copy
failure (e.g. `shutil.copy2` raising on a locked file) is unhandled inside `sync_tree()`'s
loop, so it propagates straight out of `sync_tree()` and `prune_export` is never called that
cycle at all (caught by `main()`'s blanket `except Exception`). So a genuinely *partial* copy
never reaches `prune_export` with a half-built `wanted`. The exposure is specifically the
**silent per-directory `continue`**, not an exception path.

Anchor: `for d in COPY_DIRS:` / `if not os.path.isdir(root): continue` (`sync_tree`, ~line
544-545); consuming call `pruned = prune_export(wanted)` (~line 580); the deletion itself
`if rel in wanted: continue` / `os.remove(p)` (~lines 513-517).

### MINOR-to-MAJOR (a real weakness, but currently unreachable on this machine) — the
`SITE == HERE` guard compares un-resolved paths, so a symlink/junction or a case-variant path
can defeat it

```python
if os.path.abspath(SITE) == os.path.abspath(HERE):
    return 0
```

`os.path.abspath` does not resolve symlinks/junctions and does not normalize case. On
Windows, a junction pointed from wherever `PANSCRIPTUM_EXPORT` (or the `USERPROFILE`
fallback) resolves to, back at `HERE`, would produce two *different-looking* path strings for
the *same physical directory* — the equality check passes them as different, the `.git`/live
tree is not recognised as itself, and if a `.is-export-copy` marker happened to exist at that
location (plausible: it's the exact marker `sync_tree()` itself writes into `SITE` every run,
so if `SITE` and `HERE` were ever unified via a junction even briefly, the live tree would
pick up the marker permanently), `prune_export` would proceed to delete real, non-exported
source files out of the live project. Similarly, a case-only difference between `SITE` and
`HERE` (Windows paths are case-insensitive on disk but Python string comparison is
case-sensitive) defeats the same guard. This is a genuine gap in the "REFUSES TO RUN
ANYWHERE BUT THE EXPORT COPY" claim in `prune_export`'s own docstring — the docstring says a
misresolved `SITE` "must read as nothing to do," but the equality check it relies on is
string equality on unresolved paths, not identity of the underlying directory
(`os.path.samefile` would close this). I could not find a live trigger for this on the
current setup (`export_root()`'s fallback is `USERPROFILE/panscriptum-export`, a genuinely
different directory from `HERE`, and nothing in the tree creates a junction), so this is
reported as a latent weakness in the guard's construction, not an observed live failure —
QUESTION/MINOR in current effect, but the fix (`os.path.samefile` with a fallback to the
string comparison when one side doesn't exist yet) is cheap relative to what a miss costs
here.

Anchor: `if os.path.abspath(SITE) == os.path.abspath(HERE):` (`prune_export`, ~line 498).

### MAJOR — `write()`'s temp file uses a fixed name shared by two processes the code itself
says can legitimately run concurrently

```python
tmp = STATE_JSON + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=1)
if not silence.replace_retry(tmp, STATE_JSON):
```

This is exactly the "fixed `.tmp` name, two writers" shape the brief calls out — and
`silence.write_json` (used correctly elsewhere in this same file's sibling modules, see
below) exists specifically because it builds its temp name from pid+thread to avoid this.
`write()` does not use it; it hand-rolls the older, vulnerable pattern. And this file's own
`main()` explicitly documents that two processes CAN be running `write()` concurrently: the
standing `--loop` daemon and a manual one-shot `--push` are allowed to coexist on purpose —
`codewatch.claim_singleton("publish")` is called "ONLY IN LOOP MODE," with the comment "a
one-shot is not a second daemon... a safety that blocks the operator from acting is a safety
that will be removed" (~lines 843-847). So the exact two-writers-one-repo situation `push()`
elsewhere spends a long comment worrying about (fetch-rebase-first, run #5's five silent
failures) is reachable for `write()`'s tmp file too: if the loop daemon and a hand-run
`--push` both call `write()` within the same brief window, both open
`docs/state.json.tmp` for write, and whichever's `os.replace` runs last wins — the other's
`json.dump` may be partially interleaved on a shared file object at the OS level (two
independent `open(tmp, "w")` calls on Windows will each truncate-and-write the same path;
the loser's `os.replace` can then promote a *file the other process already replaced away
from*, or the requester's own `json.dump` write can be truncated by the other process's
`open(..., "w")` opening the same path mid-write). This is a plausible corrupted-or-stale
`docs/state.json` on the public site, not merely a lost update.

Anchor: `tmp = STATE_JSON + ".tmp"` (`write`, ~line 653); the concurrency permission comment
`# ONLY IN LOOP MODE, and this needed correcting within the minute` (~line 843-847).

### Verified FIXED — the filed "unopenable file reported as clean" finding on
`scan_for_secrets`

Per the brief's request to re-check this: it is fixed. `_scan_units` streams every file via a
generator (`open(path, encoding="utf-8", errors="replace")`), and the iteration happens
*inside* the `try` block in `scan_for_secrets` (`for i, line in _scan_units(p, ...):` at
~line 400, wrapped by `try: ... except Exception as e:` at ~line 399/431). Because Python
generators are lazy, the `open()` call (and any `PermissionError`/`OSError` it raises) fires
on first `next()`, i.e. inside that same `try`. The `except` branch reports a named
`UNSCANNABLE` finding (`hits.append(...)`) rather than skipping — matching the docstring's
claim exactly ("a file that genuinely cannot be read is REFUSED BY NAME... rather than
skipped"). No live bug found here; reporting it fixed rather than filing it again.

Anchor: `def scan_for_secrets` docstring "SIZE IS NOT A REASON TO SKIP, AND UNREADABLE IS NOT
CLEAN" (~line 363); the try/except around `_scan_units` (~lines 399-436).

### QUESTION, not a defect — the export tree's contents outside `wanted` are unconditionally
prunable, including anything a human placed there by hand

`prune_export`'s own docstring says this is deliberate ("Anything else under a `COPY_DIRS`
subtree of the export copy is gone... none of them are mirrored from anything, so none of
them are this function's business"). That is an explicit, reasoned design choice, not a
silent one — flagged here only because the brief asked the adversarial question directly, and
the answer is: yes, a file a person hand-added inside `SITE/src/`, `SITE/prompts/`, etc.
(notes, a one-off script) would be deleted on the very next publish cycle, with no distinction
made between "stray" and "deliberate." Worth the owner's awareness, not a code defect against
the stated design.

---

## policy.py (328 lines)

**Guidance check 1 — is the `op="absent"` exemption drawn exactly where the docstring says?**
Yes. Docstring (lines 141-149) and code (line 150) match exactly:

```python
vacuous = [r for r in results if r["ok"] and not r["found"] and r["op"] != "absent"]
```

**Guidance check 2 — does any other operator have the same "only truthful passing case is
`found=False`" property and is it still being flagged?** No. Walking every operator in `OPS`:
`exists`/`truthy`/`gte`/`lte`/`in_range`/`nonempty`/`len_gte`/`matches`/`glob`/`is_type` all
require `v is not None` (or an equivalent truthy/length check) to pass, so their passing case
requires `found=True` in the ordinary case — they don't share `absent`'s shape. `ne` and `eq`
can pass vacuously in the specific case the rule's `arg` happens to equal `None`, but that is
not their *only* truthful passing case (unlike `absent`, whose entire reason for existing is
"the field is missing") — those remain correctly caught by the general vacuous-pass check, as
intended. `not_matches` is explicitly discussed in the docstring itself and correctly stays
un-exempted, confirmed by reading its lambda (`v is None or re.search(a, str(v)) is None` —
two distinct truthful-pass shapes, only one of which is "absent"). No other operator needs
the same carve-out; the exemption is precisely scoped. No defect found.

Read the rest of the file (`resolve`, `check_rule`, `evaluate`, `report`, the three rule
tables, `main`'s `--limit`/partial-run reporting) — nothing else wrong. `main()` correctly
counts unreadable records by name rather than dropping them silently, correctly labels
partial runs, and correctly separates INFO severity from gating failures.

---

## zfighters.py (504 lines)

Read in full. **Not mid-edit** — the file is internally consistent, every function is
complete, `ROSTER` closes cleanly, and the trailing comments describe fixes that are already
landed in the code beside them (e.g. the `write_json` return-value check at line 492 is
present and matches its own comment, not merely described). If another agent is working on
this file concurrently, no partial/contradictory state was visible at read time.

No new defects found. Of note (not a defect, a correctly-guarded prior fix, confirmed
in-effect): `main()`'s `--full` path uses `d.get("provenance", "")` rather than `d["provenance"]`
specifically because the Son Goku sheet (carried in from
`REFERENCE_ASSAYS_PRESENCE.json`) has no `provenance` key on its axes — verified by reading
the comment's claim against the actual code, which does use `.get` with a default, so this
does not crash. The final `write_json` return-value check (this file's own fix, called out in
its comment) is real: `if not silence.write_json(OUT, out, ...): ... return 1` — a refused
write is reported as a refused write, not a success. Contrast with `axis_correlation.py`
below, which has the exact bug this file's comment describes fixing.

Display-only truncations (`epoch[:38]`, `d["cited"][:60]` in print formatting) are console
column-width formatting, not data loss — the full values are in `ROSTER`/`out` and land in
`Z_FIGHTERS.json` untouched. Not a Hard Rule 0 violation.

---

## estate.py (403 lines) — edited today

Read in full. The severity-grading rework (`bad=True/False` distinguishing real faults from
known-accepted conditions and plain measurements) is internally consistent with its own
docstring's stated rationale in every call site I checked (`charter()`, `written()`,
`terminal()`, `external()`). No tautological check found, no dead guard, no discarded write
verdict (this module never writes shared state — it's read-only auditing).

**QUESTION** (not filed as a defect, flagging because Hard Rule 0 is zero-tolerance and this
is exactly the shape it warns about): `charter()`'s "catalogued sources with NO charter spine
code" row caps its *example list* at 4:

```python
note("catalogued sources with NO charter spine code", f"{len(un)} — e.g. " + ", ".join(un[:4]))
```

The count (`len(un)`) is always the true, full count — nothing about the number of affected
sources is hidden or under-reported — only the illustrative names shown alongside it are
capped, and the string is explicitly labelled "e.g." I read this as different in kind from
the Hard Rule 0 examples (a `roster(limit=600)` *function* silently returning a truncated
universe as if it were the whole one), since the actual data consumed by any downstream
process is `len(un)` and `un` itself (both full), and only a display string is short. Flagging
as a question per audit discipline rather than asserting it's fine outright, since the rule
is written as zero-tolerance and this file otherwise treats caps as forbidden.

Everything else read clean: `artifacts()` walks every file under every root with no sampling
(matches its own docstring's claim "No sampling anywhere" — verified true by reading the
loop, not just trusting the comment); `inspect()`'s zero-byte/log exemption is narrowly
scoped to `.log/.tmp/.out/.err`; the `_BAD_CHARS` control-character scan runs over every text
file, not just regex-bearing modules.

---

## axis_correlation.py (287 lines) — edited today

### MAJOR — `write()` discards `silence.write_json`'s return value; a refused write to the
public correlation matrix is reported as a success

```python
def write(doc=None):
    doc = doc or measure()
    doc["note"] = (...)
    silence.write_json(OUT, doc, indent=2, sort_keys=True)
    return OUT
```

The return value of `silence.write_json` (`True`/`False`, per its own docstring: "Returns
True if the file landed. Never raises on a denied replace") is thrown away. `main()` then
does `print("\nwrote " + write(doc))` unconditionally — so a denied replace (e.g. a reader
holding `AXIS_CORRELATION.json` open, the exact scenario `silence.replace_retry`'s own
docstring says is routine on this machine — "Norton scanning... a person with `docs/state.json`
open") prints "wrote data/AXIS_CORRELATION.json" while the file on disk is unchanged from the
previous run. This is precisely the discarded-verdict pattern item #5 in the brief describes,
and it is precisely the bug `zfighters.py` — a sibling module in this same batch — fixed for
the identical helper function, with a comment explaining exactly this failure mode ("a
crash mid-write... the quieter half of the same risk... `write_json` returns whether the
rename LANDED, this discarded it"). `axis_correlation.py` has the bug `zfighters.py`'s own
comment is describing having been fixed elsewhere.

Anchor: `silence.write_json(OUT, doc, indent=2, sort_keys=True)` with no assignment/check,
`write()` (~line 189); consumed unconditionally at `print("\nwrote " + write(doc))` in
`main()` (~line 281).

### QUESTION — `widening()` silently clamps a potentially-invalid negative total variance to
`1e-12` rather than surfacing the inconsistency

```python
total = max(indep + cov, 1e-12)
return math.sqrt(total / indep) if indep else 1.0, indep, cov
```

`cov` is built by summing `2 * w_a * w_b * rho(a,b) * sigma^2` over every axis pair using
independently-measured pairwise correlations (`AXIS_CORRELATION.json`'s `pairs`). Pairwise
correlations measured independently are not guaranteed to form a positive-semidefinite
correlation matrix, so for some weight vectors `w` the quadratic form `indep + cov` (a
variance) can go mathematically negative — which would mean the measured correlation
structure is internally inconsistent, a genuine finding worth surfacing, not a numerical
edge case to paper over. The `max(..., 1e-12)` clamp converts that case into a near-zero
`total`, producing (via `sqrt(total/indep)`) a widening factor near zero — i.e. an interval
*narrower* than the independent case, the exact opposite of what this module exists to
guarantee ("every published interval in the library is too NARROW... an overstated
confidence is a claim the evidence does not support," per the module's own docstring). This
mirrors the same clamp shape in `rigor.lognormal_product`'s `sd = math.sqrt(max(var, 0.0))`
for its `correlations` parameter — same shape, different module. **I could not find a live
trigger for either**: `axis_correlation.py`'s own measured matrix (`data/AXIS_CORRELATION.json`)
has all-positive pairwise `r` values as documented in the module header ("EVERY sizeable pair
positive, none meaningfully negative"), and no caller in the codebase currently passes
`rigor.lognormal_product`'s `correlations` argument at all (checked: `rigor.py`'s own `main()`
and `verify_math.py`'s test both call it with no `correlations`). Reporting as a QUESTION
because it may be deliberate defensive clamping against a `sqrt` domain error rather than an
oversight, but the current silent handling is inconsistent with this module's own stated
mission of never letting an interval look narrower/more-confident than the evidence supports.

Anchor: `total = max(indep + cov, 1e-12)` (`widening`, ~line 254).

### QUESTION, not a defect — `--top` caps the console print, not the data

```python
ap.add_argument("--top", type=int, default=15)
...
for key, v in ranked[:a.top]:
```

This is display-only: `write(doc)` persists the full, untruncated `doc["pairs"]` regardless
of `--top`, and `measure()` itself never truncates. Flagged only because `--top N` is
literally the shape Hard Rule 0 names as forbidden ("no `top N`... truncation of... an entry
list") — but unlike `policy.py`'s `--limit` (which caps what is *evaluated*, and is correctly
labelled `PARTIAL` when used), this caps only what is *echoed to the terminal* after full
computation. I read this as compliant with the rule's actual intent (no smaller universe is
returned or persisted) but note it because the pattern is worth the owner's eyes given how
literally it matches the forbidden shape.

Everything else in the file read clean: `observations()` correctly reports which `SOURCES`
were read vs missing (no silent shrink of the corpus), `_scores_of` correctly treats an
absent `scores` key as "not yet measured" rather than zero, `_pearson`'s zero-variance guard
correctly returns `None` rather than dividing by zero (a real guard on a real degenerate
case, not a masked failure), and `load()`/`rho()`'s fallback-to-mean-correlation behaviour is
explicitly and correctly documented as distinct from the "no matrix at all" case.

---

## recover_folder_records.py (216 lines)

Read in full. Well-hardened already: every shared-file write is gated on
`silence.write_json`'s return value and reported honestly on denial (`WRITE DENIED {name};
roll left untouched`, `ROLL WRITE DENIED`), the "already populated" check treats an unreadable
existing record as populated (fail-closed, matches its own documented reasoning), and the
excluded-register-sources set (`{"ME"}`) is justified with a specific, checkable account of
what it would otherwise misfile. No caps on the actual recovery logic — `name[:48]` in the
final print is column-width display formatting only. No defect found; nothing to report
beyond a clean read.

---

## withdraw_chapters.py (205 lines)

### MAJOR — confirmed: the stray-file sweep's `shutil.move` is unguarded, unlike its own twin
eleven lines above, and a failure there can leave the catalog and the tree disagreeing

The main per-catalog-entry move loop is correctly guarded:

```python
if a.go:
    try:
        shutil.move(src, os.path.join(arch, sub, os.path.basename(src)))
    except Exception as e:
        print("  move failed: %s (%s)" % (src, e))
        stuck.add(_addr)          # keeps its catalog record on failure
        continue
```

But the second sweep — for files sitting in `output/raw` that the catalog never claimed —
has no such guard:

```python
if not filtered and os.path.isdir(rawdir):
    for f in sorted(os.listdir(rawdir)):
        src = os.path.join(rawdir, f)
        if not os.path.isfile(src):
            continue
        if a.go:
            shutil.move(src, os.path.join(arch, "raw", f))   # <-- no try/except
        extra += 1
```

If this `shutil.move` raises (locked file, permission denied, a destination-name collision,
disk full — the same failure modes the guarded twin above explicitly exists to catch), the
exception is unhandled and propagates out of `main()` as a crash — and this block runs
*before* the code that computes `withdrawn`/`remaining` and writes `catalog.json` back
(lines 162-185, all downstream of this loop). Since the main per-catalog-entry loop above it
has *already run and already physically moved* every catalog-tracked chapter file that
succeeded, a crash here leaves those files sitting in the archive directory while
`catalog.json` on disk is never rewritten — it still lists the old `raw_path`/`compressed_path`
for files that have already left. That is exactly the tree-and-catalog disagreement the
brief's open finding describes, and it is now file-and-line confirmed rather than merely
suspected: the crash point is provably before the catalog write, and the files moved before
the crash are provably no longer where the stale catalog says they are.

A secondary, related risk in the same block: two different stray files sharing a basename
(across different subdirectories of `output/raw`, if any exist) would silently overwrite one
another at the shared destination `os.path.join(arch, "raw", f)` — `shutil.move` does not
warn on overwrite. I did not confirm whether basename collisions are currently possible given
how `output/raw` is populated elsewhere, so this is noted as a secondary observation rather
than a standalone finding.

Anchor: `shutil.move(src, os.path.join(arch, "raw", f))` with no surrounding try/except,
inside the "Anything left in output/raw that the catalog never claimed" block (~lines
158-159), contrasted with the guarded `shutil.move` in the main loop (~line 136).

### MINOR — a second discarded `write_json` verdict, lower stakes than the operational
catalog write beside it

```python
silence.write_json(os.path.join(arch, "catalog.withdrawn.json"), withdrawn, indent=2)
```

Unlike the very next write in the same function —
`catalog_landed = silence.write_json(CATALOG, remaining, indent=2)`, whose return value IS
checked and reported (`CATALOG WRITE DENIED` message) — the archive-record write two lines
above it does not check its own return value. This is the same discarded-verdict shape as
`axis_correlation.write()` above, but lower severity here: `catalog.withdrawn.json` is a
supplementary record of what a given run withdrew (for audit trail), not the operational
catalog the rest of the pipeline reads, so a denied write here does not cause the tree and
the live catalog to disagree — it just means the archive folder's own manifest of what it
holds could silently fail to land.

Anchor: `silence.write_json(os.path.join(arch, "catalog.withdrawn.json"), withdrawn,
indent=2)`, no assignment (~line 170), immediately followed by the correctly-checked twin
(~line 185).

Everything else in the file read clean: `select()` is pure and exact-match only (no fuzzy
matching that could withdraw the wrong chapters), the empty-selection-after-a-named-filter
case correctly refuses rather than silently no-op'ing, the pre-withdrawal snapshot is
verified (`SNAP.verify(sid)`) before any file moves, and the default `--label` is computed at
runtime rather than the previously-hardcoded date (confirmed fixed, matches its own comment).

---

## rigor.py (908 lines)

Read in full — this is a dense statistics/MDL library (AHP/Perron eigenvector weights,
Bradley-Terry with Ford's-condition connectivity checks, MDL bit-counting, log-normal
uncertainty propagation, extreme-value/Gumbel order-statistic correction, a derivation-graph
"resonance" measure). Traced the math against the cited references
(Saaty 1977; Jiang/Lim/Yao/Ye 2011; Hunter 2004; Rissanen 1978; Sandberg/Drexler/Ord 2018)
rather than trusting the docstrings' self-description.

**Verified correct, not a defect (checked because it looked suspicious at first read):**
`perron_weights`'s `cr = (ci / ri) if ri > 0 else 0.0` guard for `n <= 2`, where
`SAATY_RI[1] = SAATY_RI[2] = 0.0`. This looks like the "guard hides a real zero" antipattern
at first glance, but it is not: any 2x2 positive-reciprocal matrix `[[1,a],[1/a,1]]` has
`det = 0` and `trace = 2` by construction, so `lambda_max = 2 = n` and `CI = 0` are
*mathematically forced*, never merely typical. The guard prevents a genuine `0/0` (NaN), not a
hidden failure — confirmed by working the algebra, not by reading the comment.

**QUESTION, paired with the same shape found independently in `axis_correlation.py`
(above):** `lognormal_product`'s `sd = math.sqrt(max(var, 0.0))` silently clamps a
theoretically-possible negative variance (reachable only when its `correlations` argument
supplies pairwise correlations strong enough to make the quadratic form negative) to zero
rather than surfacing the inconsistency. Checked every call site in the codebase
(`rigor.py`'s own `main()`, `verify_math.py`'s test) — none currently pass `correlations`, so
this is unexercised dead-weight risk today, not a live bug. Noting it here because it's the
same clamp-instead-of-report shape as `axis_correlation.widening()`'s `max(indep+cov, 1e-12)`,
and worth fixing together if either is touched.

`mathematical_resonance()`'s `"load_bearing"` key is explicitly documented and confirmed
**not** truncated (`sorted(fanout.items(), ...)`, full list) — only `main()`'s print slices
`[:6]` for the terminal, matching the file's own Hard-Rule-0-aware comment
("Ranked, never truncated... the sole consumer slices for display").

`bradley_terry`'s Ford's-condition connectivity check (`_strongly_connected`, an iterative
Tarjan SCC) is correctly built over the *raw, unregularised* `wins` graph even when a `prior`
is supplied (confirmed by reading `beat = [(a, b) for (a, b), c in wins.items() if c > 0]`,
built from `wins`, not from the prior-augmented `W`) — matching the docstring's claim that
`identified` must answer "did the data connect these entities," not "did the regularisation."
`undefeated`/`winless` are likewise computed from `observed` (the pre-prior copy of `W`), not
the augmented matrix — also correct, and specifically called out as a prior fix in the file's
own comment, which I verified rather than took on faith.

No other defects found in this module.

---

## Not readable / not covered

None. All 8 modules in this batch were read in full.
