# run35, LOCAL batch L2 -- audit notes

Fourteen orders worked. Nine had their real fix in an owned file (`src/foreman.py`,
`src/generate.py`, `src/manifest_builder.py`, `src/retry_synthesis.py`, `src/build_terminal.py`,
`src/module_index.py`, `src/autostart.py`) and were fixed and closed. Four had their real fix in
`src/local_agent.py`, `src/context_budget.py`, `src/compress_store.py`, and `src/allsweep.py`,
none of which are owned by this batch -- each finding was verified against the current source
and left open, unresolved, for whoever owns that file.

**23a7efaeebe0** (`src/retry_synthesis.py`). Confirmed: `do_merge()` incremented one `skipped`
counter for both an already-had-synthesis skip (line ~145, genuinely benign) and a MERGE DENIED
write refusal (line ~163, `PL.write_record` returned False -- the record this run will never
revisit on its own). The summary line then said "skipped N (already had synthesis)" for both.
Split into `skipped` and `denied`; the summary now names both counts and what the denied one
means for the next run.

**4012ceb89eb4** (`src/build_terminal.py`). Confirmed: `const rim=false` at line 291 is declared
once and never reassigned anywhere in the enclosing `.forEach`, so the `rim?4:0` ternary at line
298 always evaluates to 0 -- dead code, exactly as reported. Deleted the variable and the
ternary; the `letter-spacing` attribute is gone from the `<text>` element rather than pinned to
a constant, since nothing in this codebase wanted it fixed at 0 either.

**480757b8acb5** (`src/manifest_builder.py`). Confirmed: the Feats job's `content_hash` at line
374 hashed only `{"entities": slim}` while `ctx` (mode, ceiling_entity, provisional_magnitude,
entities_with_feats, feats_in_source) sat right beside it as `source_context` but outside the
hash -- unlike the chapter job three lines up, which folds `source_context` into its own hash.
A correction to a source's ceiling entity would regenerate every chapter except Feats. Folded
`ctx` into the hash to match the chapter-job pattern.

**54950602a322** (`src/manifest_builder.py`). Confirmed: `main()` wrote
`output/index/manifest.json` -- the file `generate.py --manifest` reads on every run -- with a
bare `open(out_path, "w")` + `json.dump`, a truncate-then-fill, while `silence` was already
imported and used elsewhere in the same module (the `feats` lookup's `silence.note` call).
Replaced with `silence.write_json(out_path, {"jobs": all_jobs}, indent=2)`.

**55be447a356e** (`src/foreman.py`). Confirmed: `clear_learned_caps()` swallowed every sqlite
exception with a bare `except Exception: silence.note(...)` and fell through to
`return bool(n), f"cleared {n} bucket(s)..."` -- so a database that could not even be opened
produced the identical sentence, "cleared 0 bucket(s) pinned at one request per minute," as a
database that opened fine and genuinely had nothing to clear. The connection was also never
explicitly closed on either path. Fixed by tracking which db paths failed to open/query
separately, closing the connection in a `finally`, and returning a visibly different message
(naming the unreadable db(s) and stating the caps' state is unknown) whenever any db could not
be read.

**584fcdd7dfe5** (`src/foreman.py`). Confirmed all five reported stale numeric tags by locating
each call site fresh and checking its enclosing function against the tag: `"foreman.py:497"`
sits inside `run_charter_regression` (not line 497), `"foreman.py:595"` inside `_literals`,
`"foreman.py:824"` inside `owner_queue`, `"foreman.py:942"` inside `round_once`, and
`"foreman.py:967"` inside `main`'s `KeyboardInterrupt` handler. Renamed all five to
content-derived labels (`run_charter_regression-pool_proof`, `_literals`, `scout-blocked-read`,
`round-log-read`, `round-interrupted`), each checked against its function's existing sibling
tags (e.g. `round-log-denied`, `round-raised`, `for-owner-write`) to avoid colliding with a note
already using the plain function name for a different call site in the same function.

**eeafcd2aa091** (`src/foreman.py`). Confirmed: `recatalogue_models()` returned
`r.returncode == 0, (tail[-1] if tail else "provider lists refreshed")` -- so a nonzero exit
from `catalogue_models.py` that happened not to print a "stale model reference" line still
produced the success sentence "provider lists refreshed" paired with `did=False`, the same
substring-vs-verdict shape already fixed at `adopt_hosts`. Added an explicit nonzero-exit branch
that reports the exit code and either the tail line or captured stderr/stdout as detail, so a
failed run cannot be phrased as a completed refresh.

**a79600702b85** (`src/autostart.py`). Confirmed: `start_supervisor()` opens two log file
handles and returns the `Popen` object without ever closing its own copies; called once per
supervisor restart from `watch()`'s infinite loop, so a long-lived watchdog leaks two handles
per restart for its whole life. Wrapped the `Popen` call in `try/finally`, closing both handles
in the parent once `Popen` has taken its own duplicate -- matches the fact that a detached
child's inherited handles are independent of the parent's.

**d04fb20949b1** (`src/generate.py`, THE ORDER SPECIFICALLY CALLED OUT). Confirmed both stated
halves by execution: (1) `load_json(args.manifest, {"jobs": []})` silently returns the default
for a nonexistent path, so a mistyped `--manifest` produces `{"jobs": []}` and a clean-looking
"0 generated, 0 failed" run; (2) `if __name__ == "__main__": main()` never passed `main()`'s
return value to `sys.exit`, so even an existing `return 1` anywhere in `main()` would never
reach the process's actual exit code -- the number a scheduler reads. Fixed both: added an
explicit `os.path.exists` check on the resolved `--manifest` path before `load_json` is called,
printing a `REFUSING:` message and returning 1 when the file is absent; and changed the
`__main__` guard to `sys.exit(main())` so every return path in `main()` (0 on graceful early-
outs, 1 on this new refusal, `None`/0 on normal completion) now actually determines the exit
code. Live-verified the missing-manifest branch is reached with a direct `os.path.exists` probe
against the resolved path (a full subprocess run currently exits earlier at the prose gate,
which is closed by owner ruling and out of this order's scope to touch).

**8d0ec897cb0b** (real fix belongs in `src/local_agent.py`, NOT owned this batch). Confirmed:
`t_propose_patch`'s audit-log `entry` is only created and appended at line ~616, after all six
early-return refusal paths (no-such-file 528, name/path denylist 554, writable-surface allowlist
560, protected-region prefixes 569, blast cap 584, find-count-must-be-1 588). A model that
repeatedly tries and fails to patch a denied file leaves an empty `patches` list in the log with
no record any attempt was made. Left open -- outside this batch's file ownership.

**96ebf36510b8** (real fix belongs in `src/context_budget.py`, NOT owned this batch). Confirmed:
four bare `except Exception:` handlers at lines ~251, 257, 275, 280 (two each in
`feats_block_budget` and `report()`) silently set the read text to `""` on any read failure, and
the module imports nothing from `silence` anywhere, so none of these failures is recorded. An
unreadable `system_style.txt` makes `scaffold_chars` zero and `content_budget_chars` correspondingly
larger -- the truncating direction the module's own header says it exists to refuse. Marked
MINOR by the original sweep because `generate.py`'s `assert_fits` still refuses loudly at send
time; the loss here is only to the instrument, not the evidence. Left open.

**b635a4818c81** (real fix belongs in `src/compress_store.py`, NOT owned this batch). Confirmed:
`store()` calls `silence.replace_retry(tmp, path)` and discards its return value unconditionally,
then reports `{'hash','path','codec','raw_bytes','compressed_bytes'}` as though the write landed
even when `replace_retry` returned `False` (a denied rename on every attempt). `generate.py`
writes that unchecked `path` straight into the catalogue as `compressed_path`, so a reader can
later hit a path that was never actually written. Left open.

**d0ff339b7138** (real fix belongs in `src/allsweep.py`, NOT owned this batch). Confirmed by
reading the docstring and the function bodies directly: the header says "Three tiers... IMPORT,
VERIFY, RECONCILE... Nothing here writes," but `main()` actually runs five tiers (IMPORT, a
LINT tier at line ~381 entirely absent from the docstring, VERIFY, an ESTATE tier at line ~419
also absent, and RECONCILE), and does write `data/ALLSWEEP.json` via `silence.write_json` at the
end. LINT is one of the two tiers gating exit status and isn't mentioned in the docstring at
all. Left open.
