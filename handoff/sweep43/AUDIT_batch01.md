# AUDIT — sweep43, batch 01

Scope: `src/drill.py` (10,881 lines), read in full, top to bottom.

Context for the reader: this file has already been through roughly 42 prior sweeps and carries
its own extensive in-file history of found-and-fixed defects (dead-code-reachability bypasses,
literal-substring scans defeated by comments, capped fixtures, etc.). Given that maturity, this
pass concentrated on verifying the *shared static-analysis primitives* the newer AST-based nets
all depend on (`_live_stmts`, `_live_walk`, `_reaches_call`, `_calls_within`, `_gate_precedes_spawn`,
and friends) rather than re-deriving the history of each individual net, which is already
documented in the file's own comments.

## drill.py

### MAJOR — `_live_stmts` mishandles `while True:`/`while False:` with an `else:` clause,
### making genuinely-dead code register as reachable (and genuinely-live code as dead)

`src/drill.py:534-556` (`_live_stmts`):

```python
def _live_stmts(body):
    out = []
    for s in body:
        inner = None
        if isinstance(s, (ast.If, ast.While)):
            k = _static_truth(s.test)
            if k is False:
                inner = _live_stmts(s.orelse) if isinstance(s, ast.If) else []
            elif k is True and isinstance(s, ast.If):
                inner = _live_stmts(s.body)
```

For an `ast.While` node whose test is statically **False** (`_static_truth` returns `False`),
the code sets `inner = []` unconditionally — it drops the `While` node's `orelse` entirely,
never inlining it. But in real Python, `while False: BODY else: X` executes `X` immediately
(the `else` of a `while` runs whenever the loop terminates without `break`, including when the
condition was never true to begin with). So a call that genuinely executes on every run of the
function is treated by every net built on `_live_walk`/`_reaches_call`/`_calls_within(reachable=True)`
as dead code and skipped.

For an `ast.While` node whose test is statically **True**, the `elif` guard
(`k is True and isinstance(s, ast.If)`) does *not* apply to `While` at all, so the `While`
statement is kept as an ordinary live statement (`out.append(s)`) and `_live_walk`'s generic
field-based walk descends into both its `body` and its `orelse` fields, filtering each
independently through `_live_stmts`. But a `while True: ... else: X` can only exit via `break`
(or `return`/`raise`), both of which always skip the `else` clause — so `X` is *provably
unreachable dead code*, in every case, yet the module reports it as live.

Verified empirically against the actual functions in this file:

```
>>> src = "def f():\n    while False:\n        real_call_body()\n    else:\n        real_call_else()\n"
>>> [n.func.id for n in drill._live_walk(fn) if isinstance(n, ast.Call)]
[]                      # real_call_else() genuinely runs every call, but is reported dead

>>> src = "def f():\n    while True:\n        break\n    else:\n        dead_call_that_never_runs()\n"
>>> drill._reaches_call(tree, "dead_call_that_never_runs", ("f",))
True                    # this call can NEVER execute, yet _reaches_call says it can
```

**Why it matters.** This file's entire design philosophy — stated explicitly and repeatedly in
its own comments (e.g. the block above `_live_stmts` itself, and the run #37 history throughout)
— is that "dead code is prose that happens to parse," and that a guard call parked somewhere the
program cannot actually reach must **not** satisfy a "the guard is wired" net. Every one of the
several dozen nets in this file that ask `_reaches_call(...)` or `_calls_within(..., reachable=True)`
to prove a safety-critical call (`escalation.assert_clear`, `mutate.active`,
`codewatch.exit_if_stale`, `maintenance_shift_live`, `_manager_stopped`, etc.) is genuinely wired
into the live path relies on `_live_walk` correctly distinguishing live code from dead code. The
`while True/False: ... else:` shape is exactly the kind of construct an adversarial mutation (or
a careless future edit) could use to hide a deleted/never-executed guard behind code that reads
as though it fires — and have the reachability-based nets report HELD anyway, which is precisely
the failure class ("a check that cannot fail looks exactly like a check that passed") this whole
file exists to prevent.

**Current impact on the live tree.** I grepped every `.py` file under `src/` for a `while` loop
carrying an `orelse` clause and found none — no file in the current tree uses this construct, so
no net is *currently* giving a wrong verdict because of it. This is a latent defect in shared
analysis infrastructure, not an active false result.

**Remedy.** `_live_stmts` needs a `While`-specific case that mirrors the `If` handling correctly:
when the test is statically `False`, the `orelse` **is** live (should be inlined, same as `If`'s
False arm); when the test is statically `True`, the `orelse` is unreachable dead code and should
be dropped entirely (not merely left to the generic field walk, which currently treats it as
live). This needs a careful, verified fix rather than a mechanical one-line change, since it
touches the reachability primitive that dozens of nets are built on and a bad fix could silently
change many other verdicts. Filed as `RUN`.

## No Hard Rule 0 findings

No new `[:N]`/`limit=`/truncation issue was found in `drill.py` itself. (The file's own
`drill_no_caps`, `drill_scout`, and `_policy_corpus_clean` areas exist specifically to test other
modules for this; `drill.py`'s own console output in `main()` is explicitly uncapped per the
"THE HALT SENTENCE NAMES EVERY BREACHED NET" comment at the bottom of the file, verified by
reading — `"; ".join(r["net"] for r in breached)` has no slice.)

## No BLOCKING findings

I did not find a live, currently-triggerable BLOCKING defect (inverted predicate, wrong
variable, always-true/false comparison, etc.) in the roughly 300 individual net bodies and the
AST helpers that back them. The file is unusually mature — nearly every net body carries a
paragraph documenting the specific past defeat it was rewritten to close, and spot-checking a
representative sample of the arithmetic/comparison logic in each area (queue/dispatch/train/assay
gates, escalation chain, mutation lock, ledger CAS, codewatch budget, scout rotation, etc.)
did not turn up a fresh inversion or off-by-one.

## Questions for the OWNER

None raised this batch — the one finding above is a factual correctness bug in a shared helper,
not a curatorial or design judgment call.

## Coverage

Read `src/drill.py` in full (all 10,881 lines), top to bottom, across this session.
