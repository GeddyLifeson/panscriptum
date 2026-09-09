# Sweep #48 — Batch 02 Audit

**Batch:** 02
**Modules assigned:** `src/verify_math.py`
**Lines read:** all 12,529 lines, in full, sequentially (offsets 1–500, 501–1000, 1001–1600,
1601–2200, 2201–2800, 2801–3500, 3501–4200, 4201–4900, 4901–5600, 5601–6400, 6401–7200,
7201–8000, 8001–8700, 8701–9600, 9601–10500, 10501–11400, 11401–11800, 11801–12200,
12201–12529). No sampling — every line was read.
**Constraints observed:** read-only on `src/`; no execution of `verify_math.py`, `mutate.py`, or
`drill.py`; used `C:/Users/imarl/miniconda3/python.exe` with `PYTHONIOENCODING=utf-8` for the one
required command (see Deliverable 2 below); wrote nothing under `src/`.

## Context

`verify_math.py` is this project's own extraordinarily self-auditing test battery — a
12,500-line file that has, over roughly 48 runs, hunted and fixed dozens of instances of exactly
the defect classes this sweep is looking for (tautological checks, fail-open swallows, Hard
Rule 0 caps, stale citations), and it documents each repair at length with an "order" ID, a date,
and a before/after argument. The overwhelming majority of code that at first glance looks
suspicious (bare `except:`, a `check(label, True, True)`-shaped literal, a `[:N]` slice) turns out
on inspection to be either (a) a documented `silence-exempt` swallow with a named site, (b) a
canary/control fixture that deliberately reproduces the shape of a past bug so the detector that
catches it can be shown to still work, or (c) already fixed and now guarded by a companion
positive/negative control. I verified this pattern held for every specific site I spot-checked
rather than assuming it from the volume of doctrine comments.

Given that density, the one class of defect that is *not* self-defended is the file's own prose
citations into *other* modules — and that is where the verified finding below sits.

---

## Finding 1 — MINOR/QUESTION: three of the six cross-module line citations this file itself
claims to have "spot-checked... and all still accurate" have since drifted

**Location:** `src/verify_math.py:11720-11723` (comment inside §20ad, "THIS FILE MAY NOT CITE
ITSELF BY LINE NUMBER"):

> "WHY THE SELF-CITATIONS ROT AND THE CROSS-MODULE ONES DO NOT. Spot-checked the same day:
> `standards.py:751`, `standards.py:67`, `standards.py:1901`, `anchors.py:427`, `sevenfold.py:86`
> and `assay.py:147-189` were all still accurate. They hold because they point at OTHER files,
> which this file's own growth does not move."

These six citations also appear as the load-bearing prose in the actual checks that use them
(e.g. `standards.py:751` at lines 4511, 4533; `standards.py:1901` at line 4301; `anchors.py:427`
at line 7953).

**Verified against the actual current source** (`git`-free repo, so checked by direct line
inspection with `sed -n`):

| Citation | Claimed line | What's actually there now | Where the real thing lives now |
|---|---|---|---|
| `standards.py:751` | the cut where `standards.check()` stops rendering a success % and says UNMEASURED (`if calls < MIN_CALLS_TO_JUDGE_RATE:`) | line 751 is inside the unrelated `dry = [...]` / `frac_dry` block | **line 790** (`grep -n "if calls < MIN_CALLS_TO_JUDGE_RATE:" standards.py` → 790) |
| `standards.py:1901` | the call site of `ollama_token_flow()` inside `standards.check()` | line 1901 is prose inside an unrelated comment about a stall | **line 1968** (`flow, secs = ollama_token_flow()`) |
| `anchors.py:427` | "indexes this table [INSTRUMENT_WINDOWS] across the whole Ladder unguarded" | line 427 is inside an unrelated `verdict(...)` call in a different check | **line 546** (`collapsed = [b for b in A.LADDER if A.INSTRUMENT_WINDOWS[b][0] == ...]`) |
| `standards.py:67` | `MIN_CALLS_TO_JUDGE_RATE = tuning.MIN_CALLS_TO_JUDGE` | ✅ still exactly there | — |
| `sevenfold.py:86` | `remaining = set(members)` | ✅ still exactly there | — |
| `sevenfold.py:214` | `sorted(set(cuts))` | ✅ still exactly there | — |
| `assay.py:147-189` | the four-status (NONE/UNESTIMABLE/INAPPLICABLE/measured) doctrine block | ✅ still substantially the right span (`FACULTY_WEIGHTS` at 145, `NONE =` at 190) | — |

**How I verified it:** ran `sed -n` against the live `standards.py`, `anchors.py`, and
`sevenfold.py` at the cited line numbers, then `grep -n` for the actual code the citing prose
describes, in the same files, to find where it lives today.

**What is wrong:** three of the six citations the file itself uses as evidence that
"cross-module citations don't rot" have in fact rotted — by 39, 67, and 119 lines respectively.
This doesn't currently break any *assertion* (none of the checks that cite these lines rely on
the line number computationally; the citations are prose evidence inside comments/notes, not
program logic), so it's not a false-passing check. But it is precisely the "STALE CITATIONS"
defect class this sweep is hunting, in the one file that spends the most text in the whole
project arguing that self-citations must be avoided because they rot — while asserting, as its
own supporting evidence, a set of cross-file citations that (it turns out) rot too, just more
slowly. The argument's premise ("this file's own growth does not move them") is true but
incomplete: it ignores that the *cited* file's own growth moves them, which is exactly what
happened to 3 of 6.

**Proposed remedy:** Either (a) drop the specific line numbers from the §20ad comment and cite
those five properties by symbol the same way §20ad demands of self-citations (a function name —
`ollama_token_flow`, `INSTRUMENT_WINDOWS` — rather than `file.py:NNN`), or (b) if the numbers are
kept as a "spot-checked on this date" historical record, timestamp-qualify the claim explicitly
("as of 2026-09-08; not re-verified since") so a future reader doesn't take "all still accurate"
as a standing guarantee. Given this file's own stated doctrine (§20ad, §20b, §20p, §24 — "cite by
symbol, not by line"), (a) is the more consistent fix. This is filed as MINOR rather than MAJOR
because no check's pass/fail behavior depends on the number; it is a documentation-integrity
regression, not a correctness one.

---

## What I read and found nothing wrong in

- The overall harness (`check()`, the atexit-based crash net at `_verdict_even_if_a_row_raised_vm`,
  `_at_vm`): sound, and both directions are tested with controls (verified lines 43–172, 4383-4389).
- The ledger-suppression machinery (`_no_ledger_vm`, `_third_party_vm`, `_spy_record_vm`,
  `_spy_flush_vm`, §20z's whole closing block, lines 210–585 and 11834–12069): the wrapper is
  exercised with its own positive/negative controls, the exemption list is checked against the
  actual `silence.note(...)` call sites in `standards.py`/`dashboard.py`/`overnight.py`, and the
  witness that reads `state/failures.json` directly is kept separate from the in-process spy. I
  did not find a hole in this reasoning.
- Every `except: pass`-shaped block I located via `grep` (~45 sites) either carries a
  `silence-exempt:` comment naming why noting would be worse than silent, or is wrapped in
  `_no_ledger_vm()`/`_third_party_vm()` with an explicit assertion on the return value
  immediately following — i.e. none of the exception-swallowing in this file matches the "fail-open
  silence" pattern (an error that is discarded with nothing asserted about it downstream).
- Hard Rule 0 (unmarked caps): I found one deliberately-marked sample (`PR.build_all(limit=400)`
  at line 1570, explicitly labeled "A SAMPLE, and labelled as one") and dozens of rows that
  *assert the absence* of a cap in other modules (§19g, §19o, §19v, batch3's `coverage.report`
  rows, etc.). I found no unmarked truncation of an operator-facing roster/finding within this
  file itself.
- The many `check(label, X, True)`-shaped rows I spot-checked for the "compares a thing to
  itself" tautology (the file's own most-repeated defect class) were, in every case I checked,
  either genuinely independent computations, or a documented/fixed instance of the tautology with
  a companion control proving the fix has teeth (e.g. the `map_seed(x) == map_seed(x)` tautology
  at §13, repaired via `_asfresh`; the `SF.build()` tautology at §16; `AS.assign(...)` at §13).
- The `_ledger_counts_vm` / abstention-banner logic: correctly distinguishes "nothing moved" from
  "could not be read" (order d43a5a050c0f), and I did not find a case where an unreadable ledger
  would silently read as a clean run.

## Coverage note

Deliverable 2's `sweep_plan.record` command is run separately (see chat reply); I am reporting
its result there rather than duplicating it here since this file must not describe a run it
hasn't itself observed.
