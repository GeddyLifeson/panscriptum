# run46 — batch 16 audit

Read-and-report only. No source file was edited. `drill.py`, `mutate.py`, `allsweep.py`,
`publish.py` and `local_agent.py` were not run. No live crawl and no model call was made.

## Coverage

All eight modules read **whole**, top to bottom, no sampling — 5,573 lines.

| module | lines | read |
|---|---:|---|
| `src/local_agent.py` | 1358 | all |
| `src/binding_health.py` | 1290 | all |
| `src/completeness.py` | 813 | all |
| `src/build_terminal.py` | 668 | all |
| `src/handbuilt.py` | 517 | all |
| `src/catalogue_models.py` | 340 | all |
| `src/deprecated/catalogue_local.py` | 334 | all |
| `src/cosmology_graph.py` | 261 | all |

Recorded via `sweep_plan.record('run46', [...], batch=16)`. Confirmed afterward with
`sweep_plan.missing('run46')`: none of the eight names appear in the missing list, and
`deprecated/catalogue_local.py` — the subdirectory-path spelling — is recognised in exactly the
form it was recorded in. The coverage check can see the subdirectory module.

---

## 1. `local_agent.py` write gating

Read the whole gate chain end to end: `_safe`, `_denied_region`, `_denied_target`,
`t_propose_patch`'s three checks (name/path denylist, allowlist on both spellings, protected
regions), `_gates`' four checks (parse, pyflakes, import, verify_math), the blast-radius cap, and
the revert/escalation paths. Every one of the seven documented bypass classes (case, name prefix,
NTFS ADS, case-sensitive extension, unlisted directory, junction, allowlist-vs-resolved-path) is
closed in the code as it stands today — traced by hand rather than re-asserted from the comments,
per this sweep's own warning that a comment records what a line *used to be*.

**No new way to reach a write without passing every gate was found inside `local_agent.py`
itself.** The finding below is a different shape: the gates all fire correctly, and the *target*
they are firing on is the wrong list.

### Finding — `local_agent.DENYLIST` does not cover the one file whose entire safety is a
### textual refusal (filed RUN/MAJOR, `12c9a84b3b10`)

`src/deprecated/catalogue_local.py` is not on `local_agent.DENYLIST`, not on `DENYLIST_PATHS`,
and not under any `DENYLIST_PREFIXES` region. It IS under `WRITABLE_PREFIXES` (`src/`). Traced a
patch that deletes the file's own top-level quarantine (lines 79–94: `if -h/--help: print, exit
0; else: raise SystemExit(_REFUSAL)`) through every gate `_gates()` runs:

- **parses** — still valid Python with the block removed.
- **pyflakes** — nothing new is undefined; `_REFUSAL`'s string literal not existing is not a lint
  fault at module scope.
- **imports** — `src/deprecated/` fails `_gates`' `_in_src` test (its parent dir is not
  `HERE/src`), so the import gate loads the file via `importlib.util.spec_from_file_location`
  under the name `'_gate_probe'`, not `'__main__'` — so `if __name__ == "__main__": main()` at
  the file's own bottom never fires during the probe, and nothing downstream (the Ollama call,
  the `data/records/` write, the `SWEEP_ROLL.json` rewrite) executes to make the gate fail.
- **verify_math** — the only assertion anywhere in `verify_math.py` naming this file
  (`verify_math.py:9172`) checks that `"deprecated/catalogue_local"` is *listed* in
  `derivation.SCAN_MODULES` — a scanner-completeness check, not a check on the file's own
  content. Contrast `verify_math.py:9143–9146`, which checks a **different** deprecated-hazard
  file (`health.py`) by asserting a specific dead-branch string is *absent* from its source. The
  pattern this project already uses for "did the safety text survive" exists; it was never
  applied here.

So a patch with an innocuous `why` ("remove unreachable dead-code stub", "fix broken argument
handling") would land `applied: True`, re-enabling a module that writes
`data/records/<slug>.json` with a bare `open(path, "w")` (a third writer against the two-writer
contract `DENYLIST_PREFIXES` otherwise protects at the *data* layer, reached here through the
*code* layer instead), rewrites `data/SWEEP_ROLL.json` non-atomically inside its per-source loop,
and calls Ollama. The file's own header names this exact attack: *"somebody deleting the refusal
because six lines at the top of a deprecated file nobody reads look exactly like dead code."*
`drill.py`'s `the_deprecated_cataloguer_still_refuses` net already proves the refusal fires today
for every argv (verified independently below); nothing proves it *keeps* firing after a local-
model edit, because nothing in the gate chain looks at this file at all.

Confirmed absent by direct grep against the constant, not inferred: `catalogue_local` does not
appear anywhere in `local_agent.py`.

**Not currently exploited** — this is latent, the same status the five earlier DENYLIST gaps
(m113, m114, m121, run #25, M24) carried before they were found. It also does not fit
`DENYLIST`'s own stated rule verbatim ("the thing that detects a bad patch, or the thing doing
the patching") — `catalogue_local` is neither; it is a quarantined *hazard*, not detection
machinery. Filed with **both readings**: (1) add `catalogue_local` to `local_agent.DENYLIST`,
which is a new category the existing rule doesn't name but is the same shape of protection; or
(2) leave the denylist scoped as documented and instead add a verify_math assertion mirroring the
`health.py` pattern, which would catch removal through *any* route, not just `local_agent`'s. Per
this sweep's brief, **not** decided here — filed as a question with a concrete remedy on each
side, RUN rung because both remedies touch `local_agent.py` or `verify_math.py`, both of which sit
on `local_agent`'s own denylist and are therefore not LOCAL-rung work.

### Checked and found NOT to be defects

- **The blast-radius cap counting the wrong thing** — `_blast_ok` charges `patches`/`files` at
  the point in `t_propose_patch` right before the actual write (`:931`), after uniqueness and
  `--no-apply` are both settled, matching order 528e5b07fded's fix. Refused paths above that line
  cost no budget. Correct.
- **A revert failing while the run reports success** — traced every exit; `t_propose_patch` sets
  `reverted=False` plus an `ALARM`, `run()` collects it into `unreverted`, and `ok` is
  `not unreverted` on both the answer path and the turn-budget path. Closed.
- **`_gates` raising instead of returning a verdict** — every raise (a `subprocess.run` timeout
  included, since none of the three internal subprocess calls carry their own try/except) lands
  inside the `try` opened at `t_propose_patch:945`, so the file is reverted rather than left
  half-patched. Fails closed.
- **The empty-`find` hole (`f29382aa7911`)** — still present exactly as documented in-file
  (`original.count("") == 1` for a zero-byte target); already filed, not refiled. No zero-byte
  file sits on the writable surface today.
- **Anything calling `t_propose_patch`/`run()` outside the gated CLI** — grepped every importer
  of `local_agent` in `src/`. Only `drill.py` (test harness, pure fixtures) and `workorders.py`
  (reads `local_agent.DENYLIST` to sanity-check LOCAL-rung order targets, never calls `run()` or
  `t_propose_patch`) import it. No production dispatcher bypasses `run()`'s
  `escalation.assert_clear()` halt check.

---

## 2. `binding_health.py` — the two things the brief asked for, plus one more

**`is_quarantined` never consulted on the fetch path** — order 959b98f38a63 (OWNER, open).
Reproduced the finding rather than re-deriving it: grepped every caller of `is_quarantined` and
`quarantined()` in `src/`; neither is imported by `feats.py`'s fetch path (`feats.fetch`,
`feats.api`) at all. Confirmed still true, not refiled.

**`data/BINDING_HEALTH.json` staleness, measured**: `"at": 1787891396.79` = 2026-08-27 23:29:56,
**10.03 days old** as of this audit (2026-09-07), `checked: 134, failed: 1`.

### Finding — the one place that reads this report treats it as current with no ceiling
### (filed RUN/MAJOR, `ced15f4f9d1f`)

This is state `binding_health.py` computes and stamps honestly (`"at": time.time()` at
`:904` and `:1195`) that nothing downstream gates on. `workorders.sweep`'s binding-suspect
section (`workorders.py:1098–1195`, outside this batch but the only consumer of `BH.OUT` in
`src/`) reads `data/BINDING_HEALTH.json` whole and files/closes `BINDING_SUSPECT`,
`BINDING_RIGHT_ENTRY_NAMES_ARE_NOT_TITLES`, and `BINDING_HOST_SERVES_ANOTHER_WIKI` off it with
**no staleness check of any kind** — while the very same function, thirty lines earlier
(`workorders.py:200–259`), gates its two sibling battery artifacts
(`state/preflight_last.json`, `data/ALLSWEEP.json`) on `PREFLIGHT_MAX_AGE` /
`ALLSWEEP_MAX_AGE` and escalates a MINOR `*_STALE` fault when either is old. The data to do the
same for binding health already exists in the file; the ceiling was simply never written for
this third artifact.

It is not a transient gap either: grepped `binding_health` in `foreman.py` and `overnight.py` —
zero hits. Unlike `completeness.py` (marked `always`, refreshed every foreman round),
`binding_health.run()` has **no scheduled caller anywhere in `src/`**. It runs only when an
operator invokes `--host`/`--run` by hand. So the file can age indefinitely while
`workorders.sweep` keeps treating it as ground truth for curatorial closures — a host that
recovered, or newly went MISBOUND, since the last hand-run canary is invisible until someone
remembers to re-run it, and a stale FAIL row can keep filing (or a stale PASS row keep closing)
work orders that no longer describe the host.

This is the third artifact of this shape in the codebase and the only one without the fail-closed
staleness property Hard Rule -1 asks of every safety. Filed RUN because the fix belongs to
`workorders.py` (add a `BINDING_HEALTH_MAX_AGE` ceiling mirroring the two that already exist), and
optionally pairing it with putting `binding_health --run` on a cadence — which is an owner-level
resourcing call (a ~200-page job against hosts already IP-banned this machine once) rather than a
mechanical fix, so left as a question rather than done here.

### Checked and found NOT to be defects

- **`_BLOCKED_MARK = "refusal marker"`** — verified against `feats.page_looks_real`'s actual
  wording (not read directly this batch, but corroborated: `_probe_absent`'s own docstring quotes
  the matching phrase and this shape was independently verified by the sweep45 auditor against
  `feats.page_looks_real:251`; not re-verified live here since `feats.py` is out of this batch,
  but the string match logic in `binding_health.py` itself is internally consistent).
- **Three-valued `verdict()`** (`ok_absent is None` handled before either other test) — read the
  full truth table by hand against the four scenarios in the docstring; all four routes to the
  documented outcome.
- **`doc["failed"]` / `doc["failed_this_pass"]` top-level fields** — grepped `health.py` and
  `dashboard.py` for any read of `BH.OUT`'s summary fields: none. These two counters are
  genuinely unread by any code in `src/` today (only `workorders.py` reads `hosts`, nothing
  reads the totals). Not filed: `main()`'s own `--run` console output derives its printed
  `checked`/`failed` from the in-memory return value, not the file, so nothing is silently wrong
  — the fields are simply not yet consumed, the same "additive, nothing calls it yet" status this
  codebase accepts elsewhere (e.g. `cosmology_graph.py`'s `source_entities`, see below). Recorded
  here since the brief asked specifically for this shape; not filed as a fault because nothing
  reads a wrong answer — nothing reads an answer at all.

---

## 3. `src/deprecated/catalogue_local.py` — is it still reachable?

**No, not to do anything.** The refusal is unconditional, top-level, module-scope code
(`:91–94`), executed before `sys.path.insert`, before `import yaml`, before `HERE`/`ROLL`/
`RECORDS` are even defined, and before any function (including `main()`) exists to be called:

```
if set(sys.argv[1:]) & {"-h", "--help"}:
    print(_REFUSAL); raise SystemExit(0)
raise SystemExit(_REFUSAL)
```

Traced every route in, not just the documented one:

- **Run as a script**, any argv except `-h`/`--help` (including no argv, `--dry-run`,
  `--limit 3`, `--only Bleach`) → hits `raise SystemExit(_REFUSAL)` at line 94 before any I/O,
  any network call, or any write. `drill.py`'s own `the_deprecated_cataloguer_still_refuses` net
  already exercises exactly these four argv shapes plus checks the message lands on **stderr**
  specifically (not merely printed) and that `--help` exits **0** on **stdout** — read that net in
  full and it is correctly discriminating; not re-run live (per this audit's constraints).
- **`--help`** → prints the notice, exits 0, touches nothing. The one deliberate exemption, and
  it exists only so `allsweep.check_import`'s subprocess-based `--help` sweep doesn't file a false
  BROKEN IMPORT order against a module refusing exactly as designed.
- **In-process `import catalogue_local`** — the same unconditional top-level code would fire
  during the import statement itself, raising `SystemExit` into the importer. Grepped every
  reference to `catalogue_local` across `src/` (23 hits): every single one is either a comment, a
  string constant compared by `drill.py`/`liveness.py`/`sweep_plan.py`/`derivation.py`, or
  `drill.py`'s own **subprocess** invocation (`subprocess.run([sys.executable, mod, ...])`,
  `:4454-4458`) — never a bare `import catalogue_local`. Nothing in this tree would be taken down
  by the in-process case; it simply never happens.
- **`allsweep`'s import tier** — also subprocess-based (`subprocess.run([PY, path, "--help"])`,
  `allsweep.py:316`), so it only ever exercises the safe exemption.

So the module is visible to the scanners as of today (order f42c55355431, `sweep_plan.py:42-71`
walking subdirectories) but reachable only as an inert refusal through every path this tree
actually uses. The one way it stops being inert is the gate gap in §1 above — filed there, not
here, since the defect is in `local_agent.py`'s coverage, not in this file's own logic, which is
sound.

---

## 4. `completeness.py`, `catalogue_models.py`, `build_terminal.py`, `handbuilt.py`,
##    `cosmology_graph.py` — read whole, no new findings

All five are heavily self-documented with prior fixes (discarded-write-verdict gating, Hard
Rule 0 truncation removals, atomic temp-name writes) that were spot-checked against the live code
rather than trusted from the comments, and all checked out as described:

- **`completeness.py`** — `land()`'s three-outcome return (`True`/`False`/`SKIPPED_ONLY`) is
  correctly distinguished at both call sites; the shrink floor and the atomic write both gate on
  the real `write_json` verdict.
- **`catalogue_models.py`** — `LAST_WRITE_LANDED`'s three-state contract (`None`/`False`/`True`)
  is read correctly by `main()`; `EMPTY_LIST` is folded into `live`/`verified` on outcome, not
  truthiness, at every site that matters.
- **`build_terminal.py`** — every catalogue-derived string reaching the generated page's
  `innerHTML` passes through `esc()`. Checked the one live field that looked exempt,
  `w.s` (the Azgaar seed): traced its origin to `navtree.py:52` → `address_space.map_seed()`,
  which returns `int(hashlib.sha256(...).hexdigest()[:8], 16)` — always an integer, never
  attacker-shaped text, so its two unescaped interpolations (the URL query string and the panel's
  `seed ${w.s}`) are safe as written. Not a finding.
- **`handbuilt.py`** — pure data plus a small `compute()`/`main()`; the sentinel-score handling
  (`"unestimable"` bypassing `%5.1f`) and the atomic write ordering (write before the
  Fraktur-character console print that used to crash first) both hold.
- **`cosmology_graph.py`** — the IDF weight formula matches its own docstring exactly
  (`1/log(n+1.5)`, `×0.15` past `UBIQUITOUS_CUTOFF`); the write path is unfiltered and atomic as
  claimed. One loose end, not filed: `src_entities` is computed by `build_graph()` on **every**
  run but only reaches the written artifact under `--write` — a plain console report (no
  `--write`) computes it and prints nothing from it. Cosmetic (the persisted artifact, which is
  what `propagation.py`/`resonance.py` actually read, carries it correctly); not worth a queue
  entry.

---

## Filed this batch

| id | handler | sev | subject |
|---|---|---|---|
| `12c9a84b3b10` | RUN | MAJOR | `local_agent.DENYLIST` omits `catalogue_local` — its own quarantine refusal is patchable through every gate |
| `ced15f4f9d1f` | RUN | MAJOR | `workorders.sweep`'s binding-suspect section reads `BINDING_HEALTH.json` (10 days stale, no scheduled refresh) with no staleness ceiling, unlike its two siblings |

Corroborated, already open, not refiled: `959b98f38a63` (OWNER — `is_quarantined` never consulted
on the fetch path).
