# AUDIT — run32, batch 04

Modules read in full, every line, in `src/`:

| module | lines (wc -l) |
|---|---|
| foreman.py | 1367 (1368 incl. final unterminated line) |
| health.py | 428 |
| sweep_plan.py | 325 |
| sweep.py | 258 |
| cleanup.py | 215 |
| physics.py | 149 |

Method: full read of each file (Read tool, no offset skipped), cross-checked against live
source with `grep`/small AST probes run through miniconda python where a claim needed
confirming against the actual codebase rather than the docstring's account of it. Everything
below is VERIFIED against the code unless marked SUSPECTED.

---

## BLOCKING

### 1. `foreman.py:858-871` — `_function_source` can silently patch the wrong function
**VERIFIED, and confirmed live in this codebase, not just theoretical.**

```python
def _function_source(path, symbol):
    ...
    want = symbol.split("(")[0].split(".")[-1].strip()   # line 864: strips class qualifier
    for node in _ast.walk(tree):                          # line 865
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)) and node.name == want:
            ...
            return "".join(lines[start:end]), start, end   # first match wins
```

`symbol` (e.g. `"ClassB.method"`) is reduced to a bare name (`"method"`) and matched against
**every** `FunctionDef`/`AsyncFunctionDef` in the module via `ast.walk`, which visits nodes in
source order — the walk returns whichever function with that name comes FIRST in the file,
regardless of which class the finding actually names. Confirmed the walk order behaves exactly
this way with a two-class repro (`class A: def to_dict` before `class B: def to_dict` — walk
returns A's, line 3, even when the caller wants B's).

This is not a hypothetical name collision. Scanning every module in `src/` for duplicate
function/method names within one file (excluding `__init__`) turns up live collisions in
modules this lane is permitted to patch (i.e. not on `DENYLIST`):

- `src/endpoint.py` — function name `one` defined twice
- `src/hostcheck.py` — function name `one` defined twice

(`src/estate.py` also has `note` x4, but `estate` is on `DENYLIST` so protected — `endpoint`
and `hostcheck` are not.)

This function feeds `attempt_patch`, which is the **unsupervised model-authored patch lane**
described in the module docstring as fenced "this hard" specifically because a silent wrong
patch to live source is the exact defect class this project keeps losing to. If an
`OVERWATCH.json` finding ever names a method called `one` in `endpoint.py` or `hostcheck.py` (or
any future duplicate), `attempt_patch` will read, prompt on, and — if `dry=False` — overwrite the
WRONG function's body on disk, verified only by `_checks_pass` (import + verify_math +
allsweep), none of which can detect "patched the wrong function, the right one is untouched and
still broken, and an unrelated function now has the patched one's logic pasted over it." This is
a genuine silent-corruption path in the one lane most explicitly designed against silent
corruption.

**Failure scenario:** OVERWATCH files a finding against `hostcheck.SomeClass.one`. The model
proposes a correct fix for that method. `_function_source("hostcheck.py", "SomeClass.one")`
resolves `want = "one"`, walks the tree, and returns whichever `one` (in whatever class) appears
first lexically — which may be a different class's `one` entirely. The patch is applied to that
function instead, `_checks_pass` sees the module still imports and `verify_math`/`allsweep`
still pass (since the intended bug is untouched and the applied patch, being a plausible rewrite
of a same-named-but-different method, may well still parse and run), and the round reports
"patched and verified" for a change that fixed nothing and altered unrelated code.

---

## MAJOR

### 2. `foreman.py:192` — `SC.sweep(limit=4)` ranks then truncates hostless sources; ranks 5+ starve permanently
**VERIFIED — Hard Rule 0 violation, confirmed against `scout.py`.**

```python
res = SC.sweep(limit=4)
```

`scout.sweep()` (src/scout.py:237-241):
```python
def sweep(limit=None, register=True):
    todo = hostless()
    order = sorted(todo, key=lambda s: -len(todo[s]))   # rank
    if limit:
        order = order[:limit]                            # then truncate
```

`scout.py`'s own CLI default is `--limit None` (uncapped — correct). `foreman.py`'s
`scout_hostless` remedy hard-codes `limit=4` on every call. `order` is recomputed fresh from
`hostless()` (still-unadopted sources) on every invocation, ranked by entry count descending. A
source that repeatedly fails to gain a host (e.g. everything the scout can't verify, or that's
already logged in `SCOUT_BLOCKED.json`) stays in `hostless()` forever and therefore keeps
occupying a top-4 slot by entry count every single round — so any source ranked 5th or lower
never gets attempted, ever, for as long as the top 4 keep failing. This is exactly the "ranked
then truncated" shape Hard Rule 0 forbids, and it is not self-correcting: nothing rotates which
4 get tried.

### 3. `cleanup.py:73-80` — corruption guard for "three regexes" only actually checks two; the third is wired to `None` and silently no-ops
**VERIFIED — check that cannot fail, contradicts its own comment.**

```python
# GUARD. Three regexes in this project have been silently broken by an escape being eaten in
# transit -- a word boundary arriving as a literal backspace (0x08), which matches nothing and
# fails silently. ... This refuses to load rather than pass quietly.
for _n, _p in (("_NAV", _NAV), ("_EMPTY_MECHANIC", _EMPTY_MECHANIC),
               ("_SETTING_META", None)):
    if _p is not None and any(ord(c) < 32 for c in _p.pattern):
        raise SystemExit(f"{_n} contains a control character; the escape was mangled in transit")
```

The tuple names three regexes, but `_SETTING_META` is passed as literal `None`, not the real
object — `cleanup.py` never imports or references `pipeline._SETTING_META` anywhere else in the
file (confirmed by grep: `_SETTING_META` appears in `cleanup.py` only in this one dead tuple
entry; the real regex lives in `pipeline.py:1043`, used by `pipeline.py:1083`). Because the loop
guards with `if _p is not None`, this entry is a permanent no-op — it can never raise, no matter
what happens to `pipeline._SETTING_META`'s pattern. The comment's promise ("This refuses to load
rather than pass quietly") is false for the one of the three it explicitly names but never
actually inspects. This is a vacuous-green check of exactly the shape the LENS asks to hunt for:
a guard against a known recurring corruption class that is worded as covering three regexes and
mechanically covers two.

**Impact:** if `pipeline._SETTING_META`'s pattern is ever corrupted the same way the other five
regexes in this project's history were (escape eaten in transit -> literal control char ->
matches nothing -> silent false negatives), `cleanup.py` will not detect it, `pipeline.py` has no
equivalent guard of its own that this audit found reference to being invoked from here, and the
rules-construct filter that regex drives (`pipeline.py:1083`) will silently stop firing.

### 4. `sweep_plan.py:143-151` — the per-shard write (the one write this file's whole design depends on) bypasses the project's own atomic-write contract
**VERIFIED.**

```python
p = _shard_path(run, batch if batch is not None else "x")
tmp = "%s.tmp" % p
with open(tmp, "w", encoding="utf-8") as f:
    json.dump({"run": run, "batch": batch, "at": now, "modules": covered}, f, indent=1)
os.replace(tmp, p)
```

Every other shared-state write in this same function (`record()`, ~15 lines later) and across
`foreman.py`/`health.py` in this batch uses `silence.replace_retry(tmp, dst)`, specifically
because a bare `os.replace` can be transiently denied on Windows (antivirus/indexer holding a
handle) and `replace_retry` exists to survive that with multiple attempts. This one write — the
per-batch shard that is the ONLY record that a given batch's coverage happened, in a design whose
entire stated purpose is surviving sixteen batches recording "AT ONCE" — uses a raw single-shot
`os.replace` with no retry. It is inside the function's outer `try/except`, so a failure is
caught and `silence.note("sweep_plan.py:shard-write")` is called rather than crashing silently —
but the shard itself is simply never written, with only one attempt where the sanctioned
project-wide pattern spends five. Under real concurrent load (16 subagents recording near-
simultaneously, which is the exact scenario this file's docstring says the design must survive)
this is the one place most likely to hit exactly the transient-lock condition `replace_retry`
exists to absorb, and it's the one write in the file that doesn't use it.

---

## MINOR / NOTE (count: 3)

### 5. `foreman.py:413-523` `kill_stalled_job` / `STALLED_UNRESTARTABLE` — REFUTED as "silently dead", but genuinely un-remediated
Checked against the known lead. The escalation is NOT silent: `escalation.escalate(SUPERVISOR,
"STALLED_UNRESTARTABLE", ...)` writes to `state/escalation.log` and calls `health.record(...)`
(confirmed in `escalation.py:127-152`), both of which are visible to a person reading the
dashboard/logs. `escalate()` only raises/halts at `level >= OWNER` (escalation.py:150), so
SUPERVISOR-level correctly does not stop the library — matching the documented ladder. However:
grep across `src/` shows `STALLED_UNRESTARTABLE` is referenced nowhere except this one call site
— nothing counts repeat occurrences, nothing escalates the rung on repetition, and nothing else
in the reachable code kills or otherwise un-wedges an unrestartable job. So while it is not
silent, it is genuinely unremediated: a job in this state holds its single-instance lock
indefinitely and stays wedged until a human notices the (correctly non-silent) log entries and
intervenes by hand. Downgraded from the "silently dead" framing in the lead to a NOTE because
visibility is real, but flagging that there is no automatic path back to health for this class of
job.

### 6. `sweep_plan.py:158-176` — `SWEEP_COVERAGE.json` aggregate fold can lose a concurrent update across processes
Already self-documented as intentional/accepted in the file's own docstring (`_RECORD_LOCK` is a
`threading.Lock`, explicitly acknowledged as not holding across the 16 separate processes that
actually write this file). Confirmed the mechanism: `data = _read_shards()` is a snapshot taken
before the write, so two processes racing here can each overwrite the other's fold with a
slightly-stale merge. Not flagging as a bug because `missing()`/`covered_by()` read shards
directly and never consult this aggregate for correctness — it's documented as a "convenience
view" only, and that claim checks out against the code that actually answers completeness
questions.

### 7. Display-only truncations reviewed and cleared (not Hard Rule 0 violations)
Checked every `[:N]` / `.most_common(N)` / `top=` occurrence in all six files.
`foreman.py:230` (`top 3` failure classes in `triage_swallowed`'s summary line — full ledger
still archived unfiltered), `health.py:241` (`files[:200]` cache-emptiness sampling — documented
performance tradeoff, diagnostic only), `health.py:352` (`reopen[:20]` print — full `reopen` list
still used for the actual state mutation), `sweep.py`'s `report(rows, top=18)` (console table
only — `main()` writes the full, untruncated `rows` to `CHARACTER_SWEEP.json`), and
`cleanup.py`'s `nav[:5]`/`ceil_fixed[:6]`/`ceil_unres[:4]`/`desc_fixed[:5]`/`thin[:5]` (all
console summary prints — the actual pipeline records are written via `PL.write_record` from the
full, unsliced lists). All confirmed pure display formatting per Hard Rule 0's explicit
exception; the persisted/downstream data in every case is the full set.

---

## Known leads — disposition

- **`foreman.py:192` `SC.sweep(limit=4)`** — CONFIRMED as MAJOR finding #2 above.
- **`foreman.py:864-871` `_function_source`** — CONFIRMED as BLOCKING finding #1 above, with two
  live duplicate-name collisions found in the current tree (`endpoint.py`, `hostcheck.py`) that
  make this exploitable today, not just in theory.
- **`sweep_plan.py` self-auditing findings** — re-examined `record()`, `missing()`, `covered_by()`,
  `latest_run()` against the specific historical defects named in the file's own docstrings (lost
  update in `record()`, `missing()` answering "was run N the last to read X" instead of "did run
  N read X", a hardcoded `"run29"` completeness check). All three of those specific historical
  defects are fixed in the code as it stands today — verified no hardcoded run id anywhere in
  this file (`run29`/`run28`/etc. appear only inside docstring prose, never in an executable
  literal), `missing()` compares against live `modules()` each call, and `covered_by()` is a
  true membership query over shards rather than a newest-wins lookup. Found instead: the new
  MAJOR finding #4 above (unretried shard write) and MINOR finding #6 (documented, accepted
  aggregate race) in the same function.
- **`foreman.kill_stalled_job` / `STALLED_UNRESTARTABLE`** — REFUTED as "silently dead" (it is
  logged and health-recorded); downgraded to MINOR finding #5 (visible but genuinely
  unremediated — no escalation-level growth, no other code path revives the job).

---

## Not flagged, but noted for context

- `sweep.py`'s `cache_path()` is genuinely dead code (only caller was itself; only reference in
  the whole tree is `verify_math.py` testing `sweep.load`, not `cache_path`) but this is
  deliberate per its own docstring ("Callerless... kept and delegating rather than deleted, so it
  cannot drift back out of step with the real formula") — not treated as a defect.
- `physics.py` — clean. No caps, no swallowed exceptions, no silent defaults (`joules_for` and
  `kinetic` both raise rather than approximate on out-of-range/unknown input). No findings.
