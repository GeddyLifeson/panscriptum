# AUDIT — batch 02 — run #36

Module: `src/drill.py` (grew from 4,822 to 4,967 lines while this audit was in progress — other
agents are actively editing it; line numbers below are as-observed at read time and will drift,
so every finding is anchored on quoted text, per the sweep's own rule).

Scope note: this batch's specific guidance asked for an adversarial pass over the sixteen nets
converted from whole-file substring search to parse-tree checks, plus the new AST helper layer.
That is where the bulk of the effort went, including empirical proof-of-concept defeats built
and run against scratch fixtures (never against the real tree). A lighter general pass (tmp
names, discarded verdicts, silent caps, stale line tags) was also done over the rest of the file.

## Method

For the highest-value findings I did not just read the code — I built minimal scratch modules
(under a temp dir, never under `src/`) reproducing the shape of a "guard removed, decoy left
behind" edit, pointed the relevant helper at them with the file's own `src=`/`_SRC_OVERRIDE`
testing hook, and confirmed the predicate's actual return value. All three confirmed defeats
below were run, not inferred.

## The AST helper layer (`_ast_of`, `_defn`, `_call_spellings`, `_calls_within`,
`_code_strings`/`_says`, `_subscript_assigns`, `_srcdir`/`_SRC_OVERRIDE`)

**Read, mostly sound.** `_ast_of` (`with open(path, encoding="utf-8") as fh: return
ast.parse(...)`) raises on unreadable/unparseable and does not catch anything itself; every call
site is inside a `net()`-wrapped attack, and `net()`'s own `except Exception` records a raised
attack as `held=False` — i.e. an unparseable module reports BREACH, not a silent pass. This is
the correct fail-closed shape and it is consistent across all sixteen converted nets and the two
hand-rolled AST scans (`_no_programmatic_clear`, `_publish_never_swallows_a_missing_safety`),
which each also explicitly `return False` (breach) on `(OSError, SyntaxError)` rather than
skipping the file. `_defn` returns `None` on a miss and every call site (`_run_marks_a_landless_
run_failed`, `the_keeper_asks_before_restarting`, `mutation_never_touches_the_live_tree`,
`publish_asks_before_pushing`, `drill_does_not_halt_during_a_mutation_run`) checks for `None`
before using the result. No fail-open path found in the helper layer itself.

**MAJOR — the helper layer verifies structural PRESENCE within a scope, never REACHABILITY.**
`_calls_within(tree, n, want)` and `_says(node, fragment)` both run `ast.walk()` over the given
subtree and ask "does a matching node exist anywhere in here" — including inside an `orelse`
branch sitting beside the branch under test, and including inside code that is syntactically
present but never executes (dead code after a `return`/`break`/`continue`, or inside `if False:`
— Python parses both fine). This is the same defect class the whole rewrite exists to retire
(*"a comment reproducing the searched-for string used to make the net pass"*) recurring one
layer up: an AST node that never runs is not evidence its effect happens, in exactly the way a
comment naming a call was never evidence the call happens. Three of the sixteen converted nets
are concretely exploitable through this gap; see below.

## Confirmed defeats (built and run against scratch fixtures)

### 1. MAJOR — `mutation_never_touches_the_live_tree` (mutate.py sandbox guard) passes against a `run()` that writes straight to the live tree, unsandboxed

Anchor: *"`recorded and _defn(tree, "sandbox") is not None and _says(tree, "MUTATE_TOUCHED_LIVE_TREE")`"*
(the function `mutation_never_touches_the_live_tree`, in `drill_mutate`/mutation-run area).

This is the net the file's own docstring calls *"the architectural fix, asserted rather than
assumed"* — the guard against corrupting the live source tree that fifteen other processes read.
Its three checks are:
- `recorded`: does ANY `ast.Dict` literal ANYWHERE in the module have the key `"live_file_untouched"`
- `_defn(tree, "sandbox") is not None`: is there a function/class named `sandbox` DEFINED anywhere
- `_says(tree, "MUTATE_TOUCHED_LIVE_TREE")`: does the code string exist ANYWHERE in the module

None of the three is scoped to `run()`. None requires `sandbox()` to actually be *called*. None
requires the dict to be constructed on a live path or the string to be raised/logged when a
live-tree touch is actually detected. I built this fixture:

```python
def sandbox():
    """Defined but NEVER called by run() -- this is a decoy."""
    pass

_UNUSED_CONSTANT_TOUCH_CODE = "MUTATE_TOUCHED_LIVE_TREE"  # never raised, never checked

def run(targets):
    for t in targets:                    # writes straight to the live tree, no sandboxing
        with open(t, "w", encoding="utf-8") as fh:
            fh.write("corrupted")
    if False:
        result = {"live_file_untouched": False}   # dead literal, never assigned/returned
    return {"ok": True}
```

Run directly against this fixture (`_ast_of` + the same three-clause expression the net uses):
`recorded=True`, `sandbox defn found=True`, `says MUTATE_TOUCHED_LIVE_TREE=True` → **net result
`True` (HELD)**, on a `run()` that has no sandbox at all and mutates the live tree unconditionally.
This is the exact regression the net exists to catch, passing clean.

**Fix direction**: scope all three checks to `_defn(tree, "run")` (or wherever the write actually
happens), require `sandbox` to be *called* within it (`_calls_within`, not `_defn(...) is not
None`), and require the dict assembly / string to be on a reachable statement, not merely present
in the module.

### 2. MAJOR — `publish_asks_before_pushing` never checks that the mutation-interlock is called at all

Anchor: *"`imports_mutate = any(al.name == "mutate" ... ) ; return imports_mutate and
_says(push, "REFUSING TO PUSH")`"*.

The check is: does `push()` contain an `import mutate` statement, and does `push()` contain the
code string `"REFUSING TO PUSH"` anywhere. It never calls `_calls_within(tree, push,
"_MUT.active")` or anything equivalent — contrast with its sibling three lines below,
`drill_does_not_halt_during_a_mutation_run`, which correctly requires `_calls_within(tree, n,
"_MUT.active")` for the analogous check. I built:

```python
def push():
    import mutate  # imported but never called -- no active() check at all
    if False:
        print("REFUSING TO PUSH: a mutation run is active")
    return "pushed"  # ... real push logic with NO interlock whatsoever ...
```

Run against this: `imports_mutate=True`, `_says(push, "REFUSING TO PUSH")=True` → **net result
`True` (HELD)**, on a `push()` with zero interlock logic.

This is not only a hypothetical: the real `publish.py` already carries **three** separate
`"REFUSING TO PUSH: ..."` strings inside `push()` for three unrelated reasons — a missing
`ledger_guard` import, a missing `mutate` import, and an active mutation run (confirmed by
grepping `src/publish.py`: `"REFUSING TO PUSH: the ledger guard..."`, `"REFUSING TO PUSH: the
mutation interlock..."`, `"REFUSING TO PUSH: a mutation run is active..."`). If the actual
`_busy, _rec = _MUT.active()` call and its guarding `if` were deleted from `push()` today, this
net would keep passing on the strength of the OTHER two "REFUSING TO PUSH" strings, which have
nothing to do with the mutation interlock. The check currently proves less than it claims to.

**Fix direction**: require `_calls_within(tree, push, "_MUT.active")` (or `.active`) the same way
the sibling net does, and ideally tie the specific `"REFUSING TO PUSH"` string to the `If` node
that follows the `active()` call, not to `push()` as a whole.

### 3. MAJOR — `_halt_is_not_breakage` (overnight.py supervisor) passes against a supervisor that unconditionally treats a halted library as broken

Anchor: *"`return (_calls_within(tree, n, "_ESC.status") and any(isinstance(x, ast.Continue) for
x in ast.walk(n)) and _says(n, "it is a broken one"))`"*, where `n` is the whole `ast.If` node
for `if idle >= IDLE_LIMIT:`.

This net exists specifically to prevent a recurrence of *"this project's longest outage"* — a
supervisor that mistook a deliberate halt for breakage and exited without restarting anything.
Its three checks (`_ESC.status` called, a `Continue` present, the string `"it is a broken one"`
present) are all evaluated over `ast.walk(n)`, i.e. over the **entire If node including any
`orelse`/dead code**, not specifically the branch that must run when the library really is
halted. I built:

```python
IDLE_LIMIT = 3
def run_loop():
    idle = 0
    while True:
        idle += 1
        if idle >= IDLE_LIMIT:
            log("  HALT: ... it is a broken one")   # declares "broken" unconditionally
            break
            if False:                                # DEAD CODE -- never executes
                import escalation as _ESC
                _halted, _rec = _ESC.status()
                if _halted:
                    idle = 0
                    continue
        else:
            idle = 0
```

Run against this with `_SRC_OVERRIDE`: **`drill._halt_is_not_breakage(src=<fixture dir>)` returns
`True` (HELD)**, even though the executable path never consults halt status before declaring the
library broken and exiting — which is precisely the fault that caused the outage this net is
named for.

**Fix direction**: require the `_ESC.status()` call, the `Continue`, and the string to appear
specifically within `n.body` (not `n.orelse`), and ideally require them on the path actually
reachable before the `break`/give-up statement, e.g. by checking that the `if _halted:` node
containing the `Continue` is not itself preceded by an unconditional `break`/`return` in the same
block.

## Other findings from the sixteen-net pass (read, not independently re-derived as exploits — same class, lower confidence/impact)

- **MINOR/pattern** — `_identity_probe_is_gated` (binding_health.py), `the_keeper_asks_before_
  restarting` (overnight.py `_keep`), `daemons_actually_check_their_own_source` and
  `singleton_guard_is_wired_into_the_daemons` (codewatch calls in publish/foreman/overwatch),
  and `generator_actually_skips_an_excluded_source` (manifest_builder.py) all share the same
  "presence somewhere in scope, not reachability" limitation as the three confirmed defeats
  above. I did not build fixtures for each (time-bounded), but the mechanism is identical: a
  dead/unreachable copy of the required call or a copy sitting in a sibling branch would satisfy
  each of them. None is currently exploitable *in the live tree* the way #1–#3 are (I checked —
  each currently has exactly one real occurrence of the relevant call, in the right place), so
  these are latent rather than live, but they are the same defect the run #36 pass was meant to
  retire, one abstraction level up.

- **MINOR/QUESTION** — `resync_cannot_revert_an_exclusion` (resync_roll.py): the check finds an
  `ast.If` whose test `Compare` has `.OUT_OF_SCOPE` as *any* comparator, then requires the body
  not to reassign `r["status"]`. It never checks that the LEFT side of the comparison is the
  status being tested (it happens to be `r.get("status")` in the live file, which the check
  correctly does not hardcode — that part is fine) — the actual gap is that *any* unrelated
  `if x == roll.OUT_OF_SCOPE:` elsewhere in the file, with a body that doesn't happen to touch
  `r["status"]`, would independently satisfy the net regardless of whether the real
  exclusion-preserving branch exists at all. Currently there is exactly one `OUT_OF_SCOPE`
  comparison in `resync_roll.py` (grepped and confirmed), so this is not live-exploitable today,
  but it is a coincidence of the current file's shape rather than something the check enforces.

- **MINOR/QUESTION** — `_refusal_is_recorded` (feats.py, `pages_refused`): the "records" and
  "carried" checks are evaluated over the whole module (`ast.walk(tree)`), not scoped to the
  refusal branch specifically. Given only one `unreal[t] = why` assignment exists in `feats.py`
  today (grepped), this is not currently gameable, but it is the same un-scoped pattern.

- **QUESTION, not a defect** — `_no_programmatic_clear` (the hand-rolled AST scan, not one of the
  sixteen, but adjacent and worth checking given the guidance's "alias import / getattr / dynamic
  name" prompt): it explicitly resolves `import escalation as X`, `from escalation import clear`,
  and `getattr(escalation, "clear")(...)`, and I confirmed by direct test that a *local variable
  alias* — `f = escalation.clear; f(ruling)` — evades it (built and ran the fixture; the net
  reports "no programmatic clear" = True/HELD against a module that does call `clear`). However
  the docstring is explicit that this scan is *not* the sole enforcement: `escalation.clear()`
  itself refuses any caller that isn't `escalation.py`'s own `main()` invoked by a person at the
  CLI (`_by_a_person_at_the_cli`, exercised by `_no_runtime_clear` a few functions above), so the
  variable-alias gap does not defeat the actual security property, only this one static
  best-effort scan of it. Flagging as a question rather than a defect because the file already
  says this net is defense-in-depth, not the guarantee.

## `abandoned_sandboxes_are_reaped` — specifically checked per guidance, looks sound

Reviewed the rewritten version (anchor: *"THIS NET COULD NOT GO RED (found by the run #35 sweep,
fixed run #36)"*). It now builds two real directories under `tempfile.gettempdir()`, both
carrying the module's real `SANDBOX_PREFIX`: one back-dated past `M.ORPHAN_AGE_SECONDS` with
`os.utime`, one left fresh. It calls the real `M.reap_orphans()` with no arguments (the module's
own default age, not an inflated one — the old defeat drove the cutoff to before the epoch with
`older_than=10**9` so the call returned `[]` regardless of whether reaping worked), and requires
**both** halves: the aged one is in the returned list and no longer on disk, AND the fresh one is
absent from the returned list and still on disk. This distinguishes an indiscriminate reaper
(would delete the fresh one too — caught) from a broken/no-op reaper (would leave the aged one on
disk — caught) from the original `[]`-shortcut tautology (would fail the "aged in removed" half
outright). It also guards with `M.ORPHAN_AGE_SECONDS < 3600: return False`, closing the version of
this same trick that shrinks the constant instead of inflating the argument. Cleanup runs in
`finally` regardless of outcome. No vacuous-pass path found.

## Systematic search for remaining substring-based guard verification

Grepped the live file for the shapes the run #36 pass targeted (`in text`, `in fh.read()` used as
a boolean guard on code rather than on subprocess output, `.rfind(` used as a source-scan
apparatus). All remaining matches are either (a) inside docstrings quoting the OLD, already-
replaced code as historical explanation (e.g. *"This was `"out_of_scope" in text and "import
roll" in text`"*), or (b) legitimate substring tests against subprocess/process output text,
which `_counts_decided_by_substring`'s own docstring explicitly carves out as fine (*"`"Traceback"
in stderr`... are ordinary substring tests about TEXT and are deliberately not flagged"*). Found
no live guard-verification-by-comment-adjacent-substring that the conversion pass missed. Counted
the tag exactly: fifteen sites carry the literal `"ASKED OF THE PARSE TREE (run #36)"` /
`"AND READ AS A PARSE TREE, NOT AS TEXT (run #36)"` marker, plus `_halt_is_not_breakage` which is
the same conversion without the literal tag string — sixteen total, matching the brief's count.

## General pass over the rest of the file (tmp names, discarded verdicts, caps, stale tags)

- **Read, nothing found** — fixed `.tmp` names / read-modify-write races: the one `.tmp` /
  `.tmp2` / `.tmp3` usage found (`drill_stale_writer`, anchor `tmp = dst + ".tmp"`) is a scratch
  fixture inside a `tempfile.mkdtemp()`-created per-run directory, testing `silence.py`'s
  compare-and-swap itself; it is not a shared production temp name and does not recreate the
  two-writer hazard it is verifying against.
- **Read, nothing found** — silent caps: the only list-truncation found,
  `"; ".join(r["net"] for r in breached[:5])`, truncates only the human-readable console summary
  line printed on breach. The durable record — `evidence={"breached": [r["net"] for r in
  breached]}`, passed to `ESC.escalate(...)` — carries the full, uncapped list. Not a Hard Rule 0
  violation.
- **Read, nothing found** — discarded verdicts: `lambda: (LA.blast_reset() or True) and
  LA._BLAST["patches"] == 0` (anchor, `drill_local_agent`) looks at first glance like a discarded
  return value, but the actual verdict the net asserts is read back from state
  (`LA._BLAST["patches"] == 0`) rather than trusted from `blast_reset()`'s return — arguably a
  *more* reliable check than trusting the call's own report, not a defect. `except Exception:
  pass` was searched for specifically (the class 5/discarded-failure shape) and the only two
  matches are litter-cleanup helpers (`_sweep_probe_litter` and its inline sibling at the
  blast-cap net) that the file's own comments document were deliberately rewritten OFF `except
  Exception: pass` and onto `silence.note(...)` — confirmed by reading both call sites, which do
  record via `silence.note` rather than swallowing silently.
- **Read, nothing found** — stale `module.py:NNN` line tags: `_sweep_probe_litter` cites
  `"drill.py:%s-order-cleanup" % site` and `"drill.py:%s" % site`-style tags built from a `site`
  parameter passed at each call site, not hardcoded line numbers, so they cannot drift the way a
  literal `"drill.py:1234"` would. No hardcoded stale line-number tag found in this file.
- **QUESTION, not a defect** — `LIVENESS_CEILING = 41` (anchor, top of file): a ratchet the file's
  own multi-paragraph comment explains was raised from 38 because the *detector* got more precise
  (scope-aware `used` resolution), not because dead code increased, and states the rule this is
  not allowed to violate ("raising this to make a red drill go green is forbidden") in the same
  breath as justifying the one raise that already happened. Read the reasoning; it is
  self-consistent and does not by itself indicate a current violation. Flagging only because any
  future raise of this constant deserves the same scrutiny, not because this one fails it.

## Summary of severities

- MAJOR: 3 (all confirmed by running a crafted defeat, not inferred) — `mutation_never_touches_
  the_live_tree`, `publish_asks_before_pushing`, `_halt_is_not_breakage`.
- MINOR/pattern (latent, not currently live-exploitable): 6 nets sharing the same
  presence-not-reachability limitation, plus one hand-rolled scan (`_no_programmatic_clear`)
  with a documented-as-acceptable residual gap.
- Everything else reviewed under the general checklist: read, nothing found.
