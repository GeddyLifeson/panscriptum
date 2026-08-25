# Batch 01 audit — verify_math.py

Scope: `C:\Users\imarl\panscriptum-library-kit\src\verify_math.py` (3459 lines), read in full,
top to bottom, in five passes (1–400, 400–800, 800–1200, 1200–2000, 2000–2400, 2400–2800,
2800–3200, 3200–3459). Cross-checked against `profile.py` (build_all signature) and confirmed via
grep that verify_math.py is never `import`ed by any other module in `src/` — every caller
(`foreman.py:887`, `local_agent.py:349`) invokes it as a fresh `subprocess.run([...python...,
"verify_math.py"])`, never `import verify_math`. That fact matters for severity below.

Also ran a live AST parse over every file in `src/*.py` with
`C:/Users/imarl/miniconda3/python.exe` to confirm the current live state of one finding
(no syntax-broken files exist right now — see HIGH-1, which is about a *design gap*, not an
active failure).

## Overall assessment

This is an unusually disciplined test file. Nearly every section carries a dated provenance
comment (what broke, when, how it was measured, why the fix is not merely a restated default),
and the file explicitly self-corrects the exact failure modes this audit was asked to hunt for:
it documents and fixes a prior tautological check (line 386–390: "an earlier form of this check
compared `measure_bit_value('M7')` to itself — a tautology that could never fail"), documents and
fixes stale `want` values overtaken by a rescaled scale (line 497–507), and repeatedly asserts
that its own "recorded but silently skipped" scans (§19ab) do not go green because a file
couldn't be parsed. Two real findings survived that scrutiny; both are below.

---

## HIGH

### 1. verify_math.py:3336 — the "no console windows" AST scan silently drops unparsable files, with no safety net, unlike its own sibling scan

```python
for _p20e in sorted(_glob20e.glob(os.path.join(_here19, "*.py"))):
    try:
        _t20e = _ast20e.parse(open(_p20e, encoding="utf-8").read())
    except SyntaxError:
        continue                      # allsweep's LINT tier owns syntax; not this check's job
```//L3333-3337

This scan (Section 24, "§20e — NO CONSOLE WINDOWS, EVER") walks every `src/*.py` file looking for
unguarded `subprocess.run/Popen/call/check_output/check_call` sites (no `creationflags=` /
`startupinfo=`) and asserts the found list is empty:

```python
check("every subprocess spawn in src/ suppresses its console window",
      _unguarded20e, [], ...)                                              # L3355-3357
```

A file that fails to parse is `continue`d past with **no record kept anywhere** — no
`silence.note`, no accumulator list, nothing asserted against. If any `src/*.py` file currently
has (or later gets, mid-edit, from a crashed patch, etc.) a syntax error, and that file happens to
contain an unguarded `subprocess.run(...)` call, this check reports **clean** — the exact
"the check would go green BECAUSE something was wrong" failure this same file explicitly warns
against, almost word for word, ~850 lines earlier:

```python
except Exception:
    # NOT a silent skip. A module this scan cannot parse is a module the scan cannot
    # clear, and swallowing that would let an offending site hide inside a broken file --
    # the check would go green BECAUSE something was wrong. Recorded, and asserted below.
    silence.note("verify_math.py:S19ab-parse")
    _unparsed19ab.append(os.path.basename(_p19))
    continue
...
check("every module was readable by the context-window scan", _unparsed19ab, [], ...)  # L2509-2512
```

Section 19ab (the `num_ctx` literal scan) got this exactly right and even names the hazard in its
own comment. Section 24 (the console-window scan, written later in the file) reintroduces the
identical gap without the safety check. Given the surrounding comment states this is an "OWNER
DIRECTIVE, 2026-08-25, stated in the strongest terms: no command windows may EVER open" and the
whole point of this section is to catch a *single missed kwarg* anywhere in the tree, silently
exempting any file that fails to parse defeats that purpose in precisely the circumstance most
likely to occur (a file mid-edit).

Confirmed currently dormant: a live `ast.parse` sweep of every file in `src/*.py` right now found
zero syntax errors, so this is not an active false-green today — it is a design gap that will
produce a false-green silently and without warning the moment one file in the tree fails to parse.

**VERIFIED.** Repair: mirror the §19ab pattern — accumulate unparsed filenames into a list, log
via `silence.note`, and assert the list is empty (as §19ab already does at line 2509) so an
unparsable file makes *this* check fail loudly instead of silently excluding itself from cover.

---

## MEDIUM

### 2. verify_math.py:1298–1354 — Section 19d monkey-patches `completeness` module globals with no try/finally, unlike every other state-mutating section in the file

```python
_cp_hosts, _cp_recs, _cp_probe = _CP.HOSTS, _CP.RECORDS, _CP.category_size_probe
_CP.HOSTS, _CP.RECORDS = _chosts, _crecs                                    # L1298-1299
...
_cp_reach = _CP.host_reachable
_CP.host_reachable = lambda host, timeout=8: True                          # L1316-1317
_CP.category_size_probe = _stub([_E] * _nprobes)
check("all probes failed -> row KEPT as unreliable", len(_CP.audit(workers=1)), 1)  # L1319-1320
...  # three more _CP.category_size_probe reassignments and _CP.audit() calls, L1322-1345
_CP.host_reachable = _cp_reach
_CP.HOSTS, _CP.RECORDS, _CP.category_size_probe = _cp_hosts, _cp_recs, _cp_probe    # L1353-1354
```

Four attributes of the real `completeness` module (`HOSTS`, `RECORDS`, `host_reachable`,
`category_size_probe`) are patched to test stubs, exercised across five `_CP.audit(workers=1)`
calls, and only then restored — with **no `try:` around any of it**. Every other section of this
file that patches module state protects the restoration with `try/finally`:

- §2 (custodes) line 463/467: `try: ... finally: CU.CUSTODES.clear(); CU.CUSTODES.update(_full)`
- §18b (cascade routing) line 1053/1129: `try: ... finally: MG.F.evidence_for, ... = _saved`
- §19m (completeness `.land()`) line 1791/1815: `try: ... finally: _CP.OUT = _CP_OUT` — this is
  the *very same module*, patched correctly ~500 lines later in the same file.
- §19x (overwatch) line 1832/1895: `try: ... finally: _OW.LEDGER = _OW_LEDGER`
- §19ac (tuning) line 2562/2570, §19ad (gpu_lane) line 2594/2688,
  §19ae (tuning regime) line 2706/2740, §19l (read gates) line 2306/2308 — all guarded.

If `_CP.audit(workers=1)` were ever to raise partway through this block (a genuine bug in
`completeness.py`, not merely a failed assertion — `check()` itself never raises), the patched
stubs on `_CP.HOSTS` / `_CP.RECORDS` / `_CP.host_reachable` / `_CP.category_size_probe` would
never be restored on the real module object.

Practical severity is capped by the run model: verify_math.py is always launched as its own fresh
`subprocess.run(...)` (confirmed by grep — no `import verify_math` exists anywhere in `src/`), and
an uncaught exception here crashes that whole process before any other code could observe the
leaked stub. So this cannot currently corrupt a later section of *this* file's own run, and cannot
leak into another process. It is nonetheless a real inconsistency with the file's own established
and otherwise universal defensive pattern, and would become live risk the moment anyone imports
`verify_math` as a library (there is already prose elsewhere in the codebase gesturing at reusing
some of its checks) or copies this section's style into another long-lived process.

**VERIFIED.** Repair: wrap lines 1298/1354 in `try: ... finally:` exactly as §19m already does for
this same module 500 lines later.

---

## LOW / informational

### 3. verify_math.py:175 — unused walrus-assigned variable
```python
check("arrival(d=1.0) == YEARS_PER_UNIT_DISTANCE",
      P.arrival_years(1.0), C_ := P.YEARS_PER_UNIT_DISTANCE, tol=1e-9)
```
`C_` is bound via `:=` but never referenced again anywhere in the file (`grep -n "\bC_\b"` finds
only this line). Harmless — `want` still evaluates to the correct value — but it's dead surface
area that reads as if `C_` were meant to be reused later. **VERIFIED**, cosmetic only, not worth a
standalone fix but flagged since a future edit might build on the false assumption that `C_` is
live.

### 4. verify_math.py:791 — a cap, flagged per instructions, judged NOT a Hard Rule 0 violation
```python
# A SAMPLE, and labelled as one: 400 profiles is plenty to prove round-tripping and far
# cheaper than the full set. If decode ever breaks it breaks on the first row, not the 40,001st.
_rows = PR.build_all(limit=400)
```
`profile.build_all(limit=None)` (`src/profile.py:127`) defaults to unbounded — the full universe —
and the cap here is local to this one verification call, explicitly labelled as a sample, and
justified (round-trip decode either works structurally or it doesn't; a bad decoder fails on row
1 as reliably as row 40,001). This bounds a *measurement sample* inside the test suite, not a
delivered catalogue/roster; it does not touch `PR.build_all()`'s own default or any production
caller. **Judgment call: not a violation.**

No other `[:N]`, `.head()`, or `LIMIT`-shaped slice in this file touches real catalogued content —
the remaining hits (`_problems[:3]` at L266, `s[:220]` and `did[:5]` checked at L3126/L3160,
`str(exc)[:300]` at L3433) are either note-text truncation for print legibility, or checks that
*assert the absence* of a truncation bug elsewhere in the codebase (i.e., they are Hard-Rule-0
*compliance* checks, not violations).

---

## Patterns checked and found CLEAN

- **Tautologies / `want` massaged to match a buggy `got`**: none found. The file actively hunts
  and documents its own past instances of this (L386–390, L497–507, L1401–1407) and pins them with
  checks that fail under the old buggy code, not merely under a changed default.
- **Two-writer contract / bare `open(path, "w")` on shared state**: every bare-`open` write in the
  file targets a `tempfile.mkdtemp()` fixture (`_tdir`, `_ad`, `_cd`, `_gd`, `_wd`,
  `_land_dir`, `_GLx.LANE` pointed at a temp dir) used to simulate a foreign writer's disk state
  for a `pipeline.write_record` / `write_record_catalogue` / `silence.replace_retry` regression
  test. None write to a real project data/state path.
- **Swallowed failures**: every `except Exception`/`except SyntaxError`/`except TypeError` block
  is either (a) the assertion itself (SystemExit/TypeError catches that gate a `check()` on
  whether the exception fired), (b) explicitly logged via `silence.note(...)` and then separately
  asserted against (L48, L1538 cleanup-only, L2480/L2509, L2779, L3018), or (c) the one gap
  described in HIGH-1 above.
- **Module-state mutation without restoration**: the one gap is MEDIUM-2 above; every other
  monkey-patch site in the file (~10 of them) is wrapped in `try/finally`.
- **Concurrency**: §19t and §19ad both drive real `threading.Thread` races against
  `gpu_lane`/`read.py` gates and assert peak-concurrency bounds and zero stranded threads — these
  are correctness tests of the concurrency primitives, not concurrency bugs in the test itself.
  No unguarded shared-dict / lost-update pattern found in verify_math.py's own bookkeeping (the
  shared counters `_peak19ad`, `_gl_peak`, `_gl_cur` are all protected by their own
  `threading.Lock()`).
- **Dead code / contradicted docstrings**: none found in verify_math.py itself; the file's
  *subject matter* in several sections is exactly this defect in *other* modules (rigor.py,
  gpu_lane.py, overwatch.py), and those are pinned, not present here.

**CLEAN** (modulo the two findings above): verify_math.py's own `check()` harness (line 55–61),
sections 1–17 (physics/assay/census/propagation/time/ledger/derivation/rigor/custodes
/parity/statuses/anchors/address-space), and the bulk of sections 18–25 (§18–19c, §19e–19c/f/g/h
/h-bis/i/j/k/n/o/p/q/r/s/t/u/v/w/x/y/z/aa/ab/ac/ad/ae/af/ag/ah/ai/aj, §20a–§20f) show no
correctness bugs, no HARD RULE 0 violations, and no swallowed-failure or unrestored-state issues
beyond the two flagged above.
