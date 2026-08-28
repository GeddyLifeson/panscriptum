# Cross-module changes required by run #36, RUN rung, wave 2c

Wave 2c owns `verify_math.py`, `workorders.py`, `thread_integrity.py`, `chain.py`. Everything
below needs a file this wave does **not** own, so it is written here rather than edited.
Nothing here is applied.

---

## 1. `src/prose_gate.py` line 34 — one §-tag citation, from order c30618e03a36

**Why.** `§19s` named TWO sections of `verify_math.py`: the metrics-ledger-timestamp section
(~line 2494) and the prose-interlock battery (~line 4642). The third such collision found in
that file in this shift, fixed the same way §20e and §20f were fixed earlier today.

Which section each citer meant was determined by reading the citer, not assumed:

| tag | kept by | renamed to | citers |
|-----|---------|-----------|--------|
| `§19s` | the metrics-ledger timestamp section | — | `BUGS.md` m61 (~line 2890), `BUGS.md` m63 (~line 2816, the run #14 tie-break that awarded §19s to this section by name), `HANDOFF.md` (~4106, ~4121, ~4171) — **no change** |
| | THE PROSE INTERLOCKS, AT EVERY LAYER | **`§20x`** | `src/prose_gate.py:34` |

The metrics section keeps the tag because it has the older claim and every existing citation
except one. `§20x` is the next free letter after `§20w` (`§20o` stays skipped — it reads as a
zero), and the §20 run is the right series: the section sits inside it, between §20j and §20p.

**The one edit, by its surrounding text rather than by line number (lines drift):**

1. In `src/prose_gate.py`, the line reading
   ``  PROVEN        Each layer has a check in verify_math §19s that goes red if the layer is removed``
   → `§19s` becomes **`§20x`**.

**This is not urgent and nothing dangles without it.** The renamed section now PRINTS its old
tag and names its citer:

```
    §20x  THE PROSE INTERLOCKS, AT EVERY LAYER, INCLUDING THE OPERATORS
          [tagged §19s until run #36, when §19s was found to name TWO sections;
           prose_gate.py:34 cites this one as §19s. §19s now names the
           metrics-ledger-timestamp section only]
```

so a grep for `§19s` over `verify_math.py` or its console output still lands on both sections.
Applying the edit above is what finally retires the ambiguity; until then it is signposted
rather than silent.

**A fourth collision can no longer arrive quietly.** `verify_math.py` §20y (added with this
order) reads its own source and asserts that no two `# ---- Section` headers share a tag, plus
a second row asserting the parser actually found the headers — a matcher that matches nothing
would report zero duplicates and look exactly like a clean file.

---

## 2. `BUGS.md` line ~3019 — a §-tag citation that was ALREADY dangling before this rename

Found while reading §19s's citers; **not caused by this shift**, and not fixed here because
`BUGS.md` is not this wave's to edit.

The sentence
`concurrency test hung. Now uses `OpenProcess` + `GetExitCodeProcess`. Pinned by §19s.`
is about the GPU lane's dead-holder fix. That section is **`§19u`**, not `§19s` — run #14
(BUGS.md m63) renamed it when it split the `19s` pair at lines 2067/2163, and this citation was
not moved with it. It has resolved to the wrong section ever since.

→ `§19s` becomes **`§19u`** in that sentence only. Leave m61's and m63's `§19s` alone: those two
do mean the metrics-timestamp section, which keeps the tag.

---

## 3. Not a cross-module change, but the coordinator should know

`verify_math.py` ends this wave at **1053 passed, 1 FAILED**. The single failure is
`the live sweep proves its own completeness`, which lists 40 modules and is the expected
in-progress state while the whole-tree sweep is still running — it was already red on the
pre-edit baseline (which was 1051 passed, 2 FAILED; the second failure there was this wave's
own `[495390283745]` row, now fixed rather than described). Every check this wave added or
rewrote passes.
