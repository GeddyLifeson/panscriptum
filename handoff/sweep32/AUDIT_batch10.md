# BATCH 10 AUDIT — run32 — sweep32

Modules read in full, every line:
- src/dashboard.py — 964 lines
- src/allsweep.py — 495 lines
- src/catalogue_web.py — 403 lines
- src/escalation.py — 289 lines
- src/anchors.py — 250 lines
- src/chord_field.py — 203 lines
- src/cachekey.py — 135 lines

Also read (context only, not audited line-by-line): src/silence.py (append_line/replace_retry/
write_json docstrings), src/drill.py (`_no_programmatic_clear`, `drill_park`), src/verify_math.py
(grepped for `clear()` assertion), src/resync_roll.py (SWEEP_ROLL.json writer), src/pipeline.py
(`main()`, `write_record_catalogue()`), src/assay.py (`LADDER` order).

Severity key: BLOCKING (safety/data-loss-grade, fix before anything else) / MAJOR / MINOR / NOTE.
VERIFIED = read and confirmed against the actual code. SUSPECTED = strong textual evidence but not
traced end-to-end against every caller.

---

## escalation.py — the chain of command (safety-critical)

**escalation.py:97-106 `_append()` — BLOCKING, VERIFIED.**
`_append_log()` (called on *every* `escalate()` at every rung, 0-5) writes with buffered
`open(path, "a")` + `f.write(json.dumps(rec) + "\n")`. `silence.py`'s own `append_line()` docstring
documents this exact shape as the "torn-line defect class": Python may split one line into several
underlying writes, and two writers interleaving mid-line produce a row that parses as neither
(measured elsewhere in this project: 5 corrupt lines from the same pattern before it was fixed for
`model_metrics.jsonl`). `state/escalation.log` and `state/escalations/<src>.log` are the audit
trail for the entire safety chain and are exactly as exposed to this as the metrics ledger was.
Should call `silence.append_line` instead. Confirms the reported item.

**escalation.py:154-183 `_raise_halt()` — BLOCKING, VERIFIED.**
No lock around the read-modify-write of `HALT.json`, and the tmp filename (`HALT_FILE + ".tmp"`)
is not PID/thread-disambiguated (unlike `silence.write_json`, built for precisely this). Two
concurrent *first-time* `escalate(OWNER, ...)` calls (no halt yet standing) both see
`cur = _read_halt_raw() -> None`, both build a **fresh** payload (`also: []`) instead of one
appending to the other's `also` list, both write the same tmp path, and whichever `replace_retry`
lands last **completely overwrites** the other's fault — the opposite of the documented behaviour
("a second fault while halted is appended as corroboration rather than replacing the first"). The
FIRST/triggering fault can be silently lost. Confirms the reported item.

**escalation.py:154-183 `_raise_halt()` — BLOCKING, VERIFIED (new, not in the original report).**
If the file write itself fails (`os.makedirs`, `open(tmp,"w")`, or `replace_retry` all raise), the
`except Exception` block only writes to stderr and calls `silence.note()` — it never retries
through an alternate durable channel and never re-raises. Since `status()`/`assert_clear()` derive
"halted" *purely* from what is readable on disk, a failed write means an OWNER-level ("HALT
EVERYTHING") fault is silently downgraded to "nothing happened" for every other process in the
library. This is the read-side fail-closed guarantee (`_read_halt_raw`, verified correct — see
below) without the matching write-side guarantee, and it is the single most severe finding in this
batch: it directly violates the project's own stated invariant ("Silence must never authorise
anything").

**escalation.py:33-34 docstring / CLAUDE.md Hard Rule -1 — MAJOR, VERIFIED.**
Both claim "`verify_math` asserts that no module in `src/` calls [`clear()`]." Grepped
`verify_math.py` exhaustively for any such check — none exists. The real check
(`"no module in src/ clears the halt programmatically"`) lives in **`drill.py:509`**, implemented
by `drill.py:626-635 (_no_programmatic_clear)`. Comment/doc contradicts code at the top of the
safety chain; anyone trusting the documented claim and gating only on `verify_math` would believe
an invariant is checked that isn't, there.

**drill.py:626-635 `_no_programmatic_clear()` — MAJOR, VERIFIED (found while chasing the item above).**
The actual enforcement for "only a person may lift a halt" is a raw substring scan:
`"escalation.clear(" in t or "ESC.clear(" in t` over each module's source text. Trivially defeated
by any indirection: `import escalation as X` then `X.clear(...)` (any alias other than the literal
string `ESC`), `fn = escalation.clear` followed by a later `fn(...)`, or `getattr(escalation,
"clear")(...)`. Currently no module in `src/` does this (verified by grep — clean today), so this
is a latent structural weakness, not a live breach: the project's sole enforcement of the single
most important safety asymmetry in the codebase is a text-presence check, exactly the "checks that
cannot fail" shape the sweep is hunting for.

**escalation.py:55-56 `class Refused` — MAJOR, VERIFIED.**
Defined to represent an OPERATOR/SUPERVISOR-level refusal but never raised or referenced anywhere
else in `src/` (grepped the whole tree — zero hits beyond the definition). `escalate()`'s own
docstring says "raising is the CALLER's decision for rungs 1-4," but no caller anywhere uses the
type this module supplies for that purpose. Either every OPERATOR/SUPERVISOR refusal in the
codebase is implemented ad hoc with unrelated exceptions (inconsistent, undiscoverable from this
module), or rungs 1-2 have no real enforcement at all — dead code standing in for a safety
behaviour that may not exist.

**Fail-closed check — CONFIRMED GOOD.** `_read_halt_raw()` (186-198) correctly treats an
unreadable/corrupt `HALT.json` as `halted: True` with `code: HALT_FILE_UNREADABLE`. Verified
correct against the code as written.

**Over-escalation check — CONFIRMED GOOD (within this file).** `_raise_halt()` only fires when
`level >= OWNER` (line 146); nothing in `escalation.py` itself auto-escalates a
SUPERVISOR/SAFETY/MANAGER event into the plant-wide halt. (Whether some *caller* elsewhere
misuses `escalate(SUPERVISOR, ...)` to over-broadly refuse is outside this file and outside this
batch's assigned modules.)

---

## dashboard.py — the instruments (threading HTTP server)

**dashboard.py:378-381 `movement()` — BLOCKING, VERIFIED.**
```
tmp = HISTORY + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(hist, f)
silence.replace_retry(tmp, HISTORY)
```
`dashboard.py` runs `socketserver.ThreadingTCPServer` with `daemon_threads = True`; every
`/api/state` request runs `state()` → `movement()` in its own thread. This write is the classic
two-writer race `silence.write_json` exists to prevent: two concurrent requests both read `hist`
before either writes, both append their own row, both write to the *same* tmp filename (no
PID/thread suffix), and the later `replace_retry` wins outright — the earlier request's history
sample is silently dropped, not merged. **Correction to the reported framing:** this is not a bare
`os.replace` (it does call `silence.replace_retry`), so the read-side/atomicity half of the
two-writer contract is honored; the actual defect is the un-disambiguated shared tmp name under
concurrent same-process threads. Recommend `silence.write_json(HISTORY, hist)` instead.

**dashboard.py:316 — MAJOR, VERIFIED (confirms reported item).**
`out["swallowed"] = sorted(f.items(), key=lambda kv: -kv[1])[:6]` caps the swallowed-failures
breakdown to the top 6 by count. `swallowed_total` (line 317) does preserve the full sum, but the
*identities* of every failure site outside the top 6 are invisible on the dashboard. This is the
same shape as the finding already fixed two lines above it (line 311: "ALL open findings — a
monitoring cap ruled a truncation, 2026-08-24") and was apparently not applied consistently to the
sibling panel right below it.

**dashboard.py:377 — MAJOR, VERIFIED (confirms reported item, different mechanism than framed).**
`hist = [h for h in hist if h.get("at", 0) > cutoff][-2000:]`. The `24 * 3600`-second cutoff
computed one line above implies a 24-hour retention window, but at the 5-second poll interval that
window holds ~17,280 samples — the `[-2000:]` slice is stricter and actually governs, silently
discarding roughly 85% of the samples the adjacent code's own math implies should be kept. Comment
intent and actual retention window disagree (lens 6).

**dashboard.py:150-168 `throughput()` — MAJOR, VERIFIED.**
`c = sqlite3.connect(path)` is opened on every `/api/state` poll (every 5s per client, from a
threading server) and is never closed — no `c.close()`, no `with` block. Resource leak in a
per-request hot path.

**dashboard.py:525-527, 541-542 `safety()` — MINOR, VERIFIED.**
The `drill_last.json` and `escalation.log` reads use a bare `except Exception` explicitly exempted
from `silence.note()` on the theory that "file doesn't exist yet is the good state." But the same
except also swallows a genuinely corrupt/unreadable file with zero instrumentation — that failure
mode is invisible everywhere, including the swallowed-failures ledger that the rest of the file is
careful to feed.

**dashboard.py:645 `cls()` (JS) — NOTE.** `f<=0.001?'bad':f<0.15?'bad':...` — first branch is
dead/redundant since the second already covers it. Cosmetic only, same result either way.

---

## anchors.py — the invariant-violation curatorial question

Per the task: read the code and give a reasoned ruling on whether the DECLARED ORDER or the
SCORING is the more likely fault for each violated pair. Not fixed, per instructions.

**Goku (5.42) < Yggdrasil (6.18): the DECLARED ORDER is the more likely fault.**
`vals[name] = A.LADDER.index(a["anchor"]) + (res.get("decimal") or 0.0)` (line 218). Goku is
anchored `"M5"` (line 93) and Yggdrasil `"M6"` (line 153) — both assigned explicitly, earlier in
the *same file*, by whoever wrote `anchors.py`. `LADDER.index("M6")` is 1 greater than
`LADDER.index("M5")` (verified: `LADDER = ["M0",...,"M10"]` in assay.py), and the printed decimals
("5.42", "6.18") show the per-band fraction stays inside `[0,1)`. That means Yggdrasil's total is
**mathematically guaranteed** to exceed Goku's for any normal axis scoring within Goku's own M5
band — no adjustment to Goku's numbers could close a full band gap without also pushing his
decimal past 1.0 (out of band). The `order` list (line 215) demanding Goku > Yggdrasil directly
contradicts a tier decision the file already made two anchors earlier. This reads as an
un-reconciled "Goku is narratively the strongest fighter" intuition sitting next to a deliberate
"Yggdrasil's cosmic scope (spans nine worlds, survives Ragnarok) earns a higher band" decision —
the order list is the piece that was never updated to match.

**A Sword (0.10) < The Skate Guy (0.22): the SCORING is the more likely fault.**
Both anchors are `"M0"` (lines 73, 131) — tied at the same band, so this comparison is decided
*entirely* by decimal/axis scoring, unlike the Goku/Yggdrasil pair. A Sword has 7 of its 11 axes
scored `A.NONE` (celerity, continuity, transgression, vector, acumen, discernment, suasion all
zeroed, lines 137-146) against only 3 real numeric axes (ruin, reach, sustain); The Skate Guy has
8 numeric axes and only 2 `NONE`s (transgression, vector). The aggressive zeroing — rather than
`A.INAPPLICABLE` (excluded from the average, the treatment already given to `volition` on both
anchors on the grounds "not a contestant") — is a curatorial classification choice, not a code
defect, and it is what pulls the Sword below the Skate Guy. If an inert object's non-physical axes
(no initiative, no cognition — arguably as legitimately "not applicable" as no contest history)
were struck `INAPPLICABLE` rather than `NONE`, the smaller denominator would raise its decimal.

---

## catalogue_web.py — web cataloguer

**catalogue_web.py — main() never checks the plant-wide halt — BLOCKING, VERIFIED.**
`catalogue_web.py` performs real corpus-mutating writes (`pipeline.write_record_catalogue(...)`
into `data/records/`, plus `save_roll()` into `data/SWEEP_ROLL.json`) but `main()` never imports
`escalation` and never calls `assert_clear()`. Traced the write path: `write_record_catalogue()`
(pipeline.py:412) does **not** itself check the halt; the `assert_clear()` call in `pipeline.py`
lives only inside `pipeline.py`'s *own* `main()` (pipeline.py:1945-1962), which `catalogue_web.py`
never invokes — it imports `pipeline` as a library and calls the function directly. This is
exactly the historical incident CLAUDE.md's Hard Rule -1 and dashboard.py's own `main()` comment
describe ("nine sites, all of them quiet about it"): if the library is halted at OWNER level,
`catalogue_web.py` runs straight through and keeps writing new catalogue records, oblivious.

**catalogue_web.py:75-84 `save_roll()` — BLOCKING, VERIFIED.**
Still the hand-rolled `tmp = ROLL + ".tmp"` + `silence.replace_retry(tmp, ROLL)` pattern rather
than `silence.write_json`. `silence.py`'s own `write_json()` docstring names
`catalogue_web.save_roll()` by name as one of (at the time) four independent writers of
`data/SWEEP_ROLL.json`, and states the fix exists because the old pattern's shared,
non-PID/thread-disambiguated tmp name lets two writers collide on the temp file itself, with the
loser's replace silently clobbering the winner's target with a partial file. Checked the sibling
writer: `resync_roll.py:68` **has** since been migrated to `silence.write_json(ROLL, roll, ...)`;
`catalogue_web.py` has not. Residual risk: two concurrent `catalogue_web.py` invocations (or any
other still-hand-rolled writer of this exact path) still collide on the fixed tmp name. `save_roll`
is also called from 3 worker threads inside this same process (line 396,
`ThreadPoolExecutor(max_workers=3)`) — serialized here by `_wlock`, which protects only
within-process, not against a second process.

**catalogue_web.py:99-103 `catalogue()` — MAJOR, VERIFIED.**
```
try:
    titles = ws.clean_titles(ws.category_members(sub, c, limit=None))
except Exception:
    silence.note("catalogue_web.py:79")
    continue
```
Any transient fetch failure on a single category permanently drops that category's entries for
the run, no retry. Because `main()`'s default work selection is `entry_count == 0` (line 306), a
source that still nets *some* entries from its other categories ends up with `entry_count > 0` and
is never automatically revisited — the exact "permanent, silent loss" shape the file's own comment
at lines 380-384 explicitly fixed for the final write-denial case, left open here for per-category
fetch failures. On a large wiki (DC: 360 categories per the file's own commentary) this is a live
exposure surface.

**catalogue_web.py:184-244 `_short` staleness — MAJOR, VERIFIED.**
`_short` is set only inside the discovery loop (`for canon in ws.CATEGORY_KEYWORDS: ... _short =
canon.split(" (")[0][:16]`, line 199) and is never reassigned inside the later fetching loop
(`for canon, cats, titles in planned:`, line 232 onward). The progress heartbeat at line 244
(`_beat(_short + " fetching", d, t)`) therefore prints the **wrong, stale category label** for
every category during the fetching phase except at most the one whose name happened to match
`_short`'s final value from discovery. On a multi-hour source (DC/Marvel scale, per this file's
own commentary) this misleads anyone reading the log about which category is actually in flight.
Data correctness and the stall-prevention timer (`_beat_at[0]`) are unaffected — only the printed
label is wrong (lens 1: wrong variable / stale closure capture).

**catalogue_web.py:66-67 `slug()` — MINOR, SUSPECTED.**
`re.sub(...).strip("-")[:60]` truncates a source name to 60 chars for
`data/records/<slug>.json`, with no ownership-verification analogous to `cachekey.py`'s `owns()`
fix for the structurally identical M23 collision bug the project already found and fixed
elsewhere. Not confirmed as a live collision against the actual ~215-source roll; flagged because
it is the same defect class recurring, unguarded, in a different location.

---

## allsweep.py — the sweep of sweeps

**allsweep.py:74-80 `NEVER_RUN` — MAJOR, VERIFIED (dead safety list).**
Defined with an extensive docstring: "Modules whose no-argument run does real, expensive or
mutating work. They are still IMPORT checked; they are simply never invoked." Grepped the whole
file: the name `NEVER_RUN` appears exactly once — its own definition. `check_import()` invokes
**every** module (including `read`, `pipeline`, `generate`, `backfill`, `cleanup`,
`compress_store`, all named in the set) with `--help`, unconditionally, with no check against this
set anywhere. The documented protection does nothing; whether it matters in practice depends on
every listed module doing no real work before argparse intercepts `--help` — not verified for all
68 modules in this pass, since only the listed 7 were in scope, but the list itself is confirmed
non-functional as written (lens 6 + lens 7: a guard on a set nothing reads).

**allsweep.py:203,207,211,250,263,314 reconcile() example caps — MINOR, VERIFIED.**
`", ".join(orphan_hosts[:6])` and siblings: the persisted count (`len(...)`) is always the true,
uncapped total, but the specific *identities* beyond the first 6 are not persisted anywhere in
`ALLSWEEP.json` — only the aggregate count survives for later reading. Borderline "pure display
formatting" per the project's own precedent (dashboard.py's fix at line 311 went the other way,
showing every finding); flagging for the owner to rule on whether reconcile()'s report needs the
same treatment.

**allsweep.py:388 — NOTE, VERIFIED (correct, but fragile).**
`if "undefined name" in ln or "local variable" in ln and "referenced before" in ln:` — no
parentheses. `and` binds tighter than `or`, so this evaluates as `A or (B and C)`, which happens
to be the intended semantics for pyflakes' actual message shapes ("undefined name '...'" vs.
"local variable '...' ... referenced before assignment"). Confirmed correct as written, but the
missing parens make it look like a bug and invite a "fix" that would silently change behaviour.

---

## cachekey.py — the M23 fix (clean overall)

**cachekey.py:97-116 `load()` — MINOR, VERIFIED.** The `except Exception` on a corrupt candidate
file only reports via the optional `on_corrupt(fp)` callback; with the default `on_corrupt=None`,
a corrupt cache file is silently skipped with **no** `silence.note()` fallback — opt-in
instrumentation rather than mandatory, unlike almost everywhere else in this codebase.

**cachekey.py:119-135 `write_path()` — MINOR, VERIFIED.** Same except-swallow on a corrupt natural
path, but with no instrumentation hook at all, not even opt-in — this specific failure mode is
invisible everywhere.

**cachekey.py NAME_CAP=80 / HOST_CAP=40 — NOTE, not a defect.** These are the deliberately
preserved, byte-identical legacy filename caps the module's docstring explains at length; the
correctness gap they'd otherwise cause is closed by `owns()` (exact-string check against the
stored `entity` field) plus the disambiguated-suffix path. Explicitly not a Hard Rule 0 violation
— included here only to confirm it was checked and is not the same class of bug as the caps found
elsewhere in this batch.

---

## chord_field.py — clean

Pure reference data (physics adjudication table) and small stateless math helpers
(`total_beta`, `landauer_floor`, `recoil_momentum`, `recoil_velocity`,
`critical_power_self_focus`). No I/O, no shared mutable state, no caps, no swallowed exceptions.
No findings.

---

## Summary count

- BLOCKING: 7 (escalation.py x3, dashboard.py x1, catalogue_web.py x3)
- MAJOR: 9 (escalation.py x3, dashboard.py x2, catalogue_web.py x2, allsweep.py x1, and the
  anchors.py curatorial reasoning is reported separately as requested, not scored as a bug)
- MINOR: 6 (dashboard.py x1, catalogue_web.py x1, allsweep.py x1, cachekey.py x2, plus the
  reconcile() example-cap item)
- NOTE: 3 (dashboard.py x1, allsweep.py x1, cachekey.py x1)
