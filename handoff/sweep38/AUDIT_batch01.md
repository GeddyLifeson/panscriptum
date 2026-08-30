# SWEEP 38 — AUDIT, batch 01

**Agent:** sweep38-batch01 · **Module:** `src/verify_math.py` (read IN FULL) · **2026-08-29**

---

## 0. The file moved while I was reading it

Recorded because the brief asked for it, and because it changes what a later reader should
trust about the line numbers below.

| when | lines | md5 |
|---|---|---|
| brief written | 7,515 | — |
| my first read began, 23:40 | 7,655 | `dd9149fa9ac18287aa8ee53b8a17a68b` |
| 23:44, mid-audit | 7,710 | `10a35a67f943ebfa0c3621650e589a2d` |

Three insertions landed between my read and my analysis, all one repair: a new module-level
helper `_slices_of(src, name)` at **:122-139**, and its two call sites replacing literal greps
at **:3790** (`overnight.py` / `did[:5]`) and **:6292** (`scope.py` / `titles[:8]`). Both of
those rows had gone red against clean code because the target module's *comment recording the
fix* contained the forbidden literal. That is the repair the brief said was in hand, and it is
the same defect family this audit is about — so the region was **re-read at the new revision**
and every line number in this document is against the 7,710-line revision.

`_slices_of` itself carries a new defect; see finding 3.

## 1. Battery state observed (not filed — repair in hand)

`python src/verify_math.py` on the pre-edit revision: **1,055 passed, 2 FAILED** (plus the one
deliberately-failing scrubbed probe at :4569, which is not a failure).

- `b68ca666da79: scope.py no longer truncates fetched titles to 8` — **already repaired** by the
  23:44 edit.
- `[d9b895708c45] every standard standards.py declares actually emits a row` — got
  `['the local model has a live runner', 'the resident runner serves the context this project
  asks for']`; both are Ollama-liveness standards and the daemon is not answering.

Not filed, per the brief.

## 2. A live OWNER-rung halt is standing

Encountered while probing §20p. `escalation.assert_clear()` raises:

```
code     : DRILL_BREACH
what     : 1 safety net(s) did not hold: a routine resync cannot silently un-exclude a source
raised by: drill.py
```

I did not cause it and I have not touched it. Hard Rule -1: a fault you merely FOUND leaves the
halt standing. Flagged here so it is not mistaken for background noise.

---

## 3. FINDINGS

### 3.1 MAJOR — §20i's disarm guard is blind to half the file it guards

`src/verify_math.py:4585-4608, 4633-4657`

The row *"no check in this file is disarmed with a trailing always-true disjunct"* is the guard
the whole battery rests on: it is what stops somebody quieting a failing row with `or True`. It
works by whitespace-collapsing this file's own source and searching for three needles:

```python
_needles20i = (" or True, True,", " or 1, True,", " or True), True,")
```

**Every needle requires a comma after the `want` argument.** A disarmed row written
`check("x", expr or True, True)` — no `note=`, no `tol=` — collapses to `... or True, True)` and
matches nothing. Measured on the current revision: **211 rows close `, True)` and 207 close
`, True,`**, so the guard is blind to slightly over half of the shapes it is pointed at.

Reproduced (`scratchpad/sweep38/batch01/needle_probe.py`), guard logic copied verbatim:

| spelling | matched? |
| --- | --- |
| `check("x",\n  value == other or True,\n  True, note="x")` — the file's own fixture | ` or True, True,` |
| `check("x", value == other or True, True, tol=1e-9)` | ` or True, True,` |
| **`check("x", value == other or True, True)`** | **NOTHING** |
| **`check("x",\n  value == other\n  or True, True)`** | **NOTHING** |
| **`check("x", (value == other or True), True)`** | **NOTHING** |
| **`check("x", value == other or 1, True)`** | **NOTHING** |
| control: `check("x",\n  value == other,\n  True, note="x")` | NOTHING (correct) |

The section's own comment already says the guard read green for nine runs while blind to the
*wrapped* spelling, and adds "a detector nothing ever trips is not a detector" — then supplies
two positive-control fixtures (`_disarmed20i`, `_ordinary20i`) that **both carry `note="x"`**,
so they exercise only the trailing-comma spelling. The controls cannot see the blind spot
because they were written in the one shape that is not blind.

**Remedy (in the order):** ask the parse tree, as §20q/§20t/§20p already do. For every
`check(...)` Call in this file's own AST, flag any `got` that is an `ast.BoolOp(Or)` with a
constant-truthy operand, or a bare truthy `ast.Constant`. That is formatting-independent, needs
no runtime-assembled needles, catches `or 1` / `or "x"` / parenthesised forms, and subsumes the
`check(label, True, True)` literal tautology that order `96c4be60fb92` had to find by hand. I
ran exactly that predicate over the current file: **0 hits**, so the replacement lands green.

### 3.2 MAJOR — §20p's Hard Rule -1 interlock rows both stay green when the interlock is deleted

`src/verify_math.py:5205-5219`

Two rows guard the plant-wide halt interlock in eight jobs:

```python
check("no job swallows a missing escalation module", _failopen20p, [], ...)         # A
for _f20p in _INTERLOCKED:
    check("%s refuses to start when the chain is unimportable" % _f20p,
          "REFUSING TO" in _src20p(_f20p), True, ...)                               # B
```

Row A is a regex for the *specific* fail-open shape `except ImportError:\n    pass`. Row B is a
whole-file substring search for the words `REFUSING TO`. Between them they are supposed to
establish that each of the eight jobs refuses to start when `escalation.py` cannot be imported.

They do not, because **neither row sees the interlock being simply removed**, and row B is
satisfied by any refusal message in the file for any reason:

| module | total `REFUSING TO` strings | of which the escalation interlock |
|---|---|---|
| dashboard, feats, foreman, overwatch, pipeline | 1 | 1 |
| overnight | 2 | 2 |
| **publish.py** | **5** | **1** |
| **read.py** | **2** | **1** |

`publish.py` also says REFUSING TO RENDER (`:969`), REFUSING TO PUSH about `ledger_guard`
(`:1144`), REFUSING TO PUSH about the mutation interlock (`:1168`) and REFUSING TO PUSH about an
active mutation run (`:1192`). `read.py` also says REFUSING TO READ about the host map (`:1155`).

Reproduced (`scratchpad/sweep38/batch01/repro_20p.py`) — scratch copies only, `src/` untouched.
The escalation `raise SystemExit("REFUSING TO START: the escalation chain …")` block is deleted
and replaced with `pass`:

```
publish.py    GUTTED  -> {A finds fail-open: False,  B 'REFUSING TO' present: True}
              verdict : STILL GREEN (safety removed, battery silent)
read.py       GUTTED  -> {A finds fail-open: False,  B 'REFUSING TO' present: True}
              verdict : STILL GREEN (safety removed, battery silent)
pipeline.py   GUTTED  -> B False  -> caught
foreman.py    GUTTED  -> B False  -> caught
```

`publish.py` is the job that pushes to the public repo and `read.py` is the corpus reader; those
are two of the worst two to have unguarded. The six that *are* caught are caught only by the
accident that they carry no second refusal string — adding one unrelated `REFUSING TO` message
to any of them silently retires that module's row too.

This is the section that exists because "`except ImportError: pass` … switched the plant-wide
halt off in eight jobs at once, quietly", and CLAUDE.md's Hard Rule -1 names `verify_math` as
where that guarantee lives.

**Remedy (in the order):** assert it off the parse tree, the way §20t already does for
`escalation.clear()`. For each of the eight modules: locate the `Try` whose body imports
`escalation`, and require (i) every handler on it to contain a `Raise`, never a bare `Pass` or a
log-and-continue, and (ii) the module to call `_ESC.assert_clear(...)`. Add the house positive
control (§20s's canary convention): a synthetic gutted module must be reported, or the scan is
matching nothing.

### 3.3 MINOR — `_slices_of` is strictly weaker than the grep it replaced, and its docstring overclaims

`src/verify_math.py:122-139` (added 2026-08-29, this evening)

```python
def _slices_of(src, name):
    """Every `name[...]` SLICE in `src` that is real code, as source segments."""
```

The walk matches only `Subscript` nodes whose `.value` is a bare `ast.Name`:

```python
if (isinstance(_n, _ast0.Subscript) and isinstance(_n.slice, _ast0.Slice)
        and isinstance(_n.value, _ast0.Name) and _n.value.id == name):
```

So `self.did[:5]`, `led.did[:5]` and `obj.get("did")[:5]` are all invisible. Verified against a
synthetic module: of `did[:5]`, `self.did[:5]`, `obj.get('did')[:5]`, `(did)[:5]`, the helper
finds the first and last only.

The literal grep it replaced — `"did[:5]" in _on20code` — **did** match `self.did[:5]`, because
the substring is present. So tonight's fix, which is right about prose, gives up real coverage
in the other direction while the comment above it claims the AST form is "strictly stronger than
the string scan in the other direction too". Two of the three sentences are true; that one is
not, and the docstring's "Every `name[...]` SLICE" is not either.

Cheap: also accept `ast.Attribute` whose `.attr == name`, and correct the two claims.

### 3.4 MINOR — §20p's halt-marker row is `X == X` whenever the library is not halted

`src/verify_math.py:5300-5305`

```python
check("the marker allsweep reads a halt by is the sentence escalation actually raises",
      (_alls20p._HALT_REFUSAL in _msg20p) if _msg20p else "no live halt to check against",
      True if _msg20p else "no live halt to check against", ...)
```

When no halt stands — the normal state, and the state the library is meant to be in — `got` and
`want` are the same string literal and the row cannot fail. Its own note concedes this
("when a halt IS standing this compares them for real"). It happens to be comparing for real
tonight, only because a `DRILL_BREACH` halt is up (§2 above).

It need not be conditional at all: `allsweep._HALT_REFUSAL` is `"THE LIBRARY IS HALTED"` and
that exact sentence is a string literal in `escalation.py`. Promote it to a named constant in
`escalation.py`, have `allsweep` import it, and the row becomes an unconditional identity check
that no coincidence can satisfy. Alternatively drive `escalation` against a scratch HALT path so
a synthetic halt is always available. Either way the row stops depending on the library being
broken in order to mean anything.

### 3.5 MINOR — a prose-proximity row that turns on character distance

`src/verify_math.py:7199-7204` (`_b5_backfill_cap_visible`)

```python
check("the comment no longer claims the ranked list is 'NOT truncated' next to a cap that "
      "truncates it",
      "NOT" in src_txt and "truncated" in src_txt
      and "if cap:" in src_txt.split("truncated")[-1][:40],
      False, ...)
```

Measured against the live `backfill.backfill_source`: `"NOT"` occurs once, `"truncated"` once —
both in the comment at its `:35` that *records the fix*:

```
# f35826ab7a3f: this used to say "NOT truncated" directly above the cap two lines down,
```

and `if cap:` is 22 lines later, so the 40-character tail after the last `truncated` is
`'" directly above the cap two lines down,'` and the third conjunct is False. **The row passes
today for a reason unrelated to what it claims.** Move `if cap:` up and it goes red against
clean code; reintroduce a genuinely false "NOT truncated" claim 41 characters above `if cap:`
and it stays green. The `[-1]` also means only the *last* occurrence of `truncated` is ever
examined.

The two rows around it are behavioural and sound (`cap` defaults to `None`; the return dict
carries the pre-cap `absent`). Recommend retiring this one rather than tuning the window: it
cannot distinguish the fault from the record of the fault, which is the same trap §20b, §20p and
tonight's `_slices_of` repair were each written to escape.

### 3.6 MINOR — two rows share a label, so a FAILED dump cannot name which one broke

`src/verify_math.py:1435` (§19c, `pipeline.land_json`) and `:1569` (§19d, `completeness.land`)
both read `check("and no .tmp is left behind", …, False)`. The end-of-run dump prints only the
label, so either failure renders identically. This is §20y's section-tag collision one level
down — and §20y exists precisely because "a duplicated tag makes every existing citation resolve
to a coin flip". Rename one (e.g. `"and land_json leaves no .tmp behind"`).

Scanned the whole file: this is the **only** duplicated label among 936 rows.

### 3.7 INFO — a row advertises a tolerance it does not get

`src/verify_math.py:167-169`

```python
check("KE relativistic @ 0.5c uses gamma", round(PH.kinetic(1.0, 0.5 * 2.99792458e8)),
      round((gamma - 1) * 1.0 * 2.99792458e8 ** 2), tol=1e-9, ...)
```

`round(x)` with one argument returns an `int`, so `check()`'s `isinstance(want, float)` branch is
not taken and the comparison is exact `==`; `tol=1e-9` is silently discarded. The row passes, and
exact equality is stricter than intended rather than looser, so nothing is presently wrong — but
two integers near 4.6e16 are being compared bit-for-bit under a label that says otherwise, and
the next reader will believe the tolerance is live. This is the only one of the 68 `tol=` rows
where `want` is provably not a float.

---

## 4. QUESTIONS (possibly deliberate)

**Q1. `_b5_onomast_doctrine_counts`'s `str(n) in doc` disjunct is dead, and near-vacuous for
small counts.** `src/verify_math.py:7027-7037`. The rows read
`str(earth) in doc or _b5_spelled(earth) in doc`. Measured live: earth=26, moon=15, mars=14, and
**none of `"26"`, `"15"`, `"14"` appears anywhere in `onomast.__doc__`** — the rows pass entirely
on the spelled forms from `_NUM_WORDS_b5`. So the numeric disjunct contributes nothing today, and
`_b5_spelled` already falls back to `str(n)` for an unmapped `n`, which makes it redundant by
construction. The concern is what it becomes if a count ever lands in single digits: `"3" in doc`
matches almost any prose. Two readings: (a) the disjunct is belt-and-braces against the docstring
choosing digits over words, and is fine; (b) it is a hole that only today's values keep shut.
Owner's call on which, since it turns on how the doctrine prose is meant to be written.

**Q2. Should the whole-file literal-grep family be converted wholesale, or left to attrition?**
Not filed as a finding, because I measured it and it is **not a live defect**. I extracted all 67
substring-membership tests used as a `got` inside `check()`, took the 48 presence assertions
against a whole-module source, and asked of each whether the needle also occurs with comments and
docstrings removed. **Exactly one is satisfied by prose alone** — `"_pool_answer_usable" in
_cb_src` at `:7506`, whose label is *"cascade_bridge.py docstring names where real validation
happens"*, i.e. the docstring is deliberately the subject. Every other presence grep is currently
anchored in real code, and the eight `"REFUSING TO"` rows are too (finding 3.2 is about deletion,
not about prose). So the family's *fragility* is real and well documented — nine orders have
already been filed against instances of it, and two more were converted tonight — but there is no
second silent-green row hiding in it right now. Whether to keep converting them one incident at a
time or do the remaining set in a single pass is a judgment about queue cost, not a defect.

---

## 5. What I checked and found clean

Recorded so that *clean* is distinguishable from *unread*.

- **Self-comparison tautologies.** AST scan for a `check()` whose `got` and `want` are the same
  source expression, and for a `Compare` inside `got` whose two sides are the same source
  expression: **0 of each**. The `f(x) == f(x)` family that orders `3f86c571da58`,
  `fbdb7fe3bd4c` and `cc500a6cbf4b` were filed against is fully cleared.
- **Literal-`got` tautologies** (`check(label, True, True)`, order `96c4be60fb92`'s shape): 3
  rows have a constant `got`, and all three are deliberate — the scrubbed non-numeric probe at
  `:4569` (`None` vs `1.0`) and the two `check(..., False, True)` fold-back rows at `:7609`/`:7612`
  that report another file's harness failures by construction.
- **Always-true `got` expressions** (`or True` and friends, by AST rather than by needle): **0**.
  The blind spot in finding 3.1 is currently unoccupied — the guard is broken, not evaded.
- **Restore discipline.** Every module-global override I traced is stashed and restored: §9's
  `CU.CUSTODES`, §18b's six-tuple, §19d's `_CP.HOSTS/RECORDS/probe/host_reachable/OUT` (with the
  explicit fix-up row at `:1587` for the one that used to leak), §19m's `silence.replace_retry`,
  §19x's `_OW.LEDGER`, §19ac's `_TUNx.profile`, §19ad's `_GLx.LANE/_BEAT_SECONDS`, §19ae's three
  tuning hooks, §20r's `SIGMA_BY_ATTESTATION`/`BAND_EDGES`/`_RHO_CACHE`/`A.assay`, batch3's
  `builtins.open`, batch5's `F.api`/`WS._api`. §20r even asserts the restoration
  (`:5847 "and assay() itself was put back"`, `:5734 "the edge table was put back exactly"`).
- **Temp-directory hygiene.** Order `af447d21d634`'s `_mkdtemp_vm` + `atexit` sweep is in place
  at `:1317-1327` and the sites route through it; the three that do not (`:2931` tokenflow,
  `:4008` corrupt-cache, `:7470` runguard) each remove their own.
- **Probe files written into live `state/`** (`_VM_UNRECOGNISED_TEST.json`,
  `_VM_ATOMIC_PROBE.json`) are both removed in `finally`, and both record a `silence.note` if the
  removal fails rather than swallowing it.
- **The `--help` short-circuit** at `:27-31` genuinely precedes the sibling imports, so the
  IMPORT-tier timeout it was written for cannot recur.
- **`check()`'s own guard** (`:89-93`): non-numeric `got` against a float `want` records a FAIL
  instead of raising, and §20i at `:4560-4580` exercises it and scrubs the probe from the tally.
- **The four negative scans** (`_ctx_literals`, `_failopen20p`, `_writes_the_config20p`,
  `_callers20t`) each have the positive control order `873330d2e98d` asked for, and
  `_writes_the_config20p`'s calls the real function rather than a copy.
- **Section-tag uniqueness** (§20y) recognises all three header spellings and its floor
  (`>= 55` against 62) is set below the true count deliberately, with the reasoning written down.

---

## 6. Coverage

`sweep_plan.record('run38', ['verify_math.py'], batch=1)` — see the run log.
