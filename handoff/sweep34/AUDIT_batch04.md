# Sweep #34 — batch 04 audit

Modules read end to end: `src/standards.py` (1558), `src/corpus_db.py` (467), `src/pick_model.py`
(357), `src/weave_index.py` (276), `src/coverage.py` (243), `src/liveness.py` (205),
`src/module_index.py` (110). 3,216 lines.

Nothing under `src/` was edited. Every finding below was re-read in the source and, where a
number was involved, measured against the disk this shift. Anything I could not prove is under
QUESTIONS, not FINDINGS.

Ground truth measured during this audit:

    data/records/*.json                              216 files
    state/corpus.db meta.entries                     197,334
    state/corpus.db meta.sources                     216
    state/corpus.db meta.evidence                    143,865
    data/readfeats/*/*.json + data/feats/*/*.json    144,107 files (0 unparseable)
    src/*.py                                         113
    liveness.scan()                                  38 dead, 0 tautology, 0 phantom, 0 unparsed

---

## src/liveness.py

### FINDING L1 (MAJOR) — the DEAD pass cannot see the example in its own docstring

`liveness.py:10-11` names the founding case:

    #  * `coverage._p()` -- a fully documented cache-path helper with no callers, free to drift out of
    #    step with the real formula it duplicates.

`coverage._p()` still exists (`src/coverage.py:47`) and still has no callers — `grep -n "_p("
src/coverage.py` returns only the `def` line, and the only other mention of it anywhere in `src/`
is the liveness docstring above. It is **not** in `liveness.scan()["dead"]`.

The reason is the `used` set:

    src/liveness.py:101-108
    for name, t in trees.items():
        for node in ast.walk(t):
            if isinstance(node, ast.Name):
                used.add(node.id)
            elif isinstance(node, ast.Attribute):
                used.add(node.attr)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                used.add(node.value.strip())

One flat set of bare identifiers, with no module and no scope. `_p` lands in it because two
unrelated modules use it as a **local loop variable**:

    src/cleanup.py:89-91
    for _n, _p in (("_NAV", _NAV), ("_EMPTY_MECHANIC", _EMPTY_MECHANIC),
                   ("_SETTING_META", None)):
        if _p is not None and any(ord(c) < 32 for c in _p.pattern):

    src/tells.py:149-150
    for _n, _p in list(_COMPILED.items()) + list(_LEX.items()):
        if any(ord(c) < 32 and c not in "\n\t" for c in _p.pattern):

So `if fn not in used` (line 123) is satisfied by a loop variable in a different file. Any
module-level function whose bare name collides with any local, parameter or attribute anywhere in
`src/` is invisible to the DEAD pass.

Magnitude: 53 non-exempt module-level functions in `src/` are never a call target, never an
attribute access and never a string constant anywhere in the tree, yet are reported live. Most
are legitimately dispatched by bare name (drill nets, foreman remedies), so 53 is an upper bound
— but `coverage._p()` is in that list and is provably dead, so the true count is at least 39.

Consequence: `drill.LIVENESS_CEILING = 38` (`src/drill.py:42`) ratchets against an undercount, and
`scan()` currently returns exactly 38. The docstring is careful to disclaim the TAUTOLOGY pass
("Reporting zero tautologies must not be read as 'there are none'", line 38) but makes the DEAD
pass an unqualified claim: "a module-level function nobody calls, from anywhere in src/" (line 20).

### FINDING L2 (MAJOR) — `unparsed` is counted in the total but never printed

`scan()` returns four keys (line 179-180) and `main()` sums all four:

    src/liveness.py:188
    total = sum(len(v) for v in r.values())

but the display loop covers three:

    src/liveness.py:190-193
    for kind, label in (("tautology", ...), ("phantom", ...), ("dead", ...)):

and the summary line breaks the total into the same three:

    src/liveness.py:199-200
    print("\nliveness: %d finding(s) — %d tautology, %d phantom, %d dead"
          % (total, len(r["tautology"]), len(r["phantom"]), len(r["dead"])))

With one unparseable module the header says "39 finding(s) — 0 tautology, 0 phantom, 38 dead", the
arithmetic visibly fails to close, and the module that will not parse is never named. That is the
one output path for the fix at lines 86-95, whose own comment says the point is that the module
gets "reported as a finding of its own". It reaches the ratchet; it does not reach the reader.

### FINDING L3 (MINOR) — the parse failure's reason is discarded

    src/liveness.py:72-77
    def _parse(path):
        try:
            with open(path, encoding="utf-8") as fh:
                return ast.parse(fh.read(), filename=path)
        except Exception:
            return None

The `unparsed` row can therefore only ever say "will not parse", never whether it was a
SyntaxError, a control character, or a mid-write truncation — the three causes the comment at
lines 86-93 explicitly lists as the ones it exists to catch.

---

## src/corpus_db.py

### FINDING D1 (MAJOR) — a record that will not parse vanishes from the index in silence, and the count is then reported as a total

    src/corpus_db.py:140-145
    for p in sorted(glob.glob(os.path.join(HERE, "data", "records", "*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                rec = json.load(f)
        except Exception:
            continue

Same shape for evidence at lines 181-186. `n_src` and `n_entry` are then written into `meta` and
printed as the corpus totals (lines 204-205, 435-436). A corrupt record subtracts itself from
"216 sources, 197,334 entries" and nothing anywhere says so.

The module is inconsistent with itself: `drift()`, reading the *same* files for the *same*
purpose, records the failure —

    src/corpus_db.py:296-299
        try:
            with open(p, encoding="utf-8") as f:
                real += len(json.load(f).get("entries") or [])
        except Exception:
            silence.note("corpus_db.py:drift-record")

`silence` is already imported at line 53. (Note: all 216 records and all 144,107 evidence files
parse cleanly today, so this is a latent defect, not an active miscount.)

### FINDING D2 (MAJOR) — fixed `.tmp` path, and the pre-clean deletes a concurrent rebuild's database

    src/corpus_db.py:96-100
    tmp = DB + ".tmp"
    for p in (tmp, tmp + "-journal"):
        if os.path.exists(p):
            os.remove(p)
    con = connect(tmp)

Two rebuilds running at once write the same `state/corpus.db.tmp`, and the second one's cleanup
loop deletes the first one's in-progress database out from under its open connection. The project
rule is stated twice in the tree:

    src/silence.py:358-361 (write_json docstring)
    THE TMP NAME CARRIES PID AND THREAD, which the older hand-rolled `path + ".tmp"` sites did
    not. Two writers of the same path otherwise collide on the temp file itself, and the loser
    can replace the winner's target with a partial file

    src/module_index.py:88-90
    The tmp name carries pid and thread for the same reason
    `write_json` does: two writers otherwise collide on the temp file itself and the loser can
    land a half-built page over the winner's.

`module_index.py:91` does it correctly; `corpus_db.py:96` does not. `replace_retry` also does not
unlink `tmp` on failure (`src/silence.py:327-336`), so a denied rebuild leaves the whole temp
database on disk until the next run's cleanup.

### FINDING D3 (MAJOR) — the canned queries truncate ranked work lists

    src/corpus_db.py:336-353
    CANNED = {
        "coverage": "... FROM source ORDER BY entries DESC LIMIT 15",
        ...
        "types": "... GROUP BY type ORDER BY n DESC LIMIT 25",
        "unjudged": "SELECT source, COUNT(*) n FROM entry WHERE catalogued=0 AND excluded=0 "
                    "GROUP BY source ORDER BY n DESC LIMIT 15",
        "evidence": "... ORDER BY feats DESC LIMIT 15",
        "refused": "... ORDER BY n DESC LIMIT 15",
        "worst_cited": "... FROM source WHERE entries>=40 ORDER BY pct ASC LIMIT 15",
    }

`unjudged` and `worst_cited` are ordered work lists — sources with unjudged entries, sources with
the worst citation rate — cut to fifteen. Hard Rule 0 forbids ranking-then-truncating. That
`unaddressed`, `hostless` and `categories` in the same dict carry **no** LIMIT shows the author
knew where the line was. The comment above the dict (lines 333-335) says the point is "so two
people asking the same question get the same number" — they get the same *truncated* number.

These are also the list `datasette_metadata()` renders (line 384), so the browsable front end
inherits every cap.

### FINDING D4 (MINOR) — `datasette_metadata()` writes a shared file non-atomically

    src/corpus_db.py:390-393
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    return path

`state/datasette.json` is read by a running Datasette server. `silence` is imported at line 53 and
`silence.write_json` is the named remedy for exactly this (`src/silence.py:346-364`); the module
already uses `silence.replace_retry` at line 215.

### FINDING D5 (MINOR) — the docstring's entry count is stale by ~88,000, in the present tense

    src/corpus_db.py:5-6
    Every question anyone asks about this corpus currently costs a throwaway Python script that walks
    216 JSON files and 109,295 entries.

    src/corpus_db.py:36
    against a corpus of 109,295 entries

    src/corpus_db.py:410-411
    ap.add_argument("--no-evidence", action="store_true",
                    help="skip the 109k evidence files (much faster)")

Disk today: 216 record files (correct), **197,334** entries, **144,107** evidence files. The
later mentions of 109,295 inside `freshness()`'s docstring (lines 234-236) are explicitly
timestamped historical measurements and are fine; these three are present-tense claims. This is
the module whose closing paragraph is "anything that disagrees with the records is this file being
stale" (line 41).

### FINDING D6 (MINOR) — `evidence_limit` is a cap parameter no caller sets and no flag exposes

    src/corpus_db.py:87
    def rebuild(include_evidence=True, evidence_limit=None):
    ...
    src/corpus_db.py:178-179
        if evidence_limit:
            files = files[:evidence_limit]

`grep -rn "evidence_limit" src/` finds only these three lines. `main()` calls
`rebuild(include_evidence=not a.no_evidence)` (line 428) and there is no `--evidence-limit` flag.
It is a dead parameter, and the slice it guards is applied to an unordered concatenation of two
globs, so if it were ever set the sample would be arbitrary rather than ranked.

### FINDING D7 (MINOR) — a locked or corrupt database is reported as an absent one

    src/corpus_db.py:220-227
    def age_seconds():
        try:
            ...
        except Exception:
            return None

    src/corpus_db.py:451-453
    age = age_seconds()
    print("corpus.db %s" % ("absent -- run --rebuild"
                            if age is None else "built %.1f min ago" % (age / 60)))

`freshness()` distinguishes "no index", "index unreadable" and "index does not record when it was
built" (lines 251, 257, 260) and its own banner then collapses all three back to
`"[ NO INDEX — run --rebuild. These are not results. ]"` (`_freshness_banner`, line 312-313),
because it only tests `age_seconds is None`. The reason `freshness()` computed is thrown away by
both readers.

---

## src/standards.py

### FINDING S1 (MAJOR) — "N/N standards met" where N is only the standards that managed to emit

    src/standards.py:1509-1512
    def report(state=None):
        rows = check(state)
        bad = [r for r in rows if not r["holds"]]
        lines = [f"{len(rows) - len(bad)}/{len(rows)} standards met"]

`rows` is whatever `check()` appended. Roughly eighteen standards in `check()` live inside a
`try: ... except Exception: silence.note(...)` whose body contains the only `out.append` for that
standard, so when the input file is missing, unreadable, or the import fails, the standard does
not appear at all and the denominator shrinks with it. The blocks are at lines 554-577
(reader's gate), 802-826 (roster audit), 828-841 (shelfmarks), 848-876 (reference assays),
885-903 (charter regression), 947-973 (three allsweep standards), 976-1013 (catalogue coverage),
1023-1041 (sweep freshness), 1048-1118 (job advancing), 1132-1177 (unrecognised pool), 1190-1206
(fandom), 1208-1216 (disk), 1224-1242 (shelf ranks), 1245-1273 (runner), 1278-1298 (token flow),
1300-1326 (jobs alive), 1363-1373 (publish age), 1376-1455 (provider models), 1463-1484
(the floor self-check itself). `data/SHELF_RANKS.json` is absent right now, so that standard is
already gone from every render.

The file diagnoses this defect twice and fixes only the two instances it was looking at:

    src/standards.py:755-758
    # IT IS APPENDED UNCONDITIONALLY NOW, INCLUDING WHEN IT CANNOT BE MEASURED. A standard that
    # vanishes on a missing input is green by absence -- the exact defect batch 03 catalogued
    # across the data-file-backed standards in this file, and the one that hid this bug for its
    # whole life. UNMEASURED is a reading; silence is not.

    src/standards.py:922-929
    # A STANDARD THAT DOES NOT EMIT IS WORSE THAN ONE THAT FAILS: it does not appear on the
    # page at all, so nobody can even see that it went unmeasured. ... The check that exists to
    # catch an unmeasured floor cannot see an absent one.

The headline count is the last place that could have caught the rest, and it is computed from the
survivors. `work_orders()` (line 1492) has the same blind spot: it filters `check(state)`, so an
absent standard can never be dispatched.

### FINDING S2 (MAJOR) — the job-stall stamp file: fixed `.tmp` and a discarded write verdict

    src/standards.py:1101-1104
    tmp = JOB_WATCH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cur, f)
    silence.replace_retry(tmp, JOB_WATCH)

The boolean is dropped. If the replace is denied — and `state/job_progress.json` is read by every
`check()` run, which is the module's own stated normal case for `replace_retry` — the size stamps
never persist, `prev` stays stale, `job_stamp()` returns `held=False`, and `quiet_min` can never
reach `MAX_JOB_SILENCE_MIN`. That is precisely the failure the comment eleven lines above says
was already found and fixed once:

    src/standards.py:1072-1079
    # WHEN DID IT LAST MOVE, not when did this check last run. `at` was re-stamped to
    # `now` on every pass, so `quiet_min` measured the interval between two consecutive
    # standards runs ... The standard this file's own
    # docstring calls "the failure this whole library is built to refuse" was therefore
    # structurally unable to fire, for any job, and had been reporting "all advancing"
    # by construction.

The same line also uses a fixed `JOB_WATCH + ".tmp"` — the hand-rolled shape `silence.write_json`
exists to replace (`src/silence.py:358-361`), while `silence` is imported at line 47 and
`silence.replace_retry` is being called on the very next line.

### FINDING S3 (MINOR) — two stale `silence.note` line tags

    src/standards.py:812      silence.note("standards.py:370")
    src/standards.py:891      silence.note("standards.py:449")

Neither line number points at its own call site. Both are on the failure path of a data-file read
(`ROSTER_PURGES.json` and `CHARTER_REGRESSION.json`), so a triage reading `health.py --failures`
is sent 440 lines away from the code that failed. Every other `silence.note` in the file uses a
symbolic tag (`standards.py:ledger`, `standards.py:shelfmarks`, ...); these two are the leftovers.

### FINDING S4 (MINOR) — caps on the exact fields the order text tells a person to read

    src/standards.py:1230
    (", ".join(_pending)[:120] if _pending else "none outstanding"),

    src/standards.py:983
    worst = sorted(good, key=lambda c: c.get("coverage", 0))[:3]

The first truncates the list of sources whose spine code needs amending mid-name; the second keeps
three of the worst-covered sources for the reading a person acts on. This is the shape the file
itself calls out and says to grep the tree for:

    src/standards.py:1135-1144
    # EVERY ROW, ITS WHOLE TEXT, AND ITS AGE. This expression used to carry THREE caps at
    # once on the one field the order below tells a person to read: `[:3]` kept only the
    # three highest-count rows, `[:60]` cut each error mid-sentence ... This is m145's
    # sentence exactly (`available_sample: models[:8]`, a cap on the field a person reads to
    # act) in a second file, which is lesson 14: fix a shape, then grep the tree for it.

The grep was not done; two more instances of the same shape are in the same function.

### FINDING S5 (MINOR) — `main()` runs `check()` twice, firing every live probe twice

    src/standards.py:1553-1554
    print(report())
    return 1 if work_orders() else 0

`report()` calls `check()` (line 1510) and `work_orders()` calls `check()` again (line 1492), both
with `state=None`, so each builds its own `dashboard.state()`. Between them the second pass repeats
a DNS lookup plus a TCP connect per address with an 8s timeout (`fandom_ipv4_reachable`, line 1191),
a `powershell Get-CimInstance` with a 60s timeout (line 1338), a `tasklist` spawn, and a full
`data/readfeats/**` walk when the 120s `_UNANS_CACHE` has expired. The two passes are also free to
disagree: the report can print a standard as met and the exit code can be 1 for the same standard.

### FINDING S6 (MINOR) — a declared floor the floor-auditor cannot see

    src/standards.py:1465-1467
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    declared = set(_re.findall(r"^(M(?:IN|AX)_[A-Z_]+)\s*=", src, _re.M))
    body = src[src.index("def check("):]

The pattern requires the name to *start* with `MIN_`/`MAX_`, so

    src/standards.py:361
    CHARTER_REGRESSION_MAX_AGE_H = 26

is not in `declared` at all. It is a real floor — it decides whether "the automation reproduces the
charter" holds (line 395) — and its only use is inside `charter_regression_verdict()` at line 364,
which is defined *above* `def check(`, so it would also be outside `body` if the pattern did match
it. The standard whose order text is "A floor nothing checks is a promise that something is being
watched when nothing is" (line 1480) has a floor it structurally cannot check.

---

## src/weave_index.py

### FINDING W1 (MAJOR) — `designations()` stats the whole records directory on every call, including cache hits

    src/weave_index.py:109-112
    cacheable = records is None
    sig = _records_sig()[1] if cacheable else None
    if cacheable and _DESIGNATIONS is not None and _DESIGNATIONS[0] == sig:
        return _DESIGNATIONS[1]

`_records_sig()` globs `data/records/*.json` and calls `os.path.getmtime` on all 216 of them
(lines 173-175) — and it runs **before** the cache check, so a hit costs the same directory walk
as a miss. The call chain makes that per-entry:

    src/weave_index.py:138    known = designations()          # in continuity_of()
    src/weave_index.py:151    keep = continuity_of(name)      # in norm()
    src/weave_index.py:214    key = norm(e.get("name"))       # in build(), per entry

Measured on this machine during this audit:

    first designations()            5.51 s
    200 "cached" designations()     2.718 s   -> 13.59 ms per call
    200 norm('Thor (Earth-616)')    2.763 s

At 13.59 ms per name and 197,334 entries, `build()` spends roughly **45 minutes** doing nothing but
`getmtime`. `chain.py:255` (`idx.setdefault(WI.norm(n), n)`) has the same per-name loop.

The docstring says "Cached against the records directory's own signature, exactly like
`load_records()`" (line 99). `load_records()` is genuinely cheap on a hit because the signature is
the only thing it recomputes and it then returns a list; here the signature computation *is* the
whole cost, so the cache saves the JSON parse and nothing else.

### FINDING W2 (MINOR) — stale `silence.note` line tag

    src/weave_index.py:197        silence.note("weave_index.py:155")

The call site is line 197.

### FINDING W3 (MINOR) — record count in the docstring disagrees with disk

    src/weave_index.py:183-184
    """All records with entries -- cached against the directory's own signature.

    63MB across 217 files (marvel.json alone is 27MB), and this was re-parsed on EVERY

`data/records/` holds 216 `.json` files. `corpus_db.py` says 216 in its own header, so the two
modules disagree with each other as well as with the disk.

---

## src/coverage.py

### FINDING C1 (MAJOR) — the cache save reports success after a denied write

    src/coverage.py:77-88
    def _so_save():
        if not _SO["dirty"]:
            return
        try:
            import silence as _sil
            tmp = _SO_CACHE_P + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(_SO["d"], f)
            _sil.replace_retry(tmp, _SO_CACHE_P)
            _SO["dirty"] = 0
        except Exception:
            silence.note("coverage.py:so-save")

`replace_retry` returns False rather than raising on a persistent denial (`src/silence.py:319-336`),
so `_SO["dirty"] = 0` runs anyway and the process believes its mtime cache landed. The next run
re-parses the whole evidence corpus — which the comment at lines 58-61 says was "on the order of
the whole 874MB corpus per run". The same module's `main()` (line 237) uses the checked path
(`silence.write_json`), and `corpus_db.py:209-215` and `module_index.py:94-103` both carry
comments insisting the verdict must reach the caller.

### FINDING C2 (MINOR) — fixed `.tmp` name on a shared state file

    src/coverage.py:82        tmp = _SO_CACHE_P + ".tmp"

`state/coverage_cache.json` is written by `coverage.measure()`, which the dashboard, standards,
allsweep and the publisher all reach. Two writers collide on the temp file itself — the hazard
`silence.write_json`'s docstring names in full (`src/silence.py:358-361`). `silence` is imported
at line 37.

### FINDING C3 (MAJOR) — `report()` truncates the ranked work lists it labels as the work

    src/coverage.py:212-220
    print("\nSOURCES WITH NO WIKI HOST — nothing can ever be cited here")
    for r in sorted((x for x in rows if not x["host"]), key=lambda x: -x["entries"])[:12]:
        ...
    print("\nWORST COVERED WITH A HOST — where the work is")
    have = [r for r in rows if r["host"] and r["entries"] >= 40]
    for r in sorted(have, key=lambda x: (x["coverage"], -x["entries"]))[:show]:

`show` defaults to 26 in the function signature (line 191) and to 26 again on the CLI
(`ap.add_argument("--show", type=int, default=26)`, line 230), so a default run — which is how
the supervisor runs it — ranks every source and then prints twenty-six. The hostless list has no
flag at all: 12, always. Both headers say in words that these are the outstanding work.

### FINDING C4 (MINOR) — stale `silence.note` line tag

    src/coverage.py:151        silence.note("coverage.py:60")

The call site is line 151. Line 60 is inside the `_SO_CACHE_P` comment block. The sibling tag
eleven lines earlier is symbolic (`coverage.py:so-save`), so this is a leftover.

### FINDING C5 (MINOR) — `_p()` is dead

    src/coverage.py:47-55
    def _p(base, host, name):
        """The entity's natural cache path. M23: reads through here MUST verify ownership.
        ...
        return cachekey.natural_path(base, host, name)

No callers anywhere in `src/`. Its own docstring says it "used to be the whole answer" and that
`state_of()` now goes through `cachekey.candidate_paths` / `cachekey.owns` instead — which is what
lines 105-106 do. It is the exact hazard liveness.py's docstring describes ("free to drift out of
step with the real formula it duplicates") and, per FINDING L1, the detector cannot see it.

### FINDING C6 (MINOR) — `report()` divides by an unguarded denominator

    src/coverage.py:192-206
    n = sum(r["entries"] for r in rows)
    ...
    print(f"\n  CITED       {cited:>8,}  {cited/n:>6.1%}   carries a verbatim feat")

`measure()` guards every one of its own divisions with `max(n, 1)` (lines 185-186); `report()`
does not guard any of its seven. An empty or entry-less `rows` raises `ZeroDivisionError` from
inside the reporting function, after `measure()` has already done all the work.

---

## src/pick_model.py

### FINDING P1 (MINOR) — stale `silence.note` line tag

    src/pick_model.py:211        silence.note("pick_model.py:150")

The call site is line 211. The near-identical function 25 lines above uses a symbolic tag
(`silence.note("pick_model.py:total_vram")`, line 186), so the two `nvidia-smi` failure paths are
indistinguishable in the ledger only because one of them is misfiled.

### FINDING P2 (MINOR) — `fit_note()` still prints the MoE tolerance the owner ruling retired

    src/pick_model.py:251-253
    if is_moe(model_entry.get("name", "")):
        return (f"needs ~{need:.1f}GB vs {vram_gb:.1f}GB free -- will offload, but it's MoE "
                f"so the cost is modest")

against the constant's own comment sixty lines above:

    src/pick_model.py:79-83
    # Families that are mixture-of-experts: only a small fraction of parameters is active per
    # token ... STILL DISQUALIFYING under the residency mandate below -- the tolerance this
    # marker used to buy is what produced 40-minute single calls.

    src/pick_model.py:85-88
    # OWNER RULING 2026-08-24: GPU-ONLY, AND STICK TO IT. ... "MoE spills cheaply" was true
    # relative to a dense spill and still catastrophic in absolute terms.

The branch is reachable: `fit_note` is called at line 324 for every *scored* model, and it sizes
against `free_vram_gb()` while the residency gate sized against `total_vram_gb() - 1.0`, so a model
that passed the gate can still land in the offload branch. When it does, the operator is told the
cost is modest by the same run that just declared the opposite policy.

### FINDING P3 (MINOR) — fixed `.tmp` beside `config.yaml`

    src/pick_model.py:126-129
    import silence as _sil
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        f.write(new_raw)
    if not _sil.replace_retry(p + ".tmp", p):

The verdict is checked here — that half is right, and the docstring at 105-113 explains why. The
temp name is not: `config.yaml.tmp` is fixed, and the docstring one line above says nine modules
re-read this file. `silence` is already imported at module level (line 31), so the local re-import
at 126 is also redundant.

---

## src/module_index.py

### FINDING M1 (MINOR) — the module that forbids hand-kept counts writes one down twice

    src/module_index.py:11-15
    NO COUNT IS WRITTEN DOWN HERE, deliberately. These two paragraphs used to say "the 87 modules"
    and "eighty-seven headers"; `src/` holds 113 today, and the docstring of the module whose entire
    argument is that hand-kept copies drift had drifted by twenty-six. The count the page reports is
    computed live from `glob.glob` at every run, so the only honest thing to put in prose is that
    there is one.

    src/module_index.py:96
    # on reporting "113 modules -> handoff/MODULE_INDEX.md" and exits 0 while

Both numbers happen to be correct today — `src/` holds exactly 113 `.py` files — but they are the
same species of hand-kept copy the paragraph is arguing against, sitting inside the argument, and
they will drift on the next module added. The paragraph's own conclusion ("the only honest thing
to put in prose is that there is one") is the fix it did not apply to itself.

---

## QUESTIONS — not filed as orders

1. **`liveness.EXEMPT_PREFIXES`** (`liveness.py:63`) exempts `check_`, `phase_` and `drill_` from
   the DEAD pass on the grounds that they are "dispatched by name through a table". `drill.py`'s
   nets are passed as bare `ast.Name` values to `net(...)`, so they are already `used` without the
   exemption. Is the prefix list load-bearing, or is it suppressing a whole naming class for free?
   I could not tell without reading the dispatch tables, which are outside my batch.

2. **`pick_model.KNOWN_WEIGHT_GB`** (lines 66-77) is matched by exact tag equality
   (`if name in KNOWN_WEIGHT_GB`, line 234). The entry `"qwen3:30b-a3b-instruct-2507-q4_K_M"`
   carries a quantisation suffix that the file's own measurement table five lines earlier writes
   without it (`qwen3:30b-a3b-instruct-2507`, line 48). If Ollama reports the shorter tag, that
   entry never matches and the code silently falls back to `size` — which is more accurate anyway.
   Is the table wanted at all now that `size` is available? Ollama was not reachable to confirm
   which form the API returns, so I did not file it.

3. **`corpus_db.drift()` vs `rebuild()` count the same records differently.** `rebuild()` skips
   entries that are not dicts (`if not isinstance(e, dict): continue`, line 164-165) and skips
   unparseable records; `drift()` counts `len(entries)` flat (line 297). If the corpus ever holds a
   non-dict entry, `--rebuild` would print "closed a gap of N entries" on every run forever, for a
   gap that is structural rather than staleness. I did not find any non-dict entries on disk, so
   this is a hazard rather than a live defect.

4. **Display caps I deliberately did not file.** `weave_index.main()` lines 255 and 259
   (`sorted(spread, reverse=True)[:10]`, `sorted(candidates.items(), ...)[:18]`) and
   `coverage.report()` line 223 (`BEST COVERED ... [:10]`) all truncate ranked lists, but each is a
   summary of shape rather than a list of outstanding work, and the "best covered" list in
   particular is not a work list at all. If Hard Rule 0 is meant to cover every ranked print in the
   tree, these are three more sites; I read them as presentation and left them here.

5. **`_so_load()`'s blanket handler** (`coverage.py:66-74`) treats a *corrupt* cache exactly like a
   missing one — `_ = "silence-exempt: no cache yet is the normal first state"` — so a truncated
   `state/coverage_cache.json` is silently discarded and rebuilt rather than reported. Reasonable
   as a design choice (the cache is disposable), but the exemption text only claims the
   first-run case.

6. **`module_index.main()` leaves its temp file behind** when `replace_retry` fails (lines 91-103):
   `replace_retry` does not unlink `tmp` on failure, and the name carries pid + thread, so a
   machine that repeatedly loses the rename accumulates one `handoff/MODULE_INDEX.md.<pid>.<tid>.tmp`
   per failed run. The failure is reported and the exit code is 1, so nothing is hidden — it is
   only litter, and cleaning up on failure could plausibly be worse (the built page is the only
   copy of that run's work). Left as a question because the right answer is a judgement.
