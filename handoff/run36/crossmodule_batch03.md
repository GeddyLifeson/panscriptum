# Cross-module changes required by run #36, RUN rung, batch 3

Batch 3 owns `backfill.py`, `endpoint.py`, `pipeline.py`, `policy.py`, `verify_math.py`.
Everything below needs a file this batch does **not** own, so it is written here rather than
edited. Nothing here is applied.

---

## 1. `BUGS.md` — four §-tag citations, from order a5018a0c8ee2

**Why.** `§20e` and `§20f` each named TWO printed sections of `verify_math.py`, so a citation to
either resolved to a coin flip. Fixed in `verify_math.py` this run by giving the two interlopers
fresh tags. The tags are stable identifiers cited by name from outside the file, so the citers
have to move with them.

Which section each citer meant was determined by reading the cited bug, not assumed:

| tag | kept by | renamed to | citers |
|-----|---------|-----------|--------|
| `§20e` | §25 NO CONSOLE WINDOWS | — | `BUGS.md` m127 (line ~639) — **no change** |
| | §24 A LIVENESS REPORT MUST NOT DELETE THE REPORTER | **`§20v`** | `BUGS.md` M17 (line ~2302), m87 (line ~2313) |
| `§20f` | §26 RIGOR'S PROSE MUST NOT OUTLIVE RIGOR'S DATA | — | `src/rigor.py:123`, `BUGS.md` m88 (~2322), m89 (~2329) — **no change** |
| | §27 A PERMANENT REFUSAL MUST NOT BE FILED AS CONTENTION | **`§20w`** | `BUGS.md` m108 (line ~1069), m98 (line ~2273) |

`src/rigor.py:123` needs **no** edit: it cites `§20f`, and `§20f` still names the rigor-prose
section. That is why that section was chosen to keep the tag.

**The four edits, by their surrounding text rather than by line number (lines drift):**

1. In the **m108** entry, the sentence reading
   `Pinned by 7 more checks in `verify_math` §20f. Export commit `e234107`.`
   → `§20f` becomes **`§20w`**.
2. In the **m98** entry, the sentence reading
   `Pinned by 16 new checks in `verify_math` **§20f**. Also repaired in the same pass: `ask()`'s`
   → `§20f` becomes **`§20w`**.
3. In the **M17** entry, the sentence reading
   `unaffected — it runs its own enumeration and never self-excludes. Pinned by `verify_math` §20e,`
   → `§20e` becomes **`§20v`**.
4. In the **m87** entry, the sentence reading
   `above it moves. Pinned by `verify_math` §20e.`
   → `§20e` becomes **`§20v`**.

Leave m127's `§20e` and m88/m89's `§20f` alone.

**These edits are not urgent and nothing dangles without them.** Both renamed sections now PRINT
their old tag and name their citers, e.g.

```
24. §20v  A LIVENESS REPORT MUST NOT DELETE THE REPORTER — each renderer was
          reporting ITSELF down, and the noise hid the job that really was
          [tagged §20e until run #36, when §20e was found to name TWO sections; BUGS.md
           M17 and m87 cite this one as §20e. §20e now names §25 (console windows) only]
```

so a grep for `§20e` — over the file or over the console output — still lands on both sections.
Applying the four edits above is what finally retires the ambiguity; until then it is signposted
rather than silent. **Do not re-tag anything else**: `§20o` is deliberately skipped (it reads as a
zero), and `§20v`/`§20w` are the next free letters after `§20u`.

---

## 2. Not a cross-module change, but the coordinator should know

Two checks in `verify_math.py` were RED at the end of this batch's shift. **Neither is batch 3's
and neither is in any batch-3 order**; both are source-text pins on modules another agent was
editing while this ran (`feats.py` mtime moved twice during the shift, `canon_backup.py` once).

* `the discovery caps are measured rather than argued about` — already red on the pre-edit
  baseline. The pin greps `feats.py` for `(ap or {}).get("continue")`; `feats.py` now spells the
  same continuation walk as `cont = d.get("continue")` inside `_walk_all`, and the invariant is
  intact and arguably stronger (a repeated continuation token now counts as `_CAP_BOUND`). This
  is a stale pin, not a regression — but the fix belongs to whoever owns `feats.py` this shift,
  so it was left alone rather than churned.
* `the live sweep proves its own completeness: got ['canon_backup.py'], want []` — appeared
  DURING this shift, not on the baseline. `canon_backup.py` is being added or reworked right now.

Baseline before batch 3's edits: **1051 passed, 1 FAILED**. After: **1051 passed, 2 FAILED** —
the delta is entirely the `canon_backup.py` row arriving from another agent. All seven checks
batch 3 added or rewrote pass.
