# Sweep 43, batch 2 — audit of `src/verify_math.py`

Scope: the entire file, 9,281 lines, read top to bottom in full. This file is itself a
self-verification battery (over 1,000 `check()` assertions covering `physics.py`, `assay.py`,
`cosmography.py`, `propagation.py`, `tempus.py`, `ledger.py`, `derivation.py`, `rigor.py`,
`custodes.py`, `address_space.py`, `profile.py`, `grounding.py`, `sevenfold.py`, `burgs.py`,
`magnitude.py`, `identity.py`, `lognames.py`, and roughly forty more modules), plus a long tail
of AST-based structural scanners, mutation-test regression pins, and "canary" positive controls
proving those scanners can actually fire.

## Method note

Per the sweep's own scope, this batch audits `verify_math.py`'s **own** logic: the `check()`
harness, its module-level helper functions (`_slices_of`, `_tier_counts`,
`_nesting_violations`, `_mode_stable`, `_disarmed_rows20i`, `_write_mode`, `_int_valued20z`,
`_blank_prose20z`, `_prose_backed20z`, `_tagchars20y`, the §20p/§20t AST scanners, etc.), and the
internal arithmetic of its worked-example checks (recomputed by hand where cheap to do so:
Earth binding energy, the Charter Kenshiro Sigma worksheet, the Mihai Instrument example, tier
nesting/ordering logic, and others — all reproduced correctly). It does **not** re-verify the
correctness of the ~50 external modules under test, since asserting `X == Y` where X comes from
a live call into (e.g.) `standards.py` is a claim about that module, out of this batch's file
list; those modules are other batches' subjects.

This file is unusually self-hardened: it documents dozens of previously-found defects (survived
mutants, disarmed tautologies, green-by-absence checks, prose-vs-code scanning traps) and, for
nearly every scanner it contains, carries an explicit positive-control "canary" proving the
scanner can still fire on the shape it exists to catch, plus a negative control proving it does
not cry wolf on ordinary code. This materially reduces the space of undiscovered defects of the
kind this file has repeatedly found in itself. Given that, the yield below is intentionally
short rather than padded.

## Findings

### MINOR — `_write_mode`'s docstring contradicts its own return value

- **File:line**: `src/verify_math.py:3964-3966`
- **Quoted code**:
  ```python
  def _write_mode(c):
      """The mode string of an open() call, positional or keyword; '' if not an open()."""
      if _cname(c) != "open" or not c.args:
          return None
  ```
- **What actually happens**: the docstring promises `''` (empty string) for a call that is not
  `open(...)`; the code returns `None` in that case. The two are not the same value and are not
  treated the same way by a caller that tests `m == ""` versus one that tests `m is None`.
- **Why it matters**: Hard Rule -1's own doctrine (and this file's stated practice throughout)
  treats a docstring/code mismatch as load-bearing, because the comment is how the next reader
  learns the contract. A future edit to either call site that trusted the docstring's `''` (e.g.
  `if _write_mode(c) == "": ...`) would silently treat every non-`open()` call as "an open call
  with no explicit mode" instead of "not an open call at all" — the exact class of confusion
  Hard Rule -1 calls out elsewhere in this file (e.g. the `did[:5]`/prose-vs-code traps).
- **Verified impact today**: both current call sites (`src/verify_math.py:3980` inside
  `_writes_the_config20p`'s bare-write scan, and `:3996` inside `_for_owner_landing_b19`'s
  `_opened_w` collection) guard with `m is not None and any(ch in m for ch in "wax")`. Since an
  empty string never contains any of `"w"`, `"a"`, `"x"`, the `any(...)` half would be `False`
  regardless of whether a non-open call returned `None` or `''` — so **today** the two callers
  behave identically either way, and this finding has no live behavioural consequence. It is
  reported because the contract described is not the contract implemented, in a file whose whole
  argument is that such a divergence is how the next defect gets in.
- **Suggested remedy**: change the docstring to say `None if not an open()` (matching the code),
  or change the code to `return ""` (matching the docstring). Either is safe given the verified
  call-site behaviour above; no functional change is required, only bringing the two back into
  agreement.

## Clean

Everything else read in this file — the `check()` comparison logic (including its documented
`isinstance(want, float)` gating and the deliberate `bool`-is-`int` carve-out), the `PASS`/`FAIL`
accumulation, the `health.record` spy/wrapper and its own exercised ratchet (§20z), the
`_no_ledger_vm` context manager, `_slices_of`'s four-spelling truncation-AST scanner (including
its handling of nested subscript bases), `_tier_counts`/`_nesting_violations` (verified the
"multiverse → hyperverse" ordering direction against the charter's own printed shelfmark order,
`Ω › H0 › X2 › Mt.3 › Mv.11 › U-40`, and confirmed "count decreases going up" is the correct
claim), `_mode_stable`'s lexicographic tie-break, the §19ab/§20e/§20p/§20t AST scanners for
hardcoded `num_ctx`, unguarded subprocess spawns, the escalation fail-open shape, and
`escalation.clear()` callers, the §20i disarmed-check detector, the §20y section-tag-collision
scanner (including its three-spelling header recognition), the §20z duplicate-label and
discarded-`tol=` scanners, and the §20z prose-vs-code "needle" scanner — all matched their stated
behaviour, and every arithmetic worked example spot-checked by hand (Earth's gravitational
binding energy, the Charter Kenshiro Sigma computation and its two erratum revisions, the X.6 §7
Mihai Instrument example, the tier-count ordering) reproduced correctly.

No Hard Rule 0 (cap) violations were found in this file's own code. The one `limit=400` call
(`PR.build_all(limit=400)`, §14) is explicitly labelled in its own comment as a deliberate,
disclosed test sample for round-trip verification speed, not a production listing being
silently truncated, and is not itself a finding.

## Questions for the owner

None raised by this batch — no ambiguous design/curatorial judgment calls were found; the one
finding above is unambiguous (docstring says one thing, code does another) and did not require
an owner ruling to resolve.
