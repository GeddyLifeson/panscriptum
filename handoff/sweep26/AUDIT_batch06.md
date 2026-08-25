# AUDIT — Batch 06 (run26)

Modules (read in full, top to bottom, no sampling):

| file | lines |
|---|---|
| src/cascade_bridge.py | 1050 |
| src/silence.py | 425 |
| src/estate.py | 338 |
| src/feats_index.py | 263 |
| src/propagation.py | 214 |
| src/retry_synthesis.py | 152 |
| **total** | **2442** |

All findings below were checked against live state on disk (`state/POOL_UNRECOGNISED.json`,
`state/cascade_scratch.db`) and, where relevant, cross-referenced against `src/pipeline.py`
(external to this batch but load-bearing for one finding).

---

## PART 1 — SPECIAL FOCUS: `cascade_bridge.py` pool diagnosis

### 1a. The three "unrecognised" rows — live re-check

I loaded the actual ledger and ran the current classifiers against it (not paraphrase — literal
function calls against the live rows):

```
groq:openai/gpt-oss-120b | "All 1 candidates failed: GPT-OSS 120B (Groq)"  x30
    pool_exhausted=False  named_transient=False  empty_content=False   -> STILL UNRECOGNISED

groq:groq/compound-mini  | "empty response"                             x6
    pool_exhausted=False  named_transient=False  empty_content=TRUE     -> NOW FILTERED, resolved

sambanova:free            | {"error":{"message":"rate limit exceeded",...} x6
    pool_exhausted=False  named_transient=TRUE   empty_content=False    -> NOW FILTERED, resolved
```

`unrecognised_open()` (the function `standards.py` actually calls, `src/standards.py:951`)
currently returns 13 open rows, and the compound-mini/sambanova rows are **not** among them —
verified by calling it directly. **Two of the three symptoms named in the brief are already
fixed** by code that is present in the file as audited (`empty_content()` added run #25,
`named_transient`'s "rate limit" phrase). If the standards page (or a person) is still citing
these two as red, it is reading the raw `state/POOL_UNRECOGNISED.json` file directly rather than
through `unrecognised_open()` — the raw file legitimately still contains old rows (rows are kept
as evidence, per `unrecognised_open`'s own docstring), so that would look alarming without the
re-triage step. **Only the gpt-oss-120b row is a genuine live gap.**

### 1b. Why `All 1 candidates failed: GPT-OSS 120B (Groq)` (x30) stays nameless

`cascade_bridge.py:456-483` (`provider_error`) is supposed to unwrap this: it reads
`bucket_state.last_error` from Cascade's own scratch DB, but only if that row is `<=180s` old
(`max_age_s=180`, the default used at the one call site, line 895). I queried
`state/cascade_scratch.db` directly for this exact bucket:

```
bucket: groq:openai/gpt-oss-120b
last_error: {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` ...
             tokens per day (tpd): limit 200000, used 198611 ...}}
```

The real disposition **is** a rate limit (a Groq daily-token-quota exhaustion) and, if it ever
reached the classifier, `named_transient()` would correctly match it (contains "rate limit"). One
later occurrence of this same bucket DID unwrap successfully and was recorded separately
(`first_seen` just after the 30-count burst ended) — proving the mechanism works when the DB row
is fresh. During the 30-count burst itself, though, the unwrap never once succeeded: all 30
occurrences share the identical wrapper-only key, meaning `provider_error()` returned `""` every
single time. The most likely mechanism, given the evidence: this was the pool's first sustained
contact with this bucket, and Cascade's own `bucket_state` write for a given failure is not
guaranteed to have landed (or land within 180s of a fast retry cadence) before `cascade_bridge`
reads it back a moment later — a write-then-read staleness/ordering gap between two different
data paths for what should be the "same" event, rather than a bug in the classifier's wording
tables themselves.

**Proposed fix (not applied):** split the freshness threshold by purpose. The 180s window exists
to protect the *bench* decision (don't 4-hour-bench a bucket on a fossil) — that risk calculus
does not apply to `record_unrecognised`'s read, which explicitly never benches. Call
`provider_error(pinned.bucket, max_age_s=600)` (or no cap at all) specifically for the
unwrap-for-ledger-text purpose at `cascade_bridge.py:895`, while leaving a short window (or the
existing 180s) for any future unwrap that feeds a benching decision. This alone would very likely
retro-classify future occurrences of this exact row as `named_transient` and stop it accumulating
under a disposition-free label.

### 1c. Pool collapse — only nvidia:free calling despite 27 buckets with headroom

`state/cascade_scratch.db.bucket_state` right now: **21 of 23 known buckets have not been
attempted in 30-49 minutes** (ages 1889s-2868s), while `nvidia:free`'s own last recorded error
(`{"status":429,...}`, 2869s old) shows it too was rate-limited around the same time as everyone
else and has since recovered and kept getting picked. The buckets that went quiet did so
**simultaneously**, consistent with a single burst (most plausibly `prove()`, which pins buckets
explicitly by name) — and nothing has touched most of them since.

The code-level cause, in `_ask_call` (`cascade_bridge.py:697-716`), is that the **primary claim
path has no rotation at all**:

```python
for _ in range(4 if pin is None else 0):
    claimed = _ROUTER.claim(pool, 1)
    ...
    if _alive(cand.bucket):
        pinned = cand
        break                      # <- first alive candidate wins, no comparison, no rotation
    _ROUTER.release(cand)
```

`_ROUTER.claim(pool, 1)` asks the router for exactly one candidate and hands back whatever it
picks; `cascade_bridge` only rejects it if it's local or already benched, otherwise it locks in
immediately. There is **no round-robin, no "was this bucket just used", no anti-affinity** in
this loop — that logic exists ONLY in the widen/fallback path (`_WIDEN_RR`, lines 202-203,
760-766), which is reached only when `claim()` fails four times in a row. If the router's own
`claim(pool,1)` ranking deterministically prefers whichever bucket currently looks best (most
headroom, lowest latency, first in some priority order) and that bucket keeps having headroom,
`claim()` never fails, the widen path never triggers, and every worker converges on the same one
bucket — exactly the shape the code's own comment at lines 753-758 already diagnosed and fixed
**for the widen path only**:

> "First-alive-wins pinned EVERY call to the same front-ranked bucket, and the whole pool
> serialised through one provider's per-minute cap ... The offset spreads consecutive calls
> across the alive set"

That fix was never carried over to the primary per-call claim loop, where the actual traffic
runs. This is the most concrete, in-repo explanation for the reported symptom. `learned` limits
and any router-side backoff after nvidia:free's earlier 429 are external to this file
(`cascade`'s own `router.py`, not part of this batch) and could not be verified here, but nothing
in `cascade_bridge.py` diversifies bucket selection outside the widen fallback, so this file's own
logic is sufficient on its own to explain a collapse to one bucket whenever the router's `claim()`
rarely or never fails outright.

**Proposed fix (not applied):** either (a) have the primary claim loop track and skip the
bucket it used most recently (a simple "don't repeat last N buckets" set, mirroring `_WIDEN_RR`
but for `claim()`'s result), or (b) call `_ROUTER.claim(pool, k)` for `k>1` and choose among the
returned candidates with the same round-robin/proof-ranked logic already written for `widen`,
rather than accepting `claim()`'s single top pick unconditionally.

### 1d. `record_unrecognised` — can it lose the unknown it exists to record? Yes, two ways.

`cascade_bridge.py:486-529`. The function is deliberately "Total" (its own docstring: "a recorder
that can raise would suppress the fault it exists to expose"), which is the right instinct, but
the *totality* is implemented as a single outer `except Exception: pass` with **no `silence.note`
call inside it** — unlike every sibling `except` in this file. If the write itself starts failing
(a denied replace, a Norton object-lock outlasting `replace_retry`'s ~3s of backoff, a disk-full
condition), there is **zero trace anywhere** that `record_unrecognised` is failing — not even in
`silence`'s own failure ledger. Every other total-catch site in this file at least calls
`silence.note(...)` first; this one is silent about its own silence.

More importantly, this is a genuine **two-writer race with data loss**, not just a missing log
line. The docstring itself says this file "is written from every process that imports
`cascade_bridge` (read, pipeline, feats, overwatch)" — multiple OS processes, not just threads.
`_UNREC_LOCK` is a `threading.Lock`, which only serialises writers *within one process*. The
read-modify-write cycle (`open` → `json.load` → mutate `rows` in memory → `write_json`) has no
cross-process coordination at all — no file lock, no optimistic version check. Classic lost
update: process A reads the file, process B reads the same (pre-A-write) snapshot, A writes back
with its new key added, B writes back its own snapshot plus its own new key — and B's write
**completely overwrites A's**, silently dropping A's row (not merely undercounting it — the row
and its whole history vanish, unless some other write happens to reintroduce that same key later).
`silence.write_json`'s atomicity guarantees the file is never *corrupted*, but atomicity of the
final write does nothing to prevent this lost-update race between two independent read-modify-write
cycles. This is the exact two-writer hazard the project's own `MEMORY.md` flags generically for
this repo ("records two-writer hazard") landing concretely in the one file whose entire purpose is
"never let an unknown failure disappear."

**Recommended fix (not applied):** either move this ledger to something with real cross-process
atomicity (a single-writer queue file per process, merged periodically, the same shape
`cascade_bridge._metric`/`silence.append_line` already uses successfully for `model_metrics.jsonl`
via one-syscall appends — append rather than read-modify-write), or wrap the read-modify-write in
an OS-level file lock (`msvcrt.locking` on Windows) held across the whole cycle, not just the
final replace.

---

## PART 2 — line-by-line findings by file

### `src/cascade_bridge.py` (1050 lines)

- **MAJOR** `cascade_bridge.py:697-716` — primary claim loop has no rotation/anti-affinity; see
  §1c above. This is the strongest candidate for the live pool-collapse symptom.
- **MAJOR** `cascade_bridge.py:486-529` (`record_unrecognised`) — cross-process read-modify-write
  race can silently drop a whole ledger row; outer `except: pass` has no `silence.note`, so even
  the meta-failure is untraceable. See §1d.
- **MINOR** `cascade_bridge.py:895` (`provider_error(pinned.bucket)`, default `max_age_s=180`) —
  freshness window is shared between "safe to bench on" and "safe to display in the ledger",
  which are different risk profiles. See §1b for the concrete miss this causes.
- **MINOR** `cascade_bridge.py:311-312,326` (`dead_forever`) — `_PROVEN[0]` is cached permanently
  after the first call in a process (`if _PROVEN[0] is not None: return`), even though the
  surrounding logic clearly treats `PROOF_TTL=3600` as meaningful ("a proof this old is no longer
  evidence about now"). In a process that runs for hours (this file's own docstrings say jobs
  here do), the very first call's snapshot — which could itself have been computed while the
  proof file was already stale, yielding an empty set — is used for the rest of that process's
  life; a fresh `prove()` run by another process minutes later is invisible to it. Not exercised
  live, but worth a re-check on next restart of a long-lived worker.
- **QUESTION** `cascade_bridge.py:122-155` (`_extract_json`) — the brace-matching fallback
  restarts its search from `start+1` on a parse failure rather than from past the failed span, so
  a reply with several unbalanced `{` before the real JSON can rescan overlapping text repeatedly
  (worst-case quadratic on pathological input). Not a correctness bug, low real-world impact given
  reply sizes, flagged for completeness only.
- No subprocess spawns in this file — CREATE_NO_WINDOW lens item does not apply.
- HARD RULE 0: no caps, samples, or truncated-listing patterns found in this file. `widen_candidates`,
  `cloud_buckets`, `prove`, `try_disabled`, `dead_buckets` all iterate every model/bucket with no
  `[:N]`. `selftest()`'s `ready[:12]` (line 948) is a print-only display slice for a human-facing
  self-test banner, not a data cap — legitimate.

### `src/silence.py` (425 lines) — owns `replace_retry`, audited hard

- **MAJOR — the self-audit tool systematically under-counts silent handlers.**
  `_handlers()` (`silence.py:115-138`) computes `body = ast.dump(node)` over the **entire**
  `ExceptHandler` node (type, name, and body together), then checks `node.name in body` to decide
  `uses_exc`. But `ast.dump` of an `ExceptHandler` always serialises its own `name=` field
  (e.g. `name='e'`), so `node.name in body` is checking whether the handler's own alias string
  appears in a string that **structurally contains that exact alias by construction** — it is
  true for every `except X as name:` regardless of whether `name` is ever used inside the body.
  Verified directly:
  ```
  except Exception as e:
      pass
  ```
  classifies as `silent=False` (i.e. "observed", not flagged) purely because `name='e'` is part of
  the node's own dump — this is the textbook silent-swallow pattern the whole file exists to catch
  (identical in shape to the docstring's own worked example, "a bare `except Exception: return
  None`"), and the audit misses it entirely whenever the handler names its exception. Given
  `except ... as e/exc/err:` is an extremely common Python idiom, this means `python3 silence.py`'s
  reported "SILENT" count is a significant undercount project-wide, and has been since this
  function was written — the audit's headline number cannot be trusted as a ceiling.
- **MAJOR — companion false-positive: the `records` substring check over-matches.**
  Same function, same line: `records = any(t in body for t in ("health", "record", "log",
  "print", "raise", "swallow", "silence", "LEDGER"))` tests these as raw substrings of the full
  `ast.dump` string, which includes every string literal and identifier inside the handler
  verbatim. Verified directly:
  ```
  except Exception:
      catalog_ref = None
  ```
  classifies as `records=True` (not silent) purely because `"log"` is a substring of
  `"catalog_ref"` in the dump's `id='catalog_ref'`. A genuinely silent handler (no logging, no
  re-raise, no recording of any kind) that happens to touch a variable/string containing "log",
  "record", "raise", or "print" as a substring (catalog, dialog, backlog, appraisal, sprint,
  blueprint, fingerprint, printer, etc.) is invisibly marked "observed". This is the mirror image
  of the `uses_exc` bug above and compounds it — both push the reported SILENT count down, never
  up, so the tool's error is one-directional and always optimistic. Together these two are the
  single highest-value finding in this batch: the meta-auditor for "is a failure silently
  swallowed" is itself silently swallowing failures to detect.
  **Suggested fix (not applied):** check identifiers structurally (walk the handler's own
  `node.body` AST for `Call` nodes whose func resolves to `health.record`/`silence.note`/etc., or
  for a bare `Raise` statement) rather than substring-matching the flattened `ast.dump()` text,
  and for `uses_exc`, walk `node.body` for `Name` nodes matching `node.name` rather than searching
  the whole-node dump that trivially contains the name by construction.
- **`replace_retry`** (`silence.py:223-240`) — reviewed hard per the brief:
  - Catches `PermissionError` only. On Windows, `os.replace` failures from both ERROR_ACCESS_DENIED
    (WinError 5) and ERROR_SHARING_VIOLATION (WinError 32, the shape a Norton object-lock takes)
    both surface as `PermissionError` in CPython, so this is the right exception class for the
    documented hazard.
  - Retry bound: 5 attempts, backoff `0.3*(a+1)` seconds (~3s total worst case) before giving up.
    On final failure it calls `note(...)` (observed, not silent) and returns `False` — it does
    **not** raise and does **not** retry forever, matching the docstring's claim exactly.
  - **MINOR** — on persistent failure the orphaned `tmp` file (`path.pid.tid.tmp`) is never
    cleaned up; it is simply abandoned. Given this project runs many processes writing many state
    files over many hours, a sustained lock (e.g. Norton scanning a large `state/` file
    repeatedly) could leave an accumulation of dead `.tmp` files. Not a correctness bug (`dst`
    is never touched by a failed replace, so no truncation risk), but worth a periodic sweep.
  - **MINOR** — `write_json`'s return value is frequently ignored by callers (e.g.
    `cascade_bridge.record_unrecognised` at line 527) — see §1d. The recorder/caller contract
    ("check the boolean, note-worthy on False") is not consistently honoured project-wide.
  - The write-then-rename sequencing itself is correct: `write_json` writes to a pid+thread-unique
    temp name, and on any exception during the dump it best-effort removes the partial temp file
    and **re-raises** rather than attempting the replace — so `dst` can never observably become a
    truncated file from an interrupted dump. Confirmed no gap here.
- **`note()`** (`silence.py:290-322`) — **MINOR concurrency race**: `_SINCE_FLUSH` and
  `_ATEXIT_ARMED` are plain module globals mutated without a lock (`_SINCE_FLUSH += 1`, compare,
  reset), while `note()` is called from many worker threads across this codebase (heavily so from
  `cascade_bridge`, which runs one thread per in-flight call). Concurrent increments can race
  (lost increments delay the periodic `health.flush()`, or two threads can both observe the
  threshold and both flush). Consequence is mild — delayed/duplicated flush, not data loss, since
  the eventual `atexit` flush is still armed — but it is a genuine unlocked shared-state mutation
  in a file whose entire subject is disciplined failure-handling.
- `append_line` (`silence.py:187-220`) — single `os.write` to an `O_APPEND` fd is correctly
  reasoned for atomic sub-page appends on both POSIX and Windows (Windows honours atomic append
  via the same `O_APPEND` flag through `FILE_APPEND_DATA` semantics); no bug found.
- HARD RULE 0: no caps/samples found. `instrument()`/`audit()`/`_handlers()` walk every file, every
  handler, unbounded.

### `src/estate.py` (338 lines)

- **MINOR** `estate.py:69-76` (`inspect`) — zero-byte files are exempted from the "zero bytes"
  error **only** for extensions `.log/.tmp/.out/.err`. This means an orphaned atomic-write temp
  file left behind by a persistently-denied `replace_retry` (see `silence.py` §above) — which
  would be named e.g. `POOL_UNRECOGNISED.json.1234.5678.tmp`, extension `.tmp` — is silently
  exempt from ever being flagged, at any size: a zero-byte one is explicitly whitelisted, and a
  **non-zero** one is invisible too, because `.tmp` is in neither the `.json` branch nor
  `TEXT_EXT`, so its content is never opened/validated at all — only its size is counted. This
  directly undercuts the module's own stated premise ("No sampling... every file, opened") for
  exactly the file class most likely to be evidence of the write-failure hazard this whole batch
  was asked to hunt for.
- **MINOR** `estate.py:251-252` (`written()`) — `if d: note(label, f"{len(d)} records")` skips the
  note entirely when the loaded JSON is empty (`{}` or `[]`). A `catalog.json` or `failures.json`
  that has genuinely gone from thousands of records to zero (a real regression) produces **no
  output at all** from this check — identical to the file never having been written. Given the
  module's own framing ("Saying so with a number is the point"), a zero should be said too, not
  silently omitted.
- No other correctness issues found. Exception handling throughout `inspect()` is properly typed
  (`UnicodeDecodeError`, `json.JSONDecodeError`, generic `Exception` as a last resort) and always
  records both to `silence.note` and to the returned `rec["error"]` — this is the pattern the rest
  of the project should be following, and does not fall into the swallowed-failure trap itself.
- HARD RULE 0: `artifacts()` walks and inspects every file under every root with no cap;
  `ex.map(inspect, paths)` processes the full path list. No caps found.
- No subprocess spawns.

### `src/feats_index.py` (263 lines)

- **MINOR** `feats_index.py:187-188` (`feats_for_source`) — `entries_by_norm.setdefault(_norm(e.get
  ("name")), e)` silently keeps only the **first** catalogue entry whenever two distinct entries in
  the same source's `entries` list normalise (alphanumeric-fold) to the identical key. If that ever
  happens across two genuinely different entities (not just two spellings of the same one), a mined
  feats record would get attached to the wrong `"entry"` metadata (wrong description/magnitude
  context downstream) with no audit signal — `audit()` reports stranded *feats* records but never
  checks for entry-name collisions within a single source's own roster. Not observed to have fired
  on the current data (would need a targeted check against `data/` to confirm live impact), but the
  join logic elsewhere in this file is unusually careful about exactly this class of silent-merge
  risk (see the `_norm` docstring's own worked example about not merging DC continuities) — this one
  spot doesn't get the same treatment.
- **QUESTION** `feats_index.py:224-225` (`audit()`) — `by_src[rec["source"]] = {...}` overwrites
  rather than unions if `PL.records()` (out of this batch) ever yields the same source more than
  once; could not verify `pipeline.records()`'s yield contract without reading that file. Flagging
  as a question for whoever owns `pipeline.py`.
- Everything else in this file is clean and unusually well-reasoned: `_norm`'s docstring correctly
  documents what folding does and does not do (and was itself corrected in-place after being wrong,
  per its own changelog note); `feats_for_source` and `audit()` are explicitly no-cap
  ("NO CAPS. `feats_for_source` returns every feat of every matching entity") and verified so by
  reading the code — no `[:N]` on any real data path.
- No subprocess spawns.

### `src/propagation.py` (214 lines)

- **MINOR** `propagation.py:155-158` (`observed_mark`) — the final `return 0` is dead code.
  `ascension_years(1) == round(1.0**1.35 - 1.0, 1) == 0.0` unconditionally, and the loop only
  reaches rung 1 after the earlier `if lag < 0: return 0` guard has already ensured `lag >= 0` —
  so `lag >= ascension_years(1)` (`lag >= 0.0`) is always true by the time the loop gets there,
  and the function always returns at least `1` from inside the loop. The trailing `return 0` can
  never execute. Not a wrong *answer* necessarily (arguably [^1] is defensible for a shelf at
  exactly zero lag, per the model's own reasoning that a town-scribe countersign is priced at
  ~0 years) but it is a guard that cannot fire, and it means mark `[^0]` is reachable **only**
  via the pre-arrival branch, never via the ascension loop — worth a comment or an explicit
  `if lag == 0: return 0` if that boundary case was meant to read differently from "just arrived".
- Dijkstra implementation (`shortest`, lines 85-112) is standard and correct: visited-set guard
  against reprocessing, early break on reaching `dst`, path reconstructed via `prev`. No bugs found.
- `a[:19]`/`b[:19]` in `main()`'s demo print (line 205) is column-width display truncation for a
  human-facing CLI table, not a data cap — legitimate, not a Hard Rule 0 violation.
- HARD RULE 0: no caps on real computation found. `probes` (lines 190-197) is a fixed, small,
  hand-picked demo list for the CLI's default no-argument mode, not a truncation of any actual
  dataset — legitimate.
- No subprocess spawns.

### `src/retry_synthesis.py` (152 lines) — several real findings here

- **MAJOR — confirmed Hard Rule 0 violation, and a stale-parity claim.**
  `retry_synthesis.py:60`: `sample = sorted(rec["entries"], key=lambda e: -len(e.get
  ("description", "")))[:14]` — ranks then truncates to 14 entries, exactly the pattern
  `CLAUDE.md`'s Hard Rule 0 names as forbidden verbatim ("Ranking then truncating is not
  [allowed]"). The function's own docstring claims: *"Byte-identical prompt construction to
  phase_synthesis, so a retried source is not scored by a different method than its
  neighbours."* That claim is **false as the code now stands**. I read `pipeline.py`'s
  `phase_synthesis` (lines 655-707) directly: it used to do exactly this same rank-then-truncate,
  and was deliberately rewritten under an explicit owner ruling —
  > "The fixed sample-of-14 could silently clamp a whole source to a lesser ceiling whenever the
  > true strongest entity ranked fifteenth by feat-count ... (BUGS m13, Hard-Rule-0-shaped, ruled
  > by the owner 2026-08-24: FIX IT ALL)."
  `phase_synthesis` now **chunks** every feat-bearing entry in batches of 14
  (`chunks = [with_feats[i:i+14] for i in range(0, len(with_feats), 14)] or [rest[:14]]`,
  `pipeline.py:707`) and keeps the best band across all chunks — no feat-bearing entry is ever
  excluded. `retry_synthesis.py` never picked up this fix: it still ranks by raw description
  length (not by whether the entity has mined feats at all) and still hard-truncates to one
  sample of 14. A source retried through this path can therefore silently get a lower/absent
  ceiling nomination than the same source would get from the main pipeline, for a source whose
  true ceiling entity happens to rank outside the top 14 by description length (or is feat-heavy
  but description-light) — precisely the failure mode the owner ruling was written to close, now
  reopened in the retry path. This should either import/reuse `pipeline.py`'s chunking logic
  directly, or be fixed to match it.
- **MAJOR — validates truncated evidence instead of full evidence.**
  `retry_synthesis.py:77-81`:
  ```python
  ev = (got.get("evidence") or "").strip()[:600]
  ...
  if not PL.valid_scale_note(ev):
      band = "unassayed"
  ```
  truncates to 600 characters **before** validating. `pipeline.py`'s own canonical version
  (`pipeline.py:730-732`) validates the full, untruncated evidence string (`_ev = (g.get
  ("evidence") or "").strip()`) and only then would any storage-side truncation apply. If a
  genuinely valid scale-note's qualifying content sits past character 600 (plausible — this is
  free-form model prose, not a fixed-format field), `retry_synthesis.py` would wrongly downgrade
  a valid nomination to `"unassayed"` purely due to truncation order. Fix: validate the full
  string, truncate only what gets stored.
- **MAJOR — non-atomic, collision-prone writer; the exact pattern the project already retired
  elsewhere.** Both `save_side()` (`retry_synthesis.py:43-47`) and the per-record write inside
  `do_merge()` (`retry_synthesis.py:109-112`) use `tmp = path + ".tmp"` — a **fixed** temp
  filename, not pid+thread-unique — then `os.replace(tmp, path)` with **no retry** (no
  `try/except PermissionError`, unlike `silence.replace_retry`). This file does not `import
  silence` at all. `silence.write_json`'s own docstring documents that this exact fixed-name
  pattern was found and fixed across twelve call sites in a comprehensive 2026-08-25 sweep
  specifically because two writers of the same path collide on the temp file itself and the loser
  can replace the winner's target with a partial file — `retry_synthesis.py` was evidently not
  part of that sweep (or was added after it) and still carries the retired pattern in two places:
  - `save_side()` writes `data/SYNTHESIS_RETRY.json` inside the per-source retry loop in `main()`
    (`retry_synthesis.py:143`) with no guard against a Norton lock — an uncaught `PermissionError`
    here crashes the whole retry run, discarding all not-yet-persisted work for the source
    currently in flight (though prior sources' results are already safely on disk from earlier
    loop iterations).
  - `do_merge()` writes into `data/records/*.json` — the **exact files the pipeline itself
    read-modify-writes**, per this module's own docstring ("A second writer racing it on either
    would lose updates or truncate a record mid-write"). `do_merge()`'s only protection against
    that race is a documented precondition ("Run ONLY when the pipeline is stopped") with **no
    runtime enforcement** — no check of `state/PIPELINE_STATE.json` for a running flag, no lock
    file, nothing stopping an operator from running `--merge` while the pipeline is live, at which
    point this module reproduces, in miniature, the exact hazard its own docstring warns against.
  Recommended fix: replace both hand-rolled writers with `silence.write_json` (which already gives
  pid+thread-unique temp names and `replace_retry`'s bounded backoff+observe-don't-raise
  semantics), and have `do_merge()` check the pipeline's own state file for a live/running
  indicator before proceeding, refusing (loudly) rather than trusting the operator to remember.
- HARD RULE 0 elsewhere in this file: `evidence[:600]` and `rationale[:900]` (lines 77, 87) are
  truncations of single free-form model-output *fields* for storage, not truncations of an
  enumerable roster/list — a materially different case from the `[:14]` entry-sample cap above.
  Flagged as a QUESTION rather than a violation, but worth the owner's eyes given the evidence
  field doubles as the provenance-verification text this project treats as load-bearing elsewhere.
- No subprocess spawns.

---

## Summary of severity

- **MAJOR (act on):** cascade_bridge claim-loop rotation gap (pool collapse root cause candidate);
  cascade_bridge `record_unrecognised` cross-process lost-update race; silence.py's `_handlers()`
  self-audit false-negative pair (`uses_exc` trivially true, `records` substring over-match);
  retry_synthesis.py's stale `[:14]` Hard-Rule-0 cap reintroducing a fixed owner-ruled bug;
  retry_synthesis.py's validate-after-truncate evidence bug; retry_synthesis.py's fixed-name
  non-atomic writers on both its own side file and the pipeline's shared record files.
- **MINOR:** `dead_forever()` permanent per-process cache outliving `PROOF_TTL`'s intent;
  `provider_error`'s single freshness window serving two different risk profiles; `replace_retry`
  orphaned temp files on persistent denial; `write_json` return values frequently ignored;
  `silence.note()`'s unlocked `_SINCE_FLUSH`/`_ATEXIT_ARMED` globals; estate.py's `.tmp`
  content-blind spot; estate.py's `if d:` masking a zero-records regression; feats_index.py's
  silent entry-name collision in `entries_by_norm`; propagation.py's dead `return 0`.
- **QUESTIONS for file owners outside this batch:** `pipeline.records()`'s yield contract
  (feats_index.py `audit()`); whether `evidence`/`rationale` field truncation in
  retry_synthesis.py ever clips load-bearing provenance text.

Live verification performed: ran `cascade_bridge.pool_exhausted/named_transient/empty_content`
and `unrecognised_open()` directly against `state/POOL_UNRECOGNISED.json`; queried
`state/cascade_scratch.db.bucket_state` directly for timing evidence; ran the AST substring bugs
in `silence._handlers()` against synthetic minimal reproductions and confirmed both misclassify.
