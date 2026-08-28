# AUDIT — run36 batch 06

Modules: `feats.py`, `generate.py`, `codewatch.py`, `autostart.py`, `liveness.py`, `sweep.py`,
`style_audit.py`, `resync_roll.py`

All eight read in full (3,719 lines the batch prompt named; `feats.py` is actually 1,435 lines
on disk, read start to finish in two passes). Several findings below were checked against the
live data files on disk (`data/CHARACTER_SWEEP.json`, `data/SWEEP_ROLL.json`, `data/records/`)
rather than asserted from reading the code alone, per the discipline that audits are wrong in
both directions.

---

## feats.py

Read in full (1,435 lines). Focus per batch guidance: `_api_list_all`, the new continuation-token
walker.

**The stop conditions are sound.** Traced all three exits: `api()` returning falsy, an absent
`continue` key, and a repeated continuation token (checked against a cumulative `seen_tokens`
set, not just the previous token, so even a non-consecutive repeat is caught). A wiki that
oscillates between two tokens (A, B, A, ...) is caught on the second recurrence of A. No infinite
loop is reachable.

**MAJOR — a first-page failure is invisible, not counted, and reads as a legitimate empty list.**
`_api_list_all` (line ~579):

```python
while True:
    d = api(host, q)
    if not d:
        # Ran out of answer with more to come: partial, and it must not read as complete.
        if rows:
            with _COUNTS_LOCK:
                _CAP_BOUND[cap_key] = _CAP_BOUND.get(cap_key, 0) + 1
        return rows
```

The `_CAP_BOUND` increment — the signal `roll()` prints as "discovery lists: INCOMPLETE" — only
fires `if rows`, i.e. only when at least one page of results had already been collected before
the failure. If `api()` fails on the *very first* call (host down, transient network error, a
404 on the query endpoint itself), `rows` is still `[]`, nothing is counted, and the function
returns `[]` — structurally identical to a wiki that genuinely has zero matching subpages for
this entity. `discover()` calls this twice per entity (`aplimit` and `srlimit`); if both fail this
way, the entity falls through to just its own name, `evidence_for()` records `pages_read: []`,
and `roll()` files it under `empty` ("entities with no page") — a bucket that already conflates
"genuinely nothing to find" with several other causes elsewhere in this same file, which is
exactly the failure shape the module's own docstring calls "this project's signature failure
arriving over the network." The printed "discovery lists: complete" banner (line ~1329) can be
wrong with no signal, because the case it should flag as incomplete never touches `_CAP_BOUND`.

This is the single most likely failure to actually happen — a request failing on its first
attempt is the most common outage shape (host down at the *start*, not partway through a long
walk) — so this isn't a rare corner.

Everything else in `_api_list_all`, `discover()`, and the surrounding host-resolution and
throttling code was read and is sound: the `continue` merge rebuilds off the original `params`
each round (correct per MediaWiki's own continuation contract), and `_CAP_BOUND` being keyed only
by `"aplimit"`/`"srlimit"` (not per-host) is explicitly documented as an aggregate measurement,
not a bug.

No other findings in this module.

---

## codewatch.py

Read in full. Per guidance, NOT re-filing the known 180-second settle-window question (order
ff3c67a67b92).

**MAJOR — a denied ledger write is reported as a granted restart.** `_take_locked` (line 302):

```python
try:
    silence.write_json(LEDGER, doc, indent=2)
except Exception:
    silence.note("codewatch.py:record")
return True, used_before
```

`silence.write_json` returns `True`/`False` — `False` on a denied `os.replace` (the exact
Windows "another process still has the target open" case the module's own comments elsewhere
describe as a real, recurring event). That return value is never inspected. Whether the write
actually landed or not, `_take_locked` returns `True` (grant) — or, in enforce mode, whatever
the pre-write budget check decided — completely independent of whether the ledger update
persisted. The `except Exception` clause is close to unreachable for this purpose too:
`write_json`'s own docstring states it "Never raises on a denied replace," so the one failure
mode this call site is actually exposed to (a stuck `os.replace`) doesn't raise at all — it just
returns `False`, silently discarded here.

Consequence: `exit_if_stale()` calls `_claim_restart_slot` → `_take_locked(who, enforce=True)`.
If the ledger write is persistently denied while the budget check still says "under budget,"
the caller is told `granted=True`, actually exits with rc=17 (a real restart happens), but the
ledger never gains the new timestamp. On the *next* stale-detection within the same hour, the
budget check reads an unchanged (or still-short) history and grants again — the exact
restart-storm `BUDGET_PER_HOUR` exists to cap can be silently defeated by the same Windows
file-lock condition this project has already hit and written up (`replace_retry`'s own
docstring, `silence.py:332-337`, cites a 2026-08-23 incident of precisely this shape). This is
category 5 from the sweep's own catalogue (a discarded verdict) landing on the one safety in
this file that is supposed to prevent a bounce loop.

**Question, not a defect — `_record_restart` has no production caller.** `exit_if_stale` uses
`_claim_restart_slot` (check-and-take under one lock), not `_record_restart` (its
docstring's own account of the fix explains why: the two-step check-then-take race
`_claim_restart_slot` replaced). `_record_restart` is now exercised only by
`verify_math.py`'s `d99b11ec050e` concurrency regression test. Checked: it shares the same
`_ledger_lock`/`_take_locked` primitives the real path uses, so the test still exercises the
production locking mechanism — this isn't a guard silently not in effect, just a helper kept
for test access.

---

## generate.py

Read in full. Per guidance, checked the new try/except around `compress_store.store()`.

**Read, correctly implemented — nothing found on the specific ask.** Verified `compress_store
.store()` (`src/compress_store.py:56-64`) does raise when `silence.replace_retry` fails to land
the blob, rather than returning a "success" dict pointing at a file that was never written (the
old behaviour its own comment describes). `generate.py`'s try/except (line 526) catches exactly
that, files it under `failures` with a clear `refused` reason, calls `continue` rather than
letting one bad blob take a multi-hour run down, and does not swallow anything broader — no
bare `except: pass`, no over-wide catch hiding a different fault.

**Minor / lower-confidence — the same discarded-verdict shape as codewatch.py, but self-healing
here.** `save_json()` (line 53):

```python
def save_json(path, obj):
    full = os.path.join(HERE, path)
    silence.write_json(full, obj, indent=2)
```

Every call site (`catalog.json`, `failures.json`, both saved repeatedly through the run) discards
`write_json`'s True/False. Unlike the codewatch.py finding above, this doesn't undermine a
specific safety invariant: `catalog.json` is re-saved every 5 completions and again at the end,
so a single denied write is very likely overwritten by the next save in the same run (matching
`write_json`'s own documented "the caller's write lands next round" idiom), and even a fully
lost final save just means the affected addresses look un-cached and get regenerated on the next
invocation — redone work, not silent data corruption. Noting it because it's the identical
pattern, not because it currently causes a wrong result.

---

## autostart.py

Not edited today; read in full per guidance.

No defects found. Specifically checked and traced:
- **VBScript quoting** in `_vbs_body()` — manually expanded the string-concatenation build of
  `cmd` and confirmed it produces a syntactically valid, correctly double-quoted VBScript
  expression (`"<python>" -u "<script>" --watch`) rather than the historical
  empty-string-then-syntax-error shape the comment describes fixing.
- **`_twin_watchdog`** — correctly delegates matching to `codewatch.twins()`/`runs_script()`,
  filters survivors to `--watch` invocations only, retries `TWIN_TRIES` times on exceptions
  before failing open (logged, not silent), and the self-exclusion issue already fixed in
  `codewatch.twins()` (the `exclude_pid` bug) is inherited correctly since `codewatch.twins()`
  always excludes `os.getpid()` unconditionally now.
- **`watch()`** — the tri-state `supervisor_alive()` (`True`/`False`/`None`) is respected
  throughout: `None` never triggers a start, `False` is budgeted (`MAX_STARTS_PER_HOUR` /
  `START_WINDOW_SECONDS`), and the whole loop body is wrapped so a watchdog exception cannot kill
  the watchdog itself.
- **`main() --install`** — uses `is False` rather than a bare truth test before starting a
  supervisor, correctly declining to act on an "unknown" reading.

No caps, no discarded verdicts, no unreachable guards found in this module.

---

## liveness.py

Read in full. Per guidance, evaluated both widenings (DEAD into methods, PHANTOM past `ast.If`)
specifically for false negatives — checked each claim against the actual tree rather than
against the module's own docstring.

**Question / structural gap — DEAD-for-methods is scoped globally by bare name, not per class,
unlike module-level functions.** `_defs()` correctly walks into `ClassDef` bodies now (the
run #36 widening). But the liveness check itself (line 201, `if fn not in used and fn not in
used_local.get(name, ())`) tests the method's *bare name* (`fn = node.name`, e.g. `"rebuild"`)
against `used` — a single flat, module-blind, class-blind set built from every `ast.Attribute
.attr` in the whole 114-module tree. For module-level functions this is offset somewhat by the
per-module `used_local` scoping the docstring describes at length; no equivalent scoping exists
for methods, because Python attribute access (`obj.rebuild()`) can't statically distinguish
"the `Resolver.rebuild` method" from "any other object's `.rebuild` attribute," and the code
correctly says so in its own docstring ("collected globally"). The practical consequence: a
method sharing its bare name with *any* attribute access anywhere — another unrelated class's
live method of the same name, or an ordinary stdlib call (`.close()`, `.read()`, `.load()`,
`.run()`) — can never be flagged DEAD regardless of whether it is truly reachable.

Checked whether this currently causes a missed finding: it does not. The whole `src/` tree
defines only 9 non-dunder methods total (`dashboard.Handler._send`/`do_GET`/`log_message`,
`verify_math._StubSock.settimeout`/`connect`/`close`, `verify_math._StubNet.getaddrinfo`/
`socket`, `verify_math._FlowResp19ab.read`), and there are zero name collisions between distinct
classes among them (`__init__`/`__enter__`/`__exit__` collide across `silence.swallow` and two
`verify_math` stub classes, but those are dunders, already exempt via
`fn.startswith("__")`). So today this is a real structural blind spot with zero live impact —
flagged because it will silently swallow the first genuinely dead method with a common name
(`close`, `read`, `run`, `load`, `save`, `get`) the codebase grows into, and a detector whose
gap is invisible until it's too late is exactly what this module exists to prevent elsewhere.

**Question / structural gap — the PHANTOM widening still doesn't cover every conditional
shape.** The run #36 widening correctly extended the "name used in a guard" walk from bare
`ast.If` to `ast.While`, `ast.IfExp`, `ast.Assert`, and comprehension `.ifs` filters (line
256-265) — verified this covers `elif` chains too, since `ast.walk` recurses into an `If`
node's `orelse`, where an `elif` is represented as a nested `If`. Two conditional-execution
shapes remain outside all five checked node types: a `match`/`case` statement's `guard`
clause (`case X if cond:`), and a bare short-circuit expression statement used for control flow
(`cond and do_something()`, `cond or fallback()` as a standalone statement rather than inside an
`If`/`While`/`Assert`/comprehension). Checked the actual tree: `src/` contains zero `match`
statements and zero bare-BoolOp expression statements, so — like the DEAD finding above — this
has caused no missed finding today, but it's a residual gap in the same spirit as the widening
itself, worth a line so a future PHANTOM audit doesn't assume `ast.If`-plus-four is exhaustive.

No tautology-pass or unparsed-module issues found; the `_BAD_CHARS` self-check for this file
was not itself examined for defects (out of scope — it's identical boilerplate to the same
guard in `feats.py`/`sweep.py`/`autostart.py`, already checked there).

---

## sweep.py

Not edited today; read in full per guidance, and cross-checked against the live
`data/CHARACTER_SWEEP.json` already on disk rather than re-running the sweep.

**MAJOR — the funnel's core claim ("each stage is a strictly smaller set than the one above")
is false against the live data, and the display code mishandles the violation.** The module
docstring states: "Each stage is a strictly smaller set than the one above, and the size of each
drop is the real statement of where the project stands." Checked directly against
`data/CHARACTER_SWEEP.json` (144,528 rows):

```
n = 144,528
catalogued = 44,185
addressed  = 144,452   (i.e. bigger than catalogued, not smaller)
reachable  = 144,487   (bigger than addressed too)
read       = 121,151
```

`catalogued`, `shelfmark` (addressed), and `host` (reachable) are computed independently in
`sweep()` (lines 149-155) — nothing in the code makes `addressed` a subset of `catalogued`, or
`reachable` a subset of `addressed`. In the real data they aren't: the overwhelming majority of
entries have a shelfmark and a resolvable host *without* having been individually judged
"catalogued" by phase 2, so the funnel actually widens, not narrows, at those two steps.

Two concrete consequences in `report()` (lines 195-201):

```python
prev = n
for k in ("catalogued", "addressed", "reachable", "read", "evidenced", "assayable"):
    drop = prev - f[k]
    ...
    print(... + (f"   -{drop:,}" if drop else ""))
    prev = f[k]
```

1. Going from `catalogued` (44,185) to `addressed` (144,452), `drop = 44,185 - 144,452 =
   -100,267` — negative, but still non-zero so the `if drop:` guard fires, and the format string
   prepends its own literal `-`, printing `-{-100267:,}` as a double-negative `--100,267` rather
   than anything readable (an increase, correctly signed or explained).
2. More importantly than the cosmetic glitch: the bar chart (`"#" * int(38 * f[k] / max(n, 1))`)
   draws `addressed` and `reachable` as essentially full-width bars sitting immediately after a
   ~30%-width `catalogued` bar. Read as a funnel — which is exactly how the module frames itself
   and how a reader would interpret consecutive bars — this looks like the pipeline is almost
   entirely addressed and reachable, when the substantive judgment gate (`catalogued`) that
   those two nominally sit downstream of is only 30% done. This is the precise failure this
   module's own docstring warns against one paragraph earlier ("A number that only ever gets
   reported at the top of the funnel is a number that hides the four stages below it") — except
   here it's the *shape* of the funnel display itself doing the hiding, on data already on disk,
   not a hypothetical.

Recommend either fixing the display (report `+N` or "not a subset" explicitly when a stage
grows) or fixing the underlying assumption (only count `addressed`/`reachable` among entries
that are also `catalogued`, if that's the intended semantics) — this audit doesn't judge which,
since it isn't clear from the code which was intended, but the current print output is
misleading either way and the printed claim of monotonic narrowing is currently untrue.

**Not flagged as Hard Rule 0 violations (checked, declined):** `best = sorted(rows, ...)[:top]`
(line 218), `gap.most_common(10)` (line 227), `bysrc.most_common(8)` (line 234). All three are
console-only "top N" display summaries; the full `rows` list is written to disk in full via
`silence.write_json(OUT, rows, ...)` regardless of what the printed summary shows, matching the
same truncated-display convention `feats.py`'s own `_show()` uses. Not the same shape as a
roster silently capped and mistaken for complete.

`silence.write_json`'s return value IS checked here (line 252) — a positive contrast to the
codewatch.py/generate.py findings above; `sweep.py` gets this right.

---

## style_audit.py

Read in full.

**MAJOR — `TURN_ENDING`'s `re.M` flag makes `$` match at every line break, not the end of the
entry, so the "ending on a turn" metric can fire on a mid-entry paragraph.** Line 37:

```python
TURN_ENDING = re.compile(
    r"(?:\.|\?)\s+(?:And|But|Yet|Still|Which|That)\b[^.]{0,80}\.\s*$", re.M)
```

`audit()` uses this to decide, per entry, whether it "ends on a turn" (`if TURN_ENDING.search(r):
turns += 1`), and `report()` prints that rate against an explicit threshold ("entries ending on a
turn ... OVER (target <= 25%)"). With `re.M`, `$` matches immediately before *any* newline in the
text, not only the true end of the string. Confirmed directly:

```python
sample = """Alpha is a fortress. But it holds.

This second paragraph has nothing to do with turns and just ends normally without one"""
TURN_ENDING.search(sample)   # -> a match, even though the entry's actual last sentence
                              #    does not end on a turn construction at all
```

So an entry whose *first* paragraph happens to end on a turn-construction, followed by a blank
line and unrelated prose, is counted identically to an entry that genuinely ends the way the
metric claims to measure. This inflates `turn_rate` in the false-positive direction and can push
a corpus over the reported 25% threshold (or keep it looking clean) for a reason unrelated to
what the report claims to be checking. The fix is `\Z` in place of the trailing `$` (or dropping
`re.M` for this particular pattern), since the intent — per the docstring, the report label, and
the threshold framing — is plainly "does the entry's own final sentence do this," not "does any
line in the entry do this."

**Minor / cosmetic, no measured effect.** `entries()` (line 43):

```python
parts = re.split(r"^[◈◈]\s*", text, flags=re.M)
```

Both characters inside the bracket class are the identical Unicode codepoint U+25C8 (◈),
confirmed by inspecting the raw bytes — the class is functionally a no-op duplicate of `[◈]`.
Checked `prompts/system_style.txt` and `prompts/chapter_prompt.txt`: both consistently specify
only "◈" as the entry marker, so there's no evidence this was meant to also catch a second,
lookalike glyph and quietly failed to. Flagging only because a duplicated character inside a
class is exactly the kind of thing that looks like it was meant to do more than it does, and is
worth a second look if entry counts are ever found to undercount against a raw file's `◈` count.

---

## resync_roll.py

Read in full.

**MAJOR — a record file whose source has no matching roll row at all is completely invisible to
this script, and this has already happened in the live data.** `resync_roll.py`'s whole premise
(per its own docstring) is reconciling drift between `data/records/*.json` (authority) and
`data/SWEEP_ROLL.json` (index). The reconciliation loop (line 72) is:

```python
for r in roll:
    hit = by_source.get(norm(r["name"]))
    if not hit:
        continue
    ...
```

This only ever walks *existing roll rows* looking for their matching record file — it never
walks record files looking for a roll row that doesn't exist. Checked against the live data
(`data/records/` vs `data/SWEEP_ROLL.json`, 215 rows): one record file,
`data/records/bone-jeff-smith.json` (`source: "Bone (Jeff Smith)"`, 86 catalogued entries), has
no corresponding row anywhere in the roll — confirmed by normalized-name lookup against all 215
roll entries, not merely a near-miss spelling difference. `resync_roll.py`'s own comment (lines
100-101) states the roll's `entry_count`/`status` fields are "what every real consumer
(`manifest_builder`, `catalog.py`, `pipeline.py`) actually gates work-selection on" — so these
86 already-catalogued entries are very likely invisible to the entire downstream generation
pipeline, with nothing in this script (or, as far as this audit can tell from reading it alone,
anywhere else) flagging the gap. This is squarely the class of drift the module's docstring
describes wanting to fix ("The record files are the authority; the roll is an index over them.
They can drift apart") — it just doesn't cover the case where the drift is "the roll never had
a row for this source in the first place," only "the roll's row disagrees with the file."

Everything else in this module was checked and is sound: the duplicate-source winner is
deterministic (last filename alphabetically, matching its own printed claim, verified by
tracing the `by_source[key] = (rec, fn)` unconditional-overwrite-in-sorted-order logic), the
`OUT_OF_SCOPE` exclusion is correctly preserved rather than reverted, the zero-vs-stale-status
distinction is correctly handled, and the write's landed/not-landed verdict is checked and
acted on (line 115/128) rather than discarded. `norm()`'s aggressive stripping (alnum-only,
lowercased) was checked against the real corpus for false merges between distinct sources —
zero collisions found.

---

## Modules not read

None — all eight assigned modules were read in full.
