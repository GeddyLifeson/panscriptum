# Batch 11 audit — dashboard.py, gpu_lane.py, publish.py, context_budget.py, hosts.py, audit.py, resonance.py

Every line of every assigned module was read top to bottom. Cross-file verification (allsweep.py,
overnight.py, silence.py, custodes.py, anchors.py, health.py, weave.py, manifest_builder.py) was
done wherever a finding's real severity depended on how a value is actually produced or consumed
elsewhere, per the task's own instruction to verify the dashboard hazard "at source."

Severity key: HIGH = live or clearly-reachable correctness/security defect. MEDIUM = real,
verified defect with bounded or currently-limited blast radius. LOW = confirmed but cosmetic /
negligible-impact. Every finding below is labeled VERIFIED (reproduced or confirmed by reading
the actual code paths and/or running it) — none are speculative.

---

## HIGH

### H1. dashboard.py — movement() flags a metric "stalled" on a much tighter clock than the data it reads is ever refreshed on

**VERIFIED.** This is the hazard flagged in the task brief; verified at source with an exact
line correction.

- `dashboard.py:311` — `MOVED_WINDOW_MIN = 30` (the lookback window for computing a delta).
- `dashboard.py:362` — the actual flag: `"minutes": round(span), "stalled": delta == 0 and span >= 10`.
  **This is the real "stalled" line — not `dashboard.py:338` as named in the task brief.** Line
  338 is `with open(HISTORY, encoding="utf-8") as f:`, unrelated to the flag. The stall threshold
  is gated on `span >= 10` (minutes), which is *tighter* than the 30-minute window used to pick
  the comparison baseline — so a metric can be flagged stalled after as little as ~10 minutes of
  no movement, not 30.
- `dashboard.py:326-328` — the three coverage-derived keys tracked by `movement()`:
  ```python
  "cited": ((now_state.get("library") or {}).get("coverage") or {}).get("cited"),
  "settled": ((now_state.get("library") or {}).get("coverage") or {}).get("settled"),
  "feats": ((now_state.get("library") or {}).get("coverage") or {}).get("feats"),
  ```
- `dashboard.py:255-263` — those three values are read straight from `data/COVERAGE.json`'s
  mtime-stamped content (`_library()`), refreshed only via the 30-second `_ttl` cache, not on any
  independent schedule of its own — i.e. the dashboard shows COVERAGE.json's content as fresh as
  the file itself, no more.
- `allsweep.py:203-206` — COVERAGE.json is treated as fresh for up to **2 hours**:
  ```python
  stamp = os.path.getmtime(os.path.join(HERE, "data", "COVERAGE.json"))
  age_h = (time.time() - stamp) / 3600
  if age_h > 2:
      note("COVERAGE.json is stale", ...)
  ```
- `overnight.py:668-670` confirms *why* that 2-hour tolerance is correct: `coverage_snapshot()`
  (which rewrites COVERAGE.json) runs exactly **once per overnight cycle**, after the `read.py`
  phase (up to `--read-hours` hours) and `pipeline.py` (up to 2h timeout) have both finished. A
  multi-hour gap between COVERAGE.json rewrites is the system's normal, healthy cadence, not a
  fault.

**Net effect:** for the entire span of a normal overnight cycle (which is routinely well over 30
minutes, often hours), `cited`/`settled`/`feats` legitimately do not change — and
`dashboard.py:362` will correctly compute `delta == 0`, then incorrectly render that as
`"stalled": true`, which the front end renders as **"NO CHANGE in N min"** in red
(`panelMovement`, `dashboard.py:520-538`, class `down`). This is a real, reproducible false
positive: the instrument is applying a ~10-30 minute expectation to a file the rest of the
project's own tooling (`allsweep.py`) correctly treats as healthy for up to 2 hours.

**Repair direction:** `movement()`'s per-metric stall threshold should be looked up per-metric
(e.g. keyed off the same freshness contract `allsweep.py` uses for COVERAGE.json — 2 hours for
coverage-derived keys) rather than one global 10/30-minute constant applied to every tracked key
regardless of its true update cadence. `chunks` (sourced from a live log tail) and `standards met`
(computed fresh every call) genuinely do update on a sub-minute clock and are not implicated.

---

### H2. publish.py — the credential scrub only covers the generated snapshot, not the bulk file copy that also gets committed and pushed

**VERIFIED** as a structural gap; **no live secret currently found** in the tracked tree (checked
below), so this is a latent risk rather than an active leak today.

- `publish.py:31-33` (module docstring) claims: *"The snapshot is scrubbed as well... it carries
  no keys, and `_scrub` refuses anything credential-shaped even if a future edit puts one in the
  state dict by accident."* This is true — but it describes only `snapshot()`
  (`publish.py:167-176`), which builds `docs/state.json` and is the only thing `_scrub()`
  (`publish.py:151-164`) is ever called on.
- `sync_tree()` (`publish.py:203-241`) is the *other* thing that gets committed and pushed. It
  walks `COPY_DIRS = ("src", "prompts", "reference", "registry_terminal", "handoff")` and copies
  `COPY_FILES = ("CLAUDE.md", "README.md", "config.yaml", "requirements.txt", "WATCH.md",
  "STATUS.md", "HANDOFF.md", "BUGS.md", "NEXT_STEPS.md", "MAINTENANCE.md")` with plain
  `shutil.copy2(srcp, dstp)` (`publish.py:229`, `234`) — **no content scrubbing of any kind.**
  The only filter is a *suffix* denylist (`SKIP_SUFFIX`, `publish.py:142-143`); any file dropped
  into any of those five directories under any other name is copied verbatim, then `push()`
  (`publish.py:293-343`) does `git add -A` (`publish.py:303`) and pushes it to the public remote.
- `handoff/` is one of the five copied directories, and is exactly the kind of place a credential
  gets pasted by accident during troubleshooting (this very audit writes into
  `handoff/sweep22/`). `config.yaml` is also copied verbatim and is not shaped by any code in
  this repo to be credential-free by construction — it just happens not to hold one today.
- Checked for a live secret across every currently-copied directory/file, using the exact regex
  `publish.py` itself uses for `_scrub` (`sk-`, `gsk_`, `AIza`, `github_pat_`, `ghp_`, `hf_`,
  `xai-`, `csk-`, plus `gho_`): **zero matches.** Provider keys for the router live entirely in
  `C:\Users\imarl\cascade` (`CASCADE_HOME`, `cascade_bridge.py:36`), outside this repo and outside
  `COPY_DIRS`, so today's actual key material is never in the copy path to begin with.

**Repair direction:** either run `_scrub()` (or a filename/content pass using the same
`_SECRET` regex) over every file `sync_tree()` copies before `git add -A`, or extend
`SKIP_SUFFIX`/add a filename denylist for the classic secret-file shapes (`.env`, `*.pem`,
`*token*`, `*credentials*`, `*secret*`). As written, the protection the docstring advertises does
not extend to most of what actually gets pushed.

---

## MEDIUM

### M1. dashboard.py — read-modify-write race on `dashboard_history.json`, unguarded, under a multithreaded server

**VERIFIED** by reading the concurrency model directly.

- `dashboard.py:708-710`:
  ```python
  class Server(socketserver.ThreadingTCPServer):
      allow_reuse_address = True
      daemon_threads = True
  ```
  Every `GET /api/state` is handled on its own thread.
- `dashboard.py:335-346` (inside `movement()`, called from every `state()` call, i.e. every
  request, with no `_ttl` cache):
  ```python
  hist = []
  if os.path.exists(HISTORY):
      with open(HISTORY, encoding="utf-8") as f:
          hist = json.load(f)
  hist.append(row)
  cutoff = time.time() - 24 * 3600
  hist = [h for h in hist if h.get("at", 0) > cutoff][-2000:]
  tmp = HISTORY + ".tmp"
  with open(tmp, "w", encoding="utf-8") as f:
      json.dump(hist, f)
  silence.replace_retry(tmp, HISTORY)
  ```
  This is read-modify-write with no lock. Two concurrent `/api/state` requests (two open browser
  tabs on the dashboard, or a `curl` alongside the open tab — both entirely normal usage) can both
  read the same `hist`, both append their own row, and the second writer's `os.replace` silently
  wins, dropping the first row. The write itself is safely atomic (`silence.replace_retry`); the
  *read-then-append* is not.

**Impact is bounded**: history is a best-effort 5-second-cadence sample used only to compute
deltas, so a lost row just delays the next delta by one tick rather than corrupting anything.
Rated MEDIUM rather than HIGH for that reason — but it is a genuine, reachable lost-update race
in a module that otherwise consistently uses atomic-replace correctly.

**Repair direction:** guard the read-modify-write with a `threading.Lock()` (the module already
has `import` access to what it needs; no cross-process concern here since this file is only
written by this one server process).

---

### M2. gpu_lane.py — `_remove_retry`'s "the return value is the observation" claim is false; nothing reads it

**VERIFIED** by grep across every call site.

- `gpu_lane.py:378-382`:
  ```python
  except Exception:
      _ = ("silence-exempt: the outcome is carried in this function's RETURN VALUE, "
           "which is the observation. Raising would break fail-open, and the lease "
           "expiry is the backstop. (A # comment does not satisfy the silence audit -- "
           "it reads the AST, where comments do not exist.)")
  ```
  (The project-wide `silence-exempt` idiom is legitimate and used consistently in ~20 other sites
  across the tree — chain.py, completeness.py, coverage.py, feats.py, pipeline.py, etc. — for
  genuinely-expected states like "no cache file yet." That part is not the finding.)
- The finding is that this *specific* justification is checkable, and false: every call site of
  `_remove_retry` discards its boolean return value —
  `gpu_lane.py:209`, `:237`, `:273`, `:284`, `:452` — none of them are `if not _remove_retry(...):`
  or assign the result to anything inspected afterward.
- Net effect: a *persistent* lease-file removal failure (e.g. a stuck Windows file lock — the
  exact class of hazard `silence.replace_retry`'s own docstring in `silence.py` documents as a
  measured, real occurrence on this project's state files) is invisible everywhere: not in
  `state/failures.json`, not returned-and-checked by any caller. The system still self-heals
  (the lease naturally expires per the module's own fail-open design), so this is not a
  functional bug — but it directly reproduces the "quiet refusal is the most expensive kind"
  failure mode `gpu_lane.py:36-37` itself names as the reason this module exists, for the one
  scenario its own comment claims is covered.

**Repair direction:** either call `silence.note()` on the persistent-failure branch (matching
every other genuinely-unexpected-failure site in this file), or correct the comment to state
plainly that this failure class is deliberately unobserved and rely-on-the-lease-backstop only.

Everything else in `gpu_lane.py` — the Windows `_alive()` PID-check rewrite, the depth-counted
reentrant `foreground()`, the heartbeat thread keeping both the slot and the foreground claim
alive, `O_CREAT|O_EXCL` for the slot mutex, `status()`'s "every holder, never a sample" — is
correct, unusually well-documented, and internally consistent with its own stated design. This
module's high count of `except`/`suppress` sites is intentional fail-open design, not carelessness;
the one gap above is the only place a documented safety claim doesn't hold up under a grep.

---

### M3. hosts.py — `hosts_for()` filters the `"pages:"` sentinel but not the `"doc:"` sentinel, unlike its sibling check in health.py

**VERIFIED live**, with actual data.

- `hosts.py:69`:
  ```python
  if p and not str(p).startswith("pages:"):
      out.append(p)
  ```
- `health.py:210` does it correctly for the same file: `if h.startswith("pages:") or
  h.startswith("doc:"):` — recognizing **both** sentinels `WIKI_HOSTS.json` can legitimately
  hold. `ingest_doc.py:110` is what writes the `"doc:"` sentinel: `hosts[source] = "doc:" +
  slug(source)`, for sources ingested from a local document rather than a web host.
- Checked `data/WIKI_HOSTS.json` directly: **exactly one source currently carries a `"doc:"`
  value** — `"Arcanum Worlds (Odyssey of the Dragonlords)"` — and four carry `"pages:"` values
  (which *are* correctly filtered). `hosts_for()` and `coverage()` (`hosts.py:193-202`) both
  currently count/return that `"doc:..."` string as if it were a real, readable host.
- Blast radius today is narrow: `hosts_for()` has **no callers anywhere else in `src/`** (grepped
  — it is currently only used by `hosts.py`'s own `coverage()` and `--show` CLI), so this
  corrupts only `hosts.py`'s own reported stats and CLI output right now, not any pipeline
  decision. It is, however, exactly the kind of latent bug that becomes a real defect the moment
  a caller starts trusting `hosts_for()` as advertised ("a caller that wants everything can have
  it" — module docstring, line 23).

**Repair direction:** `not str(p).startswith(("pages:", "doc:"))`, matching `health.py`.

---

### M4. hosts.py — `add()` writes a shared data file with a bare `os.replace`, not `silence.replace_retry`, and nothing catches the failure

**VERIFIED.**

- `hosts.py:78-91`:
  ```python
  def add(source, host, evidence=None, score=None):
      ...
      tmp = EXTRA + ".tmp"
      with open(tmp, "w", encoding="utf-8") as f:
          json.dump(data, f, indent=1, ensure_ascii=False)
      os.replace(tmp, EXTRA)     # <- not silence.replace_retry
      return True
  ```
  `EXTRA` is `data/SOURCE_HOSTS.json` — a shared data file of the same class as `COVERAGE.json`
  and the others this project's own `silence.py` docstring specifically calls out as having
  independent readers ("the dashboard polls records and ASSAYS, standards scans readfeats") that
  can transiently hold a Windows file lock and make a bare `os.replace` raise `PermissionError`.
  Every comparable write in `dashboard.py`, `gpu_lane.py`, and `publish.py` in this same batch
  uses `silence.replace_retry` for exactly this reason; this is the one write in the batch that
  doesn't.
- There is no `try`/`except` around this call, and none around the call to `discover()` in
  `main()` (`hosts.py:215-225`) either — so a transient `PermissionError` here would propagate
  all the way out of `hosts.py --discover` as an unhandled traceback, aborting the whole run
  (including any not-yet-`add()`-ed results still pending in the `ThreadPoolExecutor`), rather
  than retrying and continuing per this project's established convention.
- Currently `hosts.py` is not invoked by any other module (grepped — it is a standalone CLI, not
  wired into `allsweep.py`'s verifiers or `overnight.py`'s cycle), so this is not firing in
  production today; it is a real deviation from the established contract that should be fixed
  before this module is wired in more broadly, which its own docstring frames as the intent.

**Repair direction:** `silence.replace_retry(tmp, EXTRA)`, matching every other state-file writer
in this batch.

---

### M5. resonance.py — `hodge_decompose({})` raises an uncaught `ZeroDivisionError`

**VERIFIED by direct execution:**

```
$ python -c "import resonance as R; R.hodge_decompose({})"
RAISED: ZeroDivisionError division by zero
```

- `resonance.py:71-79`:
  ```python
  for _ in range(600):
      new = {}
      for n in nodes:
          ...
      shift = sum(new.values()) / len(new)          # gauge-fix: mean zero
      theta = {n: v - shift for n, v in new.items()}
  ```
  When `edges` is empty, `nodes = sorted({n for e in edges for n in e})` (`resonance.py:62`) is
  `[]`, so the inner `for n in nodes` loop never runs, `new` stays `{}`, and
  `len(new)` is `0` — dividing by it crashes on the very first outer iteration. The eta
  computation three lines below (`resonance.py:88`) already guards this exact class of edge case
  (`eta = (grad_sq / total) if total > 0 else 1.0`); the gauge-fix step does not.

**Repair direction:** `shift = sum(new.values()) / len(new) if new else 0.0` (or return a
sentinel result immediately when `not edges`, before entering the loop at all).

### M6. resonance.py — the module's public API has zero call sites anywhere in `src/`, including the one feature it says it feeds

**VERIFIED by exhaustive grep** (`hodge_decompose(`, `incomparability_rate(`, `resonance_strength(`
against every file under `src/`, matches excluded for `def `): no call sites found anywhere.

- `custodes.py:297` (docstring for `convene()`): *"`eta` (from resonance.hodge_decompose) lets
  Threnody exercise her veto: where the contest structure is substantially curl, no scalar is
  faithful and the college says so rather than averaging harder."* `convene()` does correctly
  implement the veto when given `eta` (`custodes.py:349-354`), and `verify_math.py` exercises
  that branch with hand-supplied `eta=0.70`/`eta=0.99` test values — so the veto logic itself is
  tested in isolation.
- But the *real* production call to `convene()` — `anchors.py:190`, which is what
  `allsweep.py`'s `"the instrument"` verifier actually runs — never passes `eta` at all:
  ```python
  col = CU.convene(a["anchor"], a["scores"], attestation=a["attestation"], worksheet="anchors.py")
  ```
  `eta` defaults to `None` (`custodes.py:289`), so the veto branch (`if eta is not None and ...`,
  `custodes.py:349`) is unreachable in the live pipeline today. Nothing anywhere computes an
  `eta` from real contest data and threads it into this call.
- `weave.py:467` independently confirms the *data* side was meant to connect:
  `"shared_sample": shared[(a, b)]}   # WHOLE list (key name kept: resonance.py reads it)` — i.e.
  weave.py deliberately shapes its output for `resonance.resonance_strength()` to consume — but
  nothing calls that function either.

This is not a bug in `resonance.py`'s own arithmetic (aside from M5 above) — it is a confirmed,
verifiable gap between three modules' stated intent and what actually runs: the "Threnody veto,"
described as a real safety mechanism in `custodes.py`'s own docstring, never fires in the current
pipeline. Flagged as dead code per the audit brief's item 6, at MEDIUM because it is a designed
safety valve that the project's own documentation describes as active and it is not.

---

## LOW

- **dashboard.py:157** — `c = sqlite3.connect(path)` in `throughput()` is never closed (no
  `with`, no `c.close()`). Called on every `/api/state` request. CPython's refcounting GC closes
  it promptly in practice, so this has not caused an observed failure, but it is not a guaranteed
  close and does not match the `with`-block hygiene used everywhere else file/db handles are
  opened in this file.
- **dashboard.py:247-248** — `_library()`'s `with_host`/`without_host` counts use bare
  `hosts.get(s)` truthiness against the raw `WIKI_HOSTS.json` dict, which does not exclude the
  `"pages:"`/`"doc:"` sentinel values either (same underlying data as M3, checked independently:
  5 of 203 sources are sentinel-only). The Library panel's "sources with a host" stat is
  therefore overcounted by up to 5 (~2.5%). Same root cause as M3, different call site.
- **dashboard.py:525-533** — inside `panelMovement`'s JS, a local `let ... cls=''` shadows the
  page-global `const cls=f=>...` classifier function defined at the top of `<script>`
  (`dashboard.py:515`). Verified intentional and harmless (the local `cls` is used purely as a
  CSS class string within its own closure, and `panelMovement` never needs the global classifier)
  — flagged only because shadowed names are an explicit audit target; no behavioral effect.
- **gpu_lane.py:439-440** — `except Exception: raise` is a no-op; a bare `try/finally` without
  the `except` clause would behave identically, since nothing in the block is suppressed or
  transformed. Purely cosmetic/dead.
- **gpu_lane.py:278-279** — `_take_slot`'s `except Exception: return None` aborts scanning the
  *remaining* slot indices entirely on any unexpected error touching one slot file, rather than
  continuing to the next index. Documented as deliberate ("cannot arbitrate — caller proceeds
  unmetered"), so this is a design choice, not a confirmed bug; noted for completeness only.
- **hosts.py:44-50** — `_load()` calls `silence.note("hosts.py:load")` unconditionally on any
  read failure, including the ordinary "file does not exist yet" first-run state, unlike the
  `silence-exempt` idiom used consistently elsewhere in this codebase (chain.py, completeness.py,
  coverage.py, etc.) for the identical scenario. Not currently firing (`SOURCE_HOSTS.json`
  already exists, `state/failures.json` has no `hosts.py:*` entries today) but would add noise
  to the swallowed-failures ledger the first time it runs against a missing file.
- **resonance.py:141-143** — `resonance_strength()`'s file open/`json.load` has no exception
  handling at all (the only function in this seven-module batch with zero `try`/`except`
  anywhere), unlike the defensive-read convention used throughout the rest of the project. Low
  severity because the function is currently unreachable (see M6).

---

## HARD RULE 0 — caps and truncation inventory

Every cap found across the batch, with a verdict on each:

| Site | What it bounds | Verdict |
|---|---|---|
| `dashboard.py:78,92` `_tail_match(keep=400)` | recent log lines scanned for the newest matching progress line | **Judgment call.** Reads a log tail for the *most recent* status line, not a catalogue; documented performance bound (avoids reading tens-of-MB logs every 5s). |
| `dashboard.py:301` `sorted(...)[:6]` | swallowed-failure *breakdown* rows shown in the Watch panel | **Judgment call.** `swallowed_total` (line 302) still reports the true full sum; only the itemized top-6 display list is capped. |
| `dashboard.py:293-296` `[:160]` on `f.get("actual")` | one finding's description text in the Watch panel | **Judgment call — display truncation of a single string field**, not a roster/entry-list cap. The comment at line 296 explicitly notes the finding-count itself was deliberately made uncapped ("ALL open findings — a monitoring cap ruled a truncation, 2026-08-24"). |
| `dashboard.py:342` `[-2000:]` on 24h of history | in-memory movement-history buffer | **Judgment call.** Time-series measurement buffer, not catalogued content. |
| `dashboard.py:366` `tail_bytes=250_000` | metrics ledger tail read | **Judgment call.** Explicitly documented ("the panel wants the recent past, not an archaeology dig"). |
| `hosts.py:143` `names[:40]` | entity-name sample used to *score* a candidate secondary host | **Judgment call.** A statistical probe sample for host-quality testing, not a truncation of the source's actual catalogued roster. |
| `hosts.py:156-157` `cands[:per_source]` (default 24) | speculative candidate hosts probed per source | **Judgment call**, and explicitly documented as such at `hosts.py:152-155`: the bound sits after grounded evidence and only trims *guessed* subdomains, never known hosts. |
| `audit.py:145` `v[:4]` | example violation rows printed per failure category | **Judgment call.** The full count and rate (`len(v)`, `rate`) are always reported in full; only the illustrative examples are capped, with an explicit "...and N more" line. |
| `audit.py:117,157,170` `--sample 14`, `min(10,len(banded))` | random human-readable QA samples | **Judgment call**, and explicitly named as such in the module's own top docstring ("SAMPLE a seeded random draw... Invariants catch violations of rules we thought to write; reading catches the rest"). The exhaustive `audit_invariants()` pass that runs first covers every entry with no cap at all. |
| `resonance.py:124` `examples` capped at 5 | illustrative incomparable pairs returned alongside the exact `pairs`/`incomparable`/`rate` totals | **Judgment call.** The rate and counts are exact over the full `itertools.combinations` sweep; only the example list is bounded. |
| `publish.py:322` `sorted(code)[:6]` + `+N` | file names listed in the auto-generated commit message | **Judgment call, and inconsequential either way** — `git add -A` (line 303) stages and commits every changed file regardless; only the human-readable *commit message summary* is abbreviated, with the remainder counted, never hidden. |

**No violation was found in this batch.** Every cap present bounds a measurement/probe/display
sample and is either explicitly documented as such in the code itself or leaves the underlying
count/total exact and uncapped alongside the capped display list.

---

## Per-module summary

- **dashboard.py** — NOT clean. 1 HIGH (H1, the movement/stall false-positive — this is the
  hazard the task asked to verify, confirmed real), 2 MEDIUM (M1 history race; the sqlite leak
  and sentinel-counting issues are graded LOW), 2 LOW. Design and Hard Rule 0 discipline are
  otherwise excellent (fault-isolated panels, explicit "ALL open findings" comment, atomic
  writes via `silence.replace_retry`).
- **gpu_lane.py** — NOT clean, but close. 1 MEDIUM (M2 — the one place a documented safety claim
  doesn't survive a grep), 2 LOW (cosmetic). The 13 swallowed-failure sites this module carries
  are, on inspection, a deliberately and thoroughly documented fail-open design, not evidence of
  carelessness — this is the strongest-documented module in the batch.
- **publish.py** — NOT clean. 1 HIGH (H2 — the scrub-coverage gap; no live secret found today,
  but the docstring's guarantee does not cover most of what actually gets pushed), 1 MEDIUM
  (fragile un-verified string splice in `render_page()`). Credential hygiene around `git`/`gh`
  env vars themselves (stripping `GITHUB_TOKEN`/`GH_TOKEN`) is correctly handled.
- **context_budget.py** — **CLEAN.** No correctness bugs found. Verified against its own
  downstream consumer (`manifest_builder.py:328-334`): the documented "return value can be zero
  or negative, callers must not clamp it" contract is honored correctly (`if budget <= 0: raise
  ContextOverflow(...)`). The prose/content chars-per-token split matches the measured values
  cited in its own header, checked against the live `prompts/system_style.txt` (6,963 voice-half
  chars measured vs. 6,964 documented — a one-character rounding note, not a bug).
- **hosts.py** — NOT clean. 2 MEDIUM (M3 sentinel-filtering gap, M4 bare `os.replace` on a
  shared data file with no fallback), 1 LOW. No Hard Rule 0 violations — every roster this module
  processes (sources, hosts-per-source) is handled in full; the two caps present are documented,
  bounded probe/scoring samples.
- **audit.py** — **CLEAN.** No correctness bugs found. The exhaustive `audit_invariants()` pass
  runs over every catalogued entry with no cap; all display/sample caps are explicit, documented,
  and leave exact totals intact alongside them.
- **resonance.py** — NOT clean. 2 MEDIUM (M5 verified crash on empty input, M6 verified dead
  code / inert safety mechanism), 1 LOW (no defensive read handling, consistent with its
  currently-unreachable status). The mathematics itself (Hodge decomposition, Pareto
  incomparability) is implemented correctly for all non-empty inputs checked.
