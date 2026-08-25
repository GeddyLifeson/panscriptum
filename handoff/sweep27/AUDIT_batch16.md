# Batch 16 sweep audit (run27)

Modules read in full, every line, no sampling:
- src/build_terminal.py (580 lines)
- src/local_agent.py (580 lines)
- src/custodes.py (419 lines)
- src/ingest_doc.py (303 lines)
- src/hosts.py (254 lines)
- src/cleanup.py (209 lines)
- src/resonance.py (150 lines)

(`wc -l` reported one fewer per file than the actual last line number in each case — files end
without a final blank-line count mismatch; line numbers below are the `cat -n` / Read line
numbers, i.e. the real file lines.)

---

## local_agent.py — EXTRA FOCUS module (the gated write path)

### 1. local_agent.py:446-476 [HIGH] [CONFIRMED] — no locking around the write/gate/revert cycle: a concurrent invocation can clobber another's landed edit, and any concurrent reader sees unverified/possibly-broken code for the full gate duration

`t_propose_patch` writes straight to the **live** file path (`open(full, "w")`, non-atomic
truncate+write, no temp file, no `silence.write_json`/`replace_retry`), *then* runs `_gates()`
(parse, pyflakes ≤120s, import ≤180s, `verify_math.py` ≤600s — up to ~900s wall-clock in the
worst case), and only reverts to the in-memory `backup` variable if a gate fails.

Two distinct hazards follow, and neither is mitigated anywhere in this file (`grep -n
"lock\|Lock\|flock\|filelock"` over the file returns nothing):

- **(a) Broken code is live on disk, readable, for the whole gate window.** The parse check
  itself runs *after* the write (`_gates()`'s first action is `ast.parse(open(full,...))`), so a
  syntactically broken patch sits at its real repo path — importable by any other process,
  cron job, or subagent — until the gate loop notices and reverts, which for a patch that fails
  only at the `verify_math` stage can be several minutes later.
- **(b) A revert from run A can silently erase a successful edit from run B.** `backup = original`
  is a snapshot taken once, at the *start* of `t_propose_patch`, before the write. If two
  `local_agent.py` invocations (the delegation-ladder design explicitly anticipates concurrent
  rungs: "bots -> OLLAMA -> Claude subagents -> Claude") target the same file — run A patches
  region X, gates start; run B (reading the file *after* A's write) patches region Y and lands
  cleanly while A's gates are still running; A's gate then fails — A's revert writes `backup`
  (the pre-A, pre-B original) back over the file, discarding B's completed, verified edit with
  no trace and no error surfaced to either run.

The module's own docstring ("A backup is written before and restored on ANY failure... This is
the same six-gate discipline foreman's model lane uses") states this as an unconditional safety
guarantee. It is only sound single-process; under concurrent invocations — which this module's
own architecture description invites — it is not. This is a genuine cross-process
read-modify-write race on a shared file with no atomic test-and-set, matching the concurrency
lens directly.

Failure scenario: two local_agent.py tasks are dispatched in parallel, both touching
`src/foo.py`; the second's successful, gate-passed patch is silently reverted away because the
first patch (to an unrelated region of the same file) failed its gate later.

### 2. local_agent.py:552-561 [MEDIUM] [CONFIRMED] — no exception guard around tool dispatch; a malformed tool call crashes the whole run with an unhandled traceback

In `run()`'s turn loop, `res = t_propose_patch(apply=apply, log=patches, **args)` /
`res = impl[fn](**args)` is called with **no try/except**. Every tool function requires certain
keys (`t_read_file(path, ...)`, `t_propose_patch(path, find, replace, ...)` — `path`/`find`/
`replace` have no defaults) and none of the five tool implementations catch their own
`TypeError`s. If the model emits a tool call missing a required argument (a documented failure
mode for smaller/quantized tool-trained models under load), the call raises `TypeError`
uncaught, propagates out of `run()`, out of `main()` (which also has no try/except around
`run(...)` at line 573), and kills the process with a raw Python traceback instead of the
module's own graceful `{"ok": False, "error": ...}` contract used everywhere else in this file.

Related: `t_propose_patch`'s own read of the target file at line 434 —
`original = open(full, encoding="utf-8").read()` — has no `errors="replace"` (unlike
`t_read_file` at line 279, which does). A non-UTF-8 target file raises `UnicodeDecodeError`
before the try/except block that starts at line 446, so it also isn't caught by the
apply-time revert logic; it propagates and crashes the run the same way.

Failure scenario: the local model calls `propose_patch` with a `find`/`replace` pair but no
`path` key (a documented tool-calling slip on smaller models) → `TypeError: missing 1 required
positional argument: 'path'` → uncaught → the entire delegated task aborts with a traceback
instead of the model getting `{"error": ...}` back to retry from.

### 3. local_agent.py:574 [MEDIUM] [CONFIRMED] — final CLI summary truncated to 8000 chars with zero disclosure, inconsistent with the file's own established truncation discipline

`print(json.dumps(out, indent=1, ensure_ascii=False)[:8000])` in `main()` silently cuts the
printed JSON at 8000 characters. Every *other* truncation point in this same file discloses
itself: `t_run_check` returns an explicit `"truncated": len(out) > len(tail)` flag and a note
saying which window is shown (lines 226-230); `t_read_file` reports `chars_after_slice` and
`total_chars` (lines 283-284). This one final, most user-visible print has no such flag — if
`out["answer"]` or `out["patches"]` is long, the tail (which could contain the actual outcome of
later patches, or the true final answer) is silently dropped from what the operator sees.

### 4. local_agent.py:561 [HIGH] [CONFIRMED — restated from known-open, with concrete mechanism]

`messages.append({"role": "tool", "content": json.dumps(res)[:SLICE]})` reuses the 12000-char
read-window constant as the cap on the *serialized JSON* of every tool result, including
`t_read_file`'s own response. For a large file read near the SLICE boundary, `res["slice"]`
alone can already be ~12000 raw characters; JSON-encoding it (escaping quotes/backslashes/
newlines) plus the surrounding `{"path":..., "offset":..., "slice":"...", "chars_after_slice":
N, "total_chars": M}` envelope pushes `json.dumps(res)` well past 12000 characters. The `[:SLICE]`
cut then lands **inside** the `"slice"` field's escaped content or beyond it, silently:
(a) producing invalid/unterminated JSON in the tool message the model receives, and (b) chopping
off the `chars_after_slice`/`total_chars` disclosure fields that are the only signal the model
has for "there is more to read, page again." This directly contradicts the module docstring's
own claim (line 11): "read_file ... sliced — iterative reads, never a truncation."

### 5. local_agent.py:406-407 [HIGH] [CONFIRMED — restated from known-open, generalized]

`modname = os.path.basename(full)[:-3] if _lower.endswith(".py") else None`. Any file extension
other than exactly `.py` (case-insensitively) — `.pyw`, `.pyi`, a stray `.py.bak` that
`os.path.isfile` still resolves to something real, etc. — yields `modname = None`. Consequences,
traced end to end: `t_propose_patch`'s `denied` check (lines 429-430) only matches on `modname`
(module-name denylist) or `rel` (the two-entry `DENYLIST_PATHS`, currently just
`config.yaml`) — neither test can catch a non-`.py`-named file that is nonetheless the checking
machinery. `_gates()` (line 341) independently re-derives the same `full.lower().endswith(".py")`
test and skips parse/pyflakes/import entirely for such a file — leaving only the whole-suite
`verify_math` run as a backstop. No `.pyw` file exists in this repo today (latent only), but the
bypass is general to any non-`.py` extension, not `.pyw` specifically.

---

## build_terminal.py

No correctness, swallowed-failure, cap, or two-writer defects found. This module's prior
in-file bug fixes (documented as "BUGS m10, 2026-08-24") check out under direct tracing:

- Line 568: `data.replace("<", "\\u003c")` correctly neutralizes `</script>`-breakout risk before
  splicing catalogue JSON into an inline `<script>` block; JSON string escapes make this lossless.
- Line 79/571: `TEMPLATE.replace("__DATA__", data)` — exactly one `__DATA__` occurrence in
  `TEMPLATE`; Python's single-pass `str.replace` does not re-scan the substituted text, so no
  self-referential re-substitution risk even if `data` itself contained the literal string
  `__DATA__`.
- Line 85-87: JS `esc()` mirrors `render.py`'s `html.escape()` discipline; applied consistently
  to every catalogue-derived string reaching `innerHTML`/attribute contexts I traced (node names,
  tooltips, `data-k` attributes, panel HTML).
- The various `.slice(0, N)` calls in the JS (lines 241, 291, 323, 348, etc.) are **display-only**
  truncations for SVG label fitting — the untruncated name is always still present via the
  `<title>` tooltip (line 251) and/or the panel (line 501+), so these are not Hard-Rule-0
  violations of the underlying data, just rendering affordances, and each is accompanied by a
  comment explaining the specific readability failure it fixes.
- `OVERVIEW_DEPTH=3` limits rendered shell depth per view, but deeper shells are reachable by
  descending (`descend()`, line 544) and are not dropped from `DATA` — a rendering strategy, not
  a data truncation.

---

## custodes.py

### 6. custodes.py:335-344 [LOW] [CONFIRMED, but self-documented in the code's own comment]

`"covers_every_reading": all(abs(v - consensus) <= half + 1e-12 for v in vals)` is a check that
cannot fail by construction: `half` is defined two lines above (line 320) as
`max(1.96 * total_sd, max(abs(v - consensus) for v in vals))`, i.e. it is *already* the max
absolute deviation from `consensus` (or larger), and is only ever widened afterward (line 323,
`+= stale`, non-negative). So `abs(v - consensus) <= half` holds for every `v` for every possible
input. This matches the sweep's "a check that cannot fail" pattern exactly. It is not a hidden
bug — the code's own comment (lines 335-343, tagged "m30") already states this precisely and
explains why it is being left in place (states the invariant at the point a reader would look
for it) and flags what a *real* check would need to measure instead (whether the un-widened
1.96·sd band alone covered every reading). Flagging per the sweep brief's instruction to report
this pattern regardless of prior documentation; no action needed beyond confirming the module's
own self-assessment is accurate.

### 7. custodes.py:315 [LOW] [SUSPECTED] — `prior_share` defaults to 1.0 on a 0/0 case that may not mean what the default implies

`prior_share = (prior_var / total_var) if total_var > 0 else 1.0`. If `total_var == 0` (every
Custos's `reading` value identical), the code reports "100% prior divergence" — but zero total
variance means there is *no* divergence to attribute, prior or evidential; the split is
genuinely undefined (0/0), not necessarily 1.0. Practically near-unreachable given that the ten
Custodes carry distinct `tilt`/`axis_emphasis` values (so identical readings across all of them
would require a coincidental cancellation), but the default direction (1.0, "irreducible")
silently asserts something the zero-variance state doesn't actually establish. Flagging as a
question rather than a confirmed defect since I could not construct or run a concrete input that
reaches it.

### 8. custodes.py:301-304 [LOW] [SUSPECTED, out-of-batch dependency] — early-return dict shape differs from the normal-path dict

When `len(readings) < 2`, `convene()` returns `{"decimal": None, "reason": "insufficient
readings; band-only"}` — missing every other key (`interval`, `consensus`,
`reading_spread`, `covers_every_reading`, etc.) that the normal-path return always includes. Any
caller (in `assay.py` or elsewhere, not in this batch) that unconditionally reads
`result["interval"]` or `result["reading_spread"]` after calling `convene()` would `KeyError` on
this path. Not traced further since the caller lives outside this batch's module list.

---

## ingest_doc.py

### 9. ingest_doc.py:216 [MEDIUM] [CONFIRMED] — entity description silently truncated to 2000 characters, no disclosure, no truncation marker

`"description": (e.get("description") or "").strip()[:2000]` hard-truncates every mined entity's
description at 2000 characters before it is merged into the record via
`write_record_catalogue`. Unlike every deliberate truncation elsewhere in this batch (compare
`t_run_check`'s explicit `"truncated"` flag in local_agent.py), nothing here records that a cut
happened, nothing preserves the remainder, and nothing signals it downstream. Given this
project's Hard Rule 0 ("No limit, no cap, no sample... of ... an entry list" and the CLAUDE.md's
explicit framing that a truncation "looked like a completed job" is the exact danger), a
long-form entity description returned by the extraction model (plausible for a named character
or event with a dense passage) loses everything past 2000 characters permanently and
undetectably — the record shows a description that reads as complete prose but is actually cut
mid-sentence with no marker.

### 10. ingest_doc.py:116-126 [MEDIUM] [CONFIRMED] — `record_path()`'s fuzzy fallback match is directory-order-dependent and can silently pick the wrong record file

```python
for fn in os.listdir(RECORDS):
    base = fn[:-5]
    if want in base or base in want:
        return os.path.join(RECORDS, fn)
```
`os.listdir()` is not sorted, and the loop returns the **first** filename whose stem is a
substring match (in either direction) of the wanted slug — not the best match, not an exact
match if one exists elsewhere in the directory, just whichever the filesystem happens to yield
first. For any two sources whose slugs are substrings of one another (e.g. a `"marvel"` slug vs.
a `"marvel-cinematic-universe"` slug, or a short franchise name that is a prefix of a spinoff's
slug), which record file `mine()` merges newly-extracted entities into is non-deterministic
across machines/filesystems and can silently merge one source's PDF-mined entities into a
different source's record.

Failure scenario: records directory contains both `arcanum.json` and `arcanum-worlds.json`;
`ingest_doc.py --source "Arcanum" --mine` computes `want = "arcanum"`; both filenames satisfy
`want in base`; whichever sorts first in `os.listdir()`'s (unspecified) order is silently chosen
and gets Arcanum's mined entities merged into it, even if the correct exact-name record was
`arcanum.json` and it happened to iterate second.

### 11. ingest_doc.py:218-219 [LOW] [SUSPECTED] — category mismatch silently defaults every unmatched entity into "Persons"

```python
"category": e.get("category") if e.get("category") in CATEGORIES else CATEGORIES[0],
```
If the model's returned category string doesn't exactly match one of the 7 long descriptive
enum labels (plausible: paraphrase, capitalization, trailing whitespace — the labels are full
sentences like `"Factions & Organizations (groups, nations, guilds, companies, orders)"`, not
short codes), the entity is silently reassigned to `CATEGORIES[0]` = "Persons ...", i.e. every
category mismatch defaults toward the same one bucket regardless of what the entity actually is
— a faction, place, or event miscategorized as a Person with nothing recorded to say the
category was rejected. Whether this is reachable depends on how strictly the `_ask()` backend
(`cascade_bridge`/`pipeline.ask`, both out of this batch) enforces the JSON-schema `enum`
constraint; flagging as a question rather than confirmed since I did not trace those callers.

### 12. ingest_doc.py:181, 206-263 [LOW] [SUSPECTED] — `known` is a per-process snapshot; two concurrent `mine()` runs on the same source could double-submit

`known` is built once from the on-disk record at the top of `mine()` (line 181) and updated only
from this process's own findings thereafter. If two `mine()` invocations run concurrently against
the same `--source` (plausible if the resumable, hours-long ingest is accidentally launched
twice, e.g. by two schedulers), both processes independently decide the same not-yet-seen entity
is "new," both attempt to write it via `write_record_catalogue`. Whether this produces a
duplicate entry or is deduplicated by the catalogue writer depends on `pipeline.py` (out of this
batch); flagging the gap since nothing in `ingest_doc.py` itself guards against concurrent same-
source runs (no lockfile, no PID check).

Good: the write-outcome handling itself (lines 233-251) is correctly built — `known` is rewound
on a denied write and the cursor is *not* advanced, matching the file's own detailed commentary
about the earlier 2026-08-23 stranded-entries incident. `register()` (line 103-113) and the
`ingest_state.json` cursor (lines 254-259) both correctly use `silence.write_json` /
`silence.replace_retry` per the two-writer contract.

---

## hosts.py

### 13. hosts.py:78-97 [MEDIUM] [CONFIRMED] — comment claims a fix that the code does not actually implement: three distinct failure/no-op reasons in `add()` still collapse to a bare `False`

The comment at lines 87-93 states: *"The verdict is returned, so a caller can tell a denied
write from a duplicate host — both used to be `False`, which is how a lost host looks like a
known one."* Reading the function itself: line 81 (`host` empty or already primary) returns
`False`; line 85 (host already recorded as a known duplicate) returns `False`; line 96 (the
`silence.write_json` call failed / denied) returns `False`. All three are the literal same value,
still. Nothing in this function's return contract distinguishes them — `add()` returns a bare
`bool` on every path, and `discover()` (the only caller, line 196: `if add(source, h, ...):
added += 1`) only ever branches on truthiness. The comment describes exactly the ambiguity it
claims to have resolved, immediately above code that still has it. This is the highest-value
category-6 pattern (a "fixed" claim sitting directly above the still-open bug) in this batch's
non-`local_agent.py` files.

Failure scenario: `discover()` finds a genuinely new, well-scored secondary host for a source;
`silence.write_json` is transiently denied (the file being read live by another `discover()`
run, per this file's own header commentary about concurrent walks); `add()` returns `False`;
the caller has no way to distinguish "this host is already known, nothing to do" from "this host
was lost to a write failure and should be retried" — exactly the ambiguity the comment says was
eliminated.

### 14. hosts.py:166-167 [LOW] [worth a question, likely deliberate] — `per_source` (default 24) caps the number of *candidate* hosts probed per source

```python
if per_source and len(cands) > per_source:
    cands = cands[:per_source]
```
This is a `[:N]`-shaped cap, flagged per the sweep's instruction to check every such pattern.
The accompanying comment (lines 161-165) argues this is safe because `HC.candidates()` orders
grounded/known hosts before speculative guesses, so the cut only ever discards low-confidence
guesses, never evidence already gathered — and the *adopted* hosts themselves (`SOURCE_HOSTS.json`
via `add()`) are never capped. I did not verify `HC.candidates()`'s ordering guarantee (out of
batch), so this rests on that module actually doing what the comment says; if candidate ordering
ever put a real, unconfirmed-but-legitimate host past position 24 for a source with a very large
candidate pool, it would never be probed. Framed as a question rather than a defect given the
explicit design rationale.

---

## cleanup.py

### 15. cleanup.py:73-80 [LOW] [CONFIRMED, cosmetic] — dead reference to a non-existent `_SETTING_META` pattern in the corruption-guard loop

```python
for _n, _p in (("_NAV", _NAV), ("_EMPTY_MECHANIC", _EMPTY_MECHANIC),
               ("_SETTING_META", None)):
    if _p is not None and any(ord(c) < 32 for c in _p.pattern):
        raise SystemExit(...)
```
`_SETTING_META` is not defined anywhere in this file — it is referenced only as a string label
paired with a hardcoded `None`, which the `if _p is not None` guard skips harmlessly. This
doesn't crash (Python never evaluates `_SETTING_META` as a name, only the string literal), but
it is vestigial: apparently a third regex that existed in an earlier version of this module was
removed and the guard tuple was never cleaned up. No functional defect, but worth noting since
this exact block's purpose is "refuse to load rather than pass quietly" on a mangled regex — a
reader could reasonably believe three regexes are being defended here when only two are.

No other defects found in `cleanup.py`. `clean_ceiling()`'s three-tier match strategy
(exact/head/prefix) is conservative and explicitly declines to guess when unresolved (line 120);
`PL.write_record(path, rec)` is used correctly for this module's in-place field edits (not
cast-growing, so the pipeline-side writer is the right one per the two-writer contract);
`_NAV`'s use of `.match()` (start-anchored, not end-anchored) combined with mixed `$`/`\b`
alternatives is deliberate per its own comment (line 45-46) and behaves as documented for the
cases I traced.

---

## resonance.py

### 16. resonance.py:71 [MEDIUM] [SUSPECTED] — `hodge_decompose()`'s Gauss-Seidel solver runs a fixed 600 iterations with no convergence check

```python
for _ in range(600):
    ...
```
There is no residual/delta check to confirm the iteration has actually converged before the loop
exits and `eta`/`curl_fraction`/`theta` are computed from whatever state exists after exactly 600
passes. For a small, well-conditioned graph 600 is almost certainly overkill; for a large or
poorly-conditioned contest graph (many nodes, sparse or nearly-disconnected edges) 600 fixed
iterations of unaccelerated Gauss-Seidel may not have converged, and the function has no way to
know or report that — it returns a confident-looking `eta` value regardless. I did not run this
against a real large graph to confirm actual non-convergence (no test harness for this in the
batch), so this is a code-shape concern rather than a demonstrated failure: a fixed iteration
count with no convergence test is the classic shape of a bug that only manifests at scale the
original author didn't test against.

### 17. resonance.py:124-125 [LOW] [worth a question] — `incomparability_rate()`'s `examples` list is capped at 5 with no disclosure

```python
if len(examples) < 5:
    examples.append((a, b))
```
Matches the `[:N]`-shaped pattern the sweep asks to flag. The real, uncapped count
(`"incomparable": inc`) is exact and always fully computed — only the illustrative `examples`
list is capped, and there is no note in the returned dict saying "5 of N shown." Likely
acceptable as diagnostic sampling rather than a served roster (the function's actual measured
quantity, the rate, is never capped), but flagged per the brief's instruction to treat every
`[:N]` as a candidate regardless of how reasonable it looks, and because there's no explicit
comment here (unlike elsewhere in this batch) asserting the cap is safe.

### 18. resonance.py:144-149 [LOW] [SUSPECTED, out-of-batch dependency] — `resonance_strength()` returns the first matching pair, silently ignoring any duplicate entries

```python
for p in g["pairs"]:
    if {p["a"], p["b"]} == {a, b}:
        return {"weight": p["weight"], ...}
```
If `SHARED_STAGE_GRAPH.json` (built elsewhere, out of batch) ever contains more than one entry
for the same unordered pair `{a, b}` — e.g. from two separate co-attestation sweeps appending
rather than replacing — only the first is used and any other (possibly more current) weight is
silently discarded. Not traced further since the graph-building code isn't in this batch.

No two-writer or write-path issues in this file at all — `resonance.py` performs no writes.

---

## Summary of severities

- HIGH: local_agent.py #1 (no-lock revert race), #4 (SLICE truncation cutting disclosure fields
  — known-open, mechanism now concrete), #5 (.pyw/non-.py extension gate bypass — known-open,
  generalized)
- MEDIUM: local_agent.py #2, #3; ingest_doc.py #9, #10; hosts.py #13; resonance.py #16
- LOW: custodes.py #6, #7, #8; ingest_doc.py #11, #12; hosts.py #14; cleanup.py #15;
  resonance.py #17, #18
- No defects found: build_terminal.py (clean pass, prior fixes verified correct)
