# AUDIT — batch 09, sweep run44

Modules: `src/foreman.py`, `src/allsweep.py`, `src/rosetta.py`, `src/zfighters.py`,
`src/burgs.py`, `src/cosmography.py`, `src/runguard.py`, `src/cosmology_graph.py` (5,150 lines).
Each file was read in full, top to bottom, before anything below was written.

Overall impression: this is one of the more heavily self-audited corners of the tree. Almost
every historical defect class (falsy-zero, LIKE-substring matches, mid-name cuts, discarded
write verdicts, read-then-write races) is already named, dated and fixed in place, with the
fix's own reasoning left in the comment. My job on top of that record was to (a) verify the
specific items this batch was asked to confirm rather than re-file, and (b) find what is
genuinely new. Two new findings came out of that; the rest of this document is verification
of already-filed items, plus a couple of QUESTIONs.

---

## 1. Confirmations of already-filed items

### 1.1 `foreman.py` — the `rpm: 1` LIKE pattern (requested confirmation)

The brief asked me to check whether an over-broad remedy pattern — `LIKE '%"rpm": 1%'`, which
also strips legitimate caps of 10, 15, 19 and 100 — is still present in the source.

It is not. `clear_learned_caps()` at `src/foreman.py:175-178` reads:

```python
n += c.execute("update bucket_state set learned=NULL "
               "where json_valid(learned) "
               "and json_extract(learned, '$.rpm') = 1"
               ).rowcount
```

This compares the *extracted, typed JSON value* to the integer `1` (`json_extract(...) = 1`),
not a string substring. It cannot match `10`, `15`, `19` or `100` — a value comparison, unlike
`LIKE '%1%'`, has no way to match a leading digit of a larger number. The comment immediately
above (lines 159-169) records the fix explicitly, including a reproduction on a throwaway table
("the old predicate cleared SIX and the new one clears TWO").

**Conclusion: the over-broad pattern is fixed in the current source.** If it is still executing
somewhere, that is a stale running process holding an old in-memory copy of this function
(`foreman.py --loop` does not re-read its own source until `codewatch.exit_if_stale` fires —
see `main()`, lines 1751-1758), not a defect in `src/foreman.py` as it stands today. Worth
checking whether every long-lived `foreman.py --loop` process has actually restarted since this
fix landed; the file itself is clean.

### 1.2 `rosetta.py` — `_STAND` regex (order 77a92394a9a4) — wider than described

Filed as: the `_STAND` regex is documented as the parser for JoJo Stand statistics but does not
match what it claims. I confirm the regex itself (`src/rosetta.py:112-113`) is written as:

```python
_STAND = re.compile(
    r"\b(power|speed|range|durability|precision|potential)\s*[:=|]\s*([A-E])\b", re.I)
```

But the scope of the problem is wider than "does not match what it claims": **`_STAND` is never
referenced anywhere in the codebase except in its own defining comment.** I grepped all of
`src/` for `_STAND` and the only hits are the definition at line 112 and the comment pointing at
it from line 100 ("Stand stats are read from their parameter block instead (see `_STAND`)").
`numeric_rows()`, `ordinal_rows()` and `scales_for()` — the only functions that turn wikitext
into scored rows — never call it.

Compounding this: `ORDINAL_LADDERS` (lines 101-108) has no `"stand"` entry at all. `SCALE_QUERIES`
(line 80) does search for `"stand stats"` and `"stand parameters"`, and `_SCALE_TITLE` (line
88-90) does match a page titled around those terms, so a JoJo Stand-stats page *can* be found
and fetched by `scales_for()` — but once fetched, it falls through `numeric_rows()` (Stand grades
are letters, not numbers, so this yields nothing) and then every `ORDINAL_LADDERS` ladder in
turn (disaster/hero_class/curse_grade/ninja_rank/esper_level — none of them Stand-related), all
of which will legitimately find nothing on a Stand-stat page. The page is then discarded
(`if len(best) >= 8: ... else: continue`).

**So this is not a regex that mismatches; it is a regex that is entirely dead code, and Stand
statistics — despite being one of the two named example scales in this module's own top-of-file
docstring ("Stand statistics") — cannot be mined by `rosetta.py` at all, by any path.** JoJo is
one of the 215 catalogued sources per the project's own roll; this module's stated purpose for
it (a large-N external ground-truth check) currently does nothing.

Confidence: high (verified by grep across all of `src/`, and by reading every call site in
`scales_for`/`numeric_rows`/`ordinal_rows`).

### 1.3 `rosetta.py` — CLI output caps and mid-name cuts (order 377b69ad3c0e)

Filed as: rosetta's CLI output carries three list caps and three mid-name cuts. I found and can
confirm the following concrete instances, none of them marked with a "(+N more)" disclosure the
way the project's own doctrine (see `cosmology_graph._cut`'s docstring) requires for a compliant
display-side cut:

- **List cap:** `src/rosetta.py:462` — `top = sorted(sc["values"].items(), key=lambda kv: -kv[1])[:6]`,
  in `--probe` mode. Shows only the top 6 entities of a mined scale, unmarked, with no "and N
  more" line.
- **Mid-name cut #1:** `src/rosetta.py:464` — `print(f"          {n[:34]:<36}{v:,.0f}")`, in the
  same `--probe` loop. A name over 34 characters is truncated with no ellipsis.
- **Mid-name cut #2:** `src/rosetta.py:617` — `{r['scale'][:38]:<40}` in the `--check` UNSCORED
  branch.
- **Mid-name cut #3:** `src/rosetta.py:624` — the identical `{r['scale'][:38]:<40}` in the
  `--check` scored branch.

I only found one genuine *list*-truncation (the `[:6]` in `--probe`); the other two "caps" the
filed order counts may refer to the two occurrences of the scale-name cut, which is arguably a
cut rather than a cap. Either way, all four sites are confirmed present as of this reading, all
unmarked, and — per the project's own stated exception for marked, fully-preserved-elsewhere
cuts — none of the four currently qualifies for that exception, since `--probe` and `--check`
have no backing artifact that holds the untruncated values the console line is a head of.

Confidence: high (exact line numbers verified against the file as read).

### 1.4 `runguard.py` — fail-open on a corrupt guard (order 70f66fbd98aa) — confirmed present, not re-filed

Per the brief, this is an open owner question, not a defect. I confirm the mechanism as
described: `read()` (`src/runguard.py:52-69`) returns `None` for both "no file" and "unreadable
file" without distinguishing them, and `holder_is_live()` (lines 139-151) treats `rec is None`
identically to "no predecessor" (`if not rec or rec.get("done"): return False`). So `claim()`
(line 168-169: `prior = read(path); if holder_is_live(prior): ...`) will happily claim the guard
over a torn or corrupt `MAINTENANCE_RUN.json`, exactly as filed. No action taken; flagging only
as verified-present per the instruction.

### 1.5 `cosmography.py` — `SIZE_CLASS_MAX_GALAXIES` vs. `SIZE_CLASSES` (self-documented, not re-filed)

Not part of the requested-confirmation list, but worth recording since I verified it concretely:
the module's own comment (`src/cosmography.py:151-155`) already states that with the current
`SIZE_CLASSES` multipliers, both `POCKET` (`1e-9`) and `MINOR` (`1e-6`) computed against
`GALAXIES_DEFAULT` (`2.0e11`) produce 200 and 200,000 galaxies respectively — both far over the
`SIZE_CLASS_MAX_GALAXIES` ceiling of `1.0` — so `census("POCKET")` or `census("MINOR")` called
with the default galaxy count will **always** raise `ValueError` via `validate()`'s category
check (lines 290-296). This is explicitly left for an owner ruling in the comment itself, so I
am not filing it as new. I did verify, by grepping every caller of `cosmography.census(` in
`src/` (`address_space.py`, `pipeline.py`, `verify_math.py`), that **every existing call site
passes `"STANDARD"` only** — nothing in the tree currently calls `census()` with `POCKET` or
`MINOR`, so the always-refuses state is real but currently dormant. Worth knowing if anyone
plans to wire up pocket-dimension or single-galaxy sources (the charter names II.N.3 as exactly
that class) before the ruling is made.

---

## 2. New findings

### 2.1 `foreman.py` — the MODEL lane's safety gate never runs the VERIFY tier it needs to (MEDIUM-HIGH confidence, framed partly as a QUESTION)

`attempt_patch()` (`src/foreman.py:1336-1442`) is the function that lets a local/cloud model
rewrite one function in live source, unsupervised, and decides whether to keep or revert the
patch. The keep/revert decision runs entirely through `_checks_pass()` (lines 1278-1333):

```python
r = _run(["-c", f"import sys; sys.path.insert(0, r'{SRC}'); import {module}"], timeout=300)
...
r = _run([os.path.join(SRC, "verify_math.py")], timeout=1200)
...
r = _run([os.path.join(SRC, "allsweep.py"), "--quick"], timeout=900)
```

`allsweep.py --quick` is documented, in `allsweep.py` itself, to run **only** the IMPORT, LINT
and RECONCILE tiers — the `--quick` help text says "imports and reconciliation only", and the
code (`allsweep.py:701-702`, `:726-727`) gates both the VERIFY tier (`if not a.quick: ... VERIFY
...`) and the ESTATE tier the same way. The VERIFY tier is exactly the one that runs each of the
ten `VERIFIERS` (`allsweep.py:156-221`) as a real subprocess and checks its exit code against a
declared contract (`RC_BROKEN`/`RC_FINDINGS`).

So a MODEL-lane patch to any of the ten modules behind those VERIFIERS — `health.py`,
`silence.py`, `coverage.py`, `verify_math.py`, `thread_integrity.py`, `anchors.py`, `audit.py`,
`identity.py`, `reference.py`, **`rosetta.py`**, `cascade_bridge.py` — can regress that module's
CLI-level exit-code contract without `_checks_pass` ever noticing, *unless* `verify_math.py`
happens to independently pin that exact behavior by calling into the module's functions
directly (rather than via subprocess).

This is not hypothetical for `rosetta.py` specifically, because I read the whole file: its own
docstring at `check()` (lines 340-363) records that `verify_math` **does** drive `check()`
directly with synthetic data — which would catch a regression to the ranking/scoring logic
itself — but the CLI wiring in `main()` that turns a disagreement into an exit code
(`if bad: ... return 1`, line 635-638) is a separate piece of code that only the VERIFIERS row
`Verifier("franchise rank agreement", ["rosetta.py", "--check"], RC_BROKEN)` exercises as a
subprocess. That is precisely the piece of code this project's own history says went unread for
eleven runs the first time it broke ("for eleven runs neither consumer read it," line 210). A
MODEL-lane edit to that `if bad: return 1` line — reverting it to an unconditional `return 0`,
say — would import fine, would not touch anything `verify_math.py` asserts on directly (since
`verify_math` calls `check()`, not `main()`), and `allsweep.py --quick` would never run
`rosetta.py --check` as a subprocess to notice. The patch would be reported "patched and
verified" (line 1423) and kept.

This may be an accepted trade-off — running the full VERIFY tier inside `_checks_pass` would
add real minutes per patch attempt, and the file's own docstring already accepts a related risk
("no pre-patch baseline is taken"). But as written, the module docstring's own claim that a kept
patch has cleared "everything that must still be true" (line 1279) is stronger than what the
gate actually exercises for nine of the ten VERIFIERS-tier modules. I'd frame this as a QUESTION
for the owner: should `_checks_pass` run the full (non-`--quick`) `allsweep.py` — or at minimum
the one VERIFIERS row matching the module being patched — before keeping a patch to a module
that has a VERIFIERS entry?

Confidence: high on the mechanism (verified against both files' actual code), medium on whether
it constitutes a "bug" versus an accepted cost/coverage trade-off — hence framed as a question.

---

## 3. Everything else read and checked, with no new finding

For the record (this project's own doctrine treats absence-of-finding as worth stating, not
silently passing over):

- **`foreman.py`**: `DENYLIST` (line 120-121), `MAX_PATCH_LINES` semantics (`> MAX`, confirmed at
  line 1401), `lines_changed()` (difflib-based, not a length-delta), `regex_touched()`,
  `_function_source()`'s qualified-name resolution, the `REMEDIES` "always" re-run logic in
  `round_once()` (lines 1631-1644), `kill_stalled_job()`'s restartability gate, and every
  documented atomic-write site were all re-verified against the actual code and match their
  comments. No new defect found beyond §2.1.
- **`allsweep.py`**: `Verifier.__len__`/`__getitem__` back-compat shim, `run_verifier`'s
  `failed` computation, `_row_is_fault`'s fail-closed default, `estate_faults`, the `bad` count
  formula (no double-counting between `estate_faults` and `artifacts.bad`), and the process
  dedup via `overnight._cmd_is_running` all check out against the code as written.
- **`zfighters.py`**: `compute()`, `value()`, the Son-Goku fallback, and the atomic/gated write
  all match their comments; `textwrap.wrap` is confirmed non-truncating.
- **`burgs.py`**: `burg_count`, `rank_population`, `_rank_at_or_above`, `class_histogram` (the
  cumulative-subtraction logic over `reversed(CLASSES)` is correct — verified by hand-tracing
  the boundary arithmetic), and `burgs_for`'s narrow-only `--limit` clamp all check out.
- **`cosmography.py`**: the full derivation chain in `census()`, `validate()`'s five checks, and
  `KARDASHEV_MIX` summing to 1.0 were hand-verified arithmetically against the comments' own
  worked numbers (e.g. the "six galaxy-spanning empires per galaxy" pre-fix figure at line 93
  reproduces exactly from the old constant).
- **`runguard.py`**: the digest-before-read ordering in `claim()`/`beat()`/`release()`, and the
  CAS handoff through `_land_claim`, correctly prevent the two hazards their comments name I
  looked for a residual TOCTOU between `digest_of()` and `read()` and could not find one that
  isn't already closed by the CAS at write time (a change landing in that window forces the
  eventual `replace_if_unchanged` to fail closed, not overwrite).
- **`cosmology_graph.py`**: `build_graph()`'s weighting formula, `components()`'s union-find via
  BFS, and the `--write` gating all match the comments; the `--show`/`--threshold` split between
  console framing and clustering is honored exactly as documented.
