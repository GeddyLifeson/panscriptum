# Audit — run44, batch 14

Modules read in full, top to bottom: `src/hostcheck.py` (1,411 lines), `src/escalation.py`
(1,081 lines), `src/identity.py` (711 lines), `src/sweep_plan.py` (571 lines), `src/tiers.py`
(458 lines), `src/feats_index.py` (369 lines), `src/context_budget.py` (296 lines),
`src/profile.py` (222 lines). 5,118 lines total.

`escalation.py` got the closest reading, per this shift's brief: the `clear()` compare-and-swap
and its three new helpers (`_land_clear`, `_halt_identity`, `_halt_file_cleared`) were traced
against every retry path, including the interaction with a concurrent `_raise_halt` landing
mid-lift. No break in that mechanism was found — the identity check correctly distinguishes a
transient write refusal from a fault landing under the lift, and the readback correctly refuses
to trust a bare `landed=True`. The two already-known items (`escalation.py:409`'s confirmed
mutation false-kill in `_land_halt`'s except arm, and the open questions on `class Refused` and
the level-normalisation block) were not re-investigated per instructions. **`clear()` was not
proposed as callable programmatically, and no change of any kind was made to `src/`.**

Nothing found rises above MEDIUM confidence/LOW-MEDIUM severity. This batch's modules — several
of them already the subject of extensive prior hardening passes with their own audit trail
visible in the comments — are in solid shape. The findings below are real and verified against
the quoted lines, but none is a corruption-causing logic error; most are display-layer or
documentation inconsistencies of the same *class* the project has already fixed elsewhere.

---

## 1. `src/tiers.py:403` — source names truncated to 26 chars with no marker, in a report that
    the project has already fixed this exact bug in elsewhere

```python
for v, a, b, sh in deliberate_joins(w, shared):
    print(f"   {v:>8.0f}  {a[:26]:<28}{b[:26]:<28}{sh}")
```

`deliberate_joins()`'s own docstring (lines 306-321) records that this exact function had its
shared-evidence-list truncation (`shared.get((a,b), [])[:3]`) removed under Hard Rule 0 after an
owner ruling on 2026-08-24, and cites three sibling fixes of the identical shape elsewhere in the
tree (`weave.py:519`, `pipeline.py:2401`, `cosmology_graph.py:209`). That fix covered the
**evidence list** (`sh`) — which is now printed whole, correctly — but left the **source names**
(`a`, `b`) truncated to 26 characters with no truncation marker, one line above the passage that
argues at length against exactly this shape of cut ("three was the number of reasons a person
could ever see for a join built on nine... A cap on the evidence for a claim is not a display
convenience").

`hostcheck.py` fixed the identical bug twice in this same audit shift's neighbouring file — see
`hostcheck.py:777` and `:1256-1259`, both explicitly commented "UNCUT (Hard Rule 0...)" after a
silent mid-name column truncation was found to make two sources with a shared prefix
indistinguishable in a report. The Panscriptum roll's longest source names are exactly the
publisher-plus-title parenthetical forms (`identity.py`'s own docstring measures one at 57
characters after sanitising), which are also the ones most likely to share the first 26
characters. This is the same class of bug in the same audit, in the sibling file that fixed it,
left unfixed here.

**Confidence: high that the code truncates with no marker, medium that this rises to a filed
Hard Rule 0 violation** — this is a diagnostic CLI report (`tiers.py main()`), not a write to a
catalogue or `TIERS.json` itself, so no library data is corrupted; the only cost is that a person
reading the "DELIBERATE JOINS" table cannot always tell two long, similarly-prefixed source names
apart.

---

## 2. `src/escalation.py` — `resume_subsystem`/`resume_subsystem_verdict` claim parity with
    `clear()`'s ruling requirement, but the two enforce different minimum lengths

- `escalation.py:713-714`, `resume_subsystem`'s docstring: *"Re-open one subsystem. **Demands a
  written ruling, exactly as `clear` does.**"*
- `escalation.py:511-513`, `stop_subsystem`'s docstring, same claim again: *"It is also
  deliberately STICKY: `resume_subsystem` **demands a written ruling, exactly as `clear` does**,
  because the thing that undid the last one was an automated actor..."*
- `escalation.py:742`, the actual check in `resume_subsystem_verdict`:
  ```python
  if not (ruling or "").strip() or len(str(ruling).strip()) < 20:
      raise ValueError("resuming a stopped subsystem needs a written ruling, not a shrug")
  ```
- `escalation.py:877`, the actual check in `clear()`:
  ```python
  if not ruling or not str(ruling).strip() or len(str(ruling).strip()) < 12:
      raise ValueError("a ruling is required, in words -- what did you decide and why? "
                       "(at least a short sentence)")
  ```

The two functions require **different minimum ruling lengths** (20 characters vs. 12) despite
being described twice, in two different functions' docstrings, as enforcing the identical rule.
Either the "exactly as `clear` does" claim overstates the parity (both require *a* ruling, but
not the same bar), or one of the two numbers is the one that drifted. This is a genuine
docstring-vs-code contradiction, verified at both quoted sites.

**Confidence: high** that the two thresholds differ and that the docstring asserts equivalence.
**Severity: low** — this is not a security hole (a longer bar is stricter, not looser; the "wrong"
direction would be if `clear()`'s 12-char floor let something as thin as `"ok, I looked."`
through where `resume_subsystem` would refuse it, which is true but cosmetic given both still
demand a real sentence).

---

## 3. `src/profile.py:109` vs. `:66,96` — `decode()`'s validating regex is looser than the B32
    alphabet it is meant to validate against

```python
B32 = "0123456789abcdefghjkmnpqrstvwxyz"        # line 66 — no i, l, o, u by design
...
m = re.fullmatch(r"PS-([0-9a-z]+)-([a-z]{2})([a-z])-([0-9a-z]{4})-([0-9au])([0-4])", profile)
                       ^^^^^^^^^^                        ^^^^^^^^^^
...
def _unb32(s):                                   # line 93-97
    n = 0
    for ch in s:
        n = (n << 5) | B32.index(ch)             # line 96 — no fallback
    return n
```

The module's own header (lines 52-65) is an extended argument for why the address alphabet must
be exactly the 32 symbols `_b32`/`_unb32` agree on, closing a run-#33 finding that `u` sat in the
alphabet as a 33rd, unreachable-by-the-encoder symbol that the decoder would nonetheless accept
and silently misdecode. That fix removed `u` from `B32` and reserved it for the band's
"unassayed" sentinel — but the two capture groups that validate the **address** and **feature**
digits, `([0-9a-z]+)` and `([0-9a-z]{4})`, still accept `i`, `l`, and `o`, which were never in
`B32` at all (Crockford's alphabet excludes them on purpose, per the comment at line 52). A
profile string containing any of those three letters in its address or feature segment passes
`decode()`'s regex validation cleanly, then reaches `_unb32`'s `B32.index(ch)` (or the equivalent
lookup for features, line 114), which raises a bare, uncaught `ValueError: substring not found`
rather than the clean `ValueError(f"not a world profile: {profile!r}")` the function raises for
every other kind of malformed input (line 111).

**Confidence: medium-high** that the regex accepts characters outside the actual encodable
alphabet, verified against the quoted lines. **Severity: low** — every profile `decode()` is
actually called on inside this codebase is one this same module just produced with `encode()`
(see `main()`'s round-trip section, which the file's own comments note was itself fixed this
sweep for being tautological), so `i`/`l`/`o` never appear from an internal caller today. This
only bites a hand-typed or externally-supplied profile string, which the header's own reasoning
about `u` suggests the decoder is meant to be defensive against.

---

## 4. `src/sweep_plan.py:70` — docstring claims a sort order the code does not implement

```python
def modules():
    """Every module in src/, newest-largest first. NO exclusions, deliberately.
    ...
    """
    ...
    return sorted(out, key=lambda m: -m["lines"])
```

The docstring says "newest-largest first"; the actual sort key is purely `-m["lines"]` — largest
line count first. Nothing in `modules()` reads a modification time or any other recency signal
anywhere in the function. This is a small, cosmetic wording mismatch (most likely leftover phrasing
from an earlier design, or "newest" was never meant literally), but it is a verifiable contradiction
between the docstring's claim and the code beneath it.

**Confidence: high** (trivial to verify — no `mtime`/`getmtime` call anywhere in the function).
**Severity: very low** — `batches()`'s own docstring (line 103) correctly describes the actual
behavior as "longest-first bin packing," so the one place that depends on the ordering documents
it correctly; only `modules()`'s own one-line summary is wrong.

---

## 5. `src/identity.py:701-702` — the continuity-inventory summary caps each host's report to the
    top 6 continuities

```python
for host, cont in sorted(rows, key=lambda kv: -len(kv[1])):
    top = sorted(cont.items(), key=lambda kv: -kv[1])
    names = ", ".join(f"{d} ({n})" for d, n in top[:6])
    more = f" +{len(top) - 6} more" if len(top) > 6 else ""
    print(f"\n  {host}  — {len(cont)} continuities")
    print(f"     {names}{more}")
```

This is the `--host`-less summary branch of `identity.py main()`. It ranks (fine) then truncates
the printed list to 6 entries per host, with a "+N more" marker naming how many were cut. The
project's Hard Rule 0 explicitly names "top N... on an ordered listing" as forbidden regardless of
whether the cut is marked, and the file's own `--host` branch three lines below (line 682-688)
prints every row with no cap at all, so the un-capped behavior clearly exists and was chosen for
one branch and not the other.

**Confidence: medium** that this is the kind of truncation Hard Rule 0 targets (versus a
defensible "summary line" convention distinct from the roster/entry-list truncations the rule's
examples describe). **Severity: very low** — this is a console summary line, not a write to any
file the pipeline reads, and the count of what was cut is stated openly.

---

## Not filed (already covered by this shift's brief)

- `escalation.py:409` (approx.) — confirmed mutation false-kill in `_land_halt`'s except arm,
  `False -> True`. Not re-investigated; already covered by orders `a380a696d364` and
  `e5954a534604`.
- `escalation.py`, `class Refused` (~line 75) — open question, order `da15f582b2ea`. Not re-filed.
- `escalation.py:222-234`, `escalate()`'s level-normalisation block — open question, order
  `762256b4b844`. Not re-filed. (Read closely as part of this pass; the MANAGER-not-OWNER fallback
  for an unrecognised level, and the string-numeral edge case `escalate("2", ...)` falling through
  to MANAGER rather than being read as `SUPERVISOR`, both behave as the existing comments already
  describe and argue for. No new angle found worth adding to the open question.)
- `escalation.py`'s `clear()`/`_land_clear`/`_halt_identity`/`_halt_file_cleared` CAS chain,
  including the corroboration (`also`) list, the digest-before-read ordering, and the interaction
  where a new OWNER fault can land in the narrow window between a successful `_land_clear` and its
  own readback (`_halt_file_cleared()`) — traced in detail; in every traced scenario the mechanism
  fails toward reporting "not cleared, re-read and rule again" rather than toward a false success.
  No confirmed defect found in this hours-old code.

## Not filed (considered and rejected as findings)

- `escalation.py`'s `_by_a_person_at_the_cli()` (line ~859-862): `sys._getframe(2)` either
  returns a frame or raises `ValueError` (caught above it) — it can never return `None` — so the
  `f is not None` half of the final `return` is dead/tautological. Harmless (the exception path
  already returns `False`); not filed as a defect, noted here only because it is exactly the
  "guard that cannot fail" shape this audit was asked to watch for, and I want the shape on record
  even though this instance carries no consequence.
- `hostcheck.py`'s statistical sampling caps (`PROBE = 40`, `relevance(..., sample=12)`,
  `null_rate(..., sample=40)`, `foreign.extend(names[:3])`) — these bound API probes and control
  samples for a lift measurement, not catalogue/roster/entry listings; each is reasoned at length
  in its own docstring and is a measurement-methodology choice rather than the "smaller universe
  wearing the same shape" truncation Hard Rule 0 targets. Not filed.
- `feats_index.py:267-268`, `entries_by_norm.setdefault(_norm(e.get("name")), e)` — if two
  catalogue entries in the same source's record normalise to the same name, only the first is
  retained for feat-matching; the second's entry metadata could never be attached to a feat.
  Plausible in principle, no evidence found that it occurs on the live catalogue, and no docstring
  claims otherwise. Too speculative to file as a finding; flagged here only as a thing to watch if
  `feats_for_source`'s join rate is ever measured again.
- `context_budget.py` — read in full; the derived-budget arithmetic (`content_budget_chars`,
  `feats_block_budget`, the prose/content ratio split) checks out consistently against its own
  extensive header. No finding.
- `hostcheck.py`'s `_land_hosts` compare-and-swap and `escalation.py`'s `_raise_halt`/
  `stop_subsystem`/`resume_subsystem_verdict` CAS loops — all read closely for the retry/refusal
  shapes named in the brief. All retry on any failure (not on a parsed reason), all take their
  digest before the read, all report a genuine non-landing rather than assuming success. No
  defect found beyond what is already filed above.

## Coverage

Recorded via `sweep_plan.record('run44', [...8 modules...], batch=14)` — see the confirmation
below.
