# Sweep42 batch 14 — audit of hostcheck.py, escalation.py, derivation.py, liveness.py,
# address.py, cosmography.py, catalogue_models.py, cosmology_graph.py

All eight modules read in full (hostcheck.py: 1407 lines, in two passes; the rest read whole).

## CONFIRMED DEFECTS

### 1. src/hostcheck.py:775 — silent source-name truncation in `sweep()`'s console report (Hard Rule 0)

```python
print(f"  {r['rate']:>5.0%} held {lift} lift  {r['hits']:>3}/{r['probed']:<3} "
      f"{r['host']:<34}{r['source'][:34]}{flag}", flush=True)
```

`r['source'][:34]` is a bare slice with no ellipsis marker and no "(+N more)" indication. A
source name longer than 34 characters is silently cut, and the printed line gives no sign that
anything was dropped — it reads as a complete, correct row. This is exactly the same defect
class this file's own `roster_audit()` was fixed for a few hundred lines later (the comment at
what is now line ~1254 explicitly says: "This was `r['source'][:44]` inside a `:<46` field -- a
silent mid-name cut on the one column a person uses to tell two sources apart... The column
still pads; it no longer truncates."), and the class `cosmology_graph.py`'s dedicated `_cut()`
helper exists specifically to mark. `hostcheck.py` has no `_cut`-style helper anywhere, and this
occurrence in `sweep()` (the file's primary, most-run report) was not brought in line with the
fix made to its sibling report further down the same file.
**Confidence: high.** This is a live, unmarked truncation of the exact field (source name) that
distinguishes one source from another — the long parenthetical publisher-plus-title names this
project's own comments repeatedly flag as the ones most likely to collide on a short prefix.

### 2. src/hostcheck.py:1337 and :1340 — same defect, in `adopt()`

```python
print("   {:>+5.0%} lift  {:<9}{:<34}{}".format(lift, verdict, host, src[:40]),
      flush=True)                                                      # line 1337
...
print("      -   none      {:<34}{}".format("", src[:40]), flush=True) # line 1340
```

Both lines truncate `src` (the source name) to 40 characters with a bare slice, no ellipsis, no
count of what was cut. Same violation as #1, same file, different function (`adopt()`, the pass
that finds a host for every hostless catalogued source).
**Confidence: high**, for the same reasons as #1.

### 3. src/catalogue_models.py — an `EMPTY_LIST` provider (a fully verified "serves nothing"
answer) is reported as `unverified`, and its configured model ids are counted as "unchecked"
rather than "confirmed stale"

`ask_provider()` defines `EMPTY_LIST` explicitly as a *verified* fact, distinct from an
unreachable/unconfigured provider — its own comment says so in capitals: "A 200 CARRYING AN
EMPTY LIST IS AN ANSWER, and a different one from a dead endpoint... one is a wrong URL, the
other is an account with no entitlements" (lines 101-107), and the returned error string even
states "the API is alive and serves nothing (not a missing endpoint)" (line 141-142).

But `sweep()` throws that distinction away:

```python
live = {r["provider"]: r for r in rows if r.get("models")}         # line 176
...
verified = [r for r in rows if r.get("outcome") == LISTED]         # line 236
```

For an `EMPTY_LIST` row, `r["models"]` is `[]`, which is falsy in Python, so `r.get("models")`
is `False` and the row is dropped from `live`. Down in the per-provider loop (lines 195-205),
`r = live.get(name)` is then `None` for that provider, so it falls into the `if not r:` branch
and is filed as `unverified` with `outcome = "empty_list"`, printed under the banner "N
provider(s) produced NO model list, so their M configured model id(s) are UNVERIFIED — neither
fresh nor stale, unasked" (line 239-241). It is also excluded from `verified` at line 236 since
that only counts `LISTED`.

This is backwards. A provider that answers 200 with a well-formed empty list has definitively
verified that it serves zero models — every model id the config asks for it IS confirmed stale,
not merely "unchecked." Had `live` included `EMPTY_LIST` rows (their `models` list is correctly
`[]`), the normal `have = set(r["models"])` / `missing = [a for a in asks if a not in have]`
path at lines 206-211 would have produced exactly that correct result (`have` empty, so every
ask is `missing`/stale). Instead the whole class of provider is silently moved from "confirmed
100% stale" into "don't know," understating `stale_ids`/`counts.stale_ids` and overstating
`counts.unverified`/`unchecked_ids` — the two counters `standards.py` reads to judge the health
of the model pool.
**Confidence: medium-high.** The bug is a Python truthiness trap (`if r.get("models")` treating
`[]` the same as absent), directly contradicting the outcome taxonomy the same file just spent a
paragraph establishing.

## QUESTIONS (possibly deliberate; flagging for the owner, not proposing a fix)

### Q1. src/liveness.py — PHANTOM's `defined` set is built over the WHOLE module, not per-function

In `scan()` (lines 449-477), `defined` is populated by walking the *entire* module AST once —
every function's local variables, every comprehension binding, every parameter, from every
function in the file — and then every guard/assert/match-guard/comprehension-filter/
short-circuit condition anywhere in the module is checked against that one flat set. A name that
is a legitimate local in function A will silently mask a genuinely undefined-name bug in an
unrelated function B's guard that happens to reuse the same identifier. This matches the
module's own stated scope ("a name used in a condition that is never defined, imported or
assigned in **its module**" — line 33), so it may be intentional given this is a syntax-only
pass with no per-scope symbol table, but it is a real, unremarked detectability gap in a
detector whose whole purpose is catching invisible failure modes.

### Q2. src/escalation.py — inconsistent minimum length for a "written ruling"

`clear()` (line 877) demands `len(str(ruling).strip()) < 12` be false (i.e. at least 12
characters) to lift an OWNER halt. `resume_subsystem_verdict()` (line 742) demands at least 20
characters to resume a MANAGER-stopped subsystem — a rung *below* the halt. It's odd that the
lower-severity action requires the longer ruling; may be deliberate (different reviewers wrote
each gate at different times) but worth a sanity check.

### Q3. src/liveness.py — TAUTOLOGY only inspects two-operand `Compare` nodes

`for node in ast.walk(t): if not isinstance(node, ast.Compare) or len(node.comparators) != 1:
continue` (line 429) means a chained comparison such as `a == b == a` is invisible to this pass
even though it contains the exact same-expression shape the pass exists to catch. Zero instances
measured today (not verified independently in this audit), and the module's docstring already
disclaims a different, semantic gap (the `profile.py` case) — this is a narrower, syntactic gap
in the same spirit, not called out anywhere in the file.

## Modules read with no findings beyond the above

- **derivation.py** — the ledger and its `check_graph()`/`scan_constants()` machinery are
  internally consistent; `KARDASHEV_MIX` sums to 1.0, the cycle-detection early-return (order
  90516d53d696) is present and correct, `_target_names` correctly unwraps tuple/starred targets.
- **cosmography.py** — `census()`/`validate()`/`kardashev_to_magnitude()` are consistent; the
  `SIZE_CLASS_MAX_GALAXIES` refusal for POCKET/MINOR is a known, already-commented open owner
  question (lines 151-155), not a new finding.
- **cosmology_graph.py** — weight formula matches its own docstring; `--write` path is complete
  and uncapped (`pairs`, `clusters`, `source_entities` all written whole); write is gated on
  `silence.write_json`'s verdict correctly.
- **address.py** — `spine_code_for()`'s multi-stage matching (exact / normalized-equality /
  most-specific-substring / token-overlap) was checked for the containment-direction and
  tie-break logic described in its own extensive comments; found self-consistent. `slugify()`
  and `recipe_hash()` are uncapped.
