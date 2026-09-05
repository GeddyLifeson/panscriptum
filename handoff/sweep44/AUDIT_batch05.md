# AUDIT — sweep44, batch 05

Modules read in full: `src/mutate.py`, `src/ledger_guard.py`, `src/estate.py`,
`src/reference.py`, `src/prose_gate.py`, `src/coverage.py`, `src/scope.py`,
`src/repass_bands.py` (5,144 lines).

Special note per the work order: `prose_gate.py` was audited for correctness only — no
finding here proposes opening `prose_enabled` or `step4_enabled`, or weakening any of its four
layers. `mutate.py`'s `rebaseline_every` / `_refresh_baseline` code (added the day of this sweep)
received the closest reading in the batch, since it is the newest and least-reviewed code here
and a mutation run is live against this tree while this audit runs.

---

## src/mutate.py

### 1. `_refresh_baseline` can adopt a broken photograph mid-run, reintroducing the exact false-kill failure the module spends its whole docstring guarding against elsewhere — MAJOR, high confidence

`_run_mutation`, lines 1621–1635:

```python
def _refresh_baseline():
    """Re-photograph the gates on RESTORED code. -> True if anything moved."""
    _write(path, original)
    fresh = baseline(root, gates=tuple(gates) + tuple(confirm))
    moved = {g: (base.get(g), fresh.get(g)) for g in fresh if fresh.get(g) != base.get(g)}
    if moved:
        drifted.append({"at": time.time(), "gates_that_moved":
                        {g: {"was": w, "now": n} for g, (w, n) in moved.items()},
                        "verdicts_now_in_doubt": list(judged_since)})
        base.update(fresh)
    del judged_since[:]
    return bool(moved)
```

Compare this with the initial baseline established in `_session` (lines 1879–1895), which is
explicitly gated by `unusable_gates(base)` before anything is trusted — a gate that times out or
errors on clean code is refused outright, because (per `unusable_gates`'s own docstring)
`TIMEOUT == TIMEOUT` would otherwise report every mutant as surviving or, after the fix at
`could_not_judge`, would corrupt the comparison in the opposite direction.

`_refresh_baseline` runs the identical kind of sweep (`baseline(root, ...)`, the same function)
periodically through a run that can last sixteen hours, and adopts whatever it gets back —
`base.update(fresh)` — with **no call to `unusable_gates` or `could_not_judge` on `fresh`
first**. If a gate transiently times out or errors during one refresh sweep (`verify_math`
reaches the network per this module's own comments; `drill` runs five minutes under load), that
becomes the new `base[gate]` value — e.g. `"TIMEOUT|drill"`. Every mutant judged between that
refresh and the next one then has its real, healthy gate signature (`"rc=0|..."`) compared
against a baseline value that means "the baseline sweep itself broke," differs from it every
time, and is scored **KILLED** — for a reason that has nothing to do with the mutation. This is
precisely the failure class `could_not_judge` was written to close for the per-mutant judging
loop (see its own docstring, "False kills are the direction that HIDES holes, and they look
exactly like real ones"), reopened in the one code path that doesn't call it.

The safety net is partial, not absent: at the *next* refresh, comparing a since-recovered
`"rc=0|..."` against the corrupted `base[gate]` will itself register as `moved`, and the window's
`judged_since` (which does carry each verdict's line and mutation description) gets appended to
`drifted` and printed in `_session` as a doubted window. So a bad refresh is eventually flagged —
one cycle late — but only if the run survives to see that next refresh. A run killed while the
baseline is sitting corrupted (the exact scenario `reap_orphans`, `_lock_release`, and half of
this module exist to handle gracefully) loses the correction along with the process.

**Fix shape, not applied (audit only):** `_refresh_baseline` should reject an unusable `fresh`
(one containing a `could_not_judge` signature) before calling `base.update(fresh)`, the same way
the initial baseline is protected — either by refusing the refresh outright and reusing the old
`base`, or by updating per-gate only for gates whose fresh signature is itself judgeable.

### 2. Baseline-drift records are not persisted incrementally, unlike survivors — MEDIUM, medium confidence

Survivors are written to `state/MUTANTS_SURVIVED.jsonl` the instant they're found, via
`_journal` (lines 1710–1714), specifically because (per the block comment at lines 1689–1699) "a
long run must not hold its findings in memory until it is finished" — a 3.7-hour run once lost
20 found survivors to a crash immediately after printing the summary line.

The `drifted` list built by `_refresh_baseline` (and the `judged_since` entries it carries,
which are the only record of which specific mutants were judged under a since-discredited
baseline) has no equivalent durability: it lives only in the local variables of
`_run_mutation`, is returned inside the result dict, and reaches disk only via whatever the
console/log captures when `_session` prints it (lines 2011–2021). A process killed inside the
window between a corrupted refresh and the one that reveals the corruption (see finding 1) loses
that "these kills are not evidence of coverage" flag entirely — the survivors journal is
unaffected (kills are never journaled at all, only survivors are), but nothing durable records
that a stretch of "killed" verdicts should be distrusted. This is the same class of risk the
survivor-journaling design was built to close, left open for the newer mechanism.

### 3. `red_gates_disabled` stamped on a survivor row is computed once per target and never refreshed after a mid-run rebaseline — QUESTION, low-medium confidence

Line 1563:

```python
red_at_baseline = [g for g, _s in red_gates({g: base[g] for g in wanted})]
```

This runs once at the top of `_run_mutation`, before the mutant loop, and its value is stamped
onto every survivor journaled for the rest of that target's run (line 1714, 1719). If
`_refresh_baseline` later changes which gates are red on clean code (a gate newly red, or one
that recovers), `red_at_baseline` is not recomputed, so survivor rows filed after a mid-run
rebaseline carry a `red_gates_disabled` list describing the *original* baseline's red set, not
the set actually in force when they were scored. Given the stated purpose of this field ("so a
survivor read days later shows which detectors were down when it was scored, not only that some
were" — order 1b9a090fee64), this looks like a real gap. It may also be a deliberate
simplification (red-gate status changing mid-run is presumably rare, and the field is a
best-effort annotation rather than a proof), which is why this is filed as a question rather than
a defect.

### 4. `file_orders` silently drops any survivor whose work order could not be filed — QUESTION, low confidence (out of this batch's file scope)

Lines 1759–1777:

```python
for s in result["survivors"]:
    oid = workorders.file_order(...)
    if oid:
        ids.append(oid)
```

If `workorders.file_order` returns a falsy value for a reason other than "already filed,
harmlessly deduplicated" (a write failure, say), that survivor is quietly absent from the
returned `ids` and from the "filed N work order(s)" count printed in `_session` (line 2068), with
nothing distinguishing the two cases. `workorders.py` is outside this batch, so I cannot confirm
whether a falsy return ever means "filing failed" rather than "already on file" — flagged as a
question for whoever owns that module.

---

## src/ledger_guard.py

This module is unusually heavily self-audited already (nine or more historical incidents named
and fixed in its own comments); nothing found here rises above a minor note.

### 5. `MIN_BYTES.get(name)` floor check uses truthiness rather than `is not None` — MINOR, low confidence, no current live impact

Line 141–144:

```python
floor = MIN_BYTES.get(name)
if floor and len(text.encode("utf-8")) < floor:
```

Every value currently in `MIN_BYTES` is >= 3000, so this is not live today. But if a future
ledger were ever given a floor of `0` (as opposed to simply having no entry), `if floor` would
silently skip the check for that ledger rather than enforcing "must be non-empty" — the same
falsy-zero shape `prose_gate.floor_ok` was written specifically to refuse for the evidence floor
("a floor at or below zero is MISCONFIGURED, and a misconfigured safety refuses rather than waves
through"). Worth `is not None` for consistency with that doctrine even though nothing exploits it
today.

No other defect found in `ledger_guard.py`. `_one_insertion`, `check_append_only`,
`_lost_fraction`'s Counter-based multiset diff, the chain digest recomputation in `verify_chain`,
and the acknowledgement mechanism were all read against their own extensive commentary and each
does what its docstring claims.

---

## src/estate.py

### 6. `un[:4]` — an illustrative sample inside an otherwise-uncapped row — QUESTION, medium confidence

`charter()`, line 364–365:

```python
note("catalogued sources with NO charter spine code",
     f"{len(un)} — e.g. " + ", ".join(un[:4]))
```

Hard Rule 0's own wording is absolute — "No limit, no cap, no sample, no 'top N'" — and this is,
literally, a sample of four names out of a possibly-longer list. Two readings:

* **Not a violation.** The count (`len(un)`) is exact and uncapped; the four names are marked
  `"e.g."`, so nothing here claims completeness, and the full list (`un`) is available to any
  caller that wants it — this is closer to `ledger_guard.assert_intact`'s doctrine of a
  disclosed, reversible display cut ("the cut is kept and the cut is declared") than to the
  forbidden pattern of a `roster(limit=N)` silently returning a truncated universe as if it were
  the whole one.
* **A violation of the letter of the rule.** Hard Rule 0 names "no sample" as its own forbidden
  case, separately from "no cap" — this is exactly that, even with an accurate count alongside
  it, and the project's own history (Goku falling outside a 600-item alphabetical window) is a
  reminder that "the count is right, only the examples are cut" is precisely the kind of
  narrowing that has bitten this project before in contexts nobody initially thought risky.

Filed as a question rather than a defect because the underlying data (the count, and the full
`un` set) is not lost or hidden — only four illustrative names are chosen from it — which
distinguishes it from every incident Hard Rule 0's own text cites.

### 7. Self-check at import time leaves a file handle open — MINOR, low confidence

Line 78 (and the identical pattern in `reference.py:59`, `coverage.py:40`, `scope.py:44`):

```python
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
```

`open(...)` here is never closed or used as a context manager. This runs once per import and the
handle is reclaimed by CPython's refcounting almost immediately in practice, so the practical
impact is negligible — noted only because it is a real resource-management slip repeated across
four of this batch's eight files verbatim.

No other defect found in `estate.py`. The `_effective_ext` marker-peeling, the `.jsonl` torn-line
scan, the transient-extension carve-outs, and the four charter-table checks (band coverage, rung
count, the three named errata, and the M0–M2 erratum) were each read against their own commentary
and match it.

---

## src/reference.py

No defect found. This module is mostly hand-authored calibration data (`REFERENCE`) plus
`compute`/`card`/`citation`/`shelfmark` rendering and a `main()` that already treats a drifted
calibration as an exit-code-bearing fault distinct from a write failure (order d049dbbfed6e,
lines 375–398) — both reproduced and reasoned through in its own comments. `shelfmark`'s
rung-count clamp (lines 248–260) was checked against the three hardcoded `REFERENCE` entries and
is internally consistent (`len(upper) + len(lower) == len(RUNGS)` for all three, so the clamp
branch is currently dead code guarding against a future entry, exactly as its comment says).

---

## src/prose_gate.py

Audited for correctness only, per the work order. No finding here proposes touching
`prose_enabled`, `step4_enabled`, or any of the four in-code layers' pass/fail direction.

### 8. The entry-body regex strips any prose line that happens to start with a label word, undercounting legitimate body text — MEDIUM, medium confidence, biases toward over-refusal (the safe direction)

`section_shortfall`, lines 262–264:

```python
body = re.sub(r"(?im)^[\s*_#>-]*(%s).*$" % "|".join(
    re.escape(s.rstrip(":")) for s in REQUIRED_PER_ENTRY), "", b)
body = re.sub(r"[\s*_#>-]+", " ", body).strip()
```

`REQUIRED_PER_ENTRY` is `("Shelfmark:", "Class:", "Magnitude:", "Threads:")`. The label-presence
check earlier in the same function (line 253, `re.search(r"(?im)^[\s*_#>-]*" + re.escape(sec), b)`
where `sec` still carries its colon) correctly requires the literal colon to appear. This
body-stripping line, by contrast, strips the colon off each label first
(`s.rstrip(":")`) before building the alternation, so the pattern that removes a line from the
body-length count is `^[\s*_#>-]*(Shelfmark|Class|Magnitude|Threads).*$` — no colon required, and
`.*$` swallows the rest of the line regardless of what follows the bare word.

A genuine prose line that happens to begin with one of those four words as ordinary vocabulary —
"Threads of fate ran through both battles," "Class distinctions collapse under Gear Five" — gets
matched at the point where "Threads"/"Class" appears at (decorated) line-start and the entire
line, prose and all, is deleted from what counts toward `MIN_ENTRY_BODY_CHARS`. Given the house
style's own vocabulary (this project's material routinely discusses "threads" of narrative
connection, and the entry template's own section is literally named `Threads:`), a line
beginning with that word as the first word of a sentence is not a remote scenario.

The practical direction of this bug is the safe one for a gate whose whole purpose is refusing
under-filled entries: it can only ever make a legitimately full entry look shorter than it is,
never make a stub look fuller than it is, so its failure mode is a false refusal (an operator
re-generating a chapter that was actually fine) rather than a false pass. Flagged because it is a
genuine mismatch between the presence check's pattern (colon required) and the body-strip
pattern (colon not required) in the same function, not because it threatens the interlock's
purpose.

No other defect found in `prose_gate.py`. `gate_open`, `step4_gate_open`, `floor_ok`,
`evidence_ok`, `cited_fraction`, `cited_names_for`, `unearned_instrument`, and the
ghost/extra-entry charging in `section_shortfall` were each read against their own commentary
(all of which documents a real, previously-fixed incident) and each matches what it claims to do.

---

## src/coverage.py

### 9. `WORST COVERED` / `BEST COVERED` silently omit every host-bearing source with fewer than 40 entries, with no disclosure in the printed report — MEDIUM, medium confidence

`report()`, line 272:

```python
have = [r for r in rows if r["host"] and r["entries"] >= 40]
```

Both the "WORST COVERED WITH A HOST" and "BEST COVERED" listings are built exclusively from
`have`. A source with a wiki host and, say, 12 entries at 0% coverage never appears in either
list, and unlike the `--show` / `--show-best` caps two dozen lines later — which explicitly print
"showing N of M... more not shown" — nothing in `report()`'s output states that sources under 40
entries were excluded at all, or how many there are. The top-line summary figures (`n`, `cited`,
`read`, etc., lines 241–247) are computed over every row in `rows`, unfiltered, so the headline
numbers are accurate; only the per-source diagnostic breakdown — the listing a person reads to
decide "where the work is," per this module's own framing — quietly narrows its universe.

Two readings: this may be a deliberate, reasonable noise-reduction (a source with three entries
at 0% coverage is not statistically informative and would otherwise dominate a coverage-sorted
list with uninformative extremes), or it may be exactly the shape Hard Rule 0 names — a filtered
listing standing in for the full one with no marker that anything was left out. The absence of
any printed count of how many sources were excluded (contrast with the `hostless` listing four
lines above, which explicitly states "(N, all shown)") is what tips this toward being worth
reporting rather than dismissing: every other cut in this same function is announced, and this
one is not.

No other defect found in `coverage.py`. `state_of`'s CITED > READ > NO PAGE > NOT ATTEMPTED
precedence, the mtime-keyed per-file memo and its M23 ownership check, and the four-attempt
retry-then-fail-closed host-map load in `measure()` were each verified against their own
commentary.

---

## src/scope.py

No defect found. The highest-tier-above-floor selection in `scope_for` (lines 116–120) matches
its own "not by frequency" doctrine exactly; the `PROBE_VERSION` staleness mechanism, the
failure-vs-empty-answer distinction in `build()` (a probe failure is left unscored and retried,
a genuine empty answer is cached), and `ceiling_for`'s dict-truthiness handling of a stamped
"no scope established" record were all read against their own commentary and match it.

One inconsistency noted but not filed as a finding: the `"star system"` pattern in `TIERS`
(line 55, `r"star systems?|solar systems?|interstellar"`) lacks the `\b` word-boundary wrapping
every other tier's pattern uses. In practice this is unlikely to over-match (there is no common
English word ending in "starsystem" or similar), so it is mentioned only for consistency, not as
a defect with any known effect.

---

## src/repass_bands.py

### 10. Scale-note text is truncated to 70 characters with no truncation marker, inside the one function that elsewhere fixes the identical class of omission for entry counts — MEDIUM, medium-high confidence

Lines 52, 66, 68:

```python
demoted_sources.append((src, band, (syn.get("evidence") or "")[:70]))
...
kept_entries.append((src, e.get("name"), b, sn[:70]))
...
demoted_entries.append((src, e.get("name"), b, sn[:70]))
```

...printed later, unmarked, at lines 126 and 137:

```python
print(f"     [{b}] {str(n):<32}{sn}")
```

This module's own commentary (lines 110–122 and 128–132) documents, in detail, fixing exactly
this shape for the SURVIVORS and DEMOTED entry-count listings: both used to be capped at a small
number of rows with either a false "every one of these" claim or an undisclosed "sample of"
label, and both were deliberately uncapped and, where a cut remains anywhere in this file's
sibling modules, the doctrine cited is "the cut is kept and the cut is declared" (quoting
`ledger_guard.py`'s and `mutate.py`'s own established language for this exact situation).

The `sn[:70]` / `evidence[:70]` cuts are a different case that received none of that treatment:
the scale-note or evidence text sitting in `syn.get("evidence")` or `e.get("scale_note")` is
silently cut to 70 characters with no ellipsis, no "N more characters not shown" note, and no
mention anywhere in the surrounding commentary that this particular truncation exists or was
considered. Given that this is the exact text a person reads to judge WHY an entry was kept or
demoted — the working evidence, not a cosmetic label — and given the file's own extensive,
recent history of treating undisclosed truncation as a defect in the immediately adjacent code,
this looks like an oversight rather than a considered exception. `demoted_sources`'s truncated
evidence field (line 52) is stored but never actually printed anywhere in `main()` — that portion
of the finding has no visible effect today, but the `kept_entries`/`demoted_entries` truncation
is printed on every run for every survivor and every demotion.

---

## Summary of confidence

| # | File:line | Severity | Confidence |
|---|-----------|----------|------------|
| 1 | mutate.py:1621-1635 | MAJOR | High |
| 2 | mutate.py:1619-1635 (persistence) | Medium | Medium |
| 3 | mutate.py:1563 | Question | Low-medium |
| 4 | mutate.py:1759-1777 | Question | Low |
| 5 | ledger_guard.py:141-144 | Minor | Low |
| 6 | estate.py:364-365 | Question | Medium |
| 7 | estate.py:78 (+3 siblings) | Minor | Low |
| 8 | prose_gate.py:262-264 | Medium | Medium |
| 9 | coverage.py:272 | Medium | Medium |
| 10 | repass_bands.py:52,66,68,126,137 | Medium | Medium-high |
