# Batch 04 audit — foreman.py, endpoint.py, context_budget.py, burgs.py, audit.py, compress_store.py

Run #28, sweep batch 04. Every line of all six modules read (foreman.py 1287, endpoint.py 395,
context_budget.py 279, burgs.py 236, audit.py 178, compress_store.py 66 = 2441 lines). NEXT_STEPS.md
section 3 read first; findings cross-checked against it and marked KNOWN or NEW below.

---

## src/foreman.py (1287 lines)

### KNOWN — still open: every shared JSON write uses a fixed-name temp
NEXT_STEPS §3 "Concurrency/contract": `foreman.py:150/158,255-267,715,1041,1126,1247`.
Verified live at every cited site plus the ones the comment collapses together:

- `foreman.py:150` (`reprove_pool`) — `_pp = ...POOL_PROOF.json`; `with open(_pp + ".tmp", "w", ...)`
  then `silence.replace_retry(_pp + ".tmp", _pp)` at :158. Rename goes through the safe helper;
  the *write* is still a bare fixed-name temp shared by every process that calls this remedy.
- `foreman.py:255` and `:265` (`triage_swallowed`) — `open(arch + ".tmp", "w")` then
  `open(path + ".tmp", "w")` (state/failures.json's temp), both fixed names, on the file the
  module's own comment calls "the highest-traffic shared file in the project."
- `foreman.py:715` (`restart_ollama`) — `tmp = RESTART_STAMP + ".tmp"`, bare `open(tmp,"w")`.
- `foreman.py:1041` (`_retire`) — `tmp = path + ".tmp"` for `data/OVERWATCH.json`.
- `foreman.py:1126` (`owner_queue`) — `open(FOR_OWNER + ".tmp", "w")` for `FOR_OWNER.md`, which
  `publish.py` copies into the export tree on its own loop per the adjacent comment.
- `foreman.py:1247` (`round_once`) — `open(LOG + ".tmp", "w")` for `data/FOREMAN.json`, read by
  `overnight.foreman_report()` on its own clock.

All six sites do call `silence.replace_retry` for the rename and check its return value (an
improvement over raw `os.replace`), so the *rename* half of the two-writer contract is honored.
The *write* half is not: a fixed `X.tmp` name shared across every process that runs this same
remedy is still the collision `silence.write_json`'s docstring says was closed repo-wide — two
concurrent foreman rounds (e.g. an interactive `--go` run overlapping the scheduled one) writing
the same `.tmp` path can interleave, and the loser's `replace_retry` then renames a
partially-overwritten temp file onto the real one. Severity: MED (bounded by `replace_retry`
catching a *failed* rename, but not a *torn* one two racing writers produce before either
renames).

### KNOWN — confirmed with concrete evidence: `_function_source` drops class qualifiers, walks by bare name
NEXT_STEPS §3: "`:794-806` `_function_source` drops class qualifiers and walks by bare name --
`endpoint.py` has two functions named `one` today, so the model could be asked to fix the wrong
one."

`foreman.py:795-808`:
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
Verified directly against this batch's own `endpoint.py`: `def one(t):` is nested inside
`fetch_raw` at `endpoint.py:200`, and a *second, unrelated* `def one(u):` is nested inside
`fetch_html` at `endpoint.py:327`. `ast.walk()` is breadth-first from the module root, and since
`fetch_raw` is defined (and therefore enqueued) before `fetch_html`, `_function_source(path,
"one")` deterministically returns **`fetch_raw`'s `one`, never `fetch_html`'s**, regardless of
which one an overwatch finding's `symbol` field actually names (the qualifier is stripped by
`symbol.split(".")[-1]` before the search, so `fetch_html.one` and `fetch_raw.one` become the
same lookup key `one`). A finding filed against `endpoint.py`'s `fetch_html.one` (e.g. the
already-known "swallows every exception" defect) would have `attempt_patch` hand the model
`fetch_raw`'s `one` instead and, if the model "fixes" it and the patch passes `_checks_pass`,
silently rewrite the wrong function while leaving the actually-defective one untouched. STILL
OPEN. Severity HIGH (silently patches the wrong code, and would report success).

### NEW — `restart_ollama`'s rate-limit stamp is unlogged and fails toward *more* restarts
`foreman.py:690-695`:
```python
try:
    with open(RESTART_STAMP, encoding="utf-8") as f:
        st = json.load(f)
except Exception:
    st = {"count": 0, "last": 0}
if time.time() - st.get("last", 0) < 1800:
    return False, (...)
```
The docstring for `restart_ollama` promises "at most one automated restart per 30 minutes...
escalates to the owner instead of being restart-looped into invisibility." If `RESTART_STAMP`
(`state/OLLAMA_RESTARTS.json`) is unreadable at the moment this check runs — corrupted mid-write
by the same function's own fixed-name-temp write at :715 (see the KNOWN finding above, which is
exactly the write that populates this file), a Norton object-lock, a torn read racing a
concurrent foreman round — the code defaults to `last: 0`, i.e. "never restarted," which makes
`time.time() - 0 < 1800` False and the 30-minute cooldown is silently bypassed. This is the one
`except Exception` in the entire file that calls **no `silence.note`** — every sibling except
block in this module logs; this one is fully silent, so there is no trail to notice it happened.
Failure scenario: the stamp file becomes transiently unreadable right after a restart (plausible,
since it's written via the same fixed-name-temp pattern flagged above, which is itself racy under
concurrent foreman rounds) → the next round reads a corrupt/missing stamp → treats it as "never
restarted" → restarts Ollama again inside the 30-minute window the docstring says cannot happen →
if the daemon is genuinely wedged for a structural reason, this reopens exactly the
"restart-looped into invisibility" failure the rate limit exists to prevent. Severity MED (the
consequence is a rate-limit bypass, not data loss, but it directly undoes the one safety property
the function's docstring advertises).

### NEW — `triage_swallowed`'s logged "top classes" detail is capped at 3, hiding the pattern
`foreman.py:230-232`:
```python
top = sorted(d.items(), key=lambda kv: -kv[1])[:3]
total = sum(d.values())
detail = "; ".join(f"{k} x{v:,}" for k, v in top)
```
This is exactly the shape NEXT_STEPS lesson 16 names as the sharpest defect class of the whole
project ("A CAP ON A DIAGNOSTIC HIDES THE PATTERN, NOT JUST THE ROWS" — citing `standards.py:952`
showing 3 of 14 rows when all 14 shared one cause). Here the *archived* data is not capped (the
full dict `d` is written to `failures_archive.json` intact), but the only thing a human or the
operational log (`FOREMAN.json`, printed to stdout every round) ever sees is the top-3 detail
string. If, say, 12 distinct failure classes are all instances of the same one upstream defect (a
plausible shape per lesson 16's own example), the printed remedy result — the actual sentence a
person reads to decide whether the spike is one bug or twelve — only ever names the 3 largest
classes and silently omits whether the rest share their shape. Severity MED (data survives in the
archive file; the live diagnostic a human actually reads does not).

### LOW / speculative — DENYLIST is reused for two unrelated purposes
`foreman.py:90` defines `DENYLIST` as "files a model may never edit" for the patch lane (checked
in `attempt_patch` at :919). `kill_duplicate_jobs` at `foreman.py:498` reuses the *same* constant
to decide which job names are exempt from duplicate-process killing (`if p == os.getpid() or job
in DENYLIST: continue`). These are two different safety properties (code-patch-immunity vs.
process-dedup-immunity) sharing one name and one set; extending DENYLIST for one purpose silently
changes the other. No live misbehavior confirmed — today's DENYLIST members are plausibly correct
for both uses — but the coupling is undocumented at either site.

---

## src/endpoint.py (395 lines)

### KNOWN — still open: `fetch_html`'s `one()` swallows every exception
NEXT_STEPS §3: "`endpoint.py:327-334` — `fetch_html`'s `one()` swallows every exception;
`fetch_raw` got the 404/410 split (m15) and this did not."

`endpoint.py:327-334`:
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
Confirmed unchanged. Contrast with the sibling `fetch_raw.one` at `:200-227`, which was hardened
(same file, same module, same day per its own comment) to distinguish 404/410 ("absent") from
every other HTTP status ("refused") in the `silence.note` tag, specifically because "a 403, a
429 or a 500 reached the caller as the exact same answer a genuine 404 gives." `fetch_html.one`
still collapses a genuine 404 and a mid-scrape 429/403 rate-limit into the identical
`endpoint.py:fetch_html` tag and identical `(u, None)` return. STILL OPEN.

### KNOWN — still open: `_save()` fixed temp name + `threading.Lock`, never migrated
NEXT_STEPS §3: "`endpoint.py:83-94` — `_save()` fixed temp name + `threading.Lock`, never
migrated."

`endpoint.py:83-94`:
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
        return
```
Confirmed unchanged: fixed-name `CACHE + ".tmp"`, `threading.Lock` (intra-process only, no
cross-process protection), and a bare `os.replace` with no retry — none of `silence.write_json`
/ `silence.replace_retry`'s guarantees. Notably this is a *within-file* double standard: the same
module's `register()` function (`:356-394`, for `SOURCE_PAGES.json`) was rewritten to go through
`silence.write_json` specifically because of a prior incident, and its own docstring explains why
(torn/unreadable reads must not silently republish a smaller registry). `_save()`, guarding
`ENDPOINTS.json` — probed and written from every host-detection call across however many worker
processes run `feats.py`/`hostcheck.py` concurrently — never received the same treatment. STILL
OPEN.

---

## src/context_budget.py (279 lines)

### KNOWN — still open: prompt-file read failure defaults to `""` with no log
NEXT_STEPS §3: "`context_budget.py:242-271` — prompt-file read failure defaults to `""` with no
log, in both `feats_block_budget()` and `report()`; live via `manifest_builder.py:331`."

`context_budget.py:242-253` (`feats_block_budget`) and `:262-271` (`report`) both do:
```python
try:
    with open(os.path.join(PROMPTS, "system_style.txt"), encoding="utf-8") as f:
        system_text = f.read()
except Exception:
    system_text = ""
```
with no `silence.note` in either except block. Confirmed unchanged and confirmed live:
`manifest_builder.py:331` calls `_CBUD.feats_block_budget(cfg)` with no `system_text`/
`template_text` arguments, so a transient read failure at that exact call site is invisible.

Traced the actual failure mode further than the KNOWN note states, and it is a genuine but
*bounded* risk, not silent truncation: a read failure here makes `feats_block_budget` treat the
scaffolding as smaller than it really is (empty system prompt ⇒ smaller `scaffold_chars` ⇒
*larger* computed content budget), which is the dangerous direction the module's own header
explicitly warns against ("being wrong in [the permissive] direction... costs silently truncated
evidence"). `manifest_builder.py` then packs a feats block sized to this inflated budget. But
`generate.py`'s `call_ollama` (`:124-133`) independently loads the real `system_style.txt` via
`load_prompt_templates()` — which has **no** try/except and crashes loudly if the file is
genuinely missing — and calls `_CBUD.assert_fits()` against the *real* system prompt and the
*already-packed* user prompt just before sending. Because that final gate re-measures the actual
text rather than trusting the earlier budget, an over-packed block from a transient read glitch
at pack time fails **loudly** (`ContextOverflow`) at send time rather than being silently
truncated by Ollama. The KNOWN defect stands (silent `""` fallback, no log, live via
`manifest_builder.py:331`) but its blast radius is a mis-sized/rejected block, not the silent
data loss the module exists to prevent — worth noting since the evidence standard asks for the
actual failure scenario, and this one is milder than the raw description implies.

Additionally, `report()`'s own docstring (`:261`) claims "Used by health/preflight and by the
ledgers" — grepped the entire `src/` tree and confirmed `context_budget.report` has **zero
callers anywhere** in the codebase. `health.py` does have a function named `check_context_budget`
(`health.py:168-186`), but it does not call into `context_budget.py` at all — it hand-rolls its
own, different arithmetic (`len(R.SYSTEM)/4`, `R.CHUNK/3.7`, flat `reply=700`) against `read.py`'s
reader-chunk budget, a different subsystem than the feats/chapter generation budget
`context_budget.py` governs, and does not apply any of `context_budget.py`'s measured corrections
(`JOB_OVERHEAD_CHARS`, `METADATA_INFLATION`). So `context_budget.py` and `health.py` maintain two
independently-derived, disagreeing implementations of "does this prompt fit its window," and the
docstring's claim that `report()` is the one health/preflight actually calls is false. NEW,
severity LOW-MED (dead code with a false "used by" claim; not itself a runtime bug, but it means
`health --preflight`'s context-budget check is running unaudited, less-accurate arithmetic instead
of the module built and measured specifically for this).

---

## src/burgs.py (236 lines)

### KNOWN — still open: raw write to shared file, no two-writer contract
NEXT_STEPS §3: "`burgs.py:226-229`... raw writes to shared files."

`burgs.py:225-229`:
```python
if args.write:
    p = os.path.join(HERE, "data", "BURGS_SAMPLE.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(per_world, f, indent=2, ensure_ascii=False)
```
Confirmed unchanged: no temp file, no `silence.write_json`/`replace_retry`. STILL OPEN.

### NEW — the write's own print message contradicts what the code just wrote
`burgs.py:197-230`:
```python
worlds = WS.build_all()          # every world; Hard Rule 0
...
per_world = {}
for w in worlds:
    ...
    per_world[w["designation"]] = bs
    total += len(bs)
...
if args.write:
    p = os.path.join(HERE, "data", "BURGS_SAMPLE.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(per_world, f, indent=2, ensure_ascii=False)
    print(f"\nwrote {p} (sample of 50 worlds; the rest regenerate on demand)")
```
`per_world` is built from the entire, uncapped `worlds` list (Hard Rule 0 compliant — the comment
on the `WS.build_all()` call even says so), so `BURGS_SAMPLE.json` actually receives every
world's burg roll, not 50. The `--write` print statement's claim ("sample of 50 worlds; the rest
regenerate on demand") is stale — almost certainly left over from an earlier version that did
slice to 50 before Hard Rule 0 was enforced project-wide — and now directly contradicts what the
code two lines above it just did. No downstream consumer currently reads `BURGS_SAMPLE.json`
(grepped `src/*.py`), so this is not live data corruption today, but it is a comment/print that
actively misdescribes the code's behavior on the exact axis (a data cap) this project audits most
aggressively, and it risks misleading a future maintainer into "fixing" the message by actually
adding the cap it currently only claims to have. NEW, severity LOW-MED.

### NEW — `burgs_for`'s `limit or n` mishandles an explicit `limit=0`
`burgs.py:147`:
```python
def burgs_for(world_seed, features, limit=None):
    ...
    for k in range(1, (limit or n) + 1):
```
`limit or n` treats `limit=0` the same as `limit=None` (both falsy), so a caller that explicitly
asks for zero burgs gets the full `n`-burg roll instead. No current caller passes `limit=0`
(`burgs.py`'s own `main()` never sets it; `verify_math.py`'s calls use `limit=3`/`limit=200`), so
this is unexercised today — flagging as a latent edge-case bug per the audit lens ("wrong
operator... wrong edge cases"), not a live incident. Severity LOW, speculative impact (would need
a future caller passing `limit=0`).

---

## src/audit.py (178 lines) — BACKSCAN

### NEW — HIGH: the exhaustive INVARIANTS pass prints only 4 examples per violation class
`audit.py:139-148` (`main`):
```python
for k in sorted(fails, key=lambda x: -len(fails[x])):
    v = fails[k]
    total_f += len(v)
    rate = len(v) / max(1, stats["entries_catalogued"])
    print(f"\n  {k}")
    print(f"     {len(v):,} occurrences ({rate:.2%} of catalogued entries)")
    for x in v[:4]:
        print(f"       - {x}")
    if len(v) > 4:
        print(f"       ... and {len(v)-4:,} more")
```
This is the exact shape NEXT_STEPS lesson 16 calls the sharpest defect class the last several
sweeps have found ("A CAP ON A DIAGNOSTIC HIDES THE PATTERN, NOT JUST THE ROWS," citing
`standards.py:952` printing 3 of 14 rows when all 14 shared one cause and a prior run "read the
top row, chased it alone, and recorded the rest as genuinely unexplained"). `audit.py`'s own
module docstring (`:5-14`) draws a deliberate line between two passes: "INVARIANTS run over EVERY
entry... exhaustive, and the only way to catch a rule that quietly stopped applying" versus
"SAMPLE a seeded random draw... Invariants catch violations of rules we thought to write; reading
catches the rest." The random SAMPLE section further down (`:152-172`) is honestly labeled as a
sample and is not a Hard Rule 0 problem. The INVARIANTS section is not honestly labeled: it
claims exhaustiveness in its own header comment and then silently shows only the first 4 of
however many violations exist per category (`v[:4]`), captioned only as "... and N more" with no
indication of whether those N more share the shown examples' shape or are a different failure
entirely. The occurrence *count* and *rate* are correctly computed from the full uncapped list
(`len(v)`, not `len(v[:4])`), so the numbers are honest — but the qualitative detail a human
would use to diagnose *what kind* of violation is happening is capped exactly where lesson 16
says the danger is greatest, and in the one tool in this batch whose entire stated purpose is
letting "a person read actual rows" outside the code that's supposed to enforce the rule. Concrete
failure scenario: a single upstream defect produces (say) 40 "entry: BAND WITH NO SCALE NOTE"
violations across many different sources; if the first 4 printed happen to come from one source,
a reader would very plausibly (as happened with `standards.py:952` per lesson 16) chase that one
source's cause and miss that the other 36 are the identical shape from a different source. Not
previously listed in NEXT_STEPS §3 for this module — NEW. Severity HIGH given how explicitly and
repeatedly this exact pattern is called out as the project's worst recurring defect class.

---

## src/compress_store.py (66 lines)

No KNOWN findings apply (module not mentioned in NEXT_STEPS.md). No HIGH/MED findings found after
full read; module is small and each function does one thing correctly (gzip/zstd fallback,
content-addressed hashing, load/store round-trip all check out against direct reading).

### LOW / speculative — `store()` writes the compressed blob directly, no atomic replace
`compress_store.py:43-44`:
```python
with open(path, "wb") as f:
    f.write(blob)
```
No temp-file-plus-rename. Because `path` is content-addressed (`{sha256[:32]}.{ext}`), two
processes computing the *same* hash would write byte-identical content, so this is not a classic
read-modify-write race — but it is not atomic either: a concurrent `load()` (`:55-57`, plain
`open(path,"rb").read()`) reading the same path while a second `store()` for the same hash is
mid-write could observe a partial file. Traced the only current caller
(`generate.py:386`, via `catalog.py`/`generate.py`) and found no evidence `generate.py` is ever
run as more than one concurrent instance against the same manifest (no `ThreadPoolExecutor`/
`ProcessPoolExecutor` in `generate.py`, and `overnight.py:691` starts it as a single job named
"prose"), so this is not confirmed exploitable today. Flagging as speculative/LOW since the
pattern itself (bare `open(path,"wb")` on a file another process may read concurrently) is exactly
the shape the two-writer contract exists to rule out, and nothing in the code prevents a future
caller from parallelizing `generate.py`.

---

## Summary table

| Severity | Status | Location | Claim |
|---|---|---|---|
| HIGH | NEW | audit.py:139-148 | INVARIANTS pass (claims exhaustive) prints only 4 examples per violation class, hiding whether the rest share the shown shape |
| HIGH | KNOWN, confirmed w/ new evidence | foreman.py:794-808 | `_function_source` matches by bare name; proven against this batch's own `endpoint.py`, which has two distinct `one()` functions — a patch would silently land on the wrong one |
| MED | KNOWN, still open | foreman.py:150/158,255-267,715,1041,1126,1247 | every shared JSON write still uses a fixed-name temp before the (checked) atomic rename |
| MED | NEW | foreman.py:690-695 | `restart_ollama`'s rate-limit stamp read failure is the file's only fully unlogged except, defaults to "never restarted," and can bypass the documented 30-min restart cooldown |
| MED | NEW | foreman.py:230-232 | `triage_swallowed`'s printed/logged "top classes" caps at 3, hiding whether more failure classes share one cause (archive itself is uncapped) |
| MED | KNOWN, still open | endpoint.py:327-334 | `fetch_html.one()` still swallows every exception undifferentiated; sibling `fetch_raw.one()` got the 404/410 split, this did not |
| MED | KNOWN, still open (bounded) | context_budget.py:242-271 | silent `""` fallback on prompt-file read failure, unlogged; traced to be bounded by `generate.py`'s independent final `assert_fits` gate, so failure mode is a loud reject/mis-sized pack rather than silent truncation |
| MED | KNOWN, still open | endpoint.py:83-94 | `_save()` still fixed-temp + threading.Lock only, unlike this file's own `register()` which was migrated to `silence.write_json` |
| LOW-MED | NEW | burgs.py:230 | `--write`'s print message claims "sample of 50 worlds" while the code writes every world (correct per Hard Rule 0; the message is stale and contradicts it) |
| LOW-MED | NEW | context_budget.py:261 | `report()` docstring claims "used by health/preflight"; zero callers found anywhere, and health.py's actual context-budget check is an unrelated hand-rolled duplicate |
| LOW | NEW, speculative | burgs.py:147 | `limit or n` treats explicit `limit=0` same as unset; unexercised by any current caller |
| LOW | NEW, speculative | compress_store.py:43-44 | non-atomic write to a content-addressed path; no confirmed concurrent caller today |
| LOW | NEW, speculative | foreman.py:90,498 | `DENYLIST` reused for two unrelated safety properties (patch-immunity vs. dedup-kill-immunity) |

batch04: 6 modules, 2441 lines read, 2 high, 6 med, 5 low, report at handoff/sweep28/AUDIT_batch04.md
