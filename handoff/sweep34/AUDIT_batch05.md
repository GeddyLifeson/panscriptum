# SWEEP 34 — BATCH 05 AUDIT

**Modules read end to end:** `src/foreman.py` (1415), `src/allsweep.py` (500),
`src/catalogue_web.py` (403), `src/ingest_doc.py` (302), `src/ledger_guard.py` (258),
`src/recover_folder_records.py` (212), `src/resonance.py` (160).

Every finding below was checked against the source, and where a number is claimed it was
measured against the data on disk today (2026-08-25). Anything that could not be proved is in
the QUESTIONS section of its module, not in FINDINGS.

The library is HALTED (`state/HALT.json`, DRILL_BREACH). Nothing here was edited; no halt was
lifted or raised.

---

## src/foreman.py

### FINDINGS

**F1 — MAJOR — the model lane's third gate reads only one of allsweep's four tiers, so a
patch that introduces an undefined name is ACCEPTED.** `_checks_pass`, lines 991-1002:

```python
    r = _run([os.path.join(SRC, "allsweep.py"), "--quick"], timeout=900)
    if "BROKEN" in (r.stdout or ""):
        ...
        return False, ("allsweep reports a broken module -- NOTE: no pre-patch baseline is "
                       "taken, so this may pre-date the patch rather than be caused by it")
    return True, "checks pass"
```

The return code is never read. `allsweep.py --quick` runs two graded tiers, IMPORT and LINT.
Only IMPORT prints the token this greps for (`allsweep.py:370`
`print(f"   BROKEN  {r['module']:<26}{r['detail']}")`). LINT prints something else entirely
(`allsweep.py:396` `print(f"   UNDEFINED  {ln[:100]}")`) and is counted into the exit status
(`allsweep.py:486-496`, `bad = len(broken) + ... + len(lint_bad) + ...`, `return 1 if bad
else 0`).

So the one fault class LINT was added for passes this gate. allsweep's own comment for that
tier, lines 374-380, describes the exact scenario: *"`wiki_source.py` used `os.path` in one
function without importing `os`, imported fine, passed this sweep twice, and then failed at
the exact moment the re-catalogue asked it to resolve DC -- with the NameError swallowed by an
except and filed in silence."* The import check at `foreman.py:974` cannot catch it either,
because an undefined name inside a function body does not stop the module importing. This is
the gate that decides whether an unsupervised model rewrite of live source is KEPT.

`if r.returncode != 0` is strictly stronger and needs no new machinery.

**F2 — MINOR — five `silence.note` tags whose line numbers no longer point at their own call
site.** Measured by re-reading the file and comparing each numeric tag to its line:

| call site | tag |
|---|---|
| 724 | `foreman.py:497` |
| 917 | `foreman.py:595` |
| 1189 | `foreman.py:824` |
| 1332 | `foreman.py:942` |
| 1396 | `foreman.py:967` |

Every other note in this file is named (`foreman.py:reprove_pool`, `foreman.py:_retire`,
`foreman.py:remedy-raised`, ...), which is the convention that survives an edit. These five
are the ones that did not get converted, and each now points at unrelated code, so the failure
ledger's class name names the wrong line.

**F3 — MINOR — `clear_learned_caps` reports a swallowed database failure as a clean no-op.**
Lines 119-132:

```python
    n = 0
    for db in (...):
        if not os.path.exists(db):
            continue
        try:
            c = sqlite3.connect(db)
            n += c.execute("update bucket_state set learned=NULL ...").rowcount
            c.commit()
        except Exception:
            silence.note("foreman.py:clear_learned_caps")
    return bool(n), f"cleared {n} bucket(s) pinned at one request per minute"
```

If both connections raise, the function returns `(False, "cleared 0 bucket(s) pinned at one
request per minute")`, which is byte-identical to the healthy "there was nothing to clear"
answer, and that sentence is what `round_once` prints into the operational log
(`foreman.py:1268`). The remedy for `no bucket pinned at rpm 1` therefore cannot be
distinguished from a remedy that could not open its database. (The `sqlite3.Connection` is
also never closed on either path.)

**F4 — MINOR — `recatalogue_models` prints "provider lists refreshed" when the subprocess
failed.** Lines 294-296:

```python
    r = _run([os.path.join(SRC, "catalogue_models.py")], timeout=900)
    tail = [ln for ln in (r.stdout or "").splitlines() if "stale model reference" in ln]
    return r.returncode == 0, (tail[-1] if tail else "provider lists refreshed")
```

A nonzero exit with no matching stdout line returns `(False, "provider lists refreshed")`. The
`did` flag is honest; the sentence beside it is not, and the sentence is the half a human
reads in `data/FOREMAN.json` and in the console. Same shape as the "0 adopted" substring bug
this file already fixed at `adopt_hosts` (lines 172-178).

**F5 — MAJOR — `run_catalogue_gap` hard-codes `--shortfall 100`, and the excluded tail can
never rotate in.** Line 656:

```python
        ON.start("catalogue gap", ["src/catalogue_web.py", "--recatalogue", "--shortfall", "100"],
                 "recatalogue.log")
```

`catalogue_web.main()` uses that N as a hard filter, not a rate (`catalogue_web.py:322`,
`if missing >= args.shortfall`). Measured against `data/COMPLETENESS.json` today: 60 reliable
rows, 55 of them short. 21 are short by >=100 and are dispatched; **34 are short by 1-99 and
are never dispatched by the only automated remedy for the standard `every source is fully
catalogued`** — Fortnite (94), Fist of the North Star (82), Tekken (80), EndWar (68), League
of Legends (67), Alien (66), Predator (66), Naruto (44), all Bloons TD (41), Mad Max (40) and
24 more.

Nothing moves a source across the threshold: the only thing that shrinks a gap is a catalogue
pass, and a sub-100 source never gets one. This is the identical non-rotating window
`scout.sweep`'s docstring describes as the reason its own cap was abolished today
(`scout.py:265-280`: *"The window could not rotate, because the only thing that moved a source
out of it was the very success that was not happening."*). The standard the remedy serves can
never reach its floor by way of the remedy.

### CHECKED AND NOT A FINDING

* `scout_hostless()` still calls `SC.sweep(limit=4)` (line 192). This is **no longer** the
  Hard Rule 0 bug: `scout.sweep` was re-ordered today to last-attempted-first, and its
  docstring (`scout.py:275-280`) explicitly rules that `limit` "survives and still means how
  much work this cycle -- it is a rate ... but it no longer decides which sources exist", with
  deferred sources printed. Not re-filed.
* Every one of the 20 `REMEDIES` keys and the `MODEL_LANE` key matches a live standard name.
  Ran `standards.check(dashboard.state())`: 42 standards, 0 misses.
* `_restartable` and `_restart_horizon` use two different matching rules for the same
  question. Ran both against all six `lognames.OWNER` fragments and `overnight.STANDING`: they
  agree on all six. No drift today.
* `refresh_coverage`'s `return rc == 0, "..." if rc == 0 else "..."` parses as the intended
  tuple; `adopt_hosts`'s `m = _re.match(...) or m` keeps the last matching line, as intended.
* The module docstring's own confession at lines 42-51 (no standalone parse gate; `> MAX` not
  `>= MAX`; "no *new* broken module" is not what the code tests) is accurate to the code.

### QUESTIONS

* `kill_stalled_job` lines 435-437: `if not row or row.get("holds"): return True, "no job is
  stalled now"`. A missing standard row returns the same cheerful sentence as a healthy one.
  In practice the remedy is only reached via a work order carrying that standard's name, so
  the row should always exist — is the `not row` branch meant to be a distinct answer?
* `main()` calls `_ESC.assert_clear` before `ap.parse_args()`, so `foreman.py --help` refuses
  under a halt. `allsweep.check_import` handles that specially (line 130), so it is currently
  harmless. Deliberate ordering, or an accident that happens to be covered?

---

## src/allsweep.py

### FINDINGS

**A1 — MINOR — the module docstring describes a three-tier read-only tool; the module runs
five tiers and writes.** Lines 21-38 announce `IMPORT`, `VERIFY`, `RECONCILE` under the
heading "Three tiers", and close with *"Nothing here writes."* The code runs IMPORT (365),
LINT (381-398), VERIFY (400-417), ESTATE (419-448) and RECONCILE (450-454), and writes
`data/ALLSWEEP.json` at line 466 (`silence.write_json(OUT, {...})`). LINT is one of the two
tiers that gate the exit status, and it is not in the docstring at all — which matters,
because `foreman._checks_pass` was written against the docstring's list (see F1).

**A2 — MINOR — `NEVER_RUN` is read by nothing.** Lines 72-80 define a 30-name set with the
comment *"Modules whose no-argument run does real, expensive or mutating work. They are still
IMPORT checked; they are simply never invoked."* `grep -rn "NEVER_RUN" src/` returns the
definition and nothing else. The tiers invoke exactly two things: `--help` on every module
(`check_import`) and the explicit `VERIFIERS` list. The set is inert, and its comment reads as
a live safety.

**A3 — MINOR — stale tag.** Line 167 is `silence.note("allsweep.py:140")` inside
`run_verifier`'s `TimeoutExpired` handler. Its sibling on the next handler is named
(`allsweep.py:run_verifier`).

### CHECKED AND NOT A FINDING

* Line 388, `if "undefined name" in ln or "local variable" in ln and "referenced before" in
  ln`. `and` binds tighter than `or`, which gives exactly the intended grouping. Not a
  precedence bug.
* `--quick` leaves `verifiers = []` and `est = {}`; the `bad` arithmetic at 486-489 handles
  both without error.

### QUESTIONS

* Line 395, `for ln in lint_bad[:20]`. The ESTATE block six lines above prints a `"... and
  {:,} more (full list in ALLSWEEP.json)"` line when it truncates (433-435); the LINT block
  does not, so 21 undefined names print as 20 with no marker. The full list is persisted and
  the count is printed in the `graded:` line, so nothing is lost — is the missing marker worth
  matching to its neighbour?

---

## src/catalogue_web.py

### FINDINGS

**C1 — MAJOR — a re-catalogue REPLACES every source-level field on the record, and nulls the
pipeline's `synthesis` block. This is the two-writer hazard, and here is the mechanism.**

`catalogue()` returns a record built from scratch (lines 267-281), as does
`catalogue_composite()` (133-148). Both contain:

```python
        "synthesis": None,
```

`_one()` adds exactly one field to it (line 373, `record["category"] = r.get("category")`) and
hands it to the catalogue-side writer (line 385):

```python
            if not _P.write_record_catalogue(os.path.join(RECORDS, slug(name) + ".json"), record):
```

`pipeline.write_record_catalogue` (pipeline.py:413-466) merges **only the entry list**. It
walks `disk["entries"]`, re-appends disk-only entries onto `rec["entries"]`, copies six
per-entry judgment fields onto matching names — and then writes `rec`:

```python
    stamp_record(rec, "pipeline.write_record_catalogue")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2, ensure_ascii=False)
    return _landed(tmp, path)
```

Every top-level key the disk copy had and `rec` does not is dropped, and every key both have
is taken from `rec`. `synthesis` is in `rec` as `None`, so it is not dropped — it is
overwritten with null. Its docstring promises only that *"a merge never shrinks a cast"*, and
that promise is kept; nothing anywhere promises the source-level block survives, and it does
not.

Measured on disk today:

* `data/records/*.json`: 216 records, **186 carry a non-null `synthesis`**. Two also carry
  `purged_roster`, which `rec` has no key for and which would be dropped outright.
* Replaying `main()`'s own selection for the command the foreman dispatches
  (`--recatalogue --shortfall 100`, `foreman.py:656`): 21 sources selected, **14 of them
  already carry a non-null synthesis** — Warhammer Fantasy (ceiling Nagash), Warhammer 40,000
  (The Emperor of Mankind), all Final Fantasy (Bahamut), Mass Effect (Reapers), The Amazing
  World of Gumball (M2, William), Chowder (Hunk), Dune (Leto Atreides II), Halo (Gravemind),
  and six more.

The loss does not heal itself. `pipeline.phase_synthesis` selects
`todo = [... if not (r.get("synthesis") or {}).get("ceiling_entity")]` (pipeline.py:822-823),
which would re-select the source — but the very next lines are:

```python
    done_keys = st["done"].setdefault("synthesis", [])
    for path, rec in todo:
        src = rec["source"]
        if src in done_keys:
            continue
```

so a source whose synthesis phase is already marked done is skipped, and the nulled block
stays nulled. `write_record`'s own docstring (pipeline.py:541-545) states the pipeline's side
of the contract as *"the pipeline only ever changes per-entry judgment fields and the
source-level synthesis block"* — i.e. the source-level synthesis block is precisely the state
the catalogue side is silently discarding.

Note the direction: this is not the thin-over-fat entry revert the two writers were fixed for
in run #24. That one is closed. This is the same collision one field up, on the keys the merge
never looked at.

**C2 — MINOR — the fetch progress heartbeat is labelled with the wrong category.** `_short` is
bound inside the *discovery* loop (line 199, `_short = canon.split(" (")[0][:16]`, inside
`for canon in ws.CATEGORY_KEYWORDS:`). The *fetch* loop at line 232 (`for canon, cats, titles
in planned:`) never rebinds it, and line 244 closes over it:

```python
        texts = ws.page_texts(sub, wanted,
                              progress=lambda d, t: _beat(_short + " fetching", d, t))
```

So every `... fetching d/t` line for every category reports the last canonical class that had
categories, not the one in flight. It is not a crash (`planned` is only non-empty if the first
loop ran and bound `_short`), but this heartbeat exists specifically so a human and
`foreman.kill_stalled_job` can see which unit is progressing on a multi-hour source
(lines 162-181), and it names the wrong one.

**C3 — MINOR — two stale tags.** Line 102 is `silence.note("catalogue_web.py:79")`; line 315
is `silence.note("catalogue_web.py:266")`.

**C4 — MINOR — `CATEGORY_SCAN_DEPTH` is dead, and its comment describes a mechanism that no
longer exists.** Lines 56-58:

```python
# How deep to read a category before ranking. Must be well above MAX_PER_CATEGORY or ranking
# has nothing to choose from and the alphabetical bias returns.
CATEGORY_SCAN_DEPTH = None
```

`grep -rn "CATEGORY_SCAN_DEPTH" src/` finds only this line. `MAX_PER_CATEGORY`, which the
comment sets a relationship against, is itself `None` and is referenced only by a comment
(line 208). Both categories are now pulled with `limit=None` and ranked with `top=None`
(lines 205, 213). `MAX_PER_SOURCE` is different — it is dead as a value but live as a
tripwire (`if MAX_PER_SOURCE is not None: raise SystemExit`, 226-229) — so it should stay.

**C5 — MINOR — `catalogue_composite` swallows a failed category and still returns a
complete-looking record.** Lines 98-103:

```python
            try:
                titles = ws.clean_titles(ws.category_members(sub, c, limit=None))
            except Exception:
                silence.note("catalogue_web.py:79")
                continue
```

Any failure on one sub-wiki category drops that whole category and the pass continues; if at
least one category anywhere succeeded, the function returns `status: "catalogued"`,
`attestation: "Transcribed"` and note `"ok"`, and `_one` writes it and marks the roll
catalogued. The main `catalogue()` path does not do this — `ws.find_categories` and
`ws.category_members` are unguarded there, so a failure propagates and the source is honestly
SKIPPED. The composite path is the one that can publish a silently partial universe.

### CHECKED AND NOT A FINDING

* `--limit` (line 287) defaults to `None` and is set by no internal caller; `todo[:args.limit]`
  at 332 is a human flag, as the brief allows.
* `--shortfall`'s `todo.sort(key=lambda r: -gap[...])` is ranking, not truncation. The cap
  problem is on the foreman's side of that flag — filed as F5.
* Line 385 gates on the write verdict, line 226 refuses to run if the ceiling is ever
  restored: both live and both correct.

---

## src/ingest_doc.py

### FINDINGS

**I1 — MINOR — the owner-supplied corpus is written non-atomically.** `extract()`, lines
96-100:

```python
    d = os.path.join(DOCS, slug(source))
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "pages.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=0, ensure_ascii=False)
```

`register()`, twelve lines below, uses the house idiom for a far cheaper file
(`silence.write_json(HOSTS, hosts, ...)`, line 112) and says why. `pages.json` is the
irreplaceable half of this module's whole premise — it is the only machine copy of a book the
library cannot fetch — it is read by `mine()` (line 153) and by the evidence pipeline through
the `doc:` host, and a truncating re-extract that dies mid-dump destroys it. The resume cursor
beside it (`ingest_state.json`) *is* written atomically, with a comment explaining that a
zero-byte state file reads as "start from chunk 0" (lines 254-259).

**I2 — MINOR — the provenance write discards the landed verdict the module spends thirteen
lines arguing must be gated.** `main()`, lines 290-295:

```python
            if "ingest_doc" not in (rec.get("provenance") or ""):
                rec["provenance"] = (rec.get("provenance") or "") + note
                import pipeline as P
                P.write_record(rp, rec)
        except Exception:
            silence.note("ingest_doc.py:provenance")
```

`write_record` returns False on a denied rename and never raises (pipeline.py:594 ->
`_landed`). Nothing reads it here, and the "extracted %d pages ... host=%s" success line was
already printed ten lines earlier (280-281). The module's own comment at 233-245 makes exactly
this case: *"`write_record_catalogue` returns whether the rename actually landed
(`pipeline._landed`) precisely because on Windows it can be denied while a reader holds the
file, and it never raises -- so discarding the result advanced the resume cursor past entities
that were never saved."* Milder here (the `"ingest_doc" not in provenance` guard means a
re-run retries), but it is the same discard in the same file.

**I3 — MINOR — stale tag.** Line 160 is `silence.note("ingest_doc.py:159")`, one line above
its own call site.

### CHECKED AND NOT A FINDING

* The `"ingest_doc" not in provenance` guard does fire: the note it appends contains the
  literal `src/ingest_doc.py` (line 288).
* `record_path`'s loose containment match (lines 120-126) was run against all 215 roll
  sources. Exactly one resolves to a different filename — `Who Framed Roger Rabbit (incl. all
  content from its associated crossover-toon IPs)` — and that is the case the fallback exists
  for, because `catalogue_web.slug` truncates at 60 characters and this module's does not. No
  wrong-record collision exists today.
* `misses` resets to 0 after a successful chunk (line 205); the 60-miss / ~5h stop is real and
  resumable; `known` is correctly rewound on a denied write (247-251).

### QUESTIONS

* `ingest_doc.slug` (line 77) has no `[:60]`; `catalogue_web.slug` (line 67) and
  `recover_folder_records.slug` (line 59) do. `register()` and `extract()` build the `doc:`
  host and the corpus directory from the untruncated form, so ingest is self-consistent — but
  the record it merges into is named by the truncated one, and `record_path`'s containment
  fallback is the only thing bridging them. Should the three slug functions be one function?
* `mine()` on an empty `pages.json` produces zero chunks, so `ci >= len(chunks)` holds
  immediately and it prints `"ingest complete: 0 new entries merged"` and returns True. Is a
  vacuous pass meant to report complete?

---

## src/ledger_guard.py

### FINDINGS

**L1 — MAJOR — an unreadable hash chain verifies. `read_chain()` turns any failure into "no
chain", and an empty chain has no links to fail.** Lines 168-183:

```python
def read_chain():
    out = []
    try:
        with open(CHAIN, encoding="utf-8") as f:
            ...
    except FileNotFoundError:
        return []
    except Exception:
        return []
    return out
```

`verify_chain()` then loops `for i, rec in enumerate(links)` over an empty list, accumulates
no problems, and returns `(True, [])`. `assert_intact()` — called by `publish.py:508` before
anything is pushed to the public repo — passes on it and returns True.

So a `state/ledger_chain.jsonl` that is permission-denied, held open by another process,
encoding-broken, or a directory, is indistinguishable from a first run with no chain yet, and
the tamper-evidence reports *verified*. This module's own docstring names the standard for
this: *"A check that cannot fail reads exactly like a check that passed."* (line 95, about a
different check in the same file). `FileNotFoundError` genuinely is "no chain yet"; the bare
`except Exception` is not, and nothing distinguishes them. The reason is also discarded — this
module imports `silence` nowhere and files nothing.

**L2 — MINOR — a failed `seal()` is silent, and `assert_intact()` ignores it.** Lines 159-165
and 238:

```python
    try:
        os.makedirs(os.path.dirname(CHAIN), exist_ok=True)
        with open(CHAIN, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        return None
    return rec
```

```python
    seal()
    return True
```

If sealing has been failing since some earlier run, `verify_chain` still passes — the existing
links all verify against each other, there are simply no new ones — and `assert_intact`
returns True every time. The mechanism whose stated purpose is answering *"did anything change
these files between the last run and this one"* (lines 134-138) stops answering, and nothing
anywhere says so. `seal()`'s return value exists and has one caller, which throws it away.

### CHECKED AND NOT A FINDING

* The dual-listing scan `re.findall(r"\[([Mm]\d+)\]", ...)` is not a pattern that matches
  nothing: `BUGS.md` holds 218 bracketed ids in that exact form (`[M21]`, `[M22]`, ...).
* `REQUIRED_SECTIONS` substring tests survive the real headings (`## Watching (not bugs — ...)`,
  `## Resolved (paper trail)`), and the `marks`-sorted span construction at 96-100 is
  order-independent as its comment claims.
* `check_append_only` is not dead — `drill.py:928-934` exercises all three of its branches.

### QUESTIONS

* `MIN_BYTES` floors versus the files on disk today: `HANDOFF.md` floor 20,000 / actual
  418,996; `BUGS.md` 8,000 / 284,942; `NEXT_STEPS.md` 3,000 / 10,708; `MAINTENANCE.md`
  5,000 / 18,478. The comment says the floors exist "to catch a TRUNCATION -- a file that lost
  its history". A `HANDOFF.md` that lost 95% of its history still clears its floor. The
  append-only check and the chain's SHRANK check are the real defences — is the floor meant to
  be anything more than a wiped-file detector, and if so should it be a fraction of the last
  sealed size rather than a constant?
* `verify_chain`'s SHRANK test is gated on `name in APPEND_ONLY` (line 214), i.e. `HANDOFF.md`
  only, while the docstring describes it as *"a ledger got SMALLER between two links"*
  (191-193). `NEXT_STEPS.md` is overwritten wholesale by design, but should `BUGS.md` and
  `MAINTENANCE.md` shrinking be reported?

---

## src/recover_folder_records.py

### FINDINGS

**R1 — MINOR — the rationale in the module docstring disagrees with the data on disk by more
than an order of magnitude.** Lines 7-10:

```
100 of the 215 sources on the Acquisitions Roll show `entry_count: 0` -- a cloud session hit
a limit mid-sweep and those records were never written (77 have no record file at all; 23 have
a file containing an empty `entries` list).
```

Measured today against `data/SWEEP_ROLL.json` and `data/records/`: 215 sources (correct),
**6** with `entry_count: 0` (not 100), **0** with no record file (not 77), **6** with a file
holding an empty `entries` list (not 23). Written in the present tense, so a reader deciding
whether this recovery tool is still worth running is told there are 100 holes when there are
6. This is the module's whole "Why this exists" section.

**R2 — MINOR — the slug comment points at a module that does not exist, and at the wrong
sibling.** Lines 54-56:

```python
# Matches ingest.py's slug(), so recovered files land where the cloud session would have put
# them. load_record() in manifest_builder.py matches on alphanumerics-only containment, so the
# exact punctuation does not matter -- but consistency does, for anyone reading the folder.
```

There is no `src/ingest.py` (`ls src/ingest*.py` -> `src/ingest_doc.py` only; `src/deprecated/`
holds only `catalogue_local.py`). And `ingest_doc.slug` is *not* what this matches — it lacks
the `[:60]` truncation this function has (`ingest_doc.py:76-77` vs
`recover_folder_records.py:57-59`). The function it actually matches, character for character,
is `catalogue_web.slug` (`catalogue_web.py:66-67`), which is the right one to name, since that
is the writer whose filenames these must land beside.

### CHECKED AND NOT A FINDING

* The `already` guard (138-146) treats an unreadable record as populated and skips it, which
  is the recoverable direction, exactly as its comment claims.
* Both writes are gated on `silence.write_json`'s verdict (175, 188) and both failure paths
  leave the roll honestly untouched.
* `EXCLUDED_REGISTER_SOURCES = {"ME"}` is live and consulted at line 106.

### QUESTIONS

* Line 105, `for register_source, _declared_count in mapped:`. `FOLDER_SOURCE_MAP.json`
  carries a count per register source and the code parses it into a discarded name. Comparing
  it to `len(by_source.get(register_source, []))` would catch a map that has drifted from the
  register it points at — is leaving it unchecked deliberate (the map is treated as curatorial
  authority) or just never wired up?

---

## src/resonance.py

Audited on the brief's instruction: the module is unimported anywhere in `src/` and that is
already filed as an open order awaiting a ruling, so it is not re-filed here. What follows is
its internal correctness, which will matter if it is ever wired up.

### FINDINGS

**S1 — MAJOR — `incomparability_rate` counts missing data and exact ties as incomparability,
and its docstring says it does not.** Lines 112-139. `dominates` returns False when there is
no shared scored axis (`if not shared: return False`, 114-116) and when the vectors are equal
(`any(v1[k] > v2[k] ...)` is False, 117). `incomparability_rate` then classifies a pair as
incomparable on exactly the condition "neither dominates" (line 133), so both cases land in
the numerator. Verified by running the module:

```
R.incomparability_rate({'x': {'p': 5}, 'y': {'q': 1}})
    -> {'pairs': 1, 'incomparable': 1, 'rate': 1.0, ...}   # no shared axis at all
R.incomparability_rate({'x': {'p': 5}, 'y': {'p': 5}})
    -> {'pairs': 1, 'incomparable': 1, 'rate': 1.0, ...}   # identical vectors
```

The docstring, lines 123-125, claims the opposite in as many words: *"An incomparable pair is
not an unresolved question; it is a resolved finding that no ordering exists between two
things."* A pair with no shared axis is the unresolved question — it is missing data wearing a
finding's clothes. A tie is comparable in both directions under the capability preorder the
module cites (`A ⪰ B iff C_B ⊆ C_A`, docstring line 15): equal capability sets give `A ⪰ B`
*and* `B ⪰ A`. Both inflate the rate, and the rate is the module's headline number — the
empirical content it offers for "the omniverse is not a ladder".

**S2 — MINOR — `hodge_decompose` divides by zero on empty input, and reports perfect
consistency on no evidence.** Line 89, inside the 600-sweep loop:

```python
        shift = sum(new.values()) / len(new)          # gauge-fix: mean zero
```

With `edges == {}`, `nodes` is empty, `new` stays `{}`, and `len(new)` is 0. Verified:
`R.hodge_decompose({})` -> `ZeroDivisionError: division by zero`. And at line 99,
`eta = (grad_sq / total) if total > 0 else 1.0` — an all-zero flow returns
`{"eta": 1.0, "curl_fraction": 0.0, "ladder_representable": 100.0,
"theorem_2_error_floor": 0.0}`, verified by running it. So "no contest data" and "a perfectly
consistent ladder" produce the identical answer, and `theorem_2_error_floor` — the bound
Theorem 2 puts on every scalar assay's error — reads 0.0 on no evidence.

### CHECKED AND NOT A FINDING

* `resonance_strength`'s expectations match the file on disk: `data/SHARED_STAGE_GRAPH.json`
  exists, has top-level `pairs` / `clusters` / `threshold`, and its 1,087 pair objects carry
  `a`, `b`, `weight` and `shared_sample` exactly as the function reads them. Not a scan that
  matches nothing.
* The Jacobi update at 82-90 is Jacobi (every neighbour term reads the previous sweep's
  `theta`), which is what the docstring now says after run #33 corrected it. The gauge-fix and
  the `theta_a = mean(theta_b + F_ab)` form are right for the least-squares problem stated.
* `examples` is capped at 5 (line 135) but `pairs` and `incomparable` carry the full counts
  alongside — a labelled sample, not a truncated work-list.
