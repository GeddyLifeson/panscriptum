# sweep64 batch 08 — audit report

Scope (every line read start to finish, via the Read tool in chunks, no grep-sampling):

- src/cascade_bridge.py    2333 lines
- src/sweep_plan.py        1150 lines
- src/rosetta.py            815 lines
- src/runguard.py           660 lines
- src/catalogue_codex.py    515 lines
- src/sevenfold.py          441 lines
- src/resync_roll.py        332 lines
- src/tells.py              303 lines

Total 6,549 lines, all eight modules read completely. Read-only throughout: nothing under
`src/`, `data/`, or `state/` was edited, and no drill/verify_math/generate/pipeline/publish/
runguard --claim run. The only actions taken beyond reading were writing this report and the
mandated `sweep_plan.record()` call.

## Method

CLAUDE.md was read first (Hard Rule -1 escalation chain, Hard Rule 0 no-caps, fail-closed
doctrine, "a check that cannot fail looks exactly like a check that passed"). Then
`handoff/sweep63/` was grepped for these eight module names and every matching report read in
full before starting: `AUDIT_batch08.md` (cascade_bridge, sweep_plan, rosetta, runguard,
catalogue_codex — 0 VERIFIED/SUSPECTED), `AUDIT_batch04.md` (sevenfold.py — 0 VERIFIED/
SUSPECTED), `AUDIT_batch09.md` (resync_roll.py — 0 new, one QUESTION about the closing
summary line reading the in-memory roll rather than the post-CAS disk state), `AUDIT_batch14.md`
(tells.py — 0 VERIFIED/SUSPECTED). All eight files were re-read from scratch against the current
source rather than assuming the prior verdict still holds, per the brief.

Given the brief's specific steer toward cascade_bridge's failure attribution (live standards
showing "calls that succeed" around a quarter, and Groq refusing on output-token limits), that
module's classifier chain (`permanent_refusal`, `named_transient`, `_size_refusal_permanent`,
`pool_exhausted`, `record_unrecognised`, and the metrics line in `ask()`) got the closest
line-by-line tracing, cross-checked against `verify_math.py`'s own AST-level assertions about it
(section around line 6030-6090) and against `state/POOL_PROOF.json`/ledger-shape comments in the
source.

## Findings

### 1. VERIFIED — `cascade_bridge.py:1469-1470`, `ask()`: a successful call whose parsed reply is
not a `dict` is metered using the FAILURE-attribution format, mislabelling a success as if it
were an unattributed failed attempt.

```python
"model": ((got.get("_via") or "") if isinstance(got, dict)
          else ("tried:" + ",".join(_tried()) if _tried() else "")),
```

`_ask_call` returns `None` on every failure path. On success it returns whatever
`_extract_json` parsed — and the module's own docstring says plainly that this can be a
non-`dict` value: *"`_extract_json` will happily return a list, bool or number from a fenced
reply, `_ask_call` only tags `_via` when the payload is a dict... so a provider answering
` ```json\n[1,2]\n``` ` crashed the metrics line with AttributeError and took the whole call with
it"* (lines 1450-1454). That comment documents a real, previously-crashing case, so a successful
non-dict reply is not hypothetical here.

The `isinstance(got, dict)` test is being used as a *proxy* for "did the call fail", but it is
not equivalent to it: `got` is non-`dict` in two different circumstances — failure (`got is
None`) and success-with-a-non-object-payload (`got` is a list/bool/number). The code only
distinguishes dict vs. not-dict, so both land in the `else` branch and both get the string
`"tried:" + ",".join(_tried())`.

That string is not a neutral fallback — it is the format the surrounding comment (lines
1456-1468) and `verify_math.py`'s own commentary at line 6054 (*"failures now record
`tried:<buckets>` so a failed row says which providers spent the deadline"*) both assert is
reserved for a **failed** call, specifically so a reader can tell which bucket burned a claim
without an answer. `verify_math.py`'s AST check (`_dict_guarded`, lines 6076-6087) only verifies
that every `.get("_via")` sits inside an `isinstance(_, dict)` guard — it does not check that the
`else` branch is failure-only, so it cannot see this gap.

**Failure scenario:** a cloud provider (any of the ~26 non-schema-constrained buckets this file
routes to — this is explicitly a cloud-only risk, since the local Ollama path uses `format` to
constrain generation) answers a schema-requesting call with well-formed JSON that is not an
object, e.g. a bare fenced array. `_extract_json` parses it and returns the list; `_ask_call`
takes the success path (`_clear(pinned.bucket)` is called, the unparseable-strikes counter is
reset, no bench, no `record_unrecognised`) and returns the list to `ask()`. The metric row
written to `state/model_metrics.jsonl` then reads `"ok": true` together with
`"model": "tried:<bucket>"` — a shape that, by the codebase's own stated convention, means "this
bucket was tried and did not answer." A caller or maintenance script that recovers the serving
bucket from `model_metrics.jsonl`'s `model` field (as opposed to Cascade's own separate
`usage` table, which `dashboard.throughput()`/the "calls that succeed" standard actually reads,
and which this bug does not touch) would misclassify a real success as an unattributed failure
for that bucket, and the identity of which bucket actually served the successful non-dict reply
is discarded rather than recorded.

**Scope check, so this is not overstated:** the live "calls that succeed" standard in
`standards.py` (~line 876-894, "26% ok of 46"-shaped output) reads `errs = calls - ok` from
Cascade's own `state/cascade_scratch.db` `usage` table (`dashboard.throughput()`,
`src/dashboard.py:174-204`), which is populated by the Cascade engine itself, not by this
function. So this specific bug does **not** explain the measured 26% figure — that number is
governed by the engine's own outcome recording and by which buckets keep getting reclaimed (see
Question 1 below). This bug is a real, independent defect in `cascade_bridge.py`'s own
`model_metrics.jsonl` instrumentation, verified by tracing `_ask_call`'s return paths and
`ask()`'s consumption of them, not by assumption.

No other new VERIFIED or SUSPECTED findings survived tracing in this batch.

## Checked specifically and ruled sound (not re-filed)

- **`cascade_bridge._size_refusal_permanent` / `named_transient` / the Groq OTPM guard**
  (`_SIZE_REFUSAL`, lines 597-654) — traced the regex against the exact Groq wording quoted in
  the comment (`"...Limit 1000, Requested 1045..."`) by hand: the lazy `.*?` correctly lands on
  the first `limit <digits>` occurrence (before the later "enforced limit" phrase), the
  Limit/Requested pair is extracted correctly, and `1045 > 1000` correctly yields `True`. Traced
  forward into `_ask_call`'s failure branch: a proven size refusal skips both `permanent_refusal`
  and `named_transient`, falls through to `record_unrecognised`, and is never benched. This
  matches the comment's own admission that the full remedy ("give the router a per-bucket output
  ceiling and stop retrying a request whose Requested figure cannot shrink") is explicitly
  out of scope for this file and left as `NEXT_STEPS`-level future work. Not a defect against the
  code's own stated design — see Question 1.
- **`cascade_bridge.permanent_refusal` / `client_rejection` / `local_transport`** — re-verified
  the ordering (`local_transport` first, then `client_rejection`, then the code/word scan) and
  that `_PERMANENT_CODES` (401/402 only, word-boundaried) and `_WAF_COMPANION_WORDS` correctly
  require co-occurrence with "cloudflare" rather than a bare provider-name match, per order
  62f4b7caae73. Matches documentation.
- **`cascade_bridge.dead_forever` / the PROOF_TTL memo** — re-traced the `_PROVEN[0]` cache
  keyed on `(mtime, out)` plus a `PROOF_TTL` staleness check ahead of the memo hit; both the
  identity (mtime) and freshness (TTL) tests are applied before returning the cached set, matching
  the two-part fix the comment describes.
- **`cascade_bridge._ask_call`'s widen-fallback rotation** (`_WIDEN_RR`, lines 1618-1633) —
  confirmed the rotation offset is applied to `ranked` before the stable re-sort on
  `(bucket not in answering)`, so the rotation survives the re-sort within each of the two
  groups, matching the comment's claim.
- **`cascade_bridge.record_unrecognised`'s compare-and-swap** (lines 1109-1183) — traced the
  digest-before-read ordering, the 12-attempt jittered backoff, and the `_row_survived` readback;
  matches its extensive in-line history.
- **`sweep_plan.normalise_module` / `record` / the shard-based coverage model** — traced
  `known_modules()` → `normalise_module()` → `record()`'s accept/unknown split, and
  `covered_by()`'s per-run shard scan (deliberately not `coverage_map()`, which is newest-wins
  across runs). Matches the docstrings' claims about why each choice was made.
- **`sweep_plan.missing_detail`'s `roster`/`undetermined` handling** — confirmed `roster_of`
  returns `None` (not an empty set) when no shard for a run carries a `roster` field, and that
  `missing_detail` routes that case to `undetermined` rather than inferring from mtimes — matches
  the "unfalsifiable in the direction that matters" argument in the docstring.
- **`rosetta.numeric_rows` / `stand_rows` / `ordinal_rows`** — the row-vs-window parsing split,
  the `_STAND` labelled-parameter-block matching with the `STAND_MIN_PARAMS` floor, and the
  case-preserving-offset fix in `ordinal_rows` (matching on the original text, never a lowercased
  copy) all read as documented and traced against their own worked examples in the comments.
- **`rosetta.assays_by_host` / `check()`'s per-host scoping** — confirmed `k.partition("|")`'s
  is used with the `if sep else` fallback so a bare key files under the empty host rather than
  being mis-split, and that `check()` only ever matches a scale row against an assay from the
  *same* host when `by_host` is supplied.
- **`runguard.holder_is_live` / `guard_fault`'s asymmetric pid-identity check** — re-verified the
  "stale-but-alive" arm requires a live pid AND a matching `pid_started` before it will treat a
  stale heartbeat as still-live, and that the mirror "fresh heartbeat, pid gone" arm was
  deliberately not implemented (an ephemeral per-invocation `python.exe` pid dying seconds after
  a claim is the *normal* case for this guard's actual holder, a long-running Claude session).
  Matches the docstring's measured justification (pid 26924 example) and the owner-ruled
  fail-open-and-escalate behaviour in `claim()` on a corrupt guard (order 70f66fbd98aa).
- **`catalogue_codex.parse_codex` / the manifest-count cross-check, and the four uncapped
  collision reports** (`norm_clashes`, `ambiguous`, `reg_ambiguous`, `dupe_elements`,
  `unmapped_types`) — all five are printed in full with no truncation, and each is reported
  *before* the write summary as the code's own comments promise.
- **`sevenfold.shelve` / `seams()`'s window-plus-weaker-half-of-joins cut selection** — traced
  `_even_cuts` and the two-rule interaction (candidates restricted to at-or-below-median seams,
  then the window search around each even boundary) against the docstring's own measured
  before/after table (top branches 1-98 → 15-45, largest address 41 → 5). The construction
  matches what is claimed.
- **`resync_roll.py`'s status-relabelling rule and the owner-exclusion guard** — confirmed the
  status repair now runs unconditionally per matched row rather than only inside the
  `entry_count changed` branch (order 2ab24aeb63f7), and that `_roll.OUT_OF_SCOPE` rows are never
  relabelled by `_apply`'s bare `!=` guard, both in the resync loop and in the CAS `_apply`
  closure passed to `roll.mutate`.
- **`tells.py`'s asymmetric STRUCTURAL patterns and the `_SENTENCE_START` anchor fix** — the
  "not merely/not simply/not just...but" asymmetry, the "X, Y and Z alike" closing-word
  requirement, and the `^\s*` vs. mid-sentence anchor splice (`_anchor()`) were all traced and
  confirmed present as documented; `prompt_in_sync()` is wired via a real caller path
  (`--check` in `__main__`), not dead code.

## Questions

1. **`cascade_bridge.py`, the Groq OTPM/output-token-limit size refusal** (see
   `_SIZE_REFUSAL`/`_size_refusal_permanent`, lines 597-654) — by design, a proven per-request
   size refusal is neither benched nor treated as permanent; it is recorded once per distinct
   error text under `record_unrecognised` and the bucket stays fully eligible for the very next
   claim. Since nothing in `src/` sets `max_tokens` (the comment says so explicitly), the
   "Requested" figure that exceeds the provider's limit cannot shrink on a retry, so a bucket
   whose typical output for this pool's prompts exceeds its OTPM ceiling will fail this way on
   every claim, indefinitely, at whatever rate `_pace()` allows for that bucket — with no cooldown
   penalizing it the way a plain 429 would. This is explicitly named in the source as real
   remaining work deferred to a future "the router learns per-bucket output ceilings" order, not
   something this file's owners consider settled — flagging it as a QUESTION worth revisiting
   given the brief's own context that live success rates are currently low, since a bucket stuck
   in this state consumes claims and pacing slots at full rate for zero chance of success until
   that future work lands.
2. **`resync_roll.py`'s closing "roll now: X/Y sources catalogued" line** (main(), near the end)
   sums over the local in-process `roll` list rather than the post-`_roll.mutate()` disk state.
   Already raised as Question 1 in `handoff/sweep63/AUDIT_batch09.md` and unchanged since; not
   re-filed as a new finding, restated here only so this batch's coverage record does not read as
   having missed it.

## Coverage recorded

Recorded via `sweep_plan.record('run64', [...], batch=8)` for the eight modules above.
