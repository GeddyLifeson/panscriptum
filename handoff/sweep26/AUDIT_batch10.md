# BATCH 10 — Audit (run26)

Modules (full line-by-line read, no sampling):
- src/rigor.py (866 lines)
- src/gpu_lane.py (480 lines)
- src/reference.py (359 lines)
- src/weave_index.py (277 lines)
- src/autostart.py (219 lines)
- src/catalogue_models.py (172 lines)

Total: 2,373 lines.

---

## MAJOR findings

### 1. gpu_lane.py:267-273 — corrupt slot lease file is never reclaimed (asymmetric with foreground_active)

```python
def _take_slot(label):
    for i in range(MAX_SLOTS):
        path = os.path.join(LANE, f"slot.{i}.json")
        rec = _read(path)
        if rec is not None and _expired(rec, SLOT_LEASE_SECONDS):
            _remove_retry(path)
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue
```

`_read()` returns `None` both when the file is genuinely absent *and* when it exists but fails
`json.load` (truncated/corrupt write — plausible on this project's own documented history of
processes dying mid-write, e.g. m40/m42/M5). `_take_slot`'s `rec is not None and _expired(...)`
guard means a corrupt slot file is **never** passed to `_expired()` and never reclaimed — the
`O_EXCL` open then permanently fails with `FileExistsError` for that slot index, for the life of
the state directory. This silently reduces the effective `MAX_SLOTS` by one per corrupted file,
forever, directly contradicting the module's own stated contract ("a corrupt claim file ... all
of them end in 'go ahead anyway'", line 34).

Compare `foreground_active()` (line 207-208), which does it correctly:
```python
rec = _read(path)
if _expired(rec, CLAIM_LEASE_SECONDS):   # no `rec is not None` guard
    _remove_retry(path)
```
`_expired(None, ...)` returns `True` via `not isinstance(rec, dict)`, so foreground claims *do*
self-heal from corruption; slots do not. Same file, two near-identical functions, one right one
wrong — fix by dropping the `rec is not None` guard in `_take_slot` (or by having `_read`
distinguish "absent" from "corrupt" and having both callers treat corrupt as expired).

### 2. gpu_lane.py — no circuit-breaker for the documented "resident, no runner, 503 for 31 min" failure

The module's own header names this exact failure mode as a known past incident. `lane()` only
arbitrates *admission* (who gets a slot) and keeps a slot's lease alive via `_heartbeat()`, which
refreshes every `_BEAT_SECONDS` (~100s) **unconditionally**, with no knowledge of whether the
enclosed call is making progress or spinning on repeated 503s. If a caller is stuck retrying
against a wedged daemon for 31 minutes inside `with gpu_lane.lane():`, the heartbeat will happily
keep the slot "alive" the entire time — up to `MAX_SLOTS` (default 2) calls can be consumed this
way, at which point every other caller in the library queues for the full `SLOT_LEASE_SECONDS`
(900s) before fail-open kicks in. The module can only make that scenario worse (by holding slots
hostage), never detect or interrupt it — there is no maximum in-lane duration independent of the
heartbeat's own renewal. Worth a session-duration ceiling distinct from the lease-renewal beat, or
requiring the caller to signal genuine forward progress (e.g. touch on each successful token, not
on a fixed timer) if this is meant to be the actual defense against that incident class.

### 3. weave_index.py — no `_BAD_CHARS` control-character guard, despite being the module most exposed to it

4 of the 6 batch-10 modules (rigor.py, reference.py, autostart.py, catalogue_models.py) carry the
project-wide guard against a regex escape arriving as a literal control character (documented in
rigor.py's header as having silently broken gates "five separate times" in this project — "a gate
that passed nothing, a parser that found zero rows"). `weave_index.py` and `gpu_lane.py` have no
such guard. `weave_index.py` is the more exposed of the two: `_STRIP`, `_EARTH` and the
parenthetical-parsing regexes in `norm()`/`continuity_of()`/`designations()` are exactly the kind
of pattern the guard exists to protect, and this module IS the cross-source collision detector —
a silently-eaten `\s+`/`\(`/`\w` escape here would show up as exactly the failure mode the guard's
docstring warns about: a normalizer that quietly matches nothing, producing an empty or
wildly-wrong candidate set with no error raised. Recommend porting the guard into
`weave_index.py` at minimum, given the regex density.

### 4. catalogue_models.py:146 — `available_sample` truncates a HARD RULE 0-forbidden `[:8]` into a persisted JSON artifact

```python
stale.append({"provider": name, "wants": a, "available_sample": r["models"][:8]})
```
This is written into `payload["stale"]`, which is persisted via `silence.write_json(OUT, ...)` to
`data/PROVIDER_MODELS.json` — a file the module's own comment says `standards.py` polls on its own
cycle. This is a literal `[:N]` slice of a real data list into a machine-consumed artifact, and the
field is even self-labeled "sample" — the exact pattern Hard Rule 0 names by name ("no sample").
The full model list *is* still present elsewhere in the same payload (`payload["providers"][i]["models"]`
is unsliced), so no data is destroyed, but any consumer reading `stale[].available_sample` directly
(as `standards.py` polling this file plausibly does, to suggest a replacement model) sees only 8 of
however many models the provider actually serves — for a large catalogue this could omit the
correct replacement entirely. Classify: real cap on a field a downstream consumer is documented to
read; not merely a print. Line 153 (`", ".join(r["models"][:10])`) is console-print-only for human
review during a `sweep()` run and is a legitimate display bound by contrast.

### 5. catalogue_models.py:88-106 — "answered with zero/unparseable models" is indistinguishable from "provider unreachable"

Per the task's special focus (does the module record a non-answering provider as "serves nothing"
vs "unknown"): `ask_provider()` only returns early on a non-empty `ids` list. If a provider replies
`200 OK` with valid JSON but the response's shape doesn't match the two schemas the parser
understands (`{"data": [...]}` or a bare list, entries keyed `id`/`name`), or if it genuinely serves
zero models right now, `ids` stays empty and the loop falls through to
`return {"provider": name, "error": locals().get("last", "no model list endpoint")}` — the exact
same generic error string used for a network failure, 401, 404, or timeout on both `LIST_PATHS`
tries. There is no distinct category for "the endpoint answered but I couldn't parse or it was
truly empty" vs "the endpoint never answered." Additionally, `last` is a plain local variable
reused across the `for url in tries` loop: if the *first* URL raises (setting `last`) and the
*second* URL succeeds with `200 OK` but empty content, the function reports the **first URL's
stale exception message** as the reason, even though the actual final state was a successful-but-
empty response. Recommend a distinct `{"provider": name, "status": "empty"|"unparseable"|"error", ...}`
shape, and resetting/not-reusing `last` across independent URL attempts.

---

## MINOR findings

- **rigor.py:88-91 / catalogue_models.py:47-49 / reference.py:58-61 / autostart.py:41-43** — the
  `_BAD_CHARS` guard opens the module's own source file via bare `open(...).read()` with no context
  manager (`with`) and never closes the handle. Harmless under CPython's refcounting GC but not
  idiomatic; flagging once since it's the same pattern copy-pasted across 4 files.
- **autostart.py:111-112** — `start_supervisor()` opens `out`/`err` log file handles and hands
  them to `Popen` without an explicit `.close()` in the parent; relies on CPython refcounting to
  close them when the function returns. Fine today, but if the watchdog ends up restarting a
  crash-looping supervisor rapidly (its own stated purpose), an interpreter without prompt
  refcounting (or an exception thrown between the two `open()` calls) would leak descriptors in a
  process explicitly designed to run for the machine's uptime.
- **autostart.py:45** — `PY = sys.executable`, used both for the installed Startup `.vbs` and for
  `start_supervisor`'s `Popen`. Per this machine's standing "pythonw over python" rule: the `.vbs`
  path is hidden via `WScript.Shell.Run(..., 0, False)` and the `Popen` path uses
  `CREATE_NO_WINDOW`, so no window should actually appear either way — but if `--install` is ever
  run from a `pythonw.exe`-less environment or the caller's own interpreter is `python.exe`, the
  persisted Startup shortcut inherits whatever `sys.executable` was at install time rather than
  deliberately pinning `pythonw.exe`.
- **reference.py:232-246** (`shelfmark`) — assumes `rec["tier_key"]` always splits into exactly 3
  `.`-separated parts (so `upper` has exactly 3 elements) to align `RUNGS[3+i]` for the lower rungs
  with no off-by-one. True for all 3 current entries (`1.6.1`, `4.2.0`, `1.2.5`) but unvalidated —
  a future reference entry with a differently-shaped `tier_key` would silently misalign the
  Shelfmark's rung labels rather than error.
- **reference.py:276** (`_vernacular`) — docstring says "a band divides into thirds" but the
  thresholds used are `0.32`/`0.66`, not the exact thirds `0.333.../0.667...`. Cosmetic only.

---

## QUESTIONS (for owner / follow-up, not confirmed bugs)

- **weave_index.py:215** — entries whose normalized name collapses to `_STOPNAMES` (or length < 3)
  are `continue`d out of `index` entirely, not just excluded from cross-source candidate matching.
  The module's own docstring claims `ENTITY_INDEX.json` feeds "Collection V.1-V.11, the master
  alphabetical registry" for the Persons A-Z volume. If that volume is actually built by iterating
  `ENTITY_INDEX.json`'s keys (rather than the raw `data/records/*.json`), any genuinely-named
  entity whose normalized name happens to equal a stopword ("Father", "King", "Unknown" as an
  actual in-fiction alias, etc.) would be silently absent from that master registry — the exact
  shape Hard Rule 0 forbids ("a cap does not fail, it returns a smaller universe wearing the same
  shape as the real one"). Could not verify from this batch alone whether the downstream
  Collection V builder reads `ENTITY_INDEX.json` directly or re-derives from `data/records/`;
  worth checking the actual consumer.
- **weave_index.py:224** — `"description": (e.get("description") or "")[:400]` is a literal `[:N]`
  truncation persisted into both `data/ENTITY_INDEX.json` and `data/WEAVE_CANDIDATES.json`.
  Doesn't drop an entity (unlike the stopname issue above), only shortens its evidence text in the
  index; the full description presumably still lives in the source `data/records/*.json` file.
  Flagging per Hard Rule 0's literal wording ("no truncation... `[:N]`") for owner classification —
  real cap on persisted evidence text vs. legitimate size bound for an index file.
- **gpu_lane.py** — the lane has no concept of *which model* a call is for; `MAX_SLOTS` (default 2)
  admits up to 2 concurrent calls regardless of model identity. If any caller in the 9-process
  fleet ever requests a model other than the pinned qwen3:8b while another call is in flight, this
  module would not prevent Ollama from being asked to hold two models resident at once — that
  invariant is enforced (if at all) entirely outside this file, by whatever fixes every caller to
  the same `config.yaml` model. Worth confirming there's no code path (fallback, override,
  CLI flag) anywhere in the fleet that can pass a different model through `lane()`.
- **autostart.py `_twin_watchdog()` (lines 121-145)** — fails **open on error** (`except Exception:
  return False`, i.e. "no twin found, proceed"), the opposite of the caution the function's own
  docstring says the twin check exists to enforce ("Three of these once ran at once ... shot
  [each other's stacks], and the whole arrangement respawned itself in a loop"). A transient
  PowerShell/WMI failure at boot (plausible — many things start at login) would let a second
  watchdog proceed exactly as if it had confirmed uniqueness. The check is also a one-shot,
  point-in-time process-list scan rather than an atomic file lock (contrast `gpu_lane.py`'s
  `O_CREAT|O_EXCL` approach), so two watchdogs launched within the same instant are subject to a
  TOCTOU race neither would detect. Given this project already hit the 3-watchdog cascade once,
  a file-lock-based twin check (matching gpu_lane.py's pattern) would be more consistent with the
  fail-open-except-where-it-caused-a-known-incident lesson already learned here.

---

## SPECIAL FOCUS verdicts

- **catalogue_models.py (stale-model detection)**: the mechanism is a live `GET /v1/models` sweep,
  not an aging cache — there's no "how the catalogue ages out" logic in this file at all (no
  timestamp comparison against a prior run, no staleness decay); every invocation is a fresh
  snapshot, which is honest but means nothing here can distinguish "this provider just started
  failing" from "dead for months" without an external diff against a previous `PROVIDER_MODELS.json`.
  On the specific ask — does a non-answering provider get recorded as "serves nothing" vs
  "unknown" — see MAJOR #5: the answer is **neither, cleanly**. A provider that never answers and a
  provider that answers with an empty/unparseable list both collapse into the same generic
  `{"error": "..."}` shape and both simply drop out of `live{}`, so from the report you cannot tell
  "confirmed empty" from "couldn't ask." Plus MAJOR #4 (`available_sample` truncation).
- **gpu_lane.py (qwen3:8b GPU-only residency)**: see MAJOR #2 and the QUESTION above. No CPU
  fallback logic exists in this file (it doesn't touch Ollama at all, only local lock files), so
  that specific risk isn't introduced here — but the file also provides *no defense whatsoever*
  against the documented "resident, no runner, 503 loop" incident; it can only extend the outage
  by holding slots for callers stuck retrying inside it.
- **autostart.py (3-minute watchdog restart claim)**: **verified correct as stated.**
  `CHECK_SECONDS = 180` (line 53) is the sole poll period of `watch()`'s `while True` loop
  (line 163-179): check `supervisor_alive()`, `start_supervisor()` if not, then
  `time.sleep(CHECK_SECONDS)` unconditionally. Worst-case detection-to-restart latency is bounded
  by one full `CHECK_SECONDS` (the supervisor dies immediately after a check just passed), so the
  "restarts within three minutes" claim holds given `start_supervisor()`'s `Popen` call is
  effectively instantaneous. The one caveat is `_twin_watchdog()` above — if a false "twin exists"
  read ever occurred this loop would never start, but as documented that function fails toward
  "no twin," not toward "twin present," so it does not undermine the 3-minute claim itself.

---

## Hard Rule 0 sweep (every `[:N]` / cap-shaped construct found, classified)

| Location | Construct | Classification |
|---|---|---|
| rigor.py:449 | `[c[:3] for c in comps][:4]` inside a refusal error *message string* | Display-only inside a human-readable diagnostic; `comps` itself (untruncated) is returned separately in `out["components"]`. Legitimate. |
| rigor.py:858 | `mr["load_bearing"][:6]` in `main()`'s print | Display-only; the returned field from `mathematical_resonance()` is explicitly never truncated (module's own comment at line 717-719 states this design). Legitimate. |
| catalogue_models.py:146 | `r["models"][:8]` written into persisted `stale[].available_sample` | **Real cap** — see MAJOR #4. |
| catalogue_models.py:153 | `r["models"][:10]` in a `print()` only | Display-only, console report during `sweep()`. Legitimate. |
| weave_index.py:224 | `description[:400]` written into persisted `ENTITY_INDEX.json`/`WEAVE_CANDIDATES.json` | Truncates evidence text, not the entity roster itself — see QUESTION above for owner classification. |
| weave_index.py:255 | `sorted(spread, reverse=True)[:10]` in `main()`'s print | Display-only. Legitimate. |
| weave_index.py:259 | `sorted(candidates.items(), ...)[:18]` in `main()`'s print (`top`) | Display-only. Legitimate. |
| weave_index.py:264 | `srcs[:5]` in `main()`'s print | Display-only. Legitimate. |
| rigor.py `bradley_terry(iters=500)`, `prob_at_least_one(n_samples=200000)` | Fixed iteration/sample-size bounds | Algorithmic convergence/Monte-Carlo bounds, not a data-roster cap. Legitimate. |
| gpu_lane.py `MAX_SLOTS`, `SLOT_LEASE_SECONDS`, etc. | Concurrency limits | Resource-arbitration bounds, not data caps. Legitimate. |

No caps found that silently drop entities from a generated volume/roster within this batch's six
files — the closest candidate is the `weave_index.py` STOPNAMES exclusion, filed as a QUESTION
above since it needs the downstream consumer traced to confirm.

---

## Two-writer contract / concurrency notes

- `weave_index.py` writes via `silence.write_json(OUT_INDEX, ...)` / `silence.write_json(OUT_CAND, ...)`
  — correct, not writing into `data/records/`, so `pipeline.write_record` doesn't apply here.
- `catalogue_models.py` writes `data/PROVIDER_MODELS.json` via `silence.write_json` — correct.
- `reference.py` writes `data/REFERENCE_ASSAYS.json` via `silence.write_json` — correct.
- `gpu_lane.py` uses `silence.replace_retry` for every claim/slot/heartbeat write (`_write_claim`,
  `_touch`) and a retrying `_remove_retry` (documented against m55, a Windows rename-denied race)
  for every delete — consistent with the two-writer contract's shared-state half. No bare
  `os.replace`/`os.remove` found anywhere in this file.
- `autostart.py` writes only to its own private log files (`autostart.log`,
  `overnight_stdout.log`, `overnight_stderr.log`) via plain `open(..., "a")` appends — not shared
  mutable state in the `silence.replace_retry` sense, append-only logs, no conflict with the
  contract.

---

## Subprocess/window-spawn audit (autostart.py, per instructions)

| Site | Flags used | Verdict |
|---|---|---|
| `_vbs_body()` → `sh.Run cmd, 0, False` (VBScript, line 75) | Window style `0` (hidden), `False` = don't wait | Correct — no window. |
| `start_supervisor()` → `subprocess.Popen([...], creationflags=flags)` (line 116-118) | `CREATE_NO_WINDOW \| DETACHED_PROCESS` on `nt` | Correct. |
| `_twin_watchdog()` → `subprocess.run(["powershell", ...], creationflags=...)` (line 125-130) | `getattr(subprocess, "CREATE_NO_WINDOW", 0)` | Correct — degrades to `0` off-Windows rather than crashing. |

All three spawn sites in this module use `CREATE_NO_WINDOW` (or the VBS hidden-run equivalent).
No missing-flag spawn sites found in autostart.py.
