# SWEEP run54 — AUDIT batch 02

**Module:** `src/verify_math.py` (12,561 lines) — the numeric/property battery.

## How it was read

Every line, top to bottom, in seven passes of ~900 lines each (no sampling, no grep-first). Then
five targeted static scans over the file's own parse tree, written to the scratchpad and run with
miniconda python, to turn four suspicions into measurements rather than impressions:

1. every `check(...)` row carrying a literal `tol=` >= 1e-3, printed with its `want` expression,
   to find tolerances that make an assertion vacuous;
2. every `check(...)` row whose `got` and `want` source segments are textually identical
   (none found);
3. every `X.attr = <lambda|def>` stand-in in this file, resolved to its target module and
   compared against the real function's parameter list **by parsing the target module** rather
   than importing it (so the scan has no side effects on live state);
4. every `check(...)` row whose `got` is a `Compare` against a numeric literal, to find
   threshold/floor rows and latching counters;
5. a census of every `mkdtemp` / `mktemp` / `TemporaryDirectory` site, against the file's own
   enumeration of which ones are exempt from the atexit sweep.

Nothing under `src/`, `data/`, `state/` or any ledger was modified. `verify_math.py` was **not**
executed (the file's own §20u and order c349a51ee2c5 both record that running it concurrently
with another battery run is unsafe); every finding below is established by reading the source and
by arithmetic that does not touch the library's state.

---

## Findings

### MAJOR — the crash net is switched OFF for the last 133 lines of the battery, including §20ae

**Where:** `src/verify_math.py:12426` (the assignment), against `src/verify_math.py:145-155`
(the atexit net) and `src/verify_math.py:12428-12556` (§20ae).

**What:** `_REACHED_THE_END_VM[0] = True` is executed at line 12426. The atexit handler is

```
@_atexit_vm.register
def _verdict_even_if_a_row_raised_vm():
    if _REACHED_THE_END_VM[0]:
        return
    FAIL.append((... "A ROW RAISED INSTEAD OF REDDENING" ...))
    _print_result_vm()
```

Everything from line 12428 to 12556 runs **after** the flag is set: the §20ae banner, the
`_src20p("drill.py")` read, `_standins20ae(_drill20ae)` (two full invocations, at 12529 and again
inside the row at 12539), and five `check()` rows at 12530, 12533, 12538, 12549 and 12552. Only
then does `_print_result_vm()` run, at 12559.

**Why it is wrong:** the whole argument of the block at lines 102-119 is that "a gate that dies
before printing its verdict is unusable as a gate" — `allsweep` grades a run with no RESULT line
BROKEN rather than RED, and `mutate.py` bins it as unjudgeable. For the last 133 lines that
protection is gone: a raise there leaves the atexit hook returning at line 147 and **no RESULT
line is printed at all**, which is precisely the outcome the net exists to prevent.

The raise paths are real, not hypothetical:

* `_src20p("drill.py")` at 12528 is an unguarded `open()`;
* `_standins20ae`'s `_ast20ae.parse(src_text)` at 12476 is unguarded — a `drill.py` caught
  mid-write raises `SyntaxError`, and §20e and §20g of this same file both record that a
  truncated `src/*.py` is "not hypothetical here" because `local_agent.py` patches this tree
  under model control;
* `_imp20ae.import_module(modname)` at 12497 sits inside `except Exception`, which does **not**
  catch `SystemExit` — and §20p:12527-12530 records that every module in this tree carries a
  `_BAD_CHARS` corruption guard that raises `SystemExit`. A corrupted sibling module named in
  `drill.py`'s import list therefore exits the interpreter from inside this scan, atexit runs,
  the hook sees the flag set and returns, and the run vanishes.

The fix is positional only: the assignment belongs immediately above `_print_result_vm()` at
12559. §20ae looks to have been appended below the flag rather than above it (its own comment
dates it to run #46, 2026-09-08).

**Confidence:** high. Verified by reading all three sites and by `grep -n "_REACHED_THE_END_VM"`,
which returns exactly three hits (123, 147, 12426); and by enumerating the `check(` rows after
12426, which returns the five §20ae rows.

---

### MAJOR — §1's relativistic-KE row permits a 100% error, so it passes against the exact defect it names

**Where:** `src/verify_math.py:733-735`, against `check()` at `src/verify_math.py:90-92`.

**What:**

```
check("KE relativistic @ 0.5c uses gamma", PH.kinetic(1.0, 0.5 * 2.99792458e8),
      (gamma - 1) * 1.0 * 2.99792458e8 ** 2, tol=1.0,
      note="must switch to relativistic above 0.1c; the bar is 1 joule against a quantity near
            4.6e16, i.e. floating-point noise and nothing wider")
```

`check()` computes `abs(got - want) <= tol * max(1.0, abs(want))`. **`tol` is a RELATIVE
tolerance**, not an absolute one. With `want` ≈ 1.3904e16 and `tol=1.0`, the permitted absolute
difference is 1.3904e16 — i.e. any `got` in `[0.0, 2.78e16]` passes.

**Why it is wrong:** the row's stated subject is that `physics.kinetic` switches to the
relativistic formula above 0.1c. It cannot see that switch being removed. Measured:

| quantity | value | passes? |
|---|---|---|
| relativistic (the `want`) | 1.3903791e16 | — |
| Newtonian `0.5*m*v^2` at 0.5c | 1.1234440e16 | **yes** (diff 2.669e15 <= 1.390e16) |
| `got = 0.0` | 0.0 | **yes** |
| `got = 2 * want` | 2.781e16 | **yes** |

So deleting the `v >= RELATIVISTIC_ABOVE * C` branch from `physics.kinetic` leaves this row green.
The only other `kinetic` row in the battery is line 715, `PH.kinetic(75, 10) == 3750.0`, which is
the Newtonian case and also stays green — so the relativistic switch is guarded by nothing.

The note is wrong twice over: `tol=1.0` is not "1 joule" (it is 100% of `want`), and `want` is
1.39e16, not "near 4.6e16".

A correct spelling is `tol=1e-12` (relative), which admits floating-point noise and refuses the
Newtonian answer by a factor of ~2e11.

**Confidence:** high. Arithmetic recomputed independently in the scratchpad; the branch structure
of `physics.kinetic` read at source (`src/physics.py`, `def kinetic` through `if v >= C:`).

---

### MAJOR — §20ae's anti-vacuity row cannot detect the vacuity it is named for

**Where:** `src/verify_math.py:12538-12541`.

**What:**

```
check("the scan is looking at a real population, not at nothing",
      len(_standins20ae(_drill20ae)[0]) == 0 and _drill20ae.count("CK.load = ") >= 1, True,
      note="guards against the walk silently matching no assignment at all, which would make "
           "both rows above pass on an empty set for ever")
```

**Why it is wrong:** neither conjunct measures the population.

* `len(_standins20ae(_drill20ae)[0]) == 0` is the *fault list*, which is exactly what the row at
  12530 already asserts. Re-asserting it here adds nothing and couples this row to that one.
* `_drill20ae.count("CK.load = ") >= 1` is a substring count over `drill.py`'s **text**, not a
  count of what the walk resolved.

`_standins20ae` returns `(bad, weak, unresolved)` and never reports how many stand-in sites it
actually examined, so the row has no population figure available to it. Consequence: typo the
`Assign`/`Attribute` node test inside `_standins20ae` so it matches nothing, and all three §20ae
rows read green — `bad == []`, `unresolved == []`, and `len([]) == 0 and 2 >= 1` — for ever. That
is the shape this file exists to refuse, in the row written to refuse it.

Every sibling "real population" row in this file counts what the scan resolved, not a literal in
the subject: `_toln20z >= 60` (12158), `_seen20zn >= 30` (12367), `_used20q >= 12` (7570),
`len(_tags20y) >= 55` (11735). §20ae is the odd one out.

The repair is to have `_standins20ae` return the number of resolved stand-in sites and assert a
floor on that.

**Confidence:** high. Read the function body at 12474-12525 (it returns three lists and no
count); confirmed `drill.py` contains `CK.load = ` twice, so the second conjunct is satisfied by
the file's text regardless of what the walk does.

---

### MINOR — §20ae is pointed at `drill.py` only; this file's own stand-ins are unscanned, and two are narrower than their subjects

**Where:** `src/verify_math.py:12528` (the scan's only subject), against
`src/verify_math.py:5155` and `src/verify_math.py:10521`.

**What:** §20ae's preamble (12429-12461) states the class — "a drill net proves something by
replacing a real function with a stub … when the real function later grows a parameter, the stub
does not, and the net breaches ON A CORRECT EDIT" — and records that it raised two halts in one
day. The scan is then run against `_src20p("drill.py")` and nothing else. `verify_math.py`
installs far more stand-ins than `drill.py` does, and exempts itself.

Running the same arity comparison over `verify_math.py` (AST-only, resolving each target against
its module's source rather than importing) finds two narrow stubs:

* `verify_math.py:5155` — `_FT.discover = lambda _h, _n, resolved=None: [...]` (3 positional
  slots) stands in for `feats.discover(host, name, extra=None, resolved=None)` (4). Worse than
  arity alone: the stub's **third positional slot is named `resolved`** where the real function's
  third positional is `extra`, so a positional third argument would bind to the wrong parameter
  silently. It works today only because the one live call site,
  `feats.py:2163`, spells it `discover(host, name, resolved=resolved)`.
* `verify_math.py:10521` — `_fake_api(host, params)` stands in for
  `feats.api(host, params, retries=2, outcome=None)` (4 positional). It works today only because
  `backfill.py:88` and `backfill.py:211` both call `F.api(host, q)` with two arguments — and
  `feats.fetch` already threads `outcome=` through, so this is exactly the "correct edit that
  breaks the stub" §20ae describes.

Neither is a live fault; both are the latent form of the fault §20ae was written for, in the file
that hosts §20ae.

**Confidence:** high for the signatures (`feats.py:821` and `feats.py:1293` read directly) and
for the call sites (grepped). The claim that these would break on a future edit is a projection,
which is why this is MINOR and not MAJOR.

---

### MINOR — §18c's re-enumeration of temp-directory sites is stale, and two direct sites sit outside the atexit sweep

**Where:** `src/verify_math.py:2073-2078`, against `src/verify_math.py:5151` and
`src/verify_math.py:9160`.

**What:** the paragraph reads:

> WHAT IS ACTUALLY EXEMPT, re-enumerated by reading every temp-making site in this file rather
> than by trusting the old list: §19ab's token-flow root and §20p's halt-probe root, each
> rmtree'd from a `finally`; the two `TemporaryDirectory()` blocks; and batch6's `_tmp_guard`,
> which is a single FILE removed in a `finally`. That is five, not three … Everything else that
> makes a scratch directory goes through `_mkdtemp_vm` and is swept at exit.

A census of every temp-creation site in the file finds **seven** direct ones, not five. The two
the enumeration does not name:

* `verify_math.py:5151` — `_scratch19ft = _tf19ft.mkdtemp(prefix="vm_feats_gate_")` (the §19ft
  pages-read-gate probe, added under order 6d594a775899). Its `shutil.rmtree` is in a `finally`
  but is **not** `ignore_errors=True`; the `except OSError` at 5163 notes the site and leaks the
  directory. On this machine that is the documented failure mode — a virus scanner holding a file
  open is the reason `_sweep_tmpdirs_vm` uses `ignore_errors=True` in the first place.
* `verify_math.py:9160` — `scratch_dir = _tempfile_b2.mkdtemp()` inside
  `_codewatch_concurrency_b2`, which is **called twice per run** (9199 and 9210), so it makes two
  untracked directories per battery run. Its rmtree is `ignore_errors=True` in a `finally`, so it
  cleans up on the normal path and leaks silently on a locked file.

The closing sentence — "Everything else that makes a scratch directory goes through `_mkdtemp_vm`
and is swept at exit" — is therefore no longer true, and the enumeration is the paragraph a
reader consults to decide whether a new direct `mkdtemp` is sanctioned. That is the same
stale-inventory shape order 41e4489aa545 corrected in this very paragraph one revision earlier.

**Confidence:** high. Full census by grep over `mkdtemp|mktemp|TemporaryDirectory`; each of the
seven sites read in place.

---

### MINOR — the duplicate-label ratchet's own account of its blind spot is stale: it is blind to 16 rows, not 2

**Where:** `src/verify_math.py:12083` (the claim) against `src/verify_math.py:12092-12096` (the
scan) and everything after it.

**What:** the comment closes with

> It cannot see its own two rows either, which are appended after this line runs.

and the scan is `_labels20z = [r[0] for r in PASS] + [r[0] for r in FAIL]` taken at line 12092.

**Why it is wrong:** sixteen `check()` rows are appended after that line: the dup-label row and
its control (12093, 12097), the discarded-`tol` pair and its two controls (12155, 12158, 12175,
12179), the prose-backed set (12349, 12367, 12372, 12386, 12406, 12412), and §20ae's five (12530,
12533, 12538, 12549, 12552). A duplicated label among those sixteen — which include four rows
whose labels are near-identical sentences of the form "and the scan is looking at a real
population, not at nothing" (12158, 12367) and "the scan is looking at a real population, not at
nothing" (12538) — is invisible to the ratchet.

Those three labels are in fact only *nearly* identical (two carry a leading "and "), so there is
no live collision today; the defect is that the ratchet could not report one if there were, while
its comment tells the next reader the blind spot is two rows wide.

**Confidence:** high. Enumerated the `check(` call sites after 12092 directly.

---

### MINOR — §20ae runs its scan twice, performing live imports of every module `drill.py` aliases, for one answer

**Where:** `src/verify_math.py:12529` and `src/verify_math.py:12539`.

**What:** `_bad20ae, _weak20ae, _unres20ae = _standins20ae(_drill20ae)` at 12529, and then
`len(_standins20ae(_drill20ae)[0]) == 0` inside the row at 12539 — the same call, discarded and
recomputed.

**Why it is wrong:** `_standins20ae` calls `importlib.import_module(modname)` for every alias
that is the target of an `X.attr = …` assignment anywhere in `drill.py`, and `inspect.signature`
on each resolved attribute. Doing that twice doubles a set of live module imports inside the one
instrument whose runtime already forced the `--help` early-exit at the top of this file (lines
16-31), and doubles the exposure to the `SystemExit`-at-import path described in the first MAJOR
finding above. The value from 12529 is already in `_bad20ae`.

**Confidence:** high — read both call sites; the second is a literal repeat of the first.

---

### INFO — `axis_score`'s clamp row compares two calls to the function under test

**Where:** `src/verify_math.py:1281-1283`.

**What:** `check("axis_score CLAMPS at zero, so 0.0 is a bound not a point",
A.axis_score(1e-3, "M3", "ruin"), A.axis_score(A.BAND_EDGES["M3"]["ruin"], "M3", "ruin"),
tol=1e-12)` — both `got` and `want` are calls to the function being tested. An `axis_score` that
returned a constant, or `None` for every input, satisfies it: with `want = None`,
`isinstance(want, float)` is False and `check()` falls through to `got == want`, which holds.

**Why it is only INFO:** the blanket-refusal case is covered elsewhere, deliberately and with the
argument written down — §20r:7786 asserts `isinstance(_ax_valid, float) and 0.0 <= _ax_valid <=
10.0` under the note "a guard that refuses everything passes every refusal test ever written",
and that repair is itself recorded as order dbc2937118da. Flagged so the coordinator knows the
row was read and judged, not missed.

**Confidence:** high on the mechanism; the judgement that it is adequately controlled elsewhere
is mine and the coordinator may disagree.

---

### INFO — §13's "recorded directions" row is a latching counter

**Where:** `src/verify_math.py:1514-1515`.

**What:** `check("the graph carries recorded directions, not just addresses",
(_g42[2]["recorded_directions"] > 0) if _g42 else False, True)` reads a cumulative statistic out
of the persisted thread graph. Once `data/THREADS.json` has ever carried one recorded direction,
this row is true for ever and can no longer report a regression in the recorder.

The row immediately below it (1517-1520) drives `_TI42.classify(...)` against a real reciprocal
pair from the live graph and asserts the `RECIPROCAL` class is reachable, which is the assertion
with teeth. Reported because the brief names this shape explicitly.

**Confidence:** high on the shape; whether it matters is a judgement for the coordinator.

---

### INFO — §19n's four behavioural tie-break rows cannot fail, and the file says so

**Where:** `src/verify_math.py:3158-3167`, marked at `src/verify_math.py:3168-3181`.

**What:** `_mode_stable` uses `key=lambda v: (xs.count(v), v)`, which is total, so
`_mode_stable(["classical", "compact"]) == _mode_stable(["compact", "classical"])` (line 3162)
holds by construction, and the three frozen-answer rows beside it are a hash-seed lottery against
the defect they name.

**This is marked kept-on-purpose.** The comment measures it ("green under the defect means the
row did not catch it: the permuted-input comparison was green on 12 seeds of 13"), states that
"the four behavioural rows above are kept because each states a property worth stating, but they
are not what catches a revert", and names the source row at 3199 as the one that holds. Saw the
marking; moving on. Recorded only so the coordinator does not re-derive it.

**Confidence:** high.

---

### INFO — two physical-constant rows carry loose but non-vacuous tolerances

**Where:** `src/verify_math.py:698` (`tol=0.02`) and `src/verify_math.py:708` (`tol=0.05`).

**What:** the Earth binding-energy row allows ±4.5e30 on 2.24e32 and the uniform-Sun row allows
±1.2e40 on 2.3e41. Both are checked against a `round(x, -29)` / `round(x, -38)` quantisation of
an expression written out in full in the row itself, so the tolerance is absorbing the rounding
step rather than hiding an error: substituting a wrong coefficient (e.g. `2GM^2/5R` for
`3GM^2/5R`) moves the answer by 33%, far outside either bar. Reported for completeness because
the tolerance scan surfaced them, not as defects.

**Confidence:** high — recomputed both quantities.

---

### INFO — the six spliced batch blocks each open with a no-op string expression

**Where:** `src/verify_math.py:8584`, `8997`, `9273`, `9855`, `10276`, and the batch6 header
comment at `10746`.

**What:** each spliced `run35 batchN` block begins with a triple-quoted string as a bare module-
level expression statement. Not being the first statement in the module, these are evaluated and
discarded — they are documentation, not docstrings. Harmless and evidently deliberate (they are
the authoring notes the coordinator preserved at merge time), but they are dead expressions and a
reader may take them for docstrings. Noted, not filed as a defect.

**Confidence:** high.

---

## What was checked for and NOT found

* **Rows where `got` and `want` are the same expression.** An AST scan comparing the normalised
  source segments of argument 1 and argument 2 across all 1,247 `check(` sites returned **zero**
  matches. The four historical instances the file records (map_seed at §15 order 3f86c571da58,
  `AS.assign` order fbdb7fe3bd4c, `SF.build` at §16, `_ck19ah` order cc500a6cbf4b) have all been
  repaired to compare against an independently exec'd module or a frozen literal, and the repairs
  are real.
* **`check(label, True, True)` tautologies and `or True` disarms.** §20i's own `_disarmed_rows20i`
  scan (6228-6257) walks this file's parse tree for a constant-truthy `got` or an always-true
  disjunct at any nesting depth, asserts `== []` at 6293, and carries seven positive and three
  negative fixtures at 6307-6333. The predicate is correct as written (I traced it) and the
  historical instances it was written for — orders 96c4be60fb92, 8a6d86040d10, 2f0a734d8c15 — are
  all genuinely gone.
* **`tol=` silently discarded by an int-valued `want`.** §20z's `_discarded_tol20z`
  (12116-12150) covers this class properly, with a two-sided control at 12175/12179 and a
  population floor at 12158. My independent tolerance scan found no int-valued `want` carrying a
  `tol=`. Note that this scan does **not** cover an oversized `tol`, which is the gap the second
  MAJOR finding sits in.
* **Restore-after-monkeypatch.** Every section that swaps a module attribute was checked for a
  matching restore. All are in `finally` blocks or followed by an explicit `[control] … was put
  back` row (§19d:2416-2433, §19ai:4556-4565, §20r:7854-7857 and 8353-8357, §20aa:11608).
  `_no_ledger_vm` and `_third_party_vm` both restore whatever was installed rather than the spy by
  name, so nesting cannot lose the outer patch — read and verified at 350-363 and 504-519.
* **`silence.note` reaching the live ledger from a probe.** `silence.note` calls
  `health.record(...)` by attribute lookup (`src/silence.py:889`), so `_no_ledger_vm`'s patch of
  `health.record` genuinely takes effect. The four unwrapped `silence.note` sites in this file
  (3795, 5659, 7662, 11232) are all on genuine-fault paths — an unparseable `src/*.py`, a run35
  file that will not execute — where recording is correct.
* **Sections reading live state rather than a fixture.** Present and numerous (§13's THREADS.json
  and TIERS.json, §16's `SF.build()`, §19aj's `publish.SITE`, §20k's dashboard, §20l's
  unrecognised ledger, §20n's sweep shards, §b3's live `standards.check()`), but every one of them
  carries a written argument for why the live read is the subject and, where the verdict could
  turn on another program's weather, either an abstention wrapper (`_third_party_vm`) or a printed
  INFO line instead of a verdict. I found no live-state read that is both ungoverned and
  undeclared.

---

## Summary

| severity | count |
|---|---|
| MAJOR | 3 |
| MINOR | 4 |
| INFO | 5 |
