# Sweep #48 — Batch 11 audit

**Modules read (in full, every line):**

| module | lines read |
|---|---|
| src/magnitude.py | 1959 / 1959 |
| src/silence.py | 1122 / 1122 |
| src/completeness.py | 845 / 845 |
| src/manifest_builder.py | 670 / 670 |
| src/canon_backup.py | 504 / 504 |
| src/pantheon.py | 432 / 432 |
| src/roll.py | 318 / 318 |
| src/propagation.py | 254 / 254 |
| src/lognames.py | 52 / 52 |

Priority order followed: (1) lost updates / unsafe shared writes, (2) checks that cannot fail,
(3) fail-open silence, (4) Hard Rule 0 unmarked caps, (5) stale citations. `roll.py` and
`silence.py` (the compare-and-swap helper and the atomic-writer/audit module) got the closest
read, since a defect there is a defect everywhere. I did not find a new lost-update or
check-that-cannot-fire defect in either — both are already extremely hardened, and the one real
door left open in `roll.py` (`exclude()` bypassing `mutate()`) is the already-filed item pinned
by `handoff/run35/checks_L4.py`, not re-reported here.

Also ran `python src/silence.py`'s own `audit()` against these nine files programmatically to
cross-check for uninstrumented silent handlers; the five it found in `silence.py` itself
(`:133`, `:565`, `:607`, `:902`) and one in `magnitude.py` (`:1531`) are all deliberate,
already-documented exemptions (the recorder-must-never-raise design in `note()`/`swallow`, the
OS-drops-the-lock-anyway reasoning in `_unlock`, the absent-vs-unreadable distinction in
`_digest_or_unreadable`'s `FileNotFoundError` arm, and calibrate()'s "no prior checkpoint file"
first-run state) — not filed as findings.

---

## Finding 1 — MINOR — stale citation, magnitude.py:924

`candidates()`'s docstring says:

> "THE `cap` PARAMETER IS GONE (order 7eee204672ce). This was `candidates(ev, cap=None)` ending
> in `sorted(...)[:cap] if cap else sorted(...)`, and neither of its two callers -- :1172 here
> and sweep.py:190 -- ever passed one..."

**Verified against source.** `candidates()` is defined at magnitude.py:916; its only call site in
this file is `cand = candidates(ev)` at **magnitude.py:1207** (inside `assay_entity`), not :1172
(which sits inside `_split_gate`'s citation-resolution loop and has nothing to do with
`candidates`). The other named caller, `sweep.py`, calls `cand = M.candidates(ev)` at
**sweep.py:199**, not :190 (line 190 there is an unrelated comment about `on_corrupt`).

Both numbers in the same sentence have drifted, by 35 and 9 lines respectively — the file has
grown since the comment was written.

**Remedy:** update the citation to `:1207 here and sweep.py:199`.

## Finding 2 — MINOR — stale citation, completeness.py:71

The `SENTINELS` docstring says:

> "The project's own idiom for telling them apart is `str(h).startswith(("pages:", "doc:"))` --
> binding_health.py:1018 and health.py:486-488 both do exactly this..."

**Verified against source.** The actual matching line in `binding_health.py` is
`hosts = sorted({h for h in hosts_map.values() if h and not str(h).startswith(("pages:",
"doc:"))})` at **binding_health.py:1196**, not :1018 (which is a docstring for
`_title_variants`, an unrelated function). The actual matching code in `health.py` is
`if h.startswith("pages:") or h.startswith("doc:"): continue` at **health.py:618**, not
:486-488 (which sits inside `flush()`/ledger-read documentation, unrelated to this check).

**Remedy:** update the citation to `binding_health.py:1196 and health.py:618`.

## Finding 3 — MINOR — stale citation, manifest_builder.py:139

The comment above `FEATS_BLOCK_CHARS` says:

> "the input measurement is at read.py:80 -- 10,000 chars/5 chunks found 41 feats where 36,000
> chars/2 chunks found 19)"

**Verified against source.** The "10,000 chars/5 chunks -> 41 feats" / "36,000 chars/2 chunks ->
19 feats" measurement actually appears at **read.py:101-102**:
```
101: #     10,000 characters   5 chunks  ->  41 feats
102: #     36,000 characters   2 chunks  ->  19 feats
```
Line 80 of `read.py` is unrelated prose about `health.check_context_budget`.

**Remedy:** update the citation to `read.py:101-102`.

## Finding 4 — MINOR — stale self-citation, manifest_builder.py:171

The same block continues (about `FEATS_BLOCK_CHARS`):

> "a tree-wide grep finds three occurrences of the name -- this line and two comments
> (context_budget.py:20 and :366 below)."

**Verified against source.** `context_budget.py:20` does hold a `FEATS_BLOCK_CHARS` mention and
is correct. The self-citation `:366 below` is wrong: the only other occurrence of
`FEATS_BLOCK_CHARS` in `manifest_builder.py` is the comment beginning "DERIVED, NOT DECLARED
(m46)" at **manifest_builder.py:399**, 33 lines from where the comment claims. (The comment's own
subject — grep-verifying occurrence counts rather than freezing them into prose — makes the
irony worth flagging even though the count itself, three, is still correct.)

**Remedy:** update the self-citation to `:399 below`.

## Finding 5 — MINOR — Hard Rule 0 style: unmarked console truncation, magnitude.py:1626

In `calibrate()`, the per-benchmark NO_SCORE row is printed as:

```python
print(f"{name:<20}{_published(band, val):>10}{'--':>12}{'--':>7}"
      f"{'--':>6}{len(r.get('rejections', [])):>5}  {r.get('reason', 'band only')[:40]}")
```

This is a live `[:40]` cut on the failure `reason` string, with no ellipsis or "N more chars"
marker, in the one line of console output an operator watching a `--calibrate` run sees for a
benchmark that failed to score. The comment three lines above this exact code (line ~1619,
"UNCUT, AND IT IS PERSISTED (Hard Rule 0, sweep42-batch08)") establishes that the *persisted*
`row["reason"]` field is deliberately kept whole for exactly this reason — but the console
mirror of the same value is still silently cut. The full reason is not lost (it is in
`CHARTER_REGRESSION.json`), so this is display-only, not a data-loss bug — but it is the same
species of violation this project has fixed at the identical severity level elsewhere (e.g.
`pantheon.py`'s `epoch[:40]`, `completeness.py`'s `str(r["source"])[:33]`).

**Remedy:** either drop the slice (this is the last field on the line, nothing after it needs
aligning — the same reasoning `pantheon.py`'s comment at line 359-361 already gives for its own
identical fix), or wrap it the way `pantheon.py`'s `--full` axis citations do.

## Finding 6 — MINOR — Hard Rule 0 style: unmarked console truncation, silence.py:1048

In `instrument()`, a file that fails to parse is reported as:

```python
note("silence.py:instrument-unparseable:" + label)
print("  !! %s: could not be parsed (%s: %s); left uninstrumented"
      % (label, type(exc).__name__, str(exc)[:120]))
```

`str(exc)[:120]` truncates the `SyntaxError` message with no marker, in the module whose entire
subject is truncated/unobserved failures printing as though nothing were wrong. The class is
recorded in full via `note()` first, so nothing is lost from the ledger — this is a console
display issue only, same shape as Finding 5.

**Remedy:** print the exception message in full, or wrap it — consistent with how this same file
argues elsewhere (`main()`'s silent-handler list, "WRAPPED, NOT CUT. A wrapped list is readable
and a cut one is wrong.").

## Finding 7 — MINOR — inconsistent exit code, magnitude.py main()'s `--batch` branch

```python
if a.batch:
    run_batch(host=a.host, limit=a.limit, workers=a.workers, resume=not a.fresh)
    return 0
```
(magnitude.py:1951-1953)

`run_batch()` returns `tally["scored"]` and prints three other outcomes the same run can end in
— `refused`, `deferred` (a transport failure wearing a result's clothes), and `unlanded`
(a checkpoint write that was denied, meaning that result never reached disk at all). `main()`
discards the return value and unconditionally exits 0, even when every entity in the batch was
deferred (total transport failure) or every checkpoint write was denied. This is the identical
shape the same file's own `--calibrate` branch was rewritten to close two functions up ("the
exit code here must mean the same thing the standard it feeds does," orders f4171126348f /
b68c9523874e), and the same shape `pantheon.py`, `canon_backup.py`, and `manifest_builder.py` in
this same batch all carry the fix for on their own writes.

**Verified this is not currently gated elsewhere:** `grep`ing the tree, `--batch` is not
dispatched by `foreman.py` (only `--calibrate` is, at foreman.py:1089) and no script checks its
exit code today, so this is not silently failing a live standard the way the pre-fix
`--calibrate` was. It is a rough edge for a hand-run operator (or any future automation) reading
`$?` after a long batch, not a currently-active blind spot.

**Remedy:** `return 0 if tally["scored"] or not tally["deferred"] else 1` (or similar — the
precise threshold is a judgment call the same way `--calibrate`'s was), or at minimum
`return 1 if tally["unlanded"] else 0` so a batch whose results never reached disk is
distinguishable on exit code from one that landed.

---

## What I read and found nothing wrong in

- **roll.py** in full: `load()`, `out_of_scope()`, `in_scope()` (deliberate fail-open, correctly
  documented and correctly limited to "which sources are excluded", not the corpus itself),
  `mutate()` (the compare-and-swap: re-reads and re-applies correctly on every refusal; a
  TOCTUO gap between `digest_of()`'s own read and the subsequent `open()`+`json.load()` cannot
  produce a lost update — it can only make `replace_if_unchanged`'s own re-digest-before-swap
  refuse a write that would otherwise have been fine, i.e. it fails toward extra retries, never
  toward a silent overwrite), `update_rows()` (the `seen`-vs-`ch` distinction from order
  60cb4e0e3595 is correctly implemented), `exclude()` (the known, deliberately-unfixed lost-update
  door — not re-reported), `main()`.
- **silence.py** in full, including `swallow`, `_handler_is_observed`, `_suppressed_names` /
  `_suppress_is_declared`, `_src_py_files`, `_handlers`, `audit`, `append_line` and its Windows
  `O_APPEND`-is-not-atomic fix (locking via `msvcrt.locking`/`fcntl.flock`, `O_BINARY` handling),
  `digest_of` / `_digest_or_unreadable` (the None-vs-UNREADABLE distinction is correctly honoured
  by every caller I could find), `replace_if_unchanged` (the compare-and-swap the whole project's
  m42 fix rests on — digest-then-rename with no sleep in between, each attempt re-digesting;
  correct), `replace_retry`, `write_json`, `_discard_tmp`, `note`, and the `instrument`/
  `_ensure_import`/`_handler_tags` rewriter. No check-that-cannot-fire and no new silent swallow
  found beyond the already-documented, deliberately-exempted ones listed above.
- **completeness.py** in full: the three-outcome `land()` (`True` / `False` / `SKIPPED_ONLY`) is
  correctly threaded through `main()`; `_unmeasured()`'s zeroed `probe_failures`/`probes_run`
  fields are consistent with its four call sites; `work()`'s `no_denominator` / genuine-absence /
  shared-host / `cov > 1.0` branching is exhaustive and each branch is reachable; the
  shrink-floor and denied-write guards in `land()` are both independent and both checked.
- **manifest_builder.py** in full: `load_record()`'s fuzzy-match ladder (exact match exempt from
  the length floor, inexact arms floored at `MIN_INEXACT_LETTERS`) is correctly ordered;
  `pack_feats()`'s pagination-not-truncation of an oversized entity is correct and flushes before
  overshooting; the volume-numbering-over-`numbering_pool`-not-`build_pool` fix (order
  372168774ee7) is correctly wired so `--pilot`/`--only` cannot change another source's address;
  `main()`'s final `return 0 if (manifest_landed and report_landed) else 1` correctly carries
  both write verdicts.
- **canon_backup.py** in full: `members(strict=True)` correctly refuses on any missing canonical
  path rather than silently shrinking the set; `snapshot()`'s stamp now carries pid+thread so two
  same-second snapshots cannot collide on the final name; every write in the module (temp zip,
  manifest, restore) is verified-then-atomic and every verdict is checked; `verify()`'s
  no-manifest-is-a-failure and unreadable-is-not-changed fixes are both correctly implemented;
  `prune()`'s half-removed-pair-counts-as-not-removed logic is correct.
- **pantheon.py** in full: the merge-failure and partial-roster paths both correctly propagate
  into `merge_failed` and the process exit code; the write-verdict and merge-verdict are both
  carried into `main()`'s return; the `--full` view's uncapped citation printing is correct.
- **propagation.py** in full: `observed_mark()`'s "unreachable" trailing `return 0` is genuinely
  unreachable (verified: `ascension_years(1) == 0.0` and the loop counts down to rung 1 last, so
  the loop always returns before falling through) and is correctly documented as such rather than
  asserted without checking; both CLI paths (`--from`/`--to` and the default survey) correctly
  return a non-zero exit on a disconnected or missing pair.
- **lognames.py** in full: the `OWNER` dispatch table entries are each specific enough to
  distinguish the job they name from any other invocation of the same script, matching what the
  file's own comment requires of each entry.
