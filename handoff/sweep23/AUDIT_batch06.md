# AUDIT batch06 — magnitude.py, silence.py, estate.py, backfill.py, tells.py, scope.py

Full line-by-line read of all six files. Findings below; modules with nothing beyond
what's noted are marked CLEAN at the end of their section.

---

## magnitude.py (1026 lines, fully read)

### M1 — CONFIRMED (known, filed): `axis_score` flat-9.9 bug is on a live call path
`quantity_scores()` (line 224) calls `A.axis_score(x, anchor, axis)` at **magnitude.py:244**.
`quantity_scores()` is called live from `assay_entity()`:

```
709	    for ax, q in quantity_scores(ev, anchor).items():
710	        scores[ax] = q["score"]
711	        sheet[ax] = f"INSTRUMENT {q['measured']} = {q['si']:.3g} SI  <- {q['feat'][:120]}"
```

`scores[ax]` here unconditionally overwrites whatever the model/verify() gate produced for that
axis, and `assay_entity()` is the only entity-scoring entrypoint (`--one`, `--batch`, and
`calibrate()` all route through it). **VERIFIED**: the call path is live and unconditional —
every entity with a measured quantity (e.g. "40 tons") on an axis has that axis's score
overwritten by the instrument path, so if `axis_score` really returns a flat 9.9 at M10 (bug
M18, filed against assay.py, out of this batch's scope to re-verify), every M10 entity with any
measured quantity gets a flat 9.9 on that axis regardless of the actual magnitude. Not
re-derived here since assay.py is outside batch06; only the call-path liveness was in scope.

### M2 — VERIFIED (new): cross-process lost-update race on `data/ASSAYS.json`
`run_batch()` (magnitude.py:911-996), `work()` closure (952-987):

```
935	    done = {}
936	    if resume and os.path.exists(OUT):
937	        try:
938	            with open(OUT, encoding="utf-8") as f:
939	                done = json.load(f)
...
960	        with lock:
961	            done[h + "|" + n] = r
...
967	            tmp = OUT + ".tmp"
968	            with open(tmp, "w", encoding="utf-8") as f:
969	                json.dump(done, f, ensure_ascii=False)
...
975	            for attempt in range(5):
976	                try:
977	                    os.replace(tmp, OUT)
978	                    break
979	                except PermissionError:
980	                    ...
```

`done` is the FULL results dict, loaded once at process start (line 936-939) and never
re-read. Every completion re-serialises the *entire* process-local `done` and overwrites
`ASSAYS.json` with it. The `threading.Lock()` at line 960 only protects the multiple worker
*threads* inside one process — it gives no protection at all against a second OS *process*
running the same batch concurrently (e.g. two `--batch --host X` / `--batch --host Y`
invocations, which is exactly how this project's own convention would parallelise an
otherwise-serial multi-host sweep — see user's "use the full machine" standing note). If two
such processes run at once, each holds its own stale full snapshot of `done`; on every
completion each overwrites `ASSAYS.json` with its own snapshot, silently erasing whatever
entries the other process had already landed. This is a genuine cross-process lost-update,
distinct from (and not fixed by) the torn-write protection `replace_retry`-style atomic renames
provide — atomicity only guarantees the file is never seen half-written, not that two full-file
writers reconcile.

Contributing factor: this block reimplements `os.replace` + retry inline (975-983) instead of
calling `silence.replace_retry`, and uses a fixed tmp name (`OUT + ".tmp"`, line 967) rather
than `silence.write_json`'s pid+thread-qualified name — functionally harmless here (the
threading.Lock serialises intra-process access to that tmp path) but it is a duplicate,
un-DRY reimplementation of a primitive the project explicitly built to centralise this exact
logic, and it does not carry the extra protection `write_json` gives against a second writer's
tmp file colliding with this one's.

Severity: real but conditional on two batch processes targeting the same `ASSAYS.json`
concurrently, which is plausible operational usage (not proven to have occurred) — flagged as
VERIFIED for the code logic, UNVERIFIED for whether it has actually caused data loss in
practice.

### M3 — checked, not a bug: `candidates(ev, cap=None)` (line 396) and `queue(..., limit=None)` (line 821)
Both accept a truncating parameter (`cap=`, `limit=`). `candidates()`'s `cap` is **never** passed
by any caller (`grep` confirms the only call site, line 576, uses no `cap` arg) — so in practice
it never truncates the axis candidate lists; the "Ranked longest-first... never truncated"
docstring claim (line 407-409) holds in the live code. `queue()`'s `limit` is wired only to the
`--limit` CLI flag (line 1007), off by default (`None`), an explicit user opt-in rather than a
silent hidden cap — consistent with the project's own convention elsewhere (e.g. backfill.py's
`--cap`). Not a Hard Rule 0 violation.

### Other observations, no bug
- `_split_assay()`'s per-axis loop (451-482): `if not got: continue` on a failed `_ask()` call
  simply skips that block's contribution; `i` has already been advanced past the block, so this
  cannot infinite-loop. Fine.
- All nine `except` blocks (131, 145, 153, 234, 607, 630, 872, 879, 931, 940, 956, 979) call
  `silence.note(...)` (or print/log for 956, 979) before continuing — none are silent per the
  project's own definition. Consistent with the swallow discipline.
- `settled()` (885-908) correctly distinguishes a real finding ("no axis cleared its gate",
  saturation refusal, a scored result) from a transport failure (`DEFERRED`), matching its own
  docstring's stated purpose — read closely, does what it says.

---

## silence.py (425 lines, fully read) — the shared-write primitive, special focus applied

### CLEAN on its stated job
- `write_json()` (250-287): tmp name is `"%s.%d.%d.tmp" % (path, os.getpid(), _th.get_ident())`
  — unique per (path, pid, thread), which prevents two threads/processes racing on the *same*
  tmp file (the exact hazard found live in magnitude.py's `run_batch`, above — `write_json` is
  the fix that module doesn't use). On a failed dump it removes the tmp file and re-raises
  (280-286) rather than swallowing — an honest failure, not indistinguishable from success.
  `replace_retry` is called for the final rename and only ever returns `False` (never raises) on
  persistent `PermissionError`; a non-`PermissionError` `OSError` from `os.replace` is NOT
  caught by `replace_retry` (223-240, only catches `PermissionError`) and would propagate out of
  `write_json` too — this is narrower than the docstring's "Never raises on a denied replace"
  claim taken loosely, but the docstring is precise ("a denied replace" = `PermissionError`
  specifically) so this is not a contradiction, just a scope worth knowing. **VERIFIED** by
  reading; not exercised at runtime.
- `note()` (290-322): **VERIFIED it cannot raise** — the entire body is wrapped in a bare
  `try/except Exception: pass` (301-322), matching its own docstring ("deliberately total...
  every failure inside it is dropped on the floor"). Confirms the special-focus question
  directly: no, `note()` cannot itself raise and break a caller's `except` block.
- `replace_retry()` (223-240): backs off 0.3s * attempt on `PermissionError`, records via `note`
  only after the final attempt, returns `False`/never raises past that. Matches docstring.

### S1 — VERIFIED, low severity: unguarded global counter race in `note()`
```
246	_SINCE_FLUSH = 0
247	FLUSH_EVERY = 25
...
317	        _SINCE_FLUSH += 1
318	        if _SINCE_FLUSH >= FLUSH_EVERY:
319	            _SINCE_FLUSH = 0
320	            health.flush()
```
`note()` is called from `except` handlers all over the tree, including from inside
`ThreadPoolExecutor` workers (e.g. magnitude.py's `run_batch`/`work()`, estate.py's
`artifacts()`). `_SINCE_FLUSH += 1` is a non-atomic read-modify-write on a bare module global,
with no lock. Concurrent callers from multiple threads can lose increments, so the periodic
`health.flush()` may fire less often than every 25 recorded failures than intended (or,
less likely, double-fire). Consequence is bounded and low: `atexit.register(health.flush)`
(line 311) is armed on the very first call and still flushes everything at process exit, so no
failure is ever permanently lost — only the *mid-run* visibility cadence is degraded. Flagged
as a genuine but minor concurrency race (item 5 of the lens), not a data-loss bug.

No other findings. `_ensure_import`, `instrument`, `_handlers`, `audit`, `append_line` were all
read in full; each does what its docstring says, and `append_line`'s single `os.write` to an
`O_APPEND` fd for the shared `model_metrics.jsonl` ledger is a sound choice for sub-page-size
atomicity on Windows, exactly as its docstring argues.

**silence.py is CLEAN** on the two-writer contract and the "can the recorder itself raise"
question; only the minor S1 counter race is worth noting.

---

## estate.py (338 lines, fully read)

**CLEAN.** Read-only audit tool — walks the whole tree (`_walk`, no caps), opens and parses
every file (`inspect`), no sampling anywhere (its own docstring's central claim, and the code
matches it: no `[:N]` on any file listing, `artifacts()` iterates the full `paths` list into
`ThreadPoolExecutor.map`, nothing sliced). Every `except` branch records into the local `note()`
closure (which appends to the returned list — an actually-observed record, not silent) or into
`silence.note`. No shared-file writes anywhere in this module (nothing to check against the
two-writer contract — it's audit-only). No unguarded shared state touched by its
`ThreadPoolExecutor` (`inspect` is a pure function returning a dict per file, reduced
single-threaded afterward in `artifacts()`'s `for r in recs` loop at line 139 — no race).

---

## backfill.py (258 lines, fully read)

**CLEAN**, and notably self-documenting about its own fixed history:
- `roster()` (54-99): the docstring extensively narrates two past cap-related defects (a 600
  cap losing Goku alphabetically, a 12-subcategory cap losing anything past "Kryptonians") and
  the code matches the fix — `members()`'s inner loop pages via `cmcontinue` with no default
  stop, and the outer `roster()` only truncates via `[:limit]` (line 99) when an explicit
  `limit` is passed. **Confirmed by grep**: the only call site (backfill.py:153,
  `names = roster(host)`) never passes `limit`, so in the live `backfill_source()` path this is
  always a full, unbounded roster. No Hard Rule 0 violation in practice.
- `backfill_source()`'s `cap` (146, 165-166) is the same pattern: wired only to `--cap`
  (default `None`, "omit for everything, which is the intended use", line 208-209) — explicit
  opt-in, not a hidden default cap. `absent` is computed BEFORE the cap is applied (line 162,
  with an inline comment explaining a since-fixed defect where it was computed after and
  under-reported "absent" as 0 on every non-dry run) — verified the fix is in place: both the
  dry-run return (168) and real-run return (197-200) report the pre-cap `absent` correctly.
- `P.write_record(path, r)` (191) is the correct two-writer-contract primitive for record
  writes — compliant.
- Minor, non-blocking: `backfill_source()`'s `next((p, r) for p, r in records if r["source"] ==
  source)` (147) raises `StopIteration` uncaught if `source` doesn't match any record. The
  `--all` path (234-240) wraps the call in `try/except Exception`, so it's caught and reported
  there; the single-`--source` path (251-253) does **not** wrap it, so an unknown `--source`
  value crashes with a raw traceback instead of a clean message. This is a loud failure, not a
  silent one, so it's low priority under this project's own stated cost model ("A crash costs
  minutes... a silent null costs a full investigation") — noted for completeness, not filed as
  a defect of consequence.

---

## tells.py (215 lines, fully read)

### T1 — CONFIRMED (known, filed): alternation precedence makes the "but Y" requirement apply
to only the third alternative
```
70	    "not merely X but Y": r"\bnot merely\b|\bnot simply\b|\bnot just\b.{0,40}\bbut\b",
```
Regex `|` has the lowest precedence and splits the WHOLE pattern, giving three independent
alternatives: `\bnot merely\b`, `\bnot simply\b`, and `\bnot just\b.{0,40}\bbut\b`. Only the
third requires a following "but" within 40 characters — the first two fire on bare "not merely"
/ "not simply" with no reveal-clause needed at all. **VERIFIED** by reading the regex directly
and reasoning through Python `re` alternation precedence (no ambiguity here — this is standard
regex semantics, not a subtle edge case). Consequence: any legitimate sentence containing
"not merely" or "not simply" without a "but Y" clause (e.g. "This is not merely a rumor.") is
flagged as the "not merely X but Y" machine-tell — a false positive, exactly as filed.

No other structural or discourse pattern in the file has the same alternation-precedence flaw
(spot-checked all of STRUCTURAL and DISCOURSE; the rest are either single alternatives or use
non-capturing groups `(?:...)` correctly scoped inside a shared prefix/suffix rather than a
bare top-level `|`).

Rest of the module (LEXICAL/LEXICAL_FICTION lists, `_anchor()`'s sentence-boundary rewrite,
the control-character self-check at module load, `scan()`, `prompt_section()`) read clean and
consistent with their docstrings — the sentence-anchor fix described in the comment at line
124-126 is correctly implemented (`_anchor()` only swaps in `_SENTENCE_START` for patterns that
originally began with `^\s*`, leaving mid-text patterns alone).

---

## scope.py (152 lines, fully read)

### C1 — CONFIRMED (known, filed): a transient failure during `--build` permanently caches a
host as "no scope"
```
104	    out = {}
105	    if os.path.exists(OUT):
106	        out = json.load(open(OUT, encoding="utf-8"))
107	    todo = sorted({h for s, h in hosts.items() if h and h not in out
108	                   and not F.is_wikipedia(h)})
109	    for i, h in enumerate(todo, 1):
110	        try:
111	            sc = scope_for(h)
112	        except Exception:
113	            silence.note("scope.py:110")
114	            sc = None
115	        out[h] = sc
```
(current line numbers; the finding was originally filed against 108-118, same logic block, not
yet fixed.) **VERIFIED** by tracing both directions: on any exception from `scope_for` (network
timeout, API error, etc.) `sc = None` and `out[h] = None` is written unconditionally. On the
*next* `build()` run, `h not in out` is `False` (the key exists, with value `None`), so `h` is
permanently excluded from `todo` and never retried — indistinguishable in the cache from a host
whose wiki genuinely carries no scope signal (`scope_for` also legitimately returns `None` at
line 80 and line 97). A transient failure and a real "no scope" finding collapse into the same
stored value, which is the exact class of defect `silence.py`'s own docstring calls the
project's signature bug. Note: the file-level write itself is now atomic
(`silence.write_json(OUT, out, ...)` at line 119, with an inline comment dated 2026-08-25
confirming this was fixed) — only the retry-blindness remains open.

### C2 — VERIFIED (new, lower severity): evidence for a fiction's scope ceiling is capped
without ranking
```
68	QUERIES = ["cosmology universe world setting", "multiverse", "universe", "world"]
...
74	        d = F.api(host, {"action": "query", "list": "search", "srlimit": "3", "srsearch": q})
...
81	    pages = F.fetch(host, titles[:8])
```
Four queries at `srlimit=3` each yield up to 12 candidate titles (after the `size > 1200` filter
and dedup, line 76-78); only the first 8 are fetched (line 81) for the text that
`counts = {...}` (83) is computed from. `titles` is not ranked by relevance or size before the
slice — it is simply the order search results and queries happened to be iterated in, so the
`[:8]` can silently drop up to 4 of the 12 candidate cosmology-relevant pages a wiki search
surfaced, meaning the tier-count that decides a fiction's Magnitude **ceiling** (a value that
clamps the anchor of every entity from that source, per `host_ceiling()` in magnitude.py) is
computed from an arbitrary subset. This is smaller in scope than a roster/entity-listing
truncation (it's evidence-gathering for one scalar signal per host, not an enumeration of
catalogued entities), but it does fit the letter of the Hard Rule 0 pattern list (`srlimit=`
explicitly named) and the same "sample vs. truncation" reasoning the project applies
everywhere else — flagged as worth reviewing even though its blast radius is smaller than a
roster cap. **VERIFIED** the code contains the pattern; **UNVERIFIED** whether it has actually
changed a real ceiling outcome (would require live wiki data to test).

No other findings in scope.py. `ceiling_for()`, `main()`, and the tier table (`TIERS`,
`MIN_MENTIONS`) read clean and consistent with their stated purpose.
