# Sweep47 batch 10 — audit

Scope: `src/publish.py`, `src/overwatch.py`, `src/wiki_source.py`, `src/liveness.py`,
`src/sevenfold.py`, `src/retry_synthesis.py`, `src/catalogue_aurora.py`, `src/audit.py`.
All 8 modules read in full, every line, current source on disk (overwatch.py re-read fresh
per the brief's note that another lane had edited it today). Total ~5,639 lines per the brief;
no module or line range was skipped.

## Already-open work orders against these modules — status checked against current source

- `publish.py` **ca4f97d6b64d** UNPUSHED_DETAIL_CLIPPED — **still open, not fixed.**
  `_unpushed()` still clips with `str(e)[:80]` (the "no origin/main" detail) and `n[:40]` /
  `local[:40]` (the "not a count" details), unmarked. No change needed to this report; not
  re-filed.
- `publish.py` **3d2d9b87cc10** EXPORT_ROOT_FILE_WITHDRAWN_FROM_COPY_FILES_IS_UNREACHABLE —
  **still open, not fixed.** `COPY_FILES` still does not include `FOR_OWNER.md`; `prune_export`
  is still explicitly scoped away from root files ("the root marker files are ours"). Not
  re-filed.
- `overwatch.py` **464cc4e12fbc** OVERWATCH_DEAD_STATE_RANK_ENTRIES — **still open, not fixed.**
  `_STATE_RANK` at line ~303 still carries `"stale": 1` and `"confirmed": 1`, and grepping every
  assignment to `f["state"]` in this file confirms those two values are still never written.
  Not re-filed.
- `wiki_source.py` **4d78c426afb3** WIKISOURCE_MINPAGES_FLOOR_UNDECLARED — **still open, not
  fixed.** `find_categories()`'s docstring ("Every category on this wiki that holds subjects of
  the given canonical class") is still unqualified about the `min_pages=40` floor it inherits
  through `discover_categories` → `all_categories`. Not re-filed.
- `wiki_source.py` **83bf7498d135** WIKI_SOURCE_CACHE_KEY_OMITS_HARD_STOP — **ALREADY FIXED.**
  Current source (`all_categories`, line ~416): `key = (subdomain, min_pages, hard_stop)` —
  `hard_stop` is now part of the cache key, with a comment explicitly citing this order number
  as the reason. No action taken; reporting per the brief's instruction rather than re-filing.
- `liveness.py` **8950aa8d3f62** NO_DETECTOR_MEASURES_GATE_REACHABILITY — not specific to a line
  in this file; general to the battery. Not evaluated for a fix (out of this module's own scope)
  and not re-filed.
- `liveness.py` **6c479972e838** LIVENESS_DEAD_NEEDS_RECEIVER_AWARENESS — **still open, not
  fixed** (an owner-level ratchet-pairing decision, unchanged). Not re-filed.
- `liveness.py` **2e0ba4b02ec4** LIVENESS_PHANTOM_PASS_SCOPING — **still open, not fixed.** The
  PHANTOM pass's `defined` set (now built around line ~498, drifted from the order's cited
  449-477 by intervening additions — cite by symbol `defined = set(EXEMPT)` inside `scan()`,
  not by line) is still built module-wide, not per-function. Not re-filed.
- `retry_synthesis.py` **1f9a54bede08** SWEEP39_B07_RETRY_EVIDENCE_RATIONALE_CUT — **still open,
  not fixed.** `synthesise()` still does `ev = _ev[:600]` (line ~205) and
  `"rationale": (got.get("rationale") or "").strip()[:900]` (line ~219), unmarked, shape-parity
  with `pipeline.py`'s identical cuts. Not re-filed.
- `retry_synthesis.py` **82adeee9b7ee** LIMIT_ZERO_READ_AS_NO_LIMIT_WORLDSEED_RETRY — **still
  open, not fixed** (this file's half: `if args.smallest:` at line ~317 still reads
  `--smallest 0` as "no smallest given" rather than "pilot zero sources", running the full
  retry). Not re-filed.

## New finding filed

**0224d12400d1** `UNPUSHED_UNBORN_BRANCH_ASSUMED_ON_ANY_GIT_FAILURE` — RUN / MAJOR —
`src/publish.py:_unpushed`

`_unpushed()` exists specifically to catch a commit stranded on the local export branch after a
prior push failed (the module's own history: "the remote fell 122 commits behind while synced N
files kept printing above it"). Its docstring promises "`count` is None only when the question
genuinely cannot be answered." The implementation breaks that promise in one arm:

```python
try:
    local = git("rev-list", "--count", "HEAD")
except RuntimeError:
    return 0, "no commits on this branch yet"
```

`git()` raises `RuntimeError` on *any* non-zero exit from that command — not only the "HEAD is
unborn" case this branch is written for. A corrupted object store, a denied/locked `.git` read,
or any other transient git failure hits this same `except` and is answered with a confident,
specific *zero*, discarding the exception text entirely. Contrast the sibling branch four lines
above it in the same function, for the `origin/main..HEAD` call, which **does** capture and
report `e` (`detail = "no origin/main to compare against (%s)" % str(e)[:80]`) rather than
asserting a cause.

Consequence: `push()` calls `_unpushed()` only when `git status --porcelain` is clean — exactly
the "stranded commit from an earlier cycle" case. If `git rev-list --count HEAD` fails for any
reason other than a genuinely unborn branch, `push()` sees `ahead == 0` (not `None`), skips its
own "could not tell whether ... ahead" warning (which only fires on `None`), and does
`return False` — "nothing to push" — silently, and will keep doing so on every future clean-tree
cycle. That is the identical failure shape to the incident this file's own comments describe as
the worst one it has had.

Filed at RUN rather than LOCAL because the fix touches the load-bearing decision logic in the
module that pushes to the public repo, and deserves a second pair of eyes rather than an
unsupervised mechanical patch, even though the change itself (inspect the exception text; only
return a confident zero for an actually-unborn-branch message) is small.

## Modules read but producing no new finding

- **overwatch.py** (re-read fresh per the brief's note about another lane's edit today): the
  `structure()` reconcile filter's "failed" clause (order 5b79deaaace9) is present and matches
  the closed-order resolution text exactly; its remaining half (which non-failure kinds pass the
  isupper()/keyword filter) is still an explicitly-marked open question in the comment, as the
  closing ruling intended — nothing further to file. No other new defect found on a full re-read.
- **sevenfold.py**: the balance/seam-cutting logic (`seams()`, `_even_cuts`, `shelve`) was
  checked for off-by-ones and edge cases (empty blocks, `k=1`, ties) against its own extensively
  documented history of prior fixes; all trace correctly. The `main()` write path is properly
  gated on `silence.write_json`'s verdict.
- **catalogue_aurora.py**: dedup key, `record_path`/legacy-slug resolution, and the
  compare-and-swap roll update were re-verified against the reasoning in their own comments and
  hold up. No fresh issue.
- **audit.py**: cross-checked the synthesis-level and entry-level invariant checks (`VALID_BANDS`
  membership, `claims_a_band`, the denominator-by-population fix) against `pipeline.py`'s
  `BANDS`/`clean_band`/`valid_scale_note` and found them consistent; the "one honest row" fix
  from order f149e109c174 is intact and the asymmetry between the synthesis-level check (no
  `band is not None` guard, deliberately) and the entry-level check (`band is not None` guard) is
  correct given synthesis always writes a magnitude key when it writes at all.
- **retry_synthesis.py**: beyond the two already-open orders above, `synthesise()`'s parity with
  `pipeline.phase_synthesis` (prompt construction, transport, acceptance gate, `best`-selection
  when every chunk lands on "unassayed") was traced line-by-line against `pipeline.py`'s
  `phase_synthesis` and matches exactly. `do_merge()`'s write-through-`PL.write_record`,
  denial/unmerged accounting, and exit code are all consistent with the documented incident
  history.
- **wiki_source.py**: `resolve_wiki`'s network-failure-as-negative shape in
  `verify_wiki_matches` (a transient API failure returns `(False, 0)`, indistinguishable from a
  genuine non-match) was considered against fault shape #1, but is **not filed**: a failed
  resolution simply leaves the source uncatalogued (`entry_count` stays 0) rather than writing
  any persistent "no wiki" state, so it self-corrects on the next retry pass — unlike the
  `publish.py` finding above, there is no confident value written to disk here.
- **liveness.py**: read end-to-end including the DEAD/DEAD-CLASS/DEAD-MODULE/TAUTOLOGY/PHANTOM
  passes and their scoping machinery (`_self_attrs`, `scoped`, `by_simple`). Checked the
  `scoped[key] = set().union(*[self_attr[k][1] for k in seen])` line against the order 114a34e9a97a
  comment claiming a dead conditional was removed there — confirmed the conditional is in fact
  gone, matching the comment.

## Coverage note

All 5,639 lines across the 8 named modules were read directly (no sampling, no reliance on
grep-only inspection) before filing. Cross-references made into `src/pipeline.py`,
`src/catalogue_web.py`, and `state/workorders.json` / `state/workorders_closed.jsonl` were to
verify specific claims above (existing-order status, cross-module parity) and were not treated
as part of this batch's own scope.
