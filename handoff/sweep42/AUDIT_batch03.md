# AUDIT — batch 03 (sweep42)

Modules read in full: `src/pipeline.py` (2809 lines), `src/estate.py` (616), `src/reference.py`
(481), `src/burgs.py` (402), `src/cleanup.py` (313), `src/tempus.py` (275), `src/compress_store.py`
(150), `src/catalog.py` (139).

General note: these eight modules — `pipeline.py` especially — are unusually heavily self-audited
already. The great majority of exception handlers, caps, and gates carry inline docstrings/comments
explaining a prior incident and the fix, with `silence.note(...)` calls attached. Those were read
and are NOT re-reported here as new findings. What follows is what still looks live.

---

## CONFIRMED DEFECTS

### 1. `src/cleanup.py:272-288` — six report rosters silently truncated to 4-6 rows, no "and N more"

```python
print(f"\n1. wiki navigation removed from the catalogue : {len(nav):,}")
for s, n in nav[:5]:
    print(f"     {s[:26]:<28}{n}")
print(f"\n2. ceiling entities reduced to a name        : {len(ceil_fixed):,}")
for s, before, after, how in ceil_fixed[:6]:
    ...
print(f"   still unresolved (left alone, not guessed) : {len(ceil_unres):,}")
for s, ce in ceil_unres[:4]:
    ...
print(f"\n3. descriptions with markup stripped         : {len(desc_fixed):,}")
for s, n, b, a in desc_fixed[:5]:
    ...
print(f"\n4. descriptions too thin to write from       : {len(thin):,}  (marked, not deleted)")
for s, n, d in thin[:5]:
    ...
```

Each of these five loops shows only the first 4-6 entries of a findings roster and prints nothing
to indicate rows were cut — no "... and N more", no "e.g.", no "showing first N of M". Contrast
with the SAME file's own `unwritten` list twelve lines later, which is explicitly disclosed:

```python
for s in unwritten[:12]:
    print(f"     {s}")
if len(unwritten) > 12:
    print(f"     ... and {len(unwritten) - 12:,} more")
```

This is exactly the shape Hard Rule 0 names and that this same codebase has already fixed twice
elsewhere in the batch under audit:
- `src/catalog.py:63-78`, whose own comment says: *"This was `for n in missing[:30]` followed by
  an '... and N more' line... the roster was unreachable rather than merely folded, and this is
  the exact pathology Hard Rule 0 names by example."*
- `src/pipeline.py:2443-2451` (`phase_write`'s `refused` list), fixed the same way with the same
  reasoning ("a refusal roster is a roster").

`cleanup.py`'s own module docstring makes the point sharper than usual: *"These were filed as
'cosmetic', which was the wrong word for them"* — the module exists specifically to surface defects
an operator needs to see and act on (wiki-nav entries wrongly catalogued, ceiling entities that
still need resolving by hand, thin descriptions). A person reading only the console output has no
way to know 179 more wiki-navigation entries or 40 more unresolved ceilings exist beyond the five
printed, and no signal that they should go look at the underlying record instead of trusting the
printout is complete.

**Confidence: high.** The pattern, the missing disclosure, and the precedent for exactly this fix
within the same audited file set are all clear-cut.

---

### 2. `src/reference.py:427-431` — diagnostic `reason` field truncated with no cut marker

```python
got = row.get("result")
if not got or got.get("decimal") is None:
    status = row.get("status") or "no result"
    print(f"{name:<20}{'--':>12}{status.lower():>12}"
          f"{'':>8}  {str(row.get('reason') or '')[:44]}")
    continue
```

`row.get("reason")` is cut to 44 characters with a bare `[:44]` slice — no `...`, no indication
the string was cut. This is the identical defect class `estate.py`'s own `_brief()` helper was
written to fix (`estate.py:101-115`), whose docstring is explicit about why a bare-slice cut is
dangerous for a diagnostic string: *"a report row that ends mid-word is indistinguishable from one
that simply ended there... this module exists to tell a person ... WHERE [the fault is]; a cut
that silently drops it is this module's own signature defect turned on its own output."* The same
reasoning applies here: `reason` is presumably prose explaining why an automated Assay produced no
usable result for that entity, and a 44-character hard cut risks losing exactly the actionable
tail of that sentence, with no way for the reader to know it happened.

**Confidence: medium.** This is a `--compare` debug/calibration tool rather than a live pipeline
path, so the blast radius is small, but the defect shape (truncate a diagnostic string with no
"cut here" marker) is exactly what this project has already identified and fixed once elsewhere.

---

### 3. `src/pipeline.py:507-509` — `ask()`'s failure log truncates the exception message unmarked

```python
except Exception as e:
    if attempt == retries:
        log(f"    ollama failed after {retries + 1} tries: {type(e).__name__} {str(e)[:80]}")
        return None
```

Same defect class as #2: `str(e)[:80]` with a bare slice, no ellipsis, no marker that the message
was cut. `estate.py:101-115`'s `_brief()` docstring specifically calls out that
`json.JSONDecodeError` (and, by the same logic, many `urllib`/socket exceptions) put the
actionable detail — line/column, or the actual failing host/reason — at the END of the message,
which is exactly what a plain `[:80]` removes. This is the line an unattended overnight run
relies on to say *why* a model call failed after three tries; a cut with no marker means a reader
of `state/pipeline.log` cannot tell whether they are looking at the complete reason or a truncated
fragment.

**Confidence: medium.** Same defect shape as an already-fixed case elsewhere in this codebase
(`estate.py:_brief`), but this is a log line rather than a piece of data that gets written back to
a record, so the cost of being wrong is "harder overnight debugging," not corpus damage.

---

## QUESTIONS (may be deliberate; not fixed, not flagged as defects)

### Q1. `src/estate.py:357-365` — `un[:4]` sample in the spine-code gap report

```python
un = sorted(recs - set(codes))
if un:
    note("catalogued sources with NO charter spine code",
         f"{len(un)} — e.g. " + ", ".join(un[:4]))
```

Same shape as Finding #1 (a roster cut to 4 with the rest invisible), but here the cut is
explicitly marked with "e.g." and the total count is given, which is a real (if minimal) admission
that the list is a sample rather than complete. Given Hard Rule 0's stated tolerance for ranking
but not truncation, and that this note feeds `allsweep`'s reporting the same way `cleanup.py`'s
findings feed an operator, I'm not confident this crosses the line the same way Finding #1 does —
raising it as a question rather than folding it into #1.

### Q2. `src/pipeline.py:1140-1145` (`synthesis_prompt`) — per-entity feat/description sampling

```python
if fl:
    d = " | ".join(re.sub(r"\s+", " ", x)[:150] for x in fl[:3])[:420]
else:
    d = re.sub(r"\s+", " ", e.get("description", ""))[:300]
```

Only the first 3 of an entity's mined feats are shown to the model per nomination call, and each
feat/description is character-capped. This is a different question from the block-cap that was
already removed from `synthesis_blocks` under Hard Rule 0 (no *entity* is excluded from
nomination any more) — this is about how much evidence is shown *per entity* once it is included.
If an entity's strongest feat is its 4th-mined one, the model never sees it for that call. Given
how much of this exact function has already been rewritten specifically to close Hard-Rule-0-style
gaps, and given the extensive commentary elsewhere in `pipeline.py` about "input" truncation for
model-cost reasons being treated differently from "roster" truncation, I'm treating this as an open
question about where that line sits rather than asserting it is wrong — it looks more like a
prompt-budget engineering choice than a decision that an entity "doesn't count."

### Q3. `src/pipeline.py:2471-2495` (`phase_write`) — the reverted third arm

Already raised and left open in the code itself as a filed disagreement about what an empty-cast
source should mean for `gate_done`'s closing behaviour (drill net
`_write_phase_stays_open_when_everything_refuses` requires the vacuous case to close; a
since-reverted patch tried to hold it open instead). Not re-litigated here — flagging only so this
audit's coverage of `pipeline.py` records that the passage was read and the standing disagreement
is with the owner, not unnoticed.

---

## Coverage

Recorded via `sweep_plan.record('run42', [...], batch=3)` — see the command in the audit brief.
