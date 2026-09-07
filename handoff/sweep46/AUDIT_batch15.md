# sweep46 — batch 15

**Modules:** `read.py` `dashboard.py` `derivation.py` `manifest_builder.py` `axis_correlation.py`
`render.py` `context_budget.py` `halo.py`
**Lines:** 5,538. **Read: all of them**, every module end to end, no sampling (Hard Rule 0).
**Read-and-report only — no file under `src/` was edited.** `drill.py`, `mutate.py`, `allsweep.py`
and `publish.py` were not run; no live crawl or model call was made; `axis_correlation.py --write`
was not run. `derivation.py` (pure, offline, no crawl/model call, no writes) was run once to
verify the ledger actually closes — see below.

| module | lines | read |
|---|---|---|
| `read.py` | 1,554 | 1–1554 |
| `dashboard.py` | 1,197 | 1–1197 |
| `derivation.py` | 790 | 1–790 |
| `manifest_builder.py` | 637 | 1–637 |
| `axis_correlation.py` | 443 | 1–443 |
| `render.py` | 402 | 1–402 |
| `context_budget.py` | 296 | 1–296 |
| `halo.py` | 219 | 1–219 |

Every finding below was verified against the **executable** line, not a comment describing what
the line used to be. Two findings filed; several near-misses investigated and found already
fixed by prior orders (noted below so the next sweep does not re-open them).

---

## 1. `axis_correlation.py` × `assay.py` — the context brief's own subject

The brief's context said the module "was changed today (degraded-matrix now stamped and
printed; the ABSENT branch now ledgered)". Both of those claims check out on the executable
code:

- **ABSENT branch ledgered** — `observations()` (`axis_correlation.py:180-188`) now calls
  `silence.note("axis_correlation.py:observations-absent")` and appends to `absent` before the
  `continue`, per order `9861001e9137`. Confirmed on the line, not the comment.
- **Degraded matrix stamped** — `write()` (`axis_correlation.py:268-281`) sets
  `doc["degraded"] = sorted(missing)` whenever `sources_missing` is a known non-empty list, and
  `main()` prints `sources MISSING: ...` unconditionally from `measure()`'s own
  `sources_missing`, regardless of `--write`. Confirmed.

**But the stamp is written and never read back.** `load()` (`:284-292`) accepts any dict
carrying a non-empty `pairs`, degraded or not, and hands it back unchanged. `rho()` and
`widening()` take whatever `load()` gives them with no `degraded` check. `assay._rho_doc()`
caches that same return value, and `assay._rho_source()` reports
`"measured: data/AXIS_CORRELATION.json"` whenever `_rho_doc()` is truthy — with no distinction
between a matrix built from all 8 `SOURCES` and one built from 1 of 8. Verified by grep: `degraded`
appears nowhere in `src/*.py` outside `axis_correlation.py` itself. `write()`'s own docstring
states the whole point of the stamp is so "a reader of a published +/- ... had no way to tell 45
entities read from all eight sources apart from 5 read from one" — and that is exactly the
information that never reaches the string actually printed on a published assay
(`correlation_source`). **This is category 1 from the brief**: a degraded measurement is
indistinguishable, at the point a person reads it, from a complete one. **Filed `0922effae314`,
MAJOR, LOCAL** — a mechanical fix (surface `degraded` through `load()`/`rho_source`), not a
judgment call, so LOCAL rather than RUN/OWNER.

Also verified and NOT a bug: `main()`'s independence-verdict line only fires when
`mean_r > 0.1` (silent for a hypothetical negative mean below `-0.1`). Given every measured pair
is positive (stated in the module's own header and matching the live `data/AXIS_CORRELATION.json`
figures cited in the brief), this is a live asymmetry but not a currently-reachable gap — recorded
as a question, not filed, in case the population ever grows to include a genuinely
anti-correlated Measure pair.

## 2. `derivation.py` — the recursive-walk change, run and verified

Ran `python src/derivation.py` (pure, no network, no model call, no writes) to check the ledger
actually closes rather than trusting the docstring:

```
graph closes — no dangling parents, no rootless derivations, no cycles
...
VERDICT: LEDGER CLOSES
```

`_scan_modules()` (`:563-575`) walks `os.walk(HERE)` (HERE = `src/`), pruning `__pycache__` via
`dirs[:] = [...]`, and does **not** pass `followlinks=True`. On this machine's Python (3.13.9,
which carries the `os.path.islink` junction-detection fix from bpo-37834/Python 3.8+),
`os.walk`'s default `followlinks=False` correctly refuses to descend into a Windows junction as
well as a symlink, so the walk cannot loop even without an explicit guard. Verified no
reparse points currently exist under `src/` (`Get-ChildItem -Attributes ReparsePoint` empty).
**Judged sound** — no finding filed; this is the kind of thing worth re-checking if this project
is ever run on an older Python.

`verify_math.py`'s companion check (`order f308a7cc0ac7`, lines ~9150-9174) independently
reconstructs the same walk with the identical `__pycache__` filter rather than importing
`SCAN_MODULES` and comparing it to itself, and both walks agree today (`derivation.SCAN_MODULES`
== the independently-reconstructed list, `deprecated/catalogue_local` present in both). Confirmed
by reading, not merely re-stated.

## 3. `manifest_builder.py` — Hard Rule 2 and the fuzzy record lookup, both verified live

Hard Rule 2 (no invented shelf addresses) holds on the executable path: `assigned`/`unassigned`
split on `spine_code_for(name) == "UNASSIGNED"` (`:442-445`), `build_pool` only includes
`unassigned` sources under an explicit `--include-unassigned`, and those are always tagged
`UNSORTED.<Category>.PROVISIONAL` (`provisional_spine`, `:245-248`) — never silently promoted to
a real code. `output/index/unassigned_sources.md` is computed from the full populated roll
(`:442`), not from the `--only`/`--pilot`-filtered `build_pool`, so a pilot run still reports the
true outstanding-curatorial-work count rather than a scoped-down one.

`load_record`'s fuzzy filename matcher (`:66-124`, `MIN_INEXACT_LETTERS` floor) was run
read-only against the live roll and records directory (no write):

```
total sources: 215
exact matches: 214
inexact matches: 1  ['Who Framed Roger Rabbit (incl. all content ...)']
misses: 0
```

Matches the comment's own claim exactly (215/215 resolve, 214 exact, the one documented inexact
case). Judged sound; not filed.

`pack_feats` (`:171-242`) was re-checked against Hard Rule 0: an oversized entity is sliced
across whole blocks with a `feat_span` label rather than truncated, and a single deed larger than
the whole budget still gets its own block rather than being dropped. Confirmed on the code.

## 4. `context_budget.py` and `halo.py` — read end to end, no findings

`context_budget.py`'s arithmetic is internally consistent: `content_budget_chars()` converts
remaining tokens back to content chars at the pessimistic `CHARS_PER_TOKEN`, `JOB_OVERHEAD_CHARS`
is subtracted in the same (content-chars) unit it is measured in, and `feats_block_budget()` can
legitimately go negative or zero, which callers (`manifest_builder.py:376-381`) are required to
treat as "cannot fit," not clamp. Cross-checked against `generate.py`'s two call sites
(`call_ollama`/`assert_fits` and the feats branch's `system_for("feats", ...)` narrowing) to
confirm the module is actually being used the way its own docstring assumes — it is: the feats
branch narrows the system prompt with `system_for` before it ever reaches `assert_fits`.
(`generate.py` itself is outside this batch; checked only as a consumer of `context_budget.py`.)

`halo.py`'s `compute()` passes `attestation="Transcribed"` to `assay.assay()` for all three
roster entries — verified this is one of the four charter-recognised grades
(`assay._RAW_SIGMA`: Instrumented/Witnessed/Transcribed/Reconstructed/Disputed), so this module
does not reproduce the unrecognised-attestation-grade defect filed against `assay()` itself in a
prior sweep (order `9a0588111549`, out of this batch). Per-axis provenance tags (`wiki`/`canon`)
are genuinely per-axis, not a blanket stamp. No findings.

## 5. `render.py` — read end to end, no findings

`children_of`'s coordinate-completeness guard (`:222-228`, orders `3270e0172391` /
`3b422bc17939`) requires every prefix-tier key present in `coord` before filtering, so a partial
coordinate raises rather than silently pooling every node's children together — confirmed live on
the code, not the comment describing the two bugs it replaced. The one remaining `[:26]` slice
(`:160`, inside `containment_svg`) is a **display**-only cap on an SVG label with the full name
still returned by `children_of` to any caller that wants it — consistent with this project's
standing distinction between a reversible display truncation and an irreversible data one, and
the code's own comment names that distinction explicitly. Not a Hard Rule 0 violation.

## 6. `dashboard.py` — read end to end; one new finding, several prior findings confirmed fixed

Confirmed **already fixed** (both cases the sweep45 finding `c003673cff01` described):
- `movement()`'s history-file guard now rejects a list of non-dicts AND a dict whose `at` is
  non-numeric (`:452-454`), so a torn/legacy history file heals instead of wedging past its own
  guard.
- The per-metric delta loop (`:535-568`) now coerces a non-numeric stored value to `None` before
  subtracting (`:546-547`), so one bad field in one history sample can no longer raise out of
  `movement()` and black out the whole `/api/state` response (including the safety headline).

Confirmed **already fixed**: `quotas()`'s `worst` now reports `None` (not `1.0`) for a bucket with
no readable window (`:158-166`), and `panelQuota`'s JS renders that as `unknown`, distinct from
`ok` — order `e7ea68901bfe`. `jobs()`'s `lognames` import is now inside its own try
(`:221-230`), fault-isolated from the rest of the function. `safety()`'s `drill_last.json` and
`escalation.log` reads now distinguish `FileNotFoundError` ("legitimate first state" /
"the good state") from any other read failure (`unreadable: True` / `escalation_unreadable: True`)
— also order `e7ea68901bfe`.

**New finding**: inside that same, carefully-fixed `escalation.log` block, the **per-line** JSON
parse (`:713-716`) still swallows a malformed line with a bare `except Exception: continue` and no
`silence.note` — the one place in this exact function that drops the discipline the six lines
around it are explicit about. Worse, `r.get("at")` at `:717` sits **outside** that inner
try/except, so a line that parses as valid JSON but is not a dict raises `AttributeError`
uncaught there, which propagates to the *outer* handler at `:722` and marks the **entire**
24-hour escalation ledger `UNREADABLE` over one malformed row — the exact
one-bad-row-blacks-out-the-whole-panel shape this file's `jobs()`/`_read_row`/`_roll_row` split
was written to prevent (`:208-238`). **Filed `ffdaa9aa7288`, MINOR, LOCAL.**

`standards.py`'s known no-TTL cache issue (order `65bd015ec5d6`, RUN rung, already filed) is
directly exercised by `dashboard.py:738-742` (`state()` calls `ST.check(s)` unguarded on every
poll of this long-lived daemon) but the defect itself lives in `standards.py`, which is outside
this batch — not re-filed, just confirmed the call site matches the existing order's description.

## 7. `read.py` — read end to end, no new findings

The largest file in the batch and the most heavily pre-audited. Every guard checked against the
executable line rather than the surrounding prose: the verbatim/name/action-verb filters in
`read_entity` (`:895-945`), the `cap_chunks`-is-inert contract (`:863-878`, order `4f02ea2d7ecd`),
the chunk-vs-entity cache key including the entity (`_chunk_key`, `:700-728`, the fix for the
shared-index-page cross-contamination bug), the `unanswered -> return out` deferred-not-lost cache
gate (`:958-970`), and the adaptive local/cloud gate's thread-reentrancy guard (`_card_gate`,
`:399-419`) all match their own docstrings on the code as it stands. No unflagged Hard Rule 0
violation, no check-that-cannot-fail, no stale line citation found (the one imprecise citation,
`":872-875 nearby"` at `~:1467`, is explicitly hedged with "nearby" rather than claimed exact).

---

## Orders filed this batch

| id | sev | rung | where | what |
|---|---|---|---|---|
| `0922effae314` | MAJOR | LOCAL | `axis_correlation.py:284-292`, `assay.py:833-856` | a degraded (partial-source) correlation matrix is stamped on disk but the stamp is never read back, so every published assay's `correlation_source` calls a degraded matrix "measured" identically to a complete one |
| `ffdaa9aa7288` | MINOR | LOCAL | `dashboard.py:707-719` | one malformed `escalation.log` line is silently dropped with no note, and (if it parses as non-dict JSON) can black out the whole 24h escalation panel instead of costing one row |
