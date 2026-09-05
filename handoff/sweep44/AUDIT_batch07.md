# Audit batch 07 — run44

Modules read in full, top to bottom: `src/feats.py` (1,900 lines), `src/generate.py` (803),
`src/catalogue_web.py` (640), `src/handbuilt.py` (516), `src/axis_correlation.py` (415),
`src/navtree.py` (335), `src/recover_folder_records.py` (286), `src/audit.py` (231).

**Context for the reader.** All eight modules carry an unusually high density of load-bearing
comments documenting bugs already found and fixed by earlier sweeps (feats.py and generate.py
especially — both read like a changelog embedded in the source). The findings below are new
defects, verified directly against the code as it stands today, not restatements of the history
those comments recount. One already-known item (catalogue_web.py's `main()` missing a `return`,
order 1e45fae97848) is confirmed and its extent noted, not re-filed.

---

## 1. `src/generate.py` — P8 meta-language gate fails open on `ImportError`

**File:** `src/generate.py:656-661`

```python
        try:
            import pipeline as _PL
            _PL.assert_in_universe(text, where=job["address"])
        except ImportError:
            silence.note("generate.py:meta-ban-unavailable")
        except Exception as _meta:
            ...
            fail_count += 1
            failures[job["address"]] = {...}
            save_json(cfg["paths"]["failures"], failures)
            continue
```

This is the block that enforces Charter P8 (no meta-language breaking the in-fiction frame) —
the very check the surrounding comment block (lines 641-655, 662-674) describes at length as
newly wired up after an audit found it had **zero callers anywhere in `src/`** and was "a ban
nothing checks." The comment directly above the `except Exception` arm states the design intent
in capitals: *"Failing closed is preserved and is the point: whatever went wrong, the chapter is
recorded as refused and NOT written. A meta-ban that cannot run is not a meta-ban that passed."*

That guarantee holds for the second `except` arm (`Exception`) — it increments `fail_count`,
writes a `failures` entry, and `continue`s past the write. It does **not** hold for the first arm.
`except ImportError: silence.note(...)` only logs to the ledger and then falls through to the
rest of the loop body: `raw_path = ...` (line 689), `save_raw(...)` (692), `compress_store.store`,
and the `catalog[...]` write, all execute normally on `text` that was never checked for
meta-language leakage. If `pipeline.py` cannot be imported this run (deleted, syntax-broken,
missing a transitive dependency, or simply absent), the chapter is written and catalogued with
no P8 check having run at all — silently, with only a ledger note (no console line, no
`failures.json` entry, no effect on the exit code) marking that the safety was skipped.

This is the exact failure class the module's own comment on lines 641-648 was written to
describe and correct for the *"zero callers"* case — but the fix reintroduces the same shape one
level down, for the *"import fails"* case, in direct contradiction of the "failing closed is
preserved" claim two paragraphs later in the same block.

Confidence: **high** that the code does what is described above (traced directly, no other
handler downstream checks for this). Confidence that it is a **defect rather than deliberate**:
also high — the surrounding comments explicitly claim fail-closed behavior for this exact gate,
and `pipeline` is a large module already relied upon elsewhere in this file (`assert_gate_open`,
`_coverage_rows` via `prose_gate`, which itself may import `pipeline`), so an `ImportError` here
is a real, if infrequent, possible event (partial deploys, a broken edit to `pipeline.py`
mid-session, dependency issues) — not a theoretical one. The fix is straightforward: treat
`ImportError` the same as any other exception in this specific gate (fail closed, file it, don't
write), since `main()`'s outermost import of `pipeline` for other purposes already tolerates its
absence via `ImportError` elsewhere in the file with an explicit `raise SystemExit` (see
`feats.py`'s analogous escalation-import handling, which fails closed correctly and could serve
as the template).

---

## 2. `--limit 0` silently means "no limit" in three CLI entry points (falsy-zero slip)

Three separate `main()`/`roll()` functions guard a slice on `if <limit>:` rather than
`if <limit> is not None:`. `argparse`'s `type=int` with no default-non-None sentinel means
`--limit 0` is a distinct, meaningful value from "not passed" (`None`), but all three sites
treat `0` exactly like `None` — the truncation is skipped entirely, and *all* pending items run,
not zero.

- **`src/generate.py:589-590`**
  ```python
      if args.limit:
          pending = pending[: args.limit]
  ```
  `ap.add_argument("--limit", type=int, default=None, help="only run the first N pending jobs")`
  (line ~500). `--limit 0` (a plausible dry-run-adjacent invocation — "show me it would do
  nothing") instead runs every pending job.

- **`src/catalogue_web.py:545-546`**
  ```python
      if args.limit:
          todo = todo[: args.limit]
  ```
  Same pattern, same default (`ap.add_argument("--limit", type=int, default=None)`, line ~502).

- **`src/feats.py:1622-1623`** (inside `roll()`)
  ```python
      if limit:
          jobs = jobs[:limit]
  ```
  `roll()` is called from `main()` at line 1841 with `limit=a.limit` where
  `ap.add_argument("--limit", type=int)` defaults to `None`. Same slip.

Confidence: **high** that the code reads this way (quoted directly, three sites). Confidence
that it is worth fixing: **medium** — `--limit 0` is an edge case nobody is likely to invoke
by accident, and the consequence ("runs everything instead of nothing") is the opposite of what
Hard Rule 0 warns against (it does not shrink the universe, if anything it does the reverse), so
the severity is low. Flagging because it is the textbook shape of the falsy-zero class this
audit was asked to watch for, and it recurs identically in three independent files, suggesting a
copied pattern rather than three independent judgment calls.

---

## 3. `src/catalogue_web.py` — unmarked mid-value truncation of source names in operator-facing output

Two places in `catalogue_web.py` truncate a source name with a bare Python slice and no marker,
in a report that exists specifically for an operator to read and act on — the identical shape
this same codebase's own comments (feats.py, order `b0e69b869473`; recover_folder_records.py's
"UNCUT" comment) call out and fix elsewhere as a Hard Rule 0 violation. Neither of these two
sites carries a fix or even an acknowledging comment.

- **`src/catalogue_web.py:344`** (inside `catalogue()`'s progress heartbeat, `_beat`)
  ```python
      print(f"      {source_name[:20]:22s} {what:24s} {done}/{total}", flush=True)
  ```
  `source_name` here is the *whole* source's name (the parameter to `catalogue()`, e.g. "Who
  Framed Roger Rabbit (incl. all content from its associated crossover-toon IPs)" — the exact
  roll entry this file's own comment at lines 68-88 discusses at length as a real, measured
  identity collision hazard when truncated to a fixed width). Two sources whose first 20
  characters coincide (plausible for any franchise sharing a prefix, e.g. two "DMs Guild: ..."
  entries, which the feats.py comment at line ~604 names explicitly as "the shape that collides
  first as the roll grows") print identically in every progress line for this run, with the
  Python-standard no-marker cut giving the reader no sign anything was cut.

- **`src/catalogue_web.py:557`** (inside `main()`'s `--dry-run` listing)
  ```python
      print(f"  {r['name'][:44]:46s} -> {str(sub or 'UNRESOLVED')[:24]:26s} {name or ''}")
  ```
  This is the *same 44-character cap, on the same roll-name field*, that `feats.py`'s
  `resolve_hosts()` was corrected for under order `b0e69b869473` — that fix's own comment states
  "Measured against the live `data/SWEEP_ROLL.json` (215 sources), 11 names exceed 44 characters
  and were cut mid-word" and names this exact failure mode ("a truncated NAME is worse than a
  truncated list, because it still looks like an entry the operator can act on"). `--dry-run` is
  precisely the listing an operator reads to decide which sources will and won't resolve to a
  wiki before committing to a real run — the same class of "listing a person acts on" the fixed
  site in feats.py was corrected for. This one was not visited by that fix and still cuts to 44.

Confidence: **high** that both lines are unfixed truncations (quoted directly, confirmed no
marker or note anywhere near either line, confirmed via `grep` that no other `[:44]` or `[:20]`
site in this file carries a corrective comment). Confidence that this rises to the same severity
as the fixed sibling in feats.py: **medium-high** — the mechanism (operator-facing identity
collision on a progress/resolution report) and the field (`source`/roll name) are identical to
the already-fixed case; the only difference is these are diagnostic prints rather than a
persisted file, so the blast radius is "an operator momentarily misreads which source a line is
about" rather than permanent data loss.

(Two smaller truncations of a *canonical category label*, not a source identity — `catalogue_web.py:352`,
`:418`, `:464`, using `canon.split(" (")[0][:16]`/`[:28]` as a progress-line prefix — are lower
risk: they abbreviate a known, small, closed vocabulary of category names ("Persons", "Places",
"Vessels & Things", ...) for column alignment, not an open-ended identity field, so a collision
there would not misattribute one entity's data to another. Noted for completeness, not filed as
a separate defect.)

---

## 4. Known issue confirmed, not wider than described

**`src/catalogue_web.py`, `main()`** (spans lines ~509-635): confirmed there is no `return`
statement anywhere on the success path — the `--dry-run` branch does a bare `return` (line 558,
implicitly `None`), and the parallel-catalogue path at the bottom (`with ThreadPoolExecutor...`
through the final `print(f"Catalogued {tally['done']}/{len(todo)} ...")`) falls off the end of
the function with no `return` at all. `if __name__ == "__main__": main()` (line 640) discards
whatever `main()` returns and never calls `sys.exit()`, so the process always exits 0 regardless
of `tally['failed']`. This matches order `1e45fae97848` exactly and is not wider than filed:
every other exit path in this file (`--shortfall`'s `raise SystemExit(...)` at line ~527) does
correctly signal failure; it is specifically the tallied per-source failure count at the end of
a real catalogue run that never reaches the exit code.

---

## Summary of what was checked and cleared

`src/audit.py`, `src/navtree.py`, `src/axis_correlation.py`, and `src/recover_folder_records.py`
were read in full and are, as far as this pass can verify, correct: each carries the same dense
style of self-documenting prior fixes (compare-and-swap roll writes, gated atomic replaces,
uncapped/ranked-not-truncated listings, fail-closed escalation imports, hash-order tie-breaks
resolved deterministically) and no new defect was found in any of the four beyond what those
modules already document about themselves. `src/handbuilt.py`'s `ROSTER` data block (nine
hand-scored entities) was read in full for structural issues (duplicate keys, malformed tuples,
falsy-zero on a `"score"` field) and none were found; `compute()`/`main()` are short and already
carry fixes for the sentinel-score (`"unestimable"`) and Unicode-console failure modes visible in
their own comments.
