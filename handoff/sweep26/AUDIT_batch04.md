# BATCH 04 audit — run26

Modules (src/, full line-by-line read): foreman.py (1264), publish.py (379), context_budget.py
(278), burgs.py (235), halo.py (178), module_index.py (83). Total 2,417 lines.

---

## foreman.py

### MAJOR — M15 confirmed open: `restart_reader` and `kill_stalled_job` never check pool health before killing/bouncing a job whose real cause is a starved pool
`src/foreman.py:342-384` (`restart_reader`), `387-460` (`kill_stalled_job`), and the REMEDIES
wiring at `759` (`"corpus read is progressing": [restart_reader]`) and `736`
(`"every running job is advancing": [kill_stalled_job]`).

Both functions match a process by `lognames.OWNER` fragment and `SIGTERM` it. Neither one
consults `POOL_PROOF.json`, `dashboard.throughput()`, or any other pool-health signal before
acting. This file's own `reprove_pool` docstring (lines 138-141) documents at length that the
reader can look stalled — writing nothing, appearing dead to `standards`' liveness check — purely
because the pool it depends on has zero answering buckets ("Headroom is not evidence. Twenty-five
of thirty-six buckets reported healthy quota while answering nothing"). When that happens, the
standard `"corpus read is progressing"` goes red for a pool reason, but its only configured remedy
(`restart_reader`) kills the reader anyway. Per the file's own `_restart_horizon`, `read.py` is not
in `overnight.STANDING`, so that kill costs 42-44 minutes typically and up to 4 hours — for zero
benefit, since the root cause (empty pool) is untouched. Same gap in `kill_stalled_job`, which will
kill *any* job the standard names, including the reader, on the same blind basis.

**Failure scenario:** the pool empties (a provider outage, a mis-learned cap, a 429 storm).
`read.py` stops writing because it has nothing to write. `standards` reports `"corpus read is
progressing"` red. `restart_reader` fires, SIGTERMs the reader, and reports "bounced reader pid
N; [restart horizon]". The pool is still empty. The reader comes back (per the horizon, up to 4h
later) and immediately stalls again for the same reason — the remedy loop can do this every round
without ever fixing anything, burning the reader's uptime on a problem it doesn't have.

### MAJOR — `reprove_pool`'s return value conflates "wrote the proof file" with "the pool answers", making its own escalation path to `restart_reader` effectively dead code
`src/foreman.py:135-165`
```python
ok = [r for r in rows if r.get("verdict") == "answers"]
...
if not silence.replace_retry(_pp + ".tmp", _pp):
    return False, "pool re-proved but POOL_PROOF.json write was DENIED; ..."
CB._PROVEN[0] = None
return True, f"{len(ok)} of {len(rows)} buckets answer"
```
`did_something` here is `True` whenever the write succeeds, *regardless of `len(ok)`* — even
`0 of N buckets answer` returns `True`. Every other AUTO remedy in this file measures "did" as an
actual effect (`clear_learned_caps` returns `bool(n)`, `adopt_hosts` returns `bool(m)`,
`scout_hostless` returns `bool(found)`), so this is the one that breaks the pattern. It matters
concretely at the one place `reprove_pool` is paired with an escalation:
```
"the library's counters are moving": [reprove_pool, restart_reader],   # line 753
```
Per `round_once`'s `if did: break` (line 1182), `restart_reader` only runs if `reprove_pool`
*fails outright* (exception or denied write) — never when the pool was re-measured and found
completely dead. The one place in this file that pairs a pool re-proof with a reader-bounce as an
explicit fallback never reaches the fallback for the case it exists for.

**Fix direction:** `reprove_pool` should return `bool(ok)` (or similar) so "0 of N answer" is
reported as *not* fixed, letting the configured escalation actually run.

### MAJOR — `attempt_patch`'s exception handler claims "reverted" even when the revert itself fails
`src/foreman.py:1003-1009`
```python
except Exception as e:
    silence.note("foreman.py:attempt_patch-apply")
    try:
        shutil.copy2(backup, path)
    except Exception:
        silence.note("foreman.py:attempt_patch-revert")
    return {"ok": False, "why": f"reverted after {type(e).__name__}"}
```
If the inner `shutil.copy2(backup, path)` itself raises (disk full, permission denied — this
project's own docstrings elsewhere describe Norton locking newly-written files on this exact
machine), the exception is caught and silently noted, but the function's return value is
unconditional: it always reports `"reverted after {type}"`. This is a write to **live source
code** in `src/`, and the message actively lies about whether the file was restored. A caller (or
a human reading the operational log) has no way to tell a genuine revert from a failed one — the
live module may be left holding a partially-written, syntactically broken patch while the log
claims recovery happened.

**Failure scenario:** `attempt_patch` writes a bad patch to `src/some_module.py`, `_checks_pass`
returns `False` or an exception is raised during the write itself, and the subsequent
`shutil.copy2(backup, path)` fails (locked file, disk pressure). The module is now damaged on
disk, `attempt_patch` reports `"reverted after <ExceptionType>"`, and nothing downstream (`round_once`,
the operational log, or a human skimming it) has any signal that the revert didn't actually happen.

### MAJOR — `kill_stalled_job` reports "no job is stalled now" when the standard row is simply missing, not when it is actually green
`src/foreman.py:409-411`
```python
row = next((r for r in rows if r["standard"] == "every running job is advancing"), None)
if not row or row.get("holds"):
    return True, "no job is stalled now"
```
`row is None` (the standard's name changed, `standards.check()` raised for just that check, or a
refactor drops it from `rows`) is treated identically to `row.get("holds") is True` (the standard
genuinely passed). Both return `True, "no job is stalled now"` — a message that asserts a positive
fact ("no job is stalled") the code did not actually verify in the "row missing" branch. This is
exactly the "check that cannot fail" / "swallowed failure indistinguishable from success" shape:
if the standard's name or shape ever drifts, this remedy silently and permanently reports health
it never checked, and `round_once` logs it as a successful AUTO action every round.

**Fix direction:** distinguish `row is None` ("could not evaluate the standard") from
`row.get("holds")` ("evaluated and healthy") in the return message, the way `restart_horizon`
elsewhere in this same file insists on naming true states rather than assumed ones.

### MAJOR — Hard Rule 0: model-patch lane permanently starves findings ranked below the top 3
`src/foreman.py:1205`
```python
for f in sorted(open_f, key=lambda x: -(x.get("severity") == "high"))[:3]:
```
Every round, `round_once(patch=True)` attempts at most 3 open findings, chosen by a **stable,
deterministic sort** (severity-high first, otherwise original dict-iteration order — no rotation,
no round-robin, no "already attempted this round" exclusion). A finding that fails to patch stays
`open` (only `_retire()` on an unactionable/no-op verdict removes it from the open set). So if more
than 3 findings are open, findings ranked 4th and below are **never attempted, ever** — the same
top 3 (by this fixed ordering) are retried every round while the rest sit untouched indefinitely.
This is precisely the shape Hard Rule 0 names as forbidden ("`cap=250` took the alphabetical head
of every missing-cast repair... a cap does not fail, it returns a smaller universe wearing the
same shape as the real one").

**Failure scenario:** overwatch opens 10 findings across 5 modules. Every round, the same 3
highest-severity findings are attempted (successfully or not); findings 4-10 are never even tried
by the model lane, with no log line anywhere stating they were skipped for capacity reasons rather
than judged unactionable.

### MINOR — module docstring's "six gates" undercounts the actual patch-lane checks, omitting the most safety-critical one
`src/foreman.py:39-51` (docstring) vs. `915-985` (`attempt_patch`)
The docstring enumerates six checks a patch must clear. The code actually enforces at least eight:
denylist/path (919-923), function-found + `<=400` lines (925-934), model verdict `== "fix"`
(967-968), reply `starts with def/async def` (971-972), `MAX_PATCH_LINES` (979-981), no-op
(982-983), and — not mentioned in the docstring's list at all — `regex_touched` (984-985), which
the file's own inline comment (856-875) calls out as catching "THE FIRST PATCH THE MODEL EVER
PROPOSED", i.e. the single most consequential gate demonstrated in this project's history. The
code is stricter than advertised (safe direction), but a reader trusting the docstring's "six
gates" list would not know the regex gate exists at all.

### MINOR — `attempt_patch`'s `DENYLIST` check is an exact-string, case-sensitive match
`src/foreman.py:919-920`
```python
if not module or module in DENYLIST:
```
`DENYLIST = {"foreman", "silence", "health", "allsweep", "estate", "standards", "verify_math"}`
is a plain set membership test. If `finding.get("module")` were ever populated with a different
spelling of one of these names (different case, a `.py`-suffixed form, etc.), the check would
silently pass a module that was meant to be permanently unpatchable. Currently `module` names are
sourced consistently as lowercase basenames elsewhere in the project, so this is not observed to
be reachable today — flagging as the "guard matching only one spelling of what it forbids" shape
called out by the audit brief, worth a defensive normalization (`.lower()`/`.rstrip(".py")`) rather
than a proven live bug.

### QUESTION — `scout_hostless`'s per-round cap of 4 sources: does it rotate?
`src/foreman.py:192`
```python
res = SC.sweep(limit=4)
```
Every foreman round that runs this remedy processes at most 4 hostless sources. `scout.py` is
outside this batch, so whether repeated calls rotate through the full hostless set or always
re-offer the same first 4 (in whatever order `scout.sweep` iterates) could not be verified here.
If it does not rotate, this is a live Hard Rule 0 violation (a permanent "first 4" over the set of
hostless sources); if it does rotate across calls (e.g., by persisting an offset or by removing
adopted sources from the pool each round), it's a legitimate per-round throttle. Recommend a
follow-up read of `scout.py:sweep()`.

### Positive notes (verified correct)
- All `subprocess.run`/`Popen` calls in this file pass `creationflags=_NO_WIN` (lines 100-101,
  354-357, 433-436, 473-476, 700-703) — no console-window violations found.
- All three process-killers (`restart_reader:376`, `kill_stalled_job:446`,
  `kill_duplicate_jobs:498`) correctly exclude `os.getpid()`, and `kill_duplicate_jobs` also
  excludes the supervision chain (`overnight`, `autostart`) and the full `DENYLIST` — the
  "matcher's own command line" self-match risk named in the audit brief is well-guarded via PID
  checks plus the `wmic ... name='python.exe' or name='pythonw.exe'` filter (which itself excludes
  `wmic.exe`, so the query text can't self-match).
- `_restart_horizon` (306-339) is a real, already-implemented fix for the "supervisor restarts
  next cycle" false-claim half of M15 — both killing remedies now call it and report an honest
  per-job downtime estimate rather than the old blanket claim. Only the pool-health-blind-killing
  half of M15 remains open (see above).
- `triage_swallowed` (214-283) and `_retire` (1014-1040) both correctly check `silence.replace_retry`'s
  return value and report failure honestly (archive-then-clear ordering is right: archive is
  written and confirmed before the live ledger is cleared).
- `MAX_PATCH_LINES` (91), `top = ...[:3]` in `triage_swallowed` (230, summary display only — full
  ledger still archived), and `new[:400]` preview (987, dry-run display only) are legitimate
  bounds/summaries, not data-completeness caps.

---

## publish.py

### MAJOR — `render_page()`'s write to `docs/index.html` is not atomic at all (no tmp+rename, no retry)
`src/publish.py:261-264`
```python
os.makedirs(DOCS, exist_ok=True)
with open(PAGE, "w", encoding="utf-8") as f:
    f.write(html)
return PAGE
```
This is a bare truncating write to a file this same module's own docstring says has two
concurrent writers ("Two writers publish into this tree (the standing loop and whatever session is
working)", `push()` docstring, line 296-298) and that this same file's header docstring explicitly
documents as living under a machine where "Norton locks newly-written objects" causing intermittent
`Permission denied`. Every other shared-state write in the sibling module `foreman.py` goes through
`silence.replace_retry` specifically to survive this documented hazard; this write has neither a
temp-file swap nor a retry. A reader (GitHub Pages, or `sync_tree`'s own `os.walk` a moment later
via a second writer) can observe a truncated `index.html` mid-write, and a Norton lock here simply
raises and aborts the whole publish cycle for that round rather than retrying.

### MAJOR — `write()`'s state.json write uses raw `os.replace`, not the project's own `silence.replace_retry`
`src/publish.py:283-290`
```python
tmp = STATE_JSON + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=1)
os.replace(tmp, STATE_JSON)
return STATE_JSON
```
`silence` is imported into this module specifically (`silence.note` is used at 174, 338, 371) and
`foreman.py`'s equivalent shared-state writes all route through `silence.replace_retry` to survive
exactly the Norton-lock class of failure this file's own header names as the reason the whole
export-to-a-copy design exists. `os.replace` here has no retry: on a transient lock it raises,
propagates to `main()`'s broad `except Exception`, and the cycle is reported failed — while
`silence.replace_retry` elsewhere in the project is documented as surviving that exact failure
class. Inconsistent with the two-writer contract used everywhere else in this codebase; the `.tmp`
file is also left behind on a failed `os.replace` (minor leak, not cleaned up).

### MINOR — `_scrub` does not recurse into tuples, only `dict`/`list`/`str`
`src/publish.py:151-164`
```python
if isinstance(obj, dict):
    return {k: _scrub(v) for k, v in obj.items()}
if isinstance(obj, list):
    return [_scrub(v) for v in obj]
if isinstance(obj, str):
    return _SECRET.sub("[redacted]", obj)
return obj
```
A tuple anywhere in the state tree passes through the final `return obj` unredacted. `json.dump`
happily serializes tuples as JSON arrays without raising, so a secret-shaped string nested inside a
tuple (rather than a list) would reach the published snapshot un-scrubbed. Current callers
(`dashboard.state()`, `standards.check()`) likely only ever produce dict/list/str/number, so this
is not demonstrated as live, but it's a real gap in what the module's docstring calls "the second
lock" against a future field carrying an unredacted credential.

### MINOR — `_SECRET` regex is a fixed allowlist of known provider key prefixes
`src/publish.py:145-148`
```python
_SECRET = re.compile(
    r"(sk-[A-Za-z0-9_\-]{16,}|gsk_[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_\-]{20,}|"
    r"github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{20,}|"
    r"xai-[A-Za-z0-9]{20,}|csk-[A-Za-z0-9]{20,})")
```
Covers OpenAI/Anthropic-shaped (`sk-`), Groq, Google, GitHub, HuggingFace, xAI, and one more
provider. A key format from any provider not in this list (AWS `AKIA...`, Perplexity `pplx-`,
Replicate `r8_`, Azure, Mistral, etc.) would not be redacted if it ever ended up in the state dict.
This is the "guard matching only one spelling of what it forbids" shape named in the audit brief —
worth noting as the allowlist grows brittle every time a new provider is added to the project
unless this regex is updated in lockstep.

### QUESTION — `push()`'s early return on empty `porcelain` could in principle strand an already-committed, unpushed commit
`src/publish.py:301-306`
```python
git("add", "-A")
porcelain = git("status", "--porcelain")
if not porcelain:
    return False
```
If a previous cycle committed locally but the subsequent `fetch`/`rebase` or `push` failed (both
return `False` without raising past this point, see `push()`'s except-block at 334-341 and the
plain `git("push",...)` at 342 which — if it raises — propagates to `main()`'s handler, not
caught here), the local branch is left ahead of `origin/main`. On the *next* cycle, if nothing in
the working tree changed since that local commit, `porcelain` would be empty and this function
returns `False` ("no change to push") without attempting to push the already-committed, still-unpushed
commit. In practice this is very unlikely to manifest because `write()` regenerates `state.json`
with a fresh `"generated"` timestamp (`snapshot()`, line 175) every cycle, so `porcelain` is
effectively never empty in the standing loop — but the function's own logic doesn't guarantee a
stuck local-ahead-of-origin state ever gets retried if that assumption ever stops holding (e.g., a
future change makes `write()` skip the timestamp, or `--push` is invoked standalone without a
fresh `write()` first).

### Positive notes (verified correct)
- `push()`'s fetch-rebase-then-push design is sound on the paths that matter: a rebase conflict
  triggers `git rebase --abort` (336) before returning `False`, so the local repo is left in a
  clean, retryable state rather than a half-rebased one; the commit itself always reflects a
  complete tree (staged via `git add -A` after `sync_tree`/`render_page`/`write` have all already
  returned successfully in the same `try` block in `main()`, so no partial-sync content can reach
  a commit). A `git push` failure after a successful rebase propagates as a real exception to
  `main()`'s handler and is reported as `"publish failed"`, never misreported as `"pushed"` — no
  false-success path found on the push call itself.
- `git()` (179-200) correctly strips `GITHUB_TOKEN`/`GH_TOKEN` from the subprocess environment and
  passes `creationflags=_NO_WIN` — no console-window violation.
- `export_root()` (90-123) and `_is_throwaway()` (74-82) are a real, well-reasoned fix for the
  documented temp-directory export hazard (verified structural, not single-machine-path-specific).
- `sorted(code)[:6]` in the commit-message builder (322) is a legitimate display cap — the `+N`
  suffix (323) accounts for the remainder, no data loss.

---

## context_budget.py

### MAJOR — file-read failures in `feats_block_budget`/`report` silently default to an empty
prompt, moving the budget estimate in the dangerous (permissive) direction this module exists to
prevent
`src/context_budget.py:242-253` (`feats_block_budget`), `262-271` (`report`)
```python
if system_text is None:
    try:
        with open(os.path.join(PROMPTS, "system_style.txt"), encoding="utf-8") as f:
            system_text = f.read()
    except Exception:
        system_text = ""
if template_text is None:
    try:
        with open(os.path.join(PROMPTS, "feats_prompt.txt"), encoding="utf-8") as f:
            template_text = f.read()
    except Exception:
        template_text = ""
```
The module's entire stated purpose (see its own header docstring, "THE BUG THIS EXISTS FOR") is to
be *pessimistic on purpose*: "being wrong in that direction costs smaller blocks and more calls,
and being wrong in the other costs silently truncated evidence, which is the thing the whole
project exists to refuse." A failed read of `system_style.txt`/`feats_prompt.txt` (file locked
mid-edit, transient I/O error, permission denial — this project's own docstrings elsewhere
document exactly this class of failure recurring on this machine) is caught and silently
substituted with `""`. An empty scaffold means `scaffold_chars` computes as 0, `content_budget_chars`
returns a budget as if there were *no* system-prompt/template overhead at all — the single largest
component of the real prompt — producing an **oversized** content budget. This is the exact
failure mode (Ollama silently truncating an over-budget prompt) that this entire module was built
to refuse, reintroduced by the one place it reads its own inputs. `src/manifest_builder.py:331`
calls `feats_block_budget(cfg)` with no arguments, so this file-read path is live in production,
not just a theoretical default.

**Failure scenario:** `system_style.txt` is transiently unreadable (e.g. a concurrent editor has it
open, or a Norton scan holds a lock) exactly when `manifest_builder.py` calls
`feats_block_budget(cfg)`. The function returns a budget computed as if the ~18KB system prompt
did not exist, `pack_feats` packs a block up to that inflated budget, and the resulting prompt
overflows `num_ctx` — silently truncated by Ollama, with `generate._covered`'s name-only check
unable to detect the loss, exactly as described in this module's own header.

### MINOR — `split_system_prompt`'s heading match degrades silently, with no signal if it stops
matching
`src/context_budget.py:122-135`, `_TEMPLATE_HEADING` at line 101
```python
for i, line in enumerate(lines):
    if line.strip().startswith(_TEMPLATE_HEADING):
        return "\n".join(lines[:i]).rstrip(), text
return text, text
```
Currently matches correctly (`prompts/system_style.txt:103` is `"THE ENTRY TEMPLATE -- every entry
you write follows this exact shape..."`, an exact-prefix match). But the docstring's own stated
fallback — "If the heading is absent the split is a no-op and both halves are the whole file" — is
a *silent* degrade: if the heading line is ever reformatted (a markdown `##` prefix, reindented,
retitled), `system_for("feats", ...)` quietly starts sending feats jobs the *entire* system prompt
again (the ~11K-character template half this split exists specifically to strip out for feats
jobs), with no error, warning, or log line anywhere. Given the module's own emphasis on refusing
silent degradation elsewhere (`assert_fits` raises rather than clamps), this one silent fallback is
worth a loud warning (e.g. `silence.note`) rather than a quiet no-op.

### Positive notes (verified correct)
- The core arithmetic (`estimate_tokens`, `measure`, `fits`, `assert_fits`,
  `content_budget_chars`) is internally consistent and correctly propagates negative headroom
  without clamping (`content_budget_chars`'s docstring explicitly requires this and the code
  honours it: `feats_block_budget`'s final `int(room / METADATA_INFLATION)` preserves sign).
  `assert_fits` raises `ContextOverflow` rather than truncating — this is the pattern the rest of
  the audited code should be following for "swallowed failure" cases.
- No caps/limits over any *data set* in this file — every `[:N]`-shaped operation
  (`lines[:i]` at 134) is a deliberate two-way split of a single fixed document by heading, not a
  truncation of a growing collection.

---

## burgs.py

### MINOR — `limit or n` treats an explicit `limit=0` the same as `limit=None`
`src/burgs.py:147`
```python
for k in range(1, (limit or n) + 1):
```
`0` is falsy in Python, so `burgs_for(seed, features, limit=0)` — which should plausibly mean
"give me zero burgs" — silently falls back to the full derived count `n` instead. No current
caller in this codebase passes `limit=0` (checked: `verify_math.py` only calls with `limit=3` and
`limit=200`), so this is latent rather than observed-live, but it's the exact "zero produces a
silently wrong value" shape named in the audit brief. Correct form would be
`limit if limit is not None else n`.

### MINOR — the `--write` output's own print statement contradicts what the code just wrote
`src/burgs.py:190-230`
```python
worlds = WS.build_all()          # every world; Hard Rule 0
...
for w in worlds:
    ...
    per_world[w["designation"]] = bs
...
if args.write:
    p = os.path.join(HERE, "data", "BURGS_SAMPLE.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(per_world, f, indent=2,          # every world; Hard Rule 0
                  ensure_ascii=False)
    print(f"\nwrote {p} (sample of 50 worlds; the rest regenerate on demand)")
```
`per_world` is built from the *entire* `worlds` list (`WS.build_all()`, explicitly commented
"every world; Hard Rule 0" at both the build site and the `json.dump` call) — there is no slicing
anywhere in the loop that populates it. The write is genuinely complete, matching Hard Rule 0. But
the printed message claims the opposite: `"sample of 50 worlds; the rest regenerate on demand"`.
This is a stale/wrong operational message (the file's own name, `BURGS_SAMPLE.json`, reinforces the
same wrong impression) — the actual current behaviour is correct, but a maintainer trusting the
printed claim could reasonably "fix" this file by actually capping the write to 50 worlds to match
what it says it does, which would introduce a real Hard Rule 0 violation to match a message that
was never true of the current code.

### MINOR — `--write`'s output file is not written atomically
`src/burgs.py:226-229`
```python
with open(p, "w", encoding="utf-8") as f:
    json.dump(per_world, f, indent=2, ensure_ascii=False)
```
Bare truncating write, no tmp+rename, no `silence.replace_retry`/`silence.write_json`. Likely
low-risk in practice (a manual `--write` invocation, not part of the standing supervised loop as
far as this batch can determine), but inconsistent with the project's established atomic-write
pattern used for every other shared JSON artifact seen in this batch (`halo.py`'s
`silence.write_json`, `foreman.py`'s `silence.replace_retry` throughout).

### Positive notes (verified correct)
- `burg_count`, `largest_city`, `classify`, and the rank-size loop in `burgs_for` are all
  arithmetically sound; boundary conditions in `classify`'s `lo <= pop < hi` ranges checked and
  correct, including the `>= 10**9` overflow case (correctly falls through to `"city"`).
- `[:args.limit]` at line 218 only truncates a single console preview print for one sample world;
  it does not affect `per_world` (built without any limit at line 199) or the `--write` output —
  legitimate display-only truncation, and `[:args.limit]` with the default `limit=None` is a
  Python no-op slice (prints everything) unless `--limit` is explicitly passed on the CLI.
- No subprocess spawns, no shared mutable module state, no bare/overbroad `except` clauses at all
  in this file.

---

## halo.py

No MAJOR or MINOR findings. This module is a static, hand-curated data table (Halo assay roster)
plus a thin `compute()`/`main()` wrapper; read in full and it holds up:
- Output write (`silence.write_json(OUT, out, ...)`, line 171) is atomic and goes through the
  project's own shared-write helper — compliant with the two-writer contract.
- `[:54]` at line 169 (`d["cited"][:54]`) is a fixed-width console print truncation for `--full`
  mode only; the full `cited` text is preserved untruncated in the JSON written to
  `data/HALO_ASSAYS.json` (built from `rec["axes"]` at line 142 with no truncation).
- No subprocess calls, no bare/overbroad `except` clauses, no shared mutable state.
- QUESTION (very low confidence, out of batch scope): `main()`'s `rank = sorted(...)` at line
  151-153 calls `A.LADDER.index(kv[1]["assay"]["magnitude"])` uncaught — if `assay.assay()` ever
  returns a `magnitude` string not present in `assay.LADDER`, this raises `ValueError` straight out
  of `main()`. Not verified against `assay.py` (outside this batch); flagged only as a coupling
  assumption, not a demonstrated bug.

---

## module_index.py

### MINOR — `handoff/MODULE_INDEX.md` is written non-atomically, and `handoff/` is copied by a
concurrent process
`src/module_index.py:75-76`
```python
with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
```
Bare truncating write, no tmp+rename. `publish.py`'s `COPY_DIRS` (`src/publish.py:133`) includes
`"handoff"`, and `sync_tree()` walks it on a standing 10-minute publish loop, comparing mtime/size
and `shutil.copy2`-ing anything changed (`src/publish.py:203-230`). If `publish.py`'s `sync_tree`
happens to stat-and-copy `handoff/MODULE_INDEX.md` in the narrow window between this file's
`open(..., "w")` truncating the file and the subsequent `f.write` completing, the export tree (and
eventually the published GitHub Pages site, since `handoff/` is a named copy directory) could pick
up a partially-written or empty `MODULE_INDEX.md`. Regeneration is described as a rare/manual
operation ("Regenerate after adding a module; never hand-edit" — the docstring implies this isn't
part of the standing supervised loop), which keeps the collision window narrow, but it's the same
inconsistency class flagged in `burgs.py` above: this project has an established atomic-write
convention (`silence.write_json`/`silence.replace_retry`) that this file doesn't use for a file a
second process (`publish.py`) actively reads on a timer.

### Positive notes (verified correct)
- No caps: `glob.glob(os.path.join(HERE, "src", "*.py"))` enumerates every module unconditionally
  (line 52-53); `GROUPS` is a fixed classification list, not a truncation — modules not named in
  any group correctly fall through to the "Everything else" section (`rest = sorted(set(mods) -
  placed)`, lines 68-74) rather than being dropped.
- `first_line`'s catch-all `except Exception` (46-48) is safe: on failure it returns the visibly
  distinct `"(unparseable)"` marker rather than a value indistinguishable from a real docstring, so
  it does not qualify as a "swallowed failure" under the audit's own definition (point 2 requires
  the swallowed result to be indistinguishable from success).
- No subprocess calls, no shared mutable module state.

---

## Summary table

| Severity | Location |
|---|---|
| MAJOR | foreman.py:342-384, 387-460, 736, 759 — M15 open: reader/job killed with no pool-health check |
| MAJOR | foreman.py:161-162, 753 — `reprove_pool` always-True return deadens its own escalation to `restart_reader` |
| MAJOR | foreman.py:1003-1009 — `attempt_patch` claims "reverted" even when the backup restore itself fails |
| MAJOR | foreman.py:409-411 — `kill_stalled_job` reports "no job is stalled" when the standard row is simply missing |
| MAJOR | foreman.py:1205 — Hard Rule 0: model-patch lane permanently starves findings ranked below top 3, no rotation |
| MINOR | foreman.py:39-51 vs 915-985 — docstring's "six gates" omits the regex-literal gate and two others |
| MINOR | foreman.py:919-920 — DENYLIST is exact-case string match, no normalization |
| QUESTION | foreman.py:192 — `scout.sweep(limit=4)`: does it rotate across rounds? (scout.py out of batch) |
| MAJOR | publish.py:261-264 — `render_page()` writes docs/index.html with zero atomicity, two documented concurrent writers |
| MAJOR | publish.py:283-290 — `write()` uses raw `os.replace`, not `silence.replace_retry`, despite this file's own Norton-lock precedent |
| MINOR | publish.py:151-164 — `_scrub` does not recurse into tuples |
| MINOR | publish.py:145-148 — `_SECRET` regex is a fixed provider-prefix allowlist |
| QUESTION | publish.py:301-306 — empty-porcelain early return could in principle strand an unpushed local commit (mitigated in practice by state.json's timestamp) |
| MAJOR | context_budget.py:242-253, 262-271 — file-read failure silently defaults to empty prompt, inflating the budget in the dangerous direction; live via manifest_builder.py:331 |
| MINOR | context_budget.py:122-135 — heading-match split degrades silently with no warning if the heading text ever changes |
| MINOR | burgs.py:147 — `limit or n` treats `limit=0` same as `limit=None` (latent, no live caller) |
| MINOR | burgs.py:230 — "sample of 50 worlds" print message contradicts the full-world write it describes |
| MINOR | burgs.py:226-229 — `--write` output not atomic |
| MINOR | module_index.py:75-76 — non-atomic write to a file `publish.py` actively copies on a timer |
| QUESTION | halo.py:151-153 — uncaught `A.LADDER.index()` ValueError risk if magnitude string mismatches (assay.py out of scope) |
