# Batch 03 audit — foreman.py, catalogue_web.py, entity_match.py, anchors.py, recover_folder_records.py, compress_store.py

Every line of every file read in full. Findings grouped by severity, then by file.

---

## HIGH

### 1. `foreman.py:795-808` — `_function_source` cannot disambiguate same-named functions/methods, so the model-patch gate can silently target the wrong function

```python
def _function_source(path, symbol):
    """The source of one top-level function or method, with its line span."""
    import ast as _ast
    with open(path, encoding="utf-8") as f:
        src = f.read()
    tree = _ast.parse(src)
    want = symbol.split("(")[0].split(".")[-1].strip()
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)) and node.name == want:
            lines = src.splitlines(keepends=True)
            start = node.lineno - 1
            end = getattr(node, "end_lineno", node.lineno)
            return "".join(lines[start:end]), start, end
    return None, None, None
```

`symbol.split(".")[-1]` deliberately throws away any class qualifier (`"Foo.bar"` → `"bar"`), and `ast.walk(tree)` then does a whole-tree, breadth-first scan for the FIRST `FunctionDef`/`AsyncFunctionDef` node anywhere in the module with that bare name — not restricted to top level despite the docstring, and with no attempt to match the class the finding actually named. If a module has two methods of the same name in different classes (or a nested helper that shares a name with a module-level function), this returns whichever one `ast.walk` visits first — silently the wrong one whenever `symbol` was `Class.method` and the true target isn't the first same-named node in the tree.

The consequence is not cosmetic: `attempt_patch` (foreman.py:915 onward) takes the returned `(body, start, end)`, sends the WRONG function's body to the model as "the function with this defect," receives a patch written against that wrong context, and then splices it into `lines[start:end]` — the wrong function's line span — with no check anywhere that the returned patch's `def` name matches `want`. `MAX_PATCH_LINES`, `regex_touched`, `_checks_pass` all still run and can all still pass, because none of them re-verify identity against the finding's intended target. This is precisely the class of hole the module's own docstring says the six gates exist to prevent ("a model editing a live codebase unsupervised... the same defect class that produced eighteen silent faults would produce silent patches").

Repair: resolve `symbol` against its declared class (walk only `ClassDef.body` when the symbol is qualified, module top-level `Module.body` otherwise), and refuse (return `None, None, None`) rather than guess when more than one node matches the bare name.

VERIFIED (confirmed by reading the AST logic directly; does not require reproducing a live collision).

### 2. `foreman.py:996-997` — the model-patch write to live source is not atomic, unlike every other shared write in this file

```python
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        lines[start:end] = [new]
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        good, why = _checks_pass(module)
```

Every other shared write in this same file (`POOL_PROOF.json`, `failures.json`/archive, `OVERWATCH.json`, `OLLAMA_RESTARTS.json`, `FOREMAN.json`, `FOR_OWNER.md`) goes through a `.tmp` + `silence.replace_retry` rename, and the file's own comments repeatedly explain why: a truncating write interrupted mid-dump corrupts the file for every other reader. This is the one write in `foreman.py` that skips that discipline — and it is applied to a live `src/*.py` module, not a JSON scratch file. A backup (`shutil.copy2`) is taken first and a revert (`shutil.copy2(backup, path)`) is attempted on failure, but the revert itself is also a plain, non-atomic copy, and neither the write nor the revert is protected against a hard kill (SIGKILL, power loss, disk full) landing between `f.writelines(lines)` completing and the checks/revert running. A module interrupted at that point is left as a syntactically broken `.py` file on disk with nothing that auto-detects and restores it from the timestamped backup on the next run — the backup is just another file in `state/foreman_backups/` unless a human notices.

Given the module's own stated bar ("deliberately higher than a human's"), the patch-application step itself does not meet the atomicity standard the rest of the file enforces.

Repair: write to `path + ".tmp"`, verify with `_checks_pass` against a copy compiled from the tmp content (or accept the current write-then-revert order but do the WRITE atomically via `silence.replace_retry(tmp, path)`), and only then run `_checks_pass`/revert against the atomically-landed file.

VERIFIED.

### 3. `catalogue_web.py:325-326` — the one exception handler in the file that swallows a real failure without recording it

```python
        try:
            record, note = catalogue(name)
        except Exception as e:
            record, note = None, f"error: {type(e).__name__} {str(e)[:60]}"
```

Every other `except Exception` in this file calls `silence.note(...)` (see `catalogue_composite`'s `except Exception: silence.note("catalogue_web.py:79"); continue` and the `--shortfall` handler's `silence.note("catalogue_web.py:266")`). This one — the handler around the actual per-source cataloguing call, i.e. the one most likely to catch a real defect (a wiki API error, a `KeyError` from malformed category data, a network timeout) — does not. The failure is stringified into a console-only "SKIPPED" line and never reaches `health.record`/`state/failures.json`, so it is invisible to `foreman.triage_swallowed()` and to the `unexpected swallowed failures` standard. `silence.py`'s own module docstring names this exact shape — "a bare `except Exception: return None` or an equivalent... 45 such handlers... that number is the real bug" — as the recurring defect this whole project has been fixing. This is the 46th.

A persistent, real bug in `catalogue()` for one source (not a transient wiki hiccup) would silently produce nothing but a scrolling console message every cataloguing run, forever, with no automated system ever flagging it.

Repair: `silence.note("catalogue_web.py:_one")` inside the `except` block, same as the file's other two handlers.

VERIFIED.

### 4. `anchors.py:211-224` — the "monotone floor → ceiling" self-check is structurally guaranteed to fail, regardless of whether the instrument is healthy

```python
    order = ["The Skate Guy", "A Sword", "Yggdrasil", "Goku", "The Seat of the Creator"]
    vals = {}
    for name, a, res, inst, col in rows:
        vals[name] = A.LADDER.index(a["anchor"]) + (res.get("decimal") or 0.0)
    prev = None
    ok = True
    for n in order:
        if prev is not None and vals[n] < vals[prev]:
            ok = False
        prev = n
    print(f"  monotone floor -> ceiling : {ok}")
```

`vals[name]` is dominated by `LADDER.index(anchor)` (`LADDER = ["M0", ..., "M10"]`, `assay.py:105`), since the decimal remainder from `res.get("decimal")` is at most ~1.0. The five anchors' declared bands are: Skate Guy `M0` (anchors.py:73), A Sword `M0` (anchors.py:131), Yggdrasil `M6` (anchors.py:153), Goku `M5` (anchors.py:93), Seat of the Creator `M10` (anchors.py:115). `order` places Yggdrasil (index 6) immediately before Goku (index 5) — so `vals["Goku"] ≈ 5.x` is compared against `vals["Yggdrasil"] ≈ 6.x`, and `5.x < 6.x` sets `ok = False` on every single run, independent of anything the Assay/Instrument/College formulas actually compute. The module's stated purpose is "to find breakage, not to display success" in the instrument — but this particular invariant can never report `True`, so it can never distinguish a healthy instrument from a broken one. It is a permanently-red check that trains the reader to ignore it (the exact failure mode `triage_swallowed`'s own comment in `foreman.py` describes for the ledger: "a permanently red standard for a solved problem is indistinguishable from one for an unsolved problem, and both get ignored at the same speed").

Either `order` has Yggdrasil and Goku transposed (both narratively and by declared anchor band, Goku M5 should sit below Yggdrasil M6 in a floor→ceiling list — i.e. `order` should read `..., "Goku", "Yggdrasil", ...`), or Yggdrasil's declared `anchor="M6"` is itself wrong for where the design intends it to sit relative to Goku. Nothing in the file's comments acknowledges or excuses the mismatch.

Repair: reorder `order` to match ascending `LADDER.index(anchor)` (Skate Guy M0, Sword M0, Goku M5, Yggdrasil M6, Seat M10), or, if Yggdrasil is meant to be pinned below Goku deliberately, lower its declared anchor and say so in the note.

VERIFIED (confirmed against `assay.LADDER`'s actual ordering and each anchor's declared band; the mismatch is arithmetic, not a matter of the underlying scores).

### 5. `recover_folder_records.py:143-144` — bare, non-atomic write to a catalogue record file, bypassing the project's two-writer contract entirely

```python
        path = os.path.join(RECORDS, slug(name) + ".json")
        if not args.dry_run:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2, ensure_ascii=False)
```

`RECORDS` (`data/records/`) is exactly the directory `pipeline.write_record` / `pipeline.write_record_catalogue` exist to guard — both do atomic `.tmp` + `silence.replace_retry` writes, merge against a concurrently-modified disk copy, and return whether the rename actually landed so the caller can avoid marking a denied write as done (`pipeline.py:411-465`, extensively commented on exactly this hazard). `catalogue_web.py`'s own `_one()` uses `pipeline.write_record_catalogue` and gates on its return value for this identical reason. `recover_folder_records.py` instead truncates and writes the record file directly, with no atomicity and no merge — a crash mid-`json.dump` (this script processes potentially dozens of sources in one run) leaves a truncated JSON file that `pipeline.records()`'s own `except Exception: silence.note(...); continue` will silently skip on the next read, permanently losing the recovered entries with no automatic signal beyond a ledger entry nobody is specifically watching for this script.

VERIFIED.

### 6. `recover_folder_records.py:150-151` — bare, non-atomic write to `SWEEP_ROLL.json`, the file `resync_roll.py`'s own docstring names as suffering exactly this clobber hazard from this exact script

```python
    if not args.dry_run and written:
        with open(ROLL, "w", encoding="utf-8") as f:
            json.dump(roll, f, indent=2, ensure_ascii=False)
```

Contrast with `catalogue_web.py`'s `save_roll()` (catalogue_web.py:70-79), which writes the identical file via `.tmp` + `silence.replace_retry` and explains why: "SWEEP_ROLL.json is written from three worker threads here and read elsewhere by `load_roll` and `resync_roll.py`, BOTH of which do an unguarded `json.load`. A truncating write interrupted mid-dump therefore does not degrade anything gracefully — it kills the next run of either script outright." `recover_folder_records.py` writes the same file with a bare `open(ROLL, "w")` and no rename step at all. This is independently corroborated by `resync_roll.py`'s own docstring, which names `recover_folder_records.py` explicitly, alongside `catalogue_web.py`, `catalogue_aurora.py`, and `catalogue_codex.py`, as one of the cataloguers whose non-atomic roll rewrites have already caused one real clobber incident ("the wiki run's final save reset both to 0 while leaving the record files untouched").

Repair: route both writes through the existing atomic helpers (`pipeline.write_record_catalogue` for the record; the same `.tmp` + `silence.replace_retry` pattern `catalogue_web.save_roll()` already uses for the roll) instead of a bare `open(path, "w")`.

VERIFIED.

---

## MEDIUM

### 7. `foreman.py` — `reprove_pool`, `scout_hostless`, and `triage_swallowed` have no timeout and can stall the whole foreman loop

`_run()` (foreman.py:99-101) is a subprocess call with an explicit `timeout` and the module docstring is explicit that "Remedy timeouts are bounded WELL UNDER the loop interval" by design. But `reprove_pool` (foreman.py:135) calls `CB.prove()` in-process with no timeout of any kind, and `scout_hostless` (foreman.py:181) calls `SC.sweep(limit=4)` the same way. If either of those (network-bound, provider-facing calls) hangs rather than raising, nothing in `round_once` or `main`'s outer `try/except` catches a hang — only a raised exception is handled. The `while True` loop's entire resilience story ("a remedy raising is ORDINARY... the next one in the list is tried") depends on remedies eventually returning or raising, which is exactly the property the module's own docstring says every OTHER remedy must have by construction and these two do not.

Confidence: MEDIUM, because whether `cascade_bridge.prove()` / `scout.sweep()` carry their own internal timeouts was not verified (those modules are outside this batch). Flagging the absence of a *foreman-side* guard regardless.

UNVERIFIED as to whether the callees have their own timeout; VERIFIED that `foreman.py` itself provides none for these two remedies.

### 8. `compress_store.py:43-44` — blob write is not atomic, unlike the rest of the codebase's shared-file discipline

```python
    with open(path, "wb") as f:
        f.write(blob)
```

Every other shared write audited in this and the sibling batches in this project goes through `.tmp` + `silence.replace_retry` specifically because a bare `open(path, "w"/"wb")` can leave a truncated file for a concurrent reader or a crash. `compress_store.store()` writes its content-addressed blob directly to the final path. The blast radius is genuinely smaller than a JSON state file: the path is keyed by `content_hash(text)`, so two writers computing the same hash are writing identical bytes (not a lost-update race), and `generate.py`'s only caller (`generate.py:385`) runs a single sequential loop, not a thread pool, so concurrent-writer collisions were not observed in this batch. But a process kill between `f.write(blob)`'s buffered write and the OS flush still leaves a permanently corrupt blob at that hash's path with no self-healing mechanism (`store()` does not check-then-skip an existing file, and nothing re-verifies a written blob's integrity against its own hash before trusting it), and `catalog.py`'s `cmd_read()` (catalog.py:97) will raise uncaught on `compress_store.load()` for that entry with no retry path.

Repair: write to `path + ".tmp"` and `silence.replace_retry(tmp, path)`, matching every other file write in the project.

VERIFIED (code-level); real-world exposure is low given current single-writer usage.

---

## LOW / informational (judgment calls, not violations)

- `foreman.py:1199` — `json.load(open(os.path.join(HERE, "data", "OVERWATCH.json"), encoding="utf-8"))` opens the file without a context manager or explicit close (relies on CPython refcounting). Harmless under CPython but inconsistent with the file's own care elsewhere about explicit resource handling. Cosmetic.
- `foreman.py:1205` — `sorted(open_f, ...)[:3]` caps model-patch *attempts* to 3 per round. **Not a Hard Rule 0 violation**: this bounds how much repair work one round of an ever-repeating loop attempts, not the catalogued universe of findings — every open finding stays open and is retried in a later round. Judgment call: acceptable rate-limiting on an expensive, GPU-bound repair action.
- `foreman.py:1225` — `json.dump(prev[-200:], ...)` trims the operational log to the most recent 200 rounds. Log rotation on an operational history file, not catalogued content. Not a Hard Rule 0 violation.
- `foreman.py:192` — `scout_hostless()` calls `SC.sweep(limit=4)`. Superficially a cap, but this remedy re-runs every foreman round and any hostless source not scouted this round is retried next round rather than permanently dropped — a per-round throttle, not a truncation of the roster. Judgment call: acceptable, though worth the owner's eye if `scout.sweep`'s `limit` semantics turn out to silently drop rather than round-robin (out of this batch's scope to confirm — `scout.py` is not one of the six files).
- `catalogue_web.py:303` (`r['name'][:44]`) and `:221` (`canon.split(' (')[0][:28]`) — both are console-formatting truncations of a printed label in a dry-run/progress report, not truncations of catalogued data. Non-issue.
- `catalogue_web.py:291-292` (`if args.limit: todo = todo[:args.limit]`) — an explicit, opt-in CLI flag (`--limit N`) for bounding one run's workload, in the same family as the project's own `--pilot` convention. Not a silent Hard Rule 0 violation since it requires deliberate operator opt-in and is documented in the module's own usage banner.
- `recover_folder_records.py` — `mapped = source_map.get(name)`; an empty list `[]` from the map is treated identically to "no mapping" (`if not mapped:`) and routed to `skipped_no_map` rather than a distinct "mapped-but-empty" bucket. Minor loss of diagnostic precision, not a data-loss bug (empty mappings are functionally unrecoverable either way).

---

## Per-module summary

- **foreman.py** — 2 HIGH, 1 MEDIUM, 2 LOW.
- **catalogue_web.py** — 1 HIGH, 0 MEDIUM, 2 LOW (both non-issues on inspection). Hard Rule 0 itself is handled correctly and carefully here (`MAX_PER_SOURCE`/`MAX_PER_CATEGORY`/`CATEGORY_SCAN_DEPTH` all neutralized to `None`, with a `SystemExit` trip-wire if `MAX_PER_SOURCE` is ever set again, and ranking is explicitly never followed by truncation in either `catalogue()` or `catalogue_composite()`).
- **entity_match.py** — CLEAN. No caps, no bare shared-file writes (it performs none), no swallowed exceptions, no mutable defaults, no concurrency surface (pure function module). The `qualifier_compatible()` gate and the `limit=None` default in `candidates()` are both exactly what Hard Rule 0 and the module's own stated design require, and the code matches its own docstring's claims throughout. This module was read in full and nothing worth flagging was found.
- **anchors.py** — 1 HIGH. Everything else in the file (the anchor score dictionaries, `vector_score`'s clamping, the per-anchor print block) is internally consistent and correctly wired to `assay.py`/`custodes.py`/`rigor.py`.
- **recover_folder_records.py** — 2 HIGH, 0 MEDIUM, 1 LOW. Its Hard Rule 0 posture is otherwise sound (no caps anywhere on the entries it transcribes; `EXCLUDED_REGISTER_SOURCES` is a correctness exclusion, not a truncation).
- **compress_store.py** — 0 HIGH, 1 MEDIUM. Otherwise clean: `content_hash` is deterministic, the zstd/gzip fallback is handled correctly and reported via `silence.note`, `load()` raises rather than silently returning wrong bytes on a codec mismatch.
