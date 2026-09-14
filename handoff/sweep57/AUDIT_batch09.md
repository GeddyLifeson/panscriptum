# AUDIT — sweep57, batch 09

Modules: `src/publish.py`, `src/overwatch.py`, `src/threads.py`, `src/ingest_doc.py`,
`src/prose_gate.py`, `src/pantheon.py`, `src/resync_roll.py`, `src/audit.py`, `src/lognames.py`.

All nine read in full, top to bottom. AUDIT ONLY — nothing edited, nothing run that writes to
the library. `prose_gate.py` was read and audited only; not touched.

Known-queue check (workorders.open_orders()) run first; matches noted as KNOWN(id). No open
order names any of these nine modules directly except `b186bc4dad8f`
(THREE_AXES_NOT_TWO_CATEGORY_TOPIC_SUBROOM, `src/threads.py category_path`), which is a doctrinal
note rather than a bug report — see the threads.py section below for how it was used.

---

## DEFECT 1 — `overwatch.py`: the `--loop` daemon never re-asks the halt after startup

**Where:** `src/overwatch.py:1027-1097` (`main()`), specifically the `while True:` loop at
:1083-1097.

**Quote (the whole reachable loop body in loop mode):**
```python
    if a.loop:
        codewatch.claim_singleton("overwatch")
        codewatch.stamp("overwatch")
    while True:
        print("=" * 88)
        print(f"OVERWATCH  {time.strftime('%H:%M:%S')}")
        print("=" * 88)
        round_once(limit=a.modules, local=not a.cloud, skip_model=a.structure_only)
        if not a.loop:
            return 0
        codewatch.exit_if_stale("overwatch")
        time.sleep(a.loop * 60)
```
`_ESC.assert_clear(os.path.basename(__file__))` is called exactly once, at line 1044, before
`ap.parse_args()` — i.e. before the loop even exists. Nothing inside the `while True:` calls
`escalation.assert_clear` (or any halt check) again. Confirmed by direct search: `grep -n
"escalation\|assert_clear" src/overwatch.py` returns only the one import/call pair at the top of
`main()`.

**What is wrong:** this is the exact fault class Hard Rule -1 was written about, in the exact
words this project already used to fix it in the sibling daemon: `publish.py:1872-1909` calls
this "THE HALT IS RE-ASKED EVERY CYCLE (order 5905045ff433)" and explains that `main()` asserting
the halt once at startup, with the loop running for hours, means "an OWNER halt raised by ANY
other job while the daemon was up did not stop it." `codewatch.exit_if_stale` does not cover this
either — `drill.py:_the_loop_reasks_the_halt`'s own docstring says so verbatim: "a halt is data
in a state file" and code-fingerprinting cannot see it. `overwatch.py`'s own docstring says this
job is meant to run as "the standing sweep, which runs for days" (`round_once`'s docstring, and
`rotation`'s design assumes multi-day operation). A halt raised on day 2 of a loop started on day
1 is invisible to this process until it is killed and restarted by hand.

**Why it matters:** an OWNER halt means "nothing starts until a person rules on it" (CLAUDE.md
Hard Rule -1). `overwatch.py --loop` keeps making local/cloud model calls (`review()`,
`verify_open()`), keeps writing `data/OVERWATCH.json` and `WATCH.md`, and keeps burning the
shared cloud pool budget (`CLOUD_BUDGET`) after a halt is raised, exactly the "IN EFFECT" failure
Hard Rule -1 names: "a safety that exists in a file is not a safety that is running." The fix
already exists in this same codebase one file over (`publish.py`'s `_the_loop_reasks_the_halt`-
shaped pattern, including breaking rather than retrying on `SystemHalted`) and was never applied
here. Checked: `grep -n "overwatch" src/drill.py | grep -i "loop\|halt\|assert_clear"` returns
nothing — no drill net proves this daemon stops on a halt either, so per Hard Rule -1's own
"PROVEN" property this guard has "never run."

**Verdict: DEFECT** (new — not in the sweep56 batches 10/13/14/15 handoffs, and no open work
order names it; checked against the full open queue and against `drill.py`).

---

## DEFECT 2 — `ingest_doc.py`: `mine()`'s multi-hour loop checks the halt once, not per chunk

**Where:** `src/ingest_doc.py:315-582` (`mine()`). Halt check at :319 (`_assert_not_halted("mine")`,
called once on entry); the `while ci < len(chunks):` loop runs from :434 to :557 and can run for
hours (`misses >= 60` at 300s/miss = ~5 hours per chunk, and every fresh entity list is written to
`data/records/*.json` — one of the two files this project's own doctrine calls "not
reconstructible from anything else on disk", per this same module's docstring at :49-53).

**Quote:**
```python
def mine(source):
    """The uncapped entity pass, chunk by chunk, merged as it goes."""
    # WRITES data/records/*.json through pipeline.write_record_catalogue -- the other of the two
    # unreconstructible files. (order acea8b00848e)
    _assert_not_halted("mine")
    ...
    while ci < len(chunks):
        ...
        if fresh:
            ...
            if not P.write_record_catalogue(rp, rec):
                ...
        ...
        time.sleep(300)   # (inside the `got is None` branch, up to 60 times)
```
No second call to `_assert_not_halted` or `escalation.assert_clear` anywhere inside the loop.

**What is wrong:** identical shape to DEFECT 1, on a module that itself documents having been
retrofitted for the halt ("Order acea8b00848e ... this is `hostcheck._assert_not_halted`
transcribed"). `hostcheck.py`'s own docstring (quoted inside `ingest_doc.py:181`) argues for
re-checking "immediately before an irreversible outward act" — `mine()`'s outward act (writing
`data/records/*.json`) happens on every iteration of a loop that can run for hours, and the halt
is asked only once, before the loop starts.

**Why it matters:** a halt raised mid-ingest (e.g. because the run itself, or a concurrent job,
tripped an OWNER-level fault) does not stop this pass from continuing to merge uncapped,
unreviewed model output into the corpus for up to five more hours. This is a lower-traffic path
than `overwatch.py` (it is operator-invoked, not a standing daemon), which is why it is filed
separately and at slightly lower severity, but the mechanism and the risk are the same class Hard
Rule -1 exists for.

**Verdict: DEFECT** (new; not found in the open queue, and `grep -c ingest_doc src/drill.py`
returns hits only for the module-existence/import nets, none of which drive the `--mine` loop
against a halt raised mid-run).

---

## QUESTION 3 — `publish.py`: the maintenance-shift guard is skipped for every one-shot invocation, not only the shift's own

**Where:** `src/publish.py:1910-1926` (inside `main()`'s loop body).

**Quote:**
```python
            # A MAINTENANCE SHIFT IS EDITING THIS TREE -- TAKE NO BYTES THIS CYCLE (order
            # bb4fa3f3c9f1). ...
            #
            # LOOP MODE ONLY, exactly as `claim_singleton` above is loop-mode only, and for the
            # same reason in the same words: a one-shot is not a daemon, it is a person -- or a
            # maintenance run's own final step -- doing one thing deliberately. The shift that
            # sets this guard must still be able to publish its own results at the end of the
            # shift, and a guard that blocked its holder would be a guard nobody could ship with.
            if a.loop:
                _busy, _why = maintenance_shift_live()
                if _busy:
                    print("skipping this cycle: " + _why)
                    codewatch.exit_if_stale("publish")
                    time.sleep(a.loop * 60)
                    continue
```
The guard function itself, `maintenance_shift_live()` (:1756-1815), is never called at all unless
`a.loop` is set.

**What is wrong / possibly deliberate:** the stated justification is narrow — "the shift that
sets this guard must still be able to publish its own results at the end of the shift" — but the
mechanism implemented is broad: it exempts *every* one-shot `python src/publish.py --push`
regardless of who runs it or why, not only the shift's own closing publish. The module's own
docstring for this guard (:1759-1791) records the incident it exists to prevent: sixteen
concurrently-editing agents, with a standing loop pushing an arbitrary mid-edit instant of their
work to the PUBLIC repo twice in eleven minutes. A one-shot `--push` run by a person, by a
different scheduled job, or by a second maintenance-adjacent process while `state/
MAINTENANCE_RUN.json` shows `done:false` and a live heartbeat would publish exactly that same
half-finished, sixteen-way-concurrent tree — the guard does not distinguish "the shift's own
final step" from "any other one-shot caller." `claim_singleton`'s loop-only exemption (the
precedent this is modeled on) is safe for a *different* reason: a second one-shot process is not
competing with the loop for anything the loop needs exclusively. A maintenance-shift edit-in-
progress is not analogous — the risk (publishing half-finished source) is identical whether the
caller loops or not.

**Why it matters:** if this is intentional (e.g. because in practice only the shift's own tooling
ever calls `--push` one-shot, and an operator is expected to check `MAINTENANCE_RUN.json` by
hand before running one), that is a real but undocumented operational assumption resting outside
the code. If it is not intentional, it is a live path by which the exact 2026-08-29 incident this
guard was built for recurs via a one-shot rather than a loop.

**Verdict: QUESTION** (the code and its own comment disagree on scope; not found in the open
queue under `bb4fa3f3c9f1` or any "maintenance" / "one-shot" text — checked directly).

---

## QUESTION 4 — `threads.py`: `verify()`'s round-trip check has no coverage of T3 edges, undocumented

**Where:** `src/threads.py:687-746` (`verify()`).

**Quote:**
```python
    for src, rec in sources.items():
        if not isinstance(rec, dict) or "T1" not in rec or "T2" not in rec:
            problems.append("%s: record is not a thread record (%r)" % (src, type(rec).__name__))
            continue
        t1 = rec.get("T1") or {}
        edges = [t1] + [e for lst in (rec.get("T2") or {}).values() for e in lst]
        for e in edges:
            ...
            if e.get("to") not in known:
                problems.append("%s: thread points at %r, which is not a live address"
                                % (src, e.get("to")))
```
`rec.get("T3")` is never read anywhere in `verify()`. `known` here is built as `{rec.get("code")
for rec in sources.values() if isinstance(rec, dict)}` — i.e. only source spine codes, never
Annex canon codes (`VIII.n`) or Law codes (`X.n`), the address spaces `edge()` widens `known`
with inside `build()` (:504-511) specifically so a T3/T4 can resolve.

**What is wrong / possibly deliberate:** `verify()`'s own docstring is unusually careful about
justifying every omission it makes — the emptiness check is explicitly explained as "not checked
here, and that is a deliberate omission rather than an oversight," with the reasoning spelled
out. There is no equivalent paragraph anywhere in the docstring explaining why T3 (which *is*
stored on the record, unlike T4) is left out of the round-trip address-resolution check. Given
`known`'s definition here is strictly narrower than `build()`'s (it omits `annex_codes()` and
`law_codes()`), including T3 in the loop as written would make every T3 edge fail as "not a live
address" on every run since Phase 4.3 landed (2026-09-09) — so the omission is *functionally
necessary* given how `known` is constructed here, but nothing in the file says so, and the stated
purpose of `verify()` ("these test the artifact a reader will get rather than the object the
builder still holds... catches a serialisation that drops or mangles a field before the file
lands") is silently narrower than claimed: a T3 edge whose `to` or `class` is corrupted by the
JSON round-trip would not be caught.

**Why it matters:** T3 is a live, ratified class (§7G, admitted 2026-09-09) carrying real edges
today (`counts()` reports `T3_edges`); a corruption in it is exactly the shape `verify()`'s own
stated purpose says it exists to catch, and it would sail through `main()`'s `if problems: ...
return 1` gate silently. Low probability (JSON round-trips rarely corrupt individual dict values)
but the gap is real and undocumented, which is what every other choice in this function is not.

**Verdict: QUESTION** (fixing it properly means widening `known` in `verify()` to match `build()`
— i.e. adding `annex_codes()`/`law_codes()` — which is a judgment call about whether `verify()`
should re-derive that address space or be handed it, not a one-line fix; not found in the open
queue).

---

## Clean modules (nothing found)

- **`src/prose_gate.py`** — read and audited in full as the owner-held safety gate this task
  calls out specifically. `gate_open()` and `step4_gate_open()` both use strict identity
  (`is not True`), not a loose truth test — the `bool("false")`-shaped fail-open the task
  description warns about is **not present**; both gates fail closed on an unreadable/wrong-shape
  config, and `floor_ok()` independently forbids a floor at or below zero (closing the exact
  `evidence_ok(floor=0)` hole its own comments describe as "the exact incident scenario"). The
  section/instrument/axis-honesty regexes were checked against the specific bypass strings their
  own comments record (`**Wisdom:** 28`, `**Wisdom**: 28`) and correctly still match. Nothing
  edited, per instructions.
- **`src/pantheon.py`** — clean. Write-verdict, merge-failure and partial-roster paths all reach
  both the console and the process exit code (traced through to `return 1`/`return 0 if write_ok
  else 1`); no silent fallback found.
- **`src/resync_roll.py`** — clean. `roll.mutate`'s compare-and-swap is used rather than a whole-
  file landing; the exclusion guard is re-checked against the fresh row inside `_apply`, not the
  snapshot; exit code correctly follows the write verdict.
- **`src/audit.py`** — clean. All three historical truncation bugs named in its own comments
  (`_field`, the 60-char scale-note slice, the description slice) are genuinely fixed as
  described; the denominator-per-class fix for the rate calculation is correct.
- **`src/lognames.py`** — clean; a small, static constant-and-comment module with no logic to
  fault.

## Not independently re-checked (out of this batch's nine, but touched by adjacent findings)

- `src/escalation.py` (`SystemHalted`, `assert_clear`) — read only enough to confirm the exact
  symbols DEFECT 1/2 depend on exist and behave as the modules using them assume (confirmed: both
  present, `assert_clear` re-reads on every call per its own module).
- `src/drill.py` — grepped, not read in full, to confirm no existing net proves DEFECT 1 or
  DEFECT 2 wrong (i.e. that they are genuinely unproven per Hard Rule -1's "PROVEN" property, not
  merely unmentioned).

## Coverage recorded

`sweep_plan.record('run57', [...9 modules...], batch=9)` run from the repo root; see the
sweep_plan ledger for the stamp.
