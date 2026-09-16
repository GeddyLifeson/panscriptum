# sweep60 batch 11 — audit

Modules read in full, uncapped: `src/overnight.py` (2006 lines), `src/chain.py` (1243), `src/completeness.py` (905),
`src/secondopinion.py` (708), `src/address.py` (543), `src/axis_correlation.py` (443), `src/catalogue_models.py` (364),
`src/tempus.py` (297). Total 6,509 lines, all read start to finish via the Read tool (no sampling).

## Findings

### 1. MINOR — stale `file.py:NNN` line citation in `chain.py`'s `adjudicate_mutuals` docstring

`src/chain.py:836-838` (inside `side_epoch`'s docstring, itself nested in `adjudicate_mutuals`):

```
EVERY PROVENANCE SENTENCE, NOT THE FIRST (order 0d71cb2b08df). `prov[e].append(src)` runs
once per KEPT OUTCOME in `extract` (:492), so `len(prov[e]) == edges[e]` and this side
can carry several sentences.
```

The citation `(:492)` is stale. The actual statement `prov[e].append(src)` lives at **line 762** of the
current file, inside `extract()`'s `work()` closure:

```python
762:                prov[e].append(src)
```

Verified directly: `grep -n "prov\[e\]\.append" src/chain.py` returns only line 762 as the statement and line 836
as the docstring's mention of it. Line 492 in the current file is nowhere near `extract()` — it falls inside
`harvest()`'s docstring/body region. This is exactly the "citation with a decay rate" failure mode `secondopinion.py`
itself names elsewhere (vulture entry, "a line number in prose is a citation with a decay rate") and that
`foreman_report()`'s own comment in `overnight.py` argues for using content labels over line numbers. Cosmetic
(the surrounding *argument* — every provenance sentence is checked, not just the first — is still correct and
matches the code at line 762), but a reader chasing the citation lands in the wrong function.

### 2. MINOR — stale/wrong call-site citations in `completeness.py`'s `_unmeasured` docstring

`src/completeness.py:468-471`:

```
`probe_failures` AND `probes_run` ARE EMITTED AS ZEROS AND ARE NOT PARAMETERS (order
fc2e8e735f6c). They used to be arguments with 0 defaults, and none of this function's
four call sites -- :473, :477, :489, :560 -- ever passed either, ...
```

Verified against the current file (`grep -n "_unmeasured("`): there are **six** call sites today, at lines
500, 504, 516, 603, 631, 650 — not four, and none of them sit at the cited line numbers (473, 477, 489, 560).
The claim itself ("no call site ever passes `probe_failures`/`probes_run`") is still true of all six sites I
read, so this is not a functional bug — but the citation no longer identifies where to look, and the stated
count (four) undercounts the real call-site population by two. Same species of drift as finding 1, and the
same species of thing `overnight.py`'s own `foreman_report()` comment was rewritten to stop doing ("CONTENT
LABELS, NOT LINE NUMBERS ... pointing at code that has nothing to do with the swallow they name").

## Things I checked and believe are clean

- **Tautologies / checks that cannot fail (priority 1).** Grepped all eight files for `all(...)` over
  possibly-empty collections, the pattern this project's own doctrine flags hardest. Two hits:
  - `overnight.py:433`, `_cmd_is_running`'s `return all(a in rest for a in want_args)` — vacuously `True`
    when `want_args` is empty, but this is explicitly documented and intentional ("Absent from the fragment
    means 'any invocation of this script'"); an empty `want_args` is the fragment-with-no-arguments case,
    not an empty-input edge case masquerading as a pass.
  - `secondopinion.py:427`, `ran_clean()`'s `all(v["status"]=="RAN" and not v["findings"] for v in
    got.values())` — vacuously `True` if `got` were empty, but `got` is only ever built by `run()` from a
    fixed 3-tuple of tools (`ruff`, `vulture`, `detect-secrets`), so it is never empty in practice. Flagged
    here as low-confidence/unsure only because the function has no defensive guard against an empty dict if
    a future caller ever builds `got` some other way — not a live bug today.
  I did not find a genuine "guard on an always-true condition" or "assertion computed from the same code
  under test" in any of the eight modules.
- **Fail-open guards (priority 2).** The codebase is unusually disciplined about fail-closed behavior and
  narrates each fix explicitly (`overnight.py`'s `_manager_stopped`, `running()`'s `None`-for-unknown handling,
  `_in_this_tree`, `completeness.land()`'s shrink floor, `chain.py`'s `_singleton_active`/`_pid_alive` erring
  toward "alive"/"held", `axis_correlation.rho`/`widening`'s loud, non-silent fallback). One place worth
  naming even though it is explicitly reasoned about in the code and not a new finding: `overnight.py`'s
  cycle body gates prose-writing on `drill_rc != 1` (`overnight.py:1799`), and `drill_rc` is `None` whenever
  `safety_drill()` could not run the inspection at all (module missing, timeout, non-{0,1} exit). `None != 1`
  is `True`, so a safety drill that **did not run** does not block prose — only a drill that ran and returned
  BREACHED (`== 1`) does. The code's own docstring for this line defends the choice explicitly ("None or any
  other code means the drill DID NOT RUN ... and is not evidence of a breach"), so this is a deliberate,
  documented design decision rather than an oversight — but it is exactly the shape priority 2 asks about
  (a park inspection that can't run doesn't stop the one job with no interlock of its own), so I'm recording
  it as a documented, intentional fail-open rather than omitting it.
- **Dead code / unreachable functions (priority 3).** Several functions are explicitly marked dead by the
  project's own "mark and keep" doctrine (`address.build_address`, `completeness.category_size`,
  `tempus.concordance_now`) — all correctly self-labeled, not silently rotting. I checked
  `completeness.py`'s `_rec()` helper (defined at line 458) against its own module: it is used once (line 459
  is its own definition; the actual denominator computation at line 658 duplicates the same lookup inline
  rather than calling `_rec()`). This is redundant but not a bug — both expressions are identical logic — so
  I'm not filing it as a finding, just noting the duplication in case a future edit changes one copy and not
  the other.
- **Caps / truncation on anything that should be uncapped (priority 5).** Every persisted artifact in all
  eight files is explicitly uncapped (`chain.py`'s `write_result` unmatched roster, `completeness.py`'s
  `COMPLETENESS.json` rows, `catalogue_models.py`'s `available_sample`/alternatives lists,
  `axis_correlation.py`'s `--top` default `None` = all pairs). Every remaining `[:N]` I found is an
  explicitly-labeled console preview with the full data confirmed to live elsewhere on disk (e.g.
  `chain.py`'s "Strongest 14" preview, `completeness.py`'s `--top` print, `secondopinion.py`'s `hits[:4]`
  site list with a "+N more" marker and "the full list is a `ruff check` away"). None of these are silent.
- **Ordinary bugs (priority 6).** One item worth naming as low-confidence: `overnight.py:518`,
  `_guarded_popen` sets `_PROCS["at"] = 0.0` to invalidate the process-table cache after a successful spawn,
  but does this *without* holding `_PROCS_LOCK` (it only holds `_SPAWN_LOCK` at that point) — every other
  read/write of `_PROCS` in the file (`_proc_lines()`) is under `_PROCS_LOCK`. On CPython a single dict-item
  assignment is atomic under the GIL, so this cannot corrupt the dict, and the worst case is a lost
  cache-invalidation (a concurrent `_proc_lines()` call briefly serves one stale-by-a-beat reading) rather
  than a crash or a wrong duplicate-launch decision — the file is otherwise meticulous about lock discipline
  (see the "CONSTRUCTED AT MODULE LEVEL" comments on both locks), which is why this one unlocked write stood
  out enough to record, labeled unsure/low-severity.

I did not find any comment/docstring that contradicts the code beside it (beyond the two stale line-number
citations above, which are citation drift rather than contradiction of the argument being made), and I did
not find any new ordinary bug (wrong variable, off-by-one, swapped argument, unclosed resource, impossible
exception type) in any of the eight modules.
