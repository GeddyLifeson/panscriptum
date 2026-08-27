# Batch 09 — run35

Modules read, completely: read.py (1213), health.py (597), rosetta.py (443), pick_model.py
(355), entity_match.py (296), sweep.py (261), liveness.py (234), resync_roll.py (141),
compress_store.py (77). 3,617 lines total.

## FINDINGS FILED (5)

1. **liveness.py:137-138 (order 5569dc0d2c3e)** — DEAD detector never looks inside a class.
   `scan()` iterates `t.body` (module top-level statements only) and requires each node to be a
   module-level `FunctionDef`/`AsyncFunctionDef`; a `ClassDef` fails that check and is skipped
   entirely, so every method in its body never becomes a DEAD candidate at all — called or not.
   Distinct from the already-open `LIVENESS_DEAD_NEEDS_RECEIVER_AWARENESS` order, which is about
   false negatives among functions the scan already considers; this is functions that never
   enter the scan. `entity_match.py`, `verify_math.py` and ten other modules in the tree define
   classes with methods, none of which this detector can ever flag dead.

2. **liveness.py:200-202 (order 425aa23da643)** — PHANTOM only ever inspects `ast.If` test
   conditions. A guard on an undefined name inside a `while` condition, an `assert`, a ternary
   (`IfExp`), or a comprehension `if`-filter is the identical shape PHANTOM exists to catch (the
   `cleanup.py:77-80` founding example) but is structurally invisible to this pass, which never
   walks any of those four node kinds' test expressions.

3. **entity_match.py:276 (order c421410c2194)** — `embed_available()` has no caller anywhere in
   src/. Confirmed via `liveness.scan()["dead"]` and grep (only the def line and one docstring
   mention). Every sibling public function in this module (`candidates`, `best`,
   `qualifier_compatible`, `similarity`) is exercised by `verify_math` §19r; this one is not.

4. **resync_roll.py:61 (order aa6635963409)** — `silence.note("resync_roll.py:45")` is a stale
   line-number tag; the actual except-block is at line 61, and line 45 now falls inside an
   unrelated prose comment. Same defect class as the already-filed stale-tag orders
   (918da0e4b88b, bd33dbbb362a): a triager grepping `state/failures.json` for
   `silent:resync_roll.py:45` is pointed at the wrong code.

5. **health.py:194-198 (order a1ee7c35cf45)** — `summary()` is the one reader of
   `state/failures.json` in this module with no exception handling at all: bare
   `open()`+`json.load()`, no try/except. Every other reader of this exact file disagrees —
   `health.flush()` in the same module treats a corrupt ledger as preserve-and-report (renames
   to `.corrupt`, prints "ledger unreadable"), and both external readers (`dashboard.py:331-339`,
   `standards.py:797-800`) wrap the read in try/except. `summary()` backs `main()`'s
   `--failures` path, so a torn ledger crashes that command with a bare `JSONDecodeError`
   instead of the message every sibling gives — in the module whose entire thesis is "make
   failures loud... a check that only prints is a check the queue cannot act on."

## RESYNC_ROLL.PY TRAP: ALREADY FIXED, VERIFIED

The documented "an out-of-scope source with records must not be silently promoted back to
catalogued" trap (resync_roll.py:82-103) is correctly guarded in the current source: the
`OUT_OF_SCOPE` status (defined once in `roll.py`, the single authority) is checked and left
alone before any `catalogued`/`uncatalogued` write. Confirmed no other human-set status exists
on the roll (`grep` across catalogue_aurora.py, catalogue_codex.py, catalogue_web.py,
recover_folder_records.py — only `"catalogued"` is ever written by non-owner code). No finding
filed; this is a live trap description in the docstring that is no longer a live bug.

## OTHER MODULES: NO NEW FINDINGS

read.py, health.py (beyond #5), rosetta.py, pick_model.py, sweep.py and compress_store.py are
exceptionally well-hardened and mostly self-documenting about past defects already fixed
(cap_chunks/`--chunks` defaults to uncapped per Hard Rule 0 with an explicit CLI opt-in;
priority()'s thin-entry bucket is ranked, not dropped; every write path checks
`silence.write_json`/`replace_retry`'s verdict; every cache read in read.py distinguishes
FileNotFoundError from corruption). Cross-checked several already-open orders against current
line numbers/content and found them still accurate (7ed8fb99bb4c, a9259945a65b, cb07046fd241,
b635a4818c81, 2b695c192470, 79a7d0f284a5) — none needed refiling.

## COVERAGE RECORDED

`sweep_plan.record('run35', [read.py, health.py, rosetta.py, pick_model.py, entity_match.py,
sweep.py, liveness.py, resync_roll.py, compress_store.py], batch=9)`
