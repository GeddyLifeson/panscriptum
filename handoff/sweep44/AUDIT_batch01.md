# Sweep 44 — Batch 01 audit

**Module read in full:** `src/drill.py` (11,120 lines, 650,318 bytes)
**Read:** top to bottom, no sampling. Every finding below was re-checked against the source
lines it cites, and the mechanical ones were driven against the real functions before they were
written down.

Nothing under `src/` was modified.

---

## Summary

| Severity | Count |
|---|---|
| MAJOR | 0 |
| MINOR | 11 |
| QUESTION | 4 |

**Hard Rule 0:** no cap, no truncation and no "top N" was found anywhere in `drill.py`'s own
logic. Every `[:N]` in the file is either inside a prose paragraph describing a cap that was
removed elsewhere (`:1712`, `:2479`, `:5473`, `:9230`), or a deliberate fixture construction
(`:4017` tears a chain line in half on purpose; `:3502` places a credential across a chosen
segment seam; `:9366` reads the first three seeded cycles of a 43-cycle fixture). The two places
a reader would most expect one — `main()`'s halt sentence at `:11099-11102` and the
`AssertionError` in `no_open_order_sits_on_a_legacy_cap_boundary` at `:6354-6356` — are both
explicitly uncapped and say so. `_policy_corpus_clean` (`:5495`) walks the whole records glob.

**Area registration:** all 37 `drill_*` area functions defined at module level are present in
`main()`'s run list (verified by parsing the file: zero defined-but-unlisted, zero
listed-but-undefined). No area is silently unreached.

---

## MINOR 1 — `_is_rooted` carries a branch that can never fire, and the branch that does fire is broader than its docstring

`src/drill.py:1085-1089`

```python
    if isinstance(expr, ast.Call) and _spelled(_spellings_of_call(tree, expr, maps),
                                               "os.path.join"):
        return any(_is_rooted(tree, a, derived, maps) for a in expr.args)
    if isinstance(expr, ast.Call) and _spelled(_spellings_of_call(tree, expr, maps), "join"):
        return any(_is_rooted(tree, a, derived, maps) for a in expr.args)
```

`_spellings_of_call` (`:460-480`) only builds a dotted spelling when the call's `func.value` is
an `ast.Name`:

```python
    elif isinstance(fn, ast.Attribute):
        out.add(fn.attr)
        if isinstance(fn.value, ast.Name):
            out.add("%s.%s" % (fn.value.id, fn.attr))
```

For `os.path.join(...)` the `func.value` is itself an `Attribute` (`os.path`), not a `Name`, so
the only spelling produced is `"join"`. Driven directly:

```
spellings for os.path.join(root, 'a'): ['join']
_spelled(sp, 'os.path.join') -> False
_spelled(sp, 'join')         -> True
```

So the first branch is dead in every real spelling, and the second branch is what actually
answers. The two arms are byte-identical in body, which is why the deadness has no behavioural
consequence today — but this is precisely the shape the file's own header calls out ("a check
that cannot fail looks exactly like a check that passed"), sitting in `drill.py`'s shared
reachability toolkit.

The docstring one line up says the function accepts "an `os.path.join(root, ...)`". The live
branch accepts **any** call whose attribute is named `join`. Driven:

```
rooted names for  p = ','.join(root)   ->  ['p', 'root']
```

A `str.join` over a rooted name is treated as a rooted path. `mutation_never_touches_the_live_tree`
(`:9933`) is the only consumer, and it is over-permissive in the direction that matters: a write
whose path came out of `"".join(...)` on a sandbox-derived name would be accepted as sandboxed.
The generosity may well be deliberate (the sibling `_filtered_names` at `:989` argues explicitly
for generous over-approximation), but the docstring does not say so, and the dead `os.path.join`
arm reads as though the narrow case were the one being handled.

**Confidence: high** — both halves driven against the real functions.

---

## MINOR 2 — `_WRITE_CALLS` records the wrong argument index for the two pathlib spellings

`src/drill.py:954-956`

```python
_WRITE_CALLS = {"_write": 0, "write_bytes": 0, "write_text": 0, "os.remove": 0,
                "os.unlink": 0, "shutil.rmtree": 0, "shutil.copy": 1, "shutil.copy2": 1,
                "shutil.copyfile": 1, "shutil.move": 1, "os.replace": 1, "os.rename": 1}
```

and `:973-976`:

```python
        for want, idx in _WRITE_CALLS.items():
            if _spelled(spellings, want) and len(n.args) > idx:
                out.append((n, n.args[idx]))
                break
```

`_write_targets`'s docstring promises `[(call, path expr)]`. For `os.remove`, `shutil.copy`,
`os.replace` and the module helper `_write(path, data)` the indices are right. For
`Path(...).write_text(body)` and `.write_bytes(body)` they are not: those are **methods on the
path object**, so `args[0]` is the CONTENT and the path is `n.func.value`. Driven:

```
_write_targets on `pathlib.Path(root,'a').write_text(BODY)`
  write call -> Name('BODY', Load())
```

`mutation_never_touches_the_live_tree` (`:9992-9994`) then asks whether that expression is
rooted at a `sandbox()` call:

```python
            for _call, path in targets:
                if not _is_rooted(tree, path, rooted):
                    return False               # a write that does not go through the sandbox
```

A correctly-sandboxed pathlib write would answer `False` here — and this net returning `False`
is a breach, which `main()` escalates to OWNER. **Latent, not live:** `mutate.py` writes through
its own `_write(path, data)` helper (`src/mutate.py:354`, called at `:794`, `:798`, `:1623`,
`:1644`, `:1721`), so today's tree never reaches this path. It becomes a false OWNER halt the
first time anybody rewrites a `mutate.py` write in pathlib.

**Confidence: high** — driven; `mutate.py` inspected to confirm it is latent rather than live.

---

## MINOR 3 — the "the stopped arm must LEAVE" test accepts an exit belonging to a NESTED loop

`src/drill.py:889-899` (`_gate_precedes_spawn`)

```python
        arm = _live_stmt_walk(_live_stmts(g.body))
        if not any(isinstance(x, exits) for x in arm):
            continue                            # the stopped arm must LEAVE, not fall through
```

`_live_stmt_walk` (`:624-626`) walks the whole subtree of every statement in the arm, nested
loops and nested function definitions included. A `continue` or `break` that belongs to an inner
loop therefore satisfies the check without ending the guarded function's turn at all. Driven
against the real helper:

```python
def start(name, args):
    stopped = _manager_stopped(name, args)
    if stopped:
        for x in []:
            continue          # <- belongs to the inner for, ends nothing
    return _guarded_popen(args)
```

```
_gate_precedes_spawn(..., exits=(ast.Continue,)) -> True
```

That fixture spawns unconditionally, and the net reports the gate as an interlock. Two callers
inherit it — `_the_loop_asks_the_gate` (`:3741`) and `both_launchers_ask_before_spawning`
(`:7134`) — and three hand-written twins carry the identical shape:

* `the_keeper_asks_before_restarting`, `:7090-7092`
* `_halt_is_not_breakage._consults_the_halt`, `:2167-2169`
* `_local_buckets_excluded_from_cloud_claims.ends_the_turn`, `:5661-5664`

The last is the widest, since it accepts `Return` and `Raise` too — a `return` inside a nested
`def` in the guarded arm would answer for it.

This is one degree weaker than the property order 07c7379597ba asked for. It is not exploitable
by accident in the current tree (none of the guarded arms contains a nested loop), which is a
fact about today's source rather than about the net — the same sentence `daemons_actually_check_their_own_source`
uses about its own three call sites at `:8869-8870`.

**Confidence: high** — reproduced against the real `_gate_precedes_spawn`.

---

## MINOR 4 — a junction probe grades its own CLEANUP, contradicting the ruling written six paragraphs above it

`src/drill.py:2726`

```python
        # Refused through the link, and the ordinary path still permitted -- a gate that refuses
        # everything passes every refusal test ever written.
        return through_link is None and bool(ordinary) and not os.path.exists(link)
```

The third conjunct asserts that `unstage()` succeeded. That contradicts the same function's own
docstring, `:2658-2677`, which rules at length that a probe which could not be staged or
unstaged is **noted, not graded**:

> "an unstageable junction is NOTED and returns True, which is a measurement declining to be
> taken rather than an alarm about the writable-surface gate. The alarm it used to sound was
> about the probe, and it was aimed at the owner."

`unstage()` itself already records its own failure through `silence.note` (`:2703-2704`), which
is the channel the ruling names. Grading it a second time in the return means a denied `os.rmdir`
— which on this machine needs nothing exotic, per the identical reasoning at `:2981-2988` — is a
BREACH, and a breached net escalates to OWNER.

The sibling probe written for the same bypass family does it correctly. `:2835-2838`:

```python
        return (not got.get("applied")
                and "gate" not in got
                and bool(got.get("error"))
                and "BREACHED" not in after and bool(ordinary))
```

— no cleanup term. Three other probes in this same area (`cannot_edit_shared_run_state` `:2989-2993`,
`blast_cap_bites` `:3067-3071`, `cannot_write_an_unlisted_top_level_file` `:3165-3169`) all note
a failed cleanup and deliberately do not fail on it, each under a comment saying why.

**Confidence: high** — the contradiction is between two passages of the same function.

---

## MINOR 5 — a bare `except Exception: continue` over record files, in the shape this file records removing

`src/drill.py:10526-10531` (`excluded_sources_keep_their_records`)

```python
        for p in _g.glob(os.path.join(HERE, "data", "records", "*.json")):
            try:
                with open(p, encoding="utf-8") as fh:
                    names.add(json.load(fh).get("source"))
            except Exception:
                continue
```

An unreadable or unparseable record is skipped and its source silently does not exist as far as
this net is concerned. `_policy_corpus_clean`'s docstring, `:5481-5486`, names exactly this
construct as one of the two defects the run #34 sweep filed against it:

> "THE SWALLOWED RECORD. A bare `except Exception: continue` scored an unreadable or unparseable
> record as clean. A record that cannot be parsed has not passed its structural rules — it is a
> file this net could not read, which is the 'absence read as clean' shape the whole project
> exists against."

The fix landed in `_policy_corpus_clean` (`:5499-5501`, which counts `unreadable` and fails on
it) and did not travel to this net. The consequence here is milder and points the other way — a
swallowed record makes `had` smaller, so the net is more likely to BREACH than to pass falsely —
but the breach would then name the wrong fault: the operator reads "an excluded source lost its
records" when what happened is "a record file would not parse".

**Confidence: high.**

---

## MINOR 6 — `_esc_sandbox`'s docstring describes a two-tuple; it returns three, and the third value it does build is never read

`src/drill.py:7162-7206`

Docstring, `:7165`:

> "RETURNS a (dir, restore) pair."

Code, `:7206`:

```python
    return d, filed, restore
```

Every caller unpacks three (`_esc_probe` `:7216`, `a_halt_that_loses_the_race_...` `:7456`,
`the_destructive_tool_...` `:7574`), so the code is right and the sentence is stale.

Separately, at `:7193-7198`:

```python
    filed, recorded = [], []
    ...
    _H.record = lambda *args, **kw: recorded.append((args, kw))
```

`recorded` is written and never read — it is not returned, and no probe in the file reaches it.
The docstring's justification for building it, `:7183-7184`, says:

> "The calls still HAPPEN — the probe below that asserts an escalation reaches the queue reads
> the recorder to prove it"

The probe it means, `an_escalation_reaches_the_queue_addressed_and_graded` (`:7363-7373`), reads
`filed` — the work-order stub — not `recorded`. The health recorder is stubbed correctly (that
part is load-bearing: it keeps synthetic escalations out of `state/failures.json`), but its
capture list is a value computed and dropped, which is the file's own most-cited defect shape
(`:6308-6309`, `:9640`).

**Confidence: high** — verified by reading the whole function and by counting occurrences.

---

## MINOR 7 — four clauses in the `_safe_name` net cannot fail

`src/drill.py:2233-2240`

```python
    hostile = 'Kobold Press: ../../etc/passwd\\x00 & "quoted" (Midgard)'
    out = ESC._safe_name(hostile)
    kept = set(out) - set("-_")
    return (out and all(c.isalnum() for c in kept)
            and "/" not in out and "\\" not in out and ":" not in out and ".." not in out
            ...
```

`all(c.isalnum() for c in kept)` already forbids every character outside `{-, _}` that is not
alphanumeric. `/`, `\`, `:` and `.` are all non-alphanumeric and none of them is in `-_`, so any
output containing one of them fails the `isalnum` clause first. Checked:

```
char '/'  survives isalnum-all? False
char '\\' survives isalnum-all? False
char ':'  survives isalnum-all? False
char '.'  survives isalnum-all? False
```

The four clauses can therefore never be the reason this net returns `False`. Harmless as
belt-and-braces, and the docstring at `:2230-2231` correctly identifies the `isalnum` clause as
the load-bearing one — but they are four checks that cannot fail, in the file whose stated
purpose is finding those, and `liveness.py`'s tautology limb (counted by `LIVENESS_CEILING`,
`:125`) is exactly the instrument that would be expected to see them.

**Confidence: high** — driven.

---

## MINOR 8 — `_quiet()`'s docstring overstates what the stand-in silences

`src/drill.py:348-361`

```python
def _quiet(mod):
    """A stand-in for `silence` whose `note()` goes nowhere, for nets that drive real phases.
    ...
    """
    import types
    out = types.SimpleNamespace(**{k: getattr(mod, k) for k in dir(mod)
                                   if not k.startswith("__")})
    out.note = lambda *a, **k: None
    return out
```

The namespace holds the *same function objects* as `silence`, and those functions resolve `note`
from `silence`'s own module globals, not from the namespace. So a `note()` raised **inside** a
silence helper reached through the stand-in still goes to the real ledger. Confirmed:

```
q.note is S.note                       -> False
q.replace_if_unchanged is S.replace_if_unchanged -> True
```

and `silence.replace_if_unchanged` calls the module-global `note` at `src/silence.py:559`,
`:564`, `:577` and `:586`.

This does not break the intended use — `pipeline`'s phases call `PL.silence.note(...)` directly,
which the stand-in does intercept — and the project already has the right tool for the other case
(`_deliberately_failing`, `:265`, which patches `health.record` instead, and works precisely
because `silence.note` imports `health` late at `src/silence.py:748-751`). The docstring simply
promises more coverage than the mechanism can give, which matters because it is the sentence a
future net author will trust when deciding whether they need `_deliberately_failing` as well.

**Confidence: high** — driven, and the internal `note()` call sites in `silence.py` were read.

---

## MINOR 9 — a source-shape net is still a closure carrying an unusable `src=` parameter

`src/drill.py:2845` (`_write_lane_checks_the_halt`, defined inside `drill_local_agent`)

```python
    def _write_lane_checks_the_halt(src=None):
```

`_srcdir`'s docstring, `:396-408`, and `_guards_are_wired_where_claimed`'s, `:6410-6414`, both
name this exact shape as a fault and record the remedy:

> "MODULE LEVEL, LIKE THE OTHER SOURCE-SHAPE NETS, and for the reason `_srcdir` gives: it was a
> closure carrying an unusable `src=` parameter, so the one way to prove it still refuses —
> point it at a tree with the guards moved into dead code and watch it go red — could not be
> performed on the net itself, only on a copy of its body."

`_write_lane_checks_the_halt` was not moved with it. `net()` calls it with no arguments
(`:2874-2875`), so its `src=` is unreachable from outside and the only way to drive it against a
defeat tree is the module-level `_SRC_OVERRIDE`. Its two sibling nets in the same area,
`_failed_revert_is_escalated` (`:2476`) and `_run_marks_a_landless_run_failed` (`:2572`), are
both at module level and take `src` for real.

**Confidence: high** — the remedy is written out in the file and was applied to one net and not
the other.

---

## MINOR 10 — a sandbox probe leaks real-prefix directories into TEMP if its setup raises partway

`src/drill.py:10134-10153` (`_a_reap_never_takes_a_live_runs_sandbox`)

```python
        made = []
        child = _sp.Popen(...)
        try:
            live = _mk("netlive", child.pid, started=time.time())
            expired = _mk("netexpired", ...)
            dead = _mk("netdead", ...)
            unowned = _mk("netnone", None, age=10 * 3600)
            made = [live, expired, dead, unowned]
            ...
        finally:
            ...
            for d in made:
                shutil.rmtree(d, ignore_errors=True)
```

`made` is only populated after all four `_mk()` calls succeed. If the second, third or fourth
raises, `made` is still `[]` and the directories already created leak. They carry
`M.SANDBOX_PREFIX`, so they are indistinguishable from real abandoned mutation sandboxes — which
is the litter this very net's neighbour, `abandoned_sandboxes_are_reaped` (`:10031`), exists to
measure. The sibling gets this right by naming both paths before the `try` (`:10070-10071`) and
removing both unconditionally in the `finally` (`:10089-10090`).

**Confidence: high.**

---

## MINOR 11 — one cleanup swallow that does not follow the file's own recorded discipline

`src/drill.py:6742-6747` (`_twins_ignores_a_foreign_tree`)

```python
        if child is not None:
            try:
                child.kill()
                child.wait(timeout=5)
            except Exception:
                pass
```

The child is a `time.sleep(45)` interpreter. A failed kill leaves it running for up to
forty-five seconds — long enough to overlap the next battery — with nothing recording why. Five
other cleanups in this file were converted off `except: pass` to `silence.note` for weaker
consequences, each under a paragraph arguing the case: `drill.py:2028-2030`, `:2703-2704`,
`:2989-2993`, `:3067-3071`, `:3165-3169`. This one was not.

**Confidence: high** — the discipline and its reasoning are stated five times in the same file.

---

## QUESTION 1 — two probes compare LIVE shared ledgers byte-for-byte across a window in which sixteen agents may be writing

`src/drill.py:9739`

```python
        return refused_blob and not landed and snapshot() == before
```

and `:7043-7044`

```python
        return (set(WO._load()) == before
                and _rows_in(WO.CLOSED_LOG) == trail_before)
```

**Reading A (deliberate):** the strictness is argued for explicitly at `:9701-9702` — "Compared
as bytes rather than by counting keys, because an unrelated recorder adding one entry while a
probe leaked one would net to zero" — and at `:7016-7017` for the identity comparison. Any
weaker comparison genuinely can be defeated by a coincidence.

**Reading B (a hazard the argument does not cover):** the argument is about a concurrent write
*masking* a leak. It does not address the other direction, which is that a concurrent write by
any of the sixteen agents this project runs — any `silence.note` from any job for the first, any
detector filing or closing an order for the second — makes the comparison unequal and the net
BREACH over a probe that leaked nothing. A breached net is an OWNER halt. This file elsewhere
treats exactly that outcome as disqualifying: `_step4_needs_its_plan` (`:1539-1547`) was
rewritten off a fixed temp path because "a false breach here is worse than a missing net, because
a net that is red for an unrelated reason is DISABLED AS A DETECTOR", and
`twin_detection_does_not_match_bystanders` (`:9005-9015`) was rewritten off the live process
table on the same grounds — "A net whose answer depends on what happens to be running when it
looks is not testing the code."

I do not have a measurement of how often this actually fires, so I am not filing it as a defect.
The question for the owner is whether these two nets are meant to be exempt from that ruling, and
if so why the exemption is not written where the other two are.

---

## QUESTION 2 — `excluded_sources_keep_their_records` breaches when no excluded source ever had records

`src/drill.py:10532-10535`

```python
        # At least one excluded source that HAD records must still have them. If every excluded
        # source lost its records, "exclusion" has quietly become deletion.
        had = [n for n in ex if n in names]
        return bool(had) or not names
```

The comment says "that HAD records", but nothing here can distinguish "had records and lost
them" from "never had any". A source excluded before it was ever catalogued — which Hard Rule 2
in `CLAUDE.md` describes as an ordinary situation, since about half the roll predates the
Acquisitions Index — contributes no name, and if every excluded source is in that state the net
returns `False` and halts the library over a lawful configuration.

**Reading A:** today's four exclusions all have records (stated at `:10455`), so the state cannot
arise and the strictness is free.
**Reading B:** that is a fact about the 2026-08-25 exclusions rather than about the rule, and the
next exclusion of an uncatalogued source turns it into an OWNER halt.

Not filed as a defect because the intended semantics are genuinely ambiguous.

---

## QUESTION 3 — `drill_park` and `drill_rung_four` escalate against the LIVE escalation module while `_esc_sandbox` exists for that purpose

`drill_park.area_fault_does_not_close_the_park` (`:2011-2012`) calls
`ESC.escalate(ESC.SUPERVISOR, "DRILL_AREA", ...)` against the real module, which writes
`state/escalation.log`, `state/escalations/__drill__.log` and a real work order (resolved
afterwards). `drill_rung_four`'s three probes (`:2964`, `:2983`, `:7004`) do the same against
`state/STOPPED.json`. `_esc_sandbox` (`:7162`) exists precisely to redirect `HALT_FILE`, `LOG`,
`SRC_LOGS` and `STOPPED` and to stub `workorders.file_order` and `health.record`, and its
docstring argues the case at `:7178-7184`.

**Reading A (deliberate):** the older areas predate `_esc_sandbox`, their litter is genuinely
cleaned (I verified `_sweep_probe_litter`'s `where=` values —`__drill__`, `__drill_rung4__`,
`__drill_rung4b__`, `__drill_litter_probe__` — all match `workorders.SELFTEST_SUBJECT`
(`src/workorders.py:81`), so their closures route to `SELFTEST_LOG` and not to the paper trail),
and driving the real module is arguably the stronger test.

**Reading B:** they still append rows to two live append-only ledgers on every battery run, which
is what `_esc_sandbox` was written to stop, and the split leaves the "does the drill touch live
state" question with two different answers depending on which area you read.

I confirmed the litter routing rather than assuming it, so this is a consistency question, not a
leak.

---

## QUESTION 4 — `_ledger_redirected`'s containment assertion is a string prefix, not a path-component test

`src/drill.py:232-237`

```python
        real = os.path.abspath(keep["HERE"])
        for n in names:
            got = os.path.abspath(getattr(_LG, n))
            if not got.startswith(os.path.abspath(root)) or got.startswith(real + os.sep):
                raise AssertionError(...)
```

`got.startswith(abspath(root))` is satisfied by a sibling directory whose name merely begins with
`root`'s name (`.../drill_x` vs `.../drill_xyz`). The second clause is correctly written with
`+ os.sep`; the first is not. In practice every redirected value is built by joining `root` a few
lines above, and `root` comes from `mkdtemp`, so the check cannot be wrong today — but this
helper's whole subject (`:200-218`) is that a future path added to `ledger_guard` must be caught
loudly rather than silently, and the guard that is supposed to catch it is the looser of the two
comparisons in the same expression.

---

## What was checked and found sound

Recorded so a later reader knows these were examined rather than skipped.

* **All 37 area functions reach `main()`'s run list.** Verified by parsing the file.
* **`_live_stmts` / `_live_walk` loop-`else` handling** (`:530-621`) is correct in both
  directions, and `the_reachability_primitive_understands_loop_else` (`:6637`) drives both.
  `while False:` contributes its `else` and drops its body; `while True:`'s `else` is skipped in
  `_live_walk` at `:612-614` while the body is still walked.
* **`_no_programmatic_clear`'s exemption list** (`:3294`) matches on the relative path produced
  by `_src_py_files`, so `deprecated/escalation.py` cannot exempt itself by basename — the
  property its docstring claims at `:3288-3289` holds.
* **Probe litter routing.** Every `resolve_code` call the drill makes either carries a
  `where=` matching `workorders.SELFTEST_SUBJECT` (`^__drill[A-Za-z0-9_]*__$`) or passes
  `synthetic=True` (`blast_cap_bites`, `:3089-3090`, where `where=""` and the order is a real
  safety). None of them can reach the closed-order paper trail. Checked against
  `src/workorders.py:459-481` and `:535`.
* **`_deliberately_failing`** (`:265`) works: `silence.note` resolves `health.record` through a
  late `import health` (`src/silence.py:748-751`), so patching the module attribute intercepts it.
* **Exact float comparisons in `drill_resonance`** (`:10869-10870`, `:10894-10895`) are safe —
  `resonance.hodge_decompose` rounds `eta`, `curl_fraction`, `ladder_representable` and
  `irreducibly_chord` to 4 or 1 decimal places before returning them.
* **`main()`'s verdict write** (`:11026-11060`) checks the return of `silence.write_json` and
  prints a warning when it did not land. **`main()`'s area loop** (`:10962-10969`) records an
  area that raises as a breach rather than losing the whole run. Both are the corrected forms
  their comments describe.
* **`_the_log_roll_off_archives_before_it_trims`'s arithmetic** (`:9359-9372`) is right:
  `LOG_CYCLES + 2` seeded plus one appended leaves exactly three to roll off, and the
  union test compares sequences rather than sets.
* **The closure captures** at `:3372` and `:6037` (`(lambda v: (lambda: f(v)))(s)`) bind
  correctly; the late-binding trap is avoided.
