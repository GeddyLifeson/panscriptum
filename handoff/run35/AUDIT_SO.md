# run35 SECOND OPINION batch -- 22 ruff findings, one paragraph each

Before: `src/secondopinion.py` reported 1062 ruff findings (346 already waived in `NOT_FILED`).
After this batch: 1002 findings, 960 waived. The drop in total findings (60) is every site this
batch actually rewrote; the jump in waived count (346 -> 960, +614) is BLE001 (531) + PLW0603
(19) + RUF059 (21) + S110 (21) + S112 (9) + PLW2901 (11) + B008 (2) newly added to `NOT_FILED`
with written reasons, per rule below.

**SIM102** (nested if) -- genuinely mixed. Fixed the 3 sites in editable files
(`completeness.py`, `recover_folder_records.py`, `repass_bands.py`) by merging into one `if`
condition; no behavior change. The other 4 sites are in `workorders.py` (x3) and
`verify_math.py`, both off-limits for this run. Left open.

**RUF010** (missing `!s`/`!r` conversion flag) -- fixed the one editable site (`audit.py:170`)
using ruff's own suggested edit. The other (`standards.py:1705`) is off-limits. Left open.

**RUF023** (`__slots__` not sorted) -- trivial, fixed. Sorted `silence.py`'s
`swallow.__slots__` alphabetically.

**PLW0603** (`global` statement) -- WAIVED. Every one of the 19 sites, across at least 7
independent files, is the same lazy-initialized module-level singleton/cache idiom
(`global _X; if _X is None: _X = build()`), thread-guarded where it matters. This is deliberate
house architecture for a build-once module resource, not accidental global mutable state.

**RUF005** (list/tuple concatenation) -- genuinely mixed. Fixed 12 of 18 sites in editable files
using ruff's suggested unpacking form (`[*a, b]` instead of `a + [b]`), mechanically equivalent.
The other 6 are in `derivation.py`, `drill.py`, `mutate.py`, `verify_math.py` -- off-limits.
Left open.

**SIM117** (nested `with`) -- mixed. Fixed the one editable site (`pipeline.py:403`), merging
into one parenthesized multi-context `with` (this interpreter is 3.13, so the syntax is safe).
The other (`local_agent.py:708`) is off-limits. Left open.

**B008** (call in argument default) -- WAIVED, and the interesting one. Both sites looked at
first like the "genuine bug" class the task brief called out, but neither is: `pipeline.py`'s
`_n=len(batch)` is a DELIBERATE closure-safety freeze (removing it would reopen the exact B023
bug this codebase has already shipped once), and `sevenfold.py`'s `depth=len(TIERS)` reads a
fixed module-level tuple that never mutates after import. Fixing this "by the book" would have
made the code worse.

**RUF046** (redundant `int()` around an already-integer value) -- fixed all 4 sites
(`address_space.py`, `assay.py`, `custodes.py`, `reference.py`). `round(x)` with one argument
already returns `int`; the extra wrap was dead weight.

**PLW3301** (nested `max()`) -- fixed the 1 site (`custodes.py:325`), flattened per ruff's
suggestion. Checked that the readings list `vals` is never empty in practice (one Custos per
degree of freedom, all manned), so the theoretical edge-case behavior change does not apply.

**E741** (ambiguous name `l`) -- mixed. Fixed 5 of 8 sites (`chain.py` x3, `rigor.py`,
`scope.py`), renaming to a real word within each variable's actual scope. The other 3
(`verify_math.py`) are off-limits. Left open.

**RUF059** (unpacked variable never used) -- WAIVED, same reasoning as the already-waived B007
one level up. Every sampled site across 8 files is a tuple-unpacking assignment where the
discarded name is kept readable rather than replaced with `_`; none looked like a forgotten
variable.

**SIM300** (Yoda condition) -- mixed. Fixed 2 of 6 sites (`assay.py`, `tiers.py`), flipping the
comparison with the operator flipped to match. The other 4 (`drill.py`, `verify_math.py`) are
off-limits. Left open.

**S110** (`try`/`except`/`pass`) -- WAIVED. This is the counterpart-to-`silence.py` rule, and
the outside tool AGREES with the house detector rather than finding a blind spot: every sampled
site is already flagged `silent` by `silence.audit()` (151 of 672 handlers total). Most are the
"silence the silencer" idiom -- the note-taking/health-recording apparatus cannot itself route
through `silence.note()` without becoming circular. Matches the task brief's own prediction for
500+-site rules.

**RUF007** (prefer `itertools.pairwise`) -- fixed all 3 sites (`hostcheck.py`, `sevenfold.py`,
`tiers.py`), converting `zip(x, x[1:])` to `itertools.pairwise(x)`. This also removed those same
3 lines from the B905 order below, since `pairwise` takes no `strict=`.

**B904** (`raise` without `from`) -- fixed all 12 sites. Every site already captured and
reported the original exception in its message text; this only chains the traceback. Real bug
class, cheap fix, done in full.

**S112** (`try`/`except`/`continue`) -- WAIVED, same reasoning and same corroboration
(`silence.audit()`) as S110, one statement lower.

**PLW2901** (loop variable overwritten) -- WAIVED after actually looking hard, as instructed.
Every non-excluded site reassigns the loop variable to its own normalized or copied form
(`block = block.strip()`, `r = dict(r)`) and only the normalized form is read afterward in that
same iteration -- the safe idiom this rule also flags, not the closure-capture bug (that's
B023, checked separately below).

**RUF021** (unparenthesized mixed `and`/`or`) -- fixed the 1 site (`allsweep.py:413`).

**B023** (closure does not bind loop variable) -- mixed, and the other real bug class the task
brief called out. Fixed 2 of 3 sites (`catalogue_web.py:235`, `:270`) by binding the loop
variable as a lambda default argument -- the file already documents having shipped the
unbound version once. The third (`local_agent.py:265`) is off-limits. Left open.

**SIM103** (return negated condition) -- mixed. Fixed the 1 editable site (`pick_model.py:168`).
The other (`drill.py:1877`) is off-limits. Left open.

**B905** (`zip()` without `strict=`) -- the most judgment-heavy rule in the batch. Of 18 sites:
3 were resolved by converting to `itertools.pairwise` (RUF007, above); 8 got `strict=True` after
confirming each pair is genuinely equal-length by construction; 1 (`sevenfold.py:163`) was
LEFT DELIBERATELY -- its `zip(TIERS, c)` is an intentional unequal-length label-truncation
(`SOURCE_TIERS`/`WORLD_TIERS` are a real prefix/suffix split of `TIERS`), and `strict=True`
there would break every call that isn't the unused 5-tier default. The remaining 6 sites are in
`drill.py`/`verify_math.py`, off-limits.

**BLE001** (blind `except Exception`) -- WAIVED, the flagship case. Verified against
`silence.py`'s own `audit()` rather than just asserting agreement: 521 of 672 handlers are
already observed (recorded, logged, or re-raised) by the same convention `silence.py` audits
directly; the other 151 are the tracked "silent" category covered by S110/S112 above.
