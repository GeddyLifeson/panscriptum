# Sweep run44 — batch 02 audit

**Module read in full:** `src/verify_math.py` (9,281 lines)
**Date:** 2026-09-04

Every finding below was verified against the source lines quoted, and the four empirical claims
(the continuation predicate, the tautology scan, the prose-ratchet coverage, the section-tag
scan) were re-measured by standalone scripts that read `src/` and import nothing from it.
`src/` was not modified.

---

## Summary

| Severity | Count |
|---|---|
| MEDIUM | 4 |
| MINOR | 3 |
| QUESTION / INFO | 5 |

Nothing here is a live wrong answer. Three of the four MEDIUM findings are the same shape the
file itself polices most fiercely: a check that, when the thing it guards actually breaks,
does something other than go red — it goes green (F1), or it takes the whole battery down with
a traceback so no row prints at all (F2, F3).

### Verified clean

Stated because absence of a finding is only useful if somebody says they looked:

* **No self-comparison tautologies survive.** An AST scan over all 1,002 `check()` call sites
  found zero rows whose `got` contains a textually-identical `X == X`, and zero rows whose
  `got` and `want` are textually identical. The four historical instances (`map_seed`,
  `assign`, `_chunk_key`, `measure_bit_value`) are all genuinely repaired.
* **No duplicate section tags.** The §20y scan run independently reports 67 distinct tags
  across 46 banner / 22 print / 4 dashed headers, with no collisions.
* **The twelve raw-source needles that F4 shows are unexamined are all backed by real code
  today.** F4 is a latent hole in a ratchet, not a live false-green.

---

## MEDIUM

### F1 — `_follows_continuation` does not test what its docstring says, and the Hard Rule 0 row that rests on it can pass over the exact defect it names

`src/verify_math.py:4073-4099`, consumed at `src/verify_math.py:4102-4106`.

```python
def _follows_continuation(src):
    """Does any loop in this module read a `continue` token and re-submit it? -> bool.

    Structural on purpose: it asks for a loop that both READS `...continue...` and later writes
    that value into something it sends. Reading the token without resubmitting is precisely the
    defect this replaced -- counting the evidence of truncation while still truncating.
    """
```

The predicate:

```python
        reads = "'continue'" in body or '"continue"' in body or "continue_" in body
        # A resubmission looks like updating the outgoing params/dict with the token, which in
        # ast terms is a subscript assignment or an .update() call inside the same loop.
        resubmits = any(isinstance(n, (_ast19.Subscript,)) for n in _ast19.walk(node)) and \
            any(isinstance(n, _ast19.Call) and getattr(n.func, "attr", "") == "update"
                for n in _ast19.walk(node)) or \
            any(isinstance(n, _ast19.Assign) and any(isinstance(t, _ast19.Subscript)
                                                     for t in n.targets)
                for n in _ast19.walk(node))
        if reads and resubmits:
            return True
```

`resubmits` never establishes any relationship between the token that was read and the value
that gets written. It is satisfied by *any* subscript assignment anywhere in the same loop, for
any reason. The docstring's stated discriminator — "later writes **that value** into something
it sends" — is not implemented.

**Measured.** Feeding the real predicate a loop that reads the continue token and deliberately
never resubmits it:

```python
def f(params):
    out = {}
    while True:
        d = api(params)
        n = len(d.get('continue') or {})
        out['count'] = n          # unrelated subscript assignment
        if not n:
            break
    return out
```

returns a hit. That is precisely "counting the evidence of truncation while still truncating" —
the shape the docstring says the function exists to refuse. Against the live `feats.py` the
predicate fires on one loop (line 824, which is genuinely correct today), while 8 of the 39
loops in that file satisfy `resubmits` on their own.

**Why it matters here rather than as a style note.** The consuming row is a Hard Rule 0 guard:

```python
check("the discovery caps are measured rather than argued about",
      '_CAP_BOUND' in _ft19code and _follows_continuation(_ft19), True,
      note="m82: MediaWiki's own continue token says when aplimit/srlimit withheld results. "
           "Checked structurally -- a loop that reads the token AND resubmits it -- so that "
           "renaming the helper does not turn this red and a comment cannot turn it green")
```

The note makes the same claim the docstring does, and the code does not keep it.

**Second half of the same finding: there is no negative control.** This file's own house rule,
stated at `:277-281` and applied four more times at `:6582-6600`, is that every scan needs one:

> BOTH DIRECTIONS ARE CONTROLLED -- a positive control alone still passes if the predicate
> regressed to matching everything, which is how a sibling row in this file actually failed.

`_follows_continuation` is asserted `True` and has no fixture at all — neither a positive
control proving it can still find a real continuation loop, nor a negative one proving it can
still refuse a fake. It is the only AST predicate added to this file since order 873330d2e98d
without a control beside it.

**Confidence: high.** The behaviour is reproduced directly against the shipped function.

---

### F2 — §19ai subscripts a value that is `None` whenever the standard it measures stops being emitted, so a vanished standard crashes the battery instead of reddening a row

`src/verify_math.py:3633-3667`.

```python
def _pool19ai(buckets):
    """Run the real standards.check() over a synthetic throughput window."""
    ...
    for row in _STx.check(st):
        if row["standard"] == "calls that succeed":
            return row
    return None


_dead19ai = _pool19ai([])
check("a pool that answered NOTHING does not report a passing success rate",
      _dead19ai["holds"], False, ...)
```

Six sites subscript the result with no guard: `:3647`, `:3650`, `:3653`, `:3655`, `:3663`,
`:3667`.

A standard that stops emitting is not a hypothetical here — it is the failure class this file
devotes two whole sections to. §20k (`:5192-5224`) was written because
`sentences that survive the verbatim check` "had never once been evaluated in its whole life…
It did not read green; it was ABSENT". Order 5b85ab54b176 (`:7153-7233`) exists because roughly
twenty standards could delete themselves by failing to read their input. If `calls that succeed`
joins them — renamed, or moved behind a `try` whose handler drops it — `_pool19ai` returns
`None`, `None["holds"]` raises `TypeError` at module level, and the consequences are exactly the
ones this file names elsewhere in its own words (`:6083-6089`):

> RESULT would never print, `sys.exit(1)` would never run, and allsweep would grade verify_math
> BROKEN rather than red.

The house idiom for this is already established and used at `:1786`, `:1836`, `:3351`, `:7277`,
`:7389`, `:8997` — `X[0][...] if X else <sentinel>`, which turns the same event into a named
FAILED line. §19ai did not adopt it.

**Confidence: high** for the mechanism; the trigger condition is a future regression, not a
present one.

---

### F3 — the control row for the disarm detector crashes rather than reddens when the detector it controls breaks

`src/verify_math.py:5080-5083`.

```python
check("a red guard NAMES the row it caught, rather than saying only True != False",
      _disarmed_rows20i('check("the label it must report", x or True, True)')[0][2],
      "the label it must report",
      note="the reason this returns a list of (line, why, label) instead of a boolean")
```

`[0][2]` is unguarded. This row's entire job is to prove that `_disarmed_rows20i` still finds a
disarmed check and still names it. If the predicate regresses to matching nothing — which is the
failure the block's own comment at `:5047-5052` says it was added for ("the check above read
green for nine runs while blind to the wrapped spelling") — the list is empty, `[0]` raises
`IndexError`, and the battery dies at that line. A control that cannot report its own subject's
failure as a failure is worse placed than an ordinary row.

The same unguarded shape appears at:

| Line | Expression | Empty-input outcome |
|---|---|---|
| `:1182` | `max(len(r["profile"]) for r in _rows)` | `ValueError` |
| `:1211` | `_rows[0]["address"]` | `IndexError` |
| `:1341` | `_bs[-1]["population"]` | `IndexError` |
| `:1351` | `max(_cls, key=_cls.get)` | `ValueError` |
| `:2624-2627` | `_spans[0]` / `_spans[-1]` | `IndexError` |
| `:2855` | `max(len(json.dumps(...)) for b in _blocks for e in b)` | `ValueError` |
| `:7111` | `_printed2_b3_1230.split("WORST COVERED WITH A HOST", 1)[1]` | `IndexError` |
| `:8794` | `sorted(_RF20aa.REFERENCE)[0]` | `IndexError` |

Each of these is a subject returning nothing — a packer that stops packing, a burg roll that
stops rolling, a report that stops printing its header — which is a finding, and in every case
the finding arrives as a crash rather than as a row. The file states the cost of that at
`:2817-2818` and again at `:2844-2845` and `:8326-8327`: "which in a battery reads as a crash,
not as a failing check."

**Confidence: high** for the mechanism.

---

### F4 — §20z's prose-backed ratchet claims to have pinned its own blind spot, and has not

`src/verify_math.py:9182-9255`.

The check:

```python
check("and the bindings it cannot resolve to a file are still the same four",
      _unres20z, ["_probe_src19ab", "_src20g", "_t", "src_txt"],
      note="THE UNEXAMINED HALF, PINNED so it cannot grow in silence. ...")
```

and the enumeration above it at `:9143-9149`:

```
# WHAT IT DOES NOT EXAMINE, said out loud rather than left as an implied all-clear:
#   * REGEX searches ...
#   * bindings whose target file is not a literal in the binding line ...
#   * anything that is not a Python module ...
```

The selector inside `_prose_backed20z`:

```python
        if not (isinstance(_c, _ast20p.Compare) and len(_c.ops) == 1
                and isinstance(_c.ops[0], (_ast20p.In, _ast20p.NotIn))
                and isinstance(_c.left, _ast20p.Constant)
                and isinstance(_c.left.value, str)
                and isinstance(_c.comparators[0], _ast20p.Name)):
            continue
```

A membership test whose right operand is anything but a bare `Name` is dropped by `continue`
before `_unresolved` is ever touched. It is therefore neither examined nor counted, and the
"PINNED so it cannot grow in silence" claim does not cover it.

**Measured over this file:** 111 substring tests have a bare `Name` on the right (the examined
population); **65 do not and are silently skipped**. Most of those 65 are harmless — they test a
live function's return value, not a module's source text. But roughly a dozen are exactly the
row shape order 13357b913e3e was filed about, reading a target module's raw file text:

| Line | Row |
|---|---|
| `:2135` | `"every pool failure is recognised" in open(.../standards.py).read()` |
| `:2564` | `"key=lambda r: (regs.count(r), r)" in open(.../navtree.py).read()` |
| `:2909` | `'"at": round(t0, 1), "tag"' in _mx_src["pipeline"]` |
| `:2912` | `'"at": round(t0, 1)' in _mx_src["cascade_bridge"]` |
| `:4788` | `"silence.write_json" in _atomic_src[_m20g]` (weave, generate, feats) |
| `:4790` | `'open(OUT_GROUPS, "w"' in _atomic_src["weave.py"]` |
| `:4793` | `"silence.replace_retry(_tmp, REPORT)" in _atomic_src["overwatch.py"]` |
| `:4851` | `"d.lower() for d in DENYLIST" in open(.../local_agent.py).read()` |
| `:4861` | `'reverted = False' in open(.../local_agent.py).read()` |
| `:5956` | `"exited without a traceback" in _src20p("allsweep.py")` |
| `:8276` | `"no catalogue record on disk for this source" in open(.../completeness.py).read()` |
| `:8283` | `"UNREACHABLE in closed batches" not in open(.../health.py).read()` |

Two distinct sub-shapes escape: a dict subscript (`_atomic_src[...]`, `_mx_src[...]`) and an
inline `open(...).read()` call used directly as the comparator instead of being bound to a name
first. Neither is in the "said out loud" list.

**I checked whether any of them is currently green off prose, and none is.** Blanking comments
and docstrings from each target module and re-testing every needle: all ten presence-asserting
needles survive in code, and both absence-asserting needles are genuinely absent from the raw
file too. So this is a hole in the ratchet, not a live false claim about the library.

The load-bearing part is the note. A row that says the unexamined set is four names, when it is
four names plus every membership test that does not happen to bind its source to a variable
first, is the file's own signature failure — a measurement written down once and then relied on.

**Confidence: high.** Both the selector behaviour and the 111/65 split were measured directly.

---

## MINOR

### F5 — module-level cross-type rebind of `_a` and `_b` at §20u

`src/verify_math.py:8407`.

```python
for _a, _b in _it.combinations(_names, 2):
    _d, _ = _PRg.shortest(_g, _a, _b)
```

`_a` is bound at `:1025` to §13's packed 74-bit address (`_a = AS.pack(0, 2, 3, 11, 40, ...)`,
an `int`) and read through `:1082`. `_b` is bound at `:880` to §11's score dict and read through
`:914`, then already rebound at `:6432` to a band-name string. Both are rebound here to source
designation strings.

This is the identical hazard the file enumerates at `:8320-8334` and repaired seven times
(`_ap36`, `_cand19h`, `_rows19h`, `_rows19m`, `_ok19k`, `_r19d`, `_one20r`/`_two20r`; also
`_CBud` at `:2813-2818` and `_PRg` at `:8396-8398` in this same section). Its own words:

> the arrangement is correct only by the ACCIDENT that nothing reads the earlier binding after
> this point, and any check added in between would raise TypeError and truncate the suite at
> that line

That accident holds today — verified, nothing reads either name after `:8407` — which is why
this is MINOR and not MEDIUM. It is also the two shortest, most collision-prone names in the
file, in a section that renamed `PR` to `_PRg` eleven lines earlier for exactly this reason.

---

### F6 — five diagnostic truncations survive in failure output

The class §7 repaired at `:538-545`:

> This note was `"; ".join(_problems[:3])`, so the ONE diagnostic this check emits showed three
> problems and silently dropped the rest… Hard Rule 0 in the place it does the most damage:
> inside the failure message of the check whose whole job is to enumerate what is broken.

An AST scan for literal head-slices as code in this file returns eight, of which five are in
failure output:

| Line | Slice | What it cuts |
|---|---|---|
| `:5390` | `str(r["observed"])[:60]` | the `got` argument of a check, not just its note |
| `:8464` | `str(_e36)[:160]` | the exception text explaining why a run35 check file failed to load |
| `:8478` | `str(_e36)[:200]` | the exception text from a failing `check_*` function |
| `:8490` | `str(_label36)[:70]` | **the label** of a folded-in run35 failure |
| `:8491` | `str(_row36)[:200]` | that failure's detail |

`:8490` is the sharpest. §20z's own row at `:9036-9039` argues that "the label is the ONLY
identifier a FAILED line carries" — and here a failure imported from `handoff/run35/checks_L*.py`
is reported under a label cut at 70 characters. Two such failures sharing a 70-character prefix
would also collide in the duplicate-label check, which would then redden for the wrong reason.

(The other three literal slices — `:2452` `_rows19m[:3]`, `:5881` `n.args[1].value[:1]`,
`:7963` `(res.get("sample") or [])[:3]` — are fixture construction and a mode-string test, and
are correct.)

---

### F7 — three teardowns reset shared module state to a hardcoded literal instead of restoring the saved value

| Line | Teardown |
|---|---|
| `:2957` | `_RD._GATE_STATE.update({"at": 0.0, "regime": "cloud"})` |
| `:3472` | `_TUNx._CACHE.update({"at": 0.0, "regime": None, "why": ""})` |
| `:2536` | `_OW._SNAPSHOT["digest"] = None` |

None of the three saves what was there before overriding it; each writes a chosen value in its
`finally`. Every other override in this file saves and restores by value or by identity, and
§19d carries a long comment (`:1748-1758`, `:1841-1849`) on precisely the damage a teardown that
does not put back the original does to every later section.

**Reported as MINOR rather than a defect** because `at: 0.0` marks the cache expired, so the next
caller recomputes and the fabricated value cannot be read as measurement. If that is the intent
it is sound; it is just not what the surrounding sections do, and nothing says so.

---

## QUESTIONS

### Q1 — a truncation asserted as required

`src/verify_math.py:4601-4603`, against `src/cascade_bridge.py:1556`:

```python
check("pump() records the exception text, not just the failure flag",
      'box["error"] = str(exc)[:300]' in _cb22, True,
      note="THE BUG: without the text the classifier below matches '' and never benches")
```

**Reading A (deliberate):** 300 characters of a provider's exception is ample for the eleven
tokens the permanent-refusal classifier looks for, and an uncapped error string on the hot path
of every failed call would flood a shared ledger. Hard Rule 0 governs rosters and reference
listings, not the width of a log field.

**Reading B (defect):** the string this cap produces is the same `raw` the classifier matches
`"insufficient balance"`, `"no resource package"`, `"payment required"` and `"invalid_api_key"`
against (`:4613-4618`). A provider whose billing complaint sits past character 300 of a JSON
envelope is never benched and is re-claimed forever while reporting full headroom — which is
verbatim the failure §20w was written to close (`:4588-4595`). The cap and the classifier are
one line apart and nothing reconciles them.

Also worth noting independently of which reading wins: this row pins an exact source spelling
*including the magic number*, which is the shape the three rows either side of it were rewritten
away from (`:4621-4629`, `:4693-4708`). Changing 300 to 500 would redden a correct improvement.

### Q2 — `limit=` on the battery's own fixtures

`:1176` `_rows = PR.build_all(limit=400)`; `:1361` `BG.burgs_for(424242, _f, limit=3)`;
`:1363-1364` `BG.burgs_for(7, ..., limit=200)`.

**Reading A:** Hard Rule 0 is about the library's universe of IPs and references, not about how
many fixtures a verification battery generates. The `:1174-1175` comment announces the sample and
its reasoning ("If decode ever breaks it breaks on the first row, not the 40,001st"), which is
the announced-cap path §b3 at `:7113-7119` explicitly blesses.

**Reading B:** `limit=` on a function called `build_all` is the exact parameter shape Hard Rule 0
names, and the row underneath it makes a universal claim — "every profile round-trips to its own
address" — over about 1% of the population. If `build_all`'s own `limit=` ever became the shape
`roster(limit=600)` had, this battery would be the thing that stopped noticing.

### Q3 — determinism proved within one process

`:1300`:

```python
check("shelving is deterministic", SF.build()[1]["Alien"], _coords["Alien"])
```

`_coords` came from `SF.build()` at `:1268`. I checked `sevenfold.build()` and it carries no
memo, so this genuinely recomputes.

**Reading A:** it is a real second computation and the row means something.

**Reading B:** it is the *within-one-process* form, which this file explicitly rejected twice —
for `map_seed` at `:1045-1049` and for `assign` at `:1137-1143` — both repaired by exec'ing a
second copy of `address_space.py` from source. The reasoning given there applies unchanged: "an
import-time random seed, or a value cached into module state by an earlier call, diverges here
instead of comparing equal to itself." `build()` calls `tiers._graph()` and
`worldseed.build_all()`, and if either grows a module-level cache this row silently becomes
`f(x) == f(x)`. The `_asfresh` machinery to do it properly is already in the file at `:1050-1056`.

### Q4 — two prose counts have already drifted

`:9100-9103` says "68 rows carried `tol=` on 2026-09-01"; the current count is **67**.
`:8949-8952` says "62 tags on 2026-08-29 across 41 banner, 19 print and 4 dashed headers"; the
current figures are **67 tags across 46 / 22 / 4**.

Neither is load-bearing — both rows assert a floor (60 and 55), and both floors are comfortably
met. But order 1036c659495d exists because of exactly this ("A count written down once is a
measurement that stops being taken"), and the drift has already begun in the two notes written
to record that lesson. INFO, not a defect: the fix is to phrase the note as a floor rather than
as a date-stamped tally, or to drop the tally.

### Q5 — the section-tag matcher's third blind spot is one f-string away

`:8915`:

```python
        elif _s20y.startswith("print(") and "§" in _s20y and _s20y[6] in "\"'":
```

`_s20y[6]` is the character immediately after `print(`. A heading written `print(f"…§20zz …")`
has `f` there and is invisible to the scan. I checked: there are currently **zero** `print(`
lines carrying a section sign that do not open with a quote, so the uniqueness verdict at
`:8939` is sound today.

The question is whether that is worth pinning. This detector has been found blind twice already
— banner-only for its whole first life, then repaired at `:8880-8888` with the observation that
"a detector that certifies uniqueness while unable to see a third of the subject is worse than
no detector, because it retires the human who was doing the job." The row at `:8943-8948` asserts
"all three section-header spellings are recognised", which is a statement about the three
spellings the scan knows, not about the ones it cannot see. The file already uses an f-string
`print(` for the §20u INFO banner at `:8411`, so the spelling is in use in this file — just not
yet on a heading.

---

## Method note

Findings F1, F4, the tautology sweep and the section-tag sweep were re-measured rather than
reasoned about, using standalone scripts in a scratch directory that read `src/*.py` as text and
import nothing from the tree. `src/` was not written to at any point during this audit.
