# sweep66 batch 02 — AUDIT

## Scope

`src/verify_math.py`, **13,416 lines, all of them**. Read from line 1 to line 13,416 in
consecutive ~800-1,000-line chunks with the Read tool. Nothing was sampled and nothing was
skimmed by grep; grep was only used after the read to confirm or refute specific candidates.
This is the only module in the batch (frozen plan `state/sweep_plan/run66.json`, batch 2).

Read-only throughout. Nothing under `src/`, `data/`, `state/`, `output/`, `prompts/`,
`reference/` or the repo root was edited. I did not run `verify_math.py`, `drill.py`, or any
job. The only executions were read-only: `grep`/`sed` over source,
`json.load` of `state/workorders.json`, and one call to `silence._handlers('verify_math.py')`,
which parses the file and reports its except-handlers without writing anything. No subagents
were spawned.

## Prior-audit cross-check (handoff/sweep65/AUDIT_batch02.md)

- **sweep65 finding (MINOR, bare `assert` at the old line 11140): FIXED.** The line now reads
  `if source_name in WS.WIKI_OVERRIDES: raise AssertionError(...)` at
  `verify_math.py:11140-11143`, with a comment crediting sweep65 batch02. A grep for
  `^\s*assert ` over the whole file returns nothing. The file grew by exactly the three lines
  that fix added (13,413 → 13,416).
- **sweep65 "questions: none", with the three charter pins re-verified.** All three still stand
  as described: M18 saturation `[control]` row at `:8283`, the M5+ Instrument window pin
  (`KNOWN DEFECT: the Instrument has NO resolution above M4`) at `:1460`, and the
  `YEARS_PER_UNIT_DISTANCE` INFO line (order 9736a5a73b02) at `:11563`.
- **sweep65 "cleared" list.** I re-traced the items it cleared and agree with every one: the
  `check()` core and the atexit crash net, the four ledger wrappers and their driven controls,
  `_slices_of` and its canary, `_disarmed_rows20i`, the four end-of-file self-scanners (§20ad,
  §20z tol scan, §20z prose-backed scan, §20ae), `_recursive_py_paths`, the §20u digest gate,
  and the `CREATE_NO_WINDOW` on the one spawn this file makes (§20a).

Open work orders naming this file (checked in `state/workorders.json`): 1e6f99e54b25,
21c075e5e2d6, 3099138a82bd (hand-run tools and the halt; `_INTERLOCKED` roster), 34ec8a90c42f,
4c2101d54c10, 7099a092abd3 (rows on caller-less functions), 79d51aef8b71 (GPU hermeticity),
a66423722e45, de265a105279 (new-module sweep-completeness row). None of them covers the
findings below. No order mentions `_writejson_calls_discarded_b2`, the 1018d49b186e control,
or the three stale citations.

## Findings (DEFECTS)

### D1 — MINOR, VERIFIED — the 1018d49b186e positive control tests a re-typed copy of the scan, not the scan

`verify_math.py:9466-9497`. The real scan is a function that takes a PATH:

```python
def _writejson_calls_discarded_b2(path):
    with open(path, encoding="utf-8") as f:
        tree = _ast_b2.parse(f.read())
    ...
        if (isinstance(call, _ast_b2.Call)
                and isinstance(call.func, _ast_b2.Attribute)
                and call.func.attr == "write_json"):
```

and its "positive control" re-types the same predicate inline instead of calling it:

```python
_synthetic_b2 = "import silence\nsilence.write_json(PATH, obj)\n"
_synthetic_tree_b2 = _ast_b2.parse(_synthetic_b2)
_synthetic_bad_b2 = [n.lineno for n in _ast_b2.walk(_synthetic_tree_b2)
                     if isinstance(n, _ast_b2.Expr) and isinstance(n.value, _ast_b2.Call)
                     and isinstance(n.value.func, _ast_b2.Attribute)
                     and n.value.func.attr == "write_json"]
check("1018d49b186e: discard-detector finds a real discarded write_json (positive control)",
      _synthetic_bad_b2, [2])
```

**Why it is wrong.** This is exactly the defect order 3c72359c53aa fixed at four other scans in
this same file, in the file's own words: "The order 873330d2e98d canary used to test a RE-TYPED
COPY of this predicate, so a typo in the real scan left the scan and its canary both green"
(`_ctx_literals_in19ab` docstring, `:3924-3926`; likewise `_failopen_in20p` `:7523-7524`,
`_clear_callers20t` `:8097-8098`, and the batch1 header `:9088-9093`, which declares that
repair DONE). This fifth scan was not included.

**Failure scenario.** A later edit typo's `"write_json"` inside `_writejson_calls_discarded_b2`
(or changes the node test). The function then returns `[]` for all three modules, so the three
rows at `:9483` ("write_json verdict is captured, not discarded") read green whatever
catalogue_aurora.py / scope.py / sevenfold.py do, and the control at `:9496` still reads
`[2]` because it never calls the function. A reintroduced discarded `silence.write_json(...)`
in any of the three modules then goes unseen.

**Verified** by reading both blocks in full: the control shares no code with the function it
claims to control. The fix is the one already used for the other four scans: split the body
into a source-taking helper that both the path wrapper and the control call.

### D2 — MINOR, VERIFIED — three cross-module line citations have gone stale, beside a section that says they were converted

§20ad (`:12311-12321`) records that cross-module line citations rot on the other file's clock
and says the six it knew of were "named here by symbol instead" (order 89503c58409f). §20ad's
scanner deliberately ignores citations of OTHER files (fixture "a citation of another file",
`:12453`), so nothing in the battery catches these three, all of which point at the wrong line
today:

| Site | Text | Where the thing actually is now |
|---|---|---|
| `:4700` (inside the `note=` of `check("and the boundary MOVES WITH THE CONSTANT ...")`, so it prints on a red row) | "a literal spelled at standards.py:751 instead of the constant" | the `calls < MIN_CALLS_TO_JUDGE_RATE` cut is `standards.py:878` |
| `:5112-5113` (comment in `_for_owner_landing_b19`) | "write_json IS the temp-then-replace_retry helper ... (silence.py:511, 518)" | `def write_json` is `silence.py:956` (`replace_retry` `:905`); 511/518 are inside the handler audit |
| `:11415` (§b6 order 2f0a734d8c15 comment) | "Revert withdraw_chapters.py:176 to `default="2026-08-25"`" | `ap.add_argument("--label", ...)` is `withdraw_chapters.py:251` |

The first one is the sharpest: it is the very `standards.check()` cut that §20ad names as one of
the six citations already converted to a symbol, and it is still numeric in a row note that a
reader gets only when that row is red. **Verified** with `grep -n` against the current
`standards.py`, `silence.py` and `withdraw_chapters.py`. Fix: cite by symbol, as §20ad asks.

(Also stale but plainly historical, so not counted: `:5394` "overnight.py:741, prose", which
describes where a docstring sat on 2026-08-29; that sentence is now around `overnight.py:893`.)

## Questions (possibly deliberate; the owner or a maintainer decides)

### Q1 — unguarded subscripts of the subject's output at module level

Orders e0d71f507510 and 8cdbd0fb6c14 set the house rule that a row which subscripts a result
must not raise at module level. With the atexit net the run still reads RED rather than BROKEN,
but every row after the raise never runs. `_at_vm` and `_Absent19ai` exist for this. Several
rows still subscript the output of the code under test directly, for example:

- `:2859`, `:2861` — `_rows19h[0]["error"]`, `_rows19h[0]["count"]` right after
  `check(..., len(_rows19h), 1)`. If `record_unrecognised` regressed to writing nothing, this
  raises `IndexError` inside the §19h-bis `try` and the remaining ~10,500 lines of the battery
  do not run.
- `:3049` — `_RG.read(_gp)["superseded"]["agent"]` (`KeyError` if `claim` stops recording
  `superseded`).
- `:4160-4162` — `json.load(open(_clp19ad))` for the foreground claim file
  (`FileNotFoundError` if `lane(priority=True)` stops writing it).

Does the e0d71f507510 rule cover every subscript of a subject's output, or only detector
controls? If it covers all of them, this is a class-wide sweep, not a one-line fix.

### Q2 — three deliberate swallows without the marker this file uses elsewhere

`silence._handlers("verify_math.py")` flags 15 handlers as silent. Most of them are verdict
captures, and a comment says so (`_raises`, `_at_vm`, the §20i probe, `_sigma_table_verdict`,
and so on). Three have neither a `silence.note` site nor the `_ = "silence-exempt: ..."` marker
the file uses at `:2737`, `:3390` and `:4316`:
`:1599-1601` (THREAD_INTEGRITY_FLOOR read → `_fl42 = None`),
`:5205-5206` (`_follows_continuation`: `except SyntaxError: return False`), and
`:7044-7048` (unreadable sweep shard → `continue`, with an explanatory comment). All three fail
closed: the dependent row goes red, or an older run gets asked. None hides a pass. The only
question is whether to add the marker so the house audit stops counting them.

### Q3 — probe files in the live `state/` directory (noted, not filed)

§19h-bis writes `state/_VM_UNRECOGNISED_TEST.json` (`:2849`) and §20g writes
`state/_VM_ATOMIC_PROBE.json` (`:6224`) into the LIVE tree. Two battery processes in the live
tree at once would race on those paths, for example one removing the other's file between
`record_unrecognised` and `unrecognised_open`. Order c349a51ee2c5 already rules that
verify_math is not safe to run concurrently, and mutate.py's sandbox copies `state/`, so this
is the known constraint and not a new defect. It is recorded so nobody re-derives it.

## Cleared (looked at closely and found correct)

- §20n finished-run selection (`:7037-7092`): quiescence plus all-batches detection is sound,
  and `_planned20n` comes from the live `batches(16)`.
- §20q `_used20q >= 12` (`:8025`): the current population in pipeline.py is exactly 12
  (11 `land_json` plus 1 `land_onomasticon`), so the floor is tight and not slack.
- §20ai/§19ai pin-and-watch transport control (`:4586-4616`), including the `/api/generate`-only
  refusal: correct as documented.
- §20p `_INTERLOCKED` roster reconciliation (`:7486-7519`), both directions: correct. The
  halt-refusal policy question stays with open orders 1e6f99e54b25 / 21c075e5e2d6 /
  3099138a82bd.
- §b3 declared-vs-emitted partition (`:9234-9428`) and its four-arm control: correct. Abstention
  requires either a fired granted class or standards.py's own drop register.
- Owner-held gates: §20x pins `prose_enabled: true`, `step4_enabled: true` and
  `prose_min_cited_fraction: 0.35` as exact values (`:7218`, `:7271`, `:7278`, `:7295`). These
  are working as designed and must not be relaxed.

## Coverage note

Read in full, and only: `src/verify_math.py`, lines 1-13,416.
