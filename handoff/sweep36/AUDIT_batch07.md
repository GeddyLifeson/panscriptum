# AUDIT — run #36, batch 07

Modules: `cascade_bridge.py`, `derivation.py`, `identity.py`, `prose_gate.py`, `context_budget.py`,
`hosts.py`, `suppressions.py`, `catalog.py`, `lognames.py`

Per the batch guidance, `prose_gate.py` was read with total care and was NOT edited, and
`prose_enabled`/`step4_enabled` were not touched. `identity.py`, `hosts.py`, `suppressions.py` and
`context_budget.py` were read as currently on disk (all four were noted as edited earlier today by
other agents).

---

## `prose_gate.py`

Read in full, line by line, with the "DELETION cost 145 chapters" history in mind. **No defect
found.** This is the strongest-built module in the batch:

- `gate_open()` / `step4_gate_open()` use strict `is not True` identity checks (not truthiness),
  read `config.yaml` fresh every call, and fail closed on an unreadable file, a non-mapping parse,
  or a missing `STEP4_PLAN.md`. Verified `overnight._prose_enabled()` (the only known historical
  re-implementation of this predicate, per its own docstring at `overnight.py:48-79`) now
  **delegates to `prose_gate.gate_open()` directly** rather than reimplementing the check — the
  `bool()`-vs-`is True` divergence its own docstring describes as "AUDIT DEFEAT 7" is fixed and
  verified by reading the current source, not the changelog.
- `evidence_ok()`'s "floor has a floor" check (`0.0 < floor <= 1.0`, prose_gate.py:181) correctly
  refuses `floor=0`, which is the exact incident scenario named in its own comment.
- `section_shortfall()`/`assay honesty` (`unearned_instrument`) are wired into `generate.py`
  (confirmed at `generate.py:304,314-322`) and their results are **not discarded** — a non-empty
  `_unearned` list raises `RuntimeError` and aborts the block; `assert_block_complete` raises
  `ProseRefused`. Neither call site swallows the return value.
- `cited_names_for()` correctly fails closed (`return set()`) on any read error, which is the safe
  direction for a check whose job is refusing an unearned Instrument score.
- Confirmed `generate.py:396-407` treats a corrupt `COVERAGE.json` as `return 1` (a real failing
  exit code), not a silent "0 jobs, exit 0" — this was itself a `run #36` sweep fix and is
  in effect now.

No finding. This module and its callers are exactly what the docstring claims them to be.

---

## `cascade_bridge.py` (1,270+ lines — the pipeline's most critical routing subsystem)

### 1. MAJOR — `prove()`'s per-bucket isolation is not real isolation; a dead bucket can be
   recorded "answers" via silent fallback to a different bucket

`prove()`'s docstring (cascade_bridge.py:1328-1339) claims: *"Send one tiny call to EVERY bucket
and record which actually answer... One three-token call per bucket settles it. The result is
fact rather than inference."* It calls `ask(..., pin=m.id)` per bucket and records
`verdict = "answers" if got else "no answer"` (cascade_bridge.py:1360) purely from whether `got`
is truthy — it never checks which bucket actually produced `got`.

`_ask_call`'s `pin` handling (cascade_bridge.py:998-1006) resolves the router `Model` object for
`pin` and calls `_ROUTER.reserve(pinned)`, then passes `pinned=pinned.id` into
`e.stream_chat(...)` (line 1112). But the external router
(`C:\Users\imarl\cascade\cascade\router.py:327-338`, `Router.candidates()`) explicitly documents
that **a pinned model still gets the rest of the pool as backup**:

    if pinned:
        for model in self.models:
            if model.id == pinned:
                rest = self._order([m for m in self.models if m.id != pinned and pool in m.pools])
                ready, _ = self.provider_ready(model)
                return ([model] if ready and model.enabled else []) + rest

and `engine.stream_chat()` (`cascade/engine.py:159-190`) "Walk[s] the WHOLE list until something
answers," with `limit = max_attempts or ... or len(candidates)` — and this project's
`config.json` sets no `max_attempts` (verified: `json.load(...).get("max_attempts")` is `None`),
so the walk is effectively unbounded through the whole pool. `cascade_bridge.py`'s own `pump()`
(lines 1109-1121) silently ignores `type: "failover"` events and keeps consuming the generator,
so if the pinned bucket fails and the router falls through to a live bucket further down the
list, `pump()` happily records `box["answered"]` = that OTHER bucket's label, `ask()` returns a
non-None `got`, and `prove()` writes `verdict: "answers"` **against the bucket it meant to test**,
which never actually worked.

Verified against live data: `data/POOL_PROOF.json` currently holds only four literal verdict
strings — `"provider disabled"`, `"no answer"`, `"answers"`, `"local"` — never a bucket-specific
HTTP status or provider phrase, which is consistent with this mechanism (a bucket only reads
`"no answer"` when the ENTIRE pool's fallback walk also failed within the 45s deadline, not when
that specific bucket failed).

This directly undercuts the module's central trust claim ("the result is fact rather than
inference") for every one of its callers: `dead_forever()` (below), the widen-fallback's
`answering` set (cascade_bridge.py:1051-1055), `read.py`, `tuning.py` and `standards.py` all treat
`POOL_PROOF.json` as ground truth about individual buckets. `try_disabled()`
(cascade_bridge.py:1369-1409) shares the identical pattern and the identical exposure.

This may be an accepted trade-off (the comment at `_ask_call`:1000-1006 says the pin exists so
"the prover would [not] test whichever bucket happened to be least busy, twenty-eight times," and
does not claim the pin prevents fallback) — **flagging as a QUESTION as well as a finding**: is
`prove()`'s isolation known to be partial, or was it believed watertight? If the latter, the fix
is straightforward: compare `got.get("_via")` (or `box["answered"]`) against `pinned.bucket`
before recording `"answers"`, or pass `max_attempts=1` to `stream_chat` so the pin truly means
"only this one."

### 2. MINOR — `dead_forever()`'s HTTP-code exclusion branch appears to be dead code given current
   `prove()` output, and lacks the word-boundary protection the rest of the file insists on

`dead_forever()` (cascade_bridge.py:300-355) reads `POOL_PROOF.json` rows and does:

    if any(code in v for code in ("401", "402", "404", "410")):
        out.add(r["bucket"])
    if "no such model" in v or "needs billing" in v or "bad key" in v:
        out.add(r["bucket"])

(`v = str(r.get("verdict") or "")`, line 346-347). Per finding #1 above, `verdict` is written by
`prove()` from exactly one of `"local"`, `"provider disabled"`, `"no API key"` (via
`provider_ready()`, `C:\Users\imarl\cascade\cascade\router.py:139-145`), `"answers"`,
`"no answer"`, or `type(ex).__name__` from an exception — **none of these strings can ever
contain `"401"`, `"402"`, `"404"`, `"410"`, `"no such model"`, `"needs billing"`, or
`"bad key"`.** Live `data/POOL_PROOF.json` confirms this (verdicts observed: only the four
strings named above). So this branch of `dead_forever()` — the one the docstring's worked
examples (`hyperbolic`, `zai`, HTTP 401) describe — looks structurally unreachable as things
currently stand, and the buckets it names as examples (`cloudflare:free`, `hyperbolic:free`) are
in practice excluded only via the separate hardcoded `OWNER_EXCLUDED` dict (line 829), not via
this dynamic check.

Separately and regardless of reachability: the match is a bare substring (`code in v`), with no
`\b` word-boundary guard — the exact shape the file elsewhere goes out of its way to avoid
(`_PERMANENT_CODES`, `_TRANSIENT_CODES`, comments at lines 393-395, 569-581 all explain why a
bare `"403" in err` is dangerous, e.g. matching inside `req_4403abc`). If this branch is ever
reconnected to real code-bearing text (e.g. by wiring `is_dead()`'s phrases from
`cascade/engine.py:532-541` into what `prove()` records), it would immediately reintroduce the
false-positive risk the rest of the file was hardened against. Recommend the same `\b` treatment
if/when this path is made live, and in the meantime it is worth confirming with the owner whether
this is known-dormant defense-in-depth or a layer that was expected to be doing work.

### Read, nothing else found

- `_extract_json`, `permanent_refusal`, `named_transient`, `pool_exhausted`, `empty_content`,
  `local_transport`, `record_unrecognised`, `unrecognised_open`, `_bury`/`_clear`/`_alive`,
  `_pace`/`_interval`, `owner_excluded` — all read in full. These are extensively
  self-documented with prior incidents and current tests; the guards described (word boundaries
  on status codes, `local_transport` winning over `permanent_refusal`, `_CLIENT_REJECTION`
  excluding Cloudflare WAF pages, case-preserving `raw` vs case-folded `err`, the `_MULTI_CANDIDATE`
  raw-text-before-unwrap ordering) all check out against the code as written.
- `ask()`'s `got.get("_via")` / `_tried()` guards against a non-dict JSON reply (list/bool/number)
  are correctly applied at both of the two places the docstrings say they were fixed
  (cascade_bridge.py:968, cascade_bridge.py:1315).
- The paid-lane retirement (lines 190-211): grepped the whole file for anything resembling a paid
  bucket predicate or counter — there is none, consistent with the comment's claim.

---

## `derivation.py`

Read in full. This is a self-checking data ledger (594 lines of declared physics/charter/owner/
derived constants plus a graph-integrity checker) rather than runtime safety code. `check_graph()`
correctly detects dangling parents, rootless `DERIVED` entries, unsigned `OWNER` entries, and
cycles (via a proper open/done visited-state DFS, not a naive unbounded recursion — a cycle
terminates via the `"open"` state check at line 459-461 rather than infinite recursion).
`depth()` also terminates safely on a cyclic graph (returns 0 for the back-edge) rather than
recursing forever. `SCAN_MODULES` (line 509) now lists every `.py` file in `src/` dynamically
rather than the stale hand-typed list a prior sweep found — verified this is a plain `os.listdir`
scan, matching the comment.

No defect found. No caps, no discarded verdicts, no reachability problems in the graph checker.

---

## `identity.py`

Read in full. The three structural continuity tests (orthography / population / branching) and
`_is_continuity()`'s n==1 special case were checked against their own worked examples and are
internally consistent. `epoch_of(strict=True)` / `ProbeUnavailable` correctly separates "the
model found no marker" (`""`, a real answer) from "nothing ever asked" (raises), which is the
fix for the "check that cannot fail" bug named in its own docstring.

The mandatory-epoch enforcement (`EPOCH_REQUIRED`, `epoch_directive()`, `epoch_acceptable()`) is
confirmed **in effect**, not just declared: `magnitude.py:926` and `:961` both call
`ID.epoch_acceptable(host, final_epoch)` and `return {..., "status": "DEFERRED", ...}` on failure
— including on the split-retry path, which re-derives and re-validates the epoch rather than
trusting the first draft's validation (magnitude.py:955-966, explicitly commented as a fix for
exactly that gap).

### MINOR — stale cross-module-fix comment

`identity.py:347-349`'s docstring says: *"`strict=True` ... It is an ADDITIVE keyword with the
old behaviour as the default ... `chain.py:422` is the caller that should pass it, and that is
filed as a cross-module change in `handoff/run36/crossmodule_batch04.md` rather than edited here,
because `chain.py` belongs to another agent this shift."* Reading `chain.py` as it stands now
(lines 422-453), **the fix has already landed**: `chain.py:422` calls
`ID.epoch_of(sa, strict=True), ID.epoch_of(sb, strict=True)` inside a `try`, catches
`ID.ProbeUnavailable`, counts `unprobed`, and prints `"NOT ADJUDICATED"` — verbatim matching the
patch proposed in `handoff/run36/crossmodule_batch04.md`. The safety behavior is correct and in
effect; the `identity.py` docstring describing it as still-pending is simply out of date now that
the other half landed. Not a functional defect, but exactly the kind of "note that no longer
matches the code" this sweep is asked to flag, and worth a one-line fix so a future reader doesn't
go looking for an outstanding gap that has already closed.

---

## `context_budget.py`

Read in full (edited earlier today). The token-budget arithmetic (`content_budget_chars()`
returning zero-or-negative rather than clamping, `assert_fits()` raising `ContextOverflow` rather
than degrading, `PROSE_CHARS_PER_TOKEN` vs `CHARS_PER_TOKEN` kept pessimistic relative to their
measured values) is internally consistent and, importantly, **confirmed wired at both call
sites**: `generate.py:133` calls `_CBUD.assert_fits(...)` before dispatch (not decoratively —
`ContextOverflow` is a `RuntimeError` subclass and nothing catches it silently along that path),
and `manifest_builder.py:342-350` sizes `pack_feats`'s budget from
`_CBUD.feats_block_budget(cfg)` and explicitly raises `ContextOverflow` when the computed budget
is `<= 0` rather than packing with a bad number. No discarded verdict, no cap.

No defect found.

---

## `hosts.py`

Read in full. The multi-host registry's `discover()` correctly avoids Hard Rule 0 on the roster
it scores CANDIDATES against ("NO `[:40]`", line 149-152, verified no slice exists on `names`).
The `per_source` bound on speculative candidate subdomains (line 166-167) is explicitly justified
as sitting after the grounded-vs-speculative ordering and only trims unverified guesses, not
known/evidenced hosts — flagging as a **QUESTION** rather than a finding: worth the owner
confirming this reading of Hard Rule 0 (candidate hosts to probe, not a roster of in-fiction
entities) is the intended scope, since the rule's text says "no cap... ever" without an explicit
carve-out for network-probe candidate lists.

### MINOR — docstring claims a return-value distinction that doesn't exist

`add()`'s docstring (hosts.py:87-96) says: *"The verdict is returned, so a caller can tell a
denied write from a duplicate host — both used to be `False`."* But the code returns plain
`False` in **both** cases: the duplicate-host branch (line 84-85, `return False`) and the
denied-write branch (line 94-96, `silence.note(...); return False`) are indistinguishable from
`add()`'s return value alone — the only place the distinction actually surfaces is the
`silence.note("hosts.py:add-denied")` side channel, which a caller checking `if not add(...)`
never sees. In practice this does not cause a safety gap: the only caller, `discover()`
(line 196), just increments a counter on `True` and doesn't need the distinction — a failed write
naturally gets retried on the next `discover()` run since nothing was persisted. But the
docstring's specific claim about what the return value now lets a caller do is not accurate as
written.

---

## `suppressions.py`

Read in full (edited earlier today). This module is tightly built: `_load()` distinguishes
"missing file" (`ok=True`, real zero) from "unreadable file" (`ok=False`) and every caller that
matters (`problems()`) checks `ok` and reports `UNREADABLE` rather than silently treating a
corrupt file as zero problems — this is exactly the "check that cannot fail" pattern the module's
own docstring says it used to have (order 9a18068421c3) and it is now fixed and verified by
reading `_load`/`problems()` together. `add()` fails loudly (`raise IOError`) rather than
returning a falsy value on a denied write, so — unlike `hosts.add()` above — there is no silent
"looks committed but wasn't" path here; the module's own docstring explicitly contrasts this
design choice with a metrics-file writer that is allowed to lose a round silently. `suppressed()`
uses `fnmatch.fnmatchcase` (case-sensitive) rather than `fnmatch.fnmatch`, correctly avoiding the
Windows case-folding widening described in its own comment (verified: both `suppressed()` and
`problems()` use the case-sensitive variant, not just one of them).

No defect found.

---

## `catalog.py`

Read in full. `cmd_search` and `cmd_address`/`cmd_read` operate over the full catalog with no
slicing. `cmd_stats`'s "Populated sources with NO books yet" listing caps its printed lines at
`missing[:30]` (line 64) with an explicit `"... and N more"` follow-up (line 66-67) — an
*announced* truncation of a console report, not a silent one, and the underlying `missing` list
and every other computed count (`len(missing)`, `len(populated)`, etc.) is computed from the full,
unsliced set. Flagging as the same class of **QUESTION** noted under `identity.py` below: Hard
Rule 0 as written draws no line between "roster used by the pipeline" and "top-N lines of a
CLI report," so it's worth the owner confirming whether an announced, count-preserving console
cap like this one is in scope for the rule or not.

No functional defect found.

---

## `identity.py` (cross-reference) — same announced-CLI-cap pattern

Noted here rather than duplicating: `identity.py:main()`'s top-level continuity-inventory printout
(lines 461-466) caps the continuities shown per host at `top[:6]` with a `"+N more"` suffix,
exactly the same shape as `catalog.py`'s `missing[:30]`. Both are diagnostic CLI summaries, not
data consumed by the pipeline (`continuities()` itself, which the pipeline actually calls, returns
the full unsliced dict). Grouping these two together as one **QUESTION** for the owner: is an
announced, non-silent CLI-report truncation acceptable under Hard Rule 0, or should even a labeled
"+N more" be treated as the same violation a silent `[:N]` would be?

---

## `lognames.py`

Read in full (36 lines). The module itself is correct and minimal. But its own stated purpose —
*"A constant shared by writer and reader cannot drift"*, written specifically because
`overnight.py` and `dashboard.py` used to duplicate these filenames as independent string
literals — **is not fully honored by the rest of the tree today**, for 2 of its 6 names:

### MAJOR — `PIPELINE` and `RECATALOGUE` are still hardcoded as bare string literals at their
   write sites, defeating the single-source-of-truth guarantee for those two jobs

- `overnight.py:605` — `("pipeline", [os.path.join(SRC, "pipeline.py")], "pipeline_auto.log")`
- `overnight.py:1024` — `start("pipeline", [os.path.join(SRC, "pipeline.py")], "pipeline_auto.log")`
- `overnight.py:1075` — `"pipeline_auto.log", timeout_h=2))`
- `foreman.py:822` — `"recatalogue.log")` (inside the `ON.start("catalogue gap", ...)` call)

None of these four sites import or reference `lognames.PIPELINE` / `lognames.RECATALOGUE` — they
spell the filename out directly, exactly the pattern `lognames.py`'s own docstring names as the
original bug ("used to be string literals repeated in overnight.py and dashboard.py
independently — one rename in one place and the whole observability chain went quietly blind").
By contrast, `overnight.py` correctly uses `LN.ROLL` / `LN.READ` (verified at
`overnight.py:1042,1054`) and `foreman.py` correctly uses `LN.SWEEP` / `LN.CALIBRATE` (verified at
`foreman.py:837,894`) for the other four names — so the regression is specific to `PIPELINE` and
`RECATALOGUE`.

Today these four literals happen to still match `lognames.PIPELINE`/`lognames.RECATALOGUE`
exactly, so nothing is currently broken. But the READER side for these two names is generic —
`standards.py:1264` (`for fn, owner in sorted(LN.OWNER.items())`) and `foreman.py:472`
(`owners = {fn[:-4]: frag for fn, frag in _LN.OWNER.items()}`) both derive the expected filename
from `lognames.OWNER`, not from a literal — so if `PIPELINE` or `RECATALOGUE` were ever renamed in
`lognames.py` (the module whose entire purpose is to make that rename safe), the reader side would
follow the new name automatically while these four writer call sites would keep writing the OLD
filename. That reproduces the exact "quietly blind" failure mode `lognames.py` exists to prevent,
just with the drift direction reversed (stale writer instead of stale reader) and confined to
these two jobs. Recommend `overnight.py` and `foreman.py` import `lognames` and use
`LN.PIPELINE`/`LN.RECATALOGUE` at these four sites — this is a cross-module fix (touches files
outside this batch), so filed here rather than edited.

---

## Modules I could NOT read, or could not fully verify

None — all nine modules in the batch list were read in full. Where a finding depended on external
(non-`src/`) code (`C:\Users\imarl\cascade\cascade\router.py` and `engine.py`, for the
`cascade_bridge.py` findings above), that code was read directly rather than inferred, and cross-
checked against the live `data/POOL_PROOF.json` on disk.
