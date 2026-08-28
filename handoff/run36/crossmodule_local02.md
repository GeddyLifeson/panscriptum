# Cross-module needs — LOCAL batch 2 (run 36)

Agent scope: descending_ladder.py, feats.py, local_agent.py, overwatch.py,
recover_folder_records.py only.

## Order 671d32878fa6 (vulture-found unused locals) — my part already fixed, one part is
## out of scope, one part looks like a false positive

The order bundles three findings under one id:

1. **descending_ladder.py:129 `from_m` — ALREADY FIXED, not by me.** Verified live against
   `shrink_report()` (currently defined at line 156): `from_m` is read at lines 185-186
   (`"from_m": from_m, ... "is_descent": bool(from_m is not None and to_m < from_m)`), and the
   function's own docstring (159-164) narrates the exact fix: *"`from_m` was accepted and then
   never mentioned again... `from_m`, `to_m` and whether this is actually a descent are reported
   as data."* Another agent fixed this earlier in the shift, before this order reached me. No
   action needed; closing my share of the order on this evidence.

2. **verify_math.py:2310 `kw` — NOT REPRODUCIBLE, and I don't own this file.** Ran
   `vulture --min-confidence 90 src/verify_math.py` fresh just now; it reports 14 unused-variable
   findings and none of them is `kw` at any line. The nearest `**kw` catch-alls in the file
   (`_gl_fake_ask` at 2530, `_one_match_assay` at 5391, `_breaking_open_b3` at 6013) are
   pass-through kwargs vulture does not flag by default. Either this was already fixed, or the
   line number/variable name drifted from a different vulture run. **Whoever owns verify_math.py
   this shift:** worth a 30-second re-check with vulture, but I found nothing to hand you.

3. **verify_math.py:2399 `socktype` — CONFIRMED PRESENT (now at line 2619), but looks like
   deliberate design, not a bug.** `vulture --min-confidence 90` does flag it:
   `src/verify_math.py:2619: unused variable 'socktype' (100% confidence)`. Context:
   ```
   class _StubNet:
       """A stand-in socket module: which addresses exist, and which of them answer."""
       AF_INET, AF_INET6, SOCK_STREAM = 2, 23, 1
       def getaddrinfo(self, host, port, family=0, socktype=0):
           self.asked.append(family)
           ...
   ```
   This is a test stub standing in for the real `socket` module and matching
   `socket.getaddrinfo`'s real signature (`getaddrinfo(host, port, family=0, type=0, proto=0,
   flags=0)`), even though the stub's own logic only needs `family`. That reads as intentional —
   a stub that dropped `socktype` from its signature would silently stop matching call sites that
   pass it positionally or by keyword. **This is a question, not a mechanical fix**: if you (the
   verify_math.py owner) agree it's deliberate, it's a NOT_FILED entry with a one-line reason
   (per `secondopinion.py`'s convention), not a dead-parameter removal.

## Order 9beb0391c8ab (feats.py `page_looks_real` unused `title`) — left OPEN, needs a design
## call plus a file I don't own

Confirmed live: `feats.py:203` — `def page_looks_real(text, title="", wiki=True):` — `title`
is never read in the function body (only named in the docstring). Two real callers pass it:
`feats.py:1157` (`page_looks_real(wt, t, wiki=wiki_source)` — mine, already using the param
positionally) and **`binding_health.py:236`** (`F.page_looks_real(text, title)` — not mine).

The order offers two remedies and both cross a line I can't cross alone from feats.py:

* **Drop the parameter.** Requires editing `binding_health.py:236`'s call site (not owned by
  this batch) as well as `feats.py:1157`'s, or the signature change breaks the un-owned caller
  with a `TypeError` (too many positional args). A `local_agent.py` order in this same batch
  (a75cd9ac1273) exists specifically because an uncaught `TypeError` from a signature mismatch
  is the failure mode this shift is trying to close elsewhere — I don't want to open the same
  class of bug here just to close a MINOR lint finding.
* **Wire `title` into the check for real** (the order's own suggested use: catch a soft-404 that
  returns a different article under the same URL). This is a genuine behavior change to a
  function three other call sites already depend on for pass/fail (`drill.py:1536-1537`,
  `feats.py:1157`), and picking the right check (does the article need to literally contain its
  own title? how close a match?) is a judgment call about false-negative risk on real wiki pages,
  not a mechanical fix I should make unilaterally under "minimal changes only."

Left OPEN. **Whoever owns binding_health.py this shift** — worth deciding together whether the
right fix is (a) drop `title` from `page_looks_real`'s signature and both call sites, or (b)
actually implement the soft-404 check the docstring/order gestures at. Either is a two-file
change spanning our modules.
