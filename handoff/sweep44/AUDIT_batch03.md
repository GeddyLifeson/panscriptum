# Sweep 44 — Batch 3 Audit

Modules read in full: `src/pipeline.py` (2,825 lines), `src/threads.py` (631 lines),
`src/autostart.py` (503 lines), `src/catalogue_codex.py` (405 lines), `src/grounding.py`
(335 lines), `src/tells.py` (281 lines), `src/ledger.py` (173 lines).

Overall impression: these seven modules carry an unusually high density of in-line
provenance for defects already found and fixed by earlier sweeps (the m-numbered and
order-numbered comments). That made this pass slower than usual — most candidate findings
turned out to already be the *documented fix* for a prior bug, not a fresh one — but it also
meant the remaining candidates below survived that filter. Everything quoted below was
checked against the actual line numbers listed; nothing here is inferred from a docstring
alone.

---

## src/pipeline.py

### Finding 1 — the per-entity feat list fed to the ceiling-nomination prompt is capped at 3, unranked (Hard Rule 0 candidate)

`src/pipeline.py:1153-1166`, function `synthesis_prompt`:

```python
def synthesis_prompt(src, sample, feats_for, ci, nchunks, total):
    """The prompt for one nomination block. Same spelling for the main phase and the retry."""
    lines = []
    for e in sample:
        fl = feats_for.get(e["name"]) or []
        if fl:
            d = " | ".join(re.sub(r"\s+", " ", x)[:150] for x in fl[:3])[:420]
        else:
            d = re.sub(r"\s+", " ", e.get("description", ""))[:300]
        lines.append(f"- {e['name']} [{e.get('type','')}]: {d}")
```

`fl` is the full list of mined feat sentences for one entity (`_mined_feats`, lines
1064-1095, applies no cap when it builds this list). `fl[:3]` silently keeps only the first
three feats in whatever order the feats file stored them — `_mined_feats` does not sort by
significance, size, or any proxy for magnitude, it just returns
`[x.get("feat") for x in (d.get("feats") or []) if x.get("feat")]` in file order. So an
entity mined with, say, twelve feats has nine of them thrown away before the model that
nominates the source's power ceiling ever sees them, and there is no guarantee the three
that survive are the strongest three.

This is exactly the shape Hard Rule 0 (CLAUDE.md, and restated at the top of `pipeline.py`'s
own `PHASES`/`SUBROOMS` commentary) forbids: an ordered-then-truncated list standing in for
the whole one, deciding on the entity's behalf that its fourth-strongest feat and beyond do
not exist for the one call whose entire job is picking the source's power ceiling. The
`synthesis_blocks` docstring immediately above this function (1098-1150) is emphatic about
not capping the *number of entities* nominated per source ("no feat-bearing entry is ever
excluded from nomination") — but the cap that survived is one level down, on the *evidence*
each nominated entity is allowed to bring. An entity whose true ceiling-worthy feat is its
4th, 5th or later mined sentence would have that feat silently withheld from the model doing
the nomination.

Both callers of `synthesis_prompt` — `phase_synthesis` (the main phase) and
`retry_synthesis.synthesise()` per this file's own docstring at line 1104-1109 — share this
function, so the cap applies identically to both paths.

Confidence: **high** that this is a real, unguarded `[:N]` slice on an ordered list of
evidence with no ranking applied first; **medium** on severity, since the outer `[:420]`
character budget on the joined string means a fix would need a token-cost tradeoff rather
than being free, and the same paragraph elsewhere in this file treats character-length caps
on transcribed text (`description[:300]`, `evidence[:600]`) as an accepted convention. The
distinguishing fact here is that `fl[:3]` truncates a *count of items*, not a *string
length* — the same category of cut the file itself calls out and forbids a few functions
away.

### Finding 2 (question, not a defect) — `synthesis_blocks`: a source with any mined feats never nominates its feat-less entries at all

`src/pipeline.py:1148-1150`:

```python
    blocks = ([with_feats[i:i + 14] for i in range(0, len(with_feats), 14)]
              or [rest[i:i + 14] for i in range(0, len(rest), 14)])
    return (blocks, feats_for)
```

`with_feats` (entries with at least one mined feat) and `rest` (entries with none) are
built earlier in the same function. Because of the `or`, `rest` is consulted **only when
`with_feats` is completely empty** for the source. So a source with even a single
feat-bearing entry among hundreds never sends any of its feat-less entries to the model at
all, for the entire life of the source (barring a later mining pass adding feats to them).

Reading one way, this is exactly the intended design the surrounding docstring argues for:
feats are the reliable signal, and an entity with no mined feat contributes nothing a
description-only pass could not already provide worse. Reading the other way, the mining
pass (`feats.py`, out of this batch's scope) is not guaranteed to be exhaustive over a
source's cast — an entity that legitimately has the strongest demonstrated feat in its
source but that the miner has not yet reached would be silently excluded from every
nomination call for as long as the source has *any other* mined entity, with nothing in the
pipeline's logs flagging that the fallback path was skipped for that reason. I could not
verify from this file alone how complete `feats.py`'s mining is, so I am filing this as a
question rather than a defect: is a source's `rest` list meant to stay permanently unreached
once mining has touched any one of its entries?

---

## src/autostart.py

### Finding 3 — `--status`'s per-job loop collapses the tri-state `running()` signal the same file just built out for the supervisor line

`src/autostart.py:199-227` (`supervisor_alive`) documents at length why a two-way
true/false collapse of "is this process running" is dangerous — a `None` ("could not tell")
must never be read as "dead", because acting on it is what caused the respawn-loop incident
this whole module exists to prevent. `main()`'s own supervisor line, four lines above the
one below, honours that:

```python
# src/autostart.py:477-480
_alive = supervisor_alive()
print("supervisor       : " + ("running" if _alive else
                               "UNKNOWN (could not read the process table)"
                               if _alive is None else "NOT running"))
```

That correctly distinguishes all three states (verified: Python's chained conditional binds
so `True` -> "running", `None` -> "UNKNOWN", `False` -> "NOT running"). But the very next
block, reporting every *other* standing job by the same mechanism, does not:

```python
# src/autostart.py:492-495
for job in ON.ALL_JOBS:
    if job in ("autostart.py", "overnight.py"):
        continue
    print(f"  {job:<16}" + ("running" if ON.running(job) else "not running"))
```

`supervisor_alive()` calls `ON.running("overnight.py")` and explicitly treats its result as
tri-state (`return None if up is None else bool(up)`, line 224) — confirming
`overnight.running(name)` can return `None` for *any* job name, not just the supervisor's
own. The loop above passes that same tri-state return straight into a bare `if`, so a job
whose process-table read fails (the exact "WMI hiccup" scenario `supervisor_alive`'s
docstring describes) is reported as flatly "not running" rather than "UNKNOWN" — the precise
conflation this file spent forty-plus lines of docstring explaining is unsafe, reintroduced
three lines below the fix.

Because this is a status *report* rather than a decision that starts or stops a process, it
does not by itself cause the respawn-loop failure mode the rest of the module guards
against. But it can mislead a person reading `--status` into believing a job has died and
needs manual intervention when the process table was simply unreadable at that instant.

Confidence: **high** that the code reads as shown and is inconsistent with the tri-state
handling four lines above it in the same function; **medium** on whether `overnight.running()`
can actually return `None` for a job other than `overnight.py` itself, since `overnight.py`
is outside this batch's assigned modules and I did not read its source — the inference rests
on `supervisor_alive`'s own docstring and code treating `running()` as generically tri-state,
not on having read `overnight.running`'s body directly.

---

## src/catalogue_codex.py

### Finding 4 (minor, low confidence) — a roll source name that normalises to the empty string is silently skipped, unlike every other refusal path in this module

`src/catalogue_codex.py:210-238`:

```python
for r in roll:
    if r.get("entry_count", 0) > 0:
        continue
    n = norm(r["name"])
    title = None
    if n and n in sec_by_norm:
        title = sec_by_norm[n]
    if not title and n:
        cands = sorted({t for k, t in sec_by_norm.items() if n in k or k in n})
        if len(cands) == 1:
            title = cands[0]
        elif len(cands) > 1:
            ambiguous.append((r["name"], cands))
    if not title:
        continue
```

`norm()` (line 76-77) keeps only `c.isalnum()` characters. If a roll source's name contains
no alphanumeric characters at all (Python's `str.isalnum()` covers Unicode letters/digits
too, so this needs a name built entirely of punctuation/symbols — an edge case, not the
common one), `n` is `""`, both `if n and ...` guards are false, and the loop falls straight
to `if not title: continue` with **no entry in `ambiguous`, no entry in `norm_clashes`, and
no printed line at all**. Every other refusal path in this same function (an ambiguous
substring match, a normalised section-title collision, a register description collision) is
explicitly collected and printed for an operator to act on — this is the one silent path.

I could not find a source name on the actual roll that would trigger this (the roll is
data, not code, and outside this batch's scope), so I cannot say whether it has ever fired.
Filed as a minor gap for completeness rather than a demonstrated defect: confidence **low**
that this has ever mattered in practice, but the asymmetry with its neighbours (which do
report) is real and easy to check by grepping `data/SWEEP_ROLL.json` for a name with no
alphanumeric characters.

---

## src/threads.py

Read in full; no new defect found. The module's own docstring already documents and
corrects its prior tautological `verify()` checks (audit T-3) and its prior silent-blank
`threads_for()` bug (audit T-4), and both repairs check out against the current code:
`verify()` (447-506) now runs against a round-tripped, re-parsed graph rather than the
in-memory object `build()` just returned, and `threads_for()` (408-444) raises
`ThreadRefused` rather than returning `[]` for an unaddressed source. `cohort_family`'s one
`[:2]` slice (line 152) is address decomposition (`Collection.Set` from a dotted spine
code), not a listing truncation, and is correctly distinguished from Hard Rule 0 by the
module's own comment at lines 76-81.

## src/grounding.py

Read in full; no new defect found. `classify_source`'s `cap` parameter (177-204) is
deliberately refused with a `SystemExit` rather than silently honoured — a real Hard Rule 0
guard rather than a violation — and `classify_text`'s `top` parameter (125-174) defaults to
the whole ranked field rather than truncating it, per the fix documented in the same
docstring. Verified the fix is actually in effect: `classify_source` calls
`classify_text(" ".join(parts))` with no `top` argument (line 222), so the default (whole
field) is what is actually used at the real call site, not just in the function signature.

## src/ledger.py

Read in full; no new defect found. Checked `assay_to_standards`'s edge-of-ladder handling
(154-169) against `assay.LADDER`'s actual definition (`src/assay.py:107`,
`["M0", "M1", ..., "M10"]`, ascending) to confirm `LADDER[i + 1]` really is the next
*higher* band rather than a lower one under a reversed ordering — it is, so the M10
edge-case fallback (`hi = lo * (lo / prev)`) computes an increasing function of `ruin_score`
as intended, not an inverted one.

## src/tells.py

Read in full; no new defect found. `_anchor`'s string-slice rewrite of the `^\s*` prefix
(lines 148-149) is positionally correct for every pattern in `STRUCTURAL`/`DISCOURSE` that
actually begins with the literal 4-character sequence `^\s*`, and the guard loop at
155-159 would catch a control-character corruption of any of these patterns the same way
every other module in this kit does.

---

## Coverage note

All seven assigned modules were read top to bottom in this session (not sampled). The
`sweep_plan.record` call for this batch is being made separately per the task instructions.
