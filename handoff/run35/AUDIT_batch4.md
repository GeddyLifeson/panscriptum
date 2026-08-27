# Run35 batch 4 audit (agent scope: src/publish.py, src/ledger_guard.py, src/ledger.py, src/mutate.py, src/overwatch.py, src/secondopinion.py, src/axis_correlation.py)

## a01ab2cf736e -- ledger_guard.read_chain() confused "no chain yet" with "could not be read" -- FIXED

Confirmed exactly: `read_chain()` (ledger_guard.py) had `except FileNotFoundError: return []`
immediately followed by `except Exception: return []`, so a permission-denied, held-open,
encoding-broken, or directory-in-place-of-file chain returned the identical `[]` a genuinely
missing chain does. `verify_chain()` then iterates nothing, accumulates no problems, and
`assert_intact()` -- called by `publish.push()` right before a public push -- reports the chain
"verified". Removed the blanket `except Exception` clause so only `FileNotFoundError` is
swallowed; every other exception now propagates out of `read_chain()`, through `verify_chain()`
and `assert_intact()` (neither of which catches it), aborting `publish.push()` before any git
operation runs. Checked `workorders.py`'s own sweep, which already wraps its ledger-detector
call in `try/except Exception` and explicitly documents that a raise from this area should file
a `DETECTOR_FAILED` order rather than report clean -- so the fix is compatible with, and
completes, an interlock that was already designed to expect it. Verified live: a missing
`CHAIN` path still returns `[]`; a directory created where the chain file should be (standing in
for permission-denied/held-open/encoding-broken) now raises `PermissionError` out of both
`read_chain()` and `verify_chain()` instead of reporting `(True, [])`. `pyflakes` clean, module
imports clean.

## dec2e6bf4b37 -- publish.SKIP_SUFFIX was a denylist that fails open on the ninth suffix -- FIXED

Confirmed: `SKIP_SUFFIX` enumerated two scratch suffixes plus seven specific `.pre*` names, with
its own comment recording that the seven were added only after they had already reached the
public repo once. The tuple has no way to catch an eighth or ninth name nobody has written yet.
Replaced the enumerated `.pre*` names with a shape match: `SKIP_SUFFIX` now holds only the
non-family suffixes (`.pyc`, `.bak`, `.tmp`, `.orig`), and a new `_is_skipped()` helper (used by
`sync_tree()` in place of the old `f.endswith(SKIP_SUFFIX)`) additionally matches any filename
ending in `\.pre[a-z0-9]*$` case-insensitively. Verified: `_is_skipped("mod.py.prezzzznotarealone")`
(a suffix that has never existed in this codebase) is now `True`; `_is_skipped("mod.py")` stays
`False`; the four retained literal suffixes still match. `pyflakes` clean, module imports clean.
This is scoped to the SKIP_SUFFIX/denylist bug specifically -- it is not the deletion question
covered by 456f43361597 below.

## 456f43361597 -- publish.sync_tree() never deletes -- ANALYSED, LEFT FOR OWNER, no deleter written

Confirmed the finding as stated: `sync_tree()` (publish.py) walks `COPY_DIRS`, copies forward
into `SITE`, copies `COPY_FILES`, writes `.is-export-copy`, and returns a count -- there is no
`os.remove`, no `shutil.rmtree`, and no comparison of the destination tree against the source
anywhere in the function. A file deleted from the live project (including one removed *because*
of what it contained) stays in the export copy forever and is re-staged by `git add -A` on every
publish cycle. This is a real and non-trivial exposure -- exactly the kind the docstring's
"never fall back to TEMP" and secret-scan sections elsewhere in this file take very seriously --
but implementing a pruning pass is a design decision with real ways to go wrong, not a mechanical
fix: it has to decide what counts as "no longer live" (only files under `COPY_DIRS`/`COPY_FILES`,
never `.git`, never `.is-export-copy`, never anything a person placed in the export directly),
how to handle a file moved rather than deleted, and what a delete failure (locked file, Norton
interference — the exact class of problem this file's own header discusses at length) should do
to the rest of the sync. Per this run's instruction, that curatorial call is left to the owner;
no deleter was written. Flagging it here in case the owner wants it queued as its own order.

## 6d7f88ffb76e -- mutate.sandbox()'s docstring overclaimed "never opened for writing" -- FIXED (docstring only)

Confirmed by reading `sandbox()` directly: `src/` and `state/` are genuinely COPIED, but `data/`,
`prompts/`, `reference/`, and `output/index` are Windows JUNCTIONS -- portals into the live tree,
not copies -- while the docstring claimed "The live tree is never opened for writing at any
point" and separately (incorrectly) claimed `state/`/`output/` were "created EMPTY", when the
code right below actually copies `state/`'s `.json` files deliberately (with its own comment
explaining why an empty `state/` was tried first and rejected). Rewrote the docstring to state
the real split precisely: `src/`+`state/` are the only two subtrees where a write lands in the
sandbox rather than live; the four junctioned subtrees are read-only *today* because the current
`GATES`/`FAST_GATES` commands do not write to them (verified by reading each gate's write paths,
not assumed), not because the junction mechanism can enforce it; nothing here is a "written
guarantee". Did not add a runtime guard against a future gate writing through a junction --
whether to build one (and at what cost, given junctions exist specifically to avoid copying
gigabytes) is a design call, not a docstring fix, and is exactly the kind of judgment this run
leaves to the owner. Proposed a regression-pinning drill net in `checks_batch4.py` that fails if
the junctioned-subtree set ever grows without this reasoning being revisited. `pyflakes` clean,
module imports clean.

## adba96551729 -- mutate.verify_restore()'s docstring described a job it no longer does -- FIXED (docstring only)

Confirmed: the docstring claimed protection over "the three files this project can least afford
to corrupt," but tracing the only call site (`_run_mutation`, `path = os.path.join(root, "src",
target)`) shows `path` is always the throwaway sandbox copy, never a live file -- that stopped
being true when mutation moved into a sandbox. The live files are protected separately and more
strongly by `live_file_untouched` (digest compare before/after, escalated at OWNER level on a
mismatch). Also confirmed the order's secondary point: `_write`/`_read` are four-line, uncaught
helpers, so a permission error, a locked file, or a full disk RAISES out of `verify_restore`
rather than returning `False` -- deliberate, since `run()`'s own `try/finally` still restores the
original bytes on the way out; not a gap to paper over. Rewrote the docstring to describe the
actual, narrower guarantee (the save/restore round-trip is byte-exact on this one sandbox path,
which is what makes every mutant's later "restored" claim trustworthy) and to say plainly that
the live-file guarantee lives in `live_file_untouched` instead. No behavior change. `pyflakes`
clean, module imports clean.

## a3ee0d1d2d4c -- overwatch stamped an unreviewed module "seen" exactly like a clean one -- FIXED

Confirmed: `_ask()` returns `None` when the GPU is busy and the round's `CLOUD_BUDGET` is spent;
`review()`'s `(got or {}).get("findings", [])` turned that into an empty findings list
indistinguishable from a slice the model actually read and found nothing in; `round_once()` then
unconditionally stamped `led["seen"][m] = {"digest": ..., "at": time.time()}`, so `rotation()`
sorted the never-reviewed module to the BACK of the stale queue as if it had just been read.
Changed `review()` to return `(findings, complete)`, where `complete` goes `False` the moment any
slice's `_ask` call comes back `None`; `round_once()` now only stamps `led["seen"][m]` when
`complete` is `True`, and prints an explicit "NOT MARKED SEEN" note otherwise so the skip is
visible in the run log, not just in the ledger. Verified live: stubbing `_ask` to always return
`None` makes `review()` report `complete=False` with `findings=[]`; the one real caller
(`round_once`) was updated to unpack the new tuple, and no other caller of `review()` exists in
`src/`. `pyflakes` clean, module imports clean.

## 12694407d245 -- secondopinion's three runners never read subprocess returncode -- FIXED

Confirmed by actually running each tool at its known failure mode rather than trusting the audit's
claim: `ruff check --select ZZZ999` and `detect-secrets scan --bogus-flag` both exit 2 with EMPTY
stdout and the real reason on stderr; `vulture` on a nonexistent path exits 1 and prints an
`Error: ... could not be found.` line that happens to LOOK like `path:line:message`, fails
`int(parts[1])`, and is silently dropped by the existing parser. None of `_ruff`, `_vulture`, or
`_detect_secrets` read `r.returncode` anywhere, so all three returned `"RAN", []` for a tool that
never actually answered -- indistinguishable from a genuinely clean run to `ran_clean()`. Added a
returncode check to each: ruff and detect-secrets now report a `"TOOL ERROR (rc=N): ..."` status
(carrying the stderr reason) for any code outside their documented success range (`{0,1}` for
ruff, `0` for detect-secrets); vulture -- which has no clean error/success returncode split on
its own (a bad path returns the same `rc=1` a real finding does) -- reports an error when its
returncode is outside `{0,1}` OR when `rc==1` produced zero parseable findings, which is the
specific shape the "file not found" case takes. Verified live against the real installed tools:
forcing ruff into the bad-selector case and vulture into the missing-path case now both report a
non-"RAN" status, and `ran_clean()`/`missing()` correctly flag `ruff` as unclean/missing instead
of reporting a false pass. `pyflakes` clean, module imports clean.

## 1b29e38dbb17 -- axis_correlation.rho() returns 0.0 on an unreadable matrix -- DISPROVED AS A BUG IN THIS FILE, LEFT FOR OWNER, docstring corrected

Confirmed the code exactly as described: `rho()`'s `if not doc: return 0.0 if default is None
else default` sits directly beneath a docstring declaring 0.0 "the failure mode this module was
written to end." But tracing every actual caller shows this branch is not the load-bearing
guard the order worried about. `assay._rho()` already short-circuits to 0.0 *before* ever calling
`axis_correlation.rho()` when the matrix is unavailable, and does so as an explicit, already-
reasoned owner ruling (`assay.py:612`, "order c00cab9d0412", corrected 2026-08-26): 0.0 there
reproduces the library's pre-correlation numbers exactly rather than inventing an untested third
behavior, and it is never silent -- `RHO_FALLBACK_REASON`, a stderr print, and a
`correlation_source` stamp on every affected published assay all fire. Separately, `drill.py`'s
own `drill_correlation` net (`correlation_actually_widens_the_bar`) calls `axis_correlation.
widening()` directly with no wrapper and would fail BREACHED the moment a missing or corrupt
matrix collapsed the covariance term to zero, regardless of which of the two causes it was. So
the fallback *value* is a settled, defended decision, not this order's bug -- changing it would
re-open c00cab9d0412, which is exactly the kind of design call this run leaves alone. What IS a
real, narrower finding: `axis_correlation.rho()`'s own docstring never mentioned any of this, so
it read as contradicting its own code. Rewrote the docstring to say precisely what "the measured
mean, not zero" governs (an unmeasured PAIR inside an otherwise-present matrix) versus what the
bare `if not doc` branch is (a second, independent implementation of the assay.py-level ruling,
used only by a direct caller like the drill net) and to point at both the owner ruling and the
`drill_correlation` net that actually guards it. Added a regression check to
`checks_batch4.py` proving the two independent implementations (`axis_correlation.rho()` and
`assay._rho()`) still agree on the fallback value, so a future edit to one without the other
would be caught rather than surfacing as two published numbers disagreeing about an identical
matrix-missing situation. No behavior change. `pyflakes` clean, module imports clean.
