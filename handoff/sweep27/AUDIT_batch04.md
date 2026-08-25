# BATCH 04 AUDIT — run27 comprehensive code sweep

Modules read in full, every line:
- src/foreman.py — 1287 lines
- src/endpoint.py — 394 lines
- src/context_budget.py — 278 lines
- src/burgs.py — 235 lines
- src/catalogue_models.py — 176 lines

Total: 2370 lines across 5 modules.

Read order and method: each file read top to bottom via `cat -n`/`sed -n` in full (no sampling),
cross-referenced against `src/silence.py` (the two-writer contract's implementation) and, for the
`_function_source` finding, verified against a full AST scan of every `.py` file in `src/` for
duplicate function/method names. All REMEDIES dispatch wiring in foreman.py was traced against
`round_once`'s actual break/always semantics rather than read in isolation.

---

## catalogue_models.py (176 lines)

### 1. [HIGH] [CONFIRMED] Hard Rule 0 cap on the human-facing "alternatives" list — line 158
```python
print(f"  {name}: " + ", ".join(r["models"][:10]))
```
This prints the current model list a person would use to pick a replacement for a stale model
ID. It is truncated to the first 10. This sits nine lines below a comment (146-150) that
documents FIXING the identical bug in the adjacent `available_sample` field:
> "THE WHOLE LIST. `[:8]` here was a Hard Rule 0 cap on the very field a person reads to pick
> the replacement for a retired model name... (run #26)"
The JSON record (`available_sample`, line 151) was corrected to hold the whole list. The
console print two dozen lines later, serving the exact same purpose for a human reading the
terminal instead of the JSON, was never revisited and still caps at 10. If a provider serves
more than 10 models and the 11th+ is the right replacement for a stale ID, the operator reading
the printed summary cannot see it — the precise failure the run #26 fix was written to prevent,
reintroduced two screens down in the same function.

### 2. [MEDIUM] [CONFIRMED] `last` exception leaks across retries / 200-empty vs unreachable collapse — lines 88-106 (known-open, confirmed)
```python
for url in tries:
    try:
        ...
        if ids:
            return {"provider": name, "url": url, "models": sorted(ids)}
    except Exception as e:
        silence.note("catalogue_models.py:ask_provider")
        last = f"{type(e).__name__}: {str(e)[:70]}"
return {"provider": name, "error": locals().get("last", "no model list endpoint")}
```
`last` is written only inside `except`. Failure scenario: URL 1 raises (e.g. connection reset),
setting `last`. URL 2 (e.g. `.../v1/models` after `.../models` 404s) succeeds with HTTP 200 but
an empty `data` array — `ids` stays `[]`, the `if ids:` branch is skipped, no exception is
raised on this iteration, `last` is NOT updated. The loop ends and the function returns
`locals().get("last")`, i.e. the URL-1 exception message — misreporting a provider that
answered 200-with-nothing as whatever transient error URL 1 happened to hit. Separately, if
BOTH urls return 200-empty (no exception ever raised at all), `last` was never set and the
function falls to the "no model list endpoint" default — collapsing "reachable, serves zero
models right now" and "genuinely unreachable" into the same generic string. Both are real,
traceable from the code as written.

---

## endpoint.py (394 lines)

### 3. [HIGH] [CONFIRMED] `_save()` writes the shared ENDPOINTS.json cache with a fixed-name temp file and no cross-process lock — lines 83-94
```python
def _save():
    with _LOCK:
        if _MEM is None:
            return
        try:
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            tmp = CACHE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(_MEM, f, indent=1, sort_keys=True)
            os.replace(tmp, CACHE)
        except Exception:
            silence.note("endpoint.py:save")
```
This is a raw `open(...,'w') + json.dump + os.replace` on `data/ENDPOINTS.json`, guarded only by
`threading.Lock` — process-local, giving zero protection against a second OS process (endpoint
detection is invoked from many different jobs with no single-instance guard). It also bypasses
`silence.replace_retry` entirely (a denied Windows rename from a live reader just raises inside
the `except Exception: silence.note(...)` and is silently swallowed — the write is lost, not
retried). Two hundred lines further down, this SAME FILE's `register()` function (356-393)
explicitly documents fixing exactly this defect class for `data/SOURCE_PAGES.json`:
> "The write itself goes through `silence.write_json`, not a hand-rolled fixed-name temp: this
> file is written from every process that probes an endpoint, and a shared `PAGES_FILE + '.tmp'`
> is the collision m100 retired repo-wide."
`_save()` for `CACHE` was never migrated to that pattern. Failure scenario: two processes call
`detect()` for different hosts concurrently (normal — this module has no lock file, no
single-instance guard, and is imported by feats.py, hostcheck.py, and others); both eventually
call `_save()`; both build the identical temp path `ENDPOINTS.json.tmp`; the loser's
`os.replace` either overwrites the winner's target with a partial file mid-write, or simply
loses its own newly-probed host verdict. `silence.py`'s own `write_json` docstring (silence.py
250-266) names this exact race as the reason it exists ("Two writers of the same path otherwise
collide on the temp file itself, and the loser can replace the winner's target with a partial
file").

### 4. [MEDIUM] [CONFIRMED] `fetch_html`'s `one()` swallows every exception with no 404/410 split — lines 327-334 (known-open, confirmed)
```python
def one(u):
    try:
        body = _get(u, timeout=45)
    except Exception:
        silence.note("endpoint.py:fetch_html")
        return u, None
    text = html_text(body)
    return u, (text if len(text) > 400 else None)
```
Its sibling function `fetch_raw`'s `one()` (204-224) was explicitly fixed for this — it catches
`urllib.error.HTTPError` separately and only treats `404`/`410` as genuine absence, logging
403/429/500/etc. under a different, distinguishable ledger key, with a comment citing "BUGS
m15" and calling the old collapsed behaviour "a transient wearing the face of settled fact."
`fetch_html` was never given the same treatment: a 403 (site temporarily blocking the crawler),
a 429 (rate limit), or a 500 from a one-author homebrew site reads through `fetch_html` exactly
like the page not existing, and is filed as such by the caller. Sibling function fixed, this one
left behind, same file.

---

## context_budget.py (278 lines)

### 5. [HIGH] [CONFIRMED] Unlogged silent `""` fallback on prompt-file read failure — lines 242-253 and 262-271 (known-open, confirmed and extended)
```python
if system_text is None:
    try:
        with open(os.path.join(PROMPTS, "system_style.txt"), encoding="utf-8") as f:
            system_text = f.read()
    except Exception:
        system_text = ""          # <- no silence.note(), no log, nothing
```
(same pattern repeated for `template_text` at 248-253, and again independently in `report()` at
262-266/267-271). Every OTHER swallowed exception in this codebase's sibling modules at least
calls `silence.note(site)`; these four sites don't even do that — a read failure here leaves no
trace anywhere. Traced effect: `feats_block_budget()` (the only production caller, via
`manifest_builder.py:331`) uses this value to compute `scaffold_chars`, which drives
`content_budget_chars()`. If the prompt files are transiently unreadable, the function treats
the ~18KB system prompt as zero-length scaffolding, producing an artificially LARGE packing
budget — the OPPOSITE of the "deliberately pessimistic" posture the module's own ~60-line header
argues for at length (assert_fits exists specifically because "being wrong in that direction
costs silently truncated evidence"). The blast radius is bounded by the fact that the real
safety net, `context_budget.assert_fits()` inside `generate.call_ollama` (generate.py:132-133),
is called with the REAL `system_prompt`/`user_prompt` strings at generation time, not values
derived from this cached `""` — so in practice this degrades packing efficiency and can trigger
a spurious `ContextOverflow` at generate time rather than causing actual silent truncation. Still,
it is a real, unlogged defect inside the one module whose entire purpose is to be honest about
degradation, and the second instance in `report()` (feeding `health`/preflight's human-facing
budget display) is a new instance not previously called out.

---

## burgs.py (235 lines)

### 6. [MEDIUM] [CONFIRMED] Print message contradicts the code directly above it — lines 190, 225-230
```python
worlds = WS.build_all()          # every world; Hard Rule 0
...
if args.write:
    p = os.path.join(HERE, "data", "BURGS_SAMPLE.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(per_world, f, indent=2,          # every world; Hard Rule 0
                  ensure_ascii=False)
    print(f"\nwrote {p} (sample of 50 worlds; the rest regenerate on demand)")
```
`per_world` is populated by iterating over `worlds` with no slicing anywhere in `main()` — both
adjacent comments explicitly say "every world; Hard Rule 0". The file that lands on disk holds
EVERY world's burg roll, not a sample of 50. The print statement directly below is stale: it
describes a cap ("sample of 50 worlds") that the code does not implement. Either this used to
slice to 50 worlds and the message was never updated when the cap was removed (matching this
project's own "Hard Rule 0" cleanup pattern seen elsewhere), or the filename/message imply a
scope the data doesn't have. Either way, an operator trusting the printed line would materially
misjudge what `BURGS_SAMPLE.json` contains.

### 7. [MEDIUM] [CONFIRMED] Non-atomic hand-rolled write of BURGS_SAMPLE.json — lines 226-229
```python
with open(p, "w", encoding="utf-8") as f:
    json.dump(per_world, f, indent=2, ensure_ascii=False)
```
Raw `open('w')+json.dump`, not `silence.write_json`. Truncate-then-fill: a crash or interrupt
mid-write leaves a corrupt/partial JSON file on disk. Only one known writer today (this CLI
path), so the concurrency risk is low relative to the other findings in this batch, but it's the
same hand-rolled pattern `silence.write_json` exists to retire, and per Hard Rule 4 shared
`data/` files are supposed to land only through `replace_retry`/`write_json`.

### 8. [LOW] [SUSPECTED] `limit or n` falsy-zero bug — line 147
```python
for k in range(1, (limit or n) + 1):
```
An explicit caller of `burgs_for(seed, features, limit=0)` would get the FULL unlimited roll (n
settlements) instead of zero, because `0 or n` evaluates to `n`. Checked every current caller in
the repo (`verify_math.py`, `navtree.py`, `burgs.py` itself) — none passes `limit=0` today, so
this is dormant, but it is a real defect in a public function's contract.

### 9. [LOW] [SUSPECTED — may be deliberate] Two disconnected floor constants — lines 85, 106, 148
`HAMLET_FLOOR = 40` (line 85, "the smallest thing the record still calls a burg") is used to
derive the settlement COUNT `n` in `burg_count()` (line 106: `n = int((p1/HAMLET_FLOOR)**...)`),
but the per-rank population clamp in `burgs_for()` uses a DIFFERENT hardcoded floor, 30 (line
148: `pop = max(30, int(p1/(k**ZIPF_Q)))`), not `HAMLET_FLOOR`. For `condition` factors above 1.0
(e.g. `"thriving"`: ×1.15), `burg_count()` inflates `n` well past the rank at which the raw
rank-size formula naturally reaches population 40, so the extra tail ranks fall below 40 (toward
30) and get clamped to the disconnected 30 floor rather than the documented 40 — producing a
cluster of identical pop=30 settlements not actually derived from the rank-size law for those
worlds. This mirrors the module's own acknowledged intentional tail-shrinking for `"ruined"`
worlds, so it may be deliberate, but two different constants for what both docstrings describe
as the same concept looks more like an oversight than a second designed parameter. Worth
confirming with whoever wrote the `condition` factor table.

### 10. [LOW] Cosmetic-only slice — line 214
`w0['designation'][:60]` truncates a display header string in a print statement only (not
written data). Flagged for completeness against Hard Rule 0's literal wording ("ANY cap... on
anything"), but this does not affect any stored or returned data.

---

## foreman.py (1287 lines)

### 11. [HIGH] [CONFIRMED] `_function_source` can silently patch the WRONG function on a name collision — lines 794-806
```python
def _function_source(path, symbol):
    ...
    want = symbol.split("(")[0].split(".")[-1].strip()
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)) and node.name == want:
            ...
            return "".join(lines[start:end]), start, end
    return None, None, None
```
Any class qualifier on the finding's `symbol` (e.g. `"ClassName.method"`) is discarded before
matching (`.split(".")[-1]`), and `ast.walk()` searches the WHOLE module — every class, every
nested scope — returning the FIRST FunctionDef/AsyncFunctionDef with that bare name. This is not
hypothetical: an AST scan of every file in `src/` for duplicate `(file, function-name)` pairs
found real collisions, including one inside this very batch:
```
endpoint.py  one   2      (nested `one()` defined inside BOTH fetch_raw at line 200 AND
                            fetch_html at line 327)
hostcheck.py one   3
estate.py    note  4
verify_math.py __init__ 5
```
A finding naming symbol `"one"` against `endpoint.py` would resolve to whichever `one` `ast.walk`
happens to visit first — not necessarily the one the finding is actually about. If the model
"fixes" that wrong function, `attempt_patch` (~line 995: `lines[start:end] = [new]`) splices the
patched text into the WRONG line range, potentially overwriting a working, unrelated function
with a "fix" meant for a different one. `_checks_pass` (843-874) only verifies the module still
imports and that `verify_math.py`/`allsweep.py --quick` pass — it never confirms the intended
symbol was the one actually changed, so a misapplied patch to a same-named sibling can pass every
gate here undetected as long as the accidental edit doesn't happen to break something global.

### 12. [HIGH] [CONFIRMED] Systemic fixed-name temp files on shared JSON writes, project's own fix not applied here — lines 150/158, 255/262, 265/267, 715, 1041, 1126, 1247
Every shared-state write in this file follows the same two-step pattern: build a temp file at a
FIXED name (`path + ".tmp"`), write it with a plain `open('w')`, then call
`silence.replace_retry(tmp, path)` for the final rename. The rename step is correctly atomic and
retried — but none of these use `silence.write_json`, whose own docstring (`silence.py:250-266`)
explains this is not equivalent:
> "THE TMP NAME CARRIES PID AND THREAD, which the older hand-rolled `path + '.tmp'` sites did
> not. Two writers of the same path otherwise collide on the temp file itself, and the loser can
> replace the winner's target with a partial file."
Sites in this file, all using the same vulnerable fixed-name pattern:
- 150/158 — `data/POOL_PROOF.json` (`reprove_pool`)
- 255/262, 265/267 — `state/failures_archive.json`, `state/failures.json` (`triage_swallowed`) —
  the comment at lines 351-354 states outright: "state/failures.json is the highest-traffic
  shared file in the project... EVERY process read-modify-writes it through health.flush()" —
  i.e. this file's own comments assert genuine multi-writer traffic, yet the temp name is fixed
- 715 — `state/OLLAMA_RESTARTS.json` (`restart_ollama`)
- 1041 — `data/OVERWATCH.json` (`_retire`; see also #13)
- 1126 — `FOR_OWNER.md` (`owner_queue`)
- 1247 — `data/FOREMAN.json` (`round_once`)
The project has a documented history of exactly the precondition this needs: `kill_duplicate_jobs`'s
own docstring (~490-497) describes two supervisors having spawned two foremen that "killed each
other every three minutes for half an hour" on 2026-08-24 — i.e. duplicate concurrent foreman
processes are a real, observed failure mode, not a hypothetical one. The comment at line 1122
("Atomic, like every other shared write in this file") states these writes are safe without
qualifying that only the rename is atomic; the temp-file collision itself is not addressed
anywhere in this module.

### 13. [HIGH] [CONFIRMED — known-open, extended] `_retire()` matches by (module, symbol) with no break, and races a second live writer — lines 1026-1050
```python
for fid, v in (led.get("findings") or {}).items():
    if (v.get("module") == finding.get("module")
            and v.get("symbol") == finding.get("symbol")
            and v.get("state") == "open"):
        v["state"] = "retired"
        v["retired_why"] = finding.get("why", "unactionable")
```
Confirms the known-open item and adds two concrete details: (a) there is no `break` after a
match, so if OVERWATCH.json ever holds MORE THAN ONE open finding for the same `(module,
symbol)` pair — two distinct defects reported in the same function is entirely possible — a call
to retire ONE of them silently retires ALL findings sharing that pair, whatever their individual
`why`/severity. (b) the read-modify-write (open the file, mutate the dict, write it back) has no
lock beyond the final `replace_retry` swap, while the surrounding comment (1036-1038) itself
names `overwatch` as a second live writer of the same file ("overwatch owns this file and
persists after every module it reviews"). If overwatch.py appends a fresh finding between
foreman's read and its write, foreman's write — built from the earlier snapshot — silently
discards it. This is a genuine cross-process TOCTOU race on the file, using the same fixed-temp
pattern flagged in #12.

### 14. [HIGH] [CONFIRMED] `reprove_pool`'s false-success at 0-of-N buckets neutralizes its own paired remedy — line 753, in combination with lines 160-161
`REMEDIES["the library's counters are moving"] = [reprove_pool, restart_reader]`. Confirmed the
known-open bug at 160-161 (`reprove_pool` returns `did=True` unconditionally once the write
lands, regardless of `len(ok)`), and traced its interaction with `round_once`'s dispatch loop
(~1189-1200: `if did and not always: ... break`). Because `reprove_pool` reports success on
almost every call, this list's `break` fires after `reprove_pool` runs, and `restart_reader`
essentially never executes for this standard — even in the rare case where bouncing the reader
really would be the right fix. The paired remedy is effectively dead code as long as the upstream
bug at 160-161 stands.

### 15. [HIGH] [CONFIRMED — known-open, extended with new dispatch evidence] "corpus read is progressing" routes straight to killing the reader with no pool check — line 759, combined with 342-386
`REMEDIES["corpus read is progressing"] = [restart_reader]` — a single remedy, no pool-health
gate. Contrast with `run_charter_regression` (637-663), which explicitly reads
`data/POOL_PROOF.json` and refuses to dispatch when fewer than 3 buckets answer
("pool too thin for the regression"). `restart_reader` has no equivalent check: it SIGTERMs any
process matching the `read.py --run` fragment purely because the standard fired, without asking
whether the reader is actually wedged versus simply starved by a dead pool. Per
`_restart_horizon()`'s own documentation (289-329), `read.py` is not in the supervisor's
STANDING set, so a wrongly-killed-but-actually-fine reader does not restart for "42-44 min
typically and 4h at worst" — this remedy can convert a temporary pool outage into a multi-hour
reader outage. This sharpens the supervisor's known-open item with the exact REMEDIES-table
line and the missing-gate comparison against the one sibling remedy that DOES check pool health.

### 16. [MEDIUM] [SUSPECTED / question] Same blind spot likely applies to `kill_stalled_job` for non-reader jobs — line 736, 391-459
`REMEDIES["every running job is advancing"] = [kill_stalled_job]` has the identical structure:
no pool-health check before SIGTERM'ing whatever job the standard names as stalled. If catalogue,
sweep, or charter-regression jobs stall for the same pool-starvation reason the reader does
(plausible, given they draw from the same pool per this file's own comments elsewhere), this
remedy would kill them too without first trying to fix the actual cause. Flagged as a question,
not a certainty — I don't have direct evidence from this batch that these other jobs' stalls are
as pool-driven as the reader's.

### 17. [MEDIUM] [SUSPECTED / question] A successfully-patched finding is never retired — lines ~991-993 vs ~1233
`attempt_patch`'s success branch (`{"ok": True, "why": "patched and verified", "delta":
changed, "backup": backup}`) sets no `"retire"` key, so `round_once`'s
`if res.get("retire") and not dry: _retire(f)` never fires for it — unlike the "model says the
claim is wrong" and "no change proposed" branches, which both explicitly set `"retire": True`.
A finding that was genuinely fixed stays marked `"open"` in OVERWATCH.json and would be
re-attempted next round (re-asking the model to "fix" an already-fixed function), UNLESS
overwatch.py's own next scan independently re-examines the function and stops reporting the
now-absent defect on its own. That may be the intended design (the module that verifies code
correctness closes its own findings, rather than foreman trusting its own patch) — flagging as a
question since `overwatch.py` is outside this batch and I can't confirm its re-scan behaviour.

### 18. [MEDIUM] [CONFIRMED] Undefended `[-200:]` cap on FOREMAN.json's operational history — line 1247
```python
json.dump(prev[-200:], f, indent=1)
```
Every round, `data/FOREMAN.json`'s round-history array is truncated to the most recent 200
entries before being written back — older rounds are permanently discarded. No comment defends
or even acknowledges this as a deliberate rotation policy (contrast with the rest of this file,
which is scrupulous about documenting every deliberate limit). Under this project's own stated
Hard Rule 0 ("no cap... EVEN IF it looks reasonable," and this specific project's CLAUDE.md:
"No limit, no cap, no sample... on a roster, a page list, a chunk list, or an entry list"), an
unremarked log-rotation cap is exactly the shape the rule targets, even though log rotation is
one of the more defensible reasons for a cap to exist.

### 19. [LOW] Display-only truncation, not a data-loss cap — line 929
`"preview": new[:400]` in `attempt_patch`'s dry-run branch only affects what's shown to a human
in `--patch --dry` output; the real patch application later uses the full `new` string. Noted
for completeness, not treated as a substantive finding.

---

## Summary of known-open items status

- foreman.py:342-384,387-460 (reader killed for pool stalls) — **CONFIRMED**, and sharpened with
  the exact REMEDIES dispatch table entries (findings 14, 15) showing precisely how and why.
- foreman.py:161-162,753 (reprove_pool returns True at 0 buckets) — **CONFIRMED**, and shown to
  additionally neutralize its own paired remedy (finding 14).
- foreman.py:1016-1038 `_retire()` matches by (module,symbol) — **CONFIRMED**, with the missing
  `break` and the cross-process race against overwatch.py added (finding 13).
- endpoint.py:327-334 fetch_html's one() swallows everything — **CONFIRMED** (finding 4).
- catalogue_models.py:88-106 200-empty/unreachable collapse, `last` leak — **CONFIRMED**
  (finding 2).
- context_budget.py:242-253 prompt-file read failure defaults to "" — **CONFIRMED**, and a
  second unlogged instance in `report()` (262-271) was found (finding 5).
