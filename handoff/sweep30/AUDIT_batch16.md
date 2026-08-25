# AUDIT batch16 — sweep30

Files: `src/drill.py` `src/wiki_source.py` `src/identity.py` `src/ingest_doc.py` `src/tuning.py`
`src/style_audit.py` `src/resonance.py`

Method: every line of every file read top to bottom. Every claim below marked REPRODUCED was
verified by running real code against a scratch temp dir or, where noted, read-only against the
real repo/corpus (never written to). Everything else is marked HYPOTHESIS.

**COMMITTED SECRETS: none found.** Grepped all seven files for key/token/secret/password
patterns. The only hits are `drill.py`'s own synthetic test fixtures (`an AWS example access-key id` is  <!-- SECRET-FIXTURE: quoted example, not a credential -->
AWS's own published example key, never valid; the Slack/Stripe/JWT/PEM/bearer/DB-URL/GitHub
strings are hand-built fakes used to test the redaction scrubber) and unrelated uses of the
word "token" (text tokens, worksheet tokens). Nothing live.

---

## 1. `src/wiki_source.py` — clean, one KNOWN item reconfirmed

**F1. [HIGH] [REPRODUCED, KNOWN — reconfirmed against current source] `category_members()`
(:549-573) returns a PARTIAL roster on any exception, indistinguishable from a complete one.**

```python
def category_members(subdomain, category, limit=None):
    out, cont = [], None
    while limit is None or len(out) < limit:
        ...
        try:
            d = _api(subdomain, p)
        except Exception:
            silence.note("wiki_source.py:376")
            break                                    # <-- exits the pagination walk
        out += [m["title"] for m in d.get("query", {}).get("categorymembers", [])]
        cont = d.get("continue", {}).get("cmcontinue")
        if not cont:
            break
    return out                                        # <-- no signal of partial vs complete
```

Confirmed by reading: on ANY exception mid-walk (timeout, malformed JSON, HTTP error not already
retried inside `_get`), the loop `break`s and the function returns whatever `out` has accumulated
so far — with the exact same shape as a genuinely-exhausted, complete `cmcontinue` walk. The
caller (`catalogue_web.py:100,205`, both call with `limit=None`) has no way to tell "got all
33,614 titles" from "got the first 6,000 and then Fandom hiccupped."

This is the single most-repeated open finding in the ledger (present in sweeps 22, 23, 25, 26,
27, 28, 29 handoffs) and it is still open in the current source. Contrast with `all_categories()`
in the SAME FILE (:352-406), which was fixed for exactly this shape: it tracks a `complete` flag
and refuses to cache a partial walk. `category_members()` has no equivalent flag at all — not
even for its own return value, let alone a cache.

**Why it matters:** this is the leading candidate explanation for "every source is fully
catalogued" sitting at ~20% overall with DC specifically at 0.5% (per NEXT_STEPS/HANDOFF): DC's
Characters category alone is 33,614 titles across ~68 pages of `cmcontinue` pagination, and Fandom
serving one transient error anywhere in that walk silently truncates the roster with no record of
where it stopped.

**What a completeness flag needs:** `category_members()` should return `(titles, complete: bool)`
(matching `all_categories()`'s internal pattern), and every caller (`catalogue_web.py:100,205`,
and any future caller) needs to treat `complete=False` as "do not record this source as
catalogued" — propagated up to whatever writes `COVERAGE.json`/`SWEEP_ROLL.json` so a partial
pull cannot be reported as a finished one. A retry-with-backoff on the specific failing
`cmcontinue` token (rather than abandoning the whole walk) would also directly address the root
cause rather than just labelling the symptom.

**Suggested fix:** mirror `all_categories()`'s `complete` tracking; have callers refuse to mark a
source `catalogued` when `complete=False`.

Everything else in `wiki_source.py` reads clean: `resolve_wiki()`'s host-map-first logic, the
`WIKI_OVERRIDES`/`COMPOSITE_SOURCES` tables, `verify_wiki_matches()`'s distinctive-word check,
`_META_CATEGORY` meta-category exclusion, `all_categories()`'s hard-stop removal and
never-cache-a-failure fix, `find_categories()`'s uncapped `limit=None` default, `page_text()`'s
continue-not-return fix across the three section tries, `rank_by_size()`'s uncapped ranking, and
`clean_titles()` all match their own extensive inline commentary and the fixes those comments
describe. No Hard-Rule-0 caps found (every `limit`/`top`/`hard_stop` defaults to `None` and no
caller in this file passes a non-None value).

---

## 2. `src/identity.py` — one KNOWN docstring/code contradiction reconfirmed, one carried-forward hazard

**F2. [HIGH] [REPRODUCED, KNOWN — reconfirmed] `_is_continuity()` (:180-207) can never classify a
single-bearer branching continuity as a continuity — directly contradicting the function's own
worked example.**

```python
def _is_continuity(desig, stat):
    ...
    n = stat["bearers"] ...
    shared = stat.get("shared", 0) ...
    if n >= MIN_BEARERS:        # MIN_BEARERS = 3
        return True
    return n >= 2 and shared >= max(2, 0.5 * n)
```

The docstring states: *"(Fates) has one bearer and is obviously a continuity because that bearer
exists in three other branches. Either [population or branching] alone admits it."* Reproduced
directly:

```
Fates (1 bearer, shared with other branches) -> False
Revelation (3 bearers, 0 shared) -> True
two bearers, both shared -> True
```

For `n == 1`, the first branch is False (`1 >= 3`) and the second branch's own `n >= 2` guard is
also unconditionally False, so `_is_continuity` returns `False` no matter how large `shared` is.
The function's own documented example is therefore impossible to satisfy through this code path.
A genuine one-character young continuity whose sole bearer is shared with several other branches
— exactly the "branching" case the docstring introduces — is silently merged into the main
timeline instead of split, which is the specific, non-recoverable error class this whole module
(`identity.py`) exists to prevent (per its own MIN_BEARERS comment: "the cost of the opposite
mistake is only that two records stay separate that could have been one, which is recoverable; a
wrong merge is not").

Already flagged in sweep28's `AUDIT_batch14.md` as HIGH/STILL OPEN; still open in current source.

**Suggested fix:** drop the `n >= 2` guard on the branching path, or explicitly special-case
`n == 1 and shared >= 1` (a single bearer that is ITSELF shared with another designator is
sufficient evidence per the docstring's own reasoning).

**F3. [MEDIUM] [REPRODUCED, carried forward from sweep28] `load()`'s cache write (:218-222) uses a
fixed temp filename.**

```python
tmp = CACHE + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(inv, f, indent=1, sort_keys=True)
silence.replace_retry(tmp, CACHE)
```

`silence.replace_retry` handles the Windows "rename denied while a reader holds the target" case
correctly (verified by reading `silence.py:263-280`), but it does nothing for two writers racing
to *write* the same `DESIGNATORS.json.tmp` path concurrently — e.g. two `python src/identity.py
--refresh` invocations, or a `load(refresh=True)` call overlapping another process's. Whichever
process's `open(tmp, "w")` / `json.dump` interleaving finishes last wins, and the other's work is
silently discarded (not detected, not logged — no exception is raised by this path). This is the
same two-writer hazard shape flagged project-wide elsewhere (per project memory). Low real-world
likelihood (this cache is refreshed rarely, by hand or by an infrequent sweep step) but the
pattern is the one the project has been burned by before.

**Suggested fix:** use a PID/thread-unique tmp name (`CACHE + f".tmp.{os.getpid()}"`) as every
other atomic writer in the codebase already does (see `pipeline.py`'s `tmp = path + ".tmp"` sites,
which are all single-writer-per-path by construction; `identity.py` is the one that is not).

Everything else in `identity.py` is clean: `split()`, `mine()` (genuinely uncapped — "every title
present -- no sampling," verified true by reading: plain `os.listdir`/`glob` with no limit),
`continuities()`, `identify()`, `node()`, the epoch-on-demand machinery (`_ask`/`_json`/
`epoch_of`), and the `EPOCH_REQUIRED`/`epoch_directive`/`epoch_acceptable` mtg/D&D-specific block
all match their documented behaviour. The `_BAD_CHARS` self-check at the top (an anti-corruption
sanity check on the file's own bytes) is intentional leftover infrastructure, not a bug.

---

## 3. `src/ingest_doc.py` — clean

No correctness bugs, no swallowed failures of consequence, no Hard-Rule-0 caps (the whole
document is extracted page-by-page with no limit; `mine()` chunks and mines every chunk, no
sampling), and no secrets. The two-writer handling (`write_record_catalogue` vs `write_record`,
and the "rewind `known`, don't advance the cursor, on a denied write" logic at :244-251) was
cross-checked against `pipeline.write_record_catalogue` (:412-465) and matches its documented
behaviour exactly — the claims in `ingest_doc.py`'s own comments about that function's return
semantics (`_landed`, merge direction) are accurate.

Two minor, non-blocking observations, LOW severity:

- `record_path()` (:116-126) falls back to a substring-containment scan over
  `os.listdir(RECORDS)` when no exact slug match exists. Pre-existing design tradeoff (not new to
  this pass) — two record filenames with overlapping substrings could theoretically match the
  wrong file. Worth a note, not urgent.
- `mine()`'s chunker (:164-172) only checks `len(cur) + len(pages[label]) > CHUNK` when `cur` is
  already non-empty, so a single oversized page becomes its own chunk with no upper bound. This is
  the *correct* Hard-Rule-0 behaviour (no truncation), but an unusually large single page could in
  principle produce a chunk that overflows the local model's context window, degrading (not
  losing) that page's extraction quality. Not observed in practice; flagged for awareness only.

---

## 4. `src/tuning.py` — one new HIGH finding, one cross-file characterisation as requested

**F4. [HIGH] [REPRODUCED] `regime()` (:188-212) silently skips the success-rate requirement
whenever `judged` is False, contradicting its own docstring, and reintroduces the exact
reachability-vs-capacity bug this file's own comments say it fixed.**

```python
judged = rate is not None and calls >= MIN_CALLS_TO_JUDGE     # MIN_CALLS_TO_JUDGE = 20
...
if n >= CLOUD_MIN_BUCKETS and (not judged or rate >= CLOUD_MIN_SUCCESS):
    r = "cloud"
```

The docstring says unconditionally: *"'Cloud' now means answering AND succeeding — see
CLOUD_MIN_SUCCESS. Reachability was never the question the callers of this function are asking."*
The code only enforces "succeeding" when `judged` is True. Reproduced directly:

```
regime with NO success-rate evidence, 3 buckets answering            -> cloud
regime with 4% measured success over 25 calls, 3 buckets answering   -> local
```

`judged` is False whenever fewer than 20 calls have landed in `state/cascade_scratch.db`'s
`usage` table in the trailing 15 minutes — which happens at the start of any run, after any quiet
stretch, or on ANY failure to read the DB at all (`cloud_success_rate()`'s `except Exception:
return None, 0` at :183-185 also produces `judged=False` — a corrupt/locked DB file gets the exact
same silent fail-OPEN treatment as "no evidence yet"). In every one of those cases `regime()`
reverts to certifying "cloud" purely off proof-of-reachability (`_answering_buckets()`), which is
precisely the failure this file's own header names as "this project's most-repeated defect": a
bucket answering a proof call certifies REACHABILITY, not CAPACITY. The file's own cited incident
(2026-08-24: regime read "cloud" off 4 answering buckets while live success was 4%, and 1,168 of
1,235 chunks were thrown away) is only prevented here because that incident happened to have
`judged=True` (enough calls had already failed to be counted) — the fix as written does not
generalise to the "before enough evidence has accumulated" window, which is exactly when a
degrading pool is first turning bad.

This also compounds directly with the already-tracked `BUGS.md` M19 self-feeding loop ("a narrow
gate makes few calls, few calls make a small noisy sample, and a bad sample keeps the gate
narrow") — a narrow local gate producing few calls is one more way `calls < 20` and `judged=False`
comes about, at exactly the moment the pool's health is least certain.

Also worth flagging under HARD RULE -1's own FAIL CLOSED doctrine (CLAUDE.md): "every layer
answers 'I don't know' with STOP." `judged=False` is a textbook "I don't know" state, and this
code answers it by trusting reachability rather than refusing to widen.

**Suggested fix:** when `judged` is False, do not let bucket-count alone certify "cloud" at full
strength — either treat `not judged` as a vote for `starved`/`local` (fail closed, consistent with
the rest of the file's stated philosophy), or keep "cloud" but clamp `profile()`'s worker count to
a conservative floor until real evidence accumulates, rather than the full `max(4, min(16, n+2))`.

**Characterisation of `GATE_LOCAL_N`/`GATE_CLOUD_N` and the `regime()`/`profile()`/worker-count
interaction, as requested.** These constants live in `read.py`, not in this batch's files, and the
mechanism is already tracked as `BUGS.md` M19 ("THE READER THROTTLES THE WHOLE POOL THROUGH THE
GPU CARD'S SEMAPHORE"). Summarised for this audit's purposes: `tuning.profile()`'s reported
`workers` count is advisory only — the actual concurrency ceiling for any call routed while
`regime()` reads anything other than `"cloud"` is enforced separately, by `read._ask` acquiring
`read._gate()`, which selects `_GATE_LOCAL` (width `GATE_LOCAL_N` = the GPU card's own
`OLLAMA_NUM_PARALLEL`, measured at 2 on this machine) rather than `_GATE_CLOUD_N` (16) — and that
gate wraps the ENTIRE transport ladder, including the cloud attempt, not just the local model
call. So a "HIGH" job asking for e.g. 16 workers, while `regime()` reads `local`, is in practice
throttled to at most 2 concurrent calls of ANY kind regardless of what `tuning.profile()` reports
— matching BUGS.md's measured example ("the reader's gate is open: local, 1 of 16 permits").
`BUGS.md` records this as awaiting an explicit owner ruling (acquiring the local gate only around
the local call would change concurrency against both a shared GPU and a free-tier pool
simultaneously) rather than a code bug in `tuning.py` itself — `tuning.py`'s part of the contract
(computing the regime and a recommended worker count) is doing what it says; the gap is that
`read.py` does not consult `tuning.profile()`'s worker count when sizing its own semaphore, it
derives its gate width independently. Not re-litigated further here since `read.py` is outside
this batch.

`CLOUD_MIN_BUCKETS`, `PROOF_STALE_SECONDS`, `MIN_CALLS_TO_JUDGE`, the `workers()` zero-vs-None
contract (verified correct: `requested=0` returns `0`, matching the "ZERO IS A REQUEST" fix
described in its own docstring and pinned by `verify_math` S19ac) are all otherwise sound.

---

## 5. `src/style_audit.py` — one KNOWN item reconfirmed with exact figures, one new hypothesis

**F5. [HIGH] [REPRODUCED, KNOWN — reconfirmed with exact current-corpus figures] `record_of()`
(:48-51) matches its "The Record." marker in only 8 of 1,278 entries (0.6%) across the real
generated corpus, so 99.4% of entries are audited as their WHOLE block rather than isolated
narrative prose.**

```python
def record_of(entry):
    m = re.search(r"The Record\.?\s*(.+?)(?=\n\s*(?:Contradictions|Marginalia|▣|⌁)|\Z)",
                  entry, re.S)
    return (m.group(1) if m else entry).strip()
```

Measured against every withdrawn generated file in `output/withdrawn_2026-08-25/raw/*.md` (148
files, the real, complete population of what this project has actually generated — read-only,
nothing modified):

```
files: 148
total entries: 1278
entries where "The Record" regex actually matched: 8      (0.6%)
files with at least one matching entry: 5 of 148
```

(The KNOWN-item briefing's "3 of 144 real generated files" was evidently measured file-level on
an earlier snapshot; the current, entry-level figure is worse still — 8 of 1,278.) Reading the
actual entries confirms why: the real template almost never emits the literal "The Record."
header before its narrative paragraph — the model goes straight from the
`Shelfmark:`/`Class:`/`Magnitude:`/`Attestation:` block into prose. When the regex fails to match,
`record_of()` falls back to `entry` — the FULL per-entity chunk, header fields, prose,
`Contradictions:`, and the four `Marginalia:` hand-voice lines (AVAR/QUILL/MOTH/UNNAMED),
included and unseparated.

**Why it matters:** every measurement this module reports — `OPENERS` (first 4 words), `shapes`
(opener grammar), `banned` (Ground Rule 6 construction counts), `em_per_entry`, `turn_rate`, and
`vocab` — is computed over that oversized, wrong-content blob for 99.4% of real entries. Openers
in particular are measured from the ENTITY NAME LINE (immediately after the `◈` marker) rather
than from the prose's actual opening words, since nothing strips the header before the fallback
text is handed to `opener()`/`opener_shape()`. The tool's stated purpose — "OPENERS how many
Records begin the same way" — is not being measured for nearly the entire corpus it has ever been
run against.

**F6. [MEDIUM] [HYPOTHESIS — directional evidence only, not an exact figure] `TURN_ENDING`'s
`re.M` `$` anchor (:38-39), combined with F5's oversized fallback text, plausibly inflates
`turn_rate` by matching turn-endings inside Marginalia/Contradictions text rather than the
Record's own final sentence.**

```python
TURN_ENDING = re.compile(
    r"(?:\.|\?)\s+(?:And|But|Yet|Still|Which|That)\b[^.]{0,80}\.\s*$", re.M)
```

With `re.M`, `$` matches at the end of every LINE within the (oversized) text, not just the end of
the whole string — so a `turns += 1` fires if ANY line anywhere in the header+prose+
Contradictions+Marginalia blob happens to end on a turn construction, including inside a
Marginalia hand's own commentary (which, being separately model-generated prose, is itself
susceptible to the same rhetorical tic Ground Rule 6 is policing). I built a rough corrected
`record_of()` (stripping header-field lines, no literal-marker requirement) purely to demonstrate
directionality — **explicitly not proposed as the real fix**, since it silently produced empty
bodies for ~88% of entries whose header formatting didn't match my regex (e.g. the corpus also
contains `Attest, Transcribed` instead of `Attestation: Transcribed` in at least one file) and so
undercounts on its own:

```
AS SHIPPED   turn_rate=4.3%  (55/1278)   em_per_entry=2.52
PROSE-ONLY*  turn_rate=0.0%  (0/156)     em_per_entry=0.08     (*crude patch, 1122 entries lost to non-matching headers)
```

The magnitude of the swing (4.3% -> 0%, 2.52 -> 0.08 em-dashes/entry) is large enough that the
direction of the claim (inflation, not just noise) is well supported, but the exact "true" figures
need a properly-designed extractor, not this one-off patch — hence HYPOTHESIS, not REPRODUCED, for
the precise numbers.

**Suggested fix for both F5 and F6:** stop gating `record_of()` on the literal "The Record."
string. The reliable, always-present boundary is the LAST header-field line
(`Shelfmark:`/`Class:`/`Magnitude:`/`Attestation:`, in whatever order/spelling variant the model
actually emitted) through the next `Contradictions:`/`Marginalia:`/`▣`/`⌁` boundary — a fix needs
to handle the header-line variants actually present in the corpus (my throwaway patch did not),
not just the "The Record." literal.

Everything else in `style_audit.py` is clean: `entries()`'s `◈` split, `opener_shape()`'s
NAME-collapsing fix (verified against its own documented false-positive story), the `FUNCTION`/
`TEMPLATE_WORDS` sets, `audit()`'s per-Counter aggregation (uncapped — the underlying `Counter`s
hold every distinct value seen; only `report()`'s `most_common(top=8/10/14)` calls are
display-only truncation of an already-complete count, consistent with prior sweeps' judgment on
console-example caps — not a Hard-Rule-0 violation), and the `--self-test` fixture (verified it
does catch an obviously repetitive synthetic corpus).

---

## 6. `src/resonance.py` — both KNOWN items confirmed, with exact evidence

**F7. [HIGH] [REPRODUCED] `resonance.py` is imported nowhere in `src/`.**

```
$ grep -rn "import resonance\|from resonance" src/*.py
(no matches outside resonance.py itself)
```

The only references to `resonance.` anywhere in `src/` are inside COMMENTS (not code) in
`cosmology_graph.py:90,144`, `custodes.py:297`, and `weave.py:471,478` — none of them an actual
`import` statement. Confirmed independently by `liveness.py`'s own AST-based dead-code scan (which
only sees real code, not comments): all three of `resonance.py`'s top-level functions are flagged
DEAD —

```
resonance.py:109 incomparability_rate()
resonance.py:133 resonance_strength()
resonance.py:50  hodge_decompose()
```

— and these 3 are already counted inside `drill.py`'s `LIVENESS_CEILING=38` (see drill.py section
below), so the ratchet is not blind to this; the module being fully orphaned is simply not
surfaced as its OWN finding anywhere else in the ledger's language until now.

**F8. [HIGH] [REPRODUCED] `resonance_strength()`'s default `graph_path` (:141) points at the
WRONG graph file — the old, separately-maintained `SHARED_STAGE_GRAPH.json`, not the real
pipeline's `RESONANCE_GRAPH.json`.**

```python
path = graph_path or os.path.join(HERE, "data/SHARED_STAGE_GRAPH.json")
```

`data/SHARED_STAGE_GRAPH.json` is written by the separate, standalone `cosmology_graph.py --write`
tool (`cosmology_graph.py:55`) and read live by `propagation.py` (`propagation.py:46`). It is
NOT the same file as `data/RESONANCE_GRAPH.json`, which is what `pipeline.py`'s real production
"phase 3 weave" step actually writes (`pipeline.py:1850`) — built via `weave.resonance_graph()`
with a permutation-test null threshold (`W.null_threshold_surprisal(..., trials=12)`), topology
analysis (diameter, six-degrees), and explicitly documented in `pipeline.py`'s own docstring as
*"RESONANCE permissive. Drives X.7 propagation."* — the methodologically-real, statistically
filtered resonance graph the module's own name and purpose describe. Confirmed both files
currently exist on disk with different sizes/timestamps (`SHARED_STAGE_GRAPH.json` 250,917 bytes /
Aug 20; `RESONANCE_GRAPH.json` 55,102 bytes / Aug 22 — different content, not a rename).

**F9. [MEDIUM] [REPRODUCED] `weave.py:478`'s inline comment ("resonance.py reads it") is false on
two independent counts.**

```python
"pairs": [{"a": a, "b": b, "weight": round(v, 2),
           "shared_sample": shared[(a, b)]}   # WHOLE list (key name kept: resonance.py reads it) -- Hard Rule 0, ruled 2026-08-24
          for (a, b), v in sorted(kept.items(), key=lambda kv: -kv[1])]},
```

This comment is attached to the write of `OUT_GRAPH = data/SHARED_STAGE_GRAPH_IDF.json`
(`weave.py:82`) — the IDF-weighted variant. But (1) per F8, `resonance.py`'s default read path is
plain `SHARED_STAGE_GRAPH.json`, not the `_IDF` file this comment is attached to, and (2) per F7,
`resonance.py` is never imported by anything, so it does not "read" any file, live or otherwise.
The comment is doubly wrong: wrong file, and (as of today) no reader at all.

**Downstream consequence, not a bug in this batch's files but worth recording:**
`custodes.convene()` (outside this batch) accepts an `eta=None` parameter that is meant to be
`resonance.hodge_decompose()`'s output, and correctly implements Threnody's veto when a real `eta`
is supplied (`custodes.py:352-355`, unit-tested with synthetic `eta=0.70`/`0.99` in
`verify_math.py`). But the ONE real production call site, `anchors.py:190`
(`CU.convene(a["anchor"], a["scores"], attestation=a["attestation"], worksheet="anchors.py")`),
never passes `eta=` — so in the only place this runs against real data today, `eta` is always
`None` and the veto can never fire. This is a genuine "CHECKS THAT CANNOT FAIL" (LENS 6) instance,
directly downstream of `resonance.py` being orphaned (F7): the veto logic is real and tested, but
nothing in the live pipeline ever computes and threads the value it needs to act on.

**Suggested fix:** either wire `resonance.py` into the real pipeline (have `pipeline.py`'s phase 3
compute `hodge_decompose()` over the comparison graph it already builds, and thread `eta` into
`anchors.py`'s / any real `convene()` call), or, if it is genuinely not ready to be load-bearing,
say so explicitly at the top of the module rather than presenting it as already-wired
infrastructure — and fix `resonance_strength()`'s default path to `RESONANCE_GRAPH.json` regardless.

`hodge_decompose()`'s Gauss-Seidel solver, `dominates()`'s componentwise preorder, and
`incomparability_rate()`'s pairwise scan are otherwise mathematically sound as read (not
independently re-derived against the charter's worked examples in this pass — that would need a
`calibration_report()`-style check, which this module does not have and which nothing calls it to
provide). `incomparability_rate()`'s `examples` list capped at 5 is display-only (the `total`/
`inc` counts themselves are computed over every pair via `itertools.combinations`, uncapped) — not
a Hard-Rule-0 violation.

---

## 7. `src/drill.py` — the proof layer

Ran `python src/drill.py` once, read-only, as explicitly permitted. Current state: **102 nets
attacked, 102 held, 0 breached** (the CLAUDE.md text citing "57 nets" and the task briefing's "75"
are both stale — the file has grown since either was written; 102 is the true current count,
counted both by direct enumeration of `net(...)` call sites and by the drill's own printed
total). `state/drill_last.json` was refreshed by this run (expected, permitted side effect).

### Liveness ceiling ratchet — VERIFIED HONEST

```
liveness.scan(): dead=38  tautology=0  phantom=0  total=38
LIVENESS_CEILING (drill.py:42) = 38
```

Ran `liveness.scan()` directly: it matches `drill.py`'s own comment ("Measured 2026-08-25: 38 dead
module-level functions, 0 syntactic tautologies, 0 phantom guards") exactly, and the ceiling sits
at EXACT parity with the live count — zero slack. `liveness_does_not_worsen()` (:744-755) is a
genuine, honest ratchet: any single new dead function, tautology, or phantom guard anywhere in
`src/` would push the sum to 39 and immediately breach this net. No evidence of the ceiling having
been padded or silently raised to stay green.

### Non-attack nets found (per the special focus)

Four nets report HELD without their attack actually reaching the guard they name. All four were
reproduced by constructing the documented historical bug (or an equivalent guard-deletion) in a
scratch script and showing the net's own boolean expression is unmoved by it.

| # | Net (file:line) | What it claims to attack | What it actually tests | Verdict |
|---|---|---|---|---|
| 1 | `"COVERAGE.json unreadable is a refusal, not a pass"` (`drill.py:82-85`) | `prose_gate.cited_fraction`'s fail-closed `except Exception: return None` on an unreadable `COVERAGE.json` | `cited_fraction("anything", None)` with the REAL (readable) `COVERAGE.json` — "anything" is simply not a source name in the rows, so the function returns `None` via the ordinary "not found in the loop" path, never the `except` branch. **REPRODUCED**: deleting the `except` clause entirely and re-evaluating the net's exact expression still returns `True` (HELD). | NON-ATTACK |
| 2 | `"the cited set is looked up, not read off a key that does not exist"` (`drill.py:204-208`, guards AUDIT DEFEAT 5) | `prose_gate.cited_names_for()` correctly identifying which names carry real cited feats, as opposed to the pre-fix bug where the set was unconditionally empty | Only `result is not None and isinstance(result, set)` — a type check | **REPRODUCED**: a stub `cited_names_for` that always returns `set()` (the exact, documented, pre-fix bug) still satisfies the net's condition and reports HELD. | NON-ATTACK |
| 3 | `"the writer does not overwrite a neighbour"` (`drill.py:266-268`, the M23 fix) | `cachekey.write_path()`'s collision-avoidance branch (does it fall back to the disambiguated path when a DIFFERENT entity already owns the natural path?) | `disambiguated_path(...) != natural_path(...)` — compares two pure path-string-builder helpers, never calls `write_path()` at all | **REPRODUCED**: with `write_path()` rewritten to always `return natural_path(...)` (restoring the exact M23 overwrite bug) and a real file on disk owned by a different entity, the drill net's own expression is unaffected and still reports HELD. | NON-ATTACK |
| 4 | `"every guard is present in the file that claims it"` / `guards_are_wired_where_claimed()` (`drill.py:730-742`) | That `assert_gate_open`, `_prose_enabled()`, and `cachekey` are actually WIRED (imported and called) in `generate.py`/`overnight.py`/`coverage.py`/`feats.py`/`pipeline.py`/`hostcheck.py` | A raw substring search (`token not in fh.read()`) over each file's whole text — satisfied by a comment or docstring mentioning the word, not by real usage | **REPRODUCED**: stripped the real `import cachekey` line and every functional `cachekey.<fn>(...)` call site out of `coverage.py` in memory, leaving only the one pre-existing docstring line that already mentions "cachekey.owns()" — the substring `"cachekey"` still occurs in the gutted text, so this net's check would still report the guard as "wired" even though the actual ownership-verification calls are gone. | NON-ATTACK |

All four share the shape the task's special focus names: the attack (or, for #4, the
verification) is satisfied by an unrelated code path or a static text match, not by exercising the
guard it is named for. None of the four would go RED if the named guard were deleted or reverted
to its documented pre-fix state.

**Suggested fixes:**
1. Actually corrupt a temp copy of `COVERAGE.json` (or monkeypatch `_coverage_rows`/
   `os.path.exists`) and call `cited_fraction`/`evidence_ok` against that, the way
   `_halt_fails_closed()` (`drill.py:398-416`) already correctly does for the halt file.
2. Assert on MEMBERSHIP, not type: seed a real cache file for a name with a real cited feat,
   assert it IS in the result, and seed a name with no cited feat, assert it is NOT — the two
   things AUDIT DEFEAT 5 was actually about.
3. Call `cachekey.write_path()` directly against a scratch dir holding a file owned by a different
   entity, and assert it returns the disambiguated path — exactly the pattern
   `_scanner_finds_a_planted_secret()` (`drill.py:526-546`) already uses correctly for `publish.py`.
4. Either grep for the ACTUAL call sites (e.g. `re.search(r"\b" + fn + r"\(", text)` against a
   real attribute-call pattern) rather than a bare substring, or — better, matching this project's
   own stated preference for dynamic proof over static text search — instrument each target
   function to record a call and assert the recording fired during a real, minimal invocation of
   the file's own entrypoint.

### Other observations (not full non-attacks, but worth recording)

- **[MEDIUM] drill.py's own docstring is contradicted by two of its nets' side effects.**
  `drill.py:14-17` promises "Every attack is constructed in memory or in a scratch directory,"
  but `drill_snapshot`'s `"a snapshot restores byte-identically"` net calls the REAL
  `snapshot.before("drill", ["config.yaml"], ...)`, and `drill_park`'s
  `"a SOURCE-level fault does NOT change the park's halt state"` net calls the REAL
  `escalation.escalate(SUPERVISOR, ...)` — both write permanent artifacts into the real repo's
  `state/` tree, not a scratch directory. Confirmed: `state/snapshots/` currently holds 7
  never-cleaned `drill-*`/`drill-empty-*`/`drill-selftest-*` directories accumulated across past
  runs (plus this run's own), and `state/escalation.log` / `state/escalations/__drill__.log` grow
  by one line on every invocation. `snapshot.py` documents itself as deliberately having "no
  rotation cleverness," so this is a real, if minor, disk-accumulation issue as well as a
  comment-vs-code mismatch (LENS 7) in `drill.py`'s own header.
- **[LOW] `_no_programmatic_clear()`** (`drill.py:476-485`) detects `escalation.clear(`/
  `ESC.clear(` via literal substring search across every `.py` file in `src/`. A module that
  imported `escalation` under a different alias (`import escalation as X; X.clear(...)`) would
  evade detection. No real code does this today, so the net currently reports correctly — flagged
  as a narrow blind spot, not a confirmed non-attack.

### Everything else checked and found to be genuine

Read the corresponding target modules (`prose_gate.py` in full; `cachekey.py` in full;
`escalation.py` in full; `snapshot.py` in full; `ledger_guard.py` in full; `silence.py`'s
`digest_of`/`replace_if_unchanged`; relevant sections of `assay.py`, `local_agent.py`,
`publish.py`, `pipeline.py`) to confirm every remaining net calls the real guarded function with a
crafted input that genuinely exercises the documented failure shape, and would plausibly go RED
if that guard were removed or inverted:

- **Queue/Dispatch** (`gate_open`, `step4_gate_open`, `assert_gate_open`, `assert_step4_open`):
  every strict-identity check (`"true"`/`"false"`/`1`/non-dict) is a real call against the actual
  function with the actual adversarial value; `_step4_needs_its_plan()` genuinely renames the real
  `STEP4_PLAN.md` off and back.
- **Train / Assay-honesty** (`section_shortfall`, `assert_block_complete`, `unearned_instrument`,
  `_AXIS_RE`): all nine "AUDIT DEFEAT" fixtures are crafted text run through the real regex/scoring
  logic, including the bold-markdown and run-on-sentence obfuscation cases.
- **Assay engine** (`assay.py`): `calibration_report()` re-derives the charter's number through
  live code rather than asserting a constant; `_check_constants()`/`_broken_table_refuses()`
  genuinely mutates the real `SIGMA_BY_ATTESTATION` dict and calls the real check function.
- **Cache/M23** (`cachekey.owns`, `coverage.state_of`): direct real calls; the live-corpus pair
  check (`live_reads_are_separated`) reads actual `coverage.state_of` against the real corpus.
- **Local agent** (11 nets): `denied()`'s error-message matching (`"denylist"`/
  `"protected region"`/`"writable surface"`/`"no such file"`) maps 1:1 onto the literal strings the
  four real refusal code paths in `t_propose_patch` (`local_agent.py:492,504,511,456`) produce,
  confirmed by direct comparison; this design deliberately fails toward BREACHED (not HELD)
  whenever the actual refusal reason cannot be positively identified, so an unrecognised failure
  mode (e.g. a find-string count mismatch) cannot masquerade as a security-gate refusal — the
  precise class of bug this file's own docstring says a PRIOR version of this exact function had.
- **Publish** (redaction nets, `_scanner_finds_a_planted_secret`): real calls against real
  `scrub_text`/`scan_for_secrets`, including a genuine plant-then-scan-then-clean-then-rescan
  cycle in a real temp directory.
- **Ledgers**: real calls against real `check_append_only`/`check_structure`, crafted inputs that
  match the documented containment/truncation/dual-listing failure shapes.
- **Two-writer** (`pipeline.verify_record_provenance`/`stamp_record`): real digest recomputation
  (`_entry_digest`, SHA1 over entry names) drives genuine OK/UNSTAMPED/DRIFTED distinctions.
- **Snapshot** (`before`/`verify`): real byte-for-byte restore-and-compare in a temp dir; the
  empty-snapshot-raises case genuinely exercises `SnapshotFailed`.
- **Stale writer** (`silence.replace_if_unchanged`): a real compare-and-swap race is constructed
  (write v1, capture digest, write v2 "externally," attempt a stale write) against a real temp
  file.
- **Park** (`escalation.status`/`clear`/`_raise_halt`): `_halt_fails_closed()` points the real
  module at a genuinely corrupt temp HALT file and reads the real `status()`; the ruling-length
  and lazy-ruling checks call the real `clear()`.
- **Inspector**: all five reconciliation checks (`gate_claim_matches_reality`,
  `catalog_matches_disk`, `coverage_totals_are_recomputable`, `halt_claim_is_honest`, plus the
  liveness ratchet) read real, current project state (`COVERAGE.json`, `catalog.json`,
  `output/raw`, `HALT.json`) rather than fixtures, and would flag a real drift if one existed.

No further non-attack nets found beyond the four listed above.

---

## Summary table

| # | Severity | File:line | Status | One-line |
|---|---|---|---|---|
| F1 | HIGH | wiki_source.py:549-573 | REPRODUCED (KNOWN) | `category_members` returns a partial roster on any exception, no completeness flag |
| F2 | HIGH | identity.py:180-207 | REPRODUCED (KNOWN) | `_is_continuity` can never admit a single-bearer branching continuity, contradicting its own (Fates) example |
| F3 | MEDIUM | identity.py:218-222 | REPRODUCED (carried forward) | fixed `.tmp` cache-write filename is a two-writer race hazard |
| F4 | HIGH | tuning.py:188-212 | REPRODUCED (NEW) | `regime()` skips CLOUD_MIN_SUCCESS entirely when `judged=False`, reads "cloud" off bucket count alone |
| F5 | HIGH | style_audit.py:48-51 | REPRODUCED (KNOWN, sharpened) | `record_of()` matches 8/1278 entries (0.6%); 99.4% audited whole, not prose-only |
| F6 | MEDIUM | style_audit.py:38-39 | HYPOTHESIS (directional demo) | `TURN_ENDING`'s `re.M $` plus F5's fallback plausibly inflates turn_rate |
| F7 | HIGH | resonance.py (whole module) | REPRODUCED (KNOWN) | imported nowhere in src/; all 3 top-level fns liveness-DEAD |
| F8 | HIGH | resonance.py:141 | REPRODUCED (KNOWN) | defaults to SHARED_STAGE_GRAPH.json, not the real pipeline's RESONANCE_GRAPH.json |
| F9 | MEDIUM | weave.py:478 | REPRODUCED (KNOWN) | "resonance.py reads it" comment names the wrong file and, per F7, no reader at all |
| F10 | HIGH | drill.py:82-85 | REPRODUCED (NEW) | "COVERAGE.json unreadable" net never makes it unreadable — non-attack |
| F11 | HIGH | drill.py:204-208 | REPRODUCED (NEW) | "cited set looked up" net is a bare type check — non-attack |
| F12 | HIGH | drill.py:266-268 | REPRODUCED (NEW) | "writer does not overwrite a neighbour" net never calls write_path() — non-attack |
| F13 | HIGH | drill.py:730-742 | REPRODUCED (NEW) | "guards wired" net is a substring search, satisfied by a stray comment — non-attack |
| F14 | MEDIUM | drill.py:14-17 + snapshot/park nets | REPRODUCED (NEW) | drill.py's "scratch directory only" promise is violated; permanent state/ debris accumulates |
| F15 | LOW | drill.py:476-485 | observation (NEW) | alias-import would evade `_no_programmatic_clear()`'s literal-string search |
| — | LOW | ingest_doc.py:116-126 | observation | `record_path()` substring-containment fallback could match the wrong file |
| — | LOW | ingest_doc.py:164-172 | observation | an oversized single page becomes an unbounded chunk (correct per Hard Rule 0, flagged for awareness) |

No Hard-Rule-0 cap violations found in this batch (every roster/listing function that matters is
genuinely uncapped by default: `wiki_source.find_categories/category_members/rank_by_size`,
`identity.mine`, `ingest_doc.mine`'s chunking, `resonance.incomparability_rate`'s pair count). The
few `top=N`/`most_common(N)` sites found (`style_audit.report()`, `resonance.incomparability_rate`'s
`examples`) are display-only truncations of an already-complete underlying count/Counter, not
truncations of the roster itself, consistent with prior sweeps' treatment of the same pattern.
