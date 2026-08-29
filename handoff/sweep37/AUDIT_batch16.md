# SWEEP 37 — BATCH 16 AUDIT

Modules read **in full**, every line, no skimming (3,967 lines total):

| module | lines |
|---|---|
| `src/local_agent.py` | 934 |
| `src/rigor.py` | 908 |
| `src/derivation.py` | 590 |
| `src/codewatch.py` | 476 |
| `src/canon_backup.py` | 330 |
| `src/cosmography.py` | 282 |
| `src/cosmology_graph.py` | 244 |
| `src/chord_field.py` | 203 |

Everything below is verified against source. Where a fault could be demonstrated, it was —
offline, on a COPY in a temp directory, never against the live tree, never running
`local_agent` here, never starting/stopping/killing anything. `python src/codewatch.py`,
`python src/rigor.py`, `python src/derivation.py` and read-only `cosmography` / `cosmology_graph`
imports were run as permitted. No source file was edited.

Citations are by SYMBOL, not by line number, per the standing idiom.

---

## MAJOR

### M-1. `local_agent._safe` — the junction re-check asks only about protected *regions*, never about the protected *path*. `config.yaml` is writable through a junction.

**Where:** `src/local_agent.py`, `_safe` (the run #35 junction block) and `_denied_region`.

**What is wrong.** `t_propose_patch` refuses a path three ways: the module `DENYLIST` (keyed on
basename), `DENYLIST_PATHS` (keyed on the repo-relative path, and it holds exactly one entry —
`config.yaml`), and `DENYLIST_PREFIXES` (keyed on a region prefix). The junction fix added a
second decision on the **resolved** path, and that second decision calls `_denied_region`, which
consults `DENYLIST_PREFIXES` **and nothing else**. `_denied_region`'s own docstring says it
exists "so the junction check above can ask the SAME question of a resolved path that
`t_propose_patch` asks of the written one" — but `t_propose_patch` asks three questions and
`_denied_region` answers one.

So a directory junction placed anywhere on the writable surface (`src/`, `prompts/`, `handoff/`)
and pointing at the project root makes `config.yaml` reachable as, e.g.,
`handoff/cfg/config.yaml`. The path *as written* is not `config.yaml`, so `DENYLIST_PATHS` never
matches; the allowlist passes because it starts with `handoff/`; no protected-region prefix
matches either spelling; and `_safe` returns the path.

**Demonstrated end to end** on a temp copy of `local_agent.py` + `silence.py` in a miniature
project (`%TEMP%\la_probe`), with a real YAML parse gate and a real whole-suite gate:

```
A. handoff/cfg/config.yaml   (junction handoff/cfg -> project root)
   _safe()   : ...\la_probe\handoff\cfg\config.yaml
   realpath  : ...\la_probe\config.yaml
   _denied_region(as written) : False
   _denied_region(resolved)   : False
   t_propose_patch -> {'applied': True, 'why': 'probe'}
   config.yaml on disk now: ... | prose_enabled: TAMPERED | step4_enabled: false |
```

**Why it matters, and why no second layer catches it.** This is the file the module's own
comment names as the reason `DENYLIST_PATHS` exists ("`config.yaml` holds the prose gate ... one
bad edit misroutes the whole pipeline, and unlike a broken `.py` it fails silently"). The two
owner-held flags live there, and neither is protected by the gates that remain:

* `verify_math` asserts only *"the prose flag is a BOOLEAN in config, not a string"* —
  `isinstance(_raw_cfg.get("prose_enabled"), bool)`. It never asserts the **value**. So
  `prose_enabled: true` is a boolean and passes.
* `step4_enabled` is read by `prose_gate.step4_gate_open` and asserted **nowhere** in
  `verify_math`. Grep across `src/*.py` finds it in `drill.py` (synthetic fixtures) and
  `prose_gate.py` only.

So a patch through a junction setting either flag true clears the YAML parse gate and the
whole-suite gate and lands. That is HARD RULE -1's "a decision must be RELOCATED, never removed"
being undone by a path-string mismatch.

**Standing today.** Latent, not live: `dir /AL /S src prompts handoff` reports no reparse points
on the writable surface, and `local_agent`'s six tools cannot create one. That is exactly the
standing every one of the five previously documented bypasses had when it was found, and this
file already says so about itself ("Not reachable against any file on the writable surface
today ... which is exactly the condition under which the previous four bypasses were also 'not
currently exploitable'").

**Confidence: HIGH** — reproduced.

---

### M-2. `codewatch.stale()` — the settle window is effectively **one caller poll interval**, not `STABLE_SECONDS`.

**Where:** `src/codewatch.py`, `stale` (`_PENDING` handling) and `STABLE_SECONDS`.

This refines the standing order **ff3c67a67b92** rather than restating it. That order's finding
is "a maintenance run rewrites `src/` for hours, so the fingerprint never settles". The
mechanism is sharper than that, and the sharper reading changes the remedy.

`stale()` compares the current digest against `_PENDING["digest"]` — **the digest seen at the
previous poll**, not against wall-clock stability. Any poll where the digest differs from the
previous poll resets `first_seen`. So the guard is not "the tree held still for 180 seconds"; it
is "**two consecutive polls saw the same digest, at least 180 seconds apart**". Its effective
window is `max(STABLE_SECONDS, poll_interval)`, and `STABLE_SECONDS = 180` is inert for every
real caller: `foreman --loop 30` polls every 30 minutes, `overwatch --loop 20` every 20.

A genuine 25-minute lull inside a 30-minute poll gap is invisible: the next poll still sees a
digest different from the one 30 minutes earlier, resets the clock, and reports "changed,
settling" — a reason string that reads as transient while describing a permanent state. Nothing
escalates, because the budget/ledger escalations in `exit_if_stale` only fire once a restart has
been *claimed and refused*.

**Demonstrated** (scripted digests and a scripted clock, entirely inside a probe process; no
file, daemon or process touched):

```
CASE 1 -- foreman-shaped: --loop 30 (1800 s between polls), src/ edited between polls
   poll  1  t+ 0.5 h  ->  stale=False  changed, settling
   ...
   poll 12  t+ 6.0 h  ->  stale=False  changed, settling
CASE 2 -- same poller, tree now holds still
   poll 13  t+ 6.5 h  ->  stale=True   src/ changed AAAA -> E012 and held for 1800s
```

Six hours of running stale code, no restart, no escalation.

**Live corroboration, tonight.** `state/CODEWATCH.json` holds exactly one restart for `foreman`
(08-28 15:00) and one for `overwatch` (08-28 15:06). Both processes are still those instances —
`foreman.py --go --patch --loop 30` (pid 36264) has been up 8.6 h, `overwatch.py --loop 20`
(pid 36564) 8.5 h — while `src/` has been rewritten repeatedly all evening (newest `.py` mtime
23:13, 28 minutes before this audit). Every fix landed in this sweep, including today's
`codewatch._take_locked` fail-closed change and `local_agent`'s blast-charge move, is inert in
both of them.

**The remedy this reading suggests**, and which ff3c67a67b92's `owner_options` does not list:
fingerprint on a cadence independent of the daemon's work cycle (a `listdir` + `sha256` of
`src/` is cheap), so a real 180-second lull is actually *observed*. Quiescing the publisher and
accepting shift-long staleness both treat the symptom.

**Confidence: HIGH** — mechanism demonstrated; live state consistent.

---

### M-3. Four of the longest-lived jobs running right now do not check their own source at all, and the drill net that is supposed to guarantee they do enumerates three filenames.

**Where:** `src/codewatch.py` module docstring ("every standing daemon") vs. the callers;
`src/drill.py`, `drill_codewatch.daemons_actually_check_their_own_source`.

`codewatch.stamp` / `codewatch.exit_if_stale` call sites across `src/`:

| module | call sites | running now | up for |
|---|---|---|---|
| `publish.py` | 2 | (not resident) | — |
| `foreman.py` | 2 | pid 36264 | 8.6 h |
| `overwatch.py` | 2 | pid 36564 | 8.5 h |
| **`read.py`** | **0** | pid 13832 `--run --workers auto` | **12.1 h** |
| **`feats.py`** | **0** | pid 16752 `--roll --workers 12` (the live crawl) | **12.1 h** |
| **`dashboard.py`** | **0** | pid 27836 `--port 8777` | **12.3 h** |
| **`autostart.py`** | **0** | pid 35168 `--watch` (the watchdog) | **3.0 h** |
| `hostcheck.py` | 0 | pid 7280 | 0.1 h |
| `magnitude.py` | 0 | pid 25392 | 0.1 h |

`autostart.py` imports `codewatch` only for `twins()`; it never stamps and never exits stale.
So the watchdog that keeps everything else honest about its own code is itself a twelve-hour
photograph — and `dashboard.py`, which serves the picture a person reads, is another.

The drill net named *"every standing daemon checks whether its own source has changed"* is:

```python
for f in ("publish.py", "foreman.py", "overwatch.py"):
```

A hardcoded roster of three. Its title promises "every"; its body enumerates three; a daemon
added tomorrow is never noticed, and six standing loops are outside it today. This is the exact
"MEASURED, NOT MAINTAINED" shape that `derivation.SCAN_MODULES` was corrected for in run #35
batch 6 — a hand-typed list standing in for the real population, which "does not fail, it
returns a smaller universe wearing the same shape as the real one".

**Confidence: HIGH** — grep counts and the live process table.

---

## MINOR

### m-1. `canon_backup.prune` records a deletion it did not perform.

`prune`'s `except OSError:` branch calls `silence.note("canon_backup.py:prune-denied:...")` and
then falls through to `removed.append(f)` unconditionally. A denied delete — the ordinary case
on this machine when the dashboard or a reader holds a file open — is reported as a removal, and
`main()` prints `"pruned %d old snapshot(s): %s"` naming files that are still on disk. A
discarded write verdict in the module whose whole subject is not trusting a write it has not
confirmed. **Confidence: HIGH** (read from source; the failure branch is unambiguous).

### m-2. `canon_backup.verify` returns `ok=True` when there is no manifest to verify against.

`snapshot()` was corrected (run #36) to raise when the manifest write is denied, and the comment
there names the consequence exactly: *"Without the manifest `verify()` has no recorded digests to
compare against, so it silently degrades to 'the zip still opens'."* The read side was not
corrected. Demonstrated against a hand-built manifest-less archive:

```
verify(no manifest) -> ok=True
   archive intact, 0 members
   0 canonical files changed since the snapshot
   219 canonical files are new since the snapshot
```

`main()` prints `VERIFY: ok` and returns 0. "0 canonical files changed" is a comparison against
nothing, reported as a pass — the module's own stated hazard. Any snapshot whose manifest was
deleted (including by `prune`, which removes the two together, or by m-1's silent failure
leaving one of the pair behind) verifies clean. **Confidence: HIGH** — reproduced.

### m-3. `derivation.check_graph` never validates `kind`.

The docstring says a quantity may stand on "exactly four things, and the taxonomy is the point.
... Anything else is a violation. The checker below enforces it two ways." It does not. A
quantity with `kind="DERIVE"` (a typo), an empty `source` and no parents produces **zero**
problems, because it is not `DERIVED` so the ROOTLESS rule skips it and not `OWNER` so the
UNSIGNED rule skips it:

```
after adding kind='DERIVE' (typo), source='', no parents:
check_graph() -> []
```

Related: `UNSIGNED` is structurally near-unreachable, since every entry is built through
`Q(kind, source, ...)` where `source` is a required positional — it can only fire for a
deliberately empty string. The live ledger is clean (`kinds present: CHARTER, DERIVED, MEASURED,
OWNER`; `check_graph() -> []`), so this is a gap in the checker, not a defect in the data.
**Confidence: HIGH** — reproduced.

### m-4. `derivation.scan_constants` misses tuple-target and annotated constants — including its own.

`scan_constants` handles `ast.Assign` with `getattr(node.targets[0], "id", None)` only. A tuple
target yields `ast.Tuple` (no `.id`) and an annotated assignment is `ast.AnnAssign`, which is not
matched at all. Its docstring claims module-level uppercase assignments are "the only place a new
constant can hide"; the scan cannot see two of the three ways to write one. Demonstrated on
`derivation.py` itself, whose `MEASURED, CHARTER, OWNER, DERIVED = "MEASURED", ...` is invisible
to it:

```
constants scan_constants sees in derivation.py: ['HERE', 'LEDGER', 'SCAN_MODULES']
MEASURED/CHARTER/OWNER/DERIVED seen by the scan? []
```

**Confidence: HIGH** — reproduced.

### m-5. `local_agent._gates`' import gate checks a *different file* for any `.py` outside `src/`.

`modname` is `os.path.basename(full)[:-3]`, and the import gate runs
`sys.path.insert(0, HERE/src); import <modname>`. The writable surface includes `prompts/` and
`handoff/`, so a `.py` there whose basename matches an importable `src` module has its import
gate satisfied by the `src` module — a file that was never patched. Demonstrated: a temp
`handoff/harmless.py` was patched to `import nosuchmodule_zzz_does_not_exist` and returned
`{'applied': True}`, because `src/harmless.py` imported fine. The module docstring's promise
("the module still imports") is false for that file. Impact is bounded — nothing imports
`handoff/` or `prompts/`, and they hold no `.py` today — but this is a gate that checks the
wrong object, which is a check that cannot fail.
**Confidence: HIGH** — reproduced.

### m-6. `local_agent.t_run_check` overstates two things to the model.

* The tool description the model reads says `'compile' (does a file parse and import)`. The
  implementation runs `py_compile.compile(..., doraise=True)` and prints `parses OK`. It never
  imports. A model that "tested" importability with this tool tested nothing of the sort.
* The docstring says *"Read-only by construction: none of the four writes to the tree."*
  `py_compile.compile` writes bytecode. Verified: running the exact argv on a scratch file
  created `__pycache__/zzprobe.cpython-313.pyc` beside it. The claim is false as written; the
  write is harmless, the claim is the defect.

**Confidence: HIGH** — reproduced.

### m-7. `cosmography.kardashev_to_magnitude` cannot report "below the ladder".

`reached = ladder[0]` before the loop, and the loop only ever raises it. A civilisation whose
annual budget is below the M0 Ruin edge is reported as reaching M0. Verified against the live
`assay` tables: the lowest Ruin edge is 100 J, and `kardashev_to_magnitude(1e-30)` — 3.156e-23
J/yr, twenty-five orders of magnitude short — returns `'M0'`. The docstring says the function
"returns the band its budget REACHES", which for this input it does not. Return `None` (the
convention `kardashev_K` already uses for `watts <= 0`) or name the below-M0 case.
**Confidence: HIGH** — reproduced.

### m-8. `cosmography.SIZE_CLASSES["POCKET"]` — the declared meaning and the arithmetic disagree, and `validate()` cannot notice.

`POCKET` is documented as *"a closed loop, a demiplane, one stage and no sky"* and implemented as
a `1e-9` multiplier on a standard universe. Computed:

```
POCKET   galaxies=2.000e+02  stars=2.000e+10  extant civs=1.200e+06  TypeIII=1.200e+01
MINOR    galaxies=2.000e+05  stars=2.000e+13  extant civs=1.200e+09  TypeIII=1.200e+04
STANDARD galaxies=2.000e+11  stars=2.000e+19  extant civs=1.200e+15  TypeIII=1.200e+10
```

A demiplane with no sky containing two hundred galaxies and twelve galaxy-spanning empires.
`validate()` passes it, because every one of its ceilings is a ratio inside the same scaled
census and all of them scale together — the check is structurally unable to see a size class
whose *category* is wrong rather than whose *proportions* are. This is the same shape as the
2026-08-20 Type III correction the module records, one level up. `MINOR` ("a single galaxy's
worth, walled") computes 200,000 galaxies and has the same problem.
**Confidence: MEDIUM-HIGH** — the arithmetic is certain; whether the prose or the multiplier is
the thing to change is an owner call.

### m-9. `chord_field`: two dead constants, and a ledger note that does not match the data.

`G_NEWTON` and `HBAR` are assigned and referenced **zero** times (`C_LIGHT` once, in
`recoil_momentum`; `K_BOLTZMANN` once, in `landauer_floor`). They are hand-copied duplicates of
the ledger's `G` and `hbar`, which is the precise failure `derivation.py`'s own header exists to
prevent, and `tempus.py` already names this file in a comment about "a fourth hand-copied
instance of quantities already declared in cosmography.py, chord_field.py".

Separately, `derivation.LEDGER["beta_constants"]` reads *"X.9: the six adjudication costs, 8 to
128 bits"*. `chord_field.ADJUDICATIONS` carries six costs of `[64, 96, 8, 0, 128, 32]` — A4's is
**0**, outside the stated range. `rigor.main()`'s MDL audit table audits five of the six and
omits A4 entirely, so the one value contradicting the ledger is also the one never priced.
(A4's `must_declare` is "Nothing", so 0 may well be right; the *range* is what has drifted.)

The wider fact — `chord_field` is imported by nothing and all six of its functions are dead — is
already filed as **7e360eaec3a6**; not re-filed.
**Confidence: HIGH** on the counts, MEDIUM on the ledger-note reading.

### m-10. `local_agent`: no per-turn tool-call limit, despite the comment citing one.

The blast-cap comment says the bound is "borrowed from Strix's per-turn tool-call limiter". No
per-turn limit exists. `tool_calls_seen` is incremented in `run()`'s dispatch loop, reported in
the result and never compared to anything. A model can issue unbounded tool calls inside each of
`MAX_TURNS = 24` turns; with the (correct — see H-1) charge point, refused patches cost no
budget, so the only bound on a non-writing runaway is 24 model round-trips. Low severity — no
refused call changes the repo — but the comment describes a limiter the file does not have.
**Confidence: HIGH**.

### m-11. `rigor`: a non-positive ratio matrix silently produces NaN.

`logrank_weights` does `F = np.log(A)` and `perron_weights` eigendecomposes `A` with no check
that `A` is positive and reciprocal, which `theorem_1_check`'s own preamble states as the
hypothesis ("For a positive reciprocal matrix A (A_ij > 0, A_ji = 1/A_ij)"). A zero or negative
entry yields `-inf`/`nan` weights, `eta` = nan, and `coherent`/`both_say_consistent` come back
`False` via `bool(nan < x)` — so it fails closed on the flags but hands back NaN numbers without
saying the input was inadmissible. **Confidence: HIGH** on the mechanism; no live caller feeds it
such a matrix (`main()` uses `consistent_matrix(A.WEIGHTS)` and a hand-written positive 3x3).

### m-12. `codewatch` cosmetics worth one line each.

* `runs_script`'s fallback return reads
  `... == <20 spaces> os.path.normcase(...)` on one physical line. Verified with `cat -A`: no
  backslash, no control character — it is valid Python and behaves correctly. It is, however,
  the exact residue an eaten `\`-continuation leaves, and `codewatch.py` is one of the few
  modules here **without** the `_BAD_CHARS` self-check that `rigor.py` and `local_agent.py`
  carry at import. Worth adding the check rather than editing the line.
* `stamp(who="?")` ignores `who` entirely.

**Confidence: HIGH**.

---

## Order-store observations (not code defects)

* **`f883d9bb534e` is fixed but still open, and its citation has drifted.** It describes
  `codewatch.py:109 twins()` doing `me = os.getpid() if exclude_pid is None else exclude_pid`.
  That code no longer exists: `twins` now does `skip = {os.getpid()}` and then
  `skip.add(exclude_pid)` — additive, which is exactly the remedy the order asked for, and the
  docstring above it records the run #34 fix. The symbol is also no longer at line 109. Both
  halves are the fault classes this sweep hunts (a stale verdict, and a citation by line number).
* **`7e360eaec3a6`'s evidence has drifted the same way.** It proves its point by quoting
  `derivation.py:477: SCAN_MODULES = ["assay", "feats", ...]` — a hand-typed list that was
  replaced in run #35 batch 6 by `SCAN_MODULES = sorted(f[:-3] for f in os.listdir(HERE) ...)`.
  The order's *conclusion* still holds (`chord_field` is still imported by nothing); its proof no
  longer describes the file.

---

## HEALTHY — verified, not assumed

**H-1. The blast-radius charge point (order 528e5b07fded) is right where it now is.** I was asked
to judge this fresh and I find no argument against it. The cap's stated job is "a hard limit on
how much one invocation may CHANGE". `_blast_ok` is called immediately before the sole write in
the module (the `open(full, "w")` inside `t_propose_patch`'s `try`), which is the only point at
which what is being counted is a change. There is **no path that writes without charging** —
one write site, one charge site, charge first — and the charge stands if the write raises, which
is correct, because a raised write may still have altered the file. Billing a non-unique `find`
string or a `--no-apply` staged patch was billing refusals, and the drill's `blast_cap_bites` net
was demonstrating the cap through precisely the path that is not a change; the net was the thing
that was wrong. The cap itself remains reachable: 24 real patches or 8 distinct real files.

**H-2. The failed-revert ALARM now reaches both exits.** `t_propose_patch` raises a SAFETY
escalation plus `silence.note("local_agent.py:REVERT-FAILED:...")`, `run()` collects it in
`unreverted`, and **both** terminal paths surface it — the no-tool-calls return and the
turn-budget-exhausted return (order d185007c4b8b). `ok` is `not unreverted` on the first and
already `False` on the second, so `main()`'s `0 if out.get("ok") else 1` cannot report success
over a half-written module.

**H-3. `codewatch._take_locked` fails closed on a denied ledger write (order f06ba4c82363), and
`exit_if_stale` tells the two refusals apart correctly.** The discrimination is not cosmetic and
it is sound: the `enforce` branch returns early whenever `len(recent) >= BUDGET_PER_HOUR`, so
the denied-write branch is only reachable with `used_before < BUDGET_PER_HOUR`, which is exactly
when `spent` evaluates False. `CODEWATCH_BUDGET` and `CODEWATCH_LEDGER_DENIED` cannot be
transposed.

**H-4. `_claim_restart_slot` is one locked check-and-take**, not a check and a separate take
(the run #36 fix holds), and `_ledger_lock`'s deliberate proceed-unlocked fallback still leaves
`_take_locked`'s write-must-land requirement in force.

**H-5. `rc=17` is named in words where it is read.** `overnight.name_rc` returns
`"rc=17 (ON PURPOSE — source changed, restarting to run the current code)"`.

**H-6. The junction re-check DOES hold for protected regions.** Probe C:
`handoff/cfg/data/records/zz.json` through a junction returned `_safe() -> None`. The run #35 fix
works for `DENYLIST_PREFIXES`; M-1 is the one question it forgot to re-ask.

**H-7. The module denylist is keyed on basename and is therefore directory-independent.** Probe
B: `handoff/cfg/src/verify_math.py` through a junction was refused with *"verify_math is on the
denylist -- the checking machinery may not edit itself"*. The checking machinery cannot be
reached around by re-spelling its directory.

**H-8. `_settle` is on every return path of `t_propose_patch`.** Every `return` in the function
is `return _settle(...)`, so refusals as well as applications land in the audit trail, and
`_achievement` reads outcomes back rather than counting intents.

**H-9. `local_agent.run` asserts the halt before doing anything** (`escalation.assert_clear`,
raised not swallowed), and `blast_reset()` gives each invocation a fresh budget.

**H-10. `_gates` reads the verify_math result as a NUMBER** (`RESULT:\s*\d+\s+passed,\s*(\d+)\s+
FAILED`) and refuses when the line is absent, so "10 FAILED" cannot be read as "0 FAILED" and a
crashed verifier is a refusal.

**H-11. `_gates` refuses when pyflakes could not run** (`returncode not in (0, 1)`, or a stderr
carrying `No module named` / `Traceback`) rather than reading empty stdout as "no undefined
names".

**H-12. `canon_backup` refuses rather than shrinks.** `members(strict=True)` raises when any
declared canonical path is missing; `snapshot()` reopens the archive it just wrote and re-hashes
every member against its source, deletes the archive on any mismatch, and checks the verdict of
**both** `replace_retry` calls (archive and manifest). `newest()`/`prune()` order by name, which
is the timestamp, not by mtime. 219 canonical files, uncapped.

**H-13. `cosmology_graph` writes everything and gates its write.** Every pair that shares at
least one entity is emitted, `shared_sample` is the whole list, `threshold` is labelled
`threshold_applies_to: "clusters"`, `silence.write_json`'s verdict is read, a denied replace
prints an explicit WRITE DENIED banner saying the counts describe memory and not disk, and
`main()` returns 1. The console `--show`/`[:4]`/`[:6]` slices all print an explicit "+N more"
and name themselves as screen framing — consistent with the house rule that ranked *returned*
fields stay whole while *displays* may slice. (Already filed as 47c8def059e3; not re-filed.)

**H-14. `derivation`'s ledger closes and its scan is measured, not maintained.**
`check_graph()` returns `[]` on the live ledger; `SCAN_MODULES` is derived from `os.listdir` and
covered 113 modules in this run's output; `_address_total_bits` reads
`address_space.TOTAL_BITS` instead of restating it and degrades to a sentence rather than a
stale number.

**H-15. `rigor` runs clean and its verdicts are derived from their own evidence.** Both
`FINDING:` branches (`_muted`, `_underpriced`) are guarded on the loop's own result rather than
printed unconditionally; the Perron/logrank distinction and the CR-vs-curl-fraction precision are
stated correctly; `bradley_terry` checks Ford's condition on the **raw** wins and computes
`undefeated`/`winless` from `observed` rather than the prior-augmented matrix, so a prior cannot
empty those lists; `prob_at_least_one` integrates rather than point-estimates and reproduces the
Sandberg/Drexler/Ord result (`P(WE ARE ALONE) = 0.3331` on the Milky Way chain);
`mathematical_resonance` returns `load_bearing` whole and lets the consumer slice.

**H-16. `cosmography.validate` genuinely refuses.** `census()` raises `ValueError` on an
invalid census rather than returning it, and the Type III ceiling it enforces is the one the
2026-08-20 correction was written for. (See m-8 for what it structurally cannot see.)

**H-17. `KEEP = 7` in `canon_backup` was considered against HARD RULE 0 and is not a violation.**
It is a retention policy for *derived second copies*, declared with its horizon ("~8 days of
history at this cadence"), and `--keep 0` disables pruning entirely. Nothing in a served listing
is truncated by it. Likewise the `SLICE`/`output_tail` windows in `local_agent` are labelled as
windows with the remainder reported, which is the documented distinction between a window and a
cap.

---

## Counts

* MAJOR: **3**
* MINOR: **12**
* Order-store observations: **2**
* Healthy properties verified: **17**

No caps applied to any count above. Where something was found N times, N is written.

---

## Orders filed (found_by `sweep37-batch16`)

| id | severity | code |
|---|---|---|
| `6e0127c4f3ed` | MAJOR | `LOCAL_AGENT_JUNCTION_DENYLIST_PATHS` (M-1) |
| `838be29f9e58` | MAJOR | `CODEWATCH_SETTLE_IS_ONE_POLL_INTERVAL` (M-2, refines `ff3c67a67b92`) |
| `1f172f5acc6f` | MAJOR | `CODEWATCH_UNCOVERED_STANDING_JOBS` (M-3) |
| `4965e049c8fb` | MINOR | `CANON_BACKUP_PRUNE_DISCARDS_DELETE_VERDICT` (m-1) |
| `b6d5f70a7f19` | MINOR | `CANON_BACKUP_VERIFY_OK_WITHOUT_MANIFEST` (m-2) |
| `72bc85d74ccf` | MINOR | `DERIVATION_CHECKER_CANNOT_SEE_TWO_THINGS` (m-3, m-4) |
| `deeb24037ede` | MINOR | `LOCAL_AGENT_GATES_CHECK_WRONG_FILE_AND_OVERSTATE` (m-5, m-6) |
| `be783948fd66` | MINOR | `COSMOGRAPHY_BAND_FLOOR_AND_SIZE_CLASS` (m-7, m-8) |
| `08c1b6828384` | MINOR | `CHORD_FIELD_DEAD_CONSTANTS_AND_BETA_RANGE` (m-9) |
| `abd06525b40b` | MINOR | `WORKORDER_f883d9bb534e_IS_FIXED_AND_STILL_OPEN` |

Not re-filed, deliberately: `ff3c67a67b92` (settle window — refined above instead),
`7e360eaec3a6` (chord_field dead — its drifted proof is noted inside `08c1b6828384`),
`47c8def059e3` (cosmology_graph console slices — verified as honest display framing),
`f883d9bb534e` (superseded by the observation above rather than duplicated).

m-10 (no per-turn tool-call limit), m-11 (NaN on a non-positive ratio matrix) and m-12
(`codewatch` cosmetics) were judged too small for the queue and are recorded here only.

Coverage recorded: `sweep_plan.record('run37', [...8 modules...], batch=16)` — all eight
now read `{'run': 'run37'}`.
