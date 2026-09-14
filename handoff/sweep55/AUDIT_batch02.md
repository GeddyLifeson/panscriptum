# SWEEP run55 — AUDIT batch 02

**Module:** `src/verify_math.py` (12,656 lines, ~1,288 `check(...)` rows)

## How I read it

Every line, top to bottom, in nine passes of ~700 lines. On top of the read I ran five
scratch analyses (all in the session scratchpad, nothing written into `src/`, `data/`, `state/`
or any ledger, and `verify_math.py` itself was never executed):

1. an AST scan of every `check()` call for `got` and `want` with identical source segments, or
   with one textually nested in the other (the `f(x) == f(x)` shape this file has repaired four
   times);
2. an AST scan for `check()` rows whose `got` and `want` both call the same function;
3. an inventory of every `ExceptHandler` in the file, flagging those carrying neither a
   `silence.note` site nor a `silence-exempt:` marker;
4. a static (no-import) re-implementation of §20ae's own stand-in arity scan, pointed at
   `verify_math.py` instead of `drill.py`;
5. a direct probe of `prose_gate.instrument_shortfall` / `assert_instrument_present` against the
   four fixtures the new LAYER 4c block builds, plus a mutation of `INSTRUMENT_CLASSES`, to test
   whether the five new rows can pass vacuously.

I also resolved, by reading the target files, every `<file>.py:NNN` citation this file makes.
`prose_gate.py`, `drill.py`, `generate.py`, `standards.py`, `anchors.py`, `assay.py`,
`silence.py`, `overnight.py`, `feats.py` and `backfill.py` are **outside batch 02** — I read
them only to check citations and signatures, and I say so at each finding that depends on them.

---

### MAJOR — the five new LAYER 4c rows all stay green through a one-token mutation of the constant the gate turns on

**Where:** `src/verify_math.py:7068-7102` (fixtures `7076-7086`, rows `7087`, `7089`, `7092`,
`7096`, `7099`)

**What:** the block builds `_i_good`, `_i_lost`, `_i_place`, `_i_unins` and asserts

```
assert_instrument_present(_i_good, "t")  == 1.0
_raises(lambda: assert_instrument_present(_i_lost, "t")) is True
instrument_shortfall(_i_lost)[1]         == 1
assert_instrument_present(_i_place, "t") == 1.0
assert_instrument_present(_i_unins, "t") == 1.0
```

**Why it is wrong:** `prose_gate.assert_instrument_present` returns `1.0` on TWO different
outcomes — "every charged entry carried its section" and "nothing was charged at all"
(`prose_gate.py:502-503`, `if not required: return 1.0`). The block's own note at `7093-7095`
names this hazard exactly ("a mutant that skips it leaves required=0, and required=0 returns
1.0") and closes it with a `required == 1` companion — **but only for `_i_lost`.** The three
rows that assert `1.0` have no such companion, so each of them is satisfied by "the gate
examined this entry and was content" and by "the gate never looked at this entry".

Measured, not argued. Driving `prose_gate` directly (fixtures copied verbatim from lines
7076-7086):

| state | `instrument_shortfall(_i_place)` | `instrument_shortfall(_i_unins)` | bare `▣ The Instrument` heading, Class: Person |
|---|---|---|---|
| today | `(1, 1, [])` | `(1, 1, [])` | `(0, 1, [missing])` — refused |
| with `INSTRUMENT_CLASSES = ()` | `(1, 1, [])` | `(1, 1, [])` | `(1, 1, [])` — **accepted** |

and the five rows evaluate `[True, True, True, True, True]` in **both** states. Emptying
`INSTRUMENT_CLASSES` (or dropping `"person"` from it) turns off the "a being must show a SCORE
or an honest sentence" half of the gate entirely — a chapter carrying nothing but the heading
then passes layer 4c — and this file reports full green. The `_i_lost` rows do not catch it
because a lost section is still missing under the mutation (`marked` is False either way), and
the three `1.0` rows do not catch it because `not being` short-circuits the branch they claim
to be exercising. In particular the row at `7099` labelled *"the honest 'uninstrumented' body
satisfies a being"* passes in a world where nothing is a being.

This is the block's stated purpose defeated: its own header (`7068-7075`) says these are
"the ones that must hold in both places", and the reason given for landing them is that the
2026-09-10 mutation pass broke `instrument_shortfall` fourteen ways with nothing noticing.

**Mitigation (and why this is not a live gate hole):** `drill.py:1999-2010` — outside this
batch — carries `_I_PBARE` and `_I_BARE` nets that DO catch this mutation. So the library is
guarded; what is not guarded is the half this file claims to duplicate.

**Cheapest fix:** assert the triple rather than the fraction for the two excused fixtures, e.g.
`check(..., _PGate.instrument_shortfall(_i_place), (1, 1, []))`, and add the bare-marker
negative control (`▣ The Instrument` with no score and no honest sentence, Class: Person) that
drill already has.

**Confidence:** high. Ran `prose_gate.instrument_shortfall` / `assert_instrument_present`
against the exact fixture strings and against the mutated constant in a scratch script; read
`prose_gate.py:438-517` and `drill.py:1948-2016`. Nothing was written outside the scratchpad.

---

### MINOR — §20ad's justification for policing only SELF-citations is false: eight cross-module line citations in this file now point at unrelated code

**Where:** `src/verify_math.py:11823-11829` (the justifying paragraph), with the drifted
citations at `2533`, `2547`, `2564`, `4315`, `4525`, `4547`, `4549`, `4959`, `5240`, `8024`.

**What:** §20ad refuses `verify_math.py:NNNN` self-citations and explains why it does not
police citations of other files:

> "WHY THE SELF-CITATIONS ROT AND THE CROSS-MODULE ONES DO NOT. Spot-checked the same day:
> `standards.py:751`, `standards.py:67`, `standards.py:1901`, `anchors.py:427`,
> `sevenfold.py:86` and `assay.py:147-189` were all still accurate. They hold because they point
> at OTHER files, which this file's own growth does not move."

**Why it is wrong:** three of the six it names are wrong today, and five more elsewhere in the
file are wrong too. Resolved against the live source:

| citation (verify_math line) | claimed subject | what is actually there | where the subject really is |
|---|---|---|---|
| `standards.py:1901` (`4315`) | `standards.check()` calls `ollama_token_flow()` | `"no source outgrowing its code",` | `standards.py:2082` |
| `standards.py:751` (`4525`, `4547`, `4549`) | the `calls < MIN_CALLS_TO_JUDGE_RATE` cut | `def check(state=None):` | `standards.py:868` |
| `anchors.py:427` (`8024`) | indexes `INSTRUMENT_WINDOWS` across the Ladder unguarded | a message string in an unrelated check | `anchors.py:546`, `:551` |
| `silence.py:511, 518` (`4959`) | `write_json`'s temp-then-`replace_retry` | two unrelated comment lines | `silence.py:773` (def), `:836` (the replace) |
| `overnight.py:741` (`5240`) | `ledger_report`'s docstring naming `did[:5]` | `p.wait(timeout=timeout_h * 3600)` | `ledger_report` is at `overnight.py:939`; the `did[:5]` prose is at `889`, `894`, `926` |
| `assay.py:641` (`2533`) | `_rho_doc`'s `if not doc:` | a message-string fragment | `assay.py:1076`, `:1118` |
| `assay.py:776` (`2564`) | `len(hand_readings) > 1` | a comment about monotonicity | `assay.py:1246` |
| `assay.py:861` (`2547`) | `_ceiling = _promote = False` | a comment about grades | `assay.py:1392` |

`standards.py:67`, `sevenfold.py:86`, `sevenfold.py:214`, `cascade_bridge.py:18`,
`local_agent.py:421-424`, `prose_gate.py:34` and `assay.py:147-189` are still accurate, so the
harm is uneven — but the stated rule ("cross-module citations hold") is the reason §20ad's
enforcement stops where it does, and it is no longer true. The three `assay.py` ones sit in the
mutation-survivor commentary, which is precisely the prose a reader consults to find the guard a
mutant corrupted. A small extra irony: §20ad's own negative-control fixture at `11926` uses
`standards.py:751` as its example of *"a citation of another file"* that must not be flagged.

**Confidence:** high — every target line read directly with `sed -n`, and the real location of
each subject located by `grep`. The target files are outside batch 02; I read them read-only and
did not touch them.

---

### MINOR — two of this file's own stand-ins are NARROWER than the functions they replace, and §20ae's arity scan is pointed only at `drill.py`

**Where:** the scan: `src/verify_math.py:12543` (`_standins20ae`), applied at `12612` to
`_src20p("drill.py")` and nowhere else. The two narrow stand-ins:
`src/verify_math.py:5169` and `src/verify_math.py:10592`.

**What:** §20ae (`12497-12530`) was written because a drill stand-in that is narrower than its
subject "breaches on a CORRECT edit to the code it guards" — it records two halts caused by
exactly that in one day, one of them arriving disguised (`cited_names_for` swallows loader
exceptions, so the TypeError read as an always-empty cited set). The scan it added walks
`drill.py` only. Re-running the same predicate statically over `verify_math.py` resolves and
compares 45 stand-in sites here and finds two that are already narrow:

* `verify_math.py:5169` — `_FT.discover = lambda _h, _n, resolved=None: [...]` against
  `feats.discover(host, name, extra=None, resolved=None)`: three slots for four, missing
  `extra`. Safe today only because the one caller inside the stub window
  (`feats.evidence_for`, at `feats.py:2164`) passes `resolved=` by keyword and never passes
  `extra`.
* `verify_math.py:10592` — `F.api = _fake_api` where `_fake_api(host, params)` against
  `feats.api(host, params, retries=2, outcome=None)`: two slots for four. Safe today only
  because every `api()` call reachable from `backfill.backfill_source(dry=True)` is
  two-positional (`backfill.py:88`, `:211`). `feats.py:964` calls
  `api(host, {...}, retries=0, outcome=out)`, so a path change on either side turns this into a
  TypeError raised from inside the code under test.

**Why it is wrong:** this is the same latent break §20ae exists to prevent, in the file that
added the scan, unscanned. Neither is failing today; both fail on a correct widening of the
real function, which is the direction §20ae says punishes the fix.

**Cheapest fix:** give both stubs `**kw` (the remedy §20ae's own control row at `12640` says is
the right one), and run `_standins20ae` over `verify_math.py` as well as `drill.py`.

**Confidence:** high for the arity mismatch (read both signatures in `feats.py`, outside this
batch); medium for "safe today" — I traced the reachable call sites by grep rather than by
running the battery.

---

### MINOR — §18c's re-enumeration of the temp-directory sites that do NOT go through `_mkdtemp_vm` is itself incomplete, and its closing claim is false

**Where:** `src/verify_math.py:2062-2092`, specifically `2087-2092`.

**What:** the paragraph is a correction of an earlier enumeration that "over-claimed", and ends:

> "WHAT IS ACTUALLY EXEMPT, re-enumerated by reading every temp-making site in this file ...
> §19ab's token-flow root and §20p's halt-probe root, each rmtree'd from a `finally`; the two
> `TemporaryDirectory()` blocks; and batch6's `_tmp_guard` ... That is five, not three ...
> Everything else that makes a scratch directory goes through `_mkdtemp_vm` and is swept at
> exit."

**Why it is wrong:** there are seven untracked sites today, not five. The two omissions:

* `verify_math.py:5165` — `_scratch19ft = _tf19ft.mkdtemp(prefix="vm_feats_gate_")` (the §19ft
  feats-gate probe, landed 2026-09-08 under order `6d594a775899`), removed at `5176` inside the
  `finally`;
* `verify_math.py:9231` — `scratch_dir = _tempfile_b2.mkdtemp()` inside
  `_codewatch_concurrency_b2`, removed at `9268` in its `finally`. This one is discussed in the
  paragraph's own first half ("Batch2's `_codewatch_concurrency_b2` removed its directory AFTER
  a `json.load` that can raise ... its rmtree is now in a `finally`") and then left out of the
  list of what is exempt.

Neither leaks (both clean up from a `finally`), so the cost is the stale claim, not orphaned
directories. The claim matters because this paragraph is what a later reader trusts instead of
re-counting — which is the failure the paragraph itself is a correction of.

**Confidence:** high. Enumerated every `mkdtemp` / `TemporaryDirectory` / `mktemp` occurrence in
the file and classified each one by whether it goes through `_mkdtemp_vm`.

---

### MINOR — §20x's "the prose gate module still declares every layer" roster was not extended when layer 4c landed

**Where:** `src/verify_math.py:7153-7157`

**What:**

```
check("the prose gate module still declares every layer",
      all(hasattr(_PGate, f) for f in ("gate_open", "assert_gate_open", "evidence_ok",
                                       "section_shortfall", "assert_block_complete",
                                       "unearned_instrument")), True,
      note="a layer deleted is a layer that stops refusing, silently")
```

**Why it is wrong:** the roster names six functions and layer 4c's two
(`instrument_shortfall`, `assert_instrument_present`) are not among them, so the row's label
("every layer") and its note ("a layer deleted is a layer that stops refusing, silently") no
longer describe what it checks. Deleting `assert_instrument_present` from `prose_gate.py` leaves
this row green; the battery would still redden, but as an `AttributeError` at module level that
the atexit crash-net converts into one generic FAILED row — which is the BROKEN-rather-than-RED
outcome `e0d71f507510`/`8cdbd0fb6c14` were filed about, not the named refusal this row promises.

**Confidence:** high — read the row and grepped `prose_gate.py` for the layer-4c symbols.

---

### MINOR — nothing in this file pins that `generate.py` actually CALLS the layer-4c gate, though the identical question is asked of layer 2 by AST

**Where:** `src/verify_math.py:6962-6973` (layer 2, pinned by AST) versus the layer 4c block at
`7068-7102` (no wiring row). The live call site is `generate.py:552` — outside batch 02.

**What:** layer 2's row walks `generate.py`'s parse tree and demands an actual *Call* to
`assert_gate_open`, with the note "the supervisor gate governs only the supervisor; a hand-run
must refuse too". Layer 4c gets four behavioural rows against `prose_gate` and no wiring row at
all. `drill.py:8840`'s caller map (`want = {"generate.py": ("prose_gate.assert_gate_open", ...)}`)
likewise covers only `assert_gate_open`.

**Why it is wrong:** `generate.py:552` is a bare expression statement calling
`_PG.assert_instrument_present(text, ...)`. Deleting that one line disarms layer 4c on the live
prose path and leaves every row in this file, and the layer-4c drill family, green — because all
of them call `prose_gate` directly. This is the "the schema change landed with nothing behind
it" shape `prose_gate.py:427-436` names in its own comment, one level up.

**Confidence:** high for the absence (grepped both files for the symbol); the fix belongs in
this file (an AST row mirroring `6962-6973`) but the subject is `generate.py`, outside my batch.

---

### INFO — residual non-hermeticity: one row's verdict still turns on live machine state, by its own admission

**Where:** `src/verify_math.py:9649-9657` (and the ~15 live `standards.check()` /
`dashboard.state()` calls at `4353`, `6621`, `6626`, `6650`, `6667`, `8970`, `9587`, `9603`,
`9613`)

**What:** order `79d51aef8b71` records that this battery is not hermetic with respect to the GPU
and that its baseline moves. The abstention machinery (`_third_party_vm`, `_LIVE_STATE_VM`,
`_THIRD_PARTY_CLASSES_VM`) keeps the ledger ECHO of a live outage out of §20z, and §19ai's pin
plus its `urlopen` witness stop a 300-second `/api/generate` probe firing. What is NOT closed is
the row at `9649`, whose own note says so:

> "a standard that emits in the CLEAN run and drops in the BROKEN one lands in
> `_clean_names_b3 - _names_b3` beside the deliberately-broken one, and this row goes RED for
> somebody else's outage ... The exposure is NARROWED but not closed."

**Why it is only INFO:** it is measured, written down, and the narrowing was a deliberate
decision that refused the softer alternative. I am recording it because it is the live residue
of the order I was told to read with suspicion, and because it is still the mechanism by which a
mutation pass can be cancelled by another program. `standards.check()` still performs a real
`getaddrinfo`, a `tasklist` spawn and a PowerShell/WMI spawn roughly a dozen times per battery
run, so the exposure is not small.

**Confidence:** high — read the abstention machinery end to end and the row's own note; did not
run the battery.

---

### INFO — three rows are weak by construction (a degenerate implementation satisfies them), each covered elsewhere

**Where:** `src/verify_math.py:871`, `:1295`, `:3175`

* `871` — `prescience_horizon_bits("M5", 200)` against `round(2 * prescience_horizon_bits("M5", 100), 2)`.
  A function returning a constant `0` satisfies it (`0 == round(0, 2)`). Covered by `874-876`
  (M8 > M3).
* `1295` — `axis_score(1e-3, "M3", "ruin")` against `axis_score(BAND_EDGES["M3"]["ruin"], "M3", "ruin")`:
  both sides are the function under test, so any constant-returning `axis_score` passes. Covered
  by `762-765` and by §20r's refusal rows at `7794-7797` / `7857`.
* `3175` — `_mode_stable(["classical","compact"])` against `_mode_stable(["compact","classical"])`.
  **Marked kept-on-purpose**: `3182-3195` records that this permuted-input comparison was green
  against the defect on 12 of 13 hash seeds and is kept only because it states a property; the
  frozen triple at `3204-3212` and the source row at `3213` are what catch a revert. Saw the
  marking; moved on.

**Confidence:** medium-high — derived by an AST scan for `check()` rows whose `got` and `want`
call the same function (six hits; the other three — `1466`, `1548`, `1552` — are the deliberate
fresh-module-load and key-order repairs and are correct).

---

### INFO — `isinstance(_fl42, int)` accepts a JSON `true` as a count, in a file that is emphatic about the bool/int trap elsewhere

**Where:** `src/verify_math.py:1541-1544`

**What:** `check("the ASYMMETRIC-SUSPECT floor is on record and is a count",
isinstance(_fl42, int) and _fl42 >= 0, True, ...)` over the value read from
`state/THREAD_INTEGRITY_FLOOR.json`.

**Why it is worth a line:** `bool` is an `int` subclass, so a floor written as `true` passes as
"a count", and `True >= 0` holds. The same file calls that trap out by name twice —
`check()`'s own guard at `88-89` ("`bool` is an `int` subclass") and the
`interval_from_hands` row at `8234-8237` ("a bool dressed as a reading ... the same trap
`_check_scores` and `_check_weights` both name explicitly"). Fix is
`type(_fl42) is int` or an explicit `not isinstance(_fl42, bool)`.

**Confidence:** high (read the row); impact low — the file is written by the library, not by a
person.

---

### INFO — two `except` handlers carry neither a `silence.note` site nor a `silence-exempt:` marker, against this file's own stated inventory

**Where:** `src/verify_math.py:1539` and `src/verify_math.py:6813`

**What:** the swallow-exemption inventory at `280-311` states the doctrine that every
deliberate swallow in this tree either records its site or declares a written exemption, and
`2787-2791` repeats it ("Every other deliberate swallow in this tree records its site, and so
does this one"). An AST inventory of all 30 `ExceptHandler` nodes here found exactly two that do
neither:

* `1539` — `except Exception: _fl42 = None` around the `THREAD_INTEGRITY_FLOOR.json` read. It
  fails closed (the row above reddens on `None`), but nothing says so at the site.
* `6813` — `except Exception: continue` in the sweep-shard reader. This one explains itself in
  the comment immediately below ("An unreadable shard is sweep_plan's own reporting job (it
  notes it)"), so it has a written exemption in prose without the marker string the file's own
  `silence.instrument` classifier looks for.

**Confidence:** high — full AST inventory of the file's handlers; classified each by hand.

---

### QUESTION — five hardcoded population floors survive, after this file retired two of them as the wrong instrument

**Where:** `src/verify_math.py:9641` (`_used20q >= 12`), `11806` (`len(_tags20y) >= 55`),
`12229` (`_toln20z >= 60`), `12438` (`_seen20zn >= 30`), `12622` (`len(_seen20ae) >= 50`)

**What:** §20e (`5734-5746`) retired `_guarded20e >= 20` and §20j (`6492-6503`) retired
`len(emitted) >= 40`, with the same argument in both places: "a standard that never emits just
lowers a number nobody reconciles ... even a genuine drop below 40 would only report a COUNT,
never which standard went missing", and "keeping the weak one costs a reader the belief that the
floor meant something". Five anti-vacuity floors of the identical shape remain.

**Why this is a QUESTION and not a finding:** two of them are explicitly defended at their sites
— §20y's (`11806-11809`) argues for seven of headroom so a legitimately retired section does not
redden it, and §20ae's (`12622-12629`) was JUST strengthened this month from a grep into a count
of what the walk resolved. The others (`_toln20z`, `_seen20zn`, `_used20q`) are populations with
no obvious declared set to reconcile against. So this may be a deliberate line between "a floor
over a set that is declared somewhere" (retire it, reconcile) and "a floor over a population
nobody declares" (keep it). **For the coordinator/owner to rule on**; I am not proposing an edit.

**Confidence:** high on the facts (read all five rows and both retirement arguments); the
judgement is genuinely open.

---

## What I checked for and did NOT find

* **No `got == want` tautology.** An AST comparison of the source segments of `args[1]` and
  `args[2]` across all ~1,288 rows found zero identical pairs. The six "nested" hits
  (`3234`, `3236`, `3239`, `3241`, `4617`, `6348`) are all legitimate identity assertions — a
  function returning its argument unchanged, which is the property being claimed.
* **No disarmed row.** No `check()` whose `got` is a truthy constant, and no `... or True`
  disjunct at any nesting depth (this is §20i's own predicate, which I re-ran independently).
* **No `tol=` silently discarded.** Re-ran §20z's `_int_valued20z` predicate mentally over the
  rows that pass `tol=`; the two historical offenders (§1's relativistic KE, §3's burg row) are
  both repaired and documented.
* **No crash-on-a-missing-file in a pinned roster.** Every module named in `_INTERLOCKED`
  (`7204`), `_REPAIRED_20g` (`6041`) and §20j's `cachekey` roster (`7150`) exists on disk; all
  18 `handoff/run35/checks_*.py` files exist and reconcile exactly against the
  6 executed + 6 spliced + 6 registered accounting at `11225-11252`.
* **The layer-4c block does not write to the ledger.** `assert_instrument_present` raises
  `ProseRefused` (a plain `RuntimeError` subclass) and takes no `silence.note`, so the new rows
  cannot redden §20z. They also do not collide with any existing row label.
* **The new block sits where the brief said it does** — between the section-loss-floor row
  (`7064-7066`) and LAYER 4b (`7104`).
