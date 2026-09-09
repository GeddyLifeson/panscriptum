# AUDIT — Panscriptum run #48, batch 14

Batch: 14
Modules assigned: src/read.py, src/dashboard.py, src/generate.py, src/secondopinion.py,
src/zfighters.py, src/cosmography.py, src/navtree.py, src/resonance.py

Lines read per module (full file, in successive chunks, cover to cover):
- src/read.py — 1670/1670
- src/dashboard.py — 1248/1248
- src/generate.py — 977/977
- src/secondopinion.py — 693/693
- src/zfighters.py — 536/536
- src/cosmography.py — 375/375
- src/navtree.py — 335/335
- src/resonance.py — 298/298

Method: every finding below was checked against the current source text quoted from this
session's own Read calls, not from memory of similar-sounding past findings. Where a citation's
target was outside my assigned eight files (one case, resonance.py -> anchors.py), I read the
target file directly to confirm before filing it.

---

## Findings

### FINDING 1 — MINOR — src/read.py:558 (stale line-number citation)

**What's wrong.** The comment says:

    # COUNTED HERE, AND ONLY ON AN ANSWER (order 6f95694b8143). ... so the "(%d
    # to GPU)" figure counts what the GPU actually received -- which is the whole reason
    # read.py:213-215 says the counter exists.

But read.py:213-215 is inside `_names()` (the entity-name/pronoun matcher) and reads:

    212: # A NAME WORD MUST START A WORD OF THE SENTENCE. This was raw substring containment
    213: # (`w.lower() in low`), directly under a comment explaining why the pronoun test below was
    214: # tokenised -- the boundary discipline was applied to the second check and not the first.
    215: # Substring matching attributed 'MetalGarurumon then defeats Azulongmon' to GARURUMON ...

That passage has nothing to do with the `_FELL_BACK` GPU-received counter. The text that actually
explains "the reason the counter exists" is at read.py:271-274:

    270: _FELL_BACK = [0]
    271: # `+= 1` on a shared slot is a read-modify-write, not an atomic step, and both increments below
    272: # run inside `_ask_ungated` under the whole worker pool. Lost updates understate the "N to GPU"
    273: # figure -- and that figure is the only thing that distinguishes a run quietly served entirely
    274: # from the slow path from a run that is merely slow, which is the reason the counter exists.

**How verified.** Read both cited spans directly (read.py lines 195-234 and 260-280) and
confirmed the phrase "the reason the counter exists" is verbatim at line 274, not present
anywhere near 213-215.

**Remedy.** Change the citation at line 558 from `read.py:213-215` to `read.py:271-274` (or
name the constant `_FELL_BACK` instead of a line number, which is the fix this same file already
applies elsewhere, e.g. the `(Order ce9735ec93ba: ...)` note at line 665).

---

### FINDING 2 — MINOR — src/read.py:663 (stale line-number citation, self-contradicting)

**What's wrong.** Inside `_local_carded`, the oversized-prompt branch says:

    659: # Order 5bf48fa9f70d: a None from any piece used to be swallowed by `(got or {})` ...
    662: # ordinary chunk path -- the `len(prompt) <= CHUNK + 2000` branch at the top of THIS function
    663: # (:554-564) -- treats a None as unanswered and benches the GPU; this path has to make the
    664: # same promise, not a weaker one just because it is rarer.

The branch being described (`if len(prompt) <= CHUNK + 2000:`) is actually at read.py:648-658
(function `_local_carded` starts at line 645), not :554-564. Line 554-564 is inside `_ask_ungated`,
a different function entirely (the "(%d to GPU)" comment discussed in Finding 1).

Notably, the very next lines (665-667) are a self-aware correction of an *earlier* stale citation
in this same comment block: "(Order ce9735ec93ba: that citation read ':521-524' ... The branch is
named as well as numbered now, so the proof survives the next line shift.)" — but the number that
replaced it (:554-564) has itself now drifted to the wrong place, which undercuts the "survives
the next line shift" claim: the *name* (`len(prompt) <= CHUNK + 2000`) still resolves correctly,
but the *number* next to it is wrong again.

**How verified.** Read lines 645-667 directly; the branch in question starts at line 648 and ends
at line 658, confirmed by the `if len(prompt) <= CHUNK + 2000:` / `return got` pair.

**Remedy.** Update `:554-564` to `:648-658`, or drop the number entirely and rely on the named
branch condition alone (which this same paragraph already argues is the more durable form).

---

### FINDING 3 — MINOR — src/read.py:232 (citation points at unrelated content)

**What's wrong.** In `_names()`, discussing the case where an entity has no word longer than
three letters:

    228: # NO WORD ABOVE THE FLOOR (order e61e1c8e9ac4). ...
    232: # read_entity's chunk-selection filter (read.py:731) already falls back to the whole name
    233: # for exactly this case; this is the same fallback, but phrase-bound rather than a raw
    234: # substring test, ...

read.py:731 is inside `_chunk_key()`'s docstring, discussing the `generic_dropped` counter and a
cache-key collision bug from 2026-08-24 ("So on a shared franchise index ... `read_entity` wrote
the record as complete."). It is not part of `read_entity`'s chunk-selection logic and contains no
"fall back to the whole name" behaviour. I searched the whole file for the phrase "whole name" and
for any chunk-selection fallback logic in `read_entity` (which starts at line 786) and found no
candidate location the citation could be pointing to instead — it does not appear to have simply
drifted from a nearby correct line; the described behaviour does not exist in `read_entity` at
all under that description.

**How verified.** Read read.py:700-744 (the actual content at and around :731) and read.py:786
onward (`read_entity`'s body) in full; grepped the file for "whole name" and "fallback" — no other
match describes a chunk-selection fallback to the whole name.

**Remedy.** Either the citation needs correcting to wherever this fallback logic actually lives
(if it exists under a different name), or, if the fallback was never implemented as described,
the claim itself needs re-examining — filed as a citation defect rather than a functional one
because I could not confirm which of the two is true from read.py alone.

---

### FINDING 4 — INFO — src/resonance.py:54 (citation into another module has drifted)

**What's wrong.** resonance.py's docstring says:

    52: fires when the curl fraction clears Saaty's bar, and the eta that veto reads comes from
    53: `hodge_decompose`. Since nothing calls `hodge_decompose`, nothing computes that eta, and
    54: `anchors.py:190`, the sole real caller of `convene()`, passes none.

anchors.py:190 is prose inside a comment block ("Two consequences follow from what an anchor IS,
not from any estimate:"), not the `convene()` call site. The actual call is at anchors.py:236:
`col = CU.convene(a["anchor"], a["scores"], attestation=a["attestation"], ...)`.

**How verified.** Read anchors.py:175-204 (around the cited line) and grepped anchors.py for
`convene(` — the only call is at line 236.

**Remedy.** Update the citation from `anchors.py:190` to `anchors.py:236`. Filed as INFO rather
than MINOR because anchors.py is outside this batch's assigned modules and the surrounding claim
(no production caller computes eta) is not in dispute — only the specific line number is wrong.

---

## Question (not a finding — flagging per instructions, not proposing removal)

None. The gates I examined in generate.py (the prose-gate check at main() lines 609-616, the
Charter P8 meta-language check at lines 830-861, the evidence-floor refusal at lines 672-693, and
every exception arm around them) all read as deliberate, already-hardened fail-closed guards with
extensive owner-ruling commentary justifying each one. I did not find anything that reads as an
unnecessary-looking gate warranting a question.

---

## What I read and found nothing wrong in

- **src/generate.py**: the entire generation loop, including `strip_think` (fails toward empty
  string, never invents prose), `_covered`/`_deed_traced`/`_deed_shortfall` (layer 3/3b defences),
  `ChapterRefused` (full offender lists preserved under dedicated keys even when the human-readable
  sentence is bounded with an explicit "+N more, all of them under 'X'" marker — this is a marked
  display truncation, not a Hard Rule 0 violation), `generate_job`'s per-block write-chunking and
  retry-once-then-fail-loudly discipline, the `main()` prose gate (Layer 2), evidence floor (Layer
  3) with `or 0.0` removed and floor_ok checked before use, the `--limit is not None` vs truthiness
  fix, the P8 meta-language gate's exception handling (confirmed: every exception arm, including
  ImportError, falls through to "refuse the chapter" — never to the write), `save_raw`/`save_json`/
  `compress_store.store` failure handling (all filed to failures.json and skipped, none silently
  swallowed), and the exit-code propagation at the bottom of `main()` and `__main__`. No check-that-
  cannot-fire or fail-open-silence pattern found.
- **src/dashboard.py**: every panel builder (`quotas`, `throughput`, `jobs`/`_read_row`/`_roll_row`,
  `library`, `watch`, `movement`, `metrics`, `safety`), all independently exception-guarded per the
  file's own "fault isolation" doctrine; the halt/prose-gate/step4-gate/assay-calibration/fetch/
  drill/escalation sub-panels of `safety()` each distinguish "absent" from "unreadable" from "clean"
  per the FileNotFoundError-vs-Exception split; `movement()`'s corrupt-history self-heal and its
  reset-on-negative-delta handling; the panel roster in `tick()` (line 1117-1118) matches all ten
  defined `panelX` functions exactly — no renderer has fallen out of its own roster; the escalation
  import guard in `main()` (fails closed, raises SystemExit on ImportError) and the read-only-
  instrument exemption from the pre-argparse halt check (justified at length and scoped narrowly to
  processes that write nothing outside output/ and state/). No unmarked caps found (the two
  historical `[:160]`/`[:120]` truncations referenced in comments are already fixed and are cited
  as history, not as live behaviour).
- **src/secondopinion.py**: the fail-open design for absent tools is explicit, intentional, and
  argued at length as the one deliberate departure from house fail-closed doctrine, with the
  reasoning given; the returncode-aware `_ruff`/`_vulture`/`_detect_secrets` runners (each
  distinguishes "tool ran cleanly", "tool ran and found things", and "tool could not run" — none
  can read an unrun tool as a clean pass); `report()`'s tree-fingerprint-before/after guard against
  scanning a moving target; the three-way AGREEMENT/DISAGREEMENT/UNMEASURED branching in the
  secrets comparison; `file_orders()`'s refusal to file when the tree was torn underneath the scan.
  No unmarked caps (`hits[:4]`/`ranked[:6]` both carry "+N more" markers).
- **src/zfighters.py**: the hand-built roster and its `compute()`/`main()` — atomic, gated write
  to Z_FIGHTERS.json with an explicit WRITE DENIED path; the Goku-sheet merge failure is reported
  loudly to the console, not just the silence ledger; `--full`'s worksheet citations are wrapped,
  not truncated (order noted in-file). No caps, no fabricated data — every axis score carries a
  cited sentence and a provenance tag.
- **src/cosmography.py**: `census()`/`validate()`'s two-tier physical-plausibility checks (ratio
  ceilings scaled inside the census, plus the separate absolute size-class ceiling that exists
  specifically because the ratio checks structurally cannot catch a categorically-wrong census);
  `kardashev_to_magnitude`'s explicit `reached = None` (no longer defaults to the bottom band); the
  documented, reversible FICTIONAL vs MEASURED constant split. No functional issues found.
- **src/navtree.py**: `build()`'s no-cap world/source enumeration, the deterministic tie-break in
  `register_for`/hyperverse-naming (fixed from hash-order nondeterminism), `audit()`'s complete
  problem listing (no cap), and `main()`'s exit-code correctness (`--write` refused when problems
  exist; the final `if not audit_landed or problems: return 1` covers both the denied-audit-write
  case and the has-problems-without---write case, both of which the file's own comments describe
  as previously-wrong return-0 paths that have since been corrected). No live defect found.
- **src/resonance.py**: `hodge_decompose`'s Gauss-Seidel convergence fix (with the documented
  Jacobi/bipartite failure it replaced), the `no_evidence` vs `eta=1.0` disambiguation for both the
  empty-nodes and all-zero-flow cases, the `converged: False -> eta: None` fail-closed return, the
  asserted-but-structurally-unreachable `_isolated` check (kept deliberately as a guard against a
  future construction-logic change, and is honest about currently never firing — this is the
  opposite of Finding-class-1's "check that cannot fail" defect, since it is not claimed to be
  currently protecting anything). `incomparability_rate`'s full (uncapped) `examples` list.

---

## Coverage note

`sweep_plan.record('run48', [...], batch=14)` was run from the project root per the task's
Deliverable 2 instructions; see the tool output in this session for confirmation.
