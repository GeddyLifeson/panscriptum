# Sweep 40, batch 11 — audit

Modules read in full: `publish.py` (1534 lines), `allsweep.py` (876), `build_terminal.py` (634),
`zfighters.py` (536), `withdraw_chapters.py` (447, NOT run — moves files irreversibly), `navtree.py`
(335), `entity_match.py` (296), `cachekey.py` (190), `catalog.py` (138).

This is a mature, heavily-reviewed codebase. Most of what looked suspicious on first read turned
out to be a documented, deliberate design decision (e.g. `maintenance_shift_live`'s explicit
fail-open, the `art["bad"][:25]` console head with the full list still landed in JSON). Two real
defect classes were found and verified.

---

## FINDING 1 (MAJOR) — `allsweep.py`'s IMPORT tier actually EXECUTES `build_terminal.py`,
## writing `output/registry_terminal.html` on every sweep, contradicting the module's own
## "read-only" contract

**Where:** `src/allsweep.py` lines 96-107 (the `NEVER_RUN` roster and its comment), lines 247-289
(`check_import`), and `src/build_terminal.py` (the whole module — no `argparse`, no `sys.argv`
handling anywhere).

**The claim.** `allsweep.py` lines 96-100:

```
# Modules whose no-argument run does real, expensive or mutating work. They are still IMPORT
# checked; they are simply never invoked -- but the safety here is structural (check_import only
# ever passes `--help`, and run_verifier only ever invokes the explicit VERIFIERS list below), not
# this set. NOTHING READS NEVER_RUN; it is a roster for a human to check against, not a gate.
```

`build_terminal` is named in the `NEVER_RUN` set at line 104. `check_import`'s own docstring
(lines 250-254) repeats the claim: "`--help` is the cheapest total exercise of a module... it
runs every import, every module-level constant, every regex compile, every load-time guard, and
then builds the argument parser — **without doing any work**."

**Why it's wrong.** That safety is only real for a module that has `argparse` and therefore stops
at `--help`. `src/build_terminal.py` has no `import argparse` and never reads `sys.argv` at all —
confirmed by reading the whole file: it imports only `os`, `sys`, `threading`, and its
`if __name__ == "__main__": sys.exit(main())` calls `main()` unconditionally. `main()` (lines
582-630) reads `data/NAVTREE.json` and unconditionally writes `output/registry_terminal.html`
through an atomic tmp-then-rename (`silence.replace_retry`), returning 0 on success.

So when `allsweep.py`'s IMPORT tier runs `python src/build_terminal.py --help` (line 256-258), the
`--help` argument is silently ignored, `main()` runs to completion, and the file is genuinely
rewritten. Because the run exits 0 with no traceback, `check_import`'s grading (`ok = r.returncode
== 0` at line 259) marks it "ok" — the mutation is invisible to the report; nothing flags that a
`NEVER_RUN` module actually ran.

**Confirmed live, not just by static reading:** `output/registry_terminal.html` on disk carries an
mtime of `2026-08-31 23:38` (today), while its source `data/NAVTREE.json` is dated `2026-08-24`
— i.e. the terminal page has been freshly rewritten well after the data it's built from last
changed, consistent with a sweep having re-run `build_terminal.py`'s full `main()` in the
background during this audit window.

**Why this matters.** `allsweep.py`'s own module docstring (lines 49-54) makes an explicit safety
promise other parts of the pipeline rely on:

> "READ-ONLY AGAINST THE LIBRARY, but not writeless... It changes nothing in `data/records` or the
> corpus itself, which is the property 'safe to run at any time, including against live jobs'
> actually depends on -- and the supervisor calls it every cycle."

That property is false for at least this one module. `output/registry_terminal.html` is a real
project artifact (Part Nine of the charter calls the registry terminal a reference deliverable),
and it is being silently rewritten as a side effect of a verification sweep, every cycle, forever
— not "safe to run against live jobs" if something else is mid-write to that same file, and not
actually read-only.

**Remedy (either is sufficient, the two are independent fixes to the same hole):**
1. Give `build_terminal.py` a trivial `argparse` gate (even just `ap.parse_args()` with no
   options) so `--help` genuinely exits before `main()`'s body runs, matching every other
   `NEVER_RUN` module (`feats.py`, `read.py`, `pipeline.py`, `overnight.py`, `generate.py` all
   confirmed to have `argparse`).
2. Or make `check_import` actually honour `NEVER_RUN` as a gate (its own comment already
   documents that "NOTHING READS NEVER_RUN" is the current state) — e.g. skip real invocation for
   named modules and just do a static import/compile check instead.

Either way, the current state is a documented safety claim that the code does not deliver.

---

## FINDING 2 (MINOR, x4) — stale `file.py:NNN` cross-references inside comments in this batch

Four comments in the audited files cite a specific line (or line range) in another module as
where some piece of reasoning "already lives." All four were checked against the cited file and
none point at the content they claim to. In every case the actual matching text was found nearby
(the module has clearly been edited since the comment was written, and the citation never
followed).

1. **`src/allsweep.py` lines 127-129** (the `Verifier` class docstring):
   > "it would have broken `verify_math.py:6241` -- `any(argv == ["rosetta.py", "--check"] for
   > _label, argv in allsweep.VERIFIERS)`"

   `verify_math.py:6241` is inside an unrelated block reading `standards.py`'s `_s(...)` call
   sites (`_standards_path_b1`, `_declared_b1`, etc.) — nothing to do with `rosetta.py` or
   `VERIFIERS`. The actual `any(argv == ["rosetta.py", "--check"] ...)` check lives at
   **`verify_math.py:6824-6825`**:
   ```
   6824: check("[6e3e3e553fd5] allsweep.VERIFIERS now runs rosetta.py --check",
   6825:       any(argv == ["rosetta.py", "--check"] for _label, argv in _ALLx_b3.VERIFIERS), True,
   ```

2. **`src/allsweep.py` lines 673-674** (LINT-tier rc-predicate comment):
   > "The predicate is the one overnight.preflight (`overnight.py:961`) already uses against
   > health.py's identical `return 1 if n else 0` contract"

   `overnight.py:961` is `    for ln in fails:` inside `preflight()` — not a predicate, and
   nothing about health.py's contract. The actual matching predicate and its rationale
   ("health.py's contract is `return 1 if n else 0` (health.py:780)... CONTRADICTS that
   contract") is at **`overnight.py:1007-1015`**, with the `if` itself on line 1015:
   ```
   1015: if r.returncode not in (0, 1) or (r.returncode == 1 and not fails):
   ```

3. **`src/allsweep.py` lines 207-210** (the "franchise rank agreement" Verifier comment):
   > "rosetta.py:426-436 says the exit code 'has to carry the verdict ... so nothing that gates on
   > rc (a shell, allsweep's VERIFIERS, a scheduler) could ever learn a franchise's own published
   > ordering disagreed with our Assay'"

   `rosetta.py:426-436` is inside `_prune_scales`-type logic about numeric-scale magnitude
   ranges (`lo, hi = min(vals.values()), max(vals.values())` etc.) — unrelated. The quoted text
   is actually at **`rosetta.py:618-624`**:
   ```
   618: # THE EXIT CODE HAS TO CARRY THE VERDICT, not just the printout. This used to
   619: # `return 0` unconditionally, so nothing that gates on rc (a shell, allsweep's
   620: # VERIFIERS, a scheduler) could ever learn a franchise's own published ordering
   621: # disagreed with our Assay -- the one check this module exists for.
   ```

4. **`src/zfighters.py` lines 476-478** (the `--full` table print, epoch-column comment):
   > "Same ruling as pantheon.py:294-297, order 9d24c8a5febf, on the identical last-column cut in
   > this table's sibling."

   `pantheon.py:294-297` is the M0-M10 band-label dict (`{"M0": "a village", "M1": "a city or
   nation", ...}`) — nothing about column truncation. The actual matching comment ("`epoch[:40]`
   cut the last column of the ranked table for no gain... Order 9d24c8a5febf") is at
   **`pantheon.py:312-314`**:
   ```
   312: # `epoch[:40]` cut the last column of the ranked table for no gain: it is the LAST
   313: # column, so nothing after it needs aligning and a long epoch costs only line length.
   314: # Order 9d24c8a5febf, same rule as the citation cap below.
   ```

**Why it matters (lower stakes than Finding 1, still real):** these citations exist specifically
so a future reader can go verify the claim instead of taking the comment's word for it — the
house style in this codebase leans on them constantly. A drifted line number defeats that purpose
silently: the reader lands on unrelated code, can't confirm the claim, and has no way to tell
whether the comment is wrong or just stale. None of the four cause a runtime defect by themselves.

**Remedy:** update each citation to the verified line numbers above (or drop the line numbers and
cite by content/anchor text only, which can't drift the same way).

**Checked and found accurate (not findings, for the record):**
- `withdraw_chapters.py:146` → `publish.py:1385-1398` (the fail-closed `escalation` import) —
  verified, matches exactly.
- `withdraw_chapters.py:428` → `address_space.py:467-480` (the "shelfmark read as fresh while
  stale" argument for returning 1 on a denied write) — verified, content matches.

---

## Other things checked and NOT filed (design decisions, not defects)

- `publish.py`'s `maintenance_shift_live()` fails OPEN on an unreadable guard file — this is
  explicitly and correctly reasoned as deliberate in its own docstring ("FAILS OPEN, deliberately,
  and this is the opposite of `subsystem_stopped`'s rule"), with the asymmetric cost argued out.
  Not a finding.
- `allsweep.py`'s `art["bad"][:25]` console print and `reconcile()`'s `_head()` — both cap only
  the console line; the full list is always landed in `ALLSWEEP.json` and the count is always
  printed uncapped. Matches the pattern Hard Rule 0 itself endorses (rank, don't truncate the
  record). Not a finding.
- `entity_match.py`, `cachekey.py`, `catalog.py`, `navtree.py` — read in full; no cap, tautology,
  discarded return, or fail-open/fail-closed inversion found. `catalog.py`'s `cmd_stats` prints
  every missing source with no slice (the header's own worked example of the Hard Rule 0 fix).
  `entity_match.py`'s qualifier gate and STRONG/WEAK thresholds are consistent with their stated
  design and with `verify_math §19o/19r`'s framing as described in the header (not independently
  re-verified against `verify_math.py` itself, out of batch scope).
- `withdraw_chapters.py` — read in full, NOT run. `select()`, `_file_state()`,
  `_archive_name_free()` and the `main()` exit-code logic all look internally consistent with
  their extensive inline justifications; no additional defect found beyond what the file's own
  comments already document as fixed.
