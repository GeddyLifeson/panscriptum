# SWEEP #34 — BATCH 01 AUDIT

**Module:** `src/verify_math.py` (4,630 lines) — read end to end, in ten passes.
**Auditor:** sweep34-batch01. **Date:** 2026-08-25.
**Standing:** library HALTED (`state/HALT.json`, DRILL_BREACH) — deliberate, untouched.

Every finding below was verified at source, and where the claim was about runtime behaviour it
was verified by running the code (`assay.assay`, `address_space.map_seed`/`assign`,
`read._chunk_key`, `propagation.ascension_years`) rather than by reading it. Nothing here is
"as reported". Anything I could not prove is in QUESTIONS, not FINDINGS.

Two findings (F12, F13) are in other modules. They are here because the evidence that proves
them is in `verify_math.py` and I had to establish it anyway; they are flagged as cross-module
so whoever owns those files is not surprised by the order.

---

## FINDINGS

### F1 — MAJOR — verify_math.py:760-761 — a tautology that cannot fail

```python
check("the map seed is derived from the address, not stored",
      AS.map_seed(_a), AS.map_seed(_a))
```

`address_space.map_seed` is a pure function:

```python
def map_seed(addr):
    """Position-only seed. Retained for worlds with no card yet; prefer seed_from_card()."""
    return int(hashlib.sha256(str(addr).encode()).hexdigest()[:8], 16)
```

`got` and `want` are the same expression over the same argument, evaluated twice against a
sha256. They are equal by construction. The check cannot fail — and it does not test the
property in its label: nothing here distinguishes "derived from the address" from "looked up in
a table keyed by the address". This is the exact shape this file already names as a defect in
its own prose at line 400: *"(An earlier form of this check compared measure_bit_value('M7') to
itself -- a tautology that could never fail.)"*

An AST scan of the whole file for `check()` calls whose `got` and `want` unparse identically
returns exactly three hits: 760, 786, 2902 — F1, F2, F3.

### F2 — MINOR — verify_math.py:786-787 — same shape

```python
check("assignment is deterministic",
      AS.assign("X::a", _T["Alien"]), AS.assign("X::a", _T["Alien"]))
```

`address_space.assign` hashes with `hashlib.sha256(designation.encode("utf-8"))` and packs
fields from `tiers`; there is no clock, no RNG and no `hash()`. Within one process the two calls
are equal by construction and the check cannot fail. The label is closer to honest than F1's,
but a determinism claim that would survive a `PYTHONHASHSEED`-sensitive implementation has to be
made across processes, not twice in one.

### F3 — MINOR — verify_math.py:2900-2903 — same shape

```python
check("the same entity and passage still hit the same key",
      _ck19ah("h.example", "shared passage text", "Goku"),
      _ck19ah("h.example", "shared passage text", "Goku"),
      note="the legitimate half of the cache -- a retry re-asks only what is still missing")
```

`read._chunk_key` is `hashlib.sha256((host + chr(31) + (entity or "") + chr(31) + ch)...)`.
Pure. Cannot fail. The three sibling checks around it (different entity / different passage /
different host, 2895-2911) are real and do their job; this one is decoration.

### F4 — MAJOR — verify_math.py:2597-2601 — an assertion that re-implements the predicate it claims to pin

```python
_flow19ab = {"eval_count": 8, "response": "", "thinking": "Okay, the user just said"}
check("a reasoning model's truncated generation reads as FLOW, not a wedge",
      bool(_flow19ab.get("eval_count")) or bool(_flow19ab.get("response", "").strip()), True,
      note="the exact payload measured on 2026-08-24 that the old predicate called wedged")
```

The `got` expression is `bool(8) or bool("")` over a dict literal written two lines above. It
evaluates to `True` unconditionally. `standards.ollama_token_flow` — the code whose success
predicate this section exists to pin — is never called. The section's own prose (2589-2596) says
the predicate "was the second half of the same fault"; the check above it (2593) greps the
probe's source for `"eval_count"`, which is a spelling test, and this one was supposed to be the
behavioural half. It is instead a restatement of the fixture. If `ollama_token_flow` reverted to
judging flow by `response` alone, both checks in this pair could still read green (the grep
would fail, the behavioural one would not — and the behavioural one is the one a reader trusts).

### F5 — MINOR — verify_math.py:1377, 1853, 1880 — a module global mutated and never restored

Line 1377, in §19d:

```python
_CP.OUT = os.path.join(_cd, "COMPLETENESS.json")
```

No prior value is saved. Every other override in this file is saved and restored — §19d itself
does exactly that for `_CP.HOSTS`, `_CP.RECORDS`, `_CP.category_size_probe` (1332, 1381) and for
`_CP.host_reachable` (1336, 1380). `OUT` is the one that is not.

§19m then does:

```python
1853: _CP_OUT, _CP.OUT = _CP.OUT, os.path.join(_land_dir, "COMPLETENESS.json")
1880:     _CP.OUT = _CP_OUT
```

so its `finally` restores the §19d **temp** path, not `data/COMPLETENESS.json`. For the rest of
the process `completeness.OUT` points into a `tempfile.mkdtemp()` directory. Nothing after §19m
calls `_CP.land`, so there is no live damage today; the hazard is that the next check added
below §19m that touches completeness writes into a temp dir and passes.

### F6 — MINOR — verify_math.py:2255, 2258 — two helper functions silently rebound to data

§19o defines:

```python
2026: def _row(name, n, chars=100):
2031: def _emitted(blocks):
```

§19v, 200 lines later, rebinds both names to values:

```python
2255: _row = {"entity": "E", "entry": {}, "pages": [], "feat_count": 40, ...}
2258: _emitted = sum(len(e["feats"]) for b in _blocks for e in b)
```

Correct today only because no `_row(...)`/`_emitted(...)` call appears after 2255. Any check
added below §19v that reaches for the §19o helpers gets a `TypeError: 'dict' object is not
callable` — in the one file where a crash mid-run truncates the suite (the hazard §20i's own
probe at 3880-3895 exists to defend against).

### F7 — MINOR — verify_math.py:2295, 4222 — a third duplicated section tag, unrecorded

```
2295: # ---- Section 19s: both writers of the metrics ledger stamp a timestamp ---------------
4222: # ---- Section 19s: THE PROSE INTERLOCKS, AT EVERY LAYER, INCLUDING THE OPERATORS ------
```

Two unrelated sections carry the tag §19s. The file's own audit of this exact fault, at 3390,
names only two:

> `(The separate fault that §20e and §20f are each shared by two sections is filed on its own;`
> `renaming a tag is not a print-only change.)`

§19s is a third instance and is not in that sentence, so it is outside whatever order was filed.
The tags are described at 3388 as "the stable identifier" cited by BUGS.md and rigor.py.

### F8 — MINOR — verify_math.py printed ordinals — the sequence run33 said "closes" still has a hole at 19

`grep '^print("19' src/verify_math.py` returns nothing. Line 991 prints `18.`; the next printed
ordinal is line 3054, `20.`. The run33 note at 3383-3391 says:

> `They had drifted into three collisions and a hole: 24, 25 and 26 were each printed twice for`
> `different sections, and 30 and 31 never appeared at all, so a reader grepping the console for`
> `a section number could not land on one. ... the two skipped numbers are the two duplicated`
> `ones, and the sequence closes.`

It does not close: 19 is still absent, and §20k, §20l, §20m, §20n and §20t print no ordinal at
all (their output arrives under §20j's `31.` header). A reader grepping the console for "19." or
for §20t lands on nothing, which is the fault the renumbering was performed to fix.

### F9 — MINOR — verify_math.py:3057-3059 — stale line citations into foreman.py

```
# Two foreman remedies send exactly that signal to read.py -- restart_reader (foreman.py:315,
# wired to "the library's counters are moving" and "corpus read is progressing") and
# kill_stalled_job (foreman.py:385, wired to "every running job is advancing").
```

Verified: `grep -n "def restart_reader\|def kill_stalled_job" src/foreman.py` →
`368:def restart_reader():` and `413:def kill_stalled_job():`. `foreman.py:315` is inside a
docstring paragraph about refusing a kill; `foreman.py:385` is the `except Exception:` /
`silence.note("foreman.py:restart_reader-list")` handler inside `restart_reader`'s body.

### F10 — MINOR — verify_math.py:3322 — stale line citation into publish.py

```
#   public page   (computed by publish.py:168-172, in publish.py's process)  -> "publish.py,read.py"
```

`publish.py:166-174` is the credential-scanner regex (`dop_v1_`, `SG.`, PEM key blocks, JWTs).
The standards computation this line means is `publish.py:330-331`:

```python
330:        import standards as ST
331:        s["standards"] = ST.check(s)
```

### F11 — MAJOR — verify_math.py:3358 — the comment names a call site that does not exist

```
# sweep.load's only call site (sweep.py:129) does no existence check, so a missing evidence cache
# is the normal majority path -- 18,418 of 21,764 swallowed entries on 2026-08-25.
```

`grep -rn "sweep\.load\|_sw21\.load\|sw\.load" src/` returns only this comment and
verify_math's own two probes at 3368 and 3374. `grep -n "load(" src/sweep.py` returns
`68:def load(path)`, four `json.load` calls, and `160: ev, _ = cachekey.load(F.CACHE, host, e["name"])`
— a different function. `sweep.py:129` is `def sweep():`.

So the entire justification for §20e's second half — "this is the 85%", "the expected majority
path" — describes a call that the M23/cachekey migration removed. The two checks at 3366-3378
still exercise a real function and still assert a real split, but the reason a reader is given
for their existence is no longer true, and the reader is being pointed at line 129 of a file
where nothing of the sort happens.

### F12 — MINOR — CROSS-MODULE — sweep.py:68-86 — `sweep.load` has no caller in src/, and its docstring says it has one

Same evidence as F11. `sweep.load`'s own docstring asserts:

```
    THE ABSENT FILE IS THE NORMAL PATH, NOT A FAILURE. The only call site (`:129`) asks for the
    evidence of every Person-category entry in the library and does no existence check first,
```

There is no such call site. The function is reachable only from `verify_math.py`. This is a
curatorial call — delete it, or restore the caller, or record it as a public helper kept for
external use — so it is filed to OWNER rather than repaired.

### F13 — MINOR — CROSS-MODULE — rigor.py:122 — a citation into verify_math.py that has drifted

```
    which split `band_resolution` out for exactly this reason). The code was corrected then and
    pinned by `verify_math.py:382-384`; this worked example was not, ...
```

`verify_math.py:380-384` is the Jensen block:

```python
380: check("integrated P is a genuine probability",
381:       0.0 <= _pa["p_at_least_one_integrated"] <= 1.0, True)
382: check("with no uncertainty the two coincide",
383:       abs(R.prob_at_least_one(math.log10(2.0), 1e-9)["jensen_gap"]) < 1e-6, True,
384:       note="the correction must vanish when there is nothing to correct")
```

The check that actually pins `measure_bit_value` against `band_resolution` is at
verify_math.py:392-396, and §20f re-pins it at 3505-3512. The line-number citation is why §20f's
own repair used derived prose instead of an asserted number; the citation that points at it
never got the same treatment.

### F14 — MINOR — verify_math.py:1598-1603, 3729-3734 — two undeclared swallowed failures

```python
1598: finally:
1599:     try:
1600:         if os.path.exists(_CB.UNRECOGNISED):
1601:             os.remove(_CB.UNRECOGNISED)
1602:     except Exception:
1603:         pass
```

```python
3729: finally:
3730:     try:
3731:         if os.path.exists(_probe20g):
3732:             os.remove(_probe20g)
3733:     except Exception:
3734:         pass
```

Both discard the reason a removal failed. Both are cleaning up a probe file this suite wrote
into the **live** `state/` directory (`state/_VM_UNRECOGNISED_TEST.json` at 1588,
`state/_VM_ATOMIC_PROBE.json` at 3713), so a swallowed failure leaves a stray file in the
directory the dashboard and `standards` read, with no record that it happened. Every other
deliberate swallow in this file carries the project's declaration idiom —
`_ = "silence-exempt: ..."` at 47, 1500, 1635, 2843, 3090, 3186 — and the AST audit that reads
this file cannot tell these two apart from an accident. These two do not carry it.

### F15 — MINOR — verify_math.py:4046-4050 — a floor the file itself documents as unable to catch its own fault

```python
check("every standard the checker declares actually emits a row",
      len({r["standard"] for r in __import__("standards").check(
          __import__("dashboard").state())}) >= 40, True,
      note="run #25 observed 39 where 40 were declared, with the meta-standard still green")
```

Twenty-five lines later, at 4072-4075, the file writes its own verdict on this check:

```
# And `every standard the checker declares actually emits a row` compares the emitted count
# against a HARDCODED 40 rather than against the declared set, so a standard that never emits
# just lowers a number nobody reconciles.
```

The diagnosis is correct and the check was left as it stood. `>= 40` cannot detect a missing
standard once `standards` declares 41 or more; the count is not reconciled against anything.
§20k's response was to add two behavioural checks for the *one* standard that had gone missing,
which does not close the class.

### F16 — MINOR — verify_math.py:2567, 4406, 4441, 4618 — four negative scans with no companion net

This file establishes the rule three times, explicitly:

- 3492-3495 — `check("the guard is actually finding the spawn sites (it has not silently matched nothing)", _guarded20e >= 20, True, note="a parser bug that found zero calls would pass the two checks above vacuously")`
- 3629-3631 — `check("there is still a _via read to guard", len(_all_via) >= 1, True, note="if this ever hits zero the check below passes vacuously ...")`
- 4515-4518 — `check("the scan is actually finding the land_json calls (not silently matching nothing)", _used20q >= 12, True, note="... this is the companion net standing lesson 30 asks for")`

Four scans do not have one:

| line | scan | asserted |
|------|------|----------|
| 2567 | `_ctx_literals` (§19ab, AST: `options`→`num_ctx` integer literal) | `== []` |
| 4406 | `_failopen20p` (§20p, regex: `except ImportError: pass` around the halt check) | `== []` |
| 4441 | `_writes_the_config20p` (§20p, AST: a drill.py function that both names config.yaml and opens for write) | `== []` |
| 4618 | `_callers20t` (§20t, AST: any caller of `escalation.clear`) | `== []` |

Each has a parse-coverage net (`_unparsed19ab`, the `UNPARSEABLE` sentinel at 4579) which
defends against a *broken file*, not against a *broken matcher*. A typo in the matcher — an
attribute name, a constant value, a node type — leaves all four green forever.

§20t is the sharpest case because it was added today and CLAUDE.md's Hard Rule -1 cites it by
name as *the* place the `escalation.clear()` guarantee is asserted. Its own comment (4595-4600)
argues at length that a check nobody can find looks exactly like a check that passed; a check
nobody exercises has the same property. §20i solved this for its own guard by feeding it a
disarmed check in each spelling and requiring it to see them (3959-3968) — that is the pattern
to copy.

### F17 — MINOR — verify_math.py:643-645 — the fixture named `_MAXED` is not maxed

```python
_MAXED = {k: 10.0 for k in ("ruin", "celerity", "reach", "sustain", "continuity",
                            "transgression", "vector", "acumen", "discernment", "suasion")}
```

Ten axes. `assay.WEIGHTS` holds eleven — `volition` is missing. Verified by running:

```
missing axis: {'volition'}
_top (M10, _MAXED)                 -> axis_coverage 0.93, at_ladder_ceiling True, decimal 0.99
_top (M10, _MAXED + volition=10.0) -> axis_coverage 1.00, at_ladder_ceiling True, decimal 0.99
```

The verdicts are the same either way, so no check is currently wrong. But the section is titled
*"ANCHOR VALIDATION — the instrument at floor, standard and ceiling"* and the checks it feeds
read `"the ceiling SATURATES instead of overflowing its notation"` and `"a maxed non-top band
flags promotion"` — and the entity they are asked about is at 0.93 coverage with one axis
unscored. The saturation and promotion behaviour at true full coverage is not tested by name.

### F18 — MINOR — verify_math.py:194-195 — a dead binding, one character from a live module alias

```python
check("arrival(d=1.0) == YEARS_PER_UNIT_DISTANCE",
      P.arrival_years(1.0), C_ := P.YEARS_PER_UNIT_DISTANCE, tol=1e-9)
```

`C_` is bound and never read again (`grep -n "C_" src/verify_math.py` returns only this line and
two `_VM_ATOMIC_PROBE` substring hits). `C` — one character away — is the `cosmography` alias
bound at line 20 and used at 158-186 and 736-745. This is precisely the hazard the file already
records at 1533-1537 about `_here19h` vs `_here19`: *"Two names a character apart doing the same
job is how the stray got here in the first place; run33 spent an audit re-deriving that before
concluding the code was fine."*

### F19 — MINOR — verify_math.py:189-190 — the label claims a property the assertion does not test

```python
check("ascension is distance-independent (no arg)", P.ascension_years(17) > 0, True)
```

`propagation.ascension_years` is `def ascension_years(to_rung=LADDER_HEIGHT)` and returns
`round(float(to_rung) ** RUNG_COST_EXPONENT - 1.0, 1)`. The assertion tests only that the result
is positive; it would pass identically if the function grew a distance parameter tomorrow. The
printed label is what a reader takes away from a green line, and it is claiming a structural
fact nobody checked. The property is trivially assertable from the signature, which is how §19h
pins the same class of claim at 1552-1555 (`list(inspect.signature(...).parameters) == ["models"]`).

### F20 — MINOR — verify_math.py:285-286 — the failure diagnostic silently truncates to three

```python
_problems = D.check_graph()
check("the derivation graph closes (no dangling, rootless, or cyclic quantities)",
      len(_problems), 0, note="; ".join(_problems[:3]))
```

If the derivation graph breaks in twenty places the operator is shown three, with no count and
no ellipsis. The check itself is correct (`len(_problems)` against 0); it is the evidence handed
to the person who has to act on it that is capped. In a file whose §19g exists to refuse
`sorted(...)[:25]`, a `[:3]` on the only diagnostic a failure emits deserves at least an
"and N more".

---

## QUESTIONS

Each of these could be deliberate design. None is filed as an order.

**Q1 — verify_math.py:808-811 — `PR.build_all(limit=400)`.** An internal caller passing a fixed
N to a work-list builder, then asserting `"every profile round-trips to its own address"` over
the 400 it got. The cap is documented two lines above as a deliberate sample
(*"A SAMPLE, and labelled as one: 400 profiles is plenty to prove round-tripping and far cheaper
than the full set. If decode ever breaks it breaks on the first row, not the 40,001st."*), which
is a real argument. But the check LABEL says "every profile", and Hard Rule 0's whole point is
that "we sampled and it was fine" is the sentence that precedes the discovery. Is a fixed sample
in the battery sanctioned, and if so should the label say 400?

**Q2 — verify_math.py:3315/3392 (§20e) and 3502/3554 (§20f).** Both tags are shared by two
sections. The note at 3390 says this is "filed on its own". Is that order still open, and does
it cover F7's §19s too? I did not file a duplicate.

**Q3 — verify_math.py:1588 and 3713 — the suite writes probe files into the live `state/`.**
`state/_VM_UNRECOGNISED_TEST.json` and `state/_VM_ATOMIC_PROBE.json` are created in the real
state directory the dashboard polls. §20n at 4174-4177 states the opposing principle in as many
words: *"writing a probe shard into state/sweep_shards/ to test the reader would make the test a
writer of the very state it audits."* Both files are removed in a `finally` (whose failure is
swallowed — see F14), and both are `_VM_`-namespaced. Deliberate exception, or the same drift
one directory over? A `tempfile.mkdtemp()` would work for both, as it does for the other twelve
probes in this file.

**Q4 — verify_math.py:4574 — §20t's exemption list.** `if not _f20t.endswith(".py") or _f20t in
("escalation.py", "drill.py"): continue`. The reasoning at 4602-4605 is sound (escalation.py
owns `clear`; drill.py attacks it deliberately). The consequence is that a `clear()` caller
added to drill.py is structurally invisible to the assertion CLAUDE.md points at. drill.py is
also model-editable. Is a narrower exemption — e.g. only inside functions named `_no_programmatic_*`
— worth the complexity, or is the runtime guard inside `clear()` (4608-4610) considered to cover it?

**Q5 — verify_math.py:47-57 — `_raises` catches `Exception`, so a `SystemExit` refusal is
invisible to it.** Three sites work around this with hand-rolled try/except:
`_capped` at 1497-1502, `_refuses_cap` at 1633-1640, `_packreq` at 2166-2175. Three copies of one
predicate is the shape §20d was written to collapse (`pipeline.entry_settled`). Should `_raises`
take an expected-exception argument instead? I did not file this because it is a design call and
because the three copies each carry a correct silence-exempt declaration.

**Q6 — the FAILING check.** `verify_math.py:4193-4197` (`"the live sweep proves its own
completeness"`, `_SP20n.missing(_run20n) == []`) is this sweep's own completeness proof and is
the one FAIL in the current run. Not chased, per the brief; my `sweep_plan.record` call for
`verify_math.py` is filed.

---

## COVERAGE

`verify_math.py` — 4,630 lines, read in full. Recorded via
`sweep_plan.record('run34', ['verify_math.py'], batch=1)`.
