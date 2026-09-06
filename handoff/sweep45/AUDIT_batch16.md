# sweep45 — batch 16 audit

Read-and-report only. No source file was edited. The standing DRILL_BREACH halt was left in
place; `drill.py`, `verify_math.py`, `allsweep.py`, `publish.py` and `mutate.py` were not run.

## Coverage

All eight modules read **whole**, top to bottom, no sampling — 5,378 lines.

| module | lines | read |
|---|---:|---|
| `src/local_agent.py` | 1335 | all |
| `src/binding_health.py` | 1266 | all |
| `src/scout.py` | 748 | all |
| `src/liveness.py` | 607 | all |
| `src/tiers.py` | 473 | all |
| `src/pantheon.py` | 372 | all |
| `src/runguard.py` | 303 | all |
| `src/tempus.py` | 274 | all |

Recorded via `sweep_plan.record('sweep45', [...], batch=16)`.

---

## 1. `local_agent` write gating — first, as instructed

**No new way to write outside the allowlist was found, and no new way to reach a write without
passing every gate.** Stated at that strength because the gates were exercised, not merely read.

`_safe()` and `_denied_target()` were driven directly (pure functions, no writes) against ~40
path spellings: lower/upper/mixed case on both the module stem and the extension
(`src/Foreman.py`, `src/foreman.PY`, `SRC\FOREMAN.PY`), backslash and mixed separators,
doubled separators, `.` and `..` traversal from every writable prefix
(`handoff/../config.yaml`, `prompts/../state/HALT.json`, `src/../config.yaml`), drive-absolute
paths, sibling-prefix escapes (`...-EVIL`, `...-export`), NTFS alternate data streams
(`::$DATA`, `:Zone.Identifier`), trailing dot and trailing space, and `.git/`. **Every one
landed on the correct verdict** — denied, or refused outright by `_safe`. `src/prose_gate.py`
and `src/publish.py` are on the denylist and answer `True`.

The seven documented bypass classes are all closed in the code as written, including the two
that turn on asking *the same question of both spellings*: `_safe()` re-asks `_denied_target`
(all three refusals, not just the region prefixes) of the **resolved** path whenever it differs
from the written one, and `t_propose_patch` re-asks the **allowlist** of both spellings. That
pairing is what leaves no gap between them.

Things checked and found **not** to be defects (audits are wrong in both directions):

- **A revert failing while the run reports success** — traced every exit. `t_propose_patch`
  sets `reverted=False` and an `ALARM`; `run()` collects it into `unreverted`; `ok` is
  `not unreverted` on the answer path and already `False` on the turn-budget path, which also
  carries the ALARM (order d185007c4b8b's fix is present). The one way the ALARM could be lost
  is `silence.note` raising before the re-revert at `:941` — and `silence.note` is total by
  construction (`silence.py:767-799`, `except Exception: pass`). Closed.
- **The model forcing `apply=True` under `--no-apply`** — `args` is splatted alongside the
  explicit `apply=`/`log=` keywords, so a model-supplied `apply` raises `TypeError`, caught at
  `:1262` and returned as an error dict. Fails closed.
- **`_gates` being skipped for a non-`.py`** — it is called unconditionally at `:926`; the
  per-format parse branches are all case-folded and `verify_math` runs for every file type.
- **`_gates` raising instead of returning** — every raise lands inside the `try` opened at
  `:923`, so the file is reverted.
- **Under the standing halt**, `verify_math` refuses, `_gates` returns
  *"produced no readable result line"*, and the patch is reverted. Fails closed.

**Filed (INFO): `f29382aa7911` — `LOCAL_AGENT_EMPTY_FILE_ACCEPTS_AN_EMPTY_FIND`** (RUN, since
`local_agent.py` is on its own denylist). `original.count("") == 1` for a zero-byte file, so
`find=""` clears the uniqueness test and `"".replace("", replace, 1)` writes the whole file.
Not a gate bypass — the target still passes every allow/deny check and must already exist, and
no zero-byte file sits on the writable surface today. What it costs is the *"copy it verbatim
from read_file"* contract, which is what makes a patch evidence the model read the target.

**Corroborated, already open, not refiled:**

- `556c1b8fda9f` — NTFS **hard links** defeat the junction defence, because `realpath` does not
  resolve them. Still true of the code as it stands; this remains the one live hole in the path
  gating and it is already filed.
- `e8622cf0d047` — `:931` `why[:200]` is unguarded while every sibling use is `(why or "")`; a
  model sending `"why": null` throws away a patch that passed every gate and reports a
  `TypeError` instead. Still present verbatim.
- `eb681053b234` — the pyflakes lint gate. **Partially remedied since filing**: it now carries
  `env=dict(os.environ, PYTHONIOENCODING="utf-8")` (`:667`). The order's core is still open —
  there is still no `encoding=`/`errors=`, so `text=True` decodes with the platform default
  under `errors='strict'`.
- `cca253138a62` — the per-tool-call console trace at `:1265-1266` still cuts
  `json.dumps(args)[:90]` and `json.dumps(res)[:110]` with no marker.

---

## 2. Filed this batch

| id | handler | sev | subject |
|---|---|---|---|
| `13aee150e0dc` | SESSION | MINOR | `codewatch` uses `runguard.holder_is_live` to pick an escalation **rung** |
| `b8547f32bef0` | LOCAL | MAJOR | `scout.sweep` reads an unreadable ledger as empty, then **deletes** stamps |
| `a8eb06d38216` | LOCAL | MINOR | `pantheon` roster merge fails silently — 6 of 21 printed, no marker |
| `962bc293ec32` | RUN | INFO | `liveness` dead-class pass filters class names through the **function** table |
| `f29382aa7911` | RUN | INFO | `local_agent` empty-file `find=""` |

### `13aee150e0dc` — the `holder_is_live` question the brief asked

`holder_is_live` has exactly two consumers outside `runguard` itself: `verify_math`'s test rows,
and `codewatch._maintenance_run_live`. **Nothing uses it to decide whether a safety fires.**
What it does decide is the **rung**: `codewatch.py:675-676` picks `escalation.JANITOR`
(rung 0 — *"record it. No authority to stop anything"*) when a maintenance run is heartbeating,
and `MANAGER` (rung 4 — *"stop the SUBSYSTEM"*) when it is not. The escalation always fires;
restarts and the restart budget are untouched, exactly as the helper's docstring claims. But the
helper also says, in capitals, *"ASKED ONLY TO DESCRIBE, NEVER TO DECIDE"* — and it ranks. While
anything is heartbeating `state/MAINTENANCE_RUN.json`, the one alarm meaning *"something is
rewriting `src/` that nobody asked for"* is filed at the rung with no authority. Filed with both
readings and a small remedy; deliberately **not** framed as "a signal disarms a safety", because
it does not.

### `b8547f32bef0` — the sharpest defect in the batch

`scout` states *"an unreadable shared artifact is not an empty one"* three times
(`:120-136`, `:525-528`, `:531-534`) and then breaks it on both of `sweep()`'s own reads. The
serious limb: an unreadable `SCOUT_ATTEMPTS.json` at `:565` gives `seen = {}`, and `_unstamp` at
`:672-675` restores from that stale copy — `if seen.get(src) is None: seen_now.pop(src, None)`.
Every never-asked source therefore takes the **pop** branch and its prior timestamp is deleted
from the fresh file rather than restored, so it reads as never-attempted for ever and pins the
front of the rotation — the exact failure `sweep()`'s own docstring says it was rewritten to
remove. The window is narrow (a transient read failure at `:565` followed by a readable file at
`_mutate` time) but it is the ordinary Windows sharing violation this tree's ATOMIC comments are
about. Second limb: the `SCOUT.json` read handles unreadable but not wrong-shape, so a JSON
object there crashes `prev.append` after the whole cycle's fetches and model calls are spent.

---

## 3. Deliberate design — examined and **not** filed

- **`binding_health._BLOCKED_MARK = "refusal marker"`** looked like a textbook guard-that-cannot-
  fire (a literal matched against another module's message). **Verified against
  `feats.page_looks_real:251`**, which emits *"carries a refusal marker (%r)"*. The branch fires.
  Not a finding.
- **`runguard`'s compare-and-swap window** (`372d4a8c8d46`) and **its fail-open reads**
  (`70f66fbd98aa`) are both already open at OWNER. Read and agreed with; not refiled. The
  ownership rule — *a run may only ever refresh, or close, a record that carries its own name* —
  holds in all three of `claim`/`beat`/`release`, and all three take the digest before the read,
  which is the correct order.
- **`liveness.EXEMPT_MODULES = {}`** makes its conjunct always-true today. That is a documented
  empty hook with its reasoning written out, not a check; the class-pass instance
  (`962bc293ec32`) is different because it uses the **wrong table**, whose reasons would not
  match the finding.
- **`tiers`' module-level `assert`s** (`:123-124`) compare live constants and can genuinely fail
  if the cuts are edited. Not tautologies.
- **`tiers.main()`'s `monotone` flag** is explicitly labelled *"DIAGNOSTIC, NOT A GATE"* with the
  reason (three counts from two different builders); the containment scan is the gate and it does
  refuse. Correct as written.
- **`_probe_present`'s short-circuit on first hit** and `canary`'s skipping of the reachability
  probe when the present probe passed are both documented and sound.

## 4. Liveness count — is 48 honest?

The brief said 48 against a ceiling of 52. **Measured this shift it is 46**: 0 tautology,
0 phantom, 35 dead, 1 dead class, 10 dead module, 0 unparsed. `drill.LIVENESS_CEILING` is 52,
so six of headroom, and the ceiling's reason (the count moves during ordinary work, so a ratchet
standing exactly at the measurement breaches on the next honest addition) is written out at
`drill.py:41-63`.

**46 is honest on the module's own stated rules.** The `src/deprecated/` walk works —
`_modules()` returns 116 files and `deprecated/catalogue_local.py` is among them. It is not
reported as a dead module because `drill.py` names the string `catalogue_local`, and a string
naming a module counts as a reference by this module's explicit, argued rule. Its four functions
are not reported dead because their names (`load_cfg`, `slug`, `call`, `catalogue_source`) are
reached as attributes or from-imports elsewhere in `src/` — the documented "err toward used"
behaviour. Both are the module working as specified, not a blind spot.

## 5. Hard Rule 0 sites seen, folded into open orders

- `tiers.py:406` (`a[:26]`, `b[:26]`) — open as `1d1ac500342d` and in the gathered
  `fe99e57e1993`.
- **`tiers.py:428`** (`s[:26]` in the SAMPLE STACKS panel) is a **second site in the same file
  that neither order names**. Same shape, same fix; noted here rather than filed as a sixth
  order, since `fe99e57e1993` exists precisely to gather them.
- `binding_health.py:1251,1258` — open as `2e41f1efbd85`.
- `binding_health.py:486,692,826` (`str(e)[:120]`) — open as `ecc355769a41`.
- `binding_health.py:1075` (`quarantine()` called as a bare statement, `rec["landed"]` discarded)
  — open as `61c763a60779`.
- `tempus.DEGENERATE_TIME` dead (`0291835411d9`) and `tempus.concordance_now` dead
  (`1a9c237dda4d`) — both confirmed still true.
