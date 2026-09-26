# sweep63 batch04 — audit report

Scope (read in full, start to finish, no sampling):

- src/mutate.py           3206 lines
- src/allsweep.py         1025 lines
- src/address_space.py     679 lines
- src/worldseed.py         536 lines
- src/sevenfold.py         441 lines
- src/wh40k.py             351 lines
- src/audit.py             275 lines
- src/compress_store.py    149 lines

Total 7,662 lines, all eight read in full.

## Method

All eight modules already went through sweep61 (batch03: wh40k.py; batch04: mutate.py,
allsweep.py, address_space.py, worldseed.py, sevenfold.py; batch08: audit.py,
compress_store.py) with 0 VERIFIED new defects reported in any of the three. That pass and
this one are close in time (sweep61's batch03/04/08 reports are dated 2026-09-16, same day
as several of these files' mtimes), so this was a genuine re-read rather than a rubber stamp
of the prior verdict — every line was read again start to finish, watching specifically for
anything the extremely dense in-line order/citation commentary in this codebase has NOT
already named and fixed. `address_space.py` grew from 674 to 679 lines and `wh40k.py` from
350 to 351 since sweep61's count, confirming the files did move.

This codebase's self-documentation is exceptional even by this project's own standard —
nearly every historically-found defect carries an order id, a measured before/after, and in
several cases a citation to the exact incident that motivated the fix. I did not re-report
anything the code's own comments already name as known, fixed, deliberately kept, or
owner-ruled. I read every branch of every function, not just the ones a synopsis would
suggest matter, including `mutate.py`'s ~3,200 lines of sandbox/lock/mutation-loop machinery.

## Findings

### 1. SUSPECTED — `allsweep.py`, `main()`: `--quick` does not skip the LINT tier despite its
own help text promising it will.

`allsweep.py:751` declares:

```python
ap.add_argument("--quick", action="store_true", help="imports and reconciliation only")
```

`a.quick` is checked exactly twice in `main()`: gating the VERIFY tier at `allsweep.py:830`
(`if not a.quick:`) and the ESTATE tier at `allsweep.py:855` (`if not a.quick:`). The LINT
tier — the `subprocess.run([sys.executable, "-m", "pyflakes"] + ...)` block at
`allsweep.py:778-827`, which lints every module under `src/` (over a hundred files) with a
120-second subprocess timeout — has no `a.quick` guard at all and runs unconditionally
between IMPORT and the (possibly skipped) VERIFY tier.

So `python src/allsweep.py --quick`, advertised and presumably used as "imports and
reconciliation only" for a fast check, still pays for a full pyflakes pass over the whole
tree every time. This is a real behavioral gap against the flag's own documented contract —
not a correctness bug in what LINT reports, just a mismatch between what `--quick` promises
and what it does. Graded SUSPECTED rather than VERIFIED because I cannot rule out that this
is deliberate (LINT is cheap relative to VERIFY/ESTATE and someone may have decided it
belongs in "quick" regardless of the help text), but nothing in the surrounding comments
says so, and every other use of `a.quick` in the file is a real gate.

Suggested fix: either wrap the LINT block in `if not a.quick:` to match the help text, or
reword the help text (e.g. "skip VERIFY and ESTATE") to match the actual behavior.

### 2. SUSPECTED — `mutate.py`, `_gate_result()` (line 798): gate subprocess output is
captured without `encoding="utf-8", errors="replace"`, unlike the sibling code in
`allsweep.py` that was explicitly hardened against exactly this for the same two programs.

```python
r = subprocess.run(cmd, cwd=(cwd or HERE), capture_output=True, text=True,
                   creationflags=_NO_WIN, timeout=timeout, env=env)
```

`_gate_result` is what runs every gate in `FAST_GATES`/`CONFIRM_GATES` — `verify_math.py`
and `drill.py` — both at baseline time and once per mutant, from `baseline()`,
`flaky_gates()`, `hang_confirms_a_kill()`, and the main mutation loop in `_run_mutation()`.
None of those call sites pass `env=` (so the child inherits whatever `os.environ` the
`mutate.py` process itself has — no `PYTHONIOENCODING` is set on this path, unlike the
`--detach` self-respawn at line 2691 which does set it), and `_gate_result` itself passes
neither `encoding=` nor `errors=` to `subprocess.run`, so decoding falls back to
`locale.getpreferredencoding()` — the Windows ANSI code page unless UTF-8 mode happens to be
active machine-wide.

`allsweep.py` runs these same two programs (`verify_math.py`, `drill.py`) as part of its own
VERIFY tier and explicitly guards against this — `allsweep.py:388-391` and its surrounding
comment: "utf-8 explicitly: Windows decodes a child's output as cp1252 by default, and this
project's output is full of the charter's own typography. A verifier whose report contains
an em-dash would have crashed the auditor rather than been read." That is not a hypothetical
concern for these two files specifically: `verify_math.py` contains 58 em-dash (`—`)
characters in its own `print(...)` calls and `drill.py` contains 94, confirmed by direct
grep.

`mutate.py`'s own file-corruption guard at the top (`_BAD_CHARS` check) shows the project is
already alert to encoding fragility in this exact codebase, and `_gate_result`'s docstring
and the module's general standard elsewhere (`open(..., encoding="utf-8")` is used
consistently for every file `mutate.py` itself reads/writes) show UTF-8-explicit handling is
the house rule — it simply was not carried to this one `subprocess.run` call, which is the
one reading output from the two em-dash-heavy programs.

Practical effect if triggered: `_gate_result` catches decode failures via its blanket
`except Exception as e:` and returns `"ERROR:%s|%s" % (type(e).__name__, name)`, which
`could_not_judge()` recognizes — so the failure mode is fail-closed (an unusable baseline
gate refuses the whole run at `_session`'s `unusable_gates(base)` check, or a single mutant
scores INDETERMINATE rather than a false kill/survivor). I am not able to confirm this
actually fires on the machine mutate.py runs on — the module's own comments describe many
completed multi-hour runs with real kill/survive counts, which would not be possible if this
fired on every gate call, so either the box's effective codepage already tolerates it or
`PYTHONIOENCODING` is set in the ambient shell environment mutate.py inherits when launched.
Grading SUSPECTED rather than VERIFIED because reproducing it would mean running a gate
subprocess, which is outside this audit's read-only remit, and the existing operational
history argues it is currently dormant rather than live. Flagged because it is a genuine,
traceable gap against a fix this project already made once in the sibling module for the
identical two programs' output, and a future change to the shell/codepage this runs under
(or a machine migration) would reopen it silently — the failure mode is fail-closed today,
but "fails closed today, for reasons nobody wrote down" is exactly the shape this project's
own doctrine (Hard Rule -1, INDEPENDENT/FAIL CLOSED/PROVEN) asks to have stated rather than
assumed.

Suggested fix: add `encoding="utf-8", errors="replace"` to the `subprocess.run` call in
`_gate_result` (mutate.py:797-798), matching `allsweep.py:319` and `:391`.

## No other findings

Beyond the two above, no tautological/cannot-fail check, no fail-open guard, no new
undisclosed cap or truncation (Hard Rule 0), no wrong-variable/off-by-one/unit-mix bug, no
race on a shared file outside `silence.replace_retry`, no resource leak, and no
exception-path state corruption was found in any of the eight modules beyond what their own
comments already document as found, fixed, or deliberately retained. Specifically checked
and found sound:

- `compress_store.py`: temp-then-`replace_retry` write, hash-verifying `load()`, zstd/gzip
  fallback — all as documented, no gaps.
- `audit.py`: `BACKSCAN`'s invariants and sample passes are uncapped where the file's own
  comments say they must be; the `_JUNK` navigation-artefact regex is anchored the way its
  comment describes; no truncation slipped back in.
- `wh40k.py`: all 55 ROSTER axes are 3-tuples with a real `wiki`/`canon` provenance tag
  (matching `compute()`'s docstring claim); `_provenance()` defaults to `unattributed` rather
  than guessing, as documented.
- `sevenfold.py`: `_even_cuts`/`seams`/`shelve` balance logic traced against its own
  extensively-documented history of two prior broken shapes; the current window+median-cut
  construction does what the docstring claims. `UNSHELVED` accounting and the atomic,
  gated `SEVENFOLD.json` write are correct.
- `worldseed.py`: feature-matching fallback-to-seed logic, band parsing/provenance tagging,
  `ONOMASTICON`/`CONTINUITY_GROUPS` failure reporting, the `limit is not None` fix, and the
  designation-collision report on write are all consistent with their documentation.
- `address_space.py`: `_tier_counts`/`_bits`/`FIELDS`/`WIDTHS`/`_hash_offsets` derivation
  traced by hand against the worked example in `main()`; `pack`/`unpack` round-trip by
  keyword everywhere; `shelfmark()`'s charted-vs-hashed field split and `?`-blanking via
  `charted_gaps()` match the docstring exactly.
- `allsweep.py`: `reconcile()`'s band-ceiling, host, coverage, purge, phase and
  process-liveness checks traced individually; `estate_faults`/`_row_is_fault` fail-closed
  correctly on a keyless row; the `bad` exit-code sum covers IMPORT/VERIFY/LINT/ESTATE and
  the write-denied case, with RECONCILE deliberately and honestly left ungraded.
- `mutate.py`: the sandbox build (junction vs. hardlink vs. copy per subtree), the
  `BUILDING_PREFIX`→`SANDBOX_PREFIX` atomic-rename claim sequence, `reap_orphans`'s
  ownership-beats-age logic, the lock's O_EXCL acquire/token-checked release, the
  AST-span-based mutation locator (`_spot`/`_between`/`_token_pos`/`_fallback_spot`), the
  differential (not absolute) kill test, `hang_confirms_a_kill`'s two-reading asymmetry
  check, and the mid-run `_refresh_baseline` drift-recording were all traced end to end.
  No fail-open path, no silent truncation of `survivors`/`not_attempted`/`indeterminates`,
  and the live-tree-refusal / missing-baseline-refusal guards in `_run_mutation` do what
  their comments claim.

## Coverage recorded

Recorded via `sweep_plan.record('run63', [...], batch=4)` for the eight modules above.
