# Proposed drill nets — RUN batch 07 (run #36)

Staged, not applied: `src/drill.py` is owned by another agent this shift. Each net below is
complete and drop-in — same shape as the existing `liveness_*` nets around drill.py:3045-3074.

Three of the seven orders in this batch widened or corrected a detector. Two of those
widenings currently report **zero** new findings across the tree, which is the good outcome and
also the dangerous one: a widened detector that finds nothing is indistinguishable from a
widened detector that is broken. These nets pin the widening itself, the way
`liveness_sees_its_own_founding_example` already pins the scope-aware `used` set.

---

## Net 1 — the PHANTOM pass sees a condition that is not an `if`

Pins order **425aa23da643**. Before run #36 the pass walked `n2.test` only for `ast.If`, so an
undefined name guarding a `while`, an `assert`, a ternary or a comprehension filter was
structurally invisible. It now collects all four. Phantom is 0 across `src/` today, so nothing
in the live tree would notice if that regressed.

```python
    def liveness_phantom_is_not_only_if():
        """THE WIDENING MUST STAY WIDE. PHANTOM inspected `ast.If` tests and nothing else
        until run #36, so the same undefined-name guard was caught in an `if` and missed in a
        `while`, an `assert`, a ternary and a comprehension filter -- the shape does not
        change with the keyword. The live tree reports zero phantoms, so a regression here is
        silent: the count would not move. Fed a synthetic module instead, in a temp dir, so
        this asserts the DETECTOR rather than the corpus.
        """
        import ast
        import tempfile
        import liveness
        src = ("def w(i):\n"
               "    while UNDEF_W:\n"
               "        i.pop()\n"
               "def a(x):\n"
               "    assert UNDEF_A\n"
               "    return x\n"
               "def t(x):\n"
               "    return 1 if UNDEF_T else 2\n"
               "def c(xs):\n"
               "    return [x for x in xs if UNDEF_C]\n"
               "def i(x):\n"
               "    if UNDEF_I:\n"
               "        return x\n")
        ast.parse(src)                      # the fixture must itself be valid Python
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "probe.py"), "w", encoding="utf-8") as fh:
                fh.write(src)
            keep, liveness.SRC = liveness.SRC, d
            try:
                found = " ".join(liveness.scan()["phantom"])
            finally:
                liveness.SRC = keep
        return all(n in found for n in ("UNDEF_W", "UNDEF_A", "UNDEF_T", "UNDEF_C", "UNDEF_I"))
    net(a, "PHANTOM catches an undefined name in while/assert/ternary/comprehension, not just if",
        liveness_phantom_is_not_only_if,
        "a detector that only inspects the syntax its worked example used measures the example")
```

## Net 2 — the DEAD pass looks inside a class

Pins order **5569dc0d2c3e**. Before run #36 the pass iterated `Module.body` and stepped over
every `ClassDef` whole, so no method was ever a candidate. The widening produced exactly two
findings tree-wide, both real false positives (`dashboard.Handler.do_GET`, `.log_message`) now
in `EXEMPT` with reasons — so, again, the live count is unchanged and a regression is silent.

```python
    def liveness_dead_looks_inside_a_class():
        """A METHOD IS A FUNCTION. `liveness` walked `Module.body` until run #36, so twelve
        modules' worth of methods were never DEAD candidates -- not exempt, not judged, absent.
        The fixture pairs a method that IS reached through an instance with one that is not, so
        this fails both ways: if the pass stops looking inside classes, and if it starts
        reporting methods that are plainly used.
        """
        import tempfile
        import liveness
        src = ("class H:\n"
               "    def reached(self):\n"
               "        return 1\n"
               "    def never_reached(self):\n"
               "        return 2\n"
               "def uses():\n"
               "    return H().reached()\n")
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "probe.py"), "w", encoding="utf-8") as fh:
                fh.write(src)
            keep, liveness.SRC = liveness.SRC, d
            try:
                dead = " ".join(liveness.scan()["dead"])
            finally:
                liveness.SRC = keep
        return "H.never_reached()" in dead and "H.reached()" not in dead
    net(a, "DEAD considers methods, and still resolves one reached through an instance",
        liveness_dead_looks_inside_a_class,
        "a ClassDef was stepped over whole, so every method was absent from the scan")
```

## Net 3 — a failed control probe is not a baseline of zero

Pins order **53a0111dccac**. `hostcheck.null_rate()` collapsed an unmeasured control to `0.0`,
the most generous baseline available, which inflates every lift computed against it. This is
the same conflation `probe()` was fixed to stop, committed one call deeper, and it fails in the
ADOPTING direction — a network failure would have made a wrong host look good.

```python
    def hostcheck_failed_control_is_not_zero():
        """A REQUEST THAT FAILED IS NOT A WIKI THAT HOLDS NOTHING -- and the control side is
        the dangerous side. On the roster probe a bogus zero REJECTS a host (74 throttled
        probes unassigned warhammer40k.fandom.com). On the BASELINE it does the opposite: a
        baseline of 0.0 makes every observed rate look like pure lift, so a throttled control
        ADOPTS. null_rate must answer None, score must propagate it, and the verdict must land
        in the UNREACHABLE bucket that sweep() retries rather than the ones it repairs.
        """
        import hostcheck as HC
        keep_probe, keep_cache = HC.probe, dict(HC._NULL_CACHE)
        roster = {"host": "h", "probed": 40, "hits": 20, "rate": 0.5, "titles": ["T"]}
        try:
            HC._NULL_CACHE.clear()
            # The roster probe answers; the control probe fails, exactly as a throttle looks.
            HC.probe = lambda host, names: roster if len(names) > 1 else None
            r = HC.score("h", ["a", "b", "c"], "SRC", by={"SRC": ["a", "b", "c"]})
        finally:
            HC.probe = keep_probe
            HC._NULL_CACHE.clear()
            HC._NULL_CACHE.update(keep_cache)
        return (r["baseline"] is None and r["lift"] is None
                and r["verdict"].startswith("UNREACHABLE")
                and "h" not in HC._NULL_CACHE)   # a failure must never be cached as a baseline
    net(a, "a host whose control probe failed gets no baseline, no lift and no judgement",
        hostcheck_failed_control_is_not_zero,
        "collapsing an unmeasured control to 0.0 flatters every lift measured against it")
```

---

### Notes for whoever applies these

* **All three were executed verbatim against the patched tree and reported HELD.** They are
  staged rather than untested: the bodies above are the ones that ran. Only the `net(a, ...)`
  registration lines are unexercised, since `net` lives in `drill.py`.

* All three use `os.path.join`; `drill.py` already imports `os` at module scope.
* Nets 1 and 2 rebind `liveness.SRC` and restore it in a `finally`. Net 3 rebinds
  `hostcheck.probe` and restores both it and `_NULL_CACHE`. None of the three touch the corpus,
  the network, or any file under `src/`, so they cost milliseconds and are safe in the battery.
* Adding three nets moves the drill's net count from 57; whatever asserts that total needs the
  same bump in the same commit.
* **No `LIVENESS_CEILING` change is needed.** Both widenings finished at 33 total findings
  against the ceiling of 41 — the DEAD widening's only two hits were exempted as framework
  dispatch with a written reason each, and the PHANTOM widening found nothing real. If a later
  agent widens either detector further and the count rises, the lawful-raise justification is
  the one already written above `LIVENESS_CEILING` at drill.py:41-63.
