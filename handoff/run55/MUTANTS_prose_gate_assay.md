# Mutation survivors — `src/prose_gate.py` and `src/assay.py`

Audit date 2026-09-10. Read-only analysis: no source file was modified, nothing under `data/`
or `state/` was run, and the prose gate was never exercised for real. Every behavioural claim
below was MEASURED against a standalone replica of the predicate (regexes copied verbatim from
the current source), not reasoned about in the abstract; the two replica scripts live in this
session's scratchpad and their output is quoted inline.

**Totals.** `prose_gate.py`: 14 survivors, **0 EQUIVALENT, 14 GAP**. `assay.py`: 2 survivors,
**2 EQUIVALENT, 0 GAP**.

**Citation drift.** NONE. Every one of the 16 cited line numbers still holds the cited code in
the current source. The mutation log's `src/ MOVED UNDER THIS RUN` warning (fingerprint
`f9d8e89e7044ebf8` -> `53fe3a432306b066`) did not displace any of these lines; verified by
`grep -n` on each cited text, reproduced in §0 below.

---

## 0. Line-number verification

```
$ grep -n "_CLASS_LINE.search\|if not m:\|if cls is None:\|_INSTRUMENT_UNINSTRUMENTED.search\|being = any\|if marked and\|elif not being and excused\|if not required:\|if present < required:\|label or \"block\"" src/prose_gate.py
300:    if not required:                              <- assert_block_complete's guard, NOT ours
301:        raise ProseRefused("%s: no entries found in the returned block" % (label or "block"))
320:            % (label or "block", present, required, 100 * frac,
458:    m = _CLASS_LINE.search(block or "")
459:    if not m:
476:        if cls is None:
482:                       or _INSTRUMENT_UNINSTRUMENTED.search(b))
483:        being = any(c in cls for c in INSTRUMENT_CLASSES)
484:        if marked and (scored or excused or not being):
486:        elif not being and excused:
502:    if not required:
504:    if present < required:
513:            % (label or "block", required - present, required, len(_shown), len(missing),

$ grep -n "strict=True" src/assay.py
795:            "assigned MORE uncertainty than worse testimony." % dict(zip(order, vals, strict=True)))
877:            % (label ... ) % dict(zip(order, _floors, strict=True)))
```

All 16 cited lines confirmed in place. Note that lines 300/301/320 are the *sibling* sites in
`assert_block_complete`, which already HAVE a net (`_a_refusal_names_the_block_it_refused`,
drill.py:1948) — that net is the template for what §2 proposes, and its own docstring names
batch C01's `label or "block"` -> `label and "block"` mutants and the `if not required:` mutant
as the attackers it was written for. The 502/513 survivors below are the exact same two attacks
landed on the function that has no such net.

---

## 1. THE HEADLINE FINDING — the Instrument gate has no test of its predicate at all

**Verdict: the battery does not exercise `instrument_shortfall` in any way, with any input,
classed or not. It has never been called by a test.**

Evidence, run against the current tree:

```
$ grep -rn "instrument_shortfall" --include=*.py .
./src/prose_gate.py:464:def instrument_shortfall(text):
./src/prose_gate.py:501:    present, required, missing = instrument_shortfall(text)
./src/prose_gate.py:515:               ("; ... and %d more — the complete list is instrument_shortfall()'s third return "

$ grep -rn "assert_instrument_present" --include=*.py .
./src/generate.py:552:        _PG.assert_instrument_present(text, f"block {gi + 1}/{len(groups)}")
./src/prose_gate.py:435:# pinning `assert_instrument_present`, WITHOUT which this layer is unproven (standing lesson 9).
./src/prose_gate.py:496:def assert_instrument_present(text, label=""):
```

Three self-references inside the module that defines it, and one production call site. Nothing
else in the tree names either function. The helper `_entry_class` and every constant the
predicate reads — `INSTRUMENT_CLASSES`, `_INSTRUMENT_MARK`, `_INSTRUMENT_NOT_APPLICABLE`,
`_INSTRUMENT_UNINSTRUMENTED`, `_CLASS_LINE`, `_AXIS_LABEL` — are likewise referenced ONLY from
inside `prose_gate.py` (same grep, full output in the session log).

Nor is it reached indirectly. The complete set of `prose_gate` attributes the two test modules
touch:

```
$ grep -o "PG\.[A-Za-z_]*" src/drill.py | sort -u
PG.HERE  PG.ProseRefused  PG._coverage_rows  PG.assert_block_complete  PG.assert_gate_open
PG.assert_step  PG.cited_fraction  PG.cited_names_for  PG.evidence_ok  PG.gate_open
PG.section_shortfall  PG.step  PG.unearned_instrument

$ grep -o "_PGate\.[A-Za-z_]*" src/verify_math.py | sort -u
_PGate.REQUIRED_PER_ENTRY  _PGate.SECTION_LOSS_FLOOR  _PGate.assert_block_complete
_PGate.evidence_ok  _PGate.gate_open  _PGate.section_shortfall  _PGate.unearned_instrument
```

Thirteen names in drill, seven in verify_math, and layer 4c appears in neither. There is also no
dynamic escape hatch: `grep -n "getattr(_PGate\|getattr(PG\|getattr(prose\|dir(PG)\|vars(PG"` over
both files returns nothing, so no net reaches the function by reflection. And no structural net
pins the CALL either — `generate.py:552` is not among the call-shapes asserted at drill.py:8731
(`want = {"generate.py": ("prose_gate.assert_gate_open", ("main",))`), so even deleting the call
site would not go red.

**Therefore all 14 prose_gate survivors are ONE finding, not fourteen.** 1,283 verify_math checks
and 479 drill nets cannot tell the difference between this function and any corruption of it,
because none of them runs it. That is the whole explanation for the 14 survivals; the individual
rulings in §2 exist to say what each mutation would DO in production and to supply killing inputs,
not to suggest fourteen separate remedies.

This is not a surprise to the module. `prose_gate.py:427-436` says so in advance:

> "The check is therefore landed here in full and wired into the live path by `generate.py`
> immediately after `assert_block_complete`, so it genuinely refuses a block; what is owed is a
> fixture carrying an Instrument line plus a net and a verify_math row pinning
> `assert_instrument_present`, WITHOUT which this layer is unproven (standing lesson 9)."

The mutation run is the independent confirmation that the owed work is still owed. And the debt
matters more than an ordinary coverage hole, because layer 4c is the ONLY layer that can see the
2026-08-25 incident's headline symptom: 1,155 of 1,268 entries lost their Instrument section — a
91% loss against the 71% Threads loss that IS checked, at three nets and two verify_math rows.
`section_shortfall` scores a block with every Instrument section deleted at 10/10, and
`unearned_instrument` catches a fabricated score only when one is present. So the guard standing
between the catalogue and a recurrence of the worst symptom the library has ever had is guarded
by nothing, and any of the seven mutations in §2.1 would silently switch it off.

**The single remedy** is the fixture-plus-net-plus-row the comment already names. §2 gives the
shape; §3 gives the minimum set that kills all 14.

---

## 2. Rulings — `src/prose_gate.py` (14 survivors, all GAP)

### Method

The predicate at 479-491 was replicated verbatim into a standalone script (no project imports)
and every mutant variant evaluated against ten fixtures spanning the class/marker/score/excuse
space. Measured result — cells that differ from the original are the killing inputs:

```
fixture                                     orig   482or→and 483in→notin 484and→or 484or#1 484or#2 484drop-not 486and→or 486drop-not
being, marked, scored                      PRESENT  PRESENT   PRESENT    PRESENT   MISSING PRESENT  PRESENT     PRESENT   PRESENT
being, marked, uninstrumented               PRESENT  MISSING   PRESENT    PRESENT   MISSING MISSING  PRESENT     PRESENT   PRESENT
being, marked, bare (no score, no excuse)   MISSING  MISSING   MISSING    PRESENT   MISSING MISSING  PRESENT     MISSING   MISSING
being, NO marker, scored                    MISSING  MISSING   MISSING    PRESENT   MISSING MISSING  MISSING     MISSING   MISSING
being, NO marker, uninstrumented            MISSING  MISSING   MISSING    PRESENT   MISSING MISSING  MISSING     PRESENT   PRESENT
being, NO marker, nothing (INCIDENT SHAPE)  MISSING  MISSING   MISSING    MISSING   MISSING MISSING  MISSING     MISSING   MISSING
place, marked, Not applicable               PRESENT  PRESENT   PRESENT    PRESENT   PRESENT PRESENT  PRESENT     PRESENT   PRESENT
place, marked, bare                         PRESENT  PRESENT   MISSING    PRESENT   PRESENT MISSING  MISSING     PRESENT   PRESENT
place, NO marker, Not applicable            PRESENT  MISSING   MISSING    PRESENT   PRESENT PRESENT  PRESENT     PRESENT   MISSING
place, NO marker, nothing                   MISSING  MISSING   MISSING    PRESENT   MISSING MISSING  MISSING     PRESENT   MISSING
```

Every predicate mutant is distinguished by at least one fixture. **No predicate mutant is
equivalent.**

The six structural mutants were measured the same way, against three whole-block inputs — GOOD
(a compliant `Class: Person` entry carrying `▣ The Instrument` and `Wisdom: 18`), BAD (the same
entry with no Instrument section at all), FEATS (an entry with no `Class:` line, the exempt
case). Measured:

```
orig   GOOD=ok(1.00)      BAD=REFUSED["block 3/7: 1 of 1 entries carry no Instrument section"]  FEATS=ok(1.00)
458    GOOD=ok(1.00)      BAD=ok(1.00)                                                          FEATS=ok(1.00)
459    GOOD=ok(1.00)      BAD=ok(1.00)                                                          FEATS=AttributeError
476    GOOD=ok(1.00)      BAD=ok(1.00)                                                          FEATS=TypeError
502    GOOD=ok(1.00)      BAD=ok(1.00)                                                          FEATS=ZeroDivisionError
504    GOOD=REFUSED[...]  BAD=ok(0.00)                                                          FEATS=ok(1.00)
513    GOOD=ok(1.00)      BAD=REFUSED["block: 1 of 1 ..."]  (label lost)                        FEATS=ok(1.00)
```

Again: **no structural mutant is equivalent.** Three inputs separate all six.

### 2.1 The seven that SILENTLY DISABLE or LOOSEN the gate (false negatives — the incident recurs, unreported)

These are the dangerous half. Each lets prose through that the gate exists to refuse, and none of
them raises anything anybody would notice on a normal chapter.

---

**GAP 1 — line 502, drop `not`.** `if not required:` -> `if required:`

Behaviour: the exemption and the check trade places. Every block that HAS classed entries — i.e.
every real chapter — returns `1.0` immediately without the comparison ever running. The gate is
100% dead on exactly the input it was written for. The exempt case (a FEATS block, `required == 0`)
falls through to `if present < required` -> `0 < 0` -> False -> `return present / required` ->
**ZeroDivisionError**, which is not a refusal and would not be caught by a `_refuses(..., ProseRefused)`
net either. Measured above: `502 GOOD=ok BAD=ok FEATS=ZeroDivisionError`.

This is the same attack drill.py's `_a_refusal_names_the_block_it_refused` docstring records against
`assert_block_complete` (order 9730552e6315): *"With the negation dropped, a block with nothing to
check skips the refusal and falls through to `present / required` -- ZeroDivisionError, which is not
a refusal at all."* The sibling function was hardened; this one was not.

Killing test: `assert_instrument_present(BAD, "t")` must raise `ProseRefused`. Also
`assert_instrument_present(FEATS) == 1.0` must return, not raise (that half catches the
ZeroDivisionError direction).

---

**GAP 2 — line 504, `<` -> `>=`.** `if present < required:` -> `if present >= required:`

Behaviour: the verdict is inverted in BOTH directions. A fully compliant block is refused; a block
where every entry lost its Instrument section returns `0.0` and is filed. And the refusal it raises
on the compliant block renders as a self-refuting sentence — measured: *"block 3/7: 0 of 1 entries
carry no Instrument section"*, i.e. it announces that nothing is missing while refusing. Note that
this one is loud in production (it would halt the first compliant chapter), but it is silent in the
battery, because the battery never calls it.

Killing test: the same pair as GAP 1 — `GOOD` must return `1.0` without raising AND `BAD` must
raise. Either half alone kills it.

---

**GAP 3 — line 458, `or` -> `and`.** `_CLASS_LINE.search(block or "")` -> `search(block and "")`

Behaviour: for any non-empty block string, `block and ""` evaluates to `""`, so the search runs
against the empty string and can never match. `_entry_class` returns `None` for every entry in the
corpus; `instrument_shortfall` therefore `continue`s past all of them, reports `(0, 0, [])`, and
`assert_instrument_present` returns `1.0` via the `not required` exemption. **The gate is switched
off completely and silently — no exception anywhere, on any input.** Measured: `458 GOOD=ok BAD=ok
FEATS=ok`, all three identical to a gate that does not exist.

This is the most dangerous of the fourteen: it is the only one with no failure mode at all, and its
effect is precisely to restore the pre-2026-09-08 state in which the incident's headline symptom
passes every layer.

Killing test: `assert_instrument_present(BAD, "t")` raising — or, more pointedly,
`instrument_shortfall(BAD)[1] == 1`, asserting that a classed entry is actually CHARGED. A net on
`required` is the one that names this defect exactly.

---

**GAP 4 — line 476, `is` -> `is not`.** `if cls is None: continue` -> `if cls is not None: continue`

Behaviour: the population is inverted. Only entries that declare NO class are charged — the exact
set the ruling deliberately exempts, and the set the comment at 420-423 says must not be charged
twice for one fault. On a real chapter, where every entry carries a `Class:` line, `required` is 0
and the gate returns `1.0` — dead again. On the exempt FEATS block, `cls` is `None` and line 483
executes `"person" in None` -> **TypeError**. Measured: `476 GOOD=ok BAD=ok FEATS=TypeError`.

Killing test: same as GAP 3 (`instrument_shortfall(BAD)[1] == 1`) plus `instrument_shortfall(FEATS)
== (0, 0, [])`, which pins the exemption without crashing.

---

**GAP 5 — line 459, drop `not`.** `if not m:` -> `if m:`

Behaviour: `_entry_class` returns `None` when a Class line IS found, and falls through to
`m.group(1)` with `m is None` when it is not. So classed entries are skipped (gate dead on real
chapters) and classless entries raise **AttributeError: 'NoneType' object has no attribute 'group'**.
Measured: `459 GOOD=ok BAD=ok FEATS=AttributeError`.

Killing test: identical to GAP 4 — charge a classed block, exempt a classless one.

---

**GAP 6 — line 484, `and` -> `or`.** `if marked and (...)` -> `if marked or (...)`

Behaviour: the requirement that the section MARKER be present evaporates whenever any other
condition holds. Measured, four fixtures flip PRESENT that were MISSING:

* `being, marked, bare` — a `▣ The Instrument` heading with nothing under it now passes. (Under
  the original it is refused: a heading is not a section.)
* `being, NO marker, scored` — a Person entry with `Wisdom: 18` and no Instrument section at all
  now passes. This is the withdrawn batch's exact composite: axis numbers floating in prose with
  the Custodial section stripped.
* `being, NO marker, uninstrumented` — the honest body without the section it belongs to.
* `place, NO marker, nothing` — a Place with neither the section nor the Not-applicable sentence.

Worth stating precisely so it is not overclaimed: the pure incident shape (a Person entry with
prose only, no marker, no score, no excuse) is still MISSING under this mutant. The loosening is
real but partial — it admits the four shapes above, not literally everything.

Killing test: `instrument_shortfall(being-no-marker-scored)[2] != []`. That single fixture is the
one most worth having anyway, since it is the shape the incident actually produced.

---

**GAP 7 — line 486, `and` -> `or`.** `elif not being and excused:` -> `elif not being or excused:`

Behaviour: the non-being fallback becomes a universal amnesty. Two fixtures flip:
`being, NO marker, uninstrumented` (a Person that writes "uninstrumented" in its prose but carries
no section now passes — the excuse sentence is accepted in place of the section it is supposed to
sit INSIDE) and `place, NO marker, nothing` (a Place with neither, excused purely for not being a
being). The second is the wider hole: under this mutant every non-being entry is unconditionally
present, so four of the seven classes stop being checked entirely.

Killing test: `instrument_shortfall(place-no-marker-nothing)[2] != []` — a Place that wrote nothing
must still be charged.

### 2.2 The six that OVER-REFUSE (false positives — good prose is rejected)

Less dangerous to the catalogue (nothing bad gets published) but still real defects: an
over-refusing gate is a gate that gets deleted by whoever it blocks — drill.py states exactly this
at line 1926, *"an over-refusing gate is removed by whoever it blocks"*. All six change behaviour;
none is equivalent.

---

**GAP 8 — line 486, drop `not`.** `elif not being and excused:` -> `elif being and excused:`

Behaviour: the fallback swaps sides. `being, NO marker, uninstrumented` flips MISSING -> PRESENT
(a being is now excused without its section — a loosening), while `place, NO marker, Not applicable`
flips PRESENT -> MISSING: **the template's own prescribed answer for Places, Vessels, Factions and
Events is now refused.** That is a direct contradiction of the Entry Template quoted at
prose_gate.py:417-419.

Killing test: `assert_instrument_present(place-no-marker-Not-applicable) == 1.0` — the template's
own sentence must satisfy the gate.

---

**GAP 9 — line 484, first `or` -> `and`.** `(scored or excused or not being)` -> `(scored and excused or not being)`

Precedence after the textual substitution: `(scored and excused) or (not being)`. Behaviour: the
NORMAL GOOD CASE breaks. Measured, `being, marked, scored` flips PRESENT -> MISSING — a properly
written Person entry, `▣ The Instrument` heading with real axis scores under it, is now reported as
having no Instrument section. `being, marked, uninstrumented` flips too. Under this mutant a correct
chapter cannot be filed at all.

Killing test: `assert_instrument_present(GOOD) == 1.0`. The simplest possible net kills it.

---

**GAP 10 — line 484, second `or` -> `and`.** `(scored or excused or not being)` -> `(scored or excused and not being)`

Precedence: `scored or (excused and not being)`. Behaviour: two flips. `being, marked,
uninstrumented` PRESENT -> MISSING — the template's honest "uninstrumented -- no faculties on file"
body no longer excuses a being, which is the case the docstring at 468-470 explicitly promises to
allow. And `place, marked, bare` PRESENT -> MISSING: a non-being entry that wrote the section
heading but not the excuse sentence is now charged.

Killing test: `assert_instrument_present(being-marked-uninstrumented) == 1.0` — the docstring's own
promised third form.

---

**GAP 11 — line 484, drop `not`.** `(scored or excused or not being)` -> `(scored or excused or being)`

Behaviour: `being, marked, bare` flips MISSING -> PRESENT (a being with an empty heading is excused
merely for being a being — a loosening), and `place, marked, bare` flips PRESENT -> MISSING. The
non-being class no longer satisfies the gate by its own nature, which is the entire point of the
`not being` term.

Killing test: the pair `assert_instrument_present(place-marked-bare) == 1.0` and
`instrument_shortfall(being-marked-bare)[2] != []`.

---

**GAP 12 — line 483, `in` -> `not in`.** `any(c in cls ...)` -> `any(c not in cls ...)`

Behaviour: `being` becomes True for every class that is not simultaneously all three of
"person"/"god"/"beast" — i.e. for every real class, measured `being_notin = True` on all ten
fixtures. The being/non-being distinction is erased and every entry is held to the scored-or-excused
standard. Two flips: `place, marked, bare` and `place, NO marker, Not applicable` both PRESENT ->
MISSING. Places, Vessels, Factions and Events are now required to produce a score or an excuse
sentence they were never asked for.

Killing test: `assert_instrument_present(place-no-marker-Not-applicable) == 1.0` (shared with GAP 8).

---

**GAP 13 — line 482, `or` -> `and`.** `_INSTRUMENT_NOT_APPLICABLE.search(b) or _INSTRUMENT_UNINSTRUMENTED.search(b)` -> `and`

Behaviour: an entry must now contain BOTH excuse phrases to be excused — a combination the template
never asks anyone to write. Two flips: `being, marked, uninstrumented` and `place, NO marker, Not
applicable`, both PRESENT -> MISSING. So the two honest bodies the docstring names each individually
stop working; only a nonsensical entry containing both survives.

Killing test: the two must work SEPARATELY —
`assert_instrument_present(being-marked-uninstrumented) == 1.0` and
`assert_instrument_present(place-no-marker-Not-applicable) == 1.0`, asserted as two conditions, not
one fixture carrying both strings.

### 2.3 The diagnostic one

---

**GAP 14 — line 513, `or` -> `and`.** `(label or "block")` -> `(label and "block")`

Behaviour: the refusal stops naming the block it is about. `generate.py:552` passes
`f"block {gi + 1}/{len(groups)}"`, so the message changes from *"block 3/7: 1 of 1 entries carry no
Instrument section..."* to *"block: 1 of 1 entries carry no Instrument section..."* — measured
above. Across a run of several hundred chapter jobs, an operator deciding whether to withdraw a
batch loses which job failed. (The empty-label case degrades in the other direction: `"" and "block"`
is `""`, so the message opens with a bare colon.)

Not equivalent, and not merely cosmetic by this project's own standard: drill.py:1948's docstring
rules on exactly this mutation at the sibling site — *"a refusal that cannot say WHICH of several
hundred chapter jobs it is about is a refusal nobody can act on"* — and batch C01 landed it at both
`assert_block_complete` sites (orders d65d43a823c4, 22612f09489a) with the battery green. The net
written in response covers lines 301 and 320. Line 513 is the third site and was never added to it.

Killing test: raise from `assert_instrument_present(BAD, "II.A.3/Persons#1-30")` and assert the
label substring appears in `str(e)` — i.e. extend `_a_refusal_names_the_block_it_refused` to this
function, or write its twin.

---

## 3. What to write — the minimum that kills all fourteen

One fixture family and two test sites. Concretely:

**Fixtures** (add beside drill.py's `good` at line 1866 and verify_math's `_good` at 7051; both
existing fixtures are `Class: Person` entries with NO Instrument section, which is why layer 4c
could not be folded into `REQUIRED_PER_ENTRY` — see prose_gate.py:426-431):

```python
_I_GOOD  = ("◈ **A**\nShelfmark: 1\nClass: Person\nMagnitude: M2\n"
            "▣ The Instrument\nWisdom: 18 (Exalted)\n" + _BODY + "**Threads: pending**\n")
_I_UNINS = ("◈ **A**\nShelfmark: 1\nClass: Person\nMagnitude: M2\n"
            "▣ The Instrument\nuninstrumented -- no faculties on file\n" + _BODY)
_I_BARE  = ("◈ **A**\nShelfmark: 1\nClass: Person\nMagnitude: M2\n"
            "▣ The Instrument\n" + _BODY)                       # heading, nothing under it
_I_LOST  = ("◈ **A**\nShelfmark: 1\nClass: Person\nMagnitude: M2\n" + _BODY)   # INCIDENT SHAPE
_I_SCORE = ("◈ **A**\nShelfmark: 1\nClass: Person\nMagnitude: M2\nWisdom: 18\n" + _BODY)
_I_PLACE = ("◈ **A**\nShelfmark: 1\nClass: Place\nMagnitude: M2\n"
            "Not applicable -- the Instrument measures beings, not places.\n" + _BODY)
_I_PBARE = ("◈ **A**\nShelfmark: 1\nClass: Place\nMagnitude: M2\n" + _BODY)
_I_FEATS = ("◈ **A**\nShelfmark: 1\n" + _BODY)                  # no Class line: exempt
```

**Nets / rows** — nine conditions, which between them kill all fourteen:

| # | condition | kills |
|---|---|---|
| 1 | `assert_instrument_present(_I_GOOD, "t") == 1.0` | 9, 12 (part), 2 |
| 2 | `_refuses(lambda: assert_instrument_present(_I_LOST, "t"), ProseRefused)` | 1, 2, 3, 4, 5 |
| 3 | `instrument_shortfall(_I_LOST)[1] == 1` — the classed entry is CHARGED, not skipped | 3, 4, 5 (names the defect exactly) |
| 4 | `instrument_shortfall(_I_FEATS) == (0, 0, [])` and `assert_instrument_present(_I_FEATS) == 1.0` | 1 (ZeroDivisionError), 4 (TypeError), 5 (AttributeError) |
| 5 | `instrument_shortfall(_I_SCORE)[2] != []` — scores without the section are still a shortfall | 6 |
| 6 | `instrument_shortfall(_I_PBARE)[2] != []` — a Place that wrote nothing is still charged | 7 |
| 7 | `assert_instrument_present(_I_PLACE) == 1.0` — the template's own sentence satisfies the gate | 8, 12, 13 (half) |
| 8 | `assert_instrument_present(_I_UNINS) == 1.0` — the honest uninstrumented body satisfies it | 10, 13 (half) |
| 9 | `assert_instrument_present(_I_BARE)` refuses, AND `assert_instrument_present(_I_PBARE)` refuses while `_I_PLACE` passes | 11 |

Plus one twin of the existing message net, which is the only thing that reaches GAP 14:

```python
def _an_instrument_refusal_names_the_block_it_refused(label="II.A.3/Persons#1-30"):
    try:
        PG.assert_instrument_present(_I_LOST, label)
        return False                    # the section is gone and it passed
    except PG.ProseRefused as e:
        return label in str(e) and "Instrument" in str(e)
    except Exception:
        return False                    # a crash is not the refusal this gate promises anyone
```

That function alone kills GAP 14, GAP 1, GAP 2, GAP 3, GAP 4 and GAP 5 — six of the seven silent
ones — because it asserts the refusal, its label, and (via the bare-`except Exception`) that no
crash is substituted for it. It is the direct analogue of `_a_refusal_names_the_block_it_refused`
and should sit next to it. Condition 4 above must be a separate net, since the exempt path is the
one the crash mutants take.

Recommended placement: all of it in `drill.drill_train` (the layer-4 train, drill.py:1862-1947),
with conditions 1, 2, 7 and 8 mirrored as `check(...)` rows in verify_math §20x beside the existing
layer-4 block at verify_math.py:7046-7066, so the invariant is pinned in both modules the way
`section_shortfall` is.

---

## 4. Rulings — `src/assay.py` (2 survivors, both EQUIVALENT)

**The preliminary reading is CONFIRMED, on all points, against the current source.** Both survivors
are `strict=True` inside a `zip` whose two sequences are equal in length by construction, evaluated
only while an exception is already being raised.

### 4.1 assay.py:795 — `zip(order, vals, strict=True)` — EQUIVALENT

Current source, `_check_constants()` (lines 772-974):

```python
790:    order = ["Instrumented", "Witnessed", "Transcribed", "Reconstructed", "Disputed"]
791:    vals = [SIGMA_BY_ATTESTATION[g] for g in order]
792:    if vals != sorted(vals) or len(set(vals)) != len(vals):
793:        raise AssayIntegrityError(
794:            "attestation sigmas are not strictly increasing: %s. Better testimony must never be "
795:            "assigned MORE uncertainty than worse testimony." % dict(zip(order, vals, strict=True)))
```

Every element of the reading checks out:

* `order` is a five-element list literal, bound at line 790, one statement before use.
* `vals` is a **plain unfiltered comprehension over `order`** — no `if` clause, no nesting, no
  `zip`, no slicing. `len(vals) == len(order)` is therefore an invariant of the assignment itself,
  not a property of the table's contents.
* **Nothing reassigns either name between 790 and 795** — they are adjacent lines; there is no
  intervening statement at all. (For completeness across the whole function: `grep` over lines
  770-960 finds exactly one `order =` and one `vals =`, both here. The later loops bind `_i`,
  `_lower`, `_upper`, `_l_axes`, `_u_axes`, `_axis`, `_lo`, `_hi` — none of them shadows `order`.)
* The only way `vals` could fail to be parallel to `order` is a `KeyError` inside the comprehension
  at line 791, which aborts `_check_constants` before line 792 is ever reached.

So `strict` cannot fire on any input, `strict=True` and `strict=False` produce the identical dict,
and the mutant is behaviourally indistinguishable. **No test could ever kill it, and none should be
written for it.** This is a correct, unkillable equivalent mutant — the `strict=` is documentation
of an invariant that the comprehension already enforces, which is a reasonable thing for this file
to carry and not a defect.

### 4.2 assay.py:877 — `zip(order, _floors, strict=True)` — EQUIVALENT

```python
866:    if set(ATTESTATION_FLOOR) != set(order):
867:        raise AssayIntegrityError(... )
875:    _floors = [ATTESTATION_FLOOR[g] for g in order]
876:    if _floors != sorted(_floors) or len(set(_floors)) != len(_floors):
877:        raise AssayIntegrityError(... % dict(zip(order, _floors, strict=True)))
```

Same structure, same conclusion, with one additional belt: `_floors` is again a plain unfiltered
comprehension over the same never-rebound `order` (87 lines later, still the binding from 790 —
verified by grep, no intervening assignment), so the lengths match by construction regardless of
what `ATTESTATION_FLOOR` contains. And separately, line 866 has ALREADY established that
`set(ATTESTATION_FLOOR) == set(order)` and raised otherwise, so the `KeyError` path at 875 is itself
unreachable by the time we get there. Two independent reasons the mismatch cannot occur; `strict`
can never fire. **EQUIVALENT.**

### 4.3 One observation in passing (not a survivor, not asked for)

`ATTESTATION_FLOOR` gets a named key-set guard at line 866 with a message explaining what a renamed
or dropped grade would do. `SIGMA_BY_ATTESTATION` has no equivalent: a grade missing from that table
dies at line 791 with a bare `KeyError` at import time, with no sentence saying what was wrong. The
asymmetry is worth a line in a future pass; it is not a mutation finding and nothing here depends on
it.

---

## 5. Summary table

| file:line | mutation | ruling | one-line reason |
|---|---|---|---|
| prose_gate.py:502 | drop `not` | **GAP** | every real chapter returns 1.0 unchecked; the exempt block ZeroDivisionErrors |
| prose_gate.py:504 | `<` -> `>=` | **GAP** | verdict inverted: compliant refused, deficient filed |
| prose_gate.py:458 | `or` -> `and` | **GAP** | `_entry_class` always None; gate silently dead with no exception on any input |
| prose_gate.py:476 | `is` -> `is not` | **GAP** | charges only the exempt population; dead on chapters, TypeError on feats |
| prose_gate.py:459 | drop `not` | **GAP** | classed entries skipped, classless entries AttributeError |
| prose_gate.py:484 | `and` -> `or` | **GAP** | marker requirement evaporates; scores-without-section now pass |
| prose_gate.py:486 | `and` -> `or` | **GAP** | every non-being entry unconditionally excused; four classes stop being checked |
| prose_gate.py:486 | drop `not` | **GAP** | the template's own Not-applicable sentence is now refused |
| prose_gate.py:484 | 1st `or` -> `and` | **GAP** | a correctly scored Person entry is reported as having no Instrument |
| prose_gate.py:484 | 2nd `or` -> `and` | **GAP** | the "uninstrumented" honest body stops excusing a being |
| prose_gate.py:484 | drop `not` | **GAP** | non-being entries lose their by-nature pass |
| prose_gate.py:483 | `in` -> `not in` | **GAP** | every class becomes a "being"; Places must produce scores |
| prose_gate.py:482 | `or` -> `and` | **GAP** | excuse now requires BOTH phrases; neither honest body works alone |
| prose_gate.py:513 | `or` -> `and` | **GAP** | refusals stop naming which of several hundred chapter jobs failed |
| assay.py:795 | `True` -> `False` | EQUIVALENT | `vals` is an unfiltered comprehension over `order`, never rebound; `strict` unreachable |
| assay.py:877 | `True` -> `False` | EQUIVALENT | `_floors` likewise, and line 866 already pinned the key set |

**14 GAP, 2 EQUIVALENT. No citation drift. The 14 GAPs have one cause and one remedy: nothing in
1,283 verify_math checks or 479 drill nets has ever called `instrument_shortfall` or
`assert_instrument_present`.**
