# sweep65 batch 02 — AUDIT

Scope: `src/verify_math.py` (13,413 lines, the full file). Read sequentially from line 1 to line
13,413 in ~700-800 line chunks via the Read tool, no sampling, no grep-driven skimming. This is a
full independent read, not a diff against a prior sweep's report.

## Method

- Read-only throughout. Nothing under `src/`, `data/`, `state/`, `output/`, `prompts/` or
  `reference/` was edited, created or deleted. The only writes this session made are this report
  file and the `sweep_plan.record()` call at the end.
- Nothing was executed against the live repository. The only executions were: (1) a scratch
  reproduction of one finding, run entirely under `%TEMP%` against a throwaway 8-line script that
  imports nothing from this repo, and (2) `grep`/`python -c` read-only inspections of
  `state/workorders.json`. `verify_math.py`, `drill.py`, `generate.py`, `pipeline.py` and no other
  job/mutate/publish/crawl/overwatch/foreman action was run.
- No subagents were spawned.
- Consulted `handoff/sweep64/AUDIT_batch02.md` (and confirmed sweep63/sweep61 both cover this
  exact module with the same 0/0 verdict) only after finishing my own read, and only to decide
  whether a candidate finding was already filed. I did not find my finding mentioned in any of the
  three prior reports, and confirmed via `state/workorders.json` that no open order names it
  (searched for "bare assert", "python -O", "WIKI_OVERRIDES", the line number, and generally for
  any workorder whose text mentions `verify_math.py` — none match this finding).

## What this file is

Unchanged from the prior three audits' description: the project's largest self-auditing
regression battery, ~1,050+ `check()` calls across numbered sections §1–§20ae plus the splice of
six standalone `run35` batch files (§20s/§20u), each check paired with positive and negative
controls per this file's own house doctrine (order 873330d2e98d and others).

## Findings

### MINOR, CONFIRMED — `verify_math.py:11140`, a bare `assert` in the one file whose job is to catch this exact pattern

**Evidence.** Inside `_b5_wiki_source_nonfandom_shortcircuit()` (batch5 splice, "order
e86eec8ac173 -- belongs in verify_math.py, target src/wiki_source.py"):

```python
11134  def _b5_wiki_source_nonfandom_shortcircuit():
11135      import json as _json_b5
11136      import wiki_source as WS
11137      d = _mkdtemp_vm()          # tracked, so the scratch dir is swept at exit
11138      hosts_path = _os_b5.path.join(d, "WIKI_HOSTS.json")
11139      source_name = "Zzz Test Source Not In Overrides"
11140      assert source_name not in WS.WIKI_OVERRIDES
11141      with open(hosts_path, "w", encoding="utf-8") as f:
```

`grep -n "^\s*assert " src/verify_math.py` across the whole 13,413-line file returns exactly this
one line — every other precondition/assertion in the file goes through `check()`, a raised
exception caught by `_raises()`, or an explicit `raise`.

**Why it is a real defect and not a stylistic nit.** This codebase has independently found and
fixed the identical defect shape three times elsewhere, and states the doctrine explicitly:

- `src/entity_match.py:199` — "RAISED, NOT `assert`ed (sweep57 question bundle bf1340bc3b3f):
  `python -O` strips assertions, ..."
- `src/scale_theories.py:205` — "`assert`ed, because `python -O` strips assertions and this is
  the guarantee the callers of..."
- `src/tiers.py:165` — "RAISED, NOT `assert`ed (order 5d0fa30e4b09, item 4). `python -O` strips
  assertions, and these..."
- `src/drill.py:7736,7753,18332,18645` — carries nets that explicitly verify invariants still hold
  "under `python -O`", citing "order 5d0fa30e4b09 item 4: python -O strips assert, so a CUTS edit
  that broke nesting..."

So "a bare `assert` silently disappears under `python -O`" is a named, previously-repaired defect
class in this exact codebase — and the one file whose stated purpose is to catch exactly this
shape of defect (silent no-ops, guards that cannot fail, checks satisfied by an accident of
configuration) contains one un-exempted instance of it, missed by three prior full reads of this
same file (sweep61, sweep63, sweep64 batch02, all reporting 0/0).

**Failure scenario, reproduced by execution in a scratch copy outside the repo**
(`%TEMP%\vm_scratch_check\probe.py`, no repo imports):

```python
WIKI_OVERRIDES = {}
source_name = "Zzz Test Source Not In Overrides"
assert source_name not in WIKI_OVERRIDES
WIKI_OVERRIDES[source_name] = "somehost.fandom.com"   # the precondition is now violated
assert source_name not in WIKI_OVERRIDES              # must catch it
print("silently proceeded past a violated precondition")
```

- Plain `C:/Users/imarl/miniconda3/python.exe probe.py` → raises `AssertionError` at the second
  assert, exit code 1 (the precondition violation is visible).
- `C:/Users/imarl/miniconda3/python.exe -O probe.py` → prints `silently proceeded past a violated
  precondition`, exit code 0 (the precondition violation is invisible).

Applied to the real row: if `"Zzz Test Source Not In Overrides"` (or a source name colliding with
it) were ever added to `wiki_source.WIKI_OVERRIDES` — a plausible future edit, since
`WIKI_OVERRIDES` is a live, edited dict — a run of the battery under `-O` would silently stop
testing the intended "known non-fandom host with no override" path and instead exercise the
overridden path, while `check("resolve_wiki returns (None, None) for a known non-fandom host with
no override", ...)` three lines later would go on reading whatever `resolve_wiki` happens to
return for the now-overridden case — which could still pass, meaning nobody would ever learn the
fixture had stopped testing what its label claims.

**Impact is bounded, which is why this is MINOR and not MAJOR:** the project's own tooling
(`CLAUDE.md`, the sweep brief) invokes `python` directly, never `python -O`, and I found no
`-O` flag anywhere in the maintenance scripts that launch `verify_math.py`
(`local_agent.py:848`'s `subprocess.run([PY, ... "verify_math.py"])` passes no `-O`). So this is
not live-exploitable under the project's current invocation habits. It is real and reproducible,
it is the exact class of bug this file's own commentary elsewhere calls "a check that cannot fail
looks exactly like a check that passed," and it is un-exempted and unnoted.

**Proposed fix:** replace the bare `assert` with the pattern the rest of this file (and
`entity_match.py`/`scale_theories.py`/`tiers.py`) already use for a precondition that must hold
regardless of `-O`:

```python
if source_name in WS.WIKI_OVERRIDES:
    raise AssertionError("fixture source_name collides with a real WIKI_OVERRIDES entry")
```

or fold it into the `check()` battery itself as a `[control]` row asserting the fixture's own
precondition, consistent with how every other fixture precondition in this file is verified.

## Questions (possible deliberate design — none found this pass)

None. Unlike sweep64's batch02 report, I did not identify any open charter-owned "known defect"
questions specific to this read beyond the three already on record (M18 saturation, no Instrument
resolution above M4, and the `YEARS_PER_UNIT_DISTANCE` calibration note) — all three are pinned
with their own `[control]` rows exactly as sweep64 described, and I re-verified each pin is still
present and still reads as described (lines ~8283-8286 for M18's control row, ~1456-1468 for the
M5+ window pin, ~11530-11564 for the propagation-diameter INFO line). These are not new findings.

## Cleared (examined closely, found correct)

- The `check()` core (lines 85-104) and the atexit/crash-net wiring (`_verdict_even_if_a_row_raised_vm`,
  `_excepthook_vm`, `_at_vm`) — correct, and the "the battery ran every row it has, to the end"
  guarantee is real (traced the atexit registration order against `_REACHED_THE_END_VM`).
- The ledger-suppression machinery (`_no_ledger_vm`, `_no_ledger_for_vm`, `_third_party_vm`,
  `_spy_record_vm`, `_spy_flush_vm`) — each is exercised by its own driven control immediately
  after definition (lines ~569-646), and I traced the restore-on-exit `finally` blocks for all of
  them; none leaks a suppression past its `with` block.
- `_slices_of` (Hard Rule 0 truncation scanner) and its four-spelling canary — traced by hand
  against all four base-name shapes (bare, attribute, dict key, `.get()`), plus the unparseable-file
  sentinel path; correct.
- `_disarmed_rows20i` (the `or True` tautology-disarm scanner) — traced the BoolOp/Constant walk
  against every fixture in `_disarmed20i`/`_ordinary20i`; the ordinary-check control (line ~6549,
  `or True` on `want` rather than `got`) is correctly NOT flagged, confirming the scan is scoped to
  `got` only as documented.
- `_self_cites20ad`, `_blank_prose20z`, `_prose_backed20z`, `_standins20ae`/`_standins_wide20ae`
  (the four whole-file self-inspection scanners at the end of the file) — each carries its own
  positive AND negative controls immediately after definition, and I hand-traced each control
  fixture against the function body rather than trusting the row; all agree.
- The tol-discard scanner `_int_valued20z`/`_discarded_tol20z` — `round(x)` vs `round(x, 2)`
  distinction is handled correctly (only the one-argument form is treated as int-valued); bool
  literals correctly counted as int-valued (bool is an int subclass).
- Section 20p's `_interlock20p` / `_esc_aliases20p` (the escalation fail-open scanner) — the
  "Try whose body is EXACTLY ONE `import escalation` statement" predicate correctly does NOT flag
  `foreman.kill_stalled_job`'s advisory-escalate shape (verified against the `_advisory20p`
  control fixture at line ~7659).
- `_recursive_py_paths` (the shared os.walk helper used by ~6 whole-tree scans) — correctly skips
  `__pycache__` and correctly returns forward-slash relative paths including subdirectories.
- The `_RUN35_PINNED36` digest-and-execute gate (§20u) — traced the `_admit36` logic: a file must
  be BOTH on disk AND in the pin dict with a matching sha256 to be admitted; an on-disk-only or
  pin-only file is refused by name, never silently skipped. Confirmed against its own
  `_fixdisk36`/`_fixpins36` control fixture.
- No Windows-specific breakage found in this module: `verify_math.py` itself makes no WMIC calls
  (grep for `wmic`/`WMIC`/`psutil` returns nothing in this file — that machinery lives in
  `overnight.py`/`foreman.py`, out of this batch's scope), and the one subprocess spawn this file
  makes directly (§25/`_p20a`, the SIGTERM/rc=15 probe) correctly passes `CREATE_NO_WINDOW`.
- No other bare `except: pass`-shaped silent swallows found beyond the ones the file itself
  documents and exempts by name (`_no_ledger_vm`/`_no_ledger_for_vm`/`_third_party_vm` idiom, or a
  `silence.note("verify_math.py:<site>")` label with a stated reason) — cross-checked against
  §20z's own live-ledger-write assertion, which passed on this run.

## Coverage note

Module read in full, and only this module: `src/verify_math.py`, all 13,413 lines, start to
finish. No other module was read this session.
