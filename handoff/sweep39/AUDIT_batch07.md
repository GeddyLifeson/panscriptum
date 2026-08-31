# run39 comprehensive source audit — batch 07

Modules owned by this batch, taken from `sweep_plan.batches(16)[6]['modules']`, all read IN FULL
(no sampling, Hard Rule 0):

    mutate.py            1772 lines
    silence.py            762 lines
    manifest_builder.py   592 lines
    autostart.py          489 lines
    pick_model.py         381 lines
    retry_synthesis.py    322 lines
    render.py             278 lines
    propagation.py        235 lines
                         ----
                         4831 lines

`mutate.py` was READ, never run — a mutation pass is active on this machine.

Every finding below was checked against the current source before it was written down. Where two
readings are defensible the entry says so and is filed as INFO/QUESTION rather than as a defect.

---

## mutate.py

### M-01 (MAJOR) — `red_gates()` is called and the answer thrown away on a quiet tree

`src/mutate.py:1636` computes `red = red_gates(base)`. The only consumer is `src/mutate.py:1640`,
`if moving and red:`. When `moving` is False, `red` is never read again.

Why that matters, in the module's own terms. A mutant is killed by
`sig != base.get(gname)` (`src/mutate.py:1471`). A gate that is ALREADY red in the baseline
carries its redness into every mutant's signature, so it matches the baseline and kills nothing —
`red_gates`' own docstring and the refusal text at `src/mutate.py:1644-1646` both say exactly this
("a gate that is red in it is disabled as a detector for the whole run"). On a quiet tree with a
red baseline the run proceeds with that gate switched off as a detector and **nothing in the
output names it**: the refusal block that would have listed the red gates is behind `moving`, and
the line printed instead is `all gates reproducible; mutants judged by DIFFERENCE from the above`
(`src/mutate.py:1671`), which reads as an all-clear. The baseline signatures are printed at
`src/mutate.py:1612-1614`, so an `rc=1|...` is on the page, but no line says which gates are dead
or that the coverage number is over a reduced battery.

Remedy: keep the refusal gated on `moving and red` — that ruling is deliberate and correct — but
print the red gates unconditionally when `red` is non-empty, naming each one and saying in the
same breath that it cannot kill any mutant this run, and carry the list into the run result and
into every `_journal` row beside `tree_was_moving` so a survivor read days later shows which
detectors were down when it was scored.

### M-02 (MINOR) — the survivor journal and the work-order text cut the diff at 120 characters

`src/mutate.py:1476-1477`, `src/mutate.py:1494-1495` and `src/mutate.py:1498-1499` all write
`old_line.strip()[:120]` / `new_line.strip()[:120]`. Those values are persisted to
`state/MUTANTS_SURVIVED.jsonl` (`_journal`, `src/mutate.py:752`) and are pasted verbatim into the
work order raised by `file_orders` (`src/mutate.py:1535-1539`), which is the permanent record of
what was changed. There is no `…` and no "and N more" marker, so a cut is indistinguishable from a
short line. This directly contradicts the module docstring's own promise that each survivor "is
filed with its exact diff rather than a count" (`src/mutate.py:33`).

**Currently inert, measured 2026-08-30**: no line in any of the three `TARGETS` has more than 120
characters after `.strip()` (assay.py 0, prose_gate.py 0, escalation.py 0), so nothing on disk is
truncated today. It is a latent violation that bites the first time a target gains a long line or
`TARGETS` changes.

Remedy: store the whole line. If a bound is wanted for the printed line only, keep the cut in the
`print` at `src/mutate.py:1744-1745` (already `[:70]`, and reversible because the full value is in
the record) and take it off the persisted and filed values.

### M-03 (MINOR) — stale cross-reference: `_lock_release` cites `:222`

`src/mutate.py:260-261` reads "`_lock_acquire` stamps a per-run token into the record at :222".
Verified against the current file: `src/mutate.py:222` is a comment line
(`# mutants on disk and no way to attribute either" the lock exists to prevent.`). The token is
stamped at `src/mutate.py:243` (`"targets": list(targets), "token": token,`).

Remedy: cite the symbol, not the line — "stamps a per-run token into the record it writes" — which
is the argument `src/mutate.py:944-946` already makes for this very file.

### M-04 (INFO / QUESTION) — `drill.py:4256 -> M.reap_orphans()`

`src/mutate.py:906` names the reap-ledger call site as `drill.py:4256 -> M.reap_orphans()`.
`drill.py:4256` is currently `return records and carried`, inside
`_local_buckets_excluded_from_cloud_claims`'s neighbour. The live `reap_orphans` call sites in
`drill.py` are `6553` and `6614` (plus docstring mentions at `6508` and `6537`).

Two defensible readings, so this is a QUESTION and not a finding: the sentence may be quoting a
ledger row captured on 2026-08-27 — a historical record of what the ledger said at the time,
which does not go stale — rather than citing the current file. If that is the intent, saying so
("the ledger row read `drill.py:4256 -> M.reap_orphans()` at the time") would settle it.

### M-05 (MINOR) — stale cross-reference: `generate.py:555-558`

`src/mutate.py:946` cites "the same argument generate.py:555-558 makes for symbolic
`silence.note()` tags". Verified: `generate.py:553-560` is the EVIDENCE FLOOR print loop
(`print("\nEVIDENCE FLOOR — %d source(s) held back...")`). The symbolic-tag argument is at
`generate.py:598` ("the symbolic form other modules use (`workorders.py:load`, ...").

This is the sharpest instance in the batch, because the sentence containing the wrong line number
is itself the sentence arguing that "a line number inside a comment is a claim nothing can keep
honest".

### M-06 (INFO) — `_TOKEN_ENV` is written and read by nothing

`src/mutate.py:131` declares `_TOKEN_ENV = "PANSCRIPTUM_MUTATION_TOKEN"`; `src/mutate.py:336` puts
the token into `os.environ`; `src/mutate.py:345` pops it. A tree-wide grep over `src/` and
`handoff/` finds no other reader of either the constant or the environment variable name. The
comment at `src/mutate.py:333-335` states that the gate subprocesses inherit it and "can tell
'this tree is broken because WE are breaking it' from 'this tree is broken and nobody is admitting
to it' -- which is the distinction the drill got wrong the first time". No gate consults it.

Already reported once (`handoff/sweep34/AUDIT_batch16.md:57`) and still standing, which is why it
is repeated here rather than assumed closed. Either wire a reader (the honest one is
`escalation`/`drill` checking it before treating a red as a real fault) or delete the constant and
the paragraph that describes a mechanism that does not exist.

### M-07 (MINOR) — `sandbox()` invents a module count in its own refusal

`src/mutate.py:1079`: `% (", ".join(absent), len(missed) or 1)`. When a target is absent from the
sandbox but `missed` is empty — the case where the file was never named by `os.listdir(SRC)` at
all, so no copy was ever attempted — the message asserts "1 module(s) could not be read". Nothing
failed to be read; the file was not there to list. The two conditions are conflated under one
number, and the number is fabricated.

Remedy: report the two separately — `%d module(s) could not be read` from `len(missed)`, and say
"and %s was not present in src/ when it was listed" for the `missed == []` case.

### M-08 (MINOR) — the `_spot`-failed fallbacks reintroduce the first-occurrence rewrite

`src/mutate.py:601`, `src/mutate.py:614-615` and `src/mutate.py:627-628` fall back to
`line.replace(old, new, 1)` when `_spot()` cannot place the token. That is exactly the construction
the docstring at `src/mutate.py:383-390` identifies as the coverage hole this function was rewritten
to close ("always rewrites the FIRST occurrence of the target text on the line ... the dedup step
below then collapsed the two identical-looking entries into one, so the second `<` was a mutation
NEVER ATTEMPTED, silently absent from both the killed and the survived counts").

The dedup at `src/mutate.py:637-642` keys on `(lineno, new_src)`, so two `not` / `True` / `False`
nodes that both fall back on the same line produce the identical `new_src` and collapse — and
because the fallback SUCCEEDED, `_skip()` is not called either, so the lost site is absent from
`not_attempted` as well as from the mutant list. Narrow (it needs two same-token nodes whose spans
cross lines and start on the same line), but it is the one path where a lost site is invisible in
both directions.

Remedy: on the fallback path, search forward from the previous match's end for that line rather
than from position 0, and `_skip()` any occurrence the fallback cannot place distinctly.

### M-09 (INFO) — `capped` can be true without a cap, and the true total is not carried

`src/mutate.py:1518`: `"capped": bool(limit) and len(muts) == limit`. When the module happens to
produce exactly `limit` mutants, nothing was cut and the result still says `capped: True` and the
CLI prints "this is NOT the whole set" (`src/mutate.py:1727`). The direction is the safe one
(over-warning), but the result also never carries the pre-slice total, so a reader of the dict has
the marker without the number. Remedy: capture `total = len(muts)` before the slice at
`src/mutate.py:1444` and report both.

---

## silence.py

### S-01 (MAJOR) — `_OBSERVED_TOKENS` is a raw substring test, so an unrelated identifier can mark a silent handler observed

`src/silence.py:149-151`:

```
body = "".join(ast.dump(stmt) for stmt in node.body)
if any(t in body for t in _OBSERVED_TOKENS):
    return True
```

`ast.dump` serialises identifiers, attribute names and string-literal CONTENTS, and the test is a
bare case-sensitive `in`. So any handler whose body merely mentions a name containing `log`,
`note`, `record`, `health`, `print`, `swallow`, `silence` or `LEDGER` is classified OBSERVED
whether or not it records anything. `log` is inside `catalogue`, `dialogue`, `prologue`, `login`;
`note` is inside `notes`, `notebook`, `denote`; `record` is inside `recorded`, `unrecorded`.

**Verified live, not hypothetical.** `src/codewatch.py:363-369`:

```
except FileExistsError:
    try:
        if time.time() - os.path.getmtime(LEDGER_LOCK) > LOCK_STALE_SECONDS:
            os.remove(LEDGER_LOCK)
            continue
    except OSError:
        pass
    time.sleep(wait)
```

The outer handler records nothing, re-raises nothing and never touches a bound name — it is
exactly the shape this module exists to find — and it is classified OBSERVED because its body
names `LEDGER_LOCK`. A whole-tree scan run for this audit found 30 handlers marked observed by
substring alone with no recorder call in the body; 29 of them are the documented
`_ = "silence-exempt: ..."` markers, which is correct and intended (`silence` is in the token list
for that purpose), and `codewatch.py:363` is the false positive.

The direction of failure is the hiding one, and it hits both siblings: a handler wrongly marked
observed drops out of the SILENT count `main()` prints (`src/silence.py:229`) and out of the
rewrite list `instrument()` builds (`src/silence.py:719-721`), so it is never counted and never
instrumented.

Remedy: stop testing the dump. Test the parse tree the way the `Raise` check at
`src/silence.py:152` already does — walk the body for a `Call` whose `func` is a `Name`/`Attribute`
resolving to one of the recorders, and test the `silence-exempt:` exemption as a string CONSTANT
starting with that marker rather than as a substring anywhere. Failing that, at minimum require a
word-boundary match (`re.search(r'\b'+t+r'\b', body)`), which removes the `catalogue`/`LEDGER_LOCK`
class of false positive at the cost of one regex per token.

### S-02 (MINOR) — a comment says "Unreachable" about a reachable line

`src/silence.py:415-417` reads "Unreachable: the last PermissionError attempt returns above." The
line is reached whenever `attempts <= 0`, because the `for a in range(attempts)` loop at
`src/silence.py:378` does not execute at all. `attempts` is a public keyword argument of
`replace_if_unchanged`. Remedy: either state the real condition ("reached only when `attempts` is
non-positive, which no caller passes") or reject `attempts < 1` at the top.

### S-03 (MINOR) — stale cross-reference: `navtree.py:297`

`src/silence.py:493` says "One live caller asks for it: `navtree.py:297`, writing
`data/NAVTREE.json`". Verified: the `silence.write_json(OUT, data, separators=(",", ":"),
ensure_ascii=False)` call is at `navtree.py:304`; `navtree.py:297` is a comment line inside the
"GATED, AND THIS IS AN IDENTITY FAULT" paragraph.

### S-04 (MINOR) — misdirected cross-reference: `hostcheck.py:170`

`src/silence.py:527` says "`hostcheck.py:170` records the same litter one layer up for
`replace_if_unchanged`". Verified: `hostcheck.py:170-172` is the `except Exception: _unlink(tmp);
raise` on the JSON-DUMP path — the analogue of `write_json`'s FIRST `_discard_tmp`
(`src/silence.py:516`), not of the denied-replace one this comment is attached to. The litter it
actually describes is cleaned at `hostcheck.py:177-179`, after
`landed, why = silence.replace_if_unchanged(tmp, F.HOSTS, digest)` at `hostcheck.py:173`. The
citation points at the wrong one of two nearly identical cleanups.

### S-05 (MINOR) — stale cross-reference AND a stale count: `chain.py:141/159 and 48 others`

`src/silence.py:713-714` reads "`_ = "silence-exempt: ..."` (this project's documented exemption
marker, chain.py:141/159 and 48 others)", and `src/silence.py:715` says "would have rewritten all
fifty". Verified:

* the two markers in `chain.py` are at `chain.py:213` and `chain.py:242`, not 141 and 159
  (`chain.py:139-143` and `157-161` are comment prose about write-then-rename and
  `_corpus_root_state`);
* `grep -rn "silence-exempt" src/*.py` returns **35** occurrences in the whole tree, not 50.

Three separate claims in one clause, all measurable, all currently wrong. Remedy: name the file
without line numbers and derive the count at read time rather than freezing it — the same argument
this module's own `__doc__` makes at `src/silence.py:24-28` about not freezing the handler count
into prose.

### S-06 (MINOR) — `swallow` cuts the detail it exists to preserve

`src/silence.py:98`: `self.detail = str(detail)[:60]`, passed straight to
`health.record(f"{self.kind}:{exc_type.__name__}", self.detail)` at `src/silence.py:113`. The
detail is the per-failure discriminator (`swallow("fetch", host)` — the host), so on a long value
(a URL, a path, a source name) it is cut mid-value with no marker and two different failures can
land under the identical record. That is the pattern-visibility this class's docstring at
`src/silence.py:88-90` says is the whole point. Remedy: raise the bound well past a URL, or keep a
short display form and a full value in the record, but do not cut without a marker.

### S-07 (MINOR) — `_ensure_import` can insert a duplicate `import silence`

`src/silence.py:607-615`. The already-imported check
(`if any(getattr(a, "name", "") == "silence" ...): return src`) sits INSIDE the same loop as the
detached-block `break` (`if last and node.lineno > last + 3: break`). An `import silence` that
lives in a later, detached import block is never reached, so the loop breaks first and
`src/silence.py:631` inserts a second one. Harmless at runtime (a duplicate import is a no-op) but
it makes `--instrument` non-idempotent on such a file, and `instrument()` writes.
Remedy: scan the whole module body for an existing `import silence` before choosing the anchor.

---

## manifest_builder.py

### MB-01 (MINOR) — owner exclusions are cut mid-name and mid-reason

`src/manifest_builder.py:424`: `print("   %-44s %s" % ((_n or "?")[:43], _why[:90]))`. This is the
only line that tells the operator which sources the owner ruled out of scope and why — the block's
own comment at `src/manifest_builder.py:416-418` says they are "Reported by name rather than
silently filtered". Both the name and the reason are cut with no marker, so a long source name
(the roll has several over 43 characters — the Roger Rabbit entry named at
`src/manifest_builder.py:73-75` is 65) prints as a prefix that may not even identify the source
uniquely. Remedy: wrap rather than cut, the way `src/silence.py:247-253` already does for the
identical problem.

### MB-02 (INFO) — `FEATS_BLOCK_CHARS` is a constant nothing reads

`src/manifest_builder.py:168`. A tree-wide grep finds exactly three occurrences: the definition,
and two COMMENTS (`src/context_budget.py:20`, `src/manifest_builder.py:360`). No code reads it.
The comment at `src/manifest_builder.py:160-167` is aware of this and explicitly defers the
decision ("whether the constant should now be deleted outright is a question for NEXT_STEPS, not
a silent removal here"), so this is recorded as an open item for the owner, not as an oversight.

### MB-03 (MINOR) — the unassigned-sources report is written non-atomically

`src/manifest_builder.py:570-577` writes `output/index/unassigned_sources.md` with a bare
truncating `open(report_path, "w")`, while the manifest four lines earlier goes through
`silence.write_json` and gates on its verdict (`src/manifest_builder.py:520`). This is the file
CLAUDE.md's Hard Rule 2 points the operator at, and the block's own comment at
`src/manifest_builder.py:536-541` argues that a wrong version of it "is worse than no report: it
is a confident answer to a question nobody re-asked". A crash or a concurrent reader in the
truncate-then-fill window leaves exactly that. Remedy: land it through the same
temp-plus-`silence.replace_retry` path, and report the verdict.

### MB-04 (MINOR) — the feats-failure warning truncates the exception message

`src/manifest_builder.py:357`: `str(e)[:110]`. This is the one line that distinguishes a BUG in
`feats_index` from a source with no attested feats — the distinction the comment at
`src/manifest_builder.py:342-350` calls "Hard Rule 0's central failure". A `KeyError` traceback
message or a path in the exception text is routinely longer than 110 characters, and the cut is
unmarked. Remedy: print the whole message, on its own line if width is the concern.

---

## autostart.py

### A-01 (MINOR) — `start_supervisor` does not create `state/`, and `--install` dies after reporting success

`src/autostart.py:238-239` opens `state/overnight_stdout.log` and `state/overnight_stderr.log` in
append mode with no `os.makedirs(LOGDIR, exist_ok=True)`. `_log` at `src/autostart.py:85` DOES make
the directory, and its comment (`src/autostart.py:80-84`) is written about precisely this
condition: "On a tree where state/ does not exist yet -- a fresh checkout, or a clean that took it".

Two consequences, both verified by reading the call paths:

* `main()`'s `--install` path calls `start_supervisor(a.read_hours)` at `src/autostart.py:446`
  with no handler. On a tree with no `state/`, the run prints `installed: <path>` and then dies
  with an uncaught `FileNotFoundError` traceback — a success message followed by a crash, on the
  one command whose whole job is to be trusted unattended.
* `watch()`'s loop catches it at `src/autostart.py:414-416` and logs only
  `"watchdog error: FileNotFoundError"`, which names neither the directory nor the fact that no
  supervisor was started. It self-heals on the next 180-second cycle because `_log` creates the
  directory on the way out, and `starts` is not appended so no budget is consumed — so the cost is
  one lost cycle and one uninformative log line, not an outage.

Remedy: `os.makedirs(LOGDIR, exist_ok=True)` at the top of `start_supervisor`, matching `_log`.

### A-02 (INFO) — the twin probe sleeps after its last attempt

`src/autostart.py:295-302`. `time.sleep(TWIN_RETRY_SECONDS)` runs on every failing attempt
including `attempt == TWIN_TRIES - 1`, after which the loop exits anyway. A fully-failing probe
therefore costs 20 seconds of which the last 5 buy nothing, at logon, before the watchdog starts.
Remedy: `if attempt < TWIN_TRIES - 1: time.sleep(...)`.

### A-03 (MINOR) — `uninstall()` can raise out of a command that just reported the file present

`src/autostart.py:193-195`: `if os.path.exists(VBS): os.remove(VBS); return True`. A denied remove
— the same Windows condition every write path in this module routes through
`silence.replace_retry` to survive (`src/autostart.py:182`) — raises out of `main()` at
`src/autostart.py:430` instead of reporting "could not remove". Remedy: catch `OSError`,
`silence.note` it, and return a third state so the printed line and the exit code match what
happened, the way `install()` already does with its four verdicts.

---

## pick_model.py

### P-01 (MINOR) — the residency gate runs on a fabricated VRAM figure when `nvidia-smi` is absent

`src/pick_model.py:298`: `budget = (total_vram_gb() or 10.0) - VRAM_RESERVE_GB`.
`total_vram_gb()` returns `None` on any failure (`src/pick_model.py:187-189` — no nvidia-smi, a
non-zero return, a timeout). The `or 10.0` silently substitutes a 10 GB card, and that invented
number then drives the hard refusal at `src/pick_model.py:311` and is printed as fact at
`src/pick_model.py:330` (`vs {budget:.1f}GB budget`) and `src/pick_model.py:348`
(`budget {budget:.1f}GB`). On a machine with a 24 GB card and no working nvidia-smi, every model
over ~7.8 GB is refused and the operator is told the budget is 9.0 GB as though it had been read
off the hardware.

Remedy: keep the fallback, but carry the provenance — say "assumed 10.0GB (nvidia-smi
unavailable)" everywhere the budget is printed, and consider declining to enforce `RESIDENT_ONLY`
at all when the card could not be measured, since a gate on an unmeasured number is a gate on a
guess.

### P-02 (MINOR) — "couldn't read free VRAM" is also printed for a genuine 0.0 GB free

`src/pick_model.py:321` (`if vram_gb:`) and `src/pick_model.py:335` (`if vram_gb else ""`) treat
`0.0` and `None` alike, and the message chosen for both is
`"(couldn't read free VRAM -- nvidia-smi not available)"` (`src/pick_model.py:325`). A card with
nothing free — the exact condition this report exists to surface, and the one the docstring at
`src/pick_model.py:200-203` describes — is reported as an instrument failure. Remedy:
`if vram_gb is not None:`.

### P-03 (INFO / QUESTION) — does `MOE_MARKERS` disqualify anything?

`src/pick_model.py:82-83` states MoE families are "STILL DISQUALIFYING under the residency mandate
below". Nothing in the code disqualifies on the marker: `resident()` (`src/pick_model.py:192-194`)
is purely `weight_gb + KV_GB <= budget_gb`, and `is_moe` survives only as a word chosen in
`fit_note`'s warning string (`src/pick_model.py:256`).

Two defensible readings, so this is a QUESTION: the sentence may mean "MoE no longer buys the
tolerance it used to, so an MoE model is disqualified by size like any other" — which is true and
is what the surrounding paragraph argues — rather than "MOE_MARKERS is consulted by the gate".
Worth one clarifying word either way, because as written it reads as a claim about the list.

### P-04 (INFO) — the report's fit note and the gate that admitted the model use different budgets

`src/pick_model.py:311` admits a model on `budget` = TOTAL minus `VRAM_RESERVE_GB`;
`src/pick_model.py:335` then annotates the same model with `fit_note(m, vram_gb)` where `vram_gb`
is FREE VRAM (`src/pick_model.py:318`). On a busy desktop a model that passed the residency gate is
printed with `WILL OFFLOAD: needs ~X vs Y free`. Both numbers are defended in their own docstrings
(`src/pick_model.py:176-178` argues for total; `src/pick_model.py:200-203` argues for free), so
this is not a defect so much as two answers in one table with nothing saying they are measuring
different things. Remedy: label the fit-note column as "right now" against the gate's "by class".

---

## retry_synthesis.py

### R-01 (MINOR) — `do_merge()` cannot report a side entry whose record it never met

`src/retry_synthesis.py:219-225`: the loop walks `PL.records()` and `continue`s on
`if src not in side`. A key that IS in `side` but whose record file is never yielded — renamed,
removed, or its `source` field changed since the rescue ran — is simply never visited, and the
tally at `src/retry_synthesis.py:244-245` prints `merged`, `skipped` and `denied` only. So
`merged + skipped + denied` can be strictly less than `len(side)` with nothing said, and
`src/retry_synthesis.py:250` returns 0 for that run. These are the synthesis blocks the module
docstring says nothing else will ever recompute; a silently unmerged one is a source that reaches
the write phase with no ceiling and no band, which is verbatim the outcome the module opens by
saying it exists to prevent.

Remedy: collect the visited keys and, after the loop, name every `side` key that was never seen —
uncapped — and fold that into the exit code alongside `denied`.

### R-02 (MINOR) — evidence and rationale are cut with no marker

`src/retry_synthesis.py:181` (`[:600]`) and `src/retry_synthesis.py:199` (`[:900]`). `evidence` is
the text `PL.valid_scale_note()` is run against at `src/retry_synthesis.py:184` and the string a
reader checks a band claim against; both are stored into `data/records/*.json` by `--merge`.

Noted as shape parity rather than as a divergence: `pipeline.py:1151-1152` applies the identical
`[:600]` / `[:900]`, and `src/retry_synthesis.py:203-207` is explicit that this block must match
`pipeline.py:1157`'s shape. The remedy therefore belongs to both writers together, not to this
one — either both keep the whole value, or both append an explicit truncation marker and the
original length.

---

## render.py

### RN-01 (MINOR) — "all 9 tiers viewable" is a success report for work that was not done

`src/render.py:263` prints `all {len(TIER_ORDER)} tiers viewable` unconditionally after the loop
at `src/render.py:253-259`. For the four FETCHED tiers that loop calls `view()`, which returns
`{"kind": "url", "url": ...}` built by `galaxy_view` / `system_view` / `planet_view` / `burg_view`
(`src/render.py:67-81`) — four pure f-strings. No request is made, so nothing establishes that
`GALAXY = "https://galaxy-generator.oogabooga.dev/api/galaxy"` or
`FMG = "https://azgaar.github.io/Fantasy-Map-Generator/"` answers at all. The five DRAWN tiers are
genuinely exercised (the SVG is generated and its byte count printed); the four fetched ones are
string formatting reported as viewability.

Remedy: either say what was actually established ("5 tiers drawn, 4 addressed — the external
generators were not contacted") or add an opt-in `--probe` that issues a HEAD to each host and
reports per-tier.

### RN-02 (MINOR) — `children_of`'s coordinate filter admits everything when the coordinate is empty

`src/render.py:198`: `if any(c.get(t) != coord.get(t) for t in prefix if t in coord): continue`.
When `coord` shares no key with `prefix`, the generator is empty, `any([])` is False, and no pool
entry is ever skipped — a filter that cannot reject. `view()` reaches it with exactly that value:
`kids = children_of(tier, coord or {}, tree)` at `src/render.py:227`, so `view("hyperverse")` with
no `coord` returns the WHOLE pool bucketed by child tier and `containment_svg` draws it, captioned
with label `"?"` (`src/render.py:228`) and an honest-looking child count.

Not currently reachable from anywhere but the module's own `main()`, which always passes
`coord=sample` (`src/render.py:258`, `src/render.py:269`); a tree-wide grep finds no other caller
of `render.view` (`build_terminal.py:87` mentions `containment_svg` only in a comment). So this is
a latent hazard on a public entry point rather than a live wrong picture.

Remedy: require at least one prefix key to be present in `coord` and raise (or return `[]` with a
reason) otherwise, rather than degrading to "everything".

### RN-03 (INFO) — the URL column is cut at 64 characters

`src/render.py:256`: `rows.append((t, "url", v["url"][:64]))`. A display cut with no marker, in the
one place the operator can read the address that was built. Reversible in principle (the whole
value is still in `v`) but nothing else prints it. Remedy: wrap, or widen the column.

---

## propagation.py

### PR-01 (MINOR) — the docstring names the wrong iteration

`src/propagation.py:168-171` says: "once lag is non-negative, `ascension_years(1) == 0.0` (order
ad730acf0b18), so **the loop's first iteration** always matches and always returns; the trailing
`return 0` after the loop is unreached".

Verified: `ascension_years(1)` is `1.0 ** 1.35 - 1.0 == 0.0`, and the loop at
`src/propagation.py:176` is `range(LADDER_HEIGHT, 0, -1)` — it counts DOWN from 17, so rung 1 is
the LAST iteration, not the first. The substantive conclusion is correct and is the important part:
once `lag >= 0` the loop is guaranteed to return, so `src/propagation.py:179` is unreachable and
`[^0]` comes solely from the `lag < 0` guard. Only the sentence describing the mechanism is wrong,
in a docstring written specifically to explain why the trailing `return 0` is not a second `[^0]`
path.

Remedy: "the loop's LAST iteration (rung 1) always matches".

### PR-02 (MINOR) — the survey cuts shelf names at 19 characters

`src/propagation.py:226`: `f"{a[:19]:21s} -> {b[:19]:21s}"`. Cut mid-word with no marker, on names
this module's own comment at `src/propagation.py:72-73` shows are routinely longer
("Xanathar's Guide to Everything", "DMs Guild: Heroes of Hell"). The row is the module's primary
output. Remedy: widen, or wrap, or print the pair on its own line above the numbers.

### PR-03 (INFO) — the CLI has no exit code

`src/propagation.py:234-235`: `if __name__ == "__main__": main()`, and `main()` returns `None` on
every path — including the `DISCONNECTED` branch (`src/propagation.py:198`) and the
`?? not in graph` branch (`src/propagation.py:231`). The process therefore exits 0 whatever it
found. Every other CLI in this batch (`mutate`, `silence`, `manifest_builder`, `autostart`,
`retry_synthesis`, `render`) routes through `sys.exit(main())` and returns a verdict.
Remedy: return 1 when a requested pair is disconnected or absent from the graph, and call it
through `sys.exit`.

---

## Cross-reference verification summary

Every `file.py:NNN` citation appearing in this batch's own comments was checked against the current
file. Result:

| citation | in | verdict |
|---|---|---|
| `prose_gate.py:201` | mutate.py:442 | **correct** — `re.split(r"(?m)^◈\s", text or "")` is on that line |
| `pipeline.py:1157` | retry_synthesis.py:203 | **correct** — `"assessed_at": ...isoformat(...)` is on that line |
| `:222` (own file) | mutate.py:260 | **stale** — token is stamped at :243; :222 is a comment |
| `generate.py:555-558` | mutate.py:946 | **stale** — the symbolic-tag argument is at generate.py:598 |
| `drill.py:4256` | mutate.py:906 | **questionable** — call sites are 6553/6614; may be quoting a historical ledger row |
| `navtree.py:297` | silence.py:493 | **stale** — the call is at navtree.py:304 |
| `hostcheck.py:170` | silence.py:527 | **misdirected** — describes the litter cleaned at hostcheck.py:179 |
| `chain.py:141/159` + "48 others" / "fifty" | silence.py:713-715 | **stale** — markers at 213/242; 35 in the tree, not 50 |
| `read.py:80` | manifest_builder.py:139 | **near-stale** — the 10,000/5/41 vs 36,000/2/19 measurement is at read.py:84-85 |

---

## Checks verified as SOUND (recorded so the next sweep does not re-open them)

* `mutate._run_mutation`'s `base is None` refusal (`src/mutate.py:1398-1403`) and the `ungauged`
  refusal (`src/mutate.py:1405-1410`) both fire on the public entry point, not only on the CLI —
  the defect their comments describe is genuinely closed.
* `mutate.could_not_judge` prefix-matches (`src/mutate.py:1340`), so `"TIMEOUT|drill"` and a bare
  legacy `"TIMEOUT"` both register; the indeterminate bucket is genuinely separate from `killed`.
* `mutate._session`'s `stopped_at` break (`src/mutate.py:1754-1755`) does stop the loop and does
  carry `rc` out (`src/mutate.py:1765`) — the print-and-continue defect its comment describes is
  closed.
* `silence._handler_is_observed`'s bound-name test (`src/silence.py:162-164`) asks the body, not
  the dump, so the `'e' in body` tautology is genuinely gone; and the `Raise` test
  (`src/silence.py:152`) is asked of the tree, so the dead `"raise"` token is gone.
* `manifest_builder.load_record`'s `MIN_INEXACT_LETTERS` floor (`src/manifest_builder.py:116`) is
  applied only to the two inexact arms — equality returns at `src/manifest_builder.py:114-115`
  before the floor is reached, so `dc.json` is not stranded.
* `autostart.main`'s tri-state print (`src/autostart.py:465-467`) parses correctly: True →
  "running", None → "UNKNOWN", False → "NOT running".
* `propagation.observed_mark`'s claim that `src/propagation.py:179` is unreachable once `lag >= 0`
  is correct (`ascension_years(1) == 0.0`); only the sentence naming which iteration is wrong.
