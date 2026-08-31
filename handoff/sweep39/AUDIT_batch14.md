# AUDIT — run39, batch 14

Modules owned (from `sweep_plan.batches(16)[13]`, read programmatically, not typed):

    workorders.py  overwatch.py  wiki_source.py  liveness.py
    axis_correlation.py  snapshot.py  coverage.py  profile.py

All eight read IN FULL (4,824 lines total). No source file was edited. Scratch work stayed in
the session scratchpad; nothing but this `.md` was written under `handoff/`.

`workorders.py` was read in its current state, including `closed_at()` / `_closed_rows()` /
`ghost_orders()` and the two detector sections added by today's maintenance shift
(CLOSED_ORDER_BACK_IN_THE_OPEN_QUEUE at 1155-1209, ORDER_ADDRESSED_TO_A_RUNG_THAT_CANNOT_REACH_IT
at 1211-1266). Both are complete and coherent; neither is reported as half-finished.
`sweep_detectors()` was NOT called.

---

## A note on the brief's severity vocabulary

The brief names severities `CRITICAL/MAJOR/MINOR/INFO`. `workorders.SEVERITY` (workorders.py:60)
is `["INFO", "MINOR", "MAJOR", "BLOCKING"]`, and `file_order` **raises `BadOrder`** on anything
else (workorders.py:387-388). `CRITICAL` is not a filable severity. Verified against the live
queue: 166 open orders, all of them `MINOR`/`MAJOR`/`INFO`, none `CRITICAL` or `BLOCKING`.
Orders below use `MAJOR` where the brief would have said `CRITICAL`.

---

## FINDINGS

### F1 — MAJOR — the secret scan reports CLEAN when the export tree is absent
`src/workorders.py:938`, closing at `:952-961`

```python
raw = P.scan_for_secrets(P.SITE) if os.path.isdir(P.SITE) else []
```

Verified: `publish.SITE` is `publish.export_root()` (publish.py:126), which resolves to
`%USERPROFILE%\panscriptum-export` when `PANSCRIPTUM_EXPORT` is unset or is refused as a
throwaway path (publish.py:111-123). It exists on this machine today, so the fault is latent —
but a fresh clone, a deleted export checkout, or a `PANSCRIPTUM_EXPORT` pointing somewhere not
yet created all make `os.path.isdir(P.SITE)` false.

When it is false, `hits` is `[]`, and two BLOCKING orders are then **closed by a scan that never
ran**:

* `:952` `_fire(not hits, "SECRET_STAGED", ...)` — `_fire`'s `ok` branch (`:741`) resolves the
  order with `"detector stopped firing"`.
* `:958-961` closes `SECRET_IN_EXPORT` with the resolution
  `"scanner is clean (suppressed findings excluded)"` — a positive assertion of cleanliness.

`SECRET_IN_EXPORT` is the code the 2026-08-28 OWNER halt was raised under (see this file's own
comment at 1062-1069). Closing it on an absent directory writes a false clean into the
append-only paper trail.

The contrast is one section away and is the correct shape: the battery reader at `:970-988`
returns `None` on any read failure and `battery_faults` turns that into `BATTERY_STALE` /
`PREFLIGHT_STALE` — fail-closed, and the module's own comment at 70-73 states the doctrine
("a missing artifact fires STALE, never silence").

**Remedy:** when `P.SITE` is not a directory, do not compute `hits` at all. Either route the
condition to `_detector("secrets", False)` so it files DETECTOR_FAILED under
`where="secrets"`, or give it its own code (`SECRET_SCAN_DID_NOT_RUN`, handler RUN, severity
MAJOR, `where=P.SITE`) that self-closes when the directory reappears. In no case may
`SECRET_STAGED` or `SECRET_IN_EXPORT` be resolved on a scan that did not execute.

---

### F2 — MAJOR — an unreadable BINDING_HEALTH.json is reported as a clean, complete detector
`src/workorders.py:850-857`, with the consequences at `:858-860`, `:919-930`, `:931`

```python
rec = {}
try:
    with open(BH2.OUT, encoding="utf-8") as f:
        rec = json.load(f)
except Exception:
    rec = {}
```

`BH2.OUT` is `data/BINDING_HEALTH.json` (binding_health.py:50). The bare `except Exception ->
rec = {}` collapses three different conditions into one: the file is absent (a fresh tree, and
genuinely benign), the file is torn or half-written (a real fault), and the file is held open by
another reader.

Consequences, all verified by reading the code below it:

* `suspect` (`:858-860`) is empty, so no `BINDING_SUSPECT` /
  `BINDING_RIGHT_ENTRY_NAMES_ARE_NOT_TITLES` / `BINDING_HOST_SERVES_ANOTHER_WIKI` order is filed.
* the recovery pass (`:919`) iterates `rec.get("hosts") or []`, which is empty, so **no order is
  closed either** — the block is a total no-op.
* `_detector("binding-suspect", True)` at `:931` then declares the detector ran to completion
  and resolves any standing `DETECTOR_FAILED` at `where="binding-suspect"`.

So a corrupt canary record makes that whole area of the queue read exactly like an area with
nothing wrong in it — which is the failure `_detector`'s own comment at `:747-756` was written
to end ("that detector's area of the queue read exactly like an area with nothing wrong in it"),
arriving through a handler one level up from the one that comment hardened.

`_load()` in this same file already draws the correct line at `:281-295`: `FileNotFoundError`
alone means absent and absent is honestly empty; anything else raises.

**Remedy:** split the handler. `except FileNotFoundError:` keeps `rec = {}` (nothing to say, and
still close nothing). Any other exception should re-raise, or call `_detector("binding-suspect",
False)` directly, so the condition files under `DETECTOR_FAILED` with the exception and
traceback the wrapper already collects at `:764-779`.

---

### F3 — MAJOR — `overwatch.save()`'s verdict is discarded by all three callers, and its generic failure path is silent
`src/overwatch.py:279-281`; call sites `:834`, `:883`, `:893`

`save()` has three false-returning paths:

* `:240-245` the `_UNPRESERVED` refusal — prints to stderr itself.
* `:272-276` the denied replace — prints to stderr itself.
* `:279-281` `except Exception: silence.note("overwatch.py:save"); return False` — **prints
  nothing.** `silence.note` bumps a class-name counter in `state/failures.json`, which
  `workorders.py:750-752` describes as something "nobody on the handler ladder is described as
  reading".

All three call sites ignore the return value (verified by grep: `save(led)` at 834, 883, 893 —
no assignment, no test anywhere in the file). So an exception raised inside
`_reconcile_with_disk` (`:247`, which parses the on-disk ledger and calls `_merge_ledgers`) or
inside `silence.write_json` leaves the round printing its per-module
`"{m:<24}{len(found):>3} raw {fresh:>3} new"` lines (`:890`) and its closing
`"{open_n} finding(s) open -> WATCH.md"` (`:896`) exactly as if everything had persisted.

This is the same discarded-verdict shape the surrounding comments were written to close one
layer down — `:266-271` ("the code then dropped the verdict that reports it ... a denied replace
made each of those saves a no-op that looked identical to a successful one") — and it was closed
inside `save()` while every caller of `save()` kept doing it.

**Remedy:** two parts. (a) Give the `except Exception` handler at `:279` a stderr line naming
the exception type and message, matching the two named paths above it. (b) Have `round_once`
test the return — at minimum the final `save(led)` at `:893`, whose failure means the entire
round's model reads were lost — and fold it into the closing print the way `wrote` already is at
`:896-897`.

---

### F4 — MAJOR — the only account of a crashed structure scan is cut to 90 characters
`src/overwatch.py:408` and `src/overwatch.py:418`

```python
out["error"]        = f"{type(e).__name__}: {str(e)[:90]}"
out["estate_error"] = f"{type(e).__name__}: {str(e)[:90]}"
```

`write_report` prints these AS the whole explanation, replacing the reassuring number:

* `:682-684` `"modules that will not import: **UNKNOWN — the import scan itself failed** — {struct['error']}"`
* `:691-693` the same for `estate_error`.

WATCH.md is a file, not a console. This module removed the identical caps twice for exactly that
reason and says so in place: `:709-711` removed a `[:80]` on the reconcile detail ("WATCH.md is a
file, not a console: markdown wraps for free and there is no column to fit"), and `:733-743`
removed `actual[:180]` and `claim[:160]` under order 80519f08d9ac, noting that the house
exemption for console renderers "does not reach it". A 90-character cut on the one sentence that
says *why an entire tier is UNKNOWN* is the same fault, in the same file, in the reporting path
those two fixes were about.

Unmarked, too: nothing in the rendered line signals that the message was cut.

**Remedy:** drop `[:90]` at both sites. If a short headline is wanted for the console line at
`:818-819`, cut there — that is a console renderer and the cut is reversible at that call site.

---

### F5 — MINOR — `liveness`'s DEAD MODULE limb filters module names through a table of function names
`src/liveness.py:366`

```python
if _stem(n) not in referenced and _stem(n) not in EXEMPT
```

`EXEMPT` (`:61-78`) is a table of FUNCTION and METHOD names with a reason each: `main`,
`__init__`, `__repr__`, `__str__`, `__enter__`, `__exit__`, `do_GET`, `do_POST`, `do_HEAD`,
`log_message`. The DEAD MODULE limb tests MODULE stems against it.

Verified against the tree: no file in `src/` is named after any `EXEMPT` key (checked all ten;
there is no `main.py`, no `do_GET.py`, and so on). So the second conjunct is **always true** — a
filter that has never removed a row and, given the naming conventions of both tables, cannot.

Worse if it ever did fire: the reason attached would be the wrong one. `"main": "CLI entry
point, called by __main__"` is not a reason a whole module is legitimately unimported, and this
module's own doctrine (`:47-50`) is that "an exemption with no reason attached is how a real
finding gets waved through next time".

The module limb genuinely *needs* an exemption table it does not have. A module reached only
from outside `src/` — a scheduled task line, a `python src/x.py` invocation in a shell script,
an entry in a job roster the string pass at `:357-358` cannot see — is a legitimate never-imported
module, and today it has nowhere to be recorded except as a permanent DEAD MODULE row against
`drill.LIVENESS_CEILING` (52, drill.py:110).

**Remedy:** either delete the clause (honest: it does nothing), or replace it with a purpose-built
`EXEMPT_MODULES = {name: reason}` and test against that. Do not extend `EXEMPT` — the function
pass and the module pass need different reasons, and one table serving both is how the reason
stops matching the finding.

---

### F6 — MINOR — a branch that cannot be taken, inside the module whose subject is branches that cannot be taken
`src/liveness.py:318`

```python
scoped[key] = set().union(*[self_attr[k][1] for k in seen]) if seen else set()
```

`seen` is built by the `while stack` loop immediately above (`:306-317`), which starts
`seen, stack = set(), [key]` and whose first iteration executes `seen.add(k)` for `k = key`.
`seen` therefore always contains at least `key`, the `if seen` test is always true, and the
`else set()` arm is unreachable for every input.

Not harmful, and `liveness`'s own TAUTOLOGY pass cannot see it — that pass only inspects
`ast.Compare` nodes (`:404-414`), and this is a truthiness test in an `IfExp`. Worth removing
because this is the file that carries the standing lesson.

**Remedy:** `scoped[key] = set().union(*[self_attr[k][1] for k in seen])`.

---

### F7 — MINOR — `liveness`'s headline docstring asserts a defect in `profile.py` that has been fixed, and cites two line ranges that no longer hold what is claimed
`src/liveness.py:7-9` and `src/liveness.py:39-45`

Two stale citations and one stale present-tense claim, all three verified against the current
files:

1. `:7-8` cites `profile.py:182-187` as "a round-trip self-test comparing a decoded field
   against the input it was handed, so `d["profile"] != r["profile"]` is tautologically False.
   Green for ever." **profile.py:182-187 today is the SAMPLE header and its print loop**
   (`print("\n" + "-" * 100)` / `print("SAMPLE")` / `for r in rows[:8]:`). The tautology is gone:
   the round trip now lives at profile.py:196-208 and re-encodes what `decode()` extracted
   (`re_encoded = encode(d["address"], d["genre"], ...)` at 204-205, compared at 206). A grep
   for `d["profile"]` in profile.py returns exactly one hit — line 199, the comment recording
   that this was the old bug.

2. `:9` cites `cleanup.py:77-80` as "a guard whose condition names a regex that is never
   defined". **cleanup.py:77-81 today is a docstring paragraph** ("THE TEST IS THE ENCLOSING
   PARENTHETICAL, scanned back from the `?` to its opening paren..."). No guard, no regex name.

3. `:39-45` goes further than a historical citation. It says, in the present tense: "It does NOT
   find the `profile.py:182-187` instance that motivated it, because that one is SEMANTIC ...
   Catching that class needs dataflow this module does not do, **so `profile.py` stays on the
   human list.**" That tells every reader of this file's docstring that a known, unfixed
   tautology is standing in `profile.py`. It is not.

For contrast, the third worked example in the same list was checked and **is still accurate**:
`coverage._p()` (coverage.py:47-55) still has zero callers — every reference to it in `src/` is a
comment (drill.py:56-57, 5091-5105; liveness.py:10, 113, 179, 252, 266). That one must NOT be
"fixed": `drill.py:5102` nets on `liveness` reporting it as dead, so deleting `_p` would breach a
net. It is a deliberate fixture and is recorded here so a later shift does not tidy it away.

**Remedy:** keep the worked examples — they are the module's motivation and its test set — but
mark the two fixed ones as FIXED with their current locations (`profile.py:196-208`,
`cleanup.py` by symbol), and delete or re-point the present-tense "so `profile.py` stays on the
human list" claim at `:44-45`. Cite by SYMBOL rather than by line, per the rule this repo
already records at dashboard.py:77-80 ("a baked-in line number rots the moment anything above it
moves") — the two stale citations above are that rule's prediction coming true in the file that
is supposed to notice.

---

### F8 — MINOR — stale cross-reference `silence.py:408`
`src/workorders.py:342`

> "`silence.write_json` carries pid and thread for exactly this reason (silence.py:408); this is
> the same fix."

Verified: **silence.py:408 is `except OSError:`** inside `replace_if_unchanged` — a rename-failure
handler, unrelated to temp-file naming. The pid+thread temp name is at **silence.py:511**
(`tmp = "%s.%d.%d.tmp" % (path, os.getpid(), _th.get_ident())`), and the reasoning the comment is
pointing at is at **silence.py:483** ("THE TMP NAME CARRIES PID AND THREAD").

The claim itself is true; only the address is wrong.

**Remedy:** cite by symbol — "`silence.write_json`'s temp-name construction" — which cannot rot.

---

### F9 — MINOR — the queue listing cuts a work order's `what` at 70 characters with no marker
`src/workorders.py:1336`

```python
print("  [%-8s] %-12s %s" % (r.get("severity"), r.get("id"), r.get("what", "")[:70]))
```

This is a console renderer, and this module's house exemption explicitly permits a cut there —
`:405-409`: "the console renderers already truncate for display at their own call sites (which
is where a cap belongs, because it is reversible there)". So the cut is not the fault.

The fault is that it is **unmarked**. The same module argues at `:401-405` that "a work order's
REMEDY is written at the END", and its own detector at `:1140-1142` repeats it. Seventy
characters of a 600-plus-character order arrive with nothing to say more exists. The house form
is one file over: overwatch.py:936-939 cuts at 150 and appends `"... (whole text in WATCH.md)"`,
with the comment "An unmarked cut is the part that misleads, not the cut itself."

Verified this is a real gap in practice: 166 open orders, and the `what` fields are routinely
several hundred characters (`file_order` stores them uncapped by design since 2026-08-28).

**Remedy:** append an ellipsis and a pointer when the field was actually cut, e.g.
`w[:70] + ("... (full text: state/workorders.json)" if len(w) > 70 else "")`.

---

### F10 — MINOR — `decode()`'s regex admits address characters the alphabet cannot produce, so the refusal it was written to give is delivered as an opaque `ValueError` from a private helper
`src/profile.py:109`, with the failure at `:96` and `:114`

```python
m = re.fullmatch(r"PS-([0-9a-z]+)-([a-z]{2})([a-z])-([0-9a-z]{4})-([0-9au])([0-4])", profile)
```

`B32` (`:66`) is deliberately 32 symbols with `i`, `l`, `o` and `u` removed — the comment at
`:52-65` explains at length that `u` was removed in run #33 so it can be unambiguous as the
band's "unassayed" sentinel, and that an alphabet "that can read what it cannot write is a
decoder that cannot say 'this is not one of mine'".

The character class `[0-9a-z]` includes all four excluded letters. A profile string carrying one
of them passes `re.fullmatch`, so the `raise ValueError(f"not a world profile: {profile!r}")` at
`:111` — the guard written for exactly this — never fires. `_unb32` then reaches `B32.index(ch)`
at `:96` and raises a bare `ValueError: substring not found` from inside a private helper. Same
shape for the feature quartet: `[0-9a-z]{4}` at `:109` against `B32.index(ch)` at `:114`.

Honest scope, stated because the audit should not overclaim: the run #33 fix DID close the
dangerous half. The value is no longer silently wrong, and the exception type is the same
`ValueError` a caller of `decode` already has to handle. What is left is that the malformed
string is refused by the wrong code, with a message that names neither the profile nor the
offending character.

**Remedy:** build the class from the alphabet so the two cannot drift —
`"PS-([%s]+)-([a-z]{2})([a-z])-([%s]{4})-([0-9au])([0-4])" % (B32, B32)` — which restores the
`:111` message as the single place a malformed profile is refused.

---

### F11 — MINOR — `widening()` re-reads the matrix 55 times on the missing-matrix path, and its docstring describes behaviour it does not have
`src/axis_correlation.py:336-346`, with `rho`'s re-load at `:308`

Docstring at `:331`: "The announcement fires once here rather than 55 times inside `rho()`."

What the code does when `load()` returns None at `:336`: `_no_matrix("widening-no-matrix")` is
called at `:338`, and then `doc` — still `None` — is passed down to `rho(a, b, doc)` at `:346`
inside the 55-pair `itertools.combinations` loop. `rho` opens with `doc = doc or load()`
(`:308`), so every one of the 55 iterations re-executes `load()`, which re-opens (or re-fails to
open) `data/AXIS_CORRELATION.json`, and every one of them reaches `_no_matrix("rho-no-matrix")`
at `:310`.

The *ledger arithmetic* the docstring is defending is safe — `_NOTED` (`:129`) dedupes the
`silence.note` per site and `_ANNOUNCED` (`:132`) dedupes the stderr line per process, exactly as
`_no_matrix`'s own docstring at `:122-125` promises. So the harm is small. But two things follow
that the docstring's wording hides:

* 55 redundant filesystem reads per `widening()` call on the path that is already the degraded
  one.
* `MATRIX_FALLBACK_REASON` (`:127-128`) is re-assigned on every call, so it ends up stamped
  `"Site: rho-no-matrix"` rather than `"Site: widening-no-matrix"` — the site that actually
  produced the numbers a caller is holding is the one overwritten. Anything interrogating the
  module afterwards (which `:120` names as this variable's purpose) is told the wrong site.

**Remedy:** on the missing-matrix branch, keep the announcement and stop the re-reads — pass a
sentinel `doc` down (`{"pairs": {}, "mean_r": 0.0}` reproduces today's rho = 0 exactly and is
what the standing ruling c00cab9d0412 fixes), and reword `:331` to say what it does. The return
shape must stay three values in the same order: `drill.py:7043
correlation_actually_widens_the_bar` unpacks it.

---

### F12 — MINOR (latent) — `restore()` skips a manifest entry whose copy is missing and reports a count nobody is required to compare
`src/snapshot.py:295-296`

```python
for rel in m.get("took", []):
    src = _safe_join(os.path.join(ROOT, sid), rel)
    tgt = _safe_join(base, rel)
    if not os.path.exists(src):
        continue
```

A snapshot whose files were partly deleted, moved, or never fully copied restores fewer paths
than its own manifest names. The only signal is the returned `n` being smaller than
`len(m["took"])`, and nothing compares the two.

`verify()` does catch it — it walks `m["took"]` itself at `:248-252` and returns
`False, "restore omitted %s"` — but `verify()` restores into a temp directory. The path that
matters is `restore(sid)` with its default `into=HERE` (`:289`), the actual recovery after an
irreversible step, and that path has no such check.

This is the same shape `before()` was hardened against at `:94-107` under order f4193095edff —
"A PARTIAL SNAPSHOT REFUSES TOO, and until now only the empty one did ... An all-or-nothing
refusal that only fires when NOTHING was captured is a check that fires only in the case nobody
hits" — arriving from the restore end instead of the capture end.

Latent, and said so deliberately: `restore()` has no production caller today. The only importer
outside `drill.py` is `withdraw_chapters.py:195`, which uses `before()` and `verify()` only. That
is the same framing `_rel`'s docstring uses for its own case at `:60-63` ("Latent today ... but
this is the module that gates irreversible acts, so the latent case is the whole exposure").

**Remedy:** collect the skipped entries and raise `SnapshotFailed` naming them once the loop
ends — `SnapshotFailed` is already this module's word for "the copy did not happen"
(`:40-41`) — or return `(n, missing)` so no caller can read a partial restore as a whole one.

---

### F13 — INFO — `(_load() or {})` guards against a return `_load()` cannot make
`src/workorders.py:715` and `src/workorders.py:1233`

`_load()` either returns a `dict` or raises `QueueUnreadable`: the non-dict case raises at
`:290-295`, `FileNotFoundError` returns `{}` at `:281-282`, and every other exception raises at
`:283-289`. So `or {}` can only ever substitute `{}` for `{}`.

Harmless, but it reads as a guard against an unreadable queue at both sites, and it is not one —
the `QueueUnreadable` propagates. (That propagation is correct at both sites: `ghost_orders()`
is called inside the `try` at `:1181` and the LOCAL-rung scan inside the `try` at `:1229`, so an
unreadable queue files `DETECTOR_FAILED` through `_detector`. Nothing needs to change about the
behaviour — only the misleading fallback.)

**Remedy:** drop the `or {}` at both sites.

---

### F14 — MINOR — `verify_open` cuts the claim it re-checks and the reason it records
`src/overwatch.py:604-605` and `src/overwatch.py:618`

```python
+ "CLAIM: "         + str(f.get("claim"))[:400]  + chr(10)
+ "OBSERVED THEN: " + str(f.get("actual"))[:400] + chr(10)
...
why = str(got.get("why") or "")[:300]
```

Two different cuts with two different weights:

* The `[:400]` pair feed the auto-triage prompt. A model asked to rule `refuted` /
  `confirmed` / `unclear` on a **truncated** claim can close a finding on half of what was
  filed, and a `refuted` verdict sets `state = "closed"` at `:620`. Order 80519f08d9ac measured
  this population directly and is quoted in this same file at `:735-739`: "of 435 findings
  recorded, 71 carry an `actual` longer than 180 characters (longest 966)". At 400 the
  affected count is smaller but not zero.
* The `[:300]` on `why` is a STORED field. It becomes `f["verdict"] = "auto-triage refuted: " +
  why` at `:621` — the only record of why an open finding was automatically closed. That is
  precisely the argument `workorders.resolve` makes about its own `how[:400]` at
  workorders.py:449-457 ("NO CAP ON THE RESOLUTION ... which destroyed the one thing the paper
  trail exists to keep: WHY an order was closed").

Both are unmarked. Defensible reading, recorded honestly: the prompt cuts have a real budget
argument behind them (the local model's window is this module's stated binding constraint,
`:91-94`), so those two are a QUESTION rather than a flat finding. The stored `why[:300]` is
not a budget question at all and has no defence.

**Remedy:** remove the `[:300]` on the stored verdict outright. For the prompt, either remove
the `[:400]`s (a finding's claim plus actual is small next to a 7,000-character `SLICE`) or mark
them so the model is told the text was cut, the way `local_agent.TOOL_MSG_MAX` is described as
doing at local_agent.py:60-63 ("the model is always told what it did not get").

---

## QUESTIONS — two readings are defensible, so these are not filed as findings

* **`wiki_source._paragraphs` `:569`** — `" ".join(out)[:max_chars]` cuts the extracted lead
  prose mid-sentence with no marker, and `page_text`'s default `max_chars=900` (`:479`) is what
  the whole corpus read consumes. Against filing it: this is an excerpt with a declared
  parameter, the docstring says "Lead-section prose", and taking the whole article is explicitly
  rejected at `:489-490` on measured grounds (~420KB/article). Hard Rule 0 is about a smaller
  UNIVERSE returned in the shape of the real one — a roster, a page list, an entry list — and a
  lead excerpt is not a universe. Recorded, not filed.

* **`liveness` TAUTOLOGY pass, `:405`** — `if not isinstance(node, ast.Compare) or
  len(node.comparators) != 1: continue` skips every chained comparison, so `a < b < a` is
  invisible. The module states its honest limits at length (`:39-45`) but does not state this
  one. Against filing it: chained self-comparisons are vanishingly rare and the module's stated
  bias is to err toward silence rather than noise. Worth a sentence in the docstring's limits
  paragraph; not worth an order on its own.

* **`overwatch._anchored` `:499-502`** — a finding anchors if its symbol's bare tail is a
  substring of the source and is at least 3 characters. A model naming `get`, `out` or `key`
  anchors against almost any file. Against filing it: the filter's stated purpose (`:491-497`)
  is to remove claims about "the retry logic", which it does, and tightening it risks dropping
  real findings — an explicit tradeoff the docstring makes. Recorded.

## VERIFIED NOT A FINDING

* `workorders.py:1155-1266` — both detector sections added by today's shift are complete.
  `ghost_orders` correctly rejects the disjointness invariant both filing orders proposed
  (`:693-707`), separates ghosts from recurrences by `resolved_at` vs `last_seen`, and both
  sections wire into `_detector` and self-close. `_closed_rows` skipping an unparseable line
  (`:685-688`) errs toward missing a ghost rather than inventing one, and says so.
* `axis_correlation.py:379-385` — the citation `dashboard.py:77-80` was checked and is
  **correct**: those lines hold exactly the "a baked-in line number rots the moment anything
  above it moves" rule it claims.
* `coverage._p()` — still uncalled, still correct to leave alone (drill.py:5102 nets on it).
* `wiki_source.all_categories` `:408` / `find_categories` `:476` / `category_members` `:580` /
  `rank_by_size` `:656` — every one defaults to no cap and the `hard_stop` cache guard at
  `:426-428` correctly refuses to memoise a partial walk. Clean.
* `snapshot._rel` / `_safe_join` — containment holds in both directions; `verify()`'s
  `_dir_matches` really does read directory contents (`:203-230`), closing the
  `os.path.exists`-only hole its own docstring describes.
