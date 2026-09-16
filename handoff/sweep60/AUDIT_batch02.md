# sweep60 batch02 — audit of src/verify_math.py

Scope: the entire file, 13,337 lines, read sequentially start to finish (offsets 1-13337, no
sampling). No file under `src/` was edited. This report is the only file written.

## Summary

This file is already the product of an extremely long, adversarial, self-correcting audit
history (visible in its own comments: dozens of named "orders", mutation-testing survivor
write-ups, canaries for its own negative scans, controls for its own controls). Nearly every
shape on the priority list handed to me for this sweep — tautological comparisons, guards on
always-true conditions, checks whose probe returns True on the error path, `all()` over a
possibly-empty list, stale `file.py:NNN` citations, silent caps — has already been found and
repaired at least once in this exact file, with the repair narrated in a comment and a
"[control]" row added beside the fix to prove the detector has teeth. That makes a fresh pass
much less likely to turn up more of the same, and it did not, with one exception below.

**Finding count: 1 confirmed (verified by direct execution), 0 unsure, 0 dismissed.**

The rest of the file, as far as I can tell from a full sequential read, is clean of the failure
classes I was asked to hunt for. That is a genuine result, not a placeholder — see "What I did
not find" at the end.

---

## Finding 1 (confirmed, verified by direct testing): the self-citation scanner's
"continuation" heuristic can be fooled by a mention of `verify_math.py` itself, silently
hiding a genuine self-citation by line number

**Where:** `_self_cites20ad()`, lines 12285-12357 (the regexes at issue are at lines 12289-12292:
`_FILE20ad`, `_SELF20ad`, `_BARE20ad`). The check that consumes it is at line 12360.

**What it's for:** Section §20ad exists specifically because this file cited *itself* by line
number sixteen times, and every one of them had drifted onto unrelated code by the time anyone
checked (documented at length in the comment block starting at line 12233). The scanner's whole
job is to make sure no future `:NNNN` reference to this file's own source can rot the same way.

**The bug:** `_self_cites20ad` treats "a bare `:NNNN` after some file has been named in the same
comment block" as a *continuation* of that file's citation, and deliberately does not flag it
(this is documented as an accepted trade-off for citations of *other* files — e.g.
`sweep.py:129 ... and ":160"`). But the "some file has been named" test (`_FILE20ad`, a generic
`something.py` pattern) fires identically whether the named file is some *other* module or
`verify_math.py` **itself**. When the named file is this file, a later bare `:NNNN` in the same
block is still a self-citation by line number — exactly the thing §20ad exists to catch — but
it gets swallowed by the same suppression logic and never reaches `_out20ad`.

`_SELF20ad` (`verify_math\.py:(\d{1,5})\b`) only catches the case where the filename and the
number are directly adjacent (`verify_math.py:1234`). It does nothing for the shape "mention
`verify_math.py` in prose, then reference a line number later in the same comment without
repeating the filename" — which is precisely the natural way a person would write such a
comment, and precisely the pattern the file's own examples show for *other* files
(`sweep.py:129 ... and ":160"`).

**Verified by direct execution** (I ran the three regexes from the live file against a
constructed one-line fixture, not a hypothetical):

```
s = "# verify_math.py handles this at :4273-4301, see the device"
FILE matches: ['verify_math.py']      # sets _named20ad = True
SELF matches: []                       # does not fire — no adjacent "verify_math.py:NNNN"
BARE matches: [':4273']                # would fire, but is suppressed because _named20ad is True
```

Under the real function's control flow, this line produces **zero** entries in `_out20ad`, so
`check("no comment or docstring in this file cites this file by line number", ...)` at line
12360 would read green over a stale self-citation of exactly the shape order 363c79272987 was
filed about.

**Currently live or not:** I grepped the current file for every occurrence of `verify_math.py`
that is *not* immediately followed by `:<digits>` and checked each one for a later bare
`:NNNN` in the same comment/docstring block. None of the current occurrences have this shape —
they are either explicit `verify_math.py:<site-name>` labels (a string label, not a line
number, which is a different and already-correctly-exempted pattern) or plain prose with no
trailing bare line-number reference nearby. **So this is a live logic gap in the detector, not
a currently-undetected stale citation in the file today.** It is a guard that fails open under
a condition that has not yet been triggered by this file's own prose — which is exactly the
shape this file's own doctrine treats as worth fixing before it is exploited, not after (c.f.
the file's repeated "a check that cannot fail looks exactly like a check that passed" framing,
and its practice of writing canaries for scans before they are needed).

**Whether this is "deliberate":** The comment at lines ~12269-12276 states the trade-off in
general terms — "a block that names any file suppresses bare citations after it" — which,
read literally, covers the self-mention case too. But the stated *purpose* of the whole
section is narrower than that: catching this file's citations of *itself*. Accepting a false
negative for a citation of *another* file (to keep the check from being noisy enough to invite
hand re-pinning) is a reasonable trade explicitly argued for in the file. Silently accepting a
false negative for a citation of *this file*, when the whole section exists only to catch that
case, does not obviously follow from the same argument — the noise concern is about *other*
files' churn, not about missing this file's own line numbers, which is the one thing the
section is for. I read this as an oversight rather than a considered decision, but I flag the
ambiguity rather than asserting it outright.

**Suggested shape of a fix** (not applied — I did not touch `src/`): treat a match of
`verify_math.py` by `_FILE20ad` as *not* setting `_named20ad`, or route it through `_SELF20ad`'s
stricter "must be adjacent" rule so a subsequent bare `:NNNN` is still evaluated as a
self-citation rather than being read as a continuation of "some other file."

---

## What I looked at and did not find a defect in

For the record, since "clean" needs to be earned rather than asserted: I specifically checked
(among many other things) —

- The `check()` function itself (line ~85) and its `tol=` handling — matches the file's own
  `_discarded_tol20z` scan's model of what is and isn't silently coerced to exact equality.
- The tri-state verdict helpers (`_sigma_table_verdict`, `_iw_verdict`, `_axis_refusal`,
  `_readings_refusal`) that this file uses specifically to avoid "a crash reads as a pass"
  bugs — all correctly report `"RAISED <Type>"` rather than folding an exception into `False`.
- The various AST-based negative scans (`_ctx_literals_in19ab`, `_failopen_in20p`,
  `_writes_the_config20p`, `_clear_callers20t`, `_disarmed_rows20i`, `_standins20ae`,
  `_standins_wide20ae`) — each carries a "[control]" row exercising both a must-catch and a
  must-not-catch fixture, and I checked several of these by hand against their stated
  behaviour; they hold up.
- The sha256 pins in `_RUN35_PINNED36` (lines ~11541-11551) against the actual bytes of
  `handoff/run35/checks_L1.py` through `checks_L6.py` on disk — computed independently with
  `hashlib.sha256`, all six match exactly. No drift.
- The scratch-directory/temp-file cleanup discipline (`_mkdtemp_vm`, the `finally` blocks
  around every `_no_ledger_vm()`/`_third_party_vm()` probe) — consistent with the file's own
  stated inventory of what is and isn't swept at exit.
- Whether any of the module-level variable rebindings the file itself calls out (`_a`, `_b`,
  `_ap`, `_here19h` vs `_here19`, etc.) still collide anywhere — I did not find a new one beyond
  the ones already named and fixed in the file's own comments.

I did not find any tautological `check(label, True, True)` calls, any `all(...)` over a
demonstrably-possibly-empty list without a companion "real population" row, any bare
`except: pass` that lets work proceed silently, or any `[:N]` cap on a listing that isn't
explicitly labelled and justified as a bounded fixture (e.g. `PR.build_all(limit=400)`, which
the file itself labels "A SAMPLE, and labelled as one").

## Coverage note

Read in full via sequential `Read` calls covering every line from 1 to 13337 (offsets 1, 400,
900, 1400/1700, 2000, 2300, 2600, 2900, 3200, 3500, 3800, 4100, 4400, 4700, 5000, 5300, 5600,
5900, 6200, 6500, 6800, 7100, 7400, 7700, 8000, 8300, 8600, 8900, 9200, 9500, 9800, 10100,
10400, 10700, 11000, 11300, 11600, 11900, 12200, 12500, 12800, 13100, 13334-13337). No section
was skipped or skimmed.
