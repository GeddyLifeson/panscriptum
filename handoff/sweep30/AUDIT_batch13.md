# AUDIT — sweep30, batch 13

Scope: `src/overnight.py`, `src/publish.py`, `src/onomast.py`, `src/backfill.py`,
`src/anchors.py`, `src/liveness.py`, `src/scale_theories.py`. Every line read top to bottom in
each file. **No committed secrets found in any of the seven files** — `_SECRET` /
`_SECRET_ASSIGN` in `publish.py` were tested against 40+ synthetic (fake) credential strings; see
finding 2.1-2.4 for what they do and do not catch.

Severity counts: **HIGH 6, MEDIUM 6, LOW 4** (16 findings total).

---

## 1. `src/overnight.py`

### 1.1 `coverage_snapshot()` discards `coverage.py`'s exit code — HIGH — REPRODUCED (by code inspection; the discard is unconditional)

`overnight.py:489-497`:
```python
def coverage_snapshot():
    try:
        subprocess.run([PY, os.path.join(SRC, "coverage.py")], cwd=HERE,
                       capture_output=True, text=True, timeout=1800,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"), creationflags=_NO_WIN)
        rows = json.load(open(os.path.join(HERE, "data", "COVERAGE.json"), encoding="utf-8"))
    except Exception as e:
        silence.note("overnight.py:124")
        return {"error": f"{type(e).__name__} {str(e)[:60]}"}
```
The `subprocess.run(...)` result is never assigned to a name — its `.returncode` cannot be
checked at all. If `coverage.py` crashes or is killed partway through but leaves the *previous*
`data/COVERAGE.json` on disk untouched (the normal outcome of a crash that never reaches its own
write step), `json.load` succeeds against the **stale** file and `coverage_snapshot()` returns it
as if it were a fresh measurement. `write_status()` then stamps it into `STATUS.md` under the
current cycle's timestamp, and `history.append(snap)` records it as a real data point — the
morning coverage graph silently repeats the last-good number instead of showing a flat/failed
cycle. This is confirmed as a *discarded return code* by direct code reading: there is no `r =`
assignment anywhere on that line, so no code path anywhere in this function can see the exit
status. Contrast with `preflight()` (:508) and `safety_drill()` (:546-549) three functions later
in the same file, which both correctly do `r = subprocess.run(...)` and branch on `r.returncode`
— `coverage_snapshot()` is the one outlier of the three near-identical subprocess wrappers.

**Fix (one line, as flagged)**: capture the result and check it before trusting the file it wrote:
```python
r = subprocess.run([PY, os.path.join(SRC, "coverage.py")], cwd=HERE, ...)
if r.returncode != 0:
    raise RuntimeError(f"coverage.py exited {r.returncode}: {(r.stderr or '')[:200]}")
rows = json.load(open(...))
```
The existing `except Exception` already turns that `RuntimeError` into `{"error": ...}`, and
`main()` already has a branch (:823-825) that prints `"coverage: SNAPSHOT FAILED"` when `error` is
set — the reporting path is already correct and waiting for this to feed it.

### 1.2 `write_status()` writes `STATUS.md` with a bare `open(p, "w")`, not `silence.replace_retry` — LOW — REPRODUCED (by code inspection)

`overnight.py:567-571`. Not `silence.write_json` (STATUS.md is Markdown, not JSON) but also not
`silence.replace_retry` for the same TRUNCATE-THEN-FILL reason that pattern exists to avoid. Risk
is low in practice: only one `overnight.py` process is ever running (enforced by
`running("overnight.py")` at :610), so there is a single writer, and the file's own audit trail
(:817-822) confirms nothing downstream parses `STATUS.md` programmatically — `publish.py` copies
it verbatim and a torn read there only produces a briefly garbled published doc that heals next
cycle. Flagging for completeness of the two-writer-contract sweep, not as an active hazard.

### 1.3 `overnight.py` itself: no other discarded-return-code or tautology issues found

`running()`, `run()`, `join()`, `preflight()`, `safety_drill()`, `foreman_report()`,
`watch_report()`, `ledger_report()` all check what they call and fail closed or log loudly. The
`_prose_enabled()` delegation to `prose_gate.gate_open()` is correctly fail-closed (any exception
→ `False`). No caps found; `top=6` / `top=8` in `watch_report`/`ledger_report` are console-summary
truncations only (full data still lives in `OVERWATCH.json`/`failures.json`), not data loss.

---

## 2. `src/publish.py` — SPECIAL FOCUS: what `_scrub()` actually catches

### 2.1 `_SECRET`'s vendor list: precise catch/miss table, tested against synthetic fakes — HIGH

Built `_SECRET` / `scrub_text()` test harness (scratch dir, `publish` imported read-only, no repo
files touched, no push). Randomized (non-repeating-character) fake values used throughout so
entropy checks are meaningful.

**Caught by LOCK ONE (`_SECRET`, vendor-prefix match) — REPRODUCED:**
OpenAI `sk-…` (incl. `sk-proj-…`), Groq `gsk_…`, Google `AIza…`, GitHub `github_pat_/ghp_/gho_/
ghs_…`, HuggingFace `hf_…`, `xai-…`, `csk-…`, AWS `AKIA…`/`ASIA…` access-key IDs, an
`aws_secret_access_key=` assignment, Slack `xox[abposr]-…`, Stripe `sk_live_/sk_test_/rk_live_/
rk_test_…`, DigitalOcean `dop_v1_…`, `npm_…`, SendGrid `SG.x.y`, Twilio `SK`+32-hex (API-key SID
shape), PEM `-----BEGIN ... PRIVATE KEY-----`, three-segment JWTs, generic `Bearer <token>`, and
`postgres://`/`mysql://`/`mongodb(+srv)://` URLs **with a non-empty username**.

**Missed by both locks entirely (no vendor pattern, and no name-context to trip LOCK TWO) —
REPRODUCED:**
Discord bot tokens/webhooks, Twilio **Account SID** (`AC…`, distinct from the API-key SID above),
Azure Storage connection strings, GCP/Firebase server keys, GitLab `glpat-…`, Shopify `shpat_…`,
Square `sq0atp-…`, Heroku-style bare API keys with no field-name context, and a **redis URL with
an empty username** — `redis://:PASSWORD@host:6379/0`, the single most common real-world redis
connection-string shape. Confirmed by direct regex test:
```
redis://user:PASSWORD@host       -> MATCHES  (has a username before the ':')
redis://:PASSWORD@host           -> DOES NOT MATCH
```
The alternation `(?i:postgres|...|redis|amqp)://[^\s:@/]+:[^\s:@/]+@` requires one-or-more
characters for the *username* group before the colon; an empty-username redis URL has zero
characters there, so `[^\s:@/]+` never matches and the whole line falls through unredacted into
the public repo.

**Comment/code contradiction (lens item 7) — HIGH:**
`publish.py:150-154` and `:163` both explicitly claim the widened list covers "**Discord**/npm/
Twilio/SendGrid tokens." There is no Discord pattern anywhere in `_SECRET` — grepped the whole
file for `discord` and it appears only in these two comments, never in a regex. A maintainer
reading the comment (which is the ONLY place in the file that summarizes what LOCK ONE covers)
would reasonably believe Discord tokens are caught. They are not, unless one happens to sit next
to a credential-shaped field name (LOCK TWO, see below).

### 2.2 `_SECRET_ASSIGN` (LOCK TWO, entropy-gated) — works as designed, but its coverage is conditional on a name — MEDIUM

Confirmed the entropy fallback genuinely fires for realistic random values: `api_key = "<32
random chars>"`, `password: '<20 random chars>'`, `secret_key = "<30 random chars>"`, and a
UUID-shaped `heroku_api_key=` all redact correctly (entropy ≥ 4.0 bits/char) once given real
pseudo-random test data — my first pass at this test used same-character filler strings (zero
entropy) and wrongly looked like a miss; re-run with `random.choice(letters+digits)` fixed that
and confirmed LOCK TWO is doing real work. **The residual gap is structural, not a bug**: LOCK TWO
only fires when the value sits in a `name = value` / `name: value` shape next to a
credential-sounding field name. A bare vendor token pasted into prose (a log excerpt in
`HANDOFF.md`, a provider error quoted in `BUGS.md`) with no `token=`/`key=` prefix is invisible to
both locks unless it also happens to match a LOCK ONE vendor prefix. This is exactly the scenario
`scan_for_secrets()`'s own docstring (:232-241) names as LOCK THREE's whole reason for existing —
LOCK THREE re-uses the same two regexes, so it inherits the identical blind spot.

### 2.3 `docs/state.json` write is a raw, non-PID-qualified `os.replace` despite a **documented** two-writer scenario — HIGH — REPRODUCED empirically

`publish.py:383-390` (`write()`):
```python
def write(state=None):
    os.makedirs(DOCS, exist_ok=True)
    data = state if state is not None else snapshot()
    tmp = STATE_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, STATE_JSON)
    return STATE_JSON
```
`push()`'s own docstring three functions later (:396-400) states outright: *"Two writers publish
into this tree (the standing loop and whatever session is working)."* `STANDING` in
`overnight.py` runs `publish.py --push --loop 10` as a standing background job, and the project's
own docs (`CLAUDE.md`, module docstrings throughout) describe ad-hoc manual `python
src/publish.py --push` runs as routine. Both processes call `write()` independently, and both use
the **same fixed tmp filename** `docs/state.json.tmp` — not the PID+thread-qualified name
`silence.write_json()` uses specifically to prevent this (see `silence.py:302-305`: *"Two writers
of the same path otherwise collide on the temp file itself, and the loser can replace the
winner's target with a partial file."*), and the final `os.replace` has no retry — unlike
`silence.replace_retry`, a `PermissionError` here is not absorbed with backoff, it propagates.

**Reproduced empirically** (scratch dir, no repo state touched): spawned two independent Python
processes running publish.write()'s exact logic (same non-PID tmp name, bare `os.replace`, no
retry) against the same target file for 400 iterations each while a third process read it. Result:
**516 of 800 write attempts (64%) raised `PermissionError`/`WinError 32` ("the process cannot
access the file because it is being used by another process")** — on both the `open(tmp, "w")`
step and the `os.replace` step. In real `publish.py`, an uncaught exception here is caught by
`main()`'s broad `except Exception` (:504-505), which logs `silence.note` and prints `"publish
failed: PermissionError: ..."` — meaning the **entire cycle** (sync_tree + render_page + write +
push) is thrown away, not just the one write, every time the two documented writers collide. This
is the two-writer-contract violation the audit lens calls out by name: shared state must go
through `silence.replace_retry` / `silence.write_json`, and this is the one write site in the
batch that plainly does not.

**Fix**: `silence.write_json(STATE_JSON, data, indent=1)` in place of the four lines above — it
already does the PID-qualified tmp name and the retry-with-backoff `write()` is missing.

### 2.4 Verdict on `_scrub()`'s real coverage

The 2026-08-25 widening genuinely fixed most of what the docstring's "original eight prefixes"
comment describes — AWS, Slack, Bearer, PEM, JWT, Stripe, npm, SendGrid, and DB-connection-strings
**with a non-empty username** are now real, tested catches. But the file's own comment overclaims
Discord coverage that does not exist in the regex, several major vendors (Azure, GCP/Firebase,
GitLab, Shopify, Square, Twilio Account SID) remain completely absent from both locks, and the
DB-connection-string pattern has a live gap on the single most common redis URL shape (empty
username). The docstring's line "`_scrub` refuses anything credential-shaped" (:32-33) remains an
overclaim for any bare token that doesn't carry a recognized vendor prefix or sit next to a
credential-named field — LOCK THREE (`scan_for_secrets`, the last-mile file scan before push)
inherits the identical gaps because it reuses the same two regexes.

---

## 3. `src/onomast.py`

### 3.1 `CARRIED_NAMES` misses the DC/Marvel "Earth-N" designators that are exactly its target case — MEDIUM — REPRODUCED

`onomast.py:93-99` is a fixed 38-string allowlist (`"earth"`, `"the earth"`, `"terra"`, ...). Ran
it against `data/RESOLVED_ENTITIES.json` (read-only): `is_carried()` returns `False` for `"New
Earth"`, `"Prime Earth"`, `"Earth-Two"`, `"Earth-Three"`, and `"Earth-616"` — all real DC/Marvel
world-designators, and a `"New Earth"` world entity (`key="newearth"`) genuinely exists in the
live data. These are the textbook case the module's own docstring opens with — *"thirty peoples,
with no contact between them, call their world by the same word... [that] is DESCENT"* — DC's
in-universe convention of "Earth-Two", "New Earth", "Prime Earth" etc. across reboots is exactly a
carried-name pattern the doctrine is written to catch, but the exact-string allowlist doesn't
recognize any variant beyond the bare word. Current live impact is limited (only one `"New
Earth"` record exists today, so `len(items) < 2` and it's skipped either way), but the gap is
structural and will silently fail to disambiguate the moment a second same-named world enters the
corpus, in exactly the source category (superhero multiverse fiction) this project explicitly
catalogs. Distinct from this: 8 `"Multiverse"`-named entities across different continuity groups
also go unrenamed, but that appears to be in-scope-as-designed — `"Multiverse"` is a structural
term, not a carried toponym, and the docstring explicitly excludes non-toponym homonyms (Cerberus,
Leviathan) by the same reasoning.

**Fix**: normalize `Earth-\d+`, `Earth-[A-Za-z]+`, `(New|Prime) Earth` style DC/Marvel
designators into the carried-names test (e.g. a regex alongside the literal set), or fold them
under the bare `"earth"` bucket before grouping by `v["key"]`.

### 3.2 Print-summary loop assumes non-empty `attestations`; would crash *before* the file is written — LOW — HYPOTHESIS (not currently triggered; live data has zero empty-attestation entries)

`onomast.py:392-394`, inside `main()`, runs **before** `silence.write_json(OUT, named, ...)`
(:399). `src = v["attestations"][0]` has no guard. Ran `name_worlds()` against the live
`RESOLVED_ENTITIES.json` directly (not through `main()`, so no file was written) and confirmed 0
of 223 named entries currently have an empty `attestations` list, so this is dormant. If a future
upstream record ever has an empty list, the entire computed `named` result — otherwise complete
and correct — is lost because the crash happens before the write. Moving the `write_json` call
ahead of the print summary, or guarding the index, would make the persistence path independent of
the display path.

### 3.3 Clean notes

`is_carried()`'s parenthetical-stripping, `coin_well_formed()`'s bounded-then-escalating salt
walk (both the `taken`-set and `well_formed()` checks are enforced on every fallback tier, unlike
the pre-2026-08-24 version its own comment describes), `register_for()`'s tie-break, and the
`[:4]`/`[:9]` truncations in `main()`'s console summary (display-only — the full `named` dict is
what's passed to `silence.write_json`, so this is not a Hard-Rule-0 violation) were all read and
found correct.

---

## 4. `src/backfill.py`

### 4.1 `main()`'s `--all` loop silently discards the `"error"` key from `backfill_source()` — MEDIUM — REPRODUCED (by code inspection)

`backfill_source()` returns `{"source": source, "error": "no wiki host"}` when a source has no
mapped wiki host (:174-175). In the single-source path (:293-295) the raw dict — including
`"error"` — is printed via `json.dumps`, so the failure is visible. In the `--all` path
(:276-286), only `res.get("roster", 0)`, `res.get("absent", 0)`, `res.get("added", 0)` are read —
all default to `0` — and the printed line reads `roster 0  absent 0  added 0`, which is visually
identical to "this source has zero characters missing, nothing to do" rather than "this source
could not be checked at all." A source silently missing its host mapping in `hosts.json` would
report as clean in every automated `--all` run.

**Fix**: `if res.get("error"): print("  %3d/%d  %-46sERROR %s" % (i, len(thin), x["source"][:44], res["error"])); continue` before the roster/absent/added print line.

### 4.2 Clean notes

This module has clearly already been through several audit passes (its own comments cite run #25
and 2026-08-24 fixes for exactly the classes of bug this lens looks for): `roster()` raises
`RosterIncomplete` rather than returning a silently-truncated partial roster on a transport
failure; the subcategory walk is unconditional, not gated behind a size threshold (the fixed `<
40` cap bug); no `[:limit]` truncation applies unless `--cap` is explicitly passed, and the
default is `None` ("omit for everything, which is the intended use"); `backfill_source()` uses
`P.write_record_catalogue()` (the correct two-writer-contract call for this direction of the
race, per its own detailed comment at :215-227) rather than a raw write; `absent` is reported
pre-cap on both the dry and live paths. No caps, no discarded return codes, no tautologies, and no
committed secrets found elsewhere in the file.

---

## 5. `src/anchors.py`

### 5.1 The floor→ceiling invariant genuinely fails today — HIGH-visibility but CORRECTLY SURFACED — REPRODUCED

Ran `python src/anchors.py` in isolation (read-only: it only imports `physics`/`assay`/`custodes`/
`rigor` and prints; writes nothing). **Confirmed: exits 1.**
```
monotone floor -> ceiling : False
     The Skate Guy                  0.22
     A Sword                        0.10
     Yggdrasil                      6.18
     Goku                           5.42
     The Seat of the Creator       10.99
```
This matches the module's own comment (:236-248), which already documents that `run()`'s `ok`
value used to be computed, printed, and discarded (exiting 0 regardless) until a fix at "run #26"
made the `if __name__` block `sys.exit(0 if _ok else 1)`. **That fix is real and present in the
current file** — this is no longer a check-that-cannot-fail; it now correctly fails loudly. What
remains is the underlying assay disagreement itself, which the module's own comment correctly
declines to paper over and routes to the owner instead.

**True cause, examined**: the `order` list at :215 is
`["The Skate Guy", "A Sword", "Yggdrasil", "Goku", "The Seat of the Creator"]`. Skate Guy and A
Sword are both anchored `M0`; Goku is anchored `M5`; Yggdrasil is anchored `M6` (higher than
Goku's own M5, per `ANCHORS["Yggdrasil"]["anchor"] = "M6"` at :153). The `order` list places
Yggdrasil **before** Goku, i.e. it asserts Yggdrasil should score *lower* than Goku — which
contradicts Yggdrasil's own declared anchor rung being one full magnitude above Goku's. The
measured decimals (Yggdrasil 6.18 > Goku 5.42) are actually **consistent with the M6 > M5
anchoring**; it is the hand-authored `order` list that has Yggdrasil and Goku transposed relative
to their own declared magnitudes. Separately, `A Sword` (0.10) scoring below `The Skate Guy`
(0.22) despite sharing the same `M0` anchor is a second, independent contributor — the sword's
scores are mostly `A.NONE` (floor) across seven of eleven axes versus the Skate Guy's small-but-
present nonzero values across the same axes, which plausibly is intended behavior (an inert
object legitimately scoring near the very bottom of its own band) rather than a defect.
**This module's own scoring logic (`assay.py`/`custodes.py`) is out of this batch's scope**, so I
cannot rule on whether 6.18/5.42/0.22/0.10 are themselves correct assay outputs — but the `order`
list's Yggdrasil/Goku ordering does not match the anchors' own declared magnitude, which is worth
flagging to whoever rules on this per NEXT_STEPS: swapping `"Yggdrasil"` and `"Goku"` in `order`
would make that half of the invariant check consistent with the anchors as declared, independent
of whatever the owner decides about the Sword/Skate-Guy question.

---

## 6. `src/liveness.py` — THE IRONY CASE: can the check-that-cannot-fail detector fail to fail?

### 6.1 `main()` always `return 0`, regardless of how many findings `scan()` reports — HIGH — REPRODUCED

`liveness.py:166-184`:
```python
def main():
    ...
    r = scan()
    total = sum(len(v) for v in r.values())
    if not a.quiet:
        ...
    print("\nliveness: %d finding(s) ..." % (total, ...))
    return 0
```
There is no branch anywhere in `main()` that inspects `total` (or any of `r["dead"]`,
`r["tautology"]`, `r["phantom"]`) to decide the exit code — it is `return 0` unconditionally. Ran
`python src/liveness.py --quiet` against this repo's live `src/`: **38 findings, exit code 0.**
Any automated caller that "judges by exit code" — which is exactly the failure mode `anchors.py`'s
own fix comment describes `allsweep` doing (":238-243", *"`allsweep` lists this module under 'the
instrument' and judges it by exit code"*) — would see `liveness.py` as clean no matter how many
dead functions, tautologies, or phantom guards it finds. This is the precise shape the module was
built to detect, reproduced in the module itself: a check whose result is computed, printed, and
discarded.

**Fix**: `return 0 if total == 0 else 1` (or gate on `tautology`/`phantom` only, if `dead` is
judged too noisy for CI — but *something* nonzero must reach the exit code; today nothing does).

### 6.2 `_parse()` swallows a syntax error into `None`, and `scan()` treats that identically to "nothing to report" — HIGH — REPRODUCED

`liveness.py:72-77`:
```python
def _parse(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return ast.parse(fh.read(), filename=path)
    except Exception:
        return None
```
and `scan()` (:83-86): `if t is None: continue` — the module is dropped from `trees` entirely and
never mentioned again in any of `dead`/`tautology`/`phantom`. Reproduced directly: wrote a
syntactically-broken file to a scratch temp directory and called `liveness._parse()` on it — it
returns `None` with no diagnostic recorded anywhere. A source file with a syntax error currently
in `src/` would be **completely invisible** to this tool: not flagged as broken, not counted as a
finding, and (perversely) contributing *zero* dead-function findings where a working file of the
same size would contribute several — a corrupted module reads as a *cleaner* pass than a healthy
one. This is the exact "ABSENT, not red, not green" failure class the module's own docstring
(:14-15) names as already caught once in `standards.py`'s vanished HIGH guard — reproduced here in
the tool built to catch it. Confirmed via `py_compile`/`ast.parse` that no file in the current
`src/` actually has a syntax error today, so this is dormant, not live — but it is a real blind
spot, not a hypothetical one.

**Fix**: track parse failures separately (`unparseable: [...]`) and surface them in `main()`'s
output and total, rather than folding them into silent exclusion.

### 6.3 The `used`-set / dead-function heuristic is documented as erring toward false negatives — by design, not a bug

`scan()`'s comment at :89-91 states plainly that any string constant matching a function name
anywhere in `src/` counts that function as "used," which the module's own docstring frames as a
deliberate under-count to keep false positives low. Consistent with what it says about itself;
not flagging as a defect, only noting for the record since it bears on how much weight `dead`
should be given (see 6.1's suggested fix gating only on `tautology`/`phantom`).

### 6.4 No ratchet/baseline mechanism in this file

The CLAUDE.md reference to a "ratcheted ceiling" belongs to `drill.py` (outside this batch), not
`liveness.py` itself — `liveness.py` has no baseline file, no history, and no ceiling logic of its
own to audit. Noting this so the absence isn't mistaken for an unexamined gap: it was looked for
and isn't here.

---

## 7. `src/scale_theories.py`

### 7.1 The entire module is dead code — zero callers anywhere in `src/`, and no entry point of its own — HIGH — REPRODUCED

`grep -rn` across all of `src/*.py` and `prompts/*.txt` for `bulk_export_beta`, `growth_strike`,
`penetration_pressure`, and `surviving_theory` turns up **no call sites anywhere** — the module
name `"scale_theories"` appears exactly once elsewhere, as a string in a list inside
`derivation.py:477`, which is not a call. `scale_theories.py` also has no `main()` and no
`if __name__ == "__main__":` block — unlike every other file in this batch, there is no way to
invoke any of its functions except by importing them from another module, and nothing does.
Cross-checked against the project's own `liveness.py` (run read-only, no repo files touched):
```
scale_theories.py:104 bulk_export_beta()
scale_theories.py:121 growth_strike()
scale_theories.py:134 penetration_pressure()
scale_theories.py:145 surviving_theory()
```
All four module-level functions are independently flagged DEAD by the project's own liveness
tool, agreeing with the manual grep. The physics content itself (T1-T4, the beta-bit pricing, the
growth-strike kinetic-energy formula) is internally consistent and well-reasoned — this is not a
correctness bug in the math, it is a fully-built instrument with no wire connecting it to
anything that runs. Given Hard Rule 1 ("don't invent facts... prose dressing on top of the JSON
records") and Hard Rule 3 (Assay scoring is "its own pass," not folded into prose generation),
it's plausible this was written as reference material for a human/owner decision or a future
prompt-injection pass and simply never got wired in — but as it stands today it is exactly
`liveness.py`'s DEAD category, in the file the project apparently intended as worked physics for
an actual character judgement (Ant-Man-style shrinkers) that no phase of the pipeline currently
consults.

**Fix**: either wire `surviving_theory()`/`bulk_export_beta()`/`growth_strike()` into whatever
phase scores Transgression/Ruin for scale-changing characters (`pipeline.py`, `assay.py` — outside
this batch), or, if this is intentionally reference-only documentation, say so in the module
docstring so a future liveness sweep doesn't need to re-derive that it's deliberate.

### 7.2 `surviving_theory()` selects by a free-text string prefix, not an explicit status field — LOW

`scale_theories.py:145-148`: `t["falsified_by"].startswith("Nothing attested")`. Works correctly
today (only `T3_BULK_EXPORT`'s prose happens to start that way) but is brittle: editing that one
theory's `falsified_by` prose for readability (e.g. "No attested evidence contradicts this")
without noticing it's also a de-facto boolean flag would silently make `surviving_theory()` return
empty — indistinguishable from "no theory currently survives," which is a very different claim.

**Fix**: add an explicit `"status": "surviving"` (or `"falsified"`) key to each theory dict and
filter on that instead of parsing prose.

### 7.3 `penetration_pressure()` guards its area denominator but not its time denominator — LOW

`scale_theories.py:134-142`: `force = (mass_kg * velocity_ms) / contact_time_s` has no floor,
while two lines later `force / max(contact_area_m2, 1e-30)` does. `contact_time_s` defaults to
`1e-3` so this never fires under default use, but an explicit `contact_time_s=0` call raises
`ZeroDivisionError` uncaught. Minor asymmetry in an otherwise carefully-guarded pair of formulas.

---

## Summary of read-only reproduction methods used

- `anchors.py` run directly (no repo state mutated; it only prints).
- `liveness.py` run directly against the live repo (`--quiet`), and separately its `_parse()`
  called against a scratch-dir file with a deliberate syntax error.
- `publish.py`'s `_SECRET` / `_SECRET_ASSIGN` / `scrub_text()` imported and exercised against
  ~40 synthetic (obviously fake, randomly generated) credential-shaped strings in a scratch
  script — no real credentials used or discovered anywhere in the repo.
- `publish.py`'s `write()` race reproduced structurally: two independent scratch-dir processes
  running the identical tmp-name/`os.replace` logic against a shared target, 400 iterations each,
  while a third process read it — 516/800 collisions (`PermissionError`/`WinError 32`).
- `onomast.py`'s `is_carried()` and `name_worlds()` called directly (not through `main()`, so
  `data/ONOMASTICON.json` was never written) against the live `data/RESOLVED_ENTITIES.json`.
- `overnight.py`'s `coverage_snapshot()` discard and `backfill.py`'s `--all` error-swallow were
  confirmed by code inspection only (both are simple, unconditional code-path facts; spinning up
  a live crashed `coverage.py` or a broken `hosts.json` entry was judged unnecessary to prove the
  discard exists).
- No file in this batch was edited. No repo state (`data/`, `docs/`, git) was written to. All
  scratch scripts and outputs live under the session scratchpad directory only.
