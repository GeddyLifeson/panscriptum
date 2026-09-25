# sweep61 batch 09 audit

Scope (read in full, start to finish, no sampling):

- `src/foreman.py` — 2279 lines
- `src/codewatch.py` — 1168 lines
- `src/derivation.py` — 816 lines
- `src/manifest_builder.py` — 671 lines
- `src/zfighters.py` — 536 lines
- `src/suppressions.py` — 425 lines
- `src/deprecated/catalogue_local.py` — 333 lines
- `src/tuning.py` — 286 lines
- `src/lognames.py` — 52 lines

All nine read completely. `deprecated/catalogue_local.py` is a self-refusing module (raises
`SystemExit` at import time except for `--help`) — read in full as source, per the file's own
account of why it is kept unrepaired; no new finding recorded against it since the module is
already documented dead-by-design.

## Overall

These modules are extraordinarily heavily audited already — nearly every function carries a
multi-paragraph comment recording a prior sweep's finding, the measurement that proved it, and
the fix. Most candidate issues I found on first read turned out to already be the *subject* of
an adjacent comment explaining why the code is the way it is (a QUESTION, not a finding, per the
brief). One genuine new VERIFIED finding surfaced; everything else I could substantiate was
already on record in the source itself.

## Findings

### 1. VERIFIED — `codewatch.py:runs_script` mis-parses interpreter flags that consume a value, unlike its sibling `whoruns.py:script_of`

`codewatch.runs_script()` (lines ~344–398) is the predicate `twins()` and `claim_singleton()`
use to decide whether a live process is running a given `src/<module>.py`. Its scan for the
script token is:

```python
script = None
for arg in argv[1:]:
    a = str(arg).replace("\\", "/")
    if a.endswith(".py"):
        script = a
        break
    if not a.startswith("-"):
        break            # a non-flag, non-.py argument: this is not `python x.py`
```

This treats *every* token starting with `-` as a value-less interpreter flag to skip, and treats
the first non-flag token as either the script or proof this isn't `python x.py`. That is wrong
for the small set of CPython flags that consume a **separate** following token — `-X <opt>`,
`-W <action>`, `--check-hash-based-pycs <mode>`. For `python -X utf8 script.py`, the loop sees
`-X` (starts with `-`, skip), then sees `utf8` — which does not end in `.py` and does not start
with `-` — and `break`s with `script` still `None`, so `runs_script` returns `False` even though
the process is plainly running `script.py`.

This is exactly the bug `src/whoruns.py` was written to fix, in the same file's own words:

```python
# INTERPRETER FLAGS THAT EAT THE NEXT TOKEN. `-X utf8 script.py` puts a bare `utf8` between the
# flag and the script, and a scan that treats every non-flag token as "the script slot" reads
# `utf8` as "a bare non-flag that is not a .py" and returns None -- a CONFIDENT FALSE NEGATIVE,
# the exact answer this module exists to stop it giving (2026-09-09 sweep, batch 15).
_FLAGS_WITH_A_VALUE = ("-X", "-W", "--check-hash-based-pycs")
```

`whoruns.script_of()` special-cases `_FLAGS_WITH_A_VALUE` by advancing the index by 2 instead of
1. `codewatch.runs_script()` has no equivalent branch — it was not touched by the 2026-09-09
sweep that fixed the identical defect one file over, even though `runs_script`'s own docstring
claims it exists so this exact matching logic can be "tested without a process table" and be
depended on by `twins()`/`claim_singleton()` for duplicate-process and singleton detection.

**Verified by:** direct line-by-line comparison of `codewatch.runs_script` against
`whoruns.script_of` and `whoruns.py`'s own docstring naming the failure mode; confirmed by
tracing `-X`/`-W` token consumption by hand against `runs_script`'s loop.

**Live impact today:** dormant, not active. Grepped every `subprocess.run`/`Popen` call in
`src/` that launches `sys.executable`; the only interpreter flag ever prepended to a managed
job's argv is `overnight.py`'s `[PY, "-u", *args]` for STANDING daemons, and `-u` takes no
value, so it is handled correctly by the existing `startswith("-")` skip. No launcher in this
tree currently uses `-X`, `-W`, or `--check-hash-based-pycs`. The bug is real and would silently
make `twins()`/`claim_singleton()` report "no twin found" for a process actually running the
watched script the moment either flag is ever used to launch one — the same "confident false
negative" class `whoruns.py` was written specifically to end elsewhere in this codebase.

## Not reported as findings (already recorded in the source, or design questions)

- `foreman.py`'s `round_once` remedy-list `break` logic (an `always`-marked remedy that succeeds
  does not itself break the remaining-remedies loop) — traced through every current entry in
  `REMEDIES`; every `always`-marked remedy is the last element of its list, so this is inert
  today and is a QUESTION about future-proofing, not a live bug.
- `manifest_builder.load_record`'s exact-match early return assumes no two record filenames
  normalise to the same string — plausible in principle, not reproducible against the shipped
  `data/records/` without live data, and the function's own extensive comments already show three
  rounds of hardening against near-miss classes; treated as a QUESTION, not a finding.
- Every other "check that cannot fail" / fail-open / truncation candidate I traced in
  `tuning.py`, `suppressions.py`, `zfighters.py`, `derivation.py`, `lognames.py`, and the rest of
  `foreman.py`/`codewatch.py` resolved to a defect already named and fixed by an in-file comment
  (each carries its own "order" / "sweep" citation), not a new one.

## Summary of findings by kind

- Real bugs: 1 (VERIFIED, dormant) — `codewatch.py:runs_script` / `-X`,`-W` value-flag mis-parse.
- Tautologies / checks that cannot fail: 0 new.
- Fail-open guards: 0 new.
- Caps/truncations: 0 new.
- False comments/docstrings: 0 new.
- Dead code: 0 new (the one dead module in scope, `deprecated/catalogue_local.py`, is already
  self-documented as dead by design).
