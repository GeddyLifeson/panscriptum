# Batch 10 audit — rigor.py, gpu_lane.py, publish.py, entity_match.py, runguard.py, catalogue_models.py, lognames.py

Run #28, sweep batch 10. Every line of all 7 modules read (865+479+379+278+219+176+36 = 2,432
lines). `NEXT_STEPS.md` §3 read first; every item touching this batch's modules re-verified
against current source, several by live reproduction.

---

## SPECIAL FOCUS (a) — `publish._scrub()` (publish.py:145-164), exact credential shapes that pass

`_SECRET` (publish.py:145-148):
```python
_SECRET = re.compile(
    r"(sk-[A-Za-z0-9_\-]{16,}|gsk_[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_\-]{20,}|"
    r"github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{20,}|"
    r"xai-[A-Za-z0-9]{20,}|csk-[A-Za-z0-9]{20,})")
```
`_scrub()` (151-164) recurses dict/list/str and applies only this one regex to strings — it has
no allow/deny by field name, no shape detection beyond these 8 literal vendor prefixes. The
docstring (module header, lines 31-33) says `_scrub` "refuses anything credential-shaped."
That is false. Confirmed by enumeration — **NOT redacted, so they publish unredacted to the
public GitHub Pages repo if they ever land in the state dict**:

- **AWS** access key IDs (`AKIA[0-9A-Z]{16}`) and secret access keys (40-char base64) — no AWS
  pattern present at all.
- **Slack** tokens (`xoxb-`, `xoxp-`, `xoxa-`, `xoxr-`) — no Slack pattern.
- **Generic bearer / `Authorization: Bearer <token>` values** with no recognisable vendor
  prefix — nothing matches an opaque bearer token shape.
- **PEM / private-key blocks** (`-----BEGIN ... PRIVATE KEY-----`) — no multiline/PEM pattern;
  a pasted SSH or TLS private key would publish verbatim.
- **JWTs** (three base64url segments joined by `.`, e.g. `eyJhbGci...`) — no JWT pattern.
- **Stripe-style keys with an underscore separator** (`sk_live_`, `sk_test_`, `rk_live_`) — the
  `sk-` branch requires a literal hyphen right after `sk`, so `sk_live_...` does **not** match
  (verified: `_SECRET.search("sk…<defanged example, run #28>")` → no match).
- **Database connection strings with embedded credentials**
  (`postgres://user:pass@host/db`) — no pattern for embedded userinfo.
- **Discord bot tokens, npm tokens (`npm_...`), Twilio/SendGrid/Mailgun keys**, and any other
  vendor's key shape not in the 8-item list — none of these match.
- **Any field simply named `password`/`secret`/`api_key` holding plain text with no
  recognisable prefix** — `_scrub` is purely regex-over-string-content, so a bare secret with
  no vendor signature (e.g. a locally-generated random token) is invisible to it regardless of
  field name.

What **is** caught: OpenAI-style (`sk-...`, including Anthropic's `sk-ant-...` since `ant-...`
falls inside the `sk-` branch's character class), Groq (`gsk_`), Google (`AIza`), GitHub PAT
classic and fine-grained (`ghp_`, `github_pat_`), HuggingFace (`hf_`), xAI (`xai-`), and one
`csk-`-prefixed vendor (Cerebras/Cohere-style).

This is `NEXT_STEPS.md` Owner Ruling item 3 ("Decision C"), already recorded — **KNOWN, verified
still open**, with the enumeration above filling in exactly which shapes leak. Severity: HIGH,
because this governs what leaves the machine into the published repo, and the docstring reads
as a guarantee it does not deliver.

---

## SPECIAL FOCUS (b) — why the live "model IDs their providers still serve" catalogue is stale/wrong, and whether `catalogue_models.py:158`'s `[:10]` is implicated

**Finding: the catalogue is not wrong. It is correctly reporting a real drift in a file outside
this repo, and the automated remedy wired to the standard cannot fix that drift — so the
standard will read red forever no matter how often it re-runs.**

Live-verified chain, this session:

1. `data/PROVIDER_MODELS.json` (mtime 2026-08-25 08:12, ~13 min old at read time — well under
   `MAX_PROVIDER_MODELS_AGE_H = 12h`, `standards.py:308`) currently carries `"stale": [...]`
   with exactly 8 entries, **all provider `ollama`**: `llama3.1:latest`, `qwen2.5:14b`,
   `hf.co/unsloth/Qwen3-14B-GGUF:Q4_K_M`, `gemma3:latest`, `moondream:latest`,
   `qwen3:30b-a3b-instruct-2507-q4_K_M`, `hf.co/unsloth/Qwen3-30B-A3B-Instruct-2507-GGUF:Q3_K_M`,
   `gemma3:12b`.
2. The `providers` row for `ollama` in that same file records `"models": ["qwen3:8b"]` — i.e.
   `ask_provider` asked the local Ollama daemon and got back exactly one model.
3. Queried the live daemon directly this session: `curl http://localhost:11434/v1/models` and
   `.../api/tags` both return **one** model, `qwen3:8b`. So the catalogue's `ollama` row is
   correct — the local Ollama installation genuinely has only `qwen3:8b` pulled right now.
4. `~/cascade/config.json`'s `models` list still asks for all 8 of the missing names under
   `provider: "ollama"`. Those are real config entries pointing at models that have since been
   pruned/removed from this machine's Ollama install (consistent with the memory note on this
   machine about VRAM pressure and MoE-vs-dense tradeoffs on the 3080).
5. `standards.py:307` sets `MAX_STALE_MODEL_IDS = 0`, so any nonzero stale count fails the
   standard (`standards.py:1283`).
6. `foreman.py:763` maps the failing standard name `"model IDs their providers still serve"` to
   a single remedy, `recatalogue_models` (`foreman.py:286-296`), whose entire body is
   `_run([SRC/"catalogue_models.py"])` — it re-runs the exact same probe against the exact same
   `~/cascade/config.json`. Its own docstring says it exists "so stale-ID findings cannot
   outlive their fix" — i.e. it assumes a human has already edited the config and this just
   re-measures. Foreman calls it automatically whenever the standard is red, with nothing else
   in the remedy chain that edits `cascade/config.json`.

**Consequence:** this standard cannot be repaired by its own automated remedy. Every foreman
cycle that finds it red will re-run `catalogue_models.py`, get the identical 8-stale result
(because `cascade/config.json` still asks for models the Ollama daemon no longer has), and
foreman has no signal that the fix it needs lives in a different project's config file. This is
the same shape as NEXT_STEPS lesson 18 ("when a number won't explain itself, the cause may not
be in that subsystem at all") but one step further: here the cause is diagnosed correctly by the
tool, but the *remedy* is structurally incapable of closing the loop. **NEW finding, MED-HIGH** —
not a code bug in `catalogue_models.py` itself, but a real defect in the foreman remedy
mapping / an owner-visibility gap (cascade's config needs pruning, or the remedy needs to say so
instead of silently re-probing).

**Is `catalogue_models.py:158`'s `r["models"][:10]` implicated? No.** That line only truncates
the human-readable console line `"Current alternatives, per provider"` printed when `sweep()`
is run interactively (confirmed: `ollama`'s list has 1 model, far under 10, so it isn't even
triggered by this data). The actual persisted artifacts are uncapped:
`ask_provider`'s returned `"models": sorted(ids)` (line 102) is the full list, and
`stale[].available_sample` (line 151) explicitly stores `list(r["models"])` in full — the
comment there records this was fixed in run #26 (m145's other half). The dashboard/standard
reads `data/PROVIDER_MODELS.json` from disk, never the console output, so this cap cannot be
the source of the 8-stale figure or of any inaccuracy in it. See finding #8 below for the
cap's own (limited) standing issue.

---

## rigor.py (865 lines, read in full)

No correctness bugs found. This is the project's math/derivation module
(commensuration/AHP/Bradley-Terry/MDL/extreme-value); it is mostly pure-function math plus a
`main()` diagnostic printer, not part of the live pipeline's read/write path.

- Live-tested `bradley_terry()`'s Ford's-condition check and the Tarjan SCC helper
  (`_strongly_connected`) against a connected 3-node case and a disconnected 2-component case;
  both returned correctly (`identified=True`/`False` as expected, correct component partition).
- `bradley_terry`'s refusal message (line ~448) does `[c[:3] for c in comps][:4]` when printing
  a preview of the disconnected components — this **display-only** preview is truncated, but
  the full, untruncated `comps` list is separately returned in `out["components"]`, and the
  message also states `len(comps)` in full. Not a Hard Rule 0 violation of the returned data;
  LOW at most, informational only.
- `mathematical_resonance()` (line ~712) explicitly documents "Ranked, never truncated (Hard
  Rule 0)" for its returned `load_bearing` field, and the only truncation (`[:6]`) is in
  `main()`'s print statement, which the adjacent comment says is deliberate display-only
  slicing. Correctly done, not a finding.
- Self-check for eaten regex escapes (`_BAD_CHARS`, lines 88-91) is sound and mirrored
  identically in the other 6 files (also all confirmed present and correct in this batch:
  gpu_lane.py has no such check since it has no regex; publish.py:55-57,
  catalogue_models.py:47-49 both present and correct).

No KNOWN items from NEXT_STEPS name this file. **CLEAN.**

---

## gpu_lane.py (479 lines, read in full)

### 1. HIGH | KNOWN, confirmed by live reproduction | `gpu_lane.py:269-270` — corrupt slot file starves that slot index forever

```python
269    rec = _read(path)
270    if rec is not None and _expired(rec, SLOT_LEASE_SECONDS):
271        _remove_retry(path)
272    try:
273        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
274    except FileExistsError:
275        continue
```
`_read()` returns `None` both when the file doesn't exist AND when it exists but is unparseable
(any exception inside `_read`, gpu_lane.py:163-168). When `rec is None` because the file is
corrupt rather than absent, the guard `rec is not None and _expired(...)` is `False`, so
`_remove_retry` is never called — then `os.open(..., O_CREAT|O_EXCL)` raises `FileExistsError`
against the still-present corrupt file, and the loop `continue`s to the next index, never
freeing this one.

**Reproduced live this session** (miniconda python, `MAX_SLOTS=2`, corrupt `slot.0.json`
injected with malformed JSON): four consecutive `_take_slot` calls all returned `slot.1.json`
only; `slot.0.json` remained on disk unreclaimed after all four attempts. With `MAX_SLOTS=2`
this permanently halves the card's effective concurrency the moment one slot file is corrupted
(e.g. a crash mid-write) — silent capacity loss, no error surfaced anywhere.

### 2. HIGH | KNOWN, confirmed by live reproduction | `gpu_lane.py:66-67` — unguarded `int()` crashes the whole module on import, contradicting "FAIL OPEN, ALWAYS"

```python
66  MAX_SLOTS = max(1, int(os.environ.get("PANSCRIPTUM_GPU_SLOTS")
67                         or os.environ.get("OLLAMA_NUM_PARALLEL") or "2"))
```
No try/except. **Reproduced live**: `PANSCRIPTUM_GPU_SLOTS=notanumber python -c "import
gpu_lane"` raises `ValueError: invalid literal for int() with base 10: 'notanumber'` at import
time, before any of the module's own fail-open machinery can run. Every one of the 9 standing
processes that imports this module (read, feats --roll, pipeline, foreman, overwatch, publish,
dashboard, overnight, autostart) would fail to start entirely if either env var is ever set to
a non-numeric value. This directly contradicts the module's own header: "FAIL OPEN, ALWAYS...
every failure path here PROCEEDS rather than blocks." An import-time crash is the one failure
mode that cannot proceed.

Both confirmed exactly as recorded in `NEXT_STEPS.md` §3 ("gpu_lane.py:270 ... :66-67") — no
line drift, both **STILL OPEN**.

No other issues found; the rest of the file (foreground claims, heartbeat thread, `_alive()`'s
Windows `OpenProcess` handling, `_remove_retry`'s Windows-rename-race retry) is careful,
internally consistent, and its extensive "fixed <date>" comments (m54, m55, the `_touch`
non-resurrection guard) were checked against the current code and all hold — no
comment-contradicts-code cases found here.

---

## publish.py (379 lines, read in full)

### 3. See SPECIAL FOCUS (a) above — `_scrub()` docstring overclaim, KNOWN, HIGH.

### 4. MED | KNOWN | `publish.py:283-290` — shared `docs/state.json` written via fixed `.tmp` + bare `os.replace`

```python
283 def write(state=None):
284     os.makedirs(DOCS, exist_ok=True)
285     data = state if state is not None else snapshot()
286     tmp = STATE_JSON + ".tmp"
287     with open(tmp, "w", encoding="utf-8") as f:
288         json.dump(data, f, indent=1)
289     os.replace(tmp, STATE_JSON)
290     return STATE_JSON
```
Fixed-name tmp (not PID-scoped), bare `os.replace` (not `silence.replace_retry`) — the
project's own sanctioned pattern for a shared multi-writer JSON file
(`silence.write_json`/`replace_retry`) is not used here, even though `push()`'s own docstring
two functions below (line ~297) says outright: "Two writers publish into this tree (the
standing loop and whatever session is working)". Confirmed unchanged at these lines this run.
Two concurrent `write()` calls sharing the literal `state.json.tmp` path can interleave their
`open(...,"w")` writes (one process's `json.dump` output getting truncated/overwritten by the
other's before either calls `os.replace`), and on Windows a `PermissionError` from the bare
`os.replace` racing a reader is not retried at all (unlike every other shared-state writer in
this codebase, which routes through `replace_retry`). **STILL OPEN.**

Everything else in publish.py was verified clean: `export_root()`'s throwaway-directory refusal
logic is sound and matches its own extensive changelog comments; `SKIP_SUFFIX` correctly lists
all `.pre*` backup suffixes plus `.tmp`; `git()` correctly strips `GITHUB_TOKEN`/`GH_TOKEN` and
patches `PATH` for `gh`; `push()`'s fetch-rebase-abort-on-conflict path is correct and never
force-pushes.

---

## entity_match.py (278 lines, read in full)

**CLEAN.** This module is deliberately inert — its own header says "nothing calls this module
yet" (line ~193), and that is confirmed: the only reference to `entity_match` anywhere in
`src/` outside itself is `verify_math.py` (which pins/tests it), no pipeline module imports it.
Not a bug, matches its documentation exactly.

Verified by reading:
- `qualifier_compatible()`'s gate (107-127) is correctly absolute — a qualifier conflict is
  never overruled by similarity, matching the module's own "Wally West" design constraint and
  `verify_math §19o`/`§19r`.
- `split_qualifier()` only treats a *trailing* parenthetical as a qualifier (90-104), correctly
  avoiding false qualifiers on mid-name parens.
- `candidates()` (174-239) has no default truncation (`limit=None`), flags `truncated` when a
  caller explicitly requests one, and every early-return path (empty name, empty pool) carries
  the same `blocked_by_qualifier` key so no caller can `KeyError` on the two most-likely-real
  inputs — the exact contract bug the adjacent comment (190-194) says was fixed pre-emptively.
- `rejected.most_common(1)[0][0]` (233) picks one representative reason label for the whole
  result while the full per-reason tally survives in `blocked_by_qualifier` — not a Hard Rule 0
  violation, no data is discarded.
- `embed_available()` (258-278) degrades honestly (`available: False` with a stated reason) on
  any failure; does not silently swallow.

No findings.

---

## runguard.py (219 lines, read in full)

### 5. HIGH | KNOWN | `runguard.py:98-121` — `claim()` has no atomic test-and-set

```python
105  prior = read(path)
106  if holder_is_live(prior):
107      ...
108      return False, ...
...
119  if not _land(rec, path):
```
Between `read(path)` and `_land(rec, path)` there is no lock of any kind. Two processes racing
`claim()` when no live predecessor is recorded both observe `holder_is_live(prior) == False`
and both proceed to `_land()` their own record; the last writer's record is the only one that
survives, and **both callers receive `(True, "claimed")`** — the exact double-claim the module's
own header says it exists to prevent ("A run may only ever refresh, or close, a record that
carries its own name" presupposes only one run ever legitimately holds it). Confirmed present,
matches `NEXT_STEPS.md` §3 exactly. Notably, the *correct* pattern for this
(`os.open(path, O_CREAT|O_EXCL|O_WRONLY)`, atomic create-or-fail) already exists in this same
batch, in `gpu_lane._take_slot` (gpu_lane.py:273) — the fix pattern is sitting in a sibling
module and was not applied here.

### 6. HIGH | NEW, confirmed by live reproduction | `runguard.py:72-80` — `_land()`'s shared fixed-name tmp file makes `claim()`/`beat()`/`release()` crash with an uncaught `FileNotFoundError` under real concurrency, contradicting the module's own "WHY IT DOES NOT RAISE" section

```python
72  def _land(rec, path):
73      tmp = path + ".tmp"
74      try:
75          with open(tmp, "w", encoding="utf-8") as f:
76              json.dump(rec, f, indent=2)
77      except Exception:
78          silence.note("runguard._land")
79          return False
80      return silence.replace_retry(tmp, path)
```
`tmp = path + ".tmp"` is the **same literal path for every caller** — `claim()`, `beat()`, and
`release()` from *any* agent all funnel through `_land(rec, GUARD)`, so every concurrent caller
writes to the identical `MAINTENANCE_RUN.json.tmp`. `silence.replace_retry` (silence.py:223-240)
only retries/catches `PermissionError` — it does **not** catch `FileNotFoundError`. When two
callers race, one caller's `os.replace(tmp, dst)` can fire after a *different* caller has
already consumed (renamed away) the same `tmp` path, so the first caller's `os.replace` raises
`FileNotFoundError`, which is not caught anywhere in `replace_retry`, `_land`, or `claim`/
`beat`/`release` — it propagates straight out to the caller.

**Reproduced live this session**: 8 threads each calling `runguard.claim()` 200 times against
one shared guard path — 7 of the 8 threads raised an unhandled `FileNotFoundError` (`The system
cannot find the file specified`) out of `claim()`. (Threads stand in for the module's real
concurrency model, which is separate OS processes sharing one file — the race is on the
filesystem, not on Python's GIL, so the same interleaving reproduces across processes.)

This directly contradicts the module's own docstring, "WHY IT DOES NOT RAISE" (lines 27-33):
*"`beat()` returns False and says so on stderr rather than raising... `claim()` is the call that
decides whether work happens at all, and it reports its refusal as a value the caller must act
on."* All three (`claim`, `beat`, `release`) share the same `_land()` code path and **all three
can raise**, not just fail quietly — exactly the failure mode the header explicitly promises
does not happen. Contrast with `gpu_lane.py`'s `_touch()` (gpu_lane.py:307), which deliberately
builds a **PID-scoped** tmp name (`path + "." + str(os.getpid()) + ".tmp"`) specifically to
avoid this same collision — that defence exists in the sibling module and was not carried over
here.

Concrete failure scenario: the run-overlap guard is exercised precisely when two maintenance
runs (or a scheduled run and an interactive session) start close together — the scenario this
module exists for. Under that exact scenario, `runguard.claim()` can crash its caller with an
unhandled exception instead of returning the documented `(False, reason)` refusal, which (absent
a try/except at the call site) would abort the run with a traceback rather than "REFUSED" and a
clean exit.

Everything else in `runguard.py` checked clean: `holder_is_live()`'s three-way collapse
(`done`, stale heartbeat, missing record → all "go ahead") is intentional and documented, not a
bug; `beat()`/`release()`'s ownership checks (`owner != agent`) are correct and would actually
prevent the m27 failure the module was built to fix, if `_land()` itself didn't crash first
under concurrency.

---

## catalogue_models.py (176 lines, read in full)

### 7. See SPECIAL FOCUS (b) above — MED-HIGH, NEW: the standard's only automated remedy (`foreman.recatalogue_models`) cannot close the loop on Ollama-local staleness because the actual fix lives in `~/cascade/config.json`, outside this repo and outside anything the remedy touches.

### 8. LOW | KNOWN, confirmed present, scope limited | `catalogue_models.py:158` — `r["models"][:10]` still caps a console-only diagnostic

```python
158  print(f"  {name}: " + ", ".join(r["models"][:10]))
```
Confirmed still present (the "unfixed half of m145" per `NEXT_STEPS.md`). Verified this does
**not** reach any persisted artifact: `ask_provider`'s own returned list (line 102,
`sorted(ids)`) is uncapped, and `stale[].available_sample` (line 151) explicitly stores the full
`list(r["models"])` — the comment there documents that half of m145 as already fixed (run #26).
Line 158 only truncates the human-readable "Current alternatives, per provider" line printed
when `sweep()` runs interactively at a terminal; a person choosing a replacement model for a
provider with more than 10 live models would not see candidates 11+ in that one printed line.
Real but narrow — does not affect `data/PROVIDER_MODELS.json`, the dashboard, or the "8 stale"
figure (see focus (b)).

### 9. MED | KNOWN | `catalogue_models.py:72-106` — `ask_provider()` misattributes a "200-but-empty" response to a stale exception from an earlier URL attempt

```python
88  for url in tries:
89      try:
90          req = urllib.request.Request(url, headers={...})
93          with urllib.request.urlopen(req, timeout=timeout) as r:
94              d = json.loads(r.read().decode("utf-8", "replace"))
...
101         if ids:
102             return {"provider": name, "url": url, "models": sorted(ids)}
103     except Exception as e:
104         silence.note("catalogue_models.py:ask_provider")
105         last = f"{type(e).__name__}: {str(e)[:70]}"
106 return {"provider": name, "error": locals().get("last", "no model list endpoint")}
```
When `tries` has two URLs (base doesn't already end in `/v1`) and the **first** raises an
exception (setting `last`) while the **second** returns HTTP 200 but parses to an empty `ids`
list (unexpected JSON shape — e.g. model records keyed differently than `id`/`name`, or a
non-`dict`/`list` payload), the loop falls through both iterations without ever returning, and
the function reports `error: last` — the **stale exception message from the unrelated first
URL**, even though the actual, more recent problem was a reachable provider returning zero
parseable models. A caller reading `error` sees (say) a timeout/DNS message and would chase a
network problem, while the real fault (schema mismatch on a live, 200-responding endpoint) is
invisible. Confirmed present at these line numbers, matches `NEXT_STEPS.md` §3 description
exactly. **STILL OPEN.**

---

## lognames.py (36 lines, read in full)

**CLEAN.** Pure constants module — 6 log filename strings plus an `OWNER` dict mapping each to
the command-line fragment `overnight.running()` matches against. No logic, no I/O, nothing to
race or swallow. Cross-checked all 6 entries against the modules that actually write these logs
(`read.py`, `feats.py`, `pipeline.py`, `catalogue_web.py`, `sweep.py`, `magnitude.py` — spot
name-matched, not independently re-audited as they are out of this batch's scope) and the
`OWNER` fragments correctly include the distinguishing flag (`--run`, `--roll`,
`--recatalogue`, `--calibrate`) called out in the module's own comment as the fix for the prior
bare-script-name collision bug. No findings.
