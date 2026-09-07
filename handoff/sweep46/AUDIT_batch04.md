# run46 batch 4 audit

Modules read end to end (every line): `src/mutate.py` (2705), `src/ledger_guard.py` (810),
`src/secondopinion.py` (665), `src/sevenfold.py` (441), `src/prose_gate.py` (402),
`src/resonance.py` (298), `src/cachekey.py` (193), `src/repass_bands.py` (156). 8,670 lines.

Method: judged on the executable line, never on a comment describing a prior shape. Every
finding below was checked against the live source at the line numbers cited, not inferred from
a docstring's own claim about itself. Before filing anything, I searched `state/workorders.json`
and `state/workorders_closed.jsonl` for prior findings on the same site, because this batch turns
out to be very heavily prospected already (sweeps 39 through 45 all touched pieces of it) --
several things I found independently on first read were already filed, and in one case already
fixed. Where that happened I say so instead of re-filing a duplicate.

## `prose_gate.py` — the interlock CLAUDE.md forbids weakening

Read in full. `NEVER propose weakening it` was honoured: no changes suggested here of any kind.
This is the best-defended module in the batch. `SECTION_LOSS_FLOOR = 0.0`, `MIN_ENTRY_BODY_CHARS
= 120`, the axis-score regex that skips markdown decoration (`_AXIS_RE`), and the extra-entries
charge in `section_shortfall` (padding invented entries no longer scores 1.0) are all live,
correct, and match their docstrings. `unearned_instrument`/`cited_names_for` fail closed to "not
cited" on any read error, which is the right direction for a check whose job is refusing a
fabricated Assay score. No findings.

## `cachekey.py` — the M23 collision fix

Read in full. `load()` verifies `owns(doc, name)` before trusting a cache hit (a name-sanitizer
collision is a MISS, not a hit) and `write_path()` disambiguates onto a suffixed sibling rather
than silently overwriting a different entity's file. `provenance_ok` correctly returns the
three-way `True/False/None` (proven / stale / unverifiable) rather than collapsing "nobody
checked" into a false negative or positive. No findings.

## `secondopinion.py` — the independent second opinion

Read in full, including the `report()` mid-scan tree-fingerprint guard and the returncode
contracts for ruff/vulture/detect-secrets. **Verified the module's own central claim holds on
every code path**: `run()` never returns an empty finding list for a tool that did not actually
answer — `_exe()` distinguishes `FileNotFoundError` ("no such file") from every other spawn
failure ("UNASKABLE (reason)"), and both `_ruff`/`_vulture`/`_detect_secrets` check `returncode`
before trusting stdout, so a CLI-usage error (rc=2, empty stdout) cannot be parsed as `[]` and
read as a clean pass. `ran_clean()` requires every tool's status to be `"RAN"`, not merely an
empty `findings` list. This is the one place in the batch where the priority-1 property is the
module's entire subject, and it holds under direct reading.

Confirmed against `state/workorders.json` order `91cf746c651e` (QUESTION, INFO, still open):
the docstring's closing line says the module "escalates to JANITOR ... not to OWNER," but the
module never imports `escalation` or calls `escalate()` — the only recording is `silence.note()`.
Verified still true on today's source. Not re-filed; the existing order already frames both
readings correctly.

Minor, not filed: `_exe()`'s per-candidate probe treats a nonzero `--version` exit the same as
"try the next candidate," and if every candidate returns nonzero without raising, the function
reports the default reason `"no such file"` (NOT INSTALLED) even though a binary was found and
ran. All three adopted tools return 0 for `--version` in practice (the module's own "measured,
not assumed" methodology would apply here too), so this is a real gap in the contract but very
low materiality. Flagging in case a future tool addition breaks the assumption.

## `sevenfold.py`, `resonance.py` — read for completeness

Both read in full. `sevenfold.py`'s `shelve()`/`seams()` balance-by-construction logic is
self-documented against three previously-measured-worse alternatives and the docstrings' claimed
numbers match the code (window + median-eligible cuts). The two console sample listings
(`sample shelfmarks`, `sample WORLD shelfmarks`) are correctly headed "first 8 of {total}" —
not a Hard Rule 0 violation, this is disclosed ranking, not silent truncation. `resonance.py`
is honest in its own docstring that `hodge_decompose`/`resonance_strength` have zero production
callers; the Gauss-Seidel convergence fix (vs. the earlier non-converging Jacobi sweep) is
correctly guarded by `converged` in every return path. No findings in either file.

## `repass_bands.py` — read for completeness

Read in full. Confirmed the module's own in-code commentary against the source: the ROSTER of
survivors/demoted entries is genuinely uncapped (matches the comments describing sweep42/43
fixes), and the entity-name field uses `:<32` padding, not slicing. The per-row evidence/reason
truncations (`(syn.get("evidence") or "")[:70]` at line 52, `sn[:70]` at lines 66/68) are real,
unmarked cuts on a "reason" field — but this is **already filed** as part of `state/workorders.json`
order `fe99e57e1993` (`UNMARKED_NAME_CUTS_SWEEP44`, LOCAL/MINOR), which names
`repass_bands.py:52,66,68,126,137` explicitly. Verified still open, still accurate against
current source. Not re-filed.

## `ledger_guard.py` — the relay's integrity checks

Read in full, all three mechanisms (append-only containment, structure/floor, hash chain) plus
the acknowledgement registry. The design is sound: `check_append_only` uses longest-common-
prefix-plus-suffix rather than substring containment (correctly handles the newest-on-top
convention), `_lost_fraction` uses multiset (Counter) diff rather than set diff (closes the
duplicate-line false-negative the file's own comment documents), and `verify_chain`'s SHRANK
test uses `is not None` rather than truthiness (correctly catches a wipe-to-empty).

Investigated the priority-2 pattern here specifically, per instructions: the module's own
comments (lines 520-529) record a 2026-09-01 incident where a drill fixture "repointed only half
of this module's globals" and sealed a test fixture into the REAL chain/snapshot directory —
exactly the "gate writes state it should not, and that write is the fault it tests for" shape
this audit was told to hunt for. **This is already fixed, not a live gap**: `state/
workorders_closed.jsonl` order `be33a61be79f` (resolved 2026-09-02) shows `drill.py` now has one
`_ledger_redirected(root)` context manager that repoints `HERE`, `SNAPSHOT_DIR`, `CHAIN` and
`ACKNOWLEDGED` together and *asserts* all four land under a temp root before any probe body runs
— so a future net can no longer redirect a subset by accident. I confirmed `ledger_guard.py`
itself still exposes exactly those four independent module-level globals (`CHAIN` line 179,
`SNAPSHOT_DIR` line 184, `ACKNOWLEDGED` line 543, plus `HERE`-relative reads via `_read()`), which
is why a single-point context manager on the *caller* side was the right fix rather than something
inside this file. No new finding; noting the verification for the record.

## `mutate.py` — the two flagged items, both confirmed against current source

### 1. `_session()` KeyError on an unusable mid-run baseline refresh — STILL LIVE, re-confirmed

This is real and exactly as described in the special context. `_run_mutation._refresh_baseline`
(now ~1977-2046) appends two different event shapes to the same `drifted` list depending on
whether the mid-run rebaseline could complete:

- unusable (now ~2003-2014): `{at, refresh_unusable, kept_previous_baseline,
  verdicts_since_last_good_baseline}`
- moved (now ~2026-2029): `{at, gates_that_moved, verdicts_now_in_doubt}`

Both leave via `result["baseline_drifts"]` (~line 2188). `_session`'s report loop (now
~2595-2606) reads **only** the second shape, unconditionally:

```
for d in (r.get("baseline_drifts") or []):
    moved = ", ".join(sorted(d["gates_that_moved"]))
    doubt = d["verdicts_now_in_doubt"]
```

An unusable-refresh event carries neither key — `d["gates_that_moved"]` raises `KeyError`, with
no handling anywhere in the loop or in `_session`'s enclosing `try/finally` (the `finally` at
line 2699 only removes the sandbox; there is no `except` that would let the session report and
continue with the next target). This aborts the **entire remaining session**, not just the
current target — findings already journaled to `state/MUTANTS_SURVIVED.jsonl` survive, but any
target not yet reached is silently skipped with only a bare traceback as the record of why.

This was already filed as `f4af474dfc49` (SESSION, MAJOR) by sweep45-batch04. I independently
re-derived the identical fault by reading the code, then verified the old citation's line numbers
had drifted (1953-1956/2542-2544 → now 1975-2046/2595-2606) and **refreshed the existing order**
(same code/`where`, so `order_id` — content-addressed on `(code, where)` — resolves to the same
id rather than forking a duplicate) with the current line numbers and an explicit note that the
`where` string is deliberately left unchanged for continuity. `seen` is now 3.

**This is the single most operationally important finding in this batch.** Given the special
context describes a 20-hour `--target all` pass as imminent, and `--rebaseline-every` defaults to
1800s against an hours-long run on a shared machine, this WILL very likely fire and truncate the
run. It should be fixed (branch on which event shape `d` is before touching either key) before
that pass, not discovered by it.

### 2. `sandbox()`'s mkdtemp/claim race — confirmed as a live, accepted, OWNER-level open question

The window is real, exactly as documented in the code's own comment at `sandbox()` (order
`404d0ccf9df5`, closed as "verified, not fixed"): `tempfile.mkdtemp(prefix="panscriptum_mutate_")`
returns a directory that already matches `SANDBOX_PREFIX` — and is therefore visible to
`reap_orphans()` — one statement before `_claim_sandbox()` writes the owner file that would
protect it. `reap_orphans()`'s own `older_than` age gate closes this in every real production
call (default 6h, so a directory whose mtime is microseconds old is always skipped before
ownership is even consulted) — but `older_than=0` removes that gate entirely, and is used by
drill's own M46 probe to prove the reaper can reap at all.

This is not hypothetical: `state/workorders.json` order `f9643582fd29` (OWNER, MAJOR, still open)
is a self-report of exactly this landing in production on 2026-09-05 — a `--target all` pass died
on its third target, 60 seconds after three back-to-back `drill.py` runs, with a bare
`FileNotFoundError` on the sandbox's own `escalation.py`. The mitigation already applied
(`drill.py`'s two reap nets now redirect `tempfile.tempdir` to a throwaway root, so the drill's
own `older_than=0` calls can no longer see a real sandbox) is a real containment, but the order is
correctly left open at OWNER rung: the window in `sandbox()` itself is unchanged, and
`older_than=0` is still reachable from anywhere, not only from the drill.

Read the code with the specific question the task posed — "is there a way to close it that does
not break the reaper's contract?" — in mind. The order's own text already identifies the answer
that would close it cleanly: build the directory under a name that does **not** match
`SANDBOX_PREFIX` (or under a different temp root entirely), write `_claim_sandbox()`'s owner file
into it, and only then rename (`os.replace`, atomic on the same volume) it into its final
`SANDBOX_PREFIX`-matching path. `reap_orphans()` only ever discovers directories by listing
`tempfile.gettempdir()` and filtering on `name.startswith(SANDBOX_PREFIX)`, so a directory that
does not yet carry that prefix is invisible to it by construction — the reaper's contract (age
gate + ownership beats age) is completely unchanged; the race is closed by never publishing an
unowned directory under the name the reaper watches for. This is a genuine, mechanical fix and
does not require weakening `reap_orphans()` in any way. It is exactly the kind of change the
existing order and this project's own doctrine reserve for a person to approve (sandbox/ownership
machinery, "does not let an automated pass touch without a person reading the change") — not
something to apply here. Noted for the owner's attention when `f9643582fd29` is picked up; not
re-filed, since the existing order already carries this reasoning and is at the correct rung.

### Other `mutate.py` observations, not filed

- Every `silence.note(...)` call in this file fires from mutate.py's OWN control-plane code
  (lock/reap/sandbox bookkeeping), running in the host process against the real `src/` — not
  from inside a sandboxed gate subprocess, whose `HERE` resolves inside the sandbox because the
  copied module's own `__file__` does. These are genuine operational failures, not deliberate-
  test probe litter; writing them to the real `state/failures.json` is the same pattern every
  other house module uses and is correct here.
- Console-only truncations of gate signatures (`sig[:90]` at lines 2441/2480/2512,
  `str(a_)[:40]` at 2534) carry no "..." marker, unlike this same file's own explicit doctrine
  two lines away (2110-2114) about the `[:70]` on `was`/`became`, which argues a display cut is
  fine specifically *because* the full value is recoverable elsewhere (journal / `base` dict).
  That argument does technically apply here too (the full signature lives in `base`), so this
  reads as consistent with the file's own stated standard rather than a violation of it — flagged
  as a QUESTION, not a finding, and not filed given the low materiality (gate signatures are
  short summary lines in practice).
- `state/MUTANTS_SURVIVED.jsonl`/`state/MUTANTS_RULED_EQUIVALENT.json` writes are the module's
  actual accounting mechanism (survivors, rulings), not probe litter; `_write_rulings` is
  correctly restricted to the two human-driven CLI flags and never called from inside a mutation
  run itself.
- Did not find any additional site where a mutation run's deliberate-failure path (the mutated
  code itself, executed inside the sandbox) can reach the LIVE `state/failures.json` or any other
  live ledger — the sandbox copy of `state/` (JSON/JSONL files + the six dashboard logs +
  cascade's scratch DB via SQLite backup API) is what any sandboxed gate subprocess would write
  into, by the same `HERE`-resolves-to-`__file__` mechanism above.

## Coverage

`python -c "import sys;sys.path.insert(0,'src');import sweep_plan;sweep_plan.record('run46',['mutate.py','ledger_guard.py','secondopinion.py','sevenfold.py','prose_gate.py','resonance.py','cachekey.py','repass_bands.py'],batch=4)"`
