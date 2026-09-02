# sweep41 batch12 audit

Modules (8, 5,019 lines, all read in full):

| module | lines | verdict |
|---|---|---|
| `src/workorders.py` | 1443 | 1 finding filed (CLI observability gap) |
| `src/silence.py` | 969 | 1 finding filed (audit non-recursive) |
| `src/identity.py` | 700 | clean |
| `src/liveness.py` | 577 | 1 finding filed (scanner non-recursive -- highest-severity class this batch) |
| `src/tiers.py` | 458 | clean |
| `src/sweep.py` | 346 | clean |
| `src/coverage.py` | 300 | clean |
| `src/descending_ladder.py` | 226 | clean |

Coverage recorded: `sweep_plan.record('run41', [these 8 modules], batch=12)`.

## Findings filed (3, all MAJOR/MINOR, none BLOCKING)

### 1. `LIVENESS_MODULES_NOT_RECURSIVE` -- order `aeeba9364147` -- MAJOR
`liveness.py:_modules()` enumerates candidate files with `os.listdir(SRC)` -- top level of
`src/` only, not recursive. `src/deprecated/catalogue_local.py` (280 lines, kept on purpose
per its own README as "a record of the failure mode") therefore never enters `trees`, is
invisible to every DEAD / DEAD_CLASS / TAUTOLOGY / PHANTOM check, and can never itself be
flagged DEAD MODULE no matter what references it (or doesn't).

This is the third independent occurrence of the identical "every module in src/" defect
already found and fixed twice in this same tree: `sweep_plan._src_py_files` (order
f42c55355431, run #37) and `drill._src_py_files` (order cf9ee9000be8, run #37) both switched
from a top-level listing to `os.walk`. Neither fix touched `liveness.py`'s own `_modules()`.
Verified directly: `sed -n '101,105p' src/liveness.py` still shows the plain
`os.listdir(SRC)` loop, and `src/deprecated/catalogue_local.py` exists with real content
(an `except Exception as e:` handler among other things).

Filed as the top finding this batch per the brief's own framing: liveness.py is this
project's "check that cannot fail" detector, and a detector blind to a whole subdirectory
reports that subdirectory exactly as it would report a clean one -- the "absence read as
clean" shape the project is built against. Remedy: switch `_modules()` to the same
`os.walk`-based recursive listing already proven in `drill._src_py_files` /
`sweep_plan._src_py_files`, then re-check `drill.LIVENESS_CEILING` against the new count
(may need a considered raise, same as when the dead_module limb landed).

### 2. `SILENCE_AUDIT_NOT_RECURSIVE` -- order `d7620dd893fa` -- MAJOR
Same defect class, one module over: `silence.py`'s own `audit()` (line 245) and
`instrument()` (line 885) both list files via `glob.glob(os.path.join(root, "*.py"))`,
non-recursive. `src/deprecated/catalogue_local.py` is invisible to `python src/silence.py`
and to `--instrument`, so any silent `except: return None` it holds is never counted, never
printed, and never rewritten -- inside the one module whose entire purpose is finding
exactly that shape. Verified: `grep -n "glob.glob" src/silence.py` shows both call sites
unchanged; the deprecated file's one handler (`except Exception as e:` at
`catalogue_local.py:227`) prints on failure and so would not itself register as SILENT if
it were ever scanned -- but the structural gap (this file, or any future file placed under a
src/ subdirectory) is real regardless of what currently sits there. Remedy: same as above,
`os.walk`-based recursive listing matching `drill._src_py_files` / `sweep_plan._src_py_files`.

### 3. `WORKORDERS_RESOLVE_LOST_WRITE_READS_AS_NO_SUCH_ORDER` -- order `c1e1bf0fb769` -- MINOR
`resolve()`'s docstring frames today's `if not landed: ... ; if rec is None: ...` reordering
as fixing the confusion between "the queue write was lost after retries" (order still open,
transient) and "the order genuinely doesn't exist" (permanent) -- but both branches still
`return None`, so a caller checking only the return value (as `main()` in this same file
does) still cannot tell them apart. `main()`'s `--resolve` path prints
`"no such open order: %s"` and exits 1 for BOTH cases, directly contradicting the lost-write
branch's own stderr text ("This is not 'no such order'; it is a close that was lost.")
printed in the same invocation. Filed as a QUESTION with both readings: either this is a
residual gap worth widening the return contract for (or at minimum fixing `main()`'s
message), or it's deliberately left stderr-only because widening `resolve()`'s return shape
would be a breaking change for other callers. Data safety is not at risk (the order stays
open, stderr does report the truth) -- this is a CLI/observability gap, not a corruption
path, hence MINOR rather than MAJOR.

## Notable clean modules

- **`identity.py`** (700 lines): the continuity/timeline-splitting machinery is heavily
  self-documented with real prior fixes (cache staleness, empty-vs-absent inventory,
  epoch-unprobed-vs-unmarked distinction). No new defect found. Checked in particular:
  `_is_continuity`'s three-test boundary arithmetic (n=0,1,2,>=3 all covered, no gap);
  `epoch_of`'s strict/non-strict unprobed handling; `_titles`' `pages_read or pages or []`
  fallback (same idiom used identically in `corpus_db.py` and `coverage.py`, not unique to
  this file, not flagged).
- **`tiers.py`** (458 lines): the containment gate (`split_sources`) added today is real --
  computed AND gated (refuses to write TIERS.json on a violation), not the "computed then
  gated on nothing" shape the brief warned about. Checked the `xenoverse is None -> skip`
  short-circuit in the containment scan; verified it cannot hide a real violation because
  multiverse/metaverse membership at the two thresholds used (102.3, 100.0) always implies
  xenoverse membership at the looser 50.0 threshold for any group of size >= 2. `chart()`'s
  partial-argument footgun (`chart(srcs=...)` without `w`/`shared` would crash on `None.items()`)
  is real but not live -- both call sites (`pipeline.py`, `sevenfold.py`) either call
  `chart()` with no args or use `_graph()` directly; not filed.
- **`sweep.py`** (346 lines): `nested_run()`'s longest-nested-run algorithm is correct
  despite looking suspicious at first read (repeated best-tracking without an early break);
  traced by hand against the STAGE_TESTS ordering and it cannot return an empty chain. The
  negative-drop bug the module's own docstring describes is verifiably fixed (drop can only
  be computed within the verified-nested chain).
- **`coverage.py`** (300 lines): `coverage._p()` has zero callers -- confirmed by grep -- but
  this is a KNOWN, deliberately-kept dead function, cited by name as the founding worked
  example in `liveness.py`'s own docstring and exercised by a `drill.py` net proving
  `liveness.scan()` correctly flags it. Not re-filed.
- **`descending_ladder.py`** (226 lines): `rung_for_length()`'s repeated-overwrite loop looks
  like a bug at a glance (updates `best` on every match with no break) but is correct by
  construction -- `DESCENDING` is strictly decreasing in `length_m`, so the last row satisfying
  `metres <= r[3]` during the forward scan is provably the tightest (smallest-length) rung
  whose threshold still bounds `metres`, i.e. the correct bin. Traced by hand with
  `metres=1e-3` against the table. `transgression_bits()`'s physics-law correction
  (2026-08-20, priced against degeneracy/Schwarzschild rather than uncertainty) reads as
  already fixed and consistent with `NUCLEAR_DENSITY`'s single hoisted definition.

## Decided NOT to file

- **silence.py's `_OBSERVED_RX` matching inside string-literal contents, not only
  identifiers** (e.g. a handler that assigns a string containing the whole word "log" as
  ordinary English, with no actual logging call, could false-classify as OBSERVED). This is
  a residual limitation of the AST-dump-as-text matching approach, not something introduced
  by today's word-boundary fix -- the word-boundary change is a strict improvement over the
  substring version it replaced, and the docstring already measured the change's blast
  radius precisely (exactly one handler's classification moved, in codewatch.py). No
  concrete live instance was found in this batch's modules to point at, so this is
  speculative rather than verified; not filed. Worth a follow-up sweep specifically grepping
  handler bodies for string-literal false-observed cases if the owner wants it chased.
- **`file_order()`'s `now` timestamp being captured once outside the CAS retry loop**
  (so `last_seen` reflects call time, not landing time, across retries). Traced and it's a
  sub-second-to-low-seconds discrepancy with no correctness consequence for anything that
  reads `last_seen`/`ghost_orders`/ `closed_at` (all of which reason in minutes/hours); not a
  finding.
- **`coverage.state_of()` overwriting rather than accumulating `n_pages` across multiple
  READ candidate files** for one entity. Traced: the discarded value is never read by any
  caller (`measure()` discards the third return value entirely; the only other reference,
  `drill.py:1773`, compares state strings, not page counts). No live consequence; not filed.
- Re-filing order 1c99df1f69c1 (the shell-injection/prose-through-Bash incident) -- already
  filed, explicitly out of scope per the brief.

## Method note

Every module was read to its last line via `Read`/`cat -n` (line counts summed to exactly
5,019, matching the assignment). All three filings were made from a standalone Python script
written with `Write` and invoked with the specified miniconda interpreter --
`workorders.file_order(...)` was called directly, never with prose interpolated into a shell
command line.
