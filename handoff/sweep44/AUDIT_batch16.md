# AUDIT — sweep44, batch 16

Modules: `src/binding_health.py`, `src/local_agent.py`, `src/wiki_source.py`, `src/liveness.py`,
`src/worldseed.py`, `src/retry_synthesis.py`, `src/physics.py`, `src/tuning.py` (5,160 lines).
Every file read in full, top to bottom. All line numbers below were re-verified against the
source at the time of writing.

Known-and-filed items I was told not to re-file, and did not: `local_agent`'s rc=0-for-a-failed-
answer question (order 171ade4c7d27), the "refuse on saturated queue" idea (measured and
rejected), and `worldseed.URL_SETTABLE` (order e68664e621bf, and independently re-confirmed
still open in `handoff/sweep39/AUDIT_batch05.md` F12 — nothing wider found on it: it is read by
nothing and has diverged from `to_fmg_query`'s actual emission, exactly as already filed).

---

## src/binding_health.py — the code edited today

This is the module the brief flagged as freshly edited (`run()`'s `filtered` refactor, the
`limit is not None` fix, and the new `BINDING_FILTER_MATCHED_NOTHING` refusal). I traced every
site that reads `filtered` and every path through `run()`'s tail.

### Confirmed correct: the four `filtered` decision sites

`filtered = bool(only) or limit is not None` is computed once at line 1028 and read at four
places: line 1101 (`if not out and not filtered:`), line 1140 (`prior_digest = ... if filtered
else None`), line 1141 (`if filtered:` — read the standing report to merge), and line 1178
(`if filtered:` — build `partial_pass` and take the CAS path). I hand-traced all four
combinations of `{filtered, out empty/non-empty}`:

* **not filtered, out non-empty** (ordinary whole-estate run) — falls through both guards,
  reaches the blind `_land(OUT, doc)` at line 1192. Correct.
* **filtered, out empty** (`--host name-with-no-binding`, or `--limit 0` after the fix below) —
  line 1101 does not fire (`not filtered` is False), falls to line 1113 (`if not out:`), which
  now unconditionally means "filtered and empty" given the invariant below, and correctly raises
  `BINDING_FILTER_MATCHED_NOTHING` without touching the file.
* **not filtered, out empty** (the hosts map itself yielded nothing to canary) — line 1101 fires
  and raises `BINDING_ESTATE_EMPTY`, also without writing.
* **filtered, out non-empty** (a real `--host`/`--limit` pass) — falls through to the merge
  branch (1141) and the CAS write (1178-1191).

The invariant that makes `if not out:` at line 1113 unambiguous is that the per-host loop
(1040-1088) appends **exactly one** record to `out` for every host in the filtered `hosts` list
— either the "no catalogued title" row (1059) or a `canary()`/exception row (1072) — with no
`continue` that skips the append. So `len(out) == len(hosts)` always holds, and `out` can only
be empty when the filtered `hosts` list itself is empty. I confirmed this by reading the loop
body line by line; there is no code path that consumes a host without producing a row.

### Confirmed fixed: the `--limit 0` falsy-zero bug

Line 1037: `if limit is not None: hosts = hosts[:limit]`. Traced `--limit 0` end to end:
`filtered` = True (line 1028), `hosts` becomes `hosts[:0]` = `[]`, the per-host loop never runs,
`out` stays `[]`, line 1101's `not filtered` is False so it does not fire, and line 1113's
`if not out:` fires and refuses to re-stamp the report via `BINDING_FILTER_MATCHED_NOTHING`.
This is the exact scenario the brief asked me to check, and it now behaves correctly. `bound_hosts`
(line 1029, `len(hosts)` taken **before** either filter is applied) is likewise correct — it is
the total estate size used only for the "selected 0 of N" message at line 1135.

No divide operation exists anywhere in this file (checked by pattern search), so there is no
divide-by-zero to find in the new refusal message.

### FINDING B16-1 — `run()`'s partial-pass CAS write is not exception-guarded, unlike its two siblings [MEDIUM confidence]

`src/binding_health.py:1186`:
```python
landed, why = _land_cas(OUT, doc, prior_digest)
if not landed:
    _report_not_written(...)
```
`_land_cas` can raise (its own `try/except Exception: _unlink(tmp); raise` at lines 192-197
re-raises whatever stopped the temp file being written — a permissions error, a full disk, or
any other write failure). Its two other call sites in this same file, `quarantine()` (line
377-384) and `release()` (line 449-456), both wrap the call in `try/except Exception` and
degrade to `landed, detail = False, "the temp copy could not be written"` rather than letting
the exception propagate. The call at line 1186, inside `run()`'s filtered-merge tail, has no
such guard, and neither does its caller in `main()` (`out, failed = run(...)` at line 1241, also
bare).

If `_land_cas` raises here, the exception propagates out of `run()` uncaught, past `main()`, and
crashes the whole `--run` invocation with a traceback — discarding the already-computed `out`/
`failed` results for every host this pass canaried, which would otherwise have been printed and
returned to the caller. This directly contradicts the design already established for the
identical failure at the identical function two call sites over, and is the kind of
inconsistency the module's own commentary elsewhere calls out by name ("the asymmetry ... is
real and it is deliberate, and it is written down here because an unexplained one is how the
next editor copies the wrong half"). Here the asymmetry is not commented on at all, which reads
as an oversight rather than a decision.

Confidence is medium rather than high because the trigger condition (a write failure specifically
inside `_land_cas`'s temp-file creation, as opposed to the rename it guards against) is narrow —
but it is real, it is inconsistent with the pattern established one screen up in the same file,
and it would turn what should be a JANITOR-level "did not land" report into an unhandled crash
that loses a whole sweep's probe results.

---

## src/local_agent.py

Extremely heavily self-documented; almost every design decision already carries a paragraph
citing a prior incident and its fix. I read the whole file and traced the gate order in
`t_propose_patch`, the `_safe()` junction/case-fold hardening, `_gates()`, `_tool_message`'s
shrink loop, `_achievement`, and the turn loop in `run()`. I did not find a fresh gate bypass in
the write path. Two things worth recording:

### FINDING B16-2 — `t_grep`'s per-line truncation to 200 chars has no marker, unlike everything else in this file [LOW-MEDIUM confidence]

`src/local_agent.py:586-587`:
```python
hits.append(os.path.relpath(fp, HERE) + ":" + str(i) + ": "
            + ln.strip()[:200])
```
Every other hard slice in this file that could lose information is either a legitimate content
bound (an error-message preview capped at 120/160 chars, clearly a diagnostic snippet, not a
roster) or is dynamically computed with an explicit label saying what was cut (`_tool_message`'s
`message_truncation`/`*_shown`/`*_omitted` keys, `t_run_check`'s `"truncated": len(out) >
len(tail)`). This is the one silent `[:N]` slice in the file: the number of grep **hits** is not
capped (good, matches Hard Rule 0), but the **text of a single matched line** is hard-cut at 200
characters with nothing in the returned dict saying so. A match inside a long single-line file
(minified JSON, a wiki dump, a very long generated string) would be silently truncated with no
signal to the model that more of that line exists — the "mid-value cut with no marker" shape the
brief asked me to look for.

This could plausibly be judged a deliberate, harmless display convenience (a grep preview line is
conventionally short, and the model can always `read_file` the exact location `file:line` names
to see the rest) rather than a defect — which is the reading I'd give it if this file did not
otherwise document every other truncation this carefully. Given how consistently every other cut
in this file is labelled, the absence of a comment or a marker here reads as the one spot that
was not reviewed to the same standard, not as a considered decision. Reporting as a finding
rather than a question because the fix (add a `line_truncated` flag or lengthen the bound) is
cheap and the inconsistency with the rest of the file is the actual defect, whichever way the
number itself should go.

### Everything else checked and found sound

`_blast_ok`'s charge point (after uniqueness/allowlist/denylist checks, before the actual write —
line 879) matches its own commentary. `_gates()`'s case-folded `.py`/`.json`/`.yaml` branches,
the by-path import gate for files outside `src/`, and the `re.search(r"RESULT:\s*\d+\s+passed,
\s*(\d+)\s+FAILED", ...)` regex (rather than a `"0 FAILED" not in stdout` substring test) are all
present and correct. `_safe()`'s junction-vs-allowlist double-check (bypass class seven) is
consistent with `_denied_target()`'s three-rule union. `_achievement()`'s empty-answer and
attempted-but-not-landed guards are wired into both exit paths of `run()` (the "no tool calls"
branch and the turn-budget-exhausted branch), and the turn-budget branch's `_achievement(patches,
apply)` call omitting `answer` is intentional per its own docstring (`answer=None` is "the caller
did not say," and `ok` is already `False` on that path for the turn-budget reason alone, so
nothing is lost). `_tool_message`'s shrink loop always makes progress (the `keep >= len(out[k])`
clamp forces the list to shrink by at least one element per iteration) and cannot spin forever
inside its `range(40)` cap.

---

## src/wiki_source.py

Read in full. Nearly every function here already carries a fixed-and-documented Hard-Rule-0
history (`category_members`, `find_categories`, `rank_by_size`, `clean_titles`, `extracts`, all
uncapped by default with the reasoning written beside them). One thing not previously called out:

### FINDING B16-3 — `all_categories()`'s memoisation cache is keyed without `hard_stop`, so a bounded call can silently receive a cached UNBOUNDED result [LOW confidence, not currently reachable]

`src/wiki_source.py:402-429`. The cache key is `(subdomain, min_pages)` (line 402) — it does not
include `hard_stop`. A result is written to the cache only when `complete and hard_stop is None`
(line 426), i.e. only full, uncapped walks are ever cached. But the cache **lookup** at lines
403-405 runs before the `hard_stop` value for *this* call is consulted at all:
```python
key = (subdomain, min_pages)
with _ALLCATS_LOCK:
    if key in _ALLCATS:
        return _ALLCATS[key]
```
So once any full (`hard_stop=None`) call for a given `(subdomain, min_pages)` has completed and
cached, a *later* call for the same key that explicitly passes a bound (e.g. the debugging use
the docstring names — "left available for a human debugging a pathological wiki") gets back the
full, unbounded list from cache, silently ignoring the `hard_stop` it asked for. The direction of
the failure is the harmless one for Hard Rule 0 (a caller gets *more* than it asked for, never a
truncated roster reported as complete), which is why I am reporting it as low-confidence rather
than a Hard Rule 0 violation — but it is a real gap: the one parameter that changes the shape of
the answer for a given key is not part of the key. Not currently reachable, because (per the
module's own comment, and confirmed by grepping every call site in the tree) nothing in `src/`
passes a non-`None` `hard_stop` today — the same "not reachable given today's callers" caveat
already used elsewhere in this codebase for gate holes of this shape.

### Already-known, re-confirmed present, not re-filed as new

* `find_categories(limit=0, ...)` treats `0` the same as `None` (`return found[:limit] if limit
  else found`, line 476) — already filed as MINOR in `handoff/sweep26/AUDIT_batch15.md`.
* `rank_by_size(..., top=0)` has the identical shape (`return ranked[:top] if top else ranked`,
  line 656) — already flagged as a live-but-unused capability in `handoff/sweep27/AUDIT_batch14.md`
  (W5) and again as Q1 in `handoff/sweep42/AUDIT_batch16.md`. No caller in the tree passes a
  non-`None` value for either today.

---

## src/liveness.py

Read in full — this is the meta-detector for "checks that cannot fail," so I read it adversarially
against its own standard. The TAUTOLOGY, DEAD, DEAD CLASS and DEAD MODULE passes are all
internally consistent with their docstrings, including the already-fixed `if seen else set()`
tautology the file documents fixing in itself (line 338-342 — confirmed the conditional is
actually gone from the code, not just from the comment).

### QUESTION L16-Q1 — the PHANTOM pass's `defined` set is scope-blind across functions within one module [may be deliberate; both readings given]

`src/liveness.py:449-477`, inside the `for name, t in trees.items():` loop. `defined` is built by
walking the **entire module's** AST once — every `ast.Store` name, every function/class def,
every argument, every `except ... as e`, every `match` capture — and is then used to test every
guard/assert/comprehension-filter/match-guard/short-circuit-statement in **every function in that
module** (lines 496-522). There is no per-function scoping: a name that is only ever a local
variable or parameter inside function A is added to the same flat `defined` set that guards in
function B are checked against.

This is exactly the same shape as the bug the DEAD pass documents fixing in itself one screen
up (the "flat, scope-blind bag" that hid `coverage._p()` because a `for _p in ...` loop variable
in one file made `_p()` look called everywhere) — except here it is applied to *undefined-name*
detection rather than *call* detection, and the module's docstring does not discuss scoping
`defined` by function anywhere, unlike every other design choice in this file, which is argued at
length.

**Reading A (real gap):** a phantom name defined only as a local in function A would be
incorrectly treated as "defined" if it happens to be read, undefined, in function B's guard —
suppressing a genuine PHANTOM finding. This is a false negative in the exact detector whose job
is finding checks that cannot fail, which is the load-bearing thing about this file.

**Reading B (deliberate, consistent with the file's own stated policy):** the DEAD pass's own
docstring says repeatedly "erring toward 'it is used' is still the rule ... a false DEAD is
expensive to chase." A flat, whole-module `defined` set for PHANTOM only ever produces false
negatives (never a false alarm on legitimate cross-scope patterns such as a comprehension
variable or a locally-bound name later closed over), which is consistent with that stated
philosophy even though it is not spelled out for `defined` specifically.

I could not determine from the source alone which reading the author intended, since (unlike
every other choice in this file) it is not written down. Flagging as a question rather than a
defect for that reason. Zero live instances found in the current tree either way — I did not
find a case where this scope-blindness is currently hiding a real phantom.

---

## src/worldseed.py

Read in full, including the already-resolved `URL_SETTABLE` history (see top of this report) and
the already-fixed 200-char-window / `most_common(6)` / uncapped-`WORLD`-regex fixes, all confirmed
present in the current source.

### FINDING B16-4 — `build_all(limit=0)` silently processes the WHOLE catalogue instead of stopping at zero [HIGH confidence — same falsy-zero shape the brief flagged as already fixed in this batch's other module]

`src/worldseed.py:374`:
```python
for e in rec["entries"]:
    ...
    out.append(to_options(desig, nm, d, e.get("magnitude") or "unassayed", reg, g))
    if limit and len(out) >= limit:
        return out
```
`main()`'s `--limit` argument (line 381: `type=int, default=None`) is handed straight to
`build_all(args.limit)`. `--limit 0` arrives as the integer `0`, and `if limit` is `False` for
`0` — so the early-return never fires, regardless of how large `out` grows, and the function
processes **every** catalogued Place in the corpus (roughly 12,435 today) instead of the zero the
caller asked for. This is the exact falsy-zero shape the batch was primed on from today's
`binding_health.py` fix one file over (`--limit` defaulting to `None` with `type=int`, so `0`
reads as "no limit"), and it is unfixed here.

A prior sweep (`handoff/sweep23/AUDIT_batch15.md`) reviewed this exact line and cleared it —
but only against the Hard-Rule-0 truncation question ("truncates only when the CLI's own
`--limit` flag is explicitly passed... reads as the same sanctioned pilot/sample pattern"), which
is a different question from whether `0` specifically behaves as advertised. I confirmed by
grep that no later sweep caught the falsy-zero angle for this line. The fix is the one-word
change already applied in `binding_health.py` today: `if limit is not None and len(out) >=
limit:`.

### FINDING B16-5 — `retry_synthesis.py --smallest 0` has the identical falsy-zero shape [HIGH confidence]

(Filed here rather than under its own module heading below to keep the two side by side, since
they are the same bug in two files — see `src/retry_synthesis.py:298`.)

---

## src/retry_synthesis.py

Read in full. `save_side`'s deliberately-not-locked merge-then-CAS race, `synthesise()`'s
now-shared-with-`pipeline` prompt/transport/acceptance-gate code, and `do_merge()`'s
denied-write/unmerged-source accounting are all consistent with their (extensive) docstrings.

### FINDING B16-5 — `--smallest 0` is read as "no pilot limit," not "do zero sources" [HIGH confidence]

`src/retry_synthesis.py:298-302`:
```python
if args.smallest:
    todo = sorted(todo, key=lambda pr: len(pr[1].get("entries") or []))[:args.smallest]
```
`ap.add_argument("--smallest", type=int, metavar="N", ...)` (line 279) defaults to `None`. Passed
`--smallest 0`, `args.smallest` is the integer `0`; `if args.smallest:` is `False`, so the
`todo` list is never sliced and the **full** set of failed-or-stranded sources is retried instead
of the zero the flag's own help text ("do the N smallest pending sources first") would imply for
`N=0`. Same shape as B16-4, in a different module, and not previously flagged (grepped the
handoff tree; no prior sweep names this line for this reason). The cost here is model calls
against every stranded/failed source rather than a `--smallest 0` dry check of the "N to do now"
line, which is a real but smaller blast radius than the worldseed case (dozens of sources, not
thousands of catalogue entries) — still the identical inversion of intent.

---

## src/physics.py

Read in full. This module is unusually thorough about the exact failure class the brief asks
about (guards that cannot fail, falsy-zero, silent wrong answers) — `kinetic()`, `joules_for()`,
`sphere_volume()` and `binding_energy()} each separately refuse non-positive, non-finite, and
NaN inputs, and each also checks its OWN RESULT for non-finiteness (catching overflow inside the
arithmetic, not just at the input boundary), with each fix cross-referenced to the order that
found it. I traced every guard's order (mass-positive before mass-finite before the NaN-shaped
speed check before `v >= c` before the Newtonian/relativistic branch) and found no gap, no
tautology, and no case where a NaN or infinity could reach a returned value un-flagged. No
findings in this module.

---

## src/tuning.py

Read in full. `workers()`'s own docstring already documents fixing the exact falsy-zero shape
found twice above in this batch ("ZERO IS A REQUEST, NOT AN ABSENCE... `None` still means 'no
request'"), and the code matches it (`return min(requested, n) if requested is not None else
n`). `regime()`'s cloud/local/starved decision correctly requires both bucket count and a
judged success-rate floor (`CLOUD_MIN_SUCCESS`) rather than reachability alone, and `profile()`
reads `_CACHE["buckets"]` from the same cached reading that produced the cached regime label, so
the pairing race the module's own comment warns about (worker count and label from two different
moments) cannot occur — every `_CACHE.update(...)` sets both fields together. No findings in
this module.

---

## Summary of findings by severity

* **HIGH (2):** B16-4 (`worldseed.py:374`), B16-5 (`retry_synthesis.py:298`) — both the identical
  falsy-zero-on-an-explicit-integer-CLI-flag shape as this batch's `binding_health.py` fix,
  neither previously filed for this specific reason.
* **MEDIUM (1):** B16-1 (`binding_health.py:1186`) — the one `_land_cas` call site in `run()`
  without the try/except its two siblings both have.
* **LOW-MEDIUM (1):** B16-2 (`local_agent.py:586-587`) — an unmarked 200-char truncation of a
  single grep hit's text, inconsistent with every other cut in the file.
* **LOW (1):** B16-3 (`wiki_source.py:402-429`) — `all_categories`'s cache key omits `hard_stop`;
  not reachable given today's callers.
* **QUESTION (1):** L16-Q1 (`liveness.py:449-477`) — PHANTOM's `defined` set is not scoped per
  function; may be a deliberate consequence of the file's stated "err toward no false positive"
  policy, or may be an unnoticed gap of the same shape the file fixed elsewhere. Both readings
  given; no live instance found either way.
* **No findings:** `src/physics.py`, `src/tuning.py`.

Confirmed-but-not-re-filed (already open elsewhere, checked and found unchanged): the
`local_agent` rc-for-a-failed-answer question (171ade4c7d27), `worldseed.URL_SETTABLE`
(e68664e621bf), `find_categories(limit=0)` and `rank_by_size(top=0)` in `wiki_source.py`
(sweep26/sweep27/sweep42).
