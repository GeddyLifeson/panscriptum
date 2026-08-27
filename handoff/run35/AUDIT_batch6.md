# AUDIT — run35, batch 6

One paragraph per order. IDs are exact. FIXED orders were closed via `workorders.py --resolve`;
LEFT-FOR-OWNER orders remain open by design (see METHOD step 3: judgment calls about deliberate
design are not mine to make). Regression checks for every FIXED order are in
`handoff/run35/checks_batch6.py` (24/24 passing as written).

**28c870dd19e0 — FIXED.** Verified: `worldseed.py:315` (`to_fmg_query(worlds[0])[:150]`) and
`burgs.py:220` (`w0 = worlds[0]`) both index an empty list unconditionally, two lines after
`worldseed.py:299` already defends the same empty case with `max(1, len(addrs))`. Guarded the
one crashing line in `worldseed.main` with `if worlds:`, and wrapped `burgs.main`'s whole SAMPLE
block (everything downstream of `w0`) in `if not worlds: ... else: ...`, leaving the `--write`
path — which already tolerates an empty `per_world` dict — untouched.

**eb014351bc46 — FIXED.** Verified: `HAMLET_FLOOR = 40` is the module's own stated floor for
"the smallest thing the record still calls a burg," but `burgs_for()` clamped each settlement's
population with a bare `max(30, ...)`, an unrelated, unnamed literal eight below the real floor.
Under a "thriving" condition (factor 1.15) the rank-size tail computed at exactly 40/1.15 = 34.8
— above the bare 30 floor and therefore uncaught, but below the constant that defines what a
burg is. Changed the literal to `max(HAMLET_FLOOR, ...)`.

**b235c9c7c388 — FIXED.** Verified: `_is_continuity`'s branching test, `n >= 2 and shared >=
max(2, 0.5*n)`, can never fire at `n == 1` no matter what `shared` is, directly contradicting
the module's own worked example — `(Fates)`, one bearer, "obviously a continuity because that
bearer exists in three other branches... Either alone admits it" — and the function's own
docstring ("branching cannot be required — only sufficient"). Added an explicit `n == 1: return
shared >= 1` case matching the docstring's example; the existing `n >= 2` majority test is
untouched.

**602bbb05ffae — FIXED.** Verified by running the module: `incomparability_rate` folded two
different findings into one "incomparable" bucket — a pair with **no shared scored axis**
(nothing to compare) and a pair with **identical values on every shared axis** (compared and
found equal) both make `dominates()` return `False` in both directions for unrelated reasons,
and the function's only test was "neither dominates." That directly contradicts its own
docstring: "An incomparable pair is not an unresolved question; it is a resolved finding that no
ordering exists." Rewrote the loop to classify each pair as `unmeasured` (excluded from the
rate's denominator), `tied` (decided, not incomparable), or genuinely `incomparable`, and
re-verified live against the exact two cases the sweep found plus a genuine mixed-signal case.

**9736a5a73b02 — LEFT FOR OWNER.** Re-verified independently with the module's own `load_graph`/
`shortest`: `Left 4 Dead → Dragon Ball Z` is 1.1258, matching the sweep exactly, and the graph is
fully connected (0 disconnected pairs of 19,306). The true measured diameter, however, is now
**4.9933** (`DMs Guild: Heroes of Hell` ↔ `Xanathar's Guide to Everything`) against **197
shelves / 3,753 edges** — not the 4.0707 / 172 shelves / 1,087 edges the original sweep measured;
`data/SHARED_STAGE_GRAPH.json` has grown since batch 7's evidence was captured, and the
discrepancy has gotten larger, not smaller. `YEARS_PER_UNIT_DISTANCE` is declared under "Axiom
M3... all FICTIONAL and all reversible" in propagation.py's own header — a curatorial anchor, not
a derived quantity — so per this run's instructions this is an owner ruling, not a maintenance
fix. Left open. `checks_batch6.py` includes a live re-measurement (not a pass/fail gate) so the
drift is visible on every future run without hand-deriving it again.

**662b9fc2d7e2 — FIXED.** Verified at `completeness.py`'s `work()`: when a source has no
catalogue record on disk (`rec is None`), `persons` stays `None`, `cov = (persons/best) if
(persons and best) else 0.0` falls to the `else` branch, and none of the existing `why`
conditions (`not sizes`, shared-host, `cov > 1.0`) ever fire — so the row lands with
`"coverage": 0.0, "unreliable": None`, indistinguishable from a source that was measured and
genuinely found empty. Added a `rec is None` branch, checked first, that sets an explicit `why`
("no catalogue record on disk for this source -- coverage is unmeasured, not measured-and-zero")
before the pre-existing checks.

**824ddd2be20b — FIXED.** Verified the branch is mathematically dead, not merely rarely true: by
the point `check_state()` reaches `if P.batch_settled(key, done, batch)`, the loop already
guarantees `key in done` (an earlier `continue` requires it) and `n >= 1` unsettled entries
(another `continue` requires it) — and `batch_settled` is exactly `key in done_keys and
all(entry_settled(e) for e in batch)`, so the second operand is forced `False` every time this
line runs. `lost`/`lost_where` could never be non-zero; the comment claiming "this now asks a
reachability question" was true of the intent but not of the arithmetic. Also verified
`phase_entrypass`'s own resume gate (`pipeline.py`) shares the identical predicate, so nothing
`entrypass` marks done can go permanently unjudged under the current design — the 0 the dead
branch always reported was the correct answer, just never actually tested for by the code that
claimed to test it. Removed the dead branch and its bookkeeping; rewrote the comment to explain
why the reachability guarantee already lives one level up.

**f308a7cc0ac7 — FIXED.** Verified: `SCAN_MODULES` was a hand-typed list of 22 names against 113
`.py` files in `src/` — 91 modules, including `health.py` and `completeness.py` themselves, were
never scanned for undeclared module-level constants. `scan_constants()` only ever parses a
module's source text with `ast` (never imports it), so there is no side-effect cost to widening
the set. Replaced the literal list with `sorted(f[:-3] for f in os.listdir(HERE) if
f.endswith(".py"))`, measuring the module set off disk on every run. `main()`'s VERDICT line
still comes from `check_graph()` alone, unaffected by this change.

**beb327159a58 — FIXED.** Verified: `tempus.py:43-44` declared `SECONDS_PER_YEAR` and `C_LIGHT`,
and grepping all of `src/` for `tempus.SECONDS_PER_YEAR`, `tempus.C_LIGHT`, and both aliased
import forms (`T.`, `TP.`) found zero readers; the one `C.SECONDS_PER_YEAR` reference in
`verify_math.py` resolves to `cosmography` (imported `as C`), not `tempus`. Deleted both dead
lines rather than redirecting tempus's non-existent consumers at another module's copy — there
is nothing here to point anywhere.

**ef70feacb430 — FIXED.** Verified: `catalogue_composite()`'s per-category `try/except:
continue` swallows any `ws.category_members` exception silently (only a `silence.note`), and
returns `status: catalogued`, `attestation: Transcribed`, `note: "ok"` as long as *any* category
across *any* sub-wiki produced entries — unlike the single-wiki `catalogue()` path, where the
identical call is unguarded and a failure honestly fails the whole attempt (kept retryable via
`entry_count == 0`). Tracked failed `(sub, category)` pairs; when any occurred, the note now
reads `"ok (transport failed for N categories)"` instead of a bare `"ok"`, and the record's own
`provenance` field names which categories were never read. `_one()` now prints that note on
success too, where it was previously computed and discarded.

**6885a5ff23e5 — FIXED, not run.** Verified: `--label` defaulted to the literal `"2026-08-25"`,
and `output/withdrawn_2026-08-25/raw` already holds 148 files while this tool moves rather than
copies — a second `--go` with no `--label` would land in that same archive via the unguarded
`shutil.move` sweep at lines 88-90, with no collision guard. Changed the default to
`datetime.date.today().isoformat()`, computed when the tool runs. The unguarded `shutil.move`
sweep itself and the collision guard were out of scope for this order (fix the default only) and
are not touched. Tool was not run.

**e0c7891274ea — FIXED.** Verified the race is real, not theoretical, and reproduced it directly
against a temp guard file: `beat()`/`release()` do `rec = read(path)` → mutate → `_land(rec,
path)` with no compare-and-swap, so a successor's `claim()` landing in that gap gets silently
overwritten by the predecessor's stale copy of the record (its own name, `done: False`, a fresh
heartbeat) — restoring exactly the ownership m27 was written to prevent, just entered through
the heartbeat/release path instead of the original inline read-modify-write. `_land_claim`'s own
docstring had justified skipping this for `beat()`/`release()` on the grounds that "a heartbeat
that loses a CAS race with itself has nothing useful to do about it" — but the race is with a
different agent, not itself. Fixed both functions to take `silence.digest_of(path)` before
`read()` (matching `claim()`'s own stated ordering and reasoning) and land through the existing
`_land_claim()` CAS instead of plain `_land()`; both now print an explicit refusal and return
`False` if the guard changed underneath them. Corrected `_land_claim`'s docstring. Live repro
(also captured in `checks_batch6.py`) confirms the CAS now refuses the stale write and the
successor's claim survives.

**5d14e90b5043 — LEFT FOR OWNER.** Verified the mechanics precisely: `pipeline` is in `STANDING`
(started early in the cycle at `overnight.py`'s `start("pipeline", ...)`, before `read`, and kept
alive by the keeper thread reasserting `STANDING` every 300s), and the later `run("pipeline",
..., timeout_h=2)` call — the one carrying the comment "Runs after the reader so it sees the
evidence the reader just produced" — checks `running(os.path.basename(args[0]))` first and will
almost always find the standing copy already running, returning `"already-running"` without
doing the ordered work the comment promises; the surrounding comment even explains that
GPU-serial (post-read) pipeline execution is "OBSOLETE" now that pipeline runs continuously. That
argues the second call is leftover from before that transition. However, I also traced a second-
order effect the order's text didn't mention: `statuses` (which this `run()` call feeds) drives
an idle-cycle safety valve (`busy = [x for x in statuses if x == "already-running"]`) that
prevents the supervisor from prematurely counting a cycle as idle while a standing job is
genuinely busy. Simply deleting the dead call would remove one of the (possibly several) sources
feeding that valve, and I could not fully rule out a scenario where it is the only one firing.
Given the explicit instruction not to disturb the standing daemons' behavior without the
coordinator, and that this is exactly the "decide which of the comment or the code is wrong"
shape of judgment call this run is told to leave open, no edit was made to `overnight.py`.

**3d74ba8262a9 — FIXED (docstring).** Verified: the docstring's claim that "the reply is parsed
and VALIDATED here" against the schema is false — `_extract_json` only confirms the text is
*parseable JSON*; grepping `schema` across the whole file shows it used only to build the system
prompt (lines ~1091-1093), never to check a response's shape. `pipeline._pool_answer_usable`
exists specifically to compensate for this gap at the call site and cites `cascade_bridge.py:18`
by name — strong evidence the project's actual, working design already puts real validation one
layer up, per call, where the schema's meaning (which keys are required, what counts as usable)
is actually known. Chose to fix the docstring rather than add validation here: `cascade_bridge`
is a generic multi-provider transport, and baking every caller's schema semantics into it would
be restructuring, which this order explicitly rules out. Rewrote the STRUCTURED OUTPUT section to
describe what `_extract_json` actually does and to name where real validation lives.

## Not resolved (left open, by instruction)

- **9736a5a73b02** (propagation.py) — curatorial/fictional constant; owner ruling needed.
- **5d14e90b5043** (overnight.py) — design decision between two live-daemon code paths, with a
  discovered side effect on idle-cycle detection that raises the stakes of guessing wrong.
